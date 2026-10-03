"""Blender bridge; author in Resonite-local XYZ, Blender is Z-up."""
from __future__ import annotations
from typing import Any
from .geometry import MergedMesh
from .types import Issue, Vec3
from .uv import metric_face_uvs, uv_triangle_issues

UV_PER_METER = 0.5


def resonite_to_blender(p: Vec3) -> Vec3:
    return (p[0], p[2], p[1])


def create_object(bpy, bmesh, merged: MergedMesh, origin: Vec3, material_lookup: dict, *, uv_exempt: bool = False) -> tuple[Any, list[Issue]]:
    me = bpy.data.meshes.new(f'Slum03_{merged.name}_Mesh')
    # XZY is a mirror: reverse polygon winding to keep outward normal.
    me.from_pydata([resonite_to_blender(v) for v in merged.vertices], [],
                   [tuple(reversed(face)) for face in merged.faces])
    me.update()
    for name in merged.materials:
        me.materials.append(material_lookup[name])
    for poly, mat in zip(me.polygons, merged.face_materials):
        poly.material_index = mat
    # Do not replace a pre-existing render-active map or clear auxiliary UVs.
    uv0 = me.uv_layers.get('UV0') or me.uv_layers.new(name='UV0')
    uv0.active_render = True
    issues = []
    for poly in me.polygons:
        loops = list(poly.loop_indices)
        points = [me.vertices[me.loops[i].vertex_index].co for i in loops]
        try:
            coords = metric_face_uvs(points, poly.normal, UV_PER_METER)
            for i, uv in zip(loops, coords):
                uv0.data[i].uv = uv
            if not uv_exempt:
                for k in range(1, len(loops) - 1):
                    for message in uv_triangle_issues((points[0], points[k], points[k+1]),
                                                       (coords[0], coords[k], coords[k+1]),
                                                       poly.normal, UV_PER_METER):
                        issues.append(Issue('UV', merged.name, f'face {poly.index}: {message}'))
        except ValueError as exc:
            issues.append(Issue('UV', merged.name, f'face {poly.index}: {exc}'))
    obj = bpy.data.objects.new(merged.name, me)
    obj.location = resonite_to_blender(origin)
    return obj, issues


def write_colors(obj, colors, name: str = 'Col') -> None:
    me = obj.data
    if len(colors) != len(me.vertices):
        raise ValueError('vertex color count must match vertex count')
    attr = me.color_attributes.get(name) or me.color_attributes.new(name=name, type='FLOAT_COLOR', domain='POINT')
    attr.data.foreach_set('color', [channel for rgba in colors for channel in rgba])
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = [a.name for a in me.color_attributes].index(attr.name)
