"""Offline evaluated asset report validation; not a runtime visual or walk check."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from collections.abc import Mapping

from .types import Bounds3, Issue, Layout, Report
from .sectors import SECTORS
from .layout import read_layout
from .spatial import validate_clearance


def semantic_bounds(reports: Mapping[str, Report]) -> dict[str, Bounds3]:
    """Union named mesh bounds by placement_key; keep every ungrouped blocker."""
    result: dict[str, Bounds3] = {}
    for sector, report in reports.items():
        by_mesh = {entry.get('mesh'): entry for entry in report.get('objects', []) if entry.get('mesh')}
        for mesh, raw in report.get('evaluated_bounds', {}).items():
            b = Bounds3(tuple(raw['minimum']), tuple(raw['maximum']))
            entry = by_mesh.get(mesh, {})
            key = entry.get('placement_key') or entry.get('key') or mesh
            # Trees and patch geometry are sector-owned by the same forest placement.
            if sector == 'backdrop-west-south' and mesh.startswith(('west-city-', 'south-city-')):
                key = 'west-city' if mesh.startswith('west-city-') else 'south-city'
            if sector == 'forest' and (entry.get('kind') in ('tree', 'canopy-patch') or mesh.startswith('forest-')):
                key = 'forest'
            old = result.get(key)
            if old:
                b = Bounds3(tuple(min(a, c) for a, c in zip(b.minimum, old.minimum)),
                            tuple(max(a, c) for a, c in zip(b.maximum, old.maximum)))
            result[key] = b
    return result


def verify_assets(layout: Layout, reports: Mapping[str, Report]) -> list[Issue]:
    issues: list[Issue] = []
    for sector in SECTORS:
        report = reports.get(sector)
        if report is None:
            issues.append(Issue('SECTOR_MISSING', sector, 'no build report'))
            continue
        if report.get('sector') != sector or not report.get('export_collection'):
            issues.append(Issue('REPORT_INVALID', sector, 'wrong sector or export collection'))
        if not report.get('objects') or not report.get('evaluated_bounds'):
            issues.append(Issue('SECTOR_EMPTY', sector, 'no evaluated export meshes'))
        if not report.get('materials'):
            issues.append(Issue('MATERIAL_MISSING', sector, 'no evaluated materials'))
        for field in ('triangles', 'vertices', 'submeshes'):
            if not isinstance(report.get(field), int) or report[field] <= 0:
                issues.append(Issue('REPORT_INVALID', sector, f'no {field}'))
        for error in report.get('errors', []):
            issues.append(Issue('BUILD_ERROR', error.get('object_key', sector), error.get('message', str(error))))
        for error in report.get('uv_issues', []):
            issues.append(Issue('UV_MISSING', error.get('object_key', sector), error.get('message', str(error))))
        names = {e.get('key') for e in report.get('objects', [])}
        for p in layout.placements:
            if p.sector != sector:
                continue
            if p.key in names:
                continue
            # The scatter and backdrop/forest placements intentionally expand
            # into many independently editable objects rather than one mesh.
            prefix = {'plaza-rubble-west': 'plaza-rubble-west-',
                      'plaza-rubble-east': 'plaza-rubble-east-',
                      'forest': 'forest-', 'north-towers': 'north-highrise-',
                      'west-city': 'west-city-', 'south-city': 'south-city-'}.get(p.key)
            if prefix and any(isinstance(n, str) and n.startswith(prefix) for n in names):
                continue
            issues.append(Issue('PLACEMENT_MISSING', p.key, f'missing required {sector} placement'))
        bounds = report.get('evaluated_bounds', {})
        for entry in report.get('objects', []):
            mesh = entry.get('mesh')
            if mesh and mesh not in bounds:
                issues.append(Issue('BOUNDS_MISSING', mesh, 'no evaluated mesh bounds'))
    try:
        # Clearance requires individual realized meshes. A union of disjoint city
        # buildings would fill the empty gaps and fabricate a route collision.
        individual = {}
        for report in reports.values():
            for key, raw in report.get('evaluated_bounds', {}).items():
                if key in individual:
                    issues.append(Issue('BOUNDS_DUPLICATE', key, 'mesh name repeated across sectors'))
                individual[key] = Bounds3(tuple(raw['minimum']), tuple(raw['maximum']))
        issues.extend(validate_clearance(layout, individual))
    except (KeyError, ValueError, TypeError) as exc:
        issues.append(Issue('REPORT_INVALID', 'evaluated_bounds', str(exc)))
    return issues


def compare_geometry_exports(first: Path, second: Path) -> list[Issue]:
    """Exact decoded geometry comparison (including floats, UV order, normals and color).

    Each directory is a separately regenerated export root; filenames are
    relative within that root. JSON whitespace and export timestamps do not
    affect mesh content; no numeric quantization or rounding is permitted.
    """
    if first.resolve() == second.resolve():
        return [Issue('COMPARISON_NOT_INDEPENDENT', str(first), 'same export directory on both sides')]
    a = {str(p.relative_to(first)): p for p in first.rglob('*.mesh.json')}
    b = {str(p.relative_to(second)): p for p in second.rglob('*.mesh.json')}
    issues = [Issue('GEOMETRY_MISSING', key, 'mesh only in one export') for key in sorted(a.keys() ^ b.keys())]
    if not a or not b:
        issues.append(Issue('GEOMETRY_MISSING', str(first), 'no mesh files in one or both exports'))
    for key in sorted(a.keys() & b.keys()):
        try:
            mesh_a = json.loads(a[key].read_text(encoding='utf-8'))
            mesh_b = json.loads(b[key].read_text(encoding='utf-8'))
            # Compare complete mesh payload (including all vertex attributes and submesh ordering).
            if mesh_a != mesh_b:
                issues.append(Issue('GEOMETRY_CHANGED', key, 'vertex or submesh payload differs'))
        except (ValueError, OSError) as exc:
            issues.append(Issue('GEOMETRY_INVALID', key, str(exc)))
    return issues


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, required=True)
    p.add_argument('--layout', type=Path, required=True)
    args = p.parse_args()
    reports = {}
    for sector in SECTORS:
        path = args.reports / f'{sector}-report.json'
        if path.is_file():
            reports[sector] = json.loads(path.read_text(encoding='utf-8'))
    issues = verify_assets(read_layout(args.layout), reports)
    print(json.dumps({'status': 'fail' if issues else 'pass', 'issues': [i.__dict__ for i in issues]}, ensure_ascii=False))
    if issues:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
