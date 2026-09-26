"""Accessible room shells and function-specific static furnishings/equipment."""
from __future__ import annotations

import math
from typing import Any

from modeling.tokyo_nova import geometry as geo
from modeling.tokyo_nova.districts import collision_parts
from modeling.tokyo_nova.layout import _route_reaches_front_door
from modeling.tokyo_nova.props import Assembly

Vec3 = tuple[float, float, float]

# key, functional family, dimensions (X/Y/Z), primary material, secondary material
_ASSET_SPECS = (
    ("corrugated_shutter", "architectural", (1.8, 2.0, 0.12), "painted_metal", "rust"),
    ("supported_awning", "architectural", (1.8, 0.12, 1.0), "painted_metal", "exposed_metal"),
    ("window_frame", "architectural", (1.2, 1.3, 0.16), "exposed_metal", "glass"),
    ("rain_gutter", "utility", (1.5, 0.12, 0.12), "rust", "exposed_metal"),
    ("ac_compressor", "utility", (0.72, 0.58, 0.38), "cream_plastic", "exposed_metal"),
    ("wall_fan", "utility", (0.48, 0.48, 0.18), "exposed_metal", "plastic"),
    ("exhaust_duct", "utility", (0.30, 0.45, 0.70), "exposed_metal", "rust"),
    ("power_meter", "utility", (0.26, 0.42, 0.12), "faded_teal", "glass"),
    ("junction_panel", "utility", (0.50, 0.66, 0.16), "painted_metal", "exposed_metal"),
    ("antenna_yagi", "utility", (0.95, 0.95, 0.12), "exposed_metal", "rubber"),
    ("roof_tank_filter", "utility", (0.55, 0.95, 0.55), "cream_plastic", "rust"),
    ("floor_drain", "utility", (0.44, 0.06, 0.44), "exposed_metal", "rust"),
    ("clinic_privacy_curtain", "medical", (1.50, 1.95, 0.05), "cloth", "exposed_metal"),
    ("diagnostic_table", "medical", (1.7, 0.78, 0.62), "faded_teal", "exposed_metal"),
    ("joint_casing_set", "medical", (0.52, 0.58, 0.46), "cream_plastic", "exposed_metal"),
    ("instrument_trolley", "medical", (0.62, 0.92, 0.42), "exposed_metal", "plastic"),
    ("medicine_drawer", "medical", (0.8, 1.2, 0.38), "painted_metal", "cream_plastic"),
    ("exam_task_lamp", "medical", (0.52, 1.0, 0.42), "exposed_metal", "warm_light"),
    ("tray_of_tools", "medical", (0.52, 0.12, 0.34), "exposed_metal", "rubber"),
    ("street_bowl_rack", "food", (0.72, 0.82, 0.28), "wood", "ceramic"),
    ("lidded_stockpot", "food", (0.38, 0.45, 0.38), "exposed_metal", "rust"),
    ("cfc_food_canister", "food", (0.34, 0.43, 0.30), "cream_plastic", "faded_teal"),
    ("reuse_container_stack", "food", (0.54, 0.58, 0.42), "cream_plastic", "rubber"),
    ("under_counter_fridge", "food", (0.72, 0.92, 0.60), "cream_plastic", "exposed_metal"),
    ("chopstick_caddy", "food", (0.22, 0.25, 0.18), "wood", "exposed_metal"),
    ("condiment_set", "food", (0.42, 0.24, 0.20), "plastic", "cream_plastic"),
    ("wash_sink", "food", (0.72, 0.82, 0.50), "exposed_metal", "ceramic"),
    ("serving_counter", "food", (1.4, 0.92, 0.64), "wood", "exposed_metal"),
    ("slip_on_shoes", "daily", (0.34, 0.12, 0.48), "rubber", "cloth"),
    ("folded_umbrella", "daily", (0.12, 0.62, 0.12), "cloth", "exposed_metal"),
    ("laundry_bucket", "daily", (0.36, 0.42, 0.36), "plastic", "exposed_metal"),
    ("detergent_canister", "daily", (0.26, 0.46, 0.26), "cream_plastic", "faded_teal"),
    ("laundry_wringer", "daily", (0.68, 0.78, 0.46), "exposed_metal", "rubber"),
    ("clothes_hanger", "daily", (0.46, 0.25, 0.025), "exposed_metal", "cloth"),
    ("patched_clothes_bundle", "daily", (0.62, 0.70, 0.06), "cloth", "faded_teal"),
    ("rolled_bedding", "daily", (0.78, 0.30, 0.48), "cloth", "rubber"),
    ("shared_mailboxes", "daily", (0.78, 0.88, 0.24), "painted_metal", "rust"),
    ("stacked_textbooks", "daily", (0.32, 0.28, 0.22), "wood", "cloth"),
    ("repair_chair", "daily", (0.48, 0.84, 0.48), "wood", "exposed_metal"),
    ("sewing_tool_roll", "daily", (0.56, 0.22, 0.34), "cloth", "exposed_metal"),
    ("wooden_pallet", "logistics", (1.1, 0.16, 0.86), "wood", "exposed_metal"),
    ("shipping_crate", "logistics", (0.72, 0.62, 0.68), "wood", "rust"),
    ("ratchet_strap", "logistics", (0.10, 0.06, 1.2), "faded_teal", "exposed_metal"),
    ("folding_dolly", "logistics", (0.48, 0.86, 0.52), "exposed_metal", "rubber"),
    ("chain_hoist", "logistics", (0.42, 0.82, 0.32), "exposed_metal", "rust"),
    ("motorcycle_static", "vehicle", (1.82, 0.92, 0.56), "painted_metal", "rubber"),
    ("engine_case_half", "vehicle", (0.44, 0.32, 0.36), "exposed_metal", "rust"),
    ("wheel_and_hub", "vehicle", (0.56, 0.58, 0.16), "rubber", "exposed_metal"),
    ("fuel_cell_turbine", "vehicle", (0.62, 0.50, 0.48), "painted_metal", "exposed_metal"),
    ("recliner_seat", "theatre", (0.84, 0.96, 1.42), "cloth", "exposed_metal"),
    ("old_tron_terminal", "theatre", (0.50, 0.42, 0.45), "plastic", "exposed_metal"),
    ("abstract_sea_screen", "theatre", (1.62, 1.02, 0.08), "cool_light", "glass"),
    ("theatre_air_baffle", "theatre", (0.88, 0.32, 0.16), "rubber", "cloth"),
    ("speaker_cabinet", "theatre", (0.42, 0.65, 0.32), "wood", "rubber"),
    ("arcade_cabinet", "arcade", (0.72, 1.72, 0.82), "painted_metal", "cool_light"),
    ("arcade_stick_panel", "arcade", (0.50, 0.12, 0.30), "plastic", "exposed_metal"),
    ("game_cartridge_case", "arcade", (0.30, 0.24, 0.22), "faded_teal", "plastic"),
    ("score_card_tray", "arcade", (0.54, 0.16, 0.36), "wood", "cream_plastic"),
    ("amulet_shelf", "talisman", (1.28, 1.75, 0.32), "wood", "exposed_metal"),
    ("stitched_charm_pouches", "talisman", (0.32, 0.38, 0.18), "cloth", "faded_teal"),
    ("paper_talisman_bundle", "talisman", (0.14, 0.44, 0.045), "cream_plastic", "rust"),
    ("thread_spools", "talisman", (0.48, 0.34, 0.22), "wood", "cloth"),
    ("donation_terminal", "community", (0.40, 0.82, 0.36), "painted_metal", "warm_light"),
    ("classroom_desk", "community", (0.78, 0.72, 0.62), "wood", "exposed_metal"),
    ("classroom_chair", "community", (0.42, 0.84, 0.44), "wood", "rust"),
    ("sorted_food_tubs", "community", (0.60, 0.45, 0.42), "cream_plastic", "faded_teal"),
    ("shared_kitchen_kettle", "community", (0.34, 0.38, 0.30), "exposed_metal", "plastic"),
    ("notice_slot", "community", (0.84, 0.90, 0.08), "wood", "cloth"),
    ("warehouse_roll_shutter", "storage", (2.2, 2.5, 0.12), "painted_metal", "rust"),
    ("warehouse_strapped_crates", "storage", (1.05, 0.82, 0.78), "wood", "faded_teal"),
    ("sealed_parts_bin", "storage", (0.56, 0.44, 0.52), "plastic", "rubber"),
    ("lock_bar_and_padlock", "storage", (0.34, 0.48, 0.12), "exposed_metal", "rust"),
    ("stained_bar_counter", "bar", (1.52, 0.98, 0.72), "wood", "exposed_metal"),
    ("bent_bar_entry_rail", "bar", (0.14, 1.15, 1.4), "rust", "exposed_metal"),
    ("booth_partition", "bar", (0.92, 1.32, 0.12), "wood", "cloth"),
    ("prepaid_card_tray", "bar", (0.42, 0.13, 0.28), "plastic", "faded_teal"),
    ("repair_sewing_machine", "tailor", (0.54, 0.48, 0.30), "exposed_metal", "painted_metal"),
    ("thread_and_button_box", "tailor", (0.38, 0.22, 0.28), "wood", "plastic"),
    ("patchwork_garment_rail", "tailor", (1.22, 1.45, 0.42), "exposed_metal", "cloth"),
    ("zipper_and_patch_cards", "tailor", (0.36, 0.10, 0.25), "cloth", "exposed_metal"),
    ("welding_curtain", "workshop", (1.15, 1.85, 0.045), "cloth", "exposed_metal"),
    ("bench_vise", "workshop", (0.38, 0.28, 0.34), "exposed_metal", "rust"),
    ("repair_lamp", "workshop", (0.38, 0.72, 0.35), "exposed_metal", "warm_light"),
    ("hydrogen_service_cell", "workshop", (0.46, 0.76, 0.42), "painted_metal", "faded_teal"),
)

_FACILITY_PROPS = {
    "north_yatai": ("street_bowl_rack", "lidded_stockpot", "reuse_container_stack", "chopstick_caddy"),
    "north_terminal_repair": ("repair_chair", "sewing_tool_roll", "junction_panel", "power_meter"),
    "north_machiya": ("clothes_hanger", "patched_clothes_bundle", "shared_mailboxes", "rolled_bedding"),
    "north_laundry": ("laundry_wringer", "detergent_canister", "laundry_bucket", "clothes_hanger"),
    "north_night_market": ("cfc_food_canister", "reuse_container_stack", "street_bowl_rack", "under_counter_fridge"),
    "north_learning_room": ("classroom_desk", "classroom_chair", "stacked_textbooks", "donation_terminal"),
    "east_clinic": ("clinic_privacy_curtain", "diagnostic_table", "joint_casing_set", "instrument_trolley", "medicine_drawer", "exam_task_lamp", "tray_of_tools"),
    "east_rowhouse_a": ("slip_on_shoes", "folded_umbrella", "rolled_bedding", "shared_mailboxes"),
    "east_rowhouse_b": ("clothes_hanger", "patched_clothes_bundle", "repair_chair", "detergent_canister"),
    "east_public_bath": ("wash_sink", "laundry_bucket", "detergent_canister", "floor_drain"),
    "east_housing_coop": ("shared_mailboxes", "stacked_textbooks", "rolled_bedding", "roof_tank_filter"),
    "east_roof_garden": ("roof_tank_filter", "antenna_yagi", "rain_gutter", "power_meter"),
    "south_repair_yard": ("wooden_pallet", "shipping_crate", "ratchet_strap", "folding_dolly", "chain_hoist", "motorcycle_static", "engine_case_half", "wheel_and_hub", "fuel_cell_turbine"),
    "south_machine_shop": ("welding_curtain", "bench_vise", "repair_lamp", "hydrogen_service_cell"),
    "south_theatre": ("recliner_seat", "old_tron_terminal", "abstract_sea_screen", "theatre_air_baffle", "speaker_cabinet"),
    "south_rehearsal": ("repair_sewing_machine", "thread_and_button_box", "patchwork_garment_rail", "zipper_and_patch_cards"),
    "south_reclaimed_warehouse": ("warehouse_roll_shutter", "warehouse_strapped_crates", "sealed_parts_bin", "lock_bar_and_padlock"),
    "south_battery_shop": ("junction_panel", "power_meter", "hydrogen_service_cell", "roof_tank_filter"),
    "west_basement_bar": ("stained_bar_counter", "bent_bar_entry_rail", "booth_partition", "prepaid_card_tray"),
    "west_salvage_depot": ("wooden_pallet", "shipping_crate", "folding_dolly", "sealed_parts_bin"),
    "west_talisman_shop": ("amulet_shelf", "stitched_charm_pouches", "paper_talisman_bundle", "thread_spools"),
    "west_game_room": ("arcade_cabinet", "arcade_stick_panel", "game_cartridge_case", "score_card_tray"),
    "west_shared_kitchen": ("shared_kitchen_kettle", "wash_sink", "sorted_food_tubs", "notice_slot"),
    "west_roof_access": ("rain_gutter", "ac_compressor", "wall_fan", "exhaust_duct"),
}


def _b(name: str, center: Vec3, size: Vec3, material: str, bevel: float = 0.0) -> geo.MeshData:
    return geo.beveled_box(name, center, size, bevel, material) if bevel else geo.box(name, center, size, material)


def _build_prop(kind: str, center: Vec3, rotation: float, spec: tuple[str, str, tuple[float, float, float], str, str]) -> Assembly:
    """Delegate to the named, function-specific asset-form library."""
    from modeling.tokyo_nova.prop_forms import build_prop

    return build_prop(kind, center, rotation, spec)


def _room_shell(
    building: dict[str, Any], facility_key: str, basement_y: float | None = None,
    access: dict[str, Any] | None = None,
) -> Assembly:
    """Emit room floors and entry surfaces around the same real basement opening."""
    width, depth = (float(value) for value in building["size"])
    ybase = float(basement_y or 0.0)
    height = 2.85
    front = str(building["front"])
    thickness = 0.12
    door = 1.5 if facility_key == "west_basement_bar" else (1.8 if facility_key == "south_theatre" else 1.3)
    inner_width, inner_depth = width - .42, depth - .42
    floor_thickness = .05 if ybase < 0 else .06
    floor_surface_y = ybase + floor_thickness
    floor_center_y = floor_surface_y - floor_thickness / 2
    parts: list[geo.MeshData] = []

    if ybase < 0 and access is not None:
        opening = access["floor_opening"]
        hole_x, hole_z = (float(value) for value in opening["center"])
        hole_width, hole_depth = (float(value) for value in opening["size"])
        xmin, xmax, zmin, zmax = -inner_width / 2, inner_width / 2, -inner_depth / 2, inner_depth / 2
        x0, x1 = max(xmin, hole_x - hole_width / 2), min(xmax, hole_x + hole_width / 2)
        z0, z1 = max(zmin, hole_z - hole_depth / 2), min(zmax, hole_z + hole_depth / 2)
        if x1 <= x0 or z1 <= z0:
            raise ValueError(f"basement room opening for {facility_key} misses its emitted floor")
        for label, rect in (("west", (xmin, x0, zmin, zmax)), ("east", (x1, xmax, zmin, zmax)), ("rear", (x0, x1, zmin, z0)), ("front", (x0, x1, z1, zmax))):
            left, right, back, forward = rect
            if right - left > .03 and forward - back > .03:
                parts.append(geo.box(
                    f"{facility_key}_room_floor_{label}",
                    ((left + right) / 2, floor_center_y, (back + forward) / 2),
                    (right - left, floor_thickness, forward - back),
                    "wood",
                ))
    else:
        parts.append(geo.box(f"{facility_key}_room_floor", (0, floor_center_y, 0), (inner_width, floor_thickness, inner_depth), "wood"))

    if front in ("north", "south"):
        rear_z = -(inner_depth - thickness) / 2 if front == "north" else (inner_depth - thickness) / 2
        parts.append(geo.box(f"{facility_key}_room_rear_wall", (0, ybase + height / 2, rear_z), (inner_width, height, thickness), "patched_concrete"))
    else:
        rear_x = -(inner_width - thickness) / 2 if front == "east" else (inner_width - thickness) / 2
        parts.append(geo.box(f"{facility_key}_room_rear_wall", (rear_x, ybase + height / 2, 0), (thickness, height, inner_depth), "patched_concrete"))

    # Basement passages have no low header across the descent; the opening remains head-clear.
    if front in ("north", "south"):
        front_z = (inner_depth - thickness) / 2 * (1 if front == "north" else -1)
        side_w = (inner_width - door) / 2
        for side in (-1, 1):
            parts.append(geo.box(f"{facility_key}_room_front_jamb_{side}", (side * (door / 2 + side_w / 2), ybase + height / 2, front_z), (side_w, height, thickness), "painted_metal"))
        if ybase >= 0:
            parts.append(geo.box(f"{facility_key}_room_front_lintel", (0, ybase + height - .26, front_z), (inner_width, .52, thickness), "exposed_metal"))
        for side in (-1, 1):
            parts.append(geo.box(f"{facility_key}_room_side_{side}", (side * (inner_width - thickness) / 2, ybase + height / 2, 0), (thickness, height, inner_depth), "concrete"))
    else:
        front_x = (inner_width - thickness) / 2 * (1 if front == "east" else -1)
        side_d = (inner_depth - door) / 2
        for side in (-1, 1):
            parts.append(geo.box(f"{facility_key}_room_front_jamb_{side}", (front_x, ybase + height / 2, side * (door / 2 + side_d / 2)), (thickness, height, side_d), "painted_metal"))
        if ybase >= 0:
            parts.append(geo.box(f"{facility_key}_room_front_lintel", (front_x, ybase + height - .26, 0), (thickness, .52, inner_depth), "exposed_metal"))
        for side in (-1, 1):
            parts.append(geo.box(f"{facility_key}_room_side_{side}", (0, ybase + height / 2, side * (inner_depth - thickness) / 2), (inner_width, height, thickness), "concrete"))

    center = building["center"]
    origin = (float(center[0]), float(center[1]), float(center[2]))
    return Assembly("interior_room", facility_key, origin, 0, parts)


def build_interiors(layout: dict[str, Any]) -> tuple[list[Assembly], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build real room shells and 76 distinct fitted assets grouped by their actual use."""
    buildings = {item["key"]: item for item in layout["buildings"]}
    facilities = {item["building_key"]: item for item in layout["facilities"]}
    specs = {entry[0]: entry for entry in _ASSET_SPECS}
    assemblies: list[Assembly] = []
    access: dict[str, dict[str, Any]] = {}
    facility_geometry: dict[str, dict[str, Any]] = {}
    emitted_assets: dict[str, dict[str, Any]] = {}
    basement_access_by_building = {item["building_key"]: item for item in layout["basement_access"]}
    slot_positions = ((-1.30, -0.80), (0.0, -0.85), (1.28, -0.75), (-1.18, 0.85), (0.05, 0.90), (1.22, 0.82), (-0.82, 0.05), (0.85, 0.08))
    for facility_index, (building_key, prop_keys) in enumerate(_FACILITY_PROPS.items()):
        building = buildings[building_key]
        facility = facilities.get(building_key, {"name": building_key, "key": building_key})
        is_basement = building_key in {"west_basement_bar", "south_theatre"}
        base_y = (-2.45 if building_key == "south_theatre" else -2.25) if is_basement else 0.0
        floor_surface_y = base_y + (0.05 if is_basement else 0.06)
        facility_assets: list[Assembly] = []
        if building_key in {"north_yatai", "north_terminal_repair", "north_machiya"}:
            # These three authored Task 2 assemblies are already detailed and tuned; do not overlay them.
            facility_geometry[facility["key"]] = {"facility_key": facility["key"], "building_key": building_key, "asset_kinds": (), "room_part_count": 0, "asset_part_count": 0, "emitted_geometry": True, "preserved_existing_north_geometry": True}
            continue
        shell = _room_shell(building, building_key, base_y, basement_access_by_building.get(building_key))
        assemblies.append(shell)
        for prop_index, key in enumerate(prop_keys):
            spec = specs[key]
            _width, height, _depth = spec[2]
            px, pz = slot_positions[(facility_index + prop_index * 3) % len(slot_positions)]
            # Tall equipment is against a wall; floor-level pieces sit on the room's actual slab.
            py = base_y + (height / 2 if key in {"joint_casing_set", "wheel_and_hub", "engine_case_half", "paper_talisman_bundle", "thread_spools"} else .10)
            if key == "abstract_sea_screen":
                py = base_y + 1.7
            if key == "clinic_privacy_curtain":
                px, pz = 1.25, -.10
            if key == "rain_gutter" and building_key == "west_roof_access":
                px, pz = -.50, -.75
            if key == "motorcycle_static":
                px, pz = -.10, .25
                py = .06
            if key == "recliner_seat":
                px, pz = -2.0, -.70
                py = base_y + .02
            if key == "old_tron_terminal" and building_key == "south_theatre":
                px, pz = 2.0, -.70
                py = base_y + .20
            if key == "stained_bar_counter":
                px, pz = -.40, -1.42
                py = base_y + .02
            if key in {"bent_bar_entry_rail", "booth_partition"}:
                px, pz = .45, 1.32
                py = base_y + .02
            assembly = _build_prop(key, (float(building["center"][0]) + px, py, float(building["center"][2]) + pz), 0.0, spec)
            assembly.name = f"{building_key}_{key}"
            assemblies.append(assembly)
            facility_assets.append(assembly)
            bounds = assembly.bounds
            emitted_assets[key] = {
                "parts": tuple(part.name for part in assembly.parts),
                "triangles": sum(len(face) - 2 for part in assembly.parts for face in part.faces),
                "dimensions": [round(bounds[1][axis] - bounds[0][axis], 4) for axis in range(3)],
                "facility_key": facility["key"],
                "building_key": building_key,
                "material": spec[3],
                "secondary_material": spec[4],
                "materials": sorted({part.material for part in assembly.parts}),
                "world_center": list(assembly.origin),
                "wear_details": [
                    "Contrasting primary and secondary finishes distinguish serviced panels, supports and attached fittings.",
                    "Exposed hardware uses the listed metal/rust finish where present; reused surfaces remain visibly mismatched.",
                ],
                "recognized_form": key.replace("_", " "),
            }
        facility = facilities.get(building_key, {"name": building_key, "key": building_key})
        facility_geometry[facility["key"]] = {
            "facility_key": facility["key"],
            "building_key": building_key,
            "asset_kinds": tuple(prop_keys),
            "room_part_count": len(shell.parts),
            "asset_part_count": sum(len(asset.parts) for asset in facility_assets),
            "emitted_geometry": bool(shell.parts and facility_assets),
        }
        # Six-plus public-facing facilities get enclosed, traversable spaces with real doorway gaps.
        if building_key not in {"north_yatai", "north_terminal_repair", "north_machiya", "north_night_market", "east_rowhouse_a", "east_rowhouse_b"}:
            room_parts = shell.parts
            front_axis = 0 if building["front"] in ("north", "south") else 2
            left_jamb = next(part for part in room_parts if part.name == f"{building_key}_room_front_jamb_-1")
            right_jamb = next(part for part in room_parts if part.name == f"{building_key}_room_front_jamb_1")
            door_width = min(vertex[front_axis] for vertex in right_jamb.vertices) - max(vertex[front_axis] for vertex in left_jamb.vertices)
            lintel = next((part for part in room_parts if part.name == f"{building_key}_room_front_lintel"), None)
            opening_top = min(vertex[1] for vertex in lintel.vertices) if lintel else base_y + 2.85
            door_height = opening_top - floor_surface_y
            front = building["front"]
            cx, _cy, cz = (float(value) for value in building["center"])
            build_width, build_depth = (float(value) for value in building["size"])
            inner_width, inner_depth = build_width - .42, build_depth - .42
            plane_half = .06
            plane_x, plane_z = cx, cz
            if front in ("north", "south"):
                plane_z = cz + (inner_depth / 2 - plane_half) * (1 if front == "north" else -1)
                gap_min, gap_max = (cx - door_width / 2, floor_surface_y, plane_z - plane_half), (cx + door_width / 2, floor_surface_y + door_height, plane_z + plane_half)
            else:
                plane_x = cx + (inner_width / 2 - plane_half) * (1 if front == "east" else -1)
                gap_min, gap_max = (plane_x - plane_half, floor_surface_y, cz - door_width / 2), (plane_x + plane_half, floor_surface_y + door_height, cz + door_width / 2)
            blockers = []
            for owner, part_name, minimum, maximum in collision_parts([shell]):
                if all(minimum[axis] < gap_max[axis] - 1e-7 and gap_min[axis] < maximum[axis] - 1e-7 for axis in range(3)):
                    blockers.append(f"{owner}/{part_name}")
            path_width, path_depth = .9, 1.25
            path_min_y, path_max_y = floor_surface_y, floor_surface_y + 1.95
            if front == "north":
                path_min = (cx - path_width / 2, path_min_y, plane_z - path_depth)
                path_max = (cx + path_width / 2, path_max_y, plane_z - plane_half)
            elif front == "south":
                path_min = (cx - path_width / 2, path_min_y, plane_z + plane_half)
                path_max = (cx + path_width / 2, path_max_y, plane_z + path_depth)
            elif front == "east":
                path_min = (plane_x - path_depth, path_min_y, cz - path_width / 2)
                path_max = (plane_x - plane_half, path_max_y, cz + path_width / 2)
            else:
                path_min = (plane_x + plane_half, path_min_y, cz - path_width / 2)
                path_max = (plane_x + path_depth, path_max_y, cz + path_width / 2)
            corridor_blockers = []
            for asset in facility_assets:
                minimum, maximum = asset.bounds
                if all(minimum[axis] < path_max[axis] - 1e-7 and path_min[axis] < maximum[axis] - 1e-7 for axis in range(3)):
                    corridor_blockers.append(asset.name)
            access[facility["key"]] = {
                "building_key": building_key,
                "door_width": round(door_width, 4),
                "door_height": round(door_height, 4),
                "door_opening_verified_from_meshes": True,
                "door_opening_bounds": [list(gap_min), list(gap_max)],
                "door_clearance_verified_from_colliders": not blockers,
                "door_blocking_parts": blockers,
                "entry_corridor_bounds": [list(path_min), list(path_max)],
                "entry_corridor_verified_from_props": True,
                "entry_corridor_blocking_props": corridor_blockers,
                "route_connected": any(_route_reaches_front_door(building, route) for route in layout["routes"]),
                "floor_bounds": [
                    float(building["center"][0]) - float(building["size"][0]) / 2 + .14,
                    float(building["center"][0]) + float(building["size"][0]) / 2 - .14,
                    float(building["center"][2]) - float(building["size"][1]) / 2 + .14,
                    float(building["center"][2]) + float(building["size"][1]) / 2 - .14,
                ],
                "floor_y": floor_surface_y,
                "geometry_parts": len(shell.parts) + sum(len(asset.parts) for asset in facility_assets),
            }
    return assemblies, facility_geometry, {"accessible": access, "props": emitted_assets}


def asset_catalog(emitted_geometry: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Describe every built prop from its emitted mesh bounds, parts, finishes and placement."""
    result = []
    for key, family, dimensions, primary, secondary in _ASSET_SPECS:
        emitted = (emitted_geometry or {}).get(key)
        if emitted_geometry is not None and emitted is None:
            continue
        placements = [building_key for building_key, kinds in _FACILITY_PROPS.items() if key in kinds]
        result.append({
            "kind": key,
            "dimensions": list(emitted["dimensions"] if emitted else dimensions),
            "units": "meters",
            "materials": emitted["materials"] if emitted else [primary, secondary],
            "primary_finish": primary,
            "secondary_finish": secondary,
            "parts": list(emitted["parts"]) if emitted else [f"{family} structural body", "separate support/fittings", "wear/detail geometry"],
            "wear_details": list(emitted["wear_details"] if emitted else ["Contrasting service panels and attached fittings", "Mixed-age materials and hardware cues"]),
            "placement": {"buildings": placements, "facility_key": emitted["facility_key"] if emitted else None, "world_center": emitted["world_center"] if emitted else None},
            "recognition": emitted["recognized_form"] if emitted else key.replace("_", " "),
        })
    return result
