"""Independent, pipe-built market stalls with supported display stock."""
from .geometry import Assembly, box, mesh, tube
from .types import Layout


def _stall(p):
    w, h, d = p.size
    shelf_depth = p.params['shelf_depth']
    shelf_height = p.params['shelf_height']
    eave = p.params['awning_height']
    side = 1 if p.origin[0] < 0 else -1  # stocked faces look into market
    x0, x1 = -w/2+.3, w/2-.3
    z0, z1 = -d/2+.3, d/2-.3
    parts = []
    for x in (x0, x1):
        for z in (z0, z1):
            parts.append(tube('post', [(x, 0, z), (x, eave-.04, z)], .065, 8, 'steel_dark'))
        parts.append(tube('beam', [(x, eave-.06, z0), (x, eave-.06, z1)], .065, 8, 'steel_bare'))
    for z in (z0, z1):
        parts.append(tube('beam', [(x0, eave-.06, z), (x1, eave-.06, z)], .065, 8, 'steel_dark'))
    # Two actual pitched/folded tarp runs, meeting a transverse roof ridge.
    for a, b in ((x0, 0), (0, x1)):
        vertices = [(x, eave + (.09 if x == 0 else -.04) + (.04 if z == z0 else 0), z)
                    for z in (z0, z1) for x in (a, b)]
        parts.append(mesh('awning', vertices, ((0, 1, 3, 2),),
                          'tarp_blue' if side == 1 else 'tarp_orange'))
    # Mid-span uprights transfer both shelf-brace loads to grade and the
    # longitudinal eave beam; the corner posts alone are 2.2 m away.
    for z in (-3.5, 3.5):
        parts.append(tube('shelf-upright', [(side*(w/2-.3), 0, z),
                                            (side*(w/2-.3), eave-.04, z)],
                          .065, 8, 'steel_dark'))
    sx = side*(w/2-.3-shelf_depth/2)
    for level in (shelf_height, shelf_height+.75):
        parts.append(box('shelf', (sx, level, 0), (shelf_depth, .12, d-.6), 'pallet_wood'))
        for z in (-3.5, 3.5):
            parts.append(tube('shelf-brace', [(sx, level-.06, z), (side*(w/2-.3), level-.55, z)],
                              .04, 6, 'rust_dark'))
    # Readable stock: exposed traces/chips, monitor bezel/screen, tool shaft/head,
    # jointed prosthesis and an open ribbed crate. Nothing is strewn on the lane.
    y = shelf_height+.06
    parts.append(box('circuit-board', (sx, y+.045, -3.8), (.5, .09, .68), 'electronics'))
    for z in (-3.95, -3.7):
        parts.append(box('chip', (sx, y+.12, z), (.17, .07, .12), 'steel_dark'))
    parts.append(box('tool', (sx, y+.06, -2.6), (.09, .12, .72), 'steel_bare'))
    parts.append(box('tool-head', (sx, y+.11, -2.25), (.34, .18, .12), 'rust'))
    parts.append(box('monitor', (sx, y+.36, -.7), (.5, .65, .8), 'steel_dark'))
    parts.append(box('monitor-screen', (sx+side*.26, y+.38, -.7), (.025, .41, .58), 'glass_dark'))
    parts.append(box('monitor-foot', (sx, y+.045, -.7), (.55, .08, .28), 'steel_bare'))
    parts.append(tube('prosthetic', [(sx, y+.035, 1.1), (sx, y+.3, 1.35),
                                    (sx, y+.035, 1.7)], .085, 8, 'steel_bare'))
    parts.append(box('prosthetic-joint', (sx, y+.3, 1.35), (.27, .27, .26), 'rust_dark'))
    for z in (2.8, 4.0):
        parts.append(box('parts-crate', (sx, y+.17, z), (.52, .36, .65), 'plastic_crate'))
        for x in (sx-.22, sx+.22):
            parts.append(box('crate-rib', (x, y+.21, z), (.04, .35, .66), 'steel_dark'))
    return Assembly('stall', p.key, p.sector, p.origin, parts, {'placement_key': p.key})


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    from .market_detail import detailed_stall
    return [(detailed_stall(p, layout.seed) if p.params.get('detail_profile') == 'v2'
             else _stall(p)) for p in layout.placements
            if p.sector == sector and p.kind == 'stall']
