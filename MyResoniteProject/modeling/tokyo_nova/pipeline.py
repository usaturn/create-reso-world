"""Build stable ResoLoop manifests and record the Blender-to-Resonite pipeline."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Sequence

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


def _long_axis_rotation(direction: Sequence[float]) -> tuple[float, float, float, float]:
    """Return a quaternion rotating local +Z onto a 3D direction."""
    dx, dy, dz = (float(value) for value in direction)
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length == 0:
        raise ValueError("a ramp direction cannot be zero length")
    dx, dy, dz = dx / length, dy / length, dz / length
    if dz < -0.999999:
        return (1, 0, 0, 0)
    qx, qy, qw = -dy, dx, 1 + dz
    q_length = math.sqrt(qx * qx + qy * qy + qw * qw)
    return (qx / q_length, qy / q_length, 0, qw / q_length)


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


def _basement_floor_panels(key: str, width: float, depth: float) -> list[dict[str, Any]]:
    """Split cellar floors around access wells without altering world Ground."""
    floor_y, thickness = 0.20, 0.24
    if key == "south_theatre":
        opening_width, opening_depth = 1.8, 3.0
        side = (width - opening_width) / 2
        return [
            _box_slot("theatre_floor_well_left", "Floor panel beside basement cutout", [-width / 2 + side / 2, floor_y, 0], [side, thickness, depth], "mat_floor", collider=True),
            _box_slot("theatre_floor_well_right", "Floor panel beside basement cutout", [width / 2 - side / 2, floor_y, 0], [side, thickness, depth], "mat_floor", collider=True),
            _box_slot("theatre_floor_well_back", "Floor panel beyond basement cutout", [0, floor_y, -depth / 2 + (depth - opening_depth) / 2], [opening_width, thickness, depth - opening_depth], "mat_floor", collider=True),
        ]
    if key == "west_basement_bar":
        opening_width, opening_depth = 1.8, 3.0
        side = (depth - opening_width) / 2
        return [
            _box_slot("bar_floor_well_left", "Floor panel beside basement cutout", [0, floor_y, -depth / 2 + side / 2], [width, thickness, side], "mat_floor", collider=True),
            _box_slot("bar_floor_well_right", "Floor panel beside basement cutout", [0, floor_y, depth / 2 - side / 2], [width, thickness, side], "mat_floor", collider=True),
            _box_slot("bar_floor_well_back", "Floor panel beyond basement cutout", [-width / 2 + (width - opening_depth) / 2, floor_y, 0], [width - opening_depth, thickness, opening_width], "mat_floor", collider=True),
        ]
    return [_box_slot(f"{key}_floor", "Blockout interior floor slab", [0, floor_y, 0], [width, thickness, depth], "mat_floor", collider=True)]


def _building_shell(building: dict[str, Any]) -> dict[str, Any]:
    key, (width, depth), height = building["key"], building["size"], building["height"]
    thickness, wall_base, wall_top = 0.28, 0.32, height - 0.12
    wall_height = wall_top - wall_base
    children = _basement_floor_panels(key, width, depth)
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
    direction = [float(end[i]) - float(start[i]) for i in range(3)]
    length = math.sqrt(sum(value * value for value in direction))
    center = [(float(start[i]) + float(end[i])) / 2 for i in range(3)]
    return _box_slot(key, name, center, [width, 0.16, length], "mat_concrete", rotation=_long_axis_rotation(direction), collider=True)


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
    children.extend(_building_shell(building) for building in layout["buildings"])
    roof = next(building for building in layout["buildings"] if building["key"] == "west_roof_access")
    children.append(_ramp_slot("roof_access_ramp", "Walkable roof-overlook approach · blockout ramp", [-37, 0.16, 35], [-18, roof["height"] + 0.11, 35], 1.8))
    theatre = next(building for building in layout["buildings"] if building["key"] == "south_theatre")
    children.extend([
        _ramp_slot("south_theatre_basement_ramp", "Theatre basement ramp through open floor cutout", [theatre["center"][0], 0.16, -10], [theatre["center"][0], 0.12, -15], 1.8),
        _box_slot("theatre_basement_landing", "Shallow basement landing above world ground · theatre", [theatre["center"][0], 0.10, -15], [2.4, 0.12, 2.4], "mat_floor", collider=True),
    ])
    bar = next(building for building in layout["buildings"] if building["key"] == "west_basement_bar")
    children.extend([
        _ramp_slot("west_bar_basement_ramp", "Bar basement ramp through open floor cutout", [-10, 0.16, bar["center"][2]], [-15, 0.12, bar["center"][2]], 1.6),
        _box_slot("bar_basement_landing", "Shallow basement landing above world ground · bar", [-15, 0.10, bar["center"][2]], [2.4, 0.12, 2.2], "mat_floor", collider=True),
    ])
    return {
        "schemaVersion": "1", "ownership": {"key": ROOT_KEY}, "limits": {"expandedNodes": 12000},
        "slot": {"key": "root", "name": layout["root"]["name"], "parent": "Root", "position": list(layout["root"]["transform"]["position"]), "rotation": list(layout["root"]["transform"]["rotation"]), "scale": list(layout["root"]["transform"]["scale"])},
        "components": components, "children": children,
        "cameras": {camera["key"]: {"position": list(camera["position"]), "target": list(camera["target"]), "fieldOfView": 60, "width": 1280, "height": 720, "representative": camera["key"] in ("plaza_north_eye", "roof_overlook")} for camera in layout["cameras"]},
        "tests": [{"name": "tokyo-nova-owned-root-exists", "assertions": [{"target": "$slot:root", "exists": True}]}],
    }


def build_pipeline_record() -> dict[str, Any]:
    """Return the reproducible-command and runtime-evidence record template."""
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
            "plan_diff": "resoloop diff content/tokyo-nova/blockout.json --changes-only --json --state .resoloop/tokyo-nova/state/blockout.json",
            "apply": "resoloop apply content/tokyo-nova/blockout.json --json --state .resoloop/tokyo-nova/state/blockout.json --url ws://localhost:54238/",
            "reapply_noop": "resoloop apply content/tokyo-nova/blockout.json --json --state .resoloop/tokyo-nova/state/blockout.json --url ws://localhost:54238/",
        },
        "reflected_types": {name: f"[FrooxEngine]FrooxEngine.{name}" for name in types},
        "metadata_directory": ".resoloop/tokyo-nova/metadata",
        "texture_transfer": {"mesh_transport": "Mesh bytes are sent by the Linux ResoLoop client process.", "texture_transport": "StaticTexture2D file import reads its path on the Windows Resonite host.", "linux_workspace_mount": "/dev/sdd workspace bind", "windows_shared_path": None, "status": "investigating"},
        "capture": {"format": "PNG/JPEG live capture; SVG is offline-only and not runtime evidence.", "screenshots_directory": ".resoloop/tokyo-nova/captures", "captures": []},
        "ownership": {"root_key": ROOT_KEY, "root_id": None, "root_name": "TokyoNova_WestSlum", "root_world_position": [0, 0, 120], "state_path": STATE_PATH, "probe_root_key": "tokyo-nova-probe", "probe_root_id": None, "probe_state_path": PROBE_STATE_PATH},
        "notes": ["Root Y=0 aligns the plaza and blockout roads with the observed Ground Y=0. Y=30 would suspend the plaza above world ground.", "Layout coordinates are root-local Resonite XYZ; Blender conversion swaps Y/Z exactly once at the generation boundary.", "Existing content/main.json and content/sunset.json are prior-work inputs and are not changed."],
    }


def write_outputs(output_dir: Path, pipeline_path: Path | None = None) -> None:
    layout = build_layout()
    manifest = build_blockout_manifest(layout)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "blockout.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if pipeline_path is not None:
        pipeline_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline_path.write_text(json.dumps(build_pipeline_record(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("content/tokyo-nova"))
    parser.add_argument("--pipeline-record", type=Path, default=Path(".resoloop/tokyo-nova/pipeline.json"))
    parser.add_argument("--prepare-probe", type=Path)
    parser.add_argument("--probe-output", type=Path)
    args = parser.parse_args()
    if args.prepare_probe:
        if args.probe_output is None:
            parser.error("--probe-output is required with --prepare-probe")
        prepare_probe_manifest(args.prepare_probe, args.probe_output)
    else:
        write_outputs(args.output_dir, args.pipeline_record)


if __name__ == "__main__":
    main()
