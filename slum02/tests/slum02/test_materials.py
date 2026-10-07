from modeling.slum02 import materials as m
from modeling.slum02 import vcolor


def test_palette_kinds():
    # 固定値の理由: postprocess.convert_material は holo を FresnelMaterial に、それ以外を
    # PBS_VertexColorMetallic に変換する。新しい種類を足すと、黙って頂点カラー素材として変換される。
    kinds = {spec.kind for spec in m.MATERIALS.values()}
    assert kinds == {"vc", "neon", "holo"}


def test_every_noise_reference_exists_and_family_has_wear():
    for name, spec in m.MATERIALS.items():
        assert spec.noise is None or spec.noise in m.NOISES, name
        assert spec.family in vcolor.WEAR, name
        assert all(0.0 <= c <= 1.0 for c in spec.base_color), name
        if spec.kind in ("neon", "holo"):
            assert spec.emission is not None and spec.emission_strength > 0, name


def test_noise_ranges():
    for spec in m.NOISES.values():
        assert 0 < spec.low < spec.high <= 1.0
        assert spec.size in (64, 128, 256, 512)
