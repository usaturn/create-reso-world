"""Probe each span of the real fixed AUGMENT text against the combined exported scene."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from modeling.slum03.blender_io import resonite_to_blender
from modeling.slum03.layout import build_layout
from modeling.slum03.preview import _labels

layout = build_layout()
eye = next(v.eye for v in layout.viewpoints if v.key == 'ar-hero')
# Use the saved C export meshes as unchanged blockers, but recreate text from the
# current canonical layout. Never mutate the archived preview on disk.
for old in tuple(o for o in bpy.data.objects if o.type == 'FONT' and o.name.endswith('-preview')):
    bpy.data.objects.remove(old, do_unlink=True)
_labels(bpy, layout)
bpy.context.view_layer.update()
text = bpy.data.objects['product-copy-preview']
assert text.data.body == 'AUGMENT'
assert text.type == 'FONT'
graph = bpy.context.evaluated_depsgraph_get()
evaluated = text.evaluated_get(graph)
mesh = evaluated.to_mesh()
try:
    # Equal-width spans across the actual glyph geometry; every span must have
    # visible face centers from the unchanged, specified viewpoint.
    xs = [v.co.x for v in mesh.vertices]
    lower, upper = min(xs), max(xs)
    hits = [0] * 7
    samples = [0] * 7
    origin = Vector(resonite_to_blender(eye))
    for poly in mesh.polygons:
        center = poly.center
        bin_index = min(6, int((center.x - lower) / (upper - lower) * 7))
        samples[bin_index] += 1
        target = text.matrix_world @ center
        direction = target - origin
        hit, _, _, _, obj, _ = bpy.context.scene.ray_cast(
            graph, origin, direction.normalized(), distance=direction.length + .002)
        if hit and obj.original == text:
            hits[bin_index] += 1
    print(json.dumps({'eye': eye, 'samples': samples, 'visible': hits}))
    assert all(visible / total >= .9 for visible, total in zip(hits, samples)), (
        f'AUGMENT occluded: visible per span={hits}, samples={samples}')
finally:
    evaluated.to_mesh_clear()
