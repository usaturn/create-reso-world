from __future__ import annotations

import json
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


def test_validation_links_and_scenarios_resolve() -> None:
    content = read(VALIDATION)
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


def test_explicit_path_and_skill_references_exist() -> None:
    references: set[Path] = set()
    for source in (SKILL, SKILL_DIR / "references/session-workflow.md"):
        content = read(source)
        # Untyped bare names in prose are ambiguous. Only path syntax and the
        # explicit skill invocation namespace identify resolvable local refs.
        for name in re.findall(r"/skill:([a-z0-9][a-z0-9-]*(?::[a-z0-9-]+)?)", content):
            if not name.startswith("superpowers:"):
                skill = REPO_ROOT / ".agents/skills" / name / "SKILL.md"
                assert skill.is_file(), name
                references.add(skill)
        for chunk in re.findall(r"`([^`\n]+)`", content):
            for word in chunk.split():
                if word.startswith(("scripts/", "tests/", ".agents/")) and not any(char in word for char in "*<>$"):
                    references.add(REPO_ROOT / word)
    assert references, "skill has no explicit local path or skill references"
    for reference in references:
        assert reference.exists(), reference.relative_to(REPO_ROOT)
