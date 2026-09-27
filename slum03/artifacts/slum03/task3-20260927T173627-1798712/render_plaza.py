import bpy, math, sys
from mathutils import Vector
from pathlib import Path
out = Path(sys.argv[sys.argv.index('--')+1])
scene=bpy.context.scene
cam_data=bpy.data.cameras.new('Task3 plaza camera')
cam=bpy.data.objects.new('Task3 plaza camera',cam_data)
scene.collection.objects.link(cam);scene.camera=cam
cam.location=(0,-29,11)
target=Vector((0,12,3.8))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
cam_data.lens=35
world=bpy.data.worlds.new('Task3 ambient')
scene.world=world  # Blender 5 worlds create a node tree by default
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.25,.30,.38,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.9
for loc,power,color,size in [((-12,-8,20),2300,(1,.82,.68),12),((11,9,17),1600,(.56,.75,1),14)]:
 light=bpy.data.lights.new('Task3 local preview light','AREA');light.energy=power;light.shape='DISK';light.size=size;light.color=color
 obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=loc
 obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=12
scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
print('preview:',out)
