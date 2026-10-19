"""PR 修正ループのスキルが、利用者が明示的に起動したときだけ使われる設定であることを確かめる。"""

from __future__ import annotations

from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"


def frontmatter_lines(skill: Path) -> list[str]:
    return skill.read_text(encoding="utf-8").split("---", 2)[1].splitlines()


# 修正ループは push・マージまで進むので、通常のレビューや計画の依頼からモデルが自分で起動しないよう、
# 利用者が明示的に起動したときだけ使う設定にしている（権限を守る固定値。AGENTS.md「テストの採用基準」）。
# 値を変えるときは、このテストも合わせて更新する。
def test_loop_skill_runs_only_when_explicitly_invoked() -> None:
    assert "disable-model-invocation: true" in frontmatter_lines(SKILL)
