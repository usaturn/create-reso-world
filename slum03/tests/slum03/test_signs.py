import copy
from dataclasses import replace
import pytest
from modeling.slum03.layout import build_layout
from modeling.slum03.postprocess import postprocess


def fixture():
    m = {'schemaVersion': '1', 'ownership': {'key': 'slum03'},
         'slot': {'key': 'root', 'name': 'Slum03_Slum', 'parent': 'Root'},
         'children': [{'slot': {'key': f'object_{key}', 'name': key}} for key in
                      ('yarol', 'nightlife-east', 'nightlife-velvet', 'market-west',
                       'market-product-holo', 'nightlife-info-ad', 'east-lane-ribbon')]}
    return m, build_layout()


def nodes(n):
    yield n
    for c in n.get('children', []):
        yield from nodes(c)


def test_labels_have_fixed_parent_local_pose_and_readable_copy():
    m, layout = fixture()
    out = postprocess(m, layout, {}, (0, 0, 0))
    yarol = next(n for n in nodes(out) if n['slot']['key'] == 'label-yarol-sign')
    assert yarol['slot']['parent'] == '$slot:object_yarol'
    assert yarol['slot']['position'] == [5.9, 4, 0]
    assert yarol['components'][0]['fields']['Text'] == 'Yarol'
    assert any(c['fields']['Text'] == 'NIGHT SHIFT' for n in nodes(out)
               for c in n.get('components', []) if c['type'] == 'FrooxEngine.TextRenderer')
    assert all('rotation' in n['slot'] for n in nodes(out) if n['slot']['key'].startswith('label-'))


@pytest.mark.parametrize('mode', ['missing', 'ambiguous'])
def test_label_parent_must_resolve_uniquely(mode):
    m, layout = fixture()
    if mode == 'missing':
        m['children'][0]['slot']['name'] = 'other'
    else:
        m['children'].append({'slot': {'key': 'copy-yarol', 'name': 'yarol'}})
    with pytest.raises(ValueError, match='yarol'):
        postprocess(m, layout, {}, (0, 0, 0))
