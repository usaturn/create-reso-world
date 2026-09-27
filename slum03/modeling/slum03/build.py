"""Build one explicitly registered sector in a fresh Blender scene only."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modeling.slum03 import blender_io, sectors
from modeling.slum03.geometry import merge_assembly
from modeling.slum03.layout import build_layout
from modeling.slum03.materials import make_blender_materials
from modeling.slum03.types import Issue, Report
from modeling.slum03.vcolor import vertex_colors


def write_scene(sector: str, output: Path) -> Report:
    if sector not in sectors.SECTORS:
        raise KeyError(sector)
    if output.suffix != '.blend':
        raise ValueError('output must be .blend')
    layout = build_layout()
    assemblies = sectors.sector_assemblies(layout, sector)  # fail before any scene mutation
    import bpy
    import bmesh
    if bpy.data.filepath:
        raise RuntimeError('build requires an unsaved new Blender scene')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source = bpy.data.collections.new(f'Slum03{sector}Source')
    export = bpy.data.collections.new(f'Slum03{sector}Export')
    bpy.context.scene.collection.children.link(source)
    bpy.context.scene.collection.children.link(export)
    materials = make_blender_materials()
    issues: list[Issue] = []
    objects = []
    sources_by_name = {}
    exports_by_name = {}
    report: Report = {'sector': sector, 'export_collection': export.name, 'objects': [],
                      'evaluated_bounds': {}, 'materials': [], 'triangles': 0, 'vertices': 0,
                      'submeshes': 0, 'uv_issues': [], 'errors': []}
    for a in assemblies:
        merged = merge_assembly(a)
        obj, uv_issues = blender_io.create_object(bpy, bmesh, merged, a.origin, materials,
                                                   uv_exempt=a.meta.get('uv_exempt', False))
        blender_io.write_colors(obj, vertex_colors(merged, a.origin, layout.seed,
                                                   a.meta.get('sprays', ())))
        obj['slum03_kind'] = a.kind
        obj['slum03_sector'] = sector
        obj.name = f"{a.name}_Source"
        source.objects.link(obj)
        # Never export the editable source, only a distinct mesh/object copy.
        copy = obj.copy()
        copy.data = obj.data.copy()
        copy.name = a.name
        export.objects.link(copy)
        parent_name = a.meta.get('parent_name')
        if parent_name:
            if parent_name not in sources_by_name:
                raise ValueError(f'{a.name}: unknown or unordered parent {parent_name}')
            obj.parent = sources_by_name[parent_name]
            copy.parent = exports_by_name[parent_name]
        sources_by_name[a.name] = obj
        exports_by_name[a.name] = copy
        objects.append(copy)
        issues.extend(uv_issues)
        report['objects'].append({'key': a.meta.get('placement_key', a.name), 'kind': a.kind, 'mesh': copy.name})
    hook = sectors.BLENDER_HOOKS.get(sector)
    if hook:
        extras, extra_report = hook(bpy, layout, materials, source, export)
        objects.extend(extras)
        report.update(extra_report)
    bpy.context.view_layer.update()
    for obj in objects:
        if obj.type != 'MESH':
            issues.append(Issue('MESH', obj.name, 'export object is not a mesh'))
            continue
        points = [obj.matrix_world @ v.co for v in obj.data.vertices]
        if not points:
            issues.append(Issue('MESH', obj.name, 'empty mesh'))
            continue
        report['evaluated_bounds'][obj.name] = {
            'minimum': [min(p[i] for p in points) for i in (0, 2, 1)],
            'maximum': [max(p[i] for p in points) for i in (0, 2, 1)]}
        report['triangles'] += sum(len(p.vertices) - 2 for p in obj.data.polygons)
        report['vertices'] += len(obj.data.vertices)
        used = {p.material_index for p in obj.data.polygons}
        report['submeshes'] += len(used)
        report['materials'] = sorted(set(report['materials']) | {obj.data.materials[i].name for i in used})
    report['uv_issues'] = [asdict(i) for i in issues]
    report['errors'] = [asdict(i) for i in issues]
    output.parent.mkdir(parents=True, exist_ok=True)
    (output.parent / f'{sector}-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if issues:
        raise RuntimeError(f'{sector} mesh/UV errors: {report["errors"]}')
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sector', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    print(json.dumps(write_scene(args.sector, args.output)))


if __name__ == '__main__':
    main()
