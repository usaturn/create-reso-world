"""Verify indexed source parts against evaluated root-local geometry before counting detail."""
from __future__ import annotations
from collections.abc import Mapping
import math

from .density_metrics import layout_digest
from .detail_evidence import CATEGORIES, detail_groups
from .geometry import Assembly, merge_assembly
from .types import Issue, Layout, Report


def _bounds(points):
    if not points:
        raise ValueError('empty evaluated geometry')
    return {'minimum': [min(v[i] for v in points) for i in range(3)],
            'maximum': [max(v[i] for v in points) for i in range(3)]}


def observe_detail(assembly: Assembly, evaluated_geometry: Mapping[str, object]) -> Report:
    """Require source vertex/face identity; reject modifiers that erase part provenance.

    This deliberately fails closed for topology-changing or deforming modifiers.
    Blender may mirror polygon winding when translating XZY, but indices and
    coordinates must still identify the same physical parts.
    """
    groups = detail_groups(assembly)
    merged = merge_assembly(assembly)
    vertices, faces = evaluated_geometry['vertices'], evaluated_geometry['faces']
    if (not isinstance(vertices, (list, tuple)) or not isinstance(faces, (list, tuple))
            or len(vertices) != len(merged.vertices) or len(faces) != len(merged.faces)):
        raise ValueError('evaluated mesh cannot be mapped to source parts')
    expected = [tuple(v[i] + assembly.origin[i] for i in range(3)) for v in merged.vertices]
    for actual, source in zip(vertices, expected):
        if (not isinstance(actual, (tuple, list)) or len(actual) != 3 or
                any(type(v) not in (int, float) or not math.isfinite(v) for v in actual) or
                any(abs(a-b) > 1e-4 for a, b in zip(actual, source))):
            raise ValueError('evaluated vertex missing, moved or nonfinite')
    for actual, source in zip(faces, merged.faces):
        if (not isinstance(actual, (tuple, list)) or len(actual) != len(source) or
                len(set(actual)) != len(source) or not any(
                    tuple(actual) == tuple(source[i:] + source[:i]) or
                    tuple(actual) == tuple(source[::-1][i:] + source[::-1][:i])
                    for i in range(len(source)))):
            raise ValueError('evaluated face missing or source part correspondence lost')
        a, b, c = (vertices[i] for i in list(actual)[:3])
        ab = [b[i]-a[i] for i in range(3)]
        ac = [c[i]-a[i] for i in range(3)]
        area = [(ab[1]*ac[2]-ab[2]*ac[1]), (ab[2]*ac[0]-ab[0]*ac[2]),
                (ab[0]*ac[1]-ab[1]*ac[0])]
        if math.sqrt(sum(n*n for n in area)) < 1e-9:
            raise ValueError('collapsed evaluated face')
    output = []
    start = 0
    part_bounds = []
    for part in assembly.parts:
        indices = {start + i for face in part.faces for i in face}
        part_bounds.append(_bounds([vertices[i] for i in indices]))
        start += len(part.vertices)
    for group in groups:
        indices = set()
        offset = 0
        for i, part in enumerate(assembly.parts):
            if i in group['part_indices']:
                indices.update(offset + j for face in part.faces for j in face)
            offset += len(part.vertices)
        output.append({**group, 'bounds': _bounds([vertices[i] for i in sorted(indices)]),
                       'part_bounds': [part_bounds[i] for i in group['part_indices']]})
    return {'placement_key': assembly.meta.get('placement_key', assembly.name),
            'key': assembly.name, 'mesh': assembly.name, 'kind': assembly.kind,
            'variant': assembly.meta.get('variant'), 'detail_groups': output,
            'evaluated_bounds': _bounds(vertices), 'vertices': len(vertices), 'faces': len(faces)}


def _measured_bounds(raw):
    try:
        lo, hi = raw['minimum'], raw['maximum']
        if (len(lo) != 3 or len(hi) != 3 or any(
                type(a) not in (float, int) or type(b) not in (float, int) or
                not math.isfinite(a) or not math.isfinite(b) or a >= b
                for a, b in zip(lo, hi))):
            raise ValueError('invalid evaluated bounds')
        return lo, hi
    except (KeyError, TypeError) as exc:
        raise ValueError('missing evaluated bounds') from exc


def v2_object_issues(placement, report: Report, obj: Report) -> list[Issue]:
    """Layout-required v2 facts, independent of self-reported profile/group claims."""
    key = placement.key
    if (obj.get('placement_key') != key or obj.get('detail_profile') != 'v2' or
            obj.get('variant') != placement.params.get('variant') or
            obj.get('kind') != placement.kind):
        return [Issue('DETAIL_MISSING', key, 'owner, kind, profile or variant missing')]
    mesh = obj.get('mesh')
    bounds = report.get('evaluated_bounds', {})
    if (type(mesh) is not str or not mesh or mesh not in bounds or
            type(obj.get('vertices')) is not int or obj['vertices'] < 3 or
            type(obj.get('faces')) is not int or obj['faces'] < 1):
        return [Issue('GEOMETRY_MISSING', key, 'evaluated mesh, bounds or counts missing')]
    try:
        envelope_lo, envelope_hi = _measured_bounds(bounds[mesh])
        groups = obj.get('detail_groups')
        if not isinstance(groups, list) or not groups:
            raise ValueError('detail groups missing')
        ids = set()
        for group in groups:
            identifier = group['id']
            indices = group['part_indices']
            parts = group['part_bounds']
            if (type(identifier) is not str or not identifier or identifier in ids or
                    group['category'] not in CATEGORIES or
                    not isinstance(indices, (list, tuple)) or not indices or
                    any(type(i) is not int or i < 0 or i >= obj['vertices'] for i in indices) or
                    len(set(indices)) != len(indices) or
                    not isinstance(parts, list) or len(parts) != len(indices) or
                    type(group.get('vertex_count')) is not int or group['vertex_count'] < 3 or
                    type(group.get('face_count')) is not int or group['face_count'] < 1):
                raise ValueError('invalid or duplicate detail group')
            ids.add(identifier)
            group_lo, group_hi = _measured_bounds(group['bounds'])
            part_pairs = [_measured_bounds(part) for part in parts]
            for i in range(3):
                if (abs(group_lo[i] - min(lo[i] for lo, _ in part_pairs)) > 1e-4 or
                        abs(group_hi[i] - max(hi[i] for _, hi in part_pairs)) > 1e-4 or
                        group_lo[i] < envelope_lo[i]-1e-4 or
                        group_hi[i] > envelope_hi[i]+1e-4):
                    raise ValueError('group bounds differ from evaluated part/envelope')
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        return [Issue('DETAIL_INVALID', key, str(exc))]
    return []


def _parts_for(placement, report, obj):
    if placement.params.get('detail_profile') == 'v2':
        return [part for group in obj['detail_groups'] for part in group['part_bounds']]
    return [report['evaluated_bounds'][obj['mesh']]]


def validate_evaluated_density(layout: Layout, reports: Mapping[str, Report]) -> list[Issue]:
    """Audit Layout-required evidence and walkable parts; no legacy report promotion."""
    from .density_model import validate_density_config
    from .spatial import validate_clearance
    from .types import Bounds3

    issues = validate_density_config(layout)
    digest = layout_digest(layout)
    placements = {p.key: p for p in layout.placements}
    verified = {}  # placement key -> (placement, report, entry)
    for sector, report in reports.items():
        if report.get('layout_sha256') != digest:
            issues.append(Issue('LAYOUT_MISMATCH', sector,
                                'semantic layout digest missing or different'))
            continue
        for obj in report.get('objects', []):
            if obj.get('detail_profile') != 'v2':
                continue
            p = placements.get(obj.get('placement_key'))
            if p is None or p.params.get('detail_profile') != 'v2' or p.sector != sector:
                issues.append(Issue('DETAIL_INVALID', obj.get('key', sector),
                                    'unowned v2 evidence'))
    for p in layout.placements:
        if p.params.get('detail_profile') != 'v2':
            continue
        report = reports.get(p.sector)
        if report is None:
            issues.append(Issue('LAYOUT_MISMATCH', p.sector, 'evaluated report missing'))
            continue
        if report.get('layout_sha256') != digest:
            continue
        matches = [obj for obj in report.get('objects', [])
                   if obj.get('placement_key') == p.key or
                   (obj.get('key') == p.key and not obj.get('placement_key'))]
        if len(matches) != 1:
            issues.append(Issue('PLACEMENT_MISSING', p.key, 'v2 placement missing or duplicated'))
            continue
        obj = matches[0]
        errors = v2_object_issues(p, report, obj)
        issues.extend(errors)
        if not errors:
            verified[p.key] = p, report, obj
            for group in obj['detail_groups']:
                for raw in group['part_bounds']:
                    lo, hi = _measured_bounds(raw)
                    issues.extend(validate_clearance(layout, {p.key: Bounds3(tuple(lo), tuple(hi))}))
    # Compare actual *parts* of both owners, not enclosing mesh AABBs around
    # openings; the contact box must cover the whole physical intersection.
    for child in layout.placements:
        a = child.params.get('attachment')
        if not isinstance(a, dict) or child.key not in verified:
            continue
        parent = placements.get(a.get('parent_key'))
        if parent is None:
            continue  # validate_density_config already rejects missing parents.
        parent_entry = verified.get(parent.key)
        if parent_entry is None:
            report = reports.get(parent.sector, {})
            if report.get('layout_sha256') != digest:
                issues.append(Issue('GEOMETRY_MISSING', child.key, 'attachment parent has no evaluated report'))
                continue
            matching = [obj for obj in report.get('objects', [])
                        if (obj.get('placement_key') or obj.get('key')) == parent.key and
                        obj.get('mesh') in report.get('evaluated_bounds', {})]
            if len(matching) != 1:
                issues.append(Issue('GEOMETRY_MISSING', child.key, 'attachment parent missing evaluated mesh'))
                continue
            parent_entry = parent, report, matching[0]
        try:
            lo, hi = a['contact_min'], a['contact_max']
            if (len(lo) != 3 or len(hi) != 3 or any(type(v) not in (int, float) or
                    not math.isfinite(v) for v in (*lo, *hi))):
                continue  # Already reported by metadata validation.
            for child_part in _parts_for(*verified[child.key]):
                ca, cb = _measured_bounds(child_part)
                for parent_part in _parts_for(*parent_entry):
                    pa, pb = _measured_bounds(parent_part)
                    overlap_lo = [max(ca[i], pa[i]) for i in range(3)]
                    overlap_hi = [min(cb[i], pb[i]) for i in range(3)]
                    if all(overlap_lo[i] < overlap_hi[i] - 1e-6 for i in range(3)) and any(
                            overlap_lo[i] < lo[i]-1e-4 or overlap_hi[i] > hi[i]+1e-4
                            for i in range(3)):
                        issues.append(Issue('ATTACHMENT_INTRUSION', child.key,
                                            f'evaluated overlap with {parent.key} outside contact box'))
                        break
                else:
                    continue
                break
        except (ValueError, TypeError, KeyError) as exc:
            issues.append(Issue('GEOMETRY_MISSING', child.key, str(exc)))
    return issues
