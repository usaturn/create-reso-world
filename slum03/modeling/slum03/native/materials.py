"""Offline candidates adapted from slum02/postprocess.py; NOT current Reflection evidence."""
from __future__ import annotations
import re
from modeling.slum03.materials import MATERIALS, NOISES
from .common import add_component, group, walk

# Merge may prepend one or more sector names (including hyphenated names).
_NAME = re.compile(r'(?:[a-z0-9-]+-)?mat_material_Slum03_(.+)_[0-9a-f]{8}$')


def palette_name(key: str) -> str | None:
    m = _NAME.fullmatch(key)
    return m.group(1) if m else None


def noise(name: str) -> dict:
    n = NOISES[name]
    return {'key': f'tex-noise-{name}', 'type': 'FrooxEngine.NoiseTexture',
            'identityFields': ['Seed'], 'fields': {
                'Size': [n.size, n.size], 'Seed': n.seed, 'Monochrome': True,
                'MonochromeMin': [n.low, n.low, n.low, 1.],
                'MonochromeMax': [n.high, n.high, n.high, 1.],
                'Bias': n.bias, 'Gain': n.gain, 'FilterMode': 'Anisotropic',
                'WrapModeU': 'Repeat', 'WrapModeV': 'Repeat', 'Mipmaps': True}}


def convert(component: dict, name: str) -> dict:
    spec = MATERIALS[name]
    if spec.kind == 'holo':
        rgb = spec.emission
        return {'key': component['key'], 'type': 'FrooxEngine.FresnelMaterial',
                'fields': {'NearColor': [c*.35 for c in rgb] + [.25],
                           'FarColor': [min(1., c*1.2) for c in rgb] + [.85],
                           'Exponent': 1.6, 'GammaCurve': 1., 'BlendMode': 'Additive',
                           'Sidedness': 'Double', 'ZWrite': 'Off', 'UseVertexColors': False,
                           'NearTexture': '$component:tex-noise-holo',
                           'FarTexture': '$component:tex-noise-holo',
                           'NearTextureScale': list(spec.texture_scale),
                           'FarTextureScale': list(spec.texture_scale)}}
    fields = {key: component.get('fields', {})[key] for key in
              ('AlbedoColor', 'Metallic', 'Smoothness', 'EmissiveColor')
              if key in component.get('fields', {})}
    fields.update({'VertexColorTarget': 'Albedo', 'VertexColorInterpolationSpace': 'Linear',
                   'AlphaHandling': 'Opaque', 'Culling': 'Back',
                   'TextureScale': list(spec.texture_scale)})
    if spec.noise:
        fields['AlbedoTexture'] = f'$component:tex-noise-{spec.noise}'
    return {'key': component['key'], 'type': 'FrooxEngine.PBS_VertexColorMetallic', 'fields': fields}


def add_materials(manifest: dict) -> None:
    for n in walk(manifest):
        for i, component in enumerate(n.get('components', [])):
            if component['type'] != 'FrooxEngine.PBS_Metallic':
                continue
            key = component['key']
            name = palette_name(key)
            if name is not None and name not in MATERIALS:
                raise ValueError(f'unknown slum03 palette provider: {key}')
            if name is not None and name in MATERIALS:
                n['components'][i] = convert(component, name)
    textures = group(manifest, 'native-textures')
    for name in NOISES:
        add_component(textures, noise(name))
