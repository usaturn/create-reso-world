#!/usr/bin/env python3
"""Issue の本文を、管理対象の範囲を変えずに整形する（Issue #869）。

- ``prepare``: snapshot の本文を、編集できるスロットと ``planning-parallel-issues`` の管理対象に分ける
- ``build``: 編集したスロットを管理対象と組み立て、整形前の本文の archive を末尾に足す
- ``verify``: ``publish_issue.py`` の draft 本文を、snapshot・管理対象・archive と突き合わせる

GitHub へ接続も投稿もしない。本文は UTF-8 のバイト列をそのまま文字列にして扱い、改行を変換しない。
依存は標準ライブラリ・pydantic・``.agents/scripts/issue_format.py`` だけ（``tools.*`` は import しない）。
"""

import argparse
import difflib
import hashlib
import importlib.util
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, NoReturn, cast
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, ValidationError

ManagedKind = Literal["board", "ledger", "child"]

ROOT = Path(__file__).resolve().parents[4]
FORMAT_MODULE = ROOT / ".agents/scripts/issue_format.py"
FILE_MODE = 0o600


def _archive_summary() -> str:
    """初回の summary。build を実行した日を記録し、verify の期待値には使わない。"""
    recorded = datetime.now(UTC).date().isoformat()
    return f"整形前の本文（{recorded} に issue-authoring が保存）"


ARCHIVE_SUMMARY = _archive_summary()
_PAD_MARK = "pad"
_RECORDED_SUMMARY = re.compile(r"整形前の本文（\d{4}-\d{2}-\d{2} に issue-authoring が保存）")
URL_PARTS = 4

_BOARD_START = re.compile(r"^<!-- planning-parallel-issues:(?P<name>.+):start -->$")
_BOARD_END = re.compile(r"^<!-- planning-parallel-issues:(?P<name>.+):end -->$")
_CHILD_MARKER = re.compile(
    r"^<!-- planning-parallel-issues board:(?P<board>\S+) child:(?P<child>\S+) parent:(?P<parent>[1-9][0-9]*) -->$"
)
_PLANNING_LINE = re.compile(r"^ {0,3}<!-- planning-parallel-issues")
_COMMENT_OPEN = re.compile(r"^ {0,3}<!--")
_DETAILS_OPEN = re.compile(r"^<details><summary>(?P<summary>[^<>]*)</summary>$")
_ARCHIVE_FENCE = re.compile(r"(?:`{3,}|~{3,})[ \t]*(?P<info>.*?)[ \t]*$")
_SHA256 = re.compile(r"[0-9a-fA-F]{64}")


def _load_format() -> Any:
    """``issue_format.py`` を ``sys.modules`` に登録してから実行する。"""
    spec = importlib.util.spec_from_file_location("issue_format", FORMAT_MODULE)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {FORMAT_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["issue_format"] = module
    spec.loader.exec_module(module)
    return module


fmt: Any = _load_format()


class ReshapeError(ValueError):
    """入力・範囲の曖昧さ・保存の失敗。CLI は標準エラー出力に理由を書いて終了コード 2 にする。"""


class _ArchiveRestoreError(ReshapeError):
    """新形式の archive を、保存すべき本文へ戻せない。"""


class _Stop(Exception):
    """処理を止める。``result`` を JSON として出し、終了コード 1 にする。"""

    def __init__(self, result: dict[str, object]) -> None:
        self.result = result
        super().__init__(str(result.get("status")))


class _Snapshot(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    number: int
    html_url: str
    body: str | None = None
    pull_request: object | None = None

    @property
    def is_pull_request(self) -> bool:
        return "pull_request" in self.model_fields_set


class _DraftTarget(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    repository: str
    number: int


class _DraftExpected(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    body_sha256: str


class _Draft(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    action: str
    repository: str | None = None
    body: str
    target: _DraftTarget | None = None
    expected: _DraftExpected | None = None


@dataclass(frozen=True)
class _Span:
    start: int
    end: int
    start_line: int
    end_line: int


@dataclass(frozen=True)
class ManagedRange:
    """管理対象の範囲 1 つ。``text`` は本文から切り出したバイト同一の文字列。"""

    kind: Literal["board", "ledger", "child"]
    name: str
    text: str
    slot_index: int
    start_line: int
    end_line: int


@dataclass(frozen=True)
class PreparedBody:
    """本文の分割結果。``segments`` は管理対象の数 + 1 個の編集可能なスロット。"""

    body: str
    segments: tuple[str, ...]
    managed_ranges: tuple[ManagedRange, ...]
    metadata: Any | None
    metadata_block: str | None
    archive: str | None
    archive_body: str | None
    content_without_appendices: str
    archive_span: _Span | None = None
    metadata_span: _Span | None = None

    @property
    def managed(self) -> tuple[ManagedRange, ...]:
        """``managed_ranges`` の別名（管理対象の範囲）。"""
        return self.managed_ranges

    @property
    def original(self) -> str:
        """入力の本文の別名。"""
        return self.body

    @property
    def has_archive(self) -> bool:
        return self.archive is not None

    @property
    def child_marker(self) -> str | None:
        return next((item.text for item in self.managed_ranges if item.kind == "child"), None)

    @property
    def expected_original(self) -> str:
        """再構成した保存本文。archive が無ければ入力の本文。"""
        return self.archive_body if self.archive_body is not None else self.body


@dataclass(frozen=True)
class PreservationReport:
    """完成本文が、管理対象・先頭マーカー・archive を保存しているかの検査結果。"""

    managed_ranges_match: bool
    expected_managed_count: int
    actual_managed_count: int
    child_marker_first: bool
    archive_present: bool
    archive_matches: bool
    archive_wrapper_matches: bool
    metadata_present: bool
    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return (
            self.managed_ranges_match
            and self.child_marker_first
            and self.archive_present
            and self.archive_matches
            and self.archive_wrapper_matches
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "managed_ranges_match": self.managed_ranges_match,
            "expected_managed_count": self.expected_managed_count,
            "actual_managed_count": self.actual_managed_count,
            "child_marker_first": self.child_marker_first,
            "archive_present": self.archive_present,
            "archive_matches": self.archive_matches,
            "archive_wrapper_matches": self.archive_wrapper_matches,
            "metadata_present": self.metadata_present,
            "problems": list(self.problems),
        }


def _format_error(action: str, error: BaseException) -> ReshapeError:
    problems = getattr(error, "problems", None)
    detail = "; ".join(str(item) for item in problems) if problems else str(error)
    return ReshapeError(f"{action}: {detail}")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _line_end(body: str, lines: Sequence[Any], index: int) -> int:
    """``index`` の行の終わり。次の LF も含め、行の単位で切り出す。

    直後が archive でも、もともと範囲に含まれる LF や CRLF は外さない。末尾に LF が無い管理対象のために
    足した区切りは、ここではなく新形式の pad だけが管理対象から外す。
    """
    end = lines[index].start + len(lines[index].raw)
    if end < len(body) and body[end] == "\n":
        end += 1
    return end


def _line_span(body: str, lines: Sequence[Any], start: int, end: int) -> _Span:
    return _Span(lines[start].start, _line_end(body, lines, end), start + 1, end + 1)


def _overlaps(first: _Span, second: _Span) -> bool:
    return first.start < second.end and second.start < first.end


def _skip_blank(lines: Sequence[Any], index: int, step: int) -> int | None:
    while 0 <= index < len(lines):
        if lines[index].text.strip():
            return index
        index += step
    return None


def _fence_groups(lines: Sequence[Any]) -> list[tuple[int, int]]:
    groups: list[tuple[int, int]] = []
    index = 0
    while index < len(lines):
        if not lines[index].in_fence:
            index += 1
            continue
        end = index
        while end + 1 < len(lines) and lines[end + 1].in_fence:
            end += 1
        groups.append((index, end))
        index = end + 1
    return groups


def _comment_covered(lines: Sequence[Any]) -> set[int]:
    """HTML コメントの中にある行の添字（0 から数える）。開始の行は含めない。

    ``issue_format._excluded_numbers`` と同じく、コードブロックの外の行頭（空白 0〜3 個）の ``<!--`` だけを開始とし、
    開始より後の最初に ``-->`` を含む行（無ければ本文の最後）までを返す。行の途中の ``<!--``（インラインコードなど）
    は開始にしない。``--!>`` は閉じとして数えない。開始行を含めないのは、同じ行で閉じるマーカー行を飛ばさないため。
    """
    covered: set[int] = set()
    index = 0
    while index < len(lines):
        if lines[index].in_fence or not _COMMENT_OPEN.match(lines[index].text):
            index += 1
            continue
        closing = next((i for i in range(index, len(lines)) if "-->" in lines[i].text), len(lines) - 1)
        covered.update(range(index + 1, closing + 1))
        index = closing + 1
    return covered


def _archive_info(text: str) -> str | None:
    """囲みの開始行の info が旧形式か新形式なら、その info を返す。"""
    match = _ARCHIVE_FENCE.search(text)
    if match is None:
        return None
    info = match.group("info")
    if info in (fmt.ORIGINAL_INFO, fmt.MANAGED_ORIGINAL_INFO):
        return str(info)
    return None


def _find_archive(body: str, lines: Sequence[Any]) -> tuple[str, str, _Span, str] | None:
    """archive の包み全体・囲みの中身・範囲・info を返す。中身はまだ復元していない。"""
    found: list[tuple[int, int, str]] = []
    for opening, closing in _fence_groups(lines):
        info = _archive_info(lines[opening].text)
        if info is not None:
            found.append((opening, closing, info))
    if not found:
        return None
    if len(found) != 1:
        raise ReshapeError("the body contains more than one archive")
    opening, closing, info = found[0]
    try:
        payload = fmt.unwrap_original(body, info=info)
    except fmt.FormatError as error:
        raise _format_error("the archive cannot be read", error) from None
    if payload is None:
        raise ReshapeError("the archive fence cannot be located uniquely")
    details = _skip_blank(lines, opening - 1, -1)
    if details is None or not _DETAILS_OPEN.match(lines[details].text):
        raise ReshapeError("the archive is not wrapped by a <details><summary> line")
    after = _skip_blank(lines, closing + 1, 1)
    if after is None or lines[after].text != "</details>":
        raise ReshapeError("the archive is not closed by a </details> line")
    covered = _comment_covered(lines)
    if any(index in covered for index in (details, opening, closing, after)):
        raise ReshapeError("the archive is inside an HTML comment")
    span = _line_span(body, lines, details, after)
    # 包みの同一性は </details> の行末までで比べる。付録の間の改行は write_metadata が足す区切りである
    wrapper = body[span.start : lines[after].start + len(lines[after].text)]
    return wrapper, payload, span, info


def _managed_ranges(body: str, lines: Sequence[Any]) -> tuple[list[tuple[ManagedKind, str, _Span]], str | None]:
    """管理対象の範囲を、外側の範囲だけ返す。囲み・HTML コメントの中のマーカーは無視する。"""
    stack: list[tuple[ManagedKind, str, int, str]] = []
    ranges: list[tuple[ManagedKind, str, _Span]] = []
    covered = _comment_covered(lines)
    child_marker: str | None = None
    for index, line in enumerate(lines):
        if line.in_fence or index in covered:
            continue
        child = _CHILD_MARKER.fullmatch(line.text)
        if child is not None:
            if stack:
                continue
            if child_marker is not None:
                raise ReshapeError("the body contains more than one child marker")
            if index != 0:
                raise ReshapeError("the child marker is not on the first line")
            child_marker = line.text
            ranges.append(("child", "child", _line_span(body, lines, index, index)))
            continue
        started = _BOARD_START.fullmatch(line.text)
        ended = _BOARD_END.fullmatch(line.text)
        if started is not None:
            name = started["name"]
            if name == "board:" or (name != "ledger" and not name.startswith("board:")):
                raise ReshapeError(f"an unknown planning-parallel-issues range name is present: {name}")
            kind: ManagedKind = "board" if name.startswith("board:") else "ledger"
            stack.append((kind, name, index, line.text))
            continue
        if ended is not None:
            if not stack or stack[-1][1] != ended["name"]:
                raise ReshapeError(f"the managed range {ended['name']} has no matching start marker")
            token = stack.pop()
            if not stack:
                ranges.append((token[0], token[1], _line_span(body, lines, token[2], index)))
            continue
        if _PLANNING_LINE.match(line.text):
            raise ReshapeError(f"an unknown planning-parallel-issues marker is present on line {index + 1}")
    if stack:
        raise ReshapeError(f"the managed range {stack[-1][1]} is not closed")
    ranges.sort(key=lambda item: item[2].start)
    return ranges, child_marker


def _expanded_appendix_span(body: str, lines: Sequence[Any], span: _Span) -> _Span:
    """付録の前後の、内容を持たない空行を付録の範囲に含める。"""
    start = span.start_line - 1
    while start > 0 and not lines[start - 1].text.strip():
        start -= 1
    end = span.end_line - 1
    trailing = body[_line_end(body, lines, end) :]
    end_offset = len(body) if not trailing.strip() else span.end
    return _Span(lines[start].start, end_offset, start + 1, span.end_line)


def _remove_spans(text: str, absolute_start: int, spans: Sequence[_Span]) -> str:
    """``text`` から、絶対位置の ``spans`` を除いてつなぐ。"""
    absolute_end = absolute_start + len(text)
    cursor = 0
    pieces: list[str] = []
    for span in sorted(spans, key=lambda item: item.start):
        if span.end <= absolute_start or span.start >= absolute_end:
            continue
        start = max(span.start, absolute_start) - absolute_start
        end = max(span.end, absolute_start) - absolute_start
        if start < cursor:
            start = cursor
        if end <= cursor:
            continue
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def _join_segments(segments: Sequence[str], managed: Sequence[ManagedRange]) -> str:
    parts: list[str] = []
    for index, item in enumerate(managed):
        parts.append(segments[index])
        parts.append(item.text)
    parts.append(segments[-1])
    return "".join(parts)


def _managed_spans(body: str) -> list[tuple[ManagedKind, str, _Span]]:
    lines = fmt.scan_lines(body)
    ranges, _child = _managed_ranges(body, lines)
    return ranges


def _identities_of(body: str) -> list[tuple[str, str, str]] | None:
    """管理対象の kind・name・text。範囲が壊れているときは ``None``。"""
    try:
        spans = _managed_spans(body)
    except ReshapeError:
        return None
    return [(kind, name, body[span.start : span.end]) for kind, name, span in spans]


def _choose_delimiter(parts: Sequence[str]) -> str:
    """``parts`` に含まれない最短の ``@`` の並び。長さは 2 以上。"""
    longest = 1
    for part in parts:
        for run in re.finditer(r"@+", part):
            longest = max(longest, len(run.group()))
    return "@" * (longest + 1)


def _needs_archive_pad(saved: str, spans: Sequence[tuple[ManagedKind, str, _Span]]) -> bool:
    """保存本文の末尾が管理対象の中で、その末尾に LF が無い。"""
    return bool(spans) and spans[-1][2].end == len(saved) and not saved.endswith("\n")


def _encode_managed_payload(saved: str, spans: Sequence[tuple[ManagedKind, str, _Span]], *, pad: bool) -> str:
    """管理対象外の位置スライスと位置マーカーだけを持つ payload を作る。JSON にはしない。"""
    if not spans:
        raise ReshapeError("the managed archive requires at least one managed range")
    slices: list[str] = []
    labels: list[str] = []
    cursor = 0
    for kind, name, span in spans:
        if span.start < cursor or span.end < span.start or span.end > len(saved):
            raise ReshapeError("the managed ranges overlap or are out of order")
        slices.append(saved[cursor : span.start])
        labels.append(f"{kind}:{name}")
        cursor = span.end
    slices.append(saved[cursor:])
    delimiter = _choose_delimiter([*slices, *labels])
    pieces: list[str] = []
    for index, label in enumerate(labels):
        pieces.append(slices[index])
        pieces.append(f"{delimiter}{label}{delimiter}")
    pieces.append(slices[-1])
    mark = f" {_PAD_MARK}" if pad else ""
    return f"{fmt.MANAGED_ORIGINAL_INFO} {delimiter}{mark}\n{''.join(pieces)}"


def _managed_header(payload: str) -> tuple[str, bool, str]:
    """区切り、pad の有無、ヘッダの次の行以降。"""
    header, separator, content = payload.partition("\n")
    if not separator:
        raise _ArchiveRestoreError("the managed archive has no header")
    header = header.removesuffix("\r")
    prefix = f"{fmt.MANAGED_ORIGINAL_INFO} "
    if not header.startswith(prefix):
        raise _ArchiveRestoreError("the managed archive header is not valid")
    delimiter, separated, mark = header[len(prefix) :].partition(" ")
    if (separated and mark != _PAD_MARK) or len(delimiter) < 2 or any(char != "@" for char in delimiter):
        raise _ArchiveRestoreError("the managed archive header is not valid")
    return delimiter, bool(separated), content


def _match_managed_labels(payload: str, managed: Sequence[tuple[str, str, str]]) -> tuple[list[int], list[str]]:
    """archive の位置マーカーを live の管理対象へ順序を保って一意に対応付ける。

    対応する live の添字の列と、区切りで分割した parts を返す。archive に無い live（追加）は対応に使わない。
    削除・順序違い・kind/name の違い・一意でない対応・構造不正は黙って通さない。
    """
    if not managed:
        raise _ArchiveRestoreError("the managed archive has no live managed ranges")
    delimiter, _pad, content = _managed_header(payload)
    parts = content.split(delimiter)
    # 区切りが本文に混ざると分割数が増える。マーカーを全て消すと k = 0 になる
    if len(parts) < 3 or len(parts) % 2 == 0:
        raise _ArchiveRestoreError("the managed archive markers do not match the live managed ranges")
    labels = parts[1::2]
    live = [f"{kind}:{name}" for kind, name, _text in managed]
    left: list[int] = []
    cursor = 0
    for label in labels:
        while cursor < len(live) and live[cursor] != label:
            cursor += 1
        if cursor == len(live):
            raise _ArchiveRestoreError("the managed archive markers do not match the live managed ranges")
        left.append(cursor)
        cursor += 1
    right: list[int] = []
    cursor = len(live) - 1
    for label in reversed(labels):
        while cursor >= 0 and live[cursor] != label:
            cursor -= 1
        if cursor < 0:
            raise _ArchiveRestoreError("the managed archive markers do not match the live managed ranges")
        right.append(cursor)
        cursor -= 1
    right.reverse()
    if left != right:
        raise _ArchiveRestoreError("the managed archive markers do not match the live managed ranges uniquely")
    return left, parts


def _restore_managed_archive(payload: str, managed: Sequence[tuple[str, str, str]]) -> str:
    """位置マーカーを live の管理対象で戻す。追加は復元に使わず許容する。欠落・不一致・衝突は黙って通さない。"""
    matched, parts = _match_managed_labels(payload, managed)
    restored: list[str] = []
    for index, live_index in enumerate(matched):
        restored.append(parts[2 * index])
        restored.append(managed[live_index][2])
    restored.append(parts[-1])
    return "".join(restored)


def _summary_of(wrapper: str) -> str | None:
    first = wrapper.split("\n", 1)[0].removesuffix("\r")
    match = re.fullmatch(r"<details><summary>(?P<summary>[^<>]*)</summary>", first)
    if match is None:
        return None
    return match.group("summary")


def _archive_kind(wrapper: str) -> str | None:
    try:
        new_payload = fmt.unwrap_original(wrapper, info=fmt.MANAGED_ORIGINAL_INFO)
        old_payload = fmt.unwrap_original(wrapper)
    except fmt.FormatError:
        return None
    if new_payload is not None and old_payload is None:
        return str(fmt.MANAGED_ORIGINAL_INFO)
    if old_payload is not None and new_payload is None:
        return str(fmt.ORIGINAL_INFO)
    return None


def _wrap_saved(saved: str, summary: str) -> str:
    """保存すべき本文から、期待する archive の包みを一意に作る。"""
    spans = _managed_spans(saved)
    if not spans:
        try:
            return str(fmt.wrap_original(saved, summary=summary))
        except fmt.FormatError as error:
            raise _format_error("the original body cannot be wrapped", error) from None
    payload = _encode_managed_payload(saved, spans, pad=_needs_archive_pad(saved, spans))
    identities = [(kind, name, saved[span.start : span.end]) for kind, name, span in spans]
    if _restore_managed_archive(payload, identities) != saved:
        raise ReshapeError("the managed archive does not restore the saved body")
    try:
        return str(fmt.wrap_original(payload, summary=summary, info=fmt.MANAGED_ORIGINAL_INFO))
    except fmt.FormatError as error:
        raise _format_error("the original body cannot be wrapped", error) from None


def _migratable(prepared: PreparedBody, saved: str, wrapper: str) -> bool:
    """旧形式を新形式へ移してよいか。包みの改変や不一致は移行にしない。"""
    if _archive_kind(wrapper) != fmt.ORIGINAL_INFO:
        return False
    summary = _summary_of(wrapper)
    if summary is None:
        return False
    try:
        canonical = fmt.wrap_original(saved, summary=summary) == wrapper
    except fmt.FormatError:
        return False
    if not canonical:
        return False
    saved_ids = _identities_of(saved)
    if not saved_ids:
        return False
    live_ids = [(item.kind, item.name, item.text) for item in prepared.managed_ranges]
    return live_ids == saved_ids


def _recorded_summary(wrapper: str | None) -> str | None:
    """初回の包みに記録された保存日の summary。実行日では作らない。"""
    if wrapper is None:
        return None
    summary = _summary_of(wrapper)
    if summary is None or _RECORDED_SUMMARY.fullmatch(summary) is None:
        return None
    return summary


def _plan_archive(prepared: PreparedBody) -> tuple[str, str, bool]:
    """build が足す包み・保存本文・既存包みを再利用するか。

    初回の summary は build を実行した日である。verify の期待値には使わない。
    """
    if prepared.archive is None:
        return _wrap_saved(prepared.body, _archive_summary()), prepared.body, False
    if prepared.archive_body is None:
        raise ReshapeError("the archive cannot be read")
    saved = prepared.archive_body
    if _migratable(prepared, saved, prepared.archive):
        summary = _summary_of(prepared.archive)
        if summary is not None:
            return _wrap_saved(saved, summary), saved, False
    return prepared.archive, saved, True


def _expected_archive(prepared: PreparedBody, candidate_archive: str | None) -> tuple[str, str]:
    """verify が比べる包みと保存本文。初回は候補に記録された summary を使う。"""
    if prepared.archive is None:
        summary = _recorded_summary(candidate_archive)
        if summary is None:
            summary = _archive_summary()
        return _wrap_saved(prepared.body, summary), prepared.body
    wrapper, saved, _reused = _plan_archive(prepared)
    return wrapper, saved


def _separate_pad(
    body: str,
    archive_span: _Span | None,
    archive_payload: str | None,
    archive_info: str | None,
    ranges: list[tuple[ManagedKind, str, _Span]],
) -> tuple[_Span | None, list[tuple[ManagedKind, str, _Span]], int | None]:
    """pad が示す LF だけを管理対象から外し、archive の範囲へ移す。

    直後が archive であることだけでは外さない。pad が無い本文の終端 LF や CRLF はそのまま残す。
    pad の LF は archive の最後の位置マーカーの管理対象に帰属する。追加の範囲が引き受けるときは停止する。
    """
    if archive_span is None or archive_payload is None or archive_info != fmt.MANAGED_ORIGINAL_INFO:
        return archive_span, ranges, None
    delimiter, pad, content = _managed_header(archive_payload)
    if not pad:
        return archive_span, ranges, None
    if archive_span.start == 0 or body[archive_span.start - 1] != "\n":
        raise _ArchiveRestoreError("the managed archive pad is missing")
    pad_at = archive_span.start - 1
    parts = content.split(delimiter)
    # 構造不正でラベルを読めないときは、復元側の構造ガードに任せる
    last_label = parts[-2] if len(parts) >= 3 and len(parts) % 2 == 1 else None
    adjusted: list[tuple[ManagedKind, str, _Span]] = []
    found = False
    for kind, name, span in ranges:
        if span.end == pad_at + 1 and span.start <= pad_at:
            if last_label is not None and f"{kind}:{name}" != last_label:
                raise _ArchiveRestoreError(
                    "the managed archive pad does not belong to the last archived managed range"
                )
            span = _Span(span.start, pad_at, span.start_line, span.end_line)
            found = True
        adjusted.append((kind, name, span))
    if not found:
        raise _ArchiveRestoreError("the managed archive pad is not at the end of a managed range")
    covered = _Span(pad_at, archive_span.end, archive_span.start_line, archive_span.end_line)
    return covered, adjusted, pad_at


def _cover_pad(span: _Span, pad_at: int | None) -> _Span:
    """付録の展開で行頭へ戻しても、pad の LF を編集スロットへ出さない。"""
    if pad_at is None or span.start <= pad_at:
        return span
    return _Span(pad_at, span.end, span.start_line, span.end_line)


def prepare_body(body: str) -> PreparedBody:
    """本文を、編集可能なスロットと管理対象・archive・metadata に分ける。"""
    try:
        body.encode("utf-8")
    except UnicodeEncodeError:
        raise ReshapeError("the body cannot be encoded as UTF-8") from None
    lines = fmt.scan_lines(body)
    try:
        extracted = fmt.extract_block(body, "metadata")
    except fmt.FormatError as error:
        raise _format_error("the metadata block cannot be read", error) from None
    metadata: Any | None = None
    metadata_span: _Span | None = None
    if extracted.status in ("broken", "unknown_version"):
        raise ReshapeError(f"the metadata block cannot be read ({extracted.reason})")
    if extracted.status == "ok":
        metadata = extracted.value
        if extracted.line is None or extracted.end_line is None:
            raise ReshapeError("the metadata block has no position")
        if extracted.line - 1 in _comment_covered(lines):
            raise ReshapeError("the metadata block is inside an HTML comment")
        metadata_span = _line_span(body, lines, extracted.line - 1, extracted.end_line - 1)

    archive_result = _find_archive(body, lines)
    archive: str | None = None
    archive_payload: str | None = None
    archive_info: str | None = None
    archive_span: _Span | None = None
    if archive_result is not None:
        archive, archive_payload, archive_span, archive_info = archive_result

    raw_ranges, child_marker = _managed_ranges(body, lines)
    archive_span, raw_ranges, pad_at = _separate_pad(body, archive_span, archive_payload, archive_info, raw_ranges)
    for _, name, span in raw_ranges:
        for appendix in (metadata_span, archive_span):
            if appendix is not None and _overlaps(span, appendix):
                raise ReshapeError(f"the managed range {name} overlaps an archive or metadata block")
    managed = tuple(
        ManagedRange(kind, name, body[span.start : span.end], index, span.start_line, span.end_line)
        for index, (kind, name, span) in enumerate(raw_ranges)
    )
    archive_body: str | None = None
    if archive_payload is not None:
        if archive_info == fmt.MANAGED_ORIGINAL_INFO:
            archive_body = _restore_managed_archive(
                archive_payload, [(item.kind, item.name, item.text) for item in managed]
            )
        else:
            archive_body = archive_payload
    appendix_spans = [
        _cover_pad(_expanded_appendix_span(body, lines, span), pad_at)
        if span is archive_span
        else _expanded_appendix_span(body, lines, span)
        for span in (archive_span, metadata_span)
        if span is not None
    ]
    segments: list[str] = []
    previous = 0
    for _, _, span in raw_ranges:
        segments.append(_remove_spans(body[previous : span.start], previous, appendix_spans))
        previous = span.end
    segments.append(_remove_spans(body[previous:], previous, appendix_spans))
    if len(segments) != len(managed) + 1:
        raise ReshapeError("the body could not be split into slots")
    content_without_appendices = _join_segments(segments, managed)
    if child_marker is not None and segments[0] != "":
        raise ReshapeError("the child marker must be at the start of the body")
    return PreparedBody(
        body=body,
        segments=tuple(segments),
        managed_ranges=managed,
        metadata=metadata,
        metadata_block=body[metadata_span.start : metadata_span.end] if metadata_span is not None else None,
        archive=archive,
        archive_body=archive_body,
        content_without_appendices=content_without_appendices,
        archive_span=archive_span,
        metadata_span=metadata_span,
    )


def _append_appendix(prefix: str, appendix: str) -> str:
    if not prefix:
        return appendix
    newline = "\r\n" if "\r\n" in prefix else "\n"
    if prefix.endswith(newline + newline):
        return prefix + appendix
    if prefix.endswith(newline):
        return prefix + newline + appendix
    return prefix + newline + newline + appendix


def _append_archive(prefix: str, appendix: str, managed: Sequence[ManagedRange]) -> str:
    """archive を末尾へ足す。末尾に LF が無い管理対象の直後には LF を 1 つ足す。

    この LF を管理対象から外すのは、新形式の payload が pad を持つときだけである。
    直後が archive であることだけでは、もともと範囲に含まれる LF や CRLF を外さない。
    """
    if managed and not managed[-1].text.endswith("\n"):
        if prefix.endswith(managed[-1].text):
            return prefix + "\n" + appendix
        if prefix.endswith(managed[-1].text + "\n"):
            return prefix + appendix
    return _append_appendix(prefix, appendix)


def build_body(body: str, segments: Sequence[str]) -> str:
    """編集したスロットを管理対象と組み立て、archive を 1 つ足した本文を返す。"""
    prepared = prepare_body(body)
    if len(segments) != len(prepared.managed_ranges) + 1:
        raise ReshapeError(
            f"the segments must contain {len(prepared.managed_ranges) + 1} strings, not {len(segments)}"
        )
    if prepared.child_marker is not None and segments[0] != "":
        raise ReshapeError("the child marker must stay on the first line; the first slot must be empty")
    wrapper, _saved, reused = _plan_archive(prepared)
    reconnect_at: int | None = None
    if reused:
        payload = fmt.unwrap_original(wrapper, info=fmt.MANAGED_ORIGINAL_INFO)
        if payload is not None and _managed_header(payload)[1]:
            managed = [(item.kind, item.name, item.text) for item in prepared.managed_ranges]
            matched, _parts = _match_managed_labels(payload, managed)
            reconnect_at = matched[-1]
    if reconnect_at is None:
        candidate = _join_segments(segments, prepared.managed_ranges)
        candidate = _append_archive(candidate, wrapper, prepared.managed_ranges)
    else:
        # pad 付きの再利用包みは、最後の archive 管理対象の直後に pad の LF 1 つを挟んで接続する。
        # 被覆範囲が吸収した </details> 行の行末も再出力し、包みの後ろに続く内容を接着させない
        covered = prepared.archive_span
        if covered is None:
            raise ReshapeError("the managed archive pad is missing")
        # 被覆範囲は pad の LF から始まり、包みはその 1 つ後ろから行末を含まずに進む
        ending = prepared.body[covered.start + 1 + len(wrapper) : covered.end]
        pieces: list[str] = []
        for index, item in enumerate(prepared.managed_ranges):
            pieces.append(segments[index])
            pieces.append(item.text)
            if index == reconnect_at:
                pieces.append("\n" + wrapper + ending)
        pieces.append(segments[-1])
        candidate = "".join(pieces)
    try:
        candidate_prepared = prepare_body(candidate)
    except ReshapeError as error:
        raise ReshapeError(f"the composed body cannot be read back ({error})") from None
    if candidate_prepared.metadata is not None:
        raise ReshapeError("the build body must not contain a metadata block")
    report = verify_body(body, candidate)
    if not report.ok:
        detail = "; ".join(report.problems)
        raise ReshapeError(f"the composed body does not preserve the managed content ({detail})")
    return candidate


@dataclass(frozen=True)
class _CandidateFacts:
    """復元せずに candidate から測れた診断値。"""

    managed: tuple[tuple[str, str, str], ...]
    first_slot_empty: bool
    archive: str | None
    metadata_present: bool


def _observe_candidate(body: str) -> _CandidateFacts:
    """復元せずに、candidate から測れる管理対象・先頭 slot・archive・metadata を返す。

    ヘッダ不正と pad の位置違いでも、その前に走査できた範囲と包みの有無は残す。
    マーカー不一致も同じ走査を使う。復元した本文の一致はここでは判定しない。
    """
    lines = fmt.scan_lines(body)
    try:
        extracted = fmt.extract_block(body, "metadata")
    except fmt.FormatError as error:
        raise _format_error("the metadata block cannot be read", error) from None
    metadata_present = False
    metadata_span: _Span | None = None
    if extracted.status in ("broken", "unknown_version"):
        raise ReshapeError(f"the metadata block cannot be read ({extracted.reason})")
    if extracted.status == "ok":
        if extracted.line is None or extracted.end_line is None:
            raise ReshapeError("the metadata block has no position")
        if extracted.line - 1 in _comment_covered(lines):
            raise ReshapeError("the metadata block is inside an HTML comment")
        metadata_present = True
        metadata_span = _line_span(body, lines, extracted.line - 1, extracted.end_line - 1)

    archive_result = _find_archive(body, lines)
    archive: str | None = None
    archive_payload: str | None = None
    archive_info: str | None = None
    archive_span: _Span | None = None
    if archive_result is not None:
        archive, archive_payload, archive_span, archive_info = archive_result

    ranges, _child_marker = _managed_ranges(body, lines)
    pad_at: int | None = None
    try:
        archive_span, ranges, pad_at = _separate_pad(body, archive_span, archive_payload, archive_info, ranges)
    except _ArchiveRestoreError:
        pad_at = None
    managed = tuple((kind, name, body[span.start : span.end]) for kind, name, span in ranges)
    appendix_spans = [
        _cover_pad(_expanded_appendix_span(body, lines, span), pad_at)
        if span is archive_span
        else _expanded_appendix_span(body, lines, span)
        for span in (archive_span, metadata_span)
        if span is not None
    ]
    segments: list[str] = []
    previous = 0
    for _, _, span in ranges:
        segments.append(_remove_spans(body[previous : span.start], previous, appendix_spans))
        previous = span.end
    segments.append(_remove_spans(body[previous:], previous, appendix_spans))
    return _CandidateFacts(managed, segments[0] == "", archive, metadata_present)


def _wrapper_matches(prepared: PreparedBody, archive: str | None) -> bool:
    """包みのバイト列は復元なしで比べられる。比べられないときは一致したことにしない。"""
    if archive is None:
        return False
    try:
        expected_wrapper, _saved = _expected_archive(prepared, archive)
    except ReshapeError, fmt.FormatError:
        return False
    return archive == expected_wrapper


def _unrestored_report(prepared: PreparedBody, candidate: str) -> PreservationReport:
    """復元できない本文は成功にしない。走査できる診断値は candidate の実態にする。

    マーカーの欠落・不一致、ヘッダ不正、pad の位置違いは、この一つの報告で扱う。
    戻した本文が保存すべき本文と一致するかは確かめられないので、``archive_matches`` は成功にしない。
    """
    observed = _observe_candidate(candidate)
    expected = [(item.kind, item.name, item.text) for item in prepared.managed_ranges]
    actual = observed.managed
    actual_child = next((text for kind, _name, text in actual if kind == "child"), None)
    child_first = actual_child == prepared.child_marker and (actual_child is None or observed.first_slot_empty)
    return PreservationReport(
        managed_ranges_match=list(actual) == expected,
        expected_managed_count=len(expected),
        actual_managed_count=len(actual),
        child_marker_first=child_first,
        archive_present=observed.archive is not None,
        archive_matches=False,
        archive_wrapper_matches=_wrapper_matches(prepared, observed.archive),
        metadata_present=observed.metadata_present,
        problems=("the archive does not restore the original body",),
    )


def verify_body(original: str, candidate: str) -> PreservationReport:
    """完成本文が、元の本文の管理対象・先頭マーカー・archive を保存しているか検査する。"""
    prepared = prepare_body(original)
    try:
        composed = prepare_body(candidate)
    except _ArchiveRestoreError:
        return _unrestored_report(prepared, candidate)
    expected = [(item.kind, item.name, item.text) for item in prepared.managed_ranges]
    actual = [(item.kind, item.name, item.text) for item in composed.managed_ranges]
    problems: list[str] = []
    managed_match = expected == actual
    if not managed_match:
        problems.append(f"the managed ranges changed: expected {len(expected)} ranges, found {len(actual)}")
    expected_child = prepared.child_marker
    actual_child = composed.child_marker
    child_first = actual_child == expected_child and (actual_child is None or composed.segments[0] == "")
    if not child_first:
        problems.append("the child marker is missing, changed, or no longer on the first line")
    expected_wrapper, saved_body = _expected_archive(prepared, composed.archive)
    archive_present = composed.archive is not None
    archive_matches = archive_present and composed.archive_body == saved_body
    if not archive_matches:
        problems.append("the archive does not contain the original body")
    wrapper_matches = composed.archive == expected_wrapper
    if not wrapper_matches:
        problems.append("the archive wrapper does not match the expected archive")
    return PreservationReport(
        managed_ranges_match=managed_match,
        expected_managed_count=len(expected),
        actual_managed_count=len(actual),
        child_marker_first=child_first,
        archive_present=archive_present,
        archive_matches=archive_matches,
        archive_wrapper_matches=wrapper_matches,
        metadata_present=composed.metadata is not None,
        problems=tuple(problems),
    )


def _without_span(text: str, span: _Span | None) -> str:
    if span is None:
        return text
    return text[: span.start] + text[span.end :]


def _unified_diff(before: str, after: str, *, fromfile: str, tofile: str) -> str:
    """unified diff の文字列。改行で終わらない行は、次の行と連結せず ``\\ No newline at end of file`` を足す。"""
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=fromfile,
        tofile=tofile,
    )
    return "".join(line if line.endswith("\n") else f"{line}\n\\ No newline at end of file\n" for line in diff)


def _read_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise ReshapeError(f"cannot read {path}: {error.__class__.__name__}") from None


def _read_json(path: Path) -> object:
    try:
        return json.loads(_read_text(path))
    except json.JSONDecodeError as error:
        raise ReshapeError(f"{path} is not valid JSON at character {error.pos}") from None


def _load_snapshot(path: Path, repository: str, issue: int) -> _Snapshot:
    try:
        snapshot = _Snapshot.model_validate(_read_json(path))
    except ValidationError as error:
        detail = "; ".join(
            f"{'.'.join(str(item) for item in problem['loc'])}: {problem['msg']}"
            for problem in error.errors(include_input=False)
        )
        raise ReshapeError(f"{path} is not an issue snapshot ({detail})") from None
    if "body" not in snapshot.model_fields_set:
        raise ReshapeError("the snapshot has no body key")
    if snapshot.number != issue:
        raise ReshapeError(f"the snapshot is for issue {snapshot.number}, not {issue}")
    if snapshot.is_pull_request:
        raise ReshapeError("the snapshot is a pull request, not an issue")
    parts = urlparse(snapshot.html_url).path.strip("/").split("/")
    if len(parts) == URL_PARTS and parts[2] == "pull":
        raise ReshapeError("the snapshot is a pull request, not an issue")
    if len(parts) != URL_PARTS or parts[2] != "issues":
        raise ReshapeError(f"the snapshot URL is not an issue URL: {snapshot.html_url}")
    try:
        int(parts[3])
    except ValueError:
        raise ReshapeError(f"the snapshot URL has no issue number: {snapshot.html_url}") from None
    if int(parts[3]) != issue:
        raise ReshapeError(f"the snapshot URL is for issue {parts[3]}, not {issue}")
    if f"{parts[0]}/{parts[1]}".casefold() != repository.casefold():
        raise ReshapeError(f"the snapshot is not for {repository}")
    try:
        rules = fmt.load_rules(repository)
    except fmt.FormatError as error:
        raise _format_error(f"the rules for {repository} cannot be read", error) from None
    if rules.repository.casefold() != repository.casefold():
        raise ReshapeError(f"the snapshot is not for the registered repository {rules.repository}")
    return snapshot


def _body_of(snapshot: _Snapshot) -> str:
    return snapshot.body if snapshot.body is not None else ""


def _out_dir(path: str) -> Path:
    directory = Path(path).resolve()
    if directory.exists():
        if not directory.is_dir():
            raise ReshapeError(f"--out-dir is not a directory: {directory}")
        if any(directory.iterdir()):
            raise ReshapeError(f"--out-dir must be empty: {directory}")
    else:
        try:
            directory.mkdir(parents=True)
        except OSError as error:
            raise ReshapeError(f"cannot create --out-dir {directory}: {error.strerror}") from None
    return directory


def _write_bytes(directory: Path, name: str, data: bytes) -> Path:
    path = directory / name
    try:
        with path.open("xb") as handle:
            handle.write(data)
    except OSError as error:
        raise ReshapeError(f"cannot write {path}: {error.strerror}") from None
    path.chmod(FILE_MODE)
    return path


def _write_text(directory: Path, name: str, text: str) -> Path:
    try:
        data = text.encode("utf-8")
    except UnicodeEncodeError:
        raise ReshapeError(f"{name} cannot be encoded as UTF-8") from None
    return _write_bytes(directory, name, data)


def _write_json(directory: Path, name: str, value: object) -> Path:
    return _write_text(directory, name, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _manifest(prepared: PreparedBody, repository: str, issue: int) -> dict[str, object]:
    return {
        "version": 1,
        "repository": repository,
        "issue": issue,
        "body_sha256": _sha256_text(prepared.body),
        "body_length": len(prepared.body),
        "limit": fmt.BODY_LIMIT,
        "segment_count": len(prepared.segments),
        "managed_count": len(prepared.managed_ranges),
        "managed": [
            {
                "kind": item.kind,
                "name": item.name,
                "slot_index": item.slot_index,
                "start_line": item.start_line,
                "end_line": item.end_line,
                "length": len(item.text),
                "sha256": _sha256_text(item.text),
            }
            for item in prepared.managed_ranges
        ],
        "archive": prepared.archive is not None,
        "archive_body_sha256": _sha256_text(prepared.archive_body) if prepared.archive_body is not None else None,
        "metadata": prepared.metadata is not None,
    }


def _prepare(args: argparse.Namespace) -> dict[str, object]:
    snapshot = _load_snapshot(Path(args.read_json), args.repo, args.issue)
    prepared = prepare_body(_body_of(snapshot))
    directory = _out_dir(args.out_dir)
    original = _write_text(directory, "original.md", prepared.body)
    segments = _write_json(directory, "segments.json", list(prepared.segments))
    manifest = _write_json(directory, "manifest.json", _manifest(prepared, args.repo, args.issue))
    metadata_path: Path | None = None
    if prepared.metadata is not None:
        metadata_path = _write_json(directory, "metadata.json", prepared.metadata.model_dump(mode="json"))
    return {
        "status": "prepared",
        "repository": args.repo,
        "issue": args.issue,
        "original": str(original),
        "segments": str(segments),
        "manifest": str(manifest),
        "metadata": str(metadata_path) if metadata_path is not None else None,
        "segment_count": len(prepared.segments),
        "managed_count": len(prepared.managed_ranges),
        "body_length": len(prepared.body),
        "remaining": fmt.BODY_LIMIT - len(prepared.body),
        "archive": prepared.archive is not None,
    }


def _load_segments(path: Path, expected: int) -> list[str]:
    parsed = _read_json(path)
    if not isinstance(parsed, list):
        raise ReshapeError(f"{path} must be a JSON array of strings")
    values: list[str] = []
    for item in cast("list[object]", parsed):
        if not isinstance(item, str):
            raise ReshapeError(f"{path} must be a JSON array of strings")
        values.append(item)
    if len(values) != expected:
        raise ReshapeError(f"{path} must contain {expected} strings, not {len(values)}")
    return values


def _project_metadata(body: str, metadata: Any | None) -> str:
    """``write_metadata`` が作る本文を、上限の検査より前に組み立てる。"""
    if metadata is None:
        return body
    try:
        block = fmt.render_block(metadata)
    except fmt.FormatError as error:
        raise _format_error("the metadata cannot be rendered", error) from None
    stripped = body.rstrip()
    return f"{stripped}\n\n{block}" if stripped else block


def _write_metadata(body: str, metadata: Any | None) -> str:
    if metadata is None:
        return body
    try:
        return fmt.write_metadata(body, metadata)
    except fmt.FormatError as error:
        raise _format_error("the metadata cannot be written", error) from None


def _too_large(prepared: PreparedBody, projected_length: int, *, repository: str, issue: int) -> _Stop:
    managed_length = sum(len(item.text) for item in prepared.managed_ranges)
    return _Stop(
        {
            "status": "too_large",
            "repository": repository,
            "issue": issue,
            "original_length": len(prepared.body),
            "managed_length": managed_length,
            "assembled_length": projected_length,
            "limit": fmt.BODY_LIMIT,
            "remaining": fmt.BODY_LIMIT - projected_length,
        }
    )


def _build(args: argparse.Namespace) -> dict[str, object]:
    snapshot = _load_snapshot(Path(args.read_json), args.repo, args.issue)
    original = _body_of(snapshot)
    prepared = prepare_body(original)
    segments = _load_segments(Path(args.segments_file), len(prepared.managed_ranges) + 1)
    built = build_body(original, segments)
    composed = prepare_body(built)
    projected_text = _project_metadata(built, prepared.metadata)
    if len(projected_text) > fmt.BODY_LIMIT:
        raise _too_large(prepared, len(projected_text), repository=args.repo, issue=args.issue)
    projected = _write_metadata(built, prepared.metadata)
    report = verify_body(original, built)
    if not report.ok:
        raise _Stop(
            {
                "status": "preservation_failed",
                "repository": args.repo,
                "issue": args.issue,
                "preservation": report.as_dict(),
            }
        )
    diff = _unified_diff(
        prepared.content_without_appendices,
        composed.content_without_appendices,
        fromfile="元の本文（archiveとmetadataを除く）",
        tofile="新しい本文（archiveを除く）",
    )
    directory = _out_dir(args.out_dir)
    body_path = _write_text(directory, "body.md", built)
    diff_path = _write_text(directory, "diff.patch", diff)
    return {
        "status": "built",
        "repository": args.repo,
        "issue": args.issue,
        "body": str(body_path),
        "diff": str(diff_path),
        "body_length": len(built),
        "projected_length": len(projected),
        "limit": fmt.BODY_LIMIT,
        "remaining": fmt.BODY_LIMIT - len(projected),
        "managed_count": len(prepared.managed_ranges),
        "archive_added": prepared.archive is None,
        "archive_reused": _plan_archive(prepared)[2],
        "metadata": prepared.metadata is not None,
        "preservation": report.as_dict(),
    }


def _load_draft(path: Path) -> tuple[bytes, _Draft]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ReshapeError(f"cannot read {path}: {error.strerror}") from None
    try:
        draft = _Draft.model_validate_json(raw)
    except ValidationError as error:
        detail = "; ".join(
            f"{'.'.join(str(item) for item in problem['loc'])}: {problem['msg']}"
            for problem in error.errors(include_input=False)
        )
        raise ReshapeError(f"{path} is not a publish_issue draft ({detail})") from None
    return raw, draft


def _verify(args: argparse.Namespace) -> dict[str, object]:
    snapshot = _load_snapshot(Path(args.read_json), args.repo, args.issue)
    original = _body_of(snapshot)
    prepared = prepare_body(original)
    draft_path = Path(args.draft).resolve() / "draft.json"
    raw, draft = _load_draft(draft_path)
    if draft.action != "update":
        raise ReshapeError(f"the draft action is {draft.action}, not update")
    if draft.target is None:
        raise ReshapeError("the draft has no target issue")
    if draft.target.number != args.issue or draft.target.repository.casefold() != args.repo.casefold():
        raise ReshapeError(
            f"the draft is for {draft.target.repository}#{draft.target.number}, not {args.repo}#{args.issue}"
        )
    if draft.repository is not None and draft.repository.casefold() != args.repo.casefold():
        raise ReshapeError(f"the draft repository is {draft.repository}, not {args.repo}")
    if draft.expected is None:
        raise ReshapeError("the draft has no expected state; an update draft is required")
    snapshot_sha = _sha256_text(original)
    expected_sha = draft.expected.body_sha256.casefold()
    if _SHA256.fullmatch(expected_sha) is None:
        raise ReshapeError("the draft expected.body_sha256 is not a SHA-256")
    if expected_sha != snapshot_sha:
        raise _Stop(
            {
                "status": "expected_mismatch",
                "repository": args.repo,
                "issue": args.issue,
                "snapshot_body_sha256": snapshot_sha,
                "expected_body_sha256": expected_sha,
            }
        )
    if len(draft.body) > fmt.BODY_LIMIT:
        raise _Stop(
            {
                "status": "too_large",
                "repository": args.repo,
                "issue": args.issue,
                "body_length": len(draft.body),
                "limit": fmt.BODY_LIMIT,
                "remaining": fmt.BODY_LIMIT - len(draft.body),
            }
        )
    report = verify_body(original, draft.body)
    if not report.ok:
        raise _Stop(
            {
                "status": "preservation_failed",
                "repository": args.repo,
                "issue": args.issue,
                "preservation": report.as_dict(),
            }
        )
    composed = prepare_body(draft.body)
    diff = _unified_diff(
        _without_span(original, prepared.archive_span),
        _without_span(draft.body, composed.archive_span),
        fromfile="元の本文（archiveを除く）",
        tofile="draftの本文（archiveを除く）",
    )
    directory = _out_dir(args.out_dir)
    body_path = _write_text(directory, "body.md", draft.body)
    diff_path = _write_text(directory, "diff.patch", diff)
    report_path = _write_json(directory, "preservation.json", report.as_dict())
    return {
        "status": "verified",
        "repository": args.repo,
        "issue": args.issue,
        "draft": str(draft_path),
        "draft_sha256": hashlib.sha256(raw).hexdigest(),
        "draft_body_sha256": _sha256_text(draft.body),
        "expected_body_sha256": expected_sha,
        "snapshot_body_sha256": snapshot_sha,
        "body": str(body_path),
        "diff": str(diff_path),
        "preservation": str(report_path),
        "preservation_report": report.as_dict(),
        "metadata": composed.metadata is not None,
    }


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        sys.stderr.write(f"reshape_issue: {message}\n")
        raise SystemExit(2)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="reshape_issue.py", description="Issue の本文を管理対象を保って整形する")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="本文をスロットと管理対象に分ける")
    prepare.add_argument("--repo", required=True, metavar="OWNER/NAME")
    prepare.add_argument("--issue", required=True, type=int)
    prepare.add_argument("--read-json", required=True, metavar="PATH")
    prepare.add_argument("--out-dir", required=True, metavar="DIR")
    build = commands.add_parser("build", help="編集したスロットを組み立てる")
    build.add_argument("--repo", required=True, metavar="OWNER/NAME")
    build.add_argument("--issue", required=True, type=int)
    build.add_argument("--read-json", required=True, metavar="PATH")
    build.add_argument("--segments-file", required=True, metavar="PATH")
    build.add_argument("--out-dir", required=True, metavar="DIR")
    verify = commands.add_parser("verify", help="draft の本文を検査する")
    verify.add_argument("--repo", required=True, metavar="OWNER/NAME")
    verify.add_argument("--issue", required=True, type=int)
    verify.add_argument("--read-json", required=True, metavar="PATH")
    verify.add_argument("--draft", required=True, metavar="DIR")
    verify.add_argument("--out-dir", required=True, metavar="DIR")
    return parser


def _dispatch(args: argparse.Namespace) -> dict[str, object]:
    if args.command == "prepare":
        return _prepare(args)
    if args.command == "build":
        return _build(args)
    return _verify(args)


def _print_json(data: object) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as requested:
        return requested.code if isinstance(requested.code, int) else 0
    try:
        result = _dispatch(args)
    except _Stop as stop:
        _print_json(stop.result)
        return 1
    except (ReshapeError, fmt.FormatError, OSError, UnicodeError) as error:
        sys.stderr.write(f"reshape_issue: {error}\n")
        return 2
    _print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
