"""Build stable ResoLoop manifests and record the Blender-to-Resonite pipeline."""
from __future__ import annotations

import argparse
import json
import math
import os
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from modeling.tokyo_nova.layout import build_layout, validate_layout

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
    """Build floor panels around the opening declared by this basement access."""
    floor_y, thickness = 0.20, 0.24
    if access is None:
        return [_box_slot(f"{key}_floor", "Blockout interior floor slab", [0, floor_y, 0], [width, thickness, depth], "mat_floor", collider=True)]
    opening = access["floor_opening"]
    panel_prefix = access.get("floor_key_prefix", key)
    center_x, center_z = opening["center"]
    first_size, second_size = opening["size"]
    if opening["axis"] == "z":
        opening_width, opening_depth = first_size, second_size
        side = (width - opening_width) / 2
        z_min = -depth / 2
        remaining = center_z - opening_depth / 2 - z_min
        panels = [
            _box_slot(f"{panel_prefix}_floor_well_left", "Floor panel beside basement cutout", [center_x - opening_width / 2 - side / 2, floor_y, 0], [side, thickness, depth], "mat_floor", collider=True),
            _box_slot(f"{panel_prefix}_floor_well_right", "Floor panel beside basement cutout", [center_x + opening_width / 2 + side / 2, floor_y, 0], [side, thickness, depth], "mat_floor", collider=True),
        ]
        if remaining > 1e-8:
            panels.append(_box_slot(f"{panel_prefix}_floor_well_back", "Floor panel beyond basement cutout", [center_x, floor_y, z_min + remaining / 2], [opening_width, thickness, remaining], "mat_floor", collider=True))
        return panels
    if opening["axis"] == "x":
        opening_depth, opening_width = first_size, second_size
        side = (depth - opening_width) / 2
        x_min = -width / 2
        remaining = center_x - opening_depth / 2 - x_min
        panels = [
            _box_slot(f"{panel_prefix}_floor_well_left", "Floor panel beside basement cutout", [0, floor_y, center_z - opening_width / 2 - side / 2], [width, thickness, side], "mat_floor", collider=True),
            _box_slot(f"{panel_prefix}_floor_well_right", "Floor panel beside basement cutout", [0, floor_y, center_z + opening_width / 2 + side / 2], [width, thickness, side], "mat_floor", collider=True),
        ]
        if remaining > 1e-8:
            panels.append(_box_slot(f"{panel_prefix}_floor_well_back", "Floor panel beyond basement cutout", [x_min + remaining / 2, floor_y, center_z], [remaining, thickness, opening_width], "mat_floor", collider=True))
        return panels
    raise ValueError(f"unsupported basement floor opening axis: {opening['axis']}")


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
        result.append(_box_slot(f"{prefix}_stair_{index:02d}", "Basement stair tread · blockout", position, size, "mat_concrete", collider=True))
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
        else:
            raise ValueError(f"unsupported basement access kind: {access['kind']}")
    return result

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
    children = [
        _box_slot("outer_ground", "Tokyo Nova blockout perimeter ground", [0, -0.04, 0], [100, 0.08, 100], "mat_ground"),
        _box_slot("plaza_floor", "Continuous clear plaza floor · 20m × 20m", [0, 0.01, 0], [20, 0.06, 20], "mat_plaza"),
    ]
    for route in layout["routes"]:
        for index, (start, end) in enumerate(zip(route["points"], route["points"][1:])):
            length = math.hypot(float(end[0] - start[0]), float(end[2] - start[2]))
            if length == 0:
                continue
            position = [(float(start[0]) + float(end[0])) / 2, 0.055, (float(start[2]) + float(end[2])) / 2]
            children.append(_box_slot(f"route_{route['key']}_{index:02d}", f"Blockout route surface · {route['key']}", position, [float(route["width"]), 0.01, length], "mat_asphalt", rotation=_segment_rotation(start, end)))
    access_by_building = {access["building_key"]: access for access in layout["basement_access"]}
    children.extend(_building_shell(building, access_by_building.get(building["key"])) for building in layout["buildings"])
    roof = next(building for building in layout["buildings"] if building["key"] == layout["roof_access"]["building_key"])
    roof_west_edge = float(roof["center"][0]) - (float(roof["size"][0]) + 0.3) / 2
    children.append(_ramp_slot(
        "roof_access_ramp",
        "Walkable roof-overlook approach · blockout ramp",
        [-37, 0.0, float(roof["center"][2])],
        [roof_west_edge, float(layout["roof_access"]["target_height"]), float(roof["center"][2])],
        float(layout["roof_access"]["clear_width"]),
    ))
    children.extend(_basement_access_slots(layout))
    return {
        "schemaVersion": "1", "ownership": {"key": ROOT_KEY}, "limits": {"expandedNodes": 12000},
        "slot": {"key": "root", "name": layout["root"]["name"], "parent": "Root", "position": list(layout["root"]["transform"]["position"]), "rotation": list(layout["root"]["transform"]["rotation"]), "scale": list(layout["root"]["transform"]["scale"])},
        "components": components, "children": children,
        "cameras": {camera["key"]: {"position": list(camera["position"]), "target": list(camera["target"]), "fieldOfView": 60, "width": 1280, "height": 720, "representative": camera["key"] in ("plaza_north_eye", "roof_overlook")} for camera in layout["cameras"]},
        "tests": [{"name": "tokyo-nova-owned-root-exists", "assertions": [{"target": "$slot:root", "exists": True}]}],
    }


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
    layout = build_layout()
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
    parser.add_argument("--probe-output", type=Path)
    args = parser.parse_args()
    if args.prepare_probe:
        if args.probe_output is None:
            parser.error("--probe-output is required with --prepare-probe")
        prepare_probe_manifest(args.prepare_probe, args.probe_output)
    else:
        write_outputs(args.output_dir, args.pipeline_config)


if __name__ == "__main__":
    main()
