"""Invoked inside Blender after saved scene reopens, never a synthetic scene."""
import bpy
import json
import sys

sector = sys.argv[sys.argv.index('--')+1]
source = bpy.data.collections[f'Slum03{sector}Source']
export = bpy.data.collections[f'Slum03{sector}Export']
assert source.objects and export.objects
assert all(not o.name.endswith('_Source') for o in export.objects)
assert not any(o.name in source.objects for o in export.objects)
assert len([o for o in export.objects if o.type == 'MESH']) > 0
for obj in export.objects:
    if obj.type != 'MESH':
        assert obj.get('slum03_anchor')
        continue
    assert obj.data.uv_layers and any(layer.active_render for layer in obj.data.uv_layers)
    assert obj.data.color_attributes or obj.get('slum03_kind') == 'graffiti', obj.name
    assert all(slot.material for slot in obj.material_slots)
    assert not obj.modifiers
    assert obj.data.vertices and obj.data.polygons
if sector in ('plaza', 'forest'):
    nodes = [m.node_group for obj in source.objects for m in obj.modifiers if m.type == 'NODES']
    assert nodes and all(g and g.nodes and g.links for g in nodes)
    assert all(not m.type == 'NODES' for obj in export.objects for m in obj.modifiers)
print(json.dumps({'source': len(source.objects), 'export': len(export.objects), 'graphs': len(nodes) if sector in ('plaza', 'forest') else 0}))
