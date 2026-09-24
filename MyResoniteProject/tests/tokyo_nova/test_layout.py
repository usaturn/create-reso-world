"""Behavioral checks for the deterministic Tokyo Nova blockout layout."""
from __future__ import annotations

import importlib
import unittest


class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.layout_module = importlib.import_module("modeling.tokyo_nova.layout")
        except ModuleNotFoundError as exc:
            if exc.name == "modeling" or exc.name.startswith("modeling.tokyo_nova"):
                cls.layout_module = None
            else:
                raise
        try:
            cls.pipeline_module = importlib.import_module("modeling.tokyo_nova.pipeline")
        except ModuleNotFoundError as exc:
            if exc.name == "modeling" or exc.name.startswith("modeling.tokyo_nova"):
                cls.pipeline_module = None
            else:
                raise

    def build_layout(self) -> dict:
        self.assertIsNotNone(self.layout_module, "layout.build_layout() is not implemented")
        return self.layout_module.build_layout()

    def test_layout_has_required_unobstructed_plaza_and_building_count(self) -> None:
        layout = self.build_layout()
        self.assertEqual(layout["plaza"]["bounds_xz"], [-10, 10, -10, 10])
        self.assertEqual(len(layout["buildings"]), 24)
        for building in layout["buildings"]:
            x, _, z = building["center"]
            width, depth = building["size"]
            xmin, xmax = x - width / 2, x + width / 2
            zmin, zmax = z - depth / 2, z + depth / 2
            self.assertFalse(xmin < 10 and xmax > -10 and zmin < 10 and zmax > -10, building["key"])

    def test_routes_provide_four_entrances_two_loops_and_specified_widths(self) -> None:
        routes = self.build_layout()["routes"]
        self.assertEqual(sum(route["kind"] == "entrance" for route in routes), 4)
        self.assertGreaterEqual(sum(route.get("loop", False) for route in routes), 2)
        self.assertGreaterEqual(sum(route["kind"] == "alley" for route in routes), 6)
        for route in routes:
            if route["kind"] == "main":
                self.assertGreaterEqual(route["width"], 3)
                self.assertLessEqual(route["width"], 4)
            elif route["kind"] == "alley":
                self.assertGreaterEqual(route["width"], 1.5)
                self.assertLessEqual(route["width"], 2.5)

    def test_layout_has_stable_unique_keys_facilities_and_camera_bookmarks(self) -> None:
        layout = self.build_layout()
        entries = layout["buildings"] + layout["routes"] + layout["facilities"]
        keys = [entry["key"] for entry in entries]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(layout["facilities"]), 12)
        self.assertTrue(layout["cameras"])
        for camera in layout["cameras"]:
            self.assertEqual(len(camera["position"]), 3)
            self.assertEqual(len(camera["target"]), 3)

    def test_validator_reports_plaza_intrusion(self) -> None:
        layout = self.build_layout()
        layout["buildings"][0]["center"] = [0, 2, 0]
        errors = self.layout_module.validate_layout(layout)
        self.assertTrue(any("plaza" in error.lower() for error in errors), errors)

    def test_layout_generation_is_deterministic(self) -> None:
        self.assertEqual(self.build_layout(), self.build_layout())

    def test_resonite_to_blender_conversion_swaps_vertical_axis_once(self) -> None:
        self.assertEqual(self.pipeline_module.resonite_to_blender((1, 2, 3)), (1.0, 3.0, 2.0))

    def test_blockout_manifest_has_owned_root_and_stable_geometry_keys(self) -> None:
        manifest = self.pipeline_module.build_blockout_manifest(self.build_layout())
        self.assertEqual(manifest["ownership"]["key"], "tokyo-nova-west-slum")
        self.assertEqual(manifest["slot"]["key"], "root")
        self.assertEqual(manifest["slot"]["position"], [0.0, 30.0, 120.0])
        all_slots = list(self.pipeline_module.iter_slots(manifest))
        all_keys = [slot["slot"]["key"] for slot in all_slots]
        self.assertEqual(len(all_keys), len(set(all_keys)))
        self.assertEqual(sum(key.startswith("building_") for key in all_keys), 24)
        for key in ("plaza_floor", "outer_ground_tile_00", "roof_access_ramp", "south_theatre_basement_ramp", "west_bar_basement_stair_00"):
            self.assertIn(key, all_keys)
        self.assertIn("theatre_floor_well_left", all_keys)
        self.assertIn("bar_floor_well_back", all_keys)

    def test_manifest_expansion_limit_covers_reflected_blockout_without_maxing_cli_budget(self) -> None:
        manifest = self.pipeline_module.build_blockout_manifest(self.build_layout())
        expanded_nodes = manifest.get("limits", {}).get("expandedNodes", 0)
        self.assertGreaterEqual(expanded_nodes, 10_733)
        self.assertLessEqual(expanded_nodes, 250_000)

    def test_manifest_has_unique_sibling_slot_names_for_reconnect_safety(self) -> None:
        manifest = self.pipeline_module.build_blockout_manifest(self.build_layout())

        def check(node: dict) -> None:
            children = node.get("children", [])
            names = [child["slot"]["name"] for child in children]
            self.assertEqual(len(names), len(set(names)), names)
            for child in children:
                check(child)

        check(manifest)

    def test_each_building_shell_has_an_open_front_doorway(self) -> None:
        manifest = self.pipeline_module.build_blockout_manifest(self.build_layout())
        keys = {item["slot"]["key"] for item in self.pipeline_module.iter_slots(manifest)}
        for building in self.build_layout()["buildings"]:
            key = building["key"]
            self.assertIn(f"{key}_front_side_0", keys)
            self.assertIn(f"{key}_front_side_1", keys)
            self.assertIn(f"{key}_front_lintel", keys)
            self.assertNotIn(f"{key}_front_wall", keys)

    def test_roof_approach_rotation_points_up_and_toward_the_landing(self) -> None:
        manifest = self.pipeline_module.build_blockout_manifest(self.build_layout())
        ramp = next(slot for slot in self.pipeline_module.iter_slots(manifest) if slot["slot"]["key"] == "roof_access_ramp")
        x, y, z, w = ramp["slot"]["rotation"]
        rotated_z = (2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y))
        self.assertGreater(rotated_z[0], 0.5)
        self.assertGreater(rotated_z[1], 0.1)
        self.assertAlmostEqual(rotated_z[2], 0.0, places=6)

    def test_japanese_engine_text_is_added_idempotently_to_probe_manifest(self) -> None:
        manifest = {"slot": {"key": "root"}, "children": []}
        self.pipeline_module.add_japanese_probe_sign(manifest)
        self.pipeline_module.add_japanese_probe_sign(manifest)
        self.assertEqual(len(manifest["children"]), 1)
        sign = manifest["children"][0]
        self.assertEqual(sign["slot"]["key"], "probe_japanese_sign")
        self.assertEqual(sign["components"][0]["type"], "FrooxEngine.TextRenderer")
        self.assertIn("非対称・1m計測面", sign["components"][0]["fields"]["Text"])


if __name__ == "__main__":
    unittest.main()
