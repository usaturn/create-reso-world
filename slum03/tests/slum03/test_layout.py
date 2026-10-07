"""Regression tests for the shared, offline world plan (no live session)."""
import json
import subprocess
import sys
from dataclasses import replace

import pytest

from modeling.slum03.layout import build_layout, read_layout, validate_layout, write_layout
from modeling.slum03.types import RectXZ


def test_layout_dimensions_and_repeatability():
    # 固定値の理由: 街区 120 m 四方・工場跡地 40×30 m・中央 32×22 m は、承認済みの設計仕様
    # （2026-09-27-slum03-cyberpunk-slum-design.md の D-03・D-04・9.1「寸法」）の受入条件。
    a = build_layout()
    assert a == build_layout(260927)
    assert a.district.size == (120.0, 120.0)
    assert a.plaza.size == (40.0, 30.0)
    assert a.clear.bounds == (-16.0, 16.0, -11.0, 11.0)
    assert validate_layout(a) == []


def test_other_seeds_preserve_public_corridors_and_dimensions():
    base = build_layout()
    for seed in (7, 91):
        other = build_layout(seed)
        assert other.seed == seed
        assert other.district == base.district
        assert other.plaza == base.plaza
        assert other.clear == base.clear
        assert other.routes == base.routes
        assert validate_layout(other) == []


def test_plan_includes_canonical_sector_anchors_and_distinct_domains():
    # 固定値の理由: 必須の用途・北壁の位置と寸法・旧東壁なし・アーコロジーの高さ・Yarol の向き・AR 3 系統・
    # 方向別の視点は、承認済みの設計仕様（同上の 4 章・5.1・9.1）が定める。
    a = build_layout()
    by_key = {p.key: p for p in a.placements}
    assert len(by_key) == len(a.placements)
    for key in ('north-wall', 'yarol', 'bridge', 'checkpoint', 'forest',
                'arcology-terraces', 'arcology-gate', 'arcology-towers',
                'west-city', 'south-city'):
        assert key in by_key
    assert 'east-wall' not in by_key
    assert by_key['north-wall'].origin == (0.0, 0.0, 14.5)
    assert by_key['north-wall'].size == (36.0, 10.0, 0.8)
    assert by_key['yarol'].yaw_deg == 90.0
    assert by_key['yarol'].domain == 'district'
    assert by_key['bridge'].domain == 'road'
    assert by_key['forest'].domain == 'background'
    assert by_key['west-city'].domain == 'background'
    assert all(p.domain == 'background' and 500 <= p.size[1] <= 900
               for p in a.placements if p.key.startswith('arcology-'))
    assert {(p.key, p.target_group) for p in a.viewpoints} == {
        ('plaza-north', 'north_arcologies'), ('east-forest', 'east_forest'),
        ('east-lane', 'east_forest'),
        ('bridge-checkpoint', 'checkpoint'), ('west-city', 'west_city'),
        ('south-market', 'south_city'), ('ar-hero', 'ads')}
    assert any(label.text == 'Yarol' and label.parent_name == 'yarol' for label in a.labels)
    assert {'product-holo', 'info-ad', 'ribbon-ad'} <= {p.kind for p in a.placements}
    assert a.select('north-wall') == (by_key['north-wall'],)


def test_walkable_road_runs_beyond_district_and_river_is_outside_district():
    # 固定値の理由: 歩道・車道・川の範囲は、承認済みの設計仕様（同上の D-07・4.1 の表・9.1「寸法」）が定める。
    a = build_layout()
    road = {p.key: p for p in a.placements}
    assert road['west-sidewalk'].origin[2] == 15.0
    assert road['west-sidewalk'].size[2] == 230.0  # -100 to 130
    assert road['roadway'].origin[0] == 78.0
    assert road['roadway'].size[0] == 24.0
    assert road['east-sidewalk'].size[0] == 6.0
    assert road['river'].domain == 'water'
    assert road['river'].origin[2] == 95.0
    assert road['river'].size[2] == 34.0
    assert a.district.bounds == (-60.0, 60.0, -60.0, 60.0)
    assert all(r.size[0] >= 3 and r.size[1] >= 3 for r in a.routes)


def test_json_round_trip_and_two_fresh_processes_match(tmp_path):
    a = build_layout()
    dest = tmp_path / 'layout.json'
    write_layout(a, dest)
    assert read_layout(dest) == a
    assert json.loads(dest.read_text())['seed'] == 260927
    script = ('from modeling.slum03.layout import build_layout,write_layout; '
              'from pathlib import Path; import sys; '
              'write_layout(build_layout(),Path(sys.argv[1]))')
    one, two = tmp_path / 'one.json', tmp_path / 'two.json'
    for path in (one, two):
        subprocess.run([sys.executable, '-c', script, str(path)], check=True)
    assert one.read_bytes() == two.read_bytes() == dest.read_bytes()


def test_invalid_dimensions_and_nonfinite_numbers_are_rejected(tmp_path):
    a = build_layout()
    for rect in (RectXZ(-60, 60, -60, float('nan')), RectXZ(0, -1, 0, 1)):
        assert validate_layout(replace(a, district=rect))
    p = a.placements[0]
    for modified in (replace(p, size=(-1, 1, 1)), replace(p, yaw_deg=float('inf')),
                     replace(p, origin=(float('nan'), 0, 0))):
        broken = replace(a, placements=(modified,) + a.placements[1:])
        assert validate_layout(broken)
        with pytest.raises(ValueError):
            write_layout(broken, tmp_path / 'bad.json')
    path = tmp_path / 'bad-input.json'
    path.write_text('{"seed": NaN}')
    with pytest.raises(ValueError):
        read_layout(path)


def test_missing_landmark_and_blocked_exit_report_issues():
    a = build_layout()
    assert any(i.object_key == 'north-wall' for i in validate_layout(
        replace(a, placements=tuple(p for p in a.placements if p.key != 'north-wall'))))
    p = next(p for p in a.placements if p.key == 'north-wall')
    shifted = replace(p, origin=(18, 0, 0), size=(4, 6, 4))
    problems = validate_layout(replace(a, placements=tuple(
        shifted if q.key == p.key else q for q in a.placements)))
    assert any(i.code == 'CLEARANCE_INTRUSION' and i.object_key == 'north-wall' for i in problems)


def test_forest_boundary_and_open_checkpoint_cannot_drift_into_walkway():
    a = build_layout()
    forest = next(p for p in a.placements if p.key == 'forest')
    moved = replace(forest, origin=(159, 0, -10))
    altered = replace(a, placements=tuple(moved if p.key == forest.key else p
                                          for p in a.placements))
    assert any(i.object_key == 'forest' for i in validate_layout(altered))
    checkpoint = next(p for p in a.placements if p.key == 'checkpoint')
    shut = replace(checkpoint, params={'opening_width': 0, 'open': False})
    altered = replace(a, placements=tuple(shut if p.key == checkpoint.key else p
                                          for p in a.placements))
    assert any(i.object_key == 'checkpoint' for i in validate_layout(altered))


def test_missing_target_viewpoint_is_rejected():
    a = build_layout()
    altered = replace(a, viewpoints=tuple(v for v in a.viewpoints if v.key != 'east-forest'))
    assert any(i.object_key == 'east-forest' for i in validate_layout(altered))


def test_yarol_rotated_site_and_road_domain_are_verified():
    a = build_layout()
    yarol = next(p for p in a.placements if p.key == 'yarol')
    moved = replace(yarol, origin=(47, 0, 47))  # rotated X extent 41..53, below site X=43
    bad = replace(a, placements=tuple(moved if p.key == yarol.key else p
                                      for p in a.placements))
    assert any(i.object_key == 'yarol' for i in validate_layout(bad))
    road = next(p for p in a.placements if p.key == 'roadway')
    bad = replace(a, placements=tuple(replace(road, domain='district')
                                      if p.key == road.key else p for p in a.placements))
    assert any(i.object_key == 'roadway' for i in validate_layout(bad))


def test_north_turnback_boundary_is_required():
    a = build_layout()
    bad = replace(a, placements=tuple(p for p in a.placements if p.key != 'north-turnback'))
    assert any(i.object_key == 'north-turnback' for i in validate_layout(bad))


@pytest.mark.parametrize('key', ('river', 'north-towers'))
def test_missing_required_environment_is_rejected_on_save_and_read(tmp_path, key):
    layout = build_layout()
    missing = replace(layout, placements=tuple(p for p in layout.placements if p.key != key))
    assert any(issue.code == 'MISSING' and issue.object_key == key
               for issue in validate_layout(missing))
    with pytest.raises(ValueError, match='invalid layout'):
        write_layout(missing, tmp_path / 'missing.json')
    path = tmp_path / 'forged.json'
    write_layout(layout, path)
    data = json.loads(path.read_text(encoding='utf-8'))
    data['placements'] = [p for p in data['placements'] if p['key'] != key]
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='invalid layout JSON'):
        read_layout(path)


@pytest.mark.parametrize(('section', 'field', 'bad_value'), [
    ('placements', 'origin', [1, 2]),
    ('placements', 'origin', [1, 2, 3, 4]),
    ('placements', 'size', [1, 2]),
    ('placements', 'size', [1, 2, 3, 4]),
    ('viewpoints', 'eye', [1, 2]),
    ('viewpoints', 'eye', [1, 2, 3, 4]),
    ('labels', 'offset', [1, 2]),
    ('labels', 'offset', [1, 2, 3, 4]),
    ('labels', 'color', [1, 2, 3]),
    ('labels', 'color', [1, 2, 3, 4, 5]),
])
def test_read_layout_rejects_wrong_fixed_vector_lengths(tmp_path, section, field, bad_value):
    path = tmp_path / 'layout.json'
    write_layout(build_layout(), path)
    data = json.loads(path.read_text(encoding='utf-8'))
    if section == 'viewpoints':
        data['viewpoints'].append({'key': 'optional-lookout', 'eye': bad_value,
                                   'target_group': 'ads'})
    else:
        data[section][0][field] = bad_value
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='invalid layout JSON'):
        read_layout(path)


@pytest.mark.parametrize('bad_side', ['child', 'parent'])
def test_invalid_attachment_placement_returns_issues_instead_of_raising(bad_side):
    layout = build_layout()
    parent = next(p for p in layout.placements if p.key == 'market-west')
    child = replace(parent, key='market-west-attachment', kind='prop',
                    origin=(-9, 1, -34), size=(1, 1, 1),
                    params={'attachment': {'parent_key': 'market-west',
                                           'contact_min': [-9, 1, -34],
                                           'contact_max': [-9, 1.5, -34],
                                           'reason': 'fastened'}})
    if bad_side == 'child':
        child = replace(child, yaw_deg='invalid')
    else:
        parent = replace(parent, yaw_deg='invalid')
    altered = replace(layout, placements=tuple(parent if p.key == parent.key else p
                                               for p in layout.placements) + (child,))
    issues = validate_layout(altered)
    assert any(i.code == 'PLACEMENT' and i.object_key == (child.key if bad_side == 'child' else parent.key)
               for i in issues)
    assert any(i.code == 'ATTACHMENT' and i.object_key == child.key for i in issues)
