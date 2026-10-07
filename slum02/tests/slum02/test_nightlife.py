import math

import pytest

from modeling.slum02 import geometry as g
from modeling.slum02 import nightlife
from modeling.slum02.layout import _aabb, build_layout


def test_club_height_and_budget():
    data = build_layout()
    for spec, a in zip(data["clubs"], nightlife.nightlife_assemblies(data)):
        lo, hi = g.bounds(a.parts)
        assert abs(hi[1] - spec["height"]) < 1.6
        tris = sum(g.triangle_count(p) for p in a.parts)
        assert 1500 <= tris <= 12000


# --------------------------------------------------------------------------- extra invariants

TOL = 1e-6


@pytest.fixture(scope="module")
def data():
    return build_layout()


@pytest.fixture(scope="module")
def clubs(data):
    return nightlife.nightlife_assemblies(data)


def _local(a, meshes):
    """Undo the baked yaw: parts back into the club frame (+Z = front, X across the facade)."""
    yaw = a.meta["frame"]["yaw"]
    return [g.transformed(m, -yaw, (0.0, 0.0, 0.0)) for m in meshes]


def _parts(a, prefix):
    return [p for p in a.parts if p.name.startswith(prefix)]


def _closed_consistent(mesh):
    directed = set()
    for face in mesh.faces:
        for x, y in zip(face, (*face[1:], face[0])):
            if (x, y) in directed:
                return False
            directed.add((x, y))
    return all((y, x) in directed for x, y in directed)


def test_names_sector_origin_and_determinism(data, clubs):
    assert [a.name for a in clubs] == [c["id"] for c in data["clubs"]]
    for spec, a in zip(data["clubs"], clubs):
        assert a.sector == "nightlife" and a.kind == "club"
        assert a.origin == pytest.approx((spec["center"][0], 0.0, spec["center"][1]))
    again = nightlife.nightlife_assemblies(build_layout())
    assert [(a.name, [(p.name, p.vertices) for p in a.parts]) for a in again] == \
           [(a.name, [(p.name, p.vertices) for p in a.parts]) for a in clubs]


def test_every_part_is_a_closed_outward_shell(clubs):
    """R11: no normal recalculation in Blender, so every part is a closed outward shell."""
    for a in clubs:
        for part in a.parts:
            assert _closed_consistent(part), (a.name, part.name)
            assert g.signed_volume(part) > 0, (a.name, part.name)


def test_polygons_are_planar_for_metric_uvs(clubs):
    for a in clubs:
        for part in a.parts:
            for face in part.faces:
                if len(face) == 3:
                    continue
                pts = [part.vertices[i] for i in face]
                n = g.face_normal(pts)
                c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
                assert max(abs(sum((p[k] - c[k]) * n[k] for k in range(3))) for p in pts) < 1e-5, (a.name, part.name)


def test_building_stays_on_its_plot(data, clubs):
    """Only the front may project (awning, sign, AC): at most 0.8 m past the facade; sides 0.15 m."""
    for spec, a in zip(data["clubs"], clubs):
        world = [g.transformed(p, 0.0, a.origin) for p in a.parts]
        lo, hi = g.bounds(world)
        assert lo[1] >= -1e-6, a.name
        x0, z0, x1, z1 = _aabb(spec)
        front = spec["front"]
        slack = {"-x": (0.8, 0.15, 0.15, 0.15), "+x": (0.15, 0.15, 0.8, 0.15)}[front]
        assert lo[0] >= x0 - slack[0] and lo[2] >= z0 - slack[1], a.name
        assert hi[0] <= x1 + slack[2] and hi[2] <= z1 + slack[3], a.name
        # the main box reaches the layout height
        body = g.bounds(_parts(a, "body"))
        assert body[1][1] == pytest.approx(spec["height"] - nightlife.PARAPET), a.name
        wall = g.bounds(_parts(a, "wall-upper"))
        assert wall[1][1] == pytest.approx(spec["height"]), a.name


def test_floors_and_wall_materials(data, clubs):
    for spec, a in zip(data["clubs"], clubs):
        assert a.meta["floors"] in (2, 3), a.name
        assert _parts(a, "wall-ground")[0].material in ("concrete_patch", "concrete_stained")
        assert _parts(a, "wall-upper")[0].material in ("concrete_patch", "concrete_stained")
        assert _parts(a, "body")[0].material in ("concrete_patch", "concrete_stained")


def test_sign_anchor_matches_layout_and_sits_on_board(data, clubs):
    for spec, a in zip(data["clubs"], clubs):
        sign = next(s for s in data["signs"] if s.get("target") == spec["id"])
        anchor = a.meta["sign_anchor"]
        world = [anchor[k] + a.origin[k] for k in range(3)]
        assert world == pytest.approx(sign["position"], abs=1e-3), a.name
        board = _local(a, _parts(a, "signboard"))
        lo, hi = g.bounds(board)
        la = g.rotate_y(anchor, -a.meta["frame"]["yaw"])
        assert lo[0] < la[0] < hi[0] and lo[1] < la[1] < hi[1], a.name
        assert 0.0 < la[2] - hi[2] <= 0.03, a.name                   # text just in front of the board
        F = a.meta["frame"]["facade"]
        assert abs(lo[2] - F) < TOL, a.name                            # board flat on the facade


def test_light_anchor_in_front_of_entrance(clubs):
    for a in clubs:
        f = a.meta["frame"]
        la = g.rotate_y(a.meta["light_anchor"], -f["yaw"])
        door = f["door"]
        assert la[0] == pytest.approx((door[0] + door[2]) / 2, abs=1e-6)
        assert la[1] == pytest.approx(2.6)
        assert la[2] == pytest.approx(f["ground_face"] + 1.2)


def test_bead_curtain_strands(clubs):
    for a in clubs:
        f = a.meta["frame"]
        x0, y0, x1, y1 = f["door"]
        beads = sorted(_local(a, _parts(a, "bead-")), key=lambda m: g.bounds([m])[0][0])
        assert [m.name for m in sorted(_parts(a, "bead-"), key=lambda m: m.name)] == [f"bead-{k:02d}" for k in range(24)]
        mats = [m.material for m in beads]
        assert mats == [("cloth_red", "neon_pink")[k % 2] for k in range(24)] or \
               mats == [("neon_pink", "cloth_red")[k % 2] for k in range(24)], a.name
        rod = g.bounds(_local(a, _parts(a, "beadrail")))
        for m in beads:
            lo, hi = g.bounds([m])
            assert hi[0] - lo[0] == pytest.approx(0.015) and hi[2] - lo[2] == pytest.approx(0.015)
            assert hi[1] - lo[1] == pytest.approx(2.0)
            assert x0 < lo[0] and hi[0] < x1, a.name                  # inside the doorway, clear of the jambs
            assert hi[1] == pytest.approx(rod[0][1]), a.name          # hung from the rod
            assert lo[1] > y0 + 0.02, a.name                          # clear of the threshold
            assert f["ground_face"] - 0.35 < lo[2] and hi[2] < f["ground_face"], a.name
        assert rod[1][1] == pytest.approx(y1) and rod[0][0] == pytest.approx(x0) and rod[1][0] == pytest.approx(x1)


def test_shutter_half_open_and_slats_run_into_the_box(clubs):
    for a in clubs:
        f = a.meta["frame"]
        x0, y0, x1, _y1 = f["shutter"]
        G = f["ground_face"]
        slats = g.bounds(_local(a, _parts(a, "shutter-slats")))
        box = g.bounds(_local(a, _parts(a, "shutter-box")))
        bar = g.bounds(_local(a, _parts(a, "shutter-bar")))
        rails = _local(a, _parts(a, "shutter-rail"))
        assert _parts(a, "shutter-box")[0].material == "corrugated_rust"
        assert _parts(a, "shutter-slats")[0].material == "corrugated_rust"
        # the curtain hangs from the box: its top meets the box underside, inside the box depth
        assert slats[1][1] == pytest.approx(box[0][1]), a.name
        assert box[0][2] == pytest.approx(G) and slats[0][2] > G and slats[1][2] < box[1][2], a.name
        assert slats[0][0] == pytest.approx(x0) and slats[1][0] == pytest.approx(x1), a.name
        # bottom bar under the slats, 0.8 m of dark opening below it
        assert bar[1][1] == pytest.approx(slats[0][1]), a.name
        assert bar[0][1] - y0 == pytest.approx(0.8), a.name
        # rails flank the opening, touching the slat edges, from the ground to the box
        rl = sorted((g.bounds([r]) for r in rails), key=lambda b: b[0][0])
        assert len(rl) == 2
        assert rl[0][1][0] == pytest.approx(x0) and rl[1][0][0] == pytest.approx(x1), a.name
        for lo, hi in rl:
            assert lo[1] == pytest.approx(0.0) and hi[1] == pytest.approx(box[0][1]) and lo[2] == pytest.approx(G)


def test_neon_is_mounted_on_the_wall(clubs):
    """Neon frame and motif hang 1-3 cm off their wall on clips that touch both wall and tube."""
    for a in clubs:
        f = a.meta["frame"]
        for tube_name, clip_name, wall_z in (("neonframe-tube", "neonframe-clip", f["ground_face"]),
                                             ("neonsign-tube", "neonsign-clip", f["facade"])):
            tube = _local(a, _parts(a, tube_name))
            assert tube, (a.name, tube_name)
            assert all(t.material.startswith("neon_") for t in tube)
            back = g.bounds(tube)[0][2]
            assert 0.01 <= back - wall_z <= 0.03, (a.name, tube_name, back - wall_z)
            clips = _local(a, _parts(a, clip_name))
            assert len(clips) >= 3, (a.name, clip_name)
            for c in clips:
                lo, hi = g.bounds([c])
                assert lo[2] == pytest.approx(wall_z) and hi[2] == pytest.approx(back), (a.name, clip_name)
        assert _parts(a, "neonframe-tube")[0].material == a.meta["neon"]
        assert a.meta["motif"] in ("heart", "crescent")


def test_door_frame_surrounds_the_doorway(clubs):
    for a in clubs:
        x0, _y0, x1, y1 = a.meta["frame"]["door"]
        lo, hi = g.bounds(_local(a, _parts(a, "neonframe-tube")))
        assert lo[0] < x0 - 0.05 and hi[0] > x1 + 0.05 and hi[1] > y1 + 0.05, a.name
        awning = g.bounds(_local(a, _parts(a, "awning-sheet")))
        assert awning[0][1] > hi[1] + 0.01, a.name                     # canopy clears the neon


def test_posters(clubs):
    for a in clubs:
        f = a.meta["frame"]
        posters = _parts(a, "poster-")
        assert 6 <= len(posters) <= 10, a.name
        assert all(p.material.startswith(("paint_", "tarp_")) for p in posters)
        local = _local(a, posters)
        rects = []
        for p in local:
            lo, hi = g.bounds([p])
            wall = min((f["ground_face"], f["facade"] + nightlife.COL_OUT), key=lambda z: abs(lo[2] - z))
            assert 0.0 < lo[2] - wall <= 0.002, (a.name, p.name)        # pasted on, no gap
            assert hi[2] - wall == pytest.approx(0.01, abs=1e-6), (a.name, p.name)
            # 0.3 x 0.42 sheet (tilted by a few degrees)
            ys = sorted(v[1] for v in p.vertices)
            assert 0.42 <= ys[-1] - ys[0] <= 0.47 and 0.3 <= hi[0] - lo[0] <= 0.36
            rects.append((lo[0], lo[1], hi[0], hi[1], wall))
        keep_out = [f["door"], f["shutter"]]
        frame = g.bounds(_local(a, _parts(a, "neonframe")))
        keep_out.append((frame[0][0], frame[0][1], frame[1][0], frame[1][1]))
        for i, r in enumerate(rects):
            for o in rects[i + 1:]:
                if r[4] == o[4]:
                    assert min(r[2], o[2]) - max(r[0], o[0]) <= 0 or min(r[3], o[3]) - max(r[1], o[1]) <= 0, a.name
            if r[4] == f["ground_face"]:
                for k in keep_out:
                    assert min(r[2], k[2]) - max(r[0], k[0]) <= 0 or min(r[3], k[3]) - max(r[1], k[1]) <= 0, a.name


def test_red_lamps_and_bulbs(clubs):
    for a in clubs:
        lamps = [p for p in _parts(a, "lamp-") if p.material == "neon_red"]
        assert len(lamps) >= 2, a.name
        bulbs = [p for p in _parts(a, "bulb-") if p.material == "warm_bulb"]
        assert 2 <= len(bulbs) <= 4, a.name
        awning = g.bounds(_local(a, _parts(a, "awning-sheet")))
        for b in _local(a, bulbs):
            lo, hi = g.bounds([b])
            assert awning[0][0] < lo[0] and hi[0] < awning[1][0] and hi[1] < awning[0][1]
            assert lo[1] > 2.0, a.name                                   # head clearance


def test_upper_windows_have_red_curtains_in_the_recess(clubs):
    for a in clubs:
        f = a.meta["frame"]
        curtains = _local(a, _parts(a, "curtain-"))
        assert len(curtains) >= 2, a.name
        assert all(c.material == "cloth_red" for c in _parts(a, "curtain-"))
        for c in curtains:
            lo, hi = g.bounds([c])
            assert f["facade"] - nightlife.WINDOW_RECESS < lo[2] and hi[2] < f["facade"] - 0.1, a.name
            assert lo[1] > 3.0, a.name
            assert any(w[0] - 1e-6 <= lo[0] and hi[0] <= w[2] + 1e-6 and w[1] - 1e-6 <= lo[1] and hi[1] <= w[3] + 1e-6
                       for w in f["windows"]), (a.name, c.name)


def test_ac_units_sit_on_brackets_and_carry_pipes(clubs):
    for a in clubs:
        f = a.meta["frame"]
        units = _parts(a, "ac-")
        bodies = [p for p in units if p.name.endswith("-body")]
        assert bodies, a.name
        for body in bodies:
            stem = body.name[: -len("-body")]
            lo, _hi = g.bounds(_local(a, [body]))
            if stem.startswith("ac-roof"):
                assert lo[1] == pytest.approx(f["roof"]), (a.name, stem)
                continue
            assert lo[2] == pytest.approx(f["facade"] + nightlife.AC_GAP), (a.name, stem)
            brackets = _local(a, [p for p in units if p.name.startswith(stem + "-bracket")])
            assert len(brackets) == 2, (a.name, stem)
            for b in brackets:
                blo, bhi = g.bounds([b])
                assert blo[2] == pytest.approx(f["facade"]) and bhi[1] == pytest.approx(lo[1]), (a.name, stem)
            pipe = _local(a, [p for p in units if p.name.startswith(stem + "-pipe")])
            assert pipe and g.bounds(pipe)[0][2] == pytest.approx(f["facade"], abs=1e-6), (a.name, stem)


def test_front_projections_keep_clear_of_mounted_ads(data, clubs):
    """Vertical ads hang 0.12 m in front of club facades from 2.5 m up: nothing may reach them."""
    checked = 0
    for spec, a in zip(data["clubs"], clubs):
        f = a.meta["frame"]
        for ad in [x for x in data["ads"] if x.get("mount") == spec["id"]]:
            p = g.rotate_y((ad["position"][0] - a.origin[0], 0.0, ad["position"][2] - a.origin[2]), -f["yaw"])
            w, h = ad["size"]
            ax0, ax1 = p[0] - w / 2, p[0] + w / 2
            ay0, ay1 = ad["position"][1] - h / 2, ad["position"][1] + h / 2
            for part in _local(a, a.parts):
                for v in part.vertices:
                    if v[2] > f["facade"] + 0.1 and ax0 - 0.05 < v[0] < ax1 + 0.05 and ay0 - 0.05 < v[1] < ay1 + 0.05:
                        pytest.fail(f"{a.name} {part.name} reaches ad {ad['id']} at {v}")
            checked += 1
    assert checked == 2


def test_roof_cable_posts_meet_layout_cables(data, clubs):
    for spec, a in zip(data["clubs"], clubs):
        posts = [g.bounds([g.transformed(p, 0.0, a.origin)]) for p in _parts(a, "cablepost-")]
        for c in data["cables"]:
            for end in (c["a"], c["b"]):
                if spec["id"] in c["attach"] and abs(end[1] - spec["height"]) < 1e-6 and \
                        _aabb(spec)[0] <= end[0] <= _aabb(spec)[2] and _aabb(spec)[1] <= end[2] <= _aabb(spec)[3]:
                    assert any(lo[0] < end[0] < hi[0] and lo[2] < end[2] < hi[2] and hi[1] >= end[1] for lo, hi in posts), \
                        (a.name, c["id"])


def test_wear_sprays_have_causes(clubs):
    for a in clubs:
        sprays = a.meta["sprays"]
        f = a.meta["frame"]
        kinds = a.meta["spray_kinds"]
        assert len(kinds) == len(sprays)
        assert "rust-shutter" in kinds and "grime-foot" in kinds and "rust-ac" in kinds, a.name
        for sp in sprays:
            assert math.dist((sp.center[0], sp.center[2]), (a.origin[0], a.origin[2])) < 6.0
        # rust under the shutter box sits below its underside
        k = kinds.index("rust-shutter")
        c = g.rotate_y((sprays[k].center[0] - a.origin[0], sprays[k].center[1], sprays[k].center[2] - a.origin[2]), -f["yaw"])
        box = g.bounds(_local(a, _parts(a, "shutter-box")))
        assert c[1] < box[0][1] and box[0][0] <= c[0] <= box[1][0]


def test_content_stays_suggestive(clubs):
    """Global constraint: no imagery or text in geometry — posters are plain sheets, motif is heart or crescent."""
    for a in clubs:
        for p in _parts(a, "poster-"):
            assert len(p.vertices) == 8 and len(p.faces) == 6
        assert a.meta["motif"] in ("heart", "crescent")


def test_sector_registration_and_budget(data, clubs):
    from modeling.slum02.sectors import sector_assemblies
    assert [x.name for x in sector_assemblies(data, "nightlife")] == [a.name for a in clubs]
    assert sum(g.triangle_count(p) for a in clubs for p in a.parts) <= 48000


# --------------------------------------------------------------------------- contact / clearance (Task 9 lesson)

# wall parts contain their recess fillings (glass, curtains, beads, doors), and a column's
# lower/upper boxes form an L around the ground wall: their AABBs overlap without the solids
# touching. The awning sheet is sloped, so its AABB covers the brackets/wires under it; those
# are checked exactly in test_awning_brackets_and_bulb_wires_touch_the_sheet_underside.
_CONTAINERS = ("wall-", "column-", "awning-sheet")


def test_no_part_interpenetrates_another(clubs):
    for a in clubs:
        local = _local(a, a.parts)
        boxes = [g.bounds([p]) for p in local]
        for i, p in enumerate(local):
            if p.name.startswith(_CONTAINERS):
                continue
            for j in range(i + 1, len(local)):
                q = local[j]
                if q.name.startswith(_CONTAINERS):
                    continue
                ext = [min(boxes[i][1][k], boxes[j][1][k]) - max(boxes[i][0][k], boxes[j][0][k]) for k in range(3)]
                assert min(ext) <= 2e-3, (a.name, p.name, q.name, ext)


def _underside(sheet, x, z):
    """Lowest downward-facing sheet face below which (x, z) lies (barycentric over fan triangles)."""
    best = None
    for face in sheet.faces:
        pts = [sheet.vertices[i] for i in face]
        if g.face_normal(pts)[1] >= -0.5:
            continue
        for k in range(1, len(pts) - 1):
            p0, p1, p2 = pts[0], pts[k], pts[k + 1]
            det = (p1[2] - p2[2]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[2] - p2[2])
            if abs(det) < 1e-12:
                continue
            l1 = ((p1[2] - p2[2]) * (x - p2[0]) + (p2[0] - p1[0]) * (z - p2[2])) / det
            l2 = ((p2[2] - p0[2]) * (x - p2[0]) + (p0[0] - p2[0]) * (z - p2[2])) / det
            l3 = 1 - l1 - l2
            if min(l1, l2, l3) >= -1e-9:
                y = l1 * p0[1] + l2 * p1[1] + l3 * p2[1]
                best = y if best is None else min(best, y)
    return best


def test_awning_brackets_and_bulb_wires_touch_the_sheet_underside(clubs):
    for a in clubs:
        sheet = _local(a, _parts(a, "awning-sheet"))[0]
        for wire in _local(a, _parts(a, "bulb-wire-")):
            top = g.bounds([wire])[1][1]
            gaps = [_underside(sheet, v[0], v[2]) - v[1] for v in wire.vertices if v[1] > top - 1e-9]
            assert min(gaps) >= -1e-6 and min(gaps) <= 1e-3, (a.name, wire.name, gaps)
        for bracket in _local(a, _parts(a, "awning-bracket-")):
            tops = [v for v in bracket.vertices if v[1] > g.bounds([bracket])[1][1] - 0.1 and v[2] > a.meta["frame"]["ground_face"] + 1e-6]
            gaps = [_underside(sheet, v[0], v[2]) - v[1] for v in tops]
            assert min(gaps) >= -1e-6, (a.name, bracket.name, min(gaps))       # never pierces the sheet
            assert max(gaps) <= 3e-3, (a.name, bracket.name, max(gaps))        # and carries it


def test_cable_posts_stand_on_the_deck_clear_of_the_parapets(clubs):
    for a in clubs:
        f = a.meta["frame"]
        parapets = [g.bounds([p]) for p in _local(a, _parts(a, "parapet-"))]
        for p in _local(a, _parts(a, "cablepost-")):
            lo, hi = g.bounds([p])
            assert lo[1] >= f["roof"] - 1e-9, (a.name, p.name)
            for plo, phi in parapets:
                assert min(hi[0], phi[0]) - max(lo[0], plo[0]) <= 0 or min(hi[2], phi[2]) - max(lo[2], plo[2]) <= 0, \
                    (a.name, p.name)


def test_downpipe_hangs_from_hopper_on_clamps(clubs):
    for a in clubs:
        pipe = g.bounds(_local(a, _parts(a, "drain-pipe")))
        hopper = g.bounds(_local(a, _parts(a, "drain-hopper")))
        wall = g.bounds(_local(a, _parts(a, "body")))
        assert pipe[1][1] == pytest.approx(hopper[0][1]), a.name
        clamps = [g.bounds([c]) for c in _local(a, _parts(a, "drain-clamp-"))]
        assert len(clamps) == 3
        right = pipe[0][0] > 0
        side_x = wall[1][0] + nightlife.SIDE_T if right else wall[0][0] - nightlife.SIDE_T   # outer face of the side wall
        for lo, hi in clamps:
            wall_end, pipe_end = (lo[0], hi[0]) if right else (hi[0], lo[0])
            assert wall_end == pytest.approx(side_x), a.name                              # fixed to the wall
            assert pipe_end == pytest.approx(pipe[0][0] if right else pipe[1][0]), a.name  # reaches the pipe skin
            assert pipe[0][1] < lo[1] and hi[1] < pipe[1][1]
