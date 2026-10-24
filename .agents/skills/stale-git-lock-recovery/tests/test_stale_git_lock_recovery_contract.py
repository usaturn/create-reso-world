"""Contract tests for the stale-git-lock-recovery skill and its helper script.

The skill removes a leftover git ``index.lock`` only after proving that no live
process holds it. These tests guard executable snippet safety and the
observable behavior of ``scripts/stale_git_lock.sh`` against temporary
repositories.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "stale-git-lock-recovery"
SKILL = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "stale_git_lock.sh"

# Commands the helper script itself needs when `lsof` is absent. The list is
# deliberately explicit so the PATH-limited tests can build a PATH without
# `lsof` while keeping the rest of the toolchain available.
CORE_TOOLS = ("bash", "cat", "dirname", "basename", "flock", "git", "readlink", "rm", "stat", "tr")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def bash_blocks() -> list[str]:
    return re.findall(r"```bash\n(.*?)```", read(SKILL), re.DOTALL)


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def resolve_lock_path(repo: Path) -> Path:
    raw = git(repo, "rev-parse", "--path-format=absolute", "--git-path", "index.lock").strip()
    return Path(raw)


def limited_path_env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    """A PATH without `lsof`, plus caller-supplied environment overrides."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for tool in CORE_TOOLS:
        link = bin_dir / tool
        if not link.exists():
            target = shutil.which(tool)
            assert target, f"{tool} is required for the PATH-limited tests"
            link.symlink_to(target)
    env = {**os.environ, "PATH": str(bin_dir)}
    env.update(overrides)
    return env


def quiet_env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    """No lsof, and a PROC_ROOT whose only process is not git.

    Tests that expect a stale lock (exit 11) use it, so that git processes
    running elsewhere on the machine (for example with a GIT_WORK_TREE but no
    git dir, which cannot be ruled out) cannot turn the answer into unknown.
    Holder detection itself is covered by the tests that run real processes.
    """
    proc_root = tmp_path / "quiet-proc"
    if not proc_root.exists():
        fake_process(proc_root, 4242, "bash", cwd=tmp_path)
    return limited_path_env(tmp_path, PROC_ROOT=str(proc_root), **overrides)


def make_git_repo(repo: Path) -> Path:
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-qm", "init")
    return repo


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    return make_git_repo(tmp_path / "repo")


@contextlib.contextmanager
def holding_process(lock: Path, ready: Path) -> Iterator[subprocess.Popen[bytes]]:
    """Run a process group that keeps ``lock`` open, then yields it."""
    holder_script = 'exec 9>"$1" || exit 1; : >"$2"; sleep 60'
    process = subprocess.Popen(
        ["bash", "-c", holder_script, "holder", str(lock), str(ready)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not ready.exists():
            if process.poll() is not None:
                raise AssertionError("holder process exited before opening the lock")
            if time.monotonic() > deadline:
                raise AssertionError("holder process did not open the lock in time")
            time.sleep(0.05)
        yield process
    finally:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)


@contextlib.contextmanager
def unlistable_process(tmp_path: Path, comm: str) -> Iterator[Path]:
    """A fake PROC_ROOT with one PID whose fd directory cannot be listed."""
    proc_root = tmp_path / "proc"
    pid_dir = proc_root / "4242"
    fd_dir = pid_dir / "fd"
    fd_dir.mkdir(parents=True)
    (pid_dir / "comm").write_text(f"{comm}\n", encoding="utf-8")
    (pid_dir / "cmdline").write_bytes(f"{comm}\0".encode())
    fd_dir.chmod(0o000)
    try:
        yield proc_root
    finally:
        fd_dir.chmod(0o700)


# --------------------------------------------------------------------------
# Executable snippet safety
# --------------------------------------------------------------------------


def test_bash_snippets_do_not_run_destructive_git_commands() -> None:
    # These shortcuts can discard user work; prose may explain the prohibition
    # in any words, but executable instructions must never invoke them.
    for block in bash_blocks():
        for command in ("git clean", "git reset --hard", "git checkout -f"):
            assert command not in block, f"destructive command in snippet: {command}"


def test_skill_never_removes_the_lock_by_hand() -> None:
    # Only the helper may remove the lock, after it has ruled out a live holder;
    # a manual rm in a snippet would skip that check.
    for block in bash_blocks():
        assert "rm " not in block, f"SKILL.md must not show a manual rm:\n{block}"


# --------------------------------------------------------------------------
# Helper script behavior
# --------------------------------------------------------------------------


def test_stale_lock_is_detected_then_cleared(git_repo: Path, tmp_path: Path) -> None:
    env = quiet_env(tmp_path)
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")

    check = run_script("check", "--json", "--repo", str(git_repo), env=env)
    assert check.returncode == 11, check.stderr
    payload = json.loads(check.stdout)
    assert payload["path"] == str(lock)
    assert payload["exists"] is True
    assert payload["size"] == 0
    assert payload["holder"] == "absent"
    assert payload["stale"] is True

    clear = run_script("clear", "--json", "--repo", str(git_repo), env=env)
    assert clear.returncode == 0, clear.stderr
    assert not lock.exists()
    cleared = json.loads(clear.stdout)
    assert cleared["path"] == str(lock)
    assert cleared["removed"] is True
    assert cleared["exists"] is False

    assert run_script("check", "--repo", str(git_repo), env=env).returncode == 0


def test_rm_failure_reports_error_without_json(git_repo: Path, tmp_path: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    git_dir = lock.parent
    git_dir.chmod(0o500)
    try:
        result = run_script("clear", "--json", "--repo", str(git_repo), env=quiet_env(tmp_path))
        assert result.returncode == 1, (result.stdout, result.stderr)
        assert result.stdout == ""
        assert "failed to remove" in result.stderr
    finally:
        git_dir.chmod(0o755)


def test_live_holder_blocks_check_and_clear(git_repo: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    ready = git_repo / "holder.ready"

    with holding_process(lock, ready):
        check = run_script("check", "--json", "--repo", str(git_repo))
        assert check.returncode == 10, check.stderr
        payload = json.loads(check.stdout)
        assert payload["holder"] == "present"
        assert payload["stale"] is False

        clear = run_script("clear", "--json", "--repo", str(git_repo))
        assert clear.returncode == 10, clear.stderr
        assert not json.loads(clear.stdout)["removed"]
        assert lock.exists(), "clear must not delete a lock with a live holder"


def test_proc_scan_finds_holder_when_lsof_is_unavailable(git_repo: Path, tmp_path: Path) -> None:
    env = limited_path_env(tmp_path)
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    ready = git_repo / "holder.ready"

    with holding_process(lock, ready):
        check = run_script("check", "--json", "--repo", str(git_repo), env=env)
        assert check.returncode == 10, check.stderr
        assert json.loads(check.stdout)["holder"] == "present"

        clear = run_script("clear", "--repo", str(git_repo), env=env)
        assert clear.returncode == 10, clear.stderr
        assert lock.exists()


def test_unlistable_git_process_is_an_unknown_holder(git_repo: Path, tmp_path: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    with unlistable_process(tmp_path, "git") as proc_root:
        env = limited_path_env(tmp_path, PROC_ROOT=str(proc_root))

        check = run_script("check", "--json", "--repo", str(git_repo), env=env)
        assert check.returncode == 12, (check.stdout, check.stderr)
        payload = json.loads(check.stdout)
        assert payload["holder"] == "unknown"
        assert payload["stale"] is False

        clear = run_script("clear", "--json", "--repo", str(git_repo), env=env)
        assert clear.returncode == 12, (clear.stdout, clear.stderr)
        assert json.loads(clear.stdout)["removed"] is False
        assert lock.exists(), "clear must not delete when the holder is unknown"


def test_clear_removes_only_the_symlink_lock_not_its_target(git_repo: Path, tmp_path: Path) -> None:
    env = quiet_env(tmp_path)
    lock = resolve_lock_path(git_repo)
    target = git_repo / "precious.bin"
    target.write_bytes(b"do not delete")
    lock.symlink_to(target)

    check = run_script("check", "--json", "--repo", str(git_repo), env=env)
    assert check.returncode == 11, check.stderr
    assert json.loads(check.stdout)["exists"] is True

    clear = run_script("clear", "--json", "--repo", str(git_repo), env=env)
    assert clear.returncode == 0, clear.stderr
    assert json.loads(clear.stdout)["removed"] is True
    assert not lock.is_symlink()
    assert target.read_bytes() == b"do not delete"


def test_linked_worktree_lock_is_detected_at_its_own_path(git_repo: Path, tmp_path: Path) -> None:
    linked = tmp_path / "linked"
    git(git_repo, "worktree", "add", "-q", "-b", "linked-branch", str(linked))

    lock = resolve_lock_path(linked)
    assert "worktrees" in str(lock), "fixture must exercise the linked worktree path"
    lock.write_bytes(b"")

    check = run_script("check", "--json", "--repo", str(linked), env=quiet_env(tmp_path))
    assert check.returncode == 11, check.stderr
    payload = json.loads(check.stdout)
    assert payload["path"] == str(lock)
    assert payload["stale"] is True
    assert lock.exists()


def test_clear_refuses_force(git_repo: Path) -> None:
    # F∩S: force must not bypass holder checks and delete a live lock.
    result = run_script("clear", "--force", "--repo", str(git_repo))
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.strip()


# --------------------------------------------------------------------------
# git holds index.lock with its fd closed while hooks or the editor run
# --------------------------------------------------------------------------


def wait_for(predicate, what: str, process: subprocess.Popen[str] | None = None) -> None:
    deadline = time.monotonic() + 20
    while not predicate():
        if process is not None and process.poll() is not None:
            raise AssertionError(f"process exited before {what}: {process.communicate()}")
        if time.monotonic() > deadline:
            raise AssertionError(f"timed out waiting for {what}")
        time.sleep(0.05)


@pytest.mark.parametrize("pause_in", ["pre-commit hook", "commit message editor"])
def test_git_commit_holding_the_lock_without_an_fd_is_not_stale(
    git_repo: Path, tmp_path: Path, pause_in: str
) -> None:
    ready = tmp_path / "paused"
    release = tmp_path / "release"
    pause = f': >"{ready}"; while [ ! -e "{release}" ]; do sleep 0.05; done'
    env = {**os.environ}
    if pause_in == "pre-commit hook":
        hook = git_repo / ".git" / "hooks" / "pre-commit"
        hook.write_text(f"#!/bin/sh\n{pause}\n", encoding="utf-8")
        hook.chmod(0o755)
        args = ["git", "commit", "-a", "-qm", "second"]
    else:
        editor = tmp_path / "editor.sh"
        editor.write_text(f'#!/bin/sh\n{pause}\necho second >"$1"\n', encoding="utf-8")
        editor.chmod(0o755)
        env["GIT_EDITOR"] = str(editor)
        args = ["git", "commit", "-a", "-q"]
    (git_repo / "README.md").write_text("changed\n", encoding="utf-8")
    lock = resolve_lock_path(git_repo)

    commit = subprocess.Popen(
        args, cwd=git_repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        wait_for(ready.exists, f"the {pause_in}", commit)
        assert lock.exists(), "git must hold index.lock while the commit is paused"

        check = run_script("check", "--json", "--repo", str(git_repo))
        assert check.returncode == 12, (check.stdout, check.stderr)
        payload = json.loads(check.stdout)
        assert payload["holder"] == "unknown"
        assert payload["stale"] is False
        assert f"pid {commit.pid} (git)" in check.stderr

        clear = run_script("clear", "--json", "--repo", str(git_repo))
        assert clear.returncode == 12, (clear.stdout, clear.stderr)
        assert json.loads(clear.stdout)["removed"] is False
        assert lock.exists(), "clear must not delete a lock held by a paused git commit"
    finally:
        release.touch()
        stdout, stderr = commit.communicate(timeout=30)

    assert commit.returncode == 0, (stdout, stderr)
    assert not lock.exists()
    assert git(git_repo, "show", "HEAD:README.md") == "changed\n"
    assert git(git_repo, "ls-tree", "--name-only", "HEAD").split() == ["README.md"]


def fake_process(
    proc_root: Path,
    pid: int,
    comm: str,
    *,
    cwd: Path | None = None,
    environ: dict[str, str] | None = None,
    fds: tuple[Path, ...] = (Path("/dev/null"),),
) -> None:
    """Add one PID to a fake PROC_ROOT. ``cwd=None`` leaves the cwd unreadable."""
    pid_dir = proc_root / str(pid)
    (pid_dir / "fd").mkdir(parents=True)
    (pid_dir / "comm").write_text(f"{comm}\n", encoding="utf-8")
    (pid_dir / "cmdline").write_bytes(f"{comm}\0status\0".encode())
    (pid_dir / "environ").write_bytes(
        b"".join(f"{key}={value}\0".encode() for key, value in (environ or {}).items())
    )
    if cwd is not None:
        (pid_dir / "cwd").symlink_to(cwd)
    for number, target in enumerate(fds):
        (pid_dir / "fd" / str(number)).symlink_to(target)


def check_with_proc(repo: Path, tmp_path: Path, proc_root: Path) -> subprocess.CompletedProcess[str]:
    env = limited_path_env(tmp_path, PROC_ROOT=str(proc_root))
    return run_script("check", "--json", "--repo", str(repo), env=env)


def test_git_process_inside_the_repository_makes_the_holder_unknown(
    git_repo: Path, tmp_path: Path
) -> None:
    resolve_lock_path(git_repo).write_bytes(b"")
    cwd = git_repo / ".git"
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=cwd)

    check = check_with_proc(git_repo, tmp_path, proc_root)
    assert check.returncode == 12, (check.stdout, check.stderr)
    assert json.loads(check.stdout)["holder"] == "unknown"
    assert "pid 4242 (git)" in check.stderr


@pytest.mark.parametrize(
    "variable", ["GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"]
)
def test_git_process_pointing_at_the_repository_through_its_environment_is_unknown(
    git_repo: Path, tmp_path: Path, variable: str
) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    value = {
        "GIT_DIR": str(git_repo / ".git"),
        "GIT_WORK_TREE": str(git_repo),
        "GIT_COMMON_DIR": str(git_repo / ".git"),
        # a relative GIT_INDEX_FILE is resolved against the process's cwd
        "GIT_INDEX_FILE": os.path.relpath(lock.parent / "index", elsewhere),
    }[variable]
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=elsewhere, environ={variable: value})

    check = check_with_proc(git_repo, tmp_path, proc_root)
    assert check.returncode == 12, (check.stdout, check.stderr)


@pytest.mark.parametrize(
    "arguments",
    [("--git-dir=../repo/.git", "status"), ("--work-tree", "../repo", "commit", "-a")],
)
def test_git_process_pointing_at_the_repository_through_its_options_is_unknown(
    git_repo: Path, tmp_path: Path, arguments: tuple[str, ...]
) -> None:
    resolve_lock_path(git_repo).write_bytes(b"")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=elsewhere)
    (proc_root / "4242" / "cmdline").write_bytes(
        b"".join(f"{word}\0".encode() for word in ("git", *arguments))
    )

    check = check_with_proc(git_repo, tmp_path, proc_root)
    assert check.returncode == 12, (check.stdout, check.stderr)


def test_git_process_with_a_relative_repository_reference_cannot_be_ruled_out(
    git_repo: Path, tmp_path: Path
) -> None:
    # git may have changed directory since it started, so a relative value
    # cannot be resolved against the current cwd.
    resolve_lock_path(git_repo).write_bytes(b"")
    other = make_git_repo(tmp_path / "other")
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=other)
    words = ["git", "--git-dir", "../repo/.git", "status"]
    (proc_root / "4242" / "cmdline").write_bytes(b"".join(f"{w}\0".encode() for w in words))

    check = check_with_proc(git_repo, tmp_path, proc_root)
    assert check.returncode == 12, (check.stdout, check.stderr)


def test_git_process_with_an_unreadable_cwd_is_unknown(git_repo: Path, tmp_path: Path) -> None:
    resolve_lock_path(git_repo).write_bytes(b"")
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=None)

    check = check_with_proc(git_repo, tmp_path, proc_root)
    assert check.returncode == 12, (check.stdout, check.stderr)


@pytest.mark.parametrize("inside", [".git", ".git/hooks", ".git/worktrees/linked"])
def test_repo_inside_the_git_dir_is_refused(git_repo: Path, tmp_path: Path, inside: str) -> None:
    # Inside .git there is no work tree top, so a git process holding the lock
    # with its fd closed could be missed; the script must refuse instead.
    git(git_repo, "worktree", "add", "-q", "-b", "linked", str(tmp_path / "linked"))
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    resolve_lock_path(tmp_path / "linked").write_bytes(b"")
    for mode in ("check", "clear"):
        result = run_script(mode, "--json", "--repo", str(git_repo / inside))
        assert result.returncode == 2, (mode, result.stdout, result.stderr)
        assert result.stdout == ""
        assert "pass the work tree" in result.stderr
    assert lock.exists()
    assert resolve_lock_path(tmp_path / "linked").exists()


def fake_lsof_env(tmp_path: Path, body: str, **overrides: str) -> dict[str, str]:
    env = limited_path_env(tmp_path, **overrides)
    lsof = Path(env["PATH"]) / "lsof"
    lsof.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    lsof.chmod(0o755)
    return env


def test_union_keeps_unknown_when_lsof_finds_nothing(git_repo: Path, tmp_path: Path) -> None:
    resolve_lock_path(git_repo).write_bytes(b"")
    with unlistable_process(tmp_path, "git") as proc_root:
        env = fake_lsof_env(tmp_path, "exit 1", PROC_ROOT=str(proc_root))
        check = run_script("check", "--json", "--repo", str(git_repo), env=env)
        assert check.returncode == 12, (check.stdout, check.stderr)


def test_without_proc_lsof_alone_cannot_prove_a_lock_stale(git_repo: Path, tmp_path: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    env = fake_lsof_env(tmp_path, "exit 1", PROC_ROOT=str(tmp_path / "no-proc"))
    check = run_script("check", "--json", "--repo", str(git_repo), env=env)
    assert check.returncode == 12, (check.stdout, check.stderr)
    clear = run_script("clear", "--json", "--repo", str(git_repo), env=env)
    assert clear.returncode == 12, (clear.stdout, clear.stderr)
    assert lock.exists()


# --------------------------------------------------------------------------
# Target selection and clear serialization
# --------------------------------------------------------------------------


@pytest.mark.parametrize("variables", [("GIT_DIR",), ("GIT_DIR", "GIT_WORK_TREE"), ("GIT_COMMON_DIR",)])
def test_inherited_git_environment_does_not_redirect_the_target(
    tmp_path: Path, variables: tuple[str, ...]
) -> None:
    target = make_git_repo(tmp_path / "target")
    other = make_git_repo(tmp_path / "other")
    target_lock = resolve_lock_path(target)
    other_lock = resolve_lock_path(other)
    target_lock.write_bytes(b"")
    other_lock.write_bytes(b"")
    values = {"GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other), "GIT_COMMON_DIR": str(other / ".git")}
    env = quiet_env(tmp_path, **{name: values[name] for name in variables})

    check = run_script("check", "--json", "--repo", str(target), env=env)
    assert check.returncode == 11, (check.stdout, check.stderr)
    assert json.loads(check.stdout)["path"] == str(target_lock)

    clear = run_script("clear", "--json", "--repo", str(target), env=env)
    assert clear.returncode == 0, (clear.stdout, clear.stderr)
    assert not target_lock.exists()
    assert other_lock.exists(), "a lock of another repository must not be removed"


def test_concurrent_clear_waits_for_the_lock_directory(git_repo: Path, tmp_path: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    # A fake lsof and an empty-of-git PROC_ROOT make an unserialized clear
    # finish in well under a second, so waiting can only come from flock.
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "python", cwd=tmp_path)
    env = fake_lsof_env(tmp_path, "exit 1", PROC_ROOT=str(proc_root))
    directory = os.open(lock.parent, os.O_RDONLY)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX)
        clear = subprocess.Popen(
            ["bash", str(SCRIPT), "clear", "--repo", str(git_repo)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        time.sleep(2)
        assert clear.poll() is None, "clear must wait while another clear holds the directory"
        assert lock.exists()
        fcntl.flock(directory, fcntl.LOCK_UN)
        stdout, stderr = clear.communicate(timeout=30)
    finally:
        os.close(directory)
    assert clear.returncode == 0, (stdout, stderr)
    assert not lock.exists()


def test_clear_without_flock_removes_nothing(git_repo: Path, tmp_path: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    env = quiet_env(tmp_path)
    (Path(env["PATH"]) / "flock").unlink()

    assert run_script("check", "--repo", str(git_repo), env=env).returncode == 11
    clear = run_script("clear", "--json", "--repo", str(git_repo), env=env)
    assert clear.returncode == 1, (clear.stdout, clear.stderr)
    assert clear.stdout == ""
    assert "flock" in clear.stderr
    assert lock.exists()


def test_clear_keeps_a_lock_replaced_during_the_check(git_repo: Path, tmp_path: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    # The fake lsof runs in the middle of the holder check and stands in for a
    # new git process that re-created the lock after the old one vanished.
    env = fake_lsof_env(tmp_path, 'rm -f "$2"; printf new >"$2"; exit 1', PROC_ROOT=quiet_env(tmp_path)["PROC_ROOT"])

    clear = run_script("clear", "--json", "--repo", str(git_repo), env=env)
    assert clear.returncode == 12, (clear.stdout, clear.stderr)
    assert json.loads(clear.stdout)["removed"] is False
    assert "changed while it was being checked" in clear.stderr
    assert lock.read_bytes() == b"new"


def test_paused_commit_in_a_core_worktree_repository_is_not_stale(tmp_path: Path) -> None:
    # The git dir lives in "meta" and core.worktree points at "files"; git runs
    # from "files", where `git -C` alone cannot find the repository.
    meta = make_git_repo(tmp_path / "meta")
    files = tmp_path / "files"
    files.mkdir()
    (files / "README.md").write_text("hello\n", encoding="utf-8")
    git(meta, "config", "core.worktree", str(files))
    (meta / "README.md").unlink()
    assert git(meta, "status", "--porcelain") == ""
    ready = tmp_path / "paused"
    release = tmp_path / "release"
    hook = meta / ".git" / "hooks" / "pre-commit"
    hook.write_text(f'#!/bin/sh\n: >"{ready}"; while [ ! -e "{release}" ]; do sleep 0.05; done\n', encoding="utf-8")
    hook.chmod(0o755)
    (files / "README.md").write_text("changed\n", encoding="utf-8")
    lock = meta / ".git" / "index.lock"

    commit = subprocess.Popen(
        ["git", "commit", "-a", "-qm", "second"],
        cwd=meta,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for(ready.exists, "the pre-commit hook", commit)
        assert lock.exists()
        check = run_script("check", "--json", "--repo", str(meta))
        assert check.returncode == 12, (check.stdout, check.stderr)
        clear = run_script("clear", "--repo", str(meta))
        assert clear.returncode == 12, (clear.stdout, clear.stderr)
        assert lock.exists()
    finally:
        release.touch()
        stdout, stderr = commit.communicate(timeout=30)
    assert commit.returncode == 0, (stdout, stderr)
    assert git(meta, "show", "HEAD:README.md") == "changed\n"


def test_git_started_through_a_symlink_with_another_name_is_detected(git_repo: Path, tmp_path: Path) -> None:
    # comm and argv[0] say "xg"; only the executable shows that it is git.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git_bin = shutil.which("git")
    assert git_bin
    (bin_dir / "xg").symlink_to(git_bin)
    ready = tmp_path / "paused"
    release = tmp_path / "release"
    editor = tmp_path / "editor.sh"
    editor.write_text(
        f'#!/bin/sh\n: >"{ready}"; while [ ! -e "{release}" ]; do sleep 0.05; done\necho second >"$1"\n',
        encoding="utf-8",
    )
    editor.chmod(0o755)
    (git_repo / "README.md").write_text("changed\n", encoding="utf-8")
    lock = resolve_lock_path(git_repo)

    commit = subprocess.Popen(
        [str(bin_dir / "xg"), "commit", "-a", "-q"],
        cwd=git_repo,
        env={**os.environ, "GIT_EDITOR": str(editor)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for(ready.exists, "the commit message editor", commit)
        assert lock.exists()
        check = run_script("check", "--json", "--repo", str(git_repo))
        assert check.returncode == 12, (check.stdout, check.stderr)
        assert run_script("clear", "--repo", str(git_repo)).returncode == 12
        assert lock.exists()
    finally:
        release.touch()
        stdout, stderr = commit.communicate(timeout=30)
    assert commit.returncode == 0, (stdout, stderr)


def test_git_dir_given_as_a_dot_git_file_is_resolved(git_repo: Path, tmp_path: Path) -> None:
    # A linked worktree's .git is a file naming .git/worktrees/<name>.
    linked = tmp_path / "linked"
    git(git_repo, "worktree", "add", "-q", "-b", "linked", str(linked))
    external = tmp_path / "external"
    external.mkdir()
    resolve_lock_path(git_repo).write_bytes(b"")
    resolve_lock_path(linked).write_bytes(b"")
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=external)
    (proc_root / "4242" / "cmdline").write_bytes(
        b"".join(
            f"{word}\0".encode()
            for word in ("git", f"--git-dir={linked / '.git'}", f"--work-tree={external}", "commit", "-a")
        )
    )

    assert check_with_proc(linked, tmp_path, proc_root).returncode == 12
    assert check_with_proc(git_repo, tmp_path, proc_root).returncode == 11
