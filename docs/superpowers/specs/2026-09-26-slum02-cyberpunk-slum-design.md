# slum02 サイバーパンク・スラム街（高品質版）設計仕様

日付: 2026-09-26
ブランチ: `feat/slum02-slum`
対象プロジェクト: `/workspaces/reso-world/slum02/`（resoloop プロジェクト、所有キー `slum02`、所有 root slot `Slum02_Slum`）
接続先: ResoniteLink `ws://localhost:53724/`（Resonite 2026.9.18.82 / ResoniteLink 0.13.1、doctor で疎通確認済み）

## 目的

前回の `akichi`（同要件、2026-09-25 実装済み）は見た目がチープだった。同じ要件で **見た目の品質を大きく引き上げた** スラム街を resoloop + Blender で生成し、Resonite セッションへライブ適用して収束確認まで完了させる。

## ユーザ要件

- サイバーパンク世界のスラム街
- 中心地に瓦礫が大量に転がっている空地がある（→ 大型廃工場の跡地、20×20m）
- 廃ビル、廃墟が乱雑に並んでいる
- ジャンク屋の屋台が並んでいる
- 派手な色の AR 広告がそこら中に展開されている
- 風俗店がチラホラある
- 掘っ立て小屋がある
- 広場の東側に巨大な壁が残り、赤と黒のスプレーアートで `トーキョーN◎VA` と大きく書かれている

活用スキル: `blender-modeler` / `hard-surface` / `prop-artist` / `uv-workflow` / `procedural-modeling` / `geometry-nodes`。アート方向: `sci-fi-punk-worlds`（Cyberpunk レーン）、`brutalist-mood`（建築）、`dark-gritty-mood`（経年劣化）。

## akichi がチープだった原因と今回の対策

| 原因 | 対策 |
|---|---|
| 素材がフラット色のみ（画像テクスチャ不可） | 頂点カラーへ AO・汚れ・錆だれ・摩耗を焼き込み `PBS_VertexColorMetallic` で表示。エンジン内 `NoiseTexture` を AlbedoTexture にして粒感を付与 |
| 箱プリミティブ中心、全体 5 万三角形 | 面取り・窓枠・バルコニー・室外機・配管・崩落断面などの中間ディテールを持つジェネレータに全面刷新。全体 40〜60 万三角形 |
| 光源ゼロ | ネオン・屋台・投光器に `Light` を 20〜30 灯 |
| AR 広告が不透明な発光板 | `FresnelMaterial` の半透明ホロ + `Panner2D` / `Spinner` 等の軽い動き |
| 見て直すループがない | セクタごとに小解像度 Blender Eevee プレビューで自己レビューし修正（最終確認ではなく反復用） |

## 承認済みの決定

| 項目 | 決定 |
|---|---|
| akichi との関係 | 参照可。パイプライン骨格（layout → build → export → manifest 統合 → validate/apply）は流用、ジェネレータは全面新規 |
| 規模 | 80×80m、中央広場 20×20m |
| 素材方式 | 頂点カラー + エンジン内プロシージャルテクスチャ（画像ファイル不使用） |
| AR 広告 | 半透明ホロ + 軽い動き（ProtoFlux 不要の標準駆動コンポーネント）+ 一部ネオン光源 |
| 構築方式 | アプローチ A: akichi 骨格流用 + 生成部刷新 + 素材後処理ステージ。Geometry Nodes は瓦礫・ゴミ scatter に局所採用し export 前に realize |
| 実行方針 | spec・計画承認後、このセッション内で分割タスクを最後まで実行する（途中で止めない、agent-handoff しない） |

## 前提・制約

- **画像テクスチャ不使用**: `ImportTexture2DFile` は Resonite ホスト（Windows）のパスを読むが、dev container と共有パスがない。テクスチャはエンジン内生成（`NoiseTexture` 等）のみ使う
- **実機スクリーンショット取得不可**: `resoloop capture` は Windows 側 Pictures に書き出され、コンテナから読めない（akichi で CAPTURE_EXPORT_TIMEOUT を確認済み）。見た目の反復は Blender プレビューで行い、実機の見た目確認は pending としてユーザに委ねる
- 風俗店はネオン・看板・ファサード（シャッター、ビーズカーテン、張り紙、赤い照明）までの示唆的表現とし、露骨なコンテンツは作らない
- ワールド全体の照明・スカイボックスは変更しない。夜の雰囲気は所有 root 配下のローカル光源と emissive で出す
- 後から人間がインスペクターで触りやすいように、オブジェクトごとに 1 メッシュ（建物 1 棟 = 1 メッシュ、屋台 1 軒 = 1 メッシュ など）
- 型名・メンバー名・enum 値はすべて実機 Reflection（`resoloop type describe`）で確認してから使う。推測で書かない
- Python は `uv` 経由で実行（`python3` 直接実行禁止）

### Reflection で存在確認済みの型

`PBS_VertexColorMetallic`（AlbedoTexture / TextureScale / VertexColorTarget / AlphaHandling / Metallic / Smoothness / EmissiveColor 等）、`PBS_TriplanarMetallic`、`NoiseTexture`（Size / Seed / Monochrome / MonochromeMin/Max / Bias / Gain / FilterMode / WrapModeU/V）、`GridTexture`、`FresnelMaterial`（NearColor / FarColor / Exponent / BlendMode / NearTexture / FarTexture / Sidedness / ZWrite / UseVertexColors 等）、`Panner2D`、`Spinner`、`Wiggler`、`Light`、`FogBoxVolumeMaterial`。

メンバーの値型・enum 値・駆動対象の接続方法は実装時に `type describe --member` で確定させる。

## 街の構成（80×80m、原点中心、北 = +Z）

### 中央広場 20×20m：大型廃工場の跡地（sector `plaza`）

- 床: 割れたコンクリート工場床。機械基礎台座、アンカーボルト、ピット（排水溝・機械据付穴）
- 構造残骸: H 形鋼柱数本（折損・傾斜）、落下した鋸屋根トラス断片、クレーンレール、錆びた大型機械残骸（プレス機、ベルトコンベア断片）
- 瓦礫: コンクリート塊・鉄骨片・スレート片・鉄筋を大・中・小 3 段階で GN scatter（数百個）。接地は「半分程度埋まり、上面が見える」ように沈み量を制御（akichi の 70% 埋没を回避）
- 焼けた車両 1 台、ドラム缶焚き火（暖色 `Light` 1 灯）
- 外周: 崩れた低い塀と金網フェンス、切れ目の出入口 2 か所

### 東の巨大壁とスプレーアート（sector `plaza` 内、独立メッシュ）

- 工場外壁の残骸: 幅約 20m × 高さ約 10m、付け柱と型枠目地のある brutalist コンクリート。上端は崩れてギザギザ、鉄筋が突き出る。広場の東端に立ち、背面は風俗店の路地に面する
- 広場側（西向き）の面に `トーキョーN◎VA` を文字高さ約 3m で描く
  - OFL ライセンスの極太日本語フォント（第一候補: Google Fonts「Dela Gothic One」）をプロジェクト内 `slum02/assets/fonts/` に取り込み、ライセンスファイルも同梱
  - Blender で文字をメッシュ化し、**黒の太いアウトライン層**（オフセット拡大）と **赤の塗り層** を壁面から数 mm 浮かせて重ねる
  - 文字下端から伸びる **塗料の垂れ**（細い縦ジオメトリ、先端に滴）、周囲の **オーバースプレー**（壁メッシュの頂点カラーで赤・黒のぼかし）
  - 塗料は発光させず、ライトを受ける素材にする。近くに暖色の投光器（`Light` Spot）1 灯で見せ場にする
  - フォント取得に失敗した場合は Resonite `TextRenderer` で代替（赤塗り + 黒影の 2 枚重ね）

### 周回路地（sector `ground`）

- 広場を囲むリング路地（幅 3〜5m）と四方への放射状の細い路地
- ひび割れアスファルト、水たまり（高 Smoothness の別マテリアル）、側溝、マンホール、縁石の欠け
- 外周 80m 境界は低い廃壁・フェンスで閉じる

### 廃ビル群（sector `towers-a` / `towers-b` / `towers-c`）

- 外周に 12〜16 棟、高さ 12〜40m
- brutalist の塊: 打ち放しの型枠目地、深い窓凹み、片持ちバルコニー、付け柱のベイ
- 手続き的バリエーション: 上層の崩落、窓の抜け、露出床スラブと鉄筋、焼け跡
- 寄生増築: トタンの箱、足場、屋上小屋、外付け階段、室外機の群れ、縦長のネオン看板
- 1 棟 = 1 メッシュ

### ジャンク屋台通り（sector `market`、南側路地）

- 10〜12 軒。鉄パイプフレーム + ブルーシート/トタン屋根
- 棚: 基板、モニター、ケーブル束、義肢パーツ、バッテリー、部品箱
- 裸電球・行灯の暖色（`Light` 数灯）、手書き看板（TextRenderer）

### 風俗店（sector `nightlife`、東側）

- 3〜4 軒。ピンク/紫ネオン、半開きシャッター、ビーズカーテン、張り紙、赤い照明（`Light`）

### 掘っ立て小屋（sector `shacks`、北西の空き区画と廃ビルの隙間）

- 10〜14 棟。トタン・ベニヤ・ブルーシート・パレットの寄せ集め
- 傾いた煙突、室外機、物干しロープ、ドラム缶の雨水受け

### AR 広告（sector `ads`、全域）

- 25〜35 枚。壁面大型広告、路地上空の浮遊パネル、縦長看板
- `FresnelMaterial` の半透明ホロパネル + 暗色フレーム + TextRenderer の日本語テキスト
- 色: マゼンタ / シアン / ライム / オレンジ
- 一部に `Panner2D`（テクスチャスクロール）、`Spinner`（回転）、明滅（標準駆動コンポーネントで実現できる範囲。Reflection で確認できない場合は静止に留める）

### 頭上・仕上げ（sector `overhead`）

- 路地上空を渡る電線とケーブル束（カテナリー曲線をメッシュ化、端点は壁面・柱に接地させ浮遊させない）、配管、室外機群、ゴミ袋、段ボール

## アート方向

- 主軸は Cyberpunk: 縦方向の看板密度、ケーブル、地面と高層の対比、ネオン。看板は想定視距離で読めること
- 建築骨格は brutalist: 大きな量塊、深い凹み、影の入口、細い窓、少数の素材ファミリー。型枠目地・打継ぎは構造の説明として入れ、無意味なノイズにしない
- 表面は dark-gritty: 錆は水が溜まる場所・継ぎ目・露出エッジ、窓下の雨だれ筋。油は機械・シャッター周り。煤は焚き火・排気口の上。保護面・看板は読みやすく残す。均一なノイズにしない

## アーキテクチャ

### ディレクトリ構成

```
slum02/
  pyproject.toml              # uv プロジェクト
  assets/fonts/               # OFL フォント + ライセンス
  modeling/slum02/
    layout.py                 # 決定論配置（固定シード）+ 検証 → content/slum02/layout.json
    geometry.py               # MeshData 系: 面取り付きボックス、押し出し、窓抜き、パイプ、カテナリー等
    materials.py              # 素材ファミリー定義（色・金属度・粗さ・ノイズ種別・emissive）
    vcolor.py                 # 頂点カラー焼き込み（AO + bmesh マスク）
    buildings.py              # 廃ビル・東の巨大壁
    plaza.py                  # 廃工場跡地・瓦礫 GN scatter・スプレーアート
    stalls.py / shacks.py / nightlife.py / ads.py / overhead.py
    build.py                  # セクタ指定で .blend 生成（resoloop blender run 経由）
    preview.py                # 小解像度 Eevee プレビュー（自己レビュー用）
    pipeline.py               # export bundle → 統合 manifest
    postprocess.py            # 素材差し替え・ノイズ・ホロ・光源・駆動・コライダー付与
  artifacts/slum02/           # .blend、セクタレポート、プレビュー画像、納品レポート
  content/slum02/             # セクタ bundle + 統合 manifest（slum02.json）
  tests/slum02/               # pytest
```

- 決定論性: 固定シード・安定した反復順序・安定した名前付け
- Blender 実行は `resoloop blender run modeling/slum02/build.py --arg=...`（bpy data API / bmesh / mathutils 優先）

### 素材パイプライン

1. Blender でメッシュ生成時に、大きな面をグラデーションが出る程度に分割
2. `vcolor.py` が頂点カラー（RGB = 乗算色）を焼き込む: Cycles AO ベイク（低サンプル）× 凸エッジ摩耗 × 高さ依存の足元汚れ × 窓下・開口下の雨だれ筋 × 錆だれ（鉄部）× 煤（焚き火・排気口周辺）
3. export は Principled BSDF（定数色）で行い、頂点カラーはメッシュデータとして出力される
4. `postprocess.py` が export 済み `model.apply.json` を書き換える:
   - `PBS_Metallic` → `PBS_VertexColorMetallic`（AlbedoColor / Metallic / Smoothness / Emissive を引き継ぎ、VertexColorTarget 等は Reflection で確定）
   - 素材ファミリーごとの共有 `NoiseTexture` を AlbedoTexture に割り当て、TextureScale で粒の細かさを調整
   - ホロ用マテリアルを `FresnelMaterial` に差し替え、駆動コンポーネントを追加
   - `Light` スロット、コライダーを追加
5. 後処理は純 Python で、pytest で変換結果（型、参照整合、個数）を検証する

### データフロー

1. `layout.py` → `content/slum02/layout.json` → pytest で境界・重なり・広場確保を検証
2. `resoloop blender run modeling/slum02/build.py --arg=--sector --arg=X --arg=--output --arg=artifacts/slum02/X.blend --json`
3. `preview.py` で小解像度プレビュー → 自己レビュー → 必要ならジェネレータ修正
4. `resoloop blender export artifacts/slum02/X.blend --output content/slum02/X-v1 --name X --parent VERIFIED_PARENT --json` → `report.json` 確認
5. `postprocess.py` → `pipeline.py` で統合 manifest `content/slum02/slum02.json`（root `Slum02_Slum` 配下にセクタ）
6. `validate --json` → `validate --strict --json` → `diff --changes-only --json` → `apply --state .resoloop/slum02/state/slum02.json --json` → **同一 state で再 apply し書き込みなしの収束を確認**
7. 実機で構造 QA（find / inspect で光源・ホロ・駆動・テキスト・コライダーの存在と値）、`item audit`、納品レポート

## エラー処理・安全

- Blender 実行は `--json`。失敗した bundle は不完全なので apply しない
- apply タイムアウト時は state を捨てず進捗確認 → `--command-timeout` を引き上げて再試行
- `Root`・未検証 ID・所有境界外の既存ユーザコンテンツ（akichi の `Akichi_Slum` を含む）は削除も変更もしない。削除は対象 ID を確認のうえ明示的 `--yes`
- ResoniteLink ID はセッションスコープ。再接続後は再観察し `--state` を渡す
- Reflection で確認できない機能（例: 明滅の駆動方法）は静的表現に落とし、レポートに記録する

## テスト

- pytest（`uv run pytest tests/slum02/`）:
  - layout: 全要素が 80×80m 境界内、建物 footprint の重なりなし、広場 20×20m が空いている、東の巨大壁が広場東端にある
  - 決定論: 同一シードで 2 回生成 → 同一ハッシュ
  - 後処理: PBS_Metallic が残っていない、NoiseTexture / Fresnel / Light / 駆動の参照が解決する、個数が layout と一致
  - リソース: セクタ別レポートを集計し、advisory 閾値（50k triangles / 8 materials / 16 draw sections / 2048px）超過の根拠を記録
- 見た目: セクタごとの Blender プレビュー（512〜768px）で自己レビュー。最終確認ではない
- 実機: 構造 QA（型・値・個数）。見た目の最終確認（3 距離レビュー）は撮影画像取得不可のため pending とし、ユーザの実機確認に委ねる
- FPS 計測による個別モデル判定はしない

## 予算の目安

- 全体 40〜60 万三角形、共有マテリアル 30〜40 種、Light 20〜30 灯（影あり数灯）、画像テクスチャ 0（NoiseTexture は生成テクスチャで Size を抑える）
- 閾値超過は品質上の根拠をレポートに記録する。数字合わせの削減はしない

## 実装タスク分割（承認後、同一セッションで完走）

0. スキャフォールド（uv / pyproject / ディレクトリ / Blender・resoloop 疎通 / フォント取り込み）
1. layout.py + layout.json + テスト
2. geometry / materials / 頂点カラー基盤 + プレビュー基盤
3. ground + plaza（廃工場跡地・瓦礫 GN scatter）+ 東の巨大壁とスプレーアート
4. towers（廃ビル群 3 セクタ）
5. market（屋台通り）
6. nightlife（風俗店）
7. shacks（掘っ立て小屋）
8. ads（AR ホロ広告）
9. overhead・仕上げの汚れ
10. export + 後処理（素材差し替え・ホロ・光源・駆動・コライダー）
11. manifest 統合 + strict validate + apply + 収束確認
12. 実機構造 QA・item audit・納品レポート

各担当は着手から成果提出までの所要時間と主要 Task 別の内訳を作業報告に記録する。

## 成功基準

- 全セクタが生成され、統合 manifest が strict validate を通過して apply・再 apply 収束する
- 素材が頂点カラー + ノイズで表示され、PBS_Metallic のフラット色が残っていない
- AR 広告が半透明ホロで、一部が動く。ネオン・屋台・投光器の光源が配置されている
- 東の巨大壁に `トーキョーN◎VA` の赤黒スプレーアートがある
- Blender プレビューで、akichi に比べてディテール密度・素材の変化・汚れの物語性が明確に向上している
- リソースレポートと未実施の検査（実機の見た目確認など）が納品レポートに pending として明記されている
