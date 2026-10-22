"""usaturn/agent-workspace#598: issue_budget.py が能動時間・checkpoint の期日・同じ失敗の回数を数える仕様。"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parents[1] / "issue_budget.py"
SPEC = importlib.util.spec_from_file_location("issue_budget", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
budget = importlib.util.module_from_spec(SPEC)
sys.modules["issue_budget"] = budget
SPEC.loader.exec_module(budget)

T0 = datetime(2026, 10, 10, 0, 0, tzinfo=UTC)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def entries(*items: dict[str, Any]) -> list[Any]:
    return [budget.parse_entry(json.dumps(item, default=str)) for item in items]


def start(minutes: float = 0, **values: Any) -> dict[str, Any]:
    return {"event": "start", "at": at(minutes).isoformat(), "budget_minutes": 60, **values}


def event(name: str, minutes: float, **values: Any) -> dict[str, Any]:
    return {"event": name, "at": at(minutes).isoformat(), **values}


def test_user_wait_is_excluded_from_active_time() -> None:
    ledger = entries(start(), event("await-user", 10), event("resume", 40), event("end", 50))

    summary = budget.summarize(ledger, now=at(90))

    assert (summary.wall_seconds, summary.user_wait_seconds, summary.active_seconds) == (3000, 1800, 1200)
    assert summary.state == "ended"


def test_open_user_wait_counts_until_now() -> None:
    summary = budget.summarize(entries(start(), event("await-user", 10)), now=at(25))

    assert (summary.state, summary.user_wait_seconds, summary.active_seconds) == ("waiting_user", 900, 600)


def test_checkpoint_is_due_after_threshold_until_recorded() -> None:
    ledger = entries(start())
    assert budget.summarize(ledger, now=at(29)).due_checkpoints == ()
    assert budget.summarize(ledger, now=at(31)).due_checkpoints == (50,)

    ledger += entries(event("checkpoint", 32, decision="continue", reason="成果が増えている"))
    summary = budget.summarize(ledger, now=at(33))

    assert summary.due_checkpoints == ()
    assert summary.last_checkpoint is not None and summary.last_checkpoint.decision == "continue"
    assert budget.summarize(ledger, now=at(61)).due_checkpoints == (100,)


def test_user_wait_delays_checkpoint_due_time() -> None:
    ledger = entries(start(), event("await-user", 10), event("resume", 40))

    assert budget.summarize(ledger, now=at(55)).due_checkpoints == ()
    assert budget.summarize(ledger, now=at(61)).due_checkpoints == (50,)


def test_retry_limit_counts_same_reliability_signature() -> None:
    ledger = entries(
        start(retry_limit=1),
        event("failure", 1, failure_class="reliability", signature="timeout"),
        event("failure", 2, failure_class="reliability", signature="format"),
    )
    assert budget.summarize(ledger, now=at(3)).retry_limit_reached == ()

    ledger += entries(event("failure", 4, failure_class="reliability", signature="timeout"))
    summary = budget.summarize(ledger, now=at(5))

    assert summary.retry_limit_reached == ("timeout",)
    assert summary.failures["timeout"].count == 2
    assert summary.safety_failure is False


def test_single_safety_failure_is_reported() -> None:
    ledger = entries(start(), event("failure", 1, failure_class="safety", signature="unknown-send"))

    assert budget.summarize(ledger, now=at(2)).safety_failure is True
