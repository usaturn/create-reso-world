from __future__ import annotations

import hashlib
import importlib.util
import json
from collections.abc import Sequence
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest

HELPER = Path(__file__).resolve().parents[1] / "scripts" / "upsert_pr_comment.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
RECORDS_MODULE = REPO_ROOT / ".agents/scripts/review_records.py"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = load_module("upsert_pr_comment", HELPER)
# 記録の組み立てと読み戻しに使う、テスト自身の review_records。helper が読む module の場所は別のテストで確かめる
records: Any = load_module("review_records", RECORDS_MODULE)

MODEL = "claude-opus-5-5"
AGENT_MARKER = f"<!-- review-fix-planning:agent:{MODEL} -->"
REPO = "usaturn/create-reso-world"
PR = 485
HEAD_1 = "1" * 40
HEAD_2 = "2" * 40
COMMIT = "3" * 40
PR_URL = f"https://github.com/{REPO}/pull/{PR}"
ME = "usaturn"  # 偽の gh が `gh api user` で返す、認証済み利用者の login
OTHER = "someone-else"
BODY = "## review-fix-planning（claude-opus-5-5）\n\n### レビュー状況\n- ok\n\n### 作業判断\n- ok\n\n### 作業結果\n- ok"


class FakeGh:
    def __init__(
        self,
        *,
        pr_view: dict[str, Any] | None = None,
        comments: Any = None,
        upsert_response: dict[str, Any] | None = None,
        login: str = f"{ME}\n",
        login_fails: bool = False,
    ) -> None:
        self.pr_view = pr_view or {}
        self.comments = [] if comments is None else comments
        self.upsert_response = upsert_response or {"id": 99, "html_url": f"{PR_URL}#issuecomment-99"}
        self.login = login
        self.login_fails = login_fails
        self.calls: list[tuple[tuple[str, ...], str | None]] = []

    def __call__(
        self,
        args: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CompletedProcess[str]:
        argv = tuple(args)
        self.calls.append((argv, input_text))
        if argv[1:3] == ("pr", "view"):
            return CompletedProcess(list(args), 0, json.dumps(self.pr_view), "")
        if argv[1:3] == ("api", "user"):
            if self.login_fails:
                return CompletedProcess(list(args), 1, "", "HTTP 401: Bad credentials")
            return CompletedProcess(list(args), 0, self.login, "")
        if argv[1:4] == ("api", "--paginate", "--slurp"):
            return CompletedProcess(list(args), 0, json.dumps(self.comments), "")
        if argv[1:3] == ("api", "--method"):
            return CompletedProcess(list(args), 0, json.dumps(self.upsert_response), "")
        return CompletedProcess(list(args), 1, "", f"unexpected gh args: {argv}")

    def writes(self) -> list[tuple[tuple[str, ...], str | None]]:
        return [call for call in self.calls if "--method" in call[0]]

    def operations(self) -> list[str]:
        """gh を呼んだ順に、操作の種類を並べる。"""
        kinds = {
            ("pr", "view"): "pr view",
            ("api", "user"): "login",
            ("api", "--paginate"): "comments",
            ("api", "--method"): "write",
        }
        return [kinds.get(call[0][1:3], "unexpected") for call in self.calls]

    def view_fields(self) -> str:
        argv = next(call[0] for call in self.calls if call[0][1:3] == ("pr", "view"))
        return argv[argv.index("--json") + 1]


def pr_view(*, head: str = HEAD_1, state: str = "OPEN") -> dict[str, Any]:
    return {"url": PR_URL, "number": PR, "headRefOid": head, "state": state}


def comment(comment_id: int, body: str, association: str = "OWNER", login: str = ME) -> dict[str, Any]:
    """gh api が返すコメントの形。"""
    return {"id": comment_id, "body": body, "user": {"login": login}, "author_association": association}


def normalized(*raw: dict[str, Any]) -> list[dict[str, Any]]:
    """list_comments が返す形（id・body・author・author_association）にそろえる。"""
    return records.comments_from_api(list(raw))


def seat(head: str) -> dict[str, Any]:
    return {
        "review_file": MODEL,
        "model": MODEL,
        "runtime": "claude-code",
        "file_head": head[:12],
        "mode": "Initial",
        "rerun": True,
        "merge_recommendation": "Request changes",
    }


def decision(ref: str, state: str, change: str = "new", **extra: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "id": ref,
        "sources": [ref],
        "summary": "空の入力で export が落ちる",
        "locations": ["src/export.py:10"],
        "state": state,
        "change": change,
        "severity": "High",
        "pr_relation": "introduced",
        "reason": "H: PR が持ち込んだ検証済みの High",
    }
    if state == "skip":
        value["revisit_when"] = "利用者が指定したとき"
    value.update(extra)
    return value


def record(
    round_number: int = 1,
    *,
    head: str = HEAD_1,
    outcome: str = "no_fix_needed",
    decisions: list[dict[str, Any]] | None = None,
    model: str = MODEL,
    **extra: Any,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema": "review-records/v1",
        "pr": {"repository": REPO, "number": PR},
        "round": round_number,
        "reviewed_head": head,
        "recorded_at": f"2026-10-03T0{round_number}:00:00Z",
        "planner": {"model": model, "runtime": "claude-code", "agent_id": records.agent_id_for(model)},
        "seats": [seat(head)],
        "decisions": decisions or [],
        "outcome": outcome,
    }
    value.update(extra)
    return value


FIX_REF = f"{MODEL}#H-1@{HEAD_1[:12]}"


def awaiting_record() -> dict[str, Any]:
    return record(outcome="awaiting_approval", decisions=[decision(FIX_REF, "fix")])


def pushed_record() -> dict[str, Any]:
    return record(outcome="fixes_pushed", decisions=[decision(FIX_REF, "fix")], commit=COMMIT)


def status_comment(
    comment_id: int, value: dict[str, Any], association: str = "OWNER", login: str = ME
) -> dict[str, Any]:
    return comment(comment_id, records.compose_comment(value, BODY), association, login)


def post(gh: FakeGh, mode: str) -> dict[str, Any]:
    """mode が records なら記録付きの投稿、record-less なら記録なしの投稿。"""
    if mode == "records":
        return mod.upsert(PR, REPO, MODEL, BODY, runner=gh, record=awaiting_record())
    return mod.upsert(PR, REPO, MODEL, BODY, runner=gh)


# --- agent id と、共有する記録の module ---




def test_agent_id_comes_from_the_shared_module_whatever_the_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # helper は自分のファイルの位置から review_records を読み、cwd に頼らない
    monkeypatch.chdir(tmp_path)
    helper = load_module("upsert_pr_comment_elsewhere", HELPER)
    assert Path(helper.records.__file__).resolve() == RECORDS_MODULE.resolve()
    for model in ("Cursor Grok 4.6", "opencode/deepseek-v4-flash-free", "foo--bar", MODEL):
        assert helper.sanitize_agent_id(model) == records.agent_id_for(model)
    with pytest.raises(helper.CommentError, match="safe agent id"):
        helper.sanitize_agent_id("bad<!--model")


def test_record_less_upsert_keeps_extended_model_comments_apart() -> None:
    model = "deepseek-v4.1-flash:1017[1m]"
    digest = hashlib.sha256(model.encode("utf-8")).hexdigest()
    marker = f"<!-- review-fix-planning:agent:model--{digest} -->"
    other = comment(41, f"{AGENT_MARKER}\nold")

    first = FakeGh(pr_view=pr_view(), comments=[other])
    assert mod.upsert(PR, REPO, model, BODY, runner=first)["action"] == "created"
    (argv, payload), *_ = first.writes()
    assert argv[3] == "POST"
    created_body = json.loads(payload or "")["body"]
    assert created_body.split("\n")[0] == marker

    second = FakeGh(pr_view=pr_view(), comments=[other, comment(99, created_body)])
    assert mod.upsert(PR, REPO, model, BODY, runner=second)["action"] == "updated"
    (argv, _payload), *_ = second.writes()
    assert argv[3:5] == ("PATCH", f"repos/{REPO}/issues/comments/99")
    assert all("/41" not in argument for argument in argv)


# --- 記録なしの本文 ---








@pytest.mark.parametrize(
    "markdown",
    [
        "<!-- review-fix-planning:round:1:" + HEAD_1 + " -->\n### レビュー状況",
        "### レビュー状況\n<!-- review-records:v1:start -->\n```json\n{}\n```\n<!-- review-records:v1:end -->",
    ],
)
def test_record_less_body_rejects_round_markers_and_records_blocks(markdown: str) -> None:
    with pytest.raises(mod.CommentError, match="records post"):
        mod.compose_body("claude-opus-5", markdown)
    gh = FakeGh(pr_view=pr_view())
    with pytest.raises(mod.CommentError, match="records post"):
        mod.upsert(PR, REPO, "claude-opus-5", markdown, runner=gh)
    assert gh.calls == [], "the body is checked before any gh call"


# --- 自分の記録なしのコメントを探す ---


def test_find_own_comment_ignores_other_agents_and_rejects_duplicates() -> None:
    comments = normalized(
        comment(1, "<!-- review-fix-planning:agent:composer-2 -->\nnope"),
        comment(2, "<!-- review-fix-planning:agent:claude-opus-5 -->\nmine"),
        comment(3, "review-fix-planning without a marker"),
    )
    assert mod.find_own_comment_id(comments, "claude-opus-5", ME) == 2
    assert mod.find_own_comment_id(comments[:1], "claude-opus-5", ME) is None
    with pytest.raises(mod.CommentError, match="multiple comments"):
        mod.find_own_comment_id(comments + [comments[1]], "claude-opus-5", ME)


def test_find_own_comment_matches_the_marker_as_a_whole_first_line() -> None:
    marker = "<!-- review-fix-planning:agent:claude-opus-5 -->"
    round_marker = records.round_marker(1, HEAD_1)
    comments = normalized(
        comment(1, f"{marker} 末尾に文字がある"),
        comment(2, f"本文\n{marker}"),
        comment(3, f"人の補足。マーカーを引用する: {marker}"),
        comment(4, f"{marker}\n{round_marker}\n## 記録付きのサイクル"),
        comment(5, f"{marker}\r\nCRLF の本文"),
    )
    assert mod.find_own_comment_id(comments, "claude-opus-5", ME) == 5
    assert mod.find_own_comment_id(comments[:4], "claude-opus-5", ME) is None


def test_find_round_comment_matches_both_marker_lines_exactly() -> None:
    value = awaiting_record()
    other_agent = "<!-- review-fix-planning:agent:gpt-6 -->"
    round_line = records.round_marker(1, HEAD_1)
    comments = normalized(
        comment(1, f"{AGENT_MARKER}\n{round_line} 末尾に文字がある"),
        comment(2, f"{AGENT_MARKER}\n{records.round_marker(1, HEAD_2)}\n本文"),
        comment(3, f"{AGENT_MARKER}\n{records.round_marker(2, HEAD_1)}\n本文"),
        comment(4, f"{other_agent}\n{round_line}\n本文"),
        comment(5, f"本文\n{AGENT_MARKER}\n{round_line}"),
        comment(6, f"{AGENT_MARKER}\r\n{round_line}\r\n本文"),
    )
    assert mod.find_round_comment_id(comments, value, ME) == 6
    assert mod.find_round_comment_id(comments[:5], value, ME) is None


@pytest.mark.parametrize(
    ("association", "author", "login", "trusted"),
    [
        ("OWNER", OTHER, ME, True),
        ("CONTRIBUTOR", ME, ME, True),
        ("CONTRIBUTOR", OTHER, ME, False),
        ("NONE", OTHER, ME, False),
        # login は完全一致で比べる。大文字小文字を同一視しない
        ("CONTRIBUTOR", "Usaturn", "usaturn", False),
        # 投稿者の login が空・login の指定が空でも、空どうしで信頼しない
        ("CONTRIBUTOR", "", "", False),
    ],
)
def test_only_trusted_authors_are_matched(association: str, author: str, login: str, trusted: bool) -> None:
    own = normalized(comment(41, f"{AGENT_MARKER}\nold", association, author))
    assert mod.find_own_comment_id(own, MODEL, login) == (41 if trusted else None)
    round_comments = normalized(status_comment(41, awaiting_record(), association, author))
    assert mod.find_round_comment_id(round_comments, awaiting_record(), login) == (41 if trusted else None)


# --- 記録なしの投稿 ---








def test_upsert_stops_when_gh_resolves_a_different_repository() -> None:
    """A PR number alone is ambiguous: #7 exists in both the fork and upstream."""
    gh = FakeGh(
        pr_view={
            "url": "https://github.com/usaturn/resoloop/pull/7",
            "number": 7,
        },
        comments=[],
        upsert_response={"id": 12, "html_url": ""},
    )
    with pytest.raises(mod.CommentError, match="usaturn/resoloop"):
        mod.upsert(7, "orange3134/resoloop", "claude-opus-5", "### レビュー状況\n- ok", runner=gh)
    assert not gh.writes()
    assert gh.operations() == ["pr view"]






def test_record_less_upsert_updates_own_login_comment_and_ignores_untrusted() -> None:
    # CONTRIBUTOR でも認証済み利用者自身のコメントは更新する。別の CONTRIBUTOR の同じマーカーは更新しない
    mine = comment(41, f"{AGENT_MARKER}\nold", "CONTRIBUTOR", ME)
    theirs = comment(42, f"{AGENT_MARKER}\nforged", "CONTRIBUTOR", OTHER)

    def run(*comments: dict[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
        gh = FakeGh(pr_view=pr_view(), comments=list(comments))
        result = mod.upsert(PR, REPO, MODEL, BODY, runner=gh)
        return result, gh.writes()[0][0]

    result, argv = run(mine)
    assert result["action"] == "updated"
    assert argv[3:5] == ("PATCH", f"repos/{REPO}/issues/comments/41")

    result, argv = run(theirs)
    assert result["action"] == "created"
    assert argv[3] == "POST"

    # 信頼しない投稿者が同じマーカーを足しても、更新は止まらず、自分のコメントを更新する
    result, argv = run(theirs, mine)
    assert result["action"] == "updated"
    assert argv[3:5] == ("PATCH", f"repos/{REPO}/issues/comments/41")




def test_comments_are_read_from_every_slurped_page() -> None:
    gh = FakeGh(
        pr_view=pr_view(),
        comments=[[comment(1, "別の話題")], [comment(2, "別の話題"), comment(41, f"{AGENT_MARKER}\nold")]],
    )
    result = mod.upsert(PR, REPO, MODEL, BODY, runner=gh)
    assert result["action"] == "updated"
    assert gh.writes()[0][0][4] == f"repos/{REPO}/issues/comments/41"


def test_a_malformed_comments_payload_stops_before_any_write() -> None:
    gh = FakeGh(pr_view=pr_view(), comments={"message": "Not Found"})
    with pytest.raises(mod.CommentError, match="Not Found"):
        mod.upsert(PR, REPO, MODEL, BODY, runner=gh)
    assert not gh.writes()


# --- 認証済みの login ---


def test_authenticated_login_strips_newline_and_rejects_blank() -> None:
    # gh の --jq の出力の末尾の改行を含めない。空・空白だけ・失敗は止まる
    gh = FakeGh(login="usaturn\n")
    assert mod.authenticated_login(gh) == "usaturn"
    # 信頼する投稿者は gh の認証先で決まる。PR の作者などを問い合わせると、別の利用者を信頼してしまう
    assert gh.calls[0][0] == ("gh", "api", "user", "--jq", ".login // empty")
    for bad in (FakeGh(login=""), FakeGh(login="  \n"), FakeGh(login_fails=True)):
        with pytest.raises(mod.CommentError, match="authenticated login"):
            mod.authenticated_login(bad)






@pytest.mark.parametrize("mode", ["record-less", "records"])
def test_login_failure_stops_before_any_comment_write(mode: str) -> None:
    gh = FakeGh(pr_view=pr_view(), comments=[], login_fails=True)
    with pytest.raises(mod.CommentError, match="authenticated login"):
        post(gh, mode)
    assert not gh.writes()
    assert gh.operations() == ["pr view", "login"], "no comment is listed once the login is unknown"


# --- review-records の記録付きの投稿（.agents/review-records.md 7.4） ---


def assert_rejected(
    gh: FakeGh,
    value: dict[str, Any],
    match: str,
    *,
    model: str = MODEL,
    body: str = BODY,
    operations: list[str] | None = None,
) -> None:
    with pytest.raises(mod.CommentError, match=match):
        mod.upsert(PR, REPO, model, body, runner=gh, record=value)
    assert not gh.writes(), "a rejected records post must not fall back to any other write"
    if operations is not None:
        assert gh.operations() == operations


def test_records_post_creates_a_round_comment() -> None:
    gh = FakeGh(pr_view=pr_view(), comments=[comment(5, f"{AGENT_MARKER}\nold")])
    value = awaiting_record()
    result = mod.upsert(PR, REPO, MODEL, BODY, runner=gh, record=value)
    assert result["action"] == "created"
    (argv, payload), *_ = gh.writes()
    assert argv[3] == "POST"
    body = json.loads(payload or "")["body"]
    lines = body.split("\n")
    assert lines[0] == AGENT_MARKER
    assert lines[1] == f"<!-- review-fix-planning:round:1:{HEAD_1} -->"
    assert records.extract_record(body) == value
    assert "headRefOid" in gh.view_fields()


def test_records_post_updates_the_same_round_after_the_push() -> None:
    gh = FakeGh(pr_view=pr_view(head=COMMIT), comments=[status_comment(7, awaiting_record())])
    result = mod.upsert(PR, REPO, MODEL, BODY, runner=gh, record=pushed_record())
    assert result["action"] == "updated"
    (argv, payload), *_ = gh.writes()
    assert argv[3:5] == ("PATCH", f"repos/{REPO}/issues/comments/7")
    assert records.extract_record(json.loads(payload or "")["body"])["outcome"] == "fixes_pushed"




def test_records_post_creates_a_new_comment_for_the_next_round() -> None:
    first = pushed_record()
    second = record(
        2,
        head=COMMIT,
        decisions=[decision(FIX_REF, "resolved", change="changed", previous_state="fix")],
    )
    gh = FakeGh(
        pr_view=pr_view(head=COMMIT),
        comments=[
            status_comment(7, first),
            comment(8, f"{AGENT_MARKER}\nlegacy"),
            comment(9, "<!-- review-fix-planning:agent:pr-review-loop -->\nloop progress"),
        ],
    )
    result = mod.upsert(PR, REPO, MODEL, BODY, runner=gh, record=second)
    assert result["action"] == "created"
    assert [call[0][3] for call in gh.writes()] == ["POST"]






def test_records_post_updates_own_contributor_round_comment_and_ignores_forged_ones() -> None:
    # 上流の PR では、利用者自身が CONTRIBUTOR になる。自分の同じサイクルのコメントは更新し、
    # 別の CONTRIBUTOR のものは更新も照合もしない
    mine = status_comment(7, awaiting_record(), "CONTRIBUTOR", ME)
    forged = status_comment(8, awaiting_record(), "CONTRIBUTOR", OTHER)

    gh = FakeGh(pr_view=pr_view(head=COMMIT), comments=[forged, mine])
    result = mod.upsert(PR, REPO, MODEL, BODY, runner=gh, record=pushed_record())
    assert result["action"] == "updated"
    assert gh.writes()[0][0][3:5] == ("PATCH", f"repos/{REPO}/issues/comments/7")

    gh = FakeGh(pr_view=pr_view(head=COMMIT), comments=[forged])
    result = mod.upsert(PR, REPO, MODEL, BODY, runner=gh, record=pushed_record())
    assert result["action"] == "created"
    assert gh.writes()[0][0][3] == "POST"


def test_records_post_reads_prior_round_written_by_own_contributor_login() -> None:
    # 上流の PR（usaturn が CONTRIBUTOR）で、前のサイクルの自分の記録を照合に使う（#169）
    resolved = record(2, head=COMMIT, decisions=[decision(FIX_REF, "resolved", change="changed", previous_state="fix")])
    prior = [status_comment(7, pushed_record(), "CONTRIBUTOR", ME)]
    gh = FakeGh(pr_view=pr_view(head=COMMIT), comments=prior)
    assert mod.upsert(PR, REPO, MODEL, BODY, runner=gh, record=resolved)["action"] == "created"
    # 前のサイクルの fix の判断を落とした記録は、照合で拒否される
    gh = FakeGh(pr_view=pr_view(head=COMMIT), comments=prior)
    assert_rejected(gh, record(2, head=COMMIT), "earlier state is fix")


def test_records_post_does_not_read_rounds_of_other_contributors() -> None:
    # 別の CONTRIBUTOR の記録は、履歴として読まず、自分のサイクルの更新も止めない
    resolved = record(2, head=COMMIT, decisions=[decision(FIX_REF, "resolved", change="changed", previous_state="fix")])
    gh = FakeGh(pr_view=pr_view(head=COMMIT), comments=[status_comment(7, pushed_record(), "CONTRIBUTOR", OTHER)])
    assert_rejected(gh, resolved, "not in the earlier records")
    # 偽の「後のサイクル」を足されても、自分のサイクル 1 を更新できる
    forged_later = status_comment(8, resolved, "CONTRIBUTOR", OTHER)
    gh = FakeGh(pr_view=pr_view(head=COMMIT), comments=[status_comment(7, awaiting_record()), forged_later])
    assert mod.upsert(PR, REPO, MODEL, BODY, runner=gh, record=pushed_record())["action"] == "updated"
    assert gh.writes()[0][0][3:5] == ("PATCH", f"repos/{REPO}/issues/comments/7")




def test_records_post_rejects_a_different_model_name_before_any_gh_call() -> None:
    gh = FakeGh(pr_view=pr_view(), comments=[])
    assert_rejected(gh, awaiting_record(), "--model-name", model="other-model", operations=[])


def test_records_post_rejects_a_record_for_another_pull_request() -> None:
    value = awaiting_record()
    value["pr"] = {"repository": REPO, "number": 999}
    assert_rejected(FakeGh(pr_view=pr_view(), comments=[]), value, "pull request", operations=["pr view"])


@pytest.mark.parametrize(
    ("value", "head"),
    [
        (awaiting_record(), HEAD_2),
        (pushed_record(), HEAD_1),
    ],
)
def test_records_post_requires_the_pull_request_head(value: dict[str, Any], head: str) -> None:
    assert_rejected(FakeGh(pr_view=pr_view(head=head), comments=[]), value, "head", operations=["pr view"])


def test_records_post_rejects_a_closed_pull_request() -> None:
    # MERGED は test_finalize.py の同じ head の手動マージの例が確かめる。CLOSED は他に無い
    gh = FakeGh(pr_view=pr_view(state="CLOSED"), comments=[])
    assert_rejected(gh, awaiting_record(), "not open", operations=["pr view"])


def test_records_post_stops_when_another_agent_recorded_the_round() -> None:
    other = awaiting_record()
    other["planner"] = {"model": "gpt-6", "runtime": "codex", "agent_id": "gpt-6"}
    gh = FakeGh(pr_view=pr_view(), comments=[status_comment(7, other)])
    assert_rejected(gh, awaiting_record(), "already recorded")


def test_records_post_stops_when_a_later_round_exists() -> None:
    later = record(2, head=COMMIT, decisions=[decision(FIX_REF, "resolved", change="changed", previous_state="fix")])
    gh = FakeGh(pr_view=pr_view(head=COMMIT), comments=[status_comment(7, pushed_record()), status_comment(8, later)])
    assert_rejected(gh, pushed_record(), "can no longer be updated")




def test_records_post_rejects_no_fix_needed_with_pending_decisions() -> None:
    held = record(outcome="awaiting_approval", decisions=[decision(FIX_REF, "hold", severity="Medium")])
    gh = FakeGh(pr_view=pr_view(head=HEAD_2), comments=[status_comment(7, held)])
    assert_rejected(gh, record(2, head=HEAD_2), "pending")




def test_records_post_stops_on_duplicate_round_comments() -> None:
    duplicates = [status_comment(7, awaiting_record()), status_comment(8, awaiting_record())]
    gh = FakeGh(pr_view=pr_view(), comments=duplicates)
    assert_rejected(gh, awaiting_record(), "multiple comments")
