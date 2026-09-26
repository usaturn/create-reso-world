"""Junk-market stalls along the southern lane (sector ``market``).

Each layout stall becomes one object: steel-pipe posts (4 or 6), a roof that is either
a sagging tarp (6 x 4 grid, roped edges) or two sloped corrugated sheets held down by
tyres, a plywood counter on stacked plastic crates, back/side steel shelves with 2-3
levels, at least a dozen readable goods (circuit boards, CRT monitors, cable coils,
prosthetic limbs, batteries, parts bins), 2-3 hanging bulbs and a sign board whose
TextRenderer anchor is stored in ``meta["sign_anchor"]``. Six junk piles sit in the
gaps between the stall rows, off the lane.

Pure Python and deterministic (``random.Random(spec["seed"])`` per stall).
Local frame: +Z faces the spec's ``front`` (the lane), X runs along the counter; parts
are baked into the spec yaw, so the assembly origin is ``(cx, 0, cz)`` and
``sign_anchor`` is in that same origin-relative, yaw-baked frame (like towers).
R11: every part is a closed outward shell, including the tarp and the sign board
(thin shells via ``geometry.thick_sheet``) so they read from below and behind.
Only the roof (eave, ropes, tyres) may overhang the lane, by at most ``EAVE`` metres.
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

Vec = tuple[float, float, float]
Item = tuple[str, list[g.MeshData], float]      # (kind, meshes with base at y=0, footprint width along x)

EAVE = 0.3              # roof overhang past the plot front edge towards the lane (limit 0.4)
POST_R = 0.035
POST_INSET = 0.08
COUNTER_TOP = 0.9
CORR_AMP = 0.028        # corrugation ridge height above the valley
CORR_LAP = 0.03         # the second corrugated sheet laps 3 cm above the first
MAX_PER_LEVEL = 6       # goods per back-shelf level, leaves gaps so single items read
SIGN_UP = 0.3           # sign anchor height above the roof front edge (layout ``_signs``)
TARPS = ("tarp_blue", "tarp_orange", "tarp_green")
PANEL_MATS = ("plywood", "corrugated_rust", "pallet_wood")

# (centre xz, radius) of the six junk piles: row gaps either side of radial-s0/s1, the
# south-west corner by tower-21 and the open north-east end of the north row.
JUNK_SITES: tuple[tuple[tuple[float, float], float], ...] = (
    ((-6.0, -15.3), 0.9), ((3.0, -15.3), 0.8), ((-6.5, -20.6), 0.9),
    ((-14.3, -20.5), 0.75), ((14.6, -15.4), 1.0), ((19.5, -15.3), 1.0),
)


def _place(meshes: Sequence[g.MeshData], yaw: float, offset: Vec) -> list[g.MeshData]:
    return [g.transformed(m, yaw, offset) for m in meshes]


def _named(meshes: Sequence[g.MeshData], prefix: str) -> list[g.MeshData]:
    return [g.MeshData(f"{prefix}-{m.name}", m.vertices, m.faces, m.material) for m in meshes]


def _coil(name: str, radius: float, turns: float, pitch: float, wire: float, material: str) -> g.MeshData:
    """Loose cable coil: a flat helix around local Z, centred on the origin."""
    n = max(8, round(turns * 8))
    pts = [(radius * math.cos(math.tau * turns * k / n), radius * math.sin(math.tau * turns * k / n),
            pitch * turns * (k / n - 0.5)) for k in range(n + 1)]
    return g.tube(name, pts, wire, 5, material)


# --------------------------------------------------------------------------- goods (base at y = 0, face +Z)


def _board(rng: random.Random) -> Item:
    w, d = rng.uniform(0.2, 0.3), rng.uniform(0.14, 0.2)
    tilt = rng.uniform(0.2, 0.35)                                       # leans back against the shelf
    board = g.box("board", (0.0, d / 2, 0.0), (w, d, 0.012), "electronics")
    chips = [g.box(f"c{k}", (rng.uniform(-w / 3, w / 3), rng.uniform(0.25, 0.75) * d, 0.012),
                   (rng.uniform(0.025, 0.05), rng.uniform(0.02, 0.04), 0.012), "rubber") for k in range(3)]
    parts = [board, g.combine("chips", chips, "rubber")]
    return "board", [g.transformed_xyz(m, -tilt, 0.0, 0.0, (0.0, 0.0, 0.0)) for m in parts], w


def _board_stack(rng: random.Random) -> Item:
    boards = []
    for k in range(3):
        w, d = rng.uniform(0.22, 0.3), rng.uniform(0.15, 0.2)
        boards.append(g.transformed(g.box(f"b{k}", (0.0, 0.006 + 0.013 * k, 0.0), (w, 0.012, d), "electronics"),
                                    rng.uniform(-0.4, 0.4), (0.0, 0.0, 0.0)))
    return "boards", [g.combine("boards", boards, "electronics")], 0.34


def _crt(rng: random.Random) -> Item:
    s = rng.uniform(0.3, 0.4)
    case = g.combine("case", [g.beveled_box("front", (0.0, s * 0.45, 0.0), (s, s * 0.9, s * 0.55), 0.02, "steel_dark"),
                              g.beveled_box("back", (0.0, s * 0.42, -s * 0.4), (s * 0.7, s * 0.66, s * 0.3), 0.02,
                                            "steel_dark")])
    screen = g.box("screen", (0.0, s * 0.47, s * 0.275 + 0.004), (s * 0.74, s * 0.6, 0.012), "glass_dark")
    return "crt", [case, screen], s


def _battery(rng: random.Random) -> Item:
    w, h, d = rng.uniform(0.18, 0.26), rng.uniform(0.15, 0.2), rng.uniform(0.12, 0.17)
    body = g.beveled_box("body", (0.0, h / 2, 0.0), (w, h, d), 0.012, "paint_yellow_faded")
    terms = g.combine("terminals", [g.cylinder(f"t{k}", (sx * w * 0.3, h + 0.012, 0.0), 0.014, 0.024, 6, "steel_bare")
                                    for k, sx in enumerate((-1, 1))], "steel_bare")
    return "battery", [body, terms], w


def _battery_row(rng: random.Random) -> Item:
    cells = [g.box(f"b{k}", (-0.15 + 0.1 * k, 0.07, 0.0), (0.085, 0.14, 0.13), "paint_yellow_faded") for k in range(4)]
    return "cells", [g.combine("cells", cells, "paint_yellow_faded")], 0.42


def _parts_bin(rng: random.Random) -> Item:
    w, h, d = rng.uniform(0.28, 0.36), 0.12, rng.uniform(0.2, 0.26)
    t = 0.012
    walls = [g.box("floor", (0.0, t / 2, 0.0), (w, t, d), "plastic_crate"),
             g.box("wf", (0.0, h / 2, d / 2 - t / 2), (w, h, t), "plastic_crate"),
             g.box("wb", (0.0, h / 2, -d / 2 + t / 2), (w, h, t), "plastic_crate"),
             g.box("wl", (-w / 2 + t / 2, h / 2, 0.0), (t, h, d - 2 * t), "plastic_crate"),
             g.box("wr", (w / 2 - t / 2, h / 2, 0.0), (t, h, d - 2 * t), "plastic_crate")]
    bits = [g.transformed(g.box(f"bit{k}", (0.0, 0.0, 0.0), (rng.uniform(0.03, 0.07), 0.04, rng.uniform(0.02, 0.05)),
                                "steel_bare"), rng.uniform(0, math.pi),
                          (rng.uniform(-w / 3, w / 3), h - 0.015 + rng.uniform(0.0, 0.02), rng.uniform(-d / 3, d / 3)))
            for k in range(4)]
    return "bin", [g.combine("bin", walls, "plastic_crate"), g.combine("bits", bits, "steel_bare")], w


def _arm(rng: random.Random, hanging: bool = False) -> Item:
    """Prosthetic arm lying along X: steel limb segments, elbow/shoulder joints, a hydraulic
    strut, a flat palm with jointed fingers and cut cables trailing from the shoulder socket."""
    bend = rng.uniform(0.3, 0.7)
    r = 0.035
    y = r * 1.5                                                       # shoulder cap rests on the surface
    shoulder = (-0.3, y, 0.0)
    elbow = (0.0, y, 0.0)
    wrist = (0.28 * math.cos(bend), y, 0.28 * math.sin(bend))
    hand_dir = g.norm(g.sub(wrist, elbow))
    side = (hand_dir[2], 0.0, -hand_dir[0])
    palm_end = tuple(wrist[k] + hand_dir[k] * 0.1 for k in range(3))

    def at(p: Sequence[float], along: float, across: float, up: float = 0.0) -> Vec:
        return tuple(p[k] + hand_dir[k] * along + side[k] * across + (up if k == 1 else 0.0) for k in range(3))  # type: ignore[return-value]

    segs = [g.pipe("upper", shoulder, elbow, r, "steel_bare", 6),
            g.pipe("fore", elbow, wrist, r * 0.8, "steel_bare", 6),
            g.cylinder("shoulder", shoulder, r * 1.5, r * 2.4, 8, "steel_bare", "Z"),
            g.cylinder("elbow", elbow, r * 1.25, r * 2.2, 8, "steel_bare", "Z"),
            g.cylinder("wrist", wrist, r * 0.95, r * 1.6, 8, "steel_bare", "Z"),
            g.beam("palm", wrist, palm_end, 0.022, 0.085, "steel_bare")]
    for k in range(4):
        base = at(palm_end, -0.005, (k - 1.5) * 0.021)
        knuckle = at(base, 0.045, 0.0, -0.004)
        segs.append(g.pipe(f"finger{k}a", base, knuckle, 0.008, "steel_bare", 5))
        segs.append(g.pipe(f"finger{k}b", knuckle, at(knuckle, 0.035, 0.0, -0.012), 0.007, "steel_bare", 5))
    thumb0 = at(wrist, 0.04, 0.045)
    segs.append(g.pipe("thumb", thumb0, at(thumb0, 0.04, 0.03, -0.006), 0.009, "steel_bare", 5))
    strut = [g.pipe("strut", (-0.2, y + r + 0.012, 0.0), (0.0, y + r + 0.012, 0.0), 0.011, "steel_dark", 6),
             g.pipe("rod", (0.0, y + r + 0.012, 0.0), at(elbow, 0.12, 0.0, r + 0.01), 0.007, "steel_dark", 6)]
    wires = [g.tube(f"w{k}", [(-0.3 - r * 1.2, y + dy, dz), (-0.38, y + dy * 0.5, dz * 1.8),
                             (-0.45, max(0.012, y - 0.03 + dy), dz * 2.6)], 0.006, 5, "rubber")
             for k, (dy, dz) in enumerate(((0.012, -0.015), (-0.008, 0.0), (0.01, 0.018)))]
    meshes = [g.combine("arm", segs, "steel_bare"), g.combine("strut", strut, "steel_dark"),
              g.combine("wires", wires, "rubber")]
    if hanging:   # shoulder up, hung from a hook: rotate so the arm points down
        meshes = [g.transformed_xyz(m, 0.0, 0.0, -math.pi / 2 + 0.1, (0.0, 0.0, 0.0)) for m in meshes]
    return "arm", meshes, 0.8


def _coil_item(rng: random.Random) -> Item:
    rad = rng.uniform(0.09, 0.13)
    coil = _coil("coil", rad, rng.uniform(2.0, 2.6), 0.03, 0.012, "rubber")
    return "coil", [g.transformed_xyz(coil, -math.pi / 2, 0.0, 0.0, (0.0, 0.03, 0.0))], 2 * rad + 0.03


GOODS: dict[str, Callable[[random.Random], Item]] = {
    "board": _board, "boards": _board_stack, "crt": _crt, "battery": _battery, "cells": _battery_row,
    "bin": _parts_bin, "arm": _arm, "coil": _coil_item,
}
# Shelf fill weights per shop theme (the sign texts in layout: junk, used cyberware, boards, repair,
# batteries, cable by weight) — every stall still carries one of each kind so every shelf reads.
THEMES: tuple[dict[str, float], ...] = (
    {"crt": 3, "board": 2, "bin": 2, "battery": 1, "boards": 1, "cells": 1},
    {"arm": 1, "bin": 3, "board": 1, "crt": 1, "battery": 1},
    {"board": 3, "boards": 2, "bin": 2, "crt": 1},
    {"crt": 3, "bin": 2, "board": 2, "battery": 1},
    {"battery": 2, "cells": 3, "bin": 1, "board": 1},
    {"bin": 2, "coil": 2, "board": 1, "crt": 1, "cells": 1},
)
REQUIRED = ("board", "crt", "battery", "bin")


# --------------------------------------------------------------------------- stall


def _stall_parts(spec: dict, rng: random.Random) -> tuple[list[g.MeshData], dict[str, Any], list[tuple[str, Vec, float, tuple]]]:
    """Parts in the unrotated local frame + meta + local sprays (name, centre, radius, (colour, strength, mats))."""
    w, d = spec["size"]
    hx, hz = w / 2, d / 2
    H = float(spec["height"])
    index = int(spec["id"].split("-")[-1])
    roof_kind = "tarp" if index % 2 == 1 else "corrugated"
    drop = rng.uniform(0.25, 0.4)
    sag = round(rng.uniform(0.12, 0.25), 3) if roof_kind == "tarp" else 0.0
    zr0, zr1 = -hz - 0.04, hz + EAVE                    # roof extent (back overhang is inside the plot slack)
    rx0, rx1 = -hx - 0.06, hx + 0.06

    def roof_y(z: float) -> float:
        return H - drop + drop * (z - zr0) / (zr1 - zr0)

    def droop(x: float, z: float) -> float:
        """Tarp sag at (x, z): sag * (1 - (2u-1)^2) * (1 - (2v-1)^2) over the roof grid."""
        u, v = (x - rx0) / (rx1 - rx0), (z - zr0) / (zr1 - zr0)
        return sag * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2)

    def under(x: float, z: float) -> float:
        """Underside of the roof skin (tarp: 2 mm above the sheet's lower face; corrugated: valley)."""
        return roof_y(z) + 0.002 - droop(x, z) if roof_kind == "tarp" else roof_y(z) - 0.006

    parts: list[g.MeshData] = []
    sprays: list[tuple[str, Vec, float, tuple]] = []

    # ---- posts (4 or 6) reach the roof skin; the rails run just below it, so a sagging tarp
    # drapes over the frame instead of being pierced by it
    xs = (-hx + POST_INSET, 0.0, hx - POST_INSET) if w > 3.5 else (-hx + POST_INSET, hx - POST_INSET)
    zf, zb = hz - POST_INSET, -hz + POST_INSET
    feet: dict[tuple[int, str], tuple[float, float]] = {}
    n = 0
    for side, z in (("f", zf), ("b", zb)):
        for i, x in enumerate(xs):
            px, pz = x + rng.uniform(-0.02, 0.02), z + rng.uniform(-0.015, 0.015)
            feet[(i, side)] = (px, pz)
            parts.append(g.pipe(f"post-{n:02d}", (x, 0.0, z), (px, under(px, pz) - 0.004, pz), POST_R, "steel_bare", 8))
            parts.append(g.box(f"footplate-{n:02d}", (x, 0.004, z), (0.14, 0.008, 0.14), "steel_dark"))
            sprays.append(("rust", (x, 0.05, z), 0.45, ((1.08, 0.58, 0.32), 0.75, ("steel_bare",))))
            n += 1

    def rail(name: str, a: tuple[float, float], b: tuple[float, float], radius: float) -> g.MeshData:
        low = min(under(a[0] + (b[0] - a[0]) * t / 8, a[1] + (b[1] - a[1]) * t / 8) for t in range(9))
        ya, yb = min(low, under(*a)) - radius - 0.004, min(low, under(*b)) - radius - 0.004
        if roof_kind == "tarp":
            ya = yb = low - radius - 0.004
        return g.pipe(name, (a[0], ya, a[1]), (b[0], yb, b[1]), radius, "steel_bare", 6)

    rails = [rail(f"rail-{side}", feet[(0, side)], feet[(len(xs) - 1, side)], 0.025) for side in ("f", "b")]
    rails += [rail(f"rail-s{i}", feet[(i, "b")], feet[(i, "f")], 0.022) for i in range(len(xs))]
    parts.append(g.combine("frame-rails", rails, "steel_bare"))
    tops = {k: (x, under(x, z) - 0.004, z) for k, (x, z) in feet.items()}

    # ---- roof
    meta: dict[str, Any] = {"roof": roof_kind}
    if roof_kind == "tarp":
        meta["sag"] = sag
        tarp_mat = TARPS[rng.randrange(len(TARPS))]
        grid = []
        for i in range(7):
            u = i / 6
            row = []
            for j in range(5):
                v = j / 4
                z = zr0 + (zr1 - zr0) * v
                y = roof_y(z) + 0.012 - sag * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2)
                row.append((rx0 + (rx1 - rx0) * u, y, z))
            grid.append(row)
        parts.append(g.thick_sheet("roof-tarp", grid, (0.0, -0.01, 0.0), tarp_mat))
        edge = ([grid[i][0] for i in range(7)] + [grid[6][j] for j in range(1, 5)]
                + [grid[i][4] for i in range(5, -1, -1)] + [grid[0][j] for j in range(3, -1, -1)])
        rope_mat = "tarp_orange" if tarp_mat != "tarp_orange" else "tarp_blue"
        ropes = [g.tube("edge", [(p[0], p[1] + 0.004, p[2]) for p in edge], 0.012, 5, rope_mat)]
        for i, side in ((0, "f"), (len(xs) - 1, "f"), (0, "b"), (len(xs) - 1, "b")):   # ties to the post tops
            corner = grid[0 if i == 0 else 6][4 if side == "f" else 0]
            ropes.append(g.tube(f"tie{i}{side}", [corner, tops[(i, side)]], 0.01, 5, rope_mat))
        parts.append(g.combine("roof-rope", ropes, rope_mat))
        cx, cz = 0.0, (zr0 + zr1) / 2
        sprays.append(("pool", (cx, roof_y(cz) - sag, cz), 0.9, ((0.62, 0.6, 0.55), 0.55, (tarp_mat,))))
        roof_mats: tuple[str, ...] = (tarp_mat,)
    else:
        mats = ("corrugated", "corrugated_rust") if rng.random() < 0.5 else ("corrugated_rust", "corrugated")
        split = rng.uniform(-0.25, 0.25)
        spans = ((rx0, split + 0.1), (split - 0.1, rx1))
        for k, ((x0, x1), mat) in enumerate(zip(spans, mats)):
            lift = 0.0 if k == 0 else CORR_LAP                    # second sheet laps over the first
            cols = []
            pitch, amp = 0.19, CORR_AMP
            steps = max(2, round((x1 - x0) / pitch)) * 4
            for c in range(steps + 1):
                x = x0 + (x1 - x0) * c / steps
                phase = c % 4
                cols.append((x, (0.0, amp, amp, 0.0)[phase]))
            grid = [[(x, roof_y(z) + dy + lift, z) for z in (zr0, zr1)] for x, dy in cols]
            parts.append(g.thick_sheet(f"roof-sheet-{k}", grid, (0.0, -0.006, 0.0), mat))
        # tyres weigh the sheets down (on the roof, over the posts). Spin about Y first, then tilt
        # about X so the tyre lies parallel to the roof pitch (rising towards +Z), then drop it until
        # its lowest point rests on the ridge envelope of the sheet underneath (lap sheet 3 cm higher).
        slope = math.atan2(drop, zr1 - zr0)

        def ridge_top(x: float, z: float) -> float:
            return roof_y(z) + CORR_AMP + (CORR_LAP if x >= split - 0.1 else 0.0)

        for k, (tx, tz) in enumerate(((rx0 + 0.45, zb + 0.35), (rx1 - 0.5, zf - 0.25), (split, 0.0))[: 2 + (w > 3.5)]):
            tyre = g.torus(f"weight-tire-{k}", (0.0, 0.0, 0.0), 0.24, 0.075, 12, 6, "rubber")
            tyre = g.transformed_xyz(g.transformed(tyre, rng.uniform(0, math.pi), (0.0, 0.0, 0.0)),
                                     -slope, 0.0, 0.0, (0.0, 0.0, 0.0))
            y = max(ridge_top(tx + v[0], tz + v[2]) - v[1] for v in tyre.vertices)
            parts.append(g.transformed(tyre, 0.0, (tx, y, tz)))
        sprays.append(("runoff", (0.0, roof_y(zr0), zr0), 1.4, ((1.05, 0.6, 0.38), 0.6, ("corrugated",))))
        roof_mats = mats

    # ---- walls: back panel and a half-height side panel on the side-shelf side
    side_sign = rng.choice((-1, 1))
    back_mat = rng.choice(PANEL_MATS)
    back_h = roof_y(zb) - 0.12
    parts.append(g.subdivided_box("wall-back", (0.0, 0.08 + (back_h - 0.08) / 2, -hz + 0.03),
                                  (w - 0.2, back_h - 0.08, 0.02), 0.5, back_mat))
    parts.append(g.subdivided_box("wall-side", (side_sign * (hx - 0.03), 0.65, -0.15),
                                  (0.02, 1.2, d - 0.55), 0.5, rng.choice(PANEL_MATS)))

    # ---- counter: plywood top at 0.9 m on stacked crates
    cw, cd = w - 0.55, 0.52
    cz = hz - 0.2 - cd / 2
    top_t = 0.035
    parts.append(g.box("counter-top", (0.0, COUNTER_TOP - top_t / 2, cz), (cw, top_t, cd), "plywood"))
    crate_h = (COUNTER_TOP - top_t) / 3
    cols_x = [-cw / 2 + 0.24, cw / 2 - 0.24] + ([0.0] if cw > 2.9 else [])
    c = 0
    for x in cols_x:
        for level in range(3):
            crate = g.beveled_box("crate", (0.0, crate_h / 2, 0.0), (0.42, crate_h - 0.004, 0.36), 0.018,
                                  "plastic_crate")
            parts.append(g.transformed(crate, rng.uniform(-0.08, 0.08),
                                       (x + rng.uniform(-0.02, 0.02), level * crate_h + 0.002, cz), f"counter-crate-{c:02d}"))
            c += 1
    sprays.append(("grime", (0.0, 0.1, cz), 1.3, ((0.5, 0.47, 0.42), 0.6, ("plastic_crate", "plywood"))))

    # ---- shelves: back unit (full width) + side unit, 2-3 levels, steel_dark
    levels = (0.32, 0.95, 1.55) if rng.random() < 0.6 else (0.42, 1.25)
    meta["shelf_levels"] = len(levels)

    def shelf(name: str, x0: float, x1: float, z0: float, z1: float) -> g.MeshData:
        pieces = [g.box(f"l{k}", ((x0 + x1) / 2, y - 0.012, (z0 + z1) / 2), (x1 - x0, 0.024, z1 - z0), "steel_dark")
                  for k, y in enumerate(levels)]
        top = levels[-1] + 0.1
        for k, (ux, uz) in enumerate(((x0, z0), (x1, z0), (x0, z1), (x1, z1))):
            pieces.append(g.box(f"u{k}", (ux + (0.015 if ux == x0 else -0.015), top / 2, uz + (0.015 if uz == z0 else -0.015)),
                                (0.03, top, 0.03), "steel_dark"))
        return g.combine(name, pieces, "steel_dark")

    sb_z0, sb_z1 = -hz + 0.06, -hz + 0.44
    sb_x0, sb_x1 = -hx + 0.18, hx - 0.18
    parts.append(shelf("shelf-back", sb_x0, sb_x1, sb_z0, sb_z1))
    ss_x0, ss_x1 = sorted((side_sign * (hx - 0.06), side_sign * (hx - 0.38)))
    ss_z0, ss_z1 = sb_z1 + 0.05, sb_z1 + 0.85
    parts.append(shelf("shelf-side", ss_x0, ss_x1, ss_z0, ss_z1))

    # ---- goods
    goods: list[g.MeshData] = []
    theme = THEMES[(index - 1) % len(THEMES)]
    kinds, weights = list(theme), [theme[k] for k in theme]
    required = list(REQUIRED)
    rng.shuffle(required)

    def put(item: Item, yaw: float, at: Vec) -> None:
        kind, meshes, _ = item
        prefix = f"goods-{len({m.name.split('-')[1] for m in goods}):02d}-{kind}"
        goods.extend(_named(_place(meshes, yaw, at), prefix))

    shelf_len = sb_x1 - sb_x0 - 0.1
    sz = (sb_z0 + sb_z1) / 2
    for y in levels:
        x, placed = sb_x0 + 0.08, 0
        while placed < MAX_PER_LEVEL:
            kind = required.pop() if required else rng.choices(kinds, weights)[0]
            item = GOODS[kind](rng)
            if x + item[2] > sb_x0 + 0.05 + shelf_len:
                if kind in REQUIRED and kind not in {m.name.split("-")[2] for m in goods}:
                    required.append(kind)
                break
            put(item, rng.uniform(-0.12, 0.12), (x + item[2] / 2, y, sz + 0.02))
            x += item[2] + rng.uniform(0.06, 0.18)
            placed += 1
    for y in levels[:2]:                                       # side unit: bins and batteries
        z = ss_z0 + 0.06
        while z < ss_z1 - 0.2:
            item = GOODS[rng.choice(("bin", "battery", "board"))](rng)
            put(item, math.pi / 2 * -side_sign + rng.uniform(-0.1, 0.1), ((ss_x0 + ss_x1) / 2, y, z + item[2] / 2))
            z += item[2] + 0.05
    # counter display: a prosthetic arm, a board stack, a lying coil
    put(_arm(rng), rng.uniform(-0.2, 0.2), (-cw / 4, COUNTER_TOP, cz))
    put(_board_stack(rng), rng.uniform(-0.3, 0.3), (cw / 4, COUNTER_TOP, cz - 0.05))
    flat = _coil("coil", 0.12, 2.2, 0.02, 0.011, "rubber")
    put(("coil", [g.transformed_xyz(flat, -math.pi / 2, 0.0, 0.0, (0.0, 0.0, 0.0))], 0.26), 0.0,
        (cw / 2 - 0.2, COUNTER_TOP + 0.035, cz + 0.08))
    # hanging from the front rail: cable coils on one side, a limb on the other
    hang_z = zf - 0.06
    rail_y = min(under(x, zf) for x in (-hx, 0.0, hx)) - 0.03
    hooks = []
    for k in range(2):
        x = -side_sign * (hx - 0.35 - 0.28 * k)
        rad = rng.uniform(0.12, 0.16)
        y = rail_y - 0.2 - rad - 0.06 * k
        coil = _coil("coil", rad, rng.uniform(2.2, 3.0), 0.035, 0.012, "rubber")
        put(("coil", [coil], 0.3), rng.uniform(-0.3, 0.3), (x, y, hang_z))
        hooks.append(g.tube(f"h{k}", [(x, rail_y, zf), (x, y + rad, hang_z)], 0.005, 5, "steel_dark"))
    arm_x = side_sign * (hx - 0.45)
    arm_top = rail_y - 0.22
    arm_item = _arm(rng, hanging=True)
    arm_hi = g.bounds(arm_item[1])[1][1]
    put(arm_item, math.pi / 2, (arm_x, arm_top - arm_hi, hang_z))
    hooks.append(g.tube("ha", [(arm_x, rail_y, zf), (arm_x, arm_top, hang_z)], 0.005, 5, "steel_dark"))
    parts.append(g.combine("hooks", hooks, "steel_dark"))
    parts.extend(goods)

    # ---- bulbs on cords from the roof frame
    n_bulbs = 3 if w > 3.5 else 2
    bz = (cz + sb_z1) / 2 + 0.1
    for k in range(n_bulbs):
        bx = -hx + w * (k + 1) / (n_bulbs + 1) + rng.uniform(-0.15, 0.15)
        top_y = under(bx, bz) + 0.004
        by = rng.uniform(2.0, 2.15)
        parts.append(g.tube(f"bulb-wire-{k}", [(bx, top_y, bz), (bx, by + 0.1, bz)], 0.006, 5, "rubber"))
        parts.append(g.cylinder(f"bulb-socket-{k}", (bx, by + 0.075, bz), 0.02, 0.05, 8, "steel_dark"))
        parts.append(g.cylinder(f"bulb-{k}", (bx, by + 0.005, bz), 0.032, 0.09, 8, "warm_bulb"))
        sprays.append(("soot", (bx, top_y, bz), 0.5, ((0.55, 0.5, 0.45), 0.6, roof_mats)))

    # ---- sign board on brackets above the front edge (TextRenderer anchor 5 cm in front of it)
    sign_mat = "paint_teal_faded" if rng.random() < 0.5 else "plywood"
    sw, sh = min(w * 0.7, 2.4), 0.5
    face_z = hz + 0.04
    board = [[(x, y, face_z) for y in (H + SIGN_UP - sh / 2, H + SIGN_UP + sh / 2)] for x in (-sw / 2, 0.0, sw / 2)]
    parts.append(g.thick_sheet("sign-board", board, (0.0, 0.0, -0.03), sign_mat))
    brackets = [g.box(f"br{k}", (sx * sw * 0.35, (roof_y(zf) + H + SIGN_UP) / 2, face_z - 0.04),
                      (0.04, H + SIGN_UP - roof_y(zf), 0.02), "steel_dark") for k, sx in enumerate((-1, 1))]
    parts.append(g.combine("sign-bracket", brackets, "steel_dark"))
    meta["sign_anchor"] = [0.0, H + SIGN_UP, hz + 0.05]
    return parts, meta, sprays


def build_stall(spec: dict) -> g.Assembly:
    """One market stall from a layout spec. Origin = (cx, 0, cz); parts carry the yaw."""
    rng = random.Random(spec["seed"])
    parts, meta, local_sprays = _stall_parts(spec, rng)
    yaw = math.radians(spec["rotation"])
    cx, cz = spec["center"]
    parts = [g.planarize(g.transformed(p, yaw, (0.0, 0.0, 0.0))) for p in parts]
    ax, ay, az = g.rotate_y(meta["sign_anchor"], yaw)
    meta["sign_anchor"] = [round(ax, 6), round(ay, 6), round(az, 6)]
    sprays = []
    for _kind, centre, radius, (color, strength, mats) in local_sprays:
        wx, wy, wz = g.rotate_y(centre, yaw)
        sprays.append(Spray((wx + cx, wy, wz + cz), radius, color, strength, materials=tuple(mats)))
    meta["sprays"] = sprays
    return g.Assembly("stall", spec["id"], "market", (float(cx), 0.0, float(cz)), parts, meta)


# --------------------------------------------------------------------------- junk piles


def build_junk_pile(center: Sequence[float], radius: float, seed: int, index: int = 1) -> g.Assembly:
    """A heap of tyres, dead casings, cable tangles and boards around ``center`` (xz), inside ``radius``."""
    rng = random.Random(seed)
    r = radius
    parts: list[g.MeshData] = []
    ring = [(r * 0.85 * (0.75 + 0.25 * rng.random()) * math.cos(math.tau * k / 9),
             r * 0.85 * (0.75 + 0.25 * rng.random()) * math.sin(math.tau * k / 9)) for k in range(9)]
    parts.append(g.fan_prism("junk-base", ring, 0.0, 0.06, "mud"))
    # tyres: a flat stack and one leaning against it
    tx, tz = rng.uniform(-0.25, 0.25) * r, rng.uniform(-0.25, 0.25) * r
    for k in range(rng.randint(2, 3)):
        t = g.torus(f"tire-{k}", (0.0, 0.0, 0.0), 0.24, 0.075, 14, 6, "rubber")
        parts.append(g.transformed(g.transformed_xyz(t, rng.uniform(-0.05, 0.05), 0.0, rng.uniform(-0.05, 0.05),
                                                     (0.0, 0.0, 0.0)), rng.uniform(0, math.pi),
                                   (tx + rng.uniform(-0.04, 0.04), 0.08 + 0.15 * k, tz + rng.uniform(-0.04, 0.04))))
    lean = g.torus("tire-lean", (0.0, 0.0, 0.0), 0.24, 0.075, 14, 6, "rubber")
    ang = rng.uniform(0, math.tau)
    parts.append(g.transformed(g.transformed_xyz(lean, 0.0, 0.0, 1.2, (0.0, 0.0, 0.0)), ang,
                               (tx + 0.3 * math.cos(ang), 0.27, tz - 0.3 * math.sin(ang))))
    # dead CRT / PC casings, tumbled
    for k in range(rng.randint(1, 2)):
        _kind, meshes, s = _crt(rng)
        a = rng.uniform(0, math.tau)
        pos = (r * 0.45 * math.cos(a), 0.04, r * 0.45 * math.sin(a))
        tilt = (rng.uniform(-0.35, 0.35), rng.uniform(0, math.tau), rng.uniform(-0.35, 0.35))
        parts.extend(g.transformed_xyz(m, *tilt, pos, f"casing-{k}-{m.name}") for m in meshes)
    parts.append(g.transformed_xyz(g.beveled_box("pc", (0.0, 0.0, 0.0), (0.2, 0.42, 0.45), 0.015, "steel_dark"),
                                   rng.uniform(1.2, 1.5), rng.uniform(0, math.tau), 0.0,
                                   (-tx * 0.8, 0.14, -tz * 0.8 + 0.1), "casing-pc"))
    # boards leaning in, a corrugated scrap and a battery
    for k in range(2):
        a = rng.uniform(0, math.tau)
        plank = g.box(f"plank-{k}", (0.0, 0.0, 0.0), (rng.uniform(0.25, 0.4), rng.uniform(0.9, 1.2), 0.02),
                      rng.choice(("plywood", "pallet_wood")))
        parts.append(g.transformed_xyz(plank, rng.uniform(0.35, 0.6), a, 0.0,
                                       (r * 0.55 * math.cos(a), 0.45, r * 0.55 * math.sin(a))))
    sheet = [[(x, 0.015 * math.cos(x * 33.0), z) for z in (-0.35, 0.35)] for x in [k * 0.05 - 0.3 for k in range(13)]]
    parts.append(g.transformed_xyz(g.thick_sheet("scrap", sheet, (0.0, -0.005, 0.0), "corrugated_rust"),
                                   0.25, rng.uniform(0, math.tau), 0.1, (rng.uniform(-0.2, 0.2) * r, 0.2, 0.0)))
    _kind, bat, _w = _battery(rng)
    a = rng.uniform(0, math.tau)
    parts.extend(g.transformed(m, a, (r * 0.6 * math.cos(a), 0.06, r * 0.6 * math.sin(a)), f"battery-{m.name}") for m in bat)
    # cable tangle snaking over the heap
    pts, a = [], rng.uniform(0, math.tau)
    for k in range(14):
        a += rng.uniform(0.4, 1.0)
        rr = r * (0.2 + 0.5 * rng.random())
        pts.append((rr * math.cos(a), 0.12 + 0.25 * rng.random() * (1 - rr / r), rr * math.sin(a)))
    parts.append(g.tube("cable", pts, 0.014, 5, "rubber"))
    # keep everything above the ground and inside the radius
    out = []
    for p in parts:
        lo, hi = g.bounds([p])
        lift = max(0.0, -0.02 - lo[1])
        pull = [0.0, 0.0]
        for axis, k in ((0, 0), (2, 1)):
            if hi[axis] > r:
                pull[k] = r - hi[axis]
            elif lo[axis] < -r:
                pull[k] = -r - lo[axis]
        out.append(g.planarize(g.transformed(p, 0.0, (pull[0], lift, pull[1]))))
    sprays = [Spray((center[0], 0.0, center[1]), r * 1.3, (0.55, 0.5, 0.45), 0.55)]
    return g.Assembly("junk-pile", f"junk-{index:02d}", "market", (float(center[0]), 0.0, float(center[1])), out,
                      {"sprays": sprays})


# --------------------------------------------------------------------------- sector


@register("market")
def market_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    out = [build_stall(s) for s in data["stalls"]]
    for k, ((x, z), r) in enumerate(JUNK_SITES, start=1):
        out.append(build_junk_pile((x, z), r, SEED + 400 + k, index=k))
    return out
