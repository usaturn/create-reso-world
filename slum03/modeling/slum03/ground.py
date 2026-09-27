"""Walkable district foundation, expressed using the canonical ground placement."""
from .geometry import Assembly, box
from .types import Layout


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    ground, = (p for p in layout.placements if p.key == 'district-ground' and p.sector == sector)
    x, y, z = ground.origin
    center_y = ground.params.get('local_y_min', 0) + ground.size[1]/2
    return [Assembly('foundation', 'district-foundation', sector, (x, y, z),
                     [box('foundation', (0, center_y, 0), ground.size, 'concrete_raw')],
                     {'placement_key': ground.key})]
