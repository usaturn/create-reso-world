"""Patchwork shacks in the west block and the south-west pocket (sector ``shacks``).

Each layout shack becomes one object: 4-6 ``pallet_wood`` posts carrying two plates and
2-3 rafters, four walls of 2-4 scavenged panels (one material per wall out of corrugated /
rusty corrugated / plywood / tarp, walls of 3+ panels carry one lapping patch of another sheet;
every panel leans +-3 deg and laps its neighbour by 2-5 cm; tarps are held by battens),
a mono-pitch ``corrugated_rust`` roof (6-12 deg, 0.3 m eaves) weighed down by 2-4 tyres and
a few bricks, a door (plywood board or a tarp curtain on a rod), a window hole closed with
green vinyl, a leaning stove chimney with soot, an AC unit on blocks for about half of them,
a rain drum under the low eave and a laundry line with 3-6 cloths.

Pure Python and deterministic (``random.Random(spec["seed"])`` per shack).
Door frame: the shack is authored with the door wall at local +Z and the roof rising towards
it, then turned by a quarter turn ``k`` (the door faces the plaza) plus the layout rotation;
parts are baked into that yaw, so the assembly origin is ``(cx, 0, cz)`` and every meta point
is origin-relative and yaw-baked (like the stalls). ``meta["frame"]["yaw"]`` undoes it.
R11: every part is a closed outward shell - panels, vinyl, curtain and cloths are thin shells
(``geometry.thick_sheet``) so they read from inside and outside.
Contact: layer-0 panels hang on the post plane, lapping panels rest on the panel under them,
roof sheets rest on the rafters, tyres and bricks sit on the ridge envelope (``geometry.seat``),
the drum and the AC blocks stand on the ground, the laundry line ends inside arms nailed to
a wall and the cloths hang from the line.
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from modeling.slum02 import geometry as g
from modeling.slum02.layout import _aabb, _gap, _street_rect, build_layout
from modeling.slum02.sectors import register
from modeling.slum02.vcolor import Spray

Vec = tuple[float, float, float]

EAVE = 0.3              # roof overhang past the front / back walls, along the pitch
SIDE_EAVE = 0.15        # overhang past the side walls (before snapping to whole corrugations)
POST = 0.09
PLATE_H = 0.1
RAFTER_D, RAFTER_W = 0.08, 0.07
PITCH, CORR_AMP, CORR_THK = 0.19, 0.028, 0.006
MIN_LOW_WALL = 2.0      # roof underside at the low (back) wall
VMID = 1.2              # panel tilt pivot height
WALL_POOL = ("corrugated", "corrugated_rust", "plywood", "tarp_blue", "tarp_orange", "tarp_green")
TARP_BULGE = 0.025
TARP_STEP = 0.14
FOOT = 0.35            # height of the splash-grime row on panels standing on the ground
BATTEN_W, BATTEN_T = 0.05, 0.022
CORR_WALL_BUDGET = 6.5   # metres of corrugated wall per shack (triangle budget)
DOOR_W, DOOR_H, JAMB = 0.8, 1.85, 0.06
WINDOW_W, WINDOW_SILL, WINDOW_TOP = 0.6, 1.15, 1.6
ARM = 0.45
CLOTHS = ("cloth_red", "tarp_blue", "tarp_orange", "tarp_green")
SOOT = ((0.2, 0.2, 0.2), 0.6, 0.8)          # colour, strength, radius (brief)
GRIME = (0.5, 0.47, 0.42)
RUST = (1.05, 0.6, 0.38)
SIDES = ("front", "back", "left", "right")
_OPPOSITE = {"left": "right", "right": "left"}
NORMALS: dict[str, Vec] = {"front": (0.0, 0.0, 1.0), "back": (0.0, 0.0, -1.0),
                           "right": (1.0, 0.0, 0.0), "left": (-1.0, 0.0, 0.0)}


# --------------------------------------------------------------------------- wall frame


def _pt(side: str, hx: float, hz: float, u: float, v: float, dep: float) -> Vec:
    """Wall coordinates (u along the wall, v up, dep outward from the post plane) -> local."""
    if side == "front":
        return (u, v, hz + dep)
    if side == "back":
        return (-u, v, -hz - dep)
    if side == "right":
        return (hx + dep, v, -u)
    return (-hx - dep, v, u)


def _thk(material: str) -> float:
    return {"corrugated": CORR_THK, "corrugated_rust": CORR_THK, "plywood": 0.018}.get(material, 0.008)


@dataclass
class Panel:
    """One scavenged sheet: a quadrilateral between two leaning edge lines, profiled across its width.

    Corrugation / folds run parallel to the panel's own edges (the sheet leans with them), so
    ``x`` is the across-sheet coordinate: 0 on the left edge, ``width`` on the right edge.
    """
    name: str
    material: str
    layer: int
    left: tuple[float, float]       # (u at VMID, tan of the lean)
    right: tuple[float, float]
    vb: float                        # bottom edge height
    gap: float                       # gap under the roof / wall top
    base: float = 0.0                # inner face offset from the post plane
    phase: float = 0.0               # corrugation phase at the left edge (m)

    def edge(self, e: tuple[float, float], v: float) -> float:
        return e[0] + e[1] * (v - VMID)

    def span(self) -> tuple[float, float]:
        us = [self.edge(e, v) for e in (self.left, self.right) for v in (0.0, 4.0)]
        return min(us), max(us)

    @property
    def width(self) -> float:
        return self.right[0] - self.left[0]

    def x_of(self, u: float, v: float) -> float:
        lo, hi = self.edge(self.left, v), self.edge(self.right, v)
        return (u - lo) / (hi - lo) * self.width

    def u_of(self, x: float, v: float) -> float:
        lo, hi = self.edge(self.left, v), self.edge(self.right, v)
        return lo + x / self.width * (hi - lo)

    def inside(self, u: float, v: float) -> bool:
        return self.edge(self.left, v) - 1e-9 <= u <= self.edge(self.right, v) + 1e-9

    def profile_x(self, x: float) -> float:
        if self.material.startswith("corrugated"):
            # wall sheets: three corners per pitch (rise, flat ridge, fall to a sharp valley)
            t = ((x + self.phase) / PITCH) % 1.0
            if t < 1 / 3:
                return CORR_AMP * t * 3
            if t < 2 / 3:
                return CORR_AMP
            return CORR_AMP * (1 - t) * 3
        if self.material.startswith("tarp"):
            # piecewise linear between the tarp columns, so the mesh is exactly this profile
            k = math.floor(x / TARP_STEP)
            x0 = k * TARP_STEP
            t = (x - x0) / TARP_STEP
            return self._belly(x0) * (1 - t) + self._belly(x0 + TARP_STEP) * t
        return 0.0

    def _belly(self, x: float) -> float:
        """A loose tarp: one belly between the edges plus two shallow vertical folds."""
        s = min(1.0, max(0.0, x / self.width))
        return TARP_BULGE * math.sin(math.pi * s) * (1.0 + 0.4 * math.sin(math.tau * 2.0 * s))

    def profile(self, u: float, v: float) -> float:
        return self.profile_x(self.x_of(u, v))

    def outer(self, u: float, v: float) -> float:
        return self.base + _thk(self.material) + self.profile(u, v)

    def breaks(self) -> list[float]:
        """Across-sheet positions of the interior columns (corrugation corners, tarp folds)."""
        w = self.width
        if self.material.startswith("corrugated"):
            step = PITCH / 3
            k0 = math.ceil(self.phase / step)
            return [k * step - self.phase for k in range(k0, math.ceil((w + self.phase) / step) + 1)
                    if 0.0 < k * step - self.phase < w]
        step = TARP_STEP if self.material.startswith("tarp") else 0.5
        n = max(1, math.ceil(w / step - 1e-9))
        return [w * k / n for k in range(1, n)] if not self.material.startswith("tarp") else \
            [k * step for k in range(1, math.ceil(w / step)) if k * step < w]


@dataclass
class Wall:
    side: str
    lo: float
    hi: float
    top: Callable[[float], float]    # roof underside above the wall at u
    panels: list[Panel]
    battens: list[tuple[float, float, float, float, float]] = field(default_factory=list)   # u0 u1 v0 v1 outer

    def outer(self, u0: float, u1: float, v0: float = 0.0, v1: float = 2.4) -> float:
        """Outermost panel face over [u0, u1] x [v0, v1] (what a board, arm or frame nailed there rests on)."""
        best = 0.0
        n = max(2, math.ceil((u1 - u0) / 0.004))
        m = max(1, math.ceil((v1 - v0) / 0.1))
        for p in self.panels:
            for j in range(m + 1):
                v = v0 + (v1 - v0) * j / m
                if v < p.vb or v > self.top(p.edge(p.left, v)) - p.gap:
                    continue
                for k in range(n + 1):
                    u = u0 + (u1 - u0) * k / n
                    if p.inside(u, v):
                        best = max(best, p.outer(u, v))
        for b0, b1, c0, c1, d in self.battens:
            if b0 < u1 and b1 > u0 and c0 < v1 and c1 > v0:
                best = max(best, d)
        return best


def _sheet_piece(name: str, p: Panel, wall: Wall, hx: float, hz: float,
                 lfn: Callable[[float], float], rfn: Callable[[float], float],
                 vlo: float, vhi: Callable[[float], float]) -> g.MeshData | None:
    """Thin shell of panel ``p`` between two edge lines u = f(v), from ``vlo`` up to ``vhi(u)``.

    The edges are the panel's own leaning edges or the vertical sides of a door / window hole;
    interior columns follow the panel's lean (``Panel.u_of``) so no corrugation corner is skipped.
    """
    def solve(line: Callable[[float], float], row: Callable[[float], float]) -> tuple[float, float]:
        u = line(vlo)
        v = vlo
        for _ in range(6):
            v = row(u)
            u = line(v)
        return u, v

    top_est = max(vhi(lfn(vlo)), vhi(rfn(vlo))) + 0.1
    a = max(lfn(vlo), lfn(top_est))
    b = min(rfn(vlo), rfn(top_est))
    height = vhi((a + b) / 2) - vlo
    if b - a < 0.03 or height < 0.03:
        return None
    # corrugated / tarp strips are already fine across u; they only need rows on tall pieces.
    # Pieces standing on the ground get a row at FOOT so the splash grime stays a band.
    row_edge = 1.3 if p.material == "plywood" else 2.8
    foot = FOOT if vlo < 0.3 and height > 2 * FOOT else 0.0
    n = max(1, math.ceil((height - foot) / row_edge))
    rows: list[Callable[[float], float]] = [lambda u: vlo]
    if foot:
        rows.append(lambda u: vlo + foot)
    rows += [lambda u, f=r / n: vlo + foot + f * (vhi(u) - vlo - foot) for r in range(1, n + 1)]
    thk = _thk(p.material)
    cols: list[list[tuple[float, float]]] = [[solve(lfn, row) for row in rows]]
    for x in p.breaks():
        def line(v: float, x: float = x) -> float:
            return p.u_of(x, v)
        if all(lfn(v) + 0.008 < line(v) < rfn(v) - 0.008 for v in (vlo, top_est)):
            cols.append([solve(line, row) for row in rows])
    cols.append([solve(rfn, row) for row in rows])
    grid = [[_pt(wall.side, hx, hz, u, v, p.base + thk + p.profile(u, v)) for u, v in col] for col in cols]
    return g.thick_sheet(name, grid, g.mul(NORMALS[wall.side], -thk), p.material)


def _panel_mesh(p: Panel, wall: Wall, hx: float, hz: float,
                hole: tuple[float, float, float, float] | None) -> g.MeshData:
    def lfn(v: float) -> float:
        return p.edge(p.left, v)

    def rfn(v: float) -> float:
        return p.edge(p.right, v)

    def top(u: float) -> float:
        return wall.top(u) - p.gap

    a, b = p.span()
    pieces: list[g.MeshData | None] = []
    if hole is None or hole[1] <= a or hole[0] >= b:
        pieces.append(_sheet_piece(p.name, p, wall, hx, hz, lfn, rfn, p.vb, top))
    else:
        h0, h1, hv0, hv1 = hole
        if hv0 - p.vb > 0.03:
            pieces.append(_sheet_piece("below", p, wall, hx, hz, lfn, rfn, p.vb, lambda u: hv0))
        pieces.append(_sheet_piece("above", p, wall, hx, hz, lfn, rfn, hv1, top))
        lo_v = max(hv0, p.vb)
        if h0 - max(lfn(lo_v), lfn(hv1)) > 0.03:
            pieces.append(_sheet_piece("left", p, wall, hx, hz, lfn, lambda v: h0, lo_v, lambda u: hv1))
        if min(rfn(lo_v), rfn(hv1)) - h1 > 0.03:
            pieces.append(_sheet_piece("right", p, wall, hx, hz, lambda v: h1, rfn, lo_v, lambda u: hv1))
    kept = [m for m in pieces if m is not None]
    return g.combine(p.name, kept, p.material)


def _seams(rng: random.Random, lo: float, hi: float, n: int, hole: tuple[float, float, float, float] | None) -> list[float]:
    """Interior seam positions: evenly spread with jitter, clear of the hole edges."""
    length = hi - lo
    edges = (hole[0], hole[1]) if hole else ()
    for _ in range(40):
        seams = [lo + length * k / n + rng.uniform(-0.12, 0.12) * length / n for k in range(1, n)]
        pts = [lo, *seams, hi]
        if min(b - a for a, b in zip(pts, pts[1:])) < 0.45:
            continue
        if any(abs(s - e) < 0.17 for s in seams for e in edges):
            continue
        return seams
    if n > 2:
        return _seams(rng, lo, hi, n - 1, hole)
    # two panels always fit: put the seam in the middle of the widest hole-free stretch
    if hole is None:
        return [(lo + hi) / 2]
    left, right = hole[0] - lo, hi - hole[1]
    return [(lo + hole[0]) / 2] if left > right else [(hole[1] + hi) / 2]


def _build_wall(side: str, lo: float, hi: float, top: Callable[[float], float], material: str,
                rng: random.Random, hole: tuple[float, float, float, float] | None,
                patch: str | None = None) -> tuple[Wall, dict[str, Any]]:
    """2-4 panels of ``material``; on walls of 3+ panels one lapping panel is a ``patch`` of another sheet."""
    n = rng.randint(2, 4)
    n = max(2, min(n, int((hi - lo) / 0.55)))
    seams = _seams(rng, lo, hi, n, hole)
    n = len(seams) + 1
    tilts = [rng.choice((-1, 1)) * rng.uniform(0.8, 3.0) for _ in seams]
    laps = [rng.uniform(0.02, 0.05) for _ in seams]
    start = rng.randrange(2)
    panels: list[Panel] = []
    for k in range(n):
        layer = (k + start) % 2
        grow = 1.0 if layer == 1 else 0.0
        left = (lo, 0.0) if k == 0 else (seams[k - 1] - grow * laps[k - 1], math.tan(math.radians(tilts[k - 1])))
        right = (hi, 0.0) if k == n - 1 else (seams[k] + grow * laps[k], math.tan(math.radians(tilts[k])))
        panels.append(Panel(f"panel-{side}-{k}", material, layer, left, right,
                            vb=rng.uniform(0.0, 0.03), gap=rng.uniform(0.02, 0.05), phase=rng.uniform(0.0, PITCH)))
    patched = None
    if patch is not None and n >= 3:
        patched = rng.choice([p for p in panels if p.layer == 1])
        patched.material = patch
    # lapping panels rest on the panel under them: lowest base that clears it everywhere
    for k, p in enumerate(panels):
        if p.layer == 0:
            continue
        best = 0.0
        for j in (k - 1, k + 1):
            if not 0 <= j < n or panels[j].layer != 0:
                continue
            q = panels[j]
            # overlap strip, row by row over the height both panels share; inside the door /
            # window band the hole is cut out of both sheets, so they only meet beside it
            v0 = max(p.vb, q.vb)
            v1 = min(min(top(x.edge(x.left, 2.0)), top(x.edge(x.right, 2.0))) - x.gap for x in (p, q))
            rows = max(2, math.ceil((v1 - v0) / 0.05))
            for r in range(rows + 1):
                v = v0 + (v1 - v0) * r / rows
                a = max(p.edge(p.left, v), q.edge(q.left, v))
                b = min(p.edge(p.right, v), q.edge(q.right, v))
                segs = [(a, b)]
                if hole is not None and hole[2] < v < hole[3]:
                    segs = [(a, min(b, hole[0])), (max(a, hole[1]), b)]
                for sa, sb in segs:
                    if sb <= sa:
                        continue
                    steps = max(2, math.ceil((sb - sa) / 0.003))
                    for s in range(steps + 1):
                        u = sa + (sb - sa) * s / steps
                        best = max(best, q.outer(u, v) - p.profile(u, v))
        # + 2 mm: the triangulated strips between leaning columns deviate from the exact profile
        # by a fraction of a millimetre; keep the lap from grazing the sheet under it
        p.base = best + 0.002
    wall = Wall(side, lo, hi, top, panels)
    meta = {"material": material, "panels": n, "tilts": [round(t, 3) for t in tilts],
            "overlaps": [round(o, 4) for o in laps], "patch": patched.name if patched else None,
            "patch_material": patched.material if patched else None}
    return wall, meta


def _battens(wall: Wall, hx: float, hz: float, hole: tuple[float, float, float, float] | None) -> list[g.MeshData]:
    """Battens nailed across tarp panels near their bottom and top edges (what holds a tarp on).

    On a layer-0 tarp they stop short of the lapping neighbours; around a door or window they
    leave 14 cm so the board, curtain or frame keeps clear.
    """
    out: list[g.MeshData] = []
    for p in wall.panels:
        if not p.material.startswith("tarp"):
            continue
        top = min(wall.top(p.edge(p.left, 2.0)), wall.top(p.edge(p.right, 2.0))) - p.gap
        margin = 0.03 if p.layer == 1 else 0.07
        for i, v in enumerate((p.vb + 0.12, top - 0.08)):
            v0, v1 = v - BATTEN_W / 2, v + BATTEN_W / 2
            a = max(p.edge(p.left, v0), p.edge(p.left, v1)) + margin
            b = min(p.edge(p.right, v0), p.edge(p.right, v1)) - margin
            segs = [(a, b)]
            if hole is not None and hole[2] - 0.03 < v < hole[3] + 0.03:
                segs = [(a, min(b, hole[0] - 0.14)), (max(a, hole[1] + 0.14), b)]
            for j, (u0, u1) in enumerate(segs):
                if u1 - u0 < 0.15:
                    continue
                d0 = max(p.outer(u0 + (u1 - u0) * t / 60, vv) for t in range(61) for vv in (v0, v, v1))
                out.append(_wbox(f"batten-{p.name[6:]}-{i}{j}", wall.side, hx, hz, u0, u1, v0, v1, d0, d0 + BATTEN_T,
                                 "pallet_wood"))
                wall.battens.append((u0, u1, v0, v1, d0 + BATTEN_T))
    return out


def _wbox(name: str, side: str, hx: float, hz: float, u0: float, u1: float, v0: float, v1: float,
          d0: float, d1: float, material: str, max_edge: float | None = None) -> g.MeshData:
    """Axis-aligned box given in wall coordinates."""
    a, b = _pt(side, hx, hz, u0, v0, d0), _pt(side, hx, hz, u1, v1, d1)
    lo = tuple(min(a[k], b[k]) for k in range(3))
    hi = tuple(max(a[k], b[k]) for k in range(3))
    center = tuple((lo[k] + hi[k]) / 2 for k in range(3))
    size = tuple(hi[k] - lo[k] for k in range(3))
    if max_edge:
        return g.subdivided_box(name, center, size, max_edge, material)
    return g.box(name, center, size, material)


# --------------------------------------------------------------------------- placement


def _door_quarter(spec: dict) -> int:
    """Quarter turn that points the door wall (local +Z) at the plaza."""
    cx, cz = spec["center"]
    length = math.hypot(cx, cz) or 1.0
    target = (-cx / length, -cz / length)
    best, best_k = -2.0, 0
    for k in range(4):
        n = g.rotate_y((0.0, 0.0, 1.0), math.radians(spec["rotation"]) + k * math.pi / 2)
        score = n[0] * target[0] + n[2] * target[1]
        if score > best + 1e-9:
            best, best_k = score, k
    return best_k


class _Site:
    """World-space clearance check for things that stick out past the walls (drum, AC, laundry).

    Streets, towers, stalls, clubs and the plaza must stay 5 cm clear; towards another shack an
    item may use at most half of the gap between the two plots, so neighbours never collide.
    """

    def __init__(self, spec: dict, data: dict[str, Any], yaw: float) -> None:
        self.cx, self.cz = spec["center"]
        self.yaw = yaw
        self.own = _aabb(spec)
        self.hard = [_street_rect(s) for s in data["streets"]] + [_aabb(x) for x in [*data["towers"], *data["stalls"], *data["clubs"]]]
        plaza = data["plaza"]
        self.hard.append((plaza["min"][0], plaza["min"][1], plaza["max"][0], plaza["max"][1]))
        self.soft = [_aabb(x) for x in data["shacks"] if x["id"] != spec["id"]]

    def world_rect(self, lo: Vec, hi: Vec) -> tuple[float, float, float, float]:
        pts = [g.rotate_y((x, 0.0, z), self.yaw) for x in (lo[0], hi[0]) for z in (lo[2], hi[2])]
        return (min(p[0] for p in pts) + self.cx, min(p[2] for p in pts) + self.cz,
                max(p[0] for p in pts) + self.cx, max(p[2] for p in pts) + self.cz)

    def fits(self, meshes: list[g.MeshData]) -> bool:
        lo, hi = g.bounds(meshes)
        r = self.world_rect(lo, hi)
        if any(_gap(r, h) < 0.05 for h in self.hard):
            return False
        return all(_gap(r, s) >= _gap(self.own, s) / 2 - 1e-9 for s in self.soft)


# --------------------------------------------------------------------------- shack


def build_shack(spec: dict, data: dict[str, Any] | None = None) -> g.Assembly:
    """One shack from a layout spec. Origin = (cx, 0, cz); parts carry the yaw."""
    data = data if data is not None else build_layout()
    rng = random.Random(spec["seed"])
    w, d = (float(x) for x in spec["size"])
    H = float(spec["height"])
    k = _door_quarter(spec)
    W, D = (w, d) if k % 2 == 0 else (d, w)
    hx, hz = W / 2, D / 2
    yaw = math.radians(spec["rotation"]) + k * math.pi / 2
    site = _Site(spec, data, yaw)

    slope = min(rng.uniform(6.0, 12.0), math.degrees(math.atan((H - MIN_LOW_WALL) / hz)))
    tan = math.tan(math.radians(slope))
    cos = math.cos(math.radians(slope))

    def roof_under(z: float) -> float:
        """Rafter top / underside of the lowest roof sheet (rises towards the door, +Z)."""
        return H + tan * z

    parts: list[g.MeshData] = []
    sprays: list[tuple[Vec, float, tuple[float, float, float], float, tuple[str, ...]]] = []

    # ---- roof sheets: whole corrugations from a common phase so the laps nest
    zr0, zr1 = -hz - EAVE, hz + EAVE
    xr0 = -hx - SIDE_EAVE
    total = math.ceil((2 * hx + 2 * SIDE_EAVE) / PITCH)
    xr1 = xr0 + total * PITCH
    n_sheets = 3 if total * PITCH > 3.4 else 2
    cuts = [round(total * s / n_sheets + rng.uniform(-1.0, 1.0)) for s in range(1, n_sheets)]
    bounds_ = [0, *cuts, total]
    lifts = [0.0, CORR_THK, 0.0][:n_sheets]
    spans: list[tuple[float, float, float]] = []
    zs = [zr0 + (zr1 - zr0) * r / 2 for r in range(3)]
    for s in range(n_sheets):
        a = xr0 + max(0, bounds_[s] - (1 if s > 0 else 0)) * PITCH      # one corrugation lap
        b = xr0 + bounds_[s + 1] * PITCH
        lift = lifts[s]
        spans.append((a, b, lift))
        grid = [[(x, roof_under(z) + CORR_THK + dy + lift, z) for z in zs] for x, dy in g.corrugation(a, b, PITCH, CORR_AMP)]
        parts.append(g.thick_sheet(f"roof-sheet-{s}", grid, (0.0, -CORR_THK, 0.0), "corrugated_rust"))

    def lift_at(x: float) -> float:
        return max((lf for a, b, lf in spans if a - 1e-9 <= x <= b + 1e-9), default=0.0)

    def ridge_top(x: float, z: float) -> float:
        return roof_under(z) + CORR_THK + CORR_AMP + lift_at(x)

    # ---- frame: rafters on valley centres, plates under them, posts under the plates
    def valley(x: float, towards: int) -> float:
        m = (x - xr0) / PITCH - 0.875
        m = math.floor(m) if towards < 0 else (math.ceil(m) if towards > 0 else round(m))
        return xr0 + (m + 0.875) * PITCH

    rafter_xs = [valley(-hx + 0.045, 1), valley(hx - 0.045, -1)]
    if W > 3.0:
        rafter_xs.insert(1, valley(0.0, 0))
    drop = RAFTER_D / (2 * cos)
    for i, x in enumerate(rafter_xs):
        z0, z1 = -hz + 0.02, hz - 0.02
        parts.append(g.beam(f"rafter-{i}", (x, roof_under(z0) - drop, z0), (x, roof_under(z1) - drop, z1),
                            RAFTER_D, RAFTER_W, "pallet_wood"))
    plate_z = (hz - POST / 2, -hz + POST / 2)
    plate_bottom: dict[float, float] = {}
    for i, zc in enumerate(plate_z):
        top = roof_under(zc - POST / 2) - RAFTER_D / cos
        plate_bottom[zc] = top - PLATE_H
        parts.append(g.box(f"plate-{i}", (0.0, top - PLATE_H / 2, zc), (2 * hx, PLATE_H, POST), "pallet_wood"))
    post_xs = [-hx + POST / 2, hx - POST / 2] + ([0.0] if W > 3.2 else [])
    n = 0
    for zc in plate_z:
        for x in post_xs:
            h = plate_bottom[zc]
            parts.append(g.box(f"post-{n:02d}", (x, h / 2, zc), (POST, h, POST), "pallet_wood"))
            sprays.append(((x, 0.05, zc), 0.4, GRIME, 0.6, ("pallet_wood",)))
            n += 1

    # ---- openings: door in the front wall between posts, window in a side wall
    post_us = sorted(post_xs)
    free = [(a + POST / 2 + JAMB + 0.05, b - POST / 2 - JAMB - 0.05) for a, b in zip(post_us, post_us[1:])]
    free = [f for f in free if f[1] - f[0] >= DOOR_W]
    fa, fb = free[rng.randrange(len(free))]
    du0 = rng.uniform(fa, fb - DOOR_W)
    du1 = du0 + DOOR_W
    door_hole = (du0, du1, 0.0, DOOR_H)

    # ---- walls: one scavenged material per wall, at least three different on the shack
    mats = rng.sample(WALL_POOL, 3)
    # corrugated sheet costs ~250 triangles per metre of wall: at most two corrugated walls and
    # at most CORR_WALL_BUDGET metres of them, so every shack stays inside the 5000-triangle budget
    corr = sum(m.startswith("corrugated") for m in mats)
    mats.append(rng.choice([m for m in WALL_POOL if corr < 2 or not m.startswith("corrugated")]))
    lengths = {"front": W, "back": W, "left": D, "right": D}
    for _ in range(24):
        rng.shuffle(mats)
        if sum(lengths[sd] for sd, m in zip(SIDES, mats) if m.startswith("corrugated")) <= CORR_WALL_BUDGET:
            break
    wall_mat = dict(zip(SIDES, mats))
    # the window goes into a side wall; cutting corrugated sheet around it is the costlier option
    win_side = rng.choice(("left", "right"))
    if wall_mat[win_side].startswith("corrugated") and not wall_mat[_OPPOSITE[win_side]].startswith("corrugated"):
        win_side = _OPPOSITE[win_side]
    other_side = _OPPOSITE[win_side]
    lim = hz - POST - 0.05 - WINDOW_W / 2 - 0.05
    wc = rng.uniform(-lim, lim)
    win_hole = (wc - WINDOW_W / 2, wc + WINDOW_W / 2, WINDOW_SILL, WINDOW_TOP)
    tops: dict[str, Callable[[float], float]] = {
        "front": lambda u: roof_under(hz),
        "back": lambda u: roof_under(-hz - 0.08),
        "right": lambda u: roof_under(-u),
        "left": lambda u: roof_under(u),
    }
    holes = {"front": door_hole, win_side: win_hole}
    walls: dict[str, Wall] = {}
    walls_meta: dict[str, Any] = {}
    corr_len = sum(lengths[sd] for sd in SIDES if wall_mat[sd].startswith("corrugated"))

    def patch_for(side: str) -> str:
        pool = [m for m in ("plywood", "tarp_blue", "tarp_orange", "tarp_green", "corrugated", "corrugated_rust")
                if m != wall_mat[side] and (corr_len <= 4.5 or not m.startswith("corrugated"))]
        return rng.choice(pool)

    for side in ("left", "right"):
        walls[side], walls_meta[side] = _build_wall(side, -hz, hz, tops[side], wall_mat[side], rng, holes.get(side),
                                                    patch_for(side))
    ext = max(walls[side].outer(-hz, hz, 0.0, 4.0) for side in ("left", "right"))
    for side in ("front", "back"):
        walls[side], walls_meta[side] = _build_wall(side, -hx - ext, hx + ext, tops[side], wall_mat[side], rng,
                                                    holes.get(side), patch_for(side))
    for side in SIDES:
        wall = walls[side]
        for p in wall.panels:
            parts.append(_panel_mesh(p, wall, hx, hz, holes.get(side)))
        parts.extend(_battens(wall, hx, hz, holes.get(side)))
        span = wall.hi - wall.lo
        for f in (0.25, 0.75):
            sprays.append((_pt(side, hx, hz, wall.lo + span * f, 0.05, 0.1), 0.8, GRIME, 0.6, (wall_mat[side], "pallet_wood")))

    # ---- door: jambs + header inside the opening, then a plywood board or a tarp curtain
    jambs = [_wbox("jl", "front", hx, hz, du0 - JAMB, du0, 0.0, DOOR_H, -JAMB, 0.0, "pallet_wood"),
             _wbox("jr", "front", hx, hz, du1, du1 + JAMB, 0.0, DOOR_H, -JAMB, 0.0, "pallet_wood"),
             _wbox("hd", "front", hx, hz, du0 - JAMB, du1 + JAMB, DOOR_H, DOOR_H + JAMB, -JAMB, 0.0, "pallet_wood")]
    parts.append(g.combine("door-jamb", jambs, "pallet_wood"))
    front = walls["front"]
    door: dict[str, Any] = {"u0": round(du0, 4), "u1": round(du1, 4), "height": DOOR_H}
    if rng.random() < 0.5:
        door["kind"] = "board"
        ob = front.outer(du0 - 0.05, du1 + 0.05, 0.0, DOOR_H + 0.05)
        parts.append(_wbox("door-board", "front", hx, hz, du0 - 0.05, du1 + 0.05, 0.02, DOOR_H + 0.04,
                           ob, ob + 0.022, "plywood", 0.5))
        battens = [_wbox(f"b{i}", "front", hx, hz, du0 - 0.01, du1 + 0.01, y - 0.045, y + 0.045, ob + 0.022, ob + 0.042,
                         "pallet_wood") for i, y in enumerate((0.35, 1.55))]
        parts.append(g.combine("door-batten", battens, "pallet_wood"))
        hinge_u = (du0 + 0.02, du0 + 0.2) if rng.random() < 0.5 else (du1 - 0.2, du1 - 0.02)
        latch_u = du1 - 0.08 if hinge_u[0] < (du0 + du1) / 2 else du0 + 0.05
        hardware = [_wbox(f"h{i}", "front", hx, hz, hinge_u[0], hinge_u[1], y - 0.02, y + 0.02, ob + 0.042, ob + 0.047,
                          "steel_dark") for i, y in enumerate((0.35, 1.55))]
        hardware.append(_wbox("latch", "front", hx, hz, latch_u, latch_u + 0.03, 0.98, 1.06, ob + 0.022, ob + 0.05, "steel_dark"))
        parts.append(g.combine("door-hardware", hardware, "steel_dark"))
    else:
        door["kind"] = "curtain"
        ob = front.outer(du0 - 0.16, du1 + 0.16, 0.0, DOOR_H + 0.12)
        rod_v, rod_d = DOOR_H + 0.08, ob + 0.05
        parts.append(g.pipe("door-rod", _pt("front", hx, hz, du0 - 0.14, rod_v, rod_d),
                            _pt("front", hx, hz, du1 + 0.14, rod_v, rod_d), 0.012, "steel_bare", 8))
        brackets = [_wbox(f"k{i}", "front", hx, hz, u - 0.015, u + 0.015, rod_v - 0.025, rod_v + 0.025, ob, ob + 0.065,
                          "steel_dark") for i, u in enumerate((du0 - 0.1, du1 + 0.1))]
        parts.append(g.combine("door-rod-bracket", brackets, "steel_dark"))
        drawn = rng.uniform(0.6, 0.85)
        u_end = du0 + DOOR_W * drawn
        ncol = max(3, math.ceil((u_end - du0 + 0.1) / 0.08))
        grid = []
        for c in range(ncol + 1):
            u = du0 - 0.1 + (u_end - du0 + 0.1) * c / ncol
            fold = 0.02 * (1 if c % 2 else -1)
            grid.append([_pt("front", hx, hz, u + (0.03 * (c / ncol) if v < 1.0 else 0.0), v, rod_d + fold)
                         for v in (0.03 + 0.02 * rng.random(), 1.0, rod_v - 0.01)])
        # a tarp colour the front wall does not use, so the doorway reads against the wall
        used = {q.material for q in front.panels}
        curtain_mats = [m for m in ("tarp_blue", "tarp_orange", "tarp_green") if m not in used] or ["tarp_blue"]
        parts.append(g.thick_sheet("door-curtain", grid, (0.0, 0.0, -0.006), rng.choice(curtain_mats)))
    door["wall_outer"] = round(ob, 4)

    # ---- window: vinyl behind the hole, battens around it
    wu0, wu1, wv0, wv1 = win_hole
    vgrid = [[_pt(win_side, hx, hz, u, v, 0.0) for v in (wv0 - 0.05, (wv0 + wv1) / 2, wv1 + 0.05)]
             for u in (wu0 - 0.05, wc, wu1 + 0.05)]
    parts.append(g.thick_sheet("window-vinyl", vgrid, g.mul(NORMALS[win_side], -0.005), "tarp_green"))
    wall = walls[win_side]
    ow = wall.outer(wu0 - 0.06, wu1 + 0.06, wv0 - 0.06, wv1 + 0.06)
    frame = [_wbox("t", win_side, hx, hz, wu0 - 0.06, wu1 + 0.06, wv1, wv1 + 0.05, ow, ow + 0.025, "pallet_wood"),
             _wbox("b", win_side, hx, hz, wu0 - 0.06, wu1 + 0.06, wv0 - 0.05, wv0, ow, ow + 0.025, "pallet_wood"),
             _wbox("l", win_side, hx, hz, wu0 - 0.05, wu0, wv0, wv1, ow, ow + 0.025, "pallet_wood"),
             _wbox("r", win_side, hx, hz, wu1, wu1 + 0.05, wv0, wv1, ow, ow + 0.025, "pallet_wood")]
    parts.append(g.combine("window-frame", frame, "pallet_wood"))
    sprays.append((_pt(win_side, hx, hz, wc, wv0 - 0.3, 0.05), 0.45, GRIME, 0.5, (wall_mat[win_side],)))

    # ---- chimney: a leaning stove pipe through the back half of the roof, soot on top
    xs_sorted = sorted(rafter_xs)
    cs = rng.choice((-1, 1))
    side_r = xs_sorted[-1] if cs > 0 else xs_sorted[0]
    mid_r = xs_sorted[1] if len(xs_sorted) == 3 else 0.0
    xc = (side_r + mid_r) / 2
    zc = -hz * rng.uniform(0.2, 0.45)
    lean = rng.uniform(6.0, 14.0)
    phi = rng.uniform(0.0, math.tau)
    dvec = (math.sin(math.radians(lean)) * math.cos(phi), math.cos(math.radians(lean)),
            math.sin(math.radians(lean)) * math.sin(phi))
    p0 = (xc, roof_under(zc) - 0.4, zc)
    y_top = min(ridge_top(xc, zc) + rng.uniform(0.5, 0.7), 3.95)
    length = (y_top - p0[1]) / dvec[1]
    p1 = tuple(p0[i] + dvec[i] * length for i in range(3))
    pm = tuple(p0[i] + dvec[i] * length * 0.5 for i in range(3))
    parts.append(g.tube("chimney-pipe", [p0, pm, p1], 0.075, 8, "rust"))
    cap = g.cylinder("chimney-cap", (0.0, 0.012, 0.0), 0.12, 0.024, 10, "rust_dark")
    parts.append(g.frame(cap, p1, dvec, (1.0, 0.0, 0.0)))
    chimney_top = tuple(p1[i] + dvec[i] * 0.024 for i in range(3))
    sprays.append((chimney_top, SOOT[2], SOOT[0], SOOT[1], ()))

    # ---- roof weights: tyres near the rafters and a few bricks, seated on the ridges
    placed: list[tuple[float, float, float]] = [(xc, zc, 0.2)]
    x_lim = min(xr1, -xr0) - 0.34

    def spot(radius: float, near_rafter: bool) -> tuple[float, float] | None:
        for _ in range(60):
            if near_rafter:
                x = max(-x_lim, min(x_lim, rng.choice(rafter_xs) + rng.uniform(-0.12, 0.12)))
            else:
                x = rng.uniform(-x_lim, x_lim)
            z = rng.uniform(-hz + 0.15, hz - 0.15)
            if all(math.hypot(x - px, z - pz) >= radius + pr + 0.08 for px, pz, pr in placed):
                placed.append((x, z, radius))
                return x, z
        return None

    tilt = -math.radians(slope)
    n_tyres = rng.randint(2, 4)
    t = 0
    for _ in range(n_tyres):
        at = spot(0.315, True)
        if at is None:
            continue
        tyre = g.torus(f"tire-{t}", (0.0, 0.0, 0.0), 0.24, 0.075, 10, 6, "rubber")
        tyre = g.transformed_xyz(g.transformed(tyre, rng.uniform(0, math.pi), (0.0, 0.0, 0.0)), tilt, 0.0, 0.0, (0.0, 0.0, 0.0))
        parts.append(g.seat(g.transformed(tyre, 0.0, (at[0], 0.0, at[1])), ridge_top))
        t += 1
    b = 0
    for _ in range(rng.randint(1, 3)):
        at = spot(0.18, False)
        if at is None:
            continue
        brick = g.beveled_box(f"brick-{b}", (0.0, 0.0, 0.0), (0.3, 0.1, 0.15), 0.012, "concrete_raw")
        brick = g.transformed_xyz(g.transformed(brick, rng.uniform(0, math.pi), (0.0, 0.0, 0.0)), tilt, 0.0, 0.0, (0.0, 0.0, 0.0))
        parts.append(g.seat(g.transformed(brick, 0.0, (at[0], 0.0, at[1])), ridge_top))
        b += 1
    for f in (-0.5, 0.5):                    # rust runs off the low eave
        sprays.append(((hx * f, roof_under(zr0), zr0), 1.0, RUST, 0.6, ("corrugated_rust", "corrugated")))

    # ---- rain drum under the low eave (or beside the shack where the neighbours leave room)
    ob_back = walls["back"].outer(-hx - ext, hx + ext, 0.0, 1.0)
    ws = 1 if win_side == "right" else -1
    clear = 0.29 + BATTEN_T + 0.02            # drum radius + battens nailed over the sheets
    drum_spots = [(s * (hx - 0.4), -(hz + ob_back + clear)) for s in (ws, -ws)]
    drum_spots += [(s * (hx + walls[sd].outer(-hz, hz, 0.0, 1.0) + clear), -hz + 0.4) for s, sd in ((ws, win_side), (-ws, other_side))]
    drum_spots += [(s * (hx + walls[sd].outer(-hz, hz, 0.0, 1.0) + clear), hz - 0.4) for s, sd in ((ws, win_side), (-ws, other_side))]
    drum_mat = rng.choice(("rust", "paint_teal_faded", "rust"))
    drum: list[g.MeshData] = []
    for dx, dz in drum_spots:
        body = g.cylinder("drum-body", (dx, 0.44, dz), 0.29, 0.88, 12, drum_mat)
        if not site.fits([body]):
            continue
        drum = [body, g.cylinder("drum-water", (dx, 0.883, dz), 0.265, 0.006, 12, "asphalt_wet")]
        drum += [g.cylinder(f"drum-rib-{i}", (dx, y, dz), 0.3, 0.02, 12, drum_mat) for i, y in enumerate((0.3, 0.6))]
        sprays.append(((dx, 0.05, dz), 0.45, (1.08, 0.58, 0.32), 0.7, (drum_mat,)))
        break
    parts.extend(drum)

    # ---- AC unit on concrete blocks for about half of the shacks, piped into the wall
    has_ac = rng.random() < 0.5
    ac_parts: list[g.MeshData] = []
    ac_side = None
    if has_ac:
        for side in (other_side, "back"):
            wall = walls[side]
            lo_u, hi_u = (-hz, hz) if side in ("left", "right") else (-hx, hx)
            for _ in range(8):
                uc = rng.uniform(lo_u + 0.5, hi_u - 0.5)
                ob = wall.outer(uc - 0.4, uc + 0.4, 0.0, 1.0)
                cand = [_wbox("ac-body", side, hx, hz, uc - 0.36, uc + 0.36, 0.19, 0.69, ob + 0.06, ob + 0.34, "steel_bare")]
                cand += [_wbox(f"ac-block-{i}", side, hx, hz, uc + s * 0.22 - 0.1, uc + s * 0.22 + 0.1, 0.0, 0.19,
                               ob + BATTEN_T + 0.01, ob + 0.38, "concrete_raw") for i, s in enumerate((-1, 1))]
                if not site.fits(cand) or any(_overlaps_xz(cand, drum_m) for drum_m in drum):
                    continue
                fan_c = _pt(side, hx, hz, uc - 0.08, 0.44, ob + 0.35)
                axis = "Z" if side in ("front", "back") else "X"
                cand.append(g.cylinder("ac-fan", fan_c, 0.17, 0.02, 12, "steel_dark", axis))
                up = ob + 0.2
                ow = wall.outer(uc + 0.26, uc + 0.3, 0.93, 0.97)
                cand.append(g.tube("ac-pipe", [_pt(side, hx, hz, uc + 0.28, 0.6, up), _pt(side, hx, hz, uc + 0.28, 0.95, up),
                                               _pt(side, hx, hz, uc + 0.28, 0.95, ow)], 0.018, 6, "rubber"))
                ac_parts = cand
                ac_side = side
                sprays.append((_pt(side, hx, hz, uc, 0.05, ob + 0.2), 0.5, GRIME, 0.6, ("concrete_raw", wall_mat[side])))
                break
            if ac_parts:
                break
    parts.extend(ac_parts)

    # ---- laundry line between two arms nailed to a wall, 3-6 cloths pegged on it
    laundry: dict[str, Any] = {}
    options = [other_side, "back"] if rng.random() < 0.5 else ["back", other_side]
    for side in [*options, win_side]:
        wall = walls[side]
        span = hz if side in ("left", "right") else hx
        ua, ub = -span + 0.22, span - 0.22
        v_arm = min(1.85, min(wall.top(ua), wall.top(ub)) - 0.22)     # below the top batten
        oa = wall.outer(ua - 0.03, ua + 0.03, v_arm - 0.03, v_arm + 0.03)
        obb = wall.outer(ub - 0.03, ub + 0.03, v_arm - 0.03, v_arm + 0.03)
        tip = max(oa, obb) + ARM
        arms = [_wbox(f"laundry-arm-{i}", side, hx, hz, u - 0.022, u + 0.022, v_arm - 0.022, v_arm + 0.022, o, tip, "pallet_wood")
                for i, (u, o) in enumerate(((ua, oa), (ub, obb)))]
        if not site.fits(arms):
            continue
        sag = rng.uniform(0.08, 0.14)
        line_d = tip - 0.02
        axis = g.catenary(_pt(side, hx, hz, ua, v_arm, line_d), _pt(side, hx, hz, ub, v_arm, line_d), sag, 12)
        cloth_parts = []
        avail = ub - ua - 0.24
        count = rng.randint(3, 6)
        widths = [rng.uniform(0.25, 0.5) for _ in range(count)]
        gaps = [rng.uniform(0.05, 0.15) for _ in range(count - 1)]
        scale = min(1.0, (avail - sum(gaps)) / sum(widths))
        u = ua + 0.12
        for i, wd in enumerate(widths):
            wd *= scale
            cols = []
            for c in range(3):
                uu = u + wd * c / 2
                t_ = (uu - ua) / (ub - ua)
                seg = min(11, int(t_ * 12))
                f = t_ * 12 - seg
                y_axis = axis[seg][1] + (axis[seg + 1][1] - axis[seg][1]) * f
                top = y_axis - 0.004
                h = min(rng.uniform(0.35, 0.7), top - 0.97)
                bulge = 0.02 if c == 1 else 0.0
                cols.append([_pt(side, hx, hz, uu, top - h * r / 2 - (0.03 * rng.random() if r == 2 else 0.0),
                                 line_d + 0.003 + bulge * (r / 2)) for r in range(3)])
            cols = [list(reversed(col)) for col in cols]
            cloth_parts.append(g.thick_sheet(f"laundry-cloth-{i}", cols, g.mul(NORMALS[side], -0.006), rng.choice(CLOTHS)))
            u += wd + (gaps[i] if i < len(gaps) else 0.0)
        parts.extend(arms)
        parts.append(g.tube("laundry-line", axis, 0.006, 5, "steel_dark"))
        parts.extend(cloth_parts)
        laundry = {"side": side, "line": axis}
        break

    # ---- bake the yaw
    parts = [g.planarize(g.transformed(p, yaw, (0.0, 0.0, 0.0))) for p in parts]
    cx, cz = spec["center"]

    def bake(p: Vec) -> list[float]:
        return [round(c, 6) for c in g.rotate_y(p, yaw)]

    world_sprays = []
    for centre, radius, color, strength, mats_ in sprays:
        wx, wy, wz = g.rotate_y(centre, yaw)
        world_sprays.append(Spray((wx + cx, wy, wz + cz), radius, color, strength, materials=tuple(mats_)))
    if laundry:
        laundry["line"] = [tuple(g.rotate_y(p, yaw)) for p in laundry["line"]]
    meta: dict[str, Any] = {
        "frame": {"k": k, "w": W, "d": D, "hx": hx, "hz": hz, "H": H, "slope_deg": slope, "yaw": yaw},
        "walls": walls_meta,
        "door": door,
        "window": {"side": win_side, "hole": [round(x, 4) for x in win_hole]},
        "chimney_top": bake(chimney_top),
        "chimney_lean_deg": lean,
        "ac": bool(ac_parts),
        "ac_side": ac_side,
        "laundry": laundry,
        "sprays": world_sprays,
    }
    return g.Assembly("shack", spec["id"], "shacks", (float(cx), 0.0, float(cz)), parts, meta)


def _overlaps_xz(a: list[g.MeshData], b: g.MeshData) -> bool:
    lo1, hi1 = g.bounds(a)
    lo2, hi2 = g.bounds([b])
    return all(min(hi1[k], hi2[k]) - max(lo1[k], lo2[k]) > 0.0 for k in (0, 2))


# --------------------------------------------------------------------------- sector


@register("shacks")
def shacks_assemblies(data: dict[str, Any]) -> list[g.Assembly]:
    return [build_shack(s, data) for s in data["shacks"]]
