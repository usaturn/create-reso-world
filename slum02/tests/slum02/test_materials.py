from modeling.slum02 import materials as m
from modeling.slum02 import vcolor


def test_palette_size_and_kinds():
    assert 30 <= len(m.MATERIALS) <= 48
    kinds = {spec.kind for spec in m.MATERIALS.values()}
    assert kinds == {"vc", "neon", "holo"}


def test_every_noise_reference_exists_and_family_has_wear():
    for name, spec in m.MATERIALS.items():
        assert spec.noise is None or spec.noise in m.NOISES, name
        assert spec.family in vcolor.WEAR, name
        assert all(0.0 <= c <= 1.0 for c in spec.base_color), name
        if spec.kind in ("neon", "holo"):
            assert spec.emission is not None and spec.emission_strength > 0, name


def test_scroll_holo_materials_are_distinct_from_static():
    assert "holo_cyan_scroll" in m.MATERIALS and "holo_cyan" in m.MATERIALS
    assert m.MATERIALS["holo_cyan_scroll"] is not m.MATERIALS["holo_cyan"]


def test_noise_ranges():
    for spec in m.NOISES.values():
        assert 0 < spec.low < spec.high <= 1.0
        assert spec.size in (64, 128, 256, 512)
