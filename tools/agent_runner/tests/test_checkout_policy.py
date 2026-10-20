"""Separate unrelated sessions only when every candidate is confined.

The fake adapter's prepare callback represents a controller in another session,
not an agent write. Real DSH confinement is exercised by the sandbox tests.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from tools.agent_runner import workspace
from tools.agent_runner.adapters import AdapterContext, Capabilities, LaunchSpec
from tools.agent_runner.models import Assignment
from tools.agent_runner.runner import run_workflow
from tools.agent_runner.tests.test_runner import FakeAdapter, configuration, repository  # noqa: F401
from tools.agent_runner.tests.test_workspace import git

pytest_plugins = ("tools.test_support.plugin",)
pytestmark = pytest.mark.usefixtures("outside_runner")


class ConfinedFake(FakeAdapter):
    def __init__(self, change: Callable[[], object] = lambda: None) -> None:
        super().__init__()
        self.capabilities = Capabilities(confined_writes=True)
        self.change = change

    def prepare(self, context: AdapterContext) -> LaunchSpec:
        self.change()
        return super().prepare(context)


def test_confined_batch_reports_parallel_edit_without_blocking(repository: Path, tmp_path: Path) -> None:
    neighbor = workspace.create_worktree(repository, "HEAD", tmp_path / "neighbor")
    feature = workspace.create_worktree(repository, "HEAD", tmp_path / "feature")
    adapter = ConfinedFake(lambda: (neighbor / "tracked.txt").write_text("other session"))
    batch = run_workflow(
        configuration(), "audit", "respond", feature,
        output_dir=tmp_path / "run", adapter_loader=lambda _: adapter,
    )
    assert batch.state == "success" and batch.results[0].attempts[0].stop_confirmed
    assert batch.outside_changes == [] and batch.checkout_audit == []
    assert [(item.path, item.kind) for item in batch.unrelated_checkout_audit] == [
        (str(neighbor), "content_changed")
    ]


@pytest.mark.parametrize("target", ["main", "feature"])
def test_confined_batch_still_blocks_protected_edits(repository: Path, tmp_path: Path, target: str) -> None:
    feature = workspace.create_worktree(repository, "HEAD", tmp_path / "feature")
    changed = repository if target == "main" else feature
    adapter = ConfinedFake(lambda: (changed / "tracked.txt").write_text("concurrent protected edit"))
    batch = run_workflow(
        configuration(), "audit", "respond", feature,
        output_dir=tmp_path / "run", adapter_loader=lambda _: adapter,
    )
    assert batch.outside_changes == [str(changed)]
    assert [item.path for item in batch.checkout_audit] == [str(changed)]
    assert batch.unrelated_checkout_audit == []


def test_nonconfined_batch_preserves_strict_parallel_edit_audit(repository: Path, tmp_path: Path) -> None:
    neighbor = workspace.create_worktree(repository, "HEAD", tmp_path / "neighbor")

    class OtherSession(FakeAdapter):
        def prepare(self, context: AdapterContext) -> LaunchSpec:
            (neighbor / "tracked.txt").write_text("other session")
            return super().prepare(context)

    batch = run_workflow(
        configuration(), "audit", "respond", repository,
        output_dir=tmp_path / "run", adapter_loader=lambda _: OtherSession(),
    )
    assert batch.outside_changes == [str(neighbor)]
    assert batch.unrelated_checkout_audit == []


def test_confined_preflight_retains_unrelated_missing_registration(repository: Path, tmp_path: Path) -> None:
    from tools.agent_runner.checkout_policy import require_auditable_workflow

    neighbor = workspace.create_worktree(repository, "HEAD", tmp_path / "neighbor")
    neighbor.rename(tmp_path / "moved")  # No repair: the old registration is unavailable.
    adapter = ConfinedFake()
    require_auditable_workflow(configuration(), "audit", repository, adapter_loader=lambda _: adapter)
    batch = run_workflow(
        configuration(), "audit", "respond", repository,
        output_dir=tmp_path / "run", adapter_loader=lambda _: adapter,
    )
    assert batch.outside_changes == [] and batch.checkout_audit == []
    assert [(item.path, item.kind) for item in batch.unrelated_checkout_audit] == [
        (str(neighbor), "unavailable_before")
    ]
    assert str(neighbor) in git(repository, "worktree", "list", "--porcelain")


@pytest.mark.parametrize("case", ["nonconfined", "fallback", "all-self", "unavailable", "truthy"])
def test_unproven_configuration_keeps_unavailable_registration_blocking(
    repository: Path, tmp_path: Path, case: str,
) -> None:
    from tools.agent_runner.checkout_policy import require_auditable_workflow

    neighbor = workspace.create_worktree(repository, "HEAD", tmp_path / "neighbor")
    neighbor.rename(tmp_path / "moved")
    config = configuration()
    confined, ordinary = ConfinedFake(), FakeAdapter()
    config.agents["b"].runtime = "codex"
    if case == "fallback":
        config.workflows["audit"].assignments["inspect"].fallback = ["b"]
    if case == "all-self":
        config.workflows["audit"].assignments["inspect"] = Assignment(agents=["self"])

    def loader(runtime: str) -> FakeAdapter:
        if case == "unavailable":
            raise ValueError("unavailable adapter")
        if case == "truthy":
            from typing import cast
            ordinary.capabilities = Capabilities(confined_writes=cast(bool, "yes"))
        return ordinary if case in {"nonconfined", "truthy"} or runtime == "codex" else confined

    with pytest.raises(workspace.CheckoutAuditError) as caught:
        require_auditable_workflow(config, "audit", repository, adapter_loader=loader)
    assert [item.path for item in caught.value.findings] == [str(neighbor)]
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("target", ["main", "feature"])
def test_confined_preflight_rejects_protected_audit_failure(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str,
) -> None:
    from tools.agent_runner.checkout_policy import require_auditable_workflow

    feature = workspace.create_worktree(repository, "HEAD", tmp_path / "feature")
    failed = repository if target == "main" else feature
    original = workspace._fingerprint  # pyright: ignore[reportPrivateUsage]

    def fingerprint(path: Path) -> str:
        if path == failed:
            raise workspace.WorkspaceError("filesystem_unavailable")
        return original(path)

    monkeypatch.setattr(workspace, "_fingerprint", fingerprint)
    with pytest.raises(workspace.CheckoutAuditError) as caught:
        require_auditable_workflow(configuration(), "audit", feature, adapter_loader=lambda _: ConfinedFake())
    assert [item.path for item in caught.value.findings] == [str(failed)]


def test_required_path_missing_from_snapshot_is_not_success(repository: Path, tmp_path: Path) -> None:
    missing = str(tmp_path / "unregistered")
    with pytest.raises(workspace.CheckoutAuditError) as caught:
        workspace.require_auditable_checkouts(repository, required_paths=frozenset({str(repository), missing}))
    assert [item.path for item in caught.value.findings] == [missing]


def test_changed_adapter_guarantee_never_launches_nonconfined_attempt(repository: Path, tmp_path: Path) -> None:
    calls = 0
    ordinary = FakeAdapter()

    def loader(_: str) -> FakeAdapter:
        nonlocal calls
        calls += 1
        return ConfinedFake() if calls == 1 else ordinary

    batch = run_workflow(
        configuration(), "audit", "respond", repository,
        output_dir=tmp_path / "run", adapter_loader=loader,
    )
    assert calls == 2
    assert batch.state == "failed"
    assert batch.results[0].attempts[0].state == "unsupported"
    assert not list((tmp_path / "run").rglob("stdout.log"))
