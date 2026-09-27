"""Breaks caught: a partial scene is rendered as a complete sightline preview."""
import subprocess


def test_preview_rejects_incomplete_scene(tmp_path):
    result = subprocess.run(['resoloop', '--command-timeout', '60', 'blender', 'run',
                             'modeling/slum03/preview.py', '--arg=--output', f'--arg={tmp_path}',
                             '--json'], capture_output=True, text=True, timeout=70)
    assert result.returncode != 0
    assert 'missing sector' in (result.stdout + result.stderr).lower()
    assert not list(tmp_path.glob('*.png'))


def test_isolated_preview_saves_camera_scene_without_claiming_full_visibility(tmp_path):
    import json
    blend = tmp_path / 'plaza.blend'
    subprocess.run(['resoloop', '--command-timeout', '180', 'blender', 'run',
                    'modeling/slum03/build.py', '--arg=--sector', '--arg=plaza',
                    '--arg=--output', f'--arg={blend}', '--json'],
                   check=True, capture_output=True, text=True, timeout=200)
    out = tmp_path / 'previews'
    result = subprocess.run(['resoloop', '--command-timeout', '180', 'blender', 'run',
                             'modeling/slum03/preview.py', '--arg=--output', f'--arg={out}',
                             '--arg=--sector', '--arg=plaza', '--json'],
                            capture_output=True, text=True, timeout=200)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (out / 'plaza-preview.blend').is_file()
    assert json.loads((out / 'preview-report.json').read_text())['visibility']['status'] == 'not-tested'
