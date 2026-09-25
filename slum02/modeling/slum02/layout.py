"""Deterministic slum02 layout (Resonite XZ plane, Y up, metres) + validation + sightlines.

Conventions
-----------
* ``rotation`` is a yaw in degrees about +Y. Yaw 0 faces +Z, 90 faces +X, 180 faces -Z,
  270 faces -X (Resonite/Unity: rotating +Z by +90 deg about Y gives +X).
* ``footprint`` (towers) and ``size`` (stalls / clubs / shacks) are extents along the
  world X and Z axes *before* the residual yaw. The residual yaw is ``rotation`` snapped
  into [-45, 45) (``_residual``); it rotates the rectangle about its centre. Outer towers,
  stalls and clubs use multiples of 90 deg, so their residual is 0; inner towers carry a
  small +-4 deg jitter and shacks +-12 deg. ``front`` names the facade axis.
* Every generator task consumes this module (or ``content/slum02/layout.json``); all
  numbers are rounded to 3 dp so the JSON is byte-stable.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from modeling.slum02 import PROJECT_ROOT, SEED
from modeling.slum02.materials import MATERIALS

HALF = 40.0
EYE = 1.6
PLAZA = 10.0
STALL_DEPTH = 2.2
SHACK_GAP = 0.6
STREET_TOL = 0.05
SURFACE_TOL = 0.05
# Corner towers (8x8 at +-36) and the outer ring street (edge at 32.5) meet in a 0.5 x 0.5 m
# tip at each corner of the outer street; both values are fixed by the plan, so that tip
# (and only that) is tolerated for corner towers vs outer streets.
CORNER_STREET_TOL = 0.5 + 1e-6

HOLO_STATIC = ["holo_magenta", "holo_cyan", "holo_lime", "holo_orange"]
HOLO_SCROLL = ["holo_cyan_scroll", "holo_magenta_scroll"]

# Sightline tuning: extra metres added to rng heights of outer towers (cap 44 m).
HEIGHT_BOOST: dict[str, float] = {}
MAX_OUTER_HEIGHT = 44.0

ROT_FOR_FRONT = {"-z": 180.0, "+z": 0.0, "-x": 270.0, "+x": 90.0}


def _r(v: float) -> float:
    return round(float(v), 3)


def _rv(vs) -> list[float]:
    return [_r(v) for v in vs]


# --------------------------------------------------------------------------- geometry


def _yaw(x: float, z: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)


def _residual(deg: float) -> float:
    return ((deg + 45.0) % 90.0) - 45.0


def _extent(item: dict[str, Any]) -> tuple[float, float]:
    return tuple(item["footprint"] if "footprint" in item else item["size"])  # type: ignore[return-value]


def _aabb(item: dict[str, Any]) -> tuple[float, float, float, float]:
    """World XZ AABB (x0, z0, x1, z1) of a (residually rotated) footprint."""
    cx, cz = item["center"]
    w, d = _extent(item)
    r = math.radians(_residual(item.get("rotation", 0.0)))
    hx = w / 2 * abs(math.cos(r)) + d / 2 * abs(math.sin(r))
    hz = w / 2 * abs(math.sin(r)) + d / 2 * abs(math.cos(r))
    return cx - hx, cz - hz, cx + hx, cz + hz


def _street_rect(s: dict[str, Any]) -> tuple[float, float, float, float]:
    return s["min"][0], s["min"][1], s["max"][0], s["max"][1]


def _gap(a, b) -> float:
    """Separation of two XZ rects; negative = overlap depth (min over axes)."""
    sx = max(a[0] - b[2], b[0] - a[2])
    sz = max(a[1] - b[3], b[1] - a[3])
    return max(sx, sz)


def _to_local(item: dict[str, Any], x: float, z: float) -> tuple[float, float]:
    cx, cz = item["center"]
    return _yaw(x - cx, z - cz, -_residual(item.get("rotation", 0.0)))


def _to_world(item: dict[str, Any], lx: float, lz: float) -> tuple[float, float]:
    cx, cz = item["center"]
    wx, wz = _yaw(lx, lz, _residual(item.get("rotation", 0.0)))
    return cx + wx, cz + wz


def _top(item: dict[str, Any]) -> float:
    return item.get("core_height", item["height"])


def _wall_point(item: dict[str, Any], toward: tuple[float, float], y: float, margin: float = 0.4) -> list[float]:
    """Point on the wall of ``item`` that faces ``toward`` (world XZ), at height y."""
    w, d = _extent(item)
    lx, lz = _to_local(item, *toward)
    if abs(lx) / (w / 2) >= abs(lz) / (d / 2):
        px = math.copysign(w / 2, lx)
        pz = max(-d / 2 + margin, min(d / 2 - margin, lz))
    else:
        pz = math.copysign(d / 2, lz)
        px = max(-w / 2 + margin, min(w / 2 - margin, lx))
    x, z = _to_world(item, px, pz)
    return _rv([x, y, z])


def _roof_point(item: dict[str, Any], toward: tuple[float, float], inset: float = 0.3) -> list[float]:
    """Point on the roof of ``item``, pushed toward ``toward`` but ``inset`` inside the edge."""
    w, d = _extent(item)
    lx, lz = _to_local(item, *toward)
    px = max(-w / 2 + inset, min(w / 2 - inset, lx))
    pz = max(-d / 2 + inset, min(d / 2 - inset, lz))
    x, z = _to_world(item, px, pz)
    return _rv([x, item["height"], z])


def _on_surface(item: dict[str, Any], p) -> bool:
    w, d = _extent(item)
    lx, lz = _to_local(item, p[0], p[2])
    tol = SURFACE_TOL
    if abs(lx) > w / 2 + tol or abs(lz) > d / 2 + tol:
        return False
    on_roof = abs(p[1] - item["height"]) <= tol
    on_wall = min(abs(w / 2 - abs(lx)), abs(d / 2 - abs(lz))) <= tol and -tol <= p[1] <= item["height"] + tol
    return on_roof or on_wall


def quat_mul(a, b) -> list[float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ]


def quat_rotate(q, v) -> list[float]:
    qv = quat_mul(quat_mul(q, [v[0], v[1], v[2], 0.0]), [-q[0], -q[1], -q[2], q[3]])
    return qv[:3]


def look_rotation(src, dst) -> list[float]:
    """Quaternion [x,y,z,w] turning local +Z (Resonite light/camera forward) from src to dst."""
    d = [dst[i] - src[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in d))
    dx, dy, dz = (c / n for c in d)
    yaw = math.atan2(dx, dz)
    pitch = math.asin(max(-1.0, min(1.0, -dy)))  # +pitch about X tips +Z downward
    qy = [0.0, math.sin(yaw / 2), 0.0, math.cos(yaw / 2)]
    qx = [math.sin(pitch / 2), 0.0, 0.0, math.cos(pitch / 2)]
    return [round(c, 6) for c in quat_mul(qy, qx)]


# --------------------------------------------------------------------------- builders


def _street(id_: str, kind: str, x0, z0, x1, z1) -> dict[str, Any]:
    return {"id": id_, "kind": kind, "min": [x0, z0], "max": [x1, z1]}


def _streets() -> list[dict[str, Any]]:
    s = [
        _street("ring-n", "ring", -14, 10, 14, 14), _street("ring-s", "ring", -14, -14, 14, -10),
        _street("ring-e", "ring", 10, -10, 14, 10), _street("ring-w", "ring", -14, -10, -10, 10),
        _street("outer-n", "outer", -32.5, 29, 32.5, 32.5), _street("outer-s", "outer", -32.5, -32.5, 32.5, -29),
        _street("outer-e", "outer", 29, -29, 32.5, 29), _street("outer-w", "outer", -32.5, -29, -29, 29),
        _street("lane", "lane", -27, -19.5, 27, -16.5),
    ]
    legs = {
        "n": [(-1.5, 14, 1.5, 21), (-1.5, 21, 4.5, 24), (1.5, 24, 4.5, 29)],
        "s": [(-1.5, -21, 1.5, -14), (-4.5, -24, 1.5, -21), (-4.5, -29, -1.5, -24)],
        "e": [(14, -1.5, 21, 1.5), (21, -4.5, 24, 1.5), (24, -4.5, 29, -1.5)],
        "w": [(-21, -1.5, -14, 1.5), (-24, -1.5, -21, 4.5), (-29, 1.5, -24, 4.5)],
    }
    for side, rects in legs.items():
        for k, r in enumerate(rects):
            s.append(_street(f"radial-{side}{k}", "radial", *r))
    return s


def _outer_towers(rng: random.Random) -> list[dict[str, Any]]:
    towers: list[dict[str, Any]] = []
    corners = [((36, 36), "towers-a", "-z"), ((-36, 36), "towers-a", "-z"), ((36, -36), "towers-b", "+z"), ((-36, -36), "towers-b", "+z")]
    for (cx, cz), sector, front in corners:
        towers.append({"center": [cx, cz], "footprint": [8.0, 8.0], "height": round(rng.uniform(34, 40), 2),
                       "sector": sector, "front": front, "side": None, "span": None})
    sides = [("n", "towers-a", "-z"), ("e", "towers-a", "-x"), ("s", "towers-b", "+z"), ("w", "towers-b", "+x")]
    for side, sector, front in sides:
        widths = [rng.uniform(19, 24) for _ in range(3)]
        scale = 64.0 / sum(widths)
        cursor = -32.0
        for k, w in enumerate(widths):
            span = w * scale
            lo, hi = cursor - 0.75, cursor + span + 0.75   # 1.5 m overlap with neighbours/corners
            cursor += span
            along = (lo + hi) / 2
            length = hi - lo
            inset = 32.5 if k % 2 == 0 else 33.5
            depth = 6.5
            across = inset + depth / 2
            near_corner = 4.0 if k in (0, 2) else 0.0
            height = round(rng.uniform(24, 32) + near_corner, 2)
            if side in ("n", "s"):
                center = [round(along, 3), round(across if side == "n" else -across, 3)]
                fp = [round(length, 3), depth]
            else:
                center = [round(across if side == "e" else -across, 3), round(along, 3)]
                fp = [depth, round(length, 3)]
            towers.append({"center": center, "footprint": fp, "height": height, "sector": sector, "front": front,
                           "side": side, "span": (lo, hi), "inset": inset})
    out = []
    for k, t in enumerate(towers, start=1):
        tid = f"tower-{k:02d}"
        h = t["height"]
        if tid in HEIGHT_BOOST:
            h = round(min(MAX_OUTER_HEIGHT, h + HEIGHT_BOOST[tid]), 2)
        out.append({"id": tid, "sector": t["sector"], "role": "outer", "center": t["center"],
                    "footprint": t["footprint"], "height": h, "core_height": round(h - 2.0, 2),
                    "rotation": ROT_FOR_FRONT[t["front"]], "front": t["front"], "seed": SEED + k})
    return out


# Inner derelict blocks. tower-20 deviates from the plan table ((21.5, -22.5) 11x10): the
# tabled footprint spans z -27.5..-17.5 and would cut 2 m into the stall lane
# (z -19.5..-16.5) and the south stall row. It is pulled back to the band between the
# south stall row (z <= -21.7) and the outer street (z >= -29) and made 6.5 m deep.
INNER_TABLE = [
    ("tower-17", (-8.5, 22.5), (9.0, 11.0), 14.0),
    ("tower-18", (9.0, 19.5), (8.0, 9.0), 18.0),
    ("tower-19", (21.5, 21.5), (11.0, 11.0), 20.0),
    ("tower-20", (21.5, -25.35), (11.0, 6.5), 16.0),
    ("tower-21", (-21.5, -24.5), (10.0, 8.0), 12.0),
    ("tower-22", (-22.0, 21.0), (9.0, 10.0), 15.0),
]


def _facing_centre(x: float, z: float) -> str:
    if abs(z) >= abs(x):
        return "-z" if z > 0 else "+z"
    return "-x" if x > 0 else "+x"


def _inner_towers(rng: random.Random) -> list[dict[str, Any]]:
    out = []
    for k, (tid, (cx, cz), (w, d), h) in enumerate(INNER_TABLE, start=17):
        front = _facing_centre(cx, cz)
        rot = ROT_FOR_FRONT[front] + rng.uniform(-4, 4)
        out.append({"id": tid, "sector": "towers-c", "role": "inner", "center": [cx, cz], "footprint": [w, d],
                    "height": h, "core_height": round(h - 3.0, 2), "rotation": _r(rot % 360.0), "front": front,
                    "seed": SEED + k})
    return out


STALL_XS = [-24, -19.5, -15, -10.5, 6, 10.5, 15, 19.5, 24]


def _stalls(rng: random.Random, towers, streets) -> list[dict[str, Any]]:
    blockers = [_aabb(t) for t in towers]
    out: list[dict[str, Any]] = []
    for row, cz, front in (("n", -15.4, "-z"), ("s", -20.6, "+z")):
        picked = 0
        for x in STALL_XS:
            if picked == 6:
                break
            w = _r(rng.uniform(3.2, 3.8))
            rect = (x - w / 2, cz - STALL_DEPTH / 2, x + w / 2, cz + STALL_DEPTH / 2)
            if any(_gap(rect, b) < 0 for b in blockers):
                continue
            if any(_gap(rect, _street_rect(s)) < -STREET_TOL + 1e-9 for s in streets):
                continue
            picked += 1
            out.append({"center": [x, cz], "size": [w, STALL_DEPTH], "rotation": ROT_FOR_FRONT[front], "front": front,
                        "row": row, "height": _r(rng.uniform(2.6, 3.0))})
    return [{"id": f"stall-{k:02d}", **s, "seed": SEED + 200 + k} for k, s in enumerate(out, start=1)]


CLUB_TABLE = [
    ((17.6, 6.5), (6.0, 7.0), 7.0, "-x", "neon_pink"),
    ((17.6, -8.0), (6.0, 7.0), 8.0, "-x", "neon_magenta"),
    ((26.0, 8.0), (5.5, 7.0), 6.0, "+x", "neon_red"),
    ((26.0, -10.5), (5.5, 6.0), 7.0, "+x", "neon_pink"),
]


def _clubs() -> list[dict[str, Any]]:
    return [{"id": f"club-{k:02d}", "center": list(c), "rotation": ROT_FOR_FRONT[f], "front": f, "size": list(s),
             "height": h, "neon": n, "seed": SEED + 300 + k}
            for k, (c, s, h, f, n) in enumerate(CLUB_TABLE, start=1)]


# Candidate regions: the open bands of the W block x[-28.5,-14.5] (between the stall row,
# the west radial and tower-22) plus the SW pocket between tower-21 and the south radial.
# The rest of the W block is occupied by towers/lane/radials, so sampling there only wastes
# the 400-try budget.
SHACK_REGIONS = [(-28.5, -14.3, -14.5, -1.5), (-28.5, 1.5, -14.5, 15.9), (-16.5, -29.0, -4.5, -21.0)]


def _shacks(rng: random.Random, blocked_rects) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rects = list(blocked_rects)
    areas = [(r[2] - r[0]) * (r[3] - r[1]) for r in SHACK_REGIONS]
    for _ in range(400):
        if len(out) == 12:
            break
        pick = rng.uniform(0, sum(areas))
        idx = 0
        while pick > areas[idx] and idx < len(areas) - 1:
            pick -= areas[idx]
            idx += 1
        x0, z0, x1, z1 = SHACK_REGIONS[idx]
        size = [_r(rng.uniform(2.6, 4.2)), _r(rng.uniform(2.4, 3.6))]
        rot = _r(rng.uniform(-12, 12))
        hx, hz = _aabb({"center": [0.0, 0.0], "size": size, "rotation": rot})[2:]
        cand = {"center": [_r(rng.uniform(x0 + hx, x1 - hx)), _r(rng.uniform(z0 + hz, z1 - hz))],
                "size": size, "rotation": rot}
        box = _aabb(cand)
        if box[0] < x0 or box[1] < z0 or box[2] > x1 or box[3] > z1:
            continue
        if any(_gap(box, r) < SHACK_GAP for r in rects):
            continue
        rects.append(box)
        out.append(cand)
    assert len(out) == 12, f"only {len(out)} shacks placed"
    return [{"id": f"shack-{k:02d}", "center": s["center"], "rotation": s["rotation"], "size": s["size"],
             "height": _r(2.4 + 0.25 * (k % 4)), "seed": SEED + 400 + k}
            for k, s in enumerate(out, start=1)]


def _outer_on(towers, side: str, along: float) -> dict[str, Any]:
    """Outer side tower on ``side`` whose inward face is nearest the centre at ``along``."""
    best = None
    for t in towers:
        if t["role"] != "outer" or t["footprint"] == [8.0, 8.0]:
            continue
        x0, z0, x1, z1 = _aabb(t)
        if side == "n" and t["front"] == "-z" and x0 <= along <= x1:
            key = z0
        elif side == "s" and t["front"] == "+z" and x0 <= along <= x1:
            key = -z1
        elif side == "e" and t["front"] == "-x" and z0 <= along <= z1:
            key = x0
        elif side == "w" and t["front"] == "+x" and z0 <= along <= z1:
            key = -x1
        else:
            continue
        if best is None or key < best[0]:
            best = (key, t)
    assert best is not None, (side, along)
    return best[1]


def _face_xz(tower: dict[str, Any], side: str, along: float) -> list[float]:
    x0, z0, x1, z1 = _aabb(tower)
    return {"n": [along, z0], "s": [along, z1], "e": [x0, along], "w": [x1, along]}[side]


def _bridges(rng: random.Random, towers) -> list[dict[str, Any]]:
    by = {t["id"]: t for t in towers}
    specs = []
    # inner -> outer across the outer street
    for inner_id, side in (("tower-19", "e"), ("tower-22", "w"), ("tower-20", "s")):
        t = by[inner_id]
        far = {"e": (40.0, t["center"][1]), "w": (-40.0, t["center"][1]), "s": (t["center"][0], -40.0)}[side]
        a = _wall_point(t, far, 0.0, margin=1.0)
        along = a[2] if side in ("e", "w") else a[0]
        b = _face_xz(_outer_on(towers, side, along), side, along)
        specs.append((inner_id, [a[0], a[2]], b, t["core_height"] - 2.0))
    # outer -> outer diagonally over the NE corner of the outer street
    tn, te = _outer_on(towers, "n", 26.0), _outer_on(towers, "e", 26.0)
    specs.append((None, _face_xz(tn, "n", 26.0), _face_xz(te, "e", 26.0), 14.0))
    out = []
    for k, (_, a, b, ymax) in enumerate(specs, start=1):
        y = min(ymax, rng.uniform(8, 14))
        out.append({"id": f"bridge-{k:02d}", "a": _rv(a), "b": _rv(b), "y": _r(max(8.0, y)), "width": 1.4})
    return out


AD_TEXTS = ["電脳接続 今すぐ", "義体クリニック", "合成酒 NOVA", "ネオ東京不動産", "夢見る電脳", "24H 修理",
            "記憶 買います", "NOVA CORP", "闇医者 予約制", "義眼 最新型", "サイバー保険", "夜間営業中"]


def _panel_on_outer(rng: random.Random, t: dict[str, Any]) -> dict[str, Any]:
    x0, z0, x1, z1 = _aabb(t)
    side = {"-z": "n", "+z": "s", "-x": "e", "+x": "w"}[t["front"]]
    lo, hi = (x0, x1) if side in ("n", "s") else (z0, z1)
    w = rng.uniform(4, 8)
    h = rng.uniform(3, 6)
    usable_lo, usable_hi = lo + 0.75 + 0.3 + w / 2, hi - 0.75 - 0.3 - w / 2
    along = max(usable_lo, min(usable_hi, (lo + hi) / 2 + rng.uniform(-2, 2)))
    top_cap = min(26.0, t["core_height"] - 1.0)
    bottom = rng.uniform(8.0, top_cap - h)
    y = bottom + h / 2
    face = {"n": z0, "s": z1, "e": x0, "w": x1}[side]
    inward = {"n": -1, "s": 1, "e": -1, "w": 1}[side]
    pos_across = face + inward * 0.12
    if side in ("n", "s"):
        pos = [along, y, pos_across]
        lo_b = [along - w / 2, y - h / 2, min(face + inward * 0.07, face + inward * 0.17)]
        hi_b = [along + w / 2, y + h / 2, max(face + inward * 0.07, face + inward * 0.17)]
    else:
        pos = [pos_across, y, along]
        lo_b = [min(face + inward * 0.07, face + inward * 0.17), y - h / 2, along - w / 2]
        hi_b = [max(face + inward * 0.07, face + inward * 0.17), y + h / 2, along + w / 2]
    return {"position": _rv(pos), "rotation": t["rotation"], "size": _rv([w, h]), "mount": t["id"],
            "_box": (_rv(lo_b), _rv(hi_b))}


FLOAT_ANCHORS = [  # (x, z, yaw) over streets; yaw faces along the street
    (-6.0, 12.0, 90.0), (6.0, -12.0, 270.0), (12.0, 5.0, 0.0), (-12.0, -5.0, 180.0),
    (0.0, 17.5, 180.0), (17.5, 0.0, 270.0), (-17.5, 0.0, 90.0), (-1.5, -22.5, 0.0),
    (-6.0, -18.0, 90.0), (14.0, -18.0, 270.0),
]


def _ads(rng: random.Random, towers, clubs):
    ads: list[dict[str, Any]] = []
    boxes: dict[int, tuple] = {}
    side_towers = [t for t in towers if t["role"] == "outer" and t["footprint"] != [8.0, 8.0]]
    for k, t in enumerate(side_towers):
        p = _panel_on_outer(rng, t)
        boxes[len(ads)] = p.pop("_box")
        ads.append({"kind": "wall", **p, "material": HOLO_STATIC[k % 4], "anim": "none"})
    for k, (x, z, yaw) in enumerate(FLOAT_ANCHORS):
        w = rng.uniform(1.6, 3.0)
        h = w * rng.uniform(0.5, 0.8)
        y = rng.uniform(4.5, 9.0)
        ads.append({"kind": "float", "position": _rv([x, y, z]), "rotation": yaw, "size": _rv([w, h]),
                    "material": HOLO_STATIC[(k + 1) % 4], "anim": "spin" if k % 2 == 1 and k < 8 else "none"})
    mounts = [t for t in towers if t["role"] == "inner"] + list(clubs[:2])
    for k, m in enumerate(mounts):
        is_club = m["id"].startswith("club")
        h_max = min(6.0, m["height"] - 3.0) if is_club else 6.0
        h = rng.uniform(4.0, h_max) if h_max > 4.0 else 4.0
        bottom = 2.5 if is_club else 3.0
        lx_off = rng.uniform(-0.25, 0.25)
        w, d = _extent(m)
        front = m["front"]
        # local offset of a point 0.12 m in front of the facade centre (+ jitter along it)
        if front in ("-z", "+z"):
            sgn = -1 if front == "-z" else 1
            lx, lz = lx_off * w, sgn * (d / 2 + 0.12)
        else:
            sgn = -1 if front == "-x" else 1
            lx, lz = sgn * (w / 2 + 0.12), lx_off * d
        x, z = _to_world(m, lx, lz)
        scroll = k < 6
        ads.append({"kind": "vertical", "position": _rv([x, bottom + h / 2, z]), "rotation": m["rotation"],
                    "size": _rv([1.2, h]), "mount": m["id"],
                    "material": HOLO_SCROLL[k % 2] if scroll else HOLO_STATIC[k % 4],
                    "anim": "scroll" if scroll else "none"})
    out = []
    for k, a in enumerate(ads, start=1):
        text = AD_TEXTS[(k - 1) % len(AD_TEXTS)]
        out.append({"id": f"ad-{k:02d}", "kind": a["kind"], "position": a["position"], "rotation": a["rotation"],
                    "size": a["size"], "material": a["material"], "anim": a["anim"], "text": text,
                    **({"mount": a["mount"]} if "mount" in a else {})})
    wall_boxes = {out[i]["id"]: b for i, b in boxes.items()}
    return out, wall_boxes


STALL_SIGNS = ["ジャンク", "中古義体", "基板買取", "修理 即日", "電池", "ケーブル量り売り"]
CLUB_SIGNS = ["夜蝶", "ピンクの月", "個室あり", "CLUB 天國"]


def _signs(stalls, clubs, ads) -> list[dict[str, Any]]:
    signs: list[dict[str, Any]] = []
    north = [s for s in stalls if s["row"] == "n"]
    south = [s for s in stalls if s["row"] == "s"]
    chosen = north[0::2][:3] + south[1::2][:3]
    for s, text in zip(chosen, STALL_SIGNS):
        cx, cz = s["center"]
        fz = cz - STALL_DEPTH / 2 - 0.05 if s["front"] == "-z" else cz + STALL_DEPTH / 2 + 0.05
        signs.append({"position": _rv([cx, s["height"] + 0.3, fz]), "rotation": s["rotation"], "text": text,
                      "size": 0.35, "color": [1.0, 0.85, 0.55, 1.0], "target": s["id"]})
    for c, text in zip(clubs, CLUB_SIGNS):
        cx, cz = c["center"]
        w = c["size"][0]
        fx = cx - w / 2 - 0.08 if c["front"] == "-x" else cx + w / 2 + 0.08
        signs.append({"position": _rv([fx, c["height"] - 1.2, cz]), "rotation": c["rotation"], "text": text,
                      "size": 0.8, "color": [1.0, 0.3, 0.7, 1.0], "target": c["id"]})
    for a in [a for a in ads if a["kind"] == "wall"][:6]:
        yaw = math.radians(a["rotation"])
        nx, nz = math.sin(yaw), math.cos(yaw)
        p = a["position"]
        signs.append({"position": _rv([p[0] + nx * 0.03, p[1], p[2] + nz * 0.03]), "rotation": a["rotation"],
                      "text": a["text"], "size": _r(a["size"][1] * 0.25), "color": [0.95, 0.95, 1.0, 1.0],
                      "target": a["id"]})
    return [{"id": f"sign-{k:02d}", **s} for k, s in enumerate(signs, start=1)]


def _cables(rng: random.Random, towers, stalls, clubs) -> list[dict[str, Any]]:
    by = {x["id"]: x for x in [*towers, *stalls, *clubs]}

    def stall_at(row: str, x: float) -> str:
        return next(s["id"] for s in stalls if s["row"] == row and s["center"][0] == x)

    west = _outer_on(towers, "w", 21.0)["id"]
    east = _outer_on(towers, "e", 21.5)["id"]
    north = _outer_on(towers, "n", -8.5)["id"]
    specs = [  # (id_a, mode_a, y_a, id_b, mode_b, y_b)
        ("tower-17", "wall", 7.5, "tower-18", "wall", 8.0),
        ("tower-18", "wall", 9.0, "tower-19", "wall", 8.5),
        ("tower-17", "wall", 6.5, "tower-22", "wall", 7.0),
        ("tower-22", "wall", 9.0, west, "wall", 10.0),
        ("tower-19", "wall", 11.0, east, "wall", 12.0),
        ("tower-17", "wall", 8.0, north, "wall", 9.0),
        ("club-01", "roof", None, "club-02", "roof", None),
        ("club-01", "roof", None, "club-03", "wall", 4.5),
        ("club-02", "roof", None, "club-04", "wall", 5.0),
        ("club-03", "roof", None, "tower-19", "wall", 10.0),
        (stall_at("n", -10.5), "roof", None, stall_at("s", -10.5), "roof", None),
        (stall_at("n", 6), "roof", None, stall_at("s", 6), "roof", None),
        ("tower-20", "wall", 6.0, stall_at("s", 19.5), "roof", None),
        ("tower-21", "wall", 5.0, stall_at("n", -19.5), "roof", None),
    ]

    def endpoint(item, mode, y, other):
        target = tuple(other["center"])
        return _wall_point(item, target, y) if mode == "wall" else _roof_point(item, target)

    out = []
    for k, (ia, ma, ya, ib, mb, yb) in enumerate(specs, start=1):
        a_item, b_item = by[ia], by[ib]
        a = endpoint(a_item, ma, ya, b_item)
        b = endpoint(b_item, mb, yb, a_item)
        length = math.dist(a, b)
        sag = 0.04 * length + rng.uniform(0.1, 0.4)
        out.append({"id": f"cable-{k:02d}", "a": a, "b": b, "sag": _r(sag), "attach": [ia, ib]})
    return out


def _lights(stalls, clubs) -> list[dict[str, Any]]:
    L: list[dict[str, Any]] = []
    ident = [0.0, 0.0, 0.0, 1.0]

    def point(pos, color, intensity, rng_, shadow="None"):
        L.append({"type": "Point", "position": _rv(pos), "rotation": ident, "color": color,
                  "intensity": intensity, "range": rng_, "spot_angle": 0.0, "shadow": shadow})

    def spot(pos, aim, color, intensity, rng_, angle, shadow, target):
        L.append({"type": "Spot", "position": _rv(pos), "rotation": look_rotation(pos, aim), "color": color,
                  "intensity": intensity, "range": rng_, "spot_angle": angle, "shadow": shadow,
                  "target": target, "aim": _rv(aim)})

    point([-5.5, 1.3, 4.0], [1.0, 0.45, 0.12, 1.0], 2.2, 9.0, "Soft")                       # fire barrel
    spot([0.5, 7.6, -3.0], [9.2, 5.0, 0.0], [1.0, 0.78, 0.5, 1.0], 3.0, 18.0, 55.0, "Hard", "east-wall")
    c1 = clubs[0]
    fx = c1["center"][0] - c1["size"][0] / 2 - 0.3
    spot([fx, 4.2, c1["center"][1]], [fx - 3.0, 0.0, c1["center"][1]], [1.0, 0.08, 0.1, 1.0], 2.0, 9.0, 70.0,
         "Hard", c1["id"])
    for c, col in zip(clubs[1:], ([1.0, 0.1, 0.6, 1.0], [1.0, 0.05, 0.05, 1.0], [1.0, 0.3, 0.6, 1.0])):
        w = c["size"][0]
        fx = c["center"][0] - w / 2 - 0.6 if c["front"] == "-x" else c["center"][0] + w / 2 + 0.6
        point([fx, 3.0, c["center"][1]], col, 1.6, 7.0)
    for s in [s for s in stalls if s["row"] == "n"][::2] + [s for s in stalls if s["row"] == "s"][1::2]:
        point([s["center"][0], s["height"] - 0.3, s["center"][1]], [1.0, 0.6, 0.25, 1.0], 1.2, 5.0)
    for x, z in ((12.0, 12.0), (-12.0, 12.0), (-12.0, -12.0), (12.0, -12.0)):
        point([x, 4.5, z], [0.55, 0.8, 1.0, 1.0], 1.0, 9.0)
    for pos, col in (([0.0, 3.5, 22.5], [1.0, 0.1, 0.7, 1.0]), ([22.5, 3.5, -1.5], [0.1, 0.9, 1.0, 1.0]),
                     ([-22.5, 3.5, 1.5], [0.55, 1.0, 0.1, 1.0]), ([-1.5, 3.5, -22.5], [1.0, 0.4, 0.05, 1.0])):
        point(pos, col, 1.3, 7.0)
    point([-6.0, 5.0, -6.0], [0.5, 0.6, 0.8, 1.0], 0.6, 12.0)
    point([5.0, 6.0, 6.0], [0.5, 0.6, 0.8, 1.0], 0.6, 12.0)
    point([-21.0, 3.0, -6.0], [1.0, 0.55, 0.25, 1.0], 1.0, 7.0)
    point([-21.0, 3.0, 9.0], [1.0, 0.55, 0.25, 1.0], 1.0, 7.0)
    point([-3.0, 4.0, -18.0], [0.1, 0.9, 1.0, 1.0], 1.0, 7.0)
    return [{"id": f"light-{k:02d}", **l} for k, l in enumerate(L, start=1)]


def _backdrop(rng: random.Random) -> dict[str, Any]:
    masses = []
    for k in range(18):
        ang = math.radians(k * 20.0 + rng.uniform(-6, 6))
        rad = rng.uniform(60, 180)
        masses.append({"id": f"mass-{k + 1:02d}", "center": _rv([math.sin(ang) * rad, math.cos(ang) * rad]),
                       "footprint": _rv([rng.uniform(18, 45), rng.uniform(18, 45)]),
                       "height": _r(rng.uniform(80, 200)), "seed": SEED + 500 + k})
    return {"masses": masses, "ground_radius": 220.0}


def _plaza_features(rng: random.Random) -> dict[str, Any]:
    columns = [
        [-7.5, 7.5, 0.0, _r(rng.uniform(4, 9))],
        [0.5, -3.0, 0.0, 8.0],                            # carries the spray-wall floodlight
        [6.0, 7.0, _r(rng.uniform(8, 25)), _r(rng.uniform(4, 9))],
        [-8.0, -4.0, _r(rng.uniform(8, 25)), _r(rng.uniform(4, 9))],
        [-2.5, 8.5, 0.0, _r(rng.uniform(4, 9))],
    ]
    return {
        "fire_barrel": [-5.5, 4.0],
        "car": [3.5, -5.5, 23.0],
        "columns": columns,
        "machines": [[-4.5, -6.5, 0.0, "press"], [1.5, 6.0, 15.0, "conveyor"], [6.5, -1.0, 0.0, "tank"]],
        "pits": [[-2.0, -9.0, 1.0, -7.0], [2.5, 1.0, 5.0, 3.0]],
        "exits": [[-10.3, -2.0, -9.7, 2.0], [3.0, -10.3, 7.0, -9.7]],
    }


def _occluders(towers, bridges, wall_boxes) -> list[dict[str, Any]]:
    occ = []
    for t in towers:
        if t["role"] != "outer":
            continue
        x0, z0, x1, z1 = _aabb(t)
        occ.append({"id": f"occ-{t['id']}", "source": t["id"], "min": _rv([x0, 0.0, z0]),
                    "max": _rv([x1, t["core_height"], z1])})
    for b in bridges:
        (ax, az), (bx, bz) = b["a"], b["b"]
        dx, dz = bx - ax, bz - az
        n = math.hypot(dx, dz)
        px, pz = -dz / n * b["width"] / 2, dx / n * b["width"] / 2
        xs = [ax + px, ax - px, bx + px, bx - px]
        zs = [az + pz, az - pz, bz + pz, bz - pz]
        occ.append({"id": f"occ-{b['id']}", "source": b["id"], "min": _rv([min(xs), b["y"] - 0.6, min(zs)]),
                    "max": _rv([max(xs), b["y"] + 0.6, max(zs)])})
    for ad_id, (lo, hi) in wall_boxes.items():
        occ.append({"id": f"occ-{ad_id}", "source": ad_id, "min": lo, "max": hi})
    return occ


def build_layout() -> dict[str, Any]:
    rng = random.Random(SEED)
    streets = _streets()
    towers = _outer_towers(rng) + _inner_towers(rng)
    stalls = _stalls(rng, towers, streets)
    clubs = _clubs()
    blocked = [_street_rect(s) for s in streets] + [_aabb(x) for x in [*towers, *stalls, *clubs]]
    blocked.append((-PLAZA, -PLAZA, PLAZA, PLAZA))
    shacks = _shacks(rng, blocked)
    bridges = _bridges(rng, towers)
    ads, wall_boxes = _ads(rng, towers, clubs)
    signs = _signs(stalls, clubs, ads)
    cables = _cables(rng, towers, stalls, clubs)
    lights = _lights(stalls, clubs)
    backdrop = _backdrop(rng)
    plaza_features = _plaza_features(rng)
    occluders = _occluders(towers, bridges, wall_boxes)
    data = {
        "seed": SEED,
        "half": HALF,
        "plaza": {"min": [-PLAZA, -PLAZA], "max": [PLAZA, PLAZA]},
        "east_wall": {"center": [9.6, 0.0, 0.0], "size": [0.8, 10.0, 20.0]},
        "streets": streets,
        "towers": towers,
        "stalls": stalls,
        "clubs": clubs,
        "shacks": shacks,
        "ads": ads,
        "signs": signs,
        "cables": cables,
        "bridges": bridges,
        "lights": lights,
        "occluders": occluders,
        "backdrop": backdrop,
        "plaza_features": plaza_features,
    }
    return json.loads(json.dumps(data))  # normalise tuples -> lists


# --------------------------------------------------------------------------- validation


def _outer_adjacent(towers) -> set[frozenset[str]]:
    """Outer tower pairs allowed to overlap: neighbours around the perimeter, including
    the two side towers that meet at a corner block."""
    outer = [t for t in towers if t["role"] == "outer"]
    outer.sort(key=lambda t: math.atan2(t["center"][0], t["center"][1]))
    n = len(outer)
    pairs = set()
    for i in range(n):
        for step in (1, 2):
            pairs.add(frozenset((outer[i]["id"], outer[(i + step) % n]["id"])))
    return pairs


def validate_layout(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    towers, stalls, clubs, shacks = data["towers"], data["stalls"], data["clubs"], data["shacks"]
    streets = data["streets"]
    footprints = [*towers, *stalls, *clubs, *shacks]
    plaza = (*data["plaza"]["min"], *data["plaza"]["max"])
    corner_ids = {t["id"] for t in towers if t["role"] == "outer" and t["footprint"] == [8.0, 8.0]}

    # 1. inside 80x80
    for it in footprints:
        x0, z0, x1, z1 = _aabb(it)
        if x0 < -HALF - 1e-6 or z0 < -HALF - 1e-6 or x1 > HALF + 1e-6 or z1 > HALF + 1e-6:
            issues.append(f"{it['id']} outside bounds")
    # 2. plaza + streets
    for it in footprints:
        box = _aabb(it)
        if _gap(box, plaza) < -1e-6:
            issues.append(f"{it['id']} intrudes plaza")
        for s in streets:
            tol = STREET_TOL
            if it["id"] in corner_ids and s["kind"] == "outer":
                tol = CORNER_STREET_TOL
            if _gap(box, _street_rect(s)) <= -tol:
                issues.append(f"{it['id']} intrudes street {s['id']}")
    # 3. footprint overlaps
    allowed = _outer_adjacent(towers)
    for i, a in enumerate(footprints):
        for b in footprints[i + 1:]:
            if _gap(_aabb(a), _aabb(b)) >= -1e-6:
                continue
            if a.get("role") == "outer" and b.get("role") == "outer" and frozenset((a["id"], b["id"])) in allowed:
                continue
            issues.append(f"overlap {a['id']} / {b['id']}")
    # 4. shack spacing
    for sh in shacks:
        box = _aabb(sh)
        for other in footprints:
            if other is sh:
                continue
            if _gap(box, _aabb(other)) < SHACK_GAP - 1e-6:
                issues.append(f"{sh['id']} too close to {other['id']}")
        for s in streets:
            if _gap(box, _street_rect(s)) < SHACK_GAP - 1e-6:
                issues.append(f"{sh['id']} too close to street {s['id']}")
    # 5. lights
    lights = data["lights"]
    if sum(1 for l in lights if l["shadow"] != "None") > 3:
        issues.append("more than 3 shadowed lights")
    for l in lights:
        if l["type"] not in ("Point", "Spot") or l["shadow"] not in ("None", "Hard", "Soft"):
            issues.append(f"{l['id']} bad type/shadow")
        if (l["spot_angle"] > 0) != (l["type"] == "Spot"):
            issues.append(f"{l['id']} spot_angle mismatch")
    # 6. ads
    for a in data["ads"]:
        mat = a["material"]
        if mat not in MATERIALS or not mat.startswith("holo_"):
            issues.append(f"{a['id']} material {mat} not holo")
        if a["anim"] == "scroll" and not mat.endswith("_scroll"):
            issues.append(f"{a['id']} scroll without *_scroll material")
        if a["anim"] == "spin" and a["kind"] != "float":
            issues.append(f"{a['id']} spin on non-float")
        if a["anim"] not in ("none", "scroll", "spin"):
            issues.append(f"{a['id']} bad anim")
    # 7. cables
    by = {x["id"]: x for x in [*towers, *stalls, *clubs, *shacks]}
    for c in data["cables"]:
        att = c.get("attach", [])
        if len(att) != 2 or any(i not in by for i in att):
            issues.append(f"{c['id']} bad attach {att}")
            continue
        for p, i in zip((c["a"], c["b"]), att):
            if not _on_surface(by[i], p):
                issues.append(f"{c['id']} endpoint {p} not on {i}")
    # occluder ids
    sources = {x["id"] for x in [*towers, *data["bridges"], *data["ads"]]}
    for o in data["occluders"]:
        if o["source"] not in sources or o["id"] != f"occ-{o['source']}":
            issues.append(f"bad occluder {o['id']}")
    return issues


# --------------------------------------------------------------------------- sightlines


def ray_hit_distance(origin, direction, box_min, box_max) -> float | None:
    t0, t1 = -math.inf, math.inf
    for i in range(3):
        if abs(direction[i]) < 1e-12:
            if not box_min[i] <= origin[i] <= box_max[i]:
                return None
            continue
        a = (box_min[i] - origin[i]) / direction[i]
        b = (box_max[i] - origin[i]) / direction[i]
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    if t1 < max(t0, 0.0):
        return None
    return max(t0, 0.0)


def sightline_failures(data, *, step_deg=5, max_elev=25, elev_step=5) -> list[dict]:
    boxes = [(o["min"], o["max"], o["id"]) for o in data["occluders"]]
    wall = data["east_wall"]
    c, s = wall["center"], wall["size"]
    boxes.append(([c[0] - s[0] / 2, 0.0, c[2] - s[2] / 2], [c[0] + s[0] / 2, s[1], c[2] + s[2] / 2], "east-wall"))
    failures = []
    grid = [-9.0, -4.5, 0.0, 4.5, 9.0]
    for vx in grid:
        for vz in grid:
            origin = (vx, EYE, vz)
            for az in range(0, 360, step_deg):
                for el in range(0, max_elev + 1, elev_step):
                    a, e = math.radians(az), math.radians(el)
                    d = (math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a))
                    hits = [t for lo, hi, _ in boxes if (t := ray_hit_distance(origin, d, lo, hi)) is not None]
                    if not hits:
                        failures.append({"view": [vx, vz], "az": az, "el": el, "reason": "no hit"})
                        continue
                    t = min(hits)
                    p = [origin[i] + d[i] * t for i in range(3)]
                    if abs(p[0]) > HALF + 1e-6 or abs(p[2]) > HALF + 1e-6:
                        failures.append({"view": [vx, vz], "az": az, "el": el, "reason": "hit outside"})
    return failures


def write_layout(path: Path) -> dict[str, Any]:
    data = build_layout()
    issues = validate_layout(data)
    if issues:
        raise ValueError(f"layout invalid: {issues[:5]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    write_layout(PROJECT_ROOT / "content" / "slum02" / "layout.json")
