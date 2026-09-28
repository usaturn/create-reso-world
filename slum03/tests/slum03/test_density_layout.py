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
    assert {p.key: (p.origin, p.size, p.yaw_deg) for p in block.placements} == {
        p.key: (p.origin, p.size, p.yaw_deg) for p in full.placements}
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
