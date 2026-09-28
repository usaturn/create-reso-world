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


def _intersects(a: RectXZ, b: RectXZ, margin=0.) -> bool:
    return (a.x_min < b.x_max + margin and a.x_max > b.x_min - margin and
            a.z_min < b.z_max + margin and a.z_max > b.z_min - margin)


def _footprint(p: Placement) -> RectXZ:
    b = placement_bounds(p)
    return RectXZ(b.minimum[0], b.maximum[0], b.minimum[2], b.maximum[2])


def _candidates(zone: DensityZone, kind: str):
    # 1 m lattice makes every generated coordinate stable across processes.
    # Market stalls use denser 5 m lanes; all other units have staggered rows.
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
    old = tuple(replace(p, params={**p.params, 'detail_profile': 'v2',
                                  'variant': 'representative', 'cluster': 'anchor'})
                if p.key in selected else p for p in baseline.placements)
    if stage == 'representative':
        return replace(baseline, placements=old, density=config)
    placed = list(old)
    solids = [_footprint(p) for p in old if p.domain == 'district' and p.kind not in IGNORE_SOLIDS]
    blocked = (*baseline.routes, baseline.clear, *BRANCHES,
               RectXZ(43, 59, 40, 54))  # Yarol lot, including east-facing entry
    for kind, quotas in ADDITIONS.items():
        for zone_name, count in quotas.items():
            zone = next(z for z in ZONES if z.key == zone_name)
            options = _candidates(zone, kind)
            # Spread candidates rather than fill one edge: order by distance to
            # already occupied sites (fixed, deterministic, no RNG consumption).
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
                    distance = min((x-(r.x_min+r.x_max)/2)**2 + (z-(r.z_min+r.z_max)/2)**2
                                   for r in solids)
                    candidates.append((distance, -abs(x), -abs(z), x, z, rect))
                if not candidates:
                    raise ValueError(f'cannot fit {kind} #{number+1}/{count} in {zone_name}; quota unchanged')
                _, _, _, x, z, rect = min(candidates, key=lambda c: (c[4], c[3]))
                key = f'density-{zone_name}-{kind}-{number+1:02d}'
                variant = f'{kind}-{number % (6 if kind == "ruin" else 4) + 1}'
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
