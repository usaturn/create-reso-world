"""Guard permission interpretation: a non-string allowed-tools can change tool access."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SKILLS_ROOT = Path(__file__).resolve().parents[2] / ".agents" / "skills"
SKILL_FILES = sorted(SKILLS_ROOT.glob("*/SKILL.md"))


def frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert match, f"{path}: missing YAML frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict), f"{path}: frontmatter must be a mapping"
    return data


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
def test_allowed_tools_preserves_permission_type(path: Path) -> None:
    data = frontmatter(path)
    if "allowed-tools" in data:
        assert isinstance(data["allowed-tools"], str), f"{path.parent.name}: allowed-tools must be a comma-separated string"
