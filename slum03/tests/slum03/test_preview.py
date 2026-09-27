"""Small offline rendering regression; never touches a live world."""
import json
import subprocess
from pathlib import Path


def test_plaza_preview_renders_without_blender_deprecation_warnings(tmp_path):
    blend = tmp_path / 'plaza.blend'
    subprocess.run(['resoloop', 'blender', 'run', 'modeling/slum03/build.py',
                    '--arg=--sector', '--arg=plaza', '--arg=--output', f'--arg={blend}', '--json'],
                   check=True, capture_output=True, text=True)
    script = Path('artifacts/slum03/task3-20260927T173627-1798712/render_plaza.py')
    image = tmp_path / 'preview.png'
    result = subprocess.run(['resoloop', 'blender', 'run', str(script), '--blend', str(blend),
                             f'--arg={image}', '--json'], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)['data']
    assert image.stat().st_size > 1000
    assert 'DeprecationWarning' not in data['standardError'] + data['standardOutput']
