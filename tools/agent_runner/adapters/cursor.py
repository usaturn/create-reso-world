"""Cursor CLI (`agent -p`) adapter: stream-json events for identity and results."""

import json
import re
from pathlib import Path
from typing import cast

from tools.agent_runner.adapters import AdapterContext, AdapterOutcome, Capabilities, LaunchSpec
from tools.agent_runner.adapters.skills import prompt_lines, verified_versions
from tools.agent_runner.models import Identity, Receipt, State

_AUTHENTICATION = re.compile(
    r"(?i)(not logged in|login required|please log in|unauthorized|invalid api key|"
    r"authentication (?:required|failed)|token expired)"
)
_APPROVAL = re.compile(r"(?i)(workspace trust required|trust the contents|approval required)")
_SKILL_FILE = re.compile(r"(/[^\s\"'\\]+/skills/[^\s\"'\\]+/SKILL\.md)")


def _prompt(context: AdapterContext) -> str:
    parts = [context.request.prompt]
    if context.request.result_shape == "json":
        parts.append("Answer with a single JSON object as your final message.")
    parts.extend(prompt_lines(context.work_dir, context.agent.skill_sources, context.role.skills))
    return "\n\n".join(parts)


def _event(line: str) -> dict[str, object] | None:
    try:
        value: object = json.loads(line)
    except json.JSONDecodeError:
        return None
    return cast(dict[str, object], value) if isinstance(value, dict) else None


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _json_object(text: str) -> dict[str, object] | None:
    stripped = text.strip()
    try:
        whole: object = json.loads(stripped)
    except json.JSONDecodeError:
        pass
    else:
        if isinstance(whole, dict):
            return cast(dict[str, object], whole)
        return None
    # Do not salvage a nested object from a malformed outer JSON value.
    if stripped.startswith(("{", "[")):
        return None
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            return None
        if isinstance(value, dict):
            return cast(dict[str, object], value)
        return None
    return None


def _read_evidence(event: dict[str, object]) -> list[tuple[str, str]]:
    """Complete untruncated readToolCall completions with their returned content.

    Evidence must come from the result (returned path and content), never from
    the call arguments. Partial ranges, exceeded limits, and missing content
    stay unknown.
    """
    if event.get("type") != "tool_call" or event.get("subtype") != "completed":
        return []
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict):
        return []
    read = cast(dict[str, object], tool_call).get("readToolCall")
    if not isinstance(read, dict):
        return []
    result = cast(dict[str, object], read).get("result")
    if not isinstance(result, dict):
        return []
    read_result = cast(dict[str, object], result)
    success = read_result.get("success")
    if "error" in read_result or not isinstance(success, dict):
        return []
    read_success = cast(dict[str, object], success)
    path = read_success.get("path")
    content = read_success.get("content")
    if not isinstance(path, str) or not isinstance(content, str):
        return []
    if read_success.get("exceededLimit") is not False or read_success.get("isEmpty") is True:
        return []
    read_range = read_success.get("readRange")
    if not isinstance(read_range, dict):
        return []
    read_range = cast(dict[str, object], read_range)
    start = read_range.get("startLine")
    end = read_range.get("endLine")
    total = read_success.get("totalLines")
    if type(start) is not int or type(end) is not int or type(total) is not int:
        return []
    if start != 1 or end != total:
        return []
    return [(path, content)]


def _skill_versions(text: str) -> dict[str, str]:
    """Version map from completed reads whose returned content still equals the present bytes."""
    evidence: list[tuple[str, str]] = []
    for line in text.split("\n"):
        event = _event(line)
        if event is None:
            continue
        for item in _read_evidence(event):
            if not _SKILL_FILE.fullmatch(item[0]):
                continue
            evidence.append(item)
    return verified_versions(evidence)


def _diagnostics(stdout: str, stderr: str) -> str:
    """CLI-emitted diagnostics: stderr, non-JSON stdout lines, and failure events."""
    parts = [stderr]
    for line in stdout.split("\n"):
        if not line.strip():
            continue
        event = _event(line)
        if (
            event is None
            or event.get("type") == "error"
            or (
                event.get("type") == "result"
                and (event.get("is_error") is not False or event.get("subtype") != "success")
            )
        ):
            parts.append(line)
    return "\n".join(parts)


class _CursorAdapter:
    capabilities = Capabilities()

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        agent = context.agent
        if agent.effort is not None and ("[" in agent.model or "]" in agent.model):
            # The CLI accepts bracket overrides, but stacking two sets is not
            # a supported spelling. Keep the requested settings unambiguous.
            raise ValueError("effort cannot be combined with a model override")
        model = agent.model if agent.effort is None else f"{agent.model}[effort={agent.effort}]"
        argv = [*agent.command, "-p", "--output-format", "stream-json", "--trust"]
        # writes=false is only an instruction (#201): --mode ask/plan reject shell commands, and Cursor's sandbox
        # blocks the review helpers' writes outside the worktree, so read-only roles get the shell with it off
        argv += ["-f"] if context.role.writes else ["-f", "--sandbox", "disabled"]
        argv += ["--model", model, *agent.args]
        return LaunchSpec(tuple(argv), _prompt(context).encode("utf-8"))

    def collect(self, context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        stdout = _read(stdout_path)
        stderr = _read(stderr_path)
        events = [e for e in (_event(line) for line in stdout.split("\n")) if e is not None]

        session_id: str | None = None
        model: str | None = None
        for event in events:
            if event.get("type") == "system" and event.get("subtype") == "init":
                sid = event.get("session_id")
                session_id = sid if isinstance(sid, str) else None
                observed = event.get("model")
                model = observed if isinstance(observed, str) else None
        identity = Identity(model=model, session_id=session_id, skill_versions=_skill_versions(stdout))

        def failed(state: State) -> AdapterOutcome:
            return AdapterOutcome(identity=identity, state=state)

        diagnostics = _diagnostics(stdout, stderr)
        if _AUTHENTICATION.search(diagnostics):
            return failed("awaiting_authentication")
        if _APPROVAL.search(diagnostics):
            return failed("awaiting_approval")

        # Preserve malformed event failures instead of silently reusing an
        # earlier terminal result. Plain CLI progress lines remain harmless.
        if any(line.lstrip().startswith(("{", "[")) and _event(line) is None for line in stdout.split("\n")):
            return failed("response_failed")

        result: str | None = None
        errored = False
        for event in events:
            if event.get("type") == "assistant" or (
                event.get("type") == "system" and event.get("subtype") == "init"
            ):
                # A new response/session must produce its own terminal result.
                result = None
            if event.get("type") == "error":
                errored = True
            if event.get("type") != "result":
                continue
            candidate = event.get("result")
            if event.get("is_error") is not False or event.get("subtype") != "success" or not isinstance(candidate, str):
                errored = True
            if isinstance(candidate, str):
                result = candidate
        if errored or result is None:
            return failed("response_failed")
        if context.request.result_shape == "json":
            payload = _json_object(result)
            if payload is None:
                return failed("response_failed")
        else:
            if not result.strip():
                return failed("response_failed")
            payload = result
        request = context.request
        receipt = Receipt(
            run_id=request.run_id,
            request_id=request.request_id,
            agent_id=request.agent_id,
            role=request.role,
            status="success",
            payload=payload,
        )
        return AdapterOutcome(receipt=receipt, identity=identity)


ADAPTER = _CursorAdapter()
