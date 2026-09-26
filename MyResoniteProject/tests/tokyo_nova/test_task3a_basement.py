"""Offline F-1 acceptance: emitted support, full-width entry and composed clearance."""
from __future__ import annotations

import math
from collections import Counter
from typing import Any
from unittest import TestCase

from test_task3a_circulation import (
    Vec3,
    body_hits_box,
    colliders,
    line,
    scene,
    slots,
)

from modeling.tokyo_nova import pipeline

Box = tuple[str, Vec3, Vec3, list[float]]
BODY_HEIGHT = 1.88
BODY_HALF_WIDTH = .23
FOOT_ALLOWANCE = .20


def top_at(box: Box, x: float, z: float) -> float | None:
    """Intersect a vertical ray with the actual OBB's upward local-Y face."""
    _, center, size, rotation = box
    up = pipeline._rotate_vector(rotation, (0.0, 1.0, 0.0))
    if up[1] <= 0.1:
        return None
    y = center[1] + (size[1] / 2 - up[0] * (x-center[0]) - up[2] * (z-center[2])) / up[1]
    inverse = [-rotation[0], -rotation[1], -rotation[2], rotation[3]]
    local = pipeline._rotate_vector(inverse, (x-center[0], y-center[1], z-center[2]))
    if abs(local[0]) <= size[0]/2 + 1e-6 and abs(local[2]) <= size[2]/2 + 1e-6:
        return y
    return None


def descent(access: dict[str, Any], building: dict[str, Any]) -> tuple[Vec3, Vec3, Vec3]:
    x, _, z = building["center"]
    w, d = building["size"]
    outward = {"north": (0.0, 0.0, 1.0), "south": (0.0, 0.0, -1.0),
               "east": (1.0, 0.0, 0.0), "west": (-1.0, 0.0, 0.0)}[access["entry_side"]]
    start = (x + outward[0]*w/2, 0.0, z + outward[2]*d/2)
    run = access["approach_run"]
    end = (start[0]-outward[0]*run, -access["depth_below_grade"], start[2]-outward[2]*run)
    return start, end, outward


def nearby(boxes: list[Box], points: list[Vec3]) -> list[Box]:
    """Broad phase only; final blocker checks still use exact SAT."""
    margin = BODY_HALF_WIDTH + .01
    lo = [min(p[i] for p in points) - margin for i in range(3)]
    hi = [max(p[i] for p in points) + (FOOT_ALLOWANCE + BODY_HEIGHT if i == 1 else margin) for i in range(3)]
    result = []
    for box in boxes:
        _, center, size, rotation = box
        axes = [pipeline._rotate_vector(rotation, axis) for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
        extent = [sum(abs(axes[j][i])*size[j]/2 for j in range(3)) for i in range(3)]
        if all(center[i]+extent[i] >= lo[i] and center[i]-extent[i] <= hi[i] for i in range(3)):
            result.append(box)
    return result


def assert_supported_and_clear(points: list[Vec3], boxes: list[Box]) -> None:
    boxes = nearby(boxes, points)
    for point in points:
        supports = [b for b in boxes if (y := top_at(b, point[0], point[2])) is not None
                    and math.isclose(y, point[1], abs_tol=1e-5)]
        assert supports, f"no contact surface at {point}"
        # Only the sloping surface actually in contact with the foot is exempt:
        # an upright box envelope extends slightly into its uphill support.
        own_slopes = {b[0] for b in supports if b[3] != [0, 0, 0, 1]}
        # At the bar's 2.2/3 gradient, the uphill heel is 0.169m above
        # the center contact. Use 0.20m foot allowance (the shared SAT adds
        # 0.10m), retaining a 1.88m body and a stricter 2.08m head envelope.
        body_foot = (point[0], point[1]+FOOT_ALLOWANCE-.10, point[2])
        blockers = [b[0] for b in boxes if b[0] not in own_slopes and body_hits_box(body_foot, *b[1:])]
        assert not blockers, (point, blockers)


def test_top_face_detector_rejects_points_outside_a_rotated_support() -> None:
    node = pipeline._ramp_slot("probe", "probe", [0, 0, 0], [0, -2, 4], 1.5)
    box = colliders({"slot": {"key": "root"}, "children": [node]})[0]
    assert math.isclose(top_at(box, 0, 2) or 0, -1, abs_tol=1e-6)
    assert top_at(box, .751, 2) is None
    assert top_at(box, 0, 4.01) is None


def test_clearance_broad_phase_keeps_thin_obstacles_at_the_head() -> None:
    foot = (0.0, 0.0, 0.0)
    floor: Box = ("floor", (0.0, -.05, 0.0), (2.0, .1, 2.0), [0, 0, 0, 1])
    head: Box = ("head_obstacle", (0.0, 2.04, 0.0), (1.0, .04, 1.0), [0, 0, 0, 1])
    assert body_hits_box((0.0, .10, 0.0), *head[1:])
    with TestCase().assertRaisesRegex(AssertionError, "head_obstacle"):
        assert_supported_and_clear([foot], [floor, head])


def test_full_width_basement_descent_has_continuous_support_and_clearance() -> None:
    layout, _, manifest = scene()
    boxes = colliders(manifest)
    buildings = {b["key"]: b for b in layout["buildings"]}
    for access in layout["basement_access"]:
        start, end, outward = descent(access, buildings[access["building_key"]])
        transverse = (outward[2], 0.0, -outward[0])
        for offset in (-access["clear_width"]/2 + BODY_HALF_WIDTH, 0.0, access["clear_width"]/2 - BODY_HALF_WIDTH):
            lane_start = (start[0]+transverse[0]*offset, start[1], start[2]+transverse[2]*offset)
            lane_end = (end[0]+transverse[0]*offset, end[1], end[2]+transverse[2]*offset)
            approach = (lane_start[0]+outward[0]*1.1, 0.0, lane_start[2]+outward[2]*1.1)
            assert_supported_and_clear(line(approach, lane_start) + line(lane_start, lane_end), boxes)


def test_basement_descent_landing_turn_and_room_form_one_supported_route() -> None:
    layout, _, manifest = scene()
    boxes = colliders(manifest)
    nodes = slots(manifest)
    buildings = {b["key"]: b for b in layout["buildings"]}
    for access in layout["basement_access"]:
        _, end, outward = descent(access, buildings[access["building_key"]])
        x, _, z = nodes[access["landing_key"]]["slot"]["position"]
        landing = (float(x), end[1], float(z))
        # Enter the level bay before turning sideways: do not cut the corner
        # with the uphill half of the body still over the descending slope.
        turn = (min(landing[0], end[0]-.35) if outward[0] else landing[0], end[1],
                min(landing[2], end[2]-.35) if outward[2] else landing[2])
        room = (turn[0]-outward[2]*1.5, turn[1], turn[2]+outward[0]*1.5)
        assert_supported_and_clear(line(end, turn) + line(turn, room), boxes)


def test_descent_contact_faces_meet_grade_and_landing_across_the_declared_width() -> None:
    layout, _, manifest = scene()
    boxes = colliders(manifest)
    nodes = slots(manifest)
    buildings = {b["key"]: b for b in layout["buildings"]}
    for access in layout["basement_access"]:
        key = access["key"] + ("_walk_surface" if access["kind"] == "open_stairwell_and_landing" else "")
        node = nodes[key]
        component = next(c for c in node["components"] if c["type"] == "FrooxEngine.BoxCollider")
        width, thickness, length = component["fields"]["Size"]
        assert math.isclose(width, access["clear_width"], abs_tol=1e-9)
        start, end, outward = descent(access, buildings[access["building_key"]])
        for at_end, expected in ((False, start), (True, end)):
            for side in (-1, 0, 1):
                r = pipeline._rotate_vector(node["slot"]["rotation"], (side*width/2, thickness/2, (1 if at_end else -1)*length/2))
                p = tuple(node["slot"]["position"][i]+r[i] for i in range(3))
                assert math.isclose(p[1], expected[1], abs_tol=1e-6)
                assert math.isclose((p[0]-expected[0])*outward[0]+(p[2]-expected[2])*outward[2], 0, abs_tol=1e-6)
                # Inspect the other side of the seam, not the ramp supporting itself.
                qx = p[0] + outward[0]*(-.01 if at_end else .01)
                qz = p[2] + outward[2]*(-.01 if at_end else .01)
                supports = [b for b in boxes if not b[0].startswith(key+"/")
                            and (height := top_at(b, qx, qz)) is not None
                            and math.isclose(height, expected[1], abs_tol=1e-6)]
                assert supports, (key, at_end, side, p)


def test_city_refreshes_only_managed_basement_slots_from_the_north_checkpoint() -> None:
    layout, _, manifest = scene()
    city_nodes = slots(manifest)
    blockout_nodes = slots(pipeline.build_blockout_manifest(layout))
    for node in pipeline._basement_access_slots(layout):
        key = node["slot"]["key"]
        assert city_nodes[key] == blockout_nodes[key] == node


def test_native_stair_detail_is_noncolliding_over_a_hidden_continuous_slope() -> None:
    _, _, manifest = scene()
    nodes = slots(manifest)
    treads = [node for key, node in nodes.items() if key.startswith("west_bar_basement_stair_")]
    assert len(treads) == 12
    for tread in treads:
        assert not any(c["type"] == "FrooxEngine.BoxCollider" for c in tread["components"])
    ramp = nodes.get("west_bar_basement_stairs_walk_surface")
    assert ramp is not None, "bar stair detail needs a smooth continuous collision surface"
    assert [c["type"] for c in ramp["components"]] == ["FrooxEngine.BoxCollider"]


def test_composed_slot_and_component_identities_are_unique() -> None:
    _, _, manifest = scene()
    identities = [node["slot"]["key"] for node in pipeline.iter_slots(manifest)]
    identities += [c["key"] for node in pipeline.iter_slots(manifest) for c in node.get("components", [])]
    duplicates = {key: n for key, n in Counter(identities).items() if n > 1}
    assert not duplicates, duplicates


def test_structural_candidate_has_a_bounded_budget_for_its_actual_json_values() -> None:
    _, _, manifest = scene()

    def count(value: Any) -> int:
        if isinstance(value, dict):
            return 1 + sum(count(v) for v in value.values())
        if isinstance(value, list):
            return 1 + sum(count(v) for v in value)
        return 1

    # This in-memory candidate has no include/prototype expansion. Counting its
    # values is conservative; resoloop validate remains the authoritative gate.
    actual = count(manifest)
    assert actual <= manifest["limits"]["expandedNodes"] <= 70000


def test_each_emitted_storey_retains_its_own_floor_identity() -> None:
    _, city, _ = scene()
    for assembly in city["assemblies"]:
        if assembly.kind != "district_building":
            continue
        slabs = [p for p in assembly.parts if "floor_slab" in p.name]
        names = [p.name for p in slabs]
        assert len(names) == len(set(names)), assembly.name
        # The pre-existing ground-level identity must not move to an upper floor.
        ground = [p for p in slabs if "_floor_slab_0" in p.name]
        assert ground and all(max(v[1] for v in p.vertices) < .1 for p in ground)
