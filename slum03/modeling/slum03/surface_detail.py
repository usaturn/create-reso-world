"""Weathered street surface for the full-stage district foundation (Task 11).

Reproduces slum02's ``ground.py`` street vocabulary on slum03's Layout: asphalt on
the three main streets, curbs with broken-out sections and their fragments, gutter
grates, manholes, puddles, concrete utility-cut patches, steel road plates (覆工板),
sealed/dirt cracks, oil drips, damp grime at wall feet and small litter.

Everything is foundation-local mesh data returned to ``ground.py`` and merged into
the single ``district-foundation`` object: no new Slots and no colliders (the
district colliders are Layout-derived boxes). Walking is protected by geometry:

* Flat detail stays below ``FLAT_TOP`` (0.01 m) above the walking plane and may
  lie on routes; its underside is sunk below the plane, never coplanar with it.
* Anything 0.01 m or taller (curbs, curb fragments, litter) is rejected by its
  evaluated XZ bounds if it touches a main route, a density corridor/opening, a
  branch clearance, the factory slab or a building footprint.
* Litter is at most ``LITTER_MAX`` (0.10 m) tall.
"""
from __future__ import annotations

import math
import random

from .density_model import stable_seed
from .geometry import MeshData, box, mesh, rotate_y
from .spatial import placement_bounds
from .types import Layout

Rect = tuple[float, float, float, float]  # x0, x1, z0, z1 (foundation-local)

ROAD_SHOULDER = 1.0   # asphalt beyond each side of a main route's 3 m effective width
LANE_VERGE = 2.0      # open concrete beside a branch lane
VERGE = 3.5           # open concrete strip beside each street that also weathers
CURB_HEIGHT = .15
CURB_WIDTH = .18
CURB_SINK = .02
CURB_SKIP = .15
FLAT_TOP = .01
LITTER_MAX = .10
FRONTAGE_PAD = .3     # loose litter/fragments keep this far from shop fronts and aprons
SINK = .002           # flat detail undersides sit below the walking plane
# Decal heights are distinct so overlapping pieces never share a plane.
Y_GRIME, Y_OIL, Y_CRACK, Y_PATCH, Y_PUDDLE, Y_GRATE, Y_MANHOLE, Y_PLATE = (
    .0015, .002, .003, .004, .005, .008, .008, .009)
BUILDING_KINDS = ('ruin', 'shack', 'nightlife', 'yarol')
BLOCKER_KINDS = BUILDING_KINDS + ('stall', 'north-wall', 'rubble')
LITTER_MATERIALS = ('plywood', 'plywood', 'tarp_blue', 'tarp_orange', 'rubber')


def _overlap(a: Rect, b: Rect, pad: float = 0.) -> bool:
    return a[0] < b[1] + pad and a[1] > b[0] - pad and a[2] < b[3] + pad and a[3] > b[2] - pad


def _minus(r: Rect, hole: Rect) -> list[Rect]:
    """Axis-aligned rectangle difference (up to four pieces)."""
    if not _overlap(r, hole):
        return [r]
    x0, x1, z0, z1 = r
    hx0, hx1, hz0, hz1 = max(hole[0], x0), min(hole[1], x1), max(hole[2], z0), min(hole[3], z1)
    pieces = [(x0, hx0, z0, z1), (hx1, x1, z0, z1), (hx0, hx1, z0, hz0), (hx0, hx1, hz1, z1)]
    return [p for p in pieces if p[1] - p[0] > 1e-6 and p[3] - p[2] > 1e-6]


def _minus_all(rects: list[Rect], holes: list[Rect]) -> list[Rect]:
    for hole in holes:
        rects = [piece for r in rects for piece in _minus(r, hole)]
    return rects


def _clip(r: Rect, limit: Rect) -> Rect | None:
    c = (max(r[0], limit[0]), min(r[1], limit[1]), max(r[2], limit[2]), min(r[3], limit[3]))
    return c if c[1] - c[0] > 1e-6 and c[3] - c[2] > 1e-6 else None


def _xz_box(part: MeshData) -> Rect:
    xs = [v[0] for v in part.vertices]
    zs = [v[2] for v in part.vertices]
    return min(xs), max(xs), min(zs), max(zs)


def _top(part: MeshData) -> float:
    return max(v[1] for v in part.vertices)


class Site:
    """Street geometry derived from the Layout, in foundation-local coordinates."""

    def __init__(self, layout: Layout, ox: float, oz: float, district: Rect, floor: Rect,
                 frontages: list[Rect] = ()):
        def local(r) -> Rect:
            return (r.x_min - ox, r.x_max - ox, r.z_min - oz, r.z_max - oz)
        self.district, self.floor = district, floor
        # Stall fronts and nightlife entrance aprons (foundation-local), kept free of loose debris.
        self.frontages: list[Rect] = sorted(frontages)
        density = layout.density
        self.protected: list[Rect] = [local(r) for r in layout.routes]
        for route in density.routes:
            self.protected.append(local(route.corridor))
            self.protected.extend(local(o.bounds) for o in route.openings)
        self.protected.extend(local(r) for r in density.branch_clearances)
        # Main streets: each route's effective width plus a shoulder, inside the
        # district and never on the factory slab.
        self.roads: list[Rect] = []
        for r in layout.routes:
            x0, x1, z0, z1 = local(r)
            if x1 - x0 >= z1 - z0:
                band = (x0, x1, z0 - ROAD_SHOULDER, z1 + ROAD_SHOULDER)
            else:
                band = (x0 - ROAD_SHOULDER, x1 + ROAD_SHOULDER, z0, z1)
            clipped = _clip(band, district)
            if clipped:
                self.roads.extend(p for p in _minus(clipped, floor) if max(p[1]-p[0], p[3]-p[2]) > 4)
        # Branch lanes (枝道): the authored density corridors off the asphalt
        # (the market spine is already a main street).
        self.lanes: list[Rect] = []
        for route in density.routes:
            clipped = _clip(local(route.corridor), district)
            if clipped:
                self.lanes.extend(_minus_all([clipped], [floor, *self.roads]))
        self.blockers: list[Rect] = []
        self.buildings: list[Rect] = []
        for p in layout.placements:
            if p.kind not in BLOCKER_KINDS:
                continue
            b = placement_bounds(p)
            r = _clip((b.minimum[0] - ox, b.maximum[0] - ox, b.minimum[2] - oz, b.maximum[2] - oz),
                      district)
            if r is None:
                continue
            self.blockers.append(r)
            if p.kind in BUILDING_KINDS:
                self.buildings.append(r)
        # Placement order must not change the result (same keys, same geometry).
        self.blockers.sort()
        self.buildings.sort()
        self.streets = self.roads + self.lanes
        # Verges: open concrete beside each main street (outside the asphalt,
        # never under a building) where dirt cracks and damp stains collect.
        self.verges: list[Rect] = []
        for road in self.roads:
            wide = ((road[0], road[1], road[2] - VERGE, road[3] + VERGE) if _long_x(road)
                    else (road[0] - VERGE, road[1] + VERGE, road[2], road[3]))
            clipped = _clip(wide, district)
            if clipped:
                self.verges.extend(_minus_all([clipped], [road, floor]))
        for lane in self.lanes:
            wide = ((lane[0], lane[1], lane[2] - LANE_VERGE, lane[3] + LANE_VERGE) if _long_x(lane)
                    else (lane[0] - LANE_VERGE, lane[1] + LANE_VERGE, lane[2], lane[3]))
            clipped = _clip(wide, district)
            if clipped:
                self.verges.extend(_minus_all([clipped], [floor, *self.roads, *self.lanes]))

    def open_ground(self, r: Rect) -> bool:
        return self.flat_clear(r) and not any(_overlap(r, b) for b in self.blockers)

    def standing_clear(self, r: Rect, blocker_pad: float = 0.) -> bool:
        """A part 0.01 m or taller may occupy r (evaluated XZ bounds)."""
        d = self.district
        return (d[0] + .2 <= r[0] and r[1] <= d[1] - .2 and d[2] + .2 <= r[2] and r[3] <= d[3] - .2
                and not any(_overlap(r, p) for p in self.protected)
                and not _overlap(r, self.floor, .3)
                and not any(_overlap(r, b, blocker_pad) for b in self.blockers))

    def loose_clear(self, r: Rect) -> bool:
        """Loose small debris (litter, curb fragments): standing_clear and off every frontage."""
        return (self.standing_clear(r) and
                not any(_overlap(r, f, FRONTAGE_PAD) for f in self.frontages))

    def near_street(self, r: Rect, reach: float = 3.5) -> bool:
        return any(_overlap(r, s, reach) for s in self.streets)

    def flat_clear(self, r: Rect) -> bool:
        d = self.district
        return (d[0] + .1 <= r[0] and r[1] <= d[1] - .1 and d[2] + .1 <= r[2] and r[3] <= d[3] - .1
                and not _overlap(r, self.floor, .2))


# --------------------------------------------------------------------------- base surface

def surface_partition(x0: float, x1: float, z0: float, z1: float, y: float,
                      features: list[tuple[Rect, str, str]],
                      base: tuple[str, str] = ('foundation-top', 'concrete_raw')) -> list[MeshData]:
    """Coplanar, non-overlapping +Y cells covering one strip once, one part per (name, material).

    Features are painted by priority (first wins). Cells are built per X slab with
    Z runs merged, so an edge no longer cuts the whole strip. Each cell also carries
    the vertices its neighbouring slabs place on the shared X edge, which keeps the
    top watertight (no T-junctions).
    """
    inside = [f for f in features if _overlap(f[0], (x0, x1, z0, z1))]
    xs = sorted({x0, x1, *(min(max(v, x0), x1) for f in inside for v in f[0][:2])})
    slabs = []
    for xa, xb in zip(xs, xs[1:]):
        mid = (xa + xb) / 2
        spanning = [f for f in inside if f[0][0] < mid < f[0][1]]
        zs = sorted({z0, z1, *(min(max(v, z0), z1) for f in spanning for v in f[0][2:])})
        runs: list[list] = []
        for za, zb in zip(zs, zs[1:]):
            cz = (za + zb) / 2
            hit = next((f for f in spanning if f[0][2] < cz < f[0][3]), None)
            key = (hit[1], hit[2]) if hit else base
            if runs and runs[-1][2] == key:
                runs[-1][1] = zb
            else:
                runs.append([za, zb, key])
        slabs.append((xa, xb, runs))
    breaks = [sorted({r[0] for r in runs} | {r[1] for r in runs}) for _, _, runs in slabs]
    buckets: dict[tuple[str, str], tuple[dict, list]] = {}
    for i, (xa, xb, runs) in enumerate(slabs):
        left = breaks[i-1] if i else []
        right = breaks[i+1] if i + 1 < len(slabs) else []
        for za, zb, key in runs:
            ring = [(xa, zb), (xb, zb)]
            ring += [(xb, z) for z in sorted((z for z in right if za < z < zb), reverse=True)]
            ring += [(xb, za), (xa, za)]
            ring += [(xa, z) for z in sorted(z for z in left if za < z < zb)]
            index, faces = buckets.setdefault(key, ({}, []))
            faces.append(tuple(index.setdefault(c, len(index)) for c in ring))
    return [mesh(name, [(vx, y, vz) for vx, vz in index], faces, material)
            for (name, material), (index, faces) in buckets.items()]


# --------------------------------------------------------------------------- primitives

def _transform(part: MeshData, name: str, tilt: float, yaw: float, offset) -> MeshData:
    """Rotate about local X (tilt), then about +Y (yaw), then translate."""
    c, s = math.cos(tilt), math.sin(tilt)
    verts = []
    for x, y, z in part.vertices:
        p = rotate_y((x, y*c - z*s, y*s + z*c), yaw)
        verts.append((p[0] + offset[0], p[1] + offset[1], p[2] + offset[2]))
    return mesh(name, verts, part.faces, part.material)


def _flat_poly(name: str, outline, y: float, material: str) -> MeshData:
    """Single +Y polygon (a decal seen only from above)."""
    pts = list(outline)
    area = sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
    if area > 0:  # counter-clockwise in (x, z) faces -Y in Resonite XYZ
        pts.reverse()
    return mesh(name, [(x, y, z) for x, z in pts], [tuple(range(len(pts)))], material)


def _octagon(rng: random.Random, cx: float, cz: float, r: float, jitter: float = .25):
    phase = rng.uniform(0, math.tau)
    return [(cx + math.cos(phase + math.tau*k/8) * r * (1 + rng.uniform(-jitter, jitter)),
             cz + math.sin(phase + math.tau*k/8) * r * (1 + rng.uniform(-jitter, jitter)))
            for k in range(8)]


def _slab(name: str, centre, size, top: float, material: str) -> MeshData:
    """Thin flat box whose underside is sunk below the walking plane."""
    return box(name, (centre[0], (top - SINK) / 2, centre[1]), (size[0], top + SINK, size[1]), material)


def _curb_stone(length: float, rng: random.Random) -> MeshData:
    """Closed curb prism along local X, chamfered top edges; the road side (-Z) is sometimes chipped."""
    h, w, b = CURB_HEIGHT, CURB_WIDTH, .02
    chip = b + (rng.uniform(.015, .035) if rng.random() < .3 else 0.)
    profile = [(-w/2, 0.), (w/2, 0.), (w/2, h-b), (w/2-b, h), (-w/2+chip, h), (-w/2, h-chip)]
    hl = length / 2
    verts = [(-hl, y, z) for z, y in profile] + [(hl, y, z) for z, y in profile]
    n = len(profile)
    faces = [tuple(range(n)), tuple(range(2*n-1, n-1, -1))]
    faces += [(k, k+n, (k+1) % n + n, (k+1) % n) for k in range(n)]
    return mesh('curb', verts, faces, 'concrete_raw')


def _disc(name: str, cx: float, cz: float, r: float, top: float, material: str, sides: int = 12) -> MeshData:
    ring = [(cx + math.cos(math.tau*k/sides)*r, cz + math.sin(math.tau*k/sides)*r) for k in range(sides)]
    verts = [(x, top, z) for x, z in ring] + [(x, -SINK, z) for x, z in ring]
    faces = [tuple(range(sides-1, -1, -1)), tuple(range(sides, 2*sides))]
    faces += [(k, (k+1) % sides, sides + (k+1) % sides, sides + k) for k in range(sides)]
    return mesh(name, verts, faces, material)


# --------------------------------------------------------------------------- generators

def _rng(layout: Layout, channel: str) -> random.Random:
    return random.Random(stable_seed(layout.seed, 'street-surface', channel))


def _long_x(r: Rect) -> bool:
    return r[1] - r[0] >= r[3] - r[2]


def _pick(rng: random.Random, rects: list[Rect], margin: float):
    usable = [r for r in rects if r[1] - r[0] > 2*margin and r[3] - r[2] > 2*margin]
    if not usable:
        return None
    r = rng.choices(usable, weights=[(u[1]-u[0]) * (u[3]-u[2]) for u in usable])[0]
    return r, rng.uniform(r[0] + margin, r[1] - margin), rng.uniform(r[2] + margin, r[3] - margin)


def _curbs(site: Site, rng: random.Random):
    curbs, chunks, grates = [], [], []
    for road in site.roads:
        along_x = _long_x(road)
        lo, hi = (road[0], road[1]) if along_x else (road[2], road[3])
        for edge, sign in (((road[2], -1), (road[3], 1)) if along_x else ((road[0], -1), (road[1], 1))):
            def at(t: float, off: float):
                return (t, edge + sign*off) if along_x else (edge + sign*off, t)

            def rect(a: float, b: float, o0: float, o1: float) -> Rect:
                (px, pz), (qx, qz) = at(a, o0), at(b, o1)
                return min(px, qx), max(px, qx), min(pz, qz), max(pz, qz)
            t = lo + .2
            while t < hi - .5:
                length = min(rng.uniform(1., 2.5), hi - .2 - t)
                a, b = t, t + length
                t = b
                if length < .4 or not site.standing_clear(rect(a, b, 0., CURB_WIDTH), .3):
                    continue
                mid = (a + b) / 2
                yaw = 0. if along_x else math.pi / 2
                if rng.random() < CURB_SKIP:  # broken-out stone: its fragments stay in the gap
                    for _ in range(rng.randint(1, 2)):
                        fl, fh, fw = rng.uniform(.2, .45), rng.uniform(.06, .10), rng.uniform(.12, .18)
                        fx, fz = at(rng.uniform(a + .2, b - .2), rng.uniform(-.35, .1))
                        piece = box('chunk', (0, fh/2 - .012, 0), (fl, fh, fw), 'concrete_raw')
                        piece = _transform(piece, f'curbchunk-{len(chunks):03d}',
                                           math.radians(rng.uniform(-12, 12)), rng.uniform(0, math.tau),
                                           (fx, 0., fz))
                        if site.loose_clear(_xz_box(piece)) and _top(piece) <= .12:
                            chunks.append(piece)
                    continue
                sunk = rng.random() < .12
                drop = rng.uniform(.02, .04) if sunk else rng.uniform(-.004, .004)
                tilt = math.radians(rng.uniform(2., 5.)) * sign if sunk else 0.
                cx, cz = at(mid, CURB_WIDTH / 2)
                stone = _curb_stone(length - .02, rng)  # 0.02 m joint between stones
                # Local -Z (chipped road side) faces the street after the yaw.
                face = yaw + (0. if sign > 0 else math.pi)
                stone = _transform(stone, f'curb-{len(curbs):03d}', tilt, face,
                                   (cx, -CURB_SINK - drop, cz))
                if not site.standing_clear(_xz_box(stone), .3):
                    continue
                curbs.append(stone)
                if rng.random() < .16:
                    gx, gz = at(mid, -.3)
                    grates.extend(_grate(len(grates) // 10, gx, gz, yaw))
    return curbs, chunks, grates


def _grate(index: int, x: float, z: float, yaw: float) -> list[MeshData]:
    """0.84 x 0.44 m gutter grating: dark sump plate, side frames and cross bars."""
    parts = [_slab('plate', (0, 0), (.84, .44), Y_GRATE - .004, 'rubber'),
             _slab('frame', (0, .2), (.84, .04), Y_GRATE, 'rust_dark'),
             _slab('frame', (0, -.2), (.84, .04), Y_GRATE, 'rust_dark')]
    parts += [_slab('bar', (-.36 + k*.12, 0), (.03, .36), Y_GRATE - .001, 'rust_dark') for k in range(7)]
    return [_transform(p, f'grate-{index:02d}-{k}', 0., yaw, (x, 0., z)) for k, p in enumerate(parts)]


def _manholes(site: Site, rng: random.Random, avoid: list):
    parts = []
    for road in site.roads:
        along_x = _long_x(road)
        lo, hi = (road[0], road[1]) if along_x else (road[2], road[3])
        centre = (road[2] + road[3]) / 2 if along_x else (road[0] + road[1]) / 2
        for k in range(2):
            t = lo + (hi - lo) * (k + rng.uniform(.25, .75)) / 2
            across = centre + rng.uniform(-.4, .4)
            x, z = (t, across) if along_x else (across, t)
            if not site.flat_clear((x - .6, x + .6, z - .6, z + .6)):
                continue
            n = len(parts) // 4
            parts.append(_slab(f'manhole-{n}-frame', (x, z), (.95, .95), Y_MANHOLE - .004, 'concrete_dark'))
            parts.append(_disc(f'manhole-{n}-lid', x, z, .35, Y_MANHOLE - .001, 'steel_dark'))
            spin = rng.uniform(0, math.pi)
            for b in range(2):
                rib = _slab('rib', (0, 0), (.6, .035), Y_MANHOLE, 'steel_dark')
                parts.append(_transform(rib, f'manhole-{n}-rib{b}', 0., spin + b*math.pi/2, (x, 0., z)))
            avoid.append((x, z, .7))
    return parts


def _free(x: float, z: float, r: float, avoid: list) -> bool:
    return all(math.hypot(x - ax, z - az) >= r + ar + .3 for ax, az, ar in avoid)


def _patches(site: Site, rng: random.Random, avoid: list):
    parts: list[MeshData] = []
    plates = patches = tries = 0
    while (plates < 4 or patches < 12) and tries < 4000:
        tries += 1
        plate = plates < 4
        pick = _pick(rng, site.roads if plate or patches < 8 else site.lanes, 1.2)
        if pick is None:
            continue
        r, x, z = pick
        along, across = ((rng.uniform(2.4, 3.0), rng.uniform(1.4, 1.6)) if plate
                         else (rng.uniform(1.0, 3.2), rng.uniform(.5, 1.3)))
        across = min(across, (min(r[1]-r[0], r[3]-r[2])) - .4)
        sx, sz = (along, across) if _long_x(r) else (across, along)
        x = min(max(x, r[0] + sx/2 + .1), r[1] - sx/2 - .1)
        z = min(max(z, r[2] + sz/2 + .1), r[3] - sz/2 - .1)
        rad = math.hypot(sx, sz) / 2
        if not site.flat_clear((x - rad, x + rad, z - rad, z + rad)) or not _free(x, z, rad, avoid):
            continue
        avoid.append((x, z, rad))
        yaw = math.radians(rng.uniform(-2.5, 2.5))
        if plate:
            part = _slab('plate', (0, 0), (sx, sz), Y_PLATE, 'steel_dark')
            parts.append(_transform(part, f'roadplate-{plates}', 0., yaw, (x, 0., z)))
            plates += 1
        else:
            part = _slab('patch', (0, 0), (sx, sz), Y_PATCH, 'concrete_dark')
            parts.append(_transform(part, f'patch-{patches:02d}', 0., yaw, (x, 0., z)))
            patches += 1
    return parts


def _puddles(site: Site, rng: random.Random, avoid: list):
    parts = []
    tries = 0
    while len(parts) < 12 and tries < 4000:
        tries += 1
        pick = _pick(rng, site.roads if len(parts) < 7 else site.lanes, .8)
        if pick is None:
            continue
        r, x, z = pick
        span = min(r[1] - r[0], r[3] - r[2])
        radius = min(rng.uniform(.5, 1.4), (span / 2 - .2) / 1.3)
        if radius < .3:
            continue
        x = min(max(x, r[0] + radius*1.3), r[1] - radius*1.3)
        z = min(max(z, r[2] + radius*1.3), r[3] - radius*1.3)
        box_ = (x - radius*1.3, x + radius*1.3, z - radius*1.3, z + radius*1.3)
        if not site.flat_clear(box_) or not _free(x, z, radius*1.25, avoid):
            continue
        avoid.append((x, z, radius*1.25))
        parts.append(_flat_poly(f'puddle-{len(parts):02d}', _octagon(rng, x, z, radius),
                                Y_PUDDLE, 'asphalt_wet'))
    return parts


def _crack(name: str, points, y: float, width: float, material: str) -> MeshData:
    """Tapered strip of +Y quads (single-sided decal)."""
    n = len(points)
    left, right = [], []
    for k, (x, z) in enumerate(points):
        ax, az = points[max(k-1, 0)]
        bx, bz = points[min(k+1, n-1)]
        dx, dz = bx - ax, bz - az
        length = math.hypot(dx, dz) or 1.
        hw = width / 2 * (math.sin(math.pi * (k + .5) / n) * .8 + .2)
        px, pz = -dz / length * hw, dx / length * hw
        left.append((x + px, z + pz))
        right.append((x - px, z - pz))
    verts, faces = [], []
    for (lx, lz), (rx, rz) in zip(left, right):
        verts += [(lx, y, lz), (rx, y, rz)]
    for k in range(n - 1):
        quad = [2*k, 2*k + 2, 2*k + 3, 2*k + 1]
        pts = [(verts[i][0], verts[i][2]) for i in quad]
        area = sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
        faces.append(tuple(reversed(quad)) if area > 0 else tuple(quad))
    return mesh(name, verts, faces, material)


def _cracks(site: Site, rng: random.Random):
    parts = []
    # Tar-sealed asphalt cracks mostly follow the street; dirt-filled ones in lane concrete.
    for count, rects, y, widths, material in ((48, site.roads, Y_CRACK, (.02, .045), 'rubber'),
                                              (40, site.lanes, Y_CRACK - .0005, (.03, .06), 'mud'),
                                              (36, site.verges, Y_CRACK - .0005, (.03, .06), 'mud')):
        clear = site.flat_clear if rects is not site.verges else site.open_ground
        made = 0
        for _ in range(count * 3):
            if made >= count:
                break
            pick = _pick(rng, rects, .4)
            if pick is None:
                break
            r, x, z = pick
            heading = (0. if _long_x(r) else math.pi / 2) + rng.uniform(-.6, .6)
            heading += math.pi if rng.random() < .5 else 0.
            if not clear((x - .1, x + .1, z - .1, z + .1)):
                continue
            pts = [(x, z)]
            for _ in range(rng.randint(6, 14)):
                heading += rng.uniform(-.55, .55)
                step = rng.uniform(.35, .8)
                nxt = (pts[-1][0] + math.cos(heading)*step, pts[-1][1] + math.sin(heading)*step)
                if not (r[0] + .25 < nxt[0] < r[1] - .25 and r[2] + .25 < nxt[1] < r[3] - .25):
                    break
                if not clear((nxt[0] - .1, nxt[0] + .1, nxt[1] - .1, nxt[1] + .1)):
                    break
                pts.append(nxt)
            if len(pts) >= 4:
                parts.append(_crack(f'crack-{len(parts):03d}', pts, y, rng.uniform(*widths), material))
                made += 1
    return parts


def _oil(site: Site, rng: random.Random):
    parts = []
    tries = 0
    while len(parts) < 30 and tries < 3000:
        tries += 1
        on_road = len(parts) < 12
        rects = site.roads if on_road else site.lanes if len(parts) < 18 else site.verges
        pick = _pick(rng, rects, .8)
        if pick is None:
            continue
        _, x, z = pick
        radius = rng.uniform(.35, .9) if rects is not site.verges else rng.uniform(.8, 1.8)
        clear = site.open_ground if rects is site.verges else site.flat_clear
        if not clear((x - radius*1.3, x + radius*1.3, z - radius*1.3, z + radius*1.3)):
            continue
        parts.append(_flat_poly(f'oildrip-{len(parts):02d}', _octagon(rng, x, z, radius, .35), Y_OIL,
                                'rubber' if on_road else 'concrete_dark'))
    return parts


def _wall_sides(site: Site):
    """Building sides that face open ground within 4 m of a street or lane.

    Yields (building, axis, edge, outward sign, lo, hi): a side at X=edge (axis 'x')
    or Z=edge (axis 'z') spanning lo..hi along the other axis.
    """
    for b in site.buildings:
        for axis, edge, sign, lo, hi in (('x', b[0], -1, b[2], b[3]), ('x', b[1], 1, b[2], b[3]),
                                         ('z', b[2], -1, b[0], b[1]), ('z', b[3], 1, b[0], b[1])):
            if hi - lo < 1.5:
                continue
            strip = ((min(edge, edge + sign*.8), max(edge, edge + sign*.8), lo, hi) if axis == 'x'
                     else (lo, hi, min(edge, edge + sign*.8), max(edge, edge + sign*.8)))
            if _overlap(strip, site.floor) or not any(_overlap(strip, s, 4.) for s in site.streets):
                continue
            yield b, axis, edge, sign, lo, hi


def _grime_and_litter(site: Site, rng: random.Random):
    grime, litter = [], []
    sides = list(_wall_sides(site))
    rng.shuffle(sides)
    for _building, axis, edge, sign, lo, hi in sides:
        def pt(t: float, off: float):
            return (edge + sign*off, t) if axis == 'x' else (t, edge + sign*off)
        for _try in range(3 if len(grime) < 40 and rng.random() < .55 else 0):
            length = rng.uniform(1.5, min(4., hi - lo - .4))
            a = rng.uniform(lo + .2, hi - .2 - length)
            n = 6
            inner = [pt(a + length*k/n, .02) for k in range(n + 1)]
            outer = [pt(a + length*k/n, .02 + rng.uniform(.25, .8) * math.sin(math.pi * (k + .5) / (n + 1)) + .05)
                     for k in range(n + 1)]
            region = (min(p[0] for p in inner + outer), max(p[0] for p in inner + outer),
                      min(p[1] for p in inner + outer), max(p[1] for p in inner + outer))
            if (site.flat_clear(region) and site.near_street(region) and
                    not any(_overlap(region, o, -.05) for o in site.blockers)):
                verts, faces = [], []
                for (ix, iz), (px, pz) in zip(inner, outer):
                    verts += [(ix, Y_GRIME, iz), (px, Y_GRIME, pz)]
                for k in range(n):
                    quad = [2*k, 2*k + 2, 2*k + 3, 2*k + 1]
                    pts = [(verts[i][0], verts[i][2]) for i in quad]
                    area = sum(p[0]*q[1] - q[0]*p[1] for p, q in zip(pts, pts[1:] + pts[:1]))
                    faces.append(tuple(reversed(quad)) if area > 0 else tuple(quad))
                grime.append(mesh(f'wallgrime-{len(grime):02d}', verts, faces, 'mud'))
                break
        if len(litter) >= 48 or rng.random() > .6:
            continue
        def spot(t: float) -> Rect:
            x, z = pt(t, .2)
            return x, x, z, z
        starts = [t for t in (rng.uniform(lo + .2, hi - .2) for _ in range(6))
                  if site.near_street(spot(t), 3.)]
        if not starts:
            continue
        start = starts[0]
        direction = 1 if rng.random() < .5 else -1
        for _k in range(rng.randint(3, 5)):
            t = start + direction * rng.uniform(.1, 2.5)
            if not lo + .1 < t < hi - .1:
                continue
            x, z = pt(t, rng.uniform(.08, .28))
            w, d = rng.uniform(.1, .4), rng.uniform(.1, .4)
            flat = rng.random() < .55
            h = rng.uniform(.004, .012) if flat else rng.uniform(.03, .07)
            tilt = 0. if flat else math.radians(rng.uniform(-6, 6))
            piece = box('scrap', (0, h/2 - .004, 0), (w, h, d), rng.choice(LITTER_MATERIALS))
            piece = _transform(piece, f'litter-{len(litter):02d}', tilt, rng.uniform(0, math.tau), (x, 0., z))
            if (_top(piece) <= LITTER_MAX and site.loose_clear(_xz_box(piece)) and
                    site.near_street(_xz_box(piece))):
                litter.append(piece)
    return grime, litter


def street_detail(layout: Layout, site: Site) -> list[MeshData]:
    """All raised street detail (no base surface), deterministic from the Layout seed."""
    avoid: list = []
    manholes = _manholes(site, _rng(layout, 'manholes'), avoid)
    curbs, chunks, grates = _curbs(site, _rng(layout, 'curbs'))
    for part in grates[::10]:
        b = _xz_box(part)
        avoid.append(((b[0] + b[1]) / 2, (b[2] + b[3]) / 2, .5))
    patches = _patches(site, _rng(layout, 'patches'), avoid)
    puddles = _puddles(site, _rng(layout, 'puddles'), avoid)
    cracks = _cracks(site, _rng(layout, 'cracks'))
    oil = _oil(site, _rng(layout, 'oil'))
    grime, litter = _grime_and_litter(site, _rng(layout, 'walls'))
    return [*grime, *oil, *cracks, *patches, *puddles, *manholes, *grates, *curbs, *chunks, *litter]
