"""Deterministic Gate A blockout: fixed grid, explicit quotas and preserved anchors.

Coordinates are root-local metres (X east, Z north). The grids are *candidate*
footprints, not an invitation to silently reduce quota: exhaustion fails closed.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import replace
from pathlib import Path

from .density_model import REPRESENTATIVE_KEYS, TARGET_COUNTS
from .layout import read_layout, write_layout
from .spatial import placement_bounds
from .types import DensityConfig, DensityOpening, DensityRoute, DensityZone, Layout, Placement, RectXZ

ZONES = (
    DensityZone('northwest', RectXZ(-60, -20, 2, 60)),
    DensityZone('southwest', RectXZ(-60, -20, -60, -2)),
    DensityZone('market', RectXZ(-20, 20, -60, -16)),
    DensityZone('east', RectXZ(20, 60, -60, 40)),
)
ROUTES = (
    DensityRoute('northwest-lane', 'residential', RectXZ(-57, -54, 2, 58), ()),
    DensityRoute('southwest-lane', 'residential', RectXZ(-57, -54, -58, -2), ()),
    DensityRoute('market-spine', 'market', RectXZ(-1.5, 1.5, -60, -16),
                 (DensityOpening(RectXZ(-1.5, 1.5, -20, -16), 'plaza-entry'),)),
    DensityRoute('east-alley', 'alley', RectXZ(44, 47, -58, 35),
                 (DensityOpening(RectXZ(44, 47, -2, 2), 'east-forest-view'),)),
)
YAROL_ENTRY = RectXZ(57, 60, 43, 51)
# Baseline solids and secondary protected routes are retained, not moved.
BRANCHES = tuple(r.corridor for r in ROUTES) + (YAROL_ENTRY,)
# Counts here are ADDITIONS only. Existing 4/2/2/2/1 remain unchanged.
ADDITIONS = {
    'nightlife': {'market': 2, 'east': 4},
    'ruin': {'northwest': 5, 'southwest': 9, 'east': 14},
    'shack': {'northwest': 8, 'southwest': 9, 'east': 9},
    'stall': {'southwest': 4, 'market': 18, 'east': 4},
}
SIZES = {'ruin': (8., 12., 8.), 'shack': (4., 4., 4.),
         'stall': (3., 3., 4.), 'nightlife': (8., 8., 8.)}
IGNORE_SOLIDS = {'ground', 'floor', 'rubble', 'overhead', 'product-holo', 'info-ad', 'ribbon-ad'}
# Both southeast market shops lead directly towards the east alley, not the western market.
SOUTHEAST_SHOP_SITES = ((7., -55.), (16., -55.))
RUIN_VARIANTS = ('slab_bay', 'broken_corner', 'service_core', 'stepped_shell',
                 'exposed_frame', 'patched_facade')
SHACK_VARIANTS = ('corrugated', 'plywood', 'tarp', 'pallet')
STALL_VARIANTS = ('electronics', 'tools', 'prosthetics', 'reclaimed_equipment')
VARIANTS = {'ruin': RUIN_VARIANTS, 'shack': SHACK_VARIANTS, 'stall': STALL_VARIANTS}
REP_VARIANTS = dict(zip(REPRESENTATIVE_KEYS,
                        (RUIN_VARIANTS[0], SHACK_VARIANTS[0], STALL_VARIANTS[0])))
# Task 8 (full stage only): every other existing major use except Yarol is
# remodelled in place. Pose, sector and original parameters never change.
FULL_EXISTING = {
    'ruin-west-annex': ('northwest', 'service_core'),
    'ruin-north': ('northwest', 'stepped_shell'),
    'ruin-east': ('east', 'patched_facade'),
    'shack-west': ('southwest', 'tarp'),
    'market-east': ('market', 'tools'),
    'nightlife-east': ('east', 'nightlife-2'),
    'nightlife-velvet': ('east', 'nightlife-3'),
}
ANCHOR_ZONES = {'ruin-west': 'northwest', 'shack-row': 'southwest', 'market-west': 'market'}
# Concrete, independently supported overhead routes (full stage only). Each is
# a straight run between two ground-anchored poles in open space beside the
# buildings it serves; none crosses a protected 3 m route or the central air,
# so their complete envelope (poles included) stays off every walkway.
# key, zone, start (x, z), end (x, z), support height, route description
OVERHEAD_ROUTES = (
    ('northwest-01', 'northwest', (-44., 37.), (-44., 47.), 6.4, 'annex yard to north shacks'),
    ('northwest-02', 'northwest', (-52., 22.), (-40., 22.), 7.2, 'ruin-west / annex service gap'),
    ('northwest-03', 'northwest', (-33., 28.), (-21., 28.), 6.8, 'north shacks to ruin-north'),
    ('southwest-01', 'southwest', (-52., -50.), (-40., -50.), 6.2, 'south ruin rows'),
    ('southwest-02', 'southwest', (-38., -40.), (-26., -40.), 5.8, 'shack terrace feed'),
    ('southwest-03', 'southwest', (-44., -20.5), (-44., -12.), 6.0, 'west ruin court'),
    ('market-01', 'market', (-18., -54.), (-6., -54.), 5.6, 'south stall aisle'),
    ('market-02', 'market', (-18., -48.), (-6., -48.), 5.4, 'middle stall aisle'),
    ('market-03', 'market', (3., -43.), (12.5, -43.), 5.6, 'east stall court'),
    ('east-01', 'east', (31., -34.), (43., -34.), 6.0, 'lane back yards'),
    ('east-02', 'east', (48., -30.), (48., -18.), 6.6, 'alley-side ruins'),
    ('east-03', 'east', (26., 28.), (38., 28.), 6.4, 'ruin-east north yard'),
)
PERIPHERY_KEYS = ('plaza-rubble-west', 'plaza-rubble-east')
SURFACE_KEYS = ('district-ground',)


def _intersects(a: RectXZ, b: RectXZ, margin=0.) -> bool:
    return (a.x_min < b.x_max + margin and a.x_max > b.x_min - margin and
            a.z_min < b.z_max + margin and a.z_max > b.z_min - margin)


def _footprint(p: Placement) -> RectXZ:
    b = placement_bounds(p)
    return RectXZ(b.minimum[0], b.maximum[0], b.minimum[2], b.maximum[2])


def _candidates(zone: DensityZone, kind: str):
    # Stable 2 m candidate lattice; southwest shops use explicit sites instead.
    sx, _, sz = SIZES[kind]
    stride = 2
    xs = list(range(int(zone.bounds.x_min + sx/2 + 1),
                    int(zone.bounds.x_max - sx/2), stride))
    zs = list(range(int(zone.bounds.z_min + sz/2 + 1),
                    int(zone.bounds.z_max - sz/2), stride))
    return [(float(x), float(z)) for z in zs for x in xs]


def build_density_layout(baseline: Layout, stage: str, seed: int = 260927) -> Layout:
    if stage not in ('blockout', 'representative', 'full') or type(seed) is not int:
        raise ValueError('invalid density stage or seed')
    if baseline.seed != seed or baseline.density is not None:
        raise ValueError('expected unchanged baseline and matching seed')
    selected = REPRESENTATIVE_KEYS if stage == 'representative' else ()
    config = DensityConfig(stage, ZONES, ROUTES, BRANCHES, selected)
    old = tuple(replace(p, params={**p.params, 'variant': REP_VARIANTS[p.key],
                                  'cluster': 'anchor',
                                  **({'detail_profile': 'v2'} if stage != 'blockout' else {})})
                if p.key in REP_VARIANTS else p for p in baseline.placements)
    if stage == 'representative':
        return replace(baseline, placements=old, density=config)
    if stage == 'full':
        old = tuple(_remodel_existing(p) for p in old)
    placed = list(old)
    solids = [_footprint(p) for p in old if p.domain == 'district' and p.kind not in IGNORE_SOLIDS]
    blocked = (*baseline.routes, baseline.clear, *BRANCHES,
               RectXZ(43, 59, 40, 54))  # Yarol lot, including east-facing entry
    for kind, quotas in ADDITIONS.items():
        for zone_name, count in quotas.items():
            zone = next(z for z in ZONES if z.key == zone_name)
            options = (SOUTHEAST_SHOP_SITES if kind == 'nightlife' and zone_name == 'market'
                       else _candidates(zone, kind))
            # Stable row order; never drop quota when a site cannot be occupied.
            for number in range(count):
                candidates = []
                for x, z in options:
                    sx, sy, sz = SIZES[kind]
                    rect = RectXZ(x-sx/2, x+sx/2, z-sz/2, z+sz/2)
                    if any(_intersects(rect, other, .15) for other in (*solids, *blocked)):
                        continue
                    if any(_intersects(rect, other) for other in (baseline.plaza,)):
                        continue
                    if not (zone.bounds.x_min <= rect.x_min < rect.x_max <= zone.bounds.x_max and
                            zone.bounds.z_min <= rect.z_min < rect.z_max <= zone.bounds.z_max):
                        continue
                    candidates.append((x, z, rect))
                if not candidates:
                    raise ValueError(f'cannot fit {kind} #{number+1}/{count} in {zone_name}; quota unchanged')
                x, z, rect = min(candidates, key=lambda c: (c[1], c[0]))
                key = f'density-{zone_name}-{kind}-{number+1:02d}'
                variant = (VARIANTS[kind][number % len(VARIANTS[kind])] if kind in VARIANTS
                           else f'{kind}-{number % 4 + 1}')
                height = (6 if zone_name == 'east' else 12) if kind == 'ruin' else SIZES[kind][1]
                p = Placement(key, {'northwest': 'ruins-west', 'southwest': 'shacks',
                                    'market': 'market', 'east': 'nightlife'}[zone_name],
                              kind, (x, 0., z), (SIZES[kind][0], height, SIZES[kind][2]),
                              float((number % 4) * 90), 'district',
                              {'density_zone': zone_name, 'variant': variant,
                               'cluster': f'{zone_name}-row-{int(z)//10}',
                               **({'detail_profile': 'v2'} if stage == 'full' else {})})
                placed.append(p)
                solids.append(rect)
    actual = Counter(p.kind for p in placed if p.kind in TARGET_COUNTS and p.domain == 'district')
    if actual != TARGET_COUNTS:
        raise ValueError(f'cannot meet exact density quota: {actual}')
    if stage == 'full':
        placed.extend(_overhead_routes(solids, (*blocked, baseline.plaza)))
        selected = tuple(p.key for p in placed if p.domain == 'district' and (
            (p.kind in TARGET_COUNTS and p.kind != 'yarol') or p.kind == 'overhead' or
            p.key in PERIPHERY_KEYS or p.key in SURFACE_KEYS))
        config = replace(config, selected_keys=selected)
    return replace(baseline, placements=tuple(placed), density=config)


def _remodel_existing(p: Placement) -> Placement:
    if p.key in ANCHOR_ZONES:  # Gate B kit retained; the zone is recorded only.
        return replace(p, params={**p.params, 'density_zone': ANCHOR_ZONES[p.key]})
    if p.key not in FULL_EXISTING:
        return p
    zone, variant = FULL_EXISTING[p.key]
    return replace(p, params={**p.params, 'variant': variant, 'density_zone': zone,
                              'cluster': f'{zone}-row-{int(p.origin[2])//10}',
                              'detail_profile': 'v2'})


def _overhead_routes(solids, blocked) -> list[Placement]:
    """Fail closed if any authored route envelope touches a solid or protected air."""
    result = []
    for name, zone, (x0, z0), (x1, z1), height, route in OVERHEAD_ROUTES:
        along_x = z0 == z1
        if along_x == (x0 == x1) or height <= 3.5:
            raise ValueError(f'overhead route {name} must be one straight axis run above 3.5 m')
        length = abs(x1-x0) if along_x else abs(z1-z0)
        mx, mz = (x0+x1)/2, (z0+z1)/2
        p = Placement(f'density-overhead-{name}', 'overhead', 'overhead', (mx, height, mz),
                      (length+.9, height+.45, .9), 0. if along_x else 90., 'district',
                      {'local_y_min': -height, 'density_zone': zone,
                       'cluster': f'{zone}-row-{int(mz)//10}', 'route': route,
                       'supports': [[x0, height, z0], [x1, height, z1]]})
        rect = _footprint(p)
        zone_bounds = next(z for z in ZONES if z.key == zone).bounds
        if (any(_intersects(rect, other, .15) for other in (*solids, *blocked)) or
                not (zone_bounds.x_min <= rect.x_min < rect.x_max <= zone_bounds.x_max and
                     zone_bounds.z_min <= rect.z_min < rect.z_max <= zone_bounds.z_max)):
            raise ValueError(f'overhead route {name} intersects a solid, protected air or leaves {zone}')
        result.append(p)
        solids.append(rect)
    return result


def main():
    parser = argparse.ArgumentParser(description='Generate offline density layouts; never export/live')
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--stage', required=True, choices=('blockout', 'representative', 'full'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f'output exists: {args.output}')
    write_layout(build_density_layout(read_layout(args.base), args.stage), args.output)


if __name__ == '__main__':
    main()
