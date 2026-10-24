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


# The shape devin 3000.11.92 produced for real reviews (#185, #186): agent
# steps call tools before the final answer, and stdout concatenates every
# agent message without separators, ending with the final one.
_PROGRESS = (
    "Python 3.14 allows unparenthesized `except A, B` — not a bug. Now checking the tests.",
    "Running the new tests.",
)
_FENCED = '```json\n{\n  "status": "success",\n  "review_file": "SWE-2-Max.md"\n}\n```'
_FENCED_PAYLOAD = {"status": "success", "review_file": "SWE-2-Max.md"}


def _tool_run_export(
    final: str = _FENCED, *, final_tool_calls: list[dict[str, object]] | None = None
) -> dict[str, object]:
    export = _export(message=None)
    steps = cast(list[object], export["steps"])
    for index, text in enumerate(_PROGRESS):
        steps.append(
            {
                "source": "agent",
                "message": text,
                "tool_calls": [
                    {
                        "tool_call_id": f"call-{index}",
                        "function_name": "read",
                        "arguments": {},
                    }
                ],
                "observation": {"results": []},
            }
        )
    steps.append(
        {"source": "agent", "message": final, "tool_calls": final_tool_calls or []}
    )
    return export


def _tool_run_stdout(final: str = _FENCED) -> str:
    return "".join(_PROGRESS) + final + "\n"


# #239: devin -p prints the model's own messages to stdout, so a review can
# quote a CLI-looking line in a code block or after its JSON answer.
_QUOTE = "The adapter logs this on a bad key:\n```\nError: invalid api key\n```\n"
_QUOTED_FINAL = _FENCED + "\nError: invalid api key above is quoted from the diff."


@pytest.mark.parametrize(
    "final_tool_calls,state,payload",
    [
        (None, "success", _FENCED_PAYLOAD),
        (
            [{"tool_call_id": "call-9", "function_name": "exec", "arguments": {}}],
            "response_failed",
            None,
        ),
    ],
    ids=["answer", "no-answer"],
)
def test_quoted_diagnostics_in_model_messages_are_answer_data(
    context: AdapterContext,
    final_tool_calls: list[dict[str, object]] | None,
    state: str,
    payload: dict[str, object] | None,
) -> None:
    export = _tool_run_export(_QUOTED_FINAL, final_tool_calls=final_tool_calls)
    # The quoting message is an earlier agent step; stdout concatenates every
    # agent message and ends with the final one.
    read = [{"tool_call_id": "call-q", "function_name": "read", "arguments": {}}]
    cast(list[object], export["steps"]).insert(
        -1, {"source": "agent", "message": _QUOTE, "tool_calls": read}
    )
    stdout = "".join(_PROGRESS) + _QUOTE + _QUOTED_FINAL + "\n"
    outcome = _collect(context, stdout, export=export)
    assert outcome.receipt is not None and outcome.receipt.status == state
    assert outcome.receipt.payload == payload


def test_export_error_step_authentication_overrides_answer(
    context: AdapterContext,
) -> None:
    # An error step reports devin's own failure even though stdout still ends
    # with a plausible final answer.
    export = _tool_run_export()
    cast(list[object], export["steps"]).insert(
        -1, {"source": "error", "message": "Error: invalid api key"}
    )
    outcome = _collect(context, _tool_run_stdout(), export=export)
    assert outcome.receipt is not None
    assert outcome.receipt.status == "awaiting_authentication"
    assert outcome.receipt.payload is None


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
    outcome = _collect(
        context, "plain answer\n", export=_export(message="plain answer")
    )
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.receipt.payload == "plain answer"


def test_blank_stdout_fails_even_with_export(context: AdapterContext) -> None:
    outcome = _collect(context, "")
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_missing_export_fails(context: AdapterContext) -> None:
    outcome = _collect(context, '{"ok": true}', export=None)
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"
    assert outcome.identity.model is None


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
        {"source": "agent", "message": '{"ok": true}', "tool_calls": []}
    )
    outcome = _collect(context, '{"ok": true}', export=export)
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.identity.skill_versions == {}


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
    export = _export(message=json.dumps({"answer": secret}))
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
        {
            "source": "agent",
            "message": json.dumps({"final_answer": secret}),
            "tool_calls": [],
        }
    )
    fixture.write_text(json.dumps(export), encoding="utf-8")
    out = tmp_path / "out.txt"
    # devin prints the final answer, so stdout repeats the secret as well.
    out.write_text(json.dumps({"final_answer": secret}) + "\n")
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
    assert attempt.payload == {"final_answer": "[REDACTED]"}
    # Observed identity survives redaction of the transcript itself.
    assert attempt.identity.model == "observed-model"
    assert attempt.identity.session_id == "session-1"
    assert attempt.request_path is not None
    retained = attempt.request_path.parent / "export.json"
    text = retained.read_text(encoding="utf-8")
    assert secret not in text
    assert "[REDACTED]" in text


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
    outcome = _collect(context, '{"ok": true}', export=export)
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
    outcome = _collect(context, '{"ok": true}', stderr=diagnostic)
    assert outcome.receipt is not None and outcome.receipt.status == state
    assert outcome.receipt.payload is None


@pytest.mark.parametrize("tail", ['{"event":', '[{"event":'])
def test_truncated_later_stdout_cannot_reuse_completion(
    context: AdapterContext, tail: str
) -> None:
    outcome = _collect(context, '{"ok": true}\n' + tail)
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


def test_plain_progress_after_json_does_not_invalidate_completion(
    context: AdapterContext,
) -> None:
    outcome = _collect(context, '{"ok": true}\nprogress: export saved\n')
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.receipt.payload == {"ok": True}


def test_truncated_later_export_cannot_reuse_completion(
    context: AdapterContext,
) -> None:
    outcome = _collect(
        context, '{"ok": true}', export=json.dumps(_export()) + '\n{"step_id":'
    )
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


@pytest.mark.parametrize("message", [""])
def test_latest_empty_agent_message_cannot_reuse_earlier_answer(
    context: AdapterContext, message: object
) -> None:
    export = _export()
    cast(list[object], export["steps"]).append({"source": "agent", "message": message})
    outcome = _collect(context, '{"ok": true}', export=export)
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


@pytest.mark.parametrize(
    "tail",
    [
        {"source": "user", "message": "next unfinished request"},
    ],
)
def test_incomplete_or_failed_export_does_not_reuse_prior_answer(
    context: AdapterContext, tail: dict[str, object]
) -> None:
    export = _export()
    cast(list[object], export["steps"]).append(tail)
    outcome = _collect(context, '{"ok": true}', export=export)
    assert outcome.receipt is not None and outcome.receipt.status != "success"


@pytest.mark.parametrize(
    "stdout", ['[{"nested":true}]', '{"outer":{"nested":true},']
)
def test_invalid_final_json_does_not_return_nested_fragment(
    context: AdapterContext, stdout: str
) -> None:
    outcome = _collect(context, stdout, export=_export(message=stdout))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


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
    # Before the final answer, so stdout still ends with it and only the
    # step's error fields can fail the run (#259).
    cast(list[object], export["steps"]).insert(-1, failure)
    outcome = _collect(context, '{"ok": true}', export=export)
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"


@pytest.mark.parametrize(
    "final,payload", [(_FENCED, _FENCED_PAYLOAD), ]
)
def test_tool_run_stdout_ending_with_final_answer_succeeds(
    context: AdapterContext, final: str, payload: dict[str, object]
) -> None:
    outcome = _collect(context, _tool_run_stdout(final), export=_tool_run_export(final))
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert outcome.receipt.payload == payload


@pytest.mark.parametrize(
    "final,stdout",
    [
        # stdout stops in the middle of the answer
        # another JSON-like event follows the answer
        # the answer's line goes on, so stdout's last JSON is not the answer
        ('{"ok": true}', "".join(_PROGRESS) + '{"ok": true}, "x": 1}\n'),
        # the answer never reached stdout
    ],
)
def test_tool_run_stdout_not_ending_with_final_answer_fails(
    context: AdapterContext, final: str, stdout: str
) -> None:
    outcome = _collect(context, stdout, export=_tool_run_export(final))
    assert outcome.receipt is not None and outcome.receipt.status == "response_failed"
    assert outcome.receipt.payload is None


def test_tool_run_final_step_calling_tool_fails(context: AdapterContext) -> None:
    calls: list[dict[str, object]] = [
        {"tool_call_id": "call-9", "function_name": "exec", "arguments": {}}
    ]
    outcome = _collect(
        context, _tool_run_stdout(), export=_tool_run_export(final_tool_calls=calls)
    )
    assert outcome.receipt is not None and outcome.receipt.status != "success"
