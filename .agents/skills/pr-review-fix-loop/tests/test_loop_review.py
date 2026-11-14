"""レビュアーの起動・結果の検査・再利用・資源の回収と、2 サイクル以上の流れを確かめる。

レビュアーは runner の adapter を差し替えた偽の CLI（conftest の REVIEWER_PROGRAM）で、PR は bare remote と偽の gh。
計画担当（review-fix-planning）の代わりに、テストが記録の投稿・push・指定 commit のレビューの保存・マージを行う。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from tools.agent_runner.models import (
    Attempt,
    BatchResult,
    Identity,
    Request,
    Result,
)

pytest_plugins = ("tools.test_support.plugin",)
# 偽の担当だけを起動するので、runner の担当（AGENT_RUNNER_DEPTH=1）の中でもテストの中だけ depth を外す
pytestmark = pytest.mark.usefixtures("outside_runner")


def registered_worktrees(root: Path) -> list[str]:
    listing = subprocess.run(
        ["git", "-C", str(root), "worktree", "list", "--porcelain"], check=True, capture_output=True, text=True
    ).stdout
    return [line.removeprefix("worktree ") for line in listing.splitlines() if line.startswith("worktree ")]


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# --- 結果の検査 ---------------------------------------------------------------------------------------------------


def accepted_result(env: Any, tmp_path: Path) -> tuple[Result, str]:
    """検査を通る 1 人分の runner の結果（成果 2 件をレビューディレクトリに置く）。"""
    head = env.gh.head()
    review, candidates = env.place_review(head, "alpha-model", findings=1)
    request = Request(
        run_id="run-1",
        request_id="request-1",
        agent_id="alpha",
        role="inspect",
        work_dir=tmp_path / "work",
        prompt="review",
        deadline_seconds=60.0,
        result_shape="json",
    )
    request_path = tmp_path / "request.json"
    request_path.write_text(request.model_dump_json(), encoding="utf-8")
    document = read(candidates)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "success",
        "run_id": "run-1",
        "request_id": "request-1",
        "agent_id": "alpha",
        "role": "inspect",
        "repository": "usaturn/create-reso-world",
        "pr_number": 900,
        "pr_head": head,
        "reviewed_head": head,
        "review_file": str(review),
        "findings_file": str(candidates),
        "active_findings": 1,
        "cleanup": "success",
        "cleanup_details": {},
        "retained_paths": None,
        "reason": None,
        "reviewer": document["reviewer"],
        "timing": document["timing"],
    }
    attempt = Attempt(
        agent_id="alpha",
        state="success",
        identity=Identity(model="alpha-model"),
        exit_code=0,
        elapsed_seconds=1.0,
        stop_confirmed=True,
        work_dir=tmp_path / "work",
        request_path=request_path,
        payload=payload,
    )
    result = Result(
        request_id="request-1",
        role="inspect",
        requested_agent="alpha",
        actual_agent="alpha",
        state="success",
        attempts=[attempt],
    )
    return result, head


def broken(result: Result, case: str, env: Any, tmp_path: Path) -> Result:
    attempt = result.attempts[-1]
    payload: dict[str, Any] = dict(cast(dict[str, Any], attempt.payload))
    attempt_update: dict[str, Any] = {}
    result_update: dict[str, Any] = {}
    if case == "outer_failed":
        result_update["state"] = "timed_out"
    elif case == "stop_unconfirmed":
        attempt_update["stop_confirmed"] = False
    elif case == "payload_failed":
        payload["status"] = "failed"
    elif case == "request_mismatch":
        payload["request_id"] = "request-2"
    elif case == "actual_agent_mismatch":
        # request と payload が一致していても、実際に実行した担当との照合が必要。
        result_update["actual_agent"] = "beta"
    elif case == "other_pr":
        payload["pr_number"] = 901
    elif case == "reviewed_head_mismatch":
        payload["reviewed_head"] = "0" * 40
    elif case == "review_outside_dir":
        outside = tmp_path / "outside.md"
        outside.write_text(Path(payload["review_file"]).read_text(encoding="utf-8"), encoding="utf-8")
        payload["review_file"] = str(outside)
    elif case == "review_symlink":
        link = env.review_dir / "link.md"
        link.symlink_to(payload["review_file"])
        payload["review_file"] = str(link)
    elif case == "pair_mismatch":
        review = Path(payload["review_file"])
        review.write_text(review.read_text(encoding="utf-8").split("## High")[0], encoding="utf-8")
    elif case == "active_count_mismatch":
        payload["active_findings"] = 0
    attempt_update["payload"] = payload
    attempts = [attempt.model_copy(update=attempt_update)]
    return result.model_copy(update={**result_update, "attempts": attempts})


@pytest.mark.parametrize(
    "case",
    [
        "outer_failed",
        "stop_unconfirmed",
        "payload_failed",
        "request_mismatch",
        "actual_agent_mismatch",
        "other_pr",
        "reviewed_head_mismatch",
        "review_outside_dir",
        "review_symlink",
        "pair_mismatch",
        "active_count_mismatch",
    ],
)
def test_verify_reviewer_rejects_each_broken_condition(loop: Any, env: Any, tmp_path: Path, case: str) -> None:
    result, head = accepted_result(env, tmp_path)
    pr = loop.PrRef(
        repository="usaturn/create-reso-world", number=900, url="https://github.com/usaturn/create-reso-world/pull/900"
    )

    entry = loop.verify_reviewer(broken(result, case, env, tmp_path), pr=pr, head=head, review_dir=env.review_dir)

    assert entry.verdict == "rejected"
    assert entry.reason


def test_verify_reviewer_accepts_a_complete_payload_and_records_hashes(loop: Any, env: Any, tmp_path: Path) -> None:
    result, head = accepted_result(env, tmp_path)
    pr = loop.PrRef(
        repository="usaturn/create-reso-world", number=900, url="https://github.com/usaturn/create-reso-world/pull/900"
    )

    entry = loop.verify_reviewer(result, pr=pr, head=head, review_dir=env.review_dir)

    assert entry.verdict == "accepted", entry.reason
    assert entry.active_findings == 1
    assert entry.review_sha256 == loop.sha256_file(Path(entry.review_file))
    assert entry.findings_sha256 == loop.sha256_file(Path(entry.findings_file))
    assert entry.identity["model"] == "alpha-model"


@pytest.mark.parametrize(
    "change",
    [
        "payload_failed",
    ],
)
def test_after_run_result_is_reloaded_before_reviewer_validation(
    loop: Any, env: Any, tmp_path: Path, change: str
) -> None:
    # 後処理（after_run）が result.json を更新したら、レビュアーの検査はその保存された結果を使う
    program = (
        "import json,pathlib,sys; path=pathlib.Path(sys.argv[1]); batch=json.loads(path.read_text())\n"
        "for item in batch['results']:\n"
        "    if item['actual_agent'] == 'alpha' and " + repr(change) + " == 'payload_failed':\n"
        "        item['attempts'][-1]['payload'].update(status='failed', reason='後処理が保存を拒否した')\n"
        "path.write_text(json.dumps(batch))\n"
    )
    with env.template.open("a") as stream:
        stream.write(
            "\n[workflows.review]\nafter_run = " + json.dumps([[sys.executable, "-c", program, "{result}"]]) + "\n"
        )
    run_dir = Path(env.start()["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    adapter = env.reviewers({"alpha": "success", "beta": "failed"})
    if change == "payload_unchanged":
        reviewed = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
        assert [item["agent"] for item in reviewed["accepted"]] == ["alpha"]
        return
    # 後処理が却下させた alpha と、失敗した beta を 1 回だけ再実行する。再実行の結果にも同じ後処理がかかる
    pending = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
    assert pending["rerun"] == {"agents": ["alpha", "beta"]}
    with pytest.raises(loop.LoopError) as error:
        loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
    assert (error.value.code, error.value.stage) == (6, "review")
    reviewers = read(run_dir / "cycle-1.json")["review"]["reviewers"]
    alpha = next(item for item in reviewers if item["actual_agent"] == "alpha")
    assert alpha["verdict"] == "rejected" and "後処理が保存を拒否した" in alpha["reason"]
    saved = read(run_dir / "cycle-1" / "rerun-result.json")
    saved_alpha = next(item for item in saved["results"] if item["actual_agent"] == "alpha")
    assert saved_alpha["attempts"][-1]["payload"]["status"] == "failed"


def test_review_executes_after_run_against_saved_result(loop: Any, env: Any, tmp_path: Path) -> None:
    marker = tmp_path / "hook-result.json"
    program = f"import pathlib,sys; pathlib.Path({str(marker)!r}).write_bytes(pathlib.Path(sys.argv[1]).read_bytes())"
    with env.template.open("a") as stream:
        stream.write(
            "\n[workflows.review]\nafter_run = " + json.dumps([[sys.executable, "-c", program, "{result}"]]) + "\n"
        )
    run_dir = Path(env.start()["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    reviewed = loop.review(
        run_dir,
        github=env.github,
        adapter_loader=env.reviewers({"alpha": "success", "beta": "success"}),
        tmp_root=env.tmp_root,
    )
    assert len(reviewed["accepted"]) == 2
    assert read(marker)["state"] == "success"
    reports = read(run_dir / "cycle-1.json")["review"]["after_run"]
    assert reports[0]["state"] == "success" and reports[0]["stop_confirmed"]


def test_reuse_counts_only_pairs_for_the_current_head(loop: Any, env: Any, kit: Any) -> None:
    pr = loop.PrRef(
        repository="usaturn/create-reso-world", number=900, url="https://github.com/usaturn/create-reso-world/pull/900"
    )
    old = env.gh.head()
    env.place_review(old, "gamma")
    new = env.push("新しい commit")
    env.place_review(new, "alpha", commit=True)
    # gamma の本文を新しい HEAD のものに上書きした（候補一覧は古い HEAD のまま）
    env.place_review(new, "gamma")
    stale = env.review_dir / "findings" / f"gamma-{old[:12]}.json"
    assert stale.exists()

    reused_new = loop.find_reusable(env.review_dir, pr, new)
    reused_old = loop.find_reusable(env.review_dir, pr, old)

    assert sorted(Path(item.review_file).name for item in reused_new) == ["alpha-commit-" + new + ".md", "gamma.md"]
    assert reused_old == []


# --- レビューの起動 -----------------------------------------------------------------------------------------------


def test_review_refuses_when_the_head_moved_after_cycle_begin(loop: Any, env: Any) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    adapter = env.reviewers({"alpha": "success", "beta": "success"})
    env.push("cycle-begin の後の push")

    with pytest.raises(loop.LoopError) as error:
        loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert (error.value.code, error.value.stage) == (4, "head_moved")
    assert adapter.launched == []


def test_review_records_partial_failure_and_cleans_owned_worktrees(loop: Any, env: Any) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    adapter = env.reviewers({"alpha": "success", "beta": "failed"}, findings=1)

    pending = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
    assert pending["rerun"] == {"agents": ["beta"]}
    reviewed = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert sorted(adapter.launched) == ["alpha", "beta", "beta"]
    assert [item["agent"] for item in reviewed["accepted"]] == ["alpha"]
    assert [item["agent"] for item in reviewed["rejected"]] == ["beta"]
    assert reviewed["next"][-3:] == ["cycle-end", "--run", str(run_dir)]
    # 保護しない checkout の変化は警告として受け取り、致命にしない（runner の記録をそのまま渡す）
    cycle = read(run_dir / "cycle-1.json")
    assert reviewed["unprotected_changes"] == cycle["review"]["batch"]["unprotected_changes"]
    assert cycle["state"] == "planning"
    beta = next(item for item in cycle["review"]["reviewers"] if item["actual_agent"] == "beta")
    assert beta["verdict"] == "rejected" and beta["active_findings"] is None
    assert (run_dir / "cycle-1/review-result.json").is_file()
    run = read(run_dir / "run.json")
    assert [resource["state"] for resource in run["resources"]] == ["removed", "removed"]
    assert not any(Path(resource["path"]).exists() for resource in run["resources"])
    assert registered_worktrees(env.parent) == [str(env.parent)]


def test_review_with_no_accepted_reviewer_fails_with_code_6(loop: Any, env: Any) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    adapter = env.reviewers({"alpha": "failed", "beta": "failed"})
    # 全員が runner の成功の後に却下されたので、まず全員を 1 回だけ再実行する
    pending = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
    assert pending["accepted"] == [] and pending["rerun"] == {"agents": ["alpha", "beta"]}

    with pytest.raises(loop.LoopError) as error:
        loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert (error.value.code, error.value.stage) == (6, "review")
    assert error.value.next_command[-4:-1] == ["finish", "--run", str(run_dir)]
    cycle = read(run_dir / "cycle-1.json")
    assert [item["verdict"] for item in cycle["review"]["reviewers"]] == ["rejected", "rejected"]
    finished = loop.finish(run_dir, abort="external: レビュアーが全員失敗した", github=env.github)
    assert finished["lock_released"] is True


# --- 2 サイクル以上 -----------------------------------------------------------------------------------------------


def test_reviewers_receive_the_previous_round_when_the_head_moved(loop: Any, env: Any, kit: Any) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    head1 = loop.cycle_begin(run_dir, github=env.github)["head"]
    loop.review(run_dir, github=env.github, adapter_loader=env.reviewers({"alpha": "success"}), tmp_root=env.tmp_root)
    skip_ref = f"alpha-model#M-1@{head1[:12]}"
    pushed = env.push("修正")
    env.gh.post_record(
        kit.round_record(
            1,
            head1,
            "fixes_pushed",
            [kit.decision(skip_ref, "skip", "new"), kit.decision(f"alpha-model#H-1@{head1[:12]}", "fix", "new")],
            commit=pushed,
            seats=[kit.seat(head1, "alpha-model")],
        )
    )
    loop.cycle_end(run_dir, github=env.github)
    head3 = env.push("別の人の push")

    second = loop.cycle_begin(run_dir, github=env.github)
    assert second["review"]["mode"] == "run"
    assert second["notes"]
    loop.review(run_dir, github=env.github, adapter_loader=env.reviewers({"alpha": "success"}), tmp_root=env.tmp_root)

    received = kit.records.read_state(kit.records.comments_from_api(read(env.root / "copies/alpha.json")))
    assert [entry["round"] for entry in received["rounds"]] == [1]
    assert received["decisions"][0]["state"] == "skip"
    env.gh.post_record(
        kit.round_record(
            2,
            head3,
            "stopped",
            [kit.decision(skip_ref, "skip", "inherited")],
            stop_reason="permission: 追加レビューの認可が無い",
            seats=[kit.seat(head3, "alpha-model")],
        )
    )
    ended = loop.cycle_end(run_dir, github=env.github)
    assert ended["outcome"] == "stopped"
    assert loop.finish(run_dir)["result"]["outcome"] == "stopped"


# --- 排他の保持・中断と再開 ---------------------------------------------------------------------------------------


def test_unconfirmed_stop_holds_the_lock_until_operator_recovery(
    loop: Any, env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    real = loop.run_workflow

    def unconfirmed(*args: Any, **kwargs: Any) -> BatchResult:
        batch: BatchResult = real(*args, **kwargs)
        results = [
            item.model_copy(
                update={
                    "attempts": [attempt.model_copy(update={"stop_confirmed": False}) for attempt in item.attempts]
                }
            )
            for item in batch.results
        ]
        return batch.model_copy(update={"results": results})

    monkeypatch.setattr(loop, "run_workflow", unconfirmed)
    with pytest.raises(loop.LoopError) as review_error:
        loop.review(
            run_dir, github=env.github, adapter_loader=env.reviewers({"alpha": "success"}), tmp_root=env.tmp_root
        )
    assert review_error.value.code == 6
    resource = Path(read(run_dir / "run.json")["resources"][0]["path"])
    assert resource.exists()

    with pytest.raises(loop.LoopError) as held:
        loop.finish(run_dir, abort="environment: レビュアーの停止を確認できない", github=env.github)
    assert (held.value.code, held.value.stage) == (7, "resources")
    assert read(run_dir / "run.json")["state"] == "held"
    with pytest.raises(loop.LoopError) as refused:
        loop.recover(run_dir)
    assert refused.value.code == 7
    assert (env.review_dir / "loop/lock.json").exists()

    recovered = loop.recover(run_dir, operator_confirmed_stopped="ps で runner の子プロセスが無いことを確かめた")

    assert recovered["lock_released"] is True
    assert not resource.exists()
    assert registered_worktrees(env.parent) == [str(env.parent)]
    run = read(run_dir / "run.json")
    assert run["state"] == "ended"
    assert run["resources"][0]["state"] == "removed"
    assert "ps で" in run["resources"][0]["reason"]


def test_interrupted_review_without_result_is_not_rerun(loop: Any, env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    adapter = env.reviewers({"alpha": "success"})

    def interrupted(*args: Any, **kwargs: Any) -> BatchResult:
        Path(kwargs["output_dir"]).mkdir()
        raise KeyboardInterrupt

    real = loop.run_workflow
    monkeypatch.setattr(loop, "run_workflow", interrupted)
    with pytest.raises(KeyboardInterrupt):
        loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
    monkeypatch.setattr(loop, "run_workflow", real)

    with pytest.raises(loop.LoopError) as again:
        loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
    assert (again.value.code, again.value.stage) == (3, "interrupted_review")
    assert again.value.next_command[-3:] == ["recover", "--run", str(run_dir)]
    assert adapter.launched == []
    assert loop.status(run_dir=run_dir)["next"][-3:] == ["review", "--run", str(run_dir)]

    recovered = loop.recover(run_dir, operator_confirmed_stopped="中断した helper のプロセスが無いことを確かめた")
    assert recovered["lock_released"] is True
    run = read(run_dir / "run.json")
    assert run["state"] == "abandoned"
    # runner の結果が無いと秘密が残りうるファイルを判別できないので、ディレクトリは残して報告する
    resource = run["resources"][0]
    assert resource["state"] == "retained" and Path(resource["path"]).exists()
    assert resource["path"] in recovered["retained"]
    assert registered_worktrees(env.parent) == [str(env.parent)]


def test_resume_after_review_continues_from_status(loop: Any, env: Any, kit: Any) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    head = loop.cycle_begin(run_dir, github=env.github)["head"]
    loop.review(run_dir, github=env.github, adapter_loader=env.reviewers({"alpha": "success"}), tmp_root=env.tmp_root)

    # helper のプロセスが変わった後も、保存した状態だけから次の操作が分かる
    resumed = loop.status(run_dir=run_dir)
    assert resumed["next"][-3:] == ["cycle-end", "--run", str(run_dir)]
    env.gh.post_record(
        kit.round_record(1, head, "stopped", [], stop_reason="external: テスト", seats=[kit.seat(head, "alpha-model")])
    )
    assert loop.cycle_end(run_dir, github=env.github)["outcome"] == "stopped"
    assert loop.status(run_dir=run_dir)["next"][-3:] == ["finish", "--run", str(run_dir)]


def test_cycle_end_reads_the_roles_json_that_run_roles_writes(loop: Any, env: Any, kit: Any, tmp_path: Path) -> None:
    # run_roles.py は roles.json の batch を BatchResult.model_dump(mode="json") で書く（パスは文字列になる）。
    # 実機の確認で、strict な runner のモデルを Python モードで検証して読めなかった不具合の再現。
    started = env.start()
    run_dir = Path(started["run_dir"])
    head = env.gh.head()
    env.place_review(head)
    loop.cycle_begin(run_dir, github=env.github)
    attempt = Attempt(
        agent_id="alpha",
        state="success",
        identity=Identity(model="alpha-model", session_id="s-1"),
        exit_code=0,
        elapsed_seconds=3.0,
        stop_confirmed=True,
        work_dir=tmp_path / "implement/worktree",
        stdout_path=tmp_path / "implement/stdout.log",
        stderr_path=tmp_path / "implement/stderr.log",
        request_path=tmp_path / "implement/request.json",
        payload={"status": "completed"},
    )
    batch = BatchResult(
        run_id="run-implement",
        state="success",
        assignments={"implement": ["alpha"]},
        results=[
            Result(
                request_id="r-1",
                role="implement",
                requested_agent="alpha",
                actual_agent="alpha",
                state="success",
                attempts=[attempt],
            )
        ],
        outside_changes=[],
        elapsed_seconds=3.0,
        artifact_dir=tmp_path / "implement",
    )
    role_run = tmp_path / "implement"
    role_run.mkdir()
    (role_run / "roles.json").write_text(
        json.dumps(
            {"request": {}, "batch": batch.model_dump(mode="json"), "self_prompts": {}, "review_changes": None}
        ),
        encoding="utf-8",
    )
    pushed = env.push("修正")
    ref = f"alpha#H-1@{head[:12]}"
    env.gh.post_record(kit.round_record(1, head, "fixes_pushed", [kit.decision(ref, "fix", "new")], commit=pushed))

    loop.cycle_end(run_dir, github=env.github, role_runs=[role_run])

    recorded = read(run_dir / "cycle-1.json")["planning"]["role_runs"]
    assert recorded[0]["assignments"] == {"implement": ["alpha"]}
    assert recorded[0]["results"][0]["actual_agent"] == "alpha"
    assert recorded[0]["results"][0]["identity"]["session_id"] == "s-1"


# --- 最終レビューの指摘の再現 ---------------------------------------------------------------------------------------


def unconfirmed_batch(loop: Any, monkeypatch: pytest.MonkeyPatch, sensitive: Path | None = None) -> None:
    """runner が停止を確認できなかった結果の形（stop_confirmed=false と、秘密が残りうる receipt）を返させる。"""
    real = loop.run_workflow

    def unconfirmed(*args: Any, **kwargs: Any) -> BatchResult:
        batch: BatchResult = real(*args, **kwargs)
        results: list[Result] = []
        for item in batch.results:
            attempts: list[Attempt] = []
            for attempt in item.attempts:
                paths: list[Path] = (
                    [attempt.request_path.parent / "receipt.json"] if attempt.request_path is not None else []
                )
                if sensitive is not None:
                    paths.append(sensitive)
                for path in paths:
                    path.write_text("{}", encoding="utf-8")
                attempts.append(attempt.model_copy(update={"stop_confirmed": False, "sensitive_paths": paths}))
            results.append(item.model_copy(update={"attempts": attempts}))
        return batch.model_copy(update={"results": results})

    monkeypatch.setattr(loop, "run_workflow", unconfirmed)


def has_placeholder(argv: list[str] | None) -> bool:
    return argv is not None and any("<" in item and ">" in item for item in argv)


def test_next_commands_never_carry_placeholders_and_recover_rejects_them(
    loop: Any, env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    unconfirmed_batch(loop, monkeypatch)
    with pytest.raises(loop.LoopError) as failed:
        loop.review(
            run_dir, github=env.github, adapter_loader=env.reviewers({"alpha": "success"}), tmp_root=env.tmp_root
        )
    assert failed.value.code == 6
    assert not has_placeholder(failed.value.next_command)
    with pytest.raises(loop.LoopError) as held:
        loop.finish(run_dir, abort="environment: レビュアーの停止を確認できない", github=env.github)
    with pytest.raises(loop.LoopError) as refused:
        loop.recover(run_dir)
    assert not has_placeholder(held.value.next_command)
    assert not has_placeholder(refused.value.next_command)

    with pytest.raises(loop.LoopError) as placeholder:
        loop.recover(run_dir, operator_confirmed_stopped="<確かめた事実>")
    assert placeholder.value.code == 2
    with pytest.raises(loop.LoopError):
        loop.finish(run_dir, abort="external: <理由>")
    assert (env.review_dir / "loop/lock.json").exists()


def test_recover_keeps_files_that_may_hold_secrets(loop: Any, env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    unconfirmed_batch(loop, monkeypatch)
    with pytest.raises(loop.LoopError):
        loop.review(
            run_dir, github=env.github, adapter_loader=env.reviewers({"alpha": "success"}), tmp_root=env.tmp_root
        )
    receipts = list(Path(read(run_dir / "run.json")["resources"][0]["path"]).rglob("receipt.json"))
    assert receipts
    with pytest.raises(loop.LoopError):
        loop.finish(run_dir, abort="environment: レビュアーの停止を確認できない", github=env.github)

    recovered = loop.recover(run_dir, operator_confirmed_stopped="ps で runner の子プロセスが無いことを確かめた")

    assert all(path.exists() for path in receipts)
    assert set(map(str, receipts)) <= set(recovered["retained"])
    assert registered_worktrees(env.parent) == [str(env.parent)]
    assert recovered["lock_released"] is True


def test_failed_cleanup_paths_are_reported(loop: Any, env: Any, tmp_path: Path) -> None:
    result, head = accepted_result(env, tmp_path)
    attempt = result.attempts[-1]
    payload: dict[str, Any] = dict(cast(dict[str, Any], attempt.payload))
    payload.update(
        status="failed",
        cleanup="failed",
        reason="cleanup refused",
        retained_paths={"worktree": "/tmp/pr-review-900-x/worktree", "session_dir": "/tmp/pr-review-900-x"},
    )
    failed = result.model_copy(update={"attempts": [attempt.model_copy(update={"payload": payload})]})
    pr = loop.PrRef(
        repository="usaturn/create-reso-world", number=900, url="https://github.com/usaturn/create-reso-world/pull/900"
    )

    entry = loop.verify_reviewer(failed, pr=pr, head=head, review_dir=env.review_dir)

    assert entry.verdict == "rejected"
    assert sorted(entry.retained_paths) == ["/tmp/pr-review-900-x", "/tmp/pr-review-900-x/worktree"]


@pytest.mark.parametrize(
    "case",
    [
        "other_pr_document",
        "stale_body",
    ],
)
def test_verify_reviewer_rejects_artifacts_that_do_not_belong_to_this_head(
    loop: Any, env: Any, kit: Any, tmp_path: Path, case: str
) -> None:
    result, head = accepted_result(env, tmp_path)
    attempt = result.attempts[-1]
    payload: dict[str, Any] = dict(cast(dict[str, Any], attempt.payload))
    review, candidates = Path(payload["review_file"]), Path(payload["findings_file"])
    if case == "other_pr_document":
        document = read(candidates)
        document["pr"] = {"repository": "usaturn/create-reso-world", "number": 901}
        candidates.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    elif case == "symlink_inside_dir":
        target = env.review_dir / "real.md"
        review.rename(target)
        review.symlink_to(target)
    else:
        review.write_text(review.read_text(encoding="utf-8").replace(head[:12], "1" * 12), encoding="utf-8")
    pr = loop.PrRef(
        repository="usaturn/create-reso-world", number=900, url="https://github.com/usaturn/create-reso-world/pull/900"
    )

    entry = loop.verify_reviewer(result, pr=pr, head=head, review_dir=env.review_dir)

    assert entry.verdict == "rejected", case


@pytest.mark.parametrize(
    "entrypoint",
    [
        "cleanup",
    ],
)
@pytest.mark.parametrize(
    "locked",
    [
        True,
    ],
)
def test_missing_output_parent_does_not_hide_registered_worktrees(
    loop: Any, env: Any, tmp_path: Path, entrypoint: str, locked: bool
) -> None:
    from tools.agent_runner.workspace import create_worktree

    run_dir = Path(env.start()["run_dir"])
    run = loop.load_run(run_dir)
    parent = tmp_path / f"{loop.TMP_PREFIX}owned"
    worktree = create_worktree(env.parent, "HEAD", parent / "child\n日本語" / "worktree")
    if locked:
        subprocess.run(["git", "-C", str(env.parent), "worktree", "lock", str(worktree)], check=True)
    other = create_worktree(env.parent, "HEAD", tmp_path / "other-run" / "worktree")
    (other / "untracked").write_text("do not remove")
    resource = loop.Resource(path=str(parent), cycle=1, state="created")
    run.resources.append(resource)
    shutil.rmtree(parent)
    if entrypoint == "cleanup":
        assert loop.cleanup_output(env.parent, resource, None, force=True) == [str(worktree)]
    else:
        assert loop.audit_resources(run, []) == [str(parent)]
        # A retained resource still requires stop evidence on later calls.
        assert loop.audit_resources(run, []) == [str(parent)]
    assert resource.state == "retained"
    assert str(worktree) in [str(path) for path in loop._registered_worktrees(env.parent)]
    assert (other / "untracked").read_text() == "do not remove"
    assert not parent.exists()


@pytest.mark.parametrize(
    "entrypoint",
    [
        "audit",
    ],
)
@pytest.mark.parametrize(
    "failure",
    [
        "git_unavailable",
    ],
)
def test_missing_output_checks_fail_closed(loop: Any, env: Any, tmp_path: Path, entrypoint: str, failure: str) -> None:
    run = loop.load_run(Path(env.start()["run_dir"]))
    ancestor = tmp_path / "protected"
    ancestor.mkdir()
    parent = ancestor / f"{loop.TMP_PREFIX}owned"
    gitdir = env.parent / ".git"
    moved_gitdir = env.parent / "hidden-git"
    if failure == "inaccessible":
        parent.mkdir()
        ancestor.chmod(0)
    elif failure == "dangling":
        parent.symlink_to(tmp_path / "absent-target", target_is_directory=True)
    else:
        gitdir.rename(moved_gitdir)
        # .git が無いだけだと、tmp_path が別の作業ツリーの中にあるとき git が上の階層のリポジトリを見つけて
        # 成功する（#238）。git_output は GIT_* を除くので、GIT_CEILING_DIRECTORIES では止められない。
        # 存在しない gitdir を指す gitfile を置くと、git はこの階層で失敗する
        gitdir.write_text(f"gitdir: {tmp_path / 'absent-gitdir'}\n", encoding="utf-8")
    resource = loop.Resource(path=str(parent), cycle=1, state="created")
    run.resources.append(resource)
    try:
        result = (
            loop.cleanup_output(env.parent, resource, None, force=True)
            if entrypoint == "cleanup"
            else loop.audit_resources(run, [])
        )
        assert result == [str(parent)] and resource.state != "removed"
    finally:
        if failure == "inaccessible":
            ancestor.chmod(0o755)
        elif failure == "git_unavailable":
            gitdir.unlink()
            moved_gitdir.rename(gitdir)


@pytest.mark.parametrize(
    "entrypoint",
    [
        "cleanup",
    ],
)
def test_missing_parent_with_no_registration_is_removed(loop: Any, env: Any, tmp_path: Path, entrypoint: str) -> None:
    run = loop.load_run(Path(env.start()["run_dir"]))
    resource = loop.Resource(path=str(tmp_path / f"{loop.TMP_PREFIX}gone"), cycle=1, state="created")
    run.resources.append(resource)
    result = (
        loop.cleanup_output(env.parent, resource, None) if entrypoint == "cleanup" else loop.audit_resources(run, [])
    )
    assert result == [] and resource.state == "removed"


@pytest.mark.parametrize(("own", "removed"), [(True, True), (False, False)])
def test_cleanup_output_removes_only_its_own_prefix(loop: Any, tmp_path: Path, own: bool, removed: bool) -> None:
    """loop が作った名前（TMP_PREFIX）の出力ディレクトリだけを回収し、それ以外の名前のディレクトリは残す。"""
    prefix = loop.TMP_PREFIX if own else "other-"
    tool_root = tmp_path / "tool"
    subprocess.run(["git", "init", "-q", str(tool_root)], check=True)
    parent = tmp_path / f"{prefix}abc123"
    (parent / "cycle-1-review").mkdir(parents=True)
    resource = loop.Resource(path=str(parent), cycle=1, state="created")
    batch = BatchResult.model_validate(
        {
            "run_id": "run-1",
            "state": "success",
            "assignments": {},
            "results": [],
            "outside_changes": [],
            "elapsed_seconds": 0,
            "artifact_dir": parent / "cycle-1-review",
        }
    )
    retained = loop.cleanup_output(tool_root, resource, batch, force=True)
    assert parent.exists() is not removed
    assert (retained == []) is removed
    assert resource.state == ("removed" if removed else "retained")


@pytest.mark.parametrize(("write", "state"), [(False, "removed"), (True, "retained")])
def test_cleanup_without_force_keeps_only_a_written_worktree(
    loop: Any, env: Any, tmp_path: Path, write: bool, state: str
) -> None:
    """停止を確認した回収は force なしで worktree を外す。レビュアーが worktree に書いていたら残す。"""
    from tools.agent_runner.workspace import create_worktree

    parent = tmp_path / f"{loop.TMP_PREFIX}written"
    worktree = create_worktree(env.parent, "HEAD", parent / "cycle-1-review" / "worktree")
    if write:
        (worktree / "notes.md").write_text("reviewer\n", encoding="utf-8")
    batch = BatchResult.model_validate(
        {
            "run_id": "run-1",
            "state": "success",
            "assignments": {},
            "results": [],
            "outside_changes": [],
            "elapsed_seconds": 0,
            "artifact_dir": parent / "cycle-1-review",
        }
    )
    resource = loop.Resource(path=str(parent), cycle=1, state="created")

    retained = loop.cleanup_output(env.parent, resource, batch)

    assert resource.state == state
    if state == "removed":
        assert retained == [] and not parent.exists()
        assert str(worktree) not in registered_worktrees(env.parent)
    else:
        assert retained == [str(worktree)]
        assert (worktree / "notes.md").is_file()


# --- 未実施レビュアーの再実行 -------------------------------------------------------------------------------------


def started_cycle(loop: Any, env: Any) -> Path:
    run_dir = Path(env.start()["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    return run_dir


def test_reviewer_rejected_after_runner_success_is_rerun_once(loop: Any, env: Any) -> None:
    run_dir = started_cycle(loop, env)
    adapter = env.reviewers({"alpha": ["failed", "success"], "beta": "success"})

    first = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert first["rerun"] == {"agents": ["alpha"]}
    assert first["next"][-3:] == ["review", "--run", str(run_dir)]
    assert [item["agent"] for item in first["accepted"]] == ["beta"]
    assert read(run_dir / "cycle-1.json")["state"] == "reviewing"
    assert loop.status(run_dir=run_dir)["next"][-3:] == ["review", "--run", str(run_dir)]

    second = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert sorted(adapter.launched) == ["alpha", "alpha", "beta"]
    assert sorted(item["agent"] for item in second["accepted"]) == ["alpha", "beta"]
    assert second["next"][-3:] == ["cycle-end", "--run", str(run_dir)]
    cycle = loop.load_cycles(run_dir)[-1]
    assert cycle.state == "planning"
    assert [entry.verdict for entry in cycle.review.reviewers] == ["accepted", "accepted"]
    replaced = cycle.review.rerun.replaced
    assert [(entry.actual_agent, entry.rejected_stage) for entry in replaced] == [("alpha", "payload")]
    kept = Path(replaced[0].request_file)
    assert kept.parent == run_dir / "cycle-1" / "requests"
    assert loop.sha256_file(kept) == replaced[0].request_sha256
    assert Request.model_validate_json(kept.read_text(encoding="utf-8")).agent_id == "alpha"
    assert (run_dir / "cycle-1" / "rerun-result.json").is_file()
    run = read(run_dir / "run.json")
    assert [resource["state"] for resource in run["resources"]] == ["removed", "removed"]
    assert registered_worktrees(env.parent) == [str(env.parent)]


def test_rerun_is_not_started_while_another_attempt_is_unconfirmed(
    loop: Any, env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 再実行は依存する仕事なので、1 回目の batch の全試行の停止を確かめてからでないと始めない
    run_dir = started_cycle(loop, env)
    real = loop.run_workflow

    def alpha_unconfirmed(*args: Any, **kwargs: Any) -> BatchResult:
        batch: BatchResult = real(*args, **kwargs)
        results = [
            item.model_copy(
                update={
                    "attempts": [attempt.model_copy(update={"stop_confirmed": False}) for attempt in item.attempts]
                }
            )
            if item.actual_agent == "alpha"
            else item
            for item in batch.results
        ]
        return batch.model_copy(update={"results": results})

    monkeypatch.setattr(loop, "run_workflow", alpha_unconfirmed)
    adapter = env.reviewers({"alpha": "success", "beta": ["failed", "success"]})

    with pytest.raises(loop.LoopError) as error:
        loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert (error.value.code, error.value.stage) == (6, "review")
    assert loop.load_cycles(run_dir)[-1].review.rerun is None
    assert sorted(adapter.launched) == ["alpha", "beta"]
    assert Path(read(run_dir / "run.json")["resources"][0]["path"]).exists()


def test_request_is_kept_only_from_a_regular_file(loop: Any, env: Any, tmp_path: Path) -> None:
    result, head = accepted_result(env, tmp_path)
    attempt = result.attempts[-1]
    payload = {**cast(dict[str, Any], attempt.payload), "status": "failed"}
    target = tmp_path / "elsewhere.json"
    target.write_text(cast(Path, attempt.request_path).read_text(encoding="utf-8"), encoding="utf-8")
    link = tmp_path / "linked-request.json"
    link.symlink_to(target)
    pr = loop.PrRef(
        repository="usaturn/create-reso-world", number=900, url="https://github.com/usaturn/create-reso-world/pull/900"
    )
    kept = tmp_path / "kept"
    # 停止を確かめられない試行のファイルは、生きた書き手が差し替えうるので読まない
    for request_path, stopped, expected in (
        (link, True, False),
        (tmp_path / "missing.json", True, False),
        (attempt.request_path, False, False),
        (attempt.request_path, True, True),
    ):
        update = {"payload": payload, "request_path": request_path, "stop_confirmed": stopped}
        failed = result.model_copy(update={"attempts": [attempt.model_copy(update=update)]})
        entry = loop.verify_reviewer(failed, pr=pr, head=head, review_dir=env.review_dir)
        loop.keep_rejected_request(failed, entry, kept)
        assert (entry.request_file is not None) is expected
    assert sorted(path.name for path in kept.iterdir()) == ["request-1.json"]


# --- 移植先の書き込みの例外 -------------------------------------------------------------


def test_write_exceptions_name_the_target_checkout_git(loop: Any, env: Any, kit: Any) -> None:
    """レビュアーの helper は、PR の Git 操作の対象の checkout の Git に review の worktree・ref を書く。

    create-reso-world の PR は親、resoloop の PR は external/resoloop なので、例外の一覧もそこを指す。
    親の Git には保存のロックだけを書く（Spec D-7）。
    """
    run = loop.load_run(Path(env.start()["run_dir"]))
    parent_git = env.parent / ".git"

    own = loop.review_write_exceptions(run)

    assert any(line.startswith(f"{parent_git}: ") for line in own)
    assert own[-1].startswith("files that the agent runtime")

    fork = env.parent / "external" / "resoloop"
    subprocess.run(["git", "init", "-q", "-b", "main", str(fork)], check=True)
    kit.git(fork, "remote", "add", "origin", "https://github.com/usaturn/resoloop.git")
    kit.git(fork, "remote", "add", "upstream", "https://github.com/orange3134/resoloop.git")
    kit.git(fork, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q", "--allow-empty", "-m", "fork")
    pr = loop.PrRef(repository="usaturn/resoloop", number=900, url="https://github.com/usaturn/resoloop/pull/900")

    lines = loop.review_write_exceptions(run.model_copy(update={"pr": pr}))

    assert any(line.startswith(f"{fork / '.git'}: ") for line in lines)
    assert any(line.startswith(f"{parent_git / 'pr-review-save.lock'}: ") for line in lines)
    assert not any(line.startswith(f"{parent_git}: ") for line in lines)


# --- 停止を確認できない間の保持 -----------------------------------------------------------------------------------

STOPPED_FACT = "ps で runner・レビュアー・後処理の子プロセスが無いことを確かめた"


def tree(root: Path) -> list[tuple[str, bytes | str | None]] | None:
    """ディレクトリの中の全項目（相対パスと、ファイルのバイト列・symlink の参照先）。無ければ None。"""
    if not root.exists():
        return None
    entries: list[tuple[str, bytes | str | None]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            value: bytes | str | None = os.readlink(path)
        elif path.is_file():
            value = path.read_bytes()
        else:
            value = None
        entries.append((str(path.relative_to(root)), value))
    return entries


def held_state(env: Any, run_dir: Path) -> dict[str, Any]:
    """回収とロックの解放で変わる状態の全体。finish --abort が変える run の state と result は除く。"""
    run = read(run_dir / "run.json")
    return {
        "outputs": {resource["path"]: tree(Path(resource["path"])) for resource in run["resources"]},
        "lock": (env.review_dir / "loop/lock.json").read_bytes(),
        "run": {key: value for key, value in run.items() if key not in ("state", "result")},
        "worktrees": registered_worktrees(env.parent),
    }


def live_after_run(loop: Any, monkeypatch: pytest.MonkeyPatch, case: str) -> list[subprocess.Popen[bytes]]:
    """出力ディレクトリを cwd にした子プロセスを残したまま、停止を確認できずに終わる（または中断する）後処理。"""
    children: list[subprocess.Popen[bytes]] = []

    def after_run(commands: list[list[str]], *, result_path: Path, cwd: Path, cancel: Any) -> list[dict[str, Any]]:
        output = result_path.parent
        stdout = output / "after-run-0.stdout.log"
        with stdout.open("wb") as stream:
            children.append(
                subprocess.Popen(
                    [sys.executable, "-c", "import time; time.sleep(120)"],
                    cwd=output,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            )
        if case == "interrupted":
            raise KeyboardInterrupt
        return [
            {
                "index": 0,
                "state": "timed_out",
                "exit_code": None,
                "stop_confirmed": False,
                "stdout_path": str(stdout),
                "stderr_path": str(output / "after-run-0.stderr.log"),
            }
        ]

    monkeypatch.setattr(loop, "run_after_run", after_run)
    return children


def stop(children: list[subprocess.Popen[bytes]]) -> None:
    for child in children:
        child.terminate()
        child.wait()


@pytest.mark.parametrize(
    "entry",
    [
        "recover",
    ],
)
@pytest.mark.parametrize(
    "case",
    [
        "unconfirmed",
    ],
)
def test_unconfirmed_after_run_keeps_outputs_and_lock_until_the_operator_confirms(
    loop: Any, env: Any, monkeypatch: pytest.MonkeyPatch, case: str, entry: str
) -> None:
    # 後処理の停止を確かめられない間は、runner の試行が停止済みでも、出力を消さずロックを外さない
    run_dir = started_cycle(loop, env)
    children = live_after_run(loop, monkeypatch, case)
    adapter = env.reviewers({"alpha": "success", "beta": "success"})
    try:
        if case == "unconfirmed":
            with pytest.raises(loop.LoopError) as error:
                loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
            assert (error.value.code, error.value.stage) == (7, "after_run")
            assert error.value.next_command[-3:] == ["recover", "--run", str(run_dir)]
            assert error.value.requires_input == loop.CONFIRM_STOPPED
            assert read(run_dir / "run.json")["state"] == "held"
            assert loop.status(run_dir=run_dir)["next"][-3:] == ["recover", "--run", str(run_dir)]
        else:
            # 後処理の途中で helper が止まった（after_run_started だけが残る）。review を呼び直さずに回収を試みる
            with pytest.raises(KeyboardInterrupt):
                loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
        assert len(children) == 1
        before = held_state(env, run_dir)

        with pytest.raises(loop.LoopError) as refused:
            if entry == "recover":
                loop.recover(run_dir)
            else:
                loop.finish(run_dir, abort="environment: 後処理の停止を確認できない", github=env.github)

        assert (refused.value.code, refused.value.stage) == (7, "resources")
        assert held_state(env, run_dir) == before
        assert children[0].poll() is None

        stop(children)
        recovered = loop.recover(run_dir, operator_confirmed_stopped=STOPPED_FACT)

        assert recovered["lock_released"] is True
        assert not (env.review_dir / "loop/lock.json").exists()
        assert [resource["state"] for resource in read(run_dir / "run.json")["resources"]] == ["removed"]
    finally:
        stop(children)


def test_review_after_an_interrupted_after_run_holds_the_run(
    loop: Any, env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = started_cycle(loop, env)
    children = live_after_run(loop, monkeypatch, "interrupted")
    adapter = env.reviewers({"alpha": "success", "beta": "success"})
    try:
        with pytest.raises(KeyboardInterrupt):
            loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
        launched = list(adapter.launched)

        with pytest.raises(loop.LoopError) as error:
            loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

        assert (error.value.code, error.value.stage) == (7, "after_run")
        assert error.value.next_command[-3:] == ["recover", "--run", str(run_dir)]
        assert error.value.requires_input == loop.CONFIRM_STOPPED
        assert read(run_dir / "run.json")["state"] == "held"
        assert loop.status(run_dir=run_dir)["next"][-3:] == ["recover", "--run", str(run_dir)]
        assert adapter.launched == launched and len(children) == 1
    finally:
        stop(children)


@pytest.mark.parametrize(
    ("batch_number", "agent", "behaviors"),
    [
        (1, "alpha", {"alpha": "success", "beta": "success"}),
        (2, "beta", {"alpha": "success", "beta": ["failed", "success"]}),
    ],
    ids=["first-alpha", "rerun-beta"],
)
def test_unconfirmed_attempt_holds_the_run_instead_of_planning(
    loop: Any,
    env: Any,
    monkeypatch: pytest.MonkeyPatch,
    batch_number: int,
    agent: str,
    behaviors: dict[str, Any],
) -> None:
    # 計画は依存する作業なので、受け付けたレビュアーがいても、停止を確かめられない試行があれば始めない
    run_dir = started_cycle(loop, env)
    real = loop.run_workflow
    batches: list[str] = []

    def unconfirmed_once(*args: Any, **kwargs: Any) -> BatchResult:
        batch: BatchResult = real(*args, **kwargs)
        batches.append(batch.run_id)
        if len(batches) != batch_number:
            return batch
        results = [
            item.model_copy(
                update={
                    "attempts": [attempt.model_copy(update={"stop_confirmed": False}) for attempt in item.attempts]
                }
            )
            if item.actual_agent == agent
            else item
            for item in batch.results
        ]
        return batch.model_copy(update={"results": results})

    monkeypatch.setattr(loop, "run_workflow", unconfirmed_once)
    adapter = env.reviewers(behaviors)
    if batch_number == 2:
        pending = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
        assert pending["rerun"] == {"agents": ["beta"]}

    with pytest.raises(loop.LoopError) as error:
        loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert (error.value.code, error.value.stage) == (7, "resources")
    assert error.value.next_command[-3:] == ["recover", "--run", str(run_dir)]
    assert error.value.requires_input == loop.CONFIRM_STOPPED
    assert agent in error.value.reason
    assert read(run_dir / "cycle-1.json")["state"] == "reviewing"
    assert read(run_dir / "run.json")["state"] == "held"
    output = Path(read(run_dir / "run.json")["resources"][-1]["path"])
    assert output.exists()
    assert (env.review_dir / "loop/lock.json").exists()
    assert loop.status(run_dir=run_dir)["next"][-3:] == ["recover", "--run", str(run_dir)]

    launched = list(adapter.launched)
    with pytest.raises(loop.LoopError) as again:
        loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
    assert (again.value.code, again.value.stage) == (7, "resources")
    assert adapter.launched == launched
    with pytest.raises(loop.LoopError) as begin:
        loop.cycle_begin(run_dir, github=env.github)
    assert (begin.value.code, begin.value.stage) == (3, "state")

    before = held_state(env, run_dir)
    with pytest.raises(loop.LoopError) as refused:
        loop.recover(run_dir)
    assert refused.value.code == 7
    assert held_state(env, run_dir) == before

    recovered = loop.recover(run_dir, operator_confirmed_stopped=STOPPED_FACT)

    assert recovered["lock_released"] is True
    assert read(run_dir / "run.json")["state"] == "abandoned"
    assert not (env.review_dir / "loop/lock.json").exists()
