"""Central factory floor and surviving north-facing footprint of the south-facing wall."""
import math
import random

from .density_model import stable_seed
from .geometry import Assembly, MeshData, box, face_normal, mesh, tube
from .types import Layout

# Task 12 (revision 1): shallow depressions only. The walking collider stays the
# flat slab top (Y=0); a dish at most 5 cm deep with >=0.3 m sloped sides reads as
# worn, ponding concrete without a step, and feet float at most 5 cm over it.
PIT_DEPTH_MAX = .05
PIT_DEPTHS = (.035, .045, .05)
CELL = 2.
SPECIAL_CELLS = {(3, 3): 'asphalt_wet', (13, 4): 'asphalt_wet', (17, 11): 'asphalt_wet',
                 (7, 12): 'asphalt_wet', (4, 3): 'concrete_dark', (14, 4): 'concrete_dark',
                 (10, 9): 'concrete_dark', (7, 11): 'concrete_dark'}
# Flush decal planes (metres above the slab), distinct so overlaps never z-fight.
Y_TONE, Y_HALO, Y_DAMP, Y_OIL, Y_CRACK, Y_PAD, Y_RUST, Y_GROUT, Y_BOLT = (
    .0008, .0012, .0015, .0025, .003, .0035, .004, .0045, .005)
TONE_REACH = 1.25 * 1.12  # outline radius bound: (1 + max lobe) * max jitter
# Fix round 1: broad tone patches read at eye height (slum02 colour unevenness).
TONE_MATERIALS = ('concrete_stained', 'concrete_dark', 'mud', 'asphalt_wet', 'concrete_patch',
                  'concrete_dark', 'concrete_stained', 'mud')


def _full_stage(layout: Layout) -> bool:
    return layout.density is not None and layout.density.stage == 'full'


def _rng(layout: Layout, channel: str) -> random.Random:
    return random.Random(stable_seed(layout.seed, 'factory-floor', channel))


def _hit(a, b, pad=0.) -> bool:
    """Overlap of (x0, x1, z0, z1) rectangles."""
    return a[0] < b[1] + pad and a[1] > b[0] - pad and a[2] < b[3] + pad and a[3] > b[2] - pad


def _keepouts(layout: Layout):
    from .gn_scatter import floor_keepouts
    return [r.bounds for r in floor_keepouts(layout)]


def floor_features(layout: Layout) -> dict:
    """Seeded pits (grid-cell aligned) and machine-base traces, world XZ rectangles."""
    plaza, clear = layout.plaza, layout.clear
    keep = _keepouts(layout)
    rng = _rng(layout, 'pits')
    pits, cells = [], []
    for span in ((1, 1), (2, 1), (1, 1), (1, 2), (1, 1), (1, 1), (2, 1)):
        for _ in range(400):
            ni, nj = span
            i = rng.randrange(20 - ni + 1)
            j = rng.randrange(15 - nj + 1)
            rect = (plaza.x_min + i*CELL, plaza.x_min + (i+ni)*CELL,
                    plaza.z_min + j*CELL, plaza.z_min + (j+nj)*CELL)
            own = {(a, b) for a in range(i, i+ni) for b in range(j, j+nj)}
            if (clear.x_min <= rect[0] and rect[1] <= clear.x_max and
                    clear.z_min <= rect[2] and rect[3] <= clear.z_max and
                    not own & SPECIAL_CELLS.keys() and
                    not any(_hit(rect, k, .5) for k in keep) and
                    not any(_hit(rect, other, CELL - .1) for other in pits)):
                pits.append(rect)
                cells.append((i, j, ni, nj))
                break
    rng = _rng(layout, 'bases')
    bases = []
    for _ in range(600):
        if len(bases) >= 5:
            break
        sx, sz = rng.uniform(2., 3.4), rng.uniform(1.4, 2.4)
        if rng.random() < .5:
            sx, sz = sz, sx
        cx = rng.uniform(clear.x_min + sx/2 + .4, clear.x_max - sx/2 - .4)
        cz = rng.uniform(clear.z_min + sz/2 + .4, clear.z_max - sz/2 - .4)
        rect = (cx - sx/2, cx + sx/2, cz - sz/2, cz + sz/2)
        if (any(_hit(rect, k, .3) for k in keep) or any(_hit(rect, pit, .4) for pit in pits)
                or any(_hit(rect, other, .8) for other in bases)):
            continue
        bases.append(rect)
    return {'pits': pits, 'pit_cells': cells, 'bases': bases}


def _up(name, verts, faces, material) -> MeshData:
    """Orient every face towards +Y (seen from above), matching the inlaid cells."""
    oriented = []
    for face in faces:
        n = face_normal([verts[i] for i in face])
        oriented.append(tuple(face) if n[1] > 0 else tuple(reversed(face)))
    return mesh(name, verts, oriented, material)


def _flat(name, outline, y, material) -> MeshData:
    return _up(name, [(x, y, z) for x, z in outline], [tuple(range(len(outline)))], material)


def _octagon(rng, cx, cz, r, jitter=.25):
    phase = rng.uniform(0, math.tau)
    return [(cx + math.cos(phase + math.tau*k/8) * r * (1 + rng.uniform(-jitter, jitter)),
             cz + math.sin(phase + math.tau*k/8) * r * (1 + rng.uniform(-jitter, jitter)))
            for k in range(8)]


def _pit(k, rect, ni, nj, rng, ox, oz) -> list[MeshData]:
    """Grid-aligned shallow dish: rim on the cell corners, sloped sides, mud bottom, water."""
    x0, x1, z0, z1 = rect[0] - ox, rect[1] - ox, rect[2] - oz, rect[3] - oz
    d = PIT_DEPTHS[k % len(PIT_DEPTHS)]
    ix0, ix1 = x0 + rng.uniform(.3, .55), x1 - rng.uniform(.3, .55)
    iz0, iz1 = z0 + rng.uniform(.3, .55), z1 - rng.uniform(.3, .55)
    outer = {(a, b): (x0 + CELL*a, 0., z0 + CELL*b) for a in range(ni+1) for b in range(nj+1)}
    inner = {(a, b): (ix0 + (ix1-ix0)*a/ni, -d, iz0 + (iz1-iz0)*b/nj)
             for a in range(ni+1) for b in range(nj+1)}
    ring = ([(a, 0) for a in range(ni)] + [(ni, b) for b in range(nj)] +
            [(a, nj) for a in range(ni, 0, -1)] + [(0, b) for b in range(nj, 0, -1)])
    verts, faces = [], []
    for s, a in enumerate(ring):
        b = ring[(s+1) % len(ring)]
        base = len(verts)
        verts += [outer[a], outer[b], inner[b], inner[a]]
        faces.append((base, base+1, base+2, base+3))
    slope = _up(f'pit-{k}-slope', verts, faces, 'concrete_dark')
    keys = sorted(inner)
    index = {key: n for n, key in enumerate(keys)}
    bottom = _up(f'pit-{k}-bottom', [inner[key] for key in keys],
                 [(index[(a, b)], index[(a+1, b)], index[(a+1, b+1)], index[(a, b+1)])
                  for a in range(ni) for b in range(nj)], 'mud')
    cx, cz = (ix0+ix1)/2 + rng.uniform(-.2, .2), (iz0+iz1)/2 + rng.uniform(-.2, .2)
    radius = min(ix1-ix0, iz1-iz0) * .32
    water = _flat(f'pit-{k}-water', _octagon(rng, cx, cz, radius, .2), -d + .004, 'asphalt_wet')
    # Muddy wash-out ring on the slab around the rim (flush, outside the dish), with a
    # ragged outer edge so the square cut reads as worn rather than drawn.
    n = 4
    inner_ring = ([(x0 + (x1-x0)*t/n, z0) for t in range(n)] + [(x1, z0 + (z1-z0)*t/n) for t in range(n)] +
                  [(x1 - (x1-x0)*t/n, z1) for t in range(n)] + [(x0, z1 - (z1-z0)*t/n) for t in range(n)])
    cx0, cz0 = (x0 + x1) / 2, (z0 + z1) / 2
    outer_ring = []
    for px, pz in inner_ring:
        dx, dz = px - cx0, pz - cz0
        nx = (1 if dx > 1e-9 else -1 if dx < -1e-9 else 0) if abs(abs(dx) - (x1-x0)/2) < 1e-9 else 0
        nz = (1 if dz > 1e-9 else -1 if dz < -1e-9 else 0) if abs(abs(dz) - (z1-z0)/2) < 1e-9 else 0
        w = rng.uniform(.12, .45)  # stays inside the 0.5 m pit-to-route margin
        outer_ring.append((px + nx*w, pz + nz*w))
    halo = [_flat(f'pit-{k}-halo', [inner_ring[q], inner_ring[(q+1) % len(inner_ring)],
                                    outer_ring[(q+1) % len(inner_ring)], outer_ring[q]], Y_HALO, 'mud')
            for q in range(len(inner_ring))]
    return [slope, bottom, water, *halo]


def _base(k, rect, rng, ox, oz) -> list[MeshData]:
    """Trace of a removed machine: newer grout pad, cut outline, sheared bolts, rust and oil."""
    x0, x1, z0, z1 = rect[0] - ox, rect[1] - ox, rect[2] - oz, rect[3] - oz
    parts = [_flat(f'base-{k}-pad', [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], Y_PAD, 'concrete_patch')]
    w = .06
    for s, (a0, a1, b0, b1) in enumerate(((x0, x1, z0, z0+w), (x0, x1, z1-w, z1),
                                          (x0, x0+w, z0+w, z1-w), (x1-w, x1, z0+w, z1-w))):
        parts.append(_flat(f'base-{k}-grout-{s}', [(a0, b0), (a1, b0), (a1, b1), (a0, b1)],
                           Y_GROUT, 'concrete_dark'))
    per_side = 2 if rng.random() < .5 else 3
    bolts = []
    for zi in (z0 + .22, z1 - .22):
        for t in range(per_side):
            bolts.append((x0 + .22 + (x1 - x0 - .44) * t / (per_side - 1), zi))
    for j, (bx, bz) in enumerate(bolts):
        parts.append(_flat(f'base-{k}-rust-{j}', _octagon(rng, bx + rng.uniform(-.03, .03),
                                                          bz + rng.uniform(-.03, .03), .09, .3),
                           Y_RUST, 'rust'))
        parts.append(_flat(f'base-{k}-bolt-{j}', _octagon(rng, bx, bz, .028, .05), Y_BOLT, 'rust_dark'))
    ox_, oz_ = rng.uniform(x0 + .4, x1 - .4), rng.uniform(z0 + .3, z1 - .3)
    parts.append(_flat(f'base-{k}-oil', _octagon(rng, ox_, oz_, rng.uniform(.45, .8), .35),
                       Y_OIL, 'asphalt_wet'))
    return parts


def _walk(rng, start, heading, steps, bounds, turn=.6, reach=(.3, .85)):
    lo_x, hi_x, lo_z, hi_z = bounds
    pts = [start]
    for _ in range(steps):
        heading += rng.uniform(-turn, turn)
        step = rng.uniform(*reach)
        nxt = (pts[-1][0] + math.cos(heading)*step, pts[-1][1] + math.sin(heading)*step)
        if not (lo_x < nxt[0] < hi_x and lo_z < nxt[1] < hi_z):
            break
        pts.append(nxt)
    return pts


def _cracks(layout, features, ox, oz) -> list[MeshData]:
    """Branching slab cracks (slum02): long main runs with forked side cracks."""
    from .surface_detail import _crack
    rng = _rng(layout, 'cracks')
    plaza = layout.plaza
    avoid = [(r, .15) for r in features['pits']] + [(r, .1) for r in features['bases']]
    bounds = (plaza.x_min + .5, plaza.x_max - .5, plaza.z_min + .5, 13.6)

    def blocked(pts):
        return any(_hit((p[0] - .05, p[0] + .05, p[1] - .05, p[1] + .05), r, pad)
                   for p in pts for r, pad in avoid)

    def strip(name, pts, width, level):
        y = Y_CRACK - .0004 + .0001 * level
        crack = _crack(name, [(px - ox, pz - oz) for px, pz in pts], y, width, 'concrete_dark')
        # Align with the inlaid cells' up-facing winding.
        return _up(crack.name, crack.vertices, crack.faces, crack.material)
    parts = []
    mains = 0
    for _ in range(600):
        if mains >= 30:
            break
        heading = rng.uniform(0, math.tau)
        pts = _walk(rng, (rng.uniform(*bounds[:2]), rng.uniform(*bounds[2:])), heading,
                    rng.randint(8, 16), bounds)
        if len(pts) < 5 or blocked(pts):
            continue
        width = rng.uniform(.05, .09)
        parts.append(strip(f'crack-{mains:02d}', pts, width, mains % 5))
        for b in range(rng.randint(1, 3)):
            k = rng.randrange(1, len(pts) - 1)
            ax, az = pts[k-1]; bx, bz = pts[k+1]
            fork = math.atan2(bz - az, bx - ax) + rng.choice((-1, 1)) * rng.uniform(.5, 1.2)
            branch = _walk(rng, pts[k], fork, rng.randint(3, 7), bounds, .5, (.25, .6))
            if len(branch) >= 3 and not blocked(branch):
                parts.append(strip(f'crack-{mains:02d}-b{b}', branch, width * rng.uniform(.5, .7),
                                   (mains + b + 1) % 5))
        mains += 1
    return parts


def _tones(layout, features, ox, oz) -> list[MeshData]:
    """Broad, non-overlapping dirt/damp/oil/patch blotches: the slab's colour unevenness."""
    rng = _rng(layout, 'tones')
    plaza = layout.plaza
    avoid = [(r, .3) for r in features['pits']] + [(r, .2) for r in features['bases']]
    placed, parts = [], []
    for _ in range(3000):
        if len(parts) >= 34:
            break
        r = rng.uniform(1.0, 3.2)
        reach = r * TONE_REACH
        x = rng.uniform(plaza.x_min + reach + .3, plaza.x_max - reach - .3)
        z = rng.uniform(plaza.z_min + reach + .3, 13.4 - reach)
        box_ = (x - reach, x + reach, z - reach, z + reach)
        # Same-level patches must never overlap (z-fighting), so space by the full reach.
        if (any(_hit(box_, rect, pad) for rect, pad in avoid) or
                any(math.dist((x, z), (px, pz)) < (r + pr) * TONE_REACH + .1 for px, pz, pr in placed)):
            continue
        placed.append((x, z, r))
        phase = rng.uniform(0, math.tau)
        stretch = rng.uniform(.55, 1.0)
        # Ragged, lobed outline (two low-frequency lobes plus jitter), convex-safe fan.
        lobe, lobe_phase = rng.uniform(.1, .25), rng.uniform(0, math.tau)
        outline = []
        for k in range(16):
            a = math.tau * k / 16
            rr = r * (1 + lobe * math.sin(2*a + lobe_phase)) * rng.uniform(.85, 1.12)
            outline.append((x - ox + math.cos(phase + a) * rr,
                            z - oz + math.sin(phase + a) * rr * stretch))
        # Star-shaped about its centre: a triangle fan stays valid for a lobed outline.
        verts = [(x - ox, Y_TONE, z - oz)] + [(vx, Y_TONE, vz) for vx, vz in outline]
        fan = [(0, k + 1, (k + 1) % 16 + 1) for k in range(16)]
        parts.append(_up(f'stain-{len(parts):02d}', verts, fan,
                         TONE_MATERIALS[len(parts) % len(TONE_MATERIALS)]))
    return parts


def _damp(layout, wall, ox, oz) -> list[MeshData]:
    """Damp, dirty margins along the slab edges and at the foot of the north wall."""
    rng = _rng(layout, 'damp')
    plaza = layout.plaza
    foot = wall.origin[2] - wall.size[2]/2
    edges = (('x', plaza.x_min, 1, plaza.z_min + 1.8, foot - 1.8),
             ('x', plaza.x_max, -1, plaza.z_min + 1.8, foot - 1.8),
             ('z', plaza.z_min, 1, plaza.x_min + 1.8, plaza.x_max - 1.8),
             ('z', foot, -1, wall.origin[0] - wall.size[0]/2 + .5, wall.origin[0] + wall.size[0]/2 - .5))
    parts = []
    for axis, edge, sign, lo, hi in edges:
        t = lo + rng.uniform(0, .8)
        while t < hi - 1.2:
            length = min(rng.uniform(1.8, 4.2), hi - t)
            n = 6
            inner = [(edge, t + length*k/n) for k in range(n+1)]
            outer = [(edge + sign*(.25 + rng.uniform(.3, 1.3) * math.sin(math.pi*(k+.5)/(n+1))),
                      t + length*k/n) for k in range(n+1)]
            if axis == 'z':
                inner = [(b, a) for a, b in inner]
                outer = [(b, a) for a, b in outer]
            verts, faces = [], []
            for (ix, iz), (px, pz) in zip(inner, outer):
                verts += [(ix - ox, Y_DAMP, iz - oz), (px - ox, Y_DAMP, pz - oz)]
            faces = [(2*k, 2*k+2, 2*k+3, 2*k+1) for k in range(n)]
            parts.append(_up(f'damp-{len(parts):02d}', verts, faces,
                             'mud' if rng.random() < .7 else 'asphalt_wet'))
            t += length + rng.uniform(.4, 2.2)
    return parts


def _weathered_floor(layout: Layout, floor, wall) -> list[MeshData]:
    """Full stage: slum02-style worn slab, flush (<=Y_BOLT) except shallow pits."""
    ox, _, oz = floor.origin
    base = box('walkable-slab', (0, -.1, 0), floor.size, 'factory_floor')
    parts = [mesh('understructure', base.vertices,
                  [face for k, face in enumerate(base.faces) if k != 4], 'factory_floor')]
    features = floor_features(layout)
    in_pit = {(i + a, j + b) for i, j, ni, nj in features['pit_cells']
              for a in range(ni) for b in range(nj)}
    for i in range(20):
        for j in range(15):
            if (i, j) in in_pit:
                continue
            x0, z0 = layout.plaza.x_min + i*2 - ox, layout.plaza.z_min + j*2 - oz
            parts.append(mesh('inlaid-floor', [(x0,0,z0+2), (x0+2,0,z0+2), (x0+2,0,z0), (x0,0,z0)],
                              [(0,1,2,3)], SPECIAL_CELLS.get((i, j), 'factory_floor')))
    rng = _rng(layout, 'pit-shape')
    for k, (rect, (_, _, ni, nj)) in enumerate(zip(features['pits'], features['pit_cells'])):
        parts.extend(_pit(k, rect, ni, nj, rng, ox, oz))
    rng = _rng(layout, 'base-shape')
    for k, rect in enumerate(features['bases']):
        parts.extend(_base(k, rect, rng, ox, oz))
    parts.extend(_tones(layout, features, ox, oz))
    parts.extend(_cracks(layout, features, ox, oz))
    parts.extend(_damp(layout, wall, ox, oz))
    return parts


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    floor = next(p for p in layout.placements if p.key == 'factory-floor' and p.sector == sector)
    wall = next(p for p in layout.placements if p.key == 'north-wall' and p.sector == sector)
    if wall.params['face'] != 'south':
        raise ValueError('graffiti wall must face south')
    base = box('walkable-slab', (0, -.1, 0), floor.size, 'factory_floor')
    # Replace the top face with exactly coplanar, inlaid oil/scorch cells. There
    # are no raised decals, holes or steps anywhere in the continuous clear area.
    parts_floor = [mesh('understructure', base.vertices,
                        [face for k, face in enumerate(base.faces) if k != 4], 'factory_floor')]
    for i in range(20):
        for j in range(15):
            x0, z0 = layout.plaza.x_min + i*2, layout.plaza.z_min + j*2
            mat = ('asphalt_wet' if (i,j) in {(3,3), (13,4), (17,11), (7,12)} else
                   'concrete_dark' if (i,j) in {(4,3), (14,4), (10,9), (7,11)} else
                   'factory_floor')
            parts_floor.append(mesh('inlaid-floor', [(x0,0,z0+2), (x0+2,0,z0+2),
                                                      (x0+2,0,z0), (x0,0,z0)],
                                    [(0,1,2,3)], mat))
    if _full_stage(layout):
        # Task 12: cracks, shallow pits, machine-base traces and damp margins.
        parts_floor = _weathered_floor(layout, floor, wall)
    slab = Assembly('floor', floor.key, sector, floor.origin, parts_floor,
                    {'placement_key': floor.key})
    # A single independently editable wall mesh with an unbroken letter area, broken
    # crown, heavy exterior piers, construction seams and rusty rebar at the edges.
    parts = [box('wall-main', (0, 4.1, 0), (wall.size[0], 8.2, wall.size[2]), 'concrete_stained')]
    for height in (2.5, 6.7):
        parts.append(box('pour-seam', (0, height, -.407), (34.7, .047, .012), 'concrete_dark'))
    for x in (-15, -9, 9, 15):
        parts.append(box('formwork-tie', (x, 6.46, -.414), (.09, .09, .028), 'rust_dark'))
    for x in (-17.4, 17.4):
        parts.append(box('pier', (x, 4.25, -.22), (1.0, 8.5, .45), 'concrete_dark'))
        for offset in (-.25, .25):
            parts.append(tube('exposed-rebar', [(x+offset, 8.1, .08),
                                              (x+offset+.08, 9.35, .08)], .055, 6, 'rust'))
    for x, height in ((-14, .65), (-8, 1.15), (1, .9), (9, 1.45), (15, .55)):
        parts.append(box('broken-crown', (x, 8.2 + height/2, .12),
                         (3.2, height, .55), 'concrete_raw'))
    return [slab, Assembly('north-wall', wall.key, sector, wall.origin, parts,
                           {'placement_key': wall.key})]


def add_plaza(bpy, layout, materials, source_collection, export_collection):
    from .gn_scatter import add_scatter
    from .graffiti import add_graffiti
    rubble, rubble_report = add_scatter(bpy, layout, materials, source_collection, export_collection)
    paint, paint_report = add_graffiti(bpy, layout, materials, export_collection)
    return rubble + paint, {
        'objects': rubble_report['objects'] + paint_report['objects'],
        'uv_issues': rubble_report.get('uv_issues', []) + paint_report.get('uv_issues', []),
        'errors': rubble_report['errors'] + paint_report['errors'],
        'rubble_evaluated_bounds': rubble_report['rubble_evaluated_bounds'],
    }
