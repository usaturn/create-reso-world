"""Claude Code adapter: ``claude -p`` with ``--output-format stream-json``.

The prompt goes over stdin; stdout is NDJSON whose ``system``/``init`` event
reports the observed model, session, and CLI version, and whose ``result``
event carries the final text, error flag, and permission denials. Only local
parsing happens here; this module never starts a process.
"""

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from tools.agent_runner.adapters import AdapterContext, AdapterOutcome, Capabilities, LaunchSpec
from tools.agent_runner.adapters.skills import prompt_lines
from tools.agent_runner.models import Identity, Payload, Receipt, ReceiptStatus, Request, ResultShape

_AUTH = re.compile(
    r"(?:not logged in|not authenticated|sign[ -]?in|log ?in|unauthorized|forbidden"
    r"|authentication|invalid api key|missing api key|no api key|api key is invalid"
    r"|oauth|\b40[13]\b|credentials? (?:missing|invalid|expired))",
    re.IGNORECASE,
)
_APPROVAL = re.compile(
    r"(?:workspace trust|trust this|awaiting approval|requires? approval"
    r"|permission (?:denied|required)|grant access|confirm(?:ed)? (?:to )?continue)",
    re.IGNORECASE,
)
_INTERRUPT = re.compile(r"interrupt|abort|cancel", re.IGNORECASE)
_FENCE = re.compile(r"```(?:json|JSON)\b[^\n]*\n")


def _events(path: Path) -> Iterator[dict[str, object]]:
    try:
        data = path.read_bytes()
    except OSError:
        return
    for line in data.decode("utf-8", errors="replace").split("\n"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            value: object = json.loads(line)
        except ValueError:
            # Preserve a broken event's position so an earlier result cannot
            # hide a truncated later response. Plain notification lines above
            # remain ignorable, and malformed text is never a diagnostic.
            yield {"type": "_malformed_event"}
            continue
        if isinstance(value, dict):
            yield cast(dict[str, object], value)


def _text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _json_object(text: str) -> dict[str, object] | None:
    try:
        value: object = json.loads(text.strip())
    except ValueError:
        pass
    else:
        return cast(dict[str, object], value) if isinstance(value, dict) else None
    decoder = json.JSONDecoder()
    for opening in _FENCE.finditer(text):
        candidate = text[opening.end():].lstrip()
        try:
            value, end = decoder.raw_decode(candidate)
        except ValueError:
            continue
        # JSON strings may contain backticks. Only the decoder's object end
        # can determine where to look for the Markdown closing fence.
        if isinstance(value, dict) and candidate[end:].lstrip().startswith("```"):
            return cast(dict[str, object], value)
    return None


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


def _terminal_subtype(result: dict[str, object] | None) -> str:
    """The terminal result's subtype as a fixed diagnostic value, never its original text."""
    if result is None:
        return "not_observed"
    subtype = result.get("subtype")
    if subtype == "success":
        return "success"
    if subtype == "error":
        return "error"
    return "other"


def _approval_payload(
    result: dict[str, object] | None, source: str, diagnostic_sources: list[str]
) -> dict[str, object]:
    """Diagnostic evidence for ``awaiting_approval``; this payload is not a model answer.

    Only the classifier's source, normalized terminal metadata, and the presence/count of
    permission denials are retained. Denial entries, tool inputs, the raw subtype, and any
    diagnostic text stay out of the receipt and the persisted diagnostic.
    """
    denials = result.get("permission_denials") if result is not None else None
    is_error = result.get("is_error") if result is not None else None
    return {
        "approval": {
            "source": source,
            "terminal_subtype": _terminal_subtype(result),
            "is_error": is_error if type(is_error) is bool else None,
            "permission_denials": bool(denials),
            "denial_count": len(denials) if isinstance(denials, list) else None,
            "diagnostic_sources": diagnostic_sources,
        }
    }


def _receipt(request: Request, status: ReceiptStatus, payload: Payload = None) -> Receipt:
    return Receipt(
        run_id=request.run_id,
        request_id=request.request_id,
        agent_id=request.agent_id,
        role=request.role,
        status=status,
        payload=payload,
    )


def _message(event: dict[str, object]) -> dict[str, object] | None:
    message = event.get("message")
    return cast(dict[str, object], message) if isinstance(message, dict) else None


def _str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _identity(events: list[dict[str, object]]) -> Identity:
    empty: dict[str, object] = {}
    init = next(
        (event for event in events if event.get("type") == "system" and event.get("subtype") == "init"),
        empty,
    )
    model = _str(init.get("model"))
    for event in events:
        if event.get("type") != "assistant":
            continue
        message = _message(event)
        if message is not None and isinstance(message.get("model"), str):
            model = cast(str, message["model"])
    return Identity(
        model=model,
        session_id=_str(init.get("session_id")),
        cli_version=_str(init.get("claude_code_version")),
        # Skill invocations/listings do not expose successful full-file content.
        # Leave versions empty rather than hashing files merely named by a tool.
    )


def _classify(context: AdapterContext, events: list[dict[str, object]], stderr: str) -> tuple[ReceiptStatus, Payload]:
    result_index = next((i for i in range(len(events) - 1, -1, -1) if events[i].get("type") == "result"), None)
    result = events[result_index] if result_index is not None else None
    errors = [
        event for event in events
        if event.get("type") == "error" or (event.get("type") == "assistant" and event.get("error"))
    ]
    channels: list[tuple[str, str]] = [("stderr", stderr)]
    channels.extend(("error_event", json.dumps(event)) for event in errors)
    if result is not None and (result.get("subtype") != "success" or result.get("is_error")):
        channels.append(("terminal_result", json.dumps(result)))
    # Successful model prose and tool data may discuss authentication or approval. Only
    # dedicated failure channels and stderr supply diagnostic classifications.
    failure = _failure_status(*(text for _, text in channels))
    if failure == "awaiting_approval":
        sources: list[str] = []
        for source, text in channels:
            if _failure_status(text) == "awaiting_approval" and source not in sources:
                sources.append(source)
        return failure, _approval_payload(result, "diagnostic_text", sources)
    if failure is not None:
        return failure, None
    if result is None:
        return "response_failed", None
    if result.get("permission_denials"):
        return "awaiting_approval", _approval_payload(result, "permission_denials", [])
    if errors or (result_index is not None and any(
        event.get("type") in {"assistant", "user", "_malformed_event"}
        or (event.get("type") == "system" and event.get("subtype") == "init")
        for event in events[result_index + 1:]
    )):
        return "response_failed", None
    text = _str(result.get("result")) or ""
    if result.get("subtype") == "success" and not result.get("is_error"):
        return _payload(text, context.role.result_shape)
    if _INTERRUPT.search(str(result.get("subtype", ""))):
        return "interrupted", None
    return "response_failed", None


class ClaudeCode:
    capabilities = Capabilities()

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        agent = context.agent
        argv = [
            *agent.command,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            agent.model,
        ]
        if agent.effort is not None:
            argv.extend(("--effort", agent.effort))
        argv.extend(("--dangerously-skip-permissions", *agent.args))
        lines = [context.request.prompt]
        lines.extend(prompt_lines(context.work_dir, agent.skill_sources, context.role.skills))
        if context.role.result_shape == "json":
            lines.append("Return your final answer as a JSON object.")
        # Keep this noninteractive child's work in the foreground so it finishes
        # before the result, and give Bash 10 minutes instead of its 120s default.
        env = {
            "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
            "BASH_DEFAULT_TIMEOUT_MS": "600000",
        }
        return LaunchSpec(argv=tuple(argv), stdin="\n\n".join(lines).encode("utf-8"), env=env)

    def collect(self, context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        events = list(_events(stdout_path))
        status, payload = _classify(context, events, _text(stderr_path))
        return AdapterOutcome(
            receipt=_receipt(context.request, status, payload),
            identity=_identity(events),
        )


ADAPTER = ClaudeCode()
