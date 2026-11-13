"""マージ後に abort した run の読み取り専用照合（reconcile）を、偽の gh と一時 Git で確かめる。

成功の対照と、独立した守り（finalize・ID・PR 所属・投稿者・本文・HEAD・過去記録・日時・既存証拠）の代表拒否。
証拠が一致したときだけ reconcile.json を追記し、元の run/cycle の bytes と abort 結果は書き換えない。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPOSITORY = "usaturn/create-reso-world"
NUMBER = 900

# 制御した時刻。now() は秒単位で、実際の時計ではサイクル開始・コメント・マージ・abort が同じ秒になり、
# 前後の条件（updated < aborted など）を確定できないので、helper の時計を差し替える
T_CYCLE = "2026-11-14T00:00:00Z"
T_CREATED = "2026-11-14T00:01:00Z"
T_UPDATED = "2026-11-14T00:01:30Z"
T_MERGED = "2026-11-14T00:02:00Z"
T_ABORT = "2026-11-14T00:03:00Z"
T_LATER = "2026-11-14T00:04:00Z"


class Clock:
    def __init__(self) -> None:
        self.value = T_CYCLE

    def __call__(self) -> str:
        return self.value


class ReconcileGh:
    """conftest の FakeGitHub に、単一コメントの取得とコメント日時・PR の merged_at を足す。

    一覧・login・PR の読み取りは包んだ偽の gh に任せる。created_at/updated_at/issue_url は
    単一取得の生応答にだけ載る（一覧の正規化は日時を落とす）。
    """

    def __init__(self, gh: Any) -> None:
        self.gh = gh
        self.times: dict[int, dict[str, Any]] = {}
        self.merged_at: str | None = T_MERGED
        self.single_status = 0
        self.single_stderr = "HTTP 502 Bad Gateway"
        self.single_body: str | None = None
        self.single_login: str | None = None
        self.single_issue_url: str | None = None

    def set_times(self, comment_id: int, *, created: Any = T_CREATED, updated: Any = T_UPDATED) -> None:
        self.times[comment_id] = {"created_at": created, "updated_at": updated}

    def runner(self, argv: Any) -> subprocess.CompletedProcess[str]:
        args = list(argv)
        prefix = f"repos/{self.gh.repository}/issues/comments/"
        if args[:2] == ["gh", "api"] and len(args) == 3 and args[2].startswith(prefix):
            self.gh.calls.append(args)
            comment_id = int(args[2].removeprefix(prefix))
            if self.single_status:
                return subprocess.CompletedProcess(args, self.single_status, "", self.single_stderr)
            comment = next((item for item in self.gh.comments if item["id"] == comment_id), None)
            if comment is None:
                return subprocess.CompletedProcess(args, 1, "", "HTTP 404: Not Found (https://api.github.com/)")
            times = self.times.get(comment_id, {"created_at": T_CREATED, "updated_at": T_UPDATED})
            raw: dict[str, Any] = {
                **comment,
                "created_at": times["created_at"],
                "updated_at": times["updated_at"],
                "issue_url": self.single_issue_url
                or f"https://api.github.com/repos/{self.gh.repository}/issues/{NUMBER}",
            }
            if self.single_body is not None:
                raw["body"] = self.single_body
            if self.single_login is not None:
                raw["user"] = {"login": self.single_login}
            return subprocess.CompletedProcess(args, 0, json.dumps(raw, ensure_ascii=False), "")
        result = self.gh.runner(args)
        pulls = f"repos/{self.gh.repository}/pulls/{NUMBER}"
        if result.returncode == 0 and args[:2] == ["gh", "api"] and len(args) == 3 and args[2] == pulls:
            value = json.loads(result.stdout)
            value["merged_at"] = self.merged_at if self.gh.merged else None
            return subprocess.CompletedProcess(args, 0, json.dumps(value), "")
        return result


def write_finalize(path: Path, comment_id: int | None, **changes: Any) -> Path:
    """finalize.py の成功結果の形（MERGED 再開が返す comment.comment_id 付き）。"""
    value: dict[str, Any] = {"outcome": "no_fix_needed", "merged": True, "issues": []}
    if comment_id is not None:
        value["comment"] = {"comment_id": comment_id}
    value.update(changes)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_scene(
    loop: Any,
    env: Any,
    kit: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    round_: int = 1,
    post_before_cycle: bool = False,
) -> SimpleNamespace:
    """マージ後に abort した run と、中断前に確定した整合する証拠一式を作る。"""
    clock = Clock()
    monkeypatch.setattr(loop, "now", clock)
    gh = ReconcileGh(env.gh)
    github = loop.GitHub(gh.runner)
    env.start()
    run_dir = env.run_dirs[-1]
    head = env.gh.head()
    env.place_review(head)
    record = kit.round_record(round_, head, "no_fix_needed", [])
    # 日本語・複数行・末尾改行を含む本文（正規化しない照合の入力）
    body = "### レビュー状況\n追加の修正は不要。\n現行 HEAD で検証済み。\n"
    comment_id: int | None = None
    if post_before_cycle:
        comment_id = env.gh.post_record(record, body)
        gh.set_times(comment_id)
    clock.value = T_CYCLE
    begun = loop.cycle_begin(run_dir, github=github)
    assert begun["review"]["mode"] == "reuse"
    if comment_id is None:
        comment_id = env.gh.post_record(record, body)
        gh.set_times(comment_id)
    composed = next(item["body"] for item in env.gh.comments if item["id"] == comment_id)
    env.gh.merge()
    finalize = write_finalize(tmp_path / "final.json", comment_id)
    clock.value = T_ABORT
    finished = loop.finish(
        run_dir, abort="external: マージ後の GitHub 読み取りが失敗した", finalize_result=finalize, github=github
    )
    assert (finished["result"]["ended_by"], finished["result"]["merged"]) == ("abort", True)
    return SimpleNamespace(
        run_dir=run_dir,
        head=head,
        comment_id=comment_id,
        finalize=finalize,
        github=github,
        gh=gh,
        clock=clock,
        body=composed,
        prose=body,
        record=record,
    )


@pytest.fixture
def scene(loop: Any, env: Any, kit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    return build_scene(loop, env, kit, tmp_path, monkeypatch)


def refuse_new(loop: Any, scene: SimpleNamespace, *, stage: str | None = None, code: int = 4, **options: Any) -> None:
    """不一致は指定の終了コードで止まり、reconcile.json を作らない。"""
    arguments: dict[str, Any] = {
        "finalize_result": scene.finalize,
        "comment_id": scene.comment_id,
        "github": scene.github,
    }
    arguments.update(options)
    with pytest.raises(loop.LoopError) as error:
        loop.reconcile(scene.run_dir, **arguments)
    assert error.value.code == code
    if stage is not None:
        assert error.value.stage == stage
    assert not (scene.run_dir / "reconcile.json").exists()


# --- 成功の対照 ---------------------------------------------------------------------------------------------------


def test_reconcile_confirms_a_merged_abort_with_matching_evidence(scene: SimpleNamespace, loop: Any) -> None:
    # 本文は日本語・複数行・末尾改行を含む（正規化しない照合の成功入力）
    assert "レビュー状況" in scene.body and scene.body.count("\n") >= 3 and scene.prose.endswith("\n")
    before_run = (scene.run_dir / "run.json").read_bytes()
    before_cycle = (scene.run_dir / "cycle-1.json").read_bytes()

    output = loop.reconcile(
        scene.run_dir, finalize_result=scene.finalize, comment_id=scene.comment_id, github=scene.github
    )

    assert output["status"] == "ok"
    assert output["result"] == {
        "outcome": "no_fix_needed",
        "ended_by": "outcome",
        "stop_reason": None,
        "merged": True,
        "cycles": 1,
    }
    assert output["original_result"]["ended_by"] == "abort"
    assert output["original_result"]["stop_reason"] == "external: マージ後の GitHub 読み取りが失敗した"
    evidence = output["reconciled"]
    assert evidence["schema"] == "pr-review-fix-loop/v1" and evidence["kind"] == "reconcile"
    assert evidence["run_id"] == json.loads(before_run)["run_id"]
    assert (evidence["cycle"], evidence["head"], evidence["round"]) == (1, scene.head, 1)
    assert evidence["comment_id"] == scene.comment_id
    assert evidence["comment_created_at"] == T_CREATED
    assert evidence["comment_updated_at"] == T_UPDATED
    assert evidence["merged_at"] == T_MERGED
    assert evidence["run_sha256"] == loop.sha256_file(scene.run_dir / "run.json")
    assert evidence["cycle_sha256"] == loop.sha256_file(scene.run_dir / "cycle-1.json")
    assert evidence["finalize_sha256"] == loop.sha256_file(scene.finalize)
    assert evidence["finalize"]["result_file"] == str(scene.finalize.resolve())
    saved = json.loads((scene.run_dir / "reconcile.json").read_text(encoding="utf-8"))
    assert saved == evidence
    # 元の run/cycle の bytes と abort 結果は保持する
    assert (scene.run_dir / "run.json").read_bytes() == before_run
    assert (scene.run_dir / "cycle-1.json").read_bytes() == before_cycle
    run = json.loads(before_run)
    assert (run["result"]["outcome"], run["result"]["ended_by"], run["aborted_at"]) == ("stopped", "abort", T_ABORT)
    # GitHub は読み取りだけ。一覧への所属確認が単一取得より先
    calls = scene.gh.gh.calls
    assert all(call[:2] == ["gh", "api"] and "--method" not in call for call in calls)
    list_index = next(index for index, call in enumerate(calls) if "--slurp" in call)
    single_index = next(
        index for index, call in enumerate(calls) if call[-1].endswith(f"issues/comments/{scene.comment_id}")
    )
    assert list_index < single_index


def test_reconcile_rerun_with_the_same_evidence_keeps_the_file(scene: SimpleNamespace, loop: Any) -> None:
    first = loop.reconcile(
        scene.run_dir, finalize_result=scene.finalize, comment_id=scene.comment_id, github=scene.github
    )
    path = scene.run_dir / "reconcile.json"
    before = path.read_bytes()
    scene.clock.value = T_LATER

    again = loop.reconcile(
        scene.run_dir, finalize_result=scene.finalize, comment_id=scene.comment_id, github=scene.github
    )

    assert path.read_bytes() == before
    assert again["reconciled"] == first["reconciled"]
    assert again["result"]["merged"] is True


def test_status_without_evidence_reports_null_reconciled(scene: SimpleNamespace, loop: Any) -> None:
    output = loop.status(run_dir=scene.run_dir)
    assert output["reconciled"] is None
    assert output["result"]["ended_by"] == "abort"
    assert "original_result" not in output


# --- finalize 結果・コメント ID の不一致 -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    ["stopped", "unmerged", "unconfirmed", "other_comment", "no_comment"],
)
def test_finalize_result_must_be_the_matching_success(
    scene: SimpleNamespace, loop: Any, tmp_path: Path, change: str
) -> None:
    cid = scene.comment_id
    bad = tmp_path / "bad.json"
    if change == "stopped":
        write_finalize(bad, cid, outcome="stopped", stop_reason="external: テスト")
    elif change == "unmerged":
        write_finalize(bad, cid, merged=False)
    elif change == "unconfirmed":
        write_finalize(bad, cid, merged=None)
    elif change == "other_comment":
        write_finalize(bad, cid + 1)
    else:
        write_finalize(bad, None)
    refuse_new(loop, scene, finalize_result=bad, stage="record_inconsistent")


@pytest.mark.parametrize("bad", [0, -1, True])
def test_comment_id_must_be_a_positive_integer(scene: SimpleNamespace, loop: Any, bad: Any) -> None:
    # bool を ID として受け付けない（True == 1 の取り違えを防ぐ）
    refuse_new(loop, scene, comment_id=bad, code=2, stage="arguments")


def test_comment_id_in_the_finalize_result_must_not_be_a_bool(scene: SimpleNamespace, loop: Any, tmp_path: Path) -> None:
    bad = write_finalize(tmp_path / "bool.json", None)
    value = json.loads(bad.read_text(encoding="utf-8"))
    value["comment"] = {"comment_id": True}
    bad.write_text(json.dumps(value), encoding="utf-8")
    refuse_new(loop, scene, finalize_result=bad, comment_id=1, stage="record_inconsistent")


def test_unknown_comment_is_not_reconciled(scene: SimpleNamespace, loop: Any, tmp_path: Path) -> None:
    # finalize も同じ未知 ID を指すとき、一覧への所属確認で拒否する（存在しない・別 PR の ID）
    bad = write_finalize(tmp_path / "unknown.json", 999999)
    refuse_new(loop, scene, finalize_result=bad, comment_id=999999, stage="record_missing")


# --- PR 所属・投稿者・本文の不一致 -------------------------------------------------------------------------------


def test_single_comment_must_belong_to_this_pr(scene: SimpleNamespace, loop: Any) -> None:
    # 一覧には採用された ID でも、単一取得の応答が別の PR を指すなら確定しない
    scene.gh.single_issue_url = f"https://api.github.com/repos/{REPOSITORY}/issues/{NUMBER + 1}"
    refuse_new(loop, scene, stage="record_inconsistent")


def test_comment_author_must_be_the_authenticated_login(scene: SimpleNamespace, loop: Any) -> None:
    # 一覧では信頼できる投稿者でも、単一取得の投稿者が認証 login と違えば拒否する（association では代用しない）
    scene.gh.single_login = "someone-else"
    refuse_new(loop, scene, stage="record_inconsistent")


def test_body_must_match_without_normalization(scene: SimpleNamespace, loop: Any) -> None:
    # 末尾改行だけの違いも不一致（日本語・改行・末尾改行を正規化しない）
    scene.gh.single_body = scene.body + "\n"
    refuse_new(loop, scene, stage="record_inconsistent")


@pytest.mark.parametrize(
    ("status", "stderr", "code", "stage"),
    [
        (1, "HTTP 404: Not Found (https://api.github.com/)", 4, "record_missing"),
        (1, "HTTP 502 Bad Gateway", 5, "github"),
    ],
    ids=["gone-after-list", "infrastructure"],
)
def test_single_comment_failure_after_the_list(
    scene: SimpleNamespace, loop: Any, status: int, stderr: str, code: int, stage: str
) -> None:
    scene.gh.single_status, scene.gh.single_stderr = status, stderr
    refuse_new(loop, scene, code=code, stage=stage)


# --- HEAD・spec_commit の不一致 ----------------------------------------------------------------------------------


def test_merged_at_another_head_is_not_reconciled(scene: SimpleNamespace, loop: Any, env: Any) -> None:
    scene.gh.gh.merged_head = env.push("サイクルの後の commit")
    refuse_new(loop, scene, stage="merge_mismatch")


def test_spec_commit_head_is_out_of_scope(scene: SimpleNamespace, loop: Any, env: Any, tmp_path: Path) -> None:
    # spec_commit で HEAD が変わる run は新しい reconcile では受け付けない（既存 cycle_end の許容は変えない）
    spec = env.push("Spec だけの commit")
    moved = write_finalize(tmp_path / "spec.json", scene.comment_id, spec_commit=spec)
    scene.gh.gh.merged_head = spec
    refuse_new(loop, scene, finalize_result=moved, stage="merge_mismatch")
    # PR の HEAD がサイクルの HEAD のままでも、spec_commit の主張は証拠として整合しない
    scene.gh.gh.merged_head = scene.head
    refuse_new(loop, scene, finalize_result=moved, stage="merge_mismatch")


# --- 過去記録・日時の不一致 --------------------------------------------------------------------------------------


def test_round_not_after_prior_round_is_not_reconciled(
    loop: Any, env: Any, kit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # cycle-begin より前の記録（prior_round 以下）は、このサイクルの成功記録ではない
    built = build_scene(loop, env, kit, tmp_path, monkeypatch, post_before_cycle=True)
    refuse_new(loop, built, stage="record_inconsistent")


def test_record_conflicting_with_prior_history_is_not_reconciled(
    loop: Any, env: Any, kit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # round 1 が無いのに round 2 の記録は、先行記録との照合（trusted_login 付き）で拒否する
    built = build_scene(loop, env, kit, tmp_path, monkeypatch, round_=2)
    refuse_new(loop, built, stage="record_inconsistent")


@pytest.mark.parametrize(
    "case",
    [
        "created_before_cycle",
        "updated_at_abort",
        "merged_at_abort",
        "merged_before_created",
        "merged_missing",
        "created_missing",
        "naive",
    ],
)
def test_times_must_order_the_evidence_before_the_abort(scene: SimpleNamespace, loop: Any, case: str) -> None:
    cid = scene.comment_id
    if case == "created_before_cycle":
        scene.gh.set_times(cid, created="2026-11-13T23:59:59Z")
    elif case == "updated_at_abort":
        # abort と同じ秒は前後を確定できない
        scene.gh.set_times(cid, updated=T_ABORT)
    elif case == "merged_at_abort":
        scene.gh.merged_at = T_ABORT
    elif case == "merged_before_created":
        scene.gh.merged_at = "2026-11-14T00:00:30Z"
    elif case == "merged_missing":
        scene.gh.merged_at = None
    elif case == "created_missing":
        scene.gh.set_times(cid, created=None)
    else:
        scene.gh.set_times(cid, created="2026-11-14T00:01:00")
    refuse_new(loop, scene, stage="record_inconsistent")


def test_old_run_without_aborted_at_is_not_reconciled(scene: SimpleNamespace, loop: Any) -> None:
    # 日時のない旧 run を推測で成功にしない
    path = scene.run_dir / "run.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    del value["aborted_at"]
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    refuse_new(loop, scene, stage="record_inconsistent")


# --- 状態・ロック -------------------------------------------------------------------------------------------------


def test_active_or_completed_runs_are_not_reconciled(loop: Any, env: Any, kit: Any, tmp_path: Path) -> None:
    env.start()
    run_dir = env.run_dirs[-1]
    head = env.gh.head()
    env.place_review(head)
    loop.cycle_begin(run_dir, github=env.github)
    finalize = write_finalize(tmp_path / "final.json", 1001)

    # 結果の無い running の run
    with pytest.raises(loop.LoopError) as error:
        loop.reconcile(run_dir, finalize_result=finalize, comment_id=1001, github=env.github)
    assert (error.value.code, error.value.stage) == (3, "state")

    # サイクルが完了した run（abort ではない終わり方）
    env.gh.post_record(kit.round_record(1, head, "no_fix_needed", []))
    env.gh.merge()
    loop.cycle_end(run_dir, github=env.github, finalize_result=finalize)
    loop.finish(run_dir)
    with pytest.raises(loop.LoopError) as error:
        loop.reconcile(run_dir, finalize_result=finalize, comment_id=1001, github=env.github)
    assert (error.value.code, error.value.stage) == (3, "state")
    assert not (run_dir / "reconcile.json").exists()


def test_lock_refuses_reconcile(scene: SimpleNamespace, loop: Any, env: Any) -> None:
    lock = env.review_dir / "loop" / "lock.json"
    lock.write_text(
        json.dumps(
            {
                "schema": "pr-review-fix-loop/v1",
                "kind": "lock",
                "run_id": "f" * 32,
                "pr": {"repository": REPOSITORY, "number": NUMBER, "url": f"https://github.com/{REPOSITORY}/pull/{NUMBER}"},
                "run_dir": str(scene.run_dir),
                "created_at": T_CYCLE,
            }
        ),
        encoding="utf-8",
    )
    refuse_new(loop, scene, code=3, stage="lock_held")


# --- 既存証拠の保持と status の再検証 ----------------------------------------------------------------------------


def test_existing_evidence_is_not_overwritten(scene: SimpleNamespace, loop: Any, tmp_path: Path) -> None:
    loop.reconcile(scene.run_dir, finalize_result=scene.finalize, comment_id=scene.comment_id, github=scene.github)
    path = scene.run_dir / "reconcile.json"
    before = path.read_bytes()

    # finalize 結果の移動・再整形は同じ証拠ではない（場所と元バイト列も証拠）
    moved = tmp_path / "moved.json"
    moved.write_bytes(scene.finalize.read_bytes())
    reformatted = tmp_path / "reformatted.json"
    reformatted.write_text(json.dumps(json.loads(scene.finalize.read_text(encoding="utf-8"))), encoding="utf-8")
    for other in (moved, reformatted):
        with pytest.raises(loop.LoopError) as error:
            loop.reconcile(scene.run_dir, finalize_result=other, comment_id=scene.comment_id, github=scene.github)
        assert (error.value.code, error.value.stage) == (4, "record_inconsistent")
        assert path.read_bytes() == before


@pytest.mark.parametrize("target", ["run.json", "cycle-1.json", "reconcile.json"])
def test_status_revalidates_saved_evidence(scene: SimpleNamespace, loop: Any, target: str) -> None:
    loop.reconcile(scene.run_dir, finalize_result=scene.finalize, comment_id=scene.comment_id, github=scene.github)
    ok = loop.status(run_dir=scene.run_dir)
    assert ok["result"]["merged"] is True and ok["reconciled"] is not None
    assert ok["original_result"]["ended_by"] == "abort"
    assert ok["cycles"][-1]["state"] == "ended"

    # 保存後に元記録・証拠が改変されたら、status は 4 で止まり merged=true を返さない
    path = scene.run_dir / target
    value = json.loads(path.read_text(encoding="utf-8"))
    if target == "run.json":
        value["notes"].append("改変")
    elif target == "cycle-1.json":
        value["head"] = "0" * 40
    else:
        value["result"]["merged"] = False
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(loop.LoopError) as error:
        loop.status(run_dir=scene.run_dir)
    assert (error.value.code, error.value.stage) == (4, "record_inconsistent")


# --- finish --abort の日時 ---------------------------------------------------------------------------------------


def test_abort_time_survives_held_and_recover(loop: Any, env: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = Clock()
    monkeypatch.setattr(loop, "now", clock)
    github = loop.GitHub(ReconcileGh(env.gh).runner)
    env.start()
    run_dir = env.run_dirs[-1]
    env.place_review(env.gh.head())
    loop.cycle_begin(run_dir, github=github)
    # 停止を確認できない資源（出力ディレクトリはあるが runner の結果が無い）
    parent = env.tmp_root / "create-reso-world-pr-loop-unconfirmed"
    parent.mkdir()
    run_path = run_dir / "run.json"
    value = json.loads(run_path.read_text(encoding="utf-8"))
    value["resources"].append(
        {"path": str(parent), "kind": "runner_output", "cycle": 1, "state": "created", "reason": None}
    )
    run_path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    finalize = write_finalize(tmp_path / "final.json", 1001)

    clock.value = T_ABORT
    with pytest.raises(loop.LoopError) as held:
        loop.finish(run_dir, abort="external: テスト", finalize_result=finalize, github=github)
    assert held.value.code == 7
    run = json.loads(run_path.read_text(encoding="utf-8"))
    assert (run["state"], run["aborted_at"], run["result"]["ended_by"]) == ("held", T_ABORT, "abort")
    # held の run は照合の対象ではない
    with pytest.raises(loop.LoopError) as error:
        loop.reconcile(run_dir, finalize_result=finalize, comment_id=1001, github=github)
    assert (error.value.code, error.value.stage) == (3, "state")

    clock.value = T_LATER
    recovered = loop.recover(run_dir, operator_confirmed_stopped="ps でプロセスが残っていないことを確かめた")
    assert recovered["state"] == "ended"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    # recover は時刻を更新しない。既に結果が決まった run の再 abort も拒否する
    assert run["aborted_at"] == T_ABORT
    with pytest.raises(loop.LoopError) as error:
        loop.finish(run_dir, abort="external: 二回目", github=github)
    assert error.value.code == 3
    assert json.loads(run_path.read_text(encoding="utf-8"))["aborted_at"] == T_ABORT


# --- 実 CLI（argparse・dispatch・main の経路）の 4 ケース ----------------------------------------------------------


def cli(
    loop: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], github: Any, argv: list[str]
) -> tuple[int, dict[str, Any]]:
    monkeypatch.setattr(loop, "GitHub", lambda: github)
    capsys.readouterr()
    code = loop.main(argv)
    return code, json.loads(capsys.readouterr().out)


def reconcile_argv(scene: SimpleNamespace, **changes: Any) -> list[str]:
    values: dict[str, Any] = {
        "run": str(scene.run_dir),
        "finalize_result": str(scene.finalize),
        "comment_id": str(scene.comment_id),
    }
    values.update(changes)
    return [
        "reconcile",
        "--run",
        values["run"],
        "--finalize-result",
        values["finalize_result"],
        "--comment-id",
        values["comment_id"],
    ]


def test_cli_reconcile_success(scene: SimpleNamespace, loop: Any, monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    code, output = cli(loop, monkeypatch, capsys, scene.github, reconcile_argv(scene))
    assert code == 0
    assert output["result"]["merged"] is True and output["result"]["outcome"] == "no_fix_needed"
    assert output["reconciled"]["comment_id"] == scene.comment_id
    code, status = cli(loop, monkeypatch, capsys, scene.github, ["status", "--run", str(scene.run_dir)])
    assert code == 0
    assert status["reconciled"] is not None and status["original_result"]["ended_by"] == "abort"


def test_cli_reconcile_comment_mismatch(
    scene: SimpleNamespace, loop: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    other = scene.comment_id + 1
    bad = write_finalize(tmp_path / "other.json", other)
    code, output = cli(
        loop,
        monkeypatch,
        capsys,
        scene.github,
        reconcile_argv(scene, finalize_result=str(bad), comment_id=str(other)),
    )
    assert code == 4 and output["stage"] == "record_missing"
    assert not (scene.run_dir / "reconcile.json").exists()


def test_cli_reconcile_head_mismatch(
    scene: SimpleNamespace, loop: Any, env: Any, monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    scene.gh.gh.merged_head = env.push("サイクルの後の commit")
    code, output = cli(loop, monkeypatch, capsys, scene.github, reconcile_argv(scene))
    assert code == 4 and output["stage"] == "merge_mismatch"
    assert not (scene.run_dir / "reconcile.json").exists()


def test_cli_reconcile_existing_evidence(
    scene: SimpleNamespace, loop: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    code, _ = cli(loop, monkeypatch, capsys, scene.github, reconcile_argv(scene))
    assert code == 0
    path = scene.run_dir / "reconcile.json"
    before = path.read_bytes()
    reformatted = tmp_path / "reformatted.json"
    reformatted.write_text(json.dumps(json.loads(scene.finalize.read_text(encoding="utf-8"))), encoding="utf-8")
    code, output = cli(loop, monkeypatch, capsys, scene.github, reconcile_argv(scene, finalize_result=str(reformatted)))
    assert code == 4 and output["stage"] == "record_inconsistent"
    assert path.read_bytes() == before
