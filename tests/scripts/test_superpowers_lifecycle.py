"""Frozen-history and continuation-gate checks for the document lifecycle of PR #16.

Imported historical documents are guarded by fixed SHA-256 values captured
from commit 58c9ea8; running the check does not require that Git history.
The continuation-gate check fixes the dispositions that keep a receiver from
executing unapproved or unauthorized work.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".agents/skills/agent-handoff/references/handoff-schema.md"

IMPORT_HASHES = ROOT / "tests/scripts/fixtures/superpowers-imported-documents.sha256.json"
IMPORTED = [
    "docs/superpowers/plans/2026-09-30-list-shrink-recreate-round6-review-fixes.md",
    "docs/superpowers/plans/2026-10-02-pr9-list-shrink-round2-review-fixes.md",
    "docs/superpowers/plans/2026-10-03-pr9-list-shrink-round3-review-fixes.md",
    "docs/superpowers/specs/2026-09-29-asset-url-save-migration-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-asset-url-save-migration-round2-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-asset-url-save-migration-round3-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-list-shrink-recreate-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-list-shrink-recreate-round2-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-list-shrink-recreate-round3-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-slot-snapshot-dedup-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-29-slot-snapshot-dedup-round2-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round4-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round5-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round6-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round7-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round8-review-fixes-design.md",
    "docs/superpowers/specs/2026-09-30-list-shrink-recreate-round9-review-fixes-design.md",
    "docs/superpowers/specs/2026-10-02-pi-gpt-6.1-sol-review-fixes-design.md",
    "docs/superpowers/specs/2026-10-02-pr8-round7-review-fixes-design.md",
    "docs/superpowers/specs/2026-10-02-pr9-list-shrink-review-fixes-design.md",
    "docs/superpowers/specs/2026-10-02-pr9-list-shrink-round2-review-fixes-design.md",
    "docs/superpowers/specs/2026-10-03-pr9-list-shrink-round3-review-fixes-design.md",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class LifecycleInstructionTests(unittest.TestCase):
    """Continuation gates and immutable history."""

    def test_continuation_gates_keep_unapproved_or_unauthorized_resumes_blocked(self):
        # A receiver decides whether to resume from this table. Turning one of these
        # cases into "ready" lets it implement changes nobody approved or authorized.
        # Rows are found by the machine case key; only the disposition is fixed.
        rows = {cells[0].strip(): cells[-1].strip()
                for line in read(SCHEMA).splitlines() if line.startswith("| ")
                for cells in [line.strip().strip("|").split("|")]}
        for case in ("substantive-unapproved", "missing-authority", "unsupported-route",
                     "closed-plan", "legacy-v2-missing-facts"):
            with self.subTest(case=case):
                self.assertIn(case, rows, f"continuation gates lack the {case} case")
                self.assertEqual(rows[case].split(";", 1)[0], "blocked / not ready")

    def test_imported_documents_are_unchanged_since_import(self):
        expected = json.loads(read(IMPORT_HASHES))
        self.assertEqual(set(expected), set(IMPORTED), "import baseline must cover exactly the historical document inventory")
        for rel in IMPORTED:
            with self.subTest(document=rel):
                self.assertEqual(expected[rel], hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), rel)


if __name__ == "__main__":
    unittest.main()
