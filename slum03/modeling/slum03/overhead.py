"""Supported overhead lines: the legacy west span plus Task 8 district routes.

Every route is one Assembly per overhead Placement with two ground-anchored
poles. Cable ends sit on insulators carried by each pole's crossarm; sag stays
well above the 3 m activity air, and poles stay outside every walking route.
"""
import math

from .geometry import Assembly, box, catenary, tube
from .spatial import validate_clearance
from .types import Bounds3, Layout


def _legacy(p, sector):
    half = p.size[0]/2
    span = half-.75
    base = -p.origin[1]
    parts = []
    for x in (-span, span):
        parts.extend((
            box('pole-footing', (x, base+.16, 0), (.6, .32, .6), 'concrete_raw'),
            box('pole', (x, (base+.22)/2, 0), (.22, -base+.22, .22), 'steel_dark'),
            box('crossarm', (x, -.1, 0), (.52, .12, .6), 'steel_dark'),
            box('insulator', (x, -.035, 0), (.2, .22, .19), 'rust_dark'),
        ))
    # Endpoint centre lies on each insulator, not in midair. Sag stays above
    # the 3m activity-air limit and all supports stay outside walking routes.
    points = catenary((-span, -.02, 0), (span, -.02, 0), .68, 16)
    parts.append(tube('power-cable', points, .042, 6, 'rubber'))
    for x in (-span, span):
        parts.append(tube('strain-brace', [(x, -1.15, -.1),
                                            (x, -.18, -.26)], .04, 6, 'steel_bare'))
    return Assembly('overhead', p.key, sector, p.origin, parts, {'placement_key': p.key})


def _route(p, sector):
    """Two poles at the declared root-local supports, a power and a service line."""
    ox, oy, oz = p.origin
    ends = [tuple(s[i] - (ox, oy, oz)[i] for i in range(3)) for s in p.params['supports']]
    (ax, ay, az), (bx, by, bz) = ends
    length = math.hypot(bx-ax, bz-az)
    ux, uz = (bx-ax)/length, (bz-az)/length
    nx, nz = -uz, ux                     # crossarm direction
    along_x = abs(ux) > abs(uz)
    base = -oy
    parts = []
    for index, (sx, sy, sz) in enumerate(ends):
        arm = (.52, .12, .6) if along_x else (.6, .12, .52)
        parts += [box('pole-footing', (sx, base+.16, sz), (.6, .32, .6), 'concrete_raw'),
                  box('pole', (sx, (base+sy+.22)/2, sz), (.22, sy+.22-base, .22), 'steel_dark'),
                  box('crossarm', (sx, sy-.1, sz), arm, 'steel_dark')]
        for side in (.2, -.2):
            parts.append(box('insulator', (sx+nx*side, sy-.035, sz+nz*side), (.18, .2, .18), 'rust_dark'))
        parts.append(tube('strain-brace', [(sx-nx*.1, sy-1.15, sz-nz*.1),
                                            (sx-nx*.26, sy-.18, sz-nz*.26)], .04, 6, 'steel_bare'))
        if index == 0:  # pole-mounted transformer/junction can at the feed end
            parts += [box('transformer', (sx+nx*.26, sy-1.9, sz+nz*.26),
                          (.3, .6, .3) if not along_x else (.34, .6, .3), 'paint_teal_faded'),
                      box('transformer-band', (sx+nx*.14, sy-1.7, sz+nz*.14),
                          (.14, .06, .14), 'steel_bare')]
    sag = min(.9, .06*length)
    for name, side, extra, radius in (('power-cable', .2, 0., .042), ('service-cable', -.2, .25, .03)):
        a = (ax+nx*side, ay-.02, az+nz*side)
        b = (bx+nx*side, by-.02, bz+nz*side)
        parts.append(tube(name, catenary(a, b, sag+extra, 16), radius, 6, 'rubber'))
    return Assembly('overhead', p.key, sector, p.origin, parts,
                    {'placement_key': p.key, 'route': p.params.get('route'),
                     'cluster': p.params.get('cluster')})


def build_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    return [(_route(p, sector) if 'supports' in p.params else _legacy(p, sector))
            for p in layout.placements if p.sector == sector and p.kind == 'overhead']


def _root_bounds(assembly, part):
    return Bounds3(tuple(min(v[i] for v in part.vertices) + assembly.origin[i] for i in range(3)),
                   tuple(max(v[i] for v in part.vertices) + assembly.origin[i] for i in range(3)))


def _cable_ends(assembly, part):
    sides = len(part.faces[-1])  # tube end cap ring
    rings = (part.vertices[:sides], part.vertices[-sides:])
    return [tuple(sum(v[i] for v in ring)/sides + assembly.origin[i] for i in range(3))
            for ring in rings]


def route_evidence(layout: Layout, assemblies: list[Assembly]):
    """Count routes from geometry: supported ends, sag, span and unshared poles."""
    issues: list[str] = []
    by_name = {a.name: a for a in assemblies}
    candidates = []
    for p in layout.placements:
        if p.kind != 'overhead':
            continue
        a = by_name.get(p.key)
        if a is None:
            issues.append(f'{p.key}: route assembly missing')
            continue
        problems = []
        poles = [_root_bounds(a, part) for part in a.parts if part.name == 'pole']
        cables = [part for part in a.parts if part.name in ('power-cable', 'service-cable')]
        if not cables:
            problems.append('no cable')
        supports = []
        for cable in cables:
            for end in _cable_ends(a, cable):
                pole = next((b for b in poles
                             if b.minimum[1] <= .05 and b.maximum[1] >= end[1]-.3 and
                             b.minimum[0]-.45 <= end[0] <= b.maximum[0]+.45 and
                             b.minimum[2]-.45 <= end[2] <= b.maximum[2]+.45), None)
                if pole is None:
                    problems.append('unsupported cable endpoint')
                    continue
                centre = ((pole.minimum[0]+pole.maximum[0])/2, (pole.minimum[2]+pole.maximum[2])/2)
                if centre not in supports:
                    supports.append(centre)
            if min(v[1] + a.origin[1] for v in cable.vertices) < 3.5:
                problems.append(f'{cable.name} sags below 3.5 m')
        declared = p.params.get('supports')
        if declared is not None and sorted((round(s[0], 3), round(s[2], 3)) for s in declared) != sorted(
                (round(x, 3), round(z, 3)) for x, z in supports):
            problems.append('declared supports do not match pole geometry')
        span = math.dist(*supports) if len(supports) == 2 else 0.
        if len(supports) != 2 or span < 6:
            problems.append(f'span {span:.2f} m with {len(supports)} supports is not a route')
        for part in a.parts:
            if validate_clearance(layout, {p.key: _root_bounds(a, part)}):
                problems.append(f'{part.name} intrudes into protected 3 m air')
                break
        candidates.append((p, supports, span, problems))
    for p, supports, _, problems in candidates:
        for q, others, _, _ in candidates:
            if q.key != p.key and any(math.dist(s, t) < 1. for s in supports for t in others):
                problems.append(f'support shared with {q.key}')
                break
    routes = []
    for p, supports, span, problems in candidates:
        if problems:
            issues.extend(f'{p.key}: {problem}' for problem in problems)
            continue
        routes.append({'key': p.key, 'density_zone': p.params.get('density_zone'),
                       'cluster': p.params.get('cluster'), 'supports': supports,
                       'span': round(span, 3)})
    return routes, issues
