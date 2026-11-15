"""review-fix-planning の保存点から review-eval の収集へ記録を渡す（Issue #357）。"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tools.review_eval import capture, shim
from tools.review_eval.store import Store
from tools.review_eval.tests.support import write_collection_config

ROOT = Path(__file__).resolve().parents[4]
FINALIZE = ROOT / ".agents/skills/review-fix-planning/scripts/finalize.py"
RUN_ROLES = ROOT / ".agents/skills/review-fix-planning/scripts/run_roles.py"
UPSERT = ROOT / ".agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"
REPOSITORY = "usaturn/create-reso-world"
PR = 900
HEAD = "a" * 40
SPEC = "b" * 40


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


finalize = _load("planning_collection_finalize", FINALIZE)
run_roles = _load("planning_collection_roles", RUN_ROLES)
upsert_pr_comment = _load("planning_collection_upsert", UPSERT)


@pytest.fixture(autouse=True)
def isolated_collection_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """利用者の設定・モデル本文を読まず、runner の子の判定もテストごとに決める。"""
    home = tmp_path / "home"
    home.mkdir()
    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv("AGENT_RUNNER_DEPTH", raising=False)


def review_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "reviews" / REPOSITORY / f"#{PR}-feature-demo"
    directory.mkdir(parents=True)
    return directory


def initialized_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Store:
    store = Store.init(tmp_path / "store")
    config = write_collection_config(
        tmp_path / "review-eval.toml",
        store=store.root,
        workspace_root=tmp_path,
        repos=[REPOSITORY],
    )
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", str(config))
    return store


def observed_paths(store: Store) -> list[str]:
    return [observation.path for observation in store.observations(REPOSITORY, PR)]


def planning_record(*, round_number: int | None = 2, head: str | None = HEAD) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema": "review-records/v2",
        "pr": {"repository": REPOSITORY, "number": PR},
        "reviewed_head": head,
        "recorded_at": "2026-11-15T06:00:00Z",
        "planner": {"model": "fixture", "runtime": "pi", "agent_id": "fixture"},
        "seats": [],
        "decisions": [],
        "outcome": "no_fix_needed",
        "note": "日本語の記録\n二行目の本文です。",
        "provenance": {
            "agent_id": "fixture",
            "role": "decide",
            "provider": "unknown",
            "effort": "unknown",
            "session_id": "unknown",
            "cli_version": "unknown",
            "run_id": "unknown",
            "request_id": "unknown",
            "skills": [],
        },
    }
    if round_number is not None:
        record["round"] = round_number
    if head is None:
        del record["reviewed_head"]
    return record


def write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("spec_commit", [None, SPEC], ids=["posted", "spec-commit"])
def test_finalize_result_copied_as_virtual_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spec_commit: str | None
) -> None:
    store = initialized_store(tmp_path, monkeypatch)
    record = planning_record()
    record_file = write_json(tmp_path / "record.json", record)
    result = {
        "outcome": "no_fix_needed",
        "merged": True,
        "issues": [901],
        "comment": {"comment_id": 99},
        "note": "最終化の結果\n日本語の二行目です。",
    }
    result_file = write_json(tmp_path / "result.json", result)

    finalize.collect_result(
        record,
        record_file,
        result_file,
        result,
        spec_commit=spec_commit,
    )

    expected = {f"@finalize/{HEAD[:12]}/result.json"}
    if spec_commit is None:
        expected.add("@pr-comment/round-2/record.json")
    assert set(observed_paths(store)) == expected


def test_finalize_skips_virtual_record_without_round(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = initialized_store(tmp_path, monkeypatch)
    record = planning_record(round_number=None)
    record_file = write_json(tmp_path / "record.json", record)
    result = {"outcome": "no_fix_needed", "comment": {"comment_id": 99}}
    result_file = write_json(tmp_path / "result.json", result)

    finalize.collect_result(record, record_file, result_file, result, spec_commit=None)

    assert observed_paths(store) == [f"@finalize/{HEAD[:12]}/result.json"]


def test_run_roles_finally_collects_planning_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = initialized_store(tmp_path, monkeypatch)
    verified = review_dir(tmp_path) / "verified"
    planning = write_json(
        verified / f"{HEAD[:12]}.planning.json",
        planning_record(round_number=None),
    )

    run_roles.collect_review_dir(planning, "self-review")
    assert observed_paths(store) == [f"verified/{HEAD[:12]}.planning.json"]

    run_roles.collect_review_dir(None, "self-review")
    assert observed_paths(store) == [f"verified/{HEAD[:12]}.planning.json"]

    calls: list[tuple[Path | None, str]] = []

    def fake_collect_review_dir(planning_file: Path | None, phase: str) -> None:
        calls.append((planning_file, phase))

    monkeypatch.setattr(run_roles, "collect_review_dir", fake_collect_review_dir)
    code = run_roles.main(
        [
            "--phase",
            "self-review",
            "--request",
            str(tmp_path / "request.json"),
            "--output-dir",
            str(tmp_path / "run"),
            "--planning-file",
            str(planning),
            "--assign",
            "bogus=fixture",
        ]
    )
    assert code == 2
    assert calls == [(planning, "self-review")]


def test_upsert_hooks_absolute_record_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    record = planning_record()
    record_file = write_json(tmp_path / "records" / "round.json", record)
    (tmp_path / "review-eval.toml").write_text("enabled = false\n", encoding="utf-8")
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "review-eval.toml")
    calls: list[dict[str, Any]] = []

    def fake_run_hook(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(shim, "run_hook", fake_run_hook)

    upsert_pr_comment.collect_round_record(
        REPOSITORY,
        PR,
        Path("records/round.json"),
        {"action": "created", "comment_id": 99},
    )

    assert len(calls) == 1
    call = calls[0]
    assert call["route"] == "review-fix-planning"
    assert call["event"] == "post"
    assert call["records"] == [("@pr-comment/round-2/record.json", record_file.resolve())]
    assert call["repository"] == REPOSITORY
    assert call["pr"] == PR
    assert call["tool_root"] == ROOT
    assert Path(os.environ["REVIEW_EVAL_CONFIG"]).is_absolute()
    assert Path(os.environ["REVIEW_EVAL_CONFIG"]) == (tmp_path / "review-eval.toml").resolve()

    upsert_pr_comment.collect_round_record(
        REPOSITORY,
        PR,
        None,
        {"action": "created", "comment_id": 99},
    )
    assert len(calls) == 1


def test_save_points_call_collect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = review_dir(tmp_path)
    verified = directory / "verified"
    planning = write_json(
        verified / f"{HEAD[:12]}.planning.json",
        planning_record(round_number=None),
    )
    record = planning_record()
    record_file = write_json(tmp_path / "record.json", record)
    body_file = tmp_path / "body.md"
    body_file.write_text("## 状況\n\n日本語の本文です。\n", encoding="utf-8")
    checks_file = write_json(
        tmp_path / "checks.json",
        {"head": HEAD, "base": "c" * 40, "commands": [{"argv": ["true"], "exit_code": 0}]},
    )
    result_file = tmp_path / "result.json"
    monkeypatch.setattr(
        finalize,
        "finalize",
        lambda *_args, **_kwargs: {
            "outcome": "no_fix_needed",
            "merged": True,
            "issues": [901],
            "comment": {"comment_id": 99},
        },
    )
    collect_calls: list[dict[str, Any]] = []

    def fake_collect(**kwargs: Any) -> None:
        collect_calls.append(kwargs)

    monkeypatch.setattr(capture, "collect", fake_collect)

    assert (
        finalize.main(
            [
                "--record-file",
                str(record_file),
                "--body-file",
                str(body_file),
                "--checks-file",
                str(checks_file),
                "--result-file",
                str(result_file),
            ]
        )
        == 0
    )

    artifact_dir = tmp_path / "roles-run"
    artifact_dir.mkdir()
    write_json(artifact_dir / "roles.json", {"self_prompts": [], "review_changes": []})
    batch = SimpleNamespace(
        artifact_dir=artifact_dir,
        state="success",
        outside_changes=[],
        unprotected_changes=[],
        checkout_audit=[],
        results=[],
    )
    request_file = write_json(tmp_path / "request.json", {})
    monkeypatch.setattr(run_roles, "load_config", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(run_roles, "run", lambda *_args, **_kwargs: batch)

    assert (
        run_roles.main(
            [
                "--phase",
                "implement",
                "--request",
                str(request_file),
                "--output-dir",
                str(tmp_path / "run"),
                "--planning-file",
                str(planning),
            ]
        )
        == 0
    )

    hook_calls: list[dict[str, Any]] = []

    def fake_run_hook(**kwargs: Any) -> None:
        hook_calls.append(kwargs)

    monkeypatch.setattr(shim, "run_hook", fake_run_hook)
    monkeypatch.setattr(
        upsert_pr_comment,
        "upsert",
        lambda *_args, **_kwargs: {"action": "created", "comment_id": 99, "url": ""},
    )

    assert (
        upsert_pr_comment.main(
            [
                "--pr",
                str(PR),
                "--repo",
                REPOSITORY,
                "--model-name",
                "fixture",
                "--body-file",
                str(body_file),
                "--records-file",
                str(record_file),
            ]
        )
        == 0
    )

    assert [(call["route"], call["event"]) for call in collect_calls] == [
        ("review-fix-planning", "finalize"),
        ("review-fix-planning", "run_roles"),
    ]
    assert collect_calls[1]["review_dir"] == directory
    assert len(hook_calls) == 1
    assert hook_calls[0]["route"] == "review-fix-planning"
    assert hook_calls[0]["event"] == "post"
    assert hook_calls[0]["pr"] == PR


def test_planning_disabled_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = initialized_store(tmp_path, monkeypatch)
    verified = review_dir(tmp_path) / "verified"
    planning = write_json(
        verified / f"{HEAD[:12]}.planning.json",
        planning_record(round_number=None),
    )
    record = planning_record()
    record_file = write_json(tmp_path / "record.json", record)
    result = {"outcome": "no_fix_needed", "comment": {"comment_id": 99}}
    result_file = write_json(tmp_path / "result.json", result)
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")

    finalize.collect_result(record, record_file, result_file, result, spec_commit=None)
    run_roles.collect_review_dir(planning, "self-review")

    assert observed_paths(store) == []
