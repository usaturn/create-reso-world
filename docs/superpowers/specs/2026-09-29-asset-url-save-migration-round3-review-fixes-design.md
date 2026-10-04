# PR #4（保存で resdb に移ったアセット URL の維持）の第3ラウンドのレビュー指摘の修正設計

- 対象 PR: usaturn/resoloop #4（`fix/asset-url-save-migration`、base は `fix/slot-snapshot-dedup`）
- 現行 HEAD: `49318145e03e53f91959f76cab1618f4e4d037a5`（第2ラウンドの G2 の修正 `4931814`）
- 前回までの Spec（本書の「対応しない」の根拠として参照する）
  - 第1ラウンド（F1〜F8）: `docs/superpowers/specs/2026-09-29-asset-url-save-migration-review-fixes-design.md`
  - 第2ラウンド（G1〜G10）: `docs/superpowers/specs/2026-09-29-asset-url-save-migration-round2-review-fixes-design.md`
- 入力: `external/resoloop/reviews/#4-fix-asset-url-save-migration/`
  - `claude-opus-5-5.md`（Update。対象 HEAD `49318145e03e`）
  - `SWE-2-Max.md`（Update。対象 HEAD `49318145e03e`）
  - `qwen3.8-max.md`（Update。対象 HEAD `49318145e03e`）
  - `commandcode-deepseek-deepseek-v4.1-flash.md`（Update。対象 HEAD `49318145e03e`）
  - `deepseek-deepseek-v4.1-flash.md`（Initial。対象 HEAD `bf8616e66323`。第2ラウンドで扱った世代で、指摘は本書の H1・H4・H6・H7・H9 に含まれる）
- brainstorming の経路判定: **spike**。「対応する」は 0 件で、残すコード変更は無い。成果物は「現行 HEAD で直すべき指摘があるか」への答えであり、検証に使ったスクラッチテストは使い捨てで削除済みである

## 選別結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 2 |
| 対応する | 0 |
| 判断保留 | 0 |
| 対応しない | 10 |

検証は、現行 HEAD を detach した使い捨て worktree で行った。PR の追加テスト 13 件と、worktree にだけ置いたスクラッチテスト 5 件を `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj -c Release --filter` で実行し、18 件すべてが成功した。スクラッチテストの観測値はファイルに書き出して確認した（下記「検証の記録」）。worktree と一時ディレクトリは検証後に削除済みである。静的な指摘は `git show 49318145e03e:<path>` と `git grep 49318145e03e` で確認した。

### 全指摘の一覧

「前回 ID」は第2ラウンドの Spec の ID で、同じ論点であることを示す。

| ID | 前回 ID | 出典 | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- | --- | --- |
| H1 | G1 | Opus L-1、commandcode-DeepSeek I-2、DeepSeek L-1、Opus テスト提案 2、commandcode-DeepSeek テスト提案 3、DeepSeek テスト提案 2、Qwen の棄却候補 (e) | 宣言を変えていない参照の実機の値が、保存以外の理由（人手の差し替えなど）で 1 つの resdb URL に揃った場合も「保存による移行」として採用され、ドリフトが修正されなくなる | 対応しない | 判定条件（`WorldService.cs:1186`）の是非を問う仕様の論点で、第1ラウンドの F3・第2ラウンドの G1 で「対応しない」と決めている。区別の手がかりは state に無い。`Warnings` に出す案・文書に明記する案も仕様を足す判断で、(a)〜(d) を満たさない。現行 HEAD でも判定は変わっていない（`AssetUrlMigratedByWorldSaveIsAdoptedInsteadOfRewrittenToLocal` が、import 結果と異なる resdb URL を採用することを固定している） |
| H2 | G2 | Opus の Resolved findings（L-2） | 元ファイルを変えた apply が再 import の後で止まり、再実行の前に保存すると、古い内容の resdb URL が採用される | 解消済み | `4931814` の `ForgetAssetEvidence`（`WorldService.cs:405`、`:1199-1211`）。`InterruptedReimportDoesNotAdoptTheSavedUrlOfThePreviousContent`（2 件）が現行 HEAD の worktree で成功した。フィールド段階で止めた場合もスクラッチ A で収束を確認した |
| H3 | — | Opus テスト提案 1 | H2 の回帰テストに、フィールド段階（1 件目のフィールドを書いた直後）で止める場合を足す | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない。挙動はスクラッチ A で正しいことを確認した（新旧どちらの state でも、書き直した参照だけから新しい内容の URL を採用し、再 plan は 0 件） |
| H4 | G3 | SWE L-2、DeepSeek M-1、SWE テスト提案 1、DeepSeek テスト提案 1 | `assetFields` の無い古い state では、保存後の付け替え（`$asset:other` → `$asset:mesh`）を区別できず、`other` の resdb URL を `mesh` の移行先として採用する | 対応しない | 現行 HEAD でも再現する（スクラッチ C）。古い state ではすべての宣言を観測するという扱い（`WorldService.cs:1178` の `applied is not null` の分岐）は、既存のワールドで移行を採用するために第1ラウンドの F8 で決めたトレードオフで、第2ラウンドの G3 でも「対応しない」とした。この版で一度 apply すれば記録が書かれ、以後は区別できる。SWE も【要設計判断】としている |
| H5 | G4 | Qwen L-2、Qwen テスト提案 1・2 | `initialFields` だけで `$asset:` を参照する Component は移行の観測対象外で、relocate で作り直すと state の `local://` URL が書かれる | 対応しない | 第2ラウンドの G4 と同じ。`4931814` は観測（`WorldService.cs:1176`）と記録（`:1766-1768`）の範囲を変えておらず、`ForgetAssetEvidence` の判定（`:1201-1203`）も同じ `Spec.Fields` の範囲である。PR 前から同じ挙動で回帰ではなく、作成後に実行時に書き換わり得る `initialFields` を移行の証拠にするかは設計の論点である。Qwen も【要設計判断】としている |
| H6 | G5 | commandcode-DeepSeek L-1、DeepSeek L-2、commandcode-DeepSeek テスト提案 1・2、DeepSeek テスト提案 3 | 配列・オブジェクトの中の `$asset:` 参照をたどる `Collect`・`ContainsAssetReference` の再帰にテストが無い | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない。第1ラウンドの F5・第2ラウンドの G5 と同じ。現行 HEAD の `tests/` に入れ子の `$asset:` 宣言が無いことは `git grep` で確認した |
| H7 | G6 | DeepSeek テスト提案 4 | 付け替えのテストで、apply 後に `assetFields` が新しい宣言に更新されることも確かめる | 対応しない | 第2ラウンドの G6 と同じ。テスト追加の提案で、(a)〜(d) を満たさない。記録が書かれることは `StateWithoutRecordedAssetFieldsStillAdoptsTheMigratedUrl` が確かめている |
| H8 | G7 | Opus I-1、Qwen I-1、commandcode-DeepSeek I-1 | `docs/DECLARATIVE.md:101` が、state の URL を実機の resdb URI に更新する挙動を説明していない | 対応しない | 第1ラウンドの F4・第2ラウンドの G7 と同じ。現行 HEAD の `:101`（「source hashと返されたURLをownership stateへcheckpointし、内容が変わった場合だけ再importします」）は import 時の挙動として今も正しく、記載漏れで事実誤認ではない。fork の `AGENTS.md:42` が追随を求めるのは README の例と `skills/codex/*/SKILL.md` で、README に state の URL や diff の Reason の例は無く、`skills/codex/resonite-blender/SKILL.md:88` は URL を不透明なものとして扱う記述で今も正しい |
| H9 | G8 | DeepSeek の Unverified candidate | 一部の参照だけが resdb に移り、残りが local のままの場合は採用されず、移った参照も state の local URL で上書きされる | 対応しない | 第2ラウンドの G8 と同じ。PR 本文が「値が混在している場合は従来の挙動を維持する」と定めた仕様で、`AssetUrlIsNotTreatedAsMigratedUnlessEveryLiveReferenceSharesOneResdbUri` の `("resdb:///saved-a", null)` が固定している |
| H10 | G9 | SWE の Resolved findings（L-1 の new-key 部分）、Qwen の棄却候補 (f) | 管理済み Slot に新しいキーで追加した Component の参照は観測されない | 対応しない | 第1ラウンドの F2・第2ラウンドの G9 と同じ。新しいキーの Component には、実機で対応する管理 Component が無い |
| H11 | G10 | SWE の Resolved findings（L-1 の relocation 部分）、Qwen の Resolved findings（L-1） | relocate する Component の参照が観測されず、作り直した Component に state の `local://` URL が書かれる | 解消済み | `e61d83d` で観測対象が `component.Existing ?? component.RelocationSource` になった（`WorldService.cs:1172`）。`AssetUrlMigratedByWorldSaveIsAdoptedWhenItsOnlyReferenceIsRelocated` が現行 HEAD の worktree で成功した |
| H12 | — | commandcode-DeepSeek の Unverified candidate、Qwen の棄却候補 (a)・(b) | `ForgetAssetEvidence` は記録をフィールド単位（古い state では Component 単位）で外す。そのため、再 import したアセットと同じフィールド（古い state では同じ Component）で参照している別のアセットの証拠も、フィールドを書き直すまで失われる | 対応しない | 誤動作ではない。証拠を失う方向にしか働かず、失った場合は PR 前と同じ「state の local URL を書く」挙動に戻るだけで、誤った URL は採用しない。証拠が消えるのは、再 import の後にフィールドを書き直す前で apply が止まった間だけである。最後まで終わった apply では `CreateComponentState`（`WorldService.cs:513`）が記録を作り直す。古い state を Component 単位で扱うことは、第2ラウンドの G2 の設計（`:1195-1198` のコメント）で決めている。スクラッチ B で、古い state では他のアセットの移行を採用せずに local URL へ戻り、記録が作り直されて再 plan が 0 件になることを確認した。同じフィールドに複数のアセットを並べる場合（新しい state）は、fake が配列値を `list` として持たないため再現していないが、外す単位がフィールドであること（`:1207`）はコードで確認した |

次のものは、指摘として数えない。

- Qwen の棄却候補 (c)（新規 Component の作成とフィールドの記録の間で止まる場合）と (d)（`Collect` の配列経路で実機が文字列のフィールド）: レビュアー自身が、採用を控える方向にしか働かないとして棄却している
- Opus の Review coverage の「反証の検討」(1)〜(3): 候補の検討の記録で、Opus は指摘にしていない
- 各レビューの「未実施の検証」に挙がった Resonite 実機での確認（`e61d83d`・`bf8616e`・`4931814` は実機で未確認）: 指摘ではない

### 検証の記録

現行 HEAD（`4931814`）の worktree で、次のスクラッチテストを実行した。どれも `ImportUrlPrefix = "local://machine/asset-"` の fake を使い、保存は実機の値を書き換えて `ReloadWorld` する既存のヘルパーで模した。

**A: フィールド段階での中断（H2・H3）**。`SavedAssetWorld`（`mesh-a`・`mesh-b` が `$asset:mesh` を参照）を apply したあと `crate.bin` を書き換え、`Progress` の `fields` 段階（1 件目のフィールドを書いた直後）で cancel した。

| 観測 | 新しい state | 古い state（`assetFields` を削除） |
| --- | --- | --- |
| 中断 | `APPLY_CANCELLED`。実機は `local://machine/asset-2`（書き込み済み）と `local://machine/asset-1`。記録は `mesh-a` が `{"URL":"$asset:mesh"}`、`mesh-b` が `{}` | 同左 |
| 保存（`resdb:///saved-new`・`resdb:///saved-old`）後の plan | asset は移行と判定。`mesh-a` は `no-op`、`mesh-b` は `update`。`Changes` 1 件 | 同左 |
| apply | `ComponentsUpdated=1`。実機は 2 件とも `resdb:///saved-new`、state の url も `resdb:///saved-new` | 同左 |
| その後の plan | `Changes` 0 件 | 同左 |

**B: 1 つの Component が 2 つのアセットを参照する場合の中断（H12）**。`holder-0` が `URL: $asset:mesh`・`URL2: $asset:other` を持つワールドを apply したあと `crate.bin` を書き換え、`assets` 段階（`mesh` の再 import の直後、`other` の処理の前）で cancel した。

| 観測 | 新しい state | 古い state |
| --- | --- | --- |
| 中断後の記録 | `{"URL2":"$asset:other"}` | `{}` |
| 保存（`URL` を `resdb:///saved-old-mesh`、`URL2` を `resdb:///saved-other`）後の plan | `mesh` は移行と判定しない。`other` は移行と判定する。`holder-0` は `update` | `mesh`・`other` とも移行と判定しない。`holder-0` は `update` |
| apply | `URL` は `local://machine/asset-3`、`URL2` は `resdb:///saved-other`。state の `other` は `resdb:///saved-other` | `URL` は `local://machine/asset-3`、`URL2` は `local://machine/asset-2`（PR 前と同じ挙動）。state の `other` は `local://machine/asset-2` |
| apply 後の記録 | `{"URL":"$asset:mesh","URL2":"$asset:other"}` | 同左（作り直された） |
| その後の plan | `Changes` 0 件 | `Changes` 0 件 |

**C: 古い state での付け替え（H4）**。第2ラウンドと同じ手順（`other` を参照するワールドを apply し、実機を `resdb:///saved-other` にして保存を模し、`assetFields` を削除して `$asset:mesh` へ付け替え）を現行 HEAD で実行した。plan は `mesh` を移行と判定し、`holder-0` は `no-op`、`Changes` 0 件。apply 後の state は `mesh` が `resdb:///saved-other`、`other` が `local://machine/asset-2`、書き込み 0。第2ラウンドの結果と同じで、`4931814` はこの経路に影響しない（再 import が無いため `ForgetAssetEvidence` は呼ばれない）。

## 対応する項目の修正方針

なし。現行 HEAD で再現する誤動作（a）、事実誤認の記述（b）、理由なく削除された回帰ガード（c）、ユーザが名指しで依頼した指摘（d）のいずれも無い。PR #4 のコードは変更しない。

## 範囲外として残す論点

- **H1（仕様の論点）**: 保存による移行と、人手・ツールによる書き換えを区別できない。区別の手がかりは state に無い。警告を出すか文書に明記するかは、仕様の判断になる
- **H4（承認済みのトレードオフ）**: 記録の無い古い state では、保存後の付け替えを区別できない。一度この版で apply すれば解消する
- **H5（設計の論点）**: `initialFields` だけの `$asset:` 参照を移行の証拠にするか。relocate で作り直すときに `initialFields` の実機の値を引き継ぐかという、アセットに限らない論点と合わせて判断することになる
- **H12（安全側のトレードオフ）**: 再 import で証拠を外す単位（フィールド、古い state では Component）より細かく区別するには、記録の形式を変える必要がある。外れても PR 前の挙動に戻るだけで、最後まで終わった apply で記録は元に戻る
