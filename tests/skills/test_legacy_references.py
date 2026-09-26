"""Guards against leftovers of the repository this environment was migrated from (spec 8.2, 11).

The migration source kept its application in a `public/` submodule and ran
`scripts/ci/verify.sh`. Neither exists here, so the skills that only made sense
there are removed, and no runtime may still discover them.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Skills removed by spec 8.2, checked in every place a runtime looks for them.
REMOVED_SKILLS = ("repository-ownership",)


@pytest.mark.parametrize("name", REMOVED_SKILLS)
def test_removed_skill_is_gone_from_every_runtime(name: str) -> None:
    assert not (REPO_ROOT / ".agents/skills" / name).exists()
    link = REPO_ROOT / ".claude/skills" / name
    assert not link.is_symlink() and not link.exists()
    assert not (REPO_ROOT / ".cursor/rules" / f"{name}.mdc").exists()
