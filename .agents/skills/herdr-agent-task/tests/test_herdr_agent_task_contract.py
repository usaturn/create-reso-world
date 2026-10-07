"""State enum compatibility between the skill and its command."""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / ".agents/skills/herdr-agent-task/SKILL.md"
SCRIPT = REPO_ROOT / ".devcontainer/herdr-agent-task.bash"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_states_match_the_command() -> None:
    # The enum column is an interface; table headings and explanations are not.
    documented = set(re.findall(r"^\| `([a-z]+)`", read(SKILL), re.M))
    states = re.search(r"^\s+(working \| waiting[^)]*)\)", read(SCRIPT), re.M)
    assert states is not None, "command lacks the accepted state case"
    accepted = set(states.group(1).replace(" ", "").split("|"))
    assert documented == accepted
