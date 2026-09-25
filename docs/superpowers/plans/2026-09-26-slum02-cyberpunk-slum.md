# slum02 高品質サイバーパンク・スラム街 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 80×80m のサイバーパンク・スラム街（中央 20×20m の廃工場跡地、東の巨大壁のスプレーアート `トーキョーN◎VA`、廃ビル・屋台・風俗店・掘っ立て小屋・半透明 AR ホロ広告、外周の視線遮断と遠景）を Blender で生成し、頂点カラー＋エンジン内ノイズで素材表現して Resonite にライブ適用する。

**Architecture:** 純 Python の決定論レイアウト（Resonite 座標、Y up）→ 純 Python のメッシュ部品生成（`MeshData` / `Assembly`）→ Blender でセクタ別 .blend（1 オブジェクト = 1 メッシュ、素材ごとにサブメッシュ、頂点カラー＝汚れマスク × AO ベイク）→ `resoloop blender export --preserve-hierarchy` → 純 Python の統合＋後処理（`PBS_Metallic` → `PBS_VertexColorMetallic`＋`NoiseTexture`、ホロ＝`FresnelMaterial`＋`Panner2D`/`Spinner`、`Light`、コライダー、TextRenderer）→ validate / strict / diff / apply / 再 apply 収束。akichi のパイプライン骨格（`/workspaces/reso-world/akichi/modeling/akichi/`）を流用し、ジェネレータは新規。

**Tech Stack:** Python 3.12+（uv、pytest）、Blender 5.0.1（bpy / bmesh、Geometry Nodes、Cycles AO ベイク）、resoloop 0.1.0-preview.14、Resonite 2026.9.18.82 / ResoniteLink 0.13.1（`ws://localhost:53724/`）

**Spec:** `docs/superpowers/specs/2026-09-26-slum02-cyberpunk-slum-design.md`

## Global Constraints

- プロジェクトルート: `/workspaces/reso-world/slum02/`。コマンドは特記なき限りこのディレクトリで実行する
- Python は必ず `uv run ...`。`python3` を直接使わない
- Blender 実行は `resoloop blender run modeling/slum02/build.py --arg=... --json`（bpy data API / bmesh / mathutils 優先）
- 規模: 80×80m（x, z ∈ [-40, 40]）、中央広場 20×20m（x, z ∈ [-10, 10]）、北 = +Z、Y up、単位 m
- 所有 root slot `Slum02_Slum`、ownership key `slum02`、root slot key `root`、parent `Root`
- 接続: `ws://localhost:53724/`。state: `.resoloop/slum02/state/slum02.json`
- 画像テクスチャ不使用。テクスチャは `NoiseTexture`（エンジン内生成）のみ
- 空（`Root/Skybox`）・霧・ワールド照明・`Root/Ground`・`Akichi_Slum` は一切変更しない
- 1 オブジェクト = 1 メッシュ（建物 1 棟、屋台 1 軒 … が 1 つの Blender オブジェクト、素材はサブメッシュ）
- 風俗店は示唆的表現のみ（ネオン、シャッター、ビーズカーテン、張り紙、赤い照明）。露骨なコンテンツは作らない
- 型名・メンバー・enum は下表（2026-09-26 に実機 Reflection で取得）を使う。表にないものは `resoloop type describe` で確認してから使う
- 予算目安: 全体 40〜60 万三角形（backdrop は 2 万以下）、マテリアル 30〜40 種、Light 20〜30 灯（影ありは 3 灯以下）
- 固定シード `SEED = 260926`
- コミットは各タスク末尾。コミットメッセージ末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- 各タスクの作業報告に着手〜完了の所要時間を記録する（`artifacts/slum02/timing.md` に追記）

### Reflection 済みの型・メンバー・enum（2026-09-26 実機取得）

| 型 | 使うメンバー | enum |
|---|---|---|
| `FrooxEngine.PBS_VertexColorMetallic` | AlbedoColor(colorX) AlbedoTexture(ref ITexture2D) TextureScale(float2) TextureOffset(float2) EmissiveColor(colorX) Metallic(float) Smoothness(float) VertexColorTarget VertexColorInterpolationSpace AlphaHandling Culling | VertexColorTarget: Albedo/Emissive/Metallic、VertexColorInterpolationSpace: Linear/sRGB/sRGBAlpha、AlphaHandling: Opaque/AlphaClip/AlphaBlend、Culling: Off/Front/Back |
| `FrooxEngine.NoiseTexture` | Size(int2) Seed(int) Monochrome(bool) MonochromeMin(colorX) MonochromeMax(colorX) Bias(float) Gain(float) FilterMode WrapModeU WrapModeV Mipmaps(bool) | FilterMode: Point/Bilinear/Trilinear/Anisotropic、WrapMode: Repeat/Clamp/Mirror/MirrorOnce |
| `FrooxEngine.FresnelMaterial` | NearColor FarColor(colorX) Exponent GammaCurve(float) NearTexture FarTexture(ref) NearTextureScale NearTextureOffset FarTextureScale FarTextureOffset(float2) BlendMode Sidedness ZWrite UseVertexColors(bool) | BlendMode: Opaque/Cutout/Alpha/Transparent/Additive/Multiply、Sidedness: Auto/Front/Back/Double、ZWrite: Auto/Off/On |
| `FrooxEngine.Panner2D` | _target(ref IField<float2>) _speed(float2) _repeat(float2) _offset(float2) PingPong(bool) | — |
| `FrooxEngine.Spinner` | _target(ref IField<floatQ>) _speed(float3) Range(float3) _offset(floatQ) | — |
| `FrooxEngine.Light` | LightType Intensity(float) Color(colorX) ShadowType ShadowStrength(float) Range(float) SpotAngle(float) | LightType: Point/Directional/Spot、ShadowType: None/Hard/Soft |
| `FrooxEngine.BoxCollider` | Type Size Offset(float3) CharacterCollider(bool) | Type: NoCollision/Static/… |
| `FrooxEngine.TextRenderer` | Text Size Color HorizontalAlign VerticalAlign | HorizontalAlign: Left/Center/Right/Justify、VerticalAlign: Top/Middle/Bottom |

参照記法: コンポーネント参照 `$component:KEY`、コンポーネントのメンバー `$member:KEY.Member`、Slot のフィールド `$slot-member:SLOTKEY.Rotation`、アセット `$asset:KEY`。enum は名前文字列で書く（akichi の manifest で `"Type": "Static"`、`"HorizontalAlign": "Center"` が strict validate を通過済み）。

## Review Focus

1. **視線の抜け**: 広場のどこから見ても 80×80m の外（グリッド地面、何もない地平線）が見えてはいけない。レイキャスト試験（Task 3）と、生成メッシュが遮蔽ボリュームを実際に満たすことの build 後検査（Task 13）で担保する
2. **頂点カラーの色空間**: exporter が頂点カラーを線形で書くか sRGB で書くかで、`VertexColorInterpolationSpace` を誤ると全体が白飛び/黒つぶれする。Task 4 で実測して `postprocess.VERTEX_COLOR_SPACE` に固定し、テストで固定値を検証する
3. **共有マテリアルの駆動**: `Panner2D` が共有ホロマテリアルを駆動すると同色の全広告が一斉に流れる。スクロール広告はスクロール専用マテリアル（`holo_*_scroll`）を使い、静止広告と共有しない（Task 14 のテスト）
4. **スプレー文字の欠字**: フォントに `◎` がないと文字が消える。`◎` は常に自前ジオメトリ（二重リング）で作り、文字列は `トーキョーN` / `◎` / `VA` に分けて配置する（Task 6 のテスト）
5. **瓦礫の埋没と浮き**: akichi は頂点の 70% が地面下に埋まっていた。瓦礫インスタンスの地面上露出率 ≥ 45% をテストで担保する（Task 7。プロトタイプの沈み込み上限は Task 7 の純 Python テスト、ビルド後の露出率は Blender フックの RuntimeError）

---

## File Structure

```
slum02/
  pyproject.toml                    # Task 0
  .gitignore                        # Task 0 (tmp/, __pycache__/, .venv/)
  assets/fonts/DelaGothicOne-Regular.ttf, OFL.txt   # Task 0
  modeling/__init__.py
  modeling/slum02/__init__.py
  modeling/slum02/geometry.py       # Task 1: MeshData / primitives / subdivision / wall openings / tubes / Assembly / merge
  modeling/slum02/materials.py      # Task 2: MaterialSpec palette, NoiseSpec, Blender material creation
  modeling/slum02/vcolor.py         # Task 2: pure vertex-colour wear masks
  modeling/slum02/layout.py         # Task 3: deterministic layout + validation + occluders + sightline raycast
  modeling/slum02/uv.py             # Task 4: metric face UVs + audit (ported from akichi uv.py)
  modeling/slum02/blender_io.py     # Task 4: bpy object creation, UV, colour attributes, AO bake, save/reopen
  modeling/slum02/build.py          # Task 4: sector dispatcher + CLI (resoloop blender run)
  modeling/slum02/preview.py        # Task 4: small preview render (self-review only)
  modeling/slum02/ground.py         # Task 5: ground + backdrop
  modeling/slum02/plaza.py          # Task 6-7: factory remains, east wall (pure) + rubble scatter, spray art (Blender hook)
  modeling/slum02/towers.py         # Task 8
  modeling/slum02/stalls.py         # Task 9
  modeling/slum02/nightlife.py      # Task 10
  modeling/slum02/shacks.py         # Task 11
  modeling/slum02/ads.py            # Task 12
  modeling/slum02/overhead.py       # Task 13
  modeling/slum02/postprocess.py    # Task 14
  modeling/slum02/pipeline.py       # Task 14
  tests/__init__.py, tests/slum02/__init__.py, tests/slum02/test_*.py
  content/slum02/layout.json, <sector>-v1/, slum02.json
  artifacts/slum02/<sector>.blend, <sector>-report.json, preview/<sector>-*.png, delivery-report.json, timing.md
```

セクタ一覧（`build.SECTORS`、この順で固定）:
`ground, plaza, towers-a, towers-b, towers-c, market, nightlife, shacks, ads, overhead, backdrop`

---

### Task 0: スキャフォールド

**Files:**
- Create: `slum02/pyproject.toml`, `slum02/.gitignore`, `slum02/modeling/__init__.py`, `slum02/modeling/slum02/__init__.py`, `slum02/tests/__init__.py`, `slum02/tests/slum02/__init__.py`, `slum02/tests/slum02/test_scaffold.py`
- Create: `slum02/assets/fonts/DelaGothicOne-Regular.ttf`, `slum02/assets/fonts/OFL.txt`
- Create: `slum02/artifacts/slum02/timing.md`

**Interfaces:**
- Produces: `modeling.slum02` パッケージ、`FONT_PATH = PROJECT_ROOT / "assets/fonts/DelaGothicOne-Regular.ttf"`（`modeling/slum02/__init__.py`）

- [ ] **Step 1: pyproject / gitignore / パッケージ**

`slum02/pyproject.toml`:
```toml
[project]
name = "slum02"
version = "0.1.0"
description = "High-quality cyberpunk slum generator for Resonite via resoloop + Blender"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

`slum02/.gitignore`:
```
tmp/
__pycache__/
.venv/
.resoloop/cache/
```

`slum02/modeling/__init__.py`: 空。`slum02/tests/__init__.py`, `slum02/tests/slum02/__init__.py`: 空。

`slum02/modeling/slum02/__init__.py`:
```python
"""slum02 high-quality cyberpunk slum: layout -> Blender sectors -> Resonite bundles.

pytest covers the pure Python layers (``uv run pytest tests/slum02 -q``). Blender
runs through ``resoloop blender run modeling/slum02/build.py``.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FONT_PATH = PROJECT_ROOT / "assets" / "fonts" / "DelaGothicOne-Regular.ttf"
SEED = 260926
```

- [ ] **Step 2: フォント取得（OFL）**

```bash
mkdir -p assets/fonts
curl -fsSL -o assets/fonts/DelaGothicOne-Regular.ttf https://github.com/google/fonts/raw/main/ofl/delagothicone/DelaGothicOne-Regular.ttf
curl -fsSL -o assets/fonts/OFL.txt https://github.com/google/fonts/raw/main/ofl/delagothicone/OFL.txt
file assets/fonts/DelaGothicOne-Regular.ttf
```
Expected: `TrueType Font data`。失敗した場合は `FONT_PATH` を残したまま Task 7 で TextRenderer フォールバックを使う（Task 7 Step 4 に分岐あり）。

- [ ] **Step 3: スモークテストを書く**

`tests/slum02/test_scaffold.py`:
```python
from modeling.slum02 import FONT_PATH, PROJECT_ROOT, SEED


def test_project_root_is_slum02():
    assert PROJECT_ROOT.name == "slum02"
    assert SEED == 260926


def test_font_present_with_license():
    assert FONT_PATH.is_file() and FONT_PATH.stat().st_size > 100_000
    assert (FONT_PATH.parent / "OFL.txt").is_file()
```

- [ ] **Step 4: 実行**

Run: `uv run pytest tests/slum02 -q`
Expected: 2 passed

- [ ] **Step 5: Blender / resoloop 疎通**

```bash
resoloop blender find --json
resoloop doctor --url ws://localhost:53724 --json
```
Expected: Blender 5.0.1 検出、`resonite-connection: pass`。

- [ ] **Step 6: timing.md 作成とコミット**

`artifacts/slum02/timing.md`:
```markdown
# slum02 作業時間記録

| Task | 着手 | 完了 | 所要 | メモ |
|---|---|---|---|---|
```
```bash
cd /workspaces/reso-world && git add slum02/pyproject.toml slum02/uv.lock slum02/.gitignore slum02/modeling slum02/tests slum02/assets slum02/artifacts/slum02/timing.md slum02/AGENTS.md slum02/.resoloop.json slum02/.agents slum02/content slum02/flux
git commit -m "feat(slum02): scaffold uv project, font and smoke tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 1: geometry 基盤（部品・細分割・開口付き壁・チューブ・Assembly 統合）

**Files:**
- Create: `slum02/modeling/slum02/geometry.py`
- Test: `slum02/tests/slum02/test_geometry.py`

**Interfaces:**
- Produces:
  - `Vec3 = tuple[float, float, float]`, `Face = tuple[int, ...]`
  - `@dataclass(frozen=True) MeshData(name: str, vertices: tuple[Vec3,...], faces: tuple[Face,...], material: str)`
  - `mesh(name, vertices, faces, material) -> MeshData`
  - `box(name, center, size, material) -> MeshData`
  - `beveled_box(name, center, size, bevel, material) -> MeshData`（akichi から移植）
  - `cylinder(name, center, radius, height, segments, material, axis="Y") -> MeshData`（移植）
  - `prism(name, center, size, material) -> MeshData`（移植）
  - `pipe(name, start, end, radius, material, segments=8) -> MeshData`（移植）
  - `subdivided_box(name, center, size, max_edge, material) -> MeshData` — 各面を `max_edge` 以下の格子に分割した閉じた箱
  - `wall_with_openings(name, width, height, thickness, openings, recess, max_edge, material, closed=True) -> MeshData` — ローカル座標で x∈[-w/2,w/2]、y∈[0,h]、z∈[-t/2,t/2]、前面は +Z。`openings` は `(x0, y0, x1, y1)` の列で、そこは `recess` だけ凹む（貫通しない）。`closed=False` なら背面と 4 端面を省く（建物内側など見えない面の削減用）
  - `GridBuilder` — 頂点を共有しながら格子状の四角形を積む公開ビルダー（`v(point)`, `quad(a,b,c,d)`, `grid(origin, u, w, us, ws, skip)`, `build(name, material)`）
  - `tube(name, points, radius, sides, material) -> MeshData` — 折れ線に沿った開いた管（両端キャップあり）
  - `catenary(a, b, sag, segments) -> list[Vec3]`
  - `rotate_y(point, radians) -> Vec3`（右手系、+Y 回り: x' = x cos + z sin, z' = -x sin + z cos）
  - `transformed(mesh, radians, offset, name=None) -> MeshData`
  - `rotate_xyz(point, rx, ry, rz) -> Vec3`（X 軸 → Y 軸 → Z 軸の順に右手系で回転。傾いた柱・瓦礫用）
  - `transformed_xyz(mesh, rx, ry, rz, offset, name=None) -> MeshData`
  - `bounds(meshes: Iterable[MeshData]) -> tuple[Vec3, Vec3]`
  - `triangle_count(mesh) -> int`
  - `@dataclass Assembly(kind: str, name: str, sector: str, origin: Vec3, parts: list[MeshData], meta: dict = {})` — parts は origin 相対のローカル座標（回転は生成時に `transformed` で焼き込む）
  - `@dataclass(frozen=True) MergedMesh(name, vertices, faces, face_materials: tuple[int,...], materials: tuple[str,...])`
  - `merge_assembly(assembly) -> MergedMesh` — 素材は初出順、ローカル座標のまま

- [ ] **Step 1: 失敗するテストを書く**

`tests/slum02/test_geometry.py`:
```python
import math

import pytest

from modeling.slum02 import geometry as g


def _closed(mesh):
    """Every undirected edge is shared by exactly two faces."""
    edges = {}
    for face in mesh.faces:
        for a, b in zip(face, (*face[1:], face[0])):
            key = (min(a, b), max(a, b))
            edges[key] = edges.get(key, 0) + 1
    return all(count == 2 for count in edges.values())


def _signed_volume(mesh):
    total = 0.0
    for face in mesh.faces:
        p0 = mesh.vertices[face[0]]
        for i in range(1, len(face) - 1):
            p1, p2 = mesh.vertices[face[i]], mesh.vertices[face[i + 1]]
            total += (p0[0] * (p1[1] * p2[2] - p1[2] * p2[1])
                      - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0])
                      + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])) / 6
    return total


def test_subdivided_box_is_closed_outward_and_fine():
    m = g.subdivided_box("b", (0, 1, 0), (4, 2, 1), 0.5, "concrete_mid")
    assert _closed(m)
    assert _signed_volume(m) == pytest.approx(8.0, rel=1e-6)
    for face in m.faces:
        pts = [m.vertices[i] for i in face]
        for a, b in zip(pts, (*pts[1:], pts[0])):
            assert math.dist(a, b) <= 0.5 + 1e-9


def test_wall_with_openings_recesses_not_holes():
    m = g.wall_with_openings("w", 6.0, 3.0, 0.4, [(-1.0, 1.0, 1.0, 2.2)], 0.25, 1.0, "concrete_mid")
    assert _closed(m)
    lo, hi = g.bounds([m])
    assert lo == pytest.approx((-3.0, 0.0, -0.2))
    assert hi == pytest.approx((3.0, 3.0, 0.2))
    recessed = [v for v in m.vertices if abs(v[2] - (0.2 - 0.25)) < 1e-9]
    assert recessed, "opening back face must sit recess metres behind the front"
    assert _signed_volume(m) == pytest.approx(6 * 3 * 0.4 - 2.0 * 1.2 * 0.25, rel=1e-6)


def test_wall_openings_validated():
    with pytest.raises(ValueError):
        g.wall_with_openings("w", 2.0, 2.0, 0.3, [(-1.5, 0.5, 0.5, 1.0)], 0.1, 1.0, "m")
    with pytest.raises(ValueError):
        g.wall_with_openings("w", 2.0, 2.0, 0.3, [(-0.5, 0.5, 0.5, 1.0)], 0.3, 1.0, "m")


def test_catenary_sags_and_hits_endpoints():
    pts = g.catenary((0, 5, 0), (10, 5, 0), 1.5, 16)
    assert pts[0] == pytest.approx((0, 5, 0)) and pts[-1] == pytest.approx((10, 5, 0))
    assert min(p[1] for p in pts) == pytest.approx(3.5, abs=1e-6)
    assert len(pts) == 17


def test_tube_is_closed():
    m = g.tube("t", g.catenary((0, 5, 0), (4, 6, 1), 0.6, 8), 0.03, 6, "cable")
    assert _closed(m)


def test_rotate_y_quarter_turn():
    assert g.rotate_y((1.0, 0.0, 0.0), math.pi / 2) == pytest.approx((0.0, 0.0, -1.0))


def test_rotate_xyz_axes():
    assert g.rotate_xyz((1.0, 0.0, 0.0), 0.0, 0.0, math.pi / 2) == pytest.approx((0.0, 1.0, 0.0))
    assert g.rotate_xyz((0.0, 1.0, 0.0), math.pi / 2, 0.0, 0.0) == pytest.approx((0.0, 0.0, 1.0))
    assert g.rotate_xyz((1.0, 0.0, 0.0), 0.0, math.pi / 2, 0.0) == pytest.approx(g.rotate_y((1.0, 0.0, 0.0), math.pi / 2))


def test_open_wall_drops_back_and_ends():
    closed = g.wall_with_openings("w", 6.0, 3.0, 0.4, [(-1.0, 1.0, 1.0, 2.2)], 0.25, 1.0, "m")
    opened = g.wall_with_openings("w", 6.0, 3.0, 0.4, [(-1.0, 1.0, 1.0, 2.2)], 0.25, 1.0, "m", closed=False)
    assert len(opened.faces) < len(closed.faces)
    assert all(v[2] > -0.2 + 1e-9 for f in opened.faces for v in (opened.vertices[i] for i in f))


def test_merge_assembly_groups_materials_in_first_seen_order():
    a = g.Assembly("stall", "stall-01", "market", (5.0, 0.0, 5.0), [
        g.box("p1", (0, 0.5, 0), (1, 1, 1), "rust"),
        g.box("p2", (2, 0.5, 0), (1, 1, 1), "tarp_blue"),
        g.box("p3", (4, 0.5, 0), (1, 1, 1), "rust"),
    ])
    merged = g.merge_assembly(a)
    assert merged.name == "stall-01"
    assert merged.materials == ("rust", "tarp_blue")
    assert len(merged.faces) == 18 and len(merged.face_materials) == 18
    assert merged.face_materials[:6] == (0,) * 6 and merged.face_materials[6:12] == (1,) * 6
    assert len(merged.vertices) == 24
    assert g.bounds([g.mesh("x", merged.vertices, merged.faces, "m")])[0] == pytest.approx((-0.5, 0.0, -0.5))
```

- [ ] **Step 2: 失敗を確認**

Run: `uv run pytest tests/slum02/test_geometry.py -q`
Expected: FAIL（`ModuleNotFoundError: modeling.slum02.geometry`）

- [ ] **Step 3: 実装**

`modeling/slum02/geometry.py` を作成する。`MeshData` / `mesh` / `box` / `beveled_box` / `cylinder` / `prism` / `pipe` は `/workspaces/reso-world/akichi/modeling/akichi/geometry.py` から**そのままコピー**し、モジュール docstring を slum02 用に変える。そのうえで以下を追記する:

```python
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field


def rotate_y(point: Sequence[float], radians: float) -> Vec3:
    c, s = math.cos(radians), math.sin(radians)
    x, y, z = point
    return (x * c + z * s, y, -x * s + z * c)


def transformed(m: MeshData, radians: float, offset: Sequence[float], name: str | None = None) -> MeshData:
    ox, oy, oz = offset
    verts = tuple((p[0] + ox, p[1] + oy, p[2] + oz) for p in (rotate_y(v, radians) for v in m.vertices))
    return MeshData(name or m.name, verts, m.faces, m.material)


def rotate_xyz(point: Sequence[float], rx: float, ry: float, rz: float) -> Vec3:
    x, y, z = point
    c, s = math.cos(rx), math.sin(rx)
    y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(ry), math.sin(ry)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(rz), math.sin(rz)
    x, y = x * c - y * s, x * s + y * c
    return (x, y, z)


def transformed_xyz(m: MeshData, rx: float, ry: float, rz: float, offset: Sequence[float], name: str | None = None) -> MeshData:
    verts = tuple(tuple(p[i] + offset[i] for i in range(3)) for p in (rotate_xyz(v, rx, ry, rz) for v in m.vertices))
    return MeshData(name or m.name, verts, m.faces, m.material)  # type: ignore[arg-type]


def bounds(meshes: Iterable[MeshData]) -> tuple[Vec3, Vec3]:
    pts = [v for m in meshes for v in m.vertices]
    if not pts:
        raise ValueError("bounds of nothing")
    return (tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3)))  # type: ignore[return-value]


def triangle_count(m: MeshData) -> int:
    return sum(len(f) - 2 for f in m.faces)


def _splits(lo: float, hi: float, max_edge: float, cuts: Iterable[float] = ()) -> list[float]:
    """Sorted breakpoints from lo to hi including forced cuts, no span above max_edge."""
    points = sorted({lo, hi, *(c for c in cuts if lo < c < hi)})
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        n = max(1, math.ceil((b - a) / max_edge - 1e-9))
        out.extend(a + (b - a) * k / n for k in range(1, n + 1))
    return out


class GridBuilder:
    """Vertex-interning polygon builder shared by the subdivided primitives."""

    def __init__(self) -> None:
        self.vertices: list[Vec3] = []
        self.faces: list[Face] = []
        self._index: dict[tuple[float, float, float], int] = {}

    def v(self, p: Sequence[float]) -> int:
        key = (round(p[0], 9), round(p[1], 9), round(p[2], 9))
        if key not in self._index:
            self._index[key] = len(self.vertices)
            self.vertices.append(key)
        return self._index[key]

    def quad(self, a, b, c, d) -> None:
        self.faces.append((self.v(a), self.v(b), self.v(c), self.v(d)))

    def grid(self, origin: Vec3, u: Vec3, w: Vec3, us: list[float], ws: list[float], skip=lambda i, j: False) -> None:
        """Quads over origin + u*us[i] + w*ws[j]; winding u x w is the face normal."""
        def at(a: float, b: float) -> Vec3:
            return tuple(origin[k] + u[k] * a + w[k] * b for k in range(3))  # type: ignore[return-value]
        for i in range(len(us) - 1):
            for j in range(len(ws) - 1):
                if not skip(i, j):
                    self.quad(at(us[i], ws[j]), at(us[i + 1], ws[j]), at(us[i + 1], ws[j + 1]), at(us[i], ws[j + 1]))

    def build(self, name: str, material: str) -> MeshData:
        return mesh(name, self.vertices, self.faces, material)


def subdivided_box(name: str, center: Sequence[float], size: Sequence[float], max_edge: float, material: str) -> MeshData:
    cx, cy, cz = center
    sx, sy, sz = size
    if min(sx, sy, sz) <= 0 or max_edge <= 0:
        raise ValueError("subdivided box needs positive size and max_edge")
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    xs, ys, zs = (_splits(-h, h, max_edge) for h in (hx, hy, hz))
    b = GridBuilder()
    # +X / -X
    b.grid((cx + hx, cy, cz), (0, 1, 0), (0, 0, 1), ys, zs)
    b.grid((cx - hx, cy, cz), (0, 0, 1), (0, 1, 0), zs, ys)
    # +Y / -Y
    b.grid((cx, cy + hy, cz), (0, 0, 1), (1, 0, 0), zs, xs)
    b.grid((cx, cy - hy, cz), (1, 0, 0), (0, 0, 1), xs, zs)
    # +Z / -Z
    b.grid((cx, cy, cz + hz), (1, 0, 0), (0, 1, 0), xs, ys)
    b.grid((cx, cy, cz - hz), (0, 1, 0), (1, 0, 0), ys, xs)
    return b.build(name, material)


def wall_with_openings(name: str, width: float, height: float, thickness: float,
                       openings: Sequence[Sequence[float]], recess: float, max_edge: float, material: str,
                       closed: bool = True) -> MeshData:
    hw, ht = width / 2, thickness / 2
    if width <= 0 or height <= 0 or thickness <= 0 or max_edge <= 0:
        raise ValueError("wall needs positive dimensions")
    if not 0 < recess < thickness:
        raise ValueError("recess must be positive and thinner than the wall")
    rects = []
    for x0, y0, x1, y1 in openings:
        if not (-hw < x0 < x1 < hw and 0 < y0 < y1 < height):
            raise ValueError(f"opening {(x0, y0, x1, y1)} must lie strictly inside the wall")
        rects.append((x0, y0, x1, y1))
    xs = _splits(-hw, hw, max_edge, [c for r in rects for c in (r[0], r[2])])
    ys = _splits(0.0, height, max_edge, [c for r in rects for c in (r[1], r[3])])

    def inside(i: int, j: int) -> bool:
        mx, my = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
        return any(r[0] < mx < r[2] and r[1] < my < r[3] for r in rects)

    b = GridBuilder()
    b.grid((0, 0, ht), (1, 0, 0), (0, 1, 0), xs, ys, skip=inside)            # front (+Z) minus openings
    if closed:
        b.grid((0, 0, -ht), (0, 1, 0), (1, 0, 0), ys, xs)                      # back
        zs = [-ht, ht]
        b.grid((hw, 0, 0), (0, 1, 0), (0, 0, 1), ys, zs)                       # +X end
        b.grid((-hw, 0, 0), (0, 0, 1), (0, 1, 0), zs, ys)                      # -X end
        b.grid((0, height, 0), (0, 0, 1), (1, 0, 0), zs, xs)                   # top
        b.grid((0, 0, 0), (1, 0, 0), (0, 0, 1), xs, zs)                        # bottom
    back = ht - recess
    for x0, y0, x1, y1 in rects:
        rx = [x for x in xs if x0 - 1e-9 <= x <= x1 + 1e-9]
        ry = [y for y in ys if y0 - 1e-9 <= y <= y1 + 1e-9]
        b.grid((0, 0, back), (1, 0, 0), (0, 1, 0), rx, ry)                     # recess back (+Z facing)
        dz = [back, ht]
        b.grid((0, y0, 0), (0, 0, 1), (1, 0, 0), dz, rx)                       # sill, faces +Y
        b.grid((0, y1, 0), (1, 0, 0), (0, 0, 1), rx, dz)                       # head, faces -Y
        b.grid((x0, 0, 0), (0, 1, 0), (0, 0, 1), ry, dz)                       # left jamb, faces +X
        b.grid((x1, 0, 0), (0, 0, 1), (0, 1, 0), dz, ry)                       # right jamb, faces -X
    return b.build(name, material)


def catenary(a: Sequence[float], b: Sequence[float], sag: float, segments: int) -> list[Vec3]:
    if segments < 2 or sag < 0:
        raise ValueError("catenary needs >=2 segments and non-negative sag")
    pts = []
    for k in range(segments + 1):
        t = k / segments
        drop = sag * 4 * t * (1 - t)
        pts.append(tuple(a[i] + (b[i] - a[i]) * t - (drop if i == 1 else 0.0) for i in range(3)))
    return pts  # type: ignore[return-value]


def tube(name: str, points: Sequence[Sequence[float]], radius: float, sides: int, material: str) -> MeshData:
    if len(points) < 2 or radius <= 0 or sides < 3:
        raise ValueError("tube needs >=2 points, positive radius and >=3 sides")
    verts: list[Vec3] = []
    n = len(points)
    for k, p in enumerate(points):
        prev_p, next_p = points[max(k - 1, 0)], points[min(k + 1, n - 1)]
        d = [next_p[i] - prev_p[i] for i in range(3)]
        length = math.sqrt(sum(x * x for x in d)) or 1.0
        d = [x / length for x in d]
        ref = (0.0, 1.0, 0.0) if abs(d[1]) < 0.9 else (1.0, 0.0, 0.0)
        s = [d[1] * ref[2] - d[2] * ref[1], d[2] * ref[0] - d[0] * ref[2], d[0] * ref[1] - d[1] * ref[0]]
        sl = math.sqrt(sum(x * x for x in s))
        s = [x / sl for x in s]
        o = [d[1] * s[2] - d[2] * s[1], d[2] * s[0] - d[0] * s[2], d[0] * s[1] - d[1] * s[0]]
        for j in range(sides):
            ang = math.tau * j / sides
            verts.append(tuple(p[i] + radius * (s[i] * math.cos(ang) + o[i] * math.sin(ang)) for i in range(3)))  # type: ignore[arg-type]
    faces: list[Face] = []
    for k in range(n - 1):
        for j in range(sides):
            a, b2 = k * sides + j, k * sides + (j + 1) % sides
            faces.append((a, b2, b2 + sides, a + sides))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(range((n - 1) * sides, n * sides)))
    return mesh(name, verts, faces, material)


@dataclass
class Assembly:
    kind: str
    name: str
    sector: str
    origin: Vec3
    parts: list[MeshData]
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MergedMesh:
    name: str
    vertices: tuple[Vec3, ...]
    faces: tuple[Face, ...]
    face_materials: tuple[int, ...]
    materials: tuple[str, ...]


def merge_assembly(assembly: Assembly) -> MergedMesh:
    materials: list[str] = []
    verts: list[Vec3] = []
    faces: list[Face] = []
    face_mats: list[int] = []
    for part in assembly.parts:
        if part.material not in materials:
            materials.append(part.material)
        slot = materials.index(part.material)
        offset = len(verts)
        verts.extend(part.vertices)
        for f in part.faces:
            faces.append(tuple(offset + i for i in f))
            face_mats.append(slot)
    order = sorted(range(len(faces)), key=lambda k: face_mats[k])  # stable: groups faces by material
    return MergedMesh(assembly.name, tuple(verts), tuple(faces[k] for k in order),
                      tuple(face_mats[k] for k in order), tuple(materials))
```

注意: `tube` の側面ワインディングが内向きになる場合（`_closed` は通るが向きが逆）は Task 4 の Blender 側で `recalc_face_normals` を行うので、ここではトポロジの閉性のみ保証する。`subdivided_box` / `wall_with_openings` は符号付き体積テストで外向きを保証する。

- [ ] **Step 4: テスト実行**

Run: `uv run pytest tests/slum02/test_geometry.py -q`
Expected: 10 passed。`_signed_volume` が負になる面があれば、該当 `grid` 呼び出しの u/w を入れ替えて修正する。

- [ ] **Step 5: コミット**

```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/geometry.py slum02/tests/slum02/test_geometry.py
git commit -m "feat(slum02): add geometry primitives, walls with recesses and assembly merge

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: マテリアル定義と頂点カラーの汚れマスク

**Files:**
- Create: `slum02/modeling/slum02/materials.py`, `slum02/modeling/slum02/vcolor.py`
- Test: `slum02/tests/slum02/test_materials.py`, `slum02/tests/slum02/test_vcolor.py`

**Interfaces:**
- Consumes: `geometry.MergedMesh`
- Produces:
  - `materials.MaterialSpec(frozen dataclass)`: `base_color: tuple[float,float,float]`（Blender linear）, `metallic: float`, `roughness: float`, `kind: Literal["vc","neon","holo"]`, `family: str`, `emission: tuple|None = None`, `emission_strength: float = 0.0`, `noise: str|None = None`, `texture_scale: tuple[float,float] = (1.0, 1.0)`
  - `materials.MATERIALS: dict[str, MaterialSpec]`（キーは下表）
  - `materials.NoiseSpec(frozen)`: `seed: int, size: int, low: float, high: float, bias: float = 0.0, gain: float = 0.0`
  - `materials.NOISES: dict[str, NoiseSpec]`
  - `materials.BLENDER_PREFIX = "Slum02_"`
  - `materials.make_blender_materials() -> dict[str, bpy.types.Material]`（bpy 必須）
  - `vcolor.WearProfile(frozen)`: `variation, ground_grime, streaks, edge_wear, rust` (all float 0..1), `edge_color: tuple[float,float,float]`
  - `vcolor.WEAR: dict[str, WearProfile]`（family → profile）
  - `vcolor.value_noise3(x, y, z, seed) -> float`（0..1、格子ハッシュ三線形補間）
  - `vcolor.vertex_colors(merged, origin, seed, sprays=()) -> list[tuple[float,float,float,float]]` — 頂点ごとの RGBA（線形、乗算色、A=1）。`origin` はワールド座標のオフセット（ノイズをワールド基準にするため）。`sprays` は `Spray(center: Vec3, radius: float, color: RGB, strength: float)` の列（ワールド座標）

**マテリアル一覧（キー: base_color, metallic, roughness, kind, family, noise, texture_scale / emission）**

| key | base_color | met | rough | kind | family | noise | scale |
|---|---|---|---|---|---|---|---|
| concrete_raw | (0.34,0.33,0.31) | 0 | 0.92 | vc | concrete | concrete | (0.35,0.35) |
| concrete_dark | (0.20,0.195,0.19) | 0 | 0.94 | vc | concrete | concrete | (0.35,0.35) |
| concrete_stained | (0.27,0.25,0.21) | 0 | 0.95 | vc | concrete | concrete | (0.3,0.3) |
| concrete_patch | (0.42,0.40,0.36) | 0 | 0.86 | vc | concrete | concrete | (0.5,0.5) |
| factory_floor | (0.30,0.29,0.27) | 0 | 0.80 | vc | concrete | concrete | (0.25,0.25) |
| asphalt | (0.07,0.072,0.075) | 0 | 0.93 | vc | asphalt | asphalt | (0.4,0.4) |
| asphalt_wet | (0.035,0.042,0.05) | 0.1 | 0.12 | vc | wet | None | — |
| mud | (0.13,0.10,0.07) | 0 | 0.97 | vc | ground | asphalt | (0.5,0.5) |
| rust | (0.36,0.11,0.035) | 0.55 | 0.80 | vc | rust | metal | (0.8,0.8) |
| rust_dark | (0.19,0.065,0.03) | 0.5 | 0.85 | vc | rust | metal | (0.8,0.8) |
| steel_bare | (0.40,0.41,0.41) | 0.9 | 0.42 | vc | metal | metal | (1.0,1.0) |
| steel_dark | (0.09,0.095,0.10) | 0.75 | 0.50 | vc | metal | metal | (1.0,1.0) |
| paint_yellow_faded | (0.46,0.33,0.07) | 0.3 | 0.62 | vc | painted | metal | (0.8,0.8) |
| paint_teal_faded | (0.06,0.22,0.22) | 0.3 | 0.62 | vc | painted | metal | (0.8,0.8) |
| corrugated | (0.32,0.31,0.29) | 0.65 | 0.58 | vc | metal | metal | (0.8,0.8) |
| corrugated_rust | (0.42,0.21,0.10) | 0.55 | 0.74 | vc | rust | metal | (0.8,0.8) |
| plywood | (0.40,0.28,0.16) | 0 | 0.86 | vc | wood | wood | (1.2,0.4) |
| pallet_wood | (0.33,0.25,0.16) | 0 | 0.90 | vc | wood | wood | (1.2,0.4) |
| tarp_blue | (0.05,0.13,0.33) | 0 | 0.66 | vc | fabric | fabric | (1.5,1.5) |
| tarp_orange | (0.50,0.17,0.04) | 0 | 0.70 | vc | fabric | fabric | (1.5,1.5) |
| tarp_green | (0.07,0.20,0.09) | 0 | 0.70 | vc | fabric | fabric | (1.5,1.5) |
| cloth_red | (0.35,0.02,0.04) | 0 | 0.75 | vc | fabric | fabric | (2.0,2.0) |
| plastic_crate | (0.08,0.20,0.35) | 0 | 0.50 | vc | plastic | fabric | (2.0,2.0) |
| rubber | (0.025,0.025,0.028) | 0 | 0.85 | vc | plastic | None | — |
| glass_dark | (0.03,0.045,0.05) | 0.2 | 0.08 | vc | glass | None | — |
| electronics | (0.05,0.12,0.06) | 0.4 | 0.45 | vc | metal | metal | (3.0,3.0) |
| spray_red | (0.55,0.012,0.012) | 0 | 0.62 | vc | paint | None | — |
| spray_black | (0.012,0.012,0.014) | 0 | 0.70 | vc | paint | None | — |
| backdrop_mass | (0.035,0.037,0.045) | 0.1 | 0.80 | vc | backdrop | None | — |
| backdrop_ground | (0.03,0.03,0.033) | 0 | 0.95 | vc | backdrop | None | — |
| neon_magenta | emission (1.0,0.05,0.6) ×6 | 0 | 0.35 | neon | neon | None | — |
| neon_cyan | emission (0.05,0.9,1.0) ×6 | 0 | 0.35 | neon | neon | None | — |
| neon_lime | emission (0.55,1.0,0.05) ×5 | 0 | 0.35 | neon | neon | None | — |
| neon_orange | emission (1.0,0.35,0.02) ×5 | 0 | 0.35 | neon | neon | None | — |
| neon_pink | emission (1.0,0.25,0.55) ×6 | 0 | 0.35 | neon | neon | None | — |
| neon_red | emission (1.0,0.03,0.03) ×6 | 0 | 0.35 | neon | neon | None | — |
| warm_bulb | emission (1.0,0.55,0.2) ×4 | 0 | 0.40 | neon | neon | None | — |
| window_lit | emission (1.0,0.7,0.35) ×2.5 | 0 | 0.40 | neon | neon | None | — |
| holo_magenta | emission (1.0,0.08,0.7) ×1 | 0 | 0.1 | holo | holo | holo | (1,4) |
| holo_cyan | emission (0.05,0.85,1.0) ×1 | 0 | 0.1 | holo | holo | holo | (1,4) |
| holo_lime | emission (0.5,1.0,0.1) ×1 | 0 | 0.1 | holo | holo | holo | (1,4) |
| holo_orange | emission (1.0,0.45,0.05) ×1 | 0 | 0.1 | holo | holo | holo | (1,4) |
| holo_cyan_scroll | emission (0.05,0.85,1.0) ×1 | 0 | 0.1 | holo | holo | holo | (1,4) |
| holo_magenta_scroll | emission (1.0,0.08,0.7) ×1 | 0 | 0.1 | holo | holo | holo | (1,4) |

neon / holo の base_color は emission × 0.2（暗色ベース）。

**NOISES**: `concrete`(seed 11, size 256, low 0.72, high 1.0), `asphalt`(12, 256, 0.62, 1.0), `metal`(13, 256, 0.70, 1.0), `wood`(14, 128, 0.75, 1.0), `fabric`(15, 128, 0.82, 1.0), `holo`(16, 128, 0.25, 1.0)。

**WEAR（family → variation, ground_grime, streaks, edge_wear, rust, edge_color）**:
concrete(0.18,0.45,0.55,0.30,0.0,(1.12,1.10,1.05)), asphalt(0.25,0,0,0,0,(1,1,1)), wet(0.05,0,0,0,0,(1,1,1)), ground(0.3,0,0,0,0,(1,1,1)), rust(0.25,0.3,0.2,0.2,0.0,(0.8,0.55,0.4)), metal(0.12,0.35,0.35,0.35,0.45,(1.25,1.2,1.15)), painted(0.15,0.35,0.3,0.55,0.35,(0.75,0.72,0.70)), wood(0.2,0.4,0.25,0.2,0,(0.8,0.75,0.7)), fabric(0.15,0.3,0.15,0,0,(1,1,1)), plastic(0.1,0.3,0.1,0.2,0,(1.1,1.1,1.1)), glass(0.05,0.2,0.4,0,0,(1,1,1)), paint(0.12,0,0.2,0,0,(1,1,1)), backdrop(0.35,0,0,0,0,(1,1,1)), neon(0,0,0,0,0,(1,1,1)), holo(0,0,0,0,0,(1,1,1))

**vertex_colors の計算（頂点 v、ワールド位置 P = v + origin、family の profile を使用。複数素材の頂点は最初に参照した面の素材を採用）**:
1. `c = 1 + variation * (value_noise3(P*0.35, seed) - 0.5) * 2 * 0.5` → RGB 同値（低周波のムラ）
2. 足元の汚れ: `g = ground_grime * clamp(1 - P.y / 1.4, 0, 1)` → `c *= (1 - 0.55 g)`
3. 雨だれ: 頂点法線が水平（|n.y| < 0.35）のとき、`col = value_noise3(P.x*2.3 + P.z*2.3, 0, 0, seed+7)`、`s = streaks * smoothstep(0.55, 0.8, col) * clamp((top - P.y) / 6, 0, 1)` ここで `top` は merged メッシュの最大 y + origin.y。`c *= (1 - 0.45 s)`（縦の暗い筋）
4. エッジ摩耗: `sharp = 1 - min(dot(n_i, n_j))` を頂点に接する面法線の全ペアで計算し clamp 0..1、`e = edge_wear * smoothstep(0.3, 1.0, sharp) * value_noise3(P*1.7, seed+3)`。`c_rgb = lerp(c_rgb, c_rgb * edge_color, e)`
5. 錆: `r = rust * smoothstep(0.55, 0.85, value_noise3(P*0.9, seed+5)) * (0.5 + 0.5*g_raw)` ここで `g_raw = clamp(1 - P.y/2.5,0,1)`。`c_rgb = lerp(c_rgb, c_rgb * (1.1, 0.55, 0.3), r)`
6. スプレー: 各 `Spray` について `d = |P - center| / radius`、`k = strength * (1 - smoothstep(0.4, 1.0, d))`、`c_rgb = lerp(c_rgb, c_rgb * color, k)`
7. 最終 clamp: 各成分 [0.05, 1.3]、A=1.0

`smoothstep(a,b,x) = t*t*(3-2t), t=clamp((x-a)/(b-a),0,1)`。

- [ ] **Step 1: 失敗するテスト**

`tests/slum02/test_materials.py`:
```python
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
```

`tests/slum02/test_vcolor.py`:
```python
import pytest

from modeling.slum02 import geometry as g
from modeling.slum02 import vcolor


def _merged(part):
    return g.merge_assembly(g.Assembly("t", "t", "s", (0.0, 0.0, 0.0), [part]))


def test_noise_deterministic_and_bounded():
    a = [vcolor.value_noise3(x * 0.37, 1.1, -x * 0.21, 5) for x in range(200)]
    b = [vcolor.value_noise3(x * 0.37, 1.1, -x * 0.21, 5) for x in range(200)]
    assert a == b
    assert all(0.0 <= v <= 1.0 for v in a)
    assert max(a) - min(a) > 0.3


def test_ground_grime_darkens_bottom():
    wall = _merged(g.subdivided_box("w", (0, 3, 0), (4, 6, 0.4), 0.5, "concrete_raw"))
    cols = vcolor.vertex_colors(wall, (0.0, 0.0, 0.0), 7)
    low = [c[0] for v, c in zip(wall.vertices, cols) if v[1] < 0.3]
    high = [c[0] for v, c in zip(wall.vertices, cols) if 2.5 < v[1] < 3.5]
    assert sum(low) / len(low) < sum(high) / len(high) * 0.85


def test_rust_only_on_metal_family():
    concrete = _merged(g.subdivided_box("c", (0, 1, 0), (3, 2, 3), 0.4, "concrete_raw"))
    cols = vcolor.vertex_colors(concrete, (0.0, 0.0, 0.0), 7)
    # concrete has rust = 0, so red/blue ratio stays near neutral
    assert all(c[2] > 0 and c[0] / c[2] < 1.25 for c in cols)
    metal = _merged(g.subdivided_box("m", (0, 1, 0), (3, 2, 3), 0.4, "steel_bare"))
    mcols = vcolor.vertex_colors(metal, (0.0, 0.0, 0.0), 7)
    assert max(c[0] / c[2] for c in mcols) > 1.2


def test_spray_tints_only_near_center():
    wall = _merged(g.subdivided_box("w", (0, 5, 0), (10, 10, 0.5), 0.5, "concrete_raw"))
    spray = vcolor.Spray((0.0, 5.0, 0.25), 2.0, (1.0, 0.2, 0.2), 0.8)
    base = vcolor.vertex_colors(wall, (0.0, 0.0, 0.0), 7)
    cols = vcolor.vertex_colors(wall, (0.0, 0.0, 0.0), 7, sprays=[spray])
    for v, c0, c1 in zip(wall.vertices, base, cols):
        dist = ((v[0]) ** 2 + (v[1] - 5) ** 2 + (v[2] - 0.25) ** 2) ** 0.5
        if dist > 2.0:
            assert c1 == pytest.approx(c0)
        if dist < 0.5:
            assert c1[1] < c0[1] * 0.6


def test_colors_clamped_rgba():
    part = g.subdivided_box("p", (0, 1, 0), (2, 2, 2), 0.5, "paint_yellow_faded")
    cols = vcolor.vertex_colors(_merged(part), (3.0, 0.0, -2.0), 1)
    assert all(len(c) == 4 and c[3] == 1.0 and all(0.05 <= x <= 1.3 for x in c[:3]) for c in cols)
```

- [ ] **Step 2: 失敗確認**

Run: `uv run pytest tests/slum02/test_materials.py tests/slum02/test_vcolor.py -q`
Expected: FAIL（モジュールなし）

- [ ] **Step 3: materials.py 実装**

```python
"""Shared material palette for slum02 (Blender-linear colours, see spec).

Blender carries only constant Principled values; runtime detail comes from
vertex colours (vcolor.py) and engine NoiseTextures (postprocess.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

BLENDER_PREFIX = "Slum02_"


@dataclass(frozen=True)
class MaterialSpec:
    base_color: tuple[float, float, float]
    metallic: float
    roughness: float
    kind: Literal["vc", "neon", "holo"]
    family: str
    emission: tuple[float, float, float] | None = None
    emission_strength: float = 0.0
    noise: str | None = None
    texture_scale: tuple[float, float] = (1.0, 1.0)


@dataclass(frozen=True)
class NoiseSpec:
    seed: int
    size: int
    low: float
    high: float
    bias: float = 0.0
    gain: float = 0.0


def _vc(rgb, met, rough, family, noise=None, scale=(1.0, 1.0)) -> MaterialSpec:
    return MaterialSpec(rgb, met, rough, "vc", family, noise=noise, texture_scale=scale)


def _glow(kind, rgb, strength, rough, noise=None, scale=(1.0, 1.0)) -> MaterialSpec:
    base = tuple(round(c * 0.2, 4) for c in rgb)
    return MaterialSpec(base, 0.0, rough, kind, kind, emission=rgb, emission_strength=strength, noise=noise, texture_scale=scale)  # type: ignore[arg-type]
```
続けて上表どおり `MATERIALS: dict[str, MaterialSpec] = {...}` を全行定義する（`_vc(...)` / `_glow("neon", ...)` / `_glow("holo", ..., noise="holo", scale=(1.0, 4.0))`）。`NOISES` も上記どおり定義する。

`make_blender_materials()` は akichi の同名関数を移植し、`settings` 辞書の代わりに `MaterialSpec` の属性を読み、名前を `f"{BLENDER_PREFIX}{name}"` にする。Principled BSDF の入力は Base Color / Metallic / Roughness / Emission Color / Emission Strength のみ（ノードは追加しない。exporter が拒否するため）。`material.use_fake_user = True`。

- [ ] **Step 4: vcolor.py 実装**

```python
"""Pure-Python vertex-colour wear masks (multiplicative RGBA, Blender linear)."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from modeling.slum02.geometry import MergedMesh, Vec3
from modeling.slum02.materials import MATERIALS


@dataclass(frozen=True)
class WearProfile:
    variation: float
    ground_grime: float
    streaks: float
    edge_wear: float
    rust: float
    edge_color: tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass(frozen=True)
class Spray:
    center: Vec3
    radius: float
    color: tuple[float, float, float]
    strength: float


WEAR: dict[str, WearProfile] = {
    "concrete": WearProfile(0.18, 0.45, 0.55, 0.30, 0.0, (1.12, 1.10, 1.05)),
    # ... 上表の全 family を同じ形式で定義
}


def _hash(ix: int, iy: int, iz: int, seed: int) -> float:
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 144665) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def value_noise3(x: float, y: float, z: float, seed: int) -> float:
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    sx, sy, sz = (t * t * (3 - 2 * t) for t in (fx, fy, fz))
    def lerp(a, b, t): return a + (b - a) * t
    c = [[[_hash(ix + dx, iy + dy, iz + dz, seed) for dz in (0, 1)] for dy in (0, 1)] for dx in (0, 1)]
    x00 = lerp(c[0][0][0], c[1][0][0], sx); x10 = lerp(c[0][1][0], c[1][1][0], sx)
    x01 = lerp(c[0][0][1], c[1][0][1], sx); x11 = lerp(c[0][1][1], c[1][1][1], sx)
    return lerp(lerp(x00, x10, sy), lerp(x01, x11, sy), sz)


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))


def _smooth(a, b, x):
    t = _clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def _face_normal(pts: Sequence[Vec3]) -> Vec3:
    nx = ny = nz = 0.0
    for a, b in zip(pts, (*pts[1:], pts[0])):  # Newell
        nx += (a[1] - b[1]) * (a[2] + b[2]); ny += (a[2] - b[2]) * (a[0] + b[0]); nz += (a[0] - b[0]) * (a[1] + b[1])
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / length, ny / length, nz / length)


def vertex_colors(merged: MergedMesh, origin: Sequence[float], seed: int,
                  sprays: Sequence[Spray] = ()) -> list[tuple[float, float, float, float]]:
    n = len(merged.vertices)
    normals: list[list[Vec3]] = [[] for _ in range(n)]
    family: list[str | None] = [None] * n
    for face, mat in zip(merged.faces, merged.face_materials):
        fn = _face_normal([merged.vertices[i] for i in face])
        fam = MATERIALS[merged.materials[mat]].family
        for i in face:
            normals[i].append(fn)
            if family[i] is None:
                family[i] = fam
    top = max(v[1] for v in merged.vertices) + origin[1]
    out = []
    for idx, v in enumerate(merged.vertices):
        prof = WEAR[family[idx] or "concrete"]
        P = (v[0] + origin[0], v[1] + origin[1], v[2] + origin[2])
        base = 1 + prof.variation * (value_noise3(P[0] * 0.35, P[1] * 0.35, P[2] * 0.35, seed) - 0.5)
        rgb = [base, base, base]
        g_raw = _clamp(1 - P[1] / 1.4)
        rgb = [c * (1 - 0.55 * prof.ground_grime * g_raw) for c in rgb]
        ns = normals[idx] or [(0.0, 1.0, 0.0)]
        avg_ny = sum(n_[1] for n_ in ns) / len(ns)
        if abs(avg_ny) < 0.35 and prof.streaks > 0:
            col = value_noise3(P[0] * 2.3 + P[2] * 2.3, 0.0, 0.0, seed + 7)
            s = prof.streaks * _smooth(0.55, 0.8, col) * _clamp((top - P[1]) / 6)
            rgb = [c * (1 - 0.45 * s) for c in rgb]
        if prof.edge_wear > 0 and len(ns) > 1:
            min_dot = min(sum(a[k] * b[k] for k in range(3)) for i, a in enumerate(ns) for b in ns[i + 1:])
            e = prof.edge_wear * _smooth(0.3, 1.0, _clamp(1 - min_dot)) * value_noise3(P[0] * 1.7, P[1] * 1.7, P[2] * 1.7, seed + 3)
            rgb = [c + (c * ec - c) * e for c, ec in zip(rgb, prof.edge_color)]
        if prof.rust > 0:
            r = prof.rust * _smooth(0.55, 0.85, value_noise3(P[0] * 0.9, P[1] * 0.9, P[2] * 0.9, seed + 5)) * (0.5 + 0.5 * _clamp(1 - P[1] / 2.5))
            rgb = [c + (c * t - c) * r for c, t in zip(rgb, (1.1, 0.55, 0.3))]
        for sp in sprays:
            d = math.dist(P, sp.center) / sp.radius
            k = sp.strength * (1 - _smooth(0.4, 1.0, d))
            if k > 0:
                rgb = [c + (c * t - c) * k for c, t in zip(rgb, sp.color)]
        out.append((*(round(_clamp(c, 0.05, 1.3), 6) for c in rgb), 1.0))
    return out  # type: ignore[return-value]
```
注: 手順 6 のスプレー判定は、影響外（d ≥ 1）の頂点で色を変えないこと（テストで保証）。`_smooth(0.4,1.0,d)` は d ≥ 1 で 1 になるので k = 0 になる。

- [ ] **Step 5: テスト実行**

Run: `uv run pytest tests/slum02/test_materials.py tests/slum02/test_vcolor.py -q`
Expected: 9 passed

- [ ] **Step 6: コミット**

```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/materials.py slum02/modeling/slum02/vcolor.py slum02/tests/slum02/test_materials.py slum02/tests/slum02/test_vcolor.py
git commit -m "feat(slum02): add material palette, noise specs and vertex-colour wear masks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 決定論レイアウト・検証・視線遮断レイキャスト

**Files:**
- Create: `slum02/modeling/slum02/layout.py`
- Create: `slum02/content/slum02/layout.json`（生成物）
- Test: `slum02/tests/slum02/test_layout.py`

**Interfaces:**
- Consumes: `modeling.slum02.SEED`, `materials.MATERIALS`
- Produces:
  - `build_layout() -> dict` — キーと形式:
    - `seed: int`, `half: 40.0`, `plaza: {"min": [-10,-10], "max": [10,10]}`
    - `east_wall: {"center": [9.6, 0.0, 0.0], "size": [0.8, 10.0, 20.0]}`（x 9.2〜10.0、高さ 10、z -10〜10、広場側 = -X 面）
    - `streets: [{"id", "kind": "ring"|"outer"|"radial"|"lane", "min": [x,z], "max": [x,z]}]`
    - `towers: [{"id": "tower-NN", "sector": "towers-a"|"towers-b"|"towers-c", "role": "outer"|"inner", "center": [x,z], "footprint": [w,d], "height": h, "core_height": hc, "rotation": deg, "front": "+x"|"-x"|"+z"|"-z", "seed": int}]` — `footprint` はワールド軸（x 幅, z 奥行）で表す（外周は rotation ∈ {0,90,180,270}、footprint はワールド軸の値）
    - `stalls: [{"id": "stall-NN", "center": [x,z], "rotation": deg, "size": [w,d], "seed"}]`
    - `clubs: [{"id": "club-NN", "center": [x,z], "rotation": deg, "size": [w,d], "height": h, "neon": material, "seed"}]`
    - `shacks: [{"id": "shack-NN", "center": [x,z], "rotation": deg, "size": [w,d], "seed"}]`
    - `ads: [{"id": "ad-NN", "kind": "wall"|"float"|"vertical", "position": [x,y,z], "rotation": deg, "size": [w,h], "material": holo_*, "anim": "none"|"scroll"|"spin", "text": str}]`
    - `signs: [{"id": "sign-NN", "position": [x,y,z], "rotation": deg, "text": str, "size": float, "color": [r,g,b,a]}]`
    - `cables: [{"id": "cable-NN", "a": [x,y,z], "b": [x,y,z], "sag": float}]`
    - `bridges: [{"id": "bridge-NN", "a": [x,z], "b": [x,z], "y": float, "width": float}]`
    - `lights: [{"id": "light-NN", "type": "Point"|"Spot", "position": [x,y,z], "rotation": [qx,qy,qz,qw], "color": [r,g,b,1], "intensity": f, "range": f, "spot_angle": f, "shadow": "None"|"Hard"|"Soft"}]`
    - `occluders: [{"id": f"occ-{source}", "source": id, "min": [x,y,z], "max": [x,y,z]}]`（id は必ず `occ-<元要素の id>`。例 `occ-tower-05`、`occ-bridge-02`、`occ-ad-07`。生成側の Assembly は `meta["occludes"]` に同じ id を入れる）
    - `backdrop: {"masses": [{"id", "center": [x,z], "footprint": [w,d], "height": h, "seed"}], "ground_radius": 220.0}`
    - `plaza_features: {"fire_barrel": [x,z], "car": [x,z,deg], "columns": [[x,z,tilt_deg,height]], "machines": [[x,z,deg,kind]], "pits": [[x0,z0,x1,z1]], "exits": [[x0,z0,x1,z1]]}`
  - `validate_layout(data) -> list[str]`（空なら OK）
  - `ray_hit_distance(origin, direction, box_min, box_max) -> float | None`（slab 法）
  - `sightline_failures(data, *, step_deg=5, max_elev=25, elev_step=5) -> list[dict]`
  - `write_layout(path) -> dict`、`python -m modeling.slum02.layout` で `content/slum02/layout.json` を書く

**配置の骨格（固定表、ばらつきは `random.Random(SEED)` で高さ・細部のみ）**

- 道路:
  - ring: N `x[-14,14] z[10,14]`、S `x[-14,14] z[-14,-10]`、E `x[10,14] z[-10,10]`、W `x[-14,-10] z[-10,10]`
  - outer: N `x[-32.5,32.5] z[29,32.5]`、S `z[-32.5,-29]`、E `x[29,32.5] z[-29,29]`、W `x[-32.5,-29] z[-29,29]`
  - radial（クランク付き）:
    - N: `x[-1.5,1.5] z[14,21]` → `x[-1.5,4.5] z[21,24]` → `x[1.5,4.5] z[24,29]`
    - S: `x[-1.5,1.5] z[-21,-14]` → `x[-4.5,1.5] z[-24,-21]` → `x[-4.5,-1.5] z[-29,-24]`
    - E: `z[-1.5,1.5] x[14,21]` → `z[-4.5,1.5] x[21,24]` → `z[-4.5,-1.5] x[24,29]`
    - W: `z[-1.5,1.5] x[-21,-14]` → `z[-1.5,4.5] x[-24,-21]` → `z[1.5,4.5] x[-29,-24]`
  - lane（屋台通り）: `x[-27,27] z[-19.5,-16.5]`
- 外周タワー 16 棟（role outer、帯 32.5〜40）: 四隅 `tower-01..04` = 8×8、中心 (±36, ±36)、高さ 34〜40。各辺 3 棟ずつ（`-32..32` の 64m を幅 `rng.uniform(19,24)` の 3 区間に正規化して分割し、隣と 1.5m 重ねる）。奥行 6.5、前面位置は棟ごとに交互に 32.5 / 33.5（奥の棟は外側へずらす）。高さ 24〜36（隅に近い棟ほど +4）。前面は中心向き（北辺 front="-z"、南辺 "+z"、東辺 "-x"、西辺 "+x"）。北辺・東辺と NE/NW 隅 → `towers-a`、南辺・西辺と SE/SW 隅 → `towers-b`
- 内側の廃ビル 6 棟（role inner、`towers-c`）: `tower-17` (-8.5, 22.5) 9×11 h14、`tower-18` (9.0, 19.5) 8×9 h18、`tower-19` (21.5, 21.5) 11×11 h20、`tower-20` (21.5, -22.5) 11×10 h16、`tower-21` (-21.5, -24.5) 10×8 h12、`tower-22` (-22.0, 21.0) 9×10 h15。rotation は `rng.uniform(-4, 4)`（内側は遮蔽体として数えない）
- 屋台 12 軒: lane の北側 6 軒（z 中心 -15.4、奥行 2.2、front "-z"）と南側 6 軒（z 中心 -20.6、front "+z"）。x 中心は `[-24,-19.5,-15,-10.5,6,10.5,15,19.5,24]` から radial S のクランク `x[-4.5,1.5]` と重ならない位置を北 6 / 南 6 選ぶ。幅 3.2〜3.8
- 風俗店 4 軒: `club-01` (17.6, 6.5) 6×7 h7 front "-x"、`club-02` (17.6, -8.0) 6×7 h8 front "-x"、`club-03` (26.0, 8.0) 5.5×7 h6 front "+x"、`club-04` (26.0, -10.5) 5.5×6 h7 front "+x"。neon は `neon_pink / neon_magenta / neon_red / neon_pink`
- 掘っ立て小屋 12 棟: 候補領域 W ブロック `x[-28.5,-14.5] z[-28,28]` と NW/SW 隅から、道路・タワー・他の小屋と 0.6m 以上離れる位置を棄却サンプリング（最大 400 試行、足りなければ AssertionError）。サイズ 2.6〜4.2 × 2.4〜3.6、rotation `rng.uniform(-12, 12)`
- 橋（渡り廊下）4 本: 外周タワー同士・外周と内側タワーの間、高さ 8〜14m、幅 1.4
- 広場: `fire_barrel` (-5.5, 4.0)、`car` (3.5, -5.5, 23°)、柱 5 本（うち 2 本傾斜 8〜25°、高さ 4〜9m）、機械 3 台（press / conveyor / tank）、ピット 2 箇所、出入口 2 箇所（西辺 z[-2,2]、南辺 x[3,7]：塀の切れ目）
- AR 広告 30 枚: wall 12（外周タワー内向き面 高さ 8〜26m、4〜8m 幅）、float 10（道路上空 4.5〜9m、1.6〜3m 幅、うち 4 枚 anim "spin"）、vertical 8（内側タワー・クラブ壁面の縦長 1.2×4〜6m、うち 6 枚 anim "scroll" で material `holo_*_scroll`）
- 看板テキスト 16: 屋台 6（「ジャンク」「中古義体」「基板買取」「修理 即日」「電池」「ケーブル量り売り」）、クラブ 4（「夜蝶」「ピンクの月」「個室あり」「CLUB 天國」）、広告 6（「電脳接続 今すぐ」「義体クリニック」「合成酒 NOVA」「ネオ東京不動産」「夢見る電脳」「24H 修理」）
- 電線 14 本: 外周/内側タワー壁面の点同士、クラブ・屋台の屋根の点へ（端点は必ず壁面または屋根上 0.05m 以内）
- 光源 25 灯（影あり 3 灯: fire barrel Soft、スプレー壁の投光器 Spot Hard、club-01 Hard）
- 遠景 masses 18 個: 半径 60〜180m に角度で並べ、footprint 18〜45m、高さ 80〜200m
- occluders: 外周タワーのコア AABB（`[cx-w/2, 0, cz-d/2]`〜`[cx+w/2, core_height, cz+d/2]`、core_height = height - 2）、橋（`y-0.6`〜`y+0.6`）、wall 広告のパネル

- [ ] **Step 1: 失敗するテスト**

`tests/slum02/test_layout.py`:
```python
import hashlib
import json
import math

from modeling.slum02 import layout as L


def _data():
    return L.build_layout()


def test_deterministic():
    a = json.dumps(_data(), sort_keys=True)
    b = json.dumps(_data(), sort_keys=True)
    assert hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()


def test_validate_clean():
    assert L.validate_layout(_data()) == []


def test_counts():
    d = _data()
    outer = [t for t in d["towers"] if t["role"] == "outer"]
    assert len(outer) == 16 and len([t for t in d["towers"] if t["role"] == "inner"]) == 6
    assert 10 <= len(d["stalls"]) <= 12
    assert 3 <= len(d["clubs"]) <= 4
    assert 10 <= len(d["shacks"]) <= 14
    assert 25 <= len(d["ads"]) <= 35
    assert 20 <= len(d["lights"]) <= 30
    assert sum(1 for l in d["lights"] if l["shadow"] != "None") <= 3
    assert sum(t["footprint"][0] * t["footprint"][1] * t["height"] for t in d["towers"]) > 0


def test_plaza_is_clear_and_wall_on_east_edge():
    d = _data()
    for group in ("towers", "stalls", "clubs", "shacks"):
        for item in d[group]:
            x, z = item["center"]
            assert not (abs(x) < 10 and abs(z) < 10), item["id"]
    w = d["east_wall"]
    assert w["center"][0] + w["size"][0] / 2 == 10.0 and w["size"][1] == 10.0 and w["size"][2] == 20.0


def test_everything_inside_bounds_except_backdrop():
    d = _data()
    for group in ("towers", "stalls", "clubs", "shacks"):
        for item in d[group]:
            x, z = item["center"]
            hw, hd = item["footprint" if group == "towers" else "size"][0] / 2, item["footprint" if group == "towers" else "size"][1] / 2
            assert -40 <= x - hw and x + hw <= 40 and -40 <= z - hd and z + hd <= 40, item["id"]
    for mass in d["backdrop"]["masses"]:
        assert math.hypot(*mass["center"]) >= 55


def test_radial_alleys_have_no_straight_exit():
    d = _data()
    radials = [s for s in d["streets"] if s["kind"] == "radial"]
    assert len(radials) == 12  # 4 alleys x 3 legs (dogleg)


def test_ray_hit_distance():
    assert L.ray_hit_distance((0, 0, 0), (1, 0, 0), (5, -1, -1), (6, 1, 1)) == 5
    assert L.ray_hit_distance((0, 0, 0), (-1, 0, 0), (5, -1, -1), (6, 1, 1)) is None
    assert L.ray_hit_distance((0, 5, 0), (1, 0, 0), (5, -1, -1), (6, 1, 1)) is None


def test_sightlines_from_plaza_are_closed():
    failures = L.sightline_failures(_data())
    assert failures == [], failures[:5]


def test_layout_json_matches_generator(tmp_path):
    out = tmp_path / "layout.json"
    L.write_layout(out)
    assert json.loads(out.read_text()) == json.loads(json.dumps(_data()))
```

- [ ] **Step 2: 失敗確認**

Run: `uv run pytest tests/slum02/test_layout.py -q`
Expected: FAIL（モジュールなし）

- [ ] **Step 3: 実装（骨格コード）**

```python
"""Deterministic slum02 layout (Resonite XZ plane, Y up, metres) + validation + sightlines."""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from modeling.slum02 import PROJECT_ROOT, SEED

HALF = 40.0
EYE = 1.6


def _street(id_: str, kind: str, x0, z0, x1, z1) -> dict[str, Any]:
    return {"id": id_, "kind": kind, "min": [x0, z0], "max": [x1, z1]}


def _streets() -> list[dict[str, Any]]:
    s = [
        _street("ring-n", "ring", -14, 10, 14, 14), _street("ring-s", "ring", -14, -14, 14, -10),
        _street("ring-e", "ring", 10, -10, 14, 10), _street("ring-w", "ring", -14, -10, -10, 10),
        _street("outer-n", "outer", -32.5, 29, 32.5, 32.5), _street("outer-s", "outer", -32.5, -32.5, 32.5, -29),
        _street("outer-e", "outer", 29, -29, 32.5, 29), _street("outer-w", "outer", -32.5, -29, -29, 29),
        _street("lane", "lane", -27, -19.5, 27, -16.5),
    ]
    legs = {
        "n": [(-1.5, 14, 1.5, 21), (-1.5, 21, 4.5, 24), (1.5, 24, 4.5, 29)],
        "s": [(-1.5, -21, 1.5, -14), (-4.5, -24, 1.5, -21), (-4.5, -29, -1.5, -24)],
        "e": [(14, -1.5, 21, 1.5), (21, -4.5, 24, 1.5), (24, -4.5, 29, -1.5)],
        "w": [(-21, -1.5, -14, 1.5), (-24, -1.5, -21, 4.5), (-29, 1.5, -24, 4.5)],
    }
    for side, rects in legs.items():
        for k, r in enumerate(rects):
            s.append(_street(f"radial-{side}{k}", "radial", *r))
    return s


def _outer_towers(rng: random.Random) -> list[dict[str, Any]]:
    towers: list[dict[str, Any]] = []
    corners = [((36, 36), "towers-a", "-z"), ((-36, 36), "towers-a", "-z"), ((36, -36), "towers-b", "+z"), ((-36, -36), "towers-b", "+z")]
    for (cx, cz), sector, front in corners:
        towers.append({"center": [cx, cz], "footprint": [8.0, 8.0], "height": round(rng.uniform(34, 40), 2),
                       "sector": sector, "front": front})
    sides = [("n", "towers-a", "-z"), ("e", "towers-a", "-x"), ("s", "towers-b", "+z"), ("w", "towers-b", "+x")]
    for side, sector, front in sides:
        widths = [rng.uniform(19, 24) for _ in range(3)]
        scale = 64.0 / sum(widths)
        cursor = -32.0
        for k, w in enumerate(widths):
            span = w * scale
            lo, hi = cursor - (0.75 if k else 0.75), cursor + span + 0.75   # 1.5 m overlap with neighbours/corners
            cursor += span
            along = (lo + hi) / 2
            length = hi - lo
            inset = 32.5 if k % 2 == 0 else 33.5
            depth = 6.5
            across = inset + depth / 2
            near_corner = 4.0 if k in (0, 2) else 0.0
            height = round(rng.uniform(24, 32) + near_corner, 2)
            if side in ("n", "s"):
                center = [round(along, 3), round(across if side == "n" else -across, 3)]
                fp = [round(length, 3), depth]
            else:
                center = [round(across if side == "e" else -across, 3), round(along, 3)]
                fp = [depth, round(length, 3)]
            towers.append({"center": center, "footprint": fp, "height": height, "sector": sector, "front": front})
    rotation_for = {"-z": 180.0, "+z": 0.0, "-x": 270.0, "+x": 90.0}
    out = []
    for k, t in enumerate(towers, start=1):
        out.append({"id": f"tower-{k:02d}", "sector": t["sector"], "role": "outer", "center": t["center"],
                    "footprint": t["footprint"], "height": t["height"], "core_height": round(t["height"] - 2.0, 2),
                    "rotation": rotation_for[t["front"]], "front": t["front"], "seed": SEED + k})
    return out
```
上記に続けて `_inner_towers(rng)`（表の 6 棟、`core_height = height - 3`、`front` は広場を向く軸）、`_stalls(rng)`、`_clubs()`、`_shacks(rng, blocked_rects)`、`_bridges()`、`_ads(rng, towers, clubs)`、`_signs(stalls, clubs, ads)`、`_cables(rng, towers, stalls, clubs)`、`_lights(...)`、`_backdrop(rng)`、`_plaza_features()`、`_occluders(towers, bridges, ads)` を上記「配置の骨格」の値どおりに実装する。すべて固定順のリストで返し、`round(..., 3)` で丸める（JSON の決定性のため）。

レイキャストと検証:
```python
def ray_hit_distance(origin, direction, box_min, box_max) -> float | None:
    t0, t1 = -math.inf, math.inf
    for i in range(3):
        if abs(direction[i]) < 1e-12:
            if not box_min[i] <= origin[i] <= box_max[i]:
                return None
            continue
        a = (box_min[i] - origin[i]) / direction[i]
        b = (box_max[i] - origin[i]) / direction[i]
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    if t1 < max(t0, 0.0):
        return None
    return max(t0, 0.0)


def sightline_failures(data, *, step_deg=5, max_elev=25, elev_step=5) -> list[dict]:
    boxes = [(o["min"], o["max"], o["id"]) for o in data["occluders"]]
    wall = data["east_wall"]
    c, s = wall["center"], wall["size"]
    boxes.append(([c[0] - s[0] / 2, 0.0, c[2] - s[2] / 2], [c[0] + s[0] / 2, s[1], c[2] + s[2] / 2], "east-wall"))
    failures = []
    grid = [-9.0, -4.5, 0.0, 4.5, 9.0]
    for vx in grid:
        for vz in grid:
            origin = (vx, EYE, vz)
            for az in range(0, 360, step_deg):
                for el in range(0, max_elev + 1, elev_step):
                    a, e = math.radians(az), math.radians(el)
                    d = (math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a))
                    hits = [t for lo, hi, _ in boxes if (t := ray_hit_distance(origin, d, lo, hi)) is not None]
                    if not hits:
                        failures.append({"view": [vx, vz], "az": az, "el": el, "reason": "no hit"})
                        continue
                    t = min(hits)
                    p = [origin[i] + d[i] * t for i in range(3)]
                    if abs(p[0]) > HALF + 1e-6 or abs(p[2]) > HALF + 1e-6:
                        failures.append({"view": [vx, vz], "az": az, "el": el, "reason": "hit outside"})
    return failures
```

`validate_layout(data)` は次を検査し、違反を文字列で返す:
1. タワー・屋台・クラブ・小屋の footprint（回転を考慮した外接矩形）が 80×80 内
2. 広場 `[-10,10]²` と、道路（streets）に footprint が食い込まない（屋台は lane の外側、道路との重なり 0.05m 未満）
3. 外周タワー以外の footprint 同士の重なりなし（外周タワー同士は隣接ペアのみ許容）
4. 小屋同士・小屋と他要素の間隔 ≥ 0.6m
5. 光源の shadow ≠ "None" が 3 以下、`spot_angle` は Spot のみ正
6. ads の material は `materials.MATERIALS` の holo 系、anim "scroll" は `*_scroll` 素材、"spin" は kind "float" のみ
7. 電線の端点は `sources` のいずれかの面または屋根上にある（生成時に `attach` として付けた id を `cables[i]["attach"]` に入れ、その id が存在すること）

```python
def write_layout(path: Path) -> dict[str, Any]:
    data = build_layout()
    issues = validate_layout(data)
    if issues:
        raise ValueError(f"layout invalid: {issues[:5]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    write_layout(PROJECT_ROOT / "content" / "slum02" / "layout.json")
```

- [ ] **Step 4: テスト実行と遮蔽の調整**

Run: `uv run pytest tests/slum02/test_layout.py -q`
Expected: 10 passed。`test_sightlines_from_plaza_are_closed` が失敗したら、`failures` の `az/el` を集計し、該当方向の外周タワーの高さを +2m ずつ（上限 44m）上げるか、該当隙間に橋・wall 広告の occluder を足す。数字合わせで遮蔽を削らない。

- [ ] **Step 5: layout.json 生成**

Run: `uv run python -m modeling.slum02.layout && uv run python -c "import json;d=json.load(open('content/slum02/layout.json'));print({k:len(v) for k,v in d.items() if isinstance(v,list)})"`
Expected: towers 22, stalls 12, clubs 4, shacks 12, ads 30, lights 25 前後

- [ ] **Step 6: コミット**

```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/layout.py slum02/tests/slum02/test_layout.py slum02/content/slum02/layout.json
git commit -m "feat(slum02): add deterministic layout with sightline occlusion raycast

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Blender ビルド基盤（1 オブジェクト 1 メッシュ、UV、頂点カラー、AO ベイク、プレビュー、色空間の実測）

**Files:**
- Create: `slum02/modeling/slum02/uv.py`（akichi `uv.py` を移植、docstring のみ変更）
- Create: `slum02/modeling/slum02/blender_io.py`, `slum02/modeling/slum02/build.py`, `slum02/modeling/slum02/preview.py`
- Create: `slum02/modeling/slum02/sectors.py`（セクタ → Assembly 生成関数のディスパッチ。生成モジュールは後続タスクで登録）
- Test: `slum02/tests/slum02/test_build_pure.py`

**Interfaces:**
- Consumes: `geometry.Assembly / merge_assembly / MergedMesh`, `vcolor.vertex_colors / Spray`, `materials.make_blender_materials / MATERIALS`, `layout.build_layout / validate_layout`, `uv.metric_face_uvs / uv_triangle_issues`
- Produces:
  - `sectors.SECTORS: tuple[str, ...] = ("ground","plaza","towers-a","towers-b","towers-c","market","nightlife","shacks","ads","overhead","backdrop")`
  - `sectors.REGISTRY: dict[str, Callable[[dict], list[Assembly]]]` — 各生成モジュールが `sectors.register("name")` デコレータで登録
  - `sectors.sector_assemblies(data, sector) -> list[Assembly]`（未登録なら `NotImplementedError`）
  - `sectors.resource_report(assemblies, sector) -> dict`（`triangles`, `vertices`, `objects`, `materials`（使用素材名のソート済みリスト）, `material_count`, `submeshes`）
  - `blender_io.resonite_to_blender(p) -> Vec3`（(x, z, y)）
  - `blender_io.create_object(bpy, bmesh, merged, origin, material_lookup, *, uv_exempt=False) -> (obj, uv_issue_count)` — 頂点は `origin` を引いたローカル座標のまま、`obj.location = resonite_to_blender(origin)`
  - `blender_io.write_colors(obj, colors, name="Col")` — `FLOAT_COLOR` / `POINT` 属性を作り active/render に設定
  - `blender_io.bake_ao(bpy, objects, samples=16) -> dict`（`{"baked": n, "seconds": s}`、失敗時 `{"baked": 0, "error": str}`）
  - `blender_io.combine_ao(obj, strength=0.85)` — `Col *= lerp(1, AO, strength)`、`AO` 属性を削除
  - `build.write_scene(sector, output) -> report`、CLI `--sector --output [--no-ao]`、標準出力に `SLUM02_SECTOR_REPORT=<json>`
  - `preview.render(blend_path, output_png, camera: dict, size=(768, 432)) -> dict` — `resoloop blender run modeling/slum02/preview.py --arg=--blend ... --arg=--camera ... --arg=--output ...`
  - `postprocess.VERTEX_COLOR_SPACE`（本タスク Step 7 で決まる値を Task 14 で定義）

- [ ] **Step 1: uv.py を移植**

```bash
cp /workspaces/reso-world/akichi/modeling/akichi/uv.py modeling/slum02/uv.py
sed -i '1s/.*/"""Metric, face-local UV projections for slum02 meshes (ported from akichi)."""/' modeling/slum02/uv.py
```

- [ ] **Step 2: 失敗する純 Python テスト**

`tests/slum02/test_build_pure.py`:
```python
import pytest

from modeling.slum02 import geometry as g
from modeling.slum02 import sectors


def test_sector_order_fixed():
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
```

- [ ] **Step 3: sectors.py 実装**

```python
"""Sector registry: sector name -> pure Assembly generator (no bpy)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from modeling.slum02.geometry import Assembly, merge_assembly, triangle_count

SECTORS: tuple[str, ...] = ("ground", "plaza", "towers-a", "towers-b", "towers-c", "market",
                            "nightlife", "shacks", "ads", "overhead", "backdrop")
REGISTRY: dict[str, Callable[[dict[str, Any]], list[Assembly]]] = {}


def register(name: str):
    if name not in SECTORS:
        raise ValueError(name)
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


def _load_generators() -> None:
    # Imported lazily so each generator module self-registers; missing ones stay unregistered.
    import importlib
    for module in ("ground", "plaza", "towers", "stalls", "nightlife", "shacks", "ads", "overhead"):
        try:
            importlib.import_module(f"modeling.slum02.{module}")
        except ModuleNotFoundError as exc:
            if exc.name != f"modeling.slum02.{module}":
                raise


def sector_assemblies(data: dict[str, Any], sector: str) -> list[Assembly]:
    if sector not in SECTORS:
        raise KeyError(sector)
    _load_generators()
    if sector not in REGISTRY:
        raise NotImplementedError(f"sector {sector} has no generator yet")
    return REGISTRY[sector](data)


def resource_report(assemblies: list[Assembly], sector: str) -> dict[str, Any]:
    tris = verts = subs = 0
    mats: set[str] = set()
    for a in assemblies:
        m = merge_assembly(a)
        tris += sum(len(f) - 2 for f in m.faces)
        verts += len(m.vertices)
        subs += len(m.materials)
        mats.update(m.materials)
    return {"sector": sector, "objects": len(assemblies), "triangles": tris, "vertices": verts,
            "submeshes": subs, "materials": sorted(mats), "material_count": len(mats)}
```
（`triangle_count` の import は不要なら外す。）

Run: `uv run pytest tests/slum02/test_build_pure.py -q` → 3 passed

- [ ] **Step 4: blender_io.py 実装**

```python
"""bpy-side helpers (only imported inside Blender)."""
from __future__ import annotations

import time
from typing import Any

from modeling.slum02.geometry import MergedMesh, Vec3
from modeling.slum02.uv import metric_face_uvs, uv_triangle_issues

UV_PER_METER = 0.5


def resonite_to_blender(p) -> Vec3:
    return (p[0], p[2], p[1])


def create_object(bpy, bmesh, merged: MergedMesh, origin, material_lookup, *, uv_exempt=False):
    me = bpy.data.meshes.new(f"Slum02_{merged.name}_Mesh")
    me.from_pydata([resonite_to_blender(v) for v in merged.vertices], [], [list(f) for f in merged.faces])
    me.update()
    for name in merged.materials:
        me.materials.append(material_lookup[name])
    for poly, mat in zip(me.polygons, merged.face_materials):
        poly.material_index = mat
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    uv_layer = me.uv_layers.new(name="UV0")
    issues = 0
    for poly in me.polygons:
        ids = list(poly.loop_indices)
        pts = [me.vertices[me.loops[i].vertex_index].co for i in ids]
        uvs = metric_face_uvs(pts, tuple(-c for c in poly.normal), uv_per_meter=UV_PER_METER)
        for i, uv in zip(ids, uvs):
            uv_layer.data[i].uv = uv
        if not uv_exempt:
            for k in range(1, len(ids) - 1):
                issues += len(uv_triangle_issues((pts[0], pts[k], pts[k + 1]), (uvs[0], uvs[k], uvs[k + 1]),
                                                 poly.normal, uv_per_meter=UV_PER_METER, handedness=-1))
    obj = bpy.data.objects.new(merged.name, me)
    obj.location = resonite_to_blender(origin)
    return obj, issues


def write_colors(obj, colors, name: str = "Col") -> None:
    me = obj.data
    attr = me.color_attributes.get(name) or me.color_attributes.new(name=name, type="FLOAT_COLOR", domain="POINT")
    flat = [c for rgba in colors for c in rgba]
    attr.data.foreach_set("color", flat)
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = list(me.color_attributes).index(attr)


def bake_ao(bpy, objects, samples: int = 16) -> dict[str, Any]:
    scene = bpy.context.scene
    start = time.time()
    try:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = samples
        scene.render.bake.target = "VERTEX_COLORS"
        baked = 0
        for obj in objects:
            me = obj.data
            ao = me.color_attributes.get("AO") or me.color_attributes.new(name="AO", type="FLOAT_COLOR", domain="POINT")
            me.color_attributes.active_color = ao
            for o in bpy.context.view_layer.objects:
                o.select_set(False)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.bake(type="AO")
            baked += 1
        return {"baked": baked, "seconds": round(time.time() - start, 1), "samples": samples}
    except Exception as exc:  # AO is an enhancement: keep wear colours, record the failure
        return {"baked": 0, "error": f"{type(exc).__name__}: {exc}", "seconds": round(time.time() - start, 1)}


def combine_ao(obj, strength: float = 0.85) -> None:
    me = obj.data
    col, ao = me.color_attributes.get("Col"), me.color_attributes.get("AO")
    if ao is None:
        return
    n = len(col.data)
    cv, av = [0.0] * (4 * n), [0.0] * (4 * n)
    col.data.foreach_get("color", cv)
    ao.data.foreach_get("color", av)
    for i in range(n):
        f = 1 - strength + strength * av[4 * i]
        for k in range(3):
            cv[4 * i + k] *= f
    col.data.foreach_set("color", cv)
    me.color_attributes.remove(ao)
    col = me.color_attributes.get("Col")
    me.color_attributes.active_color = col
    me.color_attributes.render_color_index = list(me.color_attributes).index(col)
```

- [ ] **Step 5: build.py 実装**

```python
"""Sector .blend builder. Run: resoloop blender run modeling/slum02/build.py --arg=--sector --arg=ground --arg=--output --arg=artifacts/slum02/ground.blend --json"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modeling.slum02 import SEED  # noqa: E402
from modeling.slum02.geometry import merge_assembly  # noqa: E402
from modeling.slum02.layout import build_layout, validate_layout  # noqa: E402
from modeling.slum02.materials import make_blender_materials  # noqa: E402
from modeling.slum02.sectors import SECTORS, resource_report, sector_assemblies  # noqa: E402
from modeling.slum02.vcolor import vertex_colors  # noqa: E402


def _title(sector: str) -> str:
    return "".join(part.capitalize() for part in sector.split("-"))


def _reset(bpy) -> None:
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for m in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(m)


def write_scene(sector: str, output: Path, *, ao: bool = True) -> dict:
    import bmesh
    import bpy
    from modeling.slum02 import blender_io as io

    if sector not in SECTORS or output.suffix != ".blend":
        raise ValueError("bad sector or output")
    data = build_layout()
    if issues := validate_layout(data):
        raise RuntimeError(f"layout invalid: {issues[:4]}")
    _reset(bpy)
    title = _title(sector)
    export = bpy.data.collections.new(f"Slum02{title}Export")
    bpy.context.scene.collection.children.link(export)
    lookup = make_blender_materials()
    assemblies = sector_assemblies(data, sector)
    report = resource_report(assemblies, sector)
    objects, uv_issues = [], 0
    extra_objects = []
    for a in assemblies:
        merged = merge_assembly(a)
        obj, issues = io.create_object(bpy, bmesh, merged, a.origin, lookup, uv_exempt=a.meta.get("uv_exempt", False))
        io.write_colors(obj, vertex_colors(merged, a.origin, SEED + len(objects), a.meta.get("sprays", ())))
        obj["slum02_kind"] = a.kind
        obj["slum02_sector"] = sector
        export.objects.link(obj)
        objects.append(obj)
        uv_issues += issues
    # Sector hook (plaza GN scatter etc.) may add baked objects: modeling.slum02.<module>.blender_extras
    from modeling.slum02 import sectors as S
    hook = S.BLENDER_HOOKS.get(sector)
    if hook:
        extra_objects, extra_report = hook(bpy, bmesh, data, lookup, export)
        objects += extra_objects
        report.update(extra_report)
    report["ao"] = io.bake_ao(bpy, objects) if ao else {"baked": 0, "skipped": True}
    for obj in objects:
        io.combine_ao(obj)
    report["uv_issue_count"] = uv_issues
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(output.resolve()))
    col = bpy.data.collections.get(f"Slum02{title}Export")
    meshes = [o for o in col.objects if o.type == "MESH"]
    if len(meshes) != len(objects):
        raise RuntimeError(f"expected {len(objects)} meshes after reopen, got {len(meshes)}")
    for o in meshes:
        if not o.data.uv_layers or o.data.color_attributes.get("Col") is None or o.data.color_attributes.get("AO") is not None:
            raise RuntimeError(f"{o.name}: missing UV0/Col or leftover AO after reopen")
    report.update({"blend_path": str(output.resolve()), "blender_version": bpy.app.version_string,
                   "export_collection": col.name,
                   "triangles_blender": sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons)})
    (output.parent / f"{sector}-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sector", choices=SECTORS, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--no-ao", action="store_true")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    print("SLUM02_SECTOR_REPORT=" + json.dumps(write_scene(args.sector, args.output, ao=not args.no_ao), ensure_ascii=False))


if __name__ == "__main__":
    main()
```
`sectors.py` に `BLENDER_HOOKS: dict[str, Callable] = {}` と `register_blender_hook(name)` デコレータを追加する（plaza の GN scatter が使う）。

- [ ] **Step 6: preview.py 実装**

```python
"""Small self-review preview render (NOT final QA). Displays the Col attribute via a temporary shader tweak; never saves the .blend."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _show_vertex_colors(bpy) -> None:
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes.get("Principled BSDF")
        if bsdf is None:
            continue
        attr = nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["A"].default_value = bsdf.inputs["Base Color"].default_value
        links.new(attr.outputs["Color"], mix.inputs["B"])
        links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])


def _look_at(obj, target) -> None:
    from mathutils import Vector
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render(blend: Path, output: Path, camera: dict, size=(768, 432)) -> dict:
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    _show_vertex_colors(bpy)
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens_unit = "FOV"
    cam_data.angle = math.radians(camera.get("fov", 70))
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    scene.collection.objects.link(cam)
    pos, tgt = camera["position"], camera["target"]          # Resonite XYZ
    cam.location = (pos[0], pos[2], pos[1])
    _look_at(cam, (tgt[0], tgt[2], tgt[1]))
    scene.camera = cam
    sun = bpy.data.objects.new("PreviewSun", bpy.data.lights.new("PreviewSun", "SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    scene.collection.objects.link(sun)
    scene.world = scene.world or bpy.data.worlds.new("PreviewWorld")
    scene.world.color = (0.35, 0.45, 0.6)      # stand-in for the daytime world sky
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.filepath = str(output.resolve())
    engine = "BLENDER_EEVEE"
    try:
        scene.render.engine = engine
        bpy.ops.render.render(write_still=True)
    except Exception:
        engine = "CYCLES"
        scene.render.engine = engine
        scene.cycles.device = "CPU"
        scene.cycles.samples = 24
        bpy.ops.render.render(write_still=True)
    return {"output": str(output), "engine": engine, "size": list(size)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--blend", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--camera", required=True, help='JSON {"position":[x,y,z],"target":[x,y,z],"fov":70}')
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    print("SLUM02_PREVIEW=" + json.dumps(render(a.blend, a.output, json.loads(a.camera))))


if __name__ == "__main__":
    main()
```
プレビュー画像は `artifacts/slum02/preview/<sector>-<view>.png`。複数セクタをまとめて見る場合は `--blend` を複数受け取り `bpy.ops.wm.append` で他セクタのコレクションを取り込む拡張（`--extra-blend`）を Task 8 で行う。

- [ ] **Step 7: exporter の頂点カラー色空間を実測**

`tmp/probe/vc_probe.py`（Blender スクリプト、コミットしない）:
```python
import bpy, sys
sys.path.insert(0, "/workspaces/reso-world/slum02")
from modeling.slum02.materials import make_blender_materials
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
lookup = make_blender_materials()
me = bpy.data.meshes.new("Probe")
me.from_pydata([(0,0,0),(1,0,0),(1,1,0),(0,1,0)], [], [(0,1,2,3)])
me.materials.append(lookup["concrete_raw"])
me.uv_layers.new(name="UV0")
a = me.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
a.data.foreach_set("color", [0.5, 0.25, 0.1, 1.0] * 4)
me.color_attributes.active_color = a
me.color_attributes.render_color_index = 0
col = bpy.data.collections.new("ProbeExport"); bpy.context.scene.collection.children.link(col)
ob = bpy.data.objects.new("Probe", me); col.objects.link(ob)
bpy.ops.wm.save_as_mainfile(filepath="/workspaces/reso-world/slum02/tmp/probe/vc_probe.blend")
```
```bash
mkdir -p tmp/probe
resoloop blender run tmp/probe/vc_probe.py --json
resoloop blender export tmp/probe/vc_probe.blend --output tmp/probe/vc-v1 --name Probe --collection ProbeExport --parent Root --preserve-hierarchy --json
grep -o '"colors\?"[^]]*]' tmp/probe/vc-v1/*.mesh.json | head -c 400
```
判定: 値が `0.5, 0.25, 0.1` 付近なら `VERTEX_COLOR_SPACE = "Linear"`、`0.735, 0.537, 0.349` 付近なら `"sRGB"`。頂点カラーが出力されていない場合は `domain="CORNER"`, `type="BYTE_COLOR"` で再試行し、出力された組み合わせを `blender_io.write_colors` に反映する。結果を `artifacts/slum02/probe-vertex-color.json` に `{"attribute": {...}, "exported_sample": [...], "space": "Linear|sRGB"}` として記録する。

- [ ] **Step 8: 一時ジェネレータでスモーク**

`ground` の登録がまだないので、`tmp/probe/smoke_sector.py` から `sectors.register("ground")` で 1 つの `subdivided_box` を返す一時関数を登録し `write_scene("ground", tmp/probe/smoke.blend)` を呼ぶ。AO ありで成功し、`SLUM02_SECTOR_REPORT` に `ao.baked == 1` が出ること、プレビューが PNG で出ることを確認（Read で画像を開いて頂点カラーの暗部が見えること）。確認後 tmp は削除しない（gitignore 対象）。

- [ ] **Step 9: 全テストとコミット**

Run: `uv run pytest tests/slum02 -q` → all passed
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/uv.py slum02/modeling/slum02/blender_io.py slum02/modeling/slum02/build.py slum02/modeling/slum02/preview.py slum02/modeling/slum02/sectors.py slum02/tests/slum02/test_build_pure.py slum02/artifacts/slum02/probe-vertex-color.json
git commit -m "feat(slum02): add Blender build core with vertex colours, AO bake and preview

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## プレビュー自己レビュー手順（Task 5〜13 共通）

各セクタの .blend をビルドした後、次の手順で見た目を確認して直す。**最終確認ではなく反復用**（最終の見た目確認は実機で行い、未確認なら pending とする）。

1. ビルド: `resoloop blender run modeling/slum02/build.py --arg=--sector --arg=<S> --arg=--output --arg=artifacts/slum02/<S>.blend --json`（AO ありで 1 回。形状の試行中は `--arg=--no-ao` で短縮してよい）
2. プレビュー 2 枚以上: 中景（対象全体が入る距離）と近景（2〜4m）。`resoloop blender run modeling/slum02/preview.py --arg=--blend --arg=artifacts/slum02/<S>.blend --arg=--output --arg=artifacts/slum02/preview/<S>-mid.png --arg=--camera --arg='{"position":[...],"target":[...],"fov":60}' --json`
3. Read ツールで PNG を開き、次の 6 項目を判定する:
   - シルエットが箱の寄せ集めに見えないか（段差、張り出し、凹みで陰影ができているか）
   - 素材の分離（コンクリート / 金属 / 布 / 木 / 発光）が中景で読めるか
   - 汚れに原因があるか（足元の汚れ、窓下の雨だれ、錆の位置）。均一なノイズになっていないか
   - スケール（ドア 2.1m、手すり 1.0m、屋台カウンタ 0.9m）が妥当か
   - 浮き・めり込み・Z ファイティングがないか
   - ディテールが焦点（入口、看板、屋台の棚）に集まり、全面に均一に散っていないか
4. 問題があればジェネレータを直して 1 に戻る（1 セクタ最大 3 往復）。指摘と対応を `artifacts/slum02/preview/review.md` に追記する（形式: `## <S> 第N回` → 指摘 → 修正内容）
5. プレビュー PNG はコミットする（軽量なので証跡として残す）

---

### Task 5: 地面（ground）と遠景（backdrop）

**Files:**
- Create: `slum02/modeling/slum02/ground.py`
- Test: `slum02/tests/slum02/test_ground.py`

**Interfaces:**
- Consumes: `layout` の `streets / plaza / backdrop / towers`、`geometry.*`、`sectors.register`
- Produces:
  - `@register("ground") ground_assemblies(data) -> list[Assembly]`: `ground-base`（80×80 スラブ。上面 y=0.10。街区の床 = `concrete_stained`、道路 = `asphalt`。道路と街区は同じメッシュの別素材面で、境界に 0.02m の段差）、`ground-curbs`（道路縁の縁石 0.15m、欠けを 15% の確率で入れる）、`ground-puddles`（`asphalt_wet` の不定形 8 角形 14 個、上面 y=0.104）、`ground-details`（マンホール 6、側溝グレーチング、壁際のゴミ・紙くず 40 片）
  - `@register("backdrop") backdrop_assemblies(data) -> list[Assembly]`: `backdrop-ground`（|x|,|z|=40 の正方形から半径 220m の円までのリング。上面 y=0.05、64 分割、`backdrop_ground`）と `backdrop-mass-NN`（masses ごと 1 オブジェクト: 2〜3 段のセットバック塊 `backdrop_mass`、中心向きの面に `window_lit` の窓帯（4m ごとの行、長さランダムの薄い帯）、頂部に `neon_red` の航空障害灯 2〜4 個、masses のうち 3 つに `holo_magenta` / `holo_cyan` の巨大パネル）
  - 定数 `GROUND_TOP = 0.10`

- [ ] **Step 1: テスト**

`tests/slum02/test_ground.py`:
```python
import math

from modeling.slum02 import geometry as g
from modeling.slum02 import ground
from modeling.slum02.layout import build_layout


def _by_name(assemblies):
    return {a.name: a for a in assemblies}


def test_ground_slab_extent_and_top():
    a = _by_name(ground.ground_assemblies(build_layout()))
    base = a["ground-base"]
    lo, hi = g.bounds(base.parts)
    assert lo[0] == -40 and lo[2] == -40 and hi[0] == 40 and hi[2] == 40
    assert abs(hi[1] - ground.GROUND_TOP) < 0.03
    mats = {p.material for p in base.parts}
    assert {"asphalt", "concrete_stained"} <= mats


def test_puddles_and_manholes():
    a = _by_name(ground.ground_assemblies(build_layout()))
    assert sum(1 for p in a["ground-puddles"].parts if p.material == "asphalt_wet") == 14
    assert sum(1 for p in a["ground-details"].parts if p.name.startswith("manhole")) == 6


def test_backdrop_budget_and_extent():
    data = build_layout()
    parts = ground.backdrop_assemblies(data)
    tris = sum(g.triangle_count(p) for a in parts for p in a.parts)
    assert tris <= 20000
    ring = _by_name(parts)["backdrop-ground"]
    radius = max(math.hypot(v[0], v[2]) for p in ring.parts for v in p.vertices)
    assert 215 <= radius <= 221
    inner = min(max(abs(v[0]), abs(v[2])) for p in ring.parts for v in p.vertices)
    assert abs(inner - 40) < 1e-6
    assert sum(1 for a in parts if a.name.startswith("backdrop-mass-")) == len(data["backdrop"]["masses"])


def test_backdrop_has_lit_windows_and_aviation_lights():
    mats = {p.material for a in ground.backdrop_assemblies(build_layout()) for p in a.parts}
    assert {"window_lit", "neon_red", "backdrop_mass"} <= mats
```

- [ ] **Step 2: 失敗確認** — Run: `uv run pytest tests/slum02/test_ground.py -q` → FAIL

- [ ] **Step 3: 実装**

要点（すべて `random.Random(SEED + 101)` などセクタ固有のシードで決定論）:
```python
@register("ground")
def ground_assemblies(data):
    streets = data["streets"]
    base_parts = []
    # 2 m grid over 80x80; each cell's material = asphalt if its centre lies in any street rect, else concrete_stained.
    step = 2.0
    for i in range(40):
        for j in range(40):
            x0, z0 = -40 + i * step, -40 + j * step
            cx, cz = x0 + 1, z0 + 1
            on_street = any(s["min"][0] <= cx <= s["max"][0] and s["min"][1] <= cz <= s["max"][1] for s in streets) \
                or (abs(cx) < 10 and abs(cz) < 10)
            top = GROUND_TOP - (0.02 if on_street else 0.0)
            mat = "asphalt" if on_street else "concrete_stained"
            base_parts.append(g.mesh(f"cell-{i}-{j}", [(x0, top, z0), (x0, top, z0 + step), (x0 + step, top, z0 + step), (x0 + step, top, z0)],
                                     [(0, 1, 2, 3)], mat))
    base_parts.append(g.box("slab-body", (0, -0.1, 0), (80, 0.16, 80), "concrete_dark"))
    ...
```
（面の上向きは Blender 側の `recalc_face_normals` では決まらないため、上の頂点順 `(x0,z0)→(x0,z0+s)→(x0+s,z0+s)→(x0+s,z0)` で +Y 向きになることをテスト `test_ground_slab_extent_and_top` の後に `g.merge_assembly` で面法線 y>0 を確認するアサーションとして追加する。）

縁石: 各 street 矩形の 4 辺のうち街区に接する辺に沿って、長さ 1.0〜2.5m の `beveled_box`（高さ 0.15、幅 0.18、bevel 0.02、素材 `concrete_raw`）を並べ、15% をスキップ（欠け）。水たまり: 道路上の点を棄却サンプリングし、半径 0.6〜1.8m の 8 角形（頂点半径を ±25% ジッタ）。マンホール: `cylinder(r=0.35, h=0.03, 16 分割, steel_dark)` を ring と lane に 6 個。ゴミ: 外周タワー・内側タワーの壁際 0.3m 以内に `box` 0.1〜0.4m の `plywood / tarp_* / rubber` 片 40。

遠景リング: 内周は正方形 |x|,|z|=40 上に 64 点（周長を等分）、外周は半径 220 の円上に 64 点（同じ角度順）、四角形 64 枚。mass: `center, footprint(w,d), height` から下段（高さ 55%）・中段（幅 80%、30%）・上段（幅 55%、15%）の 3 箱（細分割なし）。窓帯: 中心向きの 2 面について、4m ごとに `rng.random() < 0.55` の区間に厚さ 0.05 の帯を面から 0.05 浮かせる。

- [ ] **Step 4: テスト** — Run: `uv run pytest tests/slum02/test_ground.py -q` → 4 passed（面法線アサーション含む）

- [ ] **Step 5: ビルドとプレビュー自己レビュー**（共通手順。視点: ground は `{"position":[0,1.7,-12],"target":[0,0,8],"fov":70}`、backdrop は `{"position":[0,20,0],"target":[0,40,120],"fov":70}`）

- [ ] **Step 6: コミット**
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/ground.py slum02/tests/slum02/test_ground.py slum02/artifacts/slum02/ground-report.json slum02/artifacts/slum02/backdrop-report.json slum02/artifacts/slum02/ground.blend slum02/artifacts/slum02/backdrop.blend slum02/artifacts/slum02/preview
git commit -m "feat(slum02): add ground and distant backdrop sectors

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 広場（廃工場跡地）の構造物と東の巨大壁（純 Python）

**Files:**
- Create: `slum02/modeling/slum02/plaza.py`
- Test: `slum02/tests/slum02/test_plaza.py`

**Interfaces:**
- Consumes: `layout.plaza / east_wall / plaza_features`、`geometry.*`（`GridBuilder`, `transformed_xyz` を含む）、`vcolor.Spray`、`ground.GROUND_TOP`
- Produces:
  - `FLOOR_TOP = 0.12`
  - `@register("plaza") plaza_assemblies(data) -> list[Assembly]`:
    - `plaza-floor`（`factory_floor` の 20×20 床。ピット 2 箇所は床に穴を開け、内側に壁 `concrete_dark` と底 `mud`＋`asphalt_wet`（溜まり水）。ひび割れ = 幅 0.04 の暗い帯 `concrete_dark` を折れ線で 12 本、上面 +0.004）
    - `plaza-machine-bases`（機械基礎台座 5 個 `concrete_raw` 0.3〜0.6m、アンカーボルト `steel_dark`）
    - `plaza-columns`（H 形鋼柱 5 本、フランジ 0.3、せい 0.4。2 本は 8〜25° 傾斜、1 本は途中で折れて上半分が地面に倒れている。柱脚ベースプレート。素材 `rust` / `paint_yellow_faded`）
    - `plaza-crane-rail`（2 本の柱の上、高さ 7m の走行梁 12m。片端が折れて地面へ垂れ下がる。`paint_yellow_faded` + `rust`）
    - `plaza-truss`（落下した鋸屋根トラス断片 8m、山形鋼を細い box で組み、15° 傾けて瓦礫に寄りかかる）
    - `plaza-press` / `plaza-conveyor` / `plaza-tank`（大型機械残骸 3 つ、それぞれ 1 オブジェクト）
    - `plaza-car`（焼けた車両。車体 `rust_dark`、窓なしのキャビン、ホイール `steel_dark`、タイヤは焼失）
    - `plaza-fire-barrel`（ドラム缶 `rust_dark`、上面に `neon_orange` の燠火面、周囲に木片）
    - `plaza-perimeter`（北・南・西辺の崩れた低い塀 0.6〜1.8m と金網フェンスの枠・支柱。出入口 2 箇所は空ける）
    - `east-wall`（`wall_with_openings` 幅 20 × 高さ 8.8 × 厚さ 0.8、max_edge 0.25（スプレー域）、上部に高さ 0〜1.2m の不揃いな崩れブロック、露出鉄筋 `tube` 18 本、広場側の付け柱 5 本、高所の窓凹み 4 つ。`meta["sprays"]` にオーバースプレーとタグ落書き、`meta["spray_art"]` に文字配置）
  - `spray_layout() -> dict`: `{"lines": [{"text": "トーキョー", "baseline_y": 5.9, "height": 2.8, "center_z": 0.0}, {"text": "N", ...}, {"ring": ...}, {"text": "VA", ...}], "max_width": 17.0, "plane_x": 9.195}` — 1 行目「トーキョー」、2 行目「N◎VA」（`◎` は二重リングの自前ジオメトリ）
  - `ring_glyph(center, outer_radius, band, depth) -> tuple[MeshData, MeshData]` — `◎` を「外リング＋内リング」の 2 枚（赤塗り用）と、それを 0.06m 太らせた黒縁用 2 枚として返す（戻り値は `(red_mesh, black_mesh)`）

`geometry.py` への追加（Task 1 で実装済み）: `GridBuilder`、`rotate_xyz(point, rx, ry, rz)`（X→Y→Z の順に回転）、`transformed_xyz(mesh, rx, ry, rz, offset, name=None)`、`wall_with_openings(..., closed=True)`（`closed=False` で背面と端面を省く）。

- [ ] **Step 1: テスト**

`tests/slum02/test_plaza.py`:
```python
from modeling.slum02 import geometry as g
from modeling.slum02 import plaza
from modeling.slum02.layout import build_layout


def _named():
    return {a.name: a for a in plaza.plaza_assemblies(build_layout())}


def test_expected_objects():
    names = set(_named())
    assert {"plaza-floor", "plaza-columns", "plaza-crane-rail", "plaza-truss", "plaza-press", "plaza-conveyor",
            "plaza-tank", "plaza-car", "plaza-fire-barrel", "plaza-perimeter", "east-wall"} <= names


def test_everything_inside_plaza_footprint():
    for a in plaza.plaza_assemblies(build_layout()):
        lo, hi = g.bounds([g.transformed(p, 0.0, a.origin) for p in a.parts])
        assert lo[0] >= -10.3 and hi[0] <= 10.3 and lo[2] >= -10.3 and hi[2] <= 10.3, a.name


def test_east_wall_geometry_and_front_plane():
    wall = _named()["east-wall"]
    lo, hi = g.bounds([g.transformed(p, 0.0, wall.origin) for p in wall.parts if p.name.startswith("wall-body")])
    assert abs(lo[0] - 9.2) < 1e-6 and abs(hi[0] - 10.0) < 1e-6
    assert abs(lo[2] + 10) < 1e-6 and abs(hi[2] - 10) < 1e-6
    assert 8.7 <= hi[1] <= 10.05
    assert sum(1 for p in wall.parts if p.name.startswith("rebar")) == 18


def test_overspray_sits_on_wall_face():
    wall = _named()["east-wall"]
    sprays = wall.meta["sprays"]
    assert len(sprays) >= 20
    assert all(abs(s.center[0] - 9.2) < 0.3 for s in sprays)


def test_spray_art_layout_has_ring_glyph_and_fits():
    lay = plaza.spray_layout()
    texts = [l.get("text") for l in lay["lines"] if "text" in l]
    assert texts == ["トーキョー", "N", "VA"]
    assert any("ring" in l for l in lay["lines"])
    red, black = plaza.ring_glyph((9.19, 3.5, 0.0), 1.2, 0.28, 0.006)
    rlo, rhi = g.bounds([red])
    blo, bhi = g.bounds([black])
    assert bhi[1] - blo[1] > rhi[1] - rlo[1]  # black outline is fatter than the red fill
    assert rlo[0] < 9.2 and blo[0] > rlo[0]    # red sits in front of black (closer to plaza, -X)


def test_exits_are_open():
    perim = _named()["plaza-perimeter"]
    for x0, z0, x1, z1 in build_layout()["plaza_features"]["exits"]:
        for p in perim.parts:
            lo, hi = g.bounds([p])
            overlap = lo[0] < x1 and hi[0] > x0 and lo[2] < z1 and hi[2] > z0
            assert not overlap, p.name
```

- [ ] **Step 2: 失敗確認** — Run: `uv run pytest tests/slum02/test_plaza.py -q` → FAIL

- [ ] **Step 3: 実装の要点**

- 東の壁: 局所座標（`wall_with_openings` の前面 +Z）を `rotate_y(-π/2)` で前面 -X 向きにし、origin `(9.6, FLOOR_TOP-0.12, 0)`。本体は `wall-body`（`concrete_raw`）、崩れた上端は `wall-crown-NN`（`concrete_raw`、高さ 0.2〜1.2 の box を z 方向に 0.4〜1.6m 刻みで並べ、20% を欠損）、付け柱 `wall-pilaster-NN`（広場側に 0.35 張り出し、幅 0.6、z = -8, -4, 0, 4, 8。ただし文字と重なる中央 3 本は高さ 3.0 までに留めて文字の下で途切れさせる）、鉄筋 `rebar-NN`（`tube` 3 点折れ線、半径 0.012、`rust`）
- 文字配置（`spray_layout`）: 1 行目「トーキョー」は baseline y 5.9、字高 2.8、z 中心 0（Blender 側で幅 ≤ 17m になるよう一様縮小）。2 行目は「N」→ `◎` → 「VA」を横に並べ、baseline y 1.9、字高 3.2。`◎` の中心は 2 行目の中央、外径 1.4、帯幅 0.28、内リング外径 0.75
- `ring_glyph`: 外リングと内リングをそれぞれ 48 分割の環（厚さ `depth` の薄い板）で作る。赤 = 壁面から -X 方向へ 0.010 浮かせる、黒 = 帯を 0.06 太らせて 0.005 浮かせる（赤が手前）
- オーバースプレー（`meta["sprays"]`）: 文字の各行に沿って 0.8m 間隔で黒ハロー（半径 0.6〜1.0、色 (0.15,0.15,0.16)、強度 0.35）、赤の吹きこぼれ（半径 0.4〜0.7、色 (1.0,0.3,0.3)、強度 0.3）、壁下部 0.5〜3m に他の落書きタグ 6 個（lime (0.6,1.0,0.3) / cyan (0.3,0.9,1.0) / magenta (1.0,0.3,0.8)、強度 0.45）。中心 x は 9.2（壁面）
- 瓦礫以外の構造物の寸法は上記 Produces の値を使う。H 形鋼: `h_beam(name, length, depth=0.4, flange=0.3, t=0.025, material)` を plaza.py 内に定義（フランジ 2 枚＋ウェブ 1 枚の box、y 方向に長い）。傾きは `transformed_xyz`
- 車: 下部ボディ `beveled_box`（4.2×0.7×1.8、bevel 0.08）、キャビン台形（`prism` 相当を自前の 8 頂点で）、ホイール 4 本（`cylinder` axis="X"、r 0.3）。車体は 12° ヨー、片側に 5° 傾く（タイヤ焼失）
- すべての素材は `materials.MATERIALS` に存在するキーのみ使う

- [ ] **Step 4: テスト** — Run: `uv run pytest tests/slum02/test_plaza.py -q` → 6 passed

- [ ] **Step 5: コミット**（ビルドは Task 7 の Blender フックと合わせて行う）
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/plaza.py slum02/modeling/slum02/geometry.py slum02/tests/slum02/test_plaza.py slum02/tests/slum02/test_geometry.py
git commit -m "feat(slum02): add factory-ruin plaza structures and east wall

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 広場の Blender フック（スプレー文字メッシュ化、Geometry Nodes 瓦礫 scatter）

**Files:**
- Modify: `slum02/modeling/slum02/plaza.py`（`rubble_prototypes`、`scatter_surface`、`blender_hook` を追加）
- Test: `slum02/tests/slum02/test_plaza_scatter.py`

**Interfaces:**
- Consumes: `FONT_PATH`、`plaza.spray_layout / ring_glyph`、`sectors.register_blender_hook`、`blender_io.create_object / write_colors`、`vcolor.vertex_colors`
- Produces:
  - `rubble_prototypes() -> list[tuple[str, MeshData, str]]` — `(size_class, mesh, name)` の 8 種（concrete-chunk ×3、rebar-chunk、slab-shard、brick-block、beam-stub、slate-sheet）。**原点は底面中央、底面が y = -0.1 × 高さ（沈み込み 10%）**
  - `scatter_surface(data) -> MeshData` — 広場床のうち keep-out（機械基礎、車、焚き火、ピット、出入口から広場中心への通路幅 1.4m）を除いた 0.5m 格子の面（y = FLOOR_TOP）
  - `SCATTER_CLASSES = {"small": (3.0, 0.15, 0.40), "medium": (0.6, 0.4, 0.9), "large": (0.12, 0.9, 1.8)}` — (密度/㎡, 最小スケール, 最大スケール)
  - `@register_blender_hook("plaza") blender_hook(bpy, bmesh, data, lookup, export_collection) -> (objects, report)`:
    - `spray-art` オブジェクト 1 つ（黒縁・赤塗り・`◎`・垂れを 1 メッシュに結合、素材 `spray_black` / `spray_red`）
    - `plaza-rubble` オブジェクト 1 つ（GN を realize して焼いた静的メッシュ）
    - `report["spray_art"] = {"method": "font-mesh"|"text-renderer", "width_m": float, "drips": int}`、`report["scatter"] = {"method": "geometry-nodes"|"python-fallback", "instances": {...}, "triangles": int, "exposed_fraction": float}`

- [ ] **Step 1: 純 Python テスト**

`tests/slum02/test_plaza_scatter.py`:
```python
from modeling.slum02 import geometry as g
from modeling.slum02 import plaza
from modeling.slum02.layout import build_layout


def test_prototypes_sit_on_base_with_limited_sink():
    protos = plaza.rubble_prototypes()
    assert len(protos) == 8
    for cls, mesh, name in protos:
        assert cls in plaza.SCATTER_CLASSES
        lo, hi = g.bounds([mesh])
        height = hi[1] - lo[1]
        assert -0.101 * height <= lo[1] <= 0.0, name
        above = sum(1 for v in mesh.vertices if v[1] > 0) / len(mesh.vertices)
        assert above >= 0.6, name


def test_scatter_surface_avoids_keepouts():
    data = build_layout()
    surf = plaza.scatter_surface(data)
    fx, fz = data["plaza_features"]["fire_barrel"]
    for face in surf.faces:
        cx = sum(surf.vertices[i][0] for i in face) / len(face)
        cz = sum(surf.vertices[i][2] for i in face) / len(face)
        assert (cx - fx) ** 2 + (cz - fz) ** 2 > 1.2 ** 2
        assert abs(cx) < 10 and abs(cz) < 10
        for x0, z0, x1, z1 in data["plaza_features"]["pits"]:
            assert not (x0 <= cx <= x1 and z0 <= cz <= z1)
    area = sum(0.25 for _ in surf.faces)
    assert 200 <= area <= 360


def test_expected_instance_budget():
    area = sum(0.25 for _ in plaza.scatter_surface(build_layout()).faces)
    expected = sum(d * area for d, _, _ in plaza.SCATTER_CLASSES.values())
    assert 700 <= expected <= 1300
```

- [ ] **Step 2: 失敗確認 → 実装 → 成功確認**（`uv run pytest tests/slum02/test_plaza_scatter.py -q` → 3 passed）

プロトタイプ: 各コンクリ塊は `subdivided_box` を max_edge 0.5 で作り、頂点を `vcolor.value_noise3` で ±18% ジッタ（底面の頂点は y を固定）した後、全体を `-0.1*height` 下げる。rebar-chunk は塊＋`tube` 2〜3 本。slate-sheet は波板（6 山の折れ面、厚さなしの両面 → 片面 2 枚）。

- [ ] **Step 3: blender_hook の GN scatter**

akichi の `_try_gn_scatter`（`/workspaces/reso-world/akichi/modeling/akichi/build.py`）を移植し、次を変更する:
- プロトタイプコレクションをサイズクラスごとに 3 つ作り、Distribute Points on Faces → Instance on Points → Realize を 3 系統並列にして Join Geometry で結合
- Distribute の `Density` = クラスの密度、`Seed` = SEED + クラス番号、`Density Factor` に Named Attribute `density`（Float）を接続。`density` 属性は `scatter_surface` の各頂点に `0.35 + 0.65 * value_noise3(x*0.25, 0, z*0.25, SEED+9)` を書く（山と空きのムラ）
- Rotation: Random Value (FLOAT_VECTOR) min `(-0.26, -0.26, -π)` max `(0.26, 0.26, π)`（Blender 座標で X/Y の傾き ±15°、Z ヨー全周）
- Scale: Random Value (FLOAT) min/max = クラスのスケール範囲 → Instance on Points の Scale
- ノード名・ソケット名は Blender 5.0.1 の RNA で確認済みのもの（akichi のコメント参照）。`Density Factor` ソケットが無い場合は `nodes["Distribute Points on Faces"].inputs.keys()` を出力して名前を確認し、見つからなければ密度一様で続行し `report["scatter"]["density_factor"] = False` を記録
- 焼いたメッシュの素材インデックスから `MergedMesh` を組み立て（素材名は Blender 名から `Slum02_` を除いたもの）、`vertex_colors(merged, (0,0,0), SEED+77)` を `write_colors` で書き込む。UV は metric（`uv_exempt=True`）
- `exposed_fraction` = y > FLOOR_TOP の頂点の割合。**0.45 未満なら RuntimeError**（Review Focus 5）
- GN が 2 回失敗したら純 Python フォールバック（同じ密度・スケール・回転範囲を `random.Random(SEED+250)` で実行し、同じ 1 オブジェクトにまとめる）

- [ ] **Step 4: blender_hook のスプレー文字**

```python
def _text_mesh(bpy, text, size, offset, extrude, font):
    curve = bpy.data.curves.new(f"spray_{text}_{offset}", "FONT")
    curve.body = text
    curve.font = font
    curve.size = size
    curve.offset = offset          # >0 fattens glyphs -> black outline layer
    curve.extrude = extrude
    curve.align_x = "CENTER"
    obj = bpy.data.objects.new(curve.name, curve)
    bpy.context.scene.collection.objects.link(obj)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    bpy.data.objects.remove(obj, do_unlink=True)
    return me   # Blender XY plane, glyphs face +Z (Blender), baseline at y=0
```
- フォント: `bpy.data.fonts.load(str(FONT_PATH))`。例外時は `report["spray_art"]["method"] = "text-renderer"` にして spray-art オブジェクトは `◎` と垂れなし（Task 14 で TextRenderer 2 枚重ねを追加する）
- 各行の赤メッシュ（offset 0、extrude 0.003）と黒メッシュ（offset 0.06、extrude 0.002）を作り、bmesh で「Blender XY 平面 → 壁面」へ変換: Blender の (x, y, z) → Resonite の (plane_x - dz, baseline_y + y*scale, center_z - x*scale)（壁は広場側 -X を向くので、文字の右方向 = Resonite -Z…ではなく、**広場から見て左→右 = Resonite +Z → -Z?** を確認するため、`N` の縦画が左側に来ることを 1 回の小プレビュー（`{"position":[0,4,0],"target":[9.2,4,0],"fov":60}`）で確かめ、鏡像なら z の符号を反転する）
- 赤は壁面から 0.010、黒は 0.005 手前（-X 方向）に置く
- 1 行目の幅が 17m を超える場合は一様縮小（`report["spray_art"]["width_m"]` に記録）
- 垂れ: 赤メッシュの頂点を z 方向 0.3m のバケットに分け、各バケットで最も低い頂点を候補とし、`random.Random(SEED+31)` で 22 本を選ぶ。各垂れは幅 0.03〜0.06、長さ 0.2〜1.4m の細い板（壁面から 0.010）と先端の小さな滴（0.05 の `beveled_box`）
- `◎` は `plaza.ring_glyph` の 2 メッシュを使う
- 全部を 1 つの bmesh に結合し `spray-art` オブジェクトにする（素材スロット: `spray_black`, `spray_red`）。頂点カラーは `Spray` なしの `vertex_colors`（paint family）で書く

- [ ] **Step 5: ビルドとプレビュー自己レビュー**

```bash
resoloop blender run modeling/slum02/build.py --arg=--sector --arg=plaza --arg=--output --arg=artifacts/slum02/plaza.blend --json
```
Expected: `SLUM02_SECTOR_REPORT` に `spray_art.method == "font-mesh"`、`scatter.method == "geometry-nodes"`、`scatter.exposed_fraction >= 0.45`。
プレビュー視点: 広場俯瞰 `{"position":[-9,6,-9],"target":[4,0,4],"fov":70}`、壁正面 `{"position":[-6,2.5,0],"target":[9.2,4.5,0],"fov":75}`、瓦礫近景 `{"position":[-2,1.2,-3],"target":[1,0,0],"fov":60}`。共通手順の 6 項目に加えて、文字が読めること・鏡像でないこと・赤と黒の順（赤が手前）を確認する。

- [ ] **Step 6: コミット**
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/plaza.py slum02/tests/slum02/test_plaza_scatter.py slum02/artifacts/slum02/plaza.blend slum02/artifacts/slum02/plaza-report.json slum02/artifacts/slum02/preview
git commit -m "feat(slum02): add GN rubble scatter and spray-painted TOKYO NOVA wall art

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 廃ビル群（towers-a / towers-b / towers-c）

**Files:**
- Create: `slum02/modeling/slum02/towers.py`
- Test: `slum02/tests/slum02/test_towers.py`

**Interfaces:**
- Consumes: `layout.towers`（`collapse` と `core_height` を含む）、`geometry.*`
- Produces:
  - `FLOOR_H = 3.2`、`BAY = 3.6`
  - `build_tower(spec: dict) -> Assembly` — origin = `(cx, 0, cz)`、parts は回転を焼き込んだローカル座標。`meta["occludes"] = [f"occ-{spec['id']}"]`（role outer のみ）
  - `@register("towers-a")`, `@register("towers-b")`, `@register("towers-c")` — それぞれ layout の `sector` で絞った `build_tower` の列
  - タワー 1 棟の構成（すべて 1 オブジェクト内の部品）:
    - `facade-front` / `facade-back` / `facade-left` / `facade-right`: `wall_with_openings(closed=False)`、厚さ 0.5、窓凹み 0.3。前面と側面は窓割り（ベイ 3.6m ごとに幅 1.0〜1.6 × 高さ 1.6〜2.0 の縦長窓、階ごと）、外向きの背面（role outer の外側）は窓なしで max_edge 4.0。前面と側面の max_edge は 1.2
    - `fin-NN`: ベイ境界の付け柱（0.35 張り出し、幅 0.4、全高。brutalist のリズム）
    - `slab-lip-NN`: 各階の床スラブの縁（0.2 張り出し、高さ 0.3）
    - `pane-NN`: 窓凹みの奥 0.25 に `glass_dark`（60%）、`window_lit`（6%）、なし＝暗い奥壁（34%。割れた窓）
    - `podium-entrance`: 1 階前面の深い凹み入口（幅 3.6、高さ 3.0、奥行 1.2 の box で囲う影の入口）とシャッター `corrugated_rust`
    - `balcony-NN`: 前面のランダムなベイ・階に片持ちバルコニー（奥行 1.2、パラペット 1.0）。30% に物干し（tube）・室外機・ブルーシート
    - `parasite-NN`: 増築のトタン箱（2.0〜3.5m、鉄骨ブラケット付き）を中層に 2〜4 個
    - `stair-NN`: 側面の外付け鉄骨階段（ジグザグ、踊り場ごと）を 50% の棟に
    - `scaffold-NN`: パイプ足場（縦 1.8m・横 1.8m の格子）を 30% の棟に
    - `ac-NN`: 室外機（0.8×0.6×0.3 の beveled box＋ファンの円盤）を前面・側面に 10〜24 個
    - `drain-NN`: 角の縦樋 `pipe`（steel_dark）と、その吐出口の下に錆だれスプレー
    - `roof-*`: パラペット、塔屋、水槽（脚付き cylinder）、アンテナ（pipe）、屋上小屋（role outer のみ）
    - `neon-strip`: 50% の棟に縦長のネオン看板箱（sign 裏板 steel_dark ＋ 前面 neon_*）
    - `collapse-*`: `collapse > 0` の棟は上から `collapse` 階分の片側コーナーを欠損させ、露出スラブ（鉄筋 tube 付き）と崩れた破片を載せる。**core_height 以下のファサードは欠損させない**
  - `meta["sprays"]`: 1 階の落書きタグ 3〜6 個、縦樋の吐出口下の錆だれ（色 (0.9,0.6,0.45)、強度 0.5、半径 0.5）

Task 3 の layout への追加（本タスクで layout.py を修正）: 各タワーに `collapse: int`（outer は 0〜2、inner は 0〜3、`rng`）を追加し、`core_height = round(height - collapse * FLOOR_H - 0.5, 2)`。変更後に `test_sightlines_from_plaza_are_closed` が通ることを再確認する。

- [ ] **Step 1: テスト**

`tests/slum02/test_towers.py`:
```python
import math

from modeling.slum02 import geometry as g
from modeling.slum02 import towers
from modeling.slum02.layout import build_layout


def _world(a):
    return [g.transformed(p, 0.0, a.origin) for p in a.parts]


def test_every_layout_tower_built_once_across_sectors():
    data = build_layout()
    names = [a.name for s in ("towers-a", "towers-b", "towers-c") for a in towers.SECTOR_BUILDERS[s](data)]
    assert sorted(names) == sorted(t["id"] for t in data["towers"])


def test_tower_stays_near_footprint_and_height():
    data = build_layout()
    for spec in data["towers"]:
        a = towers.build_tower(spec)
        lo, hi = g.bounds(_world(a))
        cx, cz = spec["center"]
        r = math.radians(spec["rotation"])
        hw, hd = spec["footprint"][0] / 2 + 2.0, spec["footprint"][1] / 2 + 2.0
        assert cx - hw - 0.01 <= lo[0] and hi[0] <= cx + hw + 0.01, spec["id"]
        assert cz - hd - 0.01 <= lo[2] and hi[2] <= cz + hd + 0.01, spec["id"]
        assert hi[1] <= spec["height"] + 7.0 and lo[1] >= -0.05


def test_outer_tower_facades_cover_occluder():
    data = build_layout()
    occ = {o["id"]: o for o in data["occluders"]}
    for spec in [t for t in data["towers"] if t["role"] == "outer"]:
        a = towers.build_tower(spec)
        o = occ[a.meta["occludes"][0]]
        facades = [p for p in _world(a) if p.name.startswith("facade-")]
        lo, hi = g.bounds(facades)
        assert lo[0] <= o["min"][0] + 0.05 and hi[0] >= o["max"][0] - 0.05, spec["id"]
        assert lo[2] <= o["min"][2] + 0.05 and hi[2] >= o["max"][2] - 0.05, spec["id"]
        assert hi[1] >= o["max"][1] - 0.05, spec["id"]


def test_tower_detail_and_budget():
    for spec in build_layout()["towers"]:
        a = towers.build_tower(spec)
        tris = sum(g.triangle_count(p) for p in a.parts)
        mats = {p.material for p in a.parts}
        assert 3000 <= tris <= 26000, (spec["id"], tris)
        assert 5 <= len(mats) <= 13, (spec["id"], mats)
        kinds = {p.name.split("-")[0] for p in a.parts}
        assert {"facade", "fin", "slab", "pane", "ac", "drain", "roof"} <= kinds, spec["id"]


def test_windows_are_recesses_not_holes():
    a = towers.build_tower(build_layout()["towers"][4])
    for p in a.parts:
        if p.name.startswith("facade-front"):
            assert len(p.faces) > 50


def test_total_tower_budget():
    total = sum(sum(g.triangle_count(p) for p in towers.build_tower(t).parts) for t in build_layout()["towers"])
    assert total <= 300_000
```
（`towers.SECTOR_BUILDERS = {"towers-a": fn, "towers-b": fn, "towers-c": fn}` を公開する。）

- [ ] **Step 2: 失敗確認** — `uv run pytest tests/slum02/test_towers.py -q` → FAIL

- [ ] **Step 3: 実装の要点**

```python
def _local_dims(spec):
    w, d = spec["footprint"]
    return (w, d) if spec["front"] in ("+z", "-z") else (d, w)   # local X = across the front


def _window_openings(width, height, floors, rng, *, first_floor_door=False):
    bays = max(1, int(width // BAY))
    margin = (width - bays * BAY) / 2
    ops = []
    for f in range(floors):
        y0 = f * FLOOR_H + 0.9
        if y0 + 2.0 > height - 0.3:
            break
        for b in range(bays):
            if first_floor_door and f == 0 and b == bays // 2:
                continue                      # entrance bay handled by podium-entrance
            ww = rng.uniform(1.0, 1.6)
            wh = rng.uniform(1.6, 2.0)
            cx = -width / 2 + margin + BAY * (b + 0.5)
            ops.append((round(cx - ww / 2, 3), round(y0, 3), round(cx + ww / 2, 3), round(y0 + wh, 3)))
    return ops
```
ファサード 4 面は、ローカル（前面 +Z）で `wall_with_openings(closed=False)` を作り、`transformed(mesh, yaw_side, offset)` で配置した後、全体を `rotate_y(radians(spec["rotation"]))` で回す（`transformed` をもう一度適用）。`collapse > 0` の場合、上 `collapse` 階の範囲は前面・右面のファサード幅を階ごとに 25〜60% 削った別パネルにし、欠けた部分にスラブの断面（`beveled_box` 厚 0.3）と鉄筋 `tube` を出す。

- [ ] **Step 4: テスト** — `uv run pytest tests/slum02 -q` → 全 pass（layout の sightline 含む）

- [ ] **Step 5: 3 セクタのビルドとプレビュー自己レビュー**（視点: 広場から北 `{"position":[0,1.7,-8],"target":[0,14,35],"fov":75}`、南東の外周路地 `{"position":[30.5,1.7,-20],"target":[33,10,-35],"fov":70}`、近景 `{"position":[-3,2,26],"target":[0,4,33],"fov":60}`。タワーは 3 セクタを並べて見るため、preview.py に `--extra-blend`（複数可）を追加し、`bpy.ops.wm.append` で他 .blend の `Slum02*Export` コレクションを取り込めるようにする）

- [ ] **Step 6: コミット**
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/towers.py slum02/modeling/slum02/layout.py slum02/modeling/slum02/preview.py slum02/content/slum02/layout.json slum02/tests/slum02/test_towers.py slum02/artifacts/slum02/towers-*.blend slum02/artifacts/slum02/towers-*-report.json slum02/artifacts/slum02/preview
git commit -m "feat(slum02): add brutalist ruined towers with parasitic additions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: ジャンク屋台通り（market）

**Files:**
- Create: `slum02/modeling/slum02/stalls.py`
- Test: `slum02/tests/slum02/test_stalls.py`

**Interfaces:**
- Consumes: `layout.stalls / streets`、`geometry.*`
- Produces:
  - `build_stall(spec) -> Assembly`（1 軒 1 オブジェクト、名前 = spec id）: 鉄パイプ柱 4〜6 本（`steel_bare`、錆は頂点カラー）、屋根（50% `tarp_*` のたわんだ 6×4 格子面＋縁のロープ、50% `corrugated` の傾斜板＋重しのタイヤ）、カウンタ（`plywood` 天板 0.9m 高＋`plastic_crate` の脚）、背面と側面の棚 `steel_dark` 2〜3 段、商品 ≥ 12 点（基板 `electronics` の薄板、CRT モニタ＝`beveled_box` の筐体＋`glass_dark` の画面、ケーブルのコイル＝`tube` の円、義肢＝`steel_bare` の円柱の連結、バッテリー `paint_yellow_faded`、部品箱 `plastic_crate`）、吊り電球 2〜3 個（`warm_bulb` の小円柱＋電線 `tube`）、看板板（`paint_teal_faded` または `plywood`、TextRenderer の取り付け位置を `meta["sign_anchor"] = [x,y,z]` に記録）
  - `build_junk_pile(center, radius, seed) -> Assembly`（`junk-NN`）: タイヤ・筐体・ケーブル・板の山
  - `@register("market") market_assemblies(data)` — 屋台 12 ＋ ジャンク山 6

- [ ] **Step 1: テスト**

`tests/slum02/test_stalls.py`:
```python
from modeling.slum02 import geometry as g
from modeling.slum02 import stalls
from modeling.slum02.layout import build_layout


def test_market_counts():
    a = stalls.market_assemblies(build_layout())
    assert sum(1 for x in a if x.kind == "stall") == len(build_layout()["stalls"])
    assert sum(1 for x in a if x.kind == "junk-pile") == 6


def test_stall_contents_and_scale():
    for spec in build_layout()["stalls"]:
        a = stalls.build_stall(spec)
        goods = [p for p in a.parts if p.name.startswith("goods-")]
        assert len(goods) >= 12, spec["id"]
        counter = [p for p in a.parts if p.name.startswith("counter-top")]
        assert counter and abs(g.bounds(counter)[1][1] - 0.9) < 0.08
        roof_lo, roof_hi = g.bounds([p for p in a.parts if p.name.startswith("roof-")])
        assert 2.3 <= roof_hi[1] <= 3.1
        mats = {p.material for p in a.parts}
        assert "warm_bulb" in mats and "electronics" in mats
        assert "sign_anchor" in a.meta
        tris = sum(g.triangle_count(p) for p in a.parts)
        assert 1500 <= tris <= 7000, (spec["id"], tris)


def test_stalls_do_not_block_lane():
    lane = next(s for s in build_layout()["streets"] if s["kind"] == "lane")
    for spec in build_layout()["stalls"]:
        a = stalls.build_stall(spec)
        lo, hi = g.bounds([g.transformed(p, 0.0, a.origin) for p in a.parts if p.name.startswith(("post-", "counter-"))])
        inside_z = lo[2] < lane["max"][1] - 0.2 and hi[2] > lane["min"][1] + 0.2
        assert not inside_z, spec["id"]
```

- [ ] **Step 2〜4: 失敗確認 → 実装 → 成功確認**（`uv run pytest tests/slum02/test_stalls.py -q` → 3 passed）。屋根のたわみは格子点の y を `sag * (1 - (2u-1)^2) * (1 - (2v-1)^2)` で下げる（sag 0.12〜0.25）。庇（屋根の前端）は lane 側へ 0.4m 張り出してよい（柱・カウンタは lane 外）

- [ ] **Step 5: ビルドとプレビュー自己レビュー**（視点: lane 中央 `{"position":[-20,1.6,-18],"target":[5,1.5,-18],"fov":70}`、近景 `{"position":[-9.5,1.5,-17.8],"target":[-10.5,1.1,-15.5],"fov":60}`）。棚の商品が「何の店か」読めることを確認する

- [ ] **Step 6: コミット**
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/stalls.py slum02/tests/slum02/test_stalls.py slum02/artifacts/slum02/market.blend slum02/artifacts/slum02/market-report.json slum02/artifacts/slum02/preview
git commit -m "feat(slum02): add junk market stalls with readable goods

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: 風俗店（nightlife）

**Files:**
- Create: `slum02/modeling/slum02/nightlife.py`
- Test: `slum02/tests/slum02/test_nightlife.py`

**Interfaces:**
- Consumes: `layout.clubs`、`geometry.*`
- Produces:
  - `build_club(spec) -> Assembly`（1 軒 1 オブジェクト）: 2〜3 階建ての箱（`concrete_stained` / `concrete_patch` の外壁、前面は `wall_with_openings` で窓凹み）、1 階: 半開きシャッター（`corrugated_rust` の巻き上げ箱＋下がった板、下 0.8m が開いて暗い奥）、入口のビーズカーテン（幅 1.2 に 0.015 角 × 2.0m の細板 24 本、`cloth_red` と `neon_pink` を交互）、入口のネオン枠（`tube` の矩形、`spec["neon"]`）、ネオンの図形（ハート形または三日月形の `tube`、示唆的な意匠のみ）、張り紙 6〜10 枚（壁面から 0.01、0.3×0.42、`paint_*` / `tarp_*`）、赤いランプ（`neon_red` の小箱）、小さな庇と電球、上階の窓は `cloth_red` のカーテン面（凹みの奥）、室外機・配管
  - `meta["sign_anchor"]`（TextRenderer 位置）、`meta["light_anchor"]`（Point 光源位置、入口前 1.2m・高さ 2.6m）
  - `@register("nightlife") nightlife_assemblies(data)`

- [ ] **Step 1: テスト**

`tests/slum02/test_nightlife.py`:
```python
from modeling.slum02 import geometry as g
from modeling.slum02 import nightlife
from modeling.slum02.layout import build_layout


def test_club_count_and_parts():
    clubs = nightlife.nightlife_assemblies(build_layout())
    assert len(clubs) == len(build_layout()["clubs"])
    for a in clubs:
        names = {p.name.split("-")[0] for p in a.parts}
        assert {"shutter", "bead", "neonframe", "poster", "lamp"} <= names, a.name
        assert sum(1 for p in a.parts if p.name.startswith("bead-")) == 24
        mats = {p.material for p in a.parts}
        assert "cloth_red" in mats and any(m.startswith("neon_") for m in mats)
        assert {"sign_anchor", "light_anchor"} <= set(a.meta)


def test_club_height_and_budget():
    data = build_layout()
    for spec, a in zip(data["clubs"], nightlife.nightlife_assemblies(data)):
        lo, hi = g.bounds(a.parts)
        assert abs(hi[1] - spec["height"]) < 1.6
        tris = sum(g.triangle_count(p) for p in a.parts)
        assert 1500 <= tris <= 12000
```

- [ ] **Step 2〜4: 失敗確認 → 実装 → 成功確認**（→ 2 passed）

- [ ] **Step 5: ビルドとプレビュー自己レビュー**（視点: 東リング路地 `{"position":[12,1.6,-2],"target":[17.6,2.2,6.5],"fov":70}`、入口近景 `{"position":[13.5,1.6,6.5],"target":[14.6,1.6,6.5],"fov":60}`）。示唆的表現に留まっていること（露骨な図像・文字がないこと）も確認項目に加える

- [ ] **Step 6: コミット**
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/nightlife.py slum02/tests/slum02/test_nightlife.py slum02/artifacts/slum02/nightlife.blend slum02/artifacts/slum02/nightlife-report.json slum02/artifacts/slum02/preview
git commit -m "feat(slum02): add neon-lit nightlife storefronts

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: 掘っ立て小屋（shacks）

**Files:**
- Create: `slum02/modeling/slum02/shacks.py`
- Test: `slum02/tests/slum02/test_shacks.py`

**Interfaces:**
- Consumes: `layout.shacks`、`geometry.*`
- Produces:
  - `build_shack(spec) -> Assembly`（1 棟 1 オブジェクト）: `pallet_wood` の柱 4〜6 本、各壁面は 2〜4 枚の寄せ集めパネル（`corrugated` / `corrugated_rust` / `plywood` / `tarp_*` から壁ごとに選び、±3° 傾け・0.02〜0.05m ずらして重ねる）、片流れ屋根 `corrugated_rust`（勾配 6〜12°、軒の出 0.3）＋重しのタイヤ `rubber` 2〜4 本＋レンガ、扉（`plywood` 板または `tarp_*` のカーテン）、窓穴に `tarp_green` のビニール、傾いた煙突 `tube`（上に煤スプレー: 色 (0.2,0.2,0.2)、強度 0.6、半径 0.8）、室外機 50%、雨水ドラム缶、物干しロープ（`tube` カテナリー＋洗濯物の布片 3〜6 枚）
  - `@register("shacks") shacks_assemblies(data)`

- [ ] **Step 1: テスト**

`tests/slum02/test_shacks.py`:
```python
from modeling.slum02 import geometry as g
from modeling.slum02 import shacks
from modeling.slum02.layout import build_layout


def test_shack_patchwork_and_roof_slope():
    data = build_layout()
    built = shacks.shacks_assemblies(data)
    assert len(built) == len(data["shacks"])
    for a in built:
        wall_mats = {p.material for p in a.parts if p.name.startswith("panel-")}
        assert len(wall_mats) >= 3, a.name
        roof = [p for p in a.parts if p.name.startswith("roof-sheet")]
        ys = [v[1] for p in roof for v in p.vertices]
        assert max(ys) - min(ys) > 0.25, a.name
        assert any(p.name.startswith("tire-") for p in a.parts)
        assert a.meta.get("sprays"), a.name
        tris = sum(g.triangle_count(p) for p in a.parts)
        assert 700 <= tris <= 5000, (a.name, tris)


def test_shacks_are_low():
    for a in shacks.shacks_assemblies(build_layout()):
        assert g.bounds(a.parts)[1][1] <= 4.2
```

- [ ] **Step 2〜4: 失敗確認 → 実装 → 成功確認**（→ 2 passed）

- [ ] **Step 5: ビルドとプレビュー自己レビュー**（視点: 西ブロック `{"position":[-14,1.6,-4],"target":[-22,1.2,8],"fov":70}`）

- [ ] **Step 6: コミット**
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/shacks.py slum02/tests/slum02/test_shacks.py slum02/artifacts/slum02/shacks.blend slum02/artifacts/slum02/shacks-report.json slum02/artifacts/slum02/preview
git commit -m "feat(slum02): add patchwork shacks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: AR ホロ広告（ads）

**Files:**
- Create: `slum02/modeling/slum02/ads.py`
- Test: `slum02/tests/slum02/test_ads.py`

**Interfaces:**
- Consumes: `layout.ads`、`geometry.*`
- Produces:
  - `build_ad(spec) -> list[Assembly]`:
    - wall / vertical: 1 オブジェクト `ad-NN`（`steel_dark` の枠＋壁からのブラケット＋ホロ面 1 枚（両面は Fresnel の Sidedness=Double で出すので片面 1 枚）、ホロ面は枠の 0.03 手前）
    - float（anim none）: 1 オブジェクト `ad-NN`（地面から立つ細い柱 or 上空のケーブル吊り＋下部のプロジェクタ箱（`steel_dark`＋`neon_cyan` のレンズ）＋ホロ面）
    - float（anim spin）: 2 オブジェクト。`ad-NN-mount`（柱とプロジェクタ）と `ad-NN-panel`（ホロ面と薄い枠。**origin = パネル中心**、parts はパネル中心基準のローカル座標で、Spinner がこのスロットを Y 軸回転させる）
  - ホロ面の素材は `spec["material"]`（holo_*、scroll は `holo_*_scroll`）
  - kind "wall" の広告は `meta["occludes"] = [f"occ-{spec['id']}"]`（layout の occluder に対応。パネル＋枠の AABB が occluder を含むこと）
  - `@register("ads") ads_assemblies(data)`

- [ ] **Step 1: テスト**

`tests/slum02/test_ads.py`:
```python
from modeling.slum02 import geometry as g
from modeling.slum02 import ads
from modeling.slum02.layout import build_layout


def test_one_or_two_objects_per_ad():
    data = build_layout()
    built = ads.ads_assemblies(data)
    spin = [a for a in data["ads"] if a["anim"] == "spin"]
    assert len(built) == len(data["ads"]) + len(spin)


def test_spin_panel_pivot_is_panel_centre():
    data = build_layout()
    for spec in [a for a in data["ads"] if a["anim"] == "spin"]:
        panel = next(a for a in ads.build_ad(spec) if a.name == f"{spec['id']}-panel")
        assert panel.origin == tuple(spec["position"])
        lo, hi = g.bounds(panel.parts)
        assert abs((lo[0] + hi[0]) / 2) < 0.05 and abs((lo[1] + hi[1]) / 2) < 0.05


def test_holo_material_only_on_holo_faces_and_scroll_consistent():
    for spec in build_layout()["ads"]:
        for a in ads.build_ad(spec):
            holo = [p for p in a.parts if p.material.startswith("holo_")]
            if a.name.endswith("-mount"):
                assert not holo
                continue
            assert holo and all(p.material == spec["material"] for p in holo)
            if spec["anim"] == "scroll":
                assert spec["material"].endswith("_scroll")
```

- [ ] **Step 2〜4: 失敗確認 → 実装 → 成功確認**（→ 3 passed）

- [ ] **Step 5: ビルドとプレビュー自己レビュー**（視点: 広場から全周 4 方向 `{"position":[0,1.7,0],"target":[0,8,30],"fov":80}` ほか 3 方向）。Blender では Fresnel が再現できないので、ここでは配置・大きさ・密度だけを見る

- [ ] **Step 6: コミット**
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/ads.py slum02/tests/slum02/test_ads.py slum02/artifacts/slum02/ads.blend slum02/artifacts/slum02/ads-report.json slum02/artifacts/slum02/preview
git commit -m "feat(slum02): add AR holo ad panels with spin pivots

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: 頭上・仕上げ（overhead）と視線遮断の build 後検証

**Files:**
- Create: `slum02/modeling/slum02/overhead.py`
- Test: `slum02/tests/slum02/test_overhead.py`, `slum02/tests/slum02/test_occlusion_coverage.py`

**Interfaces:**
- Consumes: `layout.cables / bridges / occluders / streets / towers`、全セクタの生成関数（`sectors.sector_assemblies`）
- Produces:
  - `@register("overhead") overhead_assemblies(data)`:
    - `cables-NN`（layout の電線 1 本ごとに 3〜6 本の束。半径 0.012〜0.03、6 角、16 分割のカテナリー、たわみは ±20% ばらつき。端点に碍子・金具（小 box））
    - `bridge-NN`（渡り廊下: `steel_dark` のグレーチング床、`steel_bare` のパイプ手すり、50% に `corrugated` の屋根、垂れ下がる `tarp_*`。`meta["occludes"] = ["occ-bridge-NN"]`）
    - `hangings-NN`（路地上空の吊り布・洗濯物・吊り看板 6 組）
    - `trash-NN`（通りごとのゴミ袋 `rubber`・段ボール `plywood`・発泡箱、道路縁 8 オブジェクト）
  - `test_occlusion_coverage.py`: すべての occluder について、`meta["occludes"]` にその id を持つ Assembly（towers / overhead / ads）が存在し、その部品のワールド AABB の和集合が occluder の AABB を含む（許容 0.05m）

- [ ] **Step 1: テスト**

`tests/slum02/test_overhead.py`:
```python
import math

from modeling.slum02 import geometry as g
from modeling.slum02 import overhead
from modeling.slum02.layout import build_layout


def test_cable_endpoints_match_layout():
    data = build_layout()
    built = {a.name: a for a in overhead.overhead_assemblies(data)}
    for c in data["cables"]:
        a = built[c["id"].replace("cable", "cables")]
        pts = [v for p in a.parts if p.name.startswith("wire-") for v in g.transformed(p, 0, a.origin).vertices]
        near_a = min(math.dist(v, c["a"]) for v in pts)
        near_b = min(math.dist(v, c["b"]) for v in pts)
        assert near_a < 0.08 and near_b < 0.08, c["id"]


def test_budget():
    tris = sum(g.triangle_count(p) for a in overhead.overhead_assemblies(build_layout()) for p in a.parts)
    assert tris <= 60_000
```

`tests/slum02/test_occlusion_coverage.py`:
```python
from modeling.slum02 import geometry as g
from modeling.slum02.layout import build_layout
from modeling.slum02.sectors import SECTORS, sector_assemblies


def test_every_occluder_is_backed_by_geometry():
    data = build_layout()
    owners = {}
    for sector in SECTORS:
        for a in sector_assemblies(data, sector):
            for oid in a.meta.get("occludes", []):
                owners.setdefault(oid, []).append(a)
    for o in data["occluders"]:
        assert o["id"] in owners, o["id"]
        parts = [g.transformed(p, 0.0, a.origin) for a in owners[o["id"]] for p in a.parts]
        lo, hi = g.bounds(parts)
        assert all(lo[i] <= o["min"][i] + 0.05 for i in range(3)), o["id"]
        assert all(hi[i] >= o["max"][i] - 0.05 for i in range(3)), o["id"]
```

- [ ] **Step 2〜4: 失敗確認 → 実装 → 成功確認**（`uv run pytest tests/slum02 -q` → 全 pass）

- [ ] **Step 5: 全セクタ合成プレビュー（視線遮断の目視）**

全 11 セクタの .blend をビルド済みにしたうえで、preview.py の `--extra-blend` で全セクタを読み込み、広場中央と四隅から 8 方向 + 仰角 15° の計 12 枚を撮る:
```bash
for az in 0 45 90 135 180 225 270 315; do ...; done   # position [0,1.7,0], target = position + 30*(sin az, 0.1, cos az)
```
80×80m の外側（グリッド地面の続き、何もない地平線）が写っていないこと、遠景の塊が屋根越しに見えることを確認し、`artifacts/slum02/preview/review.md` に記録する。抜けがあれば layout の該当方向に遮蔽を足して Task 3 のテストを再実行する。

- [ ] **Step 6: コミット**
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/overhead.py slum02/tests/slum02/test_overhead.py slum02/tests/slum02/test_occlusion_coverage.py slum02/artifacts/slum02/overhead.blend slum02/artifacts/slum02/overhead-report.json slum02/artifacts/slum02/preview
git commit -m "feat(slum02): add overhead cables, bridges and occlusion coverage check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: export・統合 manifest・後処理（素材差し替え、ノイズ、ホロ、光源、駆動、コライダー、看板）

**Files:**
- Create: `slum02/modeling/slum02/postprocess.py`, `slum02/modeling/slum02/pipeline.py`
- Test: `slum02/tests/slum02/test_postprocess.py`, `slum02/tests/slum02/test_pipeline.py`
- Generated: `slum02/content/slum02/<sector>-v1/`（11 個）, `slum02/content/slum02/slum02.json`

**Interfaces:**
- Consumes: exporter の bundle（`model.apply.json`: `slot.key == "root"`、子 Slot は `object_<name>_<hash>`、コンポーネント `mesh_*`（StaticMesh）/ `renderer_*`（MeshRenderer, `Materials` はリスト）/ `mat_material_Slum02_<name>_<8hex>`（PBS_Metallic, fields `AlbedoColor/Metallic/Smoothness/EmissiveColor`）、`assets` は `{"kind": "mesh", "source": "<file>"}`）、`layout`、`materials`
- Produces:
  - `postprocess.VERTEX_COLOR_SPACE: str`（Task 4 Step 7 の実測値）
  - `postprocess.material_name(component_key) -> str | None`（`mat_material_Slum02_(.+)_[0-9a-f]{8}$`）
  - `postprocess.convert_material(component, name) -> dict`（vc/neon → `FrooxEngine.PBS_VertexColorMetallic`、holo → `FrooxEngine.FresnelMaterial`）
  - `postprocess.texture_slot() -> dict`（slot key `textures`、NoiseTexture コンポーネント key `tex-noise-<name>`）
  - `postprocess.light_slots(layout) -> list[dict]`、`collider_slots(layout) -> list[dict]`、`sign_slots(layout, spray_method) -> list[dict]`
  - `postprocess.drive_components(manifest, layout) -> None`（scroll 素材ごとに Panner2D、spin パネル Slot に Spinner）
  - `postprocess.postprocess(manifest, layout, reports) -> dict`
  - `pipeline.build_unified_manifest(content_dir) -> dict`、`pipeline.main()` → `content/slum02/slum02.json`

変換の詳細:
- vc / neon: `{"type": "FrooxEngine.PBS_VertexColorMetallic", "key": 同じ, "fields": {"AlbedoColor": 元値, "Metallic": 元値, "Smoothness": 元値, "EmissiveColor": 元値, "VertexColorTarget": "Albedo", "VertexColorInterpolationSpace": VERTEX_COLOR_SPACE, "AlphaHandling": "Opaque", "Culling": "Back", "TextureScale": list(spec.texture_scale)} }`。`spec.noise` があれば `"AlbedoTexture": f"$component:tex-noise-{spec.noise}"`
- holo: `{"type": "FrooxEngine.FresnelMaterial", "fields": {"NearColor": [e*0.35 for e in emission]+[0.25], "FarColor": [min(1, e*1.2) ...]+[0.85], "Exponent": 1.6, "GammaCurve": 1.0, "BlendMode": "Additive", "Sidedness": "Double", "ZWrite": "Off", "UseVertexColors": False, "NearTexture": "$component:tex-noise-holo", "FarTexture": "$component:tex-noise-holo", "NearTextureScale": [1.0, 4.0], "FarTextureScale": [1.0, 4.0]}}`
- NoiseTexture: `{"Size": [s, s], "Seed": seed, "Monochrome": True, "MonochromeMin": [low, low, low, 1.0], "MonochromeMax": [high, high, high, 1.0], "FilterMode": "Anisotropic", "WrapModeU": "Repeat", "WrapModeV": "Repeat", "Mipmaps": True}`
- Panner2D（scroll 素材 1 つにつき 1 個、`textures` Slot 上）: `{"_target": "$member:<holo scroll material key>.NearTextureOffset", "_speed": [0.0, 0.35], "_repeat": [1.0, 1.0]}`、FarTextureOffset 用にもう 1 個（speed [0, 0.2]）
- Spinner（spin パネルの Slot 上。Slot は exporter の子 Slot のうち `name == "ad-NN-panel"`）: `{"_target": "$slot-member:<slot key>.Rotation", "_speed": [0.0, 30.0, 0.0]}`
- Light: `{"LightType": l["type"], "Intensity": l["intensity"], "Color": l["color"], "Range": l["range"], "ShadowType": l["shadow"]}`、Spot のみ `"SpotAngle": l["spot_angle"]`。Slot の position / rotation は layout の値
- コライダー（`Type: "Static"`, `CharacterCollider: True`）: 地面 1（size [80, 0.2, 80]、position [0, 0.0, 0]）、外周・内側タワー 22（footprint × height、回転はタワーの rotation）、東の壁 1、クラブ 4、屋台カウンタ 12、小屋 12、広場の大型機械 3・車 1・柱 5。遠景には付けない
- 看板: layout の `signs` を TextRenderer（`HorizontalAlign: "Center"`, `VerticalAlign: "Middle"`）。`spray_art.method == "text-renderer"` の場合は東壁の文字を TextRenderer 2 枚（黒: Size 3.0、赤: Size 2.9、0.01 手前）で追加
- manifest のルート: `ownership.key = "slum02"`、`slot = {"key": "root", "name": "Slum02_Slum", "parent": "Root", "position": [0,0,0], "rotation": [0,0,0,1], "scale": [1,1,1]}`、`limits.expandedNodes = ceil(実測ノード数 × 1.2)`、`cameras`（overview / plaza-east-wall / market / nightlife の 4 つ）、`tests`（root・各セクタ・textures Slot の存在）
- 統合は akichi の `pipeline.py` の `_claim_key` / `_rewrite_references` / `_merge_bundle_slots` を移植し、セクタ Slot 名は `Slum02_<Title>`

- [ ] **Step 1: テスト（合成 bundle で後処理を検証）**

`tests/slum02/test_postprocess.py`:
```python
import copy

import pytest

from modeling.slum02 import postprocess as pp
from modeling.slum02.layout import build_layout


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
```

`tests/slum02/test_pipeline.py`（`tmp_path` に 2 セクタ分の最小 bundle を書き、`pipeline.build_unified_manifest` が root・セクタ Slot・assets の source パス書き換え（`<sector>-v1/<file>`）・キー衝突時の `<sector>-` 接頭辞付与を行うことを検証する。akichi の `tests/akichi/test_pipeline*.py` があれば同等のケースを移植する）:
```python
import json

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


def test_merge_renames_conflicts_and_rewrites_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SECTORS", ("ground", "plaza"))
    _bundle(tmp_path / "ground-v1", "Ground")
    _bundle(tmp_path / "plaza-v1", "Plaza")
    m = pipeline.merge_bundles(tmp_path)
    assert m["assets"]["mesh_a"]["source"] == "ground-v1/mesh_a.mesh.json"
    assert m["assets"]["plaza-mesh_a"]["source"] == "plaza-v1/mesh_a.mesh.json"
    names = [c["slot"]["name"] for c in m["children"]]
    assert names == ["Slum02_Ground", "Slum02_Plaza"]
```
（`pipeline.merge_bundles(content_dir) -> dict` は統合のみ、`build_unified_manifest` は `merge_bundles` → `postprocess` の順に呼ぶ。）

- [ ] **Step 2: 失敗確認** — `uv run pytest tests/slum02/test_postprocess.py tests/slum02/test_pipeline.py -q` → FAIL

- [ ] **Step 3: postprocess.py / pipeline.py 実装**（上記「変換の詳細」どおり。冪等性のため、既に変換済みの型は再変換しない、追加 Slot は固定キーで上書きする）

- [ ] **Step 4: テスト** → 全 pass

- [ ] **Step 5: 11 セクタを export**

```bash
for s in ground plaza towers-a towers-b towers-c market nightlife shacks ads overhead backdrop; do
  T=$(uv run python -c "print(''.join(p.capitalize() for p in '$s'.split('-')))")
  resoloop blender export artifacts/slum02/$s.blend --output content/slum02/$s-v1 --name $T --collection Slum02${T}Export --parent Root --preserve-hierarchy --json > tmp/export-$s.json || { echo "FAILED $s"; break; }
done
```
各 `content/slum02/<s>-v1/report.json` の警告を確認し、頂点カラーが全メッシュに含まれていること（`grep -L` で mesh.json に色配列がないファイルが 0 件）を確認する。

- [ ] **Step 6: 統合とオフライン検証**

```bash
uv run python -m modeling.slum02.pipeline
resoloop validate content/slum02/slum02.json --json
```
Expected: `ok: true`。エラーは内容を読んで postprocess を直す（型名・メンバー名の誤りはここで検出される）。

- [ ] **Step 7: コミット**
```bash
cd /workspaces/reso-world && git add slum02/modeling/slum02/postprocess.py slum02/modeling/slum02/pipeline.py slum02/tests/slum02/test_postprocess.py slum02/tests/slum02/test_pipeline.py slum02/content/slum02
git commit -m "feat(slum02): export sectors and build unified manifest with vertex-colour materials, holo drives and lights

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: ライブ検証と適用（駆動の実機確認 → strict validate → apply → 再 apply 収束）

**Files:**
- Create: `slum02/content/slum02/test-drives.json`（検証用の小さな manifest）
- Create: `slum02/artifacts/slum02/live-drive-check.json`, `slum02/artifacts/slum02/apply-log.md`

**Interfaces:**
- Consumes: Task 14 の `slum02.json`、Task 4 の `tmp/probe/vc-v1`
- Produces: ライブワールドの `Root/Slum02_Slum`、state `.resoloop/slum02/state/slum02.json`

長時間コマンド（apply）の監視は `monitoring-long-tasks` スキルの手順に従う（バックグラウンド実行 → 終了コード付きの終了通知を待つ。途中経過は出力ファイルを必要な範囲だけ読む）。

- [ ] **Step 1: 接続と対象確認**

```bash
resoloop doctor --url ws://localhost:53724 --json
resoloop find --name Slum02_Slum --exact --url ws://localhost:53724 --json
resoloop find --name ResoLoop_Test_Slum02 --url ws://localhost:53724 --json
```
Expected: `Slum02_Slum` は未作成（あれば中身を inspect して、この計画の所有物か確認するまで先へ進まない）。

- [ ] **Step 2: 駆動と頂点カラーの実機確認（ResoLoop_Test_Slum02Drives）**

`content/slum02/test-drives.json`: ownership key `slum02-test`、root slot `ResoLoop_Test_Slum02Drives`（parent Root、position [0, 1.5, -45]）に、(a) probe bundle のメッシュ＋`PBS_VertexColorMetallic`（Task 14 の変換結果と同じフィールド）、(b) `FresnelMaterial`＋`Panner2D`（`$member:...NearTextureOffset`）、(c) 子 Slot に `Spinner`（`$slot-member:<slot>.Rotation`）。
```bash
resoloop validate content/slum02/test-drives.json --strict --url ws://localhost:53724 --json
resoloop apply content/slum02/test-drives.json --state tmp/test-drives-state.json --url ws://localhost:53724 --json
resoloop observe '$member:test-fresnel.NearTextureOffset' --state tmp/test-drives-state.json --url ws://localhost:53724 --json   # 2 回、2 秒空けて
resoloop inspect '$slot:test-spin' --state tmp/test-drives-state.json --url ws://localhost:53724 --json                 # 2 回、rotation が変わること
```
判定を `artifacts/slum02/live-drive-check.json` に記録（offset / rotation の 2 サンプル、変化の有無、`_speed` の単位の推定）。Spinner の回転が極端（1 秒で何周も）なら `_speed` を 30 → 適切値に修正して Task 14 の postprocess に反映。駆動が効かない場合は Reflection で `_target` の書式を再確認し、それでも不可なら該当広告を静止に落として記録する。
確認後、`resoloop find --name ResoLoop_Test_Slum02Drives --exact` で ID を確認し、その ID だけを `resoloop slot delete <ID> --yes` で削除する。

- [ ] **Step 3: strict validate と diff**

```bash
resoloop validate content/slum02/slum02.json --strict --url ws://localhost:53724 --json > tmp/strict.json
resoloop diff content/slum02/slum02.json --state .resoloop/slum02/state/slum02.json --changes-only --summary --url ws://localhost:53724 --json > tmp/diff.json
```
diff は create のみであること（update / delete が出たら中身を読んで理由を確認してから進む）。

- [ ] **Step 4: apply（バックグラウンド + 監視）**

```bash
mkdir -p .resoloop/slum02/state
resoloop apply content/slum02/slum02.json --state .resoloop/slum02/state/slum02.json --ndjson-progress --url ws://localhost:53724 --json > tmp/apply.ndjson 2> tmp/apply.err
```
タイムアウト時は state を消さず、`hierarchy --under` で進捗を確認して同じコマンドを再実行する（`--command-timeout` を 1800 に引き上げ可）。

- [ ] **Step 5: 再 apply 収束と test**

```bash
resoloop apply content/slum02/slum02.json --state .resoloop/slum02/state/slum02.json --url ws://localhost:53724 --json > tmp/reapply.json
resoloop test content/slum02/slum02.json --state .resoloop/slum02/state/slum02.json --url ws://localhost:53724 --json > tmp/test.json
```
Expected: 再 apply の書き込み 0 件、test 全 pass。結果を `artifacts/slum02/apply-log.md` に記録（コマンド、所要時間、書き込み件数）。

- [ ] **Step 6: コミット**
```bash
cd /workspaces/reso-world && git add slum02/content/slum02/test-drives.json slum02/artifacts/slum02/live-drive-check.json slum02/artifacts/slum02/apply-log.md slum02/modeling/slum02/postprocess.py slum02/content/slum02/slum02.json
git commit -m "feat(slum02): verify drives live and apply slum to Resonite with convergence

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: 実機構造 QA・item audit・納品レポート

**Files:**
- Create: `slum02/artifacts/slum02/delivery-report.json`, `slum02/artifacts/slum02/qa/*.json`
- Modify: `slum02/artifacts/slum02/timing.md`

- [ ] **Step 1: 構造 QA**

```bash
U=ws://localhost:53724
for t in Light TextRenderer Spinner Panner2D PBS_VertexColorMetallic FresnelMaterial NoiseTexture BoxCollider MeshRenderer; do
  resoloop find --component $t --under '$slot:root' --state .resoloop/slum02/state/slum02.json --url $U --json > artifacts/slum02/qa/find-$t.json
done
```
個数が manifest と一致すること、`PBS_Metallic` が 0 件であること、代表 3 素材（concrete_raw / rust / holo_cyan_scroll）と代表 3 光源の値を `component inspect` で記録。

- [ ] **Step 2: 撮影を 1 回だけ試行**

```bash
resoloop capture content/slum02/slum02.json --camera overview --output artifacts/slum02/qa/capture-overview.png --capture-timeout 30 --url ws://localhost:53724 --json
```
`CAPTURE_EXPORT_TIMEOUT` なら再試行しない（akichi の裁定 R1 と同じ環境制約）。撮れた場合は Read で開いて 3 距離レビューを行う。

- [ ] **Step 3: item audit**

```bash
resoloop item audit <Slum02_Slum の ID> --url ws://localhost:53724 --json > artifacts/slum02/qa/item-audit.json
```
`externalRoleCandidates` を読み、既定シェーダ・既定フォント等のワールド標準要素だけを型単位で `--allow-external-role` に指定して再実行（`_shader` を許可する場合は理由を記録）。

- [ ] **Step 4: 納品レポート**

`artifacts/slum02/delivery-report.json` に次を記録: セクタ別・合計の triangles / vertices / objects / submeshes / materials、NoiseTexture 数とサイズ（推定メモリ）、Light 数（影あり数）、駆動コンポーネント数、コライダー数、AO ベイク結果、瓦礫の exposed_fraction、スプレー文字の方式、視線遮断レイキャスト結果（失敗 0）、プレビュー自己レビューの要約、advisory 閾値超過の根拠、**pending**（実機の見た目確認（撮影できなかった場合）、VR 歩行・コライダー接触、保存→再ロードのポータビリティ）、既知の影響（昼の空のためネオンのコントラストが弱い）。timing.md を完成させる。

- [ ] **Step 5: 全テストと最終コミット**

Run: `uv run pytest tests/slum02 -q` → 全 pass
```bash
cd /workspaces/reso-world && git add slum02/artifacts/slum02
git commit -m "docs(slum02): record live QA, item audit and delivery report

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
