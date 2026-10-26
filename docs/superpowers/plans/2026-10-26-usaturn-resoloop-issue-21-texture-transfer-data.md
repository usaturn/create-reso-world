# usaturn/resoloop#21 画素データでテクスチャを送る取り込み Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `--texture-transfer data` で、CLI が画像を復号して画素を `ImportTexture2DRawData` で送り、Resonite からパスを読めない構成でも新規テクスチャを apply できるようにする。

**Architecture:** 設定 `textureTransfer` を既存の ConfigResolver に足し、CLI が WorldService に渡す。復号は RLoop.Core の `TextureDecoder`（StbImageSharp）が行い、画素は Core の型 `TexturePixels` で `IResoniteClient.ImportTexturePixelsAsync` に渡す。adapter がそれを `ImportTexture2DRawData` に詰める。plan の準備（`BuildAssetPlans`）で画像のヘッダーを確かめ、復号できなければワールドを変える前に止める。

**Tech Stack:** C#（.NET 10、`global.json` の SDK 10.0.201）、xUnit、YellowDogMan.ResoniteLink 0.13.1、StbImageSharp 2.30.16

**Spec:** `docs/superpowers/specs/2026-10-26-usaturn-resoloop-issue-21-texture-transfer-data-design.md`（usaturn/create-reso-world の branch `docs/resoloop-issue-21-texture-transfer-data`、`700fea7`）

**状態:** draft（Spec と同じ。実行許可は Spec の「実行許可」）

**作業場所:**
- コード: `/workspaces/reso-world/external/resoloop/.worktrees/issue-21-texture-transfer-data`（branch `feat/issue-21-texture-transfer-data`、base `4077350`）
- 文書: `/workspaces/reso-world/.worktrees/resoloop-issue-21-texture-transfer-data`（branch `docs/resoloop-issue-21-texture-transfer-data`）
- セッション: `/workspaces/reso-world/tmp/agents/issue-21.paqvzxic/`（実行予算の `budget.jsonl`、作業領域 `sdd/2026-10-26-usaturn-resoloop-issue-21-texture-transfer-data/`、実機の試験用プログラムと撮影・ログ）

## Global Constraints

- 設定: `--texture-transfer file|data`、`RESOLOOP_TEXTURE_TRANSFER`、`.resoloop.json` とユーザー設定の `textureTransfer`。既定 `file`。優先順位は CLI > 環境変数 > `.resoloop.json` > `~/.resoloop/config.json`。大文字・小文字と前後の空白は区別しない
- エラー・警告のコード: `INVALID_TEXTURE_TRANSFER`（CLI の値は終了コード 2、環境変数・設定ファイルの値は 3）、`ASSET_TEXTURE_UNDECODABLE`（6）、警告 `ASSET_AUDIO_FILE_TRANSFER`
- `data` の対象は kind が `texture`・`texture2d`（大文字・小文字を区別しない）で、plan の action が `create` の asset だけ。URI の asset と `no-op` の asset は今までどおり
- 画素は RGBA 8 bit、上の行から順。HDR は送らずに止める
- `SourceHash`（画像ファイルの SHA-256）の計算と state の形式は変えない
- Core は ResoniteLink の型を参照しない（RLoop.Core に StbImageSharp を足すのはよい）
- 実機の試験はワールドの `ResoLoop_Test_TextureTransfer_*` の Slot の下だけで行い、終わったらその Slot だけを消す。利用者の global の `resoloop` を差し替えない
- テストは Spec の「テストの方針」の組だけ（create-reso-world の「テストの採用基準」と、resoloop の `AGENTS.md` のオフラインテストの方針）
- コミットのメッセージは英語、末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## Review Focus

1. 4096² などの大きな画像: 64 MiB の画素を 1 回の WebSocket メッセージで送る。送れるか・時間・メモリを Task 4 の実機で測り、送れなければ Task 4 の contingency に従う
2. EXIF の向きを持つ JPEG: Resonite の `file` が向きを反映するなら、`data` だけ横倒しになる。Task 4 で比べ、反映するなら Task 6 を行う
3. kind の表記ゆれ（`Texture2D`）と `file://` の source: `data` に回す判定と、ヘッダーの確認の判定が食い違うと、確認を通らない画像が送られるか、確認された画像が `file` で送られる。Task 5 のテストで kind `Texture2D` の asset を使う
4. `file` で取り込み済みの state のまま `data` に切り替える: 変わっていない画像を取り込み直さない。Task 5 のテストで確かめる
5. 復号できない画像が、取り込み済みで変わっていない（`no-op`）とき: `data` に切り替えても止めない（取り込まないので）。Task 5 の停止のテストの「正しく通る例」に含める

## 要件の照合（実装前）

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 設定と優先順位、不正な値 | Task 1 | `ConfigResolver.Resolve` の値と `Sources`、`INVALID_TEXTURE_TRANSFER` | Task 1 のテスト |
| 画素の並び（上から・RGBA）、形式の展開 | Task 2 | `TextureDecoder.Decode` の結果 | Task 2 のテスト、Task 4 の実機（反転なし） |
| 生データの送信 | Task 3 | adapter が `ImportTexture2DRawData` を送り URL を返す | Task 4 の実機 |
| `colorProfile`・EXIF・大きさの決定 | Task 4（→ Task 5・6） | 撮影の区画の画素の差、時間 | `docs/TEXTURE-TRANSFER.md` の記録 |
| 変更前の停止、経路、audio の警告、切り替えで取り込み直さない | Task 5 | fake client の取り込みの記録・変更の数・警告 | Task 5 のテスト |
| `file` の失敗の案内 | Task 5 | エラーの `suggestions` | Task 8 の実機（コンテナから `file` で apply） |
| 文書 | Task 7 | README-DETAILS などの記述 | `git diff` の確認 |
| apply と再度の diff が 0 件、保存と再読込 | Task 8 | apply の結果と diff の件数、保存後の URL | Task 8 の実機 |

共有する条件（統合担当は Task 5。このセッションが担当する）:

- 「`data` で送る asset か」の判定は、`BuildAssetPlans` の確認と取り込みの経路で同じ述語（`AssetRuntime` の 1 か所）を使う。Task 5 のテストで、確認と経路の両方を同じ文書で確かめる
- `colorProfile` の値は Task 4 で決め、Task 5 の WorldService が `TextureDecoder.RawColorProfile` を adapter に渡す。adapter は値を変えずに送る
- 設定は Program が 1 回解決し、apply・plan の WorldService に渡す（`flux deploy-manifest` などアセットを取り込まない経路には渡さなくてよい）

## 実行方式

`superpowers:executing-plans`（このセッションが順に実装する）。理由: `implement_task.py check` の `self` が true（雛形の既定の適用）、WorldService と Program を複数の Task で順に変え、Task 4・8 は利用者に Resonite の起動・ワールドの保存を頼む実機の確認なので、子に渡しきれない。最後に、ブランチ全体のレビューを `superpowers:requesting-code-review` で 1 回行う。

検証の入口: コードの worktree で `dotnet test ResoLoop.slnx --nologo`。CI は public（usaturn/resoloop の `CI` workflow、windows-latest）。`--merge` なので、PR の作成後は CI を待たずにループへ進む（`finalize.py` がマージの前に CI を確かめる）。

## 実行予算

- Issue 全体の能動時間: 480 分（実装 5 Task と文書で 150 分、実機の確認 2 回で 120 分、PR と検証で 30 分、ループ 3 サイクル × 60 分。#12 の実機調査と、resoloop の PR の review-fix の実績から）
- phase の目安: 準備・Spec・Plan 40 分 / Task 1〜3 70 分 / Task 4 実機 60 分 / Task 5〜7 80 分 / Task 8 実機 60 分 / 検証・PR 30 分 / ループ 140 分
- worker: 実装の子は使わない。長時間のコマンド（`dotnet test`、約 2 分）は `run_in_background` の完了通知で待ち、期限 15 分。ループの worker の期限は pr-review-fix-loop の既定（レビュー 45 分）
- 再試行の上限: 同じ失敗の再試行は 1 回まで。実機の接続の失敗は、利用者にポートを尋ねた後に 1 回まで
- checkpoint: Task 4 の後（`colorProfile` が決まらなければ停止）、予算の 50%（240 分）・100%、Task 8 の後、ループの各サイクルの後
- 縮小・切り出し・方法変更の候補:
  - 4096² を送れない → plan で大きさの上限を確かめて止める確認を足す（上限は実測から決める）か、記録だけにして別 Issue の候補にする
  - EXIF の反映が要る → Task 6。時間が足りなければ、`data` で EXIF の向きを持つ JPEG を `ASSET_TEXTURE_UNDECODABLE` で止める縮小
  - 保存と再読込の確認を利用者が行えない → Task 8 の 4 を「マージの後の確認」にして PR 本文を `Refs #21` にし、Issue にコメント
  - どの `colorProfile` も `file` と一致しない → 停止して報告（Spec の D-9）

## ファイルの構成

| ファイル | 役割 | Task |
| --- | --- | --- |
| `src/RLoop.Core/Configuration.cs` | `RLoopConfig.TextureTransfer`、解決と検証 | 1 |
| `src/RLoop.Core/TextureTransfer.cs`（新規） | `TextureTransfer` enum、`TexturePixels`、`TextureDecoder` | 1・2・6 |
| `Directory.Packages.props`、`src/RLoop.Core/RLoop.Core.csproj` | StbImageSharp 2.30.16 | 2 |
| `src/RLoop.Core/Abstractions.cs` | `IResoniteClient.ImportTexturePixelsAsync` | 3 |
| `src/RLoop.ResoniteLink/ResoniteLinkClientAdapter.cs` | `ImportTexture2DRawData` の送信 | 3 |
| `src/RLoop.Core/WorldService.cs` | 確認・経路・警告・案内 | 5 |
| `src/RLoop.Cli/Program.cs` | `--texture-transfer`、ヘルプ、WorldService への受け渡し | 1・5 |
| `tests/RLoop.Tests/ConfigurationTests.cs` | 設定のテスト | 1 |
| `tests/RLoop.Tests/TextureDecoderTests.cs`（新規）、`tests/RLoop.Tests/TestPng.cs`（新規） | 復号のテスト、テスト用の PNG の組み立て | 2 |
| `tests/RLoop.Tests/ApplyWorkflowTests.TextureTransfer.cs`（新規）、`tests/RLoop.Tests/ApplyWorkflowTests.cs`（FakeResoniteClient） | 停止・経路のテスト | 5 |
| `README-DETAILS.md`、`docs/BLENDER.md`、`docs/DECLARATIVE.md`、`skills/codex/resonite-blender/SKILL.md`、`docs/TEXTURE-TRANSFER.md`（新規） | 文書と実機の記録 | 4・7 |

---

### Task 1: 設定 `textureTransfer`

**Files:**
- Create: `src/RLoop.Core/TextureTransfer.cs`
- Modify: `src/RLoop.Core/Configuration.cs`、`src/RLoop.Cli/Program.cs`（`cliConfig` と全体のヘルプ）
- Test: `tests/RLoop.Tests/ConfigurationTests.cs`

**Interfaces:**
- Produces: `public enum TextureTransfer { File, Data }`（`RLoop.Core`）。`RLoopConfig` の最後の引数 `string? TextureTransfer = null`（JSON の `textureTransfer`）。`ConfigResolver.Resolve` は値を `"file"`・`"data"` に正規化して返し（既定 `"file"`）、`Sources["textureTransfer"]` に出どころを入れる。`public static TextureTransfer ConfigResolver.TextureTransferOf(RLoopConfig config)`

テスト: 書く（resoloop の `AGENTS.md` が設定の優先順位のオフラインテストを求める。不正な値を黙って `file` にする誤りは、コンテナでは 52 秒の失敗まで気付けない）。

- [ ] **Step 1: 失敗するテストを書く**

`ConfigurationTests` に 2 件。既存の `BlenderUsesCliEnvironmentProjectUserPrecedence` と同じ組み立てで:

```csharp
[Fact]
public void TextureTransferUsesCliEnvironmentProjectUserPrecedence()
{
    // user "data"、project "file"、env "DATA "、cli "file" を置き、順に外す
    // 期待: cli → "file" (Sources["textureTransfer"] == "cli")、env → "data" ("environment:RESOLOOP_TEXTURE_TRANSFER")、
    //       project → "file"、user → "data"、何も無い → "file"（Sources に textureTransfer が無い）
    // TextureTransferOf(...) が "data" で TextureTransfer.Data、"file" で TextureTransfer.File
}

[Fact]
public void RejectsUnknownTextureTransfer()
{
    // cli "pixels" → RLoopException Code "INVALID_TEXTURE_TRANSFER", ExitCode 2
    // .resoloop.json {"textureTransfer":"bytes"} → Code 同じ, ExitCode 3, Context["source"] がそのファイルのパス
}
```

- [ ] **Step 2: 失敗を確かめる**

Run: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --nologo --filter "FullyQualifiedName~ConfigurationTests"`
Expected: コンパイルエラー（`TextureTransfer` が無い）

- [ ] **Step 3: 実装する**

`Pick("texture-transfer", "RESOLOOP_TEXTURE_TRANSFER", x => x.TextureTransfer, "textureTransfer")` の値を `Trim().ToLowerInvariant()` し、`file`・`data` 以外は `INVALID_TEXTURE_TRANSFER`（`Sources` が `cli` なら `ExitCodes.InvalidArguments`、ほかは `ExitCodes.ConfigurationError`。`context` に `value` と `source`）。Program の `cliConfig` に `["texture-transfer"] = parsed.Option("texture-transfer")`。全体のヘルプの Global options に `--texture-transfer file|data` の 1 行（`data`: CLI が画像を復号して画素を送る。Resonite が CLI のファイルを開けないとき）、Environment の一覧に `RESOLOOP_TEXTURE_TRANSFER`。

- [ ] **Step 4: 通ることを確かめる**

Run: Step 2 と同じ。Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/RLoop.Core/TextureTransfer.cs src/RLoop.Core/Configuration.cs src/RLoop.Cli/Program.cs tests/RLoop.Tests/ConfigurationTests.cs
git commit -m "feat: add textureTransfer setting (file|data)"
```

### Task 2: 画像の復号 `TextureDecoder`

**Files:**
- Modify: `Directory.Packages.props`（`<PackageVersion Include="StbImageSharp" Version="2.30.16" />`）、`src/RLoop.Core/RLoop.Core.csproj`（`<PackageReference Include="StbImageSharp" />`）、`src/RLoop.Core/TextureTransfer.cs`
- Create: `tests/RLoop.Tests/TestPng.cs`、`tests/RLoop.Tests/TextureDecoderTests.cs`

**Interfaces:**
- Produces（`RLoop.Core`）:
  - `public sealed record TexturePixels(int Width, int Height, byte[] Rgba)`: `Rgba.Length == Width * Height * 4`、上の行から、1 画素 R,G,B,A
  - `public static class TextureDecoder`
    - `public static string? UnsupportedReason(string path)`: ヘッダーだけを読む。扱える 8 bit・16 bit の画像なら `null`、形式が分からなければ `"unknown-format"`、HDR なら `"hdr"`
    - `public static TexturePixels Decode(string path)`: 全体を復号する。失敗は `RLoopException("ASSET_TEXTURE_UNDECODABLE", …, ExitCodes.ValidationFailed)`（`context` に `source`・`reason`）
    - `public const string? RawColorProfile`: 送るときの `colorProfile`。Task 2 では `null` を置き、Task 4 の結果で確定する
- Test helper: `internal static class TestPng { public static byte[] Encode(int width, int height, byte colorType, byte bitDepth, byte[] rows, byte[]? palette = null); }`（`rows` はフィルタ 0 の各行の前に 0 を置いた生データ。zlib は `System.IO.Compression.ZLibStream`、CRC32 は表を使う自前の計算）

テスト: 書く（誤った並び・展開は、テクスチャが反転・変色したまま気付けない S）。

- [ ] **Step 1: 失敗するテストを書く**

```csharp
[Fact]
public void DecodesRgbaTopRowFirst()
{
    // 2x2 RGBA8: (0,0)=(255,0,0,255) (1,0)=(0,255,0,128) / (0,1)=(0,0,255,255) (1,1)=(10,20,30,40)
    // Decode → Width 2, Height 2, Rgba == [255,0,0,255, 0,255,0,128, 0,0,255,255, 10,20,30,40]
}

[Theory]
// グレースケール 8 bit [0, 128] → [0,0,0,255, 128,128,128,255]
// パレット [ (1,2,3), (4,5,6) ]、索引 [1, 0] → [4,5,6,255, 1,2,3,255]
// RGB 16 bit (0xFFFF,0x8000,0x0000) → 8 bit で [255,128,0,255]（上位バイト。実測で丸めが違えば期待値を合わせて理由を書く）
public void ExpandsPngVariantsToRgba8(...)

[Fact]
public void ReportsUnknownFormatAndHdr()
{
    // "RIFF....WEBPVP8 " で始まるファイル → UnsupportedReason == "unknown-format"、Decode は ASSET_TEXTURE_UNDECODABLE
    // "#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 1 +X 1\n" + 1 画素 → UnsupportedReason == "hdr"
    // 正しく通る例: DecodesRgbaTopRowFirst の PNG → null
}
```

- [ ] **Step 2: 失敗を確かめる**

Run: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --nologo --filter "FullyQualifiedName~TextureDecoderTests"`
Expected: コンパイルエラー（`TextureDecoder` が無い）

- [ ] **Step 3: 実装する**

`ImageInfo.FromStream` で形式を判定する（null は `unknown-format`）。HDR の判定は `StbImage.stbi_is_hdr_from_memory` か `ImageInfo` の `BitsPerChannel`（実際に返る値で決め、決めた方法をコメントに書く）。`Decode` は `ImageResult.FromStream(stream, ColorComponents.RedGreenBlueAlpha)`。上下反転の設定（既定 0）には触らない。StbImageSharp の例外は `ASSET_TEXTURE_UNDECODABLE` に包む。

- [ ] **Step 4: 通ることを確かめる**

Run: Step 2 と同じ。Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add Directory.Packages.props src/RLoop.Core/RLoop.Core.csproj src/RLoop.Core/TextureTransfer.cs tests/RLoop.Tests/TestPng.cs tests/RLoop.Tests/TextureDecoderTests.cs
git commit -m "feat: decode textures to RGBA8 pixels with StbImageSharp"
```

### Task 3: adapter の生データ送信

**Files:**
- Modify: `src/RLoop.Core/Abstractions.cs`、`src/RLoop.ResoniteLink/ResoniteLinkClientAdapter.cs`

**Interfaces:**
- Consumes: `TexturePixels`（Task 2）
- Produces: `IResoniteClient.ImportTexturePixelsAsync(TexturePixels pixels, string? colorProfile, CancellationToken cancellationToken = default) -> Task<string>`（既定の実装は `ImportAssetAsync` と同じく `ASSET_IMPORT_UNAVAILABLE` の例外）。adapter は `new Link.ImportTexture2DRawData { Width, Height, ColorProfile = colorProfile, RawBinaryPayload = pixels.Rgba }` を `_link.ImportTexture` で送り、`Wait(..., "asset.texture.import-raw", …)`、`EnsureSuccess(response, "ASSET_IMPORT_FAILED", { kind = "texture", width, height, transfer = "data" })`、`AssetURL` を返す（無ければ `ASSET_URL_MISSING`）

テスト: 書かない（ResoniteLink のメッセージを組むだけで、誤りは初回の取り込みでエラーか明らかな異常になる L）。代わりの検証: ビルドが通ること、Task 4 の実機で URL が返り表示されること。

- [ ] **Step 1: 実装する**（上の Interfaces のとおり。`RawBinaryPayload` にバイト列をそのまま渡し、`AccessRawData` で複製しない）
- [ ] **Step 2: ビルドする** — Run: `dotnet build ResoLoop.slnx --nologo`。Expected: 警告・エラー 0 の増加なし
- [ ] **Step 3: Commit** — `git commit -m "feat: send texture pixels with ImportTexture2DRawData"`

### Task 4: 実機での比較（Issue の「実装の前に確かめること」の 1〜3）

**Files:**
- Create（コミットしない）: `/workspaces/reso-world/tmp/agents/issue-21.paqvzxic/probe/`（C# のコンソール。worktree の `src/RLoop.Core`・`src/RLoop.ResoniteLink` を ProjectReference）、試験用の画像（`uv run --with pillow` の Python で作る）、撮影と結果の JSON
- Create: `docs/TEXTURE-TRANSFER.md`（結果の記録。Task 7 で README-DETAILS からリンク）

**Interfaces:**
- Consumes: `TextureDecoder.Decode`（Task 2）、`ImportTexturePixelsAsync`（Task 3）、`ResoniteLinkClientAdapter`・`LiveCaptureService`（既存）
- Produces: `TextureDecoder.RawColorProfile` の確定値、EXIF の要否（Task 6 を行うか）、大きさの結果

テスト: 書かない（実機の確認）。

- [ ] **Step 1: 試験用の画像を作る**: 256×256 の 4×4 区画（区画ごとに平らな色。左上と右下は他と違う色）を、(a) sRGB カラー PNG、(b) アルファ 0/64/128/255 を含む PNG、(c) ノーマルマップ PNG、(d) データ用のグレーの段階 PNG、(e) 同じ区画の JPEG に EXIF の向き 6、(f) 16 bit PNG、(g) パレット PNG、(h) グレースケール PNG。大きさの試験用に 2048²・4096² のノイズの PNG
- [ ] **Step 2: 利用者に Resonite の起動と試験用のワールドを開くことを依頼する**（AskUserQuestion。ワールドを前面に出すことも頼む）。`resoloop discover` で 0 件ならポートを尋ねる
- [ ] **Step 3: 試験用のプログラムを実行する**: `ResoLoop_Test_TextureTransfer_<guid>` を Root の下に作り、各画像を `file`（`\\wsl.localhost\Gentoo\home\usaturn\repo\reso-world\tmp\agents\issue-21.paqvzxic\...`）と `data`（`colorProfile` 未指定・`sRGB`・`Linear`）で取り込み、`StaticTexture2D`（`Uncompressed=true`、(c) は `IsNormalMap=true`、(d) は `PreferredProfile=Linear`）と UIX の Image で格子に並べ、PNG で撮影する。2048²・4096² は `data` と `file` の取り込みの時間を測る。終わったらその Slot だけを消す
- [ ] **Step 4: 区画の中央の画素を比べる**: `file` との差の最大値を、画像 × `colorProfile` ごとに表にする（差 3 以下を一致）
- [ ] **Step 5: 決める**: Spec の「実機での確認」の表の決め方で `RawColorProfile` と EXIF の要否を決める。どれも一致しなければ停止して報告。結果を `docs/TEXTURE-TRANSFER.md` に書き、Spec の D-9・D-10 に決定を追記して文書の worktree でコミットする
- [ ] **Step 6: `RawColorProfile` を確定値にして Commit** — `git commit -m "feat: pin texture pixel color profile from live comparison"`（値が `null` のままなら、コメントだけを直す）

### Task 5: WorldService への組み込み

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`、`src/RLoop.Cli/Program.cs`（apply・plan の WorldService に `ConfigResolver.TextureTransferOf(resolution.Config)` を渡す）、`tests/RLoop.Tests/ApplyWorkflowTests.cs`（FakeResoniteClient に `ImportTexturePixelsAsync` を足し、`PixelImports`（`List<(string? ColorProfile, int Width, int Height)>`）と `FileImports`（`List<string>`、kind）を記録）
- Create: `tests/RLoop.Tests/ApplyWorkflowTests.TextureTransfer.cs`

**Interfaces:**
- Consumes: `TextureTransfer`（Task 1）、`TextureDecoder`・`TexturePixels`（Task 2）、`ImportTexturePixelsAsync`（Task 3）、`RawColorProfile`（Task 4）
- Produces: `WorldService(IResoniteClient client, string? generatedContentSource = null, TextureTransfer textureTransfer = TextureTransfer.File)`

テスト: 書く（変更前の停止が壊れると変更の途中で止まる、経路の判定の食い違いは気付けない。S）。`file` の失敗の案内はテストを書かず Task 8 の実機で確かめる。

- [ ] **Step 1: 失敗するテストを書く**（`ApplyWorkflowTests.TextureTransfer.cs`。asset は `_root` に `TestPng.Encode` で書いた PNG と、WebP のヘッダーの偽の画像、中身を問わない `.ogg`）

```csharp
[Fact]
public async Task DataTransferStopsOnUndecodableTextureBeforeAnyChange()
{
    // 文書: 新しい Slot + texture asset "bad"（WebP の偽の画像）を参照する Component
    // data: ApplyAsync → RLoopException Code "ASSET_TEXTURE_UNDECODABLE", Context["asset"] == "bad"
    //       client.Mutations は空、AssetImports 0、PixelImports 空
    // 正しく通る例 1: 同じ文書を file で ApplyAsync → 成功、FileImports に texture 1 件
    // 正しく通る例 2: その state のまま data で PlanApplyAsync → 成功（asset は no-op。取り込まない画像は確認しない）
}

[Fact]
public async Task DataTransferSendsTexturePixelsAndKeepsAudioOnFiles()
{
    // 文書: asset "albedo" kind "Texture2D"（2x1 PNG）、"clip" kind "audio"
    // data で PlanApplyAsync → Warnings に Code "ASSET_AUDIO_FILE_TRANSFER" が 1 件
    // data で ApplyAsync → PixelImports == [(TextureDecoder.RawColorProfile, 2, 1)]、FileImports == ["audio"]
    // state の albedo の SourceHash == PNG の SHA-256（file と同じ計算）
}

[Fact]
public async Task SwitchingToDataDoesNotReimportUnchangedTextures()
{
    // file で ApplyAsync（albedo を取り込む）→ data で ApplyAsync → PixelImports 空、AssetImports 1 のまま
}
```

- [ ] **Step 2: 失敗を確かめる**

Run: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --nologo --filter "FullyQualifiedName~ApplyWorkflowTests"`
Expected: コンパイルエラー（WorldService の引数、fake の記録が無い）

- [ ] **Step 3: 実装する**

- `AssetRuntime` に `public bool SendsPixels { get; init; }`（`data` かつ `DirectUrl is null` かつ kind が `texture`・`texture2d`）。`BuildAssetPlans` は `textureTransfer` を受け取り、`SendsPixels && Action == "create"` の asset で `TextureDecoder.UnsupportedReason` が null でなければ `ASSET_TEXTURE_UNDECODABLE`（`context`: `asset`・`source`・`reason`、`suggestions`: PNG・JPEG・BMP・TGA・GIF・PSD の 8 bit に変換する／Resonite がこの CLI のファイルを開ける構成なら `--texture-transfer file`）
- 取り込みは private `ImportAssetAsync(AssetRuntime asset, CancellationToken)` にまとめる。`SendsPixels` なら `TextureDecoder.Decode` → `client.ImportTexturePixelsAsync(pixels, TextureDecoder.RawColorProfile)`（復号の失敗は `context` に `asset` を足して再送出）。それ以外は `client.ImportAssetAsync`。`file` のテクスチャで `REQUEST_TIMEOUT`、または `ASSET_IMPORT_FAILED` で `Message` か `Context` の値に `DirectoryNotFoundException`・`FileNotFoundException` を含むときは、コードと終了コードを保ったまま `context` に `asset`・`source` を足し、`suggestions` の先頭に「Resonite が別のホストやこのコンテナの外で動いていて CLI のファイルを開けないときは `--texture-transfer data`（`RESOLOOP_TEXTURE_TRANSFER=data`）で画素を送る」を足す
- `PlanApplyAsync` の `Warnings` に、`data` で新規に取り込む audio があれば `ASSET_AUDIO_FILE_TRANSFER`（severity `warning`、path `$assets`、件数と最初の key を本文に）
- Program: 233 行目付近の `new WorldService(client, …)` に `ConfigResolver.TextureTransferOf(resolution.Config)` を渡す

- [ ] **Step 4: 通ることを確かめる**

Run: `dotnet test ResoLoop.slnx --nologo`
Expected: 全件 PASS（ベースラインは RLoop.Tests 521 件・IntegrationTests 22 件）

- [ ] **Step 5: Commit** — `git commit -m "feat: import textures as pixel data when textureTransfer is data"`

### Task 6: EXIF の向き（Task 4 で Resonite が向きを反映した場合だけ）

**Files:** Modify `src/RLoop.Core/TextureTransfer.cs`、`tests/RLoop.Tests/TextureDecoderTests.cs`

**Interfaces:** `TextureDecoder.Decode` が JPEG の APP1 Exif の Orientation（1〜8）を読み、画素を回転・反転して返す（幅と高さも入れ替わる）

テスト: 書く（向きの誤りは気付きにくい S）。`AppliesExifOrientation`: 2×1 の JPEG に Orientation 6 を入れた画像（テストで APP1 を差し込む）→ 1×2、上の画素が元の左の画素。JPEG の画素は損失があるので、色の差 8 以内で比べる。

- [ ] **Step 1: 失敗するテスト** → **Step 2: 失敗を確かめる** → **Step 3: 実装** → **Step 4: 通る** → **Step 5: Commit** `feat: apply EXIF orientation when sending JPEG pixels`
- Task 4 で反映しないと分かったら、この Task は行わず、`docs/TEXTURE-TRANSFER.md` に理由を書く

### Task 7: 文書

**Files:** Modify `README-DETAILS.md`（設定の優先順位の 1・2、Blender の節に「テクスチャの転送方式」の段落と `docs/TEXTURE-TRANSFER.md` へのリンク）、`docs/BLENDER.md`（画像の取り込みの段落）、`docs/DECLARATIVE.md`（Blender からの段落）、`skills/codex/resonite-blender/SKILL.md`（「Mesh bytes are sent by the client; …」の段落: 別ホスト・コンテナでは `--texture-transfer data`、`ASSET_TEXTURE_UNDECODABLE` と `ASSET_AUDIO_FILE_TRANSFER` での対応、同じ apply を繰り返さない）、`docs/TEXTURE-TRANSFER.md`（Task 4 の記録に、使い方・エラー・制限をまとめる）

テスト: 書かない（文書。F）。代わりの検証: `git diff` で、Spec の「文書」の項目がすべて入り、エラー・警告のコードと設定の名前が実装と一致することを確かめる。同梱スキルの変更で `dotnet test` が通ること。

- [ ] **Step 1: 書く** → **Step 2: `git diff` の確認** → **Step 3: Commit** `docs: describe texture transfer by pixel data`

### Task 8: 実機での受け入れ（Issue の 4 と完了の条件）

**Files:** Modify `docs/TEXTURE-TRANSFER.md`（結果の追記）。コミットしない: セッションの `accept/`（apply の文書・画像・state・ログ）

**Interfaces:** Consumes: Task 5 までの CLI（`dotnet src/RLoop.Cli/bin/Release/net10.0/resoloop.dll`。`dotnet build -c Release` で作る）

テスト: 書かない（実機の確認）。

- [ ] **Step 1: 試験用の apply の文書を作る**: `ResoLoop_Test_TextureTransfer_Accept` の Slot に、新規テクスチャ 3 枚（sRGB カラー、アルファ付き、`PreferredProfile=Linear` のデータ用）を QuadMesh・UnlitMaterial・MeshRenderer で表示する
- [ ] **Step 2: `file` で apply** → `REQUEST_TIMEOUT`（30 秒）か `ASSET_IMPORT_FAILED` になり、`suggestions` に `--texture-transfer data` が出ることを確かめる（ワールドは変わらない）
- [ ] **Step 3: `--texture-transfer data` で apply** → 成功。もう一度 `diff --texture-transfer data --changes-only` で 0 件
- [ ] **Step 4: 利用者にワールドの保存と開き直しを依頼する**（AskUserQuestion）→ 開き直した後に `diff` で 0 件、`inspect` で StaticTexture2D の URL が `resdb:///` に変わったことを記録
- [ ] **Step 5: 撮影して表示を確かめ、試験用の Slot だけを消す**（`slot delete <その ID> --yes`。消す前に名前と親を確かめる）。利用者に、保存した試験用のワールドが不要なら消してよいことを伝える
- [ ] **Step 6: 結果を `docs/TEXTURE-TRANSFER.md` に追記して Commit** `docs: record live acceptance of texture transfer by pixel data`

### 統合と仕上げ

- [ ] ブランチ全体のレビュー（`superpowers:requesting-code-review`。Spec・Plan・差分を渡す）。致命的な指摘だけを直す
- [ ] `verification-before-completion`: 最後の commit の後に `dotnet test ResoLoop.slnx --nologo`、`git status --porcelain` が空。HEAD・argv・終了コード・ログを `tmp/agents/issue-21.paqvzxic/verify/` に記録し、`finalize.py` の `--checks-file` の形のファイルも作る
- [ ] Spec・Plan に結果を追記して文書の worktree でコミット
- [ ] push の前の検査（コードと文書の両方）→ push → PR（fork: `Closes #21`。実機の確認がマージ前に済んでいなければ `Refs #21`）、文書 PR（create-reso-world: `Refs https://github.com/usaturn/resoloop/issues/21`）
- [ ] `--merge` のループ（PARENT_ROOT の `loop.py start`）

## 実行の記録（2026-10-26）

- 実行方式: `superpowers:executing-plans`（このセッション）。作業領域と ledger は `tmp/agents/issue-21.paqvzxic/sdd/2026-10-26-usaturn-resoloop-issue-21-texture-transfer-data/progress.md`
- Task 1〜5・7・8 を完了。Task 6 は Task 4 の結果（Resonite の `file` は EXIF の向きを反映しない）で行わない
- 判断（ledger の Ruling）: `TestPng.Encode` はフィルタのバイトを自分で入れる／HDR は Radiance のシグネチャで判定する（`ImageInfo` は HDR を 8 bit と報告する）／`RawColorProfile = "sRGB"`／撮影は JPEG（Resonite の書き出しが JPEG）／停止のテストに先行する正常な画像を足す（確認を外しても通ってしまったため。変異で失敗を確認）／保存と再読込は利用者の選んだ手順でやり直した／connection ID の一致による停止は範囲外
- 最後のブランチ全体のレビュー（別のコンテキストの Opus）: Critical 0、Important 1、Minor 5、判定は「修正すれば可」
  - 直した: Important 1（`data` の取り込みの失敗に asset の情報が無く、`REQUEST_TIMEOUT` に `--timeout` の案内が無い）。修正の前後を実機（`--timeout 1` の 4096²）で確かめ、文書に大きな画像の注意を足した。Minor 3（テストの重複）は、create-reso-world のテストの採用基準（D・L）に合わせて、`SwitchingToDataDoesNotReimportUnchangedTextures` を削除し、復号のテストを HDR の拒否だけにした
  - 直さない（致命的でないため）: Minor 1（`file` の案内の後に既存の「再試行」の案内が残る）、Minor 2（`data` でも audio の失敗に案内が無い。plan の警告はある）、Minor 4（2^30 を超える画像の理由が `unknown-format` になる）、Minor 5（connection ID の件を機能の文書に記録している）
