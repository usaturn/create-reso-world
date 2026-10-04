"""Behavior tests for ``scripts/ff_merge_keep_untracked.sh``.

The script fast-forwards a branch whose merge is blocked by untracked files
that the incoming commits would overwrite. It must never lose such a file:
every one is restored (symlinks as symlinks) whether the fast-forward
succeeds or fails, and the target repository is selected by ``--repo`` only.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ff_merge_keep_untracked.sh"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def run_script(
    *args: str, cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=60,
    )


def configure(repo: Path) -> None:
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")


def status(repo: Path) -> set[str]:
    out = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    return {entry for entry in out.split("\0") if entry}


@pytest.fixture()
def behind(tmp_path: Path) -> Path:
    """A clone whose main is one commit behind origin/main.

    origin/main adds ``same.md``, ``differs.md``, ``sub dir/nested.md`` and the
    symlink ``link.md``; the clone has not merged that commit yet.
    """
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "-b", "main", "--bare", str(remote)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True, capture_output=True)
    configure(work)
    (work / "base.txt").write_text("base\n", encoding="utf-8")
    git(work, "add", "base.txt")
    git(work, "commit", "-qm", "base")
    git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "branch", "-u", "origin/main")

    upstream = tmp_path / "upstream"
    subprocess.run(["git", "clone", "-q", str(remote), str(upstream)], check=True, capture_output=True)
    configure(upstream)
    (upstream / "same.md").write_text("same\n", encoding="utf-8")
    (upstream / "differs.md").write_text("upstream\n", encoding="utf-8")
    (upstream / "sub dir").mkdir()
    (upstream / "sub dir" / "nested.md").write_text("upstream nested\n", encoding="utf-8")
    (upstream / "link.md").symlink_to("base.txt")
    git(upstream, "add", "-A")
    git(upstream, "commit", "-qm", "upstream")
    git(upstream, "push", "-q", "origin", "HEAD:main")

    git(work, "fetch", "-q", "origin")
    return work


def add_conflicting_untracked_files(work: Path) -> None:
    (work / "same.md").write_text("same\n", encoding="utf-8")
    (work / "differs.md").write_text("local draft\n", encoding="utf-8")
    (work / "differs.md").chmod(0o600)
    (work / "sub dir").mkdir()
    (work / "sub dir" / "nested.md").write_text("local nested\n", encoding="utf-8")
    (work / "link.md").symlink_to("differs.md")


def assert_local_files_kept(work: Path) -> None:
    assert (work / "same.md").read_text(encoding="utf-8") == "same\n"
    assert (work / "differs.md").read_text(encoding="utf-8") == "local draft\n"
    assert (work / "differs.md").stat().st_mode & 0o777 == 0o600
    assert (work / "sub dir" / "nested.md").read_text(encoding="utf-8") == "local nested\n"
    assert (work / "link.md").is_symlink(), "a symlink must be restored as a symlink"
    assert os.readlink(work / "link.md") == "differs.md"


def test_plain_merge_is_blocked_by_the_fixture(behind: Path) -> None:
    add_conflicting_untracked_files(behind)
    result = subprocess.run(
        ["git", "-C", str(behind), "merge", "--ff-only", "origin/main"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "untracked working tree files would be overwritten" in result.stderr


def test_fast_forwards_and_restores_every_conflicting_file(behind: Path, tmp_path: Path) -> None:
    add_conflicting_untracked_files(behind)
    upstream_head = git(behind, "rev-parse", "origin/main").strip()

    # Run from outside the repository and point --repo at a subdirectory.
    result = run_script("--repo", str(behind / "sub dir"), "--ref", "origin/main", cwd=tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)

    assert git(behind, "rev-parse", "HEAD").strip() == upstream_head
    assert_local_files_kept(behind)
    # Identical files become clean; local drafts stay as modifications.
    assert status(behind) == {" M differs.md", " M link.md", " M sub dir/nested.md"}


def test_failed_fast_forward_restores_everything_and_keeps_head(behind: Path) -> None:
    add_conflicting_untracked_files(behind)
    # A tracked file with local changes that origin/main also changes makes
    # `git merge --ff-only` fail after the untracked files were moved away.
    (behind / "base.txt").write_text("local edit\n", encoding="utf-8")
    remote_main = git(behind, "rev-parse", "origin/main").strip()
    upstream = behind.parent / "upstream"
    (upstream / "base.txt").write_text("upstream edit\n", encoding="utf-8")
    git(upstream, "commit", "-qam", "edit base")
    git(upstream, "push", "-q", "origin", "HEAD:main")
    git(behind, "fetch", "-q", "origin")
    assert git(behind, "rev-parse", "origin/main").strip() != remote_main
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "HEAD is unchanged" in result.stderr

    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert_local_files_kept(behind)
    assert (behind / "base.txt").read_text(encoding="utf-8") == "local edit\n"


def test_not_a_fast_forward_changes_nothing(behind: Path) -> None:
    add_conflicting_untracked_files(behind)
    (behind / "base.txt").write_text("diverge\n", encoding="utf-8")
    git(behind, "commit", "-qam", "diverge")
    head = git(behind, "rev-parse", "HEAD").strip()

    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "not a fast-forward" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert_local_files_kept(behind)


def test_backup_failure_changes_nothing(behind: Path, tmp_path: Path) -> None:
    add_conflicting_untracked_files(behind)
    head = git(behind, "rev-parse", "HEAD").strip()
    env = {**os.environ, "TMPDIR": str(tmp_path / "missing")}

    result = run_script("--repo", str(behind), "--ref", "origin/main", env=env)
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "nothing was changed" in result.stderr
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert_local_files_kept(behind)


def test_without_conflicts_it_only_fast_forwards(behind: Path) -> None:
    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert git(behind, "rev-parse", "HEAD").strip() == git(behind, "rev-parse", "origin/main").strip()
    assert status(behind) == set()


def test_already_up_to_date_is_a_noop(behind: Path) -> None:
    git(behind, "merge", "-q", "--ff-only", "origin/main")
    result = run_script("--repo", str(behind), "--ref", "origin/main")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "already up to date" in result.stdout


def test_inherited_git_dir_does_not_redirect_the_target(behind: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    subprocess.run(["git", "init", "-q", str(other)], check=True)
    add_conflicting_untracked_files(behind)
    env = {**os.environ, "GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other)}

    result = run_script("--repo", str(behind), "--ref", "origin/main", env=env)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert git(behind, "rev-parse", "HEAD").strip() == git(behind, "rev-parse", "origin/main").strip()
    assert_local_files_kept(behind)


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("--ref",),
        ("--ref", "no-such-ref"),
        ("--ref", "origin/main", "--force"),
    ],
)
def test_usage_errors_change_nothing(behind: Path, args: tuple[str, ...]) -> None:
    add_conflicting_untracked_files(behind)
    head = git(behind, "rev-parse", "HEAD").strip()
    result = run_script(*args, cwd=behind)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert git(behind, "rev-parse", "HEAD").strip() == head
    assert_local_files_kept(behind)


def test_outside_a_work_tree_is_a_usage_error(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    result = run_script("--repo", str(plain), "--ref", "HEAD")
    assert result.returncode == 2
    assert "not a git work tree" in result.stderr
