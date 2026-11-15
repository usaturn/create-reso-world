"""loop.py の保存点から review-eval の収集へ記録を渡す（Issue #357）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.review_eval import capture
from tools.review_eval.store import Store
from tools.review_eval.tests.support import write_collection_config

REPOSITORY = "usaturn/create-reso-world"
NUMBER = 900


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


def initialized_store(env: Any, monkeypatch: pytest.MonkeyPatch) -> Store:
    store = Store.init(env.root / "store")
    config = write_collection_config(
        env.root / "review-eval.toml",
        store=store.root,
        workspace_root=env.parent,
        repos=[REPOSITORY],
    )
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", str(config))
    return store


def observed_paths(store: Store) -> list[str]:
    return [observation.path for observation in store.observations(REPOSITORY, NUMBER)]


def write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def begin_planning(loop: Any, env: Any) -> None:
    """現在の HEAD の成果を置いてから cycle-begin を呼び、レビュアーを起動せずに計画の段階へ進める。"""
    env.place_review(env.gh.head())
    begun = loop.cycle_begin(env.run_dirs[-1], github=env.github)
    assert begun["review"]["mode"] == "reuse"


def test_cycle_end_copies_records_and_virtual_records(
    loop: Any,
    env: Any,
    kit: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = initialized_store(env, monkeypatch)
    monkeypatch.setattr(loop, "GitHub", lambda: env.github)
    env.start()
    head = env.gh.head()
    begin_planning(loop, env)
    run_dir = env.run_dirs[-1]
    record_file = write_json(
        tmp_path / "record.json",
        kit.round_record(1, head, "no_fix_needed", []),
    )
    env.gh.merge()
    finalize_result = kit.finalize_result(tmp_path / "finalize.json", "no_fix_needed", merged=True)

    code = loop.main(
        [
            "cycle-end",
            "--run",
            str(run_dir),
            "--record-file",
            str(record_file),
            "--finalize-result",
            str(finalize_result),
        ]
    )

    assert code == 0
    run_id = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))["run_id"]
    expected = {
        f"loop/{run_id}/run.json",
        f"loop/{run_id}/cycle-1.json",
        "@pr-comment/round-1/record.json",
        f"@finalize/{head[:12]}/result.json",
    }
    assert expected <= set(observed_paths(store))


def test_save_points_call_collect(
    loop: Any,
    env: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env.start()
    run_dir = env.run_dirs[-1]
    run_id = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))["run_id"]
    calls: list[dict[str, Any]] = []

    def fake_collect(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(capture, "collect", fake_collect)
    monkeypatch.setattr(loop, "review", lambda _run_dir: {"status": "ok"})
    monkeypatch.setattr(loop, "cycle_end", lambda *_args, **_kwargs: {"status": "ok"})
    monkeypatch.setattr(loop, "finish", lambda *_args, **_kwargs: {"status": "ok"})
    monkeypatch.setattr(loop, "recover", lambda *_args, **_kwargs: {"status": "ok"})

    assert loop.main(["review", "--run", str(run_dir)]) == 0
    assert loop.main(["cycle-end", "--run", str(run_dir)]) == 0
    assert loop.main(["finish", "--run", str(run_dir)]) == 0
    assert loop.main(["recover", "--run", str(run_dir)]) == 0

    assert [(call["route"], call["event"], call["review_dir"]) for call in calls] == [
        ("pr-review-fix-loop", "review", env.review_dir),
        ("pr-review-fix-loop", "cycle_end", env.review_dir),
        ("pr-review-fix-loop", "finish", env.review_dir),
        ("pr-review-fix-loop", "recover", env.review_dir),
    ]
    assert [call.get("verify_loop_run") for call in calls] == [None, None, run_id, run_id]


def test_review_sweeps_before_batch(
    loop: Any,
    env: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = initialized_store(env, monkeypatch)
    env.start()
    run_dir = env.run_dirs[-1]
    loop.cycle_begin(run_dir, github=env.github)
    review_file = env.review_dir / "alpha-model.md"
    old = "# レビュー\n\n古い版の指摘です。\n二行目の本文です。\n"
    review_file.write_text(old, encoding="utf-8")

    calls: list[tuple[Any, ...]] = []
    real_collect_records = loop.collect_records

    def recording(*args: Any, **kwargs: Any) -> None:
        calls.append(args)
        real_collect_records(*args, **kwargs)

    def fake_batch(*_args: Any, **_kwargs: Any) -> Any:
        review_file.write_text("# レビュー\n\nbatch が上書きした版です。\n", encoding="utf-8")
        raise loop.LoopError(5, "runner", "テストの停止")

    monkeypatch.setattr(loop, "collect_records", recording)
    monkeypatch.setattr(loop, "_review_batch", fake_batch)

    with pytest.raises(loop.LoopError):
        loop.review(run_dir, github=env.github)

    assert calls[0][:2] == ("review", run_dir.resolve())
    observations = {observation.path: observation for observation in store.observations(REPOSITORY, NUMBER)}
    assert "alpha-model.md" in observations
    assert store.read_blob(observations["alpha-model.md"].sha256) == old.encode("utf-8")


def test_loop_error_still_collects_and_keeps_exit_code(
    loop: Any,
    env: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = initialized_store(env, monkeypatch)
    env.start()
    run_dir = env.run_dirs[-1]
    calls: list[Path] = []
    real_collect_records = loop.collect_records
    real_collect = capture.collect

    def recording(_event: str, directory: Path, **kwargs: Any) -> None:
        calls.append(directory)
        real_collect_records(_event, directory, **kwargs)

    def broken_collect(**_kwargs: Any) -> None:
        raise RuntimeError("収集に失敗した")

    monkeypatch.setattr(loop, "collect_records", recording)
    monkeypatch.setattr(capture, "collect", broken_collect)
    code = loop.main(["cycle-end", "--run", str(run_dir)])
    output = capsys.readouterr().out

    missing = tmp_path / "missing-run"
    missing_code = loop.main(["cycle-end", "--run", str(missing)])
    missing_output = capsys.readouterr().out

    assert calls == [run_dir]
    assert missing_code != code
    assert "missing-run" in missing_output

    monkeypatch.setattr(capture, "collect", real_collect)
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")
    assert loop.main(["cycle-end", "--run", str(run_dir)]) == code
    assert capsys.readouterr().out == output
    assert observed_paths(store) == []


def test_loop_disabled_writes_nothing(
    loop: Any,
    env: Any,
    kit: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = initialized_store(env, monkeypatch)
    monkeypatch.setattr(loop, "GitHub", lambda: env.github)
    env.start()
    head = env.gh.head()
    begin_planning(loop, env)
    run_dir = env.run_dirs[-1]
    record_file = write_json(
        tmp_path / "record.json",
        kit.round_record(1, head, "no_fix_needed", []),
    )
    env.gh.merge()
    finalize_result = kit.finalize_result(tmp_path / "finalize.json", "no_fix_needed", merged=True)
    monkeypatch.setenv("REVIEW_EVAL_CONFIG", "")

    assert (
        loop.main(
            [
                "cycle-end",
                "--run",
                str(run_dir),
                "--record-file",
                str(record_file),
                "--finalize-result",
                str(finalize_result),
            ]
        )
        == 0
    )
    assert observed_paths(store) == []
