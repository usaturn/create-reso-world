"""Reopen real sector blends and render directional offline evidence; never save preview cameras.

Run with resoloop blender run --blend forest.blend --arg=OUTPUT_DIR.
"""
from pathlib import Path
import json
import sys
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--')+1:]
out = Path(args[0]).resolve()
assets = Path(args[1]).resolve() if len(args) > 1 else out
assert bpy.data.filepath.endswith('forest.blend')
scene = bpy.context.scene
forest_source = bpy.data.collections['Slum03forestSource']
forest_export = bpy.data.collections['Slum03forestExport']
for sector in ('backdrop-north', 'backdrop-west-south', 'ground', 'plaza', 'road-river', 'ruins-east'):
    path = (out if sector == 'backdrop-west-south' and (out/f'{sector}.blend').exists() else assets)/f'{sector}.blend'
    with bpy.data.libraries.load(str(path), link=False) as (src, dest):
        name = f'Slum03{sector}Export'
        assert name in src.collections, name
        dest.collections = [name]
    scene.collection.children.link(dest.collections[0])

bpy.context.view_layer.update()
checks = {}
for sector in ('forest', 'backdrop-north', 'backdrop-west-south'):
    col = bpy.data.collections[f'Slum03{sector}Export']
    checks[sector] = {'objects': len(col.objects),
                      'uv0': all(any(u.name == 'UV0' and u.active_render for u in o.data.uv_layers)
                                 for o in col.objects),
                      'colors': all('Col' in o.data.color_attributes for o in col.objects)}
    assert checks[sector]['objects'] and checks[sector]['uv0'] and checks[sector]['colors']
assert forest_source.hide_render
assert len([o for o in forest_source.objects if o.modifiers and o.modifiers[0].type == 'NODES']) == 12
assert all(not o.modifiers for o in forest_export.objects)
gate = bpy.data.collections['Slum03backdrop-northExport'].objects['arcology-gate']
gate_heights = [(gate.matrix_world @ v.co).z for v in gate.data.vertices]
checks['gate_actual_height'] = max(gate_heights)
checks['gate_joint_vertices'] = sum(abs(y-796) < 1e-4 for y in gate_heights)
assert abs(checks['gate_actual_height'] - 820) < 1e-4
assert checks['gate_joint_vertices'] >= 12  # welded vertices where dwellings meet the crown
checks['editable_patches'] = 12
checks['realized_patches'] = len([o for o in forest_export.objects if o.name.startswith('forest-patch-')])
assert checks['realized_patches'] == 12

world = bpy.data.worlds.new('Task7_Overcast')
if world.node_tree:
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (.23, .25, .28, 1)
    bg.inputs['Strength'].default_value = .8
else:
    world.color = (.23, .25, .28)
scene.world = world
lamp = bpy.data.objects.new('Task7_PreviewSun', bpy.data.lights.new('Task7_PreviewSun', 'SUN'))
scene.collection.objects.link(lamp)
lamp.data.energy = 2.4
lamp.rotation_euler = (.35, -.4, -.35)
cam = bpy.data.objects.new('Task7_PreviewCamera', bpy.data.cameras.new('Task7_PreviewCamera'))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = 'PERSP'
cam.data.lens = 17
cam.data.clip_end = 2500
scene.render.engine = 'CYCLES'
scene.cycles.samples = 12
scene.render.resolution_x = 1152
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
for name, eye, target, lens in (
    ('north', (0, -6, 1.6), (28, 440, 220), 11),
    ('east', (63, 0, 1.6), (143, 0, 15), 24),
    ('east-lane', (54, 0, 1.6), (143, 0, 15), 24),
    ('west', (-54, 0, 1.6), (-118, 0, 17), 14),
    ('south', (0, -52, 1.6), (0, -126, 17), 14),
):
    cam.location = eye
    cam.rotation_euler = (Vector(target)-cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    scene.render.filepath = str(out/f'{name}.png')
    bpy.ops.render.render(write_still=True)
(out/'reopened.json').write_text(json.dumps(checks, indent=2)+'\n')
print('TASK7_REOPEN=' + json.dumps(checks))
