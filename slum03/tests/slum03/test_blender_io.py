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
    assert report['objects'] == [{'key': 'district-ground', 'kind': 'foundation',
                                  'mesh': 'district-foundation'}]
    assert report['evaluated_bounds']['district-foundation']['minimum'] == pytest.approx([-60, -.3, -60])
    assert report['evaluated_bounds']['district-foundation']['maximum'] == pytest.approx([60, 0, 60])
    # Reopen the actual artifact rather than trusting only the pre-save report.
    probe = tmp_path / 'ground_reopen.py'
    probe.write_text('import bpy, json, sys\n'
                     'from pathlib import Path\n'
                     'o=bpy.data.collections["Slum03groundExport"].objects["district-foundation"]\n'
                     'top=[p for p in o.data.polygons if p.normal.z > .99]\n'
                     'Path(sys.argv[sys.argv.index("--")+1]).write_text(json.dumps({"top":len(top), '
                     '"uv": [u.name for u in o.data.uv_layers if u.active_render], '
                     '"source_hidden":bpy.data.collections["Slum03groundSource"].hide_render}))\n')
    out = tmp_path / 'ground-reopen.json'
    subprocess.run(['resoloop', 'blender', 'run', str(probe), '--blend',
                    str(tmp_path / 'ground.blend'), f'--arg={out}', '--json'],
                   check=True, capture_output=True, text=True)
    assert json.loads(out.read_text()) == {'top': 1, 'uv': ['UV0'], 'source_hidden': True}


def test_blockout_exports_one_footprint_per_placement_plus_ground(tmp_path):
    import json
    import subprocess
    subprocess.run(['resoloop', 'blender', 'run', 'modeling/slum03/probe_blender.py',
                    '--arg=--output', f'--arg={tmp_path}', '--arg=--mode',
                    '--arg=blockout', '--json'], check=True, capture_output=True, text=True)
    report = json.loads((tmp_path / 'blockout-probe.json').read_text())
    assert report['placements'] == len(build_layout().placements)
    registered = sum(len(sectors.sector_assemblies(build_layout(), sector))
                     for sector in sectors.REGISTRY)
    assert report['source_objects'] == report['export_objects'] == report['placements'] + registered
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


def test_hook_issue_objects_and_metrics_are_not_overwritten(tmp_path):
    import json
    import subprocess
    script = tmp_path / 'hook_sector.py'
    script.write_text(
        'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd()))\n'
        'import bpy, bmesh\nfrom modeling.slum03 import sectors, build, blender_io, geometry as g\n'
        'from modeling.slum03.types import Issue\n'
        'def hooked(bpy, layout, materials, source, export):\n'
        '    part = g.box("part", (0,0,0), (1,1,1), "rust")\n'
        '    mesh = g.merge_assembly(g.Assembly("hook", "hook-extra", "ground", (4,0,0), [part]))\n'
        '    obj, issues = blender_io.create_object(bpy, bmesh, mesh, (4,0,0), materials)\n'
        '    export.objects.link(obj)\n'
        '    return [obj], {"objects": [{"key":"hook-extra", "kind":"hook", "mesh":"hook-extra"}], '
        '"uv_issues":[Issue("UV", "hook-extra", "bad uv")], '
        '"errors":[{"code":"HOOK", "object_key":"hook-extra", "message":"broken"}]}\n'
        'sectors.BLENDER_HOOKS["ground"] = hooked\n'
        f'build.write_scene("ground", Path({str(tmp_path / "hook.blend")!r}))\n')
    result = subprocess.run(['resoloop', 'blender', 'run', str(script), '--json'],
                            capture_output=True, text=True)
    assert result.returncode != 0, result.stdout
    report = json.loads((tmp_path / 'ground-report.json').read_text())
    assert report['objects'] == [
        {'key': 'district-ground', 'kind': 'foundation', 'mesh': 'district-foundation'},
        {'key': 'hook-extra', 'kind': 'hook', 'mesh': 'hook-extra'}]
    assert report['triangles'] == 24 and report['vertices'] == 16 and report['submeshes'] == 2
    assert report['evaluated_bounds']['hook-extra']['minimum'] == pytest.approx([3.5, -.5, -.5])
    assert report['uv_issues'] == [{'code':'UV', 'object_key':'hook-extra', 'message':'bad uv'}]
    assert report['errors'] == [{'code':'UV', 'object_key':'hook-extra', 'message':'bad uv'},
                                {'code':'HOOK', 'object_key':'hook-extra', 'message':'broken'}]
    assert not (tmp_path / 'hook.blend').exists()


def test_blockout_respects_registered_assembly_parent_in_both_collections(tmp_path):
    import json
    import subprocess
    script = tmp_path / 'parent_blockout.py'
    script.write_text(
        'import sys, json\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd()))\n'
        'import bpy\nfrom modeling.slum03 import sectors, probe_blender, geometry as g\n'
        'def nested(layout, sector):\n'
        '    return [g.Assembly("parent", "test-parent", sector, (10,0,0), '
        '[g.box("p",(0,0,0),(1,1,1),"rust")]), '
        'g.Assembly("child", "test-child", sector, (5,0,0), '
        '[g.box("c",(0,0,0),(1,1,1),"rust")], {"parent_name":"test-parent"})]\n'
        'sectors.REGISTRY["ground"] = nested\n'
        f'probe_blender.run(Path({str(tmp_path)!r}), "blockout")\n'
        'bpy.context.view_layer.update()\n'
        'results = {}\n'
        'for collection, name in (("Slum03BlockoutSource", "test-child_Source"), '
        '("Slum03BlockoutExport", "test-child")):\n'
        '    o = bpy.data.collections[collection].objects[name]\n'
        '    results[collection] = {"parent": o.parent.name, '
        '"world_x": float((o.matrix_world @ o.data.vertices[0].co).x)}\n'
        f'Path({str(tmp_path / "parents.json")!r}).write_text(json.dumps(results))\n')
    subprocess.run(['resoloop', 'blender', 'run', str(script), '--json'],
                   check=True, capture_output=True, text=True)
    results = json.loads((tmp_path / 'parents.json').read_text())
    assert results['Slum03BlockoutSource'] == {'parent': 'test-parent_Source', 'world_x': pytest.approx(14.5)}
    assert results['Slum03BlockoutExport'] == {'parent': 'test-parent', 'world_x': pytest.approx(14.5)}


def test_tracked_ground_probe_matches_current_world_coordinate_build():
    import json
    from pathlib import Path
    report = json.loads(Path('artifacts/slum03/probes/ground-report.json').read_text())
    assert report['objects'] == [{'key': 'district-foundation', 'kind': 'foundation',
                                  'mesh': 'district-foundation'}]
    assert report['evaluated_bounds']['district-foundation']['minimum'] == pytest.approx([-60, -.3, -60])
    assert report['evaluated_bounds']['district-foundation']['maximum'] == pytest.approx([60, 0, 60])


def test_hook_uv_issue_alone_blocks_export(tmp_path):
    import json
    import subprocess
    script = tmp_path / 'uv_hook.py'
    script.write_text(
        'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd()))\n'
        'from modeling.slum03 import sectors, build\n'
        'from modeling.slum03.types import Issue\n'
        'def uv_hook(bpy, layout, materials, source, export):\n'
        '    return [], {"uv_issues": [Issue("UV", "test-hook", "bad UV")]}\n'
        'sectors.BLENDER_HOOKS["ground"] = uv_hook\n'
        f'build.write_scene("ground", Path({str(tmp_path / "uv.blend")!r}))\n')
    result = subprocess.run(['resoloop', 'blender', 'run', str(script), '--json'],
                            capture_output=True, text=True)
    assert result.returncode != 0
    report = json.loads((tmp_path / 'ground-report.json').read_text())
    assert report['uv_issues'] == report['errors'] == [
        {'code':'UV', 'object_key':'test-hook', 'message':'bad UV'}]
    assert not (tmp_path / 'uv.blend').exists()


def test_hook_report_bounds_and_counts_include_evaluated_modifier(tmp_path):
    import json
    import subprocess
    script = tmp_path / 'solidify_hook.py'
    script.write_text(
        'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd()))\n'
        'import bpy, bmesh\nfrom modeling.slum03 import sectors, build, blender_io, geometry as g\n'
        'def hooked(bpy, layout, materials, source, export):\n'
        '    sheet = g.mesh("sheet", [(0,0,0),(0,0,1),(1,0,0)], [(0,1,2)], "rust")\n'
        '    merged = g.merge_assembly(g.Assembly("sheet", "thick-hook", "ground", (0,0,0), [sheet]))\n'
        '    obj, issues = blender_io.create_object(bpy, bmesh, merged, (0,0,0), materials)\n'
        '    assert not issues\n'
        '    mod = obj.modifiers.new("Thickness", "SOLIDIFY")\n'
        '    mod.thickness = 1\n    mod.offset = 1\n'
        '    export.objects.link(obj)\n    return [obj], {}\n'
        'sectors.BLENDER_HOOKS["ground"] = hooked\n'
        f'build.write_scene("ground", Path({str(tmp_path / "solid.blend")!r}))\n')
    subprocess.run(['resoloop', 'blender', 'run', str(script), '--json'],
                   check=True, capture_output=True, text=True)
    report = json.loads((tmp_path / 'ground-report.json').read_text())
    assert report['evaluated_bounds']['thick-hook']['maximum'][1] == pytest.approx(1)
    assert report['vertices'] > 11 and report['triangles'] > 13
    assert report['objects'][-1] == {'key':'thick-hook', 'kind':'hook', 'mesh':'thick-hook'}


def test_hook_cannot_export_unreported_object(tmp_path):
    import json
    import subprocess
    script = tmp_path / 'unreported_hook.py'
    script.write_text(
        'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd()))\n'
        'import bpy, bmesh\nfrom modeling.slum03 import sectors, build, blender_io, geometry as g\n'
        'def hooked(bpy, layout, materials, source, export):\n'
        '    part = g.box("part", (0,0,0), (1,1,1), "rust")\n'
        '    mesh = g.merge_assembly(g.Assembly("hook", "forgotten", "ground", (4,0,0), [part]))\n'
        '    obj, issues = blender_io.create_object(bpy, bmesh, mesh, (4,0,0), materials)\n'
        '    assert not issues\n    export.objects.link(obj)\n    return [], {}\n'
        'sectors.BLENDER_HOOKS["ground"] = hooked\n'
        f'build.write_scene("ground", Path({str(tmp_path / "bad.blend")!r}))\n')
    result = subprocess.run(['resoloop', 'blender', 'run', str(script), '--json'],
                            capture_output=True, text=True)
    assert result.returncode != 0
    report = json.loads((tmp_path / 'ground-report.json').read_text())
    assert report['errors'] == [{'code':'MESH', 'object_key':'forgotten',
                                 'message':'export object not returned by sector hook'}]
    assert not (tmp_path / 'bad.blend').exists()


def test_blockout_proxy_does_not_steal_real_placement_name_or_parent(tmp_path):
    import json
    import subprocess
    script = tmp_path / 'collision_blockout.py'
    script.write_text(
        'import sys, json\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd()))\n'
        'import bpy\nfrom modeling.slum03 import sectors, probe_blender, geometry as g\n'
        'def registered(layout, sector):\n'
        '    return [g.Assembly("parent", "district-ground", sector, (10,0,0), '
        '[g.box("p",(0,0,0),(1,1,1),"rust")]), '
        'g.Assembly("child", "district-ground-child", sector, (5,0,0), '
        '[g.box("c",(0,0,0),(1,1,1),"rust")], {"parent_name":"district-ground"})]\n'
        'sectors.REGISTRY["ground"] = registered\n'
        f'probe_blender.run(Path({str(tmp_path)!r}), "blockout")\n'
        'bpy.context.view_layer.update()\n'
        'collections = {name: bpy.data.collections[name] for name in '
        '("Slum03BlockoutSource", "Slum03BlockoutExport")}\n'
        'result = {}\n'
        'for kind, col in collections.items():\n'
        '    real = col.objects["district-ground" + ("_Source" if kind.endswith("Source") else "")]\n'
        '    child = col.objects["district-ground-child" + ("_Source" if kind.endswith("Source") else "")]\n'
        '    proxy = col.objects["Slum03BlockoutProxy__district-ground" + '
        '("_Source" if kind.endswith("Source") else "")]\n'
        '    result[kind] = {"parent": child.parent.name, '
        '"world_x": float((child.matrix_world @ child.data.vertices[0].co).x), '
        '"real_mesh": real.data.name, "proxy_mesh": proxy.data.name}\n'
        f'Path({str(tmp_path / "collision-result.json")!r}).write_text(json.dumps(result))\n')
    subprocess.run(['resoloop', 'blender', 'run', str(script), '--json'],
                   check=True, capture_output=True, text=True)
    result = json.loads((tmp_path / 'collision-result.json').read_text())
    report = json.loads((tmp_path / 'blockout-probe.json').read_text())
    assert (tmp_path / 'blockout.blend').exists()
    assert report['export_names'][:2] == ['district-ground', 'district-ground-child']
    assert report['proxy_names']['district-ground'] == 'Slum03BlockoutProxy__district-ground'
    assert report['placements'] == len(build_layout().placements)
    # The custom ground generator returns two real meshes; plaza is also registered.
    registered = 2 + len(sectors.sector_assemblies(build_layout(), 'plaza'))
    assert report['source_objects'] == report['export_objects'] == report['placements'] + registered
    for kind, row in result.items():
        suffix = '_Source' if kind.endswith('Source') else ''
        assert row['parent'] == 'district-ground' + suffix
        assert row['world_x'] == pytest.approx(14.5)
        assert row['real_mesh'].startswith('Slum03_district-ground_Mesh')
        assert 'Slum03BlockoutProxy__district-ground' in row['proxy_mesh']


def test_blockout_proxy_namespace_never_overwrites_real_assembly_name(tmp_path):
    import json
    import subprocess
    script = tmp_path / 'reserved_name.py'
    script.write_text(
        'import sys, json\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd()))\n'
        'import bpy\nfrom modeling.slum03 import sectors, probe_blender, geometry as g\n'
        'def registered(layout, sector):\n'
        '    return [g.Assembly("real", "Slum03BlockoutProxy__district-ground", sector, '
        '(3,0,0), [g.box("part",(0,0,0),(1,1,1),"rust")])]\n'
        'sectors.REGISTRY["ground"] = registered\n'
        f'probe_blender.run(Path({str(tmp_path)!r}), "blockout")\n'
        'names = list(bpy.data.collections["Slum03BlockoutExport"].objects.keys())\n'
        f'Path({str(tmp_path / "names.json")!r}).write_text(json.dumps(names))\n')
    subprocess.run(['resoloop', 'blender', 'run', str(script), '--json'],
                   check=True, capture_output=True, text=True)
    names = json.loads((tmp_path / 'names.json').read_text())
    report = json.loads((tmp_path / 'blockout-probe.json').read_text())
    assert 'Slum03BlockoutProxy__district-ground' in names
    assert report['export_names'][0] == 'Slum03BlockoutProxy__district-ground'
    assert report['proxy_names']['district-ground'] == 'Slum03BlockoutProxy___district-ground'
    assert 'Slum03BlockoutProxy___district-ground' in names
