"""Read-only, environment-isolated identity and transport checks for managed tools.

A matching URL is not repository membership. Operations are anchored to the
registered permanent checkout's common directory and an adopted registry blob.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from .models import ExternalToolsError, ManagedTarget, Registry
from .registry import _git, _github_repository, _repository, load_active_registry

_OPERATIONS = frozenset({"implement", "review-workspace", "review-fix", "base-read", "cleanup"})


def _text(root: Path, *args: str) -> str:
    return os.fsdecode(_git(root, *args).stdout).strip()


def _checkout(root: Path) -> tuple[Path, Path, Path]:
    if not root.is_absolute():
        raise ExternalToolsError("invalid_checkout", "Name an absolute checkout root.")
    try:
        path = root.resolve(strict=True)
        top = Path(_text(path, "rev-parse", "--show-toplevel")).resolve(strict=True)
        git_dir = Path(_text(path, "rev-parse", "--absolute-git-dir")).resolve(strict=True)
        common = Path(_text(path, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve(strict=True)
    except (OSError, ValueError, RuntimeError):
        raise ExternalToolsError("invalid_checkout", "Cannot inspect the named checkout root.") from None
    if path != top:
        raise ExternalToolsError("invalid_checkout", "Target must be the checkout root, not a subdirectory.")
    _text(path, "rev-parse", "--verify", "HEAD^{commit}")
    return path, git_dir, common


def _configured_urls(root: Path, name: str, field: str) -> list[str]:
    raw = _git(root, "config", "--null", "--get-all", f"remote.{name}.{field}", allowed=(0, 1)).stdout
    return raw.decode("utf-8", errors="replace").removesuffix("\x00").split("\x00") if raw else []


def _require_urls(urls: list[str], repository: str) -> None:
    try:
        valid = bool(urls) and all(_github_repository(url) == repository for url in urls)
    except ExternalToolsError:
        valid = False
    if not valid:
        raise ExternalToolsError("remote_mismatch", "Remote destination must identify the registered GitHub repository without credentials.")


def validate_transport_destination(target: ManagedTarget, *, direction: Literal["fetch", "push"]) -> None:
    """Inspect raw and Git-expanded local destinations only; never contact a remote."""
    if direction not in {"fetch", "push"}:
        raise ExternalToolsError("invalid_direction", "Transport direction must be fetch or push.")
    root, _, common = _checkout(target.checkout)
    if common != target.common_dir:
        raise ExternalToolsError("common_dir_mismatch", "Checkout no longer belongs to the registered repository.")
    repository = target.spec.repository
    origin = _configured_urls(root, "origin", "url")
    if len(origin) != 1:
        raise ExternalToolsError("ambiguous_origin", "Managed checkout requires exactly one configured origin URL.")
    _require_urls(origin, repository)
    # Do not silently choose among two remote names pointing to the same repo.
    matches = []
    for name in _text(root, "remote").splitlines():
        urls = _text(root, "remote", "get-url", "--all", name).splitlines()
        for url in urls:
            try:
                match = _github_repository(url) == repository
            except ExternalToolsError:
                continue
            if match:
                matches.append(name)
                break
    if matches != ["origin"] or target.base_remote != "origin":
        raise ExternalToolsError("ambiguous_remote", "Exactly one remote name, origin, must identify the registered repository.")
    _require_urls(_text(root, "remote", "get-url", "--all", "origin").splitlines(), repository)
    if direction == "push":
        configured = _configured_urls(root, "origin", "pushurl")
        if configured:
            _require_urls(configured, repository)
        _require_urls(_text(root, "remote", "get-url", "--push", "--all", "origin").splitlines(), repository)


def resolve_managed_target(
    registry: Registry, repository: str, *, operation: str, code_root: Path | None = None,
) -> ManagedTarget:
    """Resolve one allowed operation root; a candidate cannot grant authority."""
    if operation not in _OPERATIONS:
        raise ExternalToolsError("unsupported_operation", "Unsupported managed-tool operation.")
    active = load_active_registry(registry.parent_root)
    if active is None or active != registry:
        raise ExternalToolsError("registry_not_active", "Registry must match the currently adopted parent blob.")
    spec = active.find_repository(_repository(repository))
    if spec is None:
        raise ExternalToolsError("unregistered_repository", "Repository is not registered in the adopted registry.")
    registered = active.parent_root / spec.relative_path
    if not registered.exists():
        raise ExternalToolsError("checkout_missing", "Registered checkout is absent; no fallback or clone was attempted.")
    permanent, git_dir, common = _checkout(registered)
    if git_dir != common or common != permanent / ".git" or not common.is_dir():
        raise ExternalToolsError("invalid_permanent_checkout", "Registered target must be a permanent checkout, not a linked worktree or submodule.")
    permanent_target = ManagedTarget(spec, permanent, common, "origin", active.commit)
    validate_transport_destination(permanent_target, direction="fetch")
    validate_transport_destination(permanent_target, direction="push")
    if code_root is None and operation in {"implement", "review-fix"}:
        raise ExternalToolsError("linked_checkout_required", "Implementation and repair require an explicit named-branch linked worktree.")
    root, git_dir, selected_common = _checkout(code_root if code_root is not None else permanent)
    if selected_common != common:
        raise ExternalToolsError("common_dir_mismatch", "CODE_ROOT must belong to the registered repository; a matching origin URL is not sufficient.")
    if operation in {"review-workspace", "cleanup"} and root != permanent:
        raise ExternalToolsError("permanent_checkout_required", "This operation requires the registered permanent checkout.")
    if operation in {"implement", "review-fix"}:
        branch = _git(root, "symbolic-ref", "-q", "HEAD", allowed=(0, 1))
        if git_dir == common or branch.returncode or not branch.stdout.startswith(b"refs/heads/"):
            raise ExternalToolsError("linked_checkout_required", "Implementation and repair require a named-branch linked worktree.")
    target = ManagedTarget(spec, root, common, "origin", active.commit)
    if root != permanent:
        validate_transport_destination(target, direction="fetch")
        validate_transport_destination(target, direction="push")
    return target
