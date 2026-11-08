"""Git workspace isolation and audits against real repositories."""

import asyncio
import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from tools.agent_runner import environ, process, workspace
from tools.agent_runner.workspace import (
    WorkspaceError,
    changed_checkouts,
    create_worktree,
    resolve_revision,
    snapshot_checkouts,
)


def git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    (root / "tracked.txt").write_text("committed\n")
    (root / ".gitignore").write_text("ignored/\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "initial")
    return root


# Returning a symbolic revision would let a later branch movement change the worktree commit.
def test_resolve_revision_pins_commit_not_branch(repository: Path) -> None:
    initial = git(repository, "rev-parse", "HEAD")
    assert resolve_revision(repository) == initial
    (repository / "tracked.txt").write_text("second\n")
    git(repository, "commit", "-qam", "second")
    assert resolve_revision(repository, "HEAD~1") == initial


# Hashing porcelain status alone misses edits to files that were already dirty at entry.
@pytest.mark.parametrize("kind", ["tracked", "symlink"])
def test_audit_detects_existing_dirty_content_edits(repository: Path, tmp_path: Path, kind: str) -> None:
    external = create_worktree(repository, "HEAD", tmp_path / "external checkout\nwith newline")
    path = external / ("tracked.txt" if kind in ("tracked", "staged") else "untracked.txt")
    if kind == "symlink":
        path.symlink_to("first-target")
    else:
        path.write_text("dirty before\n")
    if kind == "staged":
        git(external, "add", path.name)
    before = snapshot_checkouts(repository)
    assert set(before) == {str(repository), str(external)}
    assert changed_checkouts(before) == []
    if kind == "symlink":
        path.unlink()
        path.symlink_to("different-target")
    else:
        path.write_text("dirty after!\n")
    assert changed_checkouts(before) == [str(external)]
    assert all(value is not None and "dirty" not in value for value in before.values())


@pytest.mark.parametrize("mutation", ["add", "chmod", "index", "head"])
def test_audit_detects_checkout_mutations(repository: Path, mutation: str) -> None:
    before = snapshot_checkouts(repository)
    path = repository / "tracked.txt"
    if mutation == "delete":
        path.unlink()
    elif mutation == "add":
        (repository / "new.txt").write_text("new file")
    elif mutation == "chmod":
        path.chmod(0o755)
    elif mutation == "index":
        git(repository, "update-index", "--assume-unchanged", "tracked.txt")
        # Changing the staged blob, not merely an index flag, is audited.
        path.write_text("staged change")
        git(repository, "update-index", "--no-assume-unchanged", "tracked.txt")
        git(repository, "add", "tracked.txt")
        path.write_text("committed\n")
    else:
        git(repository, "commit", "--allow-empty", "-qm", "advance HEAD")
    assert changed_checkouts(before) == [str(repository)]


def test_repair_of_moved_main_and_linked_worktree_preserves_all_resources(repository: Path, tmp_path: Path) -> None:
    old_parent = tmp_path / "旧 root"
    external = create_worktree(repository, "HEAD", old_parent / "checkout\n日本語")
    (external / "tracked.txt").write_text("dirty tracked")
    (external / "tracked.txt").chmod(0o751)
    (external / "untracked.txt").write_text("untracked content")
    (external / "ignored").mkdir()
    (external / "ignored" / "resource").write_text("ignored content")
    (external / "link").symlink_to("untracked.txt")
    head = git(repository, "rev-parse", "HEAD")
    moved_repository = tmp_path / "new-repository"
    repository.rename(moved_repository)
    moved_parent = tmp_path / "new-root"
    old_parent.rename(moved_parent)
    moved = moved_parent / external.name
    before = snapshot_checkouts(moved_repository)
    assert workspace.audit_checkouts(before)[0].kind == "unavailable_before"
    assert before[str(external)] is None
    git(moved_repository, "worktree", "repair", str(moved))
    assert git(moved, "rev-parse", "HEAD") == head
    assert git(moved, "rev-parse", "--git-common-dir") == str(moved_repository / ".git")
    assert (moved / "tracked.txt").read_text() == "dirty tracked"
    assert (moved / "tracked.txt").stat().st_mode & 0o777 == 0o751
    assert (moved / "untracked.txt").read_text() == "untracked content"
    assert (moved / "ignored" / "resource").read_text() == "ignored content"
    assert os.readlink(moved / "link") == "untracked.txt"
    fresh = workspace.require_auditable_checkouts(moved_repository)
    assert set(fresh) == {str(moved_repository), str(moved)}
    assert workspace.audit_checkouts(fresh) == []
    assert changed_checkouts(before) == [str(external)]


# Initialized submodule working files remain tracked/nonignored checkout content.
def test_audit_detects_submodule_dirty_content(repository: Path, tmp_path: Path) -> None:
    # An initialized submodule whose HEAD matches the parent's gitlink.
    parent = tmp_path / "parent"
    parent.mkdir()
    git(parent, "init", "-q")
    git(parent, "config", "user.name", "Test")
    git(parent, "config", "user.email", "test@example.invalid")
    git(parent, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(repository), "sub")
    git(parent, "commit", "-qm", "parent with submodule")
    tracked = parent / "sub" / "tracked.txt"
    tracked.write_text("already dirty")
    before = snapshot_checkouts(parent)
    tracked.write_text("dirty edit")
    assert changed_checkouts(before) == [str(parent)]


@pytest.mark.parametrize(
    ("kind", "reason", "locked", "prunable"),
    [
        ("missing", "checkout_missing", False, True),
        ("locked", "checkout_missing", True, False),
    ],
)
def test_audit_diagnoses_unavailable_baseline(
    repository: Path,
    tmp_path: Path,
    kind: str,
    reason: str,
    locked: bool,
    prunable: bool,
) -> None:
    external = create_worktree(repository, "HEAD", tmp_path / "登録 checkout\n新しい場所")
    if kind == "locked":
        git(
            repository,
            "worktree",
            "lock",
            "--reason",
            "SECRET lock reason",
            str(external),
        )
    if kind in {"missing", "locked", "file"}:
        shutil.rmtree(external)
        if kind == "file":
            external.write_text("SECRET not a directory")
    elif kind == "broken":
        (external / ".git").write_text(f"gitdir: {tmp_path / 'SECRET-broken'}\n")
    else:
        external.chmod(0)
    try:
        before = snapshot_checkouts(repository)
        diagnostics = workspace.audit_checkouts(before)
        assert [item.model_dump() for item in diagnostics] == [
            {
                "path": str(external),
                "kind": "unavailable_before",
                "reason": reason,
                "locked": locked,
                "prunable": prunable,
                "protected": False,
            }
        ]
        assert all(workspace.blocks_acceptance(item) for item in diagnostics)
        with pytest.raises(workspace.CheckoutAuditError) as caught:
            workspace.require_auditable_checkouts(repository)
        assert caught.value.findings == diagnostics
        assert "SECRET" not in str(caught.value)
        assert changed_checkouts(before) == [str(external)]
    finally:
        if kind == "unreadable":
            external.chmod(0o755)


@pytest.mark.parametrize("mutation", ["disappear", "recover"])
def test_audit_distinguishes_changes_from_unavailability(repository: Path, tmp_path: Path, mutation: str) -> None:
    external = create_worktree(repository, "HEAD", tmp_path / "external")
    gitfile = external / ".git"
    original = gitfile.read_bytes()
    if mutation == "recover":
        gitfile.write_text(f"gitdir: {tmp_path / 'absent'}\n")
    before = snapshot_checkouts(repository)
    if mutation == "recover":
        gitfile.write_bytes(original)
    elif mutation == "disappear":
        shutil.rmtree(external)
    else:
        (external / "tracked.txt").write_text("modified")
    diagnostics = workspace.audit_checkouts(before)
    assert [item.path for item in diagnostics] == [str(external)]
    assert (
        diagnostics[0].kind
        == {
            "change": "content_changed",
            "disappear": "unavailable_after",
            "recover": "unavailable_before",
        }[mutation]
    )
    assert (
        diagnostics[0].reason
        == {
            "change": "content_changed",
            "disappear": "checkout_missing",
            "recover": "git_unavailable",
        }[mutation]
    )
    assert changed_checkouts(before) == [str(external)]
    if mutation == "recover":
        assert workspace.require_auditable_checkouts(repository)[str(external)] is not None
        assert workspace.audit_checkouts(snapshot_checkouts(repository)) == []


def test_registration_list_failure_still_stops_snapshot(repository: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*_: object) -> bytes:
        raise WorkspaceError()

    monkeypatch.setattr(workspace, "_git", unavailable)
    with pytest.raises(WorkspaceError):
        snapshot_checkouts(repository)


# Preparation must consume the already-pinned commit, without synchronous Git
# resolution, and ignore ambient Git routing when creating a detached worktree.
def test_async_preparation_uses_pinned_commit_and_safe_environment(
    repository: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commit = resolve_revision(repository)
    monkeypatch.setenv("GIT_DIR", "/bogus-ambient-git")
    # Ambient Git routing in the exec environment must not reach the helpers.
    monkeypatch.setattr(environ, "_literal", environ.literal_environ() | {"GIT_DIR": "/bogus-ambient-git"})

    def forbidden(*_: object) -> bytes:
        raise AssertionError("synchronous Git in async preparation")

    monkeypatch.setattr(workspace, "_git", forbidden)
    assert callable(getattr(workspace, "prepare_worktree", None))
    destination = tmp_path / "async-worktree"
    result = asyncio.run(
        workspace.prepare_worktree(
            repository,
            commit,
            destination,
            # Only bounds a hang; creating the worktree stretches on a loaded host (#223).
            deadline_seconds=30,
            cancel=threading.Event(),
            stdout_path=tmp_path / "worktree.stdout.log",
            stderr_path=tmp_path / "worktree.stderr.log",
        )
    )
    assert result.state is None and result.exit_code == 0 and result.stop_confirmed
    assert (destination / "tracked.txt").read_text() == "committed\n"
    monkeypatch.delenv("GIT_DIR")
    assert git(destination, "rev-parse", "HEAD") == commit
    assert subprocess.run(["git", "-C", str(destination), "symbolic-ref", "-q", "HEAD"]).returncode != 0


def test_git_preparation_stops_term_resistant_child_of_exited_hook(repository: Path, tmp_path: Path) -> None:
    identity = tmp_path / "hook-child.identity"
    code = (
        "import os,pathlib,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "pid=os.getpid(); start=pathlib.Path(f'/proc/{pid}/stat').read_bytes().rsplit(b')',1)[1].split()[19]; "
        f"pathlib.Path({str(identity)!r}).write_text(str(pid)+' '+start.decode()); time.sleep(60)"
    )
    hook = repository / ".git" / "hooks" / "post-checkout"
    hook.write_text(
        f"#!/bin/sh\n{shlex.quote(sys.executable)} -c {shlex.quote(code)} &\n"
        f"while [ ! -s {shlex.quote(str(identity))} ]; do sleep 0.01; done\n"
    )
    hook.chmod(0o755)
    try:
        result = asyncio.run(
            workspace.prepare_worktree(
                repository,
                resolve_revision(repository),
                tmp_path / "hook-worktree",
                # Success, not a timeout, is checked; the deadline only bounds a hang (#223).
                deadline_seconds=30,
                cancel=threading.Event(),
                stdout_path=tmp_path / "worktree.stdout.log",
                stderr_path=tmp_path / "worktree.stderr.log",
            )
        )
        assert result.state is None and result.exit_code == 0 and result.stop_confirmed
        pid = int(identity.read_text().split()[0])
        current = process._read_proc(pid)  # pyright: ignore[reportPrivateUsage] - real hook child evidence
        assert current is None or current.state in ("Z", "X")
    finally:
        if identity.exists():
            pid, start = map(int, identity.read_text().split())
            current = process._read_proc(pid)  # pyright: ignore[reportPrivateUsage] - identity-safe fixture cleanup
            if current is not None and current.starttime == start and current.state not in ("Z", "X"):
                os.kill(pid, signal.SIGKILL)


# Callers list where a writes=False agent may write in a checkout's shared Git data (agent-workspace#658).
def test_git_common_dir_of_a_linked_worktree_is_the_main_git_directory(repository: Path, tmp_path: Path) -> None:
    linked = create_worktree(repository, "HEAD", tmp_path / "linked")
    expected = (repository / ".git").resolve()
    assert workspace.git_common_dir(repository) == expected
    assert workspace.git_common_dir(linked) == expected


def test_git_common_dir_ignores_ambient_git_routing(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-q")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setattr(environ, "_literal", environ.literal_environ() | {"GIT_DIR": str(other / ".git")})
    assert workspace.git_common_dir(repository) == (repository / ".git").resolve()


# Other sessions change and clean up their own worktrees while a run is going (#756). Only the
# checkout given to the run and the main worktree may block it; a checkout that vanished while
# still registered stays unauditable.
@pytest.mark.parametrize(
    ("which", "mutation", "kind", "protected"),
    [
        ("target", "change", "content_changed", True),
        ("main", "change", "content_changed", True),
        ("other", "remove", "removed", False),
        ("other", "vanish", "unavailable_after", False),
    ],
)
def test_audit_protects_only_the_target_and_the_main_worktree(
    repository: Path, tmp_path: Path, which: str, mutation: str, kind: str, protected: bool
) -> None:
    target = create_worktree(repository, "HEAD", tmp_path / "対象 checkout\n改行")
    other = create_worktree(repository, "HEAD", tmp_path / "other session")
    before = snapshot_checkouts(target)
    checkout = {"target": target, "main": repository, "other": other}[which]
    if mutation == "change":
        (checkout / "tracked.txt").write_text("changed by another session\n")
    elif mutation == "remove":
        git(repository, "worktree", "remove", "--force", str(checkout))
    else:
        shutil.rmtree(checkout)
    [finding] = workspace.audit_checkouts(before)
    assert (finding.path, finding.kind, finding.protected) == (str(checkout), kind, protected)
    assert workspace.blocks_acceptance(finding) is (protected or kind == "unavailable_after")


def test_target_given_through_a_symlink_is_protected(repository: Path, tmp_path: Path) -> None:
    target = create_worktree(repository, "HEAD", tmp_path / "feature")
    link = tmp_path / "link to feature"
    link.symlink_to(target, target_is_directory=True)
    before = snapshot_checkouts(link)
    (target / "tracked.txt").write_text("changed\n")
    [finding] = workspace.audit_checkouts(before)
    assert (finding.path, finding.protected) == (str(target), True)
    assert workspace.blocks_acceptance(finding)


def test_unidentified_target_protects_every_checkout(repository: Path, tmp_path: Path) -> None:
    bare = tmp_path / "bare.git"
    git(tmp_path, "clone", "-q", "--bare", str(repository), str(bare))
    linked = create_worktree(bare, "HEAD", tmp_path / "linked")
    before = snapshot_checkouts(bare)
    (linked / "tracked.txt").write_text("changed\n")
    [finding] = workspace.audit_checkouts(before)
    assert (finding.path, finding.kind, finding.protected) == (str(linked), "content_changed", True)
    assert workspace.blocks_acceptance(finding)


def test_unlisted_registrations_keep_a_vanished_checkout_unauditable(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = create_worktree(repository, "HEAD", tmp_path / "other session")
    before = snapshot_checkouts(repository)
    git(repository, "worktree", "remove", "--force", str(other))
    original = workspace._git  # pyright: ignore[reportPrivateUsage]

    def failing(repository: Path, *arguments: str) -> bytes:
        if arguments[:2] == ("worktree", "list"):
            raise WorkspaceError()
        return original(repository, *arguments)

    monkeypatch.setattr(workspace, "_git", failing)
    [finding] = workspace.audit_checkouts(before)
    assert (finding.path, finding.kind, finding.protected) == (str(other), "unavailable_after", False)
    assert workspace.blocks_acceptance(finding)
