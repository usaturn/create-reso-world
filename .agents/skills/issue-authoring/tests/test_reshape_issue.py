"""整形で元本文・管理ブロックを失うと復元できないため、復元と改変の拒否を検証する。"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

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
    metadata = reshape.fmt.IssueMetadata.model_validate_json(
        '{"filed_on":"2026-11-09",'
        '"bases":[{"repository":"usaturn/create-reso-world","branch":"main","sha":"' + "0" * 40 + '"}],'
        '"estimate":{"hours_low":1,"hours_high":2,"confidence":"high","uncertainties":[]},'
        '"baselines":[],"targets":[],"discovery":{"links":[],"note":"整形の確認"}}'
    )
    old_block = reshape.fmt.render_block(metadata).replace("\n", "\r\n")
    original += old_block + "\r\n"
    prepared = reshape.prepare_body(original)
    edited = list(prepared.segments)
    edited[0] = edited[0].replace("CRLF を保つ。", "CRLF を保ち、編集した。")
    built = reshape.build_body(original, edited)
    view = reshape.prepare_body(built)
    assert reshape.verify_body(original, built).ok
    assert view.archive_body == original
    assert old_block in view.archive_body
    assert [item.text for item in view.managed_ranges] == [item.text for item in prepared.managed_ranges]
    assert view.archive is not None
    assert not reshape.verify_body(original, built.replace("管理された内容。", "消えた内容。", 1)).ok
    altered = view.archive.replace("非ASCIIの本文", "改変した本文", 1)
    assert altered != view.archive
    assert not reshape.verify_body(original, built.replace(view.archive, altered, 1)).ok
    rebuilt = reshape.build_body(built, list(view.segments))
    assert reshape.prepare_body(rebuilt).archive_body == original
    assert reshape.verify_body(built, rebuilt).ok


def test_added_managed_blocks_do_not_rewrite_archived_original() -> None:
    """追加を凍結済み原文に混入させず、曖昧な対応で履歴を書き換えない。"""
    spec = importlib.util.spec_from_file_location("reshape_issue", SCRIPT)
    assert spec is not None and spec.loader is not None
    reshape: Any = importlib.util.module_from_spec(spec)
    sys.modules["reshape_issue"] = reshape
    spec.loader.exec_module(reshape)

    def board(name: str, text: str) -> str:
        return (
            f"<!-- planning-parallel-issues:board:{name}:start -->\r\n"
            f"{text}\r\n<!-- planning-parallel-issues:board:{name}:end -->\r\n"
        )

    original = "元本文 α\r\n" + board("keep", "元の管理対象") + "後続\r\n"
    prepared = reshape.prepare_body(original)
    built = reshape.build_body(original, list(prepared.segments))
    view = reshape.prepare_body(built)
    assert view.archive is not None
    addition = board("extra", "追加 β")
    added = built + "\r\n" + addition
    added_view = reshape.prepare_body(added)
    rebuilt = reshape.build_body(added, list(added_view.segments))
    restored = reshape.prepare_body(rebuilt)
    assert reshape.verify_body(added, rebuilt).ok
    assert restored.archive_body == original
    assert addition in [item.text for item in restored.managed_ranges]
    assert restored.archive == view.archive
    duplicate = built.replace(view.archive, board("keep", "曖昧な追加") + "\r\n" + view.archive, 1)
    with pytest.raises(reshape.ReshapeError):
        reshape.prepare_body(duplicate)
