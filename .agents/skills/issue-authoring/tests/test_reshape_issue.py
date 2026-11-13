"""整形で元本文・管理ブロックを失うと復元できないため、復元と改変の拒否を検証する。"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reshape_issue.py"


def test_original_and_managed_content_survive_reshape() -> None:
    spec = importlib.util.spec_from_file_location("reshape_issue", SCRIPT)
    assert spec is not None and spec.loader is not None
    reshape: Any = importlib.util.module_from_spec(spec)
    sys.modules["reshape_issue"] = reshape
    spec.loader.exec_module(reshape)

    original = "\r\n".join(
        [
            "## 概要", "", "非ASCIIの本文と <span>HTML</span>。", "",
            "```text", "<!-- planning-parallel-issues:ledger:start -->", "例", "```", "",
            "<!-- コメント -->", "", "## 問題", "CRLF を保つ。", "",
            "<!-- planning-parallel-issues:board:demo:start -->", "管理された内容。",
            "<!-- planning-parallel-issues:ledger:start -->", "記録", "<!-- planning-parallel-issues:ledger:end -->",
            "<!-- planning-parallel-issues:board:demo:end -->", "", "## 対象外", "なし。", "",
        ]
    )
    prepared = reshape.prepare_body(original)
    edited = list(prepared.segments)
    edited[0] = edited[0].replace("CRLF を保つ。", "CRLF を保ち、編集した。")
    built = reshape.build_body(original, edited)
    view = reshape.prepare_body(built)
    assert reshape.verify_body(original, built).ok
    assert view.archive_body == original
    assert [item.text for item in view.managed_ranges] == [item.text for item in prepared.managed_ranges]
    assert view.archive is not None
    assert not reshape.verify_body(original, built.replace("管理された内容。", "消えた内容。", 1)).ok
    altered = view.archive.replace("非ASCIIの本文", "改変した本文", 1)
    assert altered != view.archive
    assert not reshape.verify_body(original, built.replace(view.archive, altered, 1)).ok
    rebuilt = reshape.build_body(built, list(view.segments))
    assert reshape.prepare_body(rebuilt).archive_body == original
    assert reshape.verify_body(built, rebuilt).ok
