"""Shared flat Principled palette for the akichi cyberpunk slum.

Image textures are intentionally unused: the dev container has no verified shared mount for
the Windows Resonite host, so `ImportTexture2DFile` cannot read a path. Surface variation is
carried by these flat Principled parameters (colour, metallic, roughness, emission) plus
modelled detail geometry (rust streaks, cracks, patch edges).

Only base color, metallic, roughness and - for emissive materials - Emission Color plus
Emission Strength may be connected. No bump, procedural texture or mix node is authored.
"""
from __future__ import annotations

from typing import Any

# Blender material name prefix, kept distinct from the palette keys used by mesh builders.
BLENDER_MATERIAL_PREFIX = "Akichi_"

# Emissive base colours are derived from the emission colour so a lit sign does not blow out
# under its own emission strength.
_EMISSIVE_BASE_SCALE = 0.25

# Ordered neon palette used to cycle sign colours deterministically.
NEON_COLORS: list[str] = [
    "neon_magenta",
    "neon_cyan",
    "neon_orange",
    "neon_purple",
    "neon_lime",
    "neon_pink",
]


def _flat(base_color: tuple[float, float, float], metallic: float, roughness: float) -> dict[str, Any]:
    """Build a non-emissive flat Principled entry with an opaque alpha."""
    return {"base_color": (*base_color, 1.0), "metallic": metallic, "roughness": roughness}


def _scaled(rgb: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    """Scale an RGB triple component-wise."""
    return (rgb[0] * factor, rgb[1] * factor, rgb[2] * factor)


def _emissive(
    emission: tuple[float, float, float],
    emission_strength: float,
    metallic: float,
    roughness: float,
    base_color: tuple[float, float, float] | None = None,
) -> dict[str, Any]:
    """Build an emissive entry, deriving the base colour from the emission colour by default."""
    resolved = base_color if base_color is not None else _scaled(emission, _EMISSIVE_BASE_SCALE)
    values = _flat(resolved, metallic, roughness)
    values["emission"] = (*emission, 1.0)
    values["emission_strength"] = emission_strength
    return values


# The implementation plan's palette table is the authority for every number below.
MATERIALS: dict[str, dict[str, Any]] = {
    # Concrete and masonry.
    "concrete_dark": _flat((0.20, 0.19, 0.18), 0.0, 0.93),
    "concrete_mid": _flat((0.31, 0.29, 0.26), 0.0, 0.90),
    "concrete_stained": _flat((0.24, 0.22, 0.18), 0.0, 0.94),
    "patched_concrete": _flat((0.39, 0.36, 0.30), 0.0, 0.85),
    # Corroded and exposed metal.
    "rust": _flat((0.34, 0.105, 0.035), 0.55, 0.82),
    "rust_dark": _flat((0.22, 0.07, 0.03), 0.5, 0.86),
    "exposed_metal": _flat((0.38, 0.40, 0.39), 0.83, 0.39),
    "dark_metal": _flat((0.10, 0.11, 0.12), 0.7, 0.5),
    "painted_metal_faded": _flat((0.28, 0.20, 0.14), 0.4, 0.66),
    "corrugated": _flat((0.33, 0.31, 0.29), 0.65, 0.62),
    "corrugated_rusted": _flat((0.40, 0.22, 0.12), 0.55, 0.75),
    # Salvage sheeting and timber.
    "plywood": _flat((0.42, 0.30, 0.17), 0.0, 0.88),
    "tarp_blue": _flat((0.10, 0.16, 0.30), 0.0, 0.7),
    "tarp_orange": _flat((0.45, 0.22, 0.08), 0.0, 0.72),
    # Glazing and ground surfaces.
    "glass_dark": _flat((0.05, 0.08, 0.09), 0.3, 0.15),
    "asphalt_cracked": _flat((0.075, 0.08, 0.082), 0.02, 0.95),
    "asphalt_wet": _flat((0.045, 0.06, 0.068), 0.2, 0.25),
    "mud": _flat((0.13, 0.10, 0.07), 0.0, 0.97),
    "sign_backing": _flat((0.06, 0.06, 0.07), 0.1, 0.6),
    # Light sources and signage.
    "warm_light": _emissive((1.0, 0.42, 0.12), 3.0, 0.0, 0.4),
    "neon_magenta": _emissive((1.0, 0.05, 0.6), 5.0, 0.0, 0.35),
    "neon_cyan": _emissive((0.05, 0.9, 1.0), 5.0, 0.0, 0.35),
    "neon_orange": _emissive((1.0, 0.35, 0.02), 4.5, 0.0, 0.35),
    "neon_purple": _emissive((0.6, 0.1, 1.0), 5.0, 0.0, 0.35),
    "neon_lime": _emissive((0.55, 1.0, 0.05), 4.5, 0.0, 0.35),
    "neon_pink": _emissive((1.0, 0.3, 0.55), 5.0, 0.0, 0.35),
    "holo_panel": _emissive((0.1, 0.85, 1.0), 2.2, 0.0, 0.3, base_color=(0.02, 0.10, 0.12)),
}


def build_materials() -> dict[str, dict[str, Any]]:
    """Return a fresh copy of the palette that callers may mutate without affecting others."""
    return {name: dict(values) for name, values in MATERIALS.items()}


def make_blender_materials() -> dict[str, Any]:
    """Create reusable Blender Principled materials; requires Blender's ``bpy`` runtime.

    Keys are palette names, so callers look up materials by the same string stored on
    ``geometry.MeshData.material``. Blender datablocks are named ``Akichi_<palette name>`` and
    are reused when they already exist, so repeated calls converge without duplicates.
    """
    import bpy  # type: ignore[import-not-found]

    created: dict[str, Any] = {}
    for name, settings in build_materials().items():
        material = bpy.data.materials.get(f"{BLENDER_MATERIAL_PREFIX}{name}") or bpy.data.materials.new(
            f"{BLENDER_MATERIAL_PREFIX}{name}"
        )
        if material.node_tree is None:
            # Blender 5.0 creates the node tree with the material; older releases need the flag.
            material.use_nodes = True
        shader = material.node_tree.nodes.get("Principled BSDF")
        if shader is None:
            raise RuntimeError(f"Blender material {material.name} is missing Principled BSDF")
        material.diffuse_color = settings["base_color"]
        shader.inputs["Base Color"].default_value = settings["base_color"]
        shader.inputs["Metallic"].default_value = settings["metallic"]
        shader.inputs["Roughness"].default_value = settings["roughness"]
        emission = settings.get("emission")
        if emission is not None:
            shader.inputs["Emission Color"].default_value = emission
            shader.inputs["Emission Strength"].default_value = settings["emission_strength"]
        material.use_fake_user = True
        created[name] = material
    return created
