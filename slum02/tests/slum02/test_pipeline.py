"""Task 14: unified manifest built by modeling.slum02.pipeline.

``merge_bundles`` (rename / reuse / prune / reference rewrite / asset source
repaths) is covered by synthetic bundles under ``tmp_path`` so the invariants
hold in CI without the real ``content/slum02`` bundles.
"""
import json
import math

import pytest

from modeling.slum02 import pipeline


def _bundle(dir_, name):
    dir_.mkdir(parents=True)
    (dir_ / "model.apply.json").write_text(json.dumps({
        "schemaVersion": "1", "ownership": {"key": f"blender_{name}"},
        "slot": {"key": "root", "name": name, "parent": "Root"},
        "assets": {"mesh_a": {"kind": "mesh", "source": "mesh_a.mesh.json"}},
        "components": [],
        "children": [{"slot": {"key": "object_a", "name": "a"}, "components": [
            {"key": "mesh_a", "type": "FrooxEngine.StaticMesh", "fields": {"URL": "$asset:mesh_a"}}]}],
    }), encoding="utf-8")


# --------------------------------------------------------------------- ported merge invariants

SHARED_MATERIAL_FIELDS = {"AlbedoColor": [0.1, 0.2, 0.3, 1.0], "Metallic": 0.0,
                          "Smoothness": 0.5, "EmissiveColor": [0.0, 0.0, 0.0, 1.0]}
GROUND_MATERIAL_FIELDS = {"AlbedoColor": [0.4, 0.4, 0.4, 1.0], "Metallic": 0.0,
                          "Smoothness": 0.1, "EmissiveColor": [0.0, 0.0, 0.0, 1.0]}
PLAZA_MATERIAL_FIELDS = {"AlbedoColor": [0.5, 0.4, 0.2, 1.0], "Metallic": 0.0,
                         "Smoothness": 0.3, "EmissiveColor": [0.0, 0.0, 0.0, 1.0]}
DRUM_ASSET = {"kind": "mesh", "source": "mesh-drum.mesh.json"}


def _synthetic_bundle(name: str, ownership: str, assets: dict, children: list) -> dict:
    return {
        "schemaVersion": "1",
        "ownership": {"key": ownership},
        "slot": {"key": "root", "name": name, "parent": "Root"},
        "assets": assets,
        "components": [],
        "children": children,
    }


def _provider_slot(key: str, component_key: str, fields: dict) -> dict:
    return {
        "slot": {"key": key, "name": component_key},
        "components": [{"key": component_key, "type": "FrooxEngine.PBS_Metallic", "fields": fields}],
    }


def _drum_slot() -> dict:
    return {
        "slot": {"key": "object-drum", "name": "drum"},
        "components": [
            {"key": "mesh-drum", "type": "FrooxEngine.StaticMesh", "fields": {"URL": "$asset:mesh-drum"}},
            {"key": "renderer-drum", "type": "FrooxEngine.MeshRenderer",
             "fields": {"Mesh": "$component:mesh-drum", "Materials": ["$component:mat-shared"]}},
        ],
    }


def _synthetic_bundles(sectors) -> dict[str, dict]:
    ground = _synthetic_bundle(
        "Ground", "blender_Ground_synthetic", {"mesh-drum": DRUM_ASSET},
        [
            _drum_slot(),
            {"slot": {"key": "providers", "name": "Blender_Providers"}, "components": [],
             "children": [
                 _provider_slot("provider_mat-shared", "mat-shared", SHARED_MATERIAL_FIELDS),
                 _provider_slot("provider_mat-ground", "mat-ground", GROUND_MATERIAL_FIELDS)]},
        ])
    plaza = _synthetic_bundle(
        "Plaza", "blender_Plaza_synthetic", {"mesh-drum": DRUM_ASSET},
        [
            _drum_slot(),
            {"slot": {"key": "providers", "name": "Blender_Providers"}, "components": [],
             "children": [
                 # identical provider is reused, not redeclared
                 _provider_slot("provider_mat-shared", "mat-shared", SHARED_MATERIAL_FIELDS),
                 _provider_slot("provider_mat-plaza", "mat-plaza", PLAZA_MATERIAL_FIELDS)]},
        ])
    empty = _synthetic_bundle("Empty", "blender_Empty_synthetic", {}, [])
    bundles = {sector: empty for sector in sectors}
    bundles["ground"] = ground
    bundles["plaza"] = plaza
    return bundles


def _walk_slots(nodes: list) -> list:
    found = []
    for node in nodes:
        found.append(node)
        found.extend(_walk_slots(node.get("children", [])))
    return found


def _all_components(manifest: dict) -> list:
    return [c for node in _walk_slots(manifest["children"]) for c in node.get("components", [])]


def _slot_keys(manifest: dict) -> list:
    return [node["slot"]["key"] for node in _walk_slots(manifest["children"])]


def _node_by_slot_key(manifest: dict, key: str) -> dict:
    for node in _walk_slots(manifest["children"]):
        if node["slot"]["key"] == key:
            return node
    raise AssertionError(f"slot {key!r} not found in merged manifest")


def _references(manifest: dict) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    def visit(value) -> None:
        if isinstance(value, str):
            for prefix, kind in (("$asset:", "asset"), ("$component:", "component"), ("$slot:", "slot")):
                if value.startswith(prefix):
                    found.append((kind, value[len(prefix):]))
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for item in value.values():
                visit(item)

    visit(manifest.get("assets", {}))
    visit(manifest["children"])
    return found


def _assert_references_resolve(manifest: dict) -> None:
    slots = set(_slot_keys(manifest)) | {manifest["slot"]["key"]}
    components = {c["key"] for c in _all_components(manifest)}
    assets = set(manifest["assets"])
    for kind, key in _references(manifest):
        target = {"asset": assets, "component": components, "slot": slots}[kind]
        assert key in target, f"unresolved ${kind}:{key}"


@pytest.fixture()
def synthetic_manifest(tmp_path, monkeypatch):
    sectors = ("ground", "plaza", "market")
    monkeypatch.setattr(pipeline, "SECTORS", sectors)
    for sector, bundle in _synthetic_bundles(sectors).items():
        directory = tmp_path / f"{sector}-v1"
        directory.mkdir()
        (directory / "model.apply.json").write_text(json.dumps(bundle), encoding="utf-8")
    return pipeline.merge_bundles(tmp_path)


def test_merge_uniquifies_colliding_keys(synthetic_manifest):
    slot_keys = _slot_keys(synthetic_manifest)
    assert slot_keys.count("object-drum") == 1
    assert slot_keys.count("plaza-object-drum") == 1
    assert slot_keys.count("providers") == 1
    assert slot_keys.count("plaza-providers") == 1
    component_keys = [c["key"] for c in _all_components(synthetic_manifest)]
    for key in ("mesh-drum", "renderer-drum"):
        assert component_keys.count(key) == 1
        assert component_keys.count(f"plaza-{key}") == 1
    # slot と component は同一の一意性名前空間を共有する
    assert len(set(slot_keys) | set(component_keys)) == len(slot_keys) + len(component_keys)


def test_merge_reuses_shared_provider(synthetic_manifest):
    components = _all_components(synthetic_manifest)
    assert [c["key"] for c in components].count("mat-shared") == 1
    plaza_drum = _node_by_slot_key(synthetic_manifest, "plaza-object-drum")
    renderer = next(c for c in plaza_drum["components"] if c["key"] == "plaza-renderer-drum")
    assert renderer["fields"]["Materials"] == ["$component:mat-shared"]


def test_merge_prunes_emptied_provider_slot(synthetic_manifest):
    slot_keys = _slot_keys(synthetic_manifest)
    assert "provider_mat-shared" in slot_keys
    assert "plaza-provider_mat-shared" not in slot_keys
    plaza_providers = _node_by_slot_key(synthetic_manifest, "plaza-providers")
    assert [c["slot"]["key"] for c in plaza_providers["children"]] == ["provider_mat-plaza"]


def test_merge_references_follow_renames(synthetic_manifest):
    plaza_drum = _node_by_slot_key(synthetic_manifest, "plaza-object-drum")
    mesh, renderer = plaza_drum["components"]
    assert mesh["key"] == "plaza-mesh-drum"
    assert mesh["fields"]["URL"] == "$asset:plaza-mesh-drum"
    assert renderer["fields"]["Mesh"] == "$component:plaza-mesh-drum"
    assert synthetic_manifest["assets"]["mesh-drum"]["source"] == "ground-v1/mesh-drum.mesh.json"
    assert synthetic_manifest["assets"]["plaza-mesh-drum"]["source"] == "plaza-v1/mesh-drum.mesh.json"
    _assert_references_resolve(synthetic_manifest)


def test_missing_bundle_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SECTORS", ("ground", "plaza"))
    _bundle(tmp_path / "ground-v1", "Ground")
    with pytest.raises(ValueError, match="missing sector bundle"):
        pipeline.merge_bundles(tmp_path)


# --------------------------------------------------------------------- build_unified_manifest root shape


def _count_json_nodes(value) -> int:
    n = 1
    if isinstance(value, dict):
        n += sum(_count_json_nodes(v) for v in value.values())
    elif isinstance(value, list):
        n += sum(_count_json_nodes(v) for v in value)
    return n


def test_build_unified_manifest_root_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SECTORS", ("ground", "plaza"))
    _bundle(tmp_path / "ground-v1", "Ground")
    _bundle(tmp_path / "plaza-v1", "Plaza")
    m = pipeline.build_unified_manifest(tmp_path)
    assert m["schemaVersion"] == "1"
    # 固定値の理由: 所有キーと所有ルート（Root 直下の Slum02_Slum）は、既存の state
    # （.resoloop/slum02/state/slum02.json）と Resonite 上の適用済みコンテンツを結び付ける。
    # 変わると所有範囲を別物として扱い、prune の対象を誤る。
    assert m["ownership"]["key"] == "slum02"
    assert m["slot"] == {"key": "root", "name": "Slum02_Slum", "parent": "Root",
                         "position": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}
    # limits.expandedNodes = ceil(実測ノード数 × 1.2)（limits 自身は計測に含めない）
    measured = _count_json_nodes({k: v for k, v in m.items() if k != "limits"})
    assert m["limits"]["expandedNodes"] == math.ceil(measured * 1.2)
    # manifest の存在テストは、manifest 内に実在する Slot だけを指す
    targets = {a["target"] for t in m["tests"] for a in t["assertions"]}
    slot_refs = {f"$slot:{key}" for key in [m["slot"]["key"], *_slot_keys(m)]}
    assert targets and targets <= slot_refs, targets - slot_refs
    # postprocess が走っていること（追加分のグループ Slot がルート直下に出る）
    child_keys = {c["slot"]["key"] for c in m["children"]}
    assert {"textures", "lights", "colliders", "signs"} <= child_keys


def test_build_unified_manifest_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SECTORS", ("ground", "plaza"))
    _bundle(tmp_path / "ground-v1", "Ground")
    _bundle(tmp_path / "plaza-v1", "Plaza")
    a = json.dumps(pipeline.build_unified_manifest(tmp_path), sort_keys=True, ensure_ascii=False)
    b = json.dumps(pipeline.build_unified_manifest(tmp_path), sort_keys=True, ensure_ascii=False)
    assert a == b
