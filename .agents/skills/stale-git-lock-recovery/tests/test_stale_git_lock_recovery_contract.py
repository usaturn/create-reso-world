"""Contract tests for the stale-git-lock-recovery skill and its helper script.

The skill removes a leftover git ``index.lock`` only after proving that no live
process holds it. These tests pin the frontmatter contract, the safety wording
of SKILL.md, the Claude Code symlink, and the observable behavior of
``scripts/stale_git_lock.sh`` against temporary repositories.
"""
from __future__ import annotations

import contextlib
import json
import os
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
CORE_TOOLS = ("bash", "cat", "dirname", "basename", "git", "readlink", "rm", "stat", "tr")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
        "sha256",
        "sha256sum -c",
        "--ff-only",
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
