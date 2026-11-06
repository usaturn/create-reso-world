"""Parse candidates for inspection; load adopted data only from the parent HEAD.

All Git commands are local reads. Loading never fetches or trusts a working-tree
registry, and parsing a candidate does not authorize an operation on it.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tomllib
from typing import Literal, cast
from urllib.parse import urlsplit

from .models import ExternalToolsError, Registry, ToolSpec

_PARENT_REPOSITORY = "usaturn/create-reso-world"
_RESERVED_REPOSITORIES = frozenset({
    _PARENT_REPOSITORY, "usaturn/resoloop", "orange3134/resoloop", "usaturn/resoloop-meshy",
})
_RESERVED_PATHS = ("external/resoloop", "external/resoloop-meshy")
_KEY = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")
_REPOSITORY = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?/[A-Za-z0-9_.-]+")
_FIELDS = frozenset({"repository", "path", "base_branch", "ci"})


def _git(root: Path, *args: str, allowed: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[bytes]:
    # Never let an inherited GIT_DIR, worktree selector, config injection or trace
    # redirect inspection or disclose the locally inspected data.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    # Ignore refs/replace so an adopted SHA cannot mask substituted blobs or ancestry.
    try:
        result = subprocess.run(["git", "--no-replace-objects", "-C", str(root), *args], capture_output=True, env=env)
    except OSError:
        raise ExternalToolsError("git_inspection_failed", "Cannot inspect the named checkout with Git.") from None
    if result.returncode not in allowed:
        # stderr and config values can contain credentials. Do not include either.
        raise ExternalToolsError("git_inspection_failed", "Local Git inspection failed.")
    return result


def _repository(value: str) -> str:
    # Same owner/repo identifier rules as superpowers_context, without importing
    # that consumer (which will itself depend on this package).
    if not _REPOSITORY.fullmatch(value) or value.partition("/")[2] in {".", ".."}:
        raise ExternalToolsError("invalid_repository", "Use a GitHub owner/repo identifier.")
    return value.lower()


def _github_repository(value: str) -> str:
    value = value.strip()
    if value.startswith("git@github.com:"):
        path = value[len("git@github.com:"):]
    else:
        try:
            url = urlsplit(value)
        except ValueError:
            raise ExternalToolsError("invalid_origin", "Parent origin is not a supported GitHub URL.") from None
        if (
            (url.scheme, url.netloc) not in (("https", "github.com"), ("ssh", "git@github.com"))
            or url.query or url.fragment
        ):
            raise ExternalToolsError("invalid_origin", "Parent origin must use GitHub HTTPS or SSH without credentials.")
        path = url.path.removeprefix("/")
    return _repository(path.rstrip("/").removesuffix(".git"))


def _overlaps(left: Path, right: Path) -> bool:
    return left.is_relative_to(right) or right.is_relative_to(left)


def _target_path(value: str, parent: Path, previous: list[tuple[Path, Path]]) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or "\x00" in value:
        raise ExternalToolsError("unsafe_path", "Tool paths must stay relative to the parent checkout.")
    if len(path.parts) < 2 or path.parts[0] != "external" or {".git", ".worktrees"}.intersection(path.parts):
        raise ExternalToolsError("unsafe_path", "Tool paths must name checkouts under external/, outside Git/worktree internals.")
    lexical = parent / path
    external = parent / "external"
    try:
        target = lexical.resolve()
        reserved = [(parent / name).resolve() for name in _RESERVED_PATHS]
    except (OSError, ValueError, RuntimeError):
        raise ExternalToolsError("unsafe_path", "Cannot safely resolve the tool path.") from None
    if target == external or not target.is_relative_to(external):
        raise ExternalToolsError("unsafe_path", "Tool path must resolve to a checkout under external/.")
    if {".git", ".worktrees"}.intersection(target.relative_to(external).parts):
        raise ExternalToolsError("unsafe_path", "Tool path resolves inside Git/worktree internals.")
    # Check lexical and resolved reservations: even an alias cannot claim an
    # existing special route, nor can symlinks make that route available to claim.
    if any(
        _overlaps(parent / path, parent / name) or _overlaps(target, resolved)
        for name, resolved in zip(_RESERVED_PATHS, reserved)
    ):
        raise ExternalToolsError("reserved_path", "Tool path overlaps an existing special repository route.")
    if any(
        _overlaps(lexical, other_lexical) or _overlaps(target, other_target)
        for other_lexical, other_target in previous
    ):
        raise ExternalToolsError("overlapping_path", "Tool paths must not duplicate or contain each other.")
    previous.append((lexical, target))
    return path.as_posix()


def parse_registry(data: bytes, *, parent_root: Path, commit: str) -> Registry:
    """Validate a candidate's schema and placement, without adopting it."""
    try:
        document = tomllib.loads(data.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError):
        raise ExternalToolsError("invalid_registry", "Registry is not valid UTF-8 TOML.") from None
    if (
        set(document) != {"schema_version", "tools"}
        or type(document["schema_version"]) is not int or document["schema_version"] != 1
        or not isinstance(document["tools"], dict)
    ):
        raise ExternalToolsError("invalid_registry", "Registry requires schema_version 1 and a tools table only.")
    try:
        parent = parent_root.resolve(strict=True)
    except (OSError, ValueError, RuntimeError):
        raise ExternalToolsError("invalid_parent", "Cannot resolve the parent checkout.") from None
    entries: list[ToolSpec] = []
    repositories: set[str] = set()
    targets: list[tuple[Path, Path]] = []
    for key, fields in document["tools"].items():
        if not _KEY.fullmatch(key):
            raise ExternalToolsError("invalid_key", "Tool keys must be lowercase alphanumeric names with internal hyphens only.")
        if not isinstance(fields, dict) or set(fields) != _FIELDS or any(not isinstance(v, str) for v in fields.values()):
            raise ExternalToolsError("invalid_registry", "Each tool requires only repository, path, base_branch and ci strings.")
        repository = _repository(fields["repository"])
        if repository in _RESERVED_REPOSITORIES:
            raise ExternalToolsError("reserved_repository", "Registry cannot override a parent or special fork route.")
        if repository in repositories:
            raise ExternalToolsError("duplicate_repository", "A repository may appear only once in the registry.")
        repositories.add(repository)
        relative_path = _target_path(fields["path"], parent, targets)
        branch = fields["base_branch"]
        if not branch or "\x00" in branch or _git(parent, "check-ref-format", f"refs/heads/{branch}", allowed=(0, 1)).returncode:
            raise ExternalToolsError("invalid_base_branch", "Base branch must be a literal valid heads ref.")
        if fields["ci"] not in {"required", "disabled"}:
            raise ExternalToolsError("invalid_ci", "CI policy must be required or disabled.")
        entries.append(ToolSpec(key, repository, relative_path, branch, cast(Literal["required", "disabled"], fields["ci"])))
    return Registry(parent, commit, tuple(entries))


def _parent_identity(parent_root: Path) -> Path:
    if not parent_root.is_absolute():
        raise ExternalToolsError("invalid_parent", "Name the absolute permanent parent checkout root.")
    try:
        root = parent_root.resolve(strict=True)
        top = Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel").stdout).strip()).resolve(strict=True)
        common = Path(os.fsdecode(_git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout).strip()).resolve(strict=True)
        git_dir = Path(os.fsdecode(_git(root, "rev-parse", "--absolute-git-dir").stdout).strip()).resolve(strict=True)
    except (OSError, ValueError, RuntimeError):
        raise ExternalToolsError("invalid_parent", "Cannot resolve the permanent parent checkout.") from None
    if root != top or common != git_dir or common != root / ".git" or not common.is_dir():
        raise ExternalToolsError("invalid_parent", "Parent must be its permanent checkout root, not a linked worktree or submodule.")
    raw = _git(root, "config", "--null", "--get-all", "remote.origin.url", allowed=(0, 1)).stdout
    urls = raw.decode("utf-8", errors="replace").removesuffix("\x00").split("\x00") if raw else []
    if len(urls) != 1 or _github_repository(urls[0]) != _PARENT_REPOSITORY:
        raise ExternalToolsError("invalid_origin", "Parent must have one origin URL identifying create-reso-world.")
    for direction in ((), ("--push",)):
        effective = _git(root, "remote", "get-url", *direction, "--all", "origin").stdout.decode("utf-8", errors="replace").splitlines()
        if len(effective) != 1 or _github_repository(effective[0]) != _PARENT_REPOSITORY:
            raise ExternalToolsError("invalid_origin", "Parent origin effective destination does not match create-reso-world.")
    return root


def load_active_registry(parent_root: Path) -> Registry | None:
    """Read the adopted detached HEAD blob, never a candidate or working tree.

    A verified legacy parent without the blob returns None before managed-only
    branch/ancestor gates. A broken or unreadable registry never becomes None.
    """
    root = _parent_identity(parent_root)
    commit = _git(root, "rev-parse", "--verify", "HEAD^{commit}").stdout.decode("ascii").strip()
    tree = _git(root, "ls-tree", "-z", commit, "--", "external-tools.toml").stdout
    if not tree:
        return None
    if _git(root, "symbolic-ref", "-q", "HEAD", allowed=(0, 1)).returncode == 0:
        raise ExternalToolsError("parent_not_detached", "Adopted registry requires a detached parent HEAD.")
    if _git(root, "merge-base", "--is-ancestor", commit, "refs/remotes/origin/main", allowed=(0, 1)).returncode:
        raise ExternalToolsError("registry_not_adopted", "Parent HEAD must be an ancestor of local origin/main.")
    mode, kind, _ = tree.split(b"\t", 1)[0].split(b" ")
    if kind != b"blob" or mode not in {b"100644", b"100755"}:
        raise ExternalToolsError("invalid_registry", "Adopted registry must be a regular file blob.")
    data = _git(root, "cat-file", "blob", f"{commit}:external-tools.toml").stdout
    return parse_registry(data, parent_root=root, commit=commit)
