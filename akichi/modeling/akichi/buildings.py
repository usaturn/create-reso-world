"""Deterministic brutalist ruin towers and the perimeter wall for the akichi slum.

Each tower is assembled from flat primitive parts: a concrete main volume with a
setback crown, a window grid, formwork seams, an optional collapsed corner with
exposed rebar, rooftop clutter, rust streaks and one entrance. Nothing here
touches Blender or Resonite; :class:`Assembly` is pure Python data consumed by
the sector builders (Task 5/6) and the build CLI (Task 6).

Geometry uses Resonite coordinates (Y up, metres) in tower-local space around
the assembly origin; ``rotation`` is applied by :attr:`Assembly.bounds` and the
export step, exactly like the tokyo_nova assemblies.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from modeling.akichi import geometry as geo

Vec3 = tuple[float, float, float]

# Window grid and pane sizes (brief recipe 2).
WINDOW_PITCH_X = 2.8
WINDOW_PITCH_Y = 3.2
WINDOW_SIZE = (1.2, 1.6)
STORY_HEIGHT = 3.2  # shared by window rows, seams and broken-floor levels

# Damage probabilities per window: no glass 30%, distorted frame 10%, intact 60%.
_BROKEN_WINDOW_RATE = 0.30
_DISTORTED_WINDOW_RATE = 0.10

# Face descriptors: (label, normal axis 0=x 2=z, sign toward +axis).
_FACES: tuple[tuple[str, int, float], ...] = (
    ("north", 2, 1.0),
    ("east", 0, 1.0),
    ("south", 2, -1.0),
    ("west", 0, -1.0),
)


def _rotate(point: Vec3, radians: float) -> Vec3:
    c, s = math.cos(radians), math.sin(radians)
    return (point[0] * c + point[2] * s, point[1], -point[0] * s + point[2] * c)


@dataclass
class Assembly:
    """Named logical asset. Part geometry stays editable and is batched by material at export.

    ``rotation`` is radians around world-up (Y), matching tokyo_nova's Assembly;
    ``attachments`` holds assembly-local points that consumers transform with
    ``origin`` and ``rotation``.
    """

    kind: str
    name: str
    origin: Vec3
    rotation: float
    parts: list[geo.MeshData] = field(default_factory=list)
    attachments: dict[str, Vec3] = field(default_factory=dict)

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


# --- small geometry helpers ---------------------------------------------------


def _rotated_box(name: str, center: Vec3, size: Vec3, yaw_degrees: float, material: str) -> geo.MeshData:
    """Axis-aligned box corners rotated around Y, emitted as one mesh."""
    cx, cy, cz = center
    sx, sy, sz = size
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    radians = math.radians(yaw_degrees)
    c, s = math.cos(radians), math.sin(radians)
    vertices = []
    for dx, dy, dz in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                       (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)):
        x, z = dx * hx, dz * hz
        vertices.append((cx + x * c - z * s, cy + dy * hy, cz + x * s + z * c))
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    return geo.mesh(name, vertices, faces, material)


def _window_columns(span: float) -> list[float]:
    """Deterministic horizontal window centres across a face span."""
    count = max(1, int(span // WINDOW_PITCH_X))
    edge = (span - (count - 1) * WINDOW_PITCH_X) / 2.0
    return [-span / 2 + edge + i * WINDOW_PITCH_X for i in range(count)]


def _window_rows(y_bottom: float, y_top: float) -> list[float]:
    """Deterministic vertical window centres inside one volume's face."""
    rows: list[float] = []
    y = y_bottom + WINDOW_SIZE[1] / 2 + 0.8
    while y + WINDOW_SIZE[1] / 2 <= y_top - 0.5:
        rows.append(y)
        y += WINDOW_PITCH_Y
    return rows


def _seam_levels(y_bottom: float, y_top: float) -> list[float]:
    """Story pitch multiples inside a volume, used for formwork seams."""
    levels: list[float] = []
    y = math.ceil((y_bottom + 0.35) / STORY_HEIGHT) * STORY_HEIGHT
    while y <= y_top - 0.35:
        levels.append(y)
        y += STORY_HEIGHT
    return levels


# --- recipe pieces ------------------------------------------------------------


def _windows(parts: list[geo.MeshData], rng: random.Random, volumes, door_face_index: int) -> None:
    """Window grid on every face: recessed dark pane with a proud frame rim.

    The tower body is a solid box, so a true cavity would be invisible; the
    recess is expressed as a stepped panel instead. The frame box is 0.15m deep
    and centred 0.05m off the wall plane, so its front face stands 0.125m proud;
    the 0.05m glass slab sits on the wall plane itself, 0.1m behind that front
    face. Broken windows keep only the frame, which is what makes the missing
    glass readable.
    """
    count = 0
    for volume_index, (hx, hz, y_bottom, y_top) in enumerate(volumes):
        for face_index, (_face, axis, sign) in enumerate(_FACES):
            span = 2 * hx if axis == 2 else 2 * hz
            plane = sign * (hz if axis == 2 else hx)
            skip_door = volume_index == 0 and face_index == door_face_index
            for u in _window_columns(span):
                if skip_door and abs(u) <= 1.85:
                    continue
                for y in _window_rows(y_bottom, y_top):
                    roll = rng.random()
                    center = (u, y, plane + sign * 0.05) if axis == 2 else (plane + sign * 0.05, y, u)
                    frame_size = (WINDOW_SIZE[0], WINDOW_SIZE[1], 0.15) if axis == 2 else (0.15, WINDOW_SIZE[1], WINDOW_SIZE[0])
                    glass_size = (1.16, 1.56, 0.05) if axis == 2 else (0.05, 1.56, 1.16)
                    if roll < _BROKEN_WINDOW_RATE:
                        parts.append(geo.box(f"window-frame-{count}", center, frame_size, "dark_metal"))
                    elif roll < _BROKEN_WINDOW_RATE + _DISTORTED_WINDOW_RATE:
                        parts.append(_rotated_box(f"window-distorted-{count}", center, frame_size, rng.uniform(-3.0, 3.0), "dark_metal"))
                    else:
                        parts.append(geo.box(f"window-frame-{count}", center, frame_size, "dark_metal"))
                        glass_center = (u, y, plane) if axis == 2 else (plane, y, u)
                        parts.append(geo.box(f"window-glass-{count}", glass_center, glass_size, "glass_dark"))
                    count += 1


def _seams(parts: list[geo.MeshData], volumes) -> None:
    """Formwork seam bands (proud 0.03m) at every story level on every face."""
    index = 0
    for hx, hz, y_bottom, y_top in volumes:
        for label, axis, sign in _FACES:
            span = 2 * hx if axis == 2 else 2 * hz
            plane = sign * (hz if axis == 2 else hx)
            for y in _seam_levels(y_bottom, y_top):
                if axis == 2:
                    parts.append(geo.box(f"seam-{label}-{index}", (0.0, y, plane + sign * 0.03), (span - 0.6, 0.25, 0.06), "concrete_stained"))
                else:
                    parts.append(geo.box(f"seam-{label}-{index}", (plane + sign * 0.03, y, 0.0), (0.06, 0.25, span - 0.6), "concrete_stained"))
                index += 1


def _corner_damage(parts: list[geo.MeshData], rng: random.Random, hx: float, hz: float, height: float, setback: float, corner_size: float) -> None:
    """Collapsed corner: surviving L-shaped slabs, one remnant column, rebar.

    No booleans: the main box keeps its walls, the corner quadrant loses its
    structural parts (slabs and column are simply absent there) and the broken
    slab edges sprout exposed rebar pointing into the void.
    """
    floors = [STORY_HEIGHT * i for i in range(1, int(setback // STORY_HEIGHT) + 1)]
    if not floors:
        return
    sx, sz = rng.choice((-1.0, 1.0)), rng.choice((-1.0, 1.0))
    index = 0
    for y in floors:
        parts.append(geo.box(f"slab-{index}", (sx * (hx - corner_size / 2), y, sz * (hz - corner_size + 0.225)), (corner_size, 0.35, 0.45), "patched_concrete"))
        index += 1
        parts.append(geo.box(f"slab-{index}", (sx * (hx - corner_size + 0.225), y, sz * (hz - corner_size / 2)), (0.45, 0.35, corner_size), "patched_concrete"))
        index += 1
    parts.append(geo.box(f"slab-{index}", (sx * (hx - corner_size + 0.25), setback / 2, sz * (hz - corner_size + 0.25)), (0.5, setback, 0.5), "concrete_mid"))

    max_length = min(2.5, corner_size - 0.05)
    for k in range(rng.randint(4, 8)):
        source = rng.choice(("x-edge", "z-edge", "column"))
        level = rng.choice(floors)
        length = rng.uniform(1.0, max_length)
        theta = math.radians(rng.uniform(-28.0, 28.0))
        down = rng.uniform(0.1, 0.4)
        if source == "x-edge":
            anchor = (sx * (hx - corner_size + rng.uniform(0.15, corner_size / 2)), level + 0.19, sz * (hz - corner_size + 0.45))
            direction = (sx * math.sin(theta), -down, sz * math.cos(theta))
        elif source == "z-edge":
            anchor = (sx * (hx - corner_size + 0.45), level + 0.19, sz * (hz - corner_size + rng.uniform(0.15, corner_size / 2)))
            direction = (sx * math.cos(theta), -down, sz * math.sin(theta))
        else:
            anchor = (sx * (hx - corner_size + 0.25), setback + 0.19, sz * (hz - corner_size + 0.25))
            direction = (sx * math.sin(theta), -down, sz * math.cos(theta))
        end = (anchor[0] + direction[0] * length, anchor[1] + direction[1] * length, anchor[2] + direction[2] * length)
        # Keep every tip inside the tower envelope with a small outward allowance
        # so the assembly bounds stay within footprint + 1m.
        end = (
            max(-hx - 0.45, min(hx + 0.45, end[0])),
            max(0.05, min(height, end[1])),
            max(-hz - 0.45, min(hz + 0.45, end[2])),
        )
        parts.append(geo.pipe(f"rebar-{k}", anchor, end, 0.03, "exposed_metal", segments=6))


def _rooftop(parts: list[geo.MeshData], rng: random.Random, width: float, depth: float, height: float, upper_hx: float, upper_hz: float) -> None:
    """Parapet ring, machinery box (30% footprint) and an optional water tower."""
    index = 0
    for sign in (-1.0, 1.0):
        parts.append(geo.box(f"parapet-{index}", (0.0, height + 0.45, sign * (upper_hz - 0.15)), (2 * upper_hx, 0.9, 0.3), "concrete_dark"))
        index += 1
        parts.append(geo.box(f"parapet-{index}", (sign * (upper_hx - 0.15), height + 0.45, 0.0), (0.3, 0.9, 2 * upper_hz), "concrete_dark"))
        index += 1

    mw = max(1.0, min(0.55 * width, 2 * upper_hx - 0.8))
    md = max(1.0, min(0.55 * depth, 2 * upper_hz - 0.8))
    span_x = upper_hx - 0.2 - mw / 2
    span_z = upper_hz - 0.2 - md / 2
    mx = rng.uniform(-span_x, span_x) if span_x > 0 else 0.0
    mz = rng.uniform(-span_z, span_z) if span_z > 0 else 0.0
    parts.append(geo.box("machine-room", (mx, height + 1.0, mz), (mw, 2.0, md), "concrete_mid"))

    if min(2 * upper_hx, 2 * upper_hz) < 2.6 or rng.random() >= 0.6:
        return
    spots = [(sx * (upper_hx - 1.25), sz * (upper_hz - 1.25)) for sx in (-1.0, 1.0) for sz in (-1.0, 1.0)]
    rng.shuffle(spots)
    spot = None
    for tx, tz in spots:
        if abs(tx - mx) >= mw / 2 + 1.25 or abs(tz - mz) >= md / 2 + 1.25:
            spot = (tx, tz)
            break
    if spot is None:
        return
    tx, tz = spot
    for k, (lx, lz) in enumerate(((-0.85, -0.85), (0.85, -0.85), (-0.85, 0.85), (0.85, 0.85))):
        parts.append(geo.pipe(f"tank-leg-{k}", (tx + lx, height + 0.05, tz + lz), (tx + lx, height + 1.4, tz + lz), 0.05, "exposed_metal", segments=6))
    parts.append(geo.cylinder("water-tank", (tx, height + 2.45, tz), 1.2, 2.0, 8, "rust", axis="Y"))


def _rust_streaks(parts: list[geo.MeshData], rng: random.Random, volumes, door_face_index: int) -> None:
    """Dark drip marks below window sills and seams, 8-20 across the facades.

    Low-rise volumes that offer fewer than 8 anchors (windows + seams) produce
    no streaks at all instead of failing.
    """
    candidates: list[tuple[int, float, float, float, float, float]] = []
    for volume_index, (hx, hz, y_bottom, y_top) in enumerate(volumes):
        for face_index, (_face, axis, sign) in enumerate(_FACES):
            span = 2 * hx if axis == 2 else 2 * hz
            plane = sign * (hz if axis == 2 else hx)
            skip_door = volume_index == 0 and face_index == door_face_index
            for u in _window_columns(span):
                for y in _window_rows(y_bottom, y_top):
                    source_y = y - 0.86
                    if skip_door and abs(u) < 1.8 and source_y < 3.1:
                        continue
                    candidates.append((axis, sign, plane, span, u, source_y))
            for y in _seam_levels(y_bottom, y_top):
                for u in (-span / 4, 0.0, span / 4):
                    source_y = y - 0.155
                    if skip_door and abs(u) < 1.8 and source_y < 3.1:
                        continue
                    candidates.append((axis, sign, plane, span, u, source_y))
    if len(candidates) < 8:
        # A low-rise volume can offer fewer than 8 window/seam anchors. There is
        # nothing to drip from then, and rng.randint(8, <8) would raise.
        return
    count = rng.randint(8, min(20, len(candidates)))
    for k, (axis, sign, plane, span, u, source_y) in enumerate(rng.sample(candidates, count)):
        width = rng.uniform(0.1, 0.3)
        length = rng.uniform(0.5, 2.0)
        usable = min(length, source_y - 0.06)
        if usable < 0.25:
            continue
        u_final = max(-span / 2 + width / 2 + 0.1, min(span / 2 - width / 2 - 0.1, u + rng.uniform(-0.4, 0.4)))
        center_y = source_y - 0.03 - usable / 2
        if axis == 2:
            parts.append(geo.box(f"streak-{k}", (u_final, center_y, plane + sign * 0.02), (width, usable, 0.04), "rust_dark"))
        else:
            parts.append(geo.box(f"streak-{k}", (plane + sign * 0.02, center_y, u_final), (0.04, usable, width), "rust_dark"))


def _entrance(parts: list[geo.MeshData], rng: random.Random, hx: float, hz: float, door_face_index: int) -> None:
    """Dark shuttered entrance on one face, with an optional warm lamp above.

    The recess is expressed as a proud ``sign_backing`` panel for the same
    reason as the windows: the body is a solid box with no real cavity.
    """
    _, axis, sign = _FACES[door_face_index]
    plane = sign * (hz if axis == 2 else hx)
    if axis == 2:
        parts.append(geo.box("door", (0.0, 1.5, plane + sign * 0.04), (2.5, 3.0, 0.06), "sign_backing"))
        light_center = (0.0, 3.08, plane + sign * 0.05)
        light_size = (0.3, 0.1, 0.05)
    else:
        parts.append(geo.box("door", (plane + sign * 0.04, 1.5, 0.0), (0.06, 3.0, 2.5), "sign_backing"))
        light_center = (plane + sign * 0.05, 3.08, 0.0)
        light_size = (0.05, 0.1, 0.3)
    if rng.random() < 0.4:
        parts.append(geo.box("door-light", light_center, light_size, "warm_light"))


# --- public API ---------------------------------------------------------------


def build_tower(spec: dict, seed: int) -> Assembly:
    """Assemble one brutalist ruin tower from a layout tower spec.

    ``origin`` is set to ``(center_x, 0, center_z)`` with Y=0 at the ground;
    parts live in tower-local coordinates and ``rotation`` (cardinal) is applied
    by the assembly transform. Only ``random.Random(seed)`` drives variation.
    """
    rng = random.Random(seed)
    width, depth = float(spec["footprint"][0]), float(spec["footprint"][1])
    height = float(spec["height"])
    hx, hz = width / 2, depth / 2
    setback = min(float(spec["setback_height"]), height - 0.5)
    inset = min(float(spec["setback_inset"]), min(width, depth) / 2 - 0.3)
    upper_hx, upper_hz = hx - inset, hz - inset

    parts: list[geo.MeshData] = []
    body_material = rng.choice(("concrete_dark", "concrete_mid"))
    crown_material = rng.choice(("concrete_dark", "concrete_mid"))
    parts.append(geo.box("body", (0.0, height / 2, 0.0), (width, height, depth), body_material))
    if height - setback > 0.1:
        parts.append(geo.box("setback", (0.0, (setback + height) / 2, 0.0), (2 * upper_hx, height - setback, 2 * upper_hz), crown_material))
    door_face_index = rng.choice(range(len(_FACES)))
    volumes = [(hx, hz, 0.0, setback)]
    if height - setback > 0.1:
        volumes.append((upper_hx, upper_hz, setback, height))

    _windows(parts, rng, volumes, door_face_index)
    _seams(parts, volumes)
    if bool(spec["broken_corner"]):
        _corner_damage(parts, rng, hx, hz, height, setback, min(float(spec["corner_size"]), min(width, depth) - 0.6))
    _rooftop(parts, rng, width, depth, height, upper_hx, upper_hz)
    _rust_streaks(parts, rng, volumes, door_face_index)
    _entrance(parts, rng, hx, hz, door_face_index)

    origin = (float(spec["center"][0]), 0.0, float(spec["center"][1]))
    return Assembly(
        kind="tower",
        name=spec["id"],
        origin=origin,
        rotation=math.radians(float(spec["rotation"])),
        parts=parts,
        attachments={},
    )


def build_perimeter_wall(seed: int) -> Assembly:
    """Low ruined wall around the 100x100 site: 10m segments, some collapsed gaps."""
    rng = random.Random(seed)
    parts: list[geo.MeshData] = []
    half = 50.0

    def edge_segments(name: str, horizontal: bool, plane: float) -> None:
        placed = 0
        for i in range(10):
            if rng.random() < 0.16:  # collapsed gap: the segment is missing
                continue
            height = rng.uniform(1.5, 2.5)
            material = rng.choice(("concrete_dark", "concrete_mid", "patched_concrete"))
            base = -half + i * 10.0 + 5.0
            if horizontal:
                parts.append(geo.box(f"wall-{name}-{placed:02d}", (base, height / 2, plane), (10.0, height, 0.4), material))
            else:
                parts.append(geo.box(f"wall-{name}-{placed:02d}", (plane, height / 2, base), (0.4, height, 10.0), material))
            placed += 1

    edge_segments("north", True, 49.8)
    edge_segments("south", True, -49.8)
    edge_segments("east", False, 49.8)
    edge_segments("west", False, -49.8)
    return Assembly(kind="perimeter", name="perimeter-wall", origin=(0.0, 0.0, 0.0), rotation=0.0, parts=parts, attachments={})
