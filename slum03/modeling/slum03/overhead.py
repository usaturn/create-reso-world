"""Supported electrical span west of the plaza, with ground-anchored end poles."""
from .geometry import Assembly, box, catenary, tube
from .types import Layout


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    result = []
    for p in layout.placements:
        if p.sector != sector or p.kind != 'overhead':
            continue
        half = p.size[0]/2
        span = half-.75
        base = -p.origin[1]
        parts = []
        for x in (-span, span):
            parts.extend((
                box('pole-footing', (x, base+.16, 0), (.6, .32, .6), 'concrete_raw'),
                box('pole', (x, (base+.22)/2, 0), (.22, -base+.22, .22), 'steel_dark'),
                box('crossarm', (x, -.1, 0), (.52, .12, .6), 'steel_dark'),
                box('insulator', (x, -.035, 0), (.2, .22, .19), 'rust_dark'),
            ))
        # Endpoint centre lies on each insulator, not in midair. Sag stays above
        # the 3m activity-air limit and all supports stay outside walking routes.
        points = catenary((-span, -.02, 0), (span, -.02, 0), .68, 16)
        parts.append(tube('power-cable', points, .042, 6, 'rubber'))
        for x in (-span, span):
            parts.append(tube('strain-brace', [(x, -1.15, -.1),
                                                (x, -.18, -.26)], .04, 6, 'steel_bare'))
        result.append(Assembly('overhead', p.key, sector, p.origin, parts,
                               {'placement_key': p.key}))
    return result
