from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/agent-handoff"
SCHEMA = SKILL_DIR / "references/handoff-schema.md"

# Required authored schema keys prevent the receiver from losing decisions or boundaries.
AUTHORED_FIELDS = ("decisions", "out_of_scope", "verification", "landing")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def json_field_definition(key: str) -> str:
    """Read a JSON group by its machine key, not the prose heading above it."""
    definition = re.search(rf"^- `{key}`:\n(.*?)(?=^- `|^## |\Z)", read(SCHEMA), re.M | re.S)
    assert definition is not None, f"schema lacks the {key} field definition"
    return definition.group(1)


def test_schema_documents_the_authored_fields() -> None:
    # Schema keys are a machine interface: dropping an authored field loses facts.
    definitions = set(re.findall(r"^- `([a-z_]+)`:", read(SCHEMA), re.M))
    assert set(AUTHORED_FIELDS) <= definitions


def test_schema_maps_review_fix_planning_hold_to_deferred() -> None:
    # Bucket/enum compatibility prevents Hold from silently becoming Skip.
    mappings = dict(re.findall(r"^\s*\| (Fix|Hold|Skip|Resolved) \| `([a-z]+)` \|", read(SCHEMA), re.M))
    assert mappings == {"Fix": "fix", "Hold": "deferred", "Skip": "skip", "Resolved": "resolved"}


def test_schema_requires_git_branch_head_status_in_json_fields() -> None:
    # The parent checkout is often not where the work is; without these the
    # receiver acts on the wrong checkout. Find them by schema key, not prose.
    required = re.findall(r"^  - (.*?) \(required\):", json_field_definition("git"), re.M)
    fields = {field for row in required for field in re.findall(r"`([a-z_]+)`", row)}
    assert {"worktree", "branch", "head", "status"} <= fields


def test_documents_and_code_have_separate_schema_fields() -> None:
    # Documents and code may live in different checkouts; one shared field would
    # send commits to the wrong one.
    for group, fields in (
        ("sources", {"doc_root", "document_commit", "document_published", "review_copy"}),
        ("git", {"parent_checkout", "code"}),
    ):
        defined = set(re.findall(r"`([a-z_]+)`:", json_field_definition(group)))
        assert fields <= defined, f"{group}: missing {fields - defined}"
