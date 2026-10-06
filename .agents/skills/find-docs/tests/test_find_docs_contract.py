"""Shared-instruction separation and runtime packaging for find-docs."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_common_instructions_do_not_embed_tool_specific_commands() -> None:
    # Tool-specific CLI instructions belong in the skill, not shared instructions.
    assert "npx ctx7" not in read(REPO_ROOT / "AGENTS.md")


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/find-docs"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/find-docs"
