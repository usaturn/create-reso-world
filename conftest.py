"""リポジトリの pytest のテスト全体（``pyproject.toml`` の ``testpaths`` と、パスを指定した実行）に共通の fixture。"""

import os

import pytest


@pytest.fixture(autouse=True)
def drop_inherited_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """テストと、テストが起動する git に、外から渡された ``GIT_*`` を届けない（#166）。

    linked worktree の ``git rebase --exec`` は ``GIT_DIR`` を export するので、引き継ぐと一時リポジトリを作る
    ``git init``・``git -C <一時ディレクトリ>`` も、そのリポジトリの共有の設定・index・ブランチを書き換える。
    pytest は上の階層の autouse fixture から準備するので、各スイートの fixture が後から足す
    ``GIT_CONFIG_GLOBAL`` などは消さない。回帰テストは ``tools/agent_runner/tests/test_git_isolation.py``。
    """
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
