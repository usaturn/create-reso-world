# akichi サイバーパンク・スラム街 設計仕様

日付: 2026-09-25
ブランチ: `feat/akichi-slum`
対象プロジェクト: `/workspaces/reso-world/akichi/`（resoloop プロジェクト、所有キー `akichi`）

## 目的

resoloop + Blender パイプラインで、サイバーパンク世界のスラム街（約100×100m）を生成し、Resonite セッションへライブ適用して実機 QA まで完了させる。

## ユーザ要件

- サイバーパンク世界のスラム街
- 中心地に瓦礫が大量に転がっている空地がある
- 廃ビル、廃墟が乱雑に並んでいる
- ジャンク屋の屋台が並んでいる
- 派手な色の AR 広告がそこら中に展開されている
- 風俗店がチラホラある
- 掘っ立て小屋がある

活用スキル: `blender-modeler` / `hard-surface` / `prop-artist` / `uv-workflow` / `procedural-modeling` / `geometry-nodes`。アート方向: `sci-fi-punk-worlds`（Cyberpunk レーン）、`brutalist-mood`（建築）、`dark-gritty-mood`（経年劣化）。

## 承認済みの決定

| 項目 | 決定 |
|---|---|
| 規模 | 約100×100m の街区（大規模） |
| AR 広告 | 静的 emissive（Flux アニメーションなし） |
| 適用先 | Resonite ライブ適用 → strict validate → apply → 実機画像 QA・衝突設定まで |
| 構築方式 | セクタ分割モジュラーパイプライン（tokyo_nova 実績パターンを akichi/ に新設）。Geometry Nodes は瓦礫 scatter などに局所採用し、export 前に realize |
| 実行方針 | 設計・計画承認後、このセッション内で分割タスクを最後まで実行する（agent-handoff せず途中で止めない） |

## 前提（設計上の解釈）

- 風俗店はネオンサイン・看板・ファサード（カーテン、張り紙、怪しい照明）までの示唆的表現とし、露骨なコンテンツは作らない
- **イメージテクスチャ不使用**（tokyo_nova 実証済みの適応）: dev container から Windows の Resonite ホストと共有する検証済みマウント（/mnt/c 等）が存在せず、`ImportTexture2DFile` がパスを読めない。素材表現はフラットな Principled パラメータ（色・金属度・粗さ・emission）+ モデリングされたディテール（錆ストリーク、クラック、補修パッチのジオメトリ）で担う
- ネオン・AR 広告はフラット emissive マテリアル（定数 emission 色 + 強度）で表現。日本語テキストは Resonite ネイティブ `TextRenderer`（フォント依存回避、tokyo_nova 実績あり）。ホログラム風パネルは exporter が transparency 非対応のため、不透明 emissive + 暗色フレームで代替
- アート方向: Cyberpunk（高密度縦サイン・ケーブル・ネオン）× brutalist（コンクリートの塊感、打ちっぱし型の目地）× dark-gritty（原因のある錆・油・接触摩耗。保護面はきれいなまま残す）
- 全体ライティングはローカル資産の要求から変更しない（スキル方針）。夜景の雰囲気は emissive と素材色で表現し、ワールド照明は接続先セッションの既存設定を尊重する

## アーキテクチャ

### ディレクトリ構成

```
akichi/
  pyproject.toml             # uv プロジェクト（新規追加）
  modeling/akichi/
    layout.py                # 全区画の配置定義（固定シード、決定論的）+ 検証
    geometry.py              # MeshData プリミティブ（box / prism / cylinder 等）
    materials.py             # 共有マテリアル群 + emissive テクスチャ生成
    uv.py                    # メトリック UV 生成
    buildings.py             # 廃ビル・廃墟ジェネレータ
    props.py                 # 屋台・瓦礫・掘っ立て小屋・看板・ケーブル・小物
    build.py                 # セクタ指定 .blend 生成（resoloop blender run 経由）
    pipeline.py              # export bundle → 統合 manifest 生成
  artifacts/akichi/*.blend
  content/akichi/            # セクタ別 bundle + 統合 manifest（akichi-slum.json）
  tests/akichi/              # pytest
```

- 決定論性: 固定シード・安定した反復順序・安定した名前付け。同一シードなら同一出力
- Blender 実行は `resoloop blender run modeling/akichi/build.py --arg=...`（bpy data API / bmesh / mathutils 優先、`bpy.ops` は必要な箇所のみ）
- セクタ単位に 1 つのメッシュ原則を守る（後から人間がインスペクターで触りやすいように、オブジェクトごとに 1 メッシュ）

### セクタ構成（100×100m）

| セクタ | 内容 |
|---|---|
| `ground` | 100×100m の地面（ひび割れアスファルト/コンクリート、汚水溜まり表現）+ 外周の低い廃壁 |
| `vacant` | 中心空地 約30×40m。瓦礫大量 scatter（Geometry Nodes → realize）、鉄筋露出、コンクリートブロック、焼けた車両残骸 |
| `towers` | 廃ビル群 8〜12棟。高さ 10〜30m、brutalist マッシブ + 窓抜け・崩落床・露出鉄筋の手続き的バリエーション |
| `market` | ジャンク屋台通り。屋台 10〜15軒 + ジャンク山、emissive 行灯・看板 |
| `shacks` | 掘っ立て小屋群 8〜12棟。トタン・ベニヤの寄せ集め |
| `nightlife` | 風俗店 3〜5軒。ピンク/パープルのネオンサイン、カーテン・張り紙ファサード |
| `ads` | AR 広告。静的 emissive ホログラム風パネル・大型壁面広告を全区画に散在（半透明 + ネオンカラー） |

### マテリアル方針

- 共有マテリアルファミリー: コンクリート系バリアント、錆金属、トタン、ベニヤ、ガラス、ネオン emissive（フラット色）、ホログラム風 emissive
- 汚染は原因と位置で使い分ける（湿気が溜まる箇所の錆、可動部の油、接触部の摩耗、保護面は清潔）
- エクスポートは PBS_Metallic 変換の制約に従う（Principled BSDF、`Smoothness = 1 - Roughness`、emission は sRGB 画像 + 一定強度。非対応ノードグラフは使わず、必要ならベイク）
- ホログラム風広告は emissive + alpha の扱いに注意（exporter の transparency 制約を確認し、必要なら不透明 emissive パネル + 縁取りで代替）

## データフロー

1. `layout.py` → `layout.json`（全配置、シード固定）→ pytest で境界・重複検証
2. `resoloop blender run modeling/akichi/build.py --arg=--sector --arg=X --arg=--output --arg=artifacts/akichi/X.blend --json`
3. `resoloop blender export artifacts/akichi/X.blend --output content/akichi/X-v1 --name X --parent VERIFIED_PARENT --json` → `report.json` 確認
4. `pipeline.py` が統合 manifest `content/akichi/akichi-slum.json` を生成。所有 root slot `Akichi_Slum`（ownership key: `akichi`）配下にセクタ bundle を統合
5. `validate FILE --json` → `validate FILE --strict --json`（接続時）→ `diff FILE --changes-only --json` → `apply FILE --state .resoloop/akichi/state/akichi-slum.json --json` → **同一 state で再 apply して書き込みなしの収束を確認**
6. カメラブックマークで実機画像 QA（正面/裏面、UV 向き、シーム、スケール、マテリアル）→ コライダー設定（`resonite-build` 担当）→ `item audit` で保存・再ロード後も使える状態か確認

## エラー処理・安全

- Blender 実行は `--json` + `--python-exit-code 1`。失敗した bundle は不完全なので apply しない
- apply タイムアウト時は state を捨てず進捗確認 → `--command-timeout`（既定 900s）を引き上げて再試行
- Resonite 未検出時はユーザに起動を依頼。`resoloop discover --json` で候補 1 件なら自動接続、複数ならユーザに選択を問う
- `Root`・未検証 ID・所有境界外の既存ユーザコンテンツは削除も変更もしない。削除は対象 ID を確認のうえ明示的 `--yes`
- ResoniteLink ID はセッションスコープ。再接続後は再観察し `--state` を渡す

## テスト

- pytest（`uv run pytest tests/akichi/`）:
  - layout 検証: 全要素が 100×100m 境界内、建物 footprint の重なりなし、空地が中心に確保されている
  - 決定論: 同一シードで 2 回生成 → 同一ハッシュ
  - リソース: セクタ別レポートで advisory 閾値（50k triangles / 8 materials / 16 draw sections / 2048px）超過があれば根拠を記録
- 実機 QA: Blender レンダーは最終検証にしない。Resonite 実機画像で 3 距離（遠景シルエット / 中景構造・素材分離 / 近接エッジ・汚染）を確認
- FPS 計測による個別モデル判定はしない（セッション変数が多いため）

## 実装タスク分割（承認後、同一セッションで完走）

0. スキャフォールド（uv / pyproject / ディレクトリ / Blender・resoloop 疎通）
1. layout.py + layout.json + テスト
2. geometry / materials / uv 基盤
3. ground + vacant（瓦礫 GN scatter → realize）
4. towers（廃ビル群）
5. market（屋台通り）
6. shacks（掘っ立て小屋群）
7. nightlife + ads（風俗店・AR 広告）
8. ケーブル・汚染パス（dark-gritty 仕上げ）
9. セクタ別 export + リソースレポート
10. manifest 統合 + offline validate
11. discover + strict validate + apply + 収束確認
12. 実機 QA（カメラ）・コライダー・`item audit`・納品レポート

各担当は着手から成果提出までの所要時間を作業報告に記録する。

## 成功基準

- 7 セクタすべてが生成され、統合 manifest が strict validate を通過して apply・再 apply 収束する
- 実機画像で、空地の瓦礫・廃ビル群・屋台・ネオン広告・風俗店サイン・掘っ立て小屋が識別でき、Cyberpunk × brutalist × dark-gritty のアート方向が一貫している
- リソースレポート（triangles / 展開頂点 / マテリアル / draw sections / テクスチャメモリ概算 / 光源・駆動 Component 数）が納品レポートに記録されている
- 未実施の視覚・動作・ポータビリティ検査は pending として明示される
