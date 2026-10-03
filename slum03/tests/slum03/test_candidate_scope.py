"""A selected mesh may change; unrelated declarations and referenced files may not."""
import copy
import json
from pathlib import Path

import pytest

from modeling.slum03.candidate_scope import check_candidate_scope, compose_candidate
from modeling.slum03.layout import read_layout


LAYOUT = Path('content/slum03/density-representative-layout.json')


def fixture(tmp_path):
    base = tmp_path / 'baseline.json'
    draft = tmp_path / 'fixture-raw-draft.json'
    export = tmp_path / 'bundles' / 'fixture' / 'ground'
    export.mkdir(parents=True)
    for name, payload in [('old.mesh.json', b'old'), ('new.mesh.json', b'new'),
                          ('untouched.mesh.json', b'untouched')]:
        (tmp_path / name).write_bytes(payload)
        (export / name).write_bytes(payload)
    def obj(name, asset, material='shared'):
        return {'slot': {'key': 'object_' + name, 'name': name}, 'components': [
            {'key': 'mesh_' + name, 'type': 'FrooxEngine.StaticMesh', 'fields': {'URL': '$asset:' + asset}},
            {'key': 'renderer_' + name, 'type': 'FrooxEngine.MeshRenderer',
             'fields': {'Mesh': '$component:mesh_' + name, 'Materials': ['$component:' + material]}}], 'children': []}
    def manifest(asset):
        return {'schemaVersion': '1', 'ownership': {'key': 'slum03'},
                'slot': {'key': 'root', 'name': 'Slum03_Slum', 'parent': 'Root', 'position': [0, 4.5, 0]},
                'components': [], 'assets': {
                    'chosen': {'kind': 'mesh', 'source': asset},
                    'untouched': {'kind': 'mesh', 'source': 'untouched.mesh.json'}},
                'children': [obj('ruin-west', 'chosen'), obj('shack-west', 'untouched'),
                             {'slot': {'key': 'providers', 'name': 'Providers'}, 'components': [
                                 {'key': 'shared', 'type': 'FrooxEngine.PBS_Metallic', 'fields': {'Color': [1, 0, 0]}}],
                              'children': []}, obj('shack-row', 'chosen'), obj('market-west', 'chosen')]}
    b, d = manifest('old.mesh.json'), manifest('bundles/fixture/ground/new.mesh.json')
    d['assets']['untouched']['source'] = 'bundles/fixture/ground/untouched.mesh.json'
    base.write_text(json.dumps(b)); draft.write_text(json.dumps(d))
    return base, draft, b, d


def test_protected_asset_sources_and_bytes_unchanged(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    output = tmp_path / 'candidate.json'
    report = compose_candidate(base, draft, read_layout(LAYOUT), output)
    candidate = json.loads(output.read_text())
    assert candidate['assets']['untouched']['source'] == 'untouched.mesh.json'
    assert (output.parent / candidate['assets']['untouched']['source']).read_bytes() == b'untouched'
    assert candidate['assets']['chosen']['source'] == 'bundles/fixture/ground/new.mesh.json'
    assert not check_candidate_scope(b, candidate, read_layout(LAYOUT), tmp_path)
    assert candidate['children'][1] == b['children'][1]  # entire unselected subtree
    assert candidate['children'][2] == b['children'][2]  # shared provider unchanged
    assert candidate['assets']['untouched'] == b['assets']['untouched']
    assert report['protected_changes'] == 0


def test_shared_provider_edit_rejected(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    d['children'][2]['components'][0]['fields']['Color'] = [0, 1, 0]
    draft.write_text(json.dumps(d))
    # Shared old provider may never be edited even if selected renderer uses it.
    with pytest.raises(ValueError, match='provider|shared'):
        compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')


@pytest.mark.parametrize('mutation', [
    lambda m: m['children'].pop(1),
    lambda m: m['children'][1]['slot'].__setitem__('name', 'renamed'),
    lambda m: m['children'][1]['slot'].__setitem__('key', 'object_ruin-west'),
    lambda m: m['slot'].__setitem__('position', [1, 4.5, 0]),
])
def test_unselected_regeneration_drift_rejected(tmp_path, mutation):
    base, draft, b, d = fixture(tmp_path)
    mutation(d)
    draft.write_text(json.dumps(d))
    with pytest.raises(ValueError):
        compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')


def test_relative_source_cannot_be_rebased_to_other_directory(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    with pytest.raises(ValueError, match='parent'):
        compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'other' / 'candidate.json')


def test_scope_detects_asset_bytes_or_source_mutation(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    candidate = copy.deepcopy(b)
    candidate['assets']['untouched']['source'] = 'old.mesh.json'
    assert check_candidate_scope(b, candidate, read_layout(LAYOUT), tmp_path)
    candidate['assets']['untouched']['source'] = 'untouched.mesh.json'
    baseline_dir = tmp_path / 'baseline-files'
    baseline_dir.mkdir()
    (baseline_dir / 'untouched.mesh.json').write_bytes(b'untouched')
    (tmp_path / 'untouched.mesh.json').write_bytes(b'tampered')
    issues = check_candidate_scope(b, candidate, read_layout(LAYOUT), tmp_path, baseline_dir=baseline_dir)
    assert any(i.code == 'SCOPE_ASSET_BYTES' and i.object_key == 'untouched' for i in issues)


def test_identical_shared_provider_relocation_in_raw_draft_preserves_baseline(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    for manifest in (b, d):
        provider = manifest['children'][2]
        provider['slot']['key'] = 'provider_pool'
        manifest['children'].append({'slot': {'key': 'sector-a-blender_providers', 'name': 'Blender_Providers'},
                                     'components': [], 'children': []})
        manifest['children'].append({'slot': {'key': 'sector-b-blender_providers', 'name': 'Blender_Providers'},
                                     'components': [], 'children': []})
        manifest['children'].remove(provider)
        provider['slot']['key'] = 'provider_shared'
        manifest['children'][-1 if manifest is b else -2]['children'].append(provider)
    d['children'][-1]['children'].append({'slot': {'key': 'sector-b-provider_shared', 'name': 'shared'},
                                          'components': [], 'children': []})
    base.write_text(json.dumps(b)); draft.write_text(json.dumps(d))
    output = tmp_path / 'candidate.json'
    report = compose_candidate(base, draft, read_layout(LAYOUT), output)
    assert json.loads(output.read_text())['children'][-1]['children'][0] == b['children'][-1]['children'][0]
    assert report['raw_ignored_empty_provider_nodes'][0]['slot'] == 'sector-b-provider_shared'
    assert report['raw_material_relocations'][0]['from_parent'] == 'sector-b-blender_providers'
    assert report['raw_material_relocations'][0]['raw_parent'] == 'sector-a-blender_providers'


def test_new_selected_collider_provenance_is_draft(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    d['children'].append({'slot': {'key': 'collider-ruin-west-pier', 'name': 'pier'},
                          'components': [{'key': 'collider-ruin-west-pier-box',
                                          'type': 'FrooxEngine.BoxCollider', 'fields': {'Size': [1, 2, 1]}}],
                          'children': []})
    draft.write_text(json.dumps(d))
    report = compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')
    assert report['object_sources']['collider-ruin-west-pier'] == 'draft'


def test_selected_asset_must_resolve_inside_manifest_parent(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    d['assets']['chosen']['source'] = '../outside.mesh.json'
    assert any(i.code == 'SCOPE_ASSET_SOURCE' for i in
               check_candidate_scope(b, d, read_layout(LAYOUT), tmp_path))


def test_unreferenced_new_provider_is_out_of_scope(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    b['children'][2]['slot']['key'] = 'sector-market-blender_providers'
    d = copy.deepcopy(b)
    d['children'][2]['children'].append({'slot': {'key': 'provider_unrelated', 'name': 'unused'},
        'components': [{'key': 'unused', 'type': 'FrooxEngine.PBS_Metallic', 'fields': {}}], 'children': []})
    assert any(i.code == 'SCOPE_NEW_NODE' for i in
               check_candidate_scope(b, d, read_layout(LAYOUT), tmp_path))


def test_raw_draft_new_unrelated_node_rejected(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    d['children'].append({'slot': {'key': 'unrelated', 'name': 'unrelated'}, 'components': [], 'children': []})
    draft.write_text(json.dumps(d))
    with pytest.raises(ValueError, match='unrelated'):
        compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')


def test_annex_collider_is_not_selected_by_ruin_west_prefix(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    box = {'slot': {'key': 'collider-ruin-west-annex', 'name': 'annex Collider'},
           'components': [{'key': 'collider-ruin-west-annex-box', 'type': 'FrooxEngine.BoxCollider',
                           'fields': {'Size': [4, 4, 4]}}], 'children': []}
    b['children'].append(copy.deepcopy(box))
    d['children'].append(copy.deepcopy(box))
    d['children'][-1]['components'][0]['fields']['Size'] = [6, 6, 6]
    base.write_text(json.dumps(b)); draft.write_text(json.dumps(d))
    assert any(i.object_key == 'collider-ruin-west-annex' for i in
               check_candidate_scope(b, d, read_layout(LAYOUT), tmp_path))
    with pytest.raises(ValueError, match='collider-ruin-west-annex'):
        compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')


def test_reachable_new_material_provider_is_added_with_old_shared_provider_untouched(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    for manifest in (b, d):
        manifest['children'].append({'slot': {'key': 'sector-market-blender_providers',
                                               'name': 'Blender_Providers'}, 'components': [], 'children': []})
    d['children'][0]['components'][1]['fields']['Materials'].append('$component:new_paint')
    d['children'][-1]['children'].append({
        'slot': {'key': 'provider_new_paint', 'name': 'new_paint'},
        'components': [{'key': 'new_paint', 'type': 'FrooxEngine.PBS_Metallic',
                        'fields': {'AlbedoColor': [0.2, 0.4, 0.8, 1]}}], 'children': []})
    base.write_text(json.dumps(b)); draft.write_text(json.dumps(d))
    result = compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')
    saved = json.loads((tmp_path / 'candidate.json').read_text())
    assert saved['children'][-1]['children'][0] == d['children'][-1]['children'][0]
    assert saved['children'][2] == b['children'][2]
    assert result['object_sources']['provider_new_paint'] == 'draft'


def test_unreachable_new_provider_cycle_is_rejected(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    for manifest in (b, d):
        manifest['children'].append({'slot': {'key': 'sector-market-blender_providers',
                                               'name': 'Blender_Providers'}, 'components': [], 'children': []})
    for key, other in [('a', 'b'), ('b', 'a')]:
        d['children'][-1]['children'].append({
            'slot': {'key': 'provider_' + key, 'name': key},
            'components': [{'key': key, 'type': 'FrooxEngine.PBS_Metallic',
                            'fields': {'AlbedoTexture': '$component:' + other}}], 'children': []})
    assert {i.object_key for i in check_candidate_scope(b, d, read_layout(LAYOUT), tmp_path)
            if i.code == 'SCOPE_NEW_NODE'} == {'provider_a', 'provider_b'}
    draft.write_text(json.dumps(d))
    with pytest.raises(ValueError):
        compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')


def test_nonmaterial_provider_relocation_is_not_r8(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    for manifest in (b, d):
        manifest['children'].extend([
            {'slot': {'key': f'sector-{sector}-blender_providers', 'name': 'Blender_Providers'},
             'components': [], 'children': []} for sector in ('old', 'new')])
    provider = {'slot': {'key': 'provider_shared', 'name': 'shared'},
                'components': [{'key': 'shared', 'type': 'FrooxEngine.NoiseTexture', 'fields': {}}],
                'children': []}
    b['children'][2]['components'] = []
    d['children'][2]['components'] = []
    b['children'][-2]['children'].append(copy.deepcopy(provider))
    d['children'][-1]['children'].append(copy.deepcopy(provider))
    base.write_text(json.dumps(b)); draft.write_text(json.dumps(d))
    with pytest.raises(ValueError, match='provider_shared'):
        compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')


def test_referenced_empty_provider_stub_is_not_r8(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    for manifest in (b, d):
        manifest['children'].extend([
            {'slot': {'key': f'sector-{sector}-blender_providers', 'name': 'Blender_Providers'},
             'components': [], 'children': []} for sector in ('old', 'new')])
    provider = {'slot': {'key': 'provider_shared', 'name': 'shared'},
                'components': [{'key': 'shared', 'type': 'FrooxEngine.PBS_Metallic', 'fields': {}}],
                'children': []}
    b['children'][2]['components'] = []
    d['children'][2]['components'] = []
    b['children'][-2]['children'].append(copy.deepcopy(provider))
    d['children'][-1]['children'].append(copy.deepcopy(provider))
    stub = {'slot': {'key': 'sector-old-provider_shared', 'name': 'shared'},
            'components': [], 'children': []}
    d['children'][-2]['children'].append(stub)
    d['cameras'] = {'bad': {'target': '$slot:sector-old-provider_shared'}}
    base.write_text(json.dumps(b)); draft.write_text(json.dumps(d))
    with pytest.raises(ValueError, match='stub|referenced|sector-old-provider_shared'):
        compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')


def test_protected_draft_source_other_run_rejected_even_with_identical_bytes(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    current = tmp_path / 'current-raw-draft.json'
    for run in ('old', 'current', 'other'):
        folder = tmp_path / 'bundles' / run / 'ground'
        folder.mkdir(parents=True)
        (folder / 'untouched.mesh.json').write_bytes(b'untouched')
    (tmp_path / 'bundles/current/ground/new.mesh.json').write_bytes(b'new')
    d['assets']['chosen']['source'] = 'bundles/current/ground/new.mesh.json'
    b['assets']['untouched']['source'] = 'bundles/old/ground/untouched.mesh.json'
    d['assets']['untouched']['source'] = 'bundles/other/ground/untouched.mesh.json'
    base.write_text(json.dumps(b)); current.write_text(json.dumps(d))
    with pytest.raises(ValueError, match='source|run'):
        compose_candidate(base, current, read_layout(LAYOUT), tmp_path / 'candidate.json')


def test_protected_draft_source_wrong_file_same_bytes_rejected(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    current = tmp_path / 'current-raw-draft.json'
    for run, filename in (('old', 'untouched.mesh.json'), ('current', 'alternate.mesh.json')):
        folder = tmp_path / 'bundles' / run / 'ground'
        folder.mkdir(parents=True)
        (folder / filename).write_bytes(b'untouched')
    (tmp_path / 'bundles/current/ground/new.mesh.json').write_bytes(b'new')
    d['assets']['chosen']['source'] = 'bundles/current/ground/new.mesh.json'
    b['assets']['untouched']['source'] = 'bundles/old/ground/untouched.mesh.json'
    d['assets']['untouched']['source'] = 'bundles/current/ground/alternate.mesh.json'
    base.write_text(json.dumps(b)); current.write_text(json.dumps(d))
    with pytest.raises(ValueError, match='source'):
        compose_candidate(base, current, read_layout(LAYOUT), tmp_path / 'candidate.json')


def test_selected_material_reaches_new_texture_provider_and_asset(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    for doc in (b, d):
        doc['children'].append({'slot': {'key': 'sector-market-blender_providers',
                                         'name': 'Blender_Providers'}, 'components': [], 'children': []})
    paint = tmp_path / 'bundles/fixture/market/paint.png'
    paint.parent.mkdir(parents=True)
    paint.write_bytes(b'png')
    d['assets']['paint_map'] = {'kind': 'texture', 'source': 'bundles/fixture/market/paint.png'}
    d['children'][0]['components'][1]['fields']['Materials'].append('$component:new_paint')
    d['children'][-1]['children'].extend([
        {'slot': {'key': 'provider_new_paint', 'name': 'new_paint'}, 'components': [
            {'key': 'new_paint', 'type': 'FrooxEngine.PBS_Metallic',
             'fields': {'AlbedoTexture': '$component:new_tex'}}], 'children': []},
        {'slot': {'key': 'provider_new_tex', 'name': 'new_tex'}, 'components': [
            {'key': 'new_tex', 'type': 'FrooxEngine.StaticTexture2D',
             'fields': {'URL': '$asset:paint_map'}}], 'children': []}])
    base.write_text(json.dumps(b)); draft.write_text(json.dumps(d))
    result = compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')
    saved = json.loads((tmp_path / 'candidate.json').read_text())
    assert saved['assets']['paint_map'] == {'kind': 'texture', 'source': 'bundles/fixture/market/paint.png'}
    assert {n['slot']['key'] for n in saved['children'][-1]['children']} == {'provider_new_paint', 'provider_new_tex'}
    assert result['asset_sources']['paint_map']['origin'] == 'draft'


def test_new_node_with_selected_name_cannot_bypass_scope(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    d['children'].append({'slot': {'key': 'unrelated', 'name': 'ruin-west'},
                          'components': [], 'children': []})
    issues = check_candidate_scope(b, d, read_layout(LAYOUT), tmp_path)
    assert any(i.code == 'SCOPE_NEW_NODE' and i.object_key == 'unrelated' for i in issues)


def test_forged_selected_name_cannot_root_new_provider_reachability(tmp_path):
    base, draft, baseline, candidate = fixture(tmp_path)
    for manifest in (baseline, candidate):
        manifest['children'].append({'slot': {'key': 'sector-market-blender_providers',
                                               'name': 'Blender_Providers'}, 'components': [], 'children': []})
    candidate['children'][-1]['children'].append({
        'slot': {'key': 'provider_extra', 'name': 'ruin-west'},
        'components': [
            {'key': 'forged_mesh', 'type': 'FrooxEngine.StaticMesh',
             'fields': {'URL': '$asset:chosen'}},
            {'key': 'forged_render', 'type': 'FrooxEngine.MeshRenderer',
             'fields': {'Mesh': '$component:forged_mesh', 'Materials': ['$component:forged_mat']}},
            {'key': 'forged_mat', 'type': 'FrooxEngine.PBS_Metallic', 'fields': {}}],
        'children': []})
    issues = check_candidate_scope(baseline, candidate, read_layout(LAYOUT), tmp_path)
    assert any(i.code == 'SCOPE_NEW_NODE' and i.object_key == 'provider_extra' for i in issues)
    base.write_text(json.dumps(baseline)); draft.write_text(json.dumps(candidate))
    with pytest.raises(ValueError, match='provider_extra'):
        compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')


def test_unidentified_draft_name_cannot_disable_source_run_checks(tmp_path):
    base, draft, baseline, candidate = fixture(tmp_path)
    unidentifiable = tmp_path / 'draft.json'
    unidentifiable.write_text(json.dumps(candidate))
    with pytest.raises(ValueError, match='run|draft'):
        compose_candidate(base, unidentifiable, read_layout(LAYOUT), tmp_path / 'candidate.json')
    assert not (tmp_path / 'candidate.json').exists()


def test_run_name_containing_raw_draft_and_revision_is_accepted(tmp_path):
    base, _, baseline, candidate = fixture(tmp_path)
    run = 'density-raw-draft-check'
    folder = tmp_path / 'bundles' / run / 'ground'
    folder.mkdir(parents=True)
    for key, filename, payload in (('chosen', 'new.mesh.json', b'new'),
                                   ('untouched', 'untouched.mesh.json', b'untouched')):
        (folder / filename).write_bytes(payload)
        candidate['assets'][key]['source'] = f'bundles/{run}/ground/{filename}'
    draft = tmp_path / f'{run}-raw-draft-fix2.json'
    draft.write_text(json.dumps(candidate))
    result = compose_candidate(base, draft, read_layout(LAYOUT), tmp_path / 'candidate.json')
    assert result['protected_changes'] == 0
    assert json.loads((tmp_path / 'candidate.json').read_text())['assets']['untouched']['source'] == 'untouched.mesh.json'


def test_representative_candidate_limits_are_sized_from_its_own_content(tmp_path):
    import math
    from modeling.slum03.pipeline import _count
    base, draft, b, d = fixture(tmp_path)
    b['limits'] = {'expandedNodes': 5}  # stale baseline value must not leak
    base.write_text(json.dumps(b))
    output = tmp_path / 'candidate.json'
    compose_candidate(base, draft, read_layout(LAYOUT), output)
    candidate = json.loads(output.read_text())
    content = {k: v for k, v in candidate.items() if k != 'limits'}
    assert candidate['limits'] == {'expandedNodes': math.ceil(_count(content) * 1.2)}
    assert candidate['limits']['expandedNodes'] >= _count(content)
