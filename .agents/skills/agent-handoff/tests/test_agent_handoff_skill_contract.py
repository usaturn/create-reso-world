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

#
# Fields only the outgoing agent can supply. The whole point of the
# skill is that the outgoing agent writes them down, so both runtime
# versions have to name them.
#
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


def assert_shared_handoff_contract(content: str) -> None:
    """The contract both runtimes must state, whichever direction they are in."""
    assert "tmp/docs_draft/claude_handoffs" in content
    assert "references/handoff-schema.md" in content
    for field in AUTHORED_FIELDS:
        assert field in content, f"{field} is not named"
    # The receiver edits the wrong tree without these two.
    assert "git.worktree" in content
    assert "sources.spec" in content
    # Handoffs are hand-written in this repository; there is no generator CLI
    # to resolve, so a skill must not send the reader looking for one.
    assert "nova-parser-claude-handoff" not in content


def test_skill_states_the_handoff_contract() -> None:
    content = read(AGENTS_SKILL)
    assert_shared_handoff_contract(content)
    assert "handoff を書く" in content
    assert "handoff を読む" in content
    assert "拘束力" in content


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


def test_specs_and_plans_live_in_docs_superpowers() -> None:
    # AGENTS.md keeps specs and plans under docs/superpowers/; docs_draft/ is a
    # gitignored scratch area that a receiver on another checkout cannot read.
    content = read(AGENTS_SKILL)
    assert "`docs/superpowers/`" in content
    assert "docs_draft/superpowers" not in content


def test_overview_does_not_count_runtimes() -> None:
    # Every runtime reads this one file (.claude/skills/agent-handoff is a symlink to it), so the overview must not count runtimes.
    assert "両ランタイム" not in read(AGENTS_SKILL)


def test_trigger_queries_belong_to_this_repository() -> None:
    queries = {item["id"]: item for item in json.loads(read(TRIGGERS))["queries"]}
    assert queries["q2"]["should_trigger"] is True
    assert "python-tdd-team" not in json.dumps(queries, ensure_ascii=False)


def test_skill_covers_the_gaps_hand_written_handoffs_drop() -> None:
    content = read(AGENTS_SKILL)
    assert "TodoWrite" in content
    assert "heredoc" in content
    assert "サブエージェント" in content


def test_schema_is_version_2_and_documents_the_authored_fields() -> None:
    content = read(SCHEMA)
    assert "`schema_version` 2" in content
    for field in AUTHORED_FIELDS:
        assert f"`{field}`" in content, f"{field} is not documented"
    # Older artifacts predate those fields; absence there means unknown.
    assert "version 1" in content


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
    """Hold is not a disposition name; writers must map it to deferred, not skip."""
    content = read(SCHEMA)
    assert "These mirror the four buckets" not in content
    assert "| Hold | `deferred` |" in content
    assert "| Fix | `fix` |" in content
    assert "| Skip | `skip` |" in content
    assert "| Resolved | `resolved` |" in content
    assert "`skip`" in content
    assert "deferred" in content
    lowered = content.lower()
    assert "intended behaviour" in lowered or "spec question" in lowered


def test_evals_json_uses_expectations_not_assertions() -> None:
    payload = json.loads(read(EVALS))
    evals = payload["evals"]
    assert evals, "evals.json has no evals"
    for item in evals:
        eval_id = item.get("id")
        assert "expectations" in item, f"eval {eval_id} is missing expectations"
        assert "assertions" not in item, f"eval {eval_id} still uses assertions"


def test_schema_requires_git_branch_head_status_in_json_fields() -> None:
    content = read(SCHEMA)
    json_fields = content.split("## JSON fields", 1)[1]
    git_section = json_fields.split("- `git`:", 1)[1]
    assert "`branch`" in git_section
    assert "`head`" in git_section
    assert "`status`" in git_section
    assert "Required fields table" in git_section
    assert "`branch`, `head`, `status`, and `merge_base` when a branch point matters" not in git_section


def test_schema_allows_null_sources_spec() -> None:
    content = read(SCHEMA)
    sources = content.split("- `sources`:", 1)[1]
    spec_line = sources.split("\n", 2)[1]
    assert "`spec`" in spec_line
    assert "`null`" in spec_line or "null" in spec_line.lower()
    assert "none" in spec_line.lower() or "`null`" in spec_line


def test_validation_quick_validates_the_shared_skill() -> None:
    assert "quick_validate.py .agents/skills/agent-handoff" in read(AGENTS_SKILL)


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    assert CLAUDE_LINK.is_symlink()
    assert os.readlink(CLAUDE_LINK) == "../../.agents/skills/agent-handoff"
    assert CLAUDE_LINK.resolve() == SKILL_DIR.resolve()


#
# `<skill-creator-path>` is a placeholder on purpose — the script lives in a
# different place per runtime — but the section must also name how to resolve
# it. A command that cannot be run is documentation that fails silently: the
# path-existence check above skips `<>` tokens, so it cannot see this break.
#
SKILL_CREATOR_RESOLUTIONS = (
    "~/.codex/skills/.system/skill-creator",
    "find ~/.claude -name quick_validate.py",
)


def test_validation_names_every_runtime_resolution() -> None:
    content = read(AGENTS_SKILL)
    assert "<skill-creator-path>" in content
    for hint in SKILL_CREATOR_RESOLUTIONS:
        assert hint in content
    assert "skill-efficiency-check.py" in content


def test_agents_skill_documents_the_pi_fallback() -> None:
    """pi's global skill-creator ships no quick_validate.py; .agents readers need the alternative."""
    assert "skill-efficiency-check.py" in read(AGENTS_SKILL)


def test_documents_and_code_are_restored_from_separate_sources() -> None:
    content = read(AGENTS_SKILL)
    for phrase in ("`PARENT_ROOT`", "`DOC_ROOT`", "`CODE_ROOT`", "`sources.review_copy`", "閲覧補助", "公開未実施"):
        assert phrase in content, phrase
    schema = read(SCHEMA)
    for field in (
        "`doc_root`",
        "`document_commit`",
        "`document_published`",
        "`review_copy`",
        "`parent_checkout`",
        "`code`",
    ):
        assert field in schema, field
    assert "never a restore source" in schema
