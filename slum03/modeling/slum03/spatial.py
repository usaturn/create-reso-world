"""Axis-aligned occupancy of rotated placements and evaluated geometry."""
import math
from typing import Mapping

from .types import Bounds3, Issue, Layout, Placement, RectXZ

# A walkable slab may carry flush decals (cracks, stains, base traces) this far
# above its plane: well below any step a foot or collider can notice.
WALKABLE_DECAL_MAX = .01


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


def branch_intrusion(b: Bounds3, layout: Layout) -> bool:
    """Additional authored walkways/entrances, independent of fixed main paths."""
    return (layout.density is not None and b.minimum[1] < 3 and b.maximum[1] > 0
            and any(_intersects(b, r) for r in layout.density.branch_clearances))


def _walkable_floor_debris(layout: Layout, key: str, b: Bounds3) -> bool:
    """Full-stage central floor debris: small, collider-free and at most FLOOR_DEBRIS_MAX tall."""
    from .density_model import FLOOR_DEBRIS_MAX, FLOOR_DEBRIS_PREFIX
    return (layout.density is not None and layout.density.stage == 'full'
            and isinstance(key, str) and key.startswith(FLOOR_DEBRIS_PREFIX + '-')
            and b.minimum[1] >= -.02 and b.maximum[1] <= FLOOR_DEBRIS_MAX)


def validate_clearance(layout: Layout, bounds: Mapping[str, Bounds3]) -> list[Issue]:
    """Check *evaluated* bounds, not just scatter centres; floor tops are walkable."""
    placements = {p.key: p for p in layout.placements}
    issues = []
    for key, b in bounds.items():
        p = placements.get(key)
        if (len(b.minimum) != 3 or len(b.maximum) != 3 or
                any(not math.isfinite(v) for v in (*b.minimum, *b.maximum)) or
                any(lo > hi or (lo == hi and not (i == 1 and p and p.domain == 'water'))
                    for i, (lo, hi) in enumerate(zip(b.minimum, b.maximum)))):
            issues.append(Issue('BOUNDS', key, 'invalid evaluated bounds'))
            continue
        # A crossing and a roofed checkpoint have essential supports/railings
        # above the walkway; their AABBs include open circulation air. Keep
        # them inside their explicitly authored envelopes, then test their real
        # meshes for free passage (the AABB cannot express an opening).
        if p and p.kind in ('bridge', 'checkpoint'):
            allowed = placement_bounds(p)
            if all(allowed.minimum[i]-1e-6 <= b.minimum[i] <= b.maximum[i] <= allowed.maximum[i]+1e-6
                   for i in range(3)):
                continue
        if p and ((p.params.get('walkable') and b.maximum[1] <= WALKABLE_DECAL_MAX) or
                  (p.domain == 'water' and b.maximum[1] <= 0)):
            continue
        if b.minimum[1] >= 3 or b.maximum[1] <= 0:
            continue
        # Revision 1: walkable small debris may lie on the central floor only.
        on_clear = _intersects(b, layout.clear) and not _walkable_floor_debris(layout, key, b)
        if (on_clear or any(_intersects(b, r) for r in layout.routes)
                or branch_intrusion(b, layout)):
            issues.append(Issue('CLEARANCE_INTRUSION', key, 'evaluated geometry occupies central air or protected 3m route'))
    return issues
