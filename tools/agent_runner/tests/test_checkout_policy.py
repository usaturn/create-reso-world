"""The requested checkout shares one preflight and post-execution audit boundary.

Other registrations are reported only (Spec R8). Fake writes model another
session's activity.
"""

from pathlib import Path

import pytest

from tools.agent_runner import workspace
from tools.agent_runner.adapters import AdapterContext, LaunchSpec
from tools.agent_runner.checkout_policy import require_auditable_workflow
from tools.agent_runner.runner import RunnerError, run_workflow
from tools.agent_runner.tests.test_runner import FakeAdapter, configuration, repository  # noqa: F401
from tools.agent_runner.tests.test_workspace import git

pytest_plugins = ("tools.test_support.plugin",)
pytestmark = pytest.mark.usefixtures("outside_runner")


def test_batch_reports_parallel_checkout_edit(repository: Path, tmp_path: Path) -> None:
    neighbor = workspace.create_worktree(repository, "HEAD", tmp_path / "neighbor")
    feature = workspace.create_worktree(repository, "HEAD", tmp_path / "feature")

    class EditingAdapter(FakeAdapter):
        def prepare(self, context: AdapterContext) -> LaunchSpec:
            (neighbor / "tracked.txt").write_text("other session")
            return super().prepare(context)

    batch = run_workflow(
        configuration(), "audit", "respond", feature,
        output_dir=tmp_path / "run", adapter_loader=lambda _: EditingAdapter(),
    )
    assert batch.state == "success" and batch.results[0].attempts[0].stop_confirmed
    assert batch.outside_changes == []
    assert batch.unprotected_changes == [str(neighbor)]
    assert [(item.path, item.kind, item.protected) for item in batch.checkout_audit] == [
        (str(neighbor), "content_changed", False)
    ]


def test_unavailable_neighbor_is_reported_and_unavailable_target_blocks_launch(
    repository: Path, tmp_path: Path
) -> None:
    neighbor = workspace.create_worktree(repository, "HEAD", tmp_path / "neighbor")
    neighbor.rename(tmp_path / "moved")

    def no_launch(_: str) -> FakeAdapter:
        pytest.fail("an unavailable audit must block adapter loading")

    snapshot = require_auditable_workflow(configuration(), "audit", repository, adapter_loader=no_launch)
    assert snapshot[str(neighbor)] is None
    batch = run_workflow(
        configuration(), "audit", "respond", repository,
        output_dir=tmp_path / "run", adapter_loader=lambda _: FakeAdapter(),
    )
    assert batch.state == "success"
    assert batch.outside_changes == []
    assert batch.unprotected_changes == [str(neighbor)]
    assert [(item.path, item.kind, item.protected) for item in batch.checkout_audit] == [
        (str(neighbor), "unavailable_before", False)
    ]
    target = workspace.create_worktree(repository, "HEAD", tmp_path / "target")
    (target / "tracked.txt").chmod(0)  # git still works; only the fingerprint fails
    try:
        with pytest.raises(workspace.CheckoutAuditError) as caught:
            require_auditable_workflow(configuration(), "audit", target, adapter_loader=no_launch)
        assert [(item.path, item.protected) for item in caught.value.findings] == [(str(target), True)]
        with pytest.raises(RunnerError):
            run_workflow(
                configuration(), "audit", "respond", target,
                output_dir=tmp_path / "blocked", adapter_loader=no_launch,
            )
        assert not (tmp_path / "blocked").exists()
    finally:
        (target / "tracked.txt").chmod(0o644)
    assert str(neighbor) in git(repository, "worktree", "list", "--porcelain")
