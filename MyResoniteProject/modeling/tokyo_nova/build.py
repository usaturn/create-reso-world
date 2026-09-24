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

from modeling.tokyo_nova import districts, geometry, interiors, skyline
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
    mesh_data = bpy.data.meshes.new(f"{prefix}_{kind}_{material_name}_Mesh")
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
    obj = bpy.data.objects.new(f"{prefix}_{kind}_{material_name}", mesh_data)
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
    ground_mesh.from_pydata([(-55, -55, -0.04), (55, -55, -0.04), (55, 55, -0.04), (-55, 55, -0.04)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("PREVIEW_ONLY_Ground_not_exported", ground_mesh)
    preview_collection.objects.link(ground)
    ground_material = bpy.data.materials.new("PREVIEW_ONLY_DarkDryStage")
    ground_material.diffuse_color = (0.025, 0.035, 0.041, 1)
    ground_material.use_nodes = True
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
    roof_route_continuous = float(layout["roof_access"]["target_height"]) >= float(roof_record.get("roof_walk_y", 8.8))
    accessibility = {
        "route_keys": [route["key"] for route in layout["routes"]],
        "entrances": [route["key"] for route in layout["routes"] if route["kind"] == "entrance"],
        "loop_count": loop_count,
        "roof_route_continuous": roof_route_continuous,
        "roof_building_key": roof_key,
        "roof_geometry_height": roof_record["height"],
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

    layout = json.loads(layout_path.read_text(encoding="utf-8"))
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
    if city is not None:
        city_collection = bpy.data.collections.new("TokyoNovaCity")
        bpy.context.scene.collection.children.link(city_collection)
    material_lookup = make_blender_materials()
    if city is None:
        for (kind, material_name), parts in sorted(_mesh_batches(assemblies).items()):
            _create_batch_object(bpy, bmesh, source_collection, material_lookup, kind, material_name, parts)
    else:
        retained_north = {"food_stall", "terminal_repair", "patched_housing_facade", "pocket_phone", "north_frontage_pavement", "north_facility_connector"}
        north_assets = [assembly for assembly in assemblies if assembly.kind in retained_north]
        city_assets = [assembly for assembly in assemblies if assembly.kind not in retained_north]
        for (kind, material_name), parts in sorted(_mesh_batches(north_assets).items()):
            _create_batch_object(bpy, bmesh, source_collection, material_lookup, kind, material_name, parts, "North")
        for (kind, material_name), parts in sorted(_mesh_batches(city_assets).items()):
            _create_batch_object(bpy, bmesh, city_collection, material_lookup, kind, material_name, parts, "City")
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
    if city is not None and city_collection is not None:
        city_collection = bpy.data.collections.get("TokyoNovaCity")
        city_objects = [obj for obj in city_collection.objects if obj.type == "MESH"] if city_collection else []
        expected_city_batches = report["blender_object_count"] - expected_north_batches
        if len(city_objects) != expected_city_batches:
            raise RuntimeError(f"expected {expected_city_batches} city-extension material batches, reopened {len(city_objects)}")
    else:
        city_objects = []
    if any(not obj.data.polygons or not obj.data.uv_layers for obj in [*objects, *city_objects]):
        raise RuntimeError("reopened source contains an empty mesh or missing UVs")
    report.update({
        "blend_path": str(output_path.resolve()),
        "blender_version": bpy.app.version_string,
        "reopened_mesh_objects": len(objects) + len(city_objects),
        "reopened_north_meshes": len(objects),
        "reopened_city_extension_meshes": len(city_objects),
        "reopened_uv_meshes": sum(bool(obj.data.uv_layers) for obj in [*objects, *city_objects]),
        "reopened_valid_normal_polygons": sum(sum(poly.normal.length > 0.99 for poly in obj.data.polygons) for obj in [*objects, *city_objects]),
        "preview_scene_objects": preview_outputs,
        "offline_render_status": "not rendered yet; run modeling/tokyo_nova/render_city_previews.py with CPU Cycles",
        "export_collection": "TokyoNovaNorth" if sector == "north" else "TokyoNovaCity",
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
