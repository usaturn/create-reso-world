import pytest
from modeling.slum03 import blender_io
from modeling.slum03 import sectors
from modeling.slum03.layout import build_layout


def test_axis_swap_is_not_a_second_scale():
    assert blender_io.resonite_to_blender((1.0, 2.0, 3.0)) == (1.0, 3.0, 2.0)


def test_unknown_or_unimplemented_sector_fails_explicitly():
    with pytest.raises(KeyError):
        sectors.sector_assemblies(build_layout(), 'unknown')
    with pytest.raises(NotImplementedError):
        sectors.sector_assemblies(build_layout(), 'forest')


def test_registered_sector_builds_actual_mesh():
    assemblies = sectors.sector_assemblies(build_layout(), 'ground')
    assert assemblies and all(a.parts and a.sector == 'ground' for a in assemblies)


def test_builder_rejects_unknown_before_blender_import(tmp_path):
    from modeling.slum03 import build
    with pytest.raises(KeyError):
        build.write_scene('bogus', tmp_path / 'bogus.blend')


def test_ground_build_reports_resonite_bounds_and_stable_export_name(tmp_path):
    import json
    import subprocess
    command = ['resoloop', 'blender', 'run', 'modeling/slum03/build.py',
               '--arg=--sector', '--arg=ground', '--arg=--output',
               f'--arg={tmp_path / "ground.blend"}', '--json']
    subprocess.run(command, check=True, capture_output=True, text=True)
    report = json.loads((tmp_path / 'ground-report.json').read_text())
    assert report['objects'] == [{'key': 'district-foundation', 'kind': 'foundation',
                                  'mesh': 'district-foundation'}]
    assert report['evaluated_bounds']['district-foundation']['minimum'] == pytest.approx([-60, -.3, -60])
    assert report['evaluated_bounds']['district-foundation']['maximum'] == pytest.approx([60, 0, 60])


def test_blockout_exports_one_footprint_per_placement_plus_ground(tmp_path):
    import json
    import subprocess
    subprocess.run(['resoloop', 'blender', 'run', 'modeling/slum03/probe_blender.py',
                    '--arg=--output', f'--arg={tmp_path}', '--arg=--mode',
                    '--arg=blockout', '--json'], check=True, capture_output=True, text=True)
    report = json.loads((tmp_path / 'blockout-probe.json').read_text())
    assert report['placements'] == len(build_layout().placements)
    assert report['source_objects'] == report['export_objects'] == report['placements'] + 1
    assert report['export_names'][0] == 'district-foundation'


def test_builder_records_uv_failure_before_exiting(tmp_path):
    import json
    import subprocess
    script = tmp_path / 'bad_sector.py'
    script.write_text(
        'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd()))\n'
        'from modeling.slum03 import sectors, build, geometry as g\n'
        'def broken(layout, sector):\n'
        '    return [g.Assembly("broken", "bad-face", sector, (0,0,0), '
        '[g.mesh("triangle", [(0,0,0),(1,0,0),(2,0,0)], [(0,1,2)], "rust")])]\n'
        'sectors.REGISTRY["ground"] = broken\n'
        f'build.write_scene("ground", Path({str(tmp_path / "broken.blend")!r}))\n')
    run = subprocess.run(['resoloop', 'blender', 'run', str(script), '--json'],
                         capture_output=True, text=True)
    assert run.returncode != 0
    report = json.loads((tmp_path / 'ground-report.json').read_text())
    assert report['errors'][0]['code'] == 'UV'
    assert not (tmp_path / 'broken.blend').exists()


def test_fixture_render_active_second_layer_and_colors_survive_reopen(tmp_path):
    import json
    import subprocess
    subprocess.run(['resoloop', 'blender', 'run', 'modeling/slum03/probe_blender.py',
                    '--arg=--output', f'--arg={tmp_path}', '--json'],
                   check=True, capture_output=True, text=True)
    probe = json.loads((tmp_path / 'fixture-probe.json').read_text())
    assert probe['uv_layers'] == ['Aux', 'UV0']
    assert probe['render_active_uv'] == 'UV0'
    assert probe['first_face_normal_blender'] == pytest.approx([0, .31622777, -.9486833])
    assert probe['blender_position'] == pytest.approx([1, 3, 2])
    assert probe['face_materials'] == [0, 1]
    assert probe['colors'][2] == pytest.approx([.1, .8, .3, 1])


def test_builder_parent_origin_is_local_not_world(tmp_path):
    import json
    import subprocess
    script = tmp_path / 'nested_sector.py'
    script.write_text(
        'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd()))\n'
        'from modeling.slum03 import sectors, build, geometry as g\n'
        'def nested(layout, sector):\n'
        '    return [g.Assembly("parent", "parent", sector, (10,0,0), '
        '[g.box("p",(0,0,0),(1,1,1),"rust")]), '
        'g.Assembly("child", "child", sector, (5,0,0), '
        '[g.box("c",(0,0,0),(1,1,1),"rust")], {"parent_name":"parent"})]\n'
        'sectors.REGISTRY["ground"] = nested\n'
        f'build.write_scene("ground", Path({str(tmp_path / "nested.blend")!r}))\n')
    subprocess.run(['resoloop', 'blender', 'run', str(script), '--json'],
                   check=True, capture_output=True, text=True)
    report = json.loads((tmp_path / 'ground-report.json').read_text())
    assert report['evaluated_bounds']['child']['minimum'] == pytest.approx([14.5, -.5, -.5])
