"""Neon-lit nightlife storefronts on the east side (sector ``nightlife``).

Each layout club becomes one object: a 2-3 storey brutalist concrete box whose ground
floor is set back under the upper floors (a shadowed shopfront between two full-height
columns). The ground floor carries a half-open roller shutter (``corrugated_rust`` box,
slats hanging to 0.8 m above the sill, a dark interior below), a doorway with a 24-strand
bead curtain (alternating ``cloth_red`` / ``neon_pink``), a rounded neon tube frame in
``spec["neon"]``, a small corrugated canopy with bare bulbs, a red lantern outside and a
red strip lamp inside the doorway, and 6-10 plain paper posters. Upper floors have slit
windows recessed into the wall with drawn ``cloth_red`` curtains, a dark sign board
behind the layout's TextRenderer anchor, a heart- or crescent-shaped neon motif,
outdoor AC units on gusset brackets with pipes back into the wall, a side downpipe and a
roof with parapets, water tank, AC and posts for the layout's roof cables.

Content stays suggestive only (global constraint): neon, shutter, bead curtain, blank
posters, red light. No imagery or text is modelled.

Pure Python and deterministic (``random.Random(spec["seed"])`` per club).
Local frame: +Z faces the spec's ``front``, X runs across the facade; parts are baked
into the spec yaw, so the assembly origin is ``(cx, 0, cz)`` and ``sign_anchor`` /
``light_anchor`` are in that same origin-relative, yaw-baked frame (like stalls).
``meta["frame"]`` keeps the unrotated facade planes and opening rectangles for tests.
R11: every part is a closed outward shell (tubes are built in a horizontal plane so
their ring frames never flip, then rotated onto the wall).
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any

from modeling.slum02 import geometry as g
from modeling.slum02.sectors import register
from modeling.slum02.vcolor import Spray

Vec = tuple[float, float, float]
Rect = tuple[float, float, float, float]          # (x0, y0, x1, y1) on a facade plane

GROUND_H = 3.0          # ground-floor storey (soffit of the upper floors)
PARAPET = 0.5           # roof deck sits this far below the layout height
SETBACK = 0.35          # ground-floor shopfront recessed under the upper floors
GROUND_T = 0.4          # ground-floor front wall
POCKET = 0.35           # depth of the door / shutter openings (dark interior behind)
UPPER_T = 0.75          # upper front wall (fills the setback depth to the body)
WINDOW_RECESS = 0.22
COL_W, COL_OUT = 0.35, 0.15     # edge columns: width, projection past the facade
BAND_H, BAND_OUT = 0.15, 0.08   # floor-slab bands on the facade
SIDE_T, SIDE_RECESS = 0.3, 0.15  # side walls and their window recesses
AC_GAP = 0.04           # AC body stands off the facade on its brackets
DOOR: Rect = (-0.6, 0.12, 0.6, 2.2)
FRAME_OFF, FRAME_R = 0.12, 0.014
AWNING_Y, AWNING_D, AWNING_DROP, AWNING_T = 2.47, 0.55, 0.06, 0.025
POSTER_W, POSTER_H = 0.3, 0.42
POSTER_MATS = ("paint_yellow_faded", "paint_teal_faded", "tarp_blue", "tarp_orange", "tarp_green")
CONCRETE = ("concrete_stained", "concrete_patch")


def _dims(spec: dict) -> tuple[float, float]:
    a, b = spec["size"]
    return (a, b) if spec["front"] in ("+z", "-z") else (b, a)      # local X = across the front


def _overlap(a: Rect, b: Rect, pad: float = 0.0) -> bool:
    return min(a[2], b[2]) - max(a[0], b[0]) > -pad and min(a[3], b[3]) - max(a[1], b[1]) > -pad


def _box(name: str, lo: Vec, hi: Vec, material: str) -> g.MeshData:
    return g.box(name, tuple((lo[k] + hi[k]) / 2 for k in range(3)), tuple(hi[k] - lo[k] for k in range(3)), material)


def _gusset(name: str, x: float, tri_zy: Sequence[tuple[float, float]], thickness: float, material: str) -> g.MeshData:
    """Triangular plate in the (z, y) plane, ``thickness`` wide along X (AC and canopy brackets)."""
    t = thickness / 2
    verts = [(x - t, y, z) for z, y in tri_zy] + [(x + t, y, z) for z, y in tri_zy]
    faces = ((0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0))
    return g.outward(g.mesh(name, verts, faces, material))


def _wall_tube(name: str, pts: Sequence[tuple[float, float]], radius: float, z: float, material: str) -> g.MeshData:
    """Tube along a curve drawn on a wall (u across, v up) with its centre ``z`` off the facade.

    Built flat in the XZ plane (tangents stay horizontal, so ``g.tube`` ring frames never flip)
    and rotated about X onto the wall. Eight sides put ring vertices exactly at +-Z, so the
    tube's back line is at ``z - radius``.
    """
    flat = g.tube(name, [(u, 0.0, v) for u, v in pts], radius, 8, material)
    return g.transformed_xyz(flat, -math.pi / 2, 0.0, 0.0, (0.0, 0.0, z))


def _rounded_u(x0: float, x1: float, bottom: float, top: float, rc: float) -> list[tuple[float, float]]:
    """Inverted U (left leg up, across, right leg down) with rounded top corners."""
    pts = [(x0, bottom), (x0, top - rc)]
    pts += [(x0 + rc - rc * math.cos(a), top - rc + rc * math.sin(a))
            for a in (math.pi / 2 * k / 5 for k in range(1, 5))]
    pts += [(x0 + rc, top), (x1 - rc, top)]
    pts += [(x1 - rc + rc * math.sin(a), top - rc + rc * math.cos(a))
            for a in (math.pi / 2 * k / 5 for k in range(1, 5))]
    pts += [(x1, top - rc), (x1, bottom)]
    return pts


def _heart(size: float, n: int = 56) -> list[tuple[float, float]]:
    """Closed heart outline centred on the origin, ``size`` wide; starts on a smooth flank."""
    k = size / 32.0
    pts = []
    for i in range(n + 1):
        t = math.pi / 2 + math.tau * i / n
        u = 16 * math.sin(t) ** 3
        v = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((u * k, (v + 2.5) * k))
    return pts


def _crescent(size: float) -> list[tuple[float, float]]:
    """Closed crescent moon outline (opening to +u), ``size`` tall, starting on the outer arc."""
    R, ri, c = size / 2, 0.8 * size / 2, 0.45 * size / 2
    xi = (R * R - ri * ri + c * c) / (2 * c)
    yi = math.sqrt(R * R - xi * xi)
    a_out = math.atan2(yi, xi)
    a_in = math.atan2(yi, xi - c)
    pts = []
    for k in range(9):                                  # outer arc, 180 deg -> lower tip
        a = math.pi + (math.tau - a_out - math.pi) * k / 8
        pts.append((R * math.cos(a), R * math.sin(a)))
    for k in range(1, 12):                              # inner arc back, lower tip -> upper tip
        a = (math.tau - a_in) - (math.tau - 2 * a_in) * k / 12
        pts.append((c + ri * math.cos(a), ri * math.sin(a)))
    for k in range(9):                                  # outer arc, upper tip -> 180 deg
        a = a_out + (math.pi - a_out) * k / 8
        pts.append((R * math.cos(a), R * math.sin(a)))
    ox = -(min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    return [(u + ox, v) for u, v in pts]


def _side_walls(parts: list[g.MeshData], rng: random.Random, hx: float, d: float, F: float, R: float,
                floor_ys: Sequence[float], fh: float, dside: int, dz: float) -> None:
    """Both side walls: slit windows (dark glass, some curtained) per upper floor and a steel door
    on the side without the downpipe. Built in the wall frame (+Z out) and turned onto +-X."""
    z0, z1 = -d / 2, F - UPPER_T
    zc, length = (z0 + z1) / 2, z1 - z0
    for tag, sx in (("l", -1), ("r", 1)):
        yaw = sx * math.pi / 2                           # wall +Z -> world sx*X; wall x = sx * (zc - z)

        def wx(z: float, sx: int = sx) -> float:
            return sx * (zc - z)

        openings: list[Rect] = []
        extras: list[g.MeshData] = []
        n = max(1, int((length - 1.2) / 1.6))
        zs = [z0 + 0.8 + (length - 1.6) * (k + 0.5) / n for k in range(n)]
        zs = [z for z in zs if not (sx == dside and abs(z - dz) < 0.5)]
        back = SIDE_T / 2 - SIDE_RECESS
        for fy in floor_ys:
            y0, y1 = fy + 0.9, fy + 0.9 + min(1.3, fh - 1.25)
            for z in zs:
                u0, u1 = sorted((wx(z - 0.22), wx(z + 0.22)))
                openings.append((u0, y0, u1, y1))
                extras.append(_box(f"sideglass-{tag}{len(openings):02d}", (u0 + 0.001, y0 + 0.001, back + 0.002),
                                   (u1 - 0.001, y1 - 0.001, back + 0.01), "glass_dark"))
                if rng.random() < 0.5:
                    cover = rng.uniform(0.5, 0.95) * (u1 - u0 - 0.02)
                    extras.append(_box(f"sidecurtain-{tag}{len(openings):02d}", (u0 + 0.01, y0 + 0.01, back + 0.02),
                                       (u0 + 0.01 + cover, y1 - 0.01, back + 0.03), "cloth_red"))
        if sx != dside:                                  # steel back door facing the side gap
            u0, u1 = sorted((wx(z0 + 1.0), wx(z0 + 1.9)))
            openings.append((u0, 0.1, u1, 2.1))
            extras.append(_box(f"sidedoor-{tag}", (u0 + 0.01, 0.11, back + 0.001), (u1 - 0.01, 2.09, back + 0.05), "steel_dark"))
        wall = g.wall_with_openings(f"wall-side-{tag}", length, R, SIDE_T, openings, SIDE_RECESS, 0.6, "concrete_stained")
        offset = (sx * (hx - SIDE_T / 2), 0.0, zc)
        parts.append(g.transformed(wall, yaw, offset))
        parts.extend(g.transformed(m, yaw, offset) for m in extras)


def _text_width(text: str, size: float) -> float:
    return sum(size if ord(ch) > 0x2000 else size * 0.55 for ch in text)


def _to_local(point: Sequence[float], origin: Vec, yaw: float) -> Vec:
    return g.rotate_y((point[0] - origin[0], point[1] - origin[1], point[2] - origin[2]), -yaw)


# --------------------------------------------------------------------------- club


def build_club(spec: dict, data: dict[str, Any] | None = None) -> g.Assembly:
    """One club from a layout spec. Origin = (cx, 0, cz); parts carry the yaw."""
    if data is None:
        from modeling.slum02.layout import build_layout
        data = build_layout()
    rng = random.Random(spec["seed"])
    yaw = math.radians(spec["rotation"])
    cx, cz = spec["center"]
    origin: Vec = (float(cx), 0.0, float(cz))
    w, d = _dims(spec)
    hx = w / 2
    H = float(spec["height"])
    F = d / 2                           # upper facade plane
    G = F - SETBACK                     # ground-floor shopfront plane
    R = H - PARAPET                     # roof deck
    n_up = 2 if H >= 7.5 else 1
    fh = (R - GROUND_H) / n_up
    floor_ys = [GROUND_H + k * fh for k in range(n_up)]
    neon = spec["neon"]
    index = int(spec["id"].split("-")[-1])
    motif = "crescent" if index % 2 == 0 else "heart"
    s = rng.choice((-1, 1))             # shutter side; posters and the lantern take the other side
    dside = rng.choice((-1, 1))         # downpipe side; the steel side door takes the other one
    dz = F - UPPER_T - 0.35             # downpipe line on the side wall, just behind the front columns

    parts: list[g.MeshData] = []
    sprays: list[tuple[str, Vec, float, tuple]] = []

    # ---- facade features fixed by the layout: sign board and mounted vertical ads
    sign = next(x for x in data["signs"] if x.get("target") == spec["id"])
    anchor = _to_local(sign["position"], origin, yaw)
    bw = min(w - 2 * COL_W - 0.4, _text_width(sign["text"], sign["size"]) + 0.5)
    bh = sign["size"] + 0.35
    board: Rect = (anchor[0] - bw / 2, anchor[1] - bh / 2, anchor[0] + bw / 2, anchor[1] + bh / 2)
    ads: list[Rect] = []
    for ad in (x for x in data["ads"] if x.get("mount") == spec["id"]):
        p = _to_local(ad["position"], origin, yaw)
        aw, ah = ad["size"]
        ads.append((p[0] - aw / 2, p[1] - ah / 2, p[0] + aw / 2, p[1] + ah / 2))

    # ---- structure: body, ground wall, upper wall, columns, bands, coping, parapets
    parts.append(g.subdivided_box("body", (0.0, R / 2, (-d / 2 + F - UPPER_T) / 2), (w - 2 * SIDE_T, R, d - UPPER_T), 1.0,
                                  "concrete_stained"))
    _side_walls(parts, rng, hx, d, F, R, floor_ys, fh, dside, dz)
    sw = min(2.0, hx - COL_W - 1.0 - 0.15)
    xa, xb = sorted((s * 1.0, s * (1.0 + sw)))
    shutter: Rect = (round(xa, 6), 0.05, round(xb, 6), 2.15)
    ground = g.wall_with_openings("wall-ground", w, GROUND_H, GROUND_T, [DOOR, shutter], POCKET, 0.5, "concrete_patch")
    parts.append(g.transformed(ground, 0.0, (0.0, 0.0, G - GROUND_T / 2)))

    motif_size = 0.8
    m_side = -s
    if ads:
        m_side = -1 if sum((a[0] + a[2]) / 2 for a in ads) > 0 else 1
    mx = m_side * (hx - COL_W - 0.25 - motif_size / 2)
    my = GROUND_H + 0.3 + motif_size / 2
    motif_rect: Rect = (mx - motif_size / 2, my - motif_size / 2, mx + motif_size / 2, my + motif_size / 2)

    windows: list[Rect] = []
    n_cols = int((w - 2 * COL_W - 0.4) / 0.9)
    cols = [(k - (n_cols - 1) / 2) * 0.9 for k in range(n_cols)]
    for fy in floor_ys:
        y0 = fy + 0.9
        y1 = y0 + min(1.3, fh - 1.25)
        for x in cols:
            top = y1
            if _overlap((x - 0.25, y0, x + 0.25, y1), board, 0.12):
                top = min(y1, board[1] - 0.15)          # shorten the slit under the sign board
            r = (x - 0.25, y0, x + 0.25, top)
            if top - y0 >= 0.8 and not _overlap(r, board, 0.12) and not _overlap(r, motif_rect, 0.12):
                windows.append((round(r[0], 6), round(y0, 6), round(r[2], 6), round(top, 6)))
    upper = g.wall_with_openings("wall-upper", w - 2 * COL_W, H - GROUND_H, UPPER_T,
                                 [(x0, y0 - GROUND_H, x1, y1 - GROUND_H) for x0, y0, x1, y1 in windows],
                                 WINDOW_RECESS, 0.45, "concrete_stained")
    parts.append(g.transformed(upper, 0.0, (0.0, GROUND_H, F - UPPER_T / 2)))

    for tag, sx in (("l", -1), ("r", 1)):
        x0, x1 = sorted((sx * (hx - COL_W), sx * hx))
        parts.append(g.combine(f"column-{tag}", [
            g.subdivided_box("lo", ((x0 + x1) / 2, GROUND_H / 2, (G + F + COL_OUT) / 2),
                             (COL_W, GROUND_H, F + COL_OUT - G), 0.25, "concrete_stained"),
            g.subdivided_box("hi", ((x0 + x1) / 2, (GROUND_H + H) / 2, (F - UPPER_T + F + COL_OUT) / 2),
                             (COL_W, H - GROUND_H, UPPER_T + COL_OUT), 0.25, "concrete_stained")]))
        px0, px1 = sorted((sx * (hx - 0.25), sx * hx))
        parts.append(_box(f"parapet-{tag}", (px0, R, -d / 2), (px1, H, F - UPPER_T), "concrete_stained"))
    parts.append(_box("parapet-b", (-hx + 0.25, R, -d / 2), (hx - 0.25, H, -d / 2 + 0.25), "concrete_stained"))
    parts.append(_box("coping", (-hx, H, F - UPPER_T), (hx, H + 0.08, F + 0.2), "concrete_patch"))
    for k, fy in enumerate(floor_ys):
        parts.append(_box(f"band-{k}", (-hx + COL_W, fy, F), (hx - COL_W, fy + BAND_H, F + BAND_OUT), "concrete_patch"))
        for tag, sx in (("l", -1), ("r", 1)):          # the slab line wraps round the sides, broken at the downpipe
            b0, b1 = sorted((sx * hx, sx * (hx + BAND_OUT)))
            spans = [(-d / 2, F + COL_OUT)] if sx != dside else [(-d / 2, dz - 0.08), (dz + 0.08, F + COL_OUT)]
            for j, (z0, z1) in enumerate(spans):
                parts.append(_box(f"band-{k}-{tag}{j}", (b0, fy, z0), (b1, fy + BAND_H, z1), "concrete_patch"))
    for k, (x0, y0, x1, _y1) in enumerate(windows):
        parts.append(_box(f"sill-{k:02d}", (x0 - 0.05, y0 - 0.06, F), (x1 + 0.05, y0, F + 0.05), "concrete_patch"))

    # ---- upper windows: dark glass at the recess back, red curtains drawn in front of it
    back = F - WINDOW_RECESS
    for k, (x0, y0, x1, y1) in enumerate(windows):
        parts.append(_box(f"glass-{k:02d}", (x0 + 0.001, y0 + 0.001, back + 0.002),
                          (x1 - 0.001, y1 - 0.001, back + 0.01), "glass_dark"))
        ww = x1 - x0 - 0.02
        left = rng.uniform(0.3, 0.55)
        right = 1.0 - left if rng.random() < 0.35 else rng.uniform(0.25, 1.0 - left)
        for tag, u0, u1 in (("l", x0 + 0.01, x0 + 0.01 + left * ww), ("r", x1 - 0.01 - right * ww, x1 - 0.01)):
            n = max(2, round((u1 - u0) / 0.035))
            grid = [[(u0 + (u1 - u0) * i / n, y, back + 0.04 + (0.012 if i % 2 else 0.0)) for y in (y0 + 0.01, y1 - 0.01)]
                    for i in range(n + 1)]
            parts.append(g.thick_sheet(f"curtain-{k:02d}{tag}", grid, (0.0, 0.0, -0.008), "cloth_red"))

    # ---- door: bead curtain on a rod under the head, red strip lamp inside, dark interior
    x0, y0, x1, y1 = DOOR
    parts.append(_box("interior-door", (x0 + 0.001, y0 + 0.001, G - POCKET + 0.001),
                      (x1 - 0.001, y1 - 0.001, G - POCKET + 0.011), "rubber"))
    parts.append(_box("beadrail", (x0, y1 - 0.04, G - 0.115), (x1, y1, G - 0.085), "steel_dark"))
    for k in range(24):
        bx = x0 + 0.025 + 0.05 * k
        parts.append(_box(f"bead-{k:02d}", (bx - 0.0075, y1 - 0.04 - 2.0, G - 0.1075), (bx + 0.0075, y1 - 0.04, G - 0.0925),
                          ("cloth_red", "neon_pink")[k % 2]))
    parts.append(_box("lamp-01", (x0 + 0.1, y1 - 0.03, G - 0.3), (x1 - 0.1, y1, G - 0.26), "neon_red"))

    # ---- neon door frame on clips, legs ending in electrode housings
    zc = G + FRAME_R + 0.016
    fx0, fx1, ftop, fbot = x0 - FRAME_OFF, x1 + FRAME_OFF, y1 + FRAME_OFF, 0.35
    parts.append(_wall_tube("neonframe-tube", _rounded_u(fx0, fx1, fbot, ftop, 0.08), FRAME_R, zc, neon))
    fback = zc - FRAME_R
    for k, (u, v) in enumerate(((fx0, 1.2), (fx1, 1.2), (fx0 + 0.45, ftop), (fx1 - 0.45, ftop))):
        parts.append(_box(f"neonframe-clip-{k}", (u - 0.01, v - 0.015, G), (u + 0.01, v + 0.015, fback), "steel_dark"))
    for tag, u in (("l", fx0), ("r", fx1)):
        parts.append(_box(f"neonframe-cap-{tag}", (u - 0.03, fbot - 0.1, G), (u + 0.03, fbot, G + 0.05), "steel_dark"))

    # ---- canopy over the door: corrugated sheet on two gussets, three bare bulbs
    def canopy_top(z: float) -> float:
        return AWNING_Y - AWNING_DROP * (z - G) / AWNING_D

    ax0, ax1 = -0.85, 0.85
    ribs = 34
    grid = [[(ax0 + (ax1 - ax0) * i / ribs, canopy_top(z) + (0.012 if i % 2 else 0.0), z) for z in (G, G + AWNING_D)]
            for i in range(ribs + 1)]
    parts.append(g.thick_sheet("awning-sheet", grid, (0.0, -AWNING_T, 0.0), "corrugated"))
    under = [(z, canopy_top(z) - AWNING_T) for z in (G, G + 0.45)]
    rib_w = (ax1 - ax0) / ribs

    def on_valley(x: float) -> float:
        """Nearest valley (un-raised, even) rib line, where the sheet underside is lowest."""
        return ax0 + rib_w * 2 * round((x - ax0) / (2 * rib_w))

    for k, x in enumerate((on_valley(ax0 + 0.1), on_valley(ax1 - 0.1))):
        parts.append(_gusset(f"awning-bracket-{k}", x, [(G, under[0][1]), (G + 0.45, under[1][1]), (G, 2.25)], 0.02,
                             "steel_dark"))
    for k, bx in enumerate(on_valley(x) for x in (-0.5, 0.0, 0.5)):
        bz = G + 0.48
        top = canopy_top(bz + 0.005) - AWNING_T       # lowest underside over the wire's footprint (sheet falls to +Z)
        drop = rng.uniform(0.06, 0.12)
        parts.append(g.pipe(f"bulb-wire-{k}", (bx, top, bz), (bx, top - drop, bz), 0.005, "rubber", 5))
        parts.append(g.cylinder(f"bulb-socket-{k}", (bx, top - drop - 0.025, bz), 0.02, 0.05, 8, "steel_dark"))
        parts.append(g.cylinder(f"bulb-{k}", (bx, top - drop - 0.095, bz), 0.03, 0.09, 8, "warm_bulb"))

    # ---- red lantern on a bracket beside the door (poster side)
    lx = -s * 1.0
    parts.append(_box("lamp-00", (lx - 0.06, 2.05, G + 0.14), (lx + 0.06, 2.25, G + 0.26), "neon_red"))
    parts.append(g.combine("lamp-00-bracket", [
        _box("cap", (lx - 0.07, 2.25, G + 0.13), (lx + 0.07, 2.28, G + 0.27), "steel_dark"),
        _box("stem", (lx - 0.01, 2.28, G + 0.19), (lx + 0.01, 2.32, G + 0.21), "steel_dark"),
        _box("arm", (lx - 0.015, 2.32, G), (lx + 0.015, 2.35, G + 0.22), "steel_dark")]))

    # ---- roller shutter: rust box on the shopfront, rails, corrugated slats, bottom bar
    sx0, sy0, sx1, _sy1 = shutter
    box_lo = 2.17
    parts.append(g.beveled_box("shutter-box", ((sx0 + sx1) / 2, (box_lo + 2.5) / 2, G + 0.15),
                               (sx1 - sx0 + 0.2, 2.5 - box_lo, 0.3), 0.02, "corrugated_rust"))
    parts.append(_box("shutter-rail-a", (sx0 - 0.06, 0.0, G), (sx0, box_lo, G + 0.08), "steel_dark"))
    parts.append(_box("shutter-rail-b", (sx1, 0.0, G), (sx1 + 0.06, box_lo, G + 0.08), "steel_dark"))
    bar_lo = sy0 + 0.8
    parts.append(_box("shutter-bar", (sx0, bar_lo, G + 0.025), (sx1, bar_lo + 0.05, G + 0.065), "steel_dark"))
    rows = max(8, round((box_lo - bar_lo - 0.05) / 0.02))
    grid = [[(x, bar_lo + 0.05 + (box_lo - bar_lo - 0.05) * j / rows, G + 0.04 + (0.015 if j % 4 in (1, 2) else 0.0))
             for x in (sx0, sx1)] for j in range(rows + 1)]
    parts.append(g.thick_sheet("shutter-slats", grid, (0.0, 0.0, -0.006), "corrugated_rust"))
    parts.append(_box("interior-shutter", (sx0 + 0.001, sy0 + 0.001, G - POCKET + 0.001),
                      (sx1 - 0.001, 2.15 - 0.001, G - POCKET + 0.011), "rubber"))
    sprays.append(("rust-shutter", ((sx0 + sx1) / 2, 1.9, G + 0.05), 0.9,
                   ((1.08, 0.58, 0.32), 0.7, ("concrete_patch", "corrugated_rust"))))
    sprays.append(("oil-shutter", ((sx0 + sx1) / 2, 0.0, G + 0.04), 0.9, ((0.45, 0.42, 0.4), 0.6, ("steel_dark", "concrete_patch"))))

    # ---- posters: grid slots on the shopfront (poster side) plus the column fronts
    slots: list[tuple[float, float, float, float]] = []            # (x, y, wall z, max roll)
    p_start, p_end = 1.15, hx - COL_W - 0.05
    cx_ = p_start + 0.165
    while cx_ + 0.165 <= p_end + 1e-9:
        for py in (0.9, 1.42, 1.94):
            slots.append((-s * cx_, py, G, 0.05))
        cx_ += 0.45
    col_slots = [(sx * (hx - COL_W / 2), 1.5, F + COL_OUT, 0.03) for sx in (-1, 1)]
    count = rng.randint(6, 10)
    n_col = rng.randint(1, 2)
    rng.shuffle(slots)
    chosen = col_slots[:n_col] if s < 0 else col_slots[::-1][:n_col]
    chosen += slots[: count - n_col]
    for k, (px, py, wz, roll) in enumerate(chosen):
        jx, jy = (rng.uniform(-0.02, 0.02), rng.uniform(-0.015, 0.015)) if wz == G else (0.0, 0.0)
        sheet = g.box(f"poster-{k:02d}", (0.0, 0.0, 0.0), (POSTER_W, POSTER_H, 0.009), rng.choice(POSTER_MATS))
        parts.append(g.transformed_xyz(sheet, 0.0, 0.0, rng.uniform(-roll, roll), (px + jx, py + jy, wz + 0.001 + 0.0045)))

    # ---- sign board behind the TextRenderer anchor, neon edge on its face
    parts.append(_box("signboard", (board[0], board[1], F), (board[2], board[3], F + 0.06), "steel_dark"))
    edge_r = 0.01
    e = 0.04
    loop = [(board[0] + e, board[1] + e), (board[2] - e, board[1] + e), (board[2] - e, board[3] - e),
            (board[0] + e, board[3] - e), (board[0] + e, board[1] + e)]
    parts.append(_wall_tube("signedge-tube", loop, edge_r, F + 0.06 + edge_r, neon))

    # ---- neon motif (heart or crescent) on clips beside the sign
    outline = _heart(motif_size) if motif == "heart" else _crescent(motif_size)
    outline = [(mx + u, my + v) for u, v in outline]
    mz = F + FRAME_R + 0.021
    parts.append(_wall_tube("neonsign-tube", outline, FRAME_R, mz, neon))
    for k, i in enumerate(range(0, len(outline) - 1, (len(outline) - 1) // 4)):
        u, v = outline[i]
        parts.append(_box(f"neonsign-clip-{k}", (u - 0.01, v - 0.01, F), (u + 0.01, v + 0.01, mz - FRAME_R), "steel_dark"))

    # ---- facade AC units under windows, clear of the ads, board and motif
    busy = [board, motif_rect]
    candidates = []
    for x0w, y0w, x1w, _ in windows:
        ax = (x0w + x1w) / 2
        fy = y0w - 0.9
        body: Rect = (ax - 0.35, fy + 0.36, ax + 0.35, fy + 0.82)
        if any(_overlap(body, r, 0.1) for r in busy) or any(_overlap(body, r, 0.15) for r in ads):
            continue
        candidates.append(body)
    rng.shuffle(candidates)
    facade_ac: list[Rect] = []
    for body in candidates:
        if len(facade_ac) < 2 and not any(_overlap(body, o, 0.2) for o in facade_ac):
            facade_ac.append(body)
    for k, (bx0, by0, bx1, by1) in enumerate(sorted(facade_ac)):
        stem = f"ac-{k:02d}"
        ax = (bx0 + bx1) / 2
        z0 = F + AC_GAP
        parts.append(g.beveled_box(f"{stem}-body", (ax, (by0 + by1) / 2, z0 + 0.14), (0.7, by1 - by0, 0.28), 0.03, "steel_dark"))
        parts.append(g.cylinder(f"{stem}-fan", (ax + 0.08, (by0 + by1) / 2, z0 + 0.29), 0.17, 0.02, 10, "steel_bare", "Z"))
        for j, bxk in enumerate((ax - 0.25, ax + 0.25)):
            parts.append(_gusset(f"{stem}-bracket-{j}", bxk, [(F, by0), (z0 + 0.26, by0), (F, by0 - 0.17)], 0.02, "steel_dark"))
        others = [(o[0] + o[2]) / 2 for o in facade_ac if (o[0] + o[2]) / 2 != ax]
        side = (1 if ax > others[0] else -1) if others else rng.choice((-1, 1))   # run the pipe away from the neighbour
        px = ax + side * 0.35
        pm = (by0 + by1) / 2 - 0.08
        parts.append(g.tube(f"{stem}-pipe", [(px, pm, z0 + 0.14), (px + side * 0.12, pm, z0 + 0.14), (px + side * 0.12, pm, F)],
                            0.015, 6, "rubber"))
        # rust-brown drip streak running down the wall from the unit's drain side
        for drop, radius, strength in ((0.2, 0.45, 0.8), (0.65, 0.4, 0.6), (1.05, 0.32, 0.4)):
            sprays.append(("rust-ac", (ax - side * 0.2, by0 - drop, F + 0.02), radius, ((0.82, 0.55, 0.38), strength, CONCRETE)))

    # ---- roof: AC, water tank, posts for the layout's roof cables
    posts: list[tuple[float, float]] = []
    for c in data["cables"]:
        if spec["id"] not in c["attach"]:
            continue
        for end in (c["a"], c["b"]):
            p = _to_local(end, origin, yaw)
            if abs(end[1] - H) < 1e-6 and abs(p[0]) <= hx + 1e-6 and abs(p[2]) <= d / 2 + 1e-6:
                posts.append((p[0], p[2]))
    for k, (px, pz) in enumerate(posts):
        parts.append(g.cylinder(f"cablepost-{k}-foot", (px, R + 0.01, pz), 0.045, 0.02, 8, "steel_dark"))
        parts.append(g.pipe(f"cablepost-{k}", (px, R + 0.02, pz), (px, H + 0.1, pz), 0.035, "steel_bare", 8))

    def clear_of_posts(x: float, z: float, r: float) -> bool:
        return all(math.hypot(x - px, z - pz) > r + 0.15 for px, pz in posts)

    spots = [(sx * (hx - 0.25 - 0.65), sz) for sx in (-1, 1) for sz in (-d / 2 + 0.9, F - UPPER_T - 0.75)]
    rng.shuffle(spots)
    tank = next(p for p in spots if clear_of_posts(p[0], p[1], 0.65))
    tx, tz = tank
    legs = [g.pipe(f"l{k}", (tx + ux * 0.32, R, tz + uz * 0.32), (tx + ux * 0.32, R + 0.3, tz + uz * 0.32), 0.03, "steel_dark", 6)
            for k, (ux, uz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1)))]
    parts.append(g.combine("tank-stand", legs + [_box("deck", (tx - 0.42, R + 0.3, tz - 0.42), (tx + 0.42, R + 0.34, tz + 0.42),
                                                      "steel_dark")], "steel_dark"))
    parts.append(g.cylinder("tank-body", (tx, R + 0.34 + 0.45, tz), 0.42, 0.9, 12, "paint_teal_faded"))
    sprays.append(("rust-tank", (tx, R + 0.4, tz), 0.8, ((1.08, 0.6, 0.35), 0.6, ("paint_teal_faded", "steel_dark"))))
    roof_spot = next(p for p in spots if p != tank and clear_of_posts(p[0], p[1], 0.5))
    rx, rz = roof_spot
    parts.append(g.beveled_box("ac-roof-00-body", (rx, R + 0.21, rz), (0.8, 0.42, 0.34), 0.03, "steel_dark"))
    parts.append(g.cylinder("ac-roof-00-fan", (rx, R + 0.21, rz + 0.18), 0.16, 0.02, 10, "steel_bare", "Z"))
    sprays.append(("rust-ac", (rx, R + 0.02, rz), 0.7, ((0.9, 0.6, 0.42), 0.6, ("concrete_stained",))))

    # ---- side: downpipe from a hopper under the parapet, clamped to the wall
    dxw = dside * hx
    px = dxw + dside * 0.06
    hop0, hop1 = sorted((dxw, dxw + dside * 0.14))
    parts.append(_box("drain-hopper", (hop0, H - 0.35, dz - 0.1), (hop1, H - 0.12, dz + 0.1), "steel_dark"))
    parts.append(g.pipe("drain-pipe", (px, 0.15, dz), (px, H - 0.35, dz), 0.045, "steel_dark", 8))
    for k, cy in enumerate((0.8, (H - 0.35 + 0.8) / 2, H - 0.8)):
        c0, c1 = sorted((dxw, dxw + dside * 0.015))
        parts.append(_box(f"drain-clamp-{k}", (c0, cy - 0.02, dz - 0.04), (c1, cy + 0.02, dz + 0.04), "steel_dark"))
    sprays.append(("grime-drain", (px, 0.1, dz), 0.8, ((0.62, 0.58, 0.5), 0.6, CONCRETE)))

    # ---- wall anchors for cables that end on this club's walls
    for c in data["cables"]:
        if spec["id"] not in c["attach"]:
            continue
        for end in (c["a"], c["b"]):
            p = _to_local(end, origin, yaw)
            if abs(end[1] - H) < 1e-6:
                continue
            on_x, on_z = abs(abs(p[0]) - hx), abs(abs(p[2]) - d / 2)
            if min(on_x, on_z) > 0.05:
                continue
            k = sum(1 for q in parts if q.name.startswith("cable-anchor"))
            if on_x < on_z:
                a0, a1 = sorted((math.copysign(hx, p[0]), math.copysign(hx + 0.03, p[0])))
                parts.append(_box(f"cable-anchor-{k}", (a0, p[1] - 0.06, p[2] - 0.06), (a1, p[1] + 0.06, p[2] + 0.06), "steel_dark"))
            else:
                a0, a1 = sorted((math.copysign(d / 2, p[2]), math.copysign(d / 2 + 0.03, p[2])))
                parts.append(_box(f"cable-anchor-{k}", (p[0] - 0.06, p[1] - 0.06, a0), (p[0] + 0.06, p[1] + 0.06, a1), "steel_dark"))

    # ---- grime at the wall foot (shopfront, columns, sides)
    for gx in (-hx + 0.5, -s * 2.0, 0.0):
        sprays.append(("grime-foot", (gx, 0.0, G + 0.1), 1.3, ((0.55, 0.5, 0.44), 0.6, CONCRETE + ("rubber",))))
    for sx in (-1, 1):
        sprays.append(("grime-foot", (sx * hx, 0.0, F), 1.0, ((0.55, 0.5, 0.44), 0.55, CONCRETE)))

    # ---- bake the yaw, world-space sprays
    parts = [g.planarize(g.transformed(p, yaw, (0.0, 0.0, 0.0))) for p in parts]
    world_sprays, kinds = [], []
    for kind, centre, radius, (color, strength, mats) in sprays:
        wx, wy, wz = g.rotate_y(centre, yaw)
        world_sprays.append(Spray((wx + origin[0], wy, wz + origin[2]), radius, color, strength, materials=tuple(mats)))
        kinds.append(kind)
    light = g.rotate_y(((DOOR[0] + DOOR[2]) / 2, 2.6, G + 1.2), yaw)
    sign_world = g.rotate_y(anchor, yaw)
    meta: dict[str, Any] = {
        "sign_anchor": [round(v, 6) for v in sign_world],
        "light_anchor": [round(v, 6) for v in light],
        "neon": neon, "motif": motif, "floors": 1 + n_up,
        "sprays": world_sprays, "spray_kinds": kinds,
        "frame": {"yaw": yaw, "facade": F, "ground_face": G, "roof": R, "door": DOOR, "shutter": shutter,
                  "windows": windows, "board": board},
    }
    return g.Assembly("club", spec["id"], "nightlife", origin, parts, meta)


@register("nightlife")
def nightlife_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    return [build_club(spec, data) for spec in data["clubs"]]
