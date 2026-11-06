"""Acquire exactly one adopted tool, with nonblocking exclusion and no replacement.

No setup, hooks, local main branch, deletion, or rename/copy fallback. Failed
staging areas are evidence: callers decide what to do with them, never this code.
"""
from __future__ import annotations

from collections.abc import Sequence
from contextlib import ExitStack
import ctypes
import errno
import fcntl
import os
from pathlib import Path
import stat
import subprocess
import uuid

from .identity import resolve_managed_target, validate_transport_destination
from .models import CloneResult, ExternalToolsError, ManagedTarget, Registry, ToolSpec
from .registry import _github_repository, load_active_registry


class _Directories:
    """Hold directory capabilities and recheck each name against its held inode.

    Every open/mkdir/rename below is relative to a held descriptor. Checking the
    names as well catches moved ancestors without following their replacements.
    """

    def __init__(self, stack: ExitStack) -> None:
        self.stack = stack
        self.nodes: list[tuple[int, str, int]] = []

    def hold(self, fd: int) -> int:
        self.stack.callback(os.close, fd)
        return fd

    def child(self, parent: int, name: str, *, create: bool = False) -> int:
        self.check()
        if create:
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent)
            except FileExistsError:
                pass
        fd = self.hold(os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent))
        self.nodes.append((parent, name, fd))
        self.check()
        return fd

    def open(self, path: Path) -> int:
        fd = self.hold(os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC))
        for name in path.parts[1:]:
            fd = self.child(fd, name)
        return fd

    def check(self) -> None:
        for parent, name, fd in self.nodes:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            held = os.fstat(fd)
            if (current.st_dev, current.st_ino, stat.S_IFMT(current.st_mode)) != (
                held.st_dev, held.st_ino, stat.S_IFMT(held.st_mode)
            ):
                raise ExternalToolsError("path_changed", "A checked path was replaced or moved; no publication was attempted.")


def _run(args: Sequence[str], *, directory_fd: int) -> subprocess.CompletedProcess[bytes]:
    """Internal process boundary (the sole test seam); never accept a CLI executable.

    The child inherits the held cwd descriptor, not a possibly swapped pathname.
    Keep user transport configuration visible for destination checks, but discard
    inherited Git selectors/config injection/traces. No optional index refreshes,
    templates, hooks, or fsmonitor programs are needed for acquisition.
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        ["git", "--no-replace-objects", "--no-optional-locks", "-c", "core.hooksPath=/dev/null",
         "-c", "core.fsmonitor=false", "--git-dir=.git", "--work-tree=.", *args],
        cwd=f"/proc/self/fd/{directory_fd}", pass_fds=(directory_fd,), env=env, capture_output=True,
    )


def _checked(directories: _Directories, fd: int, *args: str) -> bytes:
    directories.check()
    try:
        result = _run(args, directory_fd=fd)
    except OSError:
        raise ExternalToolsError("git_failed", "Cannot run Git for the selected tool; staging was retained.") from None
    directories.check()
    if result.returncode:
        # Never return subprocess output, which may contain credentials or secrets.
        raise ExternalToolsError("git_failed", "Git did not complete acquisition; staging was retained.")
    return result.stdout


def _active(registry: Registry, directories: _Directories) -> None:
    directories.check()
    active = load_active_registry(registry.parent_root)
    if active is None or active != registry:
        raise ExternalToolsError("registry_not_active", "Registry must still match the adopted parent commit and content.")
    directories.check()


def _transport(directories: _Directories, fd: int, spec: ToolSpec) -> None:
    raw = _checked(directories, fd, "config", "--null", "--get-all", "remote.origin.url")
    urls = raw.decode("utf-8", errors="replace").removesuffix("\x00").split("\x00")
    if len(urls) != 1:
        raise ExternalToolsError("remote_mismatch", "Acquisition requires exactly one origin URL.")
    for flags in ((), ("--push",)):
        urls.extend(_checked(directories, fd, "remote", "get-url", *flags, "--all", "origin").decode("utf-8", errors="replace").splitlines())
    try:
        valid = all(_github_repository(url) == spec.repository for url in urls)
    except ExternalToolsError:
        valid = False
    if not valid:
        raise ExternalToolsError("remote_mismatch", "Effective transport must identify only the selected GitHub repository, without credentials.")


def _rename_noreplace(parent_fd: int, source: str, destination: str) -> None:
    """Linux renameat2(RENAME_NOREPLACE), with no destructive fallback."""
    try:
        rename = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError:
        raise ExternalToolsError("publish_unsupported", "Nonreplacement rename is unavailable; staging was retained.") from None
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent_fd, os.fsencode(source), parent_fd, os.fsencode(destination), 1) != 0:
        code = ctypes.get_errno()
        if code in {errno.EEXIST, errno.ENOTEMPTY}:
            reason = "destination_exists"
        elif code in {errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP, errno.EXDEV}:
            reason = "publish_unsupported"
        else:
            reason = "publish_failed"
        raise ExternalToolsError(reason, "Nonreplacement publication stopped; existing data and staging were retained.")


def clone_tool(registry: Registry, key: str) -> CloneResult:
    """Clone one key from the active registry, or leave existing data untouched."""
    spec = next((entry for entry in registry.entries if entry.key == key), None)
    path = registry.parent_root / spec.relative_path if spec else registry.parent_root
    staging: Path | None = None
    stage_fd: int | None = None
    with ExitStack() as stack:
        directories = _Directories(stack)
        try:
            # Candidate values must not even authorize lock or directory creation.
            _active(registry, directories)
            if spec is None:
                raise ExternalToolsError("unknown_tool", "Select exactly one registered tool key.")
            parent_fd = directories.open(registry.parent_root)
            common_fd = directories.child(parent_fd, ".git")
            control_fd = directories.child(common_fd, "external-tools", create=True)
            locks_fd = directories.child(control_fd, "locks", create=True)
            lock_name = f"{spec.key}.lock"
            lock_fd = directories.hold(os.open(
                lock_name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                0o600, dir_fd=locks_fd,
            ))
            lock_stat = os.fstat(lock_fd)
            if not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_nlink != 1:
                raise ExternalToolsError("unsafe_lock", "Lock must be an unaliased regular file.")
            directories.nodes.append((locks_fd, lock_name, lock_fd))
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ExternalToolsError("busy", "Another acquisition holds this tool's lock.") from None
            _active(registry, directories)
            destination_fd = parent_fd
            for name in Path(spec.relative_path).parts[:-1]:
                destination_fd = directories.child(destination_fd, name, create=True)
            destination = path.name
            try:
                existing = os.stat(destination, dir_fd=destination_fd, follow_symlinks=False)
            except FileNotFoundError:
                existing = None
            if existing is not None:
                if not stat.S_ISDIR(existing.st_mode):
                    raise ExternalToolsError("invalid_target", "Existing target is not a real checkout directory.")
                target_fd = directories.child(destination_fd, destination)
                resolve_managed_target(registry, spec.repository, operation="review-workspace")
                # status can omit edited assume-unchanged/skip-worktree entries.
                # Accept only ordinary cached (H) entries; do not clear user flags
                # or refresh their index just to make the checkout inspectable.
                entries = _checked(directories, target_fd, "ls-files", "-v", "-z")
                if any(entry[:1] != b"H" for entry in entries.split(b"\0") if entry):
                    raise ExternalToolsError("unverifiable_index", "Index flags prevent complete checkout verification.")
                dirty = _checked(directories, target_fd, "status", "--porcelain=v1", "--untracked-files=all", "--ignored")
                if dirty:
                    raise ExternalToolsError("dirty_checkout", "Existing checkout contains changes or local residue.")
                _active(registry, directories)
                return CloneResult("present", path, None, None, registry.commit)

            stage_name = f".external-tools-{key}-{uuid.uuid4().hex}"
            # Exclusive creation: even an extremely unlikely collision is not adopted.
            os.mkdir(stage_name, mode=0o700, dir_fd=destination_fd)
            staging = path.parent / stage_name
            stage_fd = directories.child(destination_fd, stage_name)
            _checked(directories, stage_fd, "init", "--template=", "--initial-branch=external-tools-unborn", ".")
            directories.child(stage_fd, ".git")
            _checked(directories, stage_fd, "remote", "add", "origin", f"https://github.com/{spec.repository}.git")
            _active(registry, directories)
            _transport(directories, stage_fd, spec)
            ref = f"refs/remotes/origin/{spec.base_branch}"
            _checked(directories, stage_fd, "fetch", "--no-recurse-submodules", "--no-tags", "origin", f"refs/heads/{spec.base_branch}:{ref}")
            _checked(directories, stage_fd, "checkout", "--detach", ref, "--")
            head = _checked(directories, stage_fd, "rev-parse", "--verify", "HEAD^{commit}")
            fetched = _checked(directories, stage_fd, "rev-parse", "--verify", f"{ref}^{{commit}}")
            if head != fetched or _checked(directories, stage_fd, "status", "--porcelain=v1", "--untracked-files=all", "--ignored"):
                raise ExternalToolsError("incomplete_checkout", "Fetched checkout did not verify cleanly; staging was retained.")
            # Reconfirm both authority and effective destinations immediately before
            # publication. Only the kernel decides whether destination is still free.
            directories.check()
            target = ManagedTarget(spec, staging, staging / ".git", "origin", registry.commit)
            validate_transport_destination(target, direction="fetch")
            validate_transport_destination(target, direction="push")
            _active(registry, directories)
            directories.check()
            _rename_noreplace(destination_fd, stage_name, destination)
            return CloneResult("cloned", path, None, None, registry.commit)
        except ExternalToolsError as error:
            status = "failed" if error.reason_code == "git_failed" else "blocked"
            reason = error.reason_code
        except OSError:
            status, reason = "blocked", "unsafe_path"
        if stage_fd is not None:
            # A renamed ancestor/stage is still held. Report its actual evidence
            # location rather than accidentally following the replacement symlink.
            try:
                staging = Path(os.readlink(f"/proc/self/fd/{stage_fd}"))
            except OSError:
                pass
        return CloneResult(status, path, staging, reason, registry.commit)
