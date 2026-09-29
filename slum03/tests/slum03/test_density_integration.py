"""Gate C: a full candidate must be the evidence of what was actually generated.

Breaks caught: full scope that rejects legitimate additions or lets unrelated
content through, selected metadata that was never regenerated, recorded
counts/hashes that do not describe the written candidate, representative
reports mixed into a full Layout, order-dependent geometry, and comparisons
that hide lost meshes, lost UV layers or rounded floats.
"""
import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from modeling.slum03.candidate_scope import check_candidate_scope, compose_candidate
from modeling.slum03.layout import read_layout
from modeling.slum03.native.lighting import light_slots
from modeling.slum03.sectors import SECTORS, sector_assemblies

FULL = Path('content/slum03/density-full-layout.json')
REP_RUN = Path('artifacts/slum03/density-rep-a-20260928Ttask6-01')
RUN = 'fixture-full'
NEW_USE = 'density-northwest-ruin-01'
NEW_ROUTE = 'density-overhead-northwest-01'
SUBSET = ('ruin-west', 'district-foundation', 'plaza-rubble-west', NEW_USE, NEW_ROUTE)


@pytest.fixture(scope='module')
def full():
    return read_layout(FULL)


def subset_layout(full, keys=SUBSET):
    return replace(full, density=replace(full.density, selected_keys=tuple(keys)))


def _cluster_lights(full):
    return [copy.deepcopy(n) for n in light_slots(full) if n['slot']['key'].startswith('local-light-cluster-')]


def _cluster_light(full):
    return copy.deepcopy(next(n for n in light_slots(full)
                              if n['slot']['key'].startswith('local-light-cluster-')))


def _obj(name, asset, material='shared'):
    return {'slot': {'key': f'object_{name}_{hashlib.sha1(name.encode()).hexdigest()[:8]}',
                     'name': name},
            'components': [
                {'key': 'mesh_' + name, 'type': 'FrooxEngine.StaticMesh', 'fields': {'URL': '$asset:' + asset}},
                {'key': 'renderer_' + name, 'type': 'FrooxEngine.MeshRenderer',
                 'fields': {'Mesh': '$component:mesh_' + name, 'Materials': ['$component:' + material]}}],
            'children': []}


def _collider(key, size):
    return {'slot': {'key': key, 'name': key.removeprefix('collider-') + ' Collider'},
            'components': [{'key': key + '-box', 'type': 'FrooxEngine.BoxCollider',
                            'fields': {'Size': size}}], 'children': []}


def _group(key, children):
    return {'slot': {'key': key, 'name': key}, 'components': [], 'children': children}


def _manifest(sources):
    return {'schemaVersion': '1', 'ownership': {'key': 'slum03'},
            'slot': {'key': 'root', 'name': 'Slum03_Slum', 'parent': 'Root', 'position': [0, 4.5, 0]},
            'components': [],
            'assets': {k: {'kind': 'mesh', 'source': v} for k, v in sources.items()},
            'children': [
                _group('sector-ground', [_obj('district-foundation', 'ground')]),
                _group('sector-plaza', [_obj('factory-floor', 'floor'),
                                        _obj('plaza-rubble-west-0-2', 'heap02'),
                                        _obj('plaza-rubble-west-0-3', 'heap03'),
                                        _obj('plaza-rubble-north-2-9', 'heapn')]),
                _group('sector-ruins-west', [_obj('ruin-west', 'ruin')]),
                _group('sector-overhead', [_obj('overhead-west', 'overhead')]),
                {'slot': {'key': 'providers', 'name': 'Providers'}, 'components': [
                    {'key': 'shared', 'type': 'FrooxEngine.PBS_Metallic', 'fields': {'Color': [1, 0, 0]}}],
                 'children': []},
                _group('native-colliders', [_collider('collider-district-ground-west', [40, .3, 120]),
                                            _collider('collider-ruin-west', [4, 4, 4])]),
                _group('native-lights', [])]}


OLD = {'ground': 'g', 'floor': 'floor', 'heap02': 'h02', 'heap03': 'h03', 'heapn': 'hn',
       'ruin': 'r', 'overhead': 'o'}
NEW = {'ground': 'g2', 'floor': 'floor', 'heap02': 'h02b', 'heap03': 'h03b', 'heapn': 'hn',
       'ruin': 'r2', 'overhead': 'o', 'use': 'use', 'route': 'route', 'heap12': 'h12'}


def full_fixture(tmp_path, full):
    """Baseline + a raw draft that regenerates the selected subset of the full Layout."""
    bundle = tmp_path / 'bundles' / RUN / 'all'
    bundle.mkdir(parents=True)
    for key, payload in OLD.items():
        (tmp_path / f'{key}.mesh.json').write_text(payload)
    for key, payload in NEW.items():
        (bundle / f'{key}.mesh.json').write_text(payload)
    baseline = _manifest({k: f'{k}.mesh.json' for k in OLD})
    draft = _manifest({k: f'bundles/{RUN}/all/{k}.mesh.json' for k in NEW})
    groups = {g['slot']['key']: g for g in draft['children']}
    plaza = groups['sector-plaza']['children']
    # Scatter renamed heap 0-3 away and added 1-2 under the same selected prefix.
    plaza[:] = [c for c in plaza if c['slot']['name'] != 'plaza-rubble-west-0-3']
    plaza.append(_obj('plaza-rubble-west-1-2', 'heap12'))
    draft['assets'].pop('heap03')
    groups['sector-ruins-west']['children'].append(_obj(NEW_USE, 'use'))
    groups['sector-overhead']['children'].append(_obj(NEW_ROUTE, 'route'))
    groups['native-colliders']['children'][0]['components'][0]['fields']['Size'] = [40, .31, 120]
    groups['native-colliders']['children'].append(_collider(f'collider-{NEW_USE}-pier-0', [1, 3, 1]))
    groups['native-lights']['children'].extend(_cluster_lights(full))
    base = tmp_path / 'baseline.json'
    raw = tmp_path / f'{RUN}-raw-draft.json'
    base.write_text(json.dumps(baseline))
    raw.write_text(json.dumps(draft))
    return base, raw, baseline, draft


def _names(manifest):
    from modeling.slum03.candidate_scope import nodes
    return {n['slot'].get('name'): key for key, (n, _) in nodes(manifest).items()}


def test_full_scope_accepts_new_keys_scatter_changes_and_ground_colliders(tmp_path, full):
    layout = subset_layout(full)
    base, raw, baseline, draft = full_fixture(tmp_path, full)
    output = tmp_path / 'candidate.json'
    report = compose_candidate(base, raw, layout, output)
    candidate = json.loads(output.read_text())
    names = _names(candidate)
    for name in (NEW_USE, NEW_ROUTE, 'plaza-rubble-west-1-2', 'plaza-rubble-west-0-2', 'factory-floor'):
        assert name in names, name
    assert 'plaza-rubble-west-0-3' not in names
    assert report['absent_baseline_slots'] == [{
        'key': _obj('plaza-rubble-west-0-3', 'x')['slot']['key'], 'name': 'plaza-rubble-west-0-3',
        'parent': 'sector-plaza', 'reason': 'scatter heap not regenerated under selected prefix plaza-rubble-west'}]
    assert candidate['assets']['use']['source'] == f'bundles/{RUN}/all/use.mesh.json'
    # The unselected north heap keeps the baseline declaration and source.
    assert candidate['assets']['heapn'] == baseline['assets']['heapn']
    assert 'local-light-cluster-' in json.dumps(candidate)
    assert check_candidate_scope(baseline, candidate, layout, tmp_path) == []


def _compose_fails(tmp_path, layout, base, raw, draft, match):
    raw.write_text(json.dumps(draft))
    with pytest.raises(ValueError, match=match):
        compose_candidate(base, raw, layout, tmp_path / 'candidate.json')
    assert not (tmp_path / 'candidate.json').exists()


def _child(draft, group, name):
    parent = next(g for g in draft['children'] if g['slot']['key'] == group)
    return parent, next(c for c in parent['children'] if c['slot'].get('name') == name)


def test_selected_new_key_that_was_never_generated_fails(tmp_path, full):
    base, raw, baseline, draft = full_fixture(tmp_path, full)
    parent, node = _child(draft, 'sector-ruins-west', NEW_USE)
    parent['children'].remove(node)
    _compose_fails(tmp_path, subset_layout(full), base, raw, draft, 'not generated')


@pytest.mark.parametrize('case', ['unselected-edit', 'rogue-node', 'unselected-prefix',
                                  'bad-heap-name', 'light-shadow', 'light-unknown'])
def test_full_scope_still_protects_everything_else(tmp_path, full, case):
    base, raw, baseline, draft = full_fixture(tmp_path, full)
    if case == 'unselected-edit':
        _, node = _child(draft, 'sector-plaza', 'factory-floor')
        node['slot']['position'] = [1, 0, 0]
    elif case == 'rogue-node':
        next(g for g in draft['children'] if g['slot']['key'] == 'sector-plaza')['children'].append(
            _obj('rogue-crate', 'use'))
    elif case == 'unselected-prefix':
        _, node = _child(draft, 'sector-plaza', 'plaza-rubble-north-2-9')
        node['components'][0]['fields']['URL'] = '$asset:heap12'
    elif case == 'bad-heap-name':
        _, node = _child(draft, 'sector-plaza', 'plaza-rubble-west-1-2')
        node['slot']['name'] = 'plaza-rubble-west-extra'
    elif case == 'light-shadow':
        light = next(g for g in draft['children'] if g['slot']['key'] == 'native-lights')['children'][0]
        light['components'][0]['fields']['ShadowType'] = 'Hard'
    elif case == 'light-unknown':
        light = next(g for g in draft['children'] if g['slot']['key'] == 'native-lights')['children'][0]
        light['slot']['key'] = 'local-light-cluster-stall-invented'
        light['components'][0]['key'] = 'local-light-cluster-stall-invented-component'
    _compose_fails(tmp_path, subset_layout(full), base, raw, draft, '.')


def test_ground_colliders_follow_the_district_foundation_selection(tmp_path, full):
    base, raw, baseline, draft = full_fixture(tmp_path, full)
    # Without the surface selection the changed ground collider is out of scope.
    keys = tuple(k for k in SUBSET if k != 'district-foundation')
    _, node = _child(draft, 'sector-ground', 'district-foundation')
    node['components'][0]['fields']['URL'] = '$asset:ground'
    draft['assets']['ground'] = {'kind': 'mesh', 'source': f'bundles/{RUN}/all/ground.mesh.json'}
    (tmp_path / 'bundles' / RUN / 'all' / 'ground.mesh.json').write_text('g')
    _compose_fails(tmp_path, subset_layout(full, keys), base, raw, draft, '.')


def test_scope_check_reports_missing_new_node_and_unknown_addition(tmp_path, full):
    layout = subset_layout(full)
    base, raw, baseline, draft = full_fixture(tmp_path, full)
    compose_candidate(base, raw, layout, tmp_path / 'candidate.json')
    candidate = json.loads((tmp_path / 'candidate.json').read_text())
    removed = copy.deepcopy(candidate)
    ruins = next(g for g in removed['children'] if g['slot']['key'] == 'sector-ruins-west')
    ruins['children'] = [c for c in ruins['children'] if c['slot']['name'] != NEW_USE]
    assert check_candidate_scope(baseline, removed, layout, tmp_path)
    added = copy.deepcopy(candidate)
    next(g for g in added['children'] if g['slot']['key'] == 'sector-plaza')['children'].append(
        _obj('density-not-selected', 'use'))
    assert check_candidate_scope(baseline, added, layout, tmp_path)


def test_selected_metadata_without_regenerated_geometry_fails(tmp_path, full):
    from modeling.slum03.density_candidate import regeneration_issues
    layout = subset_layout(full)
    base, raw, baseline, draft = full_fixture(tmp_path, full)
    compose_candidate(base, raw, layout, tmp_path / 'candidate.json')
    candidate = json.loads((tmp_path / 'candidate.json').read_text())
    assert regeneration_issues(candidate, layout, RUN) == []
    stale = copy.deepcopy(candidate)
    stale['assets']['r2'] = baseline['assets']['ruin']  # ruin-west kept old geometry
    _, node = _child(stale, 'sector-ruins-west', 'ruin-west')
    node['components'][0]['fields']['URL'] = '$asset:r2'
    issues = regeneration_issues(stale, layout, RUN)
    assert [(i.code, i.object_key) for i in issues] == [('SELECTED_NOT_REGENERATED', 'ruin-west')]
    other_run = copy.deepcopy(candidate)
    other_run['assets']['use']['source'] = 'bundles/older-run/all/use.mesh.json'
    assert [i.object_key for i in regeneration_issues(other_run, layout, RUN)] == [NEW_USE]
    missing = copy.deepcopy(candidate)
    ruins = next(g for g in missing['children'] if g['slot']['key'] == 'sector-ruins-west')
    ruins['children'] = [c for c in ruins['children'] if c['slot']['name'] != NEW_USE]
    assert [(i.code, i.object_key) for i in regeneration_issues(missing, layout, RUN)] == [
        ('SELECTED_NOT_REGENERATED', NEW_USE)]


def test_recorded_counts_and_hash_must_describe_the_written_candidate(tmp_path, full):
    from modeling.slum03.density_candidate import candidate_inventory, inventory_issues
    layout = subset_layout(full)
    base, raw, baseline, draft = full_fixture(tmp_path, full)
    output = tmp_path / 'candidate.json'
    compose_candidate(base, raw, layout, output)
    recorded = candidate_inventory(output)
    candidate = json.loads(output.read_text())
    assert recorded['sha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert recorded['slots'] == 1 + sum(1 for _ in _walk(candidate['children']))
    assert recorded['mesh_renderers'] == 9 and recorded['colliders'] == 3 and recorded['lights'] == 6
    assert inventory_issues(recorded, output) == []
    assert inventory_issues({**recorded, 'mesh_renderers': 150}, output)
    ruins = next(g for g in candidate['children'] if g['slot']['key'] == 'sector-ruins-west')
    ruins['children'].pop()
    output.write_text(json.dumps(candidate))
    codes = {i.object_key for i in inventory_issues(recorded, output)}
    assert {'sha256', 'slots', 'mesh_renderers'} <= codes


def _walk(children):
    for child in children:
        yield child
        yield from _walk(child.get('children', []))


def _reports(directory):
    return {s: json.loads((directory / f'{s}-report.json').read_text()) for s in SECTORS}


def test_representative_reports_cannot_stand_in_for_a_full_layout(full):
    from modeling.slum03.density_metrics import density_report
    from modeling.slum03.verify_assets import verify_assets
    reports = _reports(REP_RUN)
    issues = verify_assets(full, reports)
    assert {i.object_key for i in issues if i.code == 'LAYOUT_MISMATCH'} >= set(SECTORS)
    density = density_report(full, reports, 'evaluated')
    assert {i['object_key'] for i in density['issues'] if i['code'] == 'LAYOUT_MISMATCH'} == set(SECTORS)
    # One mixed-in sector is enough to fail.
    from modeling.slum03.density_metrics import layout_digest
    mixed = copy.deepcopy(reports)
    for sector, report in mixed.items():
        report['layout_sha256'] = layout_digest(full) if sector != 'forest' else report['layout_sha256']
    assert any(i.code == 'LAYOUT_MISMATCH' and i.object_key == 'forest' for i in verify_assets(full, mixed))


def _geometry(assembly):
    return hashlib.sha256(json.dumps(
        [assembly.kind, assembly.sector, list(assembly.origin),
         [[p.name, p.material, [list(v) for v in p.vertices], [list(f) for f in p.faces]]
          for p in assembly.parts]], allow_nan=False).encode()).hexdigest()


def test_layout_order_does_not_change_geometry_for_the_same_key(full):
    shuffled = replace(full, placements=tuple(reversed(full.placements)))
    sectors = ('ruins-west', 'ruins-north', 'ruins-east', 'shacks', 'market', 'nightlife',
               'yarol', 'overhead', 'plaza', 'ground')
    for sector in sectors:
        first = {a.name: _geometry(a) for a in sector_assemblies(full, sector)}
        second = {a.name: _geometry(a) for a in sector_assemblies(shuffled, sector)}
        assert first == second, sector


def _mesh():
    return {'vertices': [{'position': {'x': 0.123456789, 'y': 0, 'z': 0},
                          'normal': {'x': 0, 'y': 1, 'z': 0},
                          'uvs': [{'$type': '2D', 'uv': {'x': 0.1, 'y': 0}},
                                  {'$type': '2D', 'uv': {'x': 0.5, 'y': 0.5}}]}],
            'submeshes': [{'$type': 'trianglesFlat', 'vertexIndices': [0, 0, 0]}]}


def test_comparison_cannot_hide_mesh_loss_uv_layer_loss_or_rounding(tmp_path):
    from modeling.slum03.verify_assets import compare_geometry_exports
    first, second = tmp_path / 'c' / 'plaza', tmp_path / 'd' / 'plaza'
    first.mkdir(parents=True); second.mkdir(parents=True)
    for d in (first, second):
        (d / 'a.mesh.json').write_text(json.dumps(_mesh()))
        (d / 'b.mesh.json').write_text(json.dumps(_mesh()))
    assert compare_geometry_exports(first.parent, second.parent) == []
    lost_uv = _mesh(); lost_uv['vertices'][0]['uvs'].pop()
    (second / 'a.mesh.json').write_text(json.dumps(lost_uv))
    assert compare_geometry_exports(first.parent, second.parent)
    rounded = _mesh(); rounded['vertices'][0]['position']['x'] = round(0.123456789, 4)
    (second / 'a.mesh.json').write_text(json.dumps(rounded))
    assert compare_geometry_exports(first.parent, second.parent)
    (second / 'a.mesh.json').write_text(json.dumps(_mesh()))
    (second / 'b.mesh.json').unlink()
    assert compare_geometry_exports(first.parent, second.parent)


def test_export_mesh_reduction_on_both_sides_is_still_detected(tmp_path):
    """Identical C/D exports can both be missing meshes; counts come from the build."""
    from modeling.slum03.verify_assets import export_count_issues
    bundles = tmp_path / 'bundles'
    (bundles / 'plaza').mkdir(parents=True)
    reports = {'plaza': {'objects': [{'key': 'a', 'mesh': 'a'}, {'key': 'b', 'mesh': 'b'}]}}
    for name in ('a', 'b'):
        (bundles / 'plaza' / f'mesh_{name}.mesh.json').write_text(json.dumps(_mesh()))
    (bundles / 'plaza' / 'report.json').write_text(json.dumps({'meshes': [
        {'name': 'a', 'file': 'mesh_a.mesh.json'}, {'name': 'b', 'file': 'mesh_b.mesh.json'}]}))
    assert export_count_issues(reports, bundles) == []
    (bundles / 'plaza' / 'mesh_b.mesh.json').unlink()
    (bundles / 'plaza' / 'report.json').write_text(json.dumps({'meshes': [
        {'name': 'a', 'file': 'mesh_a.mesh.json'}]}))
    assert [i.code for i in export_count_issues(reports, bundles)] == ['EXPORT_MESH_COUNT']


def test_gate_c_adopts_only_when_density_and_structure_both_pass():
    from modeling.slum03.density_candidate import gate_c_status
    ok = gate_c_status(density_issues=[], structural_issues=[])
    assert ok['adoptable'] is True
    assert ok['visual'] == ok['walk'] == ok['save_reload'] == 'pending'
    assert ok['status'] == 'offline-adoptable-human-pending'
    for density, structure in (([{'code': 'DENSITY_COUNT'}], []), ([], [{'code': 'SCOPE_NODE'}])):
        result = gate_c_status(density_issues=density, structural_issues=structure)
        assert result['adoptable'] is False
        assert result['visual'] == 'pending'


def test_zone_resources_attribute_every_resource_once(full):
    from modeling.slum03.density_metrics import zone_resources
    manifest = _manifest({})
    groups = {g['slot']['key']: g for g in manifest['children']}
    groups['sector-ruins-west']['children'].append(_obj(NEW_USE, 'use'))
    groups['sector-plaza']['children'].append(_obj('forest-tree-0-0', 'use', 'holo'))
    manifest['children'].append({'slot': {'key': 'p2', 'name': 'P'}, 'components': [
        {'key': 'holo', 'type': 'FrooxEngine.FresnelMaterial', 'fields': {'BlendMode': 'Additive'}}],
        'children': []})
    light = _cluster_light(full)
    groups['native-lights']['children'].append(light)
    groups['native-colliders']['children'].append(_collider(f'collider-{NEW_USE}-pier-0', [1, 1, 1]))
    manifest['children'].append(_group('native-textures', [{
        'slot': {'key': 'driver-panner-scan-object_nightlife-info-ad-driven_1-near', 'name': 'x'},
        'components': [{'key': 'drv', 'type': 'FrooxEngine.Panner2D', 'fields': {}}], 'children': []}]))
    names = [NEW_USE, 'forest-tree-0-0', 'district-foundation', 'factory-floor', 'plaza-rubble-west-0-2',
             'plaza-rubble-west-0-3', 'plaza-rubble-north-2-9', 'ruin-west', 'overhead-west']
    exports = {'all': {'meshes': [{'name': n, 'file': f'{n}.mesh.json', 'vertices': 10, 'triangles': 5,
                                   'submeshes': 1} for n in names]}}
    rows = zone_resources(full, manifest, exports)
    assert sum(r['triangles'] for r in rows.values()) == 5 * len(names)
    assert sum(r['meshes'] for r in rows.values()) == len(names)
    assert rows['northwest']['meshes'] == 2 and rows['northwest']['colliders'] == 2  # ruin-west + new use
    assert rows['southwest']['meshes'] == 1  # overhead-west
    assert rows['background']['transparent_draw_sections'] == 1
    assert rows['shared-ground']['meshes'] == 1 and rows['shared-ground']['colliders'] == 1
    zone = next(z.key for z in full.density.zones
                if z.bounds.x_min <= light['slot']['position'][0] < z.bounds.x_max and
                z.bounds.z_min <= light['slot']['position'][2] < z.bounds.z_max)
    assert rows[zone]['lights'] == 1 and rows[zone]['shadow_lights'] == 0
    assert sum(r['drivers'] for r in rows.values()) == 1
    assert sum(r['lights'] for r in rows.values()) == 1
    assert rows['central-and-other']['meshes'] == 4  # factory floor and three plaza heaps


def _providers(doc, key):
    group = {'slot': {'key': key, 'name': 'Blender_Providers'}, 'components': [], 'children': []}
    doc['children'].append(group)
    return group['children']


def _material_provider(comp):
    return {'slot': {'key': 'provider_' + comp, 'name': comp},
            'components': [{'key': comp, 'type': 'FrooxEngine.PBS_Metallic', 'fields': {'Color': [0, 0, 1]}}],
            'children': []}


def _stub(sector, comp):
    return {'slot': {'key': f'{sector}-provider_{comp}', 'name': comp}, 'components': [], 'children': []}


def _use_material(draft, name, comp):
    _, node = _child(draft, 'sector-ruins-west', name)
    node['components'][1]['fields']['Materials'] = ['$component:' + comp]


@pytest.mark.parametrize('stage', ['full', 'representative'])
def test_reuse_stub_for_new_selected_material_is_ignored_only_in_full(tmp_path, full, stage):
    base, raw, baseline, draft = full_fixture(tmp_path, full)
    layout = subset_layout(full)
    if stage == 'representative':
        # Same raw exporter pattern, but the representative rules stay unchanged.
        layout = replace(layout, density=replace(layout.density, stage='representative'))
        _, node = _child(draft, 'sector-ruins-west', NEW_USE)
        next(g for g in draft['children'] if g['slot']['key'] == 'sector-ruins-west')['children'].remove(node)
        for doc in (draft,):
            groups = {g['slot']['key']: g for g in doc['children']}
            groups['native-colliders']['children'] = [c for c in groups['native-colliders']['children']
                                                      if NEW_USE not in c['slot']['key']]
            groups['native-lights']['children'] = []
        layout = replace(layout, density=replace(layout.density, selected_keys=('ruin-west',)))
        _use_material(draft, 'ruin-west', 'mat_new')
        # Undo the full-only regeneration so only the provider stub differs.
        restored = copy.deepcopy(baseline)
        for group in ('sector-ground', 'sector-plaza', 'native-colliders'):
            index = next(i for i, g in enumerate(draft['children']) if g['slot']['key'] == group)
            draft['children'][index] = next(g for g in restored['children'] if g['slot']['key'] == group)
        for key, payload in OLD.items():
            if key != 'ruin':
                (tmp_path / 'bundles' / RUN / 'all' / f'{key}.mesh.json').write_text(payload)
                draft['assets'][key] = {'kind': 'mesh', 'source': f'bundles/{RUN}/all/{key}.mesh.json'}
        for key in ('use', 'route', 'heap12'):
            draft['assets'].pop(key)
        _, route = _child(draft, 'sector-overhead', NEW_ROUTE)
        next(g for g in draft['children'] if g['slot']['key'] == 'sector-overhead')['children'].remove(route)
    else:
        _use_material(draft, NEW_USE, 'mat_new')
    for doc in (baseline, draft):
        _providers(doc, 'ruins-west-blender_providers')
        _providers(doc, 'market-blender_providers')
    groups = {g['slot']['key']: g for g in draft['children']}
    groups['ruins-west-blender_providers']['children'].append(_material_provider('mat_new'))
    groups['market-blender_providers']['children'].append(_stub('market', 'mat_new'))
    base.write_text(json.dumps(baseline)); raw.write_text(json.dumps(draft))
    output = tmp_path / 'candidate.json'
    if stage == 'representative':
        with pytest.raises(ValueError, match='stub'):
            compose_candidate(base, raw, layout, output)
        return
    report = compose_candidate(base, raw, layout, output)
    names = _names(json.loads(output.read_text()))
    assert 'mat_new' in names and names['mat_new'] == 'provider_mat_new'
    assert [e['slot'] for e in report['raw_ignored_empty_provider_nodes']] == ['market-provider_mat_new']
    # A referenced stub is never ignored.
    output.unlink()
    draft['tests'] = [{'target': '$slot:market-provider_mat_new'}]
    raw.write_text(json.dumps(draft))
    with pytest.raises(ValueError):
        compose_candidate(base, raw, layout, output)


def test_empty_baseline_stub_missing_from_raw_is_kept_verbatim(tmp_path, full):
    base, raw, baseline, draft = full_fixture(tmp_path, full)
    for doc in (baseline, draft):
        _providers(doc, 'ruins-north-blender_providers')
    groups = {g['slot']['key']: g for g in baseline['children']}
    groups['ruins-north-blender_providers']['children'].append(_stub('ruins-north', 'mat_old'))
    base.write_text(json.dumps(baseline)); raw.write_text(json.dumps(draft))
    report = compose_candidate(base, raw, subset_layout(full), tmp_path / 'candidate.json')
    candidate = json.loads((tmp_path / 'candidate.json').read_text())
    kept = next(g for g in candidate['children'] if g['slot']['key'] == 'ruins-north-blender_providers')
    assert kept['children'] == [_stub('ruins-north', 'mat_old')]
    assert [e['slot'] for e in report['raw_absent_baseline_empty_provider_stubs']] == [
        'ruins-north-provider_mat_old']
    # A real (non-empty) protected provider that the raw draft lost still stops composition.
    (tmp_path / 'candidate.json').unlink()
    groups['ruins-north-blender_providers']['children'][0]['components'] = [
        {'key': 'mat_old', 'type': 'FrooxEngine.PBS_Metallic', 'fields': {}}]
    base.write_text(json.dumps(baseline))
    with pytest.raises(ValueError, match='missing|changed'):
        compose_candidate(base, raw, subset_layout(full), tmp_path / 'candidate.json')


def test_native_counts_attribute_full_cluster_lights_to_member_sectors(full):
    from scripts.summarize_offline import native_sector_counts
    manifest = {'slot': {'key': 'root'}, 'components': [], 'children': _cluster_lights(full)}
    counts = native_sector_counts(manifest, full)
    assert sum(row['lights'] for row in counts.values()) == 6
    assert {sector for sector, row in counts.items() if row['lights']} <= {'nightlife', 'market'}
    manifest['children'][0]['slot']['key'] = 'local-light-cluster-stall-invented'
    with pytest.raises(ValueError, match='unattributed'):
        native_sector_counts(manifest, full)


def test_candidate_bytes_do_not_depend_on_hash_seed(tmp_path, full):
    """Independent C/D runs must differ only by run name, never by set iteration order."""
    import subprocess
    import sys
    base, raw, baseline, draft = full_fixture(tmp_path, full)
    script = (
        'import json, sys\n'
        'from dataclasses import replace\n'
        'from pathlib import Path\n'
        'from modeling.slum03.layout import read_layout\n'
        'from modeling.slum03.candidate_scope import compose_candidate\n'
        'full = read_layout(Path(sys.argv[1]))\n'
        'layout = replace(full, density=replace(full.density, selected_keys=tuple(sys.argv[5:])))\n'
        'compose_candidate(Path(sys.argv[2]), Path(sys.argv[3]), layout, Path(sys.argv[4]))\n')
    outputs = []
    for seed in ('1', '2', '3'):
        output = tmp_path / f'candidate-{seed}.json'
        subprocess.run([sys.executable, '-c', script, str(FULL.resolve()), str(base), str(raw), str(output), *SUBSET],
                       check=True, env={**__import__('os').environ, 'PYTHONHASHSEED': seed})
        outputs.append(output.read_bytes())
    assert outputs[0] == outputs[1] == outputs[2]


def test_representative_stage_does_not_keep_missing_baseline_stubs(tmp_path):
    """Full-only leniency must not leak into the approved representative rules."""
    from tests.slum03.test_candidate_scope import fixture, LAYOUT
    base, draft, b, d = fixture(tmp_path)
    b['children'].append({'slot': {'key': 'sector-x-blender_providers', 'name': 'Blender_Providers'},
                          'components': [], 'children': [_stub('sector-x', 'mat_old')]})
    d['children'].append({'slot': {'key': 'sector-x-blender_providers', 'name': 'Blender_Providers'},
                          'components': [], 'children': []})
    base.write_text(json.dumps(b)); draft.write_text(json.dumps(d))
    with pytest.raises(ValueError, match='missing|changed'):
        compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')
