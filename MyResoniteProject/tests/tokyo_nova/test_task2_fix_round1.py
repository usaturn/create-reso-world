"""TDD regressions for the seven north-asset findings in Task 2 review."""
from __future__ import annotations

import json
import math
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from modeling.tokyo_nova import geometry, north, props
from modeling.tokyo_nova.layout import build_layout
from modeling.tokyo_nova.sector_pipeline import integrate_north_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _part(assembly: props.Assembly, name: str) -> geometry.MeshData:
    return next(part for part in assembly.parts if part.name == name)


def _bounds(mesh: geometry.MeshData) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    xs, ys, zs = (tuple(vertex[axis] for vertex in mesh.vertices) for axis in range(3))
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _slot_tree(slot: dict):
    yield slot
    for child in slot.get("children", []):
        yield from _slot_tree(child)


def _face_front_z(assembly: props.Assembly, part_name: str) -> float:
    part = next(part for part in assembly.transformed_parts() if part.name == part_name)
    return min(vertex[2] for vertex in part.vertices)


def _ring_center(vertices: tuple[tuple[float, float, float], ...] | list[tuple[float, float, float]]) -> tuple[float, float, float]:
    return (
        sum(vertex[0] for vertex in vertices) / len(vertices),
        sum(vertex[1] for vertex in vertices) / len(vertices),
        sum(vertex[2] for vertex in vertices) / len(vertices),
    )


class Task2FixRound1Tests(unittest.TestCase):
    def test_beveled_boxes_are_closed_consistently_wound_manifolds(self) -> None:
        meshes = (
            geometry.beveled_box("unequal", (1.2, -0.4, 2.1), (2.0, 1.0, 0.4), 0.05, "metal"),
            _part(props.create("pocket_phone", (0.0, 0.0, 0.0)), "phone_shell"),
        )
        for mesh in meshes:
            undirected_edges: Counter[tuple[int, int]] = Counter()
            directed_edges: Counter[tuple[int, int]] = Counter()
            signed_volume = 0.0
            for face in mesh.faces:
                for index, start in enumerate(face):
                    end = face[(index + 1) % len(face)]
                    edge = (start, end) if start < end else (end, start)
                    undirected_edges[edge] += 1
                    directed_edges[(start, end)] += 1
                v0 = mesh.vertices[face[0]]
                for index in range(1, len(face) - 1):
                    v1, v2 = mesh.vertices[face[index]], mesh.vertices[face[index + 1]]
                    cross = (
                        v1[1] * v2[2] - v1[2] * v2[1],
                        v1[2] * v2[0] - v1[0] * v2[2],
                        v1[0] * v2[1] - v1[1] * v2[0],
                    )
                    signed_volume += sum(v0[axis] * cross[axis] for axis in range(3)) / 6.0
            self.assertTrue(all(incidents == 2 for incidents in undirected_edges.values()), mesh.name)
            for (start, end), incidents in directed_edges.items():
                self.assertEqual(incidents, 1, mesh.name)
                self.assertEqual(directed_edges[(end, start)], 1, mesh.name)
            self.assertGreater(signed_volume, 0.0, mesh.name)

    def test_phone_details_are_exposed_inside_exact_overall_dimensions(self) -> None:
        phone = props.create("pocket_phone", (0.0, 0.0, 0.0))
        shell = _bounds(_part(phone, "phone_shell"))
        screen = _bounds(_part(phone, "screen_display"))
        rear_camera = _bounds(_part(phone, "camera_cluster_ring_0"))
        side_button = _bounds(_part(phone, "side_buttons"))
        self.assertGreater(screen[1][1], shell[1][1], "screen face must rise above the thinned shell")
        self.assertLess(rear_camera[0][1], shell[0][1], "rear camera ring must be exposed past the shell")
        self.assertGreater(side_button[1][0], shell[1][0], "side key must be exposed past the shell")
        self.assertAlmostEqual(phone.bounds[1][0] - phone.bounds[0][0], 0.075, places=7)
        self.assertAlmostEqual(phone.bounds[1][1] - phone.bounds[0][1], 0.008, places=7)
        self.assertAlmostEqual(phone.bounds[1][2] - phone.bounds[0][2], 0.150, places=7)
        for part in phone.parts:
            low, high = _bounds(part)
            for axis, half_extent in enumerate((0.0375, 0.004, 0.075)):
                self.assertGreaterEqual(low[axis], -half_extent - 1e-9, part.name)
                self.assertLessEqual(high[axis], half_extent + 1e-9, part.name)

    def test_hidden_north_placeholders_do_not_leave_invisible_walls_or_lose_floor_support(self) -> None:
        base_path = PROJECT_ROOT / "content/tokyo-nova/blockout.json"
        with tempfile.TemporaryDirectory(prefix="tokyo-nova-collision-review-") as temporary:
            folder = Path(temporary)
            export_path = folder / "export/model.apply.json"
            export_path.parent.mkdir()
            export_path.write_text(json.dumps({
                "schemaVersion": "1",
                "slot": {"key": "root", "name": "North export"},
                "assets": {}, "components": [], "children": [],
            }), encoding="utf-8")
            output_path = folder / "north-apply.json"
            manifest = integrate_north_manifest(base_path, export_path, output_path)

        slots = {slot.get("slot", {}).get("key"): slot for slot in _slot_tree(manifest)}
        for building_key in ("building_north_yatai", "building_north_terminal_repair", "building_north_machiya"):
            subtree = list(_slot_tree(slots[building_key]))
            renderers = [component for slot in subtree for component in slot.get("components", []) if component.get("type") == "FrooxEngine.MeshRenderer"]
            self.assertTrue(renderers, building_key)
            for slot in subtree:
                slot_key = slot.get("slot", {}).get("key", "")
                renderers = [component for component in slot.get("components", []) if component.get("type") == "FrooxEngine.MeshRenderer"]
                colliders = [component for component in slot.get("components", []) if component.get("type") == "FrooxEngine.BoxCollider"]
                if slot_key.endswith("_floor"):
                    self.assertTrue(renderers, slot_key)
                    self.assertTrue(all(component.get("fields", {}).get("Enabled", True) is not False for component in renderers), slot_key)
                    self.assertTrue(colliders, slot_key)
                    self.assertTrue(all(component.get("fields", {}).get("Enabled", True) is not False for component in colliders), slot_key)
                else:
                    self.assertTrue(all(component.get("fields", {}).get("Enabled") is False for component in renderers), slot_key)
                    self.assertTrue(all(component.get("fields", {}).get("Enabled") is False for component in colliders), slot_key)

        for key in ("north_yatai_front_side_0", "north_yatai_front_side_1", "north_yatai_front_lintel"):
            components = slots[key].get("components", [])
            collider = next(component for component in components if component.get("type") == "FrooxEngine.BoxCollider")
            self.assertIs(collider.get("fields", {}).get("Enabled"), False, key)
        floor_collider = next(component for component in slots["north_yatai_floor"]["components"] if component.get("type") == "FrooxEngine.BoxCollider")
        self.assertIsNot(floor_collider.get("fields", {}).get("Enabled"), False)

    def test_sign_text_faces_south_and_ar_is_spaced_without_opaque_backplates(self) -> None:
        layout = build_layout()
        assemblies = north.build_north_sector(layout)
        by_kind = {assembly.kind: assembly for assembly in assemblies}
        signs = north.sign_manifest_entries(layout)
        physical_slots = {entry["slot"]["key"]: entry for entry in signs["physical"]["children"]}
        ar_slots = {entry["slot"]["key"]: entry for entry in signs["ar"]["children"]}
        cases = (
            ("north_yatai_sign_text", by_kind["food_stall"], "menu_sign_face"),
            ("north_repair_sign_text", by_kind["terminal_repair"], "repair_ad_diffuser"),
            ("north_housing_nameplate_text", by_kind["patched_housing_facade"], "housing_nameplate"),
        )
        for key, assembly, face_name in cases:
            text = physical_slots[key]
            self.assertLess(text["slot"]["position"][2], _face_front_z(assembly, face_name) - 0.001, key)
            self.assertEqual([round(value, 7) for value in text["slot"]["rotation"]], [0.0, 1.0, 0.0, 0.0], key)

        for ar_key, physical_key, assembly, face_name, gap in (
            ("north_ar_menu_text", "north_yatai_sign_text", by_kind["food_stall"], "menu_sign_face", 0.5),
            ("north_ar_repair_text", "north_repair_sign_text", by_kind["terminal_repair"], "repair_ad_diffuser", 0.5),
        ):
            ar_text = ar_slots[ar_key]
            self.assertLess(ar_text["slot"]["position"][2], _face_front_z(assembly, face_name) - gap, ar_key)
            self.assertTrue(ar_text["components"][0]["fields"]["Bounded"], ar_key)
            self.assertEqual([round(value, 7) for value in ar_text["slot"]["rotation"]], [0.0, 1.0, 0.0, 0.0], ar_key)
        self.assertFalse({"ar_menu", "ar_repair_ad"} & set(by_kind), "AR text must not sit inside opaque exported panels")

    def test_shared_canopy_spans_real_food_and_repair_attachments_with_supports(self) -> None:
        assemblies = {assembly.kind: assembly for assembly in north.build_north_sector(build_layout())}
        food, repair, connector = assemblies["food_stall"], assemblies["terminal_repair"], assemblies["north_facility_connector"]
        food_anchor = food.attachments["shared_canopy"]
        repair_anchor = repair.attachments["shared_canopy"]
        self.assertEqual(connector.attachments["food_stall"], food_anchor)
        self.assertEqual(connector.attachments["terminal_repair"], repair_anchor)
        food_post = next(part for part in food.transformed_parts() if part.name == "awning_rear_post_-2.15")
        self.assertLessEqual(math.dist(_ring_center(food_post.vertices[8:]), food_anchor), 1e-6)
        repair_header = next(part for part in repair.transformed_parts() if part.name == "repair_front_header")
        header_bounds = _bounds(repair_header)
        for axis in range(3):
            self.assertLessEqual(header_bounds[0][axis], repair_anchor[axis])
            self.assertLessEqual(repair_anchor[axis], header_bounds[1][axis])
        canopy = next(part for part in connector.transformed_parts() if part.name == "shared_mismatched_rain_canopy")
        canopy_bounds = _bounds(canopy)
        self.assertAlmostEqual(canopy_bounds[0][0], food_anchor[0], places=6)
        self.assertAlmostEqual(canopy_bounds[1][0], repair_anchor[0], places=6)
        self.assertIn("connector_food_stall_support", {part.name for part in connector.parts})
        self.assertIn("connector_terminal_repair_support", {part.name for part in connector.parts})
        for support_name, anchor in (("connector_food_stall_support", food_anchor), ("connector_terminal_repair_support", repair_anchor)):
            support = next(part for part in connector.transformed_parts() if part.name == support_name)
            start, end = _ring_center(support.vertices[:8]), _ring_center(support.vertices[8:])
            bearing = (anchor[0], canopy_bounds[0][1] + 0.005, anchor[2])
            self.assertLessEqual(min(math.dist(start, anchor), math.dist(end, anchor)), 1e-6, support_name)
            self.assertLessEqual(min(math.dist(start, bearing), math.dist(end, bearing)), 1e-6, support_name)

    def test_wall_equipment_disks_are_oriented_on_their_front_faces(self) -> None:
        repair = props.create("terminal_repair", (0.0, 0.0, 0.0), rotation=0.0)
        housing = props.create("patched_housing_facade", (0.0, 0.0, 0.0), rotation=0.0)
        for assembly, part_name, depth in (
            (repair, "rework_station_dial", 0.025),
            (housing, "wall_ac_fan", 0.025),
            (housing, "wall_ac_fan_hub", 0.012),
        ):
            low, high = _bounds(_part(assembly, part_name))
            spans = tuple(high[axis] - low[axis] for axis in range(3))
            self.assertAlmostEqual(spans[2], depth, places=7, msg=part_name)
            self.assertGreater(spans[0], depth * 2, part_name)
            self.assertGreater(spans[1], depth * 2, part_name)
        arbitrary_axis = geometry.cylinder("front_disk", (1.0, 2.0, 3.0), 0.1, 0.02, "metal", axis=(0.0, 0.0, -1.0))
        low, high = _bounds(arbitrary_axis)
        self.assertAlmostEqual(high[2] - low[2], 0.02, places=7)

    def test_catalog_dimensions_match_placed_model_bounds(self) -> None:
        layout = build_layout()
        catalog = {entry["kind"]: entry for entry in north.asset_catalog()}
        assemblies = {assembly.kind: assembly for assembly in north.build_north_sector(layout)}
        for kind in ("food_stall", "terminal_repair", "patched_housing_facade", "pocket_phone", "north_facility_connector"):
            low, high = assemblies[kind].bounds
            for axis in range(3):
                self.assertAlmostEqual(high[axis] - low[axis], catalog[kind]["dimensions"][axis], delta=0.002, msg=f"{kind} axis {axis}")

    def test_catalog_building_offsets_match_placed_assembly_origins(self) -> None:
        layout = build_layout()
        catalog = {entry["kind"]: entry for entry in north.asset_catalog()}
        assemblies = {assembly.kind: assembly for assembly in north.build_north_sector(layout)}
        building_keys = {"food_stall": "north_yatai", "terminal_repair": "north_terminal_repair", "patched_housing_facade": "north_machiya"}
        buildings = {entry["key"]: entry for entry in layout["buildings"]}
        for kind, building_key in building_keys.items():
            expected = tuple(assemblies[kind].origin[axis] - buildings[building_key]["center"][axis] for axis in range(3))
            actual = catalog[kind]["placement"]["origin_offset"]
            for axis in range(3):
                self.assertAlmostEqual(actual[axis], expected[axis], places=7, msg=f"{kind} axis {axis}")

    def test_north_phone_back_rests_on_the_repair_mat(self) -> None:
        assemblies = {assembly.kind: assembly for assembly in north.build_north_sector(build_layout())}
        repair, phone = assemblies["terminal_repair"], assemblies["pocket_phone"]
        mat_top = repair.origin[1] + _bounds(_part(repair, "anti_static_mat"))[1][1]
        self.assertAlmostEqual(phone.bounds[0][1], mat_top, places=7, msg="phone back must rest on the ESD mat")

    def test_repair_monitor_and_terminal_box_contact_their_support_surfaces(self) -> None:
        repair = props.create("terminal_repair", (0.0, 0.0, 0.0), rotation=0.0)
        mat = _bounds(_part(repair, "anti_static_mat"))
        foot = _bounds(_part(repair, "monitor_stand_foot"))
        neck = _bounds(_part(repair, "monitor_stand_neck"))
        monitor = _bounds(_part(repair, "monitor_45cm_shell"))
        terminal = _bounds(_part(repair, "terminal_box_35cm"))
        self.assertAlmostEqual(foot[0][1], mat[1][1], places=7, msg="monitor foot must sit on ESD mat")
        self.assertAlmostEqual(neck[0][1], foot[1][1], places=7, msg="monitor neck must meet its foot")
        self.assertAlmostEqual(monitor[0][1], neck[1][1], places=7, msg="monitor housing must sit on its neck")
        self.assertAlmostEqual(terminal[0][1], mat[1][1], places=7, msg="terminal enclosure must sit on ESD mat")


if __name__ == "__main__":
    unittest.main()
