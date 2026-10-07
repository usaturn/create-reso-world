"""Tower assemblies from modeling/slum02/towers.py.

Covers the brief invariants: every layout tower built exactly once across the
three sectors, world-space footprint/height bounds, per-tower and total
triangle budgets, material variety, required part prefixes, window recesses,
R11 outward winding for closed parts, outward-facing facade skins and the
occluder bookkeeping used by the sightline test.
"""
import pytest

from modeling.slum02 import geometry as g
from modeling.slum02.layout import TOWER_FLOOR_H, build_layout
from modeling.slum02.towers import (
    FLOOR_H,
    SECTOR_BUILDERS,
    build_tower,
    signed_volume,
)


@pytest.fixture(scope="module")
def data():
    return build_layout()


@pytest.fixture(scope="module")
def towers(data):
    """All towers, in sector order (towers-a, towers-b, towers-c)."""
    built = []
    for sector in ("towers-a", "towers-b", "towers-c"):
        built.extend(SECTOR_BUILDERS[sector](data))
    return built


def test_three_sector_builders_cover_every_tower_once(data, towers):
    assert set(SECTOR_BUILDERS) == {"towers-a", "towers-b", "towers-c"}
    ids = [a.name for a in towers]
    assert sorted(ids) == sorted(t["id"] for t in data["towers"])
    assert len(ids) == len(set(ids))
    for a in towers:
        spec = next(t for t in data["towers"] if t["id"] == a.name)
        assert a.sector == spec["sector"]
        assert a.kind == "tower"
        # origin is the footprint centre at ground level
        assert a.origin == pytest.approx((spec["center"][0], 0.0, spec["center"][1]))


def test_tower_stays_near_footprint_and_height(data, towers):
    # parts are local (yaw baked in); the rotated plan stays inside footprint + 2 m
    # of additions allowance on every side.
    for a in towers:
        spec = next(t for t in data["towers"] if t["id"] == a.name)
        lo, hi = g.bounds(a.parts)
        assert lo[1] >= -0.05, a.name                     # nothing sinks into the ground blocks
        assert hi[1] <= spec["height"] + 7.0, a.name      # parapet/tank/antenna allowance
        w, d = spec["footprint"]
        reach = max(w, d) / 2 + 2.0
        assert max(hi[0], hi[2], -lo[0], -lo[2]) <= reach, (a.name, lo, hi)


def test_tower_triangle_budget(data, towers):
    total = 0
    for a in towers:
        tris = sum(g.triangle_count(p) for p in a.parts)
        assert 3000 <= tris <= 26000, (a.name, tris)
        total += tris
    assert total <= 300000, total


def test_tower_material_variety(data, towers):
    for a in towers:
        mats = {p.material for p in a.parts}
        assert 5 <= len(mats) <= 13, (a.name, sorted(mats))


def test_required_part_prefixes(data, towers):
    required = ("facade", "fin", "slab", "pane", "ac", "drain", "roof")
    for a in towers:
        names = {p.name.split("-")[0] for p in a.parts}
        for prefix in required:
            assert prefix in names, (a.name, prefix, sorted(names))


def test_windows_are_recesses_not_holes(towers):
    # A windowless wall would be a bare grid; deep reveals multiply the face count.
    a = next(t for t in towers if t.name == "tower-05")
    front = next(p for p in a.parts if p.name == "facade-front")
    assert len(front.faces) > 50
    # openings are blind: every facade vertex stays within the wall thickness
    zs = [v[2] for v in front.vertices]
    assert max(zs) - min(zs) <= 0.5 + 1e-6


def test_closed_parts_have_positive_signed_volume(towers):
    """R11: closed shells (everything but the open facade skins) are outward/CCW."""
    open_prefixes = ("facade",)  # wall_with_openings(closed=False) skins
    for a in towers:
        for p in a.parts:
            if p.name.split("-")[0] in open_prefixes:
                continue
            assert signed_volume(p) > -1e-6, (a.name, p.name, signed_volume(p))


def test_facade_skins_face_outward(towers):
    """Each wall band must read from outside the tower, not through the interior.

    The four facade walls wrap an axis-aligned box before the spec yaw is baked
    in, so for the (axis-aligned) outer towers the dominant normal of each wall
    points along a world axis; collapsed panels keep the same facing.
    """
    a = next(t for t in towers if t.name == "tower-05")  # outer, faces -z (north side)
    expected = {"facade-front": (0, 0, -1), "facade-back": (0, 0, 1),
                "facade-left": (1, 0, 0), "facade-right": (-1, 0, 0)}
    for name, want in expected.items():
        wall = next(p for p in a.parts if p.name == name)
        nx = ny = nz = 0.0
        for f in wall.faces:
            pts = [wall.vertices[i] for i in f]
            # raw Newell sum: direction * (2 x area), so the accumulation is area weighted
            for u, v in zip(pts, (*pts[1:], pts[0])):
                nx += (u[1] - v[1]) * (u[2] + v[2])
                ny += (u[2] - v[2]) * (u[0] + v[0])
                nz += (u[0] - v[0]) * (u[1] + v[1])
        n = (nx, ny, nz)
        dot = sum(n[i] * want[i] for i in range(3))
        axis = next(i for i in range(3) if want[i] != 0)
        assert dot > 0 and abs(n[axis]) == max(abs(c) for c in n), (name, n)


def _facade_planes(a):
    """(unit outward normal, exterior plane offset) per facade side of one tower.

    The dominant Newell normal of each wall skin is the outward direction; the
    exterior surface is the maximum vertex projection onto it.
    """
    planes = {}
    for side in ("front", "back", "left", "right"):
        wall = next(p for p in a.parts if p.name == f"facade-{side}")
        nx = ny = nz = 0.0
        for f in wall.faces:
            pts = [wall.vertices[i] for i in f]
            for u, v in zip(pts, (*pts[1:], pts[0])):
                nx += (u[1] - v[1]) * (u[2] + v[2])
                ny += (u[2] - v[2]) * (u[0] + v[0])
                nz += (u[0] - v[0]) * (u[1] + v[1])
        n = g.norm((nx, ny, nz))
        planes[side] = (n, max(g.dot(v, n) for v in wall.vertices))
    return planes


def _projected(part, planes, side):
    n, off = planes[side]
    return max(g.dot(v, n) for v in part.vertices) - off


def test_facade_additions_protrude_past_the_wall(towers):
    """Measured projection: fins ~0.35 m, slab lips 0.2 m, AC units ~0.3 m.

    Regression for fix round 1: these parts used to be positioned relative to
    the wall centre, so WALL_T / 2 was silently embedded and AC units floated
    half-buried. Measure every face on every tower.
    """
    letter = {"f": "front", "b": "back", "l": "left", "r": "right"}
    ac_sides = set()
    for a in towers:
        planes = _facade_planes(a)
        fin_sides, lip_sides = set(), set()
        for p in a.parts:
            if p.name.startswith("fin-"):
                side = letter[p.name.split("-")[1][0]]
                fin_sides.add(side)
                assert _projected(p, planes, side) == pytest.approx(0.35, abs=0.02), (a.name, p.name)
            elif p.name.startswith("slab-lip-"):
                side = letter[p.name.split("-")[2][0]]
                lip_sides.add(side)
                assert _projected(p, planes, side) == pytest.approx(0.20, abs=0.02), (a.name, p.name)
        # every tower keeps fins and lips on all four facades
        assert fin_sides == {"front", "back", "left", "right"}, (a.name, fin_sides)
        assert lip_sides == {"front", "back", "left", "right"}, (a.name, lip_sides)
        # AC units: combined mesh on front + both sides, never on the back
        ac = next(p for p in a.parts if p.name == "ac-00")
        for side in ("front", "left", "right"):
            proj = _projected(ac, planes, side)
            if proj > 0.02:                      # this face actually carries units
                ac_sides.add(side)
                assert 0.30 <= proj <= 0.37, (a.name, side, proj)
        assert _projected(ac, planes, "back") <= 0.02, a.name
    assert ac_sides == {"front", "left", "right"}   # placement covers all intended faces


def test_outer_towers_expose_occluder(data, towers):
    for a in towers:
        spec = next(t for t in data["towers"] if t["id"] == a.name)
        if spec["role"] == "outer":
            assert a.meta["occludes"] == [f"occ-{a.name}"]
        else:
            assert "occludes" not in a.meta
    # and every occluder id points at an existing occluder box in the layout
    occluder_ids = {o["id"] for o in data["occluders"]}
    for a in towers:
        for occ in a.meta.get("occludes", []):
            assert occ in occluder_ids


def test_outer_tower_facades_cover_occluder(data, towers):
    """Sightline occluders assume the tower skin really spans its footprint."""
    occ = {o["id"]: o for o in data["occluders"]}
    for a in towers:
        spec = next(t for t in data["towers"] if t["id"] == a.name)
        if spec["role"] != "outer":
            continue
        box = occ[f"occ-{a.name}"]
        (ox0, _, oz0), (ox1, _, oz1) = box["min"], box["max"]
        ox, _oy, oz = a.origin
        facades = [p for p in a.parts if p.name.startswith("facade")]
        lo, hi = g.bounds(facades)
        assert lo[0] + ox <= ox0 + 1e-2 and hi[0] + ox >= ox1 - 1e-2, a.name
        assert lo[2] + oz <= oz0 + 1e-2 and hi[2] + oz >= oz1 - 1e-2, a.name
        assert hi[1] >= spec["core_height"] - 0.1, a.name  # walls survive to the core


def test_floor_height_matches_layout():
    # towers は崩落後の壁の上端を height - collapse * FLOOR_H とし、layout の
    # core_height（height - collapse * TOWER_FLOOR_H - 0.5）より 0.5 m 上にある前提で組む。
    # 階高が食い違うと、崩落部と遮蔽ボックスの高さがずれる。
    assert FLOOR_H == TOWER_FLOOR_H


def test_deterministic_rebuild(data):
    t = data["towers"][7]
    a, b = build_tower(t), build_tower(t)
    for pa, pb in zip(a.parts, b.parts):
        assert pa.name == pb.name and pa.vertices == pb.vertices and pa.faces == pb.faces


def test_sprays_present_and_bounded(data, towers):
    for a in towers:
        sprays = a.meta.get("sprays", [])
        spec = next(t for t in data["towers"] if t["id"] == a.name)
        assert 3 <= len([s for s in sprays if s.color != (0.9, 0.6, 0.45)]) + 1  # graffiti-ish sprays exist
        assert any(abs(s.strength - 0.5) < 1e-6 and s.color == (0.9, 0.6, 0.45) for s in sprays), a.name
        cx, cz = spec["center"]
        reach = max(spec["footprint"]) / 2 + 0.6      # spray origins stay on/just outside the skin
        for s in sprays:
            assert abs(s.center[0] - cx) <= reach and abs(s.center[2] - cz) <= reach, (a.name, s.center)


def test_collapse_parts_only_when_requested(data, towers):
    for a in towers:
        spec = next(t for t in data["towers"] if t["id"] == a.name)
        collapse_parts = [p.name for p in a.parts if p.name.startswith("collapse")]
        if spec["collapse"] == 0:
            assert collapse_parts == []
        else:
            # torn slabs + rebar + broken edges per collapsed floor
            floors = {p.name.rsplit("-", 1)[-1] for p in a.parts if p.name.startswith("collapse-slab")}
            assert len(floors) >= spec["collapse"]
            lo, hi = g.bounds([p for p in a.parts if p.name.startswith("collapse")])
            assert lo[1] >= spec["core_height"] - 0.2, a.name   # damage stays above the core
