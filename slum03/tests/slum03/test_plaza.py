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
