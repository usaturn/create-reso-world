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
