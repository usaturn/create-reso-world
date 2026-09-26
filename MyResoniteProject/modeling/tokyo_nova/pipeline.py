"""Build stable ResoLoop manifests and record the Blender-to-Resonite pipeline."""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
from collections.abc import Iterable, Sequence
from itertools import pairwise
from pathlib import Path
from typing import Any

from modeling.tokyo_nova.layout import build_layout, validate_layout
from modeling.tokyo_nova.sector_pipeline import (  # noqa: F401
    _source_for_output,
    enrich_layout,
    integrate_north_manifest,
)

RESOLOOP_URL = "ws://localhost:54238/"
ROOT_KEY = "tokyo-nova-west-slum"
STATE_PATH = ".resoloop/tokyo-nova/state/blockout.json"
PROBE_STATE_PATH = ".resoloop/tokyo-nova/state/probe.json"


def resonite_to_blender(point: Sequence[float]) -> tuple[float, float, float]:
    """Convert Resonite XYZ to Blender XZY at the generation boundary."""
    if len(point) != 3:
        raise ValueError("a coordinate must contain exactly three values")
    x, y, z = (float(value) for value in point)
    return (x, z, y)


def iter_slots(manifest: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield root and nested slot declarations in manifest order."""
    yield manifest
    for child in manifest.get("children", []):
        yield from iter_slots(child)


def add_japanese_probe_sign(manifest: dict[str, Any]) -> None:
    """Attach one native Japanese TextRenderer label to an exported probe root."""
    target = next((item for item in iter_slots(manifest) if item.get("slot", {}).get("key") == "root"), None)
    if target is None:
        raise ValueError("probe manifest has no stable root slot")
    children = target.setdefault("children", [])
    sign = {
        "slot": {"key": "probe_japanese_sign", "name": "Japanese engine text · non-symmetric 1 m face", "position": [0.0, 0.02, 0.315], "rotation": [0.0, 0.0, 0.0, 1.0]},
        "components": [{"key": "probe_japanese_text", "type": "FrooxEngine.TextRenderer", "fields": {"Text": "非対称・1m計測面\n前面 (+Z)", "Size": 0.12, "Color": [0.8, 0.95, 1.0, 1.0]}}],
    }
    for index, child in enumerate(children):
        if child.get("slot", {}).get("key") == "probe_japanese_sign":
            children[index] = sign
            break
    else:
        children.append(sign)


def prepare_probe_manifest(source_path: Path, output_path: Path) -> dict[str, Any]:
    """Make a Blender export a safe temporary ResoLoop test root with assets/text/capture."""
    source_path, output_path = source_path.resolve(), output_path.resolve()
    manifest = json.loads(source_path.read_text(encoding="utf-8"))
    if manifest.get("slot", {}).get("key") != "root":
        raise ValueError("Blender export manifest is missing its root slot")
    manifest.setdefault("ownership", {})["key"] = "tokyo-nova-probe"
    manifest["slot"].update({"name": "ResoLoop_Test_TokyoNovaProbe", "parent": "Root", "position": [0.0, 0.0, 80.0], "rotation": [0.0, 0.0, 0.0, 1.0], "scale": [1.0, 1.0, 1.0]})
    for asset in manifest.get("assets", {}).values():
        source = (source_path.parent / asset["source"]).resolve()
        asset["source"] = Path(os.path.relpath(source, output_path.parent)).as_posix()
    add_japanese_probe_sign(manifest)
    manifest["cameras"] = {"probe_front": {"position": [0.0, 0.15, 76.7], "target": [0.0, 0.0, 80.0], "fieldOfView": 55, "width": 1280, "height": 720, "representative": True}}
    manifest["tests"] = [{"name": "asymmetric-probe-root-exists", "assertions": [{"target": "$slot:root", "exists": True}]}]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def _component(key: str, type_name: str, fields: dict[str, Any]) -> dict[str, Any]:
    return {"key": key, "type": type_name, "fields": fields}


def _box_slot(key: str, name: str, position: Sequence[float], size: Sequence[float], material_key: str, *, rotation: Sequence[float] = (0, 0, 0, 1), collider: bool = False) -> dict[str, Any]:
    mesh_key = f"{key}_mesh"
    components = [
        _component(mesh_key, "FrooxEngine.BoxMesh", {"Size": [float(v) for v in size]}),
        _component(f"{key}_renderer", "FrooxEngine.MeshRenderer", {"Mesh": f"$component:{mesh_key}", "Materials": [f"$component:{material_key}"]}),
    ]
    if collider:
        components.append(_component(f"{key}_collider", "FrooxEngine.BoxCollider", {"Type": "Static", "CharacterCollider": True, "Offset": [0, 0, 0], "Size": [float(v) for v in size]}))
    return {"slot": {"key": key, "name": f"{name} · {key}", "position": [float(v) for v in position], "rotation": [float(v) for v in rotation], "scale": [1, 1, 1]}, "components": components}


_GROUND_BOUNDS_XZ = (-50.0, 50.0, -50.0, 50.0)
_GROUND_THICKNESS = 0.08


def _basement_cutout_rectangles(layout: dict[str, Any]) -> list[tuple[float, float, float, float]]:
    """Return root-local (xmin, xmax, zmin, zmax) holes from declared floor openings."""
    accesses = layout.get("basement_access", [])
    if len(accesses) != 2:
        raise ValueError(f"the blockout ground requires exactly two basement cutouts, found {len(accesses)}")
    buildings = {building["key"]: building for building in layout["buildings"]}
    holes = []
    for access in accesses:
        building = buildings[access["building_key"]]
        opening = access["floor_opening"]
        center_x = float(building["center"][0]) + float(opening["center"][0])
        center_z = float(building["center"][2]) + float(opening["center"][1])
        size_x, size_z = (float(value) for value in opening["size"])
        if size_x <= 0 or size_z <= 0:
            raise ValueError(f"basement access {access['key']} has a nonpositive ground cutout")
        hole = (center_x - size_x / 2, center_x + size_x / 2, center_z - size_z / 2, center_z + size_z / 2)
        xmin, xmax, zmin, zmax = _GROUND_BOUNDS_XZ
        if hole[0] < xmin or hole[1] > xmax or hole[2] < zmin or hole[3] > zmax:
            raise ValueError(f"basement access {access['key']} ground cutout lies outside the perimeter ground")
        holes.append(hole)
    return holes


def _partition_ground(layout: dict[str, Any]) -> list[tuple[float, float, float, float]]:
    """Tile the perimeter ground without overlap, leaving each declared access open."""
    xmin, xmax, zmin, zmax = _GROUND_BOUNDS_XZ
    holes = _basement_cutout_rectangles(layout)
    x_edges = sorted({xmin, xmax, *(edge for hole in holes for edge in hole[:2])})
    regions: list[tuple[float, float, float, float]] = []
    for x0, x1 in pairwise(x_edges):
        midpoint = (x0 + x1) / 2
        blocked = sorted((hole[2], hole[3]) for hole in holes if hole[0] < midpoint < hole[1])
        merged: list[tuple[float, float]] = []
        for low, high in blocked:
            if merged and low <= merged[-1][1] + 1e-9:
                merged[-1] = (merged[-1][0], max(merged[-1][1], high))
            else:
                merged.append((low, high))
        cursor = zmin
        for low, high in merged:
            if low > cursor + 1e-9:
                regions.append((x0, x1, cursor, low))
            cursor = max(cursor, high)
        if cursor < zmax - 1e-9:
            regions.append((x0, x1, cursor, zmax))
    if not regions:
        raise ValueError("basement cutouts removed the complete perimeter ground")
    return regions


def _ground_tile_slots(layout: dict[str, Any]) -> list[dict[str, Any]]:
    """Emit the sole grade-level collision topology from the partition rectangles."""
    tiles = []
    for index, (xmin, xmax, zmin, zmax) in enumerate(_partition_ground(layout)):
        width, depth = xmax - xmin, zmax - zmin
        key = f"outer_ground_tile_{index:02d}"
        tiles.append(_box_slot(
            key,
            "Tokyo Nova supporting ground tile · cut around basement openings",
            [(xmin + xmax) / 2, -_GROUND_THICKNESS / 2, (zmin + zmax) / 2],
            [width, _GROUND_THICKNESS, depth],
            "mat_ground",
            collider=True,
        ))
    return tiles


def _segment_rotation(start: Sequence[float], end: Sequence[float]) -> tuple[float, float, float, float]:
    yaw = math.atan2(float(end[0] - start[0]), float(end[2] - start[2]))
    return (0, math.sin(yaw / 2), 0, math.cos(yaw / 2))


def _cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(vector: Sequence[float]) -> tuple[float, float, float]:
    length = math.sqrt(sum(float(value) ** 2 for value in vector))
    if length <= 1e-12:
        raise ValueError("a ramp axis cannot have zero length")
    return (float(vector[0]) / length, float(vector[1]) / length, float(vector[2]) / length)


def _gravity_up_ramp_rotation(direction: Sequence[float]) -> tuple[float, float, float, float]:
    """Orient local +Z along the ramp while keeping local +X horizontal."""
    forward = _unit(direction)
    world_up = (0.0, 1.0, 0.0)
    right_raw = _cross(world_up, forward)
    if sum(value * value for value in right_raw) <= 1e-12:
        raise ValueError("a ramp cannot be parallel to gravity up")
    right = _unit(right_raw)
    up = _unit(_cross(forward, right))
    m00, m01, m02 = right[0], up[0], forward[0]
    m10, m11, m12 = right[1], up[1], forward[1]
    m20, m21, m22 = right[2], up[2], forward[2]
    trace = m00 + m11 + m22
    if trace > 0:
        scale = math.sqrt(trace + 1.0) * 2
        q = ((m21 - m12) / scale, (m02 - m20) / scale, (m10 - m01) / scale, 0.25 * scale)
    elif m00 > m11 and m00 > m22:
        scale = math.sqrt(1.0 + m00 - m11 - m22) * 2
        q = (0.25 * scale, (m01 + m10) / scale, (m02 + m20) / scale, (m21 - m12) / scale)
    elif m11 > m22:
        scale = math.sqrt(1.0 + m11 - m00 - m22) * 2
        q = ((m01 + m10) / scale, 0.25 * scale, (m12 + m21) / scale, (m02 - m20) / scale)
    else:
        scale = math.sqrt(1.0 + m22 - m00 - m11) * 2
        q = ((m02 + m20) / scale, (m12 + m21) / scale, 0.25 * scale, (m10 - m01) / scale)
    q_length = math.sqrt(sum(value * value for value in q))
    return (q[0] / q_length, q[1] / q_length, q[2] / q_length, q[3] / q_length)


def _rotate_vector(rotation: Sequence[float], vector: Sequence[float]) -> tuple[float, float, float]:
    x, y, z, w = (float(value) for value in rotation)
    vx, vy, vz = (float(value) for value in vector)
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + y * tz - z * ty, vy + w * ty + z * tx - x * tz, vz + w * tz + x * ty - y * tx)


def _wall_slot(key: str, position: Sequence[float], size: Sequence[float]) -> dict[str, Any]:
    return _box_slot(key, f"Blockout wall segment · {key}", position, size, "mat_wall", collider=True)


def _front_wall_parts(building: dict[str, Any], wall_base: float, wall_top: float) -> list[dict[str, Any]]:
    width, depth = building["size"]
    front, thickness, door_width, door_height = building["front"], 0.28, 1.2, 2.1
    wall_height, lintel_height = wall_top - wall_base, wall_top - wall_base - door_height
    result: list[dict[str, Any]] = []
    frame = f"{building['key']}_front"
    if front in ("north", "south"):
        face_z = (depth / 2 - thickness / 2) * (1 if front == "north" else -1)
        jamb_width = (width - door_width) / 2
        for index, side in enumerate((-1, 1)):
            result.append(_wall_slot(f"{frame}_side_{index}", [side * (door_width / 2 + jamb_width / 2), wall_base + wall_height / 2, face_z], [jamb_width, wall_height, thickness]))
        result.append(_wall_slot(f"{frame}_lintel", [0, wall_base + door_height + lintel_height / 2, face_z], [width, lintel_height, thickness]))
    else:
        face_x = (width / 2 - thickness / 2) * (1 if front == "east" else -1)
        jamb_depth = (depth - door_width) / 2
        for index, side in enumerate((-1, 1)):
            result.append(_wall_slot(f"{frame}_side_{index}", [face_x, wall_base + wall_height / 2, side * (door_width / 2 + jamb_depth / 2)], [thickness, wall_height, jamb_depth]))
        result.append(_wall_slot(f"{frame}_lintel", [face_x, wall_base + door_height + lintel_height / 2, 0], [thickness, lintel_height, depth]))
    return result


def _basement_floor_panels(key: str, width: float, depth: float, access: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Emit native floor panels around the same opening used by the actual descent."""
    floor_y, thickness = 0.20, 0.24
    if access is None:
        return [_box_slot(f"{key}_floor", "Blockout interior floor slab", [0, floor_y, 0], [width, thickness, depth], "mat_floor", collider=True)]
    opening = access["floor_opening"]
    panel_prefix = access.get("floor_key_prefix", key)
    center_x, center_z = (float(value) for value in opening["center"])
    size_x, size_z = (float(value) for value in opening["size"])
    xmin, xmax, zmin, zmax = -width / 2, width / 2, -depth / 2, depth / 2
    hole_x0, hole_x1 = max(xmin, center_x - size_x / 2), min(xmax, center_x + size_x / 2)
    hole_z0, hole_z1 = max(zmin, center_z - size_z / 2), min(zmax, center_z + size_z / 2)
    if hole_x1 <= hole_x0 or hole_z1 <= hole_z0:
        raise ValueError(f"basement opening for {key} does not cross its actual floor slab")
    rectangles = (
        ("west", xmin, hole_x0, zmin, zmax),
        ("east", hole_x1, xmax, zmin, zmax),
        ("rear", hole_x0, hole_x1, zmin, hole_z0),
        ("front", hole_x0, hole_x1, hole_z1, zmax),
    )
    result = []
    for side, x0, x1, z0, z1 in rectangles:
        if x1 - x0 <= 0.03 or z1 - z0 <= 0.03:
            continue
        result.append(_box_slot(
            f"{panel_prefix}_floor_well_{side}", "Floor panel beside basement cutout",
            [(x0 + x1) / 2, floor_y, (z0 + z1) / 2], [x1 - x0, thickness, z1 - z0],
            "mat_floor", collider=True,
        ))
    return result


def _building_shell(building: dict[str, Any], basement_access: dict[str, Any] | None = None) -> dict[str, Any]:
    key, (width, depth), height = building["key"], building["size"], building["height"]
    thickness, wall_base, wall_top = 0.28, 0.32, height - 0.12
    wall_height = wall_top - wall_base
    children = _basement_floor_panels(key, width, depth, basement_access)
    if building["front"] == "north":
        rear = _wall_slot(f"{key}_rear_wall", [0, wall_base + wall_height / 2, -depth / 2 + thickness / 2], [width, wall_height, thickness])
    elif building["front"] == "south":
        rear = _wall_slot(f"{key}_rear_wall", [0, wall_base + wall_height / 2, depth / 2 - thickness / 2], [width, wall_height, thickness])
    elif building["front"] == "east":
        rear = _wall_slot(f"{key}_rear_wall", [-width / 2 + thickness / 2, wall_base + wall_height / 2, 0], [thickness, wall_height, depth])
    else:
        rear = _wall_slot(f"{key}_rear_wall", [width / 2 - thickness / 2, wall_base + wall_height / 2, 0], [thickness, wall_height, depth])
    children.append(rear)
    if building["front"] in ("north", "south"):
        children.extend([
            _wall_slot(f"{key}_west_wall", [-width / 2 + thickness / 2, wall_base + wall_height / 2, 0], [thickness, wall_height, depth]),
            _wall_slot(f"{key}_east_wall", [width / 2 - thickness / 2, wall_base + wall_height / 2, 0], [thickness, wall_height, depth]),
        ])
    else:
        children.extend([
            _wall_slot(f"{key}_south_wall", [0, wall_base + wall_height / 2, -depth / 2 + thickness / 2], [width, wall_height, thickness]),
            _wall_slot(f"{key}_north_wall", [0, wall_base + wall_height / 2, depth / 2 - thickness / 2], [width, wall_height, thickness]),
        ])
    children.extend(_front_wall_parts(building, wall_base, wall_top))
    children.append(_box_slot(f"{key}_roof", "Flat blockout roof slab", [0, height, 0], [width + 0.3, 0.22, depth + 0.3], "mat_roof", collider=True))
    return {"slot": {"key": f"building_{key}", "name": f"BLOCKOUT · {building['kind']} · {key}", "position": list(building["center"])}, "children": children}


def _ramp_slot(key: str, name: str, start: Sequence[float], end: Sequence[float], width: float) -> dict[str, Any]:
    """Create a collidable ramp whose top contact line exactly meets its endpoints."""
    direction = [float(end[i]) - float(start[i]) for i in range(3)]
    length = math.sqrt(sum(value * value for value in direction))
    rotation = _gravity_up_ramp_rotation(direction)
    ramp_up = _rotate_vector(rotation, (0.0, 1.0, 0.0))
    thickness = 0.16
    center = [(float(start[i]) + float(end[i])) / 2 - ramp_up[i] * thickness / 2 for i in range(3)]
    return _box_slot(key, name, center, [width, thickness, length], "mat_concrete", rotation=rotation, collider=True)



def _stair_treads(access: dict[str, Any], building: dict[str, Any]) -> list[dict[str, Any]]:
    count = int(access["steps"])
    run = float(access["approach_run"])
    rise_total = float(access["depth_below_grade"])
    tread = run / count
    rise = rise_total / count
    clear_width = float(access["clear_width"])
    building_width, building_depth = building["size"]
    center_x, _center_y, center_z = building["center"]
    side = access["entry_side"]
    if side == "east":
        outward, span, axis = (1.0, 0.0), building_width, "x"
    elif side == "west":
        outward, span, axis = (-1.0, 0.0), building_width, "x"
    elif side == "north":
        outward, span, axis = (0.0, 1.0), building_depth, "z"
    elif side == "south":
        outward, span, axis = (0.0, -1.0), building_depth, "z"
    else:
        raise ValueError(f"unsupported stair entry side: {side}")
    if run > span / 2 + 1e-8:
        raise ValueError(f"stair run {run}m does not fit {building['key']} entry span")
    prefix = access["key"].removesuffix("_stairs")
    result = []
    for index in range(count):
        distance = span / 2 - (index + 0.5) * tread
        top_y = -(index + 1) * rise
        if axis == "x":
            position = [center_x + outward[0] * distance, top_y - rise / 2, center_z]
            size = [tread, rise, clear_width]
        else:
            position = [center_x, top_y - rise / 2, center_z + outward[1] * distance]
            size = [clear_width, rise, tread]
        result.append(_box_slot(f"{prefix}_stair_{index:02d}", "Basement stair tread · visual detail", position, size, "mat_concrete", collider=False))
    return result


def _basement_access_slots(layout: dict[str, Any]) -> list[dict[str, Any]]:
    buildings = {building["key"]: building for building in layout["buildings"]}
    result: list[dict[str, Any]] = []
    for access in layout["basement_access"]:
        building = buildings[access["building_key"]]
        width, depth = building["size"]
        center_x, _center_y, center_z = building["center"]
        side = access["entry_side"]
        if side == "north":
            start_xz, inward = (center_x, center_z + depth / 2), (0.0, -1.0)
        elif side == "south":
            start_xz, inward = (center_x, center_z - depth / 2), (0.0, 1.0)
        elif side == "east":
            start_xz, inward = (center_x + width / 2, center_z), (-1.0, 0.0)
        elif side == "west":
            start_xz, inward = (center_x - width / 2, center_z), (1.0, 0.0)
        else:
            raise ValueError(f"unsupported basement entry side: {side}")
        run = float(access["approach_run"])
        depth_below_grade = float(access["depth_below_grade"])
        landing_offset_x, landing_offset_z = access["landing_center_offset"]
        landing_x = center_x + float(landing_offset_x)
        landing_z = center_z + float(landing_offset_z)
        landing_size_x, landing_size_z = access["landing_size"]
        landing = _box_slot(
            access["landing_key"],
            "Basement landing at declared depth · blockout",
            [landing_x, -depth_below_grade - 0.06, landing_z],
            [float(landing_size_x), 0.12, float(landing_size_z)],
            "mat_floor",
            collider=True,
        )
        result.append(landing)
        if access["kind"] == "open_ramp_and_landing":
            start = [start_xz[0], 0.0, start_xz[1]]
            end = [start_xz[0] + inward[0] * run, -depth_below_grade, start_xz[1] + inward[1] * run]
            result.append(_ramp_slot(access["key"], "Theatre basement ramp through declared floor opening", start, end, float(access["clear_width"])))
        elif access["kind"] == "open_stairwell_and_landing":
            result.extend(_stair_treads(access, building))
            start = [start_xz[0], 0.0, start_xz[1]]
            end = [start_xz[0] + inward[0] * run, -depth_below_grade, start_xz[1] + inward[1] * run]
            surface = _ramp_slot(f"{access['key']}_walk_surface", "Continuous basement stair collision", start, end, float(access["clear_width"]))
            # Keep the authored stair silhouette, with no step edges in the walking
            # collision and no rendered ramp covering the visible treads.
            surface["components"] = [c for c in surface["components"] if c["type"] == "FrooxEngine.BoxCollider"]
            result.append(surface)
        else:
            raise ValueError(f"unsupported basement access kind: {access['kind']}")
    return result

def _roof_access_slots(layout: dict[str, Any], roof_record: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a guarded switchback whose final ramp terminates on the emitted roof slab."""
    roof_access = layout["roof_access"]
    if roof_record is None:
        from modeling.tokyo_nova.districts import build_districts
        _assemblies, records = build_districts(layout)
        roof_record = records[roof_access["building_key"]]
    entry = roof_record["roof_entry_point"]
    flights = roof_access["flights"]
    resolved = []
    for index, flight in enumerate(flights):
        start = [float(value) for value in flight["start"]]
        if "end" in flight:
            end = [float(value) for value in flight["end"]]
        else:
            end = [float(entry[0]), float(entry[1]), float(entry[2])]
        horizontal_run = math.hypot(end[0] - start[0], end[2] - start[2])
        if horizontal_run < 1e-4 or abs(end[1] - start[1]) / horizontal_run > 0.20:
            raise ValueError(f"roof ramp {flight['key']} exceeds its safe 1:5 rise/run")
        resolved.append((flight["key"], start, end))

    landing_size = [float(value) for value in roof_access["landing_size"]]
    handrail_height = float(roof_access["handrail_height"])
    clear_width = float(roof_access["clear_width"])
    children: list[dict[str, Any]] = []
    for index, landing in enumerate(roof_access["turn_landings"]):
        x, y, z = (float(value) for value in landing["center"])
        key = landing["key"]
        children.append(_box_slot(key, "Level switchback turning platform with static collision", [x, y - 0.06, z], [landing_size[0], 0.12, landing_size[1]], "mat_roof", collider=True))
        rail_y = y + handrail_height
        hx, hz = landing_size[0] / 2, landing_size[1] / 2
        contacts = ((resolved[index], True), (resolved[index + 1], False))
        # Cut only the incident flight footprints out of each perimeter rail. For
        # oblique flights the opening is the projected width at this edge plane.
        for axis, label, half_span in ((0, "x", hx), (2, "z", hz)):
            normal_axis = 2 if axis == 0 else 0
            for side in (-1, 1):
                edge = [x, rail_y, z]
                edge[normal_axis] += side * (hz if axis == 0 else hx)
                intervals = [(edge[axis] - half_span, edge[axis] + half_span)]
                for (_, start, end), at_end in contacts:
                    contact = end if at_end else start
                    if abs(contact[normal_axis] - edge[normal_axis]) > 1e-5:
                        continue
                    run = math.hypot(end[0] - start[0], end[2] - start[2])
                    normal_run = abs(end[normal_axis] - start[normal_axis])
                    if normal_run < 1e-6:
                        raise ValueError(f"roof flight is tangent to landing {key}")
                    half_opening = clear_width / 2 * run / normal_run + 0.04
                    gap_low, gap_high = contact[axis] - half_opening, contact[axis] + half_opening
                    intervals = [piece for low, high in intervals for piece in
                                 ((low, min(high, gap_low)), (max(low, gap_high), high))
                                 if piece[1] - piece[0] > 1e-5]
                for segment, (low, high) in enumerate(intervals):
                    center = list(edge)
                    center[axis] = (low + high) / 2
                    size = [0.06, 0.06, 0.06]
                    size[axis] = high - low
                    suffix = "" if segment == 0 else f"_segment_{segment}"
                    children.append(_box_slot(f"{key}_guardrail_{label}_{side}{suffix}", "Landing perimeter guardrail with flight opening", center, size, "mat_roof", collider=True))
        for side in (-1, 1):
            for corner in (-1, 1):
                children.append(_box_slot(f"{key}_guardrail_post_{side}_{corner}", "Landing guardrail post", [x + side * (hx - 0.04), y + handrail_height / 2, z + corner * (hz - 0.04)], [0.07, handrail_height, 0.07], "mat_roof", collider=True))

    for key, start, end in resolved:
        children.append(_ramp_slot(key, "Guarded walkable roof switchback flight", start, end, clear_width))
        direction = [end[axis] - start[axis] for axis in range(3)]
        length = math.sqrt(sum(value * value for value in direction))
        rotation = _gravity_up_ramp_rotation(direction)
        right = _rotate_vector(rotation, (1.0, 0.0, 0.0))
        up = _rotate_vector(rotation, (0.0, 1.0, 0.0))
        middle = [(start[axis] + end[axis]) / 2 for axis in range(3)]
        post_count = max(1, math.ceil(length / 2.0))
        for side in (-1, 1):
            offset = side * (clear_width / 2 + 0.08)
            rail_center = [middle[axis] + right[axis] * offset + up[axis] * handrail_height for axis in range(3)]
            children.append(_box_slot(f"{key}_handrail_{side}", "Continuous roof-flight handrail", rail_center, [0.055, 0.055, length], "mat_roof", rotation=rotation, collider=True))
            for post in range(post_count + 1):
                t = post / post_count
                base = [start[axis] + (end[axis] - start[axis]) * t for axis in range(3)]
                center = [base[axis] + right[axis] * offset + up[axis] * (handrail_height / 2) for axis in range(3)]
                children.append(_box_slot(f"{key}_handrail_post_{side}_{post}", "Roof-flight handrail support", center, [0.055, handrail_height, 0.055], "mat_roof", rotation=rotation, collider=True))
    return {"slot": {"key": "roof_access_geometry", "name": "Geometry-derived guarded roof switchback"}, "children": children}


def build_blockout_manifest(layout: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic native-geometry blockout manifest from layout data."""
    errors = validate_layout(layout)
    if errors:
        raise ValueError("invalid layout: " + "; ".join(errors))
    components = [
        _component("mat_ground", "FrooxEngine.PBS_Metallic", {"AlbedoColor": [0.105, 0.12, 0.14, 1], "Metallic": 0.05, "Smoothness": 0.18}),
        _component("mat_plaza", "FrooxEngine.PBS_Metallic", {"AlbedoColor": [0.24, 0.25, 0.25, 1], "Metallic": 0.03, "Smoothness": 0.22}),
        _component("mat_asphalt", "FrooxEngine.PBS_Metallic", {"AlbedoColor": [0.075, 0.09, 0.11, 1], "Metallic": 0.04, "Smoothness": 0.26}),
        _component("mat_wall", "FrooxEngine.PBS_Metallic", {"AlbedoColor": [0.31, 0.29, 0.25, 1], "Metallic": 0, "Smoothness": 0.16}),
        _component("mat_roof", "FrooxEngine.PBS_Metallic", {"AlbedoColor": [0.16, 0.17, 0.17, 1], "Metallic": 0.08, "Smoothness": 0.3}),
        _component("mat_floor", "FrooxEngine.PBS_Metallic", {"AlbedoColor": [0.25, 0.24, 0.21, 1], "Metallic": 0.02, "Smoothness": 0.24}),
        _component("mat_concrete", "FrooxEngine.PBS_Metallic", {"AlbedoColor": [0.35, 0.33, 0.28, 1], "Metallic": 0.03, "Smoothness": 0.18}),
    ]
    # These partitioned slabs are the only grade-level collision topology. Plaza and
    # road boxes remain render-only accents above them and do not cross basement holes.
    children = _ground_tile_slots(layout)
    children.append(_box_slot("plaza_floor", "Continuous clear plaza floor · 20m × 20m", [0, 0.01, 0], [20, 0.06, 20], "mat_plaza"))
    for route in layout["routes"]:
        for index, (start, end) in enumerate(zip(route["points"], route["points"][1:])):
            length = math.hypot(float(end[0] - start[0]), float(end[2] - start[2]))
            if length == 0:
                continue
            position = [(float(start[0]) + float(end[0])) / 2, 0.055, (float(start[2]) + float(end[2])) / 2]
            children.append(_box_slot(f"route_{route['key']}_{index:02d}", f"Blockout route surface · {route['key']}", position, [float(route["width"]), 0.01, length], "mat_asphalt", rotation=_segment_rotation(start, end)))
    access_by_building = {access["building_key"]: access for access in layout["basement_access"]}
    children.extend(_building_shell(building, access_by_building.get(building["key"])) for building in layout["buildings"])
    children.append(_roof_access_slots(layout))
    children.extend(_basement_access_slots(layout))
    return {
        "schemaVersion": "1", "ownership": {"key": ROOT_KEY}, "limits": {"expandedNodes": 12000},
        "slot": {"key": "root", "name": layout["root"]["name"], "parent": "Root", "position": list(layout["root"]["transform"]["position"]), "rotation": list(layout["root"]["transform"]["rotation"]), "scale": list(layout["root"]["transform"]["scale"])},
        "components": components, "children": children,
        "cameras": {camera["key"]: {"position": list(camera["position"]), "target": list(camera["target"]), "fieldOfView": 60, "width": 1280, "height": 720, "representative": camera["key"] in ("plaza_north_eye", "roof_overlook")} for camera in layout["cameras"]},
        "tests": [{"name": "tokyo-nova-owned-root-exists", "assertions": [{"target": "$slot:root", "exists": True}]}],
    }




def _city_facility_signage(layout: dict[str, Any]) -> dict[str, Any]:
    """Add restrained Japanese service labels for new facilities, outside their front walls."""
    by_key = {building["key"]: building for building in layout["buildings"]}
    signs = []
    preserved_north_signs = {"eatery", "terminal_repair"}
    for facility in layout["facilities"]:
        if facility["key"] in preserved_north_signs:
            continue
        building = by_key[facility["building_key"]]
        x, _y, z = (float(value) for value in building["center"])
        width, depth = (float(value) for value in building["size"])
        front = building["front"]
        sign_x, sign_z = x, z
        if front == "north":
            sign_z += depth / 2 + .04
            yaw = 0.0
        elif front == "south":
            sign_z -= depth / 2 + .04
            yaw = math.pi
        elif front == "east":
            sign_x += width / 2 + .04
            yaw = math.pi / 2
        else:
            sign_x -= width / 2 + .04
            yaw = -math.pi / 2
        key = f"city_sign_{facility['key']}"
        signs.append({
            "slot": {"key": key, "name": facility["name"], "position": [sign_x, 2.48, sign_z], "rotation": [0.0, math.sin(yaw / 2), 0.0, math.cos(yaw / 2)], "scale": [1.0, 1.0, 1.0]},
            "components": [{"key": f"{key}_text", "type": "FrooxEngine.TextRenderer", "fields": {"Text": facility["name"], "Size": 0.12, "Color": [0.93, 0.76, 0.48, 1.0], "ParseRichText": False}}],
        })
    return {"slot": {"key": "city_facility_signage", "name": "市街地の施設案内"}, "children": signs}

def _disable_city_blockout_shells(manifest: dict[str, Any]) -> None:
    """Replace non-north generic shells; retain only the already-tuned north floors."""
    from modeling.tokyo_nova.sector_pipeline import (
        _disable_reviewed_placeholder_renderers,
    )

    children = manifest.get("children", [])
    north_keys = {"north_yatai", "north_terminal_repair", "north_machiya"}
    for building in (child for child in children if child.get("slot", {}).get("key", "").startswith("building_")):
        key = building["slot"]["key"].removeprefix("building_")
        if key in north_keys:
            continue
        for slot in iter_slots(building):
            for component in slot.get("components", []):
                if component.get("type") in {"FrooxEngine.MeshRenderer", "FrooxEngine.BoxCollider"}:
                    component.setdefault("fields", {})["Enabled"] = False
    _disable_reviewed_placeholder_renderers(children)


def _city_collision_group(city: dict[str, Any]) -> dict[str, Any]:
    from modeling.tokyo_nova.districts import collision_parts

    owners = {assembly.name for assembly in city["assemblies"] if assembly.kind in {"district_building", "interior_room"}}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for building_key, part_name, minimum, maximum in collision_parts(city["assemblies"]):
        if building_key not in owners:
            raise ValueError(f"collider owner has no emitted building or room geometry: {building_key}")
        size = [maximum[axis] - minimum[axis] for axis in range(3)]
        center = [(minimum[axis] + maximum[axis]) / 2 for axis in range(3)]
        key = f"city_collision_{building_key}_{part_name}"
        grouped.setdefault(building_key, []).append({"key": f"{key}_box", "type": "FrooxEngine.BoxCollider", "fields": {
            "Enabled": True, "Type": "Static", "CharacterCollider": True, "Offset": center, "Size": size,
        }})
    result = [
        {"slot": {"key": f"city_collision_building_{building_key}", "name": f"City wall/floor collision set · {building_key}", "position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0], "scale": [1.0, 1.0, 1.0]}, "components": components}
        for building_key, components in sorted(grouped.items())
    ]
    return {"slot": {"key": "city_collision_geometry", "name": "Tokyo Nova colliders derived from visible walls, floors and rails"}, "children": result}


def build_city_manifest(layout: dict[str, Any], city: dict[str, Any], *, exported: dict[str, Any] | None = None, export_path: Path | None = None, output_path: Path | None = None, base_manifest: dict[str, Any] | None = None, base_source_dir: Path | None = None) -> dict[str, Any]:
    """Compose full city geometry, native collisions/lights and current north assets under its owned root."""
    from modeling.tokyo_nova.north import (
        collision_manifest_entries,
        sign_manifest_entries,
    )

    if base_manifest is not None:
        manifest = copy.deepcopy(base_manifest)
    else:
        north_manifest_path = Path("content/tokyo-nova/north/north-apply.json")
        manifest = json.loads(north_manifest_path.read_text(encoding="utf-8")) if north_manifest_path.exists() else build_blockout_manifest(enrich_layout(layout))
    if manifest.get("slot", {}).get("key") != "root" or manifest.get("ownership", {}).get("key") != ROOT_KEY:
        raise ValueError("city base manifest must retain the Tokyo Nova owned root")
    if base_source_dir is None:
        base_source_dir = Path("content/tokyo-nova/north")
    if output_path is not None:
        for asset in manifest.get("assets", {}).values():
            source = str(asset.get("source", ""))
            if not source or "://" in source:
                continue
            source_path = Path(source)
            if not source_path.is_absolute():
                source_path = (base_source_dir / source_path).resolve()
            asset["source"] = Path(os.path.relpath(source_path, output_path.parent.resolve())).as_posix()
    _disable_city_blockout_shells(manifest)
    children = manifest.setdefault("children", [])
    managed_groups = {"city_detail", "city_collision_geometry", "roof_access_geometry"}
    basement_slots = _basement_access_slots(layout)
    basement_keys = {node["slot"]["key"] for node in basement_slots}
    previous_roof_slots = {"roof_access_ramp", "roof_access_ramp_lower", "roof_access_ramp_middle", "roof_switchback_landing_1", "roof_switchback_landing_2"}
    # These stable tiles are this owned root's only grade-level collision surface. Rebuild
    # their partition from declared access wells while leaving north content and world Ground untouched.
    children[:] = [
        child for child in children
        if child.get("slot", {}).get("key") not in managed_groups | previous_roof_slots | basement_keys
        and not child.get("slot", {}).get("key", "").startswith("outer_ground_tile_")
    ]
    children.extend(_ground_tile_slots(layout))
    # The North checkpoint contains old native basement geometry. Refresh only
    # these exact managed keys, rather than leaving a stale descent in the city.
    children.extend(basement_slots)
    if not any(child.get("slot", {}).get("key") == "north_collision_geometry" for child in children):
        children.append(collision_manifest_entries(layout))
    if not any(child.get("slot", {}).get("key") == "north_physical_japanese_signage" for child in children):
        sign_groups = sign_manifest_entries(layout)
        children.append(sign_groups["physical"])
        children.append(sign_groups["ar"])
    children.append(_city_collision_group(city))
    roof_key = layout["roof_access"]["building_key"]
    children.append(_roof_access_slots(layout, city["building_geometry"][roof_key]))

    for light in city["lighting"]["lights"]:
        children.append({
            "slot": {"key": light["key"], "name": light["name"], "position": light["position"], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]},
            "components": [{"key": f"{light['key']}_component", "type": "FrooxEngine.Light", "fields": light["fields"]}],
        })

    assets = manifest.setdefault("assets", {})
    root_components = manifest.setdefault("components", [])
    if exported is not None:
        if exported.get("slot", {}).get("key") != "root":
            raise ValueError("Blender city export is missing the stable root key")
        if export_path is None or output_path is None:
            raise ValueError("export_path and output_path are required when merging a Blender export")
        component_keys = {component.get("key") for component in root_components}
        for component in exported.get("components", []):
            if component.get("key") in component_keys:
                existing = next(item for item in root_components if item.get("key") == component.get("key"))
                if existing != component:
                    raise ValueError(f"Blender city component collides with differing base component {component.get('key')}")
                continue
            root_components.append(component)
            component_keys.add(component.get("key"))
        for key, asset in exported.get("assets", {}).items():
            if key in assets and assets[key] != asset:
                raise ValueError(f"Blender city asset key collides with base asset {key}")
            assets[key] = {**asset, "source": _source_for_output(asset, export_path.parent, output_path.parent)}
        # Reuse the already-managed North material providers; export only City geometry slots here.
        extension_children = [child for child in exported.get("children", []) if child.get("slot", {}).get("key") != "blender_providers"]
        extension_children.append(_city_facility_signage(layout))
        children.append({"slot": {"key": "city_detail", "name": "Tokyo Nova full detailed city meshes, interiors and owned sky"}, "children": copy.deepcopy(extension_children)})

    # The composed structural candidate measures ~63k JSON values (not Slots).
    # Keep modest headroom; full mesh export is validated separately in Task3E.
    manifest.setdefault("limits", {})["expandedNodes"] = max(int(manifest["limits"].get("expandedNodes", 0)), 70000)
    manifest["tests"] = [{"name": "tokyo-nova-owned-root-and-open-plaza", "assertions": [{"target": "$slot:root", "exists": True}]}]
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def integrate_city_manifest(base_path: Path, export_path: Path, output_path: Path, layout_path: Path = Path("content/tokyo-nova/layout.json")) -> dict[str, Any]:
    """Merge exported city meshes into a fresh stable blockout root and retain measured source state."""
    from modeling.tokyo_nova.build import build_city

    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    city = build_city(layout)
    base = json.loads(base_path.read_text(encoding="utf-8"))
    exported = json.loads(export_path.read_text(encoding="utf-8"))
    if base.get("ownership", {}).get("key") != ROOT_KEY:
        raise ValueError("city source manifest is outside the Tokyo Nova ownership root")
    return build_city_manifest(layout, city, exported=exported, export_path=export_path.resolve(), output_path=output_path.resolve(), base_manifest=base, base_source_dir=base_path.resolve().parent)

def build_pipeline_config() -> dict[str, Any]:
    """Return reproducible source configuration, without session observations."""
    types = ("StaticMesh", "MeshRenderer", "PBS_Metallic", "BoxCollider", "Light", "UnlitMaterial", "StaticTexture2D", "StaticFont", "TextUnlitMaterial", "TextRenderer", "Skybox", "ProceduralSkyMaterial", "BoxMesh", "InteractiveCamera")
    return {
        "schema_version": 1,
        "destination": {"session": "usaturn World", "url": RESOLOOP_URL, "resonite_version": "2026.9.18.82", "resonite_link_version": "0.13.1.0"},
        "blender": {"executable": "/usr/bin/blender", "version": "5.0.1"},
        "commands": {
            "doctor": "resoloop doctor --url ws://localhost:54238/ --json",
            "reflection": "resoloop type describe '<FrooxEngine type>' --json --url ws://localhost:54238/",
            "blender_probe": "resoloop blender run modeling/tokyo_nova/probe.py --arg=.resoloop/tokyo-nova/probe.blend --json",
            "blender_export": "resoloop blender export .resoloop/tokyo-nova/probe.blend --output .resoloop/tokyo-nova/probe-export --name ResoLoop_Test_TokyoNovaProbe --parent Root --pack-pbr --json",
            "probe_prepare": "uv run python -m modeling.tokyo_nova.pipeline --prepare-probe .resoloop/tokyo-nova/probe-export/model.apply.json --probe-output .resoloop/tokyo-nova/probe-integration.json",
            "offline_validate": "resoloop validate content/tokyo-nova/blockout.json --json",
            "strict_validate": "resoloop validate content/tokyo-nova/blockout.json --strict --json",
            "plan_diff": f"resoloop diff content/tokyo-nova/blockout.json --changes-only --json --state {STATE_PATH} --url {RESOLOOP_URL}",
            "apply": f"resoloop apply content/tokyo-nova/blockout.json --json --state {STATE_PATH} --url {RESOLOOP_URL}",
            "reapply_noop": f"resoloop apply content/tokyo-nova/blockout.json --json --state {STATE_PATH} --url {RESOLOOP_URL}",
        },
        "reflected_types": {name: f"[FrooxEngine]FrooxEngine.{name}" for name in types},
        "metadata_directory": ".resoloop/tokyo-nova/metadata",
        "transfer_requirements": {
            "mesh": "ResoLoop client transports mesh bytes.",
            "textures": "StaticTexture2D import reads the source path on the Resonite host; use an authorized shared absolute path or run the client on that host.",
            "source_workspace": "/workspaces/reso-world/MyResoniteProject",
        },
        "capture_plan": {"formats": ["png", "jpg"], "output_directory": ".resoloop/tokyo-nova/captures", "svg_is_runtime_evidence": False},
        "ownership": {
            "root_key": ROOT_KEY,
            "root_name": "TokyoNova_WestSlum",
            "root_world_position": [0, 30, 120],
            "state_path": STATE_PATH,
            "probe_root_key": "tokyo-nova-probe",
            "probe_state_path": PROBE_STATE_PATH,
        },
        "notes": [
            "Owned root is raised to world Y=30; layout and plaza remain root-local Y=0, leaving existing Ground untouched.",
            "Layout coordinates use Resonite XYZ; Blender conversion swaps Y/Z exactly once at the generation boundary.",
            "Live command results, current-session IDs, transfer outcomes and screenshots are recorded separately in .resoloop/tokyo-nova/pipeline.json.",
            "Existing content/main.json and content/sunset.json are not changed.",
        ],
    }


def build_pipeline_record() -> dict[str, Any]:
    """Compatibility alias for the static pipeline source configuration."""
    return build_pipeline_config()


def write_outputs(output_dir: Path, pipeline_config_path: Path | None = None) -> None:
    """Regenerate source manifests and config without touching live evidence."""
    if pipeline_config_path is None:
        pipeline_config_path = output_dir / "pipeline-config.json"
    resolved_config = pipeline_config_path.resolve()
    if ".resoloop" in resolved_config.parts:
        raise ValueError("pipeline source config must not overwrite live evidence under .resoloop")
    layout = enrich_layout(build_layout())
    manifest = build_blockout_manifest(layout)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "blockout.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pipeline_config_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline_config_path.write_text(json.dumps(build_pipeline_config(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("content/tokyo-nova"))
    parser.add_argument("--pipeline-config", type=Path)
    parser.add_argument("--prepare-probe", type=Path)
    parser.add_argument("--integrate-city", type=Path)
    parser.add_argument("--city-apply-output", type=Path)
    parser.add_argument("--layout-path", type=Path, default=Path("content/tokyo-nova/layout.json"))
    parser.add_argument("--probe-output", type=Path)
    args = parser.parse_args()
    if args.integrate_city:
        if args.city_apply_output is None:
            parser.error("--city-apply-output is required with --integrate-city")
        integrate_city_manifest(Path("content/tokyo-nova/north/north-apply.json"), args.integrate_city, args.city_apply_output, args.layout_path)
    elif args.prepare_probe:
        if args.probe_output is None:
            parser.error("--probe-output is required with --prepare-probe")
        prepare_probe_manifest(args.prepare_probe, args.probe_output)
    else:
        write_outputs(args.output_dir, args.pipeline_config)


if __name__ == "__main__":
    main()
