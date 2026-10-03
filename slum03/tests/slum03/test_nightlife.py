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


def _front_ray_hits(parts, start, direction, max_distance):
    # Actual triangle intersections, not placement AABBs or a wall part name.
    def dot(a, b):
        return sum(x*y for x,y in zip(a,b))
    def sub(a,b):
        return tuple(x-y for x,y in zip(a,b))
    def cross(a,b):
        return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    for part in parts:
        for face in part.faces:
            for i in range(1, len(face)-1):
                a,b,c = (part.vertices[j] for j in (face[0], face[i], face[i+1]))
                edge, other = sub(b,a), sub(c,a)
                h = cross(direction,other)
                det = dot(edge,h)
                if abs(det) < 1e-9:
                    continue
                rel = sub(start,a)
                u = dot(rel,h)/det
                if not -1e-7 <= u <= 1+1e-7:
                    continue
                q = cross(rel,edge)
                v = dot(direction,q)/det
                if v < -1e-7 or u+v > 1+1e-7:
                    continue
                distance = dot(other,q)/det
                if 0 < distance <= max_distance:
                    return True
    return False


def test_nightlife_front_has_no_walkthrough_gap_at_eye_or_upper_storey_height():
    for facade in sector_assemblies(build_layout(), 'nightlife'):
        for height in (.5, 1.4, 2.5, 3.75, 4.1, 6, 10):
            for x in (-2.25, -2, -1.7, 0, 1.7, 2, 2.25):
                assert _front_ray_hits(facade.parts, (x,height,8.1), (0,0,-1), 1.35), (facade.name,height,x)


def test_nightlife_side_walls_close_both_external_perimeters():
    for facade in sector_assemblies(build_layout(), 'nightlife'):
        for sign in (-1,1):
            for height in (1.5, 6, 9.5):
                for z in (-5,0,5):
                    assert _front_ray_hits(facade.parts, (sign*3.15,height,z), (-sign,0,0), .9), (facade.name,sign,height,z)


def test_nightlife_shell_has_a_supported_roof_not_open_sky():
    for facade in sector_assemblies(build_layout(), 'nightlife'):
        for x in (-2.2, 0, 2.2):
            for z in (-5, 0, 5):
                assert _front_ray_hits(facade.parts, (x,11.25,z), (0,-1,0), .9), (facade.name,x,z)


# --- Task 8: v2 storefronts across the east lane and southeast market edge ---

from collections import Counter
from pathlib import Path

import pytest

from modeling.slum03.layout import read_layout

FULL = Path('content/slum03/density-full-layout.json')


def _full_fronts():
    layout = read_layout(FULL)
    fronts = [a for sector in ('nightlife', 'market') for a in sector_assemblies(layout, sector)
              if a.kind == 'nightlife']
    return layout, fronts


def _group_parts(a, identifier):
    group = next(g for g in a.meta['detail_groups'] if g['id'] == identifier)
    return [a.parts[i] for i in group['part_indices']]


def test_all_eight_v2_storefronts_generate_with_real_groups():
    from modeling.slum03.detail_evidence import detail_groups
    layout, fronts = _full_fronts()
    placements = {p.key: p for p in layout.placements}
    assert len(fronts) == 8 and len({a.name for a in fronts}) == 8
    for a in fronts:
        p = placements[a.name]
        assert p.params['detail_profile'] == 'v2'
        assert a.meta['placement_key'] == p.key and a.meta['variant'] == p.params['variant']
        categories = Counter(g['category'] for g in detail_groups(a))
        assert categories['architecture'] >= 3
        assert categories['utility'] >= 1 and categories['lived_in'] >= 1
        ids = {g['id'] for g in a.meta['detail_groups']}
        assert {'entrance', 'canopy', 'signage', 'frontage-lighting'} <= ids, a.name


def test_storefront_variants_change_entrance_canopy_lighting_and_equipment_not_colour():
    from modeling.slum03.nightlife import NIGHTLIFE_VARIANTS, detailed_nightlife
    from modeling.slum03.types import Placement
    signatures = {}
    for variant in NIGHTLIFE_VARIANTS:
        p = Placement('probe-front', 'nightlife', 'nightlife', (0., 0., 0.), (8., 8., 8.), 0.,
                      'district', {'detail_profile': 'v2', 'variant': variant,
                                   'density_zone': 'east', 'cluster': 'east-row-0'})
        a = detailed_nightlife(p, 260927)
        shape = []
        for identifier in ('entrance', 'canopy', 'frontage-lighting', 'wall-equipment'):
            parts = _group_parts(a, identifier)
            shape.append(tuple(sorted((part.name, len(part.faces),
                                       tuple(round(v, 3) for v in bounds([part])[1]))
                                      for part in parts)))
        signatures[variant] = tuple(shape)
    assert len(NIGHTLIFE_VARIANTS) == 4
    for index in range(4):  # every component system differs across all four variants
        assert len({sig[index] for sig in signatures.values()}) == 4, index


def test_v2_storefront_parts_fit_site_and_stay_off_protected_air():
    from modeling.slum03.materials import MATERIALS
    layout, fronts = _full_fronts()
    placements = {p.key: p for p in layout.placements}
    for a in fronts:
        site = placement_bounds(placements[a.name])
        for part in a.parts:
            lo, hi = bounds([part])
            real = Bounds3(tuple(lo[i]+a.origin[i] for i in range(3)),
                           tuple(hi[i]+a.origin[i] for i in range(3)))
            assert all(site.minimum[i]-1e-6 <= real.minimum[i] <= real.maximum[i]
                       <= site.maximum[i]+1e-6 for i in range(3)), (a.name, part.name)
            assert not validate_clearance(layout, {a.name: real}), (a.name, part.name)
            assert part.material in MATERIALS


def test_v2_storefront_is_closed_exterior_with_supported_canopy():
    from modeling.slum03.nightlife import NIGHTLIFE_VARIANTS, detailed_nightlife
    from modeling.slum03.types import Placement
    for variant in NIGHTLIFE_VARIANTS:
        for size in ((8., 8., 8.), (6., 11., 16.)):
            p = Placement('probe-front', 'nightlife', 'nightlife', (0., 0., 0.), size, 0.,
                          'district', {'detail_profile': 'v2', 'variant': variant})
            a = detailed_nightlife(p, 260927)
            w, h, d = size
            # No walk-in gap through the entrance at any height (closed exterior).
            for height in (.5, 1.4, 2.5):
                for x in (-1.2, 0, 1.2):
                    assert _front_ray_hits(a.parts, (x, height, d/2), (0, 0, -1), 1.6), (variant, size, x, height)
            # The canopy touches the facade structure it hangs from.
            canopy = _group_parts(a, 'canopy')
            structure = [part for g in a.meta['detail_groups'] if g['category'] == 'architecture'
                         for part in (a.parts[i] for i in g['part_indices'])]
            assert all(any(_overlap(c, s) for s in structure + canopy if s is not c)
                       for c in canopy), variant
            assert max(v[1] for part in canopy for v in part.vertices) <= 3.15


def test_existing_storefront_signs_stay_readable_in_front_of_v2_fascia():
    layout, fronts = _full_fronts()
    for key in ('nightlife-east', 'nightlife-velvet'):
        a = next(f for f in fronts if f.name == key)
        label = next(l for l in layout.labels if l.parent_name == key)
        x, y, z = label.offset
        for part in a.parts:
            lo, hi = bounds([part])
            if lo[0] <= x <= hi[0] and lo[1]-.35 <= y <= hi[1]+.35 and part.name not in ('neon-tube',):
                assert hi[2] < z, (key, part.name)


def test_unknown_storefront_variant_fails_closed():
    from modeling.slum03.nightlife import detailed_nightlife
    from modeling.slum03.types import Placement
    p = Placement('probe-front', 'nightlife', 'nightlife', (0., 0., 0.), (8., 8., 8.), 0.,
                  'district', {'detail_profile': 'v2', 'variant': 'explicit-club'})
    with pytest.raises(ValueError, match='variant'):
        detailed_nightlife(p, 260927)


def test_existing_v2_storefront_keeps_owned_collider_key_on_real_part():
    from dataclasses import replace
    from modeling.slum03.density_metrics import layout_digest
    from modeling.slum03.evaluated_detail import observe_detail
    from modeling.slum03.geometry import merge_assembly
    from modeling.slum03.native.colliders import collider_slots
    from modeling.slum03.nightlife import detailed_nightlife
    base = build_layout()
    old = {b['slot']['key']: b for b in collider_slots(base, {})}
    p = next(p for p in base.placements if p.key == 'nightlife-east')
    p = replace(p, params={**p.params, 'detail_profile': 'v2', 'variant': 'nightlife-2'})
    layout = replace(base, placements=tuple(p if q.key == p.key else q for q in base.placements))
    a = detailed_nightlife(p, layout.seed)
    m = merge_assembly(a)
    obj = observe_detail(a, {'vertices': [tuple(v[i]+p.origin[i] for i in range(3)) for v in m.vertices],
                             'faces': m.faces})
    obj['detail_profile'] = 'v2'
    boxes = collider_slots(layout, {p.sector: {'layout_sha256': layout_digest(layout), 'objects': [obj],
                                               'evaluated_bounds': {obj['mesh']: obj['evaluated_bounds']}}})
    keys = [b['slot']['key'] for b in boxes]
    assert keys.count('collider-nightlife-east') == 1 and len(keys) == len(set(keys))
    kept = next(b for b in boxes if b['slot']['key'] == 'collider-nightlife-east')
    assert kept['components'][0]['fields']['Size'] != old['collider-nightlife-east']['components'][0]['fields']['Size']
