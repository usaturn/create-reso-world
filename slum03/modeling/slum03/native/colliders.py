"""Simple boxes matching authored walkable slabs and separate bridge/gate parts.

Dimensions follow ground.py and road_river.py; not enclosing mesh AABBs over openings.
"""
from __future__ import annotations
from .common import node, yaw
from modeling.slum03.types import Layout, Report


def box(key: str, x0: float, x1: float, y0: float, y1: float,
        z0: float, z1: float, rotation_deg: float = 0.) -> dict:
    if not (x0 < x1 and y0 < y1 and z0 < z1):
        raise ValueError(f'invalid collider bounds: {key}')
    n = node(f'collider-{key}', f'{key} Collider',
             ((x0+x1)/2, (y0+y1)/2, (z0+z1)/2), yaw(rotation_deg))
    n['components'].append({'key': f'collider-{key}-box', 'type': 'FrooxEngine.BoxCollider',
                            'fields': {'Enabled': True, 'Type': 'Static',
                                       'CharacterCollider': True, 'Offset': [0., 0., 0.],
                                       'Size': [x1-x0, y1-y0, z1-z0]}})
    return n


def collider_slots(layout: Layout, reports: dict[str, Report]) -> list[dict]:
    unsupported = [item for item in layout.placements if item.params.get('detail_profile') == 'v2'
                   and item.kind not in ('ruin', 'shack', 'stall')]
    if unsupported:
        raise NotImplementedError(f'unsupported v2 collider kinds: '
                                  f'{[(item.key, item.kind) for item in unsupported]}')
    p = {item.key: item for item in layout.placements}
    floor = p['factory-floor']; ground = p['district-ground']
    fx0, fx1 = floor.origin[0]-floor.size[0]/2, floor.origin[0]+floor.size[0]/2
    fz0, fz1 = floor.origin[2]-floor.size[2]/2, floor.origin[2]+floor.size[2]/2
    gx0, gx1 = ground.origin[0]-ground.size[0]/2, ground.origin[0]+ground.size[0]/2
    gz0, gz1 = ground.origin[2]-ground.size[2]/2, ground.origin[2]+ground.size[2]/2
    if not (gx0 < fx0 < fx1 < gx1 and gz0 < fz0 < fz1 < gz1):
        raise ValueError('factory slab does not fit foundation')
    boxes = [box('district-ground-west', gx0, fx0, -.3, 0, gz0, gz1),
             box('district-ground-east', fx1, gx1, -.3, 0, gz0, gz1),
             box('district-ground-south', fx0, fx1, -.3, 0, gz0, fz0),
             box('district-ground-north', fx0, fx1, -.3, 0, fz1, gz1),
             box('factory-floor', fx0, fx1, -.2, 0, fz0, fz1)]
    # Road approaches stop at bridge ends; do not collide across the span twice.
    bridge = p['bridge']; b0 = bridge.origin[2]-bridge.size[2]/2; b1 = bridge.origin[2]+bridge.size[2]/2
    for name in ('west-sidewalk', 'roadway', 'east-sidewalk'):
        lane = p[name]; x, _, z = lane.origin; sx, sy, sz = lane.size
        lo, hi = z-sz/2, z+sz/2
        for side, z0, z1 in (('south', lo, b0), ('north', b1, hi)):
            boxes.append(box(f'{name}-{side}', x-sx/2, x+sx/2, -sy, 0, z0, z1))
    left, right = bridge.origin[0]-bridge.size[0]/2, bridge.origin[0]+bridge.size[0]/2
    boxes.append(box('bridge-deck', left, right, -.4, 0, b0, b1))
    for side, x0, x1 in (('west', left, left+.5), ('east', right-.5, right)):
        boxes.append(box(f'bridge-rail-{side}', x0, x1, 0, 1.65, b0, b1))
    # The pier is below the deck, never a block across the roadway.
    river = p['river']; water0, water1 = river.origin[2]-river.size[2]/2, river.origin[2]+river.size[2]/2
    for side, x in (('west', left+5), ('east', right-5)):
        for end, z in (('south', water0+4), ('north', water1-4)):
            boxes.append(box(f'bridge-pier-{side}-{end}', x-.65, x+.65, -4, -1.05, z-.7, z+.7))
    gate = p['checkpoint']; x, _, z = gate.origin; sx, _, sz = gate.size
    x0, x1, z0, z1 = x-sx/2, x+sx/2, z-sz/2, z+sz/2
    for side, a, b in (('west', x0, x0+.6), ('east', x1-.6, x1)):
        boxes.append(box(f'checkpoint-pier-{side}', a, b, 0, 4.6, z0+.4, z1-.4))
    boxes.append(box('checkpoint-canopy', x0, x1, 4.6, 5., z0, z1))
    boxes.append(box('checkpoint-crossbeam', x0, x1, 4.15, 4.6, z0+1, z0+1.45))
    # Task6 road_river._end: body 0..1.8 and marker 1.8..2.0 share
    # the full end-barrier footprint. Only ends, never the open checkpoint.
    for name in ('south-road-end', 'north-turnback'):
        end = p[name]; ex, ey, ez = end.origin; sx, _, sz = end.size
        boxes.append(box(name, ex-sx/2, ex+sx/2, ey, ey+2., ez-sz/2, ez+sz/2))
    # Roofless facade obstruction is limited to the actual north-wall location.
    wall = p['north-wall']
    boxes.append(box('north-wall', wall.origin[0]-wall.size[0]/2,
                     wall.origin[0]+wall.size[0]/2, 0, wall.size[1]*.85,
                     wall.origin[2]-wall.size[2]/2, wall.origin[2]+wall.size[2]/2))
    # Explicit enclosed exteriors; no background or walk-through stall enclosures.
    for name in ('ruin-west', 'ruin-west-annex', 'ruin-north', 'ruin-east',
                 'shack-row', 'shack-west', 'nightlife-east', 'nightlife-velvet', 'yarol'):
        item = p[name]
        if item.params.get('detail_profile') == 'v2':
            continue  # v2 shells use measured individual structural parts below.
        x, y, z = item.origin; sx, sy, sz = item.size
        # Approximate non-enterable volume; Yarol east doorway remains unblocked
        # outside the shell. Runtime walking/mesh fit remains pending.
        boxes.append(box(name, x-sx/2, x+sx/2, y, y+sy*.8, z-sz/2, z+sz/2, item.yaw_deg))
    # The supplied evaluated mesh reports bound actual exported objects, not
    # hypothetical full-placement boxes. Keep candidate boxes inside these
    # envelopes; physical surface fit still needs live walking verification.
    for sector, mesh, prefix in (('ground', 'district-foundation', 'district-ground-'),
                                 ('plaza', 'factory-floor', 'factory-floor'),
                                 ('road-river', 'bridge', 'bridge-'),
                                 ('road-river', 'checkpoint', 'checkpoint-'),
                                 ('road-river', 'south-road-end', 'south-road-end'),
                                 ('road-river', 'north-turnback', 'north-turnback')):
        report = reports.get(sector)
        if not report:
            continue
        bounds = report.get('evaluated_bounds', {}).get(mesh)
        if bounds is None:
            raise ValueError(f'missing evaluated bounds for {sector}/{mesh}')
        for candidate in boxes:
            key = candidate['slot']['key'].removeprefix('collider-')
            if not key.startswith(prefix):
                continue
            center = candidate['slot']['position']
            size = candidate['components'][0]['fields']['Size']
            for axis in range(3):
                if (center[axis]-size[axis]/2 < bounds['minimum'][axis]-.01 or
                        center[axis]+size[axis]/2 > bounds['maximum'][axis]+.01):
                    raise ValueError(f'{key} lies outside evaluated {sector}/{mesh} bounds')
    # Never enclose a walk-through v2 market canopy in one placement AABB.
    # Each collider belongs to a source-indexed part whose exported bounds were
    # checked in observe_detail; no visual stock or ungrounded background boxes.
    from modeling.slum03.density_metrics import layout_digest
    from modeling.slum03.evaluated_detail import v2_object_issues
    for item in layout.placements:
        if item.params.get('detail_profile') != 'v2' or item.kind not in ('ruin', 'shack', 'stall'):
            continue
        report = reports.get(item.sector)
        if not report or report.get('layout_sha256') != layout_digest(layout):
            raise ValueError(f'missing evaluated report for {item.key}')
        matches = [obj for obj in report.get('objects', [])
                   if obj.get('placement_key') == item.key and obj.get('mesh') in report.get('evaluated_bounds', {})]
        if len(matches) != 1 or not matches[0].get('detail_groups'):
            raise ValueError(f'missing evaluated geometry for {item.key}')
        errors = v2_object_issues(item, report, matches[0])
        if errors:
            raise ValueError(f'invalid evaluated report for {item.key}: {errors}')
        candidates = []
        for group in matches[0]['detail_groups']:
            if group['category'] not in ('architecture', 'shelf'):
                continue
            if len(group.get('part_bounds', [])) != len(group['part_indices']):
                raise ValueError(f'missing evaluated part bounds for {item.key}')
            for index, raw in zip(group['part_indices'], group['part_bounds']):
                lo, hi = raw['minimum'], raw['maximum']
                if lo[1] >= 2.1:  # canopy/roof and overhead fittings stay walk-through
                    continue
                if len(lo) != 3 or len(hi) != 3 or any(hi[i]-lo[i] <= 1e-5 for i in range(3)):
                    raise ValueError(f'invalid evaluated part collider for {item.key}')
                candidates.append((f'{item.key}-{group["id"]}-part-{index}', lo, hi))
        # An existing managed Slot/Component keeps its original keys on reapply.
        # Rebind that identity to one real structural part rather than keeping
        # its former enclosing volume (which would block the actual opening).
        legacy = {'ruin-west', 'ruin-west-annex', 'ruin-north', 'ruin-east',
                  'shack-row', 'shack-west'}
        anchor = next((i for i, (_, lo, hi) in enumerate(candidates)
                       if hi[1]-lo[1] >= 1 and lo[1] < 2.1), 0)
        if item.key in legacy and not candidates:
            raise ValueError(f'no evaluated structure for existing {item.key} collider')
        for i, (key, lo, hi) in enumerate(candidates):
            if item.key in legacy and i == anchor:
                key = item.key
            boxes.append(box(key, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    return boxes
