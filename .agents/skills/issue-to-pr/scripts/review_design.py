"""issue-to-pr の設計を、--design-review で指定した担当にレビューさせる（Spec レビューより前に 1 回だけ行う）。

check・review は --design-review で指定した担当だけを使い、設定だけでは担当を選ばない（設定の fallback は保つ）。
設計レビューは Spec と決定記録を保存した後、Spec レビュー・builder check・Plan の前に行う。
同じ LEDGER_ROOT の Spec レビューの記録（<stem>.spec-review/）があれば始めない（その結果が古い版のものになるため）。
review は Spec の写しと依頼文を記録し、外部の担当なら runner で依頼して結果を検証・記録する。
self なら依頼文のパスを返し、submit がその結果を外部と同じ形・対応・版の検証を通して記録する。
decide は司令塔の採否を検証して記録し、次工程（continue・stop）を返す。
採否を記録したレビューがあれば、2 回目は始めない（1 回で終える。失敗したレビューは数えない）。
作るものが変わる別案（changes_what_is_built が真）と、レビュアーが利用者に尋ねるべきとした指摘（ask_user）は
adopt できない。wrong_approach・blocking の指摘・利用者への問い・needs_judgment があれば、採否に依らず stop を返す。
cleanup は runner の worktree と出力先を片付ける。
記録は LEDGER_ROOT/<stem>.design-review/review-<k>/ に置き、消さない。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, model_validator

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agent_runner import Config, ConfigError, RunnerError  # noqa: E402
from tools.agent_runner.adapters import Adapter, load_adapter  # noqa: E402
from tools.agent_runner.models import Assignment  # noqa: E402
from tools.agent_runner.workspace import CheckoutAuditError  # noqa: E402


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # pydantic のモデルが前方参照を自分のモジュールで解決できるように、実行の前に登録する
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# 役割に依らない部分（依頼・runner の起動・結果の検査・記録・後片付け）は review_spec.py と同じ実装を使う
review_spec = _load_module("issue_review_design_review_spec", Path(__file__).with_name("review_spec.py"))

ReviewInputError = review_spec.ReviewInputError
ReviewRequest = review_spec.ReviewRequest


# --- 結果・採否の形 -----------------------------------------------------------------------------------------------


def _text(value: str) -> str:
    if not value.strip() or "\x00" in value:
        raise ValueError("must be nonblank text without NUL")
    return value


Text = Annotated[str, AfterValidator(_text)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Concern(_Strict):
    id: Identifier
    decision_ref: Text
    problem: Text
    evidence: Text
    alternative: Text
    tradeoffs: Text
    impact: Text
    recommendation: Literal["keep", "change", "ask_user"]
    severity: Literal["blocking", "worth_considering"]


class DesignReviewResult(_Strict):
    """担当が返す JSON。incomplete は未完了（レビュー失敗）で、sound として扱わない。"""

    review_id: str
    spec_sha256: str
    status: Literal["completed", "incomplete"]
    verdict: Literal["sound", "concerns", "wrong_approach"]
    assessment: Text
    concerns: list[Concern]
    questions_for_user: list[Text]
    incomplete: list[Text]

    @model_validator(mode="after")
    def _consistent(self) -> DesignReviewResult:
        identifiers = [concern.id for concern in self.concerns]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("concern ids must be unique")
        if (self.status == "completed") == bool(self.incomplete):
            raise ValueError("incomplete must be empty exactly when status is completed")
        if self.status == "completed" and (self.verdict == "sound") != (
            not self.concerns and not self.questions_for_user
        ):
            raise ValueError("verdict is sound exactly when there are no concerns and no questions")
        return self


class DesignDecision(_Strict):
    id: Identifier
    decision: Literal["adopt", "reject", "needs_judgment"]
    changes_what_is_built: bool
    reason: Text
    reflected_in: Text | None

    @model_validator(mode="after")
    def _consistent(self) -> DesignDecision:
        if self.decision == "adopt" and self.reflected_in is None:
            raise ValueError("an adopted concern needs reflected_in")
        if self.decision == "adopt" and self.changes_what_is_built:
            raise ValueError("a change to what is built needs the user's judgment, not adopt")
        return self


class DesignDecisions(_Strict):
    decisions: list[DesignDecision]


DESIGN_REVIEW = review_spec.Kind(
    role="design-review",
    suffix=".design-review",
    result=DesignReviewResult,
    counted="concerns",
    scalars=("verdict",),
)


def load(template: Path, config: Path | None, agent: str) -> Config:
    loaded: Config = review_spec.load(template, config, agent, DESIGN_REVIEW)
    return loaded


def check(template: Path, config: Path | None, agent: str) -> dict[str, Any]:
    payload: dict[str, Any] = review_spec.check(template, config, agent, DESIGN_REVIEW)
    return payload


def ledger_dir(spec_path: Path, ledger_root: Path) -> Path:
    path: Path = review_spec.review_ledger(spec_path, DESIGN_REVIEW, ledger_root)
    return path


# --- 依頼文 -------------------------------------------------------------------------------------------------------

RESULT_SHAPE = json.dumps(
    {
        "review_id": "<the review_id below>",
        "spec_sha256": "<the spec_sha256 below>",
        "status": "completed | incomplete",
        "verdict": "sound | concerns | wrong_approach",
        "assessment": "<overall assessment of the design>",
        "concerns": [
            {
                "id": "D1",
                "decision_ref": "<decision-record item: identifier or heading>",
                "problem": "<problem>",
                "evidence": "<evidence: Issue text, repository file:line, or Spec text>",
                "alternative": "<the better alternative>",
                "tradeoffs": "<trade-offs between the current design and the alternative>",
                "impact": "<effect on scope, acceptance criteria and user-visible behavior>",
                "recommendation": "keep | change | ask_user",
                "severity": "blocking | worth_considering",
            }
        ],
        "questions_for_user": ["<question only the user can answer>"],
        "incomplete": ["<why you could not finish>"],
    },
    ensure_ascii=False,
)


def compose_prompt(request: ReviewRequest, *, review_id: str, spec_text: str, spec_sha256: str) -> str:
    """担当への依頼文（self の司令塔も同じ文を読む）。runner はこの前に作業範囲の指示（writes=False）を付ける。"""
    begin, end = f"----- BEGIN SPEC {review_id} -----", f"----- END SPEC {review_id} -----"
    lines = [
        "You are reviewing the design chosen in a Spec before an implementation plan is written from it. You will "
        "not be able to talk to the person who wrote it. Do not modify any file, do not start other agents or "
        "subagents, and do not write to GitHub.",
        "",
        "The Spec is NOT in this worktree: its full text is between the BEGIN/END lines below. Its path is only a "
        "record of where it is kept. The worktree is the target repository at the revision below; read it to check "
        "what the Spec says about the existing code and rules. The Spec contains a decision record (chosen option, "
        "alternatives considered, reasons); check the design against it.",
        "",
        "Judge whether the design is right for the problem in the Issue and whether a better alternative exists. "
        "Look at:",
        "- fit to the problem: does the design solve what the Issue asks",
        "- comparison of alternatives: is there an alternative that is clearly better, and were the rejected "
        "alternatives dismissed for sound reasons",
        "- fit to the existing structure of the repository",
        "- scope: is it larger or smaller than the Issue needs",
        "- risk and reversibility: what is hard to undo, what breaks existing users",
        "- sufficiency of the evidence behind the decisions",
        "",
        "Report a concern only when an alternative is substantially better, or when the current design cannot meet "
        "the requirements. Do not report design taste, wording, or details the Spec explicitly leaves to the "
        "builder. Defects such as missing requirements, contradictions and missing acceptance criteria belong to a "
        "later Spec review; do not report them unless they come from the design itself.",
        "",
        "severity: blocking = the current design cannot meet the requirements of the Issue; worth_considering = a "
        "substantially better alternative exists.",
        "recommendation: keep = keep the current design; change = switch to the alternative; ask_user = the user "
        "should decide.",
        "questions_for_user: only questions that only the user can answer and whose answer changes what is built. "
        "Otherwise leave it empty.",
        "verdict: sound = nothing to report (concerns and questions_for_user are empty); concerns = there are "
        "concerns or questions; wrong_approach = the approach itself is wrong; report why as at least one concern "
        "(usually blocking) or question. concerns and wrong_approach are valid only with at least one concern or "
        "question.",
        "",
        'If you could not finish (missing context, unreadable input), return "status": "incomplete" with the '
        'reasons in "incomplete"; never return "sound" for an unfinished review. If you finished, return '
        '"status": "completed" and an empty "incomplete".',
        "",
        "Return exactly one JSON object with exactly these keys (write assessment, problem, evidence, alternative, "
        "tradeoffs, impact and questions_for_user in Japanese):",
        RESULT_SHAPE,
        "",
        f"review_id: {review_id}",
        f"spec_sha256: {spec_sha256}",
        f"repository: {request.issue.repo}",
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
        "",
        begin,
        spec_text,
        end,
    ]
    return "\n".join(lines)


# --- review・submit -----------------------------------------------------------------------------------------------


def _admit(spec_path: Path, assignment: Assignment, ledger_root: Path) -> int:
    """設計レビューを始められるかを決める。始められなければ ReviewInputError。設計レビューは 1 回で終える。"""
    started = review_spec.review_ledger(spec_path, review_spec.SPEC_REVIEW, ledger_root)
    if started.exists() or started.is_symlink():
        raise ReviewInputError("the Spec review has already started: the design review comes before it")
    for review_dir in review_spec._reviews(ledger_dir(spec_path, ledger_root)):
        if not (review_dir / "review.json").is_file():
            raise ReviewInputError(
                "a review without a result exists: submit the self review, or confirm that its runner stopped"
            )
        record = review_spec._read(review_dir / "review.json")
        if review_spec._stop_unconfirmed(record):
            raise ReviewInputError("a previous review has attempts whose stop is not confirmed")
        if record["state"] != "completed":
            continue
        if not (review_dir / "decisions.json").is_file():
            raise ReviewInputError("record the decisions on the completed review first")
        raise ReviewInputError("the design review is already done: it runs once")
    return 1


def review(
    config: Config,
    request: ReviewRequest,
    runner_dir: Path | None,
    *,
    ledger_dir: Path | None = None,
    adapter_loader: Callable[[str], Adapter] = load_adapter,
) -> dict[str, Any]:
    """設計レビューを始める。1 回だけ行う。"""
    ledger_root = review_spec.resolve_ledger_root(ledger_dir)

    def compose(review_id: str, round_: int, spec_text: str, spec_sha256: str) -> str:
        return compose_prompt(request, review_id=review_id, spec_text=spec_text, spec_sha256=spec_sha256)

    summary: dict[str, Any] = review_spec.start(
        DESIGN_REVIEW,
        config,
        request,
        runner_dir,
        ledger_root=ledger_root,
        admit=_admit,
        compose=compose,
        adapter_loader=adapter_loader,
    )
    return summary


def submit(review_dir: Path, result_path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = review_spec.submit(review_dir, result_path, DESIGN_REVIEW)
    return summary


# --- decide・cleanup ----------------------------------------------------------------------------------------------


def decide(review_dir: Path, decisions_path: Path) -> dict[str, Any]:
    """司令塔の採否を検証して記録し、次工程（continue・stop）を返す。拒否のときは何も記録しない。

    採用した指摘を Spec に反映した後（決定記録の設計レビューの節を書くならそれも済ませた後）に呼ぶ。
    この時点の Spec を反映後の版として記録する。
    """
    request = review_spec._request_of(review_dir, DESIGN_REVIEW)
    review_path = review_dir / "review.json"
    if not review_path.is_file() or review_spec._read(review_path)["state"] != "completed":
        raise ReviewInputError("decisions need a completed review")
    if (review_dir / "decisions.json").exists():
        raise ReviewInputError("this review already has decisions")
    try:
        decisions = DesignDecisions.model_validate_json(decisions_path.read_bytes()).decisions
    except ValidationError as error:
        raise ReviewInputError(f"invalid decisions: {review_spec._fields(error)}") from None
    result = DesignReviewResult.model_validate(review_spec._read(review_path)["result"])
    if (result.review_id, result.spec_sha256) != (request["review_id"], request["spec_sha256"]):
        raise ReviewInputError("the recorded result does not match the review request")
    if result.status != "completed":
        raise ReviewInputError("the recorded review is not completed")
    concerns = {concern.id: concern for concern in result.concerns}
    identifiers = [decision.id for decision in decisions]
    if len(identifiers) != len(set(identifiers)) or set(identifiers) != set(concerns):
        raise ReviewInputError("decisions must cover every concern exactly once")
    current: bytes = review_spec._read_spec(Path(request["request"]["spec_path"]))
    reflected_sha256: str = review_spec._sha256(current)
    adopted = [decision.id for decision in decisions if decision.decision == "adopt"]
    if adopted and reflected_sha256 == request["spec_sha256"]:
        raise ReviewInputError("adopted concerns are not reflected in the Spec")
    if any(decision.changes_what_is_built for decision in decisions if decision.decision == "adopt"):
        raise ReviewInputError("a design that changes what is built needs the user's judgment, not adopt")
    if any(concerns[identifier].recommendation == "ask_user" for identifier in adopted):
        raise ReviewInputError("a concern the reviewer left to the user cannot be adopted")
    reasons: list[str] = []
    if result.verdict == "wrong_approach":
        reasons.append("wrong_approach: the reviewer judged the approach itself to be wrong")
    blocking = [concern.id for concern in result.concerns if concern.severity == "blocking"]
    if blocking:
        reasons.append(f"blocking: {', '.join(blocking)}")
    if result.questions_for_user:
        reasons.append(f"questions_for_user: {len(result.questions_for_user)}")
    judgment = [decision.id for decision in decisions if decision.decision == "needs_judgment"]
    if judgment:
        reasons.append(f"needs_judgment: {', '.join(judgment)}")
    next_step = "stop" if reasons else "continue"
    review_spec._write_new_bytes(review_dir / "reflected.md", current)
    review_spec._write_new(
        review_dir / "decisions.json",
        {
            "decisions": [decision.model_dump(mode="json") for decision in decisions],
            "reviewed_spec_sha256": request["spec_sha256"],
            "reflected_spec_sha256": reflected_sha256,
            "decided_at": review_spec._now(),
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


def cleanup(review_dir: Path) -> dict[str, Any]:
    payload: dict[str, Any] = review_spec.cleanup(review_dir, DESIGN_REVIEW)
    return payload


# --- CLI ----------------------------------------------------------------------------------------------------------


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    """check と review が同じ定義で受け付ける設定の引数。"""
    parser.add_argument(
        "--design-review",
        metavar="AGENT",
        required=True,
        help="その run の設計レビューの担当（agent-runner の agent 名か self）。設定だけでは担当を選ばない",
    )
    parser.add_argument("--template", type=Path, default=review_spec.implement.DEFAULT_TEMPLATE)
    parser.add_argument(
        "--config", type=Path, help="個人設定（既定は AGENT_RUNNER_CONFIG・XDG_CONFIG_HOME・~/.config）"
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="review_design.py", description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    _add_config_arguments(commands.add_parser("check", help="設定だけを検査する（worktree・runner に触れない）"))
    launch = commands.add_parser("review", help="設計のレビューを記録し、外部の担当なら runner で依頼する")
    launch.add_argument("--request", type=Path, required=True, help="ReviewRequest の JSON")
    launch.add_argument("--runner-dir", type=Path, help="runner の出力先（外部の担当のとき。存在しないパス）")
    launch.add_argument(
        "--ledger-dir", type=Path, help="レビュー記録のルート（既定は環境変数 SESSION。未設定なら拒否する）"
    )
    _add_config_arguments(launch)
    submitted = commands.add_parser("submit", help="self のレビューの結果を検証して記録する")
    submitted.add_argument("--review-dir", type=Path, required=True)
    submitted.add_argument("--result", type=Path, required=True, help="DesignReviewResult の JSON")
    decided = commands.add_parser("decide", help="採否を検証して記録し、次工程を返す")
    decided.add_argument("--review-dir", type=Path, required=True)
    decided.add_argument("--decisions", type=Path, required=True, help="DesignDecisions の JSON")
    commands.add_parser("cleanup", help="runner の worktree の登録を外し、出力先を片付ける").add_argument(
        "--review-dir", type=Path, required=True
    )
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "check":
            config = args.config.resolve() if args.config else None
            payload = check(args.template.resolve(), config, args.design_review)
            code = 0
        elif args.command == "review":
            config = args.config.resolve() if args.config else None
            runner_dir = args.runner_dir.absolute() if args.runner_dir else None
            payload = review(
                load(args.template.resolve(), config, args.design_review),
                review_spec.read_request(args.request),
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
        return int(
            review_spec._error(
                "checkout_audit: registered checkouts cannot be audited before launch",
                checkout_audit=[finding.model_dump(mode="json") for finding in error.findings],
            )
        )
    except (ConfigError, ReviewInputError, RunnerError, OSError, subprocess.SubprocessError) as error:
        return int(review_spec._error(review_spec.failure_reason(error)))
    print(json.dumps(payload, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
