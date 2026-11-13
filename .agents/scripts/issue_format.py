"""Issue の共有書式（``.agents/issue-format.md``）のモデルと機械可読ブロックの読み書き。

スキルの helper は ``importlib.util.spec_from_file_location`` で読み込める
（読み込む側は ``sys.modules`` に登録してから実行する）。対象確認には共通 resolver を使う。

- モデル: ``IssueMetadata``（本文）・``RunRecord``（実行記録コメント）・``Evaluation``（評価コメント）
- ブロック: HTML コメントに入れた JSON。JSON の中の ``<`` と ``>`` を ``\\u003c``・``\\u003e`` の 6 文字に
  置き換えて書き、値に ``-->`` があってもコメントが途中で閉じないようにする
- 書き込み（``write_metadata``・``compose_comment``）は、組み立てた本文を読み戻して同じ値にならなければ
  ``FormatError`` で止める。投稿は取り消せないので、投稿の前のガードとして働く
- 整形前の本文の保存（``wrap_original``・``unwrap_original``）
- 規則の読み込み（``load_rules``・``missing_labels``）: 節とラベルの定義は ``.agents/issue-format.md``
  の表から読み、Python に写さない
- 本文・ラベル・タイトルの検査（``check_issue``）と CLI（``main``）

行の走査（``scan_lines``）は、コードブロックの囲みの中の行をブロックの候補にも見出しにもしない。
CRLF の本文は、各行の末尾の CR を外して判定する（``unwrap_original`` だけは CR を落とさずに返す）。

書式は ``root/.agents/issue-format.md`` から読む。対象確認は検証済みの常設親と対象 checkout を読む。
"""

import argparse
import importlib.util
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, Self, cast

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

ROOT = Path(__file__).resolve().parents[2]


def _load_helper(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


agent_tmp = _load_helper("_issue_format_agent_tmp", ROOT / ".agents/scripts/agent_tmp.py")
context = _load_helper("_issue_format_context", ROOT / "scripts/superpowers_context.py")
BODY_LIMIT = 65536
REQUIRED_FAMILIES = ("type", "area", "priority", "size", "source")
ORIGINAL_INFO = "issue-format-original"
MANAGED_ORIGINAL_INFO = "issue-format-original-managed-v1"
_ARCHIVE_INFOS = frozenset({ORIGINAL_INFO, MANAGED_ORIGINAL_INFO})

# JSON の文字列の中の < と > を置き換える 6 文字（バックスラッシュ・u・4 桁の 16 進）
_LT_ESCAPE = "\\u003c"
_GT_ESCAPE = "\\u003e"


class FormatError(ValueError):
    """書き込み・入力の拒否。``problems`` に理由をすべて持つ。"""

    def __init__(self, problems: str | Iterable[str]) -> None:
        self.problems: tuple[str, ...] = (problems,) if isinstance(problems, str) else tuple(problems)
        super().__init__("; ".join(self.problems))


# ---------------------------------------------------------------------------
# モデル（Spec 3.5〜3.7 節）
# ---------------------------------------------------------------------------


def _reject_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


# 空にできない文字列。改行・非 ASCII は許し、空白だけは拒否する
Text = Annotated[str, StringConstraints(min_length=1), AfterValidator(_reject_blank)]
Repository = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")]
Sha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Url = Annotated[str, StringConstraints(pattern=r"^https?://\S+$")]
Hours = Annotated[float, Field(ge=0, allow_inf_nan=False)]
PositiveHours = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Minutes = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class BaseRef(_Strict):
    """起票時の base（リポジトリ・branch・commit）。"""

    repository: Repository
    branch: Text
    sha: Sha


class Estimate(_Strict):
    """能動時間の見積もり。"""

    hours_low: Hours
    hours_high: PositiveHours
    confidence: Literal["high", "medium", "low"]
    uncertainties: tuple[Text, ...]

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.hours_low > self.hours_high:
            raise ValueError("hours_low must not exceed hours_high")
        if self.confidence != "high" and not self.uncertainties:
            raise ValueError("uncertainties are required unless confidence is high")
        return self


class Baseline(_Strict):
    """改善前の状態（基準値）の 1 指標。"""

    metric: Text
    value: Text
    source: Text
    measured_on: date | None


class Target(_Strict):
    """目標値と評価方法の 1 指標。"""

    metric: Text
    target: Text
    method: Text
    timing: Text
    due: date | None


class Discovery(_Strict):
    """起票の契機（発見経路のリンクとメモ）。"""

    links: tuple[Url, ...]
    note: Text | None


class Undetermined(_Strict):
    """起票の時点で決められない項目。"""

    item: Literal["type", "area", "priority", "size", "source", "estimate"]
    reason: Text
    how_to_decide: Text


class IssueRef(_Strict):
    """記録の対象の Issue。"""

    repository: Repository
    number: Annotated[int, Field(ge=1)]


class TaskTime(_Strict):
    """主要 Task 別の所要時間（分）。"""

    name: Text
    minutes: Minutes


class Stop(_Strict):
    """run の停止。``expected`` は想定された停止、``unexpected`` は予期しない障害。"""

    reason: Text
    kind: Literal["expected", "unexpected"]


class EvaluationResult(_Strict):
    """評価の 1 指標。``achieved`` は判定できないとき ``None``。"""

    metric: Text
    target: Text
    actual: Text
    achieved: bool | None
    gap: Text


class IssueMetadata(_Strict):
    """Issue の本文に置く機械可読ブロック（``issue-format:metadata:v1``）。"""

    filed_on: date
    bases: Annotated[tuple[BaseRef, ...], Field(min_length=1)]
    estimate: Estimate | None
    baselines: tuple[Baseline, ...]
    targets: tuple[Target, ...]
    discovery: Discovery
    title_language: Literal["ja", "en"] = "ja"
    undetermined: tuple[Undetermined, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> Self:
        items = [entry.item for entry in self.undetermined]
        if len(set(items)) != len(items):
            raise ValueError("undetermined items must be unique")
        if (self.estimate is None) != ("estimate" in items):
            raise ValueError("estimate must be null exactly when it is listed in undetermined")
        return self


class RunRecord(_Strict):
    """実行記録コメントのブロック（``issue-format:run-record:v1``）。"""

    issue: IssueRef
    skill: Text
    session: Text | None
    runtime: Text
    model: Text
    started_at: AwareDatetime
    ended_at: AwareDatetime
    outcome: Literal["pr_created", "merged", "stopped"]
    active_minutes: Minutes
    user_wait_minutes: Minutes
    tasks: tuple[TaskTime, ...]
    actual_size: Literal["XS", "S", "M", "L", "XL"]
    stops: tuple[Stop, ...]
    resumes: Annotated[int, Field(ge=0)]
    review_cycles: Annotated[int, Field(ge=0)] | None
    pr: Url | None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.ended_at < self.started_at:
            raise ValueError("ended_at must not be earlier than started_at")
        if self.outcome == "stopped" and not self.stops:
            raise ValueError("stops are required when outcome is stopped")
        if self.outcome in ("pr_created", "merged") and self.pr is None:
            raise ValueError("pr is required when outcome is pr_created or merged")
        return self


class Evaluation(_Strict):
    """評価コメントのブロック（``issue-format:evaluation:v1``）。"""

    issue: IssueRef
    evaluated_at: AwareDatetime
    runtime: Text
    model: Text
    scope: Text
    results: Annotated[tuple[EvaluationResult, ...], Field(min_length=1)]
    notes: Text | None


BlockValue = IssueMetadata | RunRecord | Evaluation

# 種類と版に対応するモデル。古い版のモデルは残し、古い版のブロックも読めるようにする
KINDS: dict[str, dict[int, type[BaseModel]]] = {
    "metadata": {1: IssueMetadata},
    "run-record": {1: RunRecord},
    "evaluation": {1: Evaluation},
}

# モデルから、書き込む種類と版を引く
_KEY_OF: dict[type[BaseModel], tuple[str, int]] = {
    model: (kind, version) for kind, versions in KINDS.items() for version, model in versions.items()
}


# ---------------------------------------------------------------------------
# 行の走査（Spec 4.2 節）
# ---------------------------------------------------------------------------

# 囲みの開始の行。リスト項目の中の囲みは、リスト記号（`-`・`*`・`+`、1〜9 桁の数字に `.` か `)`）と
# 空白 1〜4 個の直後に、囲みが続く（空白が 5 個以上なら、CommonMark ではインデントのコードブロックになる）。
# タブは ``_scan`` が展開してから照合する
_FENCE_OPEN = re.compile(
    r"^(?P<indent> {0,3})(?P<markers>(?:(?:[-*+]|[0-9]{1,9}[.)]) {1,4})*)(?P<fence>`{3,}|~{3,})(?P<rest>.*)$"
)
# 囲みの閉じの行。行頭の空白の数は、``_scan`` が囲みの内容の位置と照らす
_FENCE_CLOSE = re.compile(r"^(?P<indent> *)(?P<fence>`{3,}|~{3,})[ \t]*$")
_TAB_WIDTH = 4
_CANDIDATE = re.compile(r"^ {0,3}<!-- issue-format:")
# 版は 9 桁までにする（桁数の多い数字は int への変換が ValueError になるので、1 行目の形の誤りとして扱う）
_HEADER = re.compile(r"<!-- issue-format:(?P<kind>[a-z][a-z-]*):v(?P<version>[1-9][0-9]{0,8})")
# HTML がコメントの終わりと扱う並び
_COMMENT_END = re.compile(r"-->|--!>")


@dataclass(frozen=True)
class ScannedLine:
    """本文の 1 行。``text`` は末尾の CR を外したもの、``raw`` は元の行、``number`` は 1 から数える。"""

    text: str
    raw: str
    number: int
    start: int  # 本文の中の開始位置
    in_fence: bool  # コードブロックの囲みの行と、その中の行


@dataclass(frozen=True)
class _Fence:
    """コードブロック 1 つ。添字は ``scan_lines`` の返した一覧の位置（0 から数える）。"""

    open_index: int
    close_index: int | None  # 閉じが無い囲みは、本文の終わりか、リスト項目が終わる行の手前まで
    info: str


def _scan(text: str) -> tuple[list[ScannedLine], list[_Fence]]:
    """行ごとにコードブロックの内外を決める。CommonMark に合わせ、リスト項目の中の囲みも囲みとして扱う。

    リスト記号の後の囲み（リスト項目の行から始まる囲み）は、囲みの内容の位置（開始の行で囲みの文字が始まる列）を覚える。
    閉じは、その位置から 3 列以内に字下げした行である。内容の位置より字下げの少ない空行でない行は、
    リスト項目の終わりなので、囲みはその行の前で閉じの無いまま終わり、その行を囲みの外の行として開きから判定し直す。
    引用（``>``）の中の囲みは追わない。
    """
    lines: list[ScannedLine] = []
    fences: list[_Fence] = []
    marker: str | None = None  # 開いている囲みの文字列
    column = 0  # 開いている囲みの内容の位置。リスト項目の中でない囲みは 0
    open_index = 0
    info = ""
    start = 0
    for index, raw in enumerate(text.split("\n")):
        line_text = raw.removesuffix("\r")
        # 字下げの幅と囲みの文字の判定は、タブを展開した行で行う（ScannedLine の text・raw は元の行のまま）
        judged = line_text.expandtabs(_TAB_WIDTH)
        indent = len(judged) - len(judged.lstrip(" "))
        if marker is not None and column > 0 and judged.strip(" ") and indent < column:
            fences.append(_Fence(open_index, None, info))
            marker = None
        in_fence = marker is not None
        if marker is None:
            opened = _FENCE_OPEN.match(judged)
            # backtick の囲みの開始の行は、残りに backtick を含まない
            if opened is not None and not (opened["fence"][0] == "`" and "`" in opened["rest"]):
                marker, open_index, info = opened["fence"], index, opened["rest"].strip()
                column = len(opened["indent"]) + len(opened["markers"]) if opened["markers"] else 0
                in_fence = True
        else:
            closed = _FENCE_CLOSE.match(judged)
            if (
                closed is not None
                and closed["fence"][0] == marker[0]
                and len(closed["fence"]) >= len(marker)
                and column <= len(closed["indent"]) <= column + 3
            ):
                fences.append(_Fence(open_index, index, info))
                marker = None
        lines.append(ScannedLine(line_text, raw, index + 1, start, in_fence))
        start += len(raw) + 1
    if marker is not None:
        fences.append(_Fence(open_index, None, info))
    return lines, fences


def scan_lines(text: str) -> list[ScannedLine]:
    """本文を LF で分け、各行にコードブロックの内外と位置を付けて返す。"""
    return _scan(text)[0]


def _candidates(lines: list[ScannedLine]) -> list[ScannedLine]:
    return [line for line in lines if not line.in_fence and _CANDIDATE.match(line.text)]


def block_candidates(text: str) -> list[ScannedLine]:
    """コードブロックの外で、行頭の空白 0〜3 個の後に ``<!-- issue-format:`` が来る行。"""
    return _candidates(scan_lines(text))


# ---------------------------------------------------------------------------
# 描画・取り出し（Spec 4.2 節）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Extracted:
    """``extract_block`` の結果。``line`` はブロックの 1 行目、``end_line`` は ``-->`` の行（1 から数える）。"""

    status: Literal["ok", "missing", "broken", "unknown_version"]
    kind: str
    version: int | None
    value: BaseModel | None  # status が ok のときだけ
    reason: str | None  # status が broken・unknown_version のとき
    line: int | None
    end_line: int | None


def _failed(
    status: Literal["broken", "unknown_version"],
    kind: str,
    reason: str,
    *,
    version: int | None = None,
    line: int | None = None,
    end_line: int | None = None,
) -> Extracted:
    return Extracted(status, kind, version, None, reason, line, end_line)


def _describe(error: ValidationError) -> str:
    """pydantic の誤りの場所（loc）と要旨を ``; `` でつなぐ。"""
    parts: list[str] = []
    for detail in error.errors(include_url=False, include_context=False, include_input=False):
        place = ".".join(str(item) for item in detail["loc"])
        parts.append(f"{place}: {detail['msg']}" if place else detail["msg"])
    return "; ".join(parts)


def extract_block(text: str, kind: str) -> Extracted:
    """本文かコメントから、指定した種類のブロックを取り出す。

    定義に無い種類（``KINDS`` に無い ``kind``）を渡すと ``FormatError`` を出す。
    """
    if kind not in KINDS:
        raise FormatError("The block kind is not defined.")
    lines = scan_lines(text)

    headers: list[tuple[ScannedLine, str, int]] = []
    for candidate in _candidates(lines):
        header = _HEADER.fullmatch(candidate.text)
        if header is None:
            # 種類が分からないので、指定した種類を問わず壊れたものとして返す
            return _failed(
                "broken", kind, "The first line of a block does not match the expected form.", line=candidate.number
            )
        headers.append((candidate, header["kind"], int(header["version"])))
    matching = [entry for entry in headers if entry[1] == kind]
    if not matching:
        return Extracted("missing", kind, None, None, None, None, None)
    if len(matching) > 1:
        return _failed(
            "broken", kind, "The text contains more than one block of the same kind.", line=matching[1][0].number
        )
    first, _, version = matching[0]

    # 1 行目の次の文字から、最初に出る --> か --!> を探す。それがブロックの最後の行（--> だけの行）でなければ、
    # HTML のコメントが途中で閉じる
    closing = _COMMENT_END.search(text, first.start + len(first.raw) + 1)
    if closing is None:
        return _failed("broken", kind, "The block is not closed by a --> line.", version=version, line=first.number)
    last = next((line for line in lines if line.start == closing.start()), None)
    if last is None or last.text != "-->":
        return _failed(
            "broken",
            kind,
            "The first comment terminator is not on a line that contains only -->.",
            version=version,
            line=first.number,
        )

    model = KINDS[kind].get(version)
    if model is None:
        return _failed(
            "unknown_version",
            kind,
            f"Version {version} is not supported.",
            version=version,
            line=first.number,
            end_line=last.number,
        )
    content = "\n".join(line.text for line in lines[first.number : last.number - 1])
    try:
        value = model.model_validate_json(content)
    except ValidationError as error:
        return _failed("broken", kind, _describe(error), version=version, line=first.number, end_line=last.number)
    except UnicodeError:
        return _failed(
            "broken",
            kind,
            "The block contains text that cannot be encoded as UTF-8.",
            version=version,
            line=first.number,
            end_line=last.number,
        )
    return Extracted("ok", kind, version, value, None, first.number, last.number)


def _cause(extracted: Extracted, default: str) -> str:
    """``Extracted.reason`` を、括弧に入れて 1 文に収められる形（末尾のピリオドを除く）にする。"""
    return (extracted.reason or default).rstrip(".")


def render_block(value: BlockValue) -> str:
    """ブロックを描画する。描画した文字列を読み戻し、同じ値にならなければ ``FormatError``。"""
    kind, version = _KEY_OF[type(value)]
    payload = json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2)
    # JSON の構文の文字に < と > は無いので、置き換えるのは文字列の中だけ。読み戻すと元の文字に戻る
    payload = payload.replace("<", _LT_ESCAPE).replace(">", _GT_ESCAPE)
    block = "\n".join([f"<!-- issue-format:{kind}:v{version}", payload, "-->"])
    try:
        block.encode("utf-8")
    except UnicodeEncodeError:
        raise FormatError("The block contains text that cannot be encoded as UTF-8.") from None
    extracted = extract_block(block, kind)
    if extracted.status != "ok" or extracted.value != value:
        cause = _cause(extracted, "the value changed")
        raise FormatError(f"The rendered {kind} block does not read back as the same value ({cause}).")
    return block


# ---------------------------------------------------------------------------
# 書き込み（Spec 4.2 節。取り消せない投稿の前のガード）
# ---------------------------------------------------------------------------


def _check_posted(text: str, kind: str, value: BlockValue) -> None:
    """投稿する文字列が、UTF-8 にでき、上限に収まり、読み戻して同じ値になることを確かめる。"""
    problems: list[str] = []
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        problems.append("The text contains characters that cannot be encoded as UTF-8.")
    if len(text) > BODY_LIMIT:
        problems.append(f"The text exceeds the {BODY_LIMIT} character limit.")
    extracted = extract_block(text, kind)
    if extracted.status != "ok" or extracted.value != value:
        cause = _cause(extracted, "the value changed or the block is not visible")
        problems.append(f"The {kind} block does not read back as the same value ({cause}).")
    if problems:
        raise FormatError(problems)


def write_metadata(body: str, metadata: IssueMetadata) -> str:
    """本文の ``metadata`` ブロックを書き込む。既存のブロックはその位置で置き換え、無ければ末尾に足す。"""
    existing = extract_block(body, "metadata")
    if existing.status in ("broken", "unknown_version"):
        raise FormatError(f"Refusing to overwrite an unreadable metadata block ({_cause(existing, 'unreadable')}).")
    for candidate in block_candidates(body):
        header = _HEADER.fullmatch(candidate.text)
        if header is not None and header["kind"] in ("run-record", "evaluation"):
            raise FormatError("The issue body must not contain a run-record or evaluation block.")

    block = render_block(metadata)
    if existing.status == "ok":
        if existing.line is None or existing.end_line is None:
            raise FormatError("The existing metadata block has no position.")
        lines = scan_lines(body)
        first = lines[existing.line - 1]
        last = lines[existing.end_line - 1]
        # 最後の行の CR は残す（本文の改行の形を変えない）
        written = body[: first.start] + block + body[last.start + len(last.text) :]
    else:
        stripped = body.rstrip()
        # 最終内容行の行末（CRLF か LF）を保ち、末尾の空行だけを畳む。末尾改行が無ければ従来どおり LF で区切る
        ending = "\r\n" if body[len(stripped) :].startswith("\r\n") else "\n"
        written = f"{stripped}{ending}\n{block}" if stripped else block
    _check_posted(written, "metadata", metadata)
    return written


def compose_comment(text: str, record: RunRecord | Evaluation) -> str:
    """コメントの本文（人が読む文）の後に、空行を挟んで ``run-record``・``evaluation`` のブロックを足す。"""
    if block_candidates(text):
        raise FormatError("The comment text must not contain a line that starts an issue-format block.")
    kind, _ = _KEY_OF[type(record)]
    block = render_block(record)
    stripped = text.rstrip()
    composed = f"{stripped}\n\n{block}" if stripped else block
    _check_posted(composed, kind, record)
    return composed


# ---------------------------------------------------------------------------
# 整形前の本文の保存（Spec 3.3 節・4.2 節）
# ---------------------------------------------------------------------------


def wrap_original(original: str, *, summary: str, info: str = ORIGINAL_INFO) -> str:
    """元の本文を backtick の囲みに入れ、``<details>`` に置く。

    ``info`` は ``ORIGINAL_INFO`` または ``MANAGED_ORIGINAL_INFO``。既定は旧形式で、既存の呼び出しは変わらない。
    """
    if info not in _ARCHIVE_INFOS:
        raise FormatError("The original-body info string is not defined.")
    if any(char in summary for char in "\n\r<>"):
        raise FormatError("The summary must not contain line breaks, '<' or '>'.")
    # 元の本文の中の囲みで閉じないように、元の本文の最長の backtick の並びより長くする
    longest = max((len(run.group()) for run in re.finditer(r"`+", original)), default=0)
    fence = "`" * max(3, longest + 1)
    wrapped = "\n".join(
        [f"<details><summary>{summary}</summary>", "", f"{fence}{info}", original, fence, "", "</details>"]
    )
    if unwrap_original(wrapped, info=info) != original:
        raise FormatError("The wrapped original body does not read back unchanged.")
    return wrapped


def unwrap_original(body: str, *, info: str = ORIGINAL_INFO) -> str | None:
    """``wrap_original`` の囲みから中身を返す（CR を落とさない）。指定した info の囲みが無ければ ``None``。

    ``info`` の既定は旧形式。既存の呼び出しは変わらない。
    """
    if info not in _ARCHIVE_INFOS:
        raise FormatError("The original-body info string is not defined.")
    lines, fences = _scan(body)
    found = [fence for fence in fences if fence.info == info]
    if not found:
        return None
    if len(found) > 1:
        raise FormatError("The body contains more than one original-body fence.")
    fence = found[0]
    if fence.close_index is None:
        raise FormatError("The original-body fence is not closed.")
    # 開きの行の次の行の先頭から、閉じの行の直前の LF の手前まで。内容の無い囲みは空文字になる
    start = lines[fence.open_index + 1].start
    end = lines[fence.close_index].start - 1
    return body[start:end]


# ---------------------------------------------------------------------------
# 規則の読み込み（Spec 4.3 節）
# ---------------------------------------------------------------------------

_LABEL_FAMILIES = (*REQUIRED_FAMILIES, "triage")
_FAMILY_PATTERN = "|".join(_LABEL_FAMILIES)
_DESCRIPTION_LIMIT = 100  # GitHub のラベルの説明の上限
# 表の 1 列目。節は `## 見出し`、ラベルは `系統: 値`（どちらも backtick で囲む）
_SECTION_CELL = re.compile(r"^`## (?P<heading>[^`]+)`$")
_LABEL_CELL = re.compile(rf"^`(?P<family>{_FAMILY_PATTERN}): (?P<value>[^\s`](?:[^`]*[^\s`])?)`$")
# ラベルの名前のつもりで書いたが、形が合わない 1 列目（黙って読み飛ばさず、定義の誤りにする）
_LABEL_LIKE_CELL = re.compile(rf"^`(?:{_FAMILY_PATTERN}):")
_COLOR_CELL = re.compile(r"^`(?P<color>[0-9A-Fa-f]{6})`$")
# 定義の行のセルの数。節の表は「見出し・必須か任意・書く内容・対応する metadata 配列」の 4 列、
# ラベルの表は「ラベル・色・説明」の 3 列
_SECTION_CELLS = 4
_LABEL_CELLS = 3
_METADATA_KEYS = ("baselines", "targets")
_METADATA_NONE = "—"
_METADATA_CELL = re.compile(r"^`(?P<key>[^`]+)`$")


@dataclass(frozen=True)
class LabelDefinition:
    """ラベルの定義 1 件。``color`` は ``#`` の無い 6 桁の 16 進（小文字）。"""

    name: str  # 例: "type: bug"
    family: str  # type・area・priority・size・source・triage
    value: str  # 例: "bug"
    color: str
    description: str


@dataclass(frozen=True)
class SectionRule:
    """本文の節の定義。``heading`` は ``## `` を除いた見出し。

    ``metadata_key`` は、その節の内容を入れる ``IssueMetadata`` の配列。対応しない節は ``None``。
    """

    heading: str
    required: bool
    metadata_key: Literal["baselines", "targets"] | None = None


@dataclass(frozen=True)
class Rules:
    """リポジトリごとの規則。``name`` は説明用の repo 名。"""

    repository: str
    name: str
    sections: tuple[SectionRule, ...]  # 表の順
    labels: tuple[LabelDefinition, ...]  # 系統の順（``REQUIRED_FAMILIES``・``triage``）、系統の中は表の順


def _mapping(value: object) -> Mapping[str, object] | None:
    """JSON・TOML の object（辞書）なら、キーを文字列とみなして返す。"""
    return cast("dict[str, object]", value) if isinstance(value, dict) else None


def _sequence(value: object) -> list[object] | None:
    """JSON の配列なら返す。"""
    return cast("list[object]", value) if isinstance(value, list) else None


def _read_text(path: Path) -> str:
    """ファイルを UTF-8 で読む。改行を変換しない（CRLF の本文を、そのまま検査するため）。"""
    return path.read_bytes().decode("utf-8")


def _registration(repository: str) -> tuple[str, str]:
    """常設親と共通 resolver で対象を確認する。任意の checkout は受け付けない。"""
    try:
        # URL を受け入れる resolver と違い、この API は owner/repo のみ受ける。
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repository):
            raise context.ContextError("repository must be owner/repo")
        registered = context.parse_repository(repository)
        parent = agent_tmp.resolve_main_root(ROOT)
        kwargs = {}
        if registered == "usaturn/resoloop-meshy":
            fixed = parent / "external" / "resoloop-meshy"
            if not fixed.is_dir():
                raise context.ContextError("resoloop-meshy checkout is missing; run bash scripts/resoloop-meshy.sh clone first")
            if fixed.resolve(strict=True) != fixed:
                raise context.ContextError("resoloop-meshy must be the fixed checkout, not a symlink")
            checkout = context.inspect_checkout(fixed, label="resoloop-meshy", require_main=True)
            if checkout.common_dir != fixed / ".git" or context._remote_repository(checkout, "origin") != registered:
                raise context.ContextError("resoloop-meshy fixed checkout origin or identity does not match")
            kwargs["code_root"] = fixed
        resolved = context.resolve_context("review-workspace", parent_root=parent, repo=registered, **kwargs)
        if registered == "usaturn/resoloop-meshy" and resolved["code_root"] != str(fixed):
            raise context.ContextError("resoloop-meshy resolved to a different checkout")
        return registered.rpartition("/")[2], registered
    except (agent_tmp.AgentTmpError, context.ContextError, OSError, ValueError) as error:
        raise FormatError(f"Repository resolution failed: {error}") from None


def _table_rows(path: Path) -> list[list[str]]:
    """Markdown の表の行（``|`` で始まり ``|`` で終わる行）を、前後の空白を落としたセルに分ける。

    コードブロックの中の表は読まない。行は ``|`` で単純に分けるので、節・ラベルの定義の行
    （1 列目が `` `## …` `` か `` `<系統>: …` `` で始まる行）にセルの ``|`` があると、セルの境界がずれる
    （``\\|`` と書いても同じ）。余ったセルは読み捨てられ、ラベルの説明などが黙って切れる。
    1 列目の ``|`` は、定義の行を黙って読み飛ばす。
    そのため、定義の行は、末尾が ``|`` で、節はちょうど 4 セル、ラベルはちょうど 3 セルのものだけを受け付け、
    それ以外は ``FormatError`` にする。
    """
    try:
        text = _read_text(path)
    except OSError, UnicodeError:
        raise FormatError(f"The rules file {path.name} cannot be read.") from None
    rows: list[list[str]] = []
    for line in scan_lines(text):
        stripped = line.text.strip()
        if line.in_fence or not stripped.startswith("|"):
            continue
        closed = stripped.endswith("|")
        cells = [cell.strip() for cell in stripped[1 : -1 if closed else None].split("|")]
        if cells[0].startswith("`## "):
            expected_cells = _SECTION_CELLS
        elif _LABEL_LIKE_CELL.match(cells[0]) is not None:
            expected_cells = _LABEL_CELLS
        else:
            expected_cells = None
        if expected_cells is not None:
            if not closed:
                raise FormatError(f"The definition row {cells[0]} in {path.name} does not end with a pipe.")
            if "\\|" in stripped:
                raise FormatError(f"The definition row {cells[0]} in {path.name} contains an escaped pipe (\\|).")
            if len(cells) != expected_cells:
                raise FormatError(
                    f"The definition row {cells[0]} in {path.name} must have exactly {expected_cells} cells."
                )
        rows.append(cells)
    return rows


def _parse_metadata_key(cell: str, heading: str) -> Literal["baselines", "targets"] | None:
    """節の表の 4 列目を読む。対応しない節は ``—`` か空、対応する節は配列名（backtick は任意）。"""
    if cell in ("", _METADATA_NONE):
        return None
    if cell in _METADATA_KEYS:
        return cell
    matched = _METADATA_CELL.fullmatch(cell)
    if matched is not None and matched["key"] in _METADATA_KEYS:
        return cast("Literal['baselines', 'targets']", matched["key"])
    raise FormatError(f"The section row '## {heading}' has an unknown metadata array in its fourth column: {cell!r}.")


def _parse_sections(rows: list[list[str]]) -> tuple[SectionRule, ...]:
    rules: list[SectionRule] = []
    for cells in rows:
        matched = _SECTION_CELL.match(cells[0])
        if matched is None:
            if cells[0].startswith("`## "):
                raise FormatError(f"The section cell {cells[0]} is not written as `## <heading>`.")
            continue
        heading = matched["heading"]
        mark = cells[1]  # _table_rows が、定義の行のセルは 4 つと確かめている
        if mark not in ("必須", "任意"):
            raise FormatError(
                f"The section row '## {heading}' is not marked required or optional in its second column."
            )
        metadata_key = _parse_metadata_key(cells[3], heading)
        if metadata_key is not None and mark != "必須":
            raise FormatError(f"The section row '## {heading}' maps {metadata_key} but is not required.")
        if any(rule.heading == heading for rule in rules):
            raise FormatError(f"The section table lists '## {heading}' more than once.")
        rules.append(SectionRule(heading, mark == "必須", metadata_key))
    if not any(rule.required for rule in rules):
        raise FormatError("The section table defines no required section.")
    for key in _METADATA_KEYS:
        if sum(rule.metadata_key == key for rule in rules) != 1:
            raise FormatError(f"The section table must map exactly one required section to {key}.")
    return tuple(rules)


def _parse_labels(rows: list[list[str]]) -> list[LabelDefinition]:
    found: list[LabelDefinition] = []
    for cells in rows:
        matched = _LABEL_CELL.match(cells[0])
        if matched is None:
            if _LABEL_LIKE_CELL.match(cells[0]):
                raise FormatError(f"The label cell {cells[0]} is not written as `<family>: <value>`.")
            continue
        name = f"{matched['family']}: {matched['value']}"
        color = _COLOR_CELL.match(cells[1])  # _table_rows が、定義の行のセルは 3 つと確かめている
        if color is None:
            raise FormatError(f"The label '{name}' has no 6-digit hexadecimal color in its second column.")
        description = cells[2]
        if not description or len(description) > _DESCRIPTION_LIMIT:
            raise FormatError(f"The label '{name}' needs a description of 1 to {_DESCRIPTION_LIMIT} characters.")
        found.append(LabelDefinition(name, matched["family"], matched["value"], color["color"].lower(), description))
    return found


def load_rules(repository: str, *, root: Path = ROOT) -> Rules:
    """対象を検証し、``root`` の共有書式から規則を読む。``root`` は台帳の親ではない。"""
    name, registered = _registration(repository)
    format_rows = _table_rows(root / ".agents" / "issue-format.md")
    sections = _parse_sections(format_rows)
    labels = _parse_labels(format_rows)
    labels.sort(key=lambda label: _LABEL_FAMILIES.index(label.family))

    for family in _LABEL_FAMILIES:
        if not any(label.family == family for label in labels):
            raise FormatError(f"No {family}: label is defined for {registered}.")
    if sum(label.family == "triage" for label in labels) != 1:
        raise FormatError("Exactly one triage: label must be defined.")
    names = [label.name.casefold() for label in labels]
    if len(set(names)) != len(names):
        raise FormatError(f"A label is defined more than once for {registered}.")
    return Rules(registered, name, sections, tuple(labels))


def missing_labels(rules: Rules, existing: Iterable[str]) -> list[LabelDefinition]:
    """定義にあって ``existing`` に無いラベルを、定義の順で返す。名前は大文字・小文字を区別せずに比べる。"""
    present = {name.casefold() for name in existing}
    return [label for label in rules.labels if label.name.casefold() not in present]


# ---------------------------------------------------------------------------
# 本文・ラベル・タイトルの検査（Spec 4.4 節）
# ---------------------------------------------------------------------------

_BOARD_START = re.compile(r"^<!-- planning-parallel-issues:(?P<name>.+):start -->$")
_COMMENT_OPEN = re.compile(r"^ {0,3}<!--")
# wrap_original が囲みの前後に付ける行（summary に < と > は入らない）
_DETAILS_OPEN = re.compile(r"^<details><summary>[^<>]*</summary>$")
_DETAILS_CLOSE = "</details>"
_HEADING = re.compile(r"^## (?P<heading>.+?)(?:\s+#+)?\s*$")
# 節の終わりになる見出し（レベル 1 と 2）
_SECTION_END = re.compile(r"^#{1,2}(?:[ \t]|$)")
_TITLE_PREFIX = re.compile(r"^\s*(?:\[[^\]]*\]|[A-Za-z][A-Za-z0-9_.-]*:)")
# ひらがな・カタカナ・CJK 統合漢字の拡張 A と基本
_JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
_SINGLE_FAMILIES = ("type", "priority", "size", "source", "triage")


@dataclass(frozen=True)
class Problem:
    """検査の問題 1 件。``code`` は後続のスキルが処理を分けるための安定した識別子。"""

    code: str
    where: str  # 例: "section:概要"・"label:priority"・"block"・"title"
    message: str  # 英語の 1 文


@dataclass(frozen=True)
class CheckResult:
    """``check_issue`` の結果。``undetermined`` は、未確定として宣言され、まだ決まっていない項目。"""

    problems: tuple[Problem, ...]
    undetermined: tuple[str, ...]
    metadata: Extracted

    @property
    def complete(self) -> bool:
        """問題も未確定の項目も無いときだけ真。"""
        return not self.problems and not self.undetermined


def _closing_number(lines: list[ScannedLine], opening: ScannedLine) -> int:
    """``opening`` から始まる HTML コメントを閉じる行（最初に ``-->`` を含む行）の番号。無ければ本文の最後の行。"""
    for line in lines[opening.number - 1 :]:
        if "-->" in line.text:
            return line.number
    return lines[-1].number


def _skip_blank(lines: list[ScannedLine], index: int, step: int) -> ScannedLine | None:
    """``index`` の行から ``step`` の向きに、空行を飛ばして最初に現れる行を返す。"""
    while 0 <= index < len(lines):
        if lines[index].text.strip():
            return lines[index]
        index += step
    return None


def _original_wrapper_numbers(lines: list[ScannedLine], fences: list[_Fence]) -> set[int]:
    """``wrap_original`` が旧形式または新形式の囲みの前後に付けた ``<details>`` の行の番号。

    囲みの前後の空行を挟んで隣り合う行だけを数える。この行を内容として数えると、最後の必須の節が空でも、
    整形後の本文では ``section_empty`` にならない。
    """
    numbers: set[int] = set()
    for fence in fences:
        if fence.info not in _ARCHIVE_INFOS:
            continue
        before = _skip_blank(lines, fence.open_index - 1, -1)
        if before is not None and not before.in_fence and _DETAILS_OPEN.match(before.text):
            numbers.add(before.number)
        after = _skip_blank(lines, fence.close_index + 1, 1) if fence.close_index is not None else None
        if after is not None and not after.in_fence and after.text == _DETAILS_CLOSE:
            numbers.add(after.number)
    return numbers


def _excluded_numbers(lines: list[ScannedLine], fences: list[_Fence]) -> set[int]:
    """節の検査で読まない行の番号。

    - コードブロック（旧形式と新形式の archive の囲みを含む）と、その囲みの前後の ``<details>`` の行
    - コードブロックの外の HTML コメント。行頭（空白 0〜3 個）の ``<!--`` から、最初に ``-->`` を含む行まで
      （無ければ本文の終わりまで）。GitHub の画面に出ないので、中の見出しは数えない。機械可読ブロックの範囲も
      この規則に含まれる（壊れたブロックも、表示されない範囲を除く）
    - コードブロックの外の ``planning-parallel-issues`` の管理対象の範囲（入れ子は外側だけ。対応する終わりが
      無い開始は範囲にしない）
    """
    excluded = {line.number for line in lines if line.in_fence}
    excluded |= _original_wrapper_numbers(lines, fences)
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.in_fence and _COMMENT_OPEN.match(line.text):
            closing = _closing_number(lines, line)
            excluded.update(range(line.number, closing + 1))
            index = closing  # 閉じる行の次の行（番号は 1 から、添字は 0 から数える）
        else:
            index += 1
    index = 0
    while index < len(lines):
        line = lines[index]
        started = None if line.in_fence else _BOARD_START.match(line.text)
        if started is not None:
            end_text = f"<!-- planning-parallel-issues:{started['name']}:end -->"
            end_index = next(
                (i for i in range(index + 1, len(lines)) if not lines[i].in_fence and lines[i].text == end_text), None
            )
            if end_index is not None:
                excluded.update(range(line.number, lines[end_index].number + 1))
                index = end_index + 1
                continue
        index += 1
    return excluded


def _reference_pattern(rules: Rules) -> re.Pattern[str] | None:
    """親の節を参照するだけの文の形。見出しは規則の表から作り、Python に写さない。"""
    headings = [re.escape(rule.heading) for rule in rules.sections if rule.metadata_key is not None]
    if not headings:
        return None
    one = "(?:" + "|".join(headings) + ")"
    single = rf"「\s*{one}\s*」"
    inside = rf"「\s*{one}\s*[・と]\s*{one}\s*」"
    outside = rf"{single}\s*[・と]\s*{single}"
    heading = rf"(?:{outside}|{inside}|{single})"
    prefix = r"(?:親\s*(?:Issue\s*)?|Issue\s*)?"
    tail = r"(?:この\s*(?:子|Issue)\s*に固有の指標は(?:無い|ない))"
    pattern = (
        rf"^\s*(?:(?:[-*+]|[0-9]{{1,9}}[.)])\s+)?"
        rf"{prefix}\s*{_REFERENCE_TARGET}"
        rf"(?:\s*の\s*{heading})?\s*を参照する"
        rf"\s*[。.]?\s*(?:{tail}\s*[。.]?\s*)?$"
    )
    return re.compile(pattern)


_NO_METRICS = re.compile(r"^なし\s*。?$")
_NO_METRICS_REASON_START = re.compile(r"^該当なし\s*[（(]")
_ISSUE_NUMBER = r"#\d+"
_REPO_ISSUE = r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+#\d+"
_ISSUE_URL = r"https?://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/issues/\d+"
_REFERENCE_TARGET = (
    rf"(?:\[[^\]\n]*\]\(\s*(?:{_ISSUE_URL}/?|{_REPO_ISSUE}|{_ISSUE_NUMBER})\s*\)"
    rf"|{_ISSUE_URL}/?|{_REPO_ISSUE}|{_ISSUE_NUMBER})"
)


def _is_no_metrics_with_reason(text: str) -> bool:
    """``該当なし（理由）`` だけで、理由の閉じ括弧の後に内容が続かないときだけ真。

    理由の中の括弧は入れ子として数える。閉じ括弧の後に独自指標などが続くときは、節全体の除外にしない。
    """
    start = _NO_METRICS_REASON_START.match(text)
    if start is None:
        return False
    depth = 1
    for index in range(start.end(), len(text)):
        char = text[index]
        if char in "（(":
            depth += 1
        elif char in "）)":
            depth -= 1
            if depth == 0:
                reason = text[start.end() : index]
                rest = text[index + 1 :].strip()
                return bool(reason.strip()) and rest in ("", "。")
    return False


def _allows_empty_metadata(text: str, reference: re.Pattern[str] | None) -> bool:
    """内容のある節が、対応する metadata の配列を空にできる形か。節全体に一致するときだけ真。"""
    if _NO_METRICS.fullmatch(text):
        return True
    if _is_no_metrics_with_reason(text):
        return True
    return reference is not None and reference.fullmatch(text) is not None


def _check_sections(
    lines: list[ScannedLine], fences: list[_Fence], rules: Rules, metadata: Extracted
) -> list[Problem]:
    excluded = _excluded_numbers(lines, fences)
    visible = [line for line in lines if line.number not in excluded]
    positions: dict[str, list[int]] = {}
    for position, line in enumerate(visible):
        matched = _HEADING.match(line.text)
        if matched is not None:
            positions.setdefault(matched["heading"].strip(), []).append(position)

    metric_metadata = metadata.value if metadata.status == "ok" and isinstance(metadata.value, IssueMetadata) else None
    reference = _reference_pattern(rules)
    problems: list[Problem] = []
    latest = -1
    for rule in rules.sections:
        if not rule.required:
            continue  # 任意の節と、表に無い見出しは検査しない
        where = f"section:{rule.heading}"
        found = positions.get(rule.heading, [])
        if not found:
            problems.append(Problem("section_missing", where, f"The required section '## {rule.heading}' is missing."))
            continue
        if len(found) > 1:
            problems.append(
                Problem(
                    "section_duplicate", where, f"The required section '## {rule.heading}' appears more than once."
                )
            )
        if found[0] < latest:
            problems.append(
                Problem("section_order", where, f"The required section '## {rule.heading}' is out of table order.")
            )
        latest = max(latest, found[0])

        content: list[str] = []
        for line in visible[found[0] + 1 :]:
            if _SECTION_END.match(line.text):
                break
            content.append(line.text)
        text = "\n".join(content).strip()
        if not text:
            problems.append(Problem("section_empty", where, f"The required section '## {rule.heading}' is empty."))
        elif text == "該当なし":
            problems.append(
                Problem(
                    "section_no_reason",
                    where,
                    f"The required section '## {rule.heading}' says 該当なし without giving a reason.",
                )
            )
        elif rule.metadata_key is not None and metric_metadata is not None:
            values = metric_metadata.baselines if rule.metadata_key == "baselines" else metric_metadata.targets
            if not values and not _allows_empty_metadata(text, reference):
                problems.append(
                    Problem(
                        "section_metadata_empty",
                        where,
                        f"The section '## {rule.heading}' has content but the metadata array "
                        f"'{rule.metadata_key}' is empty.",
                    )
                )
    return problems


def _family_of(name: str) -> str | None:
    """ラベル名の接頭辞（``type:`` など）が 5 系統か ``triage`` なら、その系統を返す。"""
    if ":" not in name:
        return None
    family = name.split(":", 1)[0].strip().casefold()
    return family if family in _LABEL_FAMILIES else None


def _check_labels(labels: Iterable[str], rules: Rules, metadata: Extracted) -> tuple[list[Problem], tuple[str, ...]]:
    """ラベルを検査する。``(問題, まだ決まっていない未確定の項目)`` を返す。"""
    definitions = {label.name.casefold(): label for label in rules.labels}
    valid: dict[str, list[str]] = {family: [] for family in _LABEL_FAMILIES}
    problems: list[Problem] = []
    seen: set[str] = set()
    for name in labels:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        definition = definitions.get(key)
        if definition is not None:
            valid[definition.family].append(definition.name)
            continue
        family = _family_of(name)
        if family is not None:  # 5 系統と triage の接頭辞を持たないラベル（bug・planning: ready など）は無視する
            message = f"The label '{name}' is not defined for {rules.repository}."
            problems.append(Problem("label_unknown", f"label:{family}", message))

    # 未確定の宣言は、ブロックが読めるときだけ使う（読めなければ、無いラベルはすべて label_missing になる）
    declared: tuple[str, ...] = ()
    if metadata.status == "ok" and isinstance(metadata.value, IssueMetadata):
        declared = tuple(entry.item for entry in metadata.value.undetermined)

    for family in REQUIRED_FAMILIES:
        if not valid[family] and family not in declared:
            message = f"No {family}: label is set and it is not declared as undetermined."
            problems.append(Problem("label_missing", f"label:{family}", message))
    for family in _SINGLE_FAMILIES:
        if len(valid[family]) > 1:
            message = f"More than one {family}: label is set ({', '.join(valid[family])})."
            problems.append(Problem("label_multiple", f"label:{family}", message))
    for item in declared:
        if item != "estimate" and valid[item]:
            message = f"The {item} item is declared as undetermined but a {item}: label is set."
            problems.append(Problem("undetermined_conflict", f"label:{item}", message))
    if declared and not valid["triage"]:
        message = "Items are declared as undetermined but the triage: needed label is not set."
        problems.append(Problem("triage_missing", "label:triage", message))
    # ブロックが読めないときは、未確定の項目があるか分からないので、triage_stale にしない
    if valid["triage"] and metadata.status == "ok" and not declared:
        message = "The triage: needed label is set but no item is declared as undetermined."
        problems.append(Problem("triage_stale", "label:triage", message))

    pending = tuple(item for item in declared if item == "estimate" or not valid[item])
    return problems, pending


def _check_block(text: str, metadata: Extracted) -> list[Problem]:
    problems: list[Problem] = []
    if metadata.status == "missing":
        problems.append(Problem("block_missing", "block", "The issue body has no metadata block."))
    elif metadata.status == "broken":
        problems.append(
            Problem("block_broken", "block", f"The metadata block is broken ({_cause(metadata, 'unreadable')}).")
        )
    elif metadata.status == "unknown_version":
        cause = _cause(metadata, "unsupported version")
        problems.append(
            Problem("block_unknown_version", "block", f"The metadata block has an unsupported version ({cause}).")
        )
    misplaced: list[str] = []
    for candidate in block_candidates(text):
        header = _HEADER.fullmatch(candidate.text)
        if header is not None and header["kind"] in ("run-record", "evaluation") and header["kind"] not in misplaced:
            misplaced.append(header["kind"])
    for kind in misplaced:
        problems.append(Problem("block_misplaced", "block", f"The issue body must not contain a {kind} block."))
    return problems


def _check_title(title: str, metadata: Extracted) -> list[Problem]:
    if not title.strip():
        return [Problem("title_empty", "title", "The title is empty.")]
    problems: list[Problem] = []
    if _TITLE_PREFIX.match(title):
        problems.append(Problem("title_prefix", "title", "The title starts with a prefix or a bracketed tag."))
    english = (
        metadata.status == "ok" and isinstance(metadata.value, IssueMetadata) and metadata.value.title_language == "en"
    )
    if not english and not _JAPANESE.search(title):
        problems.append(
            Problem("title_not_japanese", "title", "The title has no Japanese character and title_language is not en.")
        )
    return problems


def check_issue(body: str | None, labels: Iterable[str], rules: Rules, *, title: str | None = None) -> CheckResult:
    """Issue の本文・ラベル・タイトルを検査する。``body`` が ``None`` なら空文字として扱う。

    必須の節・必須のラベル・ブロックの欠け、壊れ、未知の版は、どれも ``complete`` にしない。
    ``title`` を渡したときだけ、タイトルを検査する。
    """
    text = body or ""
    metadata = extract_block(text, "metadata")
    label_problems, pending = _check_labels(labels, rules, metadata)
    lines, fences = _scan(text)
    problems = [*_check_sections(lines, fences, rules, metadata), *label_problems, *_check_block(text, metadata)]
    if title is not None:
        problems.extend(_check_title(title, metadata))
    return CheckResult(tuple(problems), pending, metadata)


# ---------------------------------------------------------------------------
# CLI（Spec 4.5 節）
# ---------------------------------------------------------------------------


def _json_values(text: str) -> list[object]:
    """空白を挟んで連結された JSON の値をすべて読む（``gh api --paginate`` は配列を連結して出す）。"""
    decoder = json.JSONDecoder()
    values: list[object] = []
    index = 0
    while True:
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            return values
        try:
            value, index = decoder.raw_decode(text, index)
        except json.JSONDecodeError as error:
            raise FormatError(f"The JSON input is invalid at character {error.pos}.") from None
        values.append(value)


def _label_names(items: Iterable[object]) -> list[str]:
    names: list[str] = []
    for item in items:
        entry = _mapping(item)
        name = entry.get("name") if entry is not None else None
        if not isinstance(name, str):
            raise FormatError("Every label must be an object with a string name.")
        names.append(name)
    return names


def _load_issue(path: str) -> tuple[str | None, str | None, list[str]]:
    """``gh api repos/<owner>/<repo>/issues/<N>`` か ``gh issue view --json title,body,labels`` の出力を読む。"""
    values = _json_values(_read_text(Path(path)))
    issue = _mapping(values[0]) if len(values) == 1 else None
    if issue is None:
        raise FormatError("The issue JSON must contain exactly one object.")
    if "body" not in issue or "labels" not in issue:
        raise FormatError("The issue JSON must have body and labels.")
    body, title, items = issue["body"], issue.get("title"), _sequence(issue["labels"])
    if (body is not None and not isinstance(body, str)) or (title is not None and not isinstance(title, str)):
        raise FormatError("The issue title and body must be strings.")
    if items is None:
        raise FormatError("The issue labels must be an array.")
    return title, body, _label_names(items)


def _print_json(data: object) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _definition_json(label: LabelDefinition) -> dict[str, str]:
    return {
        "name": label.name,
        "family": label.family,
        "value": label.value,
        "color": label.color,
        "description": label.description,
    }


def _run_check(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if args.issue_json is not None and (args.label or args.title is not None):
        parser.error("--label and --title cannot be used with --issue-json")
    rules = load_rules(args.repo)
    if args.issue_json is not None:
        title, body, labels = _load_issue(args.issue_json)
    else:
        title, body, labels = args.title, _read_text(Path(args.body_file)), list(args.label)
    result = check_issue(body, labels, rules, title=title)
    passed = not result.problems and (not result.undetermined or args.allow_undetermined)
    _print_json(
        {
            "ok": passed,
            "complete": result.complete,
            "problems": [{"code": p.code, "where": p.where, "message": p.message} for p in result.problems],
            "undetermined": list(result.undetermined),
            "metadata": {
                "status": result.metadata.status,
                "version": result.metadata.version,
                "reason": result.metadata.reason,
                "line": result.metadata.line,
            },
        }
    )
    return 0 if passed else 1


def _run_labels(args: argparse.Namespace) -> int:
    rules = load_rules(args.repo)
    output: dict[str, object] = {
        "repository": rules.repository,
        "definitions": [_definition_json(label) for label in rules.labels],
    }
    if args.existing_json is not None:
        values = _json_values(_read_text(Path(args.existing_json)))
        if not values:
            raise FormatError("The existing labels JSON contains no array.")
        existing: list[str] = []
        for value in values:  # gh api --paginate が連結した複数の配列を、1 つにつなぐ
            items = _sequence(value)
            if items is None:
                raise FormatError("The existing labels JSON must contain only arrays.")
            existing.extend(_label_names(items))
        output["missing"] = [_definition_json(label) for label in missing_labels(rules, existing)]
    _print_json(output)
    return 0


def _run_extract(args: argparse.Namespace) -> int:
    extracted = extract_block(_read_text(Path(args.file)), args.kind)
    _print_json(
        {
            "status": extracted.status,
            "version": extracted.version,
            "reason": extracted.reason,
            "line": extracted.line,
            "value": extracted.value.model_dump(mode="json") if extracted.value is not None else None,
        }
    )
    return 0 if extracted.status == "ok" else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="issue_format.py", description="Issue の共有の書式（issue-format v1）の検査と読み書き。"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="Issue の本文・ラベル・タイトルを検査する")
    check.add_argument("--repo", required=True, metavar="OWNER/NAME", help="対象の owner/repo")
    source = check.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--issue-json", metavar="PATH", help="gh api の Issue か gh issue view --json title,body,labels の出力"
    )
    source.add_argument("--body-file", metavar="PATH", help="本文のファイル（--label・--title と組み合わせる）")
    check.add_argument(
        "--label", action="append", default=[], metavar="NAME", help="付いているラベル（複数回指定できる）"
    )
    check.add_argument("--title", help="検査するタイトル")
    check.add_argument(
        "--allow-undetermined", action="store_true", help="問題が無ければ、未確定の項目があっても成功にする"
    )

    labels = commands.add_parser("labels", help="ラベルの定義を出し、既存のラベルに無いものを示す")
    labels.add_argument("--repo", required=True, metavar="OWNER/NAME", help="対象の owner/repo")
    labels.add_argument("--existing-json", metavar="PATH", help="gh api --paginate repos/<owner>/<repo>/labels の出力")

    extract = commands.add_parser("extract", help="本文かコメントから機械可読ブロックを取り出す")
    extract.add_argument("--kind", required=True, choices=sorted(KINDS), help="ブロックの種類")
    extract.add_argument("--file", required=True, metavar="PATH", help="本文かコメントのファイル")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI の入口。入力・定義の誤りは、標準エラー出力に ``issue_format: <理由>`` を書いて 2 を返す。"""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            return _run_check(parser, args)
        if args.command == "labels":
            return _run_labels(args)
        return _run_extract(args)
    except (FormatError, OSError, UnicodeError) as error:
        sys.stderr.write(f"issue_format: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
