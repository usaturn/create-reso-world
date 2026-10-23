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


@pytest.mark.parametrize("mode,exit_code,success", [
    ("success", 0, True),
    ("turn-failed", 0, False),
])
def test_reconnect_requires_fresh_completion_and_clean_process_exit(
    repository: Path, tmp_path: Path, mode: str, exit_code: int, success: bool,
) -> None:
    args = [f"--reconnect={mode}", *(["--nonzero"] if exit_code else [])]
    batch = run_workflow(_config(args), "audit", "prompt", repository, output_dir=tmp_path / "run")
    attempt = batch.results[0].attempts[0]
    assert attempt.exit_code == exit_code and attempt.stop_confirmed
    assert batch.state == ("success" if success else "failed")
    assert attempt.state == ("success" if success else "response_failed")
    assert attempt.identity.session_id == SESSION
    assert attempt.identity.model == "observed-model"
    assert batch.outside_changes == []
    if success:
        assert attempt.payload == {"answer": 42}
    elif mode != "success":
        assert attempt.payload is None
