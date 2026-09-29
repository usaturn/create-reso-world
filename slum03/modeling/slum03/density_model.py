"""Density metadata validation; no density achievement is inferred from legacy plans."""
import hashlib
import math

from .spatial import placement_bounds
from .types import Issue, Layout, RectXZ

TARGET_COUNTS = {'ruin': 32, 'shack': 28, 'stall': 28, 'nightlife': 8, 'yarol': 1}
REPRESENTATIVE_KEYS = ('ruin-west', 'shack-row', 'market-west')
# Slot-only selected keys: valid without a same-named placement (full stage).
# 'district-foundation' is the baseline Slot name of the 'district-ground' placement;
# SCATTER_PREFIXES name rubble pile families ('<prefix>-<i>-<j>' Slots): the four
# perimeter sides plus, in the full stage, the central floor's walkable debris.
SURFACE_SLOT_KEYS = ('district-foundation',)
# Revision 1 (Task 12): the central 32x22 m floor may carry small, collider-free
# debris no taller than FLOOR_DEBRIS_MAX; never on a main route or entrance.
FLOOR_DEBRIS_PREFIX = 'plaza-rubble-floor'
FLOOR_DEBRIS_MAX = .10
SCATTER_PREFIXES = ('plaza-rubble-west', 'plaza-rubble-east',
                    'plaza-rubble-north', 'plaza-rubble-south', FLOOR_DEBRIS_PREFIX)
# Placement key -> baseline Slot name for the Slot-only surface keys above; the
# placement's native colliders ('collider-district-ground-*') follow that Slot.
SURFACE_PLACEMENT_SLOTS = {'district-ground': 'district-foundation'}


def stable_seed(seed: int, key: str, channel: str) -> int:
    """Independent deterministic 256-bit seed for one placement and channel."""
    if type(seed) is not int or not isinstance(key, str) or not isinstance(channel, str):
        raise ValueError('seed/key/channel must be int/string/string')
    return int.from_bytes(hashlib.sha256(f'{seed}\0{key}\0{channel}'.encode('utf-8')).digest(), 'big')


def _finite_number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _valid_rect(rect) -> bool:
    return (isinstance(rect, RectXZ) and all(_finite_number(v) for v in rect.bounds)
            and rect.x_min < rect.x_max and rect.z_min < rect.z_max)


def _valid_bounds_inputs(placement) -> bool:
    # Guard inputs before computing bounds; this API is callable without validate_layout.
    return (isinstance(placement.origin, (list, tuple)) and len(placement.origin) == 3
            and isinstance(placement.size, (list, tuple)) and len(placement.size) == 3
            and all(_finite_number(v) for v in (*placement.origin, *placement.size))
            and all(v > 0 for v in placement.size)
            and _finite_number(placement.yaw_deg)
            and _finite_number(placement.params.get('local_y_min', 0)))


def _valid_contact(point) -> bool:
    return (isinstance(point, (list, tuple)) and len(point) == 3
            and all(_finite_number(v) for v in point))


def validate_density_config(layout: Layout) -> list[Issue]:
    """Validate optional density/attachment metadata without declaring full achievement."""
    issues: list[Issue] = []
    density = layout.density
    if density is not None:
        if type(density.stage) is not str or density.stage not in ('blockout', 'representative', 'full'):
            issues.append(Issue('DENSITY_STAGE', 'density', 'unknown density stage'))
        for label, entries in (('zones', density.zones), ('routes', density.routes)):
            keys = [entry.key for entry in entries]
            if any(type(key) is not str or not key.strip() for key in keys) or len(keys) != len(set(keys)):
                issues.append(Issue('DENSITY_KEY', label, 'empty or duplicate density key'))
        for zone in density.zones:
            if not _valid_rect(zone.bounds):
                issues.append(Issue('DENSITY_ZONE', str(zone.key), 'invalid zone bounds'))
        for route in density.routes:
            if (type(route.purpose) is not str or route.purpose not in
                    ('residential', 'market', 'alley') or not _valid_rect(route.corridor)):
                issues.append(Issue('DENSITY_ROUTE', str(route.key), 'invalid purpose or corridor'))
            for opening in route.openings:
                if not _valid_rect(opening.bounds) or type(opening.reason) is not str or not opening.reason.strip():
                    issues.append(Issue('DENSITY_OPENING', str(route.key), 'invalid opening or missing reason'))
        for rect in density.branch_clearances:
            if not _valid_rect(rect):
                issues.append(Issue('DENSITY_CLEARANCE', 'density', 'invalid branch clearance'))
        keys = {p.key for p in layout.placements}
        if (any(type(k) is not str or (k not in keys and k not in SURFACE_SLOT_KEYS + SCATTER_PREFIXES)
                    for k in density.selected_keys)
                or len(density.selected_keys) != len(set(density.selected_keys))):
            issues.append(Issue('DENSITY_SELECTION', 'density', 'invalid selected placement keys'))

    by_key = {p.key: p for p in layout.placements}
    parents: dict[str, str] = {}
    for p in layout.placements:
        params = p.params
        if 'detail_profile' in params and params['detail_profile'] != 'v2':
            issues.append(Issue('DENSITY_PARAM', p.key, 'unknown detail profile'))
        for name in ('variant', 'density_zone', 'cluster'):
            if name in params and (type(params[name]) is not str or not params[name].strip()):
                issues.append(Issue('DENSITY_PARAM', p.key, f'invalid {name}'))
        if 'attachment' not in params:
            continue
        a = params['attachment']
        if not isinstance(a, dict):
            issues.append(Issue('ATTACHMENT', p.key, 'attachment must be an object'))
            continue
        parent = a.get('parent_key')
        if type(parent) is not str or not parent or parent == p.key or parent not in by_key:
            issues.append(Issue('ATTACHMENT', p.key, 'unknown or self parent'))
            continue
        parents[p.key] = parent
        lo, hi = a.get('contact_min'), a.get('contact_max')
        if (type(a.get('reason')) is not str or not a['reason'].strip()
                or not _valid_contact(lo) or not _valid_contact(hi)
                or any(x > y for x, y in zip(lo, hi))):
            issues.append(Issue('ATTACHMENT', p.key, 'invalid contact or reason'))
            continue
        if not _valid_bounds_inputs(p) or not _valid_bounds_inputs(by_key[parent]):
            issues.append(Issue('ATTACHMENT', p.key, 'invalid child or parent placement'))
            continue
        child_bounds, parent_bounds = placement_bounds(p), placement_bounds(by_key[parent])
        if any(not (b.minimum[i] - 1e-6 <= lo[i] <= hi[i] <= b.maximum[i] + 1e-6)
               for b in (child_bounds, parent_bounds) for i in range(3)):
            issues.append(Issue('ATTACHMENT', p.key, 'contact outside child or parent bounds'))
    for key in parents:
        seen = set()
        cursor = key
        while cursor in parents and cursor not in seen:
            seen.add(cursor)
            cursor = parents[cursor]
        if cursor in seen:
            issues.append(Issue('ATTACHMENT_CYCLE', key, 'cyclic attachment'))
    return issues
