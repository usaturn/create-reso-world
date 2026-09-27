"""Explicit sector registry. Absent generators must never silently export an empty scene."""
from __future__ import annotations
from collections.abc import Callable
from typing import Any
from .geometry import Assembly, box
from .types import Layout, Report

SECTORS = ('ground', 'plaza', 'ruins-west', 'ruins-north', 'ruins-east', 'market',
           'shacks', 'nightlife', 'yarol', 'overhead', 'ads', 'road-river', 'forest',
           'backdrop-north', 'backdrop-west-south')
REGISTRY: dict[str, Callable[[Layout, str], list[Assembly]]] = {}
BLENDER_HOOKS: dict[str, Callable[[Any, Layout, dict, Any, Any], tuple[list[Any], Report]]] = {}


def register(sector: str):
    if sector not in SECTORS:
        raise KeyError(sector)
    def decorator(fn):
        if sector in REGISTRY:
            raise ValueError(f'duplicate sector: {sector}')
        REGISTRY[sector] = fn
        return fn
    return decorator


def register_blender_hook(sector: str):
    if sector not in SECTORS:
        raise KeyError(sector)
    def decorator(fn):
        if sector in BLENDER_HOOKS:
            raise ValueError(f'duplicate Blender hook: {sector}')
        BLENDER_HOOKS[sector] = fn
        return fn
    return decorator


def sector_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    if sector not in SECTORS:
        raise KeyError(sector)
    if sector not in REGISTRY:
        raise NotImplementedError(f'sector {sector} has no generator yet')
    result = REGISTRY[sector](layout, sector)
    if not result or any(a.sector != sector or not a.parts for a in result):
        raise ValueError(f'sector {sector} returned no valid meshes')
    return result


@register('ground')
def ground_assemblies(layout: Layout, sector: str) -> list[Assembly]:
    """District foundation only; all other district features have separate sectors."""
    x, z = layout.district.size
    return [Assembly('foundation', 'district-foundation', sector, (0, 0, 0),
                     [box('foundation', (0, -0.15, 0), (x, 0.3, z), 'concrete_raw')],
                     {'placement_key': 'district-foundation'})]
