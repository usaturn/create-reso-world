"""Reopen ads.blend, render temporary proof cameras and text, do not save scene."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from modeling.slum03.layout import build_layout
from modeling.slum03.materials import make_blender_materials

out = Path(sys.argv[sys.argv.index('--')+1])
assert Path(bpy.data.filepath).name == 'ads.blend'
scene = bpy.context.scene
assert bpy.data.collections['Slum03adsSource'].hide_render
materials = make_blender_materials()
# Visual contact check for the information projector on the existing storefront roof.
nightlife = Path.cwd()/'artifacts/slum03/task5-fix1-20260927T185918-2319309/nightlife.blend'
with bpy.data.libraries.load(str(nightlife), link=False) as (source, target):
    target.collections = ['Slum03nightlifeExport']
scene.collection.children.link(target.collections[0])
context_roof = target.collections[0]
context_roof.hide_render = True
font = bpy.data.fonts.load(str(Path.cwd()/'assets/fonts/DelaGothicOne-Regular.ttf'))
for label in build_layout().labels:
    if label.parent_name not in bpy.data.collections['Slum03adsExport'].objects:
        continue
    curve = bpy.data.curves.new('TemporaryPreview_'+label.key, type='FONT')
    curve.body = label.text
    curve.font = font
    curve.size = label.height
    curve.align_x = 'CENTER'
    curve.extrude = .003
    obj = bpy.data.objects.new('TemporaryPreview_'+label.key, curve)
    scene.collection.objects.link(obj)
    obj.parent = bpy.data.objects[label.parent_name]
    obj.location = (label.offset[0], label.offset[2], label.offset[1])
    obj.rotation_euler = (1.5707963268, 0, 3.1415926536 if label.key != 'info-copy' else 0)
    curve.materials.append(materials['holo_cyan' if label.key == 'product-copy' else 'holo_magenta' if label.key == 'info-copy' else 'holo_lime'])
world = bpy.data.worlds.new('Task8_preview_world')
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.025,.035,.07,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
scene.world = world
lamp = bpy.data.objects.new('Task8_preview_area', bpy.data.lights.new('Task8_preview_area', 'AREA'))
scene.collection.objects.link(lamp)
lamp.location=(10,-15,18); lamp.data.energy=1200; lamp.data.shape='DISK';lamp.data.size=18
lamp.rotation_euler=(Vector((0,0,2))-lamp.location).to_track_quat('-Z','Y').to_euler()
cam = bpy.data.objects.new('Task8_preview_camera',bpy.data.cameras.new('Task8_preview_camera'))
scene.collection.objects.link(cam); scene.camera=cam
cam.data.type='PERSP'; cam.data.lens=43; cam.data.clip_end=150
scene.render.engine='CYCLES'; scene.cycles.samples=20
scene.render.resolution_x=800; scene.render.resolution_y=640
scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'
views = [('product',(-5,-40,5.2),(-9,-46,3.4),38),
         ('information',(37,-25,15.4),(37,-16.55,13.0),34),
         ('ribbon',(26,19,9.0),(26,10,6.6),35)]
for key,eye,target,lens in views:
    context_roof.hide_render = key != 'information'
    cam.location=eye
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=lens
    scene.render.filepath=str(out/(key+'.png'))
    bpy.ops.render.render(write_still=True)
(out/'views.json').write_text(json.dumps({'views':views, 'preview_only': True, 'blend':bpy.data.filepath}, indent=2)+'\n')
print('TASK8_PREVIEW_VIEWS_PASS')
