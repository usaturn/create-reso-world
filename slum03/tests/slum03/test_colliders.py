import glob
import json
import pytest
from dataclasses import replace
from modeling.slum03.layout import build_layout
from modeling.slum03.native.colliders import collider_slots
from modeling.slum03.postprocess import postprocess


def test_floor_touches_clear_volume_only_at_y_zero_and_background_has_no_colliders():
    layout = build_layout()
    boxes = collider_slots(layout, {})
    assert boxes
    assert not any('background' in b['slot']['key'] or 'forest' in b['slot']['key'] for b in boxes)
    for n in boxes:
        p = n['slot']['position']; size = n['components'][0]['fields']['Size']
        x0, x1 = p[0]-size[0]/2, p[0]+size[0]/2
        z0, z1 = p[2]-size[2]/2, p[2]+size[2]/2
        overlaps = (x0 < layout.clear.x_max and x1 > layout.clear.x_min and
                    z0 < layout.clear.z_max and z1 > layout.clear.z_min)
        if overlaps:
            assert n['slot']['key'] in ('collider-factory-floor',)
            assert p[1]+size[1]/2 == 0
    assert not any(b['slot']['key'] == 'collider-bridge' or b['slot']['key'] == 'collider-checkpoint' for b in boxes)


def test_bridge_deck_and_checkpoint_columns_leave_three_metre_passage():
    boxes = collider_slots(build_layout(), {})
    keys = {b['slot']['key'] for b in boxes}
    assert {'collider-bridge-deck', 'collider-bridge-rail-west', 'collider-bridge-rail-east',
            'collider-checkpoint-pier-west', 'collider-checkpoint-pier-east',
            'collider-checkpoint-canopy'} <= keys
    for n in boxes:
        if n['slot']['key'].startswith('collider-checkpoint'):
            p = n['slot']['position']; size = n['components'][0]['fields']['Size']
            if p[1]-size[1]/2 < 3:
                assert p[0]+size[0]/2 <= 63 or p[0]-size[0]/2 >= 93


def test_postprocess_does_not_duplicate_colliders():
    m = json.load(open(glob.glob('artifacts/slum03/task8-final-*/bundle/model.apply.json')[0], encoding='utf-8'))
    m['ownership']['key'] = 'slum03'
    m['slot']['name'] = 'Slum03_Slum'
    layout = build_layout()
    layout = replace(layout, labels=tuple(l for l in layout.labels
                                          if l.parent_name in ('market-product-holo', 'nightlife-info-ad', 'east-lane-ribbon')))
    out = postprocess(m, layout, {}, (0, 0, 0))
    assert postprocess(out, layout, {}, (0, 0, 0)) == out


def test_reported_mesh_envelope_rejects_colliders_outside_real_geometry():
    layout = build_layout()
    road = json.load(open(glob.glob('artifacts/slum03/task6-fix1-*/road-river-report.json')[0], encoding='utf-8'))
    ground = json.load(open(glob.glob('artifacts/slum03/task3-fix1-*/ground-report.json')[0], encoding='utf-8'))
    plaza = json.load(open(glob.glob('artifacts/slum03/task3-fix1-*/plaza-report.json')[0], encoding='utf-8'))
    assert collider_slots(layout, {'road-river': road, 'ground': ground, 'plaza': plaza})
    road['evaluated_bounds']['bridge']['maximum'][0] = 80
    with pytest.raises(ValueError, match='bridge-deck'):
        collider_slots(layout, {'road-river': road, 'ground': ground, 'plaza': plaza})


def test_nightlife_facades_have_simple_owned_building_colliders():
    keys = {n['slot']['key'] for n in collider_slots(build_layout(), {})}
    assert {'collider-nightlife-east', 'collider-nightlife-velvet', 'collider-yarol'} <= keys


def test_yarol_collider_rotates_with_visible_facade():
    from math import cos, sin, radians
    n = next(n for n in collider_slots(build_layout(), {}) if n['slot']['key'] == 'collider-yarol')
    assert n['slot']['position'] == [51, 4.4, 47]
    assert n['components'][0]['fields']['Size'] == [14, 8.8, 12]
    assert n['slot']['rotation'] == [0., 0.70710678, 0., 0.70710678]
    # Transform the collider's local XZ corners; the visual facade occupies
    # x=45..57 / z=40..54, not the unrotated x=44..58 / z=41..53.
    yaw = radians(90)
    corners = [(51 + x*cos(yaw) + z*sin(yaw),
                47 - x*sin(yaw) + z*cos(yaw))
               for x in (-7, 7) for z in (-6, 6)]
    assert (round(min(x for x, _ in corners), 6), round(max(x for x, _ in corners), 6),
            round(min(z for _, z in corners), 6), round(max(z for _, z in corners), 6)) == (45, 57, 40, 54)


def test_noncardinal_building_yaw_is_kept_on_collider_slot():
    layout = build_layout()
    placements = tuple(replace(p, yaw_deg=30.) if p.key == 'ruin-west' else p
                       for p in layout.placements)
    changed = replace(layout, placements=placements)
    n = next(n for n in collider_slots(changed, {}) if n['slot']['key'] == 'collider-ruin-west')
    assert n['slot']['rotation'] == [0., .25881905, 0., .96592583]
    assert n['components'][0]['fields']['Size'] == pytest.approx([17, 19.2, 18])


def test_road_end_colliders_match_visible_barriers_but_not_checkpoint_passage():
    road = json.load(open(glob.glob('artifacts/slum03/task6-fix1-*/road-river-report.json')[0], encoding='utf-8'))
    boxes = collider_slots(build_layout(), {'road-river': road})
    for key in ('south-road-end', 'north-turnback'):
        n = next(n for n in boxes if n['slot']['key'] == f'collider-{key}')
        center = n['slot']['position']; size = n['components'][0]['fields']['Size']
        observed = road['evaluated_bounds'][key]
        assert [center[i]-size[i]/2 for i in range(3)] == observed['minimum']
        assert [center[i]+size[i]/2 for i in range(3)] == observed['maximum']
    assert not any(n['slot']['key'] == 'collider-checkpoint' for n in boxes)


def test_v2_open_stall_only_collides_with_real_low_parts_and_preserves_legacy_boxes():
    from modeling.slum03.evaluated_detail import observe_detail
    from modeling.slum03.geometry import merge_assembly
    from modeling.slum03.density_metrics import layout_digest
    from modeling.slum03.market_detail import detailed_stall
    from modeling.slum03.types import Placement
    base = build_layout()
    p = Placement('open-demo', 'market', 'stall', (12., 0., -40.), (3., 3., 4.), 0., 'district',
                  {'variant': 'tools', 'detail_profile': 'v2'})
    layout = replace(base, placements=base.placements + (p,))
    a = detailed_stall(p, layout.seed)
    m = merge_assembly(a)
    evidence = observe_detail(a, {'vertices': [tuple(v[i]+p.origin[i] for i in range(3)) for v in m.vertices],
                                  'faces': m.faces})
    reports = {'market': {'layout_sha256': layout_digest(layout), 'objects': [evidence],
                          'evaluated_bounds': {p.key: evidence['evaluated_bounds']}}}
    original = collider_slots(base, {})
    assert len(original) == 34
    boxes = collider_slots(layout, reports)
    assert boxes[:len(original)] == original  # floor/bridge/checkpoint/old 34 unchanged
    additions = boxes[len(original):]
    assert additions and not any(n['slot']['key'] == 'collider-open-demo' for n in additions)
    # Customer front at +Z: free centre aisle up to shoulder height.
    for n in additions:
        c = n['slot']['position']; size = n['components'][0]['fields']['Size']
        assert not (c[0]-size[0]/2 < 12 < c[0]+size[0]/2 and
                    c[2]-size[2]/2 < -39 < c[2]+size[2]/2 and
                    c[1]-size[1]/2 < 1.5 < c[1]+size[1]/2)
    assert any('shelf' in n['slot']['key'] for n in additions)
    with pytest.raises(ValueError, match='evaluated|report'):
        collider_slots(layout, {})


def test_density_branch_intrusion_is_rejected_from_real_evaluated_parts():
    from modeling.slum03.evaluated_detail import validate_evaluated_density
    from modeling.slum03.density_metrics import layout_digest
    from modeling.slum03.types import DensityConfig, RectXZ
    base = build_layout()
    from modeling.slum03.types import Placement
    p = Placement('blocking', 'market', 'stall', (0., 0., 0.), (3., 3., 4.), 0., 'district',
                  {'variant': 'tools', 'detail_profile': 'v2'})
    layout = replace(base, placements=base.placements + (p,), density=DensityConfig(
        'representative', (), (), (RectXZ(-2, 2, -2, 2),), ()))
    obj = {'mesh': 'blocking', 'placement_key': 'blocking', 'detail_profile': 'v2',
           'variant': 'tools', 'vertices': 8, 'faces': 6,
           'detail_groups': [{'id': 'leg', 'category': 'architecture', 'part_indices': [0],
                              'part_bounds': [{'minimum': [-.1, 0, -.1], 'maximum': [.1, 2, .1]}]}]}
    reports = {'market': {'layout_sha256': layout_digest(layout), 'objects': [obj],
                          'evaluated_bounds': {'blocking': {'minimum': [-.1, 0, -.1], 'maximum': [.1, 2, .1]}}}}
    assert any(i.code == 'CLEARANCE_INTRUSION' for i in validate_evaluated_density(layout, reports))
