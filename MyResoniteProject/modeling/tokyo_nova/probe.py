"""Create an editable, textured asymmetric 1 m Blender pipeline probe.

Run with ``resoloop blender run modeling/tokyo_nova/probe.py --arg=OUTPUT.blend --json``.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

IMAGE_SIZE = 64


def _pixels(kind: str) -> list[float]:
    values: list[float] = []
    for y in range(IMAGE_SIZE):
        for x in range(IMAGE_SIZE):
            u, v = x / (IMAGE_SIZE - 1), y / (IMAGE_SIZE - 1)
            if kind == "albedo":
                color = (0.07, 0.36, 0.42, 1.0) if (x // 8 + y // 8) % 2 else (0.72, 0.24, 0.085, 1.0)
                if x in (1, IMAGE_SIZE - 2) or y in (1, IMAGE_SIZE - 2):
                    color = (0.94, 0.74, 0.28, 1.0)
            elif kind == "roughness":
                rough = 0.18 if x < IMAGE_SIZE // 2 else 0.82
                if y % 8 < 2:
                    rough = min(1.0, rough + 0.12)
                color = (rough, rough, rough, 1.0)
            elif kind == "emission":
                lit = (8 <= x <= 56 and y in (9, 10, 11, 52, 53, 54)) or (10 <= y <= 53 and x in (8, 9, 54, 55))
                color = (0.9, 0.24, 0.025, 1.0) if lit else (0.015, 0.0, 0.0, 1.0)
                if 27 <= x <= 36 and 27 <= y <= 36:
                    color = (0.025, 0.24, 0.85, 1.0)
            else:
                nx = 0.5 + 0.025 * math.sin(u * math.tau * 4)
                ny = 0.5 + 0.02 * math.cos(v * math.tau * 3)
                nz = math.sqrt(max(0.0, 1.0 - (nx - 0.5) ** 2 - (ny - 0.5) ** 2))
                color = (nx, ny, nz, 1.0)
            values.extend(color)
    return values


def _image(directory: Path, name: str, kind: str, non_color: bool) -> bpy.types.Image:
    image = bpy.data.images.new(name=name, width=IMAGE_SIZE, height=IMAGE_SIZE, alpha=True)
    image.filepath_raw = str(directory / f"{name}.png")
    image.file_format = "PNG"
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    image.pixels = _pixels(kind)
    image.save()
    image.pack()
    image.use_fake_user = True
    return image


def _make_mesh(collection: bpy.types.Collection) -> bpy.types.Object:
    outline = [(-0.5, -0.4), (0.5, -0.4), (0.5, -0.08), (-0.14, -0.08), (-0.14, 0.4), (-0.5, 0.4)]
    vertices = [(x, y, z) for y in (-0.3, 0.3) for x, z in outline]
    low, high = list(range(6)), list(range(6, 12))
    faces = [tuple(reversed(low)), tuple(high)]
    faces.extend((low[i], low[(i + 1) % 6], high[(i + 1) % 6], high[i]) for i in range(6))
    mesh = bpy.data.meshes.new("TokyoNova_Asymmetric_1m_Mesh")
    mesh.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="AsymmetricProbeUV")
    for polygon in mesh.polygons:
        normal = polygon.normal
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            if abs(normal.y) >= max(abs(normal.x), abs(normal.z)):
                uv = (vertex.x + 0.5, vertex.z + 0.4)
            elif abs(normal.z) >= abs(normal.x):
                uv = (vertex.x + 0.5, vertex.y + 0.3)
            else:
                uv = (vertex.z + 0.4, vertex.y + 0.3)
            uv_layer.data[loop_index].uv = uv
    obj = bpy.data.objects.new("TokyoNova_Asymmetric_1m", mesh)
    collection.objects.link(obj)
    obj["purpose"] = "Asymmetric axis, UV, normals, PBR and unit transfer probe"
    return obj


def _make_materials(directory: Path, obj: bpy.types.Object) -> list[str]:
    albedo = _image(directory, "probe-albedo", "albedo", False)
    roughness = _image(directory, "probe-roughness", "roughness", True)
    emission = _image(directory, "probe-emission", "emission", False)
    normal = _image(directory, "probe-normal", "normal", True)
    material = bpy.data.materials.new("TokyoNova_Probe_PBR_Texture_Test")
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Metallic"].default_value = 0.32
    shader.inputs["Roughness"].default_value = 0.45
    shader.inputs["Emission Strength"].default_value = 0.7
    for node_name, image, socket in (
        ("Probe Albedo Image", albedo, "Base Color"),
        ("Probe NonColor Roughness Image", roughness, "Roughness"),
        ("Probe Emissive Image", emission, "Emission Color"),
    ):
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.name, node.image = node_name, image
        material.node_tree.links.new(node.outputs["Color"], shader.inputs[socket])
    normal_node = material.node_tree.nodes.new("ShaderNodeTexImage")
    normal_node.name, normal_node.image = "Probe NonColor Normal Image", normal
    normal_map = material.node_tree.nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = 0.35
    material.node_tree.links.new(normal_node.outputs["Color"], normal_map.inputs["Color"])
    material.node_tree.links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    material.use_fake_user = True

    guide = bpy.data.materials.new("TokyoNova_Probe_Facing_Marker")
    guide_shader = guide.node_tree.nodes.get("Principled BSDF")
    guide_shader.inputs["Base Color"].default_value = (0.05, 0.75, 0.95, 1.0)
    guide_shader.inputs["Metallic"].default_value = 0.1
    guide_shader.inputs["Roughness"].default_value = 0.28
    guide.use_fake_user = True
    obj.data.materials.append(material)
    obj.data.materials.append(guide)
    for polygon in obj.data.polygons:
        polygon.material_index = 1 if polygon.normal.z > 0.9 else 0
    for image in (albedo, roughness, emission, normal):
        if image.packed_file is None:
            raise RuntimeError(f"probe image {image.name} was not packed")
    return [albedo.name, roughness.name, emission.name, normal.name]


def build_probe(output_path: Path) -> dict[str, object]:
    """Build and reopen the probe scene, checking its measured source data."""
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    collection = bpy.data.collections.new("TokyoNova_IntegrationProbe")
    scene.collection.children.link(collection)
    obj = _make_mesh(collection)
    image_names = _make_materials(output_path.parent, obj)
    bpy.context.view_layer.update()
    blender_dimensions = [round(float(value), 5) for value in obj.dimensions]
    if blender_dimensions != [1.0, 0.6, 0.8]:
        raise RuntimeError(f"asymmetric probe dimensions changed: {blender_dimensions}")
    if len(obj.data.uv_layers) != 1 or len(obj.data.polygons) < 8:
        raise RuntimeError("probe is missing UVs or expected asymmetric faces")
    if any(polygon.normal.length < 0.99 for polygon in obj.data.polygons):
        raise RuntimeError("probe contains a degenerate face normal")

    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    bpy.ops.wm.open_mainfile(filepath=str(output_path))
    reopened = bpy.data.objects.get("TokyoNova_Asymmetric_1m")
    if reopened is None or not reopened.data.uv_layers:
        raise RuntimeError("saved probe did not reopen with its UV-bearing mesh")
    packed_images = []
    for image in bpy.data.images:
        if image.packed_file is None:
            continue
        image.reload()
        # Blender 5.0 lazily loads packed Image pixels after reload; read the buffer before testing has_data.
        sample = image.pixels[0]
        if not image.has_data or not image.size[0] or not image.size[1] or not math.isfinite(sample):
            raise RuntimeError(f"packed source image {image.name} could not be loaded after reopen")
        packed_images.append(image.name)
    if not set(image_names).issubset(packed_images):
        raise RuntimeError(f"saved probe lost packed source images: {image_names}, found {packed_images}")

    report = {
        "blend_path": str(output_path),
        "blender_version": bpy.app.version_string,
        "blender_dimensions_m": blender_dimensions,
        "resonite_dimensions_m": [blender_dimensions[0], blender_dimensions[2], blender_dimensions[1]],
        "uv_map": reopened.data.uv_layers.active.name,
        "polygon_count": len(reopened.data.polygons),
        "face_normals_valid": True,
        "materials": [material.name for material in reopened.data.materials],
        "packed_images": sorted(packed_images),
        "source_images": [str(output_path.parent / f"{name}.png") for name in image_names],
        "japanese_sign_strategy": "Resonite TextRenderer: 非対称・1m計測面",
        "roughness_map": "probe-roughness.png (Non-Color; values 0.18/0.82)",
        "emission_map": "probe-emission.png (sRGB; emissive pattern)",
        "normal_map": "probe-normal.png (Non-Color tangent-space input)",
        "base_color_map": "probe-albedo.png (sRGB UV checker)",
    }
    (output_path.parent / "probe-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"TOKYO_NOVA_PROBE_REPORT={output_path.parent / 'probe-report.json'}")
    return report


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not args:
        raise SystemExit("expected an output .blend path after --")
    build_probe(Path(args[0]))


if __name__ == "__main__":
    main()
