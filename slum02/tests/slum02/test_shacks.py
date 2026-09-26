import math

import pytest

from modeling.slum02 import geometry as g
from modeling.slum02 import shacks
from modeling.slum02.layout import _aabb, _street_rect, build_layout
from tests.slum02.test_stalls import _closed_consistent, _top_surface


def test_shack_patchwork_and_roof_slope():
    data = build_layout()
    built = shacks.shacks_assemblies(data)
    assert len(built) == len(data["shacks"])
    for a in built:
        wall_mats = {p.material for p in a.parts if p.name.startswith("panel-")}
        assert len(wall_mats) >= 3, a.name
        roof = [p for p in a.parts if p.name.startswith("roof-sheet")]
        ys = [v[1] for p in roof for v in p.vertices]
        assert max(ys) - min(ys) > 0.25, a.name
        assert any(p.name.startswith("tire-") for p in a.parts)
        assert a.meta.get("sprays"), a.name
        tris = sum(g.triangle_count(p) for p in a.parts)
        assert 700 <= tris <= 5000, (a.name, tris)


def test_shacks_are_low():
    for a in shacks.shacks_assemblies(build_layout()):
        assert g.bounds(a.parts)[1][1] <= 4.2


# --------------------------------------------------------------------------- extra invariants


@pytest.fixture(scope="module")
def data():
    return build_layout()


@pytest.fixture(scope="module")
def built(data):
    return shacks.shacks_assemblies(data)


def _local(a, meshes):
    """Undo the baked yaw: door-frame local coordinates (+Z = door wall, roof rises towards +Z)."""
    yaw = a.meta["frame"]["yaw"]
    return [g.transformed(m, -yaw, (0.0, 0.0, 0.0)) for m in meshes]


def _parts(a, prefix):
    return [p for p in a.parts if p.name.startswith(prefix)]


def _world(a, meshes):
    return [g.transformed(m, 0.0, a.origin) for m in meshes]


def test_names_sector_origin_registration_and_determinism(data, built):
    from modeling.slum02.sectors import sector_assemblies
    assert [a.name for a in built] == [s["id"] for s in data["shacks"]]
    for spec, a in zip(data["shacks"], built):
        assert a.kind == "shack" and a.sector == "shacks"
        assert a.origin == pytest.approx((spec["center"][0], 0.0, spec["center"][1]))
    again = sector_assemblies(data, "shacks")
    assert [(a.name, [(p.name, p.vertices) for p in a.parts]) for a in again] == \
           [(a.name, [(p.name, p.vertices) for p in a.parts]) for a in built]
    single = shacks.build_shack(data["shacks"][0])
    assert [(p.name, p.vertices) for p in single.parts] == [(p.name, p.vertices) for p in built[0].parts]
    assert 10 <= len(built) <= 14


def test_every_part_is_a_closed_outward_shell(built):
    """R11: panels, vinyl, curtains and laundry are thin closed shells so they read from both sides."""
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


def test_posts_stand_on_the_footprint(data, built):
    for spec, a in zip(data["shacks"], built):
        posts = _parts(a, "post-")
        assert 4 <= len(posts) <= 6 and all(p.material == "pallet_wood" for p in posts), a.name
        lo, hi = g.bounds(_world(a, posts))
        x0, z0, x1, z1 = _aabb(spec)
        assert lo[1] == pytest.approx(0.0, abs=1e-6)
        assert lo[0] >= x0 - 0.02 and hi[0] <= x1 + 0.02 and lo[2] >= z0 - 0.02 and hi[2] <= z1 + 0.02, a.name
        # nothing sinks into the ground
        assert g.bounds(a.parts)[0][1] >= -1e-6, a.name


def test_walls_are_patchworks_of_tilted_overlapping_panels(built):
    pool = {"corrugated", "corrugated_rust", "plywood", "tarp_blue", "tarp_orange", "tarp_green"}
    for a in built:
        walls = a.meta["walls"]
        assert set(walls) == {"front", "back", "left", "right"}
        for side, w in walls.items():
            panels = _parts(a, f"panel-{side}-")
            assert 2 <= w["panels"] <= 4 and len(panels) == w["panels"], (a.name, side)
            assert w["material"] in pool, (a.name, side)
            # one material per wall; walls of 3+ panels may carry one lapping patch of another sheet
            for p in panels:
                if p.name == w["patch"]:
                    assert w["panels"] >= 3 and p.material in pool and p.material != w["material"], (a.name, p.name)
                else:
                    assert p.material == w["material"], (a.name, p.name)
            assert all(abs(t) <= 3.0 + 1e-9 for t in w["tilts"]), (a.name, side)
            assert any(abs(t) >= 0.5 for t in w["tilts"]), (a.name, side)
            assert all(0.02 - 1e-9 <= o <= 0.05 + 1e-9 for o in w["overlaps"]), (a.name, side)


def _depth(a, side, p):
    """Outward distance of local point ``p`` from the post plane of wall ``side``."""
    f = a.meta["frame"]
    return {"front": p[2] - f["hz"], "back": -f["hz"] - p[2], "right": p[0] - f["hx"], "left": -f["hx"] - p[0]}[side]


def _wall_u(side, p):
    return {"front": p[0], "back": -p[0], "right": -p[2], "left": p[2]}[side]


def _wall_tris(a, side, panel, u0, u1):
    """Triangles of ``panel`` in wall coordinates (u, v, depth) whose u-extent meets [u0, u1]."""
    out = []
    pts = [(_wall_u(side, v), v[1], _depth(a, side, v)) for v in panel.vertices]
    for face in panel.faces:
        for k in range(1, len(face) - 1):
            tri = (pts[face[0]], pts[face[k]], pts[face[k + 1]])
            if max(p[0] for p in tri) >= u0 and min(p[0] for p in tri) <= u1:
                out.append(tri)
    return out


def _depths_at(tris, u, v):
    """Depths where the wall-normal ray through (u, v) crosses the triangles."""
    hits = []
    for p0, p1, p2 in tris:
        det = (p1[1] - p2[1]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[1] - p2[1])
        if abs(det) < 1e-12:
            continue
        l1 = ((p1[1] - p2[1]) * (u - p2[0]) + (p2[0] - p1[0]) * (v - p2[1])) / det
        l2 = ((p2[1] - p0[1]) * (u - p2[0]) + (p0[0] - p2[0]) * (v - p2[1])) / det
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) >= -1e-9:
            hits.append(l1 * p0[2] + l2 * p1[2] + l3 * p2[2])
    return hits


def test_panels_hang_on_the_posts_or_on_the_panel_below(built):
    """Layer-0 panels touch the post plane; a lapping panel rests on the panel it laps (no gap > 1 cm, no sinking).

    Measured with rays along the wall normal through the lap: the lapping sheet's inner face
    minus the outer face of the sheet under it.
    """
    for a in built:
        for side in ("front", "back", "left", "right"):
            panels = _local(a, _parts(a, f"panel-{side}-"))
            inner = [min(_depth(a, side, v) for v in p.vertices) for p in panels]
            assert min(inner) == pytest.approx(0.0, abs=1e-6), (a.name, side)
            # hangs on the post plane: layer 0 (a tarp cut around a door may start 1-2 mm off it) and a
            # stiff patch lapping a thin tarp edge, which clears the plane by the 2 mm lap allowance
            on_posts = [x <= 0.0025 for x in inner]
            span = [(min(_wall_u(side, v) for v in p.vertices), max(_wall_u(side, v) for v in p.vertices),
                     min(v[1] for v in p.vertices), max(v[1] for v in p.vertices)) for p in panels]
            for k, p in enumerate(panels):
                if on_posts[k]:
                    assert all(_depth(a, side, v) >= -1e-6 for v in p.vertices)
                    continue
                gaps = []
                for j, q in enumerate(panels):
                    if j == k or not on_posts[j]:
                        continue
                    u0, u1 = max(span[k][0], span[j][0]), min(span[k][1], span[j][1])
                    v0, v1 = max(span[k][2], span[j][2]), min(span[k][3], span[j][3])
                    if u1 <= u0 or v1 <= v0:
                        continue
                    pt, qt = _wall_tris(a, side, p, u0, u1), _wall_tris(a, side, q, u0, u1)
                    for r in range(1, 60):
                        v = v0 + (v1 - v0) * r / 60
                        for c in range(21):
                            u = u0 + (u1 - u0) * c / 20
                            ph, qh = _depths_at(pt, u, v), _depths_at(qt, u, v)
                            if ph and qh:
                                gaps.append(min(ph) - max(qh))
                assert gaps, (a.name, p.name)
                assert min(gaps) >= -1e-3, (a.name, p.name, min(gaps))    # never sinks into the sheet under it
                assert min(gaps) <= 0.01, (a.name, p.name, min(gaps))     # and rests on it


def test_mono_pitch_roof(built):
    for a in built:
        f = a.meta["frame"]
        assert 6.0 - 1e-9 <= f["slope_deg"] <= 12.0 + 1e-9, a.name
        sheets = _local(a, _parts(a, "roof-sheet"))
        assert sheets and all(p.material == "corrugated_rust" for p in sheets)
        lo, hi = g.bounds(sheets)
        assert lo[2] == pytest.approx(-f["hz"] - 0.3, abs=1e-6) and hi[2] == pytest.approx(f["hz"] + 0.3, abs=1e-6)
        # rises towards the door side
        front = [v[1] for p in sheets for v in p.vertices if v[2] > hi[2] - 1e-6]
        back = [v[1] for p in sheets for v in p.vertices if v[2] < lo[2] + 1e-6]
        assert min(front) > max(back), a.name


def _ridge_envelope(sheets, x, z):
    tops = [t for t in (_top_surface(sheets, x + dx * 0.02, z) for dx in range(-5, 6)) if t is not None]
    return max(tops)


def test_tyres_and_bricks_rest_on_the_roof_sheet(built):
    """Task 9 lesson: weights never pierce the sheet and never float more than 1 cm above its ridges."""
    checked = 0
    for a in built:
        tyres = _parts(a, "tire-")
        assert 2 <= len(tyres) <= 4 and all(p.material == "rubber" for p in tyres), a.name
        bricks = _parts(a, "brick-")
        assert bricks, a.name
        sheets = _parts(a, "roof-sheet")
        for w in tyres + bricks:
            gaps, contact = [], []
            for v in w.vertices:
                top = _top_surface(sheets, v[0], v[2])
                assert top is not None, (a.name, w.name)   # fully over the roof, no overhang
                gaps.append(v[1] - top)
                contact.append(v[1] - _ridge_envelope(sheets, v[0], v[2]))
            assert min(gaps) >= -1e-4, (a.name, w.name, min(gaps))
            assert min(contact) <= 0.01, (a.name, w.name, min(contact))
            checked += 1
    assert checked >= 36


def test_roof_sheets_rest_on_the_rafters(built):
    """Rafters sit under corrugation valleys: the sheet touches them (a lapping sheet may ride 6 mm up)."""
    for a in built:
        local = _local(a, _parts(a, "roof-sheet"))
        for r in _local(a, _parts(a, "rafter-")):
            lo, hi = g.bounds([r])
            x = (lo[0] + hi[0]) / 2
            for k in range(1, 8):
                z = lo[2] + (hi[2] - lo[2]) * k / 8
                gap = _top_surface_below(local, x, z) - _top_surface([r], x, z)
                assert -1e-6 <= gap <= 0.007, (a.name, r.name, z, gap)


def _top_surface_below(sheets, x, z):
    """Lowest downward-facing sheet face above (x, z)."""
    best = None
    for m in sheets:
        for face in m.faces:
            pts = [m.vertices[i] for i in face]
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


def test_frame_stack_posts_plates_rafters_touch(built):
    for a in built:
        posts = _local(a, _parts(a, "post-"))
        plates = _local(a, _parts(a, "plate-"))
        assert len(plates) == 2 and all(p.material == "pallet_wood" for p in plates)
        for p in posts:
            (plo, phi) = g.bounds([p])
            pz = (plo[2] + phi[2]) / 2
            plate = next(pl for pl in plates if g.bounds([pl])[0][2] <= pz <= g.bounds([pl])[1][2])
            assert phi[1] == pytest.approx(g.bounds([plate])[0][1], abs=1e-6), (a.name, p.name)
        rafters = _local(a, _parts(a, "rafter-"))
        assert len(rafters) >= 2
        for pl in plates:
            top = g.bounds([pl])[1][1]
            lo_r = min(min(v[1] for v in r.vertices if abs(v[2] - (g.bounds([pl])[0][2] + g.bounds([pl])[1][2]) / 2) < 0.1)
                       for r in rafters)
            assert lo_r >= top - 1e-6 and lo_r <= top + 0.02, (a.name, pl.name, lo_r, top)


def test_door_and_window(built):
    kinds = set()
    for a in built:
        door = a.meta["door"]
        kinds.add(door["kind"])
        if door["kind"] == "board":
            board = _parts(a, "door-board")
            assert board and board[0].material == "plywood"
            lo, hi = g.bounds(_local(a, board))
            assert hi[1] - lo[1] >= 1.8 and lo[1] >= 0.0
        else:
            curtain = _parts(a, "door-curtain")
            assert curtain and curtain[0].material.startswith("tarp_")
            assert _parts(a, "door-rod")
        assert _parts(a, "door-jamb")
        vinyl = _parts(a, "window-vinyl")
        assert vinyl and all(p.material == "tarp_green" for p in vinyl), a.name
        # the vinyl sits right behind the hole cut in the panels of its wall
        side = a.meta["window"]["side"]
        v_lo, v_hi = g.bounds(_local(a, vinyl))
        depths = [_depth(a, side, v) for v in _local(a, vinyl)[0].vertices]
        assert -0.01 <= min(depths) and max(depths) <= 1e-6
        assert _parts(a, "window-frame")
    assert kinds == {"board", "curtain"}


def test_chimney_leans_and_carries_soot(built):
    for a in built:
        pipe = _parts(a, "chimney-pipe")
        assert pipe
        top = a.meta["chimney_top"]
        world_top = (top[0] + a.origin[0], top[1], top[2] + a.origin[2])
        soot = [s for s in a.meta["sprays"] if s.center == pytest.approx(world_top)]
        assert soot, a.name
        assert soot[0].color == (0.2, 0.2, 0.2) and soot[0].strength == 0.6 and soot[0].radius == 0.8
        lean = a.meta["chimney_lean_deg"]
        assert 5.0 <= lean <= 16.0
        roof_hi = g.bounds(_parts(a, "roof-sheet"))[1][1]
        assert top[1] > roof_hi - 0.3


def test_ac_units_at_about_half(built):
    with_ac = [a for a in built if a.meta["ac"]]
    assert 3 <= len(with_ac) <= 9
    for a in built:
        parts = _parts(a, "ac-")
        assert bool(parts) == a.meta["ac"], a.name
        if parts:
            assert g.bounds(parts)[0][1] == pytest.approx(0.0, abs=1e-6)          # blocks on the ground
            body = _parts(a, "ac-body")
            blocks = _parts(a, "ac-block")
            assert g.bounds(body)[0][1] == pytest.approx(g.bounds(blocks)[1][1], abs=1e-6)


def test_rain_drum_stands_on_the_ground_under_the_low_eave(built):
    for a in built:
        drum = _parts(a, "drum-")
        assert drum, a.name
        lo, hi = g.bounds(drum)
        assert lo[1] == pytest.approx(0.0, abs=1e-6) and 0.8 <= hi[1] <= 1.0


def test_laundry_line_hangs_between_arms_with_cloths(built):
    for a in built:
        line = _parts(a, "laundry-line")
        assert len(line) == 1
        arms = _parts(a, "laundry-arm")
        assert len(arms) == 2
        # both ends of the line lie inside an arm
        pts = line[0].vertices
        for end in (pts[0], pts[-1]):
            assert any(all(lo - 0.02 <= end[k] <= hi + 0.02 for k, (lo, hi) in enumerate(zip(*g.bounds([arm]))))
                       for arm in arms), a.name
        # the arm roots touch the wall they are nailed to
        side = a.meta["laundry"]["side"]
        panels = _local(a, _parts(a, f"panel-{side}-"))
        wall_out = max(_depth(a, side, v) for p in panels for v in p.vertices)
        for arm in _local(a, arms):
            root = min(_depth(a, side, v) for v in arm.vertices)
            assert 0.0 < root <= wall_out + 1e-6, (a.name, arm.name)
        cloths = _parts(a, "laundry-cloth")
        assert 3 <= len(cloths) <= 6, a.name
        axis = a.meta["laundry"]["line"]           # world-space line axis points (origin-relative)
        for c in cloths:
            top_y = max(v[1] for v in c.vertices)
            tops = [v for v in c.vertices if v[1] > top_y - 0.05]
            for v in tops:
                # nearest axis point in the horizontal plane
                d, y = min((math.dist((v[0], v[2]), (p[0], p[2])), p[1]) for p in _densify(axis))
                assert d < 0.06 and -0.001 <= y - v[1] <= 0.01, (a.name, c.name, d, y - v[1])
            assert g.bounds([c])[0][1] >= 0.9


def _densify(points, n=20):
    out = []
    for p, q in zip(points, points[1:]):
        out.extend(tuple(p[k] + (q[k] - p[k]) * t / n for k in range(3)) for t in range(n))
    out.append(points[-1])
    return out


def test_wear_sprays_have_causes(built):
    for a in built:
        sprays = a.meta["sprays"]
        f = a.meta["frame"]
        grime = [s for s in sprays if s.center[1] < 0.3 and s.color == (0.5, 0.47, 0.42)]
        assert len(grime) >= 4, a.name                               # wall feet
        rust = [s for s in sprays if "corrugated_rust" in s.materials and s.center[1] > 1.5]
        assert rust, a.name                                          # runoff at the low eave
        for s in sprays:
            assert math.dist((s.center[0], s.center[2]), (a.origin[0], a.origin[2])) < 3.5
        assert f["yaw"] is not None


def test_shacks_keep_clear_of_each_other_and_the_rest(data, built):
    """Ground items and laundry use at most half of the gap to a neighbour; nothing enters other plots."""
    others = [_street_rect(s) for s in data["streets"]] + [_aabb(x) for x in [*data["towers"], *data["stalls"], *data["clubs"]]]
    boxes = []
    for a in built:
        world = _world(a, a.parts)
        low = [p for p in world if g.bounds([p])[1][1] < 2.0 and not p.name.startswith("panel-")]
        boxes.append([(p.name, g.bounds([p])) for p in low])
        lo, hi = g.bounds(world)
        for r in others:
            overlap = min(hi[0], r[2]) - max(lo[0], r[0]), min(hi[2], r[3]) - max(lo[2], r[1])
            assert not (overlap[0] > 0.0 and overlap[1] > 0.0), (a.name, r)
    for i in range(len(built)):
        for j in range(i + 1, len(built)):
            for n1, (l1, h1) in boxes[i]:
                for n2, (l2, h2) in boxes[j]:
                    ext = [min(h1[k], h2[k]) - max(l1[k], l2[k]) for k in range(3)]
                    assert min(ext) <= 0.0, (built[i].name, n1, built[j].name, n2)
    # roofs of neighbouring shacks do not collide either
    roofs = [g.bounds(_world(a, _parts(a, "roof-sheet"))) for a in built]
    for i in range(len(built)):
        for j in range(i + 1, len(built)):
            (l1, h1), (l2, h2) = roofs[i], roofs[j]
            ext = [min(h1[k], h2[k]) - max(l1[k], l2[k]) for k in (0, 2)]
            assert min(ext) <= 0.0, (built[i].name, built[j].name)


def test_sector_budget(built):
    assert sum(g.triangle_count(p) for a in built for p in a.parts) <= 60000


# Sloped or wall-sized parts whose AABBs cover their neighbours without the solids touching
# (panels, roof sheets, rafters, posts/plates, the chimney through the roof); contacts with them
# are measured exactly in the lap / roof / weight tests above. The pairs below are joints by design.
_CONTAINERS = ("panel-", "roof-sheet", "rafter-", "post-", "plate-", "chimney-")
_JOINTS = {("drum-body", "drum-rib"), ("laundry-arm", "laundry-line"), ("laundry-cloth", "laundry-line"),
           ("door-curtain", "door-rod"), ("door-rod", "door-rod-bracket"), ("door-curtain", "door-rod-bracket"),
           ("ac-body", "ac-pipe"), ("door-batten", "door-hardware")}


def _stem(name):
    parts = name.split("-")
    while parts and parts[-1].isdigit():
        parts.pop()
    return "-".join(parts)


def test_no_part_interpenetrates_another(built):
    for a in built:
        local = _local(a, a.parts)
        boxes = [g.bounds([p]) for p in local]
        for i, p in enumerate(local):
            if p.name.startswith(_CONTAINERS):
                continue
            for j in range(i + 1, len(local)):
                q = local[j]
                if q.name.startswith(_CONTAINERS) or tuple(sorted((_stem(p.name), _stem(q.name)))) in _JOINTS:
                    continue
                ext = [min(boxes[i][1][k], boxes[j][1][k]) - max(boxes[i][0][k], boxes[j][0][k]) for k in range(3)]
                assert min(ext) <= 2e-3, (a.name, p.name, q.name, ext)
