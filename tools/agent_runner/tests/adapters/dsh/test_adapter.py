"""DSH launch isolation and strict headless event handling; no live API calls."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from tools.agent_runner import environ
from tools.agent_runner.adapters import (
    AdapterContext,
    AdapterOutcome,
    LaunchSpec,
    load_adapter,
    runtime_supported,
)
from tools.agent_runner.models import (
    Agent,
    Payload,
    ReceiptStatus,
    Request,
    ResultShape,
    Role,
)
from tools.test_support.dsh import write_session


@pytest.fixture
def context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AdapterContext:
    monkeypatch.setattr(
        environ,
        "_literal",
        {
            "COMMANDCODE_API_KEY": "credential-not-for-files",
            "PI_PROVIDER": "parent-provider",
            "PI_MODEL": "parent-model",
            "DSH_HOME": str(tmp_path / "shared-dsh"),
        },
    )
    work = tmp_path / "worktree"
    work.mkdir()
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    return AdapterContext(
        Request(
            run_id="run",
            request_id="request",
            agent_id="dsh-a",
            role="inspect",
            work_dir=work,
            prompt="一行目\n二行目 ☃\n",
            deadline_seconds=60.0,
            result_shape="json",
        ),
        Agent.model_validate(
            {
                "runtime": "dsh",
                "command": ["dsh"],
                "provider": "commandcode",
                "model": "a-model",
                "effort": "high",
                "env": ["COMMANDCODE_API_KEY"],
            }
        ),
        Role(writes=False, deadline_seconds=60.0, result_shape="json"),
        work,
        attempt / "receipt.json",
    )


def test_adapter_cache_paths_are_writable_with_its_scoped_runner(context: AdapterContext) -> None:
    import subprocess
    import sys

    spec = load_adapter("dsh").prepare(context)
    command = _patch(spec)["sandbox"]["config"]["runnerCommand"]
    work = str(context.work_dir.resolve())
    profile = [
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--unshare-pid",
        "--proc",
        "/proc",
        "--die-with-parent",
        "--tmpfs",
        "/tmp",
        "--bind",
        work,
        work,
        "--",
    ]
    cache, venv = Path(spec.env["UV_CACHE_DIR"]), Path(spec.env["UV_PROJECT_ENVIRONMENT"])
    assert cache.is_relative_to(spec.env["HOME"]) and venv.is_relative_to(spec.env["HOME"])
    state = Path(spec.env["DSH_HOME"]) / "visible"
    state.write_text("observed")
    program = "from pathlib import Path; " + "; ".join(f"Path({str(path)!r}).mkdir()" for path in (cache, venv))
    program += f"; assert Path({str(state)!r}).read_text() == 'observed'"
    # The profile hides /tmp; a checkout's venv there is not visible, the interpreter it links to is.
    python = str(Path(sys.executable).resolve())
    result = subprocess.run([*command, *profile, python, "-c", program], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert cache.is_dir() and venv.is_dir()


def test_runtime_is_registered() -> None:
    assert runtime_supported("dsh")


def test_arbitrary_write_grants_are_rejected_before_launch_state(context: AdapterContext) -> None:
    from dataclasses import replace

    context = replace(context, sandbox_write_paths=(context.work_dir,))
    with pytest.raises(ValueError, match="grant"):
        load_adapter("dsh").prepare(context)
    assert not (context.receipt_path.parent / "dsh").exists()


def test_dsh_disk_receipt_cannot_override_failed_jsonl(context: AdapterContext) -> None:
    from tools.agent_runner.models import Receipt
    from tools.agent_runner.runner import _collect as collect_attempt

    _collect(context, ["invalid jsonl\n"])
    receipt = Receipt(
        run_id=context.request.run_id, request_id=context.request.request_id,
        agent_id=context.request.agent_id, role=context.request.role,
        status="success", payload={"forged": True},
    )
    context.receipt_path.write_text(receipt.model_dump_json())
    state, _, payload = collect_attempt(
        load_adapter("dsh"), context, context.receipt_path.parent / "stdout.log",
        context.receipt_path.parent / "stderr.log", None,
    )
    assert state == "invalid_result" and payload is None


def test_tmp_launch_script_and_shared_environment_are_visible_readonly(
    context: AdapterContext, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os
    import subprocess
    import sys

    shared = context.work_dir.parent / "shared-venv"
    shared.mkdir()
    marker = shared / "dependency"
    marker.write_text("shared dependency")
    script = context.work_dir.parent / "cli.py"
    script.write_text(
        "import json; from pathlib import Path\n"
        f"marker = Path({str(marker)!r})\n"
        "assert marker.read_text() == 'shared dependency'\n"
        "try:\n marker.write_text('changed')\nexcept OSError:\n print(json.dumps({'readonly': True}))\n"
    )
    # sys.prefix is replaced below, so a /tmp checkout's venv is not restored; the interpreter it links to is.
    context.agent.command = [str(Path(sys.executable).resolve()), str(script)]
    with monkeypatch.context() as patch:
        patch.setattr(sys, "prefix", str(shared))
        spec = load_adapter("dsh").prepare(context)
    result = subprocess.run(
        spec.argv, input=spec.stdin, env={"PATH": os.defpath, **spec.env},
        cwd=context.work_dir, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"readonly": True}
    assert marker.read_text() == "shared dependency"


@pytest.fixture
def parent_review(context: AdapterContext) -> dict[str, Any]:
    import hashlib
    import shutil
    import subprocess

    root = context.work_dir.parent / "parent"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    (root / ".gitignore").write_text("/reviews/\n")
    directory = context.work_dir.parent / "parent-input"
    directory.mkdir()
    bundle = directory / "objects.bundle"
    bundle.write_text("fixture bundle")
    document = {
        "schema": "pr-review-parent/v1", "target": {"parent_root": str(root)},
        "base": "a" * 40, "review_commit": None, "comments": [], "requirements": {},
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
    }
    snapshot = directory / "snapshot.json"
    snapshot.write_text(json.dumps(document))
    neighbor = context.work_dir.parent / "host-neighbor"
    neighbor.write_text("host original")
    # The profile hides /tmp and restores only the checkout's tools/, so a /tmp checkout's
    # .agents/ is not visible; the attempt is restored read-only in both sandboxes.
    helper = context.receipt_path.parent / "review_target.py"
    shutil.copyfile(Path(__file__).resolve().parents[5] / ".agents/scripts/review_target.py", helper)
    parameters = {
        "parent_pr_data": {"path": str(snapshot), "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest()},
        "probe_neighbor": str(neighbor),
        "probe_helper": str(helper),
    }
    context.request.prompt = "Review this PR.\n```json\n" + json.dumps(parameters) + "\n```\n"
    return {"snapshot": snapshot, "bundle": bundle, "root": root, "neighbor": neighbor, "parameters": parameters}


def test_tmp_parent_review_inputs_are_readonly_in_native_and_inner_bash(
    context: AdapterContext, parent_review: dict[str, Any],
) -> None:
    import os
    import subprocess
    import sys

    context.agent.command = [sys.executable, str(Path(__file__).with_name("fake_cli.py")), "parent-input"]
    spec = load_adapter("dsh").prepare(context)
    result = subprocess.run(
        spec.argv, input=spec.stdin, env={"PATH": os.defpath, "AGENT_RUNNER_DEPTH": "1", **spec.env}, cwd=context.work_dir,
        capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    capture = json.loads((Path(spec.env["DSH_HOME"]) / "capture.json").read_text())
    assert capture["parent_visible"]
    assert capture["bundle"] == "fixture bundle"
    assert all(capture["parent_writes_denied"])
    assert capture["helper_exit"] == 0, capture["helper_error"]
    assert parent_review["neighbor"].read_text() == "host original"


@pytest.mark.parametrize("prompt", [
    "Explain parent_pr_data.", '```json\n{"unrelated": broken}\n```',
    '```json\n{"parent_pr_data": broken}\n```', '```json\n{"unrelated": true}\n```',
    '```json\n{"nested": {"parent_pr_data": null}}\n```',
])
def test_ordinary_prompt_without_parent_descriptor_is_unchanged(context: AdapterContext, prompt: str) -> None:
    context.request.prompt = prompt
    assert load_adapter("dsh").prepare(context).stdin == prompt.encode()


@pytest.mark.parametrize("change", [
    "hash", "bundle", "symlink", "hardlink", "bundle_symlink", "fifo", "schema",
    "parent_root", "parent_root_slash", "not_parent", "descriptor", "malformed",
])
def test_invalid_parent_review_input_is_rejected_before_launch(
    context: AdapterContext, parent_review: dict[str, Any], change: str,
) -> None:
    import hashlib

    parameters = parent_review["parameters"]
    if change == "hash":
        parameters["parent_pr_data"]["sha256"] = "0" * 64
    elif change == "bundle":
        parent_review["bundle"].write_text("changed")
    elif change == "symlink":
        snapshot = parent_review["snapshot"]
        target = snapshot.with_name("target.json")
        snapshot.rename(target)
        snapshot.symlink_to(target)
    elif change == "hardlink":
        import os

        os.link(parent_review["snapshot"], parent_review["snapshot"].with_name("linked.json"))
    elif change == "bundle_symlink":
        bundle = parent_review["bundle"]
        target = bundle.with_name("target.bundle")
        bundle.rename(target)
        bundle.symlink_to(target)
    elif change == "fifo":
        import os

        snapshot = parent_review["snapshot"]
        snapshot.unlink()
        os.mkfifo(snapshot)
    elif change in {"parent_root", "parent_root_slash", "not_parent", "schema"}:
        snapshot = parent_review["snapshot"]
        document = json.loads(snapshot.read_text())
        if change == "schema":
            document["schema"] = "unexpected"
        else:
            document["target"]["parent_root"] = {
                "parent_root": "/tmp", "parent_root_slash": "/", "not_parent": str(snapshot.parent),
            }[change]
        snapshot.write_text(json.dumps(document))
        parameters["parent_pr_data"]["sha256"] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    elif change == "descriptor":
        parameters["parent_pr_data"] = {"path": "/tmp"}
    context.request.prompt = "```json\n" + json.dumps(parameters) + "\n```\n"
    if change == "malformed":
        context.request.prompt = '```json\n{"parent_pr_data": null}\n```\n'
    with pytest.raises(ValueError):
        load_adapter("dsh").prepare(context)
    assert not (context.receipt_path.parent / "dsh").exists()


def _patch(spec: LaunchSpec) -> dict[str, Any]:
    return {row["id"]: row for row in json.loads(Path(spec.argv[spec.argv.index("--patch") + 1]).read_text())}


@pytest.mark.parametrize(
    "provider,key",
    [("commandcode", "COMMANDCODE_API_KEY"), ("opencode-go", "OPENCODE_API_KEY")],
)
def test_prepare_isolates_state_and_passes_config_not_credentials(
    context: AdapterContext, monkeypatch: pytest.MonkeyPatch, provider: str, key: str
) -> None:
    monkeypatch.setattr(environ, "_literal", {key: "credential-not-for-files"})
    context.agent.provider = provider
    context.agent.env = [key]
    spec = load_adapter("dsh").prepare(context)
    assert spec.argv[spec.argv.index("--") + 1:][:3] == ("dsh", "--profile", "headless")
    assert spec.argv[-2:] == ("--json", "-")
    assert spec.stdin == context.request.prompt.encode()
    assert all("credential-not-for-files" not in arg for arg in spec.argv)
    root = context.receipt_path.parent / "dsh"
    assert Path(spec.env["DSH_HOME"]).is_relative_to(root)
    assert Path(spec.env["HOME"]).is_relative_to(root)
    # Spills of large command output must land in the managed, retained tree,
    # never in the disposable HOME or an ambient temporary directory.
    tmpdir = Path(spec.env["TMPDIR"])
    assert tmpdir.is_relative_to(root) and not tmpdir.is_relative_to(spec.env["HOME"])
    assert tmpdir.is_dir() and list(tmpdir.iterdir()) == [tmpdir / "exports"]
    assert tmpdir.stat().st_mode & 0o077 == 0
    assert spec.env["DSH_TELEMETRY_MODE"] == "DISABLED"
    patch = _patch(spec)
    assert "credential-not-for-files" not in json.dumps(patch)
    selection = patch["agent-default-model"]["config"]
    assert selection == {
        "provider": provider,
        "model": context.agent.model,
        "reasoningEffort": context.agent.effort,
    }
    route = patch["llm-pi-ai"]["config"]["providers"][provider]
    assert spec.env[route["apiKeyEnv"]] == "credential-not-for-files"
    assert route["apiKeyEnv"] != key  # no project .env / shared credential fallback
    assert route["models"][0]["id"] == context.agent.model
    assert route["retryPolicy"] == {"mode": "normal", "maxRetries": 0}
    if provider == "commandcode":
        assert route["baseURL"] == "https://api.commandcode.ai/provider/v1"
        assert route["compat"]["thinkingFormat"] == "deepseek"
    else:
        assert "baseURL" not in route
    assert patch["approval"]["config"]["policy"] == "never"
    assert patch["permission"]["config"]["presets"]["runner"]["approval"] == "never"
    assert patch["session-persistence-jsonl"]["config"]["compression"] == "none"
    assert patch["session-title-llm"]["disabled"] is True
    assert patch["plugin-package-inventory-deepseek"]["config"]["enabled"] is False
    with pytest.raises(FileExistsError):
        load_adapter("dsh").prepare(context)  # existing launch state is not reused


def test_missing_bwrap_prevents_launch_state(context: AdapterContext) -> None:
    from dataclasses import replace

    context = replace(context, environment={"PATH": str(context.work_dir / "no-cli")})
    with pytest.raises(ValueError, match="bubblewrap"):
        load_adapter("dsh").prepare(context)
    assert not (context.receipt_path.parent / "dsh").exists()


def test_unallowlisted_key_is_not_inherited(context: AdapterContext) -> None:
    context.agent.env = []
    spec = load_adapter("dsh").prepare(context)
    route = _patch(spec)["llm-pi-ai"]["config"]["providers"]["commandcode"]
    assert spec.env[route["apiKeyEnv"]] == ""


def test_skill_source_is_used_in_stdin(context: AdapterContext) -> None:
    skill = context.work_dir / "custom" / "check" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("read-only rules")
    context.agent.skill_sources = ["custom"]
    context.role.skills = ["check"]
    spec = load_adapter("dsh").prepare(context)
    assert str(skill) in spec.stdin.decode()
    assert context.request.prompt in spec.stdin.decode()


@pytest.mark.parametrize(
    "field,value",
    [("provider", None), ("provider", "other"), ("args", ["--profile", "web"])],
)
def test_unsupported_launch_options_are_rejected(context: AdapterContext, field: str, value: object) -> None:
    setattr(context.agent, field, value)
    with pytest.raises(ValueError):
        load_adapter("dsh").prepare(context)
    assert not (context.receipt_path.parent / "dsh").exists()


def _stream(text: str = '{"ok":true}', reason: dict[str, object] | None = None) -> list[dict[str, Any]]:
    return [
        {"type": "session", "sessionId": "observed-session", "cwd": "/work"},
        {"type": "status", "phase": "turn_start", "turn": 1},
        {
            "type": "status",
            "phase": "turn_end",
            "turn": 1,
            "reason": reason or {"kind": "completed"},
        },
        {"type": "final", "text": text},
    ]


def _collect(
    context: AdapterContext, events: Iterable[object], stderr: str = "", *, with_identity: bool = True
) -> AdapterOutcome:
    home = context.receipt_path.parent / "dsh" / "state"
    if with_identity and not home.exists():
        write_session(home, context.work_dir, session_id="observed-session")
    stdout_path = context.receipt_path.parent / "stdout.log"
    stdout_path.write_text("".join(event if isinstance(event, str) else json.dumps(event) + "\n" for event in events))
    stderr_path = context.receipt_path.parent / "stderr.log"
    stderr_path.write_text(stderr)
    return load_adapter("dsh").collect(context, stdout_path, stderr_path)


def test_collector_binds_stdout_session_to_observed_model(context: AdapterContext) -> None:
    write_session(
        context.receipt_path.parent / "dsh" / "state",
        context.work_dir,
        session_id="observed-session",
        provider="live-provider",
        model="live-model",
    )
    outcome = _collect(context, _stream())
    assert outcome.receipt is not None and outcome.receipt.status == "success"
    assert (outcome.identity.provider, outcome.identity.model, outcome.identity.effort) == (
        "live-provider",
        "live-model",
        "high",
    )


def test_missing_identity_discards_success_payload(context: AdapterContext) -> None:
    outcome = _collect(context, _stream(), with_identity=False)
    assert outcome.receipt is not None
    assert outcome.receipt.status == "response_failed" and outcome.receipt.payload is None
    assert outcome.identity.provider is outcome.identity.model is None


@pytest.mark.parametrize("code,status", [("MISSING_CREDENTIAL", "awaiting_authentication"), ("APPROVAL_REQUIRED", "awaiting_approval")])
def test_missing_identity_preserves_known_failure(context: AdapterContext, code: str, status: str) -> None:
    events = _stream(reason={"kind": "error", "error": {"code": code}})
    outcome = _collect(context, events, with_identity=False)
    assert outcome.receipt is not None
    assert outcome.receipt.status == status and outcome.receipt.payload is None


def test_mismatched_identity_discards_success_payload(context: AdapterContext) -> None:
    path = write_session(context.receipt_path.parent / "dsh" / "state", context.work_dir, session_id="observed-session")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[-1]["data"]["message"]["source"]["model"] = "different-model"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    outcome = _collect(context, _stream())
    assert outcome.receipt is not None
    assert outcome.receipt.status == "response_failed" and outcome.receipt.payload is None


@pytest.mark.parametrize("field", ["provider", "model", "reasoningEffort"])
def test_changed_route_with_matching_response_discards_payload(context: AdapterContext, field: str) -> None:
    path = write_session(context.receipt_path.parent / "dsh" / "state", context.work_dir, session_id="observed-session")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    header, assistant = json.loads(json.dumps(rows[1:]))
    header["seq"], assistant["seq"] = 2, 3
    header["data"]["header"]["config"][field] = "different-value"
    if field != "reasoningEffort":
        assistant["data"]["message"]["source"][field] = "different-value"
    rows.extend([header, assistant])
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    outcome = _collect(context, _stream())
    assert outcome.receipt is not None
    assert outcome.receipt.status == "response_failed" and outcome.receipt.payload is None
    assert outcome.identity.provider is outcome.identity.model is None


def _status(context: AdapterContext, events: Iterable[object]) -> ReceiptStatus:
    outcome = _collect(context, events)
    assert outcome.receipt is not None
    return outcome.receipt.status


@pytest.mark.parametrize(
    "shape,text,expected",
    [
        ("json", '{"ok":true}', {"ok": True}),
        ("json", '```json\n{"ok":true}\n```', {"ok": True}),
        (
            "json",
            'レビュー結果です。\n```json\n{"status":"success","active_findings":0}\n```',
            {"status": "success", "active_findings": 0},
        ),
        ("json", '```json\n{"ok":true}\n```\n以上です。\n', {"ok": True}),
        (
            "json",
            '前置き ☃\n複数行\n```json\n{\n  "note": "日本語\\n☃"\n}\n```\n後書き\n',
            {"note": "日本語\n☃"},
        ),
        ("json", '結果:\n```json\n{"ok":true}```', {"ok": True}),
        ("json", '```json\n{"first":1}\n```\n```json\n{"second":2}\n```', {"first": 1}),
        (
            "text",
            "複数行\n☃ authentication is a topic\n",
            "複数行\n☃ authentication is a topic\n",
        ),
        ("text", '説明\n```json\n{"ok":true}\n```\n', '説明\n```json\n{"ok":true}\n```\n'),
    ],
)
def test_success_payload_and_observed_identity_only(
    context: AdapterContext, shape: ResultShape, text: str, expected: Payload
) -> None:
    context.role.result_shape = shape
    outcome = _collect(context, _stream(text))
    assert outcome.receipt is not None
    assert outcome.receipt.status == "success"
    assert outcome.receipt.payload == expected
    assert outcome.identity.session_id == "observed-session"
    assert (outcome.identity.provider, outcome.identity.model, outcome.identity.effort) == (
        "observed-provider", "observed-model", "high"
    )
    assert outcome.identity.cli_version is None
    assert outcome.identity.skill_versions == {}


@pytest.mark.parametrize(
    "events",
    [
        [],
        [{"type": "final", "text": '{"ok":true}'}],
        _stream()[:-1],
        _stream()[1:],
        [_stream()[0], *_stream()[2:]],
        _stream() + [_stream()[-1]],
        [_stream()[0], _stream()[-1], *_stream()[1:3]],
        _stream() + ["broken {\n"],
        [_stream()[0], "broken {\n", *_stream()[1:]],
        _stream(""),
        _stream("{}"),
        _stream("[]"),
        _stream('{"n":NaN}'),
        _stream('{"a":1,"a":2}'),
        _stream('結果: {"ok":true}'),
        _stream("説明\n```json\n{}\n```"),
        _stream("説明\n```json\n[]\n```"),
        _stream('説明\n```json\n{"a":1,"a":2}\n```'),
        _stream('説明\n```json\n{"n":NaN}\n```'),
        _stream("説明\n```json\n{broken\n```"),
        _stream(reason={"kind": "unknown"}),
        [_stream()[0], _stream()[1], {**_stream()[2], "turn": 2}, _stream()[3]],
        [{**_stream()[0], "truncated": True}, *_stream()[1:]],
    ],
)
def test_missing_malformed_or_inconsistent_stream_is_not_success(
    context: AdapterContext, events: list[object]
) -> None:
    assert _status(context, events) == "response_failed"


@pytest.mark.parametrize(
    "code,state",
    [
        ("MISSING_CREDENTIAL", "awaiting_authentication"),
        ("INVALID_CREDENTIAL", "awaiting_authentication"),
        ("UNAUTHORIZED", "awaiting_authentication"),
        ("APPROVAL_REQUIRED", "awaiting_approval"),
        ("NETWORK_ERROR", "response_failed"),
    ],
)
def test_error_reason_overrides_even_nonempty_final(context: AdapterContext, code: str, state: str) -> None:
    outcome = _collect(
        context,
        _stream(reason={"kind": "error", "error": {"code": code, "message": "diagnostic"}}),
    )
    assert outcome.receipt is not None
    assert outcome.receipt.status == state
    assert outcome.receipt.payload is None


def test_empty_final_with_missing_credential_is_authentication(context: AdapterContext) -> None:
    assert (
        _status(
            context,
            _stream("", {"kind": "error", "error": {"code": "MISSING_CREDENTIAL"}}),
        )
        == "awaiting_authentication"
    )


def test_abort_maps_to_interrupted(context: AdapterContext) -> None:
    assert _status(context, _stream("", {"kind": "aborted"})) == "interrupted"


@pytest.mark.parametrize(
    "diagnostic",
    [
        'Error: offset 2001 is out of range for "x.py" (402 lines)',
        'Error: offset 2001 is out of range for "x.py" (401 lines)',
        'Error: offset 2001 is out of range for "x.py" (403 lines)',
        'Error: ENOENT: no such file or directory, open "401.py"',
        'Error: ENOENT: no such file or directory, open "403.py"',
        'Error: no such file or directory, open "UNAUTHORIZED.py"',
        "Error: invalid api key in a tool's fixture data",
        'Error: offset 2001 is out of range for "approval-cancelled.md" (402 lines)',
        'Error: ENOENT: no such file or directory, open "approval-unavailable.txt"',
        'Error: ENOENT: no such file or directory, open "approval-rejected.md"',
        'Error: ENOENT: no such file or directory, open "notes/requires approval.md"',
        'Error: ENOENT: no such file or directory, open "/approvals/cancelled.json"',
        'Error: ENOENT: no such file, open \'the user rejected tool "read"\'',
    ],
)
def test_recovered_tool_error_preserves_final_payload(context: AdapterContext, diagnostic: str) -> None:
    events = _stream()
    events[2:2] = [
        {"type": "tool_call", "callId": "read-1", "tool": "read", "input": {}},
        {"type": "tool_result", "callId": "read-1", "status": "error", "result": diagnostic},
    ]
    outcome = _collect(context, events)
    assert outcome.receipt is not None
    assert outcome.receipt.status == "success"
    assert outcome.receipt.payload == {"ok": True}
    assert outcome.identity.model == "observed-model"


@pytest.mark.parametrize("code", ["MISSING_CREDENTIAL", "INVALID_CREDENTIAL", "UNAUTHORIZED", "401", "403"])
def test_api_auth_error_overrides_completed_final(context: AdapterContext, code: str) -> None:
    events = _stream()
    events.insert(2, {"type": "error", "code": code, "message": "API request failed"})
    outcome = _collect(context, events)
    assert outcome.receipt is not None
    assert outcome.receipt.status == "awaiting_authentication"
    assert outcome.receipt.payload is None


@pytest.mark.parametrize(
    "diagnostic",
    [
        # Literal producer messages, not strings generated from the adapter's matcher:
        # @deepseek-ai/dsh-tools:serviceAsk and dsh-sandbox:approveEscalation (0.2.0-rc.2).
        'Error: the user rejected tool "bash"',
        'Error: the user rejected tool "403"',
        'Error: approval for tool "read" was cancelled',
        'Error: tool "read" requires approval (not yet supported)',
        'Error: tool "read" requires approval, but the call has no agent to route it through',
        'Error: tool "read" requires approval, but no approval channel is available',
        (
            'Error: the user rejected escalating this command to "danger-full-access"; '
            "it stays denied, so stop and explain instead of working around it"
        ),
        (
            'Error: the user rejected escalating this operation to "danger-full-access"; '
            "it stays denied, so stop and explain instead of working around it"
        ),
        (
            'Error: the user rejected escalating this program to "danger-full-access"; '
            "it stays denied, so stop and explain instead of working around it"
        ),
        'Error: approval for escalating to "danger-full-access" was cancelled',
        'Error: sandbox escalation to "danger-full-access" requires approval, but no approval channel is available',
        'Error: sandbox escalation to "danger-full-access" requires approval, but no approval service is composed',
        'Error: sandbox escalation to "danger-full-access" requires approval, but the call has no agent to route it through',
    ],
)
@pytest.mark.parametrize("ptc", [False, True])
def test_approval_error_in_tool_result_is_not_success(context: AdapterContext, diagnostic: str, ptc: bool) -> None:
    if ptc:
        # Producer framing checked independently with the installed runProgram/ToolRuntime.
        diagnostic = (
            "Error: code run failed (exception): ToolCallError: " + diagnostic.removeprefix("Error: ")
            + "\n    at bindingFailure (file:///fixture/process.js:902:22)"
        )
    events = _stream()
    events.insert(
        2,
        {
            "type": "tool_result",
            "callId": "call",
            "status": "error",
            "result": diagnostic,
        },
    )
    outcome = _collect(context, events)
    assert outcome.receipt is not None
    assert outcome.receipt.status == "awaiting_approval" and outcome.receipt.payload is None


@pytest.mark.parametrize("source", ["error", "turn_end", "stderr"])
@pytest.mark.parametrize(
    "diagnostic,state",
    [("APPROVAL_REQUIRED", "awaiting_approval"), ("401", "awaiting_authentication")],
)
def test_control_diagnostics_keep_generic_matching(
    context: AdapterContext, source: str, diagnostic: str, state: str
) -> None:
    events = _stream()
    stderr = ""
    if source == "error":
        events.insert(2, {"type": "error", "message": diagnostic})
    elif source == "turn_end":
        events[2]["reason"] = {"kind": "error", "message": diagnostic}
    else:
        events[-1]["text"] = ""  # Only failed streams consult stderr.
        stderr = diagnostic
    outcome = _collect(context, events, stderr)
    assert outcome.receipt is not None
    assert outcome.receipt.status == state and outcome.receipt.payload is None


@pytest.mark.parametrize("denial_first", [False, True])
@pytest.mark.parametrize("separate_turns", [False, True])
@pytest.mark.parametrize("ptc", [False, True])
def test_real_denial_is_not_hidden_by_later_recovery(
    context: AdapterContext, denial_first: bool, separate_turns: bool, ptc: bool
) -> None:
    events = _stream()
    denied = {"type": "tool_result", "callId": "deny", "status": "error",
              "result": 'Error: the user rejected tool "bash"'}
    if ptc:
        denied = json.loads(Path(__file__).with_name("ptc_tool_results.json").read_text())["rejected"]
    recovered = {"type": "tool_result", "callId": "read", "status": "error",
                 "result": 'Error: no such file "approval-cancelled.md"'}
    first, second = (denied, recovered) if denial_first else (recovered, denied)
    if separate_turns:
        events[2:2] = [
            first,
            {"type": "status", "phase": "turn_end", "turn": 1, "reason": {"kind": "completed"}},
            {"type": "status", "phase": "turn_start", "turn": 2},
            second,
        ]
        events[-2]["turn"] = 2
    else:
        events[2:2] = [first, second]
    outcome = _collect(context, events)
    assert outcome.receipt is not None
    assert outcome.receipt.status == "awaiting_approval" and outcome.receipt.payload is None


def test_completed_tool_output_is_not_control_diagnostic(context: AdapterContext) -> None:
    events = _stream()
    events.insert(2, {"type": "tool_result", "callId": "read", "status": "completed",
                      "result": 'Error: the user rejected tool "bash"'})
    outcome = _collect(context, events)
    assert outcome.receipt is not None
    assert outcome.receipt.status == "success" and outcome.receipt.payload == {"ok": True}


@pytest.mark.parametrize("denied", [False, True])
@pytest.mark.parametrize("ptc", [False, True])
def test_approval_classification_does_not_mutate_input_state(context: AdapterContext, denied: bool, ptc: bool) -> None:
    root = context.work_dir.parent
    for name in ("credentials", "backup", "tmp-sentinel", "cache"):
        (root / name).write_bytes(name.encode())
    (context.work_dir / "shared-link").symlink_to(root / "credentials")
    (context.work_dir / "shared-hardlink").hardlink_to(root / "credentials")
    write_session(context.receipt_path.parent / "dsh" / "state", context.work_dir,
                  session_id="observed-session")
    events = _stream()
    diagnostic = ('Error: the user rejected tool "bash"' if denied else
                  'Error: offset 2001 is out of range for "approval-cancelled.md" (402 lines)')
    if ptc:
        cases = json.loads(Path(__file__).with_name("ptc_tool_results.json").read_text())
        diagnostic = cases["rejected" if denied else "read"]["result"]
    events.insert(2, {"type": "tool_result", "callId": "deny", "status": "error", "result": diagnostic})
    stdout, stderr = context.receipt_path.parent / "stdout.log", context.receipt_path.parent / "stderr.log"
    stdout.write_text("".join(json.dumps(event) + "\n" for event in events))
    stderr.write_text("")

    def snapshot() -> dict[str, tuple[int, bytes | str | None]]:
        return {str(path.relative_to(root)): (
            path.lstat().st_mode,
            str(path.readlink()) if path.is_symlink() else path.read_bytes() if path.is_file() else None,
        ) for path in root.rglob("*")}

    before = snapshot()
    outcome = load_adapter("dsh").collect(context, stdout, stderr)
    assert outcome.receipt is not None
    assert outcome.receipt.status == ("awaiting_approval" if denied else "success")
    assert outcome.receipt.payload == (None if denied else {"ok": True})
    assert snapshot() == before


def test_startup_error_without_final_is_classified(context: AdapterContext) -> None:
    outcome = _collect(context, [{"type": "error", "message": "MISSING_CREDENTIAL"}])
    assert outcome.receipt is not None
    assert outcome.receipt.status == "awaiting_authentication"


def test_error_events_cannot_be_hidden_by_completed_final(context: AdapterContext) -> None:
    events = _stream()
    events.insert(2, {"type": "error", "message": "failed"})
    assert _status(context, events) == "response_failed"


def test_unicode_line_separator_inside_json_string_is_preserved(context: AdapterContext) -> None:
    context.role.result_shape = "text"
    text = "日本語\u2028次行 ☃"
    events = [json.dumps(event, ensure_ascii=False) + "\n" for event in _stream(text)]
    outcome = _collect(context, events)
    assert outcome.receipt is not None
    assert outcome.receipt.status == "success"
    assert outcome.receipt.payload == text


@pytest.mark.parametrize("event", [{"type": []}, {"type": "status", "phase": []}, []])
def test_invalid_event_type_does_not_escape_collector(context: AdapterContext, event: object) -> None:
    events: list[object] = list(_stream())
    events.insert(2, event)
    assert _status(context, events) == "response_failed"


@pytest.mark.parametrize(
    "event",
    [
        {"type": "text"},
        {"type": "thinking", "text": 3},
        {"type": "status", "phase": "unknown", "turn": 1},
        {"type": "status", "phase": "step_start", "turn": 2, "step": 1},
        {"type": "status", "phase": "step_end", "turn": 1, "step": True},
        {"type": "tool_call", "callId": "call", "tool": "read"},
        {"type": "tool_result", "callId": "call", "status": "unknown", "result": "x"},
        {"type": "tool_result", "callId": "call", "status": "completed"},
    ],
)
def test_invalid_intermediate_event_is_not_ignored(context: AdapterContext, event: dict[str, object]) -> None:
    events = _stream()
    events.insert(2, event)
    assert _status(context, events) == "response_failed"


def test_documented_truncated_tool_input_and_reasoning_are_accepted(context: AdapterContext) -> None:
    events = _stream()
    events[2:2] = [
        {"type": "thinking", "text": "bounded reasoning", "truncated": True},
        {"type": "tool_call", "callId": "call", "tool": "read", "truncated": True},
        {
            "type": "tool_result",
            "callId": "call",
            "status": "completed",
            "result": "bounded result",
            "truncated": True,
        },
    ]
    assert _status(context, events) == "success"


@pytest.mark.parametrize(
    "case,state",
    [("rejected", "awaiting_approval"), ("cancelled", "awaiting_approval"),
     ("unavailable", "awaiting_approval"), ("tool_approval", "awaiting_approval"),
     ("read", "success"), ("read_403", "success"), ("captured_only", "success"),
     ("caught_rejection", "success")],
)
def test_ptc_producer_output(context: AdapterContext, case: str, state: str) -> None:
    # Generated by DSH 0.2.0-rc.2 runProgram -> ToolRuntime -> projectJsonRun with
    # fake transport/approval only, independently of this adapter. Stack paths normalized.
    cases = json.loads(Path(__file__).with_name("ptc_tool_results.json").read_text())
    events = _stream()
    events.insert(2, cases[case])
    outcome = _collect(context, events)
    assert outcome.receipt is not None
    assert outcome.receipt.status == state
    assert outcome.receipt.payload == ({"ok": True} if state == "success" else None)
    assert outcome.identity.model == "observed-model"
    # collect has no denial latch: a subsequent independent successful stream is accepted.
    recovered = _collect(context, _stream())
    assert recovered.receipt is not None
    assert recovered.receipt.status == "success" and recovered.receipt.payload == {"ok": True}


def test_ptc_refusal_survives_truncated_captured_output(context: AdapterContext) -> None:
    case = json.loads(Path(__file__).with_name("ptc_tool_results.json").read_text())["rejected"]
    case["result"] += "\nCaptured output:\n" + "x" * 9000
    case["result"] = case["result"][:8000]
    case["truncated"] = True
    events = _stream()
    events.insert(2, case)
    assert _status(context, events) == "awaiting_approval"


@pytest.mark.parametrize("first", ["auth", "ptc"])
def test_ptc_refusal_preserves_first_control_failure(context: AdapterContext, first: str) -> None:
    refused = json.loads(Path(__file__).with_name("ptc_tool_results.json").read_text())["rejected"]
    auth = {"type": "error", "code": "401", "message": "API request failed"}
    events = _stream()
    events[2:2] = [auth, refused] if first == "auth" else [refused, auth]
    outcome = _collect(context, events)
    assert outcome.receipt is not None
    assert outcome.receipt.status == ("awaiting_authentication" if first == "auth" else "awaiting_approval")
    assert outcome.receipt.payload is None
