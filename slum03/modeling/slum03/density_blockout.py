"""Offline Blender box blockout, identical-camera baseline comparison; no export/live mutation.

Run with resoloop blender run modeling/slum03/density_blockout.py
--arg=--layout --arg=... --arg=--output --arg=... --json.
All boxes are intentional placeholders, NOT v2 final geometry or a collision proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modeling.slum03.density_metrics import density_report
from modeling.slum03.layout import read_layout
from modeling.slum03.spatial import placement_bounds
from modeling.slum03.blender_io import resonite_to_blender

# Root-local coordinates, eye at 1.6 m; identical settings for both layouts.
CAMERAS = {
    'top': ((0, 165, 0), (0, 0, 0)),
    'northwest': ((-55.5, 1.6, 4), (-55.5, 2.7, 39)),
    'southwest': ((-55.5, 1.6, -55), (-55.5, 2.7, -22)),
    'market': ((0, 1.6, -59), (-5, 2.7, -34)),
    'east': ((45.5, 1.6, -55), (45.5, 2.7, -20)),
}
COLORS = {'ground': (.16, .18, .22, 1), 'floor': (.31, .37, .42, 1),
          'north-wall': (.50, .47, .42, 1), 'ruin': (.55, .59, .67, 1),
          'shack': (.68, .44, .32, 1), 'stall': (.98, .71, .30, 1),
          'nightlife': (.86, .28, .60, 1), 'yarol': (.95, .89, .51, 1),
          'roadway': (.19, .22, .28, 1)}
VISIBLE = frozenset((*COLORS, 'rubble'))


def _make_scene(bpy, layout):
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.camera = None
    materials = {}
    for kind, color in COLORS.items():
        mat = bpy.data.materials.new(f'GateA_{kind}')
        mat.diffuse_color = color
        mat.use_nodes = True
        mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = color
        materials[kind] = mat
    path_material = bpy.data.materials.new('GateA_protected_walkway')
    path_material.diffuse_color = (.25, .63, .83, 1)
    path_material.use_nodes = True
    path_material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (.25, .63, .83, 1)
    for p in layout.placements:
        if p.domain == 'background' or p.kind not in VISIBLE:
            continue
        b = placement_bounds(p)
        if p.kind in ('ground', 'floor'):
            # Planes remain below walking air, not giant vertical obstructions.
            pass
        bpy.ops.mesh.primitive_cube_add(size=1, location=resonite_to_blender(tuple(
            (a+c)/2 for a, c in zip(b.minimum, b.maximum))))
        obj = bpy.context.object
        obj.name = f'BLOCKOUT_ONLY__{p.key}'
        obj.dimensions = (b.maximum[0]-b.minimum[0], b.maximum[2]-b.minimum[2],
                          max(b.maximum[1]-b.minimum[1], .01))
        obj.data.materials.append(materials.get(p.kind, materials['ruin']))
    # Protected walkways in diagnostic blue, just above the flat ground.
    protected = list(layout.routes[:3])
    if layout.density:
        protected += list(layout.density.branch_clearances)
    for n, r in enumerate(protected):
        bpy.ops.mesh.primitive_cube_add(size=1,
            location=resonite_to_blender(((r.x_min+r.x_max)/2, .012, (r.z_min+r.z_max)/2)))
        obj = bpy.context.object
        obj.name = f'WALKWAY_ONLY__{n}'
        obj.dimensions = (r.x_max-r.x_min, r.z_max-r.z_min, .012)
        obj.data.materials.append(path_material)
    cam = bpy.data.cameras.new('GateA_Diagnostic_Camera')
    obj = bpy.data.objects.new('GateA_Diagnostic_Camera', cam)
    scene.collection.objects.link(obj)
    scene.camera = obj
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new('GateA_Studio_Background')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.52, .62, .77, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .85
    return obj


def _render(bpy, layout, output, prefix):
    from mathutils import Vector
    camera = _make_scene(bpy, layout)
    result = {}
    for name, (eye, target) in CAMERAS.items():
        camera.location = resonite_to_blender(eye)
        direction = Vector(resonite_to_blender(target)) - camera.location
        camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        camera.data.type = 'ORTHO' if name == 'top' else 'PERSP'
        camera.data.ortho_scale = 200 if name == 'top' else 0
        camera.data.lens = 24 if name != 'top' else 40
        path = (output / f'{prefix}-{name}.png').resolve()
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        if not path.is_file() or path.stat().st_size < 1000:
            raise RuntimeError(f'missing rendered image: {path}')
        result[name] = {'image': str(path), 'eye': eye, 'target': target,
                        'height_m': eye[1], 'projection': camera.data.type,
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return result


def run(layout_path: Path, output: Path):
    import bpy
    if bpy.data.filepath or output.exists():
        raise RuntimeError('fresh Blender scene and unused output directory required')
    layout_path = layout_path.resolve()
    layout = read_layout(layout_path)
    if not layout.density or layout.density.stage != 'blockout':
        raise ValueError('only offline blockout layout accepted')
    report = density_report(layout, {}, 'blockout')
    if report['issues']:
        raise ValueError(f'blockout fails Gate A spatial audit: {report["issues"][:10]}')
    output.mkdir(parents=True, exist_ok=False)
    report['references']['layout'] = {'path': str(layout_path),
        'sha256': hashlib.sha256(layout_path.read_bytes()).hexdigest()}
    report['references']['build'] = None
    report['references']['export'] = None
    report['evidence_scope'] = ('Diagnostic axis-aligned Blender box blockout; not detailed meshes, '
                                'not evaluated geometry, not live walk/visual acceptance.')
    baseline_path = PROJECT_ROOT / 'artifacts/slum03/finalfix-m-20260928T0511/layout.json'
    baseline = read_layout(baseline_path)
    report['baseline_comparison'] = {'layout': str(baseline_path.resolve()),
        'sha256': hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        'cameras': _render(bpy, baseline, output, 'baseline')}
    report['cameras'] = _render(bpy, layout, output, 'blockout')
    report['gate_a'] = {'spatial_issues': 0, 'image_review': 'pending controller inspection',
                        'live_acceptance': 'not tested'}
    # Save only the dedicated diagnostic scene; no sector export collections.
    bpy.ops.wm.save_as_mainfile(filepath=str((output / 'diagnostic-blockout.blend').resolve()))
    path = output / 'density-report.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('SLUM03_GATE_A=' + json.dumps({'report': str(path.resolve()),
          'issues': len(report['issues']), 'images': [v['image'] for v in report['cameras'].values()]}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--layout', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    run(args.layout, args.output)
