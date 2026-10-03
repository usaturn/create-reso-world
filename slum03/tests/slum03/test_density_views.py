"""Wrong root transform, inward direction or mismatched comparison pose must fail."""
from copy import deepcopy
from pathlib import Path
import json

from modeling.slum03.layout import read_layout
from modeling.slum03.density_views import density_cameras, add_density_checks
from modeling.slum03.preview import comparison_poses


def test_shared_cameras_have_local_height_and_market_inward_direction():
    layout = read_layout(Path('content/slum03/density-representative-layout.json'))
    cameras = density_cameras(layout, (0, 4.5, 0))
    assert cameras['density-market-inward']['position'][1] == 6.1
    assert cameras['density-market-inward']['target'][2] < cameras['density-market-inward']['position'][2]
    assert cameras['density-market-inward']['fieldOfView'] == 60
    assert set(cameras) == {'density-ruin-near', 'density-shack-near',
                            'density-shack-washing-near', 'density-shack-context',
                            'density-market-inward', 'density-market-shelf-front',
                            'density-market-old-stock-near', 'density-west-street', 'density-east-lane'}
    assert cameras['density-ruin-near']['position'] != cameras['density-west-street']['position']


def test_added_checks_only_extend_legacy_cameras_and_tests():
    layout = read_layout(Path('content/slum03/density-representative-layout.json'))
    manifest = json.loads(Path('content/slum03/density-rep-a-20260928Ttask6-01-candidate-fix3.json').read_text())
    original = deepcopy(manifest)
    add_density_checks(manifest, layout)
    assert all(manifest['cameras'][key] == camera for key, camera in original['cameras'].items())
    assert manifest['tests'][:len(original['tests'])] == original['tests']
    assert manifest['assets'] == original['assets'] and manifest['children'] == original['children']
    assert len(manifest['cameras']) == len(original['cameras']) + 9
    assert len(manifest['tests']) == len(original['tests']) + 1
    assert add_density_checks(manifest, layout) is None
    assert len(manifest['tests']) == len(original['tests']) + 1


def test_comparison_uses_identical_root_local_pose_and_fov():
    layout = read_layout(Path('content/slum03/density-representative-layout.json'))
    cams = density_cameras(layout, (0, 4.5, 0))
    baseline = comparison_poses(cams, (0, 4.5, 0))
    candidate = comparison_poses(cams, (0, 4.5, 0))
    assert candidate == baseline
    assert abs(baseline['density-market-inward']['eye'][1] - 1.6) < 1e-12
    assert baseline['density-market-inward']['fieldOfView'] == 60
    assert baseline['density-market-inward']['target'][2] < baseline['density-market-inward']['eye'][2]


def test_review_candidate_preserves_all_content_and_assets():
    from modeling.slum03.density_views import review_manifest
    layout = read_layout(Path('content/slum03/density-representative-layout.json'))
    source = json.loads(Path('content/slum03/density-rep-a-20260928Ttask6-01-candidate-fix3.json').read_text())
    reviewed = review_manifest(source, layout)
    assert {key: value for key, value in reviewed.items() if key not in ('cameras', 'tests', 'limits')} == {
        key: value for key, value in source.items() if key not in ('cameras', 'tests', 'limits')}
    assert reviewed['assets'] == source['assets']
    assert len(reviewed['cameras']) == len(source['cameras']) + 9


def test_written_review_attests_original_and_final_hash_without_changing_resources(tmp_path):
    import hashlib
    from modeling.slum03.density_views import write_review
    original = Path('content/slum03/density-rep-a-20260928Ttask6-01-candidate-fix3.json')
    src = tmp_path / original.name
    src.write_bytes(original.read_bytes())
    from shutil import copy2
    for asset in json.loads(src.read_text())['assets'].values():
        name = Path(asset['source'])
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            copy2(original.parent / name, dest)
    layout = Path('content/slum03/density-representative-layout.json')
    out = tmp_path / 'review-candidate.json'
    evidence = write_review(src, layout, out, tmp_path / 'qa')
    assert evidence['candidate_sha256'] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert evidence['source_sha256'] == hashlib.sha256(original.read_bytes()).hexdigest()
    assert evidence['protected_changes'] == evidence['asset_changes'] == 0
    assert json.loads((tmp_path / 'qa' / 'acceptance.json').read_text())['status'] == 'pending'
    assert evidence['candidate_sha256'] == json.loads((tmp_path / 'qa' / 'acceptance.json').read_text())['manifest_sha256']
    # The inherited limit (11576) is below this QA revision's own node count.
    import math
    from modeling.slum03.pipeline import _count
    written = json.loads(out.read_text())
    content = {k: v for k, v in written.items() if k != 'limits'}
    assert written['limits'] == {'expandedNodes': math.ceil(_count(content) * 1.2)}
    assert written['limits']['expandedNodes'] >= _count(content)


def test_near_cameras_target_authored_surfaces_and_market_shelves_from_common_pose():
    layout = read_layout(Path('content/slum03/density-representative-layout.json'))
    cameras = density_cameras(layout, (0, 4.5, 0))
    ruin = cameras['density-ruin-near']
    # Repair cluster is on southwest back corner, not through the empty east bay.
    assert ruin['target'][0] < -44 and ruin['target'][2] < 5
    west = cameras['density-west-street']
    assert abs(west['position'][2] - ruin['position'][2]) > 12
    assert abs(west['position'][0] - ruin['position'][0]) > 12
    shack = cameras['density-shack-near']
    # The entrance ray aims toward the southwest washing station rather than at blank wall.
    assert shack['target'][0] < -42 and shack['target'][2] < -32
    market = cameras['density-market-inward']
    assert market['target'][0] < -7 and market['target'][2] <= -37
    assert market['position'][0] > -6


def test_extra_synchronized_views_face_washing_and_both_stock_orientations():
    layout = read_layout(Path('content/slum03/density-representative-layout.json'))
    cameras = density_cameras(layout, (0, 4.5, 0))
    wash = cameras['density-shack-washing-near']
    assert wash['target'][0] < -42 and wash['target'][2] < -32
    assert cameras['density-shack-context']['position'] != cameras['density-shack-near']['position']
    shelf = cameras['density-market-shelf-front']
    assert -40 < shelf['target'][2] < -38 and shelf['target'][2] < shelf['position'][2]
    old_shelf = cameras['density-market-old-stock-near']
    assert -7 < old_shelf['target'][0] < -6 and abs(old_shelf['target'][2] + 34) < .01


def test_shared_preview_has_usable_comparison_quality_without_changing_legacy_quality():
    from modeling.slum03.preview import preview_quality
    assert preview_quality(True)['resolution'] == (960, 640)
    assert preview_quality(True)['samples'] >= 64
    assert preview_quality(True)['denoise'] is True
    assert preview_quality(True)['fill_watts'] == 550
    assert preview_quality(False)['resolution'] == (640, 400)
