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
