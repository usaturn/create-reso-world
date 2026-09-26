"""find-docs is the canonical Context7 procedure (spec 5.2, 8.2).

The root AGENTS.md keeps only the three-command limit and points here, so the
rules it used to carry must live in this skill.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / ".agents/skills/find-docs/SKILL.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_cli_runs_through_npx_without_a_global_install() -> None:
    content = read(SKILL)
    assert "npx ctx7@latest <command>" in content
    assert "npm install -g" not in content


def test_skill_keeps_the_rules_agents_md_points_to() -> None:
    content = read(SKILL)
    for rule in (
        "Do not run these commands more than 3 times per question",
        "Do not use it for refactoring, business logic, or code review",
        "`/org/project`",
        "Do not silently fall back to training data",
    ):
        assert rule in content, rule
    agents = read(REPO_ROOT / "AGENTS.md")
    assert "find-docs" in agents
    assert "npx ctx7" not in agents


def test_api_key_goes_to_the_secrets_file_of_this_environment() -> None:
    content = read(SKILL)
    assert "npx ctx7@latest login" in content
    assert "`CONTEXT7_API_KEY`" in content
    assert "~/.config/create-reso-world/env" in content
    assert "export CONTEXT7_API_KEY" not in content


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/find-docs"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/find-docs"
