"""ロック・サイクルの状態・判断の記録の照合・結果ごとの終わり方を、偽の gh と bare remote で確かめる。

計画担当（review-fix-planning）の代わりに、テストが記録の投稿・push・マージを行う。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest


def reuse_or_run(loop: Any, env: Any) -> dict[str, Any]:
    """現在の HEAD の成果 2 件を置いてから cycle-begin を呼び、レビュアーを起動せずに計画の段階へ進める。

    レビュアーの起動は test_loop_review で確かめる。
    """
    env.place_review(env.gh.head())
    begun: dict[str, Any] = loop.cycle_begin(Path(env.run_dirs[-1]), github=env.github)
    assert begun["review"]["mode"] == "reuse"
    return begun


def test_second_start_is_refused_while_the_first_run_holds_the_lock(loop: Any, env: Any) -> None:
    first = env.start()

    with pytest.raises(loop.LoopError) as error:
        env.start()

    assert error.value.code == 3
    assert error.value.stage == "lock_held"
    assert first["run_id"] in error.value.reason
    lock = json.loads((env.review_dir / "loop/lock.json").read_text(encoding="utf-8"))
    assert lock["run_id"] == first["run_id"]


def test_start_refuses_a_closed_pr(loop: Any, env: Any) -> None:
    env.gh.state = "closed"

    with pytest.raises(loop.LoopError) as error:
        env.start()

    assert (error.value.code, error.value.stage) == (4, "pr_not_open")
    assert not (env.review_dir / "loop/lock.json").exists()


def test_start_rejects_an_unknown_role_and_inspect_self(loop: Any, env: Any) -> None:
    for assign in (["plan=claude-opus"], ["inspect=self"], ["implement=claude-opus,codex"]):
        with pytest.raises(loop.LoopError) as error:
            env.start(assign=assign)
        assert error.value.code == 2, assign
    assert not (env.review_dir / "loop/lock.json").exists()


# テスト用の雛形（conftest の TEST_TEMPLATE）に codex の担当 echo を足す個人設定
CODEX_AGENT = """
[agents.echo]
runtime = "codex"
command = ["fake-echo"]
model = "echo-model"
"""
CODEX_REJECTED = "codex runtime agent"
CONFIG_REJECTED = "ConfigError: invalid_config"


def write_personal(root: Path, extra: str = "") -> Path:
    path = root / "personal.toml"
    path.write_text(CODEX_AGENT + extra, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("assign", "extra", "expected"),
    [
        pytest.param(["self-review=echo"], "", CODEX_REJECTED, id="assign-self-review-codex"),
        pytest.param(["fix-check=echo"], "", CODEX_REJECTED, id="assign-fix-check-codex"),
        pytest.param(
            [],
            '[workflows.fix.assignments.self-review]\nfallback = ["echo"]\n',
            CODEX_REJECTED,
            id="fallback-self-review-codex",
        ),
        pytest.param(
            [],
            '[workflows.fix.assignments.fix-check]\nfallback = ["echo"]\n',
            CODEX_REJECTED,
            id="fallback-fix-check-codex",
        ),
        pytest.param(
            [],
            '[workflows.fix.assignments.self-review]\nagents = ["alpha", "beta"]\n',
            CONFIG_REJECTED,
            id="self-review-two-primaries",
        ),
        pytest.param([], "[roles.self-review]\nwrites = true\n", CONFIG_REJECTED, id="self-review-writes"),
    ],
)
def test_start_rejects_fix_assignments_that_run_roles_refuses(
    loop: Any,
    env: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    assign: list[str],
    extra: str,
    expected: str,
) -> None:
    """run_roles が設定だけで拒否する割り当ては、レビューや implement の後ではなく start で止める（#675）。"""
    personal = write_personal(tmp_path, extra)

    with pytest.raises(loop.LoopError) as error:
        env.start(assign=assign, config=personal)

    assert (error.value.code, error.value.stage) == (2, "config")
    assert expected in error.value.reason
    assert env.gh.calls == []
    assert not (env.review_dir / "loop").exists()
    # 同じ設定を run_roles に渡したときの理由と同じ文・分類で止まる
    request = tmp_path / "request.json"
    request.write_text("{}", encoding="utf-8")
    arguments = ["--phase", "self-review", "--request", str(request), "--output-dir", str(tmp_path / "roles")]
    arguments += ["--template", str(env.template), "--config", str(personal)]
    arguments += [option for entry in assign for option in ("--assign", entry)]
    capsys.readouterr()
    assert loop.run_roles.main(arguments) == 2
    reported = re.search(r"failed \((.*)\); no verification success implied", capsys.readouterr().err)
    assert reported is not None
    assert reported.group(1) in error.value.reason


@pytest.mark.parametrize(
    ("assign", "expected"),
    [
        pytest.param([], {"implement": ["alpha"], "self-review": ["self"], "fix-check": ["self"]}, id="default"),
        pytest.param(
            ["self-review=alpha", "fix-check=beta"],
            {"implement": ["alpha"], "self-review": ["alpha"], "fix-check": ["beta"]},
            id="external-review-roles",
        ),
        pytest.param(
            ["implement=echo"],
            {"implement": ["echo"], "self-review": ["self"], "fix-check": ["self"]},
            id="implement-codex",
        ),
    ],
)
def test_start_accepts_fix_assignments_that_run_roles_accepts(
    env: Any, tmp_path: Path, assign: list[str], expected: dict[str, list[str]]
) -> None:
    """codex を拒否するのは inspect・self-review・fix-check だけ。implement（workspace-write）には使える（#731）。
    """
    started = env.start(assign=assign, config=write_personal(tmp_path))

    assert started["status"] == "ok"
    assert {role: value["agents"] for role, value in started["assignments"]["fix"].items()} == expected


@pytest.mark.parametrize(
    ("assign", "extra"),
    [
        pytest.param(["inspect=alpha,echo"], "", id="assign-inspect"),
        pytest.param([], '[workflows.review.assignments.inspect]\nfallback = ["echo"]\n', id="fallback-inspect"),
        pytest.param(
            ["inspect=alpha,codex-mini"],
            '[agents.codex-mini]\nruntime = "codex"\ncommand = ["fake-mini"]\nmodel = "mini-model"\n',
            id="other-name",
        ),
    ],
)
def test_start_rejects_a_codex_reviewer(loop: Any, env: Any, tmp_path: Path, assign: list[str], extra: str) -> None:
    """codex のレビュアーは read-only の sandbox で pr-review の helper を起動できない。run を作る前に止める（#731）。

    判定は runtime で行い、agent の名前は見ない。fallback も起動されうるので見る。
    """
    with pytest.raises(loop.LoopError) as error:
        env.start(assign=assign, config=write_personal(tmp_path, extra))

    assert (error.value.code, error.value.stage) == (2, "config")
    assert CODEX_REJECTED in error.value.reason
    assert "inspect" in error.value.reason
    assert env.gh.calls == []
    assert not (env.review_dir / "loop").exists()


def test_cli_start_reports_a_refused_fix_assignment(
    loop: Any, env: Any, kit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(loop, "GitHub", lambda: env.github)
    monkeypatch.setattr(loop.target, "default_parent_root", lambda: env.parent)
    arguments = ["start", f"#{kit.number}", "--controller-model", "test-planner", "--controller-runtime", "pi"]
    arguments += ["--assign", "self-review=echo", "--template", str(env.template)]
    arguments += ["--config", str(write_personal(tmp_path))]

    assert loop.main(arguments) == 2

    output = json.loads(capsys.readouterr().out)
    assert (output["status"], output["stage"]) == ("error", "config")
    assert CODEX_REJECTED in output["reason"]
    assert env.gh.calls == []
    assert not (env.review_dir / "loop").exists()


@pytest.mark.parametrize("entrypoint", ["api", "cli"])
def test_start_records_options_and_effective_assignments(
    loop: Any,
    env: Any,
    kit: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    entrypoint: str,
) -> None:
    # CLI でも保存と計画への引き渡しは実 helper を使い、GitHub と親 checkout の探索だけ隔離する。
    if entrypoint == "api":
        started = env.start(assign=["inspect=beta,alpha", "implement=beta"], max_cycles=2)
    else:
        monkeypatch.setattr(loop, "GitHub", lambda: env.github)
        monkeypatch.setattr(loop.target, "default_parent_root", lambda: env.parent)
        args = [
            "start",
            f"#{kit.number}",
            "--controller-model",
            "test-planner",
            "--controller-runtime",
            "pi",
            "--max-cycles",
            "2",
            "--assign",
            "inspect=beta,alpha",
            "--assign",
            "implement=beta",
            "--template",
            str(env.template),
        ]
        assert loop.main(args) == 0
        started = json.loads(capsys.readouterr().out)
        env.run_dirs.append(Path(started["run_dir"]))

    run = json.loads((Path(started["run_dir"]) / "run.json").read_text(encoding="utf-8"))
    assert run["schema"] == "pr-review-fix-loop/v1"
    assert run["options"]["max_cycles"] == 2
    # 計画への案内は、run に保存した設定から作る（司令塔に組み立て直させない）
    planning = reuse_or_run(loop, env)["planning"]
    assert planning["review_dir"] == str(env.review_dir)
    assert planning["run_roles_options"] == ["--template", str(env.template), "--assign", "implement=beta"]
    assert run["assignments"]["review"]["inspect"]["agents"] == ["beta", "alpha"]
    assert run["assignments"]["fix"]["implement"]["agents"] == ["beta"]
    if entrypoint == "api":
        assert run["tool_commit"] == kit.git(env.parent, "rev-parse", "HEAD")
    assert started["next"][-3:] == ["cycle-begin", "--run", started["run_dir"]]


def test_out_of_order_calls_are_refused(loop: Any, env: Any) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])

    with pytest.raises(loop.LoopError) as error:
        loop.cycle_end(run_dir, github=env.github)

    assert (error.value.code, error.value.stage) == (3, "state")


def test_cycle_end_before_the_record_is_posted_keeps_the_cycle_open(loop: Any, env: Any, kit: Any) -> None:
    # 関連検証が落ちて計画が修正を続けている間は、記録が無い。loop はサイクルを終えずに待つ。
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    run_dir = env.run_dirs[-1]

    with pytest.raises(loop.LoopError) as error:
        loop.cycle_end(run_dir, github=env.github)
    assert (error.value.code, error.value.stage) == (4, "record_missing")
    cycle = json.loads((run_dir / "cycle-1.json").read_text(encoding="utf-8"))
    assert cycle["state"] == "planning"

    pushed = env.push("修正")
    ref = f"alpha#H-1@{head[:12]}"
    env.gh.post_record(kit.round_record(1, head, "fixes_pushed", [kit.decision(ref, "fix", "new")], commit=pushed))
    ended = loop.cycle_end(run_dir, github=env.github)

    assert ended["outcome"] == "fixes_pushed"
    assert ended["next"][-3:] == ["cycle-begin", "--run", str(run_dir)]


def test_record_for_another_head_is_not_taken_as_this_cycle(loop: Any, env: Any, kit: Any) -> None:
    env.start()
    old_head = env.gh.head()
    env.gh.post_record(kit.round_record(1, old_head, "stopped", [], stop_reason="external: 古い記録", seats=[]))
    env.push("別の commit")
    reuse_or_run(loop, env)

    with pytest.raises(loop.LoopError) as error:
        loop.cycle_end(env.run_dirs[-1], github=env.github)

    assert error.value.stage == "record_missing"


def test_fixes_pushed_requires_the_pr_head_to_be_the_pushed_commit(loop: Any, env: Any, kit: Any) -> None:
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    pushed = env.push("修正")
    env.push("さらに別の push")
    ref = f"alpha#H-1@{head[:12]}"
    env.gh.post_record(kit.round_record(1, head, "fixes_pushed", [kit.decision(ref, "fix", "new")], commit=pushed))

    with pytest.raises(loop.LoopError) as error:
        loop.cycle_end(env.run_dirs[-1], github=env.github)

    assert (error.value.code, error.value.stage) == (4, "pushed_head_mismatch")


def test_inherited_skip_changed_without_evidence_is_rejected(loop: Any, env: Any, kit: Any) -> None:
    env.start()
    first = env.gh.head()
    reuse_or_run(loop, env)
    skip_ref = f"alpha#M-1@{first[:12]}"
    fix_ref = f"alpha#H-1@{first[:12]}"
    pushed = env.push("修正")
    env.gh.post_record(
        kit.round_record(
            1,
            first,
            "fixes_pushed",
            [kit.decision(skip_ref, "skip", "new"), kit.decision(fix_ref, "fix", "new")],
            commit=pushed,
        )
    )
    loop.cycle_end(env.run_dirs[-1], github=env.github)
    reuse_or_run(loop, env)
    # 引き継いだ skip の状態を変えた記録（inherited のまま fix）は、前の状態との照合で拒否される
    env.gh.post_record(
        kit.round_record(
            2,
            pushed,
            "stopped",
            [
                kit.decision(skip_ref, "fix", "inherited"),
                kit.decision(fix_ref, "resolved", "changed", previous_state="fix"),
            ],
            stop_reason="permission: テスト",
            seats=[kit.seat(pushed)],
        )
    )

    with pytest.raises(loop.LoopError) as error:
        loop.cycle_end(env.run_dirs[-1], github=env.github)

    assert (error.value.code, error.value.stage) == (4, "record_inconsistent")


def test_no_fix_needed_needs_a_merged_finalize_result_at_the_same_head(
    loop: Any, env: Any, kit: Any, tmp_path: Path
) -> None:
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    env.gh.post_record(kit.round_record(1, head, "no_fix_needed", []))

    with pytest.raises(loop.LoopError) as missing:
        loop.cycle_end(env.run_dirs[-1], github=env.github)
    assert (missing.value.code, missing.value.stage) == (2, "arguments")

    result = kit.finalize_result(tmp_path / "final.json", "no_fix_needed", merged=True)
    with pytest.raises(loop.LoopError) as unmerged:
        loop.cycle_end(env.run_dirs[-1], github=env.github, finalize_result=result)
    assert (unmerged.value.code, unmerged.value.stage) == (4, "merge_mismatch")

    env.gh.merge()
    ended = loop.cycle_end(env.run_dirs[-1], github=env.github, finalize_result=result)
    assert ended["outcome"] == "no_fix_needed"
    run = json.loads((env.run_dirs[-1] / "run.json").read_text(encoding="utf-8"))
    assert run["result"]["merged"] is True
    assert run["result"]["ended_by"] == "outcome"


def test_finalize_stopped_ends_the_run_as_stopped_and_not_merged(
    loop: Any, env: Any, kit: Any, tmp_path: Path
) -> None:
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    env.gh.post_record(kit.round_record(1, head, "no_fix_needed", []))
    result = kit.finalize_result(
        tmp_path / "final.json", "stopped", merged=False, stop_reason="external: mergeable が UNKNOWN"
    )

    ended = loop.cycle_end(env.run_dirs[-1], github=env.github, finalize_result=result)

    assert ended["outcome"] == "stopped"
    run = json.loads((env.run_dirs[-1] / "run.json").read_text(encoding="utf-8"))
    assert run["result"] == {
        "outcome": "stopped",
        "ended_by": "outcome",
        "stop_reason": "external: mergeable が UNKNOWN",
        "merged": False,
        "cycles": 1,
    }
    cycle = json.loads((env.run_dirs[-1] / "cycle-1.json").read_text(encoding="utf-8"))
    assert cycle["planning"]["finalize"]["result"]["outcome"] == "stopped"


@pytest.mark.parametrize(
    ("reported", "another_head"),
    # true は、finalize が別の head のマージを観測して止まった結果（Review Focus 1 をループの最後まで通す経路）。
    # true_merge_parent は、finalize がマージの後の merge commit の照合で止まった結果（#206）。PR は検証した HEAD でマージ済み
    [(False, True), (None, False), (True, True), (True, False)],
    ids=["false", "null", "true_another_head", "true_merge_parent"],
)
def test_finalize_stopped_keeps_the_real_merge(
    loop: Any, env: Any, kit: Any, tmp_path: Path, reported: bool | None, another_head: bool
) -> None:
    """finalize が止まり、未マージ（false）か未確認（null）と返したが、PR は実際にはマージ済み（#207）。

    cycle-end が読んだ実際の状態を保存し、finalize の値で上書きしない。別の head のマージは停止のまま。
    検証した HEAD のマージでも、finalize が止まれば no_fix_needed にせず、finalize の結果を残す（#206）。
    """
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    run_dir = env.run_dirs[-1]
    env.gh.post_record(kit.round_record(1, head, "no_fix_needed", []))
    if another_head:
        env.push("検証していない commit")
    env.gh.merge()
    reason = "external: PRが検証済みHEADと別のHEADでマージされた" if another_head else "external: 確認に失敗した"
    merge_parent = None
    if reported is True and not another_head:
        reason = "external: merge commitの最初の親が検証したbaseと違う"
        merge_parent = {"verified": "a" * 40, "merge_commit": "c" * 40, "first_parent": "b" * 40}
    result = kit.finalize_result(
        tmp_path / "final.json", "stopped", merged=reported, stop_reason=reason, merge_parent=merge_parent
    )

    ended = loop.cycle_end(run_dir, github=env.github, finalize_result=result)

    assert (ended["outcome"], ended["merged"], ended["stop_reason"]) == ("stopped", True, reason)
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert (run["result"]["outcome"], run["result"]["merged"], run["result"]["stop_reason"]) == (
        "stopped",
        True,
        reason,
    )
    cycle = json.loads((run_dir / "cycle-1.json").read_text(encoding="utf-8"))
    assert cycle["planning"]["merged"] is True
    assert cycle["planning"]["finalize"]["result"]["merged"] is reported
    assert cycle["planning"]["finalize"]["result"].get("merge_parent") == merge_parent


def test_finalize_merged_but_pr_not_merged_is_a_mismatch_when_stopped(
    loop: Any, env: Any, kit: Any, tmp_path: Path
) -> None:
    """マージは戻らない。finalize がマージ済みと返したのに PR が未マージなら、どちらかの読み取りが誤っている。"""
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    run_dir = env.run_dirs[-1]
    env.gh.post_record(kit.round_record(1, head, "no_fix_needed", []))
    result = kit.finalize_result(
        tmp_path / "final.json", "stopped", merged=True, stop_reason="external: 関連IssueがCLOSEDになったことを確認できない"
    )

    with pytest.raises(loop.LoopError) as error:
        loop.cycle_end(run_dir, github=env.github, finalize_result=result)

    assert (error.value.code, error.value.stage) == (4, "merge_mismatch")
    assert json.loads((run_dir / "cycle-1.json").read_text(encoding="utf-8"))["state"] == "planning"


def test_recorded_stop_keeps_a_manual_merge(loop: Any, env: Any, kit: Any) -> None:
    """結論 3（finalize を呼ばない stopped の記録）の間に、PR が手でマージされた。"""
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    env.gh.post_record(kit.round_record(1, head, "stopped", [], stop_reason="external: テスト", seats=[]))
    env.gh.merge()

    ended = loop.cycle_end(env.run_dirs[-1], github=env.github)

    assert (ended["outcome"], ended["merged"]) == ("stopped", True)
    run = json.loads((env.run_dirs[-1] / "run.json").read_text(encoding="utf-8"))
    assert run["result"]["merged"] is True


def test_cycle_limit_ends_with_fixes_pushed(loop: Any, env: Any, kit: Any) -> None:
    env.start(max_cycles=1)
    head = env.gh.head()
    reuse_or_run(loop, env)
    pushed = env.push("修正")
    ref = f"alpha#H-1@{head[:12]}"
    env.gh.post_record(kit.round_record(1, head, "fixes_pushed", [kit.decision(ref, "fix", "new")], commit=pushed))

    ended = loop.cycle_end(env.run_dirs[-1], github=env.github)

    assert ended["outcome"] == "fixes_pushed"
    assert ended["next"][-3:] == ["finish", "--run", str(env.run_dirs[-1])]
    run = json.loads((env.run_dirs[-1] / "run.json").read_text(encoding="utf-8"))
    assert run["result"]["ended_by"] == "cycle_limit"
    with pytest.raises(loop.LoopError) as error:
        loop.cycle_begin(env.run_dirs[-1], github=env.github)
    assert error.value.stage == "state"


def test_stopped_record_ends_the_run_and_finish_releases_the_lock(loop: Any, env: Any, kit: Any) -> None:
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    env.gh.post_record(
        kit.round_record(1, head, "stopped", [], stop_reason="permission: 追加レビューの認可が無い", seats=[])
    )

    ended = loop.cycle_end(env.run_dirs[-1], github=env.github)
    finished = loop.finish(env.run_dirs[-1])

    assert ended["outcome"] == "stopped"
    assert finished["result"]["stop_reason"] == "permission: 追加レビューの認可が無い"
    assert not (env.review_dir / "loop/lock.json").exists()
    assert env.start()["status"] == "ok"


def test_finish_releases_only_its_own_lock(loop: Any, env: Any) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    lock = env.review_dir / "loop/lock.json"
    other = json.loads(lock.read_text(encoding="utf-8"))
    other["run_id"] = "f" * 32
    lock.write_text(json.dumps(other), encoding="utf-8")

    with pytest.raises(loop.LoopError) as error:
        loop.finish(run_dir, abort="external: テスト")

    assert (error.value.code, error.value.stage) == (3, "not_owner")
    assert json.loads(lock.read_text(encoding="utf-8"))["run_id"] == "f" * 32


def test_abort_needs_a_classified_reason(loop: Any, env: Any) -> None:
    started = env.start()

    with pytest.raises(loop.LoopError) as error:
        loop.finish(Path(started["run_dir"]), abort="レビュアーが全員失敗した", github=env.github)
    assert error.value.code == 2

    finished = loop.finish(Path(started["run_dir"]), abort="external: レビュアーが全員失敗した", github=env.github)
    assert finished["result"]["ended_by"] == "abort"
    # マージしていない run の abort は、PR を読んだうえで今までどおり false
    assert finished["result"]["merged"] is False
    assert not (env.review_dir / "loop/lock.json").exists()


@pytest.mark.parametrize("pr_readable", [True, False], ids=["pr-read", "pr-unreadable"])
def test_abort_after_a_finalize_merge_keeps_the_merge(
    loop: Any, env: Any, kit: Any, tmp_path: Path, pr_readable: bool
) -> None:
    """finalize がマージした後に cycle-end が GitHub の失敗で止まり、司令塔が abort した（#221 の再現）。

    abort は PR を読み、読めなければ渡された finalize の結果を使う。どちらでも、マージ済みを false にしない。
    """
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    run_dir = env.run_dirs[-1]
    env.gh.post_record(kit.round_record(1, head, "no_fix_needed", []))
    env.gh.merge()
    result = kit.finalize_result(tmp_path / "final.json", "no_fix_needed", merged=True)
    env.gh.login_status = 1
    with pytest.raises(loop.LoopError) as error:
        loop.cycle_end(run_dir, github=env.github, finalize_result=result)
    assert (error.value.code, error.value.stage) == (5, "github")
    env.gh.pull_status = 0 if pr_readable else 1

    finished = loop.finish(
        run_dir, abort="external: GitHub の読み取りが失敗した", finalize_result=result, github=env.github
    )

    assert (finished["result"]["ended_by"], finished["result"]["merged"]) == ("abort", True)
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run["result"]["merged"] is True
    # PR を読めなかったときだけ、finalize の結果を使った理由を残す
    assert len(run["notes"]) == (0 if pr_readable else 1)


ABSENT = "absent"


@pytest.mark.parametrize(
    ("pr", "reported", "expected"),
    [
        # PR を読めたら、その状態。マージしていない run の abort は今までどおり false
        pytest.param("open", ABSENT, False, id="open"),
        pytest.param("open", False, False, id="open-finalize-false"),
        pytest.param("open", None, False, id="open-finalize-null"),
        pytest.param("merged", ABSENT, True, id="merged"),
        pytest.param("merged", False, True, id="merged-finalize-false"),
        # 読めなければ、渡された finalize の結果（最後の観測）。どちらも無ければ未確認で、false にしない
        pytest.param("unreadable", True, True, id="unreadable-finalize-true"),
        pytest.param("unreadable", False, False, id="unreadable-finalize-false"),
        pytest.param("unreadable", None, None, id="unreadable-finalize-null"),
        pytest.param("unreadable", ABSENT, None, id="unreadable"),
        # finalize はマージ済みと返したのに PR は未マージ: どちらかの読み取りが誤っているので未確認
        pytest.param("open", True, None, id="open-finalize-true"),
    ],
)
def test_abort_records_the_merge_state_it_observed(
    loop: Any, env: Any, kit: Any, tmp_path: Path, pr: str, reported: bool | str | None, expected: bool | None
) -> None:
    env.start()
    reuse_or_run(loop, env)
    run_dir = env.run_dirs[-1]
    if pr == "merged":
        env.gh.merge()
    env.gh.pull_status = 1 if pr == "unreadable" else 0
    result = None
    if reported != ABSENT:
        result = kit.finalize_result(
            tmp_path / "final.json",
            "no_fix_needed" if reported is True else "stopped",
            merged=reported,
            stop_reason=None if reported is True else "external: テスト",
        )

    finished = loop.finish(run_dir, abort="external: テスト", finalize_result=result, github=env.github)

    assert finished["result"]["merged"] is expected
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert (run["state"], run["result"]["merged"]) == ("ended", expected)


def test_abort_treats_a_gh_that_cannot_start_as_unreadable(loop: Any, env: Any, kit: Any, tmp_path: Path) -> None:
    """gh を起動できない（OSError）ときも abort を止めず、PR を読めないとして決める。"""
    env.start()
    run_dir = env.run_dirs[-1]

    def missing(argv: Any) -> Any:
        raise FileNotFoundError("gh")

    result = kit.finalize_result(tmp_path / "final.json", "no_fix_needed", merged=True)

    finished = loop.finish(
        run_dir, abort="environment: gh を起動できない", finalize_result=result, github=loop.GitHub(missing)
    )

    assert finished["result"]["merged"] is True
    assert len(json.loads((run_dir / "run.json").read_text(encoding="utf-8"))["notes"]) == 1


def test_finalize_result_is_only_for_abort_and_must_be_a_finalize_result(
    loop: Any, env: Any, kit: Any, tmp_path: Path
) -> None:
    """--finalize-result の誤りは、run を変えず、PR も読まずに終了コード 2 で止める。"""
    env.start()
    run_dir = env.run_dirs[-1]
    good = kit.finalize_result(tmp_path / "final.json", "no_fix_needed", merged=True)
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"outcome": "no_fix_needed", "merged": "yes", "issues": []}), encoding="utf-8")
    calls = len(env.gh.calls)

    for options in (
        {"finalize_result": good},
        {"abort": "external: テスト", "finalize_result": broken},
        {"abort": "external: テスト", "finalize_result": tmp_path / "missing.json"},
    ):
        with pytest.raises(loop.LoopError) as error:
            loop.finish(run_dir, github=env.github, **options)
        assert (error.value.code, error.value.stage) == (2, "arguments"), options

    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert (run["state"], run["result"]) == ("running", None)
    assert (env.review_dir / "loop/lock.json").exists()
    assert env.gh.calls[calls:] == []


def test_cli_finish_abort_passes_the_finalize_result(
    loop: Any, env: Any, kit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env.start()
    run_dir = env.run_dirs[-1]
    env.gh.merge()
    # PR を読めないので、merged が true になるのは渡したファイルを使ったときだけ
    env.gh.pull_status = 1
    result = kit.finalize_result(tmp_path / "final.json", "no_fix_needed", merged=True)
    monkeypatch.setattr(loop, "GitHub", lambda: env.github)
    capsys.readouterr()

    arguments = ["finish", "--run", str(run_dir), "--abort", "external: GitHub の読み取りが失敗した"]
    assert loop.main([*arguments, "--finalize-result", str(result)]) == 0

    assert json.loads(capsys.readouterr().out)["result"]["merged"] is True


def test_status_returns_the_next_command_after_a_restart(loop: Any, env: Any, kit: Any) -> None:
    started = env.start()
    run_dir = Path(started["run_dir"])
    reuse_or_run(loop, env)

    by_run = loop.status(run_dir=run_dir)
    by_pr = loop.status(argument=f"#{kit.number}", github=env.github, parent_root=env.parent)

    assert by_run["next"][-3:] == ["cycle-end", "--run", str(run_dir)]
    assert by_pr["run_id"] == started["run_id"]
    assert by_pr["next"] == by_run["next"]


def test_record_from_an_earlier_run_for_the_same_head_is_not_taken(loop: Any, env: Any, kit: Any) -> None:
    # 前の run が同じ HEAD で stopped を投稿した後、同じ HEAD で新しい run を始めた場合
    # （例: 権限不足で止まった run を同じ HEAD で再実行）
    first = env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    env.gh.post_record(
        kit.round_record(1, head, "stopped", [], stop_reason="permission: 追加レビューの認可が無い", seats=[])
    )
    loop.cycle_end(Path(first["run_dir"]), github=env.github)
    loop.finish(Path(first["run_dir"]))

    second = env.start()
    run_dir = Path(second["run_dir"])
    assert loop.cycle_begin(run_dir, github=env.github)["review"]["mode"] == "reuse"

    with pytest.raises(loop.LoopError) as error:
        loop.cycle_end(run_dir, github=env.github)
    assert (error.value.code, error.value.stage) == (4, "record_missing")

    env.gh.post_record(kit.round_record(2, head, "stopped", [], stop_reason="external: 二回目の計画の停止", seats=[]))
    ended = loop.cycle_end(run_dir, github=env.github)
    assert (ended["round"], ended["stop_reason"]) == (2, "external: 二回目の計画の停止")


def test_a_differently_cased_pr_url_shares_the_lock(loop: Any, env: Any, kit: Any) -> None:
    first = env.start()

    with pytest.raises(loop.LoopError) as error:
        loop.start(
            "https://github.com/Usaturn/Create-Reso-World/pull/900",
            controller_model="m",
            controller_runtime="claude-code",
            github=env.github,
            parent_root=env.parent,
            tool_root=env.parent,
            template=env.template,
        )

    assert (error.value.code, error.value.stage) == (3, "lock_held")
    assert first["run_id"] in error.value.reason


def test_a_failed_lock_write_leaves_no_lock(loop: Any, env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: Any, **kwargs: Any) -> str:
        raise OSError("disk full")

    real = loop.LockRecord.model_dump_json
    monkeypatch.setattr(loop.LockRecord, "model_dump_json", broken)
    with pytest.raises(OSError):
        env.start()
    monkeypatch.setattr(loop.LockRecord, "model_dump_json", real)

    assert not (env.review_dir / "loop/lock.json").exists()
    assert env.start()["status"] == "ok"


# --- 移植先で足した挙動（Spec D-3・D-9・D-10） ----------------------------------------------------------------------


def test_start_refuses_a_pr_whose_checkout_cannot_be_resolved(loop: Any, env: Any) -> None:
    """Git 操作の対象の checkout を決められない PR は、ロックを取る前に止める（Spec D-3）。

    レビュアーの pr-review は CODE_ROOT なしで同じ解決（review_target.target_checkout）を使うので、
    ここを通すと費用のかかるレビュアーが全員失敗する。
    """
    env.gh.repository = "usaturn/resoloop-meshy"

    with pytest.raises(loop.LoopError) as error:
        env.start("https://github.com/usaturn/resoloop-meshy/pull/900")

    assert (error.value.code, error.value.stage) == (2, "arguments")
    assert not (env.parent / "reviews" / "usaturn" / "resoloop-meshy").exists()


@pytest.mark.parametrize(("status", "login"), [(1, ""), (0, ""), (0, " \n")], ids=["gh-failed", "empty", "blank"])
def test_records_need_the_authenticated_login(loop: Any, env: Any, kit: Any, status: int, login: str) -> None:
    """判断の記録は認証済みの login を添えて読む（#169）。取れなければ、読む投稿者を狭めたまま続けずに止める（Spec D-9）。"""
    env.start()
    run_dir = env.run_dirs[-1]
    env.gh.login_status, env.gh.login = status, login
    with pytest.raises(loop.LoopError) as begun:
        loop.cycle_begin(run_dir, github=env.github)
    assert (begun.value.code, begun.value.stage) == (5, "github")
    assert not (run_dir / "cycle-1.json").exists()

    env.gh.login_status, env.gh.login = 0, "usaturn\n"
    head = env.gh.head()
    reuse_or_run(loop, env)
    env.gh.post_record(kit.round_record(1, head, "stopped", [], stop_reason="external: テスト", seats=[]))
    env.gh.login_status, env.gh.login = status, login
    with pytest.raises(loop.LoopError) as ended:
        loop.cycle_end(run_dir, github=env.github)
    assert (ended.value.code, ended.value.stage) == (5, "github")
    assert json.loads((run_dir / "cycle-1.json").read_text(encoding="utf-8"))["state"] == "planning"


def test_cycle_end_reads_the_authenticated_users_record(loop: Any, env: Any, kit: Any) -> None:
    """上流の PR では利用者自身のコメントが CONTRIBUTOR になる。認証済みの login と同じ投稿者の記録は読み、
    ほかの CONTRIBUTOR の記録は読まない（Spec D-9）。"""
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    record = kit.round_record(1, head, "stopped", [], stop_reason="external: テスト", seats=[])
    env.gh.post_record(record, login="someone-else", association="CONTRIBUTOR")

    with pytest.raises(loop.LoopError) as error:
        loop.cycle_end(env.run_dirs[-1], github=env.github)
    assert error.value.stage == "record_missing"

    env.gh.post_record(record, login="usaturn", association="CONTRIBUTOR")
    ended = loop.cycle_end(env.run_dirs[-1], github=env.github)
    assert (ended["round"], ended["outcome"]) == (1, "stopped")


def test_cycle_end_accepts_a_spec_commit_merge(loop: Any, env: Any, kit: Any, tmp_path: Path) -> None:
    """create-reso-world の PR の結論 2 は、検証した HEAD に Spec だけの commit S を載せて S をマージする（#155 の D-5）。

    PR の head は S なので、finalize の結果に spec_commit があればマージ済みの照合を S と比べる。無ければ従来どおり
    サイクルの HEAD と比べ、S のマージは食い違いになる（Spec D-10）。
    """
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    run_dir = env.run_dirs[-1]
    env.gh.post_record(kit.round_record(1, head, "no_fix_needed", []))
    spec_commit = env.push("Spec だけの commit")
    env.gh.merge()

    for name, value in (("without.json", None), ("other.json", "1" * 40)):
        result = kit.finalize_result(tmp_path / name, "no_fix_needed", merged=True, spec_commit=value)
        with pytest.raises(loop.LoopError) as error:
            loop.cycle_end(run_dir, github=env.github, finalize_result=result)
        assert (error.value.code, error.value.stage) == (4, "merge_mismatch"), name

    result = kit.finalize_result(tmp_path / "final.json", "no_fix_needed", merged=True, spec_commit=spec_commit)
    ended = loop.cycle_end(run_dir, github=env.github, finalize_result=result)

    assert (ended["outcome"], ended["merged"]) == ("no_fix_needed", True)
    cycle = json.loads((run_dir / "cycle-1.json").read_text(encoding="utf-8"))
    assert cycle["planning"]["finalize"]["result"]["spec_commit"] == spec_commit
    assert loop.finish(run_dir)["result"]["merged"] is True


@pytest.mark.parametrize("spec_commit", [None, 123, "abc", "A" * 40], ids=["null", "number", "short", "uppercase"])
def test_cycle_end_rejects_a_malformed_spec_commit(
    loop: Any, env: Any, kit: Any, tmp_path: Path, spec_commit: object
) -> None:
    """spec_commit があるのに SHA の形でない結果は、finalize.py の結果として読まない（Spec D-10）。"""
    env.start()
    head = env.gh.head()
    reuse_or_run(loop, env)
    env.gh.post_record(kit.round_record(1, head, "no_fix_needed", []))
    env.gh.merge()
    path = tmp_path / "final.json"
    path.write_text(
        json.dumps({"outcome": "no_fix_needed", "merged": True, "issues": [], "spec_commit": spec_commit}),
        encoding="utf-8",
    )

    with pytest.raises(loop.LoopError) as error:
        loop.cycle_end(env.run_dirs[-1], github=env.github, finalize_result=path)

    assert (error.value.code, error.value.stage) == (2, "arguments")
