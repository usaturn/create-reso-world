from dataclasses import replace
from modeling.slum03.layout import build_layout
from modeling.slum03.spatial import validate_clearance
from modeling.slum03.types import Bounds3, Placement
from modeling.slum03.gn_scatter import scatter_samples


def test_protruding_rebar_bounds_are_rejected_even_if_centre_is_outside():
    base = build_layout()
    p = Placement('rubble-probe', 'plaza', 'rubble', (16.5, 0, 0), (2, 1, 2), 45, 'district', {})
    layout = replace(base, placements=base.placements + (p,))
    issues = validate_clearance(layout, {p.key: Bounds3((15.5, 0, -1), (17.5, 1, 1))})
    assert any(i.code == 'CLEARANCE_INTRUSION' for i in issues)


def test_sampled_rubble_uses_full_maximum_extent_for_clear_and_three_entries():
    layout = build_layout()
    assert scatter_samples(layout, seed=1, count=0, max_extent=(2, 1, 2)) == ()
    first = scatter_samples(layout, seed=1, count=36, max_extent=(2, 1, 2))
    assert first == scatter_samples(layout, seed=1, count=36, max_extent=(2, 1, 2))
    assert first != scatter_samples(layout, seed=2, count=36, max_extent=(2, 1, 2))
    assert len(first) == 36
    for x, y, z in first:
        assert y == 0
        b = Bounds3((x-1, 0, z-1), (x+1, 1, z+1))
        assert not validate_clearance(layout, {'sample': b})
        assert layout.plaza.x_min <= x-1 and x+1 <= layout.plaza.x_max
        assert layout.plaza.z_min <= z-1 and z+1 <= layout.plaza.z_max


def test_scatter_rejects_extent_larger_than_factory_perimeter():
    import pytest
    with pytest.raises(ValueError, match='maximum extent exceeds plaza'):
        scatter_samples(build_layout(), seed=1, count=1, max_extent=(100, 1, 2))


def test_scatter_has_dense_perimeter_piles_and_sparser_gaps():
    import math
    points = scatter_samples(build_layout(), seed=260927, count=72,
                             max_extent=(1.8, 1.3, 1.8))
    landmarks = [(-18, -8), (-18, 8), (18, -8), (18, 8),
                 (-11, -13), (11, -13), (-11, 12.6), (11, 12.6)]
    near = [min(math.dist((x, z), c) for c in landmarks) < 1.6
            for x, _, z in points]
    assert sum(near) >= 43  # designed accumulations, not uniform scatter
    assert sum(not is_near for is_near in near) >= 7  # unfilled breathing room
    assert sum(sum(math.dist((x,z), c) < 1.6 for x, _, z in points) >= 5
               for c in landmarks) >= 4
