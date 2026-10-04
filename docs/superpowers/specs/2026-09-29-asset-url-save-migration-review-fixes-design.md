# PR #4（保存で resdb に移ったアセット URL の維持）のレビュー指摘の修正設計

- 対象 PR: usaturn/resoloop #4（`fix/asset-url-save-migration`、base は `fix/slot-snapshot-dedup`）
- 現行 HEAD: `7acc5c79bc8514415b06933ca06b54d2c4ece51a`（親は base の先端 `5bcc5f6`）
- 入力: `external/resoloop/reviews/#4-fix-asset-url-save-migration/`（いずれも Initial モードで、対象 HEAD は `7acc5c79bc85`）
  - `claude-opus-5-5.md`
  - `SWE-2-Max.md`
  - `commandcode-deepseek-deepseek-v4.1-flash.md`
  - `qwen3.8-max.md`
- brainstorming の経路判定: F1 は **bounded**（`WorldService.DetectSavedAssetMigrations` の走査対象を 1 か所変え、テストを 1 本足す。state の形式・CLI の出力形式・公開 API は変わらない）。F8 は後からユーザが名指しで追加した項目で、state の Component の記録に任意の項目を 1 つ足す。既存の state はそのまま読め、CLI の出力形式・公開 API は変わらないため、同じく **bounded** とした
- 経緯: F1 を `e61d83d` で push したあと、ユーザが「範囲外として残す論点」に書いていた付け替えの問題を「このPRで解決してください」と名指しした。これを F8 として「対応する (d)」に移した

## 選別結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 0 |
| 対応する | 2 |
| 判断保留 | 0 |
| 対応しない | 6 |

検証は、現行 HEAD を detach した使い捨て worktree で行った。worktree にだけスクラッチのテストを置いて `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter` で実行し、結果をファイルに書き出して確認した。worktree は検証後に削除済みである。

### 全指摘の一覧

| ID | 出典 | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- | --- |
| F1 | SWE L-1（relocation の部分）、Qwen L-1、SWE テスト提案 1、Qwen テスト提案 1 | Component の Slot を manifest で移す（relocate）と、その Component の `$asset:` 参照が移行判定で観測されない。保存後に唯一の参照を移すと、再作成された Component に state の `local://` URL が書き込まれる | **対応する (a)** | 下記「F1 の再現」 |
| F2 | SWE L-1（`newManagedComponent` の部分） | 管理済み Slot に新しいキーで追加した Component も観測対象外 | 対応しない | 新しいキーの Component には、実機で対応する管理 Component が無い（state に無いキーなので `MatchComponent` の対象外。`WorldService.cs:1021`）。旧キーの Component は manifest の `$asset:` 参照ではないため、PR が定める「参照が無い場合は従来の挙動」に当たる |
| F3 | Opus L-1、Opus テスト提案 1 | 人手やツールで参照が 1 つの resdb URL に揃った場合も「保存による移行」とみなされ、ドリフトが修正されなくなる | 対応しない | 移行とみなす条件（参照がすべて同じ resdb URI）は PR 本文で定めた仕様であり、その是非は仕様の論点である。Opus 自身も【要設計判断】とし、Qwen は同じ候補を設計の範囲内として棄却している。論点は下記「範囲外として残す論点」に残す |
| F4 | Opus I-1、DeepSeek I-1、Qwen I-1 | `docs/DECLARATIVE.md:101` が、state の URL を実機の resdb URI に更新する挙動を説明していない | 対応しない | HEAD の記述（「source hashと返されたURLをownership stateへcheckpointし、内容が変わった場合だけ再importします」）は import 時の挙動として今も正しく、事実誤認ではなく記載漏れである。fork の `AGENTS.md:42` が更新を求めるのは README の例と `skills/codex/*/SKILL.md` で、README には該当する記述が無く、`skills/codex/resonite-blender/SKILL.md:88`（URL を不透明なものとして扱う）とも矛盾しない |
| F5 | DeepSeek L-1、DeepSeek テスト提案 1・2、Opus テスト提案 3、SWE テスト提案 2 | 配列・オブジェクト内の `$asset:` 参照をたどる `Collect` の再帰経路にテストが無い | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない。スクラッチのテストで `"URLs":["$asset:mesh"]` と実機の list 要素 `resdb:///saved-crate` を与えると、移行が検出され（Reason が移行の文言、`plan.Changes` 0 件）、apply の書き込み 0・state の url が resdb になることを確認した |
| F6 | Opus テスト提案 2 | `TestAsync`（`resoloop test`）が `PlanAssetUrls` 経由で移行後の URL を使う経路にテストが無い | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない。HEAD の `WorldService.cs:657` は plan と同じ `PlanAssetUrls(prepared)` を使っている |
| F7 | Qwen テスト提案 2 | 既存の参照 1 件と relocation の参照 1 件が混在するときの挙動を固定する | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない。HEAD でも既存側の観測だけで移行が検出され、`PlanAssetUrls` が relocation 側の作成にも同じ resdb URI を渡す（Qwen も「現行実装でも通るはず」と記載） |
| F8 | レビューに無い（F1 の検証中に確認し、ユーザが名指しで依頼） | 保存後に manifest で参照先を別のアセットに付け替えると、実機に残る付け替え前のアセットの resdb URL が、付け替え後のアセットの移行先として採用される | **対応する (d)** | 下記「F8 の再現」 |

Qwen の「Unverified candidates」にある 4 件（Ordinal 比較、手動設定の誤検出、TOCTOU、`ToDictionary` の重複キー）は、レビュアー自身が棄却しているため指摘として数えない。

### F1 の再現

HEAD の worktree で次のスクラッチテストを実行した。

1. `crate-a` に `{"key":"mesh-a","type":"Test.AssetHolder","fields":{"URL":"$asset:mesh"}}`、`crate-b` は空という manifest を、`ImportUrlPrefix = "local://machine/asset-"` の fake に apply する
2. 実機の `mesh-a.URL` を `resdb:///saved-crate` に書き換え、`ReloadWorld` で保存と再読込を模す
3. `mesh-a` を `crate-b` へ移した manifest で diff と apply を行う

| 観測 | 結果 |
| --- | --- |
| diff の asset | `no-op` / `source hash and imported URL match state`（移行と判定されない） |
| diff の component | `relocate` / `stable key 'mesh-a' moves the Component to Slot 'crate-b'` |
| apply | Component 追加 1・削除 1 |
| apply 後の実機の URL | `local://machine/asset-1` |
| apply 後の state の url | `local://machine/asset-1` |

原因は次のとおり。

- `BuildComponentPlans` は relocate する Component の `Existing` を null にし、移動元の実機の Component を `RelocationSource` に入れる（`WorldService.cs:1016`・`1033`）
- `DetectSavedAssetMigrations` は `Existing is not null` の Component だけを走査する（`WorldService.cs:1162`）。この例では観測値が 0 件になり、移行と判定されない
- apply は再作成する Component の初期値を `assetUrls`（state の `local://`）で解決して `AddComponentAsync` に渡し（`WorldService.cs:464`・`469`）、そのあと移動元を削除する（`WorldService.cs:503`）。relocate の plan はフィールドを比較しないので、URL の書き戻しは diff にも出ない

PR 本文は「`$asset:KEY` を参照する管理 Component の実機の値がすべて同じ `resdb:///` URI のとき、保存による移行とみなす」と定めている。`RelocationSource` は manifest で `$asset:KEY` を参照している管理 Component の実機の値であり、この定義に含まれる。この経路では、PR が直そうとしている「保存済みワールドの参照を可搬性の無い local URL に戻す」挙動がそのまま残る。

## 対応する項目の修正方針

### F1: relocate する Component を、移動元の実機の値で観測する

**実装**（`src/RLoop.Core/WorldService.cs` の `DetectSavedAssetMigrations`）: 観測ループの対象を `component.Existing ?? component.RelocationSource` に広げる。

```csharp
foreach (var component in prepared.Components)
{
    var live = component.Existing ?? component.RelocationSource;
    if (live is null) continue;
    foreach (var field in component.Spec.Fields ?? new Dictionary<string, JsonElement>())
        Collect(field.Value, live.Members?.GetValueOrDefault(field.Key));
}
```

- relocate のときは `Existing` が必ず null なので（`WorldService.cs:1022`）、2 つが同時に値を持つことは無い
- 移動元が見つからない（`RelocationSource` が null）場合は、これまでどおり観測しない
- 観測するのは既存の Component と同じく `Spec.Fields` だけで、`InitialFields` は見ない。`InitialFields` は作成時にしか適用しない値で、実機の値を管理された参照とはみなさない
- 直上のコメントに「relocate する Component は、置き換える移動元の実機の Component で観測する」旨を 1 文足す

**テスト**（`tests/RLoop.Tests/ApplyWorkflowTests.AssetMigration.cs`）: `AssetUrlMigratedByWorldSaveIsAdoptedWhenItsOnlyReferenceIsRelocated` を 1 件追加する。手順は上記「F1 の再現」の 1〜3 と同じで、次を assert する。

- diff: asset は `no-op` で Reason に `migrated to resdb by a world save` を含む。`mesh-a` は `relocate`。diff の前後で state のハッシュが変わらない
- apply: Component 追加 1・削除 1、import 1 回のまま。再作成された Component の `URL` が `resdb:///saved-crate`。state の `assets.mesh.url` が `resdb:///saved-crate`
- 同じ入力で再 apply: 書き込み 0。再 diff の `plan.Changes` が空

**PR 本文**: この修正で本文の次の 2 か所が現行の挙動と食い違うため、`gh pr edit 4 --repo usaturn/resoloop --body-file <file>` で合わせる。本文ファイルは scratchpad に置く。

- 「変更」の 1 項目目の下に「Slot を移す（relocate）Component は、移動元の実機の Component の値で観測する」を足す
- 「テスト」の「追加 7 件」を「追加 8 件」にし、relocate で唯一の参照を移したケースを列挙に足す。`dotnet test` の件数は実行結果に差し替える

**検証方法**

1. テストを先に追加し、HEAD の実装で失敗すること（asset の Reason が `source hash and imported URL match state` になる）を確認する
2. 実装後、追加テストを含む `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` がすべて成功すること（PR 本文の報告では HEAD で 317 件。変更したのは RLoop.Core と RLoop.Tests だけなので、統合テストと `scripts/resoloop-fork.sh test` は反映の条件にしない）

### F8: 前回の apply から宣言が変わっていないフィールドだけを移行の証拠にする

**方針**: フィールドの宣言が前回の apply から変わっていなければ、そのフィールドの実機の値は前回 `mesh` の URL として書いたものが保存で移ったものである。宣言が変わったフィールドの実機の値は、付け替え前の値なので証拠にしない。そのために、前回の apply で宣言していた `$asset:` 参照を state の Component ごとに記録する。

**state**（`src/RLoop.Core/ApplyWorkflow.cs`）: `ApplyStateComponent` に任意の項目 `AssetFields`（`IReadOnlyDictionary<string, JsonElement>?`）を足す。キーはフィールド名、値は `$asset:` をどこかに含むフィールドの宣言そのもの（例 `"assetFields": {"URL": "$asset:mesh"}`）である。

- 新しい版は、フィールドを書き終えた時点（`WorldService.cs:507` の `CreateComponentState(component, id, fields)`）で必ず記録する。`$asset:` を含むフィールドが無い Component は空のオブジェクト `{}` にする。これにより「null は、この項目を知らない古い版が書いた state」と区別できる。`MemberNames` が null を古い state とみなす（`WorldService.cs:238`）のと同じ扱いである
- 作成前後の checkpoint（`WorldService.cs:467`・`475`）では、フィールドをまだ書いていないので、state にある前回の記録を引き継ぐ。途中で止まっても、実際に書いていない宣言を記録しない
- `schemaVersion` は上げない。古い版はこの項目を無視して読める（`System.Text.Json` の既定）。古い版が state を書き直すと項目が消え、null（古い state）の扱いに戻るだけである
- キーの移行（`migrateFrom`）と Slot の移行は `with` でレコードごと引き継ぐので、記録も移る

**判定**（`DetectSavedAssetMigrations`）: 観測するフィールドを次のとおり絞る。

- state の記録が null（古い版が書いた state）: これまでどおり、宣言しているフィールドをすべて観測する。既存の state で保存による移行を採用できるようにするためである
- 記録がある: 記録にそのフィールドがあり、`JsonElement.DeepEquals` で今の宣言と一致するときだけ観測する。付け替えたフィールドや、新しく `$asset:` を宣言したフィールドは観測しない
- 観測するフィールドが 1 件も残らなければ、従来どおり移行とみなさない。付け替えたフィールドには state の url（`local://`）を書く。そのフィールドにとっては manifest の変更の反映であり、付け替え前の他のアセットの URL を採用するよりも正しい
- F1 で観測対象にした relocate の Component も、同じ安定キーの記録で絞る

**テスト**（`tests/RLoop.Tests/ApplyWorkflowTests.AssetMigration.cs`）

- `AssetUrlIsNotAdoptedFromAReferenceThatPointedToAnotherAssetBeforeTheSave`: 上記「F8 の再現」の手順。diff で `mesh` は移行と判定されず、`mesh-a` は `update`。apply 後の実機の URL と state の `assets.mesh.url` は `local://machine/asset-1`、`assets.other.url` は `local://machine/asset-2`
- `AssetUrlIsAdoptedFromUnchangedReferencesWhenAnotherReferenceIsRepointed`: `mesh-a` が `$asset:mesh`、`mesh-b` が `$asset:other` を参照し、保存でそれぞれ `resdb:///saved-mesh`・`resdb:///saved-other` に移ったあと、`mesh-b` を `$asset:mesh` に付け替える。`mesh-a` だけが証拠になり、`mesh` は `resdb:///saved-mesh` を採用し、`mesh-b` はその URL に更新される
- `StateWithoutRecordedAssetFieldsStillAdoptsTheMigratedUrl`: 保存のあと state の全 Component から `assetFields` を消して古い版の state を模す。diff は移行と判定し、apply 後の state には `assetFields` が `{"URL":"$asset:mesh"}` として記録される
- 既存の移行テストと F1 のテストは、変更せずにそのまま成功すること

**検証方法**: F1 と同じく、追加テストが HEAD（`e61d83d`）の実装で失敗することを先に確かめ、実装後に `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` をすべて通す。PR 本文の「変更」に F8 の判定と state の項目を足し、「テスト」の件数を更新する。

**反映先**: `$TOPLEVEL/external/resoloop` で `fix/asset-url-save-migration`（PR #4 の head）を checkout して commit し、`git push origin HEAD` で既存の PR #4 へ反映する。新しい PR や `*-review-fixes` ブランチは作らない。push 後、PR #4 に review-fix-planning のコメントを作成または更新する。

### F8 の再現

HEAD（`7acc5c7`）の worktree で次のスクラッチテストを実行した。

1. アセット `mesh`・`other` を宣言し、`crate-a` の `{"key":"mesh-a","type":"Test.AssetHolder","fields":{"URL":"$asset:other"}}` だけが `other` を参照する manifest を apply する（`mesh` はどこからも参照されない。state の url は `mesh` が `local://machine/asset-1`、`other` が `local://machine/asset-2`）
2. 実機の `mesh-a.URL` を `resdb:///other-saved` に書き換え、`ReloadWorld` で保存と再読込を模す
3. `mesh-a.URL` を `$asset:mesh` に付け替えた manifest で diff と apply を行う

| 観測 | 結果 |
| --- | --- |
| diff の asset `mesh` | `no-op` / `asset URL was migrated to resdb by a world save; state will record the live URL`（誤って移行と判定） |
| diff の component `mesh-a` | `no-op` / `Component and fields already match`（付け替えが反映されない） |
| apply | 書き込み 0 |
| apply 後の実機の URL | `resdb:///other-saved`（`other` を指したまま） |
| apply 後の state | `assets.mesh.url` が `resdb:///other-saved`、`assets.other.url` は `local://machine/asset-2` |

原因は、`DetectSavedAssetMigrations` が「manifest がいま `$asset:mesh` を宣言しているフィールド」の実機の値を、無条件に `mesh` の移行先の候補として集めることにある。その値が前回の apply で `mesh` の URL として書いたものかどうかを確かめていない。state は Component ごとに、前回 apply したフィールドの宣言を持っていない。

## 範囲外として残す論点

- **F3（仕様の論点）**: 移行の判定は「参照がすべて同じ resdb URI」だけで、保存による移行と、人手・ツールによる書き換えを区別できない。今の state には区別する手がかりが無く（resdb の URI は変換後のアセットの内容から決まるので sourceHash とは照合できない）、区別するなら PR の仕様を変える判断になる
- **レビューに挙がっていない観察（F8 として対応済み。以下は F1 の時点の記録）**: F1 の修正の安全性を確かめる過程で、同じ判定条件によって manifest の変更が反映されない例を確認した。保存後に、ある Component の `URL` を manifest で `$asset:other` から `$asset:mesh` に付け替える（`mesh` は import 済みで state の url が `local://`、他に参照が無い）。すると、実機に残っている `other` の resdb URL が `mesh` の移行先として採用され、Component は `no-op`・書き込み 0 のまま `other` を指し続ける。さらに state の `assets.mesh.url` が `other` の URL に書き換わる（スクラッチテストで `live=resdb:///other-saved`、`meshState=resdb:///other-saved` を確認）。state は Component ごとの適用済みフィールド値を持たない（`ApplyStateComponent` は `IdentityValues` だけを記録する）。このため、「そのフィールドが以前もこのアセットを指していたか」を確かめる修正は state の形式の変更を伴い、数行では済まない。F1 の修正で relocate も観測対象になるので、relocate と付け替えを同時に行った場合も同じ性質を持つが、既存の Component と同じ性質が広がるだけで、新しい種類の誤採用は生まない。扱いはユーザが判断する
