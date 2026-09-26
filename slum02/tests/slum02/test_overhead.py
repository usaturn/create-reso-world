import math

import pytest

from modeling.slum02 import geometry as g
from modeling.slum02 import overhead
from modeling.slum02 import layout as L
from modeling.slum02.layout import build_layout


def test_cable_endpoints_match_layout():
    data = build_layout()
    built = {a.name: a for a in overhead.overhead_assemblies(data)}
    for c in data["cables"]:
        a = built[c["id"].replace("cable", "cables")]
        pts = [v for p in a.parts if p.name.startswith("wire-") for v in g.transformed(p, 0, a.origin).vertices]
        near_a = min(math.dist(v, c["a"]) for v in pts)
        near_b = min(math.dist(v, c["b"]) for v in pts)
        assert near_a < 0.08 and near_b < 0.08, c["id"]


def test_budget():
    tris = sum(g.triangle_count(p) for a in overhead.overhead_assemblies(build_layout()) for p in a.parts)
    assert tris <= 60_000


# --------------------------------------------------------------------------- extra invariants

TOL = 1e-6
WIRE_SIDES = 6          # 6角断面 (brief)
WIRE_SPAN = 16          # 16分割カテナリー


@pytest.fixture(scope="module")
def data():
    return build_layout()


@pytest.fixture(scope="module")
def built(data):
    return overhead.overhead_assemblies(data)


@pytest.fixture(scope="module")
def by_name(built):
    return {a.name: a for a in built}


def _closed_consistent(mesh):
    directed = set()
    for face in mesh.faces:
        for x, y in zip(face, (*face[1:], face[0])):
            if (x, y) in directed:
                return False
            directed.add((x, y))
    return all((y, x) in directed for x, y in directed)


def _ring_centres(part, sides=WIRE_SIDES):
    """Centre of each tube ring (verts are emitted ring-major)."""
    return [tuple(sum(v[i] for v in part.vertices[k * sides:(k + 1) * sides]) / sides for i in range(3))
            for k in range(len(part.vertices) // sides)]


def _measured_sag(part):
    """Largest drop of the tube's ring centres below the endpoint chord."""
    centres = _ring_centres(part)
    a, b = centres[0], centres[-1]
    n = len(centres) - 1
    return max((a[1] + (b[1] - a[1]) * k / n) - c[1] for k, c in enumerate(centres))


def test_names_kinds_sector_and_counts(data, built):
    cables = [f"cables-{k:02d}" for k in range(1, len(data["cables"]) + 1)]
    bridges = [f"bridge-{k:02d}" for k in range(1, len(data["bridges"]) + 1)]
    expected = cables + bridges + [f"hangings-{k:02d}" for k in range(1, 7)] + [f"trash-{k:02d}" for k in range(1, 9)]
    assert [a.name for a in built] == expected
    for a in built:
        assert a.sector == "overhead"
        assert a.kind == {"cables": "cable", "bridge": "bridge",
                          "hangings": "hanging", "trash": "trash"}[a.name.split("-")[0]]


def test_determinism(built):
    again = overhead.overhead_assemblies(build_layout())
    assert [(a.name, [(p.name, p.vertices, p.material) for p in a.parts]) for a in again] == \
           [(a.name, [(p.name, p.vertices, p.material) for p in a.parts]) for a in built]


def test_every_part_is_a_closed_outward_shell(built):
    """R11: no normal recalculation in Blender, so every part is a closed outward shell."""
    for a in built:
        for part in a.parts:
            assert _closed_consistent(part), (a.name, part.name)
            assert g.signed_volume(part) > 0, (a.name, part.name)


def test_polygons_are_planar_for_metric_uvs(built):
    for a in built:
        for part in a.parts:
            for face in part.faces:
                if len(face) == 3:
                    continue
                pts = [part.vertices[i] for i in face]
                n = g.face_normal(pts)
                c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
                assert max(abs(sum((p[k] - c[k]) * n[k] for k in range(3))) for p in pts) < 1e-5, (a.name, part.name)


# --------------------------------------------------------------------------- cables


def test_wire_bundle_geometry(data, by_name):
    """3-6 wires per cable; 6-sided tube, 16-span catenary, radius 0.012-0.03, sag +-20%."""
    for spec in data["cables"]:
        a = by_name[spec["id"].replace("cable", "cables")]
        wires = [p for p in a.parts if p.name.startswith("wire-")]
        assert 3 <= len(wires) <= 6, a.name
        sags = []
        for w in wires:
            assert w.material == "rubber"
            assert len(w.vertices) % WIRE_SIDES == 0 and len(w.vertices) // WIRE_SIDES == WIRE_SPAN + 1, (a.name, w.name)
            centre = _ring_centres(w)[0]
            radius = math.dist(w.vertices[0], centre)
            assert 0.012 - TOL <= radius <= 0.03 + TOL, (a.name, w.name, radius)
            sags.append(_measured_sag(w))
        # sag variance: every wire within +-20% of the layout sag, not all identical
        for s in sags:
            assert spec["sag"] * 0.8 - 0.01 <= s <= spec["sag"] * 1.2 + 0.01, (a.name, s, spec["sag"])
        assert len({round(s, 3) for s in sags}) >= 2, a.name


def test_insulators_and_brackets_at_both_ends(data, by_name):
    for spec in data["cables"]:
        a = by_name[spec["id"].replace("cable", "cables")]
        for end, key in (("a", "a"), ("b", "b")):
            insulator = [p for p in a.parts if p.name == f"insulator-{end}"]
            bracket = [p for p in a.parts if p.name == f"bracket-{end}"]
            assert insulator and bracket, (a.name, end)
            lo, hi = g.bounds(insulator)
            centre = [(lo[i] + hi[i]) / 2 for i in range(3)]
            assert math.dist(centre, spec[key]) < 0.4, (a.name, end)


def test_cables_attach_to_real_mounts(data, by_name):
    mounts = {x["id"]: x for grp in ("towers", "stalls", "clubs", "shacks") for x in data[grp]}
    for spec in data["cables"]:
        a = by_name[spec["id"].replace("cable", "cables")]
        assert a.meta["attach"] == spec["attach"]
        for item_id, p in zip(spec["attach"], (spec["a"], spec["b"])):
            assert L._on_surface(mounts[item_id], p), (spec["id"], item_id)


# --------------------------------------------------------------------------- bridges


def test_bridge_rails_roof_ratio_and_occludes(data, by_name):
    """Pipe rails both sides on every bridge; exactly 50% carry a corrugated roof."""
    occ = {o["id"]: o for o in data["occluders"]}
    roofed = 0
    for spec in data["bridges"]:
        a = by_name[spec["id"]]
        assert a.kind == "bridge" and a.meta["occludes"] == [f"occ-{spec['id']}"]
        deck = [p for p in a.parts if p.name == "deck"]
        assert deck and deck[0].material == "steel_dark"
        top = g.bounds(deck)[1][1]
        assert abs(top - spec["y"]) < 0.02, a.name            # deck surface at spec y
        for side in ("l", "r"):
            rails = [p for p in a.parts if p.name == f"rail-top-{side}"]
            assert rails and rails[0].material == "steel_bare", (a.name, side)
            assert [p for p in a.parts if p.name.startswith(f"post-{side}-")], (a.name, side)
        roof = [p for p in a.parts if p.name == "roof"]
        if roof:
            roofed += 1
            assert roof[0].material == "corrugated"
            assert g.bounds(roof)[0][1] > spec["y"] + 1.5, a.name   # roof clears the railing
        # world AABB of the union of parts contains the occluder box (+-0.05)
        lo, hi = g.bounds([g.transformed(p, 0.0, a.origin) for p in a.parts])
        box = occ[f"occ-{spec['id']}"]
        assert all(lo[i] <= box["min"][i] + 0.05 for i in range(3)), (a.name, lo, box["min"])
        assert all(hi[i] >= box["max"][i] - 0.05 for i in range(3)), (a.name, hi, box["max"])
    assert roofed == len(data["bridges"]) // 2


def test_bridge_tarp_hangs_below_rail(data, by_name):
    for spec in data["bridges"]:
        a = by_name[spec["id"]]
        tarp = [p for p in a.parts if p.name.startswith("tarp")]
        assert tarp and tarp[0].material.startswith("tarp_"), a.name
        lo, hi = g.bounds(tarp)
        assert spec["y"] < hi[1] <= spec["y"] + 1.1, a.name          # tied off near the top rail
        assert lo[1] < spec["y"] + 0.4, a.name                       # and it drapes down


# --------------------------------------------------------------------------- hangings


def test_hangings_anchored_to_walls_over_alleys(data, by_name):
    """6 sets; each anchors on real wall/roof surfaces and hangs above a street."""
    mounts = {x["id"]: x for grp in ("towers", "stalls", "clubs", "shacks") for x in data[grp]}
    rects = [(s["min"][0], s["min"][1], s["max"][0], s["max"][1]) for s in data["streets"]]
    seen = set()
    for k in range(1, 7):
        a = by_name[f"hangings-{k:02d}"]
        assert a.kind == "hanging"
        attach = a.meta["attach"]
        assert attach and all(i in mounts for i in attach), (a.name, attach)
        seen.add(a.meta["kind"])
        for p, item_id in zip(a.meta["anchors"], attach):
            assert L._on_surface(mounts[item_id], p), (a.name, item_id, p)
        mid = [(a.meta["anchors"][0][i] + a.meta["anchors"][-1][i]) / 2 for i in range(3)]
        assert any(r[0] - 0.6 <= mid[0] <= r[2] + 0.6 and r[1] - 0.6 <= mid[2] <= r[3] + 0.6 for r in rects), a.name
        if a.meta["kind"] == "laundry":
            line = [p for p in a.parts if p.name == "line"]
            assert line, a.name
            cloths = [p for p in a.parts if p.name.startswith(("cloth", "banner"))]
            assert len(cloths) >= 2, a.name
            for c in cloths:                                               # hung pieces stay off heads
                assert g.bounds([c])[0][1] > 1.2, (a.name, c.name)
        else:
            assert [p for p in a.parts if p.name == "sign-board"], a.name
    assert seen == {"laundry", "sign"}


# --------------------------------------------------------------------------- trash


def test_trash_inside_street_edges_and_grounded(data, by_name):
    rects = {s["id"]: (s["min"][0], s["min"][1], s["max"][0], s["max"][1]) for s in data["streets"]}
    materials = set()
    for k in range(1, 9):
        a = by_name[f"trash-{k:02d}"]
        assert a.kind == "trash" and len(a.parts) >= 2
        lo, hi = g.bounds([g.transformed(p, 0.0, a.origin) for p in a.parts])
        assert -0.02 <= lo[1] <= 0.05, (a.name, lo[1])                       # sits on the road surface
        r = rects[a.meta["street"]]
        assert r[0] - 0.01 <= lo[0] and hi[0] <= r[2] + 0.01, (a.name, "x")
        assert r[1] - 0.01 <= lo[2] and hi[2] <= r[3] + 0.01, (a.name, "z")
        edge = min(lo[0] - r[0], r[2] - hi[0], lo[2] - r[1], r[3] - hi[2])
        assert edge <= 1.5, (a.name, edge)                                   # hugging a kerb, not mid-road
        materials.update(p.material for p in a.parts)
    assert {"rubber", "plywood", "plastic_crate"} <= materials               # 袋・段ボール・発泡箱


def test_sector_registration(data, built):
    from modeling.slum02.sectors import sector_assemblies
    assert [x.name for x in sector_assemblies(data, "overhead")] == [a.name for a in built]
