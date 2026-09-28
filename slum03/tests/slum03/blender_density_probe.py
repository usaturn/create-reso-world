"""Blender evaluated-data probe: three representative owners and one full-derived small stall.

Usage: resoloop blender run tests/slum03/blender_density_probe.py --arg=--output --arg=PATH --json
"""
import argparse
from copy import deepcopy
import math
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



def _snapshot(mesh):
    """Values in evaluated Blender data, not layer names or component counts."""
    def uv(name):
        layer = mesh.uv_layers.get(name)
        return [tuple(data.uv) for data in layer.data] if layer else None

    colors = mesh.color_attributes.get('Col')
    return {'uv0': uv('UV0'), 'extra_uv': uv('ExtraUV'),
            'colors': [tuple(data.color) for data in colors.data] if colors else None,
            'normals': [tuple(poly.normal) for poly in mesh.polygons],
            'corner_normals': [tuple(data.vector) for data in mesh.corner_normals]}


def _same_attributes(before, after):
    # Blender data-layer values are float32. Saving and reopening must preserve
    # each value to 1e-5; exact identity would be overly sensitive to evaluation.
    for name, channels in (('uv0', 2), ('extra_uv', 2), ('colors', 4), ('normals', 3), ('corner_normals', 3)):
        left, right = before.get(name), after.get(name)
        if not isinstance(left, list) or not isinstance(right, list) or not left or len(left) != len(right):
            raise ValueError(f'{name} missing or changed size')
        if (any(len(point) != channels for point in (*left, *right)) or
                any(not math.isfinite(v) for point in (*left, *right) for v in point)):
            raise ValueError(f'{name} invalid values')
        if len({tuple(round(v, 5) for v in point) for point in left}) < 2:
            raise ValueError(f'{name} constant placeholder')
        if any(not math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-5)
               for x, y in zip(left, right) for a, b in zip(x, y)):
            raise ValueError(f'{name} changed values')
    return True


def _negative_mutations(before):
    rejected = []
    for fault, channel in (('uv0_changed', 'uv0'), ('uv0_missing', 'uv0'),
                           ('extra_uv_changed', 'extra_uv'), ('extra_uv_missing', 'extra_uv'),
                           ('colors_changed', 'colors'), ('colors_missing', 'colors'),
                           ('normals_flipped', 'normals'), ('uv0_zeroed', 'uv0'),
                           ('extra_uv_zeroed', 'extra_uv'), ('colors_zeroed', 'colors'),
                           ('corner_normals_flipped', 'corner_normals')):
        changed = deepcopy(before)
        if fault.endswith('_missing'):
            changed[channel] = None
        elif fault.endswith('_zeroed'):
            changed[channel] = [tuple(0. for _ in p) for p in changed[channel]]
        elif fault in ('normals_flipped', 'corner_normals_flipped'):
            changed[channel][0] = tuple(-v for v in changed[channel][0])  # still unit length
        else:
            v = changed[channel][0]
            changed[channel][0] = (v[0]+.25, *v[1:])
        try:
            _same_attributes(before, changed)
        except ValueError:
            rejected.append(fault)
    return rejected

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
        assert entry['detail_groups'] and entry['evaluated_parts'] and not report['errors'], (key, report['errors'])
        covered = {index for group in entry['detail_groups'] for index in group['part_indices']}
        assert covered == set(range(len(entry['evaluated_parts']))), key
        obj = bpy.data.objects[entry['mesh']]
        uv = obj.data.uv_layers.new(name='ExtraUV')
        for loop in obj.data.loops:
            a, b = obj.data.uv_layers['UV0'].data[loop.index].uv
            uv.data[loop.index].uv = (a+.123+loop.index*.001, b-.089+loop.index*.0005)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        before_obj = obj.evaluated_get(depsgraph)
        before_mesh = before_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        try:
            before = _snapshot(before_mesh)
        finally:
            before_obj.to_mesh_clear()
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str((directory / f'{sector}.blend').resolve()))
        bpy.ops.wm.open_mainfile(filepath=str((directory / f'{sector}.blend').resolve()))
        obj = bpy.data.objects[entry['mesh']]
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        try:
            assert mesh is not None
            after = _snapshot(mesh)
            assert _same_attributes(before, after), key
            if not found:
                rejected_attributes = _negative_mutations(before)
            found['small-stall' if key == small.key else key] = {
                'attribute_values_equal': True, 'corner_normals_equal': True,
                'reopened': True, 'faces': len(mesh.polygons), 'uv0': bool(mesh.uv_layers.get('UV0')),
                'extra_uv': bool(mesh.uv_layers.get('ExtraUV')),
                'colors': bool(mesh.color_attributes.get('Col') and
                               len(mesh.color_attributes['Col'].data) == len(mesh.vertices)),
                'normals': bool(mesh.polygons and
                                all(p.normal.length > .99 for p in mesh.polygons)),
                'groups': len(entry['detail_groups']),
                'physical_parts': len(entry['evaluated_parts']),
                'all_parts_annotated': True,
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
               'rejected_attributes': rejected_attributes,
               'fixture': 'full-derived PARTIAL small stall; not a 97-use build'}
    (output / 'probe.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    assert rejected == ['empty', 'collapsed']
    assert rejected_attributes == ['uv0_changed', 'uv0_missing', 'extra_uv_changed',
                                   'extra_uv_missing', 'colors_changed', 'colors_missing',
                                   'normals_flipped', 'uv0_zeroed',
                                   'extra_uv_zeroed', 'colors_zeroed',
                                   'corner_normals_flipped']
    print(json.dumps(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    run(args.output)
