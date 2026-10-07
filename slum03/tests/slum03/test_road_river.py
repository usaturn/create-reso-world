"""Task 6 geometry regressions: removing real surfaces, supports or gaps must fail."""
from modeling.slum03.spatial import validate_clearance
from modeling.slum03.types import Bounds3

from modeling.slum03.geometry import bounds
from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import sector_assemblies


def scene():
    return {a.name: a for a in sector_assemblies(build_layout(), 'road-river')}


def cuboids(a):
    for part in a.parts:
        lo, hi = bounds([part])
        yield part, tuple(lo[i]+a.origin[i] for i in range(3)), tuple(hi[i]+a.origin[i] for i in range(3))


def at_top(a, x, z, y=0):
    return any(lo[0] <= x <= hi[0] and lo[2] <= z <= hi[2]
               and abs(hi[1]-y) < 1e-5 for _, lo, hi in cuboids(a))


def intersects_walk(a, x, z, foot=0, head=2.2):
    return any(lo[0] < x < hi[0] and lo[2] < z < hi[2]
               and hi[1] > foot+1e-4 and lo[1] < head-1e-4
               for _, lo, hi in cuboids(a))


def test_bridge_matches_road_and_bank_span():
    # 固定値の理由: 橋の範囲（X 60〜96・Z 72〜118）は、承認済みの設計仕様
    # （2026-09-27-slum03-cyberpunk-slum-design.md の 4.1 の表）が定める。
    bridge, = build_layout().select('bridge')
    assert bridge.size[0] == 36.0
    assert bridge.origin[2] - bridge.size[2] / 2 == 72.0
    assert bridge.origin[2] + bridge.size[2] / 2 == 118.0


def test_bridge_walkway_connects_both_banks():
    # Removing either approach, even with an intact bridge placement, breaks this.
    pieces = scene()
    for x in (63, 78, 93):
        for z in (-99.9, 71.9, 72.1, 95, 117.9, 118.1, 129.9):
            assert any(at_top(a, x, z) for a in pieces.values()), (x, z)
            assert not any(intersects_walk(a, x, z) for a in pieces.values()), (x, z)
    assert all(not at_top(pieces['roadway'], 78, z) for z in (73, 95, 117))
    assert at_top(pieces['bridge'], 78, 95)


def test_checkpoint_has_three_metre_opening():
    pieces = scene()
    gate = pieces['checkpoint']
    assert any(hi[1] >= 4 for _, lo, hi in cuboids(gate))  # real overhead canopy
    for x in (62.5, 78, 93.5):
        for z in (66.1, 69, 71.9):
            assert at_top(pieces['west-sidewalk' if x < 66 else 'east-sidewalk' if x > 90 else 'roadway'], x, z)
            assert not any(intersects_walk(a, x, z) for a in pieces.values()), (x, z)
    for x in (76.5, 78, 79.5):
        assert not intersects_walk(gate, x, 69)


def test_railings_keep_avatar_out_of_water():
    pieces = scene()
    # The outer edge of the deck has a continuous >avatar-height barrier.
    for x in (60.2, 95.8):
        for z in (72.2, 78, 95, 112, 117.8):
            assert any(lo[0] <= x <= hi[0] and lo[2] <= z <= hi[2]
                       and lo[1] <= 0.1 and hi[1] >= 1.4
                       for _, lo, hi in cuboids(pieces['bridge'])), (x, z)
    # Open shores on either side are retained by bank walls, not by an invisible sheet.
    for x in (-100, 55, 100, 200):
        for z in (78, 112):
            assert any(lo[0] <= x <= hi[0] and lo[2] <= z <= hi[2]
                       and lo[1] <= -3.9 and hi[1] >= 0
                       for a in pieces.values() for _, lo, hi in cuboids(a)), (x, z)


def test_bridge_structural_supports_touch_deck_and_waterline():
    bridge = scene()['bridge']
    pieces = list(cuboids(bridge))
    piers = [(lo, hi) for _, lo, hi in pieces if lo[1] <= -4 and hi[1] < -1]
    girders = [(lo, hi) for _, lo, hi in pieces if -2 < lo[1] < -.4 and abs(hi[1]+.4) < 1e-5]
    decks = [(lo, hi) for _, lo, hi in pieces if abs(lo[1]+.4) < 1e-5 and abs(hi[1]) < 1e-5]
    def touches(a, b):
        lo, hi = a
        low, high = b
        return (abs(hi[1]-low[1]) < 1e-5 and
                lo[0] < high[0] and low[0] < hi[0] and
                lo[2] < high[2] and low[2] < hi[2])
    assert piers and girders and decks
    assert all(any(touches(pier, girder) and any(touches(girder, deck) for deck in decks)
                   for girder in girders) for pier in piers)
    placement, = build_layout().select('bridge')
    assert placement.origin[1]+placement.params['local_y_min'] <= -4
    assert placement.origin[1]+placement.params['local_y_min']+placement.size[1] >= 1.4


def test_river_is_below_walkway_and_has_no_duplicate_road_deck():
    pieces = scene()
    assert at_top(pieces['river'], -100, 95, -4)
    assert at_top(pieces['river'], 78, 95, -4)
    for name in ('roadway', 'west-sidewalk', 'east-sidewalk'):
        assert not at_top(pieces[name], 78 if name == 'roadway' else 63 if name == 'west-sidewalk' else 93, 95)
    assert all(not at_top(pieces['river'], 78, z, -4) for z in (77, 113))
    # South and north edges are explicit non-explorable boundaries.
    for z in (-100.5, 130.5):
        for x in (63, 78, 93):
            assert any(lo[0] <= x <= hi[0] and lo[2] <= z <= hi[2] and hi[1] >= 1.4
                       for a in pieces.values() for _, lo, hi in cuboids(a))


def test_bridge_envelope_cannot_extend_into_unowned_route():
    layout = build_layout()
    assert validate_clearance(layout, {'bridge': Bounds3((59, -4, 72), (96, 2.1, 118))})


def test_road_river_blender_reopens_with_uvs_bounds_and_renders(tmp_path):
    import json
    import subprocess
    blend = tmp_path / 'road-river.blend'
    subprocess.run(['resoloop', 'blender', 'run', 'modeling/slum03/build.py',
                    '--arg=--sector', '--arg=road-river', '--arg=--output',
                    f'--arg={blend}', '--json'], check=True, capture_output=True, text=True)
    report = json.loads((tmp_path/'road-river-report.json').read_text())
    assert not report['errors'] and not report['uv_issues']
    assert len({entry['key'] for entry in report['objects']}) == len(report['objects'])
    assert report['evaluated_bounds']['river']['minimum'][1] == -4
    assert report['evaluated_bounds']['bridge']['minimum'][1] == -4
    render = subprocess.run(['resoloop', 'blender', 'run', 'tests/slum03/blender_road_river_probe.py',
                    '--blend', str(blend), f'--arg={tmp_path}', '--json'],
                   check=True, capture_output=True, text=True)
    assert 'DeprecationWarning' not in render.stdout + render.stderr
    probe = json.loads((tmp_path/'reopened.json').read_text())
    assert probe['source_hidden']
    assert probe['objects'] == 12
    assert probe['all_uv0'] and probe['all_col']
    assert probe['deck_y'] == 0 and probe['water_y'] == -4
    assert probe['minimum_visible_local_y'] == -4
    for image in ('bridge', 'checkpoint', 'river'):
        assert (tmp_path/f'{image}.png').stat().st_size > 1000


def test_revetments_do_not_report_false_route_intrusion_from_merged_bounds():
    layout = build_layout()
    evaluated = {}
    for a in scene().values():
        lo, hi = bounds(a.parts)
        evaluated[a.name] = Bounds3(tuple(lo[i]+a.origin[i] for i in range(3)),
                                    tuple(hi[i]+a.origin[i] for i in range(3)))
    assert validate_clearance(layout, evaluated) == []


def _face_coplanar_on_same_exposed_side(a, b):
    """Compare actual polygon faces, not only names or overlapping bounding boxes."""
    def side_faces(part):
        low, high = bounds([part])
        for face in part.faces:
            xs = [part.vertices[i][0] for i in face]
            if max(xs)-min(xs) < 1e-7:
                side = 'min' if abs(xs[0]-low[0]) < 1e-7 else 'max' if abs(xs[0]-high[0]) < 1e-7 else None
                if side:
                    ys = [part.vertices[i][1] for i in face]
                    zs = [part.vertices[i][2] for i in face]
                    yield side, xs[0], (min(ys), max(ys)), (min(zs), max(zs))
    for side_a, x_a, y_a, z_a in side_faces(a):
        for side_b, x_b, y_b, z_b in side_faces(b):
            if (side_a == side_b and abs(x_a-x_b) < 1e-7 and
                    min(y_a[1], y_b[1])-max(y_a[0], y_b[0]) > 1e-5 and
                    min(z_a[1], z_b[1])-max(z_a[0], z_b[0]) > 1e-5):
                return True
    return False


def _contact_volume(a, b):
    low_a, high_a = bounds([a])
    low_b, high_b = bounds([b])
    return all(min(high_a[i], high_b[i])-max(low_a[i], low_b[i]) > .01
               for i in range(3))


def test_gate_devices_are_surface_mounted_without_exposed_coplanar_faces():
    gate = scene()['checkpoint']
    columns = [part for part in gate.parts if part.name == 'gate-pier']
    assert len(columns) == 2
    for name in ('scanner-housing', 'signal'):
        devices = [part for part in gate.parts if part.name == name]
        assert len(devices) == len(columns)
        for column, device in zip(columns, devices):
            c0, c1 = bounds([column]); d0, d1 = bounds([device])
            assert _contact_volume(column, device)  # no hovering attachment
            assert d0[0] < c0[0] or d1[0] > c1[0], 'device must be visible past pier face'
            assert not _face_coplanar_on_same_exposed_side(column, device)
    # Outermost pedestrian routes still have more than three metres free.
    for x in (62, 63, 64, 92, 93, 94):
        assert not intersects_walk(gate, x, 69)


def test_rail_stiffeners_protrude_without_coplanar_parapet_side_faces():
    bridge = scene()['bridge']
    parapets = [part for part in bridge.parts if part.name == 'bridge-parapet']
    caps = [part for part in bridge.parts if part.name == 'rail-cap']
    ribs = [part for part in bridge.parts if part.name == 'parapet-rib']
    assert len(parapets) == len(caps) == 2 and len(ribs) >= 2
    for rib in ribs:
        rail = min(parapets, key=lambda p: abs(bounds([rib])[0][0] - bounds([p])[0][0]))
        cap = min(caps, key=lambda p: abs(bounds([rib])[0][0] - bounds([p])[0][0]))
        r0, r1 = bounds([rib]); p0, p1 = bounds([rail])
        assert _contact_volume(rail, rib) and _contact_volume(cap, rib)
        assert r0[0] < p0[0] or r1[0] > p1[0], 'rib must show at rail face'
        assert not _face_coplanar_on_same_exposed_side(rail, rib)
        assert not _face_coplanar_on_same_exposed_side(cap, rib)
    for x in (62, 63, 64, 92, 93, 94):
        assert not intersects_walk(bridge, x, 95)
