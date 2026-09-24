"""Shared authored Principled material palette and explicit transfer adaptation."""
from __future__ import annotations

from typing import Any

ADAPTATION_NOTE = (
    "This north-sector source uses no image maps: the current Linux-to-Windows image path has "
    "no verified shared mount. Instead, supported Principled base color/metallic/roughness "
    "parameters are shared by material, and individually modeled paint loss, rust streaks, "
    "concrete patches, cracks, seams and damp-versus-dry surfaces carry the visual variation. "
    "No authored image map is silently replaced by a flat material."
)

_MATERIALS: dict[str, dict[str, Any]] = {
    "concrete": {"base_color": (0.31, 0.29, 0.25, 1), "metallic": 0.0, "roughness": 0.91},
    "patched_concrete": {"base_color": (0.39, 0.36, 0.30, 1), "metallic": 0.0, "roughness": 0.86},
    "painted_metal": {"base_color": (0.31, 0.18, 0.12, 1), "metallic": 0.72, "roughness": 0.56},
    "faded_teal": {"base_color": (0.10, 0.26, 0.25, 1), "metallic": 0.42, "roughness": 0.67},
    "exposed_metal": {"base_color": (0.38, 0.40, 0.39, 1), "metallic": 0.83, "roughness": 0.39},
    "rust": {"base_color": (0.34, 0.105, 0.035, 1), "metallic": 0.57, "roughness": 0.82},
    "cloth": {"base_color": (0.40, 0.28, 0.15, 1), "metallic": 0.0, "roughness": 0.96},
    "ceramic": {"base_color": (0.76, 0.72, 0.62, 1), "metallic": 0.0, "roughness": 0.27},
    "plastic": {"base_color": (0.12, 0.16, 0.17, 1), "metallic": 0.04, "roughness": 0.48},
    "cream_plastic": {"base_color": (0.62, 0.55, 0.40, 1), "metallic": 0.02, "roughness": 0.63},
    "rubber": {"base_color": (0.025, 0.03, 0.032, 1), "metallic": 0.0, "roughness": 0.88},
    "glass": {"base_color": (0.13, 0.21, 0.25, 1), "metallic": 0.23, "roughness": 0.18},
    "wood": {"base_color": (0.23, 0.12, 0.055, 1), "metallic": 0.0, "roughness": 0.84},
    "asphalt_dry": {"base_color": (0.075, 0.083, 0.084, 1), "metallic": 0.02, "roughness": 0.95},
    "asphalt_wet": {"base_color": (0.045, 0.065, 0.073, 1), "metallic": 0.19, "roughness": 0.28},
    "warm_light": {"base_color": (0.9, 0.38, 0.10, 1), "metallic": 0.0, "roughness": 0.37, "emission": (1.0, 0.31, 0.07, 1), "emission_strength": 0.35},
    "cool_light": {"base_color": (0.16, 0.44, 0.52, 1), "metallic": 0.0, "roughness": 0.46, "emission": (0.06, 0.28, 0.39, 1), "emission_strength": 0.20},
}


def build_materials() -> dict[str, dict[str, Any]]:
    """Return a fresh, shared set of export-supported Principled material parameters."""
    return {
        name: {
            **values,
            "base_color": tuple(values["base_color"]),
            "emission": tuple(values["emission"]) if "emission" in values else None,
        }
        for name, values in _MATERIALS.items()
    }


def make_blender_materials() -> dict[str, Any]:
    """Create reusable Blender Principled materials; requires Blender's ``bpy`` runtime."""
    import bpy  # type: ignore[import-not-found]

    created: dict[str, Any] = {}
    for name, settings in build_materials().items():
        material = bpy.data.materials.get(f"TokyoNova_{name}") or bpy.data.materials.new(f"TokyoNova_{name}")
        material.diffuse_color = settings["base_color"]
        material.use_nodes = True
        shader = material.node_tree.nodes.get("Principled BSDF")
        if shader is None:
            raise RuntimeError(f"Blender material {material.name} is missing Principled BSDF")
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
