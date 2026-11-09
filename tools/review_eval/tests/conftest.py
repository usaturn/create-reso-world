"""review_eval のテストの隔離: 利用者の設定（~/.config の review-eval.toml）を読ませない。

各テストの前に REVIEW_EVAL_CONFIG を空文字（明示的に無効）にする。収集を有効にして確かめるテストは、
テストの中で monkeypatch.setenv で tmp_path の設定に上書きする。このディレクトリのテストだけに効く。
"""

import pytest


@pytest.fixture(autouse=True)
def _no_user_review_eval_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")
