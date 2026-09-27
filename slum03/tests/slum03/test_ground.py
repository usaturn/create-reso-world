from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.geometry import bounds


def test_ground_uses_canonical_district_footprint_and_walkable_top():
    layout = build_layout()
    (ground,) = sector_assemblies(layout, 'ground')
    assert ground.meta['placement_key'] == 'district-ground'
    assert bounds(ground.parts) == ((-60, -.3, -60), (60, 0, 60))


def test_ground_local_bottom_is_taken_from_canonical_placement_not_duplicate_height():
    from dataclasses import replace
    from modeling.slum03.ground import build_assemblies
    layout = build_layout()
    changed = tuple(replace(p, origin=(5, 0, 0), size=(120, .6, 120),
                            params={**p.params, 'local_y_min': -.6})
                    if p.key == 'district-ground' else p for p in layout.placements)
    (assembly,) = build_assemblies(replace(layout, placements=changed), 'ground')
    assert assembly.origin == (5, 0, 0)
    assert bounds(assembly.parts) == ((-60, -.6, -60), (60, 0, 60))


def test_ground_and_factory_floor_have_no_overlapping_walkable_faces():
    """Both slabs may end at Y=0, but no area may have two coplanar top faces."""
    layout = build_layout()
    (ground,) = sector_assemblies(layout, 'ground')
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
