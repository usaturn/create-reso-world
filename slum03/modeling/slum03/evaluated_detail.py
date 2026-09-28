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
                set(actual) != set(source) or len(set(actual)) < 3):
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


def validate_evaluated_density(layout: Layout, reports: Mapping[str, Report]) -> list[Issue]:
    """Audit evaluated-only evidence; never upgrade a legacy report to v2 proof."""
    from .density_model import validate_density_config
    issues = validate_density_config(layout)
    digest = layout_digest(layout)
    for sector, report in reports.items():
        if report.get('layout_sha256') != digest:
            issues.append(Issue('LAYOUT_MISMATCH', sector, 'semantic layout digest missing or different'))
            continue
        bounds = report.get('evaluated_bounds', {})
        for obj in report.get('objects', []):
            if not obj.get('mesh'):
                continue
            if (obj['mesh'] not in bounds or not obj.get('vertices') or not obj.get('faces')):
                issues.append(Issue('GEOMETRY_MISSING', obj.get('key', sector), 'evaluated mesh absent'))
            if obj.get('detail_profile') == 'v2':
                groups = obj.get('detail_groups') or []
                if not groups:
                    issues.append(Issue('DETAIL_MISSING', obj.get('key', sector), 'no evaluated detail groups'))
                else:
                    try:
                        envelope = bounds[obj['mesh']]
                        ids = set()
                        for group in groups:
                            if (group['id'] in ids or group['category'] not in CATEGORIES
                                    or not group['part_indices'] or
                                    len(group['part_indices']) != len(group['part_bounds'])
                                    or group['face_count'] < 1):
                                raise ValueError('duplicate or empty group')
                            ids.add(group['id'])
                            for part in group['part_bounds']:
                                for i in range(3):
                                    low, high = part['minimum'][i], part['maximum'][i]
                                    if (not math.isfinite(low) or not math.isfinite(high)
                                            or low >= high or
                                            low < envelope['minimum'][i]-1e-4 or
                                            high > envelope['maximum'][i]+1e-4 or
                                            low < group['bounds']['minimum'][i]-1e-4 or
                                            high > group['bounds']['maximum'][i]+1e-4):
                                        raise ValueError('group part outside evaluated bounds')
                    except (ValueError, KeyError, TypeError, IndexError) as exc:
                        issues.append(Issue('DETAIL_INVALID', obj.get('key', sector), str(exc)))
    for p in layout.placements:
        if p.params.get('detail_profile') != 'v2':
            continue
        report = reports.get(p.sector, {})
        if report.get('layout_sha256') != digest:
            if p.sector not in reports:
                issues.append(Issue('LAYOUT_MISMATCH', p.sector, 'evaluated report missing'))
            continue
        matches = [obj for obj in report.get('objects', []) if (obj.get('placement_key') or obj.get('key')) == p.key]
        if len(matches) != 1:
            issues.append(Issue('PLACEMENT_MISSING', p.key, 'v2 placement missing or duplicated'))
        elif (matches[0].get('variant') != p.params.get('variant') or
              not matches[0].get('detail_groups')):
            issues.append(Issue('DETAIL_MISSING', p.key, 'variant or evaluated groups missing'))
    # Check each realized low part separately: a combined mesh AABB bridges
    # genuinely open frontages and must not fabricate a solid obstruction.
    from .spatial import validate_clearance
    from .types import Bounds3
    for sector, report in reports.items():
        if report.get('layout_sha256') != digest:
            continue
        for obj in report.get('objects', []):
            key = obj.get('placement_key')
            if obj.get('detail_profile') != 'v2' or not key:
                continue
            for group in obj.get('detail_groups', []):
                for raw in group.get('part_bounds', []):
                    try:
                        b = Bounds3(tuple(raw['minimum']), tuple(raw['maximum']))
                        issues.extend(validate_clearance(layout, {key: b}))
                    except (TypeError, ValueError, KeyError) as exc:
                        issues.append(Issue('GEOMETRY_MISSING', key, str(exc)))
    return issues
