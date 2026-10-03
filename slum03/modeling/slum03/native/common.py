"""Owned manifest traversal and deterministic slot keys; no ResoniteLink IDs."""
from __future__ import annotations
import math
from typing import Any, Iterator
from modeling.slum03.types import Manifest


def walk(manifest: Manifest) -> Iterator[Manifest]:
    yield manifest
    for child in manifest.get('children', []):
        yield from walk(child)


def slot_key_by_name(manifest: Manifest, name: str) -> str:
    matches = [n['slot']['key'] for n in walk(manifest) if n['slot'].get('name') == name]
    if len(matches) != 1:
        raise ValueError(f'expected exactly one slot named {name!r}; found {len(matches)}')
    return matches[0]


def yaw(degrees: float) -> list[float]:
    half = math.radians(degrees) / 2
    return [0., round(math.sin(half), 8), 0., round(math.cos(half), 8)]


def node(key: str, name: str, position=(0, 0, 0), rotation=None) -> Manifest:
    return {'slot': {'key': key, 'name': name, 'position': list(position),
                     'rotation': list(rotation) if rotation is not None else [0, 0, 0, 1],
                     'scale': [1, 1, 1]}, 'components': []}


def group(root: Manifest, key: str) -> Manifest:
    for child in root.setdefault('children', []):
        if child['slot']['key'] == key:
            return child
    child = node(key, f'Slum03_{key}')
    child['children'] = []
    root['children'].append(child)
    return child


def add_child(parent: Manifest, child: Manifest) -> None:
    if not any(n['slot']['key'] == child['slot']['key'] for n in parent.setdefault('children', [])):
        parent['children'].append(child)


def add_component(parent: Manifest, component: dict[str, Any]) -> None:
    if not any(c['key'] == component['key'] for c in parent.setdefault('components', [])):
        parent['components'].append(component)
