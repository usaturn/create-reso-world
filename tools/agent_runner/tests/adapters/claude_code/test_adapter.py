"""claude-code adapter: launch spec shape and stream-json collection."""

import json
import sys
from collections.abc import Iterable
from pathlib import Path

import pytest

from tools.agent_runner.adapters import AdapterContext
from tools.agent_runner.adapters.claude_code import ADAPTER
from tools.agent_runner.models import Agent, Assignment, Config, Role, Workflow
from tools.agent_runner.runner import run_workflow

# Only fake agents are launched here; drop AGENT_RUNNER_DEPTH inside each test so a runner agent can run them
pytestmark = pytest.mark.usefixtures("outside_runner")


def _init(model: str = "observed-model") -> dict[str, object]:
    return {
        "type": "system",
        "subtype": "init",
        "claude_code_version": "fixture-version",
        "model": model,
        "session_id": "session-1",
        "tools": [],
        "skills": [],
        "slash_commands": [],
    }


def _assistant(text: str, model: str = "observed-model") -> dict[str, object]:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "model": model, "content": [{"type": "text", "text": text}]},
    }


def _result(
    text: str = '{"ok": true}',
    *,
    subtype: str = "success",
    is_error: bool = False,
    denials: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "type": "result",
        "subtype": subtype,
        "is_error": is_error,
        "result": text,
        "permission_denials": denials or [],
        "session_id": "session-1",
        "num_turns": 1,
    }


def _stream(events: Iterable[dict[str, object]]) -> str:
    return "".join(json.dumps(event) + "\n" for event in events)


def _write_stdout(context: AdapterContext, *events: dict[str, object]) -> Path:
    path = context.receipt_path.parent / "stdout.log"
    path.write_text(_stream(events), encoding="utf-8")
    return path


def _write_stderr(context: AdapterContext, text: str) -> Path:
    path = context.receipt_path.parent / "stderr.log"
    path.write_text(text, encoding="utf-8")
    return path


def _collect(context: AdapterContext, *events: dict[str, object], stderr: str = ""):
    return ADAPTER.collect(context, _write_stdout(context, *events), _write_stderr(context, stderr))


def test_prepare_builds_stream_json_launch(context: AdapterContext) -> None:
    spec = ADAPTER.prepare(context)
    command = context.agent.command
    assert spec.argv[: len(command)] == tuple(command)
    rest = spec.argv[len(command) :]
    assert rest[:6] == ("-p", "--output-format", "stream-json", "--verbose", "--model", context.agent.model)
    assert "--dangerously-skip-permissions" in rest
    assert "--effort" not in rest
    assert context.request.prompt.encode() in spec.stdin
    assert "JSON object" in spec.stdin.decode()
    assert all(context.request.prompt != arg for arg in spec.argv)


def test_prepare_maps_effort_and_appends_agent_args(context: AdapterContext) -> None:
    context.agent.effort = "high"
    context.agent.args = ["--bare", "--add-dir", "/extra"]
    spec = ADAPTER.prepare(context)
    assert spec.argv[spec.argv.index("--effort") + 1] == "high"
    assert spec.argv[-3:] == ("--bare", "--add-dir", "/extra")


def test_collect_success_extracts_identity_and_json_payload(context: AdapterContext) -> None:
    outcome = _collect(context, _init(), _assistant('{"ok": true}'), _result())
    receipt = outcome.receipt
    assert receipt is not None and receipt.status == "success"
    assert receipt.payload == {"ok": True}
    assert (receipt.run_id, receipt.request_id, receipt.agent_id, receipt.role) == (
        context.request.run_id,
        context.request.request_id,
        context.request.agent_id,
        context.request.role,
    )
    assert outcome.identity.model == "observed-model"
    assert outcome.identity.session_id == "session-1"
    assert outcome.identity.cli_version == "fixture-version"
    assert outcome.identity.provider is None and outcome.identity.effort is None


def test_assistant_model_overrides_init_model(context: AdapterContext) -> None:
    outcome = _collect(context, _init("router-alias"), _assistant("{}", "observed-model"), _result("{}"))
    assert outcome.identity.model == "observed-model"


def test_collect_success_text_shape(context: AdapterContext) -> None:
    context.role.result_shape = "text"
    outcome = _collect(context, _init(), _result("plain answer"))
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.receipt.payload == "plain answer"


def test_non_object_answer_fails_json_shape(context: AdapterContext) -> None:
    outcome = _collect(context, _init(), _result("not json"))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"
    assert outcome.receipt.payload is None


def test_json_fence_answer_parses(context: AdapterContext) -> None:
    outcome = _collect(context, _init(), _result('Here:\n```json\n{"x": 1}\n```\n'))
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.receipt.payload == {"x": 1}


def test_permission_denials_report_awaiting_approval(context: AdapterContext) -> None:
    denials: list[dict[str, object]] = [{"tool": "Bash", "command": "rm -rf /"}]
    outcome = _collect(context, _init(), _result(denials=denials))
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_approval"


@pytest.mark.parametrize("is_error", [True, False])
def test_error_subtype_reports_response_failed(context: AdapterContext, is_error: bool) -> None:
    outcome = _collect(context, _init(), _result("boom", subtype="error_during_execution", is_error=is_error))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_auth_error_text_reports_awaiting_authentication(context: AdapterContext) -> None:
    outcome = _collect(
        context,
        _result("Error: not logged in. Run claude login.", subtype="error", is_error=True),
    )
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_authentication"


def test_missing_result_with_auth_stderr_reports_authentication(context: AdapterContext) -> None:
    outcome = _collect(context, _init(), stderr="401 Unauthorized: invalid api key")
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_authentication"


def test_missing_result_reports_response_failed(context: AdapterContext) -> None:
    outcome = _collect(context, _init(), _assistant("partial"))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_garbled_and_non_json_lines_are_skipped(context: AdapterContext) -> None:
    path = context.receipt_path.parent / "stdout.log"
    init = _init("m0")
    init["session_id"] = "s"
    init["claude_code_version"] = "9"
    lines = [
        "\x1b]777;notify;done\x07",
        json.dumps(init),
        "not json at all",
        json.dumps(_result('{"ok":1}')),
        "truncated {",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outcome = ADAPTER.collect(context, path, _write_stderr(context, ""))
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.identity.model == "m0" and outcome.identity.cli_version == "9"


def test_skill_invocation_alone_does_not_prove_file_read(context: AdapterContext) -> None:
    skill = context.work_dir / ".claude" / "skills" / "find-docs" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: find-docs\n---\nbody\n", encoding="utf-8")
    use: dict[str, object] = {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "model": "m",
            "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "find-docs"}}],
        },
    }
    outcome = _collect(context, _init(), use, _result())
    assert outcome.identity.skill_versions == {}


def test_init_skill_listing_is_not_load_evidence(context: AdapterContext) -> None:
    init = _init()
    init["skills"] = ["installed-but-not-read"]
    outcome = _collect(context, init, _result())
    assert outcome.identity.skill_versions == {}


@pytest.mark.parametrize("exit_code, expected", [(0, "success"), (7, "response_failed")])
def test_end_to_end_launch_and_collection(repository: Path, tmp_path: Path, exit_code: int, expected: str) -> None:
    capture = tmp_path / "capture.json"
    fixture = tmp_path / "fixture.jsonl"
    fixture.write_text(_stream([_init(), _assistant('{"ok": true}'), _result()]))
    config = Config(
        agents={
            "a": Agent(
                runtime="claude-code",
                command=[
                    sys.executable,
                    str(Path(__file__).with_name("fake_cli.py")),
                    "--fake-capture",
                    str(capture),
                    "--fake-stdout",
                    str(fixture),
                    "--fake-exit",
                    str(exit_code),
                ],
                model="requested-model",
            )
        },
        roles={"inspect": Role(writes=False, deadline_seconds=60.0, result_shape="json")},
        workflows={"audit": Workflow(assignments={"inspect": Assignment(agents=["a"])})},
    )
    batch = run_workflow(config, "audit", "PROMPT", repository, output_dir=tmp_path / "run")
    assert batch.state == ("success" if exit_code == 0 else "failed")
    attempt = batch.results[0].attempts[0]
    assert attempt.state == expected and attempt.identity.model == "observed-model"
    assert attempt.exit_code == exit_code and attempt.stop_confirmed
    assert attempt.identity.cli_version == "fixture-version"
    recorded = json.loads(capture.read_text())
    assert "PROMPT" in recorded["stdin"]
    assert all("PROMPT" not in arg for arg in recorded["argv"])
    assert recorded["argv"][-1] == "--dangerously-skip-permissions"
    # Core retains parsed evidence on a failed exit; attempt.state is authoritative.
    assert attempt.payload == {"ok": True}


def test_prepare_resolves_role_skills_against_work_dir(context: AdapterContext) -> None:
    skill = context.work_dir / "custom-skills" / "inspect" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("Inspect carefully.\n")
    context.role.skills = ["inspect", "native-only"]
    context.agent.skill_sources = ["custom-skills"]
    spec = ADAPTER.prepare(context)
    prompt = spec.stdin.decode()
    assert "inspect" in prompt and "native-only" in prompt
    assert str(skill) in prompt
    assert all(context.request.prompt not in arg for arg in spec.argv)
    # Configuring a skill is not evidence that its contents were read.
    outcome = _collect(context, _result())
    assert outcome.identity.skill_versions == {}


def test_missing_identity_is_not_filled_from_agent_settings(context: AdapterContext) -> None:
    context.agent.provider = "requested-provider"
    context.agent.effort = "requested-effort"
    identity = _collect(context, _result()).identity
    assert identity.model is None and identity.provider is None and identity.effort is None
    assert identity.session_id is None and identity.cli_version is None


@pytest.mark.parametrize("diagnostic, expected", [
    ("401 Unauthorized: invalid api key", "awaiting_authentication"),
    ("Workspace trust required; requires approval", "awaiting_approval"),
])
def test_stderr_failure_dominates_plausible_result(context: AdapterContext, diagnostic: str, expected: str) -> None:
    outcome = _collect(context, _result(), stderr=diagnostic)
    assert outcome.receipt is not None and outcome.receipt.status == expected
    assert outcome.receipt.payload is None


@pytest.mark.parametrize("diagnostic, expected", [
    ("Not logged in", "awaiting_authentication"),
    ("Requires approval", "awaiting_approval"),
    ("Internal execution error", "response_failed"),
])
def test_error_event_dominates_plausible_result(context: AdapterContext, diagnostic: str, expected: str) -> None:
    outcome = _collect(context, {"type": "error", "error": {"message": diagnostic}}, _result())
    assert outcome.receipt is not None and outcome.receipt.status == expected


def test_successful_answer_discussing_authentication_is_valid(context: AdapterContext) -> None:
    outcome = _collect(context, _result('{"topic": "authentication requires approval"}'))
    assert outcome.receipt is not None and outcome.receipt.status == "success"


@pytest.mark.parametrize("subtype", ["interrupted", "aborted", "cancelled"])
def test_interrupted_result_is_not_success(context: AdapterContext, subtype: str) -> None:
    outcome = _collect(context, _result(subtype=subtype, is_error=True))
    assert outcome.receipt is not None and outcome.receipt.status == "interrupted"


def test_is_error_overrides_success_subtype(context: AdapterContext) -> None:
    outcome = _collect(context, _result(is_error=True))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_empty_text_result_fails(context: AdapterContext) -> None:
    context.role.result_shape = "text"
    outcome = _collect(context, _result(" \n"))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_malformed_result_does_not_complete_stream(context: AdapterContext) -> None:
    path = _write_stdout(context, _init(), _assistant("{}"))
    with path.open("a") as stream:
        stream.write('{"type":"result",')
    outcome = ADAPTER.collect(context, path, _write_stderr(context, ""))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_incomplete_assistant_prose_is_not_auth_diagnostic(context: AdapterContext) -> None:
    outcome = _collect(context, _assistant("The authentication documentation is available."))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_failed_skill_invocation_does_not_record_hash(context: AdapterContext) -> None:
    skill = context.work_dir / ".claude" / "skills" / "inspect" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("skill body")
    call = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "call-1", "name": "Skill", "input": {"skill": "inspect"}},
    ]}}
    result = {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "call-1", "is_error": True, "content": "failed"},
    ]}}
    outcome = _collect(context, call, result, _result())
    assert outcome.identity.skill_versions == {}


def test_explicit_assistant_error_is_auth_diagnostic(context: AdapterContext) -> None:
    event = _assistant("Not logged in; run claude login.")
    event["error"] = "authentication_failed"
    outcome = _collect(context, event)
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_authentication"


def test_later_unfinished_turn_invalidates_earlier_success(context: AdapterContext) -> None:
    outcome = _collect(context, _result(), _assistant("partial next turn"))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"
