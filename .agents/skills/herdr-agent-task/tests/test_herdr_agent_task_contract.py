"""Command availability, state enum compatibility, and runtime packaging."""
from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / ".agents/skills/herdr-agent-task/SKILL.md"
SCRIPT = REPO_ROOT / ".devcontainer/herdr-agent-task.bash"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_command_script_exists() -> None:
    assert SCRIPT.is_file()


def test_states_match_the_command() -> None:
    # The enum column is an interface; table headings and explanations are not.
    documented = set(re.findall(r"^\| `([a-z]+)`", read(SKILL), re.M))
    accepted = set(re.search(r"^\s+(working \| waiting[^)]*)\)", read(SCRIPT), re.M).group(1).replace(" ", "").split("|"))
    assert documented == accepted


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/herdr-agent-task"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/herdr-agent-task"
