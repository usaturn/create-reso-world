from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / ".agents/skills/simplify-in-subagent/SKILL.md"


def split(content: str) -> tuple[dict[str, object], str]:
    _, head, body = content.split("---", 2)
    return yaml.safe_load(head), body


def test_interpolation_is_limited_to_the_target_line() -> None:
    content = SKILL.read_text(encoding="utf-8")
    assert content.count("$ARGUMENTS") == 1
    assert "対象指定: $ARGUMENTS" in content
    assert re.search(r"\$[0-9]", content) is None


def test_frontmatter_keeps_only_keys_every_runtime_can_live_with() -> None:
    head, _ = split(SKILL.read_text(encoding="utf-8"))
    assert head["argument-hint"] == "[--staged|--ref=<ref>|<files>]"
    assert head["subagent"] is True
    # Devin's YAML list of its own tool names would become Claude Code's
    # allow-list of tools that do not exist there.
    assert "allowed-tools" not in head


def test_runtime_notes_keep_the_devin_specific_rules() -> None:
    content = SKILL.read_text(encoding="utf-8")
    assert "## ランタイム別の注意" in content
    assert "ask_user_question" in content
    assert "An empty or placeholder line means `HEAD`" in content


def test_claude_code_reads_the_same_skill() -> None:
    link = REPO_ROOT / ".claude/skills/simplify-in-subagent"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/simplify-in-subagent"


def route_rows(content: str) -> list[str]:
    preflight = content.split("## Repository preflight", 1)[1].split("## Workflow", 1)[0]
    return [line for line in preflight.splitlines() if line.startswith("| ") and "---" not in line][1:]


def test_routes_follow_the_repository_boundary_table() -> None:
    # Spec 5.4: this repository and the resoloop fork are the only routes;
    # anything else stops without guessing.
    content = SKILL.read_text(encoding="utf-8")
    rows = route_rows(content)
    assert len(rows) == 2
    assert "`usaturn/create-reso-world`" in rows[0]
    assert "`usaturn/resoloop`" in rows[1] and "`orange3134/resoloop`" in rows[1]
    assert "`external/resoloop`" in rows[1]
    assert "repository boundary table in the root `AGENTS.md`" in content
    assert "git remote get-url upstream" in content
    assert "Any other target repository has no route" in content
    assert "repository-ownership" not in content


def test_examples_name_this_skill_and_need_no_question_tool() -> None:
    content = SKILL.read_text(encoding="utf-8")
    examples = content.split("## Examples", 1)[1]
    assert examples.count("/simplify-in-subagent --ref=origin/main") == 2
    assert "/simplify --ref" not in examples
    assert "it does not require a question tool" in examples
