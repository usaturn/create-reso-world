"""失敗したレビュアーの診断（#212）: ログを読む条件、原因の分類、回収の前の保存を確かめる。

ログは一時ファイルと偽の CLI だけで作り、実モデル・実 API・資格情報は使わない。保存した記録に、ログの文字列や
偽の秘密が入らないことも確かめる。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest

from tools.agent_runner.adapters import AdapterOutcome, Capabilities, LaunchSpec
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


# --- review の全体の経路（偽の CLI と偽の gh） --------------------------------------------------------------------

# stdout・stderr に書いて、指定の終了コードで終わる偽の CLI。receipt は書かない
FAILING_PROGRAM = r"""
import json, sys
spec = json.loads(sys.argv[1])
sys.stdout.write(spec["stdout"])
sys.stderr.write(spec["stderr"])
sys.exit(spec["exit"])
"""


class MixedReviewers:
    """failures の担当は FAILING_PROGRAM、ほかは conftest の偽のレビュアー（others）に任せる adapter。

    失敗させる担当の collect は、DSH のように adapter の中で分類を置き換えた形（state は response_failed、
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
        spec = {"stdout": failure.get("stdout", ""), "stderr": failure.get("stderr", ""), "exit": failure.get("exit", 1)}
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
        {"beta": {"stderr": f"HTTP 401 Unauthorized: token {secret} was rejected\n", "reported": "awaiting_authentication"}},
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
