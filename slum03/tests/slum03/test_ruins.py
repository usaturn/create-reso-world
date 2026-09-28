"""Failures caught: painted windows, intact slab silhouettes, merged buildings, and route intrusion."""
from modeling.slum03.geometry import bounds, face_normal
from modeling.slum03.layout import build_layout
from modeling.slum03.materials import MATERIALS
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.spatial import placement_bounds, validate_clearance
from modeling.slum03.types import Bounds3


def _world_bounds(assembly):
    lo, hi = bounds(assembly.parts)
    return Bounds3(tuple(lo[i] + assembly.origin[i] for i in range(3)),
                   tuple(hi[i] + assembly.origin[i] for i in range(3)))


def test_each_building_has_independent_assembly():
    objects = sector_assemblies(build_layout(), 'ruins-west')
    assert len(objects) > 1
    assert len({a.name for a in objects}) == len(objects)
    assert len({a.meta['placement_key'] for a in objects}) == len(objects)
    assert all(a.meta['placement_key'] and a.parts for a in objects)


def test_ruin_has_recessed_openings_and_broken_slab():
    ruin = sector_assemblies(build_layout(), 'ruins-west')[0]
    facade = next(part for part in ruin.parts if part.name == 'facade-openings')
    # Front is the +Z plane. The central window bay is empty at the front,
    # has deep return faces, and ends in a real back wall (not painted glass).
    front = max(v[2] for v in facade.vertices)
    back = [v[2] for v in facade.vertices if abs(v[0]) < 2 and 3 < v[1] < 5]
    assert back and min(back) < front - .35
    assert not any(all(abs(facade.vertices[i][2] - front) < 1e-6 for i in face)
                   and min(facade.vertices[i][0] for i in face) < 0 < max(facade.vertices[i][0] for i in face)
                   and min(facade.vertices[i][1] for i in face) < 4 < max(facade.vertices[i][1] for i in face)
                   for face in facade.faces)
    broken = next(part for part in ruin.parts if part.name == 'broken-slab')
    edge = {(round(v[0], 2), round(v[2], 2)) for v in broken.vertices}
    assert len(edge) > 4  # a chipped concrete perimeter, not an unbroken box
    assert any(part.name == 'exposed-rebar' for part in ruin.parts)


def test_ruin_geometry_fits_canonical_footprints_and_entrances_for_multiple_seeds():
    for seed in (260927, 8195):
        layout = build_layout(seed)
        placements = {p.key: p for p in layout.placements}
        for sector in ('ruins-west', 'ruins-north', 'ruins-east'):
            for assembly in sector_assemblies(layout, sector):
                actual = _world_bounds(assembly)
                expected = placement_bounds(placements[assembly.meta['placement_key']])
                assert all(expected.minimum[i] - 1e-6 <= actual.minimum[i] <= actual.maximum[i] <= expected.maximum[i] + 1e-6
                           for i in range(3)), assembly.name
                assert not validate_clearance(layout, {assembly.name: actual})
                assert {part.material for part in assembly.parts} <= MATERIALS.keys()
        east = sector_assemblies(layout, 'ruins-east')
        assert max(_world_bounds(a).maximum[1] for a in east) < 20
        assert min(_world_bounds(a).minimum[0] for a in east) > 16


def test_broken_slab_top_faces_up():
    slab = next(p for p in sector_assemblies(build_layout(), 'ruins-west')[0].parts
                if p.name == 'broken-slab')
    top = slab.faces[1]
    assert face_normal([slab.vertices[i] for i in top])[1] > .99


def test_roof_collapse_recedes_deep_into_slab_and_is_braced():
    ruin = sector_assemblies(build_layout(), 'ruins-east')[0]
    slab = next(p for p in ruin.parts if p.name == 'broken-slab')
    front = max(v[2] for v in slab.vertices)
    # The edge has a missing multi-metre bite; not just uniform roof trim.
    assert front - min(v[2] for v in slab.vertices if v[2] > 0) > 2
    assert any(p.name == 'cantilever-brace' for p in ruin.parts)


def test_exposed_rebar_begins_inside_broken_concrete_not_outside_edge():
    from math import hypot
    for sector in ('ruins-west', 'ruins-north', 'ruins-east'):
        for building in sector_assemblies(build_layout(), sector):
            slab = next(p for p in building.parts if p.name == 'broken-slab')
            base_y = min(v[1] for v in slab.vertices)
            outline = [(slab.vertices[i][0], slab.vertices[i][2]) for i in slab.faces[0]]
            for bar in (p for p in building.parts if p.name == 'exposed-rebar'):
                x = sum(v[0] for v in bar.vertices[:6])/6
                y = sum(v[1] for v in bar.vertices[:6])/6
                z = sum(v[2] for v in bar.vertices[:6])/6
                assert base_y+.052 < y < base_y+.48-.052
                crossings = sum((az > z) != (bz > z) and
                                x < ax+(z-az)*(bx-ax)/(bz-az)
                                for (ax,az),(bx,bz) in zip(outline,outline[1:]+outline[:1]))
                assert crossings % 2 == 1, (building.name, x, z)
                # At least one full bar radius inboard of every exposed edge.
                for (ax,az),(bx,bz) in zip(outline,outline[1:]+outline[:1]):
                    t = max(0,min(1,((x-ax)*(bx-ax)+(z-az)*(bz-az))/((bx-ax)**2+(bz-az)**2)))
                    assert hypot(x-(ax+t*(bx-ax)),z-(az+t*(bz-az))) > .052


def test_upper_floors_of_taller_shell_keep_real_apertures():
    north = sector_assemblies(build_layout(), 'ruins-north')[0]
    facade = next(part for part in north.parts if part.name == 'facade-openings')
    front = max(v[2] for v in facade.vertices)
    for x, y in ((3, 19), (.4, 24)):
        assert not any(all(abs(facade.vertices[i][2]-front) < 1e-6 for i in f)
                       and min(facade.vertices[i][0] for i in f) < x < max(facade.vertices[i][0] for i in f)
                       and min(facade.vertices[i][1] for i in f) < y < max(facade.vertices[i][1] for i in f)
                       for f in facade.faces), (x, y)


def test_v2_patch_sheets_have_real_backing_and_slab_has_edge_beam():
    from modeling.slum03.architecture_detail import detailed_ruin
    from modeling.slum03.types import Placement
    def build(variant):
        return detailed_ruin(Placement('repair-test', 'ruins-west', 'ruin', (0.,0.,0.),
                                      (8.,12.,8.), 0., 'district',
                                      {'detail_profile':'v2','variant':variant}), 260927)
    bay = build('slab_bay')
    slab = next(p for p in bay.parts if p.name == 'projecting-slab')
    beam = next(p for p in bay.parts if p.name == 'under-slab-beam')
    bottom = min(v[1] for v in slab.vertices)
    assert max(v[1] for v in beam.vertices) >= bottom-.02
    patch = build('patched_facade')
    sheets = [p for p in patch.parts if p.name == 'bolted-patch']
    assert len(sheets) == 2
    anchors = [p for p in patch.parts if p.name == 'patch-fastener']
    assert len(anchors) >= 2
    for sheet in sheets:
        assert any(all(min(v[i] for v in anchor.vertices) <= max(v[i] for v in sheet.vertices)
                           and min(v[i] for v in sheet.vertices) <= max(v[i] for v in anchor.vertices)
                           for i in range(3)) for anchor in anchors)


def test_v2_service_extension_contacts_parent_pier_without_overhanging_lot():
    from modeling.slum03.architecture_detail import detailed_ruin
    from modeling.slum03.types import Placement
    p = Placement('extension-test', 'ruins-west', 'ruin', (0.,0.,0.),
                  (8.,12.,8.), 0., 'district',
                  {'detail_profile':'v2','variant':'service_core'})
    a = detailed_ruin(p, 260927)
    core = next(part for part in a.parts if part.name == 'external-service-core')
    lo, hi = bounds([core])
    assert lo[1] == 0
    rear = [part for part in a.parts if part.name == 'structural-pier'
            and min(v[2] for v in part.vertices) < -3]
    assert any(all(min(v[i] for v in post.vertices) < hi[i]
                       and max(v[i] for v in post.vertices) > lo[i]
                       for i in range(3)) for post in rear)
