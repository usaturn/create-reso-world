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


def test_scenic_pads_are_dark_distinct_from_default_floor():
    supports = {a.name: a for a in sector_assemblies(build_layout(), 'ground')
                if a.kind == 'scenic-support'}
    assert supports['scenic-support-forest'].parts[0].material == 'mud'
    assert supports['scenic-support-west'].parts[0].material == 'backdrop_ground'
    assert supports['scenic-support-south'].parts[0].material == 'backdrop_ground'
