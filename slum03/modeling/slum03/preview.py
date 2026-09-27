"""Render small offline combined-scene previews and raycast the actual exported meshes.

Use `resoloop blender run modeling/slum03/preview.py --arg=--output
--arg=artifacts/slum03/previews --json` from the project root. Not runtime QA.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import SECTORS
from modeling.slum03.blender_io import resonite_to_blender

VIEWS = {
    'plaza-north': (0, 360, 330), 'east-forest': (155, 15, 0),
    'east-lane': (155, 12, 0), 'bridge-checkpoint': (78, 7, 90),
    'west-city': (-135, 20, 0), 'south-market': (0, 18, -140),
    'ar-hero': (-9, 4, -46),
}


def _load_scene(bpy, base: Path):
    for sector in SECTORS:
        path = base / f'{sector}.blend'
        if not path.is_file():
            raise FileNotFoundError(f'missing sector blend: {path}')
    for sector in SECTORS:
        path = base / f'{sector}.blend'
        collection_name = f'Slum03{sector}Export'
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            if collection_name not in src.collections:
                raise ValueError(f'missing sector export collection: {collection_name} in {path}')
            dst.collections = [collection_name]
        bpy.context.scene.collection.children.link(dst.collections[0])
    bpy.context.view_layer.update()


def _labels(bpy, layout):
    from mathutils import Matrix, Euler
    for label in layout.labels:
        parent = bpy.data.objects.get(label.parent_name)
        if parent is None or parent.name not in {o.name for c in bpy.context.scene.collection.children for o in c.objects}:
            raise ValueError(f'fixed label parent missing: {label.parent_name}')
        data = bpy.data.curves.new(f'{label.key}-preview', 'FONT')
        data.body = label.text
        data.size = label.height
        data.align_x = 'CENTER'
        obj = bpy.data.objects.new(f'{label.key}-preview', data)
        bpy.context.scene.collection.objects.link(obj)
        obj.matrix_world = (parent.matrix_world @ Matrix.Translation(resonite_to_blender(label.offset)) @
                            Euler((math.pi/2, 0, math.pi-math.radians(label.yaw_deg)), 'XYZ').to_matrix().to_4x4())
        mat = bpy.data.materials.new(f'{label.key}-preview-color')
        mat.diffuse_color = label.color
        node = mat.node_tree.nodes.get('Principled BSDF')
        node.inputs['Base Color'].default_value = label.color
        node.inputs['Emission Color'].default_value = label.color
        node.inputs['Emission Strength'].default_value = .3
        data.materials.append(mat)


def _visible_meshes(bpy, eye, candidates):
    """Raycast from camera eye to real polygon centers of targets in the full scene."""
    from mathutils import Vector
    scene = bpy.context.scene
    graph = bpy.context.evaluated_depsgraph_get()
    origin = Vector(resonite_to_blender(eye))
    visible = set()
    for obj in candidates:
        mesh = obj.data
        # Evenly cover the surface; avoid accepting background coordinates or AABBs.
        stride = max(1, len(mesh.polygons)//100)
        for index in range(0, len(mesh.polygons), stride):
            poly = mesh.polygons[index]
            target = obj.matrix_world @ poly.center
            direction = target - origin
            length = direction.length
            if length < 1e-5:
                continue
            hit, _, _, _, hit_obj, _ = scene.ray_cast(graph, origin, direction.normalized(), distance=length+.02)
            if hit and hit_obj.original == obj:
                visible.add(obj.name)
                break
    return sorted(visible)


def _raycast_report(bpy, layout):
    objects = [o for c in bpy.context.scene.collection.children for o in c.objects if o.type == 'MESH']
    targets = {
        'north_arcologies': [o for o in objects if o.name.startswith('arcology-')],
        'east_forest': [o for o in objects if o.name.startswith(('forest-tree-', 'forest-patch-'))],
        'west_city': [o for o in objects if o.name.startswith('west-city-')],
        'south_city': [o for o in objects if o.name.startswith('south-city-')],
    }
    eyes = {v.key: v.eye for v in layout.viewpoints}
    hits = {key: _visible_meshes(bpy, eyes[view], group)
            for key, view, group in (('north_arcologies', 'plaza-north', targets['north_arcologies']),
                                     ('east_forest', 'east-forest', targets['east_forest']),
                                     ('east_lane', 'east-lane', targets['east_forest']),
                                     ('west_city', 'west-city', targets['west_city']),
                                     ('south_city', 'south-market', targets['south_city']))}
    passed = {'north_arcologies': len(hits['north_arcologies']) >= 2,
              'east_forest': len(hits['east_forest']) >= 2 and len(hits['east_lane']) >= 2,
              'west_city': bool(hits['west_city']), 'south_city': bool(hits['south_city'])}
    return {'hits': hits, 'pass': passed, 'meshCount': len(objects)}


def preview(output_dir: Path, *, sector: str | None = None) -> dict:
    import bpy
    from mathutils import Vector
    if sector and sector not in SECTORS:
        raise KeyError(sector)
    # Isolated sector previews cannot claim directional visibility.
    if bpy.data.filepath:
        raise RuntimeError('preview requires a fresh scene')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    base = output_dir.parent
    if sector:
        path = base / f'{sector}.blend'
        if not path.is_file():
            raise FileNotFoundError(f'missing sector blend: {path}')
        with bpy.data.libraries.load(str(path)) as (src, dst):
            dst.collections = [f'Slum03{sector}Export']
        bpy.context.scene.collection.children.link(dst.collections[0])
        visibility = {'status': 'not-tested', 'reason': 'isolated sector'}
    else:
        _load_scene(bpy, base)
        visibility = _raycast_report(bpy, build_layout())
        _labels(bpy, build_layout())
    output_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    world = bpy.data.worlds.new('Slum03 preview ambient')
    scene.world = world
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.085, .11, .17, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .8
    light_data = bpy.data.lights.new('Preview sun', 'SUN'); light_data.energy = 1.4
    light = bpy.data.objects.new('Preview sun', light_data)
    scene.collection.objects.link(light)
    light.rotation_euler = (.4, -.35, -.5)
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 8
    scene.render.resolution_x = 640; scene.render.resolution_y = 400
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    eyes = {v.key: v.eye for v in build_layout().viewpoints}
    views = (sector,) if sector else tuple(VIEWS)
    evidence = {}
    for view in views:
        camera = bpy.data.objects.new(f'Preview camera {view}', bpy.data.cameras.new(f'Preview camera {view}'))
        scene.collection.objects.link(camera); scene.camera = camera
        camera.data.type = 'PERSP'; camera.data.lens = 25; camera.data.clip_end = 2000
        if sector:
            # Unit previews use a generic high-angle view and are clearly marked isolated.
            eye, target = (0, 45, -65), (0, 0, 0)
        else:
            eye, target = eyes[view], VIEWS[view]
        camera.location = resonite_to_blender(eye)
        direction = Vector(resonite_to_blender(target)) - camera.location
        camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str((output_dir / f'{view}.png').resolve())
        bpy.ops.render.render(write_still=True)
        evidence[view] = {'eye': eye, 'target': target, 'image': str(Path(scene.render.filepath).relative_to(PROJECT_ROOT) if
                                            Path(scene.render.filepath).is_relative_to(PROJECT_ROOT) else
                                            Path(scene.render.filepath)),
                          'bytes': Path(scene.render.filepath).stat().st_size}
    scene_file = output_dir / f'{sector or "combined"}-preview.blend'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_file.resolve()))
    result = {'status': 'offline-preview', 'scene': str(scene_file), 'source': str(base), 'sector': sector,
              'visibility': visibility, 'cameras': evidence, 'labels': 0 if sector else len(build_layout().labels)}
    (output_dir / 'preview-report.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    if not sector and not all(visibility['pass'].values()):
        raise RuntimeError(f'combined real-mesh sightlines failed: {visibility}')
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--sector', default=None)
    args = p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    print(json.dumps(preview(args.output, sector=args.sector)))


if __name__ == '__main__':
    main()
