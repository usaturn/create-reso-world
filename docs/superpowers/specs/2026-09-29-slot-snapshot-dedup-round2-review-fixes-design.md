# PR #3（slot snapshot の重複排除）2 回目のレビュー指摘の修正設計

- 対象 PR: usaturn/resoloop #3（`fix/slot-snapshot-dedup`）
- 現行 HEAD: `26c90d9bfa2c36e831c4497568d3c70ea04891ae`（base は `e275366`）
- 入力: `external/resoloop/reviews/#3-fix-slot-snapshot-dedup/`（いずれも Update モードで、対象 HEAD は `26c90d9bfa2c`）
  - `claude-opus-5-5.md`
  - `SWE-2-Max.md`
  - `commandcode-deepseek-deepseek-v4.1-flash.md`
  - `qwen3.8-max.md`
- 前回（対象 HEAD `e46107c`）の選別と対応: `2026-09-29-slot-snapshot-dedup-review-fixes-design.md`。その実装が `26c90d9` である
- brainstorming の経路判定: **bounded**（既存 PR の本文のうち 2 節を現行 HEAD に合わせて書き換えるだけで、コード変更は無い）

## 選別結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 2 |
| 対応する | 1 |
| 判断保留 | 0 |
| 対応しない | 9 |

検証は、現行 HEAD を detach した使い捨て worktree で行った。`dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` は 310 件すべて成功した。同じ worktree で `WorldService.cs` だけを base（`e275366`）のコミット済み blob に戻すと、追加テスト 8 件のうち 7 件が失敗した（成功したのは `DistinctSlotsOnTheSameManagedPathStayAmbiguousAfterWorldReload` だけ）。worktree は検証後に削除済みである。

### 全指摘の一覧

| ID | 出典 | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- | --- |
| R1 | Opus I-1、Opus テスト提案 1 | 曖昧性テストは `MatchSlot` で停止し、変更した `SnapshotSlots`／`FindManagedSlot` を通らない。`FindManagedSlot` を通る曖昧性テストを追加する | 対応しない | 前回 F1 と同じ。テスト追加の提案で (a)〜(d) を満たさない。テスト名と PR 本文の記載（異なる ID なら `APPLY_TARGET_AMBIGUOUS` で停止）は挙動と一致している |
| R2 | Opus I-3、Opus テスト提案 2 | 同一セッションで relocatable root を親の中の深い位置へ移すと、prune の削除計画に保存時のパス（現存しない `Root/ManagedTool/Grip/Tip`）が表示される | 対応しない | 表示するパスをどちらにするかという仕様の論点である（下記「範囲外として残す論点」）。削除は ID で行うので対象は正しい。`try` 分岐は `AddRootSnapshot(..., rootState.Path)`（`WorldService.cs:931`）で、同一セッションで親の外へ動いた root に保存時のパスを使うのは base（`e275366` の 931 行 `snapshots.Add(..., rootState.Path)`）からの挙動である |
| R3 | SWE L-1、SWE テスト提案 1 | 再読込後、直下にある root の部分木を取得してから `AddRootSnapshot` で捨てる（判定は取得前にできる） | 対応しない | 前回 F3 と同じ。性能の指摘で、正しさへの影響は無い |
| R4 | SWE I-1（Opus・Qwen も既出として言及） | PR 本文の「変更内容」が旧実装（`AddSnapshotIfNew`）の説明のまま。前回の review-fix-planning コメントの「親の直下にあるルートは、これまでどおり追加取得しない」も、再読込では取得してから捨てる現行の挙動（R3）と食い違う | **対応する (b)** | 下記「R4 の確認内容」 |
| R5 | SWE 未検証候補、DeepSeek U-1 | 親 snapshot の直下の子が `IsReferenceOnly` のスタブだと、`IsDirectChild` が一致して root 自身の取得を省き、子孫を観測できない | 対応しない | 前回 F4 と同じ。前提（ResoniteLink が要求 depth 内の子をスタブで返すこと）をリポジトリ内で確認できず、fake の `Map` は常に `IsReferenceOnly = false` なので再現できない。fork の `AGENTS.md` は ResoniteLink の挙動を推測しないよう求めている。親 snapshot の depth は `MaxDepth(document.Children)+1` 以上、つまり 1 以上である |
| R6 | DeepSeek U-2、DeepSeek テスト提案 2、Qwen テスト提案 2 | relocatable でない root を親の中の深い位置へ移すと、セッションをまたいだ場合に保存パスの解決が失敗し、子孫が切り詰められる | 対応しない | relocatable でない管理対象はパスで特定する設計で、移動の扱いは仕様の論点である。セッションをまたぐ場合は HEAD も base も `SLOT_PATH_NOT_FOUND` を catch して何も追加せず、結果は同じ（DeepSeek も退行ではないと記載）。同一セッションでは HEAD が root 自身の snapshot を先頭に置くので、base より改善している |
| R7 | SWE テスト提案 2 | relocatable でない root を同一セッションで深い位置へ移したケースのテスト | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない |
| R8 | Qwen テスト提案 3 | 旧形式の state（`PathSegments` 未設定）での再読込テスト | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない |
| R9 | DeepSeek・Qwen テスト提案 1、Opus・DeepSeek・Qwen の merge 推奨 | Resonite 実機で、保存・再読込後の `resoloop diff` と、`ReloadWorld` の fake の前提（Root 以外の全 ID が振り直される）を確認する | 対応しない | 前回 F9 と同じ。コードや文書の修正ではない。PR 本文にも未実施と明記済みで、upstream へ出す前の確認事項として残す |
| R10 | DeepSeek I-1（前回、今回撤回） | 曖昧性テストの `ids.Distinct().Count() == 2` は重複排除を固定しない | 対応しない | レビュアー自身が撤回した（提案どおり `ids.Length` で固定しても重複排除は固定できない）。前回 F5 の判断と同じ |
| R11 | Opus I-2（前回） | runtimeRelocatable な root の再読込に回帰テストが無い | 解消済み | HEAD の `ApplyWorkflowTests.WorldReload.cs:124` に `RelocatableRootConvergesAfterWorldReloadWithoutMove` がある。HEAD で成功し、`WorldService.cs` を base に戻すと失敗した |
| R12 | Qwen U-1（前回） | `AddSnapshotIfNew` の包含判定が depth を考慮せず、深い位置へ移した root の子孫の観測が失われる | 解消済み | HEAD に `AddSnapshotIfNew`／`ContainsSlot` は無い（`git grep` で確認）。`RelocatableRootMovedDeeperInsideTheParentKeepsItsDescendants`（3 経路）と `PruneAfterWorldReloadDeletesTheDescendantOfARelocatableRootMovedDeeper` が HEAD で成功し、base では失敗した |

### R4 の確認内容

PR 本文（`gh pr view 3 --repo usaturn/resoloop`）を現行 HEAD のコードと突き合わせた。事実と食い違う記述は次のとおり。

| 節 | 現在の記述 | 現行 HEAD の実際 |
| --- | --- | --- |
| 変更内容 | 「root の部分階層を追加する 3 か所を `AddSnapshotIfNew` 経由にしました。既存の snapshot に含まれる Slot は追加しません。」 | `AddSnapshotIfNew`／`ContainsSlot` は無い。追加取得に入る条件は `!IsDirectChild(parent, rootState.Id)` で、取得した root の snapshot は、親の直下に無ければ `AddRootSnapshot` が先頭に置き、直下にあれば捨てる（`WorldService.cs:916`・`1893-1900`） |
| 変更内容 | 「`SnapshotSlots` は Slot ID ごとに最初の 1 件（親 snapshot 側）だけ残します。」 | root の snapshot を先頭に置いた場合は、root 側が残る |
| 変更内容 | 「後の snapshot のほうが深い場合でも子孫を取りこぼしません。」 | `BuildSegments` の走査の説明としては正しいが、深い位置の root の子孫を取りこぼさない理由は、現在は先頭に置くことにある |
| 原因 | Issue #2 本来の原因（重複の観測）だけ | 2 コミット目で、root が親の中の深い位置にあると子孫が切り詰められる問題（Issue #2 の追記）も直している |
| テスト | 表に追加テスト 3 件だけ | 追加テストは 6 メソッド 8 ケース。Issue #2 の追記にある回帰テストの 3 項目が表に無い |
| テスト | 「修正前は追加テストのうち 2 件が失敗し」「RLoop.Tests 305 件」 | base では追加テスト 8 件のうち 7 件が失敗する。RLoop.Tests は 310 件 |

前回の review-fix-planning コメントの記述は、このターン以降に同じコメントを更新するときに正しい説明へ置き換える。

## 対応する項目の修正方針

### R4: PR 本文を現行 HEAD（`26c90d9`）の実装とテストに合わせる

`gh pr edit 3 --repo usaturn/resoloop --body-file <file>` で本文を置き換える。本文ファイルは scratchpad に置き、PR には push しない（コード変更は無いので commit も無い）。冒頭の `Refs #2`・fork 内レビュー用である旨、「補足」節、実機確認が未実施である旨はそのまま残す。書き換えるのは次の 3 節である。

**原因**: 既存の 1〜3 と再現の記述は残し、末尾に次の段落を足す。

> 2 コミット目では、同じ `PrepareAsync` にある別の問題も直しました（Issue #2 の追記）。親 snapshot の depth は、管理 root が親の直下にある前提で決まります。ところが修正前は、管理 root の ID が親 snapshot の**どこか**にあれば root 自身の snapshot を取得しませんでした（`!ContainsSlot(parent, rootState.Id)`）。そのため、runtimeRelocatable な root を親の中の深い位置へ移すと子孫が切り詰められ、既存の子孫を新規作成する計画になり、`--prune` で宣言から外した子孫も削除計画に入りませんでした。修正前（`e275366`）から、同一セッション・セッション ID の変更・保存と再読込のいずれでも起きます。1 コミット目（`e46107c`）の重複排除だけでは、再読込後の `APPLY_TARGET_AMBIGUOUS` による停止が、この誤った計画に変わっていました。

**変更内容**: 箇条書きを次に置き換える。

> - 管理 root が親 snapshot の直下の子に無い場合（`IsDirectChild`）に限り、root 自身の snapshot を取得します。取得した snapshot は、root が親の直下に無ければ `snapshots` の先頭に置き、直下にあれば追加しません（`AddRootSnapshot`、3 か所）。親の直下にある root は、親 snapshot が子孫まで含んでいるためです。
> - `SnapshotSlots` は Slot ID ごとに最初の 1 件だけ残します。root の snapshot を先頭に置いた場合は、親 snapshot の depth で切れた写しではなく、root 側の完全な部分木が残ります。
> - `BuildSegments` は登録済みの ID を上書きしません。先頭に置いた root の snapshot では、state に記録したパスの segments が採用されます。修正前は後から追加した snapshot が上書きしていたので、root の segments の決まり方は修正前と同じです。
> - 曖昧判定（`FindManagedSlot` / `MatchSlot`）は変えていません。**異なる ID が同じ管理パスに一致した場合は、従来どおり `APPLY_TARGET_AMBIGUOUS` で停止します。**
> - CLI の挙動・出力形式は変わらないため、README と skills は更新していません。

**テスト**: 表に Issue #2 の追記の 3 項目を足し、件数を差し替える。

> | Issue のチェック項目 | テスト |
> | --- | --- |
> | （既存の 5 行はそのまま） | |
> | 管理 root を親 snapshot の中の深い位置へ移した後、3 つの再接続経路で子孫を新規作成する計画にならない | `RelocatableRootMovedDeeperInsideTheParentKeepsItsDescendants`（same-session・new-session・world-reload） |
> | 同じ状況で `--prune` により宣言から外した子孫が削除計画に入る | `PruneAfterWorldReloadDeletesTheDescendantOfARelocatableRootMovedDeeper` |
> | 移動していない runtimeRelocatable な管理 root は、再読込後も変更なしで収束する | `RelocatableRootConvergesAfterWorldReloadWithoutMove` |
>
> `WorldService.cs` だけを修正前（`e275366`）に戻すと、追加テスト 8 件のうち 7 件が失敗します。成功する `DistinctSlotsOnTheSameManagedPathStayAmbiguousAfterWorldReload` は、修正前後とも `MatchSlot` で停止します。`dotnet test ResoLoop.slnx`: RLoop.Tests <N> 件、RLoop.IntegrationTests <M> 件すべて成功（Integration カテゴリの実機テストは opt-in のため未実行）。

`<N>`・`<M>` は、実装時に `26c90d9` の使い捨て worktree で `dotnet test ResoLoop.slnx` を実行して得た値を書く（RLoop.Tests は今回の検証で 310 件）。本文の記述を事実に合わせるための実行であり、既存 PR の CI の代わりではない。

### 検証方法

1. `26c90d9` の使い捨て worktree で `dotnet test ResoLoop.slnx` を実行し、本文に書く件数を得る。worktree は実行後に削除する
2. 書き換えた本文ファイルについて、`AddSnapshotIfNew`・`ContainsSlot`（原因節の修正前の説明を除く）・「305 件」・「2 件が失敗」が残っていないこと、`IsDirectChild`・`AddRootSnapshot` と追加テスト 6 メソッドの名前がすべて出ることを `grep` で確かめる。テスト名は `git show 26c90d9:tests/RLoop.Tests/ApplyWorkflowTests.WorldReload.cs` と突き合わせる
3. `gh pr edit` の後に `gh pr view 3 --repo usaturn/resoloop --json body` で反映を確かめる
4. commit / push は無いので、review-fix-planning の status comment（前回の記述の訂正を含む）を同じ PR の自エージェントのコメントに上書きする

## 範囲外として残す論点

- R2: 同一セッションで移動した relocatable root の子孫について、plan に表示するパスを保存時のパスと観測したパスのどちらにするか。親の外へ動いた場合も含めて保存時のパスを使うのが base からの挙動で、変えるなら親の外の場合も合わせて方針を決める
- R6: relocatable でない管理 root がセッションをまたいで移動した場合の扱い（新規作成の計画にするか、明示エラーで停止するか）
- R9: 実機確認は upstream へ出す前に行う
