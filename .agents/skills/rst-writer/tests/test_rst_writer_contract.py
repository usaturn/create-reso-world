"""Links, templates and eval fixtures that rst-writer points at must exist."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/rst-writer"
SKILL = SKILL_DIR / "SKILL.md"
TYPES = SKILL_DIR / "references/document-types.md"
EVALS = SKILL_DIR / "evals/evals.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_markdown_links_resolve() -> None:
    sources = [SKILL, *sorted((SKILL_DIR / "references").rglob("*.md"))]
    for source in sources:
        for target in re.findall(r"\]\(([^)#]+\.(?:md|rst))\)", read(source)):
            assert (source.parent / target).resolve().is_file(), f"{source.name}: {target}"


def test_templates_named_by_the_document_types_exist() -> None:
    templates = set(re.findall(r"(assets/[a-z-]+/template-[a-z-]+\.rst)", read(TYPES)))
    assert templates, "document types do not reference any templates"
    for template in templates:
        assert (SKILL_DIR / template).is_file(), template


def test_every_eval_uses_existing_fixture_files() -> None:
    evals = json.loads(read(EVALS))["evals"]
    assert evals
    for item in evals:
        assert isinstance(item["id"], int)
        for field in ("name", "prompt", "expected_output"):
            assert isinstance(item[field], str) and item[field].strip()
        assert isinstance(item["assertions"], list) and item["assertions"]
        assert all(isinstance(value, str) and value.strip() for value in item["assertions"])
        if item["fixture"] != "none":
            assert (SKILL_DIR / "evals/fixtures" / item["fixture"]).is_dir(), item["id"]
        assert isinstance(item["files"], list)
        for name in item["files"]:
            assert (SKILL_DIR / name).is_file(), f"{item['id']}: {name}"
