"""usaturn/agent-workspace#494: review-records v1 の検査・照合・集約・取り出し（気付けない損害を防ぐ守りだけ）。"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "review_records.py"
SPEC = importlib.util.spec_from_file_location("review_records", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
review_records = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_records)

HEAD_1 = "25e76f6c513f8083cb229077cde193047be4cf24"
HEAD_2 = "a78ab78d6b329b647864d4c850dc03e612a0f057"
COMMIT_2 = "63c4d79d5298e2d709d6b76b78189f012914612d"
SHA256_HEAD = "0123456789abcdef" * 4
UNSYNCED = "000000000000"

Mutation = Callable[[dict[str, Any]], None]


def provenance(agent: str = "self", role: str = "decide") -> dict[str, Any]:
    return {
        "agent_id": agent,
        "role": role,
        "provider": "example-provider",
        "effort": "high",
        "session_id": "example-session",
        "cli_version": "1.2.3",
        "run_id": "example-run",
        "request_id": "example-request",
        "skills": [{"path": ".agents/skills/example/SKILL.md", "sha256": SHA256_HEAD}],
    }


def round_v2() -> dict[str, Any]:
    value = round_one()
    value["schema"] = "review-records/v2"
    value["planner"]["provenance"] = provenance()
    for entry in value["seats"]:
        entry["provenance"] = provenance(entry["model"], "find")
    return value


def test_v2_record_keeps_session_through_render_extract_and_fold() -> None:
    value = round_v2()
    block = review_records.render_block(value)
    restored = review_records.extract_record(block)
    assert restored == value
    state = review_records.fold([(123, restored)])
    assert state["rounds"][0]["planner"]["provenance"]["session_id"] == "example-session"
    assert state["rounds"][0]["seats"][0]["provenance"]["role"] == "find"


def seat(name: str, file_head: str, *, rerun: bool = True) -> dict[str, Any]:
    return {
        "review_file": name,
        "model": name,
        "runtime": "codex",
        "file_head": file_head,
        "mode": "Initial",
        "rerun": rerun,
        "merge_recommendation": "Approve",
    }


def decision(decision_id: str, state: str, *, change: str = "new", **extra: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "id": decision_id,
        "sources": [decision_id.split("/")[0]],
        "summary": f"{decision_id} の要約",
        "locations": ["tools/example.py:1"],
        "state": state,
        "change": change,
        "severity": "Medium",
        "pr_relation": "introduced",
        "reason": "理由",
    }
    if state == "skip":
        value["revisit_when"] = "新しい根拠が出たとき"
    if state == "unverified":
        value["unverified_reason"] = "足りない確認"
    value.update(extra)
    return value


def round_one() -> dict[str, Any]:
    return {
        "schema": "review-records/v1",
        "pr": {"repository": "usaturn/maatlog-poc", "number": 484},
        "round": 1,
        "reviewed_head": HEAD_1,
        "recorded_at": "2026-10-01T01:40:13Z",
        "planner": {"model": "claude-opus-5-5", "runtime": "claude-code", "agent_id": "claude-opus-5-5"},
        "seats": [seat("Grok-4.7", "25e76f6c513f"), seat("qwen3.8-max", "25e76f6c513f")],
        "decisions": [
            decision("Grok-4.7#M-1@25e76f6c513f", "fix"),
            decision("Grok-4.7#M-2@25e76f6c513f", "skip"),
            decision("Grok-4.7#L-1@25e76f6c513f/b", "skip", severity="Low"),
        ],
        "outcome": "fixes_pushed",
        "commit": HEAD_2,
    }


def round_two() -> dict[str, Any]:
    d1 = {
        "reproduced_by": "claude-opus-5-5#M-1@a78ab78d6b32",
        "usage_path": "herdr-pr-review <公開側 PR> --loop の検証",
        "result_kind": "stop",
    }
    return {
        "schema": "review-records/v1",
        "pr": {"repository": "usaturn/maatlog-poc", "number": 484},
        "round": 2,
        "reviewed_head": HEAD_2,
        "recorded_at": "2026-10-01T02:25:26Z",
        "planner": {"model": "claude-opus-5-5", "runtime": "claude-code", "agent_id": "claude-opus-5-5"},
        "seats": [seat("claude-opus-5-5", "a78ab78d6b32"), seat("qwen3.8-max", "25e76f6c513f", rerun=False)],
        "decisions": [
            decision("claude-opus-5-5#M-1@a78ab78d6b32", "fix", d1=d1),
            decision("Grok-4.7#M-1@25e76f6c513f", "resolved", change="changed", previous_state="fix"),
            decision("Grok-4.7#M-2@25e76f6c513f", "skip", change="inherited"),
        ],
        "outcome": "fixes_pushed",
        "commit": COMMIT_2,
    }


def problems_of(call: Callable[[], object]) -> tuple[str, ...]:
    try:
        call()
    except review_records.RecordError as error:
        return tuple(error.problems)
    raise AssertionError("RecordError was not raised")


def set_value(*path: object, value: object) -> Mutation:
    def mutate(record: dict[str, Any]) -> None:
        target: Any = record
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return mutate


def delete(*path: object) -> Mutation:
    def mutate(record: dict[str, Any]) -> None:
        target: Any = record
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]

    return mutate


def apply(*mutations: Mutation) -> Mutation:
    def mutate(record: dict[str, Any]) -> None:
        for mutation in mutations:
            mutation(record)

    return mutate


def duplicate_second_decision(record: dict[str, Any]) -> None:
    record["decisions"].append(copy.deepcopy(record["decisions"][1]))


def share_a_source_across_bases(record: dict[str, Any]) -> None:
    record["decisions"][1]["sources"].append("Grok-4.7#M-1@25e76f6c513f")


PLANNER_D1: dict[str, Any] = {
    "reproduced_by": "planner",
    "usage_path": "通常の入口・入力・環境",
    "result_kind": "stop",
}


REPRODUCTION: dict[str, Any] = {
    "commands": ["uv run --no-sync pytest tests/test_extension.py -q"],
    "place": "公開側のコピー（.venv なし）",
    "conditions": "uv run --project tools/devenv の中から実行した",
    "result": "ModuleNotFoundError: No module named 'sphinx'（終了コード 4）",
}


PLANNER_REPRODUCTION: dict[str, Any] = {**PLANNER_D1, "reproduction": REPRODUCTION}


INVALID_RECORDS = [
    pytest.param(
        set_value("planner", "agent_id", value="claude"),
        "planner.agent_id: must be claude-opus-5-5 (agent_id_for(planner.model))",
        id="agent-id-not-derived-from-model",
    ),
    pytest.param(
        set_value("reviewed_head", value="a78ab78"),
        "reviewed_head: must be a full lowercase commit hash",
        id="short-reviewed-head",
    ),
    pytest.param(set_value("seats", value=[]), "seats: must not be empty unless the round stopped", id="empty-seats"),
    pytest.param(
        set_value("seats", 1, "review_file", value="Grok-4.7"),
        "seats: must not repeat a review_file",
        id="repeated-review-file",
    ),
    pytest.param(
        set_value("seats", 0, "rerun", value=False),
        "seats[0].rerun: must be true exactly when file_head is the first 12 characters of reviewed_head",
        id="rerun-disagrees-with-heads",
    ),
    pytest.param(
        apply(
            set_value("seats", 0, "file_head", value=UNSYNCED),
            set_value("seats", 0, "rerun", value=False),
            set_value("seats", 1, "file_head", value=UNSYNCED),
            set_value("seats", 1, "rerun", value=False),
        ),
        "seats: at least one seat must have rerun true unless the round stopped",
        id="no-rerun-seat",
    ),
    pytest.param(
        set_value("decisions", 0, "sources", value=["Grok-4.7#M-9@25e76f6c513f"]),
        "decisions[0].sources: must contain the reference part of the decision id",
        id="sources-without-decision-id",
    ),
    pytest.param(
        set_value("decisions", 0, "sources", value=["Grok-4.7#M-1"]),
        "decisions[0].sources[0]: must be a finding reference <file>#<id>@<head>",
        id="reference-without-head",
    ),
    pytest.param(
        set_value("decisions", 0, "change", value="changed"),
        "decisions[0].previous_state: required when change is changed",
        id="changed-without-previous-state",
    ),
    pytest.param(
        apply(
            set_value("decisions", 0, "change", value="changed"),
            set_value("decisions", 0, "previous_state", value="fix"),
        ),
        "decisions[0].previous_state: must differ from state",
        id="previous-state-equal-to-state",
    ),
    pytest.param(
        apply(
            set_value("decisions", 1, "state", value="fix"),
            set_value("decisions", 1, "change", value="changed"),
            set_value("decisions", 1, "previous_state", value="skip"),
            delete("decisions", 1, "revisit_when"),
        ),
        "decisions[1].new_evidence: required when previous_state is skip",
        id="reopened-skip-without-new-evidence",
    ),
    pytest.param(
        delete("decisions", 1, "revisit_when"),
        "decisions[1].revisit_when: required when state is skip",
        id="skip-without-revisit-condition",
    ),
    pytest.param(
        set_value("decisions", 0, "severity", value=None),
        "decisions[0].severity: may be null only when every source is an Unverified candidate",
        id="null-severity-for-a-finding",
    ),
    pytest.param(
        set_value("decisions", 0, "reason", value="理由 <!-- x -->"),
        "decisions[0].reason: must not contain '<!--' or '-->'",
        id="comment-marker-in-text",
    ),
    pytest.param(
        apply(
            set_value("decisions", 0, "d1", value=PLANNER_REPRODUCTION),
            set_value("decisions", 0, "pr_relation", value="preexisting"),
        ),
        "decisions[0].d1: requires pr_relation introduced or surfaced",
        id="d1-on-a-preexisting-problem",
    ),
    pytest.param(
        set_value("decisions", 0, "d1", value=PLANNER_D1),
        "decisions[0].d1.reproduction: required when reproduced_by is planner or verifier",
        id="planner-d1-without-reproduction",
    ),
    pytest.param(
        set_value(
            "decisions",
            0,
            "d1",
            value={**PLANNER_D1, "reproduced_by": "Grok-4.7#M-2@25e76f6c513f"},
        ),
        "decisions[0].d1.reproduced_by: must be one of the decision's sources, planner, or verifier",
        id="d1-reproduced-by-another-finding",
    ),
    pytest.param(
        duplicate_second_decision,
        "decisions: duplicate decision id: Grok-4.7#M-2@25e76f6c513f",
        id="duplicate-decision-id",
    ),
    pytest.param(
        share_a_source_across_bases,
        "decisions: Grok-4.7#M-1@25e76f6c513f is in more than one decision "
        "(Grok-4.7#M-1@25e76f6c513f, Grok-4.7#M-2@25e76f6c513f); only its parts may share it",
        id="source-shared-across-bases",
    ),
    pytest.param(
        set_value("commit", value=HEAD_1), "commit: must differ from reviewed_head", id="commit-equal-to-reviewed"
    ),
    pytest.param(
        apply(
            set_value("decisions", 0, "state", value="skip"),
            set_value("decisions", 0, "revisit_when", value="条件"),
        ),
        "outcome: fixes_pushed requires at least one fix decision",
        id="pushed-without-fix",
    ),
    pytest.param(
        apply(
            set_value("outcome", value="awaiting_approval"),
            delete("commit"),
            set_value("decisions", 0, "state", value="skip"),
            set_value("decisions", 0, "revisit_when", value="条件"),
        ),
        "outcome: awaiting_approval requires a fix or hold decision",
        id="awaiting-approval-without-fix-or-hold",
    ),
    pytest.param(
        apply(set_value("outcome", value="no_fix_needed"), delete("commit")),
        "outcome: no_fix_needed must not leave fix, hold, or unverified decisions",
        id="no-fix-needed-with-fix",
    ),
]


def test_round_records_pass_validation() -> None:
    for record in (round_one(), round_two()):
        assert review_records.validate_record(record) == record


@pytest.mark.parametrize(("mutate", "expected"), INVALID_RECORDS)
def test_invalid_records_are_rejected(mutate: Mutation, expected: str) -> None:
    record = round_one()
    mutate(record)
    assert expected in problems_of(lambda: review_records.validate_record(record))


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("claude-opus-5-5", "claude-opus-5-5"),
        ("opencode/deepseek-v4-flash-free", "opencode-deepseek-v4-flash-free"),
    ],
)
def test_agent_id_for_follows_the_marker_rule(model: str, expected: str) -> None:
    assert review_records.agent_id_for(model) == expected


@pytest.mark.parametrize(
    "model",
    [
        "deepseek-v4.1-flash:1017[1m]",
        "provider/model@release",
        "日本語モデル[大]",
    ],
)
def test_extended_model_ids_use_a_separate_sha256_namespace(model: str) -> None:
    digest = hashlib.sha256(model.encode("utf-8")).hexdigest()
    agent_id = review_records.agent_id_for(model)
    assert agent_id == f"model--{digest}"
    # 生成した ID 自体をモデル名として旧変換した値とは一致しない
    assert review_records.agent_id_for(agent_id) != agent_id


def test_extended_model_ids_do_not_conflate_different_symbols() -> None:
    models = [
        "deepseek-v4.1-flash:1017[1m]",
        "deepseek-v4.1-flash:1017(1m)",
        "provider/model@release",
        "provider/model#release",
        "日本語モデル[大]",
        "日本語モデル（大）",
    ]
    assert len({review_records.agent_id_for(model) for model in models}) == len(models)


POC_PR: dict[str, Any] = {"repository": "usaturn/maatlog-poc", "number": 484}


def prior_after_round_one() -> dict[str, Any]:
    return review_records.fold([(101, review_records.validate_record(round_one()))])


def test_fold_keeps_the_latest_state_merged_sources_and_planner_models() -> None:
    first = review_records.validate_record(round_one())
    second_record = round_two()
    second_record["planner"] = {"model": "gpt-6-sol", "runtime": "codex", "agent_id": "gpt-6-sol"}
    second_record["decisions"][2]["sources"] = ["Grok-4.7#M-2@25e76f6c513f", "SWE-2-Max#M-3@a78ab78d6b32"]
    second = review_records.validate_record(second_record)
    state = review_records.fold([(202, second), (101, first)])
    decisions = {entry["id"]: entry for entry in state["decisions"]}
    assert [entry["id"] for entry in state["decisions"]] == [
        "Grok-4.7#M-1@25e76f6c513f",
        "Grok-4.7#M-2@25e76f6c513f",
        "Grok-4.7#L-1@25e76f6c513f/b",
        "claude-opus-5-5#M-1@a78ab78d6b32",
    ]
    assert decisions["Grok-4.7#M-1@25e76f6c513f"]["state"] == "resolved"
    assert decisions["Grok-4.7#M-2@25e76f6c513f"]["sources"] == [
        "Grok-4.7#M-2@25e76f6c513f",
        "SWE-2-Max#M-3@a78ab78d6b32",
    ]
    history = decisions["Grok-4.7#M-2@25e76f6c513f"]["history"]
    assert [(item["planner_model"], item["outcome"]) for item in history] == [
        ("claude-opus-5-5", "fixes_pushed"),
        ("gpt-6-sol", "fixes_pushed"),
    ]
    assert decisions["Grok-4.7#L-1@25e76f6c513f/b"]["history"][0]["comment_id"] == 101
    assert [(entry["round"], entry["comment_id"], entry["commit"]) for entry in state["rounds"]] == [
        (1, 101, HEAD_2),
        (2, 202, COMMIT_2),
    ]
    assert state["pr"] == POC_PR


def test_fold_orders_one_round_by_time_and_then_comment_id() -> None:
    early = review_records.validate_record(round_one())
    late_record = round_one()
    late_record["recorded_at"] = "2026-10-01T01:50:00Z"
    late_record["decisions"][1]["state"] = "hold"
    del late_record["decisions"][1]["revisit_when"]
    late = review_records.validate_record(late_record)
    by_time = review_records.fold([(300, early), (100, late)])
    assert by_time["decisions"][1]["state"] == "hold"
    same_time = review_records.fold([(300, early), (100, review_records.validate_record(round_one()))])
    assert [entry["comment_id"] for entry in same_time["rounds"]] == [100, 300]


def test_fold_keeps_split_decisions_apart() -> None:
    record = round_one()
    record["decisions"].append(decision("Grok-4.7#L-1@25e76f6c513f/a", "resolved", severity="Low"))
    state = review_records.fold([(101, review_records.validate_record(record))])
    decisions = {entry["id"]: entry for entry in state["decisions"]}
    assert decisions["Grok-4.7#L-1@25e76f6c513f/a"]["state"] == "resolved"
    assert decisions["Grok-4.7#L-1@25e76f6c513f/b"]["state"] == "skip"
    assert decisions["Grok-4.7#L-1@25e76f6c513f/a"]["sources"] == ["Grok-4.7#L-1@25e76f6c513f"]


def test_fold_rejects_records_of_another_pull_request() -> None:
    other = round_two()
    other["pr"] = {"repository": "usaturn/maatlog", "number": 484}
    records = [
        (101, review_records.validate_record(round_one())),
        (202, review_records.validate_record(other)),
    ]
    assert problems_of(lambda: review_records.fold(records)) == ("comment 202: belongs to a different pull request",)


def test_check_against_accepts_the_next_round() -> None:
    review_records.check_against(review_records.validate_record(round_two()), prior_after_round_one())


INVALID_NEXT_ROUNDS = [
    pytest.param(
        set_value("decisions", 2, "change", value="new"),
        "decisions[2].change: Grok-4.7#M-2@25e76f6c513f is already recorded; use inherited or changed",
        id="new-but-recorded",
    ),
    pytest.param(
        apply(set_value("decisions", 2, "state", value="fix"), delete("decisions", 2, "revisit_when")),
        "decisions[2].state: an inherited decision must keep the earlier state skip",
        id="inherited-with-another-state",
    ),
    pytest.param(
        set_value("decisions", 1, "previous_state", value="hold"),
        "decisions[1].previous_state: must be the earlier state fix",
        id="changed-from-the-wrong-state",
    ),
    pytest.param(set_value("round", value=3), "round: must be 2", id="skipped-round-number"),
    pytest.param(
        set_value("pr", "number", value=485),
        "pr: must match the earlier records of this pull request",
        id="another-pull-request",
    ),
    pytest.param(
        delete("decisions", 1),
        "decisions: must list every decision whose earlier state is fix: Grok-4.7#M-1@25e76f6c513f",
        id="earlier-fix-omitted",
    ),
    pytest.param(
        set_value(
            "decisions",
            2,
            value=decision(
                "qwen3.8-max#M-5@a78ab78d6b32",
                "fix",
                sources=["qwen3.8-max#M-5@a78ab78d6b32", "Grok-4.7#M-2@25e76f6c513f"],
            ),
        ),
        "decisions[2].sources: Grok-4.7#M-2@25e76f6c513f already belongs to Grok-4.7#M-2@25e76f6c513f",
        id="skip-reference-moved-to-a-new-decision",
    ),
]


@pytest.mark.parametrize(("mutate", "expected"), INVALID_NEXT_ROUNDS)
def test_check_against_rejects_inconsistent_rounds(mutate: Mutation, expected: str) -> None:
    record = round_two()
    mutate(record)
    checked = review_records.validate_record(record)
    assert expected in problems_of(lambda: review_records.check_against(checked, prior_after_round_one()))


def test_check_against_keeps_one_planner_per_round() -> None:
    prior = review_records.fold(
        [
            (101, review_records.validate_record(round_one())),
            (202, review_records.validate_record(round_two())),
        ]
    )
    record = round_two()
    record["planner"] = {"model": "gpt-6-sol", "runtime": "codex", "agent_id": "gpt-6-sol"}
    checked = review_records.validate_record(record)
    assert "round: round 2 is already recorded by claude-opus-5-5" in problems_of(
        lambda: review_records.check_against(checked, prior)
    )


def test_check_against_refuses_to_update_a_round_after_a_later_one() -> None:
    prior = review_records.fold([(202, review_records.validate_record(round_two()))])
    checked = review_records.validate_record(round_one())
    assert "round: round 1 can no longer be updated because round 2 exists" in problems_of(
        lambda: review_records.check_against(checked, prior)
    )


def test_check_against_rejects_finishing_with_an_earlier_hold() -> None:
    first = round_one()
    first["decisions"][1]["state"] = "hold"
    del first["decisions"][1]["revisit_when"]
    prior = review_records.fold([(101, review_records.validate_record(first))])
    record = round_two()
    record["decisions"] = [decision("Grok-4.7#M-1@25e76f6c513f", "resolved", change="changed", previous_state="fix")]
    record["outcome"] = "no_fix_needed"
    del record["commit"]
    checked = review_records.validate_record(record)
    assert "outcome: no_fix_needed leaves pending decisions: Grok-4.7#M-2@25e76f6c513f" in problems_of(
        lambda: review_records.check_against(checked, prior)
    )


def test_check_against_keeps_d1_of_an_inherited_fix() -> None:
    first = round_one()
    first["decisions"][0]["d1"] = PLANNER_REPRODUCTION
    prior = review_records.fold([(101, review_records.validate_record(first))])
    record = round_two()
    record["decisions"][1] = decision("Grok-4.7#M-1@25e76f6c513f", "fix", change="inherited")
    checked = review_records.validate_record(record)
    assert "decisions[1].d1: an inherited decision must keep the earlier d1" in problems_of(
        lambda: review_records.check_against(checked, prior)
    )


SPLIT_BASE = "Grok-4.7#L-1@25e76f6c513f"


ANOTHER_SEAT_FINDING = "qwen3.8-max#L-2@25e76f6c513f"


def prior_with_a_part_holding_another_finding() -> dict[str, Any]:
    first = round_one()
    first["decisions"].append(
        decision(f"{SPLIT_BASE}/a", "skip", severity="Low", sources=[SPLIT_BASE, ANOTHER_SEAT_FINDING])
    )
    return review_records.fold([(101, review_records.validate_record(first))])


def test_check_against_keeps_a_reference_with_the_part_that_holds_it() -> None:
    record = round_two()
    record["decisions"].append(
        decision(
            f"{SPLIT_BASE}/b", "skip", change="inherited", severity="Low", sources=[SPLIT_BASE, ANOTHER_SEAT_FINDING]
        )
    )
    checked = review_records.validate_record(record)
    prior = prior_with_a_part_holding_another_finding()
    assert (
        "decisions[3].sources: qwen3.8-max#L-2@25e76f6c513f already belongs to Grok-4.7#L-1@25e76f6c513f/a"
        in problems_of(lambda: review_records.check_against(checked, prior))
    )


@pytest.mark.parametrize("category", ["permission"])
def test_stopped_round_preserves_category_and_pending_decisions(category: str) -> None:
    record = round_one()
    del record["commit"]
    record.update(outcome="stopped", stop_reason=f"{category}: 認証を更新できず push を完了できない")
    record["seats"] = []
    checked = review_records.validate_record(record)
    extracted = review_records.extract_record(review_records.render_block(checked))
    assert extracted == checked
    assert review_records.fold([(1, checked)])["rounds"][0]["stop_reason"] == checked["stop_reason"]


@pytest.mark.parametrize("reason", [None, "", "permission:", "external:   ", "iteration_limit: 1", "確認待ち"])
def test_stopped_round_requires_a_concrete_allowed_category(reason: object) -> None:
    record = round_one()
    del record["commit"]
    record["outcome"] = "stopped"
    if reason is not None:
        record["stop_reason"] = reason
    assert any("stop_reason" in problem for problem in problems_of(lambda: review_records.validate_record(record)))


HUMAN_PART = "\n".join(["## review-fix-planning（claude-opus-5-5）", "", "### レビュー状況", "", "- 分類: 例"])


LOOP_COMMENT = "<!-- review-fix-planning:agent:maatlog-pr-review-loop -->\nPR review fix loop: round 1"


def status_body(record: dict[str, Any]) -> str:
    return review_records.compose_comment(record, HUMAN_PART)


@pytest.mark.parametrize("model", ["deepseek-v4.1-flash:1017[1m]", "日本語モデル[大]"])
def test_extended_model_name_survives_compose_extract_and_fold(model: str) -> None:
    value = round_two()
    value["planner"] = {"model": model, "runtime": "pi", "agent_id": review_records.agent_id_for(model)}
    checked = review_records.validate_record(value)
    restored = review_records.extract_record(status_body(checked))
    assert restored == checked
    state = review_records.fold([(303, restored)])
    assert state["rounds"][0]["planner"]["model"] == model
    assert state["decisions"][0]["history"][0]["planner_model"] == model


def comment(comment_id: int, body: str, *, association: str = "OWNER") -> dict[str, Any]:
    return {"id": comment_id, "body": body, "author": "usaturn", "author_association": association}


def api_comment(comment_id: int, body: str, *, association: str = "OWNER") -> dict[str, Any]:
    return {"id": comment_id, "body": body, "user": {"login": "usaturn"}, "author_association": association}


def test_records_with_unicode_line_separators_round_trip() -> None:
    record = round_one()
    record["decisions"][1]["reason"] = "段落 1 段落 2 段落 3"
    checked = review_records.validate_record(record)
    assert review_records.extract_record(review_records.render_block(checked)) == checked


def test_comments_from_api_accepts_slurped_pages_and_flat_arrays() -> None:
    raw = {**api_comment(1, "a"), "html_url": "https://github.com/usaturn/maatlog-poc/pull/484#issuecomment-1"}
    expected = [comment(1, "a")]
    assert review_records.comments_from_api([[raw]]) == expected
    assert review_records.comments_from_api([raw]) == expected
    assert review_records.comments_from_api([[]]) == []
    assert review_records.comments_from_api([]) == []


def test_collect_records_reads_trusted_round_status_comments_only() -> None:
    first = review_records.validate_record(round_one())
    second = review_records.validate_record(round_two())
    forged = round_two()
    forged["decisions"][0] = decision("claude-opus-5-5#M-1@a78ab78d6b32", "skip")
    forged["outcome"] = "no_fix_needed"
    del forged["commit"]
    comments = [
        comment(101, status_body(first)),
        comment(150, "普通のコメント"),
        comment(160, f"文書の例を引用する: {review_records.BLOCK_START}"),
        comment(170, LOOP_COMMENT),
        comment(180, status_body(review_records.validate_record(forged)), association="NONE"),
        comment(202, status_body(second)),
    ]
    records, ignored = review_records.collect_records(comments)
    assert records == [(101, first), (202, second)]
    assert ignored == [
        {
            "comment_id": 160,
            "author": "usaturn",
            "author_association": "OWNER",
            "reason": "has a records block but is not a round status comment",
        },
        {
            "comment_id": 180,
            "author": "usaturn",
            "author_association": "NONE",
            "reason": "the author is not trusted",
        },
    ]
    assert review_records.collect_records(comments, exclude_comment_ids=[202])[0] == [(101, first)]


@pytest.mark.parametrize("association", ["CONTRIBUTOR"])
def test_collect_records_accepts_explicit_trusted_login(association: str) -> None:
    first = review_records.validate_record(round_one())
    comments = [comment(101, status_body(first), association=association)]
    records, ignored = review_records.collect_records(comments, trusted_login="usaturn")
    assert records == [(101, first)]
    assert ignored == []


@pytest.mark.parametrize(
    ("author", "trusted_login"),
    [("someone-else", "usaturn"), (None, "usaturn"), ("", "")],
)
def test_collect_records_does_not_trust_other_or_empty_logins(author: str | None, trusted_login: str) -> None:
    # A valid record isolates the trust boundary from schema/marker validation.
    first = review_records.validate_record(round_one())
    candidate = comment(101, status_body(first), association="CONTRIBUTOR")
    if author is None:
        del candidate["author"]
    else:
        candidate["author"] = author
    records, ignored = review_records.collect_records([candidate], trusted_login=trusted_login)
    assert records == []
    assert [entry["comment_id"] for entry in ignored] == [101]
    assert ignored[0]["reason"] == "the author is not trusted"


@pytest.mark.parametrize("association", ["OWNER"])
def test_trusted_login_keeps_association_trust(association: str) -> None:
    first = review_records.validate_record(round_one())
    records, ignored = review_records.collect_records(
        [comment(101, status_body(first), association=association)], trusted_login="someone-else"
    )
    assert records == [(101, first)]
    assert ignored == []


def test_collect_records_names_every_broken_comment() -> None:
    marker_lines = "<!-- review-fix-planning:agent:claude-opus-5-5 -->\n" + review_records.round_marker(1, HEAD_1)
    broken = status_body(review_records.validate_record(round_one())).replace('"round": 1,', '"round": 0,')
    comments = [
        comment(7, broken),
        comment(8, marker_lines + "\n" + review_records.BLOCK_START),
        comment(9, marker_lines + "\n本文だけで、記録のブロックが無い"),
    ]
    problems = problems_of(lambda: review_records.collect_records(comments))
    assert "comment 7: round: must be an integer of 1 or more" in problems
    assert "comment 8: body: must contain exactly one review-records block" in problems
    assert "comment 9: body: a round status comment must contain a records block" in problems


def test_collect_records_rejects_markers_that_disagree_with_the_record() -> None:
    body = status_body(review_records.validate_record(round_one()))
    lines = body.split("\n")
    lines[0] = "<!-- review-fix-planning:agent:gpt-6-sol -->"
    lines[1] = review_records.round_marker(3, HEAD_1)
    problems = problems_of(lambda: review_records.collect_records([comment(7, "\n".join(lines))]))
    assert problems == (
        "comment 7: body: the agent marker does not match planner.agent_id",
        "comment 7: body: the round marker does not match round and reviewed_head",
    )


def test_read_state_lists_ignored_comments_and_checks_the_pull_request() -> None:
    first = review_records.validate_record(round_one())
    comments = [comment(101, status_body(first)), comment(180, status_body(first), association="CONTRIBUTOR")]
    state = review_records.read_state(comments, expected_pr=POC_PR)
    assert [entry["round"] for entry in state["rounds"]] == [1]
    assert [entry["comment_id"] for entry in state["ignored_comments"]] == [180]
    other_pr = {"repository": "usaturn/maatlog", "number": 484}
    assert problems_of(lambda: review_records.read_state(comments, expected_pr=other_pr)) == (
        "comment 101: belongs to a different pull request",
    )


def test_updating_the_same_round_excludes_its_own_comment() -> None:
    first = review_records.validate_record(round_one())
    second = review_records.validate_record(round_two())
    comments = [comment(101, status_body(first)), comment(202, status_body(second))]
    review_records.check_against(second, review_records.read_state(comments, exclude_comment_ids=[202]))
    with_own = review_records.read_state(comments)
    assert "round: round 2 is already recorded by claude-opus-5-5" in problems_of(
        lambda: review_records.check_against(second, with_own)
    )


def test_collect_records_lists_a_status_comment_with_a_line_added_on_top() -> None:
    body = "追記: 人が先頭に足した行\n" + status_body(review_records.validate_record(round_one()))
    records, ignored = review_records.collect_records([comment(7, body)])
    assert records == []
    assert [entry["reason"] for entry in ignored] == ["has a records block but is not a round status comment"]


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def test_cli_fold_prints_the_current_state(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    body = status_body(review_records.validate_record(round_one()))
    pages = [[api_comment(101, body), api_comment(150, "普通のコメント")]]
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(pages, ensure_ascii=False)))
    assert review_records.main(["fold", "--repo", "usaturn/maatlog-poc", "--pr", "484"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in state["decisions"]] == [
        "Grok-4.7#M-1@25e76f6c513f",
        "Grok-4.7#M-2@25e76f6c513f",
        "Grok-4.7#L-1@25e76f6c513f/b",
    ]
    assert state["rounds"][0]["comment_id"] == 101
    assert state["ignored_comments"] == []


def test_cli_fold_reports_records_of_another_pull_request(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    body = status_body(review_records.validate_record(round_one()))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps([[api_comment(101, body)]], ensure_ascii=False)))
    assert review_records.main(["fold", "--repo", "usaturn/maatlog", "--pr", "484"]) == 65
    assert "comment 101: belongs to a different pull request" in capsys.readouterr().err


def test_cli_fold_exits_65_on_a_broken_record(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    markers = "<!-- review-fix-planning:agent:claude-opus-5-5 -->\n" + review_records.round_marker(1, HEAD_1)
    body = markers + "\n" + review_records.BLOCK_START
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps([api_comment(8, body)])))
    assert review_records.main(["fold"]) == 65
    assert "comment 8: body: must contain exactly one review-records block" in capsys.readouterr().err


@pytest.mark.parametrize(("trusted_login", "expected_rounds"), [(None, []), ("usaturn", [1])])
def test_cli_fold_uses_explicit_trusted_login(
    trusted_login: str | None,
    expected_rounds: list[int],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body = status_body(review_records.validate_record(round_one()))
    payload = [[api_comment(101, body, association="CONTRIBUTOR")]]
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    args = ["fold", "--repo", "usaturn/maatlog-poc", "--pr", "484"]
    if trusted_login is not None:
        args.extend(["--trusted-login", trusted_login])
    assert review_records.main(args) == 0
    state = json.loads(capsys.readouterr().out)
    assert [entry["round"] for entry in state["rounds"]] == expected_rounds
    assert [entry["comment_id"] for entry in state["ignored_comments"]] == ([] if expected_rounds else [101])


def test_cli_validate_uses_explicit_trusted_login(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    body = status_body(review_records.validate_record(round_one()))
    comments = write_json(tmp_path / "comments.json", [[api_comment(101, body, association="CONTRIBUTOR")]])
    record_file = write_json(tmp_path / "round-2.json", round_two())
    args = ["validate", "--record-file", str(record_file), "--comments-file", str(comments)]
    assert review_records.main(args) == 65
    assert "round: must be 1" in capsys.readouterr().err
    assert review_records.main([*args, "--trusted-login", "usaturn"]) == 0
    assert capsys.readouterr().err == ""


def test_cli_validate_checks_the_record_against_earlier_comments(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first_body = status_body(review_records.validate_record(round_one()))
    second_body = status_body(review_records.validate_record(round_two()))
    comments = write_json(tmp_path / "comments.json", [[api_comment(101, first_body)]])
    with_own = write_json(tmp_path / "with-own.json", [[api_comment(101, first_body), api_comment(202, second_body)]])
    record_file = write_json(tmp_path / "round-2.json", round_two())
    assert review_records.main(["validate", "--record-file", str(record_file)]) == 0
    with_comments = ["validate", "--record-file", str(record_file), "--comments-file", str(comments)]
    assert review_records.main(with_comments) == 0
    update = ["validate", "--record-file", str(record_file), "--comments-file", str(with_own)]
    assert review_records.main([*update, "--exclude-comment", "202"]) == 0
    assert review_records.main(update) == 65
    assert "round: round 2 is already recorded by claude-opus-5-5" in capsys.readouterr().err
    broken = round_two()
    del broken["decisions"][1]
    broken_file = write_json(tmp_path / "broken.json", broken)
    arguments = ["validate", "--record-file", str(broken_file), "--comments-file", str(comments)]
    assert review_records.main(arguments) == 65
    expected = "decisions: must list every decision whose earlier state is fix: Grok-4.7#M-1@25e76f6c513f"
    assert expected in capsys.readouterr().err
