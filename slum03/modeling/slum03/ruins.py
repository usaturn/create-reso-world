"""Open structural concrete shells: each lot becomes one independently editable building.

All parts are in the Placement foot frame; the source/export merger makes one mesh
per shell without merging neighbouring buildings. No solid filler occupies the rooms.
"""
from .geometry import Assembly, box, mesh, tube, wall_with_openings
from .types import Layout


def _broken_slab(width: float, depth: float, y: float):
    """Irregular concrete cantilever: a real thick slab with a fractured edge."""
    w, d = width / 2, depth / 2
    outline = [(-w+.55, -d+.6), (w-.55, -d+.6), (w-.55, d-.85),
               (w*.42, d-2.4), (w*.27, d-3.2), (w*.06, d-.3),
               (-w*.22, d-1.15), (-w+.55, d-.7)]
    n = len(outline)
    vertices = [(x, y+dy, z) for dy in (0, .48) for x, z in outline]
    faces = [tuple(range(n)), tuple(reversed(range(n, 2*n)))]
    faces.extend((i, (i+1) % n, (i+1) % n+n, i+n) for i in range(n))
    return mesh('broken-slab', vertices, faces, 'concrete_stained')


def _shell(p):
    w, h, d = p.size
    facade_z = d/2 - .58
    openings = []
    level = 0
    while 4.8 + 5*level < h-1.1:
        low, high = 3.2 + 5*level, 4.8 + 5*level
        # Alternate single bays with paired slots; leave enough solid concrete
        # at the damaged crown instead of stamping three windows on every tower.
        if level % 2 == 0:
            openings.append((-1.15, low, 1.15, high))
        else:
            openings.extend(((-w*.34, low, -w*.16, high),
                             (w*.16, low, w*.34, high)))
        level += 1
    wall = wall_with_openings('facade-openings', w-1.2, h-1.1, 1.04,
                              openings, .78, 1.5, 'concrete_stained')
    parts = [mesh(wall.name, [(x, y, z+facade_z) for x, y, z in wall.vertices],
                  wall.faces, wall.material)]
    # The gaps between piers are empty space: slabs, an exposed rear service
    # core and corner uprights define a shell rather than a filled cuboid.
    for x in (-w/2+.68, w/2-.68):
        for z in (-d/2+.65, d/2-.7):
            parts.append(box('structural-pier', (x, (h-1.1)/2, z),
                             (.9, h-1.1, .9), 'concrete_dark'))
    parts.append(box('rear-service-core', (0, (h-1.1)/2, -d/2+.6),
                     (w*.32, h-1.1, 1.1), 'concrete_raw'))
    for y in range(5, int(h-1), 5):
        parts.append(box('floor-slab', (0, y, -.2), (w-1, .55, d-1.2), 'concrete_raw'))
        parts.append(box('edge-beam', (0, y-.43, d/2-.58),
                         (w-1.1, .36, .45), 'concrete_dark'))
    slab = _broken_slab(w, d, h-1.1)
    parts.append(slab)
    parts.append(tube('cantilever-brace', [(w/2-.68, h-3, d/2-.7),
                                              (w*.42, h-1.1, d/2-2.4)],
                      .085, 8, 'steel_dark'))
    for corner in (5, 6):
        # Both positions come from the same polygon that defines the fractured
        # edge (whose local width is half the footprint). Sink each root into
        # the slab before bending the free end outward over the exposed edge.
        x, _, edge_z = slab.vertices[corner]
        parts.append(tube('exposed-rebar', [(x, h-.85, edge_z-.3),
                                             (x+.08, h-.15, edge_z+.12)],
                          .052, 6, 'rust_dark'))
    for y in (2.7, 5.4):
        parts.append(box('pour-joint', (w*.28, y, facade_z+.53),
                         (w*.17, .045, .015), 'concrete_dark'))
    return Assembly('ruin', p.key, p.sector, p.origin, parts, {'placement_key': p.key})


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    from .architecture_detail import detailed_ruin
    return [(detailed_ruin(p, layout.seed) if p.params.get('detail_profile') == 'v2'
             else _shell(p)) for p in layout.placements
            if p.sector == sector and p.kind == 'ruin']
