"""pi adapter: launcher argv shape and NDJSON event collection."""

import hashlib
import json
import sys
from collections.abc import Iterable
from pathlib import Path

import pytest

from tools.agent_runner.adapters import AdapterContext
from tools.agent_runner.adapters.pi import ADAPTER
from tools.agent_runner.models import Agent, Assignment, Config, Role, Workflow
from tools.agent_runner.runner import run_workflow

# Only fake agents are launched here; drop AGENT_RUNNER_DEPTH inside each test so a runner agent can run them
pytestmark = pytest.mark.usefixtures("outside_runner")


def _session(session_id: str = "sess-1") -> dict[str, object]:
    return {"type": "session", "version": 3, "id": session_id, "timestamp": "t", "cwd": "/w"}


def _assistant(
    text: str = '{"ok": true}',
    *,
    model: str = "fixture-model",
    provider: str = "fixture-provider",
    thinking: str = "fixture-effort",
    stop_reason: str = "stop",
) -> dict[str, object]:
    return {
        "role": "assistant",
        "model": model,
        "provider": provider,
        "thinkingLevel": thinking,
        "stopReason": stop_reason,
        "content": [{"type": "thinking", "text": ""}, {"type": "text", "text": text}],
    }


def _agent_end(messages: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "type": "agent_end",
        "messages": messages
        or [
            {"role": "system", "content": [{"type": "text", "text": "sys"}]},
            {"role": "user", "content": [{"type": "text", "text": "THE PROMPT"}]},
            _assistant(),
        ],
    }


def _write_stdout(context: AdapterContext, lines: Iterable[str | dict[str, object]]) -> Path:
    path = context.receipt_path.parent / "stdout.log"
    path.write_text(
        "".join(line if isinstance(line, str) else json.dumps(line) + "\n" for line in lines),
        encoding="utf-8",
    )
    return path


def _write_stderr(context: AdapterContext, text: str) -> Path:
    path = context.receipt_path.parent / "stderr.log"
    path.write_text(text, encoding="utf-8")
    return path


def _collect(context: AdapterContext, lines: Iterable[str | dict[str, object]], stderr: str = ""):
    return ADAPTER.collect(context, _write_stdout(context, lines), _write_stderr(context, stderr))


def test_prepare_builds_launcher_argv(context: AdapterContext) -> None:
    spec = ADAPTER.prepare(context)
    command = context.agent.command
    assert spec.argv[: len(command)] == tuple(command)
    rest = spec.argv[len(command) :]
    assert rest[:7] == ("--print", "--mode", "json", "--no-session", "--no-approve", "--provider", "fixture-provider")
    assert spec.argv[spec.argv.index("--model") + 1] == context.agent.model
    assert spec.argv[spec.argv.index("--thinking") + 1] == context.agent.effort
    assert context.request.prompt.encode() in spec.stdin
    assert all(context.request.prompt != arg for arg in spec.argv)


def test_prepare_maps_skill_sources_and_args(context: AdapterContext) -> None:
    context.agent.provider = None
    context.agent.effort = None
    context.agent.skill_sources = ["/skills/a", "/skills/b"]
    context.agent.args = ["--offline"]
    spec = ADAPTER.prepare(context)
    assert "--provider" not in spec.argv and "--thinking" not in spec.argv
    skills = [spec.argv[i + 1] for i, arg in enumerate(spec.argv) if arg == "--skill"]
    assert skills == ["/skills/a", "/skills/b"]
    assert spec.argv[-1] == "--offline"


def test_collect_success_extracts_identity_and_payload(context: AdapterContext) -> None:
    outcome = _collect(context, [_session(), {"type": "agent_start"}, _agent_end(), {"type": "agent_settled"}])
    receipt = outcome.receipt
    assert receipt is not None and receipt.status == "success"
    assert receipt.payload == {"ok": True}
    assert outcome.identity.model == "fixture-model"
    assert outcome.identity.provider == "fixture-provider"
    assert outcome.identity.effort == "fixture-effort"
    assert outcome.identity.session_id == "sess-1"
    assert outcome.identity.cli_version is None


def test_exit_zero_without_agent_end_is_response_failed(context: AdapterContext) -> None:
    outcome = _collect(context, [_session(), {"type": "agent_start"}])
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_missing_agent_settled_is_response_failed(context: AdapterContext) -> None:
    outcome = _collect(context, [_session(), _agent_end()])
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_aborted_stop_reason_is_interrupted(context: AdapterContext) -> None:
    outcome = _collect(
        context,
        [_session(), _agent_end([_assistant(stop_reason="aborted")]), {"type": "agent_settled"}],
    )
    assert outcome.receipt is not None and outcome.receipt.status == "interrupted"


def test_unknown_stop_reason_is_response_failed(context: AdapterContext) -> None:
    outcome = _collect(
        context,
        [_session(), _agent_end([_assistant(stop_reason="length")]), {"type": "agent_settled"}],
    )
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_auth_stderr_reports_awaiting_authentication(context: AdapterContext) -> None:
    outcome = _collect(context, [_session()], stderr="provider login required: not authenticated")
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_authentication"


def test_non_json_lines_and_osc_sequences_are_skipped(context: AdapterContext) -> None:
    outcome = _collect(
        context,
        [
            "\x1b]777;notify;pi;done\x07\n",
            _session(),
            "plain progress line\n",
            _agent_end(),
            "truncated {\n",
            {"type": "agent_settled"},
        ],
    )
    assert outcome.receipt is not None and outcome.receipt.status == "success"


def test_text_shape_returns_concatenated_text(context: AdapterContext) -> None:
    context.role.result_shape = "text"
    message = _assistant("first")
    message["content"] = [{"type": "text", "text": "first "}, {"type": "text", "text": "second"}]
    outcome = _collect(context, [_session(), _agent_end([message]), {"type": "agent_settled"}])
    assert outcome.receipt is not None and outcome.receipt.payload == "first second"


def test_non_object_answer_fails_json_shape(context: AdapterContext) -> None:
    outcome = _collect(context, [_session(), _agent_end([_assistant("not json")]), {"type": "agent_settled"}])
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


@pytest.mark.parametrize("mode", ["configured", "mentioned", "failed", "partial", "mismatch", "complete"])
def test_only_completed_matching_full_read_is_hashed(context: AdapterContext, mode: str) -> None:
    skill = context.work_dir / "skills" / "sample" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("Skill body\n")
    context.agent.skill_sources = [str(skill.parent)]
    events = [_session()]
    if mode != "configured":
        events.append({"type": "tool_execution_start", "toolCallId": "read-1", "toolName": "read",
                       "args": {"path": str(skill), **({"limit": 1} if mode == "partial" else {})}})
    if mode not in {"configured", "mentioned"}:
        events.append({"type": "tool_execution_end", "toolCallId": "read-1", "toolName": "read",
                       "isError": mode == "failed", "result": {"content": [{"type": "text",
                       "text": "other" if mode == "mismatch" else "Skill body\n"}]}})
    outcome = _collect(context, [*events, _agent_end(), {"type": "agent_settled"}])
    expected = {"sample": hashlib.sha256(b"Skill body\n").hexdigest()} if mode == "complete" else {}
    assert outcome.identity.skill_versions == expected


def test_prepare_applies_role_skills(context: AdapterContext) -> None:
    source = context.work_dir / "skills"
    skill = source / "sample" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("body")
    context.agent.skill_sources = ["skills"]
    context.role.skills = ["sample", "native"]
    spec = ADAPTER.prepare(context)
    assert str(skill).encode() in spec.stdin
    assert b"sample" in spec.stdin and b"native" in spec.stdin
    assert context.request.prompt not in spec.argv


@pytest.mark.parametrize("events,status", [
    ([{"type": "agent_settled"}, _agent_end()], "response_failed"),
    ([_agent_end(), {"type": "agent_settled", "aborted": True}], "interrupted"),
    ([_agent_end(), {"type": "agent_settled"}, {"type": "agent_start"}], "response_failed"),
    ([_agent_end(), {"type": "agent_settled"}, _agent_end([_assistant(stop_reason="error")]),
      {"type": "agent_settled"}], "response_failed"),
    ([_agent_end([_assistant(stop_reason="error")]), _agent_end(), {"type": "agent_settled"}], "success"),
])
def test_final_lifecycle_dominates_earlier_turn(context: AdapterContext, events: list, status: str) -> None:
    outcome = _collect(context, [_session(), *events])
    assert outcome.receipt.status == status


@pytest.mark.parametrize("diagnostic,status", [("not authenticated", "awaiting_authentication"),
                                               ("requires approval", "awaiting_approval")])
def test_diagnostics_override_plausible_answer(context: AdapterContext, diagnostic: str, status: str) -> None:
    outcome = _collect(context, [_session(), _agent_end(), {"type": "agent_settled"}], stderr=diagnostic)
    assert outcome.receipt.status == status
    error = {"type": "error", "message": diagnostic}
    outcome = _collect(context, [_session(), error, _agent_end(), {"type": "agent_settled"}])
    assert outcome.receipt.status == status


def test_auth_words_in_successful_answer_are_harmless(context: AdapterContext) -> None:
    message = _assistant('{"note": "login requires approval"}')
    outcome = _collect(context, [_session(), _agent_end([message]), {"type": "agent_settled"}])
    assert outcome.receipt.status == "success"


def test_missing_identity_is_not_filled_from_config(context: AdapterContext) -> None:
    message = _assistant()
    for key in ("model", "provider", "thinkingLevel"):
        message.pop(key)
    outcome = _collect(context, [_agent_end([message]), {"type": "agent_settled"}])
    assert outcome.receipt.status == "success"
    assert outcome.identity.model is None and outcome.identity.provider is None
    assert outcome.identity.effort is None and outcome.identity.session_id is None
    assert outcome.identity.skill_versions == {}


@pytest.mark.parametrize("exit_code,expected", [(0, "success"), (7, "response_failed")])
def test_end_to_end_launch_and_collection(repository: Path, tmp_path: Path, exit_code: int, expected: str) -> None:
    capture = tmp_path / "capture.json"
    fixture = tmp_path / "fixture.jsonl"
    fixture.write_text(
        "".join(
            json.dumps(event) + "\n"
            for event in [_session(), {"type": "agent_start"}, _agent_end(), {"type": "agent_settled"}]
        )
    )
    config = Config(
        agents={
            "a": Agent(
                runtime="pi",
                command=[
                    sys.executable,
                    str(Path(__file__).with_name("fake_launcher.py")),
                    "--fake-capture",
                    str(capture),
                    "--fake-stdout",
                    str(fixture),
                    "--fake-exit", str(exit_code),
                ],
                model="fixture-model",
                provider="fixture-provider",
                effort="fixture-effort",
            )
        },
        roles={"inspect": Role(writes=False, deadline_seconds=60.0, result_shape="json")},
        workflows={"audit": Workflow(assignments={"inspect": Assignment(agents=["a"])})},
    )
    batch = run_workflow(config, "audit", "PROMPT", repository, output_dir=tmp_path / "run")
    assert batch.state == ("success" if exit_code == 0 else "failed")
    attempt = batch.results[0].attempts[0]
    assert attempt.state == expected
    assert attempt.exit_code == exit_code and attempt.stop_confirmed
    assert attempt.identity.model == "fixture-model"
    assert attempt.identity.provider == "fixture-provider"
    assert attempt.identity.effort == "fixture-effort"
    recorded = json.loads(capture.read_text())
    assert "PROMPT" in recorded["stdin"]
    assert all("PROMPT" not in arg for arg in recorded["argv"])
    assert "--print" in recorded["argv"] and "--mode" in recorded["argv"]
    assert recorded["argv"][recorded["argv"].index("--provider") + 1] == "fixture-provider"
    assert attempt.payload == {"ok": True}


def test_malformed_event_types_do_not_crash_collection(context: AdapterContext) -> None:
    outcome = _collect(context, [{"type": []}, {"type": {}}, _agent_end(), {"type": "agent_settled"}])
    assert outcome.receipt.status == "success"


def test_empty_skill_requires_observed_text_content(context: AdapterContext) -> None:
    skill = context.work_dir / "empty" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text("")
    outcome = _collect(context, [
        {"type": "tool_execution_start", "toolName": "read", "toolCallId": "empty",
         "args": {"path": str(skill)}},
        {"type": "tool_execution_end", "toolName": "read", "toolCallId": "empty",
         "isError": False, "result": {}},
        _agent_end(), {"type": "agent_settled"},
    ])
    assert outcome.identity.skill_versions == {}
