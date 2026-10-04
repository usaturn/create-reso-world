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

# Commands the helper script itself needs when `lsof` is absent. The list is
# deliberately explicit so the /proc fallback test can build a PATH without
# `lsof` while keeping the rest of the toolchain available.
CORE_TOOLS = ("bash", "git", "stat", "readlink", "rm", "dirname", "basename")


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
    raw = git(repo, "rev-parse", "--git-path", "index.lock").strip()
    path = Path(raw)
    return path if path.is_absolute() else repo / path


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-qm", "init")
    return repo


@contextlib.contextmanager
def holding_process(lock: Path, ready: Path) -> Iterator[subprocess.Popen[bytes]]:
    """Run a process that keeps ``lock`` open, then yields it."""
    holder_script = 'exec 9>"$1" || exit 1; : >"$2"; sleep 60'
    process = subprocess.Popen(
        ["bash", "-c", holder_script, "holder", str(lock), str(ready)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


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
        "rev-parse --git-path index.lock",
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
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in CORE_TOOLS:
        target = shutil.which(tool)
        assert target, f"{tool} is required for the fallback test"
        (bin_dir / tool).symlink_to(target)
    env = {**os.environ, "PATH": str(bin_dir)}

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


def test_clear_refuses_force_and_unknown_options(git_repo: Path) -> None:
    result = run_script("clear", "--force", "--repo", str(git_repo))
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.strip()
