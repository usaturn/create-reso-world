"""Two separately editable, closed neon-lane shopfronts (non-explicit exterior only)."""
from .geometry import Assembly, box, mesh, tube
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
        parts.append(box('side-wall', (x, h/2, 0), (.35, h, d-1.1), 'concrete_stained'))
    parts.append(box('back-wall', (0, h/2, -d/2+.5), (w-.5, h, .65), 'concrete_dark'))
    parts.append(box('roof-slab', (0, h-.23, 0), (w-.3, .46, d-1.1), 'concrete_raw'))
    parts.append(box('upper-cladding', (0, (h+4.2)/2, front_z-.25),
                     (w-.85, h-4.2, .4), 'concrete_stained'))
    for y in (5.8, 8.2):
        parts.append(box('pour-joint', (0, y, front_z-.035),
                         (w-.9, .045, .025), 'concrete_dark'))
    parts.append(box('lintel', (0, sign_y-.38, front_z-.13), (w-.55, .55, .52), 'concrete_raw'))
    parts.append(box('sign-fascia', (0, (3.35+4.2)/2, front_z-.25),
                     (w-.55, 4.2-3.35, .4), 'concrete_dark'))
    gap_start = shutter/2
    pier_inside = w/2-.55
    for side in (-1, 1):
        parts.append(box('front-jamb', (side*(gap_start+pier_inside)/2, 1.8, front_z-.22),
                         (pier_inside-gap_start+.08, 3.6, .44), 'concrete_stained'))
    parts.append(box('shutter-backing', (0, 1.46, front_z-.16),
                     (shutter+.05, 2.92, .18), 'steel_dark'))
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


# Four storefront systems (non-explicit exterior only). Each differs in its
# entrance, canopy, signage, frontage lighting and wall equipment, not colour.
NIGHTLIFE_VARIANTS = ('nightlife-1', 'nightlife-2', 'nightlife-3', 'nightlife-4')
_NEON = {'nightlife-1': 'neon_magenta', 'nightlife-2': 'neon_red',
         'nightlife-3': 'neon_pink', 'nightlife-4': 'neon_magenta'}


def _sloped(name, x0, x1, y0, z0, y1, z1, thickness, material):
    """Closed thick plank from a wall line (y0, z0) down to a free edge (y1, z1)."""
    vertices = [(x, y - t, z) for t in (0., thickness) for y, z in ((y0, z0), (y1, z1))
                for x in (x0, x1)]
    faces = ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))
    return mesh(name, vertices, faces, material)


def _shell(kit, w, h, d, front, sign_y, opening):
    """Closed load-bearing shell with the legacy sign band geometry and label clearance."""
    piers = []
    for x in (-w/2+.3, w/2-.3):
        piers += [box('pier', (x, h/2, front-.15), (.5, h, .65), 'concrete_dark'),
                  box('pier', (x, h/2, -d/2+.5), (.5, h, .7), 'concrete_stained')]
    kit.add('architecture', 'piers', *piers)
    walls = [box('back-wall', (0, h/2, -d/2+.5), (w-.5, h, .65), 'concrete_dark')]
    for x in (-w/2+.3, w/2-.3):
        walls += [box('side-wall', (x, h/2, 0), (.35, h, d-1.1), 'concrete_stained'),
                  box('side-beam', (x, h-.4, 0), (.45, .55, d-1.2), 'concrete_raw')]
    kit.add('architecture', 'shell', *walls)
    kit.add('architecture', 'roof', box('roof-slab', (0, h-.23, 0), (w-.3, .46, d-1.1), 'concrete_raw'))
    upper = [box('upper-cladding', (0, (h+4.2)/2, front-.25), (w-.85, h-4.2, .4), 'concrete_stained')]
    upper += [box('pour-joint', (0, y, front-.035), (w-.9, .045, .025), 'concrete_dark')
              for y in (5.8, 8.2) if y < h-.6]
    kit.add('architecture', 'upper-facade', *upper)
    band = [box('lintel', (0, sign_y-.38, front-.13), (w-.55, .55, .52), 'concrete_raw'),
            box('sign-fascia', (0, (3.35+4.2)/2, front-.25), (w-.55, .85, .4), 'concrete_dark')]
    pier_inside = w/2-.55
    for side in (-1, 1):
        band.append(box('front-jamb', (side*(opening/2+pier_inside)/2, 1.8, front-.22),
                        (pier_inside-opening/2+.08, 3.6, .44), 'concrete_stained'))
    kit.add('architecture', 'sign-band', *band)


def _entrance(variant, opening, front):
    if variant == 'nightlife-1':  # roll shutter bar
        parts = [box('shutter-backing', (0, 1.46, front-.16), (opening+.05, 2.92, .18), 'steel_dark')]
        parts += [box('shutter-guide', (x, 1.33, front+.08), (.13, 2.66, .16), 'rust_dark')
                  for x in (-opening/2, opening/2)]
        parts += [box('shutter-slat', (0, .12+i*.22, front+.02), (opening, .20, .09),
                      'corrugated' if i % 3 else 'corrugated_rust') for i in range(12)]
        parts.append(box('splash-guard', (0, .18, front-.29), (opening, .36, .08), 'rust_dark'))
        return parts
    if variant == 'nightlife-2':  # glazed noodle counter window
        parts = [box('counter-base', (0, .5, front-.1), (opening, 1.0, .3), 'concrete_stained'),
                 box('counter-top', (0, 1.04, front+.12), (opening+.1, .08, .6), 'steel_bare'),
                 box('service-glass', (0, 1.93, front-.2), (opening, 1.76, .05), 'glass_dark'),
                 box('window-transom', (0, 2.82, front-.2), (opening, .1, .12), 'steel_dark')]
        parts += [box('mullion', (x, 1.93, front-.17), (.06, 1.76, .08), 'steel_dark')
                  for x in (-opening/4, 0., opening/4)]
        return parts
    if variant == 'nightlife-3':  # glazed arcade doors in a steel frame
        inner = opening - .2
        return [box('door-glass', (0, 1.4, front-.18), (inner, 2.7, .04), 'glass_dark'),
                box('door-frame-head', (0, 2.8, front-.18), (opening, .1, .1), 'steel_dark'),
                *[box('door-frame-side', (x, 1.4, front-.18), (.1, 2.8, .1), 'steel_dark')
                  for x in (-(opening/2-.05), opening/2-.05)],
                box('door-meeting-stile', (0, 1.4, front-.15), (.08, 2.7, .08), 'steel_dark'),
                box('push-rail', (0, 1.1, front-.12), (inner, .06, .06), 'steel_bare'),
                box('kick-plate', (0, .15, front-.15), (inner, .3, .06), 'steel_dark')]
    # nightlife-4: recessed lounge door beside a ribbed screen
    parts = [box('recess-wall', (0, 1.45, front-.45), (opening, 2.9, .12), 'concrete_dark'),
             box('door-leaf', (-.45, 1.1, front-.36), (1.0, 2.2, .06), 'steel_dark'),
             box('door-handle', (-.1, 1.05, front-.31), (.04, .25, .05), 'steel_bare')]
    parts += [box('screen-rib', (.3+i*.24, 1.3, front-.35), (.08, 2.4, .08), 'pallet_wood')
              for i in range(int((opening/2-.4)/.24))]
    return parts


def _canopy(variant, width, front):
    edge = front + .62
    if variant == 'nightlife-1':  # flat steel deck on knee braces
        return [box('canopy-deck', (0, 3.02, front+.31), (width, .08, .62), 'steel_dark'),
                *[tube('canopy-knee', [(x, 2.45, front+.01), (x, 2.98, front+.5)], .03, 6, 'steel_bare')
                  for x in (-(width/2-.08), width/2-.08)]]
    if variant == 'nightlife-2':  # sloped cloth awning with split noren
        parts = [box('awning-rail', (0, 3.0, front+.06), (width, .08, .16), 'steel_dark'),
                 _sloped('cloth-awning', -width/2, width/2, 3.06, front+.02, 2.72, edge, .03, 'cloth_red')]
        count = max(3, int(width/.55))
        pitch = width/count
        parts += [box('noren', (-width/2+(i+.5)*pitch, 2.47, edge-.02), (pitch-.06, .5, .02), 'cloth_red')
                  for i in range(count)]
        return parts
    if variant == 'nightlife-3':  # boxed marquee
        return [box('marquee', (0, 3.0, front+.3), (width, .2, .6), 'steel_dark'),
                box('marquee-soffit', (0, 2.88, front+.33), (width-.1, .04, .5), 'concrete_dark')]
    # nightlife-4: deep pitched fabric canopy with side cheeks
    return [_sloped('fabric-canopy', -width/2, width/2, 3.1, front+.02, 2.62, edge, .04, 'tarp_green'),
            *[box('canopy-cheek', (x, 2.84, front+.32), (.05, .4, .58), 'steel_dark')
              for x in (-width/2+.03, width/2-.03)]]


def _signage(variant, w, sign_y, front, opening, neon):
    if variant == 'nightlife-1':  # neon outline on two lintel mounts (legacy look)
        parts = [box('sign-mount', (x, sign_y-.28, front+.19), (.16, .26, .85), 'steel_dark')
                 for x in (-w*.31, w*.31)]
        corners = [(-w*.38, sign_y-.15, front+.59), (-w*.38, sign_y+.57, front+.59),
                   (w*.38, sign_y+.57, front+.59), (w*.38, sign_y-.15, front+.59)]
        corners.append(corners[0])
        parts += [tube('neon-tube', [a, b], .035, 6, neon) for a, b in zip(corners, corners[1:])]
        return parts
    jamb_x = (opening/2 + w/2 - .55)/2
    if variant == 'nightlife-2':  # menu board on the jamb and a blade on the right pier
        return [box('menu-board', (-jamb_x, 1.7, front+.03), (.6, .9, .06), 'plywood'),
                box('blade-bracket', (w/2-.55, 5.9, front+.1), (.1, .1, .2), 'steel_dark'),
                box('blade-sign', (w/2-.55, 5.2, front+.4), (.12, 1.6, .6), 'paint_yellow_faded'),
                tube('neon-tube', [(w/2-.55, 4.38, front+.66), (w/2-.55, 6.02, front+.66)], .03, 6, neon)]
    if variant == 'nightlife-3':  # tall blade sign on the left pier
        return [box('blade-bracket', (-w/2+.55, 6.3, front+.1), (.1, .1, .2), 'steel_dark'),
                box('blade-sign', (-w/2+.55, 5.4, front+.4), (.12, 2.0, .6), 'steel_dark'),
                *[tube('neon-tube', [(-w/2+.55, 4.4, z), (-w/2+.55, 6.4, z)], .03, 6, neon)
                  for z in (front+.21, front+.66)]]
    return [box('lightbox', (0, 3.75, front+.05), (1.4, .5, .12), 'window_lit'),
            tube('neon-tube', [(-.7, 3.47, front+.12), (.7, 3.47, front+.12)], .03, 6, neon)]


def _lighting(variant, w, width, front, neon):
    if variant == 'nightlife-1':  # warm sconces on both jambs
        parts = []
        for x in (-(w/2-.8), w/2-.8):
            parts += [box('sconce-arm', (x, 2.4, front+.12), (.06, .06, .24), 'steel_dark'),
                      box('sconce-lamp', (x, 2.35, front+.27), (.14, .14, .14), 'warm_bulb')]
        return parts
    if variant == 'nightlife-2':  # paper lanterns hung from the cloth awning underside
        parts = []
        for x in (-width*.35, width*.35):
            parts += [tube('lantern-cord', [(x, 2.89, front+.3), (x, 2.62, front+.3)], .01, 6, 'rubber'),
                      box('paper-lantern', (x, 2.44, front+.3), (.28, .36, .28), 'warm_bulb')]
        return parts
    if variant == 'nightlife-3':  # bulb row under the marquee edge
        count = max(5, int(width/.45))
        return [box('marquee-bulb', (-width/2+.2+i*(width-.4)/(count-1), 2.87, front+.55),
                    (.07, .06, .07), 'warm_bulb') for i in range(count)]
    parts = []
    for x in (-(w/2-.3), w/2-.3):  # vertical neon strips clipped to the piers
        parts += [tube('neon-strip', [(x, .6, front+.2), (x, 2.6, front+.2)], .03, 6, neon),
                  box('strip-clip', (x, 1.6, front+.19), (.1, .05, .06), 'steel_dark')]
    return parts


def _clutter(variant, w, front, seed, key):
    from .density_model import stable_seed
    shift = (stable_seed(seed, key, 'street-clutter')/(2**256-1) - .5)*.2
    z = front + .33
    parts = [tube('trash-bin', [(w/2-.85, .02, z), (w/2-.85, .8, z)], .22, 10, 'steel_dark')]
    if variant == 'nightlife-1':
        parts += [box('crate-stack', (-w/2+1.6+shift, .3, z), (.5, .6, .4), 'plastic_crate'),
                  box('crate-stack', (-w/2+1.65+shift, .82, z), (.46, .44, .38), 'plastic_crate')]
    elif variant == 'nightlife-2':
        for x in (-.6+shift, .6+shift):
            parts += [box('stool-legs', (x, .34, front+.5), (.24, .68, .24), 'steel_dark'),
                      box('stool-seat', (x, .7, front+.5), (.34, .05, .34), 'cloth_red')]
    elif variant == 'nightlife-3':
        parts += [box('delivery-box', (-w/2+1.65+shift, .22, z), (.55, .44, .42), 'plywood'),
                  box('delivery-box', (-w/2+1.6+shift, .6, z), (.4, .32, .34), 'plywood')]
    else:
        parts += [box('bench-seat', (-w/2+1.75+shift, .45, z), (1.1, .06, .36), 'pallet_wood'),
                  *[box('bench-leg', (-w/2+1.75+shift+x, .21, z), (.06, .42, .3), 'steel_dark')
                    for x in (-.45, .45)]]
    return parts


def detailed_nightlife(p, seed: int) -> Assembly:
    """Closed v2 storefront: shell, entrance, canopy, signage, lighting, equipment, clutter."""
    from .architecture_detail import _Kit
    from .utilities import utility_parts
    variant = p.params.get('variant')
    if variant not in NIGHTLIFE_VARIANTS:
        raise ValueError(f'unknown nightlife variant: {variant}')
    w, h, d = p.size
    if w < 5 or h < 6 or d < 6:
        raise ValueError('nightlife v2 needs at least a 5 x 6 x 6 m site')
    front = d/2 - .7
    sign_y = p.params.get('sign_height', 3.5)
    opening = min(p.params.get('shutter_width', 3.4), w - 2.2)
    width = min(opening + .8, w - 2.2)
    neon = _NEON[variant]
    kit = _Kit(p)
    _shell(kit, w, h, d, front, sign_y, opening)
    kit.add('architecture', 'entrance', *_entrance(variant, opening, front))
    kit.add('architecture', 'canopy', *_canopy(variant, width, front))
    kit.add('architecture', 'signage', *_signage(variant, w, sign_y, front, opening, neon))
    kit.add('utility', 'frontage-lighting', *_lighting(variant, w, width, front, neon))
    kit.add('utility', 'wall-equipment', *utility_parts(p, seed))
    kit.add('lived_in', 'street-clutter', *_clutter(variant, w, front, seed, p.key))
    return kit.finish()


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    return [(detailed_nightlife(p, layout.seed) if p.params.get('detail_profile') == 'v2'
             else _front(p)) for p in layout.placements
            if p.sector == sector and p.kind == 'nightlife']
