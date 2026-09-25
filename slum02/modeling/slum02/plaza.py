"""Central plaza: the ruined factory lot (floor, pits, steel, machinery, burnt car, fire barrel,
perimeter) and the huge east wall that carries the "トーキョーN◎VA" spray art.

Pure Python and deterministic. Coordinates are Resonite XYZ (Y up, metres, +Z north).
Every assembly except ``east-wall`` is authored in world space around origin (0, 0, 0);
``east-wall`` parts are local to its origin ``(9.6, FLOOR_TOP - 0.12, 0)``.

R11 winding rule: every part is a closed shell with outward winding (positive signed
volume). Hand-built shells go through ``_outward`` which flips a consistently wound
shell if it came out inside-out, so no part depends on Blender's normal recalculation.

The Blender-side text meshing and the rubble scatter come in Task 7; this module only
publishes the lettering layout (``spray_layout``), the ◎ glyph (``ring_glyph``) and the
overspray masks (``east-wall`` ``meta["sprays"]``).
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from typing import Any

from modeling.slum02 import SEED
from modeling.slum02 import geometry as g
from modeling.slum02.sectors import register
from modeling.slum02.vcolor import Spray

FLOOR_TOP = 0.12
WALL_ORIGIN = (9.6, FLOOR_TOP - 0.12, 0.0)
WALL_HEIGHT = 8.8
WALL_FRONT_X = 9.2
PLANE_X = 9.195
PILASTER_Z = (-8.0, -4.0, 0.0, 4.0, 8.0)
PILASTER_STUB_TOP = 1.7          # centre pilasters end below the 1.9 m baseline of line 2
RAIL_HEIGHT = 7.0
BLACK_HALO = (0.15, 0.15, 0.16)
RED_SPILL = (1.0, 0.3, 0.3)
TAG_COLORS = ((0.6, 1.0, 0.3), (0.3, 0.9, 1.0), (1.0, 0.3, 0.8))

Vec = tuple[float, float, float]
_BOX_FACES = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))


# --------------------------------------------------------------------------- vector helpers


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    length = math.sqrt(_dot(a, a))
    return _mul(a, 1.0 / length)


# --------------------------------------------------------------------------- mesh helpers


def signed_volume(m: g.MeshData) -> float:
    total = 0.0
    for face in m.faces:
        p0 = m.vertices[face[0]]
        for i in range(1, len(face) - 1):
            total += _dot(p0, _cross(m.vertices[face[i]], m.vertices[face[i + 1]])) / 6
    return total


def _outward(m: g.MeshData) -> g.MeshData:
    """Flip a consistently wound closed shell if it came out inside-out (R11)."""
    if signed_volume(m) > 0:
        return m
    return g.MeshData(m.name, m.vertices, tuple(tuple(reversed(f)) for f in m.faces), m.material)


def _planarize(m: g.MeshData, tol: float = 1e-6) -> g.MeshData:
    """Split non-planar polygons (bent tubes, torn plates) into triangles so metric UVs stay exact."""
    faces: list[tuple[int, ...]] = []
    changed = False
    for f in m.faces:
        if len(f) > 3:
            pts = [m.vertices[i] for i in f]
            n = _newell(pts)
            c = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
            if max(abs(_dot(_sub(p, c), n)) for p in pts) > tol:
                faces.extend((f[0], f[k], f[k + 1]) for k in range(1, len(f) - 1))
                changed = True
                continue
        faces.append(f)
    return g.MeshData(m.name, m.vertices, tuple(faces), m.material) if changed else m


def _newell(pts):
    nx = ny = nz = 0.0
    for a, b in zip(pts, (*pts[1:], pts[0])):
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / length, ny / length, nz / length)


def _combine(name: str, meshes: Sequence[g.MeshData], material: str | None = None) -> g.MeshData:
    verts: list[Vec] = []
    faces: list[tuple[int, ...]] = []
    for m in meshes:
        off = len(verts)
        verts.extend(m.vertices)
        faces.extend(tuple(off + i for i in f) for f in m.faces)
    return g.mesh(name, verts, faces, material or meshes[0].material)


def _hexa(name: str, corners: Sequence[Sequence[float]], material: str) -> g.MeshData:
    """Deformed box from 8 corners in ``geometry.box`` order (-x-y-z, +x-y-z, +x+y-z, -x+y-z, ... +z)."""
    return _outward(g.mesh(name, corners, _BOX_FACES, material))


def _block(name: str, x0: float, x1: float, z0: float, z1: float, y0: float,
           tops: Sequence[float], material: str, bottoms: Sequence[float] | None = None) -> g.MeshData:
    """Axis-aligned footprint with independent corner heights; ``tops``/``bottoms`` at (x0,z0),(x1,z0),(x1,z1),(x0,z1)."""
    b = bottoms or (y0, y0, y0, y0)
    t = tops
    return _hexa(name, ((x0, b[0], z0), (x1, b[1], z0), (x1, t[1], z0), (x0, t[0], z0),
                        (x0, b[3], z1), (x1, b[2], z1), (x1, t[2], z1), (x0, t[3], z1)), material)


def _basis(d: Vec, hint: Vec) -> tuple[Vec, Vec, Vec]:
    d = _norm(d)
    u = _sub(hint, _mul(d, _dot(hint, d)))
    if _dot(u, u) < 1e-10:
        alt = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 0.0, 1.0)
        u = _sub(alt, _mul(d, _dot(alt, d)))
    u = _norm(u)
    return u, d, _cross(u, d)  # right-handed: identity when u=X, d=Y


def _frame(m: g.MeshData, origin: Sequence[float], d: Vec, hint: Vec, name: str | None = None) -> g.MeshData:
    """Map local (x, y, z) to origin + x*u + y*d + z*w (a proper rotation, so winding survives)."""
    u, dd, w = _basis(d, hint)
    verts = tuple(tuple(origin[k] + p[0] * u[k] + p[1] * dd[k] + p[2] * w[k] for k in range(3)) for p in m.vertices)
    return g.MeshData(name or m.name, verts, m.faces, m.material)  # type: ignore[arg-type]


def _beam(name: str, p0: Vec, p1: Vec, su: float, sw: float, material: str, hint: Vec = (0.0, 1.0, 0.0)) -> g.MeshData:
    d = _sub(p1, p0)
    length = math.sqrt(_dot(d, d))
    return _frame(g.box(name, (0, length / 2, 0), (su, length, sw), material), p0, d, hint)


def _move(m: g.MeshData, offset: Sequence[float], yaw: float = 0.0, name: str | None = None) -> g.MeshData:
    return g.transformed(m, yaw, offset, name)


def _cells(name: str, node: Callable[[int, int, int], Sequence[float]], ni: int, nj: int,
           solid: Callable[[int, int], bool], material: str, periodic: bool = False) -> g.MeshData:
    """Closed shell of hexahedral cells (i, j) with k=0/1 layers; faces between solid cells are dropped."""
    b = g.GridBuilder()

    def is_solid(i: int, j: int) -> bool:
        if periodic:
            i %= ni
        elif not 0 <= i < ni:
            return False
        return 0 <= j < nj and solid(i, j)

    def p(i: int, j: int, k: int):
        return node(i % ni if periodic else i, j, k)

    for i in range(ni):
        for j in range(nj):
            if not is_solid(i, j):
                continue
            c = [p(i + sa, j + sb, sc) for sa, sb, sc in
                 ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))]
            emit = [True, True, not is_solid(i, j - 1), not is_solid(i + 1, j), not is_solid(i, j + 1), not is_solid(i - 1, j)]
            for face, on in zip(_BOX_FACES, emit):
                if on:
                    b.faces.append(tuple(b.v(c[k]) for k in face))
    return _outward(b.build(name, material))


def _sweep(name: str, pts: Sequence[Vec], across: Sequence[Vec], normals: Sequence[Vec],
           width: float, thick: float, material: str) -> g.MeshData:
    """Closed flat strip along ``pts``; ``across``/``normals`` are per-point unit vectors."""
    def node(i, j, k):
        return _add(_add(pts[i], _mul(across[i], (j - 0.5) * width)), _mul(normals[i], (k - 0.5) * thick))
    return _cells(name, node, len(pts) - 1, 1, lambda i, j: True, material)


def _revolve(name: str, profile: Sequence[tuple[float, float]], segments: int, material: str,
             loop: bool = False) -> g.MeshData:
    """Solid of revolution around local +Y; profile entries are (radius, y); radius 0 makes a pole."""
    b = g.GridBuilder()

    def ring(r, y):
        if r <= 1e-9:
            return [b.v((0.0, y, 0.0))] * segments
        return [b.v((r * math.cos(math.tau * s / segments), y, r * math.sin(math.tau * s / segments))) for s in range(segments)]

    rings = [ring(r, y) for r, y in profile]
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if loop else [])
    for a, c in pairs:
        for s in range(segments):
            quad = (a[s], a[(s + 1) % segments], c[(s + 1) % segments], c[s])
            face = tuple(v for k, v in enumerate(quad) if v != quad[k - 1])
            if len(face) >= 3:
                b.faces.append(face)
    return _outward(b.build(name, material))


def h_beam(name: str, length: float, depth: float = 0.4, flange: float = 0.3, t: float = 0.025,
           material: str = "rust", rng: random.Random | None = None, tear: float = 0.0,
           tear_bottom: float = 0.0) -> g.MeshData:
    """H section (two flanges + web), long in +Y from 0 to ``length``, depth along X.

    ``tear``/``tear_bottom`` shorten each plate corner by a random amount so torn ends are ragged.
    """
    def cut(amount):
        if not amount or rng is None:
            return (0.0, 0.0, 0.0, 0.0)
        return tuple(rng.uniform(0.0, amount) for _ in range(4))

    hd, hf = depth / 2, flange / 2
    plates = (("fa", hd - t, hd, -hf, hf), ("fb", -hd, -hd + t, -hf, hf), ("web", -hd + t, hd - t, -t / 2, t / 2))
    parts = []
    for tag, x0, x1, z0, z1 in plates:
        top, bot = cut(tear), cut(tear_bottom)
        parts.append(_block(f"{name}-{tag}", x0, x1, z0, z1, 0.0, [length - c for c in top], material, bottoms=list(bot)))
    return _combine(name, parts, material)


def _bolt(name: str, x: float, y: float, z: float, stick: float = 0.12) -> g.MeshData:
    """Anchor bolt with hex nut and square washer, standing on the surface at height ``y``."""
    washer = g.box(f"{name}-washer", (x, y + 0.005, z), (0.1, 0.01, 0.1), "steel_dark")
    nut = g.cylinder(f"{name}-nut", (x, y + 0.01 + 0.0175, z), 0.036, 0.035, 6, "steel_dark")
    rod = g.cylinder(f"{name}-rod", (x, y + stick / 2, z), 0.016, stick, 8, "steel_dark")
    return _combine(name, [washer, nut, rod], "steel_dark")


# --------------------------------------------------------------------------- east wall + spray art


def spray_layout() -> dict[str, Any]:
    """Lettering layout for Task 7. Seen from the plaza (looking +X) text reads from +Z to -Z."""
    ring_center = [PLANE_X, 1.9 + 3.2 / 2, 0.0]
    return {
        "lines": [
            {"text": "トーキョー", "baseline_y": 5.9, "height": 2.8, "center_z": 0.0},
            {"text": "N", "baseline_y": 1.9, "height": 3.2, "center_z": 3.0, "align": "right", "edge_z": 1.75},
            {"ring": {"center": ring_center, "outer_radius": 1.4, "band": 0.28, "inner_outer_radius": 0.75,
                      "depth": 0.006},
             "baseline_y": 1.9, "height": 3.2, "center_z": 0.0},
            {"text": "VA", "baseline_y": 1.9, "height": 3.2, "center_z": -4.05, "align": "left", "edge_z": -1.75},
        ],
        "max_width": 17.0,
        "plane_x": PLANE_X,
        "reading_direction": [0.0, 0.0, -1.0],
        "red_offset": 0.010,
        "black_offset": 0.005,
        "black_grow": 0.06,
    }


def _annulus(name: str, center: Vec, r_out: float, r_in: float, x_back: float, depth: float,
             material: str, segments: int = 48) -> g.MeshData:
    """Flat ring in the YZ plane, from ``x_back`` towards -X by ``depth``."""
    cx, cy, cz = center

    def node(i, j, k):
        a = math.tau * i / segments
        r = (r_in, r_out)[j]
        return (x_back - depth * k, cy + r * math.sin(a), cz + r * math.cos(a))
    return _cells(name, node, segments, 1, lambda i, j: True, material, periodic=True)


def ring_glyph(center: Sequence[float], outer_radius: float, band: float, depth: float) -> tuple[g.MeshData, g.MeshData]:
    """◎ as (red fill, black outline): outer + inner ring, each 48 segments.

    ``center[0]`` is the painting plane. Red floats 0.010 m in front of it (towards the plaza,
    -X); black is every band grown by 0.06 m and floats 0.005 m, so red always sits in front.
    """
    c = tuple(float(v) for v in center)
    inner_outer = outer_radius * 0.75 / 1.4
    rings = ((outer_radius, outer_radius - band), (inner_outer, inner_outer - band))
    grow = 0.06
    red = _combine("glyph-ring-red", [_annulus(f"glyph-ring-red-{k}", c, ro, ri, c[0] - 0.010, depth, "spray_red")
                                      for k, (ro, ri) in enumerate(rings)], "spray_red")
    black = _combine("glyph-ring-black", [_annulus(f"glyph-ring-black-{k}", c, ro + grow, max(ri - grow, 0.02),
                                                   c[0] - 0.005, depth, "spray_black")
                                          for k, (ro, ri) in enumerate(rings)], "spray_black")
    return red, black


def _to_wall(m: g.MeshData, name: str | None = None) -> g.MeshData:
    """Wall-local (a = world Z along the wall, y, c = +towards the plaza) -> part coordinates."""
    return g.transformed(m, -math.pi / 2, (0.0, 0.0, 0.0), name)


def _wall_sprays(rng: random.Random) -> list[Spray]:
    sprays: list[Spray] = []
    # (centre y, z extent) of the two lettering rows; see spray_layout().
    for cy, z_lo, z_hi in ((5.9 + 1.4, -7.0, 7.0), (1.9 + 1.6, -6.35, 4.25)):
        n = int(round((z_hi - z_lo) / 0.8))
        for k in range(n + 1):
            z = z_lo + (z_hi - z_lo) * k / n
            sprays.append(Spray((WALL_FRONT_X, cy + rng.uniform(-0.9, 0.9), z + rng.uniform(-0.2, 0.2)),
                                round(rng.uniform(0.6, 1.0), 3), BLACK_HALO, 0.35))
            sprays.append(Spray((WALL_FRONT_X, cy + rng.choice((-1, 1)) * rng.uniform(0.9, 1.6), z + rng.uniform(-0.3, 0.3)),
                                round(rng.uniform(0.4, 0.7), 3), RED_SPILL, 0.3))
    # Other crews' tags low on the wall (0.5-3 m), clear of the big lettering.
    for k, (z, y) in enumerate(((9.3, 1.2), (7.0, 2.4), (5.6, 0.8), (-7.4, 1.5), (-8.6, 2.7), (-9.4, 0.7))):
        sprays.append(Spray((WALL_FRONT_X, y, z), round(rng.uniform(0.5, 0.8), 3), TAG_COLORS[k % 3], 0.45))
    # Rain streaks below the four window recesses and grime at the foot of the wall.
    for z in (-9.15, 9.15):
        for y in (3.9, 3.2, 6.1, 5.5):
            sprays.append(Spray((WALL_FRONT_X, y, z), 0.45, (0.55, 0.53, 0.5), 0.5))
    for k in range(9):
        sprays.append(Spray((WALL_FRONT_X, 0.2, -9.0 + 2.25 * k), 1.3, (0.6, 0.56, 0.5), 0.4))
    return sprays


def _east_wall(rng: random.Random) -> g.Assembly:
    windows = [(8.7, 4.4, 9.6, 5.6), (8.7, 6.6, 9.6, 7.8), (-9.6, 4.4, -8.7, 5.6), (-9.6, 6.6, -8.7, 7.8)]
    parts: list[g.MeshData] = []
    body = g.wall_with_openings("wall-body", 20.0, WALL_HEIGHT, 0.8, windows, 0.3, 0.25, "concrete_raw")
    parts.append(_to_wall(body))
    ht = 0.4
    # Window sills (small projecting ledges).
    for k, (a0, y0, a1, _y1) in enumerate(windows):
        parts.append(_to_wall(g.beveled_box(f"wall-sill-{k}", ((a0 + a1) / 2, y0 - 0.06, ht + 0.05),
                                            (a1 - a0 + 0.2, 0.12, 0.1), 0.02, "concrete_raw")))
    # Formwork joints (raised fins) and form-tie plugs on both faces.
    for side, c in ((1, ht + 0.002), (-1, -ht - 0.002)):
        tag = "front" if side > 0 else "back"
        for k, y in enumerate((1.2, 2.4, 3.6, 4.8, 6.0, 7.2, 8.4)):
            span = 17.2 if side > 0 and any(w[1] < y < w[3] for w in windows) else 19.96  # stop short of the window recesses
            parts.append(_to_wall(g.box(f"wall-joint-{tag}-h{k}", (0.0, y, c), (span, 0.02, 0.006), "concrete_dark")))
        for k, a in enumerate((-7.2, -4.8, -2.4, 2.4, 4.8, 7.2)):
            parts.append(_to_wall(g.box(f"wall-joint-{tag}-v{k}", (a, WALL_HEIGHT / 2, c), (0.02, WALL_HEIGHT - 0.04, 0.006), "concrete_dark")))
        ties = []
        for i in range(22):
            a = -9.45 + 0.9 * i
            for j in range(7):
                y = 0.6 + 1.2 * j
                if any(w[0] - 0.1 < a < w[2] + 0.1 and w[1] - 0.1 < y < w[3] + 0.1 for w in windows):
                    continue
                ties.append(g.box(f"tie-{tag}-{i}-{j}", (a, y, c), (0.045, 0.045, 0.006), "concrete_dark"))
        parts.append(_to_wall(_combine(f"wall-ties-{tag}", ties, "concrete_dark")))
    # Pilasters on the plaza side; the centre three are broken off below the lettering.
    for k, a in enumerate(PILASTER_Z):
        if k in (0, 4):
            top = WALL_HEIGHT - 0.02
            parts.append(_to_wall(g.beveled_box(f"wall-pilaster-{k}", (a, top / 2, ht + 0.175), (0.6, top, 0.35), 0.03, "concrete_raw")))
        else:
            tops = [PILASTER_STUB_TOP - rng.uniform(0.0, 0.35) for _ in range(4)]
            parts.append(_to_wall(_block(f"wall-pilaster-{k}", a - 0.3, a + 0.3, ht, ht + 0.35, 0.0, tops, "concrete_raw")))
            for s in range(2):
                y1 = max(tops) + rng.uniform(0.15, 0.4)
                pa = a + (-0.18 if s == 0 else 0.18)
                parts.append(_to_wall(g.tube(f"wall-stub-bar-{k}-{s}", [(pa, 1.1, ht + 0.25), (pa, y1, ht + 0.25),
                                                                        (pa + rng.uniform(-0.1, 0.1), y1 + 0.12, ht + 0.25 + rng.uniform(0.02, 0.12))],
                                             0.012, 5, "rust")))
    # Crumbling crown: irregular blocks along the top, 20 % missing; rebar sticks out of the gaps.
    a = -10.0
    k = 0
    gaps: list[tuple[float, float]] = []
    crown_tops: list[tuple[float, float, float]] = []
    while a < 10.0 - 1e-6:
        step = min(rng.uniform(0.4, 1.6), 10.0 - a)
        if step < 0.3:
            step = 10.0 - a
        a1 = a + step
        if rng.random() < 0.2:
            gaps.append((a, a1))
        else:
            h = rng.uniform(0.2, 1.2)
            tops = [WALL_HEIGHT + h * rng.uniform(0.55, 1.0) for _ in range(4)]
            front = ht - rng.uniform(0.0, 0.2)
            back = -ht + rng.uniform(0.0, 0.2)
            inset = 0.02 if a > -9.99 else 0.0
            parts.append(_to_wall(_block(f"wall-crown-{k:02d}", a + inset, a1 - (0.02 if a1 < 9.99 else 0.0), back, front,
                                         WALL_HEIGHT - 0.03, tops, "concrete_raw")))
            crown_tops.append((a, a1, min(tops)))
            k += 1
        a = a1
    spots: list[tuple[float, float]] = []
    for a0, a1 in gaps:
        n = max(1, int((a1 - a0) / 0.35))
        spots += [(a0 + (a1 - a0) * (s + 0.5) / n, WALL_HEIGHT) for s in range(n)]
    for a0, a1, top in crown_tops:
        spots.append(((a0 + a1) / 2, top))
    rng.shuffle(spots)
    spots = sorted(spots[:18])
    while len(spots) < 18:  # always 18 bars (brief)
        spots.append((rng.uniform(-9.5, 9.5), WALL_HEIGHT))
    for k, (a, base_y) in enumerate(sorted(spots)):
        c = rng.choice((-0.28, 0.28)) + rng.uniform(-0.04, 0.04)
        rise = rng.uniform(0.3, 1.1)
        p0 = (a, base_y - 0.3, c)
        p1 = (a, base_y + rise, c)
        bend = rng.uniform(0.15, 0.5)
        p2 = (a + rng.uniform(-0.3, 0.3), base_y + rise + rng.uniform(-0.25, 0.1), max(-0.62, min(0.62, c + math.copysign(bend, c))))
        parts.append(_to_wall(g.tube(f"rebar-{k:02d}", [p0, p1, p2], 0.012, 5, "rust")))
    return g.Assembly("east-wall", "east-wall", "plaza", WALL_ORIGIN, parts,
                      meta={"sprays": _wall_sprays(rng), "spray_art": spray_layout()})


# --------------------------------------------------------------------------- floor + pits


def _pit_depth(k: int) -> float:
    return (0.9, 1.4)[k % 2]


def _crack(name: str, rng: random.Random, start: tuple[float, float], avoid: list[tuple[float, float, float, float]]) -> g.MeshData:
    heading = rng.uniform(0, math.tau)
    pts2 = [start]
    for _ in range(rng.randint(5, 9)):
        heading += rng.uniform(-0.7, 0.7)
        step = rng.uniform(0.35, 1.0)
        x = pts2[-1][0] + math.cos(heading) * step
        z = pts2[-1][1] + math.sin(heading) * step
        if abs(x) > 9.0 or abs(z) > 9.6 or any(r[0] - 0.2 < x < r[2] + 0.2 and r[1] - 0.2 < z < r[3] + 0.2 for r in avoid):
            break
        pts2.append((x, z))
    if len(pts2) < 3:
        pts2.append((pts2[-1][0] + 0.4, pts2[-1][1] + 0.2))
    pts = [(x, FLOOR_TOP, z) for x, z in pts2]
    across, normals = [], []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        t = _norm(_sub(b, a))
        across.append((-t[2], 0.0, t[0]))
        normals.append((0.0, 1.0, 0.0))
    return _sweep(name, pts, across, normals, 0.04, 0.008, "concrete_dark")


def _floor(data: dict[str, Any], rng: random.Random) -> g.Assembly:
    pits = [tuple(p) for p in data["plaza_features"]["pits"]]
    xs = g._splits(-10.0, 10.0, 0.5, [c for p in pits for c in (p[0], p[2])])
    zs = g._splits(-10.0, 10.0, 0.5, [c for p in pits for c in (p[1], p[3])])

    def in_pit(i, j):
        mx, mz = (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
        return any(p[0] < mx < p[2] and p[1] < mz < p[3] for p in pits)

    parts = [_cells("floor-slab", lambda i, j, k: (xs[i], (0.0, FLOOR_TOP)[k], zs[j]), len(xs) - 1, len(zs) - 1,
                    lambda i, j: not in_pit(i, j), "factory_floor")]
    sprays: list[Spray] = []
    for k, (x0, z0, x1, z1) in enumerate(pits):
        d = _pit_depth(k)
        w = 0.12
        top = FLOOR_TOP - 0.01
        for s, (a0, a1, b0, b1) in enumerate(((x0, x1, z0, z0 + w), (x0, x1, z1 - w, z1), (x0, x0 + w, z0 + w, z1 - w), (x1 - w, x1, z0 + w, z1 - w))):
            parts.append(_block(f"pit-{k}-wall-{s}", a0, a1, b0, b1, -d, [top] * 4, "concrete_dark"))
        # Steel edge nosing around the rim.
        n = 0.07
        for s, (cx, cz, sx, sz) in enumerate((((x0 + x1) / 2, z0 + 0.015, x1 - x0 + 0.04, n), ((x0 + x1) / 2, z1 - 0.015, x1 - x0 + 0.04, n),
                                               (x0 + 0.015, (z0 + z1) / 2, n, z1 - z0 - 0.1), (x1 - 0.015, (z0 + z1) / 2, n, z1 - z0 - 0.1))):
            parts.append(g.box(f"pit-{k}-nosing-{s}", (cx, FLOOR_TOP - 0.01, cz), (sx, 0.03, sz), "steel_dark"))
        parts.append(g.box(f"pit-{k}-mud", ((x0 + x1) / 2, -d - 0.05, (z0 + z1) / 2), (x1 - x0, 0.1, z1 - z0), "mud"))
        wx0, wx1 = x0 + w + 0.02, x1 - w - rng.uniform(0.3, 0.7)
        wz0, wz1 = z0 + w + rng.uniform(0.1, 0.4), z1 - w - 0.02
        parts.append(g.box(f"pit-{k}-water", ((wx0 + wx1) / 2, -d + 0.03, (wz0 + wz1) / 2), (wx1 - wx0, 0.06, wz1 - wz0), "asphalt_wet"))
        sprays.append(Spray(((x0 + x1) / 2, FLOOR_TOP, (z0 + z1) / 2), max(x1 - x0, z1 - z0) * 0.9, (0.62, 0.6, 0.57), 0.6))
        # Ladder rungs cast into the pit wall.
        for r in range(int(d / 0.3)):
            y = -d + 0.35 + 0.3 * r
            parts.append(g.box(f"pit-{k}-rung-{r}", (x0 + w + 0.06, y, z0 + 0.45), (0.12, 0.025, 0.4), "rust"))
    # Pit 0 is a drain sump: half-covered by a broken grating; one grate panel fell in.
    x0, z0, x1, z1 = pits[0]
    bars = []
    for b in range(9):
        z = z0 + 0.15 + b * 0.1
        bars.append(g.box(f"grate-bar-{b}", ((x0 + x1) / 2 + 0.3, FLOOR_TOP - 0.03, z), (x1 - x0 - 0.8 + (0.4 if b % 3 else 0.0), 0.03, 0.02), "rust_dark"))
    for s, x in enumerate((x0 + 0.4, x1 - 0.12)):
        bars.append(g.box(f"grate-frame-{s}", (x, FLOOR_TOP - 0.03, z0 + 0.6), (0.04, 0.04, 0.95), "rust_dark"))
    parts.append(_combine("pit-0-grate", bars, "rust_dark"))
    fallen = [g.box(f"fallen-grate-bar-{b}", (b * 0.1 - 0.35, 0.0, 0.0), (0.02, 0.03, 0.9), "rust_dark") for b in range(8)]
    fallen.append(g.box("fallen-grate-frame", (0.0, -0.02, 0.0), (0.8, 0.02, 0.05), "rust_dark"))
    parts.append(g.transformed_xyz(_combine("pit-0-fallen-grate", fallen, "rust_dark"), 0.0, 0.3, math.radians(32),
                                   (x0 + 0.9, -_pit_depth(0) + 0.35, z1 - 0.6)))
    # Pit 1 is a machine pit crossed by a broken pipe.
    x0, z0, x1, z1 = pits[1]
    parts.append(g.pipe("pit-1-pipe", (x0 + 0.13, -0.6, z0 + 0.7), (x1 - 0.13, -0.75, z0 + 0.8), 0.09, "rust", 10))
    parts.append(g.pipe("pit-1-pipe-flange", (x0 + 0.9, -0.64, z0 + 0.72), (x0 + 0.95, -0.64, z0 + 0.72), 0.14, "rust_dark", 10))
    # Cracks: 12 dark polylines, width 0.04, 4 mm proud.
    starts = [(-7.0, -2.0), (-3.5, 1.5), (2.0, -1.0), (5.5, 4.5), (-6.5, 8.0), (0.0, 8.8), (-8.5, -8.8), (7.5, -7.5),
              (-1.0, -6.0), (4.5, 1.5), (-3.0, 5.5), (6.5, 2.5)]
    for k, s in enumerate(starts):
        parts.append(_crack(f"crack-{k:02d}", rng, s, pits))
    # Heaved slab fragments near the pits and the car.
    for k, (x, z, sx, sz, rx, rz) in enumerate(((-3.0, -8.8, 1.1, 0.8, 0.10, 0.06), (1.9, -8.6, 0.9, 1.2, -0.08, 0.12),
                                                   (7.3, 2.6, 1.3, 0.9, 0.12, -0.05), (-6.8, 1.2, 0.8, 0.7, -0.1, -0.1))):
        slab = g.beveled_box(f"slab-chunk-{k}", (0, 0, 0), (sx, 0.12, sz), 0.02, "factory_floor")
        parts.append(g.transformed_xyz(slab, rx, rng.uniform(0, math.pi), rz, (x, FLOOR_TOP + 0.05, z)))
    # Cause-based floor dirt: oil under machines, soot under the car and the fire, rust at column feet.
    fx, fz = data["plaza_features"]["fire_barrel"]
    cx, cz, _ = data["plaza_features"]["car"]
    sprays += [Spray((cx, FLOOR_TOP, cz), 3.0, (0.3, 0.29, 0.28), 0.85), Spray((fx, FLOOR_TOP, fz), 1.6, (0.35, 0.33, 0.3), 0.8)]
    for x, z, _t, _h in data["plaza_features"]["columns"]:
        sprays.append(Spray((x, FLOOR_TOP, z), 1.0, (1.1, 0.62, 0.38), 0.6))
    for x, z, _y, _kind in data["plaza_features"]["machines"]:
        sprays.append(Spray((x + 0.4, FLOOR_TOP, z - 0.3), 2.2, (0.45, 0.43, 0.42), 0.65))
    for _ in range(10):
        sprays.append(Spray((rng.uniform(-9, 8), FLOOR_TOP, rng.uniform(-9, 9)), rng.uniform(1.2, 2.6), (1.18, 1.15, 1.1), rng.uniform(0.3, 0.6)))
    # Water ponds and old oil soaked into the slab: broad dark blotches of varying strength.
    for _ in range(26):
        tone = rng.uniform(0.35, 0.65)
        sprays.append(Spray((rng.uniform(-9.5, 8.8), FLOOR_TOP, rng.uniform(-9.5, 9.5)), rng.uniform(1.2, 3.2),
                            (tone, tone * 0.97, tone * 0.93), rng.uniform(0.6, 0.9)))
    # Damp, dirty margins where debris collects: along the perimeter walls and the foot of the east wall.
    for k in range(11):
        t = -9.5 + 1.9 * k
        for c in ((-9.6, t), (t, 9.6), (t, -9.6), (9.0, t)):
            sprays.append(Spray((c[0], FLOOR_TOP, c[1]), 1.3, (0.55, 0.54, 0.5), 0.6))
    return g.Assembly("plaza-floor", "plaza-floor", "plaza", (0.0, 0.0, 0.0), parts, meta={"sprays": sprays})


# --------------------------------------------------------------------------- machine bases


BASES = (  # (x, z, sx, sz, height, carries)
    (-4.5, -6.5, 3.2, 2.4, 0.35, "press"),
    (6.5, -1.0, 2.0, 4.6, 0.3, "tank"),
    (-1.5, -4.8, 2.0, 1.4, 0.45, None),
    (3.4, -1.6, 1.6, 1.2, 0.6, None),
    (-7.8, -8.0, 1.4, 1.4, 0.3, None),
)


def _machine_bases(rng: random.Random) -> g.Assembly:
    parts = []
    for k, (x, z, sx, sz, h, carries) in enumerate(BASES):
        top = FLOOR_TOP + h
        y0 = FLOOR_TOP - 0.05
        parts.append(g.beveled_box(f"base-{k}", (x, (top + y0) / 2, z), (sx, top - y0, sz), 0.05, "concrete_raw"))
        for s, (bx, bz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            px, pz = x + bx * (sx / 2 - 0.22), z + bz * (sz / 2 - 0.22)
            if carries:
                parts.append(_bolt(f"bolt-{k}-{s}", px, top, pz, 0.14))
            else:
                bolt = _bolt(f"bolt-{k}-{s}", 0.0, 0.0, 0.0, rng.uniform(0.08, 0.2))
                parts.append(g.transformed_xyz(bolt, rng.uniform(-0.3, 0.3), 0.0, rng.uniform(-0.3, 0.3), (px, top, pz)))
        if not carries:
            # Torn machine foot and steel shims left behind when the machine was cut away.
            parts.append(g.box(f"shim-{k}", (x + rng.uniform(-0.3, 0.3), top + 0.006, z + rng.uniform(-0.2, 0.2)),
                               (0.35, 0.012, 0.25), "steel_dark"))
            parts.append(_block(f"foot-{k}", x - 0.25, x + 0.25, z - 0.18, z + 0.18, top,
                                [top + rng.uniform(0.05, 0.25) for _ in range(4)], "rust"))
            parts.append(g.box(f"grout-{k}", (x, top + 0.004, z), (sx - 0.5, 0.008, sz - 0.5), "concrete_dark"))
    return g.Assembly("plaza-machine-bases", "plaza-machine-bases", "plaza", (0.0, 0.0, 0.0), parts)


# --------------------------------------------------------------------------- columns + crane rail


def _rail_frame(data):
    cols = data["plaza_features"]["columns"]
    c0 = (cols[0][0], 0.0, cols[0][1])
    c1 = (cols[1][0], 0.0, cols[1][1])
    d = _norm(_sub(c0, c1))
    n = (d[2], 0.0, -d[0])
    return c0, c1, d, n


def _column_parts(k: int, x: float, z: float, tilt_deg: float, height: float, yaw_dir: Vec,
                  rng: random.Random, broken: bool, rail_n: Vec | None) -> list[g.MeshData]:
    parts: list[g.MeshData] = []
    base_y = FLOOR_TOP + 0.065
    parts.append(g.box(f"grout-{k}", (x, FLOOR_TOP + 0.01, z), (0.8, 0.06, 0.9), "concrete_dark"))
    plate = _frame(g.box(f"baseplate-{k}", (0, 0.0125, 0), (0.6, 0.025, 0.7), "rust"), (x, FLOOR_TOP + 0.04, z), (0.0, 1.0, 0.0), yaw_dir)
    parts.append(plate)
    u, _, w = _basis((0.0, 1.0, 0.0), yaw_dir)
    for s, (a, b) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        px = x + u[0] * a * 0.22 + w[0] * b * 0.27
        pz = z + u[2] * a * 0.22 + w[2] * b * 0.27
        parts.append(_bolt(f"colbolt-{k}-{s}", px, base_y, pz, 0.1))
    # Shaft direction: tilted away from vertical in the yaw plane.
    t = math.radians(tilt_deg)
    tilt_dir = _norm((-x, 0.0, -0.3 * z))  # lean in towards the plaza centre, never into the wall or fence
    d = _norm((tilt_dir[0] * math.sin(t), math.cos(t), tilt_dir[2] * math.sin(t)))
    origin = (x, base_y, z)
    shaft = height * 0.5 if broken else height - base_y
    rust_len = 1.1
    lower = h_beam(f"shaft-{k}-rust", rust_len, material="rust")
    upper = h_beam(f"shaft-{k}-paint", shaft - rust_len, material="paint_yellow_faded", rng=rng,
                   tear=0.0 if k == 1 else (0.5 if broken else 0.3))
    parts.append(_frame(lower, origin, d, yaw_dir))
    parts.append(_frame(_move(upper, (0.0, rust_len, 0.0)), origin, d, yaw_dir))
    # Base gussets on both flange faces.
    for s, (gx, gz) in enumerate(((0.2 + 0.06, 0.0), (-0.2 - 0.06, 0.0))):
        gusset = _block(f"gusset-{k}-{s}", gx - 0.06, gx + 0.06, gz - 0.006, gz + 0.006, 0.0,
                        [0.25, 0.02, 0.02, 0.25] if gx > 0 else [0.02, 0.25, 0.25, 0.02], "rust")
        parts.append(_frame(gusset, origin, d, yaw_dir))
    if k == 1:  # clean cap plate: Task 7 mounts the spray-wall floodlight here
        parts.append(_frame(g.box(f"cap-{k}", (0.0, shaft + 0.01, 0.0), (0.45, 0.02, 0.4), "rust"), origin, d, yaw_dir))
    if rail_n is not None:
        # Crane corbel: tapered bracket on the flange that faces the runway.
        y_rel = RAIL_HEIGHT - base_y
        corbel = _block(f"corbel-{k}", 0.2, 0.85, -0.15, 0.15, 0.0, [0.5, 0.5, 0.5, 0.5], "paint_yellow_faded",
                        bottoms=[0.0, 0.32, 0.32, 0.0])
        parts.append(_frame(_move(corbel, (0.0, y_rel - 0.5, 0.0)), origin, d, yaw_dir))
        parts.append(_frame(g.box(f"corbel-plate-{k}", (0.55, y_rel - 0.01, 0.0), (0.7, 0.02, 0.36), "rust"), origin, d, yaw_dir))
    if broken:
        # The upper half lies on the floor next to the stump, resting on one flange.
        length = height * 0.5 - 0.35
        fallen = h_beam(f"fallen-{k}", length, material="paint_yellow_faded", rng=rng, tear=0.4, tear_bottom=0.4)
        lay = _norm((-0.99, -0.02, 0.1))
        parts.append(_frame(fallen, (x - 0.45, FLOOR_TOP + 0.2 + 0.02, z + 0.35), lay, (0.0, 1.0, 0.0), f"fallen-{k}"))
        parts.append(_frame(h_beam(f"fallen-{k}-rust", 0.6, material="rust", rng=rng, tear=0.2),
                            (x - 0.45 + lay[0] * length, FLOOR_TOP + 0.2 + 0.02 + lay[1] * length, z + 0.35 + lay[2] * length),
                            lay, (0.0, 1.0, 0.0), f"fallen-{k}-end"))
    return parts


def _columns(data: dict[str, Any], rng: random.Random) -> g.Assembly:
    _c0, _c1, _d, n = _rail_frame(data)
    parts: list[g.MeshData] = []
    for k, (x, z, tilt, h) in enumerate(data["plaza_features"]["columns"]):
        if k in (0, 1):
            yaw_dir = n
        else:
            a = rng.uniform(0, math.pi)
            yaw_dir = (math.cos(a), 0.0, math.sin(a))
        parts += _column_parts(k, x, z, tilt, h, yaw_dir, rng, broken=(k == 4), rail_n=n if k in (0, 1) else None)
    return g.Assembly("plaza-columns", "plaza-columns", "plaza", (0.0, 0.0, 0.0), parts)


def _crane_rail(data: dict[str, Any], rng: random.Random) -> g.Assembly:
    c0, c1, d, n = _rail_frame(data)
    offset = 0.55
    up = (0.0, 1.0, 0.0)
    y_mid = RAIL_HEIGHT + 0.3
    parts: list[g.MeshData] = []
    # A: still on the col-1 corbel, 3.0 m (0.4 m overhang), then the girder snapped and hangs 9.0 m to the floor.
    start = _add(_add(c1, _mul(n, offset)), _mul(d, -0.4))
    start = (start[0], y_mid, start[2])
    len_a, len_b = 3.0, 9.0
    beam_a = h_beam("girder-a", len_a, depth=0.6, flange=0.3, t=0.02, material="paint_yellow_faded")
    # rotate the section so the depth axis is vertical: local X -> world up
    parts.append(_frame(beam_a, start, d, up))
    kink = _add(start, _mul(d, len_a))
    drop = y_mid - (FLOOR_TOP + 0.02)
    horiz = math.sqrt(len_b ** 2 - drop ** 2)
    end = (kink[0] + d[0] * horiz, FLOOR_TOP + 0.02, kink[2] + d[2] * horiz)
    db = _norm(_sub(end, kink))
    split = 3.6
    parts.append(_frame(h_beam("girder-b-paint", split, depth=0.6, flange=0.3, t=0.02, material="paint_yellow_faded",
                               rng=rng, tear_bottom=0.15), kink, db, up))
    parts.append(_frame(h_beam("girder-b-rust", len_b - split, depth=0.6, flange=0.3, t=0.02, material="rust", rng=rng,
                               tear=0.3), _add(kink, _mul(db, split)), db, up))
    # Rail head and clips along A, the rail itself snapped and sticks out past the kink.
    rail_len = len_a + 0.9
    parts.append(_frame(g.box("rail-head", (0.34, rail_len / 2, 0.0), (0.08, rail_len, 0.07), "steel_dark"), start, d, up))
    for s in range(4):
        parts.append(_frame(g.box(f"rail-clip-{s}", (0.31, 0.3 + s * 0.8, 0.0), (0.02, 0.12, 0.22), "steel_dark"), start, d, up))
    # Torn flange shards at the kink.
    for s in range(3):
        shard = _block(f"kink-shard-{s}", -0.12, 0.12, -0.01, 0.01, 0.0, [rng.uniform(0.2, 0.45) for _ in range(4)], "rust")
        parts.append(g.transformed_xyz(shard, rng.uniform(-0.6, 0.6), rng.uniform(0, math.pi), rng.uniform(-0.6, 0.6),
                                       _add(kink, (rng.uniform(-0.2, 0.2), rng.uniform(-0.4, 0.1), rng.uniform(-0.2, 0.2)))))
    # The far end: a 1.6 m stub still sits on the col-0 corbel, ragged where it tore off.
    stub_start = _add(_add(c0, _mul(n, offset)), _mul(d, 0.4))
    stub_start = (stub_start[0], y_mid, stub_start[2])
    back = _mul(d, -1.0)
    parts.append(_frame(h_beam("girder-stub", 1.6, depth=0.6, flange=0.3, t=0.02, material="paint_yellow_faded", rng=rng,
                               tear=0.35), stub_start, back, up))
    parts.append(_frame(g.box("rail-head-stub", (0.34, 0.75, 0.0), (0.08, 1.5, 0.07), "steel_dark"), stub_start, back, up))
    # A slack chain from the girder A end.
    chain = g.catenary(_add(kink, (0.0, -0.3, 0.0)), (kink[0] - n[0] * 0.2, 3.8, kink[2] - n[2] * 0.2), 0.0, 6)
    parts.append(g.tube("hoist-chain", chain, 0.018, 5, "steel_dark"))
    parts.append(g.beveled_box("hoist-hook-block", (kink[0] - n[0] * 0.2, 3.62, kink[2] - n[2] * 0.2), (0.22, 0.34, 0.14), 0.03, "paint_yellow_faded"))
    return g.Assembly("plaza-crane-rail", "plaza-crane-rail", "plaza", (0.0, 0.0, 0.0), parts)


# --------------------------------------------------------------------------- truss


def _angle(name: str, a: tuple[float, float], b: tuple[float, float], z: float, material: str = "rust",
           leg: float = 0.075, t: float = 0.008) -> g.MeshData:
    """Equal-leg angle between two points of the truss plane (local x-y, thickness z)."""
    p0, p1 = (a[0], a[1], z), (b[0], b[1], z)
    leg_a = _beam(f"{name}-a", p0, p1, leg, t, material, hint=(0.0, 0.0, 1.0))
    leg_b = _beam(f"{name}-b", p0, p1, t, leg, material, hint=(0.0, 0.0, 1.0))
    return _combine(name, [leg_a, _move(leg_b, (0.0, 0.0, leg / 2 - t / 2 if z >= 0 else -(leg / 2 - t / 2)))], material)


def _truss(rng: random.Random) -> g.Assembly:
    span, rise = 8.0, 2.4
    members: list[g.MeshData] = []

    def top(x):
        return rise * (1 - x / span)

    for side, z in (("l", 0.045), ("r", -0.045)):  # chords are back-to-back double angles
        members.append(_angle(f"bottom-chord-{side}", (0.0, 0.0), (7.6, 0.0), z))
        members.append(_angle(f"top-chord-{side}", (0.0, rise), (7.0, top(7.0)), z))
    members.append(_angle("end-post", (0.0, 0.0), (0.0, rise), 0.0))
    xs = [1.6, 3.2, 4.8, 6.4]
    prev = 0.0
    for k, x in enumerate(xs):
        members.append(_angle(f"vertical-{k}", (x, 0.0), (x, top(x)), 0.0))
        if k % 2 == 0:
            members.append(_angle(f"diagonal-{k}", (prev, top(prev)), (x, 0.0), 0.0))
        else:
            members.append(_angle(f"diagonal-{k}", (prev, 0.0), (x, top(x)), 0.0))
        prev = x
    for k, x in enumerate([0.0, *xs]):
        members.append(g.box(f"gusset-{k}", (x, 0.08, 0.0), (0.34, 0.26, 0.01), "rust_dark"))
        members.append(g.box(f"gusset-top-{k}", (x, top(x) - 0.08, 0.0), (0.3, 0.24, 0.01), "rust_dark"))
    # Glazing mullions left in the tall end, and purlin stubs on the top chord.
    for k, y in enumerate((0.6, 1.2, 1.8)):
        members.append(g.box(f"mullion-{k}", (0.0, y, 0.25), (0.04, 0.04, 0.5 + 0.2 * k), "steel_dark"))
    for k, x in enumerate((0.8, 2.4, 5.6, 6.8)):
        ln = rng.uniform(0.4, 1.3)
        members.append(g.box(f"purlin-{k}", (x, top(x) + 0.09, ln / 2 - 0.1), (0.05, 0.15, ln), "rust"))
    # Two corrugated sheet remnants still hanging on the purlins.
    for k, (x0, w) in enumerate(((0.6, 1.3), (5.2, 1.0))):
        waves = 12
        length = 1.2

        def node(i, j, kk, x0=x0, w=w):
            s = i / waves
            xx = x0 + w * s
            yy = top(xx) + 0.17 + 0.018 * math.sin(s * waves * math.pi) + 0.004 * kk
            return (xx, yy, -0.1 + j * length)
        sheet = _cells(f"sheet-{k}", node, waves, 1, lambda i, j: True, "corrugated_rust")
        members.append(sheet)
    local = _combine("truss", [m for m in members if m.material == "rust"], "rust")
    parts = [local] + [m for m in members if m.material != "rust"]
    placed = [g.transformed_xyz(m, math.radians(15.0), 0.0, 0.0, (-1.5, FLOOR_TOP + 0.04, 3.6), f"truss-{m.name}") for m in parts]
    # The rubble it leans on.
    rest = g.beveled_box("rest-block", (0, 0, 0), (1.3, 1.2, 0.9), 0.06, "concrete_raw")
    placed.append(g.transformed_xyz(rest, 0.05, 0.12, -0.04, (2.2, FLOOR_TOP + 0.55, 4.45), "truss-rest-block"))
    rest2 = g.beveled_box("rest-block-2", (0, 0, 0), (0.8, 0.5, 0.7), 0.05, "concrete_raw")
    placed.append(g.transformed_xyz(rest2, 0.2, 0.5, 0.1, (3.2, FLOOR_TOP + 0.2, 4.2), "truss-rest-block-2"))
    return g.Assembly("plaza-truss", "plaza-truss", "plaza", (0.0, 0.0, 0.0), placed)


# --------------------------------------------------------------------------- machines


def _press(x: float, z: float, yaw: float, rng: random.Random) -> g.Assembly:
    y0 = FLOOR_TOP + 0.35
    L: list[g.MeshData] = []
    L.append(g.beveled_box("press-bed", (0, y0 + 0.45, 0), (2.8, 0.9, 1.8), 0.06, "paint_teal_faded"))
    L.append(g.box("press-bolster", (0, y0 + 0.96, 0), (2.2, 0.12, 1.4), "steel_dark"))
    for s in (-1, 1):
        L.append(g.beveled_box(f"press-upright-{s}", (s * 1.15, y0 + 0.9 + 1.3, 0), (0.55, 2.6, 1.5), 0.05, "paint_teal_faded"))
        L.append(g.box(f"press-upright-rust-{s}", (s * 1.15, y0 + 1.25, 0), (0.57, 0.5, 1.52), "rust"))
        for r in (-0.5, 0.5):
            L.append(g.cylinder(f"press-tierod-{s}-{r}", (s * 1.5, y0 + 2.3, r), 0.06, 4.6, 10, "steel_bare"))
            L.append(g.cylinder(f"press-tienut-{s}-{r}", (s * 1.5, y0 + 4.56, r), 0.1, 0.12, 6, "steel_dark"))
    L.append(g.beveled_box("press-crown", (0, y0 + 3.5 + 0.5, 0), (3.1, 1.0, 1.9), 0.07, "paint_teal_faded"))
    L.append(g.cylinder("press-cylinder", (0, y0 + 4.85, 0), 0.36, 0.7, 20, "steel_dark"))
    L.append(g.cylinder("press-cylinder-flange", (0, y0 + 4.54, 0), 0.46, 0.08, 20, "rust_dark"))
    L.append(g.beveled_box("press-ram", (0, y0 + 2.35, 0), (1.7, 0.7, 1.3), 0.04, "steel_dark"))
    L.append(g.box("press-ram-die", (0, y0 + 1.95, 0), (1.3, 0.1, 1.0), "rust"))
    # Flywheel with a hub and belt guard on the +X side.
    L.append(g.cylinder("press-flywheel", (1.75, y0 + 3.3, 0.2), 0.78, 0.22, 28, "rust_dark", axis="X"))
    L.append(g.cylinder("press-hub", (1.75, y0 + 3.3, 0.2), 0.16, 0.36, 12, "steel_dark", axis="X"))
    L.append(_block("press-guard", 1.95, 1.99, -0.7, 1.1, y0 + 2.4, [y0 + 4.1] * 4, "paint_yellow_faded"))
    # Motor on the crown, control box with a hanging door, hydraulic lines.
    L.append(g.cylinder("press-motor", (-0.7, y0 + 4.78, -0.55), 0.26, 0.8, 16, "paint_teal_faded", axis="X"))
    L.append(g.box("press-motor-foot", (-0.7, y0 + 4.56, -0.55), (0.6, 0.12, 0.4), "steel_dark"))
    L.append(g.box("press-control-box", (-1.15, y0 + 2.0, 0.95), (0.5, 0.8, 0.3), "paint_yellow_faded"))
    door = g.box("press-control-door", (0.25, 0.0, 0.0), (0.5, 0.78, 0.02), "paint_yellow_faded")
    L.append(g.transformed_xyz(door, 0.0, math.radians(-110), math.radians(-8), (-1.4, y0 + 2.0, 1.12)))
    L.append(g.tube("press-hose-a", [(0.3, y0 + 4.7, -0.35), (0.9, y0 + 4.5, -0.9), (1.35, y0 + 3.2, -0.95), (1.4, y0 + 1.2, -0.95)], 0.035, 6, "rubber"))
    L.append(g.tube("press-hose-b", [(-0.3, y0 + 4.7, -0.35), (-0.8, y0 + 4.4, -1.0), (-1.2, y0 + 1.0, -1.0), (-1.3, FLOOR_TOP + 0.06, -1.6)], 0.03, 6, "rubber"))
    # Stiffening ribs on the uprights and the crown (layered, cast-steel look) and a crown handrail.
    for s in (-1, 1):
        for zf in (-1, 1):
            for dx in (-0.14, 0.14):
                L.append(g.box(f"press-rib-{s}-{zf}-{dx}", (s * 1.15 + dx, y0 + 2.2, zf * 0.79), (0.06, 2.5, 0.08), "paint_teal_faded"))
    for zf in (-1, 1):
        for rx in (-1.2, -0.6, 0.0, 0.6, 1.2):
            L.append(g.box(f"press-crown-rib-{zf}-{rx}", (rx, y0 + 4.0, zf * 0.99), (0.07, 0.94, 0.08), "paint_teal_faded"))
        L.append(g.box(f"press-crown-band-{zf}", (0.0, y0 + 3.62, zf * 0.99), (3.0, 0.12, 0.1), "rust_dark"))
    rail_pts = [(-1.45, -0.85), (1.45, -0.85), (1.45, 0.85), (-1.45, 0.85)]
    for k, (px, pz) in enumerate(rail_pts):
        L.append(g.pipe(f"press-rail-post-{k}", (px, y0 + 4.5, pz), (px, y0 + 5.5, pz), 0.025, "paint_yellow_faded", 6))
    for k in range(3):  # one side of the handrail is gone
        a, b2 = rail_pts[k], rail_pts[k + 1]
        L.append(g.pipe(f"press-rail-{k}", (a[0], y0 + 5.45, a[1]), (b2[0], y0 + 5.45, b2[1]), 0.022, "paint_yellow_faded", 6))
    L.append(g.box("press-nameplate", (0.0, y0 + 0.55, 0.905), (0.5, 0.22, 0.01), "steel_bare"))
    # Guard panel that fell off and leans on the bed.
    panel = _block("press-fallen-guard", -0.6, 0.6, -0.01, 0.01, 0.0, [0.9] * 4, "paint_yellow_faded")
    L.append(g.transformed_xyz(panel, math.radians(-28), 0.0, 0.0, (-0.2, FLOOR_TOP + 0.36, -1.45)))
    parts = [g.transformed(m, math.radians(yaw), (x, 0.0, z)) for m in L]
    sprays = [Spray((x, y0 + 0.3, z), 2.2, (0.5, 0.45, 0.4), 0.7),                      # grime at the foot
              Spray((x + 0.3, y0 + 4.5, z - 0.95), 0.9, (0.3, 0.27, 0.24), 0.8),       # hydraulic oil leak
              Spray((x + 0.3, y0 + 3.4, z - 0.95), 0.8, (0.35, 0.3, 0.26), 0.7),
              Spray((x - 1.15, y0 + 1.3, z + 0.8), 0.9, (1.15, 0.6, 0.35), 0.7),        # rust bleeding through paint
              Spray((x + 1.15, y0 + 1.0, z - 0.8), 0.9, (1.15, 0.6, 0.35), 0.7),
              Spray((x, y0 + 5.0, z), 1.6, (0.62, 0.6, 0.56), 0.6)]                     # dust on the crown
    return g.Assembly("plaza-press", "plaza-press", "plaza", (0.0, 0.0, 0.0), parts, meta={"sprays": sprays})


def _conveyor(x: float, z: float, yaw: float, rng: random.Random) -> g.Assembly:
    L: list[g.MeshData] = []
    y_top = 0.95
    ex = -1.2  # stringers collapse west of this point
    collapsed_y = 0.3
    for s in (-1, 1):
        L.append(_beam(f"stringer-{s}", (ex, y_top, s * 0.45), (3.0, y_top, s * 0.45), 0.2, 0.05, "rust", hint=(0.0, 1.0, 0.0)))
        L.append(_beam(f"stringer-fallen-{s}", (-3.0, collapsed_y, s * 0.45), (ex, y_top, s * 0.45), 0.2, 0.05, "rust", hint=(0.0, 1.0, 0.0)))
        for k, lx in enumerate((-0.5, 1.2, 2.8)):
            L.append(g.box(f"leg-{s}-{k}", (lx, (FLOOR_TOP + y_top - 0.1) / 2, s * 0.47), (0.06, y_top - 0.1 - FLOOR_TOP, 0.06), "steel_dark"))
            L.append(g.box(f"leg-foot-{s}-{k}", (lx, FLOOR_TOP + 0.005, s * 0.47), (0.16, 0.01, 0.16), "steel_dark"))
        L.append(_beam(f"leg-bent-{s}", (-2.0, FLOOR_TOP + 0.04, s * 0.47 + 0.1), (-1.2, 0.35, s * 0.6), 0.06, 0.06, "steel_dark"))
    for k, lx in enumerate((-0.5, 1.2, 2.8)):
        L.append(_beam(f"brace-{k}", (lx, 0.3, -0.45), (lx, 0.8, 0.45), 0.04, 0.04, "steel_dark", hint=(1.0, 0.0, 0.0)))
    # Rollers (some missing), along the level run and the collapsed run.
    k = 0
    lx = -2.8
    while lx < 2.9:
        if k % 5 != 3:
            y = y_top + 0.05 if lx >= ex else collapsed_y + (y_top - collapsed_y) * (lx + 3.0) / (ex + 3.0) + 0.05
            L.append(g.cylinder(f"roller-{k}", (lx, y, 0.0), 0.055, 0.86, 8, "steel_bare", axis="Z"))
        lx += 0.35
        k += 1
    L.append(g.cylinder("drive-drum", (3.0, y_top + 0.02, 0.0), 0.16, 0.9, 16, "steel_dark", axis="Z"))
    L.append(g.beveled_box("gearbox", (3.05, y_top - 0.25, 0.75), (0.45, 0.4, 0.4), 0.03, "paint_teal_faded"))
    L.append(g.cylinder("motor", (3.05, y_top - 0.25, 1.15), 0.18, 0.45, 14, "paint_teal_faded", axis="Z"))
    # Belt: lies on the level rollers, then droops off the end to the floor.
    belt_pts = [(2.95, y_top + 0.115, 0.0), (1.5, y_top + 0.115, 0.0), (0.2, y_top + 0.115, 0.0), (-0.25, y_top - 0.05, 0.0),
                (-0.55, 0.45, 0.0), (-0.7, FLOOR_TOP + 0.05, 0.0), (-1.5, FLOOR_TOP + 0.01, 0.0)]
    across = [(0.0, 0.0, 1.0)] * len(belt_pts)
    normals = []
    for i in range(len(belt_pts)):
        a, b = belt_pts[max(i - 1, 0)], belt_pts[min(i + 1, len(belt_pts) - 1)]
        t = _norm(_sub(b, a))
        normals.append(_norm(_cross((0.0, 0.0, 1.0), t)))
    L.append(_sweep("belt", belt_pts, across, normals, 0.8, 0.012, "rubber"))
    parts = [g.transformed(m, math.radians(yaw), (x, 0.0, z), f"conveyor-{m.name}") for m in L]
    return g.Assembly("plaza-conveyor", "plaza-conveyor", "plaza", (0.0, 0.0, 0.0), parts)


def _tank(x: float, z: float, yaw: float, rng: random.Random) -> g.Assembly:
    # Kept low (cradled right on its base) so it does not hide the second lettering row from the plaza.
    r, length, t = 0.78, 4.0, 0.012
    seg = 32
    base_top = FLOOR_TOP + 0.3
    axis_y = base_top + 0.06 + r
    zs = [-length / 2 + length * j / 16 for j in range(17)]
    hole = {(i, j) for i in range(12, 16) for j in range(6, 10)} | {(12, 10), (15, 5), (13, 5)}  # upper west side
    jitter: dict[tuple[int, int], tuple[float, float, float]] = {}

    def on_rim(i, j):
        return any(((i + di) % seg, j + dj) in hole for di in (-1, 0) for dj in (-1, 0)) and \
            not all(((i + di) % seg, j + dj) in hole for di in (-1, 0) for dj in (-1, 0))

    def node(i, j, k):
        a = math.tau * i / seg
        rr = r - t * (1 - k)
        da = dz = dr = 0.0
        if on_rim(i, j):
            da, dz, dr = jitter.setdefault((i, j), (rng.uniform(-0.05, 0.05), rng.uniform(-0.06, 0.06), rng.uniform(0.04, 0.16)))
        return ((rr + dr) * math.cos(a + da), (rr + dr) * math.sin(a + da), zs[j] + dz)

    L: list[g.MeshData] = []
    L.append(_cells("tank-shell", node, seg, 16, lambda i, j: (i, j) not in hole, "rust", periodic=True))
    head = [(0.0, 0.26), (0.31, 0.235), (0.54, 0.165), (0.71, 0.07), (r - 0.002, 0.0), (r - 0.002, -0.06), (0.0, -0.06)]
    for s in (-1, 1):
        h = _revolve(f"tank-head-{s}", head, seg, "rust_dark")
        L.append(_frame(h, (0.0, 0.0, s * (length / 2 - 0.02)), (0.0, 0.0, float(s)), (1.0, 0.0, 0.0)))
    for s, zz in enumerate((-1.25, 1.5)):
        seam = _revolve(f"tank-seam-{s}", [(r, -0.02), (r + 0.012, -0.02), (r + 0.012, 0.02), (r, 0.02)], seg, "rust_dark", loop=True)
        L.append(_frame(seam, (0.0, 0.0, zz), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)))
    # Nozzles: a flanged stub on the bottom head and a snapped pipe on top.
    L.append(g.cylinder("tank-nozzle", (0.0, -0.4, length / 2 + 0.3), 0.08, 0.35, 10, "rust_dark", axis="Z"))
    L.append(g.cylinder("tank-nozzle-flange", (0.0, -0.4, length / 2 + 0.47), 0.14, 0.03, 10, "rust_dark", axis="Z"))
    L.append(g.tube("tank-riser", [(0.2, r - 0.05, 0.9), (0.2, r + 0.5, 0.9), (0.45, r + 0.62, 1.05)], 0.05, 8, "rust_dark"))
    # Manway neck on top; its cover slid off and lies on the floor.
    L.append(g.cylinder("tank-manway", (0.0, r + 0.1, -0.6), 0.28, 0.3, 16, "rust_dark", axis="Y"))
    L.append(g.cylinder("tank-manway-flange", (0.0, r + 0.25, -0.6), 0.34, 0.03, 16, "rust_dark", axis="Y"))
    tank_parts = [g.transformed(g.transformed(m, 0.0, (0.0, axis_y, 0.0)), math.radians(yaw), (x, 0.0, z)) for m in L]
    tank_parts.append(g.transformed_xyz(g.cylinder("tank-manway-cover", (0, 0, 0), 0.34, 0.03, 16, "rust_dark"),
                                        0.08, 0.0, 0.12, (x - 1.55, FLOOR_TOP + 0.06, z - 1.2)))
    # Saddles on the base, and a ladder that fell against the tank.
    for s, zz in enumerate((-1.2, 1.1)):
        z0, z1 = z + zz - 0.12, z + zz + 0.12
        low = axis_y - math.sqrt(r * r - 0.2 ** 2) - 0.005
        high = axis_y - math.sqrt(r * r - 0.75 ** 2) - 0.02
        tank_parts.append(_block(f"tank-saddle-{s}-a", x - 0.75, x - 0.2, z0, z1, base_top, [high, low, low, high], "steel_dark"))
        tank_parts.append(_block(f"tank-saddle-{s}-b", x + 0.2, x + 0.75, z0, z1, base_top, [low, high, high, low], "steel_dark"))
        tank_parts.append(g.box(f"tank-saddle-{s}-c", (x, (base_top + axis_y - r - 0.005) / 2, z + zz), (0.42, axis_y - r - 0.005 - base_top, 0.24), "steel_dark"))
        tank_parts.append(g.box(f"tank-saddle-pad-{s}", (x, base_top + 0.015, z + zz), (1.7, 0.03, 0.34), "steel_dark"))
    rails = []
    foot = (x - 1.75, FLOOR_TOP, z - 0.1)
    rest_y = axis_y + 0.45
    contact = (x - math.sqrt(r * r - (rest_y - axis_y) ** 2) - 0.04, rest_y, z - 0.1)
    lean = _norm(_sub(contact, foot))
    ladder_len = math.dist(contact, foot)
    for s in (-0.22, 0.22):
        rails.append(_beam(f"ladder-rail-{s}", _add(foot, (0.0, 0.0, s)), _add(contact, (0.0, 0.0, s)), 0.05, 0.05, "steel_dark"))
    for k in range(int((ladder_len - 0.3) / 0.3)):
        p = _add(foot, _mul(lean, 0.25 + 0.3 * k))
        rails.append(_beam(f"ladder-rung-{k}", (p[0], p[1], p[2] - 0.22), (p[0], p[1], p[2] + 0.22), 0.025, 0.025, "steel_dark",
                           hint=(1.0, 0.0, 0.0)))
    tank_parts.append(_combine("tank-ladder", rails, "steel_dark"))
    sprays = [Spray((x, axis_y, z), 3.2, (0.55, 0.52, 0.5), 0.6),                       # weathered overall
              Spray((x, axis_y - r, z), 1.6, (0.45, 0.42, 0.38), 0.7),                  # grime and splash at the bottom
              Spray((x - 0.6, axis_y + 0.5, z + 0.3), 0.7, (0.35, 0.3, 0.27), 0.75),     # dark stain around the tear
              Spray((x + 0.2, axis_y + r, z + 0.9), 0.8, (0.5, 0.42, 0.35), 0.6),
              Spray((x, axis_y + r, z - 1.8), 1.2, (0.6, 0.57, 0.52), 0.5)]
    return g.Assembly("plaza-tank", "plaza-tank", "plaza", (0.0, 0.0, 0.0), tank_parts, meta={"sprays": sprays})


# --------------------------------------------------------------------------- car + fire barrel


def _car(x: float, z: float, yaw: float) -> g.Assembly:
    L: list[g.MeshData] = []
    body_y = 0.27 + 0.35
    L.append(g.beveled_box("car-body", (0.0, body_y, 0.0), (4.2, 0.7, 1.8), 0.08, "rust_dark"))
    yb, yt = body_y + 0.35, body_y + 0.83
    # Cabin: glassless trapezoid made of roof + pillars, so the burnt interior shows.
    L.append(_hexa("car-roof", ((-0.58, yt - 0.05, -0.7), (0.62, yt - 0.05, -0.7), (0.6, yt, -0.68), (-0.55, yt, -0.68),
                                (-0.58, yt - 0.05, 0.7), (0.62, yt - 0.05, 0.7), (0.6, yt, 0.68), (-0.55, yt, 0.68)), "rust_dark"))
    for s in (-1, 1):
        for k, (bx, tx) in enumerate(((1.1, 0.6), (0.05, 0.02), (-1.0, -0.55))):
            L.append(_beam(f"car-pillar-{s}-{k}", (bx, yb - 0.02, s * 0.8), (tx, yt - 0.03, s * 0.66), 0.08, 0.06, "rust_dark",
                           hint=(1.0, 0.0, 0.0)))
    L.append(g.box("car-dash", (0.85, yb + 0.12, 0.0), (0.35, 0.25, 1.5), "rust_dark"))
    L.append(g.tube("car-steering", [(0.62, yb + 0.28 + 0.16 * math.sin(a), 0.4 + 0.16 * math.cos(a)) for a in
                                      [math.tau * s / 10 for s in range(11)]], 0.015, 4, "steel_dark"))
    for s in (-0.4, 0.4):
        L.append(g.box(f"car-seat-{s}", (0.1, yb + 0.12, s), (0.5, 0.06, 0.48), "steel_dark"))
        L.append(_beam(f"car-seatback-{s}", (-0.15, yb + 0.1, s), (-0.28, yb + 0.62, s), 0.05, 0.46, "steel_dark", hint=(1.0, 0.0, 0.0)))
    L.append(g.box("car-rear-seat", (-0.72, yb + 0.12, 0.0), (0.45, 0.06, 1.4), "steel_dark"))
    # Rims only (tyres burnt away): the car sits on them.
    for sx in (-1.35, 1.35):
        for sz in (-0.84, 0.84):
            L.append(g.cylinder(f"car-rim-{sx}-{sz}", (sx, 0.3, sz), 0.3, 0.18, 16, "steel_dark", axis="Z"))
            L.append(g.cylinder(f"car-hub-{sx}-{sz}", (sx, 0.3, sz * 1.08), 0.1, 0.06, 8, "rust_dark", axis="Z"))
    L.append(g.box("car-bumper-front", (2.14, 0.45, 0.0), (0.1, 0.16, 1.7), "steel_dark"))
    L.append(g.box("car-plate", (2.2, 0.45, 0.0), (0.02, 0.12, 0.34), "steel_bare"))
    for sz in (-0.6, 0.6):
        L.append(g.cylinder(f"car-lamp-{sz}", (2.1, 0.72, sz), 0.1, 0.04, 10, "steel_dark", axis="X"))
    L.append(g.box("car-hood-seam", (1.5, body_y + 0.352, 0.0), (0.02, 0.006, 1.5), "steel_dark"))
    L.append(g.box("car-trunk-seam", (-1.6, body_y + 0.352, 0.0), (0.02, 0.006, 1.5), "steel_dark"))
    for s in (-1, 1):
        L.append(g.box(f"car-door-seam-{s}", (0.05, body_y, s * 0.902), (0.02, 0.5, 0.006), "steel_dark"))
    # The shell lists 5 deg towards +Z: the burnt springs on that side sagged, the other side hangs at
    # full droop. Lift the car until the low-side rims just bite into the floor, then drop each
    # high-side wheel (rim + hub) straight down onto the floor as well.
    rest = FLOOR_TOP - 0.015
    parts = [g.transformed_xyz(m, math.radians(5.0), math.radians(yaw), 0.0, (x, 0.0, z)) for m in L]
    def low_y(m: g.MeshData) -> float:
        return min(v[1] for v in m.vertices)
    lift = rest - min(low_y(m) for m in parts if m.name.startswith("car-rim-"))
    parts = [g.transformed(m, 0.0, (0.0, lift, 0.0)) for m in parts]
    drop = {m.name[len("car-rim-"):]: low_y(m) - rest for m in parts if m.name.startswith("car-rim-")}
    parts = [g.transformed(m, 0.0, (0.0, -drop.get(m.name.split("-", 2)[-1], 0.0), 0.0))
             if m.name.startswith(("car-rim-", "car-hub-")) else m for m in parts]
    bumper = g.box("car-bumper-rear", (0, 0, 0), (0.16, 0.1, 1.7), "steel_dark")  # fell off, lying flat
    rear = g.rotate_y((-2.6, 0.0, 0.5), math.radians(yaw))
    parts.append(g.transformed_xyz(bumper, 0.06, math.radians(yaw + 35), 0.0, (x + rear[0], FLOOR_TOP + 0.05, z + rear[2])))
    # Burnt out: soot everywhere, heaviest over the engine bay and cabin; grey ash on the roof.
    def at(lx, ly, lz):
        p = g.rotate_y((lx, ly, lz), math.radians(yaw))
        return (x + p[0], FLOOR_TOP + p[1], z + p[2])
    sprays = [Spray(at(0.0, 0.8, 0.0), 3.6, (0.35, 0.33, 0.31), 0.75),   # the whole shell is scorched (few vertices)
              Spray(at(1.4, 0.9, 0.0), 1.5, (0.2, 0.19, 0.18), 0.9), Spray(at(0.0, 1.2, 0.0), 1.6, (0.22, 0.2, 0.19), 0.85),
              Spray(at(-1.5, 0.8, 0.0), 1.3, (0.3, 0.28, 0.26), 0.7), Spray(at(0.0, 1.6, 0.0), 0.6, (1.6, 1.5, 1.4), 0.5),
              Spray(at(1.6, 1.0, 0.5), 0.5, (1.5, 1.45, 1.35), 0.45)]
    return g.Assembly("plaza-car", "plaza-car", "plaza", (0.0, 0.0, 0.0), parts, meta={"sprays": sprays})


def _fire_barrel(x: float, z: float, rng: random.Random) -> g.Assembly:
    seg, r, t = 20, 0.29, 0.012
    ys = [0.0, 0.12, 0.2, 0.3, 0.44, 0.58, 0.72, 0.88]
    tops = {i: rng.uniform(-0.025, 0.0) for i in range(seg)}

    def node(i, j, k):
        a = math.tau * i / seg
        rr = r - t * (1 - k)
        y = ys[j] + (tops[i] if j == len(ys) - 1 else 0.0)
        return (rr * math.cos(a), FLOOR_TOP + y, rr * math.sin(a))

    L: list[g.MeshData] = []
    L.append(_cells("drum-shell", node, seg, len(ys) - 1, lambda i, j: not (j == 1 and i % 3 == 0), "rust_dark", periodic=True))
    L.append(g.cylinder("drum-bottom", (0.0, FLOOR_TOP + 0.01, 0.0), r - 0.013, 0.02, seg, "rust_dark"))
    for k, y in enumerate((0.3, 0.58)):
        rib = _revolve(f"drum-rib-{k}", [(r, -0.012), (r + 0.012, -0.012), (r + 0.012, 0.012), (r, 0.012)], seg, "rust_dark", loop=True)
        L.append(_move(rib, (0.0, FLOOR_TOP + y, 0.0)))
    L.append(g.cylinder("embers", (0.0, FLOOR_TOP + 0.7, 0.0), r - 0.02, 0.04, seg, "neon_orange"))
    for k in range(5):
        a = rng.uniform(0, math.tau)
        coal = g.beveled_box(f"coal-{k}", (0, 0, 0), (0.09, 0.05, 0.07), 0.015, "neon_orange")
        L.append(g.transformed_xyz(coal, rng.uniform(-0.4, 0.4), a, 0.0, (0.12 * math.cos(a), FLOOR_TOP + 0.74, 0.12 * math.sin(a))))
    # Charred sticks poking out of the drum, and scrap wood / seats around it.
    for k in range(4):
        a = math.tau * k / 4 + rng.uniform(-0.3, 0.3)
        p0 = (0.08 * math.cos(a), FLOOR_TOP + 0.72, 0.08 * math.sin(a))
        p1 = (0.36 * math.cos(a), FLOOR_TOP + 1.05 + rng.uniform(0, 0.12), 0.36 * math.sin(a))
        L.append(_beam(f"stick-{k}", p0, p1, 0.05, 0.035, "pallet_wood", hint=(0.0, 1.0, 0.0)))
    for k in range(7):
        a = rng.uniform(0, math.tau)
        rad = rng.uniform(0.55, 1.3)
        ln = rng.uniform(0.4, 1.1)
        plank = g.box(f"plank-{k}", (0, 0, 0), (ln, 0.025, rng.uniform(0.08, 0.14)), "pallet_wood" if k % 2 else "plywood")
        L.append(g.transformed_xyz(plank, rng.uniform(-0.1, 0.1), rng.uniform(0, math.pi), rng.uniform(-0.12, 0.12),
                                   (rad * math.cos(a), FLOOR_TOP + 0.02 + 0.03 * (k % 3), rad * math.sin(a))))
    for k, (dx, dz) in enumerate(((1.1, 0.4), (-0.5, -1.0))):
        L.append(g.beveled_box(f"seat-block-{k}", (dx, FLOOR_TOP + 0.1, dz), (0.39, 0.19, 0.19), 0.015, "concrete_raw"))
        L.append(g.beveled_box(f"seat-block-top-{k}", (dx, FLOOR_TOP + 0.29, dz), (0.39, 0.19, 0.19), 0.015, "concrete_raw"))
    crate = g.beveled_box("seat-crate", (0, 0, 0), (0.5, 0.32, 0.36), 0.02, "plastic_crate")
    L.append(g.transformed_xyz(crate, 0.0, 0.4, 0.0, (-0.9, FLOOR_TOP + 0.16, 0.7)))
    parts = [_move(m, (x, 0.0, z)) for m in L]
    sprays = [Spray((x, FLOOR_TOP + 0.95, z), 0.9, (0.18, 0.17, 0.16), 0.95),      # charred sticks and sooty drum lip
              Spray((x, FLOOR_TOP + 0.75, z), 0.45, (0.3, 0.27, 0.25), 0.8),
              Spray((x, FLOOR_TOP, z), 1.4, (0.45, 0.42, 0.4), 0.7)]               # ash-stained scrap around it
    return g.Assembly("plaza-fire-barrel", "plaza-fire-barrel", "plaza", (0.0, 0.0, 0.0), parts,
                      meta={"sprays": sprays, "light": {"position": [x, FLOOR_TOP + 1.2, z], "color": [1.0, 0.55, 0.2]}})


# --------------------------------------------------------------------------- perimeter


def _perimeter(data: dict[str, Any], rng: random.Random) -> g.Assembly:
    exits = [tuple(e) for e in data["plaza_features"]["exits"]]
    edge = 9.8
    runs: list[tuple[str, float, float, float]] = []  # (axis along, fixed coordinate, lo, hi)
    for axis, fixed, lo, hi in (("x", edge, -10.0, 9.2), ("x", -edge, -10.0, 9.2), ("z", -edge, -10.0, 10.0)):
        cuts = sorted((e[0], e[2]) if axis == "x" else (e[1], e[3]) for e in exits
                      if (axis == "x" and e[1] < fixed < e[3]) or (axis == "z" and e[0] < fixed < e[2]))
        a = lo
        for c0, c1 in cuts:
            runs.append((axis, fixed, a, c0 - 0.15))
            a = c1 + 0.15
        runs.append((axis, fixed, a, hi))
    parts: list[g.MeshData] = []
    thick = 0.2
    for k, (axis, fixed, lo, hi) in enumerate(runs):
        n = max(2, int(round((hi - lo) / 0.4)))
        ts = [lo + (hi - lo) * i / n for i in range(n + 1)]
        h, heights = rng.uniform(0.8, 1.6), []
        for i in range(n + 1):
            h += rng.uniform(-0.25, 0.25)
            if rng.random() < 0.08:
                h -= rng.uniform(0.3, 0.6)  # a knocked-out chunk
            h = min(1.8, max(0.6, h))
            heights.append(h)

        def node(i, j, kk, ts=ts, heights=heights, axis=axis, fixed=fixed):
            y = (FLOOR_TOP - 0.05, FLOOR_TOP + heights[i])[j]
            c = fixed + (kk - 0.5) * thick
            return (ts[i], y, c) if axis == "x" else (c, y, ts[i])
        parts.append(_cells(f"wall-run-{k}", node, n, 1, lambda i, j: True, "concrete_stained"))
        # Piers and fence posts every ~2.5 m; a top rail between posts that are still standing.
        m = max(1, int(round((hi - lo) / 2.5)))
        posts = []
        for i in range(m + 1):
            t = lo + 0.12 + (hi - lo - 0.24) * i / m
            px, pz = (t, fixed) if axis == "x" else (fixed, t)
            pier_h = min(1.9, max(heights) + 0.1)
            parts.append(g.beveled_box(f"pier-{k}-{i}", (px, (FLOOR_TOP - 0.05 + FLOOR_TOP + pier_h) / 2, pz),
                                       (0.3, pier_h + 0.05, 0.3), 0.02, "concrete_raw"))
            lean = rng.uniform(-0.2, 0.2) if rng.random() < 0.35 else 0.0
            top_y = FLOOR_TOP + 2.4
            top = (px + (lean if axis == "z" else 0.0), top_y, pz + (lean if axis == "x" else 0.0))
            parts.append(g.pipe(f"post-{k}-{i}", (px, FLOOR_TOP + pier_h, pz), top, 0.03, "steel_dark", 8))
            parts.append(g.cylinder(f"post-cap-{k}-{i}", (top[0], top_y + 0.02, top[2]), 0.04, 0.04, 8, "steel_dark"))
            posts.append(top)
        for i in range(m):
            if rng.random() < 0.3:
                continue  # rail missing
            a0, a1 = posts[i], posts[i + 1]
            parts.append(g.pipe(f"rail-{k}-{i}", (a0[0], a0[1] - 0.06, a0[2]), (a1[0], a1[1] - 0.06, a1[2]), 0.02, "steel_dark", 6))
            if rng.random() < 0.5:
                sag = [(p[0], p[1], p[2]) for p in g.catenary((a0[0], FLOOR_TOP + 1.95, a0[2]), (a1[0], FLOOR_TOP + 1.95, a1[2]), 0.25, 6)]
                parts.append(g.tube(f"wire-{k}-{i}", sag, 0.006, 3, "steel_dark"))
    # Splash-back grime along the foot and a few tags on the inner faces.
    sprays: list[Spray] = []
    for axis, fixed, lo, hi in runs:
        t = lo + 0.6
        while t < hi:
            p = (t, FLOOR_TOP + 0.1, fixed) if axis == "x" else (fixed, FLOOR_TOP + 0.1, t)
            sprays.append(Spray(p, 0.9, (0.55, 0.52, 0.48), 0.6))
            t += 1.2
    for k in range(5):
        axis, fixed, lo, hi = runs[k % len(runs)]
        t = rng.uniform(lo + 0.5, hi - 0.5)
        p = (t, FLOOR_TOP + 0.9, fixed) if axis == "x" else (fixed, FLOOR_TOP + 0.9, t)
        sprays.append(Spray(p, rng.uniform(0.4, 0.6), TAG_COLORS[k % 3], 0.4))
    return g.Assembly("plaza-perimeter", "plaza-perimeter", "plaza", (0.0, 0.0, 0.0), parts, meta={"sprays": sprays})


# --------------------------------------------------------------------------- sector


@register("plaza")
def plaza_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    feats = data["plaza_features"]
    machines = {m[3]: m for m in feats["machines"]}
    press, conveyor, tank = machines["press"], machines["conveyor"], machines["tank"]
    car = feats["car"]
    assemblies = [
        _floor(data, random.Random(SEED + 601)),
        _machine_bases(random.Random(SEED + 602)),
        _columns(data, random.Random(SEED + 603)),
        _crane_rail(data, random.Random(SEED + 604)),
        _truss(random.Random(SEED + 605)),
        _press(press[0], press[1], press[2], random.Random(SEED + 606)),
        _conveyor(conveyor[0], conveyor[1], conveyor[2], random.Random(SEED + 607)),
        _tank(tank[0], tank[1], tank[2], random.Random(SEED + 608)),
        _car(car[0], car[1], car[2]),
        _fire_barrel(feats["fire_barrel"][0], feats["fire_barrel"][1], random.Random(SEED + 609)),
        _perimeter(data, random.Random(SEED + 610)),
        _east_wall(random.Random(SEED + 611)),
    ]
    for a in assemblies:
        a.parts = [_planarize(p) for p in a.parts]
    return assemblies
