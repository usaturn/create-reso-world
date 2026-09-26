"""Overhead finish (sector ``overhead``): cable bundles, footbridges, alley hangings, kerbside trash.

* ``cables-NN`` — a 3-6 wire bundle for every layout ``cable-NN``: each wire is a 16-span
  catenary tube (6-sided, radius 0.012-0.03 m, sag jittered +-20% off the spec sag) ending
  in a ``bracket-*`` fitting and an ``insulator-*`` pin at both ends.
* ``bridge-NN`` — steel footbridge per layout ``bridge-NN``: ``steel_dark`` deck on edge
  stringers with grating slats, ``steel_bare`` posts and pipe rails, wall plates plus
  diagonal struts into the facades, a torn ``tarp_*`` sheet draped over one rail, and a
  mono-pitch ``corrugated`` roof on odd-numbered bridges (50 %). Every bridge carries
  ``meta["occludes"] = ["occ-bridge-NN"]`` and the world AABB of its parts contains the
  layout occluder box.
* ``hangings-NN`` — six sets above the alleys: five catenary laundry lines (cloth pieces
  plus one wider banner each) strung between facing walls/stall backs/shacks, and one
  hanging shop sign off club-01's street face. ``meta["attach"]``/``meta["anchors"]``
  record the mounts and the on-face anchor points.
* ``trash-NN`` — eight kerbside piles (``rubber`` bags, flattened ``plywood`` cardboard,
  ``plastic_crate`` foam boxes on every second pile) tucked against street edges.

All parts are authored in world space with origin (0, 0, 0) like ``ground``. Deterministic:
``random.Random(SEED + <family> + index)`` per object — the layout specs carry no seeds.
R11: every part is a closed outward shell; bent tubes/sheets run through ``planarize``.
"""
from __future__ import annotations

import math
import random
from typing import Any

from modeling.slum02 import SEED
from modeling.slum02 import geometry as g
from modeling.slum02.layout import _wall_point
from modeling.slum02.sectors import register

Vec = tuple[float, float, float]

WIRE_SIDES = 6          # 6角断面
WIRE_SPAN = 16          # 16分割カテナリー
BUNDLE_STEP = 0.03      # sideways offset between adjacent wires of a bundle
RAIL_TOP = 0.98
RAIL_MID = 0.55
ROOF_EAVE = 2.05        # roof underside height above the deck at the high end
TARP_MATS = ("tarp_blue", "tarp_orange", "tarp_green")
CLOTH_MATS = ("cloth_red", "tarp_blue", "tarp_orange", "tarp_green")

# (mount_a, mount_b, line height, kind) — laundry lines span facing walls above the
# alleys (the market lane and two radials); the lone sign set hangs off club-01's
# street face. Mount ids must exist in towers/stalls/clubs/shacks.
HANGING_SPECS: list[tuple[str, str | None, float, str]] = [
    ("stall-04", "stall-07", 2.30, "laundry"),   # across the market lane (stall backs)
    ("stall-05", "stall-08", 2.20, "laundry"),
    ("stall-06", "stall-09", 2.25, "laundry"),
    ("tower-17", "tower-18", 4.50, "laundry"),   # across the radial-n1 dogleg
    ("shack-01", "shack-05", 2.00, "laundry"),   # across radial-w0
    ("club-01", None, 4.60, "sign"),             # hanging shop sign over the street edge
]

# (street_id, x, z) — pile centres just inside a kerb line of that street.
TRASH_SPOTS: list[tuple[str, float, float]] = [
    ("lane", -20.0, -18.9),
    ("ring-s", 8.0, -13.4),
    ("ring-n", -12.5, 10.7),
    ("outer-s", -25.0, -31.8),
    ("radial-e1", 22.5, -3.6),
    ("ring-e", 10.8, -6.0),
    ("outer-n", 18.0, 29.7),
    ("ring-w", -10.8, 4.0),
]


def _v3(p) -> Vec:
    return (float(p[0]), float(p[1]), float(p[2]))


def _perp_xz(d: Vec) -> Vec:
    return g.norm((-d[2], 0.0, d[0]))


def _mounts(data: dict[str, Any]) -> dict[str, Any]:
    return {x["id"]: x for grp in ("towers", "stalls", "clubs", "shacks") for x in data[grp]}


# --------------------------------------------------------------------------- cables


def _anchor(end: str, p: Vec, mount: dict[str, Any]) -> list[g.MeshData]:
    """端点の碍子・金具: a small plate + a pin insulator where the bundle terminates."""
    out = g.norm((p[0] - mount["center"][0], 0.0, p[2] - mount["center"][1]))
    if abs(p[1] - mount["height"]) < 0.05:
        # roof mount: a base plate flat on the roof, pin standing on it
        plate = g.box(f"bracket-{end}", (p[0], p[1] + 0.025, p[2]), (0.18, 0.05, 0.18), "steel_dark")
        pin = g.cylinder(f"insulator-{end}", (p[0], p[1] + 0.10, p[2]), 0.032, 0.10, 6,
                         "plastic_crate", "Y")
    else:
        # wall mount: a plate half-buried in the face, pin just off the wall under the bundle
        plate = g.box(f"bracket-{end}", (p[0] - out[0] * 0.03, p[1], p[2] - out[2] * 0.03),
                      (0.14, 0.12, 0.14), "steel_dark")
        pin = g.cylinder(f"insulator-{end}",
                         (p[0] + out[0] * 0.06, p[1] - 0.02, p[2] + out[2] * 0.06),
                         0.032, 0.10, 6, "plastic_crate", "Y")
    return [plate, pin]


def build_cable(spec: dict[str, Any], mounts: dict[str, Any]) -> g.Assembly:
    rng = random.Random(SEED + 700 + int(spec["id"].rsplit("-", 1)[1]))
    a, b = _v3(spec["a"]), _v3(spec["b"])
    perp = _perp_xz(g.norm(g.sub(b, a)))
    n = rng.randint(3, 6)
    parts: list[g.MeshData] = []
    for j in range(n):
        s = (j - (n - 1) / 2.0) * BUNDLE_STEP
        aj = (a[0] + perp[0] * s, a[1] + rng.uniform(-0.015, 0.015), a[2] + perp[2] * s)
        bj = (b[0] + perp[0] * s, b[1] + rng.uniform(-0.015, 0.015), b[2] + perp[2] * s)
        sag = spec["sag"] * rng.uniform(0.8, 1.2)
        pts = g.catenary(aj, bj, sag, WIRE_SPAN)
        parts.append(g.planarize(
            g.tube(f"wire-{j}", pts, rng.uniform(0.012, 0.03), WIRE_SIDES, "rubber")))
    parts += _anchor("a", a, mounts[spec["attach"][0]])
    parts += _anchor("b", b, mounts[spec["attach"][1]])
    return g.Assembly("cable", spec["id"].replace("cable", "cables"), "overhead",
                      (0.0, 0.0, 0.0), parts,
                      {"attach": list(spec["attach"]), "wires": n})


# --------------------------------------------------------------------------- bridges


def _face_normal(p: Vec, d: Vec, end: str) -> Vec:
    """Axis-snapped outward normal of the facade a bridge end lands on.

    The bridge's own direction points out of the wall at end ``a`` and into it at end
    ``b``; the facade axis is whichever coordinate of the anchor is larger (outer faces
    sit near +-32.5, inner faces near +-27).
    """
    axis = 0 if abs(p[0]) > abs(p[2]) else 2
    sgn = math.copysign(1.0, d[axis])
    n = [0.0, 0.0, 0.0]
    n[axis] = sgn if end == "a" else -sgn
    return _v3(n)


def build_bridge(spec: dict[str, Any]) -> g.Assembly:
    k = int(spec["id"].rsplit("-", 1)[1])
    rng = random.Random(SEED + 750 + k)
    y = spec["y"]
    A = (spec["a"][0], y, spec["a"][1])
    B = (spec["b"][0], y, spec["b"][1])
    ab = g.sub(B, A)
    span = math.dist(A, B)
    d = g.norm(ab)
    perp = _perp_xz(d)
    w = spec["width"]
    roofed = k % 2 == 1                       # 50% of the bridges carry a roof (brief)
    parts: list[g.MeshData] = [
        g.beam("deck", (A[0], y - 0.06, A[2]), (B[0], y - 0.06, B[2]),
               0.12, w + 0.24, "steel_dark"),
    ]
    # edge stringers below the deck and grating slats across it
    for side, s in (("l", 1.0), ("r", -1.0)):
        off = g.mul(perp, s * (w / 2 - 0.03))
        parts.append(g.beam(f"stringer-{side}", (A[0] + off[0], y - 0.09, A[2] + off[2]),
                            (B[0] + off[0], y - 0.09, B[2] + off[2]), 0.18, 0.05, "steel_dark"))
    n_slat = max(2, int(span / 0.45))
    for i in range(1, n_slat):
        c = (A[0] + ab[0] * i / n_slat, y + 0.006, A[2] + ab[2] * i / n_slat)
        parts.append(g.beam(f"grate-{i:02d}",
                            (c[0] - perp[0] * w / 2, c[1], c[2] - perp[2] * w / 2),
                            (c[0] + perp[0] * w / 2, c[1], c[2] + perp[2] * w / 2),
                            0.012, 0.05, "steel_dark"))
    # posts + pipe rails on both sides; posts rise to the roof eave when roofed
    for side, s in (("l", 1.0), ("r", -1.0)):
        off = g.mul(perp, s * (w / 2 - 0.04))
        for i in range(5):
            t = i / 4
            h = ROOF_EAVE - 0.02 - 0.15 * t if roofed else RAIL_TOP
            parts.append(g.box(f"post-{side}-{i}", (A[0] + ab[0] * t + off[0], y + h / 2,
                                                    A[2] + ab[2] * t + off[2]),
                               (0.035, h, 0.035), "steel_bare"))
        for name, ry, r in (("rail-top", RAIL_TOP, 0.018), ("rail-mid", RAIL_MID, 0.014)):
            parts.append(g.pipe(f"{name}-{side}",
                                (A[0] + off[0], y + ry, A[2] + off[2]),
                                (B[0] + off[0], y + ry, B[2] + off[2]), r, "steel_bare", 6))
    if roofed:
        # mono-pitch corrugated sheet pitched along the span; corrugations run across
        profile = g.corrugation(-(w / 2 + 0.15), w / 2 + 0.15)
        grid = []
        for i in range(5):
            s_i = -0.3 + (span + 0.6) * i / 4
            eave = y + ROOF_EAVE - 0.15 * s_i / span
            grid.append([(A[0] + d[0] * s_i + perp[0] * wx, eave + prof,
                          A[2] + d[2] * s_i + perp[2] * wx) for wx, prof in profile])
        parts.append(g.thick_sheet("roof", grid, (0.0, -0.02, 0.0), "corrugated"))
    # torn tarp draped over one side rail, hem scalloped and belly out
    side = rng.choice((1.0, -1.0))
    rail_off = g.mul(perp, side * (w / 2 - 0.04))
    t0 = rng.uniform(0.15, 0.30)
    t1 = t0 + rng.uniform(0.35, 0.50)
    drop = rng.uniform(0.55, 0.85)
    grid = []
    for r in range(4):
        f = r / 3
        row = []
        for j in range(6):
            t = t0 + (t1 - t0) * j / 5
            hem = drop * f * (0.9 + 0.1 * math.sin(math.pi * j / 5))
            out = side * 0.10 * math.sin(math.pi * f)
            row.append((A[0] + ab[0] * t + rail_off[0] + perp[0] * out,
                        y + RAIL_TOP - hem,
                        A[2] + ab[2] * t + rail_off[2] + perp[2] * out))
        grid.append(row)
    parts.append(g.thick_sheet("tarp", grid, g.mul(perp, -0.006 * side), rng.choice(TARP_MATS)))
    # wall plates + diagonal struts tying the deck ends into the facades
    for end, P, sign in (("a", A, 1.0), ("b", B, -1.0)):
        n = _face_normal(P, d, end)
        parts.append(g.box(f"bracket-{end}", (P[0] - n[0] * 0.01, y - 0.5, P[2] - n[2] * 0.01),
                           (0.08 if n[0] else 0.45, 0.6, 0.08 if n[2] else 0.45), "steel_dark"))
        wall_pt = (P[0] + n[0] * 0.02, y - 1.05, P[2] + n[2] * 0.02)
        deck_pt = (P[0] + sign * d[0] * 0.75, y - 0.14, P[2] + sign * d[2] * 0.75)
        parts.append(g.beam(f"strut-{end}", wall_pt, deck_pt, 0.08, 0.10, "steel_dark"))
    return g.Assembly("bridge", spec["id"], "overhead", (0.0, 0.0, 0.0), parts,
                      {"occludes": [f"occ-{spec['id']}"], "roofed": roofed})


# --------------------------------------------------------------------------- hangings


def _line_pt(a: Vec, b: Vec, sag: float, t: float) -> Vec:
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t - sag * 4 * t * (1 - t),
            a[2] + (b[2] - a[2]) * t)


def _cloth(name: str, a: Vec, b: Vec, perp: Vec, sag: float, t0: float, t1: float,
           h: float, rng: random.Random, material: str) -> g.MeshData:
    """A hanging piece: top edge follows the catenary between t0..t1, hem drops ``h``."""
    grid = []
    for r in range(3):
        f = r / 2
        row = []
        for j in range(3):
            t = t0 + (t1 - t0) * j / 2
            p = _line_pt(a, b, sag, t)
            billow = 0.03 * math.sin(math.pi * f) + 0.02 * math.sin(math.pi * j) * f
            row.append((p[0] + perp[0] * billow, p[1] - h * f, p[2] + perp[2] * billow))
        grid.append(row)
    return g.thick_sheet(name, grid, g.mul(perp, -0.006), material)


def _laundry(k: int, a: Vec, b: Vec, ids: tuple[str, str], rng: random.Random) -> g.Assembly:
    span = math.dist(a, b)
    d = g.norm(g.sub(b, a))
    perp = _perp_xz(d)
    sag = rng.uniform(0.10, min(0.30, 0.04 * span + 0.10))
    parts: list[g.MeshData] = [
        g.planarize(g.tube("line", g.catenary(a, b, sag, 12), 0.006, 5, "steel_dark")),
        g.box("anchor-a", (a[0] - d[0] * 0.05, a[1], a[2] - d[2] * 0.05), (0.10, 0.10, 0.10), "steel_dark"),
        g.box("anchor-b", (b[0] + d[0] * 0.05, b[1], b[2] + d[2] * 0.05), (0.10, 0.10, 0.10), "steel_dark"),
    ]
    n_pieces = rng.randint(3, 5)
    for i in range(n_pieces):
        t_c = (i + 0.5) / n_pieces + rng.uniform(-0.04, 0.04)
        wd = rng.uniform(0.30, 0.55)
        t0, t1 = max(0.06, t_c - wd / span / 2), min(0.94, t_c + wd / span / 2)
        cap = min(_line_pt(a, b, sag, t)[1] for t in (t0, (t0 + t1) / 2, t1)) - 1.30
        h = rng.uniform(0.35, min(0.65, max(0.36, cap)))
        parts.append(_cloth(f"cloth-{i}", a, b, perp, sag, t0, t1, h, rng, rng.choice(CLOTH_MATS)))
    # one wider banner tarp （吊り布） near the middle of the line
    wd = rng.uniform(0.55, 0.85)
    t0, t1 = 0.5 - wd / span / 2, 0.5 + wd / span / 2
    cap = min(_line_pt(a, b, sag, t)[1] for t in (t0, (t0 + t1) / 2, t1)) - 1.30
    h = rng.uniform(0.45, min(0.70, max(0.46, cap)))
    parts.append(_cloth("banner-0", a, b, perp, sag, t0, t1, h, rng, rng.choice(TARP_MATS)))
    return g.Assembly("hanging", f"hangings-{k:02d}", "overhead", (0.0, 0.0, 0.0), parts,
                      {"kind": "laundry", "attach": [ids[0], ids[1]],
                       "anchors": [[round(c, 6) for c in a], [round(c, 6) for c in b]]})


def _shop_sign(k: int, a: Vec, mount: dict[str, Any], rng: random.Random) -> g.Assembly:
    """Perpendicular hanging sign on two arms off the facade, over the street edge."""
    out = g.norm((a[0] - mount["center"][0], 0.0, a[2] - mount["center"][1]))
    perp = _perp_xz(out)                      # along the facade
    reach = 0.62
    parts: list[g.MeshData] = []
    anchors = []
    for i, s in enumerate((-1.0, 1.0)):
        base = (a[0] + perp[0] * s * 0.32, a[1], a[2] + perp[2] * s * 0.32)
        tip = (base[0] + out[0] * reach, a[1], base[2] + out[2] * reach)
        parts.append(g.beam(f"arm-{i}",
                            (base[0] + out[0] * 0.02, a[1], base[2] + out[2] * 0.02), tip,
                            0.035, 0.035, "steel_dark"))
        anchors.append([round(c, 6) for c in base])
    board_y = a[1] - 0.40
    c = (a[0] + out[0] * (reach - 0.06), board_y, a[2] + out[2] * (reach - 0.06))
    parts.append(g.beam("sign-board",
                        (c[0] - perp[0] * 0.40, board_y, c[2] - perp[2] * 0.40),
                        (c[0] + perp[0] * 0.40, board_y, c[2] + perp[2] * 0.40),
                        0.55, 0.05, "plywood"))
    for i, s in enumerate((-1.0, 1.0)):
        tip = (a[0] + perp[0] * s * 0.32 + out[0] * reach, a[1],
               a[2] + perp[2] * s * 0.32 + out[2] * reach)
        corner = (c[0] + perp[0] * s * 0.30, board_y + 0.28, c[2] + perp[2] * s * 0.30)
        parts.append(g.pipe(f"hanger-{i}", tip, corner, 0.006, "steel_dark", 5))
    cid = mount["id"]
    return g.Assembly("hanging", f"hangings-{k:02d}", "overhead", (0.0, 0.0, 0.0), parts,
                      {"kind": "sign", "attach": [cid, cid], "anchors": anchors})


def build_hanging(k: int, mounts: dict[str, Any]) -> g.Assembly:
    rng = random.Random(SEED + 780 + k)
    ia, ib, y, kind = HANGING_SPECS[k - 1]
    item_a = mounts[ia]
    if kind == "sign":
        cx, cz = item_a["center"]
        a = _v3(_wall_point(item_a, (cx - 5.0, cz), y))
        return _shop_sign(k, a, item_a, rng)
    item_b = mounts[ib]  # type: ignore[index]
    a = _v3(_wall_point(item_a, item_b["center"], y))
    b = _v3(_wall_point(item_b, item_a["center"], y))
    return _laundry(k, a, b, (ia, ib), rng)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- trash


def build_trash(k: int, street: dict[str, Any], pos: tuple[float, float]) -> g.Assembly:
    rng = random.Random(SEED + 800 + k)
    x0, z0 = pos
    parts: list[g.MeshData] = []
    bw, bh = rng.uniform(0.38, 0.55), rng.uniform(0.34, 0.50)
    parts.append(g.transformed(
        g.beveled_box("bag-0", (0.0, bh / 2, 0.0), (bw, bh, rng.uniform(0.36, 0.50)),
                      0.09, "rubber"),
        rng.uniform(0.0, math.pi), (x0 + rng.uniform(-0.2, 0.2), 0.0, z0 + rng.uniform(-0.2, 0.2))))
    if rng.random() < 0.6:                       # second, smaller bag
        bh2 = rng.uniform(0.26, 0.40)
        parts.append(g.transformed(
            g.beveled_box("bag-1", (0.0, bh2 / 2, 0.0), (rng.uniform(0.28, 0.42), bh2, rng.uniform(0.26, 0.40)),
                          0.08, "rubber"),
            rng.uniform(0.0, math.pi), (x0 + rng.uniform(-0.3, 0.3), 0.0, z0 + rng.uniform(-0.3, 0.3))))
    parts.append(g.transformed(                  # flattened cardboard sheet
        g.box("cardboard", (0.0, 0.025, 0.0), (0.55, 0.05, 0.42), "plywood"),
        rng.uniform(0.0, math.pi), (x0 + rng.uniform(-0.35, 0.35), 0.0, z0 + rng.uniform(-0.35, 0.35))))
    if k % 2 == 0:                               # a styrofoam box on every second pile
        parts.append(g.transformed(
            g.box("foam", (0.0, 0.13, 0.0), (0.45, 0.26, 0.32), "plastic_crate"),
            rng.uniform(0.0, math.pi), (x0 + rng.uniform(-0.35, 0.35), 0.0, z0 + rng.uniform(-0.35, 0.35))))
    # keep the whole pile inside the street rect (2 cm off the kerb line)
    r = (street["min"][0], street["min"][1], street["max"][0], street["max"][1])
    lo, hi = g.bounds(parts)
    dx = max(0.0, r[0] + 0.02 - lo[0]) - max(0.0, hi[0] - r[2] + 0.02)
    dz = max(0.0, r[1] + 0.02 - lo[2]) - max(0.0, hi[2] - r[3] + 0.02)
    if dx or dz:
        parts = [g.transformed(p, 0.0, (dx, 0.0, dz)) for p in parts]
    return g.Assembly("trash", f"trash-{k:02d}", "overhead", (0.0, 0.0, 0.0), parts,
                      {"street": street["id"]})


# --------------------------------------------------------------------------- sector


@register("overhead")
def overhead_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    mounts = _mounts(data)
    streets = {s["id"]: s for s in data["streets"]}
    out = [build_cable(c, mounts) for c in data["cables"]]
    out += [build_bridge(b) for b in data["bridges"]]
    out += [build_hanging(k, mounts) for k in range(1, len(HANGING_SPECS) + 1)]
    out += [build_trash(k, streets[sid], (x, z)) for k, (sid, x, z) in enumerate(TRASH_SPOTS, start=1)]
    return out
