"""Read-only Git context validation shared by the Superpowers shell consumers.

No discovery beyond the current checkout, network access, or Git mutation.
Operation profiles deliberately distinguish review sources from repair worktrees.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from dataclasses import dataclass
from urllib.parse import urlsplit

DOCUMENT_REPOSITORY = "usaturn/create-reso-world"
FORK_REPOSITORY = "usaturn/resoloop"
UPSTREAM_REPOSITORY = "orange3134/resoloop"
OPERATIONS = ("review-workspace", "review-fix", "review-copy")


class ContextError(ValueError):
    """An expected preflight rejection with an actionable message."""


def _identifier(owner: str, repository: str) -> str:
    if (
        not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", owner)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", repository)
        or repository in (".", "..")
    ):
        raise ContextError(f"invalid GitHub repository identifier: {owner}/{repository}")
    return f"{owner}/{repository}".lower()


def normalize_github_url(value: str, *, allow_pr: bool = False) -> str:
    """Normalize supported GitHub transport URLs (and optionally a PR URL)."""
    value = value.strip()
    if value.startswith("git@github.com:"):
        path = value[len("git@github.com:"):]
    else:
        try:
            url = urlsplit(value)
        except ValueError as exc:
            raise ContextError(f"invalid GitHub repository URL: {value}") from exc
        if (url.scheme, url.netloc) not in (("https", "github.com"), ("ssh", "git@github.com")) or url.query or url.fragment:
            raise ContextError(f"unsupported GitHub repository URL/host: {value}")
        path = url.path.removeprefix("/")
    parts = path.rstrip("/").split("/")
    if len(parts) == 4 and allow_pr and value.startswith("https://github.com/"):
        if parts[2] != "pull" or not re.fullmatch(r"[1-9][0-9]*", parts[3]):
            raise ContextError(f"invalid GitHub PR repository URL: {value}")
    elif len(parts) != 2:
        raise ContextError(f"invalid GitHub repository URL: {value}")
    return _identifier(parts[0], parts[1].removesuffix(".git"))


def parse_repository(value: str) -> str:
    """Accept a canonical owner/repo or a canonical GitHub PR URL."""
    value = value.strip()
    if value.startswith("https://"):
        # --repo URLs denote PRs, not arbitrary GitHub pages or transport URLs.
        if not re.fullmatch(r"https://github\.com/[^/]+/[^/]+/pull/[1-9][0-9]*/?", value):
            raise ContextError(f"invalid GitHub PR repository URL: {value}")
        return normalize_github_url(value, allow_pr=True)
    parts = value.split("/")
    if len(parts) != 2:
        raise ContextError(f"repository must be owner/repo or a GitHub PR URL: {value}")
    return _identifier(*parts)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True)
    if result.returncode:
        raise ContextError(f"Git inspection failed in {root}: {' '.join(args)}; {result.stderr.strip()}")
    return result.stdout.strip()


@dataclass(frozen=True)
class Checkout:
    root: Path
    git_dir: Path
    common_dir: Path
    remotes: dict[str, str]
    branch: str | None
    head: str

    @property
    def linked(self) -> bool:
        return self.git_dir != self.common_dir


def inspect_checkout(root: str | Path, *, label: str, require_main: bool = False) -> Checkout:
    """Verify an explicit absolute root, then read its identity and Git state."""
    path = Path(root)
    if not path.is_absolute():
        raise ContextError(f"{label} must be an absolute path: {root}")
    try:
        path = path.resolve(strict=True)
        top = Path(_git(path, "rev-parse", "--show-toplevel")).resolve(strict=True)
        if path != top:
            raise ContextError(f"{label} is not the root of its checkout: {root}")
        git_dir = Path(_git(path, "rev-parse", "--absolute-git-dir")).resolve(strict=True)
        common_dir = Path(_git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve(strict=True)
        if require_main and git_dir != common_dir:
            raise ContextError(
                f"{label} must be the main checkout, not a linked worktree: {root}; "
                "name the create-reso-world main checkout as PARENT_ROOT when resolving the parent"
            )
        remotes = {name: _git(path, "remote", "get-url", name) for name in _git(path, "remote").splitlines()}
        branch = _git(path, "branch", "--show-current") or None
        head = _git(path, "rev-parse", "--verify", "HEAD^{commit}")
        return Checkout(path, git_dir, common_dir, remotes, branch, head)
    except (OSError, ContextError) as exc:
        raise ContextError(f"{label} checkout validation failed: {exc}") from exc


def _remote_repository(checkout: Checkout, name: str) -> str | None:
    url = checkout.remotes.get(name)
    if url is None:
        return None
    try:
        return normalize_github_url(url)
    except ContextError:
        return None


def _require_origin(checkout: Checkout, label: str) -> None:
    if _remote_repository(checkout, "origin") != DOCUMENT_REPOSITORY:
        url = checkout.remotes.get("origin", "missing origin")
        raise ContextError(f"{label} origin is not {DOCUMENT_REPOSITORY}: {checkout.root} ({url}); use a verified create-reso-world checkout")


def select_remote(checkout: Checkout, repository: str, *, label: str = "CODE_ROOT") -> str:
    """Require exactly one remote *name*, not merely one distinct URL."""
    matches = [name for name in checkout.remotes if _remote_repository(checkout, name) == repository]
    if len(matches) != 1:
        raise ContextError(f"{label} {checkout.root} has {len(matches)} remotes for {repository}; exactly one is required")
    return matches[0]


def resolve_context(
    operation: str, *, parent_root: str | Path | None = None, doc_root: str | Path | None = None,
    code_root: str | Path | None = None, repo: str = DOCUMENT_REPOSITORY,
    doc_branch: str | None = None, head_repo: str | None = None, head_branch: str | None = None,
    cwd: str | Path | None = None,
) -> dict[str, str | None]:
    """Resolve verified parent/tool, document and code identities without mutation."""
    if operation not in OPERATIONS:
        raise ContextError(f"unsupported operation: {operation}")
    repository = parse_repository(repo)
    if not parent_root:
        current = Path(cwd) if cwd else Path.cwd()
        try:
            parent_root = _git(current, "rev-parse", "--show-toplevel")
        except ContextError as exc:
            raise ContextError("PARENT_ROOT is required; name the create-reso-world main checkout explicitly") from exc
    parent = inspect_checkout(parent_root, label="PARENT_ROOT", require_main=True)
    _require_origin(parent, "PARENT_ROOT")

    document = None
    if doc_root:
        document = inspect_checkout(doc_root, label="DOC_ROOT")
        _require_origin(document, "DOC_ROOT")
        if doc_branch and document.branch != doc_branch:
            raise ContextError(f"DOC_ROOT branch is {document.branch!r}, not requested {doc_branch!r}: {document.root}")
    elif doc_branch or operation == "review-copy":
        raise ContextError("DOC_ROOT is required; name the create-reso-world document branch checkout explicitly")

    context: dict[str, str | None] = dict.fromkeys((
        "parent_root", "tool_root", "doc_root", "code_root", "repository", "base_remote",
        "head_remote", "document_branch", "document_head", "code_branch", "code_head",
    ))
    context.update(parent_root=str(parent.root), tool_root=str(parent.root), repository=repository)
    if document:
        context.update(doc_root=str(document.root), document_branch=document.branch, document_head=document.head)
    if operation == "review-copy":
        if code_root or head_repo or head_branch:
            raise ContextError("review-copy validates parent/doc roots only; omit code/head arguments")
        return context

    expected = None
    if repository == DOCUMENT_REPOSITORY:
        expected, base_remote = parent, "origin"
    elif repository in (FORK_REPOSITORY, UPSTREAM_REPOSITORY):
        try:
            expected = inspect_checkout(parent.root / "external/resoloop", label="ResoLoop fork")
            if (
                _remote_repository(expected, "origin") != FORK_REPOSITORY
                or _remote_repository(expected, "upstream") != UPSTREAM_REPOSITORY
            ):
                raise ContextError("origin/upstream do not identify the expected ResoLoop fork")
        except ContextError as exc:
            raise ContextError(f"ResoLoop fork validation failed: {exc}; run scripts/resoloop-fork.sh clone first") from exc
        base_remote = "origin" if repository == FORK_REPOSITORY else "upstream"

    if code_root:
        code = inspect_checkout(code_root, label="CODE_ROOT")
    elif expected:
        code = expected
    else:
        raise ContextError(f"unsupported PR repository: {repository}; explicitly name its checkout as CODE_ROOT")
    if operation == "review-workspace" and code.linked:
        raise ContextError(f"CODE_ROOT is a linked worktree; name the main checkout of {repository}: {code.root}")
    if expected:
        if operation == "review-workspace" and code.root != expected.root:
            raise ContextError(f"CODE_ROOT {code.root} does not match the known route {expected.root} for {repository}")
        if operation == "review-fix" and code.common_dir != expected.common_dir:
            raise ContextError(
                f"CODE_ROOT {code.root} must belong to the same Git repository as {expected.root}; "
                "a matching origin URL is not sufficient"
            )
    else:
        base_remote = select_remote(code, repository)
    context.update(code_root=str(code.root), base_remote=base_remote, code_branch=code.branch, code_head=code.head)

    if head_repo or head_branch:
        if operation != "review-fix" or not head_repo or not head_branch:
            raise ContextError("head validation requires review-fix with both --head-repo and --head-branch")
        context["head_remote"] = select_remote(code, parse_repository(head_repo), label="CODE_ROOT head remote")
        if code.branch != head_branch:
            raise ContextError(f"CODE_ROOT branch is {code.branch!r}, not requested head branch {head_branch!r}: {code.root}")
    return context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", choices=OPERATIONS, required=True)
    for option in ("parent-root", "doc-root", "code-root", "doc-branch", "head-repo", "head-branch"):
        parser.add_argument(f"--{option}")
    parser.add_argument("--repo", default=DOCUMENT_REPOSITORY)
    args = parser.parse_args(argv)
    try:
        context = resolve_context(**vars(args))
    except (ContextError, OSError) as exc:
        print(f"superpowers-context: {exc}", file=sys.stderr)
        return 66
    print(json.dumps(context, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
