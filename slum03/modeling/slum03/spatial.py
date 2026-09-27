"""Axis-aligned occupancy of rotated placements and evaluated geometry."""
import math
from typing import Mapping

from .types import Bounds3, Issue, Layout, Placement, RectXZ


def placement_bounds(p: Placement) -> Bounds3:
    """Rotation is about the foot at origin; local_y_min shifts the vertical base."""
    x, y, z = p.origin
    sx, sy, sz = p.size
    angle = math.radians(p.yaw_deg)
    dx = (abs(math.cos(angle)) * sx + abs(math.sin(angle)) * sz) / 2
    dz = (abs(math.sin(angle)) * sx + abs(math.cos(angle)) * sz) / 2
    low = y + p.params.get('local_y_min', 0.0)
    # Snap trigonometric noise at cardinal rotations, retaining sub-mm precision.
    return Bounds3((round(x - dx, 9), low, round(z - dz, 9)),
                   (round(x + dx, 9), low + sy, round(z + dz, 9)))


def _intersects(b: Bounds3, r: RectXZ) -> bool:
    return (b.minimum[0] < r.x_max and b.maximum[0] > r.x_min and
            b.minimum[2] < r.z_max and b.maximum[2] > r.z_min)


def validate_clearance(layout: Layout, bounds: Mapping[str, Bounds3]) -> list[Issue]:
    """Check *evaluated* bounds, not just scatter centres; floor tops are walkable."""
    placements = {p.key: p for p in layout.placements}
    issues = []
    for key, b in bounds.items():
        if (len(b.minimum) != 3 or len(b.maximum) != 3 or
                any(not math.isfinite(v) for v in (*b.minimum, *b.maximum)) or
                any(lo >= hi for lo, hi in zip(b.minimum, b.maximum))):
            issues.append(Issue('BOUNDS', key, 'invalid evaluated bounds'))
            continue
        p = placements.get(key)
        if p and ((p.params.get('walkable') and b.maximum[1] <= 0) or
                  (p.domain == 'water' and b.maximum[1] <= 0)):
            continue
        if b.minimum[1] >= 3 or b.maximum[1] <= 0:
            continue
        if _intersects(b, layout.clear) or any(_intersects(b, r) for r in layout.routes):
            issues.append(Issue('CLEARANCE', key, 'occupied central air or main 3m route'))
    return issues
