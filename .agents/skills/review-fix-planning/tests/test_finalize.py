"""PR最終化の順序と未完了判定。GitHubへの書込みはfake ghだけで行う。"""

from __future__ import annotations

import copy
import importlib.util
import json
from collections.abc import Sequence
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest

HELPER = Path(__file__).resolve().parents[1] / "scripts/finalize.py"
SPEC = importlib.util.spec_from_file_location("planning_finalize", HELPER)
assert SPEC is not None and SPEC.loader is not None
mod: Any = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

REPO = "usaturn/create-reso-world"
HEAD = "1" * 40
SPEC_HEAD = "3" * 40
PR = 900
ME = "usaturn"
# create-reso-worldの結論2でmainにマージされるのは、検証したHEADの上に載せたSpec 1ファイルだけ。
# 場所を取り違えると、確認していない変更をマージに含める
SPEC_FILE = "docs/superpowers/specs/2026-10-19-example-design.md"
# 検証したツリーが含む base（mainの先端）。偽のGitHubは、投稿の後・マージの後に先端を動かせる
BASE = "a" * 40
NEW_BASE = "b" * 40
MERGE_COMMIT = "c" * 40


def record() -> dict[str, Any]:
    return {
        "schema": "review-records/v1",
        "pr": {"repository": REPO, "number": PR},
        "round": 1,
        "reviewed_head": HEAD,
        "recorded_at": "2026-10-08T06:00:00Z",
        "planner": {"model": "fixture", "runtime": "pi", "agent_id": "fixture"},
        "seats": [
            {
                "review_file": "fixture",
                "model": "fixture",
                "runtime": "pi",
                "file_head": HEAD[:12],
                "mode": "Initial",
                "rerun": True,
                "merge_recommendation": "Approve",
            }
        ],
        "decisions": [],
        "outcome": "no_fix_needed",
    }


def checks() -> dict[str, Any]:
    return {"head": HEAD, "base": BASE, "commands": [{"argv": ["./scripts/ci/verify-devenv.sh"], "exit_code": 0}]}


PUBLIC = "usaturn/resoloop"
GREEN = {"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "SUCCESS"}
FAILED = {"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "FAILURE"}
RUNNING = {"__typename": "CheckRun", "status": "IN_PROGRESS", "conclusion": None}


def public_record() -> dict[str, Any]:
    value = record()
    value["pr"]["repository"] = PUBLIC
    return value


def status_comment(value: dict[str, Any], *, association: str = "OWNER", login: str = ME) -> dict[str, Any]:
    """helperが投稿するのと同じ形の、このサイクルの状況コメント。"""
    body = mod.poster.records.compose_comment(value, "状況")
    return {"id": 99, "body": body, "author_association": association, "user": {"login": login}}


def compare_commit(sha: str = SPEC_HEAD, parents: Sequence[str] = (HEAD,)) -> dict[str, Any]:
    return {"sha": sha, "parents": [{"sha": parent} for parent in parents]}


def compare_file(filename: str = SPEC_FILE, status: str = "added") -> dict[str, Any]:
    return {"filename": filename, "status": status}


def compare_response(**changes: Any) -> dict[str, Any]:
    """GitHubの比較の応答。検証したHEADの直接の子1 commitが、Spec 1ファイルだけを足している。"""
    value: dict[str, Any] = {
        "status": "ahead",
        "ahead_by": 1,
        "behind_by": 0,
        "commits": [compare_commit()],
        "files": [compare_file()],
    }
    value.update(changes)
    return value


class FakeGh:
    def __init__(self, *, state: str = "OPEN", repo: str = REPO) -> None:
        self.repo = repo
        self.view: dict[str, Any] = {
            "url": f"https://github.com/{repo}/pull/{PR}",
            "number": PR,
            "headRefOid": HEAD,
            "baseRefName": "main",
            "state": state,
            "isDraft": False,
            "mergeable": "MERGEABLE",
            "mergedAt": "2026-10-08T06:05:00Z" if state == "MERGED" else None,
            "statusCheckRollup": [{"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "SUCCESS"}],
            "closingIssuesReferences": [{"number": 901, "url": f"https://github.com/{repo}/issues/901"}],
        }
        self.calls: list[tuple[str, ...]] = []
        self.comments: list[dict[str, Any]] = []
        self.issue_state = "OPEN"
        self.post_fails = False
        self.issue_fails = False
        self.after_post: dict[str, Any] = {}
        self.merge_stays_open = False
        self.list_fails = False
        self.login = ME
        self.login_fails = False
        self.compare: Any = compare_response()
        self.compare_fails = False
        # baseブランチの先端（ブランチの名前ごと）。投稿の後に動かす先端、応答の差し替え、取得の失敗
        self.tips: dict[str, str] = {"main": BASE}
        self.tip_after_post: str | None = None
        self.branch: Any = None
        self.branch_fails = False
        # PRの読み取りの失敗（すべて・マージ済みの間だけ）と、マージの依頼の失敗（状態は変えない）
        self.view_fails = False
        self.confirm_fails = False
        self.merge_fails = False

    def __call__(self, args: Sequence[str], *, input_text: str | None = None) -> CompletedProcess[str]:
        argv = tuple(args)
        self.calls.append(argv)
        value: Any = None
        text: str | None = None
        code = 0
        if argv[1:3] == ("pr", "view"):
            code = 1 if self.view_fails or self.confirm_fails and self.view["state"] == "MERGED" else 0
            value = self.view
        elif argv[1:3] == ("api", "user"):
            # `gh api user --jq` は、JSONではなく login だけを出力する
            code = 1 if self.login_fails else 0
            text = f"{self.login}\n"
        elif argv[1:4] == ("api", "--paginate", "--slurp"):
            code = 1 if self.list_fails else 0
            value = self.comments
        elif argv[1:3] == ("api", "--method"):
            if self.post_fails:
                code = 1
            else:
                assert input_text is not None
                body = json.loads(input_text)["body"]
                self.comments = [{"id": 99, "body": body, "author_association": "OWNER", "user": {"login": ME}}]
                value = {"id": 99, "html_url": self.view["url"] + "#issuecomment-99"}
                self.view.update(self.after_post)
                self.after_post = {}
                if self.tip_after_post is not None:
                    self.tips[self.view["baseRefName"]] = self.tip_after_post
                    self.tip_after_post = None
        elif len(argv) == 3 and argv[1] == "api" and "/compare/" in argv[2]:
            code = 1 if self.compare_fails else 0
            value = self.compare
        elif len(argv) == 3 and argv[1] == "api" and "/branches/" in argv[2]:
            name = argv[2].split("/branches/", 1)[1]
            code = 1 if self.branch_fails or name not in self.tips else 0
            value = self.branch
            if value is None and not code:
                value = {"name": name, "commit": {"sha": self.tips[name]}, "protected": False}
        elif argv[1:3] == ("pr", "merge"):
            if self.merge_fails:
                code = 1
            elif not self.merge_stays_open:
                self.view.update(state="MERGED", mergedAt="2026-10-08T06:05:00Z")
                # GitHubはbaseブランチをマージのcommitに進める
                self.tips[self.view.get("baseRefName", "main")] = MERGE_COMMIT
            value = {}
        elif argv[1:3] == ("issue", "view"):
            value = {"url": f"https://github.com/{self.repo}/issues/901", "number": 901, "state": self.issue_state}
        elif argv[1:3] == ("issue", "close"):
            if self.issue_fails:
                code = 1
            else:
                self.issue_state = "CLOSED"
            value = {}
        else:
            raise AssertionError(argv)
        stdout = json.dumps(copy.deepcopy(value)) if text is None else text
        return CompletedProcess(list(args), code, stdout, "fake failure" if code else "")

    def writes(self) -> list[tuple[str, ...]]:
        return [call for call in self.calls if "--method" in call or call[1:3] in (("pr", "merge"), ("issue", "close"))]

    def compare_requests(self) -> list[str]:
        return [call[2] for call in self.calls if len(call) == 3 and call[1] == "api" and "/compare/" in call[2]]

    def branch_requests(self) -> list[str]:
        return [call[2] for call in self.calls if len(call) == 3 and call[1] == "api" and "/branches/" in call[2]]


@pytest.mark.parametrize("repo", [REPO, PUBLIC])
def test_no_fix_result_requires_post_merge_confirmation_and_issue_update(repo: str) -> None:
    gh = FakeGh(repo=repo)
    value = record()
    value["pr"]["repository"] = repo
    result = mod.finalize(value, "## マージ前の状況\n検証済み。追加修正なし。最終化を開始。", checks(), runner=gh)
    assert result["outcome"] == "no_fix_needed" and result["issues"] == [901]
    post, merge, issue = gh.writes()
    assert "POST" in post
    assert merge[merge.index("--match-head-commit") + 1] == HEAD
    # merge commitに固定する。repo-cleanup-after-mergeは祖先関係でマージ済みを判定し、
    # loopの最終化もmerge commitを使う。方式を変えるときはこのテストも合わせて更新する。
    assert "--merge" in merge and not {"--squash", "--rebase"} & set(merge)
    assert not {"--admin", "--auto", "--delete-branch"} & set(merge)
    assert issue[1:3] == ("issue", "close")
    assert gh.calls[-1][1:3] == ("issue", "view")


# 検証の記録のbaseが完全なSHAでない。照合できるbaseの無い記録で最終化を始めない
BAD_BASES: dict[str, Any] = {"short_base": BASE[:12], "upper_base": "A" * 40, "null_base": None}


@pytest.mark.parametrize("mutation", ["head", "missing", "failed", "bool", "no_base", *BAD_BASES])
def test_missing_or_wrong_verification_stops_before_network(mutation: str) -> None:
    evidence = checks()
    if mutation == "head":
        evidence["head"] = "2" * 40
    elif mutation == "missing":
        evidence["commands"] = []
    elif mutation == "no_base":
        del evidence["base"]
    elif mutation in BAD_BASES:
        evidence["base"] = BAD_BASES[mutation]
    else:
        evidence["commands"][0]["exit_code"] = True if mutation == "bool" else 1
    gh = FakeGh()
    result = mod.finalize(record(), "状況", evidence, runner=gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("environment:")
    # PRの状態を見ていないので、未マージ（false）とも言わない
    assert result["merged"] is None and gh.calls == []


@pytest.mark.parametrize("condition", ["draft", "moving", "mergeable", "state"])
def test_invalid_pr_state_does_not_post_or_merge(condition: str) -> None:
    gh = FakeGh()
    key, value = {
        "draft": ("isDraft", True),
        "moving": ("headRefOid", "2" * 40),
        "mergeable": ("mergeable", "CONFLICTING"),
        "state": ("state", "CLOSED"),
    }[condition]
    gh.view[key] = value
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and "wait_for" not in result
    assert gh.writes() == []


@pytest.mark.parametrize(
    "rollup",
    [
        [RUNNING],
        [{"__typename": "CheckRun", "status": "QUEUED", "conclusion": None}],
        [{"__typename": "StatusContext", "state": "PENDING"}],
        [{"__typename": "StatusContext", "state": "EXPECTED"}],
        [GREEN, RUNNING],
    ],
)
def test_public_ci_still_running_waits_and_the_rerun_finalizes(rollup: list[Any]) -> None:
    gh = FakeGh(repo=PUBLIC)
    gh.view["statusCheckRollup"] = rollup
    first = mod.finalize(public_record(), "状況", checks(), runner=gh)
    assert first["outcome"] == "stopped" and first["wait_for"] == "ci"
    assert first["stop_reason"].startswith("external:") and gh.writes() == []
    gh.view["statusCheckRollup"] = [GREEN]
    second = mod.finalize(public_record(), "状況", checks(), runner=gh)
    assert second["outcome"] == "no_fix_needed" and "wait_for" not in second
    assert [call[1:3] for call in gh.writes()] == [("api", "--method"), ("pr", "merge"), ("issue", "close")]


@pytest.mark.parametrize(
    "rollup",
    [
        [],
        [FAILED],
        [RUNNING, FAILED],
        [FAILED, RUNNING],
        [{"__typename": "StatusContext", "state": "ERROR"}],
        # GitHubの応答の値が文字列でない（リスト）。例外にも、待てば進む停止にもせず、成功ではないとして止める
        [{"__typename": "CheckRun", "status": "COMPLETED", "conclusion": ["SUCCESS"]}],
        [{"__typename": "StatusContext", "state": ["PENDING"]}],
    ],
)
def test_public_ci_failure_or_absence_stops_without_waiting(rollup: list[Any]) -> None:
    gh = FakeGh(repo=PUBLIC)
    gh.view["statusCheckRollup"] = rollup
    result = mod.finalize(public_record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("external:")
    assert "wait_for" not in result and gh.writes() == []


def test_unknown_mergeable_waits_and_the_rerun_finalizes() -> None:
    gh = FakeGh()
    gh.view["mergeable"] = "UNKNOWN"
    first = mod.finalize(record(), "状況", checks(), runner=gh)
    assert first["outcome"] == "stopped" and first["wait_for"] == "mergeable" and gh.writes() == []
    gh.view["mergeable"] = "MERGEABLE"
    second = mod.finalize(record(), "状況", checks(), runner=gh)
    assert second["outcome"] == "no_fix_needed" and second["issues"] == [901]


def test_wait_after_post_reruns_by_updating_the_same_comment() -> None:
    gh = FakeGh()
    gh.after_post = {"mergeable": "UNKNOWN"}
    first = mod.finalize(record(), "状況", checks(), runner=gh)
    assert first["outcome"] == "stopped" and first["wait_for"] == "mergeable"
    assert [call[3] for call in gh.writes()] == ["POST"]
    gh.view["mergeable"] = "MERGEABLE"
    second = mod.finalize(record(), "状況", checks(), runner=gh)
    assert second["outcome"] == "no_fix_needed" and second["comment"]["action"] == "updated"
    assert [call[3] if call[1] == "api" else call[1:3] for call in gh.writes()] == [
        "POST",
        "PATCH",
        ("pr", "merge"),
        ("issue", "close"),
    ]


def test_create_reso_world_ci_is_not_required_but_resoloop_ci_is() -> None:
    # create-reso-worldのActionsは止めているのでCI結果が無くてもよい（実際の検証は必須）。
    # resoloopは公開リポジトリなので、CI結果が無いままマージしない
    parent = FakeGh()
    parent.view["statusCheckRollup"] = []
    assert mod.finalize(record(), "状況", checks(), runner=parent)["outcome"] == "no_fix_needed"
    public = FakeGh(repo=PUBLIC)
    public.view["statusCheckRollup"] = []
    result = mod.finalize(public_record(), "状況", checks(), runner=public)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("external:")
    assert "wait_for" not in result and public.writes() == []
    public.view["statusCheckRollup"] = [GREEN]
    assert mod.finalize(public_record(), "状況", checks(), runner=public)["outcome"] == "no_fix_needed"


def test_a_repository_missing_from_the_ci_table_is_treated_as_requiring_ci() -> None:
    """知らないリポジトリのCIを免除しない。マージの範囲の検査が先に止めるので、finalize越しには届かない。"""
    with pytest.raises(mod.Stop):
        mod.check_ci({"statusCheckRollup": []}, "other/repo")


@pytest.mark.parametrize("repo", ["usaturn/resoloop-meshy", "orange3134/resoloop", "other/repo"])
def test_repository_outside_the_merge_scope_stops_before_network(repo: str) -> None:
    # マージは取り消せない。SKILL.mdの範囲（create-reso-worldとresoloop）をこのhelperでも守る。
    # resoloop-meshyはCIの表にあるが、範囲の外なのでCIを見る前に止まる
    gh = FakeGh(repo=repo)
    value = record()
    value["pr"]["repository"] = repo
    result = mod.finalize(value, "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("permission:")
    assert result["merged"] is None and gh.calls == []


def test_comment_rejection_cannot_be_bypassed_with_manual_post() -> None:
    gh = FakeGh()
    gh.post_fails = True
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped"
    assert len(gh.writes()) == 1


def test_moving_head_after_post_is_not_merged() -> None:
    gh = FakeGh()
    gh.after_post = {"headRefOid": "2" * 40}
    assert mod.finalize(record(), "状況", checks(), runner=gh)["outcome"] == "stopped"
    assert len(gh.writes()) == 1 and "POST" in gh.writes()[0]


def test_merge_command_success_without_merged_state_is_not_completion() -> None:
    gh = FakeGh()
    gh.merge_stays_open = True
    assert mod.finalize(record(), "状況", checks(), runner=gh)["outcome"] == "stopped"
    assert all(call[1:3] != ("issue", "close") for call in gh.calls)


def test_already_merged_with_this_record_posted_only_resumes_issue_updates() -> None:
    gh = FakeGh(state="MERGED")
    gh.comments = [status_comment(record())]
    assert mod.finalize(record(), "状況", checks(), runner=gh)["outcome"] == "no_fix_needed"
    assert gh.writes() == [("gh", "issue", "close", "901", "--repo", REPO)]


@pytest.mark.parametrize(
    ("association", "login", "trusted"),
    [("OWNER", "someone-else", True), ("NONE", ME, True), ("NONE", "someone-else", False)],
)
def test_posted_record_counts_only_from_a_writer_or_the_authenticated_user(
    association: str, login: str, trusted: bool
) -> None:
    gh = FakeGh(state="MERGED")
    gh.comments = [status_comment(record(), association=association, login=login)]
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["merged"] is True
    if trusted:
        assert result["outcome"] == "no_fix_needed" and result["issues"] == [901]
    else:
        assert result["outcome"] == "stopped" and result["issues"] == [] and gh.writes() == []


@pytest.mark.parametrize("posted", ["none", "stopped", "different"])
def test_merged_without_this_no_fix_record_is_stopped_but_merged(posted: str) -> None:
    gh = FakeGh(state="MERGED")
    if posted == "stopped":
        stopped = record()
        stopped.update(outcome="stopped", stop_reason="external: PRがdraftになっている")
        gh.comments = [status_comment(stopped)]
    elif posted == "different":
        # 記録ファイルを作り直した等で、PR上のno_fix_needed記録と内容が違う。
        other = record()
        other["recorded_at"] = "2026-10-08T05:59:00Z"
        gh.comments = [status_comment(other)]
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["merged"] is True and result["issues"] == []
    assert result["stop_reason"].startswith("external:") and "wait_for" not in result
    assert gh.writes() == []


@pytest.mark.parametrize("first_stop", ["mergeable", "draft", "public_ci"])
def test_manual_merge_after_a_stop_before_posting_is_not_no_fix_needed(first_stop: str) -> None:
    """投稿前に止まり、その間に同じHEADで手動マージされた。記録が無いので、no_fix_neededにしない。"""
    gh = FakeGh(repo=PUBLIC if first_stop == "public_ci" else REPO)
    value = public_record() if first_stop == "public_ci" else record()
    key, state = {
        "mergeable": ("mergeable", "UNKNOWN"),
        "draft": ("isDraft", True),
        "public_ci": ("statusCheckRollup", [RUNNING]),
    }[first_stop]
    gh.view[key] = state
    assert mod.finalize(value, "状況", checks(), runner=gh)["outcome"] == "stopped"
    gh.view.update(state="MERGED", mergedAt="2026-10-08T06:05:00Z")
    result = mod.finalize(value, "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["merged"] is True and result["issues"] == []
    assert gh.writes() == []


def test_issue_update_failure_is_reported_after_real_merge() -> None:
    gh = FakeGh()
    gh.issue_fails = True
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["merged"] is True
    assert "external:" in result["stop_reason"]


@pytest.mark.parametrize("bad_planner", [None, [], "invalid"])
def test_malformed_record_is_stopped_before_network(bad_planner: Any) -> None:
    value = record()
    value["planner"] = bad_planner
    gh = FakeGh()
    result = mod.finalize(value, "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["merged"] is None and gh.calls == []


def cli_args(tmp_path: Path, result: Path) -> list[str]:
    record_file = tmp_path / "record.json"
    record_file.write_text(json.dumps(record()))
    body_file = tmp_path / "body.md"
    body_file.write_text("マージ前の状況")
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps(checks()))
    return [
        "--record-file",
        str(record_file),
        "--body-file",
        str(body_file),
        "--checks-file",
        str(checks_file),
        "--result-file",
        str(result),
    ]


@pytest.mark.parametrize("bad", ["missing", "directory", "symlink"])
def test_unusable_result_path_stops_before_gh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    bad: str,
) -> None:
    result = tmp_path / "result.json"
    target = tmp_path / "other-session.json"
    if bad == "missing":
        result = tmp_path / "missing" / "result.json"
    elif bad == "directory":
        result.mkdir()
    else:
        target.write_text("preserve")
        result.symlink_to(target)
    gh = FakeGh()
    monkeypatch.setattr(mod.poster, "GhRunner", lambda: gh)
    assert mod.main(cli_args(tmp_path, result)) == 2
    assert gh.calls == [] and json.loads(capsys.readouterr().out)["merged"] is None
    if bad == "symlink":
        assert target.read_text() == "preserve"


def test_cli_saves_and_reports_actual_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = tmp_path / "result.json"
    result.write_text("prior result")
    gh = FakeGh()
    monkeypatch.setattr(mod.poster, "GhRunner", lambda: gh)
    assert mod.main(cli_args(tmp_path, result)) == 0
    actual = json.loads(capsys.readouterr().out)
    assert json.loads(result.read_text()) == actual
    assert actual["merged"] is True and actual["issues"] == [901]


def test_cli_exits_one_and_saves_the_result_when_stopped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = tmp_path / "result.json"
    gh = FakeGh()
    gh.view["isDraft"] = True
    monkeypatch.setattr(mod.poster, "GhRunner", lambda: gh)
    assert mod.main(cli_args(tmp_path, result)) == 1
    actual = json.loads(capsys.readouterr().out)
    assert json.loads(result.read_text()) == actual
    assert actual["outcome"] == "stopped" and actual["merged"] is False and gh.writes() == []


def test_post_operation_save_failure_preserves_observed_effects_in_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = tmp_path / "result.json"
    result.write_text("prior result")
    gh = FakeGh()
    monkeypatch.setattr(mod.poster, "GhRunner", lambda: gh)

    def failed_replace(source: Any, destination: Any) -> None:
        raise OSError("simulated result persistence failure")

    monkeypatch.setattr("os.replace", failed_replace)
    assert mod.main(cli_args(tmp_path, result)) == 2
    actual = json.loads(capsys.readouterr().out)
    assert actual["outcome"] == "stopped" and actual["merged"] is True and actual["issues"] == [901]
    assert actual["stop_reason"].startswith("environment:")
    assert result.read_text() == "prior result"


def test_known_manual_merge_is_not_lost_on_later_read_failure() -> None:
    gh = FakeGh(state="MERGED")
    gh.list_fails = True
    actual = mod.finalize(record(), "状況", checks(), runner=gh)
    assert actual["outcome"] == "stopped" and actual["merged"] is True
    assert actual["stop_reason"].startswith("external:")
    assert gh.writes() == []


OLD_HEAD = "0" * 40
FIX_ID = f"fixture#H-1@{OLD_HEAD[:12]}"


def earlier_fix_record() -> dict[str, Any]:
    """前のサイクルでfixにした判断を持つ記録。"""
    value = record()
    value.update(reviewed_head=OLD_HEAD, outcome="fixes_pushed", commit=HEAD, recorded_at="2026-10-08T05:00:00Z")
    value["seats"][0]["file_head"] = OLD_HEAD[:12]
    value["decisions"] = [
        {
            "id": FIX_ID,
            "sources": [FIX_ID],
            "summary": "空の入力で落ちる",
            "locations": ["scripts/x.py:1"],
            "state": "fix",
            "change": "new",
            "severity": "High",
            "pr_relation": "introduced",
            "reason": "H: PR が持ち込んだ検証済みの High",
        }
    ]
    return value


def test_blank_status_body_is_an_input_problem_found_before_network() -> None:
    gh = FakeGh()
    result = mod.finalize(record(), "  ", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("environment:")
    assert result["merged"] is None and gh.calls == []


def test_conflict_with_earlier_records_is_environment_and_names_the_decision() -> None:
    gh = FakeGh()
    earlier = status_comment(earlier_fix_record())
    earlier["id"] = 98
    gh.comments = [earlier]
    value = record()
    value["round"] = 2
    result = mod.finalize(value, "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("environment:")
    assert FIX_ID in result["stop_reason"]
    assert gh.writes() == []


def test_duplicate_round_comments_do_not_leak_markers_into_the_reason() -> None:
    gh = FakeGh()
    first, second = status_comment(record()), status_comment(record())
    second["id"] = 100
    gh.comments = [first, second]
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["stop_reason"].startswith("environment:")
    assert "<!--" not in result["stop_reason"] and "-->" not in result["stop_reason"]
    assert gh.writes() == []


def test_foreign_or_malformed_closing_issue_is_never_closed() -> None:
    gh = FakeGh()
    gh.view["closingIssuesReferences"] = [{"number": 901, "url": "https://github.com/other/repo/issues/901"}]
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped"
    assert all(call[1:3] != ("issue", "close") for call in gh.calls)


# --- --spec-commit（create-reso-worldの結論2） ---


def spec_gh(*, state: str = "OPEN") -> FakeGh:
    """PRのheadはSpecのcommit。このサイクルの記録は、そのcommitをpushする前に投稿済み。"""
    gh = FakeGh(state=state)
    gh.view["headRefOid"] = SPEC_HEAD
    gh.comments = [status_comment(record())]
    return gh


def finalize_spec(gh: FakeGh) -> dict[str, Any]:
    return mod.finalize(record(), "状況", checks(), runner=gh, spec_commit=SPEC_HEAD)


@pytest.mark.parametrize("state", ["OPEN", "MERGED"])
@pytest.mark.parametrize("problem", ["fails", "empty"])
@pytest.mark.parametrize("spec", [False, True])
def test_login_failure_is_external_and_does_not_post_or_merge(spec: bool, problem: str, state: str) -> None:
    gh = spec_gh(state=state) if spec else FakeGh(state=state)
    if problem == "fails":
        gh.login_fails = True
    else:
        gh.login = ""
    result = mod.finalize(record(), "状況", checks(), runner=gh, spec_commit=SPEC_HEAD if spec else None)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("external:")
    # 手でマージ済みなら、その事実は失わない
    assert result["merged"] is (state == "MERGED") and result["issues"] == []
    assert gh.writes() == []


@pytest.mark.parametrize("status", ["added", "modified"])
def test_spec_commit_merges_the_spec_head_after_the_record_was_posted(status: str) -> None:
    gh = spec_gh()
    gh.compare["files"][0]["status"] = status
    result = finalize_spec(gh)
    assert result["outcome"] == "no_fix_needed" and result["merged"] is True and result["issues"] == [901]
    assert result["spec_commit"] == SPEC_HEAD and "comment" not in result
    assert gh.compare_requests() == [f"repos/{REPO}/compare/{HEAD}...{SPEC_HEAD}"]
    # 記録は投稿済みなので投稿しない。書き込むのは、Specのcommitのマージと、Issueのcloseだけ
    merge, issue = gh.writes()
    assert merge[1:3] == ("pr", "merge") and issue[1:3] == ("issue", "close")
    assert merge[merge.index("--match-head-commit") + 1] == SPEC_HEAD
    assert "--merge" in merge and not {"--squash", "--rebase", "--admin", "--auto", "--delete-branch"} & set(merge)


# 1項目だけ変えた比較の応答。どれもマージせずにenvironmentで止まる
BAD_COMPARISONS: dict[str, Any] = {
    "not_ahead": compare_response(status="diverged"),
    "behind": compare_response(behind_by=1),
    "ahead_by_two": compare_response(ahead_by=2),
    "ahead_by_bool": compare_response(ahead_by=True),
    "two_commits": compare_response(commits=[compare_commit(), compare_commit()]),
    "no_commit": compare_response(commits=[]),
    "wrong_sha": compare_response(commits=[compare_commit(sha="4" * 40)]),
    "wrong_parent": compare_response(commits=[compare_commit(parents=["4" * 40])]),
    "merge_commit": compare_response(commits=[compare_commit(parents=[HEAD, "4" * 40])]),
    "no_parent": compare_response(commits=[compare_commit(parents=[])]),
    "two_files": compare_response(files=[compare_file(), compare_file("docs/superpowers/specs/other.md")]),
    "no_file": compare_response(files=[]),
    "renamed": compare_response(files=[compare_file(status="renamed")]),
    "removed": compare_response(files=[compare_file(status="removed")]),
    "subdirectory": compare_response(files=[compare_file("docs/superpowers/specs/draft/x.md")]),
    "other_directory": compare_response(files=[compare_file("docs/superpowers/plans/x.md")]),
    "outside_docs": compare_response(files=[compare_file(".agents/scripts/x.md")]),
    "repository_root": compare_response(files=[compare_file("README.md")]),
    "not_markdown": compare_response(files=[compare_file("docs/superpowers/specs/x.txt")]),
    "script": compare_response(files=[compare_file("docs/superpowers/specs/run.py")]),
    "not_an_object": ["ahead"],
    "no_files_key": {key: value for key, value in compare_response().items() if key != "files"},
    # 値の型が想定外（GitHubの応答が崩れた）。例外にせず、成功と見なさずに止める
    "status_list": compare_response(files=[{"filename": SPEC_FILE, "status": ["added"]}]),
    "status_object": compare_response(files=[{"filename": SPEC_FILE, "status": {}}]),
    "filename_not_a_string": compare_response(files=[{"filename": [SPEC_FILE], "status": "added"}]),
    "file_not_an_object": compare_response(files=[SPEC_FILE]),
    "commits_not_a_list": compare_response(commits={"sha": SPEC_HEAD}),
    "commit_not_an_object": compare_response(commits=[SPEC_HEAD]),
    "parents_missing": compare_response(commits=[{"sha": SPEC_HEAD}]),
    "parent_not_an_object": compare_response(commits=[{"sha": SPEC_HEAD, "parents": [HEAD]}]),
}


@pytest.mark.parametrize("mutation", list(BAD_COMPARISONS))
def test_spec_commit_compare_must_be_one_spec_file_on_the_reviewed_head(mutation: str) -> None:
    gh = spec_gh()
    gh.compare = BAD_COMPARISONS[mutation]
    result = finalize_spec(gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("environment:")
    assert result["merged"] is False and gh.writes() == []


def test_spec_commit_compare_request_failure_is_external_and_does_not_merge() -> None:
    gh = spec_gh()
    gh.compare_fails = True
    result = finalize_spec(gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("external:")
    assert gh.writes() == []


@pytest.mark.parametrize("posted", ["none", "different", "stopped", "untrusted_author"])
def test_spec_commit_requires_the_identical_record_already_posted(posted: str) -> None:
    gh = spec_gh()
    if posted == "none":
        gh.comments = []
    elif posted == "different":
        other = record()
        other["recorded_at"] = "2026-10-08T05:59:00Z"
        gh.comments = [status_comment(other)]
    elif posted == "stopped":
        stopped = record()
        stopped.update(outcome="stopped", stop_reason="external: PRがdraftになっている")
        gh.comments = [status_comment(stopped)]
    else:
        # 書き込み権限が無く、認証済みの利用者でもない投稿者の同じ記録は、投稿済みと見なさない
        gh.comments = [status_comment(record(), association="NONE", login="someone-else")]
    result = finalize_spec(gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("environment:")
    assert result["merged"] is False and gh.writes() == []


def test_spec_commit_accepts_the_record_posted_by_the_authenticated_user() -> None:
    gh = spec_gh()
    gh.comments = [status_comment(record(), association="NONE", login=ME)]
    assert finalize_spec(gh)["outcome"] == "no_fix_needed"


@pytest.mark.parametrize("bad", ["other_repo", "same_as_reviewed_head", "short_sha", "uppercase"])
def test_invalid_spec_commit_stops_before_network(bad: str) -> None:
    repo, spec_commit = REPO, SPEC_HEAD
    if bad == "other_repo":
        # マージの範囲の中でも、Specを載せるのはcreate-reso-worldのPRだけ
        repo = PUBLIC
    elif bad == "same_as_reviewed_head":
        spec_commit = HEAD
    elif bad == "short_sha":
        spec_commit = SPEC_HEAD[:12]
    else:
        spec_commit = "A" * 40
    gh = FakeGh(repo=repo)
    value = record()
    value["pr"]["repository"] = repo
    result = mod.finalize(value, "状況", checks(), runner=gh, spec_commit=spec_commit)
    expected = "permission:" if bad == "other_repo" else "environment:"
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith(expected)
    assert result["merged"] is None and gh.calls == []


def test_spec_commit_waits_until_the_pushed_spec_commit_is_the_pr_head() -> None:
    # pushの直後は、GitHubがまだ前のhead（検証したHEAD）を返すことがある（PR #192）
    gh = spec_gh()
    gh.view["headRefOid"] = HEAD
    first = finalize_spec(gh)
    assert first["outcome"] == "stopped" and first["wait_for"] == "head"
    assert first["stop_reason"].startswith("external:") and first["merged"] is False and gh.writes() == []
    gh.view["headRefOid"] = SPEC_HEAD
    assert finalize_spec(gh)["outcome"] == "no_fix_needed"


@pytest.mark.parametrize(("state", "head"), [("OPEN", "2" * 40), ("MERGED", HEAD)])
def test_spec_commit_with_another_head_stops_without_waiting(state: str, head: str) -> None:
    # headが別のcommitに動いた。または、Specのcommitのpushの前に、検証したHEADのまま手でマージされた
    gh = spec_gh(state=state)
    gh.view["headRefOid"] = head
    result = finalize_spec(gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("external:")
    assert "wait_for" not in result and gh.writes() == []
    # 止まっても、観測したマージ済みは失わない（#207）
    assert result["merged"] is (state == "MERGED")


def test_spec_commit_waits_for_mergeable_and_the_rerun_finalizes() -> None:
    gh = spec_gh()
    gh.view["mergeable"] = "UNKNOWN"
    first = finalize_spec(gh)
    assert first["outcome"] == "stopped" and first["wait_for"] == "mergeable" and gh.writes() == []
    gh.view["mergeable"] = "MERGEABLE"
    second = finalize_spec(gh)
    assert second["outcome"] == "no_fix_needed" and "wait_for" not in second and second["issues"] == [901]


def test_spec_commit_already_merged_with_the_record_posted_only_resumes_issue_updates() -> None:
    gh = spec_gh(state="MERGED")
    result = finalize_spec(gh)
    assert result["outcome"] == "no_fix_needed" and result["merged"] is True
    assert result["spec_commit"] == SPEC_HEAD and result["issues"] == [901]
    assert gh.writes() == [("gh", "issue", "close", "901", "--repo", REPO)]


def test_spec_commit_merged_without_the_record_is_stopped_but_merged() -> None:
    gh = spec_gh(state="MERGED")
    gh.comments = []
    result = finalize_spec(gh)
    assert result["outcome"] == "stopped" and result["merged"] is True and result["issues"] == []
    assert result["stop_reason"].startswith("external:") and gh.writes() == []


def test_spec_commit_merged_with_a_changed_diff_is_not_completed() -> None:
    # 手でマージ済みでも、検証したHEADの上のSpec 1ファイルだけの変更かを確かめる
    gh = spec_gh(state="MERGED")
    gh.compare = BAD_COMPARISONS["two_files"]
    result = finalize_spec(gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("environment:")
    assert result["merged"] is True and result["issues"] == [] and gh.writes() == []


def test_cli_spec_commit_merges_the_spec_head_and_reports_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = tmp_path / "result.json"
    gh = spec_gh()
    monkeypatch.setattr(mod.poster, "GhRunner", lambda: gh)
    assert mod.main([*cli_args(tmp_path, result), "--spec-commit", SPEC_HEAD]) == 0
    actual = json.loads(capsys.readouterr().out)
    assert json.loads(result.read_text()) == actual
    assert actual["outcome"] == "no_fix_needed" and actual["spec_commit"] == SPEC_HEAD
    assert [call[1:3] for call in gh.writes()] == [("pr", "merge"), ("issue", "close")]


# --- 検証したbaseの照合 ---


def finalize_with(gh: FakeGh, spec: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return mod.finalize(record(), "状況", evidence, runner=gh, spec_commit=SPEC_HEAD if spec else None)


@pytest.mark.parametrize("spec", [False, True])
def test_base_moved_after_verification_is_not_merged_until_the_new_base_is_verified(spec: bool) -> None:
    """検証の後に別のPRがマージされた。検証していない組み合わせをマージせず、新しい先端の検証を求める。"""
    gh = spec_gh() if spec else FakeGh()
    gh.tips["main"] = NEW_BASE
    # PRのbaseRefOidはbaseブランチの先端に追従しない。検証したbaseのままでも、ブランチの先端で判定する
    gh.view["baseRefOid"] = BASE
    first = finalize_with(gh, spec, checks())
    assert first["outcome"] == "stopped" and first["merged"] is False and "wait_for" not in first
    assert first["stop_reason"].startswith("external:")
    assert first["base_moved"] == {"ref": "main", "verified": BASE, "current": NEW_BASE}
    # 投稿もマージもしない（--spec-commitが無い経路は、投稿の前に照合する）
    assert gh.writes() == [] and gh.branch_requests() == [f"repos/{REPO}/branches/main"]
    # 新しい先端をheadにmergeしたツリーで検証し直した記録なら、同じ判断の記録でマージする
    second = finalize_with(gh, spec, {**checks(), "base": NEW_BASE})
    assert second["outcome"] == "no_fix_needed" and second["merged"] is True and "base_moved" not in second
    posted = [] if spec else [("api", "--method")]
    assert [call[1:3] for call in gh.writes()] == [*posted, ("pr", "merge"), ("issue", "close")]


def test_base_moved_after_posting_is_not_merged_and_the_rerun_updates_the_comment() -> None:
    gh = FakeGh()
    gh.tip_after_post = NEW_BASE
    first = mod.finalize(record(), "状況", checks(), runner=gh)
    assert first["outcome"] == "stopped" and first["merged"] is False
    assert first["base_moved"] == {"ref": "main", "verified": BASE, "current": NEW_BASE}
    assert [call[3] for call in gh.writes()] == ["POST"]
    second = mod.finalize(record(), "状況", {**checks(), "base": NEW_BASE}, runner=gh)
    assert second["outcome"] == "no_fix_needed" and second["comment"]["action"] == "updated"
    assert [call[3] if call[1] == "api" else call[1:3] for call in gh.writes()] == [
        "POST",
        "PATCH",
        ("pr", "merge"),
        ("issue", "close"),
    ]


@pytest.mark.parametrize("spec", [False, True])
def test_rerun_after_the_merge_does_not_compare_the_moved_base(spec: bool) -> None:
    """マージの後はbaseの先端がマージのcommitに進む。Issueの更新をやり直す再実行を、baseの照合で止めない。"""
    gh = spec_gh() if spec else FakeGh()
    gh.issue_fails = True
    first = finalize_with(gh, spec, checks())
    assert first["outcome"] == "stopped" and first["merged"] is True and gh.tips["main"] == MERGE_COMMIT
    gh.issue_fails = False
    requests = len(gh.branch_requests())
    second = finalize_with(gh, spec, checks())
    assert second["outcome"] == "no_fix_needed" and second["issues"] == [901]
    assert len(gh.branch_requests()) == requests


# baseブランチの応答が想定と違う。どれも先端を確認できないとして、マージせずに止まる
UNREADABLE_BASES: dict[str, Any] = {
    # 改名したブランチのリダイレクトなど、問い合わせたのと別のブランチの応答
    "renamed": {"name": "trunk", "commit": {"sha": BASE}, "protected": False},
    "short_sha": {"name": "main", "commit": {"sha": BASE[:12]}, "protected": False},
    "no_commit": {"name": "main", "protected": False},
    "not_an_object": ["main"],
}


@pytest.mark.parametrize("problem", [*UNREADABLE_BASES, "request_fails", "no_base_ref", "blank_base_ref"])
@pytest.mark.parametrize("spec", [False, True])
def test_unreadable_base_tip_stops_without_merging(spec: bool, problem: str) -> None:
    gh = spec_gh() if spec else FakeGh()
    if problem == "request_fails":
        gh.branch_fails = True
    elif problem == "no_base_ref":
        del gh.view["baseRefName"]
    elif problem == "blank_base_ref":
        gh.view["baseRefName"] = ""
    else:
        gh.branch = UNREADABLE_BASES[problem]
    result = finalize_with(gh, spec, checks())
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("external:")
    assert result["merged"] is False and "base_moved" not in result and gh.writes() == []


def test_base_branch_name_with_a_slash_is_read_whole() -> None:
    gh = FakeGh()
    gh.view["baseRefName"] = "release/1.0"
    gh.tips = {"release/1.0": BASE}
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "no_fix_needed" and result["merged"] is True
    assert gh.branch_requests()[0] == f"repos/{REPO}/branches/release/1.0"


def test_retargeted_base_is_compared_with_the_new_base_branch() -> None:
    """検証の後にPRのbaseを別のブランチに変えた。変えた先のブランチの先端と照合する。"""
    gh = FakeGh()
    gh.view["baseRefName"] = "develop"
    gh.tips["develop"] = NEW_BASE
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["merged"] is False
    assert result["base_moved"] == {"ref": "develop", "verified": BASE, "current": NEW_BASE}
    assert gh.writes() == []


# --- 観測したマージ状態（#207） ---
# merged は、finalizeが最後に観測したPRの状態。止まってもマージ済みの事実を失わず、
# 確かめていないとき（マージを依頼した後に読めないなど）は未マージ（false）と言わずにNoneを返す


def written(gh: FakeGh) -> list[Any]:
    return [call[3] if call[1] == "api" else call[1:3] for call in gh.writes()]


@pytest.mark.parametrize(
    ("spec", "head"),
    [(False, "2" * 40), (True, "2" * 40), (True, HEAD)],
    ids=["another_head", "spec_another_head", "spec_parent"],
)
def test_merged_with_another_head_keeps_the_merge(spec: bool, head: str) -> None:
    """検証したのと別のheadで、既にマージされていた。止まるが、マージ済みは報告する。"""
    gh = spec_gh(state="MERGED") if spec else FakeGh(state="MERGED")
    gh.view["headRefOid"] = head
    result = finalize_with(gh, spec, checks())
    assert result["outcome"] == "stopped" and result["merged"] is True and result["issues"] == []
    assert result["stop_reason"].startswith("external:") and "wait_for" not in result
    assert gh.writes() == []
    # openのままheadが動いた停止（新しいheadでやり直せる）とは、停止理由で区別できる
    moved = spec_gh() if spec else FakeGh()
    moved.view["headRefOid"] = "2" * 40
    assert finalize_with(moved, spec, checks())["stop_reason"] != result["stop_reason"]


def test_spec_parent_merge_is_reported_apart_from_an_unverified_head() -> None:
    """Specのcommitを載せる前に、検証したHEADのまま手でマージされた。入ったのは検証済みのコードで、欠けたのはSpecだけ。

    検証していないheadのマージと同じ停止理由にすると、読んだ人が検証していないコードが入ったと受け取る。
    """
    parent = spec_gh(state="MERGED")
    parent.view["headRefOid"] = HEAD
    other = spec_gh(state="MERGED")
    other.view["headRefOid"] = "2" * 40
    at_parent, elsewhere = finalize_spec(parent), finalize_spec(other)
    assert at_parent["merged"] is True and elsewhere["merged"] is True
    assert at_parent["stop_reason"].startswith("external:") and parent.writes() == []
    assert at_parent["stop_reason"] != elsewhere["stop_reason"]


def test_manual_merge_with_another_head_after_posting_keeps_the_merge() -> None:
    """状況を投稿した後、マージの直前の確認までに、別のheadで手でマージされた。"""
    gh = FakeGh()
    gh.after_post = {"headRefOid": "2" * 40, "state": "MERGED", "mergedAt": "2026-10-08T06:05:00Z"}
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["merged"] is True and result["issues"] == []
    assert result["stop_reason"].startswith("external:")
    assert written(gh) == ["POST"]


def test_failed_confirmation_after_the_merge_is_unconfirmed_and_the_rerun_recovers() -> None:
    """マージは成功したが、直後の確認の読み取りだけが失敗した。未マージとは言わず、再実行で読み直して完了する。"""
    gh = FakeGh()
    gh.confirm_fails = True
    first = mod.finalize(record(), "状況", checks(), runner=gh)
    assert first["outcome"] == "stopped" and first["merged"] is None and first["issues"] == []
    assert first["stop_reason"].startswith("external:")
    assert written(gh) == ["POST", ("pr", "merge")] and gh.view["state"] == "MERGED"
    gh.confirm_fails = False
    second = mod.finalize(record(), "状況", checks(), runner=gh)
    assert second["outcome"] == "no_fix_needed" and second["merged"] is True and second["issues"] == [901]
    # 2回目はマージも投稿もしない。Issueの更新だけを続ける
    assert written(gh) == ["POST", ("pr", "merge"), ("issue", "close")]


def test_failed_merge_request_is_unconfirmed_and_the_rerun_recovers() -> None:
    """マージの依頼が失敗を返した。GitHubが処理したかは分からないので未確認とし、再実行で読み直す。"""
    gh = FakeGh()
    gh.merge_fails = True
    first = mod.finalize(record(), "状況", checks(), runner=gh)
    assert first["outcome"] == "stopped" and first["merged"] is None
    assert all(call[1:3] != ("issue", "close") for call in gh.calls)
    gh.merge_fails = False
    second = mod.finalize(record(), "状況", checks(), runner=gh)
    assert second["outcome"] == "no_fix_needed" and second["merged"] is True and second["issues"] == [901]


@pytest.mark.parametrize("problem", ["request_fails", "unknown_state"])
def test_unreadable_pr_state_is_unconfirmed(problem: str) -> None:
    gh = FakeGh()
    if problem == "request_fails":
        gh.view_fails = True
    else:
        gh.view["state"] = "UNKNOWN"
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["merged"] is None
    assert result["stop_reason"].startswith("external:") and gh.writes() == []
