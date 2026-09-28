"""Build one explicitly registered sector in a fresh Blender scene only."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modeling.slum03 import blender_io, sectors
from modeling.slum03.geometry import Assembly, merge_assembly
from modeling.slum03.layout import read_layout
from modeling.slum03.materials import make_blender_materials
from modeling.slum03.types import Issue, Layout, Report
from modeling.slum03.vcolor import vertex_colors, vertex_colors_v2
from modeling.slum03.detail_evidence import detail_groups
from modeling.slum03.evaluated_detail import observe_detail
from modeling.slum03.density_metrics import layout_digest


def add_assembly(bpy, bmesh, assembly: Assembly, materials: dict, source, export,
                 sources_by_name: dict, exports_by_name: dict, seed: int):
    """Add independent editable/export meshes with identical local parent transforms."""
    name = assembly.name
    if name in sources_by_name or name in exports_by_name:
        raise ValueError(f'duplicate assembly name: {name}')
    parent_name = assembly.meta.get('parent_name')
    if parent_name and parent_name not in sources_by_name:
        raise ValueError(f'{name}: unknown or unordered parent {parent_name}')
    if assembly.meta.get('anchor'):
        if assembly.parts or parent_name:
            raise ValueError(f'{name}: placement anchor must be a root empty')
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_size = .25
        obj.location = blender_io.resonite_to_blender(assembly.origin)
        # Resonite +Y yaw becomes Blender -Z after the XZY handedness swap.
        obj.rotation_euler.z = -math.radians(assembly.meta.get('yaw_deg', 0.0))
        obj['slum03_anchor'] = True
        issues = []
    else:
        merged = merge_assembly(assembly)
        obj, issues = blender_io.create_object(bpy, bmesh, merged, assembly.origin, materials,
                                                uv_exempt=assembly.meta.get('uv_exempt', False))
        if assembly.meta.get('detail_groups'):
            groups = detail_groups(assembly)
            joints = [tuple((lo+hi)/2 + assembly.origin[i] for i, (lo, hi) in
                            enumerate(zip(g['bounds']['minimum'], g['bounds']['maximum'])))
                      for g in groups if g['category'] == 'utility']
            colors = vertex_colors_v2(merged, assembly.origin, seed,
                                       assembly.meta['placement_key'], joints,
                                       assembly.meta.get('sprays', ()))
        else:
            colors = vertex_colors(merged, assembly.origin, seed, assembly.meta.get('sprays', ()))
        blender_io.write_colors(obj, colors)
    obj['slum03_kind'] = assembly.kind
    obj['slum03_sector'] = assembly.sector
    obj.name = f'{name}_Source'
    source.objects.link(obj)
    # Never export the editable source or parent export objects under source objects.
    copy = obj.copy()
    if obj.type == 'MESH':
        copy.data = obj.data.copy()
    copy.name = name
    export.objects.link(copy)
    if parent_name:
        obj.parent = sources_by_name[parent_name]
        copy.parent = exports_by_name[parent_name]
    sources_by_name[name] = obj
    exports_by_name[name] = copy
    return copy, issues


def _issue_dict(issue: Issue | dict) -> dict:
    if isinstance(issue, Issue):
        return asdict(issue)
    if isinstance(issue, dict) and all(isinstance(issue.get(key), str)
                                       for key in ('code', 'object_key', 'message')):
        return {key: issue[key] for key in ('code', 'object_key', 'message')}
    raise ValueError(f'invalid hook issue: {issue!r}')


def write_scene(sector: str, output: Path, layout: Layout | None = None) -> Report:
    if sector not in sectors.SECTORS:
        raise KeyError(sector)
    if output.suffix != '.blend':
        raise ValueError('output must be .blend')
    layout = layout if layout is not None else read_layout(PROJECT_ROOT / 'content/slum03/layout.json')
    assemblies = sectors.sector_assemblies(layout, sector)  # fail before any scene mutation
    import bpy
    import bmesh
    if bpy.data.filepath:
        raise RuntimeError('build requires an unsaved new Blender scene')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source = bpy.data.collections.new(f'Slum03{sector}Source')
    export = bpy.data.collections.new(f'Slum03{sector}Export')
    bpy.context.scene.collection.children.link(source)
    source.hide_render = True  # never double-render source and static export copies
    bpy.context.scene.collection.children.link(export)
    materials = make_blender_materials()
    uv_issues: list[dict] = []
    errors: list[dict] = []
    objects = []
    sources_by_name = {}
    assemblies_by_name = {}
    exports_by_name = {}
    report: Report = {'sector': sector, 'export_collection': export.name, 'objects': [],
                      'evaluated_bounds': {}, 'materials': [], 'triangles': 0, 'vertices': 0,
                      'submeshes': 0, 'uv_issues': [], 'errors': []}
    if layout.density is not None:
        report['layout_sha256'] = layout_digest(layout)
    for assembly in assemblies:
        obj, issues = add_assembly(bpy, bmesh, assembly, materials, source, export,
                                   sources_by_name, exports_by_name, layout.seed)
        objects.append(obj)
        assemblies_by_name[obj.name] = assembly
        mapped = [_issue_dict(issue) for issue in issues]
        uv_issues.extend(mapped)
        errors.extend(mapped)
        entry = {'key': assembly.meta.get('placement_key', assembly.name),
                 'kind': assembly.kind, 'mesh': obj.name if obj.type == 'MESH' else None}
        if obj.type == 'EMPTY':
            entry['name'] = obj.name
        if assembly.meta.get('detail_groups'):
            entry['placement_key'] = assembly.meta.get('placement_key', assembly.name)
            entry['detail_profile'] = 'v2'
            entry['variant'] = assembly.meta.get('variant')
        report['objects'].append(entry)
    hook = sectors.BLENDER_HOOKS.get(sector)
    if hook:
        extras, extra_report = hook(bpy, layout, materials, source, export)
        objects.extend(extras)
        reported = extra_report.get('objects', [])
        report['objects'].extend(reported)
        described = {entry['mesh'] for entry in reported}
        for obj in extras:
            if obj.name not in described:
                report['objects'].append({'key': obj.name, 'kind': obj.get('slum03_kind', 'hook'),
                                          'mesh': obj.name})
        hook_uv = [_issue_dict(issue) for issue in extra_report.get('uv_issues', [])]
        uv_issues.extend(hook_uv)
        errors.extend(hook_uv)
        errors.extend(_issue_dict(issue) for issue in extra_report.get('errors', []))
        # The builder computes resource counts from actual objects, not hook estimates.
        reserved = set(report)
        report.update({key: value for key, value in extra_report.items() if key not in reserved})
    returned_names = {obj.name for obj in objects}
    for obj in export.objects:
        if obj.name not in returned_names:
            errors.append(asdict(Issue('MESH', obj.name, 'export object not returned by sector hook')))
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        if obj.type == 'EMPTY' and obj.get('slum03_anchor') and obj.name in export.objects:
            continue
        if obj.name not in export.objects or obj.type != 'MESH':
            errors.append(asdict(Issue('MESH', obj.name, 'hook export object missing or not a mesh')))
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        if mesh is None:
            errors.append(asdict(Issue('MESH', obj.name, 'evaluated mesh is missing')))
            continue
        try:
            points = [evaluated.matrix_world @ v.co for v in mesh.vertices]
            if not points or not mesh.polygons:
                errors.append(asdict(Issue('MESH', obj.name, 'empty evaluated mesh')))
                continue
            report['evaluated_bounds'][obj.name] = {
                'minimum': [min(p[i] for p in points) for i in (0, 2, 1)],
                'maximum': [max(p[i] for p in points) for i in (0, 2, 1)]}
            entry = next((e for e in report['objects'] if e.get('mesh') == obj.name), None)
            if entry is not None and layout.density is not None:
                entry['vertices'], entry['faces'] = len(mesh.vertices), len(mesh.polygons)
            if obj.name in assemblies_by_name and assemblies_by_name[obj.name].meta.get('detail_groups'):
                try:
                    geometry = {'vertices': [(p[0], p[2], p[1]) for p in points],
                                'faces': [tuple(poly.vertices) for poly in mesh.polygons]}
                    measured = observe_detail(assemblies_by_name[obj.name], geometry)
                    entry.update({'detail_groups': measured['detail_groups'],
                                  'evaluated_bounds': measured['evaluated_bounds']})
                except (ValueError, KeyError, TypeError) as exc:
                    errors.append(asdict(Issue('DETAIL_INVALID', obj.name, str(exc))))
            uv0 = next((layer for layer in mesh.uv_layers if layer.active_render), None)
            if uv0 is None:
                errors.append(asdict(Issue('UV_MISSING', obj.name, 'evaluated UV0 absent')))
            else:
                invalid_uv = False
                for poly in mesh.polygons:
                    loops = list(poly.loop_indices)
                    coords = [uv0.data[i].uv for i in loops]
                    if any(not math.isfinite(value) for uv in coords for value in uv):
                        errors.append(asdict(Issue('UV_NONFINITE', obj.name,
                                                   f'evaluated UV0 face {poly.index} has nonfinite coordinates')))
                        invalid_uv = True
                        break
                    for k in range(1, len(loops) - 1):
                        a, b, c = (mesh.vertices[mesh.loops[loops[j]].vertex_index].co
                                   for j in (0, k, k + 1))
                        xyz_area = (b - a).cross(c - a).length
                        if xyz_area <= 2e-9:
                            continue  # Geometrically collapsed triangles have no UV area to audit.
                        u, v, w = (coords[j] for j in (0, k, k + 1))
                        area = (v.x-u.x)*(w.y-u.y)-(v.y-u.y)*(w.x-u.x)
                        if not math.isfinite(area) or abs(area) <= max(1e-14, xyz_area * 1e-4):
                            errors.append(asdict(Issue('UV_DEGENERATE', obj.name,
                                                       f'evaluated UV0 face {poly.index} has zero UV area')))
                            invalid_uv = True
                            break
                    if invalid_uv:
                        break
            if not mesh.materials or any(p.material_index >= len(mesh.materials) or
                                         mesh.materials[p.material_index] is None for p in mesh.polygons):
                errors.append(asdict(Issue('MATERIAL_MISSING', obj.name, 'evaluated material missing')))
            report['triangles'] += sum(len(p.vertices) - 2 for p in mesh.polygons)
            report['vertices'] += len(mesh.vertices)
            used = {p.material_index for p in mesh.polygons}
            report['submeshes'] += len(used)
            report['materials'] = sorted(set(report['materials']) | {mesh.materials[i].name for i in used if i < len(mesh.materials) and mesh.materials[i]})
        finally:
            evaluated.to_mesh_clear()
    report['uv_issues'] = uv_issues
    report['errors'] = errors
    output.parent.mkdir(parents=True, exist_ok=True)
    (output.parent / f'{sector}-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if errors:
        raise RuntimeError(f'{sector} mesh/UV errors: {errors}')
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sector', required=True)
    parser.add_argument('--layout', type=Path, default=PROJECT_ROOT / 'content/slum03/layout.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    print(json.dumps(write_scene(args.sector, args.output, read_layout(args.layout))))


if __name__ == '__main__':
    main()
