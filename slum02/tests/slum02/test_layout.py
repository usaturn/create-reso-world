import json
import math

from modeling.slum02 import layout as L


def _data():
    return L.build_layout()


def test_deterministic():
    # build_layout() は組み立てた結果をキャッシュするため、2 回呼んでも同じ文字列を読み直すだけになる。
    # キャッシュを通さずに組み立て直し、同じシードから同じ layout になることを確かめる。
    assert L._assemble() == _data()


def test_validate_clean():
    assert L.validate_layout(_data()) == []


def test_counts():
    # 固定値の理由: 承認済みの設計仕様（2026-09-26-slum02-cyberpunk-slum-design.md の「街の構成」
    # 「予算の目安」）と Plan の予算目安（影ありの Light は 3 灯以下）が定める範囲。
    # 範囲の外へ出す変更は、仕様の変更として扱う。
    d = _data()
    assert 10 <= len(d["stalls"]) <= 12
    assert 3 <= len(d["clubs"]) <= 4
    assert 10 <= len(d["shacks"]) <= 14
    assert 25 <= len(d["ads"]) <= 35
    assert 20 <= len(d["lights"]) <= 30
    assert sum(1 for l in d["lights"] if l["shadow"] != "None") <= 3


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
