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


# --- Task 12 (revision 1): walkable small debris on the central floor -------

def _full_layout():
    from pathlib import Path
    from modeling.slum03.layout import read_layout
    return read_layout(Path('content/slum03/density-full-layout.json'))


def test_low_floor_debris_may_lie_on_the_central_floor_but_nowhere_protected():
    from modeling.slum03.density_model import FLOOR_DEBRIS_MAX, FLOOR_DEBRIS_PREFIX
    full = _full_layout()
    key = f'{FLOOR_DEBRIS_PREFIX}-0-0'
    low = Bounds3((-12, -.004, -9), (-4, FLOOR_DEBRIS_MAX, -3))
    assert validate_clearance(full, {key: low}) == []
    # Too tall, on a main route (the plaza entrances), or outside the floor debris family.
    for name, b in ((key, Bounds3((-12, -.004, -9), (-4, FLOOR_DEBRIS_MAX + .01, -3))),
                    (key, Bounds3((-12, -.004, -9), (-1, .05, -3))),       # south route x -1.5..1.5
                    (key, Bounds3((-12, -.004, -2), (-4, .05, -1))),       # west-east route
                    (key, Bounds3((-19, -.004, -1), (-17, .05, 1))),       # west entrance
                    ('plaza-rubble-west-3-3', low), ('north-wall', low)):
        assert any(i.code == 'CLEARANCE_INTRUSION' for i in validate_clearance(full, {name: b})), (name, b)
    # Pre-full layouts keep the old rule: nothing above the central floor.
    assert any(i.code == 'CLEARANCE_INTRUSION' for i in validate_clearance(build_layout(), {key: low}))


def test_walkable_floor_may_carry_flush_decals_below_one_centimetre():
    from modeling.slum03.spatial import WALKABLE_DECAL_MAX
    a = build_layout()
    floor = next(p for p in a.placements if p.key == 'factory-floor')
    assert WALKABLE_DECAL_MAX <= .01
    decal = Bounds3((-20, -.2, -15), (20, WALKABLE_DECAL_MAX, 15))
    assert validate_clearance(a, {floor.key: decal}) == []
    step = Bounds3((-20, -.2, -15), (20, WALKABLE_DECAL_MAX + .005, 15))
    assert any(i.code == 'CLEARANCE_INTRUSION' for i in validate_clearance(a, {floor.key: step}))


def test_district_foundation_slot_is_the_walkable_district_ground():
    """The Slot/mesh 'district-foundation' is the 'district-ground' placement (T13-GROUND)."""
    a = build_layout()
    flat = Bounds3((-60, -.3, -60), (60, .005, 60))  # flush decals only
    assert validate_clearance(a, {'district-foundation': flat}) == []
    # A raised aggregate is not blindly exempt: curbs need part-level evidence.
    curbed = Bounds3((-60, -.3, -60), (60, .134, 60))
    assert any(i.code == 'CLEARANCE_INTRUSION'
               for i in validate_clearance(a, {'district-foundation': curbed}))
