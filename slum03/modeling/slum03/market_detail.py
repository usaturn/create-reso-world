"""Compact stocked market stall; one owned mesh with real grouped substructure.

+Z is the open customer frontage before Placement yaw. All dimensions are in
metres; display positions and brace anchors follow shelf/span dimensions.
"""
from __future__ import annotations

import math

from .geometry import Assembly, MeshData, box, mesh, rotate_y, tube
from .merchandise import stock_items
from .types import Placement


def _awning(w: float, d: float, material: str) -> MeshData:
    """Thick folded tarpaulin, with outward-facing top, underside and edge faces."""
    x = w/2-.18
    z = d/2-.18
    vertices = [(vx, height, vz) for offset in (0., -.09)
                for vz in (-z, z)
                for vx, height in ((-x, 2.52+offset), (0., 2.72+offset),
                                   (x, 2.52+offset))]
    return mesh('folded-awning', vertices,
                ((0, 3, 4, 1), (1, 4, 5, 2),
                 (6, 7, 10, 9), (7, 8, 11, 10),
                 (0, 1, 7, 6), (1, 2, 8, 7),
                 (3, 9, 10, 4), (4, 10, 11, 5),
                 (0, 6, 9, 3), (2, 5, 11, 8)), material)


def detailed_stall(p: Placement, seed: int) -> Assembly:
    """Add two stocked shelves, load-bearing braces and local merchandise parts."""
    if p.params.get('variant') not in ('electronics', 'tools', 'prosthetics', 'reclaimed_equipment'):
        raise ValueError(f"unknown stall variant: {p.params.get('variant')}")
    w, _, d = p.size
    parts: list[MeshData] = []
    groups: list[dict] = []

    def add(category: str, identifier: str, *new_parts: MeshData) -> None:
        start = len(parts)
        parts.extend(new_parts)
        groups.append({'id': identifier, 'category': category,
                       'part_indices': list(range(start, len(parts)))})

    x0, x1 = -w/2+.24, w/2-.24
    z0, z1 = -d/2+.24, d/2-.24
    for x in (x0, x1):
        for z in (z0, z1):
            add('architecture', f'post-{x:.2f}-{z:.2f}',
                tube('post', [(x, .05, z), (x, 2.51, z)], .048, 8, 'steel_dark'))
        add('architecture', f'roof-stringer-{x:.2f}',
            tube('roof-stringer', [(x, 2.47, z0), (x, 2.47, z1)],
                 .043, 8, 'steel_bare'))
    for z in (z0, z1):
        add('architecture', f'roof-crossbar-{z:.2f}',
            tube('roof-crossbar', [(x0, 2.47, z), (x1, 2.47, z)],
                 .043, 8, 'steel_dark'))
    add('architecture', 'folded-roof', _awning(w, d,
        'tarp_blue' if p.params['variant'] in ('electronics', 'prosthetics') else 'tarp_orange'))
    # Tie-down eyelets carry the edges of the fabric into the corner posts.
    for x in (x0, x1):
        for z in (z0, z1):
            add('utility', f'roof-tie-{x:.2f}-{z:.2f}',
                box('eyelet', (x, 2.48, z), (.085, .07, .085), 'steel_bare'),
                tube('tarp-tie', [(x, 2.48, z), (x, 2.42, z)], .019, 6, 'rubber'))
    # The display sits against the back of the frame. Nothing blocks +Z frontage.
    shelf_z = -d/2+.82
    shelf_depth = .8
    rear_z = -d/2+.48
    for x in (x0, x1):
        add('architecture', f'shelf-upright-{x:.2f}',
            tube('shelf-upright', [(x, .04, rear_z), (x, 2.45, rear_z)],
                 .045, 8, 'steel_dark'))
    for row, top in enumerate((.99, 1.72)):
        add('shelf', f'display-{row}',
            box('shelf', (0, top-.05, shelf_z), (w-.6, .1, shelf_depth), 'pallet_wood'),
            box('shelf-lip', (0, top-.025, shelf_z+shelf_depth/2-.025),
                (w-.6, .05, .05), 'steel_dark'))
        for x in (x0, x1):
            add('architecture', f'shelf-brace-{row}-{x:.2f}',
                tube('shelf-brace', [(x, top-.06, shelf_z+.31),
                                     (x, top-.43, rear_z)], .034, 6, 'rust_dark'),
                box('brace-bolt', (x, top-.43, rear_z), (.09, .08, .09), 'steel_bare'))
    add('lived_in', 'under-counter-storage',
        box('storage-floor', (0, .085, shelf_z), (w-.7, .17, .66), 'pallet_wood'),
        box('storage-bin', (0, .36, shelf_z), (min(.72, w-.8), .38, .51), 'plastic_crate'),
        box('storage-handle', (0, .46, shelf_z+.27), (.23, .045, .05), 'steel_bare'))
    for item in stock_items(p, seed):
        # Item vertices are authored at item-local zero. Translate to the stall
        # shelf origin BEFORE applying yaw to the complete assembled stall.
        start = len(parts)
        parts.extend(mesh(part.name,
                          [(v[0]+item.origin[0], v[1]+item.origin[1], v[2]+item.origin[2])
                           for v in part.vertices], part.faces, part.material)
                     for part in item.parts)
        groups.append({'id': item.name, 'category': 'merchandise',
                       'part_indices': list(range(start, len(parts)))})
    angle = math.radians(p.yaw_deg)
    rotated = [mesh(part.name, [rotate_y(v, angle) for v in part.vertices],
                    part.faces, part.material) for part in parts]
    return Assembly('stall', p.key, p.sector, p.origin, rotated,
                    {'placement_key': p.key, 'variant': p.params['variant'],
                     'detail_groups': groups})
