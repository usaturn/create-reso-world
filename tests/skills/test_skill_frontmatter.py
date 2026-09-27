"""Frontmatter guards for every shared skill under .agents/skills (spec 8.1).

pi validates `name` and `description` against the Agent Skills spec (description up
to 1024 characters) and ignores other keys. Claude Code reads `allowed-tools` as a
comma-separated string. A merged skill that breaks either rule silently drops out of
one runtime, so every shared skill is checked here.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SKILLS_ROOT = Path(__file__).resolve().parents[2] / ".agents" / "skills"
SKILL_FILES = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_DESCRIPTION = 1024


def frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert match, f"{path}: missing YAML frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict), f"{path}: frontmatter must be a mapping"
    return data


def test_shared_skills_are_discovered() -> None:
    assert len(SKILL_FILES) >= 10


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
def test_frontmatter_is_valid_for_every_runtime(path: Path) -> None:
    data = frontmatter(path)
    name = data.get("name")
    assert name == path.parent.name
    assert isinstance(name, str) and NAME_PATTERN.match(name) and len(name) <= 64
    description = data.get("description")
    assert isinstance(description, str) and description.strip()
    assert len(description) <= MAX_DESCRIPTION, f"{name}: description has {len(description)} characters"
    if "allowed-tools" in data:
        assert isinstance(data["allowed-tools"], str), f"{name}: allowed-tools must be a comma-separated string"


def test_every_skill_directory_has_a_skill_file() -> None:
    for directory in sorted(p for p in SKILLS_ROOT.iterdir() if p.is_dir()):
        if directory.name == "references":
            continue
        assert (directory / "SKILL.md").is_file(), directory
