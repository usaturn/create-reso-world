"""失敗したレビュアーの診断（#212）: ログを読む条件、原因の分類、回収の前の保存を確かめる。

ログは一時ファイルと偽の CLI だけで作り、実モデル・実 API・資格情報は使わない。保存した記録に、ログの文字列や
偽の秘密が入らないことも確かめる。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from tools.agent_runner.models import Attempt, Result

pytest_plugins = ("tools.test_support.plugin",)
# 偽の担当だけを起動するので、runner の担当（AGENT_RUNNER_DEPTH=1）の中でもテストの中だけ depth を外す
pytestmark = pytest.mark.usefixtures("outside_runner")

AUTH_LINE = "Error: invalid api key\n"


def failed_attempt(tmp_path: Path, *, stdout: str = "", stderr: str = "", **update: Any) -> tuple[Attempt, Path]:
    """runner の出力ディレクトリ（tmp_path/out）の中にログを書いた、停止を確認できた失敗の試行と、その出力。"""
    output = tmp_path / "out"
    directory = output / "request-1" / "attempt-1"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "stdout.log").write_text(stdout, encoding="utf-8")
    (directory / "stderr.log").write_text(stderr, encoding="utf-8")
    values: dict[str, Any] = {
        "agent_id": "beta",
        "state": "response_failed",
        "reported_state": "response_failed",
        "exit_code": 1,
        "elapsed_seconds": 2.5,
        "stop_confirmed": True,
        "stdout_path": directory / "stdout.log",
        "stderr_path": directory / "stderr.log",
        **update,
    }
    return Attempt(**values), output


# --- ログを読む条件 -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case", ["readable", "not_recorded", "not_stopped", "sensitive", "outside_output", "missing", "symlink", "fifo"]
)
def test_logs_are_read_only_when_safe(loop: Any, tmp_path: Path, case: str) -> None:
    # 読めば authentication になるログを置き、読んではいけない条件では読まずに理由を残す（受け入れ条件 2・4）
    attempt, output = failed_attempt(tmp_path, stderr=AUTH_LINE)
    log = attempt.stderr_path
    assert log is not None
    update: dict[str, Any] = {}
    if case == "not_recorded":
        update["stderr_path"] = None
    elif case == "not_stopped":
        update["stop_confirmed"] = False
    elif case == "sensitive":
        update["sensitive_paths"] = [log]
    elif case == "outside_output":
        outside = tmp_path / "elsewhere.log"
        outside.write_text(AUTH_LINE, encoding="utf-8")
        update["stderr_path"] = outside
    elif case == "missing":
        log.unlink()
    elif case == "symlink":
        target = output / "target.log"
        target.write_text(AUTH_LINE, encoding="utf-8")
        log.unlink()
        log.symlink_to(target)
    elif case == "fifo":
        log.unlink()
        os.mkfifo(log)

    diagnostic = loop.diagnose_attempt(attempt.model_copy(update=update), output)

    expected = {"readable": None, "symlink": "not_regular_file", "fifo": "not_regular_file"}.get(case, case)
    assert diagnostic.unavailable.get("stderr") == expected
    assert diagnostic.cause == ("authentication" if case == "readable" else "unknown")


@pytest.mark.parametrize(
    ("text", "cause"),
    [("x" * 200 + "\nError: read ECONNRESET\n", "connection"), (AUTH_LINE + "x" * 200 + "\n", "unknown")],
    ids=["cause-at-tail", "cause-at-head"],
)
def test_large_log_is_read_from_the_tail(
    loop: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str, cause: str
) -> None:
    monkeypatch.setattr(loop, "DIAGNOSTIC_READ_BYTES", 64)
    attempt, output = failed_attempt(tmp_path, stderr=text)

    diagnostic = loop.diagnose_attempt(attempt, output)

    assert (diagnostic.unavailable.get("stderr"), diagnostic.cause) == ("partial", cause)


# --- 原因の分類 ---------------------------------------------------------------------------------------------------

DSH_AUTH_TURN_END = {
    "type": "status",
    "phase": "turn_end",
    "turn": 1,
    "reason": {"kind": "error", "error": {"code": "AUTH", "message": "401: rejected"}},
}


@pytest.mark.parametrize(
    ("stdout", "stderr", "cause"),
    [
        pytest.param(
            json.dumps({"type": "tool_result", "status": "completed", "result": "HTTP 401 Unauthorized"}) + "\n",
            "",
            "unknown",
            id="tool-output-is-data",
        ),
        pytest.param("The handler returns 429 when rate limited.\n", "", "unknown", id="model-prose-is-data"),
        pytest.param(json.dumps({"type": "error", "message": "invalid api key"}) + "\n", "", "authentication", id="error-event"),
        pytest.param(json.dumps(DSH_AUTH_TURN_END) + "\n", "", "authentication", id="dsh-turn-end"),
        pytest.param("Error: fetch failed\n", "", "connection", id="diagnostic-line"),
        pytest.param(
            "",
            'Traceback (most recent call last):\n  File "run.py", line 401, in main\nRuntimeError: boom\n',
            "runtime_error",
            id="traceback-line-number-is-not-a-status",
        ),
        pytest.param("", "HTTP 401 Unauthorized\nconnection reset by peer\n", "authentication", id="priority"),
        pytest.param("", "HTTP 429 Too Many Requests\n", "rate_limit", id="rate-limit"),
        pytest.param("", "dsh-sandbox: cannot bind the workspace\n", "sandbox", id="sandbox"),
        pytest.param("", "Request timed out\n", "timeout", id="timeout"),
    ],
)
def test_cause_uses_only_failure_channels(loop: Any, tmp_path: Path, stdout: str, stderr: str, cause: str) -> None:
    attempt, output = failed_attempt(tmp_path, stdout=stdout, stderr=stderr)

    assert loop.diagnose_attempt(attempt, output).cause == cause


@pytest.mark.parametrize(
    ("exit_code", "state", "reported", "sensitive", "stopped", "cause"),
    [
        (0, "response_failed", None, False, True, "response_extraction"),
        (0, "invalid_result", "response_failed", False, True, "response_extraction"),
        (0, "missing_result", "success", False, True, "unknown"),
        (1, "response_failed", None, False, True, "unknown"),
        (0, "response_failed", None, True, True, "unknown"),
        (0, "response_failed", None, False, False, "unknown"),
    ],
)
def test_response_extraction_is_decided_from_the_end_state(
    loop: Any,
    tmp_path: Path,
    exit_code: int,
    state: str,
    reported: str | None,
    sensitive: bool,
    stopped: bool,
    cause: str,
) -> None:
    # ログの照合に当たらないとき、停止確認済み・終了コード 0 なのに結果が無いことだけが「応答の取り出し」
    attempt, output = failed_attempt(
        tmp_path,
        exit_code=exit_code,
        state=state,
        reported_state=reported,
        stop_confirmed=stopped,
        sensitive_paths=[tmp_path / "receipt.json"] if sensitive else [],
    )

    assert loop.diagnose_attempt(attempt, output).cause == cause


def test_unobserved_values_are_listed(loop: Any, tmp_path: Path) -> None:
    attempt, output = failed_attempt(tmp_path, exit_code=None, reported_state=None)

    diagnostic = loop.diagnose_attempt(attempt, output)

    assert diagnostic.unavailable == {"exit_code": "not_observed", "reported_state": "not_observed"}
    assert (diagnostic.exit_code, diagnostic.reported_state, diagnostic.cause) == (None, None, "unknown")


# --- 保存 ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("verdict", "stage", "states", "saved"),
    [
        ("accepted", None, ["success"], False),
        ("accepted", None, ["response_failed", "success"], True),
        ("rejected", "payload", ["success"], True),
    ],
    ids=["accepted", "failed-fallback", "rejected"],
)
def test_keep_diagnostic_covers_only_reviewers_with_a_failure(
    loop: Any, tmp_path: Path, verdict: str, stage: str | None, states: list[str], saved: bool
) -> None:
    attempts = []
    for number, state in enumerate(states, 1):
        attempt, output = failed_attempt(tmp_path / f"attempt-{number}", state=state, exit_code=0)
        attempts.append(attempt.model_copy(update={"agent_id": f"agent-{number}"}))
    result = Result(
        request_id="request-1",
        role="inspect",
        requested_agent="agent-1",
        actual_agent=f"agent-{len(states)}",
        state="success",
        attempts=attempts,
    )
    entry = loop.ReviewerEntry(
        requested_agent="agent-1",
        actual_agent=f"agent-{len(states)}",
        runner_state="success",
        verdict=verdict,
        rejected_stage=stage,
    )
    directory = tmp_path / "diagnostics"

    assert loop.keep_diagnostic(result, entry, directory, tmp_path) is True

    if not saved:
        assert not directory.exists() and entry.diagnostic_file is None
        return
    path = Path(entry.diagnostic_file)
    assert path == directory / "request-1.json"
    assert loop.sha256_file(path) == entry.diagnostic_sha256 and entry.diagnostic_error is None
    diagnostic = loop.ReviewerDiagnostic.model_validate_json(path.read_text(encoding="utf-8"))
    assert (diagnostic.verdict, diagnostic.stage) == (verdict, stage)
    assert [item.agent_id for item in diagnostic.attempts] == [f"agent-{number}" for number in range(1, len(states) + 1)]
