"""End-to-end `run_workflow` with the real cursor adapter and a fake CLI."""

import subprocess
import sys
from pathlib import Path

import pytest

from tools.agent_runner.models import Agent, Assignment, Config, Role, Workflow
from tools.agent_runner.runner import run_workflow
from tools.agent_runner.tests.adapters.cursor.fake_cli import SESSION

pytest_plugins = ("tools.test_support.plugin",)
# Only fake agents are launched here; drop AGENT_RUNNER_DEPTH inside each test so a runner agent can run them
pytestmark = pytest.mark.usefixtures("outside_runner")

_FAKE = str(Path(__file__).with_name("fake_cli.py"))


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
            "cursor-agent": Agent(
                runtime="cursor",
                command=[sys.executable, _FAKE],
                model="requested-model",
                args=args or [],
                env=["PATH", "HOME"],
            )
        },
        roles={"inspect": Role(skills=[], writes=False, deadline_seconds=30.0, result_shape="json")},
        workflows={"audit": Workflow(assignments={"inspect": Assignment(agents=["cursor-agent"])})},
    )


def test_success_with_real_adapter_and_fake_cli(repository: Path, tmp_path: Path) -> None:
    batch = run_workflow(_config(), "audit", "summarize", repository, output_dir=tmp_path / "run")
    assert batch.state == "success"
    attempt = batch.results[0].attempts[0]
    assert attempt.exit_code == 0 and attempt.stop_confirmed
    assert attempt.payload == {"answer": 42}
    assert attempt.identity.session_id == SESSION
    assert attempt.identity.model == "Fake Model X"


def test_authentication_failure_maps_to_awaiting_authentication(repository: Path, tmp_path: Path) -> None:
    batch = run_workflow(_config(["--fail-auth"]), "audit", "prompt", repository, output_dir=tmp_path / "run")
    assert batch.state == "failed"
    assert batch.results[0].state == "awaiting_authentication"


def test_workspace_trust_maps_to_awaiting_approval(repository: Path, tmp_path: Path) -> None:
    batch = run_workflow(_config(["--fail-trust"]), "audit", "prompt", repository, output_dir=tmp_path / "run")
    assert batch.state == "failed"
    assert batch.results[0].state == "awaiting_approval"


def test_error_result_maps_to_response_failed(repository: Path, tmp_path: Path) -> None:
    batch = run_workflow(_config(["--fail-bad"]), "audit", "prompt", repository, output_dir=tmp_path / "run")
    assert batch.state == "failed"
    assert batch.results[0].state == "response_failed"


# #201: every cursor agent, whatever its name and whether it runs as the primary or a fallback, launches the
# writes=false roles that run the review helpers (inspect, self-review, fix-check) with the shell and without
# Cursor's sandbox
def test_read_only_roles_launch_any_cursor_agent_with_shell_and_without_sandbox(
    repository: Path, tmp_path: Path
) -> None:
    def agent(*args: str, model: str = "requested-model") -> Agent:
        return Agent(
            runtime="cursor", command=[sys.executable, _FAKE], model=model, args=list(args), env=["PATH", "HOME"]
        )

    read_only = Role(skills=[], writes=False, deadline_seconds=30.0, result_shape="json")
    config = Config(
        agents={
            "reviewer-one": agent("--echo-argv"),
            "broken-primary": agent("--fail-bad"),
            "fallback-reviewer": agent("--echo-argv", model="fallback-model"),
            "my-cursor": agent("--echo-argv"),
        },
        roles={"inspect": read_only, "self-review": read_only, "fix-check": read_only},
        workflows={
            "review-roles": Workflow(
                assignments={
                    "inspect": Assignment(agents=["reviewer-one"]),
                    "self-review": Assignment(agents=["broken-primary"], fallback=["fallback-reviewer"]),
                    "fix-check": Assignment(agents=["my-cursor"]),
                }
            )
        },
    )
    batch = run_workflow(config, "review-roles", "prompt", repository, output_dir=tmp_path / "run")
    assert batch.state == "success"
    results = {result.role: result for result in batch.results}
    assert [attempt.state for attempt in results["self-review"].attempts] == ["response_failed", "success"]
    assert {role: result.actual_agent for role, result in results.items()} == {
        "inspect": "reviewer-one",
        "self-review": "fallback-reviewer",
        "fix-check": "my-cursor",
    }
    for result in results.values():
        payload = result.attempts[-1].payload
        assert isinstance(payload, dict)
        argv = payload["argv"]
        assert isinstance(argv, list)
        assert argv.count("-f") == 1
        assert argv[argv.index("--sandbox") + 1] == "disabled"
        assert "--mode" not in argv and "--plan" not in argv


@pytest.mark.parametrize("args,state", [
    (["--nonzero"], "response_failed"),
    (["--truncate"], "response_failed"),
    (["--late-auth"], "awaiting_authentication"),
    (["--late-trust"], "awaiting_approval"),
])
def test_success_shaped_output_does_not_hide_failure(repository: Path, tmp_path: Path, args: list[str], state: str) -> None:
    batch = run_workflow(_config(args), "audit", "prompt", repository, output_dir=tmp_path / "run")
    assert batch.state == "failed"
    assert batch.results[0].state == state
    assert batch.results[0].attempts[0].stop_confirmed
