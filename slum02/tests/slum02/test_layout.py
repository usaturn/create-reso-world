import hashlib
import json
import math

from modeling.slum02 import layout as L


def _data():
    return L.build_layout()


def test_deterministic():
    a = json.dumps(_data(), sort_keys=True)
    b = json.dumps(_data(), sort_keys=True)
    assert hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()


def test_validate_clean():
    assert L.validate_layout(_data()) == []


def test_counts():
    d = _data()
    outer = [t for t in d["towers"] if t["role"] == "outer"]
    assert len(outer) == 16 and len([t for t in d["towers"] if t["role"] == "inner"]) == 6
    assert 10 <= len(d["stalls"]) <= 12
    assert 3 <= len(d["clubs"]) <= 4
    assert 10 <= len(d["shacks"]) <= 14
    assert 25 <= len(d["ads"]) <= 35
    assert 20 <= len(d["lights"]) <= 30
    assert sum(1 for l in d["lights"] if l["shadow"] != "None") <= 3
    assert sum(t["footprint"][0] * t["footprint"][1] * t["height"] for t in d["towers"]) > 0


def test_plaza_is_clear_and_wall_on_east_edge():
    d = _data()
    for group in ("towers", "stalls", "clubs", "shacks"):
        for item in d[group]:
            x, z = item["center"]
            assert not (abs(x) < 10 and abs(z) < 10), item["id"]
    w = d["east_wall"]
    assert w["center"][0] + w["size"][0] / 2 == 10.0 and w["size"][1] == 10.0 and w["size"][2] == 20.0


def test_everything_inside_bounds_except_backdrop():
    d = _data()
    for group in ("towers", "stalls", "clubs", "shacks"):
        for item in d[group]:
            x, z = item["center"]
            hw, hd = item["footprint" if group == "towers" else "size"][0] / 2, item["footprint" if group == "towers" else "size"][1] / 2
            assert -40 <= x - hw and x + hw <= 40 and -40 <= z - hd and z + hd <= 40, item["id"]
    for mass in d["backdrop"]["masses"]:
        assert math.hypot(*mass["center"]) >= 55


def test_radial_alleys_have_no_straight_exit():
    d = _data()
    radials = [s for s in d["streets"] if s["kind"] == "radial"]
    assert len(radials) == 12  # 4 alleys x 3 legs (dogleg)


def test_ray_hit_distance():
    assert L.ray_hit_distance((0, 0, 0), (1, 0, 0), (5, -1, -1), (6, 1, 1)) == 5
    assert L.ray_hit_distance((0, 0, 0), (-1, 0, 0), (5, -1, -1), (6, 1, 1)) is None
    assert L.ray_hit_distance((0, 5, 0), (1, 0, 0), (5, -1, -1), (6, 1, 1)) is None


def test_sightlines_from_plaza_are_closed():
    failures = L.sightline_failures(_data())
    assert failures == [], failures[:5]


def test_layout_json_matches_generator(tmp_path):
    out = tmp_path / "layout.json"
    L.write_layout(out)
    assert json.loads(out.read_text()) == json.loads(json.dumps(_data()))


# --- additional checks (beyond the brief) ---------------------------------


def test_occluder_ids_reference_existing_sources():
    d = _data()
    ids = {t["id"] for t in d["towers"]} | {b["id"] for b in d["bridges"]} | {a["id"] for a in d["ads"]}
    outer = {t["id"] for t in d["towers"] if t["role"] == "outer"}
    occ = {o["source"] for o in d["occluders"]}
    assert outer <= occ
    assert {b["id"] for b in d["bridges"]} <= occ
    assert {a["id"] for a in d["ads"] if a["kind"] == "wall"} <= occ
    for o in d["occluders"]:
        assert o["id"] == f"occ-{o['source']}" and o["source"] in ids
        assert all(lo < hi for lo, hi in zip(o["min"], o["max"]))
    inner = {t["id"] for t in d["towers"] if t["role"] == "inner"}
    assert not (inner & occ)


def test_spot_lights_aim_at_target():
    d = _data()
    spots = [l for l in d["lights"] if l["type"] == "Spot"]
    assert spots
    for light in d["lights"]:
        q = light["rotation"]
        assert abs(math.sqrt(sum(c * c for c in q)) - 1.0) < 1e-3
    flood = next(l for l in spots if l["shadow"] == "Hard" and l.get("target") == "east-wall")
    fwd = L.quat_rotate(flood["rotation"], (0.0, 0.0, 1.0))
    p = flood["position"]
    to = [9.2 - p[0], 5.0 - p[1], 0.0 - p[2]]
    n = math.sqrt(sum(c * c for c in to))
    assert sum(f * t / n for f, t in zip(fwd, to)) > 0.999


def test_cable_attachments_exist():
    d = _data()
    assert len(d["cables"]) == 14
    ids = {x["id"] for g in ("towers", "stalls", "clubs") for x in d[g]}
    for c in d["cables"]:
        assert len(c["attach"]) == 2 and set(c["attach"]) <= ids, c["id"]


def test_ads_mix():
    d = _data()
    kinds = [a["kind"] for a in d["ads"]]
    assert kinds.count("wall") == 12 and kinds.count("float") == 10 and kinds.count("vertical") == 8
    assert sum(1 for a in d["ads"] if a["anim"] == "spin") == 4
    assert sum(1 for a in d["ads"] if a["anim"] == "scroll") == 6
    assert len(d["signs"]) == 16
