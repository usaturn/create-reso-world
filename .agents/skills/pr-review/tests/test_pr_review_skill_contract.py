from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_SKILL = REPO_ROOT / ".agents/skills/pr-review/SKILL.md"
AGENTS_HELPER = REPO_ROOT / ".agents/skills/pr-review/scripts/pr_review_workspace.py"
CLAUDE_LINK = REPO_ROOT / ".claude/skills/pr-review"
BUDGET_REFERENCE = REPO_ROOT / ".agents/skills/pr-review/references/time-budget.md"


class ResolverStopped(Exception):
    """Raised when the skill resolver exits non-zero (fail-closed)."""

    def __init__(self, returncode: int, stderr: str) -> None:
        super().__init__(returncode, stderr)
        self.returncode = returncode
        self.stderr = stderr


class _RootPath:
    """Path-like root updated by the fixture; supports / and equality at runtime."""

    __slots__ = ("_parts",)

    def __init__(self, *parts: str) -> None:
        self._parts = parts

    def __truediv__(self, other: str | Path) -> _RootPath:
        return _RootPath(*self._parts, str(other))

    def _absolute(self) -> Path:
        base = _FixtureState.toplevel
        assert base is not None, "resolver_fixture must bind TOPLEVEL before resolve"
        return base.joinpath(*self._parts)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Path, _RootPath)):
            return NotImplemented
        left = self._absolute()
        right = other._absolute() if isinstance(other, _RootPath) else other
        return left == right

    def __hash__(self) -> int:
        return hash(self._parts)

    def __repr__(self) -> str:
        return f"TOPLEVEL.joinpath{self._parts!r}"


class _FixtureState:
    toplevel: Path | None = None


TOPLEVEL = _RootPath()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_resolver_script(skill_text: str) -> str:
    """Extract the MAIN_ROOT resolver bash block from a skill document."""
    pattern = re.compile(
        r"```bash\n("
        r"[ \t]*PR_URL=\$\(printf '%s' \"\$PR_JSON\" \| jq -r \.url\)\n"
        r"[ \t]*TOPLEVEL=\$\(git rev-parse --show-toplevel\)\n"
        r"[ \t]*github_repository\(\) \{.*?"
        r"[ \t]*fi\n"
        r")[ \t]*```",
        re.DOTALL,
    )
    match = pattern.search(skill_text)
    assert match is not None, "resolver bash block not found in skill"
    block = match.group(1)
    # Nested list markdown indents the fence body; strip a common indent.
    lines = block.splitlines()
    indents = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip()]
    common = min(indents) if indents else 0
    return "\n".join(line[common:] if len(line) >= common else line for line in lines) + "\n"


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", *args],
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
    )


def build_parent_with_public(tmp_path: Path) -> Path:
    """Create an isolated parent repo with a registered public submodule."""
    parent = tmp_path / "parent"
    parent.mkdir()
    _git(parent, "init")
    _git(parent, "commit", "--allow-empty", "-m", "init parent")
    _git(parent, "remote", "add", "origin", "https://github.com/owner/repository.git")

    public_src = tmp_path / "public_src"
    public_src.mkdir()
    _git(public_src, "init")
    (public_src / "README.md").write_text("public\n", encoding="utf-8")
    _git(public_src, "add", "README.md")
    _git(public_src, "commit", "-m", "init public")
    _git(public_src, "remote", "add", "origin", "https://github.com/usaturn/maatlog.git")

    # Local path submodule clones require protocol.file.allow on modern Git.
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=test",
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(public_src.resolve()),
            "public",
        ],
        cwd=parent,
        check=True,
        text=True,
        capture_output=True,
    )
    _git(
        parent,
        "config",
        "-f",
        ".gitmodules",
        "submodule.public.url",
        "https://github.com/usaturn/maatlog.git",
    )
    _git(
        parent / "public",
        "remote",
        "set-url",
        "origin",
        "https://github.com/usaturn/maatlog.git",
    )
    _git(parent, "add", ".gitmodules", "public")
    _git(parent, "commit", "-m", "register public submodule")
    return parent.resolve()


@dataclass
class ResolverFixture:
    toplevel: Path

    def resolve(self, pr_url: str, *, skill_path: Path) -> Path:
        script = extract_resolver_script(read(skill_path))
        pr_json = json.dumps({"url": pr_url})
        # Emit MAIN_ROOT after the skill block for the test harness.
        harness = f"""set -euo pipefail
PR_JSON={json.dumps(pr_json)}
{script}
printf '%s\\n' "$MAIN_ROOT"
"""
        completed = subprocess.run(
            ["bash", "-c", harness],
            cwd=self.toplevel,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ResolverStopped(completed.returncode, completed.stderr)
        main_root = completed.stdout.strip().splitlines()[-1]
        return Path(main_root).resolve()


@pytest.fixture
def resolver_fixture(tmp_path: Path) -> ResolverFixture:
    toplevel = build_parent_with_public(tmp_path)
    _FixtureState.toplevel = toplevel
    return ResolverFixture(toplevel=toplevel)


def assert_review_contract(content: str) -> None:
    # The user-supplied value is kept raw ($PR_ARG) so gh resolves a URL's
    # owner/repo itself; every later gh call is pinned to the canonical
    # $PR_URL so a foreign-repository URL cannot silently review the
    # same-numbered PR of the checkout's repository.
    assert 'gh pr view "$PR_ARG"' in content
    assert 'gh pr view "$PR_URL" --comments' in content
    assert 'gh pr diff "$PR_URL"' in content
    assert 'gh pr view "$PR_NUMBER"' not in content
    assert 'gh pr diff "$PR_NUMBER"' not in content
    # The helper lives in the parent repository's skill tree, so it must
    # resolve from $TOPLEVEL even when MAIN_ROOT points at public/.
    assert 'HELPER="$TOPLEVEL/' in content
    assert 'HELPER="$MAIN_ROOT/' not in content
    assert 'git rev-parse --short=12 "$PR_HEAD"' in content
    assert 'date -u +"%Y-%m-%dT%H:%M:%SZ"' in content
    assert "previous_review" in content
    assert "Review history" in content
    assert "Reviewed at (UTC)" in content
    assert "Initial" in content
    assert "Update" in content
    assert "検出時 HEAD" in content
    assert "Resolved findings" in content
    assert "解消確認時 HEAD" in content
    assert "不明（旧形式）" in content
    assert content.count("headRefOid") >= 3
    assert "他モデルのレビュー本文" in content
    assert "PR_URL=$(printf '%s' \"$PR_JSON\" | jq -r .url)" in content
    assert "github_repository()" in content
    assert 'MAIN_ROOT="$TOPLEVEL"' in content
    assert 'MAIN_ROOT="$TOPLEVEL/public"' in content
    assert "usaturn/maatlog" in content
    assert "submodule.public.url" in content
    assert "submodule status -- public" in content
    assert 'git -C "$TOPLEVEL" remote get-url origin' in content
    assert 'git -C "$TOPLEVEL/public" remote get-url origin' in content
    assert "unsupported PR repository" in content
    assert "#160-feature-issue-148-fail-fast" in content
    assert "reviews/#" in content
    assert "追跡パス" not in content
    assert "if printf '%s' \"$PR_URL\" | grep -q devenv; then" not in content
    assert 'MAIN_ROOT="$TOPLEVEL/devenv"' not in content
    assert 'MAIN_ROOT="$(pwd)"' not in content


def assert_skip_verify_sh_allows_other_verification_contract(content: str) -> None:
    # Review skips ./scripts/ci/verify.sh because implementation already
    # ran it and repeating it is too slow. Related pytest, REPL, and
    # minimal repro scripts remain allowed. helper verify is destination
    # fingerprinting, not the CI runner.
    assert "レビュー中に `./scripts/ci/verify.sh` を実行しない" in content
    assert "実装時に確認" in content
    assert "冗長" in content
    assert "3. **実行検証**" in content
    assert "関連する pytest" in content
    assert "REPL" in content
    assert "最小再現スクリプト" in content
    assert "helper の `verify`" in content
    assert "`CLAUDE.md` の検証プロファイル規定より優先する" in content
    assert "verify.sh が起動するテスト" not in content
    assert "動かして確かめることも行わない" not in content
    assert "プロジェクトのテストを実行しない" not in content
    assert "プロジェクトのテストコマンド" not in content
    assert "既存テストファイルは読むが実行しない" not in content
    assert "npm test" not in content


@pytest.mark.parametrize("skill", [AGENTS_SKILL])
def test_pr_review_skills_define_review_update_contract(skill: Path) -> None:
    assert_review_contract(read(skill))


@pytest.mark.parametrize("skill", [AGENTS_SKILL])
def test_pr_review_skills_skip_verify_sh_and_allow_other_verification(skill: Path) -> None:
    assert_skip_verify_sh_allows_other_verification_contract(read(skill))


def assert_cleanup_contract(content: str) -> None:
    assert 'cleanup --state "$STATE_FILE"' in content
    assert "セッションディレクトリ" in content
    assert "レビュー本文の「根拠」に転記" in content
    assert "削除は helper の `cleanup` だけが行う" in content
    # The "no $WT paths in the final response" rule must stay scoped to a
    # successful cleanup; on the stop-unconfirmed branch $WT still exists and
    # its full path must be reported.
    assert "`cleanup` 成功後は `$WT` 配下のパスは既に存在しないため案内に含めない" in content
    # Cleanup must stay gated on a verified save and must never be hand-rolled.
    assert "worktree、session state、外部バックアップを自動削除しない" not in content
    assert "残した worktree の完全パス" not in content
    assert "最終応答後も削除しない" not in content


@pytest.mark.parametrize("skill", [AGENTS_SKILL])
def test_pr_review_skills_require_session_cleanup(skill: Path) -> None:
    assert_cleanup_contract(read(skill))


def test_helper_has_one_real_copy_shared_through_the_skill_symlink() -> None:
    assert AGENTS_HELPER.is_file() and not AGENTS_HELPER.is_symlink()
    assert AGENTS_HELPER.stat().st_size > 0
    assert CLAUDE_LINK.is_symlink()
    assert os.readlink(CLAUDE_LINK) == "../../.agents/skills/pr-review"
    assert not (REPO_ROOT / ".devin/skills").exists()


def test_skill_interpolation_is_limited_to_the_target_line() -> None:
    content = read(AGENTS_SKILL)
    # Claude Code and Devin replace $ARGUMENTS and $0-$9 in the body with the
    # invocation arguments. Only the target-PR line may carry $ARGUMENTS, and
    # embedded shell code must not use positional parameters.
    assert content.count("$ARGUMENTS") == 1
    assert "対象 PR（スキル呼び出しの引数）: $ARGUMENTS" in content
    assert re.search(r"\$[0-9]", content) is None


def test_skill_keeps_claude_code_permissions_consistent() -> None:
    content = read(AGENTS_SKILL)
    head = content.split("---", 2)[1]
    assert "allowed-tools:" in head
    assert "Bash(date *)" in head
    assert "Edit(/tmp/pr-review-*/review-backup/**)" in head
    assert 'argument-hint: "<PR番号またはURL>"' in head
    assert '--model-name "$MODEL_NAME"' in content
    assert "CODEX_THREAD_ID" in content
    create_lines = [line for line in content.splitlines() if '"$HELPER" create' in line]
    assert len(create_lines) >= 2
    for line in create_lines:
        # allowed-tools only permits Edit/Write under /tmp/pr-review-*, so every
        # runtime pins the helper's temp root there.
        assert "--temp-root /tmp" in line, line


def test_skill_keeps_runtime_specific_notes() -> None:
    content = read(AGENTS_SKILL)
    assert "## ランタイム別の注意" in content
    for heading in ("### 対象 PR の受け取り", "### Claude Code", "### Codex", "### Devin", "### pi"):
        assert heading in content
    assert "You are powered by" in content
    assert "pi-model-name" in content


@pytest.mark.parametrize("skill_path", [AGENTS_SKILL])
@pytest.mark.parametrize(
    ("pr_url", "expected_root"),
    [
        ("https://github.com/owner/repository/pull/1", TOPLEVEL),
        ("https://github.com/usaturn/maatlog/pull/2", TOPLEVEL / "public"),
    ],
)
def test_pr_review_resolver_selects_only_registered_repositories(
    skill_path: Path,
    pr_url: str,
    expected_root: Path,
    resolver_fixture: ResolverFixture,
) -> None:
    assert resolver_fixture.resolve(pr_url, skill_path=skill_path) == expected_root


@pytest.mark.parametrize("skill_path", [AGENTS_SKILL])
def test_pr_review_resolver_stops_for_unknown_repository(skill_path: Path, resolver_fixture: ResolverFixture) -> None:
    with pytest.raises(ResolverStopped):
        resolver_fixture.resolve(
            "https://github.com/other/repository/pull/3",
            skill_path=skill_path,
        )


@pytest.mark.parametrize("forbidden", ["$TOPLEVEL/devenv", "submodule status -- devenv"])
def test_pr_review_skills_have_no_legacy_path_selection(forbidden: str) -> None:
    for skill in (AGENTS_SKILL,):
        assert forbidden not in skill.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("skill", "relative"),
    [(AGENTS_SKILL, "references/time-budget.md")],
)
def test_review_budget_reference_is_required_and_resolves(skill: Path, relative: str) -> None:
    content = read(skill)
    assert f"[時間予算と委譲規約]({relative})" in content
    assert "最初の PR API 呼び出しより前に全文を読む" in content
    assert (skill.parent / relative).resolve() == BUDGET_REFERENCE.resolve()
    assert BUDGET_REFERENCE.is_file()
    assert "0. **時間予算の開始**" in content


def test_review_budget_has_fixed_deadlines_and_safe_fallback() -> None:
    content = read(BUDGET_REFERENCE)
    for required in (
        "全体 45 分",
        "開始 40 分",
        "予約枠は 5 分",
        "起動時刻 + 10分",
        "実質進捗から 5 分",
        "300 行以下",
        "3 個以下",
        "進捗があっても延長しない",
        "停止確認",
        "再委譲",
        "最大 1 件",
        "停止手段を利用できなければ委譲を省略する",
        "同期起動のみのランタイムでは委譲しない",
        "呼び出し元・呼び出し先",
        "指摘の根拠となる精読をサブエージェント任せにしない",
        "サブエージェントの報告のみを根拠に【検証済み】を付けない",
        "停止確認不能なら cleanup を省略する",
        "未検証",
        "実時間保証ではない",
        "応答本文へ逐次記し",
        "重要な未検証候補",
        "未再検証の過去指摘",
        "差分の実質的な未読箇所",
    ):
        assert required in content
    assert (
        content.index("`Request changes`") < content.index("`Needs manual verification`") < content.index("`Approve`")
    )


@pytest.mark.parametrize("skill", [AGENTS_SKILL])
def test_pr_review_skills_keep_delegation_optional_and_readonly(skill: Path) -> None:
    content = read(skill)
    assert "読み取り専用の補助委譲として" in content
    assert "起動してよい" in content
    assert "並行して起動する" not in content


@pytest.mark.parametrize("skill", [AGENTS_SKILL])
def test_incomplete_reviews_preserve_pending_and_gate_approval(skill: Path) -> None:
    content = read(skill)
    for section in (
        "Review coverage",
        "Unverified candidates",
        "Pending previous findings",
        "Review timing",
    ):
        assert section in content
    for rule in (
        "未再検証の指摘を Resolved にしない",
        "次回更新で Pending previous findings も再検証する",
        "active / pending / resolved 全体で ID の衝突を避ける",
        "確認不足判定は coverage と pending も参照する",
        "停止確認不能なら cleanup を省略する",
        "重要な未検証候補",
        "未再検証の過去指摘",
        "差分の実質的な未読箇所",
    ):
        assert rule in content
    assert (
        content.index("**Request changes**")
        < content.index("**Needs manual verification**")
        < content.index("**Approve**")
    )


def test_timing_separates_observation_from_runtime_measurement() -> None:
    content = read(BUDGET_REFERENCE)
    for required in (
        "turn_duration",
        "durationMs",
        "tool_use",
        "tool_result",
        "モデル応答までの観測間隔",
        "ツール実時間は不明",
        "ターン外時間",
        "和集合",
        "並行した区間を総時間へ加算しない",
        "出力しない",
        "未完の末尾行",
        "save/cleanup",
        "最終応答",
        "600 秒以下",
        "2700 秒以下",
    ):
        assert required in content
