"""rst-writer writes this repository's documents by default (spec 8.2).

The profile of the migration source is gone together with its fixtures. The
OSS Python Extension profile stays reserved and unconnected.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/rst-writer"
SKILL = SKILL_DIR / "SKILL.md"
PROFILE = SKILL_DIR / "references/profiles/create-reso-world.md"
INTERFACE = SKILL_DIR / "references/profile-interface.md"
TYPES = SKILL_DIR / "references/document-types.md"
CORE = SKILL_DIR / "references/rst-core-style-guide.md"
EVALS = SKILL_DIR / "evals/evals.json"
CHECK = 'uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning "$TARGET"'


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def names(directory: Path) -> set[str]:
    return {entry.name for entry in directory.iterdir() if entry.name != "__pycache__"}


def test_this_repository_profile_is_the_default() -> None:
    content = read(SKILL)
    assert "省略時の `profile` は `create-reso-world`" in content
    assert "[create-reso-world profile](references/profiles/create-reso-world.md)" in content
    assert "**省略時だけ** `create-reso-world`" in read(INTERFACE)
    assert "**available は create-reso-world の3種だけ**" in read(TYPES)
    # Only this repository's profile and the reserved OSS profile remain.
    assert names(SKILL_DIR / "references/profiles") == {"create-reso-world.md", "oss-python-extension.md"}
    assert names(SKILL_DIR / "assets") == {"create-reso-world", "oss-python-extension"}
    assert names(SKILL_DIR / "evals/fixtures") == {"negative", "oss-extension", "repo-env"}
    assert not (SKILL_DIR / "references/rst-style-guide.md").exists()


def test_profile_drafts_in_docs_draft_without_a_glossary() -> None:
    content = read(PROFILE)
    assert "リポジトリのルートの `docs_draft/<目的に合う名前>.rst`" in content
    assert "用語集（`glossary`）を探したり、作成・照合・追記したりしない" in content
    assert "`:ref:`、`:term:`、`:doc:`" in content
    assert CHECK in content
    assert "`wabun-rst-ulint`）は、この profile では実行しない" in content


def test_core_guide_leaves_the_static_check_to_the_profile() -> None:
    content = read(CORE)
    assert "確定しない profile は、その profile の検査手順に従う" in content
    assert "Sphinx を使わない profile" in content


def test_skill_runs_the_profile_check() -> None:
    assert "uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning" in read(SKILL)


def test_markdown_links_resolve() -> None:
    sources = [SKILL, *sorted((SKILL_DIR / "references").rglob("*.md"))]
    for source in sources:
        for target in re.findall(r"\]\(([^)#]+\.(?:md|rst))\)", read(source)):
            assert (source.parent / target).resolve().is_file(), f"{source.name}: {target}"


def test_templates_named_by_the_document_types_exist() -> None:
    templates = set(re.findall(r"(assets/[a-z-]+/template-[a-z-]+\.rst)", read(TYPES)))
    assert "assets/create-reso-world/template-procedure.rst" in templates
    for template in templates:
        assert (SKILL_DIR / template).is_file(), template


def test_every_eval_uses_existing_fixture_files() -> None:
    evals = json.loads(read(EVALS))["evals"]
    for item in evals:
        assert item["fixture"] in {"oss-extension", "repo-env", "none"}, item["id"]
        for name in item["files"]:
            assert (SKILL_DIR / name).is_file(), f"{item['id']}: {name}"


def test_evals_cover_the_profile_of_this_repository() -> None:
    names = {item["name"] for item in json.loads(read(EVALS))["evals"]}
    assert {"repo-procedure-default", "repo-explanation-explicit-target", "repo-edit-existing"} <= names


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/rst-writer"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/rst-writer"
