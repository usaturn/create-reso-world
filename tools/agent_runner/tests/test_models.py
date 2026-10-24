"""Reading results that earlier versions of the runner saved."""

import json

import pytest
from pydantic import ValidationError

from tools.agent_runner.models import BatchResult


def saved_v1_result(unrelated: list[dict[str, object]]) -> str:
    """A Pi result saved before #243: model_dump_json always wrote ``unrelated_checkout_audit``."""
    attempt = {"agent_id": "pi-gpt", "state": "success", "elapsed_seconds": 1.0, "stop_confirmed": True}
    return json.dumps(
        {
            "schema_version": 1,
            "run_id": "run-1",
            "state": "success",
            "assignments": {"inspect": ["pi-gpt"]},
            "results": [
                {
                    "request_id": "request-1",
                    "role": "inspect",
                    "requested_agent": "pi-gpt",
                    "actual_agent": "pi-gpt",
                    "state": "success",
                    "attempts": [attempt],
                }
            ],
            "outside_changes": [],
            "checkout_audit": [],
            "unrelated_checkout_audit": unrelated,
            "elapsed_seconds": 1.0,
            "artifact_dir": "/runs/run-1",
        }
    )


@pytest.mark.parametrize(
    "unrelated",
    [[], [{"path": "/other", "kind": "content_changed", "reason": "content_changed"}]],
    ids=["empty", "recorded"],
)
def test_saved_v1_result_keeps_its_stop_state_without_dropping_observations(
    unrelated: list[dict[str, object]],
) -> None:
    """The loop's resume and resource reclaim, role runs, attach-runner and issue-to-pr read saved results here.

    Rejecting an empty legacy field makes the loop treat a stopped run as having no result and keep its
    resources unreclaimed; accepting a recorded observation would discard it without notice.
    """
    text = saved_v1_result(unrelated)
    if unrelated:
        with pytest.raises(ValidationError):
            BatchResult.model_validate_json(text)
        return
    batch = BatchResult.model_validate_json(text)
    assert [attempt.stop_confirmed for item in batch.results for attempt in item.attempts] == [True]
