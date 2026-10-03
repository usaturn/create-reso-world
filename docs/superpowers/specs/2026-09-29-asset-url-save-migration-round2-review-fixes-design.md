# PR #4（保存で resdb に移ったアセット URL の維持）の第2ラウンドのレビュー指摘の修正設計

- 対象 PR: usaturn/resoloop #4（`fix/asset-url-save-migration`、base は `fix/slot-snapshot-dedup`）
- 現行 HEAD: `bf8616e66323cb2ff13f51f789c06b175dfef0fd`（第1ラウンドの F1 `e61d83d`・F8 `bf8616e` を含む）
- 前回の Spec: `docs/superpowers/specs/2026-09-29-asset-url-save-migration-review-fixes-design.md`（F1〜F8。本書の「対応しない」の根拠として参照する）
- 入力: `external/resoloop/reviews/#4-fix-asset-url-save-migration/`
  - `claude-opus-5-5.md`（Update。対象 HEAD `bf8616e66323`）
  - `SWE-2-Max.md`（Update。対象 HEAD `bf8616e66323`）
  - `deepseek-deepseek-v4.1-flash.md`（Initial。対象 HEAD `bf8616e66323`）
  - `qwen3.8-max.md`（Update。対象 HEAD `bf8616e66323`）
  - `commandcode-deepseek-deepseek-v4.1-flash.md`（Initial。対象 HEAD `7acc5c79bc85`。第1ラウンドで扱った世代で、指摘は本書の G5・G7 に含まれる）
- brainstorming の経路判定: **bounded**。apply のアセットループに処理を 1 か所足し、`ContainsAssetReference` にアセットキーでの絞り込みを足す。state の形式（`assetFields` の意味）・CLI の出力形式・公開 API は変わらない

## 選別結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 1 |
| 対応する | 1 |
| 判断保留 | 0 |
| 対応しない | 8 |

検証は、現行 HEAD を detach した使い捨て worktree で行った。worktree にだけスクラッチのテストを置いて `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter` で実行し、観測値をファイルに書き出して確認した。あわせて PR の追加テスト 11 件を同じ worktree で実行し、すべて成功した。worktree は検証後に削除済みである。

### 全指摘の一覧

| ID | 出典 | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- | --- |
| G1 | Opus L-1、DeepSeek L-1、Opus テスト提案 2、DeepSeek テスト提案 2 | 宣言を変えていないフィールドの実機の値を、人手で別の resdb URL に書き換えた場合も「保存による移行」とみなされ、ドリフトが修正されなくなる | 対応しない | 判定条件そのものの是非を問う仕様の論点で、第1ラウンドの F3 で「対応しない」と決めている。Opus・DeepSeek とも【要設計判断】としている。採用した URL を Warnings や Reason に出す提案も、仕様を足す判断になる |
| G2 | Opus L-2、Opus テスト提案 1 | 元ファイルを変えた apply が再 import の後で止まり、再実行の前にワールドを保存すると、古い内容の resdb URL が新しい sourceHash と組で state に採用される。以後の diff は 0 件で収束しない | **対応する (a)** | 下記「G2 の再現」 |
| G3 | SWE L-2、DeepSeek M-1、SWE テスト提案 1、DeepSeek テスト提案 1 | `assetFields` の無い古い state では、保存後の付け替え（`$asset:other` → `$asset:mesh`）を区別できず、`other` の resdb URL を `mesh` の移行先として採用する | 対応しない | HEAD で再現する（下記「対応しない指摘の再現」）。ただし、古い state ではすべての宣言を観測するという扱いは、第1ラウンドの F8 の設計で承認済みのトレードオフである（古い state のまま動いている既存のワールドで移行を採用するため）。厳密にする案（記録の無い Component を観測しない）は、既存のワールドでの移行の採用という PR の主目的を失わせる。Reason や文書に注記する提案は (a)〜(d) を満たさない。この版で一度 apply すれば記録が書かれ、以後は区別できる |
| G4 | Qwen L-2、Qwen テスト提案 1・2 | `initialFields` だけで `$asset:` を参照する Component は移行の観測対象外で、relocate で作り直すと state の `local://` URL が書かれる | 対応しない | HEAD で再現する（下記「対応しない指摘の再現」）が、PR 前から同じ挙動で回帰ではない。`initialFields` は「新規作成時だけ初期化し、再 apply では上書きしない」値で（`docs/DECLARATIVE.md:57`）、作成後は実行時に書き換わり得る。その実機の値を移行の証拠にしてよいかは設計の論点である。relocate で作り直すと `initialFields` が初期値に戻るのは、アセットに限らない既存の挙動である。Qwen も【要設計判断】とし、回帰ではないとしている |
| G5 | DeepSeek L-2、commandcode-DeepSeek L-1、DeepSeek テスト提案 3、commandcode-DeepSeek テスト提案 1・2 | 配列・オブジェクトの中の `$asset:` 参照をたどる `Collect`・`ContainsAssetReference` の再帰にテストが無い | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない。第1ラウンドの F5 と同じで、この経路で移行が検出されることは第1ラウンドのスクラッチテストで確認済みである |
| G6 | DeepSeek テスト提案 4 | 付け替えのテストで、apply 後に `assetFields` が新しい宣言に更新されることも確かめる | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない。記録が書かれることは `StateWithoutRecordedAssetFieldsStillAdoptsTheMigratedUrl` が確かめている |
| G7 | Opus I-1、Qwen I-1、commandcode-DeepSeek I-1 | `docs/DECLARATIVE.md:101` が、state の URL を実機の resdb URI に更新する挙動を説明していない | 対応しない | 第1ラウンドの F4 と同じ。HEAD の `:101`（「source hashと返されたURLをownership stateへcheckpointし、内容が変わった場合だけ再importします」）は変わっておらず、import 時の挙動として今も正しい。記載漏れで、事実誤認ではない |
| G8 | DeepSeek の Unverified candidate | 一部の参照だけが resdb に移り、残りが local のままの場合は採用されず、移った参照も state の local URL で上書きされる | 対応しない | PR 本文が「値が混在している場合は従来の挙動を維持する」と定めた仕様であり、`AssetUrlIsNotTreatedAsMigratedUnlessEveryLiveReferenceSharesOneResdbUri` の `("resdb:///saved-a", null)` がこの挙動を固定している |
| G9 | SWE の Resolved findings（L-1 の new-key 部分） | 管理済み Slot に新しいキーで追加した Component の参照は観測されない | 対応しない | 第1ラウンドの F2 と同じ。新しいキーの Component には実機で対応する管理 Component が無い。SWE もこの扱いに同意している |
| G10 | SWE L-1（relocation の部分。Resolved）、Qwen L-1（Resolved） | relocate する Component の参照が観測されず、作り直した Component に state の `local://` URL が書かれる | 解消済み | `e61d83d` で観測対象が `component.Existing ?? component.RelocationSource` になった（`WorldService.cs:1168`）。`AssetUrlMigratedByWorldSaveIsAdoptedWhenItsOnlyReferenceIsRelocated` が HEAD の worktree で成功した |

Qwen の「検討して棄却した候補」(a)〜(d) は、レビュアー自身が棄却しているため指摘として数えない。

### G2 の再現

HEAD（`bf8616e`）の worktree で次のスクラッチテストを実行した。

1. `SavedAssetWorld`（`mesh-a`・`mesh-b` が `$asset:mesh` を参照）を `ImportUrlPrefix = "local://machine/asset-"` の fake に apply する。実機の URL は 2 件とも `local://machine/asset-1`
2. `crate.bin` を書き換え、`ApplyOptions.Progress` の `assets` 段階で `CancellationTokenSource` を cancel して apply を止める
3. 実機の 2 件の URL を `resdb:///saved-old-content` にして `ReloadWorld` で保存と再読込を模す
4. 同じ manifest で diff と apply を再実行する

| 観測 | 結果 |
| --- | --- |
| 中断 | `APPLY_CANCELLED`。state の url は `local://machine/asset-2`（sourceHash は書き換え後の内容）、実機は 2 件とも `local://machine/asset-1`、`mesh-a` の `assetFields` は `{"URL":"$asset:mesh"}` のまま |
| 保存後の diff | asset は `no-op` / `asset URL was migrated to resdb by a world save; state will record the live URL`、`Changes` 0 件 |
| 再実行の apply | `ComponentsUpdated=0`、書き込み 0。実機は 2 件とも `resdb:///saved-old-content` のまま |
| 再実行後の state | url が `resdb:///saved-old-content`、sourceHash は書き換え後の内容 |
| その後の diff | `Changes` 0 件 |

原因は次のとおり。

- apply はアセットのループで再 import し、state の `assets.mesh` を新しい sourceHash と新しい URL で checkpoint する（`WorldService.cs:400-405`）。フィールドを書き直すのはその後の Component のループである
- `assetFields` を新しくするのはフィールドを書き終えた時点（`WorldService.cs:509`）だけで、途中の checkpoint（`:467`・`:475`）は前回の記録を引き継ぐ。そのため中断した時点の記録は「前回の apply で `$asset:mesh` を書いた」ことを示すが、そのとき書いた URL は古い内容のものである
- `DetectSavedAssetMigrations` は宣言が記録と一致するかだけを見る（`WorldService.cs:1170-1176`）。古い内容の URL が保存で移った値を、新しい内容の移行先として採用する

PR より前は、手順 4 の apply が state の `local://machine/asset-2` を書き込み、新しい内容に収束していた。エラー時の案内（「同じ apply を再実行すれば収束する」）が成り立たなくなり、しかも diff に何も出ない。

### 対応しない指摘の再現

判定の正確さのために、G3 と G4 も同じ worktree で再現した。

- G3: `TwoAssetWorld(…, "other")` を apply し、実機の URL を `resdb:///saved-other` にして保存を模したあと、state の全 Component から `assetFields` を消して `$asset:mesh` へ付け替えた。diff は `mesh` を移行と判定し、`holder-0` は `no-op`、`Changes` 0 件。apply 後の state は `mesh` が `resdb:///saved-other`、`other` が `local://machine/asset-2`、書き込み 0
- G4: `initialFields` だけで `$asset:mesh` を参照する Component を apply し、実機の URL を `resdb:///saved-crate` にして保存を模した。同じ manifest の diff は `Changes` 0 件（書き戻しは起きない）。Component を別の Slot へ移した manifest では、asset は移行と判定されず、Component は `relocate`。apply 後の実機の URL と state の url は `local://machine/asset-1`

## 対応する項目の修正方針

### G2: 再 import したアセットの参照は、フィールドを書き直すまで移行の証拠にしない

**方針**: アセットを import し直すと、そのアセットを参照している実機の値は、フィールドを書き直すまで前の内容を指している。その間に止まった apply の state では、その参照を移行の証拠から外しておく。フィールドを書き終えた時点で `CreateComponentState` が記録を作り直すので、最後まで終わった apply の state はこれまでと変わらない。

**実装**（`src/RLoop.Core/WorldService.cs`）

- `ApplyAsync` のアセットのループで、`asset.Action == "create"` のとき、state の `assets.<key>` を書き換えて checkpoint する前に、state の全 Component の記録からそのアセットの参照を外す（新しい private static メソッド。名前は実装時に決める。例 `ForgetAssetEvidence(prepared, asset.Key)`）
  - 記録がある Component: `assetFields` から、記録している宣言が `$asset:<key>` を含むフィールドを外す。配列やオブジェクトの中で他のアセットと一緒に参照しているフィールドもまとめて外す（安全側）
  - 記録が null（この版より前に書かれた state）の Component: manifest の今の宣言が `$asset:<key>` を含むときだけ `{}` にする。manifest に無い Component も `{}` にする。それ以外は null のままにして、他のアセットについては従来どおりすべての宣言を観測できるようにする
- `ContainsAssetReference` に省略可能なアセットキーを足し、指定したときは `$asset:<key>` と完全に一致する参照だけを数える。既存の呼び出し（`CreateComponentState` の記録）は変えない
- `DetectSavedAssetMigrations` と `CreateComponentState` は変えない

**古い state の扱いを Component 単位にする理由**: この版で初めて apply するワールド（既存のワールドはすべてこれに当たる。実機の確認では 147 アセットが移行の採用対象だった）で、元ファイルを変えたアセットがあり、かつ apply が途中で止まった場合を考える。記録が null の Component をすべて `{}` にすると、再実行の apply では変えていない他のアセットの移行も採用されなくなり、保存済みの参照が local URL に戻る。今の宣言が再 import したアセットを参照する Component だけを `{}` にすれば、影響をそのアセットに限れる。

**副次的な効果**: Component のループの途中で止まった場合、フィールドを書き終えた Component は新しい内容の URL を書いて記録も作り直している。書いていない Component は証拠から外れるので、保存後の再実行では新しい内容の resdb URL だけが観測され、正しく移行として採用される。HEAD では新旧の URL が混在して採用されず、local URL の書き戻しになっていた。

**テスト**（`tests/RLoop.Tests/ApplyWorkflowTests.AssetMigration.cs`）

- `InterruptedReimportDoesNotAdoptTheSavedUrlOfThePreviousContent(bool legacyState)`（`[Theory]`、`false`・`true` の 2 件）
  1. `TwoAssetWorld(…, "mesh", "other")` を apply する（`mesh` は `local://machine/asset-1`、`other` は `local://machine/asset-2`）。`legacyState` なら state の全 Component から `assetFields` を消す
  2. `crate.bin` を書き換え、`Progress` の `assets` 段階で cancel して apply を止める（`APPLY_CANCELLED`。`mesh` は `local://machine/asset-3` として checkpoint される）
  3. `SaveAssetUrls(client, "resdb:///saved-old-mesh", "resdb:///saved-other")` で保存を模す
  4. diff: `mesh` の Reason は `source hash and imported URL match state`、`holder-0` は `update`。`other` の Reason は移行の文言、`holder-1` は `no-op`
  5. apply: `holder-0` は `local://machine/asset-3`、`holder-1` は `resdb:///saved-other`。state は `mesh` が `local://machine/asset-3`、`other` が `resdb:///saved-other`
  6. 再度の diff は `Changes` 0 件
- `legacyState = true` は、記録が null の Component のうち再 import したアセットを参照するもの（`holder-0`）だけが証拠から外れ、他のアセットを参照するもの（`holder-1`）は従来どおり観測されることを確かめる
- 既存の移行テスト 11 件は、変更せずにそのまま成功すること

**検証方法**

1. 追加テストが HEAD（`bf8616e`）の実装で失敗することを先に確かめる（2 件とも、手順 4 で `mesh` が移行と判定される）
2. 実装後、追加テストを含む `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` がすべて成功すること（PR 本文の報告では `bf8616e` で 321 件）。変更は RLoop.Core と RLoop.Tests だけなので、統合テストと `scripts/resoloop-fork.sh test` は反映の条件にしない

**PR 本文**: 「変更」に「元ファイルが変わったアセットを import し直すときは、フィールドを書き直すまで、そのアセットを参照する記録を移行の証拠から外す（途中で止まった apply の後に保存しても、古い内容の resdb URL を採用しない）」を足し、「テスト」の件数（追加 11 件 → 13 件、RLoop.Tests の件数）を更新する。

**反映先**: `$TOPLEVEL/external/resoloop` で `fix/asset-url-save-migration`（PR #4 の head）に commit し、`git push origin HEAD` で既存の PR #4 へ反映する。新しい PR や `*-review-fixes` ブランチは作らない。push 後、PR #4 の review-fix-planning のコメント（マーカー `review-fix-planning:agent:claude-opus-5-5`）を更新する。

## 範囲外として残す論点

- **G1（仕様の論点）**: 保存による移行と、人手・ツールによる書き換えを区別できない。区別の手がかりは state に無く、第1ラウンドの F3 のとおり仕様の判断になる
- **G3（承認済みのトレードオフ）**: 記録の無い古い state では、保存後の付け替えを区別できない。一度この版で apply すれば解消する。注記や警告を足すかは、仕様の判断になる
- **G4（設計の論点）**: `initialFields` だけの `$asset:` 参照を移行の証拠にするか。relocate で作り直すときに `initialFields` の実機の値を引き継ぐかという、アセットに限らない論点と合わせて判断することになる
