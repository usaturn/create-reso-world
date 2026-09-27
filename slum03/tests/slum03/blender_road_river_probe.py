"""Reopen an offline sector blend, audit evaluated meshes and render three views.

Run with `resoloop blender run ... --blend road-river.blend --arg=OUTPUT_DIR`.
Coordinates in this script are Blender X/Y/Z, unlike the source Resonite X/Y/Z.
"""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


output = Path(sys.argv[sys.argv.index('--')+1])
output.mkdir(parents=True, exist_ok=True)
source = bpy.data.collections['Slum03road-riverSource']
export = bpy.data.collections['Slum03road-riverExport']
assert bpy.data.filepath.endswith('road-river.blend')
scene = bpy.context.scene
bpy.context.view_layer.update()
evaluated = bpy.context.evaluated_depsgraph_get()
mesh_bounds = {}
for obj in export.objects:
    e = obj.evaluated_get(evaluated)
    m = e.to_mesh()
    try:
        coords = [e.matrix_world @ v.co for v in m.vertices]
        mesh_bounds[obj.name] = {
            'minimum': [min(p.x for p in coords), min(p.z for p in coords), min(p.y for p in coords)],
            'maximum': [max(p.x for p in coords), max(p.z for p in coords), max(p.y for p in coords)],
        }
    finally:
        e.to_mesh_clear()
all_uv0 = all(any(u.name == 'UV0' and u.active_render for u in o.data.uv_layers)
              for o in export.objects)
all_col = all('Col' in o.data.color_attributes for o in export.objects)
result = {'source_hidden': source.hide_render, 'objects': len(export.objects),
          'all_uv0': all_uv0, 'all_col': all_col,
          'minimum_visible_local_y': min(b['minimum'][1] for b in mesh_bounds.values()),
          'deck_y': None,
          'water_y': mesh_bounds['river']['maximum'][1],
          'evaluated_bounds': mesh_bounds,
          'blender_version': bpy.app.version_string}
# Use actual walkable horizontal polygons, not a height deduced from the railing.
bridge = export.objects['bridge']
result['deck_y'] = max((bridge.matrix_world @ v.co).z for poly in bridge.data.polygons
                       if bridge.data.materials[poly.material_index].name == 'Slum03_asphalt'
                       for v in (bridge.data.vertices[i] for i in poly.vertices))
assert all_uv0 and all_col and len(export.objects) == 12
assert result['deck_y'] == 0 and result['water_y'] == -4
assert result['minimum_visible_local_y'] == -4

# Preview-only lighting and cameras are NOT added to the saved authoring blend.
world = bpy.data.worlds.new('Preview_Overcast')
if world.node_tree:
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (.18, .24, .30, 1)
    bg.inputs['Strength'].default_value = .75
else:
    world.color = (.18, .24, .30)
scene.world = world
sun = bpy.data.lights.new('Preview_Sun', 'SUN')
sun.energy = 2.5
sun.angle = .25
lamp = bpy.data.objects.new('Preview_Sun', sun)
scene.collection.objects.link(lamp)
lamp.rotation_euler = (.4, -.4, -.4)
cam_data = bpy.data.cameras.new('Preview_Ortho')
cam = bpy.data.objects.new('Preview_Ortho', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.type = 'ORTHO'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.render.resolution_x = 1100
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
for name, eye, target, scale in (
    ('bridge', (137, 24, 82), (78, 95, 0), 105),
    ('checkpoint', (106, 29, 24), (78, 69, 1), 52),
    ('river', (170, 61, 65), (105, 95, -3), 155),
):
    cam.location = eye
    cam.rotation_euler = (Vector(target)-cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam_data.ortho_scale = scale
    scene.render.filepath = str((output/f'{name}.png').resolve())
    bpy.ops.render.render(write_still=True)
(output/'reopened.json').write_text(json.dumps(result, indent=2)+'\n')
print('TASK6_PROBE=' + json.dumps(result))
