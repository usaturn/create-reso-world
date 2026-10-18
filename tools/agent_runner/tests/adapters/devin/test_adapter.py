"""devin adapter: --prompt-file launch and ATIF export collection."""

import json
import sys
from pathlib import Path
from typing import cast

import pytest

from tools.agent_runner.adapters import AdapterContext
from tools.agent_runner.adapters.devin import ADAPTER
from tools.agent_runner.models import Agent, Assignment, Config, Role, Workflow
from tools.agent_runner.runner import run_workflow

pytest_plugins = ("tools.test_support.plugin",)
# Only fake agents are launched here; drop AGENT_RUNNER_DEPTH inside each test so a runner agent can run them
pytestmark = pytest.mark.usefixtures("outside_runner")


def _export(
    message: str | None = '{"ok": true}',
    tool_calls: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    steps: list[dict[str, object]] = [
        {"step_id": 1, "source": "system", "message": "system prompt"},
        {"step_id": 2, "source": "user", "message": "THE PROMPT"},
    ]
    if message is not None:
        steps.append(
            {
                "step_id": 3,
                "source": "agent",
                "message": message,
                "model_name": "requested-model",
                "tool_calls": tool_calls or [],
            }
        )
    return {
        "schema_version": "ATIF-v1.7",
        "session_id": "session-1",
        "agent": {
            "name": "devin",
            "version": "fixture-version",
            "model_name": "observed-model",
        },
        "steps": steps,
    }


def _write(context: AdapterContext, name: str, text: str) -> Path:
    path = context.receipt_path.parent / name
    path.write_text(text, encoding="utf-8")
    return path


def _collect(
    context: AdapterContext,
    stdout: str,
    *,
    export: dict[str, object] | None | object = "unset",
    stderr: str = "",
):
    out = _write(context, "stdout.log", stdout)
    err = _write(context, "stderr.log", stderr)
    if export != "unset":
        if export is None:
            pass  # devin left no export file
        else:
            _write(
                context,
                "export.json",
                json.dumps(export) if not isinstance(export, str) else export,
            )
    else:
        _write(context, "export.json", json.dumps(_export()))
    return ADAPTER.collect(context, out, err)


def test_prepare_writes_prompt_file_and_maps_flags(context: AdapterContext) -> None:
    spec = ADAPTER.prepare(context)
    prompt_path = spec.argv[spec.argv.index("--prompt-file") + 1]
    assert context.request.prompt in Path(prompt_path).read_text(encoding="utf-8")
    assert "JSON object" in Path(prompt_path).read_text(encoding="utf-8")
    assert "-p" in spec.argv
    assert Path(prompt_path).parent == context.receipt_path.parent
    assert spec.argv[spec.argv.index("--export") + 1].endswith("export.json")
    assert spec.argv[spec.argv.index("--model") + 1] == context.agent.model
    assert spec.argv[spec.argv.index("--permission-mode") + 1] == "dangerous"
    assert spec.argv[spec.argv.index("--respect-workspace-trust") + 1] == "false"
    assert spec.stdin == b""
    assert all(context.request.prompt != arg for arg in spec.argv)


def test_prepare_appends_agent_args(context: AdapterContext) -> None:
    context.agent.args = ["--sandbox"]
    spec = ADAPTER.prepare(context)
    assert spec.argv[-1] == "--sandbox"


def test_collect_success_extracts_identity(context: AdapterContext) -> None:
    outcome = _collect(context, '{"ok": true}\n')
    receipt = outcome.receipt
    assert receipt is not None and receipt.status == "success"
    assert receipt.payload == {"ok": True}
    assert outcome.identity.model == "observed-model"
    assert outcome.identity.cli_version == "fixture-version"
    assert outcome.identity.session_id == "session-1"
    assert outcome.identity.provider is None and outcome.identity.effort is None


def test_collect_success_text_shape(context: AdapterContext) -> None:
    context.role.result_shape = "text"
    outcome = _collect(context, "plain answer\n")
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.receipt.payload == "plain answer\n"


def test_blank_stdout_fails_even_with_export(context: AdapterContext) -> None:
    outcome = _collect(context, "")
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_missing_export_fails(context: AdapterContext) -> None:
    outcome = _collect(context, '{"ok": true}', export=None)
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"
    assert outcome.identity.model is None


def test_malformed_export_fails(context: AdapterContext) -> None:
    outcome = _collect(context, '{"ok": true}', export="not json {")
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_export_without_agent_message_fails(context: AdapterContext) -> None:
    outcome = _collect(context, '{"ok": true}', export=_export(message=None))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_auth_stderr_reports_awaiting_authentication(context: AdapterContext) -> None:
    outcome = _collect(context, "", export=None, stderr="Error: not logged in")
    assert (
        outcome.receipt is not None
        and outcome.receipt.status == "awaiting_authentication"
    )


def test_workspace_trust_stderr_reports_awaiting_approval(
    context: AdapterContext,
) -> None:
    outcome = _collect(
        context,
        "",
        export=None,
        stderr="workspace trust is required; pass --respect-workspace-trust",
    )
    assert outcome.receipt is not None and outcome.receipt.status == "awaiting_approval"


def test_non_object_stdout_fails_json_shape(context: AdapterContext) -> None:
    outcome = _collect(context, "plain text")
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_skill_tool_call_path_alone_does_not_prove_read(
    context: AdapterContext, tmp_path: Path
) -> None:
    skill_dir = tmp_path / "skills" / "review"
    skill_dir.mkdir(parents=True)
    skill = skill_dir / "SKILL.md"
    skill.write_text("---\nname: review\n---\nbody\n", encoding="utf-8")
    context.agent.skill_sources = [str(tmp_path / "skills")]
    calls: list[dict[str, object]] = [
        {
            "type": "function",
            "function": {"name": "read", "arguments": json.dumps({"path": str(skill)})},
        }
    ]
    export = _export(tool_calls=calls)
    cast(list[object], export["steps"]).append(
        {"source": "agent", "message": "final answer", "tool_calls": []}
    )
    outcome = _collect(context, '{"ok": true}', export=export)
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.identity.skill_versions == {}


def test_end_to_end_launch_and_collection(repository: Path, tmp_path: Path) -> None:
    capture = tmp_path / "capture.json"
    fixture = tmp_path / "export.json"
    fixture.write_text(json.dumps(_export()))
    out = tmp_path / "out.txt"
    out.write_text('{"ok": true}\n')
    config = Config(
        agents={
            "a": Agent(
                runtime="devin",
                command=[
                    sys.executable,
                    str(Path(__file__).with_name("fake_cli.py")),
                    "--fake-capture",
                    str(capture),
                    "--fake-export",
                    str(fixture),
                    "--fake-stdout",
                    str(out),
                ],
                model="requested-model",
            )
        },
        roles={
            "inspect": Role(writes=False, deadline_seconds=60.0, result_shape="json")
        },
        workflows={
            "audit": Workflow(assignments={"inspect": Assignment(agents=["a"])})
        },
    )
    batch = run_workflow(
        config, "audit", "PROMPT", repository, output_dir=tmp_path / "run"
    )
    assert batch.state == "success"
    attempt = batch.results[0].attempts[0]
    assert attempt.state == "success" and attempt.identity.model == "observed-model"
    assert attempt.identity.session_id == "session-1"
    recorded = json.loads(capture.read_text())
    assert "PROMPT" in recorded["prompt"]
    assert all("PROMPT" not in arg for arg in recorded["argv"])
    assert "--prompt-file" in recorded["argv"]
    assert attempt.payload == {"ok": True}


# The runner keeps <attempt>/export.json as a managed retained artifact and
# must redact inherited secret values from it before collection sees it.
def _devin_config(agent: Agent) -> Config:
    return Config(
        agents={"a": agent},
        roles={
            "inspect": Role(writes=False, deadline_seconds=60.0, result_shape="json")
        },
        workflows={
            "audit": Workflow(assignments={"inspect": Assignment(agents=["a"])})
        },
    )


def _runtime_agent(tmp_path: Path, *extra_args: str) -> Agent:
    return Agent(
        runtime="devin",
        command=[
            sys.executable,
            str(Path(__file__).with_name("fake_cli.py")),
            *extra_args,
        ],
        model="requested-model",
    )


def test_retained_export_with_secrets_is_redacted_before_collection(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "synthetic-cli-token-98765"
    monkeypatch.setenv("SERVICE_TOKEN", secret)
    fixture = tmp_path / "export.json"
    export = _export(message="answer " + secret)
    extra: dict[str, object] = {
        "step_id": 4,
        "source": "agent",
        "message": "still " + secret,
        "tool_calls": [
            {
                "type": "function",
                "function": {
                    "name": "run",
                    "arguments": json.dumps({"shell": "token=" + secret}),
                },
            }
        ],
    }
    cast(list[object], export["steps"]).append(extra)
    cast(list[object], export["steps"]).append(
        {"source": "agent", "message": "final answer " + secret, "tool_calls": []}
    )
    fixture.write_text(json.dumps(export), encoding="utf-8")
    out = tmp_path / "out.txt"
    out.write_text('{"ok": true}\n')
    config = _devin_config(
        _runtime_agent(
            tmp_path,
            "--fake-capture",
            str(tmp_path / "capture.json"),
            "--fake-export",
            str(fixture),
            "--fake-stdout",
            str(out),
        )
    )
    config.agents["a"].env = ["SERVICE_TOKEN"]
    batch = run_workflow(
        config, "audit", "PROMPT", repository, output_dir=tmp_path / "run"
    )
    assert batch.state == "success"
    attempt = batch.results[0].attempts[0]
    assert attempt.state == "success"
    assert attempt.payload == {"ok": True}
    # Observed identity survives redaction of the transcript itself.
    assert attempt.identity.model == "observed-model"
    assert attempt.identity.session_id == "session-1"
    assert attempt.request_path is not None
    retained = attempt.request_path.parent / "export.json"
    text = retained.read_text(encoding="utf-8")
    assert secret not in text
    assert "[REDACTED]" in text


def test_missing_retained_export_keeps_response_failed(
    repository: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out.txt"
    out.write_text('{"ok": true}\n')
    config = _devin_config(
        _runtime_agent(
            tmp_path,
            "--fake-capture",
            str(tmp_path / "capture.json"),
            "--fake-stdout",
            str(out),
        )
    )
    batch = run_workflow(
        config, "audit", "PROMPT", repository, output_dir=tmp_path / "run"
    )
    result = batch.results[0]
    assert result.state == "response_failed"
    attempt = result.attempts[0]
    assert attempt.stop_confirmed and attempt.sensitive_paths == []
    assert (
        not (attempt.request_path or tmp_path).parent.joinpath("export.json").exists()
    )
    assert attempt.identity.model is None


def test_secret_free_multiline_export_is_retained_unchanged(
    repository: Path, tmp_path: Path
) -> None:
    export = json.dumps(
        {
            "schema_version": "ATIF-v1.7",
            "session_id": "session-1",
            "agent": {
                "name": "devin",
                "version": "fixture-version",
                "model_name": "observed-model",
            },
            "steps": [
                {"step_id": 1, "source": "user", "message": "日本語\n複数行の依頼"},
                {
                    "step_id": 2,
                    "source": "agent",
                    "message": "回答\n日本語",
                    "tool_calls": [],
                },
            ],
        },
        ensure_ascii=False,
    )
    fixture = tmp_path / "export.json"
    fixture.write_text(export, encoding="utf-8")
    out = tmp_path / "out.txt"
    out.write_text('{"ok": true}\n')
    config = _devin_config(
        _runtime_agent(
            tmp_path, "--fake-export", str(fixture), "--fake-stdout", str(out)
        )
    )
    batch = run_workflow(
        config, "audit", "PROMPT", repository, output_dir=tmp_path / "run"
    )
    attempt = batch.results[0].attempts[0]
    assert attempt.state == "success"
    assert attempt.payload == {"ok": True}
    assert attempt.identity.model == "observed-model"
    assert attempt.request_path is not None
    retained = attempt.request_path.parent / "export.json"
    assert retained.read_text(encoding="utf-8") == export
    assert "[REDACTED]" not in retained.read_text(encoding="utf-8")


def test_prepare_includes_requested_skills_and_configured_source(
    context: AdapterContext,
) -> None:
    skill = context.work_dir / "source" / "alpha" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("skill body")
    context.role.skills = ["alpha", "native-only"]
    context.agent.skill_sources = ["source"]
    spec = ADAPTER.prepare(context)
    prompt = Path(spec.argv[spec.argv.index("--prompt-file") + 1]).read_text()
    assert context.request.prompt in prompt
    assert "alpha" in prompt and "native-only" in prompt and str(skill) in prompt
    assert all(
        context.request.prompt not in arg and str(skill) not in arg for arg in spec.argv
    )


def test_identity_never_copies_requested_configuration(context: AdapterContext) -> None:
    context.agent.provider = "requested-provider"
    context.agent.effort = "requested-effort"
    export = _export()
    export.pop("agent")
    export.pop("session_id")
    outcome = _collect(context, '{"ok":true}', export=export)
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.identity.model is None and outcome.identity.provider is None
    assert outcome.identity.effort is None and outcome.identity.cli_version is None
    assert outcome.identity.session_id is None and outcome.identity.skill_versions == {}


@pytest.mark.parametrize(
    "diagnostic,state",
    [
        ("Not logged in", "awaiting_authentication"),
        ("Approval required", "awaiting_approval"),
        ("waiting for approval", "awaiting_approval"),
    ],
)
def test_diagnostics_override_plausible_success(
    context: AdapterContext, diagnostic: str, state: str
) -> None:
    outcome = _collect(context, '{"ok":true}', stderr=diagnostic)
    assert outcome.receipt is not None and outcome.receipt.status == state
    assert outcome.receipt.payload is None


@pytest.mark.parametrize("diagnostic", ["Error: not logged in", "Approval required"])
def test_stdout_diagnostic_without_answer_is_not_success(
    context: AdapterContext, diagnostic: str
) -> None:
    context.role.result_shape = "text"
    outcome = _collect(context, diagnostic, export=None)
    assert outcome.receipt is not None
    assert outcome.receipt.status in {"awaiting_authentication", "awaiting_approval"}


def test_success_payload_can_discuss_authentication(context: AdapterContext) -> None:
    outcome = _collect(
        context,
        '{"explanation":"Authentication and approval required are diagnostic examples"}',
    )
    assert outcome.receipt is not None and outcome.receipt.status == "success"


@pytest.mark.parametrize("tail", ['{"event":', '[{"event":', "{broken json}"])
def test_truncated_later_stdout_cannot_reuse_completion(
    context: AdapterContext, tail: str
) -> None:
    outcome = _collect(context, '{"ok":true}\n' + tail)
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_plain_progress_after_json_does_not_invalidate_completion(
    context: AdapterContext,
) -> None:
    outcome = _collect(context, '{"ok":true}\nprogress: export saved\n')
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.receipt.payload == {"ok": True}


def test_truncated_later_export_cannot_reuse_completion(
    context: AdapterContext,
) -> None:
    outcome = _collect(
        context, '{"ok":true}', export=json.dumps(_export()) + '\n{"step_id":'
    )
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


@pytest.mark.parametrize("message", ["", " ", None, 17])
def test_latest_empty_agent_message_cannot_reuse_earlier_answer(
    context: AdapterContext, message: object
) -> None:
    export = _export()
    cast(list[object], export["steps"]).append({"source": "agent", "message": message})
    outcome = _collect(context, '{"ok":true}', export=export)
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


@pytest.mark.parametrize(
    "tail",
    [
        {"source": "user", "message": "next unfinished request"},
        {
            "source": "agent",
            "message": "calling tool",
            "tool_calls": [{"function": {"name": "read"}}],
        },
        {"source": "error", "message": "Not logged in"},
    ],
)
def test_incomplete_or_failed_export_does_not_reuse_prior_answer(
    context: AdapterContext, tail: dict[str, object]
) -> None:
    export = _export()
    cast(list[object], export["steps"]).append(tail)
    outcome = _collect(context, '{"ok":true}', export=export)
    assert outcome.receipt is not None and outcome.receipt.status != "success"


@pytest.mark.parametrize(
    "stdout", ["[]", '[{"nested":true}]', "{}", '{"outer":{"nested":true},']
)
def test_invalid_final_json_does_not_return_nested_fragment(
    context: AdapterContext, stdout: str
) -> None:
    outcome = _collect(context, stdout)
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_nonzero_cli_exit_cannot_succeed_with_valid_artifacts(
    repository: Path, tmp_path: Path
) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps(_export()))
    out = tmp_path / "out.txt"
    out.write_text('{"ok":true}')
    config = _devin_config(
        _runtime_agent(
            tmp_path,
            "--fake-export",
            str(fixture),
            "--fake-stdout",
            str(out),
            "--fake-exit",
            "7",
        )
    )
    batch = run_workflow(
        config, "audit", "PROMPT", repository, output_dir=tmp_path / "run"
    )
    attempt = batch.results[0].attempts[0]
    assert attempt.state == "response_failed"
    assert attempt.stop_confirmed


@pytest.mark.parametrize("prefix", ['{"ok":true}', '```json\n{"ok":true}\n```'])
@pytest.mark.parametrize(
    "suffix,state",
    [
        ("\nError: not logged in", "awaiting_authentication"),
        ("\nApproval required", "awaiting_approval"),
        ('\n{"event":', "response_failed"),
    ],
)
def test_late_diagnostic_or_truncation_after_answer_is_failure(
    context: AdapterContext, prefix: str, suffix: str, state: str
) -> None:
    outcome = _collect(context, prefix + suffix)
    assert outcome.receipt is not None and outcome.receipt.status == state


@pytest.mark.parametrize(
    "answer",
    ['```json\n{"ok":true}\n```', '```json\n{"ok":true}\n```\nprogress: saved'],
)
def test_fenced_json_answer(context: AdapterContext, answer: str) -> None:
    outcome = _collect(context, answer)
    assert outcome.receipt is not None and outcome.receipt.payload == {"ok": True}


@pytest.mark.parametrize(
    "diagnostic,state",
    [
        ("Error: Not logged in", "awaiting_authentication"),
        ("Approval required", "awaiting_approval"),
    ],
)
def test_text_diagnostic_with_valid_export_is_not_success(
    context: AdapterContext, diagnostic: str, state: str
) -> None:
    context.role.result_shape = "text"
    outcome = _collect(context, diagnostic)
    assert outcome.receipt is not None and outcome.receipt.status == state


@pytest.mark.parametrize(
    "failure",
    [
        {"source": "agent", "message": "answer", "error": "operation failed"},
        {"source": "agent", "message": "answer", "is_error": True},
    ],
)
def test_export_error_fields_override_answer(
    context: AdapterContext, failure: dict[str, object]
) -> None:
    export = _export()
    cast(list[object], export["steps"]).append(failure)
    outcome = _collect(context, '{"ok":true}', export=export)
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_prepare_does_not_invent_provider_or_effort_flags(
    context: AdapterContext,
) -> None:
    context.agent.provider = "requested-provider"
    context.agent.effort = "requested-effort"
    spec = ADAPTER.prepare(context)
    assert spec.argv[spec.argv.index("--model") + 1] == context.agent.model
    assert (
        context.agent.provider not in spec.argv
        and context.agent.effort not in spec.argv
    )
