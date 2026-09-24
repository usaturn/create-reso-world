"""Deterministic spatial source for the Tokyo Nova West Slum blockout."""

from __future__ import annotations

from typing import Any

SEED = 240918
ROOT_TRANSFORM = {
    "position": [0.0, 0.0, 120.0],
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
    ("east_public_bath", "public_bath", 15, 15, 6, 6, 6, "west"),
    ("east_housing_coop", "housing_coop", 15, 25, 6, 6, 10, "west"),
    ("east_roof_garden", "roof_garden", 15, 35, 6, 7, 7, "west"),
    ("south_repair_yard", "repair_yard", -35, -15, 8, 6, 6, "north"),
    ("south_machine_shop", "machine_shop", -25, -15, 7, 6, 7, "north"),
    ("south_theatre", "underground_theatre", -15, -15, 6, 6, 8, "north"),
    ("south_rehearsal", "rehearsal_room", 15, -15, 6, 6, 6, "north"),
    ("south_reclaimed_warehouse", "warehouse", 25, -15, 8, 6, 9, "north"),
    ("south_battery_shop", "battery_shop", 35, -15, 8, 6, 6, "north"),
    ("west_basement_bar", "basement_bar", -15, -35, 6, 7, 6, "east"),
    ("west_salvage_depot", "salvage_depot", -15, -25, 6, 6, 7, "east"),
    ("west_talisman_shop", "talisman_shop", -15, -15, 6, 6, 5, "east"),
    ("west_game_room", "game_room", -15, 15, 6, 6, 6, "east"),
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
)

_PROP_CATALOG = (
    "folding_steel_shutter", "corrugated_awning_frame", "canvas_awning", "rain_gutter",
    "downpipe_elbow", "roof_water_tank", "water_filter_canister", "pressure_gauge",
    "patch_cable_tray", "junction_box", "ceramic_fuse_holder", "battery_rack",
    "solar_charge_controller", "wall_mount_fan", "ventilation_duct", "exhaust_cowl",
    "shop_counter", "ticket_dispenser", "coin_return_mechanism", "handwritten_menu_board",
    "stackable_food_tray", "portable_gas_burner", "steel_stockpot", "rice_container",
    "soldering_station", "hot_air_rework_tool", "bench_power_supply", "oscilloscope",
    "component_drawer", "anti_static_mat", "surgical_lamp", "medicine_cabinet",
    "privacy_screen_track", "folding_exam_couch", "laundry_wringer", "detergent_drum",
    "clothes_rail", "drain_grate", "utility_sink", "workbench_vise",
    "angle_grinder_guard", "welding_curtain_frame", "compressed_air_regulator", "tool_shadow_board",
    "salvage_sorting_bin", "hand_cart", "pallet_rack", "weighing_scale",
    "theatre_ticket_window", "stage_truss", "blackout_curtain_track", "floor_monitor_speaker",
    "barrel_table", "under_counter_cooler", "bottle_crate", "game_cartridge_case",
    "arcade_control_panel", "repairable_bicycle_stand", "folding_rain_screen", "roof_planter_trough",
    "stair_landing_handrail", "emergency_ladder_cage", "basement_sump_pump", "inspection_hatch",
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
        {"key": "loop_midwest", "kind": "alley", "width": 2.0, "loop": True, "points": [[-34, 0, -5], [-34, 0, 5], [-5, 0, 5], [-5, 0, -5], [-34, 0, -5]]},
        {"key": "alley_northwest", "kind": "alley", "width": 2.0, "points": [[-40, 0, 24], [-18, 0, 24]]},
        {"key": "alley_southeast", "kind": "alley", "width": 2.0, "points": [[18, 0, -24], [40, 0, -24]]},
        {"key": "alley_northfront", "kind": "alley", "width": 1.5, "points": [[-46, 0, 10.9], [46, 0, 10.9]]},
        {"key": "alley_southfront", "kind": "alley", "width": 1.5, "points": [[-46, 0, -10.9], [46, 0, -10.9]]},
        {"key": "alley_eastfront", "kind": "alley", "width": 1.5, "points": [[10.9, 0, -46], [10.9, 0, 46]]},
        {"key": "alley_westfront", "kind": "alley", "width": 1.5, "points": [[-10.9, 0, -46], [-10.9, 0, 46]]},
    ]
    local_cameras = (
        ("plaza_north_eye", (6, 1.6, 28), (0, 1.1, 0)),
        ("plaza_south_eye", (-6, 1.6, -28), (0, 1.1, 0)),
        ("west_entry_eye", (-28, 1.6, 6), (0, 1.1, 0)),
        ("east_entry_eye", (28, 1.6, -6), (0, 1.1, 0)),
        ("roof_overlook", (-15, 9, 35), (0, 2, 0)),
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
            "world_ground_alignment": "Root Y=0 aligns plaza and street finish with observed Ground Y=0",
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
        "roof_access": {"building_key": "west_roof_access", "kind": "external_walkable_ramp_to_roof_landing", "clear_width": 1.8, "target_height": 9.0},
        "basement_access": [
            {"key": "south_theatre_basement_ramp", "building_key": "south_theatre", "kind": "open_ramp_and_landing", "clear_width": 1.8, "depth_below_grade": 2.4},
            {"key": "west_bar_basement_stairs", "building_key": "west_basement_bar", "kind": "open_stairwell_and_landing", "clear_width": 1.5, "depth_below_grade": 2.2},
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


def validate_layout(layout: dict[str, Any]) -> list[str]:
    """Return human-readable violations of the spatial and ownership invariants."""
    errors: list[str] = []
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
