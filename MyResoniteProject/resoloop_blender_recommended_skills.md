# ResoLoop + Blender 向け推奨 Skill 選定ガイド

調査時点: 2026-09-24

## 1. 目的

本ドキュメントは、`resoloop` を使ってコーディングエージェントから Blender を操作し、最終的に Resonite 内へ 3D モデルやワールド要素を構築する環境を対象に、`arjun988/blender-skills` などの Blender 向け Skill から **ResoLoop 標準 Skill と重複しないものだけを選別し、導入候補を整理する**ことを目的とする。

対象:

- ResoLoop: <https://github.com/orange3134/resoloop>
- ResoLoop 詳細資料: <https://github.com/orange3134/resoloop/blob/main/README-DETAILS.md>
- Blender Skills: <https://github.com/arjun988/blender-skills>
- Blender Skills Guide: <https://github.com/arjun988/blender-skills/blob/main/SKILLS_GUIDE.md>

## 2. 前提

ResoLoop の現行構成では、以下の Skill が標準で同梱されている。

- `resonite-build`
- `resonite-blender`
- `resonite-inspect`
- `resonite-debug`
- `resonite-flux`
- `resonite-uix`

特に 3D モデル制作では、`resonite-build` と `resonite-blender` が広い範囲を担当する。

`resonite-build` は、Resonite ワールド全体について次を担当する。

- ワールドや環境の blockout
- 空間構成と sightline の確認
- 開口部・動線・traversable space の確認
- collider の確認
- Resonite 上での capture / test
- apply / diff / state 管理
- native Resonite と Blender の使い分け

`resonite-blender` は、Blender を利用した静的 3D モデル制作について次を担当する。

- Blender の検出と `resoloop blender run`
- 再現可能な `model.py` と `.blend` の管理
- silhouette / construction detail / focal detail の品質基準
- 近景・中景・遠景の 3 段階レビュー
- UV / normal / tangent / hard edge の扱い
- Principled BSDF から Resonite `PBS_Metallic` への変換
- sRGB / Linear / Normal Map の扱い
- `--pack-pbr`
- Geometry Nodes / instance の static mesh 化方針
- hierarchy / pivot の保持
- Blender → Resonite export
- triangle / expanded vertices / material / draw section / texture memory 等の資源レビュー
- Resonite 実機 capture による visual QA
- validate / diff / apply / reapply の検証

したがって、追加する Blender Skill は **「Blender でどのように形を作るか」という専門造形知識へ限定する**べきである。

---

# 3. 基本導入を推奨する Skill

## 3.1 `blender-modeler`

**推奨度: 最優先**

### 導入すべき理由

Blender の基本的なモデリング技法をまとめた Skill であり、ResoLoop 側では具体的な Blender 造形手法までは詳細に規定していない。

主に次の知識が有用である。

- primitive を使った blockout
- modifier stack の設計
- Mirror / Array / Solidify / Boolean / Bevel 等の使い分け
- scene / collection の整理
- real-world scale
- pivot / origin
- normal / manifold / loose geometry の cleanup
- repeated geometry の instance 化

`resoloop blender run` で実行する Python を生成する際の基礎 Skill として使える。

### 導入時の注意事項

元 Skill の `MCP-first` や `via MCP` の指示は削除する。

代わりに、次を共通ルールとして追加する。

```text
Blender の変更は再現可能な Python ソースとして保存する。
実行は resoloop blender run を使用する。
可能な限り bpy の data API / bmesh / mathutils を優先し、
context 依存の bpy.ops は必要な場合だけ使用する。
```

また、ResoLoop exporter は評価済み modifier を扱えるため、制作途中で modifier を早期に destructive apply しない。

---

## 3.2 `hard-surface`

**推奨度: 最優先**

### 導入すべき理由

Resonite ワールドでは、次のような hard-surface asset を作成する機会が多い。

- 工業設備
- 配管
- 換気設備
- 機械
- 武器
- 車両
- エレベーター
- ドア
- コンソール
- SF 機器

この Skill が持つ以下の専門知識は `resonite-blender` とほぼ重複しない。

- primary / secondary / tertiary form の階層
- manufacturing logic
- panel break
- boolean cutter の管理
- bevel 幅の考え方
- greeble の配置
- mechanical readability
- functional seam の考え方

### 導入時の注意事項

以下は削除または修正する。

- Blender MCP 固有の操作手順
- Unreal / Unity を前提とした export 記述
- 固定的な polygon budget の強制

ResoLoop では polycount の固定上限より、見た目・視距離・同時配置数・expanded vertices・draw sections 等を総合的に評価する。

また、最終的に Resonite で動かす必要がある部品は `--preserve-hierarchy` と pivot 設計を考慮する。

---

## 3.3 `prop-artist`

**推奨度: 最優先**

### 導入すべき理由

ワールドの完成度を上げる大量の小物制作に向いている。

例:

- 木箱
- パレット
- ドラム缶
- 棚
- 工具
- 家具
- ケース
- 電子機器
- 雑貨
- 生活用品
- 工業用小物

特に有用な知識は以下である。

- real-world scale
- silhouette readability
- hero / standard / background の asset tier
- pivot の役割
- kitbash 用部品の設計
- mundane object を過剰に sci-fi 化しない判断

### 導入時の注意事項

元 Skill に含まれる triangle 数は参考値に留め、強制ルールにしない。

ResoLoop の `resonite-blender` は固定 budget よりも、実際の役割・視距離・同時配置数を重視するため、こちらを優先する。

collision の最終実装も Blender 側で完結させず、必要に応じて `resonite-build` で native Resonite Collider を構成する。

---

## 3.4 `uv-workflow`

**推奨度: 高**

### 導入すべき理由

`resonite-blender` は UV の export / preservation / tangent への影響を規定しているが、**UV をどう作るか**という制作技法自体は専門 Skill として分離する価値がある。

有用な内容:

- seam placement
- manual unwrap
- texel density
- UV packing
- modular atlas
- hard-surface の construction seam と UV seam の一致
- intentional overlap の管理

### 導入時の注意事項

以下は Resonite 用途では優先度が低いため削除または optional 扱いにする。

- Unity / Unreal lightmap UV 前提
- UDIM を標準手法とする記述
- engine 固有 UV 制約

ResoLoop exporter は render-active UV を UV0 として扱い、追加 UV も保持するため、その仕様を優先する。

---

## 3.5 `procedural-modeling`

**推奨度: 高**

### 導入すべき理由

大規模な Resonite ワールド制作で特に有用である。

適用例:

- 配管
- ケーブル
- 道路
- 壁
- 建物
- ダクト
- 岩
- sci-fi panel
- repeating structure
- modular structure

パラメータと seed を持つ再生成可能なモデルを作りやすく、`resoloop blender run` の「Python を Git 管理して再生成する」方式と非常に相性がよい。

### 導入時の注意事項

最終出力は procedural system のままにしない。

ResoLoop の static exporter に渡す前に、必要に応じて以下を実施する。

```text
procedural system
→ evaluate
→ realize / bake
→ explicit static mesh
→ resoloop blender export
```

random を使用する場合は必ず seed を固定し、再生成可能性を維持する。

---

## 3.6 `geometry-nodes`

**推奨度: 高**

### 導入すべき理由

Geometry Nodes は次の作業を効率化できる。

- object scatter
- pipes / cables
- modular repetition
- vegetation placement
- parametric wall
- rock variation
- building variation

複数の `bpy` object を逐次作成するより効率的なケースも多い。

### 導入時の注意事項

ResoLoop の Blender exporter は **Geometry Nodes や instance をそのまま Resonite へ転送しない**。

したがって、この Skill は runtime 技術ではなく **Blender 制作時の authoring 技術**として使う。

最終 export 前に、対象 geometry を明示的に static mesh 化する。

```text
Geometry Nodes
→ Realize Instances
→ evaluated geometry
→ static mesh copy
→ export
```

元の Geometry Nodes 構成は editable source として `.blend` に残す。

---

# 4. 条件付きで導入を推奨する Skill

## 4.1 `retopology`

**推奨度: 条件付きで高**

### 導入すべき理由

次の入力を扱う場合に有効である。

- AI 生成 3D model
- sculpt mesh
- photogrammetry
- scan data
- 非常に重い mesh
- topology が壊れた外部 asset

主目的は animation-ready quad mesh を作ることではなく、Resonite 向け static asset として扱いやすい geometry へ整理することに置き換える。

### 導入時の注意事項

character animation 前提の edge loop 規則は、static asset では不要な場合が多い。

次を中心に残す。

- silhouette preservation
- poly reduction
- non-manifold cleanup
- scan / AI mesh cleanup
- UV を作りやすい topology

すべての static mesh を quad 化するような運用は避ける。

---

## 4.2 `sculpting`

**推奨度: 条件付き**

### 導入すべき理由

次のような hero asset では利用価値がある。

- 岩
- 生物的形状
- 破損表現
- 凹み
- 摩耗
- 有機的な surface
- 高密度 detail の bake source

### 導入時の注意事項

high-poly sculpt をそのまま Resonite へ出力することを標準にしない。

原則として、用途に応じて次へ収束させる。

```text
sculpt source
→ retopology または optimized static mesh
→ normal / texture bake
→ Resonite 用 asset
```

背景 asset や低視距離 asset に sculpt を濫用しない。

---

# 5. Style / Mood 系 Skill

Style / Mood 系は Blender の実行方法ではなく **Art Direction** を提供するため、ResoLoop 標準 Skill と競合しにくい。

プロジェクトに必要なものだけ選択的に導入する。

## 推奨候補

### `horror-style`

用途:

- ホラー環境
- 工業的・廃墟的空間
- limited visibility
- sparse detail
- environmental storytelling

注意:

Skill 内の Blender lighting / volumetric 表現をそのまま最終成果物とみなさない。最終 lighting は Resonite 上で確認・調整する。

### `lowpoly-style`

用途:

- PS1 / PS2 系
- Lethal Company 系
- 軽量 stylized world
- silhouette 優先の asset

注意:

元 Skill の固定 triangle budget は参考値として扱い、ResoLoop の resource review を優先する。

### `realistic-style`

用途:

- 写実的 asset
- real-world scale
- PBR material
- scan cleanup

注意:

Skill 内の ORM / engine export 規則を削除し、Material の最終仕様は `resonite-blender` に従う。

### `dark-gritty-mood`

用途:

- rust
- decay
- industrial
- abandoned
- melancholic / tense environment

実行方式への依存が少ないため導入しやすい。

### `brutalist-mood`

用途:

- raw concrete
- monumental architecture
- austere environment
- 地下施設
- institutional interior

### `liminal-space-style`

用途:

- Backrooms 系
- empty mall
- 廊下
- 不自然な反復空間
- uncanny environment

### `sci-fi-punk-worlds`

用途:

- cyberpunk
- steampunk
- dieselpunk
- hard sci-fi
- space opera
- solarpunk 等

注意:

複数 style を無秩序に混ぜないための Art Direction として使用する。

---

# 6. Skill としては導入せず、Reference だけ取り込む候補

## 6.1 `environment-artist`

Skill 全体は導入しない。

理由:

- blockout
- composition
- focal area
- sightline
- environment QA
- optimization

の多くが `resonite-build` / `resonite-blender` と重複する。

ただし以下の知識は有用なので、reference として取り込む価値がある。

- modular kit の分類
- grid size の考え方
- corner / edge / fill / trim / opening の設計
- architecture module の規格化

推奨:

```text
references/modular-environment-design.md
```

のような ResoLoop 向け reference に再構成する。

---

## 6.2 `set-dressing`

Skill 全体は導入しない。

理由:

ResoLoop 側ですでに blockout 後の visual composition / focal area / prop 配置 / concept comparison を扱っているため。

ただし以下は有用。

- narrative cluster
- prop density
- negative space
- traversal path を塞がない配置

推奨:

```text
references/set-dressing-patterns.md
```

として `resonite-build` または Blender 造形 Skill から参照する。

---

## 6.3 `texture-workflow`

Skill 全体は導入しない。

理由:

Material / texture の target-engine-specific な部分が `resonite-blender` と重複し、特に ORM packing などは Resonite と仕様が異なる。

ただし以下は reference として有用。

- high-poly → normal bake
- cage
- AO / curvature bake
- atlas
- texture margin

Resonite の channel packing ルールを混在させないように、bake 技術だけ抽出する。

---

# 7. 導入しない方がよい Skill

以下は ResoLoop 標準 Skill と責務が重なるか、static Blender → Resonite workflow と相性が悪いため、原則導入しない。

| Skill | 除外理由 |
|---|---|
| `blender-director` | `resonite-build` + `resonite-blender` が上位 orchestration を担当済み |
| `scene-assembly` | world layout / blockout / composition が `resonite-build` と重複 |
| `environment-artist` | Skill 全体では重複が多い。modular kit 知識のみ reference 化 |
| `set-dressing` | `resonite-build` と重複。placement pattern のみ reference 化 |
| `materials` | Principled → PBS_Metallic、PBR packing 等を `resonite-blender` が定義済み |
| `texture-workflow` | target-engine-specific texture rule が衝突。bake 技術のみ reference 化 |
| `asset-optimization` | `resonite-blender` が Resonite 向け resource review を既に担当 |
| `qa-review` | validate / diff / apply / capture / reapply が ResoLoop に存在 |
| `lookdev` | 最終見た目は Resonite capture で確認すべき |
| `collision-proxy` | native Resonite Collider と `resonite-build` を優先 |
| `lod-pipeline` | 一律 LOD を要求せず、ResoLoop の実用途ベース最適化を優先 |
| `export-pipeline` | `resoloop blender export` が専用 export pipeline |
| `unity-export` | 不要 |
| `unreal-export` | 不要 |
| `godot-export` | 不要 |
| `rendering` | Blender final render は成果物ではない |
| `compositing` | 最終成果物が Resonite のため通常不要 |
| `camera-cinematography` | 最終 visual QA は Resonite capture を使用 |
| `rigging` | static exporter の対象外 |
| `animation` | static exporter の対象外 |
| `hair-groom` | static workflow では優先度が低い |
| `cloth-sim` | runtime asset として直接移植しにくい |
| `vfx-fx` | Blender VFX をそのまま Resonite へ移植できない |
| `physics-sim` | runtime physics は Resonite 側で設計する方が適切 |

---

# 8. 導入時の共通修正方針

## 8.1 Blender MCP 依存を完全に除去する

`blender-skills` の元 Skill には次の表現が多い。

```text
via MCP
MCP-first
execute via Blender MCP
get_viewport_screenshot
```

これらを ResoLoop 向けに置換する。

推奨共通ルール:

```text
Blender 操作は MCP に依存しない。

すべての変更は再現可能な Python ソースとして project 内に保存する。
Blender 実行には resoloop blender run を使用する。

新規作成:
resoloop blender run modeling/model.py --arg=artifacts/model.blend --json

既存 .blend の修正:
resoloop blender run modeling/adjust.py --blend artifacts/model.blend --arg=artifacts/model-v2.blend --json

Python では可能な限り bpy data API、bmesh、mathutils を優先する。
context に依存する bpy.ops は必要な場合に限定する。
```

---

## 8.2 Export / QA は `resonite-blender` へ渡す

追加 Skill は Blender model の制作までを担当し、その後は必ず ResoLoop 標準 workflow に戻す。

```text
Blender specialist Skill
        ↓
model.py
        ↓
resoloop blender run
        ↓
.blend
        ↓
resonite-blender
        ↓
resoloop blender export
        ↓
validate --strict
        ↓
diff
        ↓
apply
        ↓
Resonite capture
```

追加 Skill 独自の FBX / GLTF / Unreal / Unity export を行わない。

---

## 8.3 ResoLoop の resource policy を優先する

外部 Skill に次のような固定 budget が含まれていても、ResoLoop の方針を優先する。

- hero prop は必ず X tris 以下
- material は X 個以下
- texture は最大 2K
- hero asset は必ず LOD0〜LOD3

ResoLoop では次を考慮する。

- visual quality
- viewing distance
- simultaneous instance count
- triangle count
- expanded vertex count
- mesh count
- material count
- draw sections
- texture dimensions
- texture memory with mipmaps
- alpha overdraw
- collider complexity
- shadows

固定値は「レビュー開始の目安」としてのみ使用する。

---

## 8.4 Material rule は `resonite-blender` を唯一の基準にする

Material / texture に関するルールは追加 Skill 側で独自定義しない。

特に以下を混在させない。

- glTF ORM
- Unreal ORM
- Unity Mask Map
- Resonite PBS_Metallic packing

ResoLoop の `--pack-pbr` や Reflection で確認した Resonite material member を優先する。

---

## 8.5 Geometry Nodes / instance は authoring 専用とする

Geometry Nodes や instance は制作効率向上のために使ってよいが、最終 export の仕様ではない。

```text
editable procedural source
        ↓
realize / static conversion
        ↓
export collection
        ↓
resoloop blender export
```

元 `.blend` には editable source を残す。

---

## 8.6 最終 visual QA は Resonite で行う

Blender 上で正しく見えても、Resonite では次が変わる可能性がある。

- material
- smoothness
- normal map
- UV
- scale
- hierarchy
- texture color profile

そのため Blender render を最終合否判定にしない。

ResoLoop の capture / inspect を使って最終確認する。

---

# 9. 推奨ディレクトリ構成

```text
.agents/skills/
│
│  # ResoLoop 標準 — 変更しない
├── resonite-build/
├── resonite-blender/
├── resonite-inspect/
├── resonite-debug/
├── resonite-flux/
├── resonite-uix/
│
│  # Blender 造形 Skill
├── blender-modeler/
├── hard-surface/
├── prop-artist/
├── uv-workflow/
├── procedural-modeling/
├── geometry-nodes/
│
│  # Optional
├── retopology/
├── sculpting/
│
│  # Art Direction — 必要なものだけ
├── horror-style/
├── lowpoly-style/
├── realistic-style/
├── dark-gritty-mood/
├── brutalist-mood/
├── liminal-space-style/
├── sci-fi-punk-worlds/
│
└── references/
    ├── modular-environment-design.md
    ├── set-dressing-patterns.md
    ├── texture-baking.md
    ├── reference-image-match.md
    └── reference-analysis-template.md
```

## 注意

ResoLoop の bundled Skill は `resoloop skills sync` の管理対象であり、利用者による編集がある場合は conflict として保護される。

そのため、外部 Skill の内容を `resonite-blender/SKILL.md` へ直接追記するより、**独立 Skill / reference として追加し、ResoLoop bundled Skill を改変しない**運用が望ましい。

---

# 10. 推奨 Skill セット

## 最小構成

まず導入するなら以下の 6 Skill で十分である。

```text
blender-modeler
hard-surface
prop-artist
uv-workflow
procedural-modeling
geometry-nodes
```

この構成だけでも、Resonite の一般的な static 3D asset / environment 制作をかなり補強できる。

## 拡張構成

外部 asset、AI 生成 mesh、高密度造形も扱う場合は追加する。

```text
retopology
sculpting
```

## Art Direction

作品ごとに必要なものだけ追加する。

例: ホラー地下施設

```text
horror-style
dark-gritty-mood
brutalist-mood
```

例: SF スラム / 工業都市

```text
sci-fi-punk-worlds
dark-gritty-mood
hard-surface
```

例: PS1 系ホラー

```text
horror-style
lowpoly-style
liminal-space-style
```

---

# 11. 最終的な責務分担

```text
User request
    │
    ▼
resonite-build
    │
    ├── native Resonite が適切
    │       └── Resonite Slot / Component / Flux
    │
    └── Blender が適切
            │
            ▼
      resonite-blender
            │
            ├── blender-modeler
            ├── hard-surface
            ├── prop-artist
            ├── uv-workflow
            ├── procedural-modeling
            ├── geometry-nodes
            ├── retopology [optional]
            ├── sculpting [optional]
            └── style / mood [optional]
                    │
                    ▼
                 model.py
                    │
                    ▼
          resoloop blender run
                    │
                    ▼
                  .blend
                    │
                    ▼
          resonite-blender export
                    │
                    ▼
          validate / diff / apply
                    │
                    ▼
                 Resonite
                    │
                    ▼
          capture / inspect / test
```

役割を一言で整理すると、次のようになる。

- **`resonite-build`**: 全体 Director
- **`resonite-blender`**: Blender ↔ Resonite Technical Director
- **追加 Blender Skill**: 造形の専門家
- **Style / Mood Skill**: Art Director
- **Resonite capture**: 最終 visual QA

この責務分担を崩さないことが、Skill の重複・矛盾・誤った engine-specific rule の混入を防ぐ上で最も重要である。

---

# 12. 参照

- ResoLoop README: <https://github.com/orange3134/resoloop>
- ResoLoop 詳細資料: <https://github.com/orange3134/resoloop/blob/main/README-DETAILS.md>
- `resonite-build`: <https://github.com/orange3134/resoloop/blob/main/skills/codex/resonite-build/SKILL.md>
- `resonite-blender`: <https://github.com/orange3134/resoloop/blob/main/skills/codex/resonite-blender/SKILL.md>
- Blender workflow: <https://github.com/orange3134/resoloop/blob/main/docs/BLENDER.md>
- Blender Skills: <https://github.com/arjun988/blender-skills>
- Blender Skills Guide: <https://github.com/arjun988/blender-skills/blob/main/SKILLS_GUIDE.md>
