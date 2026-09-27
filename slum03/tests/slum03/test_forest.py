"""Regressions: forest must be readable near road and remain exportable."""
from modeling.slum03.layout import build_layout
from modeling.slum03.sectors import sector_assemblies
from modeling.slum03.geometry import merge_assembly


def test_near_trees_have_distinct_trunks_branches_and_natural_crowns():
    trees = [a for a in sector_assemblies(build_layout(), 'forest') if a.kind == 'tree']
    assert len(trees) >= 12
    assert len({tuple(round(v, 1) for v in a.origin) for a in trees}) == len(trees)
    assert len({round(max(v[1] for p in a.parts for v in p.vertices), 1) for a in trees}) >= 3
    for tree in trees:
        assert tree.origin[0] >= 100
        assert {'trunk', 'branch', 'crown'} <= {p.name.split('-')[0] for p in tree.parts}
        assert {'bark', 'leaf_deep', 'leaf_moss'} & {p.material for p in tree.parts}
        assert merge_assembly(tree).faces
        assert tree.meta.get('collider') is None


def test_forest_sector_does_not_export_just_a_flat_screen():
    assemblies = sector_assemblies(build_layout(), 'forest')
    assert len(assemblies) >= 12
    assert any(a.origin[0] < 120 for a in assemblies)
    assert max(a.origin[2] for a in assemblies) > 35
    assert min(a.origin[2] for a in assemblies) < -35
    assert all(a.sector == 'forest' for a in assemblies)


def test_crown_faces_point_outward_for_correct_lighting_and_uvs():
    from modeling.slum03.forest import crown
    from modeling.slum03.geometry import signed_volume
    assert signed_volume(crown('sample', 5, 10, 'leaf_deep')) > 0
