#!/usr/bin/env python3
"""Create or update this agent's review-fix-planning status comment on a PR."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import urlparse

MARKER_TEMPLATE = "<!-- review-fix-planning:agent:{agent_id} -->"
MARKER_RE = re.compile(r"<!-- review-fix-planning:agent:([^ ]+) -->")
MODEL_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*")


class Runner(Protocol):
    def __call__(
        self,
        args: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]: ...


class CommentError(RuntimeError):
    """Fail closed without posting a malformed or ambiguous comment."""


def sanitize_agent_id(value: str) -> str:
    sanitized = value.replace("/", "-").replace(" ", "-")
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")
    if MODEL_FILENAME.fullmatch(sanitized) is None:
        raise CommentError("model identifier is not a safe agent id")
    return sanitized


def marker_for(agent_id: str) -> str:
    return MARKER_TEMPLATE.format(agent_id=sanitize_agent_id(agent_id))


def compose_body(model_name: str, markdown: str) -> str:
    text = markdown.strip()
    if not text:
        raise CommentError("comment body is empty")
    agent_id = sanitize_agent_id(model_name)
    own = marker_for(agent_id)
    found = list(MARKER_RE.finditer(text))
    foreign = [match.group(1) for match in found if match.group(1) != agent_id]
    if foreign:
        raise CommentError(
            "comment body already has a review-fix-planning marker for another agent: " + ", ".join(foreign)
        )
    if own in text:
        if not text.startswith(own):
            raise CommentError("own review-fix-planning marker must be the first line")
        return text
    return f"{own}\n{text}"


def find_own_comment_id(comments: Sequence[Mapping[str, Any]], model_name: str) -> int | None:
    own = marker_for(model_name)
    matches: list[int] = []
    for comment in comments:
        body = comment.get("body")
        if not isinstance(body, str) or own not in body:
            continue
        comment_id = comment.get("id")
        if not isinstance(comment_id, int):
            raise CommentError("comment id is missing")
        matches.append(comment_id)
    if len(matches) > 1:
        raise CommentError(f"multiple comments carry {own}: " + ", ".join(str(item) for item in matches))
    if not matches:
        return None
    return matches[0]


def _json_object(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value)


def flatten_comment_pages(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise CommentError("unexpected comments payload")
    pages = cast(list[object], raw)
    if not pages:
        return []
    if all(isinstance(item, dict) for item in pages):
        mapped = [_json_object(item) for item in pages]
        return [item for item in mapped if item is not None]
    out: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, list):
            raise CommentError("unexpected comments payload")
        for item in cast(list[object], page):
            mapping = _json_object(item)
            if mapping is None:
                raise CommentError("unexpected comments payload")
            out.append(mapping)
    return out


def validate_repo(repo: str) -> str:
    if REPOSITORY.fullmatch(repo) is None:
        raise CommentError(f"repository must be owner/name: {repo}")
    return repo


def repository_from_pr_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 4 or parts[2] != "pull":
        raise CommentError(f"cannot parse PR url: {url}")
    try:
        number = int(parts[3])
    except ValueError as error:
        raise CommentError(f"cannot parse PR url: {url}") from error
    return f"{parts[0]}/{parts[1]}", number


class GhRunner:
    def __call__(
        self,
        args: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(args),
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )


def run_gh(
    args: Sequence[str],
    *,
    runner: Runner,
    input_text: str | None = None,
) -> str:
    command = ["gh", *args]
    completed = runner(command, input_text=input_text)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "gh failed"
        raise CommentError(detail)
    return completed.stdout


def load_json(text: str, what: str) -> object:
    try:
        loaded: object = json.loads(text)
    except json.JSONDecodeError as error:
        raise CommentError(f"invalid JSON from {what}") from error
    return loaded


def resolve_pr(pr: int, repo: str, runner: Runner) -> tuple[str, int]:
    expected = validate_repo(repo)
    raw = load_json(
        run_gh(
            ["pr", "view", str(pr), "--repo", expected, "--json", "url,number"],
            runner=runner,
        ),
        "gh pr view",
    )
    parsed = _json_object(raw)
    if parsed is None:
        raise CommentError("unexpected gh pr view payload")
    url = parsed.get("url")
    number = parsed.get("number")
    if not isinstance(url, str) or not isinstance(number, int):
        raise CommentError("gh pr view did not return url and number")
    parsed_repo, parsed_number = repository_from_pr_url(url)
    if parsed_number != number or number != pr:
        raise CommentError("PR number from gh pr view does not match")
    if parsed_repo != expected:
        raise CommentError(f"gh pr view resolved {parsed_repo}, not the requested {expected}")
    return parsed_repo, number


def list_comments(repo: str, pr: int, runner: Runner) -> list[dict[str, Any]]:
    raw = load_json(
        run_gh(
            ["api", "--paginate", "--slurp", f"repos/{repo}/issues/{pr}/comments"],
            runner=runner,
        ),
        "gh api comments",
    )
    return flatten_comment_pages(raw)


def upsert(
    pr: int,
    repo: str,
    model_name: str,
    markdown: str,
    *,
    runner: Runner | None = None,
) -> dict[str, Any]:
    active = GhRunner() if runner is None else runner
    body = compose_body(model_name, markdown)
    repo, pr_number = resolve_pr(pr, repo, active)
    existing = find_own_comment_id(list_comments(repo, pr_number, active), model_name)
    payload = json.dumps({"body": body}, ensure_ascii=False)
    if existing is None:
        raw = run_gh(
            [
                "api",
                "--method",
                "POST",
                f"repos/{repo}/issues/{pr_number}/comments",
                "--input",
                "-",
            ],
            runner=active,
            input_text=payload,
        )
        action = "created"
    else:
        raw = run_gh(
            [
                "api",
                "--method",
                "PATCH",
                f"repos/{repo}/issues/comments/{existing}",
                "--input",
                "-",
            ],
            runner=active,
            input_text=payload,
        )
        action = "updated"
    created = _json_object(load_json(raw, "gh api upsert"))
    if created is None or not isinstance(created.get("id"), int):
        raise CommentError("upsert response did not include a comment id")
    url = created.get("html_url")
    return {
        "action": action,
        "comment_id": created["id"],
        "url": url if isinstance(url, str) else "",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument(
        "--repo",
        required=True,
        help="owner/name of the repository holding the PR. Never inferred from cwd.",
    )
    parser.add_argument("--model-name", required=True)
    parser.add_argument(
        "--body-file",
        help="Markdown body without the agent marker. Defaults to stdin.",
    )
    return parser.parse_args(argv)


def read_body(path: str | None) -> str:
    if path is None:
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = upsert(args.pr, args.repo, args.model_name, read_body(args.body_file))
    except CommentError as error:
        print(str(error), file=sys.stderr)
        return 64
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
