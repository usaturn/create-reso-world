"""Consumer-visible regressions from the final independent branch review."""

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

from tools.agent_runner import environ, process
from tools.agent_runner.adapters import AdapterContext, AdapterOutcome
from tools.agent_runner.runner import run_workflow
from tools.agent_runner.tests.test_runner import FakeAdapter, configuration

pytest_plugins = ("tools.test_support.plugin",)
# Only fake agents are launched here; drop AGENT_RUNNER_DEPTH inside each test so a runner agent can run them
pytestmark = pytest.mark.usefixtures("outside_runner")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    for args in (["init", "-q"], ["config", "user.name", "Test"], ["config", "user.email", "test@example.invalid"]):
        subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)
    (root / "file").write_text("original")
    subprocess.run(["git", "-C", str(root), "add", "file"], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], capture_output=True, check=True)
    return root


@pytest.mark.parametrize("concurrency", [2])
def test_one_fallback_cannot_fill_two_parallel_role_slots(repo: Path, concurrency: int) -> None:
    adapter = FakeAdapter({"a": {"missing": True}, "b": {"missing": True}})
    batch = run_workflow(
        configuration(["a", "b"], fallback=["c"]),
        "audit",
        "inspect",
        repo,
        concurrency=concurrency,
        adapter_loader=lambda _: adapter,
    )
    assert sum(attempt.agent_id == "c" for item in batch.results for attempt in item.attempts) == 1
    assert batch.state == "partial_success"
    exhausted = next(item for item in batch.results if item.state != "success")
    assert exhausted.fallback_exhausted


@pytest.mark.parametrize("malformed", [True])
def test_retained_receipts_are_scrubbed_even_when_invalid(
    repo: Path, monkeypatch: pytest.MonkeyPatch, malformed: bool
) -> None:
    secret = "known-credential-value"
    monkeypatch.setenv("SERVICE_TOKEN", secret)
    options: dict[str, object] = {"payload": {"credential": secret}}
    if malformed:
        options["raw"] = '{"credential":"' + secret
    batch = run_workflow(
        configuration(), "audit", "inspect", repo, adapter_loader=lambda _: FakeAdapter({"a": options})
    )
    attempt = batch.results[0].attempts[0]
    assert attempt.request_path is not None
    raw = (attempt.request_path.parent / "receipt.json").read_bytes()
    assert secret.encode() not in raw
    assert b"[REDACTED]" in raw
    assert attempt.sensitive_paths == []
    assert secret not in batch.model_dump_json()
    if not malformed:
        assert json.loads(raw)["payload"]["credential"] == "[REDACTED]"


class NeverCollect(FakeAdapter):
    def collect(self, context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        raise AssertionError("must not collect while process stop is unconfirmed")


def test_unconfirmed_stop_does_not_read_or_rewrite_live_receipt(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = process.execute
    calls = 0

    async def unconfirmed(*args: Any, **kwargs: Any) -> process.ProcessResult:
        nonlocal calls
        calls += 1
        result = await original(*args, **kwargs)
        return process.ProcessResult(result.state, result.exit_code, False, result.elapsed_seconds)

    # Patch the agent execute only; worktree preparation has its own real execute.
    monkeypatch.setattr("tools.agent_runner.runner.execute", unconfirmed)
    secret = "retained-live-credential"
    monkeypatch.setenv("SERVICE_TOKEN", secret)
    batch = run_workflow(
        configuration(fallback=["b"]),
        "audit",
        "inspect",
        repo,
        cancel=threading.Event(),
        adapter_loader=lambda _: NeverCollect({"a": {"payload": {"credential": secret}}}),
    )
    attempt = batch.results[0].attempts[0]
    assert calls == 1
    assert attempt.state == "response_failed" and not attempt.stop_confirmed
    assert attempt.request_path is not None
    path = attempt.request_path.parent / "receipt.json"
    assert attempt.sensitive_paths == [path]
    assert secret in path.read_text()
    assert secret not in batch.model_dump_json()


# Runs run_workflow in a fresh interpreter whose startup locale coercion cannot
# be reproduced by monkeypatch.setenv inside this already-running process.
_LITERAL_ENV_PROBE = """
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])

from tools.agent_runner.adapters import AdapterContext, AdapterOutcome, Capabilities, LaunchSpec
from tools.agent_runner.models import Agent, Assignment, Config, Receipt, Role, Workflow
from tools.agent_runner.runner import run_workflow


class EnvAdapter:
    capabilities = Capabilities()

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        return LaunchSpec(("/usr/bin/env", "-0"), b"")

    def collect(self, context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        env = {
            name.decode("utf-8", "replace"): value.decode("utf-8", "replace")
            for entry in stdout_path.read_bytes().split(b"\\0")
            if entry
            for name, value in [entry.split(b"=", 1)]
        }
        return AdapterOutcome(
            Receipt(
                run_id=context.request.run_id,
                request_id=context.request.request_id,
                agent_id=context.request.agent_id,
                role=context.request.role,
                status="success",
                payload={"env": env},
            )
        )


config = Config(
    agents={"a": Agent(runtime="pi", command=["/usr/bin/env"], model="a", env=["LC_CTYPE"])},
    roles={"inspect": Role(writes=False, deadline_seconds=30, result_shape="json")},
    workflows={"audit": Workflow(assignments={"inspect": Assignment(agents=["a"])})},
)
batch = run_workflow(
    config, "audit", "prompt", Path(sys.argv[2]), output_dir=Path(sys.argv[3]), adapter_loader=lambda _: EnvAdapter()
)
assert batch.state == "success", batch.model_dump_json()
attempt = batch.results[0].attempts[0]
assert attempt.payload is not None, batch.model_dump_json()
print(json.dumps(attempt.payload["env"]))
"""


# An allowlisted variable is inherited from the environment the runner was
# started with; interpreter startup coercion must not rewrite or inject it.
@pytest.mark.parametrize(
    ("exec_env", "expected"),
    [
        ({"LC_CTYPE": "C"}, "C"),
    ],
)
def test_allowlisted_environment_is_the_literal_exec_environment(
    repo: Path, tmp_path: Path, exec_env: dict[str, str], expected: str | None
) -> None:
    probe = tmp_path / "literal_env_probe.py"
    probe.write_text(_LITERAL_ENV_PROBE)
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(probe),
            str(Path(__file__).resolve().parents[3]),
            str(repo),
            str(tmp_path / "run"),
        ],
        env={"PATH": os.defpath, "HOME": str(tmp_path / "home"), **exec_env},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    env = json.loads(completed.stdout.strip().splitlines()[-1])
    assert env.get("LC_CTYPE") == expected


# A secret-named value that exists only in the exec environment can still be
# allowlisted into a command; it must be scrubbed from retained output even
# though os.environ never held it.
def test_exec_only_secrets_are_scrubbed_from_command_output(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "exec-env-only-credential-4f2a9c"
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)
    monkeypatch.setattr(environ, "_literal", environ.literal_environ() | {"SERVICE_TOKEN": secret})
    cfg = configuration()
    cfg.agents["a"].env = ["SERVICE_TOKEN"]
    batch = run_workflow(cfg, "audit", "inspect", repo, adapter_loader=lambda _: FakeAdapter())
    assert batch.state == "success" and batch.results[0].state == "success"
    attempt = batch.results[0].attempts[0]
    assert attempt.stdout_path is not None
    stdout = attempt.stdout_path.read_text()
    assert secret not in stdout and "[REDACTED]" in stdout
