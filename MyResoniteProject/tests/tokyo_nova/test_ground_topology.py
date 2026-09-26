"""Geometry-level regression tests for basement ground cutouts and floor support."""
from __future__ import annotations

import math
import unittest
from collections.abc import Iterator, Sequence
from typing import Any

from modeling.tokyo_nova.layout import build_layout
from modeling.tokyo_nova.pipeline import build_blockout_manifest, iter_slots


def _component(slot: dict[str, Any], type_name: str) -> dict[str, Any] | None:
    return next((item for item in slot.get("components", []) if item.get("type") == type_name), None)


def _ground_tiles(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in manifest.get("children", [])
        if item["slot"].get("key", "").startswith("outer_ground_tile_")
    ]


def _cutouts(layout: dict[str, Any]) -> list[tuple[float, float, float, float]]:
    buildings = {item["key"]: item for item in layout["buildings"]}
    result = []
    for access in layout["basement_access"]:
        building = buildings[access["building_key"]]
        opening = access["floor_opening"]
        center_x = building["center"][0] + opening["center"][0]
        center_z = building["center"][2] + opening["center"][1]
        size_x, size_z = opening["size"]
        result.append((center_x - size_x / 2, center_x + size_x / 2, center_z - size_z / 2, center_z + size_z / 2))
    return result


def _collider_covers_xz(slot: dict[str, Any], collider: dict[str, Any], x: float, z: float) -> bool:
    position = slot["slot"]["position"]
    rotation = slot["slot"].get("rotation", [0.0, 0.0, 0.0, 1.0])
    size = collider["fields"]["Size"]
    offset = collider["fields"].get("Offset", [0.0, 0.0, 0.0])
    assert rotation == [0.0, 0.0, 0.0, 1.0], "ground tiles must be axis-aligned"
    center_x, center_z = position[0] + offset[0], position[2] + offset[2]
    return center_x - size[0] / 2 - 1e-9 <= x <= center_x + size[0] / 2 + 1e-9 and center_z - size[2] / 2 - 1e-9 <= z <= center_z + size[2] / 2 + 1e-9


def _rotate(q: Sequence[float], v: Sequence[float]) -> tuple[float, float, float]:
    x, y, z, w = (float(value) for value in q)
    vx, vy, vz = (float(value) for value in v)
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + y * tz - z * ty, vy + w * ty + z * tx - x * tz, vz + w * tz + x * ty - y * tx)


def _multiply_quaternions(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float, float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def _scale_vectors(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] * b[0], a[1] * b[1], a[2] * b[2])


def _horizontal_boxes(manifest: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield emitted low-profile horizontal BoxMesh/BoxCollider shapes in root-local space."""
    identity = {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 0.0, 1.0), "scale": (1.0, 1.0, 1.0)}

    def visit(node: dict[str, Any], parent: dict[str, Any]) -> Iterator[dict[str, Any]]:
        slot = node["slot"]
        local_position = slot.get("position", [0.0, 0.0, 0.0])
        local_rotation = slot.get("rotation", [0.0, 0.0, 0.0, 1.0])
        local_scale = slot.get("scale", [1.0, 1.0, 1.0])
        scaled_position = _scale_vectors(parent["scale"], local_position)
        rotated_position = _rotate(parent["rotation"], scaled_position)
        position = tuple(parent["position"][i] + rotated_position[i] for i in range(3))
        rotation = _multiply_quaternions(parent["rotation"], local_rotation)
        scale = _scale_vectors(parent["scale"], local_scale)
        up = _rotate(rotation, (0.0, 1.0, 0.0))
        for component in node.get("components", []):
            if component.get("type") not in ("FrooxEngine.BoxMesh", "FrooxEngine.BoxCollider"):
                continue
            fields = component.get("fields", {})
            if "Size" not in fields:
                continue
            size = _scale_vectors(scale, fields["Size"])
            if abs(up[0]) > 1e-8 or up[1] < 1.0 - 1e-8 or abs(up[2]) > 1e-8:
                continue
            if size[1] >= min(size[0], size[2]):
                continue
            offset = fields.get("Offset", [0.0, 0.0, 0.0]) if component["type"] == "FrooxEngine.BoxCollider" else [0.0, 0.0, 0.0]
            rotated_offset = _rotate(rotation, _scale_vectors(scale, offset))
            center = tuple(position[i] + rotated_offset[i] for i in range(3))
            corners = [
                _rotate(rotation, (sx * size[0] / 2, 0.0, sz * size[2] / 2))
                for sx in (-1, 1) for sz in (-1, 1)
            ]
            yield {
                "key": slot["key"],
                "type": component["type"],
                "center": center,
                "size": size,
                "bounds_xz": (
                    center[0] + min(corner[0] for corner in corners),
                    center[0] + max(corner[0] for corner in corners),
                    center[2] + min(corner[2] for corner in corners),
                    center[2] + max(corner[2] for corner in corners),
                ),
                "bounds_y": (center[1] - size[1] / 2, center[1] + size[1] / 2),
            }
        child_parent = {"position": position, "rotation": rotation, "scale": scale}
        for child in node.get("children", []):
            yield from visit(child, child_parent)

    for child in manifest.get("children", []):
        yield from visit(child, identity)


def _strict_rect_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] < b[1] - 1e-9 and b[0] < a[1] - 1e-9 and a[2] < b[3] - 1e-9 and b[2] < a[3] - 1e-9


class GroundTopologyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = build_layout()
        self.manifest = build_blockout_manifest(self.layout)
        self.tiles = _ground_tiles(self.manifest)
        self.cutouts = _cutouts(self.layout)

    def _support_count(self, x: float, z: float) -> int:
        count = 0
        for tile in self.tiles:
            collider = _component(tile, "FrooxEngine.BoxCollider")
            if collider is not None and _collider_covers_xz(tile, collider, x, z):
                self.assertAlmostEqual(tile["slot"]["position"][1] + collider["fields"]["Size"][1] / 2, 0.0, places=8)
                count += 1
        return count

    def test_partitioned_ground_mesh_and_collider_shapes_leave_only_the_two_basement_cutouts(self) -> None:
        self.assertGreaterEqual(len(self.tiles), 2, "the 100m ground slab must be split into support tiles")
        self.assertEqual(len(self.cutouts), 2, "the layout declares exactly two basement openings")
        rectangles: list[tuple[float, float, float, float]] = []
        covered_area = 0.0
        for tile in self.tiles:
            key = tile["slot"]["key"]
            mesh = _component(tile, "FrooxEngine.BoxMesh")
            collider = _component(tile, "FrooxEngine.BoxCollider")
            self.assertIsNotNone(mesh, key)
            self.assertIsNotNone(collider, key)
            assert mesh is not None and collider is not None
            mesh_size = mesh["fields"]["Size"]
            collider_fields = collider["fields"]
            self.assertEqual(collider_fields["Size"], mesh_size, key)
            self.assertEqual(collider_fields["Offset"], [0.0, 0.0, 0.0], key)
            self.assertEqual(collider_fields["Type"], "Static", key)
            self.assertTrue(collider_fields["CharacterCollider"], key)
            position = tile["slot"]["position"]
            self.assertAlmostEqual(position[1] + mesh_size[1] / 2, 0.0, places=8, msg=key)
            rect = (position[0] - mesh_size[0] / 2, position[0] + mesh_size[0] / 2, position[2] - mesh_size[2] / 2, position[2] + mesh_size[2] / 2)
            self.assertGreater(rect[1] - rect[0], 0)
            self.assertGreater(rect[3] - rect[2], 0)
            self.assertGreaterEqual(rect[0], -50)
            self.assertLessEqual(rect[1], 50)
            self.assertGreaterEqual(rect[2], -50)
            self.assertLessEqual(rect[3], 50)
            rectangles.append(rect)
            covered_area += mesh_size[0] * mesh_size[2]
        for index, first in enumerate(rectangles):
            for second in rectangles[index + 1 :]:
                self.assertFalse(_strict_rect_overlap(first, second), (first, second))
        opening_area = sum((x1 - x0) * (z1 - z0) for x0, x1, z0, z1 in self.cutouts)
        self.assertAlmostEqual(covered_area, 10000.0 - opening_area, places=6)
        for ix in range(100):
            x = -49.5 + ix
            for iz in range(100):
                z = -49.5 + iz
                in_opening = any(x0 < x < x1 and z0 < z < z1 for x0, x1, z0, z1 in self.cutouts)
                self.assertEqual(self._support_count(x, z), 0 if in_opening else 1, (x, z))
        for x0, x1, z0, z1 in self.cutouts:
            for ix in range(1, 5):
                for iz in range(1, 5):
                    x = x0 + (x1 - x0) * ix / 5
                    z = z0 + (z1 - z0) * iz / 5
                    self.assertEqual(self._support_count(x, z), 0, (x, z))

    def test_the_whole_plaza_and_every_route_are_supported_by_a_collider_at_y_zero(self) -> None:
        self.assertGreaterEqual(len(self.tiles), 2, "supporting ground tiles must be emitted")
        for ix in range(41):
            x = -10.0 + ix * 0.5
            for iz in range(41):
                z = -10.0 + iz * 0.5
                self.assertEqual(self._support_count(x, z), 1, ("plaza", x, z))
        for route in self.layout["routes"]:
            for start, end in zip(route["points"], route["points"][1:]):
                dx, dz = end[0] - start[0], end[2] - start[2]
                length = math.hypot(dx, dz)
                steps = max(1, math.ceil(length * 2))
                half_width = route["width"] / 2 - 0.05
                perpendicular = (0.0, 1.0) if abs(dx) >= abs(dz) else (1.0, 0.0)
                for index in range(steps + 1):
                    t = index / steps
                    center_x = start[0] + dx * t
                    center_z = start[2] + dz * t
                    for offset in (-half_width, 0.0, half_width):
                        x = center_x + perpendicular[0] * offset
                        z = center_z + perpendicular[1] * offset
                        self.assertGreaterEqual(self._support_count(x, z), 1, (route["key"], x, z))

    def test_both_descent_paths_are_open_at_grade_and_landings_meet_declared_depth(self) -> None:
        self.assertEqual(len(self.layout["basement_access"]), 2)
        boxes = list(_horizontal_boxes(self.manifest))
        for access in self.layout["basement_access"]:
            rect = next(
                rect for rect in self.cutouts
                if self._opening_matches_access(rect, access)
            )
            expected_access_slots = {access["key"], access["landing_key"]}
            prefix = access["key"].removesuffix("_stairs") + "_stair_"
            if access["kind"] == "open_stairwell_and_landing":
                expected_access_slots.update(f"{prefix}{index:02d}" for index in range(int(access["steps"])))
            sample_points = [
                (rect[0] + (rect[1] - rect[0]) * ix / 5, rect[2] + (rect[3] - rect[2]) * iz / 5)
                for ix in range(1, 5) for iz in range(1, 5)
            ]
            for x, z in sample_points:
                self.assertEqual(self._support_count(x, z), 0, (access["key"], x, z))
                for shape in boxes:
                    if shape["key"] in expected_access_slots:
                        continue
                    vertical_overlap = shape["bounds_y"][1] > -0.01 and shape["bounds_y"][0] < 0.36
                    x0, x1, z0, z1 = shape["bounds_xz"]
                    horizontal_overlap = x0 < x < x1 and z0 < z < z1
                    self.assertFalse(vertical_overlap and horizontal_overlap, (access["key"], shape["key"], shape["type"], x, z))
            landing = next(item for item in iter_slots(self.manifest) if item["slot"].get("key") == access["landing_key"])
            landing_mesh = _component(landing, "FrooxEngine.BoxMesh")
            landing_collider = _component(landing, "FrooxEngine.BoxCollider")
            self.assertIsNotNone(landing_mesh, access["landing_key"])
            self.assertIsNotNone(landing_collider, access["landing_key"])
            assert landing_mesh is not None and landing_collider is not None
            self.assertEqual(landing_collider["fields"]["Size"], landing_mesh["fields"]["Size"])
            self.assertAlmostEqual(
                landing["slot"]["position"][1] + landing_mesh["fields"]["Size"][1] / 2,
                -access["depth_below_grade"],
                places=6,
            )
            if access["kind"] == "open_ramp_and_landing":
                ramp = next(item for item in iter_slots(self.manifest) if item["slot"].get("key") == access["key"])
                self.assertIsNotNone(_component(ramp, "FrooxEngine.BoxCollider"), access["key"])
            else:
                steps = [item for item in iter_slots(self.manifest) if item["slot"].get("key", "").startswith(prefix)]
                self.assertEqual(len(steps), int(access["steps"]))
                self.assertTrue(all(_component(step, "FrooxEngine.BoxCollider") is None for step in steps))
                surface = next(item for item in iter_slots(self.manifest) if item["slot"].get("key") == f"{access['key']}_walk_surface")
                self.assertIsNotNone(_component(surface, "FrooxEngine.BoxCollider"))
                self.assertIsNone(_component(surface, "FrooxEngine.MeshRenderer"))

    def _opening_matches_access(self, rect: tuple[float, float, float, float], access: dict[str, Any]) -> bool:
        buildings = {item["key"]: item for item in self.layout["buildings"]}
        building = buildings[access["building_key"]]
        opening = access["floor_opening"]
        x = building["center"][0] + opening["center"][0]
        z = building["center"][2] + opening["center"][1]
        size_x, size_z = opening["size"]
        expected = (x - size_x / 2, x + size_x / 2, z - size_z / 2, z + size_z / 2)
        return all(abs(a - b) < 1e-9 for a, b in zip(rect, expected))


if __name__ == "__main__":
    unittest.main()
