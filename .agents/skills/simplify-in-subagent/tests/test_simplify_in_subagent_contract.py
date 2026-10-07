from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / ".agents/skills/simplify-in-subagent/SKILL.md"


def test_interpolation_is_limited_to_the_target_line() -> None:
    content = SKILL.read_text(encoding="utf-8")
    # Claude Code replaces $ARGUMENTS and $0-$9 in the body with the invocation
    # arguments, which would rewrite code blocks that use them.
    assert content.count("$ARGUMENTS") == 1
    assert all("$ARGUMENTS" not in block for block in re.findall(r"```[^\n]*\n(.*?)```", content, re.DOTALL))
    assert re.search(r"\$[0-9]", content) is None
