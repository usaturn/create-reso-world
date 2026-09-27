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
