"""Read-only Git context validation shared by the Superpowers shell consumers.

No discovery beyond the current checkout, network access, or Git mutation.
Operation profiles deliberately distinguish review sources from repair worktrees.
Spec/Plan live in create-reso-world unless the code repository declares its own
(``DOCUMENTS_MARKER`` in its committed AGENTS.md; docs/superpowers/README.md).
"""
from __future__ import annotations

import argparse
import functools
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass
from urllib.parse import urlsplit

DOCUMENT_REPOSITORY = "usaturn/create-reso-world"
FORK_REPOSITORY = "usaturn/resoloop"
UPSTREAM_REPOSITORY = "orange3134/resoloop"
OPERATIONS = ("review-workspace", "review-fix", "review-copy")
# A new repository commits this AGENTS.md line to keep its own Spec/Plan.
DOCUMENTS_MARKER = "<!-- superpowers-documents: this-repository -->"
# Repositories with special routes keep their Spec/Plan in create-reso-world even if declared.
SHARED_DOCUMENT_REPOSITORIES = (FORK_REPOSITORY, UPSTREAM_REPOSITORY, "usaturn/resoloop-meshy")


class ContextError(ValueError):
    """An expected preflight rejection with an actionable message."""

    exit_code = 66


class InputError(ContextError):
    """A required context input is absent or incomplete."""

    exit_code = 64


class ForkPrerequisiteError(ContextError):
    """The known ResoLoop fork is absent or incorrectly configured."""

    exit_code = 65


@functools.cache
def _external_tools():
    """Load only the common package adjacent to this helper, under a private name.

    A caller may already have a different ``tools`` package in sys.modules, or
    supply one through cwd/PYTHONPATH. Neither can select our identity provider.
    """
    path = Path(__file__).resolve().parents[1] / "tools/external_tools"
    name = f"_superpowers_external_tools_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(
        name, path / "__init__.py", submodule_search_locations=[str(path)])
    if spec is None or spec.loader is None:
        raise ContextError("cannot load the adjacent external-tools package")
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    importlib.import_module(f"{name}.registry")
    importlib.import_module(f"{name}.identity")
    return package


def _identifier(owner: str, repository: str) -> str:
    if (
        not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", owner)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", repository)
        or repository in (".", "..")
    ):
        raise ContextError("invalid GitHub repository identifier; use valid owner/repo names")
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
            raise ContextError("invalid GitHub repository URL; check its syntax") from exc
        if (url.scheme, url.netloc) not in (("https", "github.com"), ("ssh", "git@github.com")) or url.query or url.fragment:
            raise ContextError("unsupported GitHub repository URL/host; use GitHub HTTPS or SSH without credentials, query or fragment")
        path = url.path.removeprefix("/")
    parts = path.rstrip("/").split("/")
    if len(parts) == 4 and allow_pr and value.startswith("https://github.com/"):
        if parts[2] != "pull" or not re.fullmatch(r"[1-9][0-9]*", parts[3]):
            raise ContextError("invalid GitHub PR repository URL; use https://github.com/owner/repo/pull/number")
    elif len(parts) != 2:
        raise ContextError("invalid GitHub repository URL; use a GitHub owner/repo URL")
    return _identifier(parts[0], parts[1].removesuffix(".git"))


def parse_repository(value: str) -> str:
    """Accept a canonical owner/repo or a canonical GitHub PR URL."""
    value = value.strip()
    if value.startswith("https://"):
        # --repo URLs denote PRs, not arbitrary GitHub pages or transport URLs.
        if not re.fullmatch(r"https://github\.com/[^/]+/[^/]+/pull/[1-9][0-9]*/?", value):
            raise ContextError("invalid GitHub PR repository URL; use https://github.com/owner/repo/pull/number")
        return normalize_github_url(value, allow_pr=True)
    parts = value.split("/")
    if len(parts) != 2:
        raise ContextError("repository must be owner/repo or a GitHub PR URL")
    return _identifier(*parts)


def _git(root: Path, *args: str) -> str:
    # Inspect the named root's own Git, not one that ambient GIT_DIR and friends point at.
    # review_target.py loads this module, so it repeats that helper's rule instead of importing it.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, env=env)
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
        reason = "missing origin" if "origin" not in checkout.remotes else "unsupported URL or different repository"
        raise ContextError(f"{label} origin is not {DOCUMENT_REPOSITORY}: {checkout.root} ({reason}); use a verified create-reso-world checkout")


def declares_own_documents(checkout: Checkout) -> bool:
    """True when HEAD's committed AGENTS.md has the DOCUMENTS_MARKER line (worktree edits do not count)."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(["git", "-C", str(checkout.root), "cat-file", "blob", "HEAD:AGENTS.md"],
                            capture_output=True, env=env)
    if result.returncode:
        return False
    return any(line.strip() == DOCUMENTS_MARKER
               for line in result.stdout.decode("utf-8", errors="replace").splitlines())


def _document_repository(checkout: Checkout, repository: str) -> str:
    """Where Spec/Plan for work on *repository* are committed."""
    if repository == DOCUMENT_REPOSITORY or repository in SHARED_DOCUMENT_REPOSITORIES:
        return DOCUMENT_REPOSITORY
    return repository if declares_own_documents(checkout) else DOCUMENT_REPOSITORY


def _require_own_documents(checkout: Checkout, repository: str) -> None:
    if repository in SHARED_DOCUMENT_REPOSITORIES:
        raise ContextError(
            f"DOC_ROOT cannot hold Spec/Plan for {repository}: it keeps them in {DOCUMENT_REPOSITORY}; "
            "omit --doc-repo and use a create-reso-world DOC_ROOT")
    if _remote_repository(checkout, "origin") != repository:
        reason = "missing origin" if "origin" not in checkout.remotes else "unsupported URL or different repository"
        raise ContextError(f"DOC_ROOT origin is not {repository}: {checkout.root} ({reason}); use a checkout of {repository}")
    if not declares_own_documents(checkout):
        raise ContextError(
            f"DOC_ROOT {checkout.root} does not declare its own Spec/Plan: HEAD:AGENTS.md has no line "
            f"{DOCUMENTS_MARKER}; keep the documents in {DOCUMENT_REPOSITORY}")


def select_remote(checkout: Checkout, repository: str, *, label: str = "CODE_ROOT") -> str:
    """Require exactly one remote *name*, not merely one distinct URL."""
    matches = [name for name in checkout.remotes if _remote_repository(checkout, name) == repository]
    if len(matches) != 1:
        raise ContextError(f"{label} {checkout.root} has {len(matches)} remotes for {repository}; exactly one is required")
    return matches[0]


def select_push_remote(checkout: Checkout, repository: str) -> str:
    """Require one remote name whose *every* effective push URL targets head."""
    matches = []
    for name in checkout.remotes:
        # Git applies pushurl, fetch-URL fallback and pushInsteadOf expansion.
        urls = _git(checkout.root, "remote", "get-url", "--push", "--all", name).splitlines()
        repositories = []
        for url in urls:
            try:
                repositories.append(normalize_github_url(url))
            except ContextError:
                repositories.append(None)
        if repositories and all(target == repository for target in repositories):
            matches.append(name)
    if len(matches) != 1:
        raise ContextError(
            f"CODE_ROOT head remote {checkout.root} has {len(matches)} remotes whose effective push URLs "
            f"all target {repository}; exactly one is required; check each remote's push configuration"
        )
    return matches[0]


def resolve_context(
    operation: str, *, parent_root: str | Path | None = None, doc_root: str | Path | None = None,
    code_root: str | Path | None = None, repo: str = DOCUMENT_REPOSITORY,
    doc_branch: str | None = None, head_repo: str | None = None, head_branch: str | None = None,
    cwd: str | Path | None = None, doc_repo: str | None = None,
) -> dict[str, str | None]:
    """Resolve verified parent/tool, document and code identities without mutation."""
    if operation not in OPERATIONS:
        raise ContextError(f"unsupported operation: {operation}")
    repository = parse_repository(repo)
    documents_for = parse_repository(doc_repo) if doc_repo else DOCUMENT_REPOSITORY
    if not parent_root:
        current = Path(cwd) if cwd else Path.cwd()
        try:
            parent_root = _git(current, "rev-parse", "--show-toplevel")
        except ContextError as exc:
            raise InputError("PARENT_ROOT is required; name the create-reso-world main checkout explicitly") from exc
    parent = inspect_checkout(parent_root, label="PARENT_ROOT", require_main=True)
    _require_origin(parent, "PARENT_ROOT")

    document = None
    if doc_root:
        document = inspect_checkout(doc_root, label="DOC_ROOT")
        if documents_for == DOCUMENT_REPOSITORY:
            _require_origin(document, "DOC_ROOT")
        else:
            _require_own_documents(document, documents_for)
        if doc_branch and document.branch != doc_branch:
            raise ContextError(f"DOC_ROOT branch is {document.branch!r}, not requested {doc_branch!r}: {document.root}")
    elif doc_branch or operation == "review-copy":
        # --doc-repo alone is ignored: a context block re-runs with its earlier output before DOC_ROOT is chosen.
        raise InputError("DOC_ROOT is required; name the document branch checkout explicitly")

    context: dict[str, str | None] = dict.fromkeys((
        "parent_root", "tool_root", "doc_root", "code_root", "repository", "base_remote",
        "head_remote", "document_branch", "document_head", "code_branch", "code_head", "document_repository",
    ))
    context.update(parent_root=str(parent.root), tool_root=str(parent.root), repository=repository)
    if document:
        context.update(doc_root=str(document.root), document_branch=document.branch, document_head=document.head)
    if (head_repo or head_branch) and not (head_repo and head_branch):
        raise InputError("head validation requires review-fix with both --head-repo and --head-branch")
    if operation == "review-copy":
        if code_root or head_repo or head_branch:
            raise ContextError("review-copy validates parent/doc roots only; omit code/head arguments")
        context["document_repository"] = documents_for
        return context

    tools = _external_tools()
    try:
        registry = tools.registry.load_active_registry(parent.root)
    except tools.models.ExternalToolsError as error:
        raise ContextError(f"external-tools: {error.reason_code}: {error}") from None
    managed = None
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
            raise ForkPrerequisiteError(f"ResoLoop fork validation failed: {exc}; run scripts/resoloop-fork.sh clone first") from exc
        base_remote = "origin" if repository == FORK_REPOSITORY else "upstream"
    elif registry is not None and registry.find_repository(repository) is not None:
        try:
            managed = tools.identity.resolve_managed_target(
                registry, repository, operation=operation,
                code_root=Path(code_root) if code_root else None)
        except tools.models.ExternalToolsError as error:
            raise ContextError(f"external-tools: {error.reason_code}: {error}") from None
        base_remote = managed.base_remote

    if managed:
        code = inspect_checkout(managed.checkout, label="CODE_ROOT")
    elif code_root:
        code = inspect_checkout(code_root, label="CODE_ROOT")
    elif expected:
        code = expected
    else:
        raise InputError(f"unsupported PR repository: {repository}; explicitly name its checkout as CODE_ROOT")
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
        # Shared repository membership does not guarantee worktree-effective URLs.
        if repository == DOCUMENT_REPOSITORY:
            _require_origin(code, "CODE_ROOT")
        elif (
            _remote_repository(code, "origin") != FORK_REPOSITORY
            or _remote_repository(code, "upstream") != UPSTREAM_REPOSITORY
        ):
            raise ContextError(
                f"CODE_ROOT origin/upstream do not identify the expected ResoLoop fork: {code.root}; "
                "check the repair worktree's effective remote configuration"
            )
    elif managed is None:
        base_remote = select_remote(code, repository)
    context.update(code_root=str(code.root), base_remote=base_remote, code_branch=code.branch, code_head=code.head)
    expected_documents = _document_repository(code, repository)
    if document and documents_for != expected_documents:
        raise ContextError(
            f"DOC_ROOT holds Spec/Plan for {documents_for}, but Spec/Plan for {repository} belong in "
            f"{expected_documents}; pass --doc-repo {expected_documents} with a checkout of it")
    context["document_repository"] = expected_documents

    if head_repo or head_branch:
        if operation != "review-fix":
            raise ContextError("head validation requires review-fix with both --head-repo and --head-branch")
        context["head_remote"] = select_push_remote(code, parse_repository(head_repo))
        if code.branch != head_branch:
            raise ContextError(f"CODE_ROOT branch is {code.branch!r}, not requested head branch {head_branch!r}: {code.root}")
    return context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", choices=OPERATIONS)
    for option in ("parent-root", "doc-root", "code-root", "doc-branch", "doc-repo", "head-repo", "head-branch"):
        parser.add_argument(f"--{option}")
    parser.add_argument("--repo", default=DOCUMENT_REPOSITORY)
    args = parser.parse_args(argv)
    try:
        if args.operation is None:
            raise InputError("--operation is required; choose review-workspace, review-fix, or review-copy")
        context = resolve_context(**vars(args))
    except ContextError as exc:
        print(f"superpowers-context: {exc}", file=sys.stderr)
        return exc.exit_code
    except OSError as exc:
        print(f"superpowers-context: {exc}", file=sys.stderr)
        return 66
    print(json.dumps(context, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
