"""Function-specific, editable static forms for the Tokyo Nova prop library."""
from __future__ import annotations

import math
from typing import Iterable

from modeling.tokyo_nova import geometry as geo
from modeling.tokyo_nova.props import Assembly

Vec3 = tuple[float, float, float]


def _box(parts: list[geo.MeshData], name: str, center: Vec3, size: Vec3, material: str, bevel: float = 0.0) -> None:
    parts.append(geo.beveled_box(name, center, size, min(bevel, min(size) * 0.35), material) if bevel else geo.box(name, center, size, material))


def _pipe(parts: list[geo.MeshData], name: str, start: Vec3, end: Vec3, radius: float, material: str = "exposed_metal") -> None:
    parts.append(geo.pipe(name, start, end, radius, material, segments=8))


def _cylinder(parts: list[geo.MeshData], name: str, center: Vec3, radius: float, depth: float, material: str = "exposed_metal", axis: Vec3 = (0.0, 1.0, 0.0), segments: int = 12) -> None:
    parts.append(geo.cylinder(name, center, radius, depth, material, segments=segments, axis=axis))


def _torus(name: str, center: Vec3, major: float, minor: float, material: str, axis: Vec3 = (0.0, 1.0, 0.0), segments: int = 20, sides: int = 6) -> geo.MeshData:
    length = math.sqrt(sum(value * value for value in axis))
    normal = tuple(value / length for value in axis)
    reference = (1.0, 0.0, 0.0) if abs(normal[0]) < 0.8 else (0.0, 0.0, 1.0)
    u0 = (normal[1] * reference[2] - normal[2] * reference[1], normal[2] * reference[0] - normal[0] * reference[2], normal[0] * reference[1] - normal[1] * reference[0])
    ulen = math.sqrt(sum(value * value for value in u0))
    u = tuple(value / ulen for value in u0)
    v = (normal[1] * u[2] - normal[2] * u[1], normal[2] * u[0] - normal[0] * u[2], normal[0] * u[1] - normal[1] * u[0])
    vertices: list[Vec3] = []
    faces: list[tuple[int, ...]] = []
    for ring in range(segments):
        theta = math.tau * ring / segments
        radial = tuple(math.cos(theta) * u[axis_index] + math.sin(theta) * v[axis_index] for axis_index in range(3))
        for side in range(sides):
            phi = math.tau * side / sides
            offset = tuple((major + minor * math.cos(phi)) * radial[axis_index] + minor * math.sin(phi) * normal[axis_index] for axis_index in range(3))
            vertices.append(tuple(center[axis_index] + offset[axis_index] for axis_index in range(3)))
    for ring in range(segments):
        next_ring = (ring + 1) % segments
        for side in range(sides):
            next_side = (side + 1) % sides
            a = ring * sides + side
            b = next_ring * sides + side
            c = next_ring * sides + next_side
            d = ring * sides + next_side
            faces.append((a, b, c, d))
    return geo.mesh(name, vertices, faces, material)


def _vessel(name: str, center: Vec3, radius: float, height: float, material: str, *, bowl: bool = False, segments: int = 16) -> geo.MeshData:
    """A wall-thickness vessel with an open mouth and visible inner floor."""
    if bowl:
        profile = ((0.08, radius * 0.43), (0.16, radius * 0.64), (0.40, radius * 0.94), (0.48, radius), (0.43, radius * 0.84), (0.27, radius * 0.58), (0.19, radius * 0.35))
    else:
        profile = ((0.04, radius * 0.78), (0.12, radius * 0.92), (height * 0.86, radius), (height, radius), (height - 0.045, radius * 0.86), (0.14, radius * 0.84), (0.12, radius * 0.52))
    vertices: list[Vec3] = []
    faces: list[tuple[int, ...]] = []
    for y_fraction, ring_radius in profile:
        y = center[1] + (y_fraction * height if not bowl else y_fraction * height / 0.48)
        for side in range(segments):
            angle = math.tau * side / segments
            vertices.append((center[0] + ring_radius * math.cos(angle), y, center[2] + ring_radius * math.sin(angle)))
    for ring in range(len(profile) - 1):
        for side in range(segments):
            a = ring * segments + side
            b = ring * segments + (side + 1) % segments
            c = (ring + 1) * segments + (side + 1) % segments
            d = (ring + 1) * segments + side
            faces.append((a, b, c, d))
    inner_bottom = (center[0], center[1] + (0.19 * height / 0.48 if bowl else 0.12), center[2])
    bottom_index = len(vertices)
    vertices.append(inner_bottom)
    first_inner = (len(profile) - 1) * segments
    for side in range(segments):
        faces.append((first_inner + side, first_inner + (side + 1) % segments, bottom_index))
    return geo.mesh(name, vertices, faces, material)


def _curtain(name: str, width: float, height: float, thickness: float, primary: str, secondary: str) -> list[geo.MeshData]:
    vertices: list[Vec3] = []
    faces: list[tuple[int, ...]] = []
    folds = 12
    for row, y in enumerate((0.0, height)):
        for fold in range(folds + 1):
            x = -width / 2 + width * fold / folds
            depth = thickness * (0.5 + 0.5 * math.cos(fold * math.pi)) + row * 0.003
            vertices.append((x, y, depth))
    for fold in range(folds):
        faces.append((fold, fold + 1, folds + 1 + fold + 1, folds + 1 + fold))
    parts = [geo.mesh(f"{name}_folded_fabric", vertices, faces, primary)]
    _pipe(parts, f"{name}_suspension_rail", (-width * 0.53, height + 0.06, 0.0), (width * 0.53, height + 0.06, 0.0), 0.02, secondary)
    for hook in range(5):
        x = -width * 0.42 + hook * width * 0.21
        parts.append(_torus(f"{name}_curtain_hook_{hook}", (x, height + 0.025, 0.0), 0.035, 0.008, secondary, axis=(1, 0, 0), segments=8, sides=4))
    return parts


def _open_tray(name: str, center: Vec3, width: float, height: float, depth: float, material: str, trim: str) -> list[geo.MeshData]:
    parts = [geo.box(f"{name}_bottom", center, (width, max(0.025, height * 0.12), depth), material)]
    wall = max(0.025, min(width, depth) * 0.07)
    y = center[1] + height / 2
    for side in (-1, 1):
        parts.append(geo.box(f"{name}_long_rim_{side}", (center[0], y, center[2] + side * (depth - wall) / 2), (width, height, wall), trim))
        parts.append(geo.box(f"{name}_short_rim_{side}", (center[0] + side * (width - wall) / 2, y, center[2]), (wall, height, max(0.01, depth - 2 * wall)), trim))
    return parts


def _blade(name: str, center: Vec3, radius: float, angle: float, thickness: float, material: str) -> geo.MeshData:
    inner = radius * 0.22
    outer = radius
    points = ((inner, -thickness), (outer * 0.70, -thickness * 1.8), (outer, thickness * 0.10), (outer * 0.55, thickness * 1.5), (inner, thickness))
    vertices = []
    for x, z in points:
        vertices.append((center[0] + x * math.cos(angle) - z * math.sin(angle), center[1], center[2] + x * math.sin(angle) + z * math.cos(angle)))
    return geo.mesh(name, vertices, ((0, 1, 2, 3, 4),), material)


def _frame_corners(parts: list[geo.MeshData], name: str, width: float, height: float, depth: float, material: str, y0: float = 0.0) -> None:
    for x in (-width / 2, width / 2):
        for z in (-depth / 2, depth / 2):
            _box(parts, f"{name}_leg_{x:+.2f}_{z:+.2f}", (x, y0 + height / 2, z), (0.055, height, 0.055), material)


def _make_parts(kind: str, sx: float, sy: float, sz: float, primary: str, secondary: str) -> list[geo.MeshData]:
    p: list[geo.MeshData] = []
    cx, cy, cz = 0.0, sy / 2, 0.0

    if kind in {"corrugated_shutter", "warehouse_roll_shutter"}:
        slats = 10 if kind == "corrugated_shutter" else 13
        for side in (-1, 1):
            _box(p, f"{kind}_guide_rail_{side}", (side * sx * 0.47, sy / 2, 0), (0.06, sy, 0.08), secondary)
        for row in range(slats):
            y = sy * (0.10 + row * 0.76 / slats)
            _box(p, f"{kind}_interlocking_slatted_leaf_{row}", (0, y, 0), (sx * 0.88, sy * 0.76 / slats * 0.82, sz * 0.48), primary, 0.012)
        _cylinder(p, f"{kind}_rolled_header_tube", (0, sy * 0.93, 0), sz * 0.35, sx * 0.96, secondary, axis=(1, 0, 0))
        _pipe(p, f"{kind}_pull_handle", (-sx * 0.12, sy * 0.04, -sz * 0.28), (sx * 0.12, sy * 0.04, -sz * 0.28), 0.018)
    elif kind == "supported_awning":
        vertices = ((-sx / 2, sy * 0.70, -sz / 2), (sx / 2, sy * 0.70, -sz / 2), (sx / 2, sy * 0.30, sz / 2), (-sx / 2, sy * 0.30, sz / 2))
        p.append(geo.mesh("supported_awning_sloped_canvas", vertices, ((0, 1, 2, 3),), primary))
        for side in (-1, 1):
            _pipe(p, f"supported_awning_wall_anchor_{side}", (side * sx * 0.42, sy * 0.67, -sz * 0.48), (side * sx * 0.42, sy * 0.67, -sz * 0.36), 0.025, secondary)
            _pipe(p, f"supported_awning_front_post_{side}", (side * sx * 0.42, 0.02, sz * 0.48), (side * sx * 0.42, sy * 0.30, sz * 0.48), 0.035, secondary)
            _pipe(p, f"supported_awning_diagonal_brace_{side}", (side * sx * 0.42, sy * 0.31, sz * 0.46), (side * sx * 0.30, sy * 0.66, -sz * 0.36), 0.018, secondary)
        for ridge in range(7):
            x = -sx * 0.45 + ridge * sx * 0.15
            _pipe(p, f"supported_awning_canvas_batten_{ridge}", (x, sy * 0.70, -sz * 0.49), (x, sy * 0.30, sz * 0.49), 0.008, secondary)
    elif kind == "window_frame":
        _box(p, "window_frame_left_jamb", (-sx * 0.46, cy, 0), (sx * 0.08, sy, sz), primary)
        _box(p, "window_frame_right_jamb", (sx * 0.46, cy, 0), (sx * 0.08, sy, sz), primary)
        _box(p, "window_frame_head", (0, sy * 0.46, 0), (sx * 0.84, sy * 0.08, sz), primary)
        _box(p, "window_frame_sill", (0, -sy * 0.46, 0), (sx * 0.92, sy * 0.08, sz * 1.25), secondary)
        _box(p, "window_frame_glass_pane", (0, cy, -sz * 0.08), (sx * 0.81, sy * 0.82, sz * 0.035), "glass")
        _box(p, "window_frame_vertical_mullion", (0, cy, -sz * 0.02), (0.035, sy * 0.82, sz * 0.045), secondary)
        _box(p, "window_frame_horizontal_mullion", (0, cy, -sz * 0.02), (sx * 0.81, 0.035, sz * 0.045), secondary)
    elif kind == "rain_gutter":
        length = sx
        half = sz * 0.44
        bottom = -sy * 0.30
        top = sy * 0.48
        verts = ((-length / 2, bottom, -half), (length / 2, bottom, -half), (-length / 2, top, -half), (length / 2, top, -half), (-length / 2, bottom, half), (length / 2, bottom, half), (-length / 2, top, half), (length / 2, top, half))
        faces = ((0, 1, 5, 4), (0, 2, 3, 1), (4, 5, 7, 6))
        p.append(geo.mesh("rain_gutter_open_trough", verts, faces, primary))
        for bracket in range(4):
            x = -sx * 0.42 + bracket * sx * 0.28
            _pipe(p, f"rain_gutter_saddle_bracket_{bracket}", (x, top, -half), (x, top + sy * 0.38, half), 0.014, secondary)
        _pipe(p, "rain_gutter_downspout_elbow", (sx * 0.48, bottom, half), (sx * 0.48, bottom - sy * 0.20, half), 0.025, secondary)
        _pipe(p, "rain_gutter_downpipe", (sx * 0.48, bottom - sy * 0.18, half), (sx * 0.48, -sy * 1.8, half), 0.022, primary)
    elif kind in {"ac_compressor", "wall_fan"}:
        fan_radius = min(sx, sy) * (0.27 if kind == "ac_compressor" else 0.36)
        _box(p, f"{kind}_isolated_mounting_chassis", (0, sy * 0.48, 0), (sx * 0.84, sy * 0.60, sz * 0.74), primary, 0.035)
        if kind == "ac_compressor":
            for side in (-1, 1):
                for row in range(7):
                    y = sy * (0.25 + row * 0.065)
                    _box(p, f"ac_compressor_condenser_grille_{side}_{row}", (side * sx * 0.43, y, 0), (0.025, 0.025, sz * 0.58), secondary)
                _box(p, f"ac_compressor_mounting_foot_{side}", (side * sx * 0.32, sy * 0.10, 0), (sx * 0.18, sy * 0.12, sz * 0.78), "rubber")
            p.append(_torus("ac_compressor_fan_guard_ring", (0, sy * 0.52, -sz * 0.43), fan_radius, 0.012, secondary, axis=(0, 0, 1)))
            fan_center = (0, sy * 0.52, -sz * 0.45)
            for blade in range(4):
                p.append(_blade(f"ac_compressor_fan_blade_{blade}", fan_center, fan_radius * 0.83, math.tau * blade / 4 + 0.22, 0.035, "exposed_metal"))
            for coil in range(3):
                _pipe(p, f"ac_compressor_refrigerant_line_{coil}", (-sx * 0.33, sy * 0.2 + coil * 0.09, sz * 0.4), (-sx * 0.42, sy * 0.25 + coil * 0.1, sz * 0.60), 0.014, "rust")
        else:
            _box(p, "wall_fan_wall_mounting_bracket", (0, sy * 0.5, sz * 0.38), (sx * 0.24, sy * 0.55, sz * 0.12), secondary)
            fan_center = (0, sy * 0.50, -sz * 0.35)
            p.append(_torus("wall_fan_circular_guard_ring", fan_center, fan_radius, 0.012, secondary, axis=(0, 0, 1)))
            for blade in range(3):
                p.append(_blade(f"wall_fan_fan_blade_{blade}", fan_center, fan_radius * 0.86, math.tau * blade / 3, 0.045, primary))
            for spoke in range(6):
                angle = math.tau * spoke / 6
                _pipe(p, f"wall_fan_guard_spoke_{spoke}", fan_center, (fan_center[0] + fan_radius * math.cos(angle), fan_center[1] + fan_radius * math.sin(angle), fan_center[2]), 0.007, secondary)
        _cylinder(p, f"{kind}_fan_hub", (0, sy * 0.50, -sz * 0.48), fan_radius * 0.17, 0.045, "rust", axis=(0, 0, 1))
    elif kind == "exhaust_duct":
        _cylinder(p, "exhaust_duct_vertical_tube", (0, sy * 0.50, 0), sz * 0.23, sy * 0.74, primary)
        _cylinder(p, "exhaust_duct_elbow_horizontal", (sx * 0.24, sy * 0.84, 0), sz * 0.20, sx * 0.54, primary, axis=(1, 0, 0))
        for side in (-1, 1):
            p.append(_torus(f"exhaust_duct_flange_{side}", (side * sx * 0.40, sy * 0.84, 0), sz * 0.21, 0.018, secondary, axis=(1, 0, 0), segments=12))
        _box(p, "exhaust_duct_mouth_guard", (sx * 0.48, sy * 0.84, 0), (0.04, sy * 0.22, sz * 0.32), secondary)
    elif kind == "power_meter":
        _box(p, "power_meter_weatherproof_back_case", (0, cy, 0), (sx * 0.82, sy * 0.90, sz * 0.65), primary, 0.025)
        p.append(_torus("power_meter_dial_bezel", (0, sy * 0.64, -sz * 0.36), min(sx, sy) * 0.24, 0.018, secondary, axis=(0, 0, 1)))
        _cylinder(p, "power_meter_glass_dial", (0, sy * 0.64, -sz * 0.37), min(sx, sy) * 0.225, 0.012, "glass", axis=(0, 0, 1))
        _pipe(p, "power_meter_needle", (0, sy * 0.64, -sz * 0.39), (sx * 0.12, sy * 0.72, -sz * 0.40), 0.009, "rust")
        for side in (-1, 1):
            _pipe(p, f"power_meter_cable_{side}", (side * sx * 0.36, sy * 0.10, sz * 0.27), (side * sx * 0.42, -sy * 0.18, sz * 0.47), 0.016, secondary)
        _box(p, "power_meter_inspection_seal", (sx * 0.22, sy * 0.22, -sz * 0.36), (sx * 0.22, sy * 0.07, 0.025), "warm_light")
    elif kind == "junction_panel":
        _box(p, "junction_panel_enclosure", (0, cy, 0), (sx * 0.94, sy * 0.94, sz * 0.72), primary, 0.025)
        _box(p, "junction_panel_hinged_door", (0, cy, -sz * 0.40), (sx * 0.82, sy * 0.86, 0.025), secondary)
        for fuse in range(4):
            x = -sx * 0.29 + fuse * sx * 0.19
            _cylinder(p, f"junction_panel_ceramic_fuse_{fuse}", (x, sy * 0.62, -sz * 0.43), 0.035, 0.08, "ceramic", axis=(0, 0, 1))
        for side in (-1, 1):
            _pipe(p, f"junction_panel_cable_gland_{side}", (side * sx * 0.34, sy * 0.10, 0), (side * sx * 0.52, -sy * 0.42, 0), 0.016, "rubber")
        _box(p, "junction_panel_latch", (sx * 0.36, cy, -sz * 0.45), (0.04, 0.12, 0.035), "rust")
    elif kind == "antenna_yagi":
        _pipe(p, "antenna_yagi_director_boom", (0, sy * 0.50, -sz * 0.46), (0, sy * 0.50, sz * 0.46), 0.016, primary)
        for element in range(5):
            z = -sz * 0.38 + element * sz * 0.19
            half = sx * (0.43 if element == 0 else 0.34)
            _pipe(p, f"antenna_yagi_radiator_{element}", (-half, sy * 0.5, z), (half, sy * 0.5, z), 0.012, secondary)
        _box(p, "antenna_yagi_mast_clamp", (0, sy * 0.50, 0), (sx * 0.22, sy * 0.14, sz * 0.23), "rust")
        _pipe(p, "antenna_yagi_mast", (0, 0, 0), (0, sy, 0), 0.022, secondary)
        _pipe(p, "antenna_yagi_coaxial_lead", (0, sy * 0.45, 0), (sx * 0.33, sy * 0.12, sz * 0.46), 0.008, "rubber")
    elif kind == "roof_tank_filter":
        p.append(_vessel("roof_tank_filter_open_canister", (0, 0, 0), min(sx, sz) * 0.38, sy * 0.82, primary))
        _cylinder(p, "roof_tank_filter_threaded_cap", (0, sy * 0.90, 0), min(sx, sz) * 0.40, 0.05, secondary)
        for side in (-1, 1):
            _pipe(p, f"roof_tank_filter_inlet_{side}", (side * sx * 0.32, sy * 0.28, 0), (side * sx * 0.56, sy * 0.28, 0), 0.025, "rust")
        p.append(_torus("roof_tank_filter_mounting_collar", (0, sy * 0.17, 0), min(sx, sz) * 0.40, 0.018, secondary))
        _cylinder(p, "roof_tank_filter_pressure_gauge", (0, sy * 0.75, -sz * 0.34), 0.07, 0.03, "glass", axis=(0, 0, 1))
    elif kind == "floor_drain":
        _box(p, "floor_drain_outer_frame", (0, cy, 0), (sx, sy, sz), secondary)
        _box(p, "floor_drain_recessed_sump", (0, -sy * 0.9, 0), (sx * 0.72, sy, sz * 0.72), primary)
        for bar in range(7):
            x = -sx * 0.36 + bar * sx * 0.12
            _box(p, f"floor_drain_separated_grate_bar_{bar}", (x, sy * 0.08, 0), (sx * 0.045, sy * 0.18, sz * 0.70), secondary)
        p.append(_torus("floor_drain_silt_ring", (0, -sy * 0.45, 0), sx * 0.15, 0.012, "rust"))
    elif kind in {"clinic_privacy_curtain", "welding_curtain"}:
        p.extend(_curtain(kind, sx, sy, sz, primary, secondary))
        _box(p, f"{kind}_weighted_hem", (0, 0.015, sz * 0.05), (sx * 0.87, 0.035, 0.025), secondary)
        if kind == "welding_curtain":
            for seam in range(5):
                x = -sx * 0.40 + seam * sx * 0.20
                _pipe(p, f"welding_curtain_reinforced_seam_{seam}", (x, 0.03, sz * 0.52), (x, sy * 0.95, sz * 0.52), 0.008, "rust")
    elif kind == "diagnostic_table":
        _box(p, "diagnostic_table_padded_top", (0, sy * 0.74, 0), (sx, sy * 0.13, sz * 0.82), primary, 0.04)
        _frame_corners(p, "diagnostic_table_tubular_base", sx * 0.82, sy * 0.62, sz * 0.72, secondary, sy * 0.05)
        _box(p, "diagnostic_table_instrument_shelf", (0, sy * 0.32, 0), (sx * 0.70, 0.045, sz * 0.60), secondary)
        _cylinder(p, "diagnostic_table_exam_paper_roll", (sx * 0.32, sy * 0.84, -sz * 0.28), 0.035, sz * 0.65, "cloth", axis=(0, 0, 1))
        _pipe(p, "diagnostic_table_paper_edge", (-sx * 0.40, sy * 0.84, 0), (sx * 0.40, sy * 0.84, 0), 0.012, "cream_plastic")
    elif kind == "joint_casing_set":
        for index, x in enumerate((-sx * 0.30, 0.0, sx * 0.30)):
            radius = min(sx, sz) * (0.22 if index != 1 else 0.28)
            p.append(_torus(f"joint_casing_bearing_housing_{index}", (x, sy * 0.50, 0), radius, 0.055, primary, axis=(1, 0, 0), segments=12))
            _cylinder(p, f"joint_casing_axle_{index}", (x, sy * 0.5, 0), radius * 0.48, 0.12, secondary, axis=(1, 0, 0))
            _pipe(p, f"joint_casing_hydraulic_link_{index}", (x, sy * 0.35, -sz * 0.20), (x, sy * 0.66, sz * 0.20), 0.018, "rust")
        _box(p, "joint_casing_shipping_cradle", (0, sy * 0.12, 0), (sx, sy * 0.12, sz * 0.86), secondary)
    elif kind == "instrument_trolley":
        _frame_corners(p, "instrument_trolley_frame", sx * 0.82, sy * 0.76, sz * 0.78, secondary, sy * 0.12)
        for deck in range(3):
            y = sy * (0.28 + deck * 0.28)
            _box(p, f"instrument_trolley_tray_deck_{deck}", (0, y, 0), (sx * 0.92, 0.055, sz * 0.88), primary, 0.015)
            _box(p, f"instrument_trolley_tray_lip_{deck}", (0, y + 0.045, -sz * 0.40), (sx * 0.80, 0.045, 0.025), secondary)
        for wheel in range(4):
            x = -sx * 0.36 if wheel < 2 else sx * 0.36
            z = -sz * 0.34 if wheel % 2 == 0 else sz * 0.34
            p.append(_torus(f"instrument_trolley_caster_wheel_{wheel}", (x, sy * 0.10, z), 0.045, 0.018, "rubber", axis=(1, 0, 0), segments=12))
            _pipe(p, f"instrument_trolley_caster_fork_{wheel}", (x, sy * 0.14, z), (x, sy * 0.10, z), 0.014, secondary)
        _pipe(p, "instrument_trolley_push_handle", (-sx * 0.38, sy * 0.88, -sz * 0.36), (sx * 0.38, sy * 0.88, -sz * 0.36), 0.018, secondary)
    elif kind == "medicine_drawer":
        _box(p, "medicine_drawer_outer_carcass", (0, cy, 0), (sx * 0.90, sy * 0.96, sz * 0.80), primary)
        for drawer in range(4):
            y = sy * (0.18 + drawer * 0.20)
            _box(p, f"medicine_drawer_front_{drawer}", (0, y, -sz * 0.42), (sx * 0.82, sy * 0.16, 0.035), secondary, 0.012)
            _pipe(p, f"medicine_drawer_pull_{drawer}", (-sx * 0.10, y, -sz * 0.46), (sx * 0.10, y, -sz * 0.46), 0.012, "exposed_metal")
            _box(p, f"medicine_drawer_label_tab_{drawer}", (sx * 0.29, y, -sz * 0.46), (sx * 0.15, 0.055, 0.02), "cream_plastic")
        for side in (-1, 1):
            _box(p, f"medicine_drawer_base_foot_{side}", (side * sx * 0.30, sy * 0.04, 0), (0.06, 0.08, sz * 0.50), secondary)
    elif kind in {"exam_task_lamp", "repair_lamp"}:
        _box(p, f"{kind}_weighted_base", (0, sy * 0.06, 0), (sx * 0.52, sy * 0.12, sz * 0.52), primary, 0.04)
        _pipe(p, f"{kind}_lower_articulated_arm", (0, sy * 0.12, 0), (sx * 0.15, sy * 0.55, 0), 0.022, secondary)
        p.append(_torus(f"{kind}_hinge_joint", (sx * 0.15, sy * 0.55, 0), 0.055, 0.018, secondary, axis=(0, 0, 1), segments=12))
        _pipe(p, f"{kind}_upper_articulated_arm", (sx * 0.15, sy * 0.55, 0), (sx * 0.34, sy * 0.82, 0), 0.018, secondary)
        _cylinder(p, f"{kind}_reflector_shade", (sx * 0.36, sy * 0.84, 0), min(sx, sz) * 0.25, 0.11, secondary, axis=(1, 0, 0))
        _cylinder(p, f"{kind}_diffuser", (sx * 0.36, sy * 0.84, -0.05), min(sx, sz) * 0.19, 0.015, "warm_light", axis=(1, 0, 0))
        _pipe(p, f"{kind}_power_lead", (-sx * 0.20, sy * 0.10, sz * 0.22), (sx * 0.10, sy * 0.22, sz * 0.30), 0.008, "rubber")
    elif kind == "tray_of_tools":
        p.extend(_open_tray("tray_of_tools_open_rim", (0, sy * 0.25, 0), sx, sy * 0.45, sz, primary, secondary))
        for tool in range(5):
            x = -sx * 0.35 + tool * sx * 0.17
            _pipe(p, f"tray_of_tools_screwdriver_shaft_{tool}", (x, sy * 0.36, -sz * 0.34), (x + sx * 0.06, sy * 0.75, sz * 0.26), 0.012, secondary)
            _cylinder(p, f"tray_of_tools_handle_{tool}", (x, sy * 0.79, sz * 0.31), 0.026, 0.12, "rubber")
    elif kind == "street_bowl_rack":
        for side in (-1, 1):
            _box(p, f"street_bowl_rack_upright_{side}", (side * sx * 0.43, sy * 0.50, 0), (0.05, sy, 0.07), primary)
        for deck in range(2):
            y = sy * (0.30 + deck * 0.43)
            _box(p, f"street_bowl_rack_shelf_{deck}", (0, y, 0), (sx * 0.90, 0.045, sz * 0.84), primary)
            for bowl in range(3):
                x = -sx * 0.30 + bowl * sx * 0.30
                p.append(_vessel(f"street_bowl_rack_hollow_bowl_{deck}_{bowl}", (x, y + 0.03, 0), min(sx, sz) * 0.16, 0.13, "ceramic", bowl=True, segments=12))
        for divider in (-1, 1):
            _box(p, f"street_bowl_rack_divider_{divider}", (divider * sx * 0.18, sy * 0.68, 0), (0.025, sy * 0.28, sz * 0.76), secondary)
    elif kind in {"lidded_stockpot", "cfc_food_canister", "laundry_bucket", "detergent_canister", "shared_kitchen_kettle"}:
        radius = min(sx, sz) * (0.44 if kind != "detergent_canister" else 0.40)
        body_height = sy * (0.75 if kind in {"lidded_stockpot", "laundry_bucket"} else 0.80)
        p.append(_vessel(f"{kind}_hollow_vessel", (0, 0, 0), radius, body_height, primary, bowl=kind == "lidded_stockpot"))
        p.append(_torus(f"{kind}_rolled_open_mouth_rim", (0, body_height, 0), radius * 0.93, 0.018, secondary))
        if kind == "lidded_stockpot":
            _cylinder(p, "lidded_stockpot_loose_lid", (0, body_height + 0.055, 0), radius * 0.91, 0.035, secondary)
            _cylinder(p, "lidded_stockpot_lid_knob", (0, body_height + 0.095, 0), 0.045, 0.05, "rubber")
            for side in (-1, 1):
                _pipe(p, f"lidded_stockpot_wire_handle_{side}", (side * radius, body_height * 0.55, 0), (side * radius * 1.38, body_height * 0.55, 0), 0.018, secondary)
        elif kind == "laundry_bucket":
            p.append(_torus("laundry_bucket_bail_handle", (0, sy * 0.92, 0), radius * 1.2, 0.014, secondary, axis=(1, 0, 0)))
            p.append(_torus("laundry_bucket_base_rib", (0, sy * 0.12, 0), radius * 0.82, 0.018, secondary))
        elif kind == "cfc_food_canister":
            _box(p, "cfc_food_canister_return_label", (0, sy * 0.56, -radius * 0.98), (radius * 1.2, sy * 0.18, 0.018), "faded_teal")
            _pipe(p, "cfc_food_canister_hinged_carry_handle", (-radius * 0.75, sy * 0.92, 0), (radius * 0.75, sy * 0.92, 0), 0.018, secondary)
            _box(p, "cfc_food_canister_reusable_seal_latch", (radius * 0.84, body_height * 0.88, -0.01), (0.035, 0.085, 0.03), "rust")
        elif kind == "detergent_canister":
            _box(p, "detergent_canister_integrated_grip", (radius * 0.45, sy * 0.87, 0), (radius * 0.54, sy * 0.17, radius * 0.30), primary, 0.04)
            _cylinder(p, "detergent_canister_pour_neck", (-radius * 0.12, sy * 0.94, 0), radius * 0.33, sy * 0.16, secondary)
            _cylinder(p, "detergent_canister_cap", (-radius * 0.12, sy * 1.035, 0), radius * 0.35, 0.035, "faded_teal")
        elif kind == "shared_kitchen_kettle":
            _pipe(p, "shared_kitchen_kettle_spout", (radius * 0.72, sy * 0.62, 0), (radius * 1.35, sy * 0.82, 0), 0.055, secondary)
            p.append(_torus("shared_kitchen_kettle_handle", (0, sy * 0.95, 0), radius * 0.70, 0.028, secondary, axis=(1, 0, 0)))
            _cylinder(p, "shared_kitchen_kettle_lid", (0, body_height * 1.01, 0), radius * 0.80, 0.03, secondary)
    elif kind == "cfc_food_canister":
        pass
    elif kind == "reuse_container_stack":
        for row in range(3):
            y = sy * (0.20 + row * 0.27)
            x = (row % 2) * sx * 0.16
            p.extend(_open_tray(f"reuse_container_stack_open_tub_{row}", (x, y, 0), sx * 0.76, sy * 0.26, sz * 0.80, primary, secondary))
            _box(p, f"reuse_container_stack_lid_gasket_{row}", (x, y + sy * 0.14, 0), (sx * 0.80, 0.018, sz * 0.84), "rubber")
    elif kind == "under_counter_fridge":
        _box(p, "under_counter_fridge_insulated_cabinet", (0, cy, 0), (sx * 0.94, sy * 0.88, sz * 0.88), primary, 0.045)
        _box(p, "under_counter_fridge_hinged_door", (0, cy, -sz * 0.46), (sx * 0.82, sy * 0.70, 0.035), secondary, 0.02)
        _pipe(p, "under_counter_fridge_handle", (sx * 0.35, sy * 0.60, -sz * 0.49), (sx * 0.35, sy * 0.78, -sz * 0.49), 0.015)
        for vent in range(6):
            _box(p, f"under_counter_fridge_condenser_vent_{vent}", (0, sy * (0.12 + vent * 0.035), -sz * 0.49), (sx * 0.48, 0.012, 0.012), "rubber")
        for side in (-1, 1):
            _box(p, f"under_counter_fridge_leveling_foot_{side}", (side * sx * 0.35, sy * 0.04, sz * 0.30), (0.07, sy * 0.08, 0.07), secondary)
    elif kind == "chopstick_caddy":
        p.append(_vessel("chopstick_caddy_open_holder", (0, 0, 0), sx * 0.38, sy * 0.70, primary))
        for stick in range(9):
            angle = math.tau * stick / 9
            x = sx * 0.16 * math.cos(angle)
            z = sz * 0.16 * math.sin(angle)
            _pipe(p, f"chopstick_caddy_visible_chopstick_{stick}", (x, sy * 0.45, z), (x * 1.4, sy * (0.77 + (stick % 3) * 0.04), z * 1.4), 0.008, secondary)
    elif kind == "condiment_set":
        p.extend(_open_tray("condiment_set_recessed_carrier", (0, sy * 0.08, 0), sx, sy * 0.18, sz, primary, secondary))
        for bottle in range(3):
            x = -sx * 0.30 + bottle * sx * 0.30
            _cylinder(p, f"condiment_set_sauce_bottle_{bottle}", (x, sy * 0.52, 0), sx * 0.09, sy * 0.52, "plastic")
            _cylinder(p, f"condiment_set_pour_cap_{bottle}", (x, sy * 0.82, 0), sx * 0.10, sy * 0.10, secondary)
            _cylinder(p, f"condiment_set_nozzle_{bottle}", (x, sy * 0.91, 0), 0.018, sy * 0.08, "rubber")
        p.append(_vessel("condiment_set_open_sauce_dish", (sx * 0.35, sy * 0.18, 0), sx * 0.10, sy * 0.22, "ceramic", bowl=True, segments=12))
    elif kind == "wash_sink":
        top_y = sy * 0.77
        _box(p, "wash_sink_left_counter_wing", (-sx * 0.33, top_y, 0), (sx * 0.34, sy * 0.10, sz), primary)
        _box(p, "wash_sink_right_counter_wing", (sx * 0.33, top_y, 0), (sx * 0.34, sy * 0.10, sz), primary)
        _box(p, "wash_sink_front_counter_rail", (0, top_y, sz * 0.43), (sx * 0.34, sy * 0.10, sz * 0.14), primary)
        _box(p, "wash_sink_back_counter_rail", (0, top_y, -sz * 0.43), (sx * 0.34, sy * 0.10, sz * 0.14), primary)
        p.append(_vessel("wash_sink_open_sink_bowl", (0, sy * 0.51, 0), min(sx, sz) * 0.24, sy * 0.55, secondary, bowl=True))
        p.append(_torus("wash_sink_drain_ring", (0, sy * 0.20, 0), min(sx, sz) * 0.07, 0.012, "exposed_metal"))
        _pipe(p, "wash_sink_faucet_spout", (-sx * 0.22, sy * 0.87, -sz * 0.30), (0, sy * 0.83, -sz * 0.12), 0.018, secondary)
        for side in (-1, 1):
            _pipe(p, f"wash_sink_tap_{side}", (side * sx * 0.24, sy * 0.78, -sz * 0.30), (side * sx * 0.24, sy * 0.68, -sz * 0.30), 0.014, "rust")
            _box(p, f"wash_sink_support_leg_{side}", (side * sx * 0.38, sy * 0.37, 0), (0.06, sy * 0.70, 0.06), secondary)
    elif kind == "serving_counter":
        _box(p, "serving_counter_stone_top", (0, sy * 0.83, 0), (sx, sy * 0.12, sz), primary)
        for side in (-1, 1):
            _box(p, f"serving_counter_end_support_{side}", (side * sx * 0.43, sy * 0.43, 0), (sx * 0.12, sy * 0.78, sz * 0.82), secondary)
        _box(p, "serving_counter_access_shelf", (0, sy * 0.35, 0), (sx * 0.78, 0.06, sz * 0.72), primary)
        _box(p, "serving_counter_customer_foot_rail", (0, sy * 0.11, sz * 0.50), (sx * 0.92, 0.035, 0.035), secondary)
        for drawer in range(2):
            x = -sx * 0.22 + drawer * sx * 0.44
            _box(p, f"serving_counter_cash_drawer_{drawer}", (x, sy * 0.68, -sz * 0.46), (sx * 0.34, sy * 0.14, 0.025), secondary)
            _pipe(p, f"serving_counter_drawer_pull_{drawer}", (x - 0.06, sy * 0.68, -sz * 0.50), (x + 0.06, sy * 0.68, -sz * 0.50), 0.012)
    elif kind == "slip_on_shoes":
        for shoe in range(2):
            x = -sx * 0.24 + shoe * sx * 0.48
            z = (shoe - 0.5) * sz * 0.30
            _box(p, f"slip_on_shoes_rubber_sole_{shoe}", (x, sy * 0.12, z), (sx * 0.62, sy * 0.16, sz * 0.76), "rubber", 0.035)
            vertices = ((x - sx * 0.27, sy * 0.18, z - sz * 0.30), (x + sx * 0.27, sy * 0.18, z - sz * 0.30), (x + sx * 0.22, sy * 0.75, z + sz * 0.28), (x - sx * 0.22, sy * 0.75, z + sz * 0.28), (x, sy * 0.88, z + sz * 0.36))
            p.append(geo.mesh(f"slip_on_shoes_stitched_upper_{shoe}", vertices, ((0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)), primary))
            _pipe(p, f"slip_on_shoes_opening_binding_{shoe}", (x - sx * 0.12, sy * 0.58, z + sz * 0.25), (x + sx * 0.12, sy * 0.58, z + sz * 0.25), 0.012, secondary)
    elif kind == "folded_umbrella":
        _pipe(p, "folded_umbrella_steel_shaft", (0, 0, 0), (0, sy * 0.88, 0), 0.018, secondary)
        for panel in range(6):
            angle = math.tau * panel / 6
            x = math.cos(angle)
            z = math.sin(angle)
            _pipe(p, f"folded_umbrella_collapsed_rib_{panel}", (0, sy * 0.83, 0), (x * sx * 0.40, sy * 0.22, z * sz * 0.40), 0.012, secondary)
            _pipe(p, f"folded_umbrella_gathered_cloth_{panel}", (x * sx * 0.12, sy * 0.75, z * sz * 0.12), (x * sx * 0.38, sy * 0.27, z * sz * 0.38), 0.035, primary)
        _pipe(p, "folded_umbrella_hook_handle", (0, sy * 0.08, 0), (sx * 0.24, sy * 0.04, 0), 0.025, secondary)
        p.append(_torus("folded_umbrella_retaining_strap", (0, sy * 0.55, 0), sx * 0.32, 0.012, "rubber"))
    elif kind == "laundry_wringer":
        p.extend(_open_tray("laundry_wringer_wash_tub", (0, sy * 0.20, 0), sx * 0.92, sy * 0.38, sz * 0.86, primary, secondary))
        for side in (-1, 1):
            _pipe(p, f"laundry_wringer_press_upright_{side}", (side * sx * 0.36, sy * 0.38, 0), (side * sx * 0.36, sy * 0.96, 0), 0.028, secondary)
        for roller in (-1, 1):
            _cylinder(p, f"laundry_wringer_opposed_pressure_roller_{roller}", (0, sy * 0.80, roller * sz * 0.10), sz * 0.13, sx * 0.82, "rubber", axis=(1, 0, 0))
        _pipe(p, "laundry_wringer_crank_arm", (sx * 0.46, sy * 0.84, 0), (sx * 0.58, sy * 0.68, 0), 0.018, secondary)
        _cylinder(p, "laundry_wringer_crank_grip", (sx * 0.58, sy * 0.68, 0), 0.025, 0.11, "rubber", axis=(1, 0, 0))
    elif kind == "clothes_hanger":
        hook_center = (0.0, sy * 0.90, 0.0)
        p.append(_torus("clothes_hanger_hook", hook_center, sy * 0.065, 0.010, secondary, axis=(1, 0, 0), segments=10, sides=4))
        _pipe(p, "clothes_hanger_hook_neck", (0, sy * 0.85, 0), (0, sy * 0.76, 0), 0.010, secondary)
        _pipe(p, "clothes_hanger_left_shoulder", (0, sy * 0.76, 0), (-sx * 0.48, sy * 0.12, 0), 0.012, secondary)
        _pipe(p, "clothes_hanger_right_shoulder", (0, sy * 0.76, 0), (sx * 0.48, sy * 0.12, 0), 0.012, secondary)
        _pipe(p, "clothes_hanger_bar", (-sx * 0.48, sy * 0.12, 0), (sx * 0.48, sy * 0.12, 0), 0.012, secondary)
        _pipe(p, "clothes_hanger_repair_wrap", (-sx * 0.20, sy * 0.14, 0.015), (sx * 0.20, sy * 0.14, 0.015), 0.007, "rust")
    elif kind == "patched_clothes_bundle":
        for layer in range(4):
            y = sy * (0.16 + layer * 0.16)
            x = (layer % 2) * sx * 0.12
            _box(p, f"patched_clothes_bundle_folded_cloth_{layer}", (x, y, 0), (sx * (0.82 - layer * 0.08), sy * 0.17, sz * (0.86 - layer * 0.06)), primary, 0.02)
            if layer % 2 == 0:
                _box(p, f"patched_clothes_bundle_repair_patch_{layer}", (x + sx * 0.18, y + sy * 0.09, sz * 0.20), (sx * 0.22, sy * 0.012, sz * 0.19), secondary)
        _pipe(p, "patched_clothes_bundle_tie_cord", (-sx * 0.43, sy * 0.55, -sz * 0.48), (sx * 0.43, sy * 0.55, -sz * 0.48), 0.012, "rust")
    elif kind == "rolled_bedding":
        for roll in range(2):
            z = -sz * 0.24 + roll * sz * 0.48
            _cylinder(p, f"rolled_bedding_quilt_roll_{roll}", (0, sy * 0.35, z), sy * 0.31, sx * 0.90, primary, axis=(1, 0, 0), segments=16)
            for strap in (-1, 1):
                p.append(_torus(f"rolled_bedding_buckle_strap_{roll}_{strap}", (strap * sx * 0.24, sy * 0.35, z), sy * 0.31, 0.018, secondary, axis=(1, 0, 0), segments=16))
        _box(p, "rolled_bedding_patched_outer_fold", (0, sy * 0.88, 0), (sx * 0.48, sy * 0.07, sz * 0.38), "faded_teal", 0.025)
    elif kind == "shared_mailboxes":
        _box(p, "shared_mailboxes_backframe", (0, cy, sz * 0.36), (sx, sy, 0.08), primary)
        for row in range(3):
            for col in range(3):
                x = (col - 1) * sx * 0.31
                y = sy * (0.18 + row * 0.29)
                _box(p, f"shared_mailboxes_individual_cubby_{row}_{col}", (x, y, 0), (sx * 0.28, sy * 0.27, sz * 0.58), primary)
                _box(p, f"shared_mailboxes_hinged_door_{row}_{col}", (x, y, -sz * 0.31), (sx * 0.25, sy * 0.22, 0.025), secondary)
                _box(p, f"shared_mailboxes_address_slot_{row}_{col}", (x, y + sy * 0.04, -sz * 0.33), (sx * 0.12, 0.025, 0.01), "cream_plastic")
                _cylinder(p, f"shared_mailboxes_cam_lock_{row}_{col}", (x + sx * 0.09, y, -sz * 0.34), 0.016, 0.014, "rust", axis=(0, 0, 1), segments=8)
    elif kind == "stacked_textbooks":
        for book in range(4):
            x = (book % 2) * sx * 0.20
            y = sy * (0.15 + (book // 2) * 0.31)
            angle = (book - 1.5) * 0.035
            _box(p, f"stacked_textbooks_page_block_{book}", (x, y, 0), (sx * 0.78, sy * 0.23, sz * 0.70), "cream_plastic", 0.012)
            _box(p, f"stacked_textbooks_hard_cover_{book}", (x, y + sy * 0.13, 0), (sx * 0.84, 0.035, sz * 0.76), primary)
            _box(p, f"stacked_textbooks_title_label_{book}", (x, y + sy * 0.15, -sz * 0.20), (sx * 0.36, 0.012, sz * 0.04), secondary)
            _pipe(p, f"stacked_textbooks_spine_{book}", (x - sx * 0.40, y + sy * 0.12, -sz * 0.30), (x - sx * 0.40, y + sy * 0.12, sz * 0.30), 0.012, "rust")
    elif kind == "repair_chair" or kind == "classroom_chair":
        _box(p, f"{kind}_seat_board", (0, sy * 0.49, 0), (sx * 0.82, sy * 0.10, sz * 0.78), primary, 0.025)
        _box(p, f"{kind}_back_slat", (0, sy * 0.76, -sz * 0.34), (sx * 0.80, sy * 0.42, sz * 0.10), secondary)
        for side in (-1, 1):
            _box(p, f"{kind}_front_leg_{side}", (side * sx * 0.34, sy * 0.25, sz * 0.28), (0.045, sy * 0.50, 0.045), secondary)
            _box(p, f"{kind}_rear_leg_{side}", (side * sx * 0.34, sy * 0.31, -sz * 0.30), (0.045, sy * 0.62, 0.045), secondary)
            _pipe(p, f"{kind}_side_brace_{side}", (side * sx * 0.34, sy * 0.33, -sz * 0.30), (side * sx * 0.34, sy * 0.40, sz * 0.28), 0.018, "rust")
        _box(p, f"{kind}_rear_crossbar", (0, sy * 0.32, -sz * 0.31), (sx * 0.72, 0.045, 0.045), secondary)
    elif kind == "sewing_tool_roll":
        _box(p, "sewing_tool_roll_unrolled_canvas", (0, sy * 0.10, 0), (sx, sy * 0.10, sz * 0.84), primary)
        for tool in range(6):
            x = -sx * 0.40 + tool * sx * 0.16
            _box(p, f"sewing_tool_roll_individual_pocket_{tool}", (x, sy * 0.20, -sz * 0.27), (sx * 0.12, sy * 0.18, sz * 0.30), secondary)
            _pipe(p, f"sewing_tool_roll_tool_handle_{tool}", (x, sy * 0.25, -sz * 0.32), (x + sx * 0.04, sy * 0.65, sz * 0.18), 0.012, "exposed_metal")
        _pipe(p, "sewing_tool_roll_tie_left", (-sx * 0.48, sy * 0.16, sz * 0.40), (-sx * 0.35, sy * 0.18, sz * 0.48), 0.008, "rust")
        _pipe(p, "sewing_tool_roll_tie_right", (sx * 0.35, sy * 0.18, sz * 0.48), (sx * 0.48, sy * 0.16, sz * 0.40), 0.008, "rust")
    elif kind == "wooden_pallet":
        for board in range(7):
            z = -sz * 0.44 + board * sz * 0.145
            _box(p, f"wooden_pallet_deck_board_{board}", (0, sy * 0.63, z), (sx, sy * 0.22, sz * 0.12), primary)
            _box(p, f"wooden_pallet_cross_runner_{board}", (0, sy * 0.30, z), (sx * 0.88, sy * 0.35, sz * 0.065), secondary)
        for block in (-1, 0, 1):
            _box(p, f"wooden_pallet_fork_entry_block_{block}", (block * sx * 0.39, sy * 0.28, 0), (sx * 0.14, sy * 0.36, sz * 0.84), primary)
    elif kind in {"shipping_crate", "warehouse_strapped_crates"}:
        count = 2 if kind == "warehouse_strapped_crates" else 1
        for crate in range(count):
            ox = (crate - (count - 1) / 2) * sx * 0.50
            w = sx * (0.48 if count == 2 else 0.90)
            h = sy * (0.54 if count == 2 else 0.90)
            _box(p, f"{kind}_open_crate_base_{crate}", (ox, sy * 0.05 + crate * sy * 0.5, 0), (w, sy * 0.08, sz * 0.83), primary)
            for side in (-1, 1):
                _box(p, f"{kind}_slatted_long_side_{crate}_{side}", (ox, sy * 0.5 + crate * sy * 0.5, side * sz * 0.40), (w, h, 0.045), primary)
                for row in range(3):
                    _box(p, f"{kind}_separated_slats_{crate}_{side}_{row}", (ox, sy * (0.28 + row * 0.18) + crate * sy * 0.5, side * sz * 0.43), (w * 0.94, h * 0.12, 0.045), secondary)
            for side in (-1, 1):
                _box(p, f"{kind}_end_stave_{crate}_{side}", (ox + side * w * 0.47, sy * 0.5 + crate * sy * 0.5, 0), (0.045, h, sz * 0.80), secondary)
            if kind == "warehouse_strapped_crates":
                _box(p, f"warehouse_strapped_crates_tension_band_{crate}", (ox, sy * (0.50 + crate * 0.5), -sz * 0.46), (0.055, h * 0.92, 0.025), "faded_teal")
    elif kind == "ratchet_strap":
        for band in range(2):
            z = -sz * 0.27 + band * sz * 0.54
            _pipe(p, f"ratchet_strap_load_belt_{band}_upper", (-sx * 0.46, sy * 0.55, z), (sx * 0.46, sy * 0.55, z), max(0.012, sx * 0.11), primary)
            _pipe(p, f"ratchet_strap_load_belt_{band}_return", (sx * 0.46, sy * 0.55, z), (sx * 0.46, sy * 0.18, z), max(0.012, sx * 0.11), primary)
        _box(p, "ratchet_strap_winch_plate", (0, sy * 0.53, 0), (sx * 0.30, sy * 0.18, sz * 0.25), secondary)
        _pipe(p, "ratchet_strap_winch_handle", (-sx * 0.42, sy * 0.63, 0), (sx * 0.42, sy * 0.63, 0), 0.016, secondary)
        for side in (-1, 1):
            p.append(_torus(f"ratchet_strap_anchor_hook_{side}", (side * sx * 0.46, sy * 0.18, 0), 0.045, 0.012, secondary, axis=(1, 0, 0), segments=10))
    elif kind == "folding_dolly":
        _box(p, "folding_dolly_load_toe_plate", (0, sy * 0.08, sz * 0.25), (sx * 0.92, sy * 0.10, sz * 0.42), secondary)
        for side in (-1, 1):
            _pipe(p, f"folding_dolly_main_tube_{side}", (side * sx * 0.38, sy * 0.12, sz * 0.36), (side * sx * 0.38, sy * 0.92, -sz * 0.30), 0.028, primary)
            _pipe(p, f"folding_dolly_crossbrace_{side}", (side * sx * 0.38, sy * 0.52, -sz * 0.12), (-side * sx * 0.38, sy * 0.52, -sz * 0.12), 0.022, secondary)
            p.append(_torus(f"folding_dolly_tire_{side}", (side * sx * 0.40, sy * 0.13, -sz * 0.32), sy * 0.13, 0.025, "rubber", axis=(1, 0, 0), segments=16))
            _cylinder(p, f"folding_dolly_wheel_hub_{side}", (side * sx * 0.40, sy * 0.13, -sz * 0.32), sy * 0.055, 0.045, secondary, axis=(1, 0, 0))
    elif kind == "chain_hoist":
        _box(p, "chain_hoist_upper_trolley", (0, sy * 0.88, 0), (sx * 0.88, sy * 0.18, sz * 0.72), primary, 0.035)
        for wheel in (-1, 1):
            p.append(_torus(f"chain_hoist_trolley_wheel_{wheel}", (wheel * sx * 0.38, sy * 0.95, 0), sz * 0.18, 0.024, secondary, axis=(1, 0, 0), segments=12))
        for link in range(8):
            y = sy * (0.75 - link * 0.075)
            p.append(_torus(f"chain_hoist_chain_link_{link}", (0, y, 0), 0.032, 0.009, "rust", axis=(1, 0, 0) if link % 2 else (0, 0, 1), segments=8, sides=4))
        _cylinder(p, "chain_hoist_load_sheave", (0, sy * 0.31, 0), sx * 0.18, sz * 0.24, secondary, axis=(1, 0, 0))
        _pipe(p, "chain_hoist_hook_neck", (0, sy * 0.20, 0), (0, sy * 0.11, 0), 0.018, secondary)
        p.append(_torus("chain_hoist_load_hook", (0, sy * 0.07, 0), 0.06, 0.018, secondary, axis=(1, 0, 0), segments=12, sides=5))
        _pipe(p, "chain_hoist_hook_tip", (0.05, sy * 0.08, 0), (0.02, sy * 0.16, 0), 0.012, secondary)
    elif kind == "motorcycle_static":
        wheel_y = sy * 0.23
        for index, x in enumerate((-sx * 0.37, sx * 0.37)):
            p.append(_torus(f"motorcycle_static_tire_torus_{index}", (x, wheel_y, 0), sy * 0.22, sy * 0.055, "rubber", axis=(1, 0, 0), segments=20, sides=8))
            p.append(_torus(f"motorcycle_static_rim_ring_{index}", (x, wheel_y, 0), sy * 0.16, 0.018, secondary, axis=(1, 0, 0), segments=16))
            _cylinder(p, f"motorcycle_static_wheel_hub_{index}", (x, wheel_y, 0), sy * 0.055, 0.18, secondary, axis=(1, 0, 0))
            for spoke in range(8):
                angle = math.tau * spoke / 8
                _pipe(p, f"motorcycle_static_spoke_{index}_{spoke}", (x, wheel_y, 0), (x, wheel_y + sy * 0.16 * math.sin(angle), sy * 0.16 * math.cos(angle)), 0.006, secondary)
        _pipe(p, "motorcycle_static_lower_frame", (-sx * 0.35, wheel_y, 0), (sx * 0.12, sy * 0.46, 0), 0.028, secondary)
        _pipe(p, "motorcycle_static_upper_frame", (-sx * 0.30, sy * 0.46, 0), (sx * 0.20, sy * 0.39, 0), 0.024, secondary)
        _pipe(p, "motorcycle_static_front_fork", (sx * 0.35, wheel_y, 0), (sx * 0.29, sy * 0.70, 0), 0.022, secondary)
        _box(p, "motorcycle_static_engine_case", (0, sy * 0.39, 0), (sx * 0.27, sy * 0.29, sz * 0.52), "exposed_metal", 0.035)
        for fin in range(4):
            _box(p, f"motorcycle_static_cylinder_fin_{fin}", (0, sy * (0.34 + fin * 0.045), -sz * 0.29), (sx * 0.34, 0.018, 0.025), secondary)
        _box(p, "motorcycle_static_fuel_tank", (sx * 0.08, sy * 0.67, 0), (sx * 0.32, sy * 0.25, sz * 0.40), primary, 0.06)
        _box(p, "motorcycle_static_saddle", (-sx * 0.12, sy * 0.77, 0), (sx * 0.40, sy * 0.10, sz * 0.32), "rubber", 0.035)
        _pipe(p, "motorcycle_static_handlebar", (sx * 0.29, sy * 0.77, -sz * 0.28), (sx * 0.29, sy * 0.77, sz * 0.28), 0.016, secondary)
        _pipe(p, "motorcycle_static_exhaust", (-sx * 0.04, sy * 0.30, -sz * 0.34), (-sx * 0.40, sy * 0.34, -sz * 0.34), 0.025, "rust")
        _box(p, "motorcycle_static_opened_side_cowl", (-sx * 0.23, sy * 0.48, -sz * 0.31), (sx * 0.23, sy * 0.19, 0.025), primary)
    elif kind == "engine_case_half":
        _box(p, "engine_case_split_casting_half", (0, cy, 0), (sx * 0.90, sy * 0.77, sz * 0.72), primary, 0.045)
        p.append(_torus("engine_case_open_crank_bore", (0, sy * 0.46, -sz * 0.39), sy * 0.20, 0.035, secondary, axis=(0, 0, 1), segments=16))
        p.append(_torus("engine_case_bolt_rim", (0, sy * 0.46, -sz * 0.41), sy * 0.27, 0.018, "rust", axis=(0, 0, 1), segments=16))
        for rib in range(5):
            x = -sx * 0.36 + rib * sx * 0.18
            _box(p, f"engine_case_casting_rib_{rib}", (x, sy * 0.5, -sz * 0.38), (0.025, sy * 0.55, 0.035), secondary)
        for bolt in range(6):
            angle = math.tau * bolt / 6
            _cylinder(p, f"engine_case_perimeter_fastener_{bolt}", (sy * 0.31 * math.cos(angle), sy * (0.46 + 0.31 * math.sin(angle)), -sz * 0.42), 0.018, 0.02, "rust", axis=(0, 0, 1), segments=8)
    elif kind == "wheel_and_hub":
        p.append(_torus("wheel_and_hub_pneumatic_tire", (0, cy, 0), min(sx, sy) * 0.38, min(sx, sy) * 0.09, "rubber", axis=(0, 0, 1), segments=24, sides=8))
        p.append(_torus("wheel_and_hub_inner_rim", (0, cy, 0.02), min(sx, sy) * 0.28, 0.024, secondary, axis=(0, 0, 1), segments=20))
        _cylinder(p, "wheel_and_hub_bearing", (0, cy, 0.03), min(sx, sy) * 0.10, sz * 0.45, "rust", axis=(0, 0, 1))
        for spoke in range(12):
            angle = math.tau * spoke / 12
            _pipe(p, f"wheel_and_hub_spoke_{spoke}", (0, cy, 0.05), (min(sx, sy) * 0.28 * math.cos(angle), cy + min(sx, sy) * 0.28 * math.sin(angle), 0.05), 0.006, secondary)
    elif kind == "fuel_cell_turbine":
        _cylinder(p, "fuel_cell_turbine_pressure_shell", (0, cy, 0), min(sx, sz) * 0.38, sy * 0.78, primary)
        for side in (-1, 1):
            x = side * sx * 0.39
            p.append(_torus(f"fuel_cell_turbine_intake_lip_{side}", (x, cy, 0), min(sy, sz) * 0.28, 0.025, secondary, axis=(1, 0, 0)))
            for vane in range(5):
                z = -sz * 0.25 + vane * sz * 0.125
                _pipe(p, f"fuel_cell_turbine_stator_vane_{side}_{vane}", (x, cy - sy * 0.19, z), (x, cy + sy * 0.19, z), 0.012, "exposed_metal")
        _pipe(p, "fuel_cell_turbine_fuel_feed", (-sx * 0.36, sy * 0.28, sz * 0.30), (sx * 0.18, sy * 0.32, sz * 0.42), 0.02, "faded_teal")
        _box(p, "fuel_cell_turbine_cage_saddle", (0, sy * 0.08, 0), (sx * 0.88, 0.07, sz * 0.80), secondary)
    elif kind == "recliner_seat":
        _box(p, "recliner_seat_base_frame", (0, sy * 0.17, 0), (sx * 0.78, sy * 0.18, sz * 0.72), secondary)
        _box(p, "recliner_seat_cushion", (0, sy * 0.39, -sz * 0.08), (sx * 0.84, sy * 0.16, sz * 0.58), primary, 0.05)
        _box(p, "recliner_seat_back_cushion", (0, sy * 0.69, -sz * 0.34), (sx * 0.80, sy * 0.43, sz * 0.16), primary, 0.055)
        for side in (-1, 1):
            _box(p, f"recliner_seat_armrest_{side}", (side * sx * 0.46, sy * 0.50, -sz * 0.02), (sx * 0.11, sy * 0.24, sz * 0.56), secondary, 0.025)
            _pipe(p, f"recliner_seat_articulated_side_link_{side}", (side * sx * 0.30, sy * 0.26, -sz * 0.27), (side * sx * 0.30, sy * 0.63, -sz * 0.36), 0.018, "rust")
        _box(p, "recliner_seat_padded_footrest", (0, sy * 0.31, sz * 0.48), (sx * 0.74, sy * 0.12, sz * 0.26), primary, 0.04)
        _pipe(p, "recliner_seat_tilt_link", (-sx * 0.28, sy * 0.22, -sz * 0.12), (sx * 0.28, sy * 0.22, -sz * 0.12), 0.02, secondary)
    elif kind in {"old_tron_terminal", "abstract_sea_screen", "arcade_cabinet", "donation_terminal"}:
        if kind == "abstract_sea_screen":
            _box(p, "abstract_sea_screen_frame", (0, cy, 0), (sx, sy, sz), secondary, 0.025)
            _box(p, "abstract_sea_screen_glass_or_screen", (0, cy, -sz * 0.56), (sx * 0.86, sy * 0.82, sz * 0.20), "glass", 0.01)
            display_z = -sz * 0.56 - sz * 0.10 - 0.012
            for wave in range(4):
                vertices = []
                faces = []
                for point in range(11):
                    x = -sx * 0.38 + point * sx * 0.076
                    y = sy * (0.38 + wave * 0.075) + math.sin(point * 0.72 + wave * 0.9) * sy * 0.018
                    vertices.extend(((x, y - 0.012, display_z), (x, y + 0.012, display_z)))
                for point in range(10):
                    offset = point * 2
                    faces.append((offset, offset + 2, offset + 3, offset + 1))
                p.append(geo.mesh(f"abstract_sea_screen_sea_wave_{wave}", vertices, faces, "cool_light" if wave % 2 else "faded_teal"))
            for bubble in range(3):
                _cylinder(p, f"abstract_sea_screen_sea_glint_{bubble}", ((bubble - 1) * sx * 0.18, sy * (0.46 + bubble * 0.07), display_z - 0.008), 0.023, 0.01, "warm_light", axis=(0, 0, 1), segments=10)
        elif kind == "arcade_cabinet":
            _box(p, "arcade_cabinet_weighted_case", (0, sy * 0.36, 0), (sx, sy * 0.68, sz), primary, 0.06)
            _box(p, "arcade_cabinet_recessed_bezel", (0, sy * 0.73, -sz * 0.51), (sx * 0.82, sy * 0.31, 0.04), secondary)
            _box(p, "arcade_cabinet_glass_display", (0, sy * 0.74, -sz * 0.54), (sx * 0.72, sy * 0.25, 0.025), "cool_light")
            _box(p, "arcade_cabinet_control_deck", (0, sy * 0.56, -sz * 0.58), (sx * 0.80, 0.10, sz * 0.24), secondary)
            _pipe(p, "arcade_cabinet_ball_top_joystick", (-sx * 0.20, sy * 0.62, -sz * 0.60), (-sx * 0.20, sy * 0.73, -sz * 0.60), 0.012, "exposed_metal")
            _cylinder(p, "arcade_cabinet_joystick_ball", (-sx * 0.20, sy * 0.74, -sz * 0.60), 0.035, 0.045, "rust")
            for button in range(4):
                _cylinder(p, f"arcade_cabinet_action_button_{button}", (sx * 0.02 + button * sx * 0.13, sy * 0.62, -sz * 0.60), 0.028, 0.028, "warm_light" if button == 0 else "cream_plastic")
            _box(p, "arcade_cabinet_coin_door", (0, sy * 0.26, -sz * 0.51), (sx * 0.54, sy * 0.19, 0.025), "painted_metal")
        elif kind == "donation_terminal":
            _box(p, "donation_terminal_pedestal", (0, sy * 0.43, 0), (sx * 0.72, sy * 0.65, sz * 0.70), primary, 0.04)
            _box(p, "donation_terminal_touchscreen_bezel", (0, sy * 0.79, -sz * 0.38), (sx * 0.76, sy * 0.27, 0.04), secondary)
            _box(p, "donation_terminal_touchscreen", (0, sy * 0.79, -sz * 0.41), (sx * 0.66, sy * 0.20, 0.018), "warm_light")
            _box(p, "donation_terminal_receipt_slot", (0, sy * 0.54, -sz * 0.40), (sx * 0.46, 0.025, 0.02), "rubber")
            _cylinder(p, "donation_terminal_physical_button", (sx * 0.20, sy * 0.40, -sz * 0.40), 0.027, 0.02, "faded_teal", axis=(0, 0, 1))
            for side in (-1, 1):
                _pipe(p, f"donation_terminal_anchor_bolt_{side}", (side * sx * 0.30, sy * 0.10, 0), (side * sx * 0.30, sy * 0.02, 0), 0.015, secondary)
        else:
            _box(p, f"{kind}_terminal_tapered_case", (0, sy * 0.48, 0), (sx, sy * 0.82, sz), primary, 0.04)
            _box(p, f"{kind}_screen_bezel", (0, sy * 0.70, -sz * 0.53), (sx * 0.82, sy * 0.32, 0.04), secondary)
            _box(p, f"{kind}_glass_display", (0, sy * 0.70, -sz * 0.56), (sx * 0.70, sy * 0.23, 0.018), "glass")
            for row in range(4):
                _box(p, f"{kind}_vent_slot_{row}", (0, sy * (0.25 + row * 0.05), -sz * 0.53), (sx * 0.44, 0.018, 0.012), "rubber")
            for button in range(3):
                _cylinder(p, f"{kind}_control_button_{button}", ((button - 1) * sx * 0.17, sy * 0.42, -sz * 0.55), 0.024, 0.025, "exposed_metal", axis=(0, 0, 1))
    elif kind == "theatre_air_baffle":
        for panel in range(5):
            angle = (panel - 2) * 0.14
            x = (panel - 2) * sx * 0.20
            vertices = ((x - sx * 0.09, 0.02, -sz * 0.45), (x + sx * 0.09, 0.02, -sz * 0.45), (x + sx * 0.09 + angle, sy, sz * 0.45), (x - sx * 0.09 + angle, sy, sz * 0.45))
            p.append(geo.mesh(f"theatre_air_baffle_spaced_acoustic_panel_{panel}", vertices, ((0, 1, 2, 3),), primary))
            _pipe(p, f"theatre_air_baffle_hanger_{panel}", (x, sy, 0), (x, sy + 0.18, 0), 0.012, secondary)
    elif kind == "speaker_cabinet":
        _box(p, "speaker_cabinet_mdf_enclosure", (0, cy, 0), (sx * 0.94, sy * 0.94, sz * 0.86), primary, 0.035)
        p.append(_torus("speaker_cabinet_woofer_surround", (0, sy * 0.56, -sz * 0.46), sx * 0.28, 0.025, secondary, axis=(0, 0, 1)))
        _cylinder(p, "speaker_cabinet_woofer_cone", (0, sy * 0.56, -sz * 0.47), sx * 0.25, 0.045, "rubber", axis=(0, 0, 1))
        _cylinder(p, "speaker_cabinet_dust_cap", (0, sy * 0.56, -sz * 0.50), sx * 0.10, 0.03, "exposed_metal", axis=(0, 0, 1))
        p.append(_torus("speaker_cabinet_tweeter_ring", (0, sy * 0.82, -sz * 0.46), sx * 0.08, 0.014, secondary, axis=(0, 0, 1), segments=12))
        _box(p, "speaker_cabinet_bass_port", (sx * 0.30, sy * 0.18, -sz * 0.46), (sx * 0.12, sy * 0.08, 0.025), "rubber")
    elif kind == "arcade_stick_panel":
        _box(p, "arcade_stick_panel_control_plate", (0, cy, 0), (sx, sy * 0.26, sz), primary, 0.025)
        _pipe(p, "arcade_stick_panel_joystick_stem", (-sx * 0.25, sy * 0.66, -sz * 0.15), (-sx * 0.25, sy * 0.93, -sz * 0.15), 0.018, secondary)
        _cylinder(p, "arcade_stick_panel_ball_top", (-sx * 0.25, sy * 0.95, -sz * 0.15), 0.040, 0.04, "rust")
        for button in range(5):
            x = sx * (0.02 + button * 0.13)
            _cylinder(p, f"arcade_stick_panel_action_button_{button}", (x, sy * 0.72, sz * 0.15), 0.034, 0.04, "cool_light" if button == 0 else secondary)
        _box(p, "arcade_stick_panel_wiring_plate", (0, sy * 0.24, 0), (sx * 0.80, 0.03, sz * 0.70), "rubber")
    elif kind == "game_cartridge_case":
        _box(p, "game_cartridge_case_molded_shell", (0, cy, 0), (sx, sy * 0.82, sz), primary, 0.035)
        _box(p, "game_cartridge_case_recessed_label", (0, sy * 0.67, -sz * 0.53), (sx * 0.70, sy * 0.37, 0.015), secondary)
        _box(p, "game_cartridge_case_connector_shroud", (0, sy * 0.12, sz * 0.52), (sx * 0.78, sy * 0.16, sz * 0.18), "rubber")
        for pin in range(8):
            x = -sx * 0.33 + pin * sx * 0.095
            _box(p, f"game_cartridge_case_contact_pin_{pin}", (x, sy * 0.10, sz * 0.62), (0.012, sy * 0.06, 0.03), "exposed_metal")
    elif kind in {"score_card_tray", "prepaid_card_tray", "sorted_food_tubs"}:
        p.extend(_open_tray(f"{kind}_compartmented_open_tray", (0, sy * 0.18, 0), sx, sy * 0.36, sz, primary, secondary))
        count = 4 if kind != "prepaid_card_tray" else 5
        for item in range(count):
            x = -sx * 0.38 + item * sx * 0.18
            if kind == "sorted_food_tubs":
                p.append(_vessel(f"sorted_food_tubs_open_bin_{item}", (x, sy * 0.28, 0), sx * 0.09, sy * 0.52, "cream_plastic", segments=12))
            else:
                _box(p, f"{kind}_individual_index_card_{item}", (x, sy * 0.45, 0), (sx * 0.10, sy * 0.54, sz * 0.72), "cream_plastic", 0.006)
                _box(p, f"{kind}_printed_face_label_{item}", (x, sy * 0.47, -sz * 0.37), (sx * 0.07, sy * 0.27, 0.012), "faded_teal")
        for divider in range(3):
            x = -sx * 0.30 + divider * sx * 0.30
            _box(p, f"{kind}_slot_divider_{divider}", (x, sy * 0.22, 0), (0.018, sy * 0.30, sz * 0.85), secondary)
    elif kind == "amulet_shelf":
        for side in (-1, 1):
            _box(p, f"amulet_shelf_stone_post_{side}", (side * sx * 0.46, sy * 0.50, 0), (sx * 0.08, sy, sz * 0.24), primary)
        for tier in range(4):
            y = sy * (0.16 + tier * 0.22)
            _box(p, f"amulet_shelf_display_shelf_{tier}", (0, y, 0), (sx, 0.04, sz * 0.42), primary)
            for charm in range(4):
                x = -sx * 0.32 + charm * sx * 0.21
                _pipe(p, f"amulet_shelf_charm_cord_{tier}_{charm}", (x, y + sy * 0.06, -sz * 0.10), (x, y + sy * 0.06, sz * 0.12), 0.006, secondary)
                _box(p, f"amulet_shelf_paper_charm_{tier}_{charm}", (x, y - sy * 0.03, sz * 0.15), (0.06, sy * 0.12, 0.012), "cream_plastic")
    elif kind == "stitched_charm_pouches":
        for pouch in range(3):
            x = (pouch - 1) * sx * 0.34
            _box(p, f"stitched_charm_pouches_soft_bag_body_{pouch}", (x, sy * 0.35, 0), (sx * 0.27, sy * 0.48, sz * 0.80), primary, 0.055)
            _pipe(p, f"stitched_charm_pouches_drawstring_{pouch}", (x - sx * 0.10, sy * 0.63, -sz * 0.38), (x + sx * 0.10, sy * 0.63, -sz * 0.38), 0.008, secondary)
            for stitch in range(4):
                _pipe(p, f"stitched_charm_pouches_seam_{pouch}_{stitch}", (x - sx * 0.09, sy * (0.20 + stitch * 0.09), -sz * 0.42), (x + sx * 0.09, sy * (0.20 + stitch * 0.09), -sz * 0.42), 0.004, "rust")
    elif kind == "paper_talisman_bundle":
        for paper in range(4):
            x = (paper - 1.5) * sx * 0.14
            _box(p, f"paper_talisman_bundle_folded_paper_{paper}", (x, sy * 0.49, paper * 0.003), (sx * 0.68, sy * 0.84, 0.008), primary)
            _pipe(p, f"paper_talisman_bundle_brush_mark_{paper}", (x, sy * 0.60, -0.008), (x, sy * 0.32, -0.008), 0.009, "rust")
            _pipe(p, f"paper_talisman_bundle_hanging_thread_{paper}", (x, sy * 0.90, 0), (x + sx * 0.10, sy * 1.05, 0), 0.006, secondary)
        _box(p, "paper_talisman_bundle_wooden_spindle", (0, sy * 0.97, 0), (sx * 0.90, 0.035, 0.04), secondary)
    elif kind == "thread_spools":
        for spool in range(5):
            x = -sx * 0.38 + spool * sx * 0.19
            radius = min(sy, sz) * (0.14 + (spool % 2) * 0.02)
            _cylinder(p, f"thread_spools_wooden_core_{spool}", (x, sy * 0.42, 0), radius * 0.32, sy * 0.70, primary)
            p.append(_torus(f"thread_spools_lower_flange_{spool}", (x, sy * 0.10, 0), radius * 0.80, 0.018, secondary))
            p.append(_torus(f"thread_spools_upper_flange_{spool}", (x, sy * 0.76, 0), radius * 0.80, 0.018, secondary))
            for layer in range(4):
                y = sy * (0.21 + layer * 0.13)
                p.append(_torus(f"thread_spools_wound_thread_layer_{spool}_{layer}", (x, y, 0), radius * (0.62 + layer * 0.02), 0.018, "cloth", segments=12, sides=4))
    elif kind == "classroom_desk":
        _box(p, "classroom_desk_wooden_worktop", (0, sy * 0.79, 0), (sx, sy * 0.12, sz), primary)
        for side in (-1, 1):
            for front in (-1, 1):
                _box(p, f"classroom_desk_frame_leg_{side}_{front}", (side * sx * 0.42, sy * 0.40, front * sz * 0.38), (0.045, sy * 0.76, 0.045), secondary)
        _box(p, "classroom_desk_open_bag_hook", (sx * 0.43, sy * 0.52, 0), (0.04, 0.15, 0.10), "rust")
        _box(p, "classroom_desk_pencil_groove", (0, sy * 0.86, sz * 0.43), (sx * 0.86, 0.018, 0.035), secondary)
        _box(p, "classroom_desk_single_drawer", (0, sy * 0.61, -sz * 0.36), (sx * 0.62, sy * 0.12, sz * 0.22), secondary)
    elif kind == "notice_slot":
        _box(p, "notice_slot_corkboard", (0, cy, 0), (sx, sy * 0.90, 0.08), primary)
        for paper in range(4):
            x = -sx * 0.32 + (paper % 2) * sx * 0.52
            y = sy * (0.22 + (paper // 2) * 0.42)
            _box(p, f"notice_slot_posted_notice_{paper}", (x, y, -0.06), (sx * 0.35, sy * 0.30, 0.015), "cream_plastic")
            _cylinder(p, f"notice_slot_red_pin_{paper}", (x, y + sy * 0.12, -0.075), 0.018, 0.015, "rust", axis=(0, 0, 1), segments=8)
        _box(p, "notice_slot_lower_paper_ledge", (0, -sy * 0.03, -0.12), (sx * 1.04, 0.06, 0.18), secondary)
        _pipe(p, "notice_slot_hanging_wire", (-sx * 0.40, sy * 0.99, 0), (sx * 0.40, sy * 0.99, 0), 0.008, "exposed_metal")
    elif kind == "sealed_parts_bin":
        p.extend(_open_tray("sealed_parts_bin_open_top_tote", (0, sy * 0.45, 0), sx, sy * 0.85, sz, primary, secondary))
        for side in (-1, 1):
            _box(p, f"sealed_parts_bin_lift_handle_{side}", (side * sx * 0.47, sy * 0.62, 0), (0.03, 0.12, sz * 0.30), "rubber")
        _box(p, "sealed_parts_bin_inventory_label", (0, sy * 0.55, -sz * 0.52), (sx * 0.48, sy * 0.18, 0.02), "cream_plastic")
        for rib in range(4):
            _box(p, f"sealed_parts_bin_reinforcing_rib_{rib}", (0, sy * (0.12 + rib * 0.16), sz * 0.50), (sx * 0.86, 0.025, 0.025), secondary)
    elif kind == "lock_bar_and_padlock":
        _pipe(p, "lock_bar_and_padlock_cross_door_bar", (-sx * 0.52, sy * 0.55, 0), (sx * 0.52, sy * 0.55, 0), 0.028, primary)
        for side in (-1, 1):
            _box(p, f"lock_bar_and_padlock_hasp_plate_{side}", (side * sx * 0.40, sy * 0.55, 0), (0.12, 0.18, 0.05), secondary)
            p.append(_torus(f"lock_bar_and_padlock_padlock_shackle_{side}", (side * sx * 0.20, sy * 0.73, 0), 0.055, 0.014, secondary, axis=(1, 0, 0), segments=10))
            _box(p, f"lock_bar_and_padlock_brass_lock_body_{side}", (side * sx * 0.20, sy * 0.62, 0), (0.13, 0.13, 0.07), "rust", 0.018)
            _cylinder(p, f"lock_bar_and_padlock_keyhole_{side}", (side * sx * 0.20, sy * 0.61, -0.04), 0.014, 0.01, "rubber", axis=(0, 0, 1), segments=8)
    elif kind == "stained_bar_counter":
        _box(p, "stained_bar_counter_stone_top", (0, sy * 0.82, 0), (sx, sy * 0.12, sz), primary, 0.025)
        for side in (-1, 1):
            _box(p, f"stained_bar_counter_end_panel_{side}", (side * sx * 0.45, sy * 0.43, 0), (sx * 0.10, sy * 0.74, sz * 0.80), secondary)
        _box(p, "stained_bar_counter_open_knee_bay", (0, sy * 0.44, 0), (sx * 0.78, sy * 0.12, sz * 0.60), primary)
        _box(p, "stained_bar_counter_front_fascia", (0, sy * 0.63, -sz * 0.44), (sx * 0.86, sy * 0.23, 0.03), secondary)
        _pipe(p, "stained_bar_counter_foot_rail", (-sx * 0.44, sy * 0.12, -sz * 0.54), (sx * 0.44, sy * 0.12, -sz * 0.54), 0.025, "exposed_metal")
        for drawer in range(2):
            x = (drawer - 0.5) * sx * 0.42
            _box(p, f"stained_bar_counter_drawer_{drawer}", (x, sy * 0.69, -sz * 0.47), (sx * 0.34, sy * 0.12, 0.02), "wood")
    elif kind == "bent_bar_entry_rail":
        _pipe(p, "bent_bar_entry_rail_bent_handrail", (-sx * 0.42, sy * 0.86, -sz * 0.45), (-sx * 0.42, sy * 0.86, sz * 0.38), 0.03, primary)
        _pipe(p, "bent_bar_entry_rail_return", (-sx * 0.42, sy * 0.86, sz * 0.38), (sx * 0.36, sy * 0.86, sz * 0.38), 0.03, primary)
        for post in range(4):
            x = -sx * 0.42 + post * sx * 0.26
            z = -sz * 0.40 + post * sz * 0.24
            _pipe(p, f"bent_bar_entry_rail_floor_post_{post}", (x, 0, z), (x, sy * 0.86, z), 0.026, secondary)
            _box(p, f"bent_bar_entry_rail_anchor_plate_{post}", (x, 0.025, z), (0.11, 0.035, 0.11), "rust")
    elif kind == "booth_partition":
        for booth in range(2):
            x = (booth - 0.5) * sx * 0.50
            _box(p, f"booth_partition_upholstered_back_{booth}", (x, sy * 0.68, -sz * 0.38), (sx * 0.45, sy * 0.62, sz * 0.18), primary, 0.03)
            _box(p, f"booth_partition_bench_seat_{booth}", (x, sy * 0.28, sz * 0.02), (sx * 0.43, sy * 0.12, sz * 0.56), secondary, 0.035)
            for side in (-1, 1):
                _box(p, f"booth_partition_seat_support_{booth}_{side}", (x + side * sx * 0.18, sy * 0.13, 0), (0.045, sy * 0.26, 0.045), "exposed_metal")
        _box(p, "booth_partition_privacy_divider", (0, sy * 0.62, sz * 0.15), (0.06, sy * 0.74, sz * 0.60), primary)
    elif kind == "repair_sewing_machine":
        _box(p, "repair_sewing_machine_cast_iron_bed", (0, sy * 0.18, 0), (sx, sy * 0.13, sz), primary, 0.025)
        _box(p, "repair_sewing_machine_vertical_arm", (-sx * 0.27, sy * 0.56, -sz * 0.18), (sx * 0.18, sy * 0.67, sz * 0.22), secondary)
        _box(p, "repair_sewing_machine_horizontal_head", (0, sy * 0.80, -sz * 0.18), (sx * 0.72, sy * 0.16, sz * 0.22), primary, 0.035)
        _pipe(p, "repair_sewing_machine_needle_bar", (sx * 0.29, sy * 0.78, -sz * 0.22), (sx * 0.29, sy * 0.30, -sz * 0.22), 0.012, secondary)
        _pipe(p, "repair_sewing_machine_presser_foot", (sx * 0.25, sy * 0.32, -sz * 0.16), (sx * 0.34, sy * 0.32, -sz * 0.16), 0.012, "rust")
        p.append(_torus("repair_sewing_machine_handwheel", (-sx * 0.48, sy * 0.54, 0), sy * 0.22, 0.018, secondary, axis=(1, 0, 0), segments=16))
        _cylinder(p, "repair_sewing_machine_spool_pin", (-sx * 0.28, sy * 0.94, 0), 0.018, sy * 0.18, secondary)
        _cylinder(p, "repair_sewing_machine_thread_spool", (-sx * 0.28, sy * 1.02, 0), 0.06, sy * 0.12, "cloth")
        _box(p, "repair_sewing_machine_thread_plate", (sx * 0.22, sy * 0.22, -sz * 0.22), (sx * 0.32, 0.012, sz * 0.20), "exposed_metal")
    elif kind == "thread_and_button_box":
        p.extend(_open_tray("thread_and_button_box_open_drawer", (0, sy * 0.42, 0), sx, sy * 0.80, sz, primary, secondary))
        for spool in range(3):
            x = -sx * 0.28 + spool * sx * 0.27
            _cylinder(p, f"thread_and_button_box_thread_spool_core_{spool}", (x, sy * 0.56, -sz * 0.13), 0.04, sy * 0.45, secondary)
            p.append(_torus(f"thread_and_button_box_spool_winding_{spool}", (x, sy * 0.56, -sz * 0.13), 0.07, 0.018, "cloth", segments=12, sides=4))
        for button in range(8):
            x = -sx * 0.36 + (button % 4) * sx * 0.23
            z = -sz * 0.30 + (button // 4) * sz * 0.46
            p.append(_torus(f"thread_and_button_box_loose_button_{button}", (x, sy * 0.90, z), 0.035, 0.01, "cream_plastic", axis=(0, 1, 0), segments=10, sides=4))
    elif kind == "patchwork_garment_rail":
        _pipe(p, "patchwork_garment_rail_clothes_bar", (-sx * 0.48, sy * 0.91, 0), (sx * 0.48, sy * 0.91, 0), 0.022, secondary)
        for side in (-1, 1):
            _pipe(p, f"patchwork_garment_rail_stand_{side}", (side * sx * 0.42, 0, 0), (side * sx * 0.42, sy * 0.93, 0), 0.025, secondary)
            _pipe(p, f"patchwork_garment_rail_floor_foot_{side}", (side * sx * 0.52, 0.03, 0), (side * sx * 0.32, 0.03, 0), 0.025, secondary)
        for garment in range(4):
            x = -sx * 0.33 + garment * sx * 0.22
            _pipe(p, f"patchwork_garment_rail_hanger_{garment}", (x, sy * 0.87, 0), (x - sx * 0.08, sy * 0.70, 0), 0.009, "rust")
            _box(p, f"patchwork_garment_rail_hanging_patchwork_{garment}", (x, sy * 0.44, sz * 0.07), (sx * 0.18, sy * 0.45, 0.025), primary)
            _box(p, f"patchwork_garment_rail_visible_mending_patch_{garment}", (x + sx * 0.04, sy * 0.49, sz * 0.09), (sx * 0.07, sy * 0.08, 0.012), secondary)
    elif kind == "zipper_and_patch_cards":
        for card in range(3):
            x = (card - 1) * sx * 0.32
            _box(p, f"zipper_and_patch_cards_sewing_card_{card}", (x, sy * 0.38, 0), (sx * 0.28, sy * 0.72, sz * 0.72), primary)
            _box(p, f"zipper_and_patch_cards_fabric_patch_{card}", (x, sy * 0.42, -sz * 0.39), (sx * 0.20, sy * 0.26, 0.018), secondary)
            for tooth in range(6):
                y = sy * (0.19 + tooth * 0.075)
                _box(p, f"zipper_and_patch_cards_zipper_tooth_{card}_{tooth}", (x, y, -sz * 0.41), (0.018, 0.015, 0.012), "exposed_metal")
            _pipe(p, f"zipper_and_patch_cards_zipper_tape_{card}", (x, sy * 0.15, -sz * 0.40), (x, sy * 0.78, -sz * 0.40), 0.012, secondary)
    elif kind == "bench_vise":
        _box(p, "bench_vise_mounting_bolted_base", (0, sy * 0.10, 0), (sx * 0.72, sy * 0.16, sz * 0.72), secondary)
        _box(p, "bench_vise_fixed_jaw", (0, sy * 0.54, -sz * 0.24), (sx * 0.78, sy * 0.58, sz * 0.20), primary)
        _box(p, "bench_vise_movable_jaw", (0, sy * 0.54, sz * 0.22), (sx * 0.78, sy * 0.58, sz * 0.20), primary)
        _box(p, "bench_vise_hardened_jaw_face_fixed", (0, sy * 0.64, -sz * 0.34), (sx * 0.69, sy * 0.24, 0.035), "exposed_metal")
        _box(p, "bench_vise_hardened_jaw_face_movable", (0, sy * 0.64, sz * 0.31), (sx * 0.69, sy * 0.24, 0.035), "exposed_metal")
        _pipe(p, "bench_vise_lead_screw", (0, sy * 0.38, -sz * 0.28), (0, sy * 0.38, sz * 0.45), 0.018, secondary)
        _pipe(p, "bench_vise_cross_handle", (-sx * 0.43, sy * 0.38, sz * 0.45), (sx * 0.43, sy * 0.38, sz * 0.45), 0.014, secondary)
        _box(p, "bench_vise_anvil_pad", (0, sy * 0.86, 0), (sx * 0.48, 0.035, sz * 0.55), secondary)
    elif kind == "hydrogen_service_cell":
        _cylinder(p, "hydrogen_service_cell_pressure_vessel", (0, sy * 0.49, 0), min(sx, sz) * 0.36, sy * 0.74, primary)
        for side in (-1, 1):
            _pipe(p, f"hydrogen_service_cell_cage_upright_{side}", (side * sx * 0.42, sy * 0.04, -sz * 0.25), (side * sx * 0.42, sy * 0.96, -sz * 0.25), 0.022, secondary)
            p.append(_torus(f"hydrogen_service_cell_cage_band_{side}", (0, sy * 0.25 + (side + 1) * sy * 0.47, 0), min(sx, sz) * 0.40, 0.016, secondary))
        _cylinder(p, "hydrogen_service_cell_valve", (0, sy * 0.91, 0), 0.05, 0.10, "rust")
        p.append(_torus("hydrogen_service_cell_regulator_gauge", (0, sy * 0.79, -sz * 0.37), 0.05, 0.012, "exposed_metal", axis=(0, 0, 1), segments=10))
        _pipe(p, "hydrogen_service_cell_regulator_line", (sx * 0.15, sy * 0.83, -sz * 0.36), (sx * 0.46, sy * 0.25, -sz * 0.36), 0.014, "faded_teal")
    else:
        raise ValueError(f"no function-specific static form defined for prop kind {kind!r}")

    # Each assembled prop keeps named source parts and has a non-zero measured silhouette.
    if len(p) < 3 or sum(len(part.faces) for part in p) < 12:
        raise RuntimeError(f"prop {kind} lacks physical feature geometry")
    return p


def build_prop(kind: str, center: Vec3, rotation: float, spec: tuple[str, str, tuple[float, float, float], str, str]) -> Assembly:
    key, _family, size, primary, secondary = spec
    if kind != key:
        raise ValueError(f"asset spec {key!r} does not describe requested prop {kind!r}")
    parts = _make_parts(kind, float(size[0]), float(size[1]), float(size[2]), primary, secondary)
    return Assembly("interior_props", kind, center, rotation, parts)
