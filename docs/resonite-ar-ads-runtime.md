# AR 広告を共有アトラスと時刻からの再生に移す

ワールドの AR 広告（sprite sheet を `UVAtlasAnimator` と `TimeIntDriver` で装置ごとに再生する広告）を、共有のアトラスと共通の ProtoFlux で再生する方式に移すときの手引き。slum02 の移行（2026-10-27〜28）で確かめた作り・手順・落とし穴をまとめる。
slum02 のコードはローカルの作業物（`worlds/slum02/`、Git の追跡対象外）にある。別のワールドへ移すときは、このファイルとそのコードを読み、ワールドごとの Spec・Plan を作ってから進める。

## 何が変わるか

| 項目 | 移行前（装置ごとの再生） | 移行後 |
| --- | --- | --- |
| 画像 | 装置ごとに sprite sheet の StaticTexture2D | 全装置で共有するアトラス（slum02 は 4096×1280 を 6 枚。1 枚に 4 シート×10 コマ） |
| 時刻 | 装置ごとの `TimeIntDriver` | 共通の `WorldTimeDouble` から、各ユーザがローカルに計算する（同期の書き込み・ポーリングなし） |
| 切り替え | UV を即座に切り替え | 2 枚のレイヤー（A・B）で、決めた効果で次のコマへ移る |
| 重複 | 装置ごとに独立 | 先頭 24 台は、異なる装置で同じコマ（同じ広告）を同時に見せない |

## 作り

### 部品（装置ごと、レイヤー A・B のそれぞれ）

- `UnlitMaterial`（元の material の値を写す。slum02 は Additive・ZWrite Off）
- `AssetMultiplexer<ITexture2D>`: `Assets` に共有アトラス 6 枚、`Target` は material の `Texture`、`Index` を駆動する
- `UVAtlasAnimator`: `AtlasInfo` は共有の 1 個（8×5、40 コマ）、`ScaleField`・`OffsetField` は material の `TextureScale`・`TextureOffset`、`Frame` を駆動する
- 面ごとの `MeshRenderer`（元の QuadMesh を使い回す）。両面の装置は `ValueMultiDriver<bool>` で両面の `Enabled` を駆動する
- 装置の `ValueField<int>`（DisplayID、管理された値）と `ValueField<bool>`（移行の許可。`initialFields` で false）
- 共通の controller: `UseTestClock`・`TestSeconds`・`PlaybackEnabled`（どれも `initialFields`。表示ゲートは閉じた状態で作る）

### 時刻の式（1 コマ 5 秒表示＋1 秒の切り替え）

```text
q = floor(t / 6)                    // コマの通し番号
u = t - 6*q                         // [0,6)。[0,5) は表示、[5,6) は切り替え
k = floor(q / 10)                   // シートの周期
f = q - 10*k                        // シートの中のコマ 0..9
s = (DisplayID + k) % 24            // 今のコマのシート
next = f < 9 ? (s, f + 1) : ((s + 1) % 24, 0)
p = u < 5 ? 0 : u - 5               // 切り替えの進み
curLayer = q % 2                    // A と B を交互に使う
```

- 見えているレイヤーのテクスチャ・UV は切り替えない。次のコマのレイヤーは、見えなくなった直後に次のコマへ切り替わり、見えないまま待つ。
- 先頭 24 台は各装置が別のシートの同じコマ番号を出すので、全装置が同時に切り替えても同じコマは重ならない。25 台目以降は重複を許す。
- 倍精度の `floor(t / 6)` は 6q のすぐ下で q − 1 になり、`u` は [0,6) を外れない（確かめ済み）。Python の式と ProtoGraph は同じ演算順・型にする。

### 効果（装置ごとに 1 つ。対応表の `mode`）

| 効果 | 見え方 | 作り |
| --- | --- | --- |
| crossfade | 2 枚が重なりながら入れ替わる | cur の Alpha = 1 − p、next = p |
| neon-wipe | 境界がシアンの走査線とともに横切る（コマごとに左右が交互） | 共用のマスク 2 枚（右半分・左半分が白）を `MaskTexture` に固定し、`MaskOffset` を駆動。走査線は共用の細線テクスチャを別の material の `TextureOffset` で動かす |
| dissolve | 斑模様に溶けて次の広告が現れる | 共用のノイズ 2 枚（n と 1 − n）を `MaskMode: AlphaClip` のマスクにし、cur の `AlphaCutoff` = p、next = 1 − p |
| glitch | 1/6 秒ごとに今と次を入れ替え、淡い色を付ける | 整数の擬似乱数（段・DisplayID・q から計算）。slum02 では「汚い」との評価で使わないことにした |

- どの効果も、広告の UV をセルの外へずらさない（隣の広告が見えるため、スライドやズームは採れない）。
- 効果用の画像は全装置で共有する 1 組だけ。装置ごとの画像は作らない。

### ProtoGraph

- `ARState.pg`（手書き）: `DisplayID`・`TimeSeconds`・`Mode` から、A・B の atlas・frame・Tint・Visible と、効果の値（MaskOffset、AlphaCutoff、走査線）を出す。`Pack_Float2`・`Pack_ColorX`・`Floor_Double`・`FloorToInt_Double` を使う。
- `ARAds.pg`（生成）: 装置ごとに `ARState` を呼び、出力を native の member へ drive で bind する。効果は生成時の定数として `Mode` に渡す。Visible には `PlaybackEnabled` と装置の移行許可のゲートを掛ける。
- 28 装置で 337 binding、約 6,000 ノード。module の配備先は controller の Slot。

## ResoLoop と Resonite の落とし穴

- **駆動される参照を宣言しない。** material の `Texture` は mux が書き換えるので、`fields`・`initialFields` に書くと state の識別条件に入り、切り替え後に Component を解決できず、再 apply が material を複製して失敗する（create-reso-world #287、usaturn/resoloop#25）。駆動する値（`TintColor`・`MaskOffset`・`AlphaCutoff`・`Frame`・`Index`）は `initialFields` に書く。
- **効果を変えたときに設定が残る。** ResoLoop は宣言した member だけを書くので、宣言から外した `MaskTexture` などは world に残る。どの効果でも `MaskTexture`（null かマスク）と `MaskMode` を宣言し、dissolve 以外は `AlphaCutoff` を既定値 0.5 で宣言する。neon-wipe をやめる装置は、走査線の部品の削除を prune する。
- **マスクは RGB×A で読まれる。** RGB と A の両方に値を入れたノイズでは、dissolve の途中が 4〜6 割抜けた。RGB は白にして A だけに値を入れ、`Uncompressed: true`・`PreferredProfile: Linear` にする。マスクはメッシュの UV で読まれ、Additive でも明るさに効く（neon-wipe・dissolve とも実機で確認）。
- **`MaskTextureMode` の値は `MultiplyAlpha`・`AlphaClip`。** Reflection の型の問い合わせ（`resoloop type query`）で enum の値を確かめる。キャッシュに無いことがある。
- **`flux deploy-manifest` に `--library-path` は無い。** DLL は `RESONITE_MANAGED_DATA_PATH=<managed data> resoloop flux deploy-manifest ...` のようにコマンドだけに付ける。付けないとビルドで止まる（ワールドは変わらない）。
- **ResoLoop は ObjectRoot の Slot に `AI_GeneratedContent` を付ける。** diff の作成の数が宣言より多いのはこのため。
- **旧表示の renderer は宣言に `Enabled` を持たない。** 段階の切り替えは、旧 renderer の `Enabled` を `component set` で false にしてから、装置の移行許可を true にする（apply で戻らない）。全件の確認後に、旧表示の部品を宣言から外して prune する。
- **再生成で旧表示を復活させない。** 生成経路（slum02 は `postprocess` → `extend_configured_manifest`）が config を読むので、退役した装置の旧部品を宣言から外す処理を生成側に入れる（slum02 は config の `retired_keys`）。テストは本番の config を読まないよう、`conftest.py` で空の config に差し替える。
- **observe は Component をまたいで不可分ではない。** 1 回の observe に数秒かかり、全装置が 6 秒ごとに同時に切り替わるので、通常の時計での読み取りは「alpha 0 なのに可視」などに見えることがある。正しさは凍結時刻（`UseTestClock`・`TestSeconds`）の標本で確かめる。
- **撮影の `--frame` は UIX の Canvas 用。** 広告の撮影は、面の中心と向きから計算したカメラの bookmark を capture の JSON に書く。一時カメラ `ResoLoop_Test_Capture_*` が残っていないことを `resoloop find` で確かめる。

## 進め方

1. **調べる。** 対象の装置（生成元・material・面・旧画像・共有の参照）を一覧にし、除外（入口の専用再生など）を決める。DisplayID を採番して対応表に記録する。
2. **Spec・Plan。** 方式、時刻の式、排他、効果の割り当て、受け入れ基準・防御範囲・動作環境を決める。効果は撮影で決めることが多いので、色・段数などは初期値として扱う。
3. **ローカルの実装（TDD）。** アトラスと効果用の画像、native の部品、ProtoGraph、凍結時刻の観測を期待値と比べる verifier。テストは「壊れてもエラーにならない損害」を防ぐものだけにする（リポジトリの「テストの採用基準」）。
4. **試作。** 所有ルートの下の `ResoLoop_Test_*` に 1 装置 → 全装置を作り、どの変更の前にも新しい diff を審査する。apply → 同じ apply の書き込み 0 → Flux の配備 → 配備後の diff 0 → binding の全件照合。凍結時刻の標本（コマ・シートの境界の前後、切り替えの途中、大きな前進・後退）で verifier と排他を確かめ、効果を撮影する。
5. **本番。** 閉じたゲートで準備（apply・配備）→ 1 装置 → 先頭 24 → 残りの順に切り替え → 旧表示の部品を prune → 同じ apply の書き込み 0。変更前の宣言・state・配備 state を控えておく。
6. **受け入れ。** 保存→再読み込み、途中参加、複数ユーザ、低 FPS、性能（VRAM・描画・読み込み）。利用者の協力が要るものはまとめて頼む。

効果を後から変えるときは、対応表を変える → 候補を作る → diff を審査 → apply → 直後に Flux を配備 → 配備後に diff と同じ apply、の順にする（旧 Flux が駆動していた member への書き込みが 1 回出ることがある）。

## slum02 の実装（参照先）

- `worlds/slum02/modeling/slum02/`: `ar_atlas.py`（アトラス）、`ar_effects.py`（効果用の画像）、`ar_migration.py`（対応表・在庫の照合）、`ar_runtime.py`（native の部品・ProtoGraph の生成・退役）、`ar_schedule.py`（時刻の式・監査）、`ar_runtime_verify.py`（凍結時刻の照合）
- `worlds/slum02/flux/ARState.pg`、`ARAds.pg`、`ar-ads.flux.json`
- `worlds/slum02/content/slum02/ar-ads-displays-v1.json`（対応表）、`ar-runtime-v1.json`（config）、`ar-atlas-v1/`、`ar-effects-v1/`
- `worlds/slum02/tests/slum02/test_ar_*.py`、`conftest.py`
- 試作と本番の手順のスクリプト（収集・排他・切り替え・撮影のカメラ）: `tmp/agents/slum02-ar-rev1.*/scripts/`（ローカルの作業記録。消える場合がある）
