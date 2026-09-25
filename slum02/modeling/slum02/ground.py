"""Ground (streets, blocks, curbs, puddles, street furniture) and distant backdrop sectors.

Both generators are pure Python and deterministic (sector-specific ``random.Random``
seeds derived from ``SEED``). Coordinates are Resonite XYZ (Y up, metres); every part is
authored in world space around an origin of (0, 0, 0).

Ground
    ``ground-base`` is one 80 x 80 m sheet split on a 1 m grid whose lines also follow
    every street edge, so the asphalt / block boundary sits exactly where the curbs are.
    Street cells sit 0.02 m below the block top (``GROUND_TOP``) and a vertical step face
    closes every boundary. All parts follow the R11 winding rule (outward/CCW in Resonite
    XYZ; ``create_object`` only mirrors, it never recalculates normals): walkable sheets face
    +Y by vertex order and every other part is a closed, outward shell.
    Dirt is caused rather than uniform: ``vcolor.Spray`` masks darken the foot of every
    building wall, the gutter band along each curb, oil drips, puddle rims and the rust
    bleed around manholes.

Backdrop
    A low-poly ring beyond the 80 m site: a flat ground annulus from the site square out to
    a 220 m circle (hides the world's grid floor) and one set-back mass per layout mass
    with lit window bands on its two centre-facing sides, aviation lights and, on three
    masses, a giant holo billboard.
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any

from modeling.slum02 import SEED
from modeling.slum02 import geometry as g
from modeling.slum02.layout import _aabb, _extent, _to_world
from modeling.slum02.sectors import register
from modeling.slum02.vcolor import Spray, _face_normal

GROUND_TOP = 0.10
STREET_DROP = 0.02
STREET_TOP = GROUND_TOP - STREET_DROP
HALF = 40.0
PLAZA = 10.0
CELL = 1.0
PUDDLE_TOP = 0.104
CURB_HEIGHT = 0.15
CURB_WIDTH = 0.18
CURB_SKIP = 0.15
BACKDROP_TOP = 0.05
RING_SEGMENTS = 64
WINDOW_MIN_Y = 24.0

Rect = tuple[float, float, float, float]
LITTER_MATERIALS = ("plywood", "plywood", "tarp_blue", "tarp_orange", "tarp_green", "rubber")


# --------------------------------------------------------------------------- helpers


def _in_rect(x: float, z: float, r: Rect, pad: float = 0.0) -> bool:
    return r[0] - pad <= x <= r[2] + pad and r[1] - pad <= z <= r[3] + pad


def _street_rects(data: dict[str, Any]) -> list[Rect]:
    return [(s["min"][0], s["min"][1], s["max"][0], s["max"][1]) for s in data["streets"]]


PLAZA_RECT: Rect = (-PLAZA, -PLAZA, PLAZA, PLAZA)


def _on_street(x: float, z: float, streets: list[Rect]) -> bool:
    return any(_in_rect(x, z, r) for r in streets) or _in_rect(x, z, PLAZA_RECT)


def top_at(x: float, z: float, streets: list[Rect]) -> float:
    return STREET_TOP if _on_street(x, z, streets) else GROUND_TOP


def _tower_corners(t: dict[str, Any]) -> list[tuple[float, float]]:
    w, d = _extent(t)
    return [_to_world(t, sx * w / 2, sz * d / 2) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def _octagon(rng: random.Random, cx: float, cz: float, r: float, jitter: float = 0.25) -> list[tuple[float, float]]:
    phase = rng.uniform(0, math.tau)
    out = []
    for k in range(8):
        a = phase + math.tau * k / 8
        rr = r * (1 + rng.uniform(-jitter, jitter))
        out.append((cx + math.cos(a) * rr, cz + math.sin(a) * rr))
    return out


def _blockers(data: dict[str, Any]) -> list[Rect]:
    return [_aabb(x) for key in ("towers", "stalls", "clubs", "shacks") for x in data[key]]


# --------------------------------------------------------------------------- ground base


def _slab_pieces(holes: list[Rect]) -> list[Rect]:
    """Split the 80 x 80 m slab into x-strips of z-intervals that leave every hole open."""
    xs = sorted({-HALF, HALF, *(c for r in holes for c in (r[0], r[2]))})
    pieces: list[Rect] = []
    for x0, x1 in zip(xs, xs[1:]):
        mid = (x0 + x1) / 2
        cuts = sorted((r[1], r[3]) for r in holes if r[0] < mid < r[2])
        z = -HALF
        for z0, z1 in cuts:
            if z0 > z:
                pieces.append((x0, z, x1, z0))
            z = max(z, z1)
        if z < HALF:
            pieces.append((x0, z, x1, HALF))
    return pieces


def _base_parts(streets: list[Rect], holes: list[Rect] = ()) -> list[g.MeshData]:
    """Ground sheet + slab. ``holes`` (the plaza's below-grade pits) are left open in both."""
    holes = list(holes)
    cuts_x = sorted({c for r in (*streets, PLAZA_RECT, *holes) for c in (r[0], r[2]) if -HALF < c < HALF})
    cuts_z = sorted({c for r in (*streets, PLAZA_RECT, *holes) for c in (r[1], r[3]) if -HALF < c < HALF})
    xs = g._splits(-HALF, HALF, CELL, cuts_x)
    zs = g._splits(-HALF, HALF, CELL, cuts_z)
    nx, nz = len(xs) - 1, len(zs) - 1
    street = [[_on_street((xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2, streets) for j in range(nz)]
              for i in range(nx)]
    road, block = g.GridBuilder(), g.GridBuilder()
    for i in range(nx):
        for j in range(nz):
            x0, x1, z0, z1 = xs[i], xs[i + 1], zs[j], zs[j + 1]
            if any(_in_rect((x0 + x1) / 2, (z0 + z1) / 2, h) for h in holes):
                continue  # the plaza pit liner closes the hole
            top = STREET_TOP if street[i][j] else GROUND_TOP
            # (x0,z0)->(x0,z1)->(x1,z1)->(x1,z0) is +Y by Newell in Resonite XYZ.
            (road if street[i][j] else block).quad((x0, top, z0), (x0, top, z1), (x1, top, z1), (x1, top, z0))
    parts = [road.build("base-asphalt", "asphalt"), block.build("base-blocks", "concrete_stained")]
    # 0.02 m step where a block cell meets a street cell. Each straight run is one closed thin box
    # (closed thin shells survive later welding/editing better than stray vertical quads).
    runs: list[tuple[str, float, float, float]] = []
    for i in range(nx - 1):
        for j in range(nz):
            if street[i][j] != street[i + 1][j]:
                runs.append(("x", xs[i + 1], zs[j], zs[j + 1]))
    for j in range(nz - 1):
        for i in range(nx):
            if street[i][j] != street[i][j + 1]:
                runs.append(("z", zs[j + 1], xs[i], xs[i + 1]))
    merged: list[list[float]] = []
    for axis, value, lo, hi in sorted(runs):
        last = merged[-1] if merged else None
        if last and last[0] == axis and abs(last[1] - value) < 1e-9 and abs(last[3] - lo) < 1e-9:
            last[3] = hi
        else:
            merged.append([axis, value, lo, hi])
    t = 0.02
    for k, (axis, value, lo, hi) in enumerate(merged):
        mid, length = (lo + hi) / 2, hi - lo
        centre = (value, (STREET_TOP + GROUND_TOP) / 2 - 0.001, mid) if axis == "x" else (mid, (STREET_TOP + GROUND_TOP) / 2 - 0.001, value)
        size = (t, STREET_DROP - 0.002, length) if axis == "x" else (length, STREET_DROP - 0.002, t)
        parts.append(g.box(f"step-{k:03d}", centre, size, "concrete_stained"))
    # Perimeter skirt down to the slab body (inside the 80 m square, closed boxes).
    sk, y0 = 0.02, -0.02
    h = GROUND_TOP - 0.001 - y0
    for k, (cx, cz, sx, sz) in enumerate(((HALF - sk / 2, 0, sk, 2 * HALF), (-HALF + sk / 2, 0, sk, 2 * HALF),
                                          (0, HALF - sk / 2, 2 * HALF - 2 * sk, sk), (0, -HALF + sk / 2, 2 * HALF - 2 * sk, sk))):
        parts.append(g.box(f"skirt-{k}", (cx, y0 + h / 2, cz), (sx, h, sz), "concrete_dark"))
    for k, (x0, z0, x1, z1) in enumerate(_slab_pieces(holes)):
        name = "slab-body" if not holes else f"slab-body-{k:02d}"
        parts.append(g.box(name, ((x0 + x1) / 2, -0.1, (z0 + z1) / 2), (x1 - x0, 0.16, z1 - z0), "concrete_dark"))
    return parts


# --------------------------------------------------------------------------- curbs + grates


def _curb_edges(streets: list[Rect], blockers: list[Rect]):
    """Yield (start, end, inward_normal) street edges that border a block (not another street)."""
    for r in streets:
        x0, z0, x1, z1 = r
        # (fixed coordinate axis, fixed value, lo, hi, outward sign)
        for axis, value, lo, hi, sign in (("z", z0, x0, x1, -1), ("z", z1, x0, x1, 1),
                                          ("x", x0, z0, z1, -1), ("x", x1, z0, z1, 1)):
            if abs(value) >= HALF - 0.01:
                continue
            yield r, axis, value, lo, hi, sign


def _curbs_and_grates(streets: list[Rect], blockers: list[Rect], rng: random.Random):
    curbs: list[g.MeshData] = []
    grates: list[g.MeshData] = []
    gutter_points: list[tuple[float, float]] = []
    towers_only = blockers

    def pt(axis: str, value: float, t: float, off: float) -> tuple[float, float]:
        return (t, value + off) if axis == "z" else (value + off, t)

    for r, axis, value, lo, hi, sign in _curb_edges(streets, blockers):
        others = [o for o in streets if o != r]
        t = lo
        while t < hi - 0.3:
            length = min(rng.uniform(1.0, 2.5), hi - t)
            a, b = t, t + length
            t = b
            samples = (a + 0.05, (a + b) / 2, b - 0.05)
            outside = [pt(axis, value, s, sign * 0.3) for s in samples]
            inside = [pt(axis, value, s, -sign * 0.3) for s in samples]
            if any(_on_street(x, z, streets) or abs(x) > HALF - 0.2 or abs(z) > HALF - 0.2 for x, z in outside):
                continue
            if any(_in_rect(x, z, o) for x, z in inside for o in [*others, PLAZA_RECT]):
                continue
            if any(_in_rect(x, z, bl, 0.4) for x, z in outside for bl in towers_only):
                continue
            mid = (a + b) / 2
            gx, gz = pt(axis, value, mid, -sign * 0.55)
            gutter_points.append((gx, gz))
            if rng.random() < CURB_SKIP:      # broken-out curb stone: leave its fragments in the gap
                for f in range(rng.randint(1, 2)):
                    fl, fh, fw = rng.uniform(0.2, 0.45), rng.uniform(0.07, 0.12), rng.uniform(0.12, 0.18)
                    fx, fz = pt(axis, value, rng.uniform(a + 0.2, b - 0.2), -sign * rng.uniform(0.1, 0.35))
                    chunk = g.box("chunk", (0, fh / 2, 0), (fl, fh, fw), "concrete_raw")
                    curbs.append(g.transformed_xyz(chunk, math.radians(rng.uniform(-18, 18)), rng.uniform(0, math.tau),
                                                   math.radians(rng.uniform(-12, 12)), (fx, STREET_TOP - 0.01, fz),
                                                   name=f"curb-chunk-{len(curbs):03d}"))
                continue
            piece_len = length - 0.02            # visible joint between stones
            sunk = rng.random() < 0.12
            drop = rng.uniform(0.02, 0.05) if sunk else rng.uniform(-0.004, 0.004)
            local = _curb_stone(piece_len, rng)
            tilt = math.radians(rng.uniform(2.0, 5.0)) * (1 if rng.random() < 0.5 else -1) if sunk else 0.0
            yaw = math.radians(rng.uniform(-0.8, 0.8)) + (0.0 if axis == "z" else math.pi / 2)
            cx, cz = pt(axis, value, mid, -sign * (CURB_WIDTH / 2))
            m = g.transformed_xyz(local, tilt, yaw, 0.0, (cx, STREET_TOP - 0.005 - drop, cz), name=f"curb-{len(curbs):03d}")
            curbs.append(m)
            if rng.random() < 0.14:
                grates.extend(_grate(len(grates) // 10, axis, pt(axis, value, mid, -sign * (CURB_WIDTH + 0.24))))
    return curbs, grates, gutter_points


def _curb_stone(length: float, rng: random.Random) -> g.MeshData:
    """Closed curb-stone prism along local X: chamfered top edges (0.02 m), 20 triangles.

    The street-side top edge is sometimes chipped deeper, as kerbs are hit by wheels.
    """
    h, w, b = CURB_HEIGHT, CURB_WIDTH, 0.02
    chip = b + (rng.uniform(0.015, 0.035) if rng.random() < 0.3 else 0.0)
    profile = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h - b), (w / 2 - b, h), (-w / 2 + chip, h), (-w / 2, h - chip)]
    hl = length / 2
    verts = [(-hl, y, z) for z, y in profile] + [(hl, y, z) for z, y in profile]
    n = len(profile)
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    faces += [(k, k + n, (k + 1) % n + n, (k + 1) % n) for k in range(n)]
    return g.mesh("curb", verts, faces, "concrete_raw")


def _grate(index: int, axis: str, centre: tuple[float, float]) -> list[g.MeshData]:
    """0.8 x 0.4 m gutter grating: dark sump plate, side frame and cross bars (local along = X)."""
    parts = [g.box("plate", (0, STREET_TOP + 0.002, 0), (0.84, 0.006, 0.44), "rubber"),
             g.box("frame-a", (0, STREET_TOP + 0.008, 0.2), (0.84, 0.014, 0.04), "rust_dark"),
             g.box("frame-b", (0, STREET_TOP + 0.008, -0.2), (0.84, 0.014, 0.04), "rust_dark")]
    for k in range(7):
        x = -0.36 + k * 0.12
        parts.append(g.box("bar", (x, STREET_TOP + 0.008, 0), (0.03, 0.012, 0.36), "rust_dark"))
    yaw = 0.0 if axis == "z" else math.pi / 2
    return [g.transformed(p, yaw, (centre[0], 0.0, centre[1]), name=f"grate-{index:02d}-{p.name}") for p in parts]


# --------------------------------------------------------------------------- puddles, manholes, cracks, litter


def _street_point(rng: random.Random, streets: list[Rect], margin: float) -> tuple[float, float] | None:
    weights = [max(0.0, (r[2] - r[0] - 2 * margin) * (r[3] - r[1] - 2 * margin)) for r in streets]
    r = rng.choices(streets, weights=weights)[0]
    if r[2] - r[0] <= 2 * margin or r[3] - r[1] <= 2 * margin:
        return None
    return rng.uniform(r[0] + margin, r[2] - margin), rng.uniform(r[1] + margin, r[3] - margin)


def _puddles(streets: list[Rect], avoid: list[tuple[float, float, float]], rng: random.Random):
    parts, halos = [], []
    attempts = 0
    while len(parts) < 14 and attempts < 4000:
        attempts += 1
        r = rng.choices(streets, weights=[(s[2] - s[0]) * (s[3] - s[1]) for s in streets])[0]
        span = min(r[2] - r[0], r[3] - r[1])
        # Brief range 0.6-1.8 m, clamped so the jittered rim + meniscus stays inside the curbs.
        radius = min(rng.uniform(0.6, 1.8), (span / 2 - 0.4) / 1.25)
        margin = radius * 1.25 + 0.3
        p = (rng.uniform(r[0] + margin, r[2] - margin), rng.uniform(r[1] + margin, r[3] - margin))
        if _in_rect(*p, PLAZA_RECT, radius + 0.5):
            continue
        if any(math.hypot(p[0] - ax, p[1] - az) < radius + ar + 0.6 for ax, az, ar in avoid):
            continue
        rim = _octagon(rng, p[0], p[1], radius)
        outer = [(p[0] + (x - p[0]) * 1.0 + (x - p[0]) / max(1e-6, math.hypot(x - p[0], z - p[1])) * 0.25,
                  p[1] + (z - p[1]) * 1.0 + (z - p[1]) / max(1e-6, math.hypot(x - p[0], z - p[1])) * 0.25) for x, z in rim]
        verts = [(x, PUDDLE_TOP, z) for x, z in rim] + [(x, STREET_TOP + 0.0015, z) for x, z in outer]
        # Top octagon (+Y) and a sloped meniscus skirt down to the asphalt.
        faces = [tuple(reversed(range(8)))]
        if _face_normal([verts[i] for i in faces[0]])[1] < 0:
            faces = [tuple(range(8))]
        for k in range(8):
            q = [k, (k + 1) % 8, 8 + (k + 1) % 8, 8 + k]
            n = _face_normal([verts[i] for i in q])
            faces.append(tuple(q) if n[1] > 0 else tuple(reversed(q)))
        bottom = tuple(range(8, 16))
        faces.append(bottom if _face_normal([verts[i] for i in bottom])[1] < 0 else tuple(reversed(bottom)))
        parts.append(g.mesh(f"puddle-{len(parts):02d}", verts, faces, "asphalt_wet"))  # closed shell
        avoid.append((p[0], p[1], radius * 1.25 + 0.25))
        halos.append(Spray((p[0], STREET_TOP, p[1]), radius * 1.9 + 0.6, (0.55, 0.58, 0.63), 0.75))
    return parts, halos


MANHOLE_SITES: tuple[tuple[str, float], ...] = (
    ("ring-n", -6.0), ("ring-s", 5.0), ("ring-e", -4.5), ("ring-w", 6.5), ("lane", -12.5), ("lane", 13.5))


def _manholes(data: dict[str, Any], rng: random.Random):
    by_id = {s["id"]: s for s in data["streets"]}
    parts, avoid, sprays = [], [], []
    for k, (sid, along) in enumerate(MANHOLE_SITES):
        s = by_id[sid]
        (x0, z0), (x1, z1) = s["min"], s["max"]
        horizontal = (x1 - x0) >= (z1 - z0)
        across = ((z0 + z1) / 2 if horizontal else (x0 + x1) / 2) + rng.uniform(-0.4, 0.4)
        along += rng.uniform(-1.0, 1.0)
        x, z = (along, across) if horizontal else (across, along)
        parts.append(g.box(f"mh-frame-{k}", (x, STREET_TOP + 0.004, z), (0.95, 0.008, 0.95), "concrete_dark"))
        parts.append(g.cylinder(f"manhole-{k}", (x, STREET_TOP + 0.012, z), 0.35, 0.03, 16, "steel_dark"))
        spin = rng.uniform(0, math.pi)
        for b in range(2):
            rib = g.box("rib", (0, STREET_TOP + 0.03, 0), (0.6, 0.008, 0.035), "steel_dark")
            parts.append(g.transformed(rib, spin + b * math.pi / 2, (x, 0.0, z), name=f"mh-rib-{k}-{b}"))
        avoid.append((x, z, 0.6))
        sprays.append(Spray((x + rng.uniform(-0.3, 0.3), STREET_TOP, z + rng.uniform(-0.3, 0.3)), 1.1, (1.12, 0.72, 0.5), 0.55))
    return parts, avoid, sprays


def _patches(streets: list[Rect], avoid: list[tuple[float, float, float]], rng: random.Random) -> list[g.MeshData]:
    """Utility-cut repairs: concrete patches set into the asphalt and a few steel road plates (覆工板)."""
    parts: list[g.MeshData] = []
    tries = 0
    plates = patches = 0
    while (plates < 4 or patches < 10) and tries < 3000:
        tries += 1
        r = rng.choices(streets, weights=[(s[2] - s[0]) * (s[3] - s[1]) for s in streets])[0]
        horizontal = (r[2] - r[0]) >= (r[3] - r[1])
        plate = plates < 4
        along, across = (rng.uniform(2.6, 3.2), rng.uniform(1.4, 1.6)) if plate else (rng.uniform(1.0, 3.5), rng.uniform(0.5, 1.4))
        sx, sz = (along, across) if horizontal else (across, along)
        mx, mz = sx / 2 + 0.35, sz / 2 + 0.35
        if r[2] - r[0] <= 2 * mx or r[3] - r[1] <= 2 * mz:
            continue
        x, z = rng.uniform(r[0] + mx, r[2] - mx), rng.uniform(r[1] + mz, r[3] - mz)
        if _in_rect(x, z, PLAZA_RECT, max(sx, sz)):
            continue
        rad = math.hypot(sx, sz) / 2
        if any(math.hypot(x - ax, z - az) < rad + ar + 0.4 for ax, az, ar in avoid):
            continue
        avoid.append((x, z, rad))
        yaw = math.radians(rng.uniform(-2.5, 2.5))
        if plate:
            m = g.beveled_box("plate", (0, STREET_TOP + 0.012, 0), (sx, 0.025, sz), 0.008, "steel_dark")
            parts.append(g.transformed(m, yaw, (x, 0.0, z), name=f"roadplate-{plates}"))
            plates += 1
        else:
            m = g.box("patch", (0, STREET_TOP + 0.0005, 0), (sx, 0.007, sz), "concrete_dark")
            parts.append(g.transformed(m, yaw, (x, 0.0, z), name=f"patch-{patches:02d}"))
            patches += 1
    return parts


def _crack_strip(name: str, points: list[tuple[float, float]], y: float, width: float, material: str) -> g.MeshData:
    b = g.GridBuilder()
    n = len(points)
    left, right = [], []
    for k, (x, z) in enumerate(points):
        ax, az = points[max(k - 1, 0)]
        bx, bz = points[min(k + 1, n - 1)]
        dx, dz = bx - ax, bz - az
        length = math.hypot(dx, dz) or 1.0
        taper = math.sin(math.pi * (k + 0.5) / n) * 0.8 + 0.2
        hw = width / 2 * taper
        px, pz = -dz / length * hw, dx / length * hw
        left.append((x + px, y, z + pz))
        right.append((x - px, y, z - pz))
    tops = [[left[k], left[k + 1], right[k + 1], right[k]] for k in range(n - 1)]
    return _extrude_down(name, tops, DECAL_DEPTH, material)


DECAL_DEPTH = 0.006


def _extrude_down(name: str, tops: Sequence[Sequence[Sequence[float]]], depth: float, material: str) -> g.MeshData:
    """Closed thin shell under flat top polygons: +Y tops, -Y bottoms, outward side walls.

    Generators author outward/CCW winding in Resonite space (R11); the side wall for every
    boundary edge a->b of the top is (b, a, a_down, b_down), so the shell is edge-consistent
    and has positive signed volume.
    """
    b = g.GridBuilder()
    top_faces = []
    for poly in tops:
        pts = [tuple(float(c) for c in p) for p in poly]
        if _face_normal(pts)[1] < 0:  # type: ignore[arg-type]
            pts.reverse()
        top_faces.append(tuple(b.v(p) for p in pts))
    b.faces.extend(top_faces)
    directed = {(f[i], f[(i + 1) % len(f)]) for f in top_faces for i in range(len(f))}
    boundary = [(x, y) for x, y in directed if (y, x) not in directed]
    for f in top_faces:
        b.faces.append(tuple(b.v(_down(b.vertices[i], depth)) for i in reversed(f)))
    for x, y in sorted(boundary):
        px, py = b.vertices[x], b.vertices[y]
        b.faces.append((y, x, b.v(_down(px, depth)), b.v(_down(py, depth))))
    return b.build(name, material)


def _down(p: Sequence[float], depth: float = DECAL_DEPTH) -> tuple[float, float, float]:
    return (p[0], p[1] - depth, p[2])


def _decal_polygon(name: str, outline: Sequence[Sequence[float]], material: str) -> g.MeshData:
    """Closed thin slab from a flat outline (top face +Y)."""
    return _extrude_down(name, [outline], DECAL_DEPTH, material)


def _cracks(streets: list[Rect], blockers: list[Rect], rng: random.Random) -> list[g.MeshData]:
    parts = []
    # Tar-sealed asphalt cracks, mostly following the street direction.
    for k in range(60):
        p = _street_point(rng, streets, 0.4)
        if p is None or _in_rect(*p, PLAZA_RECT, 0.3):
            continue
        r = next(s for s in streets if _in_rect(*p, s))
        heading = 0.0 if (r[2] - r[0]) >= (r[3] - r[1]) else math.pi / 2
        heading += rng.uniform(-0.6, 0.6) + (math.pi if rng.random() < 0.5 else 0.0)
        pts = [p]
        for _ in range(rng.randint(6, 16)):
            heading += rng.uniform(-0.55, 0.55)
            step = rng.uniform(0.35, 0.8)
            nxt = (pts[-1][0] + math.cos(heading) * step, pts[-1][1] + math.sin(heading) * step)
            if not _in_rect(*nxt, r, -0.25) or _in_rect(*nxt, PLAZA_RECT, 0.3):
                break
            pts.append(nxt)
        if len(pts) >= 4:
            parts.append(_crack_strip(f"crack-{k:02d}", pts, STREET_TOP + 0.003, rng.uniform(0.02, 0.045), "rubber"))
    # Dirt-filled cracks in the block concrete.
    for k in range(60):
        x, z = rng.uniform(-38, 38), rng.uniform(-38, 38)
        if _on_street(x, z, streets) or any(_in_rect(x, z, b, 0.3) for b in blockers):
            continue
        heading = rng.uniform(0, math.tau)
        pts = [(x, z)]
        for _ in range(rng.randint(5, 12)):
            heading += rng.uniform(-0.7, 0.7)
            step = rng.uniform(0.3, 0.7)
            nxt = (pts[-1][0] + math.cos(heading) * step, pts[-1][1] + math.sin(heading) * step)
            if _on_street(*nxt, streets) or abs(nxt[0]) > 39 or abs(nxt[1]) > 39 or any(_in_rect(*nxt, b, 0.1) for b in blockers):
                break
            pts.append(nxt)
        if len(pts) >= 4:
            parts.append(_crack_strip(f"crack-c{k:02d}", pts, GROUND_TOP + 0.003, rng.uniform(0.03, 0.06), "mud"))
    return parts


def _wall_corners(data: dict[str, Any], streets: list[Rect], blockers: list[Rect]) -> list[tuple[float, float, float, float]]:
    """Tower footprint corners on open ground: (x, z, outward_x, outward_z) diagonals."""
    out = []
    for t in data["towers"]:
        cx, cz = t["center"]
        for x, z in _tower_corners(t):
            dx, dz = x - cx, z - cz
            n = math.hypot(dx, dz)
            ox, oz = dx / n, dz / n
            px, pz = x + ox * 0.6, z + oz * 0.6
            if abs(px) > 39 or abs(pz) > 39 or _in_rect(px, pz, PLAZA_RECT, 0.5):
                continue
            if any(_in_rect(px, pz, b, 0.05) for b in blockers):
                continue
            out.append((x, z, ox, oz))
    return out


def _litter(data: dict[str, Any], streets: list[Rect], blockers: list[Rect], rng: random.Random):
    """40 scraps clustered along the foot of tower walls (within 0.3 m), plus mud drifts at corners."""
    corners = _wall_corners(data, streets, blockers)
    rng.shuffle(corners)
    parts: list[g.MeshData] = []
    mud: list[g.MeshData] = []
    # Clusters of 3-5 scraps start at a corner and trail along one of its two walls.
    ci = 0
    while len(parts) < 40 and ci < len(corners) * 4:
        x, z, ox, oz = corners[ci % len(corners)]
        ci += 1
        along = (1.0, 0.0) if rng.random() < 0.5 else (0.0, 1.0)
        sx = -math.copysign(1, ox) if along[0] else 0.0
        sz = -math.copysign(1, oz) if along[1] else 0.0
        if ci <= len(corners) and len(mud) < 10:
            poly = _octagon(rng, x + ox * 0.5, z + oz * 0.5, rng.uniform(0.7, 1.3), 0.35)
            y = top_at(x + ox * 0.5, z + oz * 0.5, streets) + 0.0025
            mud.append(_decal_polygon(f"mud-{len(mud):02d}", [(px, y, pz) for px, pz in poly], "mud"))
        for _ in range(rng.randint(3, 5)):
            if len(parts) >= 40:
                break
            d = rng.uniform(0.1, 3.0)
            wall_off = rng.uniform(0.08, 0.28)
            # Slide along the wall and keep within 0.3 m of it on the outside.
            if along[0]:
                px, pz = x + sx * d, z + math.copysign(wall_off, oz)
            else:
                px, pz = x + math.copysign(wall_off, ox), z + sz * d
            if abs(px) > 39.5 or abs(pz) > 39.5 or any(_in_rect(px, pz, b, -0.02) for b in blockers):
                continue
            w, dd = rng.uniform(0.1, 0.4), rng.uniform(0.1, 0.4)
            h = rng.uniform(0.004, 0.012) if rng.random() < 0.55 else rng.uniform(0.04, 0.16)
            mat = rng.choice(LITTER_MATERIALS)
            y = top_at(px, pz, streets)
            piece = g.box("scrap", (0, h / 2, 0), (w, h, dd), mat)
            tilt_x = math.radians(rng.uniform(-6, 6)) if h > 0.03 else 0.0
            piece = g.transformed_xyz(piece, tilt_x, rng.uniform(0, math.tau), 0.0, (px, y - 0.004, pz),
                                      name=f"litter-{len(parts):02d}")
            parts.append(piece)
    return parts, mud


# --------------------------------------------------------------------------- dirt masks


def _wall_grime(data: dict[str, Any], streets: list[Rect]) -> list[Spray]:
    out = []
    for t in data["towers"]:
        corners = _tower_corners(t)
        for (ax, az), (bx, bz) in zip(corners, corners[1:] + corners[:1]):
            length = math.hypot(bx - ax, bz - az)
            n = max(1, int(length / 2.2))
            for k in range(n + 1):
                x, z = ax + (bx - ax) * k / n, az + (bz - az) * k / n
                if abs(x) > HALF or abs(z) > HALF:
                    continue
                out.append(Spray((x, GROUND_TOP, z), 1.7, (0.58, 0.54, 0.49), 0.6))
    return out


def _gutter_grime(points: list[tuple[float, float]]) -> list[Spray]:
    return [Spray((x, STREET_TOP, z), 1.15, (0.68, 0.64, 0.6), 0.5) for x, z in points]


def _oil_stains(streets: list[Rect], rng: random.Random) -> list[Spray]:
    out = []
    while len(out) < 22:
        p = _street_point(rng, streets, 0.6)
        if p is None or _in_rect(*p, PLAZA_RECT, 0.5):
            continue
        out.append(Spray((p[0], STREET_TOP, p[1]), rng.uniform(0.9, 1.6), (0.5, 0.5, 0.54), rng.uniform(0.5, 0.85)))
    return out


def _dust(streets: list[Rect], rng: random.Random) -> list[Spray]:
    """Sun-bleached, dusty asphalt: broad lighter patches so the road is not one flat tone."""
    out = []
    while len(out) < 70:
        p = _street_point(rng, streets, 0.0)
        if p is None or _in_rect(*p, PLAZA_RECT, -0.5):
            continue
        out.append(Spray((p[0], STREET_TOP, p[1]), rng.uniform(1.6, 3.5), (1.3, 1.27, 1.2), rng.uniform(0.5, 0.95)))
    return out


def _block_stains(streets: list[Rect], blockers: list[Rect], rng: random.Random) -> list[Spray]:
    """Damp, dirt-darkened patches on open block concrete (where water stands and dust settles)."""
    out = []
    tries = 0
    while len(out) < 60 and tries < 5000:
        tries += 1
        x, z = rng.uniform(-39, 39), rng.uniform(-39, 39)
        if _on_street(x, z, streets) or any(_in_rect(x, z, b) for b in blockers):
            continue
        out.append(Spray((x, GROUND_TOP, z), rng.uniform(1.5, 3.5), (0.72, 0.68, 0.62), rng.uniform(0.45, 0.85)))
    return out


# --------------------------------------------------------------------------- ground sector


def _assembly(name: str, parts: list[g.MeshData], kind: str, sector: str, **meta: Any) -> g.Assembly:
    return g.Assembly(kind, name, sector, (0.0, 0.0, 0.0), parts, dict(meta))


@register("ground")
def ground_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    streets = _street_rects(data)
    blockers = _blockers(data)
    tower_rects = [_aabb(t) for t in data["towers"]]
    pits = [tuple(p) for p in data.get("plaza_features", {}).get("pits", [])]
    base = _base_parts(streets, pits)
    curbs, grates, gutter = _curbs_and_grates(streets, tower_rects, random.Random(SEED + 101))
    manholes, avoid, rust = _manholes(data, random.Random(SEED + 102))
    puddles, halos = _puddles(streets, avoid, random.Random(SEED + 103))
    cracks = _cracks(streets, blockers, random.Random(SEED + 104))
    patches = _patches(streets, avoid, random.Random(SEED + 107))
    litter, mud = _litter(data, streets, blockers, random.Random(SEED + 105))
    sprays = [*_dust(streets, random.Random(SEED + 108)), *_block_stains(streets, blockers, random.Random(SEED + 109)), *_wall_grime(data, streets), *_gutter_grime(gutter), *_oil_stains(streets, random.Random(SEED + 106)),
              *halos, *rust]
    return [
        _assembly("ground-base", base, "ground", "ground", sprays=tuple(sprays)),
        _assembly("ground-curbs", curbs, "curbs", "ground", sprays=tuple(_wall_grime(data, streets))),
        _assembly("ground-puddles", puddles, "puddles", "ground"),
        _assembly("ground-details", [*manholes, *grates, *patches, *cracks, *mud, *litter], "details", "ground",
                  sprays=tuple(rust)),
    ]


# --------------------------------------------------------------------------- backdrop sector


def _ring_parts() -> list[g.MeshData]:
    inner: list[tuple[float, float]] = []
    step = 8 * HALF / RING_SEGMENTS
    for k in range(RING_SEGMENTS):
        s = k * step                      # distance along the square perimeter from (40, -40), CCW
        side, t = divmod(s, 2 * HALF)
        if side == 0:
            inner.append((HALF, -HALF + t))
        elif side == 1:
            inner.append((HALF - t, HALF))
        elif side == 2:
            inner.append((-HALF, HALF - t))
        else:
            inner.append((-HALF + t, -HALF))
    radius = 220.0
    outer = [(math.cos(math.atan2(z, x)) * radius, math.sin(math.atan2(z, x)) * radius) for x, z in inner]
    verts = [(x, BACKDROP_TOP, z) for x, z in inner] + [(x, BACKDROP_TOP, z) for x, z in outer]
    faces = []
    for k in range(RING_SEGMENTS):
        q = (k, (k + 1) % RING_SEGMENTS, RING_SEGMENTS + (k + 1) % RING_SEGMENTS, RING_SEGMENTS + k)
        if _face_normal([verts[i] for i in q])[1] < 0:
            q = tuple(reversed(q))
        faces.append(q)
    # Close the annulus (bottom, inner and outer walls) as an outward shell (R11).
    n = len(verts)
    verts += [(x, BACKDROP_TOP - 0.1, z) for x, y, z in verts]
    for k in range(RING_SEGMENTS):
        a, b = k, (k + 1) % RING_SEGMENTS
        faces.append(tuple(reversed(tuple(i + n for i in faces[k]))))
        faces.append((a, a + n, b + n, b))
        faces.append((RING_SEGMENTS + a, RING_SEGMENTS + b, RING_SEGMENTS + b + n, RING_SEGMENTS + a + n))
    return [g.mesh("ring", verts, faces, "backdrop_ground")]


def _facing_sides(cx: float, cz: float) -> list[tuple[int, int]]:
    """The two axis sides (axis index 0=x / 2=z, sign) whose outward normals face the origin most."""
    sides = [(0, 1), (0, -1), (2, 1), (2, -1)]
    to_c = {0: -cx, 2: -cz}
    return sorted(sides, key=lambda s: -(s[1] * to_c[s[0]]))[:2]


def _mass_parts(m: dict[str, Any], rng: random.Random, holo: str | None) -> list[g.MeshData]:
    cx, cz = m["center"]
    w, d = m["footprint"]
    h = m["height"]
    parts: list[g.MeshData] = []
    tiers = []
    base_y = -1.0
    # Three set-back tiers; upper tiers slide toward a random corner so the silhouette is asymmetric.
    shift = (rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12))
    for k, (scale, frac) in enumerate(((1.0, 0.55), (0.8, 0.30), (0.55, 0.15))):
        tw, td = w * scale, d * scale
        tx = cx + (w - tw) * shift[0] * k
        tz = cz + (d - td) * shift[1] * k
        top = base_y + h * frac + (1.0 if k == 0 else 0.0)
        parts.append(g.box(f"tier-{k}", (tx, (base_y + top) / 2, tz), (tw, top - base_y, td), "backdrop_mass"))
        tiers.append((tx, tz, tw, td, base_y, top))
        base_y = top
    # Break the stacked-box read: mechanical-floor ledges that cast horizontal shadow lines,
    # a lower annex slab on one flank and a service core running up the back side.
    for k, (tx, tz, tw, td, y0, y1) in enumerate(tiers[:2]):
        ly = y1 - rng.uniform(0.5, 1.5)
        parts.append(g.box(f"ledge-{k}", (tx, ly, tz), (tw + 2.4, 1.2, td + 2.4), "backdrop_mass"))
        if y1 - y0 > 40:
            my = y0 + (y1 - y0) * rng.uniform(0.4, 0.6)
            parts.append(g.box(f"ledge-{k}m", (tx, my, tz), (tw + 1.6, 0.9, td + 1.6), "backdrop_mass"))
    facing = _facing_sides(cx, cz)
    # The two facing sides use different axes; the annex and core sit on the two hidden sides.
    (side_axis, side_sign), (back_axis, back_sign) = [(ax_, -sg) for ax_, sg in facing]
    tx, tz, tw, td, y0, y1 = tiers[0]
    ah = h * rng.uniform(0.3, 0.45)
    aw, ad = (rng.uniform(8, 14), td * rng.uniform(0.5, 0.8)) if side_axis == 0 else (tw * rng.uniform(0.5, 0.8), rng.uniform(8, 14))
    ax = tx + (side_sign * (tw / 2 + aw / 2 - 0.5) if side_axis == 0 else rng.uniform(-(tw - aw) / 2, (tw - aw) / 2))
    az = tz + (side_sign * (td / 2 + ad / 2 - 0.5) if side_axis == 2 else rng.uniform(-(td - ad) / 2, (td - ad) / 2))
    parts.append(g.box("annex", (ax, ah / 2 - 1.0, az), (aw, ah, ad), "backdrop_mass"))
    ctop = tiers[1][5] + rng.uniform(4, 12)
    cw = rng.uniform(5, 9)
    if back_axis == 0:
        cc, cs = (tx + back_sign * (tw * 0.8 / 2 + 1.0), ctop / 2 - 1.0, tz), (4.0, ctop + 2.0, cw)
    else:
        cc, cs = (tx, ctop / 2 - 1.0, tz + back_sign * (td * 0.8 / 2 + 1.0)), (cw, ctop + 2.0, 4.0)
    parts.append(g.box("core", cc, cs, "backdrop_mass"))
    # Roof clutter and a mast on the crown for a broken skyline.
    tx, tz, tw, td, _, top = tiers[-1]
    for k in range(rng.randint(2, 4)):
        bw, bd, bh = rng.uniform(2, tw * 0.35), rng.uniform(2, td * 0.35), rng.uniform(2, 7)
        bx = tx + rng.uniform(-(tw - bw) / 2, (tw - bw) / 2)
        bz = tz + rng.uniform(-(td - bd) / 2, (td - bd) / 2)
        parts.append(g.box(f"roof-{k}", (bx, top + bh / 2, bz), (bw, bh, bd), "backdrop_mass"))
    mast_h = rng.uniform(10, 28)
    mx, mz = tx + rng.uniform(-tw * 0.25, tw * 0.25), tz + rng.uniform(-td * 0.25, td * 0.25)
    parts.append(g.box("mast", (mx, top + mast_h / 2, mz), (0.8, mast_h, 0.8), "steel_dark"))
    parts.append(g.box("light-mast", (mx, top + mast_h + 0.6, mz), (1.2, 1.2, 1.2), "neon_red"))
    # Aviation lights on crown corners (2-4 including the mast tip).
    corners = [(tx + sx * (tw / 2 - 0.8), tz + sz * (td / 2 - 0.8)) for sx in (-1, 1) for sz in (-1, 1)]
    rng.shuffle(corners)
    for k, (lx, lz) in enumerate(corners[: rng.randint(1, 3)]):
        parts.append(g.box(f"light-{k}", (lx, top + 0.7, lz), (1.2, 1.4, 1.2), "neon_red"))
    # Lit window bands on the two centre-facing sides of every tier.
    for axis, sign in _facing_sides(cx, cz):
        for ti, (tx, tz, tw, td, y0, y1) in enumerate(tiers):
            face_len = td if axis == 0 else tw
            face_pos = (tx if axis == 0 else tz) + sign * ((tw if axis == 0 else td) / 2 + 0.05)
            along_c = tz if axis == 0 else tx
            # Below ~24 m the site towers (24-44 m, 33-40 m away) hide the masses from street level.
            y = max(y0 + 3.0, WINDOW_MIN_Y)
            while y + 1.4 < y1 - 1.5:
                band_h = rng.uniform(0.9, 1.4)
                s = -face_len / 2 + 1.0
                while s < face_len / 2 - 1.5:
                    seg = rng.uniform(5.0, 18.0)
                    e = min(s + seg, face_len / 2 - 1.0)
                    if rng.random() < 0.55 and e - s > 1.0:
                        # 0.05 m thick band floating 0.05 m off the facade (closed outward box).
                        mid, length = along_c + (s + e) / 2, e - s
                        off = face_pos + sign * 0.025
                        if axis == 0:
                            centre, size = (off, y + band_h / 2, mid), (0.05, band_h, length)
                        else:
                            centre, size = (mid, y + band_h / 2, off), (length, band_h, 0.05)
                        parts.append(g.box(f"win-{ti}", centre, size, "window_lit"))
                    s = e + rng.uniform(1.0, 5.0)
                y += 4.0
    if holo:
        axis, sign = _facing_sides(cx, cz)[0]
        # From street level the site towers (<= ~44 m at 33-40 m) hide roughly everything below
        # y ~= horizontal distance, so the billboard goes above that line, on the tier it fits.
        ph = rng.uniform(26, 40)
        dist = math.hypot(cx, cz) - max(w, d) / 2
        want = dist + ph / 2 + rng.uniform(2, 10)
        fits = [t for t in tiers if t[5] - t[4] >= ph + 6]
        tier = next((t for t in fits if t[4] + ph / 2 + 3 <= want <= t[5] - ph / 2 - 3), None) or max(fits, key=lambda t: t[5])
        tx, tz, tw, td, y0, y1 = tier
        py = min(max(want, y0 + ph / 2 + 3), y1 - ph / 2 - 3)
        face_len = td if axis == 0 else tw
        pw = face_len * rng.uniform(0.45, 0.6)
        off = (tw if axis == 0 else td) / 2
        along = rng.uniform(-(face_len - pw) / 2, (face_len - pw) / 2) * 0.6
        if axis == 0:
            frame_c = (tx + sign * (off + 0.6), py, tz + along)
            panel_c = (tx + sign * (off + 1.1), py, tz + along)
            fsize, psize = (1.0, ph + 2, pw + 2), (0.2, ph, pw)
        else:
            frame_c = (tx + along, py, tz + sign * (off + 0.6))
            panel_c = (tx + along, py, tz + sign * (off + 1.1))
            fsize, psize = (pw + 2, ph + 2, 1.0), (pw, ph, 0.2)
        parts.append(g.box("holo-frame", frame_c, fsize, "steel_dark"))
        parts.append(g.box("holo-panel", panel_c, psize, holo))
    return parts


@register("backdrop")
def backdrop_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    masses = data["backdrop"]["masses"]
    # The three tallest masses carry giant holo billboards (most visible over the roofs).
    tallest = sorted(masses, key=lambda m: -m["height"])[:3]
    holos = {tallest[0]["id"]: "holo_magenta", tallest[1]["id"]: "holo_cyan", tallest[2]["id"]: "holo_magenta"}
    out = [_assembly("backdrop-ground", _ring_parts(), "backdrop-ground", "backdrop", uv_exempt=True)]
    for k, m in enumerate(masses, start=1):
        parts = _mass_parts(m, random.Random(m["seed"]), holos.get(m["id"]))
        out.append(_assembly(f"backdrop-mass-{k:02d}", parts, "backdrop-mass", "backdrop"))
    return out
