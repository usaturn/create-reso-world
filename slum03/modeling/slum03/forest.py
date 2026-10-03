"""Near trees as independent meshes; deeper crowns as editable GN patches.

The forest is nonwalkable. Each near tree has a distinct trunk/branches/crown
silhouette; far patches are foliage volumes, not a wall of green billboards.
"""
from __future__ import annotations
import math
import random
from .geometry import Assembly, mesh, merge_assembly, tube
from .types import Layout, Report


def crown(name: str, radius: float, height: float, material: str):
    """Faceted asymmetric foliage volume about the local origin (Y up)."""
    vertices = []
    for y, scale in ((-height*.45, .48), (-height*.22, .9), (height*.24, 1.), (height*.43, .51)):
        for i in range(9):
            angle = math.tau * i / 9
            jitter = 1 + .08 * math.sin(i * 5.1 + radius)
            vertices.append((radius * scale * jitter * math.cos(angle), y,
                             radius * scale * jitter * math.sin(angle)))
    vertices.extend(((0, -height*.48, 0), (0, height*.51, 0)))
    faces = []
    for ring in range(3):
        for i in range(9):
            a, b = ring*9+i, ring*9+(i+1)%9
            faces.append((a, b, b+9, a+9))
    for i in range(9):
        faces.extend(((36, (i+1)%9, i), (27+i, 27+(i+1)%9, 37)))
    return mesh(name, vertices, [tuple(reversed(face)) for face in faces], material)


def _shift(part, xyz):
    return mesh(part.name, [(v[0]+xyz[0], v[1]+xyz[1], v[2]+xyz[2]) for v in part.vertices],
                part.faces, part.material)


def _triangulate(part):
    # Bent branches and lobed foliage have non-planar quads; UV projection of
    # each explicit triangle is metric and avoids hidden Blender triangulation.
    return mesh(part.name, part.vertices,
                [face if len(face) == 3 else (face[0], face[i], face[i+1])
                 for face in part.faces for i in range(1, len(face)-1)], part.material)


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    if sector != 'forest':
        raise ValueError(sector)
    site = next(p for p in layout.placements if p.key == 'forest')
    rng = random.Random(layout.seed + 714)
    trees = []
    # Rows break alignment and allow sightlines between discrete close trunks.
    for row, x in enumerate((site.origin[0]-46, site.origin[0]-33, site.origin[0]-20)):
        for col in range(8):
            z = site.origin[2]-63 + col*17 + (row % 2)*7 + rng.uniform(-3, 3)
            tx = x + rng.uniform(-2, 2)
            height = rng.uniform(17, 30)
            spread = rng.uniform(4.5, 7.2)
            parts = [tube('trunk-main', [(0, 0, 0), (.25, height*.35, .2),
                                       (-.3, height*.68, -.12)], .74 + height*.016, 9, 'bark')]
            for j in range(3):
                angle = (col*1.3 + j*2.1 + row*.4)
                end = (math.cos(angle)*spread*.72, height*(.72 + j*.055),
                       math.sin(angle)*spread*.72)
                parts.append(tube(f'branch-{j}', [(-.3, height*(.43+j*.09), -.12),
                                                 (end[0]*.5, height*.64, end[2]*.5), end],
                                  .26 + (2-j)*.065, 7, 'bark'))
                parts.append(_shift(crown(f'crown-{j}', spread*(.66 if j else .9),
                                          height*(.39 if j else .51),
                                          ('leaf_deep', 'leaf_moss', 'leaf_olive')[(col+j+row)%3]),
                                    end))
            parts.append(_shift(crown('crown-top', spread*.82, height*.46,
                                      ('leaf_deep', 'leaf_moss', 'leaf_olive')[(col+row)%3]),
                                (-.3, height*.82, -.12)))
            assert tx - spread > site.origin[0] - site.size[0]/2
            trees.append(Assembly('tree', f'forest-tree-{row}-{col}', sector,
                                  (round(tx, 4), 0, round(z, 4)), [_triangulate(part) for part in parts],
                                  {'placement_key': f'forest-tree-{row}-{col}'}))
    return trees


def add_canopy(bpy, layout: Layout, materials: dict, source_collection,
               export_collection) -> tuple[list, Report]:
    """Retain GN point clouds + variants; export only per-patch realized mesh copies."""
    from . import blender_io
    from .vcolor import vertex_colors
    import bmesh
    rng = random.Random(layout.seed + 715)
    site = next(p for p in layout.placements if p.key == 'forest')
    variants = []
    errors = []
    for j in range(3):
        parts = [crown(f'foliage-{j}-{i}', 5.5+i*.8, 9+i*2,
                       ('leaf_deep', 'leaf_moss', 'leaf_olive')[(j+i)%3]) for i in range(3)]
        shifted = [_shift(part, (i*3.2-3.2, (i%2)*2, (i-1)*2.4)) for i, part in enumerate(parts)]
        merged = merge_assembly(Assembly('canopy-source', f'forest-canopy-variant-{j}',
                                         'forest', (0, 0, 0), shifted))
        obj, issues = blender_io.create_object(bpy, bmesh, merged, (0, 0, 0), materials)
        errors.extend(issues)
        blender_io.write_colors(obj, vertex_colors(merged, (0, 0, 0), layout.seed+j))
        obj.hide_render = True
        source_collection.objects.link(obj)
        variants.append(obj)
    group = bpy.data.node_groups.new('Slum03_CanopyScatter', 'GeometryNodeTree')
    group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nodes, links = group.nodes, group.links
    inp, out = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
    join = nodes.new('GeometryNodeJoinGeometry')
    for obj in variants:
        node = nodes.new('GeometryNodeObjectInfo')
        node.inputs['Object'].default_value = obj
        node.inputs['As Instance'].default_value = True
        links.new(node.outputs['Geometry'], join.inputs['Geometry'])
    instance = nodes.new('GeometryNodeInstanceOnPoints')
    instance.inputs['Pick Instance'].default_value = True
    links.new(inp.outputs['Geometry'], instance.inputs['Points'])
    links.new(join.outputs['Geometry'], instance.inputs['Instance'])
    index = nodes.new('GeometryNodeInputNamedAttribute')
    index.data_type = 'INT'; index.inputs['Name'].default_value = 'canopy_variant'
    links.new(index.outputs['Attribute'], instance.inputs['Instance Index'])
    scale = nodes.new('GeometryNodeInputNamedAttribute')
    scale.data_type = 'FLOAT_VECTOR'; scale.inputs['Name'].default_value = 'canopy_scale'
    links.new(scale.outputs['Attribute'], instance.inputs['Scale'])
    links.new(instance.outputs['Instances'], out.inputs['Geometry'])
    # Separate export-only group: authoring node retains live instances.
    export_group = bpy.data.node_groups.new('Slum03_CanopyExportRealize', 'GeometryNodeTree')
    export_group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    export_group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    ein, eout = export_group.nodes.new('NodeGroupInput'), export_group.nodes.new('NodeGroupOutput')
    real = export_group.nodes.new('GeometryNodeRealizeInstances')
    export_group.links.new(ein.outputs['Geometry'], real.inputs['Geometry'])
    export_group.links.new(real.outputs['Geometry'], eout.inputs['Geometry'])
    group['seed'] = layout.seed
    exports = []
    # Independent patches instead of one world-spanning mesh. The foreground
    # crowns remain separate trees; distance replaces detail, not density.
    for row, x in enumerate((site.origin[0]-9, site.origin[0]+14, site.origin[0]+36)):
        for col, z in enumerate((site.origin[2]-49, site.origin[2]-15,
                                 site.origin[2]+20, site.origin[2]+53)):
            cloud = bpy.data.meshes.new(f'Slum03_CanopyPoints_{row}_{col}')
            points = [(rng.uniform(-8, 8), rng.uniform(-15, 15), rng.uniform(16, 27))
                      for _ in range(11)]
            cloud.from_pydata(points, [], [])
            cloud.update()
            cloud.attributes.new('canopy_variant', 'INT', 'POINT')
            cloud.attributes.new('canopy_scale', 'FLOAT_VECTOR', 'POINT')
            for i in range(len(points)):
                cloud.attributes['canopy_variant'].data[i].value = rng.randrange(3)
                s = rng.uniform(.75, 1.5)
                cloud.attributes['canopy_scale'].data[i].vector = (s, s, s)
            author = bpy.data.objects.new(f'forest-patch-{row}-{col}_Source', cloud)
            author.location = (x, z, 0)
            source_collection.objects.link(author)
            author.modifiers.new('Editable canopy', 'NODES').node_group = group
            temporary = author.copy()
            temporary.data = author.data.copy()
            source_collection.objects.link(temporary)
            temporary.modifiers.new('Export only: realize', 'NODES').node_group = export_group
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()
            evaluated = temporary.evaluated_get(depsgraph)
            me = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
            bpy.data.objects.remove(temporary, do_unlink=True)
            obj = bpy.data.objects.new(f'forest-patch-{row}-{col}', me)
            obj.matrix_world = author.matrix_world.copy()
            obj['slum03_kind'] = 'canopy-patch'
            export_collection.objects.link(obj)
            if not me.vertices or not me.uv_layers:
                errors.append({'code': 'MESH', 'object_key': obj.name, 'message': 'missing realized canopy or UV0'})
            exports.append(obj)
    return exports, {'objects': [{'key': o.name, 'kind': 'canopy-patch', 'mesh': o.name} for o in exports],
                     'errors': errors}
