"""Guard permission interpretation: a non-string allowed-tools can change tool access."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

SKILLS_ROOT = Path(__file__).resolve().parents[2] / ".agents" / "skills"


def frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert match, f"{path}: missing YAML frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict), f"{path}: frontmatter must be a mapping"
    return data


def test_allowed_tools_preserves_permission_type() -> None:
    skill_files = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
    assert skill_files, f"{SKILLS_ROOT}: no SKILL.md found"
    for path in skill_files:
        data = frontmatter(path)
        if "allowed-tools" in data:
            assert isinstance(data["allowed-tools"], str), f"{path.parent.name}: allowed-tools must be a comma-separated string"
