"""Gate D2 live evidence is bound to the canonical manifest; nothing is upgraded to pass by inference."""
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path

import pytest

from modeling.slum03.density_acceptance import summarize_density_delivery, validate_acceptance
from modeling.slum03.layout import read_layout
from modeling.slum03.native.common import walk
from modeling.slum03.sectors import SECTORS

EVIDENCE = Path('tests/slum03/fixtures/density-gate-d2-evidence-redacted.json')
CANONICAL = Path('content/slum03/slum03.json')
BASELINE = Path('content/slum03/density-baseline.json')
RECORDS = Path('artifacts/slum03')
LIVE = RECORDS / 'live-verification.json'
REPORT = RECORDS / 'delivery-report.json'
APPLY_LOG = RECORDS / 'apply-log.md'
TIMING = RECORDS / 'timing.md'
# The Task 12 canonical (pre-density) manifest, later frozen as density-baseline.json.
SUPERSEDED_SHA = '2a048a15fd41de680964590c9182868e85bfd175e5fb12044b4824236c0e2bec'
SUPERSEDED_RUN = 'finalfix-m-20260928T0511'
WRITES = ('slotsCreated', 'slotsUpdated', 'componentsAdded', 'componentsUpdated',
          'slotsDeleted', 'componentsDeleted')


def _json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reapply_zero(counts):
    """True/False when every write/import counter is known; None when any is unknown."""
    if not isinstance(counts, Mapping):
        return None
    keys = WRITES + ('assetsImported',)
    if any(type(counts.get(key)) is not int for key in keys):
        return None
    return sum(counts[key] for key in WRITES) == 0 and counts['assetsImported'] == 0


@pytest.fixture(scope='module')
def evidence():
    return _json(EVIDENCE)


@pytest.fixture(scope='module')
def live():
    return _json(LIVE)


@pytest.fixture(scope='module')
def report():
    return _json(REPORT)


def _run(evidence):
    return RECORDS / evidence['candidate']['run']


def test_adopted_candidate_is_canonical_and_shares_the_base(evidence, live, report):
    candidate = Path(evidence['candidate']['path'])
    digest = evidence['candidate']['sha256']
    assert _sha(candidate) == digest
    assert CANONICAL.read_bytes() == candidate.read_bytes()
    assert _sha(CANONICAL) == digest
    # Review candidate -> protected candidate -> baseline: the same base as the superseded canonical.
    review = _json(candidate.with_name(candidate.stem + '-provenance.json'))
    assert review['candidate_sha256'] == digest
    assert _sha(review['source']) == review['source_sha256']
    protected = _json(Path(review['source']).with_name(Path(review['source']).stem + '-provenance.json'))
    assert protected['baseline']['path'] == str(BASELINE)
    assert protected['baseline']['sha256'] == _sha(BASELINE) == SUPERSEDED_SHA
    assert protected['candidate']['sha256'] == review['source_sha256']
    assert live['manifest_sha256'] == digest
    assert live['candidate'] == evidence['candidate']
    assert live['base_manifest'] == {'path': str(BASELINE), 'sha256': SUPERSEDED_SHA}
    assert report['manifest'] == str(CANONICAL)
    assert report['density']['manifest_sha256'] == digest
    acceptance = report['density']['acceptance']
    assert acceptance['manifest_sha256'] == digest
    assert not validate_acceptance(acceptance, digest, 'full')


def test_reapply_writes_and_imports_are_zero_from_recorded_counts(evidence, live, report):
    counts = live['reapply']['counts']
    writes = sum(counts[key] for key in WRITES)
    assert writes == 0
    assert counts['assetsImported'] == 0
    assert reapply_zero(counts) is True
    assert all(counts[key] == evidence['reapply']['counts'][key] for key in WRITES + ('assetsImported',))
    assert live['reapply']['status'] == report['checks']['reapply']['status'] == 'pass'
    assert report['checks']['reapply']['details']['counts'] == counts
    assert live['diff_after']['creates'] == live['diff_after']['updates'] == live['diff_after']['deletes'] == 0


@pytest.mark.parametrize('counts', [None, {}, {'slotsCreated': 0},
                                    {**{key: 0 for key in WRITES}, 'assetsImported': None}])
def test_unknown_reapply_counts_are_not_treated_as_zero(counts):
    assert reapply_zero(counts) is None


def test_committed_reapply_pass_requires_known_zero_counts(live, report):
    known = reapply_zero(live['reapply'].get('counts'))
    if known is not True:
        assert report['checks']['reapply']['status'] != 'pass'
    else:
        assert report['checks']['reapply']['status'] == 'pass'


def test_export_live_and_report_counts_correspond(evidence, live, report):
    manifest = _json(CANONICAL)
    run = _run(evidence)
    summary = _json(run / 'asset-summary.json')
    meshes = sum(asset['kind'] == 'mesh' for asset in manifest['assets'].values())
    slots = len(list(walk(manifest)))
    assert meshes == summary['exportTotals']['meshes'] == summary['comparison']['meshCount']
    audit = evidence['strict_item_audit']
    applied, recorded = live['apply']['counts'], live['reapply']['counts']
    again = evidence['reapply']['counts']
    assert applied == evidence['apply']['counts']
    assert all(recorded[key] == again[key] for key in recorded)
    assert applied['assetsImported'] + applied['assetsUnchanged'] == meshes
    assert again['assetsUnchanged'] == live['reapply']['unchanged_assets'] == meshes
    assert applied['slotsCreated'] + applied['slotsUnchanged'] == slots == audit['slots']
    assert again['slotsUnchanged'] == live['reapply']['unchanged_slots'] == slots
    live_components = applied['componentsAdded'] + applied['componentsUpdated'] + applied['componentsUnchanged']
    assert live_components == again['componentsUnchanged'] == audit['components']
    assert live['reapply']['unchanged_components'] == live_components
    assert report['checks']['apply']['details']['counts'] == applied
    assert report['checks']['resources']['details']['exportTotals'] == summary['exportTotals']
    assert report['checks']['resources']['details']['live_mesh_assets'] == meshes
    assert report['buildEvidence'][0] == str(run / 'asset-summary.json')
    assert len(report['checks']['build']['evidence']) == len(SECTORS)
    assert all(path.startswith(str(run) + '/') and Path(path).is_file()
               for path in report['checks']['build']['evidence'])
    assert live['diff_before']['outside_Slum03_Slum'] == 0
    assert live['structure']['total'] == live['structure']['passed_count'] == len(manifest['tests'])


def test_remaining_grabbable_failure_keeps_overall_from_pass(evidence, live, report):
    assert evidence['strict_item_audit']['remaining_failure'] == 'ITEM_GRABBABLE_MISSING'
    assert [i['code'] for i in live['strict_audit']['remaining_issues']] == ['ITEM_GRABBABLE_MISSING']
    assert live['strict_audit']['status'] == 'fail'
    assert live['strict_audit']['unmatched_roles'] == []
    assert report['checks']['portability']['status'] == 'fail'
    overall = report['status']
    assert overall != 'pass'
    # The committed report is exactly what the Task 7 summarizer yields for its own inputs.
    run = _run(evidence)
    layout = read_layout(run / 'layout.json')
    assert layout.density.stage == 'full'
    builds = {sector: {**_json(run / f'{sector}-report.json'),
                       'report_path': str(run / f'{sector}-report.json')} for sector in SECTORS}
    inputs = {key: report['checks'][key] for key in report['checks'] if key != 'build'}
    inputs['manifest_sha256'] = _sha(CANONICAL)
    again = summarize_density_delivery(layout, builds, inputs, report['density']['acceptance'])
    assert again['status'] == overall == 'fail'
    assert {k: v['status'] for k, v in again['checks'].items()} == {
        k: v['status'] for k, v in report['checks'].items()}
    assert again['checks']['build'] == report['checks']['build']
    assert again['density'] == report['density']


def test_human_results_are_recorded_independently(evidence, live, report):
    human = evidence['human']
    assert live['manual_visual'] == {'status': 'pass', 'source': human['visual']['source']}
    assert live['walk'] == {'status': 'pass', 'source': human['walk']['source']}
    assert live['save'] == {'status': 'done', 'source': human['save']['source']}
    assert live['reload'] == {'status': 'pending', 'source': human['reload']['source']}
    assert live['save_reload']['status'] == 'pending'
    assert live['capture']['status'] == 'not_run'
    checks = report['checks']
    assert checks['visual']['status'] == checks['walk']['status'] == 'pass'
    assert checks['visual']['details']['source'] == human['visual']['source']
    assert checks['walk']['details']['source'] == human['walk']['source']
    assert checks['portability']['details']['save_reload']['status'] == 'pending'
    assert checks['portability']['details']['save_reload']['save'] == 'done'
    assert checks['portability']['details']['save_reload']['reload'] == 'pending'
    assert checks['resources']['status'] == 'pending'
    acceptance = report['density']['acceptance']
    assert acceptance['evidence']['visual']['status'] == acceptance['evidence']['walk']['status'] == 'pass'
    assert acceptance['evidence']['resources']['status'] == 'pending'
    assert acceptance['status'] != 'pass' and report['density']['status'] == 'pending'
    # Retention of the previous version is history, never this version's save/reload result.
    previous = live['history']['gate_d']
    assert previous['save_reload_retention'] == {
        'status': 'pass', 'basis': evidence['earlier_gate_d']['save_reload_retention_prev_version']}
    assert previous['manifest_sha256'] != live['manifest_sha256']
    assert previous['visual'] == 'rejected'


def test_superseded_records_remain_only_as_history(evidence, live, report):
    digest = evidence['candidate']['sha256']
    assert live['manifest_sha256'] != SUPERSEDED_SHA
    current = json.dumps({k: v for k, v in report.items() if k != 'history'})
    assert SUPERSEDED_RUN not in current and SUPERSEDED_SHA not in current
    assert SUPERSEDED_RUN not in json.dumps({k: v for k, v in live.items() if k != 'history'})
    assert live['history']['task12_original']['manifest_sha256'] == SUPERSEDED_SHA
    assert live['history']['task12_original']['status'] == 'superseded'
    assert report['history']['task12_original']['manifest_sha256'] == SUPERSEDED_SHA
    assert report['history']['task12_original']['status'] == 'superseded'
    assert report['history']['gate_d']['manifest_sha256'] == live['history']['gate_d']['manifest_sha256']
    assert _sha(live['history']['gate_d']['candidate']) == live['history']['gate_d']['manifest_sha256']
    log = APPLY_LOG.read_text(encoding='utf-8')
    current_section = log.split('\n## ', 2)[1] if '\n## ' in log else ''
    assert 'Gate D2' in current_section and digest in current_section
    assert 'Task 10' in TIMING.read_text(encoding='utf-8')


RAW = re.compile(r'Reso_|ws://|wss://|localhost|127\.0\.0\.1|\bU-[A-Za-z0-9_-]{4,}|'
                 r'\bS-[0-9a-f]{8}-|:[0-9]{4,5}/|\bID[0-9A-F]{6,}')


@pytest.mark.parametrize('path', [EVIDENCE, LIVE, REPORT, APPLY_LOG, TIMING])
def test_tracked_records_contain_no_raw_live_identifiers(path):
    assert not RAW.findall(path.read_text(encoding='utf-8'))
