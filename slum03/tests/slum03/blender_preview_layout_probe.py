"""Verify fixed preview text follows a supplied persisted label, not a default plan."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import bpy
from mathutils import Vector
from modeling.slum03.blender_io import resonite_to_blender
from modeling.slum03.layout import read_layout

layout = read_layout(__import__('pathlib').Path(sys.argv[sys.argv.index('--') + 1]))
label = next(l for l in layout.labels if l.key == 'product-copy')
parent = bpy.data.objects[label.parent_name]
text = bpy.data.objects[label.key + '-preview']
expected = parent.matrix_world @ Vector(resonite_to_blender(label.offset))
assert (expected - text.matrix_world.translation).length < 1e-4
assert text.data.body == label.text
print('persisted label position verified')
