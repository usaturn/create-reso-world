"""Breaks caught: self-declared groups, missing export stock, collapsed shapes and stale Layout."""
from dataclasses import replace
import pytest
from modeling.slum03.geometry import Assembly, box, merge_assembly
import importlib

def observe_detail(*args):
    return importlib.import_module("modeling.slum03.evaluated_detail").observe_detail(*args)

def validate_evaluated_density(*args):
    return importlib.import_module("modeling.slum03.evaluated_detail").validate_evaluated_density(*args)
from modeling.slum03.layout import build_layout
from modeling.slum03.density_metrics import layout_digest


def specimen():
    a = Assembly('stall', 'demo', 'market', (3., 0., 4.),
                 [box('leg', (0, 1, 0), (.1, 2, .1), 'steel_dark'),
                  box('stock', (.5, 1, 0), (.2, .2, .2), 'steel_dark')],
                 {'placement_key': 'demo', 'variant': 'tools', 'detail_groups': [
                     {'id': 'frame', 'category': 'architecture', 'part_indices': [0]},
                     {'id': 'item', 'category': 'merchandise', 'part_indices': [1]}]})
    merged = merge_assembly(a)
    return a, {'vertices': [tuple(v[i]+a.origin[i] for i in range(3)) for v in merged.vertices],
               'faces': merged.faces}


def test_observation_checks_actual_placed_faces_and_part_bounds():
    a, geometry = specimen()
    report = observe_detail(a, geometry)
    assert report['placement_key'] == 'demo'
    assert report['detail_groups'][1]['bounds'] == {'minimum': [3.4, .9, 3.9],
                                                     'maximum': [3.6, 1.1, 4.1]}
    assert report['detail_groups'][1]['face_count'] == 6
    assert report['evaluated_bounds']['maximum'] == [3.6, 2., 4.1]


@pytest.mark.parametrize('change', ['missing', 'collapsed', 'fake', 'nonfinite'])
def test_observation_rejects_missing_or_unmatched_geometry(change):
    a, geometry = specimen()
    if change == 'missing':
        geometry['faces'] = geometry['faces'][:6]
    elif change == 'collapsed':
        geometry['vertices'] = [(3., 0., 4.)] * len(geometry['vertices'])
    elif change == 'fake':
        a.meta['detail_groups'].append({'id': 'ghost', 'category': 'merchandise', 'part_indices': [99]})
    else:
        geometry['vertices'][0] = (float('nan'), 0, 0)
    with pytest.raises(ValueError):
        observe_detail(a, geometry)


def test_density_validation_rejects_wrong_layout_digest_before_using_groups():
    layout = build_layout()
    a, geometry = specimen()
    obj = observe_detail(a, geometry)
    reports = {'market': {'layout_sha256': layout_digest(layout)+'wrong', 'objects': [obj],
                          'evaluated_bounds': {'demo': obj['evaluated_bounds']}}}
    assert any(i.code == 'LAYOUT_MISMATCH' for i in validate_evaluated_density(layout, reports))


def test_report_rejects_fabricated_item_outside_export_envelope():
    a, geometry = specimen()
    obj = observe_detail(a, geometry)
    obj['detail_profile'] = 'v2'
    obj['detail_groups'][1]['part_bounds'][0]['maximum'][0] = 20.
    layout = build_layout()
    reports = {'market': {'layout_sha256': layout_digest(layout), 'objects': [obj],
                          'evaluated_bounds': {'demo': obj['evaluated_bounds']}}}
    assert any(i.code == 'DETAIL_INVALID' for i in validate_evaluated_density(layout, reports))


def test_evaluated_validation_rejects_out_of_range_attachment_contact():
    from modeling.slum03.types import Placement
    layout = build_layout()
    child = Placement('mounted', 'market', 'utility', (0., 0., 0.), (1., 1., 1.), 0., 'district',
                      {'attachment': {'parent_key': 'market-west', 'reason': 'bracket',
                                      'contact_min': [99., 0., 0.], 'contact_max': [100., .5, .5]}})
    altered = replace(layout, placements=layout.placements + (child,))
    assert any(i.code == 'ATTACHMENT' for i in validate_evaluated_density(altered, {}))


def test_missing_v2_sector_report_is_not_treated_as_evaluated():
    layout = build_layout()
    altered = replace(layout, placements=tuple(replace(p, params={**p.params,
        'detail_profile': 'v2', 'variant': 'electronics'}) if p.key == 'market-west' else p
        for p in layout.placements))
    assert any(i.code == 'LAYOUT_MISMATCH' and i.object_key == 'market'
               for i in validate_evaluated_density(altered, {}))


def test_face_with_same_indices_but_self_crossing_order_is_rejected():
    a, geometry = specimen()
    face = list(geometry['faces'][0])
    assert len(face) == 4
    geometry['faces'] = ((face[0], face[2], face[1], face[3]), *geometry['faces'][1:])
    with pytest.raises(ValueError, match='face'):
        observe_detail(a, geometry)


@pytest.mark.parametrize('fault', ['mesh', 'profile', 'counts', 'group'])
def test_layout_required_v2_evidence_cannot_be_bypassed_by_report_tags(fault):
    base = build_layout()
    target = next(p for p in base.placements if p.key == 'market-west')
    layout = replace(base, placements=tuple(replace(p, params={**p.params,
        'detail_profile': 'v2', 'variant': 'electronics'}) if p == target else p
        for p in base.placements))
    a, geometry = specimen()
    obj = observe_detail(a, geometry)
    obj.update({'key': 'market-west', 'placement_key': 'market-west', 'variant': 'electronics',
                'detail_profile': 'v2'})
    bounds = {'demo': obj['evaluated_bounds']}
    if fault == 'mesh':
        obj['mesh'] = None
    elif fault == 'profile':
        obj.pop('detail_profile')
    elif fault == 'counts':
        obj['vertices'] = 0
    else:
        obj['detail_groups'] = [{}]
    reports = {'market': {'layout_sha256': layout_digest(layout), 'objects': [obj],
                          'evaluated_bounds': bounds}}
    issues = validate_evaluated_density(layout, reports)
    assert any(i.object_key == 'market-west' and i.code in ('GEOMETRY_MISSING', 'DETAIL_MISSING',
                                                             'DETAIL_INVALID') for i in issues), issues


def test_contact_box_allows_only_actual_overlap_within_its_bounds():
    from modeling.slum03.types import Placement
    base = build_layout()
    parent = Placement('attached-parent', 'market', 'stall', (22., 0., -30.), (4., 3., 4.),
                       0., 'district', {'detail_profile': 'v2', 'variant': 'tools'})
    child = Placement('attached-child', 'market', 'stall', (23., 0., -30.), (2., 3., 2.),
                      0., 'district', {'detail_profile': 'v2', 'variant': 'tools',
                                     'attachment': {'parent_key': parent.key, 'reason': 'bracket',
                                                    'contact_min': [22.9, .3, -.1 - 30],
                                                    'contact_max': [23.1, .7, .1 - 30]}})
    layout = replace(base, placements=base.placements + (parent, child))

    def report_for(p, stock):
        # One physical rectangular component, with unchanged face/vertex provenance.
        a = Assembly('stall', p.key, 'market', p.origin,
                     [box('brace', (1. if p == parent else 0., .5, 0.), stock, 'steel_dark')],
                     {'placement_key': p.key, 'variant': 'tools', 'detail_groups': [
                         {'id': 'brace', 'category': 'architecture', 'part_indices': [0]}]})
        merged = merge_assembly(a)
        obj = observe_detail(a, {'vertices': [tuple(v[i]+p.origin[i] for i in range(3))
                                                for v in merged.vertices], 'faces': merged.faces})
        obj['detail_profile'] = 'v2'
        return obj

    def issues(stock):
        parent_obj, child_obj = report_for(parent, stock), report_for(child, stock)
        reports = {'market': {'layout_sha256': layout_digest(layout),
                             'objects': [parent_obj, child_obj],
                             'evaluated_bounds': {p['mesh']: p['evaluated_bounds']
                                                  for p in (parent_obj, child_obj)}}}
        return validate_evaluated_density(layout, reports)

    assert not any(i.code == 'ATTACHMENT_INTRUSION' for i in issues((.2, .4, .2)))
    assert any(i.code == 'ATTACHMENT_INTRUSION' and i.object_key == child.key
               for i in issues((.5, 2., .5)))
