"""Task 8 district rollout: every living cluster carries real equipment and traces.

Breaks caught: a partial fixture standing in for the whole district, empty or
self-declared groups, uses silently dropped or duplicated by kind dispatch,
utility parts floating outside their owner or intruding into protected 3 m air,
and Yarol drifting while its neighbours are remodelled.
"""
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from modeling.slum03.density_layout import build_density_layout
from modeling.slum03.density_model import TARGET_COUNTS
from modeling.slum03.detail_evidence import detail_groups
from modeling.slum03.geometry import Assembly, bounds
from modeling.slum03.layout import build_layout, read_layout
from modeling.slum03.materials import MATERIALS
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.spatial import placement_bounds, validate_clearance
from modeling.slum03.types import Bounds3

FULL = Path('content/slum03/density-full-layout.json')
BASE = Path('artifacts/slum03/finalfix-m-20260928T0511/layout.json')
BLOCK = Path('content/slum03/density-blockout-layout.json')
USE_SECTORS = ('ruins-west', 'ruins-north', 'ruins-east', 'shacks', 'market',
               'nightlife', 'yarol')


@pytest.fixture(scope='module')
def full():
    return read_layout(FULL)


@pytest.fixture(scope='module')
def uses(full):
    built = [a for sector in USE_SECTORS for a in sector_assemblies(full, sector)]
    names = [a.name for a in built]
    assert len(names) == len(set(names)), 'a use was generated twice'
    return {a.name: a for a in built}


def _root_bounds(assembly, part):
    lo, hi = bounds([part])
    return Bounds3(tuple(lo[i] + assembly.origin[i] for i in range(3)),
                   tuple(hi[i] + assembly.origin[i] for i in range(3)))


def test_saved_full_layout_is_the_generator_output():
    # The authored JSON may not drift from density_layout.py (single source).
    assert read_layout(FULL) == build_density_layout(read_layout(BASE), 'full')


def test_all_97_uses_dispatch_by_kind_without_loss_or_duplication(full, uses):
    majors = {p.key: p for p in full.placements
              if p.domain == 'district' and p.kind in TARGET_COUNTS}
    assert Counter(p.kind for p in majors.values()) == TARGET_COUNTS
    assert set(uses) == set(majors)
    assert all(uses[key].kind == p.kind and uses[key].sector == p.sector
               for key, p in majors.items())
    assert Counter(a.kind for a in uses.values()) == Counter(
        {'ruin': 32, 'shack': 28, 'stall': 28, 'nightlife': 8, 'yarol': 1})
    # Every remodelled use is v2 with a formal, geometry-backed variant.
    variants = {kind: {p.params['variant'] for p in majors.values() if p.kind == kind}
                for kind in ('ruin', 'shack', 'stall', 'nightlife')}
    assert variants['ruin'] == {'slab_bay', 'broken_corner', 'service_core', 'stepped_shell',
                                'exposed_frame', 'patched_facade'}
    assert variants['shack'] == {'corrugated', 'plywood', 'tarp', 'pallet'}
    assert variants['stall'] == {'electronics', 'tools', 'prosthetics', 'reclaimed_equipment'}
    assert len(variants['nightlife']) == 4
    assert all(p.params.get('detail_profile') == 'v2' for p in majors.values()
               if p.kind != 'yarol')
    assert all(uses[key].meta.get('variant') == p.params['variant']
               for key, p in majors.items() if p.kind != 'yarol')


def test_market_branch_and_east_shop_counts_hold(full):
    majors = [p for p in full.placements if p.domain == 'district' and p.kind in TARGET_COUNTS]
    stalls = Counter(p.params.get('density_zone') for p in majors if p.kind == 'stall')
    assert stalls['market'] == 20
    assert stalls['southwest'] + stalls['east'] == 8
    shops = [p for p in majors if p.kind == 'nightlife']
    assert sum(p.params.get('density_zone') == 'east' for p in shops) == 6
    southeast = [p for p in shops if p.params.get('density_zone') == 'market']
    assert len(southeast) == 2 and all(p.origin[0] > 0 and p.origin[2] < -42 for p in southeast)


def test_every_remodelled_use_has_real_utility_and_lived_in_groups(full, uses):
    from modeling.slum03.utilities import district_kit, utility_parts
    for key, a in uses.items():
        if a.kind == 'yarol':
            continue
        groups = detail_groups(a)  # rejects empty/invalid groups, measured from faces
        categories = Counter(g['category'] for g in groups)
        assert categories['utility'] >= 1 and categories['lived_in'] >= 1, key
        p = next(p for p in full.placements if p.key == key)
        if district_kit(p):
            # The shared per-use equipment is actually joined into this owner.
            names = {part.name for part in utility_parts(p, full.seed)}
            owned = {a.parts[i].name for g in a.meta['detail_groups']
                     if g['category'] == 'utility' for i in g['part_indices']}
            assert names and names <= owned, key
    # Anchors approved at Gate B keep their kit; everyone else joins the district kit.
    assert sum(district_kit(p) for p in full.placements) == 96 - 3


def test_each_living_cluster_has_utility_and_lived_in(full, uses):
    from modeling.slum03.utilities import cluster_coverage
    coverage, issues = cluster_coverage(full, list(uses.values()))
    assert not issues
    assert len(coverage) >= 20
    for cluster, entry in coverage.items():
        assert entry['utility_groups'] >= 1 and entry['lived_in_groups'] >= 1, cluster
        assert entry['uses'] >= 1


def test_coverage_rejects_empty_missing_or_claimed_groups(full, uses):
    from modeling.slum03.utilities import cluster_coverage
    key = next(k for k, a in uses.items() if a.kind == 'shack' and k.startswith('density-'))
    original = uses[key]
    cases = {
        'empty': [*original.meta['detail_groups'],
                  {'id': 'claimed-empty', 'category': 'utility', 'part_indices': []}],
        'missing-lived-in': [g for g in original.meta['detail_groups']
                             if g['category'] != 'lived_in'],
        'missing-utility': [g for g in original.meta['detail_groups']
                            if g['category'] != 'utility'],
    }
    for name, groups in cases.items():
        broken = Assembly(original.kind, original.name, original.sector, original.origin,
                          original.parts, {**original.meta, 'detail_groups': groups})
        others = [a for k, a in uses.items() if k != key]
        _, issues = cluster_coverage(full, others + [broken])
        assert any(key in issue for issue in issues), name
    # Dropping a use entirely must also be reported, not ignored.
    _, issues = cluster_coverage(full, [a for k, a in uses.items() if k != key])
    assert any(key in issue for issue in issues)


def test_utility_parts_are_mounted_inside_owner_and_off_protected_air(full, uses):
    from modeling.slum03.utilities import district_kit, utility_parts
    checked = 0
    for p in full.placements:
        if not district_kit(p):
            continue
        a = uses[p.key]
        allowed = placement_bounds(p)
        for part in a.parts:
            b = _root_bounds(a, part)
            assert all(allowed.minimum[i] - 1e-6 <= b.minimum[i] <= b.maximum[i]
                       <= allowed.maximum[i] + 1e-6 for i in range(3)), (p.key, part.name)
            assert not validate_clearance(full, {p.key: b}), (p.key, part.name)
            assert part.material in MATERIALS
        assert utility_parts(p, full.seed) == utility_parts(p, full.seed)
        checked += 1
    assert checked == 93


def test_utility_parts_depend_on_owner_not_iteration_order(full):
    from modeling.slum03.utilities import utility_parts
    shacks = [p for p in full.placements if p.key.startswith('density-') and p.kind == 'shack']
    a, b = shacks[:2]
    first = utility_parts(a, full.seed)
    assert utility_parts(replace(b, key=a.key, params={**b.params, 'variant': a.params['variant']},
                                 size=a.size), full.seed) == first
    assert utility_parts(a, full.seed + 1) != first  # small per-owner jitter
    with pytest.raises(ValueError, match='utility'):
        utility_parts(replace(a, kind='yarol'), full.seed)


def test_yarol_and_its_entrance_are_unchanged(full, uses):
    base = read_layout(BASE)
    old = next(p for p in base.placements if p.key == 'yarol')
    new = next(p for p in full.placements if p.key == 'yarol')
    assert new == old
    assert uses['yarol'] == sector_assemblies(base, 'yarol')[0]
    assert 'yarol' not in full.density.selected_keys


def test_full_selection_names_only_uses_overhead_periphery_and_surface(full):
    majors = {p.key for p in full.placements
              if p.domain == 'district' and p.kind in TARGET_COUNTS and p.kind != 'yarol'}
    overhead = {p.key for p in full.placements if p.kind == 'overhead'}
    assert set(full.density.selected_keys) == (
        majors | overhead | {'district-foundation', 'plaza-rubble-west', 'plaza-rubble-east',
                             'plaza-rubble-north', 'plaza-rubble-south',
                             'plaza-rubble-floor',  # Task 12: central floor debris family
                             'factory-floor'})  # Task 12: the weathered factory floor mesh
    assert len(full.density.selected_keys) == len(set(full.density.selected_keys))


def test_blockout_poses_and_routes_did_not_move(full):
    block = read_layout(BLOCK)
    poses = {p.key: (p.origin, p.size, p.yaw_deg, p.sector, p.kind) for p in full.placements}
    assert all(poses[p.key] == (p.origin, p.size, p.yaw_deg, p.sector, p.kind)
               for p in block.placements)
    assert {p.kind for p in full.placements if p.key not in poses.keys() & {
        q.key for q in block.placements}} == {'overhead'}
    assert full.routes == block.routes and full.clear == block.clear
    assert full.density.routes == block.density.routes
    assert full.density.branch_clearances == block.density.branch_clearances
    assert build_layout().routes == full.routes


def test_utility_parts_touch_the_kit_or_ground(full, uses):
    """Fixed offsets in _ruin/_shack/_stall/_nightlife may not leave floating equipment."""
    from modeling.slum03.utilities import district_kit, utility_parts

    def overlap(a, b):
        lo_a, hi_a = bounds([a]); lo_b, hi_b = bounds([b])
        return all(lo_a[i] <= hi_b[i] + .005 and lo_b[i] <= hi_a[i] + .005 for i in range(3))

    checked = 0
    for p in full.placements:
        if not district_kit(p) or p.kind == 'nightlife':  # storefront equipment: test_nightlife.py
            continue
        a = uses[p.key]
        indices = {i for g in a.meta['detail_groups'] if g['id'] == 'district-utility'
                   for i in g['part_indices']}
        assert len(indices) == len(utility_parts(p, full.seed)), p.key
        util = [a.parts[i] for i in sorted(indices)]
        kit = [part for i, part in enumerate(a.parts) if i not in indices]
        assert kit, p.key
        # Connected groups of equipment must reach the kit or the ground.
        seen: set[int] = set()
        for start in range(len(util)):
            if start in seen:
                continue
            group, stack = [], [start]
            seen.add(start)
            while stack:
                i = stack.pop(); group.append(i)
                for j in range(len(util)):
                    if j not in seen and overlap(util[i], util[j]):
                        seen.add(j); stack.append(j)
            grounded = any(bounds([util[i]])[0][1] <= .03 for i in group)
            mounted = any(overlap(util[i], k) for i in group for k in kit)
            assert grounded or mounted, (p.key, p.kind, [util[i].name for i in group])
        checked += 1
    assert checked == 93 - 8
