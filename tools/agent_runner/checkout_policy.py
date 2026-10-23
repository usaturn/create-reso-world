"""Require all registered checkouts to be auditable before paid work."""

from collections.abc import Callable
from pathlib import Path

from tools.agent_runner.adapters import Adapter, load_adapter
from tools.agent_runner.models import Config
from tools.agent_runner.workspace import CheckoutSnapshot, require_auditable_checkouts


def require_auditable_workflow(
    config: Config, workflow: str, repository: Path, *,
    adapter_loader: Callable[[str], Adapter] = load_adapter,
) -> CheckoutSnapshot:
    """Preflight all registrations before reservations or external execution.

    The configuration and loader arguments remain compatible with strict callers;
    the audit boundary always covers every registered checkout.
    """
    return require_auditable_checkouts(repository)
