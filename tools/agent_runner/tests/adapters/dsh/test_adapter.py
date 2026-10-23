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
    state, _, payload, reported = collect_attempt(
        load_adapter("dsh"), context, context.receipt_path.parent / "stdout.log",
        context.receipt_path.parent / "stderr.log", None,
    )
    # The collector never ran, so nothing was classified before an override (#212)
    assert state == "invalid_result" and payload is None and reported is None


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


@pytest.mark.parametrize("change", [
    "hash",     "parent_root", "parent_root_slash", "not_parent", ])
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


def test_missing_identity_discards_success_payload(context: AdapterContext) -> None:
    outcome = _collect(context, _stream(), with_identity=False)
    assert outcome.receipt is not None
    assert outcome.receipt.status == "response_failed" and outcome.receipt.payload is None
    assert outcome.identity.provider is outcome.identity.model is None


@pytest.mark.parametrize("code,status", [("MISSING_CREDENTIAL", "awaiting_authentication")])
def test_missing_identity_preserves_known_failure(context: AdapterContext, code: str, status: str) -> None:
    events = _stream(reason={"kind": "error", "error": {"code": code}})
    outcome = _collect(context, events, with_identity=False)
    assert outcome.receipt is not None
    assert outcome.receipt.status == status and outcome.receipt.payload is None


@pytest.mark.parametrize(
    ("reason", "reported"),
    [
        (None, "success"),
    ],
)
def test_unreadable_identity_keeps_the_classified_state(
    context: AdapterContext, reason: dict[str, object] | None, reported: str
) -> None:
    # A session without an assistant response (the first request failed, #212): collect replaces the
    # classified state with response_failed and hands the classified one over as reported_state
    path = write_session(context.receipt_path.parent / "dsh" / "state", context.work_dir, session_id="observed-session")
    path.write_text("".join(line + "\n" for line in path.read_text().splitlines()[:-1]))
    outcome = _collect(context, _stream(reason=reason))
    assert outcome.receipt is not None
    assert (outcome.receipt.status, outcome.reported_state) == ("response_failed", reported)


def test_mismatched_identity_discards_success_payload(context: AdapterContext) -> None:
    path = write_session(context.receipt_path.parent / "dsh" / "state", context.work_dir, session_id="observed-session")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[-1]["data"]["message"]["source"]["model"] = "different-model"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    outcome = _collect(context, _stream())
    assert outcome.receipt is not None
    assert outcome.receipt.status == "response_failed" and outcome.receipt.payload is None


@pytest.mark.parametrize("field", ["provider", "reasoningEffort"])
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
        ("json", '```json\n{"first":1}\n```\n```json\n{"second":2}\n```', {"first": 1}),
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
        _stream() + [_stream()[-1]],
        _stream('{"n":NaN}'),
        _stream('{"a":1,"a":2}'),
        _stream('結果: {"ok":true}'),
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


def test_abort_maps_to_interrupted(context: AdapterContext) -> None:
    assert _status(context, _stream("", {"kind": "aborted"})) == "interrupted"


@pytest.mark.parametrize(
    "diagnostic",
    [
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


@pytest.mark.parametrize(
    "ptc,diagnostic",
    [
        (False, 'Error: the user rejected tool "bash"'),
        (False, 'Error: approval for tool "read" was cancelled'),
        (False, 'Error: tool "read" requires approval (not yet supported)'),
        (False, 'Error: tool "read" requires approval, but the call has no agent to route it through'),
        (False, 'Error: tool "read" requires approval, but no approval channel is available'),
        (False, 'Error: the user rejected escalating this program to "danger-full-access"; '
                "it stays denied, so stop and explain instead of working around it"),
        (False, 'Error: approval for escalating to "danger-full-access" was cancelled'),
        (False, 'Error: sandbox escalation to "danger-full-access" requires approval, but no approval channel is available'),
        (False, 'Error: sandbox escalation to "danger-full-access" requires approval, but no approval service is composed'),
        (False, 'Error: sandbox escalation to "danger-full-access" requires approval, but the call has no agent to route it through'),
    ],
    ids=[
        "False-Error: the user rejected tool \"bash\"",
        "False-Error: approval for tool \"read\" was cancelled",
        "False-Error: tool \"read\" requires approval (not yet supported)",
        "False-Error: tool \"read\" requires approval, but the call has no agent to route it through",
        "False-Error: tool \"read\" requires approval, but no approval channel is available",
        "False-Error: the user rejected escalating this program to \"danger-full-access\"; it stays denied, so stop and explain instead of working around it",
        "False-Error: approval for escalating to \"danger-full-access\" was cancelled",
        "False-Error: sandbox escalation to \"danger-full-access\" requires approval, but no approval channel is available",
        "False-Error: sandbox escalation to \"danger-full-access\" requires approval, but no approval service is composed",
        "False-Error: sandbox escalation to \"danger-full-access\" requires approval, but the call has no agent to route it through",
    ],
)
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


@pytest.mark.parametrize(
    "ptc,separate_turns,denial_first",
    [
        (True, True, False),
    ],
    ids=[
        "True-True-False",
    ],
)
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


@pytest.mark.parametrize(
    "ptc,denied",
    [
        (False, True),
    ],
    ids=[
        "False-True",
    ],
)
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


def test_error_events_cannot_be_hidden_by_completed_final(context: AdapterContext) -> None:
    events = _stream()
    events.insert(2, {"type": "error", "message": "failed"})
    assert _status(context, events) == "response_failed"


@pytest.mark.parametrize(
    "event",
    [
        {"type": "status", "phase": "unknown", "turn": 1},
        {"type": "tool_call", "callId": "call", "tool": "read"},
        {"type": "tool_result", "callId": "call", "status": "unknown", "result": "x"},
        {"type": "tool_result", "callId": "call", "status": "completed"},
    ],
)
def test_invalid_intermediate_event_is_not_ignored(context: AdapterContext, event: dict[str, object]) -> None:
    events = _stream()
    events.insert(2, event)
    assert _status(context, events) == "response_failed"


@pytest.mark.parametrize(
    "case,state",
    [("rejected", "awaiting_approval"),           ("captured_only", "success"),
     ],
)
def test_ptc_producer_output(context: AdapterContext, case: str, state: str) -> None:
    # Generated by DSH 0.2.0-rc.2 runProgram -> ToolRuntime -> projectJsonRun with
    # fake transport/approval only, independently of this adapter. Stack paths normalized.
    # 0.2.1-rc.2 keeps these producer strings and framing; its real CLI emits the same first
    # line (the only part the adapter reads) for "rejected" (#209).
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
