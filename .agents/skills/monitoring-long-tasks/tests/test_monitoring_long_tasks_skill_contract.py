from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_SKILL = REPO_ROOT / ".agents/skills/monitoring-long-tasks/SKILL.md"
CLAUDE_SKILL = REPO_ROOT / ".claude/skills/monitoring-long-tasks/SKILL.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
RUNTIMES = REPO_ROOT / ".agents/monitoring-runtimes.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_runtime_skill_copies_are_byte_identical() -> None:
    assert AGENTS_SKILL.read_bytes() == CLAUDE_SKILL.read_bytes()


def test_controller_owns_the_wait_and_stall_polling() -> None:
    content = read(AGENTS_SKILL)
    assert "The controller owns this wait and stall polling" in content
    assert "keeps its turn until `report exists OR worker is not alive` resolves" in content
    assert "not permission to end the controller's turn while the worker is alive" in content


def test_completion_notification_has_a_narrow_scope() -> None:
    content = read(AGENTS_SKILL)
    assert "process-exit notification carrying an exit status" in content
    assert "not a report, artifact, or sub-agent result" in content


def test_agents_md_matches_the_controller_rule() -> None:
    content = read(AGENTS_MD)
    assert "終了条件が成立するまでターンを保持し、stall ポーリングを担当する" in content
    assert "終了コード付きプロセス終了通知" in content
    assert "成果物やサブエージェントの結果通知とは区別する" in content
    assert "対象の実行中にターンを終える根拠にしない" in content
    assert (
        "PR レビュー委譲の期限・無進捗打ち切りに限り、停止確認不能のときは"
        "委譲対象・停止状態・残存パスを報告してターンを終えてよい" in content
    )
    assert "実装サブエージェントはテスト、lint、回帰を同期実行し、完了を待ってからターンを終える" in content
    assert read(CLAUDE_MD).splitlines()[0] == "@AGENTS.md"


def test_skill_remains_runtime_neutral_for_issue_237() -> None:
    content = read(AGENTS_SKILL)
    # Contingency 2026-09-10: "Monitor" matches generic English already in
    # the skill ("Monitoring Long Tasks" title, "Monitor the log path" step 5)
    # as a substring, so the plan's raw substring check can never pass.
    # Neutralize those pre-existing generic uses; any new runtime facility
    # mention still fails. Contract meaning (no #237 runtime mapping) unchanged.
    neutralized = content.replace("Monitoring Long Tasks", "").replace("Monitor the log path", "the log path")
    for runtime_term in ("Monitor", "run_in_background", "BashOutput", "AwaitShell"):
        assert runtime_term not in neutralized


def test_review_deadline_exception_is_predeclared_and_narrow() -> None:
    content = read(AGENTS_SKILL)
    for required in (
        "## Predeclared PR review delegation deadlines",
        "read-only PR review delegation",
        "before dispatch",
        "target identity",
        "cancellation",
        "deadline",
        "does not apply to verification commands or implementation workers",
        "do not remove its worktree",
        "unconfirmed cancellation",
    ):
        assert required in content


def test_liveness_rules_cover_any_command_that_prints_its_log() -> None:
    # Spec 8.2: the PID and log rules no longer name one verification script.
    content = read(AGENTS_SKILL)
    for rule in (
        "When the command prints its log path and the log name ends with its PID",
        "`ps -p <pid> -o args=` contains the intended command",
        "`readlink -f /proc/<pid>/cwd` equals the target worktree",
        "apply step 3's command and cwd identity check to each remaining PID",
        "Monitor the log path the command prints",
    ):
        assert rule in content, rule


def test_runtime_table_uses_the_generic_log_rules() -> None:
    content = read(RUNTIMES)
    assert "ログ名からの PID 導出" in content
    assert "ログ path を印字するコマンドはその path を使い" in content
    for path in (AGENTS_SKILL, RUNTIMES):
        assert "scripts/ci/" not in read(path)
