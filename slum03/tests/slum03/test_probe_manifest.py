import json
from pathlib import Path
import pytest
from modeling.slum03 import probe_manifest


def test_probe_manifest_is_owned_and_keeps_assets_relative(tmp_path):
    source = tmp_path / 'bundle'
    source.mkdir()
    (source / 'mesh.mesh.json').write_text('{}')
    manifest = {'schemaVersion': '1', 'ownership': {'key': 'blender_elsewhere'},
                'slot': {'key': 'root', 'name': 'Elsewhere', 'parent': 'Root'},
                'assets': {'mesh': {'kind': 'mesh', 'source': 'mesh.mesh.json'}},
                'components': [{'key': 'ref', 'type': 'Example', 'fields': {'Target': '$slot:root'}}],
                'children': [{'slot': {'key': 'child', 'name': 'Child', 'parent': '$slot:root'}, 'components': []}]}
    (source / 'model.apply.json').write_text(json.dumps(manifest))
    out = tmp_path / 'preview' / 'model.apply.json'
    result = probe_manifest.prepare_probe_manifest(source, out, (1, 2, 3))
    assert result == json.loads(out.read_text())
    assert result['ownership']['key'] == 'slum03'
    assert result['slot'] == {'key': 'root', 'name': 'Slum03_Slum', 'parent': 'Root', 'position': [1, 2, 3]}
    preview = result['children'][0]
    assert preview['slot']['key'] == 'blockout-preview'
    assert preview['slot']['name'] == 'ResoLoop_Test_Slum03_Blockout'
    inner = preview['children'][0]
    assert 'parent' not in inner['slot']
    assert inner['components'][0]['fields']['Target'] == '$slot:blockout-preview-bundle'
    assert inner['children'][0]['slot']['parent'] == '$slot:blockout-preview-bundle'
    assert Path(out.parent / result['assets']['mesh']['source']).resolve() == (source / 'mesh.mesh.json').resolve()
    assert not any(c['slot'].get('parent') == 'Root' for c in preview['children'])


def test_probe_rejects_escaping_assets(tmp_path):
    source = tmp_path / 'bundle'
    source.mkdir()
    (source / 'model.apply.json').write_text(json.dumps({'slot': {'key':'root'}, 'assets': {'evil': {'kind':'mesh', 'source':'../elsewhere'}}}))
    with pytest.raises(ValueError, match='asset'):
        probe_manifest.prepare_probe_manifest(source, tmp_path / 'preview.json', (0, 0, 0))


def test_probe_rejects_explicit_external_parent(tmp_path):
    source = tmp_path / 'bundle'
    source.mkdir()
    (source / 'model.apply.json').write_text(json.dumps({
        'schemaVersion': '1', 'slot': {'key': 'root', 'name': 'Bundle', 'parent': 'Root'},
        'children': [{'slot': {'key': 'rogue', 'name': 'Rogue', 'parent': 'Root'}}]}))
    with pytest.raises(ValueError, match='parent'):
        probe_manifest.prepare_probe_manifest(source, tmp_path / 'preview.json', (0, 0, 0))


@pytest.mark.parametrize('parent', ['$slot:root', '$slot:missing'])
def test_probe_rejects_parent_reference_outside_source_bundle(tmp_path, parent):
    source = tmp_path / 'bundle'
    source.mkdir()
    (source / 'model.apply.json').write_text(json.dumps({
        'schemaVersion': '1', 'slot': {'key': 'source-root', 'name': 'Source', 'parent': 'Root'},
        'children': [{'slot': {'key': 'child', 'name': 'Child', 'parent': parent}}]}))
    out = tmp_path / 'preview.json'
    with pytest.raises(ValueError, match='parent'):
        probe_manifest.prepare_probe_manifest(source, out, (0, 0, 0))
    assert not out.exists()
