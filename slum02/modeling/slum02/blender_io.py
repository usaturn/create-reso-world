"""bpy-side helpers (only imported inside Blender).

Vertex colours are written as a ``FLOAT_COLOR`` / ``POINT`` attribute named ``Col``;
``artifacts/slum02/probe-vertex-color.json`` records that the resoloop exporter copies
these values verbatim (Linear, unclamped). The AO bake uses the same domain/type.
"""
from __future__ import annotations

import time
from typing import Any

from modeling.slum02.geometry import MergedMesh, Vec3
from modeling.slum02.uv import metric_face_uvs, uv_triangle_issues

UV_PER_METER = 0.5
COLOR_TYPE = "FLOAT_COLOR"
COLOR_DOMAIN = "POINT"


def resonite_to_blender(p) -> Vec3:
    return (p[0], p[2], p[1])


def create_object(bpy, bmesh, merged: MergedMesh, origin, material_lookup, *, uv_exempt=False):
    me = bpy.data.meshes.new(f"Slum02_{merged.name}_Mesh")
    # Generators author outward/CCW winding in Resonite XYZ (R11). The XZY swap is a mirror,
    # so reversing every face restores outward normals in Blender. Normals are deliberately
    # not recalculated: Blender's heuristic cannot orient open cards or flat sheets.
    me.from_pydata([resonite_to_blender(v) for v in merged.vertices], [], [list(reversed(f)) for f in merged.faces])
    me.update()
    for name in merged.materials:
        me.materials.append(material_lookup[name])
    for poly, mat in zip(me.polygons, merged.face_materials):
        poly.material_index = mat
    uv_layer = me.uv_layers.new(name="UV0")
    issues = 0
    for poly in me.polygons:
        ids = list(poly.loop_indices)
        pts = [me.vertices[me.loops[i].vertex_index].co for i in ids]
        uvs = metric_face_uvs(pts, tuple(-c for c in poly.normal), uv_per_meter=UV_PER_METER)
        for i, uv in zip(ids, uvs):
            uv_layer.data[i].uv = uv
        if not uv_exempt:
            for k in range(1, len(ids) - 1):
                issues += len(uv_triangle_issues((pts[0], pts[k], pts[k + 1]), (uvs[0], uvs[k], uvs[k + 1]),
                                                 poly.normal, uv_per_meter=UV_PER_METER, handedness=-1))
    obj = bpy.data.objects.new(merged.name, me)
    obj.location = resonite_to_blender(origin)
    return obj, issues


def _set_render_color(me, attr) -> None:
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = [a.name for a in me.color_attributes].index(attr.name)


def write_colors(obj, colors, name: str = "Col") -> None:
    me = obj.data
    attr = me.color_attributes.get(name) or me.color_attributes.new(name=name, type=COLOR_TYPE, domain=COLOR_DOMAIN)
    flat = [c for rgba in colors for c in rgba]
    attr.data.foreach_set("color", flat)
    _set_render_color(me, attr)


def bake_ao(bpy, objects, samples: int = 16) -> dict[str, Any]:
    scene = bpy.context.scene
    start = time.time()
    try:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = samples
        scene.render.bake.target = "VERTEX_COLORS"
        baked = 0
        # Objects removed/linked during the build leave the view layer's object base
        # cache stale in background mode (None entries); resync before selecting.
        view_layer = bpy.context.view_layer
        view_layer.update()
        for obj in objects:
            me = obj.data
            ao = me.color_attributes.get("AO") or me.color_attributes.new(name="AO", type=COLOR_TYPE, domain=COLOR_DOMAIN)
            me.color_attributes.active_color = ao
            for o in view_layer.objects:
                if o is not None:
                    o.select_set(False)
            obj.select_set(True)
            view_layer.objects.active = obj
            bpy.ops.object.bake(type="AO")
            baked += 1
        return {"baked": baked, "seconds": round(time.time() - start, 1), "samples": samples}
    except Exception as exc:  # AO is an enhancement: keep wear colours, record the failure
        return {"baked": 0, "error": f"{type(exc).__name__}: {exc}", "seconds": round(time.time() - start, 1)}


def combine_ao(obj, strength: float = 0.85) -> None:
    me = obj.data
    col, ao = me.color_attributes.get("Col"), me.color_attributes.get("AO")
    if ao is None:
        return
    n = len(col.data)
    cv, av = [0.0] * (4 * n), [0.0] * (4 * n)
    col.data.foreach_get("color", cv)
    ao.data.foreach_get("color", av)
    for i in range(n):
        f = 1 - strength + strength * av[4 * i]
        for k in range(3):
            cv[4 * i + k] *= f
    col.data.foreach_set("color", cv)
    me.color_attributes.remove(ao)
    col = me.color_attributes.get("Col")
    _set_render_color(me, col)
