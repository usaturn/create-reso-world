"""Measure every loose piece of the realized central-floor debris; called only by pytest."""
import json
import sys
from pathlib import Path
import bpy

output = Path(sys.argv[sys.argv.index('--') + 1])
source = bpy.data.collections['Slum03plazaSource']
export = bpy.data.collections['Slum03plazaExport']
PREFIX = 'plaza-rubble-floor-'


def pieces(obj):
    """Connected vertex islands of the exported static mesh, in world metres (Blender Z up)."""
    mesh = obj.data
    parent = list(range(len(mesh.vertices)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for poly in mesh.polygons:
        vs = list(poly.vertices)
        for v in vs[1:]:
            a, b = find(vs[0]), find(v)
            if a != b:
                parent[a] = b
    groups = {}
    for v in mesh.vertices:
        groups.setdefault(find(v.index), []).append(obj.matrix_world @ v.co)
    result = []
    for pts in groups.values():
        xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
        # Blender X/Y/Z = Resonite X/Z/Y.
        result.append({'object': obj.name, 'top': max(zs), 'bottom': min(zs),
                       'height': max(zs) - min(zs),
                       'x': (min(xs) + max(xs)) / 2, 'z': (min(ys) + max(ys)) / 2,
                       'long': max(max(xs) - min(xs), max(ys) - min(ys))})
    return result


floor_exports = [o for o in export.objects if o.name.startswith(PREFIX)]
floor_sources = [o for o in source.objects if o.name.startswith(PREFIX)]
result = {
    'floor_pieces': [p for o in floor_exports for p in pieces(o)],
    'floor_sources_have_nodes': bool(floor_sources) and all(
        [m.type for m in o.modifiers] == ['NODES'] for o in floor_sources),
    'floor_exports_static': bool(floor_exports) and all(not o.modifiers for o in floor_exports),
}
output.write_text(json.dumps(result), encoding='utf-8')
