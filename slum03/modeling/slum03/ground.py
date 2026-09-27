"""District foundation with a recessed seat for the separately editable factory slab."""
from .geometry import Assembly, box
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
    return [Assembly('foundation', 'district-foundation', sector, ground.origin,
                     parts, {'placement_key': ground.key})]
