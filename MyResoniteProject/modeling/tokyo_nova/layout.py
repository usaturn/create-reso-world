"""Deterministic spatial source for the Tokyo Nova West Slum blockout."""

from __future__ import annotations

from typing import Any

SEED = 240918
ROOT_TRANSFORM = {
    "position": [0.0, 30.0, 120.0],
    "rotation": [0.0, 0.0, 0.0, 1.0],
    "scale": [1.0, 1.0, 1.0],
}
PLAZA_BOUNDS_XZ = [-10.0, 10.0, -10.0, 10.0]

_BUILDING_ROWS = (
    ("north_yatai", "food_stall", -35, 15, 7, 6, 5, "south"),
    ("north_terminal_repair", "repair_shop", -25, 15, 7, 6, 6, "south"),
    ("north_machiya", "mixed_use", -15, 15, 6, 6, 9, "south"),
    ("north_laundry", "laundry", 15, 15, 6, 6, 5, "south"),
    ("north_night_market", "market", 25, 15, 7, 6, 7, "south"),
    ("north_learning_room", "learning_room", 35, 15, 8, 6, 8, "south"),
    ("east_clinic", "clinic", 15, -35, 6, 7, 8, "west"),
    ("east_rowhouse_a", "rowhouse", 15, -25, 6, 6, 6, "west"),
    ("east_rowhouse_b", "rowhouse", 15, -15, 6, 6, 7, "west"),
    ("east_public_bath", "public_bath", 15, 5, 6, 6, 6, "west"),
    ("east_housing_coop", "housing_coop", 15, 25, 6, 6, 10, "west"),
    ("east_roof_garden", "roof_utility_deck", 15, 35, 6, 7, 7, "west"),
    ("south_repair_yard", "repair_yard", -35, -15, 8, 6, 6, "north"),
    ("south_machine_shop", "machine_shop", -25, -15, 7, 6, 7, "north"),
    ("south_theatre", "underground_theatre", -15, -15, 6, 6, 8, "north"),
    ("south_rehearsal", "clothing_repair", 35, -35, 6, 6, 6, "north"),
    ("south_reclaimed_warehouse", "warehouse", 25, -15, 8, 6, 9, "north"),
    ("south_battery_shop", "battery_shop", 35, -15, 8, 6, 6, "north"),
    ("west_basement_bar", "basement_bar", -15, -35, 6, 7, 6, "east"),
    ("west_salvage_depot", "salvage_depot", -15, -25, 6, 6, 7, "east"),
    ("west_talisman_shop", "talisman_shop", -35, -25, 6, 6, 5, "west"),
    ("west_game_room", "game_room", -25, -35, 6, 6, 6, "south"),
    ("west_shared_kitchen", "shared_kitchen", -15, 25, 6, 6, 5, "east"),
    ("west_roof_access", "roof_access_block", -15, 35, 6, 7, 9, "east"),
)

_FACILITIES = (
    ("eatery", "立ち食い「雨粒」", "food", "north_yatai"),
    ("terminal_repair", "端末修理・はんだ台", "repair", "north_terminal_repair"),
    ("laundry", "共同洗濯場", "daily_service", "north_laundry"),
    ("night_market", "夜間食料棚", "retail", "north_night_market"),
    ("learning_room", "支援学習室", "community", "north_learning_room"),
    ("clinic", "夜間診療室", "health", "east_clinic"),
    ("public_bath", "共同浴場", "daily_service", "east_public_bath"),
    ("housing_coop", "寄り合い長屋", "housing", "east_housing_coop"),
    ("repair_yard", "補修・溶接ヤード", "workshop", "south_repair_yard"),
    ("machine_shop", "小型機械工房", "workshop", "south_machine_shop"),
    ("underground_theatre", "地下小劇場", "culture", "south_theatre"),
    ("reclaimed_warehouse", "転用倉庫", "storage", "south_reclaimed_warehouse"),
    ("battery_shop", "蓄電池交換所", "utility", "south_battery_shop"),
    ("basement_bar", "地下酒場「余白」", "food", "west_basement_bar"),
    ("salvage_depot", "再生材置場", "recycling", "west_salvage_depot"),
    ("talisman_shop", "お守りと修繕糸", "retail", "west_talisman_shop"),
    ("game_room", "中古ゲーム卓", "recreation", "west_game_room"),
    ("shared_kitchen", "共同炊事場", "community", "west_shared_kitchen"),
    ("clothing_repair", "古着仕立て・縫い直し", "repair", "south_rehearsal"),
)

_PROP_CATALOG = (
    "folding_steel_shutter", "corrugated_awning_frame", "canvas_awning", "rain_gutter",
    "downpipe_elbow", "roof_water_tank", "water_filter_canister", "pressure_gauge",
    "patch_cable_tray", "junction_box", "ceramic_fuse_holder", "battery_rack",
    "solar_charge_controller", "wall_mount_fan", "ventilation_duct", "exhaust_cowl",
    "shop_counter", "handwritten_menu_board", "stackable_food_tray", "portable_gas_burner",
    "steel_stockpot", "rice_container", "folding_service_table", "reusable_food_cover",
    "soldering_station", "hot_air_rework_tool", "bench_power_supply", "oscilloscope",
    "component_drawer", "anti_static_mat", "surgical_lamp", "medicine_cabinet",
    "privacy_screen_track", "folding_exam_couch", "laundry_wringer", "detergent_drum",
    "clothes_rail", "drain_grate", "utility_sink", "workbench_vise",
    "angle_grinder_guard", "welding_curtain_frame", "compressed_air_regulator", "tool_shadow_board",
    "salvage_sorting_bin", "hand_cart", "pallet_rack", "weighing_scale",
    "theatre_programme_rack", "fixed_projection_screen_frame", "blackout_curtain_track", "theatre_acoustic_baffles",
    "barrel_table", "under_counter_cooler", "bottle_crate", "game_cartridge_case",
    "arcade_control_panel", "repairable_bicycle_stand", "folding_rain_screen", "roof_drain_filter_basket",
    "stair_landing_handrail", "emergency_ladder_cage", "basement_sump_pump", "inspection_hatch",
    "theatre_floor_seating", "fixed_projection_shelf", "sound_absorbing_door_seal", "roof_service_cable_tray",
    "north_patched_housing_facade", "secondhand_terminal_repair_assembly", "pocket_phone",
    "reusable_cfc_food_container", "north_ar_menu_surface", "north_corrugated_food_awning",
)


def _world_point(local: tuple[float, float, float]) -> list[float]:
    return [local[index] + ROOT_TRANSFORM["position"][index] for index in range(3)]


def build_layout() -> dict[str, Any]:
    """Return stable, JSON-compatible layout data in root-local Resonite coordinates."""
    buildings = [
        {
            "key": key,
            "kind": kind,
            "center": [float(x), 0.0, float(z)],
            "size": [float(width), float(depth)],
            "height": float(height),
            "front": front,
        }
        for key, kind, x, z, width, depth, height, front in _BUILDING_ROWS
    ]
    building_by_key = {building["key"]: building for building in buildings}
    facilities = [
        {
            "key": key,
            "name": name,
            "kind": kind,
            "building_key": building_key,
            "position": list(building_by_key[building_key]["center"]),
        }
        for key, name, kind, building_key in _FACILITIES
    ]
    routes = [
        {"key": "entrance_north", "kind": "entrance", "width": 3.5, "points": [[7, 0, 48], [7, 0, 26], [7, 0, 10]], "side": "north"},
        {"key": "entrance_east", "kind": "entrance", "width": 3.5, "points": [[48, 0, -7], [26, 0, -7], [10, 0, -7]], "side": "east"},
        {"key": "entrance_south", "kind": "entrance", "width": 3.5, "points": [[-7, 0, -48], [-7, 0, -26], [-7, 0, -10]], "side": "south"},
        {"key": "entrance_west", "kind": "entrance", "width": 3.5, "points": [[-48, 0, 7], [-26, 0, 7], [-10, 0, 7]], "side": "west"},
        {"key": "main_north_south", "kind": "main", "width": 3.5, "points": [[0, 0, 48], [0, 0, -48]]},
        {"key": "main_east_west", "kind": "main", "width": 3.5, "points": [[-48, 0, 0], [48, 0, 0]]},
        {"key": "loop_outer", "kind": "main", "width": 3.5, "loop": True, "points": [[-48, 0, -48], [48, 0, -48], [48, 0, 48], [-48, 0, 48], [-48, 0, -48]]},
        {"key": "loop_midwest", "kind": "alley", "width": 2.0, "loop": True, "points": [[-34, 0, -5], [-34, 0, 5], [-18, 0, 5], [-18, 0, -5], [-34, 0, -5]]},
        {"key": "alley_northwest", "kind": "alley", "width": 2.0, "points": [[-40, 0, 24], [-18, 0, 24]]},
        {"key": "alley_southeast", "kind": "alley", "width": 2.0, "points": [[18, 0, -24], [40, 0, -24]]},
        {"key": "alley_northfront", "kind": "alley", "width": 1.5, "points": [[-46, 0, 10.9], [46, 0, 10.9]]},
        {"key": "alley_southfront", "kind": "alley", "width": 1.5, "points": [[-46, 0, -10.9], [46, 0, -10.9]]},
        {"key": "alley_eastfront", "kind": "alley", "width": 1.5, "points": [[10.9, 0, -46], [10.9, 0, 46]]},
        {"key": "alley_westfront", "kind": "alley", "width": 1.5, "points": [[-10.9, 0, -46], [-10.9, 0, 46]]},
        {"key": "alley_south_rehearsal_access", "kind": "alley", "width": 1.5, "points": [[35, 0, -24], [35, 0, -32]], "building_access_key": "south_rehearsal"},
        {"key": "alley_west_game_room_access", "kind": "alley", "width": 1.5, "points": [[-25, 0, -48], [-25, 0, -38]], "building_access_key": "west_game_room"},
        {"key": "alley_west_talisman_shop_access", "kind": "alley", "width": 1.5, "points": [[-48, 0, -25], [-38, 0, -25]], "building_access_key": "west_talisman_shop"},
    ]
    local_cameras = (
        ("plaza_north_eye", (6, 1.6, 28), (0, 1.1, 0)),
        ("plaza_south_eye", (-6, 1.6, -28), (0, 1.1, 0)),
        ("west_entry_eye", (-28, 1.6, 6), (0, 1.1, 0)),
        ("east_entry_eye", (28, 1.6, -6), (0, 1.1, 0)),
        ("roof_overlook", (-15, 10.71, 35), (0, 2, 0)),
        ("north_market_detail", (14, 1.6, 11), (25, 3, 15)),
        ("south_workshop_detail", (-5, 1.6, -11), (-25, 3, -15)),
        ("street_overview", (44, 18, 44), (0, 3, 0)),
    )
    return {
        "schema_version": 1,
        "seed": SEED,
        "coordinate_system": {
            "world_axes": "Resonite XYZ (X right, Y up, Z depth)",
            "layout_positions": "root-local Resonite meters",
            "blender_conversion": "(x, y, z) -> (x, z, y) at Blender generation boundary only",
        },
        "root": {
            "key": "tokyo_nova_west_slum",
            "name": "TokyoNova_WestSlum",
            "transform": ROOT_TRANSFORM,
            "world_ground_alignment": "Root world Y=30 preserves root-local plaza Y=0 and keeps basement depths clear of existing Ground",
        },
        "plaza": {
            "bounds_xz": list(PLAZA_BOUNDS_XZ),
            "level_y": 0.0,
            "clear_area_m2": 400.0,
            "surface": "continuous_plaza_floor",
        },
        "districts": {
            "north": "street food, terminal repair, shared services and learning support",
            "east": "housing, night clinic and daily care",
            "south": "repair yards, machine shop and underground theatre",
            "west": "basement bar, salvage, talisman repair and recreation",
        },
        "buildings": buildings,
        "routes": routes,
        "facilities": facilities,
        "roof_access": {"building_key": "west_roof_access", "kind": "external_walkable_ramp_to_roof_landing", "clear_width": 1.8, "target_height": 9.11},
        "basement_access": [
            {
                "key": "south_theatre_basement_ramp", "building_key": "south_theatre", "kind": "open_ramp_and_landing",
                "entry_side": "north", "clear_width": 1.8, "depth_below_grade": 2.4, "approach_run": 5.0,
                "floor_opening": {"axis": "z", "center": [0.0, 0.5], "size": [1.8, 5.0], "depth": 5.0}, "floor_key_prefix": "theatre",
                "landing_key": "theatre_basement_landing", "landing_center_offset": [0.0, -2.0], "landing_size": [2.4, 2.4]
            },
            {
                "key": "west_bar_basement_stairs", "building_key": "west_basement_bar", "kind": "open_stairwell_and_landing",
                "entry_side": "east", "clear_width": 1.5, "depth_below_grade": 2.2, "approach_run": 3.0, "steps": 12,
                "floor_opening": {"axis": "x", "center": [1.5, 0.0], "size": [3.0, 1.8], "depth": 3.0}, "floor_key_prefix": "bar",
                "landing_key": "bar_basement_landing", "landing_center_offset": [-1.2, 0.0], "landing_size": [2.4, 2.2]
            },
        ],
        "prop_catalog": [{"key": name, "kind": name} for name in _PROP_CATALOG],
        "cameras": [
            {
                "key": key,
                "position": _world_point(position),
                "target": _world_point(target),
                "coordinate_space": "world",
                "local_position": list(position),
                "local_target": list(target),
            }
            for key, position, target in local_cameras
        ],
    }



def _footprint(building: dict[str, Any]) -> tuple[float, float, float, float]:
    x, _y, z = building["center"]
    width, depth = building["size"]
    return (x - width / 2, x + width / 2, z - depth / 2, z + depth / 2)


def _intervals_overlap(first_min: float, first_max: float, second_min: float, second_max: float) -> bool:
    return first_min < second_max - 1e-8 and second_min < first_max - 1e-8


def _route_segment_intersects_building(start: list[float], end: list[float], width: float, building: dict[str, Any]) -> bool:
    xmin, xmax, zmin, zmax = _footprint(building)
    dx, dz = float(end[0] - start[0]), float(end[2] - start[2])
    if abs(dx) < 1e-8:
        # A north/south path has width along X; its endpoints do not extend longitudinally.
        return (
            xmin - width / 2 < start[0] < xmax + width / 2
            and _intervals_overlap(min(start[2], end[2]), max(start[2], end[2]), zmin, zmax)
        )
    if abs(dz) < 1e-8:
        # An east/west path has width along Z; its endpoints do not extend longitudinally.
        return (
            zmin - width / 2 < start[2] < zmax + width / 2
            and _intervals_overlap(min(start[0], end[0]), max(start[0], end[0]), xmin, xmax)
        )
    # Current source routes are axis aligned. Keep a conservative fallback for future diagonals.
    bounds = (xmin - width / 2, xmax + width / 2, zmin - width / 2, zmax + width / 2)
    t_min, t_max = 0.0, 1.0
    for origin, delta, low, high in ((start[0], dx, bounds[0], bounds[1]), (start[2], dz, bounds[2], bounds[3])):
        if abs(delta) < 1e-8:
            if not low < origin < high:
                return False
            continue
        enter, leave = (low - origin) / delta, (high - origin) / delta
        t_min = max(t_min, min(enter, leave))
        t_max = min(t_max, max(enter, leave))
    return t_min < t_max - 1e-8


def _front_door(building: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float]]:
    x, _y, z = building["center"]
    width, depth = building["size"]
    front = building["front"]
    if front == "north":
        return (x, z + depth / 2), (0.0, 1.0)
    if front == "south":
        return (x, z - depth / 2), (0.0, -1.0)
    if front == "east":
        return (x + width / 2, z), (1.0, 0.0)
    if front == "west":
        return (x - width / 2, z), (-1.0, 0.0)
    raise ValueError(f"building {building.get('key', '<unknown>')} has invalid front {front!r}")


def _route_reaches_front_door(building: dict[str, Any], route: dict[str, Any]) -> bool:
    door, normal = _front_door(building)
    for start, end in zip(route.get("points", []), route.get("points", [])[1:]):
        sx, sz = float(start[0]), float(start[2])
        dx, dz = float(end[0]) - sx, float(end[2]) - sz
        length_squared = dx * dx + dz * dz
        t = 0.0 if length_squared == 0 else max(0.0, min(1.0, ((door[0] - sx) * dx + (door[1] - sz) * dz) / length_squared))
        nearest = (sx + t * dx, sz + t * dz)
        offset = (nearest[0] - door[0], nearest[1] - door[1])
        outward = offset[0] * normal[0] + offset[1] * normal[1]
        sideways = offset[0] * -normal[1] + offset[1] * normal[0]
        if -1e-6 <= outward <= 2.5 and abs(sideways) <= 0.6 + float(route["width"]) / 2:
            return True
    return False


def _route_ends_at_front_door(building: dict[str, Any], route: dict[str, Any]) -> bool:
    if not route.get("points"):
        return False
    door, _normal = _front_door(building)
    endpoint = route["points"][-1]
    return abs(float(endpoint[0]) - door[0]) <= 1e-6 and abs(float(endpoint[2]) - door[1]) <= 1e-6


def _door_clearance_overlaps_building(building: dict[str, Any], other: dict[str, Any]) -> bool:
    (door_x, door_z), (normal_x, normal_z) = _front_door(building)
    half_width, depth = 0.6, 2.5
    if normal_x:
        corridor = (door_x, door_x + normal_x * depth, door_z - half_width, door_z + half_width)
        xmin, xmax = sorted(corridor[:2])
        zmin, zmax = corridor[2:]
    else:
        corridor = (door_x - half_width, door_x + half_width, door_z, door_z + normal_z * depth)
        xmin, xmax = corridor[:2]
        zmin, zmax = sorted(corridor[2:])
    oxmin, oxmax, ozmin, ozmax = _footprint(other)
    return _intervals_overlap(xmin, xmax, oxmin, oxmax) and _intervals_overlap(zmin, zmax, ozmin, ozmax)

def validate_layout(layout: dict[str, Any]) -> list[str]:
    """Return human-readable violations of the spatial and ownership invariants."""
    errors: list[str] = []
    root_position = layout.get("root", {}).get("transform", {}).get("position")
    root_transform = layout.get("root", {}).get("transform", {})
    if root_position != [0.0, 30.0, 120.0]:
        errors.append("owned root world placement must remain [0, 30, 120]")
    if root_transform.get("rotation") != [0.0, 0.0, 0.0, 1.0] or root_transform.get("scale") != [1.0, 1.0, 1.0]:
        errors.append("owned root must retain identity rotation and unit scale")
    if layout.get("plaza", {}).get("bounds_xz") != PLAZA_BOUNDS_XZ:
        errors.append(f"plaza bounds must remain {PLAZA_BOUNDS_XZ}")
    buildings = layout.get("buildings", [])
    if len(buildings) != 24:
        errors.append(f"expected 24 buildings, found {len(buildings)}")
    for building in buildings:
        try:
            x, _y, z = building["center"]
            width, depth = building["size"]
            xmin, xmax = x - width / 2, x + width / 2
            zmin, zmax = z - depth / 2, z + depth / 2
        except (KeyError, TypeError, ValueError):
            errors.append(f"building {building.get('key', '<unknown>')} has invalid footprint data")
            continue
        if xmin < 10 and xmax > -10 and zmin < 10 and zmax > -10:
            errors.append(f"building {building.get('key', '<unknown>')} intrudes into the clear plaza")
        if width <= 0 or depth <= 0 or building.get("height", 0) <= 0:
            errors.append(f"building {building.get('key', '<unknown>')} dimensions must be positive")

    for index, first in enumerate(buildings):
        for second in buildings[index + 1 :]:
            try:
                ax0, ax1, az0, az1 = _footprint(first)
                bx0, bx1, bz0, bz1 = _footprint(second)
            except (KeyError, TypeError, ValueError):
                continue
            if _intervals_overlap(ax0, ax1, bx0, bx1) and _intervals_overlap(az0, az1, bz0, bz1):
                errors.append(f"building footprints overlap: {first.get('key')} and {second.get('key')}")

    routes = layout.get("routes", [])
    entrances = [route for route in routes if route.get("kind") == "entrance"]
    loops = [route for route in routes if route.get("loop") is True]
    if len(entrances) != 4:
        errors.append(f"expected four offset entrances, found {len(entrances)}")
    if len(loops) < 2:
        errors.append(f"expected at least two loops, found {len(loops)}")
    for route in routes:
        width = route.get("width")
        if not isinstance(width, (int, float)) or width <= 0:
            errors.append(f"route {route.get('key', '<unknown>')} width must be positive")
            continue
        if route.get("kind") == "main" and not 3 <= width <= 4:
            errors.append(f"main route {route.get('key', '<unknown>')} width must be 3–4m")
        if route.get("kind") == "alley" and not 1.5 <= width <= 2.5:
            errors.append(f"alley {route.get('key', '<unknown>')} width must be 1.5–2.5m")
        if len(route.get("points", [])) < 2:
            errors.append(f"route {route.get('key', '<unknown>')} needs at least two points")
        target_key = route.get("building_access_key")
        target = next((building for building in buildings if building.get("key") == target_key), None)
        if target_key and target is None:
            errors.append(f"route {route.get('key')} targets unknown building {target_key}")
        elif target is not None and not _route_ends_at_front_door(target, route):
            errors.append(f"route {route.get('key')} does not terminate at {target_key}'s front door")
        for start, end in zip(route.get("points", []), route.get("points", [])[1:]):
            for building in buildings:
                if _route_segment_intersects_building(start, end, float(width), building):
                    errors.append(f"route {route.get('key')} intersects building {building.get('key')}")

    for building in buildings:
        try:
            _front_door(building)
        except (KeyError, TypeError, ValueError):
            errors.append(f"building {building.get('key', '<unknown>')} has invalid front-door data")
            continue
        if not any(_route_reaches_front_door(building, route) for route in routes):
            errors.append(f"building {building.get('key')} has no clear front door approach")
        for other in buildings:
            if other is not building and _door_clearance_overlaps_building(building, other):
                errors.append(f"front door approach for {building.get('key')} is blocked by {other.get('key')}")

    for access in layout.get("basement_access", []):
        building = next((item for item in buildings if item.get("key") == access.get("building_key")), None)
        if building is None:
            errors.append(f"basement access {access.get('key')} references an unknown building")
            continue
        if access.get("entry_side") != building.get("front"):
            errors.append(f"basement access {access.get('key')} must enter through the building front")
        run = access.get("approach_run")
        depth = access.get("depth_below_grade")
        opening = access.get("floor_opening", {})
        if not isinstance(run, (int, float)) or run <= 0 or not isinstance(depth, (int, float)) or depth <= 0:
            errors.append(f"basement access {access.get('key')} must declare positive run and depth")
        elif opening.get("depth") != run:
            errors.append(f"basement access {access.get('key')} floor opening must span its declared approach run")
        if opening.get("axis") not in ("x", "z") or len(opening.get("size", [])) != 2:
            errors.append(f"basement access {access.get('key')} has invalid floor-opening geometry")

    facilities = layout.get("facilities", [])
    if len(facilities) < 12:
        errors.append(f"expected at least 12 facilities, found {len(facilities)}")
    keys = [entry.get("key") for group in (buildings, routes, facilities) for entry in group]
    if len(keys) != len(set(keys)):
        errors.append("building, route and facility keys must be distinct")
    building_keys = {building.get("key") for building in buildings}
    for facility in facilities:
        if facility.get("building_key") not in building_keys:
            errors.append(f"facility {facility.get('key', '<unknown>')} references an unknown building")

    if len(layout.get("prop_catalog", [])) < 60:
        errors.append("prop_catalog must contain at least 60 functionally distinct kinds")
    cameras = layout.get("cameras", [])
    if not cameras:
        errors.append("at least one camera bookmark is required")
    for camera in cameras:
        if camera.get("coordinate_space") != "world":
            errors.append(f"camera {camera.get('key', '<unknown>')} must use world coordinates")
        for member in ("position", "target"):
            if len(camera.get(member, [])) != 3:
                errors.append(f"camera {camera.get('key', '<unknown>')} {member} must be a 3D point")
    return errors
