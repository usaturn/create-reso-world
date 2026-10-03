"""Explicit sector registry. Absent generators must never silently export an empty scene."""
from __future__ import annotations
from collections.abc import Callable
from typing import Any
from .geometry import Assembly
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
    if layout.density is not None and sector in ('ruins-west', 'ruins-north', 'ruins-east',
                                                  'shacks', 'market', 'nightlife'):
        # New layouts can mix uses inside a physical sector; generators filter by
        # kind themselves. Preserve legacy dispatch byte-for-byte.
        from . import ruins, shacks, stalls
        builders = {'ruin': ruins.build_assemblies, 'shack': shacks.build_assemblies,
                    'stall': stalls.build_assemblies, 'nightlife': nightlife.build_assemblies}
        targets = [p for p in layout.placements if p.sector == sector]
        unsupported = {p.kind for p in targets} - builders.keys()
        if unsupported:
            raise NotImplementedError(f'{sector}: unsupported density kinds {sorted(unsupported)}')
        built = {a.name: a for kind, builder in builders.items()
                 for a in builder(layout, sector) if kind == a.kind}
        if len(built) != len(targets) or set(built) != {p.key for p in targets}:
            raise ValueError(f'{sector}: density assembly missing or duplicated')
        result = [built[p.key] for p in targets]
    else:
        result = REGISTRY[sector](layout, sector)
    if not result or not any(a.parts for a in result) or any(
            a.sector != sector or (not a.parts and not a.meta.get('anchor')) for a in result):
        raise ValueError(f'sector {sector} returned no valid meshes')
    return result


from . import ground, plaza, ruins, shacks, overhead, stalls, nightlife, yarol, road_river, forest, backdrop, ads

register('ground')(ground.build_assemblies)
register('plaza')(plaza.build_assemblies)
for _sector in ('ruins-west', 'ruins-north', 'ruins-east'):
    register(_sector)(ruins.build_assemblies)
register('shacks')(shacks.build_assemblies)
register('market')(stalls.build_assemblies)
register('nightlife')(nightlife.build_assemblies)
register('yarol')(yarol.build_assemblies)
register('overhead')(overhead.build_assemblies)
register('ads')(ads.build_assemblies)
register('road-river')(road_river.build_assemblies)
register('forest')(forest.build_assemblies)
register_blender_hook('forest')(forest.add_canopy)
for _sector in ('backdrop-north', 'backdrop-west-south'):
    register(_sector)(backdrop.build_assemblies)
register_blender_hook('plaza')(plaza.add_plaza)
