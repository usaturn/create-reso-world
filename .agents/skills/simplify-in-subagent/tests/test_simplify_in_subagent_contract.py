from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / ".agents/skills/simplify-in-subagent/SKILL.md"


def test_interpolation_is_limited_to_the_target_line() -> None:
    content = SKILL.read_text(encoding="utf-8")
    assert content.count("$ARGUMENTS") == 1
    assert all("$ARGUMENTS" not in block for block in re.findall(r"```[^\n]*\n(.*?)```", content, re.DOTALL))
    assert re.search(r"\$[0-9]", content) is None


def test_frontmatter_keeps_only_keys_every_runtime_can_live_with() -> None:
    head = yaml.safe_load(SKILL.read_text(encoding="utf-8").split("---", 2)[1])
    assert head["argument-hint"] == "[--staged|--ref=<ref>|<files>]"
    assert head["subagent"] is True
    # Devin's YAML list of its own tool names would become Claude Code's
    # allow-list of tools that do not exist there.
    assert "allowed-tools" not in head


def test_claude_code_reads_the_same_skill() -> None:
    link = REPO_ROOT / ".claude/skills/simplify-in-subagent"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/simplify-in-subagent"
