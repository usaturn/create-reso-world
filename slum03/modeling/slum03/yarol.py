"""East-facing Yarol exterior: sealed threshold, shallow warm windows, concrete mass."""
from math import radians
from .geometry import Assembly, box, mesh, rotate_y, tube
from .types import Layout


def _bar(p):
    w, h, d = p.size
    door = p.params['door_width']
    window = p.params['window_width']
    depth = p.params['reveal_depth']
    sign_y = p.params['sign_height']
    z = d/2-.5  # building-front in +Z before yaw=90: +X in world
    parts = []
    for x in (-w/2+.4, w/2-.4):
        parts.append(box('corner-pier', (x, h/2, z-.25), (.8, h, 1.0), 'concrete_dark'))
        parts.append(box('corner-pier', (x, h/2, -d/2+.5), (.8, h, 1.0), 'concrete_dark'))
        parts.append(box('side-wall', (x, h/2, 0), (.52, h, d-1.1), 'concrete_stained'))
    parts.append(box('rear-wall', (0, h/2, -d/2+.5), (w-.8, h, .85), 'concrete_dark'))
    parts.append(box('roof-slab', (0, h-.28, 0), (w, .56, d), 'concrete_raw'))
    parts.append(box('fascia', (0, sign_y+.65, z-.18), (w-.9, 2.1, .65), 'concrete_dark'))
    parts.append(box('sill', (0, .36, z-.12), (w-.9, .72, .55), 'concrete_raw'))
    # Solid infill between the sealed door, shallow lit windows and corner
    # piers. The reveal/glow stays uncovered; every remaining bay meets the
    # fascia and the upper infill, not a hollow room behind the sign.
    window_x = w*.32
    inner = window_x-window/2
    outer = window_x+window/2
    pier_inner = w/2-.8
    for side in (-1, 1):
        for start, end in ((door/2, inner), (outer, pier_inner)):
            parts.append(box('front-infill', (side*(start+end)/2, 1.8, z-.16),
                             (end-start+.04, 3.6, .32), 'concrete_stained'))
        parts.append(box('window-head', (side*window_x, 3.3, z-.16),
                         (window+.04, .6, .32), 'concrete_dark'))
    parts.append(box('door-head', (0, 3.1, z-.16),
                     (door+.04, 1.0, .32), 'concrete_raw'))
    parts.append(box('upper-front', (0, (5.7+h-.56)/2, z-.16),
                     (w-.85, h-.56-5.7, .32), 'concrete_stained'))
    # Closed wood/steel-faced entrance is a full barrier, not a doorway cut
    # through the shell; the lit reveal is a shallow stage behind glazing.
    parts.append(box('closed-entrance', (0, 1.3, z+.03), (door, 2.6, .16), 'pallet_wood'))
    parts.append(box('door-pull', (door*.32, 1.25, z+.16), (.07, .42, .13), 'steel_bare'))
    for x in (-w*.32, w*.32):
        parts.append(box('shallow-reveal', (x, 1.94, z-depth),
                         (window+.28, 2.65, .12), 'concrete_stained'))
        parts.append(box('window-glow', (x, 1.9, z-depth+.08),
                         (window, 2.2, .08), 'window_lit'))
        for edge in (-window/2, window/2):
            parts.append(box('window-frame', (x+edge, 1.9, z-.02), (.10, 2.45, .18), 'steel_dark'))
        parts.append(box('window-frame', (x, 3.12, z-.02), (window+.1, .10, .18), 'steel_dark'))
        parts.append(box('window-frame', (x, .68, z-.02), (window+.1, .10, .18), 'steel_dark'))
        # Near-glazing bars suggest depth without building an explorable room.
        parts.append(box('window-silhouette', (x+.4, 1.13, z-depth+.14), (.16, .64, .10), 'steel_dark'))
    for x in (-1.1, 1.1):
        parts.append(box('sign-bracket', (x, sign_y-.25, z+.12), (.13, .16, .70), 'steel_bare'))
    corners = [(-2.35, sign_y-.32, z+.42), (-2.35, sign_y+.8, z+.42),
               (2.35, sign_y+.8, z+.42), (2.35, sign_y-.32, z+.42)]
    corners.append(corners[0])
    for a, b in zip(corners, corners[1:]):
        parts.append(tube('sign-trim', [a, b], .035, 6, 'neon_orange'))
    # Origin remains the Placement foot; transform the actual meshes so the
    # Blender export and evaluated bounds face east without a hidden yaw.
    angle = radians(p.yaw_deg)
    turned = [mesh(part.name, [rotate_y(v, angle) for v in part.vertices],
                   part.faces, part.material) for part in parts]
    return Assembly('yarol', p.key, p.sector, p.origin, turned,
                    {'placement_key': p.key})


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    return [_bar(p) for p in layout.placements if p.sector == sector and p.kind == 'yarol']
