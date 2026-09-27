"""Ads regressions: flat impostors, moving headline, unmounted emitters, swept route collision."""
import math
import pytest

from modeling.slum03.geometry import bounds
from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.spatial import validate_clearance
from modeling.slum03.types import Bounds3


def _world(p, v, spin=0):
    """Independent Resonite Y-up parent/pivot transform (anchor then driven)."""
    a = math.radians(p.yaw_deg)
    b = math.radians(spin)
    x, y, z = v
    x, z = x*math.cos(b)+z*math.sin(b), -x*math.sin(b)+z*math.cos(b)
    return (p.origin[0]+x*math.cos(a)+z*math.sin(a), p.origin[1]+y,
            p.origin[2]-x*math.sin(a)+z*math.cos(a))


def test_three_hologram_families_have_depth():
    ads = sector_assemblies(build_layout(), 'ads')
    for kind in ('product-holo', 'info-ad', 'ribbon-ad'):
        pieces = [a for a in ads if a.kind == kind and a.parts]
        assert pieces, kind
        coordinates = [v for a in pieces for part in a.parts for v in part.vertices]
        assert max(v[2] for v in coordinates)-min(v[2] for v in coordinates) >= .55, kind
    product = [a for a in ads if a.kind == 'product-holo']
    assert any('optic' in part.name for a in product for part in a.parts)
    assert any('arc' in part.name for a in product for part in a.parts)
    ribbon = [a for a in ads if a.kind == 'ribbon-ad']
    assert any('ribbon' in part.name and len({round(v[2], 2) for v in part.vertices}) > 4
               for a in ribbon for part in a.parts)
    info = [a for a in ads if a.kind == 'info-ad']
    assert len({round(v[2], 1) for a in info for part in a.parts for v in part.vertices}) >= 4


def test_primary_copy_is_not_driven():
    layout = build_layout()
    objects = sector_assemblies(layout, 'ads')
    moving_names = {a.name for a in objects if a.meta.get('motion')}
    anchors = {a.name for a in objects if a.meta.get('anchor')}
    assert len(moving_names) == 3
    for placement in (p for p in layout.placements if p.sector == 'ads'):
        assert placement.key in anchors
        assert any(a.meta.get('placement_key') == placement.key and a.name in moving_names
                   and a.meta['parent_name'] == placement.key for a in objects)
        assert any(label.parent_name == placement.key for label in layout.labels)
    assert all(label.parent_name not in moving_names for label in layout.labels)
    assert all(a.meta['motion']['driven_name'] == a.name and a.meta['motion']['rate'] <= 8
               for a in objects if a.meta.get('motion'))


def test_motion_envelope_avoids_routes():
    layout = build_layout()
    objects = sector_assemblies(layout, 'ads')
    for placement in (p for p in layout.placements if p.sector == 'ads'):
        group = [a for a in objects if a.meta.get('placement_key') == placement.key and a.parts]
        assert group
        # True transformed vertices, including the full spin envelope (not centre points).
        for angle in range(0, 360, 10):
            points = [_world(placement, v, angle if a.meta.get('motion', {}).get('kind') == 'spin' else 0)
                      for a in group for part in a.parts for v in part.vertices]
            lower = tuple(min(v[i] for v in points) for i in range(3))
            upper = tuple(max(v[i] for v in points) for i in range(3))
            assert not validate_clearance(layout, {placement.key: Bounds3(lower, upper)}), (placement.key, angle)
            # Motion and static mounts must remain inside the allotted X/Z footprint.
            assert lower[0] >= placement.origin[0]-placement.size[0]/2-.01
            assert upper[0] <= placement.origin[0]+placement.size[0]/2+.01
            assert lower[2] >= placement.origin[2]-placement.size[2]/2-.55  # headline sits ahead
            assert upper[2] <= placement.origin[2]+placement.size[2]/2+.01


def test_projector_has_physical_mount():
    layout = build_layout()
    ads = sector_assemblies(layout, 'ads')
    for p in (p for p in layout.placements if p.sector == 'ads'):
        fixed = [a for a in ads if a.meta.get('placement_key') == p.key and not a.meta.get('motion') and a.parts]
        parts = [part for a in fixed for part in a.parts]
        mounts = [part for part in parts if 'mount' in part.name or 'mast' in part.name]
        emitters = [part for part in parts if part.name == 'emitter']
        assert mounts and emitters, p.key
        contact_y = 11 if p.kind == 'info-ad' else 0
        assert min(v[1] for m in mounts for v in m.vertices) <= contact_y-p.origin[1]+.05
        if p.kind == 'info-ad':
            # Actual roof of two storefronts ends at Z=-15.55, not the air in front.
            roof_mounts = [m for m in mounts if m.name == 'roof-mount']
            assert roof_mounts
            assert all(-30.45 <= p.origin[2]+v[2] <= -15.55
                       for m in roof_mounts for v in m.vertices)
        for emitter in emitters:
            el, eh = bounds([emitter])
            assert any(all(bounds([m])[0][i] <= eh[i]+.02 and el[i] <= bounds([m])[1][i]+.02
                           for i in range(3)) for m in mounts)


def test_blender_reopens_real_anchor_hierarchy_and_world_transform(tmp_path):
    import subprocess
    blend = tmp_path/'ads.blend'
    built = subprocess.run(['resoloop', 'blender', 'run', 'modeling/slum03/build.py',
                            '--arg=--sector', '--arg=ads', f'--arg=--output', f'--arg={blend}',
                            '--json'], capture_output=True, text=True)
    assert built.returncode == 0, built.stdout + built.stderr
    probe = subprocess.run(['resoloop', 'blender', 'run', 'tests/slum03/blender_ads_probe.py',
                            '--blend', str(blend), '--json'], capture_output=True, text=True)
    assert probe.returncode == 0, probe.stdout + probe.stderr
    assert 'ADS_REOPEN_AND_PARENT_TRANSFORM_PASS' in probe.stdout
    import json
    bundle = tmp_path/'bundle'
    exported = subprocess.run(['resoloop', 'blender', 'export', str(blend),
                               '--output', str(bundle), '--name', 'Slum03Ads',
                               '--collection', 'Slum03adsExport', '--parent', 'Root',
                               '--preserve-hierarchy', '--json'], capture_output=True, text=True)
    assert exported.returncode == 0, exported.stdout + exported.stderr
    document = json.loads((bundle/'model.apply.json').read_text())
    placements = {p.key for p in build_layout().placements if p.sector == 'ads'}
    by_name = {child['slot']['name']: child for child in document['children']}
    assert placements <= by_name.keys()
    for name in placements:
        anchor = by_name[name]
        assert not anchor.get('components')
        assert {child['slot']['name'] for child in anchor['children']} == {
            name+'-projector', name+'-driven'}
        assert anchor['slot']['position'] == pytest.approx(
            next(p.origin for p in build_layout().placements if p.key == name), abs=1e-5)
        assert all(child['slot']['position'] == [0, 0, 0] for child in anchor['children'])
    report = json.loads((bundle/'report.json').read_text())
    assert report['preserveHierarchy'] and len(report['meshes']) == 6
    for exported_mesh in report['meshes']:
        data = json.loads((bundle/exported_mesh['file']).read_text())
        assert all(vertex.get('uvs') and vertex.get('color') for vertex in data['vertices'])
