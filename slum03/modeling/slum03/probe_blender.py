"""Offline Blender 5 probe. Run with resoloop blender run (never directly via Python)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modeling.slum03 import blender_io, geometry, sectors
from modeling.slum03.layout import build_layout
from modeling.slum03.materials import make_blender_materials


def _fixture(bpy, bmesh, output: Path):
    materials = make_blender_materials()
    collection = bpy.data.collections.new('Slum03ProbeExport')
    bpy.context.scene.collection.children.link(collection)
    # Unequal XYZ triangle, intentionally non-symmetric in both geometry and UVs.
    first = geometry.mesh('front', [(0, 0, 0), (2, 0, 0), (0, 1, 3)], [(0, 1, 2)], 'concrete_raw')
    second = geometry.mesh('side', [(0, 0, 0), (0, 1, 3), (-1, 0, 1)], [(0, 1, 2)], 'steel_bare')
    merged = geometry.merge_assembly(geometry.Assembly('fixture', 'asymmetric-fixture', 'probe',
                                                         (1, 2, 3), [first, second]))
    obj, issues = blender_io.create_object(bpy, bmesh, merged, (1, 2, 3), materials, uv_exempt=True)
    if issues:
        raise RuntimeError(issues)
    # UV0 remains the render-active UV0 even with a second channel present.
    aux = obj.data.uv_layers['UV0']
    aux.name = 'Aux'
    uv0 = obj.data.uv_layers.new(name='UV0')
    primary = ((.1, .2), (.8, .25), (.15, .9))
    auxiliary = ((0, 0), (.3, 0), (.2, .4))
    for loop, uv in zip(obj.data.polygons[0].loop_indices, reversed(primary)):
        uv0.data[loop].uv = uv
    for loop, uv in zip(obj.data.polygons[0].loop_indices, reversed(auxiliary)):
        aux.data[loop].uv = uv
    uv0.active_render = True
    colors = [(.2, .3, .4, 1), (.7, .1, .2, 1), (.1, .8, .3, 1), (.4, .5, .9, 1), (.6, .3, .2, 1), (.9, .2, .6, 1)]
    blender_io.write_colors(obj, colors)
    collection.objects.link(obj)
    return obj


def _blockout(bpy, bmesh):
    layout = build_layout()
    source = bpy.data.collections.new('Slum03BlockoutSource')
    export = bpy.data.collections.new('Slum03BlockoutExport')
    bpy.context.scene.collection.children.link(source)
    bpy.context.scene.collection.children.link(export)
    mats = make_blender_materials()
    export_names = []
    for sector in sectors.SECTORS:
        if sector not in sectors.REGISTRY:
            continue
        for a in sectors.sector_assemblies(layout, sector):
            obj, issues = blender_io.create_object(bpy, bmesh, geometry.merge_assembly(a), a.origin, mats)
            if issues:
                raise RuntimeError(issues)
            obj.name = f'{a.name}_Source'
            source.objects.link(obj)
            copy = obj.copy()
            copy.data = obj.data.copy()
            copy.name = a.name
            export.objects.link(copy)
            export_names.append(copy.name)
    for p in layout.placements:
        # Lightweight footprint for every Placement, including unregistered sectors.
        part = geometry.box(p.key, (0, p.params.get('local_y_min', 0) + p.size[1] / 2, 0),
                            p.size, 'concrete_dark')
        obj, issues = blender_io.create_object(bpy, bmesh, geometry.merge_assembly(
            geometry.Assembly(p.kind, p.key, p.sector, p.origin, [part])), p.origin, mats, uv_exempt=True)
        if issues:
            raise RuntimeError(issues)
        obj.rotation_euler[2] = __import__('math').radians(-p.yaw_deg)
        obj.name = f'{p.key}_Source'
        source.objects.link(obj)
        copy = obj.copy()
        copy.data = obj.data.copy()
        copy.name = p.key
        export.objects.link(copy)
        export_names.append(copy.name)
    return {'export_names': export_names, 'placements': len(layout.placements), 'source_objects': len(source.objects),
            'export_objects': len(export.objects), 'export_collection': export.name}


def run(output: Path, mode: str = 'fixture'):
    import bpy
    import bmesh
    if bpy.data.filepath:
        raise RuntimeError('probe requires an unsaved new Blender scene')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    output.mkdir(parents=True, exist_ok=True)
    if mode == 'blockout':
        details = _blockout(bpy, bmesh)
    else:
        _fixture(bpy, bmesh, output)
        details = {'export_collection': 'Slum03ProbeExport'}
    dest = output / ('fixture.blend' if mode == 'fixture' else 'blockout.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(dest.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(dest.resolve()))
    if mode == 'fixture':
        obj = bpy.data.collections['Slum03ProbeExport'].objects['asymmetric-fixture']
        me = obj.data
        uv0, aux = me.uv_layers['UV0'], me.uv_layers['Aux']
        poly = me.polygons[0]
        loops = list(poly.loop_indices)
        details.update({
            'blender_position': list(obj.location), 'first_face_normal_blender': list(poly.normal),
            'first_face_vertices_blender': [list(me.vertices[me.loops[i].vertex_index].co) for i in loops],
            'uv_layers': [layer.name for layer in me.uv_layers],
            'render_active_uv': next(layer.name for layer in me.uv_layers if layer.active_render),
            'uv0': [list(uv0.data[i].uv) for i in loops],
            'aux': [list(aux.data[i].uv) for i in loops],
            'colors': [list(c.color) for c in me.color_attributes['Col'].data],
            'material_order': [m.name for m in me.materials],
            'face_materials': [p.material_index for p in me.polygons],
            'color_domain': me.color_attributes['Col'].domain,
            'color_type': me.color_attributes['Col'].data_type,
            'principled_sockets': [i.name for i in bpy.data.materials['Slum03_concrete_raw'].node_tree.nodes['Principled BSDF'].inputs],
        })
        if details['render_active_uv'] != 'UV0' or details['uv_layers'] != ['Aux', 'UV0']:
            raise RuntimeError('UV channels lost during blend save/reopen')
    details['blender_version'] = bpy.app.version_string
    details['blend'] = str(dest.resolve())
    (output / f'{mode}-probe.json').write_text(json.dumps(details, indent=2) + '\n', encoding='utf-8')
    print('SLUM03_PROBE=' + json.dumps(details))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['fixture', 'blockout'], default='fixture')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    run(args.output, args.mode)
