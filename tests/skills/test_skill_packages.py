"""Packaging and behavior guards for the shared Blender skills under .agents/skills.

Run with: uv run pytest tests/skills/test_skill_packages.py -q
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[2] / ".agents" / "skills"
SKILL_NAMES = (
    "blender-modeler", "hard-surface", "prop-artist", "uv-workflow",
    "procedural-modeling", "geometry-nodes", "horror-style",
    "sci-fi-punk-worlds", "dark-gritty-mood", "brutalist-mood",
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


def read_skill(name: str) -> tuple[Path, str]:
    path = SKILLS_ROOT / name / "SKILL.md"
    if not path.is_file():
        raise AssertionError(f"missing required skill: {path}")
    return path, path.read_text(encoding="utf-8")


class SkillPackageTests(unittest.TestCase):
    def skills(self) -> dict[str, tuple[Path, str]]:
        return {name: read_skill(name) for name in SKILL_NAMES}

    def test_execution_guidance_guards_cover_positive_and_negative_fixtures(self) -> None:
        self.assertTrue(has_positive_guidance("Use Blender MCP to edit this model.", POSITIVE_MCP))
        self.assertFalse(has_positive_guidance("Do not use Blender MCP for this task.", POSITIVE_MCP))
        self.assertTrue(has_positive_guidance("Export the mesh to Unity.", POSITIVE_OTHER_ENGINE))
        self.assertFalse(has_positive_guidance("Do not export the mesh to Unity.", POSITIVE_OTHER_ENGINE))
        self.assertFalse(has_positive_guidance("Do not run commands via Blender MCP.", POSITIVE_MCP))
        self.assertTrue(has_positive_guidance("Do not alter lighting, use Blender MCP to model.", POSITIVE_MCP))
        self.assertTrue(has_positive_guidance("Do not alter lighting, export the mesh to Unity.", POSITIVE_OTHER_ENGINE))

    def test_no_positive_execution_guidance_in_skills_or_shared_references(self) -> None:
        # The skills run Blender only through `resoloop blender run`. Guidance to
        # drive Blender MCP or hand assets to another engine was removed on import
        # (blender-skills-sources.json) because it acts outside that pipeline.
        guarded_texts = [(name, text) for name, (_, text) in self.skills().items()]
        for reference in REQUIRED_REFERENCES:
            path = SKILLS_ROOT / "references" / reference
            guarded_texts.append((f"references/{reference}", path.read_text(encoding="utf-8")))
        for label, text in guarded_texts:
            self.assertFalse(has_positive_guidance(text, POSITIVE_MCP), f"{label}: positive MCP guidance")
            self.assertFalse(has_positive_guidance(text, POSITIVE_OTHER_ENGINE), f"{label}: other-engine guidance")

    def test_provenance_license_and_document_coverage(self) -> None:
        # The source SHA, MIT attribution and each document's records freeze the reviewed
        # import provenance; losing a record would not fail anything else.
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


if __name__ == "__main__":
    unittest.main()
