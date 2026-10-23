"""Parser boundaries: JSON strings are data, not record/fence delimiters.

Regressions catch Unicode record splitting, fence regex truncation, and Codex
retry errors being treated as terminal before a fresh completed response.
"""

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


@pytest.mark.parametrize("separator", _SEPARATORS[:1])
def test_codex_unicode_session_metadata_cannot_hide_mismatch(tmp_path: Path, separator: str) -> None:
    context = _rollout(_context(tmp_path, "codex"), [
        {"type": "session_meta", "payload": {"note": "data" + separator + "end", "id": "foreign"}},
        {"type": "turn_context", "payload": {"model": "foreign-model"}}])
    outcome = _collect(context, _jsonl(_events("codex", '{"ok":true}')))
    _success(outcome, {"ok": True})
    assert outcome.identity.model is None


@pytest.mark.parametrize("runtime", ("pi",))
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


@pytest.mark.parametrize(
    "bad,state,channel",
    [
        ('```json\n{"ok":true}', "response_failed", "atif"),
    ],
    ids=[
        "```json\\n{\"ok\":true}-response_failed-atif",
    ],
)
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


@pytest.mark.parametrize(
    "restart,diagnostic",
    [
        (False, "authentication required"),
    ],
    ids=[
        "False-authentication required",
    ],
)
def test_codex_fresh_completed_message_recovers_error(tmp_path: Path, diagnostic: str, restart: bool) -> None:
    events = [_message('{"stale":true}'), {"type": "turn.completed"}, {"type": "error", "message": diagnostic}]
    if restart:
        events.append({"type": "turn.started"})
    events.extend([_message('{"fresh":true}'), {"type": "turn.completed"}])
    outcome = _collect(_context(tmp_path, "codex"), _jsonl(events))
    _success(outcome, {"fresh": True})


@pytest.mark.parametrize("tail", [
        [{"type": "turn.failed"}, _message('{"fresh":true}'), {"type": "turn.completed"}],
])
def test_codex_recovery_requires_new_complete_message_and_terminal_success(tmp_path: Path, tail: list[dict]) -> None:
    events = [_message('{"stale":true}'), {"type": "turn.completed"}, {"type": "error", "message": "transport"}, *tail]
    outcome = _collect(_context(tmp_path, "codex"), _jsonl(events))
    assert outcome.state == "response_failed" and outcome.receipt is None


@pytest.mark.parametrize(
    "diagnostic,state,channel",
    [
        ("authentication required", "awaiting_authentication", "non-json"),
    ],
    ids=[
        "authentication required-awaiting_authentication-non-json",
    ],
)
def test_codex_recovery_does_not_clear_other_diagnostic_channels(tmp_path: Path, channel: str,
                                                               diagnostic: str, state: str) -> None:
    body = _jsonl([{"type": "error", "message": "temporary"}, _message('{"fresh":true}'), {"type": "turn.completed"}])
    outcome = _collect(_context(tmp_path, "codex"), body + (diagnostic if channel == "non-json" else ""),
                       stderr=diagnostic if channel == "stderr" else "")
    assert outcome.state == state and outcome.receipt is None


@pytest.mark.parametrize("separator", _SEPARATORS[:1])
def test_codex_unicode_rollout_cannot_hide_corrupt_lf_record(tmp_path: Path, separator: str) -> None:
    context = _rollout(_context(tmp_path, "codex"), [
        {"type": "turn_context", "payload": {"model": "observed" + separator + "model"}}])
    rollout = next(context.work_dir.rglob("*.jsonl"))
    with rollout.open("a") as stream:
        stream.write('{"type":')
    outcome = _collect(context, _jsonl(_events("codex", '{"ok":true}')))
    assert outcome.state == "response_failed" and outcome.receipt is None
    assert outcome.identity.model == "observed" + separator + "model"
