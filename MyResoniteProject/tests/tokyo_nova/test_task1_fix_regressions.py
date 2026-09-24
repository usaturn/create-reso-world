"""Regression tests for the Task 1 review corrections."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from modeling.tokyo_nova.layout import build_layout, validate_layout
from modeling.tokyo_nova.pipeline import build_blockout_manifest, iter_slots

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _slot_by_key(manifest: dict, key: str) -> dict | None:
    return next((item for item in iter_slots(manifest) if item["slot"].get("key") == key), None)


def _component(slot: dict, type_name: str, key: str | None = None) -> dict | None:
    for component in slot.get("components", []):
        if component.get("type") == type_name and (key is None or component.get("key") == key):
            return component
    return None


def _rotated(q: list[float], vector: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z, w = q
    vx, vy, vz = vector
    tx = 2 * (y * vz - z * vy)
    ty = 2 * (z * vx - x * vz)
    tz = 2 * (x * vy - y * vx)
    return (
        vx + w * tx + y * tz - z * ty,
        vy + w * ty + z * tx - x * tz,
        vz + w * tz + x * ty - y * tx,
    )


def _ramp_surface_endpoints(slot: dict) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    mesh = _component(slot, "FrooxEngine.BoxMesh")
    assert mesh is not None
    _width, thickness, length = mesh["fields"]["Size"]
    rotation = slot["slot"]["rotation"]
    up = _rotated(rotation, (0.0, 1.0, 0.0))
    forward = _rotated(rotation, (0.0, 0.0, 1.0))
    center = slot["slot"]["position"]
    start = tuple(center[i] - forward[i] * length / 2 + up[i] * thickness / 2 for i in range(3))
    end = tuple(center[i] + forward[i] * length / 2 + up[i] * thickness / 2 for i in range(3))
    right = _rotated(rotation, (1.0, 0.0, 0.0))
    return start, end, right


def _footprints_overlap(first: dict, second: dict) -> bool:
    ax, _ay, az = first["center"]
    aw, ad = first["size"]
    bx, _by, bz = second["center"]
    bw, bd = second["size"]
    return (abs(ax - bx) * 2 < aw + bw - 1e-6) and (abs(az - bz) * 2 < ad + bd - 1e-6)


def _route_segment_hits_footprint(start: list[float], end: list[float], width: float, building: dict) -> bool:
    """Check an axis-aligned swept route rectangle against a building footprint."""
    building_x, _y, building_z = building["center"]
    building_width, building_depth = building["size"]
    xmin, xmax = building_x - building_width / 2, building_x + building_width / 2
    zmin, zmax = building_z - building_depth / 2, building_z + building_depth / 2
    if abs(start[2] - end[2]) < 1e-8:
        route_z = start[2]
        longitudinal_overlap = max(min(start[0], end[0]), xmin) < min(max(start[0], end[0]), xmax) - 1e-8
        lateral_overlap = route_z + width / 2 > zmin + 1e-8 and route_z - width / 2 < zmax - 1e-8
        return longitudinal_overlap and lateral_overlap
    if abs(start[0] - end[0]) < 1e-8:
        route_x = start[0]
        longitudinal_overlap = max(min(start[2], end[2]), zmin) < min(max(start[2], end[2]), zmax) - 1e-8
        lateral_overlap = route_x + width / 2 > xmin + 1e-8 and route_x - width / 2 < xmax - 1e-8
        return longitudinal_overlap and lateral_overlap
    raise AssertionError("layout route segments must remain axis aligned for clearance checks")


def _route_reaches_front_door(building: dict, route: dict) -> bool:
    x, _y, z = building["center"]
    width, depth = building["size"]
    front = building["front"]
    if front == "north":
        door = (x, z + depth / 2)
        normal = (0.0, 1.0)
    elif front == "south":
        door = (x, z - depth / 2)
        normal = (0.0, -1.0)
    elif front == "east":
        door = (x + width / 2, z)
        normal = (1.0, 0.0)
    else:
        door = (x - width / 2, z)
        normal = (-1.0, 0.0)
    for start, end in zip(route["points"], route["points"][1:]):
        sx, sz = start[0], start[2]
        ex, ez = end[0], end[2]
        dx, dz = ex - sx, ez - sz
        length_squared = dx * dx + dz * dz
        t = 0.0 if length_squared == 0 else max(0.0, min(1.0, ((door[0] - sx) * dx + (door[1] - sz) * dz) / length_squared))
        nearest = (sx + t * dx, sz + t * dz)
        offset = (nearest[0] - door[0], nearest[1] - door[1])
        outward = offset[0] * normal[0] + offset[1] * normal[1]
        sideways = offset[0] * -normal[1] + offset[1] * normal[0]
        if -1e-6 <= outward <= 2.5 and abs(sideways) <= 0.6 + route["width"] / 2:
            return True
    return False


class Task1ReviewRegressionTests(unittest.TestCase):
    def test_owned_root_is_raised_without_changing_local_plaza_level(self) -> None:
        layout = build_layout()
        transform = layout["root"]["transform"]
        self.assertEqual(transform["position"], [0.0, 30.0, 120.0])
        self.assertEqual(transform["rotation"], [0.0, 0.0, 0.0, 1.0])
        self.assertEqual(transform["scale"], [1.0, 1.0, 1.0])
        self.assertEqual(layout["plaza"]["level_y"], 0.0)
        manifest = build_blockout_manifest(layout)
        root = _slot_by_key(manifest, "root")
        assert root is not None
        self.assertEqual(root["slot"]["position"], [0.0, 30.0, 120.0])

    def test_all_building_footprints_are_pairwise_disjoint(self) -> None:
        buildings = build_layout()["buildings"]
        overlaps = [
            (first["key"], second["key"])
            for index, first in enumerate(buildings)
            for second in buildings[index + 1 :]
            if _footprints_overlap(first, second)
        ]
        self.assertEqual(overlaps, [])

    def test_every_road_and_entrance_sweep_stays_outside_building_footprints(self) -> None:
        layout = build_layout()
        collisions = []
        for route in layout["routes"]:
            for start, end in zip(route["points"], route["points"][1:]):
                for building in layout["buildings"]:
                    if _route_segment_hits_footprint(start, end, route["width"], building):
                        collisions.append((route["key"], building["key"]))
        self.assertEqual(collisions, [])

    def test_validator_rejects_a_main_passage_cut_through_a_building(self) -> None:
        layout = build_layout()
        building = layout["buildings"][0]
        x = building["center"][0]
        main_route = next(route for route in layout["routes"] if route["key"] == "main_north_south")
        main_route["points"] = [[x, 0.0, -48.0], [x, 0.0, 48.0]]
        errors = validate_layout(layout)
        self.assertTrue(
            any("main_north_south" in error and building["key"] in error for error in errors),
            errors,
        )

    def test_every_building_front_door_has_an_outward_route_approach(self) -> None:
        layout = build_layout()
        missing = [
            building["key"]
            for building in layout["buildings"]
            if not any(_route_reaches_front_door(building, route) for route in layout["routes"])
        ]
        self.assertEqual(missing, [])
        access_routes = [route for route in layout["routes"] if route.get("building_access_key")]
        self.assertGreaterEqual(len(access_routes), 3)
        self.assertEqual(
            {route["building_access_key"] for route in access_routes},
            {"west_game_room", "south_rehearsal", "west_talisman_shop"},
        )

    def test_declared_basement_depths_drive_floor_wells_and_landing_heights(self) -> None:
        layout = build_layout()
        manifest = build_blockout_manifest(layout)
        access_by_key = {access["key"]: access for access in layout["basement_access"]}
        expected_landing = {
            "south_theatre_basement_ramp": "theatre_basement_landing",
            "west_bar_basement_stairs": "bar_basement_landing",
        }
        for access_key, landing_key in expected_landing.items():
            access = access_by_key[access_key]
            landing = _slot_by_key(manifest, landing_key)
            self.assertIsNotNone(landing, f"missing {landing_key}")
            assert landing is not None
            floor_mesh = _component(landing, "FrooxEngine.BoxMesh")
            self.assertIsNotNone(floor_mesh)
            assert floor_mesh is not None
            center_y = landing["slot"]["position"][1]
            thickness = floor_mesh["fields"]["Size"][1]
            self.assertAlmostEqual(center_y + thickness / 2, -access["depth_below_grade"], places=6)
            self.assertEqual(access.get("floor_opening", {}).get("depth"), access.get("approach_run"))
        theatre = _slot_by_key(manifest, "building_south_theatre")
        assert theatre is not None
        floor_panels = [child for child in theatre.get("children", []) if child["slot"].get("key", "").startswith("theatre_floor_well_")]
        self.assertEqual(len(floor_panels), 3)
        for z in (-1.9, -1.0, 0.0, 1.0, 2.9):
            self.assertFalse(any(
                abs(panel["slot"]["position"][0]) <= panel_mesh["fields"]["Size"][0] / 2
                and abs(z - panel["slot"]["position"][2]) <= panel_mesh["fields"]["Size"][2] / 2
                for panel in floor_panels
                if (panel_mesh := _component(panel, "FrooxEngine.BoxMesh")) is not None
            ), f"theatre floor covers the ramp opening at z={z}")

    def test_theatre_ramp_contact_surface_runs_from_grade_to_declared_depth(self) -> None:
        manifest = build_blockout_manifest(build_layout())
        ramp = _slot_by_key(manifest, "south_theatre_basement_ramp")
        self.assertIsNotNone(ramp)
        assert ramp is not None
        start, end, right = _ramp_surface_endpoints(ramp)
        self.assertAlmostEqual(start[1], 0.0, places=6)
        self.assertAlmostEqual(end[1], -2.4, places=6)
        self.assertAlmostEqual(right[1], 0.0, places=6)

    def test_bar_basement_is_a_staircase_inside_the_declared_floor_opening(self) -> None:
        layout = build_layout()
        manifest = build_blockout_manifest(layout)
        access = next(item for item in layout["basement_access"] if item["key"] == "west_bar_basement_stairs")
        opening = access.get("floor_opening")
        self.assertIsNotNone(opening)
        assert opening is not None
        optional_steps = [_slot_by_key(manifest, f"west_bar_basement_stair_{index:02d}") for index in range(12)]
        self.assertTrue(all(step is not None for step in optional_steps), "all twelve collidable stair treads must be generated")
        steps = [step for step in optional_steps if step is not None]
        building = next(item for item in layout["buildings"] if item["key"] == access["building_key"])
        for step in steps:
            x, _y, z = step["slot"]["position"]
            mesh = _component(step, "FrooxEngine.BoxMesh")
            self.assertIsNotNone(mesh)
            assert mesh is not None
            size_x, _height, size_z = mesh["fields"]["Size"]
            open_x = building["center"][0] + opening["center"][0]
            open_z = building["center"][2] + opening["center"][1]
            open_width, open_depth = opening["size"]
            self.assertGreaterEqual(x - size_x / 2, open_x - open_width / 2 - 1e-6)
            self.assertLessEqual(x + size_x / 2, open_x + open_width / 2 + 1e-6)
            self.assertGreaterEqual(z - size_z / 2, open_z - open_depth / 2 - 1e-6)
            self.assertLessEqual(z + size_z / 2, open_z + open_depth / 2 + 1e-6)
        landing = _slot_by_key(manifest, "bar_basement_landing")
        self.assertIsNotNone(landing)
        assert landing is not None
        last_step = steps[-1]
        landing_mesh = _component(landing, "FrooxEngine.BoxMesh")
        last_mesh = _component(last_step, "FrooxEngine.BoxMesh")
        assert landing_mesh is not None and last_mesh is not None
        self.assertAlmostEqual(
            last_step["slot"]["position"][1] + last_mesh["fields"]["Size"][1] / 2,
            landing["slot"]["position"][1] + landing_mesh["fields"]["Size"][1] / 2,
            places=6,
        )
        landing_x = landing["slot"]["position"][0]
        landing_width = landing_mesh["fields"]["Size"][0]
        last_x = last_step["slot"]["position"][0]
        last_width = last_mesh["fields"]["Size"][0]
        self.assertAlmostEqual(landing_x + landing_width / 2, last_x - last_width / 2, places=6)

    def test_roof_ramp_frame_is_gravity_up_and_contact_ends_meet_grade_and_roof(self) -> None:
        layout = build_layout()
        manifest = build_blockout_manifest(layout)
        roof = next(building for building in layout["buildings"] if building["key"] == "west_roof_access")
        ramp = _slot_by_key(manifest, "roof_access_ramp")
        self.assertIsNotNone(ramp)
        assert ramp is not None
        start, end, right = _ramp_surface_endpoints(ramp)
        self.assertAlmostEqual(start[1], 0.0, places=6)
        self.assertAlmostEqual(end[1], roof["height"] + 0.11, places=6)
        self.assertAlmostEqual(end[0], roof["center"][0] - (roof["size"][0] + 0.3) / 2, places=6)
        self.assertAlmostEqual(end[2], roof["center"][2], places=6)
        self.assertAlmostEqual(right[1], 0.0, places=6)
        self.assertGreater(_rotated(ramp["slot"]["rotation"], (0.0, 1.0, 0.0))[1], 0.0)

    def test_roof_overlook_camera_is_above_the_roof_by_eye_height(self) -> None:
        layout = build_layout()
        roof = next(building for building in layout["buildings"] if building["key"] == "west_roof_access")
        camera = next(camera for camera in layout["cameras"] if camera["key"] == "roof_overlook")
        self.assertGreaterEqual(camera["position"][1], roof["height"] + 0.11 + 1.6)

    def test_prop_catalog_omits_payment_live_stage_and_natural_roof_garden_near_misses(self) -> None:
        excluded = {
            "ticket_dispenser",
            "coin_return_mechanism",
            "theatre_ticket_window",
            "stage_truss",
            "floor_monitor_speaker",
            "roof_planter_trough",
        }
        keys = {item["key"] for item in build_layout()["prop_catalog"]}
        self.assertTrue(excluded.isdisjoint(keys), sorted(excluded & keys))
        self.assertGreaterEqual(len(keys), 60)
        roof_deck = next(building for building in build_layout()["buildings"] if building["key"] == "east_roof_garden")
        self.assertEqual(roof_deck["kind"], "roof_utility_deck")

    def test_regeneration_writes_source_config_without_overwriting_live_pipeline_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tokyo-nova-evidence-") as temp_dir:
            root = Path(temp_dir)
            evidence = root / ".resoloop" / "tokyo-nova" / "pipeline.json"
            evidence.parent.mkdir(parents=True)
            original = {"ownership": {"root_id": "Reso_6654"}, "capture": {"status": "blocked-CAPTURE_EXPORT_TIMEOUT"}}
            evidence.write_text(json.dumps(original), encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPOSITORY_ROOT), env.get("PYTHONPATH", "")]))
            result = subprocess.run(
                [sys.executable, "-m", "modeling.tokyo_nova.pipeline", "--output-dir", "content/tokyo-nova"],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(evidence.read_text(encoding="utf-8")), original)
            source_config = root / "content" / "tokyo-nova" / "pipeline-config.json"
            self.assertTrue(source_config.is_file())
            config = json.loads(source_config.read_text(encoding="utf-8"))
            self.assertNotIn("root_id", config.get("ownership", {}))


if __name__ == "__main__":
    unittest.main()
