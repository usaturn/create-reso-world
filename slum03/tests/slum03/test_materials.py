from modeling.slum03 import geometry as g, vcolor


def test_vertex_wear_is_deterministic_and_grimy_at_ground():
    m = g.merge_assembly(g.Assembly('wall', 'wall', 'plaza', (0, 0, 0),
                                      [g.subdivided_box('wall', (0, 3, 0), (4, 6, .4), .5, 'concrete_raw')]))
    a = vcolor.vertex_colors(m, (0, 0, 0), 7)
    assert a == vcolor.vertex_colors(m, (0, 0, 0), 7)
    low = [c[0] for p, c in zip(m.vertices, a) if p[1] < .3]
    high = [c[0] for p, c in zip(m.vertices, a) if 2.5 < p[1] < 3.5]
    assert sum(low)/len(low) < sum(high)/len(high) * .85
    assert all(c[3] == 1 for c in a)
