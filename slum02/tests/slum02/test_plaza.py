import math

from modeling.slum02 import geometry as g
from modeling.slum02 import plaza
from modeling.slum02.layout import build_layout


def _named():
    return {a.name: a for a in plaza.plaza_assemblies(build_layout())}


def test_expected_objects():
    names = set(_named())
    assert {"plaza-floor", "plaza-columns", "plaza-crane-rail", "plaza-truss", "plaza-press", "plaza-conveyor",
            "plaza-tank", "plaza-car", "plaza-fire-barrel", "plaza-perimeter", "east-wall"} <= names


def test_everything_inside_plaza_footprint():
    for a in plaza.plaza_assemblies(build_layout()):
        lo, hi = g.bounds([g.transformed(p, 0.0, a.origin) for p in a.parts])
        assert lo[0] >= -10.3 and hi[0] <= 10.3 and lo[2] >= -10.3 and hi[2] <= 10.3, a.name


def test_east_wall_geometry_and_front_plane():
    wall = _named()["east-wall"]
    lo, hi = g.bounds([g.transformed(p, 0.0, wall.origin) for p in wall.parts if p.name.startswith("wall-body")])
    assert abs(lo[0] - 9.2) < 1e-6 and abs(hi[0] - 10.0) < 1e-6
    assert abs(lo[2] + 10) < 1e-6 and abs(hi[2] - 10) < 1e-6
    assert 8.7 <= hi[1] <= 10.05
    assert sum(1 for p in wall.parts if p.name.startswith("rebar")) == 18


def test_overspray_sits_on_wall_face():
    wall = _named()["east-wall"]
    sprays = wall.meta["sprays"]
    assert len(sprays) >= 20
    assert all(abs(s.center[0] - 9.2) < 0.3 for s in sprays)


def test_spray_art_layout_has_ring_glyph_and_fits():
    lay = plaza.spray_layout()
    texts = [l.get("text") for l in lay["lines"] if "text" in l]
    assert texts == ["トーキョー", "N", "VA"]
    assert any("ring" in l for l in lay["lines"])
    red, black = plaza.ring_glyph((9.19, 3.5, 0.0), 1.2, 0.28, 0.006)
    rlo, rhi = g.bounds([red])
    blo, bhi = g.bounds([black])
    assert bhi[1] - blo[1] > rhi[1] - rlo[1]  # black outline is fatter than the red fill
    assert rlo[0] < 9.2 and blo[0] > rlo[0]    # red sits in front of black (closer to plaza, -X)


def test_exits_are_open():
    perim = _named()["plaza-perimeter"]
    for x0, z0, x1, z1 in build_layout()["plaza_features"]["exits"]:
        for p in perim.parts:
            lo, hi = g.bounds([p])
            overlap = lo[0] < x1 and hi[0] > x0 and lo[2] < z1 and hi[2] > z0
            assert not overlap, p.name


# --------------------------------------------------------------------------- additional checks


def _closed_consistent(mesh):
    directed = set()
    for face in mesh.faces:
        for a, b in zip(face, (*face[1:], face[0])):
            if (a, b) in directed:
                return False
            directed.add((a, b))
    return all((b, a) in directed for a, b in directed)


def _signed_volume(mesh):
    total = 0.0
    for face in mesh.faces:
        p0 = mesh.vertices[face[0]]
        for i in range(1, len(face) - 1):
            p1, p2 = mesh.vertices[face[i]], mesh.vertices[face[i + 1]]
            total += (p0[0] * (p1[1] * p2[2] - p1[2] * p2[1])
                      - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0])
                      + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])) / 6
    return total


def test_all_plaza_parts_are_closed_and_wound_outward():
    """R11: Blender never recalculates normals, so every plaza part is a closed outward shell."""
    for a in plaza.plaza_assemblies(build_layout()):
        for part in a.parts:
            assert _closed_consistent(part), (a.name, part.name)
            assert _signed_volume(part) > 0, (a.name, part.name)


def test_ring_glyph_parts_are_closed_and_outward():
    for m in plaza.ring_glyph((9.195, 3.5, 0.0), 1.4, 0.28, 0.006):
        assert _closed_consistent(m) and _signed_volume(m) > 0, m.name


def test_spray_layout_values():
    lay = plaza.spray_layout()
    assert lay["max_width"] == 17.0 and lay["plane_x"] == 9.195
    first = lay["lines"][0]
    assert (first["text"], first["baseline_y"], first["height"], first["center_z"]) == ("トーキョー", 5.9, 2.8, 0.0)
    second = [l for l in lay["lines"][1:]]
    assert all(l["baseline_y"] == 1.9 and l["height"] == 3.2 for l in second)
    ring = next(l["ring"] for l in lay["lines"] if "ring" in l)
    assert ring["center"] == [9.195, 3.5, 0.0]
    assert (ring["outer_radius"], ring["band"], ring["inner_outer_radius"]) == (1.4, 0.28, 0.75)


def test_budget_and_materials_and_determinism():
    from modeling.slum02.materials import MATERIALS
    from modeling.slum02.sectors import resource_report
    first = plaza.plaza_assemblies(build_layout())
    report = resource_report(first, "plaza")
    assert report["triangles"] <= 90_000, report["triangles"]
    assert set(report["materials"]) <= set(MATERIALS)
    second = plaza.plaza_assemblies(build_layout())
    assert [p.vertices for a in first for p in a.parts] == [p.vertices for a in second for p in a.parts]


def test_floor_top_pits_and_cracks():
    assert plaza.FLOOR_TOP == 0.12
    floor = _named()["plaza-floor"]
    slab = next(p for p in floor.parts if p.name == "floor-slab")
    lo, hi = g.bounds([slab])
    assert abs(hi[1] - plaza.FLOOR_TOP) < 1e-9 and lo[0] == -10 and hi[0] == 10 and lo[2] == -10 and hi[2] == 10
    # The slab is open over both pits; each pit has a floor of mud and standing water below grade.
    for x0, z0, x1, z1 in build_layout()["plaza_features"]["pits"]:
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        for face in slab.faces:
            pts = [slab.vertices[i] for i in face]
            fx = sum(p[0] for p in pts) / len(pts)
            fz = sum(p[2] for p in pts) / len(pts)
            assert not (abs(fx - cx) < 0.2 and abs(fz - cz) < 0.2 and min(p[1] for p in pts) > 0.1)
    assert sum(1 for p in floor.parts if p.name.startswith("pit-") and p.material == "mud") == 2
    assert sum(1 for p in floor.parts if p.name.startswith("pit-") and p.material == "asphalt_wet") >= 2
    cracks = [p for p in floor.parts if p.name.startswith("crack-")]
    assert len(cracks) == 12 and all(p.material == "concrete_dark" for p in cracks)
    assert all(abs(max(v[1] for v in p.vertices) - (plaza.FLOOR_TOP + 0.004)) < 1e-9 for p in cracks)


def test_columns_tilt_break_and_crane_rail_hangs():
    named = _named()
    cols = named["plaza-columns"]
    assert sum(1 for p in cols.parts if p.name.startswith("baseplate-")) == 5
    assert {p.material for p in cols.parts} >= {"rust", "paint_yellow_faded"}
    fallen = [p for p in cols.parts if p.name.startswith("fallen-")]
    assert fallen and max(v[1] for p in fallen for v in p.vertices) < 1.0
    rail = named["plaza-crane-rail"]
    ys = [v[1] for p in rail.parts for v in p.vertices]
    assert min(ys) <= plaza.FLOOR_TOP + 0.05 and 7.0 <= max(ys) <= 8.0


def test_car_and_fire_barrel_materials():
    named = _named()
    car = {p.material for p in named["plaza-car"].parts}
    assert {"rust_dark", "steel_dark"} <= car and "rubber" not in car  # tyres burnt away
    barrel = named["plaza-fire-barrel"]
    embers = [p for p in barrel.parts if p.material == "neon_orange"]
    assert embers
    drum_top = max(v[1] for p in barrel.parts if p.name.startswith("drum") for v in p.vertices)
    assert max(v[1] for p in embers for v in p.vertices) < drum_top


def test_car_rims_rest_on_the_floor():
    car = {p.name: p for p in _named()["plaza-car"].parts}
    rims = [n for n in car if n.startswith("car-rim-")]
    assert len(rims) == 4
    for n in rims:
        low = min(v[1] for v in car[n].vertices)
        assert plaza.FLOOR_TOP - 0.03 <= low <= plaza.FLOOR_TOP + 0.03, (n, low)
        # The hub stays centred on its rim.
        rim_mid = sum(g.bounds([car[n]])[i][1] for i in range(2)) / 2
        hub = car[n.replace("car-rim-", "car-hub-")]
        assert abs(sum(g.bounds([hub])[i][1] for i in range(2)) / 2 - rim_mid) < 0.02, n
    # The shell still lists: one side of the body sits clearly lower than the other.
    body = car["car-body"].vertices
    assert max(v[1] for v in body) - min(v[1] for v in body) > 0.7 + 0.1


def test_machine_bases_have_anchor_bolts():
    bases = _named()["plaza-machine-bases"]
    assert sum(1 for p in bases.parts if p.name.startswith("base-") and p.material == "concrete_raw") == 5
    heights = [g.bounds([p])[1][1] - plaza.FLOOR_TOP for p in bases.parts if p.name.startswith("base-")]
    assert all(0.3 - 1e-6 <= h <= 0.6 + 1e-6 for h in heights)
    assert sum(1 for p in bases.parts if p.material == "steel_dark") >= 20


def test_east_wall_pilasters_stop_below_lettering():
    wall = _named()["east-wall"]
    pil = sorted((p for p in wall.parts if p.name.startswith("wall-pilaster-")), key=lambda p: g.bounds([p])[0][2])
    assert len(pil) == 5
    tops = []
    for p in pil:
        lo, hi = g.bounds([g.transformed(p, 0.0, wall.origin)])
        assert abs(lo[0] - (9.2 - 0.35)) < 1e-6 and abs((hi[2] - lo[2]) - 0.6) < 1e-6
        tops.append(hi[1])
    assert tops[0] > 8 and tops[4] > 8
    assert all(t < 1.9 for t in tops[1:4])  # centre three end below the second line's baseline
    crowns = [p for p in wall.parts if p.name.startswith("wall-crown-")]
    assert crowns
    assert max(g.bounds([g.transformed(p, 0.0, wall.origin)])[1][1] for p in crowns) <= 10.0 + 1e-6
    assert wall.meta["spray_art"] == plaza.spray_layout()
    tags = [s for s in wall.meta["sprays"] if s.strength == 0.45]
    assert len(tags) == 6 and all(0.5 <= s.center[1] <= 3.0 for s in tags)


def test_polygons_are_planar_for_metric_uvs():
    """Blender's metric UV audit flags non-planar quads (bent tubes, torn plates); they must be split."""
    from modeling.slum02.vcolor import _face_normal
    for a in plaza.plaza_assemblies(build_layout()):
        for part in a.parts:
            for face in part.faces:
                if len(face) == 3:
                    continue
                pts = [part.vertices[i] for i in face]
                n = _face_normal(pts)
                c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
                assert max(abs(sum((p[k] - c[k]) * n[k] for k in range(3))) for p in pts) < 1e-5, (a.name, part.name)
