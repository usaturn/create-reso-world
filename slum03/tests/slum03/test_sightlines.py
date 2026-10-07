from modeling.slum03.layout import build_layout
from modeling.slum03.spatial import placement_bounds
from modeling.slum03.sightlines import sightline_report
from modeling.slum03.types import Bounds3


def _bounds(layout):
    return {p.key: placement_bounds(p) for p in layout.placements}


def test_north_wall_does_not_hide_all_arcologies():
    layout = build_layout()
    assert sightline_report(layout, _bounds(layout))['north_arcologies']
    # A taller solid foreground facade must NOT pass merely because towers still have keys.
    bounds = _bounds(layout)
    bounds['north-wall'] = Bounds3((-80, 0, 14), (80, 850, 16))
    assert sightline_report(layout, bounds)['north_arcologies'] is False


def test_north_requires_two_distinct_readable_silhouettes():
    layout = build_layout()
    bounds = _bounds(layout)
    for key in ('arcology-gate', 'arcology-towers'):
        bounds.pop(key)
    assert sightline_report(layout, bounds)['north_arcologies'] is False


def test_east_route_sees_forest():
    layout = build_layout()
    bounds = _bounds(layout)
    assert sightline_report(layout, bounds)['east_forest']
    bounds['forest'] = Bounds3((180, 0, -88), (220, 2, 67))
    assert sightline_report(layout, bounds)['east_forest'] is False
    bounds = _bounds(layout)
    bounds['east-screen'] = Bounds3((97, 0, -100), (99, 60, 80))
    assert sightline_report(layout, bounds)['east_forest'] is False


def test_west_south_background_rejects_exposed_horizon_end():
    layout = build_layout()
    bounds = _bounds(layout)
    assert sightline_report(layout, bounds)['west_city']
    assert sightline_report(layout, bounds)['south_city']
    bounds.pop('west-city')
    bounds.pop('south-city')
    assert not sightline_report(layout, bounds)['west_city']
    assert not sightline_report(layout, bounds)['south_city']
    bounds = _bounds(layout)
    bounds['west-city'] = Bounds3((-147, 0, 25), (-82, 42, 75))
    bounds['south-city'] = Bounds3((25, 0, -154), (57, 38, -89))
    report = sightline_report(layout, bounds)
    assert report['west_city'] is False
    assert report['south_city'] is False


def test_east_laneway_eye_is_in_district_public_route():
    layout = build_layout()
    eye = next(v.eye for v in layout.viewpoints if v.key == 'east-lane')
    sidewalk = next(v.eye for v in layout.viewpoints if v.key == 'east-forest')
    assert eye != sidewalk and layout.district.x_min < eye[0] < layout.district.x_max
    assert any(r.x_min <= eye[0] <= r.x_max and r.z_min <= eye[2] <= r.z_max
               for r in layout.routes)
    assert sightline_report(layout, _bounds(layout))['east_forest']


def test_lane_blocked_but_sidewalk_open_fails_east_forest():
    layout = build_layout()
    bounds = _bounds(layout)
    # In the district, before the sidewalk at x63; walking on sidewalk is still clear.
    bounds['laneway-screen'] = Bounds3((57, 0, -40), (59, 45, 40))
    assert sightline_report(layout, bounds)['east_forest'] is False


def test_sidewalk_blocked_but_east_lane_open_fails_east_forest():
    layout = build_layout()
    bounds = _bounds(layout)
    # Thin screen at the west sidewalk eye. The two oblique rays from x54
    # bypass it, but all three rays originating at x63 hit it immediately.
    bounds['sidewalk-screen'] = Bounds3((62.8, 0, -1), (63.2, 45, 1))
    assert sightline_report(layout, bounds)['east_forest'] is False
