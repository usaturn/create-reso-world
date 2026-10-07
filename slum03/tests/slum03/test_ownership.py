"""Reject external targets, malformed references and unsafe paths before emission."""
import json

import pytest
from modeling.slum03 import pipeline
from tests.slum03.test_pipeline import _setup


def test_foreign_ownership_references_rejected(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch)
    path = directory / 'ground' / 'model.apply.json'
    data = json.loads(path.read_text())
    data['children'][0]['children'][0]['components'][2]['fields']['Anchor'] = '$slot:foreign-world'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='foreign|unresolved'):
        pipeline.merge_bundles(directory)


@pytest.mark.parametrize('ref', ['$asset:missing', '$component:missing', '$member:missing.Value',
                                '$slot-member:outside.Position', '$asset:',
                                '$slot-member:object_driven.', '$component:mesh_a.BadField'])
def test_invalid_refs_rejected(tmp_path, monkeypatch, ref):
    directory = _setup(tmp_path, monkeypatch)
    path = directory / 'plaza' / 'model.apply.json'
    data = json.loads(path.read_text())
    data['children'][0]['children'][0]['components'][2]['fields']['Anchor'] = ref
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='reference|foreign|unresolved|malformed'):
        pipeline.merge_bundles(directory)


@pytest.mark.parametrize('source', ['../outside.mesh.json', '/tmp/foreign.mesh.json',
                                    'https://foreign.example/mesh', '', 'missing.mesh.json'])
def test_unsafe_asset_sources_rejected(tmp_path, monkeypatch, source):
    directory = _setup(tmp_path, monkeypatch)
    path = directory / 'plaza' / 'model.apply.json'
    data = json.loads(path.read_text())
    data['assets']['mesh_a']['source'] = source
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='asset|source'):
        pipeline.merge_bundles(directory)


def test_symlink_asset_escape_rejected(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch)
    asset = directory / 'plaza' / 'mesh_a.mesh.json'
    asset.unlink()
    outside = tmp_path / 'outside.mesh.json'
    outside.write_bytes(b'foreign')
    asset.symlink_to(outside)
    with pytest.raises(ValueError, match='asset|source'):
        pipeline.merge_bundles(directory)


def test_bundle_cannot_change_parent_or_own_outside_root(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch)
    path = directory / 'plaza' / 'model.apply.json'
    data = json.loads(path.read_text())
    data['children'][0]['slot']['parent'] = 'Root'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='parent|foreign'):
        pipeline.merge_bundles(directory)


def test_write_rejects_external_asset_and_leaves_input_unchanged(tmp_path):
    m = {'assets': {'mesh': {'kind': 'mesh', 'source': '/tmp/foreign.mesh.json'}}}
    with pytest.raises(ValueError, match='asset|source'):
        pipeline.write_unified_manifest(m, tmp_path / 'out.json')
    assert m['assets']['mesh']['source'] == '/tmp/foreign.mesh.json'
    assert not (tmp_path / 'out.json').exists()


def test_local_root_reference_rebased_to_sector_slot(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch)
    path = directory / 'plaza' / 'model.apply.json'
    data = json.loads(path.read_text())
    data['children'][0]['children'][0]['components'][2]['fields']['Anchor'] = '$slot:root'
    path.write_text(json.dumps(data))
    merged = pipeline.merge_bundles(directory)
    driven = merged['children'][1]['children'][0]['children'][0]
    assert driven['components'][2]['fields']['Anchor'] == '$slot:sector-plaza'


def test_unrecognized_top_level_mutations_rejected(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch)
    path = directory / 'ground' / 'model.apply.json'
    data = json.loads(path.read_text())
    data['commands'] = [{'target': '$slot:object_a', 'action': 'delete'}]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='bundle|unexpected'):
        pipeline.merge_bundles(directory)


def test_cross_sector_refs_rejected_even_if_global_key_exists(tmp_path, monkeypatch):
    directory = _setup(tmp_path, monkeypatch)
    path = directory / 'plaza' / 'model.apply.json'
    data = json.loads(path.read_text())
    data['children'][0]['children'][0]['components'][2]['fields']['Anchor'] = '$slot:sector-ground'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='reference'):
        pipeline.merge_bundles(directory)


def test_write_never_accepts_a_renamed_owned_root(tmp_path, monkeypatch):
    m = pipeline.merge_bundles(_setup(tmp_path, monkeypatch))
    directory = tmp_path / 'bundles' / 'rev'
    for asset in m['assets'].values():
        asset['source'] = str((directory / asset['source']).resolve())
    m['slot']['name'] = 'User_World_Root'
    with pytest.raises(ValueError, match='ownership|root'):
        pipeline.write_unified_manifest(m, tmp_path / 'slum03.json')
