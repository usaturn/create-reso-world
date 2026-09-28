"""Breaks caught: summed overlapping occupancy, fake frontage, and missing geometry."""
from dataclasses import replace

from modeling.slum03.density_metrics import union_area, density_report, validate_density
from modeling.slum03.density_layout import build_density_layout
from modeling.slum03.layout import build_layout
from modeling.slum03.types import (Bounds3, DensityConfig, DensityOpening, DensityRoute,
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
    reports = {'ruins': {'objects': [{'mesh': 'mesh-a', 'placement_key': a.key, 'vertices': 8, 'faces': 6},
                                     {'mesh': 'mesh-b', 'placement_key': b.key, 'vertices': 8, 'faces': 6}],
                          'evaluated_bounds': {'mesh-a': raw, 'mesh-b': raw}}}
    assert any(i.code == 'DENSITY_OVERLAP' for i in validate_density(full, reports, 'evaluated'))


def test_forged_approved_reason_cannot_suppress_unapproved_gap():
    layout = frontage_fixture(20.01)
    fake = DensityOpening(RectXZ(-1.5, 1.5, 30, 35), 'plaza-entry')
    altered = replace(layout, density=replace(layout.density, routes=(
        replace(layout.density.routes[0], openings=(fake,)),)))
    assert 'FRONTAGE_GAP' in {i.code for i in validate_density(altered, {}, 'blockout')}
