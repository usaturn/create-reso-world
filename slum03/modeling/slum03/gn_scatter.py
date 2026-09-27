"""Seeded safe rubble samples and editable, per-cluster Blender Geometry Nodes."""
from __future__ import annotations
import math
import random
from typing import Any

from .geometry import Assembly, box, mesh as polygon_mesh, merge_assembly, tube
from .spatial import validate_clearance, placement_bounds
from .types import Bounds3, Layout, Report, Vec3

# Local shape envelope includes any protruding reinforcing bars after yaw rotation.
MAX_EXTENT: Vec3 = (3.2, 2.5, 3.2)  # largest rotated truss/rebar after scale 1.45


def scatter_samples(layout: Layout, *, seed: int, count: int, max_extent: Vec3) -> tuple[Vec3, ...]:
    """Reject the entire worst-case rotated variant envelope, not the sample point."""
    if count < 0 or len(max_extent) != 3 or any(not math.isfinite(v) or v <= 0 for v in max_extent):
        raise ValueError('count must be nonnegative and maximum extents finite positive')
    if max_extent[0] > layout.plaza.size[0] or max_extent[2] > layout.plaza.size[1]:
        raise ValueError('maximum extent exceeds plaza')
    rng = random.Random(seed)
    hx, _, hz = (v / 2 for v in max_extent)
    wall = next(p for p in layout.placements if p.key == 'north-wall')
    occupied_wall = placement_bounds(wall)
    result: list[Vec3] = []
    attempts = 0
    while len(result) < count:
        attempts += 1
        if attempts > max(1000, count * 500):
            raise ValueError('rubble cannot fit in available perimeter')
        # Intentional heaps near the remnants; the remainder stays sparse.
        if rng.random() < .72:
            cx, cz = rng.choice(((-18, -8), (-18, 8), (18, -8), (18, 8),
                                 (-11, -13), (11, -13), (-11, 12.6), (11, 12.6)))
            spread = .55
        else:
            cx, cz = rng.choice(((-18, -4), (-18, 4), (18, -4), (18, 4),
                                 (-5, -13), (5, -13), (-5, 12.6), (5, 12.6)))
            spread = 1.05
        x, z = rng.gauss(cx, spread), rng.gauss(cz, spread)
        if not (layout.plaza.x_min + hx <= x <= layout.plaza.x_max - hx and
                layout.plaza.z_min + hz <= z <= layout.plaza.z_max - hz):
            continue
        b = Bounds3((x-hx, 0, z-hz), (x+hx, max_extent[1], z+hz))
        if validate_clearance(layout, {f'rubble-{len(result)}': b}):
            continue
        if (b.minimum[0] < occupied_wall.maximum[0] and b.maximum[0] > occupied_wall.minimum[0]
                and b.minimum[2] < occupied_wall.maximum[2] and b.maximum[2] > occupied_wall.minimum[2]):
            continue
        result.append((round(x, 6), 0., round(z, 6)))
    return tuple(result)


def _variant(index):
    """Asymmetric concrete with fully modeled rebar; both fall inside MAX_EXTENT on rotation."""
    if index == 1:  # collapsed I beam: two flanges held apart by a deep web
        return [box('I-beam-web', (0,.4,0), (1.55,.6,.12), 'steel_dark'),
                box('I-beam-upper-flange', (0,.73,0), (1.55,.09,.62), 'rust'),
                box('I-beam-lower-flange', (0,.08,0), (1.55,.12,.62), 'steel_bare'),
                tube('loose-rebar', [(-.4,.1,.35),(-.75,.51,.52)], .045, 7, 'rust_dark'),
                box('truss-bottom-chord', (0,.16,-.1), (2.0,.08,.11), 'steel_dark'),
                box('truss-top-chord', (0,1.09,-.1), (2.0,.08,.11), 'steel_bare'),
                tube('truss-diagonal-a', [(-1,.2,-.1),(1,1.05,-.1)], .04, 6, 'rust'),
                tube('truss-diagonal-b', [(1,.2,-.1),(-1,1.05,-.1)], .04, 6, 'steel_dark')]
    if index == 2:  # crushed equipment with dark casing and exposed circuit tray
        return [box('equipment-housing', (0,.36,0), (1.35,.72,1.1), 'steel_dark'),
                box('broken-tray', (.03,.77,-.12), (1.04,.11,.65), 'electronics'),
                box('broken-cover', (-.17,.68,.47), (.92,.08,.26), 'rust_dark'),
                tube('power-feed', [(-.5,.12,.4),(-.63,.89,.45)], .06, 7, 'rust')]
    width, depth = (1.35, 1.15)
    corners = [(-width/2, 0, -depth/2), (width/2, 0, -depth/2),
               (width/2, 0, depth/2), (-width/2, 0, depth/2)]
    top = [(-width*.38, .66, -depth*.37),
           (width*.42, .72, -depth*.31), (width*.31, .43, depth*.38),
           (-width*.45, .58, depth*.35)]
    chunk = polygon_mesh('fractured-concrete', corners+top,
                         [(3,2,1,0), (4,5,6,7), (0,1,5,4), (1,2,6,5),
                          (2,3,7,6), (3,0,4,7)], 'concrete_stained')
    return [chunk, box('rust-shard', (.0, .35, -.25), (.72, .08, .22), 'rust_dark'),
            tube('rebar', [(.15, .05, -.1), (.43, .68, -.38), (.68, 1.36, -.45)], .055, 7, 'rust')]


def _node_group(bpy, name, variants, seed):
    group = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nodes, links = group.nodes, group.links
    geo = nodes.new('NodeGroupInput')
    join = nodes.new('GeometryNodeJoinGeometry')
    for obj in variants:
        info = nodes.new('GeometryNodeObjectInfo')
        info.inputs['Object'].default_value = obj
        info.inputs['As Instance'].default_value = True
        links.new(info.outputs['Geometry'], join.inputs['Geometry'])
    instance = nodes.new('GeometryNodeInstanceOnPoints')
    instance.inputs['Pick Instance'].default_value = True
    links.new(geo.outputs['Geometry'], instance.inputs['Points'])
    links.new(join.outputs['Geometry'], instance.inputs['Instance'])
    choice = nodes.new('GeometryNodeInputNamedAttribute')
    choice.data_type = 'INT'; choice.inputs['Name'].default_value = 'rubble_variant'
    links.new(choice.outputs['Attribute'], instance.inputs['Instance Index'])
    size = nodes.new('GeometryNodeInputNamedAttribute')
    size.data_type = 'FLOAT_VECTOR'; size.inputs['Name'].default_value = 'rubble_scale'
    links.new(size.outputs['Attribute'], instance.inputs['Scale'])
    yaw = nodes.new('GeometryNodeInputNamedAttribute')
    yaw.data_type = 'FLOAT'; yaw.inputs['Name'].default_value = 'rubble_yaw'
    rotation = nodes.new('FunctionNodeAxisAngleToRotation')
    rotation.inputs['Axis'].default_value = (0, 0, 1)
    links.new(yaw.outputs['Attribute'], rotation.inputs['Angle'])
    links.new(rotation.outputs['Rotation'], instance.inputs['Rotation'])
    result = nodes.new('NodeGroupOutput')
    links.new(instance.outputs['Instances'], result.inputs['Geometry'])
    group['seed'] = seed
    group['variant_count'] = len(variants)
    return group


def add_scatter(bpy, layout: Layout, materials: dict, source_collection, export_collection) -> tuple[list[Any], Report]:
    """Keep point clouds, source variants and GN live; only export static realized copies."""
    from . import blender_io
    import bmesh
    from .vcolor import vertex_colors
    # Each tier is sampled against its entire *maximum* rotated/raised envelope.
    # Large fragments cannot fit the narrow north band in front of the wall; the
    # sampler rejects that area for them rather than clipping the geometry later.
    tiers = ((36, (1.8, 1.3, 1.8), (.54, .70)),
             (24, (2.5, 1.9, 2.5), (.96, 1.10)),
             (12, MAX_EXTENT, (1.32, 1.45)))
    rng = random.Random(layout.seed)
    samples = []
    for tier, (count, extent, scale_range) in enumerate(tiers):
        for p in scatter_samples(layout, seed=layout.seed+tier, count=count, max_extent=extent):
            variant = len(samples) % 3
            samples.append((p, extent, rng.uniform(*scale_range), variant))
    buckets = {'west': [], 'east': [], 'north': [], 'south': []}
    for p, extent, scale, variant in samples:
        if p[0] + extent[0]/2 <= layout.clear.x_min:
            bucket = 'west'
        elif p[0] - extent[0]/2 >= layout.clear.x_max:
            bucket = 'east'
        elif p[2] - extent[2]/2 >= layout.clear.z_max:
            bucket = 'north'
        else:
            bucket = 'south'
        buckets[bucket].append((p, scale, variant))
    # Three-metre cells plus at most 3.2m shape envelopes: independent heaps.
    heaps = {}
    for side, points in buckets.items():
        for p, scale, variant in points:
            ix = math.floor((p[0] - layout.plaza.x_min) / 3)
            iz = math.floor((p[2] - layout.plaza.z_min) / 3)
            heaps.setdefault(f'{side}-{ix}-{iz}', []).append((p, scale, variant))
    heaps = dict(sorted(heaps.items()))
    variant_objects = []
    errors = []
    for i in range(3):
        # Triangulate non-planar fractured quads and twisted rebar sides before UV projection.
        parts = [polygon_mesh(part.name, part.vertices,
                              [tuple(face) if len(face) == 3 else
                               (face[0], face[j], face[j+1])
                               for face in part.faces for j in range(1, len(face)-1)],
                              part.material) for part in _variant(i)]
        merged = merge_assembly(Assembly('rubble-variant', f'rubble-variant-{i}', 'plaza',
                                         (0,0,0), parts))
        obj, issues = blender_io.create_object(bpy, bmesh, merged, (0,0,0), materials)
        errors.extend(issues)
        blender_io.write_colors(obj, vertex_colors(merged, (0,0,0), layout.seed+i))
        obj.hide_render = True
        source_collection.objects.link(obj)
        variant_objects.append(obj)
    exports = []
    eval_bounds = {}
    bpy.context.view_layer.update()
    for name, points in heaps.items():
        cloud = bpy.data.meshes.new(f'Slum03_RubblePoints_{name}')
        # Each local cloud retains the fixed scatter points and yaw, editable in Blender.
        origin = points[0][0]
        cloud.from_pydata([(p[0]-origin[0], p[2]-origin[2], 0) for p, _, _ in points], [], [])
        cloud.update()
        cloud.attributes.new('rubble_scale', 'FLOAT_VECTOR', 'POINT')
        cloud.attributes.new('rubble_variant', 'INT', 'POINT')
        cloud.attributes.new('rubble_yaw', 'FLOAT', 'POINT')
        # Creating another attribute can invalidate earlier RNA references.
        scale_attr = cloud.attributes['rubble_scale']
        variant_attr = cloud.attributes['rubble_variant']
        yaw = cloud.attributes['rubble_yaw']
        for i, (_, scale, variant) in enumerate(points):
            scale_attr.data[i].vector = (scale, scale, scale)
            variant_attr.data[i].value = variant
        for i, item in enumerate(yaw.data):
            item.value = math.radians(random.Random(f'{layout.seed}-{name}-{i}').uniform(-165, 165))
        author = bpy.data.objects.new(f'plaza-rubble-{name}_Source', cloud)
        author.location = (origin[0], origin[2], 0)
        author['slum03_kind'] = 'rubble'
        source_collection.objects.link(author)
        modifier = author.modifiers.new('Editable rubble scatter', 'NODES')
        modifier.node_group = _node_group(bpy, f'Slum03_Rubble_{name}', variant_objects, layout.seed)
        # Evaluate a temporary copy with Realize Instances, never the editable source.
        temporary = author.copy()
        temporary.data = author.data.copy()
        source_collection.objects.link(temporary)
        realized = bpy.data.node_groups.new(f'Slum03_Realize_{name}', 'GeometryNodeTree')
        realized.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        realized.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        inp = realized.nodes.new('NodeGroupInput')
        node = realized.nodes.new('GeometryNodeRealizeInstances')
        out = realized.nodes.new('NodeGroupOutput')
        realized.links.new(inp.outputs['Geometry'], node.inputs['Geometry'])
        realized.links.new(node.outputs['Geometry'], out.inputs['Geometry'])
        temporary.modifiers.new('Export only: realize instances', 'NODES').node_group = realized
        bpy.context.view_layer.update()
        evaluated = temporary.evaluated_get(bpy.context.evaluated_depsgraph_get())
        # Only the evaluated export copy is collapsed; source instances remain editable.
        # bpy.data.meshes.new_from_object evaluates geometry nodes and material/UV/color layers.
        me = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True,
                                             depsgraph=bpy.context.evaluated_depsgraph_get())
        bpy.data.objects.remove(temporary, do_unlink=True)
        obj = bpy.data.objects.new(f'plaza-rubble-{name}', me)
        obj.matrix_world = author.matrix_world.copy()
        obj['slum03_kind'] = 'rubble'
        export_collection.objects.link(obj)
        exports.append(obj)
        coords = [obj.matrix_world @ vertex.co for vertex in me.vertices]
        if not coords:
            errors.append({'code':'MESH', 'object_key':obj.name, 'message':'scatter evaluated to empty geometry'})
            continue
        bounds = Bounds3((min(v.x for v in coords), min(v.z for v in coords), min(v.y for v in coords)),
                         (max(v.x for v in coords), max(v.z for v in coords), max(v.y for v in coords)))
        eval_bounds[obj.name] = {'minimum': bounds.minimum, 'maximum': bounds.maximum}
        errors.extend(validate_clearance(layout, {obj.name: bounds}))
    return exports, {'objects': [{'key': obj.name, 'kind': 'rubble', 'mesh': obj.name} for obj in exports],
                     'rubble_evaluated_bounds': eval_bounds, 'errors': errors}
