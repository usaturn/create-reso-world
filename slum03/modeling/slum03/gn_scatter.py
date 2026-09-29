"""Seeded safe rubble samples and editable, per-cluster Blender Geometry Nodes."""
from __future__ import annotations
import math
import random
from typing import Any

from .density_model import FLOOR_DEBRIS_MAX, FLOOR_DEBRIS_PREFIX, stable_seed
from .geometry import Assembly, box, mesh as polygon_mesh, merge_assembly, tube
from .spatial import validate_clearance, placement_bounds
from .types import Bounds3, Layout, RectXZ, Report, Vec3

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


def _debris(index):
    """Small mixed pile: fractured concrete lumps, a brick pair, pipe stub and rebar."""
    def lump(name, cx, cz, sx, sz, top, material):
        base = [(cx-sx/2, 0, cz-sz/2), (cx+sx/2, 0, cz-sz/2),
                (cx+sx/2, 0, cz+sz/2), (cx-sx/2, 0, cz+sz/2)]
        crown = [(cx-sx*.36, top*.8, cz-sz*.3), (cx+sx*.4, top, cz-sz*.28),
                 (cx+sx*.3, top*.7, cz+sz*.36), (cx-sx*.42, top*.9, cz+sz*.33)]
        return polygon_mesh(name, base+crown, [(3,2,1,0), (4,5,6,7), (0,1,5,4), (1,2,6,5),
                                                (2,3,7,6), (3,0,4,7)], material)
    return [lump('debris-lump', -.3, .05, .62, .5, .42, 'concrete_stained'),
            lump('debris-lump', .32, -.22, .44, .4, .3, 'concrete_raw'),
            lump('debris-lump', .12, .38, .36, .3, .24, 'concrete_dark'),
            box('brick', (-.05, .06, -.42), (.24, .12, .12), 'rust_dark'),
            box('brick', (.2, .06, -.5), (.24, .12, .12), 'rust_dark'),
            tube('pipe-stub', [(-.62, .08, -.2), (-.3, .1, -.52)], .06, 8, 'steel_dark'),
            tube('bent-rebar', [(.05, .05, .12), (.3, .4, .22), (.55, .55, .05)], .035, 6, 'rust')]


def _chip(name, cx, cz, sx, sz, top, material, skew=0.):
    """Irregular low lump: flat base sunk 4 mm below the floor, sloped broken crown."""
    base = [(cx-sx/2, -.004, cz-sz/2), (cx+sx/2, -.004, cz-sz/2),
            (cx+sx/2, -.004, cz+sz/2), (cx-sx/2, -.004, cz+sz/2)]
    crown = [(cx-sx*.34+skew, top*.72, cz-sz*.3), (cx+sx*.38, top, cz-sz*.26+skew),
             (cx+sx*.28-skew, top*.62, cz+sz*.34), (cx-sx*.4, top*.86, cz+sz*.3-skew)]
    return polygon_mesh(name, base+crown, [(3,2,1,0), (4,5,6,7), (0,1,5,4), (1,2,6,5),
                                            (2,3,7,6), (3,0,4,7)], material)


def _shard(name, cx, cz, radius, sides, thick, lift, phase, material):
    """Broken floor slab shard: ragged polygon prism with one edge propped up."""
    ring = [(cx + math.cos(phase + math.tau*k/sides) * radius * (.72 + .28*((k*7) % 5)/4),
             cz + math.sin(phase + math.tau*k/sides) * radius * (.72 + .28*((k*3) % 5)/4))
            for k in range(sides)]
    lo = [(x, -.004 + lift * max(0., (x-cx)/radius), z) for x, z in ring]
    hi = [(x, y + thick, z) for x, y, z in lo]
    faces = [tuple(range(sides-1, -1, -1)), tuple(range(sides, 2*sides))]
    faces += [(k, (k+1) % sides, sides + (k+1) % sides, sides + k) for k in range(sides)]
    return polygon_mesh(name, lo+hi, faces, material)


def _floor_chips():
    """Concrete chips and gravel knocked off the slab (all under 8 cm)."""
    return [_chip('chip', -.18, .08, .26, .2, .078, 'concrete_stained', .02),
            _chip('chip', .1, -.14, .19, .16, .06, 'concrete_raw'),
            _chip('chip', .2, .17, .11, .1, .04, 'concrete_dark', -.01),
            _chip('chip', -.05, -.26, .09, .08, .032, 'factory_floor'),
            _chip('chip', -.27, -.1, .08, .07, .03, 'concrete_raw', .01),
            _chip('chip', .03, .26, .07, .06, .026, 'concrete_stained')]


def _floor_shards():
    """Flat broken slab/tile shards and half a brick."""
    return [_shard('slab-shard', -.1, .02, .21, 6, .04, .018, .3, 'factory_floor'),
            _shard('slab-shard', .18, -.13, .13, 5, .035, 0., 1.2, 'concrete_patch'),
            _shard('tile-shard', .14, .2, .09, 5, .02, .012, 2.1, 'concrete_dark'),
            box('half-brick', (-.22, .024, -.2), (.11, .056, .08), 'rust_dark'),
            _chip('grit', .27, .05, .06, .05, .022, 'concrete_raw')]


def _floor_scrap():
    """Metal offcuts: bent rebar lying flat, a pipe stub, plate scrap and a nut."""
    return [tube('flat-rebar', [(-.3, .009, -.08), (-.02, .009, .02), (.28, .011, -.06)],
                 .012, 6, 'rust', (0., 1., 0.)),
            tube('pipe-offcut', [(-.12, .028, .2), (.12, .028, .24)], .032, 8, 'steel_dark'),
            box('plate-scrap', (.12, .002, -.2), (.2, .012, .13), 'rust'),
            box('nut', (-.2, .012, .18), (.035, .03, .035), 'steel_bare'),
            _chip('chip', .25, .12, .08, .07, .03, 'concrete_stained')]


def _floor_litter():
    """Soft rubbish blown onto the slab: plywood splinters, a sheet scrap, cable."""
    splinter = box('plywood-splinter', (0, .006, 0), (.34, .014, .07), 'plywood')
    angle = .5
    splinter = polygon_mesh('plywood-splinter',
                            [(x*math.cos(angle) - z*math.sin(angle) - .08, y,
                              x*math.sin(angle) + z*math.cos(angle) + .05)
                             for x, y, z in splinter.vertices], splinter.faces, 'plywood')
    return [splinter,
            box('sheet-scrap', (.14, .0015, -.14), (.24, .007, .17), 'tarp_blue'),
            tube('cable', [(-.28, .008, -.12), (-.1, .008, -.24), (.06, .009, -.2),
                           (.2, .008, .02)], .009, 5, 'rubber', (0., 1., 0.)),
            _chip('chip', .22, .22, .09, .08, .035, 'concrete_raw')]


VARIANT_KINDS = {0: 'concrete', 1: 'steel', 2: 'machine', 3: 'debris',
                 4: 'chips', 5: 'shards', 6: 'scrap', 7: 'litter'}
# Size class of each variant at its largest instance scale; only 'small' (walkable,
# <= FLOOR_DEBRIS_MAX, collider-free) may be placed on the central floor.
SIZE_CLASS = {0: 'large', 1: 'large', 2: 'large', 3: 'medium',
              4: 'small', 5: 'small', 6: 'small', 7: 'small'}
FLOOR_VARIANTS = (4, 5, 6, 7)
_FLOOR_BUILDERS = {4: _floor_chips, 5: _floor_shards, 6: _floor_scrap, 7: _floor_litter}


def variant_parts(index):
    """Source geometry of one instanced variant, at the instance origin."""
    if index not in VARIANT_KINDS:
        raise ValueError(f'unknown rubble variant {index}')
    if index in _FLOOR_BUILDERS:
        return _FLOOR_BUILDERS[index]()
    return _debris(index) if index == 3 else _variant(index)


# Legacy tiers are retained byte-for-byte for existing and representative builds.
LEGACY_TIERS = ((36, (1.8, 1.3, 1.8), (.54, .70)),
                (24, (2.5, 1.9, 2.5), (.96, 1.10)),
                (12, MAX_EXTENT, (1.32, 1.45)))
# Task 8 full district: more small debris, fewer large pieces; a cyclic mix per
# tier keeps concrete, steel, machinery and small debris all readable.
FULL_TIERS = ((64, (1.8, 1.3, 1.8), (.54, .70)),
              (34, (2.5, 1.9, 2.5), (.96, 1.10)),
              (16, MAX_EXTENT, (1.32, 1.45)))
FULL_MIX = ((3, 0, 3, 1, 3, 2, 0, 3), (0, 2, 1, 3, 0, 1), (0, 1, 2, 0))


def _full_stage(layout: Layout) -> bool:
    return layout.density is not None and layout.density.stage == 'full'


# --- Task 12 (revision 1): walkable small debris on the central floor ---------
FLOOR_COUNT = 200
FLOOR_SCALE = (.8, 1.15)
FLOOR_EXTENT: Vec3 = (.9, FLOOR_DEBRIS_MAX, .9)   # every floor variant at FLOOR_SCALE[1]
FLOOR_ROUTE_MARGIN = .3   # beyond each main route/entrance effective width
FLOOR_SPACING = .5
FLOOR_CELL = (8., 5.5)    # heap cells never straddle the routes crossing at the origin
FLOOR_MIX = (4, 4, 4, 5, 5, 5, 6, 6, 7, 7)


def floor_keepouts(layout: Layout) -> list[RectXZ]:
    """Main-route effective widths (every plaza entrance lies on one) and authored branches."""
    rects = list(layout.routes)
    if layout.density is not None:
        for route in layout.density.routes:
            rects.append(route.corridor)
            rects.extend(o.bounds for o in route.openings)
        rects.extend(layout.density.branch_clearances)
    return rects


def floor_debris_samples(layout: Layout) -> list[dict]:
    """Seeded carpet of small debris over the central floor, clustered with bare patches."""
    from .plaza import floor_features
    rng = random.Random(stable_seed(layout.seed, FLOOR_DEBRIS_PREFIX, 'samples'))
    clear = layout.clear
    half = FLOOR_EXTENT[0] / 2
    blocked = [RectXZ(r.x_min - FLOOR_ROUTE_MARGIN - half, r.x_max + FLOOR_ROUTE_MARGIN + half,
                      r.z_min - FLOOR_ROUTE_MARGIN - half, r.z_max + FLOOR_ROUTE_MARGIN + half)
               for r in floor_keepouts(layout)]
    blocked += [RectXZ(x0 - .1 - half, x1 + .1 + half, z0 - .1 - half, z1 + .1 + half)
                for x0, x1, z0, z1 in floor_features(layout)['pits']]

    def free(x, z):
        return (clear.x_min + half + .05 <= x <= clear.x_max - half - .05 and
                clear.z_min + half + .05 <= z <= clear.z_max - half - .05 and
                not any(r.x_min < x < r.x_max and r.z_min < z < r.z_max for r in blocked))
    centres = []
    while len(centres) < 16:  # four piles per quadrant between the crossing routes
        west, south = len(centres) % 2, len(centres) // 2 % 2
        x = rng.uniform(clear.x_min, 0) if west else rng.uniform(0, clear.x_max)
        z = rng.uniform(clear.z_min, 0) if south else rng.uniform(0, clear.z_max)
        if free(x, z):
            centres.append((x, z, rng.uniform(.7, 1.5)))
    result: list[dict] = []
    attempts = 0
    while len(result) < FLOOR_COUNT:
        attempts += 1
        if attempts > FLOOR_COUNT * 400:
            raise ValueError('floor debris cannot fit the central floor')
        mode = rng.random()
        if mode < .6:  # piles around knocked-off concrete, with bare floor between them
            cx, cz, spread = rng.choice(centres)
            x, z = rng.gauss(cx, spread), rng.gauss(cz, spread)
        elif mode < .8:  # spill inward from the perimeter heaps
            side = rng.randrange(4)
            t = rng.random()
            depth = abs(rng.gauss(0, 1.2)) + half + .05
            x, z = ((clear.x_min + depth, clear.z_min + t*(clear.z_max-clear.z_min)) if side == 0 else
                    (clear.x_max - depth, clear.z_min + t*(clear.z_max-clear.z_min)) if side == 1 else
                    (clear.x_min + t*(clear.x_max-clear.x_min), clear.z_min + depth) if side == 2 else
                    (clear.x_min + t*(clear.x_max-clear.x_min), clear.z_max - depth))
        else:  # sparse strays
            x, z = rng.uniform(clear.x_min, clear.x_max), rng.uniform(clear.z_min, clear.z_max)
        if not free(x, z) or any(math.dist((x, z), (o['point'][0], o['point'][2])) < FLOOR_SPACING
                                 for o in result):
            continue
        result.append({'point': (round(x, 6), 0., round(z, 6)), 'extent': FLOOR_EXTENT,
                       'scale': rng.uniform(*FLOOR_SCALE), 'variant': rng.choice(FLOOR_MIX),
                       'tier': 3})
    return result


def scatter_plan(layout: Layout) -> dict[str, list[dict]]:
    """Deterministic heaps of instances (point, envelope, scale, variant, yaw)."""
    full = _full_stage(layout)
    rng = random.Random(layout.seed)
    samples = []
    for tier, (count, extent, scale_range) in enumerate(FULL_TIERS if full else LEGACY_TIERS):
        for k, p in enumerate(scatter_samples(layout, seed=layout.seed+tier, count=count,
                                              max_extent=extent)):
            variant = FULL_MIX[tier][k % len(FULL_MIX[tier])] if full else len(samples) % 3
            samples.append((p, extent, rng.uniform(*scale_range), variant, tier))
    heaps: dict[str, list[dict]] = {}
    for p, extent, scale, variant, tier in samples:
        if p[0] + extent[0]/2 <= layout.clear.x_min:
            side = 'west'
        elif p[0] - extent[0]/2 >= layout.clear.x_max:
            side = 'east'
        elif p[2] - extent[2]/2 >= layout.clear.z_max:
            side = 'north'
        else:
            side = 'south'
        # Three-metre cells plus at most 3.2m shape envelopes: independent heaps.
        ix = math.floor((p[0] - layout.plaza.x_min) / 3)
        iz = math.floor((p[2] - layout.plaza.z_min) / 3)
        heaps.setdefault(f'{side}-{ix}-{iz}', []).append(
            {'point': p, 'extent': extent, 'scale': scale, 'variant': variant, 'tier': tier})
    if full:
        for item in floor_debris_samples(layout):
            ix = math.floor(item['point'][0] / FLOOR_CELL[0]) + 2
            iz = math.floor(item['point'][2] / FLOOR_CELL[1]) + 2
            heaps.setdefault(f'floor-{ix}-{iz}', []).append(item)
    heaps = dict(sorted(heaps.items()))
    for name, items in heaps.items():
        for i, item in enumerate(items):
            item['yaw'] = math.radians(random.Random(f'{layout.seed}-{name}-{i}').uniform(-165, 165))
    return heaps


def realize_instance(item: dict):
    """Pure-Python equivalent of the exported Realize Instances result (root-local)."""
    c, s = math.cos(item['yaw']), math.sin(item['yaw'])
    x0, y0, z0 = item['point']
    k = item['scale']
    result = []
    for part in variant_parts(item['variant']):
        # Blender rotates about its Z (= Resonite Y) with Blender Y = Resonite Z.
        result.append(polygon_mesh(part.name, [(x0 + k*(x*c - z*s), y0 + k*y, z0 + k*(x*s + z*c))
                                               for x, y, z in part.vertices], part.faces, part.material))
    return result


def _node_group(bpy, name, variants, seed, ordered=False):
    """Instance on points; ``ordered`` makes Pick Instance index i select ``variants[i]``.

    Join Geometry lists its multi-input links newest first, so linking the variants
    in order makes index i pick variants[-1-i]. Legacy and representative builds keep
    that historical (reversed) pick so their exports stay byte-identical; the full
    stage links in reverse so the realized geometry matches ``scatter_plan``.
    """
    group = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nodes, links = group.nodes, group.links
    geo = nodes.new('NodeGroupInput')
    join = nodes.new('GeometryNodeJoinGeometry')
    for obj in (reversed(variants) if ordered else variants):
        info = nodes.new('GeometryNodeObjectInfo')
        info.inputs['Object'].default_value = obj
        info.inputs['As Instance'].default_value = True
        links.new(info.outputs['Geometry'], join.inputs['Geometry'])
    if ordered:
        picked = [link.from_node.inputs['Object'].default_value for link in join.inputs['Geometry'].links]
        if picked != list(variants):
            raise ValueError(f'{name}: instance index order does not match the variant index')
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
    heaps = scatter_plan(layout)
    variant_count = len(VARIANT_KINDS) if _full_stage(layout) else 3
    variant_objects = []
    errors = []
    for i in range(variant_count):
        # Triangulate non-planar fractured quads and twisted rebar sides before UV projection.
        parts = [polygon_mesh(part.name, part.vertices,
                              [tuple(face) if len(face) == 3 else
                               (face[0], face[j], face[j+1])
                               for face in part.faces for j in range(1, len(face)-1)],
                              part.material) for part in variant_parts(i)]
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
        origin = points[0]['point']
        cloud.from_pydata([(item['point'][0]-origin[0], item['point'][2]-origin[2], 0)
                           for item in points], [], [])
        cloud.update()
        cloud.attributes.new('rubble_scale', 'FLOAT_VECTOR', 'POINT')
        cloud.attributes.new('rubble_variant', 'INT', 'POINT')
        cloud.attributes.new('rubble_yaw', 'FLOAT', 'POINT')
        # Creating another attribute can invalidate earlier RNA references.
        scale_attr = cloud.attributes['rubble_scale']
        variant_attr = cloud.attributes['rubble_variant']
        yaw = cloud.attributes['rubble_yaw']
        for i, item in enumerate(points):
            scale_attr.data[i].vector = (item['scale'],) * 3
            variant_attr.data[i].value = item['variant']
            yaw.data[i].value = item['yaw']
        author = bpy.data.objects.new(f'plaza-rubble-{name}_Source', cloud)
        author.location = (origin[0], origin[2], 0)
        author['slum03_kind'] = 'rubble'
        source_collection.objects.link(author)
        modifier = author.modifiers.new('Editable rubble scatter', 'NODES')
        modifier.node_group = _node_group(bpy, f'Slum03_Rubble_{name}', variant_objects, layout.seed,
                                          ordered=_full_stage(layout))
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
        if name.startswith('floor-') and bounds.maximum[1] > FLOOR_DEBRIS_MAX:
            errors.append({'code': 'FLOOR_DEBRIS_HEIGHT', 'object_key': obj.name,
                           'message': f'realized floor debris {bounds.maximum[1]:.3f} m tall'})
        errors.extend(validate_clearance(layout, {obj.name: bounds}))
    return exports, {'objects': [{'key': obj.name, 'kind': 'rubble', 'mesh': obj.name} for obj in exports],
                     'rubble_evaluated_bounds': eval_bounds, 'errors': errors}
