"""agent_tmp.py が親の checkout と tmp/agents/ のセッションディレクトリを決める仕様。

usaturn/agent-workspace#333 のテストを create-reso-world#123 で移植した。判定関数のテストは移植元のまま、
CLI のテストは create-reso-world の形（origin/main の detached HEAD の親 checkout、.worktrees の worktree、
別の repository として clone した external/resoloop-meshy、自分の .git を持つワールド）の fixture で実行する。
"""

from __future__ import annotations

import importlib.util
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "agent_tmp.py"
REPO_GITIGNORE = SCRIPT.parents[2] / ".gitignore"
SPEC = importlib.util.spec_from_file_location("agent_tmp", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
agent_tmp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent_tmp)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def make_repo(path: Path, *, ignore_tmp: bool = True) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    git(path, "config", "user.name", "Test User")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "commit.gpgsign", "false")
    (path / ".gitignore").write_text("tmp\n" if ignore_tmp else "build\n", encoding="utf-8")
    git(path, "add", ".gitignore")
    git(path, "commit", "-m", "fixture")
    return path.resolve()


def test_resolve_main_root_rejects_submodule_checkout(tmp_path: Path) -> None:
    sub = make_repo(tmp_path / "sub")
    parent = make_repo(tmp_path / "parent")
    git(parent, "-c", "protocol.file.allow=always", "submodule", "add", str(sub), "public")
    git(parent, "commit", "-m", "add submodule")

    with pytest.raises(agent_tmp.AgentTmpError, match="common dir"):
        agent_tmp.resolve_main_root(parent / "public")


def test_make_session_dir_creates_unique_dirs_under_tmp_agents(tmp_path: Path) -> None:
    main = make_repo(tmp_path / "main")

    first = agent_tmp.make_session_dir(main, "issue-333")
    second = agent_tmp.make_session_dir(main, "issue-333")

    assert first != second
    for path in (first, second):
        assert path.is_dir()
        assert path.parent == main / "tmp" / "agents"
        assert path.name.startswith("issue-333.")
    assert git(main, "status", "--porcelain") == ""


@pytest.mark.parametrize("topic", ["a/b", "../x", ".x"])
def test_make_session_dir_rejects_invalid_topic(tmp_path: Path, topic: str) -> None:
    main = make_repo(tmp_path / "main")

    with pytest.raises(agent_tmp.AgentTmpError, match="invalid topic"):
        agent_tmp.make_session_dir(main, topic)
    assert not (main / "tmp").exists()


def test_make_session_dir_refuses_when_tmp_is_not_ignored(tmp_path: Path) -> None:
    main = make_repo(tmp_path / "main", ignore_tmp=False)

    with pytest.raises(agent_tmp.AgentTmpError, match="not ignored"):
        agent_tmp.make_session_dir(main, "issue-333")
    assert not (main / "tmp").exists()


@pytest.mark.parametrize("link", ["tmp", "tmp/agents"])
def test_make_session_dir_refuses_symlink_escaping_main_worktree(tmp_path: Path, link: str) -> None:
    main = make_repo(tmp_path / "main")
    outside = tmp_path / "outside"
    outside.mkdir()
    link_path = main / link
    link_path.parent.mkdir(parents=True, exist_ok=True)
    link_path.symlink_to(outside, target_is_directory=True)

    with pytest.raises(agent_tmp.AgentTmpError):
        agent_tmp.make_session_dir(main, "issue-333")
    assert list(outside.iterdir()) == []


def test_make_session_dir_refuses_symlink_into_unignored_directory(tmp_path: Path) -> None:
    # `tmp/agents` itself matches the `tmp` ignore rule, so only the resolved target shows it is tracked.
    main = make_repo(tmp_path / "main")
    src = main / "src"
    src.mkdir()
    (src / "keep.py").write_text("x = 1\n", encoding="utf-8")
    git(main, "add", "src/keep.py")
    git(main, "commit", "-m", "tracked src")
    (main / "tmp").mkdir()
    (main / "tmp/agents").symlink_to(Path("../src"), target_is_directory=True)

    with pytest.raises(agent_tmp.AgentTmpError, match="not ignored"):
        agent_tmp.make_session_dir(main, "issue-333")
    assert [path.name for path in src.iterdir()] == ["keep.py"]


@dataclass(frozen=True)
class Layout:
    parent: Path
    worktree: Path
    meshy: Path
    meshy_worktree: Path
    world: Path
    outside: Path


def clone_detached(src: Path, dest: Path) -> Path:
    """`src` の bare の origin を作り、実際の親 checkout と同じく origin/main の detached HEAD（ローカルの main 無し）で clone する。"""
    origin = src.with_name(f"{src.name}.git")
    subprocess.run(["git", "clone", "-q", "--bare", str(src), str(origin)], check=True, capture_output=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(dest)], check=True, capture_output=True)
    git(dest, "checkout", "-q", "--detach", "origin/main")
    git(dest, "branch", "-q", "-D", "main")
    return dest.resolve()


@pytest.fixture
def layout(tmp_path: Path) -> Layout:
    # 実際の .gitignore を写す。tmp/agents を無視する実際の規則の上で mkdir が動くことを確かめるため。
    parent_src = make_repo(tmp_path / "src" / "create-reso-world")
    shutil.copyfile(REPO_GITIGNORE, parent_src / ".gitignore")
    (parent_src / ".agents" / "scripts").mkdir(parents=True)
    shutil.copyfile(SCRIPT, parent_src / ".agents" / "scripts" / "agent_tmp.py")
    git(parent_src, "add", ".gitignore", ".agents/scripts/agent_tmp.py")
    git(parent_src, "commit", "-m", "parent fixture")
    meshy_src = make_repo(tmp_path / "src" / "resoloop-meshy")

    parent = clone_detached(parent_src, tmp_path / "reso-world")
    worktree = parent / ".worktrees" / "topic"
    git(parent, "worktree", "add", "-q", "-b", "feat/topic", str(worktree), "origin/main")
    meshy = clone_detached(meshy_src, parent / "external" / "resoloop-meshy")
    meshy_worktree = meshy / ".worktrees" / "topic"
    git(meshy, "worktree", "add", "-q", "-b", "feat/topic", str(meshy_worktree), "origin/main")
    world = parent / "worlds" / "w"
    (world / "sub").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(world)], check=True, capture_output=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    return Layout(parent, worktree, meshy, meshy_worktree, world, outside)


def run_cli(script: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], cwd=cwd, check=False, capture_output=True, text=True)


def test_cli_root_from_every_cwd(layout: Layout) -> None:
    cwds = [
        layout.parent,
        layout.worktree,
        layout.meshy,
        layout.meshy_worktree,
        layout.world,
        layout.world / "sub",
        layout.outside,
    ]
    for copy in (layout.parent, layout.worktree):
        script = copy / ".agents" / "scripts" / "agent_tmp.py"
        for cwd in cwds:
            result = run_cli(script, "root", cwd=cwd)

            assert result.returncode == 0, (script, cwd, result.stderr)
            assert result.stdout == f"{layout.parent}\n", (script, cwd)


def test_cli_mkdir_from_worktree_copy_writes_parent_tmp(layout: Layout) -> None:
    script = layout.worktree / ".agents" / "scripts" / "agent_tmp.py"

    result = run_cli(script, "mkdir", "issue-123", cwd=layout.meshy_worktree)

    assert result.returncode == 0, result.stderr
    created = Path(result.stdout.removesuffix("\n"))
    assert created.parent == layout.parent / "tmp" / "agents"
    assert created.name.startswith("issue-123.")
    assert created.is_dir()
    assert stat.S_IMODE(created.stat().st_mode) == 0o700
    assert not (layout.worktree / "tmp").exists()
    assert not (layout.meshy_worktree / "tmp").exists()
    assert git(layout.parent, "status", "--porcelain") == ""
    assert git(layout.worktree, "status", "--porcelain") == ""
