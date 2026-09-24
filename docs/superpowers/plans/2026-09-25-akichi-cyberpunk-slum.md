# akichi サイバーパンク・スラム街 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** resoloop + Blender で約100×100m のサイバーパンク・スラム街（中心空地・廃ビル群・屋台・AR広告・風俗店・掘っ立て小屋）を決定論的に生成し、Resonite へライブ適用して実機 QA まで完了する。

**Architecture:** `akichi/modeling/akichi/` に決定論的 Python パイプラインを新設。layout.json（固定シード）→ セクタ別 .blend 生成（`resoloop blender run`）→ セクタ別 export bundle → 統合 manifest（`content/akichi/akichi-slum.json`）→ validate/diff/apply/再apply 収束 → 実機 QA。tokyo_nova（`MyResoniteProject/modeling/tokyo_nova/`）の実証済みパターンを移植する。

**Tech Stack:** Python 3.12+（uv 必須）、bpy/bmesh/mathutils（Blender 5.0.1、`/usr/bin/blender`）、resoloop CLI（Blender run/export、ResoniteLink 0.13.1）、pytest。

**Spec:** `docs/superpowers/specs/2026-09-25-akichi-cyberpunk-slum-design.md`

## Global Constraints

- 座標系: layout/geometry は Resonite XYZ（Y up、単位 m）。Blender XZY 変換は build 境界で 1 回だけ（`resonite_to_blender`）
- 決定論性: `SEED = 250925`。`random.Random(seed + 安定オフセット)` のみ使用。反復順序・命名は安定（`tower-01` 形式のゼロ埋め ID）
- Python 実行は必ず `uv run`（`python3` 直呼び禁止）。作業ディレクトリは `/workspaces/reso-world/akichi`
- **イメージテクスチャ不使用**: 共有マウント不在のためフラット Principled パラメータ + モデリングディテールのみ（仕様書「前提」参照）。Blender マテリアルは Principled BSDF の base_color/metallic/roughness/emission/emission_strength のみ接続（exporter が PBS_Metallic に変換可能。Bump・Mix RGB・手続きテクスチャ等は禁止）
- ホログラム/半透明表現は不透明 emissive + 暗色フレームで代替（exporter transparency 非対応）
- 1 論理オブジェクト = 1 メッシュ: export 時は (sector, category, material) バッチの static mesh にマージし、インスペクターで人間が触れる単位を保つ
- export advisory 閾値（50k triangles / 8 materials / 16 draw sections / 2048px）超過はエラーではなく記録して根拠を残す
- resoloop 安全規則: `Root`・未検証 ID・所有境界外を触らない。実験は `ResoLoop_Test_*` のみ、削除は検証済み ID + `--yes`。apply は `--state .resoloop/akichi/state/akichi-slum.json` を保持し、タイムアウト時も state を捨てない
- 日本語テキストは Resonite ネイティブ `FrooxEngine.TextRenderer` のみ（Blender フォントに依存しない）
- ブランチ `feat/akichi-slum`。タスクごとにコミット。コミットメッセージ末尾に `Co-Authored-By: Claude Code <noreply@anthropic.com>`
- 風俗店は示唆的表現（ネオン・カーテン・張り紙）まで。露骨なコンテンツ不可
- 長時間 Blender/resoloop コマンドの監視は `monitoring-long-tasks` スキルと `.agents/monitoring-runtimes.md` に従う。実装サブエージェント内では同期実行（バックグラウンド化してターンを終えない）

## Review Focus

1. **セクタ境界の不整合**: layout の建物 footprint と ads/cables の配置が重なり、看板が壁にめり込む → `validate_layout` のクリアランス検査（Task 3）で防ぐ
2. **決定論の破れ**: dict 反復順や `random` 全局所化で再生成のたびにハッシュが変わり、apply 収束確認が機能しない → 同一シード 2 回生成のハッシュ一致テスト（Task 3・Task 5・Task 9）で防ぐ
3. **UV/法線の export 破綻**: metric UV 未適用や XZY 変換の winding 反転で実機が真っ黒/縞模様 → `uv_triangle_issues` 監査（Task 1・Task 6）と実機 QA（Task 11）で防ぐ
4. **emissive の変換漏れ**: emission_strength 未設定や非対応ノードで看板が光らない → materials テスト（Task 2）と export report の material 検査（Task 8）で防ぐ
5. **リソース爆発**: 100×100m の瓦礫を無制限 scatter して apply がセッションを重くする → セクタ別リソースレポートと advisory 閾値の記録（Task 6・Task 7）で防ぐ

---

### Task 1: プロジェクトスキャフォールド + geometry/uv 基盤

**Files:**
- Create: `akichi/pyproject.toml`, `akichi/modeling/__init__.py`, `akichi/modeling/akichi/__init__.py`
- Create: `akichi/modeling/akichi/geometry.py`（tokyo_nova から移植）
- Create: `akichi/modeling/akichi/uv.py`（tokyo_nova から移植）
- Test: `akichi/tests/__init__.py`, `akichi/tests/akichi/__init__.py`, `akichi/tests/akichi/test_geometry.py`

**Interfaces:**
- Consumes: `MyResoniteProject/modeling/tokyo_nova/geometry.py`（189行）と `uv.py`（102行）を移植元として読む
- Produces:
  - `geometry.MeshData`（frozen dataclass: `name: str, vertices: tuple[Vec3,...], faces: tuple[Face,...], material: str`）
  - `geometry.mesh(name, vertices, faces, material) -> MeshData`
  - `geometry.box(name, center: Sequence[float], size: Sequence[float], material: str) -> MeshData`
  - `geometry.beveled_box(name, center, size, bevel: float, material) -> MeshData`
  - `geometry.cylinder(name, center, radius: float, height: float, segments: int, material, axis: str = "Y") -> MeshData`（新規追加。移植元にない場合この仕様で実装: axis 方向の円柱、上面/下面 cap 付き、`segments >= 3`）
  - `geometry.prism(name, center, size, material) -> MeshData`（新規追加: 三角柱。屋根用に使用。size=(w,h,d)、h は稜線までの高さ、頂点8→6の三角柱: 底面4点 + 稜線2点）
  - `uv.metric_face_uvs(points, normal, uv_per_meter=0.5) -> list[Vec2]`
  - `uv.uv_triangle_issues(points, uvs, normal, uv_per_meter=0.5, handedness=1) -> list[str]`

- [ ] **Step 1: pyproject.toml 作成**

```toml
[project]
name = "akichi"
version = "0.1.0"
description = "Cyberpunk slum district generator for Resonite via resoloop + Blender"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`akichi/` 直下に作成し、`cd /workspaces/reso-world/akichi && uv sync` が成功することを確認する。

- [ ] **Step 2: 失敗するテストを書く**

`tests/akichi/test_geometry.py`:

```python
"""geometry/uv 基盤の動作検証。"""
from __future__ import annotations

from modeling.akichi import geometry, uv


def test_box_is_deterministic_and_manifold():
    a = geometry.box("b", (0, 0, 0), (2, 3, 4), "concrete_dark")
    b = geometry.box("b", (0, 0, 0), (2, 3, 4), "concrete_dark")
    assert a == b
    assert len(a.vertices) == 8 and len(a.faces) == 6
    # 各辺がちょうど2面に共有される = 閉じた多面体
    from collections import Counter
    edge_count = Counter()
    for face in a.faces:
        for i, j in zip(face, face[1:] + face[:1]):
            edge_count[tuple(sorted((i, j)))] += 1
    assert all(count == 2 for count in edge_count.values())


def test_cylinder_axis_and_segments():
    c = geometry.cylinder("c", (0, 0, 0), 0.5, 2.0, 8, "dark_metal", axis="Y")
    ys = [v[1] for v in c.vertices]
    assert min(ys) == -1.0 and max(ys) == 1.0
    assert len(c.faces) == 10  # 側面 8 quad + 上下 cap 2 n-gon


def test_prism_roof_shape():
    p = geometry.prism("roof", (0, 0, 0), (4, 1.5, 6), "corrugated")
    assert len(p.vertices) == 6
    ridge = max(v[1] for v in p.vertices)
    assert ridge == 0.75  # h/2


def test_beveled_box_rejects_bad_input():
    try:
        geometry.beveled_box("x", (0, 0, 0), (1, 1, 0), 0.1, "rust")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_metric_face_uvs_pass_audit():
    points = [(0, 0, 0), (2, 0, 0), (2, 0, 3), (0, 0, 3)]
    normal = (0, 1, 0)
    uvs = uv.metric_face_uvs(points, normal, uv_per_meter=0.5)
    assert len(uvs) == 4
    # 三角分割して監査: 問題なし
    for tri in ((0, 1, 2), (0, 2, 3)):
        issues = uv.uv_triangle_issues(
            [points[i] for i in tri], [uvs[i] for i in tri], normal, 0.5, 1
        )
        assert issues == []
```

- [ ] **Step 3: テストが失敗することを確認**

Run: `cd /workspaces/reso-world/akichi && uv run pytest tests/akichi/test_geometry.py -v`
Expected: FAIL（`ModuleNotFoundError: modeling`）

- [ ] **Step 4: geometry.py / uv.py を移植**

`MyResoniteProject/modeling/tokyo_nova/geometry.py` と `uv.py` を `akichi/modeling/akichi/` にコピーし、以下を変更:
- module docstring を akichi 用に更新（座標系注記は維持）
- `cylinder()` と `prism()` を上記インターフェース仕様通りに新規実装（既存の `box` と同じ決定論スタイル: 純粋関数、入力検証、共有頂点なしでよい）
- import は標準ライブラリのみ（math, dataclasses, collections.abc）

`modeling/__init__.py` と `modeling/akichi/__init__.py` は空ファイル。pytest の `rootdir` 解決のため `pyproject.toml` に以下を追加:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 5: テスト成功を確認**

Run: `cd /workspaces/reso-world/akichi && uv run pytest tests/akichi/test_geometry.py -v`
Expected: 全 PASS

- [ ] **Step 6: resoloop blender 疎通スモーク**

```bash
cd /workspaces/reso-world/akichi
cat > /tmp/smoke.py <<'EOF'
import bpy, json, sys
print(json.dumps({"ok": True, "blender": bpy.app.version_string}))
sys.exit(0)
EOF
resoloop blender run /tmp/smoke.py --json
```

Expected: `"ok":true` と Blender バージョンを含む JSON 出力（失敗時は `resoloop blender find --json` で再確認し、環境問題を報告）

- [ ] **Step 7: コミット**

```bash
cd /workspaces/reso-world && git add akichi/pyproject.toml akichi/modeling akichi/tests akichi/uv.lock
git commit -m "feat(akichi): scaffold uv project with geometry/uv foundation

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: materials.py — Cyberpunk パレット

**Files:**
- Create: `akichi/modeling/akichi/materials.py`
- Test: `akichi/tests/akichi/test_materials.py`

**Interfaces:**
- Consumes: なし（Task 3 以降が名前文字列で参照）
- Produces:
  - `materials.MATERIALS: dict[str, dict[str, Any]]` — キーはマテリアル名、値は `{"base_color": (r,g,b,a), "metallic": float, "roughness": float}`、emissive のみ `"emission": (r,g,b,a), "emission_strength": float` を追加
  - `materials.build_materials() -> dict[str, dict]` — 新鮮なコピーを返す
  - `materials.make_blender_materials() -> dict[str, Any]` — bpy ランタイムで Principled マテリアルを生成（base_color/metallic/roughness のみ接続、emission ありは Emission Color + Emission Strength 接続。それ以外のソケットは接続しない）
  - `materials.NEON_COLORS: list[str]` — ネオンマテリアル名の順序固定リスト

マテリアル一覧（27種、tokyo_nova パレットを cyberpunk 方向に拡張）:

| 名前 | base_color (sRGB近似) | metallic | roughness | 用途 |
|---|---|---|---|---|
| `concrete_dark` | (0.20,0.19,0.18) | 0.0 | 0.93 | 廃ビル主体 |
| `concrete_mid` | (0.31,0.29,0.26) | 0.0 | 0.90 | ビルバリエーション |
| `concrete_stained` | (0.24,0.22,0.18) | 0.0 | 0.94 | 汚れ面・雨だれ |
| `patched_concrete` | (0.39,0.36,0.30) | 0.0 | 0.85 | 補修パッチ |
| `rust` | (0.34,0.105,0.035) | 0.55 | 0.82 | 錆 |
| `rust_dark` | (0.22,0.07,0.03) | 0.5 | 0.86 | 錆ストリーク |
| `exposed_metal` | (0.38,0.40,0.39) | 0.83 | 0.39 | 鉄筋・框架 |
| `dark_metal` | (0.10,0.11,0.12) | 0.7 | 0.5 | 枠・パイプ |
| `painted_metal_faded` | (0.28,0.20,0.14) | 0.4 | 0.66 | 褪色塗装 |
| `corrugated` | (0.33,0.31,0.29) | 0.65 | 0.62 | トタン |
| `corrugated_rusted` | (0.40,0.22,0.12) | 0.55 | 0.75 | 錆トタン |
| `plywood` | (0.42,0.30,0.17) | 0.0 | 0.88 | ベニヤ |
| `tarp_blue` | (0.10,0.16,0.30) | 0.0 | 0.7 | ブルーシート |
| `tarp_orange` | (0.45,0.22,0.08) | 0.0 | 0.72 | オレンジシート |
| `glass_dark` | (0.05,0.08,0.09) | 0.3 | 0.15 | 窓ガラス（暗） |
| `asphalt_cracked` | (0.075,0.08,0.082) | 0.02 | 0.95 | 地面 |
| `asphalt_wet` | (0.045,0.06,0.068) | 0.2 | 0.25 | 濡れ路面 |
| `mud` | (0.13,0.10,0.07) | 0.0 | 0.97 | 泥土 |
| `sign_backing` | (0.06,0.06,0.07) | 0.1 | 0.6 | 看板裏板 |
| `warm_light` | emission (1.0,0.42,0.12), strength 3.0 | 0.0 | 0.4 | 行灯・窓明かり |
| `neon_magenta` | emission (1.0,0.05,0.6), strength 5.0 | 0.0 | 0.35 | AR広告・サイン |
| `neon_cyan` | emission (0.05,0.9,1.0), strength 5.0 | 0.0 | 0.35 | 同上 |
| `neon_orange` | emission (1.0,0.35,0.02), strength 4.5 | 0.0 | 0.35 | 同上 |
| `neon_purple` | emission (0.6,0.1,1.0), strength 5.0 | 0.0 | 0.35 | 風俗系サイン |
| `neon_lime` | emission (0.55,1.0,0.05), strength 4.5 | 0.0 | 0.35 | AR広告 |
| `neon_pink` | emission (1.0,0.3,0.55), strength 5.0 | 0.0 | 0.35 | 風俗系サイン |
| `holo_panel` | base (0.02,0.10,0.12), emission (0.1,0.85,1.0), strength 2.2 | 0.0 | 0.3 | ホログラム風広告面 |

emissive の base_color は emission 色 × 0.25 程度（Blender で emission_strength を掛けた見た目の破綻防止）。`NEON_COLORS = ["neon_magenta","neon_cyan","neon_orange","neon_purple","neon_lime","neon_pink"]`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/akichi/test_materials.py`:

```python
from modeling.akichi import materials


def test_palette_is_complete_and_export_safe():
    mats = materials.build_materials()
    assert len(mats) >= 24
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
```

- [ ] **Step 2: 失敗を確認** — `uv run pytest tests/akichi/test_materials.py -v` → FAIL（ModuleNotFoundError）
- [ ] **Step 3: materials.py を実装**（上記表の定数 + 3関数。`make_blender_materials` は tokyo_nova 版を移植し、emission を `Emission Color`/`Emission Strength` ソケット名で接続する前に `bpy.types.PrincipledBSDFInput` の RNA を確認。Blender 5.0 のソケット名は `"Emission Color"` と `"Emission Strength"`）
- [ ] **Step 4: テスト成功** — 全 PASS
- [ ] **Step 5: コミット** — `git add akichi/modeling/akichi/materials.py akichi/tests/akichi/test_materials.py && git commit -m "feat(akichi): add cyberpunk material palette

Co-Authored-By: Claude Code <noreply@anthropic.com>"`

---

### Task 3: layout.py — 決定論的配置定義 + 検証

**Files:**
- Create: `akichi/modeling/akichi/layout.py`
- Test: `akichi/tests/akichi/test_layout.py`

**Interfaces:**
- Consumes: なし（純粋データ生成）
- Produces:
  - `layout.SEED = 250925`
  - `layout.SITE = {"width": 100.0, "depth": 100.0}`（x: -50..50, z: -50..50）
  - `layout.build_layout() -> dict` — 下記スキーマの dict（毎回同一内容）
  - `layout.validate_layout(data: dict) -> list[str]` — 問題文字列のリスト（空 = 妥当）

**layout スキーマ:**

```python
{
  "schema_version": 1,
  "seed": 250925,
  "site": {"width": 100.0, "depth": 100.0},
  "vacant": {"min": [-14.0, -19.0], "max": [14.0, 19.0]},  # 中心空地 [x,z] 約28×38m
  "streets": [  # 空地を囲む環状路 + 外周路（アスファルト帯）
    {"id": "ring-north", "min": [-50, 19], "max": [50, 27]},
    {"id": "ring-south", "min": [-50, -27], "max": [50, -19]},
    {"id": "ring-east", "min": [14, -27], "max": [22, 27]},
    {"id": "ring-west", "min": [-22, -27], "max": [-14, 27]},
    {"id": "perimeter-north", "min": [-50, 42], "max": [50, 50]},
    {"id": "perimeter-south", "min": [-50, -50], "max": [50, -42]},
    {"id": "perimeter-east", "min": [42, -50], "max": [50, 50]},
    {"id": "perimeter-west", "min": [-50, -50], "max": [-42, 50]},
  ],
  "towers": [  # 10棟。footprint 8×8〜15×15、height 10〜30、rotation 0/90/180/270 以外の微妙な角度は禁止
    {"id": "tower-01", "center": [x, z], "footprint": [w, d], "height": h,
     "rotation": deg, "setback_height": h*0.6〜0.8, "setback_inset": 1.0〜2.5,
     "broken_corner": bool, "corner_size": 2.0〜4.0},
    # 配置帯: 北側 z∈[27,42] に3棟、南側 z∈[-42,-27] に3棟、
    # 東側 x∈[22,42] に2棟、西側 x∈[-42,-22] に2棟。
    # footprint は帯域内に完全収まり、相互に2m以上離隔
  ],
  "stalls": [  # 屋台12軒。ring-east 帯内 x=17.5 付近に z=-16..16 で 2.9m 間隔の6軒、
               # ring-west 帯内 x=-17.5 付近に同様の6軒。rotation は通りの向き + 0/180
               #（Ruling: 旧記載 x∈[23,30] は ring 帯 x∈[14,22] と検査項目4に矛盾するため帯内配置に修正）
    {"id": "stall-01", "center": [x, z], "rotation": deg, "kind": "junk"|"parts"|"food", "awning": "tarp_blue"|"tarp_orange"},
  ],
  "shacks": [  # 掘っ立て小屋10棟。南西ブロック x∈[-42,-24], z∈[-42,-28] に
               # rng でジグザグ配置、footprint 2.5×2.5〜4×5、rotation -15..15 度の乱雑さ、相互1.5m以上離隔
    {"id": "shack-01", "center": [x, z], "footprint": [w, d], "height": 2.4〜3.2, "rotation": deg, "wall_mix": ["corrugated","plywood",...]（2〜3種の壁材）},
  ],
  "nightlife": [  # 風俗店4軒。北側ビル帯 z∈[27,30] の tower 間に3軒 + 東 ring 北端に1軒
    {"id": "club-01", "center": [x, z], "rotation": deg, "width": 4〜6, "neon": "neon_pink"|"neon_purple"|"neon_magenta", "sign_text": "..."（Task 10 で TextRenderer 化）},
  ],
  "ads": [  # AR広告26面。内訳: 壁面広告8（tower 面の y=4〜15 に 3×2〜6×3m）、
            # 自立ホロパネル10（vacant 外周・street 沿い、1.2×2m〜2×3m、y底部 0 または支柱上）、
            # 屋台上大型広告4（tower 屋上 y=height+1〜3、4×2〜8×3m）、屋台行灯4（stall 上 y=2.2、0.6×0.9m）
    {"id": "ad-01", "kind": "wall"|"holo"|"rooftop"|"lantern", "position": [x, y, z],
     "rotation": deg, "size": [w, h], "color": NEON_COLORS から巡回, "frame": "dark_metal"|"sign_backing"},
  ],
  "cables": [  # ケーブル12本。tower 間・tower-stall 間の catenary。端点2つ + sag 0.5〜2m
    {"id": "cable-01", "from": [x, y, z], "to": [x, y, z], "sag": m, "radius": 0.03〜0.06},
  ],
  "signs": [  # TextRenderer 看板（日本語）。nightlife 4 + junk屋 4 + ads テキスト 6
    {"id": "sign-01", "attach_to": "club-01"|"stall-03"|"ad-05", "offset": [x, y, z],
     "text": "..." , "color": [r,g,b,a], "size": 0.15〜0.6},
  ],
}
```

**sign_text の候補**（示唆的だが露骨でない日本語）: 風俗店 `"ピンクサロン 夢の国"` / `"ガールズバー NEON"` / `"マッサージ 桃源郷"` / `"スナック 星屑"`。ジャンク屋 `"ジャンク屋 鉄屑堂"` / `"電脳パーツ 秋葉屋"` / `"リペア受付"` / `"中古義体 激安"`。広告 `"ヌードル24時"` / `"サイバー義体 SALE"` / `"ネオ東京へようこそ"` / `"合成酒 ホロドリンク"` / `"24H カプセルホテル"` / `"データ復旧 即納"`。

**validate_layout の検査項目:**
1. towers/shacks/stalls/nightlife の footprint が site 境界内
2. towers 相互の footprint 離隔 >= 2.0m、shacks 相互 >= 1.5m、nightlife と towers の footprint 離隔 >= 2.0m
3. vacant 矩形内 towers/shacks/stalls/nightlife の footprint が侵入しない（ads kind=holo で vacant 外周 2m 以内も不可）
4. stalls が streets 帯（ring）内に収まる
5. ads kind=wall/rooftop の position が対応 tower の面から 0.5m 以内（壁面吸着）— tower ID を `attach` フィールドで参照して検査
6. cables の端点が site 内、y >= 2.0
7. 決定論: `build_layout() == build_layout()`

- [ ] **Step 1: 失敗するテストを書く**

`tests/akichi/test_layout.py`:

```python
import json

from modeling.akichi import layout


def test_layout_is_deterministic():
    a = json.dumps(layout.build_layout(), sort_keys=True)
    b = json.dumps(layout.build_layout(), sort_keys=True)
    assert a == b


def test_layout_counts():
    data = layout.build_layout()
    assert len(data["towers"]) == 10
    assert len(data["stalls"]) == 12
    assert len(data["shacks"]) == 10
    assert len(data["nightlife"]) == 4
    assert len(data["ads"]) == 26
    assert len(data["cables"]) == 12
    assert len(data["signs"]) == 14


def test_layout_validates_clean():
    data = layout.build_layout()
    assert layout.validate_layout(data) == []


def test_vacant_lot_is_clear():
    data = layout.build_layout()
    vmin, vmax = data["vacant"]["min"], data["vacant"]["max"]
    for tower in data["towers"]:
        cx, cz = tower["center"]
        w, d = tower["footprint"]
        # footprint が vacant と重ならない
        assert not (cx - w/2 < vmax[0] and cx + w/2 > vmin[0]
                    and cz - d/2 < vmax[1] and cz + d/2 > vmin[1]), tower["id"]


def test_validator_detects_intrusion():
    data = layout.build_layout()
    data["towers"][0]["center"] = [0.0, 0.0]  # vacant の中へ移動
    issues = layout.validate_layout(data)
    assert any("vacant" in issue for issue in issues)


def test_all_ids_unique_and_zero_padded():
    data = layout.build_layout()
    ids = [item["id"] for group in ("towers","stalls","shacks","nightlife","ads","cables","signs") for item in data[group]]
    assert len(ids) == len(set(ids))
    assert all("-" in i and i.split("-")[1].isdigit() for i in ids)
```

- [ ] **Step 2: 失敗を確認** — `uv run pytest tests/akichi/test_layout.py -v` → FAIL
- [ ] **Step 3: layout.py を実装**

実装方針（決定論の要）:
- `rng = random.Random(SEED)` を 1 回だけ生成し、**カテゴリ順（towers → stalls → shacks → nightlife → ads → cables → signs）に消費**。カテゴリ内は ID 順
- tower 配置は帯域ごとに固定スロットリスト（例: 北帯 `(-34, 34), (-12, 35), (30, 33)` 等）を用意し、rng で footprint/height/setback/broken_corner を選ぶ。帯域収まりは生成時に clamp して保証
- ads kind=wall/rooftop は tower spec から面位置を計算して吸着（`attach: "tower-NN"`, `face: "north"|"south"|"east"|"west"` を ads エントリに追加してよい）
- validate_layout は上記7項目を純粋関数で検査

- [ ] **Step 4: テスト成功** — 全 PASS
- [ ] **Step 5: コミット** — `git commit -m "feat(akichi): add deterministic district layout with validation

Co-Authored-By: Claude Code <noreply@anthropic.com>"`

---

### Task 4: buildings.py — 廃ビルジェネレータ（brutalist + 破損）

**Files:**
- Create: `akichi/modeling/akichi/buildings.py`
- Test: `akichi/tests/akichi/test_buildings.py`

**Interfaces:**
- Consumes: `geometry.box/beveled_box/cylinder/prism/MeshData`、`materials` 名文字列、layout の tower spec dict
- Produces:
  - `buildings.Assembly`（dataclass: `kind: str, name: str, origin: Vec3, rotation: float, parts: list[MeshData], attachments: dict[str, Vec3]`。tokyo_nova props.py の Assembly と同型）
  - `buildings.build_tower(spec: dict, seed: int) -> Assembly` — origin=(center_x, 0, center_z)、Y=0 が地面
  - `buildings.build_perimeter_wall(seed: int) -> Assembly`（外周の低い廃壁: site 周囲に高さ 1.5〜2.5m、厚さ 0.4m の壁を約 10m ピッチで分節、ところどころ崩落＝分節を欠番にする）

**build_tower の幾何レシピ**（brutalist-mood + dark-gritty-mood 準拠）:
1. **主体**: `box` footprint × height、素材 `concrete_dark`/`concrete_mid`（spec の rng で選択）。setback_height 以上は inset した上位ボリューム（setback_inset だけ小さい box）を積む
2. **窓グリッド**: 各面に幅 1.2m × 高 1.6m の窓を 2.8m ピッチ（水平）× 3.2m ピッチ（垂直）で窪み表現 = 窓枠 box（`dark_metal`、奥行 0.15）+ ガラス面 box（`glass_dark`、厚 0.05、枠より 0.1 奥）。**破損窓**: rng により 30% はガラスなし（枠のみ）、10% は枠も歪み（回転 ±3度の薄い box）
3. **formwork シーム**: 3.2m ごとに水平の薄い box（`concrete_stained`、厚 0.06、幅 0.25）を面に貼る（打ちっぱコンクリートの打設目地）
4. **崩落床**（spec `broken_corner=True` のみ）: 角を corner_size 分切り欠いた表現 = 角部分に高さ全階分の欠損 box を置き（ブーリアンは使わず、角の柱・床スラブを個別 mesh として配置し欠損部は空ける）、露出鉄筋 = 細い `cylinder`（radius 0.03、長 1〜2.5m、`exposed_metal`）を欠損縁から 4〜8 本、rng の角度で突出
5. **屋上**: パラペット（厚 0.3 × 高 0.9 の枠 box 4本）+ 機械室 box（footprint の 30%、高 2m、`concrete_mid`）+ 給水塔（`cylinder` r=1.2, h=2 + 脚 4本）を rng で 60%
6. **錆ストリーク**: 窓下・シーム下に `rust_dark` の薄い box（幅 0.1〜0.3、長 0.5〜2m、厚 0.04）を rng で面に 8〜20 本（dark-gritty: 湿気・雨水経路の下方に限定）
7. **エントランス**: 1 面に幅 2.5 × 高 3m の窪み（`sign_backing` の暗い奥面）+ 上に `warm_light` の小さな emissive box（0.3×0.1）を 40%

parts 数は 1 棟あたり概ね 120〜260。10 棟合計で 60k triangles を超えないことを Task 8 のレポートで確認（超えたら窓ピッチを粗くして調整）。

- [ ] **Step 1: 失敗するテストを書く**

```python
from modeling.akichi import buildings, layout


def _tower_spec(**overrides):
    base = {"id": "tower-01", "center": [0.0, 30.0], "footprint": [10.0, 10.0],
            "height": 20.0, "rotation": 0, "setback_height": 14.0, "setback_inset": 1.5,
            "broken_corner": True, "corner_size": 3.0}
    base.update(overrides)
    return base


def test_tower_is_deterministic():
    a = buildings.build_tower(_tower_spec(), seed=1)
    b = buildings.build_tower(_tower_spec(), seed=1)
    assert [p.name for p in a.parts] == [p.name for p in b.parts]
    assert a.parts[0].vertices == b.parts[0].vertices


def test_tower_bounds_match_spec():
    spec = _tower_spec()
    tower = buildings.build_tower(spec, seed=1)
    (minx, miny, minz), (maxx, maxy, maxz) = tower.bounds
    assert abs(miny) < 0.01  # 地面接地
    assert maxy <= spec["height"] + 3.5  # 屋上構造物込みの上限
    assert maxx - minx <= spec["footprint"][0] + 1.0
    assert maxz - minz <= spec["footprint"][1] + 1.0


def test_tower_has_windows_and_seams():
    tower = buildings.build_tower(_tower_spec(), seed=2)
    kinds = {p.name.rsplit("-", 1)[0] for p in tower.parts}
    assert any("window" in k for k in kinds)
    assert any("seam" in k for k in kinds)
    materials_used = {p.material for p in tower.parts}
    assert "glass_dark" in materials_used and "concrete_stained" in materials_used


def test_broken_corner_adds_rebar():
    tower = buildings.build_tower(_tower_spec(broken_corner=True), seed=3)
    rebar = [p for p in tower.parts if "rebar" in p.name]
    assert len(rebar) >= 4
    plain = buildings.build_tower(_tower_spec(broken_corner=False), seed=3)
    assert len([p for p in plain.parts if "rebar" in p.name]) == 0


def test_triangle_budget_per_tower():
    tower = buildings.build_tower(_tower_spec(), seed=4)
    triangles = sum(len(p.faces) - 2 for p in tower.parts)  # 概算（quad 主体）
    assert triangles < 9000


def test_perimeter_wall_segments():
    wall = buildings.build_perimeter_wall(seed=5)
    assert wall.kind == "perimeter"
    assert len(wall.parts) >= 20
```

- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: buildings.py を実装**（Assembly は tokyo_nova props.py から移植。`bounds` プロパティ含む。上記レシピの各要素を private 関数 `_windows/_seams/_corner_damage/_rooftop/_rust_streaks/_entrance` に分け、`build_tower` が合成）
- [ ] **Step 4: テスト成功**
- [ ] **Step 5: layout の全 10 tower spec で回して予算確認**

```python
# uv run python -c で実行
from modeling.akichi import buildings, layout
data = layout.build_layout()
total = 0
for spec in data["towers"]:
    t = buildings.build_tower(spec, seed=250925)
    total += sum(len(p.faces) - 2 for p in t.parts)
print("tower triangles:", total)
assert total < 70000
```

- [ ] **Step 6: コミット** — `git commit -m "feat(akichi): add brutalist ruin tower generator

Co-Authored-By: Claude Code <noreply@anthropic.com>"`

---

### Task 5: props.py — 屋台・小屋・瓦礫・風俗店・広告パネル・ケーブル

**Files:**
- Create: `akichi/modeling/akichi/props.py`
- Test: `akichi/tests/akichi/test_props.py`

**Interfaces:**
- Consumes: `geometry`、`materials` 名、`buildings.Assembly`
- Produces（すべて `-> Assembly`、origin は床接地面中心、seed 引数で決定論）:
  - `props.build_stall(spec: dict, seed: int)` — ジャンク屋台
  - `props.build_shack(spec: dict, seed: int)` — 掘っ立て小屋
  - `props.build_club(spec: dict, seed: int)` — 風俗店ファサード
  - `props.build_ad(spec: dict, seed: int)` — AR 広告（kind: wall/holo/rooftop/lantern）
  - `props.build_cable(spec: dict) -> Assembly` — catenary ケーブル
  - `props.rubble_prototypes() -> list[MeshData]` — GN scatter の原型（3種: `rubble-chunk` コンクリート塊 0.3〜0.8m の歪んだ box 変形（頂点を rng で ±0.15 動かした非整形 box）、`rubble-slab` 平板 0.8×0.1×0.6、`rubble-rebar` 鉄筋束 cylinder×3）
  - `props.build_vehicle_husk(seed: int)` — 焼けた車両残骸（車体 box 変形 + キャビン + 車輪 cylinder×4、素材 `rust_dark`/`dark_metal`、全長 4m 程度）
  - `props.build_junk_pile(seed: int, radius: float)` — ジャンク山（小型 box/cylinder を rng で 15〜30 個積み上げ、素材 corrugated/dark_metal/painted_metal_faded/plastic 系）

**幾何レシピ:**

- **stall**（幅 2.4 × 奥 1.8 × 高 2.4m）: 柱 4本（`dark_metal` 0.08 角）+ カウンター（`plywood` 1.8×0.9×0.1、高 0.9）+ 屋根（`prism` または傾斜 box、spec.awning 素材）+ 商品ジャンク（counter 上に小型 box/cylinder 5〜9 個）+ 行灯（0.25×0.35 の `warm_light` emissive box を屋根下に吊るし、kind=lantern の ad が取り付く `attachments["lantern"]` を持つ）
- **shack**（spec.footprint、高 spec.height）: 壁 4 面を spec.wall_mix 素材で厚 0.08 の box、屋根は傾斜トタン（`prism`、オーバーハング 0.2）、ドア（`plywood` 0.8×1.9 の凹み + `dark_metal` 取っ手）、窓 0〜1（0.6×0.6 `glass_dark`）、壁面に錆ストリーク 2〜5 本、屋根上に重し（`cylinder` タイヤ風 1〜2）
- **club**（幅 spec.width、奥行 5、高 3.5m のファサード壁）: 本体 box（`concrete_mid`）+ 入口の暖簾風カーテン（`tarp_blue` 等の暗色布 box 2 枚、わずかに傾け）+ ネオンサイン框（`sign_backing` の裏板 box + spec.neon の emissive 縁取り = 幅 0.08 の box 4本）+ 張り紙（壁に 0.3×0.4 の薄い box 3〜6 枚、`plywood`/白系 `patched_concrete`）+ 入口上 `neon_pink` の細い emissive ライン + `attachments["sign"]`（TextRenderer 取付点、サイン框中央）+ 床置き看板（A フレーム: 傾いた box 2 枚 + emissive 縁）
- **ad**:
  - `wall`: 裏板 box（size + 厚 0.1、`sign_backing`）+ 面 emissive box（厚 0.04、spec.color）+ フレーム縁 4本（`dark_metal` 0.06 角）+ 支持金具 2本
  - `holo`: 支柱（`dark_metal` cylinder r=0.05、高 1.2〜2）+ 基台 box + パネル面（`holo_panel` emissive、厚 0.03）+ 上下フレーム + 疑似スキャンライン = 面板上に `neon_cyan` の極薄 box（高さ 0.02）を 4〜7 本等間隔（幾何でホログラム感を表現）
  - `rooftop`: wall の大型版 + 脚 4本（`dark_metal`、高 1m）
  - `lantern`: 0.6×0.9 の小型版（`warm_light` または spec.color）+ 吊り棒
- **cable**: 端点間を 8 セグメントの catenary（放物線近似: `y(t) = lerp(y0,y1,t) - 4*sag*t*(1-t)`）で結び、各セグメントを細い box（radius 相当の幅、`dark_metal`、方向はセグメント向きに回転）で接続
- **vehicle_husk / junk_pile / rubble_prototypes**: 上記インターフェース記述の通り

- [ ] **Step 1: 失敗するテストを書く**

```python
from modeling.akichi import layout, props


def test_stall_deterministic_and_grounded():
    spec = {"id": "stall-01", "center": [0, 0], "rotation": 0, "kind": "junk", "awning": "tarp_blue"}
    a = props.build_stall(spec, seed=1)
    b = props.build_stall(spec, seed=1)
    assert [p.name for p in a.parts] == [p.name for p in b.parts]
    (minx, miny, minz), _ = a.bounds
    assert abs(miny) < 0.05
    assert "lantern" in a.attachments


def test_shack_uses_wall_mix():
    spec = {"id": "shack-01", "center": [0, 0], "footprint": [3, 4], "height": 2.8,
            "rotation": 5, "wall_mix": ["corrugated", "plywood"]}
    shack = props.build_shack(spec, seed=2)
    used = {p.material for p in shack.parts}
    assert "corrugated" in used and "plywood" in used


def test_club_has_neon_and_sign_anchor():
    spec = {"id": "club-01", "center": [0, 0], "rotation": 0, "width": 5,
            "neon": "neon_pink", "sign_text": "テスト"}
    club = props.build_club(spec, seed=3)
    assert "neon_pink" in {p.material for p in club.parts}
    assert "sign" in club.attachments


def test_ad_kinds():
    for kind in ("wall", "holo", "rooftop", "lantern"):
        spec = {"id": f"ad-{kind}", "kind": kind, "position": [0, 5, 0], "rotation": 0,
                "size": [2, 1.5], "color": "neon_cyan", "frame": "dark_metal"}
        ad = props.build_ad(spec, seed=4)
        assert any(p.material in ("neon_cyan", "holo_panel", "warm_light") for p in ad.parts), kind


def test_cable_sags_between_endpoints():
    spec = {"id": "cable-01", "from": [0, 8, 0], "to": [10, 6, 0], "sag": 1.5, "radius": 0.04}
    cable = props.build_cable(spec)
    ys = [v[1] for p in cable.parts for v in p.vertices]
    assert min(ys) <= 5.6  # 中央で端点(y=8/6)より sag=1.5 分下がる（中点 ≈ 5.5）


def test_rubble_prototypes_are_small():
    protos = props.rubble_prototypes()
    assert len(protos) == 3
    for proto in protos:
        span = max(max(v[i] for v in proto.vertices) - min(v[i] for v in proto.vertices) for i in range(3))
        assert span < 1.2, proto.name
```

- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: props.py を実装**（上記レシピ。各 builder は rng = random.Random(seed + hash_of_id は不安定なので、seed + id 末尾数字 のような安定オフセットを使用）
- [ ] **Step 4: テスト成功**
- [ ] **Step 5: layout 全件でスモーク**（uv run python -c: stalls/shacks/nightlife/ads/cables を全 spec 分生成し、 Assembly 生成が例外なく完了、parts 総数 < 3000 を確認）
- [ ] **Step 6: コミット** — `git commit -m "feat(akichi): add slum prop builders (stalls, shacks, clubs, ads, cables, rubble)

Co-Authored-By: Claude Code <noreply@anthropic.com>"`

---

### Task 6: build.py — セクタ別 .blend 生成 CLI

**Files:**
- Create: `akichi/modeling/akichi/build.py`
- Test: `akichi/tests/akichi/test_build_helpers.py`

**Interfaces:**
- Consumes: 上記全モジュール + `layout.build_layout()`
- Produces:
  - CLI: `resoloop blender run modeling/akichi/build.py --arg=--sector --arg=<name> --arg=--output --arg=artifacts/akichi/<name>.blend --json`（`sys.argv.index("--")` 以降を argparse で読む。tokyo_nova build.py と同型）
  - セクタ名: `ground|vacant|towers|market|shacks|nightlife|ads`
  - `build.resonite_to_blender(point) -> tuple`（(x,y,z)→(x,z,y)）
  - `build.batch_assembly(assembly) -> dict[str, MeshData]` — Assembly の parts を material ごとに 1 メッシュへマージ（頂点連結 + face インデックスオフセット。名前 `<assembly.name>__<material>`）
  - `build.write_scene(sector, output_path) -> dict` — bpy 環境で呼ぶ。コレクション構成: `Akichi<Sector>`（編集可能ソース）と `Akichi<Sector>Export`（export 用: material バッチ mesh、metric UV 適用済み、GN realize 済み）。リソースレポート dict を返し、`artifacts/akichi/<sector>-report.json` にも保存
  - `build.resource_report(assemblies, sector) -> dict`

**セクタ → 内容:**
- `ground`: 地面 plane 100×100（`asphalt_cracked`、厚 0.2 の box）+ streets 帯（`asphalt_cracked` より明るいパッチ or `asphalt_wet` の水たまり薄 box 8〜15 枚、vacant 内は `mud` パッチ）+ 外周廃壁（buildings.build_perimeter_wall）+ vacant 区域の `mud`/瓦礫下地 plane
- `vacant`: rubble_prototypes を GN scatter（下記）+ vehicle_husk 2 台 + junk_pile 3 + 大型コンクリート塊（rubble-chunk の 3〜5 倍スケール版を rng 配置 6 個）+ 中央に倒壊構造物（beveled_box 積み重ね）
- `towers`: layout.towers 全 10 棟
- `market`: stalls 12 + junk_pile 各屋台脇 1 + 地面パッチ
- `shacks`: shacks 10 + 周囲に junk_pile 5 + cable 4
- `nightlife`: clubs 4 + ads kind=wall のうち club 隣接分 + cable 4
- `ads`: 残り全 ads + cable 4（cables のセクタ割り当ては index 順で固定: `cables[0:4]` → shacks、`cables[4:8]` → nightlife、`cables[8:12]` → ads）

**GN realize メッシュの UV 監査除外**: scatter で realize した瓦礫メッシュは原型が UV を持たないため `uv_triangle_issues` 監査の対象外とし、レポートに `"gn_scatter_uv_exempt": true` を記録する。UV 監査（uv_issue_count）は material バッチメッシュのみに適用する。

**GN scatter（vacant のみ、geometry-nodes スキル準拠）:**
1. scatter 対象 plane（vacant 矩形）に Geometry Nodes modifier を追加。ノードグループは最小構成: `Distribute Points on Faces`（density 0.35/m²、seed 固定 250925）→ 3 prototype を `Instance on Points`（`Random Index` で選択、seed 固定）→ ランダム回転（`Random Value` rotation、seed 固定）→ `Realize Instances`
2. **ノードタイプ名・ソケット名は実行前に `bpy.types.GeometryNodeDistributePointsOnFaces` 等の RNA を確認して使う**（推測禁止）
3. export コピーでは depsgraph 評価で realize 済みメッシュを取得し、GN modifier なしの static mesh として `...Export` コレクションに配置（authoring グラフはソースコレクションの .blend に保持）
4. **フォールバック**: Blender 5.0 の RNA 確認で GN 構築に 2 回失敗したら、`random.Random(250925)` の Python scatter（同一密度・同一 prototype）に切り替え、レポートに `"scatter_method": "python-fallback"` を記録（GN なら `"geometry-nodes"`）。density 0.35/m² × 約 1064m² ≒ 370 インスタンス → 370 × 概算 40 tri ≒ 15k tri 予算

**material バッチと UV:**
- batch_assembly の各マージメッシュの全 face に `uv.metric_face_uvs(points, normal, uv_per_meter=0.5)` を適用し、`uv.uv_triangle_issues(..., handedness=-1)`（XZY 変換後）で監査。issues があればレポートにカウントを記録（0 が目標）
- Blender マテリアルは `make_blender_materials()` で 1 回だけ生成し共用

**レポートスキーマ**（tokyo_nova city-resource-report.json に倣う）:

```python
{"schema_version": 1, "sector": "vacant", "seed": 250925,
 "assembly_count": N, "total_parts": N, "total_vertices": N, "total_triangles": N,
 "blender_object_count": N, "material_count": N, "scatter_method": "geometry-nodes"|"python-fallback",
 "uv_issue_count": N, "blend_path": "...", "blender_version": "5.0.1"}
```

- [ ] **Step 1: 失敗するテストを書く**（純粋 Python ヘルパのみ単体テスト。bpy 依存部は Task 7 の実行で検証）

```python
from modeling.akichi import build, geometry


def test_resonite_to_blender_swaps_yz():
    assert build.resonite_to_blender((1, 2, 3)) == (1, 3, 2)


def test_batch_assembly_merges_by_material():
    from modeling.akichi.buildings import Assembly
    a = Assembly(kind="test", name="t1", origin=(0, 0, 0), rotation=0.0)
    a.parts.append(geometry.box("p1", (0, 0, 0), (1, 1, 1), "rust"))
    a.parts.append(geometry.box("p2", (2, 0, 0), (1, 1, 1), "rust"))
    a.parts.append(geometry.box("p3", (4, 0, 0), (1, 1, 1), "dark_metal"))
    batched = build.batch_assembly(a)
    assert set(batched) == {"t1__rust", "t1__dark_metal"}
    assert len(batched["t1__rust"].vertices) == 16
    assert len(batched["t1__rust"].faces) == 12


def test_batch_offset_is_correct():
    from modeling.akichi.buildings import Assembly
    a = Assembly(kind="test", name="t2", origin=(0, 0, 0), rotation=0.0)
    a.parts.append(geometry.box("p1", (0, 0, 0), (1, 1, 1), "rust"))
    a.parts.append(geometry.box("p2", (10, 0, 0), (1, 1, 1), "rust"))
    merged = build.batch_assembly(a)["t2__rust"]
    xs = [v[0] for v in merged.vertices]
    assert min(xs) == -0.5 and max(xs) == 10.5
```

- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: build.py を実装**（argparse エントリ + 上記ヘルパ + write_scene の bpy 実装。bpy import は関数内で行い、単体テストがヘッドレスでも import 可能にする）
- [ ] **Step 4: テスト成功**
- [ ] **Step 5: コミット** — `git commit -m "feat(akichi): add sector build CLI with material batching and GN scatter

Co-Authored-By: Claude Code <noreply@anthropic.com>"`

---

### Task 7: 全セクタの .blend 生成実行 + レポート検証

**Files:**
- Create: `akichi/artifacts/akichi/*.blend`（7ファイル）、`akichi/artifacts/akichi/*-report.json`

**Interfaces:**
- Consumes: Task 6 の CLI
- Produces: 7 セクタの .blend + レポート（Task 8 の export 入力）

- [ ] **Step 1: 7 セクタを順にビルド**（各コマンドは最大 900s。`monitoring-long-tasks` に従い同期実行）

```bash
cd /workspaces/reso-world/akichi
for s in ground vacant towers market shacks nightlife ads; do
  resoloop blender run modeling/akichi/build.py --arg=--sector --arg=$s \
    --arg=--output --arg=artifacts/akichi/$s.blend --json
done
```

各出力の `"ok": true` を確認。失敗セクタがあればエラーメッセージを修正して再実行（.blend は上書き）。

- [ ] **Step 2: レポート検証**

```bash
uv run python - <<'EOF'
import json, pathlib
total_tri = total_verts = 0
for report in sorted(pathlib.Path("artifacts/akichi").glob("*-report.json")):
    data = json.loads(report.read_text())
    print(data["sector"], "tri:", data["total_triangles"], "obj:", data["blender_object_count"],
          "mat:", data["material_count"], "uv_issues:", data["uv_issue_count"],
          "scatter:", data.get("scatter_method", "n/a"))
    total_tri += data["total_triangles"]; total_verts += data["total_vertices"]
    assert data["uv_issue_count"] == 0, data["sector"]
print("TOTAL tri:", total_tri, "verts:", total_verts)
assert total_tri < 250000  # tokyo_nova 実績 169k を上限目安に
EOF
```

Expected: 7 セクタ分出力、uv_issue_count 全 0、合計 < 250k triangles。閾値超過時は密度・窓ピッチを落として Task 6 のコードを修正 → 再生成。

- [ ] **Step 3: .blend 再オープン検証**（save/pack の完全性: 各 .blend を再度開き、メッシュオブジェクト数とレポートの `blender_object_count` 一致を確認するスクリプトを `resoloop blender run` で実行）
- [ ] **Step 4: コミット** — .blend はバイナリのため artifacts の .gitignore 方針を確認（tokyo_nova は tracked blend を commit 済み → 同様に `git add akichi/artifacts/akichi/` でコミット。サイズが 50MB を超える場合はレポートと source のみコミットし、.blend は LFS 方針をユーザに確認）。既定: レポート JSON + build ソースをコミット、`git commit -m "feat(akichi): generate seven sector blends with resource reports

Co-Authored-By: Claude Code <noreply@anthropic.com>"`

---

### Task 8: セクタ別 export bundle 生成

**Files:**
- Create: `akichi/content/akichi/<sector>-v1/`（model.apply.json、*.mesh.json、report.json）× 7

- [ ] **Step 1: 事前確認** — export は `--parent` に検証済み Slot ID を要求するが、オフライン export では未検証でもよい（apply 時に検証）。統合 manifest の parent は Task 9 で決めるため、ここでは `--collection Akichi<Sector>Export` を明示してセクタ単体 bundle を作る

```bash
cd /workspaces/reso-world/akichi
for s in ground vacant towers market shacks nightlife ads; do
  resoloop blender export artifacts/akichi/$s.blend --output content/akichi/$s-v1 \
    --name $(echo $s | sed 's/./\u&/') --collection Akichi$(echo $s | sed 's/./\u&/')Export --json
done
```

（`--name` は `Ground`/`Vacant`/`Towers`/`Market`/`Shacks`/`Nightlife`/`Ads`。collection 名と一致させる）

- [ ] **Step 2: 各 bundle の report.json を検証** — mesh 数・material 数・triangles が Task 7 レポートと整合、`"warnings"` に missing image/unsupported material がないこと（テクスチャ不使用なので image 警告は出ないはず）
- [ ] **Step 3: bundle ごとのオフライン validate**

```bash
for s in ground vacant towers market shacks nightlife ads; do
  resoloop validate content/akichi/$s-v1/model.apply.json --json
done
```

Expected: 全 bundle OK（parent 未検証の警告は可）

- [ ] **Step 4: コミット** — `git add akichi/content/akichi && git commit -m "feat(akichi): export seven sector bundles

Co-Authored-By: Claude Code <noreply@anthropic.com>"`（mesh.json が巨大な場合は .gitignore に `content/akichi/*/*.mesh.json` を追加し、apply.json と report.json のみコミット。判断は実行者に委ね、判断を作業報告に記録する）

---

### Task 9: pipeline.py — 統合 manifest 生成

**Files:**
- Create: `akichi/modeling/akichi/pipeline.py`
- Create: `akichi/content/akichi/akichi-slum.json`（生成物）
- Test: `akichi/tests/akichi/test_pipeline.py`

**Interfaces:**
- Consumes: 7 bundle の `model.apply.json`、`layout.build_layout()`（signs 用）
- Produces:
  - `pipeline.build_unified_manifest(bundle_dir: Path) -> dict`
  - `pipeline.main()` — `uv run python -m modeling.akichi.pipeline` で `content/akichi/akichi-slum.json` を書き出す

**統合 manifest の構造:**

```python
{
  "schemaVersion": "1",
  "ownership": {"key": "akichi"},
  "slot": {"key": "root", "name": "Akichi_Slum", "parent": "Root",
           "position": [0, 0, 0], "scale": [1, 1, 1]},
  "assets": {  # 各 bundle の mesh/texture asset をマージ（キー衝突時は "<sector>-<元キー>" にリネームし参照も追随）
    ...
  },
  "children": [
    # セクタごとに 1 子 Slot（key: "sector-<name>", name: "Akichi_<Sector>"）
    # 各子 Slot の components に bundle の mesh Slot 定義を展開
    # （bundle 側 root の children をこのセクタ Slot の children として取り込む。
    #   bundle root 自体の slot name はセクタ名に置換）
    # TextRenderer 看板（layout["signs"]）:
    #   exporter は階層をフラット化しワールド変換を mesh 頂点にベイクするため、
    #   mesh Slot への相対 offset ではなく**絶対座標でセクタ Slot 直下に配置する**。
    #   位置 = attach_to の Assembly origin + offset（Y 軸回転 rotation を適用）、
    #   回転 = attach_to の rotation から Y 軸クォータニオンを計算。
    #   子 Slot: {"key": "sign-NN", "name": "Sign_NN", "position": [絶対座標],
    #     "rotation": [qx,qy,qz,qw],
    #     "components": [{"key": "sign-text-NN", "type": "FrooxEngine.TextRenderer",
    #       "fields": {"Text": "...", "Size": size, "Color": color, "Alignment": "Center"}}]}
    #   配置先セクタ: nightlife の signs → sector-nightlife、stall → sector-market、
    #   ad → sector-ads
  ],
  "cameras": {
    "overview-north": {"position": [0, 45, -75], "target": [0, 5, 10], "fieldOfView": 60, "width": 1280, "height": 720, "representative": true},
    "vacant-street": {"position": [0, 1.7, -30], "target": [0, 3, 15], "fieldOfView": 70, "width": 1280, "height": 720},
    "market-close": {"position": [26, 1.7, -4], "target": [22, 1.5, 4], "fieldOfView": 70, "width": 1280, "height": 720},
    "nightlife-alley": {"position": [-4, 1.7, 32], "target": [6, 3, 28], "fieldOfView": 70, "width": 1280, "height": 720}
  },
  "tests": [
    {"name": "root-exists", "assertions": [{"target": "$slot:root", "exists": true}]},
    # 各セクタ Slot の exists + 主要 emissive material Slot の exists
  ]
}
```

**コライダー宣言**（resonite-build の所有領域なので manifest に含める）:
- ground セクタの子 Slot に `FrooxEngine.BoxCollider`（center [0,-0.1,0]、size [100,0.2,100]）または `StaticMeshCollider`（Mesh の $asset 参照）— **StaticMeshCollider を第一候補**とし、`resoloop type describe FrooxEngine.StaticMeshCollider --json` で Reflection 検証してから宣言（Mesh フィールド名を推測しない）
- towers 各棟に `FrooxEngine.BoxCollider`（footprint × height、中心は棟中心）。10 棟のみで軽量
- 小さい props（stall/shack/club）はコライダーなし（接触は許容）— 実機 QA で必要なら追加

- [ ] **Step 1: 失敗するテストを書く**

```python
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
    assert sectors == {f"sector-{s}" for s in ("ground","vacant","towers","market","shacks","nightlife","ads")}
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
```

- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: pipeline.py を実装**（bundle の apply.json マージ、asset キー衝突リネーム、TextRenderer Slot 注入、collider 宣言、cameras/tests 付与。書き込みは `json.dumps(..., ensure_ascii=False, indent=2)`）
- [ ] **Step 4: テスト成功**
- [ ] **Step 5: オフライン validate** — `resoloop validate content/akichi/akichi-slum.json --json` → OK（strict は接続後の Task 10）
- [ ] **Step 6: コミット** — `git commit -m "feat(akichi): add unified manifest pipeline with signs and colliders

Co-Authored-By: Claude Code <noreply@anthropic.com>"`

---

### Task 10: Resonite 接続・strict validate・apply・収束確認

**Files:**
- Create: `akichi/.resoloop/akichi/state/akichi-slum.json`（apply state、コミット対象）

**前提:** Resonite が起動し ResoniteLink が入っていること。未起動なら**ユーザに起動を依頼する（計画全体で唯一許容される中断）**。

- [ ] **Step 1: discover + doctor**

```bash
cd /workspaces/reso-world/akichi
resoloop discover --json
# 候補1件なら自動接続、複数ならユーザに選択を問う（AGENTS.md）
resoloop doctor --url <URL> --json
resoloop status --url <URL> --json
```

`status` で Root 直下の既存コンテンツを観察し、`Akichi_Slum` と同名の既存 Slot がないこと・所有境界外に触れないことを確認。

- [ ] **Step 2: strict validate + diff**

```bash
resoloop validate content/akichi/akichi-slum.json --strict --url <URL> --json
resoloop diff content/akichi/akichi-slum.json --changes-only --url <URL> --json
```

Expected: strict OK、diff の変更は新規作成のみ（既存 Slot の変更・削除が 0 件）。StaticMeshCollider のメンバ名エラーが出たら `resoloop type describe FrooxEngine.StaticMeshCollider --json` で正しいメンバ名に修正し、Task 9 のコード・manifest を更新して再実行。

- [ ] **Step 3: apply**

```bash
resoloop apply content/akichi/akichi-slum.json --state .resoloop/akichi/state/akichi-slum.json --url <URL> --json
```

mesh asset import は時間がかかる。Bash ツールの timeout 上限は 600000ms なので、長時間化が予想される場合は `monitoring-long-tasks` スキルに従い `run_in_background` で実行し進捗を監視する。タイムアウト時は state を保持したまま `status` で進捗を確認し、`.resoloop.json` の `commandTimeoutSeconds`（既定 900）を引き上げて再実行。焦って中断しない。

- [ ] **Step 4: 再 apply で収束確認**

```bash
resoloop apply content/akichi/akichi-slum.json --state .resoloop/akichi/state/akichi-slum.json --url <URL> --json
```

Expected: 冗長な書き込み/import なし（収束）。差分が出る場合は原因（UV 微差・タンジェント等）を特定し、manifest を修正して収束するまで繰り返す。

- [ ] **Step 5: コミット** — state ファイル + 修正があれば manifest をコミット `git commit -m "feat(akichi): apply slum district to Resonite with converged state

Co-Authored-By: Claude Code <noreply@anthropic.com>"`

---

### Task 11: 実機 QA・audit・納品レポート

- [ ] **Step 1: カメラ撮影**（manifest の 4 カメラブックマーク）

```bash
resoloop capture --camera overview-north --output artifacts/akichi/qa-overview.png --url <URL> --json
# 以下 vacant-street / market-close / nightlife-alley も同様に
```

（`capture` の正確なサブコマンド名は `resoloop --help` で確認。tokyo_nova では manifest cameras を使用）

- [ ] **Step 2: 3 距離レビュー** — 画像を Read で確認:
  - 遠景（overview）: シルエットに廃ビル群・空地・屋台街が読み取れるか
  - 中景（vacant-street, market-close）: 素材分離・ネオン emissive が光っているか・瓦礫密度
  - 近接（nightlife-alley）: サイン TextRenderer の日本語が読めるか、ネオン枠・カーテン・張り紙の存在感
  - 問題があれば該当セクタの build コードを修正 → 再生成 → re-export → 再 apply（収束確認）→ 再撮影

- [ ] **Step 3: item audit** — `resoloop item audit --url <URL> --json`（所有 root 配下）。external role 警告は `issues`/`externalRoleCandidates` を確認し、必要ならレビューのうえ `--allow-external-role`

- [ ] **Step 4: 納品レポート作成** — `akichi/artifacts/akichi/delivery-report.json`:

```python
{"delivered_at": "...", "total_triangles": N, "total_vertices": N, "mesh_count": N,
 "material_count": N, "draw_sections": N, "texture_count": 0,
 "colliders": {"StaticMeshCollider": 1, "BoxCollider": 10},
 "lights_added": 0, "driving_components": 0,
 "pending": [ ...未実施の検査があれば明記... ],
 "sector_reports": [7件のサマリ], "notes": "advisory 閾値超過の根拠など"}
```

- [ ] **Step 5: 最終コミット** — `git commit -m "feat(akichi): complete cyberpunk slum delivery with QA report

Co-Authored-By: Claude Code <noreply@anthropic.com>"`
- [ ] **Step 6: ユーザへ完了報告** — 所要時間・Task 別内訳、リソース合計、QA 画像の所見、pending 項目を日本語で報告
