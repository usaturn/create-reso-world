"""Render bounded offline CPU Cycles views for geometry-only spatial review."""
from __future__ import annotations

import sys
from pathlib import Path

import bpy  # type: ignore[import-not-found]

output = Path(sys.argv[sys.argv.index("--") + 1])
output.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 8
scene.cycles.use_denoising = True
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False

views = (
    ("plaza-eye-offline.png", "PREVIEW_ONLY_PlazaEyeLevel"),
    ("city-overhead-offline.png", "PREVIEW_ONLY_CityOverhead"),
    ("clinic-interior-offline.png", "PREVIEW_ONLY_ClinicInterior"),
    ("theatre-interior-offline.png", "PREVIEW_ONLY_TheatreInterior"),
    ("roof-overlook-offline.png", "PREVIEW_ONLY_RoofOverlook"),
)
for filename, camera_name in views:
    dome = next((obj for obj in bpy.data.objects if obj.type == "MESH" and "night_sky_dome" in obj.name.lower()), None)
    restore_dome = dome.hide_render if dome is not None else None
    if camera_name == "PREVIEW_ONLY_CityOverhead" and dome is not None:
        # The canopy masks an overhead reviewer camera near its inner surface; the live dome is untouched.
        dome.hide_render = True
    camera = bpy.data.objects.get(camera_name)
    if camera is None:
        raise RuntimeError(f"offline review camera is missing: {camera_name}")
    scene.camera = camera
    scene.render.filepath = str(output / filename)
    interior_emissions = []
    if camera_name in {"PREVIEW_ONLY_ClinicInterior", "PREVIEW_ONLY_TheatreInterior"}:
        # A low base-color emission fill keeps geometry legible in these design-review images only.
        for material in bpy.data.materials:
            if not material.name.startswith("TokyoNova_") or not material.use_nodes:
                continue
            for node in material.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    color = node.inputs["Base Color"].default_value[:]
                    emission = node.inputs["Emission Color"].default_value[:]
                    strength = node.inputs["Emission Strength"].default_value
                    interior_emissions.append((node, color, emission, strength))
                    node.inputs["Emission Color"].default_value = color
                    node.inputs["Emission Strength"].default_value = 0.18
    bpy.ops.render.render(write_still=True)
    for node, _color, emission, strength in interior_emissions:
        node.inputs["Emission Color"].default_value = emission
        node.inputs["Emission Strength"].default_value = strength
    if dome is not None and restore_dome is not None:
        dome.hide_render = restore_dome
    path = output / filename
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"offline preview was not written: {path}")
    print(f"OFFLINE_CITY_PREVIEW={path} bytes={path.stat().st_size}")

report_path = bpy.path.abspath("//city-resource-report.json")
if Path(report_path).is_file():
    import json

    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    report["offline_render_status"] = "rendered with Blender CPU Cycles at 640x360, 8 samples; geometry review only"
    report["offline_previews"] = [{"file": filename, "camera": camera_name, "width": 640, "height": 360, "samples": 8} for filename, camera_name in views]
    report["interior_preview_note"] = "Temporary 0.18 base-color emission fill was applied only during interior geometry previews; it was restored before saving and is absent from the live manifest."
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
