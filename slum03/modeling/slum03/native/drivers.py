"""Offline motion candidates. Spin owns Rotation; scan pans cloned material only."""
from __future__ import annotations
import copy
from modeling.slum03.ads import build_assemblies
from modeling.slum03.materials import MATERIALS
from modeling.slum03.types import Layout
from .common import add_component, add_child, group, node, slot_key_by_name, walk
from .materials import palette_name


def add_drivers(manifest: dict, layout: Layout) -> None:
    motions = [a.meta['motion'] for a in build_assemblies(layout, 'ads') if a.meta.get('motion')]
    for motion in motions:
        name = motion['driven_name']
        slot_key = slot_key_by_name(manifest, name)
        driven = next(n for n in walk(manifest) if n['slot']['key'] == slot_key)
        if motion['kind'] == 'spin':
            add_component(driven, {'key': f'spinner-{slot_key}', 'type': 'FrooxEngine.Spinner',
                                   'fields': {'_target': f'$slot-member:{slot_key}.Rotation',
                                              '_speed': [axis*motion['rate'] for axis in motion['axis']]}})
            # Do not manage runtime-driven quaternion on initial or repeated apply.
            driven['slot'].pop('rotation', None)
            driven['slot']['managedFields'] = ['position', 'scale']
        elif motion['kind'] == 'scan':
            scan_materials(manifest, driven, motion)
        else:
            raise ValueError(f'unsupported motion kind: {motion["kind"]}')


def scan_materials(manifest: dict, driven: dict, motion: dict) -> None:
    renderer = [c for c in driven.get('components', []) if c['type'] == 'FrooxEngine.MeshRenderer']
    if len(renderer) != 1:
        raise ValueError(f'scan driven mesh must have one renderer: {motion["driven_name"]}')
    providers = {c['key']: c for n in walk(manifest) for c in n.get('components', [])}
    refs = renderer[0]['fields']['Materials']
    dest = group(manifest, 'native-scan-materials')
    textures = group(manifest, 'native-textures')
    for i, ref in enumerate(refs):
        if not ref.startswith('$component:'):
            raise ValueError(f'unresolved scan material: {ref}')
        key = ref.removeprefix('$component:')
        if key.startswith('scan-'):
            continue  # already cloned on previous postprocess invocation
        provider = providers.get(key)
        if provider is None:
            raise ValueError(f'unresolved scan material: {ref}')
        name = palette_name(key)
        if name is None or MATERIALS[name].kind != 'holo':
            continue  # static hardware stays static, even on the driven mesh
        clone = copy.deepcopy(provider)
        clone['key'] = f'scan-{driven["slot"]["key"]}-{key}'
        holder = node(f'provider-{clone["key"]}', clone['key'])
        holder['components'] = [clone]
        add_child(dest, holder)
        refs[i] = f'$component:{clone["key"]}'
        for side in ('Near', 'Far'):
            axis = 0 if motion['axis'][0] else 1
            speed = [0., 0.]
            # cycles/s, not degrees/s or a whole-panel rotation. One tile of
            # TextureScale traversed each 1/rate seconds (verify in live QA).
            speed[axis] = motion['rate'] / MATERIALS[name].texture_scale[axis]
            key = f'panner-{clone["key"]}-{side.lower()}'
            holder = node(f'driver-{key}', key)
            add_component(holder, {'key': key,
                                     'type': 'FrooxEngine.Panner2D',
                                     'identityFields': ['_target'],
                                     'fields': {'_target': f'$member:{clone["key"]}.{side}TextureOffset',
                                                '_speed': speed, '_repeat': [1., 1.]}})
            add_child(textures, holder)
