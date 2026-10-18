"""End-to-end `run_workflow` with the real codex adapter and a fake `codex` CLI."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.agent_runner import environ
from tools.agent_runner.models import Agent, Assignment, Config, Role, Workflow
from tools.agent_runner.runner import run_workflow
from tools.agent_runner.tests.adapters.codex.fake_cli import SESSION

pytest_plugins = ("tools.test_support.plugin",)
# Only fake agents are launched here; drop AGENT_RUNNER_DEPTH inside each test so a runner agent can run them
pytestmark = pytest.mark.usefixtures("outside_runner")

_FAKE = str(Path(__file__).with_name("fake_cli.py"))


@pytest.fixture(autouse=True)
def isolated_runtime_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Fake subprocesses must never write rollouts into the user's CLI state.
    monkeypatch.setattr(environ, "_literal", {
        "PATH": os.defpath,
        "HOME": str(tmp_path / "fake-home"),
        "CODEX_HOME": str(tmp_path / "fake-codex-home"),
    })


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (
        ["init", "-q"],
        ["config", "user.email", "test@example.invalid"],
        ["config", "user.name", "Test"],
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    (repo / "tracked.txt").write_text("original")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True, capture_output=True)
    return repo


def _config(args: list[str] | None = None) -> Config:
    return Config(
        agents={
            "codex-agent": Agent(
                runtime="codex",
                command=[sys.executable, _FAKE],
                model="requested-model",
                args=args or [],
                env=["PATH", "HOME", "CODEX_HOME"],
            )
        },
        roles={"inspect": Role(skills=[], writes=False, deadline_seconds=30.0, result_shape="json")},
        workflows={"audit": Workflow(assignments={"inspect": Assignment(agents=["codex-agent"])})},
    )


def test_success_with_real_adapter_and_fake_cli(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / "codex-home"
    monkeypatch.setattr(environ, "_literal", environ.literal_environ() | {"CODEX_HOME": str(codex_home)})
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "wrong-controller-home"))
    batch = run_workflow(_config(), "audit", "summarize", repository, output_dir=tmp_path / "run")
    assert batch.state == "success"
    attempt = batch.results[0].attempts[0]
    assert attempt.exit_code == 0 and attempt.stop_confirmed
    assert attempt.payload == {"answer": 42}
    assert attempt.identity.session_id == SESSION
    # The fake CLI wrote its own session rollout into the runtime home it inherited.
    rollouts = list((codex_home / "sessions").rglob(f"rollout-*-{SESSION}.jsonl"))
    assert len(rollouts) == 1 and rollouts[0].is_file()
    assert attempt.identity.model == "observed-model"
    assert attempt.identity.provider == "observed-provider"
    assert attempt.identity.effort == "observed-effort"
    assert attempt.identity.cli_version == "observed-cli"


def test_authentication_failure_maps_to_awaiting_authentication(repository: Path, tmp_path: Path) -> None:
    batch = run_workflow(_config(["--fail-auth"]), "audit", "prompt", repository, output_dir=tmp_path / "run")
    assert batch.state == "failed"
    assert batch.results[0].state == "awaiting_authentication"


def test_event_error_maps_to_response_failed(repository: Path, tmp_path: Path) -> None:
    batch = run_workflow(_config(["--fail-bad"]), "audit", "prompt", repository, output_dir=tmp_path / "run")
    assert batch.state == "failed"
    assert batch.results[0].state == "response_failed"


@pytest.mark.parametrize('args,state', [
    (['--nonzero'], 'response_failed'),
    (['--fail-approval'], 'awaiting_approval'),
    (['--truncate'], 'response_failed'),
])
def test_plausible_response_does_not_hide_failure(repository: Path, tmp_path: Path, args: list[str], state: str) -> None:
    batch = run_workflow(_config(args), 'audit', 'prompt', repository, output_dir=tmp_path/'run')
    attempt = batch.results[0].attempts[0]
    assert batch.state == 'failed'
    assert batch.results[0].state == state
    assert attempt.stop_confirmed
