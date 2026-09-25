"""Small self-review preview render (NOT final QA). Displays the Col attribute via a temporary shader tweak; never saves the .blend.

Run: resoloop blender run modeling/slum02/preview.py --arg=--blend --arg=artifacts/slum02/<S>.blend
     --arg=--output --arg=artifacts/slum02/preview/<S>-mid.png
     --arg=--camera --arg='{"position":[x,y,z],"target":[x,y,z],"fov":60}' --json
Camera coordinates are Resonite XYZ (Y up). Blender 5.0.1 exposes Eevee as ``BLENDER_EEVEE``; without libEGL (this container) Cycles CPU is used.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SKY = (0.35, 0.45, 0.6)  # stand-in for the daytime world sky


def _show_vertex_colors(bpy) -> None:
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes.get("Principled BSDF")
        if bsdf is None:
            continue
        attr = nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        # With data_type RGBA, name lookup resolves to the enabled A_Color/B_Color/Result_Color sockets (probed in 5.0.1).
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["A"].default_value = bsdf.inputs["Base Color"].default_value
        links.new(attr.outputs["Color"], mix.inputs["B"])
        links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])


def _look_at(obj, target) -> None:
    from mathutils import Vector
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _set_sky(bpy, scene) -> None:
    scene.world = scene.world or bpy.data.worlds.new("PreviewWorld")
    scene.world.color = SKY
    # Blender 5.0 worlds always carry a node tree; the Background node is what renders.
    tree = scene.world.node_tree
    bg = tree.nodes.get("Background") if tree else None
    if bg is not None:
        bg.inputs["Color"].default_value = (*SKY, 1.0)
        bg.inputs["Strength"].default_value = 1.0


def _pick_engine() -> str:
    """Eevee needs an EGL/GPU context; without libEGL Blender 5.0.1 aborts (SIGABRT) instead of
    raising, so a try/except fallback cannot work. Choose the engine before rendering."""
    import ctypes.util
    return "BLENDER_EEVEE" if ctypes.util.find_library("EGL") else "CYCLES"


def render(blend: Path, output: Path, camera: dict, size=(768, 432)) -> dict:
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    _show_vertex_colors(bpy)
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens_unit = "FOV"
    cam_data.angle = math.radians(camera.get("fov", 70))
    cam_data.clip_end = 1000.0
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    scene.collection.objects.link(cam)
    pos, tgt = camera["position"], camera["target"]          # Resonite XYZ
    cam.location = (pos[0], pos[2], pos[1])
    _look_at(cam, (tgt[0], tgt[2], tgt[1]))
    scene.camera = cam
    sun = bpy.data.objects.new("PreviewSun", bpy.data.lights.new("PreviewSun", "SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    scene.collection.objects.link(sun)
    _set_sky(bpy, scene)
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output.resolve())
    engine = _pick_engine()
    scene.render.engine = engine
    if engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = 24
    bpy.ops.render.render(write_still=True)
    return {"output": str(output), "engine": engine, "size": list(size)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--blend", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--camera", required=True, help='JSON {"position":[x,y,z],"target":[x,y,z],"fov":70}')
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    print("SLUM02_PREVIEW=" + json.dumps(render(a.blend, a.output, json.loads(a.camera))))


if __name__ == "__main__":
    main()
