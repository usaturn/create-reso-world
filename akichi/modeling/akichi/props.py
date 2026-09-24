"""Deterministic slum prop builders for the akichi cyberpunk district.

Stalls, shacks, club facades, AR ads, catenary cables, rubble scatter prototypes,
burnt vehicle husks and junk piles. Every builder returns a
:class:`modeling.akichi.buildings.Assembly` whose parts are prop-local meshes in
Resonite coordinates (Y up, metres) with the assembly origin on the ground under
the prop's centre; ``Assembly.rotation`` is radians, as everywhere else in the
pipeline, while the specs handed over by :mod:`modeling.akichi.layout` carry
degrees, so each builder converts once.

Variation is driven only by ``random.Random(seed + numeric id suffix)`` - never by
``hash()``, dict order or set order - so repeated runs are bit-identical. Every
material name is a key of :data:`modeling.akichi.materials.MATERIALS`; the brief's
"plastic 系" has no palette entry, so the junk heap uses rusted sheet (``rust``)
for the salvaged-plastic drums instead.
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence

from modeling.akichi import geometry as geo
from modeling.akichi.buildings import Assembly

Vec3 = tuple[float, float, float]

# Nominal prop sizes; the stall and club figures mirror layout.py's placement rules.
STALL_WIDTH, STALL_DEPTH, STALL_HEIGHT = 2.4, 1.8, 2.4
CLUB_DEPTH, CLUB_HEIGHT = 5.0, 3.5
VEHICLE_LENGTH = 4.0

# Catenary polyline resolution and the round cross-section of one cable segment.
CABLE_SEGMENTS = 8
CABLE_PIPE_SEGMENTS = 6

# Scatter prototypes are shared by every call, so they are built from one fixed seed.
RUBBLE_SEED = 250925

# Salvage palette for the junk heap (brief: corrugated/dark_metal/painted_metal_faded/plastic 系).
_JUNK_PILE_MATERIALS: tuple[str, ...] = ("corrugated", "dark_metal", "painted_metal_faded", "rust")

# Counter goods per stall kind, so the layout's kind field colours the merchandise.
_STALL_GOODS: dict[str, tuple[str, ...]] = {
    "junk": ("rust", "exposed_metal", "dark_metal"),
    "parts": ("exposed_metal", "dark_metal", "corrugated"),
    "food": ("plywood", "tarp_orange", "painted_metal_faded"),
}

_CORNERS = ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))
_BOX_FACES = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))


# --- shared helpers -----------------------------------------------------------


def _seeded(spec: dict, seed: int) -> random.Random:
    """Per-spec rng: the numeric suffix of the id offsets the caller seed.

    ``hash()`` is randomised per process, so the offset is read straight from the
    id ("stall-07" -> 7) to keep the sequence stable across runs.
    """
    digits = "".join(character for character in str(spec.get("id", "")) if character.isdigit())
    return random.Random(seed + (int(digits) if digits else 0))


def _vec3(value: Sequence[float], name: str) -> Vec3:
    if len(value) != 3:
        raise ValueError(f"{name} must have three coordinates")
    return (float(value[0]), float(value[1]), float(value[2]))


def _yaw_box(name: str, center: Vec3, size: Vec3, radians: float, material: str) -> geo.MeshData:
    """Box rotated about local Y by ``radians`` (the Assembly yaw convention)."""
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    cosine, sine = math.cos(radians), math.sin(radians)
    vertices = []
    for dx, dy, dz in _CORNERS:
        x, z = dx * hx, dz * hz
        vertices.append((cx + x * cosine + z * sine, cy + dy * hy, cz - x * sine + z * cosine))
    return geo.mesh(name, vertices, _BOX_FACES, material)


def _lean_box(name: str, center: Vec3, size: Vec3, radians: float, material: str) -> geo.MeshData:
    """Box rotated about local X by ``radians``, so it leans toward +/-Z."""
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    cosine, sine = math.cos(radians), math.sin(radians)
    vertices = []
    for dx, dy, dz in _CORNERS:
        y, z = dy * hy, dz * hz
        vertices.append((cx + dx * hx, cy + y * cosine - z * sine, cz + y * sine + z * cosine))
    return geo.mesh(name, vertices, _BOX_FACES, material)


def _jitter_box(name: str, center: Vec3, size: Vec3, jitter: float, rng: random.Random, material: str) -> geo.MeshData:
    """Box with every corner displaced by up to ``jitter`` (a wrecked silhouette)."""
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    vertices = tuple(
        (cx + dx * hx + rng.uniform(-jitter, jitter),
         cy + dy * hy + rng.uniform(-jitter, jitter),
         cz + dz * hz + rng.uniform(-jitter, jitter))
        for dx, dy, dz in _CORNERS
    )
    return geo.mesh(name, vertices, _BOX_FACES, material)


def _grounded(name: str, part: geo.MeshData) -> geo.MeshData:
    """Re-emit ``part`` with its lowest vertex sitting exactly on y = 0."""
    lift = -min(vertex[1] for vertex in part.vertices)
    return geo.mesh(name, [(v[0], v[1] + lift, v[2]) for v in part.vertices], part.faces, part.material)


def _merge(name: str, parts: Sequence[geo.MeshData], material: str) -> geo.MeshData:
    """Concatenate meshes into one MeshData, re-indexing every face."""
    vertices: list[Vec3] = []
    faces: list[geo.Face] = []
    for part in parts:
        offset = len(vertices)
        vertices.extend(part.vertices)
        faces.extend(tuple(index + offset for index in face) for face in part.faces)
    return geo.mesh(name, vertices, faces, material)


def _gable_roof(name: str, center: Vec3, width: float, height: float, depth: float, ridge_axis: str, material: str) -> geo.MeshData:
    """Gable roof covering ``width`` (X) x ``depth`` (Z) with its base at ``center.y - height/2``.

    ``geometry.prism`` always runs its ridge along Z, so an X ridge is produced by
    building the prism with swapped extents and rotating it 90 degrees about Y - a
    proper rotation, which keeps the outward face winding intact.
    """
    if ridge_axis == "Z":
        return geo.prism(name, center, (width, height, depth), material)
    base = geo.prism(name, (0.0, 0.0, 0.0), (depth, height, width), material)
    cx, cy, cz = center
    return geo.mesh(name, [(cx + v[2], cy + v[1], cz - v[0]) for v in base.vertices], base.faces, material)


def _gable_surface(x: float, z: float, base_y: float, rise: float, width: float, depth: float, ridge_axis: str) -> float:
    """Height of a gable roof's upper surface at (x, z)."""
    if ridge_axis == "Z":
        return base_y + rise * max(0.0, 1.0 - abs(x) / (width / 2))
    return base_y + rise * max(0.0, 1.0 - abs(z) / (depth / 2))


# --- stall --------------------------------------------------------------------


def build_stall(spec: dict, seed: int) -> Assembly:
    """Junk stall: four posts, counter, tarp awning, counter goods and a lantern.

    The counter is the brief's 1.8 x 0.9 x 0.1 plywood box read as a front apron
    with its top edge at 0.9m, plus the top slab the merchandise actually rests on.
    """
    rng = _seeded(spec, seed)
    half_w, half_d = STALL_WIDTH / 2, STALL_DEPTH / 2
    post = 0.08
    parts: list[geo.MeshData] = []
    for index, (sx, sz) in enumerate(((-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0))):
        parts.append(geo.box(f"post-{index}", (sx * (half_w - post / 2), STALL_HEIGHT / 2, sz * (half_d - post / 2)),
                             (post, STALL_HEIGHT, post), "dark_metal"))

    counter_h = 0.9
    parts.append(geo.box("counter-front", (0.0, counter_h / 2, half_d - 0.05), (1.8, counter_h, 0.1), "plywood"))
    parts.append(geo.box("counter-top", (0.0, counter_h - 0.05, half_d - 0.45), (1.8, 0.1, 0.7), "plywood"))

    goods = _STALL_GOODS.get(str(spec.get("kind", "")), _STALL_GOODS["junk"])
    for index in range(rng.randint(5, 9)):
        x, z = rng.uniform(-0.75, 0.75), rng.uniform(0.18, 0.72)
        material = rng.choice(goods)
        if rng.random() < 0.5:
            size = (rng.uniform(0.12, 0.3), rng.uniform(0.12, 0.32), rng.uniform(0.12, 0.3))
            parts.append(geo.box(f"goods-box-{index}", (x, counter_h + size[1] / 2, z), size, material))
        else:
            height = rng.uniform(0.12, 0.34)
            parts.append(geo.cylinder(f"goods-can-{index}", (x, counter_h + height / 2, z),
                                      rng.uniform(0.05, 0.14), height, 8, material, axis="Y"))

    rise, overhang = 0.35, 0.15
    roof_w, roof_d = STALL_WIDTH + 2 * overhang, STALL_DEPTH + 2 * overhang
    ridge = "X" if roof_w >= roof_d else "Z"
    parts.append(_gable_roof("awning", (0.0, STALL_HEIGHT + rise / 2, 0.0), roof_w, rise, roof_d, ridge, str(spec["awning"])))

    # The lantern hangs over the counter, its top just under the awning slope.
    lantern_z = STALL_DEPTH / 2 - 0.15
    lantern_top = _gable_surface(0.0, lantern_z, STALL_HEIGHT, rise, roof_w, roof_d, ridge) - 0.02
    lantern_center = (0.0, lantern_top - 0.175, lantern_z)
    parts.append(geo.box("lantern", lantern_center, (0.25, 0.35, 0.25), "warm_light"))

    return Assembly(
        kind="stall",
        name=spec["id"],
        origin=(float(spec["center"][0]), 0.0, float(spec["center"][1])),
        rotation=math.radians(float(spec["rotation"])),
        parts=parts,
        attachments={"lantern": lantern_center},
    )


# --- shack --------------------------------------------------------------------


def build_shack(spec: dict, seed: int) -> Assembly:
    """Lean-to shack: mixed-material walls, tin gable roof, door, window and streaks.

    Wall materials are dealt round-robin through ``spec["wall_mix"]``, so every
    named material is guaranteed to appear on the four walls.
    """
    rng = _seeded(spec, seed)
    width, depth = float(spec["footprint"][0]), float(spec["footprint"][1])
    height = float(spec["height"])
    wall_mix = [str(name) for name in spec["wall_mix"]]
    half_w, half_d, wall = width / 2, depth / 2, 0.08

    parts: list[geo.MeshData] = []
    walls = (
        ("front", (0.0, height / 2, half_d - wall / 2), (width, height, wall)),
        ("back", (0.0, height / 2, -half_d + wall / 2), (width, height, wall)),
        ("left", (-half_w + wall / 2, height / 2, 0.0), (wall, height, depth - 2 * wall)),
        ("right", (half_w - wall / 2, height / 2, 0.0), (wall, height, depth - 2 * wall)),
    )
    for index, (label, center, size) in enumerate(walls):
        parts.append(geo.box(f"wall-{label}", center, size, wall_mix[index % len(wall_mix)]))

    parts.append(geo.box("door", (0.0, 0.95, half_d + 0.01), (0.8, 1.9, 0.06), "plywood"))
    parts.append(geo.box("door-handle", (0.28, 1.0, half_d + 0.07), (0.06, 0.06, 0.06), "dark_metal"))
    if rng.random() < 0.6:
        window_y = rng.uniform(1.3, max(1.35, height - 0.5))
        parts.append(geo.box("window", (half_w + 0.01, window_y, rng.uniform(-half_d * 0.4, half_d * 0.4)),
                             (0.06, 0.6, 0.6), "glass_dark"))

    for index in range(rng.randint(2, 5)):
        length = rng.uniform(0.4, 1.0)
        top = rng.uniform(max(0.6, height - 0.6), height - 0.05)
        if rng.random() < 0.5:
            side = rng.choice((-1.0, 1.0))
            center = (rng.uniform(-half_w + 0.2, half_w - 0.2), top - length / 2, side * (half_d + 0.015))
            size = (0.05, length, 0.03)
        else:
            side = rng.choice((-1.0, 1.0))
            center = (side * (half_w + 0.015), top - length / 2, rng.uniform(-half_d + 0.2, half_d - 0.2))
            size = (0.03, length, 0.05)
        parts.append(geo.box(f"streak-{index}", center, size, "rust_dark"))

    overhang = 0.2
    roof_w, roof_d = width + 2 * overhang, depth + 2 * overhang
    rise = min(0.6, 0.25 * min(roof_w, roof_d))
    ridge = "Z" if depth >= width else "X"
    parts.append(_gable_roof("roof", (0.0, height + rise / 2, 0.0), roof_w, rise, roof_d, ridge,
                             rng.choice(("corrugated", "corrugated_rusted"))))

    # Roof weights: tyres laid flat on the slope, so each disc is built along the
    # local surface normal rather than standing upright on the tin.
    for index in range(rng.randint(1, 2)):
        if ridge == "Z":
            wx = rng.choice((-1.0, 1.0)) * rng.uniform(0.35, 0.8) * (roof_w / 2)
            wz = rng.uniform(-0.35, 0.35) * roof_d
            normal = (rise / (roof_w / 2) * (1.0 if wx >= 0 else -1.0), 1.0, 0.0)
        else:
            wz = rng.choice((-1.0, 1.0)) * rng.uniform(0.35, 0.8) * (roof_d / 2)
            wx = rng.uniform(-0.35, 0.35) * roof_w
            normal = (0.0, 1.0, rise / (roof_d / 2) * (1.0 if wz >= 0 else -1.0))
        length = math.sqrt(normal[0] ** 2 + normal[1] ** 2 + normal[2] ** 2)
        unit = (normal[0] / length, normal[1] / length, normal[2] / length)
        surface = _gable_surface(wx, wz, height, rise, roof_w, roof_d, ridge) + 0.1
        parts.append(geo.pipe(f"roof-weight-{index}",
                              (wx - unit[0] * 0.09, surface - unit[1] * 0.09, wz - unit[2] * 0.09),
                              (wx + unit[0] * 0.09, surface + unit[1] * 0.09, wz + unit[2] * 0.09),
                              0.25, "dark_metal", segments=8))

    return Assembly(
        kind="shack",
        name=spec["id"],
        origin=(float(spec["center"][0]), 0.0, float(spec["center"][1])),
        rotation=math.radians(float(spec["rotation"])),
        parts=parts,
        attachments={},
    )


# --- club ---------------------------------------------------------------------


def build_club(spec: dict, seed: int) -> Assembly:
    """Nightlife facade: solid block, curtained doorway, neon box sign, posters, A-board.

    Only suggestion is modelled - neon, noren curtains and pasted notices. The
    ``sign`` attachment sits at the neon frame centre, which is where layout.py's
    club sign offset ([0, 2.6, 2.56]) expects the TextRenderer to land.
    """
    rng = _seeded(spec, seed)
    width = float(spec["width"])
    neon = str(spec["neon"])
    front = CLUB_DEPTH / 2
    parts: list[geo.MeshData] = [geo.box("body", (0.0, CLUB_HEIGHT / 2, 0.0), (width, CLUB_HEIGHT, CLUB_DEPTH), "concrete_mid")]

    parts.append(geo.box("doorway", (0.0, 1.0, front + 0.01), (1.7, 2.0, 0.06), "sign_backing"))
    for index, sx in enumerate((-0.42, 0.42)):
        parts.append(_yaw_box(f"curtain-{index}", (sx, 1.45, front + 0.07), (0.72, 1.1, 0.06),
                              rng.uniform(-0.1, 0.1), "tarp_blue"))

    sign_w, sign_h, sign_y = min(width - 0.8, 3.2), 0.9, 2.6
    parts.append(geo.box("sign-backing", (0.0, sign_y, front + 0.025), (sign_w, sign_h, 0.05), "sign_backing"))
    parts.append(geo.box("sign-border-top", (0.0, sign_y + sign_h / 2 + 0.04, front + 0.05), (sign_w + 0.16, 0.08, 0.08), neon))
    parts.append(geo.box("sign-border-bottom", (0.0, sign_y - sign_h / 2 - 0.04, front + 0.05), (sign_w + 0.16, 0.08, 0.08), neon))
    parts.append(geo.box("sign-border-left", (-sign_w / 2 - 0.04, sign_y, front + 0.05), (0.08, sign_h + 0.16, 0.08), neon))
    parts.append(geo.box("sign-border-right", (sign_w / 2 + 0.04, sign_y, front + 0.05), (0.08, sign_h + 0.16, 0.08), neon))
    parts.append(geo.box("entrance-line", (0.0, 2.03, front + 0.05), (1.9, 0.05, 0.05), "neon_pink"))

    for index in range(rng.randint(3, 6)):
        x = rng.choice((-1.0, 1.0)) * rng.uniform(0.95, max(1.0, width / 2 - 0.4))
        parts.append(_yaw_box(f"poster-{index}", (x, rng.uniform(0.9, 2.4), front + 0.02), (0.3, 0.4, 0.03),
                              rng.uniform(-0.15, 0.15), rng.choice(("plywood", "patched_concrete"))))

    # A-board on the pavement: two boards hinged at the top, each with a lit rim.
    lean, hinge_z, board_x = math.radians(20.0), front + 0.45, width / 2 - 0.55
    for index, direction in enumerate((1.0, -1.0)):
        tilt = lean * direction
        board_z = hinge_z - direction * 0.16
        parts.append(_lean_box(f"aboard-board-{index}", (board_x, 0.43, board_z), (0.6, 0.9, 0.05), tilt, "plywood"))
        parts.append(_lean_box(f"aboard-trim-{index}", (board_x, 0.43 + 0.45 * math.cos(lean), board_z + direction * 0.154),
                               (0.5, 0.06, 0.05), tilt, neon))

    return Assembly(
        kind="club",
        name=spec["id"],
        origin=(float(spec["center"][0]), 0.0, float(spec["center"][1])),
        rotation=math.radians(float(spec["rotation"])),
        parts=parts,
        attachments={"sign": (0.0, sign_y, front + 0.06)},
    )


# --- ads ----------------------------------------------------------------------


def _sign_panel(width: float, height: float, color: str, frame: str) -> list[geo.MeshData]:
    """Double-sided lightbox: dark core, emissive face on both sides, four frame edges.

    Both faces are lit because layout.py's ``_FACE_ROTATION`` is self-consistent
    with a local +Z front for the holo panels but inverted for the north/south
    wall ads; a single-faced panel would show its dark backing to the street for
    six of the eight wall ads.
    """
    parts = [geo.box("sign-core", (0.0, 0.0, 0.0), (width + 0.1, height + 0.1, 0.1), "sign_backing")]
    for index, side in enumerate((-1.0, 1.0)):
        parts.append(geo.box(f"sign-face-{index}", (0.0, 0.0, side * 0.07), (width, height, 0.05), color))
    edge_w, edge_h = width + 0.16, height + 0.16
    parts.append(geo.box("sign-frame-top", (0.0, (height + 0.1) / 2 + 0.03, 0.0), (edge_w, 0.06, 0.2), frame))
    parts.append(geo.box("sign-frame-bottom", (0.0, -(height + 0.1) / 2 - 0.03, 0.0), (edge_w, 0.06, 0.2), frame))
    parts.append(geo.box("sign-frame-left", (-edge_w / 2 + 0.03, 0.0, 0.0), (0.06, edge_h, 0.2), frame))
    parts.append(geo.box("sign-frame-right", (edge_w / 2 - 0.03, 0.0, 0.0), (0.06, edge_h, 0.2), frame))
    return parts


def _holo_panel(rng: random.Random, width: float, height: float, frame: str, panel_y: float) -> list[geo.MeshData]:
    """Hologram stand: glowing plane with scanlines, frames, posts and a base.

    ``panel_y`` is the panel centre's world height, so the local ground sits at
    ``-panel_y`` and the posts can be sized from the panel's bottom edge down to
    it. A grounded panel (layout's ``on_posts=False``) is slotted into a plinth
    and drops the bottom rail, which would otherwise sit below the street.
    """
    parts = [geo.box("holo-panel", (0.0, 0.0, 0.0), (width, height, 0.03), "holo_panel")]
    parts.append(geo.box("holo-frame-top", (0.0, height / 2 + 0.04, 0.0), (width + 0.16, 0.08, 0.08), frame))
    lines = rng.randint(4, 7)
    for index in range(lines):
        y = -height / 2 + height * (index + 1) / (lines + 1)
        parts.append(geo.box(f"scanline-{index}", (0.0, y, 0.02), (width - 0.2, 0.02, 0.01), "neon_cyan"))

    ground = -panel_y
    bottom = panel_y - height / 2
    if bottom > 0.4:  # post-mounted panel standing in the street
        parts.append(geo.box("holo-frame-bottom", (0.0, -height / 2 - 0.04, 0.0), (width + 0.16, 0.08, 0.08), frame))
        parts.append(geo.box("holo-base", (0.0, ground + 0.05, 0.0), (width + 0.35, 0.1, 0.45), "dark_metal"))
        post_height = bottom - 0.1
        for index, sx in enumerate((-1.0, 1.0)):
            x = sx * max(0.06, width / 2 - 0.12)
            parts.append(geo.cylinder(f"holo-post-{index}", (x, ground + 0.1 + post_height / 2, 0.0),
                                      0.05, post_height, 8, "dark_metal", axis="Y"))
    else:
        # Grounded panel slotted into its plinth: the bottom rail would be buried
        # (layout rounds the panel centre to 2dp), so the plinth replaces it.
        parts.append(geo.box("holo-base", (0.0, ground + 0.14, 0.0), (width + 0.35, 0.28, 0.45), "dark_metal"))
    return parts


def build_ad(spec: dict, seed: int) -> Assembly:
    """One AR ad: wall panel, holo stand, rooftop board or hanging lantern.

    ``spec["color"]`` lights the wall, rooftop and lantern kinds; the holo recipe
    keeps the fixed ``holo_panel`` plane with ``neon_cyan`` scanlines instead.
    """
    rng = _seeded(spec, seed)
    kind = str(spec["kind"])
    width, height = float(spec["size"][0]), float(spec["size"][1])
    color, frame = str(spec["color"]), str(spec["frame"])
    position = _vec3(spec["position"], "position")

    if kind in ("wall", "rooftop"):
        parts = _sign_panel(width, height, color, frame)
        bottom = -(height + 0.1) / 2
        if kind == "rooftop":
            for index, (sx, sz) in enumerate(((-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0))):
                parts.append(geo.box(f"rooftop-leg-{index}", (sx * max(0.15, width / 2 - 0.2), bottom - 0.5, sz * 0.09),
                                     (0.07, 1.0, 0.07), "dark_metal"))
        else:
            for index, sx in enumerate((-1.0, 1.0)):
                parts.append(geo.box(f"ad-bracket-{index}", (sx * max(0.12, width / 2 - 0.3), bottom - 0.2, -0.02),
                                     (0.07, 0.4, 0.06), "dark_metal"))
    elif kind == "holo":
        parts = _holo_panel(rng, width, height, frame, position[1])
    elif kind == "lantern":
        parts = [
            geo.box("lantern-body", (0.0, 0.0, 0.0), (width, height, width), color),
            geo.box("lantern-rod", (0.0, height / 2 + 0.12, 0.0), (0.05, 0.24, 0.05), "dark_metal"),
        ]
    else:
        raise ValueError(f"unknown ad kind: {kind!r}")

    return Assembly(
        kind="ad",
        name=spec["id"],
        origin=position,
        rotation=math.radians(float(spec["rotation"])),
        parts=parts,
        attachments={},
    )


# --- cables -------------------------------------------------------------------


def build_cable(spec: dict) -> Assembly:
    """Catenary cable between two world-space endpoints, as 8 straight segments.

    ``y(t) = lerp(y0, y1, t) - 4 * sag * t * (1 - t)`` for t = 0, 1/8 ... 1; each
    segment is a round pipe (``geometry.pipe``), which orients a cylinder along an
    arbitrary direction without a hand-rolled rotation basis.
    """
    start, end = _vec3(spec["from"], "from"), _vec3(spec["to"], "to")
    sag, radius = float(spec["sag"]), float(spec["radius"])
    if sag < 0.0:
        raise ValueError("cable sag must not be negative")
    if radius <= 0.0:
        raise ValueError("cable radius must be positive")

    points = [
        (start[0] + (end[0] - start[0]) * t,
         start[1] + (end[1] - start[1]) * t - 4.0 * sag * t * (1.0 - t),
         start[2] + (end[2] - start[2]) * t)
        for t in (index / CABLE_SEGMENTS for index in range(CABLE_SEGMENTS + 1))
    ]

    parts: list[geo.MeshData] = []
    for index in range(CABLE_SEGMENTS):
        head, tail = points[index], points[index + 1]
        if math.dist(head, tail) <= 1e-9:
            raise ValueError("cable endpoints must differ")
        parts.append(geo.pipe(f"cable-segment-{index}", head, tail, radius, "dark_metal", segments=CABLE_PIPE_SEGMENTS))

    return Assembly(kind="cable", name=spec["id"], origin=(0.0, 0.0, 0.0), rotation=0.0, parts=parts, attachments={})


# --- scatter prototypes, wrecks and heaps -------------------------------------


def rubble_prototypes() -> list[geo.MeshData]:
    """Three GN-scatter prototypes: concrete chunk, slab and a rebar bundle.

    Each prototype's lowest vertex sits on y = 0 so the scatter can sink it into
    the ground. The rebar bundle is three round bars leaning out of one point,
    merged into a single mesh because ``geometry`` emits one mesh per primitive.
    """
    rng = random.Random(RUBBLE_SEED)
    base = rng.uniform(0.35, 0.5)
    chunk = _grounded("rubble-chunk", _jitter_box("rubble-chunk", (0.0, base / 2, 0.0), (base, base, base), 0.15, rng, "concrete_mid"))
    slab = geo.box("rubble-slab", (0.0, 0.05, 0.0), (0.8, 0.1, 0.6), "concrete_stained")
    rods = [
        geo.pipe(f"rebar-{index}", (dx * 0.2, 0.02, dz * 0.2), (dx, 0.6 + index * 0.08, dz), 0.018, "exposed_metal", segments=6)
        for index, (dx, dz) in enumerate(((0.22, 0.05), (-0.14, 0.18), (0.05, -0.2)))
    ]
    return [chunk, slab, _merge("rubble-rebar", rods, "exposed_metal")]


def build_vehicle_husk(seed: int) -> Assembly:
    """Burnt-out car shell: jittered body and cabin with four wheels, 4m long on local X."""
    rng = random.Random(seed)
    parts = [
        _jitter_box("husk-body", (0.0, 0.72, 0.0), (VEHICLE_LENGTH, 0.75, 1.7), 0.06, rng, "rust_dark"),
        _jitter_box("husk-cabin", (-0.35, 1.28, 0.0), (1.7, 0.62, 1.55), 0.05, rng, "dark_metal"),
    ]
    for index, (sx, sz) in enumerate(((-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0))):
        parts.append(geo.cylinder(f"husk-wheel-{index}", (sx * 1.35, 0.34, sz * 0.85), 0.34, 0.22, 8, "dark_metal", axis="Z"))
    return Assembly(kind="vehicle-husk", name="vehicle-husk", origin=(0.0, 0.0, 0.0), rotation=0.0, parts=parts, attachments={})


def build_junk_pile(seed: int, radius: float) -> Assembly:
    """Junk heap: 15 to 30 salvaged crates and drums piled inside ``radius`` metres."""
    if radius <= 0.0:
        raise ValueError("junk pile radius must be positive")
    rng = random.Random(seed)
    parts: list[geo.MeshData] = []
    for index in range(rng.randint(15, 30)):
        angle = rng.uniform(0.0, math.tau)
        distance = radius * math.sqrt(rng.random())  # uniform over the disc
        x, z = math.cos(angle) * distance, math.sin(angle) * distance
        ceiling = 0.2 + 0.7 * radius * (1.0 - distance / radius)
        material = rng.choice(_JUNK_PILE_MATERIALS)
        if rng.random() < 0.45:
            size = (rng.uniform(0.15, 0.38), rng.uniform(0.12, 0.32), rng.uniform(0.15, 0.38))
            y = max(rng.uniform(0.05, ceiling), size[1] / 2 + 0.01)
            parts.append(geo.box(f"junk-box-{index}", (x, y, z), size, material))
        else:
            height, axis = rng.uniform(0.15, 0.5), rng.choice(("X", "Y", "Z"))
            piece_radius = rng.uniform(0.06, 0.15)
            y = max(rng.uniform(0.05, ceiling), (height / 2 if axis == "Y" else piece_radius) + 0.01)
            parts.append(geo.cylinder(f"junk-drum-{index}", (x, y, z), piece_radius, height, 8, material, axis=axis))
    return Assembly(kind="junk-pile", name="junk-pile", origin=(0.0, 0.0, 0.0), rotation=0.0, parts=parts, attachments={})