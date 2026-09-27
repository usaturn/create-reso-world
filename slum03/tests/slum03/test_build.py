"""Breaks caught: editable GN and realized export conflated; saved data layers lost."""
import json
import subprocess
from pathlib import Path
import pytest


@pytest.mark.parametrize('sector', ['plaza', 'forest'])
def test_saved_sector_keeps_editable_sources_and_realized_export(sector, tmp_path):
    blend = tmp_path / f'{sector}.blend'
    run = subprocess.run(['resoloop', '--command-timeout', '180', 'blender', 'run',
                          'modeling/slum03/build.py', '--arg=--sector', f'--arg={sector}',
                          '--arg=--output', f'--arg={blend}', '--json'],
                         capture_output=True, text=True, timeout=200)
    assert run.returncode == 0, run.stderr + run.stdout[-3000:]
    report = json.loads((tmp_path / f'{sector}-report.json').read_text())
    assert report['objects'] and report['triangles'] > 0
    assert report['evaluated_bounds'] and not report['errors']
    probe = subprocess.run(['resoloop', '--command-timeout', '120', 'blender', 'run',
                            'tests/slum03/blender_asset_probe.py', '--blend', str(blend),
                            f'--arg={sector}', '--json'], capture_output=True, text=True, timeout=140)
    assert probe.returncode == 0, probe.stderr + probe.stdout[-3000:]


def test_checked_in_layout_is_accepted_by_current_layout_validator():
    from modeling.slum03.layout import read_layout, build_layout
    assert read_layout(Path('content/slum03/layout.json')) == build_layout()


def test_fixed_label_faces_approved_positive_z_and_follows_anchor():
    run = subprocess.run(['resoloop', '--command-timeout', '60', 'blender', 'run',
                          'tests/slum03/blender_label_probe.py', '--json'],
                         capture_output=True, text=True, timeout=70)
    assert run.returncode == 0, run.stdout + run.stderr


@pytest.mark.parametrize('defect,code', [('uv','UV_MISSING'), ('material','MATERIAL_MISSING')])
def test_build_rejects_broken_evaluated_uv_or_material(defect, code, tmp_path):
    output = tmp_path / 'ground.blend'
    result = subprocess.run(['resoloop', '--command-timeout', '90', 'blender', 'run',
                             'tests/slum03/blender_corrupt_export.py',
                             f'--arg={defect}', f'--arg={output}', '--json'],
                            capture_output=True, text=True, timeout=105)
    assert result.returncode != 0
    report = json.loads((tmp_path / 'ground-report.json').read_text())
    assert any(e['code'] == code for e in report['errors'])
    assert not output.exists()
