from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_SKILL = REPO_ROOT / ".agents/skills/review-fix-planning/SKILL.md"
AGENTS_HELPER = REPO_ROOT / ".agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"
EVALS = REPO_ROOT / ".agents/skills/review-fix-planning/evals/evals.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter_description(content: str) -> str:
    """Return the YAML frontmatter block (between the first two --- lines)."""
    parts = content.split("---")
    if len(parts) < 3:
        return ""
    return parts[1]


def assert_shared_landing_contract(content: str) -> None:
    """Landing recipe both runtimes must state, after an approved implementation."""
    lowered = content.lower()
    assert "commit" in lowered
    assert "push" in lowered
    # The gate depends on what changed: environment, skills, a world project, the fork.
    landing = content.split("## 実装後", 1)[1].split("## 作業終了前の PR 投稿", 1)[0]
    gate = landing.split("2. **変更の種類に応じた検証**", 1)[1].split("\n3. ", 1)[0]
    for check in (
        "`bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh`",
        "`uv run pytest tests/skills .agents/skills`",
        "そのプロジェクトのディレクトリで `uv run pytest`",
        "変更したプロジェクトに関連する `dotnet test`",
    ):
        assert check in gate, check
    assert "scripts/resoloop-fork.sh test" in landing
    assert "finishing-a-development-branch" in content
    assert "upsert_pr_comment.py" in content
    assert "<!-- review-fix-planning:agent:" in content
    assert "### レビュー状況" in content
    assert "### 作業判断" in content
    assert "### 作業結果" in content
    assert "--edit-last" in content
    assert_status_comment_snippet(content)


def assert_status_comment_snippet(content: str) -> None:
    """The posting snippet is run verbatim, so it must survive an unquoted heredoc."""
    # Bare backticks inside <<EOF would run the branch name as a command.
    assert "\\`$HEAD_BRANCH\\`" in content
    assert "\\`$HEAD_SHA\\`" in content
    assert "（`$HEAD_BRANCH`）" not in content
    assert ": `$HEAD_SHA`" not in content
    # The repository is passed explicitly; a PR number alone is ambiguous.
    assert '--repo "$PR_REPO"' in content


def assert_japanese_landing_contract(content: str) -> None:
    assert_shared_landing_contract(content)
    assert "実装に関連したテスト" in content
    assert "既存 PR" in content
    assert "新しい PR を開かない" in content
    assert "承認を得て停止する" in content
    assert "作業終了前の PR 投稿" in content


def assert_japanese_number_argument_contract(content: str) -> None:
    assert "#<番号>" in content
    assert "reviews/" in content
    assert "直下" in content
    assert "開始" in content
    body = content.split("---", 2)[2]
    assert "`#<番号>-`" in body
    assert "1 件" in content
    assert "複数" in content


def test_agents_skill_resolves_number_argument_to_reviews_dir() -> None:
    assert_japanese_number_argument_contract(read(AGENTS_SKILL))


def test_agents_skill_lands_on_existing_pr_after_related_tests() -> None:
    assert_japanese_landing_contract(read(AGENTS_SKILL))


def test_helper_has_one_real_copy_shared_through_the_skill_symlink() -> None:
    assert AGENTS_HELPER.is_file() and not AGENTS_HELPER.is_symlink()
    assert AGENTS_HELPER.stat().st_size > 0
    link = REPO_ROOT / ".claude/skills/review-fix-planning"
    assert link.is_symlink(), link
    assert os.readlink(link) == "../../.agents/skills/review-fix-planning"


def test_pr_comment_lists_skipped_findings_without_spec_dependency() -> None:
    """The comment stands alone; an uncommitted Spec exists only locally."""
    content = read(AGENTS_SKILL)
    assert "全件は Spec を参照" not in content
    spec_lines = [line for line in content.splitlines() if line.strip().startswith("- Spec:")]
    assert spec_lines, "the template must keep a Spec: line"
    assert any("ローカルにしか無い" in line for line in spec_lines)
    assert "単体で読める" in content


def test_pr_posting_required_only_after_landing() -> None:
    """Mandatory posting is limited to landing turns."""
    content = read(AGENTS_SKILL)
    assert "計画のみのセッションも投稿する" not in content
    assert "承認待ちで止まるターンは停止直前に1回" not in content
    assert "commit / push まで完了したターン" in content
    assert "任意" in content


def test_pr_comment_purpose_is_record_not_stall_relief() -> None:
    """The comment is only a durable record, not stall relief."""
    content = read(AGENTS_SKILL)
    assert "永続的な記録" in content
    assert "stall" in content.lower()
    assert "Monitor" in content


def test_skill_descriptions_do_not_advertise_pr_posting() -> None:
    """Posting lives in the body section, not the description."""
    description = frontmatter_description(read(AGENTS_SKILL))
    assert "作業終了前の PR 投稿" not in description
    assert "Before finishing, post review status" not in description


def test_allowed_tools_match_the_verification_and_spec_location() -> None:
    tools = yaml.safe_load(frontmatter_description(read(AGENTS_SKILL)))["allowed-tools"]
    assert isinstance(tools, str)
    for entry in (
        "Bash(uv run *)",
        "Bash(bash .devcontainer/run-tests.bash*)",
        "Bash(bash scripts/check-layout.sh*)",
        "Bash(bash tests/scripts/*)",
        "Bash(bash scripts/superpowers-review-copy.sh*)",
        "Write(docs/superpowers/specs/**)",
        "Edit(docs/superpowers/specs/**)",
    ):
        assert entry in tools, entry
    assert "scripts/ci/" not in tools
    assert "docs_draft" not in tools


def test_review_fix_examples_cover_this_repository_and_the_fork() -> None:
    """MAIN_ROOT follows the repository boundary table; the gate is the
    change-specific checks, not every suite."""
    content = read(AGENTS_SKILL)
    # Skill helpers live only in this repository; resolve via TOPLEVEL.
    assert '"$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"' in content
    assert '"$MAIN_ROOT/.agents/skills/review-fix-planning' not in content
    assert "リポジトリ境界" in content
    assert "scripts/resoloop-fork.sh clone" in content

    example_lines = [line for line in content.splitlines() if line.lstrip().startswith("例:")]
    assert example_lines, "expected an example line"
    example = example_lines[0]
    assert "usaturn/create-reso-world" in example
    assert "bash .devcontainer/run-tests.bash" in example
    assert "bash scripts/check-layout.sh" in example

    fork_lines = [
        line for line in content.splitlines() if "orange3134/resoloop" in line and "scripts/resoloop-fork.sh test" in line
    ]
    assert fork_lines, "expected a fork example"
    assert "$TOPLEVEL/external/resoloop" in fork_lines[0]


def test_number_argument_searches_the_fork_reviews_too() -> None:
    """pr-review saves resoloop PR reviews under external/resoloop/reviews/."""
    section = read(AGENTS_SKILL).split("## 第1引数の解決", 1)[1].split("## 手順", 1)[0]
    scope = next(line for line in section.splitlines() if "ディレクトリだけを見る" in line)
    assert "`reviews/`" in scope
    assert "`external/resoloop/reviews/`" in scope


def test_spec_goes_to_docs_superpowers_specs_of_this_repository() -> None:
    content = read(AGENTS_SKILL)
    # DOC_ROOT may be a separate checkout of the document branch; the spec is
    # written where it is committed, not in the parent checkout (TOPLEVEL).
    assert "$DOC_ROOT/docs/superpowers/specs/" in content
    assert "$TOPLEVEL/docs/superpowers/specs/" not in content
    assert "$MAIN_ROOT/docs" not in content
    assert "docs_draft" not in content
    step6 = content.split("6. **Spec を書く**", 1)[1].split("7. **", 1)[0]
    assert "`DOC_ROOT`" in step6


def test_landing_eval_uses_the_change_specific_gate() -> None:
    evals = {item["id"]: item for item in json.loads(read(EVALS))["evals"]}
    landing = evals[5]
    assert any(
        "bash .devcontainer/run-tests.bash" in item and "bash scripts/check-layout.sh" in item
        for item in landing["expectations"]
    )
    assert "scripts/ci/" not in json.dumps(landing, ensure_ascii=False)


def test_other_repositories_need_an_explicit_code_root() -> None:
    step2 = read(AGENTS_SKILL).split("2. **現行 HEAD を特定する**", 1)[1].split("3. **", 1)[0]
    assert "`CODE_ROOT`" in step2
    assert "推測せず停止する" in step2
    assert "pr-review" in step2


def test_spec_is_committed_and_copied_before_approval() -> None:
    content = read(AGENTS_SKILL)
    section = content.split("## Spec のコミットと確認用コピー", 1)[1].split("\n## ", 1)[0]
    for phrase in (
        "`DOC_ROOT`",
        "`PARENT_ROOT`",
        "bash scripts/superpowers-review-copy.sh",
        "--replace-from",
        "文書用ブランチ",
        "文書専用 PR",
        "公開未実施",
    ):
        assert phrase in section, phrase
    step7 = content.split("7. **承認を得て停止する**", 1)[1].split("\n## ", 1)[0]
    assert "## Spec のコミットと確認用コピー" not in step7
    assert "確認用コピー" in step7


def test_fork_pr_push_target_is_confirmed_for_other_repositories() -> None:
    landing = read(AGENTS_SKILL).split("## 実装後", 1)[1].split("\n## ", 1)[0]
    assert "head リポジトリ" in landing
    assert "headRepository" in landing
