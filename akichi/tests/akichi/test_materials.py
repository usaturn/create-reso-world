from modeling.akichi import materials


def test_palette_is_complete_and_export_safe():
    mats = materials.build_materials()
    for name, values in mats.items():
        assert len(values["base_color"]) == 4, name
        assert 0.0 <= values["metallic"] <= 1.0, name
        assert 0.0 <= values["roughness"] <= 1.0, name
        allowed = {"base_color", "metallic", "roughness", "emission", "emission_strength"}
        assert set(values) <= allowed, f"{name} has unsupported keys {set(values) - allowed}"
        if "emission" in values:
            assert values["emission_strength"] > 0, name


def test_neon_colors_are_emissive():
    mats = materials.build_materials()
    for name in materials.NEON_COLORS:
        assert "emission" in mats[name], name
        assert max(mats[name]["emission"][:3]) >= 0.9, f"{name} is not vivid"


def test_build_materials_returns_fresh_copy():
    a = materials.build_materials()
    a["rust"]["base_color"] = (0, 0, 0, 0)
    b = materials.build_materials()
    assert b["rust"]["base_color"] != (0, 0, 0, 0)
