import copy
from dataclasses import replace
import pytest
from modeling.slum03.layout import build_layout
from modeling.slum03.native.text import add_labels
from modeling.slum03.types import LabelSpec


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
    add_labels(m, layout)
    out = m
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
        add_labels(m, layout)


def test_japanese_main_copy_stays_on_fixed_parent_with_exact_unicode():
    m, layout = fixture()
    label = LabelSpec('jp-product-copy', '義眼の未来', 'market-product-holo',
                      (0, 1.2, 1.35), 0., 1.1, (.3, 1., 1., 1.))
    add_labels(m, replace(layout, labels=layout.labels + (label,)))
    entry = next(n for n in nodes(m) if n['slot']['key'] == 'label-jp-product-copy')
    assert entry['slot']['parent'] == '$slot:object_market-product-holo'
    assert entry['slot']['position'] == [0, 1.2, 1.35]
    assert entry['components'][0]['fields']['Text'] == '義眼の未来'
    assert all(entry['slot']['parent'] != f'$slot:{n["slot"]["key"]}' for n in nodes(m)
               if n['slot'].get('name', '').endswith('-driven'))
