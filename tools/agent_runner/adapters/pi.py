"""Pi adapter: ``pi --print --mode json`` over a launcher such as piccd/pigs.

The prompt goes over stdin; stdout is NDJSON events. ``session`` reports the
session id, ``agent_end`` carries the final assistant message (model,
provider, thinkingLevel, stopReason, text parts), and ``agent_settled`` marks
clean completion. A zero exit code without a complete event stream is still a
failure. Only local parsing happens here; this module never starts a process.
"""

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from tools.agent_runner.adapters import AdapterContext, AdapterOutcome, Capabilities, LaunchSpec
from tools.agent_runner.adapters.skills import prompt_lines, verified_versions
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
_FENCE = re.compile(r"```(?:json|JSON)\b[^\n]*\n(.*?)```", re.DOTALL)
_STOP_OK = {"stop", "endturn", "end_turn", "completed", "complete", "finished", "normal"}


def _events(path: Path) -> Iterator[dict[str, object]]:
    try:
        data = path.read_bytes()
    except OSError:
        return
    for line in data.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith(("{", "[")):
            continue
        try:
            value: object = json.loads(line)
        except ValueError:
            value = None
        if isinstance(value, dict) and isinstance(value.get("type"), str):
            yield cast(dict[str, object], value)
        else:
            # Keep corruption in stream order so it cannot disappear behind
            # a previous successful completion. A fresh response may recover.
            yield {"type": None, "malformed": line}


def _text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _json_object(text: str) -> dict[str, object] | None:
    candidates = [text.strip()]
    candidates.extend(block.strip() for block in _FENCE.findall(text))
    for candidate in candidates:
        if not candidate:
            continue
        try:
            value: object = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(value, dict):
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


def _receipt(request: Request, status: ReceiptStatus, payload: Payload = None) -> Receipt:
    return Receipt(
        run_id=request.run_id,
        request_id=request.request_id,
        agent_id=request.agent_id,
        role=request.role,
        status=status,
        payload=payload,
    )


def _last_assistant(messages: object) -> dict[str, object] | None:
    if not isinstance(messages, list):
        return None
    for message in reversed(cast(list[object], messages)):
        if isinstance(message, dict) and cast(dict[str, object], message).get("role") == "assistant":
            return cast(dict[str, object], message)
    return None


def _final_text(message: dict[str, object]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "".join(
        cast(str, part_map["text"])
        for part in cast(list[object], content)
        if isinstance(part, dict)
        and (part_map := cast(dict[str, object], part)).get("type") == "text"
        and isinstance(part_map.get("text"), str)
    )


def _skill_evidence(events: list[dict[str, object]], work_dir: Path) -> Iterator[tuple[str, str]]:
    """Accept only correlated, successful, full-file native read observations."""
    pending: dict[str, dict[str, object]] = {}
    for event in events:
        call_id = event.get("toolCallId")
        if not isinstance(call_id, str):
            continue
        if event.get("type") == "tool_execution_start":
            pending.pop(call_id, None)
            args = event.get("args")
            if event.get("toolName") == "read" and isinstance(args, dict):
                pending[call_id] = cast(dict[str, object], args)
        elif event.get("type") == "tool_execution_end":
            args = pending.pop(call_id, None)
            if args is None or event.get("toolName") != "read" or event.get("isError") is not False:
                continue
            path_text = args.get("path")
            if not isinstance(path_text, str) or "offset" in args or "limit" in args:
                continue
            path = Path(path_text)
            if path.name != "SKILL.md":
                continue
            path = path if path.is_absolute() else work_dir / path
            result = event.get("result")
            if not isinstance(result, dict):
                continue
            # Native read output may include truncation annotations. Exact raw
            # content matching below deliberately rejects annotated/partial reads.
            result = cast(dict[str, object], result)
            content = result.get("content")
            if not isinstance(content, list) or not content or any(
                not isinstance(part, dict) or part.get("type") != "text" or not isinstance(part.get("text"), str)
                for part in content
            ):
                continue
            details = result.get("details")
            if isinstance(details, dict) and details.get("truncation"):
                continue
            yield str(path), _final_text(result)


def _str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _classify(
    context: AdapterContext, events: list[dict[str, object]], stderr: str
) -> tuple[ReceiptStatus, Payload, dict[str, object] | None]:
    end_index = next(
        (i for i in range(len(events) - 1, -1, -1) if events[i].get("type") == "agent_end"), None
    )
    message = _last_assistant(events[end_index].get("messages")) if end_index is not None else None
    # Only diagnostics and failed assistant messages are failure channels;
    # successful text, echoed prompts and tool data may discuss authentication.
    diagnostics = [stderr]
    failed = False
    for event in events:
        malformed = event.get("malformed")
        if event.get("type") is None and isinstance(malformed, str) and re.search(
            r'"type"\s*:\s*"(?:error|agent_error)"', malformed
        ):
            diagnostics.append(malformed)
            failed = True
        if event.get("type") in {"error", "agent_error"}:
            diagnostics.append(json.dumps(event))
            failed = True
    if message is not None:
        reason = str(message.get("stopReason") or message.get("rawStopReason") or "").lower()
        if reason not in _STOP_OK:
            diagnostics.extend((_final_text(message), str(message.get("errorMessage") or "")))
    hint = _failure_status(*diagnostics)
    if hint is not None:
        return hint, None, message
    if failed or end_index is None or message is None:
        return "response_failed", None, message
    trailing = events[end_index + 1:]
    # Recovery may emit several agent_end events; only the final one and its
    # following settlement can complete this request. A new run invalidates it.
    settled = next((event for event in reversed(trailing) if event.get("type") == "agent_settled"), None)
    if settled is None or any(event.get("type") in {None, "session", "agent_start", "turn_start"} for event in trailing):
        return "response_failed", None, message
    if settled.get("aborted") is True:
        return "interrupted", None, message
    reason = str(message.get("stopReason") or message.get("rawStopReason") or "").lower()
    if reason in _STOP_OK:
        status, payload = _payload(_final_text(message), context.role.result_shape)
        return status, payload, message
    if any(word in reason for word in ("interrupt", "abort", "cancel")):
        return "interrupted", None, message
    return "response_failed", None, message


def _identity(events: list[dict[str, object]], message: dict[str, object] | None, context: AdapterContext) -> Identity:
    empty: dict[str, object] = {}
    session = next((event for event in reversed(events) if event.get("type") == "session"), empty)
    message = message or empty
    return Identity(
        model=_str(message.get("model")),
        provider=_str(message.get("provider")),
        effort=_str(message.get("thinkingLevel")),
        session_id=_str(session.get("id")),
        skill_versions=verified_versions(_skill_evidence(events, context.work_dir)),
    )


class Pi:
    capabilities = Capabilities()

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        agent = context.agent
        argv = [*agent.command, "--print", "--mode", "json", "--no-session", "--no-approve"]
        if agent.provider is not None:
            argv.extend(("--provider", agent.provider))
        argv.extend(("--model", agent.model))
        if agent.effort is not None:
            argv.extend(("--thinking", agent.effort))
        for source in agent.skill_sources:
            path = Path(source)
            path = path if path.is_absolute() else context.work_dir / path
            argv.extend(("--skill", str(path)))
        argv.extend(agent.args)
        lines = [context.request.prompt]
        lines.extend(prompt_lines(context.work_dir, agent.skill_sources, context.role.skills))
        if context.role.result_shape == "json":
            lines.append("Return your final answer as a JSON object.")
        return LaunchSpec(argv=tuple(argv), stdin="\n\n".join(lines).encode("utf-8"))

    def collect(self, context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        events = list(_events(stdout_path))
        stderr = _text(stderr_path)
        status, payload, message = _classify(context, events, stderr)
        return AdapterOutcome(
            receipt=_receipt(context.request, status, payload),
            identity=_identity(events, message, context),
        )


ADAPTER = Pi()
