"""issue-to-pr の Spec を、--spec-review で指定した担当にレビューさせる。

check・review は --spec-review で指定した担当だけを使い、設定だけでは担当を選ばない（設定の fallback は保つ）。
check は設定（雛形 < 個人設定）と指定の担当を検査し、worktree・runner・GitHub に触れない。
review は Spec の写しと依頼文を SESSION の下の新しい runner-dir に記録し、外部の担当なら runner で依頼して
結果を検証・記録する。self なら依頼文のパスを返し、submit がその結果を外部と同じ形・対応・版の検証を通して記録する。
decide は司令塔の採否を検証して記録し、次工程（plan・rereview・stop）を返す。
cleanup は runner の worktree と出力先を片付ける。記録は LEDGER_ROOT/<spec-stem>.spec-review/review-<k>/ に置き、消さない。
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agent_runner import Config, ConfigError, RunnerError, load_config, run_workflow  # noqa: E402
from tools.agent_runner.adapters import Adapter, load_adapter  # noqa: E402
from tools.agent_runner.checkout_policy import require_auditable_workflow  # noqa: E402
from tools.agent_runner.models import Assignment, BatchResult  # noqa: E402
from tools.agent_runner.workspace import CheckoutAuditError  # noqa: E402


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # pydantic のモデルが前方参照を自分のモジュールで解決できるように、実行の前に登録する
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# 設定の投影・git の読み取り・試行の worktree の後片付けは implement_task.py と同じ規則を使う
implement = _load_module("issue_review_spec_implement_task", Path(__file__).with_name("implement_task.py"))

WORKFLOW = "issue"
ROLE = "spec-review"
SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
REVIEW_DIR = re.compile(r"review-([1-9][0-9]*)")


class ReviewInputError(ValueError):
    """review_spec 自身の入力の誤り。文は値・パスを含まない固定の文で、そのまま出す。"""


# --- 依頼・結果・採否の形 -----------------------------------------------------------------------------------------


def _text(value: str) -> str:
    if not value.strip() or "\x00" in value:
        raise ValueError("must be nonblank text without NUL")
    return value


Text = Annotated[str, AfterValidator(_text)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class IssueRef(_Strict):
    """resolve_issue.py の出力の該当項目。"""

    repo: Text
    number: int = Field(gt=0)
    url: Text
    title: Text
    body: str


class ReviewRequest(_Strict):
    """司令塔が作る依頼の JSON。context は Issue のコメントの要点・適用される規則など、レビューに要る文脈。"""

    spec_path: str
    repository: str
    revision: str
    issue: IssueRef
    context: Text

    @field_validator("spec_path", "repository")
    @classmethod
    def _absolute(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("must be an absolute path")
        return value

    @field_validator("revision")
    @classmethod
    def _revision(cls, value: str) -> str:
        if SHA.fullmatch(value) is None:
            raise ValueError("must be a full lowercase commit hash")
        return value


class Finding(_Strict):
    id: Identifier
    section: Text
    problem: Text
    evidence: Text
    impact: Text
    severity: Literal["important", "minor"]
    suggestion: Text


class ReviewResult(_Strict):
    """担当が返す JSON。completed で findings が空なら指摘 0 件、incomplete は未完了（レビュー失敗）。"""

    review_id: str
    spec_sha256: str
    status: Literal["completed", "incomplete"]
    findings: list[Finding]
    incomplete: list[Text]

    @model_validator(mode="after")
    def _consistent(self) -> ReviewResult:
        identifiers = [finding.id for finding in self.findings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("finding ids must be unique")
        if (self.status == "completed") == bool(self.incomplete):
            raise ValueError("incomplete must be empty exactly when status is completed")
        return self


class Decision(_Strict):
    id: Identifier
    decision: Literal["adopt", "reject", "needs_judgment"]
    reason: Text
    reflected_in: Text | None

    @model_validator(mode="after")
    def _reflected(self) -> Decision:
        if self.decision == "adopt" and self.reflected_in is None:
            raise ValueError("an adopted finding needs reflected_in")
        return self


class Decisions(_Strict):
    decisions: list[Decision]


# --- レビューの種類・設定 -----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Kind:
    """役割に依らない部分を使い回すための、レビューの種類ごとの違い。

    result はモデルのクラスで、インスタンスが review_id・spec_sha256・status を持つ。
    counted は要約に件数を出す result の項目名、scalars は要約にそのまま写す result の項目名。
    """

    role: str
    suffix: str
    result: type[Any]
    counted: str
    scalars: tuple[str, ...] = ()


SPEC_REVIEW = Kind(role=ROLE, suffix=".spec-review", result=ReviewResult, counted="findings")


def load(template: Path, config: Path | None, agent: str, kind: Kind = SPEC_REVIEW) -> Config:
    """雛形 < 個人設定で読み込み、担当を agent に置き換えて kind.role（writes = false）だけに投影する。"""
    loaded = load_config(
        template, implement.personal_config(config), assignments={kind.role: [agent]}, workflow=WORKFLOW
    )
    projected: Config = implement.project(loaded, kind.role, writes=False)
    return projected


def assignment_of(config: Config, kind: Kind = SPEC_REVIEW) -> Assignment:
    return config.workflows[WORKFLOW].assignments[kind.role]


def check(template: Path, config: Path | None, agent: str, kind: Kind = SPEC_REVIEW) -> dict[str, Any]:
    assignment = assignment_of(load(template, config, agent, kind), kind)
    personal: Path | None = implement.personal_config(config)
    return {
        "status": "ok",
        "assignment": assignment.model_dump(mode="json"),
        "self": assignment.agents == ["self"],
        "template": str(template),
        "config": str(personal) if personal is not None else None,
    }


RESULT_SHAPE = json.dumps(
    {
        "review_id": "<the review_id below>",
        "spec_sha256": "<the spec_sha256 below>",
        "status": "completed | incomplete",
        "findings": [
            {
                "id": "S1",
                "section": "<Spec section>",
                "problem": "<problem>",
                "evidence": "<evidence: Issue text, repository file:line, or Spec text>",
                "impact": "<what goes wrong in the plan or the implementation>",
                "severity": "important | minor",
                "suggestion": "<concrete change to the Spec>",
            }
        ],
        "incomplete": ["<why you could not finish>"],
    },
    ensure_ascii=False,
)


def compose_prompt(
    request: ReviewRequest,
    *,
    review_id: str,
    round_: int,
    spec_text: str,
    spec_sha256: str,
    previous: dict[str, Any] | None,
) -> str:
    """担当への依頼文（self の司令塔も同じ文を読む）。runner はこの前に作業範囲の指示（writes=False）を付ける。"""
    begin, end = f"----- BEGIN SPEC {review_id} -----", f"----- END SPEC {review_id} -----"
    lines = [
        "You are reviewing a design Spec before an implementation plan is written from it. You will not be able to "
        "talk to the person who wrote it. Do not modify any file, do not start other agents or subagents, and do "
        "not write to GitHub.",
        "",
        "The Spec is NOT in this worktree: its full text is between the BEGIN/END lines below. Its path is only a "
        "record of where it is kept. The worktree is the target repository at the revision below; read it to check "
        "what the Spec says about the existing code and rules.",
        "",
        "Report only problems that matter for planning and building it:",
        "- requirements of the Issue that the Spec misses or changes",
        "- contradictions inside the Spec",
        "- acceptance criteria that are missing or cannot be checked",
        "- statements that disagree with the existing code or the repository rules",
        "- scope beyond the Issue",
        "- places where a talented builder would still have to guess before planning, and a wrong guess would "
        "matter; rank these by importance",
        "Skip wording preferences, details the Spec explicitly leaves to the builder, and anything a builder could "
        "reasonably decide alone.",
        "",
        "severity: important = the plan would be wrong, or the builder would have to guess in a way that matters; "
        "minor = worth fixing, but a sensible builder could settle it.",
        "",
        'If you could not finish (missing context, unreadable input), return "status": "incomplete" with the reasons '
        'in "incomplete"; never return an empty findings list for an unfinished review. If nothing that matters is '
        "left, return \"status\": \"completed\" with an empty findings list.",
        "",
        "Return exactly one JSON object with exactly these keys (write problem, evidence, impact and suggestion in "
        "Japanese):",
        RESULT_SHAPE,
        "",
        f"review_id: {review_id}",
        f"spec_sha256: {spec_sha256}",
        f"round: {round_}",
        f"repository: {request.repository}",
        f"issue repository: {request.issue.repo}",
        f"issue: #{request.issue.number} {request.issue.url}",
        f"issue title: {request.issue.title}",
        f"revision: {request.revision}",
        f"spec path (record only): {request.spec_path}",
        "",
        "Issue body:",
        request.issue.body,
        "",
        "Context from the caller:",
        request.context,
    ]
    if previous is not None:
        lines += [
            "",
            f"This is round {round_}: a re-review after the caller applied its decisions on the previous review. "
            "Report only problems that remain or that the changes introduced. Report a finding that was rejected "
            "with a reason again only when that reason is wrong.",
            "Previous findings and decisions:",
            json.dumps(previous["decisions"], ensure_ascii=False),
            "Changes from the previously reviewed version to this version (unified diff):",
            previous["diff"],
        ]
    lines += ["", begin, spec_text, end]
    return "\n".join(lines)


# --- 保存先 -------------------------------------------------------------------------------------------------------


def resolve_ledger_root(explicit: Path | None) -> Path:
    """--ledger-dir または環境変数 SESSION。未設定・相対パスは推測せず拒否する。"""
    if explicit is not None:
        path = explicit
    else:
        value = os.environ.get("SESSION")
        if not value:
            raise ReviewInputError("--ledger-dir or the SESSION environment variable is required")
        path = Path(value)
    if not path.is_absolute():
        raise ReviewInputError("the ledger directory must be an absolute path")
    return path.expanduser().resolve(strict=False)


def review_ledger(spec_path: Path, kind: Kind, ledger_root: Path) -> Path:
    """レビューの履歴は Spec の隣ではなく、明示された外部の LEDGER_ROOT の下に置く。"""
    return ledger_root / f"{spec_path.stem}{kind.suffix}"


# 互換のための別名（呼び出し側は review_ledger を使う）
ledger_dir = review_ledger


def _real(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _overlaps(first: Path, second: Path) -> bool:
    return _within(first, second) or _within(second, first)


def _checkout_root(path: Path) -> Path | None:
    """path を含む Git の worktree（DOC_ROOT）。Git の外なら None。"""
    try:
        output = implement._git(path, "rev-parse", "--show-toplevel").stdout
    except (subprocess.SubprocessError, OSError):
        return None
    if not output.strip():
        return None
    return _real(Path(os.fsdecode(output.rstrip(b"\n"))))


def _check_storage(
    spec_path: Path,
    repository: Path,
    ledger_root: Path,
    ledger: Path,
    runner_dir: Path | None,
) -> None:
    """ledger と runner の記録を、コードと Spec のどちらの worktree にも置かず、互いを消し得る包含も拒否する。"""
    protected = [root for root in (_checkout_root(repository), _checkout_root(spec_path.parent)) if root is not None]
    for candidate in (ledger_root, ledger):
        if any(_within(_real(candidate), root) for root in protected):
            raise ReviewInputError("review records must be outside the code and Spec worktrees")
    if ledger.is_symlink():
        raise ReviewInputError("the review ledger must not be a symbolic link")
    if ledger.exists() and not ledger.is_dir():
        raise ReviewInputError("the review ledger must be a directory")
    if runner_dir is not None:
        if runner_dir.exists() or runner_dir.is_symlink():
            raise ReviewInputError("runner directory must be new")
        real_runner = _real(runner_dir)
        if any(_overlaps(real_runner, root) for root in protected):
            raise ReviewInputError("the runner directory must be outside the code and Spec worktrees")
        if _overlaps(real_runner, _real(ledger)):
            raise ReviewInputError("the runner directory and the review ledger must not contain each other")


def _read_spec(path: Path) -> bytes:
    """バイト列のまま読む（read_text は CRLF を LF に変える）。UTF-8 の空でない文書だけを受け付ける。"""
    if path.is_symlink() or not path.is_file():
        raise ReviewInputError("spec_path must be a regular file")
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ReviewInputError("the Spec is not UTF-8") from None
    if not text.strip():
        raise ReviewInputError("the Spec is empty")
    return data


# --- 記録 ---------------------------------------------------------------------------------------------------------


def _indexed(ledger: Path) -> list[tuple[int, Path]]:
    """review-<k> を k の順に返す。"""
    if not ledger.is_dir() or ledger.is_symlink():
        return []
    found: list[tuple[int, Path]] = []
    for path in ledger.iterdir():
        match = REVIEW_DIR.fullmatch(path.name)
        if match is not None and path.is_dir() and not path.is_symlink():
            found.append((int(match.group(1)), path))
    return sorted(found)


def _reviews(ledger: Path) -> list[Path]:
    return [path for _, path in _indexed(ledger)]


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, data: object) -> None:
    """記録は上書きしない（既にあれば FileExistsError）。"""
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _write_new_bytes(path: Path, data: bytes) -> None:
    """反映後の snapshot も上書きしない。"""
    with path.open("xb") as stream:
        stream.write(data)


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _elapsed(since: str) -> float:
    return max(0.0, (datetime.datetime.now(datetime.UTC) - datetime.datetime.fromisoformat(since)).total_seconds())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stop_unconfirmed(record: dict[str, Any]) -> bool:
    """停止を確かめられていない試行があるか。

    runner が戻らなかった外部実行は、どの試行が動いているか分からないので停止未確認として扱う。
    結果の無い失敗を単なる failed として読み飛ばし、旧担当が動いたまま次のレビューを始めない。
    """
    if record["stop_unconfirmed"]:
        return True
    return record["mode"] == "external" and record.get("batch") is None


def next_round(ledger: Path, kind: Kind = SPEC_REVIEW) -> int:
    """何回目のレビューかを決める。始められなければ ReviewInputError。失敗したレビューは数えない。"""
    round_ = 1
    for review_dir in _reviews(ledger):
        if not (review_dir / "review.json").is_file():
            raise ReviewInputError(
                "a review without a result exists: submit the self review, or confirm that its runner stopped"
            )
        record = _read(review_dir / "review.json")
        if _stop_unconfirmed(record):
            raise ReviewInputError("a previous review has attempts whose stop is not confirmed")
        if record["state"] != "completed":
            continue
        request = _read(review_dir / "request.json")
        try:
            result = kind.result.model_validate(record["result"])
        except ValidationError:
            raise ReviewInputError("a completed review has an invalid result record") from None
        if (result.review_id, result.spec_sha256) != (request["review_id"], request["spec_sha256"]):
            raise ReviewInputError("a completed review does not match its request")
        if result.status != "completed":
            raise ReviewInputError("a completed review record has an incomplete result")
        if not (review_dir / "decisions.json").is_file():
            raise ReviewInputError("record the decisions on the completed review first")
        if _read(review_dir / "decisions.json")["next"] != "rereview":
            raise ReviewInputError("the review gate is already closed (plan or stop)")
        round_ = request["round"] + 1
    if round_ > 2:
        raise ReviewInputError("only one re-review is allowed")
    return round_


def _new_review_dir(ledger: Path) -> Path:
    if ledger.is_symlink():
        raise ReviewInputError("the review ledger must not be a symbolic link")
    ledger.mkdir(parents=True, exist_ok=True)
    last = max((index for index, _ in _indexed(ledger)), default=0)
    review_dir = ledger / f"review-{last + 1}"
    review_dir.mkdir()
    return review_dir


def _summary(review_dir: Path, record: dict[str, Any], kind: Kind = SPEC_REVIEW) -> dict[str, Any]:
    result = record["result"]
    request = _read(review_dir / "request.json")
    scalars = {name: result[name] if result is not None else None for name in kind.scalars}
    return {
        "state": record["state"],
        "reasons": record["reasons"],
        "review_dir": str(review_dir),
        "review_id": request["review_id"],
        "spec_sha256": request["spec_sha256"],
        "round": request["round"],
        **scalars,
        kind.counted: len(result[kind.counted]) if result is not None else None,
        "mode": record["mode"],
        "requested_agent": record["requested_agent"],
        "actual_agent": record["actual_agent"],
        "identity": record["identity"],
        "elapsed_seconds": record["elapsed_seconds"],
        "outside_changes": record["outside_changes"],
        "unprotected_changes": record["unprotected_changes"],
    }


# --- review・submit -----------------------------------------------------------------------------------------------


def _check_repository(repository: Path, revision: str) -> None:
    try:
        current: str = implement.head(repository)
    except (subprocess.SubprocessError, OSError):
        raise ReviewInputError("repository is not a readable git checkout") from None
    if current != revision:
        raise ReviewInputError("revision must be the current HEAD of repository")


def start(
    kind: Kind,
    config: Config,
    request: ReviewRequest,
    runner_dir: Path | None,
    *,
    ledger_root: Path,
    admit: Callable[[Path, Assignment, Path], int],
    compose: Callable[[str, int, str, str], str],
    adapter_loader: Callable[[str], Adapter] = load_adapter,
) -> dict[str, Any]:
    """記録を作る前の検査をすべて済ませてから、写しと依頼文を記録する。self なら依頼文のパスを返す。

    admit は始められるかを決め（拒否は ReviewInputError）、何回目かを返す。
    compose は (review_id, 回数, Spec の全文, Spec の SHA-256) から依頼文を作る。
    """
    selected: Config = implement.project(config, kind.role, writes=False)
    assignment = assignment_of(selected, kind)
    is_self = assignment.agents == ["self"]
    spec_path = Path(request.spec_path)
    spec_bytes = _read_spec(spec_path)
    spec_sha256 = _sha256(spec_bytes)
    repository = Path(request.repository)
    _check_repository(repository, request.revision)
    ledger = review_ledger(spec_path, kind, ledger_root)
    _check_storage(spec_path, repository, ledger_root, ledger, None if is_self else runner_dir)
    if not is_self and runner_dir is not None:
        # 保存するパスも実パスにそろえ、cleanup が別の場所を消さないようにする
        runner_dir = _real(runner_dir)
    round_ = admit(spec_path, assignment, ledger_root)
    if not is_self:
        if runner_dir is None:
            raise ReviewInputError("an external review needs --runner-dir")
        require_auditable_workflow(selected, WORKFLOW, repository, adapter_loader=adapter_loader)
    review_id = uuid.uuid4().hex
    prompt = compose(review_id, round_, spec_bytes.decode("utf-8"), spec_sha256)
    review_dir = _new_review_dir(ledger)
    _write_new(
        review_dir / "request.json",
        {
            "request": request.model_dump(mode="json"),
            "review_id": review_id,
            "round": round_,
            "spec_sha256": spec_sha256,
            "created_at": _now(),
            "assignment": assignment.model_dump(mode="json"),
            "mode": "self" if is_self else "external",
            "kind": kind.role,
            "ledger_root": str(ledger_root),
            "ledger_dir": str(ledger),
            "runner_dir": str(runner_dir) if runner_dir is not None and not is_self else None,
        },
    )
    (review_dir / "spec.md").write_bytes(spec_bytes)
    (review_dir / "prompt.txt").write_bytes(prompt.encode("utf-8"))
    if is_self:
        return {
            "state": "self",
            "review_dir": str(review_dir),
            "prompt_path": str(review_dir / "prompt.txt"),
            "review_id": review_id,
            "spec_sha256": spec_sha256,
            "round": round_,
        }
    assert runner_dir is not None
    expected = (review_id, spec_sha256)

    def matches(payload: object) -> bool:
        try:
            result = kind.result.model_validate(payload)
        except ValidationError:
            return False
        return (result.review_id, result.spec_sha256) == expected

    # ここからは記録がある。どの失敗も review.json に残し、結果の無い記録を残さない
    try:
        batch = run_workflow(
            selected,
            WORKFLOW,
            prompt,
            repository,
            revision=request.revision,
            concurrency=1,
            output_dir=runner_dir,
            adapter_loader=adapter_loader,
            payload_check=matches,
        )
    except Exception as error:
        record = _record(
            "external",
            reasons=[f"the runner did not finish: {failure_reason(error)}"],
            elapsed_seconds=_elapsed(_read(review_dir / "request.json")["created_at"]),
        )
        _write_new(review_dir / "review.json", record)
        return _summary(review_dir, record, kind)
    reasons, result = assess(batch, repository, spec_path, request.revision, expected, kind)
    try:
        current_revision = implement.head(repository)
    except (subprocess.SubprocessError, OSError):
        reasons.append("the repository cannot be read after the review")
    else:
        if current_revision != request.revision:
            reasons.append("the repository changed during the review")
    outcome = batch.results[0] if len(batch.results) == 1 else None
    attempts = [attempt for item in batch.results for attempt in item.attempts]
    record = _record(
        "external",
        reasons=reasons,
        elapsed_seconds=batch.elapsed_seconds,
        requested_agent=outcome.requested_agent if outcome is not None else None,
        actual_agent=outcome.actual_agent if outcome is not None else None,
        identity=attempts[-1].identity.model_dump(mode="json") if attempts else None,
        attempts=[
            {
                "agent_id": attempt.agent_id,
                "state": attempt.state,
                "elapsed_seconds": attempt.elapsed_seconds,
                "stop_confirmed": attempt.stop_confirmed,
                "exit_code": attempt.exit_code,
                "work_dir": str(attempt.work_dir) if attempt.work_dir is not None else None,
            }
            for attempt in attempts
        ],
        stop_unconfirmed=[attempt.agent_id for attempt in attempts if not attempt.stop_confirmed],
        outside_changes=batch.outside_changes,
        unprotected_changes=batch.unprotected_changes,
        result=result.model_dump(mode="json") if result is not None else None,
        batch=batch.model_dump(mode="json"),
    )
    _write_new(review_dir / "review.json", record)
    return _summary(review_dir, record, kind)


def review(
    config: Config,
    request: ReviewRequest,
    runner_dir: Path | None,
    *,
    ledger_dir: Path | None = None,
    adapter_loader: Callable[[str], Adapter] = load_adapter,
) -> dict[str, Any]:
    """Spec レビューを始める。再レビューは 1 回まで、同じ担当で行う。"""
    ledger_root = resolve_ledger_root(ledger_dir)

    def admit(spec_path: Path, assignment: Assignment, root: Path) -> int:
        ledger = review_ledger(spec_path, SPEC_REVIEW, root)
        round_ = next_round(ledger)
        if round_ > 1 and _read(_last_decided(ledger) / "request.json")["assignment"] != assignment.model_dump(
            mode="json"
        ):
            raise ReviewInputError("a re-review must use the same assignment as the first review")
        return round_

    def compose(review_id: str, round_: int, spec_text: str, spec_sha256: str) -> str:
        ledger = review_ledger(Path(request.spec_path), SPEC_REVIEW, ledger_root)
        return compose_prompt(
            request,
            review_id=review_id,
            round_=round_,
            spec_text=spec_text,
            spec_sha256=spec_sha256,
            previous=_previous(ledger, spec_text.encode("utf-8")) if round_ > 1 else None,
        )

    return start(
        SPEC_REVIEW,
        config,
        request,
        runner_dir,
        ledger_root=ledger_root,
        admit=admit,
        compose=compose,
        adapter_loader=adapter_loader,
    )


def _record(
    mode: Literal["self", "external"], *, reasons: list[str], elapsed_seconds: float, **fields: Any
) -> dict[str, Any]:
    """review.json の形。外部実行で runner が戻らなかったときは batch・attempts を空のまま書く。"""
    record: dict[str, Any] = {
        "state": "failed" if reasons else "completed",
        "reasons": reasons,
        "mode": mode,
        "requested_agent": None,
        "actual_agent": None,
        "identity": None,
        "attempts": [],
        "stop_unconfirmed": [],
        "outside_changes": [],
        "unprotected_changes": [],
        "elapsed_seconds": elapsed_seconds,
        "finished_at": _now(),
        "result": None,
        "batch": None,
    }
    record.update(fields)
    return record


def assess(
    batch: BatchResult,
    repository: Path,
    spec_path: Path,
    revision: str,
    expected: tuple[str, str],
    kind: Kind = SPEC_REVIEW,
) -> tuple[list[str], Any | None]:
    """外部実行の結果を採用できるかを確かめる。理由が 1 つでもあれば採用しない。

    runner の checkout 監査は実行中に作られた試行の worktree を見ないので、停止を確認したすべての試行
    （fallback の前に失敗した一次担当を含む）の worktree を git で読み、writes = false の違反を探す。
    準備の前に終わった試行だけを対象外にし、結果や依頼記録がある試行は worktree が無いと監査できない
    ので採用しない。worktree の分類は implement_task.classify_attempt_worktree と共有し、symlink を
    含むパス、未登録・common-dir 違いのパス、読めないパスは参照先の HEAD/status を読まずに採用しない。
    """
    reasons: list[str] = []
    attempts = [attempt for outcome in batch.results for attempt in outcome.attempts]
    unstopped = [attempt.agent_id for attempt in attempts if not attempt.stop_confirmed]
    if unstopped:
        reasons.append(f"stop_unconfirmed: attempts of {', '.join(unstopped)}; their areas are retained")
    sensitive = [attempt.agent_id for attempt in attempts if attempt.stop_confirmed and attempt.sensitive_paths]
    if sensitive:
        reasons.append(f"sensitive_paths: attempts of {', '.join(sensitive)}; their areas are retained")
    result: Any = None
    if len(batch.results) != 1:
        reasons.append("the runner returned an unexpected number of results")
    elif batch.results[0].state != "success" or not batch.results[0].attempts:
        outcome = batch.results[0]
        reasons.append(f"runner: {outcome.state}{'; fallback exhausted' if outcome.fallback_exhausted else ''}")
    else:
        # runner の payload_check で検査済み。記録の取り違えへの防御として、戻った後にもう一度確かめる
        try:
            result = kind.result.model_validate(batch.results[0].attempts[-1].payload)
        except ValidationError as error:
            reasons.append(f"invalid_result: {_fields(error)}")
        else:
            if (result.review_id, result.spec_sha256) != expected:
                reasons.append("the result does not match the review request")
            if result.status != "completed":
                reasons.append("incomplete: the reviewer could not finish")
    try:
        if _sha256(_read_spec(spec_path)) != expected[1]:
            reasons.append("the Spec changed during the review")
    except (ReviewInputError, OSError):
        reasons.append("the Spec cannot be read after the review")
    if batch.outside_changes:
        reasons.append(f"outside_changes: {', '.join(batch.outside_changes)}")
    for attempt in attempts:
        status = implement.classify_attempt_worktree(repository, attempt)
        if status.kind == "prepare-failed":
            # 準備の前に終わった試行。レビューの結果を持たないので監査対象外
            continue
        if status.kind == "unconfirmed":
            # stop_unconfirmed と sensitive_paths は上で理由にまとめた。領域は監査しない
            continue
        if status.kind != "registered":
            reasons.append(
                f"the worktree of {attempt.agent_id} {status.reason}, so its changes cannot be audited"
            )
            continue
        assert attempt.work_dir is not None
        try:
            moved = implement.head(attempt.work_dir) != revision
            changed = implement.status_paths(attempt.work_dir)
        except (subprocess.SubprocessError, OSError):
            reasons.append(f"the worktree of {attempt.agent_id} cannot be read with git")
            continue
        if moved or changed:
            reasons.append(f"{attempt.agent_id} changed its worktree although the role does not write")
    return reasons, result


def _fields(error: ValidationError) -> str:
    """検査に失敗した項目の位置だけ（値は出さない）。"""
    locations = {
        ".".join(str(part) for part in detail["loc"]) or "(root)"
        for detail in error.errors(include_url=False, include_input=False)
    }
    return ", ".join(sorted(locations))


def _request_of(review_dir: Path, kind: Kind = SPEC_REVIEW) -> dict[str, Any]:
    path = review_dir / "request.json"
    if review_dir.is_symlink() or path.is_symlink() or not path.is_file():
        raise ReviewInputError("review directory must be a real directory with request.json written by review")
    record: dict[str, Any] = _read(path)
    ledger = Path(record["ledger_dir"]).resolve(strict=False)
    if _real(review_dir).parent != ledger or REVIEW_DIR.fullmatch(review_dir.name) is None:
        raise ReviewInputError("review directory is not inside the recorded ledger")
    if record.get("kind") != kind.role:
        raise ReviewInputError("review directory belongs to a different review kind")
    return record


def submit(review_dir: Path, result_path: Path, kind: Kind = SPEC_REVIEW) -> dict[str, Any]:
    """self のレビューの結果を検証して記録する。形・対応の誤りは記録せずに拒否する（直して出し直せる）。"""
    request = _request_of(review_dir, kind)
    if request["mode"] != "self":
        raise ReviewInputError("submit is only for self reviews")
    if (review_dir / "review.json").exists():
        raise ReviewInputError("this review already has a result")
    try:
        result = kind.result.model_validate_json(result_path.read_bytes())
    except ValidationError as error:
        raise ReviewInputError(f"invalid result: {_fields(error)}") from None
    if result.review_id != request["review_id"] or result.spec_sha256 != request["spec_sha256"]:
        raise ReviewInputError("the result does not match the review request")
    reasons: list[str] = []
    if result.status != "completed":
        reasons.append("incomplete: the reviewer could not finish")
    spec_path = Path(request["request"]["spec_path"])
    if _sha256(_read_spec(spec_path)) != request["spec_sha256"]:
        reasons.append("the Spec changed during the review")
    repository = Path(request["request"]["repository"])
    try:
        current_revision = implement.head(repository)
    except (subprocess.SubprocessError, OSError):
        reasons.append("the repository cannot be read after the review")
    else:
        if current_revision != request["request"]["revision"]:
            reasons.append("the repository changed during the review")
    # このセッション自身のレビュー。外部 agent の起動や runner によるモデルの観測は無い（identity は null）
    record = _record(
        "self",
        reasons=reasons,
        elapsed_seconds=_elapsed(request["created_at"]),
        requested_agent="self",
        actual_agent="self",
        result=result.model_dump(mode="json"),
    )
    _write_new(review_dir / "review.json", record)
    return _summary(review_dir, record, kind)


# --- decide・cleanup ----------------------------------------------------------------------------------------------


def decide(review_dir: Path, decisions_path: Path) -> dict[str, Any]:
    """司令塔の採否を検証して記録し、次工程を返す。拒否のときは何も記録しない。

    採用した指摘を Spec に反映した後（Spec に採否の節を書くならそれも済ませた後）に呼ぶ。
    この時点の Spec を反映後の版として記録する。
    """
    request = _request_of(review_dir, SPEC_REVIEW)
    review_path = review_dir / "review.json"
    if not review_path.is_file() or _read(review_path)["state"] != "completed":
        raise ReviewInputError("decisions need a completed review")
    if (review_dir / "decisions.json").exists():
        raise ReviewInputError("this review already has decisions")
    try:
        decisions = Decisions.model_validate_json(decisions_path.read_bytes()).decisions
    except ValidationError as error:
        raise ReviewInputError(f"invalid decisions: {_fields(error)}") from None
    result = ReviewResult.model_validate(_read(review_path)["result"])
    if (result.review_id, result.spec_sha256) != (request["review_id"], request["spec_sha256"]):
        raise ReviewInputError("the recorded result does not match the review request")
    if result.status != "completed":
        raise ReviewInputError("the recorded review is not completed")
    findings = {finding.id: finding for finding in result.findings}
    identifiers = [decision.id for decision in decisions]
    if len(identifiers) != len(set(identifiers)) or set(identifiers) != set(findings):
        raise ReviewInputError("decisions must cover every finding exactly once")
    current = _read_spec(Path(request["request"]["spec_path"]))
    reflected_sha256 = _sha256(current)
    adopted = [decision.id for decision in decisions if decision.decision == "adopt"]
    if adopted and reflected_sha256 == request["spec_sha256"]:
        raise ReviewInputError("adopted findings are not reflected in the Spec")
    judgment = [decision.id for decision in decisions if decision.decision == "needs_judgment"]
    important = [identifier for identifier in adopted if findings[identifier].severity == "important"]
    if judgment:
        next_step, reasons = "stop", [f"needs_judgment: {', '.join(judgment)}"]
    elif request["round"] == 1 and important:
        next_step, reasons = "rereview", [f"important findings adopted: {', '.join(important)}"]
    else:
        next_step, reasons = "plan", []
    _write_new_bytes(review_dir / "reflected.md", current)
    _write_new(
        review_dir / "decisions.json",
        {
            "decisions": [decision.model_dump(mode="json") for decision in decisions],
            "reviewed_spec_sha256": request["spec_sha256"],
            "reflected_spec_sha256": reflected_sha256,
            "decided_at": _now(),
            "next": next_step,
            "reasons": reasons,
        },
    )
    return {
        "next": next_step,
        "reasons": reasons,
        "review_dir": str(review_dir),
        "reviewed_spec_sha256": request["spec_sha256"],
        "reflected_spec_sha256": reflected_sha256,
    }


def _last_decided(ledger: Path) -> Path:
    """採否を記録した最後のレビューの記録。無ければ ReviewInputError。"""
    for review_dir in reversed(_reviews(ledger)):
        if (review_dir / "decisions.json").is_file():
            return review_dir
    raise ReviewInputError("a re-review needs a decided previous review")


def _previous(ledger: Path, spec_bytes: bytes) -> dict[str, Any]:
    """再レビューに渡す、直前の採否のあるレビューの指摘・採否と、その版から今の版への差分。"""
    review_dir = _last_decided(ledger)
    decided = {item["id"]: item for item in _read(review_dir / "decisions.json")["decisions"]}
    findings = _read(review_dir / "review.json")["result"]["findings"]
    reviewed = (review_dir / "spec.md").read_bytes().decode("utf-8")
    diff = difflib.unified_diff(
        reviewed.splitlines(keepends=True),
        spec_bytes.decode("utf-8").splitlines(keepends=True),
        fromfile="previously reviewed",
        tofile="current",
    )
    return {
        "decisions": [{"finding": finding, "decision": decided[finding["id"]]} for finding in findings],
        "diff": "".join(diff),
    }


CLEANUP_RECEIPT = "cleanup.jsonl"


class CleanupEvent(_Strict):
    """review.cleanup が記録する、成功した回収 1 件。既存の結果・採否とは別の追記専用ファイルに置く。"""

    event: Literal["worktree_removed", "runner_dir_removed"]
    review_id: str
    kind: str
    spec_sha256: str
    run_id: str
    runner_dir: str
    path: str
    removed_at: str


def _receipt_path(review_dir: Path) -> Path:
    return review_dir / CLEANUP_RECEIPT


@contextmanager
def _open_cleanup_receipt(path: Path, flags: int) -> Iterator[int]:
    """回収記録を開き、ledger 内の専用の regular file か確かめる。

    symlink をたどらず、hardlink など共有された実体は読み書きしない。追記側も同じ確認をする。
    """
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    descriptor = os.open(path, flags, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ReviewInputError("the cleanup receipt is not a private regular file")
        yield descriptor
    finally:
        os.close(descriptor)


def _read_cleanup_events(
    review_dir: Path,
    request: dict[str, Any],
    kind: Kind,
    batch: BatchResult,
    runner_dir: Path,
) -> list[CleanupEvent]:
    """回収記録を読み、このレビュー・batch・runner 領域に結び付いた記録だけを受け付ける。

    記録の破損・symlink/hardlink・対応不一致は、worktree や runner 出力を消す前に拒否する。
    """
    path = _receipt_path(review_dir)
    try:
        with _open_cleanup_receipt(path, os.O_RDONLY) as descriptor:
            data = bytearray()
            while chunk := os.read(descriptor, 65536):
                data.extend(chunk)
    except FileNotFoundError:
        return []
    except OSError:
        raise ReviewInputError("the cleanup receipt cannot be read") from None
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        raise ReviewInputError("the cleanup receipt cannot be read") from None
    paths = {
        str(attempt.work_dir)
        for outcome in batch.results
        for attempt in outcome.attempts
        if attempt.work_dir is not None
    }
    events: list[CleanupEvent] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            event = CleanupEvent.model_validate_json(line)
        except ValidationError:
            raise ReviewInputError("the cleanup receipt is invalid") from None
        if (
            event.review_id != request["review_id"]
            or event.kind != kind.role
            or event.spec_sha256 != request["spec_sha256"]
            or event.run_id != batch.run_id
            or event.runner_dir != str(runner_dir)
        ):
            raise ReviewInputError("the cleanup receipt does not match this review")
        if event.event == "worktree_removed":
            if event.path not in paths:
                raise ReviewInputError("the cleanup receipt names a path outside this batch")
        elif event.path != str(runner_dir):
            raise ReviewInputError("the cleanup receipt names another runner directory")
        events.append(event)
    return events


def _append_cleanup_event(review_dir: Path, event: CleanupEvent) -> None:
    """回収記録を 1 行追記する。既存の記録は差し替えず、共有された実体には書かない。"""
    path = _receipt_path(review_dir)
    line = json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n"
    try:
        with _open_cleanup_receipt(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT) as descriptor:
            data = line.encode("utf-8")
            while data:
                written = os.write(descriptor, data)
                if written <= 0:
                    raise OSError("short write")
                data = data[written:]
            os.fsync(descriptor)
    except OSError:
        raise ReviewInputError("the cleanup receipt cannot be written") from None


def _cleanup_event(
    request: dict[str, Any],
    kind: Kind,
    batch: BatchResult,
    runner_dir: Path,
    event: Literal["worktree_removed", "runner_dir_removed"],
    path: Path,
) -> CleanupEvent:
    return CleanupEvent(
        event=event,
        review_id=request["review_id"],
        kind=kind.role,
        spec_sha256=request["spec_sha256"],
        run_id=batch.run_id,
        runner_dir=str(runner_dir),
        path=str(path),
        removed_at=_now(),
    )


def cleanup(review_dir: Path, kind: Kind = SPEC_REVIEW) -> dict[str, Any]:
    """外部実行の runner の worktree の登録を外し、何も残らなければ runner の出力先を消す。記録は消さない。

    回収の成功は review_dir の追記専用の cleanup.jsonl に残す。同じ cleanup の再実行は記録済みの
    worktree と runner 領域を no-op にし、回収後に再出現した path は保持する。記録が壊れている・
    このレビューと対応しないときは、何も消す前に拒否する。
    """
    request = _request_of(review_dir, kind)
    if request["mode"] == "self":
        return {"removed_worktrees": [], "retained": [], "removed_runner_dir": False}
    if not (review_dir / "review.json").is_file():
        raise ReviewInputError("the review has no result: confirm that its runner stopped before cleaning up")
    record = _read(review_dir / "review.json")
    runner_dir = Path(request["runner_dir"])
    if record["batch"] is None:
        # runner が戻らなかった。中身を確かめられないので消さない
        present = runner_dir.exists() or runner_dir.is_symlink()
        retained = (
            [{"path": str(runner_dir), "reason": "the runner did not finish; check it by hand"}] if present else []
        )
        return {"removed_worktrees": [], "retained": retained, "removed_runner_dir": False}
    batch = BatchResult.model_validate_json(json.dumps(record["batch"]))
    repository = Path(request["request"]["repository"])
    spec_path = Path(request["request"]["spec_path"])
    events = _read_cleanup_events(review_dir, request, kind, batch, runner_dir)
    collected = {event.path for event in events if event.event == "worktree_removed"}
    runner_collected = any(event.event == "runner_dir_removed" for event in events)

    def append_event(event: Literal["worktree_removed", "runner_dir_removed"], path: Path) -> None:
        _append_cleanup_event(review_dir, _cleanup_event(request, kind, batch, runner_dir, event, path))

    if runner_collected:
        # 既に回収した runner 領域の再実行は no-op。再出現した path だけを保持の理由にする
        retained: list[dict[str, str]] = []
        if runner_dir.exists() or runner_dir.is_symlink():
            retained.append(
                {"path": str(runner_dir), "reason": "the runner directory reappeared after it was collected"}
            )
        for attempt in (attempt for outcome in batch.results for attempt in outcome.attempts):
            status = implement.classify_attempt_worktree(repository, attempt, collected=collected)
            if status.kind in {"prepare-failed", "collected"}:
                continue
            reason = status.reason or "the worktree still exists after the runner directory was collected"
            retained.append(
                {
                    "path": implement.retained_path(attempt, batch, parent=status.kind == "unconfirmed"),
                    "reason": reason,
                }
            )
        return {"removed_worktrees": [], "retained": retained, "removed_runner_dir": False}

    removed, retained = implement.remove_attempts(
        repository,
        batch,
        collected=collected,
        on_removed=lambda path: append_event("worktree_removed", path),
    )
    ledger = _real(Path(request["ledger_dir"]))
    resolved = _real(runner_dir)
    protected = [
        root for root in (_checkout_root(repository), _checkout_root(spec_path.parent)) if root is not None
    ]
    if (
        runner_dir.is_symlink()
        or resolved != runner_dir
        or _overlaps(resolved, ledger)
        or any(_overlaps(resolved, root) for root in protected)
    ):
        retained.append({"path": str(runner_dir), "reason": "the runner directory changed; check it by hand"})
    removed_runner_dir = False
    if not retained:
        if not runner_dir.exists() and not runner_dir.is_symlink():
            retained.append({"path": str(runner_dir), "reason": "the runner directory is missing; check it by hand"})
        elif not runner_dir.is_dir() or runner_dir.is_symlink():
            retained.append(
                {"path": str(runner_dir), "reason": "the runner directory is not a real directory; check it by hand"}
            )
        else:
            try:
                shutil.rmtree(runner_dir)
            except OSError:
                retained.append(
                    {"path": str(runner_dir), "reason": "the runner directory could not be removed; check it by hand"}
                )
            else:
                try:
                    append_event("runner_dir_removed", runner_dir)
                except ReviewInputError:
                    retained.append(
                        {
                            "path": str(runner_dir),
                            "reason": "the runner directory was removed but its cleanup receipt could not be written; check it by hand",
                        }
                    )
                else:
                    removed_runner_dir = True
    return {"removed_worktrees": removed, "retained": retained, "removed_runner_dir": removed_runner_dir}


# --- CLI ----------------------------------------------------------------------------------------------------------


def failure_reason(error: Exception) -> str:
    if isinstance(error, ReviewInputError):
        return str(error)
    if isinstance(error, ConfigError):
        return f"config: {error.category}"
    if isinstance(error, RunnerError):
        return f"runner: {error.category}"
    return type(error).__name__


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    """check と review が同じ定義で受け付ける設定の引数。"""
    parser.add_argument(
        "--spec-review",
        metavar="AGENT",
        required=True,
        help="その run の Spec レビューの担当（agent-runner の agent 名か self）。設定だけでは担当を選ばない",
    )
    parser.add_argument("--template", type=Path, default=implement.DEFAULT_TEMPLATE)
    parser.add_argument(
        "--config", type=Path, help="個人設定（既定は AGENT_RUNNER_CONFIG・XDG_CONFIG_HOME・~/.config）"
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="review_spec.py", description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    _add_config_arguments(commands.add_parser("check", help="設定だけを検査する（worktree・runner に触れない）"))
    launch = commands.add_parser("review", help="Spec のレビューを記録し、外部の担当なら runner で依頼する")
    launch.add_argument("--request", type=Path, required=True, help="ReviewRequest の JSON")
    launch.add_argument("--runner-dir", type=Path, help="runner の出力先（外部の担当のとき。存在しないパス）")
    launch.add_argument(
        "--ledger-dir", type=Path, help="レビュー記録のルート（既定は環境変数 SESSION。未設定なら拒否する）"
    )
    _add_config_arguments(launch)
    submitted = commands.add_parser("submit", help="self のレビューの結果を検証して記録する")
    submitted.add_argument("--review-dir", type=Path, required=True)
    submitted.add_argument("--result", type=Path, required=True, help="ReviewResult の JSON")
    decided = commands.add_parser("decide", help="採否を検証して記録し、次工程を返す")
    decided.add_argument("--review-dir", type=Path, required=True)
    decided.add_argument("--decisions", type=Path, required=True, help="Decisions の JSON")
    commands.add_parser("cleanup", help="runner の worktree の登録を外し、出力先を片付ける").add_argument(
        "--review-dir", type=Path, required=True
    )
    return root


def _error(reason: str, **extra: object) -> int:
    print(json.dumps({"status": "error", "reason": reason, **extra}, ensure_ascii=False))
    return 2


def read_request(path: Path) -> ReviewRequest:
    try:
        return ReviewRequest.model_validate_json(path.read_bytes())
    except ValidationError as error:
        raise ReviewInputError(f"invalid request: {_fields(error)}") from None


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "check":
            config = args.config.resolve() if args.config else None
            payload = check(args.template.resolve(), config, args.spec_review)
            code = 0
        elif args.command == "review":
            config = args.config.resolve() if args.config else None
            runner_dir = args.runner_dir.absolute() if args.runner_dir else None
            payload = review(
                load(args.template.resolve(), config, args.spec_review),
                read_request(args.request),
                runner_dir,
                ledger_dir=args.ledger_dir,
            )
            code = 0 if payload["state"] in {"self", "completed"} else 1
        elif args.command == "submit":
            payload = submit(args.review_dir.absolute(), args.result)
            code = 0 if payload["state"] == "completed" else 1
        elif args.command == "decide":
            payload = decide(args.review_dir.absolute(), args.decisions)
            code = 1 if payload["next"] == "stop" else 0
        else:
            payload = cleanup(args.review_dir.absolute())
            code = 1 if payload["retained"] else 0
    except CheckoutAuditError as error:
        return _error(
            "checkout_audit: registered checkouts cannot be audited before launch",
            checkout_audit=[finding.model_dump(mode="json") for finding in error.findings],
        )
    except (ConfigError, ReviewInputError, RunnerError, OSError, subprocess.SubprocessError) as error:
        return _error(failure_reason(error))
    print(json.dumps(payload, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
