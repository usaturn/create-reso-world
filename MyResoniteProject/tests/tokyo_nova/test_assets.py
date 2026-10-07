"""Acceptance tests for the detailed north-sector Blender asset toolkit."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from modeling.tokyo_nova import build, geometry, materials, north, pipeline, props
from modeling.tokyo_nova.layout import build_layout


class NorthAssetTests(unittest.TestCase):
    def test_catalog_records_finished_asset_design_and_exact_phone_scale(self) -> None:
        catalog = north.asset_catalog()
        self.assertGreaterEqual(len(catalog), 3)
        for asset in catalog:
            for field in ("kind", "dimensions", "materials", "parts", "wear", "placement", "recognition"):
                self.assertIn(field, asset, f"{asset.get('kind')} missing {field}")
            self.assertTrue(asset["materials"])
            self.assertGreaterEqual(len(asset["parts"]), 5)
            self.assertTrue(asset["wear"])
            self.assertTrue(asset["recognition"])
        phone = next(asset for asset in catalog if asset["kind"] == "pocket_phone")
        self.assertEqual(phone["dimensions"], [0.075, 0.008, 0.15])
        excluded = ("humanoid", "mannequin", "payment", "ianus", "identity", "camera_surveillance")
        serialized = str(catalog).lower()
        for term in excluded:
            self.assertNotIn(term, serialized)
        enriched = pipeline.enrich_layout(build_layout())
        self.assertEqual(enriched["north_assets"], catalog)
        catalog_kinds = {asset["kind"] for asset in catalog}
        self.assertTrue(catalog_kinds.issubset({entry["kind"] for entry in enriched["prop_catalog"]}))

    def test_each_modeled_kind_has_real_geometry_and_a_nonempty_resource_report(self) -> None:
        assemblies = north.build_north_sector(build_layout())
        report = build.resource_report(assemblies)
        by_kind = {entry["kind"]: entry for entry in report["assemblies"]}
        self.assertEqual(set(by_kind), {assembly.kind for assembly in assemblies})
        for kind, entry in by_kind.items():
            self.assertGreater(entry["vertices"], 0, kind)
            self.assertGreater(entry["triangles"], 0, kind)
            self.assertGreater(entry["parts"], 0, kind)
            self.assertTrue(entry["materials"], kind)
        self.assertGreater(report["total_triangles"], 1000)
        self.assertEqual(report["seed"], build_layout()["seed"])

    def test_phone_assembly_has_repairable_physical_parts(self) -> None:
        phone = props.create("pocket_phone", origin=(0, 0, 0))
        part_names = {part.name for part in phone.parts}
        self.assertGreaterEqual(len(phone.parts), 7)
        self.assertTrue({"rounded_glass", "side_buttons", "camera_cluster", "removable_back"}.issubset(part_names))

    def test_geometry_builders_return_deterministic_nonempty_meshes(self) -> None:
        constructors = (
            lambda: geometry.box("box", (0, 0, 0), (1, 2, 3), "concrete"),
            lambda: geometry.beveled_box("bevel", (0, 0, 0), (1, 2, 3), 0.05, "plastic"),
            lambda: geometry.cylinder("pot", (0, 0, 0), 0.2, 0.3, "ceramic"),
            lambda: geometry.pipe("drain", (0, 0, 0), (0, 1, 0), 0.04, "metal"),
            lambda: geometry.mesh("custom", ((0, 0, 0), (1, 0, 0), (0, 0, 1)), ((0, 1, 2),), "rust"),
        )
        for constructor in constructors:
            first, second = constructor(), constructor()
            self.assertTrue(first.vertices)
            self.assertTrue(first.faces)
            self.assertEqual(first.vertices, second.vertices)
            self.assertEqual(first.faces, second.faces)

    def test_shared_materials_declare_supported_visual_adaptation_without_flattening(self) -> None:
        palette = materials.build_materials()
        required = {"concrete", "painted_metal", "exposed_metal", "rust", "cloth", "ceramic", "plastic", "glass", "asphalt_wet", "asphalt_dry"}
        self.assertTrue(required.issubset(palette))
        self.assertLessEqual(len(palette), 20)
        for material in palette.values():
            self.assertIn("base_color", material)
            self.assertIn("roughness", material)
            self.assertIn("metallic", material)
        self.assertTrue(materials.ADAPTATION_NOTE)

    def test_composition_preserves_owned_root_and_disables_only_reviewed_north_renderers(self) -> None:
        base = {
            "schemaVersion": "1", "ownership": {"key": "tokyo-nova-west-slum"}, "limits": {"expandedNodes": 12000},
            "slot": {"key": "root", "name": "TokyoNova_WestSlum", "parent": "Root", "position": [0, 30, 120]},
            "components": [], "children": [
                {"slot": {"key": "building_north_yatai"}, "children": [], "components": [{"key": "yatai_renderer", "type": "FrooxEngine.MeshRenderer", "fields": {"Enabled": True}}, {"key": "yatai_collider", "type": "FrooxEngine.BoxCollider", "fields": {"CharacterCollider": True}}]},
                {"slot": {"key": "building_east_clinic"}, "components": [{"key": "clinic_renderer", "type": "FrooxEngine.MeshRenderer", "fields": {"Enabled": True}}]},
            ],
        }
        exported = {"schemaVersion": "1", "ownership": {"key": "blender_north"}, "slot": {"key": "root", "name": "North"}, "assets": {"wall": {"kind": "texture", "source": "wall.png"}}, "components": [], "children": [{"slot": {"key": "north_model"}, "components": [], "children": []}]}
        with tempfile.TemporaryDirectory(prefix="tokyo-nova-compose-") as temp_dir:
            folder = Path(temp_dir)
            source = folder / "base.json"
            export_path = folder / "export" / "model.apply.json"
            export_path.parent.mkdir()
            output = folder / "north-apply.json"
            source.write_text(json.dumps(base), encoding="utf-8")
            export_path.write_text(json.dumps(exported), encoding="utf-8")
            (export_path.parent / "wall.png").write_bytes(b"source texture")
            composed = pipeline.integrate_north_manifest(source, export_path, output)
            saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(composed["ownership"], base["ownership"])
        self.assertEqual(composed["slot"]["position"], [0, 30, 120])
        self.assertGreaterEqual(composed["limits"]["expandedNodes"], 16000)
        north_children = composed["children"][0]
        north_components = {component["key"]: component for component in north_children["components"]}
        self.assertFalse(north_components["yatai_renderer"]["fields"]["Enabled"])
        self.assertTrue(north_components["yatai_collider"]["fields"]["CharacterCollider"])
        self.assertTrue(composed["children"][1]["components"][0]["fields"]["Enabled"])
        self.assertEqual(len([child for child in composed["children"] if child["slot"].get("key") == "north_detail"]), 1)
        self.assertEqual((output.parent / composed["assets"]["wall"]["source"]).resolve(), (export_path.parent / "wall.png").resolve())
        self.assertEqual(saved, composed)


if __name__ == "__main__":
    unittest.main()
