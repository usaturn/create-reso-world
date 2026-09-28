"""Fail-closed offline density candidate build; no state, promotion or live calls."""
from __future__ import annotations

import hashlib
import json
import math
import copy
import os
from pathlib import Path

from .candidate_scope import compose_candidate, check_candidate_scope, _file
from .density_metrics import density_report, layout_digest
from .layout import read_layout
from .pipeline import _reports, _count
from .verify_assets import verify_assets


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(stage: str, baseline: Path, source: Path, run: str, root_y: float):
    if stage not in ('representative', 'full'):
        raise ValueError('blockout is not a density candidate stage')
    if not run or run in ('.', '..') or '/' in run or '\\' in run:
        raise ValueError('run must be a unique single directory name')
    if not math.isfinite(root_y) or root_y != 4.5:
        raise ValueError('root position must remain [0, 4.5, 0]')
    layout = read_layout(source)
    if not layout.density or layout.density.stage != stage:
        raise ValueError('stage does not match saved Layout')
    if stage == 'representative' and set(layout.density.selected_keys) != {'ruin-west', 'shack-row', 'market-west'}:
        raise ValueError('representative layout must select precisely the three protected placements')
    if baseline.parent.resolve() != Path('content/slum03').resolve():
        raise ValueError('baseline must remain beside canonical manifest')
    if not baseline.is_file():
        raise FileNotFoundError(baseline)
    if any(p.exists() for p in (Path('artifacts/slum03') / run,
                                 Path('content/slum03/bundles') / run,
                                 Path('content/slum03') / f'{run}-candidate.json',
                                 Path('content/slum03') / f'{run}-raw-draft.json')):
        raise FileExistsError(f'run already exists: {run}')
    return layout


def finalize(stage: str, baseline: Path, source: Path, run: str, root_y: float,
             artifact: Path, bundles: Path, manifest: dict) -> dict:
    """Write raw draft, independently validate evaluated assets and protect baseline."""
    from .pipeline import write_unified_manifest
    layout_path = artifact / 'layout.json'
    layout = read_layout(layout_path)
    if layout.density is None or layout.density.stage != stage:
        raise ValueError('copied Layout changed stage')
    reports = _reports(artifact, layout, bundles)
    if verify_assets(layout, reports):
        raise ValueError('evaluated assets invalid')
    report = density_report(layout, reports, 'evaluated')
    if report['issues']:
        raise ValueError(f'evaluated density failed: {report["issues"][:5]}')
    draft = Path('content/slum03') / f'{run}-raw-draft.json'
    candidate = Path('content/slum03') / f'{run}-candidate.json'
    if candidate.exists():
        raise FileExistsError('candidate already exists')
    if draft.exists():
        expected = copy.deepcopy(manifest)
        for asset in expected['assets'].values():
            asset['source'] = os.path.relpath(asset['source'], draft.parent.resolve())
        expected.pop('limits', None)
        expected['limits'] = {'expandedNodes': math.ceil(_count(expected) * 1.2)}
        if json.loads(draft.read_text()) != expected:
            raise ValueError('existing raw draft differs from current regenerated manifest')
    else:
        write_unified_manifest(manifest, draft)
    scope = compose_candidate(baseline, draft, layout, candidate)
    draft_data = json.loads(draft.read_text())
    result = json.loads(candidate.read_text())
    # Every resource must match the freshly exported run, including retained old sources.
    comparison = {}
    for key, asset in result['assets'].items():
        fresh = draft_data['assets'].get(key)
        if not fresh or {k: v for k, v in asset.items() if k != 'source'} != {k: v for k, v in fresh.items() if k != 'source'}:
            raise ValueError(f'no current export for candidate asset: {key}')
        old_source, old_hash = _file(candidate.parent, asset['source'])
        new_source, new_hash = _file(draft.parent, fresh['source'])
        if old_hash != new_hash:
            raise ValueError(f'candidate resource differs from new export: {key}')
        comparison[key] = {'candidate_source': old_source, 'draft_source': new_source,
                           'sha256': old_hash, 'origin': scope['asset_sources'][key]['origin']}
    issues = check_candidate_scope(json.loads(baseline.read_text()), result, layout, candidate.parent)
    if issues:
        raise ValueError(f'scope changed: {issues[:5]}')
    report['references'] = {'layout': {'path': str(layout_path), 'sha256': sha(layout_path),
                                        'hash_basis': 'saved-file-bytes', 'semantic_sha256': layout_digest(layout)},
                            'build': {sector: {'path': str(artifact / f'{sector}-report.json'),
                                               'sha256': sha(artifact / f'{sector}-report.json')} for sector in reports},
                            'export': {sector: {'path': str(bundles / sector / 'report.json'),
                                                'sha256': sha(bundles / sector / 'report.json')} for sector in reports}}
    (artifact / 'density-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (artifact / 'scope-report.json').write_text(json.dumps({'protected_changes': 0, 'protected_updates': 0, 'protected_deletes': 0, 'protected_asset_changes': 0, 'issues': [],
        'selected_nodes': scope['selected_nodes'],
        'raw_ignored_empty_provider_nodes': scope['raw_ignored_empty_provider_nodes'],
        'asset_matches_new_export': comparison}, ensure_ascii=False, indent=2) + '\n')
    provenance = {'status': 'OFFLINE PROTECTED CANDIDATE', 'liveApplied': False,
                  'currentReflectionValidated': False, 'baseline': {'path': str(baseline), 'sha256': sha(baseline)},
                  'draft': {'path': str(draft), 'sha256': sha(draft)},
                  'candidate': {'path': str(candidate), 'sha256': sha(candidate)},
                  'layout': report['references']['layout'], 'rootPosition': [0, root_y, 0],
                  'object_sources': scope['object_sources'], 'asset_sources': comparison}
    (candidate.with_name(candidate.stem + '-provenance.json')).write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + '\n')
    return {'run': run, 'candidate': str(candidate), 'draft': str(draft), 'scope': str(artifact / 'scope-report.json'),
            'assets': len(comparison), 'protected_changes': 0}
