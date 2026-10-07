from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/repo-cleanup-after-merge"
SKILL = SKILL_DIR / "SKILL.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_related_skills_exist() -> None:
    # Enumerate references across the document rather than under a prose heading.
    names = re.findall(r"^[ \t]*[-*+][ \t]+`([a-z0-9]+(?:-[a-z0-9]+)+)`", read(SKILL), re.M)
    assert names, "skill has no related skill references"
    for name in names:
        assert (REPO_ROOT / ".agents/skills" / name / "SKILL.md").is_file(), name


@pytest.mark.parametrize("skill_dir", [SKILL_DIR, REPO_ROOT / ".agents/skills/review-fix-planning"],
                         ids=lambda path: path.name)
def test_evals_have_valid_structure_and_existing_files(skill_dir: Path) -> None:
    # These two datasets share this schema; fixture paths stay relative to each
    # skill, not the file that happens to host the validation.
    payload = json.loads(read(skill_dir / "evals/evals.json"))
    assert payload["skill_name"] == skill_dir.name
    assert payload["evals"]
    for item in payload["evals"]:
        assert isinstance(item["id"], int)
        for field in ("name", "prompt", "expected_output"):
            assert isinstance(item[field], str) and item[field].strip()
        assert isinstance(item["expectations"], list) and item["expectations"]
        assert all(isinstance(value, str) and value.strip() for value in item["expectations"])
        assert isinstance(item["files"], list)
        for name in item["files"]:
            assert (skill_dir / name).is_file(), name
