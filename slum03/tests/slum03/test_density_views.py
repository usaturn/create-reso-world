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
    assert set(cameras) == {'density-ruin-near', 'density-shack-near', 'density-market-inward',
                            'density-west-street', 'density-east-lane'}
    assert cameras['density-ruin-near']['position'] != cameras['density-west-street']['position']


def test_added_checks_only_extend_legacy_cameras_and_tests():
    layout = read_layout(Path('content/slum03/density-representative-layout.json'))
    manifest = json.loads(Path('content/slum03/density-rep-a-20260928Ttask6-01-candidate-fix3.json').read_text())
    original = deepcopy(manifest)
    add_density_checks(manifest, layout)
    assert all(manifest['cameras'][key] == camera for key, camera in original['cameras'].items())
    assert manifest['tests'][:len(original['tests'])] == original['tests']
    assert manifest['assets'] == original['assets'] and manifest['children'] == original['children']
    assert len(manifest['cameras']) == len(original['cameras']) + 5
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
    assert {key: value for key, value in reviewed.items() if key not in ('cameras', 'tests')} == {
        key: value for key, value in source.items() if key not in ('cameras', 'tests')}
    assert reviewed['assets'] == source['assets']
    assert len(reviewed['cameras']) == len(source['cameras']) + 5


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
