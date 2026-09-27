"""Continuous eastern approach, exposed watercourse, supported crossing and open checkpoint.

All coordinates come from Layout placements. Mesh vertices are local to each
placement and each assembly exports as one editable Blender mesh.
"""
from .geometry import Assembly, box, mesh
from .types import Layout


def _rect(part, name, x0, x1, y0, y1, z0, z1, material):
    """World-space extrema to assembly-local box; prevents a second coordinate plan."""
    ox, oy, oz = part.origin
    return box(name, ((x0+x1)/2-ox, (y0+y1)/2-oy, (z0+z1)/2-oz),
               (x1-x0, y1-y0, z1-z0), material)


def _edges(p):
    x, y, z = p.origin
    sx, _, sz = p.size
    return x-sx/2, x+sx/2, z-sz/2, z+sz/2


def _pavement(p, bridge):
    x0, x1, z0, z1 = _edges(p)
    _, _, cut0, cut1 = _edges(bridge)
    bottom = p.origin[1]+p.params['local_y_min']
    parts = [_rect(p, 'south-approach', x0, x1, bottom, p.origin[1], z0, cut0,
                   'asphalt' if p.kind == 'roadway' else 'concrete_stained'),
             _rect(p, 'north-approach', x0, x1, bottom, p.origin[1], cut1, z1,
                   'asphalt' if p.kind == 'roadway' else 'concrete_stained')]
    return Assembly(p.kind, p.key, p.sector, p.origin, parts, {'placement_key': p.key})


def _river(p):
    x0, x1, z0, z1 = _edges(p)
    x, y, z = p.origin
    # An actual water surface, not a thick slab protruding below the visible
    # waterline: minimum visible local Y remains exactly -4.0.
    surface = mesh('water-surface', ((x0-x, 0, z0-z), (x0-x, 0, z1-z),
                                    (x1-x, 0, z1-z), (x1-x, 0, z0-z)),
                   ((0, 1, 2, 3),), 'asphalt_wet')
    return Assembly('river', p.key, p.sector, p.origin, [surface],
                    {'placement_key': p.key})


def _bridge(p, sidewalk_west, road, sidewalk_east, river):
    left, right, south, north = _edges(p)
    water_south, water_north = _edges(river)[2:]
    parts = []
    # Three non-overlapping top faces continue the three approach lanes at Y=0.
    for lane, mat in ((sidewalk_west, 'concrete_stained'),
                      (road, 'asphalt'), (sidewalk_east, 'concrete_stained')):
        x0, x1, _, _ = _edges(lane)
        parts.append(_rect(p, 'span-deck', x0, x1, -.4, 0, south, north, mat))
    # Longitudinal girders tie the banks and the two river piers directly to
    # the underside of the slab. The piers stand from waterline to girder.
    for x in (left+5, right-5):
        parts.append(_rect(p, 'underdeck-girder', x-.35, x+.35, -1.05, -.4,
                           south, north, 'steel_dark'))
        for z in (water_south+4, water_north-4):
            parts.append(_rect(p, 'river-pier', x-.65, x+.65, -4, -1.05,
                               z-.7, z+.7, 'concrete_dark'))
    for z in (south+1, north-1):
        parts.append(_rect(p, 'bank-bearing', left+1, right-1, -1.3, -.4,
                           z-.45, z+.45, 'concrete_dark'))
    # Solid lower parapet with spaced upper steel bars: no missing segment at
    # midspan or at either bank. Kept inside the placement envelope.
    for x0, x1 in ((left, left+.5), (right-.5, right)):
        parts.append(_rect(p, 'bridge-parapet', x0, x1, 0, 1.5,
                           south, north, 'concrete_stained'))
        parts.append(_rect(p, 'rail-cap', x0, x1, 1.5, 1.65,
                           south, north, 'paint_yellow_faded'))
        for step in range(1, 9):
            z = south + (north-south)*step/9
            parts.append(_rect(p, 'parapet-rib', x0, x1, 0, 2.1,
                               z-.09, z+.09, 'steel_dark'))
    return Assembly('bridge', p.key, p.sector, p.origin, parts, {'placement_key': p.key})


def _bank(p, river, bridge, north):
    water0, water1 = _edges(river)[2:]
    x0, x1, _, _ = _edges(river)
    bridge0, bridge1, _, _ = _edges(bridge)
    z = water1 if north else water0
    # Shoreline stops at the bridge: no invisible wall across the crossing.
    banks = []
    for side, (a, b) in (('west', (x0, bridge0)), ('east', (bridge1, x1))):
        parts = [_rect(p, 'stepped-revetment', a, b, -4, 0,
                       z-.55, z+.55, 'concrete_dark'),
                 _rect(p, 'shore-coping', a, b, 0, .24,
                       z-.7, z+.7, 'concrete_stained')]
        key = p.key + ('-north' if north else '-south') + '-' + side
        banks.append(Assembly('riverbank', key, p.sector, p.origin, parts,
                              {'placement_key': key}))
    return banks


def _checkpoint(p):
    x0, x1, z0, z1 = _edges(p)
    # Both sidewalks and the entire roadway are open below the beam. Service
    # equipment sits on the side columns, not in the pedestrian route.
    parts = []
    for a, b in ((x0, x0+.6), (x1-.6, x1)):
        parts.append(_rect(p, 'gate-pier', a, b, 0, 4.6,
                           z0+.4, z1-.4, 'concrete_dark'))
        parts.append(_rect(p, 'scanner-housing', a, b, 2.65, 3.4,
                           z0+1, z1-1, 'steel_dark'))
        parts.append(_rect(p, 'signal', a, b, 3.5, 3.9,
                           z0+1, z1-1, 'paint_yellow_faded'))
    parts.append(_rect(p, 'gate-canopy', x0, x1, 4.6, 5.0,
                       z0, z1, 'corrugated_rust'))
    parts.append(_rect(p, 'gate-crossbeam', x0, x1, 4.15, 4.6,
                       z0+1, z0+1.45, 'steel_dark'))
    return Assembly('checkpoint', p.key, p.sector, p.origin, parts,
                    {'placement_key': p.key})


def _end(p):
    x0, x1, z0, z1 = _edges(p)
    parts = [_rect(p, 'end-barrier', x0, x1, 0, 1.8, z0, z1, 'concrete_dark'),
             _rect(p, 'end-marker', x0, x1, 1.8, 2, z0, z1, 'paint_yellow_faded')]
    return Assembly('boundary', p.key, p.sector, p.origin, parts,
                    {'placement_key': p.key})


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    if sector != 'road-river':
        raise ValueError(sector)
    placements = {p.key: p for p in layout.placements if p.sector == sector}
    west, road, east = (placements[key] for key in
                        ('west-sidewalk', 'roadway', 'east-sidewalk'))
    bridge, river = (placements[key] for key in ('bridge', 'river'))
    # Bank placement uses the water datum; its parts are absolute-local to it.
    return ([_pavement(p, bridge) for p in (west, road, east)] +
            [_river(river), _bridge(bridge, west, road, east, river),
             *_bank(river, river, bridge, False), *_bank(river, river, bridge, True),
             _checkpoint(placements['checkpoint'])] +
            [_end(placements[key]) for key in ('south-road-end', 'north-turnback')])
