import math

import pytest

from modeling.slum02 import geometry as g
from modeling.slum02 import stalls
from modeling.slum02.layout import _aabb, _street_rect, build_layout


def test_stall_contents_and_scale():
    for spec in build_layout()["stalls"]:
        a = stalls.build_stall(spec)
        goods = [p for p in a.parts if p.name.startswith("goods-")]
        assert len(goods) >= 12, spec["id"]
        counter = [p for p in a.parts if p.name.startswith("counter-top")]
        assert counter and abs(g.bounds(counter)[1][1] - 0.9) < 0.08
        roof_lo, roof_hi = g.bounds([p for p in a.parts if p.name.startswith("roof-")])
        assert 2.3 <= roof_hi[1] <= 3.1
        mats = {p.material for p in a.parts}
        assert "warm_bulb" in mats and "electronics" in mats
        assert "sign_anchor" in a.meta
        tris = sum(g.triangle_count(p) for p in a.parts)
        assert 1500 <= tris <= 7000, (spec["id"], tris)


# --------------------------------------------------------------------------- extra invariants


def _closed_consistent(mesh):
    directed = set()
    for face in mesh.faces:
        for a, b in zip(face, (*face[1:], face[0])):
            if (a, b) in directed:
                return False
            directed.add((a, b))
    return all((b, a) in directed for a, b in directed)


@pytest.fixture(scope="module")
def market():
    return stalls.market_assemblies(build_layout())


def test_names_ids_and_origin(market):
    data = build_layout()
    stall_ids = [a.name for a in market if a.kind == "stall"]
    assert stall_ids == [s["id"] for s in data["stalls"]]
    assert [a.name for a in market if a.kind == "junk-pile"] == [f"junk-{k:02d}" for k in range(1, 7)]
    for a in market:
        assert a.sector == "market"
    for spec in data["stalls"]:
        a = stalls.build_stall(spec)
        assert a.origin == pytest.approx((spec["center"][0], 0.0, spec["center"][1]))


def test_every_part_is_a_closed_outward_shell(market):
    """R11: no normal recalculation in Blender, so every part (tarp and signs included) is closed and outward."""
    for a in market:
        for part in a.parts:
            assert _closed_consistent(part), (a.name, part.name)
            assert g.signed_volume(part) > 0, (a.name, part.name)


def test_polygons_are_planar_for_metric_uvs(market):
    for a in market:
        for part in a.parts:
            for face in part.faces:
                if len(face) == 3:
                    continue
                pts = [part.vertices[i] for i in face]
                n = g.face_normal(pts)
                c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
                assert max(abs(sum((p[k] - c[k]) * n[k] for k in range(3))) for p in pts) < 1e-5, (a.name, part.name)


def test_roof_eave_overhangs_lane_at_most_40cm_and_stall_stays_on_its_plot():
    data = build_layout()
    lane = next(s for s in data["streets"] if s["kind"] == "lane")
    for spec in data["stalls"]:
        a = stalls.build_stall(spec)
        world = [g.transformed(p, 0.0, a.origin) for p in a.parts]
        lo, hi = g.bounds(world)
        x0, z0, x1, z1 = _aabb(spec)
        # nothing sinks into the ground; only the roof may leave the plot, and only towards the lane
        assert lo[1] >= -0.02, spec["id"]
        assert lo[0] >= x0 - 0.45 and hi[0] <= x1 + 0.45, spec["id"]
        if spec["front"] == "-z":
            assert hi[2] <= z1 + 0.05 and lo[2] >= lane["max"][1] - 0.4 - 1e-6, spec["id"]
        else:
            assert lo[2] >= z0 - 0.05 and hi[2] <= lane["min"][1] + 0.4 + 1e-6, spec["id"]
        # everything except the roof (eave, ropes, weights) stays behind the lane edge
        body = [p for p in world if not p.name.startswith(("roof-", "weight-"))]
        blo, bhi = g.bounds(body)
        if spec["front"] == "-z":
            assert blo[2] >= lane["max"][1] - 0.06, (spec["id"], blo)
        else:
            assert bhi[2] <= lane["min"][1] + 0.06, (spec["id"], bhi)


def test_roof_types_split_between_tarp_and_corrugated():
    kinds = [stalls.build_stall(s).meta["roof"] for s in build_layout()["stalls"]]
    assert set(kinds) == {"tarp", "corrugated"}
    assert kinds.count("tarp") == len(kinds) // 2
    for s in build_layout()["stalls"]:
        a = stalls.build_stall(s)
        mats = {p.material for p in a.parts if p.name.startswith("roof-")}
        if a.meta["roof"] == "tarp":
            assert mats & {"tarp_blue", "tarp_orange", "tarp_green"}
            assert any(p.name.startswith("roof-rope") for p in a.parts)
        else:
            assert "corrugated" in mats or "corrugated_rust" in mats
            assert any(p.name.startswith("weight-tire") and p.material == "rubber" for p in a.parts)


def test_tarp_sags_between_its_edges():
    for s in build_layout()["stalls"]:
        a = stalls.build_stall(s)
        if a.meta["roof"] != "tarp":
            continue
        assert 0.12 <= a.meta["sag"] <= 0.25
        tarp = next(p for p in a.parts if p.name.startswith("roof-tarp"))
        ys = [v[1] for v in tarp.vertices]
        assert max(ys) - min(ys) >= a.meta["sag"]


def test_posts_shelves_bulbs_and_goods_materials():
    for s in build_layout()["stalls"]:
        a = stalls.build_stall(s)
        posts = [p for p in a.parts if p.name.startswith("post-")]
        assert 4 <= len(posts) <= 6 and all(p.material == "steel_bare" for p in posts)
        shelves = [p for p in a.parts if p.name.startswith("shelf-")]
        assert shelves and all(p.material == "steel_dark" for p in shelves)
        assert 2 <= a.meta["shelf_levels"] <= 3
        bulbs = [p for p in a.parts if p.name.startswith("bulb-") and p.material == "warm_bulb"]
        assert 2 <= len(bulbs) <= 3
        goods_mats = {p.material for p in a.parts if p.name.startswith("goods-")}
        assert {"electronics", "glass_dark", "rubber", "steel_bare", "paint_yellow_faded", "plastic_crate"} <= goods_mats
        sign = [p for p in a.parts if p.name.startswith("sign-board")]
        assert sign and sign[0].material in {"paint_teal_faded", "plywood"}


def test_sign_anchor_matches_layout_sign_positions():
    data = build_layout()
    for s in data["stalls"]:
        a = stalls.build_stall(s)
        anchor = a.meta["sign_anchor"]
        world = [anchor[0] + a.origin[0], anchor[1] + a.origin[1], anchor[2] + a.origin[2]]
        sign = next((x for x in data["signs"] if x.get("target") == s["id"]), None)
        if sign is not None:
            assert world == pytest.approx(sign["position"], abs=1e-3), s["id"]
        # the anchor sits just in front of the board face
        board = next(p for p in a.parts if p.name.startswith("sign-board"))
        blo, bhi = g.bounds([g.transformed(board, 0.0, a.origin)])
        assert blo[0] <= world[0] <= bhi[0] and blo[1] <= world[1] <= bhi[1]
        face_z = blo[2] if s["front"] == "-z" else bhi[2]
        assert 0.0 < abs(world[2] - face_z) <= 0.03, s["id"]


def test_counter_is_behind_front_posts_and_crates_carry_it():
    for s in build_layout()["stalls"]:
        a = stalls.build_stall(s)
        top = next(p for p in a.parts if p.name.startswith("counter-top"))
        crates = [p for p in a.parts if p.name.startswith("counter-crate")]
        assert len(crates) >= 2 and all(p.material == "plastic_crate" for p in crates)
        assert top.material == "plywood"
        clo, chi = g.bounds(crates)
        assert clo[1] >= -1e-6 and abs(chi[1] - g.bounds([top])[0][1]) < 0.01


def test_junk_piles_stay_off_lane_streets_and_plots(market):
    data = build_layout()
    blockers = [_aabb(x) for x in [*data["towers"], *data["stalls"], *data["clubs"], *data["shacks"]]]
    streets = [_street_rect(s) for s in data["streets"]]
    for a in market:
        if a.kind != "junk-pile":
            continue
        lo, hi = g.bounds([g.transformed(p, 0.0, a.origin) for p in a.parts])
        assert lo[1] >= -0.05 and hi[1] <= 1.6, a.name
        for r in [*blockers, *streets]:
            overlap = min(hi[0], r[2]) - max(lo[0], r[0]), min(hi[2], r[3]) - max(lo[2], r[1])
            assert not (overlap[0] > 0.02 and overlap[1] > 0.02), (a.name, r)
        mats = {p.material for p in a.parts}
        assert "rubber" in mats and len(mats) >= 4
        assert 400 <= sum(g.triangle_count(p) for p in a.parts) <= 4000


def test_budget_and_determinism(market):
    tris = sum(g.triangle_count(p) for a in market for p in a.parts)
    assert tris <= 75000
    again = stalls.market_assemblies(build_layout())
    assert [(a.name, [(p.name, p.vertices) for p in a.parts]) for a in again] == \
           [(a.name, [(p.name, p.vertices) for p in a.parts]) for a in market]


def test_wear_sprays_have_causes():
    for s in build_layout()["stalls"]:
        a = stalls.build_stall(s)
        sprays = a.meta["sprays"]
        feet = [sp for sp in sprays if sp.materials == ("steel_bare",) and sp.center[1] < 0.3]
        assert len(feet) >= 4, s["id"]                       # rust at every post foot
        under = [sp for sp in sprays if sp.center[1] < 0.5 and "plastic_crate" in sp.materials]
        assert under, s["id"]                                 # grime under the counter
        for sp in sprays:                                      # sprays are world-space, near the stall
            assert math.dist((sp.center[0], sp.center[2]), (a.origin[0], a.origin[2])) < 3.5


def test_torus_primitive_is_closed_outward():
    t = g.torus("t", (1.0, 2.0, 3.0), 0.3, 0.08, 12, 6, "rubber")
    assert _closed_consistent(t) and g.signed_volume(t) > 0
    expected = 2 * math.pi ** 2 * 0.3 * 0.08 ** 2
    assert g.signed_volume(t) == pytest.approx(expected, rel=0.25)   # hexagonal section, 12 segments


def _top_surface(sheets, x, z):
    """Highest upward-facing sheet face above (x, z), by barycentric test on fan triangles; None if none."""
    best = None
    for m in sheets:
        for face in m.faces:
            pts = [m.vertices[i] for i in face]
            if g.face_normal(pts)[1] <= 0.5:
                continue
            for k in range(1, len(pts) - 1):
                a, b, c = pts[0], pts[k], pts[k + 1]
                det = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
                if abs(det) < 1e-12:
                    continue
                l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / det
                l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / det
                l3 = 1 - l1 - l2
                if min(l1, l2, l3) >= -1e-9:
                    y = l1 * a[1] + l2 * b[1] + l3 * c[1]
                    best = y if best is None else max(best, y)
    return best


def test_weight_tyres_rest_on_the_corrugated_sheets():
    """Regression (review fix 1): tyres were tilted against the pitch and sank through the sheets."""
    checked = 0
    for s in build_layout()["stalls"]:
        a = stalls.build_stall(s)
        if a.meta["roof"] != "corrugated":
            continue
        sheets = [p for p in a.parts if p.name.startswith("roof-sheet")]
        for tyre in [p for p in a.parts if p.name.startswith("weight-tire")]:
            gaps, contact = [], []
            for v in tyre.vertices:
                top = _top_surface(sheets, v[0], v[2])
                if top is None:
                    continue
                gaps.append(v[1] - top)
                # ridge envelope: highest sheet top within one corrugation pitch along x
                env = max(t for t in (_top_surface(sheets, v[0] + dx * 0.02, v[2]) for dx in range(-5, 6))
                          if t is not None)
                contact.append(v[1] - env)
            assert gaps, (s["id"], tyre.name)
            assert min(gaps) >= -1e-4, (s["id"], tyre.name, min(gaps))       # never below the top skin
            assert min(contact) <= 0.01, (s["id"], tyre.name, min(contact))  # and not floating
            checked += 1
    assert checked >= 12
