"""Task 9: unified manifest built by modeling.akichi.pipeline.

The structural assertions mirror the brief; asset reference integrity is checked
by ``resoloop validate`` (offline), not by these tests.
"""
import json
from pathlib import Path

from modeling.akichi import pipeline


def test_manifest_structure(tmp_path):
    # 実 bundle がある場合はそれを使い、CI 的に最小構成でも検証できること
    manifest = pipeline.build_unified_manifest(Path("content/akichi"))
    assert manifest["ownership"]["key"] == "akichi"
    assert manifest["slot"]["name"] == "Akichi_Slum"
    assert manifest["slot"]["parent"] == "Root"
    sectors = {child["slot"]["key"] for child in manifest["children"]}
    assert sectors == {f"sector-{s}" for s in ("ground", "vacant", "towers", "market", "shacks", "nightlife", "ads")}
    # asset 参照の整合は resoloop validate（Step 5）で検査するため、ここでは構造のみ確認


def test_signs_attached():
    manifest = pipeline.build_unified_manifest(Path("content/akichi"))
    text = json.dumps(manifest, ensure_ascii=False)
    assert "TextRenderer" in text
    assert "ジャンク屋 鉄屑堂" in text


def test_cameras_and_tests_present():
    manifest = pipeline.build_unified_manifest(Path("content/akichi"))
    assert len(manifest["cameras"]) == 4
    assert manifest["cameras"]["overview-north"]["representative"] is True
    assert any(t["name"] == "root-exists" for t in manifest["tests"])


def test_manifest_is_deterministic():
    a = json.dumps(pipeline.build_unified_manifest(Path("content/akichi")), sort_keys=True, ensure_ascii=False)
    b = json.dumps(pipeline.build_unified_manifest(Path("content/akichi")), sort_keys=True, ensure_ascii=False)
    assert a == b