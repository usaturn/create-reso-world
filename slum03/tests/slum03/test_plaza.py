from modeling.slum03.geometry import bounds, face_normal
from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import sector_assemblies


def test_plaza_has_flat_floor_and_north_wall_but_no_east_wall():
    assemblies = sector_assemblies(build_layout(), 'plaza')
    by_key = {a.meta['placement_key']: a for a in assemblies}
    assert set(by_key) == {'factory-floor', 'north-wall'}
    assert bounds(by_key['factory-floor'].parts) == ((-20, -.2, -15), (20, 0, 15))
    wall = by_key['north-wall']
    assert wall.origin == (0, 0, 14.5)
    assert sum(p.name == 'pour-seam' for p in wall.parts) >= 2
    assert bounds(wall.parts)[0][0] == -18
    assert any(face_normal([p.vertices[i] for i in face])[2] < -.99
               for p in wall.parts for face in p.faces)


def test_generated_plaza_reopens_with_editable_scatter_and_static_uv_color_exports(tmp_path):
    import json
    import subprocess
    blend = tmp_path / 'plaza.blend'
    subprocess.run(['resoloop', 'blender', 'run', 'modeling/slum03/build.py',
                    '--arg=--sector', '--arg=plaza', '--arg=--output', f'--arg={blend}', '--json'],
                   check=True, capture_output=True, text=True)
    probe = tmp_path / 'probe.json'
    subprocess.run(['resoloop', 'blender', 'run', 'tests/slum03/blender_plaza_probe.py',
                    '--blend', str(blend), f'--arg={probe}', '--json'],
                   check=True, capture_output=True, text=True)
    data = json.loads(probe.read_text())
    report = json.loads((tmp_path / 'plaza-report.json').read_text())
    assert report['errors'] == report['uv_issues'] == []
    assert data['source_hidden_in_render']
    assert data['graffiti_text'] == '稲垣は絶対マカぶる'
    assert data['graffiti_facing_blender'] == [0, -1, 0]
    assert data['wall_south_normals'] and len(data['wall_south_normals']) >= 3
    assert data['graffiti_uv'] == ['UV0'] and data['font_packed']
    assert data['red_mesh_south_normals'] > 0 and data['red_mesh_polygons'] > 200
    assert -18 < data['letter_x_span'][0] < 0 < data['letter_x_span'][1] < 18
    assert {'Slum03_spray_red', 'Slum03_spray_black'} <= set(data['graffiti_materials'])
    assert len(data['red_streaks']) >= 5
    assert all(offset is not None and 0 <= offset <= .09
               for offset in data['drip_offsets_from_glyph_base'])
    assert len(data['overspray_x_gap']) >= 4
    assert all(gap < .6 for gap in data['overspray_x_gap'])
    assert all(data['red_y_span'][0]-.35 <= y <= data['red_y_span'][1]+.35
               for y in data['overspray_y'])
    assert 'Slum03_asphalt_wet' in data['floor_materials']  # inlaid oil, not an obstacle
    assert 'Slum03_steel_dark' in data['variant_materials']['rubble-variant-1']
    assert 'Slum03_electronics' in data['variant_materials']['rubble-variant-2']
    assert data['scale_linked']
    assert sum(.45 <= s <= .72 for s in data['rubble_scales']) >= 10
    assert sum(.9 <= s <= 1.15 for s in data['rubble_scales']) >= 8
    assert sum(1.3 <= s <= 1.58 for s in data['rubble_scales']) >= 6
    assert set(data['rubble_variants']) == {0, 1, 2}
    assert data['truss_variant_span'][0] >= 2 and data['truss_variant_span'][1] >= 1
    assert 'Slum03_steel_bare' in data['realized_rubble_materials']
    assert data['rubble_source_count'] >= 4
    assert data['rubble_source_count'] == data['rubble_export_count']
    assert all(m == ['NODES'] for m in data['source_modifiers'])
    assert {'GeometryNodeInstanceOnPoints', 'GeometryNodeObjectInfo',
           } <= set(data['source_node_types'])
    assert all(not mods for mods in data['export_modifiers'])
    assert all(faces > 20 for faces in data['export_faces'])
    assert all('UV0' in uvs for uvs in data['export_uvs'])
    assert all('Col' in colors for colors in data['export_colors'])
    rubble_heights = [b['maximum'][1] - b['minimum'][1]
                      for k, b in report['evaluated_bounds'].items() if k.startswith('plaza-rubble-')]
    assert min(rubble_heights) < .8 and max(rubble_heights) > 1.8
    for name, bounds in report['evaluated_bounds'].items():
        if name.startswith('plaza-rubble-'):
            x0, y0, z0 = bounds['minimum']; x1, y1, z1 = bounds['maximum']
            assert y0 >= -0.001 and y1 > 0
            assert x1-x0 <= 6.5 and z1-z0 <= 6.5  # small editable heaps
            assert x1 <= -16 or x0 >= 16 or z0 >= 11 or z1 <= -11
    assert len(report['objects']) == len(data['export_names'])
    from modeling.slum03.types import Bounds3
    from modeling.slum03.spatial import validate_clearance
    evaluated = {key: Bounds3(tuple(bounds['minimum']), tuple(bounds['maximum']))
                 for key, bounds in report['evaluated_bounds'].items() if key != 'factory-floor'}
    assert not validate_clearance(build_layout(), evaluated)  # includes upper 3m and all entrances
    for key, bounds in report['rubble_evaluated_bounds'].items():
        assert report['evaluated_bounds'][key] == bounds


# --- Task 12: weathered factory floor (full stage only) ---------------------

def _full():
    from pathlib import Path
    from modeling.slum03.layout import read_layout
    return read_layout(Path('content/slum03/density-full-layout.json'))


def _floor(layout):
    return next(a for a in sector_assemblies(layout, 'plaza') if a.meta['placement_key'] == 'factory-floor')


def _kind(part):
    return part.name.split('-')[0]


def test_legacy_and_staged_plaza_geometry_is_unchanged():
    import hashlib
    from pathlib import Path
    from modeling.slum03.layout import read_layout
    for layout in (build_layout(), read_layout(Path('content/slum03/density-representative-layout.json')),
                   read_layout(Path('content/slum03/density-blockout-layout.json'))):
        assemblies = sector_assemblies(layout, 'plaza')
        assert hashlib.sha256(repr(assemblies).encode()).hexdigest() == (
            'f68e3f32bded06bd7a261749c4764b98c7ae56fdd636f9772ca8835b59a56cca')


def test_full_factory_floor_has_cracks_pits_machine_bases_and_damp_margins():
    from collections import Counter
    from modeling.slum03.plaza import PIT_DEPTH_MAX
    layout = _full()
    floor = _floor(layout)
    kinds = Counter(_kind(p) for p in floor.parts)
    assert kinds['crack'] >= 20
    assert len({p.name.split('-')[1] for p in floor.parts if _kind(p) == 'pit'}) >= 5
    assert len({p.name.split('-')[1] for p in floor.parts if _kind(p) == 'base'}) >= 4
    assert sum(p.name.startswith('base-') and '-bolt-' in p.name for p in floor.parts) >= 16
    assert kinds['damp'] >= 12
    materials = {p.material for p in floor.parts}
    assert {'factory_floor', 'concrete_dark', 'mud', 'asphalt_wet', 'rust_dark'} <= materials
    # Pits are shallow dishes: the flat walking collider and footing are unaffected.
    assert 0 < PIT_DEPTH_MAX <= .05
    for part in floor.parts:
        if _kind(part) == 'pit':
            assert min(v[1] for v in part.vertices) >= -PIT_DEPTH_MAX - 1e-9, part.name


def test_full_factory_floor_stays_a_flush_walkable_surface():
    from modeling.slum03.geometry import bounds as part_bounds
    from modeling.slum03.spatial import WALKABLE_DECAL_MAX, validate_clearance
    from modeling.slum03.types import Bounds3
    layout = _full()
    floor = _floor(layout)
    lo, hi = part_bounds(floor.parts)
    assert (lo[0], lo[1], lo[2], hi[0], hi[2]) == (-20, -.2, -15, 20, 15)
    assert 0 < hi[1] <= WALKABLE_DECAL_MAX  # decals only; no step anywhere on the slab
    assert validate_clearance(layout, {'factory-floor': Bounds3(lo, hi)}) == []
    # Pits and base traces stay off the main-route effective widths (entrances included).
    for part in floor.parts:
        if _kind(part) not in ('pit', 'base'):
            continue
        xs = [v[0] for v in part.vertices]; zs = [v[2] for v in part.vertices]
        for r in layout.routes:
            assert not (min(xs) < r.x_max and max(xs) > r.x_min and
                        min(zs) < r.z_max and max(zs) > r.z_min), part.name
    # Seeded: the same Layout repeats, another seed moves the weathering.
    from dataclasses import replace
    assert repr(_floor(_full())) == repr(floor)
    assert repr(_floor(replace(layout, seed=layout.seed + 1))) != repr(floor)


def test_full_colliders_leave_central_floor_and_air_to_the_flat_slab():
    from dataclasses import replace
    from modeling.slum03.native.colliders import collider_slots
    layout = _full()
    # v2 shells need their measured sector reports; as plain boxes they stay outside
    # the clear area anyway. Every other collider source is the real full Layout.
    plain = replace(layout, placements=tuple(
        replace(p, params={k: v for k, v in p.params.items() if k != 'detail_profile'})
        for p in layout.placements))
    boxes = collider_slots(plain, {})
    assert 'collider-factory-floor' in {n['slot']['key'] for n in boxes}
    for n in boxes:
        if n['slot']['key'] == 'collider-factory-floor':
            continue
        p = n['slot']['position']; size = n['components'][0]['fields']['Size']
        x0, x1 = p[0]-size[0]/2, p[0]+size[0]/2
        z0, z1 = p[2]-size[2]/2, p[2]+size[2]/2
        y0, y1 = p[1]-size[1]/2, p[1]+size[1]/2
        if (x0 < layout.clear.x_max and x1 > layout.clear.x_min and
                z0 < layout.clear.z_max and z1 > layout.clear.z_min and y1 > 0 and y0 < 3):
            raise AssertionError(n['slot']['key'])
        assert 'rubble' not in n['slot']['key']


def test_full_plaza_build_realizes_only_walkable_debris_on_the_central_floor(tmp_path):
    """Evaluated (post Geometry Nodes realization) geometry, not plan metadata."""
    import json
    import subprocess
    from modeling.slum03.density_model import FLOOR_DEBRIS_MAX, FLOOR_DEBRIS_PREFIX
    from modeling.slum03.native.colliders import collider_slots
    from modeling.slum03.spatial import WALKABLE_DECAL_MAX, validate_clearance
    from modeling.slum03.types import Bounds3
    blend = tmp_path / 'plaza.blend'
    subprocess.run(['resoloop', 'blender', 'run', 'modeling/slum03/build.py',
                    '--arg=--sector', '--arg=plaza', '--arg=--layout',
                    '--arg=content/slum03/density-full-layout.json',
                    '--arg=--output', f'--arg={blend}', '--json'],
                   check=True, capture_output=True, text=True)
    probe = tmp_path / 'probe.json'
    subprocess.run(['resoloop', 'blender', 'run', 'tests/slum03/blender_floor_debris_probe.py',
                    '--blend', str(blend), f'--arg={probe}', '--json'],
                   check=True, capture_output=True, text=True)
    data = json.loads(probe.read_text())
    report = json.loads((tmp_path / 'plaza-report.json').read_text())
    assert report['errors'] == report['uv_issues'] == []
    layout = _full()
    clear = layout.clear
    bounds = report['evaluated_bounds']
    floor_heaps = [k for k in bounds if k.startswith(FLOOR_DEBRIS_PREFIX + '-')]
    assert 8 <= len(floor_heaps) <= 16
    for key, b in bounds.items():
        lo, hi = b['minimum'], b['maximum']
        over_clear = (lo[0] < clear.x_max and hi[0] > clear.x_min and
                      lo[2] < clear.z_max and hi[2] > clear.z_min and hi[1] > 0 and lo[1] < 3)
        if key == 'factory-floor':
            assert hi[1] <= WALKABLE_DECAL_MAX
        elif key in floor_heaps:
            assert hi[1] <= FLOOR_DEBRIS_MAX and lo[1] >= -.01, (key, lo, hi)
        else:
            assert not over_clear, key  # medium+ rubble and walls stay off the floor and its air
    evaluated = {k: Bounds3(tuple(b['minimum']), tuple(b['maximum'])) for k, b in bounds.items()}
    assert validate_clearance(layout, evaluated) == []
    # The Blender-realized heaps are exactly the planned variants (index order, scale, yaw).
    from modeling.slum03.gn_scatter import realize_instance, scatter_plan
    for name, items in scatter_plan(layout).items():
        verts = [v for item in items for part in realize_instance(item) for v in part.vertices]
        planned = [[min(v[i] for v in verts) for i in range(3)], [max(v[i] for v in verts) for i in range(3)]]
        real = bounds[f'plaza-rubble-{name}']
        for axis in range(3):
            assert abs(real['minimum'][axis] - planned[0][axis]) < 1e-4, (name, axis)
            assert abs(real['maximum'][axis] - planned[1][axis]) < 1e-4, (name, axis)
    # Every loose piece of the realized debris, measured on the exported mesh.
    pieces = data['floor_pieces']
    assert len(pieces) >= 450
    assert max(p['height'] for p in pieces) <= FLOOR_DEBRIS_MAX
    assert all(p['top'] <= FLOOR_DEBRIS_MAX + 1e-6 for p in pieces)
    assert data['floor_sources_have_nodes'] and data['floor_exports_static']
    # Fix round 1: the realized debris covers every open 4 m square of the floor.
    from tests.slum03.test_scatter import floor_coverage
    cells = floor_coverage(layout, [(p['x'], p['z'], p['long']) for p in pieces])
    assert len(cells) >= 40 and min(c['pieces'] for c in cells) >= 4
    assert max(p['long'] for p in pieces) <= .7
    # The flat slab collider still fits inside the (decal-raised) evaluated floor.
    from dataclasses import replace
    plain = replace(layout, placements=tuple(
        replace(p, params={k: v for k, v in p.params.items() if k != 'detail_profile'})
        for p in layout.placements))
    keys = {n['slot']['key'] for n in collider_slots(plain, {'plaza': report})}
    assert 'collider-factory-floor' in keys and not any('rubble' in k for k in keys)


def test_full_factory_floor_character_reads_at_eye_height():
    """Fix round 1: branching wider cracks and broad, high-contrast tone patches (flush)."""
    import math
    from modeling.slum03.materials import MATERIALS
    layout = _full()
    floor = _floor(layout)
    mains = [p for p in floor.parts if _kind(p) == 'crack' and '-b' not in p.name]
    branches = [p for p in floor.parts if _kind(p) == 'crack' and '-b' in p.name]
    assert len(mains) >= 25 and len(branches) >= 25
    widths = []
    for part in mains:
        k = len(part.vertices) // 4 * 2
        a, b = part.vertices[k], part.vertices[k + 1]
        widths.append(math.dist((a[0], a[2]), (b[0], b[2])))
    assert min(widths) >= .04 and sum(widths) / len(widths) >= .055
    stains = [p for p in floor.parts if _kind(p) == 'stain']
    assert len(stains) >= 24

    def area(part):
        total = 0.
        for face in part.faces:
            pts = [(part.vertices[i][0], part.vertices[i][2]) for i in face]
            total += abs(sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2
        return total
    assert sum(area(p) for p in stains) >= 150 and min(area(p) for p in stains) >= 1.
    # Contrast against the slab colour: darker, wetter and lighter patches all occur.
    slab = sum(MATERIALS['factory_floor'].base_color[:3]) / 3
    tones = {p.material for p in stains}
    assert len(tones) >= 4
    lum = [sum(MATERIALS[m].base_color[:3]) / 3 for m in tones]
    assert min(lum) < slab * .5 and max(lum) > slab * 1.2
    assert all(max(v[1] for v in p.vertices) < .002 for p in stains)  # flush, no step
    # Same-level tone patches never overlap (z-fighting) and stay on the slab.
    discs = [(p.vertices[0], max(math.dist((p.vertices[0][0], p.vertices[0][2]), (v[0], v[2]))
                                 for v in p.vertices)) for p in stains]
    for i, (a, ra) in enumerate(discs):
        for b, rb in discs[i + 1:]:
            assert math.dist((a[0], a[2]), (b[0], b[2])) > ra + rb
    plaza = layout.plaza
    ox, oz = (plaza.x_min + plaza.x_max) / 2, (plaza.z_min + plaza.z_max) / 2
    for p in stains:
        assert all(plaza.x_min - ox <= v[0] <= plaza.x_max - ox and
                   plaza.z_min - oz <= v[2] <= plaza.z_max - oz for v in p.vertices)
    halos = [p for p in floor.parts if p.name.endswith('-halo')]
    assert len(halos) >= 20
    damp_levels = {round(v[1], 5) for p in floor.parts if _kind(p) == 'damp' for v in p.vertices}
    assert {round(v[1], 5) for p in halos for v in p.vertices}.isdisjoint(damp_levels)
