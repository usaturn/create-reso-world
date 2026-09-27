"""Breaks caught: a single signboard in place of shopfronts or a blocked east lane."""
from modeling.slum03.geometry import bounds
from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.spatial import placement_bounds, validate_clearance
from modeling.slum03.types import Bounds3


def test_nightlife_has_separate_non_explicit_storefronts_and_labels():
    layout = build_layout()
    fronts = sector_assemblies(layout, 'nightlife')
    assert len(fronts) >= 2 and len({a.name for a in fronts}) == len(fronts)
    for front in fronts:
        assert front.meta['placement_key'] == front.name
        assert any(label.parent_name == front.name and label.text for label in layout.labels)
        names = {part.name for part in front.parts}
        assert {'pier', 'shutter-slat', 'shutter-guide', 'sign-mount', 'neon-tube'} <= names
        lo, hi = bounds(front.parts)
        real = Bounds3(tuple(lo[i]+front.origin[i] for i in range(3)),
                       tuple(hi[i]+front.origin[i] for i in range(3)))
        site = placement_bounds(next(p for p in layout.placements if p.key == front.name))
        assert all(site.minimum[i]-1e-6 <= real.minimum[i] <= real.maximum[i] <= site.maximum[i]+1e-6
                   for i in range(3))
        assert not validate_clearance(layout, {front.name: real})
        guides = [p for p in front.parts if p.name == 'shutter-guide']
        slats = [p for p in front.parts if p.name == 'shutter-slat']
        assert len(guides) == 2 and len(slats) >= 5
        assert all(min(v[1] for v in s.vertices) < 2.6 for s in slats)
        # Sign mounting actually joins a pier or lintel, not an unsupported floating sign.
        mounts = [p for p in front.parts if p.name == 'sign-mount']
        structure = [p for p in front.parts if p.name in ('pier', 'lintel')]
        for mount in mounts:
            a, b = bounds([mount])
            assert any(all(a[i] <= bounds([s])[1][i]+.02 and bounds([s])[0][i] <= b[i]+.02
                           for i in range(3)) for s in structure)


def test_upper_storefront_is_closed_and_labels_are_in_front_of_the_lintel():
    layout = build_layout()
    for front in sector_assemblies(layout, 'nightlife'):
        cladding = [p for p in front.parts if p.name == 'upper-cladding']
        assert cladding
        assert max(v[1] for part in cladding for v in part.vertices) >= 10
        lintel = next(p for p in front.parts if p.name == 'lintel')
        label = next(l for l in layout.labels if l.parent_name == front.name)
        assert label.offset[2] > bounds([lintel])[1][2]
        assert label.offset[2] < max(v[2] for part in front.parts if part.name == 'neon-tube' for v in part.vertices)


def test_neon_outline_touches_each_storefront_mount():
    for a in sector_assemblies(build_layout(), 'nightlife'):
        mounts = [p for p in a.parts if p.name == 'sign-mount']
        tubes = [p for p in a.parts if p.name == 'neon-tube']
        assert len(mounts) == 2
        assert all(any(_overlap(mount, tube) for tube in tubes) for mount in mounts)


def _overlap(a, b):
    low, high = bounds([a]); lo, hi = bounds([b])
    return all(low[i] <= hi[i]+.005 and lo[i] <= high[i]+.005 for i in range(3))
