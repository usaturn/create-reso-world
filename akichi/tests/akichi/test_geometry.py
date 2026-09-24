"""geometry/uv 基盤の動作検証。"""
from __future__ import annotations

from modeling.akichi import geometry, uv


def test_box_is_deterministic_and_manifold():
    a = geometry.box("b", (0, 0, 0), (2, 3, 4), "concrete_dark")
    b = geometry.box("b", (0, 0, 0), (2, 3, 4), "concrete_dark")
    assert a == b
    assert len(a.vertices) == 8 and len(a.faces) == 6
    # 各辺がちょうど2面に共有される = 閉じた多面体
    from collections import Counter
    edge_count = Counter()
    for face in a.faces:
        for i, j in zip(face, face[1:] + face[:1]):
            edge_count[tuple(sorted((i, j)))] += 1
    assert all(count == 2 for count in edge_count.values())


def test_cylinder_axis_and_segments():
    c = geometry.cylinder("c", (0, 0, 0), 0.5, 2.0, 8, "dark_metal", axis="Y")
    ys = [v[1] for v in c.vertices]
    assert min(ys) == -1.0 and max(ys) == 1.0
    assert len(c.faces) == 10  # 側面 8 quad + 上下 cap 2 n-gon


def test_prism_roof_shape():
    p = geometry.prism("roof", (0, 0, 0), (4, 1.5, 6), "corrugated")
    assert len(p.vertices) == 6
    ridge = max(v[1] for v in p.vertices)
    assert ridge == 0.75  # h/2


def test_beveled_box_rejects_bad_input():
    try:
        geometry.beveled_box("x", (0, 0, 0), (1, 1, 0), 0.1, "rust")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_metric_face_uvs_pass_audit():
    points = [(0, 0, 0), (2, 0, 0), (2, 0, 3), (0, 0, 3)]
    normal = (0, 1, 0)
    uvs = uv.metric_face_uvs(points, normal, uv_per_meter=0.5)
    assert len(uvs) == 4
    # 三角分割して監査: 問題なし
    for tri in ((0, 1, 2), (0, 2, 3)):
        issues = uv.uv_triangle_issues(
            [points[i] for i in tri], [uvs[i] for i in tri], normal, 0.5, 1
        )
        assert issues == []
