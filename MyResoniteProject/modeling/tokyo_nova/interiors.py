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
    _key, family, size, primary, secondary = spec
    sx, sy, sz = size
    parts: list[geo.MeshData] = []
    def box(name: str, pos: Vec3, dimensions: Vec3, material: str = primary, bevel: float = 0.0) -> None:
        parts.append(_b(f"{kind}_{name}", pos, dimensions, material, min(bevel, min(dimensions) * .4) if bevel else 0))
    def pipe(name: str, start: Vec3, end: Vec3, radius: float, material: str = secondary) -> None:
        parts.append(geo.pipe(f"{kind}_{name}", start, end, radius, material, segments=8))
    def cylinder(name: str, pos: Vec3, radius: float, depth: float, material: str = primary, axis: Vec3 = (0.0, 1.0, 0.0)) -> None:
        parts.append(geo.cylinder(f"{kind}_{name}", pos, radius, depth, material, segments=12, axis=axis))

    if family == "architectural":
        box("main_leaf", (0, sy * .5, 0), (sx, max(.035, sy * .76), sz), primary, .025)
        box("stiffener", (0, sy * .19, sz * .54), (sx * .94, .055, .035), secondary)
        for side in (-1, 1):
            pipe(f"hinge_{side}", (side * sx * .43, sy * .18, -sz * .50), (side * sx * .43, sy * .82, -sz * .50), .018)
        for n in range(5):
            box(f"corrugation_{n}", (0, sy * (.25 + n * .11), sz * .54), (sx * .92, .018, .018), secondary)
    elif family == "utility":
        box("casing", (0, sy * .50, 0), (sx * .82, sy * .82, sz * .74), primary, .04)
        box("service_cover", (0, sy * .52, -sz * .40), (sx * .62, sy * .62, .025), secondary, .018)
        cylinder("gauge", (0, sy * .60, -sz * .43), min(sx, sy) * .15, .025, "glass", axis=(0, 0, -1))
        for xside in (-1, 1):
            pipe(f"hose_{xside}", (xside * sx * .40, sy * .18, 0), (xside * sx * .42, sy * .05, sz * .40), .018)
        for n in range(3):
            box(f"vent_{n}", (0, sy * (.30 + n * .12), -sz * .43), (sx * .50, .025, .018), "rubber")
    elif family in ("medical", "food", "daily", "logistics", "community", "storage", "bar", "tailor", "workshop", "arcade", "theatre", "talisman", "vehicle"):
        # Each function family has different useful geometry, support and wear cues.
        if kind in {"lidded_stockpot", "cfc_food_canister", "laundry_bucket", "detergent_canister", "roof_tank_filter", "shared_kitchen_kettle"}:
            cylinder("vessel", (0, sy * .48, 0), min(sx, sz) * .45, sy * .76, primary)
            cylinder("rolled_rim", (0, sy * .86, 0), min(sx, sz) * .48, .035, secondary)
            cylinder("lid", (0, sy * .91, 0), min(sx, sz) * .43, .035, "cream_plastic" if primary != "cream_plastic" else "exposed_metal")
            for side in (-1, 1):
                pipe(f"handle_{side}", (side * sx * .43, sy * .60, 0), (side * sx * .58, sy * .60, 0), .025)
        elif kind in {"diagnostic_table", "serving_counter", "classroom_desk", "stained_bar_counter", "wooden_pallet", "warehouse_strapped_crates", "shipping_crate"}:
            box("top_or_body", (0, sy * .80, 0), (sx, sy * .18, sz), primary, .035)
            for xi in (-1, 1):
                for zi in (-1, 1):
                    box(f"leg_{xi}_{zi}", (xi * sx * .42, sy * .40, zi * sz * .38), (max(.035, sx * .07), sy * .75, max(.035, sz * .07)), secondary, .012)
            box("front_apron", (0, sy * .55, sz * .47), (sx * .88, sy * .18, .045), secondary)
            if kind in {"shipping_crate", "warehouse_strapped_crates"}:
                for side in (-1, 1):
                    box(f"strap_{side}", (side * sx * .27, sy * .50, -sz * .515), (sx * .10, sy * .88, .025), "faded_teal")
        elif kind in {"recliner_seat", "repair_chair", "classroom_chair"}:
            box("seat_cushion", (0, sy * .40, 0), (sx * .82, sy * .13, sz * .65), primary, .045)
            box("back_cushion", (0, sy * .70, -sz * .28), (sx * .76, sy * .48, sz * .13), "cloth" if primary != "cloth" else secondary, .04)
            for side in (-1, 1):
                box(f"leg_{side}", (side * sx * .32, sy * .18, sz * .20), (.045, sy * .36, .045), secondary)
                if kind == "recliner_seat":
                    box(f"arm_{side}", (side * sx * .46, sy * .52, sz * .05), (.10, .15, sz * .66), secondary, .025)
            if kind == "recliner_seat":
                pipe("tilt_link", (-sx * .28, sy * .20, -sz * .12), (sx * .28, sy * .27, -sz * .12), .022)
        elif kind in {"motorcycle_static", "engine_case_half", "wheel_and_hub", "fuel_cell_turbine"}:
            if kind == "motorcycle_static":
                for wheel_x in (-sx * .36, sx * .36):
                    cylinder(f"tire_{wheel_x:+.2f}", (wheel_x, sy * .20, 0), sy * .20, .12, "rubber", axis=(1, 0, 0))
                    cylinder(f"hub_{wheel_x:+.2f}", (wheel_x, sy * .20, 0), sy * .09, .14, "exposed_metal", axis=(1, 0, 0))
                pipe("lower_frame", (-sx * .34, sy * .22, 0), (sx * .12, sy * .47, 0), .032)
                pipe("upper_frame", (-sx * .34, sy * .22, 0), (sx * .25, sy * .28, 0), .027)
                pipe("front_fork", (sx * .32, sy * .21, 0), (sx * .43, sy * .62, 0), .026)
                box("engine_block", (0, sy * .40, 0), (sx * .30, sy * .28, sz * .48), "exposed_metal", .035)
                box("seat", (-sx * .02, sy * .71, 0), (sx * .36, sy * .11, sz * .36), "rubber", .03)
                box("opened_side_cowl", (-sx * .20, sy * .48, -sz * .37), (sx * .32, sy * .26, .025), primary, .02)
                pipe("handlebar", (sx * .38, sy * .75, -sz * .32), (sx * .38, sy * .75, sz * .32), .02)
                pipe("detached_cover_lead", (-sx * .25, sy * .53, -sz * .42), (-sx * .46, sy * .38, -sz * .28), .012, "rubber")
            else:
                box("housing", (0, sy * .52, 0), (sx * .78, sy * .62, sz * .72), primary, .045)
                for n in range(5):
                    box(f"cooling_fin_{n}", (-sx * .28 + n * sx * .14, sy * .52, -sz * .40), (.035, sy * .44, .035), secondary)
                cylinder("bearing", (0, sy * .22, 0), min(sx, sz) * .22, .06, "rust", axis=(0, 1, 0))
                for side in (-1, 1):
                    pipe(f"mount_{side}", (side * sx * .38, sy * .16, 0), (side * sx * .46, sy * .05, 0), .025)
        elif kind in {"arcade_cabinet", "old_tron_terminal", "abstract_sea_screen", "donation_terminal"}:
            box("lower_case", (0, sy * .30, 0), (sx, sy * .58, sz), primary, .045)
            box("bezel", (0, sy * .69, -sz * .42), (sx * .82, sy * .31, .065), secondary, .025)
            box("glass_or_screen", (0, sy * .70, -sz * .46), (sx * .68, sy * .23, .022), "cool_light" if kind in {"arcade_cabinet", "abstract_sea_screen"} else "glass", .015)
            box("maintenance_door", (0, sy * .23, -sz * .515), (sx * .70, sy * .28, .018), "painted_metal")
            for side in (-1, 1):
                cylinder(f"control_{side}", (side * sx * .18, sy * .53, -sz * .48), .035, .035, "exposed_metal", axis=(0, 0, -1))
            if kind == "abstract_sea_screen":
                screen_z = -sz * .46 + .025
                for wave in range(4):
                    vertices = []
                    faces = []
                    for segment in range(9):
                        x = -sx * .30 + segment * sx * .075
                        center_y = sy * (.61 + wave * .052) + math.sin(segment * .82 + wave * .93) * sy * .018
                        vertices.extend(((x, center_y - .012, screen_z), (x, center_y + .012, screen_z)))
                    for segment in range(8):
                        start = segment * 2
                        faces.append((start, start + 2, start + 3, start + 1))
                    parts.append(geo.mesh(f"{kind}_sea_wave_{wave}", vertices, faces, "cool_light" if wave % 2 else "faded_teal"))
                for bubble in range(3):
                    cylinder(f"{kind}_sea_glint_{bubble}", ((bubble - 1) * sx * .16, sy * (.63 + bubble * .055), screen_z + .004), .026, .012, "warm_light", axis=(0, 0, 1))
        elif kind in {"clinic_privacy_curtain", "welding_curtain", "booth_partition", "patchwork_garment_rail", "amulet_shelf", "shared_mailboxes"}:
            if "curtain" in kind or kind == "booth_partition":
                pipe("top_rail", (-sx * .48, sy * .92, 0), (sx * .48, sy * .92, 0), .022)
                box("fabric", (0, sy * .48, 0), (sx * .86, sy * .78, sz), primary, .008)
                for n in range(5):
                    box(f"pleat_{n}", (-sx * .34 + n * sx * .17, sy * .48, sz * .55), (.025, sy * .75, .025), secondary)
            else:
                box("back_or_body", (0, sy * .50, 0), (sx, sy * .84, max(.06, sz * .18)), primary, .025)
                for side in (-1, 1):
                    pipe(f"upright_{side}", (side * sx * .44, .04, 0), (side * sx * .44, sy, 0), .025, secondary)
                for n in range(3):
                    box(f"shelf_{n}", (0, sy * (.18 + n * .28), sz * .30), (sx * .90, .045, sz * .72), primary)
                if kind == "shared_mailboxes":
                    for row in range(3):
                        for col in range(2):
                            box(f"mail_door_{row}_{col}", ((col - .5) * sx * .42, sy * (.20 + row * .25), -sz * .12), (sx * .36, sy * .19, .025), secondary)
        elif kind in {"slip_on_shoes", "stitched_charm_pouches", "paper_talisman_bundle", "clothes_hanger", "thread_spools", "stacked_textbooks", "game_cartridge_case", "score_card_tray", "prepaid_card_tray", "zipper_and_patch_cards", "sewing_tool_roll", "sorted_food_tubs", "reuse_container_stack", "tray_of_tools"}:
            box("tray_or_case", (0, sy * .45, 0), (sx, sy * .30, sz), primary, .025)
            for n in range(3):
                box(f"item_{n}", (-sx * .30 + n * sx * .30, sy * .72, 0), (sx * .20, sy * .32, sz * .55), secondary if n % 2 else primary, .015)
            if kind in {"stitched_charm_pouches", "paper_talisman_bundle"}:
                for n in range(3):
                    pipe(f"suspension_thread_{n}", (-sx * .30 + n * sx * .30, sy * .90, -sz * .18), (-sx * .30 + n * sx * .30, sy * .65, -sz * .18), .008, "rust")
        else:
            # Distinct assembled utility furniture: a load-bearing top, four legs and fitted fittings.
            box("body", (0, sy * .54, 0), (sx * .82, sy * .74, sz * .74), primary, .025)
            box("access_panel", (0, sy * .52, -sz * .40), (sx * .58, sy * .42, .025), secondary, .012)
            for side in (-1, 1):
                pipe(f"support_{side}", (side * sx * .35, sy * .16, sz * .30), (side * sx * .40, sy * .02, sz * .34), .02, secondary)
                cylinder(f"fastener_{side}", (side * sx * .23, sy * .52, -sz * .43), .018, .012, "rust", axis=(0, 0, -1))
            for n in range(2):
                box(f"service_detail_{n}", ((n - .5) * sx * .25, sy * .34, -sz * .42), (sx * .08, sy * .12, .02), "warm_light" if n == 0 and kind in {"repair_lamp", "donation_terminal"} else "rubber")
    else:
        raise ValueError(f"unsupported prop family {family!r} for {kind}")

    # Avoid zero-volume/coplanar parts, and put every assembly at the specified room position.
    return Assembly("interior_props", kind, center, rotation, parts)


def _room_shell(building: dict[str, Any], facility_key: str, basement_y: float | None = None) -> Assembly:
    width, depth = (float(v) for v in building["size"])
    ybase = float(basement_y or 0.0)
    height = 2.85
    front = str(building["front"])
    thickness = .12
    door = 1.5 if facility_key == "west_basement_bar" else (1.8 if facility_key == "south_theatre" else 1.3)
    inner_width, inner_depth = width - .42, depth - .42
    floor_thickness = 0.05 if ybase < 0 else 0.06
    floor_surface_y = ybase + (0.05 if ybase < 0 else 0.06)
    floor_center_y = floor_surface_y - floor_thickness / 2
    if ybase < 0:
        # Keep the continuous basement stair/ramp corridor open; no hidden floor collider crosses it.
        corridor_width = 1.5 if facility_key == "west_basement_bar" else 1.8
        if facility_key == "west_basement_bar":
            side_width = (inner_depth - corridor_width) / 2
            parts: list[geo.MeshData] = [
                geo.box(f"{facility_key}_room_floor_left", (0, floor_center_y, -corridor_width / 2 - side_width / 2), (inner_width, floor_thickness, side_width), "wood"),
                geo.box(f"{facility_key}_room_floor_right", (0, floor_center_y, corridor_width / 2 + side_width / 2), (inner_width, floor_thickness, side_width), "wood"),
            ]
        else:
            side_width = (inner_width - corridor_width) / 2
            parts = [
                geo.box(f"{facility_key}_room_floor_left", (-corridor_width / 2 - side_width / 2, floor_center_y, 0), (side_width, floor_thickness, inner_depth), "wood"),
                geo.box(f"{facility_key}_room_floor_right", (corridor_width / 2 + side_width / 2, floor_center_y, 0), (side_width, floor_thickness, inner_depth), "wood"),
            ]
    else:
        parts = [geo.box(f"{facility_key}_room_floor", (0, floor_center_y, 0), (inner_width, floor_thickness, inner_depth), "wood")]
    if front in ("north", "south"):
        rear_z = -(inner_depth - thickness) / 2 if front == "north" else (inner_depth - thickness) / 2
        parts.append(geo.box(f"{facility_key}_room_rear_wall", (0, ybase + height / 2, rear_z), (inner_width, height, thickness), "patched_concrete"))
    else:
        rear_x = -(inner_width - thickness) / 2 if front == "east" else (inner_width - thickness) / 2
        parts.append(geo.box(f"{facility_key}_room_rear_wall", (rear_x, ybase + height / 2, 0), (thickness, height, inner_depth), "patched_concrete"))
    # Omit the actual front wall entry and the corresponding section of one adjacent return wall.
    if front in ("north", "south"):
        front_z = (inner_depth - thickness) / 2 * (1 if front == "north" else -1)
        side_w = (inner_width - door) / 2
        for side in (-1, 1):
            parts.append(geo.box(f"{facility_key}_room_front_jamb_{side}", (side * (door / 2 + side_w / 2), ybase + height / 2, front_z), (side_w, height, thickness), "painted_metal"))
        parts.append(geo.box(f"{facility_key}_room_front_lintel", (0, ybase + height - .26, front_z), (inner_width, .52, thickness), "exposed_metal"))
        for side in (-1, 1):
            parts.append(geo.box(f"{facility_key}_room_side_{side}", (side * (inner_width - thickness) / 2, ybase + height / 2, 0), (thickness, height, inner_depth), "concrete"))
    else:
        front_x = (inner_width - thickness) / 2 * (1 if front == "east" else -1)
        side_d = (inner_depth - door) / 2
        for side in (-1, 1):
            parts.append(geo.box(f"{facility_key}_room_front_jamb_{side}", (front_x, ybase + height / 2, side * (door / 2 + side_d / 2)), (thickness, height, side_d), "painted_metal"))
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
        shell = _room_shell(building, building_key, base_y)
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
            lintel = next(part for part in room_parts if part.name == f"{building_key}_room_front_lintel")
            door_height = min(vertex[1] for vertex in lintel.vertices) - floor_surface_y
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
