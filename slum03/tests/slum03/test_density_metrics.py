"""Breaks caught: summed overlapping occupancy, fake frontage, and missing geometry."""
from dataclasses import replace

from modeling.slum03.density_metrics import union_area, density_report, validate_density
from modeling.slum03.density_layout import build_density_layout
from modeling.slum03.layout import build_layout
from modeling.slum03.types import (DensityConfig, DensityOpening, DensityRoute,
                                   DensityZone, Placement, RectXZ)


def test_rectangle_union_does_not_double_count():
    assert union_area([RectXZ(0, 2, 0, 2), RectXZ(1, 3, 0, 2)]) == 6
    assert union_area([]) == 0


def frontage_fixture(length, opening=()):
    base = build_layout()
    # North/south route; centre at x=0, span z=20..60. Two 2m-frontage
    # buildings at the ends leave a controlled, literal continuous gap.
    route = DensityRoute('test-lane', 'alley', RectXZ(-1.5, 1.5, 20, 60), opening)
    density = DensityConfig('full', (DensityZone('test', RectXZ(-20, 20, 20, 60)),),
                            (route,), (), ())
    # x=5 lies in the right-hand 10m band. Buildings have width & height >=1m.
    buildings = (Placement('edge-a', 'test', 'ruin', (5, 0, 21), (2, 4, 2), 0, 'district',
                           {'density_zone': 'test', 'variant': 'a'}),
                 Placement('edge-b', 'test', 'ruin', (5, 0, 23 + length), (2, 4, 2), 0, 'district',
                           {'density_zone': 'test', 'variant': 'b'}))
    return replace(base, density=density, placements=base.placements + buildings)


def test_frontage_20_allowed_20_01_rejected():
    for length, flagged in [(20, False), (20.01, True)]:
        layout = frontage_fixture(length)
        gaps = density_report(layout, {}, 'blockout')['frontage_gaps']['test-lane']
        assert any(abs(g['length'] - length) < .0001 for g in gaps)
        assert any(i.code == 'FRONTAGE_GAP' for i in validate_density(layout, {}, 'blockout')) == flagged


def test_tiny_props_background_and_unapproved_openings_do_not_hide_frontage():
    layout = frontage_fixture(20.01)
    prop = Placement('tiny', 'test', 'prop', (-5, 0, 35), (.9, .9, 2), 0, 'district')
    background = Placement('bg', 'test', 'ruin', (-5, 0, 36), (2, 4, 3), 0, 'background')
    bad_opening = DensityOpening(RectXZ(-15, 15, 22, 50), 'unapproved')
    layout = replace(layout, placements=layout.placements + (prop, background),
                     density=replace(layout.density, routes=(replace(layout.density.routes[0],
                                                                     openings=(bad_opening,)),)))
    assert 'FRONTAGE_GAP' in {i.code for i in validate_density(layout, {}, 'blockout')}


def test_evaluated_requires_real_geometry_not_just_placement_or_empty_mesh():
    base = build_layout()
    full = build_density_layout(base, 'full')
    assert 'GEOMETRY_MISSING' in {i.code for i in validate_density(full, {}, 'evaluated')}
    p = next(p for p in full.placements if p.key.startswith('density-') and p.kind == 'ruin')
    bounds = {'minimum': [p.origin[0]-4, 0, p.origin[2]-4],
              'maximum': [p.origin[0]+4, 10, p.origin[2]+4]}
    reports = {'test': {'objects': [{'mesh': 'fake', 'placement_key': p.key,
                                    'vertices': 0, 'faces': 0}],
                        'evaluated_bounds': {'fake': bounds}}}
    assert 'GEOMETRY_MISSING' in {i.code for i in validate_density(full, reports, 'evaluated')}


def test_attachment_without_contact_is_rejected():
    full = build_density_layout(build_layout(), 'full')
    p = next(p for p in full.placements if p.key.startswith('density-') and p.kind == 'ruin')
    changed = replace(p, params={**p.params, 'attachment': {'parent_key': 'yarol',
                      'contact_min': [0, 0, 0], 'contact_max': [0, 1, 0], 'reason': 'fake'}})
    altered = replace(full, placements=tuple(changed if q.key == p.key else q for q in full.placements))
    assert 'ATTACHMENT' in {i.code for i in validate_density(altered, {}, 'blockout')}


def test_evaluated_mesh_intersection_is_caught_individually():
    from modeling.slum03.spatial import placement_bounds
    full = build_density_layout(build_layout(), 'full')
    a, b = [p for p in full.placements if p.key.startswith('density-') and p.kind == 'ruin'][:2]
    ba = placement_bounds(a)
    raw = {'minimum': list(ba.minimum), 'maximum': list(ba.maximum)}
    reports = {'ruins': {'layout_sha256': density_report(full, {}, 'blockout')['layout_sha256'],
                         'objects': [{'mesh': 'mesh-a', 'placement_key': a.key, 'vertices': 8, 'faces': 6},
                                     {'mesh': 'mesh-b', 'placement_key': b.key, 'vertices': 8, 'faces': 6}],
                          'evaluated_bounds': {'mesh-a': raw, 'mesh-b': raw}}}
    assert any(i.code == 'DENSITY_OVERLAP' for i in validate_density(full, reports, 'evaluated'))


def test_forged_approved_reason_cannot_suppress_unapproved_gap():
    layout = frontage_fixture(20.01)
    fake = DensityOpening(RectXZ(-1.5, 1.5, 30, 35), 'plaza-entry')
    altered = replace(layout, density=replace(layout.density, routes=(
        replace(layout.density.routes[0], openings=(fake,)),)))
    assert 'FRONTAGE_GAP' in {i.code for i in validate_density(altered, {}, 'blockout')}


def test_frontage_longitudinal_width_not_lateral_overlap():
    lane = frontage_fixture(20.01)
    # Wall only 0.1m across the street but 5m along it qualifies.
    long_wall = Placement('wall', 'test', 'utility', (5, 0, 32), (.1, 3, 5), 0, 'district')
    # Conversely 2m across the street and 0.1m along it cannot break the gap.
    short_wall = replace(long_wall, size=(2, 3, .1))
    assert 'FRONTAGE_GAP' not in {i.code for i in validate_density(
        replace(lane, placements=lane.placements + (long_wall,)), {}, 'blockout')}
    assert 'FRONTAGE_GAP' in {i.code for i in validate_density(
        replace(lane, placements=lane.placements + (short_wall,)), {}, 'blockout')}


def test_evaluated_reports_without_matching_layout_digest_are_never_accepted():
    full = build_density_layout(build_layout(), 'full')
    p = next(p for p in full.placements if p.key.startswith('density-') and p.kind == 'ruin')
    original = density_report(full, {}, 'blockout')['layout_sha256']
    raw = {'minimum': [p.origin[0]-4, 0, p.origin[2]-4],
           'maximum': [p.origin[0]+4, 10, p.origin[2]+4]}
    for digest in (None, '0'*64, original):
        report = {'objects': [{'mesh': 'real', 'placement_key': p.key, 'vertices': 8, 'faces': 6}],
                  'evaluated_bounds': {'real': raw}}
        if digest is not None:
            report['layout_sha256'] = digest
        result = density_report(full, {'ruins': report}, 'evaluated')
        if digest == original:
            assert result['occupied_union_m2'] > 0
            assert not any(i['code'] == 'LAYOUT_MISMATCH' for i in result['issues'])
        else:
            assert result['occupied_union_m2'] == 0
            assert any(i['code'] == 'LAYOUT_MISMATCH' for i in result['issues'])


def test_representative_evaluated_shape_and_utility_are_not_exempt_from_collisions():
    from modeling.slum03.spatial import placement_bounds
    rep = build_density_layout(build_layout(), 'representative')
    annex = next(p for p in rep.placements if p.key == 'ruin-west-annex')
    market = next(p for p in rep.placements if p.key == 'market-west')
    utility = Placement('extra-utility', 'market', 'utility', market.origin, (2, 2, 2), 0,
                        'district')
    rep = replace(rep, placements=rep.placements + (utility,))
    bounds = placement_bounds(annex)
    def raw(b):
        return {'minimum': list(b.minimum), 'maximum': list(b.maximum)}
    report = {'layout_sha256': density_report(rep, {}, 'blockout')['layout_sha256'],
              'objects': [{'mesh': key, 'placement_key': key, 'vertices': 8, 'faces': 6}
                          for key in ('ruin-west', 'ruin-west-annex', 'market-west', 'extra-utility')],
              'evaluated_bounds': {'ruin-west': raw(bounds), 'ruin-west-annex': raw(bounds),
                                   'market-west': raw(placement_bounds(market)),
                                   'extra-utility': raw(placement_bounds(utility))}}
    problems = validate_density(rep, {'ruins': report}, 'evaluated')
    assert any(i.code == 'DENSITY_OVERLAP' and 'ruin-west-annex' in i.message for i in problems)
    assert any(i.code == 'DENSITY_OVERLAP' and 'extra-utility' in i.message for i in problems)


def test_layout_digest_is_semantic_and_distinct_from_pretty_saved_json(tmp_path):
    import hashlib
    from modeling.slum03.layout import write_layout, read_layout
    layout = build_density_layout(build_layout(), 'full')
    path = tmp_path / 'full.json'
    write_layout(layout, path)
    first = density_report(layout, {}, 'blockout')
    second = density_report(read_layout(path), {}, 'blockout')
    assert first['layout_sha256'] == second['layout_sha256']
    assert first['layout_sha256_basis'] == 'canonical-layout-json-utf8'
    assert hashlib.sha256(path.read_bytes()).hexdigest() != first['layout_sha256']


def _ground_report(layout, top_override=None):
    from modeling.slum03 import ground
    from modeling.slum03.density_metrics import layout_digest
    foundation = next(a for a in ground.build_assemblies(layout, 'ground')
                      if a.name == 'district-foundation')
    lo = [min(v[i] for p in foundation.parts for v in p.vertices) for i in range(3)]
    hi = [max(v[i] for p in foundation.parts for v in p.vertices) for i in range(3)]
    if top_override is not None:
        hi[1] = top_override
    return {'layout_sha256': layout_digest(layout),
            'objects': [{'key': 'district-ground', 'kind': 'foundation',
                         'mesh': 'district-foundation', 'vertices': 8, 'faces': 6}],
            'evaluated_bounds': {'district-foundation': {'minimum': lo, 'maximum': hi}}}


def test_evaluated_curbed_foundation_is_checked_by_parts_not_as_one_route_blocker():
    """Task 11 curbs raise the ground envelope to ~0.134 m (T13-GROUND)."""
    from pathlib import Path
    from modeling.slum03.layout import read_layout
    full = read_layout(Path('content/slum03/density-full-layout.json'))
    ground = {i['code'] for i in density_report(full, {'ground': _ground_report(full)}, 'evaluated')['issues']
              if i['object_key'] in ('district-ground', 'district-foundation')}
    assert ground == set()
    forged = {i['code'] for i in density_report(full, {'ground': _ground_report(full, .5)}, 'evaluated')['issues']
              if i['object_key'] in ('district-ground', 'district-foundation')}
    assert {'SURFACE_EVIDENCE', 'CLEARANCE_INTRUSION'} <= forged
