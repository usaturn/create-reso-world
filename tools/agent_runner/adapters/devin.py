"""Devin CLI adapter: ``devin -p`` with ``--prompt-file`` and ``--export``.

``devin -p`` does not read stdin, so ``prepare`` writes the prompt into the
attempt directory and passes it by path. ``--export`` leaves an ATIF export
whose final agent message is the answer; it also reports the observed model,
CLI version, and session id. ``devin -p`` prints every agent message to stdout
without separators, so stdout must end with that answer. Those messages are the
model's own words, so only stderr and the export's error steps report the CLI's
failures. Only local parsing happens here; this module never starts a process.
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
_PROMPT_FILE = "prompt.txt"
_EXPORT_FILE = "export.json"


def _text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _plain_tail(tail: str) -> bool:
    # Plain lines can follow the answer, but another JSON-like event (complete
    # or truncated) is not a valid single final response. Their words are not
    # CLI diagnostics: devin reports its own failures on stderr (#239).
    return not any(
        line.lstrip().startswith(("{", "[", "```")) for line in tail.splitlines()
    )


def _ends_with(stdout: str, answer: str) -> bool:
    # devin -p prints every agent message without separators, so earlier
    # messages may precede the answer on its first line. The answer's last
    # line must end there; only plain progress lines may follow.
    answer = answer.strip()
    index = stdout.rfind(answer)
    if index < 0:
        return False
    rest, _, tail = stdout[index + len(answer):].partition("\n")
    return not rest.strip() and _plain_tail(tail)


def _json_object(text: str) -> dict[str, object] | None:
    # Decode from the start, never search nested objects in a malformed answer.
    candidate = text.strip()
    fenced = candidate.startswith("```")
    if fenced:
        opening = re.match(r"```(?:json|JSON)\b[^\n]*\n", candidate)
        if opening is None:
            return None
        candidate = candidate[opening.end():].lstrip()
    try:
        value, end = json.JSONDecoder().raw_decode(candidate)
    except ValueError:
        return None
    tail = candidate[end:].strip()
    if fenced:
        # Do not interpret backticks inside a JSON string as the closing fence.
        if not tail.startswith("```"):
            return None
        tail = tail[3:].strip()
    if not _plain_tail(tail):
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
        export = _export(context.receipt_path.parent / _EXPORT_FILE)
        final = _final_agent_message(export) if export is not None else None
        # stdout and the final ATIF message are the model's own words, so a line
        # quoting "Error: invalid api key" there is answer data. Only stderr and
        # the export's error steps report the CLI's failures (#239).
        failure = _failure_status(stderr) or (
            _export_failure(export) if export is not None else None
        )
        payload: Payload
        if failure is not None:
            status, payload = failure, None
        elif final is not None and _ends_with(stdout, final):
            # The final ATIF message is the answer, and stdout must end with it:
            # neither a truncated stdout nor a malformed final answer succeeds.
            status, payload = _payload(final, context.role.result_shape)
        else:
            status, payload = "response_failed", None
        return AdapterOutcome(
            receipt=_receipt(context.request, status, payload),
            identity=_identity(export) if export is not None else Identity(),
        )


ADAPTER = Devin()
