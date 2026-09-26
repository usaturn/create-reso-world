"""Guards against leftovers of the repository this environment was migrated from (spec 8.2, 11).

The migration source kept its application in a `public/` submodule and ran
`scripts/ci/verify.sh`. Neither exists here, so the skills that only made sense
there are removed, and no tracked file may send an agent looking for them.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Skills removed by spec 8.2, checked in every place a runtime looks for them.
REMOVED_SKILLS = ("repository-ownership",)

# Spec 11: no tracked file refers to the migration source, its public/
# submodule or its verify.sh. git grep narrows the candidates with fixed strings
# (the world projects hold large text meshes), then the patterns decide.
CANDIDATES = ("maatlog", "public/", "submodule", "-C public", "scripts/ci/verify", "verify.sh", "verify-devenv")
LEGACY = re.compile(
    r"maatlog|(^|[^a-z0-9_./-])public/|submodule.{0,20}public|-C public|scripts/ci/verify|verify\.sh|verify-devenv",
    re.IGNORECASE,
)
# The design records describe the migration itself, and these tests spell the
# words out to assert that they are gone.
EXCLUDED = (
    "docs/superpowers",
    ".devcontainer/test-cleanup-workspace.bash",
    ".devcontainer/test-readme.bash",
    "tests/scripts/test-instructions.bash",
    "tests/skills/test_legacy_references.py",
)


@pytest.mark.parametrize("name", REMOVED_SKILLS)
def test_removed_skill_is_gone_from_every_runtime(name: str) -> None:
    assert not (REPO_ROOT / ".agents/skills" / name).exists()
    link = REPO_ROOT / ".claude/skills" / name
    assert not link.is_symlink() and not link.exists()
    assert not (REPO_ROOT / ".cursor/rules" / f"{name}.mdc").exists()


def test_tracked_files_do_not_refer_to_the_migration_source() -> None:
    for path in EXCLUDED:
        assert (REPO_ROOT / path).exists(), f"stale exclusion: {path}"
    candidates = [arg for text in CANDIDATES for arg in ("-e", text)]
    excludes = [f":(exclude){path}" for path in EXCLUDED]
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "grep", "-I", "-n", "-i", "-F", *candidates, "--", ".", *excludes],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1), result.stderr
    # Each line is "<path>:<line number>:<text>"; only the text decides.
    hits = [line for line in result.stdout.splitlines() if LEGACY.search(line.split(":", 2)[2])]
    assert not hits, "tracked files still refer to the migration source:\n" + "\n".join(hits)
