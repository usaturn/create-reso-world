"""`.agents/scripts` の helper のテストに共通の fixture。"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_review_eval_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """利用者の review-eval 設定を読ませない（収集は既定で無効）。"""
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")
