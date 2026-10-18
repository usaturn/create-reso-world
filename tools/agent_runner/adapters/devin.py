"""Devin CLI adapter: ``devin -p`` with ``--prompt-file`` and ``--export``.

``devin -p`` does not read stdin, so ``prepare`` writes the prompt into the
attempt directory and passes it by path. The run's stdout is the final answer;
``--export`` leaves an ATIF export that reports the observed model, CLI
version, and session id. Only local parsing happens here; this module never
starts a process.
"""

import json
import re
from pathlib import Path
from typing import cast

from tools.agent_runner.adapters import (
    AdapterContext,
    AdapterOutcome,
    Capabilities,
    LaunchSpec,
)
from tools.agent_runner.adapters.skills import prompt_lines
from tools.agent_runner.models import (
    Identity,
    Payload,
    Receipt,
    ReceiptStatus,
    Request,
    ResultShape,
)

_AUTH = re.compile(
    r"(?:not logged in|not authenticated|sign[ -]?in|log ?in|unauthorized|forbidden"
    r"|authentication|invalid api key|missing api key|no api key|api key is invalid"
    r"|oauth|\b40[13]\b|credentials? (?:missing|invalid|expired))",
    re.IGNORECASE,
)
_APPROVAL = re.compile(
    r"(?:workspace trust|trust this|awaiting approval|waiting for approval|approval required|requires? approval"
    r"|permission (?:denied|required)|grant access|confirm(?:ed)? (?:to )?continue)",
    re.IGNORECASE,
)
_DIAGNOSTIC_LINE = re.compile(
    r"^(?:error:|fatal:|not logged in\b|not authenticated\b|approval required\b"
    r"|waiting for approval\b|awaiting approval\b|workspace trust\b)",
    re.IGNORECASE,
)
_PROMPT_FILE = "prompt.txt"
_EXPORT_FILE = "export.json"


def _text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _json_object(text: str) -> dict[str, object] | None:
    # Decode from the start, never search nested objects in a malformed answer.
    # Plain CLI progress can follow the answer, but another JSON-like event
    # (complete or truncated) is not a valid single final response.
    candidate = text.strip()
    trailing = ""
    if candidate.startswith("```"):
        fence = re.fullmatch(
            r"```(?:json|JSON)\b[^\n]*\n(.*?)```(.*)", candidate, re.DOTALL
        )
        if fence is None:
            return None
        candidate, trailing = fence.group(1).strip(), fence.group(2).strip()
    try:
        value, end = json.JSONDecoder().raw_decode(candidate)
    except ValueError:
        return None
    tail = "\n".join((candidate[end:].strip(), trailing)).strip()
    if _failure_status(tail) is not None or any(
        line.lstrip().startswith(("{", "[", "```")) for line in tail.splitlines()
    ):
        return None
    return cast(dict[str, object], value) if isinstance(value, dict) and value else None


def _payload(text: str, shape: ResultShape) -> tuple[ReceiptStatus, Payload]:
    if shape == "text":
        return ("success", text) if text.strip() else ("response_failed", None)
    parsed = _json_object(text)
    return ("success", parsed) if parsed is not None else ("response_failed", None)


def _failure_status(*texts: str) -> ReceiptStatus | None:
    combined = "\n".join(text for text in texts if text)
    if not combined.strip():
        return None
    if _AUTH.search(combined):
        return "awaiting_authentication"
    if _APPROVAL.search(combined):
        return "awaiting_approval"
    return None


def _receipt(
    request: Request, status: ReceiptStatus, payload: Payload = None
) -> Receipt:
    return Receipt(
        run_id=request.run_id,
        request_id=request.request_id,
        agent_id=request.agent_id,
        role=request.role,
        status=status,
        payload=payload,
    )


def _export(path: Path) -> dict[str, object] | None:
    try:
        value: object = json.loads(path.read_bytes())
    except OSError, ValueError:
        return None
    return cast(dict[str, object], value) if isinstance(value, dict) else None


def _final_agent_message(export: dict[str, object]) -> str | None:
    steps = export.get("steps")
    if not isinstance(steps, list) or not steps:
        return None
    # A trailing user/tool/error step or an agent still making tool calls is
    # incomplete. Do not borrow an earlier successful agent response.
    step = steps[-1]
    if (
        not isinstance(step, dict)
        or step.get("source") != "agent"
        or step.get("tool_calls")
    ):
        return None
    message = step.get("message")
    return message if isinstance(message, str) and message.strip() else None


def _export_failure(export: dict[str, object]) -> ReceiptStatus | None:
    steps = export.get("steps")
    if not isinstance(steps, list):
        return None
    for step in steps:
        if not isinstance(step, dict):
            continue
        if (
            step.get("source") == "error"
            or step.get("is_error") is True
            or step.get("error")
        ):
            return (
                _failure_status(
                    str(step.get("message", "")), str(step.get("error", ""))
                )
                or "response_failed"
            )
    return None


def _str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _identity(export: dict[str, object]) -> Identity:
    agent = export.get("agent")
    agent_map = cast(dict[str, object], agent) if isinstance(agent, dict) else {}
    return Identity(
        model=_str(agent_map.get("model_name")),
        session_id=_str(export.get("session_id")),
        cli_version=_str(agent_map.get("version")),
        # ATIF tool-call arguments alone do not prove a completed full read.
        skill_versions={},
    )


class Devin:
    capabilities = Capabilities()

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        agent = context.agent
        attempt = context.receipt_path.parent
        prompt_file = attempt / _PROMPT_FILE
        lines = [context.request.prompt]
        if context.role.result_shape == "json":
            lines.append(
                "Return the final answer as one nonempty JSON object, without surrounding prose."
            )
        lines.extend(
            prompt_lines(context.work_dir, agent.skill_sources, context.role.skills)
        )
        prompt_file.write_text("\n\n".join(lines), encoding="utf-8")
        argv = (
            *agent.command,
            "-p",
            "--prompt-file",
            str(prompt_file),
            "--export",
            str(attempt / _EXPORT_FILE),
            "--model",
            agent.model,
            "--permission-mode",
            "dangerous",
            "--respect-workspace-trust",
            "false",
            *agent.args,
        )
        return LaunchSpec(argv=argv, stdin=b"")

    def collect(
        self, context: AdapterContext, stdout_path: Path, stderr_path: Path
    ) -> AdapterOutcome:
        stdout = _text(stdout_path)
        stderr = _text(stderr_path)
        # stdout can be a prose answer. Only explicit diagnostic lines are
        # failure channels; a payload discussing authentication is ordinary data.
        diagnostics = [
            line for line in stdout.splitlines() if _DIAGNOSTIC_LINE.match(line.strip())
        ]
        hint = _failure_status(stderr, *diagnostics)
        export = _export(context.receipt_path.parent / _EXPORT_FILE)
        final = _final_agent_message(export) if export is not None else None
        failure = hint or (_export_failure(export) if export is not None else None)
        if failure is not None:
            status, payload = failure, None
        elif stdout.strip() and final is not None:
            status, payload = _payload(stdout, context.role.result_shape)
            if status != "success":
                status = _failure_status(stdout) or status
        else:
            status, payload = _failure_status(stdout) or "response_failed", None
        return AdapterOutcome(
            receipt=_receipt(context.request, status, payload),
            identity=_identity(export) if export is not None else Identity(),
        )


ADAPTER = Devin()
