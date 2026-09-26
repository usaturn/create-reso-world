"""Task3A: check emitted surfaces and composed collisions, not access flags.

A 0.46m-wide, 1.88m-high standing envelope is structural evidence only.
It is not a substitute for an actual VR traversal test.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from modeling.tokyo_nova import build, pipeline
from modeling.tokyo_nova.layout import build_layout

Vec3 = tuple[float, float, float]


@lru_cache(maxsize=1)
def scene() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    layout = build_layout()
    city = build.build_city(layout)
    return layout, city, pipeline.build_city_manifest(layout, city)


def slots(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["slot"]["key"]: node for node in pipeline.iter_slots(manifest)}


def box_size(node: dict[str, Any]) -> Vec3:
    fields = next(c["fields"] for c in node["components"] if c["type"] == "FrooxEngine.BoxMesh")
    x, y, z = fields["Size"]
    return float(x), float(y), float(z)


def surface_end(node: dict[str, Any], end: bool) -> Vec3:
    _, thickness, length = box_size(node)
    local = (0.0, thickness / 2, (1 if end else -1) * length / 2)
    rotated = pipeline._rotate_vector(node["slot"]["rotation"], local)
    x, y, z = (node["slot"]["position"][i] + rotated[i] for i in range(3))
    return x, y, z


def bounds(vertices: list[Vec3]) -> tuple[Vec3, Vec3]:
    lo = tuple(min(v[i] for v in vertices) for i in range(3))
    hi = tuple(max(v[i] for v in vertices) for i in range(3))
    return (lo[0], lo[1], lo[2]), (hi[0], hi[1], hi[2])


def dot(a: Vec3, b: Vec3) -> float:
    return sum(a[i] * b[i] for i in range(3))


def cross(a: Vec3, b: Vec3) -> Vec3:
    return a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]


def body_hits_box(foot: Vec3, center: Vec3, size: Vec3, rotation: list[float]) -> bool:
    """Exact AABB/OBB separating-axis test (no sloping-ramp AABB false positives)."""
    body_center = (foot[0], foot[1] + 0.94 + 0.10, foot[2])
    body_half = (0.23, 0.94, 0.23)
    basis: tuple[Vec3, ...] = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    oriented = tuple(pipeline._rotate_vector(rotation, axis) for axis in basis)
    delta = (center[0]-body_center[0], center[1]-body_center[1], center[2]-body_center[2])
    for axis in (*basis, *oriented, *(cross(a, b) for a in basis for b in oriented)):
        if dot(axis, axis) < 1e-12:
            continue
        body_radius = sum(body_half[i] * abs(axis[i]) for i in range(3))
        box_radius = sum(size[i] / 2 * abs(dot(oriented[i], axis)) for i in range(3))
        if abs(dot(delta, axis)) >= body_radius + box_radius - 1e-6:
            return False
    return True


def colliders(manifest: dict[str, Any]) -> list[tuple[str, Vec3, Vec3, list[float]]]:
    """Compose hierarchy by transforming a collider's center and three edge vectors."""
    result = []

    def walk(node: dict[str, Any], ancestors: list[dict[str, Any]], active: bool) -> None:
        slot = node["slot"]
        active = active and slot.get("active", True)
        chain = ancestors if slot["key"] == "root" else [slot, *ancestors]

        def transform(point: Vec3) -> Vec3:
            for parent in chain:
                scale = parent.get("scale", [1, 1, 1])
                x, y, z = (point[i] * scale[i] for i in range(3))
                r = pipeline._rotate_vector(parent.get("rotation", [0, 0, 0, 1]), (x, y, z))
                p = parent.get("position", [0, 0, 0])
                point = r[0]+p[0], r[1]+p[1], r[2]+p[2]
            return point

        # Current content has axis-aligned ancestors; assert this instead of silently
        # dropping a future rotated ancestor (native ramps carry their own rotation).
        for parent in ancestors:
            assert parent.get("rotation", [0, 0, 0, 1]) == [0, 0, 0, 1]
            assert parent.get("scale", [1, 1, 1]) == [1, 1, 1]
        for component in node.get("components", []):
            f = component.get("fields", {})
            if not active or component["type"] != "FrooxEngine.BoxCollider" or not f.get("Enabled", True):
                continue
            offset = f.get("Offset", [0, 0, 0])
            center = transform((offset[0], offset[1], offset[2]))
            scale = slot.get("scale", [1, 1, 1])
            size = tuple(float(f["Size"][i]) * scale[i] for i in range(3))
            result.append((slot["key"] + "/" + component["key"], center, (size[0], size[1], size[2]), slot.get("rotation", [0, 0, 0, 1])))
        for child in node.get("children", []):
            walk(child, chain, active)

    walk(manifest, [], True)
    return result


def line(start: Vec3, end: Vec3, spacing: float = 0.10) -> list[Vec3]:
    count = max(1, math.ceil(math.dist(start, end) / spacing))
    return [(start[0]+(end[0]-start[0])*i/count,
             start[1]+(end[1]-start[1])*i/count,
             start[2]+(end[2]-start[2])*i/count) for i in range(count+1)]


def test_roof_flights_meet_the_platform_boundary_not_its_middle() -> None:
    layout, _, manifest = scene()
    nodes = slots(manifest)
    route = layout["roof_access"]
    for turn in (0, 1):
        landing = nodes[route["turn_landings"][turn]["key"]]
        px, py, pz = landing["slot"]["position"]
        width, thickness, depth = box_size(landing)
        for flight_index, at_end in ((turn, True), (turn+1, False)):
            point = surface_end(nodes[route["flights"][flight_index]["key"]], at_end)
            assert math.isclose(point[1], py + thickness/2, abs_tol=1e-6)
            edge_distance = min(abs(abs(point[0]-px)-width/2), abs(abs(point[2]-pz)-depth/2))
            assert edge_distance < 0.005, f"flight endpoint {point} is inside platform rather than at its edge"


def test_roof_body_path_clears_all_composed_colliders_including_turn_rails() -> None:
    layout, _, manifest = scene()
    nodes = slots(manifest)
    route = layout["roof_access"]
    samples: list[Vec3] = []
    for i, flight in enumerate(route["flights"]):
        start, end = surface_end(nodes[flight["key"]], False), surface_end(nodes[flight["key"]], True)
        samples.extend(line(start, end))
        if i < len(route["turn_landings"]):
            center = route["turn_landings"][i]["center"]
            following = surface_end(nodes[route["flights"][i+1]["key"]], False)
            # Go into the level turning bay before crossing the divider between flights.
            bend1 = (float(center[0]), end[1], end[2])
            bend2 = (float(center[0]), following[1], following[2])
            samples.extend(line(end, bend1) + line(bend1, bend2) + line(bend2, following))
        else:
            samples.extend(line(end, (end[0]+1.0, end[1], end[2])))
    obstacles = colliders(manifest)
    hits = [(p, key) for p in samples for key, center, size, rotation in obstacles if body_hits_box(p, center, size, rotation)]
    assert not hits, f"roof walking envelope hits composed geometry: {hits[:8]}"


def test_basement_transitions_have_floor_support_and_body_clearance() -> None:
    layout, city, manifest = scene()
    nodes = slots(manifest)
    obstacles = colliders(manifest)
    for access in layout["basement_access"]:
        room = next(a for a in city["assemblies"] if a.kind == "interior_room" and a.name == access["building_key"])
        floor_bounds = [bounds(p.vertices) for p in room.transformed_parts() if "room_floor" in p.name]
        landing = nodes[access["landing_key"]]
        x, y, z = landing["slot"]["position"]
        sx, sy, sz = box_size(landing)
        floor_y = y + sy/2
        assert all(math.isclose(hi[1], floor_y, abs_tol=1e-6) for _, hi in floor_bounds)
        # Traverse from the bottom landing into the room around the floor opening.
        start = (float(x), floor_y, float(z))
        end = (float(x)-1.5, floor_y, float(z)) if access["entry_side"] == "north" else (float(x), floor_y, float(z)+1.5)
        surfaces = [*floor_bounds, ((x-sx/2, y-sy/2, z-sz/2), (x+sx/2, y+sy/2, z+sz/2))]
        for point in line(start, end):
            assert any(lo[0]-1e-6 <= point[0] <= hi[0]+1e-6 and lo[2]-1e-6 <= point[2] <= hi[2]+1e-6 for lo, hi in surfaces)
            # The uphill side of the standing foot envelope intersects its own
            # slope at this exact contact seam; do not treat that support as a wall.
            supporting_ramp = access["key"] + "/" + access["key"] + "_collider"
            blockers = [key for key, center, size, rot in obstacles
                        if key != supporting_ramp and body_hits_box(point, center, size, rot)]
            assert not blockers, (access["key"], point, blockers)


def test_roof_guard_colliders_include_the_visible_balusters() -> None:
    layout, city, manifest = scene()
    owner = layout["roof_access"]["building_key"]
    roof = next(a for a in city["assemblies"] if a.name == owner)
    guard_names = {p.name for p in roof.parts if "_roof_baluster_" in p.name}
    collider_keys = {c["key"] for node in pipeline.iter_slots(manifest) for c in node.get("components", []) if c["type"] == "FrooxEngine.BoxCollider"}
    missing = [name for name in guard_names if not any(name in key for key in collider_keys)]
    assert not missing, f"visible vertical roof guards lack collision: {missing[:8]}"


def test_entire_flight_width_meets_the_platform_and_roof_edge_planes() -> None:
    layout, city, manifest = scene()
    nodes = slots(manifest)
    route = layout["roof_access"]
    for i, flight in enumerate(route["flights"]):
        node = nodes[flight["key"]]
        end = surface_end(node, True)
        width = box_size(node)[0]
        right = pipeline._rotate_vector(node["slot"]["rotation"], (width/2, 0.0, 0.0))
        if i < len(route["turn_landings"]):
            platform = nodes[route["turn_landings"][i]["key"]]
            px = platform["slot"]["position"][0]
            edge_x = px + (-1 if i == 0 else 1) * box_size(platform)[0]/2
        else:
            edge_x = city["building_geometry"][route["building_key"]]["roof_slab_bounds"][0][0]
        for side in (-1, 1):
            assert math.isclose(end[0] + side*right[0], edge_x, abs_tol=1e-5), (
                "oblique rectangular flight leaves a triangular gap/overlap at the flat landing", flight["key"])


def test_clearance_detector_distinguishes_oriented_boxes_and_low_headers() -> None:
    assert body_hits_box((0, 0, 0), (0, 1.2, 0), (2, .1, .1), [0, 0, 0, 1])
    assert not body_hits_box((0, 0, 0), (0, -.1, 0), (2, .2, 2), [0, 0, 0, 1])
    rotation = pipeline._gravity_up_ramp_rotation((10, 2, 0))
    assert not body_hits_box((0, 0, 0), (0, -.2, 0), (1.8, .16, 10), list(rotation))


def test_roof_perimeter_is_guarded_except_for_the_authored_entry() -> None:
    layout, city, manifest = scene()
    record = city["building_geometry"][layout["roof_access"]["building_key"]]
    low, high = record["roof_slab_bounds"]
    entry_z = record["roof_entry_point"][2]
    opening_half = record["roof_entry_clear_width"]/2
    guards = [(key, center, size, rot) for key, center, size, rot in colliders(manifest)
              if "city_collision_building_west_roof_access/" in key
              and ("_roof_rail_" in key or "_roof_baluster_" in key)]
    for side, start, end in (
        ("west", (low[0], high[1], low[2]), (low[0], high[1], high[2])),
        ("east", (high[0], high[1], low[2]), (high[0], high[1], high[2])),
        ("south", (low[0], high[1], low[2]), (high[0], high[1], low[2])),
        ("north", (low[0], high[1], high[2]), (high[0], high[1], high[2])),
    ):
        for point in line(start, end):
            if side == "west" and abs(point[2]-entry_z) < opening_half:
                continue
            assert any(body_hits_box(point, center, size, rot) for _, center, size, rot in guards), (side, point)


def test_composition_preserves_owned_root_and_existing_north_groups() -> None:
    import json
    from pathlib import Path

    _, _, manifest = scene()
    base = json.loads(Path("content/tokyo-nova/north/north-apply.json").read_text())
    assert manifest["ownership"] == base["ownership"]
    assert manifest["slot"] == base["slot"]
    actual = slots(manifest)
    for node in base["children"]:
        key = node["slot"]["key"]
        if key.startswith("north_"):
            assert actual[key] == node, key
    assert manifest["assets"] == base["assets"]
