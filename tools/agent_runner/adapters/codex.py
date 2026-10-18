"""Codex (`codex exec`) adapter: JSONL events plus session rollout identity."""

import json
import os
import re
import shlex
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from tools.agent_runner.adapters import AdapterContext, AdapterOutcome, Capabilities, LaunchSpec
from tools.agent_runner.adapters.skills import prompt_lines, verified_versions
from tools.agent_runner.models import Identity, Receipt, State

_AUTHENTICATION = re.compile(
    r"(?i)(not logged in|login required|please log in|please run ['\"`]?\S* login|"
    r"unauthorized|invalid api key|authentication (?:required|failed)|token expired)"
)
_APPROVAL = re.compile(
    r"(?i)(approval (?:required|needed|pending)|(?:waiting|awaiting) (?:for )?approval|"
    r"permission (?:required|denied)|requires? (?:user )?(?:approval|confirmation))"
)
_THREAD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
_SKILL_FILE = re.compile(r"(/[^\s\"'\\]+/[^\s\"'\\]+/SKILL\.md)")


def _prompt(context: AdapterContext) -> str:
    parts = [context.request.prompt]
    if context.request.result_shape == "json":
        parts.append("Answer with a single JSON object as your final message.")
    parts.extend(prompt_lines(context.work_dir, context.agent.skill_sources, context.role.skills, prefix="$"))
    return "\n\n".join(parts)


def _event(line: str) -> dict[str, object] | None:
    try:
        value: object = json.loads(line)
    except json.JSONDecodeError:
        return None
    # Invalid event types are malformed output, never ignorable events.
    # Validate before either diagnostic or failure set membership sees them.
    return cast(dict[str, object], value) if isinstance(value, dict) and isinstance(value.get("type"), str) else None


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
        # Bare JSON must be complete; do not salvage a nested object from a
        # truncated outer object or array. Prose/fences may wrap one object.
        if stripped.startswith(("{", "[")):
            return None
    else:
        return cast(dict[str, object], whole) if isinstance(whole, dict) and whole else None
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character not in "{[":
            continue
        try:
            value, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            return None
        if text[index + end:].lstrip().startswith(("{", "[")):
            return None
        return cast(dict[str, object], value) if isinstance(value, dict) and value else None
    return None


def _read_evidence(event: dict[str, object]) -> list[tuple[str, str]]:
    """Successful simple cat commands with their observed output, as (path, content)."""
    if event.get("type") != "item.completed":
        return []
    item = event.get("item")
    if not isinstance(item, dict):
        return []
    entry = cast(dict[str, object], item)
    if entry.get("type") != "command_execution" or entry.get("status") != "completed" or entry.get("exit_code") != 0:
        return []
    command = entry.get("command")
    if not isinstance(command, str):
        return []
    try:
        words = shlex.split(command)
        if len(words) == 3 and words[:2] == ["/bin/bash", "-lc"]:
            words = shlex.split(words[2])
    except ValueError:
        return []
    # Deliberately do not interpret compound commands, options or shell expansions.
    if len(words) != 2 or words[0] != "cat" or not _SKILL_FILE.fullmatch(words[1]):
        return []
    if any(character in words[1] for character in "$`*?[]{}~;|&()<>"):
        return []
    output = entry.get("aggregated_output")
    if not isinstance(output, str):
        return []
    return [(words[1], output)]


def _skill_versions(*texts: str) -> dict[str, str]:
    """Version map from reads whose observed output still equals the present bytes."""
    evidence: list[tuple[str, str]] = []
    for text in texts:
        for line in text.split("\n"):
            event = _event(line)
            if event is None:
                continue
            evidence.extend(_read_evidence(event))
    return verified_versions(evidence)


def _diagnostics(stdout: str, stderr: str, failures: list[dict[str, object]]) -> str:
    """CLI diagnostics, retaining only unrecovered stream errors and fatal turns."""
    parts = [stderr]
    for line in stdout.split("\n"):
        if not line.strip():
            continue
        event = _event(line)
        if event is None:
            parts.append(line)
    parts.extend(json.dumps(event) for event in failures)
    return "\n".join(parts)


def _rollout(session_id: str | None, environment: Mapping[str, str]) -> str:
    """Read only a matching session in the actual child state directory."""
    if not session_id or not _THREAD_ID.fullmatch(session_id):
        return ""
    if codex_home := environment.get("CODEX_HOME"):
        root = Path(codex_home)
    elif home := environment.get("HOME"):
        root = Path(home) / ".codex"
    else:
        return ""
    filename = re.compile(
        r"rollout-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-" + re.escape(session_id) + r"\.jsonl"
    )
    # Codex's date-partitioned layout bounds traversal depth. Filename matching
    # alone must not select another thread whose ID merely ends in ours.
    sessions = root / "sessions"
    try:
        boundary = sessions.resolve()
        if not boundary.is_relative_to(root.resolve()):
            return ""
        hits = sorted(sessions.glob(f"*/*/*/rollout-*-{session_id}.jsonl"))
        for path in reversed(hits):
            if not filename.fullmatch(path.name) or not path.resolve().is_relative_to(boundary):
                continue
            text = _read(path)
            mismatched = False
            for line in text.split("\n"):
                record = _event(line)
                if record is None or record.get("type") != "session_meta":
                    continue
                payload = record.get("payload")
                if isinstance(payload, dict):
                    for key in ("id", "session_id"):
                        if key in payload and payload[key] != session_id:
                            mismatched = True
            if not mismatched:
                return text
    except OSError:
        pass
    return ""


def _malformed_events(text: str) -> bool:
    """Reject JSON-like corruption without treating ordinary progress as JSON."""
    return any(line.lstrip().startswith(("{", "[")) and _event(line) is None for line in text.split("\n"))


def _rollout_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.split("\n"):
        record = _event(line)
        if record is None:
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        record_payload = cast(dict[str, object], payload)
        for key in ("cli_version", "model_provider", "model", "effort"):
            if key not in fields:
                value = record_payload.get(key)
                if isinstance(value, str) and value:
                    fields[key] = value
    return fields


class _CodexAdapter:
    capabilities = Capabilities()

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        agent = context.agent
        sandbox = "workspace-write" if context.role.writes else "read-only"
        argv = [*agent.command, "--json", "-s", sandbox, "-m", agent.model]
        if agent.effort is not None:
            argv += ["-c", f"model_reasoning_effort={agent.effort}"]
        argv += [*agent.args, "-"]
        return LaunchSpec(tuple(argv), _prompt(context).encode("utf-8"))

    def collect(self, context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        stdout = _read(stdout_path)
        stderr = _read(stderr_path)
        events = [e for e in (_event(line) for line in stdout.split("\n")) if e is not None]

        session_id: str | None = None
        valid_thread = True
        for event in events:
            if event.get("type") != "thread.started":
                continue
            thread_id = event.get("thread_id")
            if not isinstance(thread_id, str) or not _THREAD_ID.fullmatch(thread_id):
                valid_thread = False
            elif session_id is not None and session_id != thread_id:
                valid_thread = False
            else:
                session_id = thread_id
        environment = context.environment if context.environment is not None else os.environ
        rollout_text = _rollout(session_id, environment) if valid_thread else ""
        fields = _rollout_fields(rollout_text)
        identity = Identity(
            model=fields.get("model"),
            provider=fields.get("model_provider"),
            effort=fields.get("effort"),
            session_id=session_id,
            cli_version=fields.get("cli_version"),
            skill_versions=_skill_versions(rollout_text, stdout),
        )

        def failed(state: State) -> AdapterOutcome:
            return AdapterOutcome(identity=identity, state=state)

        text: str | None = None
        completed = False
        pending_errors: list[dict[str, object]] = []
        failed_turns: list[dict[str, object]] = []
        for event in events:
            kind = event.get("type")
            if kind in {"turn.started", "error", "turn.failed"}:
                # An error invalidates all prior message/completion evidence.
                text = None
                completed = False
                if kind == "error":
                    pending_errors.append(event)
                elif kind == "turn.failed":
                    # Unlike transport errors, a failed turn is always fatal.
                    failed_turns.append(event)
            elif kind == "turn.completed":
                completed = True
                if text is not None and text.strip() and (
                    context.request.result_shape != "json" or _json_object(text) is not None
                ):
                    pending_errors.clear()
            elif kind == "item.completed":
                item = event.get("item")
                if not isinstance(item, dict) or item.get("type") != "agent_message":
                    continue
                candidate = item.get("text")
                text = candidate if isinstance(candidate, str) else None
                completed = False
        diagnostics = _diagnostics(stdout, stderr, [*pending_errors, *failed_turns])
        if _AUTHENTICATION.search(diagnostics):
            return failed("awaiting_authentication")
        if _APPROVAL.search(diagnostics):
            return failed("awaiting_approval")
        if not valid_thread or _malformed_events(stdout) or _malformed_events(rollout_text):
            return failed("response_failed")
        if pending_errors or failed_turns:
            return failed("response_failed")
        if not completed:
            return failed("response_failed")
        if text is None:
            return failed("response_failed")
        if context.request.result_shape == "json":
            payload = _json_object(text)
            if payload is None:
                return failed("response_failed")
        else:
            if not text.strip():
                return failed("response_failed")
            payload = text
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


ADAPTER = _CodexAdapter()
