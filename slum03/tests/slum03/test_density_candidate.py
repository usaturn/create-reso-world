"""Offline density CLI rejects wrong stage, root, existing output and state creation."""
import json
import subprocess
import sys
from pathlib import Path

from modeling.slum03.layout import read_layout
from modeling.slum03.density_metrics import layout_digest


def run(*args):
    return subprocess.run([sys.executable, 'scripts/build_density.py', *map(str, args)],
                          capture_output=True, text=True)


def test_blockout_stage_rejected_without_output(tmp_path):
    run_name = 'density-test-do-not-create'
    state = Path('.resoloop/slum03/state/slum03.json')
    before = state.read_bytes() if state.exists() else None
    result = run('--stage', 'blockout', '--base-manifest', 'content/slum03/density-baseline.json',
                 '--layout', 'content/slum03/density-blockout-layout.json', '--run', run_name, '--root-y', '4.5')
    assert result.returncode != 0
    assert 'blockout' in result.stderr.lower()
    assert not (Path('artifacts/slum03') / run_name).exists()
    assert (state.read_bytes() if state.exists() else None) == before


def test_representative_stage_rejects_full_layout(tmp_path):
    result = run('--stage', 'representative', '--base-manifest', 'content/slum03/density-baseline.json',
                 '--layout', 'content/slum03/density-full-layout.json', '--run', 'density-test-no-create', '--root-y', '4.5')
    assert result.returncode != 0
    assert not Path('artifacts/slum03/density-test-no-create').exists()


def test_summary_rejects_different_saved_layout_digest(tmp_path):
    first, second = 'density-test-first', 'density-test-second'
    saved = Path('content/slum03/density-representative-layout.json').read_bytes()
    for name, payload in [(first, saved), (second, saved + b'\n')]:
        target = tmp_path / 'artifacts/slum03' / name
        target.mkdir(parents=True)
        (target / 'layout.json').write_bytes(payload)
    script = Path('scripts/summarize_offline.py').resolve()
    result = subprocess.run([sys.executable, str(script), '--first', first, '--second', second,
                             '--layout', f'artifacts/slum03/{first}/layout.json'],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'Layout bytes/digest differ' in result.stderr


def test_evaluated_density_uses_legacy_object_key_when_placement_key_absent():
    from modeling.slum03.density_metrics import density_report
    layout = read_layout(Path('content/slum03/density-representative-layout.json'))
    report = {'layout_sha256': layout_digest(layout), 'objects': [
        {'key': 'ruin-west-annex', 'mesh': 'ruin-west-annex', 'vertices': 10, 'faces': 4}],
        'evaluated_bounds': {'ruin-west-annex': {'minimum': [-40, 0, -34],
                                                  'maximum': [-30, 8, -20]}}}
    result = density_report(layout, {'ruins-west': report}, 'evaluated')
    assert not [i for i in result['issues'] if i['code'] == 'GEOMETRY_MISSING'
                and i['object_key'] == 'ruin-west-annex']


def test_planar_river_evaluated_bounds_do_not_invalidate_density():
    from modeling.slum03.density_metrics import density_report
    layout = read_layout(Path('content/slum03/density-representative-layout.json'))
    report = {'layout_sha256': layout_digest(layout), 'objects': [
        {'key': 'river', 'mesh': 'river', 'vertices': 4, 'faces': 1}],
        'evaluated_bounds': {'river': {'minimum': [-200, -4, 78], 'maximum': [230, -4, 112]}}}
    result = density_report(layout, {'road-river': report}, 'evaluated')
    assert not [i for i in result['issues'] if i['object_key'] == 'river']


def test_legacy_offline_cli_records_copied_layout(tmp_path, monkeypatch, capsys):
    import scripts.build_offline as script
    import sys
    artifact = tmp_path / 'artifact'; artifact.mkdir()
    (artifact / 'layout.json').write_text('{}')
    bundle = tmp_path / 'bundles'; bundle.mkdir()
    monkeypatch.setattr(script, 'build_raw_run', lambda *a: (artifact, bundle, {},
        {'schemaVersion': '1', 'ownership': {'key': 'slum03'},
         'slot': {'key': 'root', 'name': 'Slum03_Slum', 'parent': 'Root'},
         'assets': {}, 'components': [], 'children': []}, 4.5))
    monkeypatch.setattr(script, 'SECTORS', ())
    monkeypatch.setattr(sys, 'argv', ['build_offline.py', '--run', 'cli-test', '--layout', str(artifact / 'layout.json')])
    monkeypatch.chdir(tmp_path)
    script.main()
    provenance = json.loads((tmp_path / 'content/slum03/cli-test-candidate-provenance.json').read_text())
    assert provenance['layout'] == str(artifact / 'layout.json')


def test_export_source_must_match_current_bundle_even_when_bytes_match(tmp_path, monkeypatch):
    from modeling.slum03.density_candidate import verify_export_sources
    import modeling.slum03.pipeline as pipeline
    monkeypatch.setattr(pipeline, 'SECTORS', ('ground',))
    manifest_dir = tmp_path / 'content'; manifest_dir.mkdir()
    bundle = manifest_dir / 'bundles' / 'now' / 'ground'; bundle.mkdir(parents=True)
    (bundle / 'mesh_real.mesh.json').write_bytes(b'exact')
    (bundle / 'report.json').write_text(json.dumps({'meshes': [{'name': 'real', 'file': 'mesh_real.mesh.json'}]}))
    (bundle / 'model.apply.json').write_text(json.dumps({
        'schemaVersion': '1', 'ownership': {'key': 'blender_ground'},
        'slot': {'key': 'root', 'name': 'Ground', 'parent': 'Root'},
        'components': [], 'children': [{'slot': {'key': 'object', 'name': 'real'},
                                         'components': [{'key': 'mesh_provider', 'type': 'FrooxEngine.StaticMesh',
                                                         'fields': {'URL': '$asset:mesh_real'}}]}],
        'assets': {'mesh_real': {'kind': 'mesh', 'source': 'mesh_real.mesh.json'}}}))
    current = {'mesh_real': {'kind': 'mesh', 'source': 'bundles/now/ground/mesh_real.mesh.json'}}
    verify_export_sources(current, manifest_dir / 'bundles' / 'now', manifest_dir)
    for wrong_source in ('bundles/other/ground/mesh_real.mesh.json',
                         'bundles/now/ground/mesh_wrong.mesh.json'):
        wrong = manifest_dir / wrong_source
        wrong.parent.mkdir(parents=True, exist_ok=True)
        wrong.write_bytes(b'exact')
        try:
            verify_export_sources({'mesh_real': {'kind': 'mesh', 'source': wrong_source}},
                                  manifest_dir / 'bundles' / 'now', manifest_dir)
        except ValueError as exc:
            assert 'source' in str(exc) or 'export' in str(exc)
        else:
            raise AssertionError(f'accepted same-byte wrong export source: {wrong_source}')


def test_unmoved_material_reuse_stub_removed_only_when_empty_and_unreferenced(tmp_path):
    from modeling.slum03.density_candidate import prune_unmoved_reuse_stubs
    from tests.slum03.test_candidate_scope import fixture, LAYOUT
    base, draft, baseline, raw = fixture(tmp_path)
    for doc in (baseline, raw):
        doc['children'].append({'slot': {'key': 'sector-old-blender_providers', 'name': 'Blender_Providers'},
                                 'components': [], 'children': []})
        doc['children'][2]['components'] = []
        doc['children'][-1]['children'].append({'slot': {'key': 'provider_shared', 'name': 'shared'},
            'components': [{'key': 'shared', 'type': 'FrooxEngine.PBS_Metallic', 'fields': {}}], 'children': []})
    raw['children'][-1]['children'].append({'slot': {'key': 'sector-old-provider_shared', 'name': 'shared'},
                                            'components': [], 'children': []})
    cleaned, evidence = prune_unmoved_reuse_stubs(raw, baseline, read_layout(LAYOUT))
    assert len(cleaned['children'][-1]['children']) == 1
    assert evidence[0]['slot'] == 'sector-old-provider_shared'
    assert evidence[0]['unchanged_provider'] == 'provider_shared'
    assert raw['children'][-1]['children'][-1]['slot']['key'] == 'sector-old-provider_shared'
    raw['tests'] = [{'target': '$slot:sector-old-provider_shared'}]
    try:
        prune_unmoved_reuse_stubs(raw, baseline, read_layout(LAYOUT))
    except ValueError as exc:
        assert 'referenced' in str(exc)
    else:
        raise AssertionError('removed referenced raw stub')


def test_selected_sector_empty_stub_for_unchanged_earlier_material_is_removed(tmp_path):
    from modeling.slum03.density_candidate import prune_unmoved_reuse_stubs
    from tests.slum03.test_candidate_scope import fixture, LAYOUT
    base, draft, b, d = fixture(tmp_path)
    for doc in (b, d):
        doc['children'][2]['components'] = []
        doc['children'].append({'slot': {'key': 'sector-plaza-blender_providers', 'name': 'Blender_Providers'},
                                'components': [], 'children': [{'slot': {'key': 'provider_shared', 'name': 'shared'},
                                 'components': [{'key': 'shared', 'type': 'FrooxEngine.PBS_Metallic',
                                                 'fields': {}}], 'children': []}]})
        doc['children'].append({'slot': {'key': 'sector-ruins-west-blender_providers',
                                         'name': 'Blender_Providers'}, 'components': [], 'children': []})
    d['children'][-1]['children'].append({'slot': {'key': 'sector-ruins-west-provider_shared',
                                                  'name': 'shared'}, 'components': [], 'children': []})
    normalized, evidence = prune_unmoved_reuse_stubs(d, b, read_layout(LAYOUT))
    assert not normalized['children'][-1]['children']
    assert evidence[0]['unchanged_provider'] == 'provider_shared'
