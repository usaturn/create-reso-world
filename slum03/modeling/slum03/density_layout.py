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
    return replace(baseline, placements=tuple(placed), density=config)


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
