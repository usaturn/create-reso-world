"""North-frontage asset catalog, detailed assembly placement and native signage."""
from __future__ import annotations

import math
from typing import Any

from modeling.tokyo_nova import geometry as geo
from modeling.tokyo_nova.props import Assembly, create

FOOD_STALL_OFFSET = (0.0, 0.18, -1.0)
REPAIR_SHOP_OFFSET = (0.0, 0.15, 1.8)
HOUSING_OFFSET = (0.0, 0.0, -2.5)
SOUTH_FACING_YAW = math.pi
Vec3 = tuple[float, float, float]


def asset_catalog() -> list[dict[str, Any]]:
    """Return the explicit design catalog for the north block's modeled assemblies."""
    return [
        {
            "kind": "food_stall", "dimensions": [4.5, 2.7525, 2.099], "units": "meters",
            "materials": ["wood", "painted_metal", "exposed_metal", "rust", "ceramic", "plastic", "cloth", "warm_light"],
            "parts": ["mismatched corrugated awning and braces", "rolled-rim service counter", "lidded steel pots", "ceramic bowls and chopsticks", "condiment trays", "reusable CFC containers", "vented under-counter refrigerator", "fan and task light", "physical Japanese menu board"],
            "wear": ["uneven replacement sheets", "rust streaks", "painted and exposed frame edges", "reused wood counter"],
            "placement": {"building_key": "north_yatai", "front": "south", "origin_offset": [0, 0.18, -1.0]},
            "recognition": "busy standing counter under a mismatched ribbed awning; lidded pots and ceramic serviceware are visible from the aisle",
        },
        {
            "kind": "terminal_repair", "dimensions": [4.8, 3.36, 5.1475], "units": "meters",
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
            "placement": {"building_key": "north_machiya", "front": "south", "origin_offset": [0, 0, -2.5]},
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
            "kind": "north_facility_connector", "dimensions": [5.61, 0.579, 0.88], "units": "meters",
            "materials": ["painted_metal", "exposed_metal", "rust", "rubber"],
            "parts": ["canopy sized between the real food-awning post and repair-shop header", "two bearing supports from those attachment points", "corrugation ribs", "rain gutter and downspout", "shared cable tray"],
            "wear": ["mismatched roofing sheet", "rust at bearing brackets", "repaired cable sleeve"],
            "placement": {"between": ["north_yatai", "north_terminal_repair"], "attachment_points": "derived from placed facade geometry", "walk_clearance_m": 3.0},
            "recognition": "supported continuous rain cover bears on both neighboring facilities and leaves the passage below clear",
        },
        {
            "kind": "ar_menu", "dimensions": [0.8, 0.5, 0.0], "units": "meters",
            "materials": ["cool_light"],
            "parts": ["bounded Japanese TextRenderer plane", "separate hideable group", "no opaque backing or support", "restrained emission tint", "explicit 0.8 × 0.5 m bounds"],
            "wear": ["steady low-luminance text tint; no animation"],
            "placement": {"building_key": "north_yatai", "group": "north_ar_displays", "front": "south", "clear_of_physical_sign_m": 0.75},
            "recognition": "separately hideable 0.8 m × 0.5 m Japanese menu text in open space south of the physical sign",
        },
        {
            "kind": "ar_repair_ad", "dimensions": [2.0, 0.7, 0.0], "units": "meters",
            "materials": ["warm_light"],
            "parts": ["bounded Japanese TextRenderer plane", "separate hideable group", "no opaque backing or support", "restrained emission tint", "explicit 2.0 × 0.7 m bounds"],
            "wear": ["steady low-brightness text tint; no flashing"],
            "placement": {"building_key": "north_terminal_repair", "group": "north_ar_displays", "front": "south", "clear_of_physical_sign_m": 0.75},
            "recognition": "separately hideable 2.0 m × 0.7 m Japanese repair text in open space south of the physical fascia",
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


def _placed_point(origin: tuple[float, float, float], yaw: float, point: Vec3) -> Vec3:
    cosine, sine = math.cos(yaw), math.sin(yaw)
    return (
        origin[0] + point[0] * cosine + point[2] * sine,
        origin[1] + point[1],
        origin[2] - point[0] * sine + point[2] * cosine,
    )


def _facility_connector(food: Assembly, repair: Assembly) -> Assembly:
    """Bridge the facilities from their actual awning-post and header-bearing points."""
    food_anchor = food.attachments["shared_canopy"]
    repair_anchor = repair.attachments["shared_canopy"]
    left_x, right_x = food_anchor[0], repair_anchor[0]
    if right_x <= left_x:
        raise ValueError("north connector attachment points must run from food stall to repair shop")
    span = right_x - left_x
    z_margin = 0.30
    z_min = min(food_anchor[2], repair_anchor[2]) - z_margin
    z_max = max(food_anchor[2], repair_anchor[2]) + z_margin
    center_x, center_z = (left_x + right_x) / 2, (z_min + z_max) / 2
    roof_thickness = 0.075
    roof_bottom = max(food_anchor[1], repair_anchor[1]) + 0.08
    roof_center_y = roof_bottom + roof_thickness / 2
    origin = (center_x, 0.0, center_z)

    def local(point: Vec3) -> Vec3:
        return (point[0] - origin[0], point[1], point[2] - origin[2])

    parts = [geo.beveled_box("shared_mismatched_rain_canopy", (0, roof_center_y, 0), (span, roof_thickness, z_max - z_min), 0.025, "painted_metal")]
    for index, z_fraction in enumerate((-0.34, 0.0, 0.34)):
        z = z_fraction * (z_max - z_min)
        parts.append(geo.pipe(f"connector_corrugation_{index}", (-span / 2 + 0.06, roof_center_y + roof_thickness / 2, z), (span / 2 - 0.06, roof_center_y + roof_thickness / 2, z), 0.014, "exposed_metal"))
    for key, anchor in (("food_stall", food_anchor), ("terminal_repair", repair_anchor)):
        bearing_end = (anchor[0], roof_bottom + 0.005, anchor[2])
        parts.append(geo.pipe(f"connector_{key}_support", local(anchor), local(bearing_end), 0.035, "rust"))
    gutter_z = z_max - center_z - 0.045
    parts.append(geo.pipe("shared_rain_gutter", (-span / 2, roof_bottom - 0.035, gutter_z), (span / 2, roof_bottom - 0.035, gutter_z), 0.035, "exposed_metal"))
    parts.append(geo.pipe("shared_gutter_downspout", (span / 2 - 0.035, roof_bottom - 0.035, gutter_z), (span / 2 - 0.035, repair_anchor[1], gutter_z), 0.03, "rust"))
    parts.append(geo.box("shared_repaired_cable_tray", (0, roof_bottom - 0.15, 0), (span - 0.16, 0.06, 0.12), "exposed_metal"))
    return Assembly(
        "north_facility_connector",
        "Supported canopy and service tray",
        origin,
        0.0,
        parts,
        {"food_stall": food_anchor, "terminal_repair": repair_anchor},
    )

def build_north_sector(layout: dict[str, Any]) -> list[Assembly]:
    """Place deterministic reusable assemblies from stable keys and measured attachment points."""
    buildings = {entry["key"]: entry for entry in layout["buildings"]}
    assemblies: list[Assembly] = []

    def place(kind: str, building_key: str, offset: Vec3, yaw: float) -> Assembly:
        center = buildings[building_key]["center"]
        assembly_origin = tuple(center[index] + offset[index] for index in range(3))
        assembly = create(kind, assembly_origin, yaw)
        assemblies.append(assembly)
        return assembly

    food = place("food_stall", "north_yatai", FOOD_STALL_OFFSET, SOUTH_FACING_YAW)
    food.attachments["shared_canopy"] = _placed_point(food.origin, food.rotation, (-2.15, 2.78, 0.04))
    repair = place("terminal_repair", "north_terminal_repair", REPAIR_SHOP_OFFSET, SOUTH_FACING_YAW)
    repair.attachments["shared_canopy"] = _placed_point(repair.origin, repair.rotation, (2.31, 3.22, 3.12))
    place("patched_housing_facade", "north_machiya", HOUSING_OFFSET, 0.0)
    # Fit the phone on the actual ESD mat footprint and derive its underside from the top.
    mat = next(part for part in repair.transformed_parts() if part.name == "anti_static_mat")
    mat_x = tuple(vertex[0] for vertex in mat.vertices)
    mat_y = tuple(vertex[1] for vertex in mat.vertices)
    mat_z = tuple(vertex[2] for vertex in mat.vertices)
    phone_template = create("pocket_phone", (0.0, 0.0, 0.0))
    phone_min, _ = phone_template.bounds
    phone_origin = (
        (min(mat_x) + max(mat_x)) / 2 - 0.60,
        max(mat_y) - phone_min[1],
        (min(mat_z) + max(mat_z)) / 2 - 0.14,
    )
    assemblies.append(create("pocket_phone", phone_origin, 0.0))
    assemblies.extend((_frontage_pavement(), _facility_connector(food, repair)))
    return assemblies


def collision_manifest_entries(layout: dict[str, Any]) -> dict[str, Any]:
    """Return precise colliders for visible solid north walls and furniture only."""
    assemblies = {assembly.kind: assembly for assembly in build_north_sector(layout)}
    housing_parts = assemblies["patched_housing_facade"].parts
    parts_by_kind = {
        "food_stall": {"counter_body", "counter_top"},
        "terminal_repair": {
            "repair_shop_rear_wall", "repair_shop_side_wall_-2.31", "repair_shop_side_wall_2.31",
            "repair_front_pier_-2.31", "repair_front_pier_2.31", "repair_front_header",
            "repair_window_glass_0", "repair_window_glass_1", "retracted_rolling_shutter",
        },
        "patched_housing_facade": {
            part.name for part in housing_parts
            if part.name.startswith("housing_masonry_") or part.name.startswith("window_glazing_")
        } | {"entry_door_leaf"},
    }
    colliders: list[dict[str, Any]] = []
    for kind, names in parts_by_kind.items():
        parts = {part.name: part for part in assemblies[kind].transformed_parts()}
        for part_name in sorted(names):
            part = parts.get(part_name)
            if part is None:
                raise ValueError(f"collider source part does not exist: {kind}/{part_name}")
            minimum = tuple(min(vertex[axis] for vertex in part.vertices) for axis in range(3))
            maximum = tuple(max(vertex[axis] for vertex in part.vertices) for axis in range(3))
            size = [maximum[axis] - minimum[axis] for axis in range(3)]
            if any(extent <= 0.0 for extent in size):
                raise ValueError(f"collider source part must have positive volume: {kind}/{part_name}")
            center = [(minimum[axis] + maximum[axis]) / 2 for axis in range(3)]
            key = f"north_collision_{kind}_{part_name}"
            colliders.append({
                "slot": {
                    "key": key,
                    "name": f"North collider · {kind} · {part_name}",
                    "position": center,
                    "rotation": [0.0, 0.0, 0.0, 1.0],
                    "scale": [1.0, 1.0, 1.0],
                },
                "components": [{
                    "key": f"{key}_box_collider",
                    "type": "FrooxEngine.BoxCollider",
                    "fields": {
                        "Enabled": True,
                        "Type": "Static",
                        "CharacterCollider": True,
                        "Offset": [0.0, 0.0, 0.0],
                        "Size": size,
                    },
                }],
            })
    return {"slot": {"key": "north_collision_geometry", "name": "North detailed collision geometry"}, "children": colliders}


def sign_manifest_entries(layout: dict[str, Any]) -> dict[str, Any]:
    """Place physical text on south-facing sign faces and AR text clear of those faces."""
    buildings = {entry["key"]: entry for entry in layout["buildings"]}

    def origin(building_key: str, offset: Vec3) -> Vec3:
        center = buildings[building_key]["center"]
        return tuple(float(center[index]) + offset[index] for index in range(3))  # type: ignore[return-value]

    def south_face(building_key: str, offset: Vec3, yaw: float, local_face: Vec3, outward: float = 0.005) -> Vec3:
        base = origin(building_key, offset)
        face = _placed_point(base, yaw, local_face)
        return (face[0], face[1], face[2] - outward)

    south_rotation = [0.0, math.sin(SOUTH_FACING_YAW / 2), 0.0, math.cos(SOUTH_FACING_YAW / 2)]

    def sign(key: str, name: str, position: Vec3, text: str, size: float, *, ar: bool = False, bounds: tuple[float, float] | None = None, color: tuple[float, float, float, float] = (0.95, 0.78, 0.49, 1.0)) -> dict[str, Any]:
        component: dict[str, Any] = {"Text": text, "Size": size, "Color": list(color), "ParseRichText": False}
        if ar and bounds is not None:
            component.update({"Bounded": True, "BoundsSize": list(bounds), "HorizontalAutoSize": False, "VerticalAutoSize": False})
        return {"slot": {"key": key, "name": name, "position": list(position), "rotation": south_rotation}, "components": [{"key": f"{key}_text", "type": "FrooxEngine.TextRenderer", "fields": component}]}

    food_face = south_face("north_yatai", FOOD_STALL_OFFSET, SOUTH_FACING_YAW, (0.0, 2.40, 1.071))
    repair_face = south_face("north_terminal_repair", REPAIR_SHOP_OFFSET, SOUTH_FACING_YAW, (0.0, 2.45, 3.9575))
    housing_face = south_face("north_machiya", HOUSING_OFFSET, 0.0, (0.0, 3.95, -0.3175))
    physical = [
        sign("north_yatai_sign_text", "Physical Japanese sign · 立ち食い雨粒", food_face, "立ち食い「雨粒」\n煮込み・おにぎり", 0.145),
        sign("north_repair_sign_text", "Physical Japanese sign · 端末修理", repair_face, "端末修理・中古トロン\n基板洗浄／部品交換", 0.14),
        sign("north_housing_nameplate_text", "Physical Japanese nameplate · 北町", housing_face, "北町寄合長屋", 0.105, color=(0.84, 0.74, 0.54, 1.0)),
    ]
    ar_displays = [
        sign("north_ar_menu_text", "Hideable AR menu · 0.8 × 0.5 m", (food_face[0], food_face[1], food_face[2] - 0.75), "本日の煮込み\nおにぎり二種 · 営業 18–02時", 0.105, ar=True, bounds=(0.8, 0.5), color=(0.54, 0.80, 0.84, 1.0)),
        sign("north_ar_repair_text", "Hideable AR repair notice · 2.0 × 0.7 m", (repair_face[0], repair_face[1], repair_face[2] - 0.75), "端末修理 20時まで\n旧型トロン・部品持込歓迎", 0.14, ar=True, bounds=(2.0, 0.7), color=(0.96, 0.65, 0.35, 1.0)),
    ]
    return {
        "physical": {"slot": {"key": "north_physical_japanese_signage", "name": "North physical Japanese signage"}, "children": physical},
        "ar": {"slot": {"key": "north_ar_displays", "name": "North hideable AR displays"}, "children": ar_displays},
    }
