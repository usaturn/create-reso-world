"""Failures caught: floating cable ends and wires crossing the activity air volume."""
from modeling.slum03.geometry import bounds
from modeling.slum03.layout import build_layout
from modeling.slum03.materials import MATERIALS
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.spatial import placement_bounds, validate_clearance
from modeling.slum03.types import Bounds3


def test_overhead_avoids_activity_volume():
    for seed in (260927, 8195):
        layout = build_layout(seed)
        p = next(p for p in layout.placements if p.key == 'overhead-west')
        for a in sector_assemblies(layout, 'overhead'):
            lo, hi = bounds(a.parts)
            real = Bounds3(tuple(lo[i] + a.origin[i] for i in range(3)),
                           tuple(hi[i] + a.origin[i] for i in range(3)))
            canon = placement_bounds(p)
            assert all(canon.minimum[i] - 1e-6 <= real.minimum[i] <= real.maximum[i] <= canon.maximum[i] + 1e-6
                       for i in range(3))
            assert not validate_clearance(layout, {a.name: real})
            assert {part.material for part in a.parts} <= MATERIALS.keys()


def test_cable_endpoints_have_supports():
    (a,) = sector_assemblies(build_layout(), 'overhead')
    assert a.meta['placement_key'] == 'overhead-west'
    cable = next(p for p in a.parts if p.name == 'power-cable')
    supports = [p for p in a.parts if p.name == 'pole']
    assert len(supports) == 2
    xs = sorted((min(v[0] for v in cable.vertices), max(v[0] for v in cable.vertices)))
    for x, support in zip(xs, sorted(supports, key=lambda p: min(v[0] for v in p.vertices))):
        sl, sh = bounds([support])
        assert sl[0] - .25 <= x <= sh[0] + .25
        assert sl[1] <= -11 and sh[1] >= -.15  # pole physically runs to ground and attachment
    assert any(p.name == 'insulator' for p in a.parts)


# --- Task 8: independent, supported overhead routes across the district ---

from dataclasses import replace
from pathlib import Path

import pytest

from modeling.slum03.geometry import Assembly
from modeling.slum03.layout import read_layout

FULL = Path('content/slum03/density-full-layout.json')


def _full():
    layout = read_layout(FULL)
    return layout, sector_assemblies(layout, 'overhead')


def test_full_has_twelve_or_more_independently_supported_routes():
    from modeling.slum03.overhead import route_evidence
    layout, assemblies = _full()
    placements = [p for p in layout.placements if p.kind == 'overhead']
    assert len(assemblies) == len(placements) >= 12
    assert {a.name for a in assemblies} == {p.key for p in placements}
    routes, issues = route_evidence(layout, assemblies)
    assert not issues
    assert len(routes) >= 12
    zones = {r['density_zone'] for r in routes if r['density_zone']}
    assert zones == {'northwest', 'southwest', 'market', 'east'}
    for p in placements:
        if p.key == 'overhead-west':
            continue
        assert {'supports', 'route', 'cluster', 'density_zone'} <= p.params.keys()
        assert len(p.params['supports']) == 2


def test_route_parts_stay_in_site_and_out_of_protected_air():
    layout, assemblies = _full()
    sites = {p.key: placement_bounds(p) for p in layout.placements}
    for a in assemblies:
        for part in a.parts:
            lo, hi = bounds([part])
            real = Bounds3(tuple(lo[i]+a.origin[i] for i in range(3)),
                           tuple(hi[i]+a.origin[i] for i in range(3)))
            site = sites[a.name]
            assert all(site.minimum[i]-1e-6 <= real.minimum[i] <= real.maximum[i]
                       <= site.maximum[i]+1e-6 for i in range(3)), (a.name, part.name)
            assert not validate_clearance(layout, {a.name: real}), (a.name, part.name)
            assert part.material in MATERIALS
        cables = [p for p in a.parts if p.name in ('power-cable', 'service-cable')]
        assert cables and min(v[1]+a.origin[1] for c in cables for v in c.vertices) >= 3.5


def test_segmented_single_line_is_not_counted_as_many_routes():
    from modeling.slum03.overhead import route_evidence
    layout, assemblies = _full()
    p = next(p for p in layout.placements if p.key.startswith('density-overhead-'))
    (x0, y0, z0), (x1, y1, z1) = p.params['supports']
    # Split one route into three collinear pieces sharing their poles.
    points = [(x0 + (x1-x0)*t, y0, z0 + (z1-z0)*t) for t in (0, 1/3, 2/3, 1)]
    pieces = []
    for i in range(3):
        mid = tuple((points[i][k] + points[i+1][k])/2 for k in range(3))
        pieces.append(replace(p, key=f'{p.key}-piece-{i}', origin=mid,
                              params={**p.params, 'supports': [list(points[i]), list(points[i+1])]}))
    from modeling.slum03.overhead import build_assemblies
    fake = replace(layout, placements=tuple(q for q in layout.placements if q.key != p.key) + tuple(pieces))
    fake_assemblies = build_assemblies(fake, 'overhead')
    routes, issues = route_evidence(fake, fake_assemblies)
    assert len(routes) < len(_full()[1])
    assert any('shared' in issue or 'span' in issue for issue in issues)


def test_unsupported_endpoint_and_low_sag_are_rejected():
    from modeling.slum03.overhead import route_evidence
    layout, assemblies = _full()
    target = next(a for a in assemblies if a.name.startswith('density-overhead-'))
    floating = Assembly(target.kind, target.name, target.sector, target.origin,
                        [part for part in target.parts if part.name != 'pole'], target.meta)
    _, issues = route_evidence(layout, [floating if a is target else a for a in assemblies])
    assert any(target.name in issue and 'support' in issue for issue in issues)
    from modeling.slum03.geometry import mesh
    sagging = Assembly(target.kind, target.name, target.sector, target.origin,
                       [mesh(part.name, [(v[0], v[1]-4.5 if 0 < i < len(part.vertices)-8 else v[1], v[2])
                                         for i, v in enumerate(part.vertices)], part.faces, part.material)
                        if part.name == 'power-cable' else part for part in target.parts], target.meta)
    _, issues = route_evidence(layout, [sagging if a is target else a for a in assemblies])
    assert any(target.name in issue for issue in issues)
