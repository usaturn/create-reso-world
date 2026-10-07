import pytest

from modeling.slum02 import geometry as g
from modeling.slum02 import sectors


def test_sector_order_fixed():
    # 固定値の理由: pipeline.merge_bundles はこの順にセクタを統合し、衝突したキーは後のセクタ側を
    # <sector>-<key> に改名する。順序が変わると適用済みの state と安定キーが一致せず、作り直しや prune の対象を誤る。
    assert sectors.SECTORS == ("ground", "plaza", "towers-a", "towers-b", "towers-c", "market",
                               "nightlife", "shacks", "ads", "overhead", "backdrop")


def test_unregistered_sector_raises():
    with pytest.raises(KeyError):
        sectors.sector_assemblies({}, "nope")


def test_resource_report_counts_submeshes():
    a = g.Assembly("x", "x-01", "ground", (0.0, 0.0, 0.0), [
        g.box("a", (0, 0, 0), (1, 1, 1), "rust"), g.box("b", (2, 0, 0), (1, 1, 1), "asphalt")])
    b = g.Assembly("x", "x-02", "ground", (5.0, 0.0, 0.0), [g.box("c", (0, 0, 0), (1, 1, 1), "rust")])
    r = sectors.resource_report([a, b], "ground")
    assert r["objects"] == 2 and r["submeshes"] == 3 and r["triangles"] == 36
    assert r["materials"] == ["asphalt", "rust"] and r["material_count"] == 2
