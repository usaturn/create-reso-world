"""Review promotion requires native output and preserves real policy failures."""

import json
from pathlib import Path

import pytest

from tools.agent_runner.dsh_review_evidence import promotion_refusal


DENIAL = (
    "Error: [sandbox: file access denied under workspace-write mode]\n"
    "[sandbox: escalation available — retry this exact operation once with "
    "sandbox_permissions (the narrowest wider mode that suffices) + justification; "
    "the approval prompt asks the user]"
)


def _stream(attempt: Path) -> list[dict]:
    rows: list[dict] = [
        {"type": "session", "sessionId": "fixture"},
        {"type": "status", "phase": "turn_start", "turn": 1},
    ]
    for name in ("review.md", "findings.json"):
        rows.extend([
            {"type": "tool_call", "callId": name, "tool": "write",
             "input": {"file_path": str(attempt / "dsh/tmp/exports" / name), "content": "fixture"}},
            {"type": "tool_result", "callId": name, "status": "completed", "result": "written"},
        ])
    rows.extend([
        {"type": "status", "phase": "turn_end", "turn": 1, "reason": {"kind": "completed"}},
        {"type": "final", "text": '{"status":"staged"}'},
    ])
    return rows


def _check(attempt: Path, rows: list[dict] | None) -> str | None:
    if rows is not None:
        (attempt / "stdout.log").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    return promotion_refusal(attempt)


def test_native_pair_and_recovered_read_error_are_accepted(tmp_path: Path) -> None:
    rows = _stream(tmp_path)
    rows[2:2] = [
        {"type": "tool_call", "tool": "read", "callId": "read", "input": {"file_path": "x.py"}},
        {"type": "tool_result", "callId": "read", "status": "error",
         "result": 'Error: offset 999 is out of range for "x.py" (403 lines)'},
    ]
    assert _check(tmp_path, rows) is None


@pytest.mark.parametrize("change", ["shell", "foreign-path", "failed", "duplicate"])
def test_missing_or_uncorrelated_native_success_is_refused(tmp_path: Path, change: str) -> None:
    rows = _stream(tmp_path)
    if change == "shell":
        rows[2]["tool"] = "bash"
    elif change == "foreign-path":
        rows[2]["input"]["file_path"] = str(tmp_path.parent / "other/review.md")
    elif change == "failed":
        rows[3]["status"] = "error"
        rows[3]["result"] = "Error: disk full"
    elif change == "unmatched":
        rows[3]["callId"] = "unknown"
    elif change == "duplicate":
        rows.insert(3, dict(rows[2]))
    else:
        rows[2].pop("input")
        rows[2]["truncated"] = True
    assert _check(tmp_path, rows) is not None


@pytest.mark.parametrize("diagnostic,tool", [
    (DENIAL, "write"),
])
def test_refusal_is_not_erased_by_later_native_success(tmp_path: Path, diagnostic: str, tool: str) -> None:
    rows = _stream(tmp_path)
    rows[2:2] = [
        {"type": "tool_call", "tool": tool, "callId": "denied", "input": {}},
        {"type": "tool_result", "callId": "denied", "status": "error", "result": diagnostic},
    ]
    assert _check(tmp_path, rows) is not None


def test_escalation_request_is_refused_even_if_result_claims_success(tmp_path: Path) -> None:
    rows = _stream(tmp_path)
    rows[2]["input"]["sandbox_permissions"] = "danger-full-access"
    assert _check(tmp_path, rows) is not None


@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_unsafe_log_is_refused_without_touching_its_target(tmp_path: Path, kind: str) -> None:
    target = tmp_path / "source"
    raw = "\n".join(json.dumps(row) for row in _stream(tmp_path))
    target.write_text(raw)
    log = tmp_path / "stdout.log"
    if kind == "malformed":
        log.write_text("not JSON")
    elif kind == "symlink":
        log.symlink_to(target)
    elif kind == "hardlink":
        log.hardlink_to(target)
    elif kind == "duplicate-json-key":
        log.write_text('{"type":"session","type":"final"}')
    assert _check(tmp_path, None) is not None
    assert target.read_text() == raw
