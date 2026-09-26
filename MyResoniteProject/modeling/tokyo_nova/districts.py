"""Authored, irregular building shells for the non-north Tokyo Nova blocks."""
from __future__ import annotations

import hashlib
import math
from typing import Any

from modeling.tokyo_nova import geometry as geo
from modeling.tokyo_nova.layout import _route_reaches_front_door
from modeling.tokyo_nova.props import Assembly

Vec3 = tuple[float, float, float]
_NORTH_KEYS = {"north_yatai", "north_terminal_repair", "north_machiya"}
_MATERIALS = ("concrete", "patched_concrete", "painted_metal", "faded_teal", "exposed_metal", "rust", "wood")
_PROFILE_NAMES = ("cantilevered_slab_and_buttress", "deep_recessed_core_frame", "offset_shear_walls", "weathered_podium_terrace")


def _box(parts: list[geo.MeshData], name: str, center: Vec3, size: Vec3, material: str, bevel: float = 0.0) -> None:
    if min(size) <= 1e-5:
        raise ValueError(f"part {name} has a nonpositive dimension {size}")
    parts.append(geo.beveled_box(name, center, size, bevel, material) if bevel else geo.box(name, center, size, material))


def _pipe(parts: list[geo.MeshData], name: str, start: Vec3, end: Vec3, radius: float, material: str) -> None:
    parts.append(geo.pipe(name, start, end, radius, material, segments=8))


def _front_frame(front: str, width: float, depth: float, wall_t: float) -> tuple[float, float, float]:
    if front == "north":
        return (0.0, 0.0, depth / 2 - wall_t / 2)
    if front == "south":
        return (0.0, 0.0, -depth / 2 + wall_t / 2)
    if front == "east":
        return (width / 2 - wall_t / 2, 0.0, 0.0)
    return (-width / 2 + wall_t / 2, 0.0, 0.0)


def _front_wall(
    parts: list[geo.MeshData], key: str, width: float, depth: float, y0: float,
    floor_height: float, front: str, level: int, palette: tuple[str, ...],
    window_center: float, window_width: float, door_width: float = 1.25,
) -> tuple[float, float, float]:
    """Emit openings and fitted frames in one facade-local frame for every facing."""
    wall_t = 0.18
    wall_material = palette[level % len(palette)]
    door_height = 2.12
    x, _y, z = _front_frame(front, width, depth, wall_t)
    along_x = front in ("north", "south")
    normal = 1.0 if front in ("north", "east") else -1.0
    if level == 0:
        if along_x:
            left = width / 2 - door_width / 2
            right = width / 2 - door_width / 2
            _box(parts, f"{key}_front_wall_left", (-door_width / 2 - left / 2, y0 + floor_height / 2, z), (left, floor_height, wall_t), wall_material)
            _box(parts, f"{key}_front_wall_right", (door_width / 2 + right / 2, y0 + floor_height / 2, z), (right, floor_height, wall_t), wall_material)
            _box(parts, f"{key}_front_door_lintel", (0, y0 + door_height + (floor_height - door_height) / 2, z), (width, floor_height - door_height, wall_t), "exposed_metal")
        else:
            left = depth / 2 - door_width / 2
            right = depth / 2 - door_width / 2
            _box(parts, f"{key}_front_wall_left", (x, y0 + floor_height / 2, -door_width / 2 - left / 2), (wall_t, floor_height, left), wall_material)
            _box(parts, f"{key}_front_wall_right", (x, y0 + floor_height / 2, door_width / 2 + right / 2), (wall_t, floor_height, right), wall_material)
            _box(parts, f"{key}_front_door_lintel", (x, y0 + door_height + (floor_height - door_height) / 2, 0), (wall_t, floor_height - door_height, depth), "exposed_metal")
        return door_width, door_height, 0.0

    window_height = min(1.05, floor_height * 0.43)
    window_center_y = y0 + floor_height * 0.54
    window_center = max(-((width if along_x else depth) / 2) + window_width / 2 + 0.1, min(window_center, ((width if along_x else depth) / 2) - window_width / 2 - 0.1))
    low_u, high_u = window_center - window_width / 2, window_center + window_width / 2
    total_u = width if along_x else depth
    left_span, right_span = low_u + total_u / 2, total_u / 2 - high_u
    if along_x:
        _box(parts, f"{key}_front_wall_left_{level}", (-total_u / 2 + left_span / 2, y0 + floor_height / 2, z), (left_span, floor_height, wall_t), wall_material)
        _box(parts, f"{key}_front_wall_right_{level}", (high_u + right_span / 2, y0 + floor_height / 2, z), (right_span, floor_height, wall_t), wall_material)
        bottom_h = max(0.05, window_center_y - window_height / 2 - y0)
        top_h = max(0.05, y0 + floor_height - window_center_y - window_height / 2)
        _box(parts, f"{key}_front_spandrel_{level}", (window_center, y0 + bottom_h / 2, z), (window_width, bottom_h, wall_t), "patched_concrete")
        _box(parts, f"{key}_front_header_{level}", (window_center, window_center_y + window_height / 2 + top_h / 2, z), (window_width, top_h, wall_t), wall_material)
        glass_center = (window_center, window_center_y, z + normal * 0.025)
        _box(parts, f"{key}_front_glazing_{level}", glass_center, (window_width - 0.12, window_height - 0.12, 0.025), "glass")
        for side in (-1, 1):
            _box(parts, f"{key}_front_window_jamb_{level}_{side}", (window_center + side * (window_width / 2 - 0.025), window_center_y, z + normal * 0.015), (0.05, window_height + 0.04, wall_t * 0.8), "painted_metal")
        _box(parts, f"{key}_front_window_sill_{level}", (window_center, window_center_y - window_height / 2 - 0.04, z), (window_width + 0.12, 0.08, 0.28), "exposed_metal")
    else:
        _box(parts, f"{key}_front_wall_left_{level}", (x, y0 + floor_height / 2, -total_u / 2 + left_span / 2), (wall_t, floor_height, left_span), wall_material)
        _box(parts, f"{key}_front_wall_right_{level}", (x, y0 + floor_height / 2, high_u + right_span / 2), (wall_t, floor_height, right_span), wall_material)
        bottom_h = max(0.05, window_center_y - window_height / 2 - y0)
        top_h = max(0.05, y0 + floor_height - window_center_y - window_height / 2)
        _box(parts, f"{key}_front_spandrel_{level}", (x, y0 + bottom_h / 2, window_center), (wall_t, bottom_h, window_width), "patched_concrete")
        _box(parts, f"{key}_front_header_{level}", (x, window_center_y + window_height / 2 + top_h / 2, window_center), (wall_t, top_h, window_width), wall_material)
        glass_center = (x + normal * 0.025, window_center_y, window_center)
        _box(parts, f"{key}_front_glazing_{level}", glass_center, (0.025, window_height - 0.12, window_width - 0.12), "glass")
        for side in (-1, 1):
            _box(parts, f"{key}_front_window_jamb_{level}_{side}", (x + normal * 0.015, window_center_y, window_center + side * (window_width / 2 - 0.025)), (wall_t * 0.8, window_height + 0.04, 0.05), "painted_metal")
        _box(parts, f"{key}_front_window_sill_{level}", (x, window_center_y - window_height / 2 - 0.04, window_center), (0.28, 0.08, window_width + 0.12), "exposed_metal")
    return window_center, window_center_y, window_width


def _floor_slab_parts(
    parts: list[geo.MeshData], key: str, width: float, depth: float, y: float,
    thickness: float, projection: float, access: dict[str, Any] | None, level: int,
) -> None:
    floor_w, floor_d = width + projection, depth + projection
    slab_key = f"{key}_floor_slab_{level}"
    if access is None:
        _box(parts, slab_key, (0, y, 0), (floor_w, thickness, floor_d), "patched_concrete")
        return
    opening = access["floor_opening"]
    center_x, center_z = (float(value) for value in opening["center"])
    size_x, size_z = (float(value) for value in opening["size"])
    xmin, xmax = -floor_w / 2, floor_w / 2
    zmin, zmax = -floor_d / 2, floor_d / 2
    hole_x0, hole_x1 = max(xmin, center_x - size_x / 2), min(xmax, center_x + size_x / 2)
    hole_z0, hole_z1 = max(zmin, center_z - size_z / 2), min(zmax, center_z + size_z / 2)
    # A frontage opening also cuts the projecting slab lip. Ground cutouts stop
    # at the entry plane, so the adjacent public route keeps its grade support.
    side = access["entry_side"]
    if side == "north":
        hole_z1 = zmax
    elif side == "south":
        hole_z0 = zmin
    elif side == "east":
        hole_x1 = xmax
    elif side == "west":
        hole_x0 = xmin
    if hole_x1 <= hole_x0 or hole_z1 <= hole_z0:
        raise ValueError(f"floor opening for {key} does not intersect its emitted floor slab")

    def panel(label: str, x0: float, x1: float, z0: float, z1: float) -> None:
        if x1 - x0 > 0.03 and z1 - z0 > 0.03:
            _box(parts, f"{slab_key}_{label}", ((x0 + x1) / 2, y, (z0 + z1) / 2), (x1 - x0, thickness, z1 - z0), "patched_concrete")

    panel("west", xmin, hole_x0, zmin, zmax)
    panel("east", hole_x1, xmax, zmin, zmax)
    panel("rear", hole_x0, hole_x1, zmin, hole_z0)
    panel("front", hole_x0, hole_x1, hole_z1, zmax)


def _emit_formwork_and_ties(
    parts: list[geo.MeshData], key: str, width: float, depth: float, y0: float,
    floor_height: float, front: str, level: int, window: tuple[float, float, float] | None,
    module_width: float, density: float, profile: int,
) -> None:
    wall_t = 0.18
    x, _y, z = _front_frame(front, width, depth, wall_t)
    along_x = front in ("north", "south")
    outward = 1.0 if front in ("north", "east") else -1.0
    outer_x, outer_z = (x + outward * wall_t / 2, z) if not along_x else (x, z + outward * wall_t / 2)
    span = width if along_x else depth
    step = max(0.75, module_width / max(0.25, density))
    count = max(1, int(math.floor((span - 0.8) / step)))
    for module in range(count + 1):
        u = -span / 2 + 0.4 + module * (span - 0.8) / count
        if window is not None and abs(u - window[0]) < window[2] / 2 + 0.16:
            continue
        if level == 0 and abs(u) < 0.80:
            continue
        if along_x:
            _box(parts, f"{key}_formwork_joint_{level}_{module}", (u, y0 + floor_height / 2, outer_z + outward * 0.008), (0.012, floor_height - 0.40, 0.012), "exposed_metal")
            for row, y in enumerate((y0 + 0.22, y0 + floor_height - 0.22)):
                parts.append(geo.cylinder(f"{key}_concrete_tie_hole_{level}_{module}_{row}", (u, y, outer_z + outward * 0.015), 0.026, 0.012, "rubber", segments=8, axis=(0, 0, 1)))
        else:
            _box(parts, f"{key}_formwork_joint_{level}_{module}", (outer_x + outward * 0.008, y0 + floor_height / 2, u), (0.012, floor_height - 0.40, 0.012), "exposed_metal")
            for row, y in enumerate((y0 + 0.22, y0 + floor_height - 0.22)):
                parts.append(geo.cylinder(f"{key}_concrete_tie_hole_{level}_{module}_{row}", (outer_x + outward * 0.015, y, u), 0.026, 0.012, "rubber", segments=8, axis=(1, 0, 0)))
    if profile == 2 and level > 0:
        _box(parts, f"{key}_cast_shadow_reveal_{level}", (outer_x + outward * 0.012, y0 + floor_height * 0.52, 0), (0.018, 0.025, min(depth * 0.74, 4.8)), "rust")


def _emit_vertical_service_details(parts: list[geo.MeshData], key: str, width: float, depth: float, roof_y: float, front: str, profile: int) -> None:
    x, _y, z = _front_frame(front, width, depth, 0.18)
    outward = 1.0 if front in ("north", "east") else -1.0
    sign_u = width if front in ("north", "south") else depth
    u = min(sign_u * 0.34, 1.15)
    if front in ("north", "south"):
        sign_x, sign_z = u, z + outward * 0.12
        sign_size = (0.28, min(1.6, roof_y * 0.18), 0.065)
    else:
        sign_x, sign_z = x + outward * 0.12, u
        sign_size = (0.065, min(1.6, roof_y * 0.18), 0.28)
    sign_y = min(2.75, roof_y * 0.24)
    _box(parts, f"{key}_vertical_service_sign_backplate", (sign_x, sign_y, sign_z), sign_size, "faded_teal")
    if profile in (1, 3):
        strip_size = (0.025, sign_size[1] * 0.82, 0.025) if front in ("north", "south") else (0.025, sign_size[1] * 0.82, 0.025)
        _box(parts, f"{key}_vertical_service_sign_sparse_light_strip", (sign_x, sign_y, sign_z - outward * 0.04), strip_size, "warm_light" if profile == 3 else "cool_light")
    if profile != 1:
        if front in ("north", "south"):
            cable_x, cable_z = -width * 0.40, z + outward * 0.10
            _pipe(parts, f"{key}_vertical_service_cable_riser", (cable_x, 0.25, cable_z), (cable_x, roof_y, cable_z), 0.018, "rust")
            for bracket in range(max(2, int(roof_y // 4))):
                y = 0.75 + bracket * 3.4
                _box(parts, f"{key}_cable_riser_clamp_{bracket}", (cable_x, y, cable_z), (0.12, 0.035, 0.035), "exposed_metal")
        else:
            cable_x, cable_z = x + outward * 0.10, -depth * 0.40
            _pipe(parts, f"{key}_vertical_service_cable_riser", (cable_x, 0.25, cable_z), (cable_x, roof_y, cable_z), 0.018, "rust")
            for bracket in range(max(2, int(roof_y // 4))):
                y = 0.75 + bracket * 3.4
                _box(parts, f"{key}_cable_riser_clamp_{bracket}", (cable_x, y, cable_z), (0.035, 0.035, 0.12), "exposed_metal")


def _make_building(building: dict[str, Any], index: int, generation: dict[str, Any], access: dict[str, Any] | None) -> tuple[Assembly, dict[str, Any]]:
    key = str(building["key"])
    width, depth = (float(value) for value in building["size"])
    seed = int(generation["seed"])
    profile = (seed + index * 17) % len(_PROFILE_NAMES)
    digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).digest()
    min_storeys, max_storeys = int(generation["storeys_min"]), int(generation["storeys_max"])
    if key == "west_roof_access":
        levels = 3
    else:
        levels = min_storeys + int.from_bytes(digest[:2], "big") % (max_storeys - min_storeys + 1)
    storey_height = float(generation["storey_height_m"])
    height = max(float(building["height"]), levels * storey_height + 0.42)
    floor_height = (height - 0.42) / levels
    palette = tuple(_MATERIALS[(index + profile + shift) % len(_MATERIALS)] for shift in (0, 1, 2, 3))
    parts: list[geo.MeshData] = []
    wall_t = 0.18
    projection = 0.18 + profile * 0.07
    window_width = min(1.55, width * 0.34)
    window_u = ((-0.28 if profile % 2 else 0.25) * (width if building["front"] in ("north", "south") else depth))
    opening_access = access
    entry_width = float(access["clear_width"]) if access is not None else 1.25

    for level in range(levels):
        y0 = level * floor_height
        inset = 0.0 if level < 2 else min(0.72, (level - 1) * (0.12 + profile * 0.018))
        if profile == 3 and level >= 3 and level % 2:
            inset += 0.10
        w, d = width - inset, depth - inset * 0.65
        slab_t = 0.08 if level == 0 else 0.16
        slab_y = 0.03 if level == 0 else y0 + 0.08
        _floor_slab_parts(parts, key, w, d, slab_y, slab_t, projection, opening_access if level == 0 else None, level)
        window = _front_wall(parts, key, w, d, y0, floor_height, str(building["front"]), level, palette, window_u, window_width, entry_width)
        if level > 0:
            actual_window_center, window_y, actual_window_width = window
            u = actual_window_center
            if building["front"] in ("north", "south"):
                frame_z = _front_frame(str(building["front"]), w, d, wall_t)[2]
                normal = 1 if building["front"] == "north" else -1
                glass_z = frame_z + normal * 0.025
                for row in range(4):
                    ly = window_y - window_height if False else window_y - 0.38 + row * 0.25
                    _box(parts, f"{key}_window_louver_{level}_{row}", (u, ly, glass_z + normal * 0.035), (actual_window_width * 0.92, 0.028, 0.03), "exposed_metal" if row % 2 else "faded_teal")
                light_center = (u, window_y, glass_z - normal * 0.045)
                _box(parts, f"{key}_interior_warm_window_{level}", light_center, (actual_window_width - 0.18, 0.82, 0.018), "warm_light")
            else:
                frame_x = _front_frame(str(building["front"]), w, d, wall_t)[0]
                normal = 1 if building["front"] == "east" else -1
                glass_x = frame_x + normal * 0.025
                for row in range(4):
                    ly = window_y - 0.38 + row * 0.25
                    _box(parts, f"{key}_window_louver_{level}_{row}", (glass_x + normal * 0.035, ly, u), (0.03, 0.028, actual_window_width * 0.92), "exposed_metal" if row % 2 else "faded_teal")
                light_center = (glass_x - normal * 0.045, window_y, u)
                _box(parts, f"{key}_interior_warm_window_{level}", light_center, (0.018, 0.82, actual_window_width - 0.18), "warm_light")
            window = (actual_window_center, window_y, actual_window_width)
        else:
            window = None

        rear_material = palette[(level + 2) % len(palette)]
        side_material = palette[(level + 1) % len(palette)]
        if building["front"] in ("north", "south"):
            rear_z = -(d - wall_t) / 2 if building["front"] == "north" else (d - wall_t) / 2
            _box(parts, f"{key}_rear_wall_{level}", (0, y0 + floor_height / 2, rear_z), (w, floor_height, wall_t), rear_material)
            for side, side_x in ((-1, -(w - wall_t) / 2), (1, (w - wall_t) / 2)):
                _box(parts, f"{key}_wall_side_{side}_{level}", (side_x, y0 + floor_height / 2, 0), (wall_t, floor_height, d), side_material)
        else:
            rear_x = -(w - wall_t) / 2 if building["front"] == "east" else (w - wall_t) / 2
            _box(parts, f"{key}_rear_wall_{level}", (rear_x, y0 + floor_height / 2, 0), (wall_t, floor_height, d), rear_material)
            for side, side_z in ((-1, -(d - wall_t) / 2), (1, (d - wall_t) / 2)):
                _box(parts, f"{key}_wall_side_{side}_{level}", (0, y0 + floor_height / 2, side_z), (w, floor_height, wall_t), side_material)

        # Full-height concrete piers carry the projecting slabs; footing blocks vary by profile.
        pier_w = 0.28 + (0.08 if profile == 1 else 0.0)
        for sx in (-1, 1):
            for sz in (-1, 1):
                px, pz = sx * (w / 2 - pier_w / 2), sz * (d / 2 - pier_w / 2)
                _box(parts, f"{key}_loadbearing_pier_{level}_{sx}_{sz}", (px, y0 + floor_height / 2, pz), (pier_w, floor_height + 0.08, pier_w), "concrete", 0.015)
                if profile in (0, 1):
                    _box(parts, f"{key}_buttress_foot_{level}_{sx}_{sz}", (px, y0 + 0.14, pz), (pier_w * 1.55, 0.28, pier_w * 1.55), "patched_concrete")
        band_material = "patched_concrete" if level % 2 == 0 else "painted_metal"
        if building["front"] in ("north", "south"):
            sign = 1 if building["front"] == "north" else -1
            band_z = sign * (d / 2 + projection * 0.12)
            _box(parts, f"{key}_cantilever_floor_band_{level}", (0, y0 + floor_height - 0.09, band_z), (w + projection, 0.17, 0.26 + projection * 0.18), band_material, 0.025)
        else:
            sign = 1 if building["front"] == "east" else -1
            band_x = sign * (w / 2 + projection * 0.12)
            _box(parts, f"{key}_cantilever_floor_band_{level}", (band_x, y0 + floor_height - 0.09, 0), (0.26 + projection * 0.18, 0.17, d + projection), band_material, 0.025)
        _emit_formwork_and_ties(parts, key, w, d, y0, floor_height, str(building["front"]), level, window, float(generation["facade_module_width_m"]), float(generation["facade_detail_density"]), profile)

        if level == 0:
            leaf_width = 1.05
            hinge_offset = entry_width + (0.24 if access is not None else 0.0)
            if building["front"] in ("north", "south"):
                door_x = -(hinge_offset / 2 + 0.04)
                door_z = (depth / 2 - wall_t / 2 - leaf_width / 2) * (1 if building["front"] == "north" else -1)
                door_size = (0.07, 2.06, leaf_width)
                pull_x, pull_z = door_x + 0.12, door_z
            else:
                door_x = (width / 2 - wall_t / 2 - leaf_width / 2) * (1 if building["front"] == "east" else -1)
                door_z = -(hinge_offset / 2 + 0.04)
                door_size = (leaf_width, 2.06, 0.07)
                pull_x, pull_z = door_x, door_z + 0.12
            _box(parts, f"{key}_open_door_leaf", (door_x, 1.04, door_z), door_size, "wood", 0.02)
            _pipe(parts, f"{key}_door_pull", (pull_x, 0.92, pull_z), (pull_x, 1.26, pull_z), 0.018, "exposed_metal")
        # Deep canopies, interrupted vents and tied-back electrical risers enrich the street facade.
        front_x, _fy, front_z = _front_frame(str(building["front"]), w, d, wall_t)
        if building["front"] in ("north", "south"):
            outward = 1 if building["front"] == "north" else -1
            _box(parts, f"{key}_awning_bracket_{level}", (0, y0 + 2.30, front_z + outward * 0.22), (0.11, 0.06, 0.55), "exposed_metal")
            _box(parts, f"{key}_service_canopy_{level}", (0, y0 + 2.26, front_z + outward * 0.34), (min(w - 0.5, 2.5 + (index % 4) * 0.25), 0.08, 0.94), "painted_metal", 0.025)
        else:
            outward = 1 if building["front"] == "east" else -1
            _box(parts, f"{key}_awning_bracket_{level}", (front_x + outward * 0.22, y0 + 2.30, 0), (0.55, 0.06, 0.11), "exposed_metal")
            _box(parts, f"{key}_service_canopy_{level}", (front_x + outward * 0.34, y0 + 2.26, 0), (0.94, 0.08, min(d - 0.5, 2.5 + (index % 4) * 0.25)), "painted_metal", 0.025)

    roof_y = levels * floor_height + 0.08
    _box(parts, f"{key}_roof_slab", (0, roof_y, 0), (width + 0.20, 0.22, depth + 0.20), "exposed_metal")
    roof_surface = roof_y + 0.11
    roof_half_x, roof_half_z = (width + 0.20) / 2, (depth + 0.20) / 2
    rail_y = roof_surface + 1.05
    entry_offset = float(building.get("roof_entry_z_offset", 2.0))
    entry_half = 1.10
    west_segments = ((-roof_half_z, entry_offset - entry_half), (entry_offset + entry_half, roof_half_z))
    for side, x in (("west", -roof_half_x), ("east", roof_half_x)):
        segments = west_segments if side == "west" else ((-roof_half_z, roof_half_z),)
        for segment, (low, high) in enumerate(segments):
            if high - low < 0.12:
                continue
            _pipe(parts, f"{key}_roof_rail_{side}_{segment}", (x, rail_y, low), (x, rail_y, high), 0.028, "rust")
            count = max(2, int((high - low) / 0.9))
            for post in range(count + 1):
                zz = low + (high - low) * post / count
                _pipe(parts, f"{key}_roof_baluster_{side}_{segment}_{post}", (x, roof_surface + 0.10, zz), (x, rail_y, zz), 0.014, "exposed_metal")
    for side, z in (("south", -roof_half_z), ("north", roof_half_z)):
        _pipe(parts, f"{key}_roof_rail_{side}_0", (-roof_half_x, rail_y, z), (roof_half_x, rail_y, z), 0.028, "rust")
        count = max(3, int((2 * roof_half_x) / 0.9))
        for post in range(count + 1):
            xx = -roof_half_x + 2 * roof_half_x * post / count
            _pipe(parts, f"{key}_roof_baluster_{side}_{post}", (xx, roof_surface + 0.10, z), (xx, rail_y, z), 0.014, "exposed_metal")

    # Roof silhouettes differ by seeded structural profile rather than repeating one box kit.
    hut_x = 0.38 if profile % 2 else -0.42
    hut_depth = min(1.8, depth * 0.30)
    if profile in (0, 2):
        _box(parts, f"{key}_roof_prefab_plant_room", (hut_x, roof_surface + 0.82, -0.28), (min(2.1, width * 0.36), 1.48, hut_depth), "patched_concrete", 0.045)
        _box(parts, f"{key}_roof_plant_room_door", (hut_x, roof_surface + 0.70, -0.28 - hut_depth / 2 - 0.018), (0.68, 1.18, 0.035), "painted_metal", 0.018)
    if profile in (0, 1, 3):
        parts.append(geo.cylinder(f"{key}_roof_reused_water_tank", (-width * 0.30, roof_surface + 0.58, depth * 0.24), 0.42, 1.02, "cream_plastic", segments=16))
        for ring_y in (roof_surface + 0.20, roof_surface + 0.91):
            _pipe(parts, f"{key}_roof_tank_hoop_{ring_y:.2f}", (-width * 0.30 - 0.37, ring_y, depth * 0.24), (-width * 0.30 + 0.37, ring_y, depth * 0.24), 0.016, "exposed_metal")
    if profile == 1:
        for mast in (-0.55, 0.0, 0.55):
            _pipe(parts, f"{key}_roof_antenna_mast_{mast:+.2f}", (mast, roof_surface, -depth * 0.30), (mast, roof_surface + 2.4, -depth * 0.30), 0.018, "exposed_metal")
    if profile == 2:
        for vent in range(3):
            x = -width * 0.30 + vent * width * 0.30
            _box(parts, f"{key}_roof_louver_vent_{vent}", (x, roof_surface + 0.38, depth * 0.30), (0.42, 0.72, 0.34), "painted_metal", 0.025)
    if profile == 3:
        for post in (-1, 1):
            _pipe(parts, f"{key}_roof_repair_gantry_post_{post}", (post * width * 0.32, roof_surface, -depth * 0.34), (post * width * 0.32, roof_surface + 1.8, -depth * 0.34), 0.03, "rust")
        _pipe(parts, f"{key}_roof_repair_gantry_beam", (-width * 0.32, roof_surface + 1.8, -depth * 0.34), (width * 0.32, roof_surface + 1.8, -depth * 0.34), 0.03, "exposed_metal")
    _box(parts, f"{key}_roof_service_panel", (width * 0.28, roof_surface + 0.38, -depth * 0.27), (0.64, 0.72, 0.12), "faded_teal", 0.022)
    _box(parts, f"{key}_roof_gauge_face", (width * 0.28, roof_surface + 0.44, -depth * 0.19), (0.29, 0.23, 0.025), "glass")
    for pipe_index in range(2 + profile % 2):
        px = -width * 0.34 + pipe_index * 0.18
        _pipe(parts, f"{key}_roof_conduit_{pipe_index}", (px, roof_surface + 0.10, -depth / 2), (px, roof_surface + 1.52, -depth / 2), 0.022, "rust" if pipe_index == 0 else "exposed_metal")
    _emit_vertical_service_details(parts, key, width, depth, roof_surface, str(building["front"]), profile)

    front_axis = 0 if building["front"] in ("north", "south") else 2
    left_wall = next(part for part in parts if part.name == f"{key}_front_wall_left")
    right_wall = next(part for part in parts if part.name == f"{key}_front_wall_right")
    opening_width = min(vertex[front_axis] for vertex in right_wall.vertices) - max(vertex[front_axis] for vertex in left_wall.vertices)
    lintel = next(part for part in parts if part.name == f"{key}_front_door_lintel")
    opening_height = min(vertex[1] for vertex in lintel.vertices)
    center = building["center"]
    origin = (float(center[0]), float(center[1]), float(center[2]))
    assembly = Assembly("district_building", key, origin, 0.0, parts)
    roof_part = next(part for part in assembly.transformed_parts() if part.name == f"{key}_roof_slab")
    roof_min = tuple(min(vertex[axis] for vertex in roof_part.vertices) for axis in range(3))
    roof_max = tuple(max(vertex[axis] for vertex in roof_part.vertices) for axis in range(3))
    return assembly, {
        "building_key": key,
        "floor_count": levels,
        "height": round(roof_max[1] + 1.05, 3),
        "roof_walk_y": round(roof_max[1], 5),
        "roof_rail_y": round(rail_y, 3),
        "roof_slab_bounds": [list(roof_min), list(roof_max)],
        "roof_entry_point": [round(roof_min[0], 5), round(roof_max[1], 5), round(origin[2] + entry_offset, 5)],
        "roof_entry_clear_width": 2 * entry_half,
        "architecture_profile": _PROFILE_NAMES[profile],
        "door_width": round(opening_width, 4),
        "door_height": round(opening_height, 4),
        "door_opening_verified_from_meshes": True,
        "route_connected": True,
        "structural_part_names": tuple(part.name for part in parts if any(token in part.name for token in ("floor_slab", "cantilever", "wall_", "rear_wall", "roof_slab", "glazing", "door_leaf", "roof_rail", "front_door_lintel", "loadbearing_pier", "formwork_joint", "concrete_tie_hole"))),
    }


def build_districts(layout: dict[str, Any]) -> tuple[list[Assembly], dict[str, dict[str, Any]]]:
    """Build 21 non-north structures with seeded silhouettes and measured connections."""
    generation = layout["generation"]
    access_by_key = {item["building_key"]: item for item in layout["basement_access"]}
    roof = layout["roof_access"]
    assemblies: list[Assembly] = []
    records: dict[str, dict[str, Any]] = {}
    for index, source_building in enumerate(item for item in layout["buildings"] if item["key"] not in _NORTH_KEYS):
        building = dict(source_building)
        if building["key"] == roof["building_key"]:
            building["roof_entry_z_offset"] = float(roof["flights"][-1]["roof_entry_z_offset"])
        assembly, record = _make_building(building, index, generation, access_by_key.get(building["key"]))
        assemblies.append(assembly)
        bounds = assembly.bounds
        record["silhouette"] = [round(bounds[1][axis] - bounds[0][axis], 3) for axis in range(3)]
        record["part_count"] = len(assembly.parts)
        record["route_connected"] = any(_route_reaches_front_door(building, route) for route in layout["routes"])
        cx, _cy, cz = (float(value) for value in building["center"])
        width, depth = (float(value) for value in building["size"])
        front = building["front"]
        half_w = record["door_width"] / 2
        plane_half = 0.09
        if front in ("north", "south"):
            plane_z = cz + (depth / 2 - plane_half) * (1 if front == "north" else -1)
            gap_min = (cx - half_w, 0.06, plane_z - plane_half)
            gap_max = (cx + half_w, record["door_height"], plane_z + plane_half)
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


def roof_access_report(layout: dict[str, Any], assembly: Assembly, record: dict[str, Any]) -> dict[str, Any]:
    """Verify flight rise/run, landings, guardrail gap and slab endpoint from emitted meshes."""
    route = layout["roof_access"]
    entry = tuple(float(value) for value in record["roof_entry_point"])
    slab = record["roof_slab_bounds"]
    slab_min, slab_max = tuple(slab[0]), tuple(slab[1])
    flights = route["flights"]
    landings = route["turn_landings"]
    resolved: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    for index, flight in enumerate(flights):
        sx, sy, sz = (float(value) for value in flight["start"])
        ex, ey, ez = (float(value) for value in flight["end"]) if "end" in flight else entry
        start, end = (sx, sy, sz), (ex, ey, ez)
        horizontal = math.hypot(end[0] - start[0], end[2] - start[2])
        resolved.append((start, end))
        if horizontal <= 1e-6 or abs(end[1] - start[1]) / horizontal > 0.20:
            return {"continuous": False, "reason": f"flight {index} exceeds safe grade", "flights": []}
    turn_clearance = []
    landing_size = tuple(float(value) for value in route["landing_size"])
    for index, landing in enumerate(landings):
        center = tuple(float(value) for value in landing["center"])
        before, after = resolved[index][1], resolved[index + 1][0]
        contained = all(abs(point[axis] - center[axis]) <= landing_size[0 if axis == 0 else 1] / 2 for point in (before, after) for axis in (0, 2))
        level = abs(before[1] - center[1]) <= 0.02 and abs(after[1] - center[1]) <= 0.02
        at_boundary = all(min(abs(abs(point[axis] - center[axis]) - landing_size[0 if axis == 0 else 1] / 2) for axis in (0, 2)) <= 0.005 for point in (before, after))
        turn_clearance.append({"landing_key": landing["key"], "endpoints_within_mesh_footprint": contained, "endpoints_at_platform_boundary": at_boundary, "level_transition": level, "endpoint_gap_m": round(math.dist(before, after), 4)})
    rail_sides = {side: any(f"_roof_rail_{side}_" in part.name for part in assembly.parts) for side in ("west", "east", "north", "south")}
    blocked_entry = []
    for part in assembly.transformed_parts():
        if "_roof_rail_west_" not in part.name:
            continue
        low = tuple(min(vertex[axis] for vertex in part.vertices) for axis in range(3))
        high = tuple(max(vertex[axis] for vertex in part.vertices) for axis in range(3))
        if low[0] < entry[0] + 0.06 and entry[0] - 0.06 < high[0] and low[2] < entry[2] + float(route["clear_width"]) / 2 and entry[2] - float(route["clear_width"]) / 2 < high[2]:
            blocked_entry.append(part.name)
    slab_contact = abs(entry[0] - slab_min[0]) <= 0.01 and abs(entry[1] - slab_max[1]) <= 0.005 and slab_min[2] < entry[2] < slab_max[2]
    continuous = slab_contact and all(rail_sides.values()) and not blocked_entry and all(item["endpoints_within_mesh_footprint"] and item["endpoints_at_platform_boundary"] and item["level_transition"] for item in turn_clearance)
    return {
        "continuous": continuous,
        "endpoint_source": "emitted roof slab AABB and rail geometry",
        "roof_surface_y": round(slab_max[1], 5),
        "ramp_endpoint": [round(value, 5) for value in entry],
        "slab_contact": slab_contact,
        "maximum_flight_grade": round(max(abs(end[1] - start[1]) / math.hypot(end[0] - start[0], end[2] - start[2]) for start, end in resolved), 5),
        "guardrail_sides": rail_sides,
        "entry_gap_blockers": blocked_entry,
        "turn_landings": turn_clearance,
    }


def collision_parts(assemblies: list[Assembly]) -> list[tuple[str, str, tuple[float, float, float], tuple[float, float, float]]]:
    """Return visible wall, slab, pier and rail parts as exact transformed AABBs."""
    tokens = (
        "floor_slab", "room_floor", "room_", "wall_", "rear_wall", "roof_slab", "glazing", "door_leaf",
        "roof_rail", "roof_baluster", "front_door_lintel", "front_spandrel", "front_header", "loadbearing_pier", "buttress_foot",
    )
    colliders = []
    for assembly in assemblies:
        if assembly.kind not in {"district_building", "interior_room"}:
            continue
        for part in assembly.transformed_parts():
            if not any(token in part.name for token in tokens):
                continue
            minimum = tuple(min(vertex[axis] for vertex in part.vertices) for axis in range(3))
            maximum = tuple(max(vertex[axis] for vertex in part.vertices) for axis in range(3))
            if all(maximum[axis] - minimum[axis] > 1e-5 for axis in range(3)):
                colliders.append((assembly.name, part.name, minimum, maximum))
    return colliders
