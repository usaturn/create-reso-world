"""Guards against references to the repository this environment was migrated from (spec 11).

The migration source kept its application in a `public/` submodule and ran
`scripts/ci/verify.sh`. Neither exists here, and content is still ported from
that repository, so no tracked file may send an agent to its repository, its
submodule or its scripts: an agent following such an instruction would act on
the wrong target.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Spec 11: no tracked file refers to the migration source, its public/
# submodule or its verify.sh. git grep narrows the candidates with fixed strings
# (the world projects hold large text meshes), then the patterns decide.
CANDIDATES = ("maatlog", "public/", "submodule", "-C public", "scripts/ci/verify", "verify.sh", "verify-devenv")
LEGACY = re.compile(
    r"maatlog|(^|[^a-z0-9_-])public/|submodule.{0,20}public|-C public|scripts/ci/verify|verify\.sh|verify-devenv",
    re.IGNORECASE,
)
# The design records and the porting table of Issue #17 (which lists every
# file of the migration source) describe the migration itself, and this test
# spells the words out to assert that they are gone.
EXCLUDED = (
    "docs/superpowers",
    "docs/maatlog-poc-porting.md",
    "tests/skills/test_legacy_references.py",
)


def test_tracked_files_do_not_refer_to_the_migration_source() -> None:
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


# The repository has no hits, so only these cases show that the pattern can
# fire at all, and that it does not fire on look-alike paths.
@pytest.mark.parametrize(
    "text,should_match",
    [
        ("cd $TOPLEVEL/public/app.py", True),
        ("see external/public/README.md", True),
        ("./public/x", True),
        ("cd public/", True),
        ("the public/ submodule", True),
        ("republic/", False),
        ("my-public/", False),
        ("public_html/", False),
    ],
)
def test_legacy_regex_pattern(text: str, should_match: bool) -> None:
    assert bool(LEGACY.search(text)) is should_match, f"text={text!r} should_match={should_match}"
