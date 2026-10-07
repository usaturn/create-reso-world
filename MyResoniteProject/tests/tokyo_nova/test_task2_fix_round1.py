"""TDD regressions for the Task 2 north-asset review findings."""
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


def _placed_point(assembly: props.Assembly, point: tuple[float, float, float]) -> tuple[float, float, float]:
    cosine, sine = math.cos(assembly.rotation), math.sin(assembly.rotation)
    return (
        assembly.origin[0] + point[0] * cosine + point[2] * sine,
        assembly.origin[1] + point[1],
        assembly.origin[2] - point[0] * sine + point[2] * cosine,
    )


def _point_hits_colliders(point: tuple[float, float, float], colliders: list[dict]) -> bool:
    for slot in colliders:
        for component in slot.get("components", []):
            if component.get("type") != "FrooxEngine.BoxCollider":
                continue
            fields = component.get("fields", {})
            if fields.get("Enabled") is not True:
                continue
            slot_position = slot.get("slot", {}).get("position", [0.0, 0.0, 0.0])
            offset = fields.get("Offset", [0.0, 0.0, 0.0])
            size = fields["Size"]
            if all(abs(point[axis] - slot_position[axis] - offset[axis]) <= size[axis] / 2 + 1e-9 for axis in range(3)):
                return True
    return False


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
        source_base = PROJECT_ROOT / "content/tokyo-nova/blockout.json"
        with tempfile.TemporaryDirectory(prefix="tokyo-nova-collision-review-") as temporary:
            folder = Path(temporary)
            base_manifest = json.loads(source_base.read_text(encoding="utf-8"))
            for slot in _slot_tree(base_manifest):
                if slot.get("slot", {}).get("key") in {"north_yatai_floor", "north_terminal_repair_floor", "north_machiya_floor"}:
                    for component in slot.get("components", []):
                        if component.get("type") in {"FrooxEngine.MeshRenderer", "FrooxEngine.BoxCollider"}:
                            component.setdefault("fields", {})["Enabled"] = False
            base_path = folder / "blockout-with-disabled-floors.json"
            base_path.write_text(json.dumps(base_manifest), encoding="utf-8")
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
                    self.assertTrue(colliders, slot_key)
                    self.assertTrue(all(component.get("fields", {}).get("Enabled") is True for component in renderers), slot_key)
                    self.assertTrue(all(component.get("fields", {}).get("Enabled") is True for component in colliders), slot_key)
                else:
                    self.assertTrue(all(component.get("fields", {}).get("Enabled") is False for component in renderers), slot_key)
                    self.assertTrue(all(component.get("fields", {}).get("Enabled") is False for component in colliders), slot_key)

        for key in ("north_yatai_front_side_0", "north_yatai_front_side_1", "north_yatai_front_lintel"):
            components = slots[key].get("components", [])
            collider = next(component for component in components if component.get("type") == "FrooxEngine.BoxCollider")
            self.assertIs(collider.get("fields", {}).get("Enabled"), False, key)
        floor_collider = next(component for component in slots["north_yatai_floor"]["components"] if component.get("type") == "FrooxEngine.BoxCollider")
        self.assertIsNot(floor_collider.get("fields", {}).get("Enabled"), False)

    def test_detailed_north_colliders_match_solid_geometry_and_leave_passages_open(self) -> None:
        layout = build_layout()
        assemblies = {assembly.kind: assembly for assembly in north.build_north_sector(layout)}
        with tempfile.TemporaryDirectory(prefix="tokyo-nova-collider-manifest-") as temporary:
            folder = Path(temporary)
            export_path = folder / "export/model.apply.json"
            export_path.parent.mkdir()
            export_path.write_text(json.dumps({
                "schemaVersion": "1",
                "slot": {"key": "root", "name": "North export"},
                "assets": {}, "components": [], "children": [],
            }), encoding="utf-8")
            manifest = integrate_north_manifest(
                PROJECT_ROOT / "content/tokyo-nova/blockout.json",
                export_path,
                folder / "north-apply.json",
            )

        slots = {slot.get("slot", {}).get("key"): slot for slot in _slot_tree(manifest)}
        collision_group = slots.get("north_collision_geometry")
        if collision_group is None:
            self.fail("detailed wall/counter colliders must be emitted under their own group")
        colliders = collision_group.get("children", [])
        by_key = {slot["slot"]["key"]: slot for slot in colliders}

        expected_parts = {
            "food_stall": {"counter_body", "counter_top"},
            "terminal_repair": {
                "repair_shop_rear_wall", "repair_shop_side_wall_-2.31", "repair_shop_side_wall_2.31",
                "repair_front_pier_-2.31", "repair_front_pier_2.31", "repair_front_header",
                "repair_window_glass_0", "repair_window_glass_1", "retracted_rolling_shutter",
            },
            "patched_housing_facade": {
                part.name for part in assemblies["patched_housing_facade"].parts if part.name.startswith("housing_masonry_")
            } | {
                part.name for part in assemblies["patched_housing_facade"].parts if part.name.startswith("window_glazing_")
            } | {"entry_door_leaf"},
        }
        expected_keys = {
            f"north_collision_{kind}_{part_name}"
            for kind, names in expected_parts.items()
            for part_name in names
        }
        self.assertEqual(set(by_key), expected_keys, "only named solid surfaces should receive colliders")

        for kind, names in expected_parts.items():
            parts = {part.name: part for part in assemblies[kind].transformed_parts()}
            for part_name in names:
                collider_slot = by_key[f"north_collision_{kind}_{part_name}"]
                mesh_bounds = _bounds(parts[part_name])
                component = next(entry for entry in collider_slot["components"] if entry["type"] == "FrooxEngine.BoxCollider")
                fields = component["fields"]
                expected_center = [(mesh_bounds[0][axis] + mesh_bounds[1][axis]) / 2 for axis in range(3)]
                expected_size = [mesh_bounds[1][axis] - mesh_bounds[0][axis] for axis in range(3)]
                self.assertEqual(collider_slot["slot"]["rotation"], [0.0, 0.0, 0.0, 1.0], part_name)
                self.assertEqual(collider_slot["slot"]["scale"], [1.0, 1.0, 1.0], part_name)
                for axis in range(3):
                    self.assertAlmostEqual(collider_slot["slot"]["position"][axis], expected_center[axis], places=7, msg=part_name)
                    self.assertAlmostEqual(fields["Size"][axis], expected_size[axis], places=7, msg=part_name)
                    self.assertEqual(fields["Offset"][axis], 0.0, part_name)
                self.assertIs(fields["Enabled"], True, part_name)
                self.assertIs(fields["CharacterCollider"], True, part_name)
                self.assertEqual(fields["Type"], "Static", part_name)

        food, repair, housing = assemblies["food_stall"], assemblies["terminal_repair"], assemblies["patched_housing_facade"]
        self.assertTrue(_point_hits_colliders(_placed_point(food, (0.0, 1.0, 0.0)), colliders), "the visible food counter must block through its solid body")
        self.assertFalse(_point_hits_colliders(_placed_point(food, (0.0, 1.0, 1.0)), colliders), "the aisle in front of the counter must remain passable")
        self.assertTrue(_point_hits_colliders(_placed_point(repair, (0.0, 1.68, -0.94)), colliders), "the visible repair-shop back wall must block")
        self.assertTrue(_point_hits_colliders(_placed_point(repair, (2.31, 1.68, 0.02)), colliders), "the visible repair-shop side wall must block")
        self.assertFalse(_point_hits_colliders(_placed_point(repair, (0.0, 1.0, 3.14)), colliders), "the actual repair-shop doorway must remain open")
        self.assertTrue(_point_hits_colliders(_placed_point(housing, (0.0, 4.5, 0.0)), colliders), "closed housing masonry must block")
        self.assertTrue(_point_hits_colliders(_placed_point(housing, (-1.78, 3.0, -0.17)), colliders), "visible window glazing must have a matching collider")

    def test_phone_footprint_is_inside_mat_and_rests_on_its_top(self) -> None:
        assemblies = {assembly.kind: assembly for assembly in north.build_north_sector(build_layout())}
        repair, phone = assemblies["terminal_repair"], assemblies["pocket_phone"]
        mat = next(part for part in repair.transformed_parts() if part.name == "anti_static_mat")
        mat_bounds, phone_bounds = _bounds(mat), phone.bounds
        self.assertGreaterEqual(phone_bounds[0][0], mat_bounds[0][0], "phone left edge must be inside the actual mat")
        self.assertLessEqual(phone_bounds[1][0], mat_bounds[1][0], "phone right edge must be inside the actual mat")
        self.assertGreaterEqual(phone_bounds[0][2], mat_bounds[0][2], "phone back edge must be inside the actual mat")
        self.assertLessEqual(phone_bounds[1][2], mat_bounds[1][2], "phone front edge must be inside the actual mat")
        self.assertAlmostEqual(phone_bounds[0][1], mat_bounds[1][1], places=7, msg="phone back must rest on the ESD mat")

    def test_phone_bounds_do_not_overlap_other_repair_desk_parts(self) -> None:
        assemblies = {assembly.kind: assembly for assembly in north.build_north_sector(build_layout())}
        repair, phone = assemblies["terminal_repair"], assemblies["pocket_phone"]
        phone_bounds = phone.bounds
        support_parts = {"anti_static_mat", "repair_bench_top"}
        overlaps = []
        for part in repair.transformed_parts():
            if part.name in support_parts:
                continue
            part_bounds = _bounds(part)
            if all(
                phone_bounds[0][axis] < part_bounds[1][axis] - 1e-9
                and phone_bounds[1][axis] > part_bounds[0][axis] + 1e-9
                for axis in range(3)
            ):
                overlaps.append(part.name)
        self.assertEqual(overlaps, [], "phone geometry must not overlap raised repair-desk equipment")

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
