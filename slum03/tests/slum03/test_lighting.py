from dataclasses import replace
from modeling.slum03.layout import build_layout
from modeling.slum03.native.lighting import light_slots
from modeling.slum03.postprocess import postprocess


def test_lights_are_local_and_only_inside_owned_root():
    layout = build_layout()
    m = {'schemaVersion': '1', 'ownership': {'key': 'slum03'},
         'slot': {'key': 'root', 'name': 'Slum03_Slum', 'parent': 'Root'}, 'children': []}
    out = postprocess(m, replace(layout, labels=()), {}, (0, 0, 0))
    group = next(c for c in out['children'] if c['slot']['key'] == 'native-lights')
    assert len(group['children']) >= 3
    assert all(child['components'][0]['type'] == 'FrooxEngine.Light' for child in group['children'])
    assert all(0 < child['components'][0]['fields']['Range'] <= 24 for child in group['children'])
    assert all(child['slot']['key'] != 'Root' for child in group['children'])
    assert light_slots(layout) == light_slots(layout)
