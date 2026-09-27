from dataclasses import replace

import pytest

from modeling.slum03.layout import build_layout
from modeling.slum03.spatial import placement_bounds, validate_clearance
from modeling.slum03.types import Bounds3, Placement


def test_rotated_placement_uses_full_footprint_and_local_vertical_offset():
    p = Placement('test', 'market', 'stall', (5, 2, 9), (4, 3, 2), 90, 'district',
                  {'local_y_min': -3})
    b = placement_bounds(p)
    assert b.minimum == (4, -1, 7)
    assert b.maximum == (6, 2, 11)


def test_evaluated_bounds_catch_intrusion_even_if_origin_is_outside():
    a = build_layout()
    p = next(p for p in a.placements if p.key == 'north-wall')
    extended = Bounds3((-2, 0, 10), (2, 3, 15))
    issues = validate_clearance(a, {p.key: extended})
    assert any(i.code == 'CLEARANCE_INTRUSION' and i.object_key == p.key for i in issues)


def test_obstacles_blocking_plaza_upper_air_or_routes_are_reported():
    a = build_layout()
    p = next(p for p in a.placements if p.key == 'north-wall')
    for b in (Bounds3((-1, 2.5, -1), (1, 4, 1)),
              Bounds3((20, 0, -1), (23, 3, 1))):
        assert any(i.code == 'CLEARANCE_INTRUSION' for i in validate_clearance(a, {p.key: b}))


def test_floor_surfaces_do_not_count_as_walkway_obstacles():
    a = build_layout()
    floor = next(p for p in a.placements if p.key == 'factory-floor')
    assert validate_clearance(a, {floor.key: placement_bounds(floor)}) == []


def test_bad_evaluated_bounds_are_not_silently_accepted():
    a = build_layout()
    assert any(i.code == 'BOUNDS' for i in validate_clearance(
        a, {'north-wall': Bounds3((2, 0, 0), (1, 1, 1))}))


def test_evaluated_floor_protrusion_above_walkway_is_not_exempt():
    a = build_layout()
    floor = next(p for p in a.placements if p.key == 'factory-floor')
    raised = Bounds3((-20, -.2, -15), (20, 1, 15))
    assert any(i.code == 'CLEARANCE_INTRUSION' for i in validate_clearance(a, {floor.key: raised}))


@pytest.mark.parametrize('bad_bounds', [
    Bounds3((0, 0), (1, 1, 1)),
    Bounds3((0, 0, 0, 0), (1, 1, 1)),
    Bounds3((0, 0, 0), (1, 1)),
    Bounds3((0, 0, 0), (1, 1, 1, 1)),
])
def test_evaluated_bounds_with_wrong_vector_lengths_report_issue(bad_bounds):
    issues = validate_clearance(build_layout(), {'north-wall': bad_bounds})
    assert any(issue.code == 'BOUNDS' and issue.object_key == 'north-wall'
               for issue in issues)
