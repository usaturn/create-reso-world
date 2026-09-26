from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_SKILL = REPO_ROOT / ".agents/skills/review-fix-planning/SKILL.md"
AGENTS_HELPER = REPO_ROOT / ".agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"
REPO_CLEANUP_SKILLS = (REPO_ROOT / ".agents/skills/repo-cleanup-after-merge/SKILL.md",)


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
    assert "./scripts/ci/verify.sh full" in content
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


def test_helper_has_one_real_copy_shared_through_the_skill_symlinks() -> None:
    assert AGENTS_HELPER.is_file() and not AGENTS_HELPER.is_symlink()
    assert AGENTS_HELPER.stat().st_size > 0
    for name in ("review-fix-planning", "repo-cleanup-after-merge"):
        link = REPO_ROOT / ".claude/skills" / name
        assert link.is_symlink(), link
        assert os.readlink(link) == f"../../.agents/skills/{name}"


def test_pr_comment_lists_skipped_findings_without_spec_dependency() -> None:
    """Issue #235 A: no dangling reference to the gitignored Spec."""
    content = read(AGENTS_SKILL)
    assert "全件は Spec を参照" not in content
    spec_lines = [line for line in content.splitlines() if line.strip().startswith("- Spec:")]
    assert spec_lines, "the template must keep a Spec: line"
    assert any("gitignore" in line for line in spec_lines)
    assert "単体で読める" in content


def test_pr_posting_required_only_after_landing() -> None:
    """Issue #235 B: mandatory posting is limited to landing turns."""
    content = read(AGENTS_SKILL)
    assert "計画のみのセッションも投稿する" not in content
    assert "承認待ちで止まるターンは停止直前に1回" not in content
    assert "commit / push まで完了したターン" in content
    assert "任意" in content


def test_pr_comment_purpose_is_record_not_stall_relief() -> None:
    """Issue #235 C: the comment is only a durable record, not stall relief."""
    content = read(AGENTS_SKILL)
    assert "永続的な記録" in content
    assert "stall" in content.lower()
    assert "Monitor" in content


def test_skill_descriptions_do_not_advertise_pr_posting() -> None:
    """Issue #235 D: posting lives in the body section, not the description."""
    description = frontmatter_description(read(AGENTS_SKILL))
    assert "作業終了前の PR 投稿" not in description
    assert "Before finishing, post review status" not in description


def test_merged_skills_keep_claude_code_allowed_tools() -> None:
    for path in (AGENTS_SKILL, *REPO_CLEANUP_SKILLS):
        assert "allowed-tools:" in frontmatter_description(read(path)), path


def test_repo_cleanup_keeps_gh_failure_stop_and_user_confirmation() -> None:
    content = read(REPO_CLEANUP_SKILLS[0])
    assert "が非0終了した場合、PR の状態は不明である" in content
    assert "AskUserQuestion" in content


def test_review_fix_examples_distinguish_public_and_parent_prs() -> None:
    """Issue #377 F-3: the application example names usaturn/maatlog and
    resolves MAIN_ROOT to the public checkout; the environment example points
    to the parent. Both keep related tests, not a full verifier, as the
    commit/push gate."""
    for path in (AGENTS_SKILL,):
        content = read(path)
        assert re.search(r"usaturn/maatlog(?!-)", content), path
        assert "usaturn/maatlog-poc" in content, path
        assert "./scripts/ci/verify-devenv.sh" in content, path

        # Skill helpers live only in the parent repo; resolve via TOPLEVEL.
        assert '"$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"' in content, path
        assert '"$MAIN_ROOT/.agents/skills/review-fix-planning' not in content, path

        # The application-PR example names the public repo and the public
        # root, and never invokes the parent's verifier for it.
        example_lines = [line for line in content.splitlines() if line.lstrip().startswith(("Example:", "例:"))]
        assert example_lines, f"{path}: expected an example line"
        app_example = example_lines[0]
        assert re.search(r"usaturn/maatlog(?!-)", app_example), app_example
        assert "public/" in app_example, app_example
        assert "verify-devenv.sh" not in app_example, app_example

        # An environment-PR example points to the parent and names its verifier.
        env_lines = [
            line for line in content.splitlines() if "usaturn/maatlog-poc" in line and "verify-devenv.sh" in line
        ]
        assert env_lines, f"{path}: expected a parent-PR example"


def test_number_argument_searches_public_reviews_too() -> None:
    """Issue #377 review: public-PR review directories live under
    public/reviews/, so #<number> resolution must look there as well."""
    for path in (AGENTS_SKILL,):
        content = read(path)
        assert "public/reviews/" in content, path


def test_spec_location_stays_in_parent_docs_draft() -> None:
    """Issue #377 review: docs_draft/ is only gitignored in the parent repo;
    pinning Specs to $MAIN_ROOT would drop them unignored into public/."""
    for path in (AGENTS_SKILL,):
        content = read(path)
        assert "$MAIN_ROOT/docs_draft" not in content, path
        assert "$TOPLEVEL/docs_draft/superpowers/" in content, path


def test_repo_cleanup_selects_public_root_for_public_prs() -> None:
    """Issue #377 F-3: cleanup of a merged usaturn/maatlog PR runs inside the
    public/ checkout with gh calls pinned to the public repository."""
    for path in REPO_CLEANUP_SKILLS:
        content = read(path)
        assert re.search(r"usaturn/maatlog(?!-)", content), path
        assert "git -C public" in content, path
        assert "--repo usaturn/maatlog" in content, path
