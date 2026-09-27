"""Two separately editable, closed neon-lane shopfronts (non-explicit exterior only)."""
from .geometry import Assembly, box, tube
from .types import Layout


def _front(p):
    w, h, d = p.size
    shutter = p.params['shutter_width']
    sign_y = p.params['sign_height']
    front_z = d/2-.7
    parts = []
    # Load-bearing piers, recessed shutter and a beam running back to the
    # service wall. No doorway or explorable interior is included.
    for x in (-w/2+.3, w/2-.3):
        parts.append(box('pier', (x, h/2, front_z-.15), (.5, h, .65), 'concrete_dark'))
        parts.append(box('pier', (x, h/2, -d/2+.5), (.5, h, .7), 'concrete_stained'))
        parts.append(box('side-beam', (x, h-.4, 0), (.45, .55, d-1.2), 'concrete_raw'))
    parts.append(box('back-wall', (0, h/2, -d/2+.5), (w-.5, h, .65), 'concrete_dark'))
    parts.append(box('upper-cladding', (0, (h+4.2)/2, front_z-.25),
                     (w-.85, h-4.2, .4), 'concrete_stained'))
    for y in (5.8, 8.2):
        parts.append(box('pour-joint', (0, y, front_z-.035),
                         (w-.9, .045, .025), 'concrete_dark'))
    parts.append(box('lintel', (0, sign_y-.38, front_z-.13), (w-.55, .55, .52), 'concrete_raw'))
    for x in (-shutter/2, shutter/2):
        parts.append(box('shutter-guide', (x, 1.33, front_z+.08), (.13, 2.66, .16), 'rust_dark'))
    for i in range(12):
        parts.append(box('shutter-slat', (0, .12+i*.22, front_z+.02),
                         (shutter, .20, .09), 'corrugated' if i % 3 else 'corrugated_rust'))
    # Brackets bolt to the lintel and carry the restrained tube outline.
    for x in (-w*.31, w*.31):
        parts.append(box('sign-mount', (x, sign_y-.28, front_z+.19), (.16, .26, .85), 'steel_dark'))
    color = 'neon_magenta' if p.params['storefront_name'] == 'LANTERN' else 'neon_pink'
    corners = [(-w*.38, sign_y-.15, front_z+.59),
               (-w*.38, sign_y+.57, front_z+.59),
               (w*.38, sign_y+.57, front_z+.59),
               (w*.38, sign_y-.15, front_z+.59)]
    corners.append(corners[0])
    for a, b in zip(corners, corners[1:]):
        parts.append(tube('neon-tube', [a, b], .035, 6, color))
    # Weathered splash guards and a small service vent above the shutters.
    parts.append(box('splash-guard', (0, .18, front_z-.25), (w-.8, .36, .16), 'rust_dark'))
    parts.append(box('service-vent', (0, h-1.2, front_z+.18), (.95, .3, .07), 'steel_dark'))
    return Assembly('nightlife', p.key, p.sector, p.origin, parts, {'placement_key': p.key})


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    return [_front(p) for p in layout.placements if p.sector == sector and p.kind == 'nightlife']
