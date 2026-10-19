"""Evidence required for PR review promotion, separate from generic collection.

Only producer diagnostics override recovery; quoted tool output remains data.
The parent calls this after the runner has confirmed stop and scrubbed secrets.
"""

import os
import stat
from contextlib import ExitStack
from pathlib import Path

from tools.agent_runner.adapters.dsh import _classify, _decode, _tool_denial
from tools.agent_runner.dsh_paths import review_exports

_LOG_LIMIT = 64 * 1024 * 1024
_FS_MARKERS = {
    f"[sandbox: file access denied under {mode} mode]"
    for mode in ("read-only", "workspace-write")
}
_HINT = (
    "[sandbox: escalation available — retry this exact operation once with "
    "sandbox_permissions (the narrowest wider mode that suffices) + justification; "
    "the approval prompt asks the user]"
)


def _log_bytes(attempt: Path) -> bytes:
    if not attempt.is_absolute() or ".." in attempt.parts:
        raise ValueError("noncanonical attempt")
    # Open every ancestor without following links. FIFO logs must not block.
    with ExitStack() as stack:
        directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        stack.callback(os.close, directory)
        for part in attempt.parts[1:]:
            directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            stack.callback(os.close, directory)
        descriptor = os.open("stdout.log", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        stream = stack.enter_context(os.fdopen(descriptor, "rb"))
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or info.st_size > _LOG_LIMIT
        ):
            raise ValueError("unsafe log")
        raw = stream.read(_LOG_LIMIT + 1)
        if len(raw) > _LOG_LIMIT:
            raise ValueError("oversize log")
        return raw


def _filesystem_denial(text: str) -> bool:
    prefix = "Error: code run failed (exception): ToolCallError: "
    if text.startswith(prefix):
        return text[len(prefix):].partition("\n")[0] in _FS_MARKERS
    if text.startswith("Error: "):
        return text[len("Error: "):] in {marker + "\n" + _HINT for marker in _FS_MARKERS}
    return False


def promotion_refusal(attempt_dir: Path) -> str | None:
    """Return a safe reason unless both fixed exports have native tool evidence."""
    try:
        events = [_decode(line) for line in _log_bytes(attempt_dir).decode("utf-8").split("\n") if line.strip()]
        if not all(isinstance(event, dict) for event in events):
            raise ValueError("non-object event")
        state, payload = _classify(events, "json")
        if state != "success" or not isinstance(payload, dict) or payload.get("status") != "staged":
            return "DSH review log does not show a successful staged result"
        pending: dict[str, dict] = {}
        seen: set[str] = set()
        written: set[Path] = set()
        expected = {review_exports(attempt_dir) / name for name in ("review.md", "findings.json")}
        for event in events:
            if event.get("type") == "tool_call":
                call_id = event["callId"]
                if call_id in seen:
                    return "DSH review log repeats a tool call identifier"
                seen.add(call_id)
                pending[call_id] = event
                arguments = event.get("input")
                if isinstance(arguments, dict) and arguments.get("sandbox_permissions") is not None:
                    return "DSH review attempted sandbox escalation"
            elif event.get("type") == "tool_result":
                call = pending.pop(event["callId"], None)
                if call is None:
                    return "DSH review tool result has no matching call"
                result = event["result"]
                if event["status"] == "error":
                    if _tool_denial(result) or _filesystem_denial(result):
                        return "DSH review contains a sandbox or approval refusal"
                    continue
                arguments = call.get("input")
                if call["tool"] not in {"write", "edit"} or not isinstance(arguments, dict):
                    continue
                file_path = arguments.get("file_path")
                if isinstance(file_path, str) and file_path and "\x00" not in file_path:
                    path = Path(file_path)
                    if not path.is_absolute():
                        path = attempt_dir / "worktree" / path
                    path = Path(os.path.normpath(path))
                    if path in expected:
                        written.add(path)
        if pending:
            return "DSH review log has unfinished tool calls"
        if written != expected:
            return "DSH review needs successful native write/edit for both fixed exports"
        return None
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        return "DSH review log is missing, unsafe, or malformed"
