"""Herdr がハングしても、PR の処理を始める start が戻ることを確かめる。"""

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
