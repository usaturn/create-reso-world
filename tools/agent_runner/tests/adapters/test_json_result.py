"""json_result: rejection boundaries of the ported parser (#406).

The guards live here because json_result implements them (AGENTS.md: put a
guard in the tests of the module that implements it). The acceptance shapes
through the runner path are covered by the devin fake-CLI tests.
"""

import json

from tools.agent_runner.adapters.json_result import json_object


def test_malformed_wrapper_rejects_complete_inner_object() -> None:
    inner: dict[str, object] = {"status": "DONE", "commit": None}
    text = "```json\n" + '{"result": ' + json.dumps(inner) + ', "note": invalid}\n```'
    assert json_object(text) is None


def test_broken_correction_inside_fence_crossed_by_inline_span() -> None:
    done: dict[str, object] = {"status": "DONE", "commit": None}
    text = (
        "```json\n" + json.dumps(done) + "\n```\n"
        'Fix `name is required:\n```json\n{"status": 123\n```\n'
        "Then `pytest` later."
    )
    assert json_object(text) is None


def test_truncated_candidate_does_not_fall_back_to_earlier_object() -> None:
    text = '{"ok": true}\nDone.\n{"status": "DONE",'
    assert json_object(text) is None


def test_prose_before_object_is_a_passing_candidate() -> None:
    # The passing example required alongside the rejection guards: prose does
    # not hide a valid object, and a prose brace is not a candidate.
    assert json_object('Use {name} here.\nDone.\n{"ok": true}') == {"ok": True}
