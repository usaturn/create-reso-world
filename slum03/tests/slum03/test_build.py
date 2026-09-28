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


@pytest.mark.parametrize('defect,code', [
    ('uv', 'UV_MISSING'), ('uv-flat', 'UV_DEGENERATE'),
    ('uv-nan', 'UV_NONFINITE'), ('material', 'MATERIAL_MISSING')])
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


def test_fixed_product_copy_is_unoccluded_at_designated_ar_eye():
    scene = Path('artifacts/slum03/task11-c-20260927T2158/previews/combined-preview.blend')
    assert scene.is_file()
    result = subprocess.run(['resoloop', '--command-timeout', '90', 'blender', 'run',
                             'tests/slum03/blender_copy_visibility_probe.py', '--blend', str(scene),
                             '--json'], capture_output=True, text=True, timeout=105)
    assert result.returncode == 0, result.stdout + result.stderr


def test_custom_persisted_layout_drives_mesh_hook_and_native_collider(tmp_path):
    import json, subprocess
    from dataclasses import replace
    from modeling.slum03.layout import build_layout, write_layout, validate_layout
    from modeling.slum03.native.colliders import collider_slots
    layout = build_layout(7)
    changed = replace(layout, placements=tuple(
        replace(p, origin=(p.origin[0] + (1 if p.key == 'forest' else -1), p.origin[1], p.origin[2]))
        if p.key in ('ruin-west', 'forest') else p for p in layout.placements))
    assert not validate_layout(changed)
    path = tmp_path / 'custom-layout.json'
    write_layout(changed, path)
    for sector in ('ruins-west', 'forest'):
        output = tmp_path / f'{sector}.blend'
        result = subprocess.run(['resoloop', '--command-timeout', '180', 'blender', 'run',
                                 'modeling/slum03/build.py', '--arg=--layout', f'--arg={path}',
                                 '--arg=--sector', f'--arg={sector}', '--arg=--output', f'--arg={output}',
                                 '--json'], capture_output=True, text=True, timeout=200)
        assert result.returncode == 0, result.stdout + result.stderr
    ruin = json.loads((tmp_path / 'ruins-west-report.json').read_text())['evaluated_bounds']['ruin-west']
    baseline = json.loads(Path('artifacts/slum03/task11-fix2-20260928T0356/ruins-west-report.json').read_text())['evaluated_bounds']['ruin-west']
    assert abs(ruin['minimum'][0] - baseline['minimum'][0] + 1) < .001
    boxes = collider_slots(changed, {})
    west = next(n for n in boxes if n['slot']['key'] == 'collider-ruin-west')
    assert west['slot']['position'][0] == -39
    assert ruin['minimum'][0] <= west['slot']['position'][0] <= ruin['maximum'][0]
    baseline_path = tmp_path / 'seed7-layout.json'
    write_layout(layout, baseline_path)
    baseline_output = tmp_path / 'baseline' / 'forest.blend'
    result = subprocess.run(['resoloop', '--command-timeout', '180', 'blender', 'run',
                             'modeling/slum03/build.py', '--arg=--layout', f'--arg={baseline_path}',
                             '--arg=--sector', '--arg=forest', '--arg=--output', f'--arg={baseline_output}',
                             '--json'], capture_output=True, text=True, timeout=200)
    assert result.returncode == 0, result.stdout + result.stderr
    forest = json.loads((tmp_path / 'forest-report.json').read_text())['evaluated_bounds']
    seed7_forest = json.loads((baseline_output.parent / 'forest-report.json').read_text())['evaluated_bounds']
    for key in ('forest-tree-0-0', 'forest-patch-0-0'):
        assert abs(forest[key]['minimum'][0] - seed7_forest[key]['minimum'][0] - 1) < .001
    baseline_forest = json.loads(Path('artifacts/slum03/task11-fix2-20260928T0356/forest-report.json').read_text())['evaluated_bounds']
    assert forest['forest-tree-0-0'] != baseline_forest['forest-tree-0-0']
    assert forest['forest-patch-0-0'] != baseline_forest['forest-patch-0-0']


def test_v2_vertex_wear_is_stable_per_owner_and_tracks_joints():
    from modeling.slum03.geometry import Assembly, box, merge_assembly
    from modeling.slum03.vcolor import vertex_colors_v2
    a = Assembly('ruin', 'wear-test', 'ruins-west', (0, 0, 0),
                 [box('wall', (0, 1, 0), (2, 2, .2), 'concrete_stained')])
    m = merge_assembly(a)
    joints = ((-1., 0., 0.),)
    first = vertex_colors_v2(m, a.origin, 260927, 'wear-test', joints)
    assert first == vertex_colors_v2(m, a.origin, 260927, 'wear-test', joints)
    assert first != vertex_colors_v2(m, a.origin, 260927, 'other-owner', joints)
    assert first != vertex_colors_v2(m, a.origin, 260927, 'wear-test', ())


def test_blender_probe_evaluates_three_representatives_and_small_open_stall(tmp_path):
    import subprocess, json
    target = tmp_path / 'density-probe'
    result = subprocess.run(['resoloop', '--command-timeout', '300', 'blender', 'run',
                             'tests/slum03/blender_density_probe.py', '--arg=--output',
                             f'--arg={target}', '--json'], capture_output=True, text=True, timeout=320)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    summary = json.loads((target / 'probe.json').read_text())
    assert set(summary['objects']) == {'ruin-west', 'shack-row', 'market-west', 'small-stall'}
    assert all(x['uv0'] and x['extra_uv'] and x['colors'] and x['normals']
               and x['faces'] > 0 for x in summary['objects'].values())
    assert summary['rejected'] == ['empty', 'collapsed']
    assert all(x.get('reopened') and x.get('attribute_values_equal') and x.get('corner_normals_equal')
               for x in summary['objects'].values())
    assert summary.get('rejected_attributes') == ['uv0_changed', 'uv0_missing',
        'extra_uv_changed', 'extra_uv_missing', 'colors_changed', 'colors_missing',
        'normals_flipped', 'uv0_zeroed', 'extra_uv_zeroed', 'colors_zeroed',
        'corner_normals_flipped']
