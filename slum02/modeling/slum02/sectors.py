"""Sector registry: sector name -> pure Assembly generator (no bpy).

Generator modules self-register with ``@register("<sector>")``. Sectors that need
extra Blender-side objects (e.g. the plaza Geometry Nodes scatter) additionally
register ``@register_blender_hook("<sector>")``; the hook is called by
``build.write_scene`` as ``hook(bpy, bmesh, data, material_lookup, export_collection)``
and returns ``(extra_objects, extra_report)``.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from modeling.slum02.geometry import Assembly, merge_assembly

SECTORS: tuple[str, ...] = ("ground", "plaza", "towers-a", "towers-b", "towers-c", "market",
                            "nightlife", "shacks", "ads", "overhead", "backdrop")
REGISTRY: dict[str, Callable[[dict[str, Any]], list[Assembly]]] = {}
BLENDER_HOOKS: dict[str, Callable[..., tuple[list[Any], dict[str, Any]]]] = {}


def register(name: str):
    if name not in SECTORS:
        raise ValueError(name)

    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


def register_blender_hook(name: str):
    if name not in SECTORS:
        raise ValueError(name)

    def deco(fn):
        BLENDER_HOOKS[name] = fn
        return fn
    return deco


def _load_generators() -> None:
    # Imported lazily so each generator module self-registers; missing ones stay unregistered.
    import importlib
    for module in ("ground", "plaza", "towers", "stalls", "nightlife", "shacks", "ads", "overhead"):
        try:
            importlib.import_module(f"modeling.slum02.{module}")
        except ModuleNotFoundError as exc:
            if exc.name != f"modeling.slum02.{module}":
                raise


def sector_assemblies(data: dict[str, Any], sector: str) -> list[Assembly]:
    if sector not in SECTORS:
        raise KeyError(sector)
    _load_generators()
    if sector not in REGISTRY:
        raise NotImplementedError(f"sector {sector} has no generator yet")
    return REGISTRY[sector](data)


def resource_report(assemblies: list[Assembly], sector: str) -> dict[str, Any]:
    tris = verts = subs = 0
    mats: set[str] = set()
    for a in assemblies:
        m = merge_assembly(a)
        tris += sum(len(f) - 2 for f in m.faces)
        verts += len(m.vertices)
        subs += len(m.materials)
        mats.update(m.materials)
    return {"sector": sector, "objects": len(assemblies), "triangles": tris, "vertices": verts,
            "submeshes": subs, "materials": sorted(mats), "material_count": len(mats)}
