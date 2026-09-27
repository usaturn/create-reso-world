import math
import pytest
from modeling.slum03 import geometry as g


def test_outward_box_and_recessed_wall():
    box = g.box('box', (0, 1, 0), (4, 2, 1), 'concrete_raw')
    wall = g.wall_with_openings('wall', 6, 3, .4, [(-1, 1, 1, 2.2)], .25, 1, 'concrete_raw')
    assert g.signed_volume(box) == pytest.approx(8)
    assert g.signed_volume(wall) == pytest.approx(6 * 3 * .4 - 2 * 1.2 * .25)
    lo, hi = g.bounds([wall])
    assert lo == pytest.approx((-3, 0, -.2))
    assert hi == pytest.approx((3, 3, .2))


def test_material_order_matches_submeshes():
    parts = [g.box('a', (0, 1, 0), (1, 2, 1), mat) for mat in ('rust', 'steel_bare', 'rust')]
    merged = g.merge_assembly(g.Assembly('test', 'one', 'ground', (0, 0, 0), parts))
    assert merged.materials == ('rust', 'steel_bare')
    assert merged.face_materials == (0,) * 6 + (1,) * 6 + (0,) * 6
    assert len(merged.vertices) == 24


def test_cable_sags_and_rotates_about_up_axis():
    points = g.catenary((0, 5, 0), (10, 5, 0), 1.5, 16)
    assert points[0] == (0, 5, 0) and points[-1] == (10, 5, 0)
    assert min(p[1] for p in points) == pytest.approx(3.5)
    assert g.rotate_y((1, 0, 0), math.pi / 2) == pytest.approx((0, 0, -1))
    assert g.signed_volume(g.tube('cable', points, .05, 6, 'rust')) > 0
