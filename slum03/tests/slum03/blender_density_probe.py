"""Blender evaluated-data probe: three representative owners and one full-derived small stall.

Usage: resoloop blender run tests/slum03/blender_density_probe.py --arg=--output --arg=PATH --json
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from modeling.slum03.build import write_scene
from modeling.slum03.evaluated_detail import observe_detail
from modeling.slum03.geometry import Assembly, box, merge_assembly
from modeling.slum03.layout import read_layout, write_layout


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    rep = read_layout(ROOT / 'content/slum03/density-representative-layout.json')
    full = read_layout(ROOT / 'content/slum03/density-full-layout.json')
    small = next(p for p in full.placements if p.kind == 'stall' and p.key.startswith('density-')
                 and p.sector == 'market')
    # This is an explicit full-derived PARTIAL fixture, not an all-97 build.
    partial = replace(full, placements=tuple(p for p in full.placements
                                              if not p.key.startswith("density-")) + (small,))
    write_layout(partial, output / 'small-partial-layout.json')
    found = {}
    for key, sector, layout in (('ruin-west', 'ruins-west', rep),
                                ('shack-row', 'shacks', rep),
                                ('market-west', 'market', rep),
                                (small.key, 'market', partial)):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        directory = output / key if key != small.key else output / 'small-stall'
        directory.mkdir()
        report = write_scene(sector, directory / f'{sector}.blend', layout)
        entry = next(e for e in report['objects'] if e.get('placement_key') == key)
        assert entry['detail_groups'] and not report['errors'], (key, report['errors'])
        obj = bpy.data.objects[entry['mesh']]
        uv = obj.data.uv_layers.new(name='ExtraUV')
        for loop in obj.data.loops:
            uv.data[loop.index].uv = (.125, .375)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str((directory / f'{sector}.blend').resolve()))
        bpy.ops.wm.open_mainfile(filepath=str((directory / f'{sector}.blend').resolve()))
        obj = bpy.data.objects[entry['mesh']]
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        try:
            assert mesh is not None
            found['small-stall' if key == small.key else key] = {
                'reopened': True, 'faces': len(mesh.polygons), 'uv0': bool(mesh.uv_layers.get('UV0')),
                'extra_uv': bool(mesh.uv_layers.get('ExtraUV') and
                                 all(tuple(round(c, 3) for c in mesh.uv_layers['ExtraUV'].data[i].uv) == (.125, .375)
                                     for i in range(len(mesh.loops)))),
                'colors': bool(mesh.color_attributes.get('Col') and
                               len(mesh.color_attributes['Col'].data) == len(mesh.vertices)),
                'normals': bool(mesh.polygons and
                                all(p.normal.length > .99 for p in mesh.polygons)),
                'groups': len(entry['detail_groups']),
                'source': str(directory / f'{sector}.blend')}
        finally:
            evaluated.to_mesh_clear()
    a = Assembly('stall', 'fault', 'market', (0., 0., 0.),
                 [box('stock', (0., 1., 0.), (.2, .2, .2), 'steel_dark')],
                 {'detail_groups': [{'id': 'item', 'category': 'merchandise', 'part_indices': [0]}]})
    m = merge_assembly(a)
    rejected = []
    for defect, geometry in [('empty', {'vertices': [], 'faces': []}),
                             ('collapsed', {'vertices': [(0., 0., 0.) for _ in m.vertices],
                                            'faces': m.faces})]:
        try:
            observe_detail(a, geometry)
        except ValueError:
            rejected.append(defect)
    summary = {'objects': found, 'rejected': rejected,
               'fixture': 'full-derived PARTIAL small stall; not a 97-use build'}
    (output / 'probe.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    assert rejected == ['empty', 'collapsed']
    print(json.dumps(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    run(args.output)
