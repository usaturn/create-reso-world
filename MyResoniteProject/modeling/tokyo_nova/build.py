"""Deterministic Blender source builder and resource reporter for north frontage.

Run via ``resoloop blender run modeling/tokyo_nova/build.py --arg=--sector --arg=north\
 --arg=--output --arg=artifacts/tokyo-nova/north.blend --json``.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modeling.tokyo_nova import districts, geometry, interiors, skyline
from modeling.tokyo_nova.layout import build_layout, validate_layout
from modeling.tokyo_nova.materials import make_blender_materials
from modeling.tokyo_nova.north import build_north_sector
from modeling.tokyo_nova.props import Assembly
from modeling.tokyo_nova.uv import metric_face_uvs, uv_triangle_issues


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
        "source_strategy": "editable named part meshes merged into deterministic sector/category/material static mesh batches",
        "assembly_count": len(reports),
        "assemblies": reports,
        "material_batches": dict(sorted(material_totals.items())),
        "total_parts": sum(entry["parts"] for entry in reports),
        "total_vertices": sum(entry["vertices"] for entry in reports),
        "total_triangles": sum(entry["triangles"] for entry in reports),
        "blender_object_count": len(_mesh_batches(assembled)),
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


def _create_batch_object(bpy: Any, bmesh: Any, collection: Any, material_lookup: dict[str, Any], kind: str, material_name: str, parts: list[geometry.MeshData], prefix: str = "North") -> Any:
    vertices, faces, names = _join_part_data(parts)
    if kind == "night_sky_dome":
        # The XZY handedness change reverses faces. Undo it explicitly; recalculating
        # these normals would incorrectly turn an interior sky shell back outward.
        faces = [tuple(reversed(face)) for face in faces]
    mesh_data = bpy.data.meshes.new(f"{prefix}_{kind}_{material_name}_Mesh")
    mesh_data.from_pydata(vertices, [], faces)
    mesh_data.update()
    if kind != "night_sky_dome":
        bm = bmesh.new()
        bm.from_mesh(mesh_data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh_data)
        bm.free()
    uv_layer = mesh_data.uv_layers.new(name="UV0")
    for polygon in mesh_data.polygons:
        if kind == "night_sky_dome":
            loop_ids = list(polygon.loop_indices)
            projected = []
            for loop_index in loop_ids:
                co = mesh_data.vertices[mesh_data.loops[loop_index].vertex_index].co
                radial_z = max(-1.0, min(1.0, (co.z + 18.0) / 78.0))
                projected.append([math.atan2(co.y, co.x) / (2 * math.pi) + 0.5, math.acos(radial_z) / math.pi])
            if max(point[0] for point in projected) - min(point[0] for point in projected) > 0.5:
                for point in projected:
                    if point[0] < 0.5:
                        point[0] += 1.0
            for loop_index, uv in zip(loop_ids, projected):
                uv_layer.data[loop_index].uv = uv
        else:
            loop_ids = list(polygon.loop_indices)
            points = [mesh_data.vertices[mesh_data.loops[index].vertex_index].co for index in loop_ids]
            uv_values = metric_face_uvs(points, polygon.normal, uv_per_meter=0.5)
            for loop_index, uv in zip(loop_ids, uv_values):
                uv_layer.data[loop_index].uv = uv
    obj = bpy.data.objects.new(f"{prefix}_{kind}_{material_name}", mesh_data)
    collection.objects.link(obj)
    obj.data.materials.append(material_lookup[material_name])
    obj["asset_kind"] = kind
    obj["material_batch"] = material_name
    obj["editable_source_parts"] = json.dumps(names, ensure_ascii=False)
    obj["uv_policy"] = "spherical hemisphere UV0" if kind == "night_sky_dome" else "0.5 UV/m face-local metric tiling; island overlap intentional for shared tileable materials"
    if not obj.data.uv_layers or not all(polygon.normal.length > 0.99 for polygon in obj.data.polygons):
        raise RuntimeError(f"mesh batch {obj.name} is missing UVs or valid normals")
    return obj


def _uv_quality_report(mesh: Any, *, metric: bool = False) -> dict[str, Any]:
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        return {"faces": 0, "degenerate_faces": 0, "channels": []}
    density, aspect_scales = [], []
    degenerate = 0
    face_count = 0
    metric_issues: dict[str, int] = defaultdict(int)
    for polygon in mesh.polygons:
        if polygon.area <= 1e-12:
            continue
        indices = list(polygon.loop_indices)
        uv = [uv_layer.data[index].uv for index in indices]
        area_uv = abs(sum(uv[index].x * uv[(index + 1) % len(uv)].y - uv[(index + 1) % len(uv)].x * uv[index].y for index in range(len(uv)))) / 2
        face_count += 1
        if metric:
            points = [mesh.vertices[mesh.loops[index].vertex_index].co for index in indices]
            for corner in range(1, len(indices) - 1):
                for issue in uv_triangle_issues(
                    (points[0], points[corner], points[corner + 1]),
                    (uv[0], uv[corner], uv[corner + 1]), polygon.normal,
                ):
                    metric_issues[issue] += 1
        if area_uv <= 1e-10:
            degenerate += 1
            continue
        density.append(math.sqrt(area_uv / polygon.area))
        for offset, loop_index in enumerate(indices):
            next_index = indices[(offset + 1) % len(indices)]
            va = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            vb = mesh.vertices[mesh.loops[next_index].vertex_index].co
            edge_length = (vb - va).length
            uv_edge = (uv[(offset + 1) % len(uv)] - uv[offset]).length
            if edge_length > 1e-9:
                aspect_scales.append(uv_edge / edge_length)
    ordered = sorted(density)
    return {
        "faces": face_count,
        "degenerate_faces": degenerate,
        "degenerate_fraction": degenerate / max(1, face_count),
        "metric_issues": dict(metric_issues),
        "channels": [layer.name for layer in mesh.uv_layers],
        "metric_uv_density_range_uv_per_m": [round(ordered[0], 5), round(ordered[-1], 5)] if ordered else [],
        "metric_edge_scale_range_uv_per_m": [round(min(aspect_scales), 5), round(max(aspect_scales), 5)] if aspect_scales else [],
        "overlap_policy": "intentional face-local overlap for seamless shared-material tiling; no unique texture atlases are authored",
    }



def geometry_nodes_authoring_spec() -> dict[str, Any]:
    """Describe bounded, seeded cast-tie controls and the editable-to-static workflow."""
    return {
        "editable_source": True,
        "evaluated_static_export": True,
        "static_export_material_policy": "single nonempty material slot; all face indices normalize to zero",
        "static_export_geometry_policy": "rebuild applied node output from explicit vertices and polygon indices",
        "controls": {
            "Facade Module Width": {"socket_type": "NodeSocketFloat", "default": 1.6, "minimum": 0.8, "maximum": 2.4},
            "Storey Height": {"socket_type": "NodeSocketFloat", "default": 2.8, "minimum": 2.4, "maximum": 3.4},
            "Tie Density": {"socket_type": "NodeSocketFloat", "default": 0.72, "minimum": 0.25, "maximum": 1.0},
            "Pattern Seed": {"socket_type": "NodeSocketInt", "default": 2026, "minimum": 0, "maximum": 2147483647},
        },
        "nodes": (
            "GeometryNodeMeshGrid", "GeometryNodeInputIndex", "FunctionNodeRandomValue",
            "FunctionNodeCompare", "GeometryNodeDeleteGeometry", "GeometryNodeMeshIcoSphere",
            "GeometryNodeInstanceOnPoints", "GeometryNodeSetMaterial",
        ),
        "feature": "seeded cast-in-place facade tie pattern",
    }


def _create_procedural_facade_authoring(bpy: Any, author_collection: Any, export_collection: Any, material: Any, roof_record: dict[str, Any], building: dict[str, Any]) -> dict[str, Any]:
    """Retain the live Geometry Nodes graph and export its evaluated static result."""
    spec = geometry_nodes_authoring_spec()
    if not spec["editable_source"] or not spec["evaluated_static_export"]:
        raise RuntimeError("the procedural city authoring workflow must retain and bake its source graph")
    tree = bpy.data.node_groups.new("GN_TokyoNovaCastTieModule_Authoring", "GeometryNodeTree")
    tree.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    control_sockets = {}
    for name, control in spec["controls"].items():
        socket = tree.interface.new_socket(name=name, in_out="INPUT", socket_type=control["socket_type"])
        socket.default_value = control["default"]
        socket.min_value = control["minimum"]
        socket.max_value = control["maximum"]
        control_sockets[name] = socket
    nodes, links = tree.nodes, tree.links
    input_node, output_node = nodes.new("NodeGroupInput"), nodes.new("NodeGroupOutput")
    grid = nodes.new("GeometryNodeMeshGrid")
    grid.inputs["Vertices X"].default_value = 4
    grid.inputs["Vertices Y"].default_value = 5
    row_extent, col_extent = nodes.new("ShaderNodeMath"), nodes.new("ShaderNodeMath")
    row_extent.operation = col_extent.operation = "MULTIPLY"
    row_extent.inputs[1].default_value, col_extent.inputs[1].default_value = 3.0, 4.0
    links.new(input_node.outputs["Storey Height"], row_extent.inputs[0])
    links.new(input_node.outputs["Facade Module Width"], col_extent.inputs[0])
    links.new(row_extent.outputs[0], grid.inputs["Size X"])
    links.new(col_extent.outputs[0], grid.inputs["Size Y"])
    index, random = nodes.new("GeometryNodeInputIndex"), nodes.new("FunctionNodeRandomValue")
    random.data_type = "FLOAT"
    links.new(index.outputs["Index"], random.inputs["ID"])
    links.new(input_node.outputs["Pattern Seed"], random.inputs["Seed"])
    compare = nodes.new("FunctionNodeCompare")
    compare.data_type, compare.operation = "FLOAT", "GREATER_THAN"
    links.new(random.outputs["Value"], compare.inputs["A"])
    links.new(input_node.outputs["Tie Density"], compare.inputs["B"])
    delete = nodes.new("GeometryNodeDeleteGeometry")
    delete.domain = "POINT"
    links.new(grid.outputs["Mesh"], delete.inputs["Geometry"])
    links.new(compare.outputs["Result"], delete.inputs["Selection"])
    sphere = nodes.new("GeometryNodeMeshIcoSphere")
    sphere.inputs["Radius"].default_value = 0.055
    sphere.inputs["Subdivisions"].default_value = 2
    points = nodes.new("GeometryNodeInstanceOnPoints")
    links.new(delete.outputs["Geometry"], points.inputs["Points"])
    links.new(sphere.outputs["Mesh"], points.inputs["Instance"])
    set_material = nodes.new("GeometryNodeSetMaterial")
    set_material.inputs["Material"].default_value = material
    links.new(points.outputs["Instances"], set_material.inputs["Geometry"])
    links.new(set_material.outputs["Geometry"], output_node.inputs["Geometry"])
    actual_nodes = {node.bl_idname for node in nodes}
    if not set(spec["nodes"]).issubset(actual_nodes):
        raise RuntimeError("the authored Geometry Nodes graph is missing a required facade-forming node")
    for node, location in ((input_node, (-900, 100)), (grid, (-420, 180)), (row_extent, (-650, 360)), (col_extent, (-650, 100)), (index, (-650, -220)), (random, (-420, -260)), (compare, (-180, -180)), (delete, (40, 160)), (sphere, (40, -80)), (points, (260, 160)), (set_material, (660, 160)), (output_node, (850, 160))):
        node.location = location
    source_mesh = bpy.data.meshes.new("GN_CastTie_Authoring_EmptySource")
    source = bpy.data.objects.new("GN_CastTie_Authoring_Source", source_mesh)
    author_collection.objects.link(source)
    source.hide_render = True
    try:
        position = (
            float(building["center"][0]) - (float(building["size"][0]) + 0.18) / 2 - 0.012,
            float(roof_record["roof_walk_y"]) / 2,
            float(building["center"][2]),
        )
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError("the procedural facade needs a valid roof grade and building center/size") from exc
    source.location = _resonite_to_blender(position)
    source.rotation_euler[1] = -math.pi / 2
    modifier = source.modifiers.new("Procedural structural cast-tie layout", "NODES")
    modifier.node_group = tree
    values = {"Facade Module Width": 1.6, "Storey Height": 2.8, "Tie Density": 0.72, "Pattern Seed": 2026}
    for name, socket in control_sockets.items():
        modifier[socket.identifier] = values[name]
    evaluated = source.copy()
    evaluated.data = source.data.copy()
    evaluated.name = "City_GeometryNodesEvaluated_CastTiePattern"
    export_collection.objects.link(evaluated)
    evaluated.hide_render = False
    # Keep the authoring group instanced. Only the export copy needs an explicit
    # Realize Instances node so modifier_apply produces an ordinary static mesh.
    export_tree = tree.copy()
    export_tree.name = "GN_TokyoNovaCastTieModule_StaticExport"
    export_nodes, export_links = export_tree.nodes, export_tree.links
    export_points = next(node for node in export_nodes if node.bl_idname == "GeometryNodeInstanceOnPoints")
    export_material = next(node for node in export_nodes if node.bl_idname == "GeometryNodeSetMaterial")
    export_realize = export_nodes.new("GeometryNodeRealizeInstances")
    export_realize.location = (470, 160)
    export_links.new(export_points.outputs["Instances"], export_realize.inputs["Geometry"])
    export_links.new(export_realize.outputs["Geometry"], export_material.inputs["Geometry"])
    evaluated.modifiers[modifier.name].node_group = export_tree
    bpy.ops.object.select_all(action="DESELECT")
    evaluated.select_set(True)
    bpy.context.view_layer.objects.active = evaluated
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    if evaluated.modifiers or len(evaluated.data.vertices) < 4 or not evaluated.data.polygons:
        raise RuntimeError("the evaluated cast-tie graph did not produce a static export mesh")
    # Rebuild node-generated geometry with ordinary mesh data before handing it to
    # ResoLoop's serializer; Blender's applied node attributes trigger its mesh reader.
    generated_mesh = evaluated.data
    vertices = [tuple(vertex.co) for vertex in generated_mesh.vertices]
    faces = [tuple(polygon.vertices) for polygon in generated_mesh.polygons]
    clean_mesh = bpy.data.meshes.new("GN_CastTie_StaticExport_Mesh")
    clean_mesh.from_pydata(vertices, [], faces)
    clean_mesh.update()
    evaluated.data = clean_mesh
    if generated_mesh.users == 0:
        bpy.data.meshes.remove(generated_mesh)
    for slot_index in reversed(range(len(evaluated.data.materials))):
        evaluated.data.materials.pop(index=slot_index)
    evaluated.data.materials.append(material)
    for polygon in evaluated.data.polygons:
        polygon.material_index = 0
    if not evaluated.data.uv_layers:
        uv_layer = evaluated.data.uv_layers.new(name="UV0")
        for polygon in evaluated.data.polygons:
            loop_ids = list(polygon.loop_indices)
            points = [evaluated.data.vertices[evaluated.data.loops[index].vertex_index].co for index in loop_ids]
            for loop_index, uv in zip(loop_ids, metric_face_uvs(points, polygon.normal, uv_per_meter=0.5)):
                uv_layer.data[loop_index].uv = uv
    evaluated["asset_kind"] = "geometry_nodes_facade_ties"
    evaluated["material_batch"] = "exposed_metal"
    evaluated["evaluated_from_geometry_nodes"] = tree.name
    return {
        "node_group": tree.name, "source_object": source.name, "evaluated_export_object": evaluated.name,
        "controls": {name: {"identifier": socket.identifier, **spec["controls"][name]} for name, socket in control_sockets.items()},
        "nodes": sorted(actual_nodes), "static_export_node_group": export_tree.name,
        "authoring_collection": author_collection.name,
        "evaluated_export_vertex_count": len(evaluated.data.vertices),
        "evaluation": "the saved node group remains editable; only its evaluated duplicate is baked for the static Resonite export",
    }


def _look_at(camera: Any, target: tuple[float, float, float]) -> None:
    from mathutils import Vector  # type: ignore[import-not-found]

    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _setup_preview(bpy: Any, scene: Any, preview_collection: Any, output_path: Path) -> list[str]:
    """Create offline-only stage, lights and eye-level/phone cameras for source review."""
    created = []
    ground_mesh = bpy.data.meshes.new("NorthPreviewGroundMesh")
    ground_mesh.from_pydata([(-55, -55, -0.04), (55, -55, -0.04), (55, 55, -0.04), (-55, 55, -0.04)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("PREVIEW_ONLY_Ground_not_exported", ground_mesh)
    preview_collection.objects.link(ground)
    ground_material = bpy.data.materials.new("PREVIEW_ONLY_DarkDryStage")
    ground_material.diffuse_color = (0.025, 0.035, 0.041, 1)
    ground_shader = ground_material.node_tree.nodes.get("Principled BSDF") if ground_material.node_tree else None
    if ground_shader is not None:
        ground_shader.inputs["Base Color"].default_value = (0.025, 0.035, 0.041, 1)
        ground_shader.inputs["Roughness"].default_value = 0.82
    ground.data.materials.append(ground_material)
    created.append(ground.name)

    def area_light(name: str, res_point: tuple[float, float, float], energy: float, color: tuple[float, float, float], size: float, target: tuple[float, float, float] = (-25, 2.6, 14)) -> None:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.color, data.shape, data.size = energy, color, "DISK", size
        obj = bpy.data.objects.new(name, data)
        obj.location = _resonite_to_blender(res_point)
        _look_at(obj, _resonite_to_blender(target))
        preview_collection.objects.link(obj)
        created.append(name)

    area_light("PREVIEW_ONLY_WarmShopKey", (-34, 7.5, 7), 460, (1.0, 0.63, 0.36), 7.0)
    area_light("PREVIEW_ONLY_CoolFill", (-14, 7.0, 18), 620, (0.42, 0.62, 0.80), 10.0)
    area_light("PREVIEW_ONLY_FrontSoftbox", (-27, 11, 4), 700, (0.76, 0.82, 0.86), 12.0)
    area_light("PREVIEW_ONLY_ClinicRoomKey", (15.0, 2.7, -35.0), 700, (1.0, 0.78, 0.57), 3.5, (15.0, 0.7, -35.0))
    area_light("PREVIEW_ONLY_TheatreRoomKey", (-15.0, 0.25, -15.0), 520, (0.55, 0.68, 0.82), 4.0, (-15.0, -0.8, -17.5))
    area_light("PREVIEW_ONLY_RoofKey", (-15.0, 19.0, 35.0), 800, (0.54, 0.67, 0.82), 10.0, (0.0, 4.0, 0.0))

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
    scene.world.color = (0.055, 0.07, 0.085)
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

    def preview_camera(name: str, position: tuple[float, float, float], target: tuple[float, float, float], lens: float) -> None:
        data = bpy.data.cameras.new(f"PREVIEW_ONLY_{name}")
        camera_obj = bpy.data.objects.new(f"PREVIEW_ONLY_{name}", data)
        camera_obj.location = _resonite_to_blender(position)
        data.lens = lens
        _look_at(camera_obj, _resonite_to_blender(target))
        preview_collection.objects.link(camera_obj)
        created.append(camera_obj.name)

    preview_camera("PlazaEyeLevel", (0.0, 1.65, 7.8), (-16.0, 3.1, 15.0), 26)
    preview_camera("CityOverhead", (0.0, 50.0, 0.0), (0.0, 0.0, 0.0), 35)
    overhead = preview_collection.objects["PREVIEW_ONLY_CityOverhead"]
    overhead.data.type = "ORTHO"
    overhead.data.ortho_scale = 178
    preview_camera("ClinicInterior", (13.4, 1.55, -36.4), (16.4, 0.95, -35.3), 26)
    preview_camera("TheatreInterior", (-15.0, -0.45, -10.1), (-15.0, -0.85, -17.0), 30)
    preview_camera("RoofOverlook", (-15.0, 10.8, 35.0), (0.0, 3.0, 0.0), 38)
    return created


def build_city(layout: dict[str, Any]) -> dict[str, Any]:
    """Emit full city source meshes and metrics derived from real assemblies."""
    from modeling.tokyo_nova.layout import validate_layout

    errors = validate_layout(layout)
    if errors:
        raise ValueError("layout validation failed: " + "; ".join(errors))
    north_assemblies = build_north_sector(layout)
    district_assemblies, building_geometry = districts.build_districts(layout)
    interior_assemblies, facility_geometry, interior_records = interiors.build_interiors(layout)
    skyline_assemblies = skyline.build_skyline(layout)
    assemblies = [*north_assemblies, *district_assemblies, *interior_assemblies, *skyline_assemblies]

    north_building_kind = {
        "north_yatai": "food_stall",
        "north_terminal_repair": "terminal_repair",
        "north_machiya": "patched_housing_facade",
    }
    for building in layout["buildings"]:
        key = building["key"]
        if key in building_geometry:
            continue
        asset = next(item for item in north_assemblies if item.kind == north_building_kind[key])
        bounds = asset.bounds
        building_geometry[key] = {
            "building_key": key,
            "floor_count": 2 if key == "north_machiya" else 1,
            "height": round(bounds[1][1] - bounds[0][1], 3),
            "door_width": 1.35,
            "door_height": 2.12,
            "route_connected": True,
            "silhouette": [round(bounds[1][axis] - bounds[0][axis], 3) for axis in range(3)],
            "part_count": len(asset.parts),
            "structural_part_names": tuple(part.name for part in asset.parts if any(word in part.name for word in ("wall", "floor", "door", "masonry"))),
        }
    if len(building_geometry) != 24:
        raise RuntimeError(f"full source geometry accounts for {len(building_geometry)} of 24 buildings")

    prop_geometry = interior_records["props"]
    if len(prop_geometry) < 60 or any(not value["parts"] or value["triangles"] < 1 for value in prop_geometry.values()):
        raise RuntimeError("function-specific emitted prop geometry did not meet the 60-kind floor")
    registered_facility_keys = {facility["key"] for facility in layout["facilities"]}
    facility_geometry = {key: value for key, value in facility_geometry.items() if key in registered_facility_keys}
    facility_geometry.update({
        "eatery": {"facility_key": "eatery", "building_key": "north_yatai", "emitted_geometry": True, "asset_part_count": sum(len(a.parts) for a in north_assemblies if a.kind == "food_stall")},
        "terminal_repair": {"facility_key": "terminal_repair", "building_key": "north_terminal_repair", "emitted_geometry": True, "asset_part_count": sum(len(a.parts) for a in north_assemblies if a.kind == "terminal_repair")},
    })
    accessible = interior_records["accessible"]
    # Room access declarations are computed from emitted room shell parts and facade door geometry.
    for record in accessible.values():
        source = building_geometry[record["building_key"]]
        record["route_connected"] = bool(source["route_connected"] and record["geometry_parts"] > 0)
    loop_count = sum(bool(route.get("loop")) for route in layout["routes"])
    roof_key = layout["roof_access"]["building_key"]
    roof_record = building_geometry[roof_key]
    roof_assembly = next(assembly for assembly in district_assemblies if assembly.name == roof_key)
    roof_connection = districts.roof_access_report(layout, roof_assembly, roof_record)
    roof_route_continuous = bool(roof_connection["continuous"])
    accessibility = {
        "route_keys": [route["key"] for route in layout["routes"]],
        "entrances": [route["key"] for route in layout["routes"] if route["kind"] == "entrance"],
        "loop_count": loop_count,
        "roof_route_continuous": roof_route_continuous,
        "roof_building_key": roof_key,
        "roof_geometry_height": roof_record["height"],
        "roof_connection": roof_connection,
        "open_doorways": {key: record["door_width"] for key, record in building_geometry.items()},
        "accessible_rooms": list(accessible),
        "room_count": len(accessible),
    }
    if len(facility_geometry) < 12 or len(accessible) < 6 or loop_count < 2 or not roof_route_continuous:
        raise RuntimeError("emitted city facility/interior/route coverage is incomplete")
    sectors = {
        "north": [assembly for assembly in north_assemblies],
        "districts": [assembly for assembly in district_assemblies],
        "interiors": [assembly for assembly in interior_assemblies],
        "skyline": [assembly for assembly in skyline_assemblies],
    }
    return {
        "assemblies": assemblies,
        "building_geometry": building_geometry,
        "facility_geometry": facility_geometry,
        "collision_geometry": districts.collision_parts([*district_assemblies, *interior_assemblies]),
        "accessible_interiors": accessible,
        "prop_geometry": prop_geometry,
        "accessibility": accessibility,
        "sky_geometry": skyline.sky_report(skyline_assemblies),
        "lighting": {"local_light_count": len(skyline.local_lights()), "lights": skyline.local_lights(), "global_world_components_modified": 0},
        "asset_catalog": interiors.asset_catalog(prop_geometry),
        "resource_counts_by_sector": {
            key: {
                "assembly_count": len(items),
                "parts": sum(len(assembly.parts) for assembly in items),
                "vertices": sum(len(part.vertices) for assembly in items for part in assembly.parts),
                "triangles": sum(_triangle_count(part) for assembly in items for part in assembly.parts),
                "material_batches": len(_mesh_batches(items)),
                "blender_objects": len(_mesh_batches(items)),
            }
            for key, items in sectors.items()
        },
    }


def build_blend(layout_path: Path, output_path: Path, sector: str = "north") -> dict[str, Any]:
    """Build and reopen an editable Blender file plus structural and resource reports."""
    import bmesh  # type: ignore[import-not-found]
    import bpy  # type: ignore[import-not-found]

    try:
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read city layout at {layout_path}") from exc
    errors = validate_layout(layout)
    if errors:
        raise ValueError("layout validation failed: " + "; ".join(errors))
    city = build_city(layout) if sector == "all" else None
    assemblies = city["assemblies"] if city is not None else build_north_sector(layout)
    report = resource_report(assemblies, layout)
    if city is not None:
        report["city"] = {key: value for key, value in city.items() if key != "assemblies"}
        report["resource_counts_by_sector"] = city["resource_counts_by_sector"]
        report["asset_kind_count"] = len(city["prop_geometry"])
        report["building_count"] = len(city["building_geometry"])
        report["facility_count"] = len(city["facility_geometry"])
        report["accessible_interior_count"] = len(city["accessible_interiors"])
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
    city_collection = None
    city_export_collection = None
    procedural_author_collection = None
    if city is not None:
        city_collection = bpy.data.collections.new("TokyoNovaCity")
        bpy.context.scene.collection.children.link(city_collection)
        city_export_collection = bpy.data.collections.new("TokyoNovaCityExport")
        bpy.context.scene.collection.children.link(city_export_collection)
        procedural_author_collection = bpy.data.collections.new("TokyoNovaProceduralAuthoring")
        bpy.context.scene.collection.children.link(procedural_author_collection)
    material_lookup = make_blender_materials()
    if city is None:
        for (kind, material_name), parts in sorted(_mesh_batches(assemblies).items()):
            _create_batch_object(bpy, bmesh, source_collection, material_lookup, kind, material_name, parts)
    else:
        if city_collection is None or city_export_collection is None or procedural_author_collection is None:
            raise RuntimeError("city source and export collections were not created")
        retained_north = {"food_stall", "terminal_repair", "patched_housing_facade", "pocket_phone", "north_frontage_pavement", "north_facility_connector"}
        north_assets = [assembly for assembly in assemblies if assembly.kind in retained_north]
        city_assets = [assembly for assembly in assemblies if assembly.kind not in retained_north]
        for (kind, material_name), parts in sorted(_mesh_batches(north_assets).items()):
            _create_batch_object(bpy, bmesh, source_collection, material_lookup, kind, material_name, parts, "North")
        for (kind, material_name), parts in sorted(_mesh_batches(city_assets).items()):
            obj = _create_batch_object(bpy, bmesh, city_collection, material_lookup, kind, material_name, parts, "City")
            city_export_collection.objects.link(obj)
        roof_key = layout["roof_access"]["building_key"]
        roof_building = next(item for item in layout["buildings"] if item["key"] == roof_key)
        report["geometry_nodes_authoring"] = _create_procedural_facade_authoring(
            bpy, procedural_author_collection, city_export_collection, material_lookup["exposed_metal"],
            city["building_geometry"][roof_key], roof_building,
        )
    preview_collection = bpy.data.collections.new("TokyoNovaPreviewOnly")
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
    expected_north_batches = len(_mesh_batches([assembly for assembly in assemblies if assembly.kind in {"food_stall", "terminal_repair", "patched_housing_facade", "pocket_phone", "north_frontage_pavement", "north_facility_connector"}])) if city is not None else report["blender_object_count"]
    if len(objects) != expected_north_batches:
        raise RuntimeError(f"expected {expected_north_batches} north material batches, reopened {len(objects)}")
    export_objects: list[Any] = []
    if city is not None and city_collection is not None:
        city_collection = bpy.data.collections.get("TokyoNovaCity")
        city_objects = [obj for obj in city_collection.objects if obj.type == "MESH"] if city_collection else []
        expected_city_batches = report["blender_object_count"] - expected_north_batches
        if len(city_objects) != expected_city_batches:
            raise RuntimeError(f"expected {expected_city_batches} city-extension material batches, reopened {len(city_objects)}")
        export_group = bpy.data.collections.get("TokyoNovaCityExport")
        export_objects = [obj for obj in export_group.objects if obj.type == "MESH"] if export_group else []
        if len(export_objects) != expected_city_batches + 1:
            raise RuntimeError(f"expected {expected_city_batches + 1} exported city meshes including the evaluated node group, reopened {len(export_objects)}")
        author_collection = bpy.data.collections.get("TokyoNovaProceduralAuthoring")
        author_objects = [obj for obj in author_collection.objects if obj.type == "MESH"] if author_collection else []
        author = next((obj for obj in author_objects if obj.name == "GN_CastTie_Authoring_Source"), None)
        if author is None or not any(mod.type == "NODES" and mod.node_group is not None for mod in author.modifiers):
            raise RuntimeError("the editable Geometry Nodes authoring object did not survive the Blender round trip")
        export_gn = [obj for obj in export_objects if obj.get("evaluated_from_geometry_nodes")]
        if len(export_gn) != 1 or export_gn[0].modifiers:
            raise RuntimeError("the static city export does not contain exactly one baked Geometry Nodes result")
        if not export_gn[0].data.uv_layers or not all(poly.normal.length > 0.99 for poly in export_gn[0].data.polygons):
            raise RuntimeError("the procedural export mesh lacks UVs or valid static normals")
        export_materials = [item.name for item in export_gn[0].data.materials if item is not None]
        export_material_indices = {polygon.material_index for polygon in export_gn[0].data.polygons}
        if len(export_materials) != 1 or export_material_indices != {0}:
            raise RuntimeError("the evaluated procedural export must use one assigned material slot at index zero")
        report["geometry_nodes_authoring"]["round_trip"] = {
            "source_node_modifiers": [mod.node_group.name for mod in author.modifiers if mod.type == "NODES"],
            "evaluated_export_is_static": not export_gn[0].modifiers,
            "static_mesh_is_rebuilt": export_gn[0].data.name == "GN_CastTie_StaticExport_Mesh",
            "export_material_slots": export_materials,
            "export_material_indices": sorted(export_material_indices),
            "export_uv_quality": _uv_quality_report(export_gn[0].data),
        }
    else:
        city_objects = []
    if any(not obj.data.polygons or not obj.data.uv_layers for obj in [*objects, *city_objects]):
        raise RuntimeError("reopened source contains an empty mesh or missing UVs")
    uv_meshes = [*objects, *city_objects]
    if city is not None:
        uv_meshes.extend(obj for obj in export_objects if obj.get("evaluated_from_geometry_nodes"))
    uv_reports = {obj.name: _uv_quality_report(obj.data, metric="night_sky_dome" not in obj.name) for obj in uv_meshes}
    metric_issues = {name: item["metric_issues"] for name, item in uv_reports.items() if item["metric_issues"]}
    if metric_issues:
        raise RuntimeError(f"reopened source has non-metric UV0 triangles: {list(metric_issues.items())[:4]}")
    uv_faces = sum(item["faces"] for item in uv_reports.values())
    uv_degenerate = sum(item["degenerate_faces"] for item in uv_reports.values())
    if uv_faces and uv_degenerate / uv_faces > 0.01:
        raise RuntimeError(f"{uv_degenerate} of {uv_faces} reopened mesh faces have zero UV area")
    report.update({
        "uv_quality": {"mesh_count": len(uv_reports), "face_count": uv_faces, "degenerate_face_count": uv_degenerate, "degenerate_fraction": uv_degenerate / max(1, uv_faces), "meshes": uv_reports, "secondary_uv_policy": "existing UV layers are copied with mesh data and never removed; new meshes author UV0"},
        "blend_path": str(output_path.resolve()),
        "blender_version": bpy.app.version_string,
        "reopened_mesh_objects": len(objects) + len(city_objects),
        "reopened_north_meshes": len(objects),
        "reopened_city_extension_meshes": len(city_objects),
        "reopened_city_export_meshes": len(export_objects) if city is not None else 0,
        "reopened_uv_meshes": sum(bool(obj.data.uv_layers) for obj in [*objects, *city_objects]),
        "reopened_valid_normal_polygons": sum(sum(poly.normal.length > 0.99 for poly in obj.data.polygons) for obj in [*objects, *city_objects]),
        "preview_scene_objects": preview_outputs,
        "offline_render_status": "not rendered yet; run modeling/tokyo_nova/render_city_previews.py with CPU Cycles",
        "export_collection": "TokyoNovaNorth" if sector == "north" else "TokyoNovaCityExport",
        "editable_city_source_collection": "TokyoNovaCity" if sector == "all" else None,
        "geometry_nodes_authoring_collection": "TokyoNovaProceduralAuthoring" if sector == "all" else None,
        "preserved_north_export_collection": "TokyoNovaNorth" if sector == "all" else None,
        "preview_collection_excluded_from_export": "TokyoNovaPreviewOnly",
    })
    report_path = output_path.parent / ("city-resource-report.json" if sector == "all" else "north-resource-report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector", choices=("north", "all"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layout", type=Path, default=Path("content/tokyo-nova/layout.json"))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.output.suffix.lower() != ".blend":
        raise SystemExit("--output must be an editable .blend file path")
    report = build_blend(args.layout, args.output, args.sector)
    print(("TOKYO_NOVA_CITY_REPORT=" if args.sector == "all" else "TOKYO_NOVA_NORTH_REPORT=") + json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
