"""Density wire compatibility and fail-closed metadata validation."""
import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from modeling.slum03.density_model import REPRESENTATIVE_KEYS, stable_seed, validate_density_config
from modeling.slum03.layout import read_layout, validate_layout, write_layout
from modeling.slum03.types import (DensityConfig, DensityOpening, DensityRoute,
                                   DensityZone, RectXZ)


def _density():
    return DensityConfig('representative',
                         (DensityZone('west', RectXZ(-50, -20, -45, -15)),),
                         (DensityRoute('lane', 'alley', RectXZ(-20, -16, -40, -20),
                                       (DensityOpening(RectXZ(-20, -16, -32, -29), 'pedestrian access'),)),),
                         (RectXZ(-20, -16, -40, -20),), ('ruin-west',))


def test_legacy_layout_not_full_density(legacy_layout, legacy_reports, legacy_manifest):
    assert legacy_layout.density is None
    assert validate_density_config(legacy_layout) == []
    assert 'density' not in legacy_reports['ruins-west']
    assert legacy_manifest['ownership']['key'] == 'slum03'
    assert validate_layout(legacy_layout) == []


def test_density_round_trip_preserves_typed_metadata(tmp_path, legacy_layout):
    layout = replace(legacy_layout, density=_density())
    path = tmp_path / 'layout.json'
    write_layout(layout, path)
    assert read_layout(path) == layout
    assert json.loads(path.read_text())['density']['routes'][0]['openings'][0]['reason'] == 'pedestrian access'


def test_old_eight_positional_arguments_still_construct_layout(legacy_layout):
    assert type(legacy_layout)(*tuple(getattr(legacy_layout, k) for k in (
        'seed', 'district', 'plaza', 'clear', 'routes', 'placements', 'viewpoints', 'labels'))).density is None


@pytest.mark.parametrize('invalid', [
    lambda d: replace(d, stage='completed'),
    lambda d: replace(d, zones=(DensityZone('west', RectXZ(-50, -20, -45, -15)),) * 2),
    lambda d: replace(d, routes=d.routes * 2),
    lambda d: replace(d, routes=(replace(d.routes[0], purpose='road'),)),
    lambda d: replace(d, zones=(DensityZone('west', RectXZ(float('nan'), -20, -45, -15)),)),
    lambda d: replace(d, branch_clearances=(RectXZ(False, 2, -10, -4),)),
    lambda d: replace(d, routes=(replace(d.routes[0], openings=(
        DensityOpening(RectXZ(-20, -16, -32, -29), '  '),)),)),
])
def test_invalid_density_is_rejected_by_validation_and_writer(legacy_layout, tmp_path, invalid):
    layout = replace(legacy_layout, density=invalid(_density()))
    assert validate_density_config(layout)
    with pytest.raises(ValueError, match='invalid layout'):
        write_layout(layout, tmp_path / 'invalid.json')


@pytest.mark.parametrize(('field', 'value'), [
    ('stage', 'unknown'), ('stage', True), ('stage', None),
    ('branch_clearances', [{'x_min': 0, 'x_max': 3, 'z_min': 0, 'z_max': float('nan')}]),
    ('selected_keys', ''),
])
def test_invalid_density_json_is_rejected(legacy_layout, tmp_path, field, value):
    path = tmp_path / 'layout.json'
    write_layout(replace(legacy_layout, density=_density()), path)
    payload = json.loads(path.read_text())
    payload['density'][field] = value
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        read_layout(path)


def test_stable_seed_uses_utf8_sha256_and_is_process_independent():
    expected = int.from_bytes(hashlib.sha256('260927\0a\0wear'.encode('utf-8')).digest(), 'big')
    first = stable_seed(260927, 'a', 'wear')
    command = ('from modeling.slum03.density_model import stable_seed; '
               'print(stable_seed(260927, "a", "wear"))')
    other = int(subprocess.check_output([sys.executable, '-c', command], text=True).strip())
    assert first == expected == other
    assert first != stable_seed(260927, 'b', 'wear')
    assert first != stable_seed(260927, 'a', 'goods')
    assert REPRESENTATIVE_KEYS == ('ruin-west', 'shack-row', 'market-west')


def test_saved_baseline_has_original_fixed_hash_and_slot_keys(legacy_manifest):
    # 固定値の理由: density-baseline.json は Gate D2 で適用した候補の基準（apply-log.md・live-verification.json が
    # この SHA を記録）として凍結した。Slot キーは適用済みの state が指す代表 3 単位の安定キー。
    baseline = Path('content/slum03/density-baseline.json').read_bytes()
    assert hashlib.sha256(baseline).hexdigest() == (
        '2a048a15fd41de680964590c9182868e85bfd175e5fb12044b4824236c0e2bec')
    def walk(node):
        yield node['slot']
        for child in node.get('children', []):
            yield from walk(child)
    names = {slot['name']: slot['key'] for slot in walk(legacy_manifest)}
    assert {name: names[name] for name in REPRESENTATIVE_KEYS} == {
        'ruin-west': 'object_ruin-west_268d72a5',
        'shack-row': 'object_shack-row_06a9a4ed',
        'market-west': 'object_market-west_c7b851dd',
    }
