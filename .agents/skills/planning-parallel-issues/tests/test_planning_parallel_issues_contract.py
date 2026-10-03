from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/planning-parallel-issues"
SKILL = SKILL_DIR / "SKILL.md"
VALIDATION = SKILL_DIR / "evals/validation.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_boards_target_the_issues_of_this_repository() -> None:
    # Spec 8.2: the skill works on usaturn/create-reso-world Issues.
    content = read(SKILL)
    target = content.split("## Target repository", 1)[1].split("\n## ", 1)[0]
    assert "`usaturn/create-reso-world`" in target
    assert "git remote get-url origin" in target
    assert "`{owner}/{repo}`" in target
    assert "repository boundary table in the root `AGENTS.md`" in target


def test_referenced_procedures_exist() -> None:
    links = re.findall(r"\]\((references/[^)]+)\)", read(SKILL))
    assert links
    for link in links:
        assert (SKILL_DIR / link).is_file(), link


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/planning-parallel-issues"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/planning-parallel-issues"


def test_validation_record_lists_only_checks_that_exist_here() -> None:
    assert "scripts/ci/" not in read(VALIDATION)


def test_children_may_target_other_repositories_but_documents_stay_here() -> None:
    target = read(SKILL).split("## Target repository", 1)[1].split("\n## ", 1)[0]
    assert "exact identifier" in target
    assert "`CODE_ROOT`" in target
    assert "Stop instead of guessing for any other repository." not in target
    workflow = read(SKILL_DIR / "references/session-workflow.md")
    artifacts = workflow.split("## Required artifact set", 1)[1].split("\n## ", 1)[0]
    assert "`usaturn/create-reso-world`" in artifacts
    assert "scripts/superpowers-review-copy.sh" in artifacts
    assert "viewing aid" in artifacts
