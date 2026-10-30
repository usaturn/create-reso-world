"""Base selection safety: real local Git, with only origin URL discovery replaced.

Each rejection prevents silently selecting another repository/history or modifying
an existing checkout. Normal cases keep the boundary from becoming reject-all.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resolve_base.py"
REPO = "usaturn/create-reso-world"
INTEGRATION = "統合/プラグイン"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def snapshot(root: Path) -> tuple[str, str, str, bytes, bytes | None]:
    fetch_head = root / ".git" / "FETCH_HEAD"
    return (
        git(root, "for-each-ref"),
        git(root, "status", "--porcelain"),
        git(root, "symbolic-ref", "HEAD"),
        (root / ".git" / "index").read_bytes(),
        fetch_head.read_bytes() if fetch_head.exists() else None,
    )


@dataclass
class Repository:
    root: Path
    seed: Path
    remote: Path
    fetch_log: Path


def resolve(
    repository: Repository, *args: str, checkout: Path | None = None, repo: str = REPO
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--checkout", str(checkout or repository.root), "--repo", repo, *args],
        capture_output=True,
        text=True,
    )


def rejected(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 2, result.stdout
    assert result.stdout == ""
    assert result.stderr


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Repository:
    # The root conftest drops inherited GIT_* before this fixture. Use a one-test
    # HOME so the real Git setup also cannot use the developer's global config.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Base test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "base@example.test")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Base test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "base@example.test")
    remote, seed, root = (tmp_path / name for name in ("remote.git", "seed", "checkout"))
    subprocess.run(["git", "init", "--bare", "--quiet", "--initial-branch=main", str(remote)], check=True)
    subprocess.run(["git", "init", "--quiet", "--initial-branch=main", str(seed)], check=True)
    (seed / "content").write_text("main history\n", encoding="utf-8")
    git(seed, "add", "content")
    git(seed, "commit", "--quiet", "-m", "main")
    git(seed, "switch", "--quiet", "-c", INTEGRATION)
    (seed / "content").write_text("統合の履歴\nsecond line\n", encoding="utf-8")
    git(seed, "commit", "--quiet", "-am", "integration")
    git(seed, "tag", "tag-only")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "--quiet", "origin", "--all")
    git(seed, "push", "--quiet", "origin", "--tags")
    subprocess.run(
        ["git", "clone", "--quiet", "--single-branch", "--branch", "main", str(remote), str(root)],
        check=True,
    )
    git(root, "switch", "--quiet", "-c", "feature/local")
    (root / "local").write_text("keep the feature\n", encoding="utf-8")
    git(root, "add", "local")
    git(root, "commit", "--quiet", "-m", "local feature")
    (root / "local").write_text("keep uncommitted edits\n", encoding="utf-8")
    # A configured refmap must not redirect base acquisition into local heads.
    git(root, "config", "remote.origin.fetch", "+refs/heads/*:refs/heads/*")
    real_git = shutil.which("git")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fetch_log = tmp_path / "fetch.log"
    wrapper = bin_dir / "git"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import os, pathlib, subprocess, sys\n"
        f"real_git = {real_git!r}\n"
        "args = sys.argv[1:]\n"
        "if args[:2] == ['remote', 'get-url']:\n"
        "    response = subprocess.run([real_git, *args], capture_output=True, text=True)\n"
        "    if response.returncode:\n"
        "        sys.exit(response.returncode)\n"
        "    key = 'BASE_PUSH_URL' if '--push' in args else 'BASE_FETCH_URL'\n"
        "    print(response.stdout.strip().replace(os.environ['BASE_REMOTE'], os.environ[key]))\n"
        "    sys.exit(0)\n"
        "if args and args[0] == 'fetch':\n"
        "    with pathlib.Path(os.environ['BASE_FETCH_LOG']).open('a') as log:\n"
        "        log.write('fetch\\n')\n"
        "    if os.environ.get('BASE_MOVE_ON_FETCH'):\n"
        "        subprocess.run([real_git, '-C', os.environ['BASE_REMOTE'], 'update-ref',\n"
        "                        'refs/heads/main', os.environ['BASE_MOVE_ON_FETCH']], check=True)\n"
        "if args and args[0] == 'ls-remote' and os.environ.get('BASE_REMOTE_ERROR'):\n"
        "    print(os.environ['BASE_REMOTE_ERROR'], file=sys.stderr)\n"
        "    sys.exit(128)\n"
        "os.execv(real_git, [real_git, *args])\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("BASE_REMOTE", str(remote))
    monkeypatch.setenv("BASE_FETCH_URL", f"https://github.com/{REPO}.git")
    monkeypatch.setenv("BASE_PUSH_URL", f"git@github.com:{REPO}.git")
    monkeypatch.setenv("BASE_FETCH_LOG", str(fetch_log))
    return Repository(root, seed, remote, fetch_log)


def test_resolve_exact_origin_branch(repository: Repository) -> None:
    """Defaulting all requests to main, or returning a local feature SHA, loses integration work."""
    before = snapshot(repository.root)
    main = git(repository.remote, "rev-parse", "refs/heads/main")
    integration = git(repository.remote, "rev-parse", f"refs/heads/{INTEGRATION}")
    assert main != integration
    for args, branch, sha, content in (
        ([], "main", main, "main history"),
        (["--base", INTEGRATION], INTEGRATION, integration, "統合の履歴\nsecond line"),
    ):
        result = resolve(repository, *args)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {
            "repo": REPO, "remote": "origin", "branch": branch,
            "ref": f"refs/heads/{branch}", "sha": sha,
        }
        assert git(repository.root, "cat-file", "-t", sha) == "commit"
        assert git(repository.root, "show", f"{sha}:content") == content
        assert snapshot(repository.root) == before


def test_rejects_wrong_target_and_required_base(repository: Repository, monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrong fetch/push targets and dropped handoff requirements must stop before acquisition."""
    before = snapshot(repository.root)
    for key in ("BASE_FETCH_URL", "BASE_PUSH_URL"):
        with monkeypatch.context() as patch:
            patch.setenv(key, "https://github.com/usaturn/resoloop.git")
            rejected(resolve(repository))
        assert not repository.fetch_log.exists()
    for args in (
        ["--required-base", INTEGRATION],
        ["--base", "main", "--required-base", INTEGRATION],
        ["--base", INTEGRATION, "--required-base", INTEGRATION, "--required-base", "main"],
    ):
        rejected(resolve(repository, *args))
        assert not repository.fetch_log.exists()
    assert snapshot(repository.root) == before
    result = resolve(repository, "--base", INTEGRATION, "--required-base", INTEGRATION,
                     "--required-base", INTEGRATION)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["sha"] == git(repository.remote, "rev-parse", f"refs/heads/{INTEGRATION}")


def test_rejects_non_root_and_untracked_checkout(repository: Repository) -> None:
    """Accepting an ignored world/subdirectory could create a PR for a different tracked target."""
    (repository.root / ".gitignore").write_text("worlds/\n", encoding="utf-8")
    world = repository.root / "worlds" / "project"
    world.mkdir(parents=True)
    subdirectory = repository.root / "tracked-subdir"
    subdirectory.mkdir()
    before = snapshot(repository.root)
    for path in (world, subdirectory, repository.remote):
        rejected(resolve(repository, checkout=path))
        assert not repository.fetch_log.exists()
    assert snapshot(repository.root) == before
    assert resolve(repository).returncode == 0


def test_base_cannot_select_other_ref_or_revision(repository: Repository) -> None:
    """Revision expansion, tag fallback, and injected refspecs can silently select/overwrite other work."""
    before = snapshot(repository.root)
    for branch in (
        "tag-only", "missing", "@{-1}", "main~1", "refs/tags/tag-only", "refs/heads/main",
        "main:refs/heads/feature/local", "+main", "-main", "HEAD", "main*",
    ):
        rejected(resolve(repository, f"--base={branch}"))
        assert snapshot(repository.root) == before
        assert not repository.fetch_log.exists()
    assert resolve(repository, "--base", "main").returncode == 0


def test_base_movement_rejected(repository: Repository, monkeypatch: pytest.MonkeyPatch) -> None:
    """Rechecking a captured SHA must not silently adopt a moved remote base or reset the feature."""
    before = snapshot(repository.root)
    first = resolve(repository)
    assert first.returncode == 0, first.stderr
    captured = json.loads(first.stdout)["sha"]
    rechecked = resolve(repository, "--expected-sha", captured)
    assert rechecked.returncode == 0, rechecked.stderr
    assert json.loads(rechecked.stdout)["sha"] == captured
    advanced = git(repository.remote, "rev-parse", f"refs/heads/{INTEGRATION}")
    git(repository.remote, "update-ref", "refs/heads/main", advanced)
    rejected(resolve(repository, "--expected-sha", captured))
    assert snapshot(repository.root) == before
    # Also catch a movement between ls-remote and the exact fetch, even when the
    # captured object is already present locally from the previous invocation.
    git(repository.remote, "update-ref", "refs/heads/main", captured)
    monkeypatch.setenv("BASE_MOVE_ON_FETCH", advanced)
    rejected(resolve(repository, "--expected-sha", captured))
    assert snapshot(repository.root) == before


def test_inherited_git_environment_cannot_redirect_checkout(
    repository: Repository, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """GIT_DIR/config injection must not make a validated checkout read another repository's origin/base."""
    expected = git(repository.remote, "rev-parse", "refs/heads/main")
    # ls-remote/fetch keep the transport authentication names; an insteadOf left in
    # that environment would read another history's main while origin still verifies.
    wrong = tmp_path / "wrong.git"
    subprocess.run(["git", "init", "--bare", "--quiet", "--initial-branch=main", str(wrong)], check=True)
    git(repository.seed, "push", "--quiet", str(wrong), f"{INTEGRATION}:refs/heads/main")
    foreign_before = git(repository.seed, "for-each-ref")
    before = snapshot(repository.root)
    with monkeypatch.context() as patch:
        patch.setenv("GIT_DIR", str(repository.seed / ".git"))
        patch.setenv("GIT_WORK_TREE", str(repository.seed))
        patch.setenv("GIT_INDEX_FILE", str(tmp_path / "foreign-index"))
        patch.setenv("GIT_CONFIG_COUNT", "2")
        patch.setenv("GIT_CONFIG_KEY_0", "remote.origin.url")
        patch.setenv("GIT_CONFIG_VALUE_0", str(wrong))
        patch.setenv("GIT_CONFIG_KEY_1", f"url.{wrong}.insteadOf")
        patch.setenv("GIT_CONFIG_VALUE_1", str(repository.remote))
        result = resolve(repository)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["sha"] == expected
    assert snapshot(repository.root) == before
    assert git(repository.seed, "for-each-ref") == foreign_before
    assert not (tmp_path / "foreign-index").exists()


def test_remote_failure_does_not_expose_credentials(repository: Repository, monkeypatch: pytest.MonkeyPatch) -> None:
    """Git may echo credential URLs on transport failure; forwarding stderr leaks them into reports."""
    secret = "-".join(("base", "test", "credential"))
    monkeypatch.setenv("BASE_REMOTE_ERROR", f"fatal: https://user:{secret}@github.com/{REPO}.git failed")
    result = resolve(repository)
    rejected(result)
    assert secret not in result.stderr
    assert not repository.fetch_log.exists()
    monkeypatch.delenv("BASE_REMOTE_ERROR")
    assert resolve(repository).returncode == 0
