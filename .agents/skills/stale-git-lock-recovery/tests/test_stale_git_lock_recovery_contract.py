"""Contract tests for the stale-git-lock-recovery skill and its helper script.

The skill removes a leftover git ``index.lock`` only after proving that no live
process holds it. These tests pin the frontmatter contract, the safety wording
of SKILL.md, the Claude Code symlink, and the observable behavior of
``scripts/stale_git_lock.sh`` against temporary repositories.
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
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "stale-git-lock-recovery"
SKILL = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "stale_git_lock.sh"
CLAUDE_LINK = REPO_ROOT / ".claude" / "skills" / "stale-git-lock-recovery"

JSON_KEYS = {"path", "exists", "removed", "size", "mtime", "holder", "stale"}

# Commands the helper script itself needs when `lsof` is absent. The list is
# deliberately explicit so the PATH-limited tests can build a PATH without
# `lsof` while keeping the rest of the toolchain available.
CORE_TOOLS = ("bash", "cat", "dirname", "basename", "flock", "git", "readlink", "rm", "stat", "tr")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def bash_blocks() -> list[str]:
    return re.findall(r"```bash\n(.*?)```", read(SKILL), re.DOTALL)


def frontmatter() -> dict[str, object]:
    text = read(SKILL)
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    data = yaml.safe_load(text.split("---", 2)[1])
    assert isinstance(data, dict)
    return data


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
# Frontmatter, safety wording, and runtime wiring
# --------------------------------------------------------------------------


def test_frontmatter_declares_name_and_trigger_conditions_only() -> None:
    data = frontmatter()
    assert set(data) == {"name", "description"}
    assert data["name"] == "stale-git-lock-recovery"
    description = data["description"]
    assert isinstance(description, str)
    assert description.startswith("Use when")
    assert len(description) <= 1024, f"description has {len(description)} characters"
    for phrase in (
        "index.lock",
        "File exists",
        "Another git process seems to be running",
    ):
        assert phrase in description, f"description is missing trigger phrase {phrase!r}"


def test_skill_documents_the_safety_contract() -> None:
    content = read(SKILL)
    for phrase in (
        "保持",
        "削除しない",
        "git clean",
        "git reset --hard",
        "git checkout -f",
        "--ff-only",
        "ff_merge_keep_untracked.sh",
        "cp -a",
        "fd を閉じたまま",
        "GIT_DIR",
        "flock",
        "rev-parse --path-format=absolute --git-path index.lock",
        "--path-format=absolute",
        "PID namespace",
        "bind mount",
        "人間の確認",
        "参考情報",
        "removed",
        "/proc",
        "pr-review-save.lock",
        "pr-review",
        "repo-cleanup-after-merge",
    ):
        assert phrase in content, f"SKILL.md is missing {phrase!r}"


def test_destructive_shortcuts_are_only_mentioned_as_prohibitions() -> None:
    lines = read(SKILL).splitlines()
    for command in ("git clean", "git reset --hard", "git checkout -f"):
        matching = [line for line in lines if command in line]
        assert matching, f"SKILL.md never mentions {command}"
        for line in matching:
            assert any(word in line for word in ("使わない", "禁止", "しない")), (
                f"{command} must be documented as a prohibition, got: {line}"
            )


def test_skill_never_removes_the_lock_by_hand() -> None:
    content = read(SKILL)
    assert "削除は `clear` だけで行う" in content
    for block in bash_blocks():
        assert "rm " not in block, f"SKILL.md must not show a manual rm:\n{block}"


def test_bash_snippets_do_not_clobber_zsh_special_variables() -> None:
    # zsh ties `path` to PATH and makes `status` read-only, so a snippet pasted
    # into zsh (the devcontainer shell and Claude Code's Bash tool) must not
    # assign them.
    special = re.compile(r"(?:^|[\s;(])(?:path|status)=|\bread\b[^\n]*\s(?:path|status)\b")
    for block in bash_blocks():
        assert not special.search(block), f"zsh special variable in snippet:\n{block}"


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    assert CLAUDE_LINK.is_symlink()
    assert os.readlink(CLAUDE_LINK) == "../../.agents/skills/stale-git-lock-recovery"


# --------------------------------------------------------------------------
# Helper script behavior
# --------------------------------------------------------------------------


def test_check_reports_no_lock(git_repo: Path) -> None:
    result = run_script("check", "--repo", str(git_repo))
    assert result.returncode == 0, result.stderr

    payload = json.loads(run_script("check", "--json", "--repo", str(git_repo)).stdout)
    assert payload["path"] == str(resolve_lock_path(git_repo))
    assert payload["exists"] is False
    assert payload["stale"] is False


def test_json_object_has_a_fixed_key_set(git_repo: Path) -> None:
    lock = resolve_lock_path(git_repo)
    payloads = [json.loads(run_script("check", "--json", "--repo", str(git_repo)).stdout)]
    lock.write_bytes(b"")
    payloads.append(json.loads(run_script("check", "--json", "--repo", str(git_repo)).stdout))
    payloads.append(json.loads(run_script("clear", "--json", "--repo", str(git_repo)).stdout))
    for payload in payloads:
        assert set(payload) == JSON_KEYS


def test_stale_lock_is_detected_then_cleared(git_repo: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")

    check = run_script("check", "--json", "--repo", str(git_repo))
    assert check.returncode == 11, check.stderr
    payload = json.loads(check.stdout)
    assert payload["path"] == str(lock)
    assert payload["exists"] is True
    assert payload["size"] == 0
    assert payload["holder"] == "absent"
    assert payload["stale"] is True

    clear = run_script("clear", "--json", "--repo", str(git_repo))
    assert clear.returncode == 0, clear.stderr
    assert not lock.exists()
    cleared = json.loads(clear.stdout)
    assert cleared["path"] == str(lock)
    assert cleared["removed"] is True
    assert cleared["exists"] is False

    assert run_script("check", "--repo", str(git_repo)).returncode == 0


def test_nonzero_byte_lock_is_still_stale_when_unheld(git_repo: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"junk" * 100)

    check = run_script("check", "--json", "--repo", str(git_repo))
    assert check.returncode == 11, check.stderr
    payload = json.loads(check.stdout)
    assert payload["size"] == 400
    assert payload["holder"] == "absent"
    assert payload["stale"] is True

    clear = run_script("clear", "--json", "--repo", str(git_repo))
    assert clear.returncode == 0, clear.stderr
    assert not lock.exists()


def test_clear_without_lock_is_a_noop(git_repo: Path) -> None:
    clear = run_script("clear", "--json", "--repo", str(git_repo))
    assert clear.returncode == 0, clear.stderr
    payload = json.loads(clear.stdout)
    assert payload["exists"] is False
    assert payload["removed"] is False


def test_non_git_repo_is_a_usage_error(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    result = run_script("check", "--repo", str(plain))
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.strip()


def test_rm_failure_reports_error_without_json(git_repo: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    git_dir = lock.parent
    git_dir.chmod(0o500)
    try:
        result = run_script("clear", "--json", "--repo", str(git_repo))
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


def test_unlistable_non_git_process_is_not_a_holder(git_repo: Path, tmp_path: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    with unlistable_process(tmp_path, "python") as proc_root:
        env = limited_path_env(tmp_path, PROC_ROOT=str(proc_root))
        check = run_script("check", "--json", "--repo", str(git_repo), env=env)
        assert check.returncode == 11, (check.stdout, check.stderr)
        payload = json.loads(check.stdout)
        assert payload["holder"] == "absent"
        assert payload["stale"] is True


def test_unknown_holder_blocks_clear(git_repo: Path, tmp_path: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    empty_proc = tmp_path / "empty-proc"
    empty_proc.mkdir()
    env = limited_path_env(tmp_path, PROC_ROOT=str(empty_proc))

    check = run_script("check", "--json", "--repo", str(git_repo), env=env)
    assert check.returncode == 12, (check.stdout, check.stderr)
    assert json.loads(check.stdout)["holder"] == "unknown"

    clear = run_script("clear", "--json", "--repo", str(git_repo), env=env)
    assert clear.returncode == 12, (clear.stdout, clear.stderr)
    assert json.loads(clear.stdout)["removed"] is False
    assert lock.exists(), "clear must not delete when the holder cannot be determined"


def test_clear_removes_only_the_symlink_lock_not_its_target(git_repo: Path) -> None:
    lock = resolve_lock_path(git_repo)
    target = git_repo / "precious.bin"
    target.write_bytes(b"do not delete")
    lock.symlink_to(target)

    check = run_script("check", "--json", "--repo", str(git_repo))
    assert check.returncode == 11, check.stderr
    assert json.loads(check.stdout)["exists"] is True

    clear = run_script("clear", "--json", "--repo", str(git_repo))
    assert clear.returncode == 0, clear.stderr
    assert json.loads(clear.stdout)["removed"] is True
    assert not lock.is_symlink()
    assert target.read_bytes() == b"do not delete"


def test_dangling_symlink_lock_is_detected_and_cleared(git_repo: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.symlink_to(git_repo / "missing-target")

    check = run_script("check", "--json", "--repo", str(git_repo))
    assert check.returncode == 11, check.stderr
    payload = json.loads(check.stdout)
    assert payload["exists"] is True
    assert payload["stale"] is True

    clear = run_script("clear", "--json", "--repo", str(git_repo))
    assert clear.returncode == 0, clear.stderr
    assert json.loads(clear.stdout)["removed"] is True
    assert not lock.is_symlink()


def test_linked_worktree_lock_is_detected_at_its_own_path(git_repo: Path, tmp_path: Path) -> None:
    linked = tmp_path / "linked"
    git(git_repo, "worktree", "add", "-q", "-b", "linked-branch", str(linked))

    lock = resolve_lock_path(linked)
    assert "worktrees" in str(lock), "fixture must exercise the linked worktree path"
    lock.write_bytes(b"")

    check = run_script("check", "--json", "--repo", str(linked))
    assert check.returncode == 11, check.stderr
    payload = json.loads(check.stdout)
    assert payload["path"] == str(lock)
    assert payload["stale"] is True
    assert lock.exists()


def test_json_escapes_special_characters_in_path(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / 'we"ird\nname' / "repo")

    result = run_script("check", "--json", "--repo", str(repo))
    assert result.returncode == 0, result.stderr
    # json.loads fails if the quote/newline were not escaped as JSON strings.
    payload = json.loads(result.stdout)
    assert payload["path"] == str(resolve_lock_path(repo))


def test_clear_refuses_force_and_unknown_options(git_repo: Path) -> None:
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


@pytest.mark.parametrize(
    "where",
    ["work tree top", "subdirectory", "git dir"],
)
def test_git_process_inside_the_repository_makes_the_holder_unknown(
    git_repo: Path, tmp_path: Path, where: str
) -> None:
    resolve_lock_path(git_repo).write_bytes(b"")
    (git_repo / "sub").mkdir()
    cwd = {"work tree top": git_repo, "subdirectory": git_repo / "sub", "git dir": git_repo / ".git"}[where]
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=cwd)

    check = check_with_proc(git_repo, tmp_path, proc_root)
    assert check.returncode == 12, (check.stdout, check.stderr)
    assert json.loads(check.stdout)["holder"] == "unknown"
    assert "pid 4242 (git)" in check.stderr


@pytest.mark.parametrize("variable", ["GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"])
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
        # relative values are resolved against the process's cwd
        "GIT_INDEX_FILE": os.path.relpath(lock, elsewhere),
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


@pytest.mark.parametrize(
    "where",
    [("environ", "GIT_DIR=../x/.git"), ("cmdline", "--work-tree=sub"), ("cmdline", "--git-dir")],
)
def test_git_process_with_a_relative_repository_reference_cannot_be_ruled_out(
    git_repo: Path, tmp_path: Path, where: tuple[str, str]
) -> None:
    # git may have changed directory since it started, so a relative value
    # cannot be resolved against the current cwd.
    resolve_lock_path(git_repo).write_bytes(b"")
    other = make_git_repo(tmp_path / "other")
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=other)
    kind, value = where
    if kind == "environ":
        (proc_root / "4242" / "environ").write_bytes(f"{value}\0".encode())
    else:
        words = ["git", value] + (["../repo/.git"] if value == "--git-dir" else []) + ["status"]
        (proc_root / "4242" / "cmdline").write_bytes(b"".join(f"{w}\0".encode() for w in words))

    check = check_with_proc(git_repo, tmp_path, proc_root)
    assert check.returncode == 12, (check.stdout, check.stderr)


def test_git_process_with_an_unreadable_cwd_is_unknown(git_repo: Path, tmp_path: Path) -> None:
    resolve_lock_path(git_repo).write_bytes(b"")
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=None)

    check = check_with_proc(git_repo, tmp_path, proc_root)
    assert check.returncode == 12, (check.stdout, check.stderr)


def test_unrelated_processes_do_not_block_a_stale_lock(git_repo: Path, tmp_path: Path) -> None:
    resolve_lock_path(git_repo).write_bytes(b"")
    other = make_git_repo(tmp_path / "other")
    proc_root = tmp_path / "proc"
    # a git process in another repository that names it with an absolute GIT_DIR
    fake_process(proc_root, 4242, "git", cwd=other, environ={"GIT_DIR": str(other / ".git")})
    # a non-git process working inside this repository
    fake_process(proc_root, 4243, "vim", cwd=git_repo)
    # a process whose command line merely mentions a path ending in /git
    fake_process(proc_root, 4244, "bash", cwd=git_repo)
    (proc_root / "4244" / "cmdline").write_bytes(b"bash\0/opt/git\0")

    check = check_with_proc(git_repo, tmp_path, proc_root)
    assert check.returncode == 11, (check.stdout, check.stderr)
    assert json.loads(check.stdout)["stale"] is True


def test_git_process_in_a_nested_worktree_or_repository_does_not_block_the_outer_lock(
    git_repo: Path, tmp_path: Path
) -> None:
    # Worktrees under the main work tree (as in .worktrees/<name>) and nested
    # repositories work on their own index; only git on the same work tree counts.
    nested_worktree = git_repo / ".worktrees" / "feature"
    git(git_repo, "worktree", "add", "-q", "-b", "feature", str(nested_worktree))
    nested_repo = make_git_repo(git_repo / "vendor" / "lib")
    resolve_lock_path(git_repo).write_bytes(b"")
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=nested_worktree)
    fake_process(proc_root, 4243, "git", cwd=nested_repo)

    assert check_with_proc(git_repo, tmp_path, proc_root).returncode == 11
    fake_process(proc_root, 4244, "git", cwd=git_repo / "vendor")
    assert check_with_proc(git_repo, tmp_path, proc_root).returncode == 12


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


def test_git_process_in_the_main_worktree_does_not_block_a_linked_worktree_lock(
    git_repo: Path, tmp_path: Path
) -> None:
    linked = tmp_path / "linked"
    git(git_repo, "worktree", "add", "-q", "-b", "linked-branch", str(linked))
    resolve_lock_path(linked).write_bytes(b"")
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=git_repo)

    assert check_with_proc(linked, tmp_path, proc_root).returncode == 11
    fake_process(proc_root, 4243, "git", cwd=linked)
    assert check_with_proc(linked, tmp_path, proc_root).returncode == 12


def test_holder_found_after_an_unknown_process_is_still_present(git_repo: Path, tmp_path: Path) -> None:
    lock = resolve_lock_path(git_repo)
    lock.write_bytes(b"")
    with unlistable_process(tmp_path, "git") as proc_root:
        # PID 4242 (unlistable git) is scanned before PID 5000, which has the lock open.
        fake_process(proc_root, 5000, "python", cwd=tmp_path, fds=(lock,))
        check = check_with_proc(git_repo, tmp_path, proc_root)
        assert check.returncode == 10, (check.stdout, check.stderr)
        assert json.loads(check.stdout)["holder"] == "present"


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


def test_lsof_holder_wins_over_an_unusable_proc(git_repo: Path, tmp_path: Path) -> None:
    resolve_lock_path(git_repo).write_bytes(b"")
    body = 'echo "COMMAND PID USER FD"; echo "git 31337 me 3w"; exit 0'
    env = fake_lsof_env(tmp_path, body, PROC_ROOT=str(tmp_path / "no-proc"))
    check = run_script("check", "--json", "--repo", str(git_repo), env=env)
    assert check.returncode == 10, (check.stdout, check.stderr)
    assert "pid 31337 (git)" in check.stderr


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
    env = {**os.environ, **{name: values[name] for name in variables}}

    check = run_script("check", "--json", "--repo", str(target), env=env)
    assert check.returncode == 11, (check.stdout, check.stderr)
    assert json.loads(check.stdout)["path"] == str(target_lock)

    clear = run_script("clear", "--json", "--repo", str(target), env=env)
    assert clear.returncode == 0, (clear.stdout, clear.stderr)
    assert not target_lock.exists()
    assert other_lock.exists(), "a lock of another repository must not be removed"


def test_stale_suggestion_is_a_runnable_command_for_paths_with_spaces(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "scratch repo x")
    lock = resolve_lock_path(repo)
    lock.write_bytes(b"")

    check = run_script("check", "--repo", str(repo))
    assert check.returncode == 11, check.stderr
    prefix = "remove it with: "
    suggestion = next(line for line in check.stdout.splitlines() if line.startswith(prefix))

    result = subprocess.run(["bash", "-c", suggestion[len(prefix):]], capture_output=True, text=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert not lock.exists()


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
    env = limited_path_env(tmp_path)
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
    env = fake_lsof_env(tmp_path, 'rm -f "$2"; printf new >"$2"; exit 1')

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


def test_git_child_of_a_linked_worktree_does_not_block_the_main_lock(git_repo: Path, tmp_path: Path) -> None:
    # git exports GIT_DIR=<common>/worktrees/<name> to processes it starts in a
    # linked worktree (aliases, hooks); they use that worktree's index only.
    linked = tmp_path / "linked"
    git(git_repo, "worktree", "add", "-q", "-b", "linked", str(linked))
    linked_git_dir = git_repo / ".git" / "worktrees" / "linked"
    resolve_lock_path(git_repo).write_bytes(b"")
    resolve_lock_path(linked).write_bytes(b"")
    proc_root = tmp_path / "proc"
    fake_process(proc_root, 4242, "git", cwd=linked, environ={"GIT_DIR": str(linked_git_dir)})

    assert check_with_proc(git_repo, tmp_path, proc_root).returncode == 11
    assert check_with_proc(linked, tmp_path, proc_root).returncode == 12


def test_submodule_git_dir_is_refused(tmp_path: Path) -> None:
    library = make_git_repo(tmp_path / "library")
    superproject = make_git_repo(tmp_path / "super")
    subprocess.run(
        ["git", "-C", str(superproject), "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(library), "lib"],
        check=True,
        capture_output=True,
    )
    module_git_dir = superproject / ".git" / "modules" / "lib"
    assert module_git_dir.is_dir()
    result = run_script("check", "--repo", str(module_git_dir))
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "pass the work tree" in result.stderr
    # The submodule's own work tree is accepted.
    assert run_script("check", "--repo", str(superproject / "lib")).returncode == 0


@pytest.mark.parametrize("how", ["GIT_WORK_TREE", "--work-tree"])
def test_paused_commit_with_an_external_work_tree_is_not_stale(tmp_path: Path, how: str) -> None:
    # git finds the git dir from the cwd it starts in, then moves to the work
    # tree given by GIT_WORK_TREE / --work-tree, outside the repository.
    repo = make_git_repo(tmp_path / "repo")
    work_tree = tmp_path / "external"
    work_tree.mkdir()
    (work_tree / "README.md").write_text("changed\n", encoding="utf-8")
    ready = tmp_path / "paused"
    release = tmp_path / "release"
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text(f'#!/bin/sh\n: >"{ready}"; while [ ! -e "{release}" ]; do sleep 0.05; done\n', encoding="utf-8")
    hook.chmod(0o755)
    lock = repo / ".git" / "index.lock"
    env = {**os.environ}
    args = ["git", "commit", "-a", "-qm", "second"]
    if how == "GIT_WORK_TREE":
        env["GIT_WORK_TREE"] = str(work_tree)
    else:
        args[1:1] = [f"--work-tree={work_tree}"]

    commit = subprocess.Popen(args, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        wait_for(ready.exists, "the pre-commit hook", commit)
        assert lock.exists()
        check = run_script("check", "--json", "--repo", str(repo))
        assert check.returncode == 12, (check.stdout, check.stderr)
        clear = run_script("clear", "--repo", str(repo))
        assert clear.returncode == 12, (clear.stdout, clear.stderr)
        assert lock.exists()
    finally:
        release.touch()
        stdout, stderr = commit.communicate(timeout=30)
    assert commit.returncode == 0, (stdout, stderr)
    assert git(repo, "show", "HEAD:README.md") == "changed\n"


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


def test_zombie_git_process_does_not_block(git_repo: Path, tmp_path: Path) -> None:
    # A zombie has an empty fd directory and no readable cwd, but holds nothing.
    resolve_lock_path(git_repo).write_bytes(b"")
    proc_root = tmp_path / "proc"
    pid_dir = proc_root / "4242"
    (pid_dir / "fd").mkdir(parents=True)
    (pid_dir / "comm").write_text("git\n", encoding="utf-8")
    (pid_dir / "cmdline").write_bytes(b"")
    (pid_dir / "stat").write_text("4242 (git) Z 1 4242 4242 0 -1 4194316 0 0 0 0\n", encoding="utf-8")

    assert check_with_proc(git_repo, tmp_path, proc_root).returncode == 11
    (pid_dir / "stat").write_text("4242 (git) S 1 4242 4242 0 -1 4194316 0 0 0 0\n", encoding="utf-8")
    assert check_with_proc(git_repo, tmp_path, proc_root).returncode == 12
