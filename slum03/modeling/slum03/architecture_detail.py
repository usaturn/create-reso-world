"""Bounded, pose-aware near-field structural kits (one Assembly per owned building).

Foot datum is the Placement origin; +Z is the street face before yaw. Parts
remain individually inspectable here but the exporter merges each Assembly.
"""
from __future__ import annotations

import hashlib
import math

from .geometry import Assembly, MeshData, box, mesh, rotate_y, tube, wall_with_openings
from .types import Placement


class _Kit:
    def __init__(self, p: Placement):
        self.p = p
        self.parts: list[MeshData] = []
        self.groups: list[dict] = []

    def add(self, category: str, identifier: str, *parts: MeshData) -> None:
        start = len(self.parts)
        self.parts.extend(parts)
        self.groups.append({'id': identifier, 'category': category,
                            'part_indices': list(range(start, len(self.parts)))})

    def finish(self) -> Assembly:
        angle = math.radians(self.p.yaw_deg)
        turned = [mesh(part.name, [rotate_y(v, angle) for v in part.vertices],
                       part.faces, part.material) for part in self.parts]
        return Assembly(self.p.kind, self.p.key, self.p.sector, self.p.origin, turned,
                        {'placement_key': self.p.key, 'variant': self.p.params['variant'],
                         'detail_groups': self.groups})


def _variation(seed: int, key: str, channel: str) -> float:
    """Stable for each owner and channel, regardless of build iteration order."""
    digest = hashlib.sha256(f'{seed}:{key}:{channel}'.encode('utf-8')).digest()
    return int.from_bytes(digest[:8], 'big') / (2**64 - 1)


def _translated(part: MeshData, name: str, dx=0., dy=0., dz=0.) -> MeshData:
    return mesh(name, [(x+dx, y+dy, z+dz) for x, y, z in part.vertices],
                part.faces, part.material)


def _notched_slab(w: float, d: float, y: float) -> MeshData:
    """Missing street corner: exposed full-depth chipped edge, not surface paint."""
    x, z = w/2-.65, d/2-.65
    outline = [(-x, -z), (x, -z), (x, z-2), (x-.7, z-2.3),
               (x-2.4, z-2.3), (x-2.8, z-.25), (-x, z-.25)]
    n = len(outline)
    vertices = [(a, y+height, b) for height in (0., .4) for a, b in outline]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2*n))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    return mesh('sheared-corner-slab', vertices, faces, 'concrete_stained')


def detailed_ruin(p: Placement, seed: int) -> Assembly:
    """Six distinguishable load paths with shallow closed recesses, never walkable floors."""
    variant = p.params['variant']
    if variant not in ('slab_bay', 'broken_corner', 'service_core', 'stepped_shell',
                       'exposed_frame', 'patched_facade'):
        raise ValueError(f'unknown ruin variant: {variant}')
    w, h, d = p.size
    kit = _Kit(p)
    front = d/2-.85
    opening = wall_with_openings('recessed-window', w-1.3, h-.8, .65,
                                 [(-.95, 2.3, .95, 3.65)], .45, 1.2,
                                 'concrete_stained')
    kit.add('architecture', 'street-window', _translated(opening, 'recessed-window', dz=front),
            box('front-spandrel', (0, 4.05, front+.33), (2.15, .23, .17), 'concrete_dark'))
    for x in (-w/2+.55, w/2-.55):
        for z in (-d/2+.55, d/2-.55):
            kit.add('architecture', f'pier-{x:.2f}-{z:.2f}',
                    box('structural-pier', (x, (h-.7)/2, z), (.62, h-.7, .62), 'concrete_raw'))
    kit.add('architecture', 'rear-tie',
            box('rear-beam', (0, h-.85, -d/2+.6), (w-1., .42, .5), 'concrete_dark'))
    if variant == 'slab_bay':
        kit.add('architecture', 'projected-bay',
                box('projecting-slab', (0, h*.49, .35), (w-1., .48, d-1.05), 'concrete_raw'),
                box('under-slab-beam', (0, h*.49-.32, d/2-.7), (w-1.1, .27, .34), 'concrete_dark'))
    elif variant == 'broken_corner':
        kit.add('architecture', 'collapsed-corner', _notched_slab(w, d, h-.9),
                tube('exposed-rebar', [(w/2-1.3, h-.6, d/2-2.6),
                                      (w/2-1.2, h-.21, d/2-2.4)], .045, 6, 'rust_dark'))
    elif variant == 'service_core':
        # A projecting side shaft and its pipe risers are bolted to the main wall.
        x = w/2-.95
        kit.add('architecture', 'side-shaft',
                box('external-service-core', (x, (h-.7)/2, -d*.30),
                    (1.2, h-.7, d*.33), 'concrete_dark'),
                box('shaft-footing', (x, .18, -d*.30), (1.35, .36, d*.36), 'concrete_raw'))
        kit.add('utility', 'shaft-riser',
                tube('shaft-pipe', [(x+.34, .45, -d*.30), (x+.34, h-.9, -d*.30)], .075, 8, 'rust'))
    elif variant == 'stepped_shell':
        kit.add('architecture', 'setbacks',
                box('setback-slab', (-.45, h*.52, -.55), (w-1.9, .43, d-2.3), 'concrete_raw'),
                box('setback-slab', (-1., h-.9, -1.1), (w-3., .44, d-3.2), 'concrete_stained'),
                box('setback-return', (w/2-1.6, h*.77, -1.1), (.32, h*.43, d-3.2), 'concrete_dark'))
    elif variant == 'exposed_frame':
        kit.add('architecture', 'open-bays',
                box('open-frame-girder', (0, h*.55, -.3), (w-1., .39, d-1.4), 'steel_dark'),
                box('open-frame-girder', (0, h-.95, -.3), (w-1., .39, d-1.4), 'steel_bare'),
                tube('diagonal-brace', [(-w/2+.6, 1.1, -d/2+.6),
                                        (-w/2+.6, h*.55, d/2-.6)], .08, 8, 'rust_dark'))
    else:  # patched_facade
        kit.add('architecture', 'riveted-skin',
                box('bolted-patch', (-w*.27, h*.58, front+.39),
                    (w*.28, h*.22, .12), 'corrugated_rust'),
                box('bolted-patch', (w*.27, h*.66, front+.4),
                    (w*.28, h*.31, .12), 'corrugated'),
                box('patch-rail', (0, h*.44, front+.38), (w*.74, .16, .19), 'steel_dark'),
                box('patch-fastener', (-w*.27, h*.58, front+.37), (.12, .12, .24), 'steel_bare'),
                box('patch-fastener', (w*.27, h*.66, front+.37), (.12, .12, .24), 'steel_bare'))
    # Shared fixed wall service and a deliberate repair/work cluster under it.
    x = w/2-1.12
    kit.add('utility', 'wall-service-bracket',
            box('joint-anchor', (x, 2.1, front+.37), (.25, .22, .26), 'steel_dark'),
            box('meter-case', (x, 1.78, front+.34), (.56, .57, .22), 'paint_yellow_faded'),
            tube('service-conduit', [(x, 1.55, front+.38),
                                     (x, .38, front+.38)], .045, 6, 'steel_bare'))
    shift = (_variation(seed, p.key, 'repair')-.5)*.27
    kit.add('lived_in', 'wall-repair',
            box('work-crate', (-w/2+1.2+shift, .32, -d/2+1.05),
                (.8, .64, .72), 'pallet_wood'),
            box('tool-on-crate', (-w/2+1.2+shift, .67, -d/2+1.05),
                (.47, .06, .14), 'steel_bare'))
    return kit.finish()


def _folded_sheet(w: float, h: float, d: float) -> MeshData:
    # Reuse the existing genuinely folded sheet and its continuous eave fall.
    from .shacks import _roof
    original = _roof(w, h, d)
    return mesh('folded-sheet', original.vertices, original.faces, original.material)


def _strip(name: str, x0: float, x1: float, h: float, d: float, material: str) -> MeshData:
    """Watertight pitched sheet / board with thickness and two supported ends."""
    z0, z1 = -d/2+.32, d/2-.32
    back, fore = h-.48, h-1.06
    vertices = [(x, y, z) for y, z in ((back,z0), (fore,z1),
                                         (back-.07,z0), (fore-.07,z1)) for x in (x0,x1)]
    return mesh(name, vertices, ((0,1,3,2), (4,6,7,5), (0,4,5,1),
                                  (2,3,7,6), (0,2,6,4), (1,5,7,3)), material)


def detailed_shack(p: Placement, seed: int) -> Assembly:
    """Four roof/wall construction systems, each with a usable-looking open door."""
    variant = p.params['variant']
    if variant not in ('corrugated', 'plywood', 'tarp', 'pallet'):
        raise ValueError(f'unknown shack variant: {variant}')
    w, h, d = p.size
    kit = _Kit(p)
    front = d/2-.43
    kit.add('architecture', 'raised-floor',
            box('floor-boards', (0, .14, 0), (w-.5, .28, d-.55), 'pallet_wood'))
    for x in (-w/2+.37, w/2-.37):
        for z in (-d/2+.38, d/2-.38):
            if variant == 'corrugated':
                from .shacks import _eave_height, _fold_height
                top = _eave_height(h, d, z) + _fold_height(w, x) - .075
            elif variant == 'tarp':
                top = h-1.17 if z < 0 else h-1.35
            else:
                top = h-.55 - (z+d/2-.32)/(d-.64)*.58
            kit.add('architecture', f'corner-post-{x:.2f}-{z:.2f}',
                    box('support-post', (x, top/2, z), (.2, top, .2), 'pallet_wood'))
    kit.add('architecture', 'wall-envelope',
            box('rear-cladding', (0, (h-1.3)/2, -d/2+.43),
                (w-.8, h-1.3, .1), 'plywood'),
            box('left-cladding', (-w/2+.42, (h-1.35)/2, 0),
                (.1, h-1.35, d-.9), 'corrugated' if variant == 'corrugated' else 'plywood'),
            box('right-cladding', (w/2-.42, (h-1.35)/2, 0),
                (.1, h-1.35, d-.9), 'plywood'),
            box('door-jamb', (-1., 1.12, front), (.16, 2.24, .16), 'pallet_wood'),
            box('door-jamb', (1., 1.12, front), (.16, 2.24, .16), 'pallet_wood'),
            box('door-header', (0, 2.28, front), (2.13, .17, .2), 'pallet_wood'),
            box('front-cladding', (-w/4-.5, 1.12, front), (w/2-1.1, 2.24, .1), 'corrugated'),
            box('front-cladding', (w/4+.5, 1.12, front), (w/2-1.1, 2.24, .1), 'plywood'))
    if variant == 'corrugated':
        kit.add('architecture', 'folded-roof', _folded_sheet(w, h, d),
                box('roof-rail', (0, h-1.24, front-.08), (w-.7, .16, .19), 'steel_dark'))
    elif variant == 'plywood':
        boards = [_strip('staggered-board-roof', -w/2+.32+i*(w-.64)/5+.018,
                         -w/2+.32+(i+1)*(w-.64)/5+.03, h-.04*(i%2), d, 'plywood')
                  for i in range(5)]
        kit.add('architecture', 'overlapped-boards', *boards)
    elif variant == 'tarp':
        half = w/2-.3
        z0, z1 = -d/2+.32, d/2-.32
        vertices = [(-half,h-1.12,z0), (0,h-.25,z0), (half,h-1.12,z0),
                    (-half,h-1.3,z1), (0,h-.83,z1), (half,h-1.3,z1),
                    (-half,h-1.17,z0), (0,h-.32,z0), (half,h-1.17,z0),
                    (-half,h-1.35,z1), (0,h-.90,z1), (half,h-1.35,z1)]
        canopy = mesh('tensioned-canopy', vertices,
                      ((0,3,4,1), (1,4,5,2), (6,7,10,9), (7,8,11,10),
                       (0,1,7,6), (1,2,8,7), (3,9,10,4), (4,10,11,5),
                       (0,6,9,3), (2,5,11,8)), 'tarp_blue')
        kit.add('architecture', 'ridge-and-ties', canopy,
                tube('ridge-rope', [(0,h-.3,z0), (0,h-.86,z1)], .045, 6, 'rust_dark'),
                tube('tarp-tie', [(-half,h-1.25,z1), (-w/2+.37,h-1.18,z1)], .035, 6, 'rubber'))
    else:
        kit.add('architecture', 'pallet-rafters',
                *[_strip('spaced-pallet-roof', -w/2+.32+i*(w-.64)/6,
                         -w/2+.32+i*(w-.64)/6+(w-.64)/6*.82, h, d, 'pallet_wood')
                  for i in range(6)],
                box('pallet-crossbar', (0, h-.65, -d/2+.5), (w-.7, .19, .18), 'steel_dark'))
    kit.add('utility', 'vent-and-rainwater',
            box('vent-grille', (-w*.2, h-1.8, -d/2+.5), (.54, .17, .1), 'steel_dark'),
            tube('drip-gutter', [(-w/2+.37,h-1.17, d/2-.35),
                                  (w/2-.37,h-1.17,d/2-.35)], .055, 6, 'rust_dark'),
            tube('downspout', [(w/2-.37,h-1.17,d/2-.35),
                                (w/2-.37,.25,d/2-.35)], .05, 6, 'steel_dark'))
    offset = (_variation(seed, p.key, 'basin')-.5)*.18
    x, z = -w/2+.94+offset, -d/2+1.02
    kit.add('lived_in', 'washing-station',
            box('basin-stand', (x,.39,z), (.65,.78,.64), 'pallet_wood'),
            box('wash-basin', (x,.81,z), (.79,.09,.75), 'steel_bare'),
            box('basin-rim', (x,.88,z-.34), (.79,.12,.07), 'steel_dark'),
            box('basin-rim', (x,.88,z+.34), (.79,.12,.07), 'steel_dark'),
            box('basin-rim', (x-.35,.88,z), (.07,.12,.61), 'steel_dark'),
            box('basin-rim', (x+.35,.88,z), (.07,.12,.61), 'steel_dark'))
    return kit.finish()
