from dataclasses import replace
import copy
import glob
import json
import pytest

from modeling.slum03.postprocess import postprocess
from modeling.slum03.layout import build_layout
from modeling.slum03.native.common import slot_key_by_name


def nodes(n):
    yield n
    for c in n.get('children', []):
        yield from nodes(c)


def fixture():
    m = json.load(open(glob.glob('artifacts/slum03/task8-final-*/bundle/model.apply.json')[0], encoding='utf-8'))
    m['ownership']['key'] = 'slum03'
    m['slot']['name'] = 'Slum03_Slum'
    return m, replace(build_layout(), labels=tuple(l for l in build_layout().labels if l.parent_name in ('market-product-holo', 'nightlife-info-ad', 'east-lane-ribbon')))


def test_live_rotation_is_not_managed_by_reapply():
    m, layout = fixture()
    out = postprocess(m, layout, {}, (0, 0, 0))
    key = slot_key_by_name(out, 'market-product-holo-driven')
    node = next(n for n in nodes(out) if n['slot']['key'] == key)
    assert 'rotation' not in node['slot']
    assert 'rotation' not in node['slot']['managedFields']
    assert next(c for c in node['components'] if c['type'] == 'FrooxEngine.Spinner')['fields']['_target'] == f'$slot-member:{key}.Rotation'
    assert all(c['type'] != 'FrooxEngine.Spinner' for n in nodes(out)
               if n['slot']['name'] in ('nightlife-info-ad-driven', 'east-lane-ribbon-driven')
               for c in n.get('components', []))


def test_scan_clones_only_driven_material_and_pans_texture_not_slot():
    m, layout = fixture()
    out = postprocess(m, layout, {}, (0, 0, 0))
    info = next(n for n in nodes(out) if n['slot']['name'] == 'nightlife-info-ad-driven')
    fixed = next(n for n in nodes(out) if n['slot']['name'] == 'nightlife-info-ad-projector')
    driven_refs = next(c for c in info['components'] if c['type'] == 'FrooxEngine.MeshRenderer')['fields']['Materials']
    fixed_refs = next(c for c in fixed['components'] if c['type'] == 'FrooxEngine.MeshRenderer')['fields']['Materials']
    assert '$component:mat_material_Slum03_holo_cyan_a06e351f' in fixed_refs
    assert '$component:mat_material_Slum03_holo_cyan_a06e351f' not in driven_refs
    panners = [c for n in nodes(out) for c in n.get('components', []) if c['type'] == 'FrooxEngine.Panner2D']
    assert panners and all(c['fields']['_target'].startswith('$member:') for c in panners)
    assert all(c['type'] != 'FrooxEngine.Spinner' for c in info['components'])
    assert postprocess(out, layout, {}, (0, 0, 0)) == out


def test_missing_or_ambiguous_driven_slot_fails():
    for mode in ('missing', 'duplicate'):
        m, layout = fixture()
        node = next(n for n in nodes(m) if n['slot']['name'] == 'market-product-holo-driven')
        if mode == 'missing':
            node['slot']['name'] = 'renamed'
        else:
            clone = copy.deepcopy(node)
            clone['slot']['key'] = 'duplicate-driven-key'
            m['children'].append(clone)
        with pytest.raises(ValueError, match='market-product-holo-driven'):
            postprocess(m, layout, {}, (0, 0, 0))
