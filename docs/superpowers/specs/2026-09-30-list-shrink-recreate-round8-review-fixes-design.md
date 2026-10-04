# PR #5: 宣言外の key の index・入れ子参照の検査・置換どうしの参照の修正（round 8）

- 状態: **2026-09-30 承認済み・実装済み**（Claude Code セッションで実装。反映結果は §9）
- 作成日: 2026-09-30
- brainstorming 経路: **bounded**。`WorldService.cs` の既存の処理 4 か所（index の保存し直し、`ValidateRecreateReferences`、recreate の検証ループ、`CreateComponentState`）と回帰テストに限定する。永続 state の形式、公開 CLI / API、エラーコード、plan の表示は変えない。review-fix-planning の指定により、bounded でも Spec を保存する。
- 対象 PR: https://github.com/usaturn/resoloop/pull/5 （OPEN、base は `fix/asset-url-save-migration`）
- 対象 branch: `fix/list-shrink-recreate`（作業ツリー `external/resoloop/.worktrees/fix-list-shrink-recreate`、HEAD `ce39425`、未コミット変更なし）
- PR_REPO: `usaturn/resoloop`
- TOPLEVEL: `/workspaces/reso-world`
- MAIN_ROOT: `/workspaces/reso-world/external/resoloop`
- 検証 HEAD: `ce39425a2d026f3f453c1adde969e4f77603d89d`（`git fetch origin` 後の `origin/fix/list-shrink-recreate` と PR の headRefOid が一致）
- fork remote: origin=`usaturn/resoloop`、upstream=`orange3134/resoloop` を確認済み。

## 1. 目的・範囲・進行状況

レビューの指摘を現行 HEAD（`ce39425`）で検証し、再現した誤動作だけを修正の対象にする。成功条件は次の 4 つ。

1. 宣言から外して prune していない key が Slot に残っていても、apply が Component を外したあとにワールドを再読込すると、plan・apply は止まらずに収束する。
2. 作り直す Component を、管理 Component の入れ子の子のうち宣言していないものが参照しているときは、変更の前に `APPLY_LIST_SHRINK_REFERENCED` で止まる。
3. refill の検証で作り直しを取り消したとき、削除した置換を指す参照が残らない。
4. フィールドを設定せずに作った置換の作成応答を失っても、再実行したときに置換を重複して作らない。

入力はレビューディレクトリだけである。round 7 の判断は PR コメント（review-fix-planning）と round 7 Spec の記述を参照した。ただし、解消したかどうかの根拠には、今回確認したコミット済みのコードと実行結果だけを使った。

- [x] PR URL から唯一のレビューディレクトリを確定し、全 8 ファイルを読む
- [x] リポジトリ境界と現行 HEAD を確認する
- [x] コミット済みのコードと隔離 worktree で検証し、worktree を撤去する
- [x] 全指摘を 4 区分へ分類する
- [x] brainstorming で bounded と判定し、修正方針を整理する
- [x] Spec を保存し、一覧・件数・根拠を照合する
- [x] ユーザーの明示承認を受ける（2026-09-30、Claude Code セッション）

## 2. 入力と集計単位

入力ディレクトリ: `external/resoloop/reviews/#5-fix-list-shrink-recreate/`

| 接頭辞 | 読んだファイル | 冒頭の対象 HEAD | 文書内のレビュー履歴 |
| --- | --- | --- | --- |
| O | `claude-opus-5-5.md` | `ce39425a2d02` | `d615eeb` → … → `0acf969` → `ce39425` |
| P | `gpt-6.1-sol.md` | `ce39425a2d02` | `ce39425`（Initial） |
| K | `grok-4.7.md`（小文字） | `ce39425a2d02` | `ce39425`（Initial） |
| G | `Grok-4.7.md`（大文字） | `0acf96985f20` | `485e508` → `0acf969`（round 7 から更新なし） |
| S | `SWE-2-Max.md` | `0acf96985f20` | `d615eeb` → … → `0acf969`（round 7 から更新なし） |
| C | `commandcode-deepseek-deepseek-v4.1-flash.md` | `0acf96985f20` | `d615eeb` → … → `0acf969`（round 7 から更新なし） |
| D | `deepseek-deepseek-v4.1-flash.md` | `485e508e8c65` | `616c510` → `485e508`（round 6 から更新なし） |
| Q | `qwen3.8-max.md` | `616c510b6ffe` | `d615eeb` → … → `616c510`（round 6 から更新なし） |

`Grok-4.7.md` と `grok-4.7.md` は大文字と小文字だけが違う別のファイルなので、接頭辞を G と K に分けた。`U1` などは、各ファイルの「Unverified candidates」を掲載順に採番したもので、S と C の番号は round 7 と同じである。Resolved findings も一覧に含める。複数のレビューが同じ問題を挙げていても省略せず、入力上の項目を 1 件ずつ数える。Test suggestions は対応する項目の検証案なので、別件には数えない。

| 区分 | ID 付き指摘 | 未検証候補 | 合計 |
| --- | ---: | ---: | ---: |
| 解消済み | 21 | 4 | **25** |
| 対応する | 4 | 0 | **4** |
| 判断保留 | 0 | 0 | **0** |
| 対応しない | 15 | 9 | **24** |
| 全件 | 40 | 13 | **53** |

「対応する」の 4 件（O-L11・P-H1・P-M1・K-M1）は、それぞれ別の修正項目 A〜D になる。4 件とも採用基準は **(a) 現行 HEAD で再現を確認した誤動作**である。

## 3. 検証方法と結果

ソースは `git show ce39425:<path>` で読んだ。再現は、`mktemp -d /tmp/review-fix-planning.XXXXXX` で作った一意な親ディレクトリの中に detached worktree を置いて行い、HEAD の完全な SHA が一致することを確かめた。プロダクトコードと既存テストは変更していない。追加したのは一時テストファイル `ApplyWorkflowTests.ReviewProbe.cs` だけである。テストの `TMPDIR` とログも同じ親ディレクトリの中に限定した。一時テストは、正しい挙動をアサートし、経過をログに書き出す形にした。つまり、失敗すれば再現したことになる。

| 証拠 | 内容 | 結果 |
| --- | --- | --- |
| E1 | `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter 'FullyQualifiedName~ApplyWorkflowTests'`（一時テストを含む） | 181 件中 174 件が成功した。**既存の 170 件はすべて成功**し、round 7 の回帰テスト（`ComponentRemovedFromARecreatingSlotLeavesIndexesAWorldReloadBinds` の 4 ケース、`MovingAKeyWhoseRecreateWasInterruptedLeavesSiblingIndexesAWorldReloadBinds`、`ComponentRemovedFromASlotLeavesIndexesAWorldReloadBinds` の 2 ケース）も含まれる。失敗した 7 件は、下の E2〜E6 で再現を確かめた一時テストである |
| E2 | O-L11: Rubble に同型の `renderer`（north、4 要素）と、その後ろに `old`（south、4 要素）を置いて apply する。次に、`old` を外して `renderer` を 3 要素にした文書を `--prune` なしで apply する（同じ apply で外す場合と、先の apply で外しておく場合の 2 通り） | どちらも apply は成功した。実際の配置は `[old, renderer']` なのに、state は `old`=1・`renderer`=1 だった。`ReloadWorld` のあとは、plan・`--prune` なしの apply・`--prune --yes` の apply のすべてが `APPLY_COMPONENT_OWNERSHIP_CONFLICT`（`renderer'` を `renderer/live` と `old/delete` が主張）で止まり、書き込みは 0 件だった。対照として `old` を `renderer` の前に置くと、再読込後の plan は `delete old` だけになり、apply の書き込みは 0 件、prune も成功した |
| E3 | O-L11 の作り直しが無い場合: Rubble に同型の `mover`・`old`・`tail` を置いて apply する。次に、`old` を外し（`--prune` なし）、`mover` を子 Slot の Debris へ移す | apply は成功した。実際の配置は `[old, tail]` なのに、state は `old`=1・`tail`=1 だった（`tail` は round 7 の処理で保存し直されるが、`old` は保存し直されない）。再読込後の apply は `APPLY_COMPONENT_OWNERSHIP_CONFLICT`（`tail/live` と `old/delete`）で止まった |
| E4 | P-H1: Rubble に `renderer`（4 要素）と `consumer`（`Test.Slider`、`"SnapPositions":{"LocalSpace":"$slot:root"}`）を置いて apply する。その後、`consumer.SnapPositions` を syncObject `{LocalSpace→Plaza, Offset, Target→renderer}` にしてから、`renderer` を 3 要素にする | plan・apply とも成功し（書き込み 2 件）、旧 `renderer`（C5）は削除された。ところが `consumer` の宣言外の `SnapPositions.Target` は C5 のままだった。対照として、`Target` の無い syncObject では成功し（正しい動作）、`{"Offset":1}` のようにシンボルの無い宣言では `APPLY_LIST_SHRINK_REFERENCED`・書き込み 0 件で止まった |
| E5 | P-M1: `renderer` に `"Target":"$ref:renderer"`（自己参照）を宣言し、4 要素で apply する。3 要素の apply で `LoseNextComponentCreateResponse` を立て、同じ文書・同じセッションで再実行する。相互参照（`renderer`↔`second`、両方を縮める）でも行う | 自己参照の場合、中断直後は `[C5(4 要素), C6(空)]` で、state は `renderer={id:"", supersededId:C5, referenceSelectors:{Target:$ref:renderer}}` だった。再実行は成功したが、配置は `[C6(空), C7(3 要素)]` になり、**C6 はどの state key からも追跡されない**。次の apply も書き込み 0 件で成功し、C6 は残ったままだった。相互参照の場合も、最後の配置は `[C7(空), C8, C9]` で C7 が管理外で残った。対照として `Target` が `$ref:m1` の場合は、再実行で C6 に束縛し、管理外の Component は残らなかった |
| E6 | K-M1: `renderer`（`"Target":"$ref:second"`）と `second` を同じ Slot に置き、両方を 4 要素から 3 要素にする。偽クライアントは、作成時に Label が south の Renderer だけ、リストを 1 要素長く埋め直す | apply は `APPLY_LIST_SHRINK_NOT_CONVERGED`（`removedReplacementId: C8`）で止まった。`renderer` の置換 C7 の `Target` は、削除済みの C8 を指したまま残った。state は `renderer={id:C7, supersededId:C5}` だった。同じ文書で再実行すると同じ停止を繰り返し（C9 を作って削除する）、C7 の参照は直らない |

Resonite 実機、ソリューション全体、ほかのプロジェクトのテストは実行していない。外部のワールドに対する操作もしていない。

検証用の `/tmp/review-fix-planning.7R8onU/worktree` は、`git worktree remove --force` が成功したあとに親ディレクトリごと削除した（15:26 JST ごろ、`/tmp/review-fix-planning*` が残っていないことを確認）。一時テストとログは残していない。再現の条件は本 Spec に記録している。

## 4. 全指摘の分類

`W` は現行 HEAD の `src/RLoop.Core/WorldService.cs`、`T` は `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`、`R` は `tests/RLoop.Tests/ApplyWorkflowTests.WorldReload.cs` を指す。行番号は `ce39425` 基準。`ce39425` で変わったのは W の削除 3 か所と `SaveIndexesAfterRemoving`（W:537–552）、plan 時点の index のコメントだけで、ほかの箇所は `0acf969` から変わっていない。テスト名で示した解消の根拠は、すべて E1 の対象に含まれ、成功している。

### O: Claude Opus（`ce39425`）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| O-L11 | 作り直す Component より後ろに prune 前の同型 key があると、再読込後の plan・apply が毎回 ownership conflict で止まる | 対応する | **(a)** E2・E3。index を保存し直す 3 か所（W:467–470、W:541–552、`UndoRecreateState`）は宣言された key だけを対象にしている。修正 A |
| O-L3 | 非同期の refill で、apply のたびに作り直しを繰り返す | 対応しない | W:515 で一度だけ観測する処理は変わっていない。実機の遅延 refill は未確認。作り直しの履歴の永続化は別の設計（round 7 と同じ） |
| O-I1 | recreate・停止コードの文書、`diff --deletes-only` に置換の削除が出ない | 対応しない | 文書は S-I1 と同じ。deletes-only の表示は relocate と共通の表示仕様（round 7 と同じ） |
| O-U1 | 空で作った置換を再開すると、フィールド設定前の検証が空振りする | 対応しない | W:509–515 は変わっていない。フィールドの設定をきっかけにした実機の refill は未確認（round 7 と同じ） |
| O-M1 | 作り直しで `initialFields`・未宣言 member が初期値に戻ることの記述の矛盾 | 解消済み | `docs/DECLARATIVE.md:57`、`README-DETAILS.md:181`、build skill の手順 6 に明記 |
| O-L1 | 取り消し時に sibling の index がずれる | 解消済み | `UndoRecreateState`。`UndoneRecreateKeepsSiblingIndexesSoAWorldReloadStillBindsThem` が成功 |
| O-L2 | 中断後に key を外して prune すると旧 Component が残る | 解消済み | W:1536–1548。`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` の 2 ケースが成功 |
| O-L4 | 作成前の中断で同型 sibling と ownership conflict | 解消済み | `HeldByOtherKeys`。`InterruptedRecreateNextToASameTypeSiblingResumes` などが成功 |
| O-L5 | 再読込後の復旧ヒントが成り立たない | 解消済み | `InterruptedRecreateAcrossSession`。`InterruptedRecreateNextToSameTypeSiblingsRecoversAfterWorldReloadByFollowingTheHint` の 5 ケースが成功 |
| O-L6 | 新しい key の作成応答を失うと重複して作る | 解消済み | W:1130 の `recreatedOnNode` の絞り込み。`ResumedCreateOfANewKeyNextToARecreateBindsWhatItCreated` の 2 ケースが成功 |
| O-L7 | sibling が 2 つあると、ヒントどおりに復旧したあと止まる | 解消済み | W:467–470。上記のヒント復旧の 5 ケースが成功 |
| O-L8 | `supersededId` の保存前に止まると sibling だけ final index になる | 解消済み | W:459–463。`ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` の 3 ケースが成功 |
| O-L9 | 保存 ID の無い key が、リストの長い管理外 Component を作り直す | 解消済み | `UnsavedMatchWithALongerList`。`InterruptedCreateOfANewKeyDoesNotRecreateAnUnmanagedComponentWithALongerList` の 2 ケースが成功 |
| O-L10 | recreate より前に処理した同型の新しい key が final index で保存される | 解消済み | `AtSavedLayout`。`NewKeyCreatedBeforeARecreateConvergesAfterWorldReload` の 3 ケースと `NewKeyCreatedBeforeAnInterruptedRecreateIsSavedAtItsFinalIndex` が成功 |

### P: GPT-6.1 Sol（`ce39425`）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| P-H1 | 入れ子の一部を宣言しただけで、宣言外の子参照も作り直しの安全チェックから外れる | 対応する | **(a)** E4。W:1370–1371 は、トップレベルの member の宣言にシンボルが 1 つでもあれば、その member の中の参照をすべて除外する。修正 B |
| P-M1 | 未適用の参照 topology が、応答を失った作り直しの置換を照合候補から外し、重複を残す | 対応する | **(a)** E5。作成前・作成後の checkpoint（W:485・493）は、実際には書いていない参照の selector を `CreateComponentState`（W:2055–2060）で保存する。修正 D |

### K: Grok 4.7（小文字、`ce39425`）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| K-M1 | 先に検証する recreate が、あとで削除される置換を参照したまま残る | 対応する | **(a)** E6。検証ループ（W:503–513）は、検証前にすべての置換を `byKey` へ入れてから、空で作った置換のフィールドを書く。**(b)** の性質もある: W:447–448 のコメント「置換は検証されるまで参照できない」は、置換どうしの参照では成り立たない。修正 C |

### G: Grok（大文字、`0acf969` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| G-H2 | recreate と同じ apply で Slot から外した Component を最終 index が数え、再読込後に止まり続ける | 解消済み | `ce39425` の `SaveIndexesAfterRemoving`（W:537–552）。`ComponentRemovedFromARecreatingSlotLeavesIndexesAWorldReloadBinds` の 4 ケースが成功 |
| G-H1 | recreate より前に保存した同型の新しい key が、再読込後に置換対象を奪う | 解消済み | `43c262a` の `AtSavedLayout`。`NewKeyCreatedBeforeARecreateConvergesAfterWorldReload` の 3 ケースが成功 |

### S: SWE（`0acf969` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| S-L1 | prune 予定の参照元も `APPLY_LIST_SHRINK_REFERENCED` に数える | 対応しない | W:1359–1361 は変わっていない。変更前に止まる安全側の動作で、停止条件の緩和は仕様の変更（round 7 と同じ） |
| S-L3 | 中断した recreate の relocate がさらに中断すると、置換が管理外で残る | 対応しない | 通常の relocate にもある、削除元の追跡（state が 2 つの ID しか持たない）の設計課題（round 7 と同じ） |
| S-I1 | action の列挙・停止コード・復旧手順の文書への追記 | 対応しない | 作り直しで値が戻ることは `docs/DECLARATIVE.md:57` に記載済み。残りは情報の追加。fork の AGENTS.md「Skills are workflows, not command mirrors」 |
| S-I2 | 偽クライアントの `SetFields` が裸の文字列で `JsonException` になる | 対応しない | 現行のテストで使わない入力。偽クライアントを一般化しない |
| S-I3 | relocate の再中断後、復旧候補に移動元の置換元が出ない | 対応しない | S-L3 と同じ設計課題。変更前に止まる |
| S-U1 | stale ID の key と空 ID の key の二重主張 | 対応しない | `RecreatedOnNode` は変わっていない。端から端までの再現は無く、ownership による停止を緩める根拠も無い |
| S-U2 | 空で作成して中断した Component に `initialFields` が適用されない | 対応しない | recreate 以前からある、作成の再開の仕様論点 |
| S-U3 | relocate+superseded・relocate の移動元・prune で、移動元の保存 index が削除を反映しない | 解消済み | `ce39425` の `SaveIndexesAfterRemoving`。`ComponentRemovedFromARecreatingSlotLeavesIndexesAWorldReloadBinds`・`MovingAKeyWhoseRecreateWasInterruptedLeavesSiblingIndexesAWorldReloadBinds`・`ComponentRemovedFromASlotLeavesIndexesAWorldReloadBinds` が成功。宣言外の key に残る同じ種類のずれは O-L11 として扱う |
| S-U4 | relocate の移動元の照合に `recreatedOnNode` の絞り込みが無い | 対応しない | W:1147–1150 は変わっていない。管理外の候補を含む、端から端までの再現が無い |
| S-U5 | 同じ Slot の 2 つの新しい recreate の間で中断すると、2 本目の束縛先を取り違える | 対応しない | round 7 の E6 で、3 系列とも変更前に止まり、ヒントどおりの復旧で収束した。関係するコードは変わっていない |
| S-U6 | 作成直後に実機が member を完全に返すか | 対応しない | 実機での不足は未確認。adapter を推測で直さない |
| S-L4 | `supersededId` 保存済みの recreate の再開で、sibling が現在の配置の index に戻る | 解消済み | W:459 の `!SavedFinalIndexes`。`ResumedRecreateStoppedAtASiblingKeepsItsFinalIndexAcrossWorldReload` の 2 ケースが成功 |
| S-M1 | NOT_CONVERGED の取り消しで、参照が削除済みの置換を指す | 解消済み | 非 recreate の参照元については W:449–450・492 で解消。`UndoneRecreateLeavesNoReferenceToTheRemovedReplacement` が成功。置換どうしの参照で残る穴は K-M1 として扱う |
| S-L2 | `supersededId` が残る Component の relocate・宣言削除で旧 Component が残る | 解消済み | `MovingAComponentWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent`・`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` が成功 |
| S-M2 | 作成前に中断した key の移動で、他の key の同型 Component を移動元として束縛する | 解消済み | `HeldByOtherKeys`。`InterruptedCreateOfANewKeyThatMovesIsCreatedOnTheNewSlot` が成功 |

### C: commandcode / DeepSeek（`0acf969` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| C-L1 | 置換元が削除済みでも再読込後に止まり、state の手編集が要る | 対応しない | W:1117–1122 は変わっていない。session-scoped の ID から削除済みと推定せずに止まる安全側の方針（round 7 と同じ） |
| C-I1 | `recreate` と 3 つのエラーコードが文書・スキルに無い | 対応しない | S-I1 と同じ |
| C-I2 | plan の Warnings に観測範囲の注意が無い | 対応しない | 停止時の suggestions と PR 本文に制限を記載済み。成功した plan への警告の追加は UX の改善 |
| C-I3 | 置換が無い key を prune すると、実在しない ID の key が state に残る | 対応しない | 実在しない対象の key を残すのは、通常の prune と同じ方針（round 7 と同じ） |
| C-U1 | recreate と relocate が同じ Slot にあると、relocate 側の index が補正されない | 対応しない | round 7 の E5 で、宣言順の 2 通りとも index が一致し、再読込後に収束した。関係するコードは変わっていない |
| C-U2 | 置換元を失う移動元 Slot の sibling の index を保存し直さない | 解消済み | `ce39425`。`MovingAKeyWhoseRecreateWasInterruptedLeavesSiblingIndexesAWorldReloadBinds` が成功 |
| C-U3 | 管理外 Component の証拠一致で宣言値を書き込む・`id` の欠けた state で held が効かない | 対応しない | D-H1 と共通の採用方針。公式の writer は `id` を空文字以上で保存し、欠けた state が入る経路は未確認 |
| C-U4 | 中断した create の key を recreate の apply で宣言せず、同じセッションで再宣言すると誤束縛する | 対応しない | round 7 と同じ。apply と apply の間の文書編集が前提で、宣言されない key は ID も Component も分からない。修正 A も、ID で追跡できない key には適用しない |
| C-H1 | held 候補の除外で index がずれ、管理外 Component を採用する | 解消済み | `MatchComponent` の held。`ResumedRecreateBindsItsReplacementNextToAnUnmanagedSameTypeComponent` などが成功 |
| C-H2 | 位置で採用した管理外 Component を refill の取り消しで削除する | 解消済み | W:519–521 の `matchedByPosition`。`UndoneRecreateKeepsAReplacementMatchedWithoutItsSavedId` の 2 ケースが成功 |

### D: DeepSeek（`485e508` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| D-H1 | 作成が実行されなかった recreate の再開で、管理外の同型 Component を採用する | 対応しない | 位置照合による採用方針は変わっていない。応答喪失による正当な再開と区別するには、証拠と停止方針の変更が要る（round 6 でユーザーが承認した据え置き） |
| D-M1 | 中断後の並び替えで管理外 Component を採用し、本来の置換が孤立する | 対応しない | D-H1 と同じ位置照合の設計課題。実機で先頭に挿入できるかは未確認 |
| D-U1 | 連続した中断で current / final の index が混ざる | 解消済み | S-L4 と同じ。`ResumedRecreateStoppedAtASiblingKeepsItsFinalIndexAcrossWorldReload` が成功 |

### Q: Qwen（`616c510` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| Q-L1 | 空の fields で作った置換を再開すると、refill の検証が空振りする | 対応しない | O-U1 と同じ |
| Q-I2 | relocate の移動元 Slot の sibling の index が削除前の位置で保存される | 解消済み | `ce39425`。`ComponentRemovedFromASlotLeavesIndexesAWorldReloadBinds` の 2 ケースと、C-U2 のテストが成功 |
| Q-U1 | 作成ループの前に一括で final を保存すると停止の窓ができる | 解消済み | 一括の保存は `485e508` で廃止。`ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` の 3 ケースが成功 |
| Q-M1 | 中断した recreate の移動で、新旧どちらかが孤立する | 解消済み | S-L2 と同じ |
| Q-M2 | 再開時に refill の検証を飛ばして旧 Component を削除する | 解消済み | W:503–515。`ResumedRecreateThatTheRuntimeRefilledStopsAndKeepsTheOriginal` が成功 |
| Q-I1 | 停止コードの文書不足（原レビューでは解消扱い） | 対応しない | round 7 と同じ。値のリセットの記述の矛盾は解消済みで、停止コードの一覧などは情報の追加 |

## 5. 修正方針

A〜D は互いに独立しているので、それぞれ回帰テストを先に追加し、`ce39425` で失敗することを確かめてから実装する。

### A. 宣言から外した key の保存 index も、Component を外すたびに合わせる（O-L11）

対応 ID: **O-L11**、基準 **(a)**。

原因: 保存 index を配置に合わせて保存し直す処理は 3 か所ある。最初の `supersededId` の checkpoint（W:467–470）、削除のたびの `SaveIndexesAfterRemoving`（W:541–552）、取り消し時の `UndoRecreateState` である。3 か所とも、文書に宣言された key（`prepared.Components`）だけを対象にしている。文書から外して `--prune` なしで apply した key は state に残る（README とスキルが案内する通常の手順）。再読込後、`BuildDeletionPlans`（W:1550–1556）は prune の有無にかかわらず、この key を保存 index で照合して削除候補にする。そして `ValidateComponentOwnership`（W:1581–1600）がこの削除候補も所有権の検査に含める。作り直しでは置換が Slot の末尾に追加されるので、置換元より後ろにある宣言外の key の古い index は、ちょうど置換を指す。そのため plan・apply・`--prune --yes` のどれも止まり続ける（E2）。作り直しが無くても、前の Component を relocate で外すと同じずれが起き、後ろに同型の宣言された key があれば止まる（E3）。

方針:

- 静的なヘルパーを 1 つ追加する（例: `SaveUndeclaredIndexes(prepared, node, removed)`）。`AssignComponentIndexes` と同じ `kept`（Slot の Component から `removed` を除いた並び）を作り、その Slot（`SlotKey == node.StableKey`）にある宣言外の state key の `componentIndex` を、`kept` の中での位置で保存し直す。
- 宣言外の key の Component は、`prepared.Deletions` のうち、その key の Component 削除（`Kind == "component"`、`Id != SupersededId`）の ID で特定する。同じセッションでは保存 ID で、別セッションでは証拠で、変更の前に照合した結果である。別セッションでは state の ID が古いので、ID は state から取らない。ワールドを再読込したあとに作り直しの apply をする、という一般的な流れを扱うためである。
- 照合できなかった key（ID の無い key、C-U4）と、Component がすでに削除された key は、そのままにする。
- 呼ぶ場所は、宣言された key の index を保存し直す 3 か所で、`removed` にも同じ集合を渡す。
  1. 最初の `supersededId` の checkpoint（W:467–470）: その Slot の recreate の置換元（plan 時点の `AssignComponentIndexes` と同じ集合）
  2. `SaveIndexesAfterRemoving`（W:541–552）: ここまでの削除と、その Slot でまだ残っている置換元
  3. `UndoRecreateState`: 取り消し時と同じ集合。1 で final に変換したものを、取り消し後の配置に戻す
- どの場所もあとに既存の checkpoint があるので、checkpoint は増やさない。
- E3 の、作り直しの無い relocate にも同じ処理が働く。PR 以前からある種類のずれだが、原因と修正箇所が同じなので、round 7 の Q-I2 と同じく、条件を分けずにまとめて直す。

検証:

- T に Theory を追加する。`renderer` の後ろに同型の `old` を置き、`old` を外して（`--prune` なし）`renderer` を縮める。ケースは (1) 同じ apply で外す、(2) 先の apply で外しておく、(3) (2) のあと作り直しの apply の前に `ReloadWorld` する（別セッションでの作り直し）の 3 通り。apply 直後に `old` の保存 index が実際の位置と一致すること。`ReloadWorld` のあと、plan の変更が `delete old` だけであること、`--prune` なしの apply の書き込みが 0 件であること、`--prune --yes` が `old` の Component だけを削除し、`renderer` の state が置換を指すこと。
- T に、取り消しの場合を追加する。`RefillRenderers` で `APPLY_LIST_SHRINK_NOT_CONVERGED` になったあと、`old` の保存 index が実際の位置と一致し、再読込後の plan の変更が `delete old` だけであること。
- R に、E3（作り直しの無い relocate）の構成で、再読込後の apply が書き込み 0 件で成功することを追加する。

### B. 作り直しの参照の検査を、宣言した子の位置ごとに行う（P-H1）

対応 ID: **P-H1**、基準 **(a)**。

原因: `ValidateRecreateReferences` の `Check`（W:1366–1374）は、トップレベルの member の中にある参照を `ReferenceTargets` で入れ子までまとめて集める。そして、所有者の管理 Component がその member 名を宣言し、宣言のどこかにシンボルがあれば（`ContainsWorldReference(declared)`）、中の参照をすべて除外する。一方、syncObject の部分宣言は、宣言した子だけを比較して書き込む（`MemberMatchesRaw` W:1828–1840、既存テスト `PartialNestedReferencesConvergeAndStillDetectDrift` の方針）。そのため、宣言していない子の参照は張り替えられないのに検査も通り、apply は参照先を削除して成功する（E4）。

方針:

- `Check` で、観測した member と宣言した JSON を同じ位置で対応付けながらたどる。
  - reference: 同じ位置の宣言があり、そこにシンボルがある（`ContainsWorldReference`）ときだけ、張り替えられるとみなして除外する。
  - syncObject / dictionary の子: 宣言のオブジェクトの同じ名前のプロパティと対応付ける。宣言が無ければ、対応なしとする。
  - list の要素: 宣言の配列の同じ index の要素と対応付ける。
- トップレベルの reference member をシンボルで宣言した場合の扱い（除外）は変えない。管理外の Component と Slot の member は、これまでどおりすべて違反に数える。
- 入れ子の参照は、同じ位置にシンボルの宣言が無ければ違反になる。今より保守的になるだけで、今止まっているものが通るようにはならない。エラーコード・context のキー・suggestions は変えない（`member` はトップレベルの名前のまま）。

検証:

- T に Theory を追加する。(1) E4 の構成（部分宣言と、宣言外の `Target`）で、plan と apply が `APPLY_LIST_SHRINK_REFERENCED`・書き込み 0 件で止まり、旧 `renderer` と `consumer` と state が変わらないこと。(2) `SnapPositions` の宣言に `"Target":"$component:renderer"` も入れると、止まらずに成功し、`consumer` への書き込みが置換の ID を含むこと。(3) 入れ子に `renderer` への参照が無ければ、これまでどおり成功すること。
- 既存の `PartialNestedReferencesConvergeAndStillDetectDrift` と、参照の検査に関する既存のテストを維持する。

### C. 検証の終わっていない置換を、ほかの置換から参照させない（K-M1）

対応 ID: **K-M1**、基準 **(a)**（W:447–448 のコメントについては (b) も満たす）。

原因: 検証ループ（W:503–505）は、refill の検証を始める前に、検証する置換をすべて `byKey` に入れる。そのあと、空で作った置換（`CanResolveAll` が偽だったもの）は、作成時のフィールドを解決して書き込んでから検証する（W:509–513）。宣言順で先の置換が後の置換を参照していると、後の置換の ID が先の置換に書き込まれる。その後、後の置換が検証で止まると、置換は削除されて state は元に戻るが（W:516–523）、先の置換に書いた参照は戻らない。state は先の key を、その置換と `supersededId` で追跡したままになる（E6）。W:447–448 のコメントは「置換は検証されるまで参照できない」としているが、置換どうしの参照では成り立っていない。

方針:

- 検証ループの前に置換を `byKey` へ入れるのをやめ、すべての置換が検証を通ったあとで入れる。
- 空で作った置換の検証では、作成時のフィールドのうち、その時点の `byKey` で解決できるもの（`CanResolve`）だけを書き、`AppliedOnCreate` にもその分だけを記録する。置換への参照（自分自身への参照を含む）は、ここでは書かない。
- 残りのフィールドは、既存のフィールドのループが書く。このループの `changed` は `AppliedOnCreate` との差を書くので、変更は要らない。このループはすべての検証が通ったあとに走るので、削除される置換を参照することはない。
- W:447–448 のコメントを、置換どうしの参照も含む書き方に直す。
- 残る制限: 置換への参照を書いたことがきっかけで runtime がリストを埋め直す場合、その apply では検出できない（次の apply で `APPLY_LIST_SHRINK_NOT_CONVERGED` になる）。フィールドの設定をきっかけにした refill は、O-U1・Q-L1 と同じく実機で未確認なので、この Spec では扱わない。

検証:

- T に追加する。(1) E6 の構成で `APPLY_LIST_SHRINK_NOT_CONVERGED` になったあと、`renderer` の置換の `Target` が `removedReplacementId` を指さないこと。そのあと `second` を 4 要素に戻した文書で apply すると、`renderer` の置換の `Target` が `second` の Component を指して収束し、次の apply の書き込みが 0 件であること。(2) refill の無い成功の経路で、`renderer` の置換の `Target` が `second` の置換を指し、次の apply の書き込みが 0 件であること。
- 既存の `UndoneRecreateLeavesNoReferenceToTheRemovedReplacement` を維持する。

### D. 書いていない参照を、作成中の Component の照合条件にしない（P-M1）

対応 ID: **P-M1**、基準 **(a)**。

原因: 作成前（W:485）と作成後（W:493）の checkpoint は `CreateComponentState` を使う。この関数は、作成時にフィールドを書いたかどうかに関係なく、宣言にある参照の selector を `referenceSelectors` に保存する（W:2055–2060）。置換は検証前には参照できないので（W:449–450）、自分自身や別の置換を参照する置換は、フィールドを設定せずに作られる。その作成応答を失うと、state は `{id:"", supersededId, referenceSelectors}` になる。再実行では `BuildComponentPlans` がこの selector から topology を解決し（W:1107–1108）、旧 Component を指す。`StableComponentCandidates` は、その参照を持たない（まだ書いていない）置換を候補から外す（W:2025–2028）。候補が無いので未作成として扱われ、置換をもう 1 つ作る。先に作った置換は管理外のまま残り、以後の apply も書き込み 0 件で成功するので、自動では直らない（E5）。

方針:

- `CreateComponentState` で、この apply で作る Component（`Existing is null`）のフィールドをまだ書いていないとき（`resolvedFields is null`、つまり作成前・作成後の checkpoint）は、`AppliedOnCreate` にある member の selector だけを `referenceSelectors` に保存する。フィールドを設定せずに作った場合は保存しない。
- フィールドのループの checkpoint（`resolvedFields` あり）では、これまでどおりすべて保存する。束縛済みの Component（`Existing` あり）の扱いも変えない。state の形式は変えない。
- これにより、応答を失った置換は、型・member 名・index で照合される。参照先が作り直されない場合（E5 の対照）と同じ扱いになる。作成が実行されなかったときに、保存 index の位置にある管理外の同型 Component を採用しうるのは、D-H1 として据え置いている既存の制限と同じで、それより広がることはない。
- 自分自身を参照する通常の新規 Component の作成応答を失った場合も、同じ理由で重複していたはずで、この変更で同じく直る（この経路の再現は未実施。回帰テストの対象にもしない）。

検証:

- T に Theory を追加する（自己参照・相互参照）。3 要素の apply で作成応答を失わせ、同じ文書・同じセッションで再実行する。Rubble の `Test.Renderer` の数が宣言した数と一致し、すべての Renderer を state の key が追跡していること、最初に作られた置換が再利用されること、次の apply の書き込みが 0 件であること。
- 修正 C のあとも E5 の構成は、置換がフィールドを設定せずに作られる経路のままであることを、テストの前提として確かめる。

## 6. 対象ファイル・非対象・互換性

実装予定のファイル（fork のルート基準）:

- `src/RLoop.Core/WorldService.cs`: 修正 A〜D。
- `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`: A〜D の回帰テスト。
- `tests/RLoop.Tests/ApplyWorkflowTests.WorldReload.cs`: A の、作り直しの無い relocate の回帰テスト。

変更しないもの:

- 永続 state の形式、公開 CLI / API、エラーコードと context のキー、plan の表示。
- 位置照合による採用方針（D-H1・D-M1・C-U3）、ID の無い宣言外の key の index（C-U4）、relocate の削除元の追跡と復旧候補の範囲（S-L3・S-I3）、prune 予定の参照元での停止（S-L1）。
- 非同期 refill・フィールドの設定による refill（O-L3・O-U1・Q-L1）、adapter の推測による修正、文書の追記。
- すでに保存された、ずれた index を推測で直す移行処理。修正前の apply で保存された宣言外の key の index は、そのまま残る。

削除と、その直後の checkpoint の間で強制終了した場合は、round 7 と同じく、その 1 件の削除だけ index がずれたまま残る。

## 7. 承認後の検証・既存 PR への反映

1. 作業ツリー `external/resoloop/.worktrees/fix-list-shrink-recreate` の HEAD と `origin/fix/list-shrink-recreate` が `ce39425` で一致することを確かめる。
2. A〜D の回帰テストを先に追加し、`ce39425` で期待どおり失敗することを確かめる。一時テストの「経過をログに書くだけ」の形を、そのまま恒久テストにしない。
3. A〜D を実装し、追加したテストと `--filter 'FullyQualifiedName~ApplyWorkflowTests'` を実行する。
4. 変更したプロジェクトに関連する検証として `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` を実行する。失敗している間は commit しない。実機への接続、関係の無いワールドのテスト、fork 全体の一括テストは条件にしない。
5. `git fetch origin` で PR の HEAD を確認し直す。根拠にした SHA から更新があれば、関係する部分を確認し直す。
6. `fix/list-shrink-recreate` へ commit し、`origin` へ push する。main、追加の review-fixes ブランチ、新しい PR には載せない。
7. モデル識別子 `claude-opus-5-5` で、TOPLEVEL 側の `upsert_pr_comment.py` を使い、PR #5 の自エージェントのコメント（マーカー `review-fix-planning:agent:claude-opus-5-5`）を更新する。他のエージェントのコメントは編集しない。

計画のターンでは、PR コメントの投稿・commit・push をしていない。

## 8. 作業時間

担当: このセッション（Claude Code、claude-opus-5-5）。2026-09-30 15:17 JST ごろに着手。

- Task 1–2: レビューディレクトリの特定、全 8 ファイルの読解、PR・remote・HEAD・既存の PR コメント・round 7 Spec の確認: 約 5 分
- Task 3: コミット済みのコードの読解、一時テスト 11 件の作成、`ApplyWorkflowTests` 181 件の実行、撤去: 約 5 分
- Task 4–6: 分類、bounded の設計、Spec の作成と一覧の照合: 約 6 分
- 合計: 約 16 分。テストは同期実行し、終了コードを確かめてから撤去した。

サブエージェントは使用していない（ユーザーの明示的な依頼が無いため）。

## 9. 承認後の実装と反映（2026-09-30、Claude Code）

- 経路は bounded のまま、実装計画の文書は作らずにこのセッションで実装した（サブエージェントは使用していない）。作業ツリーは `external/resoloop/.worktrees/fix-list-shrink-recreate`。
- A〜D ごとに、回帰テストを先に追加して修正前の HEAD で失敗することを確かめ、実装してから commit した。
  - A（`1ac2692`）: `UndeclaredKeyOnARecreatingSlotKeepsAnIndexAWorldReloadBinds`（3 ケース）、`InterruptedRecreateSavesAnUndeclaredKeyAtTheIndexTheReloadHintLeaves`、`UndeclaredKeyLeftOnASlotAComponentMovesOffKeepsAnIndexAWorldReloadBinds`（R）の 5 件が `ce39425` で保存 index の不一致（期待 0・実際 1）で失敗した。`UndoneRecreateKeepsAnUndeclaredKeyIndexAWorldReloadBinds` は、最初の `supersededId` の checkpoint で変換した index を取り消しで戻すことを確かめる回帰ガードで、`ce39425` でも成功する。
  - B（`2c324e3`）: `ListShrinkChecksEachNestedReferenceAgainstItsOwnDeclaredChild` の `undeclared-child` が「例外が出ない」で失敗した。`declared-child`・`no-reference` は、止めすぎないことを確かめるケースで、修正前も成功する。
  - C（`d53613f`）: `UndoneRecreateLeavesNoOtherReplacementReferencingTheRemovedOne` が、削除済みの置換（C8）を参照していることで失敗した。`RecreateReferencingAnotherRecreateTargetsItsReplacement` は成功の経路の回帰ガード。
  - D（`555338e`）: `ResumedRecreateCreatedWithoutItsReferencesBindsWhatItCreated`（`self`・`mutual`）が、Renderer が 1 つ多い（期待 1・2、実際 2・3）ことで失敗した。
- 実装の要点
  - A: 静的ヘルパー `SaveUndeclaredIndexes` を追加し、最初の `supersededId` の checkpoint、`SaveIndexesAfterRemoving`、`UndoRecreateState` から、宣言された key と同じ `removed` で呼ぶ。`kept` の計算は `KeptComponentIds` にまとめ、`AssignComponentIndexes` と共有した。
  - B: `ValidateRecreateReferences` の `ReferenceTargets` を、宣言の JSON と同じ位置を対応付けてたどる `References` に置き換えた。
  - C: 検証ループの前に置換を `byKey` へ入れる処理を、ループの後ろへ移した。空で作った置換の検証前の書き込みは、`CanResolve` で解決できるフィールドだけにした（空なら書き込まない）。
  - D: `CreateComponentState` で、この apply で作る Component のフィールドを書く前は、`AppliedOnCreate` にある member の selector だけを保存する。
- 検証（`555338e`、TMPDIR はセッションの scratchpad に隔離、実機の Resonite には接続していない）
  - `--filter 'FullyQualifiedName~ApplyWorkflowTests'`: 183 件成功（既存 170 件と追加 13 件）、ビルド警告なし
  - `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj`: 395 件成功（従来の 382 件と追加 13 件）、ビルド警告なし
- commit / push: `git fetch origin` で PR の先端が `ce39425` のままであることを確かめてから、4 commit を `fix/list-shrink-recreate` へ push した（`ce39425..555338e`）。
- 範囲外の観察（対応していない）: 別セッションの apply は、宣言外の key の保存 ID を更新しない。そのため、再読込後に `--prune` なしで apply したあと、同じセッションで `--prune --yes` を実行しても、その key の Component は保存 ID で見つからず、削除されない（E2 の対照の一時テストで観察）。PR 以前からの prune の挙動で、今回のレビューの指摘には含まれない。A の回帰テストは、再読込の直後に `--prune --yes` を実行して確かめている。
- 作業時間: 承認後の実装から反映まで約 15 分（15:34〜15:49 JST ごろ）。内訳は A 約 6 分、B 約 3 分、C 約 3 分、D 約 2 分、全体テストと push 約 1 分。
