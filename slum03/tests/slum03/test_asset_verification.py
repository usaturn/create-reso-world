"""Breaks caught: missing/invalid sector evidence, evaluated intrusions, changed exported attributes."""
import json

from modeling.slum03.layout import build_layout
from modeling.slum03.verify_assets import verify_assets, compare_geometry_exports, semantic_bounds
from tests.slum03.helpers import minimal_reports


def test_build_error_blocks_asset_verification():
    layout = build_layout()
    reports = minimal_reports(layout)
    reports['plaza']['errors'] = [{'code': 'UV_MISSING', 'object_key': 'north-wall', 'message': 'missing UV0'}]
    assert any(i.code == 'BUILD_ERROR' for i in verify_assets(layout, reports))


def test_missing_sector_and_empty_sector_fail_closed():
    layout = build_layout()
    reports = minimal_reports(layout)
    reports.pop('ads')
    reports['forest']['objects'] = []
    issues = verify_assets(layout, reports)
    assert any(i.code == 'SECTOR_MISSING' and i.object_key == 'ads' for i in issues)
    assert any(i.code == 'SECTOR_EMPTY' and i.object_key == 'forest' for i in issues)


def test_missing_material_and_uv_issue_fail():
    layout = build_layout()
    reports = minimal_reports(layout)
    reports['market']['materials'] = []
    reports['plaza']['uv_issues'] = [{'code': 'UV_MISSING', 'object_key': 'wall', 'message': 'UV0'}]
    codes = {i.code for i in verify_assets(layout, reports)}
    assert 'MATERIAL_MISSING' in codes and 'UV_MISSING' in codes


def test_evaluated_rubble_extent_crosses_clear_space_even_if_origin_outside():
    layout = build_layout()
    reports = minimal_reports(layout)
    reports['plaza']['objects'].append({'key': 'rubble-west', 'kind': 'rubble', 'mesh': 'rubble-west'})
    reports['plaza']['evaluated_bounds']['rubble-west'] = {
        'minimum': [-17, 0, -2], 'maximum': [-15, 2, 2]}
    assert any(i.code == 'CLEARANCE_INTRUSION' for i in verify_assets(layout, reports))


def test_mesh_name_bounds_aggregate_to_semantic_target_and_retain_blocker():
    layout = build_layout()
    reports = minimal_reports(layout)
    reports['forest']['evaluated_bounds'] = {'forest-tree-0-0': {
        'minimum': [115, 0, -5], 'maximum': [120, 22, 5]}}
    reports['forest']['objects'] = [{'key': 'forest-tree-0-0', 'kind': 'tree', 'mesh': 'forest-tree-0-0',
                                     'placement_key': 'forest'}]
    reports['plaza']['evaluated_bounds']['foreground-blocker'] = {
        'minimum': [-2, 3, 20], 'maximum': [2, 300, 500]}
    reports['plaza']['objects'].append({'key': 'foreground-blocker', 'kind': 'wall',
                                         'mesh': 'foreground-blocker'})
    bounds = semantic_bounds(reports)
    assert bounds['forest'].maximum[1] >= 22
    assert bounds['foreground-blocker'].maximum[1] == 300


def _mesh(color):
    return {'vertices': [{'position': {'x': 0, 'y': 0, 'z': 0},
                          'normal': {'x': 0, 'y': 1, 'z': 0},
                          'tangent': {'x': 1, 'y': 0, 'z': 0, 'w': 1},
                          'uvs': [{'$type': '2D', 'uv': {'x': 0, 'y': 0}}],
                          'color': {'r': color, 'g': 0, 'b': 0, 'a': 1}}],
            'submeshes': [{'$type': 'trianglesFlat', 'vertexIndices': [0, 0, 0]}]}


def test_geometry_comparison_checks_color_normals_uv_tangent_submeshes_and_missing_mesh(tmp_path):
    first, second = tmp_path / 'first', tmp_path / 'second'
    first.mkdir(); second.mkdir()
    (first / 'part.mesh.json').write_text(json.dumps(_mesh(.5)))
    (second / 'part.mesh.json').write_text(json.dumps(_mesh(.5)))
    assert compare_geometry_exports(first, second) == []
    for field, value in [('color', {'r': .6}), ('normal', {'x': .3}),
                         ('uvs', [{'$type': '2D', 'uv': {'x': .1, 'y': 0}}]),
                         ('tangent', {'w': -1})]:
        changed = _mesh(.5)
        changed['vertices'][0][field] = value
        (second / 'part.mesh.json').write_text(json.dumps(changed))
        assert compare_geometry_exports(first, second), field
    changed = _mesh(.5); changed['submeshes'][0]['vertexIndices'] = [0, 0, 1]
    (second / 'part.mesh.json').write_text(json.dumps(changed))
    assert compare_geometry_exports(first, second)
    (second / 'part.mesh.json').unlink()
    assert compare_geometry_exports(first, second)


def test_disconnected_background_buildings_do_not_create_phantom_clearance_blocker():
    layout = build_layout()
    reports = minimal_reports(layout)
    reports['backdrop-west-south']['objects'] = [
        {'key': 'south-city-0-0', 'kind': 'low-city', 'mesh': 'south-city-0-0'},
        {'key': 'south-city-0-1', 'kind': 'low-city', 'mesh': 'south-city-0-1'}]
    reports['backdrop-west-south']['evaluated_bounds'] = {
        'south-city-0-0': {'minimum': [-100, 0, -5], 'maximum': [-90, 30, 5]},
        'south-city-0-1': {'minimum': [90, 0, -5], 'maximum': [100, 30, 5]}}
    assert not any(i.code == 'CLEARANCE_INTRUSION' and i.object_key == 'south-city'
                   for i in verify_assets(layout, reports))


def test_report_omitting_a_required_direct_placement_fails():
    reports = minimal_reports(build_layout())
    reports['plaza']['objects'] = [o for o in reports['plaza']['objects'] if o['key'] != 'north-wall']
    reports['plaza']['evaluated_bounds'].pop('north-wall')
    assert any(i.code == 'PLACEMENT_MISSING' and i.object_key == 'north-wall'
               for i in verify_assets(build_layout(), reports))


def test_geometry_comparison_rejects_same_export_directory(tmp_path):
    path = tmp_path / 'only'
    path.mkdir()
    (path / 'mesh.mesh.json').write_text(json.dumps(_mesh(.5)))
    assert any(i.code == 'COMPARISON_NOT_INDEPENDENT' for i in compare_geometry_exports(path, path))


def test_native_resource_attribution_uses_owned_placement_sector():
    from scripts.summarize_offline import native_sector_counts
    manifest = {'slot': {'key': 'root'}, 'children': [
        {'slot': {'key': 'collider-district-ground-west'},
         'components': [{'key': 'floor', 'type': 'FrooxEngine.BoxCollider'}]},
        {'slot': {'key': 'local-light-yarol'},
         'components': [{'key': 'warm', 'type': 'FrooxEngine.Light'}]}]}
    counts = native_sector_counts(manifest, build_layout())
    assert counts['ground']['colliders'] == 1
    assert counts['yarol']['lights'] == 1
    assert counts['plaza']['lights'] == 0


def test_evaluated_uv_coordinate_error_blocks_asset_verification():
    reports = minimal_reports(build_layout())
    reports['ground']['errors'] = [{'code': 'UV_DEGENERATE', 'object_key': 'ground',
                                    'message': 'evaluated UV0 collapsed'}]
    assert any(i.code == 'BUILD_ERROR' and i.object_key == 'ground'
               for i in verify_assets(build_layout(), reports))


def test_offline_build_orders_ar_last_after_background():
    from scripts.build_offline import BUILD_ORDER
    from modeling.slum03.sectors import SECTORS
    assert set(BUILD_ORDER) == set(SECTORS)
    assert len(BUILD_ORDER) == len(SECTORS)
    assert BUILD_ORDER[-1] == 'ads'
    assert BUILD_ORDER.index('forest') < BUILD_ORDER.index('ads')


def test_offline_driver_passes_explicit_persisted_layout_to_blender(tmp_path, monkeypatch):
    import sys
    import pytest
    from pathlib import Path
    from modeling.slum03.layout import build_layout, read_layout, write_layout
    from scripts import build_offline
    path = tmp_path / 'custom.json'
    write_layout(build_layout(7), path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['build_offline.py', '--run', 'unique', '--layout', str(path)])
    def stop_at_blender(*args, **kwargs):
        raise RuntimeError('Blender command: ' + ' '.join(args))
    monkeypatch.setattr(build_offline, 'command', stop_at_blender)
    with pytest.raises(RuntimeError, match='Blender command:') as exc:
        build_offline.main()
    assert '--arg=--layout' in str(exc.value)
    snapshot = tmp_path / 'artifacts/slum03/unique/layout.json'
    assert '--arg=' + str(snapshot) in str(exc.value)
    assert read_layout(snapshot).seed == 7


def test_v2_report_cannot_promote_legacy_evidence_or_wrong_layout():
    from dataclasses import replace
    from modeling.slum03.density_metrics import layout_digest
    layout = build_layout()
    p = next(p for p in layout.placements if p.key == 'market-west')
    layout = replace(layout, placements=tuple(replace(x, params={**x.params,
        'detail_profile': 'v2', 'variant': 'electronics'}) if x.key == p.key else x
        for x in layout.placements))
    reports = minimal_reports(layout)
    for r in reports.values():
        r['layout_sha256'] = layout_digest(layout)
    assert any(i.code == 'DETAIL_MISSING' for i in verify_assets(layout, reports))
    reports['market']['layout_sha256'] = '0' * 64
    assert any(i.code == 'LAYOUT_MISMATCH' for i in verify_assets(layout, reports))
