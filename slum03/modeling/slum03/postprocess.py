"""Deterministic offline native candidate postprocess; current Reflection pending.

Input must be one owned slum03 root. Never apply this document before current
Reflection, diff review, and a verified separate empty world are available.
"""
from __future__ import annotations
import copy
import math
from typing import Mapping
from modeling.slum03.types import Layout, Manifest, Report, Vec3
from .native.common import add_child, group
from .native.colliders import collider_slots
from .native.drivers import add_drivers
from .native.lighting import light_slots
from .native.materials import add_materials
from .native.text import add_labels


def choose_root_y(existing_floor_top: float | None, lowest_visible_local_y: float,
                  margin: float = 0.5) -> float:
    values = (lowest_visible_local_y, margin) if existing_floor_top is None else (existing_floor_top, lowest_visible_local_y, margin)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in values) or margin < 0:
        raise ValueError('root anchor requires finite numbers and nonnegative margin')
    return 0. if existing_floor_top is None else max(0., existing_floor_top-lowest_visible_local_y+margin)


def postprocess(manifest: Manifest, layout: Layout, reports: Mapping[str, Report],
                root_position: Vec3) -> Manifest:
    if (manifest.get('ownership', {}).get('key') != 'slum03' or
            manifest.get('slot', {}).get('key') != 'root' or
            manifest['slot'].get('name') != 'Slum03_Slum' or
            manifest['slot'].get('parent') != 'Root'):
        raise ValueError('expected Slum03_Slum owned root; never edit external content')
    if (len(root_position) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float))
            or not math.isfinite(v) for v in root_position)):
        raise ValueError('root_position must be a finite Vec3')
    result = copy.deepcopy(manifest)
    result['slot']['position'] = list(root_position)
    add_materials(result)
    colliders = group(result, 'native-colliders')
    for candidate in collider_slots(layout, dict(reports)):
        add_child(colliders, candidate)
    lights = group(result, 'native-lights')
    for candidate in light_slots(layout):
        add_child(lights, candidate)
    add_drivers(result, layout)
    add_labels(result, layout)
    return result
