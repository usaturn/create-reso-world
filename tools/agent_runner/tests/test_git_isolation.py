"""外から渡された ``GIT_*`` が、テストの fixture の git に届かないこと（#166）。

linked worktree で ``git rebase --exec '<pytest>'`` を実行すると、git はその worktree の ``GIT_DIR`` を export して
コマンドを起動する。ルートの ``conftest.py`` が ``GIT_*`` を除かないと、一時リポジトリを作る fixture の
``git init``・``git -C <一時ディレクトリ>`` がそのリポジトリの共有の設定・index・ブランチを書き換える。
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_fixture_git_stays_in_its_temporary_repository(tmp_path: Path) -> None:
    # 下のテストが GIT_DIR を export して別のプロセスで実行する。fixture（test_workspace.py の repository など）と同じ形
    root = tmp_path / "fixture"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    (root / "tracked.txt").write_text("committed\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "initial")
    assert Path(git(root, "rev-parse", "--absolute-git-dir")) == root / ".git"


def snapshot(main: Path, linked: Path) -> tuple[bytes, str, str, bytes, str]:
    gitdir = Path(git(linked, "rev-parse", "--absolute-git-dir"))
    return (
        (main / ".git" / "config").read_bytes(),
        git(linked, "symbolic-ref", "HEAD"),
        git(linked, "rev-parse", "HEAD"),
        (gitdir / "index").read_bytes(),
        git(linked, "status", "--porcelain", "--untracked-files=all"),
    )


def test_inherited_git_dir_of_a_linked_worktree_does_not_reach_fixture_git(tmp_path: Path) -> None:
    main = tmp_path / "main"
    main.mkdir()
    git(main, "init", "-q", "-b", "main")
    git(main, "config", "user.name", "Owner")
    git(main, "config", "user.email", "owner@example.invalid")
    (main / "real.txt").write_text("real\n")
    git(main, "add", ".")
    git(main, "commit", "-qm", "real")
    linked = tmp_path / "linked"
    git(main, "worktree", "add", "-q", "-b", "work", str(linked))
    before = snapshot(main, linked)

    # linked worktree の git rebase --exec が export するのと同じ GIT_DIR（その worktree の管理領域の絶対パス）
    env = dict(os.environ, GIT_DIR=git(linked, "rev-parse", "--absolute-git-dir"))
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "--basetemp", str(tmp_path / "inner"),
            f"{Path(__file__).resolve()}::test_fixture_git_stays_in_its_temporary_repository",
        ],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(main, linked) == before
