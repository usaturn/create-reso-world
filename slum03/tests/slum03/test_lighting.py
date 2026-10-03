import glob
import json
from dataclasses import replace
from modeling.slum03.layout import build_layout
from modeling.slum03.native.lighting import light_slots
from modeling.slum03.postprocess import postprocess


def test_lights_are_local_and_only_inside_owned_root():
    layout = build_layout()
    m = json.load(open(glob.glob('artifacts/slum03/task8-final-*/bundle/model.apply.json')[0], encoding='utf-8'))
    m['ownership']['key'] = 'slum03'
    m['slot']['name'] = 'Slum03_Slum'
    layout = replace(layout, labels=tuple(l for l in layout.labels
                                          if l.parent_name in ('market-product-holo', 'nightlife-info-ad', 'east-lane-ribbon')))
    out = postprocess(m, layout, {}, (0, 0, 0))
    group = next(c for c in out['children'] if c['slot']['key'] == 'native-lights')
    assert len(group['children']) >= 3
    assert all(child['components'][0]['type'] == 'FrooxEngine.Light' for child in group['children'])
    assert all(0 < child['components'][0]['fields']['Range'] <= 24 for child in group['children'])
    assert all(child['slot']['key'] != 'Root' for child in group['children'])
    assert light_slots(layout) == light_slots(layout)


def test_full_adds_shadowless_cluster_lights_and_keeps_existing_six():
    from pathlib import Path
    from modeling.slum03.layout import read_layout
    legacy = light_slots(build_layout())
    rep = light_slots(read_layout(Path('content/slum03/density-representative-layout.json')))
    full_layout = read_layout(Path('content/slum03/density-full-layout.json'))
    full = light_slots(full_layout)
    assert len(legacy) == len(rep) == 6
    assert full[:6] == legacy
    added = full[6:]
    assert 1 <= len(added) <= 8
    keys = [n['slot']['key'] for n in full]
    assert len(keys) == len(set(keys))
    clusters = {p.params.get('cluster') for p in full_layout.placements}
    for n in added:
        fields = n['components'][0]['fields']
        assert fields['ShadowType'] == 'None' and 0 < fields['Range'] <= 12
        assert fields['Intensity'] <= 1.2
        assert any(n['slot']['key'].endswith(c) for c in clusters if c), n['slot']['key']
