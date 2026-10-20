"""Parser boundaries: JSON strings are data, not record/fence delimiters.

Regressions catch Unicode record splitting, fence regex truncation, and Codex
retry errors being treated as terminal before a fresh completed response.
"""

import hashlib
import json
import os
import stat
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from tools.agent_runner.adapters import AdapterContext
from tools.agent_runner.adapters.claude_code import ADAPTER as CLAUDE
from tools.agent_runner.adapters.codex import ADAPTER as CODEX
from tools.agent_runner.adapters.cursor import ADAPTER as CURSOR
from tools.agent_runner.adapters.devin import ADAPTER as DEVIN
from tools.agent_runner.adapters.pi import ADAPTER as PI
from tools.agent_runner.models import Agent, Request, Role

_ADAPTERS = {"claude-code": CLAUDE, "pi": PI, "codex": CODEX, "cursor": CURSOR, "devin": DEVIN}
_JSONL = ("claude-code", "pi", "codex", "cursor")
_SEPARATORS = ("\u2028", "\u2029", "\u0085")


def _context(base: Path, runtime: str) -> AdapterContext:
    work = base / "work"
    work.mkdir()
    attempt = base / "attempt"
    attempt.mkdir()
    request = Request(run_id="r", request_id="q", agent_id="a", role="inspect", work_dir=work,
                      prompt="inspect", deadline_seconds=30, result_shape="json")
    return AdapterContext(request, Agent(runtime=runtime, command=["unused"], model="requested"),
                          Role(writes=False, deadline_seconds=30, result_shape="json"), work, attempt / "receipt.json", environment={})


def _jsonl(events: list[dict]) -> str:
    # Literal Unicode is essential: escaped fixtures never exercised splitlines.
    return "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events)


def _message(text: object) -> dict:
    return {"type": "item.completed", "item": {"type": "agent_message", "text": text}}


def _events(runtime: str, text: str, model: str = "observed", session: str = "session") -> list[dict]:
    if runtime == "claude-code":
        return [{"type": "system", "subtype": "init", "model": model, "session_id": session},
                {"type": "assistant", "message": {"model": model}},
                {"type": "result", "subtype": "success", "is_error": False, "result": text}]
    if runtime == "pi":
        return [{"type": "session", "id": session}, {"type": "agent_end", "messages": [
            {"role": "assistant", "model": model, "provider": model, "thinkingLevel": model,
             "stopReason": "stop", "content": [{"type": "text", "text": text}]}]}, {"type": "agent_settled"}]
    if runtime == "cursor":
        return [{"type": "system", "subtype": "init", "model": model, "session_id": session},
                {"type": "result", "subtype": "success", "is_error": False, "result": text}]
    return [{"type": "thread.started", "thread_id": "session"}, _message(text), {"type": "turn.completed"}]


def _export(text: str, model: str = "observed") -> dict:
    return {"session_id": "session", "agent": {"model_name": model},
            "steps": [{"source": "agent", "message": text}]}


def _collect(context: AdapterContext, body: str, *, export: dict | None = None, stderr: str = ""):
    out = context.receipt_path.parent / "stdout.log"
    err = out.with_name("stderr.log")
    out.write_text(body, encoding="utf-8")
    err.write_text(stderr, encoding="utf-8")
    if export is not None:
        out.with_name("export.json").write_text(json.dumps(export, ensure_ascii=False), encoding="utf-8")
    return _ADAPTERS[context.agent.runtime].collect(context, out, err)


def _rollout(context: AdapterContext, records: list[dict]) -> AdapterContext:
    home = context.work_dir / "codex-home"
    directory = home / "sessions" / "2026" / "10" / "18"
    directory.mkdir(parents=True)
    (directory / "rollout-2026-10-18T00-00-00-session.jsonl").write_text(_jsonl(records), encoding="utf-8")
    return replace(context, environment={"CODEX_HOME": str(home)})


def _success(outcome, payload: dict) -> None:
    assert outcome.state is None
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.receipt.payload == payload


@pytest.mark.parametrize("runtime", _JSONL)
@pytest.mark.parametrize("separator", _SEPARATORS)
def test_literal_unicode_preserves_payload_and_observed_identity(tmp_path: Path, runtime: str, separator: str) -> None:
    context = _context(tmp_path, runtime)
    observed = "observed" + separator + "model"
    payload = {"note": "data" + separator + "authentication required"}
    if runtime == "codex":
        context = _rollout(context, [{"type": "session_meta", "payload": {"note": observed, "id": "session"}},
                                    {"type": "turn_context", "payload": {"model": observed, "effort": observed,
                                                                         "model_provider": observed}}])
    outcome = _collect(context, _jsonl(_events(runtime, json.dumps(payload, ensure_ascii=False), observed, observed)))
    _success(outcome, payload)
    assert outcome.identity.model == observed
    assert outcome.identity.session_id == ("session" if runtime == "codex" else observed)
    if runtime in {"pi", "codex"}:
        assert outcome.identity.provider == observed and outcome.identity.effort == observed


@pytest.mark.parametrize("runtime", ("pi", "codex", "cursor"))
@pytest.mark.parametrize("separator", _SEPARATORS)
def test_literal_unicode_full_skill_read_is_hashed(tmp_path: Path, runtime: str, separator: str) -> None:
    context = _context(tmp_path, runtime)
    skill = context.work_dir / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    content = "first" + separator + "second\n"
    skill.write_text(content, encoding="utf-8")
    if runtime == "pi":
        evidence = [{"type": "tool_execution_start", "toolName": "read", "toolCallId": "read",
                     "args": {"path": str(skill)}},
                    {"type": "tool_execution_end", "toolName": "read", "toolCallId": "read", "isError": False,
                     "result": {"content": [{"type": "text", "text": content}]}}]
    elif runtime == "codex":
        evidence = [{"type": "item.completed", "item": {"type": "command_execution", "command": f"cat {skill}",
                     "status": "completed", "exit_code": 0, "aggregated_output": content}}]
    else:
        evidence = [{"type": "tool_call", "subtype": "completed", "tool_call": {"readToolCall": {"result": {
            "success": {"path": str(skill), "content": content, "exceededLimit": False, "isEmpty": False,
                        "readRange": {"startLine": 1, "endLine": 1}, "totalLines": 1}}}}}]
    outcome = _collect(context, _jsonl([*evidence, *_events(runtime, '{"ok":true}')]))
    _success(outcome, {"ok": True})
    assert outcome.identity.skill_versions == {"alpha": hashlib.sha256(content.encode()).hexdigest()}


@pytest.mark.parametrize("separator", _SEPARATORS)
def test_codex_rollout_unicode_skill_evidence_survives_reparsing(tmp_path: Path, separator: str) -> None:
    context = _context(tmp_path, "codex")
    skill = context.work_dir / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    content = "body" + separator + "end"
    skill.write_text(content, encoding="utf-8")
    context = _rollout(context, [{"type": "item.completed", "item": {"type": "command_execution",
        "command": f"cat {skill}", "status": "completed", "exit_code": 0, "aggregated_output": content}}])
    outcome = _collect(context, _jsonl(_events("codex", '{"ok":true}')))
    _success(outcome, {"ok": True})
    assert outcome.identity.skill_versions == {"alpha": hashlib.sha256(content.encode()).hexdigest()}


@pytest.mark.parametrize("separator", _SEPARATORS)
def test_codex_unicode_session_metadata_cannot_hide_mismatch(tmp_path: Path, separator: str) -> None:
    context = _rollout(_context(tmp_path, "codex"), [
        {"type": "session_meta", "payload": {"note": "data" + separator + "end", "id": "foreign"}},
        {"type": "turn_context", "payload": {"model": "foreign-model"}}])
    outcome = _collect(context, _jsonl(_events("codex", '{"ok":true}')))
    _success(outcome, {"ok": True})
    assert outcome.identity.model is None


@pytest.mark.parametrize("runtime", _JSONL)
@pytest.mark.parametrize("separator", _SEPARATORS[:2])
def test_unicode_in_failure_event_keeps_diagnostic_classification(tmp_path: Path, runtime: str, separator: str) -> None:
    context = _context(tmp_path, runtime)
    body = _jsonl([*_events(runtime, '{"ok":true}'),
                   {"type": "error", "message": "transport" + separator + "authentication required"}])
    outcome = _collect(context, body)
    assert outcome.receipt is None or outcome.receipt.payload is None
    assert (outcome.state or outcome.receipt.status) == "awaiting_authentication"


@pytest.mark.parametrize("runtime", _JSONL)
def test_unicode_success_cannot_hide_corrupt_lf_record(tmp_path: Path, runtime: str) -> None:
    context = _context(tmp_path, runtime)
    outcome = _collect(context, _jsonl(_events(runtime, '{"note":"a\u2028b"}')) + '{"type":')
    assert (outcome.state or outcome.receipt.status) == "response_failed"
    assert outcome.receipt is None or outcome.receipt.payload is None


@pytest.mark.parametrize("runtime", tuple(_ADAPTERS))
def test_fenced_json_with_nested_code_backticks_is_data(tmp_path: Path, runtime: str) -> None:
    context = _context(tmp_path, runtime)
    payload = {"findings": [{"code": "```python\nprint('ok')\n```", "note": "literal ``` too"}]}
    text = "```json\n" + json.dumps(payload) + "\n```\nprogress: saved"
    outcome = _collect(context, text if runtime == "devin" else _jsonl(_events(runtime, text)),
                       export=_export(text) if runtime == "devin" else None)
    _success(outcome, payload)


@pytest.mark.parametrize("runtime", ("claude-code", "pi"))
@pytest.mark.parametrize("text", ['```json\n{"ok":true}', '```json\n{"outer":{"ok":true},\n```'])
def test_invalid_fence_cannot_salvage_inner_json(tmp_path: Path, runtime: str, text: str) -> None:
    outcome = _collect(_context(tmp_path, runtime), _jsonl(_events(runtime, text)))
    assert outcome.receipt.status == "response_failed" and outcome.receipt.payload is None


@pytest.mark.parametrize("channel", ("stdout", "atif"))
@pytest.mark.parametrize("bad,state", [
    ('```json\n{"ok":true}', "response_failed"),
    ('```json\n{"outer":{"ok":true},\n```', "response_failed"),
    ('```json\n{"ok":true}\n```\nError: not logged in', "awaiting_authentication"),
    ('```json\n{"ok":true}\n```\nApproval required', "awaiting_approval"),
    ('```json\n{"ok":true}\n```\n{"second":', "response_failed"),
    ('```json\n{"ok":true}\n```\n{"second":true}', "response_failed"),
])
def test_devin_fence_failure_in_either_channel_is_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                          channel: str, bad: str, state: str) -> None:
    context = _context(tmp_path, "devin")
    attempt = context.receipt_path.parent
    good = '```json\n{"ok":true}\n```'
    (attempt / "stdout.log").write_text(bad if channel == "stdout" else good)
    (attempt / "stderr.log").write_text("")
    (attempt / "export.json").write_text(json.dumps(_export(bad if channel == "atif" else good)))
    context.receipt_path.write_bytes(b"existing receipt must not change")
    os.link(context.receipt_path, tmp_path / "receipt-peer")
    (tmp_path / "export-link").symlink_to(attempt / "export.json")
    (attempt / "stdout.log").chmod(0o640)

    def snapshot() -> dict:
        result = {}
        for path in tmp_path.rglob("*"):
            mode = path.lstat().st_mode
            result[str(path.relative_to(tmp_path))] = (
                stat.S_IFMT(mode), stat.S_IMODE(mode),
                os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None)
        return result

    def no_process(*args, **kwargs):
        pytest.fail("collect must not launch an external command")

    monkeypatch.setattr(subprocess, "Popen", no_process)
    monkeypatch.setattr(os, "system", no_process)
    before = snapshot()
    outcome = DEVIN.collect(context, attempt / "stdout.log", attempt / "stderr.log")
    assert snapshot() == before
    assert outcome.receipt.status == state and outcome.receipt.payload is None


@pytest.mark.parametrize("diagnostic", ("transport temporarily unavailable", "authentication required", "approval required"))
@pytest.mark.parametrize("restart", (False, True))
def test_codex_fresh_completed_message_recovers_error(tmp_path: Path, diagnostic: str, restart: bool) -> None:
    events = [_message('{"stale":true}'), {"type": "turn.completed"}, {"type": "error", "message": diagnostic}]
    if restart:
        events.append({"type": "turn.started"})
    events.extend([_message('{"fresh":true}'), {"type": "turn.completed"}])
    outcome = _collect(_context(tmp_path, "codex"), _jsonl(events))
    _success(outcome, {"fresh": True})


@pytest.mark.parametrize("tail", [
    [], [{"type": "turn.completed"}], [_message('{"fresh":true}')],
    [{"type": "turn.completed"}, _message('{"fresh":true}')],
    [_message(None), {"type": "turn.completed"}],
    [_message(""), {"type": "turn.completed"}],
    [_message('{"unfinished":'), {"type": "turn.completed"}],
    [_message('{"fresh":true}'), {"type": "turn.completed"}, {"type": "turn.started"}],
    [_message('{"fresh":true}'), {"type": "turn.completed"}, {"type": "error", "message": "terminal"}],
    [{"type": "turn.failed"}, _message('{"fresh":true}'), {"type": "turn.completed"}],
])
def test_codex_recovery_requires_new_complete_message_and_terminal_success(tmp_path: Path, tail: list[dict]) -> None:
    events = [_message('{"stale":true}'), {"type": "turn.completed"}, {"type": "error", "message": "transport"}, *tail]
    outcome = _collect(_context(tmp_path, "codex"), _jsonl(events))
    assert outcome.state == "response_failed" and outcome.receipt is None


@pytest.mark.parametrize("channel", ("stderr", "non-json"))
@pytest.mark.parametrize("diagnostic,state", [("authentication required", "awaiting_authentication"),
                                              ("approval required", "awaiting_approval")])
def test_codex_recovery_does_not_clear_other_diagnostic_channels(tmp_path: Path, channel: str,
                                                               diagnostic: str, state: str) -> None:
    body = _jsonl([{"type": "error", "message": "temporary"}, _message('{"fresh":true}'), {"type": "turn.completed"}])
    outcome = _collect(_context(tmp_path, "codex"), body + (diagnostic if channel == "non-json" else ""),
                       stderr=diagnostic if channel == "stderr" else "")
    assert outcome.state == state and outcome.receipt is None


def test_codex_corrupt_event_cannot_be_recovered_by_success(tmp_path: Path) -> None:
    body = _jsonl([{"type": "error", "message": "transport"}]) + '{"type":\n' + _jsonl([
        _message('{"fresh":true}'), {"type": "turn.completed"}])
    outcome = _collect(_context(tmp_path, "codex"), body)
    assert outcome.state == "response_failed" and outcome.receipt is None


@pytest.mark.parametrize("separator", _SEPARATORS[:2])
def test_codex_unicode_rollout_cannot_hide_corrupt_lf_record(tmp_path: Path, separator: str) -> None:
    context = _rollout(_context(tmp_path, "codex"), [
        {"type": "turn_context", "payload": {"model": "observed" + separator + "model"}}])
    rollout = next(context.work_dir.rglob("*.jsonl"))
    with rollout.open("a") as stream:
        stream.write('{"type":')
    outcome = _collect(context, _jsonl(_events("codex", '{"ok":true}')))
    assert outcome.state == "response_failed" and outcome.receipt is None
    assert outcome.identity.model == "observed" + separator + "model"


@pytest.mark.parametrize("diagnostic,state", [("authentication required", "awaiting_authentication"),
                                              ("approval required", "awaiting_approval")])
@pytest.mark.parametrize("tail", [
    [_message('{"fresh":true}')],
    [{"type": "turn.completed"}],
    [_message('{"unfinished":'), {"type": "turn.completed"}],
])
def test_codex_unverified_recovery_keeps_pending_diagnostic(tmp_path: Path, diagnostic: str,
                                                          state: str, tail: list[dict]) -> None:
    body = _jsonl([{"type": "error", "message": diagnostic}, *tail])
    outcome = _collect(_context(tmp_path, "codex"), body)
    assert outcome.state == state and outcome.receipt is None


@pytest.mark.parametrize("channel", ("stdout", "atif"))
@pytest.mark.parametrize("diagnostic", ("Error: not logged in", "Approval required"))
@pytest.mark.parametrize("separator", _SEPARATORS)
def test_devin_unicode_diagnostic_inside_json_remains_data(tmp_path: Path, channel: str,
                                                         diagnostic: str, separator: str) -> None:
    context = _context(tmp_path, "devin")
    payload = {"note": "example" + separator + diagnostic}
    text = json.dumps(payload, ensure_ascii=False)
    good = '{"ok":true}'
    # stdout concatenates every agent message and ends with the final ATIF answer (#188),
    # so the stdout-only case carries the text in an earlier message.
    final = text if channel == "atif" else good
    outcome = _collect(context, (text if channel == "stdout" else "") + final, export=_export(final))
    _success(outcome, payload if channel == "atif" else {"ok": True})


@pytest.mark.parametrize("separator", _SEPARATORS)
def test_devin_export_unicode_remains_json_data(tmp_path: Path, separator: str) -> None:
    context = _context(tmp_path, "devin")
    payload = {"note": "data" + separator + "end"}
    text = json.dumps(payload, ensure_ascii=False)
    observed = "observed" + separator + "model"
    outcome = _collect(context, text, export=_export(text, observed))
    _success(outcome, payload)
    assert outcome.identity.model == observed
