"""Regression targets: anonymous box stock, clip-count fraud, unsupported or invisible goods."""
import pytest

from modeling.slum03.geometry import bounds
from modeling.slum03.types import Placement


def sample(variant, w=2.5, d=3.):
    return Placement('compact-stall', 'market', 'stall', (7., 0., -12.),
                     (w, 3., d), 0., 'district',
                     {'detail_profile': 'v2', 'variant': variant})


def shape(item):
    """Compare geometry relative to item origin, independent of palette and part names."""
    return tuple(sorted(tuple(sorted(tuple(sorted(tuple(round(c, 5) for c in part.vertices[i])
                                          for i in face)) for face in part.faces)) for part in item.parts))


@pytest.mark.parametrize('variant', ['electronics', 'tools', 'prosthetics', 'reclaimed_equipment'])
@pytest.mark.parametrize('w,d', [(2.5, 3.), (4., 5.)])
def test_stock_is_twelve_discrete_multi_part_local_objects_in_display_cells(variant, w, d):
    from modeling.slum03.merchandise import stock_items
    p = sample(variant, w, d)
    items = stock_items(p, 260927)
    assert len(items) >= 12
    assert len({item.name for item in items}) == len(items)
    assert all(item.kind == 'merchandise' and item.sector == p.sector for item in items)
    assert all(len(item.parts) >= 2 for item in items)
    # Replacing goods with twelve copies of a color-coded cuboid fails even if names change.
    assert len({shape(item) for item in items}) >= 3
    for item in items:
        low, high = bounds(item.parts)
        assert low[1] >= -1e-6  # origin is the supporting shelf top, not world origin
        for axis, half in ((0, w/2), (2, d/2)):
            assert -half+1e-6 < low[axis]+item.origin[axis]
            assert high[axis]+item.origin[axis] < half-1e-6
        assert all(part.faces and part.vertices for part in item.parts)


def test_circuitry_tool_monitor_and_limb_have_different_actual_silhouettes():
    from modeling.slum03.merchandise import stock_items
    signatures = {}
    for variant in ('electronics', 'tools', 'prosthetics', 'reclaimed_equipment'):
        items = stock_items(sample(variant), 260927)
        signatures[variant] = {shape(item) for item in items}
        assert any(len(item.parts) >= 3 for item in items)
        assert any(len(part.vertices) > 8 for item in items for part in item.parts)
    assert all(signatures[a] != signatures[b] for a in signatures for b in signatures if a != b)


def test_merchandise_can_be_translated_to_support_without_extra_export_slots():
    from modeling.slum03.merchandise import stock_items
    from modeling.slum03.market_detail import detailed_stall
    p = sample('electronics')
    stock = stock_items(p, 260927)
    stall = detailed_stall(p, 260927)
    assert all(item.origin != p.origin for item in stock)
    assert len([g for g in stall.meta['detail_groups'] if g['category'] == 'merchandise']) == len(stock)
    assert all(any(part.vertices for part in item.parts) for item in stock)
    assert stall.kind == 'stall'  # no additional assembly/Slot for each chip or commodity
