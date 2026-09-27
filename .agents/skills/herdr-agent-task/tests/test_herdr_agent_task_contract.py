"""herdr-agent-task names its command by paths from the repository root (spec 8.2)."""
from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / ".agents/skills/herdr-agent-task/SKILL.md"
SCRIPT = REPO_ROOT / ".devcontainer/herdr-agent-task.bash"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_command_source_is_named_from_the_repository_root() -> None:
    content = read(SKILL)
    assert "`.devcontainer/herdr-agent-task.bash`" in content
    assert SCRIPT.is_file()
    # Works from a world project's directory too: the path starts at the toplevel.
    assert 'bash "$(git rev-parse --show-toplevel)/.devcontainer/herdr-agent-task.bash" set' in content
    assert "~/bin/herdr-agent-task" in content


def test_states_match_the_command() -> None:
    table = read(SKILL).split("## 状態の選び方", 1)[1].split("\n## ", 1)[0]
    documented = set(re.findall(r"^\| `([a-z]+)`", table, re.M))
    accepted = set(re.search(r"^\s+(working \| waiting[^)]*)\)", read(SCRIPT), re.M).group(1).replace(" ", "").split("|"))
    assert documented == accepted


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/herdr-agent-task"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/herdr-agent-task"
