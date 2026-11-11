"""start の Herdr ペイン名を確かめる。ハングしても PR の処理を始める start が戻ること、現在のペインだけを
正しい名前に 1 回変えること（単独起動は PR#<番号>、Issue 起点は <repo>:#<Issue番号>）、無効な Issue 引数を
ロックの前に拒否すること、改名の失敗を warnings に残すこと。
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def hanging_herdr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """実際の Herdr に接続せず、起動した印を残して待つ単一プロセスを置く。"""
    directory = tmp_path / "herdr-bin"
    directory.mkdir()
    called = tmp_path / "herdr-called"
    program = directory / "herdr"
    program.write_text(
        f"#!{sys.executable}\nimport pathlib, time\npathlib.Path({str(called)!r}).touch()\ntime.sleep(60)\n",
        encoding="utf-8",
    )
    program.chmod(0o755)
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setenv("HERDR_PANE_ID", "w1:p9")
    return called


@pytest.fixture
def recording_herdr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """実際の Herdr に接続せず、呼び出しの argv を JSONL に記録する fake を PATH の先頭に置く。

    終了コードは既定 0。FAKE_HERDR_EXIT で変える（改名の失敗のテスト）。
    """
    directory = tmp_path / "herdr-bin"
    directory.mkdir()
    calls = tmp_path / "herdr-calls.jsonl"
    program = directory / "herdr"
    program.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys\n"
        f"with pathlib.Path({str(calls)!r}).open('a', encoding='utf-8') as stream:\n"
        "    stream.write(json.dumps(sys.argv[1:], ensure_ascii=False) + '\\n')\n"
        "sys.exit(int(os.environ.get('FAKE_HERDR_EXIT', '0')))\n",
        encoding="utf-8",
    )
    program.chmod(0o755)
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setenv("HERDR_PANE_ID", "w1:p9")
    return calls


def recorded_calls(calls: Path) -> list[list[str]]:
    if not calls.exists():
        return []
    return [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]


def test_start_succeeds_when_herdr_hangs(
    loop: Any, env: Any, hanging_herdr: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # UI の補助処理が停止しないために、本来の PR 処理まで無期限に止まる退行を防ぐ。
    monkeypatch.setattr(loop, "HERDR_TIMEOUT_SECONDS", 0.5)
    began = time.monotonic()

    started = env.start()

    assert time.monotonic() - began < 5
    assert hanging_herdr.exists()
    assert started["status"] == "ok"
    assert started["herdr_pane"]["state"] == "failed"
    assert started["herdr_pane"]["reason"]
    lock = json.loads((env.review_dir / "loop/lock.json").read_text(encoding="utf-8"))
    assert lock["run_id"] == started["run_id"]
    run = loop.load_run(Path(started["run_dir"]))
    assert run.state == "running"


def test_start_without_issue_number_renames_current_pane_to_pr_label(env: Any, recording_herdr: Path) -> None:
    # 単独起動は PR#<番号> を維持し、現在のペインだけを 1 回変える。別のペインを操作する・名前を残さない退行を防ぐ。
    started = env.start()

    assert started["herdr_pane"]["state"] == "renamed"
    assert started["herdr_pane"]["label"] == "PR#900"
    assert recorded_calls(recording_herdr) == [["pane", "rename", "w1:p9", "PR#900"]]
    run = json.loads((Path(started["run_dir"]) / "run.json").read_text(encoding="utf-8"))
    assert run["herdr_pane"] == started["herdr_pane"]


def test_start_with_issue_number_uses_issue_label(env: Any, recording_herdr: Path) -> None:
    # Issue 起点の run は現在のペインに <repo>:#<Issue番号> を出す。PR のラベルで Issue の識別を失う退行を防ぐ。
    started = env.start(issue_number=355)

    assert started["herdr_pane"]["label"] == "create-reso-world:#355"
    assert recorded_calls(recording_herdr) == [["pane", "rename", "w1:p9", "create-reso-world:#355"]]


def test_start_with_issue_repository_keeps_issue_repo_label(env: Any, recording_herdr: Path) -> None:
    # クロス repo では PR の repo から再導出せず、渡された Issue の repo の表示を保つ。Issue の識別を別の repo の
    # 名前で上書きする退行を防ぐ。
    started = env.start(issue_number=355, issue_repository="other-owner/other-repo")

    assert started["herdr_pane"]["label"] == "other-repo:#355"
    assert recorded_calls(recording_herdr) == [["pane", "rename", "w1:p9", "other-repo:#355"]]


@pytest.mark.parametrize("issue_number", [0, -1])
def test_start_rejects_non_positive_issue_number_before_lock(
    loop: Any, env: Any, recording_herdr: Path, issue_number: int
) -> None:
    # 無効値はロック取得の前に拒否する。誤った Issue 番号で黙って始める・拒否でロックや run が残る退行を防ぐ。
    with pytest.raises(loop.LoopError) as exc:
        env.start(issue_number=issue_number)

    assert exc.value.code == 2
    assert exc.value.stage == "arguments"
    assert not (env.review_dir / "loop" / "lock.json").exists()
    assert not (env.review_dir / "loop").exists()
    assert recorded_calls(recording_herdr) == []


@pytest.mark.parametrize(
    ("issue_number", "issue_repository"),
    [(355, "no-slash"), (None, "other-owner/other-repo")],
)
def test_start_rejects_invalid_issue_repository(
    loop: Any, env: Any, recording_herdr: Path, issue_number: int | None, issue_repository: str
) -> None:
    # 形式違反と --issue-repository 単独はロックの前に拒否する。誤った repo の表示・引数の黙殺を防ぐ。
    options: dict[str, Any] = {"issue_repository": issue_repository}
    if issue_number is not None:
        options["issue_number"] = issue_number
    with pytest.raises(loop.LoopError) as exc:
        env.start(**options)

    assert exc.value.code == 2
    assert exc.value.stage == "arguments"
    assert not (env.review_dir / "loop" / "lock.json").exists()
    assert not (env.review_dir / "loop").exists()
    assert recorded_calls(recording_herdr) == []


def test_start_succeeds_when_rename_fails(
    env: Any, recording_herdr: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 改名の失敗で run を止めない一方、失敗を成功として報告しない: herdr_pane と warnings に失敗を残す。
    monkeypatch.setenv("FAKE_HERDR_EXIT", "1")

    started = env.start()

    assert started["status"] == "ok"
    assert started["herdr_pane"]["state"] == "failed"
    reason = started["herdr_pane"]["reason"]
    assert reason
    assert any(reason in warning for warning in started["warnings"])
