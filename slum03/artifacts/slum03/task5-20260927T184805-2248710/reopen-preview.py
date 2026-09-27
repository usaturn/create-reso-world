"""Offline saved-blend audit and Cycles preview; run via resoloop blender run --blend."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

out = Path(sys.argv[sys.argv.index('--')+1])
sector = out.stem
source = bpy.data.collections[f'Slum03{sector}Source']
export = bpy.data.collections[f'Slum03{sector}Export']
assert source.hide_render and len(source.objects) == len(export.objects)
for obj in source.objects:
    obj.hide_render = True
for obj in export.objects:
    obj.hide_render = False
bpy.context.view_layer.update()
graph = bpy.context.evaluated_depsgraph_get()
all_points = []
items = []
for obj in export.objects:
    eval_obj = obj.evaluated_get(graph)
    evaluated_mesh = eval_obj.to_mesh()
    points = [eval_obj.matrix_world @ v.co for v in evaluated_mesh.vertices]
    assert points and [u.name for u in obj.data.uv_layers if u.active_render] == ['UV0']
    assert 'Col' in obj.data.color_attributes
    all_points.extend(points)
    items.append({'name': obj.name, 'vertices': len(points),
                  'bounds_blender': [[min(v[i] for v in points) for i in range(3)],
                                     [max(v[i] for v in points) for i in range(3)]]})
    eval_obj.to_mesh_clear()
(out.parent / f'{sector}-reopened.json').write_text(json.dumps({
    'source_count': len(source.objects), 'export_count': len(export.objects),
    'source_hidden': source.hide_render, 'objects': items,
    'version': bpy.app.version_string}, indent=2)+'\n')
for material in bpy.data.materials:
    if material.node_tree:
        node = material.node_tree.nodes.get('Principled BSDF')
        if node:
            material.diffuse_color = tuple(node.inputs['Base Color'].default_value)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8
world = bpy.data.worlds.new('Task5PreviewWorld')
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.12, .16, .21, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.2
scene.world = world
scene.render.resolution_x, scene.render.resolution_y = 720, 540
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(out.resolve())
low = Vector([min(v[i] for v in all_points) for i in range(3)])
high = Vector([max(v[i] for v in all_points) for i in range(3)])
target = (low+high)*.5
span = high-low
camera_data = bpy.data.cameras.new('PreviewCamera')
camera = bpy.data.objects.new('PreviewCamera', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
# Blender axes: X east, Y north, Z up. Approach from the intended shop front.
if sector == 'yarol':
    approach = Vector((23, -18, 13))
else:
    approach = Vector((18, 21, 17))
camera.location = target + approach
camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = max(span.x*1.6, span.y*1.5, span.z*1.7)
bpy.ops.render.render(write_still=True)
assert out.is_file() and out.stat().st_size > 1000
print(f'PREVIEW={out} REOPENED={len(items)}')
