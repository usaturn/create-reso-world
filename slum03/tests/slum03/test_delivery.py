"""Delivery gates: losing evidence, build reports or a QA check cannot yield pass."""
import copy
import json
from pathlib import Path

from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import SECTORS
from modeling.slum03.delivery import summarize_delivery, declare_delivery_checks
from modeling.slum03.native.common import walk
from modeling.slum03.pipeline import build_unified_manifest


def _passed():
    return {'status': 'pass', 'evidence': ['evidence/report.json'], 'details': {}}


def _reports():
    return {sector: {'sector': sector, 'errors': [], 'warnings': [],
                     'report_path': f'artifacts/slum03/build/{sector}-report.json'} for sector in SECTORS}


def test_missing_live_visual_check_remains_pending():
    checks = {key: _passed() for key in ('apply', 'reapply', 'structure', 'walk', 'portability', 'resources')}
    r = summarize_delivery(build_layout(), _reports(), checks)
    assert r['status'] == 'pending'
    assert r['checks']['visual']['status'] == 'pending'


def test_import_success_is_not_visual_success():
    r = summarize_delivery(build_layout(), {}, {'apply': _passed()})
    assert r['status'] == 'pending'
    assert r['checks']['visual']['status'] == 'pending'
    assert r['checks']['build']['status'] == 'pending'


def test_portability_warning_is_not_pass():
    checks = {key: _passed() for key in ('apply', 'reapply', 'structure', 'visual', 'walk', 'resources')}
    checks['portability'] = {'status': 'pass', 'evidence': ['evidence/reload.json'], 'details': {'warning': 'reload not tested'}}
    r = summarize_delivery(build_layout(), _reports(), checks)
    assert r['status'] == 'pending'
    assert r['checks']['portability']['status'] == 'pending'


def test_elapsed_and_task_times_are_distinct():
    checks = {key: _passed() for key in ('apply', 'reapply', 'structure', 'visual', 'walk', 'portability', 'resources')}
    checks['timing'] = {'elapsed_seconds': 120, 'task_times_seconds': {'build': 55, 'qa': 35}}
    r = summarize_delivery(build_layout(), _reports(), checks)
    assert r['status'] == 'pass'
    assert r['timing'] == checks['timing']
    assert r['timing']['elapsed_seconds'] != sum(r['timing']['task_times_seconds'].values())


def test_fail_dominates_pending_and_invalid_status_does_not_pass():
    r = summarize_delivery(build_layout(), {}, {'walk': {'status': 'fail', 'evidence': ['walk.txt'], 'details': {'issue': 'blocked'}},
                                                 'visual': {'status': 'unsupported', 'evidence': ['image.png'], 'details': {}}})
    assert r['status'] == 'fail'
    assert r['checks']['walk']['details']['issue'] == 'blocked'
    assert r['checks']['visual']['status'] == 'pending'


def test_build_errors_and_unreviewed_warnings_do_not_pass():
    reports = _reports()
    reports['plaza']['errors'] = [{'code': 'UV_DEGENERATE'}]
    assert summarize_delivery(build_layout(), reports, {})['checks']['build']['status'] == 'fail'
    reports['plaza']['errors'] = []
    reports['plaza']['warnings'] = [{'code': 'SECTION_COUNT'}]
    r = summarize_delivery(build_layout(), reports, {'resources': _passed()})
    assert r['checks']['build']['status'] == 'pending'
    assert r['checks']['build']['details']['warnings']


def test_world_cameras_have_root_height_and_six_distinct_targets():
    manifest = json.loads(Path("content/slum03/task11-fix2-20260928T0356-candidate.json").read_text())
    declare_delivery_checks(manifest, build_layout())
    assert set(manifest['cameras']) == {'plaza-north', 'east-forest', 'bridge-checkpoint',
                                       'west-city', 'south-market', 'ar-hero'}
    assert manifest['cameras']['plaza-north']['position'] == [0, 6.1, -6]
    assert manifest['cameras']['plaza-north']['target'] == [0, 364.5, 330]
    assert manifest['cameras']['bridge-checkpoint']['target'] == [78, 11.5, 90]
    assert manifest['cameras']['east-forest']['target'] == [155, 19.5, 0]
    assert all(v['position'] != v['target'] for v in manifest['cameras'].values())
    assert any(a['target'] == '$slot:root' for t in manifest['tests'] for a in t['assertions'])
    assert any(a['target'].startswith('$component:') for t in manifest['tests'] for a in t['assertions'])
    assert len({t['name'] for t in manifest['tests']}) == len(manifest['tests'])


def test_panners_have_separate_stable_slots_and_preserve_driven_references(tmp_path):
    base = Path('content/slum03/bundles/task11-fix2-20260928T0356')
    layout = build_layout()
    reports = {sector: json.loads((Path("artifacts/slum03/task11-fix2-20260928T0356") / f"{sector}-report.json").read_text()) for sector in SECTORS}
    manifest = build_unified_manifest(base, layout, reports, (0, 4.5, 0))
    first = json.dumps(manifest, sort_keys=True)
    again = build_unified_manifest(base, layout, reports, (0, 4.5, 0))
    assert json.dumps(again, sort_keys=True) == first
    holders = [n for n in walk(manifest) if any(c['type'] == 'FrooxEngine.Panner2D'
                                                      for c in n.get('components', []))]
    assert len(holders) == 4
    assert all(len(n['components']) == 1 for n in holders)
    assert len({n['slot']['key'] for n in holders}) == 4
    component_keys = {c['key'] for n in walk(manifest) for c in n.get('components', [])}
    assert all(c['fields']['_target'].split('.')[0].removeprefix('$member:') in component_keys
               for n in holders for c in n['components'])
    assert all(c['identityFields'] == ['_target'] for n in holders for c in n['components'])
    spin = [n for n in walk(manifest) if any(c['type'] == 'FrooxEngine.Spinner' for c in n.get('components', []))]
    assert len(spin) == 1 and 'rotation' not in spin[0]['slot']
    assert spin[0]['slot']['managedFields'] == ['position', 'scale']


def test_canonical_manifest_is_portable_and_contains_live_qa():
    path = Path('content/slum03/slum03.json')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    assert manifest['ownership'] == {'key': 'slum03'}
    assert manifest['slot']['position'] == [0, 4.5, 0]
    assert len(manifest['cameras']) == 6 and manifest['tests']
    assert len([a for a in manifest['assets'].values() if a['kind'] == 'mesh']) == 150
    assert all(not Path(a['source']).is_absolute() and
               (path.parent / a['source']).is_file() and
               'finalfix-m-20260928T0511' in a['source']
               for a in manifest['assets'].values())


def test_plural_live_warnings_with_valid_evidence_remain_pending():
    checks = {key: _passed() for key in ('apply', 'reapply', 'structure', 'visual', 'walk', 'portability', 'resources')}
    checks['visual'] = {'status': 'pass', 'evidence': ['evidence/image.png'],
                        'details': {'warnings': ['unverified material']}}
    assert summarize_delivery(build_layout(), _reports(), checks)['checks']['visual']['status'] == 'pending'


def test_delivery_resources_and_build_evidence_match_canonical_bundle():
    report = json.loads(Path('artifacts/slum03/delivery-report.json').read_text())
    run = 'finalfix-m-20260928T0511'
    summary = json.loads((Path('artifacts/slum03') / run / 'asset-summary.json').read_text())
    assert report['buildEvidence'][0] == f'artifacts/slum03/{run}/asset-summary.json'
    assert report['buildEvidence'][1] == f'artifacts/slum03/{run}/previews-bright/preview-report.json'
    assert Path(report['buildEvidence'][1]).is_file()
    assert report['checks']['resources']['details']['exportTotals'] == summary['exportTotals']
    assert report['checks']['build']['status'] == 'pass'
    assert len(report['checks']['build']['evidence']) == len(SECTORS)
    assert all(f'/{run}/' in path and Path(path).is_file()
               for path in report['checks']['build']['evidence'])
    assert report['checks']['apply']['status'] == 'pending'
    assert report['status'] == 'pending'
