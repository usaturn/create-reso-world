#!/usr/bin/env python3
"""Issue の作成・更新・コメントの案を作り、秘密情報を検査し、承認された案をそのまま投稿する。

- ``draft``: GitHub を読むだけで、書き込まない。案（``draft.json``）と人が読む案（``preview.md``）を
  ``--out-dir`` に書く
- ``publish``: 承認された ``--sha256`` と一致する案だけを送る。送る前に秘密情報を検査し直し、
  読んだ後に本文・タイトル・ラベルが変わっていれば上書きしない。結果の分からない作成・投稿は送り直さない

標準出力に JSON を 1 つ出す（``status`` を必ず持つ）。入力・定義の誤りは標準エラー出力に
``publish_issue: <理由>`` を書いて終了コード 2、``check_failed`` などで止まるときは終了コード 1、成功は 0。

依存は pydantic と標準ライブラリと ``.agents/scripts/issue_format.py`` だけ（``tools.*`` は import しない）。
``gh`` の呼び出しは ``Runner``、秘密情報の検査は ``Scanner``、非対話の判定は環境変数の ``Mapping`` を引数で受け取る。
"""

import argparse
import difflib
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePath
from typing import Any, Literal, NoReturn, Protocol, Self, cast
from urllib.parse import quote, urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

ROOT = Path(__file__).resolve().parents[4]
FORMAT_MODULE = ROOT / ".agents/scripts/issue_format.py"
LEAKS_FOUND = 99
REMOVED_ENV = ("GITLEAKS_CONFIG", "GITLEAKS_CONFIG_TOML")
FILE_MODE = 0o600
CANARY_NAME = "canary"
CANARY_LENGTH = 36
MESSAGE_LIMIT = 500
REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*")
REFERENCE = re.compile(r"(?:(?P<repo>[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*)#)?(?P<number>[1-9][0-9]*)")
SHA256 = re.compile(r"[0-9a-fA-F]{64}")
PIN_LINE = re.compile(r'^readonly GITLEAKS_VERSION="(?P<version>[^"]+)"$', re.MULTILINE)
COMMENT_OPEN = re.compile(r"^ {0,3}<!--")
KNOWN_COMMENT = re.compile(r"^ {0,3}<!-- (?:issue-format:|planning-parallel-issues(?::| board:))")
OK_STATUSES = frozenset({"draft_saved", "published", "already_published"})
NO_PARENT = "No parent issue found"
URL_PARTS = 4


def _load_format() -> Any:
    """``issue_format.py`` を ``sys.modules`` に登録してから実行する（pydantic のモデルが自分のモジュールを引く）。"""
    spec = importlib.util.spec_from_file_location("issue_format", FORMAT_MODULE)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {FORMAT_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["issue_format"] = module
    spec.loader.exec_module(module)
    return module


fmt: Any = _load_format()


class PublishError(ValueError):
    """入力・定義の誤り。``main`` が ``publish_issue: <理由>`` と終了コード 2 にする。"""


class _Stop(Exception):
    """処理を止める。``result`` がそのまま出力になる。"""

    def __init__(self, result: dict[str, object]) -> None:
        self.result = result
        super().__init__(str(result.get("status")))


class _GhError(_Stop):
    """``gh`` の失敗。結果の分からない送信かどうかは、呼び出し側が手順の記録で判断する。"""

    def __init__(self, step: str, returncode: int, stdout: str, stderr: str) -> None:
        self.stdout = stdout
        self.stderr = stderr
        message = (stderr.strip() or stdout.strip())[:MESSAGE_LIMIT]
        super().__init__({"status": "gh_failed", "step": step, "returncode": returncode, "message": message})


class Runner(Protocol):
    def __call__(
        self,
        args: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]: ...


def run_process(args: Sequence[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    """既定の ``Runner``。シェルを通さず、UTF-8 で標準入出力を扱う。"""
    return subprocess.run(list(args), input=input_text, text=True, encoding="utf-8", capture_output=True, check=False)


@dataclass(frozen=True)
class Scanner:
    """秘密情報の検査。``binary`` は Gitleaks の実行ファイル、``pin_file`` は版を定義するファイル。"""

    binary: str = "gitleaks"
    pin_file: Path = ROOT / ".devcontainer/install_gitleaks.bash"
    timeout: float = 120.0


# ---------------------------------------------------------------------------
# 案・記録のモデル
# ---------------------------------------------------------------------------


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class LabelSpec(_Model):
    name: str
    color: str
    description: str


class IssueTarget(_Model):
    repository: str
    number: int
    id: int


class Expected(_Model):
    """読んだ時点の Issue。``updated_at`` は記録だけで、比べるのは本文の SHA-256・タイトル・ラベル。

    ``labels`` はラベル名を ``casefold`` して重複を除き、並べ替えた値（``_label_keys``）。
    """

    title: str
    body_sha256: str
    labels: tuple[str, ...]
    updated_at: str


class DraftWarning(_Model):
    code: Literal["hidden_comment"]
    target: Literal["body"]
    line: int


class Draft(_Model):
    """承認する案。``labels`` は create なら付けるもの、update なら足すもの。"""

    version: Literal[1]
    action: Literal["create", "update", "comment"]
    repository: str
    created_at: str
    title: str | None
    body: str
    labels: tuple[str, ...]
    remove_labels: tuple[str, ...]
    create_labels: tuple[LabelSpec, ...]
    parent: IssueTarget | None
    blocked_by: tuple[IssueTarget, ...]
    target: IssueTarget | None
    expected: Expected | None
    warnings: tuple[DraftWarning, ...]

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.action == "create":
            if self.title is None or self.target is not None or self.expected is not None or self.remove_labels:
                raise ValueError("a create draft needs a title and has no target, expected state or removed labels")
            return self
        if self.target is None:
            raise ValueError("an update or comment draft needs a target")
        if self.parent is not None or self.blocked_by:
            raise ValueError("only a create draft has relationships")
        if self.action == "update":
            if self.expected is None:
                raise ValueError("an update draft needs the state it was read in")
            return self
        if self.title is not None or self.expected is not None or self.labels or self.remove_labels:
            raise ValueError("a comment draft has only a body")
        if self.create_labels:
            raise ValueError("a comment draft creates no labels")
        return self


class StepRecord(_Model):
    step: str
    state: Literal["intent", "done"]
    detail: dict[str, str | int] = Field(default_factory=dict[str, str | int])


class ResultFile(_Model):
    version: Literal[1]
    draft_sha256: str
    published: bool
    url: str | None
    steps: tuple[StepRecord, ...]


class _IssueLabel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str


class IssueSnapshot(BaseModel):
    """``gh api repos/<o>/<r>/issues/<n>`` の応答。``pull_request`` のキーがあれば PR。"""

    model_config = ConfigDict(extra="ignore")
    number: int
    id: int
    title: str
    body: str | None = None
    labels: tuple[_IssueLabel, ...] = ()
    updated_at: str
    html_url: str
    pull_request: object | None = None

    @property
    def is_pull_request(self) -> bool:
        return "pull_request" in self.model_fields_set

    @property
    def label_names(self) -> list[str]:
        return [label.name for label in self.labels]


class _Response(BaseModel):
    """作成・投稿・親の取得の応答から読む値だけ（残りは読まない）。"""

    model_config = ConfigDict(extra="ignore")
    id: int
    number: int | None = None
    html_url: str | None = None


class Journal:
    """``result.json``。手順ごとに、送る前に意図、送った後に結果を書く（一時ファイルに書いて ``os.replace``）。"""

    def __init__(self, path: Path, draft_sha256: str, record: ResultFile | None) -> None:
        self.path = path
        self.draft_sha256 = draft_sha256
        self.published = record.published if record is not None else False
        self.url = record.url if record is not None else None
        self._steps: dict[str, StepRecord] = {item.step: item for item in record.steps} if record is not None else {}

    @classmethod
    def load(cls, path: Path, draft_sha256: str) -> Self:
        if not path.exists():
            return cls(path, draft_sha256, None)
        try:
            record = ResultFile.model_validate_json(path.read_bytes())
        except OSError, ValidationError:
            raise _Stop({"status": "uncertain", "reason": "result_unreadable", "result": str(path)}) from None
        if record.draft_sha256 != draft_sha256:
            raise PublishError("result.json belongs to a different draft")
        return cls(path, draft_sha256, record)

    def state(self, step: str) -> str | None:
        record = self._steps.get(step)
        return record.state if record is not None else None

    def detail(self, step: str) -> dict[str, str | int]:
        record = self._steps.get(step)
        return dict(record.detail) if record is not None else {}

    def done_steps(self) -> list[str]:
        return [name for name, record in self._steps.items() if record.state == "done"]

    def created_labels(self) -> list[str]:
        return [
            name.removeprefix("label:")
            for name, record in self._steps.items()
            if name.startswith("label:") and record.state == "done" and record.detail.get("created") == 1
        ]

    def intent(self, step: str) -> None:
        self._steps[step] = StepRecord(step=step, state="intent")
        self._flush()

    def done(self, step: str, **detail: str | int) -> None:
        self._steps[step] = StepRecord(step=step, state="done", detail=detail)
        self._flush()

    def finish(self, url: str) -> None:
        self.published = True
        self.url = url
        self._flush()

    def _flush(self) -> None:
        record = ResultFile(
            version=1,
            draft_sha256=self.draft_sha256,
            published=self.published,
            url=self.url,
            steps=tuple(self._steps.values()),
        )
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".result-", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(record.model_dump_json(indent=2).encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.path)
        except BaseException:
            Path(name).unlink(missing_ok=True)
            raise


# ---------------------------------------------------------------------------
# 小さな部品
# ---------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _body_sha256(body: str | None) -> str:
    """読んだ時点の本文の SHA-256。``null`` は空文字として扱い、改行は変換しない（API の文字列のまま）。"""
    return _sha256((body or "").encode("utf-8"))


def _label_keys(names: Iterable[str]) -> tuple[str, ...]:
    """ラベル名の集合を、大文字・小文字を区別せず比べられる並びにする。"""
    return tuple(sorted({name.casefold() for name in names}))


def _mapping(value: object) -> Mapping[str, object] | None:
    return cast("dict[str, object]", value) if isinstance(value, dict) else None


def _encode(text: str) -> bytes:
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError:
        raise PublishError("the text cannot be encoded as UTF-8") from None


def _write_exclusive(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, FILE_MODE)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def _rules(repository: str) -> Any:
    """登録したリポジトリの規則。未登録・定義の誤りは入力の誤り。"""
    if REPOSITORY.fullmatch(repository) is None:
        raise PublishError(f"the repository must look like OWNER/NAME: {repository}")
    try:
        return fmt.load_rules(repository)
    except fmt.FormatError as error:
        raise PublishError("; ".join(error.problems)) from None


def _check_out_dir(out_dir: Path) -> None:
    if not out_dir.is_dir():
        raise PublishError(f"--out-dir must be an existing directory: {out_dir}")
    if any(out_dir.iterdir()):
        raise PublishError(f"--out-dir must be empty: {out_dir}")


def non_interactive_reason(env: Mapping[str, str]) -> str | None:
    """見分けられる非対話の実行なら理由を返す。Pi の print モードは見分けられない（SKILL.md の手順で防ぐ）。"""
    if env.get("CLAUDE_CODE_SESSION_ATTENDED") == "0":
        return "CLAUDE_CODE_SESSION_ATTENDED=0"
    if env.get("CLAUDE_CODE_ENTRYPOINT", "").startswith("sdk"):
        return "CLAUDE_CODE_ENTRYPOINT=sdk*"
    if env.get("AGENT_RUNNER_DEPTH"):
        return "AGENT_RUNNER_DEPTH"
    if env.get("CI"):
        return "CI"
    return None


# ---------------------------------------------------------------------------
# gh の呼び出し
# ---------------------------------------------------------------------------


def _call(
    runner: Runner,
    method: str,
    endpoint: str,
    *,
    step: str,
    payload: Mapping[str, object] | None = None,
    paginate_jq: str | None = None,
) -> str:
    """``gh api --method <M> <endpoint>`` を 1 回実行して標準出力を返す。失敗は ``_GhError``。"""
    argv = ["gh", "api", "--method", method]
    if paginate_jq is not None:
        argv.append("--paginate")
    argv.append(endpoint)
    if paginate_jq is not None:
        argv += ["--jq", paginate_jq]
    input_text: str | None = None
    if payload is not None:
        argv += ["--input", "-"]
        input_text = json.dumps(payload)  # ASCII のみの JSON にし、実行環境の文字コードに左右されないようにする
    try:
        done = runner(argv, input_text=input_text)
    except OSError as error:
        raise _GhError(step, 127, "", str(error)) from None
    if done.returncode != 0:
        raise _GhError(step, done.returncode, done.stdout, done.stderr)
    return done.stdout


def _get_issue(runner: Runner, repository: str, number: int, *, step: str) -> IssueSnapshot:
    out = _call(runner, "GET", f"repos/{repository}/issues/{number}", step=step)
    try:
        return IssueSnapshot.model_validate_json(out)
    except ValidationError:
        raise _GhError(step, 0, out, "unexpected response for the issue") from None


def _list_labels(runner: Runner, repository: str, *, step: str) -> list[str]:
    """``--paginate`` の行の並び（1 行 1 名）。最初のページだけで判断しない。"""
    out = _call(runner, "GET", f"repos/{repository}/labels", step=step, paginate_jq=".[].name")
    return [line.removesuffix("\r") for line in out.split("\n") if line.removesuffix("\r")]


def _not_an_issue(repository: str, number: int) -> _Stop:
    return _Stop({"status": "not_an_issue", "repository": repository, "number": number})


def _resolve_reference(reference: str, default_repository: str, runner: Runner) -> IssueTarget:
    matched = REFERENCE.fullmatch(reference)
    if matched is None:
        raise PublishError(f"a reference must be N or OWNER/NAME#N: {reference}")
    repository = default_repository
    if matched["repo"] is not None:
        repository = _rules(matched["repo"]).repository
    number = int(matched["number"])
    snapshot = _get_issue(runner, repository, number, step=f"relation:{reference}")
    if snapshot.is_pull_request:
        raise _not_an_issue(repository, number)
    return IssueTarget(repository=repository, number=number, id=snapshot.id)


# ---------------------------------------------------------------------------
# 秘密情報の検査
# ---------------------------------------------------------------------------


def _scan_failed(reason: str) -> _Stop:
    return _Stop({"status": "scan_failed", "reason": reason})


def _pinned_version(pin_file: Path) -> str:
    matched = PIN_LINE.search(pin_file.read_text(encoding="utf-8"))
    if matched is None:
        raise ValueError("no GITLEAKS_VERSION line")
    return matched["version"]


def _scan_environment() -> dict[str, str]:
    env = dict(os.environ)
    for name in REMOVED_ENV:
        env.pop(name, None)
    return env


def _canary() -> str:
    alphabet = string.ascii_letters + string.digits
    return "gh" + "p_" + "".join(secrets.choice(alphabet) for _ in range(CANARY_LENGTH))


def _evaluate_report(report: Path, names: Mapping[str, str]) -> list[dict[str, object]]:
    """レポートを判定する。見本（canary）が検出されていなければ検査できていない。値は ``--redact`` で出ない。"""
    try:
        parsed: object = json.loads(report.read_bytes())
    except OSError, ValueError:
        raise _scan_failed("report_unreadable") from None
    if not isinstance(parsed, list):
        raise _scan_failed("report_not_list")
    findings: list[dict[str, object]] = []
    canary_seen = False
    for entry in cast("list[object]", parsed):
        item = _mapping(entry)
        file = item.get("File") if item is not None else None
        if item is None or not isinstance(file, str):
            raise _scan_failed("report_mismatch")
        name = PurePath(file).name
        if name == CANARY_NAME:
            canary_seen = True
        elif name in names:
            line = item.get("StartLine")
            findings.append(
                {
                    "target": names[name],
                    "rule": str(item.get("RuleID", "")),
                    "line": line if isinstance(line, int) else 0,
                }
            )
        else:
            raise _scan_failed("report_mismatch")
    if not canary_seen:
        raise _scan_failed("canary_not_detected")
    return findings


def _scan_in(work: Path, items: Sequence[tuple[str, str]], scanner: Scanner, version: str) -> None:
    source = work / "source"
    source.mkdir(mode=0o700)
    names: dict[str, str] = {}
    for index, (target, text) in enumerate(items):
        name = f"{index:04d}"
        _write_exclusive(source / name, _encode(text))
        names[name] = target
    _write_exclusive(source / CANARY_NAME, f"{_canary()}\n".encode())
    ignore = work / "ignore"
    _write_exclusive(ignore, b"")
    report = work / "report.json"
    env = _scan_environment()
    try:
        reported = subprocess.run(
            [scanner.binary, "version"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=scanner.timeout,
            env=env,
            cwd=work,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        raise _scan_failed("scanner_unavailable") from None
    if reported.returncode != 0 or reported.stdout.strip() != version:
        raise _scan_failed("version_mismatch")
    argv = [
        scanner.binary,
        "dir",
        str(source),
        "--no-banner",
        "--redact",
        "--exit-code",
        str(LEAKS_FOUND),
        "--report-format",
        "json",
        "--report-path",
        str(report),
        "--ignore-gitleaks-allow",
        "--gitleaks-ignore-path",
        str(ignore),
    ]
    try:
        scanned = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=scanner.timeout,
            env=env,
            cwd=work,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        raise _scan_failed("scanner_failed") from None
    # 終了コード 0 は、見本を検出しなかった（規則なしで動いた・別の場所を検査した）失敗として扱う
    if scanned.returncode != LEAKS_FOUND:
        raise _scan_failed(f"exit_code_{scanned.returncode}")
    findings = _evaluate_report(report, names)
    if findings:
        raise _Stop({"status": "secret_detected", "findings": findings})


def _scan(items: Sequence[tuple[str, str]], scanner: Scanner) -> None:
    """送る文字列（対象名と内容）を検査する。検出は ``secret_detected``、検査の失敗は ``scan_failed``。"""
    try:
        version = _pinned_version(scanner.pin_file)
    except OSError, UnicodeError, ValueError:
        raise _scan_failed("pin_unreadable") from None
    work = Path(tempfile.mkdtemp(prefix="issue-authoring-scan-"))
    try:
        _scan_in(work, items, scanner, version)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# draft
# ---------------------------------------------------------------------------


def _compose(body: str, metadata: BaseModel | None) -> str:
    """機械可読ブロックを入れた本文を作り、上限を超えていれば ``too_large``。"""
    text = body
    if metadata is not None:
        if len(body) > fmt.BODY_LIMIT:
            raise _Stop({"status": "too_large", "length": len(body), "limit": fmt.BODY_LIMIT})
        try:
            text = fmt.write_metadata(body, metadata)
        except fmt.FormatError as error:
            raise PublishError("; ".join(error.problems)) from None
    if len(text) > fmt.BODY_LIMIT:
        raise _Stop({"status": "too_large", "length": len(text), "limit": fmt.BODY_LIMIT})
    return text


def _warnings(body: str) -> tuple[DraftWarning, ...]:
    """コードブロックの外の行頭の ``<!--``。issue-format のブロックと planning-parallel-issues のマーカーは除く。"""
    return tuple(
        DraftWarning(code="hidden_comment", target="body", line=line.number)
        for line in fmt.scan_lines(body)
        if not line.in_fence and COMMENT_OPEN.match(line.text) and not KNOWN_COMMENT.match(line.text)
    )


def _plan_labels(requested: Sequence[str], existing: Sequence[str], rules: Any) -> tuple[list[str], list[LabelSpec]]:
    """既存のラベルか、規則に定義があるラベル（作る）だけを許す。大文字・小文字は区別しない。"""
    existing_by_key = {name.casefold(): name for name in existing}
    defined = {label.name.casefold(): label for label in rules.labels}
    attach: list[str] = []
    create: list[LabelSpec] = []
    unknown: list[str] = []
    seen: set[str] = set()
    for name in requested:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        if key in existing_by_key:
            attach.append(existing_by_key[key])
        elif key in defined:
            label = defined[key]
            attach.append(label.name)
            create.append(LabelSpec(name=label.name, color=label.color, description=label.description))
        else:
            unknown.append(name)
    if unknown:
        raise _Stop({"status": "unknown_label", "labels": unknown})
    return attach, create


def _check(body: str, labels: Sequence[str], rules: Any, *, title: str) -> tuple[str, ...]:
    result = fmt.check_issue(body, labels, rules, title=title)
    if result.problems:
        problems = [{"code": item.code, "where": item.where, "message": item.message} for item in result.problems]
        raise _Stop({"status": "check_failed", "problems": problems})
    return tuple(result.undetermined)


def _fence(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _preview(draft: Draft, before: str | None) -> str:
    lines = [f"# 案: {draft.action} {draft.repository}", ""]
    if draft.target is not None:
        lines.append(f"- 対象: {draft.target.repository}#{draft.target.number}")
    if draft.title is not None:
        lines.append(f"- タイトル: {draft.title}")
    if draft.labels:
        lines.append(f"- ラベル（付ける）: {', '.join(draft.labels)}")
    if draft.remove_labels:
        lines.append(f"- ラベル（外す）: {', '.join(draft.remove_labels)}")
    for label in draft.create_labels:
        lines.append(f"- ラベル（新しく作る）: {label.name}（色: {label.color}、説明: {label.description}）")
    if draft.parent is not None:
        lines.append(f"- 親: {draft.parent.repository}#{draft.parent.number}")
    for blocker in draft.blocked_by:
        lines.append(f"- 先行: {blocker.repository}#{blocker.number}")
    for warning in draft.warnings:
        lines.append(f"- 警告: {warning.target} の {warning.line} 行目に見えない HTML コメント（{warning.code}）")
    fence = _fence(draft.body)
    lines += ["", "## 本文", "", f"{fence}markdown", draft.body, fence]
    if before is not None:
        diff = "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                draft.body.splitlines(keepends=True),
                fromfile="読んだ時点の本文",
                tofile="新しい本文",
            )
        )
        diff_fence = _fence(diff)
        lines += ["", "## 差分", "", f"{diff_fence}diff", diff.rstrip("\n"), diff_fence]
    return "\n".join(lines) + "\n"


def _save(draft: Draft, out_dir: Path, *, before: str | None, undetermined: Sequence[str]) -> dict[str, object]:
    raw = draft.model_dump_json(indent=2).encode("utf-8")
    draft_path = out_dir / "draft.json"
    preview_path = out_dir / "preview.md"
    _write_exclusive(draft_path, raw)
    _write_exclusive(preview_path, _encode(_preview(draft, before)))
    return {
        "status": "draft_saved",
        "draft": str(draft_path),
        "sha256": _sha256(raw),
        "preview": str(preview_path),
        "create_labels": [label.name for label in draft.create_labels],
        "undetermined": list(undetermined),
        "warnings": [warning.model_dump() for warning in draft.warnings],
    }


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def draft_create(
    *,
    repo: str,
    title: str,
    body: str,
    metadata: BaseModel | None,
    labels: Sequence[str],
    parent: str | None,
    blocked_by: Sequence[str],
    out_dir: Path,
    runner: Runner,
    scanner: Scanner,
) -> dict[str, object]:
    """新しい Issue の案を作る。GitHub は読むだけで、書き込まない。"""
    try:
        rules = _rules(repo)
        repository: str = rules.repository
        _check_out_dir(out_dir)
        text = _compose(body, metadata)
        _scan([("title", title), ("body", text)], scanner)
        existing = _list_labels(runner, repository, step="labels")
        attach, create = _plan_labels(labels, existing, rules)
        parent_target = _resolve_reference(parent, repository, runner) if parent is not None else None
        blockers = tuple(_resolve_reference(reference, repository, runner) for reference in blocked_by)
        undetermined = _check(text, attach, rules, title=title)
        draft = Draft(
            version=1,
            action="create",
            repository=repository,
            created_at=_now(),
            title=title,
            body=text,
            labels=tuple(attach),
            remove_labels=(),
            create_labels=tuple(create),
            parent=parent_target,
            blocked_by=blockers,
            target=None,
            expected=None,
            warnings=_warnings(text),
        )
        return _save(draft, out_dir, before=None, undetermined=undetermined)
    except _Stop as stop:
        return stop.result


def _read_snapshot(read_json: Mapping[str, object], issue: int, repository: str) -> IssueSnapshot:
    try:
        snapshot = IssueSnapshot.model_validate(read_json)
    except ValidationError:
        raise PublishError("--read-json is not the output of `gh api repos/<owner>/<repo>/issues/<N>`") from None
    parts = urlparse(snapshot.html_url).path.strip("/").split("/")
    if snapshot.is_pull_request or (len(parts) == URL_PARTS and parts[2] == "pull"):
        raise _not_an_issue(repository, snapshot.number)
    if snapshot.number != issue:
        raise PublishError(f"--read-json is for issue {snapshot.number}, not {issue}")
    if len(parts) != URL_PARTS or parts[2] != "issues" or f"{parts[0]}/{parts[1]}".casefold() != repository.casefold():
        raise PublishError(f"--read-json is not for an issue of {repository}")
    return snapshot


def draft_update(
    *,
    repo: str,
    issue: int,
    read_json: Mapping[str, object],
    body: str,
    metadata: BaseModel | None,
    title: str | None,
    add_labels: Sequence[str],
    remove_labels: Sequence[str],
    out_dir: Path,
    runner: Runner,
    scanner: Scanner,
) -> dict[str, object]:
    """既存の Issue を更新する案を作る。読んだ時点の本文の SHA-256・タイトル・ラベルを案に入れ、投稿の直前に比べる。"""
    try:
        rules = _rules(repo)
        repository: str = rules.repository
        _check_out_dir(out_dir)
        read = _read_snapshot(read_json, issue, repository)
        current = _get_issue(runner, repository, issue, step="issue")
        if current.is_pull_request:
            raise _not_an_issue(repository, issue)
        if (
            (current.body or "") != (read.body or "")
            or current.title != read.title
            or _label_keys(current.label_names) != _label_keys(read.label_names)
        ):
            raise _Stop({"status": "conflict", "issue": issue, "reason": "changed_since_read"})
        text = _compose(body, metadata)
        new_title = title if title is not None else current.title
        scanned = [("body", text)] if title is None else [("title", title), ("body", text)]
        _scan(scanned, scanner)

        current_keys = {name.casefold() for name in current.label_names}
        add_keys = {name.casefold() for name in add_labels}
        attach: list[str] = []
        create: list[LabelSpec] = []
        if add_labels:
            attach, create = _plan_labels(add_labels, _list_labels(runner, repository, step="labels"), rules)
        remove_keys = {name.casefold() for name in remove_labels}
        to_remove = [name for name in current.label_names if name.casefold() in remove_keys - add_keys]
        to_add = [name for name in attach if name.casefold() not in current_keys]
        final = [name for name in current.label_names if name not in to_remove] + to_add
        undetermined = _check(text, final, rules, title=new_title)
        draft = Draft(
            version=1,
            action="update",
            repository=repository,
            created_at=_now(),
            title=title if title is not None and title != current.title else None,
            body=text,
            labels=tuple(to_add),
            remove_labels=tuple(to_remove),
            create_labels=tuple(label for label in create if label.name in to_add),
            parent=None,
            blocked_by=(),
            target=IssueTarget(repository=repository, number=issue, id=current.id),
            expected=Expected(
                title=read.title,
                body_sha256=_body_sha256(read.body),
                labels=_label_keys(read.label_names),
                updated_at=read.updated_at,
            ),
            warnings=_warnings(text),
        )
        return _save(draft, out_dir, before=read.body or "", undetermined=undetermined)
    except _Stop as stop:
        return stop.result


def draft_comment(
    *,
    repo: str,
    issue: int,
    body: str,
    out_dir: Path,
    runner: Runner,
    scanner: Scanner,
) -> dict[str, object]:
    """コメントの案を作る。評価コメントの形は ``compose_comment`` が確かめるので、書式の検査はしない。"""
    try:
        rules = _rules(repo)
        repository: str = rules.repository
        _check_out_dir(out_dir)
        text = _compose(body, None)
        _scan([("body", text)], scanner)
        snapshot = _get_issue(runner, repository, issue, step="issue")
        if snapshot.is_pull_request:
            raise _not_an_issue(repository, issue)
        draft = Draft(
            version=1,
            action="comment",
            repository=repository,
            created_at=_now(),
            title=None,
            body=text,
            labels=(),
            remove_labels=(),
            create_labels=(),
            parent=None,
            blocked_by=(),
            target=IssueTarget(repository=repository, number=issue, id=snapshot.id),
            expected=None,
            warnings=_warnings(text),
        )
        return _save(draft, out_dir, before=None, undetermined=())
    except _Stop as stop:
        return stop.result


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Context:
    runner: Runner
    draft: Draft
    journal: Journal


def _ensure_labels(ctx: _Context) -> None:
    """案のラベルのうち無いものを作る（既存を上書きしない）。案が作る前提にしていないラベルが無ければ止まる。"""
    draft = ctx.draft
    if not draft.labels and not draft.create_labels:
        return
    existing = {name.casefold() for name in _list_labels(ctx.runner, draft.repository, step="labels")}
    creatable = {label.name.casefold() for label in draft.create_labels}
    missing = [name for name in draft.labels if name.casefold() not in existing | creatable]
    if missing:
        raise _Stop({"status": "labels_changed", "labels": missing})
    for spec in draft.create_labels:
        step = f"label:{spec.name}"
        if ctx.journal.state(step) == "done":
            continue
        if spec.name.casefold() in existing:
            ctx.journal.done(step, created=0)
            continue
        ctx.journal.intent(step)
        payload = {"name": spec.name, "color": spec.color, "description": spec.description}
        try:
            _call(ctx.runner, "POST", f"repos/{draft.repository}/labels", step=step, payload=payload)
        except _GhError:
            # 同時に作られた（already exists の 422）ときは、取り直して名前があれば完了として扱う
            now = {name.casefold() for name in _list_labels(ctx.runner, draft.repository, step=step)}
            if spec.name.casefold() not in now:
                raise
            ctx.journal.done(step, created=0)
            continue
        ctx.journal.done(step, created=1)


def _unexpected(step: str, out: str) -> _GhError:
    return _GhError(step, 0, out, "unexpected response")


def _create_issue(ctx: _Context) -> None:
    draft = ctx.draft
    if ctx.journal.state("issue") == "done":
        return
    ctx.journal.intent("issue")
    payload = {"title": draft.title, "body": draft.body, "labels": list(draft.labels)}
    out = _call(ctx.runner, "POST", f"repos/{draft.repository}/issues", step="issue", payload=payload)
    try:
        created = _Response.model_validate_json(out)
    except ValidationError:
        raise _unexpected("issue", out) from None
    if created.number is None or created.html_url is None:
        raise _unexpected("issue", out)
    ctx.journal.done("issue", number=created.number, id=created.id, url=created.html_url)


def _set_parent(ctx: _Context, child_number: int, child_id: int) -> None:
    parent = ctx.draft.parent
    if parent is None or ctx.journal.state("parent") == "done":
        return
    ctx.journal.intent("parent")
    endpoint = f"repos/{ctx.draft.repository}/issues/{child_number}/parent"
    try:
        out = _call(ctx.runner, "GET", endpoint, step="parent")
    except _GhError as error:
        if NO_PARENT not in error.stdout + error.stderr:
            raise
    else:
        try:
            found = _Response.model_validate_json(out)
        except ValidationError:
            raise _unexpected("parent", out) from None
        if found.id != parent.id:
            raise _GhError("parent", 0, "", "the issue already has a different parent")
        ctx.journal.done("parent", existed=1)
        return
    endpoint = f"repos/{parent.repository}/issues/{parent.number}/sub_issues"
    _call(ctx.runner, "POST", endpoint, step="parent", payload={"sub_issue_id": child_id})
    ctx.journal.done("parent", existed=0)


def _set_blockers(ctx: _Context, child_number: int) -> None:
    endpoint = f"repos/{ctx.draft.repository}/issues/{child_number}/dependencies/blocked_by"
    for blocker in ctx.draft.blocked_by:
        step = f"blocked_by:{blocker.repository}#{blocker.number}"
        if ctx.journal.state(step) == "done":
            continue
        ctx.journal.intent(step)
        listed = _call(ctx.runner, "GET", endpoint, step=step, paginate_jq=".[].id")
        if str(blocker.id) in {line.strip() for line in listed.split("\n")}:
            ctx.journal.done(step, existed=1)
            continue
        _call(ctx.runner, "POST", endpoint, step=step, payload={"issue_id": blocker.id})
        ctx.journal.done(step, existed=0)


def _run_create(ctx: _Context) -> str:
    _ensure_labels(ctx)
    _create_issue(ctx)
    created = ctx.journal.detail("issue")
    number, identifier, url = created["number"], created["id"], created["url"]
    if not isinstance(number, int) or not isinstance(identifier, int) or not isinstance(url, str):
        raise _unexpected("issue", "")
    _set_parent(ctx, number, identifier)
    _set_blockers(ctx, number)
    return url


def _body_applied(ctx: _Context, target: IssueTarget, expected: Expected) -> bool:
    """Issue を読み直し、本文の更新が済んでいれば ``True``、読んだ時点のままなら ``False``。それ以外は ``conflict``。

    比べるのは本文の SHA-256・タイトル・ラベルの組。本文の更新はラベルを変えないので、ラベルは読んだ時点のまま。
    ``True`` は、送った更新の応答を失った後の再実行と、既に同じ内容になっている場合。
    """
    current = _get_issue(ctx.runner, target.repository, target.number, step="body")
    if current.is_pull_request:
        raise _not_an_issue(target.repository, target.number)
    now = (_body_sha256(current.body), current.title, _label_keys(current.label_names))
    after = (
        _body_sha256(ctx.draft.body),
        ctx.draft.title if ctx.draft.title is not None else expected.title,
        expected.labels,
    )
    if now == after:
        return True
    if now != (expected.body_sha256, expected.title, expected.labels):
        raise _Stop({"status": "conflict", "issue": target.number, "reason": "changed_since_read"})
    return False


def _update_body(ctx: _Context, target: IssueTarget, expected: Expected) -> None:
    """本文を更新する直前に読み直し、読んだ時点（本文・タイトル・ラベル）から変わっていれば上書きしない。"""
    draft = ctx.draft
    if ctx.journal.state("body") == "done":
        return
    if _body_applied(ctx, target, expected):
        ctx.journal.done("body")
        return
    ctx.journal.intent("body")
    payload: dict[str, object] = {"body": draft.body}
    if draft.title is not None:
        payload["title"] = draft.title
    _call(ctx.runner, "PATCH", f"repos/{target.repository}/issues/{target.number}", step="body", payload=payload)
    ctx.journal.done("body")


def _label_path(draft: Draft, expected: Expected) -> tuple[list[str], list[tuple[str, ...]]]:
    """ラベルの手順（名前）と、読んだ時点から手順を 1 つずつ当てたときのラベルの集合（先頭は読んだ時点）。"""
    steps = ["add_labels"] if draft.labels else []
    steps += [f"remove_label:{name}" for name in draft.remove_labels]
    keys = set(expected.labels)
    path = [_label_keys(keys)]
    if draft.labels:
        keys |= {name.casefold() for name in draft.labels}
        path.append(_label_keys(keys))
    for name in draft.remove_labels:
        keys.discard(name.casefold())
        path.append(_label_keys(keys))
    return steps, path


def _require_update_state(ctx: _Context, target: IssueTarget, expected: Expected) -> IssueSnapshot:
    """本文・タイトルが承認案どおりで、ラベルが記録に沿った途中状態にあると確かめる。"""
    steps, path = _label_path(ctx.draft, expected)
    finished = 0
    for step in steps:
        if ctx.journal.state(step) != "done":
            break
        finished += 1
    current = _get_issue(ctx.runner, target.repository, target.number, step="labels_state")
    if current.is_pull_request:
        raise _not_an_issue(target.repository, target.number)
    if (
        _body_sha256(current.body) != _body_sha256(ctx.draft.body)
        or current.title != (ctx.draft.title if ctx.draft.title is not None else expected.title)
        or _label_keys(current.label_names) not in path[finished:]
    ):
        raise _Stop(
            {
                "status": "conflict",
                "issue": target.number,
                "reason": "changed_since_read",
                "completed": ctx.journal.done_steps(),
            }
        )
    return current


def _update_labels(ctx: _Context, target: IssueTarget, expected: Expected) -> None:
    base = f"repos/{target.repository}/issues/{target.number}"
    draft = ctx.draft
    if draft.labels and ctx.journal.state("add_labels") != "done":
        _require_update_state(ctx, target, expected)
        ctx.journal.intent("add_labels")
        _call(ctx.runner, "POST", f"{base}/labels", step="add_labels", payload={"labels": list(draft.labels)})
        ctx.journal.done("add_labels")
    for name in draft.remove_labels:
        step = f"remove_label:{name}"
        if ctx.journal.state(step) == "done":
            continue
        current = _require_update_state(ctx, target, expected)
        ctx.journal.intent(step)
        if name.casefold() in {item.casefold() for item in current.label_names}:
            _call(ctx.runner, "DELETE", f"{base}/labels/{quote(name, safe='')}", step=step)
        ctx.journal.done(step)


def _run_update(ctx: _Context) -> str:
    target, expected = ctx.draft.target, ctx.draft.expected
    if target is None or expected is None:
        raise PublishError("the draft has no target")
    if ctx.journal.state("body") != "done":
        _body_applied(ctx, target, expected)  # 作るラベルの書き込みの前に、読んだ後に変わっていれば止める
    else:
        _require_update_state(ctx, target, expected)
    _ensure_labels(ctx)
    _update_body(ctx, target, expected)
    _update_labels(ctx, target, expected)
    _require_update_state(ctx, target, expected)
    return f"https://github.com/{target.repository}/issues/{target.number}"


def _run_comment(ctx: _Context) -> str:
    target = ctx.draft.target
    if target is None:
        raise PublishError("the draft has no target")
    if ctx.journal.state("comment") == "done":
        url = ctx.journal.detail("comment").get("url")
        return url if isinstance(url, str) else ""
    ctx.journal.intent("comment")
    endpoint = f"repos/{target.repository}/issues/{target.number}/comments"
    out = _call(ctx.runner, "POST", endpoint, step="comment", payload={"body": ctx.draft.body})
    try:
        posted = _Response.model_validate_json(out)
    except ValidationError:
        raise _unexpected("comment", out) from None
    if posted.html_url is None:
        raise _unexpected("comment", out)
    ctx.journal.done("comment", url=posted.html_url)
    return posted.html_url


def _published(ctx: _Context, url: str) -> dict[str, object]:
    ctx.journal.finish(url)
    result: dict[str, object] = {
        "status": "published",
        "action": ctx.draft.action,
        "url": url,
        "created_labels": ctx.journal.created_labels(),
        "result": str(ctx.journal.path),
    }
    if ctx.draft.action == "create":
        result["relations"] = [
            name for name in ctx.journal.done_steps() if name == "parent" or name.startswith("blocked_by:")
        ]
    return result


def _load_draft(raw: bytes) -> Draft:
    try:
        return Draft.model_validate_json(raw)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors(include_input=False)
        )
        raise PublishError(f"draft.json is not a valid draft ({problems})") from None


def _publish(
    draft_dir: Path, sha256: str, runner: Runner, scanner: Scanner, env: Mapping[str, str]
) -> dict[str, object]:
    if SHA256.fullmatch(sha256) is None:
        raise PublishError("--sha256 must be 64 hexadecimal digits")
    draft_path = draft_dir / "draft.json"
    try:
        raw = draft_path.read_bytes()
    except OSError as error:
        raise PublishError(f"cannot read {draft_path}: {error.strerror}") from None
    approved = sha256.lower()
    if _sha256(raw) != approved:
        return {"status": "draft_changed", "draft": str(draft_path)}
    reason = non_interactive_reason(env)
    if reason is not None:
        return {"status": "non_interactive", "reason": reason, "draft": str(draft_path)}
    draft = _load_draft(raw)
    _rules(draft.repository)
    journal = Journal.load(draft_dir / "result.json", approved)
    if journal.published:
        return {"status": "already_published", "url": journal.url, "result": str(journal.path)}
    for step in ("issue", "comment"):
        if journal.state(step) == "intent":  # 送ったかどうか分からないので、送り直さない
            return {"status": "uncertain", "step": step, "result": str(journal.path)}
    ctx = _Context(runner, draft, journal)
    try:
        scanned = [("body", draft.body)] if draft.title is None else [("title", draft.title), ("body", draft.body)]
        _scan(scanned, scanner)
        runners = {"create": _run_create, "update": _run_update, "comment": _run_comment}
        return _published(ctx, runners[draft.action](ctx))
    except _GhError as error:
        return {**error.result, "completed": journal.done_steps(), "result": str(journal.path)}


def publish(
    *,
    draft_dir: Path,
    sha256: str,
    runner: Runner,
    scanner: Scanner,
    env: Mapping[str, str],
) -> dict[str, object]:
    """承認された案を送る。順序は、案の SHA-256 → 非対話 → 結果の記録 → 秘密情報の検査 → 手順。"""
    try:
        return _publish(draft_dir, sha256, runner, scanner, env)
    except _Stop as stop:
        return stop.result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        print(f"publish_issue: {message}", file=sys.stderr)
        raise SystemExit(2)


def _read_text(path: str) -> str:
    """UTF-8 で読む。改行を変換しない。"""
    try:
        return Path(path).read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise PublishError(f"cannot read {path}: {error.__class__.__name__}") from None


def _read_metadata(path: str | None) -> BaseModel | None:
    if path is None:
        return None
    try:
        return fmt.IssueMetadata.model_validate_json(_read_text(path))
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors(include_input=False)
        )
        raise PublishError(f"{path} is not valid metadata ({problems})") from None


def _read_json_object(path: str) -> dict[str, object]:
    try:
        parsed: object = json.loads(_read_text(path))
    except ValueError:
        raise PublishError(f"{path} is not valid JSON") from None
    mapping = _mapping(parsed)
    if mapping is None:
        raise PublishError(f"{path} is not a JSON object")
    return dict(mapping)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="publish_issue.py", description="Draft, scan and publish an issue for issue-authoring.")
    commands = parser.add_subparsers(dest="command", required=True)
    draft = commands.add_parser("draft", help="save a draft (reads GitHub, writes nothing to it)")
    kinds = draft.add_subparsers(dest="kind", required=True)

    def common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--repo", required=True, metavar="OWNER/NAME")
        sub.add_argument("--body-file", required=True)
        sub.add_argument("--out-dir", required=True)

    create = kinds.add_parser("create", help="draft a new issue")
    common(create)
    create.add_argument("--title", required=True)
    create.add_argument("--metadata-file")
    create.add_argument("--label", action="append", default=[], dest="labels")
    create.add_argument("--parent")
    create.add_argument("--blocked-by", action="append", default=[], dest="blocked_by")

    update = kinds.add_parser("update", help="draft an update of an issue")
    common(update)
    update.add_argument("--issue", required=True, type=int)
    update.add_argument("--read-json", required=True)
    update.add_argument("--metadata-file")
    update.add_argument("--title")
    update.add_argument("--add-label", action="append", default=[], dest="add_labels")
    update.add_argument("--remove-label", action="append", default=[], dest="remove_labels")

    comment = kinds.add_parser("comment", help="draft a comment")
    common(comment)
    comment.add_argument("--issue", required=True, type=int)

    send = commands.add_parser("publish", help="send an approved draft")
    send.add_argument("--draft", required=True)
    send.add_argument("--sha256", required=True)
    return parser


def _dispatch(args: argparse.Namespace) -> dict[str, object]:
    if args.command == "publish":
        return publish(
            draft_dir=Path(args.draft), sha256=args.sha256, runner=run_process, scanner=Scanner(), env=os.environ
        )
    body = _read_text(args.body_file)
    out_dir = Path(args.out_dir)
    if args.kind == "create":
        return draft_create(
            repo=args.repo,
            title=args.title,
            body=body,
            metadata=_read_metadata(args.metadata_file),
            labels=args.labels,
            parent=args.parent,
            blocked_by=args.blocked_by,
            out_dir=out_dir,
            runner=run_process,
            scanner=Scanner(),
        )
    if args.kind == "update":
        return draft_update(
            repo=args.repo,
            issue=args.issue,
            read_json=_read_json_object(args.read_json),
            body=body,
            metadata=_read_metadata(args.metadata_file),
            title=args.title,
            add_labels=args.add_labels,
            remove_labels=args.remove_labels,
            out_dir=out_dir,
            runner=run_process,
            scanner=Scanner(),
        )
    return draft_comment(
        repo=args.repo, issue=args.issue, body=body, out_dir=out_dir, runner=run_process, scanner=Scanner()
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_request:
        return exit_request.code if isinstance(exit_request.code, int) else 0
    try:
        result = _dispatch(args)
    except PublishError as error:
        print(f"publish_issue: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in OK_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
