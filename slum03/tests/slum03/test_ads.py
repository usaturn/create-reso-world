"""Ads regressions: flat impostors, moving headline, unmounted emitters, swept route collision."""
import math
from dataclasses import replace
import pytest

from modeling.slum03.geometry import bounds, face_normal, signed_volume
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


def _projected_depth(assemblies):
    # Projected surface/light only: support mast, mounting boxes, and emitter
    # lenses cannot prove that the advertised content has any depth.
    parts = [part for a in assemblies for part in a.parts
             if part.material.startswith('holo_') and not part.name.startswith('emitter')]
    assert parts
    z = [vertex[2] for part in parts for vertex in part.vertices]
    return max(z)-min(z)


def test_three_hologram_families_have_depth():
    ads = sector_assemblies(build_layout(), 'ads')
    for kind in ('product-holo', 'info-ad', 'ribbon-ad'):
        pieces = [a for a in ads if a.kind == kind and a.parts]
        assert pieces, kind
        assert _projected_depth(pieces) >= .55, kind
        # Negative control: flatten *only projected parts*, leaving the physical
        # floor mast and grounded bracket intact; the depth check must fail.
        flat = [replace(a, parts=[replace(part, vertices=tuple((x,y,0.) for x,y,_ in part.vertices))
                                  if part.material.startswith('holo_') and not part.name.startswith('emitter')
                                  else part for part in a.parts]) for a in pieces]
        assert _projected_depth(flat) == 0, kind
    product = [a for a in ads if a.kind == 'product-holo']
    assert any('optic' in part.name for a in product for part in a.parts)
    assert any('arc' in part.name for a in product for part in a.parts)
    ribbon = [a for a in ads if a.kind == 'ribbon-ad']
    assert any('ribbon' in part.name and len({round(v[2], 2) for v in part.vertices}) > 4
               for a in ribbon for part in a.parts)
    info = [a for a in ads if a.kind == 'info-ad']
    assert len({round(v[2], 1) for a in info for part in a.parts for v in part.vertices}) >= 4


def test_optical_casing_faces_outward_including_caps():
    product = [a for a in sector_assemblies(build_layout(), 'ads') if a.kind == 'product-holo']
    housing = next(p for a in product for p in a.parts if p.name == 'optic-housing')
    assert signed_volume(housing) > .5  # closed shell; catches globally inward winding
    normals = [face_normal([housing.vertices[i] for i in face]) for face in housing.faces]
    # Sides of the casing must point out towards +X, not back into the optic.
    side = [(face, n) for face, n in zip(housing.faces, normals)
            if 3 <= len(face) and sum(housing.vertices[i][0] for i in face)/len(face) > .23
            and abs(sum(housing.vertices[i][1] for i in face)/len(face)-.48) < .9]
    assert side and all(n[0] > 0 for _, n in side if n[0] != 0)
    bottom = min(housing.vertices, key=lambda v: v[1])[1]
    top = max(housing.vertices, key=lambda v: v[1])[1]
    assert any(all(abs(housing.vertices[i][1]-bottom) < 1e-5 for i in face) and n[1] < -.9
               for face,n in zip(housing.faces, normals))
    assert any(all(abs(housing.vertices[i][1]-top) < 1e-5 for i in face) and n[1] > .9
               for face,n in zip(housing.faces, normals))


def test_product_reads_as_stepped_optical_cyberware_not_glowing_capsule():
    product = [a for a in sector_assemblies(build_layout(), 'ads') if a.kind == 'product-holo']
    parts = [part for a in product if a.meta.get('motion') for part in a.parts]
    housing = next(p for p in parts if p.name == 'optic-housing')
    assert not housing.material.startswith('holo_')  # metal casing, not an opaque cyan pill
    barrels = [p for p in parts if p.name == 'lens-barrel']
    assert barrels
    barrel = barrels[0]
    lo, hi = bounds([barrel])
    assert hi[2]-lo[2] >= .25 and hi[0]-lo[0] >= .8
    assert len({round(v[0]**2+(v[1]-.48)**2, 2) for v in barrel.vertices}) >= 3
    assert signed_volume(barrel) > 0  # genuinely hollow outward stepped barrel
    lens = [p for p in parts if p.name == 'cornea-lens']
    assert lens and lens[0].material.startswith('holo_')
    assert min(v[2] for v in lens[0].vertices) > lo[2]
    assert max(v[2] for v in lens[0].vertices) > hi[2]
    assert any(p.name == 'rear-connector' for p in parts)


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
    optical = next(m for m in report['meshes'] if m['name'] == 'market-product-holo-driven')
    exported_data = json.loads((bundle/optical['file']).read_text())
    # Unmodified casing corner is an asymmetric sample: check the *exported*
    # normal, not only Blender's local face math or the mirrored XZY transform.
    sample = [v for v in exported_data['vertices']
              if abs(v['position']['x']-.405689) < 1e-3
              and abs(v['position']['y']+.22) < 1e-3
              and abs(v['position']['z']-.124705) < 1e-3]
    assert sample and all(v['normal']['x'] > .2 for v in sample), sample
