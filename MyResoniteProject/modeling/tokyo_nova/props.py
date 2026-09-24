"""Reusable, physically modeled north-district assemblies."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

from modeling.tokyo_nova import geometry as geo

Vec3 = tuple[float, float, float]


def _rotate(point: Vec3, radians: float) -> Vec3:
    c, s = math.cos(radians), math.sin(radians)
    return (point[0] * c + point[2] * s, point[1], -point[0] * s + point[2] * c)


@dataclass
class Assembly:
    """Named logical asset. Part geometry stays editable and is batched by material at export."""

    kind: str
    name: str
    origin: Vec3
    rotation: float
    parts: list[geo.MeshData] = field(default_factory=list)

    @property
    def bounds(self) -> tuple[Vec3, Vec3]:
        points = []
        for part in self.parts:
            for vertex in part.vertices:
                rotated = _rotate(vertex, self.rotation)
                points.append(tuple(rotated[i] + self.origin[i] for i in range(3)))
        if not points:
            return self.origin, self.origin
        return tuple(min(point[i] for point in points) for i in range(3)), tuple(max(point[i] for point in points) for i in range(3))  # type: ignore[return-value]

    def transformed_parts(self) -> list[geo.MeshData]:
        """Return parts with placement baked into vertices for direct mesh batching."""
        result = []
        for part in self.parts:
            vertices = []
            for vertex in part.vertices:
                rotated = _rotate(vertex, self.rotation)
                vertices.append(tuple(rotated[i] + self.origin[i] for i in range(3)))
            result.append(geo.mesh(part.name, vertices, part.faces, part.material))
        return result


def _box(parts: list[geo.MeshData], name: str, center: Vec3, size: Vec3, material: str, bevel: float = 0.0) -> None:
    parts.append(geo.beveled_box(name, center, size, bevel, material) if bevel else geo.box(name, center, size, material))


def _pipe(parts: list[geo.MeshData], name: str, start: Vec3, end: Vec3, radius: float, material: str) -> None:
    parts.append(geo.pipe(name, start, end, radius, material, segments=8))


def _cylinder(parts: list[geo.MeshData], name: str, center: Vec3, radius: float, depth: float, material: str, segments: int = 12) -> None:
    parts.append(geo.cylinder(name, center, radius, depth, material, segments=segments))


def _food_stall() -> list[geo.MeshData]:
    parts: list[geo.MeshData] = []
    # Four mismatched, sloping corrugated awning panels and the timber/steel frame.
    panel_widths = (0.97, 1.08, 0.82, 1.03)
    cursor = -sum(panel_widths) / 2
    for index, width in enumerate(panel_widths):
        x = cursor + width / 2
        cursor += width
        _box(parts, f"awning_sheet_{index}", (x, 2.78 + (index % 2) * 0.025, 0.64), (width, 0.055, 1.38 - (index % 2) * 0.12), "painted_metal", 0.012)
        for ridge in range(5):
            rx = x - width * 0.39 + ridge * width * 0.19
            _pipe(parts, f"awning_corrugation_{index}_{ridge}", (rx, 2.815, 0.02), (rx, 2.74, 1.25), 0.009, "exposed_metal")
    for x in (-2.15, 2.15):
        _pipe(parts, f"awning_front_post_{x}", (x, 0.18, 1.28), (x, 2.68, 1.28), 0.045, "painted_metal")
        _pipe(parts, f"awning_rear_post_{x}", (x, 0.18, -0.55), (x, 2.94, -0.55), 0.04, "exposed_metal")
        _pipe(parts, f"awning_diagonal_brace_{x}", (x, 2.20, 0.2), (x, 2.72, 1.23), 0.025, "rust")
    _pipe(parts, "awning_front_beam", (-2.16, 2.68, 1.26), (2.16, 2.68, 1.26), 0.035, "exposed_metal")
    # Counter with separate rolled rim, two fascia strips and stout side supports.
    _box(parts, "counter_body", (0, 1.02, 0.25), (4.35, 0.72, 0.78), "wood", 0.045)
    _box(parts, "counter_top", (0, 1.42, 0.25), (4.5, 0.09, 0.91), "exposed_metal", 0.025)
    _box(parts, "counter_front_rim", (0, 1.49, 0.715), (4.42, 0.055, 0.045), "painted_metal", 0.012)
    _box(parts, "counter_lower_rim", (0, 0.63, 0.64), (4.23, 0.06, 0.06), "exposed_metal", 0.012)
    for x in (-1.87, 1.87):
        _box(parts, f"counter_support_{x}", (x, 0.47, 0.25), (0.12, 0.18, 0.68), "rust", 0.018)
    # Two lidded stockpots with wire handles and foot rings.
    for index, x in enumerate((-1.22, -0.48)):
        _cylinder(parts, f"stockpot_{index}", (x, 1.82, 0.12), 0.30, 0.48, "exposed_metal", 20)
        _cylinder(parts, f"stockpot_lid_{index}", (x, 2.08, 0.12), 0.315, 0.045, "exposed_metal", 20)
        _cylinder(parts, f"stockpot_lid_knob_{index}", (x, 2.12, 0.12), 0.045, 0.045, "rubber", 10)
        _pipe(parts, f"stockpot_handle_left_{index}", (x - 0.29, 1.92, 0.12), (x - 0.39, 1.92, 0.12), 0.025, "exposed_metal")
        _pipe(parts, f"stockpot_handle_right_{index}", (x + 0.29, 1.92, 0.12), (x + 0.39, 1.92, 0.12), 0.025, "exposed_metal")
        _cylinder(parts, f"stockpot_wear_ring_{index}", (x, 1.62, 0.12), 0.307, 0.024, "rust", 20)
    # Ceramic bowls, paired chopsticks, tray and condiments.
    for index, x in enumerate((0.38, 0.96, 1.54)):
        _cylinder(parts, f"ceramic_bowl_{index}", (x, 1.57, 0.30), 0.15, 0.10, "ceramic", 16)
        _cylinder(parts, f"bowl_inner_{index}", (x, 1.619, 0.30), 0.112, 0.012, "glass", 16)
        _pipe(parts, f"chopstick_a_{index}", (x - 0.07, 1.67, 0.28), (x + 0.06, 1.67, 0.67), 0.007, "wood")
        _pipe(parts, f"chopstick_b_{index}", (x - 0.025, 1.67, 0.27), (x + 0.105, 1.67, 0.66), 0.007, "wood")
    _box(parts, "condiment_tray", (1.95, 1.57, 0.32), (0.42, 0.10, 0.55), "exposed_metal", 0.018)
    for index, x in enumerate((1.82, 1.96, 2.10)):
        _cylinder(parts, f"condiment_jar_{index}", (x, 1.69, 0.28), 0.045, 0.20, "plastic", 10)
        _cylinder(parts, f"condiment_cap_{index}", (x, 1.80, 0.28), 0.047, 0.025, "cream_plastic", 10)
    # Reusable CFC canisters and nested wash-up trays, not disposable packaging.
    for index, x in enumerate((-1.94, -1.63)):
        _box(parts, f"reusable_container_{index}", (x, 1.63, 0.68), (0.23, 0.21, 0.22), "cream_plastic", 0.035)
        _box(parts, f"container_gasket_{index}", (x, 1.744, 0.68), (0.21, 0.018, 0.20), "rubber", 0.008)
        _box(parts, f"container_latch_{index}", (x, 1.65, 0.796), (0.055, 0.07, 0.012), "exposed_metal", 0.006)
    for index in range(2):
        _box(parts, f"dish_tray_{index}", (0.80 + index * 0.45, 1.58, -0.36), (0.38, 0.08, 0.3), "plastic", 0.022)
        for rib in range(3):
            _box(parts, f"tray_rib_{index}_{rib}", (0.80 + index * 0.45, 1.625, -0.45 + rib * 0.09), (0.31, 0.012, 0.012), "exposed_metal")
    # Refrigerated counter unit, slotted condenser, fan guard, handle and drain.
    _box(parts, "under_counter_refrigerator", (-1.48, 0.43, -0.38), (0.92, 0.70, 0.66), "cream_plastic", 0.055)
    _box(parts, "refrigerator_door", (-1.48, 0.43, -0.721), (0.82, 0.59, 0.025), "painted_metal", 0.018)
    _pipe(parts, "refrigerator_pull", (-1.78, 0.44, -0.75), (-1.64, 0.44, -0.75), 0.018, "exposed_metal")
    _box(parts, "refrigerator_vent_panel", (-1.48, 0.42, -0.755), (0.35, 0.22, 0.014), "rubber")
    for vent in range(7):
        _box(parts, f"refrigerator_vent_slot_{vent}", (-1.62 + vent * 0.047, 0.42, -0.766), (0.014, 0.16, 0.006), "exposed_metal")
    _cylinder(parts, "ventilation_fan_hub", (1.82, 2.16, -0.55), 0.09, 0.07, "exposed_metal", 16)
    for blade in range(4):
        angle = math.tau * blade / 4
        _pipe(parts, f"ventilation_fan_blade_{blade}", (1.82, 2.16, -0.55), (1.82 + 0.24 * math.cos(angle), 2.16 + 0.24 * math.sin(angle), -0.55), 0.025, "painted_metal")
    _box(parts, "service_light_casing", (0, 2.47, -0.42), (0.80, 0.12, 0.16), "plastic", 0.04)
    _box(parts, "service_light_diffuser", (0, 2.40, -0.42), (0.67, 0.025, 0.12), "warm_light", 0.012)
    _box(parts, "menu_sign_panel", (0, 2.40, 1.02), (1.66, 0.52, 0.07), "wood", 0.025)
    _box(parts, "menu_sign_face", (0, 2.40, 1.064), (1.52, 0.38, 0.014), "painted_metal", 0.008)
    # Drips, edge wear and a replaced sheet distinguish this from clean uniform props.
    for index, x in enumerate((-1.84, -0.15, 1.72)):
        _pipe(parts, f"awning_rust_streak_{index}", (x, 2.69, 1.24), (x + 0.025, 2.27 + (index % 2) * 0.1, 1.27), 0.012, "rust")
    return parts


def _repair_shop() -> list[geo.MeshData]:
    parts: list[geo.MeshData] = []
    # Main repair bench with replaceable laminate, steel frame and drawers.
    _box(parts, "repair_bench_top", (0, 0.94, 0.05), (3.8, 0.11, 1.02), "wood", 0.04)
    _box(parts, "bench_front_edge", (0, 0.88, 0.57), (3.76, 0.045, 0.045), "exposed_metal", 0.01)
    for x in (-1.72, 1.72):
        for z in (-0.36, 0.40):
            _box(parts, f"bench_leg_{x}_{z}", (x, 0.43, z), (0.08, 0.80, 0.08), "painted_metal", 0.012)
    for x in (-1.12, 0.0, 1.12):
        _box(parts, f"drawer_{x}", (x, 0.67, 0.57), (0.94, 0.31, 0.13), "painted_metal", 0.018)
        _pipe(parts, f"drawer_pull_{x}", (x - 0.10, 0.67, 0.65), (x + 0.10, 0.67, 0.65), 0.012, "exposed_metal")
    _box(parts, "anti_static_mat", (0, 1.012, -0.04), (1.90, 0.025, 0.63), "faded_teal", 0.015)
    # Exactly 45 cm monitor with bezel, stand, knobs and rear cooling slots.
    _box(parts, "monitor_45cm_shell", (-0.76, 1.72, -0.27), (0.45, 0.31, 0.055), "plastic", 0.035)
    _box(parts, "monitor_45cm_glass", (-0.76, 1.73, -0.238), (0.414, 0.263, 0.008), "glass", 0.018)
    _box(parts, "monitor_stand_neck", (-0.76, 1.48, -0.28), (0.045, 0.20, 0.05), "exposed_metal", 0.012)
    _box(parts, "monitor_stand_foot", (-0.76, 1.365, -0.25), (0.27, 0.025, 0.18), "plastic", 0.012)
    _cylinder(parts, "monitor_status_lamp", (-0.58, 1.57, -0.237), 0.012, 0.008, "cool_light", 8)
    for vent in range(7):
        _box(parts, f"monitor_rear_vent_{vent}", (-0.90 + vent * 0.047, 1.57, -0.298), (0.018, 0.055, 0.006), "exposed_metal")
    # 35 cm repairable terminal mainboard, vented enclosure and removable cover.
    _box(parts, "terminal_box_35cm", (0.15, 1.19, 0.03), (0.35, 0.18, 0.29), "painted_metal", 0.025)
    _box(parts, "terminal_removable_cover", (0.15, 1.19, 0.184), (0.32, 0.15, 0.012), "exposed_metal", 0.012)
    for vent in range(6):
        _box(parts, f"terminal_box_vent_{vent}", (0.035 + vent * 0.044, 1.19, 0.194), (0.012, 0.09, 0.004), "rubber")
    for screw_x in (-0.005, 0.305):
        for screw_y in (1.13, 1.25):
            _cylinder(parts, f"terminal_cover_fastener_{screw_x}_{screw_y}", (screw_x, screw_y, 0.195), 0.008, 0.004, "rust", 8)
    # Two tray levels and a grounded ESD parts tray with compartments.
    for index, x in enumerate((-1.35, 1.30)):
        _box(parts, f"repair_tray_{index}", (x, 1.07, 0.22), (0.46, 0.06, 0.38), "exposed_metal", 0.012)
        for divider in (-0.08, 0.08):
            _box(parts, f"tray_divider_{index}_{divider}", (x + divider, 1.105, 0.22), (0.012, 0.025, 0.34), "painted_metal")
    _box(parts, "parts_cabinet", (1.46, 1.75, -0.48), (0.63, 1.04, 0.38), "painted_metal", 0.035)
    for row in range(4):
        for column in range(3):
            x = 1.25 + column * 0.20
            y = 1.39 + row * 0.22
            _box(parts, f"drawer_bin_{row}_{column}", (x, y, -0.276), (0.16, 0.17, 0.02), "plastic", 0.012)
            _pipe(parts, f"drawer_bin_pull_{row}_{column}", (x - 0.025, y, -0.262), (x + 0.025, y, -0.262), 0.006, "exposed_metal")
    # Hand tools, rework air hose, cable coil, solder stand and static-safe caddy.
    for index, x in enumerate((-1.43, -1.12, -0.81)):
        _pipe(parts, f"precision_driver_handle_{index}", (x, 1.06, -0.10), (x, 1.16, -0.10), 0.022, "rubber")
        _pipe(parts, f"precision_driver_shaft_{index}", (x, 1.16, -0.10), (x + 0.035, 1.30, -0.10), 0.006, "exposed_metal")
    _box(parts, "hot_air_rework_station", (0.98, 1.15, -0.42), (0.49, 0.28, 0.39), "plastic", 0.025)
    _cylinder(parts, "rework_station_dial", (0.82, 1.18, -0.216), 0.043, 0.025, "exposed_metal", 12)
    _pipe(parts, "rework_air_hose", (1.14, 1.28, -0.40), (1.39, 1.58, -0.44), 0.016, "rubber")
    _pipe(parts, "soldering_iron", (0.42, 1.04, -0.25), (0.62, 1.23, -0.21), 0.018, "exposed_metal")
    _box(parts, "soldering_iron_grip", (0.48, 1.10, -0.23), (0.13, 0.045, 0.05), "rubber", 0.018)
    _box(parts, "solder_iron_stand_base", (0.65, 1.05, 0.16), (0.30, 0.045, 0.20), "exposed_metal", 0.018)
    _pipe(parts, "solder_iron_stand_arm", (0.65, 1.07, 0.15), (0.65, 1.30, 0.15), 0.014, "exposed_metal")
    _cylinder(parts, "magnifier_ring", (-0.12, 1.12, 0.28), 0.105, 0.018, "exposed_metal", 20)
    _pipe(parts, "magnifier_stem", (-0.12, 1.06, 0.28), (-0.12, 1.29, 0.28), 0.012, "painted_metal")
    # Cable bundle includes distinct insulated leads and strain-relief boots.
    for index in range(5):
        x = -0.32 + index * 0.075
        _pipe(parts, f"test_lead_{index}", (x, 1.04, -0.32), (x + 0.19, 1.13, -0.45 + index * 0.025), 0.008, "faded_teal" if index % 2 else "rubber")
    _box(parts, "repair_ad_lightbox", (0, 2.45, 3.90), (2.02, 0.72, 0.09), "painted_metal", 0.028)
    _box(parts, "repair_ad_diffuser", (0, 2.45, 3.95), (1.86, 0.56, 0.015), "warm_light", 0.015)
    # Patched cable trunk and local task lamp.
    _box(parts, "cable_trunk", (1.95, 2.22, -0.5), (0.13, 0.10, 1.38), "exposed_metal", 0.018)
    _pipe(parts, "task_lamp_arm", (-1.58, 1.04, -0.22), (-1.58, 1.55, -0.30), 0.014, "exposed_metal")
    _box(parts, "task_lamp_shade", (-1.58, 1.57, -0.30), (0.28, 0.07, 0.20), "painted_metal", 0.035)
    _box(parts, "task_lamp_diffuser", (-1.58, 1.53, -0.30), (0.22, 0.015, 0.15), "warm_light", 0.01)
    # Detailed shell around the equipment: true glazed windows and a clear 1.35 m entry.
    _box(parts, "repair_shop_rear_wall", (0, 1.68, -0.94), (4.66, 3.36, 0.16), "patched_concrete", 0.025)
    for x in (-2.31, 2.31):
        _box(parts, f"repair_shop_side_wall_{x}", (x, 1.68, 0.02), (0.16, 3.36, 1.95), "concrete", 0.02)
        _box(parts, f"repair_front_pier_{x}", (x, 1.62, 3.12), (0.18, 3.18, 0.20), "patched_concrete", 0.025)
    _box(parts, "repair_front_header", (0, 3.22, 3.12), (4.78, 0.24, 0.20), "exposed_metal", 0.025)
    for index, x in enumerate((-1.38, 1.38)):
        _box(parts, f"repair_window_reveal_{index}", (x, 1.77, 3.12), (1.18, 1.60, 0.09), "rubber")
        _box(parts, f"repair_window_glass_{index}", (x, 1.77, 3.18), (1.05, 1.43, 0.025), "glass")
        _box(parts, f"repair_window_sill_{index}", (x, 0.91, 3.18), (1.30, 0.10, 0.30), "exposed_metal", 0.015)
        _box(parts, f"repair_window_mullion_{index}", (x, 1.77, 3.20), (0.035, 1.48, 0.03), "painted_metal")
    for x in (-0.74, 0.74):
        _box(parts, f"repair_door_jamb_{x}", (x, 1.06, 3.14), (0.12, 2.12, 0.16), "rust", 0.018)
    _box(parts, "repair_door_lintel", (0, 2.17, 3.14), (1.60, 0.13, 0.16), "exposed_metal", 0.018)
    _box(parts, "retracted_rolling_shutter", (0.55, 1.04, 3.24), (0.22, 1.86, 0.025), "painted_metal", 0.015)
    for slat in range(9):
        _box(parts, f"shutter_slat_{slat}", (0.55, 0.24 + slat * 0.20, 3.26), (0.21, 0.025, 0.009), "exposed_metal")
    return parts


def _housing_facade() -> list[geo.MeshData]:
    parts: list[geo.MeshData] = []
    # Segmented masonry leaves true door/window openings instead of dressing a solid panel.
    openings = ((-0.65, 0.65, 0.0, 2.54), (-2.43, -1.13, 2.40, 3.60), (0.89, 2.19, 2.40, 3.60), (-2.43, -1.13, 5.75, 6.95), (0.89, 2.19, 5.75, 6.95))
    x_edges = sorted({-2.86, 2.86, *(edge for opening in openings for edge in opening[:2])})
    y_edges = sorted({0.0, 8.70, *(edge for opening in openings for edge in opening[2:])})
    for ix, (x0, x1) in enumerate(pairwise(x_edges)):
        for iy, (y0, y1) in enumerate(pairwise(y_edges)):
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if any(lo_x < cx < hi_x and lo_y < cy < hi_y for lo_x, hi_x, lo_y, hi_y in openings):
                continue
            _box(parts, f"housing_masonry_{ix}_{iy}", (cx, cy, 0), (x1 - x0, y1 - y0, 0.23), "concrete")
    # Patched two-storey facade face (front is local -Z) with real reveals and sills.
    _box(parts, "facade_patched_plaster_left", (-1.68, 2.20, -0.125), (2.16, 1.35, 0.025), "patched_concrete", 0.018)
    _box(parts, "facade_painted_patch", (1.67, 5.65, -0.126), (1.78, 1.06, 0.025), "faded_teal", 0.015)
    # Deep window frames, sills, mullions and mismatched shutters on both levels.
    for floor_y in (3.00, 6.35):
        for index, x in enumerate((-1.78, 1.54)):
            _box(parts, f"window_shadow_reveal_{floor_y}_{x}", (x, floor_y, -0.145), (1.30, 1.18, 0.035), "rubber")
            _box(parts, f"window_glazing_{floor_y}_{x}", (x, floor_y, -0.17), (1.13, 1.01, 0.022), "glass")
            for dx in (-0.66, 0.66):
                _box(parts, f"window_jamb_{floor_y}_{x}_{dx}", (x + dx, floor_y, -0.20), (0.10, 1.32, 0.12), "painted_metal", 0.016)
            for dy in (-0.65, 0.65):
                _box(parts, f"window_cross_rail_{floor_y}_{x}_{dy}", (x, floor_y + dy, -0.20), (1.40, 0.10, 0.12), "exposed_metal", 0.012)
            _box(parts, f"window_mullion_{floor_y}_{x}", (x, floor_y, -0.217), (0.045, 1.08, 0.035), "exposed_metal")
            _box(parts, f"window_sill_{floor_y}_{x}", (x, floor_y - 0.72, -0.25), (1.58, 0.10, 0.32), "concrete", 0.018)
            _box(parts, f"shutter_panel_{floor_y}_{x}", (x - 0.58, floor_y, -0.245), (0.17, 1.05, 0.045), "painted_metal", 0.012)
            for slat in range(6):
                _box(parts, f"shutter_slats_{floor_y}_{x}_{slat}", (x - 0.58, floor_y - 0.43 + slat * 0.17, -0.274), (0.18, 0.025, 0.012), "rust")
    # Recessed patched doorway and heavy frame.
    _box(parts, "housing_entry_reveal", (0, 1.26, -0.151), (1.31, 2.56, 0.05), "rubber")
    _box(parts, "entry_door_leaf", (0, 1.22, -0.19), (1.07, 2.36, 0.09), "wood", 0.025)
    for x in (-0.68, 0.68):
        _box(parts, f"entry_door_jamb_{x}", (x, 1.30, -0.23), (0.12, 2.63, 0.16), "exposed_metal", 0.015)
    _box(parts, "entry_door_lintel", (0, 2.62, -0.23), (1.48, 0.14, 0.16), "rust", 0.02)
    _pipe(parts, "door_pull", (0.33, 1.22, -0.245), (0.33, 1.55, -0.245), 0.018, "exposed_metal")
    # Upper improvised balcony, rails, laundry, vented AC compressor and cable additions.
    _box(parts, "upper_ledge", (0, 5.33, -0.37), (4.72, 0.12, 0.72), "concrete", 0.025)
    _pipe(parts, "balcony_top_rail", (-2.26, 6.12, -0.69), (2.26, 6.12, -0.69), 0.026, "rust")
    for x in (-2.25, -1.5, -0.75, 0, 0.75, 1.5, 2.25):
        _pipe(parts, f"balcony_baluster_{x}", (x, 5.40, -0.69), (x, 6.12, -0.69), 0.016, "exposed_metal")
    for index, x in enumerate((-1.5, -0.8, 0.4, 1.1)):
        _pipe(parts, f"laundry_line_{index}", (x, 6.88, -0.33), (x + 0.34, 6.70, -0.36), 0.009, "exposed_metal")
        _box(parts, f"hanging_laundry_{index}", (x + 0.17, 6.45, -0.34), (0.34, 0.42, 0.035), "cloth", 0.012)
    _box(parts, "wall_ac_mount", (2.48, 4.28, -0.27), (0.52, 0.10, 0.38), "exposed_metal", 0.015)
    _box(parts, "wall_ac_body", (2.48, 4.59, -0.30), (0.74, 0.55, 0.42), "cream_plastic", 0.065)
    _cylinder(parts, "wall_ac_fan", (2.48, 4.59, -0.525), 0.18, 0.025, "exposed_metal", 20)
    _cylinder(parts, "wall_ac_fan_hub", (2.48, 4.59, -0.543), 0.045, 0.012, "plastic", 12)
    for vent in range(5):
        _box(parts, f"ac_outlet_louver_{vent}", (2.25 + vent * 0.11, 4.37, -0.52), (0.07, 0.025, 0.018), "exposed_metal")
    # Elbowed downpipe, cleanout, clamps and several real patch scars/cracks.
    _pipe(parts, "downpipe_upper", (2.80, 8.54, 0.10), (2.80, 0.45, 0.10), 0.055, "rust")
    _pipe(parts, "downpipe_elbow", (2.80, 0.45, 0.10), (2.62, 0.27, 0.10), 0.055, "exposed_metal")
    for y in (1.0, 3.0, 5.0, 7.0):
        _box(parts, f"downpipe_clamp_{y}", (2.80, y, -0.02), (0.13, 0.065, 0.18), "painted_metal", 0.018)
    _box(parts, "downpipe_cleanout", (2.68, 0.52, -0.005), (0.16, 0.24, 0.08), "exposed_metal", 0.025)
    cracks = (
        ((-2.63, 4.10, -0.16), (-2.25, 3.78, -0.16), (-2.39, 3.30, -0.16)),
        ((0.92, 7.72, -0.16), (0.66, 7.31, -0.16), (1.11, 6.98, -0.16)),
        ((-0.45, 2.21, -0.16), (-0.16, 1.96, -0.16), (-0.30, 1.60, -0.16)),
    )
    for index, points in enumerate(cracks):
        parts.append(geo.mesh(f"plaster_crack_{index}", points, ((0, 1, 2),), "rust"))
    for index, x in enumerate((-2.2, -1.2, 0.9, 1.8)):
        _box(parts, f"paint_edge_loss_{index}", (x, 0.62 + (index % 2) * 0.15, -0.164), (0.19, 0.045, 0.009), "concrete", 0.004)
    # Roof line additions, patched wiring/conduit and a warm non-flashing wall lamp.
    _box(parts, "roof_edge_cap", (0, 8.72, 0.02), (5.94, 0.18, 0.42), "exposed_metal", 0.02)
    _box(parts, "upper_service_addition", (-2.14, 8.18, 0.17), (1.17, 0.82, 0.42), "patched_concrete", 0.04)
    for cable in range(3):
        _pipe(parts, f"facade_service_cable_{cable}", (-2.75 + cable * 0.10, 8.54, -0.16), (-2.75 + cable * 0.10, 1.1, -0.17), 0.012, "rubber")
    _box(parts, "wall_lamp_backplate", (-2.52, 2.72, -0.29), (0.22, 0.28, 0.08), "painted_metal", 0.025)
    _box(parts, "wall_lamp_glow", (-2.52, 2.70, -0.345), (0.12, 0.19, 0.03), "warm_light", 0.025)
    _box(parts, "housing_nameplate", (0.0, 3.95, -0.30), (0.63, 0.25, 0.035), "wood", 0.018)
    return parts


def _phone() -> list[geo.MeshData]:
    parts: list[geo.MeshData] = []
    # Exact 75 × 8 × 150 mm body, front screen up (+Y), removable rear panel.
    parts.append(geo.beveled_box("phone_shell", (0, 0, 0), (0.075, 0.008, 0.150), 0.0033, "plastic"))
    parts.append(geo.beveled_box("rounded_glass", (0, 0.00355, 0), (0.0705, 0.00065, 0.1455), 0.003, "glass"))
    parts.append(geo.beveled_box("screen_display", (0, 0.00391, 0), (0.063, 0.00012, 0.131), 0.0025, "cool_light"))
    parts.append(geo.beveled_box("removable_back", (0, -0.00354, 0), (0.068, 0.00072, 0.139), 0.003, "faded_teal"))
    # Recess seams make the back cover visibly serviceable.
    for x in (-0.032, 0.032):
        _box(parts, f"back_panel_seam_{x}", (x, -0.00394, 0), (0.0014, 0.00008, 0.118), "exposed_metal")
    for side in (-1, 1):
        _box(parts, f"side_buttons_{side}", (side * 0.0352, 0.0013, 0.024), (0.0020, 0.0014, 0.018), "exposed_metal", 0.00065)
        _box(parts, f"side_button_lower_{side}", (side * 0.0350, 0.0012, -0.005), (0.0018, 0.0011, 0.010), "painted_metal", 0.0005)
    # Raised grouping bezel, ring bezels and lens glass make the rear camera cluster distinct.
    parts.append(geo.beveled_box("camera_cluster", (0, -0.00385, 0.056), (0.053, 0.00025, 0.018), 0.0001, "plastic"))
    _box(parts, "side_buttons", (0.0358, 0.00125, 0.012), (0.0014, 0.0010, 0.027), "exposed_metal", 0.0002)
    for index, (x, z) in enumerate(((-0.021, 0.056), (0.0, 0.056), (0.021, 0.056))):
        _cylinder(parts, f"camera_cluster_ring_{index}", (x, -0.00390, z), 0.006, 0.00016, "exposed_metal", 12)
        _cylinder(parts, f"camera_lens_{index}", (x, -0.00393, z), 0.0037, 0.00008, "glass", 12)
    _cylinder(parts, "camera_flash", (0.026, -0.00391, 0.040), 0.0021, 0.00012, "warm_light", 8)
    _box(parts, "earpiece_grill", (0, 0.00385, 0.0685), (0.018, 0.00012, 0.0018), "exposed_metal", 0.0007)
    _box(parts, "speaker_grill", (0, 0.00385, -0.067), (0.021, 0.00012, 0.0018), "exposed_metal", 0.0007)
    _cylinder(parts, "charging_port", (0, 0, -0.071), 0.0025, 0.0012, "rubber", 8)
    return parts


_BUILDERS = {"food_stall": ("北の立ち食い屋台", _food_stall), "terminal_repair": ("端末修理・トロン中古店", _repair_shop), "patched_housing_facade": ("補修跡のある増築長屋正面", _housing_facade), "pocket_phone": ("修理台のポケットロン", _phone)}


def create(kind: str, origin: tuple[float, float, float], rotation: float = 0) -> Assembly:
    """Create a named, functional mesh assembly at Resonite ``origin`` and yaw ``rotation``.

    ``origin`` is in Resonite meters (XYZ, Y up); ``rotation`` is radians around world-up.
    Supported kinds are ``food_stall``, ``terminal_repair``, ``patched_housing_facade`` and
    ``pocket_phone``. Assemblies expose individually named editable ``MeshData`` parts.
    """
    if kind not in _BUILDERS:
        raise ValueError(f"unsupported detailed prop kind: {kind}")
    if len(origin) != 3:
        raise ValueError("origin must contain three coordinates")
    name, builder = _BUILDERS[kind]
    parts = builder()
    if not parts or any(not part.vertices or not part.faces for part in parts):
        raise RuntimeError(f"asset builder {kind} produced empty geometry")
    return Assembly(kind, name, tuple(float(value) for value in origin), float(rotation), parts)  # type: ignore[arg-type]


def modeled_kinds() -> tuple[str, ...]:
    """List reusable kinds built by ``create`` in stable order."""
    return tuple(_BUILDERS)
