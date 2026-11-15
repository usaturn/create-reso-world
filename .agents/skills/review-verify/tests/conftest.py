"""State observation for safety tests; never follow fixture symlinks."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from collections.abc import Callable

import pytest


@pytest.fixture(autouse=True)
def isolated_review_eval_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """利用者の review-eval 設定を読ませない（収集は既定で無効）。"""
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")


@pytest.fixture
def managed_state() -> Callable[[Path], dict[str, tuple[int, bytes | str | None]]]:
    def observe(root: Path) -> dict[str, tuple[int, bytes | str | None]]:
        result: dict[str, tuple[int, bytes | str | None]] = {}

        def visit(path: Path) -> None:
            info = path.lstat()
            value: bytes | str | None = None
            if stat.S_ISLNK(info.st_mode):
                value = os.readlink(path)
            elif stat.S_ISREG(info.st_mode):
                value = path.read_bytes()
            result[str(path.relative_to(root))] = (info.st_mode, value)
            if stat.S_ISDIR(info.st_mode):
                for child in path.iterdir():
                    visit(child)

        visit(root)
        return result

    return observe
