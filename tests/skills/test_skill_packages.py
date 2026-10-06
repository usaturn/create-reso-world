"""Packaging and behavior guards for the shared Blender skills under .agents/skills.

Run with: uv run pytest tests/skills/test_skill_packages.py -q
For sequential validation, run the targeted test with SKILL_UNDER_TEST=<name>.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

SKILLS_ROOT = Path(__file__).resolve().parents[2] / ".agents" / "skills"
SKILL_NAMES = (
    "blender-modeler", "hard-surface", "prop-artist", "uv-workflow",
    "procedural-modeling", "geometry-nodes", "horror-style",
    "sci-fi-punk-worlds", "dark-gritty-mood", "brutalist-mood",
)
STANDARD_SKILL_NAMES = (
    "resonite-build", "resonite-blender", "resonite-inspect",
    "resonite-debug", "resonite-flux", "resonite-uix",
)
REQUIRED_REFERENCES = (
    "modular-environment-design.md", "set-dressing-patterns.md", "texture-baking.md",
)
MCP_ACTION = r"(?:use|run|execute|operate|create|apply|query|connect)"
ENGINE_ACTION = r"(?:export|import|ship|deliver|bake|pack)"
POSITIVE_MCP = re.compile(
    rf"(?P<action>\b{MCP_ACTION}\b)[^\n.!?;]{{0,55}}\b(?:blender\s+)?mcp\b|"
    rf"\b(?:blender\s+)?mcp\b[^\n.!?;]{{0,55}}(?P<action_after_target>\b{MCP_ACTION}\b)",
    re.IGNORECASE,
)
POSITIVE_OTHER_ENGINE = re.compile(
    rf"(?P<action>\b{ENGINE_ACTION}\b)[^\n.!?;]{{0,65}}\b(?:fbx|glb|gltf|unity|unreal|godot)\b|"
    rf"\b(?:fbx|glb|gltf|unity|unreal|godot)\b[^\n.!?;]{{0,65}}(?P<action_after_target>\b{ENGINE_ACTION}\b)",
    re.IGNORECASE,
)
NEGATED_ACTION = re.compile(
    r"(?:\bdo\s+not\b|\bdon't\b|\bmust\s+not\b|\bshould\s+not\b|\bnever\b|\bavoid\b)\s*$",
    re.IGNORECASE,
)


def has_positive_guidance(text: str, pattern: re.Pattern[str]) -> bool:
    """Match unsafe instructions, exempting only negation directly before the action."""
    for match in pattern.finditer(text):
        action_group = "action" if match.group("action") is not None else "action_after_target"
        action_start = match.start(action_group)
        prefix = text[max(0, action_start - 48):action_start]
        if NEGATED_ACTION.search(prefix):
            continue
        return True
    return False


def read_skill(name: str, root: Path = SKILLS_ROOT) -> tuple[Path, str, dict[str, object]]:
    path = root / name / "SKILL.md"
    if not path.is_file():
        raise AssertionError(f"missing required skill: {path}")
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise AssertionError(f"{name}: missing YAML frontmatter")
    frontmatter = yaml.safe_load(match.group(1))
    if not isinstance(frontmatter, dict):
        raise TypeError(f"{name}: frontmatter must be a mapping")
    if frontmatter.get("name") != name:
        raise AssertionError(f"{name}: frontmatter name does not match directory")
    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        raise AssertionError(f"{name}: description must be a non-empty string")
    return path, text, frontmatter


class SkillPackageTests(unittest.TestCase):
    def skills(self, root: Path = SKILLS_ROOT) -> dict[str, tuple[Path, str, dict[str, object]]]:
        return {name: read_skill(name, root) for name in SKILL_NAMES}

    def assert_owned_skill_packages(self, root: Path) -> dict[str, tuple[Path, str, dict[str, object]]]:
        present = {path.name for path in root.iterdir() if path.is_dir()}
        missing = set(SKILL_NAMES) - present
        self.assertFalse(missing, f"missing owned skill directories: {sorted(missing)}")
        return self.skills(root)


    def assert_no_unapproved_guidance(self, root: Path) -> None:
        for name, (_, text, _) in self.skills(root).items():
            normalized = text.casefold()
            for unapproved in ("blender-director", "asset-optimization", "export-pipeline", "scene-assembly"):
                self.assertNotIn(unapproved, normalized, f"{name}: unapproved delegation {unapproved}")
            if name in ("procedural-modeling", "geometry-nodes"):
                self.assertRegex(normalized, r"different seeds.{0,80}(?:not|aren't|are not).{0,30}lod|(?:not|aren't|are not).{0,30}lod.{0,80}seed")
            if name == "horror-style":
                self.assertRegex(normalized, r"(?:fog|volumetric).{0,60}(?:optional|not required|not assumed)|(?:optional|not required|not assumed).{0,60}(?:fog|volumetric)")

    def test_targeted_skill_semantics(self) -> None:
        name = os.environ.get("SKILL_UNDER_TEST", "")
        if not name:
            self.skipTest("set SKILL_UNDER_TEST for sequential per-skill validation")
        self.assertIn(name, SKILL_NAMES, "SKILL_UNDER_TEST must name an approved skill")
        _, text, _ = read_skill(name)
        self.assertFalse(has_positive_guidance(text, POSITIVE_MCP), f"{name}: positive MCP guidance")
        self.assertFalse(has_positive_guidance(text, POSITIVE_OTHER_ENGINE), f"{name}: other-engine guidance")

    def test_required_names_and_valid_frontmatter(self) -> None:
        self.assert_owned_skill_packages(SKILLS_ROOT)

    def test_installed_style_layout_preserves_standard_and_unrelated_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".agents" / "skills"
            root.parent.mkdir(parents=True)
            root.mkdir()
            for name in SKILL_NAMES:
                shutil.copytree(SKILLS_ROOT / name, root / name)
            shutil.copytree(SKILLS_ROOT / "references", root / "references")
            preserved: dict[str, bytes] = {}
            for name in STANDARD_SKILL_NAMES:
                path = root / name / "SKILL.md"
                path.parent.mkdir(parents=True)
                content = f"---\nname: {name}\ndescription: preserved standard skill\n---\n".encode()
                path.write_bytes(content)
                preserved[path.relative_to(root).as_posix()] = content
            unrelated_skill = root / "pre-existing-extra" / "SKILL.md"
            unrelated_skill.parent.mkdir()
            unrelated_content = b"pre-existing unrelated skill\n"
            unrelated_skill.write_bytes(unrelated_content)
            preserved[unrelated_skill.relative_to(root).as_posix()] = unrelated_content
            unrelated_file = root / "legacy-notes.txt"
            unrelated_file.write_text("pre-existing unrelated content\n", encoding="utf-8")
            preserved[unrelated_file.relative_to(root).as_posix()] = unrelated_file.read_bytes()

            self.assert_owned_skill_packages(root)
            self.assert_no_unapproved_guidance(root)
            present = {path.name for path in root.iterdir() if path.is_dir()}
            self.assertTrue(set(STANDARD_SKILL_NAMES) <= present)
            for relative, expected in preserved.items():
                self.assertEqual((root / relative).read_bytes(), expected, f"modified pre-existing content: {relative}")

    def test_references_and_links_resolve(self) -> None:
        refs_dir = SKILLS_ROOT / "references"
        for reference in REQUIRED_REFERENCES:
            self.assertTrue((refs_dir / reference).is_file(), f"missing shared reference {reference}")
        for name, (path, text, _) in self.skills().items():
            links = re.findall(r"\[[^\]]+\]\(([^)]+)\)|`((?:references|\.\./references)/[^`]+)`", text)
            for link in links:
                target = next((part for part in link if part), "")
                if target.startswith(("http:", "https:", "#")):
                    continue
                self.assertTrue((path.parent / target).resolve().is_file(), f"{name}: broken link {target}")


    def test_execution_guidance_guards_cover_positive_and_negative_fixtures(self) -> None:
        self.assertTrue(has_positive_guidance("Use Blender MCP to edit this model.", POSITIVE_MCP))
        self.assertFalse(has_positive_guidance("Do not use Blender MCP for this task.", POSITIVE_MCP))
        self.assertTrue(has_positive_guidance("Export the mesh to Unity.", POSITIVE_OTHER_ENGINE))
        self.assertFalse(has_positive_guidance("Do not export the mesh to Unity.", POSITIVE_OTHER_ENGINE))
        self.assertFalse(has_positive_guidance("Do not run commands via Blender MCP.", POSITIVE_MCP))
        self.assertTrue(has_positive_guidance("Do not alter lighting, use Blender MCP to model.", POSITIVE_MCP))
        self.assertTrue(has_positive_guidance("Do not alter lighting, export the mesh to Unity.", POSITIVE_OTHER_ENGINE))

    def test_no_positive_execution_guidance_in_skills_or_shared_references(self) -> None:
        guarded_texts = [(name, text) for name, (_, text, _) in self.skills().items()]
        for reference in REQUIRED_REFERENCES:
            path = SKILLS_ROOT / "references" / reference
            guarded_texts.append((f"references/{reference}", path.read_text(encoding="utf-8")))
        for label, text in guarded_texts:
            self.assertFalse(has_positive_guidance(text, POSITIVE_MCP), f"{label}: positive MCP guidance")
            self.assertFalse(has_positive_guidance(text, POSITIVE_OTHER_ENGINE), f"{label}: other-engine guidance")

    def test_provenance_license_and_document_coverage(self) -> None:
        # The source SHA and MIT attribution freeze the reviewed import provenance.
        references = SKILLS_ROOT / "references"
        license_text = (references / "blender-skills-LICENSE.txt").read_text(encoding="utf-8")
        for required in ("MIT License", "Copyright (c) 2026 blender-skills contributors", "WITHOUT WARRANTY OF ANY KIND"):
            self.assertIn(required, license_text)
        provenance = json.loads((references / "blender-skills-sources.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["repository"], "https://github.com/arjun988/blender-skills")
        self.assertEqual(provenance["commit"], "8f778d2405a214b508d4c7d80742be8e43acdd52")
        self.assertEqual(set(provenance["documents"]), set(SKILL_NAMES) | set(REQUIRED_REFERENCES))
        for key, entry in provenance["documents"].items():
            self.assertTrue(entry["source_paths"], f"{key}: source paths are required")
            self.assertTrue(entry["modifications"].strip(), f"{key}: modifications summary required")
            self.assertTrue(entry["output_paths"], f"{key}: output paths are required")
            for source in entry["source_paths"]:
                self.assertTrue(source.startswith(".claude/skills/"), f"{key}: non-source path {source}")
            for output in entry["output_paths"]:
                self.assertTrue((SKILLS_ROOT.parent.parent / output).is_file(), f"{key}: missing output {output}")

    def test_no_unapproved_guidance_or_false_runtime_claims(self) -> None:
        self.assert_no_unapproved_guidance(SKILLS_ROOT)


if __name__ == "__main__":
    unittest.main()
