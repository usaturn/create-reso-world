"""Manifest-bound human acceptance cannot be inferred from structural or offline evidence."""
from dataclasses import replace
from pathlib import Path
from modeling.slum03.layout import read_layout
from modeling.slum03.density_acceptance import validate_acceptance, summarize_density_delivery

HASH = 'a' * 64


def record(stage='representative', **updates):
    r = {'stage': stage, 'manifest_sha256': HASH, 'status': 'pass',
         'evidence': {'visual': {'status': 'pass', 'paths': ['capture.png'], 'subject_visible': True,
                                 'exposure_usable': True},
                      'walk': {'status': 'pass', 'paths': ['walk.md']},
                      'resources': {'status': 'pass', 'paths': ['resources.json']}},
         'confirmed_by': 'explicit user', 'confirmed_at': '2026-09-28T20:00:00Z', 'scope': stage}
    r.update(updates)
    return r


def test_wrong_hash_or_reused_stage_is_rejected():
    assert validate_acceptance(record(manifest_sha256='b'*64), HASH, 'representative')
    assert validate_acceptance(record(), HASH, 'full')
    assert validate_acceptance(record(scope='full'), HASH, 'representative')


def test_timeout_or_unseen_or_dark_subject_cannot_pass():
    for change in ({'status': 'timeout'}, {'subject_visible': None}, {'exposure_usable': False}):
        r = record()
        r['evidence']['visual'].update(change)
        assert validate_acceptance(r, HASH, 'representative')


def test_unconfirmed_or_visual_only_cannot_claim_other_checks():
    assert validate_acceptance(record(confirmed_by=None), HASH, 'representative')
    r = record()
    r['evidence'].pop('walk')
    assert validate_acceptance(r, HASH, 'representative')
    r = record(status='pending', confirmed_by=None, confirmed_at=None)
    assert not validate_acceptance(r, HASH, 'representative')


def test_density_summary_keeps_legacy_and_strict_forest_failures_independent():
    layout = read_layout(Path('content/slum03/density-representative-layout.json'))
    live = {key: {'status': 'pass', 'evidence': ['live.json']} for key in
            ('apply', 'reapply', 'structure', 'visual', 'walk', 'portability', 'resources')}
    live['manifest_sha256'] = HASH
    live['portability'] = {'status': 'fail', 'evidence': ['strict-audit.json']}
    live['forest'] = {'status': 'fail', 'evidence': ['forest.json']}
    result = summarize_density_delivery(layout, {}, live, record())
    assert result['density']['status'] == 'pass'
    assert result['checks']['portability']['status'] == 'fail'
    assert result['checks']['forest']['status'] == 'fail'
    assert result['status'] == 'fail'
    pending = summarize_density_delivery(layout, {}, {'manifest_sha256': HASH}, record(status='pending', confirmed_by=None, confirmed_at=None))
    assert pending['density']['status'] == 'pending' and pending['status'] == 'pending'
    full_layout = replace(layout, density=replace(layout.density, stage='full'))
    assert summarize_density_delivery(full_layout, {}, {'manifest_sha256': HASH}, record())['density']['status'] == 'fail'
