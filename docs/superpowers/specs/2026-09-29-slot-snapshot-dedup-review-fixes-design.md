# PR #3（slot snapshot の重複排除）レビュー指摘の修正設計

- 対象 PR: usaturn/resoloop #3（`fix/slot-snapshot-dedup`）
- 現行 HEAD: `e46107c0c66b982aa1c2f8d4f7cb0692fc6d089d`（base は `e275366`）
- 入力: `external/resoloop/reviews/#3-fix-slot-snapshot-dedup/`
  - `claude-opus-5-5.md`（対象 HEAD `e46107c0c66b`）
  - `SWE-2-Max.md`（同）
  - `commandcode-deepseek-deepseek-v4.1-flash.md`（同）
  - `qwen3.8-max.md`（同）
- brainstorming の経路判定: **bounded**（既存の `PrepareAsync` の root snapshot の取得条件と追加方法の変更、および既存テストファイルへのテスト追加で完結する）

## 選別結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 0 |
| 対応する | 3 |
| 判断保留 | 0 |
| 対応しない | 7 |

検証は、現行 HEAD を detach した使い捨て worktree で行った。一時テストを置いて `dotnet test` を実行し、同じ worktree で `WorldService.cs` だけを base（`e275366`）のコミット済み blob に戻した実行とも比べた。worktree は検証後に削除済みである。

F10 は計画を提示した後にユーザが追加を指示したもので、Issue #2 に追記し、F6・F7 と合わせて対応する。

### 全指摘の一覧

| ID | 出典 | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- | --- |
| F1 | Opus I-1 | 曖昧性テスト（`DistinctSlotsOnTheSameManagedPathStayAmbiguousAfterWorldReload`）は `MatchSlot` で停止し、変更した `SnapshotSlots`／`FindManagedSlot` を通らない | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない。テストの名前と PR 本文の記載（異なる ID なら `APPLY_TARGET_AMBIGUOUS` で停止）は挙動と一致しており、事実誤認ではない |
| F2 | Opus I-2 | runtimeRelocatable な root の再読込に回帰テストが無い | 対応しない | 単独ではテスト追加の提案である。ただし F6・F7・F10 の修正でこの分岐を変えるので、その検証として同じ状況のテスト（下記テスト 3）を追加する |
| F3 | SWE L-1 | 931 行の経路で、`AddSnapshotIfNew` が捨てる部分木を先に取得している（無駄な 1 往復） | 対応しない | 性能の指摘で、正しさへの影響は無い |
| F4 | SWE 未検証候補 / DeepSeek U-1 | 親 snapshot 内の同じ ID が `IsReferenceOnly` のスタブだと、`AddSnapshotIfNew` が完全な部分木を捨てる | 対応しない | 前提（ResoniteLink が要求 depth 内の Slot をスタブで返すこと）をリポジトリ内で確認できず、fake では再現できない。修正後に追加取得を省くのは root が親の直下にある場合だけで、取得 depth は 1 以上なので、そこはスタブの範囲外である |
| F5 | DeepSeek I-1 | 曖昧性テストの `ids.Distinct().Count() == 2` は重複排除を固定しない | 対応しない | テストの強化提案である。さらに、このテストは修正前も修正後も `MatchSlot`（`parent.Children` の名前照合、970 行）で例外になり、`ids` は常に異なる 2 件になる。そのため、提案どおり `ids.Length` で固定しても重複排除は固定できない |
| F6 | DeepSeek U-2 | 移動した relocatable item で、再読込後に宣言外の子孫がパス解決できなくなる | **対応する (a)** | 下記「再現」の B |
| F7 | Qwen U-1 | `AddSnapshotIfNew` の包含判定が depth を考慮しないため、深い位置へ移動した relocatable root の子孫の観測が失われ、既存の子を作成する計画になる | **対応する (a)** | 下記「再現」の A |
| F8 | Qwen テスト提案 2 | 深い state 木（`stateDepth > MaxDepth(document.Children)`）での再読込テスト | 対応しない | テスト追加の提案で、(a)〜(d) を満たさない |
| F9 | Opus・DeepSeek・Qwen の merge 推奨 | Resonite 実機で、保存・再読込後の `resoloop diff` を確認する | 対応しない | コードや文書の修正ではない。PR 本文にも未実施と明記済み。upstream へ出す前の確認事項として残す |
| F10 | 選別時の検証（ユーザが Issue #2 への追記と対応を指示） | 再読込を伴わない再接続（セッション ID の変更のみ）や同一セッションでも、root が親 snapshot の中の深い位置にあると子孫が切り詰められ、既存の子を作成する計画になる | **対応する (d)** | 下記「再現」の D・E。`e275366` でも同じ結果になる（修正前からある問題） |

### 再現

relocatable な root `ManagedTool`（identity Component 付き）の下に `Grip/Tip` を置いて apply する。その後 Root の下に `Shelf` を作り、`ManagedTool` を `Shelf` の下へ移す。これで root は Root から depth 2 に来る。親 snapshot の depth は `max(MaxDepth+1, stateDepth) = 3` なので、`Tip` は切り詰められる。この状態で再接続して plan を作る。

| ケース | 再接続 | 次の document | 修正前（e275366） | 現行 HEAD（e46107c） |
| --- | --- | --- | --- | --- |
| A | `ReloadWorld` | root 名を `RenamedTool` に変更 | `APPLY_TARGET_AMBIGUOUS` で停止（書き込み 0） | `create:slot:tip`・`create:component:tip-target`。既存の Tip を重複して作成する計画になる |
| B | `ReloadWorld` | A に加えて Tip を宣言から外し、`Prune: true` | `APPLY_TARGET_AMBIGUOUS` で停止 | Tip の削除が計画に入らない（deletes=0） |
| C | `ReloadWorld` | root 名を変えない | `APPLY_TARGET_AMBIGUOUS` で停止 | `APPLY_RUNTIME_RELOCATABLE_ACTIVE` で停止（正しい） |
| D | セッション ID の変更のみ | root 名を変更 | A の現行と同じ（Tip を作成） | 同左 |
| E | 同一セッション | root 名を変更 | A の現行と同じ（Tip を作成） | 同左 |

D は `e275366` で実行して確認した。E は、root の ID が親 snapshot に含まれるため 916 行の分岐に入らず、PR の変更が効かない経路なので、コード上 `e275366` と同じである。現行 HEAD では A・B・D・E を下記のテストで再現した（red）。

原因は 2 つある。

- 916 行の `!ContainsSlot(parent, rootState.Id)` は、root が親 snapshot の**どこか**にあれば追加取得を省く（D・E）。親 snapshot の depth は root が親の直下にある前提で決まっているので、root が深い位置へ移動していると子孫が切り詰められる
- 再読込では旧 ID が見つからないので追加取得に入るが、`AddSnapshotIfNew`（924・941 行）が同じ理由で depth 64 の `relocated` を捨てる（A・B）。また `BuildSegments` の先勝ち化（1930 行）により、root の path segments は記録済みのパスではなく移動後の実際のパスになる。そのため `FindManagedSlot` の byPath（宣言外の子孫の解決に使う）も一致しない

修正前は A・B で同一 ID の重複から `APPLY_TARGET_AMBIGUOUS` になり、書き込み前に停止していた。この PR は、その停止を誤った計画に変えている。

## 対応する項目の修正方針

### F6・F7・F10: root が親の直下に無いときは root の snapshot を先頭に置く

`src/RLoop.Core/WorldService.cs` の `PrepareAsync` を次のように変える。

1. 追加取得に入る条件を、`!ContainsSlot(parent, rootState.Id)` から「root が親 snapshot の直下の子に無い」（`!parent.Children.Any(child => child.Id == rootState.Id)`）に変える
2. `AddSnapshotIfNew` を `AddRootSnapshot(snapshots, parent, root, path)` に置き換える。取得した root が親の直下にあれば追加しない。そうでなければ `snapshots.Insert(0, ...)` で先頭に置く。3 か所（924・931・941 行）すべてで使う。理由はヘルパーに 1 行のコメントで残す
3. 使われなくなる `ContainsSlot` と `AddSnapshotIfNew` を削除する

この変更で何が保証されるか:

- 親の直下にある root は、親 snapshot で子孫まで取得済みである。親 snapshot の depth は `max(MaxDepth(document.Children)+1, stateDepth)` で、`stateDepth` は Root からの絶対 depth なので、root の下の記録済みの Slot は root から depth `stateDepth-1` 以内にあり、すべて含まれる。そのため追加取得を省いても取りこぼさない（PR の本来の修正、つまり再読込で宣言位置にある root を二重に数えない挙動はそのまま）
- 親の直下に無い root は、root 自身を起点に取得した snapshot（relocatable なら depth 64、それ以外は `stateDepth`）を使う。`SnapshotSlots` の `DistinctBy`（1917 行）と `BuildSegments` の `TryAdd`（1930 行）はどちらも先勝ちなので、先頭に置いた完全なコピーと、state に記録したパスの segments が採用される。修正前（`e275366`）は後から追加した snapshot が segments を上書きしていたので、segments の決まり方は修正前と同じになる
- 同一 ID の重複は引き続き `DistinctBy`／`TryAdd` が 1 件にまとめる。PR が直した誤判定（同じ Slot を 2 件と数える）は再発しない
- root が親 snapshot の外にある場合（従来の relocation）は重なりが無いので、順序を変えても挙動は変わらない
- 分岐に入る場面が増えるのは、root が親の直下に無い場合だけである。relocatable でない root をセッションをまたいで動かした場合は、宣言パスの解決が `SLOT_PATH_NOT_FOUND` になって catch され、何も追加しない。これは従来の結果（root を新規作成する計画）と同じ

使い捨て worktree での試作（relocatable 経路だけを先頭へ置く版）では、A は `creates=0`（Tip は no-op）、B は `delete:slot:tip`、C は変わらず `APPLY_RUNTIME_RELOCATABLE_ACTIVE` になった。`RLoop.Tests` もすべて成功した。

### テスト（`tests/RLoop.Tests/ApplyWorkflowTests.WorldReload.cs`）

1. `RelocatableRootMovedDeeperInsideTheParentKeepsItsDescendants`（Theory: `same-session`・`new-session`・`world-reload`）: root を `Shelf` の下へ移し、再接続後に名前を変えて `PlanApplyAsync` を呼ぶ。`Creates == 0`、root が `relocate`、`tip` が `no-op`、書き込み 0 件を確かめる（A・D・E）
2. `PruneAfterWorldReloadDeletesTheDescendantOfARelocatableRootMovedDeeper`: 1 と同じ状況（`world-reload`）で、Tip を外した文書に `Prune: true` を付けて `PlanApplyAsync` を呼ぶ。Slot の削除が `tip` の 1 件だけであること、書き込み 0 件を確かめる（B）
3. `RelocatableRootConvergesAfterWorldReloadWithoutMove`: 移動していない relocatable root の再読込で、`PlanApplyAsync` と `ApplyAsync` が変更なし（creates・deletes・changes が 0、書き込み 0）で収束することを確かめる。変更する分岐のうちよく使われる経路の回帰ガードで、F2 の提案も兼ねる

### 検証方法

1. テスト 1・2 を先に書き、現行 HEAD で失敗することを確かめる（red）。確認済み: Theory の 3 ケースと prune の計 4 件が失敗し、テスト 3 は成功した
2. 修正後、`dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter "FullyQualifiedName~WorldReload|FullyQualifiedName~Relocat"` が成功することを確かめる
3. 変更したプロジェクトに関連するテストとして `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` をすべて通す

## 範囲外として残す論点

- F9 の実機確認（保存したワールドを再読込したあとの `resoloop diff`）は、upstream へ出す前に行う
- PR 本文の「変更内容」は `AddSnapshotIfNew` による説明のままなので、今回の修正後は実装と食い違う。本文の更新はユーザの判断に委ねる（経緯は PR へのコメントに記録する）
