import math

import pytest

from modeling.slum02 import geometry as g


def _closed(mesh):
    """Every undirected edge is shared by exactly two faces."""
    edges = {}
    for face in mesh.faces:
        for a, b in zip(face, (*face[1:], face[0])):
            key = (min(a, b), max(a, b))
            edges[key] = edges.get(key, 0) + 1
    return all(count == 2 for count in edges.values())


def _signed_volume(mesh):
    total = 0.0
    for face in mesh.faces:
        p0 = mesh.vertices[face[0]]
        for i in range(1, len(face) - 1):
            p1, p2 = mesh.vertices[face[i]], mesh.vertices[face[i + 1]]
            total += (p0[0] * (p1[1] * p2[2] - p1[2] * p2[1])
                      - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0])
                      + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])) / 6
    return total


def test_subdivided_box_is_closed_outward_and_fine():
    m = g.subdivided_box("b", (0, 1, 0), (4, 2, 1), 0.5, "concrete_mid")
    assert _closed(m)
    assert _signed_volume(m) == pytest.approx(8.0, rel=1e-6)
    for face in m.faces:
        pts = [m.vertices[i] for i in face]
        for a, b in zip(pts, (*pts[1:], pts[0])):
            assert math.dist(a, b) <= 0.5 + 1e-9


def test_wall_with_openings_recesses_not_holes():
    m = g.wall_with_openings("w", 6.0, 3.0, 0.4, [(-1.0, 1.0, 1.0, 2.2)], 0.25, 1.0, "concrete_mid")
    assert _closed(m)
    lo, hi = g.bounds([m])
    assert lo == pytest.approx((-3.0, 0.0, -0.2))
    assert hi == pytest.approx((3.0, 3.0, 0.2))
    recessed = [v for v in m.vertices if abs(v[2] - (0.2 - 0.25)) < 1e-9]
    assert recessed, "opening back face must sit recess metres behind the front"
    assert _signed_volume(m) == pytest.approx(6 * 3 * 0.4 - 2.0 * 1.2 * 0.25, rel=1e-6)


def test_wall_openings_validated():
    with pytest.raises(ValueError):
        g.wall_with_openings("w", 2.0, 2.0, 0.3, [(-1.5, 0.5, 0.5, 1.0)], 0.1, 1.0, "m")
    with pytest.raises(ValueError):
        g.wall_with_openings("w", 2.0, 2.0, 0.3, [(-0.5, 0.5, 0.5, 1.0)], 0.3, 1.0, "m")


def test_catenary_sags_and_hits_endpoints():
    pts = g.catenary((0, 5, 0), (10, 5, 0), 1.5, 16)
    assert pts[0] == pytest.approx((0, 5, 0)) and pts[-1] == pytest.approx((10, 5, 0))
    assert min(p[1] for p in pts) == pytest.approx(3.5, abs=1e-6)
    assert len(pts) == 17


def test_tube_is_closed():
    m = g.tube("t", g.catenary((0, 5, 0), (4, 6, 1), 0.6, 8), 0.03, 6, "cable")
    assert _closed(m)


def test_rotate_y_quarter_turn():
    assert g.rotate_y((1.0, 0.0, 0.0), math.pi / 2) == pytest.approx((0.0, 0.0, -1.0))


def test_rotate_xyz_axes():
    assert g.rotate_xyz((1.0, 0.0, 0.0), 0.0, 0.0, math.pi / 2) == pytest.approx((0.0, 1.0, 0.0))
    assert g.rotate_xyz((0.0, 1.0, 0.0), math.pi / 2, 0.0, 0.0) == pytest.approx((0.0, 0.0, 1.0))
    assert g.rotate_xyz((1.0, 0.0, 0.0), 0.0, math.pi / 2, 0.0) == pytest.approx(g.rotate_y((1.0, 0.0, 0.0), math.pi / 2))


def test_open_wall_drops_back_and_ends():
    closed = g.wall_with_openings("w", 6.0, 3.0, 0.4, [(-1.0, 1.0, 1.0, 2.2)], 0.25, 1.0, "m")
    opened = g.wall_with_openings("w", 6.0, 3.0, 0.4, [(-1.0, 1.0, 1.0, 2.2)], 0.25, 1.0, "m", closed=False)
    assert len(opened.faces) < len(closed.faces)
    assert all(v[2] > -0.2 + 1e-9 for f in opened.faces for v in (opened.vertices[i] for i in f))


def test_merge_assembly_groups_materials_in_first_seen_order():
    a = g.Assembly("stall", "stall-01", "market", (5.0, 0.0, 5.0), [
        g.box("p1", (0, 0.5, 0), (1, 1, 1), "rust"),
        g.box("p2", (2, 0.5, 0), (1, 1, 1), "tarp_blue"),
        g.box("p3", (4, 0.5, 0), (1, 1, 1), "rust"),
    ])
    merged = g.merge_assembly(a)
    assert merged.name == "stall-01"
    assert merged.materials == ("rust", "tarp_blue")
    assert len(merged.faces) == 18 and len(merged.face_materials) == 18
    assert merged.face_materials[:6] == (0,) * 6 and merged.face_materials[6:12] == (1,) * 6
    assert len(merged.vertices) == 24
    assert g.bounds([g.mesh("x", merged.vertices, merged.faces, "m")])[0] == pytest.approx((-0.5, 0.0, -0.5))
