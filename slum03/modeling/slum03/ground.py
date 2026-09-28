"""District foundation and owned, collider-free directional scenic support."""
import random
from .geometry import Assembly, box, mesh
from .types import Layout


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    ground, = (p for p in layout.placements if p.key == 'district-ground' and p.sector == sector)
    floor, = (p for p in layout.placements if p.key == 'factory-floor')
    x, y, z = ground.origin
    sx, sy, sz = ground.size
    left, right, south, north = -sx/2, sx/2, -sz/2, sz/2
    fx0 = floor.origin[0] - floor.size[0]/2 - x
    fx1 = floor.origin[0] + floor.size[0]/2 - x
    fz0 = floor.origin[2] - floor.size[2]/2 - z
    fz1 = floor.origin[2] + floor.size[2]/2 - z
    if not (left < fx0 < fx1 < right and south < fz0 < fz1 < north):
        raise ValueError('factory floor must fit inside district foundation')
    bottom = ground.params.get('local_y_min', 0)
    top = bottom + sy
    parts = []
    # Four disjoint visible strips leave the factory slab as the sole top face
    # over the entire 40×30 footprint. Edges meet only at their boundaries.
    for name, x0, x1, z0, z1 in (
        ('west-foundation', left, fx0, south, north),
        ('east-foundation', fx1, right, south, north),
        ('south-foundation', fx0, fx1, south, fz0),
        ('north-foundation', fx0, fx1, fz1, north),
    ):
        parts.append(box(name, ((x0+x1)/2, (bottom+top)/2, (z0+z1)/2),
                         (x1-x0, sy, z1-z0), 'concrete_raw'))
    # Provide a structural seat below, not a second coplanar visible surface.
    floor_bottom = floor.origin[1] + floor.params.get('local_y_min', 0) - y
    if floor_bottom > bottom:
        parts.append(box('factory-subbase', ((fx0+fx1)/2, (bottom+floor_bottom)/2,
                                            (fz0+fz1)/2),
                         (fx1-fx0, floor_bottom-bottom, fz1-fz0), 'concrete_raw'))
    result = [Assembly('foundation', 'district-foundation', sector, ground.origin,
                       parts, {'placement_key': ground.key})]
    # Scenic pads are owned visual geometry only. Join the district/road bank
    # exactly at their edges; leave the water span (Z=78..112) unobstructed.
    sites = {p.key: p for p in layout.placements}
    def rect(key):
        p = sites[key]
        return (p.origin[0]-p.size[0]/2, p.origin[0]+p.size[0]/2,
                p.origin[2]-p.size[2]/2, p.origin[2]+p.size[2]/2)
    district = layout.district
    river = rect('river')
    west = rect('west-city'); south_city = rect('south-city'); forest = rect('forest')
    scenic = (
        ('west', west[0], district.x_min, west[2], river[2]),
        ('south', south_city[0], south_city[1], south_city[2], district.z_min),
        # The canopy hook's crown volumes extend up to 4m past the forest anchor.
        ('forest', rect('east-sidewalk')[1], forest[1]+5, forest[2]-4, river[2]),
        ('north-towers-west', rect('north-towers')[0], district.x_max,
         river[3], rect('north-towers')[3]),
        ('north-towers-east', district.x_max, rect('north-towers')[1],
         rect('north-turnback')[3], rect('north-towers')[3]),
        *((key, *rect(key)) for key in ('arcology-terraces', 'arcology-gate', 'arcology-towers')),
    )
    for key, x0, x1, z0, z1 in scenic:
        if x0 >= x1 or z0 >= z1 or (z0 < river[3] and z1 > river[2]):
            raise ValueError(f'scenic support intersects river or has invalid footprint: {key}')
        name = f'scenic-support-{key}'
        part = box(name, ((x0+x1)/2, (bottom+top)/2, (z0+z1)/2),
                   (x1-x0, sy, z1-z0), 'mud' if key == 'forest' else 'backdrop_ground')
        result.append(Assembly('scenic-support', name, sector, (0, 0, 0), [part],
                               {'nonwalkable': True}))
    # A broken foliage backstop obscures the *far edge* between foreground trees;
    # this follows the same forest placement, not an arbitrary world-sized slab.
    from .forest import crown, _triangulate
    rng = random.Random(layout.seed + 716)
    x = forest[1] - 2.5
    z0, z1 = forest[2]-3, river[2]-1
    width = (z1-z0)/12
    hedge = []
    for i in range(12):
        height = rng.uniform(14, 18)
        part = _triangulate(crown(f'forest-edge-{i}', 7, height,
                                   'leaf_deep' if i%2 else 'leaf_olive'))
        hedge.append(mesh(part.name, [(v[0]+x, v[1]+height*.48, v[2]+z0+(i+.5)*width)
                                      for v in part.vertices], part.faces, part.material))
    result.append(Assembly('scenic-support', 'forest-backstop', sector, (0, 0, 0), hedge,
                           {'nonwalkable': True}))
    return result
