"""整形で元本文・管理ブロックを失うと復元できないため、復元と改変の拒否を検証する。"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reshape_issue.py"

BOARD_KEY = "agent-workspace-port-2026-11-08"
BOARD_LINE = f"<!-- planning-parallel-issues board: {BOARD_KEY} -->"
LEDGER_START = "<!-- board-ledger:start -->"
LEDGER_END = "<!-- board-ledger:end -->"
LEDGER_ROW = "| `alpha` | #1 |"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("reshape_issue", SCRIPT)
    assert spec is not None and spec.loader is not None
    reshape: Any = importlib.util.module_from_spec(spec)
    sys.modules["reshape_issue"] = reshape
    spec.loader.exec_module(reshape)
    return reshape


def test_original_and_managed_content_survive_reshape() -> None:
    reshape = _load()

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
    reshape = _load()

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


@pytest.mark.parametrize("variant", ["plain", "no-final-newline", "with-board-range"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_board_ledger_form_survives_reshape(newline: str, variant: str) -> None:
    """board-ledger 形式の ledger が、整形で黙って失われたり編集スロットへ混ざったりしない。"""
    reshape = _load()
    head = [
        "## 概要", "", "非ASCIIの文と <span>HTML</span>。", "",
        "```text", LEDGER_START, "```", "",
        "## Publication ledger", "",
        BOARD_LINE, LEDGER_START, "子 Issue の作成後に実際の値を記録した。", "",
        "| key | issue |", "|---|---|", LEDGER_ROW, LEDGER_END,
    ]  # fmt: skip
    if variant == "no-final-newline":
        original = newline.join(head)
    else:
        tail = ["", "## 対象外", "なし。"]
        if variant == "with-board-range":
            tail += [
                "", "<!-- planning-parallel-issues:board:demo:start -->", "管理された内容。",
                "<!-- planning-parallel-issues:board:demo:end -->",
            ]  # fmt: skip
        original = newline.join([*head, *tail]) + newline
    begin = original.index(BOARD_LINE)
    end = original.index(LEDGER_END) + len(LEDGER_END)
    if original[end:].startswith(newline):
        end += len(newline)
    ledger_text = original[begin:end]

    prepared = reshape.prepare_body(original)
    ledgers = [item for item in prepared.managed_ranges if item.kind == "ledger"]
    assert [(item.kind, item.name) for item in ledgers] == [("ledger", f"legacy-ledger:{BOARD_KEY}")]
    assert ledgers[0].text == ledger_text
    assert len(prepared.managed_ranges) == (2 if variant == "with-board-range" else 1)
    assert all(LEDGER_ROW not in segment for segment in prepared.segments)

    built = reshape.build_body(original, list(prepared.segments))
    view = reshape.prepare_body(built)
    assert reshape.verify_body(original, built).ok
    assert view.archive_body == original
    assert [item.text for item in view.managed_ranges] == [item.text for item in prepared.managed_ranges]
    rebuilt = reshape.build_body(built, list(view.segments))
    assert reshape.verify_body(built, rebuilt).ok
    assert reshape.prepare_body(rebuilt).archive_body == original
    assert not reshape.verify_body(original, built.replace(LEDGER_ROW, "| `alpha` | #2 |", 1)).ok


@pytest.mark.parametrize("body_kind", ["child", "child-in-ledger"])
def test_child_marker_is_kept(body_kind: str) -> None:
    """子マーカーを認識し損ねたり、board-ledger 形式の範囲の中の子マーカーで拒否・分断したりしない。"""
    reshape = _load()
    child = "<!-- planning-parallel-issues board:demo child:alpha parent:349 -->"
    if body_kind == "child":
        original = "\n".join([child, "## 概要", "子の本文。", "", "## 対象外", "なし。", ""])
    else:
        original = "\n".join(
            [
                "## 概要", "本文。", "", BOARD_LINE, LEDGER_START, "| key | issue |", "|---|---|", LEDGER_ROW,
                child, LEDGER_END, "", "## 対象外", "なし。", "",
            ]
        )  # fmt: skip
    prepared = reshape.prepare_body(original)
    built = reshape.build_body(original, list(prepared.segments))
    assert reshape.verify_body(original, built).ok
    if body_kind == "child":
        assert [item.kind for item in prepared.managed_ranges] == ["child"]
        assert reshape.prepare_body(built).segments[0] == ""
        assert built.split("\n", 1)[0] == child
    else:
        assert [(item.kind, item.name) for item in prepared.managed_ranges] == [
            ("ledger", f"legacy-ledger:{BOARD_KEY}")
        ]
        assert child in prepared.managed_ranges[0].text
        assert all(child not in segment for segment in prepared.segments)


@pytest.mark.parametrize(
    "lines",
    [
        [BOARD_LINE, LEDGER_START, "x"],
        [LEDGER_START, "x", LEDGER_END],
        ["<!-- planning-parallel-issues unknown -->"],
    ],
    ids=["ledger-not-closed", "ledger-without-board-line", "unknown-marker"],
)
def test_broken_or_unknown_board_markers_are_rejected(lines: list[str]) -> None:
    """壊れたマーカーが編集可能なスロットへ入り、整形で黙って消えない。"""
    reshape = _load()
    body = "\n".join(["## 概要", "本文。", "", *lines, "", "## 対象外", "なし。"])
    with pytest.raises(reshape.ReshapeError):
        reshape.prepare_body(body)
