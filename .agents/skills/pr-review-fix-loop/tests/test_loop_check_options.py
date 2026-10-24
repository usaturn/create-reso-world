"""check-options が、start と同じ検査を PR・ロック・run・GitHub・herdr に触れずに行うことを確かめる（#678）。

issue-to-pr は worktree を作る前に check-options を呼び、何時間も実装した後で start が拒否する事態を避ける。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


def check_options(loop: Any, capsys: pytest.CaptureFixture[str], *arguments: str) -> tuple[int, dict[str, Any]]:
    capsys.readouterr()
    code = loop.main(["check-options", *arguments])
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def isolated(loop: Any, env: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """check-options が GitHub や親 checkout を使えば、偽の gh の呼び出しとして見えるようにする。"""
    monkeypatch.setattr(loop, "GitHub", lambda: env.github)
    monkeypatch.setattr(loop.target, "default_parent_root", lambda: env.parent)
    return env


def assert_untouched(env: Any) -> None:
    assert env.gh.calls == []
    assert not (env.parent / "reviews").exists()


def test_check_options_has_no_external_side_effects(
    loop: Any, isolated: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    code, output = check_options(loop, capsys, "--template", str(isolated.template))

    assert code == 0
    assert output["status"] == "ok"
    assert_untouched(isolated)


def test_check_options_reports_the_options_start_would_record(
    loop: Any, isolated: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    code, output = check_options(
        loop,
        capsys,
        "--max-cycles",
        "2",
        "--assign",
        "inspect=beta",
        "--assign",
        "implement=beta",
        "--template",
        str(isolated.template),
    )

    assert code == 0
    started = isolated.start(max_cycles=2, assign=["inspect=beta", "implement=beta"])
    run = json.loads((Path(started["run_dir"]) / "run.json").read_text(encoding="utf-8"))
    assert output["options"] == {key: value for key, value in run["options"].items() if key != "fresh_review"}
    assert output["assignments"] == run["assignments"]
