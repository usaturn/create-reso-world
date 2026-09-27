"""Three fixed, grounded AR projectors with separate local driven meshes.

Coordinates are metres, Y up; each named empty owns one placement transform.
Headline glyphs are authored later from Layout.labels under that *fixed* empty.
"""
from __future__ import annotations
import math

from .geometry import Assembly, box, mesh, tube
from .types import Layout


def _arc(name, radius, y, start, end, depth, color):
    return tube(name, [(radius*math.sin(start+(end-start)*j/20),
                        y + .08*math.sin((start+(end-start)*j/20)*2),
                        depth+radius*(math.cos(start+(end-start)*j/20)-1))
                       for j in range(21)], .023, 6, color, ref=(0, 1, 0))


def _optic():
    """Closed elongated optical housing: bulging cornea, inset pupil and an orbital rim."""
    vertices = []
    levels = ((-.9, .12, -.06), (-.7, .42, .06), (-.25, .57, .2),
              (.35, .54, .21), (.76, .37, .08), (.93, .09, -.04))
    for y, radius, z in levels:
        for j in range(24):
            a = 2*math.pi*j/24
            vertices.append((radius*math.cos(a), y+.48, z+.25*math.sin(a)))
    faces = []
    for k in range(len(levels)-1):
        for j in range(24):
            u = k*24+j; v = k*24+(j+1)%24
            faces.append((u, v, v+24, u+24))
    faces.extend((tuple(reversed(range(24))), tuple(range((len(levels)-1)*24, len(levels)*24))))
    return mesh('optic-housing', vertices, faces, 'holo_cyan')


def _product():
    fixed = [box('floor-mount', (0, -3.85, 0), (.76, .30, .76), 'steel_dark'),
             box('mast', (0, -2.1, 0), (.20, 3.55, .20), 'steel_bare'),
             box('emitter', (0, -.29, 0), (.68, .19, .68), 'steel_dark'),
             box('emitter-lens', (0, -.172, 0), (.33, .045, .33), 'holo_cyan')]
    moving = [_optic(),
              tube('iris', [(math.cos(t*math.tau/32)*.38, .49+math.sin(t*math.tau/32)*.38, .49)
                            for t in range(33)], .026, 6, 'holo_magenta', ref=(0, 0, 1)),
              box('pupil', (0, .49, .52), (.13, .26, .04), 'holo_magenta')]
    for start, end, y, radius in ((-.95,-.15,.48,1.12), (.1,.92,.48,1.12),
                                  (1.18,2.04,.48,1.12), (2.26,2.96,.48,1.12),
                                  (-.62,.54,1.37,.78), (1.20,2.26,1.37,.78)):
        # Orbital telemetry sweeps: short tubes with open gaps, not a chunky frame.
        moving.append(tube('segmented-arc', [(radius*math.sin(start+(end-start)*j/16),
                                              y+.15*math.sin((start+(end-start)*j/16)*2),
                                              radius*math.cos(start+(end-start)*j/16))
                                             for j in range(17)], .027, 6, 'holo_magenta', ref=(0, 1, 0)))
    return fixed, moving


def _info():
    fixed = [box('roof-mount', (0, -.91, .73), (1.15, .18, .46), 'steel_dark'),
             box('mast', (0, -.48, .73), (.22, .85, .22), 'steel_bare'),
             box('emitter', (0, -.05, .73), (1.1, .16, .33), 'steel_dark')]
    # Stagger narrow, interrupted shapes in Z, leaving the headline space unobstructed.
    for z, width, height, color in ((.63, 4.3, 2.7, 'holo_magenta'),
                                     (.23, 3.7, 2.15, 'holo_cyan'),
                                     (-.42, 3.1, 1.5, 'holo_magenta')):
        for side in (-1, 1):
            x = side*width/2
            fixed.append(tube('broken-outline', [(x, .27, z), (x, height*.46, z)],
                              .022, 6, color))
            fixed.append(tube('broken-outline', [(x, height*.64, z), (x, height, z),
                                                   (x-side*.65, height, z)], .022, 6, color))
        fixed.append(box('depth-tick', (-width*.28, height*.72, z),
                         (.32, .035, .035), color))
    moving = []
    for j in range(5):
        moving.append(box('scan-stroke', (-1.45+j*.72, .38+j*.43, -.62),
                          (.42, .025, .025), 'holo_cyan'))
    return fixed, moving


def _ribbon_mesh():
    """A thin solid bent sign, with actual swept front/back/edge faces."""
    verts = []
    for i in range(41):
        a = -.68+1.36*i/40
        x, z = 4.35*math.sin(a), 4.35*(math.cos(a)-1)
        for depth in (0, -.022):
            for y in (-.34, .34):
                verts.append((x, .94+y, z+depth))
    faces = []
    for i in range(40):
        a, b = 4*i, 4*(i+1)
        faces.extend(((a, b, b+1, a+1), (a+2, a+3, b+3, b+2),
                      (a, a+2, b+2, b), (a+1, b+1, b+3, a+3)))
    faces.extend(((0, 1, 3, 2), (160, 162, 163, 161)))
    return mesh('curved-ribbon', verts, faces, 'holo_lime')


def _ribbon():
    fixed = [box('floor-mount', (0, -5.86, -.68), (.72, .28, .72), 'steel_dark'),
             box('mast', (0, -2.92, -.68), (.18, 5.73, .18), 'steel_bare'),
             box('emitter', (0, -.03, -.68), (.86, .18, .42), 'steel_dark'),
             _ribbon_mesh()]
    for side in (-1, 1):
        fixed.append(box('emitter-arm', (side*.73, .08, -.68), (1.35, .08, .11), 'steel_dark'))
    for start, end in ((-.66,-.3), (-.18,.18), (.3,.66)):
        fixed.append(_arc('light-arc', 4.39, 1.38, start, end, .025, 'holo_orange'))
    moving = []
    for a in (-.52, -.25, .13, .4):
        x, z = 4.39*math.sin(a), 4.39*(math.cos(a)-1)
        moving.append(tube('flow-glyph', [(x-.08, .82, z+.04), (x, 1.0, z+.05),
                                          (x+.08, .82, z+.04)], .018, 6, 'holo_orange'))
    return fixed, moving


def _triangles(part):
    # Bent ribbon, rotating cornea and curved light-tube quad corners are not
    # coplanar; triangulate explicitly so per-face metric UV projection is exact.
    return mesh(part.name, part.vertices,
                [ (face[0], face[j], face[j+1])
                  for face in part.faces for j in range(1, len(face)-1) ], part.material)


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    if sector != 'ads':
        raise ValueError(f'not an ads sector: {sector}')
    result = []
    families = {'product-holo': (_product, 'spin', (0., 1., 0.), 5.),
                'info-ad': (_info, 'scan', (0., 1., 0.), .08),
                'ribbon-ad': (_ribbon, 'scan', (1., 0., 0.), .06)}
    for p in layout.placements:
        if p.sector != sector:
            continue
        make, kind, axis, rate = families[p.kind]
        fixed, moving = make()
        fixed = [_triangles(part) for part in fixed]
        moving = [_triangles(part) for part in moving]
        driven = f'{p.key}-driven'
        result.append(Assembly(p.kind, p.key, sector, p.origin, [],
                               {'placement_key': p.key, 'anchor': True, 'yaw_deg': p.yaw_deg}))
        result.append(Assembly(p.kind, f'{p.key}-projector', sector, (0, 0, 0), fixed,
                               {'placement_key': p.key, 'parent_name': p.key}))
        result.append(Assembly(p.kind, driven, sector, (0, 0, 0), moving,
                               {'placement_key': p.key, 'parent_name': p.key,
                                'motion': {'kind': kind, 'driven_name': driven, 'axis': axis,
                                           'rate': rate}}))
    return result
