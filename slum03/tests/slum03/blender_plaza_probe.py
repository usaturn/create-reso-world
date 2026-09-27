"""Reopen a generated scene with real Blender; called only by offline pytest."""
import json
import sys
from pathlib import Path
import bpy

output = Path(sys.argv[sys.argv.index('--') + 1])
source = bpy.data.collections['Slum03plazaSource']
export = bpy.data.collections['Slum03plazaExport']
wall = export.objects['north-wall']
letters = export.objects['north-wall-graffiti-red']
front_normals = [tuple(p.normal) for p in wall.data.polygons
                 if p.center.y < -0.39 and p.normal.y < -.99]
source_rubble = [o for o in source.objects if o.name.startswith('plaza-rubble-')]
export_rubble = [o for o in export.objects if o.name.startswith('plaza-rubble-')]
# Separate physically disconnected paint islands in the actual realized mesh.
def islands(obj, material_name):
    mesh = obj.data
    face_vertices = [tuple(p.vertices) for p in mesh.polygons
                     if mesh.materials[p.material_index].name == material_name]
    neighbours = {}
    for vertices in face_vertices:
        for v in vertices:
            neighbours.setdefault(v, set()).update(vertices)
    result = []
    while neighbours:
        seed = next(iter(neighbours))
        component, pending = set(), [seed]
        while pending:
            v = pending.pop()
            if v not in component:
                component.add(v)
                pending.extend(neighbours[v] - component)
        for v in component:
            neighbours.pop(v)
        pts = [obj.matrix_world @ mesh.vertices[v].co for v in component]
        result.append({'x': (min(p.x for p in pts)+max(p.x for p in pts))/2,
                       'top_y': max(p.z for p in pts), 'min_y': min(p.z for p in pts)})
    return result

red_vertices = [letters.matrix_world @ v.co for v in letters.data.vertices]
red_min_x = min(v.x for v in red_vertices)
red_max_x = max(v.x for v in red_vertices)
red_min_y = min(v.z for v in red_vertices)
red_max_y = max(v.z for v in red_vertices)
drips_obj = export.objects['north-wall-graffiti-drips']
red_streaks = islands(drips_obj, 'Slum03_spray_red')
black_marks = islands(drips_obj, 'Slum03_spray_black')
result = {
    'source_hidden_in_render': source.hide_render,
    'source_names': sorted(o.name for o in source.objects),
    'export_names': sorted(o.name for o in export.objects),
    'wall_south_normals': front_normals,
    'graffiti_text': letters['graffiti_text'],
    'drip_offsets_from_glyph_base': [stroke['top_y'] -
                                    min(v.z for v in red_vertices if abs(v.x-stroke['x']) <= .08)
                                    if any(abs(v.x-stroke['x']) <= .08 for v in red_vertices)
                                    else None for stroke in red_streaks],
    'red_streaks': red_streaks,
    'overspray_x_gap': [min(abs(mark['x']-red_min_x), abs(mark['x']-red_max_x))
                        for mark in black_marks],
    'overspray_y': [mark['top_y'] for mark in black_marks],
    'red_y_span': [red_min_y, red_max_y],
    'graffiti_facing_blender': list(letters['face_normal_blender']),
    'graffiti_uv': [l.name for l in letters.data.uv_layers if l.active_render],
    'graffiti_materials': sorted({m.name for o in export.objects if 'graffiti' in o.name for m in o.data.materials}),
    'rubble_source_count': len(source_rubble), 'rubble_export_count': len(export_rubble),
    'rubble_scales': [float(item.vector[0]) for obj in source_rubble
                      if (attr := obj.data.attributes.get('rubble_scale'))
                      for item in attr.data],
    'rubble_variants': [int(item.value) for obj in source_rubble
                        if (attr := obj.data.attributes.get('rubble_variant'))
                        for item in attr.data],
    'scale_linked': all(next(n for n in o.modifiers[0].node_group.nodes
                             if n.bl_idname == 'GeometryNodeInstanceOnPoints').inputs['Scale'].is_linked
                        for o in source_rubble),
    'realized_rubble_materials': sorted({m.name for o in export_rubble for m in o.data.materials}),
    'truss_variant_span': [max(v.co.x for v in source.objects['rubble-variant-1'].data.vertices) -
                          min(v.co.x for v in source.objects['rubble-variant-1'].data.vertices),
                          max(v.co.z for v in source.objects['rubble-variant-1'].data.vertices) -
                          min(v.co.z for v in source.objects['rubble-variant-1'].data.vertices)],
    'variant_materials': {o.name: [m.name for m in o.data.materials] for o in source.objects if o.name.startswith('rubble-variant-')},
    'floor_materials': sorted({m.name for m in export.objects['factory-floor'].data.materials}),
    'source_modifiers': [[m.type for m in o.modifiers] for o in source_rubble],
    'source_node_types': sorted({n.bl_idname for o in source_rubble
                                  for m in o.modifiers for n in m.node_group.nodes}),
    'export_modifiers': [[m.type for m in o.modifiers] for o in export_rubble],
    'export_faces': [len(o.data.polygons) for o in export_rubble],
    'export_uvs': [[u.name for u in o.data.uv_layers] for o in export_rubble],
    'export_colors': [[c.name for c in o.data.color_attributes] for o in export_rubble],
    'font_packed': any(f.packed_file for f in bpy.data.fonts if f.name != 'Bfont Regular'),
    'red_mesh_south_normals': sum(1 for p in letters.data.polygons if (letters.matrix_world.to_3x3() @ p.normal).y < -.9),
    'red_mesh_polygons': len(letters.data.polygons),
    'letter_x_span': [min((letters.matrix_world @ v.co).x for v in letters.data.vertices), max((letters.matrix_world @ v.co).x for v in letters.data.vertices)],
}
output.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
