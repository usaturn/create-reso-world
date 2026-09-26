import copy

import pytest

from modeling.slum02 import postprocess as pp
from modeling.slum02.layout import build_layout
from modeling.slum02.materials import MATERIALS, NOISES


def _mini_manifest():
    return {
        "schemaVersion": "1", "ownership": {"key": "slum02"},
        "slot": {"key": "root", "name": "Slum02_Slum", "parent": "Root"},
        "assets": {}, "components": [],
        "children": [{
            "slot": {"key": "sector-ads", "name": "Slum02_Ads"},
            "children": [
                {"slot": {"key": "object_ad-03-panel_1234abcd", "name": "ad-03-panel"}, "components": [
                    {"key": "renderer_x", "type": "FrooxEngine.MeshRenderer",
                     "fields": {"Mesh": "$component:mesh_x", "Materials": ["$component:mat_material_Slum02_holo_cyan_scroll_deadbeef", "$component:mat_material_Slum02_concrete_raw_0badf00d"]}}]},
                {"slot": {"key": "providers", "name": "Blender_Providers"}, "components": [
                    {"key": "mat_material_Slum02_holo_cyan_scroll_deadbeef", "type": "FrooxEngine.PBS_Metallic",
                     "fields": {"AlbedoColor": [0.1, 0.2, 0.2, 1.0], "Metallic": 0.0, "Smoothness": 0.9, "EmissiveColor": [0.05, 0.85, 1.0, 1]}},
                    {"key": "mat_material_Slum02_concrete_raw_0badf00d", "type": "FrooxEngine.PBS_Metallic",
                     "fields": {"AlbedoColor": [0.6, 0.6, 0.58, 1.0], "Metallic": 0.0, "Smoothness": 0.08, "EmissiveColor": [0, 0, 0, 1]}},
                ]},
            ],
        }],
    }


def _all_components(node, out=None):
    out = [] if out is None else out
    out.extend(node.get("components", []))
    for c in node.get("children", []):
        _all_components(c, out)
    return out


def _all_slots(node, out=None):
    out = [] if out is None else out
    out.append(node["slot"])
    for c in node.get("children", []):
        _all_slots(c, out)
    return out


def test_material_name_parsing():
    assert pp.material_name("mat_material_Slum02_holo_cyan_scroll_deadbeef") == "holo_cyan_scroll"
    assert pp.material_name("mat_material_Slum02_concrete_raw_0badf00d") == "concrete_raw"
    assert pp.material_name("renderer_x") is None


def test_no_pbs_metallic_left_and_types_converted():
    m = pp.postprocess(_mini_manifest(), build_layout(), {})
    comps = _all_components(m)
    assert not [c for c in comps if c["type"] == "FrooxEngine.PBS_Metallic"]
    by_key = {c["key"]: c for c in comps}
    holo = by_key["mat_material_Slum02_holo_cyan_scroll_deadbeef"]
    assert holo["type"] == "FrooxEngine.FresnelMaterial" and holo["fields"]["BlendMode"] == "Additive"
    concrete = by_key["mat_material_Slum02_concrete_raw_0badf00d"]
    assert concrete["type"] == "FrooxEngine.PBS_VertexColorMetallic"
    assert concrete["fields"]["VertexColorTarget"] == "Albedo"
    assert concrete["fields"]["VertexColorInterpolationSpace"] == pp.VERTEX_COLOR_SPACE
    assert concrete["fields"]["AlbedoTexture"] == "$component:tex-noise-concrete"


def test_every_component_reference_resolves():
    m = pp.postprocess(_mini_manifest(), build_layout(), {})
    comps = _all_components(m)
    keys = {c["key"] for c in comps}
    def refs(v):
        if isinstance(v, str) and v.startswith(("$component:", "$member:")):
            yield v.split(":", 1)[1].split(".")[0]
        elif isinstance(v, list):
            for x in v:
                yield from refs(x)
        elif isinstance(v, dict):
            for x in v.values():
                yield from refs(x)
    missing = {r for c in comps for r in refs(c.get("fields", {}))} - keys - {"mesh_x"}
    assert not missing, missing


def test_scroll_panner_and_spinner_targets():
    m = pp.postprocess(_mini_manifest(), build_layout(), {})
    comps = _all_components(m)
    panners = [c for c in comps if c["type"] == "FrooxEngine.Panner2D"]
    assert {p["fields"]["_target"] for p in panners} == {
        "$member:mat_material_Slum02_holo_cyan_scroll_deadbeef.NearTextureOffset",
        "$member:mat_material_Slum02_holo_cyan_scroll_deadbeef.FarTextureOffset"}
    spinners = [c for c in comps if c["type"] == "FrooxEngine.Spinner"]
    assert [s["fields"]["_target"] for s in spinners] == ["$slot-member:object_ad-03-panel_1234abcd.Rotation"]


def test_lights_colliders_and_shadow_budget():
    layout = build_layout()
    m = pp.postprocess(_mini_manifest(), layout, {})
    comps = _all_components(m)
    lights = [c for c in comps if c["type"] == "FrooxEngine.Light"]
    assert len(lights) == len(layout["lights"])
    assert sum(1 for l in lights if l["fields"]["ShadowType"] != "None") <= 3
    assert sum(1 for c in comps if c["type"] == "FrooxEngine.BoxCollider") >= 40


def test_postprocess_is_idempotent():
    layout = build_layout()
    once = pp.postprocess(_mini_manifest(), layout, {})
    twice = pp.postprocess(copy.deepcopy(once), layout, {})
    assert once == twice


# --------------------------------------------------------------------- edge tests


def test_holo_fields_exact():
    """FresnelMaterial 変換の全フィールドを emission から検算する。"""
    spec = MATERIALS["holo_cyan_scroll"]
    e = list(spec.emission)
    comp = {"key": "mat_material_Slum02_holo_cyan_scroll_deadbeef", "type": "FrooxEngine.PBS_Metallic",
            "fields": {"AlbedoColor": [0.1, 0.2, 0.2, 1.0], "Metallic": 0.0, "Smoothness": 0.9,
                       "EmissiveColor": [0.05, 0.85, 1.0, 1]}}
    out = pp.convert_material(comp, "holo_cyan_scroll")
    assert out["key"] == comp["key"] and out["type"] == "FrooxEngine.FresnelMaterial"
    f = out["fields"]
    assert f["NearColor"] == pytest.approx([c * 0.35 for c in e] + [0.25])
    assert f["FarColor"] == pytest.approx([min(1.0, c * 1.2) for c in e] + [0.85])
    assert f["Exponent"] == 1.6 and f["GammaCurve"] == 1.0
    assert f["BlendMode"] == "Additive" and f["Sidedness"] == "Double" and f["ZWrite"] == "Off"
    assert f["UseVertexColors"] is False
    assert f["NearTexture"] == "$component:tex-noise-holo" == f["FarTexture"]
    assert f["NearTextureScale"] == [1.0, 4.0] == f["FarTextureScale"]


def test_vc_material_keeps_source_fields_and_no_noise_material_has_no_texture():
    comp = {"key": "mat_material_Slum02_rubber_1234abcd", "type": "FrooxEngine.PBS_Metallic",
            "fields": {"AlbedoColor": [0.02, 0.02, 0.02, 1.0], "Metallic": 0.0, "Smoothness": 0.15,
                       "EmissiveColor": [0, 0, 0, 1], "DroppedExtra": 9}}
    out = pp.convert_material(comp, "rubber")  # rubber has no noise spec
    f = out["fields"]
    assert f["AlbedoColor"] == [0.02, 0.02, 0.02, 1.0]
    assert f["Metallic"] == 0.0 and f["Smoothness"] == 0.15 and f["EmissiveColor"] == [0, 0, 0, 1]
    assert f["TextureScale"] == list(MATERIALS["rubber"].texture_scale)
    assert "AlbedoTexture" not in f
    assert "DroppedExtra" not in f  # ブリーフに列挙されたフィールドのみ引き継ぐ


def test_neon_material_also_becomes_vertex_color():
    comp = {"key": "mat_material_Slum02_neon_cyan_00abcdef", "type": "FrooxEngine.PBS_Metallic",
            "fields": {"AlbedoColor": [0.01, 0.18, 0.2, 1.0], "Metallic": 0.0, "Smoothness": 0.65,
                       "EmissiveColor": [0.3, 5.4, 6.0, 1]}}
    out = pp.convert_material(comp, "neon_cyan")
    assert out["type"] == "FrooxEngine.PBS_VertexColorMetallic"
    assert out["fields"]["EmissiveColor"] == [0.3, 5.4, 6.0, 1]
    assert "AlbedoTexture" not in out["fields"]


def test_unknown_material_name_raises():
    comp = {"key": "k", "type": "FrooxEngine.PBS_Metallic", "fields": {}}
    with pytest.raises(KeyError):
        pp.convert_material(comp, "no_such_material")


def test_textures_slot_has_all_noise_components():
    slot = pp.texture_slot()
    assert slot["slot"]["key"] == "textures"
    by_key = {c["key"]: c for c in slot["components"]}
    assert set(by_key) == {f"tex-noise-{name}" for name in NOISES}
    concrete = by_key["tex-noise-concrete"]
    n = NOISES["concrete"]
    f = concrete["fields"]
    assert f["Size"] == [n.size, n.size] and f["Seed"] == n.seed
    assert f["Monochrome"] is True
    assert f["MonochromeMin"] == [n.low, n.low, n.low, 1.0]
    assert f["MonochromeMax"] == [n.high, n.high, n.high, 1.0]
    assert f["WrapModeU"] == "Repeat" and f["WrapModeV"] == "Repeat" and f["FilterMode"] == "Anisotropic"
    assert f["Mipmaps"] is True


def test_spinner_only_on_ad_panel_slots():
    manifest = _mini_manifest()
    manifest["children"][0]["children"].append(
        {"slot": {"key": "object_ad-04-mount_9999eeee", "name": "ad-04-mount"}, "components": []})
    m = pp.postprocess(manifest, build_layout(), {})
    spinners = [c for c in _all_components(m) if c["type"] == "FrooxEngine.Spinner"]
    assert [s["fields"]["_target"] for s in spinners] == ["$slot-member:object_ad-03-panel_1234abcd.Rotation"]
    assert spinners[0]["fields"]["_speed"] == [0.0, 30.0, 0.0]


def test_panner_fields_exact():
    m = pp.postprocess(_mini_manifest(), build_layout(), {})
    panners = {c["fields"]["_target"]: c["fields"] for c in _all_components(m) if c["type"] == "FrooxEngine.Panner2D"}
    key = "mat_material_Slum02_holo_cyan_scroll_deadbeef"
    assert panners[f"$member:{key}.NearTextureOffset"]["_speed"] == [0.0, 0.35]
    assert panners[f"$member:{key}.FarTextureOffset"]["_speed"] == [0.0, 0.2]
    assert all(f["_repeat"] == [1.0, 1.0] for f in panners.values())


def test_light_slots_spot_angle_and_transform():
    layout = build_layout()
    m = pp.postprocess(_mini_manifest(), layout, {})
    lights = {c["key"]: c for c in _all_components(m) if c["type"] == "FrooxEngine.Light"}
    layout_by_id = {l["id"]: l for l in layout["lights"]}
    slots = {s["key"]: s for s in _all_slots(m) if s["key"].startswith("light-")}
    for lid, l in layout_by_id.items():
        comp = lights[f"{lid}-light"]
        f = comp["fields"]
        assert f["LightType"] == l["type"] and f["Intensity"] == l["intensity"]
        assert f["Color"] == list(l["color"]) and f["Range"] == l["range"] and f["ShadowType"] == l["shadow"]
        if l["type"] == "Spot":
            assert f["SpotAngle"] == l["spot_angle"]
        else:
            assert "SpotAngle" not in f
        assert slots[lid]["position"] == list(l["position"])
        assert slots[lid]["rotation"] == list(l["rotation"])


def test_collider_count_and_ground_box():
    layout = build_layout()
    m = pp.postprocess(_mini_manifest(), layout, {})
    comps = _all_components(m)
    colliders = [c for c in comps if c["type"] == "FrooxEngine.BoxCollider"]
    # 地面1 + タワー22 + 東壁1 + クラブ4 + 屋台12 + 小屋12 + 機械3 + 車1 + 柱5
    assert len(colliders) == 1 + 22 + 1 + 4 + 12 + 12 + 3 + 1 + 5
    assert all(c["fields"]["Type"] == "Static" and c["fields"]["CharacterCollider"] is True for c in colliders)
    slots = {s["key"]: s for s in _all_slots(m)}
    ground = next(c for c in comps if c["key"] == "collider-ground-box")
    assert ground["fields"]["Size"] == [80.0, 0.2, 80.0]
    assert slots["collider-ground"]["position"] == [0.0, 0.0, 0.0]
    # 全タワー分のコライダーがある
    for t in layout["towers"]:
        assert f"collider-{t['id']}" in slots


def test_sign_slots_text_renderers():
    layout = build_layout()
    m = pp.postprocess(_mini_manifest(), layout, {})
    texts = [c for c in _all_components(m) if c["type"] == "FrooxEngine.TextRenderer"]
    assert len(texts) == len(layout["signs"])  # font-mesh なので東壁フォールバックは増えない
    assert all(t["fields"]["HorizontalAlign"] == "Center" and t["fields"]["VerticalAlign"] == "Middle"
               for t in texts)


def test_spray_text_renderer_fallback_only_when_requested():
    layout = build_layout()
    reports = {"plaza": {"spray_art": {"method": "text-renderer"}}}
    m = pp.postprocess(_mini_manifest(), layout, reports)
    texts = [c for c in _all_components(m) if c["type"] == "FrooxEngine.TextRenderer"]
    assert len(texts) == len(layout["signs"]) + 2
    by_size = sorted(t["fields"]["Size"] for t in texts[-2:])
    assert by_size == [2.9, 3.0]
