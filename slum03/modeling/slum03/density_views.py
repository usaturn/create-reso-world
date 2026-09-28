"""Shared Root-space cameras for offline comparison and live read-only QA."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from .native.common import slot_key_by_name
from .types import Layout, Manifest, Vec3

# Eye positions in local Resonite coordinates, looking inward to real selected
# placements; near eyes are 3m from nominal facade, street eyes are wider.
# The position of each camera is derived from the saved Layout, not the old run.
_DENSITY_VIEWS = (
    ('density-ruin-near', 'ruin-west', (12, 1.6, 3), (0, 5, 0)),
    ('density-shack-near', 'shack-row', (0, 1.6, 9), (0, 2.3, 0)),
    ('density-market-inward', 'market-west', (0, 1.6, 5), (0, 1.5, 0)),
    ('density-west-street', 'ruin-west', (18, 1.6, 3), (0, 8, 0)),
    ('density-east-lane', 'market-west', (12, 1.6, 16), (0, 1.5, 0)),
)


def density_cameras(layout: Layout, root_position: Vec3) -> dict[str, dict]:
    """World-space camera schema; eyes and targets both receive Root once."""
    placements = {p.key: p for p in layout.placements}
    if layout.density is None or layout.density.stage not in ('representative', 'full'):
        raise ValueError('density cameras require a representative/full layout')
    if any(key not in placements or key not in layout.density.selected_keys
           for _, key, _, _ in _DENSITY_VIEWS):
        raise ValueError('missing selected density camera subject')
    def point(origin, offset):
        return [root_position[i] + origin[i] + offset[i] for i in range(3)]
    return {name: {'position': point(placements[key].origin, eye),
                   'target': point(placements[key].origin, target),
                   'fieldOfView': 60, 'width': 768, 'height': 512,
                   'representative': True}
            for name, key, eye, target in _DENSITY_VIEWS}


def add_density_checks(manifest: Manifest, layout: Layout) -> None:
    """Extend only QA; preserve all original camera, tests and content declarations."""
    cameras = density_cameras(layout, tuple(manifest['slot']['position']))
    for key, camera in cameras.items():
        if key in manifest.get('cameras', {}) and manifest['cameras'][key] != camera:
            raise ValueError(f'camera key conflict: {key}')
    assertions = [{'target': '$slot:' + slot_key_by_name(manifest, key), 'exists': True}
                  for key in ('ruin-west', 'shack-row', 'market-west')]
    name = 'selected density placements exist (structural only)'
    tests = manifest.setdefault('tests', [])
    if not any(t.get('name') == name for t in tests):
        tests.append({'name': name, 'assertions': assertions})
    elif next(t for t in tests if t.get('name') == name)['assertions'] != assertions:
        raise ValueError('density test name conflict')
    manifest.setdefault('cameras', {}).update(cameras)


def review_manifest(source: Manifest, layout: Layout) -> Manifest:
    """Construct an isolated QA-only revision; never mutate the reviewed input."""
    result = copy.deepcopy(source)
    add_density_checks(result, layout)
    if {k: v for k, v in result.items() if k not in ('cameras', 'tests')} != {
            k: v for k, v in source.items() if k not in ('cameras', 'tests')}:
        raise ValueError('review revision changed content')
    return result


def write_review(source: Path, layout_path: Path, output: Path, evidence_dir: Path) -> dict:
    """Persist a separate QA revision with independent source/final byte attestation."""
    from .candidate_scope import check_candidate_scope
    from .layout import read_layout
    from .pipeline import _validate_final
    source, output, evidence_dir = Path(source), Path(output), Path(evidence_dir)
    if source.parent.resolve() != output.parent.resolve():
        raise ValueError('review manifest must remain beside source asset paths')
    provenance = output.with_name(output.stem + '-provenance.json')
    if any(p.exists() for p in (output, provenance, evidence_dir)):
        raise FileExistsError('review candidate/evidence already exists')
    layout = read_layout(Path(layout_path))
    original = json.loads(source.read_text(encoding='utf-8'))
    baseline_path = Path('content/slum03/density-baseline.json')
    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
    issues = check_candidate_scope(baseline, original, layout, source.parent, baseline_dir=baseline_path.parent)
    if issues:
        raise ValueError(f'original candidate scope failed: {issues[:3]}')
    reviewed = review_manifest(original, layout)
    _validate_final(reviewed)
    # review_manifest already checked every non-QA declaration for equality.
    content = json.dumps(reviewed, ensure_ascii=False, indent=2) + '\n'
    digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    evidence_dir.mkdir(parents=True)
    output.write_text(content, encoding='utf-8')
    scope = {'source': str(source), 'source_sha256': source_digest, 'candidate': str(output),
             'candidate_sha256': digest, 'layout': str(layout_path),
             'layout_sha256': hashlib.sha256(Path(layout_path).read_bytes()).hexdigest(),
             'protected_changes': 0, 'asset_changes': 0, 'slot_changes': 0,
             'component_changes': 0, 'geometry_changes': 0, 'issues': [],
             'qa_added_cameras': sorted(set(reviewed['cameras']) - set(original['cameras'])),
             'qa_added_tests': [t['name'] for t in reviewed['tests'][len(original['tests']):]]}
    (evidence_dir / 'scope-report.json').write_text(json.dumps(scope, indent=2) + '\n')
    provenance.write_text(json.dumps({'status': 'OFFLINE QA CANDIDATE', 'liveApplied': False,
        'currentReflectionValidated': False, **scope}, indent=2) + '\n')
    (evidence_dir / 'acceptance.json').write_text(json.dumps({
        'stage': layout.density.stage, 'scope': layout.density.stage,
        'manifest_sha256': digest, 'status': 'pending', 'evidence': {
            'visual': {'status': 'pending', 'paths': [], 'subject_visible': None, 'exposure_usable': None},
            'walk': {'status': 'pending', 'paths': []},
            'resources': {'status': 'pending', 'paths': []}},
        'confirmed_by': None, 'confirmed_at': None}, indent=2) + '\n')
    return scope
