"""All registrations share one preflight and post-execution audit boundary.

These safety tests prevent accepting changes or starting work when a registered
checkout cannot be audited. Fake writes model another session's activity.
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


def test_unavailable_registration_blocks_work_without_launch_or_repair(repository: Path, tmp_path: Path) -> None:
    neighbor = workspace.create_worktree(repository, "HEAD", tmp_path / "neighbor")
    neighbor.rename(tmp_path / "moved")

    def no_launch(_: str) -> FakeAdapter:
        pytest.fail("an unavailable audit must block adapter loading")

    with pytest.raises(workspace.CheckoutAuditError) as caught:
        require_auditable_workflow(configuration(), "audit", repository, adapter_loader=no_launch)
    assert [item.path for item in caught.value.findings] == [str(neighbor)]
    with pytest.raises(RunnerError):
        run_workflow(
            configuration(), "audit", "respond", repository,
            output_dir=tmp_path / "run", adapter_loader=no_launch,
        )
    assert not (tmp_path / "run").exists()
    assert str(neighbor) in git(repository, "worktree", "list", "--porcelain")
