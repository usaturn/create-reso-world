import pytest
from modeling.slum03 import uv


def test_metric_uv_on_asymmetric_triangle():
    points = [(0, 0, 0), (3, 0, 0), (0, 0, 2)]
    uvs = uv.metric_face_uvs(points, (0, -1, 0))
    assert uv.uv_triangle_issues(points, uvs, (0, -1, 0)) == []
    assert abs((uvs[1][0]-uvs[0][0])*(uvs[2][1]-uvs[0][1]) - (uvs[1][1]-uvs[0][1])*(uvs[2][0]-uvs[0][0])) == pytest.approx(1.5)


def test_uv_degenerate_face_rejected():
    with pytest.raises(ValueError, match='zero|degenerate'):
        uv.metric_face_uvs([(0, 0, 0), (1, 0, 0), (2, 0, 0)], (0, 0, 1))
    assert 'zero UV area' in uv.uv_triangle_issues([(0, 0, 0), (2, 0, 0), (0, 2, 0)], [(0, 0)]*3, (0, 0, 1))
