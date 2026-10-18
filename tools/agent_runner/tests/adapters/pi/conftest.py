"""Fixtures for the pi adapter tests."""

import subprocess
import sys
from pathlib import Path

import pytest

from tools.agent_runner.adapters import AdapterContext
from tools.agent_runner.models import Agent, Request, Role

FAKE_CLI = Path(__file__).with_name("fake_launcher.py")


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


@pytest.fixture
def context(tmp_path: Path) -> AdapterContext:
    work_dir = tmp_path / "worktree"
    work_dir.mkdir()
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    request = Request(
        run_id="run-1",
        request_id="req-1",
        agent_id="agent-a",
        role="inspect",
        work_dir=work_dir,
        prompt="THE PROMPT",
        deadline_seconds=60.0,
        result_shape="json",
    )
    agent = Agent(
        runtime="pi",
        command=[sys.executable, str(FAKE_CLI)],
        model="fixture-model",
        provider="fixture-provider",
        effort="fixture-effort",
    )
    role = Role(writes=False, deadline_seconds=60.0, result_shape="json")
    return AdapterContext(request, agent, role, work_dir, attempt / "receipt.json")


@pytest.fixture
def outside_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_RUNNER_DEPTH", raising=False)
