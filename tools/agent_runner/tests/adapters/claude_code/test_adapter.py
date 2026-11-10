"""claude-code adapter: launch spec shape and stream-json collection."""

import json
from collections.abc import Iterable
from pathlib import Path

import pytest

from tools.agent_runner.adapters import AdapterContext
from tools.agent_runner.adapters.claude_code import ADAPTER

# Only fake agents are launched here; drop AGENT_RUNNER_DEPTH inside each test so a runner agent can run them


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


def test_permission_denials_report_awaiting_approval(context: AdapterContext) -> None:
    secret = "fixture-secret-tool-input"
    denials: list[dict[str, object]] = [{"tool": "Bash", "tool_input": {"command": secret}}]
    outcome = _collect(context, _init(), _result(denials=denials))
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_approval"
    assert outcome.receipt.payload == {
        "approval": {
            "source": "permission_denials",
            "terminal_subtype": "success",
            "is_error": False,
            "permission_denials": True,
            "denial_count": 1,
            "diagnostic_sources": [],
        }
    }
    assert secret not in json.dumps(outcome.receipt.payload)


@pytest.mark.parametrize(
    ("events", "stderr", "expected"),
    [
        pytest.param((
            {"type": "error", "error": {"message": "requires approval"}},
            _result(),
        ), "", {
            "source": "diagnostic_text",
            "terminal_subtype": "success",
            "is_error": False,
            "permission_denials": False,
            "denial_count": 0,
            "diagnostic_sources": ["error_event"],
        }, id="error-event"),
        pytest.param((_result("requires approval", subtype="error", is_error=True),), "", {
            "source": "diagnostic_text",
            "terminal_subtype": "error",
            "is_error": True,
            "permission_denials": False,
            "denial_count": 0,
            "diagnostic_sources": ["terminal_result"],
        }, id="terminal-result"),
    ],
)
def test_diagnostic_text_approval_records_safe_source(
    context: AdapterContext,
    events: tuple[dict[str, object], ...],
    stderr: str,
    expected: dict[str, object],
) -> None:
    outcome = _collect(context, *events, stderr=stderr)
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_approval"
    assert outcome.receipt.payload == {"approval": expected}


def test_arbitrary_denial_metadata_is_normalized_and_not_copied(context: AdapterContext) -> None:
    secret = "fixture-secret-subtype"
    result = _result()
    result["subtype"] = secret
    result["is_error"] = secret
    result["permission_denials"] = secret
    outcome = _collect(context, _init(), result)
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_approval"
    assert outcome.receipt.payload == {
        "approval": {
            "source": "permission_denials",
            "terminal_subtype": "other",
            "is_error": None,
            "permission_denials": True,
            "denial_count": None,
            "diagnostic_sources": [],
        }
    }
    assert secret not in json.dumps(outcome.receipt.payload)


def test_approval_words_in_success_output_are_not_failure_evidence(context: AdapterContext) -> None:
    text = '{"status": "success", "approval": {"source": "forged"},\n"note": "承認待ちで requires approval と引用された"}'
    tool_result = {
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "content": "approval required in a quoted log"}],
        },
    }
    outcome = _collect(
        context,
        _init(),
        _assistant("承認待ちです。requires approval という引用です。\n二行目"),
        tool_result,
        _result(text),
    )
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.receipt.payload == {
        "status": "success",
        "approval": {"source": "forged"},
        "note": "承認待ちで requires approval と引用された",
    }


@pytest.mark.parametrize("is_error", [False])
def test_error_subtype_reports_response_failed(context: AdapterContext, is_error: bool) -> None:
    outcome = _collect(context, _init(), _result("boom", subtype="error_during_execution", is_error=is_error))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_auth_error_text_reports_awaiting_authentication(context: AdapterContext) -> None:
    outcome = _collect(
        context,
        _result("Error: not logged in. Run claude login.", subtype="error", is_error=True),
    )
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_authentication"


def test_missing_result_reports_response_failed(context: AdapterContext) -> None:
    outcome = _collect(context, _init(), _assistant("partial"))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


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
    if expected == "awaiting_approval":
        assert outcome.receipt.payload == {
            "approval": {
                "source": "diagnostic_text",
                "terminal_subtype": "success",
                "is_error": False,
                "permission_denials": False,
                "denial_count": 0,
                "diagnostic_sources": ["stderr"],
            }
        }
    else:
        assert outcome.receipt.payload is None


@pytest.mark.parametrize("diagnostic, expected", [
    ("Internal execution error", "response_failed"),
])
def test_error_event_dominates_plausible_result(context: AdapterContext, diagnostic: str, expected: str) -> None:
    outcome = _collect(context, {"type": "error", "error": {"message": diagnostic}}, _result())
    assert outcome.receipt is not None and outcome.receipt.status == expected


@pytest.mark.parametrize("subtype", ["interrupted", "aborted", "cancelled"])
def test_interrupted_result_is_not_success(context: AdapterContext, subtype: str) -> None:
    outcome = _collect(context, _result(subtype=subtype, is_error=True))
    assert outcome.receipt is not None and outcome.receipt.status == "interrupted"


def test_is_error_overrides_success_subtype(context: AdapterContext) -> None:
    outcome = _collect(context, _result(is_error=True))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_incomplete_assistant_prose_is_not_auth_diagnostic(context: AdapterContext) -> None:
    outcome = _collect(context, _assistant("The authentication documentation is available."))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_explicit_assistant_error_is_auth_diagnostic(context: AdapterContext) -> None:
    event = _assistant("Not logged in; run claude login.")
    event["error"] = "authentication_failed"
    outcome = _collect(context, event)
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_authentication"


def test_later_unfinished_turn_invalidates_earlier_success(context: AdapterContext) -> None:
    outcome = _collect(context, _result(), _assistant("partial next turn"))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


@pytest.mark.parametrize("tail", ['  {'])
def test_truncated_event_after_success_invalidates_completion(context: AdapterContext, tail: str) -> None:
    path = _write_stdout(context, _result())
    with path.open("a") as stream:
        stream.write(tail)
    outcome = ADAPTER.collect(context, path, _write_stderr(context, ""))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"
    assert outcome.receipt.payload is None
