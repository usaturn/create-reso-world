from modeling.akichi import buildings, layout


def _tower_spec(**overrides):
    base = {"id": "tower-01", "center": [0.0, 30.0], "footprint": [10.0, 10.0],
            "height": 20.0, "rotation": 0, "setback_height": 14.0, "setback_inset": 1.5,
            "broken_corner": True, "corner_size": 3.0}
    base.update(overrides)
    return base


def test_tower_is_deterministic():
    a = buildings.build_tower(_tower_spec(), seed=1)
    b = buildings.build_tower(_tower_spec(), seed=1)
    assert [p.name for p in a.parts] == [p.name for p in b.parts]
    assert a.parts[0].vertices == b.parts[0].vertices


def test_tower_bounds_match_spec():
    spec = _tower_spec()
    tower = buildings.build_tower(spec, seed=1)
    (minx, miny, minz), (maxx, maxy, maxz) = tower.bounds
    assert abs(miny) < 0.01  # 地面接地
    assert maxy <= spec["height"] + 3.5  # 屋上構造物込みの上限
    assert maxx - minx <= spec["footprint"][0] + 1.0
    assert maxz - minz <= spec["footprint"][1] + 1.0


def test_tower_has_windows_and_seams():
    tower = buildings.build_tower(_tower_spec(), seed=2)
    kinds = {p.name.rsplit("-", 1)[0] for p in tower.parts}
    assert any("window" in k for k in kinds)
    assert any("seam" in k for k in kinds)
    materials_used = {p.material for p in tower.parts}
    assert "glass_dark" in materials_used and "concrete_stained" in materials_used


def test_broken_corner_adds_rebar():
    tower = buildings.build_tower(_tower_spec(broken_corner=True), seed=3)
    rebar = [p for p in tower.parts if "rebar" in p.name]
    assert len(rebar) >= 4
    plain = buildings.build_tower(_tower_spec(broken_corner=False), seed=3)
    assert len([p for p in plain.parts if "rebar" in p.name]) == 0


def test_triangle_budget_per_tower():
    tower = buildings.build_tower(_tower_spec(), seed=4)
    triangles = sum(len(p.faces) - 2 for p in tower.parts)  # 概算（quad 主体）
    assert triangles < 9000


def test_perimeter_wall_segments():
    wall = buildings.build_perimeter_wall(seed=5)
    assert wall.kind == "perimeter"
    assert len(wall.parts) >= 20