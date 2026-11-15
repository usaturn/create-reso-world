"""json_result: rejection boundaries of the ported parser (#406).

The guards live here because json_result implements them (AGENTS.md: put a
guard in the tests of the module that implements it). The acceptance shapes
through the runner path are covered by the devin fake-CLI tests.
"""

import json

from tools.agent_runner.adapters.json_result import first_json_object, json_object


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


def test_jsonc_example_accepts_result_after_fence() -> None:
    # S: treating a jsonc example as a result fence loses the later DONE when
    # the comment makes the example fail to decode, turning a success into
    # response_failed. The later result is also the positive control that an
    # implementation rejecting every example cannot pass.
    text = (
        "設定例:\n"
        "```jsonc\n"
        "{\n"
        '  "名前": "試験",\n'
        '  "enabled": true /* comment */\n'
        "}\n"
        "```\n"
        "結果:\n"
        "```json\n"
        '{"status": "DONE"}\n'
        "```\n"
    )
    assert json_object(text) == {"status": "DONE"}


def test_malformed_example_requires_result_beyond_its_end() -> None:
    # S: ignoring a json5 example unconditionally accepts the EXAMPLE object
    # inside it even though the malformed candidate was never followed by a
    # result beyond the example's end. It also prevents accepting OLD as a
    # fallback; both would report a broken answer as success.
    text = (
        '{"status": "OLD"}\n'
        "```json5\n"
        '{"enabled": true,}\n'
        '{"status": "EXAMPLE"}\n'
        "```\n"
    )
    assert json_object(text) is None


def test_first_result_cannot_precede_malformed_example() -> None:
    # S: without the last broken example's end limiting the first selection,
    # the old result becomes a plausible success instead of the later DONE.
    # The no-OLD control keeps the existing first selection for a candidate
    # after the example; first_json_object must not switch to another object.
    old_before_example = (
        '{"status": "OLD"}\n'
        "```jsonc\n"
        '{"enabled": true,}\n'
        "```\n"
        '{"status": "DONE"}\n'
    )
    assert first_json_object(old_before_example) is None
    later_result = (
        "```jsonc\n"
        '{"enabled": true,}\n'
        "```\n"
        '{"status": "DONE"}\n'
    )
    assert first_json_object(later_result) == {"status": "DONE"}
