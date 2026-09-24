"""Deterministic Blender source builder and resource reporter for north frontage.

Run via ``resoloop blender run modeling/tokyo_nova/build.py --arg=--sector --arg=north\
 --arg=--output --arg=artifacts/tokyo-nova/north.blend --json``.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modeling.tokyo_nova import geometry
from modeling.tokyo_nova.layout import build_layout, validate_layout
from modeling.tokyo_nova.materials import make_blender_materials
from modeling.tokyo_nova.north import build_north_sector
from modeling.tokyo_nova.props import Assembly


def _triangle_count(part: geometry.MeshData) -> int:
    return sum(len(face) - 2 for face in part.faces)


def resource_report(assemblies: Iterable[Assembly], layout: dict[str, Any] | None = None) -> dict[str, Any]:
    """Summarize actual polygon resources by logical assembly and shared material."""
    assembled = list(assemblies)
    layout = layout or build_layout()
    reports = []
    material_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"vertices": 0, "triangles": 0, "parts": 0})
    for assembly in assembled:
        vertex_count = sum(len(part.vertices) for part in assembly.parts)
        triangles = sum(_triangle_count(part) for part in assembly.parts)
        materials = sorted({part.material for part in assembly.parts})
        for part in assembly.parts:
            material_totals[part.material]["vertices"] += len(part.vertices)
            material_totals[part.material]["triangles"] += _triangle_count(part)
            material_totals[part.material]["parts"] += 1
        bounds = assembly.bounds
        reports.append({
            "kind": assembly.kind,
            "name": assembly.name,
            "parts": len(assembly.parts),
            "vertices": vertex_count,
            "triangles": triangles,
            "materials": materials,
            "bounds_min": [round(value, 6) for value in bounds[0]],
            "bounds_max": [round(value, 6) for value in bounds[1]],
            "mesh_batches": len(materials),
        })
    return {
        "schema_version": 1,
        "seed": layout["seed"],
        "coordinate_system": "Resonite XYZ (Y up); Blender conversion is a single XZY coordinate swap",
        "source_strategy": "editable named part meshes merged into per-assembly/material static mesh batches",
        "assembly_count": len(reports),
        "assemblies": reports,
        "material_batches": dict(sorted(material_totals.items())),
        "total_parts": sum(entry["parts"] for entry in reports),
        "total_vertices": sum(entry["vertices"] for entry in reports),
        "total_triangles": sum(entry["triangles"] for entry in reports),
        "blender_object_count": sum(entry["mesh_batches"] for entry in reports),
        "material_count": len({material for entry in reports for material in entry["materials"]}),
        "texture_transfer_adaptation": (
            "No image textures in live export; shared Principled color/metallic/roughness plus authored edge wear, "
            "cracks, repair patches, rust streak geometry and wet/dry surface materials."
        ),
    }


def _resonite_to_blender(point: tuple[float, float, float]) -> tuple[float, float, float]:
    return (point[0], point[2], point[1])


def _mesh_batches(assemblies: Iterable[Assembly]) -> dict[tuple[str, str], list[geometry.MeshData]]:
    batches: dict[tuple[str, str], list[geometry.MeshData]] = defaultdict(list)
    for assembly in assemblies:
        for part in assembly.transformed_parts():
            batches[(assembly.kind, part.material)].append(part)
    return batches


def _join_part_data(parts: list[geometry.MeshData]) -> tuple[list[tuple[float, float, float]], list[tuple[int, ...]], list[str]]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    names: list[str] = []
    for part in parts:
        offset = len(vertices)
        vertices.extend(_resonite_to_blender(vertex) for vertex in part.vertices)
        faces.extend(tuple(offset + index for index in face) for face in part.faces)
        names.append(part.name)
    return vertices, faces, names


def _create_batch_object(bpy: Any, bmesh: Any, collection: Any, material_lookup: dict[str, Any], kind: str, material_name: str, parts: list[geometry.MeshData]) -> Any:
    vertices, faces, names = _join_part_data(parts)
    mesh_data = bpy.data.meshes.new(f"North_{kind}_{material_name}_Mesh")
    mesh_data.from_pydata(vertices, [], faces)
    mesh_data.update()
    bm = bmesh.new()
    bm.from_mesh(mesh_data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh_data)
    bm.free()
    uv_layer = mesh_data.uv_layers.new(name="NorthPlanarMeters")
    for polygon in mesh_data.polygons:
        normal = polygon.normal
        dominant = max(range(3), key=lambda axis: abs(normal[axis]))
        for loop_index in polygon.loop_indices:
            co = mesh_data.vertices[mesh_data.loops[loop_index].vertex_index].co
            if dominant == 2:
                uv = (co.x, co.y)
            elif dominant == 1:
                uv = (co.x, co.z)
            else:
                uv = (co.y, co.z)
            uv_layer.data[loop_index].uv = uv
    obj = bpy.data.objects.new(f"North_{kind}_{material_name}", mesh_data)
    collection.objects.link(obj)
    obj.data.materials.append(material_lookup[material_name])
    obj["asset_kind"] = kind
    obj["material_batch"] = material_name
    obj["editable_source_parts"] = json.dumps(names, ensure_ascii=False)
    if not obj.data.uv_layers or not all(polygon.normal.length > 0.99 for polygon in obj.data.polygons):
        raise RuntimeError(f"mesh batch {obj.name} is missing UVs or valid normals")
    return obj


def _look_at(camera: Any, target: tuple[float, float, float]) -> None:
    from mathutils import Vector  # type: ignore[import-not-found]

    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _setup_preview(bpy: Any, scene: Any, preview_collection: Any, output_path: Path) -> list[str]:
    """Create offline-only stage, lights and eye-level/phone cameras for source review."""
    created = []
    ground_mesh = bpy.data.meshes.new("NorthPreviewGroundMesh")
    ground_mesh.from_pydata([(-50, -5, -0.04), (5, -5, -0.04), (5, 55, -0.04), (-50, 55, -0.04)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("PREVIEW_ONLY_Ground_not_exported", ground_mesh)
    preview_collection.objects.link(ground)
    ground_material = bpy.data.materials.new("PREVIEW_ONLY_DarkDryStage")
    ground_material.diffuse_color = (0.035, 0.045, 0.052, 1)
    ground.data.materials.append(ground_material)
    created.append(ground.name)

    def area_light(name: str, res_point: tuple[float, float, float], energy: float, color: tuple[float, float, float], size: float) -> None:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.color, data.shape, data.size = energy, color, "DISK", size
        obj = bpy.data.objects.new(name, data)
        obj.location = _resonite_to_blender(res_point)
        _look_at(obj, _resonite_to_blender((-25, 2.6, 14)))
        preview_collection.objects.link(obj)
        created.append(name)

    area_light("PREVIEW_ONLY_WarmShopKey", (-34, 7.5, 7), 950, (1.0, 0.63, 0.36), 7.0)
    area_light("PREVIEW_ONLY_CoolFill", (-14, 7.0, 18), 1200, (0.42, 0.62, 0.80), 10.0)
    area_light("PREVIEW_ONLY_FrontSoftbox", (-27, 11, 4), 1500, (0.76, 0.82, 0.86), 12.0)

    camera_data = bpy.data.cameras.new("PREVIEW_ONLY_NorthEyeLevelCamera")
    camera = bpy.data.objects.new("PREVIEW_ONLY_NorthEyeLevelCamera", camera_data)
    camera.location = _resonite_to_blender((-25, 2.1, 3.5))
    camera_data.lens = 28
    _look_at(camera, _resonite_to_blender((-25, 3.2, 15)))
    preview_collection.objects.link(camera)
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1280, 720, 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.035, 0.05)
    scene.view_settings.view_transform = "AgX"
    # A second frame verifies the calibrated phone face, side keys and camera cluster at close range.
    phone_data = bpy.data.cameras.new("PREVIEW_ONLY_PhoneCloseCamera")
    phone_camera = bpy.data.objects.new("PREVIEW_ONLY_PhoneCloseCamera", phone_data)
    phone_camera.location = _resonite_to_blender((-26.15, 1.35, 15.35))
    _look_at(phone_camera, _resonite_to_blender((-26.04, 1.025, 16.70)))
    phone_data.lens = 58
    preview_collection.objects.link(phone_camera)
    previous_camera = scene.camera
    scene.camera = phone_camera
    scene.camera = previous_camera
    return created


def build_blend(layout_path: Path, output_path: Path) -> dict[str, Any]:
    """Build and reopen an editable Blender file plus structural and resource reports."""
    import bmesh  # type: ignore[import-not-found]
    import bpy  # type: ignore[import-not-found]

    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    errors = validate_layout(layout)
    if errors:
        raise ValueError("layout validation failed: " + "; ".join(errors))
    assemblies = build_north_sector(layout)
    report = resource_report(assemblies, layout)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    source_collection = bpy.data.collections.get("Collection") or bpy.data.collections.new("Collection")
    source_collection.name = "TokyoNovaNorth"
    if source_collection.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(source_collection)
    material_lookup = make_blender_materials()
    for (kind, material_name), parts in sorted(_mesh_batches(assemblies).items()):
        _create_batch_object(bpy, bmesh, source_collection, material_lookup, kind, material_name, parts)
    preview_collection = bpy.data.collections.new("TokyoNovaNorthPreviewOnly")
    bpy.context.scene.collection.children.link(preview_collection)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.image_settings.color_mode = "RGBA"
    preview_outputs = _setup_preview(bpy, scene, preview_collection, output_path)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(output_path.resolve()))
    source = bpy.data.collections.get("TokyoNovaNorth")
    if source is None:
        raise RuntimeError("editable north source collection disappeared after reopening")
    objects = [obj for obj in source.objects if obj.type == "MESH"]
    if len(objects) != report["blender_object_count"]:
        raise RuntimeError(f"expected {report['blender_object_count']} material batches, reopened {len(objects)}")
    if any(not obj.data.polygons or not obj.data.uv_layers for obj in objects):
        raise RuntimeError("reopened north model contains an empty mesh or missing UVs")
    report.update({
        "blend_path": str(output_path.resolve()),
        "blender_version": bpy.app.version_string,
        "reopened_mesh_objects": len(objects),
        "reopened_uv_meshes": sum(bool(obj.data.uv_layers) for obj in objects),
        "reopened_valid_normal_polygons": sum(sum(poly.normal.length > 0.99 for poly in obj.data.polygons) for obj in objects),
        "preview_scene_objects": preview_outputs,
        "offline_render_status": "not rendered: Blender process lacks libEGL.so.1; install prohibited",
        "export_collection": "TokyoNovaNorth",
        "preview_collection_excluded_from_export": "TokyoNovaNorthPreviewOnly",
    })
    report_path = output_path.parent / "north-resource-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector", choices=("north",), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layout", type=Path, default=Path("content/tokyo-nova/layout.json"))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.output.suffix.lower() != ".blend":
        raise SystemExit("--output must be an editable .blend file path")
    report = build_blend(args.layout, args.output)
    print("TOKYO_NOVA_NORTH_REPORT=" + json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
