"""The new world stays self-contained and ready for later generation tasks."""
from pathlib import Path

from modeling.slum03.layout import build_layout

ROOT = Path(__file__).resolve().parents[2]


def test_project_scaffold_is_standalone():
    # 固定値の理由: 承認済みの設計仕様（2026-09-27-slum03-cyberpunk-slum-design.md の 7.2・9.1「所有」）は
    # slum02 のコードと state の混入を禁じ、4.1 で既定シードを 260927 と定める。適用済みのワールドはこのシードから生成した。
    assert not (ROOT / 'modeling/slum02').exists()
    assert not (ROOT / '.resoloop/slum02').exists()
    assert build_layout().seed == 260927


def test_scaffold_manifest_and_flux_use_the_approved_world_identity():
    # 固定値の理由: 所有キー・所有ルート・state のパスは、適用済みの state と Resonite 上の Slum03_Slum の対応。
    # Grabbable を付けないのは、strict audit の警告を消すためだけに街全体を Grabbable にしない判断（Issue #12）による。
    import json
    manifest = json.loads((ROOT / 'content/main.json').read_text())
    assert manifest['ownership']['key'] == 'slum03'
    assert manifest['slot']['key'] == 'root'
    assert manifest['slot']['name'] == 'Slum03_Slum'
    assert manifest['slot']['parent'] == 'Root'
    assert not any(c['type'].endswith('.Grabbable') for c in manifest.get('components', []))
    flux = json.loads((ROOT / 'flux/resoloop.flux.json').read_text())
    assert flux['worldState'] == '../.resoloop/slum03/state/slum03.json'
