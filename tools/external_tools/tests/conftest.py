"""Local Git workspaces: never contact or mutate real remotes."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tools.external_tools.models import Registry


ADOPTED = b'''schema_version = 1

[tools.emission-editor]
repository = "usaturn/resonite-emission-editor"
path = "external/emission-editor"
base_branch = "main"
ci = "disabled"
'''
OTHER = b'''
[tools.other-tool]
repository = "sample-owner/other-tool"
path = "external/other-tool"
base_branch = "development"
ci = "required"
'''
UNADOPTED = b'''
[tools.unadopted]
repository = "sample-owner/unadopted"
path = "external/unadopted"
base_branch = "main"
ci = "disabled"
'''


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True,
        env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    )
    return result.stdout.strip()


def make_repo(root: Path, repository: str) -> Path:
    root.mkdir(parents=True)
    git(root, "init", "-b", "fixture-base")
    git(root, "config", "user.name", "Test User")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "remote", "add", "origin", f"https://github.com/{repository}.git")
    (root / ".gitignore").write_text("/external/\n/.worktrees/\n", encoding="utf-8")
    git(root, "add", ".gitignore")
    git(root, "commit", "-m", "fixture base")
    return root


@dataclass(frozen=True)
class Workspace:
    parent: Path
    adopted_sha: str
    registered: Path
    linked: Path
    other_clone: Path
    repository: str
    candidate: Path

    @property
    def registry(self) -> Registry:
        from tools.external_tools.registry import load_active_registry

        result = load_active_registry(self.parent)
        assert result is not None
        return result


@pytest.fixture(autouse=True)
def isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # S: no inherited Git selector or user HOME may redirect fixture mutations.
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    home = tmp_path / "isolated home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    parent = make_repo(tmp_path / "parent with spaces", "usaturn/create-reso-world")
    (parent / "external-tools.toml").write_bytes(ADOPTED)
    git(parent, "add", "external-tools.toml")
    git(parent, "commit", "-m", "adopt registry")
    adopted_sha = git(parent, "rev-parse", "HEAD")
    git(parent, "update-ref", "refs/remotes/origin/main", adopted_sha)
    git(parent, "checkout", "--detach", adopted_sha)

    candidate = tmp_path / "candidate worktree"
    git(parent, "worktree", "add", "-b", "candidate", str(candidate), adopted_sha)
    (candidate / "external-tools.toml").write_bytes(ADOPTED + UNADOPTED)
    git(candidate, "add", "external-tools.toml")
    git(candidate, "commit", "-m", "unadopted candidate")

    repository = "usaturn/resonite-emission-editor"
    registered = make_repo(parent / "external/emission-editor", repository)
    linked = tmp_path / "tool linked worktree"
    git(registered, "worktree", "add", "-b", "tool-change", str(linked))
    other_clone = make_repo(tmp_path / "other clone", repository)
    return Workspace(parent, adopted_sha, registered, linked, other_clone, repository, candidate)
