"""props.py（屋台・小屋・風俗店・広告・ケーブル・瓦礫・車両・ジャンク山）の動作検証。"""
from __future__ import annotations

import pytest

from modeling.akichi import layout, props
from modeling.akichi.materials import MATERIALS


def test_stall_deterministic_and_grounded():
    spec = {"id": "stall-01", "center": [0, 0], "rotation": 0, "kind": "junk", "awning": "tarp_blue"}
    a = props.build_stall(spec, seed=1)
    b = props.build_stall(spec, seed=1)
    assert [p.name for p in a.parts] == [p.name for p in b.parts]
    (minx, miny, minz), _ = a.bounds
    assert abs(miny) < 0.05
    assert "lantern" in a.attachments


def test_shack_uses_wall_mix():
    spec = {"id": "shack-01", "center": [0, 0], "footprint": [3, 4], "height": 2.8,
            "rotation": 5, "wall_mix": ["corrugated", "plywood"]}
    shack = props.build_shack(spec, seed=2)
    used = {p.material for p in shack.parts}
    assert "corrugated" in used and "plywood" in used


def test_club_has_neon_and_sign_anchor():
    spec = {"id": "club-01", "center": [0, 0], "rotation": 0, "width": 5,
            "neon": "neon_pink", "sign_text": "テスト"}
    club = props.build_club(spec, seed=3)
    assert "neon_pink" in {p.material for p in club.parts}
    assert "sign" in club.attachments


def test_ad_kinds():
    for kind in ("wall", "holo", "rooftop", "lantern"):
        spec = {"id": f"ad-{kind}", "kind": kind, "position": [0, 5, 0], "rotation": 0,
                "size": [2, 1.5], "color": "neon_cyan", "frame": "dark_metal"}
        ad = props.build_ad(spec, seed=4)
        assert any(p.material in ("neon_cyan", "holo_panel", "warm_light") for p in ad.parts), kind


def test_cable_sags_between_endpoints():
    spec = {"id": "cable-01", "from": [0, 8, 0], "to": [10, 6, 0], "sag": 1.5, "radius": 0.04}
    cable = props.build_cable(spec)
    ys = [v[1] for p in cable.parts for v in p.vertices]
    assert min(ys) <= 5.6  # 中央で端点(y=8/6)より sag=1.5 分下がる（中点 ≈ 5.5）


def test_rubble_prototypes_are_small():
    protos = props.rubble_prototypes()
    assert len(protos) == 3
    for proto in protos:
        span = max(max(v[i] for v in proto.vertices) - min(v[i] for v in proto.vertices) for i in range(3))
        assert span < 1.2, proto.name


# --- 追加検証（エッジケース耐久化・layout 全件スモーク） -------------------------


def test_props_use_only_palette_materials():
    """全ビルダーが生成するマテリアルは MATERIALS の27キーに限定される。"""
    assemblies = _all_layout_props()
    assemblies += [
        props.build_vehicle_husk(seed=11),
        props.build_junk_pile(seed=12, radius=1.4),
    ]
    for assembly in assemblies:
        for part in assembly.parts:
            assert part.material in MATERIALS, f"{assembly.name}: {part.material}"


def test_layout_props_smoke():
    """layout の全 spec から Assembly が例外なく組み上がり、parts 総数が予算内に収まる。"""
    assemblies = _all_layout_props()
    total = sum(len(assembly.parts) for assembly in assemblies)
    assert total < 3000
    for assembly in assemblies:
        if assembly.kind in ("stall", "shack", "club"):
            low, _ = assembly.bounds
            assert abs(low[1]) < 0.05, assembly.name
        if assembly.kind == "ad":
            # ホロパネルは街路に自立するので地面下にジオメトリを残さない
            world_low = min(v[1] for part in assembly.parts for v in part.vertices) + assembly.origin[1]
            assert world_low > -0.01, assembly.name


def test_props_are_deterministic_for_every_builder():
    """同一 seed → 同一頂点列（dict/set 順に依存しない）。"""
    specs = layout.build_layout()
    for spec in specs["stalls"]:
        _assert_same_vertices(props.build_stall(spec, seed=5), props.build_stall(spec, seed=5))
    for spec in specs["shacks"]:
        _assert_same_vertices(props.build_shack(spec, seed=5), props.build_shack(spec, seed=5))
    for spec in specs["nightlife"]:
        _assert_same_vertices(props.build_club(spec, seed=5), props.build_club(spec, seed=5))
    for spec in specs["ads"]:
        _assert_same_vertices(props.build_ad(spec, seed=5), props.build_ad(spec, seed=5))
    for spec in specs["cables"]:
        _assert_same_vertices(props.build_cable(spec), props.build_cable(spec))
    _assert_same_vertices(props.build_vehicle_husk(seed=6), props.build_vehicle_husk(seed=6))
    _assert_same_vertices(props.build_junk_pile(seed=6, radius=1.0), props.build_junk_pile(seed=6, radius=1.0))
    first, second = props.rubble_prototypes(), props.rubble_prototypes()
    assert [(p.name, p.vertices, p.faces) for p in first] == [(p.name, p.vertices, p.faces) for p in second]


def test_cable_rejects_degenerate_specs():
    """退化入力（同一端点かつ sag なし・負 sag・半径 0・2要素ベクトル）は ValueError。"""
    degenerate = [
        {"id": "c", "from": [0, 8, 0], "to": [0, 8, 0], "sag": 0.0, "radius": 0.04},
        {"id": "c", "from": [0, 8, 0], "to": [4, 6, 0], "sag": -1.0, "radius": 0.04},
        {"id": "c", "from": [0, 8, 0], "to": [4, 6, 0], "sag": 1.0, "radius": 0.0},
        {"id": "c", "from": [0, 8, 0], "to": [4, 6], "sag": 1.0, "radius": 0.04},
    ]
    for spec in degenerate:
        with pytest.raises(ValueError):
            props.build_cable(spec)


def test_junk_pile_budget_and_rejects_bad_radius():
    pile = props.build_junk_pile(seed=7, radius=1.2)
    assert 15 <= len(pile.parts) <= 30
    assert pile.parts == [] or min(v[1] for part in pile.parts for v in part.vertices) >= -0.01
    with pytest.raises(ValueError):
        props.build_junk_pile(seed=7, radius=0.0)


def test_vehicle_husk_length_and_grounding():
    husk = props.build_vehicle_husk(seed=3)
    low, high = husk.bounds
    assert abs(low[1]) < 0.02
    assert 3.5 <= high[0] - low[0] <= 4.6  # 全長 4m 程度
    wheels = [p for p in husk.parts if "wheel" in p.name]
    assert len(wheels) == 4


def test_shack_roof_ridge_follows_long_axis():
    """稜線は常に長い方の水平軸に沿って伸びる（prism の既定は Z 稜線）。"""
    for footprint, axis3, axis2 in (((4.0, 2.6), 0, 0), ((2.6, 4.0), 2, 1)):
        spec = {"id": "shack-01", "center": [0, 0], "footprint": list(footprint), "height": 2.6,
                "rotation": 0, "wall_mix": ["corrugated", "plywood"]}
        roof = next(p for p in props.build_shack(spec, seed=8).parts if p.name == "roof")
        low = [min(v[i] for v in roof.vertices) for i in range(3)]
        high = [max(v[i] for v in roof.vertices) for i in range(3)]
        assert high[axis3] - low[axis3] >= footprint[axis2]  # オーバーハング
        ridge = [v for v in roof.vertices if abs(v[1] - high[1]) < 1e-9]
        assert len(ridge) == 2
        # 稜線の2頂点が長い方の軸の両端まで届いている
        assert abs(ridge[0][axis3] - ridge[1][axis3]) == pytest.approx(high[axis3] - low[axis3])


def _assert_same_vertices(first, second):
    assert [(p.name, p.vertices, p.faces) for p in first.parts] == [
        (p.name, p.vertices, p.faces) for p in second.parts
    ]


def _all_layout_props():
    data = layout.build_layout()
    assemblies = [props.build_stall(spec, seed=250925) for spec in data["stalls"]]
    assemblies += [props.build_shack(spec, seed=250925) for spec in data["shacks"]]
    assemblies += [props.build_club(spec, seed=250925) for spec in data["nightlife"]]
    assemblies += [props.build_ad(spec, seed=250925) for spec in data["ads"]]
    assemblies += [props.build_cable(spec) for spec in data["cables"]]
    return assemblies