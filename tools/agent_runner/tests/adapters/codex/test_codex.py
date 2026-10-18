"""Codex adapter: argv/stdin construction and JSONL/rollout collection."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from tools.agent_runner.adapters import AdapterContext
from tools.agent_runner.adapters.codex import ADAPTER
from tools.agent_runner.models import Agent, Request, Role


def _context(
    base: Path,
    *,
    writes: bool = False,
    effort: str | None = None,
    args: tuple[str, ...] = (),
    skills: tuple[str, ...] = (),
    sources: tuple[str, ...] = (),
    result_shape: str = "json",
    prompt: str = "PROMPT-UNIQUE-TEXT",
) -> AdapterContext:
    request = Request(
        run_id="run1",
        request_id="req1",
        agent_id="codex",
        role="inspect",
        work_dir=base / "worktree",
        prompt=prompt,
        deadline_seconds=60.0,
        result_shape=result_shape,  # type: ignore[arg-type]
    )
    agent = Agent(
        runtime="codex",
        command=["codex", "exec"],
        model="requested-model",
        effort=effort,
        args=list(args),
        skill_sources=list(sources),
    )
    role = Role(skills=list(skills), writes=writes, deadline_seconds=60.0, result_shape=result_shape)  # type: ignore[arg-type]
    attempt = base / "attempt"
    attempt.mkdir(parents=True, exist_ok=True)
    return AdapterContext(request, agent, role, base / "worktree", attempt / "receipt.json")


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _stdout_events(tmp_path: Path, *events: dict[str, object]) -> Path:
    """Build a completed stream; incomplete-stream tests write their tail explicitly."""
    if any(e.get("type") == "item.completed" and isinstance(e.get("item"), dict) and e["item"].get("type") == "agent_message" for e in events):
        events = (*events, {"type": "turn.completed"})
    return _write(tmp_path / "stdout.log", "".join(json.dumps(e) + "\n" for e in events))


def _rollout(home: Path, thread_id: str, records: list[dict[str, object]]) -> None:
    session_dir = home / "sessions" / "2026" / "10" / "06"
    session_dir.mkdir(parents=True)
    body = "".join(json.dumps(r) + "\n" for r in records)
    (session_dir / f"rollout-2026-10-06T00-00-00-{thread_id}.jsonl").write_text(body, encoding="utf-8")


def test_prepare_passes_prompt_over_stdin_with_read_only_sandbox(tmp_path: Path) -> None:
    spec = ADAPTER.prepare(_context(tmp_path))
    assert spec.argv[:2] == ("codex", "exec")
    assert "--json" in spec.argv
    assert spec.argv[spec.argv.index("-s") + 1] == "read-only"
    assert spec.argv[spec.argv.index("-m") + 1] == "requested-model"
    assert spec.argv[-1] == "-"
    assert all("PROMPT-UNIQUE-TEXT" not in argument for argument in spec.argv)
    assert "PROMPT-UNIQUE-TEXT" in spec.stdin.decode()


def test_prepare_write_role_uses_workspace_write_effort_and_args(tmp_path: Path) -> None:
    spec = ADAPTER.prepare(_context(tmp_path, writes=True, effort="high", args=("--flag", "v")))
    assert spec.argv[spec.argv.index("-s") + 1] == "workspace-write"
    pair = spec.argv[spec.argv.index("-c") + 1]
    assert pair == "model_reasoning_effort=high"
    flag_at = spec.argv.index("--flag")
    assert spec.argv[flag_at + 1] == "v"
    assert flag_at < spec.argv.index("-")


def test_prepare_appends_json_shape_and_skill_instruction(tmp_path: Path) -> None:
    spec = ADAPTER.prepare(_context(tmp_path, skills=("pr-review",)))
    text = spec.stdin.decode()
    assert "JSON" in text
    assert "$pr-review" in text


def test_collect_success_builds_receipt_and_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    thread_id = "01a11250-9702-73b2-aebb-2f8f7434d5d6"
    stdout = _stdout_events(
        tmp_path,
        {"type": "thread.started", "thread_id": thread_id},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"id": "item_0", "type": "reasoning", "text": "thinking"}},
        {"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": '{"answer": 1}'}},
        {"type": "turn.completed", "usage": {"input_tokens": 1}},
    )
    stderr = _write(tmp_path / "stderr.log", "")
    home = tmp_path / "codex-home"
    _rollout(
        home,
        thread_id,
        [
            {
                "type": "session_meta",
                "payload": {"session_id": thread_id, "cli_version": "observed-cli", "model_provider": "observed-provider"},
            },
            {"type": "turn_context", "payload": {"model": "requested-model", "effort": "observed-effort"}},
        ],
    )
    monkeypatch.setenv("CODEX_HOME", str(home))
    context = _context(tmp_path)
    outcome = ADAPTER.collect(context, stdout, stderr)
    assert outcome.state is None
    assert outcome.receipt is not None
    assert outcome.receipt.status == "success"
    assert outcome.receipt.payload == {"answer": 1}
    assert (outcome.receipt.run_id, outcome.receipt.request_id, outcome.receipt.agent_id, outcome.receipt.role) == (
        "run1",
        "req1",
        "codex",
        "inspect",
    )
    assert outcome.identity.session_id == thread_id
    assert outcome.identity.model == "requested-model"
    assert outcome.identity.effort == "observed-effort"
    assert outcome.identity.provider == "observed-provider"
    assert outcome.identity.cli_version == "observed-cli"


def test_collect_text_shape_returns_raw_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "missing"))
    stdout = _stdout_events(
        tmp_path,
        {"type": "thread.started", "thread_id": "t1"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "free form answer"}},
    )
    outcome = ADAPTER.collect(_context(tmp_path, result_shape="text"), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is not None
    assert outcome.receipt.payload == "free form answer"


def test_collect_turn_failed_is_response_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "missing"))
    stdout = _stdout_events(
        tmp_path,
        {"type": "thread.started", "thread_id": "t1"},
        {"type": "turn.failed", "error": {"message": "boom"}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is None
    assert outcome.state == "response_failed"


def test_collect_authentication_message_is_awaiting_authentication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "missing"))
    stdout = _write(tmp_path / "stdout.log", "")
    stderr = _write(tmp_path / "stderr.log", "ERROR: Not logged in. Please run 'codex login'.\n")
    outcome = ADAPTER.collect(_context(tmp_path), stdout, stderr)
    assert outcome.receipt is None
    assert outcome.state == "awaiting_authentication"


def test_collect_missing_agent_message_is_response_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "missing"))
    stdout = _stdout_events(
        tmp_path,
        {"type": "thread.started", "thread_id": "t1"},
        {"type": "turn.completed", "usage": {}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is None
    assert outcome.state == "response_failed"


def test_collect_non_dict_json_shape_is_response_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "missing"))
    stdout = _stdout_events(
        tmp_path,
        {"type": "item.completed", "item": {"type": "agent_message", "text": "plain prose, not json"}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is None
    assert outcome.state == "response_failed"


def test_collect_embedded_json_object_is_extracted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "missing"))
    stdout = _stdout_events(
        tmp_path,
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": 'Here is the result:\n{"k": "v", "n": 2}\nDone.'},
        },
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is not None
    assert outcome.receipt.payload == {"k": "v", "n": 2}


def test_collect_nested_json_object_returns_outer_object(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "missing"))
    text = 'Here is the result:\n```json\n{"findings": [{"id": "F1"}], "count": 1}\n```\nDone.'
    stdout = _stdout_events(
        tmp_path,
        {"type": "item.completed", "item": {"type": "agent_message", "text": text}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is not None
    assert outcome.receipt.payload == {"findings": [{"id": "F1"}], "count": 1}


def test_collect_authentication_words_in_output_do_not_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "missing"))
    stdout = _stdout_events(
        tmp_path,
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": "curl -sI https://api.example.com/",
                "aggregated_output": "HTTP/1.1 401 Unauthorized\nlogin required\n",
            },
        },
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": '{"finding": "API returns 401 Unauthorized without token"}'},
        },
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.state is None
    assert outcome.receipt is not None
    assert outcome.receipt.payload == {"finding": "API returns 401 Unauthorized without token"}


def test_collect_identity_fields_stay_null_without_rollout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "missing"))
    monkeypatch.delenv("HOME", raising=False)
    stdout = _stdout_events(
        tmp_path,
        {"type": "thread.started", "thread_id": "t-absent"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": '{"a": 1}'}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.identity.session_id == "t-absent"
    assert outcome.identity.model is None
    assert outcome.identity.effort is None
    assert outcome.identity.cli_version is None


def test_collect_skill_versions_hash_successfully_read_skill_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill = tmp_path / "skills" / "pr-review"
    skill.mkdir(parents=True)
    skill_md = skill / "SKILL.md"
    skill_md.write_text("skill body", encoding="utf-8")
    thread_id = "t-skill"
    home = tmp_path / "codex-home"
    mentioned = tmp_path / "skills" / "mentioned-only"
    mentioned.mkdir(parents=True)
    (mentioned / "SKILL.md").write_text("mentioned body", encoding="utf-8")
    _rollout(
        home,
        thread_id,
        [
            {
                "type": "response_item",
                "payload": {"type": "message", "content": [{"text": f"see {mentioned / 'SKILL.md'}"}]},
            },
            {"type": "turn_context", "payload": {"model": "m1"}},
        ],
    )
    monkeypatch.setenv("CODEX_HOME", str(home))
    stdout = _stdout_events(
        tmp_path,
        {"type": "thread.started", "thread_id": thread_id},
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": f"/bin/bash -lc 'cat {skill_md}'",
                "aggregated_output": "skill body",
                "exit_code": 0,
                "status": "completed",
            },
        },
        {"type": "item.completed", "item": {"type": "agent_message", "text": '{"a": 1}'}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    expected = hashlib.sha256(b"skill body").hexdigest()
    assert outcome.identity.skill_versions == {"pr-review": expected}


def test_collect_skill_path_mentioned_in_message_is_not_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill = tmp_path / "skills" / "pr-review"
    skill.mkdir(parents=True)
    skill_md = skill / "SKILL.md"
    skill_md.write_text("skill body", encoding="utf-8")
    thread_id = "t-mention"
    home = tmp_path / "codex-home"
    _rollout(
        home,
        thread_id,
        [
            {"type": "response_item", "payload": {"type": "message", "content": [{"text": f"read {skill_md}"}]}},
        ],
    )
    monkeypatch.setenv("CODEX_HOME", str(home))
    stdout = _stdout_events(
        tmp_path,
        {"type": "thread.started", "thread_id": thread_id},
        {"type": "item.completed", "item": {"type": "agent_message", "text": f'{{"used": "{skill_md}"}}'}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is not None
    assert outcome.identity.skill_versions == {}


@pytest.mark.parametrize(
    ("event_type", "status", "exit_code"),
    [
        ("item.started", "in_progress", None),
        ("item.completed", "failed", 1),
        ("item.completed", "completed", None),
        ("item.completed", "failed", 0),
    ],
    ids=["started-only", "failed", "unknown-exit", "failed-status"],
)
def test_collect_unproven_cat_reads_are_not_recorded(
    tmp_path: Path, event_type: str, status: str, exit_code: int | None
) -> None:
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b"actual skill")
    stdout = _stdout_events(
        tmp_path,
        {
            "type": event_type,
            "item": {
                "type": "command_execution",
                "command": f"cat {skill}",
                "aggregated_output": "",
                "status": status,
                "exit_code": exit_code,
            },
        },
        {"type": "item.completed", "item": {"type": "agent_message", "text": '{"ok": true}'}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is not None
    assert outcome.identity.skill_versions == {}


@pytest.mark.parametrize("command", ["echo {path}", "cat {path} && echo done"], ids=["echo", "compound-command"])
def test_collect_commands_without_unambiguous_read_evidence_are_not_recorded(tmp_path: Path, command: str) -> None:
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b"actual skill")
    stdout = _stdout_events(
        tmp_path,
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": command.format(path=skill),
                "aggregated_output": str(skill),
                "status": "completed",
                "exit_code": 0,
            },
        },
        {"type": "item.completed", "item": {"type": "agent_message", "text": '{"ok": true}'}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is not None
    assert outcome.identity.skill_versions == {}


@pytest.mark.parametrize("kind", ["prompt-echo", "tool-invocation", "parsed-command"])
def test_collect_rollout_without_successful_execution_is_not_read_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b"actual skill")
    payloads = {
        "prompt-echo": {
            "type": "message",
            "role": "user",
            "content": [
                {"command": f"cat {skill}", "arguments": {"path": str(skill), "input": f"cat {skill}"}},
            ],
        },
        "tool-invocation": {
            "type": "custom_tool_call",
            "name": "shell",
            "input": f"cat {skill}",
            "status": "completed",
            "call_id": "read1",
        },
        "parsed-command": {"type": "exec_command_begin", "parsed_cmd": [{"type": "read", "path": str(skill)}]},
    }
    home = tmp_path / "codex-home"
    _rollout(home, "synthetic-read", [{"type": "response_item", "payload": payloads[kind]}])
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.delenv("HOME", raising=False)
    stdout = _stdout_events(
        tmp_path,
        {"type": "thread.started", "thread_id": "synthetic-read"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": '{"ok": true}'}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is not None
    assert outcome.identity.skill_versions == {}


def test_collect_skill_version_stays_unknown_when_observed_content_differs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b"present body")
    stdout = _stdout_events(
        tmp_path,
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": f"/bin/bash -lc 'cat {skill}'",
                "aggregated_output": "observed body",
                "status": "completed",
                "exit_code": 0,
            },
        },
        {"type": "item.completed", "item": {"type": "agent_message", "text": '{"ok": true}'}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is not None
    assert outcome.identity.skill_versions == {}


def test_collect_skill_version_stays_unknown_when_file_deleted_after_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b"skill body")
    stdout = _stdout_events(
        tmp_path,
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": f"cat {skill}",
                "aggregated_output": "skill body",
                "status": "completed",
                "exit_code": 0,
            },
        },
        {"type": "item.completed", "item": {"type": "agent_message", "text": '{"ok": true}'}},
    )
    skill.unlink()
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is not None
    assert outcome.identity.skill_versions == {}


def test_collect_skill_version_stays_unknown_when_observed_content_is_truncated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill = tmp_path / "skills" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes(b"first line\nsecond line\n")
    stdout = _stdout_events(
        tmp_path,
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": f"cat {skill}",
                "aggregated_output": "first line\n",
                "status": "completed",
                "exit_code": 0,
            },
        },
        {"type": "item.completed", "item": {"type": "agent_message", "text": '{"ok": true}'}},
    )
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.receipt is not None
    assert outcome.identity.skill_versions == {}


def test_prepare_tells_model_to_read_configured_skill_source_paths(tmp_path: Path) -> None:
    skill = tmp_path / "worktree" / "skill-src" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("configured body", encoding="utf-8")
    context = _context(tmp_path, skills=("alpha",), sources=("skill-src",))
    spec = ADAPTER.prepare(context)
    text = spec.stdin.decode()
    assert f'Read the configured source of skill "alpha" before using it: {skill}' in text
    assert f"{skill}. This absolute path takes priority over native discovery." in text
    assert "$alpha" in text
    assert all(str(skill) not in argument for argument in spec.argv)
    assert skill.is_file() and (tmp_path / "worktree" / "skill-src" / "alpha").is_dir()


@pytest.mark.parametrize('diagnostic,state', [
    ('Not logged in', 'awaiting_authentication'),
    ('Approval required', 'awaiting_approval'),
    ('waiting for approval', 'awaiting_approval'),
    ('command failed', 'response_failed'),
])
@pytest.mark.parametrize('channel', ['stderr', 'error', 'turn.failed'])
def test_failure_diagnostics_override_prior_message(tmp_path: Path, diagnostic: str, state: str, channel: str) -> None:
    stdout = _stdout_events(tmp_path, {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{"ok": true}'}})
    stderr = _write(tmp_path / 'stderr.log', diagnostic if channel == 'stderr' else '')
    if channel != 'stderr':
        with stdout.open('a') as stream:
            stream.write(json.dumps({'type': channel, 'message': diagnostic}) + '\n')
    outcome = ADAPTER.collect(_context(tmp_path), stdout, stderr)
    if channel == 'stderr' and state == 'response_failed':
        # Generic stderr can be harmless progress; the core owns exit status.
        assert outcome.receipt is not None
    else:
        assert outcome.receipt is None
        assert outcome.state == state


@pytest.mark.parametrize('suffix', ['{"type":"item.completed",', '[{"type":', '{broken json}'])
def test_truncated_later_event_does_not_reuse_success(tmp_path: Path, suffix: str) -> None:
    stdout = _stdout_events(tmp_path, {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{"ok": true}'}})
    with stdout.open('a') as stream:
        stream.write(suffix)
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / 'stderr.log', ''))
    assert outcome.receipt is None
    assert outcome.state == 'response_failed'


def test_plain_progress_does_not_invalidate_completion(tmp_path: Path) -> None:
    stdout = _stdout_events(tmp_path, {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{"ok": true}'}})
    with stdout.open('a') as stream:
        stream.write('progress: local cleanup complete\n')
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path / 'stderr.log', ''))
    assert outcome.receipt is not None


@pytest.mark.parametrize('tail', ['', '{"type":"turn.started"}\n'])
def test_missing_or_unfinished_final_turn_is_failure(tmp_path: Path, tail: str) -> None:
    message = json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{"ok": true}'}}) + '\n'
    body = message if not tail else message + '{"type":"turn.completed"}\n' + tail
    outcome = ADAPTER.collect(_context(tmp_path), _write(tmp_path/'stdout.log', body), _write(tmp_path/'stderr.log', ''))
    assert outcome.receipt is None
    assert outcome.state == 'response_failed'


@pytest.mark.parametrize('thread_id', ['../foreign', '*', 'foreign?','bad/name','bad\\name',''])
def test_untrusted_thread_id_cannot_select_rollout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, thread_id: str) -> None:
    home = tmp_path / 'home'
    _rollout(home, 'foreign', [{'type': 'turn_context', 'payload': {'model': 'foreign-model'}}])
    monkeypatch.setenv('CODEX_HOME', str(home))
    stdout = _stdout_events(tmp_path, {'type': 'thread.started', 'thread_id': thread_id}, {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{"ok":true}'}})
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path/'stderr.log',''))
    assert outcome.receipt is None
    assert outcome.identity.model is None


@pytest.mark.parametrize('effective', ['CODEX_HOME', 'HOME', 'empty'])
def test_rollout_uses_effective_child_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, effective: str) -> None:
    from dataclasses import replace
    controller = tmp_path/'controller'
    child = tmp_path/'child'
    thread = 'same-thread'
    _rollout(controller, thread, [{'type':'turn_context','payload':{'model':'wrong-controller'}}])
    _rollout(child/'.codex', thread, [{'type':'turn_context','payload':{'model':'child-observed'}}])
    monkeypatch.setenv('CODEX_HOME', str(controller))
    environment = {'CODEX_HOME': str(child/'.codex')} if effective == 'CODEX_HOME' else {'HOME':str(child)} if effective == 'HOME' else {}
    context = replace(_context(tmp_path), environment=environment)
    stdout = _stdout_events(tmp_path, {'type':'thread.started','thread_id':thread}, {'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}})
    outcome = ADAPTER.collect(context, stdout, _write(tmp_path/'stderr.log',''))
    assert outcome.identity.model == (None if effective == 'empty' else 'child-observed')


@pytest.mark.parametrize('kind', ['suffix-collision', 'metadata-mismatch', 'symlink-escape', 'symlink-within-home'])
def test_rollout_cannot_borrow_identity_from_another_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    home = tmp_path/'home'
    thread = 'thread-a'
    other = 'prefix-thread-a' if kind == 'suffix-collision' else thread
    _rollout(home, other, [{'type':'session_meta','payload':{'id':'other-session' if kind == 'metadata-mismatch' else other,'model':'foreign'}}])
    if kind in {'symlink-escape', 'symlink-within-home'}:
        rollout = next(home.rglob('*.jsonl'))
        external = (home if kind == 'symlink-within-home' else tmp_path)/'external.jsonl'
        rollout.rename(external)
        rollout.symlink_to(external)
    monkeypatch.setenv('CODEX_HOME', str(home))
    stdout = _stdout_events(tmp_path, {'type':'thread.started','thread_id':thread}, {'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}})
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path/'stderr.log',''))
    assert outcome.identity.model is None


@pytest.mark.parametrize('tail', [
    [{'type':'turn.started'}, {'type':'turn.completed'}],
    [{'type':'item.completed','item':{'type':'agent_message','text':None}}, {'type':'turn.completed'}],
    [{'type':'item.completed','item':{'type':'agent_message','text':''}}, {'type':'turn.completed'}],
])
def test_latest_turn_cannot_reuse_an_earlier_message(tmp_path: Path, tail: list[dict[str, object]]) -> None:
    stdout = _stdout_events(tmp_path, {'type':'item.completed','item':{'type':'agent_message','text':'{"stale":true}'}})
    with stdout.open('a') as stream:
        for event in tail:
            stream.write(json.dumps(event)+'\n')
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path/'stderr.log',''))
    assert outcome.receipt is None
    assert outcome.state == 'response_failed'


def test_configured_source_read_can_prove_version_without_native_directory_name(tmp_path: Path) -> None:
    skill = tmp_path/'external-source'/'alpha'/'SKILL.md'
    skill.parent.mkdir(parents=True)
    skill.write_text('observed full body', encoding='utf-8')
    context = _context(tmp_path, skills=('alpha',), sources=(str(skill.parent.parent),))
    stdout = _stdout_events(tmp_path, {'type':'item.completed','item':{
        'type':'command_execution','command':f'cat {skill}', 'status':'completed','exit_code':0,'aggregated_output':'observed full body',
    }}, {'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}})
    outcome = ADAPTER.collect(context, stdout, _write(tmp_path/'stderr.log',''))
    assert outcome.identity.skill_versions == {'alpha':hashlib.sha256(b'observed full body').hexdigest()}


@pytest.mark.parametrize('thread_ids', [[None], [17], ['thread-a', 'thread-b']])
def test_invalid_or_ambiguous_thread_event_is_failure(tmp_path: Path, thread_ids: list[object]) -> None:
    events = [{'type':'thread.started','thread_id':value} for value in thread_ids]
    stdout = _stdout_events(tmp_path, *events, {'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}})
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path/'stderr.log',''))
    assert outcome.receipt is None
    assert outcome.state == 'response_failed'


def test_rollout_sessions_directory_cannot_escape_runtime_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    foreign = tmp_path/'foreign'
    _rollout(foreign, 'thread-a', [{'type':'turn_context','payload':{'model':'foreign-model'}}])
    home = tmp_path/'home'
    home.mkdir()
    (home/'sessions').symlink_to(foreign/'sessions', target_is_directory=True)
    monkeypatch.setenv('CODEX_HOME',str(home))
    stdout = _stdout_events(tmp_path, {'type':'thread.started','thread_id':'thread-a'}, {'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}})
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path/'stderr.log',''))
    assert outcome.identity.model is None


@pytest.mark.parametrize('text', ['[]', '[{"nested":true}]', '{}', '{"outer":{"nested":true},', 'prefix\n{"outer":{"nested":true},'])
def test_invalid_final_object_cannot_return_a_nested_fragment(tmp_path: Path, text: str) -> None:
    stdout = _stdout_events(tmp_path, {'type':'item.completed','item':{'type':'agent_message','text':text}})
    outcome = ADAPTER.collect(_context(tmp_path), stdout, _write(tmp_path/'stderr.log',''))
    assert outcome.receipt is None
    assert outcome.state == 'response_failed'


@pytest.mark.parametrize("bad_type", [[], {}])
@pytest.mark.parametrize("prior_success", [False, True])
def test_invalid_event_type_is_response_failed_with_identity(tmp_path: Path, bad_type: object, prior_success: bool) -> None:
    events = [{"type": "thread.started", "thread_id": "observed-thread"}]
    if prior_success:
        events.extend([
            {"type": "item.completed", "item": {"type": "agent_message", "text": '{"old": true}'}},
            {"type": "turn.completed"},
        ])
    events.append({"type": bad_type})
    stdout = _write(tmp_path / "stdout.log", "".join(json.dumps(event) + "\n" for event in events))
    context = replace(_context(tmp_path), environment={"CODEX_HOME": str(tmp_path / "missing")})
    outcome = ADAPTER.collect(context, stdout, _write(tmp_path / "stderr.log", ""))
    assert outcome.state == "response_failed" and outcome.receipt is None
    assert outcome.identity.session_id == "observed-thread"


@pytest.mark.parametrize("bad_type", [[], {}])
@pytest.mark.parametrize("diagnostic,state", [
    ("authentication required", "awaiting_authentication"),
    ("approval required", "awaiting_approval"),
])
def test_invalid_type_preserves_failure_diagnostic_precedence(tmp_path: Path, bad_type: object, diagnostic: str, state: str) -> None:
    stdout = _stdout_events(tmp_path, {"type": "thread.started", "thread_id": "observed-thread"}, {"type": bad_type})
    context = replace(_context(tmp_path), environment={"CODEX_HOME": str(tmp_path / "missing")})
    outcome = ADAPTER.collect(context, stdout, _write(tmp_path / "stderr.log", diagnostic))
    assert outcome.state == state and outcome.receipt is None
    assert outcome.identity.session_id == "observed-thread"
