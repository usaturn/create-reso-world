"""Require the requested checkout to be auditable before paid work; others are reported only."""

from collections.abc import Callable
from pathlib import Path

from tools.agent_runner.adapters import Adapter, load_adapter
from tools.agent_runner.models import Config
from tools.agent_runner.workspace import CheckoutSnapshot, require_auditable_checkouts


def require_auditable_workflow(
    config: Config, workflow: str, repository: Path, *,
    adapter_loader: Callable[[str], Adapter] = load_adapter,
) -> CheckoutSnapshot:
    """Preflight the requested checkout before reservations or external execution.

    The configuration and loader arguments remain compatible with strict callers.
    Only the requested checkout (every registration when it cannot be identified)
    must be auditable; other registrations are fingerprinted and reported only.
    """
    return require_auditable_checkouts(repository)
