from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_SKILL = REPO_ROOT / ".agents/skills/monitoring-long-tasks/SKILL.md"
CLAUDE_SKILL = REPO_ROOT / ".claude/skills/monitoring-long-tasks/SKILL.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
RUNTIMES = REPO_ROOT / ".agents/monitoring-runtimes.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_runtime_skill_copies_are_byte_identical() -> None:
    assert AGENTS_SKILL.read_bytes() == CLAUDE_SKILL.read_bytes()


def test_claude_loads_the_shared_instructions() -> None:
    assert read(CLAUDE_MD).splitlines()[0] == "@AGENTS.md"


def test_runtime_instructions_do_not_reference_removed_scripts() -> None:
    for path in (AGENTS_SKILL, RUNTIMES):
        assert "scripts/ci/" not in read(path)
