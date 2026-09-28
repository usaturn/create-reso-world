"""Offline density audit. Blockout envelopes are not evaluated geometry or live QA."""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
import math
from typing import Mapping, Sequence

from .density_model import TARGET_COUNTS, validate_density_config
from .spatial import placement_bounds, validate_clearance
from .types import Bounds3, Issue, Layout, RectXZ, Report

MAJOR = frozenset(TARGET_COUNTS)
FRONTAGE = frozenset(('ruin', 'shack', 'stall', 'nightlife', 'yarol', 'utility'))
OPENING_REASONS = frozenset(('plaza-entry', 'east-forest-view', 'market-loading'))


def union_area(rects: Sequence[RectXZ]) -> float:
    """Sweep X slices; union Z intervals within each slice, never sum overlaps."""
    if not rects:
        return 0.
    xs = sorted({v for r in rects for v in (r.x_min, r.x_max)})
    area = 0.
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((r.z_min, r.z_max) for r in rects
                           if r.x_min < right and r.x_max > left)
        length, end = 0., -math.inf
        for lo, hi in intervals:
            length += max(0., hi - max(lo, end))
            end = max(end, hi)
        area += (right-left)*length
    return area


def _rect(b: Bounds3) -> RectXZ:
    return RectXZ(b.minimum[0], b.maximum[0], b.minimum[2], b.maximum[2])


def _clip(a: RectXZ, b: RectXZ) -> RectXZ | None:
    r = RectXZ(max(a.x_min, b.x_min), min(a.x_max, b.x_max),
               max(a.z_min, b.z_min), min(a.z_max, b.z_max))
    return r if min(r.size) > 0 else None


def _hash(data) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def layout_digest(layout: Layout) -> str:
    """Semantic digest of canonical UTF-8 JSON; not the saved file byte hash.

    Task 5 build reports must emit this digest of the *input Layout*; the
    reference file's SHA-256 is recorded separately on the diagnostic report.
    """
    return _hash(asdict(layout))


def _evidence(layout: Layout, reports: Mapping[str, Report], basis: str):
    """Return *individual* bounds; no disjoint buildings combined into one AABB."""
    if basis == 'blockout':
        return {p.key: [placement_bounds(p)] for p in layout.placements}, []
    if basis != 'evaluated':
        raise ValueError('geometry_basis must be blockout or evaluated')
    result = defaultdict(list)
    issues = []
    placements = {p.key: p for p in layout.placements}
    digest = layout_digest(layout)
    for sector, report in reports.items():
        if report.get('layout_sha256') != digest:
            issues.append(Issue('LAYOUT_MISMATCH', sector,
                                'evaluated report missing or mismatching semantic Layout digest'))
            continue  # Never promote old geometry to the current Layout.
        for obj in report.get('objects', []):
            key, mesh = obj.get('placement_key') or obj.get('key'), obj.get('mesh')
            if key not in placements or not mesh:
                continue
            raw = report.get('evaluated_bounds', {}).get(mesh)
            if (not raw or type(obj.get('vertices')) is not int or obj['vertices'] < 3
                    or type(obj.get('faces')) is not int or obj['faces'] < 1):
                issues.append(Issue('GEOMETRY_MISSING', key, 'no nonempty evaluated mesh and bounds'))
                continue
            try:
                b = Bounds3(tuple(raw['minimum']), tuple(raw['maximum']))
                if (len(b.minimum) != 3 or len(b.maximum) != 3 or
                        any(not isinstance(v, (int, float)) or not math.isfinite(v)
                            for v in (*b.minimum, *b.maximum)) or
                        b.minimum[0] >= b.maximum[0] or b.minimum[2] >= b.maximum[2] or
                        b.minimum[1] > b.maximum[1] or
                        (placements[key].kind in MAJOR and b.minimum[1] == b.maximum[1])):
                    raise ValueError('invalid bounds')
                result[key].append(b)
            except (KeyError, TypeError, ValueError):
                issues.append(Issue('GEOMETRY_MISSING', key, 'invalid evaluated bounds'))
    for p in layout.placements:
        if p.domain == 'district' and p.kind in MAJOR and not result[p.key]:
            issues.append(Issue('GEOMETRY_MISSING', p.key, 'no evaluated major-use geometry'))
    return result, issues


def _interval_gaps(route, layout, evidence):
    corridor = route.corridor
    vertical = corridor.size[1] >= corridor.size[0]
    start, stop = ((corridor.z_min, corridor.z_max) if vertical else
                   (corridor.x_min, corridor.x_max))
    mid = ((corridor.x_min + corridor.x_max)/2 if vertical else
           (corridor.z_min + corridor.z_max)/2)
    intervals = []
    by_key = {p.key: p for p in layout.placements}
    for key, bounds in evidence.items():
        p = by_key.get(key)
        if not p or p.domain != 'district' or p.kind not in FRONTAGE:
            continue
        for b in bounds:
            if b.maximum[1] <= 0 or b.minimum[1] >= 8 or min(b.maximum[1], 8)-max(b.minimum[1], 0) < 1:
                continue
            r = _rect(b)
            for side in (-1, 1):
                band = ((mid-10, mid) if side < 0 else (mid, mid+10))
                lateral = (r.x_min, r.x_max) if vertical else (r.z_min, r.z_max)
                if min(lateral[1], band[1]) <= max(lateral[0], band[0]):
                    continue
                lo, hi = ((r.z_min, r.z_max) if vertical else (r.x_min, r.x_max))
                if min(hi, stop) - max(lo, start) >= 1:
                    intervals.append((max(start, lo), min(stop, hi)))
    # Only explicit, bounded, corridor-crossing, approved openings count.
    from .density_layout import ROUTES as AUTHORED_ROUTES
    authorized = next((r.openings for r in AUTHORED_ROUTES
                       if r.key == route.key and r.corridor == route.corridor), ())
    for opening in route.openings:
        if opening not in authorized:
            continue
        r = opening.bounds
        lo, hi = ((r.z_min, r.z_max) if vertical else (r.x_min, r.x_max))
        cross = (r.x_min <= corridor.x_min and r.x_max >= corridor.x_max) if vertical else (
            r.z_min <= corridor.z_min and r.z_max >= corridor.z_max)
        if opening.reason in OPENING_REASONS and cross and 0 < hi-lo <= 6 and start <= lo < hi <= stop:
            intervals.append((lo, hi))
    gaps = []
    end = start
    for lo, hi in sorted(intervals):
        if lo > end:
            gaps.append({'start': end, 'end': lo, 'length': lo-end})
        end = max(end, hi)
    if end < stop:
        gaps.append({'start': end, 'end': stop, 'length': stop-end})
    return gaps


def density_report(layout: Layout, reports: Mapping[str, Report], geometry_basis: str) -> Report:
    evidence, geometry_issues = _evidence(layout, reports, geometry_basis)
    density = layout.density
    uses = [p for p in layout.placements if p.domain == 'district' and p.kind in MAJOR]
    occupancy = [_rect(b) for p in uses for b in evidence.get(p.key, [])]
    by_zone = {}
    if density:
        for zone in density.zones:
            contained = [p for p in uses if p.params.get('density_zone') == zone.key or
                         (not p.params.get('density_zone') and
                          zone.bounds.x_min <= p.origin[0] < zone.bounds.x_max and
                          zone.bounds.z_min <= p.origin[2] < zone.bounds.z_max)]
            clips = [c for p in uses for b in evidence.get(p.key, [])
                     if (c := _clip(_rect(b), zone.bounds)) is not None]
            by_zone[zone.key] = {'counts': dict(Counter(p.kind for p in contained)),
                                  'occupied_union_m2': union_area(clips)}
    paths = {r.key: _interval_gaps(r, layout, evidence) for r in density.routes} if density else {}
    attachments = [{'child': p.key, 'parent': p.params['attachment'].get('parent_key'),
                    'contact_min': p.params['attachment'].get('contact_min'),
                    'contact_max': p.params['attachment'].get('contact_max')}
                   for p in layout.placements if isinstance(p.params.get('attachment'), dict)]
    issues = _issues(layout, evidence, geometry_issues, paths, geometry_basis)
    return {'stage': density.stage if density else None, 'geometry_basis': geometry_basis,
            'layout_sha256': layout_digest(layout),
            'layout_sha256_basis': 'canonical-layout-json-utf8',
            'counts': dict(Counter(p.kind for p in uses)), 'by_zone': by_zone,
            'variants': {kind: sorted({p.params['variant'] for p in uses
                                      if p.kind == kind and 'variant' in p.params}) for kind in MAJOR},
            'occupied_union_m2': union_area(occupancy), 'frontage_gaps': paths,
            'attachments': attachments, 'issues': [asdict(i) for i in issues],
            'references': {'layout': None, 'build': None, 'export': None,
                           'report_sha256': {name: _hash(report) for name, report in reports.items()}},
            'occupancy_note': 'Per-mesh conservative evaluated rectangles; union does not prove walkable openings.'}


def _attached_contact_covers(a, b, overlap):
    for child, parent in ((a, b), (b, a)):
        contact = child.params.get('attachment')
        if not isinstance(contact, dict) or contact.get('parent_key') != parent.key:
            continue
        lo, hi = contact.get('contact_min'), contact.get('contact_max')
        if (not isinstance(lo, (list, tuple)) or not isinstance(hi, (list, tuple)) or
                len(lo) != 3 or len(hi) != 3):
            continue
        if all(type(v) in (float, int) and math.isfinite(v) for v in (*lo, *hi)) and all(
                lo[i]-1e-6 <= overlap.minimum[i] <= overlap.maximum[i] <= hi[i]+1e-6
                for i in range(3)):
            return True
    return False


def _issues(layout, evidence, geometry_issues, paths, basis):
    issues = list(geometry_issues) + validate_density_config(layout)
    density = layout.density
    if density is None:
        return issues + [Issue('DENSITY_CONFIG', 'density', 'density configuration missing')]
    uses = [p for p in layout.placements if p.domain == 'district' and p.kind in MAJOR]
    if density.stage in ('full', 'blockout'):
        counts = Counter(p.kind for p in uses)
        for kind, count in TARGET_COUNTS.items():
            if counts[kind] != count:
                issues.append(Issue('DENSITY_COUNT', kind, f'expected {count}, found {counts[kind]}'))
        # Actual position must be within the declared zone, not merely tagged.
        for p in uses:
            if p.key == 'yarol':
                continue
            matches = [z for z in density.zones if z.key == p.params.get('density_zone')]
            if p.key.startswith('density-') and (not matches or
                    not (matches[0].bounds.x_min <= p.origin[0] < matches[0].bounds.x_max and
                         matches[0].bounds.z_min <= p.origin[2] < matches[0].bounds.z_max)):
                issues.append(Issue('DENSITY_ZONE', p.key, 'placement is outside declared zone'))
        for zone in density.zones:
            if not any(p.kind in MAJOR and p.key != 'yarol' and
                       zone.bounds.x_min <= p.origin[0] < zone.bounds.x_max and
                       zone.bounds.z_min <= p.origin[2] < zone.bounds.z_max for p in uses):
                issues.append(Issue('DENSITY_ZONE', zone.key, 'empty district'))
    for key, gaps in (paths.items() if density.stage != 'representative' else ()):
        for gap in gaps:
            if gap['length'] > 20 + 1e-8:
                issues.append(Issue('FRONTAGE_GAP', key, f"{gap['length']:.3f} m empty frontage"))
    # Individual physical mesh/envelopes, including v2 replacements and mounted
    # utility: exclude walkable surfaces and nonphysical advertising projections.
    solids = [p for p in layout.placements if p.domain == 'district' and
              p.kind not in {'ground', 'floor', 'product-holo', 'info-ad', 'ribbon-ad'}]
    for i, a in enumerate(solids):
        for b in solids[i+1:]:
            if not (a.key.startswith('density-') or b.key.startswith('density-') or
                    a.kind == 'utility' or b.kind == 'utility' or
                    a.params.get('detail_profile') == 'v2' or
                    b.params.get('detail_profile') == 'v2'):
                continue  # Neither side was added or remodeled.
            for ba in evidence.get(a.key, []):
                for bb in evidence.get(b.key, []):
                    overlap = Bounds3(tuple(max(x, y) for x, y in zip(ba.minimum, bb.minimum)),
                                      tuple(min(x, y) for x, y in zip(ba.maximum, bb.maximum)))
                    if all(x < y for x, y in zip(overlap.minimum, overlap.maximum)) and not _attached_contact_covers(a, b, overlap):
                        issues.append(Issue('DENSITY_OVERLAP', a.key, f'intersects {b.key}'))
    # Clearance expects placement keys; use individual meshes without merging bounds.
    for key, bs in evidence.items():
        for b in bs:
            issues.extend(validate_clearance(layout, {key: b}))
    entry = RectXZ(57, 60, 43, 51)
    for p in layout.placements:
        if not p.key.startswith('density-') or p.domain != 'district':
            continue
        for b in evidence.get(p.key, []):
            if _clip(_rect(b), entry) and b.minimum[1] < 3 and b.maximum[1] > 0:
                issues.append(Issue('YAROL_ENTRANCE', p.key, 'east-facing entrance blocked'))
    return issues


def validate_density(layout: Layout, reports: Mapping[str, Report], geometry_basis: str) -> list[Issue]:
    return [Issue(**i) for i in density_report(layout, reports, geometry_basis)['issues']]
