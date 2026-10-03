"""Run against a freshly reopened ads.blend with resoloop blender run --blend."""
import math
from pathlib import Path
import bpy
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mathutils import Vector
from modeling.slum03.build import add_assembly
from modeling.slum03.geometry import Assembly, box
from modeling.slum03.layout import build_layout
from modeling.slum03.materials import make_blender_materials
from modeling.slum03.sectors import sector_assemblies
import bmesh

assert Path(bpy.data.filepath).name == 'ads.blend'
source = bpy.data.collections['Slum03adsSource']
export = bpy.data.collections['Slum03adsExport']
layout = build_layout()
for p in (p for p in layout.placements if p.sector == 'ads'):
    anchor = export.objects[p.key]
    assert anchor.type == 'EMPTY' and anchor.parent is None
    assert (anchor.location - Vector((p.origin[0], p.origin[2], p.origin[1]))).length < 1e-5
    assert math.isclose(anchor.rotation_euler.z, -math.radians(p.yaw_deg), abs_tol=1e-6)
    assert source.objects[f'{p.key}_Source'].type == 'EMPTY'
    assert any(label.parent_name == anchor.name for label in layout.labels)
for a in sector_assemblies(layout, 'ads'):
    if a.parts:
        obj = export.objects[a.name]
        assert obj.parent == export.objects[a.meta['parent_name']]
        assert obj.data is not source.objects[a.name+'_Source'].data
        assert obj.data.uv_layers.get('UV0').active_render
        assert obj.data.color_attributes.get('Col')
        assert not obj.get('slum03_anchor', False)
# An asymmetric local child pose under a yawed Empty: compare real evaluated world vertex
# to independent hand-computed Blender XZY reflection; no copied placement translation.
custom_source = bpy.data.collections.new('ProbeSource')
custom_export = bpy.data.collections.new('ProbeExport')
bpy.context.scene.collection.children.link(custom_source)
bpy.context.scene.collection.children.link(custom_export)
src, dst = {}, {}
anchor = Assembly('probe', 'probe-anchor', 'ads', (2,3,4), [], {'anchor':True, 'yaw_deg':30})
child = Assembly('probe', 'probe-child', 'ads', (.5, .2, .3),
                 [box('offset', (.17,.12,.27), (.1,.1,.1), 'steel_dark')],
                 {'parent_name':'probe-anchor'})
for a in (anchor, child):
    obj, issues = add_assembly(bpy,bmesh,a,make_blender_materials(),custom_source,custom_export,src,dst,260927)
    assert not issues
bpy.context.view_layer.update()
obj = dst['probe-child']
actual = obj.matrix_world @ obj.data.vertices[0].co
local = obj.data.vertices[0].co
x, z, y = local.x+.5, local.y+.3, local.z+.2
angle = math.radians(30)
expected = Vector((2+x*math.cos(angle)+z*math.sin(angle),
                   4-x*math.sin(angle)+z*math.cos(angle), 3+y))
assert (actual-expected).length < 1e-5, (actual[:], expected[:])
assert obj.parent == dst['probe-anchor'] and src['probe-child'].parent == src['probe-anchor']
assert obj.data is not src['probe-child'].data
# Independently editable source must never mutate export-copy geometry.
original = obj.data.vertices[0].co.copy()
src['probe-child'].data.vertices[0].co.x += .4
assert (obj.data.vertices[0].co-original).length < 1e-7
print('ADS_REOPEN_AND_PARENT_TRANSFORM_PASS')
