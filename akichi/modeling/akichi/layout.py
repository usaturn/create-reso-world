"""Deterministic district layout and validation for the akichi cyberpunk slum.

A single ``random.Random(SEED)`` drives every placement, consumed in a fixed
category order (towers -> stalls -> shacks -> nightlife -> ads -> cables ->
signs), so :func:`build_layout` always returns the same data for the same seed.
The output is plain JSON-safe data (lists/dicts/numbers) consumed by the sector
builders: Task 4 reads ``towers``, Task 5 reads the prop specs, Task 9 reads
``signs``.

Coordinate system: Resonite XYZ (Y up, metres). Ground positions are spelled
``[x, z]`` with the site spanning x: -50..50, z: -50..50; elevations use ``y``.
Ads of kind ``wall``/``rooftop``/``lantern`` carry an ``attach`` field naming
the tower (or stall) they are mounted on, and wall ads also carry the ``face``
they sit on so validation item 5 can verify the 0.5m catch. Rooftop ads also
carry ``roof_height``, the world y of the attached tower's roof plane, so the
prop builder can reach it with the panel's legs.
"""
from __future__ import annotations

import math
import random
from typing import Any

from modeling.akichi.materials import NEON_COLORS

SEED = 250925
SITE: dict[str, float] = {"width": 100.0, "depth": 100.0}

# Comparison slop shared by generation and validation so rounded specs that sit
# exactly on a required margin do not flap.
_EPS = 1e-6

VACANT_RECT: tuple[float, float, float, float] = (-14.0, -19.0, 14.0, 19.0)

STREETS: list[dict[str, Any]] = [
    {"id": "ring-north", "min": [-50, 19], "max": [50, 27]},
    {"id": "ring-south", "min": [-50, -27], "max": [50, -19]},
    {"id": "ring-east", "min": [14, -27], "max": [22, 27]},
    {"id": "ring-west", "min": [-22, -27], "max": [-14, 27]},
    {"id": "perimeter-north", "min": [-50, 42], "max": [50, 50]},
    {"id": "perimeter-south", "min": [-50, -50], "max": [50, -42]},
    {"id": "perimeter-east", "min": [42, -50], "max": [50, 50]},
    {"id": "perimeter-west", "min": [-50, -50], "max": [-42, 50]},
]

# --- shared shape conventions -------------------------------------------------

# Nominal stall footprint (w, d); stalls carry no footprint field in the schema.
STALL_SIZE: tuple[float, float] = (2.4, 1.8)
# Club depth in z (a facade 5m deep); the schema only stores `width`.
CLUB_DEPTH = 5.0

# Fixed cardinal yaw degrees (Y-up) used by towers, stalls, ads and signs.
CARDINALS = (0, 90, 180, 270)
_FACE_ROTATION = {"north": 180, "south": 0, "east": 90, "west": 270}
_FRAMES = ("dark_metal", "sign_backing")

# --- tower bands and anchors --------------------------------------------------

# Each band: (band axis, band low, band high, anchor slots). Footprint is drawn
# first, then the anchor is clamped into the band shrunk by the half-footprint,
# guaranteeing full containment inside the band. The anchors are spaced so that
# even maximum 15x15 footprints keep >= 2m of separation from every other band.
TOWER_BANDS: list[tuple[str, str, float, float, list[tuple[float, float]]]] = [
    ("north", "z", 27.0, 42.0, [(-32.0, 34.5), (-6.0, 34.5), (24.0, 34.5)]),
    ("south", "z", -42.0, -27.0, [(-32.0, -34.5), (-6.0, -34.5), (24.0, -34.5)]),
    ("east", "x", 22.0, 42.0, [(32.0, 11.5), (32.0, -11.5)]),
    ("west", "x", -42.0, -22.0, [(-32.0, 11.5), (-32.0, -11.5)]),
]

# --- stall rows ---------------------------------------------------------------

STALL_X_EAST = 17.5  # inside ring-east street x: 14..22, clear of the vacant lot
STALL_X_WEST = -17.5  # inside ring-west street x: -22..-14
STALL_Z_SLOTS = [round(-7.25 + 2.9 * i, 2) for i in range(6)]
# Guarantees junk stalls for the four junk-shop signs at stall-01/04/07/10.
STALL_KINDS = {
    "east": ("junk", "parts", "food", "junk", "parts", "junk"),
    "west": ("junk", "food", "parts", "junk", "parts", "junk"),
}

# --- shacks -------------------------------------------------------------------

SHACK_BLOCK = (-42.0, -24.0, -42.0, -28.0)  # south-west block x,z
SHACK_WIDTH_RANGE = (2.5, 4.0)
SHACK_DEPTH_RANGE = (2.5, 5.0)
SHACK_HEIGHT_RANGE = (2.4, 3.2)
SHACK_ROTATION_RANGE = (-15.0, 15.0)
SHACK_MIN_GAP = 1.5
SHACK_ATTEMPTS = 64
SHACK_WALL_POOL = ("corrugated", "corrugated_rusted", "plywood", "painted_metal_faded")
# Deterministic shelter for the case where a shack's random attempts all
# collide: a 4x3 lattice of 2.5x2.5 cells with >= 2.0m gaps, plus progressively
# finer scans of the block interior that also keep the clearance.
_SHACK_FALLBACK_CELLS = [
    (x, z) for z in (-40.5, -36.0, -31.5) for x in (-40.5, -36.0, -31.5, -27.0)
]


def _linspace(start: float, stop: float, step: float) -> list[float]:
    """Deterministic arithmetic range for fallback scans (no rng involved)."""
    values: list[float] = []
    value = start
    while value <= stop + 1e-9:
        values.append(round(value, 4))
        value += step
    return values


def _shelter_cells_available(
    placed: list[tuple[list[float], tuple[float, float], float]],
) -> int:
    """Count 2.5x2.5 shelter cells still clear of every placed shack.

    The fallback lattice cells are 4.5m apart on both axes, so their 2.5x2.5
    footprints never conflict with each other (2.0m gap > 1.5m). Each tentatively
    placed shack can therefore only ever reduce this count by occupying a cell.
    """
    count = 0
    for fx, fz in _SHACK_FALLBACK_CELLS:
        center = [fx, fz]
        if all(
            _rect_pair_distance(center, (2.5, 2.5), 0.0, c, fp, rot)
            >= SHACK_MIN_GAP - _EPS
            for c, fp, rot in placed
        ):
            count += 1
    return count


def _shelter_placement(
    placed: list[tuple[list[float], tuple[float, float], float]],
) -> tuple[dict[str, Any], tuple[list[float], tuple[float, float], float]]:
    """Return a clearance-respecting 2.5x2.5 placement, deterministically.

    Only reached when the random attempts for a shack all collided. The scans
    never consult the rng, so the layout stays reproducible. Cell placement uses
    the exact rotated-rectangle distance, the same measure generation and
    validation agree on.
    """
    xmin, xmax, zmin, zmax = SHACK_BLOCK

    def fits(
        cx: float, cz: float
    ) -> tuple[dict[str, Any], tuple[list[float], tuple[float, float], float]] | None:
        center = [round(cx, 2), round(cz, 2)]
        if all(
            _rect_pair_distance(center, (2.5, 2.5), 0.0, c, fp, rot)
            >= SHACK_MIN_GAP - _EPS
            for c, fp, rot in placed
        ):
            return (
                {"center": center, "footprint": [2.5, 2.5], "rotation": 0.0},
                (center, (2.5, 2.5), 0.0),
            )
        return None

    for fx, fz in _SHACK_FALLBACK_CELLS:
        pair = fits(fx, fz)
        if pair is not None:
            return pair
    # The packing guard in _build_shacks keeps at least one cell clear at every
    # step, so the lattice above always succeeds; this coarse pass over the
    # interior is belt and braces only.
    for cx in _linspace(xmin + 1.25, xmax - 1.25, 0.5):
        for cz in _linspace(zmin + 1.25, zmax - 1.25, 0.5):
            pair = fits(cx, cz)
            if pair is not None:
                return pair
    raise RuntimeError("unreachable: no clearance-respecting shack cell in the block")

# --- nightlife ----------------------------------------------------------------

CLUB_SLOTS: list[tuple[float, float]] = [
    (-19.0, 28.5),  # between north towers 01 and 02
    (9.0, 28.5),  # between north towers 02 and 03
    (36.5, 28.5),  # east of tower 03, inside the north band
    (17.4, 22.0),  # north end of ring-east street
]
CLUB_WIDTH_RANGE = (4.0, 6.0)
CLUB_NEON = ("neon_pink", "neon_purple", "neon_magenta")

NIGHTLIFE_TEXTS = [
    "ピンクサロン 夢の国",
    "ガールズバー NEON",
    "マッサージ 桃源郷",
    "スナック 星屑",
]
JUNK_TEXTS = ["ジャンク屋 鉄屑堂", "電脳パーツ 秋葉屋", "リペア受付", "中古義体 激安"]
AD_TEXTS = [
    "ヌードル24時",
    "サイバー義体 SALE",
    "ネオ東京へようこそ",
    "合成酒 ホロドリンク",
    "24H カプセルホテル",
    "データ復旧 即納",
]

# --- ads ----------------------------------------------------------------------

# 8 wall ads: (tower id, face toward the street / site centre).
WALL_AD_ATTACH: list[tuple[str, str]] = [
    ("tower-01", "south"),
    ("tower-02", "south"),
    ("tower-03", "south"),
    ("tower-05", "north"),
    ("tower-06", "north"),
    ("tower-08", "east"),
    ("tower-04", "north"),
    ("tower-07", "west"),
]
WALL_AD_WIDTH_RANGE = (3.0, 6.0)
WALL_AD_HEIGHT_RANGE = (2.0, 3.0)
WALL_AD_Y_RANGE = (4.0, 15.0)
_FACE_STANDOFF = 0.05

# 10 free-standing holo panels along the streets around the vacant lot
# (>= 2m from the vacant rect), facing the lot; the slot rotation is cardinal.
HOLO_SLOTS: list[tuple[float, float, int]] = [
    (-22.0, 24.5, 180), (-6.0, 24.5, 180), (10.0, 24.5, 180),  # ring-north
    (-22.0, -24.5, 0), (-6.0, -24.5, 0), (10.0, -24.5, 0),  # ring-south
    (19.0, 12.0, 270), (19.0, -12.0, 270),  # ring-east
    (-19.0, 12.0, 90), (-19.0, -12.0, 90),  # ring-west
]
HOLO_WIDTH_RANGE = (1.2, 2.0)
HOLO_HEIGHT_RANGE = (2.0, 3.0)
HOLO_POST_Y_RANGE = (1.2, 2.0)

ROOFTOP_AD_ATTACH: tuple[str, ...] = ("tower-01", "tower-04", "tower-07", "tower-09")
ROOFTOP_WIDTH_RANGE = (4.0, 8.0)
ROOFTOP_BOTTOM_OFFSET_RANGE = (1.0, 3.0)

LANTERN_ATTACH: tuple[str, ...] = ("stall-01", "stall-04", "stall-07", "stall-10")
LANTERN_Y = 2.2
LANTERN_SIZE: tuple[float, float] = (0.6, 0.9)

# --- cables -------------------------------------------------------------------

# Pairs connect towers and stalls. Index 0:4 endpoint near the shacks block,
# 4:8 near the nightlife strip, 8:12 across the ad sectors (Task 6 slices by
# index), so endpoints were chosen geographically to match those sections.
CABLE_PAIRS: list[tuple[str, str]] = [
    ("tower-10", "tower-05"),  # over the south-west shacks block
    ("tower-10", "tower-04"),
    ("tower-09", "stall-08"),
    ("tower-10", "stall-07"),
    ("tower-01", "tower-02"),  # along the north tower row, above the clubs
    ("tower-02", "tower-03"),
    ("tower-03", "tower-07"),  # north-east diagonal past the east junction
    ("tower-02", "tower-07"),
    ("tower-07", "stall-03"),  # ring-east stall row
    ("tower-08", "stall-06"),
    ("tower-04", "tower-05"),  # south tower row
    ("tower-06", "tower-08"),  # south-east corner
]
CABLE_SAG_RANGE = (0.5, 2.0)
CABLE_RADIUS_RANGE = (0.03, 0.06)
CABLE_TOWER_Y_RANGE = (5.0, 15.0)
CABLE_STALL_Y_RANGE = (2.8, 3.6)

# --- signs --------------------------------------------------------------------

SIGN_COLORS: tuple[tuple[float, float, float, float], ...] = (
    (1.0, 1.0, 1.0, 1.0),
    (1.0, 0.4, 0.8, 1.0),
    (0.15, 0.9, 1.0, 1.0),
    (1.0, 0.8, 0.15, 1.0),
)
SIGN_SIZE_RANGE = (0.25, 0.5)
JUNK_SIGN_STALLS = ("stall-01", "stall-04", "stall-07", "stall-10")
AD_SIGN_ADS = ("ad-09", "ad-10", "ad-11", "ad-12", "ad-13", "ad-14")  # the holo panels


# --- geometric helpers --------------------------------------------------------


def _rect(
    center: list[float],
    footprint: tuple[float, float],
    rotation: float,
) -> tuple[float, float, float, float]:
    """Axis-aligned bounding box (minx, minz, maxx, maxz) of a rotated footprint.

    Exact for cardinal angles; conservative for the arbitrary shack angles. The
    AABB drives containment checks and cardinal pairwise gaps, while rotated
    shack pairs use the exact :func:`_rect_pair_distance`.
    """
    r = math.radians(rotation)
    cosv, sinv = abs(math.cos(r)), abs(math.sin(r))
    w, d = footprint
    hx = w / 2 * cosv + d / 2 * sinv
    hz = w / 2 * sinv + d / 2 * cosv
    cx, cz = center
    return (cx - hx, cz - hz, cx + hx, cz + hz)


def _rect_gap(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Minimum euclidean distance between two AABBs in the XZ plane."""
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iz = min(a[3], b[3]) - max(a[1], b[1])
    if ix > 0 and iz > 0:
        return 0.0  # intersecting
    if ix > 0:
        return max(0.0, -iz)
    if iz > 0:
        return max(0.0, -ix)
    return math.hypot(-ix, -iz)


def _rects_overlap(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def _point_rect_distance(
    px: float, pz: float, rect: tuple[float, ...]
) -> float:
    dx = max(rect[0] - px, 0.0, px - rect[2])
    dz = max(rect[1] - pz, 0.0, pz - rect[3])
    return math.hypot(dx, dz)


def _rect_corners(
    center: list[float], footprint: tuple[float, float], rotation: float
) -> list[tuple[float, float]]:
    """Four corners of a rotated footprint rectangle in the XZ plane."""
    cx, cz = center
    w, d = footprint
    cosv, sinv = math.cos(math.radians(rotation)), math.sin(math.radians(rotation))
    hx, hz = w / 2, d / 2
    return [
        (cx + cosv * sx - sinv * sz, cz + sinv * sx + cosv * sz)
        for sx, sz in ((-hx, -hz), (hx, -hz), (hx, hz), (-hx, hz))
    ]


def _point_segment_distance(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    ex, ez = b[0] - a[0], b[1] - a[1]
    length_sq = ex * ex + ez * ez
    if length_sq == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = ((p[0] - a[0]) * ex + (p[1] - a[1]) * ez) / length_sq
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - (a[0] + t * ex), p[1] - (a[1] + t * ez))


def _point_quad_distance(p: tuple[float, float], quad: list[tuple[float, float]]) -> float:
    return min(
        _point_segment_distance(p, quad[i], quad[(i + 1) % 4]) for i in range(4)
    )


def _rect_pair_distance(
    a_center: list[float], a_footprint: tuple[float, float], a_rotation: float,
    b_center: list[float], b_footprint: tuple[float, float], b_rotation: float,
) -> float:
    """Exact minimum euclidean distance between two rotated rectangles (XZ).

    Used for the shack clearance (rotated by design); for cardinal angles it
    degenerates to the AABB gap. Overlapping rectangles return 0. Disjoint
    convex rectangles always have their closest points on a vertex of one of
    them, so the min over the 8 vertex-to-quad distances is exact.
    """
    a = _rect_corners(a_center, a_footprint, a_rotation)
    b = _rect_corners(b_center, b_footprint, b_rotation)
    # Separating-axis overlap test on the two rectangles' own edge normals.
    axes = [
        (math.cos(math.radians(a_rotation)), math.sin(math.radians(a_rotation))),
        (-math.sin(math.radians(a_rotation)), math.cos(math.radians(a_rotation))),
        (math.cos(math.radians(b_rotation)), math.sin(math.radians(b_rotation))),
        (-math.sin(math.radians(b_rotation)), math.cos(math.radians(b_rotation))),
    ]
    for ax, az in axes:
        a_proj = sorted(p[0] * ax + p[1] * az for p in a)
        b_proj = sorted(p[0] * ax + p[1] * az for p in b)
        if a_proj[0] > b_proj[-1] or b_proj[0] > a_proj[-1]:
            break
    else:
        return 0.0  # overlapping on every axis
    return min(
        min(_point_quad_distance(p, b) for p in a),
        min(_point_quad_distance(p, a) for p in b),
    )


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(max(value, lo), hi)


def _tower_extents(tower: dict[str, Any]) -> tuple[float, float]:
    """X and Z extents of a tower footprint honouring its rotation."""
    w, d = tower["footprint"]
    if tower["rotation"] % 180 == 0:
        return w, d
    return d, w


def _face_point(
    cx: float, cz: float, xext: float, zext: float, face: str
) -> tuple[float, float]:
    """Point on a tower's outer wall face, stood off by _FACE_STANDOFF."""
    offset = _FACE_STANDOFF
    if face == "north":
        return (cx, cz + zext / 2 + offset)
    if face == "south":
        return (cx, cz - zext / 2 - offset)
    if face == "east":
        return (cx + xext / 2 + offset, cz)
    return (cx - xext / 2 - offset, cz)  # west


# --- category builders --------------------------------------------------------


def _build_towers(rng: random.Random) -> list[dict[str, Any]]:
    towers: list[dict[str, Any]] = []
    index = 0
    for _band_name, band_axis, lo, hi, anchors in TOWER_BANDS:
        for anchor_x, anchor_z in anchors:
            w = round(rng.uniform(8.0, 15.0), 2)
            d = round(rng.uniform(8.0, 15.0), 2)
            height = round(rng.uniform(10.0, 30.0), 2)
            rotation = rng.choice(CARDINALS)
            if band_axis == "z":
                band_extent = d if rotation % 180 == 0 else w
                center = [round(anchor_x, 2), round(_clamp(anchor_z, lo + band_extent / 2, hi - band_extent / 2), 2)]
            else:
                band_extent = w if rotation % 180 == 0 else d
                center = [round(_clamp(anchor_x, lo + band_extent / 2, hi - band_extent / 2), 2), round(anchor_z, 2)]
            setback_height = round(rng.uniform(0.6, 0.8) * height, 2)
            setback_inset = round(rng.uniform(1.0, 2.5), 2)
            broken_corner = rng.random() < 0.5
            corner_size = round(rng.uniform(2.0, 4.0), 2)
            index += 1
            towers.append(
                {
                    "id": f"tower-{index:02d}",
                    "center": center,
                    "footprint": [w, d],
                    "height": height,
                    "rotation": rotation,
                    "setback_height": setback_height,
                    "setback_inset": setback_inset,
                    "broken_corner": broken_corner,
                    "corner_size": corner_size,
                }
            )
    return towers


def _build_stalls(rng: random.Random) -> list[dict[str, Any]]:
    # East faces the street one way, west the mirrored way; both may vary by 180.
    east_rotations = [rng.choice((-90, 90, 0, 180)) for _ in range(6)]
    stalls: list[dict[str, Any]] = []
    index = 0
    for side, x, kinds in (
        ("east", STALL_X_EAST, STALL_KINDS["east"]),
        ("west", STALL_X_WEST, STALL_KINDS["west"]),
    ):
        for i, z in enumerate(STALL_Z_SLOTS):
            rotation = east_rotations[i] if side == "east" else (east_rotations[i] + 180) % 360
            kind = kinds[i]
            awning = rng.choice(("tarp_blue", "tarp_orange"))
            index += 1
            stalls.append(
                {
                    "id": f"stall-{index:02d}",
                    "center": [x, z],
                    "rotation": rotation,
                    "kind": kind,
                    "awning": awning,
                }
            )
    return stalls


def _build_shacks(rng: random.Random) -> list[dict[str, Any]]:
    xmin, xmax, zmin, zmax = SHACK_BLOCK
    shacks: list[dict[str, Any]] = []
    placed: list[tuple[list[float], tuple[float, float], float]] = []
    for index in range(10):
        spec: dict[str, Any] | None = None
        placement: tuple[list[float], tuple[float, float], float] | None = None
        for _ in range(SHACK_ATTEMPTS):
            # Min-of-two uniforms bias footprints toward the smaller end so the
            # block stays packable and the ten shacks mix sizes organically.
            w = round(min(rng.uniform(*SHACK_WIDTH_RANGE), rng.uniform(*SHACK_WIDTH_RANGE)), 2)
            d = round(min(rng.uniform(*SHACK_DEPTH_RANGE), rng.uniform(*SHACK_DEPTH_RANGE)), 2)
            height = round(rng.uniform(*SHACK_HEIGHT_RANGE), 2)
            rotation = round(rng.uniform(*SHACK_ROTATION_RANGE), 2)
            candidate_x = round(rng.uniform(xmin + 1.3, xmax - 1.3), 2)
            candidate_z = round(rng.uniform(zmin + 1.3, zmax - 1.3), 2)
            # Clamp into the block first, then demand the exact 1.5m gap. The
            # AABB of the rotated footprint must stay in the block, which is
            # the safe (slightly conservative) containment check.
            trial = _rect([candidate_x, candidate_z], (w, d), rotation)
            cx = _clamp(candidate_x, xmin + (trial[2] - trial[0]) / 2, xmax - (trial[2] - trial[0]) / 2)
            cz = _clamp(candidate_z, zmin + (trial[3] - trial[1]) / 2, zmax - (trial[3] - trial[1]) / 2)
            center = [round(cx, 2), round(cz, 2)]
            # Accept when the exact 1.5m gap to every placed shack holds AND the
            # shelter lattice can still absorb every shack not yet placed. The
            # second condition is the packing guard: because lattice cells never
            # conflict with each other, it makes completion guaranteed while the
            # organic draws stay greedy-random.
            remaining = 10 - index - 1
            candidate = (center, (w, d), rotation)
            if all(
                _rect_pair_distance(center, (w, d), rotation, c, fp, rot)
                >= SHACK_MIN_GAP - _EPS
                for c, fp, rot in placed
            ) and _shelter_cells_available(placed + [candidate]) >= remaining:
                spec = {
                    "center": center,
                    "footprint": [w, d],
                    "height": height,
                    "rotation": rotation,
                }
                placement = candidate
                break
        if spec is None:
            spec, placement = _shelter_placement(placed)
            spec["height"] = round(rng.uniform(*SHACK_HEIGHT_RANGE), 2)
        wall_mix = rng.sample(SHACK_WALL_POOL, rng.randint(2, 3))
        placed.append(placement)
        shacks.append({**spec, "id": f"shack-{index + 1:02d}", "wall_mix": wall_mix})
    return shacks


def _build_nightlife(rng: random.Random) -> list[dict[str, Any]]:
    texts = rng.sample(NIGHTLIFE_TEXTS, len(NIGHTLIFE_TEXTS))
    clubs: list[dict[str, Any]] = []
    for index, (x, z) in enumerate(CLUB_SLOTS):
        width = round(rng.uniform(*CLUB_WIDTH_RANGE), 2)
        rotation = rng.choice((0, 180))
        neon = rng.choice(CLUB_NEON)
        clubs.append(
            {
                "id": f"club-{index + 1:02d}",
                "center": [x, z],
                "rotation": rotation,
                "width": width,
                "neon": neon,
                "sign_text": texts[index],
            }
        )
    return clubs


def _build_ads(
    rng: random.Random, towers: list[dict[str, Any]], stalls: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    towers_by_id = {t["id"]: t for t in towers}
    stalls_by_id = {s["id"]: s for s in stalls}
    ads: list[dict[str, Any]] = []

    def _uid() -> str:
        return f"ad-{len(ads) + 1:02d}"

    for tower_id, face in WALL_AD_ATTACH:
        tower = towers_by_id[tower_id]
        cx, cz = tower["center"]
        xext, zext = _tower_extents(tower)
        w = round(rng.uniform(*WALL_AD_WIDTH_RANGE), 2)
        h = round(rng.uniform(*WALL_AD_HEIGHT_RANGE), 2)
        face_x, face_z = _face_point(cx, cz, xext, zext, face)
        if face in ("north", "south"):
            span = xext
            px = cx + rng.uniform(-(span / 2 - w / 2 - 0.3), span / 2 - w / 2 - 0.3)
            pz = face_z
        else:
            span = zext
            pz = cz + rng.uniform(-(span / 2 - w / 2 - 0.3), span / 2 - w / 2 - 0.3)
            px = face_x
        y = rng.uniform(
            WALL_AD_Y_RANGE[0] + h / 2, min(WALL_AD_Y_RANGE[1], tower["height"]) - h / 2
        )
        frame = rng.choice(_FRAMES)
        ads.append(
            {
                "id": _uid(),
                "kind": "wall",
                "position": [round(px, 2), round(y, 2), round(pz, 2)],
                "rotation": _FACE_ROTATION[face],
                "size": [w, h],
                "frame": frame,
                "attach": tower_id,
                "face": face,
            }
        )

    for x, z, rotation in HOLO_SLOTS:
        w = round(rng.uniform(*HOLO_WIDTH_RANGE), 2)
        h = round(rng.uniform(*HOLO_HEIGHT_RANGE), 2)
        on_posts = rng.random() < 0.5
        y_bottom = round(rng.uniform(*HOLO_POST_Y_RANGE), 2) if on_posts else 0.0
        frame = rng.choice(_FRAMES)
        ads.append(
            {
                "id": _uid(),
                "kind": "holo",
                "position": [x, round(y_bottom + h / 2, 2), z],
                "rotation": rotation,
                "size": [w, h],
                "frame": frame,
            }
        )

    for tower_id in ROOFTOP_AD_ATTACH:
        tower = towers_by_id[tower_id]
        cx, cz = tower["center"]
        xext, zext = _tower_extents(tower)
        w = round(min(rng.uniform(*ROOFTOP_WIDTH_RANGE), min(xext, zext) - 0.5), 2)
        h = round(rng.uniform(*WALL_AD_HEIGHT_RANGE), 2)
        dx = rng.uniform(-(xext / 2 - w / 2 - 0.2), xext / 2 - w / 2 - 0.2)
        dz = rng.uniform(-(zext / 2 - w / 2 - 0.2), zext / 2 - w / 2 - 0.2)
        y_bottom = tower["height"] + rng.uniform(*ROOFTOP_BOTTOM_OFFSET_RANGE)
        frame = rng.choice(_FRAMES)
        ads.append(
            {
                "id": _uid(),
                "kind": "rooftop",
                "position": [round(cx + dx, 2), round(y_bottom + h / 2, 2), round(cz + dz, 2)],
                "rotation": rng.choice(CARDINALS),
                "size": [w, h],
                "frame": frame,
                "attach": tower_id,
                # world y of the attached tower's roof plane, so the prop builder
                # can size the legs down to it (derived, so it consumes no rng).
                "roof_height": tower["height"],
            }
        )

    for stall_id in LANTERN_ATTACH:
        stall = stalls_by_id[stall_id]
        frame = rng.choice(_FRAMES)
        ads.append(
            {
                "id": _uid(),
                "kind": "lantern",
                "position": [stall["center"][0], LANTERN_Y, stall["center"][1]],
                "rotation": stall["rotation"],
                "size": list(LANTERN_SIZE),
                "frame": frame,
                "attach": stall_id,
            }
        )

    # Neon colour cycles across the ad IDs in order, cycling the palette.
    for i, ad in enumerate(ads):
        ad["color"] = NEON_COLORS[i % len(NEON_COLORS)]
    return ads


def _build_cables(
    rng: random.Random, towers: list[dict[str, Any]], stalls: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    towers_by_id = {t["id"]: t for t in towers}
    stalls_by_id = {s["id"]: s for s in stalls}

    def anchor(
        item: dict[str, Any], partner_center: list[float], y: float, is_tower: bool
    ) -> list[float]:
        cx, cz = item["center"]
        if not is_tower:
            return [cx, round(y, 2), cz]
        dx = partner_center[0] - cx
        dz = partner_center[1] - cz
        if abs(dx) >= abs(dz):
            face = "east" if dx >= 0 else "west"
        else:
            face = "north" if dz >= 0 else "south"
        xext, zext = _tower_extents(item)
        fx, fz = _face_point(cx, cz, xext, zext, face)
        return [round(fx, 2), round(y, 2), round(fz, 2)]

    cables: list[dict[str, Any]] = []
    for index, (a_id, b_id) in enumerate(CABLE_PAIRS):
        a_is_tower = a_id.startswith("tower")
        b_is_tower = b_id.startswith("tower")
        a = towers_by_id[a_id] if a_is_tower else stalls_by_id[a_id]
        b = towers_by_id[b_id] if b_is_tower else stalls_by_id[b_id]
        y_a = (
            round(rng.uniform(CABLE_TOWER_Y_RANGE[0], min(CABLE_TOWER_Y_RANGE[1], a["height"] - 1.0)), 2)
            if a_is_tower
            else round(rng.uniform(*CABLE_STALL_Y_RANGE), 2)
        )
        y_b = (
            round(rng.uniform(CABLE_TOWER_Y_RANGE[0], min(CABLE_TOWER_Y_RANGE[1], b["height"] - 1.0)), 2)
            if b_is_tower
            else round(rng.uniform(*CABLE_STALL_Y_RANGE), 2)
        )
        sag = round(rng.uniform(*CABLE_SAG_RANGE), 2)
        radius = round(rng.uniform(*CABLE_RADIUS_RANGE), 2)
        cables.append(
            {
                "id": f"cable-{index + 1:02d}",
                "from": anchor(a, b["center"], y_a, a_is_tower),
                "to": anchor(b, a["center"], y_b, b_is_tower),
                "sag": sag,
                "radius": radius,
            }
        )
    return cables


def _build_signs(
    rng: random.Random,
    clubs: list[dict[str, Any]],
    stalls: list[dict[str, Any]],
    ads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ad_by_id = {ad["id"]: ad for ad in ads}
    signs: list[dict[str, Any]] = []

    def append(attach_to: str, offset: list[float], text: str) -> None:
        size = round(rng.uniform(*SIGN_SIZE_RANGE), 2)
        color = list(rng.choice(SIGN_COLORS))
        signs.append(
            {
                "id": f"sign-{len(signs) + 1:02d}",
                "attach_to": attach_to,
                "offset": offset,
                "text": text,
                "color": color,
                "size": size,
            }
        )

    # Nightlife signs echo the club's own sign_text.
    for club in clubs:
        append(club["id"], [0.0, 2.6, 2.56], club["sign_text"])

    junk_texts = rng.sample(JUNK_TEXTS, 4)
    for stall_id, text in zip(JUNK_SIGN_STALLS, junk_texts):
        append(stall_id, [0.0, 2.55, 0.93], text)

    # Ad texts hang on the holo panels, near their top edge.
    ad_texts = rng.sample(AD_TEXTS, 6)
    for ad_id, text in zip(AD_SIGN_ADS, ad_texts):
        panel_h = ad_by_id[ad_id]["size"][1]
        append(ad_id, [0.0, round(panel_h / 2 + 0.05, 2), 0.06], text)

    return signs


# --- public API ---------------------------------------------------------------


def build_layout() -> dict[str, Any]:
    """Build the full district layout deterministically from the fixed seed."""
    rng = random.Random(SEED)
    towers = _build_towers(rng)
    stalls = _build_stalls(rng)
    shacks = _build_shacks(rng)
    nightlife = _build_nightlife(rng)
    ads = _build_ads(rng, towers, stalls)
    cables = _build_cables(rng, towers, stalls)
    signs = _build_signs(rng, nightlife, stalls, ads)
    return {
        "schema_version": 1,
        "seed": SEED,
        "site": dict(SITE),
        "vacant": {"min": [VACANT_RECT[0], VACANT_RECT[1]], "max": [VACANT_RECT[2], VACANT_RECT[3]]},
        "streets": [dict(street) for street in STREETS],
        "towers": towers,
        "stalls": stalls,
        "shacks": shacks,
        "nightlife": nightlife,
        "ads": ads,
        "cables": cables,
        "signs": signs,
    }


def validate_layout(data: dict[str, Any]) -> list[str]:
    """Check the brief's 7 validation items; returns a list of problem strings.

    An empty list means the layout is valid. Item 7 (determinism) is exercised
    by the test suite through repeated builds, not by this function.
    """
    issues: list[str] = []
    half = SITE["width"] / 2

    def footprint_of(item: dict[str, Any], group: str) -> tuple[float, float]:
        if group == "towers":
            return (item["footprint"][0], item["footprint"][1])
        if group == "shacks":
            return (item["footprint"][0], item["footprint"][1])
        if group == "stalls":
            return STALL_SIZE
        return (item["width"], CLUB_DEPTH)  # nightlife

    GROUPS = ("towers", "shacks", "stalls", "nightlife")
    rects: dict[str, tuple[float, float, float, float]] = {}
    for group in GROUPS:
        for item in data[group]:
            rects[item["id"]] = _rect(item["center"], footprint_of(item, group), item["rotation"])

    # 1. Footprints stay inside the site bounds.
    for group in GROUPS:
        for item in data[group]:
            rect = rects[item["id"]]
            if rect[0] < -half or rect[2] > half or rect[1] < -half or rect[3] > half:
                issues.append(f"{item['id']}: footprint outside the site bounds")

    # 2. Pairwise clearances: towers 2.0m, shacks 1.5m, nightlife-towers 2.0m.
    for group_a, group_b, needed in (
        ("towers", "towers", 2.0),
        ("shacks", "shacks", 1.5),
        ("nightlife", "towers", 2.0),
    ):
        items_a = data[group_a]
        items_b = data[group_b]
        for i, item_a in enumerate(items_a):
            start = i + 1 if group_a == group_b else 0
            for item_b in items_b[start:]:
                # Shacks are rotated by design, so their pairs need the exact
                # rectangle distance (the measure generation placed them with);
                # cardinal footprints pass through the AABB gap which is exact
                # for them.
                if group_a == "shacks":
                    gap = _rect_pair_distance(
                        item_a["center"], tuple(item_a["footprint"]), item_a["rotation"],
                        item_b["center"], tuple(item_b["footprint"]), item_b["rotation"],
                    )
                else:
                    gap = _rect_gap(rects[item_a["id"]], rects[item_b["id"]])
                if gap < needed - _EPS:
                    issues.append(
                        f"{item_a['id']}/{item_b['id']}: footprint clearance below {needed}m"
                    )

    # 3. Nothing stands on the vacant lot; holo ads keep 2m away from its rim.
    for group in GROUPS:
        for item in data[group]:
            if _rects_overlap(rects[item["id"]], VACANT_RECT):
                issues.append(f"{item['id']}: footprint intrudes the vacant lot")
    for ad in data["ads"]:
        if ad["kind"] == "holo":
            distance = _point_rect_distance(ad["position"][0], ad["position"][2], VACANT_RECT)
            if distance <= 2.0 + _EPS:
                issues.append(f"{ad['id']}: holo panel within 2m of the vacant lot")

    # 4. Stalls sit fully inside the ring streets.
    ring_streets = [
        (s["min"][0], s["min"][1], s["max"][0], s["max"][1])
        for s in data["streets"]
        if s["id"].startswith("ring")
    ]
    for stall in data["stalls"]:
        x0, z0, x1, z1 = rects[stall["id"]]
        corners = ((x0, z0), (x1, z0), (x0, z1), (x1, z1))
        if not all(
            any(sx0 <= px <= sx1 and sz0 <= pz <= sz1 for sx0, sz0, sx1, sz1 in ring_streets)
            for px, pz in corners
        ):
            issues.append(f"{stall['id']}: stall outside the ring streets")

    # 5. Wall and rooftop ads hug their attached tower (0.5m in the XZ plane).
    towers_by_id = {t["id"]: t for t in data["towers"]}
    for ad in data["ads"]:
        if ad["kind"] not in ("wall", "rooftop"):
            continue
        tower = towers_by_id.get(ad.get("attach", ""))
        if tower is None:
            issues.append(f"{ad['id']}: ad lacks a valid attached tower")
            continue
        tower_rect = rects[tower["id"]]
        gap = _point_rect_distance(ad["position"][0], ad["position"][2], tower_rect)
        if gap > 0.5 + _EPS:
            issues.append(f"{ad['id']}: ad not flush with its attached tower face")
        if ad["kind"] == "rooftop" and ad["position"][1] <= tower["height"]:
            issues.append(f"{ad['id']}: rooftop ad below the tower roof")

    # 6. Cable endpoints stay inside the site with y >= 2.0.
    for cable in data["cables"]:
        for key in ("from", "to"):
            x, y, z = cable[key]
            if abs(x) > half or abs(z) > half:
                issues.append(f"{cable['id']}: endpoint outside the site")
            if y < 2.0 - _EPS:
                issues.append(f"{cable['id']}: endpoint below y=2.0")

    return issues