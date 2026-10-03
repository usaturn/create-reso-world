"""Conservative directional proxy rays; not a replacement for real-mesh scene QA.

A ray only counts if it reaches the requested target before any nearer bound.
For the north test the upper silhouette is sampled, rather than accepting a
coordinate north of the wall. West/south sample a three-ray horizon fan.
"""
from __future__ import annotations
import math
from collections.abc import Mapping
from .types import Bounds3, Layout, Vec3


def _hit(eye: Vec3, point: Vec3, bounds: Bounds3) -> float | None:
    """First parametric intersection with a closed AABB along a finite segment."""
    lo, hi = 0., 1.
    for i in range(3):
        d = point[i] - eye[i]
        if abs(d) < 1e-10:
            if not bounds.minimum[i] <= eye[i] <= bounds.maximum[i]:
                return None
            continue
        a, b = ((bounds.minimum[i] - eye[i])/d, (bounds.maximum[i] - eye[i])/d)
        lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
        if lo > hi:
            return None
    return lo


def _visible(eye: Vec3, point: Vec3, target: str, bounds: Mapping[str, Bounds3]) -> bool:
    target_box = bounds.get(target)
    if target_box is None:
        return False
    distance = _hit(eye, point, target_box)
    if distance is None:
        return False
    for key, box in bounds.items():
        if key == target:
            continue
        hit = _hit(eye, point, box)
        if hit is not None and hit < distance - 1e-5:
            return False
    return True


def sightline_report(layout: Layout, bounds_by_key: Mapping[str, Bounds3]) -> dict[str, bool]:
    eyes = {v.key: v.eye for v in layout.viewpoints}
    arcologies = [p.key for p in layout.select('arcology') if p.key in bounds_by_key]
    north = eyes['plaza-north']
    readable = 0
    for key in arcologies:
        b = bounds_by_key[key]
        # Two separated upper-face sample rays must survive foreground occluders.
        z = b.minimum[2]
        y = b.minimum[1] + .88 * (b.maximum[1] - b.minimum[1])
        samples = [(b.minimum[0] + t*(b.maximum[0]-b.minimum[0]), y, z) for t in (.3, .7)]
        if all(_visible(north, point, key, bounds_by_key) for point in samples):
            readable += 1
    forest = bounds_by_key.get('forest')
    east = False
    if forest and forest.maximum[1] >= 12:
        visible_from = []
        for eye in (eyes['east-forest'], eyes['east-lane']):
            points = [(forest.minimum[0], forest.minimum[1] + .55 * (forest.maximum[1]-forest.minimum[1]), z)
                      for z in (-35, 0, 35)]
            visible_from.append(sum(_visible(eye, pt, 'forest', bounds_by_key) for pt in points) >= 2)
        east = all(visible_from)
    def city(view: str, key: str, axis: int, direction: int) -> bool:
        b = bounds_by_key.get(key)
        if b is None or b.maximum[1] < 12:
            return False
        eye = eyes[view]
        near = b.maximum[axis] if direction < 0 else b.minimum[axis]
        other = 2 if axis == 0 else 0
        rays = []
        for angle in (-15, 0, 15):
            pt = list(eye)
            pt[axis] = near
            pt[other] += (near - eye[axis]) * math.tan(math.radians(angle))
            pt[1] = 12.
            rays.append(tuple(pt))
        return all(_visible(eye, pt, key, bounds_by_key) for pt in rays)
    return {'north_arcologies': readable >= 2, 'east_forest': east,
            'west_city': city('west-city', 'west-city', 0, -1),
            'south_city': city('south-market', 'south-city', 2, -1)}
