"""Derelict tower blocks (sectors ``towers-a`` / ``towers-b`` / ``towers-c``).

Each layout tower becomes one brutalist ruin: deep recessed window grids on
bays of ``BAY`` metres, protruding bay fins, floor-slab lips, a shadowed podium
entrance with a rusted shutter, cantilevered balconies, bolted-on corrugated
parasite boxes, external steel stairs, pipe scaffold, herds of AC units, corner
downspouts, roof clutter and, on half of them, a perpendicular neon strip sign.
``collapse`` floors from the layout lose the top corner on one side, leaving
torn slab edges with rebar and debris above the intact ``core_height``.

Pure Python and deterministic (``random.Random(spec["seed"])`` per tower).
Local frame: +Z faces the spec's ``front`` direction, local X lies across the
front; parts are baked into the spec yaw, so the assembly origin is just
``(cx, 0, cz)``. R11: every part is a closed outward shell except the facade
skins, which are open walls authored facing outward (both are asserted in
``tests/slum02/test_towers.py``). A dark ``core-void`` box fills the interior
so missing corners, entrances and broken windows never show see-through walls.
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any

from modeling.slum02 import geometry as g
from modeling.slum02.sectors import register
from modeling.slum02.vcolor import Spray

FLOOR_H = 3.2
BAY = 3.6
WALL_T = 0.5
RECESS = 0.3
PANE_DEPTH = 0.25
FIN_OUT = 0.35
FIN_W = 0.4
LIP_H = 0.3
CORE_INSET = 1.35       # interior shadow box; clears the 1.2 m entrance alcove
MAX_PROTRUDE = 1.5      # outer surface allowance incl. the +-4 deg inner-tower jitter

Vec = tuple[float, float, float]
TAG_COLORS = ((0.6, 1.0, 0.3), (0.3, 0.9, 1.0), (1.0, 0.3, 0.8), (0.95, 0.85, 0.25))
NEON_MATS = ("neon_magenta", "neon_cyan", "neon_lime", "neon_orange", "neon_pink", "neon_red")
PARASITE_MATS = ("corrugated", "corrugated_rust", "paint_teal_faded", "paint_yellow_faded")


# --------------------------------------------------------------------------- small mesh helpers (kept local; see plaza.py twins)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _norm(a):
    length = math.sqrt(_dot(a, a)) or 1.0
    return _mul(a, 1.0 / length)


def _face_normal(pts):
    nx = ny = nz = 0.0
    for a, b in zip(pts, (*pts[1:], pts[0])):
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / length, ny / length, nz / length)


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
    """Split non-planar polygons into triangles so metric UVs stay exact."""
    faces: list[tuple[int, ...]] = []
    changed = False
    for f in m.faces:
        if len(f) > 3:
            pts = [m.vertices[i] for i in f]
            n = _face_normal(pts)
            c = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
            if max(abs(_dot(_sub(p, c), n)) for p in pts) > tol:
                faces.extend((f[0], f[k], f[k + 1]) for k in range(1, len(f) - 1))
                changed = True
                continue
        faces.append(f)
    return g.MeshData(m.name, m.vertices, tuple(faces), m.material) if changed else m


def _combine(name: str, meshes: Sequence[g.MeshData], material: str | None = None) -> g.MeshData:
    verts: list[Vec] = []
    faces: list[tuple[int, ...]] = []
    for m in meshes:
        off = len(verts)
        verts.extend(m.vertices)
        faces.extend(tuple(off + i for i in f) for f in m.faces)
    return g.mesh(name, verts, faces, material or meshes[0].material)


def _fan_prism(name: str, ring: Sequence[tuple[float, float]], y0: float, y1: float, material: str) -> g.MeshData:
    """Closed prism over a star-shaped (x, z) outline; caps are fans around the centroid."""
    n = len(ring)
    cx, cz = sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n
    verts = [(x, y0, z) for x, z in ring] + [(x, y1, z) for x, z in ring] + [(cx, y0, cz), (cx, y1, cz)]
    bc, tc = 2 * n, 2 * n + 1
    faces = []
    for i in range(n):
        k = (i + 1) % n
        faces.append((bc, i, k))
        faces.append((tc, n + k, n + i))
        faces.append((i, n + i, n + k, k))
    return _outward(g.mesh(name, verts, faces, material))


def _basis(d: Vec, hint: Vec) -> tuple[Vec, Vec, Vec]:
    d = _norm(d)
    u = _sub(hint, _mul(d, _dot(hint, d)))
    if _dot(u, u) < 1e-10:
        alt = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 0.0, 1.0)
        u = _sub(alt, _mul(d, _dot(alt, d)))
    u = _norm(u)
    return u, d, _cross(u, d)   # right-handed: identity when u=X, d=Y


def _frame(m: g.MeshData, origin: Sequence[float], d: Vec, hint: Vec, name: str | None = None) -> g.MeshData:
    u, dd, w = _basis(d, hint)
    verts = tuple(tuple(origin[k] + p[0] * u[k] + p[1] * dd[k] + p[2] * w[k] for k in range(3)) for p in m.vertices)
    return g.MeshData(name or m.name, verts, m.faces, m.material)  # type: ignore[arg-type]


def _beam(name: str, p0: Vec, p1: Vec, su: float, sw: float, material: str, hint: Vec = (0.0, 0.0, 1.0)) -> g.MeshData:
    """Box beam between two points; ``su``/``sw`` are the section sizes, axis along p0->p1."""
    d = _sub(p1, p0)
    length = math.sqrt(_dot(d, d))
    return _frame(g.box(name, (0, length / 2, 0), (su, length, sw), material), p0, d, hint)


# --------------------------------------------------------------------------- layout helpers


def _local_dims(spec):
    w, d = spec["footprint"]
    return (w, d) if spec["front"] in ("+z", "-z") else (d, w)   # local X = across the front


def _bays(width: float) -> tuple[int, float]:
    bays = max(1, int(width // BAY))
    return bays, (width - bays * BAY) / 2


def _window_openings(width, height, floors, rng, *, first_floor_door=False):
    # The wall grid splits at every unique opening edge, so per-window jitter would blow
    # the tri budget: share one width per bay column and one height per floor row —
    # the elevation still reads varied, but the grid stays (2*bays)x(2*floors).
    bays, margin = _bays(width)
    col_w = [rng.uniform(1.0, 1.6) for _ in range(bays)]
    row_h = [rng.uniform(1.6, 2.0) for _ in range(floors)]
    ops = []
    for f in range(floors):
        y0 = f * FLOOR_H + 0.9
        if y0 + 2.0 > height - 0.3:
            break
        for b in range(bays):
            if first_floor_door and f == 0 and b == bays // 2:
                continue                      # entrance bay handled by podium-entrance
            ww, wh = col_w[b], row_h[f]
            cx = -width / 2 + margin + BAY * (b + 0.5)
            ops.append((round(cx - ww / 2, 3), round(y0, 3), round(cx + ww / 2, 3), round(y0 + wh, 3)))
    return ops


def _wall(name: str, width: float, height: float, openings, max_edge: float, material: str) -> g.MeshData:
    return g.wall_with_openings(name, width, height, WALL_T, openings, RECESS, max_edge, material, closed=False)


# Face placement: (yaw, offset) taking a wall built in the front frame (+Z out,
# x across, y 0..height) onto each side of the local box.
def _face_transform(side: str, hx: float, hz: float) -> tuple[float, Vec]:
    p = WALL_T / 2
    return {"front": (0.0, (0.0, 0.0, hz - p)),
            "back": (math.pi, (0.0, 0.0, -(hz - p))),
            "right": (math.pi / 2, (hx - p, 0.0, 0.0)),
            "left": (-math.pi / 2, (-(hx - p), 0.0, 0.0))}[side]


def _ragged_strip(name: str, x0: float, x1: float, z0: float, z1: float, y0: float,
                  thick: float, rng: random.Random, material: str) -> g.MeshData:
    """Torn slab band with a jittered outline (closed prism)."""
    ring = []
    n = 8
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        ring.append((x + rng.uniform(-0.12, 0.12), z0 + rng.uniform(-0.1, 0.1)))
    for i in range(n - 1, -1, -1):
        t = i / n
        x = x0 + (x1 - x0) * t
        ring.append((x + rng.uniform(-0.12, 0.12), z1 + rng.uniform(-0.1, 0.1)))
    return _fan_prism(name, ring, y0, y0 + thick, material)


def _chunk(name: str, size: Sequence[float], rng: random.Random, material: str) -> g.MeshData:
    """Small concrete lump: jittered box, loosely rotated."""
    m = g.box(name, (0.0, size[1] / 2, 0.0), size, material)
    return g.transformed_xyz(m, math.radians(rng.uniform(-8, 8)), rng.uniform(0, math.tau),
                             math.radians(rng.uniform(-8, 8)), (0.0, 0.0, 0.0))


# --------------------------------------------------------------------------- tower pieces


def _panes(openings, skip: set[int], yaw: float, offset: Vec, rng: random.Random,
           glass: list[g.MeshData], lit: list[g.MeshData], tag: str) -> None:
    """Window fills in the recess: 60 % dark glass, 6 % lit, rest stays a dark broken recess."""
    for i, (x0, y0, x1, y1) in enumerate(openings):
        if i in skip:
            continue
        roll = rng.random()
        if roll >= 0.66:
            continue
        inset = 0.05
        pane = g.box(f"pane-{tag}-{i}", ((x0 + x1) / 2, (y0 + y1) / 2, -PANE_DEPTH + WALL_T / 2),
                     (x1 - x0 - 2 * inset, y1 - y0 - 2 * inset, 0.04),
                     "window_lit" if roll >= 0.60 else "glass_dark")
        (lit if roll >= 0.60 else glass).append(g.transformed(pane, yaw, offset))


def _podium(parts: list[g.MeshData], hx: float, hz: float, door_cx: float,
            door_h: float, rng: random.Random) -> None:
    """Shadowed ground-floor entrance: 1.2 m deep alcove behind the facade opening plus a
    corrugated shutter, closed or rolled up over a dark gap."""
    back = hz - 1.2
    alcove = [
        g.box("al-back", (door_cx, door_h / 2, back + 0.04), (3.56, door_h, 0.08), "concrete_dark"),
        g.box("al-top", (door_cx, door_h + 0.04, (hz + back) / 2 - 0.05), (3.56, 0.08, hz - back - 0.1), "concrete_dark"),
        g.box("al-left", (door_cx - 1.76, door_h / 2, (hz + back) / 2 - 0.05), (0.08, door_h, hz - back - 0.1), "concrete_dark"),
        g.box("al-right", (door_cx + 1.76, door_h / 2, (hz + back) / 2 - 0.05), (0.08, door_h, hz - back - 0.1), "concrete_dark"),
    ]
    parts.append(_combine("podium-entrance", alcove, "concrete_dark"))
    gap = rng.uniform(0.0, 1.3)
    if gap < 0.3:
        gap = 0.0                                     # shutter fully down
    shutter_h = door_h - gap
    shutter = [g.box("sh-body", (door_cx, gap + shutter_h / 2, hz - 0.27), (3.5, shutter_h, 0.06), "corrugated_rust")]
    for i in range(4):
        y = gap + shutter_h * (i + 0.5) / 4
        shutter.append(g.box(f"sh-rib-{i}", (door_cx, y, hz - 0.235), (3.5, 0.06, 0.05), "corrugated_rust"))
    parts.append(_combine("podium-shutter", shutter, "corrugated_rust"))


def _balconies(parts: list[g.MeshData], w: float, hz: float, tarp_mats,
               intact_top: float, rng: random.Random) -> None:
    """Cantilevered front balconies: slab, parapet, struts; 30 % carry laundry, a sheet or an AC."""
    bays, margin = _bays(w)
    floors = int(intact_top // FLOOR_H)
    picks: list[tuple[int, int]] = []
    if floors < 2 or bays < 2:
        return
    count = rng.randint(1, min(3, floors - 1))
    for n in range(count):
        f = rng.randint(1, floors - 1)
        b = rng.randrange(bays)
        if (f, b) in picks:
            continue
        picks.append((f, b))
        bx = -w / 2 + margin + BAY * (b + 0.5)
        fy = f * FLOOR_H
        bw = min(BAY - 0.7, 3.0)
        z0 = hz - 0.02
        idx = len([p for p in parts if p.name.startswith("balcony")])
        parts.append(g.box(f"balcony-{idx}-slab", (bx, fy + 0.08, z0 + 0.6), (bw, 0.14, 1.2), "concrete_dark"))
        parts.append(g.box(f"balcony-{idx}-pf", (bx, fy + 0.14 + 0.5, z0 + 1.17), (bw, 1.0, 0.06), "concrete_dark"))
        for sgn in (-1.0, 1.0):
            parts.append(g.box(f"balcony-{idx}-ps{int(sgn)}", (bx + sgn * (bw / 2 - 0.03), fy + 0.64, z0 + 0.6),
                               (0.06, 1.0, 1.14), "concrete_dark"))
            parts.append(_beam(f"balcony-{idx}-strut{int(sgn)}", (bx + sgn * bw * 0.33, fy - 1.1, hz - 0.05),
                               (bx + sgn * bw * 0.33, fy + 0.02, z0 + 0.95), 0.07, 0.07, "steel_dark"))
        roll = rng.random()
        if roll < 0.12:    # laundry line + cloth
            parts.append(g.pipe(f"balcony-{idx}-line", (bx - bw / 2 + 0.12, fy + 1.02, z0 + 0.95),
                                (bx + bw / 2 - 0.12, fy + 1.02, z0 + 0.95), 0.015, "steel_dark", segments=6))
            for c in range(rng.randint(2, 3)):
                cx = bx - bw / 4 + c * bw / 4
                parts.append(g.box(f"balcony-{idx}-cloth{c}", (cx, fy + 0.78, z0 + 0.96),
                                   (0.4, 0.45, 0.02), rng.choice(tarp_mats)))
        elif roll < 0.22:  # blue sheet draped over the parapet
            sheet = g.box(f"balcony-{idx}-sheet", (bx + rng.uniform(-0.4, 0.4), fy + 0.75, z0 + 1.13),
                          (bw * 0.6, 0.75, 0.03), rng.choice(tarp_mats))
            parts.append(_planarize(g.transformed_xyz(sheet, math.radians(rng.uniform(4, 10)), 0.0, 0.0, (0.0, 0.0, 0.0))))
        elif roll < 0.30:  # balcony AC unit
            ax = bx + rng.choice((-1.0, 1.0)) * bw * 0.28
            parts.append(g.beveled_box(f"balcony-{idx}-ac", (ax, fy + 0.14 + 0.28, z0 + 0.75), (0.8, 0.56, 0.5), 0.04, "steel_dark"))


def _parasites(parts: list[g.MeshData], w: float, d: float, hx: float, hz: float,
               parasite_mats, intact_top: float, rng: random.Random) -> None:
    """Bolted-on corrugated rooms at mid height with steel brackets."""
    count = rng.randint(2, 4)
    bays_f, margin_f = _bays(w)
    bays_s, margin_s = _bays(d)
    for n in range(count):
        side = rng.choice(("front", "right", "left"))
        width = w if side == "front" else d
        bays, margin = (bays_f, margin_f) if side == "front" else (bays_s, margin_s)
        b = rng.randrange(bays)
        u = -width / 2 + margin + BAY * (b + 0.5)
        bw = rng.uniform(2.0, 3.4)
        bh = rng.uniform(1.9, 2.7)
        depth = rng.uniform(1.1, MAX_PROTRUDE - 0.05)
        y_c = rng.uniform(max(FLOOR_H * 2, intact_top * 0.35), max(FLOOR_H * 2 + 0.5, intact_top * 0.8 - bh))
        mat = rng.choice(parasite_mats)
        yaw, off = _face_transform(side, hx, hz)
        box_ = g.box(f"para-box-{n}", (u, y_c, depth / 2 - 0.06), (bw, bh, depth), mat)
        parts.append(g.transformed(box_, yaw, off, name=f"parasite-{n}"))
        brk = []
        for sgn in (-1.0, 1.0):
            brk.append(_beam(f"pb-{n}{int(sgn)}", (u + sgn * bw * 0.36, y_c - bh / 2 - 0.9, 0.02),
                             (u + sgn * bw * 0.36, y_c - bh / 2 + 0.02, depth - 0.12), 0.06, 0.06, "steel_dark"))
        parts.append(_combine(f"parasite-brk-{n}", [g.transformed(m, yaw, off) for m in brk], "steel_dark"))
        if rng.random() < 0.6:   # tiny dark window on the outer face
            win = g.box(f"pw-{n}", (u + rng.uniform(-0.3, 0.3), y_c + rng.uniform(-0.2, 0.3), depth - 0.045),
                        (0.6, 0.55, 0.03), "glass_dark")
            parts.append(g.transformed(win, yaw, off, name=f"parasite-win-{n}"))


def _stairs(parts: list[g.MeshData], side: str, hx: float, hz: float, d: float,
            intact_top: float, rng: random.Random) -> None:
    """External zigzag steel stair on a side face: landing, flight, landing, alternating."""
    depth_out = 1.45
    flights = min(rng.randint(3, 6), max(1, int(intact_top // FLOOR_H) - 1))
    za = d / 2 - 1.1
    if za < 1.0:
        return
    yaw, off = _face_transform(side, hx, hz)
    elems: list[g.MeshData] = []
    # deck is at wall-local x0..x0+depth_out from the face plane (wall z maps to the face normal)
    def land(z_u: float, y: float, tag: str) -> None:
        elems.append(g.box(f"st-land-{tag}", (z_u, y + 0.04, depth_out / 2 + 0.1), (1.2, 0.08, depth_out), "steel_dark"))
        # railing on the outer edge
        elems.append(g.box(f"st-rr-{tag}", (z_u, y + 0.55, depth_out + 0.02), (1.2, 0.05, 0.04), "steel_dark"))
        for sgn in (-1.0, 1.0):
            elems.append(g.box(f"st-rp-{tag}{int(sgn)}", (z_u + sgn * 0.55, y + 0.3, depth_out + 0.02), (0.04, 0.6, 0.04), "steel_dark"))

    flip = rng.random() < 0.5
    for f in range(flights):
        z_a, z_b = ((-za, za) if (f + flip) % 2 == 0 else (za, -za))
        y0, y1 = f * FLOOR_H, (f + 1) * FLOOR_H
        # stringers (start high enough that the 0.3-deep section stays off the ground)
        for s in (-0.5, 0.5):
            elems.append(_beam(f"st-str-{f}-{int(s*10)}", (z_a, max(y0 + 0.05, 0.2), depth_out / 2 + 0.1 + s * (depth_out - 0.3)),
                               (z_b, y1 + 0.05, depth_out / 2 + 0.1 + s * (depth_out - 0.3)), 0.06, 0.3, "rust",
                               hint=(0.0, 0.0, 1.0)))
        # steps
        steps = 9
        for i in range(steps):
            t = (i + 0.5) / steps
            z = z_a + (z_b - z_a) * t
            y = y0 + (y1 - y0) * t
            elems.append(g.box(f"st-st-{f}-{i}", (z, y, depth_out / 2 + 0.1), (abs(z_b - z_a) / steps * 0.55, 0.05, depth_out - 0.2), "steel_dark"))
        land(z_b, y1, f"{f}b")
    parts.append(_combine("stair-00", [g.transformed(m, yaw, off) for m in elems], "steel_dark"))


def _scaffold(parts: list[g.MeshData], side: str, hx: float, hz: float, width: float,
              intact_top: float, rng: random.Random) -> None:
    """Pipe scaffold grid (1.8 m cells) standing off a lower patch of the face."""
    cell = 1.8
    nw = max(2, min(int(width // cell) - 1, rng.randint(2, 4)))
    nh = max(2, min(int(intact_top // cell) - 1, rng.randint(3, 5)))
    bays, margin = _bays(width)
    u_start = -width / 2 + margin + rng.uniform(0.0, max(0.0, width - 2 * margin - nw * cell))
    yaw, off = _face_transform(side, hx, hz)
    pipes: list[g.MeshData] = []
    out0, out1 = 0.12, 0.55
    for i in range(nw + 1):
        for out in (out0, out1):
            pipes.append(g.pipe(f"sc-v-{i}-{int(out*10)}", (u_start + i * cell, 0.0, out),
                                (u_start + i * cell, nh * cell, out), 0.03, "steel_dark", segments=6))
    for j in range(nh + 1):
        for out in (out0, out1):
            pipes.append(g.pipe(f"sc-h-{j}-{int(out*10)}", (u_start, j * cell, out),
                                (u_start + nw * cell, j * cell, out), 0.025, "steel_dark", segments=6))
        for i in range(nw):
            pipes.append(g.pipe(f"sc-r-{j}-{i}", (u_start + i * cell, j * cell, out1),
                                (u_start + (i + 1) * cell, j * cell, out1), 0.02, "steel_dark", segments=5))
    for k in range(2):  # diagonal braces on the outer frame
        i = rng.randrange(nw)
        j = rng.randrange(nh)
        pipes.append(g.pipe(f"sc-d-{k}", (u_start + i * cell, j * cell, out1),
                            (u_start + (i + 1) * cell, (j + 1) * cell, out1), 0.02, "steel_dark", segments=5))
    frame = _combine("scaffold-00-frame", [g.transformed(p, yaw, off) for p in pipes], "steel_dark")
    parts.append(frame)
    planks = []
    for j in range(1, nh):
        if rng.random() < 0.45:
            i = rng.randrange(nw)
            planks.append(g.box(f"sc-pl-{j}", (u_start + (i + 0.5) * cell, j * cell + 0.05, out1 - 0.2),
                                (cell * 0.95, 0.06, 0.32), "pallet_wood"))
    if planks:
        parts.append(_combine("scaffold-01-plank", [g.transformed(p, yaw, off) for p in planks], "pallet_wood"))


def _ac_units(parts: list[g.MeshData], w: float, d: float, hx: float, hz: float,
              intact_top: float, rng: random.Random) -> None:
    """Outdoor AC units (beveled box + fan disc) scattered below windows on the front and sides."""
    count = rng.randint(10, 24)
    units: list[g.MeshData] = []
    fans: list[g.MeshData] = []
    floors = max(1, int(intact_top // FLOOR_H) - 1)
    for n in range(count):
        side = rng.choice(("front", "front", "right", "left"))
        width = w if side == "front" else d
        bays, margin = _bays(width)
        b = rng.randrange(bays)
        f = rng.randrange(floors)
        u = -width / 2 + margin + BAY * (b + 0.5) + rng.uniform(0.75, 1.15) * rng.choice((-1, 1))
        y = f * FLOOR_H + 0.62
        yaw, off = _face_transform(side, hx, hz)
        body = g.beveled_box(f"ac-b-{n}", (u, y, 0.21), (0.8, 0.6, 0.34), 0.04, "steel_dark")
        units.append(g.transformed(body, yaw, off))
        fans.append(g.transformed(g.cylinder(f"ac-f-{n}", (u, y, 0.40), 0.21, 0.05, 8, "steel_dark", axis="Z"), yaw, off))
    parts.append(_combine("ac-00", units + fans, "steel_dark"))


def _drains(parts: list[g.MeshData], sprays: list[Spray], w: float, d: float,
            hx: float, hz: float, top: float, rng: random.Random, to_world) -> None:
    """Corner downspouts and the rust streak sprayed below each outlet."""
    corners = [(1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)]
    rng.shuffle(corners)
    n_drains = rng.randint(2, 4)
    for n, (sx, sz) in enumerate(corners[:n_drains]):
        on_front = sz > 0
        if on_front:
            u = sx * (w / 2 - 0.35)
            pts = [(u, top, hz + 0.09), (u, 0.55, hz + 0.09), (u, 0.32, hz + 0.26)]
            spray_at = (u, 0.3, hz + 0.3)
        else:
            u = sz * (d / 2 - 0.35)
            pts = [(hx + 0.09, top, u), (hx + 0.09, 0.55, u), (hx + 0.26, 0.32, u)]
            spray_at = (hx + 0.3, 0.3, u)
        parts.append(g.tube(f"drain-{n:02d}", pts, 0.045, 6, "steel_dark"))
        sprays.append(Spray(to_world(spray_at), 0.5, (0.9, 0.6, 0.45), 0.5,
                            materials=("concrete_raw", "concrete_stained", "concrete_dark", "concrete_patch")))


def _rooftop(parts: list[g.MeshData], spec: dict, w: float, d: float, hx: float, hz: float,
             H: float, intact_top: float, keep_last: tuple[float, float], rng: random.Random,
             outer: bool) -> None:
    """Parapet ring (broken at the collapsed corner), roof cap, penthouse, tank, antenna, hut."""
    kf, kr = keep_last   # surviving fractions of the top floor's front / right walls
    # parapet: front and right stop at the surviving edge of the top floor.
    f_edge = -w / 2 + w * kf
    r_edge = -d / 2 + d * kr
    parapets = [
        g.box("roof-par-f", ((-w / 2 + f_edge) / 2, H + 0.4, hz - 0.15), (f_edge + w / 2, 0.9, 0.25), "concrete_dark"),
        g.box("roof-par-b", (0.0, H + 0.4, -hz + 0.15), (w, 0.9, 0.25), "concrete_dark"),
        g.box("roof-par-l", (-hx + 0.15, H + 0.4, 0.0), (0.25, 0.9, d), "concrete_dark"),
        g.box("roof-par-r", (hx - 0.15, H + 0.4, (-hz + r_edge) / 2), (0.25, 0.9, r_edge + hz), "concrete_dark"),
    ]
    for p in parapets:
        spans = [(max(v[c] for v in p.vertices) - min(v[c] for v in p.vertices)) for c in range(3)]
        if min(spans) > 0.05:
            parts.append(p)
    # roof cap over the surviving L of the top (keeps the interior closed from above)
    if kf >= 0.999 and kr >= 0.999:
        parts.append(g.box("roof-slab", (0.0, H - 0.08, 0.0), (w - 0.4, 0.16, d - 0.4), "concrete_dark"))
    else:
        parts.append(g.box("roof-slab-a", (0.0, H - 0.08, (-hz + r_edge - 0.1) / 2),
                           (w - 0.4, 0.16, r_edge - 0.1 + hz), "concrete_dark"))
        parts.append(g.box("roof-slab-b", ((-w / 2 + f_edge - 0.1) / 2, H - 0.08, (hz + r_edge - 0.1) / 2),
                           (f_edge - 0.1 + w / 2, 0.16, hz - r_edge + 0.1), "concrete_dark"))
    # penthouse on the surviving back-left quadrant
    pw, pd = rng.uniform(2.2, 3.6), rng.uniform(2.0, 3.2)
    ph = rng.uniform(2.0, 2.9)
    px = rng.uniform(-w / 2 + 0.6 + pw / 2, min(-0.4, w / 2 - 0.6 - pw / 2))
    pz = rng.uniform(-hz + 0.6 + pd / 2, min(-0.4, hz / 2 - 0.6 - pd / 2))
    parts.append(g.box("roof-penthouse", (px, H + ph / 2, pz), (pw, ph, pd), rng.choice(("concrete_dark", "concrete_patch"))))
    # water tank on legs
    if rng.random() < 0.7:
        tx = rng.uniform(-w / 2 + 1.6, min(w / 2 - 1.6, 0.5))
        tz = rng.uniform(-hz + 1.6, min(hz / 2 - 1.6, -0.5))
        r = rng.uniform(0.9, 1.25)
        tank_h = rng.uniform(1.7, 2.2)
        leg_h = 1.1
        legs = []
        for lx, lz in ((-0.8, -0.8), (0.8, -0.8), (-0.8, 0.8), (0.8, 0.8)):
            legs.append(g.pipe("tank-leg", (tx + lx * r / 1.1, H + 0.02, tz + lz * r / 1.1),
                               (tx + lx * r / 1.1, H + leg_h + 0.1, tz + lz * r / 1.1), 0.05, "steel_dark", segments=6))
        parts.append(_combine("roof-tank-legs", legs, "steel_dark"))
        parts.append(g.cylinder("roof-tank", (tx, H + leg_h + 0.15 + tank_h / 2, tz), r, tank_h, 10, "rust"))
    # antenna
    for n in range(rng.randint(1, 2)):
        ax = rng.uniform(-w / 2 + 1.0, w / 4)
        az = rng.uniform(-hz + 1.0, hz / 3)
        ah = rng.uniform(3.0, 5.0)
        parts.append(g.pipe(f"roof-ant-{n}", (ax, H + 0.4, az), (ax, H + 0.4 + ah, az), 0.03, "steel_dark", segments=6))
        parts.append(g.pipe(f"roof-ant-x{n}", (ax - 0.5, H + 0.4 + ah * 0.75, az),
                            (ax + 0.5, H + 0.4 + ah * 0.75, az), 0.02, "steel_dark", segments=5))
    # rooftop hut (outer towers only)
    if outer and rng.random() < 0.6:
        hw, hd = rng.uniform(1.8, 2.6), rng.uniform(1.6, 2.2)
        hh = rng.uniform(1.8, 2.3)
        hxx = rng.uniform(-w / 2 + 0.8 + hw / 2, min(w / 4, w / 2 - 0.8 - hw / 2))
        hzz = rng.uniform(-hz + 0.8 + hd / 2, min(hz / 4, hz / 2 - 0.8 - hd / 2))
        parts.append(g.box("roof-hut", (hxx, H + 0.9 + hh / 2, hzz), (hw, hh, hd), rng.choice(("corrugated", "corrugated_rust"))))
        lid = g.prism("roof-hut-lid", (0.0, 0.0, 0.0), (hw + 0.3, 0.5, hd + 0.3), "corrugated_rust")
        parts.append(g.transformed_xyz(lid, 0.0, rng.choice((0.0, math.pi / 2)), 0.0,
                                       (hxx, H + 0.9 + hh + 0.25, hzz), name="roof-hut-lid"))


def _neon_strip(parts: list[g.MeshData], spec: dict, w: float, hz: float,
                intact_top: float, rng: random.Random) -> None:
    """Perpendicular vertical sign: steel backing + neon faces both ways, on the front."""
    h = rng.uniform(3.2, min(6.0, intact_top - 2.0))
    if h < 2.5:
        return
    depth = rng.uniform(0.6, 0.85)
    x = rng.uniform(-w / 2 + 1.5, w / 2 - 1.5)
    y_c = rng.uniform(3.5, max(3.6, intact_top - h - 0.8)) + h / 2
    neon = rng.choice(NEON_MATS)
    parts.append(g.box("neon-strip-back", (x, y_c, hz + depth / 2), (0.16, h, depth), "steel_dark"))
    for sgn in (-1.0, 1.0):
        parts.append(g.box(f"neon-strip-face-{int(sgn)}", (x + sgn * 0.085, y_c, hz + depth / 2),
                           (0.02, h - 0.25, depth - 0.12), neon))
    for sgn in (-0.3, 0.3):
        parts.append(_beam(f"neon-strip-arm{int(sgn*10)}", (x, y_c + sgn * h, hz - 0.02),
                           (x, y_c + sgn * h, hz + 0.3), 0.05, 0.05, "steel_dark"))


# --------------------------------------------------------------------------- tower assembly


def build_tower(spec: dict) -> g.Assembly:
    """One derelict tower from a layout spec. Origin = (cx, 0, cz); parts carry the yaw."""
    rng = random.Random(spec["seed"])
    w, d = _local_dims(spec)
    hx, hz = w / 2, d / 2
    H = float(spec["height"])
    collapse = int(spec.get("collapse", 0))
    intact_top = round(H - collapse * FLOOR_H, 2)          # == core_height + 0.5
    outer = spec["role"] == "outer"
    cx, cz = spec["center"]
    yaw_total = math.radians(spec["rotation"])
    facade_mat = rng.choice(("concrete_raw", "concrete_stained"))
    parts: list[g.MeshData] = []
    sprays: list[Spray] = []

    def to_world(p: Vec) -> Vec:
        q = g.rotate_y(p, yaw_total)
        return (q[0] + cx, q[1], q[2] + cz)

    floors_intact = max(1, int(intact_top // FLOOR_H))

    # --- facades -------------------------------------------------------------
    bays_f, margin_f = _bays(w)
    bays_d, margin_d = _bays(d)
    door_bay = bays_f // 2
    door_cx = -w / 2 + margin_f + BAY * (door_bay + 0.5)
    door_h = min(3.0, intact_top - 0.4)
    has_door = door_h >= 1.8
    front_ops = _window_openings(w, intact_top, floors_intact + 1, rng, first_floor_door=has_door)
    door_idx = -1
    if has_door:
        front_ops.append((round(door_cx - 1.8, 3), 0.06, round(door_cx + 1.8, 3), round(door_h, 3)))
        door_idx = len(front_ops) - 1
    back_ops = [] if outer else _window_openings(w, H, int(H // FLOOR_H) + 1, rng)
    left_ops = _window_openings(d, H, int(H // FLOOR_H) + 1, rng)
    right_ops = _window_openings(d, intact_top, floors_intact + 1, rng)

    walls = {
        "front": _wall("facade-front", w, intact_top, front_ops, 1.2, facade_mat),
        "back": _wall("facade-back", w, H, back_ops, 4.0 if outer else 1.2, facade_mat),
        "left": _wall("facade-left", d, H, left_ops, 1.2, facade_mat),
        "right": _wall("facade-right", d, intact_top, right_ops, 1.2, facade_mat),
    }
    face_ops = {"front": front_ops, "back": back_ops, "left": left_ops, "right": right_ops}
    for side, wall in walls.items():
        yaw, off = _face_transform(side, hx, hz)
        parts.append(g.transformed(wall, yaw, off))

    # interior shadow box: dark mass behind recesses/entrances and the collapsed corner
    parts.append(g.box("core-void", (0.0, (H - 0.35) / 2 + 0.02, 0.0),
                       (max(0.5, w - 2 * CORE_INSET), H - 0.35, max(0.5, d - 2 * CORE_INSET)), "concrete_dark"))

    # --- collapsed corner (front-right): partial panels, torn slabs, rebar ---
    keep_f = [1.0] + [1 - rng.uniform(0.25, 0.60) for _ in range(collapse)]
    keep_r = [1.0] + [1 - rng.uniform(0.25, 0.60) for _ in range(collapse)]
    collapsed_ops: list[tuple[float, list, float, Vec]] = []   # (yaw, ops, y0, offset) for panes
    for j in range(collapse):
        y0 = intact_top + j * FLOOR_H
        wj = w * keep_f[j + 1]
        ops = _window_openings(wj, FLOOR_H, 2, rng)
        panel = _wall(f"facade-front-top-{j}", wj, FLOOR_H, ops, 1.2, facade_mat)
        parts.append(g.transformed(panel, 0.0, (-w / 2 + wj / 2, y0, hz - WALL_T / 2)))
        collapsed_ops.append((0.0, ops, y0, (-w / 2 + wj / 2, y0, hz - WALL_T / 2)))
        dj = d * keep_r[j + 1]
        ops = _window_openings(dj, FLOOR_H, 2, rng)
        panel = _wall(f"facade-right-top-{j}", dj, FLOOR_H, ops, 1.2, facade_mat)
        parts.append(g.transformed(panel, math.pi / 2, (hx - WALL_T / 2, y0, -hz + dj / 2)))
        collapsed_ops.append((math.pi / 2, ops, y0, (hx - WALL_T / 2, y0, -hz + dj / 2)))
        edge_f = -w / 2 + wj
        edge_r = -hz + dj
        # broken wall edges at the surviving panel ends
        parts.append(g.box(f"collapse-edge-f-{j}", (edge_f - 0.07, y0 + FLOOR_H / 2, hz - 0.28),
                           (0.16, FLOOR_H, 0.56), "concrete_dark"))
        parts.append(g.box(f"collapse-edge-r-{j}", (hx - 0.28, y0 + FLOOR_H / 2, edge_r - 0.07),
                           (0.56, FLOOR_H, 0.16), "concrete_dark"))
        # torn slab bands sticking out of the void, ragged outline
        parts.append(_ragged_strip(f"collapse-slab-f-{j}", edge_f - 0.2, hx + 0.15, hz - 1.15, hz + 0.05,
                                   y0, 0.3, rng, "concrete_stained"))
        parts.append(_ragged_strip(f"collapse-slab-r-{j}", hx - 1.15, hx + 0.05, edge_r - 0.2, hz + 0.15,
                                   y0, 0.3, rng, "concrete_stained"))
        rebar = []
        for b in range(rng.randint(3, 5)):
            bx = rng.uniform(edge_f + 0.2, hx - 0.2)
            rebar.append(g.tube(f"rb-f-{j}-{b}", [(bx, y0 + 0.1, hz - 0.9), (bx + rng.uniform(-0.1, 0.1), y0 + 0.12, hz - 0.3),
                                                  (bx + rng.uniform(-0.2, 0.2), y0 - rng.uniform(0.1, 0.5), hz + rng.uniform(0.3, 0.7))],
                                0.018, 5, "rust"))
            bz = rng.uniform(edge_r + 0.2, hz - 0.2)
            rebar.append(g.tube(f"rb-r-{j}-{b}", [(hx - 0.9, y0 + 0.1, bz), (hx - 0.3, y0 + 0.12, bz + rng.uniform(-0.1, 0.1)),
                                                  (hx + rng.uniform(0.3, 0.7), y0 - rng.uniform(0.1, 0.5), bz + rng.uniform(-0.2, 0.2))],
                                0.018, 5, "rust"))
        parts.append(_combine(f"collapse-rebar-{j}", rebar, "rust"))
        for c in range(rng.randint(1, 2)):
            debris = _chunk(f"collapse-debris-{j}-{c}", (rng.uniform(0.3, 0.7), rng.uniform(0.15, 0.4), rng.uniform(0.3, 0.6)),
                            rng, "concrete_stained")
            parts.append(g.transformed(debris, 0.0, (rng.uniform(edge_f + 0.3, hx - 0.5), y0 + 0.28, hz - 0.6)))

    # --- panes (in the recess, some lit) --------------------------------------
    glass: list[g.MeshData] = []
    lit: list[g.MeshData] = []
    for side, ops in face_ops.items():
        yaw, off = _face_transform(side, hx, hz)
        skip = {door_idx} if side == "front" and door_idx >= 0 else set()
        _panes(ops, skip, yaw, off, rng, glass, lit, side)
    for yaw, ops, _y0, off in collapsed_ops:
        _panes(ops, set(), yaw, off, rng, glass, lit, "top")
    if glass:
        parts.append(_combine("pane-00-glass", glass, "glass_dark"))
    if lit:
        parts.append(_combine("pane-01-lit", lit, "window_lit"))

    # --- fins + slab lips ------------------------------------------------------
    edge_f_last = -w / 2 + w * keep_f[-1] if collapse else w / 2
    edge_r_last = -hz + d * keep_r[-1] if collapse else hz
    for side, width in (("front", w), ("back", w), ("left", d), ("right", d)):
        yaw, off = _face_transform(side, hx, hz)
        bays, margin = _bays(width)
        for b in range(bays + 1):
            u = -width / 2 + margin + b * BAY
            top = H
            if side == "front" and u > edge_f_last - 0.25:
                top = intact_top
            if side == "right" and u > edge_r_last - 0.25:
                top = intact_top
            if top < 1.0:
                continue
            fin = g.box("fin", (u, top / 2, FIN_OUT / 2 - 0.12), (FIN_W, top, FIN_OUT + 0.24), facade_mat)
            parts.append(g.transformed(fin, yaw, off, name=f"fin-{side[0]}{b}"))
        for f in range(1, int(H // FLOOR_H) + 1):
            y = f * FLOOR_H
            if y > H - 0.2:
                continue
            u0, u1 = -width / 2, width / 2
            if y > intact_top - 0.01:
                jj = min(collapse - 1, int((y - intact_top) // FLOOR_H)) if collapse else 0
                if side == "front":
                    u1 = -w / 2 + w * keep_f[jj + 1]
                elif side == "right":
                    u1 = -d / 2 + d * keep_r[jj + 1]
            if u1 - u0 < 0.4:
                continue
            lip = g.box("slip", ((u0 + u1) / 2, y, 0.07), (u1 - u0, LIP_H, 0.26), "concrete_dark")
            parts.append(g.transformed(lip, yaw, off, name=f"slab-lip-{side[0]}{f}"))

    # --- podium entrance --------------------------------------------------------
    if has_door:
        _podium(parts, hx, hz, door_cx, door_h, rng)

    # --- additions --------------------------------------------------------------
    # cap per-tower material variety (<=13 materials): additions reuse a 2-tone pick
    parasite_mats = rng.sample(PARASITE_MATS, 2)
    tarp_mats = rng.sample(("tarp_blue", "tarp_orange", "tarp_green", "cloth_red"), 2)
    _balconies(parts, w, hz, tarp_mats, intact_top, rng)
    _parasites(parts, w, d, hx, hz, parasite_mats, intact_top, rng)
    stair_side = rng.choice(("right", "left"))
    if rng.random() < 0.5:
        _stairs(parts, stair_side, hx, hz, d, intact_top, rng)
    if rng.random() < 0.3:
        _scaffold(parts, rng.choice(("right", "left")), hx, hz, d, intact_top, rng)
    _ac_units(parts, w, d, hx, hz, intact_top, rng)
    _drains(parts, sprays, w, d, hx, hz, intact_top - 0.3, rng, to_world)
    _rooftop(parts, spec, w, d, hx, hz, H, intact_top, (keep_f[-1], keep_r[-1]), rng, outer)
    if rng.random() < 0.5:
        _neon_strip(parts, spec, w, hz, intact_top, rng)

    # --- sprays: ground-floor tags, sill streaks -------------------------------
    concrete_only = ("concrete_raw", "concrete_stained", "concrete_dark", "concrete_patch")
    for n in range(rng.randint(3, 6)):
        side = rng.choice(("front", "front", "right", "left"))
        width = w if side == "front" else d
        u = rng.uniform(-width / 2 + 1.0, width / 2 - 1.0)
        y = rng.uniform(0.6, 2.6)
        local = (u, y, hz + 0.05) if side == "front" else (hx + 0.05, y, u) if side == "right" else (-hx - 0.05, y, u)
        sprays.append(Spray(to_world(local), round(rng.uniform(0.45, 0.8), 3), TAG_COLORS[n % len(TAG_COLORS)],
                            round(rng.uniform(0.35, 0.55), 3), materials=concrete_only))
    # rain streaks below a few window sills (concrete only, off the glass)
    sill_pool = (front_ops[:door_idx] if door_idx >= 0 else front_ops)[:24]
    rng.shuffle(sill_pool)
    for x0, y0, x1, _y1 in sill_pool[: rng.randint(4, 8)]:
        sprays.append(Spray(to_world(((x0 + x1) / 2 + rng.uniform(-0.2, 0.2), y0 - 0.2, hz + 0.04)),
                            round(rng.uniform(0.45, 0.7), 3), (0.55, 0.52, 0.48), 0.35, materials=concrete_only))

    # bake the spec yaw into every part; origin stays the footprint centre at ground
    parts = [g.transformed(_planarize(p), yaw_total, (0.0, 0.0, 0.0)) for p in parts]
    meta: dict[str, Any] = {"sprays": sprays}
    if outer:
        meta["occludes"] = [f"occ-{spec['id']}"]
    return g.Assembly("tower", spec["id"], spec["sector"], (cx, 0.0, cz), parts, meta)


# --------------------------------------------------------------------------- sectors


def _sector_towers(data: dict[str, Any], sector: str) -> list[g.Assembly]:
    return [build_tower(t) for t in data["towers"] if t["sector"] == sector]


@register("towers-a")
def towers_a_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    return _sector_towers(data, "towers-a")


@register("towers-b")
def towers_b_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    return _sector_towers(data, "towers-b")


@register("towers-c")
def towers_c_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    return _sector_towers(data, "towers-c")


SECTOR_BUILDERS = {"towers-a": towers_a_assemblies, "towers-b": towers_b_assemblies,
                   "towers-c": towers_c_assemblies}
