"""Central factory floor and surviving north-facing footprint of the south-facing wall."""
from .geometry import Assembly, box, mesh, tube
from .types import Layout


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    floor = next(p for p in layout.placements if p.key == 'factory-floor' and p.sector == sector)
    wall = next(p for p in layout.placements if p.key == 'north-wall' and p.sector == sector)
    if wall.params['face'] != 'south':
        raise ValueError('graffiti wall must face south')
    base = box('walkable-slab', (0, -.1, 0), floor.size, 'factory_floor')
    # Replace the top face with exactly coplanar, inlaid oil/scorch cells. There
    # are no raised decals, holes or steps anywhere in the continuous clear area.
    parts_floor = [mesh('understructure', base.vertices,
                        [face for k, face in enumerate(base.faces) if k != 4], 'factory_floor')]
    for i in range(20):
        for j in range(15):
            x0, z0 = layout.plaza.x_min + i*2, layout.plaza.z_min + j*2
            mat = ('asphalt_wet' if (i,j) in {(3,3), (13,4), (17,11), (7,12)} else
                   'concrete_dark' if (i,j) in {(4,3), (14,4), (10,9), (7,11)} else
                   'factory_floor')
            parts_floor.append(mesh('inlaid-floor', [(x0,0,z0+2), (x0+2,0,z0+2),
                                                      (x0+2,0,z0), (x0,0,z0)],
                                    [(0,1,2,3)], mat))
    slab = Assembly('floor', floor.key, sector, floor.origin, parts_floor,
                    {'placement_key': floor.key})
    # A single independently editable wall mesh with an unbroken letter area, broken
    # crown, heavy exterior piers, construction seams and rusty rebar at the edges.
    parts = [box('wall-main', (0, 4.1, 0), (wall.size[0], 8.2, wall.size[2]), 'concrete_stained')]
    for height in (2.5, 6.7):
        parts.append(box('pour-seam', (0, height, -.407), (34.7, .047, .012), 'concrete_dark'))
    for x in (-15, -9, 9, 15):
        parts.append(box('formwork-tie', (x, 6.46, -.414), (.09, .09, .028), 'rust_dark'))
    for x in (-17.4, 17.4):
        parts.append(box('pier', (x, 4.25, -.22), (1.0, 8.5, .45), 'concrete_dark'))
        for offset in (-.25, .25):
            parts.append(tube('exposed-rebar', [(x+offset, 8.1, .08),
                                              (x+offset+.08, 9.35, .08)], .055, 6, 'rust'))
    for x, height in ((-14, .65), (-8, 1.15), (1, .9), (9, 1.45), (15, .55)):
        parts.append(box('broken-crown', (x, 8.2 + height/2, .12),
                         (3.2, height, .55), 'concrete_raw'))
    return [slab, Assembly('north-wall', wall.key, sector, wall.origin, parts,
                           {'placement_key': wall.key})]


def add_plaza(bpy, layout, materials, source_collection, export_collection):
    from .gn_scatter import add_scatter
    from .graffiti import add_graffiti
    rubble, rubble_report = add_scatter(bpy, layout, materials, source_collection, export_collection)
    paint, paint_report = add_graffiti(bpy, layout, materials, export_collection)
    return rubble + paint, {
        'objects': rubble_report['objects'] + paint_report['objects'],
        'uv_issues': rubble_report.get('uv_issues', []) + paint_report.get('uv_issues', []),
        'errors': rubble_report['errors'] + paint_report['errors'],
        'rubble_evaluated_bounds': rubble_report['rubble_evaluated_bounds'],
    }
