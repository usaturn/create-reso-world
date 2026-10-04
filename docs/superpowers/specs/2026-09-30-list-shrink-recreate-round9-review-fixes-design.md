# PR #5: 再読込後の宣言外の key の ID・フィールド無しで作った置換の再開時の検証の修正（round 9）

- 状態: **保留（レビュー修正の打ち切り）**。2026-09-30 にユーザーがレビュー修正の打ち切りを決めたため、実装しない。根本対策は https://github.com/usaturn/create-reso-world/issues/5 で扱う（§9）
- 作成日: 2026-09-30
- brainstorming 経路: **bounded**。`WorldService.cs` の既存の処理 2 か所（`ApplyAsync` の最初の checkpoint の前と、recreate の検証ループ）、偽クライアントのフック 1 つ、回帰テストに限定する。永続 state の形式、公開 CLI / API、エラーコード、plan の表示は変えない。review-fix-planning の指定により、bounded でも Spec を保存する。
- 対象 PR: https://github.com/usaturn/resoloop/pull/5 （OPEN、base は `fix/asset-url-save-migration`）
- 対象 branch: `fix/list-shrink-recreate`（作業ツリー `external/resoloop/.worktrees/fix-list-shrink-recreate`、HEAD `555338e`、未コミット変更なし）
- PR_REPO: `usaturn/resoloop`
- TOPLEVEL: `/workspaces/reso-world`
- MAIN_ROOT: `/workspaces/reso-world/external/resoloop`
- 検証 HEAD: `555338e10bf1ae0ac76473406f3c23d6729b78a3`（`git fetch origin` 後の `origin/fix/list-shrink-recreate` と PR の headRefOid が一致）
- fork remote: origin=`usaturn/resoloop`、upstream=`orange3134/resoloop` を確認済み。

## 1. 目的・範囲・進行状況

レビューの指摘を現行 HEAD（`555338e`）で検証し、再現した誤動作だけを修正の対象にする。成功条件は次の 2 つ。

1. ワールドを再読込したあとに一度 apply し、同じセッションで作り直しの apply をしても、次の再読込後の plan・apply は止まらずに収束する。
2. フィールドを設定せずに作った置換を再開したときも、初回の apply と同じく、フィールドを書いたあとの置換を検証する。フィールドを書いたことで runtime がリストを宣言より長くする場合は、元の Component を削除せずに `APPLY_LIST_SHRINK_NOT_CONVERGED` で止まる。

入力はレビューディレクトリだけである。round 7・8 の判断は PR コメント（review-fix-planning）と round 8 Spec の記述を参照した。ただし、解消したかどうかの根拠には、今回確認したコミット済みのコードと実行結果だけを使った。

- [x] PR URL から唯一のレビューディレクトリを確定し、全 8 ファイルを読む
- [x] リポジトリ境界と現行 HEAD を確認する
- [x] コミット済みのコードと隔離 worktree で検証し、worktree を撤去する
- [x] 全指摘を 4 区分へ分類する
- [x] brainstorming で bounded と判定し、修正方針を整理する
- [x] Spec を保存し、一覧・件数・根拠を照合する
- [x] ユーザーの判断を受ける（承認ではなく、レビュー修正の打ち切り。§9）

## 2. 入力と集計単位

入力ディレクトリ: `external/resoloop/reviews/#5-fix-list-shrink-recreate/`

| 接頭辞 | 読んだファイル | 冒頭の対象 HEAD | 文書内のレビュー履歴 |
| --- | --- | --- | --- |
| O | `claude-opus-5-5.md` | `555338e10bf1` | `d615eeb` → … → `ce39425` → `555338e` |
| K | `grok-4.7.md`（小文字） | `555338e10bf1` | `ce39425` → `555338e` |
| Q | `qwen3.8-max.md` | `555338e10bf1` | `d615eeb` → … → `616c510` → `555338e` |
| C | `commandcode-deepseek-deepseek-v4.1-flash.md` | `555338e10bf1` | `d615eeb` → … → `0acf969` → `555338e` |
| P | `gpt-6.1-sol.md` | `ce39425a2d02` | `ce39425`（Initial、round 8 から更新なし） |
| G | `Grok-4.7.md`（大文字） | `0acf96985f20` | `485e508` → `0acf969`（round 7 から更新なし） |
| S | `SWE-2-Max.md` | `0acf96985f20` | `d615eeb` → … → `0acf969`（round 7 から更新なし） |
| D | `deepseek-deepseek-v4.1-flash.md` | `485e508e8c65` | `616c510` → `485e508`（round 6 から更新なし） |

`Grok-4.7.md` と `grok-4.7.md` は大文字と小文字だけが違う別のファイルなので、接頭辞を G と K に分けた（round 8 と同じ）。`U1` などは、各ファイルの「Unverified candidates」を掲載順に採番したものである。C のファイルは今回番号を振り直しているので、C-U2 は round 8 の C-U4 に当たる（C-U1・C-U3 は round 8 と同じ内容）。Q の前回の未検証候補（Q-U1）は、Q のファイルが「解消を確認した」と本文に記載しているので、一覧に含める。Resolved findings も一覧に含める。複数のレビューが同じ問題を挙げていても省略せず、入力上の項目を 1 件ずつ数える。Test suggestions は対応する項目の検証案なので、別件には数えない。

| 区分 | ID 付き指摘 | 未検証候補 | 合計 |
| --- | ---: | ---: | ---: |
| 解消済み | 25 | 3 | **28** |
| 対応する | 3 | 2 | **5** |
| 判断保留 | 0 | 0 | **0** |
| 対応しない | 14 | 8 | **22** |
| 全件 | 42 | 13 | **55** |

「対応する」の 5 件は 2 つの修正項目になる。O-L12 が修正 A、K-H1・K-U1・O-U1・Q-L1 が修正 B である。5 件とも採用基準は **(a) 現行 HEAD で再現を確認した誤動作**で、K-H1 は **(b)**（検証ループのコメントの事実誤認）も満たす。

**round 8 からの判断の変更:** O-U1・Q-L1 は、round 7・8 で「フィールドの設定をきっかけにした実機の refill は未確認」として対応しないとしていた。今回は「対応する」に移す。理由は次の 3 つ。

- 初回の apply では、フィールド無しで作った置換に、検証の前にフィールドを書いている（W:514–522）。つまり、フィールドを書いたことで runtime がリストを埋め直す場合に備えた検証は、すでに実装の前提になっている。再開した場合だけ、その書き込みを飛ばしている。
- 検証ループのコメント（W:506–509）は「中断した apply が作った置換も検証する」「フィールド無しで作った置換には、検証の前にフィールドを書く」としているが、再開した置換では後者が成り立たない（(b)）。
- 中断が無くても入る経路を確認した（§3 の E4）。同じ apply の先の作り直しが `APPLY_LIST_SHRINK_NOT_CONVERGED` で止まると、後の置換はフィールド無しのまま `supersededId` 付きで残る。停止時の案内どおりに先の key の要素数を直して再実行すると、後の key の元の Component が削除される。

非同期の refill（O-L3）は、これまでどおり対応しない。

## 3. 検証方法と結果

ソースは `git show 555338e:<path>` で読んだ。再現は、`mktemp -d /tmp/review-fix-planning.XXXXXX` で作った一意な親ディレクトリの中に detached worktree を置いて行い、HEAD の完全な SHA が一致することを確かめた。プロダクトコードは変更していない。一時的に変えたのは次の 2 つだけである。

- 偽クライアント（`ApplyWorkflowTests.cs`）の `SetComponentMembersAsync` に、書き込んだあとに呼ぶフック `AfterMembersSet` を 1 行追加した。フィールドを書いたときに runtime がリストを埋め直す挙動（例: 設定した mesh からリストの長さが決まる）を模すためである。既存の `AfterComponentAdded` は作成時にしか呼ばれない。
- 一時テストファイル `ApplyWorkflowTests.ReviewProbe.cs` を追加した。フックは「`Test.Renderer` の指定したリスト member が書かれたら、要素数を 4 にそろえる」とした。

テストの `TMPDIR` とログも同じ親ディレクトリの中に限定した。一時テストは正しい挙動をアサートし、経過をログに書き出す形にした。つまり、失敗すれば再現したことになる。

| 証拠 | 内容 | 結果 |
| --- | --- | --- |
| E1 | `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter 'FullyQualifiedName~ApplyWorkflowTests'`（一時テストを含む） | 189 件中 186 件が成功した。**既存の 183 件はすべて成功**し、round 8 の回帰テスト（`UndeclaredKeyOnARecreatingSlotKeepsAnIndexAWorldReloadBinds` の 3 ケース、`ListShrinkChecksEachNestedReferenceAgainstItsOwnDeclaredChild` の 3 ケース、`UndoneRecreateLeavesNoOtherReplacementReferencingTheRemovedOne`、`ResumedRecreateCreatedWithoutItsReferencesBindsWhatItCreated` の 2 ケースなど）も含まれる。失敗した 3 件は E2・E3 で再現を確かめた一時テストである（成功した 3 件はその対照）。E4・E5 の一時テスト 4 件は、そのあと同じ worktree で個別に実行した（再現 3 件が失敗、切り分けられなかった構成 1 件が成功） |
| E2 | O-L12: 既存のヘルパー `DropOldAfterRendererAsync(dropNow: true)`（同型の `renderer` と後ろの `old` を apply し、`old` を外して `--prune` なしで apply）→ `ReloadWorld` → `renderer` 4 要素の文書で apply → 同じセッションで 3 要素の文書を apply → `ReloadWorld` | 3 要素の apply の直後、配置は `[C12(south = old), C13(north = renderer')]` なのに、state は `old={id:C6, componentIndex:1}` だった。`C6` は再読込前の ID で、実際の位置は 0。途中の 4 要素の apply（`sessionId` は新しいセッションになった）が `old` の ID を更新しないため、同じセッションの作り直しで `old` の削除計画ができず（W:1596）、`SaveUndeclaredIndexes`（W:1339–1349）が保存し直さない。再読込後は、plan も `--prune --yes` の apply も `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で止まった。対照として、途中の apply をせずに再読込後すぐ 3 要素で apply すると、`old` の保存 index は 0 で一致し、再読込後の plan・prune とも成功した |
| E3 | K-H1・K-U1: Rubble に `renderer` と `second` を置き、互いに `Target` で参照させる（`$ref:second` / `$ref:renderer`）。4 要素で apply したあと、3 要素の apply を 3 回目の書き込み（検証の前のフィールドの書き込み）で失敗させ、フックを有効にして同じ文書で再実行する。リスト member は、参照のリスト `Materials` と、数値のリスト `Weights`（`ListMembers` に追加）の 2 通り | 中断の直後は `[C5(4), C6(4), C7(空), C8(空)]`、state は `renderer={id:C7, supersededId:C5}`・`second={id:C8, supersededId:C6}` だった。再実行すると、`Materials` は `APPLY_REFERENCE_NOT_RETAINED` で止まり、`[C7(4), C8(4)]` が残って元の `C5`・`C6` は削除され、`supersededId` も消えた。`Weights` は **apply が成功**し、元の Component は削除され、置換のリストは 4 要素のままだった。次の apply で初めて `APPLY_LIST_SHRINK_NOT_CONVERGED` になった。対照として、中断せずに同じフックで apply すると、どちらのリストも `APPLY_LIST_SHRINK_NOT_CONVERGED` で止まり、元の Component は残った |
| E4 | 中断の無い経路: E3 と同じ構成で、最初からフックを有効にして 3 要素で apply する。そのあと、停止時の案内どおり `renderer` だけを 4 要素に戻し、`second` は 3 要素のまま再実行する | 最初の apply は `renderer` の検証で `APPLY_LIST_SHRINK_NOT_CONVERGED` になり、`renderer` は元に戻ったが、`second` はフィールド無しの置換 `C8` と `supersededId:C6` のまま残った。再実行すると、`second` の元の `C6` が削除された。`Materials` は `APPLY_REFERENCE_NOT_RETAINED`、`Weights` は成功（置換のリストは 4 要素）だった |
| E5 | 作成応答を失う経路（位置での照合）: `renderer` に自己参照（`"Target":"$ref:renderer"`）を宣言し、4 要素で apply する。3 要素の apply で `LoseNextComponentCreateResponse` を立て、フックを有効にして同じ文書で再実行する | 中断の直後は `[C5(4), C6(空)]`、state は `renderer={id:"", supersededId:C5}` だった。再実行は `C6` を位置で照合し、フィールドを書かずに検証を通したあと、元の `C5` を削除して `APPLY_REFERENCE_NOT_RETAINED` で止まった（残ったのは `C6(4)`）。なお、互いに参照する 2 つの構成では、もう一方の新しい置換の検証が先に止まったため、この経路を切り分けられなかった |

Resonite 実機、ソリューション全体、ほかのプロジェクトのテストは実行していない。外部のワールドに対する操作もしていない。

検証用の `/tmp/review-fix-planning.C7ym8i/worktree` は、`git worktree remove --force` が成功したあとに親ディレクトリごと削除した（16:40 JST ごろ、`/tmp/review-fix-planning*` が残っていないことを確認）。一時テストとログは残していない。再現の条件は本 Spec に記録している。

## 4. 全指摘の分類

`W` は現行 HEAD の `src/RLoop.Core/WorldService.cs`、`T` は `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`、`R` は `tests/RLoop.Tests/ApplyWorkflowTests.WorldReload.cs` を指す。行番号は `555338e` 基準。テスト名で示した解消の根拠は、すべて E1 の対象に含まれ、成功している。

### O: Claude Opus（`555338e`）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| O-L12 | 再読込後に一度 apply してから同じセッションで作り直すと、宣言外の key の index が保存し直されず、次の再読込後に止まり続ける | 対応する | **(a)** E2。別セッションの apply は宣言外の key の保存 ID を更新しない。修正 A |
| O-L3 | 非同期の refill で、apply のたびに作り直しを繰り返す | 対応しない | 検証は置換の作成直後に 1 回だけ行う（W:523）。実機の遅延 refill は未確認で、作り直しの履歴の永続化は別の設計（round 7・8 と同じ） |
| O-I1 | recreate・停止コードの文書、`diff --deletes-only` に置換の削除が出ない | 対応しない | `555338e` の `*.md` に 3 つの停止コードの記載は無いが、値のリセットは `docs/DECLARATIVE.md:57` に記載済みで、残りは情報の追加。deletes-only は relocate と共通の表示仕様（round 7・8 と同じ） |
| O-U1 | 空で作った置換を再開すると、フィールドを書く前に検証する | 対応する | **(a)** E3・E5。K-H1 と同じ原因（§2 の判断の変更を参照）。修正 B |
| O-M1 | 作り直しで `initialFields`・未宣言 member が初期値に戻ることの記述の矛盾 | 解消済み | `docs/DECLARATIVE.md:57`、`README-DETAILS.md:181`、build skill の手順 6 に明記 |
| O-L1 | 取り消し時に sibling の index がずれる | 解消済み | `UndoRecreateState`（W:1354–1366）。`UndoneRecreateKeepsSiblingIndexesSoAWorldReloadStillBindsThem` が成功 |
| O-L2 | 中断後に key を外して prune すると旧 Component が残る | 解消済み | W:1581–1594。`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` の 2 ケースが成功 |
| O-L4 | 作成前の中断で同型 sibling と ownership conflict | 解消済み | `HeldByOtherKeys`。`InterruptedRecreateNextToASameTypeSiblingResumes` などが成功 |
| O-L5 | 再読込後の復旧ヒントが成り立たない | 解消済み | `InterruptedRecreateAcrossSession`。`InterruptedRecreateNextToSameTypeSiblingsRecoversAfterWorldReloadByFollowingTheHint` の 5 ケースが成功 |
| O-L6 | 新しい key の作成応答を失うと重複して作る | 解消済み | `RecreatedOnNode` の絞り込み。`ResumedCreateOfANewKeyNextToARecreateBindsWhatItCreated` の 2 ケースが成功 |
| O-L7 | sibling が 2 つあると、ヒントどおりに復旧したあと止まる | 解消済み | 最初の `supersededId` の checkpoint での保存し直し（W:465–474）。上記のヒント復旧の 5 ケースが成功 |
| O-L8 | `supersededId` の保存前に止まると sibling だけ final index になる | 解消済み | `recreatingNodes`・`AtSavedLayout`。`ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` の 3 ケースが成功 |
| O-L9 | 保存 ID の無い key が、リストの長い管理外 Component を作り直す | 解消済み | `UnsavedMatchWithALongerList`。`InterruptedCreateOfANewKeyDoesNotRecreateAnUnmanagedComponentWithALongerList` の 2 ケースが成功 |
| O-L10 | recreate より前に処理した同型の新しい key が final index で保存される | 解消済み | `AtSavedLayout`。`NewKeyCreatedBeforeARecreateConvergesAfterWorldReload` の 3 ケースと `NewKeyCreatedBeforeAnInterruptedRecreateIsSavedAtItsFinalIndex` が成功 |
| O-L11 | 作り直す Component より後ろに prune 前の同型 key があると、再読込後に止まり続ける | 解消済み | round 8 の修正 A（`1ac2692`、`SaveUndeclaredIndexes`）。`UndeclaredKeyOnARecreatingSlotKeepsAnIndexAWorldReloadBinds` の 3 ケースなどが成功。残る経路は O-L12 として扱う |

### K: Grok 4.7（小文字、`555338e`）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| K-H1 | フィールド未適用の置換を再開すると、refill の検証の前に元 Component を削除する | 対応する | **(a)** E3・E4。**(b)** W:506–509 のコメントは、フィールド無しで作った置換には検証の前にフィールドを書くとしているが、W:514 の条件は `Existing is null` のときだけで、再開した置換には書かない。修正 B |
| K-U1 | 同じ再開で、伸びるリストが参照を含まないと、元 Component を削除したまま apply が成功する | 対応する | **(a)** E3・E4 の `Weights`。末尾の参照の照合（W:657–681）は参照を含むフィールドしか見ない。修正 B |
| K-M1 | 先に検証する recreate が、後で削除される置換を参照したまま残る | 解消済み | round 8 の修正 C（`d53613f`）。`UndoneRecreateLeavesNoOtherReplacementReferencingTheRemovedOne` が成功 |

### Q: Qwen（`555338e`）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| Q-L1 | 空の fields で作った置換を再開すると、refill の検証が空振りして旧 Component が削除される | 対応する | **(a)** E3〜E5。K-H1 と同じ原因で、作成応答の喪失（E5）と数値のリスト（K-U1）も挙げている。修正 B |
| Q-U1 | 作成ループの前の保存と、作成前の停止が作る再読込時の index のずれ | 解消済み | `AtSavedLayout`・`CurrentIndex`（W:452–464）。`ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` の 3 ケースなどが成功 |
| Q-M1 | 中断した recreate の移動で、新旧どちらかが孤立する | 解消済み | `MovingAComponentWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent`・`InterruptedRecreateStopsBeforeMutationAfterWorldReloadWhenTheKeyMovesOrIsRemoved` が成功 |
| Q-M2 | 再開時に refill の検証を飛ばして旧 Component を削除する | 解消済み | 検証ループは再開した置換も対象にする（`VerifiesRecreate`）。`ResumedRecreateThatTheRuntimeRefilledStopsAndKeepsTheOriginal` が成功。フィールド無しで作った置換の再開で残る穴は Q-L1 として扱う |
| Q-I1 | 停止コード 3 種と `supersededId` の文書不足（原レビューでは解消扱い） | 対応しない | round 7・8 と同じ。値のリセットの記述の矛盾は解消済みで、停止コードの説明は情報の追加 |
| Q-I2 | relocate の移動元 Slot の sibling の index が削除前の位置で保存される | 解消済み | `SaveIndexesAfterRemoving`（W:547–563）。`ComponentRemovedFromASlotLeavesIndexesAWorldReloadBinds` の 2 ケースなどが成功 |

### C: commandcode / DeepSeek（`555338e`）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| C-L1 | 置換元が削除済みでも再読込後に止まり、state の手編集が要る | 対応しない | W:1128–1133・W:1584–1585 は変わっていない。session-scoped の ID から削除済みと推定せずに止まる安全側の方針（round 7・8 と同じ） |
| C-I1 | `recreate` と 3 つのエラーコードが文書・スキルに無い | 対応しない | O-I1 と同じ。fork の AGENTS.md「Skills are workflows, not command mirrors」 |
| C-I2 | plan の Warnings に観測範囲の注意が無い | 対応しない | 停止時の suggestions と PR 本文に制限を記載済み。成功した plan への警告の追加は UX の改善 |
| C-I3 | 置換が無い key を prune すると、実在しない ID の key が state に残る | 対応しない | 実在しない対象の key を残すのは、通常の prune と同じ方針（round 7・8 と同じ） |
| C-U1 | recreate と relocate が同じ Slot にあると、relocate 側の index が補正されない | 対応しない | round 7 の再現で、宣言順の 2 通りとも index が一致し、再読込後に収束した。関係するコードは変わっていない |
| C-U2 | ID の無い宣言外の key の index が、同じ Slot の recreate で更新されない（round 8 の C-U4） | 対応しない | round 8 と同じ。宣言されない ID 無しの key は位置から推測するしかない。`SaveUndeclaredIndexes` も修正 A も、変更の前に照合できた key だけを扱う |
| C-U3 | 管理外 Component を証拠一致で採用し、宣言値を書き込む | 対応しない | D-H1 と共通の採用方針。`id` の欠けた state が入る経路は未確認 |
| C-H1 | held 候補の除外で index がずれ、管理外 Component を採用する | 解消済み | `MatchComponent` の held。`ResumedRecreateBindsItsReplacementNextToAnUnmanagedSameTypeComponent` などが成功 |
| C-H2 | 位置で採用した管理外 Component を refill の取り消しで削除する | 解消済み | W:527–528 の `matchedByPosition`。`UndoneRecreateKeepsAReplacementMatchedWithoutItsSavedId` の 2 ケースと `ResumedRecreateKeepsARefilledReplacementWhoseCreateResponseWasLost` が成功 |

### P: GPT-6.1 Sol（`ce39425` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| P-H1 | 入れ子の一部を宣言しただけで、宣言外の子参照も作り直しの安全チェックから外れる | 解消済み | round 8 の修正 B（`2c324e3`）。`ListShrinkChecksEachNestedReferenceAgainstItsOwnDeclaredChild` の 3 ケースが成功 |
| P-M1 | 未適用の参照 topology が、応答を失った置換を照合候補から外し、重複を残す | 解消済み | round 8 の修正 D（`555338e`、`CreateComponentState` の `written`）。`ResumedRecreateCreatedWithoutItsReferencesBindsWhatItCreated` の 2 ケースが成功 |

### G: Grok（大文字、`0acf969` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| G-H2 | recreate と同じ apply で Slot から外した Component を最終 index が数え、再読込後に止まり続ける | 解消済み | round 7 の `SaveIndexesAfterRemoving`。`ComponentRemovedFromARecreatingSlotLeavesIndexesAWorldReloadBinds` の 4 ケースが成功 |
| G-H1 | recreate より前に保存した同型の新しい key が、再読込後に置換対象を奪う | 解消済み | `AtSavedLayout`。`NewKeyCreatedBeforeARecreateConvergesAfterWorldReload` の 3 ケースが成功 |

### S: SWE（`0acf969` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| S-L1 | prune 予定の参照元も `APPLY_LIST_SHRINK_REFERENCED` に数える | 対応しない | 変更前に止まる安全側の動作で、停止条件の緩和は仕様の変更（round 7・8 と同じ） |
| S-L3 | 中断した recreate の relocate がさらに中断すると、置換が管理外で残る | 対応しない | 通常の relocate にもある、削除元の追跡（state が 2 つの ID しか持たない）の設計課題（round 7・8 と同じ） |
| S-I1 | action の列挙・停止コード・復旧手順の文書への追記 | 対応しない | O-I1 と同じ |
| S-I2 | 偽クライアントの `SetFields` が裸の文字列で `JsonException` になる | 対応しない | 現行のテストで使わない入力。偽クライアントを一般化しない |
| S-I3 | relocate の再中断後、復旧候補に移動元の置換元が出ない | 対応しない | S-L3 と同じ設計課題。変更前に止まる |
| S-U1 | stale ID の key と空 ID の key の二重主張 | 対応しない | 端から端までの再現は無く、ownership による停止を緩める根拠も無い |
| S-U2 | 空で作成して中断した Component に `initialFields` が適用されない | 対応しない | recreate 以前からある、作成の再開の仕様論点。修正 B も再開した置換には `fields` だけを書き、`initialFields` の扱いは変えない |
| S-U3 | relocate+superseded・relocate の移動元・prune で、移動元の保存 index が削除を反映しない | 解消済み | `SaveIndexesAfterRemoving`。`ComponentRemovedFromARecreatingSlotLeavesIndexesAWorldReloadBinds`・`MovingAKeyWhoseRecreateWasInterruptedLeavesSiblingIndexesAWorldReloadBinds`・`ComponentRemovedFromASlotLeavesIndexesAWorldReloadBinds` が成功 |
| S-U4 | relocate の移動元の照合に `recreatedOnNode` の絞り込みが無い | 対応しない | 管理外の候補を含む、端から端までの再現が無い |
| S-U5 | 同じ Slot の 2 つの新しい recreate の間で中断すると、2 本目の束縛先を取り違える | 対応しない | round 7 の再現で、変更前に止まり、ヒントどおりの復旧で収束した。関係するコードは変わっていない |
| S-U6 | 作成直後に実機が member を完全に返すか | 対応しない | 実機での不足は未確認。adapter を推測で直さない |
| S-L4 | `supersededId` 保存済みの recreate の再開で、sibling が現在の配置の index に戻る | 解消済み | `!SavedFinalIndexes`（W:461）。`ResumedRecreateStoppedAtASiblingKeepsItsFinalIndexAcrossWorldReload` の 2 ケースが成功 |
| S-M1 | NOT_CONVERGED の取り消しで、参照が削除済みの置換を指す | 解消済み | `UndoneRecreateLeavesNoReferenceToTheRemovedReplacement` と、置換どうしの参照の `UndoneRecreateLeavesNoOtherReplacementReferencingTheRemovedOne` が成功 |
| S-L2 | `supersededId` が残る Component の relocate・宣言削除で旧 Component が残る | 解消済み | `MovingAComponentWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent`・`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` が成功 |
| S-M2 | 作成前に中断した key の移動で、他の key の同型 Component を移動元として束縛する | 解消済み | `HeldByOtherKeys`。`InterruptedCreateOfANewKeyThatMovesIsCreatedOnTheNewSlot` が成功 |

### D: DeepSeek（`485e508` 世代、更新なし）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| D-H1 | 作成が実行されなかった recreate の再開で、管理外の同型 Component を採用する | 対応しない | 位置照合による採用方針は変わっていない。応答喪失による正当な再開と区別するには、証拠と停止方針の変更が要る（round 6 でユーザーが承認した据え置き） |
| D-M1 | 中断後の並び替えで管理外 Component を採用し、本来の置換が孤立する | 対応しない | D-H1 と同じ位置照合の設計課題。実機で先頭に挿入できるかは未確認 |
| D-U1 | 連続した中断で current / final の index が混ざる | 解消済み | S-L4 と同じ。`ResumedRecreateStoppedAtASiblingKeepsItsFinalIndexAcrossWorldReload` が成功 |

## 5. 修正方針

A と B は互いに独立しているので、それぞれ回帰テストを先に追加し、`555338e` で失敗することを確かめてから実装する。

### A. 別セッションの apply で、宣言外の key の ID を照合した Component の ID に更新する（O-L12）

対応 ID: **O-L12**、基準 **(a)**。

原因: `PrepareAsync` は state の `sessionId` を現在のセッションに書き換え（W:1006–1007）、最初の checkpoint がそれを保存する。宣言された key の `id` は、その apply の checkpoint で新しい ID に更新される。一方、文書から外して `--prune` なしで残した key は、別セッションの apply で削除計画が証拠から照合しても（W:1597–1602）、`id` は再読込前のまま残る。そのため、同じセッションの次の apply では、`BuildDeletionPlans` が古い保存 ID で探して見つけられず（W:1596）、削除計画を作らない。round 8 の修正 A（`SaveUndeclaredIndexes`）は削除計画のある key だけを保存し直すので、作り直しで Slot の並びが変わっても、その key の保存 index は古いまま残る。作り直しの置換は Slot の末尾に付くので、後ろにある宣言外の key の古い index がちょうど置換を指し、次の再読込後は plan・apply が毎回止まる（E2）。

方針:

- `ApplyAsync` で `PrepareAsync` のすぐあと、最初の checkpoint の前に、別セッション（`!prepared.SameSession`）なら、`prepared.Deletions` の Component の削除計画（`Kind == "component"`）ごとに、state のその key の `id` を削除計画の ID（`deletion.Id`）に更新する。
  - 別セッションで `supersededId` を持つ key は、その前に `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION` で止まるので、対象は通常の削除計画だけになる。
  - `ValidateComponentOwnership` などの検査は `PrepareAsync` の中で終わっているので、衝突があれば state を書く前に止まる。
  - 同じセッションでは、削除計画の ID は保存 ID そのものなので、何もしない。
- 更新は、新しい `sessionId` と同じ checkpoint で保存される。plan（`PlanApplyAsync`）は state を書かないので変えない。
- 副次的に、round 8 で「範囲外の観察」とした、再読込後に `--prune` なしで apply したあと同じセッションの `--prune --yes` がその Component を削除しない問題も直る。
- 変えないもの: 照合できなかった宣言外の key（ID の無い key を含む。C-U2）と、宣言外の Slot の保存 ID。

検証:

- T の `UndeclaredKeyOnARecreatingSlotKeepsAnIndexAWorldReloadBinds` に `apply-after-reload` のケースを追加する。`DropOldAfterRendererAsync(dropNow: true)` → `ReloadWorld` → `renderer` 4 要素で apply → 3 要素で apply の順に操作し、既存のケースと同じく、`old` の保存 index が実際の位置と一致すること、再読込後の plan の変更が `delete:old` だけであること、`--prune --yes` が `old` の Component だけを削除して `renderer` の state が置換を指すことを確かめる。あわせて、4 要素の apply のあとで `old` の state の `id` が `south` の Component の ID になっていることを確かめる。
- T に、再読込後に `--prune` なしで apply したあと、同じセッションの `--prune --yes` が `old` の Component を削除し、state から `old` が消えることを確かめるテストを 1 件追加する。

### B. 再開した置換も、フィールドを書いてから検証する（K-H1・K-U1・O-U1・Q-L1）

対応 ID: **K-H1**（(a)・(b)）、**K-U1**・**O-U1**・**Q-L1**（(a)）。

原因: 検証ループ（W:506–543）は、この apply で作った置換（`Existing is null`）がフィールド無しで作られていれば、置換を参照しないフィールドを検証の前に書く（W:514–522）。再開した置換（`Existing` あり）は、中断した apply がフィールド無しで作ったものでも、何も書かずに検証する。リストはまだ宣言より短いので検証を通り、そのあとのフィールドの反映（W:565–596）で runtime がリストを宣言より長くしても、もう検証は無い。元の Component の削除（W:598–610）で `supersededId` も消えてから、参照のリストなら末尾の照合が `APPLY_REFERENCE_NOT_RETAINED` で止まり、数値のリストなら apply は成功する（E3〜E5）。再開に入る経路は、検証の前の中断（E3）、同じ apply の先の作り直しの `APPLY_LIST_SHRINK_NOT_CONVERGED`（E4）、置換の作成応答の喪失（E5）の 3 つである。

方針:

- 検証ループで、`AppliedOnCreate` が無い置換は、再開したものも含めて、置換を参照しないフィールドを書いてから検証する。
  - この apply で作った置換: 今と同じ（`MergeCreateFields` のうち `CanResolve` で解決できるもの）。
  - 再開した置換: `Spec.Fields` のうち `CanResolve` で解決でき、観測した値（`Existing.Members`）と一致しないものだけを書く。フィールドを付けて作った置換では書くものが無く、書き込みは増えない。`initialFields` は、今のフィールドの反映と同じく書かない（S-U2 の扱いは変えない）。
  - 書いたかどうかにかかわらず、解決したフィールドを `AppliedOnCreate` に記録する。フィールドの反映（W:570–574）は `AppliedOnCreate` と同じ値のフィールドを書かないので、同じ値を二度書かない。
- 位置で照合した置換（`matchedByPosition`、W:527）は、管理外の Component のことがある。書き込む前に、今と同じ検査（`GetComponentAsync` と `ListShrinkReason`）を行い、リストがすでに宣言より長ければ、何も書かずに今の停止（置換を残して元に戻す）をする。これで `UndoneRecreateKeepsAReplacementMatchedWithoutItsSavedId` などが確かめている「管理外の Component の member を変えない」挙動を保つ。短ければフィールドを書き、もう一度検査する。
- 書いたあとの検査で長ければ、今と同じく、保存 ID で束縛した置換は削除し、位置で照合した置換は残して、`UndoRecreateState` で元に戻し、`APPLY_LIST_SHRINK_NOT_CONVERGED` で止まる。停止コード・context・suggestions は変えない。
- W:506–509 のコメントを、再開した置換にも書くこと、位置で照合した置換は書く前に検査することが分かる書き方に直す（(b)）。
- 残る制限（変えない）: 置換への参照を書いたことがきっかけの refill（round 8 の修正 C の残る制限）と、非同期の refill（O-L3）は検出しない。位置で照合した置換にフィールドを書いたあとで止まった場合、その Component は書いた値のまま残る（今でも、検証を通ればフィールドの反映で同じ値を書く）。

偽クライアントの変更:

- `ApplyWorkflowTests.cs` の偽クライアントに `AfterMembersSet`（`Action<FakeComponent, IReadOnlyDictionary<string, string>>?`）を追加し、`SetComponentMembersAsync` の `SetFields` の直後に呼ぶ。コメントで、フィールドを設定したときに runtime がリストを埋め直す挙動（設定した mesh からリストの長さが決まる、など）を模すものであることを書く。既定は null で、既存のテストの挙動は変わらない。

検証:

- T に Theory を追加する（例: `ResumedRecreateCreatedWithoutItsFieldsIsVerifiedWithThem`）。フックは、`Test.Renderer` の対象のリスト member が書かれたら要素数を 4 にそろえる。
  - `stopped-before-verification`（`Materials`・`Weights`）: E3 の構成。再実行が `APPLY_LIST_SHRINK_NOT_CONVERGED` で止まり、`renderer` の元の Component が残り、state の `renderer` が元の ID で `supersededId` を持たないこと。
  - `earlier-recreate-undone`（`Materials`・`Weights`）: E4 の構成。再実行が `APPLY_LIST_SHRINK_NOT_CONVERGED`（`componentKey` は `second`）で止まり、`second` の元の Component が残ること。
  - `lost-create-response`（`Materials`、自己参照）: E5 の構成。再実行が `APPLY_LIST_SHRINK_NOT_CONVERGED` で止まり、元の Component が残り、`keptComponentId` が作成応答を失った置換であること。
- T に、フックが無い場合に E3 の構成の再実行が収束すること（`Test.Renderer` が 2 つだけで、すべて state の key が追跡し、次の apply の書き込みが 0 件）を確かめるケースを追加する。
- 既存の `ResumedRecreateThatTheRuntimeRefilledStopsAndKeepsTheOriginal`、`UndoneRecreateKeepsAReplacementMatchedWithoutItsSavedId`（2 ケース）、`ResumedRecreateKeepsARefilledReplacementWhoseCreateResponseWasLost`、`ResumedRecreateCreatedWithoutItsReferencesBindsWhatItCreated`（2 ケース）、`InterruptedListShrinkRecreateResumesWithoutDuplicates`（3 ケース）を維持する。フィールドを付けて作った置換を再開したときに書き込みが増えないことは、これらの既存テストの書き込み数のアサーションで確かめる。

## 6. 対象ファイル・非対象・互換性

実装予定のファイル（fork のルート基準）:

- `src/RLoop.Core/WorldService.cs`: 修正 A（`ApplyAsync` の最初の checkpoint の前）と修正 B（検証ループとそのコメント）。
- `tests/RLoop.Tests/ApplyWorkflowTests.cs`: 偽クライアントの `AfterMembersSet`。
- `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`: A・B の回帰テスト。

変更しないもの:

- 永続 state の形式、公開 CLI / API、エラーコードと context のキー、suggestions、plan の表示。
- 位置照合による採用方針（D-H1・D-M1・C-U3）、ID の無い宣言外の key（C-U2）、宣言外の Slot の保存 ID、relocate の削除元の追跡と復旧候補の範囲（S-L3・S-I3）、prune 予定の参照元での停止（S-L1）、置換元が無い場合の再読込後の停止（C-L1）。
- 非同期の refill（O-L3）、再開した Component への `initialFields` の適用（S-U2）、adapter の推測による修正、文書の追記。
- すでに保存された、古い ID や index を推測で直す移行処理。修正前の apply で保存された宣言外の key の古い ID は、次の別セッションの apply で照合できたときに更新される。

## 7. 承認後の検証・既存 PR への反映

1. 作業ツリー `external/resoloop/.worktrees/fix-list-shrink-recreate` の HEAD と `origin/fix/list-shrink-recreate` が `555338e` で一致することを確かめる。
2. A・B の回帰テスト（B は偽クライアントのフックを含む）を先に追加し、`555338e` で期待どおり失敗することを確かめる。一時テストの「経過をログに書くだけ」の形を、そのまま恒久テストにしない。
3. A・B を実装し、追加したテストと `--filter 'FullyQualifiedName~ApplyWorkflowTests'` を実行する。
4. 変更したプロジェクトに関連する検証として `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` を実行する。失敗している間は commit しない。実機への接続、関係の無いワールドのテスト、fork 全体の一括テストは条件にしない。
5. `git fetch origin` で PR の HEAD を確認し直す。根拠にした SHA から更新があれば、関係する部分を確認し直す。
6. 修正ごとに `fix/list-shrink-recreate` へ commit し、`origin` へ push する。main、追加の review-fixes ブランチ、新しい PR には載せない。
7. モデル識別子 `claude-opus-5-5` で、TOPLEVEL 側の `upsert_pr_comment.py` を使い、PR #5 の自エージェントのコメント（マーカー `review-fix-planning:agent:claude-opus-5-5`）を更新する。他のエージェントのコメントは編集しない。

計画のターンでは、PR コメントの投稿・commit・push をしていない。

## 8. 作業時間

担当: このセッション（Claude Code、claude-opus-5-5）。2026-09-30 16:20 JST ごろに着手。

- Task 1–2: レビューディレクトリの特定、全 8 ファイルの読解、PR・remote・HEAD・既存の PR コメント・round 8 Spec の確認: 約 8 分
- Task 3: コミット済みのコードの読解、一時テスト 10 件（再現 6 件・対照 3 件・切り分けられなかった構成 1 件）の作成と実行、撤去: 約 12 分
- Task 4–6: 分類、bounded の設計、Spec の作成と一覧の照合: 約 10 分
- 合計: 約 30 分。テストは同期実行し、終了コードを確かめてから撤去した。

サブエージェントは使用していない（ユーザーの明示的な依頼が無いため）。

## 9. レビュー修正の打ち切り（2026-09-30）

- 経緯: 修正→レビューのたびに回帰と適用漏れが出てコミットが積み上がる根本原因を調べた結果、ユーザーが PR #5 のレビュー修正を `555338e` で打ち切ることにした。根本原因と対策は https://github.com/usaturn/create-reso-world/issues/5 に記録した。
- この Spec の修正 A（O-L12）と修正 B（K-H1・K-U1・O-U1・Q-L1）は実装しない。§4 の分類と §3 の再現記録は、Issue #5 の対策を進めるときの資料として残す。
- 打ち切りの判断材料: 未対応の指摘は、3 プロジェクトの apply 文書 29 件（`tmp/` を除く）に無い構成を前提にしている。参照のリストを持つ Component は `MeshRenderer`（`Materials`）の 2,256 個だけで、同じ Slot に同型の `MeshRenderer` が複数ある Slot も、`MeshRenderer` どうし（自分自身を含む）の参照も 0 件だった。大半は変更の前に止まる種類の不具合である。また、`.devcontainer/resoloop.lock` は `fix/blender5-uv-export`（`1ef4d18`）を指しており、PR #5 のコードは現在の環境で使われていない。
- 実施したこと:
  - PR #5 の説明の「既知の制限」に、未対応の指摘と回避方法を追記し、テスト結果を `555338e` の値に更新した（`dotnet test ResoLoop.slnx`: `RLoop.Tests` 395 件、`RLoop.IntegrationTests` 19 件、すべて成功）。
  - PR #5 の自エージェントのコメント（`review-fix-planning:agent:claude-opus-5-5`）を、round 9 の選別結果と打ち切りの判断で更新した。
  - Issue #5 に、打ち切りの記録を追記した。
- commit / push はしていない。PR #5 の HEAD は `555338e` のまま。
- PR #5 を使い始めるときは、base の PR #4 を先にマージし、ロックファイルを明示的に更新する。そのとき、同じ Slot に同型の Component を置く文書には `identityFields` を付ける。
