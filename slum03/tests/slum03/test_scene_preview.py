"""Breaks caught: a partial scene is rendered as a complete sightline preview."""
import subprocess
from pathlib import Path


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


def test_combined_preview_reads_persisted_custom_labels_and_builds_supplemental_views(tmp_path):
    import json
    from dataclasses import replace
    from modeling.slum03.layout import build_layout, write_layout
    from modeling.slum03.sectors import SECTORS
    layout = build_layout(7)
    label = next(l for l in layout.labels if l.key == 'product-copy')
    changed = replace(layout, labels=tuple(replace(l, offset=(l.offset[0], l.offset[1]+1, l.offset[2]))
                                           if l.key == label.key else l for l in layout.labels))
    source = tmp_path / 'layout.json'
    write_layout(changed, source)
    original = Path('artifacts/slum03/task11-fix2-20260928T0356').resolve()
    for sector in SECTORS:
        (tmp_path / f'{sector}.blend').symlink_to(original / f'{sector}.blend')
    output = tmp_path / 'previews'
    result = subprocess.run(['resoloop', '--command-timeout', '300', 'blender', 'run',
                             'modeling/slum03/preview.py', '--arg=--output', f'--arg={output}',
                             '--arg=--layout', f'--arg={source}', '--json'],
                            capture_output=True, text=True, timeout=320)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((output / 'preview-report.json').read_text())
    assert report['layout_seed'] == 7
    assert report['cameras']['west-detail']['exposure'] >= 1.5
    assert report['cameras']['south-detail']['exposure'] >= 1.5
    assert {'north-graffiti', 'north-activity', 'west-detail', 'south-detail'} <= set(report['cameras'])
    assert all((output / (key + '.png')).is_file() for key in report['cameras'])
    probe = subprocess.run(['resoloop', '--command-timeout', '90', 'blender', 'run',
                            'tests/slum03/blender_preview_layout_probe.py', '--blend',
                            str(output / 'combined-preview.blend'), f'--arg={source}', '--json'],
                           capture_output=True, text=True, timeout=110)
    assert probe.returncode == 0, probe.stdout + probe.stderr
