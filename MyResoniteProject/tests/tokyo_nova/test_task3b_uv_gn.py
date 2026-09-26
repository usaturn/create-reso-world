"""Small UV examples that distinguish valid tiling from misleading UV0 presence."""
from __future__ import annotations

from modeling.tokyo_nova.uv import metric_face_uvs, uv_triangle_issues


def test_uv_audit_accepts_metric_uvs_on_a_nonsquare_face() -> None:
    face = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    uvs = metric_face_uvs(face, (0.0, 0.0, 1.0))
    assert uv_triangle_issues(face[:3], uvs[:3], (0.0, 0.0, 1.0)) == []
    assert uv_triangle_issues((face[0], face[2], face[3]), (uvs[0], uvs[2], uvs[3]), (0.0, 0.0, 1.0)) == []


def test_uv_audit_rejects_collapsed_stretched_and_flipped_corners() -> None:
    face = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 1.0, 0.0)]
    assert "zero UV area" in uv_triangle_issues(face, ((1, 0), (0, 1), (1, 0)), (0, 0, 1))
    assert "metric distortion" in uv_triangle_issues(face, ((0, 0), (1, 0), (1, 2)), (0, 0, 1))
    assert "reversed orientation" in uv_triangle_issues(face, ((0, 0), (0, 0.5), (1, 0.5)), (0, 0, 1))
