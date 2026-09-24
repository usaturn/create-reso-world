"""North-frontage asset catalog, detailed assembly placement and native signage."""
from __future__ import annotations

import math
from typing import Any

from modeling.tokyo_nova import geometry as geo
from modeling.tokyo_nova.props import Assembly, create


def asset_catalog() -> list[dict[str, Any]]:
    """Return the explicit design catalog for the north block's modeled assemblies."""
    return [
        {
            "kind": "food_stall", "dimensions": [4.5, 2.86, 2.10], "units": "meters",
            "materials": ["wood", "painted_metal", "exposed_metal", "rust", "ceramic", "plastic", "cloth", "warm_light"],
            "parts": ["mismatched corrugated awning and braces", "rolled-rim service counter", "lidded steel pots", "ceramic bowls and chopsticks", "condiment trays", "reusable CFC containers", "vented under-counter refrigerator", "fan and task light", "physical Japanese menu board"],
            "wear": ["uneven replacement sheets", "rust streaks", "painted and exposed frame edges", "reused wood counter"],
            "placement": {"building_key": "north_yatai", "front": "south", "origin_offset": [0, 0.18, -1.0]},
            "recognition": "busy standing counter under a mismatched ribbed awning; lidded pots and ceramic serviceware are visible from the aisle",
        },
        {
            "kind": "terminal_repair", "dimensions": [4.8, 3.36, 5.15], "units": "meters",
            "materials": ["concrete", "wood", "painted_metal", "exposed_metal", "rust", "plastic", "glass", "rubber", "faded_teal", "warm_light"],
            "parts": ["repair bench and three drawers", "45 cm monitor and stand", "35 cm vented terminal box", "removable terminal cover", "component bins", "repair trays", "precision drivers", "hot-air station and hose", "solder iron and stand", "cables and task lamp", "rear and side walls", "glazed frontage with open doorway", "physical repair fascia"],
            "wear": ["replaceable bench edge", "mixed metal panels", "scuffed ESD mat", "different-age drawer bins", "repaired cable trunk"],
            "placement": {"building_key": "north_terminal_repair", "front": "south", "origin_offset": [0, 0.15, 1.8]},
            "recognition": "open workbench with a separate 45 cm display, compact vented 35 cm equipment case, tools, trays, open front door and warm Japanese repair fascia",
        },
        {
            "kind": "patched_housing_facade", "dimensions": [5.94, 8.83, 1.11], "units": "meters",
            "materials": ["concrete", "patched_concrete", "faded_teal", "painted_metal", "exposed_metal", "rust", "glass", "wood", "cloth", "warm_light", "rubber"],
            "parts": ["masonry split around real door and window openings", "deep reveal windows", "mullions and unequal shutters", "recessed entry and lintel", "upper balcony and rails", "laundry lines", "wall air conditioner and louver", "elbowed drainpipe and cleanout", "roof service addition", "cables", "wall lamp", "nameplate"],
            "wear": ["three branching cracks", "exposed patch repairs", "paint loss at edges", "rusted drain clamps", "asymmetric altered openings"],
            "placement": {"building_key": "north_machiya", "front": "south", "origin_offset": [0, 0, -3.0]},
            "recognition": "deep two-level openings, patched wall, improvised balcony/laundry and a mismatched AC unit read as occupied housing rather than a blank blockout shell",
        },
        {
            "kind": "pocket_phone", "dimensions": [0.075, 0.008, 0.15], "units": "meters",
            "materials": ["plastic", "glass", "faded_teal", "exposed_metal", "rubber", "cool_light", "warm_light"],
            "parts": ["rounded structural shell", "glass and display", "raised volume/power buttons", "three-lens camera cluster", "flash", "removable back cover", "speaker grills", "charging port"],
            "wear": ["serviceable seam", "individual metal camera rings", "small edge keys", "matte replaceable rear cover"],
            "placement": {"building_key": "north_terminal_repair", "surface": "repair_bench", "orientation": "screen faces up"},
            "recognition": "75 mm by 150 mm smartphone silhouette with a distinct 8 mm rounded edge, camera cluster and side keys; no oversized tablet geometry",
        },
        {
            "kind": "north_frontage_pavement", "dimensions": [26.0, 0.052, 0.34], "units": "meters",
            "materials": ["asphalt_dry", "asphalt_wet", "patched_concrete", "rust", "exposed_metal"],
            "parts": ["dry repaired asphalt strip", "three shallow puddle patches", "broken seam and crack scars", "small drain grate and ribs", "exposed patch edges"],
            "wear": ["alternating dull dry asphalt and smooth damp asphalt", "local cracks and repaired joints"],
            "placement": {"building_key": "north_yatai", "span_buildings": ["north_yatai", "north_terminal_repair", "north_machiya"], "root_local_z": 11.82, "noncollidable": True},
            "recognition": "thin wet/dry frontage strip sits clear of the north path; puddles and repaired seams separate material response without filling the plaza",
        },
        {
            "kind": "north_facility_connector", "dimensions": [3.16, 0.60, 0.935], "units": "meters",
            "materials": ["painted_metal", "exposed_metal", "rust", "rubber"],
            "parts": ["overhead replacement rain sheet", "three corrugation ribs", "two wall brackets", "rain gutter and downspout", "shared cable tray"],
            "wear": ["two mismatched roofing sheets", "rust on old brackets", "repaired cable sleeve"],
            "placement": {"between": ["north_yatai", "north_terminal_repair"], "root_local_center": [-30.0, 3.55, 12.55], "walk_clearance_m": 3.0},
            "recognition": "elevated continuous rain cover and cable tray visibly join the neighboring food and repair facades while preserving a clear passage below",
        },
        {
            "kind": "ar_menu", "dimensions": [0.8, 0.5, 0.045], "units": "meters",
            "materials": ["painted_metal", "cool_light"],
            "parts": ["thin framed menu panel", "restrained emissive face", "Japanese TextRenderer content", "service brackets", "bezel and diffuse face"],
            "wear": ["steady low-luminance cool tint; no animation"],
            "placement": {"building_key": "north_yatai", "group": "north_ar_displays", "front": "south"},
            "recognition": "separately hideable 0.8 m × 0.5 m menu surface showing a short meal list and hours",
        },
        {
            "kind": "ar_repair_ad", "dimensions": [2.0, 0.7, 0.045], "units": "meters",
            "materials": ["painted_metal", "warm_light"],
            "parts": ["slender framed repair-hours panel", "restrained emissive face", "Japanese TextRenderer content", "service brackets", "bezel and diffuse face"],
            "wear": ["steady low-brightness warm lettering; no flashing"],
            "placement": {"building_key": "north_terminal_repair", "group": "north_ar_displays", "front": "south"},
            "recognition": "separately hideable 2.0 m × 0.7 m repair notice distinct from the physical fascia",
        },
    ]


def _frontage_pavement() -> Assembly:
    parts = [geo.box("dry_asphalt_base", (0, 0, 0), (26.0, 0.022, 0.30), "asphalt_dry")]
    for index, x in enumerate((-7.2, -1.0, 6.8)):
        parts.append(geo.beveled_box(f"wet_asphalt_puddle_{index}", (x, 0.015, (-1) ** index * 0.035), (1.8, 0.010, 0.19), 0.018, "asphalt_wet"))
    for index, x in enumerate((-9.0, -3.6, 2.5, 9.4)):
        parts.append(geo.mesh(f"asphalt_crack_{index}", ((x, 0.014, -0.09), (x + 0.25, 0.014, 0.02), (x + 0.48, 0.014, 0.06)), ((0, 1, 2),), "rubber"))
    parts.append(geo.box("street_drain_frame", (-10.0, 0.018, -0.08), (0.56, 0.025, 0.22), "rust"))
    for index in range(7):
        parts.append(geo.box(f"street_drain_rib_{index}", (-10.24 + index * 0.08, 0.035, -0.08), (0.025, 0.012, 0.19), "exposed_metal"))
    return Assembly("north_frontage_pavement", "Wet/dry repaired north frontage", (-25.0, 0.026, 11.86), 0.0, parts)


def _facility_connector() -> Assembly:
    parts = [geo.beveled_box("shared_mismatched_rain_canopy", (0, 0, 0), (3.16, 0.075, 0.90), 0.035, "painted_metal")]
    for index, x in enumerate((-0.95, 0.05, 1.05)):
        parts.append(geo.pipe(f"connector_corrugation_{index}", (x, 0.045, -0.42), (x, 0.045, 0.42), 0.018, "exposed_metal"))
    for side in (-1, 1):
        parts.append(geo.pipe(f"connector_bracket_{side}", (side * 1.48, -0.24, -0.34), (side * 1.48, -0.01, 0), 0.035, "rust"))
    parts.append(geo.pipe("shared_rain_gutter", (-1.55, -0.10, 0.44), (1.55, -0.10, 0.44), 0.045, "exposed_metal"))
    parts.append(geo.pipe("shared_gutter_downspout", (1.52, -0.10, 0.44), (1.52, -0.34, 0.44), 0.035, "rust"))
    parts.append(geo.box("shared_repaired_cable_tray", (0, 0.22, -0.30), (2.8, 0.08, 0.12), "exposed_metal",))
    return Assembly("north_facility_connector", "Shared canopy and service tray", (-30.0, 3.55, 12.55), 0.0, parts)


def _ar_panel(kind: str, name: str, origin: tuple[float, float, float], width: float, height: float, material: str) -> Assembly:
    depth = 0.045
    parts = [geo.beveled_box(f"{kind}_outer_frame", (0, 0, 0), (width, height, depth), min(width, height) * 0.045, "painted_metal")]
    parts.append(geo.beveled_box(f"{kind}_emissive_face", (0, 0, depth * 0.53), (width - 0.055, height - 0.055, 0.008), min(width, height) * 0.025, material))
    for x in (-width * 0.36, width * 0.36):
        parts.append(geo.box(f"{kind}_mount_bracket_{x}", (x, -height * 0.40, -depth * 0.30), (0.055, 0.09, 0.015), "exposed_metal"))
    return Assembly(kind, name, origin, math.pi, parts)


def build_north_sector(layout: dict[str, Any]) -> list[Assembly]:
    """Place deterministic reusable assemblies from the layout's stable building keys."""
    buildings = {entry["key"]: entry for entry in layout["buildings"]}
    assemblies: list[Assembly] = []

    def place(kind: str, building_key: str, offset: tuple[float, float, float], yaw: float) -> Assembly:
        center = buildings[building_key]["center"]
        assembly = create(kind, (center[0] + offset[0], center[1] + offset[1], center[2] + offset[2]), yaw)
        assemblies.append(assembly)
        return assembly

    place("food_stall", "north_yatai", (0.0, 0.18, -1.0), math.pi)
    repair = place("terminal_repair", "north_terminal_repair", (0.0, 0.15, 1.8), math.pi)
    place("patched_housing_facade", "north_machiya", (0.0, 0.0, -2.5), 0.0)
    # One measured phone rests on the repair bench with its display upward.
    phone_origin = (repair.origin[0] - 1.04, repair.origin[1] + 1.0, repair.origin[2] - 0.10)
    assemblies.append(create("pocket_phone", phone_origin, 0.0))
    assemblies.extend((_frontage_pavement(), _facility_connector()))
    assemblies.append(_ar_panel("ar_menu", "Hideable 0.8 × 0.5 m menu", (-35.0, 2.63, 13.08), 0.8, 0.5, "cool_light"))
    assemblies.append(_ar_panel("ar_repair_ad", "Hideable 2.0 × 0.7 m repair notice", (-25.0, 2.79, 12.96), 2.0, 0.7, "warm_light"))
    return assemblies


def sign_manifest_entries(layout: dict[str, Any]) -> dict[str, Any]:
    """Native Japanese physical and AR signs organized into independently hideable groups."""
    buildings = {entry["key"]: entry for entry in layout["buildings"]}

    def sign(key: str, name: str, building_key: str, offset: tuple[float, float, float], text: str, size: float, *, ar: bool = False, bounds: tuple[float, float] | None = None, color: tuple[float, float, float, float] = (0.95, 0.78, 0.49, 1.0)) -> dict[str, Any]:
        center = buildings[building_key]["center"]
        position = [center[index] + offset[index] for index in range(3)]
        component: dict[str, Any] = {"Text": text, "Size": size, "Color": list(color), "ParseRichText": False}
        if ar and bounds is not None:
            component.update({"Bounded": True, "BoundsSize": list(bounds), "HorizontalAutoSize": False, "VerticalAutoSize": False})
        return {"slot": {"key": key, "name": name, "position": position, "rotation": [0.0, 1.0, 0.0, 0.0]}, "components": [{"key": f"{key}_text", "type": "FrooxEngine.TextRenderer", "fields": component}]}

    physical = [
        sign("north_yatai_sign_text", "Physical Japanese sign · 立ち食い雨粒", "north_yatai", (0, 2.58, -2.04), "立ち食い「雨粒」\n煮込み・おにぎり", 0.145),
        sign("north_repair_sign_text", "Physical Japanese sign · 端末修理", "north_terminal_repair", (0, 2.60, -2.15), "端末修理・中古トロン\n基板洗浄／部品交換", 0.14),
        sign("north_housing_nameplate_text", "Physical Japanese nameplate · 北町", "north_machiya", (0, 3.95, -2.70), "北町寄合長屋", 0.105, color=(0.84, 0.74, 0.54, 1.0)),
    ]
    ar_displays = [
        sign("north_ar_menu_text", "Hideable AR menu · 0.8 × 0.5 m", "north_yatai", (0.0, 2.63, -1.96), "本日の煮込み\nおにぎり二種 · 営業 18–02時", 0.105, ar=True, bounds=(0.8, 0.5), color=(0.54, 0.80, 0.84, 1.0)),
        sign("north_ar_repair_text", "Hideable AR repair notice · 2.0 × 0.7 m", "north_terminal_repair", (0.0, 2.79, -2.04), "端末修理 20時まで\n旧型トロン・部品持込歓迎", 0.14, ar=True, bounds=(2.0, 0.7), color=(0.96, 0.65, 0.35, 1.0)),
    ]
    return {
        "physical": {"slot": {"key": "north_physical_japanese_signage", "name": "North physical Japanese signage"}, "children": physical},
        "ar": {"slot": {"key": "north_ar_displays", "name": "North hideable AR displays"}, "children": ar_displays},
    }
