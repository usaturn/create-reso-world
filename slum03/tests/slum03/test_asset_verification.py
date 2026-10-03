"""Breaks caught: missing/invalid sector evidence, evaluated intrusions, changed exported attributes."""
import json
import pytest

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


def test_real_v2_side_posts_leave_protected_branch_open_despite_one_mesh_envelope():
    from dataclasses import replace
    from modeling.slum03.density_metrics import layout_digest
    from modeling.slum03.evaluated_detail import observe_detail
    from modeling.slum03.geometry import Assembly, box, merge_assembly
    from modeling.slum03.types import Placement, DensityConfig, RectXZ
    base = build_layout()
    p = Placement('open-demo', 'market', 'stall', (20., 0., -30.), (4., 4., 4.),
                  0., 'district', {'detail_profile': 'v2', 'variant': 'tools'})
    layout = replace(base, placements=base.placements + (p,), density=DensityConfig(
        'representative', (), (), (RectXZ(19.5, 20.5, -31., -29.),), ()))
    a = Assembly('stall', p.key, p.sector, p.origin,
                 [box('left-post', (-1.5, 1., 0.), (.2, 2., .2), 'steel_dark'),
                  box('right-post', (1.5, 1., 0.), (.2, 2., .2), 'steel_dark'),
                  box('roof', (0., 3.5, 0.), (3.4, .2, 2.), 'steel_dark')],
                 {'placement_key': p.key, 'variant': 'tools', 'detail_groups': [
                     {'id': 'posts', 'category': 'architecture', 'part_indices': [0, 1]},
                     {'id': 'roof', 'category': 'architecture', 'part_indices': [2]}]})
    merged = merge_assembly(a)
    obj = observe_detail(a, {'vertices': [tuple(v[i]+p.origin[i] for i in range(3))
                                          for v in merged.vertices], 'faces': merged.faces})
    obj['detail_profile'] = 'v2'
    reports = minimal_reports(layout)
    for report in reports.values():
        report['layout_sha256'] = layout_digest(layout)
    reports['market']['objects'][-1] = obj
    reports['market']['evaluated_bounds'][p.key] = obj['evaluated_bounds']
    issues = verify_assets(layout, reports)
    assert not any(i.code == 'CLEARANCE_INTRUSION' and i.object_key == p.key for i in issues), issues


def test_ungrouped_center_blocker_cannot_hide_behind_open_stall_semantic_tags():
    from dataclasses import replace
    from modeling.slum03.density_metrics import layout_digest
    from modeling.slum03.evaluated_detail import observe_detail
    from modeling.slum03.geometry import Assembly, box, merge_assembly
    from modeling.slum03.types import Placement, DensityConfig, RectXZ
    base = build_layout()
    p = Placement('open-demo', 'market', 'stall', (20., 0., -30.), (4., 4., 4.),
                  0., 'district', {'detail_profile': 'v2', 'variant': 'tools'})
    layout = replace(base, placements=base.placements + (p,), density=DensityConfig(
        'representative', (), (), (RectXZ(19.5, 20.5, -31., -29.),), ()))
    a = Assembly('stall', p.key, p.sector, p.origin,
                 [box('left-post', (-1.5, 1., 0.), (.2, 2., .2), 'steel_dark'),
                  box('right-post', (1.5, 1., 0.), (.2, 2., .2), 'steel_dark'),
                  box('hidden-center-post', (0., 1., 0.), (.2, 2., .2), 'steel_dark'),
                  box('roof', (0., 3.5, 0.), (3.4, .2, 2.), 'steel_dark')],
                 {'placement_key': p.key, 'variant': 'tools', 'detail_groups': [
                     {'id': 'posts', 'category': 'architecture', 'part_indices': [0, 1]},
                     {'id': 'roof', 'category': 'architecture', 'part_indices': [3]}]})
    merged = merge_assembly(a)
    obj = observe_detail(a, {'vertices': [tuple(v[i]+p.origin[i] for i in range(3))
                                          for v in merged.vertices], 'faces': merged.faces})
    obj['detail_profile'] = 'v2'
    reports = minimal_reports(layout)
    for report in reports.values():
        report['layout_sha256'] = layout_digest(layout)
    reports['market']['objects'][-1] = obj
    reports['market']['evaluated_bounds'][p.key] = obj['evaluated_bounds']
    issues = verify_assets(layout, reports)
    assert any(i.object_key == p.key and i.code in ('DETAIL_INVALID', 'CLEARANCE_INTRUSION')
               for i in issues), issues


@pytest.mark.parametrize('parent_v2', [False, True])
def test_unprofiled_attachment_child_outside_valid_contact_is_rejected_publicly(parent_v2):
    from dataclasses import replace
    from modeling.slum03.density_metrics import layout_digest
    from modeling.slum03.evaluated_detail import observe_detail, validate_evaluated_density
    from modeling.slum03.geometry import Assembly, box, merge_assembly
    from modeling.slum03.types import Placement
    base = build_layout()
    params = {'detail_profile': 'v2', 'variant': 'tools'} if parent_v2 else {}
    parent = Placement('mounted-parent', 'market', 'stall', (22., 0., -30.),
                       (4., 3., 4.), 0., 'district', params)
    child = Placement('mounted-utility', 'market', 'utility', (23., 0., -30.),
                      (2., 3., 2.), 0., 'district', {'attachment': {
                          'parent_key': parent.key, 'reason': 'bracket',
                          'contact_min': [22.9, .3, -30.1],
                          'contact_max': [23.1, .7, -29.9]}})
    layout = replace(base, placements=base.placements + (parent, child))

    def issues(size, *, drop_child=False):
        reports = minimal_reports(layout)
        for report in reports.values():
            report['layout_sha256'] = layout_digest(layout)
        parent_mesh = box('bracket', (1., .5, 0.), size, 'steel_dark')
        child_mesh = box('bracket', (0., .5, 0.), size, 'steel_dark')
        for p, part in ((parent, parent_mesh), (child, child_mesh)):
            lo = [min(v[i] + p.origin[i] for v in part.vertices) for i in range(3)]
            hi = [max(v[i] + p.origin[i] for v in part.vertices) for i in range(3)]
            obj = {'key': p.key, 'placement_key': p.key, 'kind': p.kind,
                   'mesh': p.key, 'vertices': 8, 'faces': 6}
            if p == parent and parent_v2:
                assembly = Assembly(p.kind, p.key, p.sector, p.origin, [part],
                                    {'placement_key': p.key, 'variant': 'tools',
                                     'detail_groups': [{'id': 'bracket', 'category': 'architecture',
                                                        'part_indices': [0]}]})
                merged = merge_assembly(assembly)
                obj = observe_detail(assembly, {
                    'vertices': [tuple(v[i]+p.origin[i] for i in range(3))
                                 for v in merged.vertices], 'faces': merged.faces})
                obj['detail_profile'] = 'v2'
            report = reports[p.sector]
            report['objects'] = [obj if entry['key'] == p.key else entry
                                 for entry in report['objects']]
            report['evaluated_bounds'][p.key] = {'minimum': lo, 'maximum': hi}
            if drop_child and p == child:
                report['evaluated_bounds'].pop(p.key)
        return validate_evaluated_density(layout, reports), verify_assets(layout, reports)

    for check in issues((.2, .4, .2)):
        assert not any(i.code == 'ATTACHMENT_INTRUSION' and i.object_key == child.key
                       for i in check)
    for check in issues((.5, 2., .5)):
        assert any(i.code == 'ATTACHMENT_INTRUSION' and i.object_key == child.key
                   for i in check), check
    assert any(i.code == 'GEOMETRY_MISSING' and i.object_key == child.key
               for i in issues((.2, .4, .2), drop_child=True)[0])


def _curbed_foundation_reports(parts_extra=()):
    """Full Layout reports whose ground mesh is the real curbed district-foundation."""
    from dataclasses import replace
    from pathlib import Path
    from modeling.slum03 import ground
    from modeling.slum03.layout import read_layout
    layout = read_layout(Path('content/slum03/density-full-layout.json'))
    reports = minimal_reports(layout)
    foundation = next(a for a in ground.build_assemblies(layout, 'ground')
                      if a.name == 'district-foundation')
    parts = list(foundation.parts) + list(parts_extra)
    lo = [min(v[i] for p in parts for v in p.vertices) + foundation.origin[i] for i in range(3)]
    hi = [max(v[i] for p in parts for v in p.vertices) + foundation.origin[i] for i in range(3)]
    report = reports['ground']
    report['objects'] = [o for o in report['objects'] if o['key'] != 'district-ground']
    report['objects'].insert(0, {'key': 'district-ground', 'kind': 'foundation',
                                 'mesh': 'district-foundation'})
    del report['evaluated_bounds']['district-ground']
    report['evaluated_bounds']['district-foundation'] = {'minimum': lo, 'maximum': hi}
    return layout, reports, replace(foundation, parts=parts)


def _foundation_issues(layout, reports):
    return [i for i in verify_assets(layout, reports)
            if i.object_key == 'district-foundation']


def test_curbed_district_foundation_is_walkable_ground_not_a_route_intrusion():
    layout, reports, _ = _curbed_foundation_reports()
    top = reports['ground']['evaluated_bounds']['district-foundation']['maximum'][1]
    assert .1 < top < .15  # Task 11 curbs raise the evaluated envelope
    assert _foundation_issues(layout, reports) == []


def test_curb_across_a_main_route_is_still_a_clearance_intrusion(monkeypatch):
    from modeling.slum03 import ground
    from modeling.slum03.geometry import box
    # A 0.15 m curb laid across the west main street (route z -1.5..1.5 at x=-40).
    stray = box('curb-stray', (-40, .06, 0), (.18, .15, 5), 'concrete_raw')
    layout, reports, patched = _curbed_foundation_reports([stray])
    original = ground.build_assemblies
    monkeypatch.setattr(ground, 'build_assemblies', lambda lay, sector: [
        patched if a.name == 'district-foundation' else a for a in original(lay, sector)])
    assert any(i.code == 'CLEARANCE_INTRUSION' for i in _foundation_issues(layout, reports))


def test_curbed_foundation_without_matching_source_parts_fails_closed():
    layout, reports, _ = _curbed_foundation_reports()
    reports['ground']['evaluated_bounds']['district-foundation']['maximum'][1] = .5
    codes = {i.code for i in _foundation_issues(layout, reports)}
    assert 'SURFACE_EVIDENCE' in codes and 'CLEARANCE_INTRUSION' in codes
