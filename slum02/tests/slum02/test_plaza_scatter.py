from modeling.slum02 import geometry as g
from modeling.slum02 import plaza
from modeling.slum02.layout import build_layout


def test_prototypes_sit_on_base_with_limited_sink():
    protos = plaza.rubble_prototypes()
    assert len(protos) == 8
    for cls, mesh, name in protos:
        assert cls in plaza.SCATTER_CLASSES
        lo, hi = g.bounds([mesh])
        height = hi[1] - lo[1]
        assert -0.101 * height <= lo[1] <= 0.0, name
        above = sum(1 for v in mesh.vertices if v[1] > 0) / len(mesh.vertices)
        assert above >= 0.6, name


def test_scatter_surface_avoids_keepouts():
    data = build_layout()
    surf = plaza.scatter_surface(data)
    fx, fz = data["plaza_features"]["fire_barrel"]
    for face in surf.faces:
        cx = sum(surf.vertices[i][0] for i in face) / len(face)
        cz = sum(surf.vertices[i][2] for i in face) / len(face)
        assert (cx - fx) ** 2 + (cz - fz) ** 2 > 1.2 ** 2
        assert abs(cx) < 10 and abs(cz) < 10
        for x0, z0, x1, z1 in data["plaza_features"]["pits"]:
            assert not (x0 <= cx <= x1 and z0 <= cz <= z1)
    area = sum(0.25 for _ in surf.faces)
    assert 200 <= area <= 360


def test_expected_instance_budget():
    area = sum(0.25 for _ in plaza.scatter_surface(build_layout()).faces)
    expected = sum(d * area for d, _, _ in plaza.SCATTER_CLASSES.values())
    assert 700 <= expected <= 1300
