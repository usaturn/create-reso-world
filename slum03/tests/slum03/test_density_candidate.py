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
