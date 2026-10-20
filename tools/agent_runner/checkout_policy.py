"""One audit policy for the runner and strict result consumers.

Only trusted adapters with whole-process confinement may separate unrelated
checkouts. A workflow whose primaries are all self keeps the full audit because
an assignment override can retain a fallback that never launches. Otherwise
every assigned candidate, including unused fallbacks, must qualify.
"""

from collections.abc import Callable
from pathlib import Path

from tools.agent_runner.adapters import Adapter, load_adapter
from tools.agent_runner.models import CheckoutAudit, Config
from tools.agent_runner.workspace import (
    CheckoutAuditError,
    CheckoutSnapshot,
    WorkspaceError,
    protected_checkout_paths,
    require_auditable_checkouts,
)


def workflow_checkout_scope(
    config: Config, workflow: str, repository: Path, *,
    adapter_loader: Callable[[str], Adapter] = load_adapter,
) -> frozenset[str] | None:
    """None means all registrations are required; never trust the sandbox name."""
    assignments = config.workflows[workflow].assignments.values()
    if not any(name != "self" for assignment in assignments for name in assignment.agents):
        # --assign self keeps the template's fallback, but that fallback never runs.
        return None
    candidates = {
        name
        for assignment in assignments
        for name in (*assignment.agents, *assignment.fallback)
        if name != "self"
    }
    try:
        for name in sorted(candidates):
            if adapter_loader(config.agents[name].runtime).capabilities.confined_writes is not True:
                return None
    except Exception:
        # An adapter we cannot inspect is not evidence of confinement.
        return None
    return protected_checkout_paths(repository)


def require_auditable_workflow(
    config: Config, workflow: str, repository: Path, *,
    adapter_loader: Callable[[str], Adapter] = load_adapter,
) -> CheckoutSnapshot:
    """Run before reservations and paid work, using the runner's same policy."""
    try:
        required = workflow_checkout_scope(config, workflow, repository, adapter_loader=adapter_loader)
    except WorkspaceError as error:
        raise CheckoutAuditError([
            CheckoutAudit(path=str(repository), kind="unavailable_before", reason=error.reason)
        ]) from None
    return require_auditable_checkouts(repository, required_paths=required)
