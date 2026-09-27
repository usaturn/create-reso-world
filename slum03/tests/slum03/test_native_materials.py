from dataclasses import replace
import copy
import glob
import json
import pytest

from modeling.slum03.postprocess import postprocess
from modeling.slum03.layout import build_layout


def bundle():
    path = glob.glob('artifacts/slum03/task8-final-*/bundle/model.apply.json')[0]
    return json.load(open(path, encoding='utf-8'))


def nodes(root):
    yield root
    for child in root.get('children', []):
        yield from nodes(child)


def test_exported_palette_providers_become_vertex_color_or_holo_without_losing_renderer_refs():
    source = bundle()
    source['ownership']['key'] = 'slum03'
    source['slot']['name'] = 'Slum03_Slum'
    before = copy.deepcopy(source)
    out = postprocess(source, replace(build_layout(), labels=tuple(l for l in build_layout().labels if l.parent_name in ('market-product-holo', 'nightlife-info-ad', 'east-lane-ribbon'))), {}, (0, 0, 0))
    assert source == before
    components = {c['key']: c for n in nodes(out) for c in n.get('components', [])}
    assert components['mat_material_Slum03_steel_dark_498bd928']['type'] == 'FrooxEngine.PBS_VertexColorMetallic'
    assert components['mat_material_Slum03_steel_dark_498bd928']['fields']['VertexColorTarget'] == 'Albedo'
    holo = components['mat_material_Slum03_holo_cyan_a06e351f']
    assert holo['type'] == 'FrooxEngine.FresnelMaterial'
    assert holo['fields']['NearTexture'] == '$component:tex-noise-holo'
    for c in components.values():
        if c['type'] == 'FrooxEngine.MeshRenderer':
            assert all(ref.removeprefix('$component:') in components for ref in c['fields']['Materials'])
    assert postprocess(out, replace(build_layout(), labels=tuple(l for l in build_layout().labels if l.parent_name in ('market-product-holo', 'nightlife-info-ad', 'east-lane-ribbon'))), {}, (0, 0, 0)) == out


def test_unknown_palette_or_provider_does_not_silently_claim_vertex_color_support():
    m = bundle()
    provider = next(c for n in nodes(m) for c in n.get('components', []) if c['type'] == 'FrooxEngine.PBS_Metallic')
    provider['key'] = 'mat_material_Slum03_unlisted_deadbeef'
    m['ownership']['key'] = 'slum03'
    m['slot']['name'] = 'Slum03_Slum'
    with pytest.raises(ValueError, match='unlisted'):
        postprocess(m, replace(build_layout(), labels=tuple(l for l in build_layout().labels if l.parent_name in ('market-product-holo', 'nightlife-info-ad', 'east-lane-ribbon'))), {}, (0, 0, 0))


def test_malformed_palette_prefixed_provider_is_rejected():
    from modeling.slum03.native.materials import add_materials
    manifest = {'slot': {'key': 'root', 'name': 'Slum03_Slum'},
                'components': [{'key': 'backdrop-north-mat_material_Slum03_holo_cyan_BADHASH',
                                'type': 'FrooxEngine.PBS_Metallic', 'fields': {}}]}
    with pytest.raises(ValueError, match='palette'):
        add_materials(manifest)
