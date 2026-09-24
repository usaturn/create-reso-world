"""Deterministic sector-based .blend build CLI for the akichi cyberpunk slum.

Run via ``resoloop blender run modeling/akichi/build.py --arg=--sector --arg=vacant
--arg=--output --arg=artifacts/akichi/vacant.blend --json``.

Seven sectors share one fixed layout (``layout.build_layout``): ``ground``,
``vacant``, ``towers``, ``market``, ``shacks``, ``nightlife`` and ``ads``.

Pipeline contract (Task 6):

* Resonite XYZ (Y up, metres) converts to Blender exactly once at the build
  boundary with the XZY swap in :func:`resonite_to_blender`. The swap mirrors
  the scene, so batch meshes get their face normals recalculated after the
  conversion and UV0 is authored against the negated polygon normal (audited
  with ``handedness=-1``).
* Every assembly merges its parts by material into one named batch mesh
  (``<assembly.name>__<material>``) via :func:`batch_assembly`, which bakes the
  assembly rotation (radians around Y) and origin into the vertices.
* The vacant lot's rubble uses a Geometry Nodes scatter (Distribute Points on
  Faces, density 0.35/m², seed 250925) baked to a static depsgraph-evaluated
  mesh. If the GN construction fails twice, a ``random.Random(250925)`` Python
  scatter with the same density and prototypes produces the fallback batches.
  Scatter meshes are audit-exempt because the jittered rubble-chunk prototype
  is intentionally non-metric.
* ``write_scene`` builds two collections: ``Akichi<Sector>`` (editable source,
  including the GN authoring plane) and ``Akichi<Sector>Export`` (static
  export: the same batch objects plus the baked scatter mesh). The .blend is
  saved, reopened and verified before the resource report is returned and
  written next to the output file.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modeling.akichi import geometry, props
from modeling.akichi.buildings import Assembly, _rotate, build_perimeter_wall, build_tower
from modeling.akichi.layout import build_layout, validate_layout
from modeling.akichi.materials import make_blender_materials
from modeling.akichi.uv import metric_face_uvs, uv_triangle_issues

Vec3 = tuple[float, float, float]
Face = tuple[int, ...]

SEED = 250925
SECTORS: tuple[str, ...] = ("ground", "vacant", "towers", "market", "shacks", "nightlife", "ads")

# Wall ads that stay with the nightlife strip: the three south-face ads on the
# north-band towers hosting the clubs (controller ruling: deterministic ID rule).
NIGHTLIFE_TOWERS: frozenset[str] = frozenset({"tower-01", "tower-02", "tower-03"})

GN_SCATTER_DENSITY = 0.35  # instances per m² on the vacant lot
GN_SCATTER_NODE_GROUP = "GN_AkichiVacantScatter"
GN_SCATTER_PROTO_COLLECTION = "AkichiVacantScatterPrototypes"
GN_SCATTER_PLANE = "AkichiVacantScatterPlane"
GN_SCATTER_BAKED = "AkichiVacantScatterBaked"
UV_PER_METER = 0.5

# Ground level offsets (Resonite Y). The ground slab tops out at 0.1; every
# overlay sits proud of the layer below so no two coplanar faces z-fight.
GROUND_TOP = 0.1
OVERLAY_BOTTOM = 0.102


def resonite_to_blender(point: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert Resonite XYZ (Y up) to Blender XYZ (Z up) with an XZY swap."""
    return (point[0], point[2], point[1])


# --- batch assembly (pure) -----------------------------------------------------


def batch_assembly(assembly: Assembly) -> dict[str, geometry.MeshData]:
    """Merge one assembly's parts by material into named batch meshes.

    Vertex batches concatenate the parts in declaration order and offset face
    indices; the assembly rotation (radians, world-up) and origin are applied
    to every vertex exactly once, here at the build boundary.
    """
    groups: dict[str, list[geometry.MeshData]] = {}
    for part in assembly.parts:
        groups.setdefault(part.material, []).append(part)
    batches: dict[str, geometry.MeshData] = {}
    for material, parts in groups.items():
        vertices: list[Vec3] = []
        faces: list[Face] = []
        for part in parts:
            offset = len(vertices)
            for vertex in part.vertices:
                rotated = _rotate(vertex, assembly.rotation)
                vertices.append(
                    (
                        rotated[0] + assembly.origin[0],
                        rotated[1] + assembly.origin[1],
                        rotated[2] + assembly.origin[2],
                    )
                )
            faces.extend(tuple(offset + index for index in face) for face in part.faces)
        key = f"{assembly.name}__{material}"
        batches[key] = geometry.mesh(key, vertices, faces, material)
    return batches


def _triangle_count(mesh: geometry.MeshData) -> int:
    return sum(len(face) - 2 for face in mesh.faces)


def _relocated(
    assembly: Assembly,
    *,
    name: str | None = None,
    origin: tuple[float, float, float] | None = None,
    rotation: float | None = None,
) -> Assembly:
    """Copy an assembly with a new name, origin or rotation (unique batch keys)."""
    return replace(
        assembly,
        name=name if name is not None else assembly.name,
        origin=origin if origin is not None else assembly.origin,
        rotation=rotation if rotation is not None else assembly.rotation,
    )


def _point_in_rect(point: Vec3, lo: Vec3, hi: Vec3) -> bool:
    return lo[0] <= point[0] <= hi[0] and lo[1] <= point[1] <= hi[1] and lo[2] <= point[2] <= hi[2]


def _vacant_spot(
    rng: random.Random,
    vmin: list[float],
    vmax: list[float],
    taken: list[tuple[float, float, float]],
    *,
    margin: float,
    clearance: float,
    central_half: tuple[float, float] = (6.5, 5.5),
) -> tuple[float, float]:
    """Rejection-sample a spot inside the vacant rect, clear of the collapsed
    structure's central box and of every previously taken spot. Falls back to a
    fixed corner-ish anchor after 64 tries so the layout always resolves."""
    for _ in range(64):
        x = rng.uniform(vmin[0] + margin, vmax[0] - margin)
        z = rng.uniform(vmin[1] + margin, vmax[1] - margin)
        if abs(x) < central_half[0] and abs(z) < central_half[1]:
            continue
        if all(math.hypot(x - tx, z - tz) >= clearance for tx, tz, _ in taken):
            return x, z
    return vmin[0] + margin + 0.5, vmin[1] + margin + 0.5


# --- sector assemblies (pure) --------------------------------------------------


def _ground_assemblies(data: dict[str, Any]) -> list[Assembly]:
    assemblies = [
        Assembly(
            kind="ground",
            name="ground",
            origin=(0.0, 0.0, 0.0),
            rotation=0.0,
            parts=[geometry.box("ground", (0.0, 0.0, 0.0), (100.0, 0.2, 100.0), "asphalt_cracked")],
        )
    ]
    # 8-15 worn-asphalt patches / wet puddles inside the street bands.
    rng = random.Random(SEED)
    streets = data["streets"]
    stall_centers = [(s["center"][0], s["center"][1]) for s in data["stalls"]]
    count = rng.randint(8, 15)
    patch_parts: list[geometry.MeshData] = []
    for index in range(count):
        band = streets[index % len(streets)]
        x0, z0 = band["min"]
        x1, z1 = band["max"]
        px = pz = 0.0
        w = d = 1.0
        for _ in range(8):
            px = rng.uniform(x0 + 0.5, x1 - 0.5)
            pz = rng.uniform(z0 + 0.5, z1 - 0.5)
            w = rng.uniform(0.8, 2.2)
            d = rng.uniform(0.8, 2.2)
            if all(math.hypot(px - sx, pz - sz) > 3.2 for sx, sz in stall_centers):
                break
        else:
            px, pz = x0 + 1.0, z0 + 1.0
        vmin, vmax = data["vacant"]["min"], data["vacant"]["max"]
        material = "mud" if (vmin[0] <= px <= vmax[0] and vmin[1] <= pz <= vmax[1]) else None
        if material is None:
            material = "patched_concrete" if rng.random() < 0.6 else "asphalt_wet"
        patch_parts.append(
            geometry.box(f"street-patch-{index:02d}", (px, OVERLAY_BOTTOM + 0.02, pz), (w, 0.04, d), material)
        )
    assemblies.append(
        Assembly(kind="street-patches", name="street-patches", origin=(0.0, 0.0, 0.0), rotation=0.0, parts=patch_parts)
    )
    vmin, vmax = data["vacant"]["min"], data["vacant"]["max"]
    center = ((vmin[0] + vmax[0]) / 2, OVERLAY_BOTTOM + 0.03, (vmin[1] + vmax[1]) / 2)
    size = (vmax[0] - vmin[0], 0.06, vmax[1] - vmin[1])
    assemblies.append(
        Assembly(
            kind="vacant-base",
            name="vacant-base",
            origin=(0.0, 0.0, 0.0),
            rotation=0.0,
            parts=[geometry.box("vacant-base", center, size, "mud")],
        )
    )
    assemblies.append(build_perimeter_wall(SEED))
    return assemblies


def _collapsed_structure() -> Assembly:
    """Central wreck of stacked beveled slabs with a few leaning beams."""
    rng = random.Random(SEED + 400)
    parts: list[geometry.MeshData] = []
    materials = ("concrete_dark", "concrete_mid", "patched_concrete")
    layer_bases = (0.0, 0.62, 1.24)
    layer_counts = (5, 4, 3)
    index = 0
    for base_y, count in zip(layer_bases, layer_counts):
        for _ in range(count):
            sx = rng.uniform(1.3, 2.1)
            sz = rng.uniform(1.1, 1.9)
            sy = rng.uniform(0.42, 0.66)
            y = base_y + sy / 2 + rng.uniform(-0.08, 0.08)
            parts.append(
                geometry.beveled_box(
                    f"slab-{index:02d}",
                    (rng.uniform(-3.6, 3.6), y, rng.uniform(-2.8, 2.8)),
                    (sx, sy, sz),
                    0.1,
                    rng.choice(materials),
                )
            )
            index += 1
    # Leaning concrete beams: a box along local +Z, rolled about X and yawed
    # about Y, anchored near the pile top so the far end sticks up askew.
    for beam_index in range(3):
        length = rng.uniform(2.2, 4.2)
        local = geometry.box(
            f"beam-{beam_index}", (0.0, 0.0, length / 2 - 0.3), (0.26, 0.4, length), materials[beam_index % 3]
        )
        roll = rng.uniform(-0.65, -0.2)  # negative roll: the far end tips up out of the pile
        yaw = rng.uniform(0.0, math.tau)
        anchor = (rng.uniform(-3.0, 3.0), rng.uniform(0.9, 1.5), rng.uniform(-2.4, 2.4))

        def transform(vertex: Vec3) -> Vec3:
            x, y, z = vertex
            cr, sr = math.cos(roll), math.sin(roll)  # about X
            y, z = y * cr - z * sr, y * sr + z * cr
            cy, sy = math.cos(yaw), math.sin(yaw)  # about Y
            x, z = x * cy + z * sy, -x * sy + z * cy
            return (x + anchor[0], y + anchor[1], z + anchor[2])

        parts.append(geometry.mesh(f"beam-{beam_index}", [transform(v) for v in local.vertices], local.faces, local.material))
    return Assembly(kind="collapsed-structure", name="collapsed-structure", origin=(0.0, 0.0, 0.0), rotation=0.0, parts=parts)


def _vacant_assemblies(data: dict[str, Any]) -> list[Assembly]:
    vmin, vmax = data["vacant"]["min"], data["vacant"]["max"]
    taken: list[tuple[float, float, float]] = []
    rng = random.Random(SEED)
    assemblies = [_collapsed_structure()]

    for index in range(2):
        x, z = _vacant_spot(rng, vmin, vmax, taken, margin=2.9, clearance=2.5)
        husk = props.build_vehicle_husk(SEED + index)
        assemblies.append(
            _relocated(husk, name=f"vehicle-husk-{index + 1:02d}", origin=(x, 0.0, z), rotation=rng.uniform(0.0, math.tau))
        )
        taken.append((x, z, 3.0))

    for index in range(3):
        x, z = _vacant_spot(rng, vmin, vmax, taken, margin=1.6, clearance=1.4)
        radius = rng.uniform(0.7, 1.0)
        pile = props.build_junk_pile(SEED + 130 + index, radius)
        assemblies.append(
            _relocated(
                pile,
                name=f"junk-pile-{index + 1:02d}",
                origin=(x, 0.0, z),
                rotation=rng.uniform(0.0, math.tau),
            )
        )
        taken.append((x, z, radius + 0.6))

    chunk_materials = ("concrete_mid", "concrete_stained", "patched_concrete")
    for index in range(6):
        x, z = _vacant_spot(rng, vmin, vmax, taken, margin=1.6, clearance=1.6)
        sx = rng.uniform(1.2, 2.6)
        sy = rng.uniform(0.8, 1.6)
        sz = rng.uniform(1.2, 2.6)
        chunk = geometry.beveled_box(
            f"large-chunk-{index + 1:02d}",
            (0.0, sy / 2 - 0.06, 0.0),
            (sx, sy, sz),
            0.12,
            rng.choice(chunk_materials),
        )
        assemblies.append(
            Assembly(
                kind="large-chunk",
                name=f"large-chunk-{index + 1:02d}",
                origin=(x, 0.0, z),
                rotation=rng.uniform(0.0, math.tau),
                parts=[chunk],
            )
        )
        taken.append((x, z, min(sx, sz)))
    return assemblies


def _tower_assemblies(data: dict[str, Any]) -> list[Assembly]:
    return [build_tower(spec, SEED) for spec in data["towers"]]


def _market_assemblies(data: dict[str, Any]) -> list[Assembly]:
    assemblies = [props.build_stall(spec, SEED) for spec in data["stalls"]]
    rng = random.Random(SEED + 160)
    for index, spec in enumerate(data["stalls"]):
        cx, cz = spec["center"]
        side = 1.9 if cx > 0 else -1.9
        radius = rng.uniform(0.6, 0.9)
        pile = props.build_junk_pile(SEED + 161 + index, radius)
        assemblies.append(
            _relocated(
                pile,
                name=f"junk-pile-{index + 1:02d}",
                origin=(cx + side, 0.0, cz + rng.uniform(-0.4, 0.4)),
                rotation=rng.uniform(0.0, math.tau),
            )
        )
        pad = geometry.box("pad", (0.0, OVERLAY_BOTTOM + 0.02, 0.0), (2.6, 0.04, 2.0), "mud")
        assemblies.append(
            Assembly(
                kind="stall-pad",
                name=f"stall-pad-{index + 1:02d}",
                origin=(cx, 0.0, cz),
                rotation=math.radians(float(spec["rotation"])),
                parts=[pad],
            )
        )
    return assemblies


def _shacks_assemblies(data: dict[str, Any]) -> list[Assembly]:
    assemblies = [props.build_shack(spec, SEED) for spec in data["shacks"]]
    rng = random.Random(SEED + 180)
    shack_centers = [(s["center"][0], s["center"][1]) for s in data["shacks"]]
    for index in range(5):
        for _ in range(16):
            x = rng.uniform(-40.5, -25.5)
            z = rng.uniform(-40.5, -29.5)
            if all(math.hypot(x - sx, z - sz) >= 2.2 for sx, sz in shack_centers):
                break
        else:
            x, z = -40.0 + (index % 4) * 3.4, -40.0 + (index // 4) * 3.4
        pile = props.build_junk_pile(SEED + 181 + index, rng.uniform(0.55, 0.85))
        assemblies.append(
            _relocated(
                pile,
                name=f"junk-pile-{index + 1:02d}",
                origin=(x, 0.0, z),
                rotation=rng.uniform(0.0, math.tau),
            )
        )
    assemblies.extend(props.build_cable(spec) for spec in data["cables"][0:4])
    return assemblies


def _nightlife_assemblies(data: dict[str, Any]) -> list[Assembly]:
    assemblies = [props.build_club(spec, SEED) for spec in data["nightlife"]]
    assemblies.extend(
        props.build_ad(spec, SEED)
        for spec in data["ads"]
        if spec["kind"] == "wall" and spec["attach"] in NIGHTLIFE_TOWERS
    )
    assemblies.extend(props.build_cable(spec) for spec in data["cables"][4:8])
    return assemblies


def _ads_assemblies(data: dict[str, Any]) -> list[Assembly]:
    nightlife_ads = {
        spec["id"]
        for spec in data["ads"]
        if spec["kind"] == "wall" and spec["attach"] in NIGHTLIFE_TOWERS
    }
    assemblies = [props.build_ad(spec, SEED) for spec in data["ads"] if spec["id"] not in nightlife_ads]
    assemblies.extend(props.build_cable(spec) for spec in data["cables"][8:12])
    return assemblies


_SECTOR_BUILDERS: dict[str, Callable[[dict[str, Any]], list[Assembly]]] = {
    "ground": _ground_assemblies,
    "vacant": _vacant_assemblies,
    "towers": _tower_assemblies,
    "market": _market_assemblies,
    "shacks": _shacks_assemblies,
    "nightlife": _nightlife_assemblies,
    "ads": _ads_assemblies,
}


def build_sector_assemblies(data: dict[str, Any], sector: str) -> list[Assembly]:
    """Build the sector's logical assemblies from a layout dict (pure Python)."""
    if sector not in _SECTOR_BUILDERS:
        raise ValueError(f"unknown sector {sector!r}; expected one of {SECTORS}")
    return _SECTOR_BUILDERS[sector](data)


def _python_scatter_assemblies(data: dict[str, Any]) -> list[Assembly]:
    """Fallback rubble scatter: same density and prototypes as the GN graph.

    One ``random.Random(SEED)`` draws, in a fixed order per instance, the
    prototype index, a full euler rotation and the x/z placement (matching the
    GN graph's Random Value nodes, which use the same seed for index and
    rotation). The three prototype groups become three assemblies so they stay
    one mesh batch per material.
    """
    rng = random.Random(SEED)
    prototypes = props.rubble_prototypes()
    x0, z0 = data["vacant"]["min"]
    x1, z1 = data["vacant"]["max"]
    count = round((x1 - x0) * (z1 - z0) * GN_SCATTER_DENSITY)
    grouped: dict[int, list[geometry.MeshData]] = {0: [], 1: [], 2: []}

    def rotate_euler(vertex: Vec3, euler: Vec3) -> Vec3:
        x, y, z = vertex
        cr, sr = math.cos(euler[0]), math.sin(euler[0])  # about X
        y, z = y * cr - z * sr, y * sr + z * cr
        cy, sy = math.cos(euler[1]), math.sin(euler[1])  # about Y
        x, z = x * cy + z * sy, -x * sy + z * cy
        cz, sz = math.cos(euler[2]), math.sin(euler[2])  # about Z
        return (x * cz - y * sz, x * sz + y * cz, z)

    for index in range(count):
        slot = rng.randrange(len(prototypes))
        prototype = prototypes[slot]
        euler = (rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi))
        place = (rng.uniform(x0 + 0.5, x1 - 0.5), 0.0, rng.uniform(z0 + 0.5, z1 - 0.5))
        vertices = tuple(
            (x + place[0], y + place[1], z + place[2]) for x, y, z in (rotate_euler(v, euler) for v in prototype.vertices)
        )
        grouped[slot].append(geometry.mesh(f"rubble-{index:03d}", vertices, prototype.faces, prototype.material))
    return [
        Assembly(kind="rubble-scatter", name=f"rubble-scatter-{slot:02d}", origin=(0.0, 0.0, 0.0), rotation=0.0, parts=grouped[slot])
        for slot in (0, 1, 2)
    ]


def resource_report(assemblies: list[Assembly], sector: str) -> dict[str, Any]:
    """Summarize the sector's polygon resources (brief's schema_version 1)."""
    assembled = list(assemblies)
    parts = [part for assembly in assembled for part in assembly.parts]
    return {
        "schema_version": 1,
        "sector": sector,
        "seed": SEED,
        "assembly_count": len(assembled),
        "total_parts": len(parts),
        "total_vertices": sum(len(part.vertices) for part in parts),
        "total_triangles": sum(_triangle_count(part) for part in parts),
        "blender_object_count": sum(len(batch_assembly(assembly)) for assembly in assembled),
        "material_count": len({part.material for part in parts}),
        "scatter_method": "n/a",
        "uv_issue_count": 0,
        "blend_path": None,
        "blender_version": None,
    }


# --- Blender object creation ---------------------------------------------------


def _author_face_uv(uv_layer: Any, mesh_data: Any, polygon: Any, uv_per_meter: float = UV_PER_METER) -> list[Any]:
    """Author metric UV0 for one polygon against the negated normal.

    The XZY conversion mirrors the scene, so the charted normal flips; the UV
    audit then runs with ``handedness=-1`` on the polygon's own normal.
    """
    loop_ids = list(polygon.loop_indices)
    points = [mesh_data.vertices[mesh_data.loops[index].vertex_index].co for index in loop_ids]
    normal = (-polygon.normal[0], -polygon.normal[1], -polygon.normal[2])
    uv_values = metric_face_uvs(points, normal, uv_per_meter=uv_per_meter)
    for loop_index, uv in zip(loop_ids, uv_values):
        uv_layer.data[loop_index].uv = uv
    return uv_values


def _audit_face_uv(mesh_data: Any, polygon: Any, uv_values: list[Any]) -> int:
    loop_ids = list(polygon.loop_indices)
    points = [mesh_data.vertices[mesh_data.loops[index].vertex_index].co for index in loop_ids]
    issues = 0
    for corner in range(1, len(loop_ids) - 1):
        issues += len(
            uv_triangle_issues(
                (points[0], points[corner], points[corner + 1]),
                (uv_values[0], uv_values[corner], uv_values[corner + 1]),
                polygon.normal,
                uv_per_meter=UV_PER_METER,
                handedness=-1,
            )
        )
    return issues


def _new_batch_mesh(bpy: Any, bmesh: Any, merged: geometry.MeshData, *, recover_normals: bool = True) -> Any:
    mesh_data = bpy.data.meshes.new(f"Akichi_{merged.name}_Mesh")
    mesh_data.from_pydata(
        [resonite_to_blender(vertex) for vertex in merged.vertices], [], [list(face) for face in merged.faces]
    )
    mesh_data.update()
    if recover_normals:
        bm = bmesh.new()
        bm.from_mesh(mesh_data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh_data)
        bm.free()
    return mesh_data


def _create_batch_object(
    bpy: Any,
    bmesh: Any,
    merged: geometry.MeshData,
    material_lookup: dict[str, Any],
    object_name: str,
    *,
    uv_exempt: bool = False,
) -> tuple[Any, int]:
    """One static mesh object per (assembly, material) batch, with metric UV0."""
    mesh_data = _new_batch_mesh(bpy, bmesh, merged)
    uv_layer = mesh_data.uv_layers.new(name="UV0")
    issues = 0
    for polygon in mesh_data.polygons:
        uv_values = _author_face_uv(uv_layer, mesh_data, polygon)
        if not uv_exempt:
            issues += _audit_face_uv(mesh_data, polygon, uv_values)
    object_ = bpy.data.objects.new(object_name, mesh_data)
    object_.data.materials.append(material_lookup[merged.material])
    object_["material_batch"] = merged.material
    object_["uv_policy"] = "0.5 UV/m face-local metric tiling; island overlap intentional for shared tileable materials"
    if uv_exempt:
        object_["scatter_uv_exempt"] = True
    if not uv_layer or not all(polygon.normal.length > 0.99 for polygon in mesh_data.polygons):
        raise RuntimeError(f"mesh batch {object_name} is missing UVs or valid normals")
    return object_, issues


# --- Geometry Nodes scatter ----------------------------------------------------


def _cleanup_scatter_state(bpy: Any) -> None:
    for name in (GN_SCATTER_BAKED, GN_SCATTER_PLANE):
        object_ = bpy.data.objects.get(name)
        if object_ is not None:
            bpy.data.objects.remove(object_, do_unlink=True)
    collection = bpy.data.collections.get(GN_SCATTER_PROTO_COLLECTION)
    if collection is not None:
        for object_ in list(collection.objects):
            bpy.data.objects.remove(object_, do_unlink=True)
        bpy.data.collections.remove(collection)
    group = bpy.data.node_groups.get(GN_SCATTER_NODE_GROUP)
    if group is not None:
        bpy.data.node_groups.remove(group)
    for mesh in [
        m
        for m in list(bpy.data.meshes)
        if m.name == "AkichiVacantScatter_Mesh" or m.name.startswith("AkichiScatterProto") or m.name == "AkichiVacantScatterPlane_M"
    ]:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def _try_gn_scatter(
    bpy: Any, bmesh: Any, data: dict[str, Any], material_lookup: dict[str, Any], source_collection: Any
) -> dict[str, Any]:
    """Construct the GN scatter graph (RNA-verified node/socket names) and bake
    the depsgraph-evaluated result into a static UV'd mesh linked in the export
    collection. Raises on any failure so the caller can retry or fall back."""
    vmin, vmax = data["vacant"]["min"], data["vacant"]["max"]
    prototypes = props.rubble_prototypes()

    prototype_collection = bpy.data.collections.new(GN_SCATTER_PROTO_COLLECTION)
    bpy.context.scene.collection.children.link(prototype_collection)
    for slot, prototype in enumerate(prototypes):
        mesh = bpy.data.meshes.new(f"AkichiScatterProto{slot}_M")
        mesh.from_pydata(
            [resonite_to_blender(vertex) for vertex in prototype.vertices], [], [list(face) for face in prototype.faces]
        )
        mesh.update()
        object_ = bpy.data.objects.new(f"AkichiScatterProto{slot}", mesh)
        prototype_collection.objects.link(object_)
        object_.data.materials.append(material_lookup[prototype.material])
        object_.hide_render = True

    plane_mesh = bpy.data.meshes.new("AkichiVacantScatterPlane_M")
    plane_mesh.from_pydata(
        [resonite_to_blender((x, 0.05, z)) for x, z in ((vmin[0], vmin[1]), (vmax[0], vmin[1]), (vmax[0], vmax[1]), (vmin[0], vmax[1]))],
        [],
        [(0, 1, 2, 3)],
    )
    plane_mesh.update()
    plane = bpy.data.objects.new(GN_SCATTER_PLANE, plane_mesh)
    source_collection.objects.link(plane)
    plane.hide_render = True

    # Node graph. Names all verified against Blender 5.0.1 RNA (probe): the
    # Distribute node lost its `distribution` enum socket in 5.0 (density path
    # is the default), and Random Value has no ROTATION data type, so the
    # rotation uses FLOAT_VECTOR (euler XYZ) with an implicit conversion into
    # the Instance on Points ROTATION socket.
    tree = bpy.data.node_groups.new(GN_SCATTER_NODE_GROUP, "GeometryNodeTree")
    tree.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes, links = tree.nodes, tree.links
    node_in = nodes.new("NodeGroupInput")
    node_out = nodes.new("NodeGroupOutput")
    node_in.location = (-1100, 0)
    node_out.location = (1200, 0)

    distribute = nodes.new("GeometryNodeDistributePointsOnFaces")
    distribute.location = (-820, 0)
    distribute.inputs["Density"].default_value = GN_SCATTER_DENSITY
    distribute.inputs["Seed"].default_value = SEED

    collection_info = nodes.new("GeometryNodeCollectionInfo")
    collection_info.location = (-820, 420)
    collection_info.inputs["Collection"].default_value = prototype_collection
    collection_info.inputs["Separate Children"].default_value = True
    collection_info.inputs["Reset Children"].default_value = True

    instance = nodes.new("GeometryNodeInstanceOnPoints")
    instance.location = (-480, 0)
    instance.inputs["Pick Instance"].default_value = True

    random_index = nodes.new("FunctionNodeRandomValue")
    random_index.location = (-760, -240)
    random_index.data_type = "INT"
    random_index.inputs["Min"].default_value = 0
    random_index.inputs["Max"].default_value = len(prototypes) - 1
    random_index.inputs["Seed"].default_value = SEED

    random_rotation = nodes.new("FunctionNodeRandomValue")
    random_rotation.location = (-760, -440)
    random_rotation.data_type = "FLOAT_VECTOR"
    random_rotation.inputs["Min"].default_value = (-math.pi, -math.pi, -math.pi)
    random_rotation.inputs["Max"].default_value = (math.pi, math.pi, math.pi)
    random_rotation.inputs["Seed"].default_value = SEED

    realize = nodes.new("GeometryNodeRealizeInstances")
    realize.location = (600, 0)

    in_geom = next(s for s in node_in.outputs if s.type == "GEOMETRY")
    out_geom = next(s for s in node_out.inputs if s.type == "GEOMETRY")
    links.new(in_geom, distribute.inputs["Mesh"])
    links.new(distribute.outputs["Points"], instance.inputs["Points"])
    links.new(collection_info.outputs["Instances"], instance.inputs["Instance"])
    links.new(random_index.outputs["Value"], instance.inputs["Instance Index"])
    links.new(random_rotation.outputs["Value"], instance.inputs["Rotation"])
    links.new(instance.outputs["Instances"], realize.inputs["Geometry"])
    links.new(realize.outputs["Geometry"], out_geom)

    modifier = plane.modifiers.new("AkichiVacantScatter", "NODES")
    modifier.node_group = tree

    # Evaluate through the depsgraph and bake a static export mesh.
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_object = plane.evaluated_get(depsgraph)
    evaluated = evaluated_object.to_mesh()
    if evaluated is None or len(evaluated.polygons) == 0 or len(evaluated.materials) == 0:
        evaluated_object.to_mesh_clear()
        raise RuntimeError("GN scatter produced an empty or material-less mesh")
    vertices = [tuple(vertex.co) for vertex in evaluated.vertices]
    faces = [tuple(polygon.vertices) for polygon in evaluated.polygons]
    material_indices = [polygon.material_index for polygon in evaluated.polygons]
    slot_names = [material.name for material in evaluated.materials if material is not None]
    evaluated_object.to_mesh_clear()

    baked_mesh = bpy.data.meshes.new("AkichiVacantScatter_Mesh")
    baked_mesh.from_pydata(vertices, [], faces)
    baked_mesh.update()
    for slot_name in slot_names:
        baked_mesh.materials.append(bpy.data.materials[slot_name])
    for polygon, material_index in zip(baked_mesh.polygons, material_indices):
        polygon.material_index = min(material_index, len(slot_names) - 1)
    if {polygon.material_index for polygon in baked_mesh.polygons} != set(range(len(slot_names))):
        raise RuntimeError("GN scatter material indices do not cover every prototype slot")
    bm = bmesh.new()
    bm.from_mesh(baked_mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(baked_mesh)
    bm.free()

    uv_layer = baked_mesh.uv_layers.new(name="UV0")
    for polygon in baked_mesh.polygons:
        _author_face_uv(uv_layer, baked_mesh, polygon)

    baked = bpy.data.objects.new(GN_SCATTER_BAKED, baked_mesh)
    baked["evaluated_from_geometry_nodes"] = True
    baked["gn_scatter_uv_exempt"] = True
    baked["uv_policy"] = "0.5 UV/m face-local metric tiling authored on the realized scatter; exempt from the metric audit (jittered chunk prototype)"
    return {
        "object": baked,
        "method": "geometry-nodes",
        "vertices": len(vertices),
        "triangles": sum(len(face) - 2 for face in faces),
        "slot_names": slot_names,
        "area_m2": (vmax[0] - vmin[0]) * (vmax[1] - vmin[1]),
        "expected_instances": round((vmax[0] - vmin[0]) * (vmax[1] - vmin[1]) * GN_SCATTER_DENSITY),
    }


def _resolve_scatter(
    bpy: Any,
    bmesh: Any,
    data: dict[str, Any],
    material_lookup: dict[str, Any],
    source_collection: Any,
    export_collection: Any,
) -> tuple[dict[str, Any], list[Assembly]]:
    """Two GN attempts, then the Python fallback (controller ruling 3)."""
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            gn = _try_gn_scatter(bpy, bmesh, data, material_lookup, source_collection)
            export_collection.objects.link(gn.pop("object"))
            return {**gn, "attempts": attempt, "uv_exempt": True}, []
        except Exception as exc:  # pragma: no cover - exercised by the fallback smoke
            last_error = exc
            _cleanup_scatter_state(bpy)
    fallback = _python_scatter_assemblies(data)
    return {
        "method": "python-fallback",
        "attempts": 2,
        "uv_exempt": True,
        "error": f"{type(last_error).__name__}: {last_error}" if last_error else "GN construction failed twice",
        "expected_instances": round(
            (data["vacant"]["max"][0] - data["vacant"]["min"][0])
            * (data["vacant"]["max"][1] - data["vacant"]["min"][1])
            * GN_SCATTER_DENSITY
        ),
    }, fallback


# --- scene writing -------------------------------------------------------------


def _reset_scene(bpy: Any) -> None:
    for object_ in list(bpy.data.objects):
        bpy.data.objects.remove(object_, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    for group in [g for g in list(bpy.data.node_groups) if g.name.startswith("GN_Akichi")]:
        bpy.data.node_groups.remove(group)
    for mesh in [m for m in list(bpy.data.meshes) if m.users == 0]:
        bpy.data.meshes.remove(mesh)


def write_scene(sector: str, output_path: str | Path) -> dict[str, Any]:
    """Build one sector's .blend: editable source + static export collections,
    metric UVs, GN scatter (baked) and a saved/reopened verification pass."""
    if sector not in SECTORS:
        raise ValueError(f"unknown sector {sector!r}; expected one of {SECTORS}")
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".blend":
        raise ValueError("--output must be an editable .blend file path")

    import bmesh  # pylint: disable=import-outside-toplevel
    import bpy  # pylint: disable=import-outside-toplevel

    data = build_layout()
    issues = validate_layout(data)
    if issues:
        raise RuntimeError(f"layout validation failed: {issues[:4]}")

    _reset_scene(bpy)
    title = sector.capitalize()
    source_collection = bpy.data.collections.new(f"Akichi{title}")
    export_collection = bpy.data.collections.new(f"Akichi{title}Export")
    bpy.context.scene.collection.children.link(source_collection)
    bpy.context.scene.collection.children.link(export_collection)
    material_lookup = make_blender_materials()

    assemblies = build_sector_assemblies(data, sector)
    scatter_info: dict[str, Any] = {}
    if sector == "vacant":
        scatter_info, fallback_assemblies = _resolve_scatter(
            bpy, bmesh, data, material_lookup, source_collection, export_collection
        )
        assemblies = [*fallback_assemblies, *assemblies]

    report = resource_report(assemblies, sector)
    uv_issues = 0
    for assembly in assemblies:
        uv_exempt = assembly.kind == "rubble-scatter"
        for key, merged in batch_assembly(assembly).items():
            object_, issues = _create_batch_object(
                bpy, bmesh, merged, material_lookup, key, uv_exempt=uv_exempt
            )
            object_["asset_kind"] = assembly.kind
            object_["akichi_sector"] = sector
            source_collection.objects.link(object_)
            export_collection.objects.link(object_)
            uv_issues += issues

    if sector == "vacant":
        report["scatter_method"] = scatter_info["method"]
        report["scatter_info"] = {
            key: value for key, value in scatter_info.items() if key != "error"
        }
        report["gn_scatter_uv_exempt"] = scatter_info["method"] == "geometry-nodes"
        if scatter_info["method"] == "geometry-nodes":
            report["blender_object_count"] += 1
            # The baked scatter exports as one extra mesh; count its geometry in
            # the sector totals so the resource figures match the real export.
            report["total_vertices"] += scatter_info["vertices"]
            report["total_triangles"] += scatter_info["triangles"]
        else:
            report["scatter_uv_exempt"] = True
            report["scatter_info"]["error"] = scatter_info.get("error")
    report["uv_issue_count"] = uv_issues

    report_path = output_path.parent / f"{sector}-report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(output_path.resolve()))

    # Reopen verification against freshly loaded datablocks.
    reopened_export = bpy.data.collections.get(f"Akichi{title}Export")
    reopened_source = bpy.data.collections.get(f"Akichi{title}")
    if reopened_export is None or reopened_source is None:
        raise RuntimeError(f"the {title} source or export collection did not survive the reopening")
    export_objects = [obj for obj in reopened_export.objects if obj.type == "MESH"]
    if len(export_objects) != report["blender_object_count"]:
        raise RuntimeError(
            f"expected {report['blender_object_count']} export meshes, reopened {len(export_objects)}"
        )
    if any(not obj.data.uv_layers for obj in export_objects):
        raise RuntimeError("a reopened export mesh is missing UV0")
    if any(not all(poly.normal.length > 0.99 for poly in obj.data.polygons) for obj in export_objects):
        raise RuntimeError("a reopened export mesh has invalid normals")
    if sector == "vacant" and scatter_info["method"] == "geometry-nodes":
        baked = [obj for obj in export_objects if obj.get("evaluated_from_geometry_nodes")]
        if len(baked) != 1 or baked[0].modifiers or baked[0].data.name != "AkichiVacantScatter_Mesh":
            raise RuntimeError("the vacant export does not contain exactly one static baked GN scatter")
        scatter_objects = [
            obj for obj in reopened_source.objects if obj.type == "MESH" and obj.get("evaluated_from_geometry_nodes")
        ]
        gn_authoring = [
            obj for obj in reopened_source.objects
            if obj.type == "MESH" and any(mod.type == "NODES" and mod.node_group is not None for mod in obj.modifiers)
        ]
        if scatter_objects or len(gn_authoring) != 1 or gn_authoring[0].name != GN_SCATTER_PLANE:
            raise RuntimeError("the editable GN authoring plane did not survive the reopening")

    report.update(
        {
            "blend_path": str(output_path.resolve()),
            "blender_version": bpy.app.version_string,
            "reopened_export_meshes": len(export_objects),
            "source_collection": f"Akichi{title}",
            "export_collection": f"Akichi{title}Export",
        }
    )
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    """CLI entry: argparse reads options after the resoloop runner's ``--``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector", choices=SECTORS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    report = write_scene(args.sector, args.output)
    print("AKICHI_SECTOR_REPORT=" + json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()