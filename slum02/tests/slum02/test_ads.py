import math

import pytest

from modeling.slum02 import geometry as g
from modeling.slum02 import ads
from modeling.slum02.layout import build_layout


def test_one_or_two_objects_per_ad():
    data = build_layout()
    built = ads.ads_assemblies(data)
    spin = [a for a in data["ads"] if a["anim"] == "spin"]
    assert len(built) == len(data["ads"]) + len(spin)


def test_spin_panel_pivot_is_panel_centre():
    data = build_layout()
    for spec in [a for a in data["ads"] if a["anim"] == "spin"]:
        panel = next(a for a in ads.build_ad(spec) if a.name == f"{spec['id']}-panel")
        assert panel.origin == tuple(spec["position"])
        lo, hi = g.bounds(panel.parts)
        assert abs((lo[0] + hi[0]) / 2) < 0.05 and abs((lo[1] + hi[1]) / 2) < 0.05


def test_holo_material_only_on_holo_faces_and_scroll_consistent():
    for spec in build_layout()["ads"]:
        for a in ads.build_ad(spec):
            holo = [p for p in a.parts if p.material.startswith("holo_")]
            if a.name.endswith("-mount"):
                assert not holo
                continue
            assert holo and all(p.material == spec["material"] for p in holo)
            if spec["anim"] == "scroll":
                assert spec["material"].endswith("_scroll")


# --------------------------------------------------------------------------- extra invariants

TOL = 1e-6


@pytest.fixture(scope="module")
def data():
    return build_layout()


@pytest.fixture(scope="module")
def built(data):
    return ads.ads_assemblies(data)


def _local(a, spec):
    """Undo the baked yaw: parts back into the ad frame (+Z faces out, X across, wall at z=-0.12)."""
    yaw = math.radians(spec["rotation"])
    return [g.transformed(m, -yaw, (0.0, 0.0, 0.0)) for m in a.parts]


def _closed_consistent(mesh):
    directed = set()
    for face in mesh.faces:
        for x, y in zip(face, (*face[1:], face[0])):
            if (x, y) in directed:
                return False
            directed.add((x, y))
    return all((y, x) in directed for x, y in directed)


def test_names_sector_origin_and_determinism(data, built):
    expected = []
    for spec in data["ads"]:
        expected += [f"{spec['id']}-mount", f"{spec['id']}-panel"] if spec["anim"] == "spin" else [spec["id"]]
    assert [a.name for a in built] == expected
    by_id = {s["id"]: s for s in data["ads"]}
    for a in built:
        spec = by_id[a.name.removesuffix("-mount").removesuffix("-panel")]
        assert a.sector == "ads" and a.kind == "ad"
        assert a.origin == pytest.approx(tuple(spec["position"]), abs=1e-9)
    again = ads.ads_assemblies(build_layout())
    assert [(a.name, [(p.name, p.vertices) for p in a.parts]) for a in again] == \
           [(a.name, [(p.name, p.vertices) for p in a.parts]) for a in built]


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


def test_wall_ads_cover_their_occluder_box(data):
    """Panel+frame world AABB must contain the layout occluder ``occ-ad-NN`` (brief rule)."""
    occ = {o["id"]: o for o in data["occluders"]}
    for spec in [a for a in data["ads"] if a["kind"] == "wall"]:
        a = ads.build_ad(spec)[0]
        assert a.meta["occludes"] == [f"occ-{spec['id']}"]
        lo, hi = g.bounds([g.transformed(p, 0.0, a.origin) for p in a.parts])
        box = occ[f"occ-{spec['id']}"]
        assert all(l <= m + TOL for l, m in zip(lo, box["min"])), (a.name, lo, box["min"])
        assert all(h >= m - TOL for h, m in zip(hi, box["max"])), (a.name, hi, box["max"])


def test_mounted_ads_bracket_into_the_wall_and_stay_in_front(data):
    """Wall/vertical ads: plates anchor into the facade, nothing sinks more than 3 cm in."""
    for spec in [a for a in data["ads"] if a["kind"] in ("wall", "vertical")]:
        a = ads.build_ad(spec)[0]
        local = _local(a, spec)
        lo, hi = g.bounds(local)
        assert -0.15 <= lo[2] < -0.12 + TOL, (a.name, lo[2])     # plate buried <=3cm, touching the wall
        assert hi[2] <= 0.3, (a.name, hi[2])                    # modest projection off the facade
        arms = [p for p in local if p.name.startswith("frame") or "arm" in p.name]
        assert g.bounds(arms)[0][2] < -0.06, a.name             # arms reach back toward the wall


def test_holo_face_sits_just_in_front_of_the_frame(data):
    """ホロ面は枠の 0.03 手前: the gap between the frame front and the holo back is ~0.03."""
    for spec in data["ads"]:
        for a in ads.build_ad(spec):
            local = _local(a, spec)
            holo = [p for p in local if p.material.startswith("holo_")]
            if not holo:
                continue
            frame = [p for p in local if p.name.startswith("frame")]
            assert frame, a.name
            gap = g.bounds(holo)[0][2] - g.bounds(frame)[1][2]
            assert gap == pytest.approx(0.03, abs=0.011), (a.name, gap)


def test_float_projector_and_lens_sit_below_the_panel(data):
    for spec in [a for a in data["ads"] if a["kind"] == "float"]:
        for a in ads.build_ad(spec):
            if a.name.endswith("-panel"):
                continue
            local = _local(a, spec)
            lens = [p for p in local if p.material == "neon_cyan"]
            assert len(lens) == 1, a.name
            # the lens points up at the panel: its top stays below the canvas bottom
            assert g.bounds(lens)[1][1] < -spec["size"][1] / 2, a.name
            housing = [p for p in local if p.name.startswith("housing")]
            assert housing and g.bounds(housing)[1][1] < -spec["size"][1] / 2, a.name


def test_float_supports(data):
    """Pole-mounted floats plant a pole on the ground; cable-hung floats rise above the panel."""
    kinds = set()
    for spec in [a for a in data["ads"] if a["kind"] == "float"]:
        for a in ads.build_ad(spec):
            if a.name.endswith("-panel"):
                continue
            local = _local(a, spec)
            lo = g.bounds(local)[0]
            pole = [p for p in local if p.name == "pole"]
            cables = [p for p in local if p.name == "cables"]
            if pole:
                assert lo[1] == pytest.approx(-spec["position"][1], abs=0.02), a.name  # foot on the ground
                kinds.add("pole")
            if cables:
                top = g.bounds(cables)[1][1]
                assert top > spec["size"][1] / 2 + 2.0, a.name                        # drop vanishes overhead
                kinds.add("cable")
            assert pole or cables, a.name
            if spec["anim"] == "spin":
                assert not cables, a.name
    assert kinds == {"pole", "cable"}                                                  # both mounts exist


def test_spin_mount_and_panel_split(data):
    for spec in [a for a in data["ads"] if a["anim"] == "spin"]:
        pair = ads.build_ad(spec)
        assert [a.name for a in pair] == [f"{spec['id']}-mount", f"{spec['id']}-panel"]
        mount, panel = pair
        assert mount.origin == pytest.approx(tuple(spec["position"]))
        local_m = _local(mount, spec)
        local_p = _local(panel, spec)
        # the mount top (projector box) stays below the panel bottom edge
        assert g.bounds(local_m)[1][1] < -spec["size"][1] / 2, spec["id"]
        # the panel is the thin frame + the holo canvas centred on the pivot
        assert len(local_p) == 2 and {p.material for p in local_p} == {"steel_dark", spec["material"]}


def test_club_ads_clear_the_sign_board_and_entrance(data):
    """R18: club-mounted vertical ads must not cover the physical sign board or the door."""
    from modeling.slum02 import nightlife
    checked = 0
    for spec in data["clubs"]:
        ad = next((a for a in data["ads"] if a.get("mount") == spec["id"]), None)
        if ad is None:
            continue
        club = nightlife.build_club(spec, data)
        f = club.meta["frame"]
        p = g.rotate_y((ad["position"][0] - club.origin[0], 0.0, ad["position"][2] - club.origin[2]), -f["yaw"])
        ax0, ax1 = p[0] - ad["size"][0] / 2, p[0] + ad["size"][0] / 2
        board, door = f["board"], f["door"]
        assert ax1 <= board[0] + TOL or ax0 >= board[2] - TOL, (spec["id"], ax0, ax1, board)
        assert ax1 <= door[0] + TOL or ax0 >= door[2] - TOL, (spec["id"], ax0, ax1, door)
        # and it still hangs on the facade, clear of the edge columns (0.05 test pad)
        w, _d = nightlife._dims(spec)
        assert max(abs(ax0), abs(ax1)) <= w / 2 - nightlife.COL_W - 0.05 + TOL, spec["id"]
        checked += 1
    assert checked == 2


def test_sector_registration_and_budget(data, built):
    from modeling.slum02.sectors import sector_assemblies
    assert [x.name for x in sector_assemblies(data, "ads")] == [a.name for a in built]
    assert sum(g.triangle_count(p) for a in built for p in a.parts) <= 20000
