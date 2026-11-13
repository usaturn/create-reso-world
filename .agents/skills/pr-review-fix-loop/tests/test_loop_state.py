"""ロック・サイクルの状態・判断の記録の照合・結果ごとの終わり方を、偽の gh と bare remote で確かめる。

計画担当（review-fix-planning）の代わりに、テストが記録の投稿・push・マージを行う。
"""

from __future__ import annotations

import json
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


# テスト用の雛形（conftest の TEST_TEMPLATE）に codex の担当 echo を足す個人設定
CODEX_AGENT = """
[agents.echo]
runtime = "codex"
command = ["fake-echo"]
model = "echo-model"
"""


def write_personal(root: Path) -> Path:
    path = root / "personal.toml"
    path.write_text(CODEX_AGENT, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("assign", "expected"),
    [
        pytest.param(
            [],
            {"implement": ["alpha"], "self-review": ["self"], "fix-check": ["self"]},
            id="default",
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
    """codex を拒否するのは inspect・self-review・fix-check だけ。implement（workspace-write）には使える（#731）。"""
    started = env.start(assign=assign, config=write_personal(tmp_path))

    assert started["status"] == "ok"
    assert {role: value["agents"] for role, value in started["assignments"]["fix"].items()} == expected


def test_start_records_options_and_effective_assignments(
    loop: Any, env: Any, kit: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # CLI の --assign が dispatch で落ちないことを確かめる。保存と計画への引き渡しは実 helper を使い、
    # GitHub と親 checkout の探索だけ隔離する。
    monkeypatch.setattr(loop, "GitHub", lambda: env.github)
    monkeypatch.setattr(loop.target, "default_parent_root", lambda: env.parent)
    arguments = ["start", f"#{kit.number}", "--controller-model", "test-planner", "--controller-runtime", "pi"]
    arguments += ["--max-cycles", "2", "--assign", "inspect=beta,alpha", "--assign", "implement=beta"]
    arguments += ["--template", str(env.template)]
    assert loop.main(arguments) == 0
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
    assert run["tool_commit"] == kit.git(Path(run["tool_root"]), "rev-parse", "HEAD")
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
    assert json.loads((env.run_dirs[-1] / "cycle-1.json").read_text(encoding="utf-8"))["state"] == "planning"

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
    # false は、finalize が別の head のマージを観測して止まった結果（Review Focus 1 をループの最後まで通す経路）。
    # true_merge_parent は、finalize がマージの後の merge commit の照合で止まった結果（#206）。PR は検証した HEAD でマージ済み
    [
        (False, True),
        (None, False),
        (True, False),
    ],
    ids=["false", "null", "true_merge_parent"],
)
def test_finalize_stopped_keeps_the_real_merge(
    loop: Any,
    env: Any,
    kit: Any,
    tmp_path: Path,
    reported: bool | None,
    another_head: bool,
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


@pytest.mark.parametrize(
    "pr_readable",
    [
        False,
    ],
    ids=["pr-unreadable"],
)
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
        # PR を読めたら、その状態。マージしていない run の abort は false で、未確認（null）にしない
        pytest.param("open", ABSENT, False, id="open"),
        pytest.param("merged", False, True, id="merged-finalize-false"),
        pytest.param("unreadable", ABSENT, None, id="unreadable"),
        pytest.param("open", True, None, id="open-finalize-true"),
    ],
)
def test_abort_records_the_merge_state_it_observed(
    loop: Any,
    env: Any,
    kit: Any,
    tmp_path: Path,
    pr: str,
    reported: bool | str | None,
    expected: bool | None,
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
    # abort を受理した時刻を初回だけ保存する（reconcile の日時照合の根拠。merged の 3 値は変えない）
    assert run["aborted_at"] is not None
    aborted_at = run["aborted_at"]
    with pytest.raises(loop.LoopError) as again:
        loop.finish(run_dir, abort="external: 二回目", github=env.github)
    assert again.value.code == 3
    assert json.loads((run_dir / "run.json").read_text(encoding="utf-8"))["aborted_at"] == aborted_at


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


# --- 移植先で足した挙動（Spec D-3・D-9・D-10） ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "login"),
    [
        (0, " \n"),
    ],
    ids=["blank"],
)
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
