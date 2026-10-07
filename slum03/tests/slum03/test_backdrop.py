from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.geometry import merge_assembly


def test_multiple_arcologies_are_north_of_river():
    # 固定値の理由: 川の北に 500〜900 m 級のアーコロジーを 3 種類のシルエットで最低 3 棟置くことは、承認済みの
    # 設計仕様（2026-09-27-slum03-cyberpunk-slum-design.md の 4.5・9.1「景観」）の受入条件。
    towers = build_layout().select('arcology')
    assert len(towers) >= 3
    assert all(p.origin[2] - p.size[2] / 2 > 112.0 for p in towers)
    assert all(500.0 <= p.size[1] <= 900.0 for p in towers)
    assert {p.params['silhouette'] for p in towers} == {'terraced', 'gate', 'linked-towers'}


def test_north_has_real_void_and_linked_spans_not_scaled_solid_boxes():
    north = sector_assemblies(build_layout(), 'backdrop-north')
    by_key = {a.meta['placement_key']: a for a in north}
    assert {'arcology-terraces', 'arcology-gate', 'arcology-towers'} <= by_key.keys()
    assert len([a for a in north if a.kind == 'highrise']) >= 8
    assert all(80 <= max(v[1] for part in a.parts for v in part.vertices) <= 200
               for a in north if a.kind == 'highrise')
    for key in ('arcology-terraces', 'arcology-gate', 'arcology-towers'):
        a = by_key[key]
        assert len(a.parts) >= 7
        assert max(v[1] for p in a.parts for v in p.vertices) >= 500
        assert max(v[2] for p in a.parts for v in p.vertices) - min(v[2] for p in a.parts for v in p.vertices) >= 75
        assert len(merge_assembly(a).materials) >= 2
    gate = by_key['arcology-gate']
    # A traversable silhouette gap at the middle-height lower half, not a facade painted on a box.
    assert not any(min(v[0] for v in p.vertices) < 0 < max(v[0] for v in p.vertices)
                   and min(v[1] for v in p.vertices) < 180 < max(v[1] for v in p.vertices)
                   for p in gate.parts)
    assert any('link' in p.name for p in by_key['arcology-towers'].parts)


def test_west_south_background_is_low_city_with_roof_layers():
    city = sector_assemblies(build_layout(), 'backdrop-west-south')
    assert len(city) >= 12
    assert all(a.kind == 'low-city' and a.meta.get('collider') is None for a in city)
    assert all(max(v[1] for p in a.parts for v in p.vertices) <= 65 for a in city)
    assert any('roof' in p.name for a in city for p in a.parts)
    assert any('lean' in p.name for a in city for p in a.parts)
    assert any('sign' in p.name for a in city for p in a.parts)


def test_west_floors_face_west_viewpoint_not_hidden_side_wall():
    west = [a for a in sector_assemblies(build_layout(), 'backdrop-west-south')
            if a.name.startswith('west-city-')]
    for a in west:
        strips = [p for p in a.parts if p.name.startswith('facade-recess')]
        assert strips
        assert all(min(v[0] for v in p.vertices) > 6 for p in strips)
        assert all(max(v[2] for v in p.vertices)-min(v[2] for v in p.vertices) > 8
                   for p in strips)


def test_gate_crown_is_supported_by_dwellings_at_each_allowed_height():
    from dataclasses import replace
    from modeling.slum03.geometry import bounds
    # These are genuine mesh bounds at the minimum, default and maximum
    # allowed arcology heights, not the declared Placement envelope.
    for width, height, depth in ((140, 500, 80), (180, 820, 100), (220, 900, 120)):
        base = build_layout()
        layout = replace(base, placements=tuple(
            replace(p, size=(width, height, depth)) if p.key == 'arcology-gate' else p
            for p in base.placements))
        gate = next(a for a in sector_assemblies(layout, 'backdrop-north')
                    if a.name == 'arcology-gate')
        meshes = {p.name: p for p in gate.parts}
        crown_min, crown_max = bounds([meshes['gate-crown']])
        assert crown_max[1] == height
        assert max(v[1] for part in gate.parts for v in part.vertices) <= height
        for side in (-1, 1):
            dwelling_min, dwelling_max = bounds([meshes[f'upper-dwelling-{side}']])
            pier_max = bounds([meshes[f'pier-{side}']])[1]
            assert dwelling_min[1] <= pier_max[1] + 1e-6
            assert dwelling_max[1] + 1e-6 >= crown_min[1]
            assert dwelling_min[0] < crown_max[0] and dwelling_max[0] > crown_min[0]
            assert dwelling_min[2] < crown_max[2] and dwelling_max[2] > crown_min[2]
        # Lower monumental gap stays empty while the high crown is supported.
        assert not any(min(v[0] for v in p.vertices) < 0 < max(v[0] for v in p.vertices)
                       and min(v[1] for v in p.vertices) < 180 < max(v[1] for v in p.vertices)
                       for p in gate.parts)
