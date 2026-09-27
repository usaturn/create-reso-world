"""Blender coordinate test: label yaw=0 must face Resonite +Z (Blender +Y)."""
import bpy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mathutils import Vector
from modeling.slum03.preview import _labels
from modeling.slum03.types import LabelSpec
from types import SimpleNamespace

parent = bpy.data.objects.new('market-product-holo', None)
collection = bpy.data.collections.new('Slum03adsExport')
bpy.context.scene.collection.children.link(collection)
collection.objects.link(parent)
parent.location = (-9, -46, 4)
bpy.context.view_layer.update()
label = LabelSpec('product-copy', 'AUGMENT', 'market-product-holo', (0, -1, 1.35), 0, .9, (1,1,1,1))
_labels(bpy, SimpleNamespace(labels=(label,)))
bpy.context.view_layer.update()
text = bpy.data.objects['product-copy-preview']
front = text.matrix_world.to_3x3() @ Vector((0,0,1))
assert front.y > .999, tuple(front)
assert (text.matrix_world.to_3x3() @ Vector((1,0,0))).x < -.999, 'text must read left-to-right from +Z'
assert tuple(round(x, 3) for x in text.matrix_world.translation) == (-9, -44.65, 3)
