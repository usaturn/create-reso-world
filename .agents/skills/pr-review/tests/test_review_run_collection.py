"""review_run.py の保存点から review-eval の収集へ記録を渡す（Issue #357）。"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tools.review_eval import capture
from tools.review_eval.store import Store
from tools.review_eval.tests.support import write_collection_config

SCRIPT = Path(__file__).parents[1] / "scripts" / "review_run.py"
SPEC = importlib.util.spec_from_file_location("review_run_collection", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
review_run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_run)

REPOSITORY = "usaturn/create-reso-world"
PR = 900
HEAD = "a" * 40
BASE = "b" * 40


@pytest.fixture(autouse=True)
def isolated_collection_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """利用者の設定・モデル本文を読まず、runner の子の判定もテストごとに決める。"""
    home = tmp_path / "home"
    home.mkdir()
    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv("AGENT_RUNNER_DEPTH", raising=False)


def review_dir(tmp_path: Path, name: str = "#900-feature-demo") -> Path:
    directory = tmp_path / "reviews" / "usaturn" / "create-reso-world" / name
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


def write_run(directory: Path, name: str = "20261115-observed-model.json") -> Path:
    path = directory / "runs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "review-findings/v2",
                "kind": "review_run",
                "pr": {"repository": REPOSITORY, "number": PR},
                "reviewed_head": HEAD,
                "base": BASE,
                "status": "success",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_findings(directory: Path) -> Path:
    path = directory / "findings" / f"m-{HEAD[:12]}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "review-findings/v2",
                "kind": "candidates",
                "source": "reviewer",
                "pr": {"repository": REPOSITORY, "number": PR},
                "reviewed_head": HEAD,
                "base": BASE,
                "findings": [],
                "unverified_candidates": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_complete_copies_saved_outputs_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = review_dir(tmp_path)
    store = initialized_store(tmp_path, monkeypatch)
    review = directory / "observed-model.md"
    review.write_text(
        "# レビュー\n\n指摘はありません。\n二行目の本文です。\n", encoding="utf-8"
    )
    findings = write_findings(directory)
    run = write_run(directory)

    review_run.collect_outputs(
        "complete",
        tmp_path,
        None,
        {
            "status": "success",
            "run_record": str(run),
            "review_file": str(review),
            "findings_file": str(findings),
        },
    )

    assert set(observed_paths(store)) == {
        "observed-model.md",
        f"findings/m-{HEAD[:12]}.json",
        "runs/20261115-observed-model.json",
    }


def test_disabled_writes_nothing_and_main_output_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    directory = review_dir(tmp_path)
    store = initialized_store(tmp_path, monkeypatch)
    run = write_run(directory)
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")
    result_file = tmp_path / "result.json"
    result_file.write_text("{}", encoding="utf-8")

    def fake_attach(path: Path) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": "success",
            "result_file": str(path),
            "attached": [str(run)],
            "unchanged": [],
        }

    monkeypatch.setattr(review_run, "attach_runner", fake_attach)
    argv = ["attach-runner", "--result", str(result_file)]
    first_code = review_run.main(argv)
    first_output = capsys.readouterr().out

    def broken_collect(**_kwargs: Any) -> None:
        raise RuntimeError("収集に失敗した")

    monkeypatch.setattr(capture, "collect", broken_collect)
    second_code = review_run.main(argv)
    second_output = capsys.readouterr().out

    assert (first_code, first_output) == (second_code, second_output)
    assert first_code == 0
    assert observed_paths(store) == []


def test_attach_runner_shares_deadline_and_skips_after_expiry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = initialized_store(tmp_path, monkeypatch)
    first_directory = review_dir(tmp_path, "#900-feature-demo")
    second_directory = review_dir(tmp_path, "#900-second-demo")
    first_run = write_run(first_directory, "first.json")
    second_run = write_run(second_directory, "second.json")

    clock = [time.monotonic()]

    def monotonic() -> float:
        return clock[0]

    monkeypatch.setattr(review_run, "time", SimpleNamespace(monotonic=monotonic))
    calls: list[dict[str, Any]] = []
    real_collect = capture.collect

    def advancing_collect(**kwargs: Any) -> None:
        calls.append(kwargs)
        real_collect(**kwargs)
        clock[0] += 31.0

    monkeypatch.setattr(capture, "collect", advancing_collect)
    started = clock[0]

    review_run.collect_outputs(
        "attach-runner",
        tmp_path,
        None,
        {
            "status": "success",
            "attached": [str(first_run), str(second_run)],
            "unchanged": [],
        },
    )

    assert observed_paths(store) == ["runs/first.json"]
    assert len(calls) == 1
    assert calls[0]["review_dir"] == first_directory
    assert calls[0]["deadline"] == started + 30.0


def test_attach_runner_collects_in_runner_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = initialized_store(tmp_path, monkeypatch)
    attach_directory = review_dir(tmp_path, "#900-feature-demo")
    complete_directory = review_dir(tmp_path, "#900-second-demo")
    attach_run = write_run(attach_directory, "attach.json")
    complete_run = write_run(complete_directory, "complete.json")
    monkeypatch.setenv("AGENT_RUNNER_DEPTH", "1")

    review_run.collect_outputs(
        "attach-runner",
        tmp_path,
        None,
        {"status": "success", "attached": [str(attach_run)], "unchanged": []},
    )
    review_run.collect_outputs(
        "complete",
        tmp_path,
        None,
        {"status": "success", "run_record": str(complete_run)},
    )

    assert observed_paths(store) == ["runs/attach.json"]


def test_save_points_call_collect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = review_dir(tmp_path)
    prepare_run = write_run(directory, "prepare.json")
    complete_run = write_run(directory, "complete.json")
    fail_run = write_run(directory, "fail.json")
    attach_run = write_run(directory, "attach.json")
    calls: list[dict[str, Any]] = []

    def fake_collect(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(capture, "collect", fake_collect)
    monkeypatch.setattr(
        review_run.workspace,
        "load_state",
        lambda _path: (tmp_path, {}),
    )
    monkeypatch.setattr(
        review_run,
        "prepare",
        lambda _args: {"status": "success", "run_record": str(prepare_run)},
    )
    monkeypatch.setattr(
        review_run,
        "complete",
        lambda _args: {"status": "success", "run_record": str(complete_run)},
    )
    monkeypatch.setattr(
        review_run,
        "fail_review",
        lambda _parent, _state, _reason: {"run_record": str(fail_run)},
    )
    monkeypatch.setattr(
        review_run,
        "attach_runner",
        lambda _path: {
            "status": "success",
            "attached": [str(attach_run)],
            "unchanged": [],
        },
    )
    monkeypatch.setattr(review_run, "retained_paths", lambda _state: {})
    state = tmp_path / "state.json"
    state.write_text("{}", encoding="utf-8")

    assert review_run.main(["prepare", "--pr", "x", "--runtime", "claude-code"]) == 0
    assert review_run.main(["complete", "--state", str(state)]) == 0
    assert review_run.main(["fail", "--state", str(state), "--reason", "停止"]) == 1
    assert (
        review_run.main(
            ["attach-runner", "--result", str(tmp_path / "runner-result.json")]
        )
        == 0
    )

    assert [(call["route"], call["event"], call["review_dir"]) for call in calls] == [
        ("pr-review", "prepare", directory),
        ("pr-review", "complete", directory),
        ("pr-review", "fail", directory),
        ("pr-review", "attach-runner", directory),
    ]
    assert calls[0]["files"] == ()
