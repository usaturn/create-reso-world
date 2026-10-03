"""Breaks caught: a wrong-facing Yarol or an enterable/excessively deep facade."""
from modeling.slum03.geometry import bounds
from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.spatial import placement_bounds, validate_clearance
from modeling.slum03.types import Bounds3


def test_yarol_is_northeast_and_east_facing():
    layout = build_layout()
    bar, = layout.select('yarol')
    assert 43 <= bar.origin[0] <= 59 and 40 <= bar.origin[2] <= 54
    assert bar.yaw_deg == 90
    assert any(s.text == 'Yarol' and s.parent_name == 'yarol' for s in layout.labels)
    (a,) = sector_assemblies(layout, 'yarol')
    assert a.name == 'yarol' and a.meta['placement_key'] == 'yarol'
    front = [p for p in a.parts if p.name in ('closed-entrance', 'window-glow')]
    assert len(front) >= 2
    assert all(min(v[0] for v in part.vertices) > 4.5 for part in front), 'front must face world east'
    assert any(p.name == 'sign-bracket' for p in a.parts)
    lo, hi = bounds(a.parts)
    real = Bounds3(tuple(lo[i]+a.origin[i] for i in range(3)),
                   tuple(hi[i]+a.origin[i] for i in range(3)))
    lot = placement_bounds(bar)
    assert all(lot.minimum[i]-1e-6 <= real.minimum[i] <= real.maximum[i] <= lot.maximum[i]+1e-6
               for i in range(3))
    assert not validate_clearance(layout, {a.name: real})


def test_yarol_has_no_enterable_interior():
    (a,) = sector_assemblies(build_layout(), 'yarol')
    names = {p.name for p in a.parts}
    assert {'closed-entrance', 'window-glow', 'window-frame', 'shallow-reveal', 'sign-bracket'} <= names
    assert not names.intersection({'room', 'floor', 'open-door', 'interior'})
    doors = [p for p in a.parts if p.name == 'closed-entrance']
    assert len(doors) == 1
    lo, hi = bounds(doors)
    assert lo[1] <= .01 and hi[1] >= 2.2
    assert hi[2]-lo[2] >= 1.6  # width of the closed east-facing door, along world Z
    # At person height the closed panel covers the middle of the approach, and
    # the decorative illuminated depth behind the window is under half a metre.
    assert any(min(v[2] for v in p.vertices) < 0 < max(v[2] for v in p.vertices)
               for p in doors)
    glow = next(p for p in a.parts if p.name == 'window-glow')
    assert abs(bounds([glow])[0][0]-bounds(doors)[0][0]) < .5


def test_yarol_neon_is_physically_supported_by_wall_brackets():
    (a,) = sector_assemblies(build_layout(), 'yarol')
    fascia = next(part for part in a.parts if part.name == 'fascia')
    brackets = [part for part in a.parts if part.name == 'sign-bracket']
    trim = [part for part in a.parts if part.name == 'sign-trim']
    assert len(brackets) == 2
    def overlaps(part, other):
        lo, hi = bounds([part]); low, high = bounds([other])
        return all(lo[i] <= high[i]+.005 and low[i] <= hi[i]+.005 for i in range(3))
    assert all(overlaps(bracket, fascia) for bracket in brackets)
    assert all(any(overlaps(bracket, tube) for tube in trim) for bracket in brackets)


def _front_ray_hits(parts, start, direction, max_distance):
    # Actual triangle intersections, not placement AABBs or a wall part name.
    def dot(a, b):
        return sum(x*y for x,y in zip(a,b))
    def sub(a,b):
        return tuple(x-y for x,y in zip(a,b))
    def cross(a,b):
        return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    for part in parts:
        for face in part.faces:
            for i in range(1, len(face)-1):
                a,b,c = (part.vertices[j] for j in (face[0], face[i], face[i+1]))
                edge, other = sub(b,a), sub(c,a)
                h = cross(direction,other)
                det = dot(edge,h)
                if abs(det) < 1e-9:
                    continue
                rel = sub(start,a)
                u = dot(rel,h)/det
                if not -1e-7 <= u <= 1+1e-7:
                    continue
                q = cross(rel,edge)
                v = dot(direction,q)/det
                if v < -1e-7 or u+v > 1+1e-7:
                    continue
                distance = dot(other,q)/det
                if 0 < distance <= max_distance:
                    return True
    return False


def test_yarol_front_grid_hits_closed_exterior_at_shallow_depth():
    (bar,) = sector_assemblies(build_layout(), 'yarol')
    # World-east approach. Check gaps between door/glazing and the upper storeys,
    # not just the closed door and one illuminated window.
    for height in (.9, 1.6, 2.35, 3.4, 5.9, 7.7, 10.1):
        for north in (-5.9, -4.48, -3, -2, 0, 2, 3, 4.48, 5.9):
            assert _front_ray_hits(bar.parts, (6.05,height,north), (-1,0,0), 1.2), (height,north)
