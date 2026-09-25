import pytest

from modeling.slum02 import geometry as g
from modeling.slum02 import vcolor


def _merged(part):
    return g.merge_assembly(g.Assembly("t", "t", "s", (0.0, 0.0, 0.0), [part]))


def test_noise_deterministic_and_bounded():
    a = [vcolor.value_noise3(x * 0.37, 1.1, -x * 0.21, 5) for x in range(200)]
    b = [vcolor.value_noise3(x * 0.37, 1.1, -x * 0.21, 5) for x in range(200)]
    assert a == b
    assert all(0.0 <= v <= 1.0 for v in a)
    assert max(a) - min(a) > 0.3


def test_ground_grime_darkens_bottom():
    wall = _merged(g.subdivided_box("w", (0, 3, 0), (4, 6, 0.4), 0.5, "concrete_raw"))
    cols = vcolor.vertex_colors(wall, (0.0, 0.0, 0.0), 7)
    low = [c[0] for v, c in zip(wall.vertices, cols) if v[1] < 0.3]
    high = [c[0] for v, c in zip(wall.vertices, cols) if 2.5 < v[1] < 3.5]
    assert sum(low) / len(low) < sum(high) / len(high) * 0.85


def test_rust_only_on_metal_family():
    concrete = _merged(g.subdivided_box("c", (0, 1, 0), (3, 2, 3), 0.4, "concrete_raw"))
    cols = vcolor.vertex_colors(concrete, (0.0, 0.0, 0.0), 7)
    # concrete has rust = 0, so red/blue ratio stays near neutral
    assert all(c[2] > 0 and c[0] / c[2] < 1.25 for c in cols)
    metal = _merged(g.subdivided_box("m", (0, 1, 0), (3, 2, 3), 0.4, "steel_bare"))
    mcols = vcolor.vertex_colors(metal, (0.0, 0.0, 0.0), 7)
    assert max(c[0] / c[2] for c in mcols) > 1.2


def test_spray_tints_only_near_center():
    wall = _merged(g.subdivided_box("w", (0, 5, 0), (10, 10, 0.5), 0.5, "concrete_raw"))
    spray = vcolor.Spray((0.0, 5.0, 0.25), 2.0, (1.0, 0.2, 0.2), 0.8)
    base = vcolor.vertex_colors(wall, (0.0, 0.0, 0.0), 7)
    cols = vcolor.vertex_colors(wall, (0.0, 0.0, 0.0), 7, sprays=[spray])
    for v, c0, c1 in zip(wall.vertices, base, cols):
        dist = ((v[0]) ** 2 + (v[1] - 5) ** 2 + (v[2] - 0.25) ** 2) ** 0.5
        if dist > 2.0:
            assert c1 == pytest.approx(c0)
        if dist < 0.5:
            assert c1[1] < c0[1] * 0.6


def test_colors_clamped_rgba():
    part = g.subdivided_box("p", (0, 1, 0), (2, 2, 2), 0.5, "paint_yellow_faded")
    cols = vcolor.vertex_colors(_merged(part), (3.0, 0.0, -2.0), 1)
    assert all(len(c) == 4 and c[3] == 1.0 and all(0.05 <= x <= 1.3 for x in c[:3]) for c in cols)
