from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/agent-handoff"
AGENTS_SKILL = SKILL_DIR / "SKILL.md"
CLAUDE_LINK = REPO_ROOT / ".claude/skills/agent-handoff"
SCHEMA = SKILL_DIR / "references/handoff-schema.md"
EVALS = SKILL_DIR / "evals/evals.json"
TRIGGERS = SKILL_DIR / "evals/trigger_queries.json"

# Required authored schema keys prevent the receiver from losing decisions or boundaries.
AUTHORED_FIELDS = ("decisions", "out_of_scope", "verification", "landing")

#
# Paths a reader is told to open, and which the repository is expected to carry.
# Runtime locations are deliberately absent: `tmp/`, `docs_draft/` and
# `.claude/worktrees/` are gitignored, so a fresh checkout does not have them
# and their absence says nothing about whether the skill is broken.
#
REPO_PREFIXES = (".agents/", ".claude/skills/", "scripts/", "src/", "tests/")
SKILL_RELATIVE_PREFIXES = ("references/", "evals/", "agents/", "tests/")
CHECKED_PREFIXES = REPO_PREFIXES + SKILL_RELATIVE_PREFIXES


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def referenced_paths(content: str) -> list[str]:
    """Concrete repository paths a skill points its reader at.

    Globs and placeholders are excluded: they name a shape, not a file.
    """
    #
    # Split each backticked chunk on whitespace so that command lines are
    # covered too, not just bare paths. The reference that made the previous
    # version unusable sat inside a `uv run pytest <path>` command.
    #
    words = (word for chunk in re.findall(r"`([^`\n]+)`", content) for word in chunk.split())
    return [word for word in words if word.startswith(CHECKED_PREFIXES) and not any(char in word for char in "*<>$")]


def resolve(token: str) -> list[Path]:
    """Where a referenced path may live.

    A bare `tests/...` is ambiguous: it reads as skill-relative, which is how
    the previous version named a module that did not exist. Accept either
    reading so the check stays about existence, not about spelling.
    """
    return [REPO_ROOT / token, SKILL_DIR / token]


def json_field_definition(key: str) -> str:
    """Read a JSON group by its machine key, not the prose heading above it."""
    definition = re.search(rf"^- `{key}`:\n(.*?)(?=^- `|^## |\Z)", read(SCHEMA), re.M | re.S)
    assert definition is not None, f"schema lacks the {key} field definition"
    return definition.group(1)


def test_skill_does_not_reference_the_removed_generator() -> None:
    # The removed CLI cannot generate this repository's handoff schema.
    assert "nova-parser-claude-handoff" not in read(AGENTS_SKILL)


def test_skill_declares_claude_code_allowed_tools() -> None:
    """Claude Code gates the skill's tool surface; Codex and pi ignore the key."""
    tools = yaml.safe_load(read(AGENTS_SKILL).split("---", 2)[1])["allowed-tools"]
    assert isinstance(tools, str)
    for entry in (
        "Write(tmp/docs_draft/claude_handoffs/**)",
        "Edit(tmp/docs_draft/claude_handoffs/**)",
        "Write(docs/superpowers/**)",
        "Edit(docs/superpowers/**)",
    ):
        assert entry in tools, entry
    assert "docs_draft/superpowers" not in tools


def test_trigger_queries_have_valid_structure() -> None:
    payload = json.loads(read(TRIGGERS))
    assert payload["skill_name"] == SKILL_DIR.name
    assert payload["queries"]
    for item in payload["queries"]:
        assert isinstance(item["id"], str) and item["id"].strip()
        assert isinstance(item["query"], str) and item["query"].strip()
        assert isinstance(item["should_trigger"], bool)
        assert isinstance(item["expected_terms"], list)
        assert all(isinstance(value, str) for value in item["expected_terms"])
    # A migrated trigger must not point agents at the source repository.
    assert "python-tdd-team" not in json.dumps(payload, ensure_ascii=False)


def test_schema_is_version_2_and_documents_the_authored_fields() -> None:
    content = read(SCHEMA)
    assert re.search(r'^- `schema_version`: `"2"`\.', content, re.M)
    # Schema keys are a machine interface: dropping an authored field loses facts.
    definitions = set(re.findall(r"^- `([a-z_]+)`:", content, re.M))
    assert set(AUTHORED_FIELDS) <= definitions


def test_every_referenced_path_exists() -> None:
    """A skill that points at a file which was never in this repository is broken.

    This guards the failure that made the previous version unusable: the
    Validation section named a test module that did not exist.
    """
    missing: list[str] = []
    for source in (AGENTS_SKILL, SCHEMA):
        for token in referenced_paths(read(source)):
            if not any(path.exists() for path in resolve(token)):
                missing.append(f"{source.name}: {token}")
    assert not missing, f"referenced paths do not exist: {missing}"


def test_schema_maps_review_fix_planning_hold_to_deferred() -> None:
    # Bucket/enum compatibility prevents Hold from silently becoming Skip.
    mappings = dict(re.findall(r"^\s*\| (Fix|Hold|Skip|Resolved) \| `([a-z]+)` \|", read(SCHEMA), re.M))
    assert mappings == {"Fix": "fix", "Hold": "deferred", "Skip": "skip", "Resolved": "resolved"}


def test_evals_json_uses_expectations_not_assertions() -> None:
    payload = json.loads(read(EVALS))
    evals = payload["evals"]
    assert evals, "evals.json has no evals"
    for item in evals:
        eval_id = item.get("id")
        assert "expectations" in item, f"eval {eval_id} is missing expectations"
        assert "assertions" not in item, f"eval {eval_id} still uses assertions"


def test_schema_requires_git_branch_head_status_in_json_fields() -> None:
    # Find the definition by its schema key, not the surrounding prose heading.
    required = re.findall(r"^  - (.*?) \(required\):", json_field_definition("git"), re.M)
    fields = {field for row in required for field in re.findall(r"`([a-z_]+)`", row)}
    assert {"worktree", "branch", "head", "status"} <= fields


def test_schema_allows_null_sources_spec() -> None:
    spec = re.search(r"^  - `spec` \(required\):([^\n]*)", json_field_definition("sources"), re.M)
    assert spec is not None, "sources lacks a required spec field"
    assert "`null`" in spec.group(1)


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    assert CLAUDE_LINK.is_symlink()
    assert os.readlink(CLAUDE_LINK) == "../../.agents/skills/agent-handoff"
    assert CLAUDE_LINK.resolve() == SKILL_DIR.resolve()


def test_documents_and_code_have_separate_schema_fields() -> None:
    for group, fields in (
        ("sources", {"doc_root", "document_commit", "document_published", "review_copy"}),
        ("git", {"parent_checkout", "code"}),
    ):
        defined = set(re.findall(r"`([a-z_]+)`:", json_field_definition(group)))
        assert fields <= defined, f"{group}: missing {fields - defined}"
