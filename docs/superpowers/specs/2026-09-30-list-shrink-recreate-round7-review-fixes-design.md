# PR #5: Component を外した Slot の保存 index の修正（round 7）

- 状態: **2026-09-30 承認済み・実装済み**（Claude Code セッションで実装。反映結果は §9）
- 作成日: 2026-09-30
- brainstorming 経路: **bounded**。`WorldService.ApplyAsync` の Component 削除 3 か所と index の保存、回帰テストに限定する。review-fix-planning の指定により、bounded でも Spec を保存する。
- 対象 PR: https://github.com/usaturn/resoloop/pull/5 （OPEN、base は `fix/asset-url-save-migration`）
- 対象 branch: `fix/list-shrink-recreate`（作業ツリー `external/resoloop/.worktrees/fix-list-shrink-recreate`、未コミット変更なし）
- PR_REPO: `usaturn/resoloop`
- TOPLEVEL: `/workspaces/reso-world`
- MAIN_ROOT: `/workspaces/reso-world/external/resoloop`
- 検証 HEAD: `0acf96985f20a1b19968fd042ff0052d2f28cd18`（`git fetch origin` 後の `origin/fix/list-shrink-recreate` と PR の headRefOid が一致）
- fork remote: origin=`usaturn/resoloop`、upstream=`orange3134/resoloop` を確認済み。

## 1. 目的・範囲・進行状況

レビューの指摘を現行 HEAD で検証し、再現した誤動作だけを修正対象にする。成功条件は次のとおり。Component を Slot から外す apply（relocate で移動元から外す、`--prune` で削除する、中断した recreate の置換元を削除する）が成功したら、その Slot に残る管理 key の保存 `componentIndex` が実際の位置と一致する。ワールドを再読込したあとの apply が停止せずに収束し、その次の apply の書き込みが 0 件になる。

入力はレビューディレクトリだけである。他の worktree の変更、既存の未コミット Spec は検証の根拠にしていない。round 6 の判断は PR コメントと round 6 Spec の記述として参照したが、解消の根拠は今回確認したコミット済みのコードと実行結果である。

- [x] PR URL から唯一のレビューディレクトリを確定し、全 6 ファイルを読む
- [x] リポジトリ境界と現行 HEAD を確認する
- [x] コミット済みのコード・隔離 worktree で検証し、worktree を撤去する
- [x] 全指摘を 4 区分へ分類する
- [x] brainstorming で bounded と判定し、修正方針を整理する
- [x] Spec を保存し、一覧・件数・根拠を照合する
- [x] ユーザーの明示承認を受ける（2026-09-30、Claude Code セッション）

## 2. 入力と集計単位

入力ディレクトリ: `external/resoloop/reviews/#5-fix-list-shrink-recreate/`

| 接頭辞 | 読んだファイル | 冒頭の対象 HEAD | 文書内のレビュー履歴 |
| --- | --- | --- | --- |
| G | `Grok-4.7.md` | `0acf96985f20` | `485e508` → `0acf969` |
| S | `SWE-2-Max.md` | `0acf96985f20` | `d615eeb` → … → `485e508` → `0acf969` |
| O | `claude-opus-5-5.md` | `0acf96985f20` | `d615eeb` → … → `485e508` → `0acf969` |
| C | `commandcode-deepseek-deepseek-v4.1-flash.md` | `0acf96985f20` | `d615eeb` → `dc1c651` → `30476c4` → `929c9ae` → `0acf969` |
| D | `deepseek-deepseek-v4.1-flash.md` | `485e508e8c65` | `616c510` → `485e508`（round 6 から更新なし） |
| Q | `qwen3.8-max.md` | `616c510b6ffe` | `d615eeb` → … → `616c510`（round 6 から更新なし） |

`U1` などは各ファイルの「Unverified candidates」を掲載順に採番した。**S と C の `U` 番号は round 6 と一致しない**（S-U5 は round 6 では「新 key の final index」だったが、今回は「同じ Slot の 2 つの recreate」である。C-U4 は今回が初出）。Resolved findings も一覧に含める。同じ問題を複数のレビューが挙げていても省略せず、入力上の各項目を 1 件として数える。Test suggestions は対応する項目の検証案であり、別件には数えない。

| 区分 | ID 付き指摘 | 未検証候補 | 合計 |
| --- | ---: | ---: | ---: |
| 解消済み | 19 | 2 | **21** |
| 対応する | 2 | 2 | **4** |
| 判断保留 | 0 | 0 | **0** |
| 対応しない | 15 | 9 | **24** |
| 全件 | 36 | 13 | **49** |

「対応する」の 4 件（G-H2・S-U3・C-U2・Q-I2）は、重複をまとめると **1 つの修正項目 A** になる。すべて採用基準 **(a) 現行 HEAD で再現した誤動作**に該当する。

## 3. 検証方法と結果

ソースは `git show 0acf969:<path>` で読んだ。再現は `mktemp -d /tmp/review-fix-planning.XXXXXX` で作った一意な親ディレクトリの中の detached worktree で行い、HEAD の完全な SHA の一致を確認した。プロダクトコードと既存テストの差分はゼロで、一時テストファイル `ApplyWorkflowTests.ReviewProbe.cs` だけを追加した。テストの `TMPDIR` とログも同じ親ディレクトリに限定した。

| 証拠 | 内容 | 結果 |
| --- | --- | --- |
| E1 | `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter 'FullyQualifiedName~ApplyWorkflowTests'`（一時テストを含む） | **178 件成功 / 0 件失敗、exit 0**。既存 163 件（round 6 で追加した回帰テストを含む）と一時テスト 15 件 |
| E2 | G-H2: Rubble に同型の `renderer`（4 要素）・`doomed`・`sibling` を置き、同じ apply で `renderer` を 3 要素に縮め、`doomed` を子 Slot へ移すか、宣言から外して `--prune --yes` する | 4 通り（`doomed` を 2 番目・末尾 × relocate・prune）すべてで apply は成功した。保存 index は外した Component を数えたまま（例: `renderer` 2 / `sibling` 1、実位置は 1 / 0）。`ReloadWorld` のあとの apply は `STABLE_COMPONENT_AMBIGUOUS`・書き込み 0 件で、再実行しても同じ |
| E3 | E2 の対照（recreate なし、4 要素のまま） | `doomed` が `sibling` より前なら、relocate・prune とも `sibling` の保存 index が 2（実位置 1）のままで、再読込後に同じく停止し続ける。`doomed` が末尾の relocate は収束する（書き込み 0 件） |
| E4 | C-U2: `renderer`・`sib1`・`sib2`（同型）の Slot で、`renderer` の recreate を置換元の削除前に中断（`FailOnWrite=2`）。同じセッションで `renderer` を子 Slot へ移す | 移動の apply は成功した（置換と置換元の両方を削除）。`sib1`・`sib2` の保存 index は 1・2（実位置 0・1）で、再読込後の apply は `STABLE_COMPONENT_AMBIGUOUS`・書き込み 0 件 |
| E5 | C-U1: `renderer` を作り直す apply で、子 Slot の同型 `mover` を Rubble へ移す（宣言順が先・後の 2 通り） | 保存 index は実位置と一致し、再読込後の apply は書き込み 0 件で収束 |
| E6 | S-U5: 同じ Slot の `renderer` と `second` を同じ apply で 4 → 3 要素に縮め、最初の recreate の checkpoint のあと、`second` の checkpoint より前に止める（作成直後の cancel・作成前の失敗・作成応答の喪失の 3 通り） | 3 通りとも、再読込後は `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION`・書き込み 0 件で止まる。ヒントどおりに復旧すると書き込み 3 件で宣言どおりに収束し、次の apply は 0 件。cancel の系列では 2 つの key が束縛する Component が入れ替わるが、どちらの key も作り直しの対象で、宣言値に収束する |
| E7 | C-U4: 新しい key `extra` の作成応答を失わせ（作成された Component は state に ID が無い）、`extra` を宣言しない apply で `renderer` を作り直して置換元の削除前に中断する。同じセッションで `extra` を再び宣言する | apply は成功し、`extra` は新しい Component を作る。応答を失った Component は管理外のまま残る。作り直しの作成前に中断した場合は、`renderer` と `extra` が同じ Component を主張して `APPLY_COMPONENT_OWNERSHIP_CONFLICT`・書き込み 0 件で止まり続ける（D-H1 と同じ位置照合の問題） |

一時テストの最終実行は `--filter 'FullyQualifiedName~ReviewProbe'` の 12 件と、`ReviewProbeCU1|ReviewProbeCU2` の 3 件である。どちらも成功し、exit 0 だった。これらはアサーションを置かずに経過をログへ書き出したもので、修正後の回帰テストが成功したという意味ではない。

Resonite 実機、ソリューション全体、他のプロジェクトのテストは実行していない。外部のワールドに対する操作もしていない。

検証用の `/tmp/review-fix-planning.xviuaL/worktree` は、`git worktree remove --force` が成功したあと親ディレクトリごと削除した（14:17 JST ごろに不存在を確認）。一時ログとテストは残していない。再現条件は本 Spec に記録している。

## 4. 全指摘の分類

`W` は現行 HEAD の `src/RLoop.Core/WorldService.cs`、`T` は `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`。行番号は `0acf969` 基準。テスト名で示した解消の根拠は、すべて E1 の対象に含まれる。

### G: Grok

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| G-H2 | recreate と同じ apply で Slot から外した Component を最終 index が数え、再読込後に止まり続ける | 対応する | **(a)** E2。W:1140–1142 の `AssignComponentIndexes` が除くのは `Superseded` だけで、relocate の移動元・prune 対象は `kept` に残る。修正 A |
| G-H1 | recreate より前に保存した同型の新 key が、再読込後に置換対象を奪う | 解消済み | `43c262a`。W:459–470,485,493 の `AtSavedLayout`。`NewKeyCreatedBeforeARecreateConvergesAfterWorldReload` の 3 ケースが成功 |

### S: SWE

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| S-L1 | prune 予定の参照元も `APPLY_LIST_SHRINK_REFERENCED` に数える | 対応しない | W:1338–1340 は不変。変更前に止まる安全側の動作で、停止条件の緩和は仕様の変更（round 6 E7） |
| S-L3 | 中断した recreate の relocate がさらに中断すると、置換が管理外で残る | 対応しない | W:487–494,556–561 は不変。通常の relocate にもある削除元の追跡（state が 2 ID しか持たない）の設計課題（round 6 E5） |
| S-I1 | action の列挙・停止コード・復旧手順の文書追記 | 対応しない | `docs/DECLARATIVE.md:57` に作り直しで値が戻ることは記載済み。残りは情報の追加。fork の AGENTS.md「Skills are workflows, not command mirrors」 |
| S-I2 | fake の `SetFields` が裸の文字列で `JsonException` | 対応しない | 現行テストで使わない入力。fake の一般化はしない |
| S-I3 | relocate の再中断後、復旧候補に移動元の置換元が出ない | 対応しない | S-L3 と同じ移動元の追跡と候補範囲の設計課題。変更前に止まる |
| S-U1 | stale ID の key と空 ID の key の二重主張 | 対応しない | W:1213–1229 の `RecreatedOnNode` は不変。端から端までの再現なし。ownership による停止を緩める根拠なし |
| S-U2 | 空で作成して中断した Component に `initialFields` が適用されない | 対応しない | recreate 以前からの create 再開の仕様論点 |
| S-U3 | relocate+superseded・relocate の移動元・prune で、移動元の保存 index が削除を反映しない | 対応する | **(a)** E2・E3・E4。relocate+superseded は E4、移動元・prune は E2・E3 で再現。修正 A |
| S-U4 | relocate の移動元照合に `recreatedOnNode` の絞り込みが無い | 対応しない | W:1127–1130 は不変。管理外候補を含む端から端までの再現なし |
| S-U5 | 同じ Slot の 2 つの新しい recreate の間で中断すると、2 本目の束縛先を取り違える | 対応しない | E6 の 3 系列はすべて変更前に停止し、ヒントどおりの復旧で収束した。cancel の系列で 2 つの key の束縛先が入れ替わるが、どちらも作り直しの対象で、宣言値に収束する。誤動作は再現しない |
| S-U6 | 作成直後に実機が member を完全に返すか | 対応しない | 実機の不足は未確認。adapter を推測で直さない |
| S-L4 | `supersededId` 保存済みの recreate の再開で sibling が現配置 index に戻る | 解消済み | `3824a1f`。W:459 の `!SavedFinalIndexes`。`ResumedRecreateStoppedAtASiblingKeepsItsFinalIndexAcrossWorldReload` の 2 ケースが成功 |
| S-M1 | NOT_CONVERGED の取り消しで、参照が削除済みの置換を指す | 解消済み | W:449,492,504–505。`UndoneRecreateLeavesNoReferenceToTheRemovedReplacement` が成功 |
| S-L2 | `supersededId` が残る Component の relocate・宣言削除で旧 Component が残る | 解消済み | W:571–580,602–603。`MovingAComponentWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent`・`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` が成功 |
| S-M2 | 作成前に中断した key の移動で、他 key の同型 Component を移動元として束縛する | 解消済み | W:1108,1129–1130,1242–1247。`InterruptedCreateOfANewKeyThatMovesIsCreatedOnTheNewSlot` が成功 |

### O: Claude Opus

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| O-L3 | 非同期の refill で apply のたびに作り直しを繰り返す | 対応しない | W:515 の一度だけの観測は不変。実機の遅延 refill は未確認。作り直しの履歴の永続化は別の設計 |
| O-I1 | recreate・停止コードの文書、`diff --deletes-only` に置換の削除が出ない | 対応しない | 文書は S-I1 と同じ。deletes-only の表示は relocate と共通の表示仕様 |
| O-U1 | 空で作った置換を再開すると、fields 設定前の検証が空振りする | 対応しない | W:509–515 は不変。fields 設定をきっかけにした実機の refill は未確認 |
| O-M1 | 作り直しで `initialFields`・未宣言 member が初期値に戻る記述の矛盾 | 解消済み | `docs/DECLARATIVE.md:57`、`README-DETAILS.md:181`、build skill の手順 6 に明記 |
| O-L1 | 取り消し時に sibling の index がずれる | 解消済み | W:1303–1314 の `UndoRecreateState`。`UndoneRecreateKeepsSiblingIndexesSoAWorldReloadStillBindsThem` が成功 |
| O-L2 | 中断後に key を外して prune すると旧 Component が残る | 解消済み | W:597–609,1515–1523。`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` の 2 ケースが成功 |
| O-L4 | 作成前の中断で同型 sibling と ownership conflict | 解消済み | W:1242–1247,1938。`InterruptedRecreateNextToASameTypeSiblingResumes` などが成功 |
| O-L5 | 再読込後の復旧ヒントが成り立たない | 解消済み | W:1252–1275。`InterruptedRecreateNextToSameTypeSiblingsRecoversAfterWorldReloadByFollowingTheHint` の 5 ケースが成功 |
| O-L6 | 新 key の作成応答喪失で重複作成 | 解消済み | W:1106–1110。`ResumedCreateOfANewKeyNextToARecreateBindsWhatItCreated` の 2 ケースが成功 |
| O-L7 | sibling 2 つでヒント復旧後に止まる | 解消済み | W:467–470。上記ヒント復旧の 5 ケースが成功 |
| O-L8 | `supersededId` 保存前の停止で sibling だけ final index | 解消済み | W:459–463。`ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` の 3 ケースが成功 |
| O-L9 | 保存 ID の無い key が長いリストの管理外 Component を作り直す | 解消済み | W:1114–1116,1280–1288。`InterruptedCreateOfANewKeyDoesNotRecreateAnUnmanagedComponentWithALongerList` の 2 ケースが成功 |
| O-L10 | recreate より前に処理した同型の新 key が final index で保存される | 解消済み | `43c262a`。G-H1 と同じ。`NewKeyCreatedBeforeAnInterruptedRecreateIsSavedAtItsFinalIndex` も成功 |

### C: commandcode / DeepSeek

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| C-L1 | 置換元が削除済みでも再読込後に停止し、state の手編集が要る | 対応しない | W:1097–1101 は不変。session-scoped の ID から削除済みと推定せず停止する安全側の方針（round 6 E9） |
| C-I1 | `recreate` と 3 つのエラーコードが文書・スキルに無い | 対応しない | S-I1 と同じ |
| C-I2 | plan の Warnings に観測範囲の注意が無い | 対応しない | 停止時の suggestions（W:1371–1373）と PR 本文に制限を記載済み。成功した plan への警告の追加は UX の改善 |
| C-I3 | 置換が無い key を prune すると、実在しない ID の key が state に残る | 対応しない | W:602–604 は不変。実在しない対象の key を残す通常の prune と同じ方針（round 6 E8） |
| C-U1 | recreate と relocate の同居で relocate 側の index が補正されない | 対応しない | E5 で、宣言順の 2 通りとも index が一致し、再読込後に収束した。再現しない |
| C-U2 | 置換元を失う移動元 Slot の sibling の index を保存し直さない | 対応する | **(a)** E4。修正 A |
| C-U3 | 管理外 Component の証拠一致で宣言値を書き込む・`id` の欠けた state で held が効かない | 対応しない | D-H1 と共通の採用方針。公式の writer は `id` を空文字以上で保存し、欠けた state が入る経路は未確認 |
| C-U4 | 中断した create の key を recreate の apply で宣言せず、同じセッションで再宣言すると誤束縛する | 対応しない | E7 で再現した（応答を失った Component が管理外で残る）。ただし、中断した apply と apply の間に key を文書から外し、再び加える必要がある。これは round 6 で承認済みの既知の制限（実行の間の文書編集。保存用の配置の一般化が要る）と同じ類型である。宣言されない key は ID も Component も分からないため、位置から推測して変換するしかない。管理 Component の削除・上書きは起きない |
| C-H1 | held 候補の除外で index がずれ、管理外 Component を採用する | 解消済み | W:1933–1938。`ResumedRecreateBindsItsReplacementNextToAnUnmanagedSameTypeComponent` などが成功 |
| C-H2 | 位置で採用した管理外 Component を refill の取り消しで削除する | 解消済み | W:519–521。`UndoneRecreateKeepsAReplacementMatchedWithoutItsSavedId` の 2 ケースが成功 |

### D: DeepSeek（`485e508` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| D-H1 | 作成が実行されなかった recreate の再開で、管理外の同型 Component を採用する | 対応しない | W:1946 の単一候補の採用は、`0acf969` でも候補が held でなければ変わらない（W:1938 は全候補が held のときだけ作成に回す）。応答喪失の正当な再開と区別するには、証拠と停止方針の変更が要る（round 6 E4、ユーザー承認済みの据え置き） |
| D-M1 | 中断後の並び替えで管理外 Component を採用し、本来の置換が孤立する | 対応しない | D-H1 と同じ位置照合の設計課題。実機で先頭に挿入できるかは未確認（round 6 E6） |
| D-U1 | 連続した中断で current / final の index が混在する | 解消済み | `3824a1f`。S-L4 と同じ。`ResumedRecreateStoppedAtASiblingKeepsItsFinalIndexAcrossWorldReload` が成功 |

### Q: Qwen（`616c510` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| Q-L1 | 空 fields の置換の再開で、refill の検証が空振りする | 対応しない | O-U1 と同じ |
| Q-I2 | relocate の移動元 Slot の sibling の index が削除前の位置で保存される | 対応する | **(a)** E3（recreate の無い relocate・prune）、E4（中断した recreate の relocate）。修正 A |
| Q-U1 | 作成ループ前の一括 final 保存が停止窓を作る | 解消済み | `616c510` の一括保存は `485e508` で廃止。W:459–470。`ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` の 3 ケースが成功 |
| Q-M1 | 中断した recreate の移動で新旧どちらかが孤立する | 解消済み | S-L2 と同じ |
| Q-M2 | 再開時に refill の検証を飛ばして旧 Component を削除する | 解消済み | W:503–515。`ResumedRecreateThatTheRuntimeRefilledStopsAndKeepsTheOriginal` が成功 |
| Q-I1 | 停止コードの文書不足（原レビューでは解消扱い） | 対応しない | round 6 と同じ。値のリセットの記述の矛盾は解消済みで、停止コード一覧などは情報の追加 |

## 5. 修正方針

### A. Component を Slot から外したら、その Slot の保存 index を実際の配置に合わせる

対応 ID: **G-H2 / S-U3 / C-U2 / Q-I2**、基準 **(a)**。

原因: 保存 `componentIndex` は plan 時点で決まる。recreate のある Slot では `AssignComponentIndexes`（W:1140–1142）が「置換元を除き、新しい Component を末尾に足した配置」を計算するが、除くのは `Superseded` だけである。それ以外の Slot では snapshot 上の位置（W:1121）を使う。apply が Slot から Component を外す経路は次の 3 つあり、どれも残る key の index を保存し直さない。

1. relocate の移動元の削除（W:556–561）
2. 置換元の削除（W:571–580）。relocate+superseded では、置換元は移動先ではなく移動元 Slot にある
3. `--prune` による Component の削除（W:597–609）

そのため、外した Component より後ろにある Component の保存 index は 1 つずつ大きいまま残る。recreate のある Slot では、末尾に足した置換の index が外した Component を数えるため、外した Component が末尾にあってもずれる。再読込後は保存 ID が使えないので、index で候補を絞れず（W:2009、`componentIndex < components.Count` の条件）、`STABLE_COMPONENT_AMBIGUOUS` で止まる。state は書き換わらないので、再実行しても進まない。

再現手順（E2、代表例）:

1. Rubble に `renderer`（`Test.Renderer`、Materials 4 要素、Label=north）、`doomed`（同型、1 要素、west）、`sibling`（同型、4 要素、south）を宣言して apply する。`identityFields` は指定しない。
2. `renderer` を 3 要素にし、`doomed` を Rubble の子 Slot（Debris）へ移した文書で apply する。成功する。
3. 実配置は `[sibling, renderer']` なのに、state は `sibling`=1、`renderer`=2 である。
4. `ReloadWorld` のあと同じ文書で apply すると `STABLE_COMPONENT_AMBIGUOUS`・書き込み 0 件で、何度実行しても同じ。

方針:

- `ApplyAsync` に、この apply が削除した Component の ID の集合を持たせる。上記 3 か所の `RemoveComponentAsync` の直後に、削除した Component を snapshot に持つ宣言済み Slot を探す。その Slot の宣言済み Component の index を、既存の `AssignComponentIndexes` で次の配置として計算し直す。
  - snapshot の Component から、この apply が削除済みのものと、その Slot でまだ削除していない置換元（`Superseded`）を除く
  - この apply で作った Component を作成順に末尾へ足す
- 計算し直した index を、ランタイムの `ComponentIndex` と、state の保存値（`SlotKey` がその Slot の key）の両方に書く。削除のたびに既存の checkpoint（W:562–563・577–578・606）があるので、新しい checkpoint は増やさない。ランタイムの値も更新するのは、フィールドのループで後から処理する key の checkpoint（W:562）が古い index で上書きしないようにするためである。
- 削除の前の checkpoint は現行のままにする。plan 時点で移動元・prune 対象を除く案（G-H2 の推奨対応）は採らない。その案では、`supersededId` の checkpoint から移動元を削除するまでの間、まだ Slot にある Component を除いた index を保存することになる。そこで中断して再読込し、ヒントどおりに置換元を消すと、sibling の index がまだ残る移動元を指してしまう。
- recreate の無い Slot の relocate・prune（Q-I2 と E3 の対照）にも同じ処理が働く。これは PR 以前からある挙動の修正になる。ただし、recreate のある Slot（G-H2）、中断した recreate の relocate（C-U2）と同じ箇所の同じ原因なので、条件を分けずにまとめて直す。
- 宣言されていない state key（`--prune` なしで残る key、C-U4 の key）は、現行の `supersededId` の checkpoint（W:467–470）と同じく対象外とする。

検証（先に回帰テストを追加し、`0acf969` で失敗することを確かめてから実装する）:

- `T` に、recreate と同じ apply で別の同型 Component を外す Theory を加える。外し方は relocate・prune の 2 通り、外す Component の位置は sibling の前・末尾の 2 通り。成功直後の各 key の `componentIndex` が Rubble 上の実位置と一致すること。`ReloadWorld` のあとの apply が書き込み 0 件で成功し、宣言どおりの Component に束縛されること。
- `T` に、C-U2 の構成を固定するテストを加える。中断した recreate の key を子 Slot へ移し、移動元に同型 sibling が 2 つ残る構成で、上と同じことを確かめる。
- `tests/RLoop.Tests/ApplyWorkflowTests.WorldReload.cs` に、recreate の無い relocate・prune（E3 で停止した 2 通り）で、再読込後に収束することを確かめるテストを加える。
- 既存のヒント復旧・中断・取り消しのテスト（E1 の 163 件）をすべて維持する。特に、削除より前の中断を固定するテスト（`MovingAComponentWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent`、`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` の中断ケース、`InterruptedRecreateStopsBeforeMutationAfterWorldReloadWhenTheKeyMovesOrIsRemoved`）が変わらず成功すること。

## 6. 対象ファイル・非対象・互換性

実装予定のファイル（fork のルート基準）:

- `src/RLoop.Core/WorldService.cs`: 削除 3 か所のあとで、その Slot の index を計算し直して保存する。
- `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`: G-H2・C-U2 の回帰テスト。
- `tests/RLoop.Tests/ApplyWorkflowTests.WorldReload.cs`: recreate の無い relocate・prune の回帰テスト。

変更しないもの:

- 永続 state の形式、公開 CLI / API、エラーコード、plan の表示。
- plan 時点の `AssignComponentIndexes`、`AtSavedLayout` と最初の `supersededId` の checkpoint、取り消し時の `UndoRecreateState`。
- relocate の削除元 ID の追加保存と復旧候補の範囲（S-L3・S-I3）、位置照合による採用方針（D-H1・D-M1・C-U3）、宣言されない key の index の変換（C-U4）。
- 非同期 refill の履歴、adapter の推測修正、文書の追記。
- すでに保存された、ずれた index を推測で直す移行処理。修正前の apply で保存された state は、同じセッションでもう一度 apply すると snapshot 上の位置で保存し直されるが、再読込が先だと従来どおり停止する。

削除と、その直後の checkpoint の間で強制終了した場合は、その 1 件の削除だけ index がずれたまま残る。これは現行の削除と同じ範囲である。

## 7. 承認後の検証・既存 PR への反映

1. 回帰テストを先に追加し、`0acf969` で期待する収束条件が失敗することを確かめる。一時テストの「経過をログに書くだけ」の形をそのまま恒久テストにしない。
2. 修正 A を実装し、追加したテストと `--filter 'FullyQualifiedName~ApplyWorkflowTests'` を実行する。
3. 変更したプロジェクトに関連する検証として `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` を実行する。失敗している間は commit しない。実機接続、無関係なワールドのテスト、fork 全体の一括テストは条件にしない。
4. `git fetch origin` で PR の HEAD を確認し直す。根拠の SHA から更新があれば、関係する部分を確認し直す。
5. `fix/list-shrink-recreate` へ commit し、`origin` へ push する。main、追加の review-fixes ブランチ、新しい PR には載せない。
6. モデル識別子 `claude-opus-5-5` で、TOPLEVEL 側の `upsert_pr_comment.py` を使い、既存の PR #5 の自エージェントのコメント（マーカー `review-fix-planning:agent:claude-opus-5-5`）を更新する。他のエージェントのコメントは編集しない。

計画のターンでは PR コメントの投稿・commit・push をしなかった。承認後の反映は §9 に記録する。

## 8. 作業時間

担当: このセッション（Claude Code、claude-opus-5-5）。2026-09-30 13:58 JST ごろに着手。

- Task 1–2: 入力の特定（最初に指定されたディレクトリが存在せず停止、PR URL で再指定）、規約・PR・remote・HEAD の確認: 約 5 分
- Task 3: コミット済みコードの読解、一時テスト 15 件の作成・実行、既存テスト 178 件の実行、撤去: 約 12 分
- Task 4–6: 分類、bounded 設計、Spec の作成と一覧の照合: 約 7 分
- 合計: 約 24 分。テストは同期実行し、終了コードを確認してから撤去した。

サブエージェントは使用していない（ユーザーの明示的な依頼が無いため）。

## 9. 承認後の実装と反映（2026-09-30、Claude Code）

- 経路は bounded のまま、実装計画の文書は作らずにこのセッションで実装した（サブエージェントは使用していない）。
- 回帰テストを先に追加し、`0acf969` で 7 件すべてが保存 index の不一致で失敗することを確かめた。
  - `ComponentRemovedFromARecreatingSlotLeavesIndexesAWorldReloadBinds`（ListShrink、relocate・prune × 外す Component が sibling の前・末尾の 4 ケース）
  - `MovingAKeyWhoseRecreateWasInterruptedLeavesSiblingIndexesAWorldReloadBinds`（ListShrink、C-U2）
  - `ComponentRemovedFromASlotLeavesIndexesAWorldReloadBinds`（WorldReload、recreate の無い relocate・prune の 2 ケース）
  - C-U2 のテストは最初、前提の中断が起きずに失敗した。最初の apply のあと書き込みカウンタをリセットしていなかったためで、テスト側を直してから index の不一致で失敗することを確かめた。
- 実装: `ApplyAsync` にローカル関数 `SaveIndexesAfterRemoving` を追加し、relocate の移動元・置換元・prune の 3 か所の `RemoveComponentAsync` の直後に呼ぶ。plan 時点の `AssignComponentIndexes` のコメントを、recreate 以外の削除では apply が index を保存し直すことに合わせて直した。
- 検証（`ce39425`、TMPDIR はセッションの scratchpad に隔離、実機の Resonite には接続していない）
  - `--filter 'FullyQualifiedName~ApplyWorkflowTests'`: 170 件成功（既存 163 件と追加 7 件）、ビルド警告なし
  - `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj`: 382 件成功（従来の 375 件と追加 7 件）
- commit / push: `ce39425` を `fix/list-shrink-recreate` へ push した（`0acf969..ce39425`）。
