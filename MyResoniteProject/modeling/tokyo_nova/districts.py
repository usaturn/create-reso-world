"""Authored, irregular building shells for the non-north Tokyo Nova blocks."""
from __future__ import annotations

from typing import Any

from modeling.tokyo_nova import geometry as geo
from modeling.tokyo_nova.layout import _route_reaches_front_door
from modeling.tokyo_nova.props import Assembly

Vec3 = tuple[float, float, float]
_NORTH_KEYS = {"north_yatai", "north_terminal_repair", "north_machiya"}
_MATERIALS = ("concrete", "patched_concrete", "painted_metal", "faded_teal", "exposed_metal", "rust", "wood")


def _box(parts: list[geo.MeshData], name: str, center: Vec3, size: Vec3, material: str, bevel: float = 0.0) -> None:
    parts.append(geo.beveled_box(name, center, size, bevel, material) if bevel else geo.box(name, center, size, material))


def _pipe(parts: list[geo.MeshData], name: str, start: Vec3, end: Vec3, radius: float, material: str) -> None:
    parts.append(geo.pipe(name, start, end, radius, material, segments=8))


def _front_wall(parts: list[geo.MeshData], key: str, width: float, depth: float, y0: float, floor_height: float, front: str, level: int, palette: tuple[str, ...]) -> float:
    """Emit a wall with a real door void at grade and fitted window voids above."""
    wall_t = 0.18
    wall_material = palette[level % len(palette)]
    door_width, door_height = 1.25, 2.12
    if front in ("north", "south"):
        z = (depth / 2 - wall_t / 2) * (1 if front == "north" else -1)
        if level == 0:
            side_w = (width - door_width) / 2
            _box(parts, f"{key}_front_wall_left", (-door_width / 2 - side_w / 2, y0 + floor_height / 2, z), (side_w, floor_height, wall_t), wall_material)
            _box(parts, f"{key}_front_wall_right", (door_width / 2 + side_w / 2, y0 + floor_height / 2, z), (side_w, floor_height, wall_t), wall_material)
            _box(parts, f"{key}_front_door_lintel", (0, y0 + door_height + (floor_height - door_height) / 2, z), (width, floor_height - door_height, wall_t), "exposed_metal")
        else:
            window_w, window_h = min(1.55, width * 0.34), 1.05
            window_y = y0 + floor_height * 0.54
            side_w = (width - window_w) / 2
            _box(parts, f"{key}_front_wall_left_{level}", (-window_w / 2 - side_w / 2, y0 + floor_height / 2, z), (side_w, floor_height, wall_t), wall_material)
            _box(parts, f"{key}_front_wall_right_{level}", (window_w / 2 + side_w / 2, y0 + floor_height / 2, z), (side_w, floor_height, wall_t), wall_material)
            _box(parts, f"{key}_front_spandrel_{level}", (0, y0 + (window_y - window_h / 2 - y0) / 2, z), (window_w, window_y - window_h / 2 - y0, wall_t), "patched_concrete")
            _box(parts, f"{key}_front_header_{level}", (0, window_y + window_h / 2 + (y0 + floor_height - window_y - window_h / 2) / 2, z), (width, y0 + floor_height - window_y - window_h / 2, wall_t), wall_material)
            # The pane is visible, framed and collision-compatible rather than an invisible wall.
            _box(parts, f"{key}_front_glazing_{level}", (0, window_y, z + (0.025 if front == "north" else -0.025)), (window_w - 0.10, window_h - 0.10, 0.025), "glass")
            _box(parts, f"{key}_front_sill_{level}", (0, window_y - window_h / 2 - 0.05, z), (window_w + 0.16, 0.08, 0.28), "exposed_metal")
    else:
        x = (width / 2 - wall_t / 2) * (1 if front == "east" else -1)
        if level == 0:
            side_d = (depth - door_width) / 2
            _box(parts, f"{key}_front_wall_left", (x, y0 + floor_height / 2, -door_width / 2 - side_d / 2), (wall_t, floor_height, side_d), wall_material)
            _box(parts, f"{key}_front_wall_right", (x, y0 + floor_height / 2, door_width / 2 + side_d / 2), (wall_t, floor_height, side_d), wall_material)
            _box(parts, f"{key}_front_door_lintel", (x, y0 + door_height + (floor_height - door_height) / 2, 0), (wall_t, floor_height - door_height, depth), "exposed_metal")
        else:
            window_w, window_h = min(1.5, depth * 0.32), 1.0
            window_y = y0 + floor_height * 0.54
            side_d = (depth - window_w) / 2
            _box(parts, f"{key}_front_wall_left_{level}", (x, y0 + floor_height / 2, -window_w / 2 - side_d / 2), (wall_t, floor_height, side_d), wall_material)
            _box(parts, f"{key}_front_wall_right_{level}", (x, y0 + floor_height / 2, window_w / 2 + side_d / 2), (wall_t, floor_height, side_d), wall_material)
            _box(parts, f"{key}_front_spandrel_{level}", (x, y0 + (window_y - window_h / 2 - y0) / 2, 0), (wall_t, window_y - window_h / 2 - y0, depth), "patched_concrete")
            _box(parts, f"{key}_front_header_{level}", (x, window_y + window_h / 2 + (y0 + floor_height - window_y - window_h / 2) / 2, 0), (wall_t, y0 + floor_height - window_y - window_h / 2, depth), wall_material)
            _box(parts, f"{key}_front_glazing_{level}", (x + (0.025 if front == "east" else -0.025), window_y, 0), (0.025, window_h - 0.1, window_w - 0.1), "glass")
            _box(parts, f"{key}_front_sill_{level}", (x, window_y - window_h / 2 - 0.05, 0), (0.28, 0.08, window_w + 0.16), "exposed_metal")
    return door_width


def _make_building(building: dict[str, Any], index: int) -> tuple[Assembly, dict[str, Any]]:
    key = str(building["key"])
    width, depth = (float(value) for value in building["size"])
    palette = tuple(_MATERIALS[(index + shift) % len(_MATERIALS)] for shift in (0, 1, 2, 3))
    requested_height = float(building["height"])
    if key == "west_roof_access":
        levels = 3
        height = max(requested_height, 9.0)
    else:
        levels = 3 + ((index * 5 + 1) % 6)
        height = max(requested_height, levels * 2.45 + 0.5 + (index % 4) * 0.17)
    floor_height = (height - 0.42) / levels
    parts: list[geo.MeshData] = []
    wall_t = 0.18

    # Each storey has its own floor, changing wall plane, open storefront and window bays.
    for level in range(levels):
        y0 = level * floor_height
        inset = 0.0 if level < 2 else 0.10 * (1 + index % 3)
        w, d = width - inset, depth - inset * 0.65
        floor_thickness = 0.06 if level == 0 else 0.16
        floor_center_y = 0.03 if level == 0 else y0 + 0.08
        _box(parts, f"{key}_floor_slab_{level}", (0, floor_center_y, 0), (w - 0.25, floor_thickness, d - 0.25), "concrete" if level else "patched_concrete")
        _front_wall(parts, key, w, d, y0, floor_height, str(building["front"]), level, palette)
        # Continuous side/rear walls retain the occupied room volume but use openings and patch panels.
        side_material = palette[(level + 1) % len(palette)]
        rear_material = palette[(level + 2) % len(palette)]
        if building["front"] in ("north", "south"):
            rear_z = -(d - wall_t) / 2 if building["front"] == "north" else (d - wall_t) / 2
            _box(parts, f"{key}_rear_wall_{level}", (0, y0 + floor_height / 2, rear_z), (w, floor_height, wall_t), rear_material)
            for side, x in ((-1, -(w - wall_t) / 2), (1, (w - wall_t) / 2)):
                _box(parts, f"{key}_side_wall_{side}_{level}", (x, y0 + floor_height / 2, 0), (wall_t, floor_height, d), side_material if side < 0 else palette[level % len(palette)])
        else:
            rear_x = -(w - wall_t) / 2 if building["front"] == "east" else (w - wall_t) / 2
            _box(parts, f"{key}_rear_wall_{level}", (rear_x, y0 + floor_height / 2, 0), (wall_t, floor_height, d), rear_material)
            for side, z in ((-1, -(d - wall_t) / 2), (1, (d - wall_t) / 2)):
                _box(parts, f"{key}_side_wall_{side}_{level}", (0, y0 + floor_height / 2, z), (w, floor_height, wall_t), side_material if side < 0 else palette[level % len(palette)])
        # Structural pilasters, floor-to-floor band, drain and a visibly supported awning.
        for side in (-1, 1):
            _box(parts, f"{key}_facade_pilaster_{level}_{side}", (side * (w / 2 - 0.13), y0 + floor_height / 2, -d / 2), (0.16, floor_height, 0.19), "exposed_metal" if level % 2 else "rust")
        _box(parts, f"{key}_floor_band_{level}", (0, y0 + floor_height - 0.10, -d / 2), (w + 0.14, 0.15, 0.26), "painted_metal" if level % 2 else "patched_concrete", 0.025)
        if level == 0:
            # The leaf is actually hinged at one jamb, swung inward along the side of the passage.
            leaf_width = 1.05
            hinge_offset = 1.25 / 2 + 0.04
            if building["front"] in ("north", "south"):
                door_x = -hinge_offset
                door_z = (depth / 2 - wall_t / 2 - leaf_width / 2) * (1 if building["front"] == "north" else -1)
                door_size = (0.07, 2.06, leaf_width)
                pull_x, pull_z = door_x + 0.12, door_z
            else:
                door_x = (width / 2 - wall_t / 2 - leaf_width / 2) * (1 if building["front"] == "east" else -1)
                door_z = -hinge_offset
                door_size = (leaf_width, 2.06, 0.07)
                pull_x, pull_z = door_x, door_z + 0.12
            _box(parts, f"{key}_open_door_leaf", (door_x, 1.04, door_z), door_size, "wood", 0.02)
            _pipe(parts, f"{key}_door_pull", (pull_x, 0.92, pull_z), (pull_x, 1.26, pull_z), 0.018, "exposed_metal")
        # Unequal louvered windows, lintels, bolts and compact warm interior glazing.
        if level > 0:
            wx, wy = ((-0.27 if index % 2 else 0.25) * w, y0 + floor_height * 0.55)
            z = -d / 2 - 0.025 if building["front"] == "south" else d / 2 + 0.025
            if building["front"] in ("north", "south"):
                for side in (-1, 1):
                    _box(parts, f"{key}_window_jamb_{level}_{side}", (wx + side * 0.83, wy, z), (0.08, 1.32, 0.12), "painted_metal")
                for row in range(4):
                    _box(parts, f"{key}_window_louver_{level}_{row}", (wx, wy - 0.42 + row * 0.28, z - 0.055), (1.56, 0.035, 0.045), "exposed_metal" if row % 2 else "faded_teal")
            else:
                x = -width / 2 - 0.025 if building["front"] == "west" else width / 2 + 0.025
                for side in (-1, 1):
                    _box(parts, f"{key}_window_jamb_{level}_{side}", (x, wy, wx + side * 0.83), (0.12, 1.32, 0.08), "painted_metal")
                for row in range(4):
                    _box(parts, f"{key}_window_louver_{level}_{row}", (x, wy - 0.42 + row * 0.28, wx), (0.045, 0.035, 1.56), "exposed_metal" if row % 2 else "faded_teal")
            _box(parts, f"{key}_interior_warm_window_{level}", (wx, wy, z + (0.08 if building["front"] == "south" else -0.08)), (1.22, 0.96, 0.025), "warm_light")
        # Each facade addition is bolted into a bearer; protrusions remain above head height.
        _box(parts, f"{key}_awning_bracket_{level}", (0, y0 + 2.30, -d / 2 - 0.38), (0.11, 0.06, 0.55), "exposed_metal")
        _box(parts, f"{key}_service_canopy_{level}", (0, y0 + 2.26, -d / 2 - 0.48), (min(w - 0.5, 2.5 + (index % 4) * 0.25), 0.08, 0.94), "painted_metal", 0.025)

    roof_y = levels * floor_height + 0.08
    _box(parts, f"{key}_roof_slab", (0, roof_y, 0), (width + 0.20, 0.22, depth + 0.20), "exposed_metal")
    # Mixed parapet / rails leave the roof stair landing open and add safe edge protection.
    rail_y = roof_y + 0.62
    for side in (-1, 1):
        x = side * (width / 2 - 0.08)
        _pipe(parts, f"{key}_roof_rail_side_{side}", (x, rail_y, -depth / 2), (x, rail_y, depth / 2), 0.026, "rust")
        for n in range(5):
            z = -depth / 2 + n * depth / 4
            _pipe(parts, f"{key}_roof_baluster_{side}_{n}", (x, roof_y + 0.15, z), (x, rail_y, z), 0.014, "exposed_metal")
    # Roof service hut, tank saddle, exhaust, meters and patched conduits.
    hut_x = 0.38 if index % 2 else -0.42
    _box(parts, f"{key}_roof_prefab_hut", (hut_x, roof_y + 0.92, 0.28), (min(2.1, width * 0.36), 1.62, min(1.8, depth * 0.30)), "patched_concrete", 0.045)
    _box(parts, f"{key}_roof_hut_door", (hut_x, roof_y + 0.73, 0.28 - min(1.8, depth * 0.30) / 2 - 0.018), (0.72, 1.27, 0.035), "painted_metal", 0.018)
    _cylinder = geo.cylinder(f"{key}_roof_water_tank", (-width * 0.30, roof_y + 0.68, depth * 0.24), 0.46, 1.16, "cream_plastic", segments=16)
    parts.append(_cylinder)
    for clamp_y in (roof_y + 0.24, roof_y + 0.98):
        _pipe(parts, f"{key}_tank_hoop_{clamp_y:.2f}", (-width * .30 - .40, clamp_y, depth * .24), (-width * .30 + .40, clamp_y, depth * .24), 0.018, "exposed_metal")
    _box(parts, f"{key}_roof_service_panel", (width * .28, roof_y + 0.48, -depth * .27), (0.64, 0.82, 0.12), "faded_teal", 0.022)
    _box(parts, f"{key}_roof_gauge_face", (width * .28, roof_y + 0.56, -depth * .19), (0.29, 0.23, 0.025), "glass")
    for pipe_index in range(3):
        px = -width * .34 + pipe_index * 0.16
        _pipe(parts, f"{key}_roof_conduit_{pipe_index}", (px, roof_y + 0.17, -depth / 2), (px, roof_y + 1.7 + (index % 3) * 0.13, -depth / 2), 0.025, "rust" if pipe_index == 0 else "exposed_metal")
    # Narrow clothesline, replaced sheet, backlit but static Japanese trade placard.
    _pipe(parts, f"{key}_laundry_line", (-width * .42, roof_y + 1.96, -depth * .36), (width * .40, roof_y + 1.83, -depth * .36), 0.009, "exposed_metal")
    for n, cloth_x in enumerate((-width * .24, 0.0, width * .19)):
        _box(parts, f"{key}_roof_drying_cloth_{n}", (cloth_x, roof_y + 1.47, -depth * .35), (0.40, 0.56, 0.03), "cloth", 0.018)
    front_axis = 0 if building["front"] in ("north", "south") else 2
    left_wall = next(part for part in parts if part.name == f"{key}_front_wall_left")
    right_wall = next(part for part in parts if part.name == f"{key}_front_wall_right")
    opening_width = min(vertex[front_axis] for vertex in right_wall.vertices) - max(vertex[front_axis] for vertex in left_wall.vertices)
    lintel = next(part for part in parts if part.name == f"{key}_front_door_lintel")
    opening_height = min(vertex[1] for vertex in lintel.vertices)
    center = building["center"]
    origin = (float(center[0]), float(center[1]), float(center[2]))
    return Assembly("district_building", key, origin, 0.0, parts), {
        "building_key": key,
        "floor_count": levels,
        "height": round(roof_y + 0.73, 3),
        "roof_walk_y": round(roof_y + 0.11, 3),
        "roof_rail_y": round(rail_y, 3),
        "door_width": round(opening_width, 4),
        "door_height": round(opening_height, 4),
        "door_opening_verified_from_meshes": True,
        "route_connected": True,
        "structural_part_names": tuple(part.name for part in parts if any(token in part.name for token in ("floor_slab", "wall_", "rear_wall", "roof_slab", "glazing", "door_leaf", "roof_rail", "front_door_lintel"))),
    }


def build_districts(layout: dict[str, Any]) -> tuple[list[Assembly], dict[str, dict[str, Any]]]:
    """Build actual 21 non-north buildings and geometry-backed access records."""
    assemblies: list[Assembly] = []
    records: dict[str, dict[str, Any]] = {}
    for index, building in enumerate(item for item in layout["buildings"] if item["key"] not in _NORTH_KEYS):
        assembly, record = _make_building(building, index)
        assemblies.append(assembly)
        bounds = assembly.bounds
        record["silhouette"] = [round(bounds[1][axis] - bounds[0][axis], 3) for axis in range(3)]
        if record["building_key"] == "west_roof_access":
            record["roof_walk_y"] = round(float(building["height"]) - 0.09, 3)
            record["roof_rail_y"] = record["height"]
        record["part_count"] = len(assembly.parts)
        record["route_connected"] = any(_route_reaches_front_door(building, route) for route in layout["routes"])
        cx, _cy, cz = (float(value) for value in building["center"])
        width, depth = (float(value) for value in building["size"])
        front = building["front"]
        half_w = record["door_width"] / 2
        plane_half = 0.09
        if front in ("north", "south"):
            plane_z = cz + (depth / 2 - plane_half) * (1 if front == "north" else -1)
            gap_min = (cx - half_w, 0.06, plane_z - plane_half,)
            gap_max = (cx + half_w, record["door_height"], plane_z + plane_half,)
        else:
            plane_x = cx + (width / 2 - plane_half) * (1 if front == "east" else -1)
            gap_min = (plane_x - plane_half, 0.06, cz - half_w)
            gap_max = (plane_x + plane_half, record["door_height"], cz + half_w)
        blockers = []
        for owner, part_name, minimum, maximum in collision_parts([assembly]):
            if all(minimum[axis] < gap_max[axis] - 1e-7 and gap_min[axis] < maximum[axis] - 1e-7 for axis in range(3)):
                blockers.append(f"{owner}/{part_name}")
        record["door_opening_bounds"] = [list(gap_min), list(gap_max)]
        record["door_clearance_verified_from_colliders"] = not blockers
        record["door_blocking_parts"] = blockers
        records[record["building_key"]] = record
    return assemblies, records


def collision_parts(assemblies: list[Assembly]) -> list[tuple[str, str, tuple[float, float, float], tuple[float, float, float]]]:
    """Return only visible structural parts as exact transformed AABB collider plans."""
    tokens = ("floor_slab", "room_floor", "room_", "wall_", "rear_wall", "roof_slab", "glazing", "door_leaf", "roof_rail", "front_door_lintel", "front_spandrel", "front_header")
    colliders = []
    for assembly in assemblies:
        if assembly.kind != "district_building" and assembly.kind != "interior_room":
            continue
        for part in assembly.transformed_parts():
            if not any(token in part.name for token in tokens):
                continue
            minimum = tuple(min(vertex[axis] for vertex in part.vertices) for axis in range(3))
            maximum = tuple(max(vertex[axis] for vertex in part.vertices) for axis in range(3))
            if all(maximum[axis] - minimum[axis] > 1e-5 for axis in range(3)):
                colliders.append((assembly.name, part.name, minimum, maximum))
    return colliders
