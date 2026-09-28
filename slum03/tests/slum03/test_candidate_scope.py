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
    draft = tmp_path / 'draft.json'
    for name, payload in [('old.mesh.json', b'old'), ('new.mesh.json', b'new'),
                          ('untouched.mesh.json', b'untouched')]:
        (tmp_path / name).write_bytes(payload)
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
    b, d = manifest('old.mesh.json'), manifest('new.mesh.json')
    base.write_text(json.dumps(b)); draft.write_text(json.dumps(d))
    return base, draft, b, d


def test_protected_asset_sources_and_bytes_unchanged(tmp_path):
    base, draft, b, d = fixture(tmp_path)
    output = tmp_path / 'candidate.json'
    report = compose_candidate(base, draft, read_layout(LAYOUT), output)
    candidate = json.loads(output.read_text())
    assert candidate['assets']['untouched']['source'] == 'untouched.mesh.json'
    assert (output.parent / candidate['assets']['untouched']['source']).read_bytes() == b'untouched'
    assert candidate['assets']['chosen']['source'] == 'new.mesh.json'
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
    base.write_text(json.dumps(b)); draft.write_text(json.dumps(d))
    output = tmp_path / 'candidate.json'
    compose_candidate(base, draft, read_layout(LAYOUT), output)
    assert json.loads(output.read_text())['children'][-1]['children'][0] == b['children'][-1]['children'][0]


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
