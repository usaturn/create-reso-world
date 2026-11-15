"""review-fix-planning のテストから利用者の review-eval 設定を読ませない。"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_review_eval_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """収集は既定で無効にする（有効な設定を使うテストだけが上書きする）。"""
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")
