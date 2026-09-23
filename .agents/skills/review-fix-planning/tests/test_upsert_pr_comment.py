from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest

HELPER = Path(__file__).resolve().parents[1] / "scripts" / "upsert_pr_comment.py"


def load_helper() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("upsert_pr_comment", HELPER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = load_helper()


class FakeGh:
    def __init__(
        self,
        *,
        pr_view: dict[str, Any],
        comments: Any,
        upsert_response: dict[str, Any],
    ) -> None:
        self.pr_view = pr_view
        self.comments = comments
        self.upsert_response = upsert_response
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
        if argv[1:4] == ("api", "--paginate", "--slurp"):
            return CompletedProcess(list(args), 0, json.dumps(self.comments), "")
        if argv[1:3] == ("api", "--method"):
            return CompletedProcess(list(args), 0, json.dumps(self.upsert_response), "")
        return CompletedProcess(list(args), 1, "", f"unexpected gh args: {argv}")


def test_sanitize_replaces_slash_space_and_double_hyphen() -> None:
    assert mod.sanitize_agent_id("Cursor Grok 4.6") == "Cursor-Grok-4.6"
    assert mod.sanitize_agent_id("opencode/deepseek-v4-flash-free") == ("opencode-deepseek-v4-flash-free")
    assert mod.sanitize_agent_id("foo--bar") == "foo-bar"


def test_compose_body_prepends_marker() -> None:
    body = mod.compose_body("claude-opus-5", "### レビュー状況\n- ok")
    assert body.startswith("<!-- review-fix-planning:agent:claude-opus-5 -->\n")
    assert "### レビュー状況" in body


def test_compose_body_rejects_empty_and_foreign_marker() -> None:
    with pytest.raises(mod.CommentError, match="empty"):
        mod.compose_body("claude-opus-5", "   ")
    with pytest.raises(mod.CommentError, match="another agent"):
        mod.compose_body(
            "claude-opus-5",
            "<!-- review-fix-planning:agent:composer-2 -->\n### レビュー状況",
        )


def test_find_own_comment_ignores_other_agents_and_rejects_duplicates() -> None:
    comments = [
        {"id": 1, "body": "<!-- review-fix-planning:agent:composer-2 -->\nnope"},
        {"id": 2, "body": "<!-- review-fix-planning:agent:claude-opus-5 -->\nmine"},
        {"id": 3, "body": "review-fix-planning without a marker"},
    ]
    assert mod.find_own_comment_id(comments, "claude-opus-5") == 2
    assert mod.find_own_comment_id(comments[:1], "claude-opus-5") is None
    with pytest.raises(mod.CommentError, match="multiple comments"):
        mod.find_own_comment_id(comments + [comments[1]], "claude-opus-5")


def test_upsert_creates_when_no_own_comment() -> None:
    gh = FakeGh(
        pr_view={
            "url": "https://github.com/usaturn/maatlog/pull/225",
            "number": 225,
        },
        comments=[],
        upsert_response={
            "id": 99,
            "html_url": "https://github.com/usaturn/maatlog/pull/225#issuecomment-99",
        },
    )
    result = mod.upsert(225, "usaturn/maatlog", "claude-opus-5", "### レビュー状況\n- ok", runner=gh)
    assert result["action"] == "created"
    assert result["comment_id"] == 99
    method_call = next(call for call in gh.calls if call[0][2] == "--method")
    assert method_call[0][3] == "POST"
    assert "issues/225/comments" in method_call[0][4]
    payload = json.loads(method_call[1] or "")
    assert payload["body"].startswith("<!-- review-fix-planning:agent:claude-opus-5 -->")


def test_upsert_patches_existing_own_comment() -> None:
    gh = FakeGh(
        pr_view={
            "url": "https://github.com/usaturn/maatlog/pull/225",
            "number": 225,
        },
        comments=[
            {
                "id": 41,
                "body": "<!-- review-fix-planning:agent:claude-opus-5 -->\nold",
            }
        ],
        upsert_response={
            "id": 41,
            "html_url": "https://github.com/usaturn/maatlog/pull/225#issuecomment-41",
        },
    )
    result = mod.upsert(225, "usaturn/maatlog", "claude-opus-5", "### 作業結果\n- push 済み", runner=gh)
    assert result["action"] == "updated"
    method_call = next(call for call in gh.calls if call[0][2] == "--method")
    assert method_call[0][3] == "PATCH"
    assert method_call[0][4] == "repos/usaturn/maatlog/issues/comments/41"


def test_upsert_passes_the_requested_repository_to_gh_pr_view() -> None:
    gh = FakeGh(
        pr_view={
            "url": "https://github.com/usaturn/maatlog/pull/7",
            "number": 7,
        },
        comments=[],
        upsert_response={
            "id": 12,
            "html_url": "https://github.com/usaturn/maatlog/pull/7#issuecomment-12",
        },
    )
    mod.upsert(7, "usaturn/maatlog", "claude-opus-5", "### レビュー状況\n- ok", runner=gh)
    view_call = next(call for call in gh.calls if call[0][1:3] == ("pr", "view"))
    argv = view_call[0]
    assert "--repo" in argv
    assert argv[argv.index("--repo") + 1] == "usaturn/maatlog"


def test_upsert_stops_when_gh_resolves_a_different_repository() -> None:
    """A PR number alone is ambiguous: #7 exists in both maatlog-poc and maatlog."""
    gh = FakeGh(
        pr_view={
            "url": "https://github.com/usaturn/maatlog-poc/pull/7",
            "number": 7,
        },
        comments=[],
        upsert_response={"id": 12, "html_url": ""},
    )
    with pytest.raises(mod.CommentError, match="usaturn/maatlog-poc"):
        mod.upsert(7, "usaturn/maatlog", "claude-opus-5", "### レビュー状況\n- ok", runner=gh)
    assert not [call for call in gh.calls if "--method" in call[0]]


def test_validate_repo_rejects_anything_but_owner_name() -> None:
    assert mod.validate_repo("usaturn/maatlog") == "usaturn/maatlog"
    for bad in ("maatlog", "usaturn/maatlog/extra", "", "usaturn /maatlog"):
        with pytest.raises(mod.CommentError, match="owner/name"):
            mod.validate_repo(bad)
