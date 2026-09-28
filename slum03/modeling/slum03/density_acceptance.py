"""Validate human confirmation separately from structural and legacy delivery gates."""
from __future__ import annotations

import re
from collections.abc import Mapping
from .delivery import summarize_delivery, _status
from .types import Issue, Layout, Report

_SHA = re.compile(r'[0-9a-f]{64}\Z')


def validate_acceptance(record: Report, manifest_sha256: str, stage: str) -> list[Issue]:
    """A pending record may have incomplete evidence; a pass may not."""
    issues = []
    def invalid(code: str, message: str):
        issues.append(Issue(code, 'acceptance', message))
    if not isinstance(record, Mapping):
        return [Issue('ACCEPTANCE_RECORD', 'acceptance', 'missing acceptance record')]
    if stage not in ('representative', 'full') or record.get('stage') != stage or record.get('scope') != stage:
        invalid('ACCEPTANCE_STAGE', 'stage and scope must exactly match this build')
    if not isinstance(manifest_sha256, str) or not _SHA.fullmatch(manifest_sha256) or record.get('manifest_sha256') != manifest_sha256:
        invalid('ACCEPTANCE_HASH', 'approval must refer to exact candidate bytes')
    status = record.get('status')
    if status not in ('pass', 'fail', 'pending'):
        invalid('ACCEPTANCE_STATUS', 'unknown acceptance status')
    if status != 'pass':
        return issues
    if not all(isinstance(record.get(field), str) and record[field].strip()
               for field in ('confirmed_by', 'confirmed_at')):
        invalid('ACCEPTANCE_HUMAN', 'explicit human confirmation and time required')
    evidence = record.get('evidence')
    for key in ('visual', 'walk', 'resources'):
        check = evidence.get(key) if isinstance(evidence, Mapping) else None
        if (not isinstance(check, Mapping) or check.get('status') != 'pass' or
                not isinstance(check.get('paths'), list) or not check['paths'] or
                not all(isinstance(p, str) and p.strip() for p in check['paths'])):
            invalid('ACCEPTANCE_' + key.upper(), f'{key} independent passing evidence required')
        if key == 'visual' and (not isinstance(check, Mapping) or
                check.get('subject_visible') is not True or check.get('exposure_usable') is not True):
            invalid('ACCEPTANCE_VISIBILITY', 'actual subject and exposure must be inspected')
    return issues


def summarize_density_delivery(layout: Layout, build_reports: Mapping[str, Report],
                               live_results: Mapping[str, object], acceptance: Report) -> Report:
    """Never replace legacy seven checks, strict audit or forest by density status."""
    legacy = summarize_delivery(layout, build_reports, live_results)
    stage = layout.density.stage if layout.density else ''
    issues = validate_acceptance(acceptance, live_results.get('manifest_sha256'), stage)
    claimed = acceptance.get('status') if isinstance(acceptance, Mapping) else None
    density_status = 'fail' if issues and claimed == 'pass' else claimed if not issues else 'pending'
    density_status = density_status if density_status in ('pass', 'fail', 'pending') else 'pending'
    density = {'stage': stage, 'status': density_status,
               'manifest_sha256': live_results.get('manifest_sha256'),
               'issues': [vars(issue) for issue in issues], 'acceptance': acceptance}
    forest = _status(live_results.get('forest'))
    checks = {**legacy['checks'], 'forest': forest}
    statuses = {legacy['status'], forest['status'], density_status}
    return {**legacy, 'checks': checks, 'density': density,
            'status': 'fail' if 'fail' in statuses else 'pending' if 'pending' in statuses else 'pass'}
