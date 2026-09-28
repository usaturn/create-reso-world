"""Regression targets: oversize stock, false detail counts, closed front and inward awning."""
from dataclasses import replace
import math

import pytest

from modeling.slum03.detail_evidence import detail_groups
from modeling.slum03.geometry import bounds, box, face_normal, rotate_y, signed_volume
from modeling.slum03.types import Placement


def sample(variant, w=2.5, d=3., yaw=0):
    return Placement('compact-stall', 'market', 'stall', (7., 0., -12.),
                     (w, 3., d), yaw, 'district',
                     {'detail_profile': 'v2', 'variant': variant})


def front_blocked(parts, d):
    """Face spanning the customer ray at the shelf face, between merchandise rows."""
    for part in parts:
        for face in part.faces:
            vertices = [part.vertices[i] for i in face]
            if (min(v[0] for v in vertices) < 0 < max(v[0] for v in vertices)
                    and min(v[1] for v in vertices) < 1.35 < max(v[1] for v in vertices)
                    and min(v[2] for v in vertices) > -d/2+1.3
                    and max(v[2] for v in vertices) < d/2-.05):
                return True
    return False


@pytest.mark.parametrize('variant', ['electronics', 'tools', 'prosthetics', 'reclaimed_equipment'])
@pytest.mark.parametrize('w,d', [(2.5, 3.), (4., 5.)])
def test_compact_stocked_stall_has_two_real_shelves_and_twelve_separate_supported_items(variant, w, d):
    # Removing shelves, duplicating part indices, counting chips separately, or using
    # old +/-3.5 m uprights will break these face-backed geometry checks.
    from modeling.slum03.market_detail import detailed_stall
    p = sample(variant, w, d)
    a = detailed_stall(p, 260927)
    assert a.origin == p.origin and a.name == a.meta['placement_key'] == p.key
    assert a.kind == p.kind and a.sector == p.sector and a.meta['variant'] == variant
    groups = detail_groups(a)
    shelves = [g for g in groups if g['category'] == 'shelf']
    merchandise = [g for g in groups if g['category'] == 'merchandise']
    assert len(shelves) >= 2 and len(merchandise) >= 12
    assert len({g['id'] for g in merchandise}) == len(merchandise)
    assert len({i for g in merchandise for i in g['part_indices']}) >= 24
    assert all(len(g['part_indices']) >= 2 for g in merchandise)
    lo, hi = bounds(a.parts)
    assert lo[0] >= -w/2-1e-6 and hi[0] <= w/2+1e-6
    assert lo[1] >= -1e-6 and hi[1] <= 3+1e-6
    assert lo[2] >= -d/2-1e-6 and hi[2] <= d/2+1e-6
    for g in merchandise:
        lower, upper = g['bounds']['minimum'], g['bounds']['maximum']
        assert any(abs(lower[1]-s['bounds']['maximum'][1]) < .004
                   and s['bounds']['minimum'][0] <= lower[0] <= upper[0] <= s['bounds']['maximum'][0]
                   and s['bounds']['minimum'][2] <= lower[2] <= upper[2] <= s['bounds']['maximum'][2]
                   for s in shelves)
        assert lower[2] > -d/2 and upper[2] < d/2-.35  # visible from open +Z frontage
    assert not front_blocked(a.parts, d)
    assert all(part.material for part in a.parts)


def test_pose_rotates_each_combined_part_once_after_translating_items():
    from modeling.slum03.market_detail import detailed_stall
    p = sample('prosthetics', 2.5, 3.)
    zero, turned = detailed_stall(p, 260927), detailed_stall(replace(p, yaw_deg=90), 260927)
    assert zero.origin == turned.origin == p.origin
    assert len(zero.parts) == len(turned.parts)
    for first, second in zip(zero.parts, turned.parts):
        assert second.vertices == pytest.approx([rotate_y(v, math.pi/2) for v in first.vertices], abs=1e-7)


def test_seed_and_key_change_stock_placement_but_not_supports():
    from modeling.slum03.market_detail import detailed_stall
    p = sample('tools')
    a, b = detailed_stall(p, 260927), detailed_stall(p, 260928)
    assert a == detailed_stall(p, 260927) and a != b
    assert a != detailed_stall(replace(p, key='second'), 260927)
    assert [part for part in a.parts if part.name == 'shelf'] == [part for part in b.parts if part.name == 'shelf']


def test_awning_custom_faces_point_outward_and_market_front_is_open():
    from modeling.slum03.market_detail import detailed_stall
    a = detailed_stall(sample('electronics'), 260927)
    awning = next(part for part in a.parts if part.name == 'folded-awning')
    assert signed_volume(awning) > 0
    normals = [face_normal([awning.vertices[i] for i in face]) for face in awning.faces]
    assert any(n[1] > .7 for n in normals) and any(n[1] < -.7 for n in normals)
    assert not front_blocked(a.parts, 3.)
    # A solid new panel at customer height must be caught even when flat in Z.
    assert front_blocked([*a.parts, box('closed-front', (0, 1.35, 1.18),
                                       (1.5, 1.2, .08), 'steel_dark')], 3.)


def test_unknown_market_variant_rejected():
    from modeling.slum03.market_detail import detailed_stall
    with pytest.raises(ValueError, match='variant'):
        detailed_stall(sample('generic'), 260927)
