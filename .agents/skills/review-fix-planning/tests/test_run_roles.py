"""設定役割の実行・回数制限・fix-check受取を実Gitとfake adapterで確かめる。"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.agent_runner import Config, ConfigError
from tools.agent_runner.adapters import AdapterContext, AdapterOutcome, Capabilities, LaunchSpec
from tools.agent_runner.models import Agent, Assignment, Identity, Receipt, Role, Runtime, Workflow
from tools.agent_runner.runner import EXCEPTIONS_HEADING

pytest_plugins = ("tools.test_support.plugin",)
# 偽の担当だけを起動するので、runner の担当（AGENT_RUNNER_DEPTH=1）の中でもテストの中だけ depth を外す
pytestmark = pytest.mark.usefixtures("outside_runner")

HELPER = Path(__file__).resolve().parents[1] / "scripts/run_roles.py"
SPEC = importlib.util.spec_from_file_location("planning_roles", HELPER)
assert SPEC is not None and SPEC.loader is not None
mod: Any = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

PROGRAM = """
import json, pathlib, sys
request = json.load(sys.stdin)
receipt = {key: request[key] for key in ('schema_version','run_id','request_id','agent_id','role')}
receipt.update(status='success', payload={'role': request['role']})
pathlib.Path(sys.argv[1]).write_text(json.dumps(receipt))
"""


class FakeAdapter:
    capabilities = Capabilities()

    def __init__(self) -> None:
        self.requests: list[Any] = []

    def __call__(self, runtime: str) -> FakeAdapter:
        return self

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        self.requests.append(context.request)
        return LaunchSpec(
            argv=(*context.agent.command, str(context.receipt_path)),
            stdin=context.request.model_dump_json().encode(),
        )

    def collect(self, context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        return AdapterOutcome(
            Receipt.model_validate_json(context.receipt_path.read_bytes()),
            Identity(model=context.agent.model, session_id="fake-session"),
        )


def config(self_review: str = "self", fix_check: str = "self") -> Config:
    """``a``・``b`` は pi、``d`` は DSH、``c`` は codex の担当（どれも fake adapter で動く）。"""
    runtimes: dict[str, Runtime] = {"a": "pi", "b": "pi", "d": "dsh", "c": "codex"}
    return Config(
        agents={
            name: Agent(runtime=runtime, command=[sys.executable, "-c", PROGRAM], model=name)
            for name, runtime in runtimes.items()
        },
        roles={
            name: Role(writes=name == "implement", deadline_seconds=20.0, result_shape="json")
            for name in ("implement", "self-review", "fix-check")
        },
        workflows={
            "fix": Workflow(
                assignments={
                    "implement": Assignment(agents=["a"]),
                    "self-review": Assignment(agents=[self_review]),
                    "fix-check": Assignment(agents=[fix_check]),
                }
            )
        },
    )


@pytest.fixture(autouse=True)
def isolated_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """GIT_DIR など（rebase --exec・フックが export）で、一時リポジトリの git が実リポジトリを書き換えない（#166）。"""
    for name in tuple(os.environ):
        if name.startswith("GIT_") or name in {"BASH_ENV", "ENV"}:
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


@pytest.fixture
def inputs(tmp_path: Path) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "fixture")
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "commit", "-qm", "base", "--allow-empty")
    source = git(repo, "rev-parse", "HEAD")
    git(repo, "commit", "-qm", "fix", "--allow-empty")
    target = git(repo, "rev-parse", "HEAD")
    request = {
        "repository": str(repo),
        "source_head": source,
        "revision": target,
        "pr": {"repository": "usaturn/create-reso-world", "number": 900},
        "prompt": {
            name: f"{name}: inspect all assigned committed input" for name in ("implement", "self-review", "fix-check")
        },
    }
    actor: dict[str, Any] = {
        "model": "fixture",
        "runtime": "pi",
        "provenance": {
            "agent_id": "self",
            "role": "decide",
            "provider": "unknown",
            "effort": "unknown",
            "session_id": "unknown",
            "cli_version": "unknown",
            "run_id": "unknown",
            "request_id": "unknown",
            "skills": [],
        },
    }
    planning = tmp_path / "planning.json"
    planning.write_text(
        json.dumps(
            {
                "schema": "review-findings/v2",
                "kind": "planning",
                "pr": request["pr"],
                "reviewed_head": source,
                "planner": actor,
                "verified_file": f"verified/{source[:12]}.json",
                "stages": {"decide_seconds": None, "fix_seconds": None, "fix_check_seconds": []},
                "fix_checks": [],
                "outcome": "stopped",
                "comment_id": None,
                "activities": [],
                "rework": [],
            }
        )
    )
    review_dir = tmp_path / "fix-staging"
    review_dir.mkdir()
    verified_file = review_dir / "verified-input.json"
    verified_file.write_text(
        json.dumps(
            {
                "schema": "review-findings/v1",
                "kind": "verified",
                "mode": "cycle",
                "pr": request["pr"],
                "reviewed_head": source,
                "base": source,
                "verifier": {"model": "fixture", "runtime": "pi"},
                "skill": {"path": ".agents/skills/review-verify/SKILL.md", "sha256": "0" * 64},
                "timing": {"started_at": "2026-10-08T06:00:00Z", "finished_at": "2026-10-08T06:00:00Z", "seconds": 0},
                "inputs": [],
                "coverage": {"closed": [], "remaining": []},
                "findings": [],
                "accuracy": {"reviewers": [], "find_seconds": {}, "verify_seconds": 0},
            }
        )
    )
    fix_input = {
        "repository": str(repo),
        "from": source,
        "to": target,
        "fix_ids": ["fixture#H-1@" + source[:12]],
        "fix_sections": "## Fix\nCorrect the introduced defect; relevant checks passed.",
        "verified_file": str(verified_file),
        "review_dir": str(review_dir),
    }
    return request, planning, fix_input


def launch(
    inputs: tuple[dict[str, Any], Path, dict[str, Any]], tmp_path: Path, selected: Config, **kwargs: Any
) -> Any:
    request, planning, fix_input = inputs
    return mod.run(
        selected, "self-review", request, tmp_path / "run", planning_file=planning, fix_input=fix_input, **kwargs
    )




SELF_REVIEW, FIX_CHECK = " (self-review role only)", " (fix-check role only)"


def exception_lines(prompt: str) -> list[str]:
    """runner の作業範囲の指示（最初の空行まで）のうち、例外の見出しの後の行。"""
    scope = prompt.split("\n\n", 1)[0].splitlines()
    return [line.removeprefix("- ") for line in scope[scope.index(EXCEPTIONS_HEADING) + 1 :]]


def granted(lines: list[str], path: object) -> int:
    """``path`` で始まる行（``<path>: <説明>`` か ``<path> and ...``）の数。"""
    return sum(line.startswith((f"{path}:", f"{path} ")) for line in lines)


@pytest.fixture
def parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """親の main worktree。fixture の repository とは別の Git ディレクトリ（プロジェクトの PR と同じ形）。"""
    root = tmp_path / "parent"
    root.mkdir()
    git(root, "init", "-q")
    monkeypatch.setattr(mod.review_target, "default_parent_root", lambda: root)
    return root


def test_external_review_roles_list_their_write_exceptions_with_the_role(
    inputs: tuple[dict[str, Any], Path, dict[str, Any]], tmp_path: Path, parent: Path
) -> None:
    """runner は全役割に同じ一覧を付けるので、各行は末尾で役割を名指しする（#658）。"""
    adapter = FakeAdapter()
    launch(inputs, tmp_path, config("a", "b"), adapter_loader=adapter)
    prompts = [exception_lines(request.prompt) for request in adapter.requests]
    assert len(prompts) == 2 and prompts[0] == prompts[1]
    lines = prompts[0]
    assert all(line.endswith((SELF_REVIEW, FIX_CHECK)) for line in lines)
    source_git = (Path(inputs[0]["repository"]) / ".git").resolve()
    review = [line for line in lines if line.endswith(SELF_REVIEW)]
    expected = (
        mod.ROOT,
        f"{parent}/reviews/usaturn/create-reso-world/#900-*",
        (parent / ".git").resolve() / "pr-review-save.lock",
        source_git,
        f"{parent}/tmp/agents/pr-review-scratch-900.*",
        mod.ROOT / ".venv",
    )
    assert [granted(review, path) for path in expected] == [1] * len(expected)
    check = [line for line in lines if line.endswith(FIX_CHECK)]
    assert [granted(check, path) for path in (mod.ROOT, source_git)] == [1, 1]


@pytest.mark.parametrize("assigned", [("self", "b"), ("a", "self")])
def test_only_the_externally_assigned_role_lists_exceptions(
    inputs: tuple[dict[str, Any], Path, dict[str, Any]], tmp_path: Path, parent: Path, assigned: tuple[str, str]
) -> None:
    adapter = FakeAdapter()
    launch(inputs, tmp_path, config(*assigned), adapter_loader=adapter)
    lines = exception_lines(adapter.requests[0].prompt)
    external = SELF_REVIEW if assigned[0] != "self" else FIX_CHECK
    assert lines and all(line.endswith(external) for line in lines)






@pytest.mark.parametrize("assigned", [("self", "self"), ("a", "b")])
def test_single_call_uses_both_review_roles_and_retains_self_instructions(
    inputs: tuple[dict[str, Any], Path, dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    assigned: tuple[str, str],
) -> None:
    original = mod.run_workflow
    calls: list[dict[str, Any]] = []

    def counted(*args: Any, **kwargs: Any) -> Any:
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(mod, "run_workflow", counted)
    adapter = FakeAdapter()
    batch = launch(inputs, tmp_path, config(*assigned), adapter_loader=adapter)
    assert len(calls) == 1 and calls[0]["concurrency"] == 2
    assert {result.role for result in batch.results} == {"self-review", "fix-check"}
    assert len(adapter.requests) == sum(name != "self" for name in assigned)
    saved = json.loads((batch.artifact_dir / "roles.json").read_text())
    assert set(saved["self_prompts"]) == {
        role for role, agent in zip(("self-review", "fix-check"), assigned, strict=True) if agent == "self"
    }
    assert saved["review_changes"] == []
    activities = json.loads(inputs[1].read_text())["activities"]
    assert len(activities) == 1 and activities[0]["stage"] == "pre_push_review"
    assert activities[0]["seconds"] is None
    receipt = mod.verifier.read_dispatch(batch.artifact_dir / "fix-check-receipt")
    assert receipt["request"] == inputs[2]
    assert len(receipt["batch"]["results"]) == 1
    if assigned[1] == "self":
        assert receipt["batch"]["state"] == "self" and receipt["verifier"] is None
        with pytest.raises(mod.verifier.AcceptError, match="not success"):
            mod.verifier.accept(batch.artifact_dir / "fix-check-receipt")
    else:
        assert receipt["verifier"]["provenance"]["agent_id"] == assigned[1]
        with pytest.raises(mod.verifier.AcceptError, match="payload"):
            mod.verifier.accept(batch.artifact_dir / "fix-check-receipt")


def test_unresolved_parent_stops_before_reserving_the_review(
    inputs: tuple[dict[str, Any], Path, dict[str, Any]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unresolved() -> Path:
        raise mod.review_target.TargetError(2, "no parent main worktree")

    monkeypatch.setattr(mod.review_target, "default_parent_root", unresolved)
    with pytest.raises(mod.RoleInputError):
        launch(inputs, tmp_path, config("a", "self"), adapter_loader=FakeAdapter())
    assert json.loads(inputs[1].read_text())["activities"] == []
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("wrong", ["pr", "head"])
def test_verified_input_mismatch_never_consumes_the_only_review(inputs: Any, tmp_path: Path, wrong: str) -> None:
    path = Path(inputs[2]["verified_file"])
    value = json.loads(path.read_text())
    if wrong == "pr":
        value["pr"]["number"] += 1
    else:
        value["reviewed_head"] = "f" * 40
    path.write_text(json.dumps(value))
    with pytest.raises((ValueError, mod.findings.FindingsError)):
        launch(inputs, tmp_path, config())
    assert not (tmp_path / "run").exists()
    assert json.loads(inputs[1].read_text())["activities"] == []




def test_second_review_is_refused_even_when_all_assignments_are_self(inputs: Any, tmp_path: Path) -> None:
    launch(inputs, tmp_path, config())
    with pytest.raises(ValueError, match="already reserved"):
        mod.run(config(), "self-review", inputs[0], tmp_path / "second", planning_file=inputs[1], fix_input=inputs[2])
    assert not (tmp_path / "second").exists()


def test_existing_lock_does_not_start_or_erase_another_call(inputs: Any, tmp_path: Path) -> None:
    lock = inputs[1].with_suffix(".json.review-lock")
    lock.write_text("other-session")
    with pytest.raises(ValueError, match="locked"):
        launch(inputs, tmp_path, config())
    assert lock.read_text() == "other-session"
    assert json.loads(inputs[1].read_text())["activities"] == []




def test_binding_mismatch_is_rejected_before_reservation(inputs: Any, tmp_path: Path) -> None:
    inputs[0]["pr"]["number"] = 901
    with pytest.raises(ValueError):
        launch(inputs, tmp_path, config())
    assert json.loads(inputs[1].read_text())["activities"] == []


def test_unusable_fix_check_destination_stops_before_reservation_or_launch(
    inputs: Any, tmp_path: Path, parent: Path
) -> None:
    """保存できない fix-check の保存先では、戻せない 1 回枠を予約せず、担当も起動しない（#177）。"""
    _, planning, fix_input = inputs
    fix_input["review_dir"] = str(tmp_path / "absent-staging")
    adapter = FakeAdapter()
    with pytest.raises(ValueError, match="review_dir must be an existing directory"):
        launch(inputs, tmp_path, config("a", "b"), adapter_loader=adapter)
    assert adapter.requests == []
    assert json.loads(planning.read_text())["activities"] == []
    assert not (tmp_path / "run").exists()
    assert not planning.with_suffix(".json.review-lock").exists()


def test_invalid_writable_review_role_never_consumes_budget(inputs: Any, tmp_path: Path) -> None:
    selected = config()
    selected.roles["self-review"].writes = True
    with pytest.raises(ConfigError):
        launch(inputs, tmp_path, selected)
    assert json.loads(inputs[1].read_text())["activities"] == []










# DSH には親の準備が無い（#671）。codex は read-only の sandbox で helper を起動できない（#731）
@pytest.mark.parametrize(
    ("agent", "reason", "role", "slot"),
    [
        pytest.param("d", "dsh runtime", "self-review", "agents", id="dsh-self-review"),
        pytest.param("c", "codex runtime agent", "fix-check", "fallback", id="codex-fix-check-fallback"),
    ],
)
def test_review_assignment_that_cannot_run_the_helpers_stops_before_reserving_the_review(
    inputs: tuple[dict[str, Any], Path, dict[str, Any]],
    tmp_path: Path,
    parent: Path,
    agent: str,
    reason: str,
    role: str,
    slot: str,
) -> None:
    """完了できない担当は、1 回枠を消費する前に止める（#671・#731）。fallback は一次担当が self でも見る。"""
    selected = config()
    assignment = selected.workflows["fix"].assignments[role]
    if slot == "agents":
        assignment.agents = [agent]
    else:
        assignment.fallback = [agent]
    adapter = FakeAdapter()
    with pytest.raises(mod.RoleInputError, match=reason):
        launch(inputs, tmp_path, selected, adapter_loader=adapter)
    assert adapter.requests == []
    assert json.loads(inputs[1].read_text())["activities"] == []
    assert not (tmp_path / "run").exists()
    assert not inputs[1].with_suffix(".json.review-lock").exists()








def test_review_directory_tampering_is_not_accepted_or_cleaned(inputs: Any, tmp_path: Path) -> None:
    class Tampering(FakeAdapter):
        def collect(self, context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
            Path(inputs[2]["review_dir"], "external-change").write_text("do not erase")
            return super().collect(context, stdout_path, stderr_path)

    batch = launch(inputs, tmp_path, config("a", "b"), adapter_loader=Tampering())
    saved = json.loads((batch.artifact_dir / "roles.json").read_text())
    assert saved["review_changes"] == ["external-change"]
    with pytest.raises(mod.verifier.AcceptError, match="review_dir changed"):
        mod.verifier.accept(batch.artifact_dir / "fix-check-receipt")
    assert Path(inputs[2]["review_dir"], "external-change").read_text() == "do not erase"


def test_unconfirmed_stop_blocks_fix_check_accept_and_keeps_budget(
    inputs: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = mod.run_workflow

    def no_stop(*args: Any, **kwargs: Any) -> Any:
        batch = original(*args, **kwargs)
        batch.results[0].attempts[-1].stop_confirmed = False
        return batch

    monkeypatch.setattr(mod, "run_workflow", no_stop)
    batch = launch(inputs, tmp_path, config("a", "b"), adapter_loader=FakeAdapter())
    assert json.loads((batch.artifact_dir / "roles.json").read_text())["review_changes"] is None
    with pytest.raises(mod.verifier.AcceptError, match="not success"):
        mod.verifier.accept(batch.artifact_dir / "fix-check-receipt")
    assert len(json.loads(inputs[1].read_text())["activities"]) == 1
