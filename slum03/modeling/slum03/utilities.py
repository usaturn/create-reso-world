"""Per-use wall equipment and household traces joined into their owning Assembly.

All parts are authored in the owner's foot frame before yaw (+Z is the street
face), exactly like the architecture/market kits that join them. Every piece is
mounted on a named surface of that kit (wall face, cladding, frame member or
floor) and stays inside the owner's placement envelope. Small offsets come from
the shared per-owner/channel seed so build order never reshuffles them.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from .density_model import stable_seed
from .detail_evidence import detail_groups
from .geometry import Assembly, MeshData, box, tube
from .types import Layout, Placement

UTILITY_KINDS = ('ruin', 'shack', 'stall', 'nightlife')


def district_kit(p: Placement) -> bool:
    """Remodelled district uses; Gate B anchors keep their approved kit unchanged."""
    return (p.kind in UTILITY_KINDS and p.params.get('detail_profile') == 'v2'
            and p.params.get('cluster') not in (None, 'anchor'))


def _run(name: str, points, radius: float, sides: int, material: str) -> list[MeshData]:
    """A bent cable/pipe as straight tube pieces: no twisted quads at 3D bends."""
    return [tube(name, [a, b], radius, sides, material) for a, b in zip(points, points[1:])]


def _jitter(seed: int, key: str, channel: str, span: float) -> float:
    return (stable_seed(seed, key, channel) / (2**256 - 1) - .5) * span


def _ruin(p: Placement, seed: int) -> list[MeshData]:
    # Mounted on the recessed-window front wall (outer face f) of detailed_ruin.
    w, h, d = p.size
    f = d/2 - .85 + .325
    xa = -w/2 + 1.45 + _jitter(seed, p.key, 'utility-ac', .12)
    ya = 2.1
    xj = -w/2 + 2.35
    xm = w/2 - 1.12          # existing meter bracket of detailed_ruin
    cy = min(4.45, h - 1.3)  # above the window head and spandrel
    xg = -w/2 + 1.18
    return [
        box('ac-bracket', (xa-.3, ya-.33, f+.2), (.06, .06, .44), 'steel_dark'),
        box('ac-bracket', (xa+.3, ya-.33, f+.2), (.06, .06, .44), 'steel_dark'),
        box('ac-unit', (xa, ya, f+.22), (.84, .6, .4), 'steel_bare'),
        tube('ac-fan-guard', [(xa+.12, ya, f+.42), (xa+.12, ya, f+.445)], .21, 12, 'steel_dark'),
        tube('condensate-drain', [(xa+.34, ya-.3, f+.3), (xa+.34, .06, f+.3)], .022, 6, 'rubber'),
        box('junction-box', (xj, 1.6, f+.1), (.42, .55, .2), 'paint_teal_faded'),
        tube('service-conduit', [(xj, 1.875, f+.2), (xj, cy, f+.2), (xm, cy, f+.2),
                                 (xm, 2.24, f+.2)], .035, 6, 'steel_dark', ref=(0., 0., 1.)),
        *[box('conduit-standoff', (x, cy, f+.1), (.08, .08, .2), 'steel_bare')
          for x in (xj, (xj+xm)/2, xm)],
        tube('gas-cylinder', [(xg, .02, f+.25), (xg, 1.25, f+.25)], .14, 10, 'rust'),
        box('cylinder-strap', (xg, .9, f+.05), (.34, .05, .14), 'steel_dark'),
    ]


def _shack(p: Placement, seed: int) -> list[MeshData]:
    # Meter and service drop on the right cladding; rain bucket under the downspout.
    w, h, d = p.size
    z = -.3 + _jitter(seed, p.key, 'utility-meter', .2)
    x = w/2 - .22
    return [
        box('meter-box', (w/2-.27, 1.7, z), (.2, .4, .3), 'paint_teal_faded'),
        tube('service-drop', [(x, 1.9, z), (x, h-1.45, z), (x, h-1.45, -d/2+.3)],
             .02, 6, 'rubber', ref=(1., 0., 0.)),
        *[box('cable-clip', (w/2-.28, y, z), (.18, .05, .06), 'steel_dark')
          for y in (2.5, h-1.6)],
        # Beyond the floor lip and front post; an elbow turns the downspout into it.
        tube('spout-elbow', [(w/2-.37, .45, d/2-.35), (w/2-.15, .45, d/2-.14)], .03, 6, 'steel_dark'),
        tube('rain-bucket', [(w/2-.15, .02, d/2-.14), (w/2-.15, .36, d/2-.14)], .12, 10, 'plastic_crate'),
    ]


def _stall(p: Placement, seed: int) -> list[MeshData]:
    # Battery on the under-counter floor feeding a work lamp on the front crossbar.
    w, _, d = p.size
    shelf_z = -d/2 + .82
    rear_z = -d/2 + .48
    support_x = (w-.6)/2 - .025
    front = d/2 - .24
    bx = (w-.7)/2 - .2
    lx = .35 + _jitter(seed, p.key, 'utility-lamp', .16)
    return [
        box('battery-box', (bx, .31, shelf_z), (.3, .28, .3), 'steel_dark'),
        *_run('power-lead', [(bx, .45, shelf_z), (support_x+.07, .5, rear_z+.07),
                             (support_x+.07, 2.40, rear_z+.07), (lx, 2.40, front)],
              .02, 6, 'rubber'),
        tube('lamp-cord', [(lx, 2.40, front), (lx, 2.24, front)], .012, 6, 'rubber'),
        box('lamp-shade', (lx, 2.2, front), (.24, .1, .24), 'steel_dark'),
        box('lamp-bulb', (lx, 2.12, front), (.1, .07, .1), 'warm_bulb'),
    ]


def _nightlife(p: Placement, seed: int) -> list[MeshData]:
    """Wall equipment differs per storefront system; all of it is fixed to the facade."""
    w, h, d = p.size
    face = d/2 - .7 - .05          # upper cladding / fascia outer face
    shutter = min(p.params.get('shutter_width', 3.4), w - 2.2)
    xa = w/2 - 1.2
    xr = -w/2 + .95
    xb = (shutter/2 + w/2 - .55)/2  # right jamb centre
    lift = _jitter(seed, p.key, 'utility-ac', .2)
    variant = p.params.get('variant')

    def condenser(y):
        return [box('ac-bracket', (xa, y-.31, face+.19), (.7, .06, .4), 'steel_dark'),
                box('ac-unit', (xa, y, face+.2), (.8, .55, .36), 'steel_bare'),
                tube('ac-fan-guard', [(xa+.1, y, face+.38), (xa+.1, y, face+.4)], .19, 12, 'steel_dark')]

    parts = [box('breaker-box', (xb, 1.6, face+.14), (.35, .45, .18), 'paint_teal_faded')]
    if variant == 'nightlife-2':
        # Kitchen exhaust: rectangular duct from a hood box up the upper facade.
        parts += [box('exhaust-hood', (xr+.1, 4.6, face+.2), (.6, .4, .4), 'steel_bare'),
                  box('exhaust-duct', (xr+.1, (4.8+h-.4)/2, face+.2), (.36, h-.4-4.8, .36), 'steel_bare'),
                  *[box('duct-strap', (xr+.1, y, face+.09), (.44, .06, .18), 'steel_dark')
                    for y in (5.6, h-1.0)],
                  *[tube('gas-cylinder', [(-xb+dx, .02, face+.35), (-xb+dx, 1.05, face+.35)], .13, 10, 'rust')
                    for dx in (-.16, .16)]]
    elif variant == 'nightlife-3':
        # One condenser, a signal dish and a bundled cable run to the blade sign.
        parts += condenser(5.6 + lift)
        parts += [box('dish-arm', (xa, h-1.4, face+.15), (.08, .08, .3), 'steel_dark'),
                  tube('signal-dish', [(xa, h-1.4, face+.3), (xa, h-1.4, face+.36)], .32, 12, 'steel_bare'),
                  # Runs up the jamb behind the sign line, then over the fascia.
                  *_run('cable-bundle', [(xb, 1.83, face+.1), (xb, 2.75, face+.25), (xb, 4.45, face+.25),
                                         (-w/2+.9, 4.45, face+.25), (-w/2+.67, 4.45, face+.3)],
                        .04, 6, 'rubber')]
    elif variant == 'nightlife-4':
        # Rooftop-fed water tank on a wall cradle and an entry intercom / camera.
        parts += [box('tank-cradle', (xa, 4.85, face+.26), (1.0, .08, .5), 'steel_dark'),
                  tube('water-tank', [(xa-.45, 5.25, face+.34), (xa+.45, 5.25, face+.34)], .33, 12, 'plastic_crate'),
                  *_run('tank-feed', [(xa+.45, 5.25, face+.34), (xa+.6, 5.25, face+.1), (xa+.6, h-.5, face+.1)],
                        .03, 6, 'steel_dark'),
                  box('intercom', (-(shutter/2 + w/2 - .55)/2, 1.45, face+.1), (.2, .3, .1), 'steel_bare'),
                  box('camera', (-(shutter/2 + w/2 - .55)/2, 2.9, face+.16), (.14, .12, .22), 'steel_dark')]
    else:
        parts += condenser(5.0 + lift) + (condenser(6.3 + lift) if 6.6 + lift < h - .5 else [])
    parts += [tube('service-riser', [(xr, .3, face+.25), (xr, min(4.3, h-.5), face+.25)], .05, 8, 'steel_dark'),
              *[box('riser-clamp', (xr, y, face+.14), (.12, .08, .26), 'steel_bare') for y in (1.2, 3.9)]]
    return parts


def utility_parts(p: Placement, seed: int) -> list[MeshData]:
    """Equipment cluster for one owner, in its foot frame before yaw."""
    builders = {'ruin': _ruin, 'shack': _shack, 'stall': _stall, 'nightlife': _nightlife}
    if p.kind not in builders:
        raise ValueError(f'no utility kit for kind {p.kind}')
    return builders[p.kind](p, seed)


def household_parts(p: Placement, seed: int) -> list[MeshData]:
    """Interior living traces of a remodelled shack (bedroll, stool, drying cloth)."""
    if p.kind != 'shack':
        raise ValueError('household traces belong to shacks')
    w, _, d = p.size
    shift = _jitter(seed, p.key, 'household', .2)
    x = w/2 - .92
    return [
        box('bedroll', (x, .34, -d/2+1.15), (.8, .12, 1.3), 'cloth_red'),
        box('pillow', (x, .43, -d/2+.67), (.5, .08, .25), 'tarp_green'),
        box('stool-legs', (-.1+shift, .5, .15), (.26, .44, .26), 'pallet_wood'),
        box('stool-seat', (-.1+shift, .745, .15), (.34, .05, .34), 'pallet_wood'),
        box('cloth-hook', (-w/2+.5, 1.8, .35), (.08, .06, .06), 'steel_dark'),
        box('drying-cloth', (-w/2+.52, 1.45, .35), (.04, .62, .5), 'tarp_green'),
    ]


def cluster_coverage(layout: Layout, assemblies: list[Assembly]):
    """Measured utility/lived-in groups per (zone, cluster); never trusts counts in meta."""
    issues: list[str] = []
    by_name = defaultdict(list)
    for a in assemblies:
        by_name[a.name].append(a)
    coverage: dict[str, dict] = {}
    for p in layout.placements:
        if p.kind not in UTILITY_KINDS or p.params.get('detail_profile') != 'v2':
            continue
        cluster = f"{p.params.get('density_zone')}/{p.params.get('cluster')}"
        entry = coverage.setdefault(cluster, {'uses': 0, 'utility_groups': 0, 'lived_in_groups': 0})
        found = by_name.get(p.key, [])
        if len(found) != 1 or found[0].kind != p.kind:
            issues.append(f'{p.key}: use missing, duplicated or wrong kind')
            continue
        try:
            groups = detail_groups(found[0])
        except ValueError as exc:
            issues.append(f'{p.key}: invalid detail groups ({exc})')
            continue
        counts = Counter(g['category'] for g in groups)
        for category in ('utility', 'lived_in'):
            if not counts[category]:
                issues.append(f'{p.key}: no {category} group')
        entry['uses'] += 1
        entry['utility_groups'] += counts['utility']
        entry['lived_in_groups'] += counts['lived_in']
    for cluster, entry in coverage.items():
        if not entry['utility_groups'] or not entry['lived_in_groups']:
            issues.append(f'{cluster}: cluster lacks utility or lived-in detail')
    return coverage, issues
