import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

out = Path(sys.argv[sys.argv.index('--')+1])
name = out.stem
src = bpy.data.collections[f'Slum03{name}Source']
export = bpy.data.collections[f'Slum03{name}Export']
assert src.hide_render and len(src.objects) == len(export.objects)
objects = list(export.objects)
assert all(o.type == 'MESH' and len(o.data.uv_layers) > 0 and
           any(u.name == 'UV0' and u.active_render for u in o.data.uv_layers) and
           'Col' in o.data.color_attributes for o in objects)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
world = []
for o in objects:
    evaluated = o.evaluated_get(dg)
    m = evaluated.to_mesh()
    world += [evaluated.matrix_world @ v.co for v in m.vertices]
    evaluated.to_mesh_clear()
mn = Vector(tuple(min(v[i] for v in world) for i in range(3)))
mx = Vector(tuple(max(v[i] for v in world) for i in range(3)))
center = (mn + mx) / 2
extent = mx - mn
cam_data = bpy.data.cameras.new('QA-camera')
cam = bpy.data.objects.new('QA-camera', cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = center + Vector((max(extent.x, 12)*1.2, max(extent.y, 12)*1.4, max(extent.z, 10)*.72))
direction = center - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
cam_data.type = 'ORTHO'
cam_data.ortho_scale = max(extent.x*1.9, extent.y*1.7, extent.z*2, 19)
bpy.context.scene.camera = cam
for position, power in ((cam.location+Vector((0,0,12)), 2300), (center+Vector((-10,5,15)), 1900)):
    data = bpy.data.lights.new('QA-area', 'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = 25
    lamp = bpy.data.objects.new('QA-area', data)
    bpy.context.scene.collection.objects.link(lamp)
    lamp.location = position
    lamp.rotation_euler = (center - position).to_track_quat('-Z','Y').to_euler()
scene = bpy.context.scene
scene.world = bpy.data.worlds.new('QA ambience')
scene.world.color = (.35, .35, .35)
scene.render.engine = 'CYCLES'
scene.cycles.samples = 12
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(out)
bpy.ops.render.render(write_still=True)
(out.with_suffix('.json')).write_text(json.dumps({
    'source':len(src.objects), 'export':len(export.objects),
    'names':[o.name for o in objects], 'blender_min':list(mn), 'blender_max':list(mx),
    'uv0_and_color':True, 'render':str(out)
},indent=2))
