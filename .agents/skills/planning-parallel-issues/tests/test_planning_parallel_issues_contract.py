from __future__ import annotations

import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/planning-parallel-issues"
SKILL = SKILL_DIR / "SKILL.md"
VALIDATION = SKILL_DIR / "evals/validation.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_referenced_procedures_exist() -> None:
    links = re.findall(r"\]\((references/[^)]+)\)", read(SKILL))
    assert links
    for link in links:
        assert (SKILL_DIR / link.split("#", 1)[0]).is_file(), link


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/planning-parallel-issues"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/planning-parallel-issues"


def test_validation_links_and_scenarios_resolve() -> None:
    content = read(VALIDATION)
    assert "scripts/ci/" not in content
    for link in re.findall(r"\]\(([^)]+)\)", content):
        target = link.split("#", 1)[0]
        if target and not target.startswith(("https:", "http:")):
            assert (VALIDATION.parent / target).is_file(), target
    payload = json.loads(read(SKILL_DIR / "evals/scenarios.json"))
    assert payload["skill_name"] == SKILL_DIR.name
    assert isinstance(payload["method"], dict)
    assert payload["scenarios"]
    for scenario in payload["scenarios"]:
        for key in ("id", "prompt"):
            assert isinstance(scenario[key], str) and scenario[key].strip()
        assert isinstance(scenario["expected"], list) and scenario["expected"]
        assert all(isinstance(value, str) and value.strip() for value in scenario["expected"])


def test_referenced_skills_and_commands_exist() -> None:
    names: set[str] = set()
    for source in (SKILL, SKILL_DIR / "references/session-workflow.md"):
        content = read(source)
        # A declared dependency list identifies skills; arbitrary backticked
        # prose such as read-only or fast-forward does not.
        for dependencies in re.findall(r"REQUIRED SUB-SKILLS:([^\n.]+)", content):
            names.update(name for name in re.findall(r"`([^`]+)`", dependencies)
                         if not name.startswith("superpowers:"))
        for chunk in re.findall(r"`([^`\n]+)`", content):
            for word in chunk.split():
                if word.startswith(("scripts/", "tests/", ".agents/")) and not any(char in word for char in "*<>$"):
                    assert (REPO_ROOT / word).exists(), word
    assert names, "skill has no declared local skill dependencies"
    for name in names:
        assert (REPO_ROOT / ".agents/skills" / name / "SKILL.md").is_file(), name
