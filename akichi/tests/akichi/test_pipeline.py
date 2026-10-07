"""Task 9: unified manifest built by modeling.akichi.pipeline.

The structural assertions mirror the brief; asset reference integrity is checked
by ``resoloop validate`` (offline), not by these tests.

``_merge_bundle_slots`` (rename / reuse / prune / reference rewrite) is covered
by synthetic two-sector bundles under ``tmp_path`` so the invariants hold in CI
without the real ``content/akichi`` bundles.
"""
import json
from pathlib import Path

import pytest
from modeling.akichi import pipeline
from modeling.akichi.layout import build_layout

# --- 実 bundle 依存のテスト ---------------------------------------------------


def _real_manifest_or_skip() -> dict:
    """実 content/akichi の統合 manifest。無いチェックアウトでは skip する。"""
    manifest_path = Path("content/akichi") / pipeline.UNIFIED_NAME
    if not manifest_path.is_file():
        pytest.skip(f"real manifest not available: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def test_manifest_structure(tmp_path):
    # 実 bundle がある場合はそれを使い、CI 的に最小構成でも検証できること
    manifest = pipeline.build_unified_manifest(Path("content/akichi"))
    # 固定値の理由: 所有キーと所有ルート（Root 直下の Akichi_Slum）は、既存の state と
    # Resonite 上の適用済みコンテンツを結び付ける。変わると所有範囲を別物として扱い、prune の対象を誤る。
    assert manifest["ownership"]["key"] == "akichi"
    assert manifest["slot"]["name"] == "Akichi_Slum"
    assert manifest["slot"]["parent"] == "Root"
    sectors = {child["slot"]["key"] for child in manifest["children"]}
    assert sectors == {f"sector-{s}" for s in ("ground", "vacant", "towers", "market", "shacks", "nightlife", "ads")}
    # asset 参照の整合は resoloop validate（Step 5）で検査するため、ここでは構造のみ確認


def test_signs_attached():
    """layout の看板が 1 枚ずつ、同じ文言の TextRenderer として manifest に入る。"""
    manifest = pipeline.build_unified_manifest(Path("content/akichi"))
    texts = [
        component["fields"]["Text"]
        for component in _all_components(manifest)
        if component["type"] == "FrooxEngine.TextRenderer"
    ]
    assert sorted(texts) == sorted(sign["text"] for sign in build_layout()["signs"])


def test_manifest_is_deterministic():
    a = json.dumps(pipeline.build_unified_manifest(Path("content/akichi")), sort_keys=True, ensure_ascii=False)
    b = json.dumps(pipeline.build_unified_manifest(Path("content/akichi")), sort_keys=True, ensure_ascii=False)
    assert a == b


def test_manifest_references_resolve():
    """実 manifest の $slot:/$component:/$asset: が全て実在キーを指す。"""
    manifest = _real_manifest_or_skip()
    _assert_references_resolve(manifest)


# --- 合成 bundle による _merge_bundle_slots の不変条件 -------------------------


SHARED_MATERIAL_FIELDS = {"BaseColor": [0.1, 0.2, 0.3, 1.0], "Metallic": 0.0, "Roughness": 0.8}
GROUND_MATERIAL_FIELDS = {"BaseColor": [0.4, 0.4, 0.4, 1.0], "Metallic": 0.0, "Roughness": 0.9}
VACANT_MATERIAL_FIELDS = {"BaseColor": [0.5, 0.4, 0.2, 1.0], "Metallic": 0.0, "Roughness": 0.7}

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
    """衝突する slot/component キーと、共有 provider を指す参照を持つスロット。"""
    return {
        "slot": {"key": "object-drum", "name": "drum"},
        "components": [
            {"key": "mesh-drum", "type": "FrooxEngine.StaticMesh", "fields": {"URL": "$asset:mesh-drum"}},
            {
                "key": "renderer-drum",
                "type": "FrooxEngine.MeshRenderer",
                "fields": {"Mesh": "$component:mesh-drum", "Materials": ["$component:mat-shared"]},
            },
        ],
    }


def _synthetic_bundles() -> dict[str, dict]:
    """ground と vacant が衝突キー・共有 provider・刈り込まれる provider を持つ構成。"""
    ground = _synthetic_bundle(
        "Ground",
        "blender_Ground_synthetic",
        {"mesh-drum": DRUM_ASSET},
        [
            _drum_slot(),
            {
                "slot": {"key": "blender_providers", "name": "Blender_Providers"},
                "components": [],
                "children": [
                    _provider_slot("provider_mat-shared", "mat-shared", SHARED_MATERIAL_FIELDS),
                    _provider_slot("provider_mat-ground", "mat-ground", GROUND_MATERIAL_FIELDS),
                ],
            },
        ],
    )
    vacant = _synthetic_bundle(
        "Vacant",
        "blender_Vacant_synthetic",
        {"mesh-drum": DRUM_ASSET},
        [
            _drum_slot(),
            {
                "slot": {"key": "blender_providers", "name": "Blender_Providers"},
                "components": [],
                "children": [
                    # 同一フィールドの provider は再利用され、宣言されない
                    _provider_slot("provider_mat-shared", "mat-shared", SHARED_MATERIAL_FIELDS),
                    _provider_slot("provider_mat-vacant", "mat-vacant", VACANT_MATERIAL_FIELDS),
                ],
            },
        ],
    )
    empty = _synthetic_bundle("Empty", "blender_Empty_synthetic", {}, [])
    bundles = {sector: empty for sector in pipeline.SECTORS}
    bundles["ground"] = ground
    bundles["vacant"] = vacant
    return bundles


@pytest.fixture(scope="module")
def synthetic_bundle_dir(tmp_path_factory) -> Path:
    """全 7 セクタ分の合成 bundle（ground/vacant のみ中身あり）を書き出す。"""
    root = tmp_path_factory.mktemp("synthetic-bundles")
    for sector, bundle in _synthetic_bundles().items():
        directory = root / f"{sector}{pipeline.BUNDLE_SUBDIR_SUFFIX}"
        directory.mkdir()
        (directory / pipeline.BUNDLE_APPLY_NAME).write_text(json.dumps(bundle), encoding="utf-8")
        (directory / "mesh-drum.mesh.json").write_text(
            json.dumps({"vertices": [], "faces": []}), encoding="utf-8"
        )
    return root


@pytest.fixture(scope="module")
def synthetic_manifest(synthetic_bundle_dir) -> dict:
    return pipeline.build_unified_manifest(synthetic_bundle_dir)


def _walk_slots(nodes: list) -> list:
    found = []
    for node in nodes:
        found.append(node)
        found.extend(_walk_slots(node.get("children", [])))
    return found


def _all_components(manifest: dict) -> list:
    return [component for node in _walk_slots(manifest["children"]) for component in node.get("components", [])]


def _slot_keys(manifest: dict) -> list:
    return [node["slot"]["key"] for node in _walk_slots(manifest["children"])]


def _node_by_slot_key(manifest: dict, key: str) -> dict:
    for node in _walk_slots(manifest["children"]):
        if node["slot"]["key"] == key:
            return node
    raise AssertionError(f"slot {key!r} not found in merged manifest")


def _references(manifest: dict) -> list[tuple[str, str]]:
    """``(kind, key)`` の一覧。kind は asset / component / slot。"""
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
    visit(manifest.get("cameras", {}))
    visit(manifest.get("tests", []))
    visit(manifest["children"])
    return found


def _assert_references_resolve(manifest: dict) -> None:
    slots = set(_slot_keys(manifest)) | {manifest["slot"]["key"]}
    components = {component["key"] for component in _all_components(manifest)}
    assets = set(manifest["assets"])
    for kind, key in _references(manifest):
        target = {"asset": assets, "component": components, "slot": slots}[kind]
        assert key in target, f"unresolved ${kind}:{key}"


def test_merge_uniquifies_colliding_keys(synthetic_manifest):
    """①衝突キーは sector- prefix で退避され、両セクタの分が別々に残る。"""
    slot_keys = _slot_keys(synthetic_manifest)
    assert slot_keys.count("object-drum") == 1
    assert slot_keys.count("vacant-object-drum") == 1
    assert slot_keys.count("blender_providers") == 1
    assert slot_keys.count("vacant-blender_providers") == 1

    component_keys = [component["key"] for component in _all_components(synthetic_manifest)]
    for key in ("mesh-drum", "renderer-drum"):
        assert component_keys.count(key) == 1
        assert component_keys.count(f"vacant-{key}") == 1
    # slot と component は同一の一意性名前空間を共有する
    assert len(set(slot_keys) | set(component_keys)) == len(slot_keys) + len(component_keys)


def test_merge_reuses_shared_provider(synthetic_manifest):
    """②同一 provider は 1 回だけ宣言され、他セクタの参照はそこを指す。"""
    components = _all_components(synthetic_manifest)
    assert [component["key"] for component in components].count("mat-shared") == 1
    declared = next(component for component in components if component["key"] == "mat-shared")
    assert declared["fields"] == SHARED_MATERIAL_FIELDS

    # vacant 側の renderer は再利用された 1 つの宣言を指したまま
    vacant_drum = _node_by_slot_key(synthetic_manifest, "vacant-object-drum")
    renderer = next(component for component in vacant_drum["components"] if component["key"] == "vacant-renderer-drum")
    assert renderer["fields"]["Materials"] == ["$component:mat-shared"]


def test_merge_prunes_emptied_provider_slot(synthetic_manifest):
    """③中身が全て再利用された provider スロットは出力から消える。"""
    slot_keys = _slot_keys(synthetic_manifest)
    assert "provider_mat-shared" in slot_keys  # ground 側の宣言元は残る
    assert "vacant-provider_mat-shared" not in slot_keys
    # vacant 側の providers スロットは残った provider 1 つだけを持つ
    vacant_providers = _node_by_slot_key(synthetic_manifest, "vacant-blender_providers")
    assert [child["slot"]["key"] for child in vacant_providers["children"]] == ["provider_mat-vacant"]


def test_merge_references_follow_renames(synthetic_manifest):
    """④$component:/$asset: は退避先キーに追従し、全て実在キーを指す。"""
    vacant_drum = _node_by_slot_key(synthetic_manifest, "vacant-object-drum")
    mesh, renderer = vacant_drum["components"]
    assert mesh["key"] == "vacant-mesh-drum"
    assert mesh["fields"]["URL"] == "$asset:vacant-mesh-drum"
    assert renderer["key"] == "vacant-renderer-drum"
    assert renderer["fields"]["Mesh"] == "$component:vacant-mesh-drum"

    # asset キーも別名前空間で一意化され、source はセクタ bundle 配下を指す
    assert synthetic_manifest["assets"]["mesh-drum"]["source"] == "ground-v1/mesh-drum.mesh.json"
    assert synthetic_manifest["assets"]["vacant-mesh-drum"]["source"] == "vacant-v1/mesh-drum.mesh.json"

    # ground 側は退避されない（先着がそのまま使われる）
    ground_drum = _node_by_slot_key(synthetic_manifest, "object-drum")
    assert ground_drum["components"][0]["fields"]["URL"] == "$asset:mesh-drum"
    _assert_references_resolve(synthetic_manifest)
