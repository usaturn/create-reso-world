"""Shared material palette for slum03 (Blender-linear colours, see spec).

Blender carries only constant Principled values; runtime detail comes from
vertex colours (vcolor.py) and engine NoiseTextures (postprocess.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BLENDER_PREFIX = "Slum03_"


@dataclass(frozen=True)
class MaterialSpec:
    base_color: tuple[float, float, float]
    metallic: float
    roughness: float
    kind: Literal["vc", "neon", "holo"]
    family: str
    emission: tuple[float, float, float] | None = None
    emission_strength: float = 0.0
    noise: str | None = None
    texture_scale: tuple[float, float] = (1.0, 1.0)


@dataclass(frozen=True)
class NoiseSpec:
    seed: int
    size: int
    low: float
    high: float
    bias: float = 0.0
    gain: float = 0.0


def _vc(rgb, met, rough, family, noise=None, scale=(1.0, 1.0)) -> MaterialSpec:
    return MaterialSpec(rgb, met, rough, "vc", family, noise=noise, texture_scale=scale)


def _glow(kind, rgb, strength, rough, noise=None, scale=(1.0, 1.0)) -> MaterialSpec:
    base = tuple(round(c * 0.2, 4) for c in rgb)
    return MaterialSpec(base, 0.0, rough, kind, kind, emission=rgb, emission_strength=strength, noise=noise, texture_scale=scale)  # type: ignore[arg-type]


NOISES: dict[str, NoiseSpec] = {
    "concrete": NoiseSpec(seed=11, size=256, low=0.72, high=1.0),
    "asphalt": NoiseSpec(seed=12, size=256, low=0.62, high=1.0),
    "metal": NoiseSpec(seed=13, size=256, low=0.70, high=1.0),
    "wood": NoiseSpec(seed=14, size=128, low=0.75, high=1.0),
    "fabric": NoiseSpec(seed=15, size=128, low=0.82, high=1.0),
    "holo": NoiseSpec(seed=16, size=128, low=0.25, high=1.0),
}


MATERIALS: dict[str, MaterialSpec] = {
    # Concrete / masonry.
    "concrete_raw": _vc((0.34, 0.33, 0.31), 0, 0.92, "concrete", "concrete", (0.35, 0.35)),
    "concrete_dark": _vc((0.20, 0.195, 0.19), 0, 0.94, "concrete", "concrete", (0.35, 0.35)),
    "concrete_stained": _vc((0.27, 0.25, 0.21), 0, 0.95, "concrete", "concrete", (0.3, 0.3)),
    "concrete_patch": _vc((0.42, 0.40, 0.36), 0, 0.86, "concrete", "concrete", (0.5, 0.5)),
    "factory_floor": _vc((0.30, 0.29, 0.27), 0, 0.80, "concrete", "concrete", (0.25, 0.25)),
    # Ground.
    "asphalt": _vc((0.07, 0.072, 0.075), 0, 0.93, "asphalt", "asphalt", (0.4, 0.4)),
    "asphalt_wet": _vc((0.035, 0.042, 0.05), 0.1, 0.12, "wet"),
    "mud": _vc((0.13, 0.10, 0.07), 0, 0.97, "ground", "asphalt", (0.5, 0.5)),
    # Metal / rust.
    "rust": _vc((0.36, 0.11, 0.035), 0.55, 0.80, "rust", "metal", (0.8, 0.8)),
    "rust_dark": _vc((0.19, 0.065, 0.03), 0.5, 0.85, "rust", "metal", (0.8, 0.8)),
    "steel_bare": _vc((0.40, 0.41, 0.41), 0.9, 0.42, "metal", "metal", (1.0, 1.0)),
    "steel_dark": _vc((0.09, 0.095, 0.10), 0.75, 0.50, "metal", "metal", (1.0, 1.0)),
    "paint_yellow_faded": _vc((0.46, 0.33, 0.07), 0.3, 0.62, "painted", "metal", (0.8, 0.8)),
    "paint_teal_faded": _vc((0.06, 0.22, 0.22), 0.3, 0.62, "painted", "metal", (0.8, 0.8)),
    "corrugated": _vc((0.32, 0.31, 0.29), 0.65, 0.58, "metal", "metal", (0.8, 0.8)),
    "corrugated_rust": _vc((0.42, 0.21, 0.10), 0.55, 0.74, "rust", "metal", (0.8, 0.8)),
    # Wood.
    "plywood": _vc((0.40, 0.28, 0.16), 0, 0.86, "wood", "wood", (1.2, 0.4)),
    "pallet_wood": _vc((0.33, 0.25, 0.16), 0, 0.90, "wood", "wood", (1.2, 0.4)),
    # Fabric / plastic.
    "tarp_blue": _vc((0.05, 0.13, 0.33), 0, 0.66, "fabric", "fabric", (1.5, 1.5)),
    "tarp_orange": _vc((0.50, 0.17, 0.04), 0, 0.70, "fabric", "fabric", (1.5, 1.5)),
    "tarp_green": _vc((0.07, 0.20, 0.09), 0, 0.70, "fabric", "fabric", (1.5, 1.5)),
    "cloth_red": _vc((0.35, 0.02, 0.04), 0, 0.75, "fabric", "fabric", (2.0, 2.0)),
    "plastic_crate": _vc((0.08, 0.20, 0.35), 0, 0.50, "plastic", "fabric", (2.0, 2.0)),
    "rubber": _vc((0.025, 0.025, 0.028), 0, 0.85, "plastic"),
    "glass_dark": _vc((0.03, 0.045, 0.05), 0.2, 0.08, "glass"),
    "electronics": _vc((0.05, 0.12, 0.06), 0.4, 0.45, "metal", "metal", (3.0, 3.0)),
    # Paint / backdrop.
    "spray_red": _vc((0.55, 0.012, 0.012), 0, 0.62, "paint"),
    "spray_black": _vc((0.012, 0.012, 0.014), 0, 0.70, "paint"),
    "backdrop_mass": _vc((0.035, 0.037, 0.045), 0.1, 0.80, "backdrop"),
    "backdrop_ground": _vc((0.03, 0.03, 0.033), 0, 0.95, "backdrop"),
    # Neon.
    "neon_magenta": _glow("neon", (1.0, 0.05, 0.6), 6, 0.35),
    "neon_cyan": _glow("neon", (0.05, 0.9, 1.0), 6, 0.35),
    "neon_lime": _glow("neon", (0.55, 1.0, 0.05), 5, 0.35),
    "neon_orange": _glow("neon", (1.0, 0.35, 0.02), 5, 0.35),
    "neon_pink": _glow("neon", (1.0, 0.25, 0.55), 6, 0.35),
    "neon_red": _glow("neon", (1.0, 0.03, 0.03), 6, 0.35),
    "warm_bulb": _glow("neon", (1.0, 0.55, 0.2), 4, 0.40),
    "window_lit": _glow("neon", (1.0, 0.7, 0.35), 2.5, 0.40),
    # Holo.
    "holo_magenta": _glow("holo", (1.0, 0.08, 0.7), 1, 0.1, noise="holo", scale=(1.0, 4.0)),
    "holo_cyan": _glow("holo", (0.05, 0.85, 1.0), 1, 0.1, noise="holo", scale=(1.0, 4.0)),
    "holo_lime": _glow("holo", (0.5, 1.0, 0.1), 1, 0.1, noise="holo", scale=(1.0, 4.0)),
    "holo_orange": _glow("holo", (1.0, 0.45, 0.05), 1, 0.1, noise="holo", scale=(1.0, 4.0)),
    "holo_cyan_scroll": _glow("holo", (0.05, 0.85, 1.0), 1, 0.1, noise="holo", scale=(1.0, 4.0)),
    "holo_magenta_scroll": _glow("holo", (1.0, 0.08, 0.7), 1, 0.1, noise="holo", scale=(1.0, 4.0)),
}


def make_blender_materials() -> dict[str, "bpy.types.Material"]:  # type: ignore[name-defined]
    """Create reusable Blender Principled materials; requires Blender's ``bpy`` runtime.

    Keys are palette names, so callers look up materials by the same string stored on
    ``geometry.MeshData.material``. Blender datablocks are named ``Slum03_<palette name>``
    and are reused when they already exist, so repeated calls converge without duplicates.
    """
    import bpy  # type: ignore[import-not-found]

    created: dict[str, "bpy.types.Material"] = {}  # type: ignore[name-defined]
    for name, spec in MATERIALS.items():
        material = bpy.data.materials.get(f"{BLENDER_PREFIX}{name}") or bpy.data.materials.new(f"{BLENDER_PREFIX}{name}")
        if material.node_tree is None:
            # Blender 5.0 creates the node tree with the material; older releases need the flag.
            material.use_nodes = True
        shader = material.node_tree.nodes.get("Principled BSDF")
        if shader is None:
            raise RuntimeError(f"Blender material {material.name} is missing Principled BSDF")
        shader.inputs["Base Color"].default_value = (*spec.base_color, 1.0)
        shader.inputs["Metallic"].default_value = spec.metallic
        shader.inputs["Roughness"].default_value = spec.roughness
        if spec.emission is not None:
            shader.inputs["Emission Color"].default_value = (*spec.emission, 1.0)
            shader.inputs["Emission Strength"].default_value = spec.emission_strength
        material.use_fake_user = True
        created[name] = material
    return created
