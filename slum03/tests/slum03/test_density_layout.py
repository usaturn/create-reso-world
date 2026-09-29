"""Gate A: catch sparse, concentrated, colliding and anchor-changing layouts."""
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from modeling.slum03.density_model import TARGET_COUNTS, REPRESENTATIVE_KEYS
from modeling.slum03.density_layout import build_density_layout
from modeling.slum03.density_metrics import validate_density
from modeling.slum03.layout import read_layout, write_layout

BASE = Path('artifacts/slum03/finalfix-m-20260928T0511/layout.json')


def full_layout():
    return build_density_layout(read_layout(BASE), 'full')


def codes(layout):
    return {issue.code for issue in validate_density(layout, {}, 'blockout')}


def test_full_has_exact_97_major_uses_and_four_districts():
    full = full_layout()
    assert Counter(p.kind for p in full.placements if p.kind in TARGET_COUNTS) == TARGET_COUNTS
    assert len(full.density.zones) == 4
    assert not codes(full)
    assert Counter(p.params['density_zone'] for p in full.placements
                   if p.key.startswith('density-') and p.kind in TARGET_COUNTS)['east'] >= 10


def test_representative_preserves_all_existing_poses_and_only_three_v2():
    base = read_layout(BASE)
    rep = build_density_layout(base, 'representative')
    original = {p.key: p for p in base.placements}
    assert {p.key for p in rep.placements} == set(original)
    assert all((p.origin, p.size, p.yaw_deg) ==
               (original[p.key].origin, original[p.key].size, original[p.key].yaw_deg)
               for p in rep.placements)
    assert {p.key for p in rep.placements if p.params.get('detail_profile') == 'v2'} == set(REPRESENTATIVE_KEYS)
    assert rep.density.selected_keys == REPRESENTATIVE_KEYS
    assert codes(rep) == set()


def test_blockout_and_full_share_poses_and_roundtrip(tmp_path):
    base = read_layout(BASE)
    block = build_density_layout(base, 'blockout')
    full = build_density_layout(base, 'full')
    full_poses = {p.key: (p.origin, p.size, p.yaw_deg) for p in full.placements}
    assert {p.key: (p.origin, p.size, p.yaw_deg) for p in block.placements} == {
        key: full_poses[key] for key in {p.key for p in block.placements}}
    # Task 8 only adds concrete overhead support routes to the full Layout.
    assert {p.kind for p in full.placements
            if p.key not in {q.key for q in block.placements}} == {'overhead'}
    for stage, layout in [('blockout', block), ('full', full),
                          ('representative', build_density_layout(base, 'representative'))]:
        path = tmp_path / (stage + '.json')
        write_layout(layout, path)
        assert read_layout(path) == layout


def test_sparse_baseline_is_not_full():
    base = read_layout(BASE)
    assert 'DENSITY_COUNT' in codes(replace(base, density=full_layout().density))


def test_missing_zone_and_duplicate_pose_fail_even_with_97_keys():
    full = full_layout()
    a, b = [p for p in full.placements if p.key.startswith('density-') and p.kind == 'ruin'][:2]
    moved = replace(a, origin=b.origin, params={**a.params, 'density_zone': b.params['density_zone']})
    broken = replace(full, placements=tuple(moved if p.key == a.key else p for p in full.placements))
    assert 'DENSITY_OVERLAP' in codes(broken)
    concentrated = replace(full, placements=tuple(replace(p, params={**p.params, 'density_zone': 'northwest'})
                    if p.key.startswith('density-') and p.kind in TARGET_COUNTS else p for p in full.placements))
    assert 'DENSITY_ZONE' in codes(concentrated)


def test_background_cannot_replace_a_missing_use():
    full = full_layout()
    p = next(p for p in full.placements if p.key.startswith('density-') and p.kind == 'stall')
    altered = replace(full, placements=tuple(replace(p, domain='background') if q.key == p.key else q
                                      for q in full.placements))
    assert 'DENSITY_COUNT' in codes(altered)


def test_clearance_and_yarol_east_entrance_blockers():
    full = full_layout()
    p = next(p for p in full.placements if p.key.startswith('density-') and p.kind == 'shack')
    for origin, expected in [((0, 0, 0), 'CLEARANCE_INTRUSION'),
                             ((-9, 0, -1), 'CLEARANCE_INTRUSION'),
                             ((58, 0, 47), 'YAROL_ENTRANCE')]:
        bad = replace(full, placements=tuple(replace(p, origin=origin) if q.key == p.key else q
                                             for q in full.placements))
        assert expected in codes(bad)


def test_unattached_intersection_cannot_be_excused_by_unrelated_parent():
    full = full_layout()
    a, b = [p for p in full.placements if p.key.startswith('density-') and p.kind == 'ruin'][:2]
    child = replace(a, origin=b.origin, params={**a.params, 'attachment': {
        'parent_key': 'yarol', 'contact_min': [0, 0, 0], 'contact_max': [0, 0, 0],
        'reason': 'unrelated'}})
    altered = replace(full, placements=tuple(child if p.key == a.key else p for p in full.placements))
    assert 'DENSITY_OVERLAP' in codes(altered)


def test_attachment_allows_only_declared_contact_overlap():
    from modeling.slum03.spatial import placement_bounds
    full = full_layout()
    a, b = [p for p in full.placements if p.key.startswith('density-') and p.kind == 'ruin'][:2]
    parent = placement_bounds(b)
    child = replace(a, origin=(parent.maximum[0] + a.size[0]/2 - .25, 0,
                               (parent.minimum[2]+parent.maximum[2])/2))
    x0, x1 = parent.maximum[0]-.25, parent.maximum[0]
    contact = {'parent_key': b.key, 'contact_min': [x0, 0, parent.minimum[2]],
               'contact_max': [x1, min(a.size[1], b.size[1]), parent.maximum[2]],
               'reason': 'bolted to wall'}
    child = replace(child, params={**child.params, 'attachment': contact})
    altered = replace(full, placements=tuple(child if p.key == a.key else p for p in full.placements))
    # Other buildings can be hit by the relocated child; only the b overlap
    # may be suppressed, not any unrelated intersection.
    assert not any(i.code == 'DENSITY_OVERLAP' and i.object_key == child.key and b.key in i.message
                   for i in validate_density(altered, {}, 'blockout'))
    deeper = replace(child, origin=(child.origin[0]-.25, 0, child.origin[2]))
    altered = replace(full, placements=tuple(deeper if p.key == a.key else p for p in full.placements))
    assert any(i.code == 'DENSITY_OVERLAP' and i.object_key == child.key and b.key in i.message
               for i in validate_density(altered, {}, 'blockout'))


def test_both_market_edge_storefronts_are_southeast_and_link_to_east_alley():
    full = full_layout()
    shops = [p for p in full.placements if p.key.startswith('density-market-nightlife-')]
    assert len(shops) == 2
    assert all(7 <= p.origin[0] <= 16 and -60 < p.origin[2] <= -42 for p in shops)
    east = next(p for p in full.placements if p.key == 'density-east-nightlife-01')
    assert any(0 < east.origin[0] - p.origin[0] <= 10 and
               abs(east.origin[2] - p.origin[2]) <= 5 for p in shops)


def test_canonical_variants_drive_representative_and_full_without_touching_other_legacy_metadata():
    base = read_layout(BASE)
    canon = {'ruin-west': 'slab_bay', 'shack-row': 'corrugated', 'market-west': 'electronics'}
    for stage in ('representative', 'blockout', 'full'):
        layout = build_density_layout(base, stage)
        originals = {p.key: p for p in base.placements}
        actual = {p.key: p for p in layout.placements}
        assert {key: actual[key].params['variant'] for key in canon} == canon
        if stage != 'full':
            assert all(actual[p.key] == p for p in base.placements if p.key not in canon)
        else:
            # Task 8 remodels every other existing major use (not Yarol) in place:
            # pose/sector/kind and original parameters are retained, v2 is added.
            for p in base.placements:
                if p.key in canon:
                    continue
                q = actual[p.key]
                assert (q.origin, q.size, q.yaw_deg, q.sector, q.kind, q.domain) == (
                    p.origin, p.size, p.yaw_deg, p.sector, p.kind, p.domain)
                assert {k: q.params[k] for k in p.params} == p.params
                if p.kind in ('ruin', 'shack', 'stall', 'nightlife'):
                    assert q.params['detail_profile'] == 'v2' and q.params['density_zone']
                else:
                    assert q == p
        additions = [p for p in layout.placements if p.key.startswith('density-')]
        expected = {'ruin': {'slab_bay', 'broken_corner', 'service_core', 'stepped_shell',
                             'exposed_frame', 'patched_facade'},
                    'shack': {'corrugated', 'plywood', 'tarp', 'pallet'},
                    'stall': {'electronics', 'tools', 'prosthetics', 'reclaimed_equipment'}}
        for kind, names in expected.items():
            assert {p.params['variant'] for p in additions if p.kind == kind} == (
                set() if stage == 'representative' else names)
        if stage == 'full':
            assert {p.kind for p in additions} - set(expected) == {'nightlife', 'overhead'}


def _resolve_selected_key(key, baseline_names):
    """Classes a key can belong to; candidate_scope resolves only class 'baseline'."""
    from modeling.slum03.density_layout import NEW_KEY_PREFIXES
    from modeling.slum03.density_model import SCATTER_PREFIXES
    classes = []
    if baseline_names.count(key) == 1:
        classes.append('baseline')
    if any(key.startswith(prefix) for prefix in NEW_KEY_PREFIXES) and key not in baseline_names:
        classes.append('new')
    if key in SCATTER_PREFIXES:
        classes.append('scatter')
    return classes


def test_full_selected_keys_resolve_to_exactly_one_class(legacy_manifest):
    import json
    from modeling.slum03.candidate_scope import nodes
    from modeling.slum03.density_model import SCATTER_PREFIXES, TARGET_COUNTS
    names = [node['slot'].get('name') for node, _ in nodes(legacy_manifest).values()]
    saved = read_layout(Path('content/slum03/density-full-layout.json'))
    keys = saved.density.selected_keys
    result = {key: _resolve_selected_key(key, names) for key in keys}
    assert all(len(classes) == 1 for classes in result.values()), {k: c for k, c in result.items() if len(c) != 1}
    counts = Counter(c[0] for c in result.values())
    # 11 existing Slots (10 uses + overhead-west) + foundation, 86 added uses + 12 routes, 4 sides.
    assert counts == {'baseline': 12, 'new': 86 + 12, 'scatter': 4}
    assert {k for k, c in result.items() if c == ['baseline']} >= {'district-foundation', 'overhead-west'}
    # Scatter keys cover all four sides and every baseline rubble pile has an owner key.
    assert set(SCATTER_PREFIXES) == {f'plaza-rubble-{side}' for side in ('west', 'east', 'north', 'south')}
    assert set(SCATTER_PREFIXES) <= set(keys)
    piles = [n for n in names if n and n.startswith('plaza-rubble-')]
    assert piles and all(any(n.startswith(prefix + '-') for prefix in SCATTER_PREFIXES) for n in piles)
    # Placement keys of the pre-fix selection that have no baseline Slot are gone.
    assert 'district-ground' not in keys
    # Nothing selected may be Yarol, and no key repeats.
    assert 'yarol' not in keys and len(keys) == len(set(keys))
    assert json.loads(json.dumps(list(keys))) == list(keys)


def test_selected_key_classifier_rejects_the_old_unresolvable_key(legacy_manifest):
    from modeling.slum03.candidate_scope import nodes
    names = [node['slot'].get('name') for node, _ in nodes(legacy_manifest).values()]
    assert _resolve_selected_key('district-ground', names) == []      # old key: no Slot
    assert _resolve_selected_key('plaza-rubble-north-3-9', names) == ['baseline']
    assert _resolve_selected_key('plaza-rubble-nowhere', names) == []
