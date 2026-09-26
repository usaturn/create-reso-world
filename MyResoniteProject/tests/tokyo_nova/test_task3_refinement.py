"""Regression tests for Task 3 review fixes and the authored Blender workflow."""
from __future__ import annotations

import copy
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from modeling.tokyo_nova import build, interiors, pipeline, skyline
from modeling.tokyo_nova.layout import build_layout


@lru_cache(maxsize=1)
def _city() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    layout = build_layout()
    city = build.build_city(layout)
    manifest = pipeline.build_city_manifest(layout, city)
    return layout, city, manifest


def _bounds(vertices: list[tuple[float, float, float]]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    return (
        tuple(min(vertex[axis] for vertex in vertices) for axis in range(3)),  # type: ignore[return-value]
        tuple(max(vertex[axis] for vertex in vertices) for axis in range(3)),  # type: ignore[return-value]
    )


def _center(vertices: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    low, high = _bounds(vertices)
    return tuple((low[axis] + high[axis]) / 2 for axis in range(3))  # type: ignore[return-value]


def _quat_multiply(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def _manifest_colliders(manifest: dict[str, Any]) -> list[tuple[str, tuple[float, ...], tuple[float, ...]]]:
    """Compose every active BoxCollider into root-local world-AABB bounds."""
    colliders: list[tuple[str, tuple[float, ...], tuple[float, ...]]] = []
    identity = (0.0, 0.0, 0.0, 1.0)

    def walk(node: dict[str, Any], parent_position: tuple[float, float, float], parent_rotation: tuple[float, float, float, float], parent_scale: tuple[float, float, float], path: str) -> None:
        slot = node.get("slot", {})
        key = str(slot.get("key", ""))
        local_position = tuple(float(value) for value in slot.get("position", (0.0, 0.0, 0.0)))
        local_rotation = tuple(float(value) for value in slot.get("rotation", identity))
        local_scale = tuple(float(value) for value in slot.get("scale", (1.0, 1.0, 1.0)))
        # Root coordinates in manifests are world placement; compare all authored paths root-locally.
        if key == "root":
            origin, rotation, scale = (0.0, 0.0, 0.0), identity, (1.0, 1.0, 1.0)
        else:
            scaled = tuple(parent_scale[i] * local_position[i] for i in range(3))
            rotated = pipeline._rotate_vector(parent_rotation, scaled)
            origin = tuple(parent_position[i] + rotated[i] for i in range(3))
            rotation = _quat_multiply(parent_rotation, local_rotation)  # type: ignore[arg-type]
            scale = tuple(parent_scale[i] * local_scale[i] for i in range(3))
        owner_path = f"{path}/{key}" if path else key
        for component in node.get("components", []):
            if component.get("type") != "FrooxEngine.BoxCollider":
                continue
            fields = component.get("fields", {})
            if fields.get("Enabled", True) is False:
                continue
            offset = tuple(float(value) * scale[i] for i, value in enumerate(fields.get("Offset", (0.0, 0.0, 0.0))))
            rotated_offset = pipeline._rotate_vector(rotation, offset)
            center = tuple(origin[i] + rotated_offset[i] for i in range(3))
            size = tuple(float(value) * scale[i] for i, value in enumerate(fields["Size"]))
            axes = [pipeline._rotate_vector(rotation, basis) for basis in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))]
            half = tuple(sum(abs(axes[axis][component_axis]) * size[axis] / 2 for axis in range(3)) for component_axis in range(3))
            low = tuple(center[i] - half[i] for i in range(3))
            high = tuple(center[i] + half[i] for i in range(3))
            colliders.append((f"{owner_path}/{component.get('key', '')}", low, high))
        for child in node.get("children", []):
            walk(child, origin, rotation, scale, owner_path)

    walk(manifest, (0.0, 0.0, 0.0), identity, (1.0, 1.0, 1.0), "")
    return colliders


def _intersects(a_min: tuple[float, ...], a_max: tuple[float, ...], b_min: tuple[float, ...], b_max: tuple[float, ...]) -> bool:
    return all(a_min[axis] < b_max[axis] - 1e-5 and b_min[axis] < a_max[axis] - 1e-5 for axis in range(3))


def _basement_body_samples(layout: dict[str, Any], manifest: dict[str, Any]) -> list[tuple[str, tuple[float, float, float], tuple[float, float, float], str]]:
    nodes = {node["slot"]["key"]: node for node in pipeline.iter_slots(manifest)}
    samples = []
    for access in layout["basement_access"]:
        key = access["key"] + ("_walk_surface" if access["kind"] == "open_stairwell_and_landing" else "")
        node = nodes[key]
        collider = next(c for c in node["components"] if c["type"] == "FrooxEngine.BoxCollider")
        _width, thickness, length = collider["fields"]["Size"]
        position = node["slot"]["position"]
        for step in range(21):
            local = (0.0, thickness / 2, (step / 20 - .5) * length)
            contact = pipeline._rotate_vector(node["slot"]["rotation"], local)
            # Sample the smooth collision surface, not the lower decorative
            # stair treads. 0.20m allows for the heel on the 2.2/3 bar gradient;
            # the standing head envelope is conservatively 2.08m above contact.
            center = (position[0]+contact[0], position[1]+contact[1]+.94+.20, position[2]+contact[2])
            samples.append((access["key"], center, (0.46, 1.88, 0.46), key))
    return samples


def test_basement_body_paths_are_clear_in_the_composed_collider_world() -> None:
    layout, _city_geometry, manifest = _city()
    colliders = _manifest_colliders(manifest)
    samples = _basement_body_samples(layout, manifest)
    assert samples, "both authored basement descents must produce body-clearance samples"
    walkable_keys = {"south_theatre_basement_ramp", "theatre_basement_landing", "bar_basement_landing"}
    walkable_keys.update(access["key"] + "_walk_surface" for access in layout["basement_access"] if access["kind"] == "open_stairwell_and_landing")
    blockers = []
    for path_key, (cx, cy, cz), (body_width, body_height, body_depth), _support_key in samples:
        body_min = (cx - body_width / 2, cy - body_height / 2, cz - body_depth / 2)
        body_max = (cx + body_width / 2, cy + body_height / 2, cz + body_depth / 2)
        for collider_key, low, high in colliders:
            # The AABB of a slope overlaps its own standing body; exempt only
            # the exact authored support slots, not arbitrary prefix matches.
            if collider_key.split("/")[-2] in walkable_keys:
                continue
            if _intersects(body_min, body_max, low, high):
                blockers.append((path_key, collider_key))
    assert not blockers, f"composed emitted colliders intersect a basement body path: {blockers[:12]}"


def test_basement_grade_floors_are_cut_to_the_emitted_access_openings() -> None:
    layout, city, _manifest = _city()
    buildings = {building["key"]: building for building in layout["buildings"]}
    access_by_building = {access["building_key"]: access for access in layout["basement_access"]}
    assemblies = [assembly for assembly in city["assemblies"] if assembly.kind in {"district_building", "interior_room"}]
    blocked = []
    for assembly in assemblies:
        access = access_by_building.get(assembly.name)
        if access is None:
            continue
        building = buildings[assembly.name]
        center_x, _center_y, center_z = building["center"]
        opening = access["floor_opening"]
        open_center_x = center_x + float(opening["center"][0])
        open_center_z = center_z + float(opening["center"][1])
        size_x, size_z = (float(value) for value in opening["size"])
        hole_min = (open_center_x - size_x / 2, open_center_z - size_z / 2)
        hole_max = (open_center_x + size_x / 2, open_center_z + size_z / 2)
        for part in assembly.transformed_parts():
            if "floor" not in part.name:
                continue
            low, high = _bounds(part.vertices)
            overlaps_hole = low[0] < hole_max[0] and hole_min[0] < high[0] and low[2] < hole_max[1] and hole_min[1] < high[2]
            if overlaps_hole and low[1] <= 0.06 and high[1] > -0.03:
                blocked.append(f"{assembly.name}/{part.name}")
    assert not blocked, f"grade-level emitted floor panels cover declared basement openings: {blocked}"


def _ramp_surface_end(slot: dict[str, Any], end: bool) -> tuple[float, float, float]:
    mesh = next(component for component in slot["components"] if component["type"] == "FrooxEngine.BoxMesh")
    _width, thickness, length = (float(value) for value in mesh["fields"]["Size"])
    rotation = slot["slot"]["rotation"]
    direction = 1.0 if end else -1.0
    along = pipeline._rotate_vector(rotation, (0.0, 0.0, direction * length / 2))
    normal = pipeline._rotate_vector(rotation, (0.0, thickness / 2, 0.0))
    position = slot["slot"]["position"]
    return tuple(float(position[axis]) + along[axis] + normal[axis] for axis in range(3))


def test_roof_access_is_a_guarded_switchback_meeting_the_emitted_roof() -> None:
    layout, city, manifest = _city()
    roof_key = layout["roof_access"]["building_key"]
    building = next(item for item in city["assemblies"] if item.kind == "district_building" and item.name == roof_key)
    roof_slab = next(part for part in building.transformed_parts() if part.name.endswith("_roof_slab"))
    roof_bounds = _bounds(roof_slab.vertices)
    roof_y = roof_bounds[1][1]
    assert math.isclose(float(city["building_geometry"][roof_key]["roof_walk_y"]), roof_y, abs_tol=0.005), "roof access metadata must come from the emitted slab surface"

    slots = {slot.get("slot", {}).get("key"): slot for slot in pipeline.iter_slots(manifest)}
    ramp_keys = ("roof_access_ramp_lower", "roof_access_ramp_middle", "roof_access_ramp")
    assert all(key in slots for key in ramp_keys), "roof route must contain its three authored switchback flights"
    ends = [_ramp_surface_end(slots[key], True) for key in ramp_keys]
    starts = [_ramp_surface_end(slots[key], False) for key in ramp_keys]
    assert math.dist(ends[0], starts[1]) <= 4.1, "first turn must remain within its walkable landing"
    assert math.dist(ends[1], starts[2]) <= 4.1, "second turn must remain within its walkable landing"
    final = ends[-1]
    west_edge_x = roof_bounds[0][0]
    assert math.isclose(final[0], west_edge_x, abs_tol=0.01), "ramp must meet the actual roof slab edge"
    assert math.isclose(final[1], roof_y, abs_tol=0.01), "ramp surface must meet the roof without a step"
    for key in ramp_keys:
        start, end = _ramp_surface_end(slots[key], False), _ramp_surface_end(slots[key], True)
        horizontal = math.hypot(end[0] - start[0], end[2] - start[2])
        assert horizontal > 0 and abs(end[1] - start[1]) / horizontal <= 0.20, f"{key} exceeds the authored safe rise/run"

    rail_names = {part.name for part in building.parts if "_roof_rail_" in part.name}
    for side in ("west", "east", "north", "south"):
        assert any(f"_roof_rail_{side}_" in name for name in rail_names), f"roof edge {side} has no guardrail geometry"
    entry_z = final[2]
    west_rails = [part for part in building.transformed_parts() if "_roof_rail_west_" in part.name]
    for rail in west_rails:
        low, high = _bounds(rail.vertices)
        crosses_entry = low[0] <= final[0] + 0.06 and high[0] >= final[0] - 0.06 and low[2] < entry_z + 0.9 and entry_z - 0.9 < high[2]
        assert not crosses_entry, f"west roof guardrail blocks the ramp landing: {rail.name}"


def test_windows_glazing_frames_and_emission_share_the_same_facade_frame() -> None:
    layout, city, _manifest = _city()
    district_assemblies = [assembly for assembly in city["assemblies"] if assembly.kind == "district_building"]
    observed_fronts = set()
    checked = 0
    for assembly in district_assemblies:
        windows: dict[str, dict[str, tuple[float, float, float]]] = {}
        for part in assembly.transformed_parts():
            if "_front_glazing_" in part.name:
                windows[part.name.rsplit("_", 1)[-1]] = {"glass": _center(part.vertices)}
            elif "_interior_warm_window_" in part.name:
                level = part.name.rsplit("_", 1)[-1]
                windows.setdefault(level, {})["emission"] = _center(part.vertices)
        if not windows:
            continue
        building = next(item for item in layout["buildings"] if item["key"] == assembly.name)
        observed_fronts.add(building["front"])
        for level, details in windows.items():
            assert set(details) == {"glass", "emission"}, f"{assembly.name} level {level} has a mismatched pane/emission pair"
            assert math.dist(details["glass"], details["emission"]) <= 0.12, f"{assembly.name} level {level} misaligns glass and warm interior light"
            checked += 1
    assert observed_fronts == {"north", "south", "east", "west"}
    assert checked >= 20, "all emitted window levels need co-framed glazing and emission"


def test_emitted_props_have_functional_forms_not_only_catalog_names() -> None:
    specs = {spec[0]: spec for spec in interiors._ASSET_SPECS}
    examples = {key: interiors._build_prop(key, (0.0, 0.0, 0.0), 0.0, specs[key]) for key in (
        "rain_gutter", "ac_compressor", "wall_fan", "antenna_yagi", "instrument_trolley",
        "chain_hoist", "motorcycle_static", "recliner_seat", "wash_sink", "street_bowl_rack",
    )}
    part_names = {key: [part.name for part in asset.parts] for key, asset in examples.items()}
    requirements = {
        "rain_gutter": ("open_trough", "downspout_elbow"),
        "ac_compressor": ("fan_blade_", "mounting_foot", "condenser_grille"),
        "wall_fan": ("fan_blade_", "guard_ring", "mounting_bracket"),
        "antenna_yagi": ("boom", "radiator_", "mast_clamp"),
        "instrument_trolley": ("tray_deck_", "caster_wheel_", "push_handle"),
        "chain_hoist": ("chain_link_", "load_hook", "upper_trolley"),
        "motorcycle_static": ("tire_torus_", "engine_case", "front_fork"),
        "recliner_seat": ("footrest", "tilt_link", "seat_cushion"),
        "wash_sink": ("open_sink_bowl", "drain", "faucet_spout"),
        "street_bowl_rack": ("hollow_bowl_", "rack_divider"),
    }
    missing = {key: [token for token in tokens if not any(token in name for name in part_names[key])] for key, tokens in requirements.items()}
    assert not {key: tokens for key, tokens in missing.items() if tokens}, f"named assets lack function-defining geometry: {missing}"

    _layout, city, _manifest = _city()
    assert len(city["prop_geometry"]) == 76
    prop_assemblies = [asset for asset in city["assemblies"] if asset.kind == "interior_props"]
    by_kind = {key: next((asset for asset in prop_assemblies if asset.name.endswith(f"_{key}")), None) for key in city["prop_geometry"]}
    assert all(asset is not None for asset in by_kind.values()), "the reported prop catalog must equal actually emitted geometry"
    generic_only = []
    generic_features = {"casing", "service_cover", "body", "access_panel", "service_detail_0", "service_detail_1"}
    for key, asset in by_kind.items():
        assert asset is not None
        functional_parts = [part for part in asset.parts if part.name.rsplit("_", 1)[-1] not in generic_features]
        if len(functional_parts) < 3:
            generic_only.append(key)
    assert not generic_only, f"props still rely on generic family geometry: {generic_only}"


def test_theatre_waves_are_between_the_screen_face_and_audience() -> None:
    _layout, city, _manifest = _city()
    screen = next(asset for asset in city["assemblies"] if asset.kind == "interior_props" and asset.name.endswith("_abstract_sea_screen"))
    parts = {part.name: part for part in screen.transformed_parts()}
    face_part = next(part for name, part in parts.items() if name.endswith("_glass_or_screen"))
    face = _bounds(face_part.vertices)[0][2]
    waves = [part for name, part in parts.items() if "sea_wave" in name]
    assert len(waves) >= 4
    assert all(max(vertex[2] for vertex in wave.vertices) < face - 0.002 for wave in waves), "wave motif must sit in front of the screen's negative-Z display face"
    audience = [asset for asset in city["assemblies"] if asset.kind == "interior_props" and asset.name.endswith("_recliner_seat")]
    assert audience, "the theatre must emit its audience seating"
    seat_z = sum(asset.bounds[0][2] + asset.bounds[1][2] for asset in audience) / (2 * len(audience))
    assert all(min(vertex[2] for vertex in wave.vertices) > seat_z for wave in waves), "wave motif must remain in the audience-to-screen sight line"


def test_owned_sky_dome_mesh_winding_and_exported_normals_face_inward() -> None:
    dome = skyline._dome().parts[0]
    center = (0.0, -18.0, 0.0)
    outward = []
    for face in dome.faces:
        a, b, c = (dome.vertices[index] for index in face[:3])
        ab = tuple(b[axis] - a[axis] for axis in range(3))
        ac = tuple(c[axis] - a[axis] for axis in range(3))
        normal = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
        centroid = tuple(sum(dome.vertices[index][axis] for index in face) / len(face) for axis in range(3))
        radial = tuple(centroid[axis] - center[axis] for axis in range(3))
        dot = sum(normal[axis] * radial[axis] for axis in range(3))
        if dot > 1e-7:
            outward.append(face)
    assert not outward, f"source dome contains {len(outward)} outward-facing faces"

    export_dir = Path("content/tokyo-nova/city/export")
    exported = list(export_dir.glob("mesh_City_night_sky_dome_glass_*.mesh.json")) if export_dir.exists() else []
    if not exported:
        return  # Blender/ResoLoop export verification is performed after the city build.
    data = json.loads(exported[0].read_text(encoding="utf-8"))
    bad_normals = []
    for vertex in data["vertices"]:
        position = vertex["position"]
        normal = vertex["normal"]
        radial = (position["x"], position["y"] + 18.0, position["z"])
        radial_length = math.sqrt(sum(value * value for value in radial))
        normal_length = math.sqrt(sum(normal[axis] ** 2 for axis in ("x", "y", "z")))
        if radial_length <= 1e-8 or normal_length <= 1e-8:
            bad_normals.append(position)
            continue
        dot = sum(normal[axis] * radial[index] for index, axis in enumerate(("x", "y", "z"))) / (radial_length * normal_length)
        if dot >= -0.25:
            bad_normals.append(position)
    assert not bad_normals, f"exported dome vertex normals do not face its interior: {bad_normals[:4]}"


def test_exported_city_uvs_have_non_degenerate_metric_area() -> None:
    export_dir = Path("content/tokyo-nova/city/export")
    if not export_dir.exists():
        return  # The export audit is exercised after building the Blender source.
    bad = []
    total = 0
    for path in export_dir.glob("mesh_City*.mesh.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        vertices = data["vertices"]
        for submesh in data["submeshes"]:
            indices = submesh.get("vertexIndices", [])
            for offset in range(0, len(indices) - 2, 3):
                tri = [vertices[indices[offset + index]] for index in range(3)]
                xyz = [tuple(float(vertex["position"][axis]) for axis in ("x", "y", "z")) for vertex in tri]
                ab = tuple(xyz[1][axis] - xyz[0][axis] for axis in range(3))
                ac = tuple(xyz[2][axis] - xyz[0][axis] for axis in range(3))
                cross = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
                area_3d = math.sqrt(sum(value * value for value in cross)) / 2
                if area_3d <= 1e-9:
                    continue
                uv = [vertex["uvs"][0]["uv"] for vertex in tri]
                area_uv = abs((uv[1]["x"] - uv[0]["x"]) * (uv[2]["y"] - uv[0]["y"]) - (uv[1]["y"] - uv[0]["y"]) * (uv[2]["x"] - uv[0]["x"])) / 2
                total += 1
                if area_uv <= 1e-10:
                    bad.append(path.name)
    assert total > 1000
    assert len(bad) / total < 0.01, f"{len(bad)} of {total} emitted city triangles have zero UV area; samples: {bad[:8]}"


def test_atmosphere_glow_stays_distant_instead_of_ringing_the_plaza() -> None:
    _layout, city, _manifest = _city()
    atmosphere = next(asset for asset in city["assemblies"] if asset.kind == "night_atmosphere")
    near_warm_vertices = [
        vertex for part in atmosphere.parts if part.material == "warm_light"
        for vertex in part.vertices if math.hypot(vertex[0], vertex[2]) < 40.0
    ]
    assert not near_warm_vertices, f"owned warm horizon glow forms a close ring around the plaza ({len(near_warm_vertices)} vertices inside 40 m)"


def test_brutalist_generation_exposes_bounded_parameters_and_seeded_variation() -> None:
    layout, city, _manifest = _city()
    generation = layout.get("generation")
    assert generation is not None, "district authoring must expose bounded storey, module, detail-density, and seed parameters"
    assert generation["storeys_min"] == 3 and generation["storeys_max"] == 8
    assert 2.4 <= generation["storey_height_m"] <= 3.4
    assert 0.8 <= generation["facade_module_width_m"] <= 2.4
    assert 0.25 <= generation["facade_detail_density"] <= 1.0
    assert city["sky_geometry"]["inner_facing"] is True
    profiles = {record["architecture_profile"] for record in city["building_geometry"].values() if "architecture_profile" in record}
    assert len(profiles) >= 4, "district massing must vary among load-bearing Brutalist profiles"
    assert all(3 <= record["floor_count"] <= 8 for record in city["building_geometry"].values() if "architecture_profile" in record)

    low = copy.deepcopy(layout)
    low["generation"].update({"storeys_min": 3, "storeys_max": 3, "storey_height_m": 2.4, "facade_module_width_m": 0.8, "facade_detail_density": 0.25})
    high = copy.deepcopy(layout)
    high["generation"].update({"storeys_min": 8, "storeys_max": 8, "storey_height_m": 3.4, "facade_module_width_m": 2.4, "facade_detail_density": 1.0})
    from modeling.tokyo_nova.districts import build_districts
    _low_assemblies, low_records = build_districts(low)
    _high_assemblies, high_records = build_districts(high)
    assert {item["floor_count"] for item in low_records.values()} == {3}
    assert {key: item["floor_count"] for key, item in high_records.items() if key != "west_roof_access"} == {
        key: 8 for key in high_records if key != "west_roof_access"
    }
    assert high_records["west_roof_access"]["floor_count"] == 3, "the switchback receiving tower stays low enough for its bounded three-flight grade"
    assert max(item["height"] for item in high_records.values()) > max(item["height"] for item in low_records.values()) + 10


def test_city_geometry_nodes_authoring_contract_is_bounded_and_static_export_ready() -> None:
    spec_getter = getattr(build, "geometry_nodes_authoring_spec", None)
    assert callable(spec_getter), "the editable Blender city needs an explicit Geometry Nodes authoring contract"
    spec = spec_getter()
    assert isinstance(spec, dict)
    assert spec["editable_source"] is True
    assert spec["evaluated_static_export"] is True
    assert spec.get("static_export_material_policy") == "single nonempty material slot; all face indices normalize to zero", "the evaluated export must avoid empty/duplicate material slots that break static mesh serialization"
    assert spec.get("static_export_geometry_policy") == "rebuild applied node output from explicit vertices and polygon indices", "the static export must not retain Geometry Nodes mesh attributes that crash serialization"
    assert set(spec["controls"]) == {"Facade Module Width", "Storey Height", "Tie Density", "Pattern Seed"}
    for name, bounds in (("Facade Module Width", (0.8, 2.4)), ("Storey Height", (2.4, 3.4)), ("Tie Density", (0.25, 1.0)), ("Pattern Seed", (0, 2147483647))):
        assert spec["controls"][name]["minimum"] == bounds[0]
        assert spec["controls"][name]["maximum"] == bounds[1]
    assert {"GeometryNodeMeshGrid", "GeometryNodeInputIndex", "FunctionNodeRandomValue", "GeometryNodeDeleteGeometry", "GeometryNodeMeshIcoSphere"}.issubset(spec["nodes"])
    assert "GeometryNodeRealizeInstances" not in spec["nodes"], "only the static export copy may realize the authoring instances"


def test_every_emitted_asset_kind_has_multiple_physical_features() -> None:
    _layout, city, _manifest = _city()
    props = [assembly for assembly in city["assemblies"] if assembly.kind == "interior_props"]
    keys = list(city["prop_geometry"])
    assert len(keys) == 76
    by_kind = {key: next((asset for asset in props if asset.name.endswith(f"_{key}")), None) for key in keys}
    assert all(asset is not None for asset in by_kind.values()), "the reported prop catalog must equal actually emitted geometry"
    lacking = [key for key, asset in by_kind.items() if asset is None or len(asset.parts) < 3 or sum(len(part.faces) for part in asset.parts) < 12]
    assert not lacking, f"emitted props need multiple actual functional mesh features: {lacking}"
