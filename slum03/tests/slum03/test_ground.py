from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.geometry import bounds


def test_ground_uses_canonical_district_footprint_and_walkable_top():
    layout = build_layout()
    ground = next(a for a in sector_assemblies(layout, 'ground') if a.name == 'district-foundation')
    assert ground.meta['placement_key'] == 'district-ground'
    assert bounds(ground.parts) == ((-60, -.3, -60), (60, 0, 60))


def test_ground_local_bottom_is_taken_from_canonical_placement_not_duplicate_height():
    from dataclasses import replace
    from modeling.slum03.ground import build_assemblies
    layout = build_layout()
    changed = tuple(replace(p, origin=(5, 0, 0), size=(120, .6, 120),
                            params={**p.params, 'local_y_min': -.6})
                    if p.key == 'district-ground' else p for p in layout.placements)
    assembly = next(a for a in build_assemblies(replace(layout, placements=changed), 'ground') if a.name == 'district-foundation')
    assert assembly.origin == (5, 0, 0)
    assert bounds(assembly.parts) == ((-60, -.6, -60), (60, 0, 60))


def test_ground_and_factory_floor_have_no_overlapping_walkable_faces():
    """Both slabs may end at Y=0, but no area may have two coplanar top faces."""
    layout = build_layout()
    ground = next(a for a in sector_assemblies(layout, 'ground') if a.name == 'district-foundation')
    (factory,) = [a for a in sector_assemblies(layout, 'plaza') if a.kind == 'floor']

    def top_rects(assembly):
        from modeling.slum03.geometry import face_normal
        result = []
        for part in assembly.parts:
            for face in part.faces:
                pts = [part.vertices[i] for i in face]
                if all(abs(assembly.origin[1] + p[1]) < 1e-8 for p in pts) and face_normal(pts)[1] > .99:
                    result.append((min(p[0] + assembly.origin[0] for p in pts),
                                   max(p[0] + assembly.origin[0] for p in pts),
                                   min(p[2] + assembly.origin[2] for p in pts),
                                   max(p[2] + assembly.origin[2] for p in pts)))
        return result

    outside, inside = top_rects(ground), top_rects(factory)
    assert len(outside) >= 4 and len(inside) >= 1
    assert any(x0 <= -50 <= x1 and z0 <= 0 <= z1 for x0, x1, z0, z1 in outside)
    assert any(x0 <= 0 <= x1 and z0 <= 0 <= z1 for x0, x1, z0, z1 in inside)
    assert not any(min(ax1, bx1) > max(ax0, bx0) and min(az1, bz1) > max(az0, bz0)
                   for ax0, ax1, az0, az1 in outside
                   for bx0, bx1, bz0, bz1 in inside)


def test_owned_nonwalkable_support_covers_scenery_without_covering_river():
    # Removing scenic support reveals the default floor under the raised root.
    layout = build_layout()
    assemblies = sector_assemblies(layout, 'ground')
    supports = [a for a in assemblies if a.kind == 'scenic-support']
    assert len(supports) >= 6
    from modeling.slum03.native.colliders import collider_slots
    assert not any('scenic' in n['slot']['key'] for n in collider_slots(layout, {}))
    def covered(x, z):
        return any((lo[0]+a.origin[0] <= x <= hi[0]+a.origin[0] and
                    lo[2]+a.origin[2] <= z <= hi[2]+a.origin[2] and
                    abs(hi[1]+a.origin[1]) < 1e-7)
                   for a in supports for lo, hi in [bounds(a.parts)])
    for point in ((99, -65), (110, 0), (196, 63), (-61, 30), (-120, -90), (-110, 77), (110, 77),
                  (0, -75), (0, -145), (0, 130), (-130, 330), (25, 440), (195, 370)):
        assert covered(*point), point
    for point in ((0, 95), (110, 95), (78, 95), (61, 115), (61, -85), (0, 0), (500, 500)):
        assert not covered(*point), point


def test_forest_owned_far_edge_blocks_visible_ground_horizon():
    # Removing the rear screen exposes the pad's far edge between tree trunks.
    assemblies = sector_assemblies(build_layout(), 'ground')
    backstop = next(a for a in assemblies if a.name == 'forest-backstop')
    lo, hi = bounds(backstop.parts)
    assert lo[0] >= 210 and hi[0] >= 223 and hi[1] >= 10
    assert all(len(part.vertices) >= 36 for part in backstop.parts)
    assert lo[2] <= -87.5 and hi[2] >= 67.5
    assert backstop.meta['nonwalkable'] is True


def _full():
    from pathlib import Path
    from modeling.slum03.layout import read_layout
    return read_layout(Path('content/slum03/density-full-layout.json'))


def test_full_ground_stains_are_coplanar_surface_cells_only():
    import hashlib
    from pathlib import Path
    from modeling.slum03.layout import read_layout
    from modeling.slum03.geometry import face_normal
    legacy = next(a for a in sector_assemblies(build_layout(), 'ground') if a.name == 'district-foundation')
    layout = _full()
    ground = next(a for a in sector_assemblies(layout, 'ground') if a.name == 'district-foundation')
    # Task 11 street detail may stand above the plane (curbs <= 0.15 m); the
    # slab footprint and underside stay those of the legacy foundation.
    (lo, hi), (legacy_lo, legacy_hi) = bounds(ground.parts), bounds(legacy.parts)
    assert (lo, hi[0], hi[2]) == (legacy_lo, legacy_hi[0], legacy_hi[2])
    assert legacy_hi[1] == 0 and 0 < hi[1] <= .15
    stains = [p for p in ground.parts if p.name in ('oil-stain', 'wet-stain')]
    assert {p.material for p in stains} == {'concrete_dark', 'asphalt_wet'}
    assert all(abs(v[1]) < 1e-9 for p in stains for v in p.vertices)  # no raised decal
    # Every top face is a single-sided, non-overlapping cell covering the strips once.
    area = 0.
    cells = []
    for part in ground.parts:
        for face in part.faces:
            pts = [part.vertices[i] for i in face]
            if all(abs(p[1]) < 1e-9 for p in pts):
                assert face_normal(pts)[1] > .99
                x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
                z0, z1 = min(p[2] for p in pts), max(p[2] for p in pts)
                cells.append((x0, x1, z0, z1))
                area += (x1-x0)*(z1-z0)
    floor = next(p for p in layout.placements if p.key == 'factory-floor')
    assert abs(area - (120*120 - floor.size[0]*floor.size[2])) < 1e-3
    stain_area = sum((max(v[0] for v in [p.vertices[i] for i in f]) - min(v[0] for v in [p.vertices[i] for i in f])) *
                     (max(v[2] for v in [p.vertices[i] for i in f]) - min(v[2] for v in [p.vertices[i] for i in f]))
                     for p in stains for f in p.faces)
    assert 60 < stain_area < 400
    # Stains are placed at working frontages, never on the factory slab.
    fx0, fx1 = -floor.size[0]/2, floor.size[0]/2
    fz0, fz1 = -floor.size[2]/2, floor.size[2]/2
    for p in stains:
        for v in p.vertices:
            assert not (fx0 < v[0] < fx1 and fz0 < v[2] < fz1)
    # Legacy/representative ground keeps its exact pre-Task8 mesh.
    # 固定値の理由: 旧版と代表段階では地面のメッシュを変えない（旧版は適用済み。密度改善の設計仕様 7 章 Gate B
    # 「その他の既存内容は保持」）。値が変わったら、保護する既存内容を生成器が変えたことになる。
    rep = read_layout(Path('content/slum03/density-representative-layout.json'))
    rep_ground = next(a for a in sector_assemblies(rep, 'ground') if a.name == 'district-foundation')
    for kept in (legacy, rep_ground):
        assert hashlib.sha256(repr(kept).encode()).hexdigest() == (
            'fca0a828780b4b6253f782be1d32c012ae3de7e505e37cb4c067f88aeabfe492')
    assert not [p for p in legacy.parts if p.name in ('oil-stain', 'wet-stain')]


# --- Task 11: weathered street surface (full stage only) -------------------

import re

_DETAIL = re.compile(r'^(crack|patch|roadplate|curb|curbchunk|grate|manhole|puddle|'
                     r'oildrip|wallgrime|litter)-')
_FLAT_KINDS = ('crack', 'patch', 'roadplate', 'grate', 'manhole', 'puddle', 'oildrip', 'wallgrime')


def _full_ground():
    layout = _full()
    ground = next(a for a in sector_assemblies(layout, 'ground') if a.name == 'district-foundation')
    return layout, ground


def _world_box(assembly, part):
    ox, oy, oz = assembly.origin
    xs = [v[0] + ox for v in part.vertices]
    ys = [v[1] + oy for v in part.vertices]
    zs = [v[2] + oz for v in part.vertices]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def _by_kind(assembly):
    kinds: dict[str, list] = {}
    for part in assembly.parts:
        match = _DETAIL.match(part.name)
        if match:
            kinds.setdefault(match[1], []).append(part)
    return kinds


def _protected(layout):
    """Main routes' effective widths and authored branch clearances, from the Layout."""
    rects = [r.bounds for r in layout.routes]
    for route in layout.density.routes:
        rects.append(route.corridor.bounds)
        rects.extend(o.bounds.bounds for o in route.openings)
    rects.extend(r.bounds for r in layout.density.branch_clearances)
    return rects


def _hits(box, rect, pad=0.):
    x0, x1, _, _, z0, z1 = box
    return x0 < rect[1] + pad and x1 > rect[0] - pad and z0 < rect[3] + pad and z1 > rect[2] - pad


def test_full_street_surface_has_every_weathered_detail_kind():
    layout, ground = _full_ground()
    kinds = _by_kind(ground)
    minimum = {'crack': 40, 'patch': 8, 'roadplate': 3, 'curb': 40, 'curbchunk': 3, 'grate': 4,
               'manhole': 4, 'puddle': 8, 'oildrip': 10, 'wallgrime': 12, 'litter': 30}
    assert {k: len(kinds.get(k, ())) >= n for k, n in minimum.items()} == {k: True for k in minimum}
    # Asphalt road surface sits exactly in the ground plane on the three main streets only.
    from modeling.slum03.geometry import face_normal
    def surface_at(x, z):
        for part in ground.parts:
            for face in part.faces:
                pts = [part.vertices[i] for i in face]
                if (all(abs(p[1]) < 1e-9 for p in pts) and face_normal(pts)[1] > .99 and
                        min(p[0] for p in pts) <= x <= max(p[0] for p in pts) and
                        min(p[2] for p in pts) <= z <= max(p[2] for p in pts)):
                    return part.material
    assert surface_at(-40.3, 0.2) == surface_at(40.3, -0.2) == surface_at(0.2, -40.3) == 'asphalt'
    assert surface_at(-40.3, 20.3) == 'concrete_raw'
    # Branch lanes (枝道) carry detail too, not only the main streets.
    for route in layout.density.routes:
        c = route.corridor
        inside = [p for k in ('crack', 'patch', 'puddle', 'oildrip') for p in kinds[k]
                  if _hits(_world_box(ground, p), c.bounds)]
        assert inside, route.key
    # Detail stays on streets/lanes and their building edges, never on the factory slab.
    floor = next(p for p in layout.placements if p.key == 'factory-floor')
    fx, fz = floor.size[0]/2, floor.size[2]/2
    streets = [r.bounds for r in layout.routes] + [r.corridor.bounds for r in layout.density.routes]
    for parts in kinds.values():
        for part in parts:
            box = _world_box(ground, part)
            assert not _hits(box, (-fx, fx, -fz, fz)), part.name
            assert -60 <= box[0] and box[1] <= 60 and -60 <= box[4] and box[5] <= 60, part.name
            assert any(_hits(box, r, 4.5) for r in streets), part.name


def test_full_street_detail_keeps_main_routes_walkable_by_geometry():
    layout, ground = _full_ground()
    kinds = _by_kind(ground)
    protected = _protected(layout)
    for kind in _FLAT_KINDS:
        for part in kinds[kind]:
            box = _world_box(ground, part)
            assert box[3] < 0.01 and box[2] > -0.3, (part.name, box[3])  # step below 0.01 m
    for part in ground.parts:
        box = _world_box(ground, part)
        if box[3] < 0.01:
            continue
        # Anything standing 0.01 m or more is outside every effective width and clearance.
        assert _DETAIL.match(part.name), part.name
        assert not any(_hits(box, r) for r in protected), part.name
    for part in kinds['litter']:
        assert _world_box(ground, part)[3] <= 0.10, part.name
    # Detail is mesh-only: no new objects (hence no new collider owners) in the ground sector.
    legacy = {a.name for a in sector_assemblies(build_layout(), 'ground')}
    assert {a.name for a in sector_assemblies(layout, 'ground')} == legacy


def test_full_street_detail_is_seeded_and_bounded():
    import hashlib
    from dataclasses import replace
    layout, ground = _full_ground()
    again = next(a for a in sector_assemblies(_full(), 'ground') if a.name == 'district-foundation')
    assert repr(again) == repr(ground)
    other = next(a for a in sector_assemblies(replace(layout, seed=layout.seed + 1), 'ground')
                 if a.name == 'district-foundation')
    assert hashlib.sha256(repr(other).encode()).digest() != hashlib.sha256(repr(ground).encode()).digest()
    triangles = sum(len(f) - 2 for p in ground.parts for f in p.faces)
    assert triangles < 20000
    assert len({p.material for p in ground.parts}) <= 14


def test_full_small_street_debris_stays_off_entrance_aprons_and_shop_fronts():
    """Litter and curb fragments never lie on a nightlife apron or a stall front (Task 11 review)."""
    from modeling.slum03.ground import _stains
    from modeling.slum03.surface_detail import FRONTAGE_PAD
    layout, ground = _full_ground()
    ox, _, oz = ground.origin
    fronts = [(r[0] + ox, r[1] + ox, r[2] + oz, r[3] + oz)
              for r, p in zip(_stains(layout, ox, oz),
                              (p for p in layout.placements
                               if p.params.get('detail_profile') == 'v2'
                               and p.kind in ('stall', 'nightlife', 'shack')))
              if p.kind in ('stall', 'nightlife')]
    assert len(fronts) >= 8  # every remodelled stall and nightlife frontage
    # Stall aprons (fix round 1): the customer strip from the counter front (local
    # z = d/2) out to d/2 + 1.0 across the stall width, computed here independently.
    import math
    for p in layout.placements:
        if p.params.get('detail_profile') != 'v2' or p.kind != 'stall':
            continue
        w, _, d = p.size
        a = math.radians(p.yaw_deg)
        corners = [(p.origin[0] + lx*math.cos(a) + lz*math.sin(a),
                    p.origin[2] - lx*math.sin(a) + lz*math.cos(a))
                   for lx in (-w/2, w/2) for lz in (d/2, d/2 + 1.0)]
        fronts.append((min(c[0] for c in corners), max(c[0] for c in corners),
                       min(c[1] for c in corners), max(c[1] for c in corners)))
    assert len(fronts) >= 8 + 28
    kinds = _by_kind(ground)
    small = kinds['litter'] + kinds['curbchunk']
    assert len(kinds['litter']) >= 30
    offenders = [part.name for part in small
                 if any(_hits(_world_box(ground, part), f, FRONTAGE_PAD) for f in fronts)]
    assert offenders == []


def test_local_rect_rejects_yaw_that_is_not_a_multiple_of_90():
    import pytest
    from modeling.slum03.ground import _local_rect
    from modeling.slum03.types import Placement
    def at(yaw):
        return Placement('p', 'market', 'stall', (0., 0., 0.), (2., 2., 2.), yaw, 'district')
    _local_rect(at(90.), (1., 0.), (2., 1.), 0., 0.)
    _local_rect(at(-180.), (1., 0.), (2., 1.), 0., 0.)
    with pytest.raises(ValueError, match='multiple of 90'):
        _local_rect(at(45.), (1., 0.), (2., 1.), 0., 0.)
