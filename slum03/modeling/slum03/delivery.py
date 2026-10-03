"""Offline delivery summary and owned live QA declarations; no world mutation."""
from __future__ import annotations

from typing import Any, Mapping

from .native.common import slot_key_by_name, walk
from .sectors import SECTORS
from .types import Layout, Manifest, Report

LIVE_CHECKS = ('apply', 'reapply', 'structure', 'visual', 'walk', 'portability', 'resources')
# Local Resonite coordinates. The live camera schema uses Root-space position/target.
TARGETS = {
    'plaza-north': (0, 360, 330),
    'east-forest': (155, 15, 0),
    'bridge-checkpoint': (78, 7, 90),
    'west-city': (-135, 20, 0),
    'south-market': (0, 18, -140),
    'ar-hero': (-9, 4, -46),
}


def _status(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {'status': 'pending', 'evidence': [], 'details': {}}
    evidence = value.get('evidence', [])
    evidence = evidence if isinstance(evidence, list) else []
    evidence = [p for p in evidence if isinstance(p, str) and p.strip()]
    details = value.get('details', {})
    details = dict(details) if isinstance(details, Mapping) else {}
    status = value.get('status')
    if status not in ('pass', 'fail', 'pending') or (status == 'pass' and not evidence):
        status = 'pending'
    # Warning-bearing claims cannot be silently counted as verified success.
    if status == 'pass' and (details.get('warning') or details.get('warnings')):
        status = 'pending'
    return {'status': status, 'evidence': evidence, 'details': details}


def summarize_delivery(layout: Layout, build_reports: Mapping[str, Report],
                       live_results: Mapping[str, Any], *, manifest_sha256: str | None = None) -> Report:
    """An offline build and import cannot substitute for seven independent live checks."""
    checks = {key: _status(live_results.get(key)) for key in LIVE_CHECKS}
    if manifest_sha256 is not None and checks['portability']['status'] == 'pass':
        details = checks['portability']['details']
        if (details.get('save_reload_status') != 'pass' or
                details.get('saved_manifest_sha256') != manifest_sha256 or
                details.get('reloaded_manifest_sha256') != manifest_sha256):
            checks['portability']['status'] = 'pending'
            checks['portability']['details']['warning'] = 'save/reload not confirmed for current manifest'

    missing = [sector for sector in SECTORS if sector not in build_reports]
    errors = {sector: report.get('errors') for sector, report in build_reports.items()
              if isinstance(report, Mapping) and report.get('errors')}
    warnings = {sector: report.get('warnings') for sector, report in build_reports.items()
                if isinstance(report, Mapping) and report.get('warnings')}
    evidence = [report['report_path'] for sector in SECTORS
                if isinstance((report := build_reports.get(sector)), Mapping)
                and isinstance(report.get('report_path'), str) and report['report_path'].strip()
                and report.get('sector') == sector and isinstance(report.get('errors'), list)]
    build_status = ('fail' if errors else 'pass' if not missing and len(evidence) == len(SECTORS)
                    and not warnings else 'pending')
    checks['build'] = {'status': build_status, 'evidence': evidence,
                       'details': {'missing': missing, 'errors': errors, 'warnings': warnings}}
    statuses = {check['status'] for check in checks.values()}
    overall = 'fail' if 'fail' in statuses else 'pending' if 'pending' in statuses else 'pass'
    result: Report = {'status': overall, 'checks': checks, 'layout_seed': layout.seed}
    if isinstance(live_results.get('timing'), Mapping):
        t = live_results['timing']
        result['timing'] = {'elapsed_seconds': t.get('elapsed_seconds'),
                            'task_times_seconds': t.get('task_times_seconds', {})}
    return result


def declare_delivery_checks(manifest: Manifest, layout: Layout) -> None:
    """Install six Root-space camera bookmarks and read-only existence tests."""
    root = manifest['slot']['position']
    eyes = {v.key: v.eye for v in layout.viewpoints}
    manifest['cameras'] = {
        key: {'position': [root[i] + eyes[key][i] for i in range(3)],
              'target': [root[i] + target[i] for i in range(3)],
              'fieldOfView': 60, 'width': 768, 'height': 512,
              'representative': key == 'plaza-north'}
        for key, target in TARGETS.items()
    }
    assertions = [{'target': '$slot:root', 'exists': True}]
    for name in ('north-wall', 'yarol', 'bridge', 'checkpoint', 'river',
                 'market-product-holo', 'market-product-holo-driven'):
        assertions.append({'target': '$slot:' + slot_key_by_name(manifest, name), 'exists': True})
    for key in ('sector-forest', 'sector-backdrop-north', 'sector-backdrop-west-south'):
        if not any(n['slot']['key'] == key for n in walk(manifest)):
            raise ValueError(f'missing owned QA anchor {key}')
        assertions.append({'target': '$slot:' + key, 'exists': True})
    for n in walk(manifest):
        for component in n.get('components', []):
            if component['type'] in ('FrooxEngine.Spinner', 'FrooxEngine.Panner2D', 'FrooxEngine.TextRenderer'):
                assertions.append({'target': '$component:' + component['key'], 'exists': True})
    manifest['tests'] = [{'name': 'owned slum03 structural anchors and drivers', 'assertions': assertions}]
