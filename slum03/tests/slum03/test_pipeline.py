"""Merge contract: changing source bytes, reference mapping, or output base must break these tests."""
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest
from modeling.slum03 import pipeline


def _bundle(directory, name, *, mesh=b'first', material=None):
    directory.mkdir(parents=True)
    (directory / 'mesh_a.mesh.json').write_bytes(mesh)
    material = material or {'AlbedoColor': [1, 0, 0, 1]}
    payload = {
        'schemaVersion': '1', 'ownership': {'key': 'blender_' + name},
        'slot': {'key': 'root', 'name': name, 'parent': 'Root'},
        'assets': {'mesh_a': {'kind': 'mesh', 'source': 'mesh_a.mesh.json'}},
        'components': [],
        'children': [
            {'slot': {'key': 'object_a', 'name': name + '_fixed'}, 'children': [
                {'slot': {'key': 'object_driven', 'name': name + '_driven',
                          'position': [0, 1, 0]}, 'components': [
                    {'key': 'mesh_a', 'type': 'FrooxEngine.StaticMesh', 'fields': {'URL': '$asset:mesh_a'}},
                    {'key': 'renderer_a', 'type': 'FrooxEngine.MeshRenderer',
                     'fields': {'Mesh': '$component:mesh_a', 'Materials': ['$component:mat_a', '$component:mat_b']}},
                    {'key': 'driver_a', 'type': 'FrooxEngine.Spinner',
                     'fields': {'_target': '$slot-member:object_driven.Rotation',
                                'Anchor': '$slot:object_a', 'Source': '$member:mat_a.AlbedoColor'}},
                ]}]},
            {'slot': {'key': 'providers', 'name': 'Blender_Providers'}, 'children': [
                {'slot': {'key': 'provider_mat_a', 'name': 'material_a'}, 'components': [
                    {'key': 'mat_a', 'type': 'FrooxEngine.PBS_Metallic', 'fields': material}]},
                {'slot': {'key': 'provider_mat_b', 'name': 'material_b'}, 'components': [
                    {'key': 'mat_b', 'type': 'FrooxEngine.PBS_Metallic', 'fields': {'AlbedoColor': [0, 1, 0, 1]}}]},
            ]},
        ],
    }
    (directory / 'model.apply.json').write_text(json.dumps(payload), encoding='utf-8')
    return payload


def _nodes(m):
    def walk(n):
        yield n
        for c in n.get('children', []):
            yield from walk(c)
    return list(walk(m))


def _setup(tmp_path, monkeypatch, *, second=b'second'):
    monkeypatch.setattr(pipeline, 'SECTORS', ('ground', 'plaza'))
    directory = tmp_path / 'bundles' / 'rev'
    _bundle(directory / 'ground', 'Ground')
    _bundle(directory / 'plaza', 'Plaza', mesh=second, material={'AlbedoColor': [0, 0, 1, 1]})
    return directory


def test_conflicting_asset_names_are_rewritten(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch)
    m = pipeline.merge_bundles(directory)
    assert m['assets']['mesh_a']['source'] == 'ground/mesh_a.mesh.json'
    assert m['assets']['plaza-mesh_a']['source'] == 'plaza/mesh_a.mesh.json'
    nodes = {n['slot']['key']: n for n in _nodes(m)}
    assert nodes['plaza-object_driven']['components'][0]['fields']['URL'] == '$asset:plaza-mesh_a'
    assert nodes['plaza-object_driven']['components'][1]['fields'] == {
        'Mesh': '$component:plaza-mesh_a', 'Materials': ['$component:plaza-mat_a', '$component:mat_b']}
    assert nodes['plaza-object_driven']['components'][2]['fields'] == {
        '_target': '$slot-member:plaza-object_driven.Rotation',
        'Anchor': '$slot:plaza-object_a', 'Source': '$member:plaza-mat_a.AlbedoColor'}
    assert nodes['plaza-object_driven'] in nodes['plaza-object_a']['children']
    assert [c['key'] for c in nodes['plaza-provider_mat_a']['components']] == ['plaza-mat_a']
    assert len({n['slot']['key'] for n in _nodes(m)}) == len(_nodes(m))


def test_identical_assets_and_materials_share_provider(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch, second=b'first')
    payload_path = directory / 'plaza' / 'model.apply.json'
    payload = json.loads(payload_path.read_text())
    payload['children'][1]['children'][0]['components'][0]['fields'] = {'AlbedoColor': [1, 0, 0, 1]}
    payload_path.write_text(json.dumps(payload))
    m = pipeline.merge_bundles(directory)
    assert list(m['assets']) == ['mesh_a']
    comps = [c for n in _nodes(m) for c in n.get('components', [])]
    assert [c['key'] for c in comps].count('mat_a') == 1
    driven = next(n for n in _nodes(m) if n['slot']['name'] == 'Plaza_driven')
    assert driven['components'][0]['fields']['URL'] == '$asset:mesh_a'
    assert driven['components'][1]['fields']['Materials'] == ['$component:mat_a', '$component:mat_b']


def _full_setup(tmp_path):
    """Real ads export + tiny synthetic sectors, with wide evaluated bounds for native candidates."""
    import shutil
    from modeling.slum03.layout import build_layout
    directory = tmp_path / 'bundles' / 'rev'
    ads = Path('artifacts/slum03/task8-final-20260927T201851-2822336/bundle')
    shutil.copytree(ads, directory / 'ads')
    layout = build_layout()
    for sector in pipeline.SECTORS:
        if sector == 'ads':
            continue
        d = directory / sector
        if sector in ('ground', 'plaza'):
            _bundle(d, sector.title(), mesh=b'first' if sector == 'ground' else b'second')
            payload = json.loads((d / 'model.apply.json').read_text())
        else:
            d.mkdir(parents=True)
            payload = {'schemaVersion': '1', 'ownership': {'key': 'blender_' + sector},
                       'slot': {'key': 'root', 'name': sector, 'parent': 'Root'},
                       'assets': {}, 'components': [], 'children': []}
        payload['children'].extend({'slot': {'key': 'label_' + label.parent_name,
                                              'name': label.parent_name}, 'components': []}
                                   for label in layout.labels if (label.parent_name == 'yarol' and sector == 'yarol')
                                   or (label.parent_name in ('nightlife-east', 'nightlife-velvet') and sector == 'nightlife')
                                   or (label.parent_name == 'market-west' and sector == 'market'))
        (d / 'model.apply.json').write_text(json.dumps(payload))
        (d / 'report.json').write_text(json.dumps({'sector': sector, 'errors': [],
            'evaluated_bounds': {name: {'minimum': [-10000]*3, 'maximum': [10000]*3}
                                 for name in ('district-foundation', 'factory-floor', 'bridge',
                                              'checkpoint', 'south-road-end', 'north-turnback')}}))
    return directory, layout


def test_nested_bundle_paths_survive_final_write(tmp_path):
    directory, layout = _full_setup(tmp_path)
    m = pipeline.build_unified_manifest(directory, layout, {}, (0, 5, 0))
    assert m['assets']['mesh_a']['source'] == str((directory / 'ground' / 'mesh_a.mesh.json').resolve())
    output = tmp_path / 'slum03.json'
    before = json.dumps(m, sort_keys=True)
    pipeline.write_unified_manifest(m, output)
    saved = json.loads(output.read_text())
    assert json.dumps(m, sort_keys=True) == before
    assert saved['assets']['mesh_a']['source'] == 'bundles/rev/ground/mesh_a.mesh.json'
    assert (output.parent / saved['assets']['mesh_a']['source']).read_bytes() == b'first'
    assert saved['slot']['position'] == [0, 5, 0]
    assert saved['limits']['expandedNodes'] == math.ceil(1.2 * _count({k: v for k, v in saved.items() if k != 'limits'}))


def _count(value):
    return 1 + (sum(_count(v) for v in value.values()) if isinstance(value, dict)
                else sum(_count(v) for v in value) if isinstance(value, list) else 0)


def test_missing_sector_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'SECTORS', ('ground', 'plaza'))
    _bundle(tmp_path / 'ground', 'Ground')
    with pytest.raises(ValueError, match='missing sector'):
        pipeline.merge_bundles(tmp_path)


def test_material_provider_has_unique_slot(tmp_path, monkeypatch):
    m = pipeline.merge_bundles(_setup(tmp_path, monkeypatch))
    nodes = _nodes(m)
    assert len({n['slot']['key'] for n in nodes}) == len(nodes)
    for n in nodes:
        for c in n.get('components', []):
            if c['type'] == 'FrooxEngine.PBS_Metallic':
                assert n['slot']['key'].startswith('provider_') or n['slot']['key'].startswith('plaza-provider_')
    assert {'provider_mat_a', 'plaza-provider_mat_a'} <= {n['slot']['key'] for n in nodes}


def test_same_manifest_is_deterministic(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch)
    assert json.dumps(pipeline.merge_bundles(directory)) == json.dumps(pipeline.merge_bundles(directory))


def test_cli_rejects_synthetic_exporter_like_reports(tmp_path):
    from modeling.slum03.layout import write_layout
    directory, layout = _full_setup(tmp_path)
    path = tmp_path / 'layout.json'
    write_layout(layout, path)
    output = tmp_path / 'slum03.json'
    result = subprocess.run([sys.executable, '-m', 'modeling.slum03.pipeline', '--bundles', str(directory),
                             '--layout', str(path), '--reports', str(directory), '--root-y', '5', '--output', str(output)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert not output.exists()


def test_native_postprocess_runs_once_on_merged_manifest(tmp_path, monkeypatch):
    directory, layout = _full_setup(tmp_path)
    real = pipeline.postprocess
    received = []
    def observe(manifest, passed_layout, reports, root_position):
        received.append((manifest, passed_layout, reports, root_position))
        return real(manifest, passed_layout, reports, root_position)
    monkeypatch.setattr(pipeline, 'postprocess', observe)
    final = pipeline.build_unified_manifest(directory, layout, {}, (0, 5, 0))
    assert len(received) == 1
    assert received[0][1:] == (layout, {}, (0, 5, 0))
    assert [n['slot']['key'] for n in _nodes(final)].count('native-textures') == 1
    assert final['slot']['name'] == 'Slum03_Slum'
    assert final['ownership'] == {'key': 'slum03'}
    assert final['slot']['parent'] == 'Root'


def test_write_rebases_to_output_in_sibling_directory(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch)
    m = pipeline.merge_bundles(directory)
    for asset in m['assets'].values():
        asset['source'] = str((directory / asset['source']).resolve())
    output = tmp_path / 'other' / 'slum03.json'
    pipeline.write_unified_manifest(m, output)
    saved = json.loads(output.read_text())
    assert saved['assets']['mesh_a']['source'] == '../bundles/rev/ground/mesh_a.mesh.json'
    assert (output.parent / saved['assets']['mesh_a']['source']).read_bytes() == b'first'


def test_materials_with_same_local_reference_spelling_but_different_targets_stay_distinct(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch, second=b'first')
    for sector, seed in (('ground', 1), ('plaza', 2)):
        source = directory / sector / 'model.apply.json'
        bundle = json.loads(source.read_text())
        material = bundle['children'][1]['children'][0]['components'][0]
        material['fields'] = {'AlbedoColor': [1, 0, 0, 1], 'AlbedoTexture': '$component:tex'}
        bundle['children'][1]['children'].append({
            'slot': {'key': 'provider_tex', 'name': 'tex_' + sector},
            'components': [{'key': 'tex', 'type': 'FrooxEngine.NoiseTexture', 'fields': {'Seed': seed}}]})
        source.write_text(json.dumps(bundle))
    merged = pipeline.merge_bundles(directory)
    comps = {c['key']: c for n in _nodes(merged) for c in n.get('components', [])}
    assert comps['mat_a']['fields']['AlbedoTexture'] == '$component:tex'
    assert comps['plaza-mat_a']['fields']['AlbedoTexture'] == '$component:plaza-tex'
    plaza = next(n for n in _nodes(merged) if n['slot']['name'] == 'Plaza_driven')
    renderer = next(c for c in plaza['components'] if c['type'] == 'FrooxEngine.MeshRenderer')
    assert renderer['fields']['Materials'] == ['$component:plaza-mat_a', '$component:mat_b']


def test_third_sector_reuses_second_sectors_identical_assets_and_materials(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'SECTORS', ('ground', 'plaza', 'market'))
    directory = tmp_path / 'bundles' / 'rev'
    _bundle(directory / 'ground', 'Ground', mesh=b'A', material={'AlbedoColor': [1, 0, 0, 1]})
    _bundle(directory / 'plaza', 'Plaza', mesh=b'B', material={'AlbedoColor': [0, 0, 1, 1]})
    _bundle(directory / 'market', 'Market', mesh=b'B', material={'AlbedoColor': [0, 0, 1, 1]})
    merged = pipeline.merge_bundles(directory)
    assert list(merged['assets']) == ['mesh_a', 'plaza-mesh_a']
    assert [merged['assets'][k]['source'] for k in merged['assets']] == [
        'ground/mesh_a.mesh.json', 'plaza/mesh_a.mesh.json']
    comps = {c['key']: c for n in _nodes(merged) for c in n.get('components', [])}
    assert 'market-mat_a' not in comps
    assert comps['plaza-mat_a']['fields'] == {'AlbedoColor': [0, 0, 1, 1]}
    market = next(n for n in _nodes(merged) if n['slot']['name'] == 'Market_driven')
    assert market['components'][0]['fields']['URL'] == '$asset:plaza-mesh_a'
    assert market['components'][1]['fields']['Materials'] == ['$component:plaza-mat_a', '$component:mat_b']
    assert market['components'][1]['fields']['Mesh'] == '$component:market-mesh_a'


def test_colliding_canonical_ads_material_still_converts_and_pans(tmp_path):
    directory, layout = _full_setup(tmp_path)
    key = 'mat_material_Slum03_holo_cyan_a06e351f'
    ground = directory / 'ground' / 'model.apply.json'
    bundle = json.loads(ground.read_text())
    bundle['children'][1]['children'].append({
        'slot': {'key': 'provider_' + key, 'name': 'ground_holo'},
        'components': [{'key': key, 'type': 'FrooxEngine.PBS_Metallic',
                        'fields': {'AlbedoColor': [1, 0, 0, 1]}}]})
    ground.write_text(json.dumps(bundle))
    final = pipeline.build_unified_manifest(directory, layout, {}, (0, 5, 0))
    comps = {c['key']: c for n in _nodes(final) for c in n.get('components', [])}
    renamed = 'ads-' + key
    assert comps[renamed]['type'] == 'FrooxEngine.FresnelMaterial'
    scan = next(n for n in _nodes(final) if n['slot']['name'] == 'nightlife-info-ad-driven')
    renderer = next(c for c in scan['components'] if c['type'] == 'FrooxEngine.MeshRenderer')
    clone = 'scan-' + scan['slot']['key'] + '-' + renamed
    assert '$component:' + clone in renderer['fields']['Materials']
    assert comps[clone]['type'] == 'FrooxEngine.FresnelMaterial'
    for side in ('near', 'far'):
        assert comps['panner-' + clone + '-' + side]['type'] == 'FrooxEngine.Panner2D'


def test_actual_bundle_cli_requires_matching_blender_reports(tmp_path):
    # Removing --reports must not silently consume exporter report.json.
    bundles = Path('content/slum03/bundles/finalfix-m-20260928T0511')
    reports = Path('artifacts/slum03/finalfix-m-20260928T0511')
    output = tmp_path / 'actual.json'
    base = [sys.executable, '-m', 'modeling.slum03.pipeline', '--bundles', str(bundles),
            '--layout', 'content/slum03/layout.json', '--root-y', '4.5', '--output', str(output)]
    missing = subprocess.run(base, capture_output=True, text=True)
    assert missing.returncode != 0 and not output.exists()
    result = subprocess.run(base + ['--reports', str(reports)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(output.read_text())
    assert manifest['slot']['position'] == [0, 4.5, 0]
    assert all((output.parent / a['source']).is_file() for a in manifest['assets'].values())
    provenance = json.loads((tmp_path / 'actual-provenance.json').read_text())
    assert provenance['reports'] == str(reports)


def test_actual_bundle_cli_rejects_exporter_report_as_evaluated_report(tmp_path):
    bundles = Path('content/slum03/bundles/finalfix-m-20260928T0511')
    reports = Path('artifacts/slum03/finalfix-m-20260928T0511')
    fake = tmp_path / 'reports'
    fake.mkdir()
    for sector in pipeline.SECTORS:
        source = bundles / sector / 'report.json' if sector == 'ground' else reports / f'{sector}-report.json'
        (fake / f'{sector}-report.json').write_bytes(source.read_bytes())
    output = tmp_path / 'bad.json'
    result = subprocess.run([sys.executable, '-m', 'modeling.slum03.pipeline',
                             '--bundles', str(bundles), '--layout', 'content/slum03/layout.json',
                             '--reports', str(fake), '--root-y', '4.5', '--output', str(output)],
                            capture_output=True, text=True)
    assert result.returncode != 0 and not output.exists()
    assert 'report' in result.stderr.lower() or 'bounds' in result.stderr.lower()


def test_actual_bundle_cli_can_regenerate_delivery_manifest(tmp_path):
    output = tmp_path / 'delivery.json'
    result = subprocess.run([sys.executable, '-m', 'modeling.slum03.pipeline',
                             '--bundles', 'content/slum03/bundles/finalfix-m-20260928T0511',
                             '--layout', 'content/slum03/layout.json',
                             '--reports', 'artifacts/slum03/finalfix-m-20260928T0511',
                             '--root-y', '4.5', '--delivery-checks', '--output', str(output)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    result_manifest = json.loads(output.read_text())
    assert len(result_manifest['cameras']) == 6
    assert result_manifest['tests'][0]['assertions']
    assert result_manifest['slot']['position'] == [0, 4.5, 0]


def test_cli_rejects_valid_reports_from_another_geometry_revision(tmp_path):
    bundles = Path('content/slum03/bundles/finalfix-m-20260928T0511')
    current = Path('artifacts/slum03/finalfix-m-20260928T0511')
    earlier = Path('artifacts/slum03/task11-fix2-20260928T0356')
    reports = tmp_path / 'reports'
    reports.mkdir()
    for sector in pipeline.SECTORS:
        (reports / f'{sector}-report.json').write_bytes(
            ((earlier if sector == 'ground' else current) / f'{sector}-report.json').read_bytes())
    output = tmp_path / 'mixed.json'
    result = subprocess.run([sys.executable, '-m', 'modeling.slum03.pipeline',
                             '--bundles', str(bundles), '--reports', str(reports),
                             '--layout', 'content/slum03/layout.json', '--root-y', '4.5',
                             '--output', str(output)], capture_output=True, text=True)
    assert result.returncode != 0 and not output.exists()
    assert 'ground' in result.stderr
