"""失敗したレビュアーの診断（#212）: ログを読む条件、原因の分類、回収の前の保存を確かめる。

ログは一時ファイルと偽の CLI だけで作り、実モデル・実 API・資格情報は使わない。保存した記録に、ログの文字列や
偽の秘密が入らないことも確かめる。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest

from tools.agent_runner.adapters import AdapterOutcome, Capabilities, LaunchSpec
from tools.agent_runner.adapters.claude_code import ADAPTER as CLAUDE_CODE_ADAPTER
from tools.agent_runner.models import Attempt, BatchResult, Identity, Result

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
    "case",
    [
        "readable",
        "not_stopped",
        "sensitive",
        "outside_output",
        "symlink",
        "fifo",
        "ancestor-swap",
    ],
)
def test_logs_are_read_only_when_safe(
    loop: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    # 読めば authentication になるログを置き、読んではいけない条件では読まずに理由を残す（受け入れ条件 2・4）
    attempt, output = failed_attempt(tmp_path, stderr=AUTH_LINE)
    log = attempt.stderr_path
    assert log is not None
    update: dict[str, Any] = {}
    if case == "not_stopped":
        # 生存中の書き手がログを差し替えうるので、パスが安全でも読まない。
        update["stop_confirmed"] = False
    elif case == "sensitive":
        update["sensitive_paths"] = [log]
    elif case == "outside_output":
        outside = tmp_path / "elsewhere.log"
        outside.write_text(AUTH_LINE, encoding="utf-8")
        update["stderr_path"] = outside
    elif case == "symlink":
        target = output / "target.log"
        target.write_text(AUTH_LINE, encoding="utf-8")
        log.unlink()
        log.symlink_to(target)
    elif case == "fifo":
        log.unlink()
        os.mkfifo(log)
    elif case == "ancestor-swap":
        # os.open の境界で祖先ディレクトリを出力の外への symlink に差し替える。字句上のパスが出力の内側でも、
        # 差し替えられた祖先は辿らず、出力の外の認証文字列を読まない（祖先 fd 固定の受け入れ条件）
        outside = tmp_path / "outside"
        (outside / "attempt-1").mkdir(parents=True)
        (outside / "attempt-1" / "stderr.log").write_text(AUTH_LINE, encoding="utf-8")
        real_open = os.open
        swapped = False

        def swap_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
            nonlocal swapped
            if not swapped and (path == log or (path == "request-1" and kwargs.get("dir_fd") is not None)):
                swapped = True
                shutil.rmtree(log.parent.parent)
                log.parent.parent.symlink_to(outside)
            return real_open(path, flags, *args, **kwargs)

        monkeypatch.setattr(loop.os, "open", swap_open)

    diagnostic = loop.diagnose_attempt(attempt.model_copy(update=update), output, runtime="pi")

    expected = {
        "readable": None,
        "symlink": "not_regular_file",
        "fifo": "not_regular_file",
        "ancestor-swap": "not_regular_file",
    }.get(case, case)
    assert diagnostic.unavailable.get("stderr") == expected
    assert diagnostic.cause == ("authentication" if case == "readable" else "unknown")


# --- 原因の分類 ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stdout", "stderr", "cause"),
    [
        pytest.param(
            json.dumps(
                {
                    "type": "tool_result",
                    "status": "completed",
                    "result": "HTTP 401 Unauthorized",
                }
            )
            + "\n",
            "",
            "unknown",
            id="tool-output-is-data",
        ),
        pytest.param(
            json.dumps({"type": "error", "message": "invalid api key"}) + "\n",
            "",
            "authentication",
            id="error-event",
        ),
        pytest.param(
            "",
            'Traceback (most recent call last):\n  File "run.py", line 401, in main\nRuntimeError: boom\n',
            "runtime_error",
            id="traceback-line-number-is-not-a-status",
        ),
        pytest.param("[ERROR] connection refused\n", "", "connection", id="bracketed-diagnostic"),
        pytest.param(
            json.dumps({"type": "tool_result", "is_error": True, "content": "HTTP 401 Unauthorized"}) + "\n",
            "",
            "unknown",
            id="tool-result-error-body",
        ),
        pytest.param(
            json.dumps({"type": "tool_result", "is_error": True, "message": "HTTP 401 Unauthorized"}) + "\n",
            "",
            "unknown",
            id="tool-result-error-message",
        ),
        pytest.param(
            json.dumps(
                {"type": "result", "subtype": "success", "is_error": True, "result": "HTTP 401 Unauthorized"}
            )
            + "\n",
            "",
            "unknown",
            id="result-error-body",
        ),
        pytest.param(
            json.dumps({"type": "error", "message": {"text": "HTTP 401 Unauthorized"}}) + "\n",
            "",
            "unknown",
            id="error-message-not-a-string",
        ),
        pytest.param(
            json.dumps({"type": "error", "error": {"message": "invalid api key"}}) + "\n",
            "",
            "authentication",
            id="error-object-message",
        ),
        pytest.param(
            json.dumps(
                {"type": "error", "message": "request failed", "error": {"message": "HTTP 401 Unauthorized"}}
            )
            + "\n",
            "",
            "authentication",
            id="error-message-and-error-object",
        ),
        pytest.param(
            json.dumps({"type": "turn.failed", "error": "invalid api key"}) + "\n",
            "",
            "authentication",
            id="error-string",
        ),
    ],
)
def test_cause_uses_only_failure_channels(loop: Any, tmp_path: Path, stdout: str, stderr: str, cause: str) -> None:
    # 失敗のイベントから使うのは安全な CLI のエラー欄（文字列の message・error・error.message）だけで、
    # message があっても error.message を捨てない。tool_result・result/content・モデル本文は is_error=true でも
    # 分類しない（PR の本文やコードの偽陽性）
    attempt, output = failed_attempt(tmp_path, stdout=stdout, stderr=stderr)

    assert loop.diagnose_attempt(attempt, output, runtime="pi").cause == cause


@pytest.mark.parametrize(
    ("state", "reported", "cause"),
    [
        ("success", "success", "unknown"),
        ("response_failed", "response_failed", "authentication"),
        # reported_state は adapter の分類で成功の根拠にしない。失敗の試行は同じログを今までどおり分類する
        ("response_failed", "success", "authentication"),
    ],
    ids=["success", "failed", "reported-success-is-not-success"],
)
def test_successful_attempts_have_no_failure_cause(
    loop: Any, tmp_path: Path, state: str, reported: str, cause: str
) -> None:
    # 成功した試行（state == success）に失敗の原因は付けない。ログに認証の語があっても unknown。
    # 同じログでも失敗の試行は authentication になる（陽性対照）
    attempt, output = failed_attempt(tmp_path, stderr=AUTH_LINE, state=state, reported_state=reported, exit_code=0)

    assert loop.diagnose_attempt(attempt, output, runtime="pi").cause == cause


@pytest.mark.parametrize(
    "stdout_event",
    [
        pytest.param(
            {"type": "result", "subtype": "success", "is_error": True, "result": "HTTP 401 Unauthorized"},
            id="result-body-only",
        ),
        pytest.param(
            {"type": "tool_result", "is_error": True, "message": "HTTP 401 Unauthorized"},
            id="tool-result-message",
        ),
    ],
)
def test_reported_failure_without_safe_text_is_not_response_extraction(
    loop: Any, tmp_path: Path, stdout_event: dict[str, Any]
) -> None:
    # 失敗の報告があっても安全に取り出せる文が無い（result 本文だけ・tool_result の出力）ときは、報告の事実だけを
    # 数えて文は空にし、response_extraction と推測しない。本文そのものも分類しない（終了コード 0 の取り出し失敗の条件で確かめる）
    attempt, output = failed_attempt(tmp_path, stdout=json.dumps(stdout_event) + "\n", exit_code=0)

    assert loop.diagnose_attempt(attempt, output, runtime="pi").cause == "unknown"


@pytest.mark.parametrize(
    ("exit_code", "state", "reported", "sensitive", "stopped", "cause"),
    [
        (0, "response_failed", None, False, True, "response_extraction"),
        (0, "missing_result", "success", False, True, "unknown"),
        (1, "response_failed", None, False, True, "unknown"),
        # ログは読めても、秘密の残る保持物（receipt）がある試行は取り出しの失敗と推測しない
        (0, "response_failed", None, True, True, "unknown"),
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

    assert loop.diagnose_attempt(attempt, output, runtime="pi").cause == cause


def test_success_payload_approval_key_is_not_a_diagnostic(loop: Any, tmp_path: Path) -> None:
    secret = "fixture-approval-payload-secret"
    stdout = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "permission_denials": [],
            "result": "承認待ち。requires approval と引用された。",
        }
    ) + "\n"
    attempt, output = failed_attempt(
        tmp_path,
        stdout=stdout,
        state="success",
        reported_state="success",
        exit_code=0,
        payload={
            "approval": {
                "source": "permission_denials",
                "terminal_subtype": "success",
                "is_error": False,
                "permission_denials": True,
                "denial_count": 1,
                "diagnostic_sources": [],
            },
            "raw": secret,
        },
    )

    diagnostic = loop.diagnose_attempt(attempt, output, runtime="claude-code")

    assert diagnostic.approval is None
    assert diagnostic.cause == "unknown"
    assert secret not in diagnostic.model_dump_json()


def test_other_runtime_approval_payload_is_not_a_diagnostic(loop: Any, tmp_path: Path) -> None:
    secret = "fixture-other-runtime-secret"
    attempt, output = failed_attempt(
        tmp_path,
        state="awaiting_approval",
        exit_code=0,
        payload={
            "approval": {
                "source": "permission_denials",
                "terminal_subtype": "success",
                "is_error": False,
                "permission_denials": True,
                "denial_count": 1,
                "diagnostic_sources": [],
            },
            "raw": secret,
        },
    )

    diagnostic = loop.diagnose_attempt(attempt, output, runtime="pi")

    assert diagnostic.approval is None
    assert diagnostic.cause == "unknown"
    assert secret not in diagnostic.model_dump_json()


@pytest.mark.parametrize(
    "forged",
    [
        {
            "source": "permission_denials",
            "terminal_subtype": "success",
            "is_error": False,
            "permission_denials": True,
            "denial_count": 1,
            "diagnostic_sources": [],
            "raw": "fixture-approval-metadata-secret",
        },
        {
            "source": "permission_denials",
            "terminal_subtype": "success",
            "is_error": 1,
            "permission_denials": True,
            "denial_count": -1,
            "diagnostic_sources": [],
        },
    ],
    ids=["unknown-key", "wrong-types"],
)
def test_malformed_approval_payload_is_not_a_diagnostic(loop: Any, tmp_path: Path, forged: dict[str, Any]) -> None:
    attempt, output = failed_attempt(
        tmp_path,
        state="awaiting_approval",
        exit_code=0,
        payload={"approval": forged},
    )

    diagnostic = loop.diagnose_attempt(attempt, output, runtime="claude-code")

    assert diagnostic.approval is None
    assert "fixture-approval-metadata-secret" not in diagnostic.model_dump_json()


def pi_message(stop_reason: str, error: str | None = None) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "stopReason": stop_reason, "content": []}
    if error is not None:
        message["errorMessage"] = error
    return message


PI_PROMPT = {"role": "user", "content": "Check the 401 Unauthorized handling and the connection reset path."}
PI_FAILED_429 = pi_message("error", "429 rate_limit_error")
PI_FAILED_503 = pi_message("error", '503 {"error":{"type":"overloaded_error"}}')


@pytest.mark.parametrize(
    ("events", "cause"),
    [
        pytest.param(
            [
                {"type": "message_end", "message": PI_FAILED_503},
                {"type": "agent_end", "messages": [PI_PROMPT, PI_FAILED_503]},
            ],
            "connection",
            id="failed-message",
        ),
        pytest.param(
            [{"type": "agent_end", "messages": [PI_PROMPT, pi_message("stop")]}],
            "response_extraction",
            id="nothing-reported",
        ),
    ],
)
def test_reported_failures_are_not_response_extraction(
    loop: Any, tmp_path: Path, events: list[dict[str, Any]], cause: str
) -> None:
    # pi は提供元の失敗を、失敗で終わった assistant のメッセージの errorMessage にだけ書き、終了コード 0 で終わる。
    # 報告された失敗は「応答の取り出し」にしない。プロンプト（PR の本文を含みうる）は分類に使わない
    stdout = "".join(json.dumps(event) + "\n" for event in events)
    attempt, output = failed_attempt(tmp_path, stdout=stdout, exit_code=0)

    assert loop.diagnose_attempt(attempt, output, runtime="pi").cause == cause


CLAUDE_INIT = {"type": "system", "subtype": "init", "model": "claude-opus-5-5", "session_id": "s"}
CLAUDE_TEXT = {"type": "assistant", "message": {"content": [{"type": "text", "text": "done"}]}}
CLAUDE_NON_JSON = {"type": "result", "subtype": "success", "is_error": False, "result": "not a json object"}
CLAUDE_OVERLOADED = {"type": "result", "subtype": "success", "is_error": True, "result": "API Error: 529 overloaded_error"}


def claude_retry(error: str, status: int) -> dict[str, Any]:
    """Claude Code が自動の再試行のたびに stream-json に出す通知（回復すれば試行は続く）。"""
    return {"type": "system", "subtype": "api_retry", "attempt": 1, "max_retries": 10, "error_status": status, "error": error}


# pi は再試行の前の失敗を message_end・turn_end に出し、agent_end の履歴にも残してから auto_retry_start を出す
PI_RETRY = [
    {"type": "message_end", "message": PI_FAILED_429},
    {"type": "turn_end", "message": PI_FAILED_429},
    {"type": "auto_retry_start", "attempt": 1, "maxAttempts": 3, "delayMs": 500, "errorMessage": "429 rate_limit_error"},
]


@pytest.mark.parametrize(
    ("events", "exit_code", "cause"),
    [
        pytest.param(
            [
                CLAUDE_INIT,
                claude_retry("overloaded", 529),
                CLAUDE_TEXT,
                CLAUDE_NON_JSON,
            ],
            0,
            "response_extraction",
            id="claude-retry-overloaded",
        ),
        pytest.param(
            [CLAUDE_INIT, claude_retry("overloaded", 529), CLAUDE_OVERLOADED],
            1,
            # result 本文はモデルの最終応答と区別できないので分類しない。失敗の報告はあるので unknown
            "unknown",
            id="claude-retries-exhausted-result-only",
        ),
        pytest.param(
            [
                CLAUDE_INIT,
                claude_retry("overloaded", 529),
                {"type": "error", "error": {"message": "API Error: 529 overloaded_error"}},
            ],
            1,
            "connection",
            id="claude-retries-exhausted-error-field",
        ),
        pytest.param(
            [
                *PI_RETRY,
                {"type": "auto_retry_end", "success": True, "attempt": 1},
                {"type": "message_end", "message": pi_message("stop")},
                {
                    "type": "agent_end",
                    "messages": [PI_PROMPT, PI_FAILED_429, pi_message("stop")],
                },
            ],
            0,
            "response_extraction",
            id="pi-retry-recovered",
        ),
        pytest.param(
            [
                *PI_RETRY,
                {"type": "message_end", "message": PI_FAILED_503},
                {
                    "type": "auto_retry_end",
                    "success": False,
                    "attempt": 3,
                    "finalError": "503 overloaded_error",
                },
            ],
            0,
            "connection",
            id="pi-retries-exhausted-without-agent-end",
        ),
    ],
)
def test_recovered_failures_do_not_decide_the_cause(
    loop: Any, tmp_path: Path, events: list[dict[str, Any]], exit_code: int, cause: str
) -> None:
    # 回復した一時的な失敗ではなく、試行を終わらせた失敗で分類する（PR #237 の claude-opus-5-5#M-1）。
    # 再試行を使い切った・取り消した失敗は報告なので、分類できなくても response_extraction にしない。
    # result 本文だけ（CLAUDE_OVERLOADED）は分類せず、同じ接続障害を CLI の error.message で報告した対照は connection
    stdout = "".join(json.dumps(event) + "\n" for event in events)
    attempt, output = failed_attempt(tmp_path, stdout=stdout, exit_code=exit_code)

    assert loop.diagnose_attempt(attempt, output, runtime="pi").cause == cause


def test_unobservable_logs_are_not_response_extraction(
    loop: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 失敗の報告の有無を観測できなければ、終了状態だけから「応答の取り出し」と推測しない（受け入れ条件 2、
    # PR #237 の deepseek#M-1）。末尾だけを読んだ（partial）ログも、切れた行に最後の失敗が隠れうるので観測としない
    attempt, output = failed_attempt(tmp_path, stdout="x" * 100 + "\n", exit_code=0)
    monkeypatch.setattr(loop, "DIAGNOSTIC_READ_BYTES", 16)

    diagnostic = loop.diagnose_attempt(attempt, output, runtime="pi")

    assert (diagnostic.cause, diagnostic.unavailable.get("stdout")) == ("unknown", "partial")


@pytest.mark.parametrize(
    ("limit", "tail_events", "cause"),
    [
        pytest.param(
            None,
            ["message_end", "agent_end"],
            "connection",
            id="history-line-over-1-mib",
        ),
        pytest.param(
            4096,
            ["message_end", "agent_end"],
            "unknown",
            id="history-line-over-the-limit",
        ),
    ],
)
def test_final_pi_failure_survives_a_long_history(
    loop: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    limit: int | None,
    tail_events: list[str],
    cause: str,
) -> None:
    # pi の agent_end は会話の履歴全体を 1 行に含み、実際のレビューの出力で 1 MiB を超える（PR #237 の自己レビューの
    # M-1）。最後の失敗はその直前の message_end にもあるので、履歴の行の大きさで分類が変わらない。
    # 上限を超えて末尾しか読めなければ、最後の失敗を見落としうるので response_extraction と推測しない
    if limit is not None:
        monkeypatch.setattr(loop, "DIAGNOSTIC_READ_BYTES", limit)
    history = [PI_PROMPT, *({"role": "toolResult", "content": "x" * 1000} for _ in range(1500)), PI_FAILED_503]
    events = {
        "message_end": {"type": "message_end", "message": PI_FAILED_503},
        "agent_end": {"type": "agent_end", "messages": history},
    }
    stdout = "".join(json.dumps(events[name]) + "\n" for name in tail_events)
    attempt, output = failed_attempt(tmp_path, stdout=stdout, exit_code=0)

    assert loop.diagnose_attempt(attempt, output, runtime="pi").cause == cause


@pytest.mark.parametrize(
    ("runtime", "stdout", "stderr", "state", "cause"),
    [
        pytest.param(
            "devin",
            "ログには次の行が出ていました。\n```text\nError: connection refused\n```\n"
            + json.dumps({"status": "failed"}),
            "",
            "success",
            "unknown",
            id="devin-fenced-example",
        ),
        pytest.param(
            "devin",
            "",
            "Error: read ECONNRESET\n",
            "response_failed",
            "connection",
            id="devin-stderr",
        ),
        pytest.param(
            "cursor",
            "Error: Authentication required\n",
            "",
            "response_failed",
            "authentication",
            id="cursor-cli-line",
        ),
        pytest.param(
            None,
            json.dumps({"type": "message_end", "message": PI_FAILED_503}) + "\n",
            "",
            "response_failed",
            "unknown",
            id="unknown-runtime",
        ),
    ],
)
def test_model_prose_stdout_never_decides_the_cause(
    loop: Any,
    tmp_path: Path,
    runtime: str | None,
    stdout: str,
    stderr: str,
    state: str,
    cause: str,
) -> None:
    # Devin の stdout はモデルの発言の平文で、コードブロックの中のログの例を含みうる（PR #237 のサイクル 2 の
    # gpt-6.1-sol#M-1・deepseek#L-1）。JSON のイベントの stream でないランタイムの stdout は照合の文にせず、
    # 失敗の報告に見える行があれば response_extraction とも推測しない。stderr は今までどおり使う
    attempt, output = failed_attempt(
        tmp_path, stdout=stdout, stderr=stderr, state=state, reported_state=state, exit_code=0
    )

    assert loop.diagnose_attempt(attempt, output, runtime=runtime).cause == cause


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
    loop: Any,
    tmp_path: Path,
    verdict: str,
    stage: str | None,
    states: list[str],
    saved: bool,
) -> None:
    attempts = []
    for number, state in enumerate(states, 1):
        attempt, _output = failed_attempt(tmp_path / f"attempt-{number}", state=state, exit_code=0)
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

    assert loop.keep_diagnostic(result, entry, directory, tmp_path, {}) is True

    if not saved:
        assert not directory.exists() and entry.diagnostic_file is None
        return
    path = Path(entry.diagnostic_file)
    assert path == directory / "request-1.json"
    assert loop.sha256_file(path) == entry.diagnostic_sha256 and entry.diagnostic_error is None
    diagnostic = loop.ReviewerDiagnostic.model_validate_json(path.read_text(encoding="utf-8"))
    assert (diagnostic.verdict, diagnostic.stage) == (verdict, stage)
    assert [item.agent_id for item in diagnostic.attempts] == [f"agent-{index}" for index in range(1, len(states) + 1)]


# --- review の全体の経路（偽の CLI と偽の gh） --------------------------------------------------------------------

# stdout・stderr に書いて、指定の終了コードで終わる偽の CLI。receipt は書かない
FAILING_PROGRAM = r"""
import json, sys
spec = json.loads(sys.argv[1])
sys.stdout.write(spec["stdout"])
sys.stderr.write(spec["stderr"])
sys.exit(spec["exit"])
"""


CLAUDE_NDJSON_PROGRAM = r"""
import json, sys
spec = json.loads(sys.argv[1])
sys.stdout.write(spec["stdout"])
sys.stderr.write(spec["stderr"])
sys.exit(spec.get("exit", 0))
"""


class ClaudeNDJSONReviewers:
    """Claude の NDJSON を書く偽の CLI と、本物の Claude adapter の collect を組み合わせる。

    receipt は書かない。runner は adapter が返した receipt を既存の保存経路に載せ、終了コード 0 の成功結果でも
    permission_denials を承認待ちのまま保存する。
    """

    def __init__(self, fixtures: dict[str, dict[str, object]], others: Any) -> None:
        self.capabilities = Capabilities()
        self.fixtures = fixtures
        self.others = others

    def __call__(self, runtime: str) -> ClaudeNDJSONReviewers:
        return self

    def prepare(self, context: Any) -> LaunchSpec:
        if context.request.agent_id not in self.fixtures:
            return self.others.prepare(context)
        fixture = self.fixtures[context.request.agent_id]
        return LaunchSpec(argv=(sys.executable, "-c", CLAUDE_NDJSON_PROGRAM, json.dumps(fixture)), stdin=b"")

    def collect(self, context: Any, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        if context.request.agent_id not in self.fixtures:
            return self.others.collect(context, stdout_path, stderr_path)
        return CLAUDE_CODE_ADAPTER.collect(context, stdout_path, stderr_path)


class MixedReviewers:
    """failures の担当は FAILING_PROGRAM、ほかは conftest の偽のレビュアー（others）に任せる adapter。

    失敗させる担当の collect は、adapter の中で分類を置き換えた形（state は response_failed、
    reported_state は置き換える前の値）を返す。
    """

    def __init__(self, others: Any, failures: dict[str, dict[str, Any]]) -> None:
        self.capabilities = Capabilities()
        self.others = others
        self.failures = failures

    def __call__(self, runtime: str) -> MixedReviewers:
        return self

    def prepare(self, context: Any) -> LaunchSpec:
        failure = self.failures.get(context.request.agent_id)
        if failure is None:
            return cast_spec(self.others.prepare(context))
        spec = {key: failure.get(key, default) for key, default in (("stdout", ""), ("stderr", ""), ("exit", 1))}
        return LaunchSpec(argv=(sys.executable, "-c", FAILING_PROGRAM, json.dumps(spec)), stdin=b"")

    def collect(self, context: Any, stdout_path: Path, stderr_path: Path) -> AdapterOutcome:
        failure = self.failures.get(context.request.agent_id)
        if failure is None:
            return self.others.collect(context, stdout_path, stderr_path)
        return AdapterOutcome(
            identity=Identity(model=context.agent.model),
            state="response_failed",
            reported_state=failure.get("reported"),
        )


def cast_spec(value: Any) -> LaunchSpec:
    assert isinstance(value, LaunchSpec)
    return value


def started_cycle(loop: Any, env: Any) -> Path:
    run_dir = Path(env.start()["run_dir"])
    loop.cycle_begin(run_dir, github=env.github)
    return run_dir


def saved_text(root: Path) -> str:
    """root の下の全ファイルの中身（保存した記録に、ログの文字列が写っていないかを調べる）。"""
    return "\n".join(
        path.read_bytes().decode("utf-8", errors="replace") for path in sorted(root.rglob("*")) if path.is_file()
    )


def registered_worktrees(root: Path) -> list[str]:
    listing = subprocess.run(
        ["git", "-C", str(root), "worktree", "list", "--porcelain"], check=True, capture_output=True, text=True
    ).stdout
    return [line.removeprefix("worktree ") for line in listing.splitlines() if line.startswith("worktree ")]


def read_diagnostic(loop: Any, path: str | None) -> Any:
    assert path is not None
    return loop.ReviewerDiagnostic.model_validate_json(Path(path).read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", ["terminal-denial", "stderr"], ids=["terminal-denial", "stderr"])
def test_claude_approval_evidence_survives_cleanup(loop: Any, env: Any, case: str) -> None:
    # 実 adapter の判定根拠が runner の保存経路を通り、生ログの回収後も診断に残る（受け入れ条件 1・4）
    secret = "fixture-" + uuid.uuid4().hex
    run_dir = started_cycle(loop, env)
    result: dict[str, object] = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": '{"status": "success"}',
        "permission_denials": [],
        "session_id": "fixture-session",
    }
    stderr = ""
    expected: tuple[str, str, bool, bool, int, list[str]]
    if case == "terminal-denial":
        result["permission_denials"] = [{"tool_name": "Bash", "tool_input": {"command": secret}}]
        expected = ("permission_denials", "success", False, True, 1, [])
    else:
        result["subtype"] = secret
        stderr = "requires approval\n"
        expected = ("diagnostic_text", "other", False, False, 0, ["stderr"])
    adapter = ClaudeNDJSONReviewers(
        {"beta": {"stdout": json.dumps(result) + "\n", "stderr": stderr}},
        env.reviewers({"alpha": "success"}),
    )

    reviewed = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert [entry["agent"] for entry in reviewed["accepted"]] == ["alpha"]
    (rejected,) = reviewed["rejected"]
    assert (rejected["agent"], rejected["rejected_stage"], rejected["diagnostic_error"]) == (
        "beta",
        "runner",
        None,
    )
    cycle = loop.load_cycles(run_dir)[-1]
    (attempt,) = read_diagnostic(loop, rejected["diagnostic_file"]).attempts
    assert (attempt.state, attempt.cause, attempt.exit_code) == ("awaiting_approval", "approval", 0)
    assert attempt.approval is not None
    assert (
        attempt.approval.source,
        attempt.approval.terminal_subtype,
        attempt.approval.is_error,
        attempt.approval.permission_denials,
        attempt.approval.denial_count,
        attempt.approval.diagnostic_sources,
    ) == expected
    run = loop.load_run(run_dir)
    assert [resource.state for resource in run.resources] == ["removed"]
    assert not Path(run.resources[0].path).exists()
    saved = saved_text(env.review_dir)
    assert secret not in saved
    assert secret not in json.dumps(attempt.approval.model_dump(mode="json"), ensure_ascii=False)

    batch_text = Path(cycle.review.batch.result_file).read_text(encoding="utf-8")
    assert secret not in batch_text
    batch = BatchResult.model_validate_json(batch_text)
    beta_attempt = next(result for result in batch.results if result.actual_agent == "beta").attempts[0]
    assert (beta_attempt.state, beta_attempt.reported_state, beta_attempt.exit_code) == (
        "awaiting_approval",
        "awaiting_approval",
        0,
    )


def test_claude_authentication_priority_keeps_approval_evidence(loop: Any, env: Any) -> None:
    # stderr は adapter では承認待ちの根拠になるが、既存の原因分類では認証が優先する。承認根拠を保存しつつ、
    # 復旧に必要な認証の分類を承認で上書きしない（#370 のレビュー）。実 adapter の保存経路と回収を通す。
    run_dir = started_cycle(loop, env)
    result: dict[str, object] = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": '{"status": "success"}',
        "permission_denials": [],
        "session_id": "fixture-session",
    }
    adapter = ClaudeNDJSONReviewers(
        {"beta": {"stdout": json.dumps(result) + "\n", "stderr": "Error: token expired; requires approval\n"}},
        env.reviewers({"alpha": "success"}),
    )

    reviewed = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert [entry["agent"] for entry in reviewed["accepted"]] == ["alpha"]
    (rejected,) = reviewed["rejected"]
    assert (rejected["agent"], rejected["rejected_stage"], rejected["diagnostic_error"]) == (
        "beta",
        "runner",
        None,
    )
    (attempt,) = read_diagnostic(loop, rejected["diagnostic_file"]).attempts
    assert (attempt.state, attempt.cause, attempt.exit_code) == ("awaiting_approval", "authentication", 0)
    assert attempt.approval is not None
    assert (attempt.approval.source, attempt.approval.diagnostic_sources) == ("diagnostic_text", ["stderr"])


def test_different_failures_leave_distinct_causes_after_cleanup(loop: Any, env: Any) -> None:
    # Issue #212 の再現と同じ形: 原因の違う失敗が、ログを回収した後も原因の分類で区別できる（受け入れ条件 1・5）
    run_dir = started_cycle(loop, env)
    markers = [f"fixture-{uuid.uuid4().hex}" for _ in range(2)]
    adapter = MixedReviewers(
        env.reviewers({}),
        {
            "alpha": {"stderr": f"Error: read ECONNRESET ({markers[0]})\n"},
            "beta": {
                "stderr": f'Traceback (most recent call last):\n  File "{markers[1]}.py", line 401, in main\n'
                "RuntimeError: boom\n"
            },
        },
    )

    with pytest.raises(loop.LoopError) as error:
        loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert (error.value.code, error.value.stage) == (6, "review")
    causes: dict[str, str] = {}
    for entry in loop.load_cycles(run_dir)[-1].review.reviewers:
        assert loop.sha256_file(Path(entry.diagnostic_file)) == entry.diagnostic_sha256
        diagnostic = read_diagnostic(loop, entry.diagnostic_file)
        (attempt,) = diagnostic.attempts
        assert (diagnostic.stage, attempt.state, attempt.exit_code, attempt.stop_confirmed) == (
            "runner",
            "response_failed",
            1,
            True,
        )
        assert attempt.unavailable == {}
        causes[entry.actual_agent] = attempt.cause
    assert causes == {"alpha": "connection", "beta": "runtime_error"}
    run = loop.load_run(run_dir)
    assert [resource.state for resource in run.resources] == ["removed"]
    assert not Path(run.resources[0].path).exists()
    saved = saved_text(env.review_dir)
    assert not any(marker in saved for marker in markers)


def test_secret_in_logs_never_reaches_the_records(loop: Any, env: Any) -> None:
    # 偽の秘密（実行時に組み立てる）を原因と同じ行に書いても、診断には分類名だけが残る（受け入れ条件 3・5）
    secret = "sk-" + hashlib.sha256(b"issue-212 fixture").hexdigest()[:40]
    run_dir = started_cycle(loop, env)
    adapter = MixedReviewers(
        env.reviewers({"alpha": "success"}),
        {
            "beta": {
                "stderr": f"HTTP 401 Unauthorized: token {secret} was rejected\n",
                "reported": "awaiting_authentication",
            }
        },
    )

    reviewed = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert reviewed["next"][-3:] == ["cycle-end", "--run", str(run_dir)]
    (accepted,) = reviewed["accepted"]
    (rejected,) = reviewed["rejected"]
    assert accepted["diagnostic_file"] is None and rejected["diagnostic_error"] is None
    (attempt,) = read_diagnostic(loop, rejected["diagnostic_file"]).attempts
    assert (attempt.cause, attempt.reported_state, attempt.state) == (
        "authentication",
        "awaiting_authentication",
        "response_failed",
    )
    assert secret not in saved_text(env.review_dir)
    assert secret not in json.dumps(reviewed, ensure_ascii=False)


def test_unsaved_diagnostic_keeps_the_output_and_tells_the_controller(loop: Any, env: Any) -> None:
    # 診断を保存できなければ、理由を司令塔に返し、ログを含む出力を消さずに残す（受け入れ条件 3）
    run_dir = started_cycle(loop, env)
    (run_dir / "cycle-1" / "diagnostics").write_text("not a directory", encoding="utf-8")
    adapter = MixedReviewers(env.reviewers({"alpha": "success"}), {"beta": {"stderr": "Error: read ECONNRESET\n"}})

    reviewed = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    assert reviewed["next"][-3:] == ["cycle-end", "--run", str(run_dir)]
    (rejected,) = reviewed["rejected"]
    assert (rejected["diagnostic_file"], rejected["diagnostic_error"]) == (None, "診断を保存できない（EEXIST）")
    (resource,) = loop.load_run(run_dir).resources
    assert resource.state == "retained" and "診断を保存できなかった" in str(resource.reason)
    assert resource.path in reviewed["retained"]
    cycle = loop.load_cycles(run_dir)[-1]
    batch = BatchResult.model_validate_json(Path(cycle.review.batch.result_file).read_text(encoding="utf-8"))
    beta = next(result for result in batch.results if result.actual_agent == "beta")
    assert beta.attempts[-1].stderr_path is not None and beta.attempts[-1].stderr_path.is_file()
    assert registered_worktrees(env.parent) == [str(env.parent)]
    finished = loop.finish(run_dir, abort="environment: 診断を保存できなかった", github=env.github)
    assert resource.path in finished["retained"]


def test_review_reads_stdout_by_the_reviewer_runtime(loop: Any, env: Any) -> None:
    # review は担当の設定のランタイムを診断に渡す。pi（JSON のイベントの stream）は stdout の失敗のイベントで分類する
    run_dir = started_cycle(loop, env)
    failure = {"stdout": json.dumps({"type": "error", "message": "connection refused"}) + "\n"}
    adapter = MixedReviewers(env.reviewers({"beta": "success"}), {"alpha": failure})

    reviewed = loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    (rejected,) = reviewed["rejected"]
    (attempt,) = read_diagnostic(loop, rejected["diagnostic_file"]).attempts
    assert (rejected["agent"], attempt.cause) == ("alpha", "connection")


def test_rerun_keeps_a_diagnostic_for_each_request(loop: Any, env: Any) -> None:
    # 同じサイクルの再実行でも、1 回目（replaced）と再実行のそれぞれの request に診断が残る
    run_dir = started_cycle(loop, env)
    adapter = env.reviewers({"alpha": "success", "beta": "failed"})
    loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
    loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)

    cycle = loop.load_cycles(run_dir)[-1]
    first = cycle.review.rerun.replaced[0]
    second = next(entry for entry in cycle.review.reviewers if entry.actual_agent == "beta")
    assert sorted([Path(first.diagnostic_file), Path(second.diagnostic_file)]) == sorted(
        (run_dir / "cycle-1" / "diagnostics").iterdir()
    )
    for entry in (first, second):
        diagnostic = read_diagnostic(loop, entry.diagnostic_file)
        assert (diagnostic.stage, [attempt.state for attempt in diagnostic.attempts]) == ("payload", ["success"])


@pytest.mark.parametrize(
    "unsaved",
    [
        False,
    ],
    ids=["saved"],
)
def test_all_failed_review_returns_the_diagnostics_to_the_controller(
    loop: Any, env: Any, capsys: pytest.CaptureFixture[str], unsaved: bool
) -> None:
    # 全員が失敗した（終了コード 6）ときも、診断のパスか保存できなかった理由を司令塔に返す（受け入れ条件 3）
    run_dir = started_cycle(loop, env)
    if unsaved:
        (run_dir / "cycle-1" / "diagnostics").write_text("not a directory", encoding="utf-8")
    failure = {"stderr": "Error: read ECONNRESET\n"}
    adapter = MixedReviewers(env.reviewers({}), {"alpha": failure, "beta": failure})

    with pytest.raises(loop.LoopError) as error:
        loop.review(run_dir, github=env.github, adapter_loader=adapter, tmp_root=env.tmp_root)
    assert error.value.code == 6
    # CLI の出力。2 回目の review はレビュアーを起動せず、同じ失敗を返す
    assert loop.main(["review", "--run", str(run_dir)]) == 6

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "error"
    rejected = {item["agent"]: item for item in output["rejected"]}
    assert sorted(rejected) == ["alpha", "beta"]
    for item in rejected.values():
        if unsaved:
            assert (item["diagnostic_file"], item["diagnostic_error"]) == (None, "診断を保存できない（EEXIST）")
        else:
            assert item["diagnostic_error"] is None
            (attempt,) = read_diagnostic(loop, item["diagnostic_file"]).attempts
            assert attempt.cause == "connection"
