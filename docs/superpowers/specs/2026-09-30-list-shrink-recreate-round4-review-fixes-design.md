# list-shrink-recreate レビュー指摘の修正設計（ラウンド 4）

- 日付: 2026-09-30
- 対象 PR: usaturn/resoloop #5（`fix/list-shrink-recreate` → `fix/asset-url-save-migration`）
- 現行 HEAD: `929c9ae337e6193286927a5b7c6cd4850d4640bb`（レビュー対象 HEAD と同じ。ラウンド 3 の修正コミット）
- 入力: `external/resoloop/reviews/#5-fix-list-shrink-recreate/`（4 件とも対象 HEAD は `929c9ae337e6`。各指摘の検出時 HEAD は `d615eeb`・`dc1c651`・`30476c4`・`929c9ae`）
  - `claude-opus-5-5.md`
  - `SWE-2-Max.md`
  - `commandcode-deepseek-deepseek-v4.1-flash.md`
  - `qwen3.8-max.md`
- 前回: `docs/superpowers/specs/2026-09-29-list-shrink-recreate-round3-review-fixes-design.md`（ラウンド 3。G7・G8 を `929c9ae` で反映済み）
- brainstorming の経路: **bounded**（`WorldService.cs` の既存の照合・作成・作り直しの取り消しの流れを直す修正。state の形式とエラーコードの集合は変えない。`APPLY_LIST_SHRINK_NOT_CONVERGED` の context に項目を 1 つ足す）

## 目的と成功条件

- 目的: 中断した apply を同じセッションで再実行したとき、Component を重複して作らず、管理外の Component を削除しないこと。再読込後の復旧ヒントどおりに操作すれば収束すること。
- 制約: 変更前に止まる既存の停止（`APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION`・`STABLE_COMPONENT_AMBIGUOUS`）は緩めない。state の形式を変えない。修正は PR #5 のブランチに載せる。
- 成功条件: 下記の再現テストが修正前に失敗し修正後に成功すること。既存の `ApplyWorkflowTests` 141 件がすべて成功すること。

## 検証の方法

`git -C external/resoloop worktree add --detach` で `929c9ae` を一時 worktree に取り出し、偽クライアント（`ApplyWorkflowTests`）で再現テストを書いて `dotnet test --filter` で実行した。修正案も同じ worktree で試作し、既存テストと再現テストを流した。未改変の `929c9ae` では `FullyQualifiedName~ApplyWorkflowTests` の 141 件がすべて成功することを、別の一時 worktree で確かめた。worktree と一時ディレクトリは検証後に削除済み。

表の `C5(north,4)` は「ID C5・`Label` が `north`・`Materials` が 4 要素の `Test.Renderer`」を表す。`ApplyFourMaterialsAsync` で 4 要素の `renderer` を作ったあと、3 要素に縮める文書で apply した。

| 再現 | HEAD（`929c9ae`） | 試作した修正 |
| --- | --- | --- |
| O-L6: 同じ Slot に同型の新しい key `extra`（`Label: "east"`）を `renderer` の後に宣言し、`extra` の作成応答だけを失わせる | 中断後 `[C5(north,4), C6(north,3), C7(east,1)]`、state は `extra{id="", componentIndex=1}`。再実行の plan は `renderer:recreate, extra:create` で、結果は `[C6, C7(east,1), C8(east,1)]`。C7 が管理外で残り、3 回目の apply の書き込みは 0（検出されない） | plan は `renderer:recreate` だけ。`extra` は C7 に束縛され `[C6, C7]` に収束。3 回目の書き込み 0 |
| O-L6: 同上で `extra` を `renderer` の前に宣言 | 中断後 `[C5(north,4), C6(east,1)]`、state は `renderer{id=C5}`（`supersededId` なし）・`extra{id="", componentIndex=0}`。再実行後 `[C6(east,1), C7(east,1), C8(north,3)]` で C6 が管理外で残る | `extra` は C6 に束縛され `[C6(east,1), C7(north,3)]` に収束。3 回目の書き込み 0 |
| O-L7: `renderer` の後に同型の `sibA`（south）・`sibB`（east）を宣言し、`before-add`（`FailOnWrite=1`）で中断 → 再読込 → ヒントどおり `north` の候補を削除し state から `renderer` を外す | 中断後の state は `sibA{componentIndex=1}`・`sibB{componentIndex=2}` のまま。ヒントどおりの操作後 `[C13(south), C14(east)]` で、再実行は `STABLE_COMPONENT_AMBIGUOUS {"candidateIds":["C13","C14"]}`、書き込み 0 | 中断後の state は `sibA{0}`・`sibB{1}`。再実行は書き込み 1 で `[C13(south), C14(east), C15(north,3)]` に収束 |
| O-L7: 同上を `lost-add-response` で中断 | 同じく `STABLE_COMPONENT_AMBIGUOUS`、書き込み 0 | 同じく収束 |
| O-L7（対照）: sibling が 1 つで `before-add` | ヒントどおりの操作で収束 | 同じ |
| D-H2: 作り直しを `before-add` で中断（state は `id=""`・`supersededId=C5`）→ 管理外の同型 C6（`Label: "west"`、`Materials` 4 要素）を追加 → 同じセッションで再実行 | C6 を置換として束縛し、refill と判定して C6 を削除する。`APPLY_LIST_SHRINK_NOT_CONVERGED`、書き込み 1（削除のみ）、残るのは `[C5(north,4)]` | C6 を削除しない。`APPLY_LIST_SHRINK_NOT_CONVERGED`、書き込み 0、`[C5(north,4), C6(west,4)]` のまま。state は `renderer{id=C5}` に戻る |
| S-U1（一般形）: 置換作成後に中断（`FailOnWrite=2`、state は `id=C6`・`supersededId=C5`）→ 置換 C6 を手で削除し、管理外の同型 C7（west、4 要素）を追加 → 再実行 | 保存 ID で見つからないため型と位置で C7 を束縛し、C7 を削除する。書き込み 1 | C7 を削除しない。書き込み 0 |
| D-H2（対照）: 同上で管理外 C6 の `Materials` が 1 要素 | C6 を置換として採用し、`Label` と `Materials` を書き換えて C5 を削除する | 同じ（ラウンド 3 の「残る制約」。今回は扱わない） |
| 既存テスト | `ApplyWorkflowTests` 141 件がすべて成功 | 141 件と再現テスト 8 件がすべて成功 |

## 分類

解消済み 13 / 対応する 4（修正は 3 系統）/ 判断保留 0 / 対応しない 21（計 38）。ID の接頭辞は O = claude-opus-5-5、S = SWE-2-Max、D = deepseek、Q = qwen3.8-max。U は各レビューの Unverified candidates の番号（記載順）。

### 解消済み

各レビューの Resolved findings に挙がったもの。未改変の `929c9ae` で該当テストを含む `ApplyWorkflowTests` 141 件の成功を確認した。

| ID | 根拠 |
| --- | --- |
| O-M1 | 作り直しで `initialFields` と未宣言 member が初期値に戻ることを `docs/DECLARATIVE.md:57`・`README-DETAILS.md:181`・`skills/codex/resonite-build/SKILL.md` に明記済み（ラウンド 1 の G5） |
| O-L1 | `UndoRecreateState` が sibling の `componentIndex` を保存し直す。`UndoneRecreateKeepsSiblingIndexesSoAWorldReloadStillBindsThem` が成功 |
| O-L2 | `BuildDeletionPlans` が旧 Component の削除を先に計画する。`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` が成功 |
| O-L4 | `InterruptedRecreateNextToASameTypeSiblingResumes`（2 ケース）・`InterruptedCreateOfANewKeyNextToAManagedSameTypeComponentResumes` が成功 |
| O-L5 | `929c9ae` の G8。候補に `fields` を添え、ヒントを保存 ID の有無で分けた。`InterruptedRecreateNextToASameTypeSiblingRecoversAfterWorldReloadByFollowingTheHint`（3 ケース）が成功。sibling が 2 つ以上の場合は O-L7 として扱う |
| D-H1 | `929c9ae` の G7。`HeldByOtherKeys` が候補の配列を縮めなくなった。`ResumedRecreateBindsItsReplacementNextToAnUnmanagedSameTypeComponent`・`ResumedCreateOfANewKeyBindsWhatItCreatedNextToAnUnmanagedSameTypeComponent`（各 2 ケース）が成功 |
| S-M1 | 検証前の置換を `byKey` に入れない。`UndoneRecreateLeavesNoReferenceToTheRemovedReplacement` が成功 |
| S-L2 | 旧 Component を snapshot 全体から探して relocate・宣言削除でも削除し、再読込後は変更前に停止する。`Moving…`・`Pruning…`・`InterruptedRecreateStopsBeforeMutationAfterWorldReloadWhenTheKeyMovesOrIsRemoved` が成功 |
| S-M2 | `929c9ae` の G7。relocate の移動元の照合にも `HeldByOtherKeys` を渡す。`InterruptedCreateOfANewKeyThatMovesIsCreatedOnTheNewSlot` が成功 |
| Q-M1 | S-L2 と同じ修正・テスト |
| Q-M2 | `VerifiesRecreate` で再開した作り直しも refill を検証する。`ResumedRecreateThatTheRuntimeRefilledStopsAndKeepsTheOriginal` が成功 |
| Q-U1 | D-H1 と同じ（index の意味のずれによる誤束縛）。同じテストが成功 |
| Q-U2 | S-M2 と同じ（relocate の移動元で他 key の保持分を選ぶ）。同じテストが成功 |

### 対応する

| ID | 区分 | 一行 |
| --- | --- | --- |
| O-L6 | (a) | 作り直しと同じ Slot に同型の新しい key を足す apply で、新しい key の作成応答を失うと、再実行で Component を重複して作り、先に作った Component が管理外で残る。保存 index は作り直し後の配置、照合する配列は作り直し前の配置で、位置が 1 つずれて他 key の保持分を指す。`30476c4` では収束していた回帰。宣言順 2 通りとも再現した |
| O-L7 | (a) | 再読込後の `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION` のヒントどおりに操作しても、作り直す key の後に同型 sibling が 2 つ以上ある Slot では、sibling の保存 index が作り直し前の値のままで `STABLE_COMPONENT_AMBIGUOUS` で止まり、収束させる手段が無い。`before-add`・`lost-add-response` とも再現した |
| D-H2 | (a) | 作り直しを置換の作成前に中断したあと、同じ Slot に管理外の同型 Component があると、再実行がそれを置換として束縛し、リストが宣言より長いと refill と判定して `--prune` なしの apply で削除する。fork の `AGENTS.md`（Resonite safety）の「既存のユーザのコンテンツを変更しない」「未検証の ID に破壊的操作をしない」に反する |
| S-U1 | (a) | D-H2 と同じ削除の経路。レビューの「`memberNames` が空」という条件は、リスト member を宣言しないと作り直しが起きないため成立しないが、一般形（置換を手で消した・保存 ID はある・管理外の同型 Component が 1 つ）で削除を再現した。D-H2 の修正で同時に塞ぐ |

### 判断保留

なし。

### 対応しない

| ID | 理由 |
| --- | --- |
| O-L3 | ラウンド 1〜3 と同じ。実機で非同期に refill されるリストがあるかは未確認で、偽クライアントでは再現できない。対策には state に作り直しの履歴を残す設計が要る |
| O-U1 / Q-L1 | ラウンド 1〜3 と同じ。空で作った置換の再開時に refill を見逃すのは、runtime がフィールド設定をきっかけにリストを埋め直す場合に限られ、実機の挙動が未確認。次の apply で `NOT_CONVERGED` として検出される |
| O-I1 / S-I1 / D-I1 / Q-I1 | ラウンド 1〜3 と同じ。`recreate` と新しいエラーコード 3 件の記載漏れ（Info）。README の例に action の一覧は無く、fork の `AGENTS.md` は skill を「workflows, not command mirrors」とする。停止コードはヒントで復旧手順を自己記述する（今回 O-L7 でヒントの手順が成り立つ条件を広げる）。qwen は作者の判断として解消扱いにしている |
| S-L1 | ラウンド 1〜3 と同じ。`--prune` で消える Component からの参照も数えるのは、変更前に止まる安全側の停止。緩めるかは仕様の判断 |
| S-L3 | ラウンド 2・3 と同じ。通常の relocate も同じ中断区間で移動元を残す既存の挙動。塞ぐには state に削除待ちの ID を別に持たせる設計変更が要る |
| S-I2 | ラウンド 1〜3 と同じ。偽クライアント `SetFields` に該当する入力は現行テストに無い |
| S-I3 | 作り直しの中断 → その key の relocate の中断 → 再読込、の 3 つが重なる場合に限る。変更前に停止し、2 つ目のヒント（候補を `fields` で絞れなければ Resonite で確認する）が残る。原因は S-L3 と同じ relocate の中断区間で、relocate 全体の設計として別途扱う |
| S-U2 | ラウンド 1〜3 と同じ。空で作った Component の中断再開で `initialFields` が適用されないのは PR 以前からの挙動 |
| S-U3 / Q-I2 / D-U2 | ラウンド 2・3 と同じ。relocate 後に移動元 Slot の sibling の `componentIndex` を保存し直さないのは通常の relocate と同じ既存の挙動。誤束縛は再現されていない |
| S-U4 | ラウンド 1〜3 と同じ。ResoniteLink が作成直後に member を完全に返すかは実機での確認事項 |
| D-L1 | ラウンド 1〜3 と同じ。置換元がすでに無くても再読込後に停止するのは fail-closed の設計判断。レビュアーも【要設計判断】としている。ヒントは `929c9ae` で「旧 Component がまだある」と断定しない文言になっている |
| D-I2 | ラウンド 1〜3 と同じ。参照検査の範囲を plan で警告するのは機能追加の提案 |
| D-I3 | ラウンド 2・3 と同じ。置換側がすでに無い key が prune 後も state に残るのは、Component が消えた key を `BuildDeletionPlans` が `continue` で残す既存の挙動と同じ |
| D-U1 | ラウンド 3 と同じ。レビュアー自身が実行で確認していない未検証候補（同じ Node に recreate と relocation が同居する場合の index） |
| D-U3 | 作成（recreate でない）の再開で管理外の Component を型と位置で採用する点は、ラウンド 3 の「残る制約」と同じ（保存 ID が無い以上、型・member 名・位置でしか照合できない）。削除は伴わない。state の `id` が欠けると保持分の除外が効かない点は、この実装が書く state には必ず `""` 以上が入り、欠けるのは手編集だけ |

論点として残すもの: relocate の中断区間（S-L3・S-I3）と移動元 Slot の index（S-U3 ほか）は、relocate 全体の設計として別途扱う（ラウンド 2・3 と同じ）。

## 修正方針

### G9: 保存 ID が空の key は、この apply が同じ Slot で取り除く Component を除いた配置で照合する（O-L6）

原因: 作り直しのある Slot では、`AssignComponentIndexes`（`WorldService.cs:1217-1226`）が各 key の `componentIndex` を「作り直しで取り除く Component を除き、新しい Component を末尾に足した最終配置」で決め、作成前の checkpoint（`WorldService.cs:469-470`）でその値を保存する。ところが再実行時の照合（`WorldService.cs:1085-1087`）は、その key 自身の `superseded` だけを除いた配列を使う。他の key が作り直しで取り除く Component（旧 `renderer`）は配列に残るため、保存 index が 1 つずれて他の key の保持分を指し、`MatchComponent` の `held` 判定で `null`（作成）になる。宣言順が `extra` → `renderer` のときは、`renderer` の作成前の checkpoint が走っていないため、state に `supersededId` も残らない。

変更（`WorldService.cs`）:

- Slot ごとに、この apply が作り直しで取り除く Component の ID の集合を、各 key の照合の前に求める関数を足す（仮称 `RecreatedOnNode(prepared, node)`）。同じセッションの場合だけ求め、次の 2 つを入れる:
  - その Slot の宣言済み key の state にある `supersededId` のうち、Slot 上に残っているもの
  - その Slot の宣言済み key のうち、保存 ID で Slot 上の Component に結び付き、`ListShrinkReason` が作り直しを返すもの（宣言順が前の key が中断した場合、まだ state に `supersededId` が無いため）
- stable key（`spec.Key ?? "<slot>/component:<type>:<ordinal>"`）を求める処理は `BuildComponentPlans` と共有する（小さな列挙ヘルパに切り出し、同じ規則を 2 か所に書かない）。
- `HeldByOtherKeys` が集合を返す場合（同じセッションで保存 ID が空の key）だけ、照合する配列から上の集合を除く。保存 ID がある key、別セッション、relocate の移動元の照合は変えない。
- 取り除く集合の Component はどれも他の key が保持しているため、`held` があれば採用されない。除くことで変わるのは index の位置だけで、保存 index と同じ基準（最終配置）で照合できるようになる。
- `HeldByOtherKeys` の上のコメントと新しい関数のコメントに、この規則（保存 index は作り直し後の配置なので、ID の無い key は同じ配置で照合する）を書く。

残る制約: 中断のあと再実行までに文書を変え、中断した apply で予定していた作り直しが再実行では起きなくなった場合は、保存 index が作り直し後の配置を指したままになり、他の key の保持分を指せば作成（重複）になる。中断中に文書を変える操作に限られ、今回は扱わない。

検証（`tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` に既存の作法で追加。`ShrinkDocument` に `renderer` の前に置く Component を渡す省略可能な引数を足す。いずれも HEAD で失敗することを確認する）:

1. `renderer` を 3 要素に縮める文書に、同型の新しい key `extra`（`Materials: ["$ref:m4"]`、`Label: "east"`）を加える。`AfterComponentAdded` で `extra` の作成時だけ `LoseNextComponentCreateResponse` を立てて中断する。`extra` を `renderer` の後に置く場合と前に置く場合の Theory。再実行後に Rubble の `Test.Renderer` が `renderer`（north・3 要素）と `extra`（east）の 2 つだけで、state の `extra` が中断で作られた Component を指し、`renderer` の state に `supersededId` が無い。3 回目の apply の書き込みは 0

### G10: 作り直しのある Slot では、Component を作る前に、束縛済みの Component の `componentIndex` を最終配置で保存する（O-L7）

原因: 作成ループ（`WorldService.cs:452-481`）は宣言順に各 key の state を保存する。作り直す key の作成（作成前の失敗・作成応答の喪失）で apply が止まると、それより後に宣言した key の `componentIndex` は作り直し前の値のまま残る。再読込後のヒントどおりに旧 Component（と置換）を削除すると、Slot は最終配置になるが、sibling の保存 index は古いままなので、同型 sibling が 2 つ以上あると index の tie-break が別の sibling を指し、`STABLE_COMPONENT_AMBIGUOUS` で止まる。置換の作成後に止まった場合（`before-remove`）は、作成ループが全 key を最終配置で保存し終えているため収束する。

変更（`ApplyAsync` の作成ループの直前）:

- 作り直し（`Superseded` を持つ Component）がある Slot について、その Slot の束縛済みの Component（`Existing` がある）の state の `componentIndex` だけを、計画時に決めた最終配置の値に書き換え、1 回 checkpoint する。`UndoRecreateState` が sibling の index を保存し直すのと同じ要領（`saved with { ComponentIndex = … }`）で、state に既にある key だけを対象にする。
- 作り直しの無い apply では何もしない（checkpoint も増やさない）。
- 作成ループが後で同じ値を書くので、apply が最後まで進んだときの state は変わらない。変わるのは、作り直す key の作成で止まったときに残る sibling の index だけで、`before-remove` で止まったときと同じ状態になる。
- 置換の作成より前に止まったあと、ヒントに従わず「作り直しをやめて旧 Component に戻す」操作をした場合は、sibling の index が最終配置を指したままになる。これは現行 HEAD の `before-remove` の中断と同じ状態であり、ヒントは位置で候補を選ばないよう案内している。

検証:

2. `InterruptedRecreateNextToASameTypeSiblingRecoversAfterWorldReloadByFollowingTheHint` と同じ手順で、`renderer` の後に同型の sibling を 2 つ（`sibA`: south、`sibB`: east、どちらも 4 要素）置くケースを `before-add`・`lost-add-response` の Theory で加える。ヒントどおりに操作した再実行が成功し、`renderer` が 3 要素で収束し、`sibA`・`sibB` の ID・state・リストが変わらない。再 apply の書き込みは 0。既存の sibling 1 つの 3 ケースも引き続き成功する

### G11: 作り直しの取り消しで削除するのは、この apply が作った置換か、保存 ID で結び付いた置換だけにする（D-H2・S-U1）

原因: 検証ループ（`WorldService.cs:490-512`）は、置換のリストが宣言より長いと、その置換を無条件に削除して作り直しを取り消す。再開した作り直しでは、置換は `MatchComponent` で束縛されるが、保存 ID が空（作成前の中断・作成応答の喪失）か、保存 ID の Component が無い（手で削除された）ときは、型・member 名・位置だけで束縛する。候補が管理外の同型 Component 1 つだけなら、それが置換になり、削除される。

変更（検証ループと `UndoRecreateState`）:

- 置換が「この apply で作った」（`Existing` が null）か「保存 ID で結び付いた」（`PreviousState.Id` が `Existing.Id` と一致）場合は、現行どおり削除して取り消す。
- それ以外（型と位置だけで束縛した）場合は削除しない。state は現行どおり旧 Component に戻す（`id` を旧 Component、`supersededId` なし）。`UndoRecreateState` に「置換を残す」引数を足し、残した置換を Slot 上にあるものとして sibling の `componentIndex` を計算する。
- どちらの場合も `APPLY_LIST_SHRINK_NOT_CONVERGED` で停止する（エラーコードは増やさない）。残した場合は、メッセージを「置換として照合した Component は保存 ID ではなく型と位置で見つけたものなので残した。旧 Component を保った」という趣旨にし、context の `removedReplacementId` の代わりに `keptComponentId` を返す。ヒントは「中断した apply がこの Component を作ったのなら Resonite で削除して再実行する。そうでなければこの文書の管理外なので、そのまま再実行すれば Component を作り直す」とする。
- 採用した管理外の Component にこの時点で書き込みはしていない（フィールドの設定は検証ループの後）ので、残した Component は変わらない。

トレードオフ: 作成応答を失った置換を runtime が refill した場合（中断した apply が自分で作った置換）も、型と位置で束縛するため削除せずに残る。利用者が Resonite で削除するまで Slot に残るが、context とヒントで ID を示す。管理外の Component を削除するより安全側に倒す。

残る制約（ラウンド 3 と同じ）: 保存 ID が無い再開で、管理外の同型 Component のリストが宣言以下なら、それを置換として採用してフィールドを書き換え、旧 Component を削除する。保存 ID が無い以上、型・member 名・位置でしか照合できないため、今回は扱わない。

検証:

3. 作り直しの再開と管理外の Component（Theory）:
   - `before-add`（`FailOnWrite=1`）で中断し、管理外の同型 Component（`Label: "west"`、`Materials` 4 要素）を追加する
   - `before-remove`（`FailOnWrite=2`）で中断し、置換を手で削除してから、同じ管理外 Component を追加する（S-U1）

   いずれも再実行が `APPLY_LIST_SHRINK_NOT_CONVERGED` で停止し、書き込みが 0、管理外 Component の ID・`Label`・リストが変わらず、旧 Component が残り、state の `renderer` が旧 Component を指して `supersededId` が無く、context の `keptComponentId` が管理外 Component を指す。続けてもう一度 apply すると、作り直しが完了して `renderer` が 3 要素で収束し、管理外 Component は変わらない。その次の apply の書き込みは 0
4. `lost-add-response` と refill（`RefillRenderers`）で中断し、同じセッションで再実行すると、中断で作られた置換を削除せずに `APPLY_LIST_SHRINK_NOT_CONVERGED` で停止し、`keptComponentId` がその置換を指す（上のトレードオフを固定する）
5. 既存の `ResumedRecreateThatTheRuntimeRefilledStopsAndKeepsTheOriginal`（保存 ID で結び付いた置換は削除する）が引き続き成功する

## 反映の手順（承認後）

実装は `fix/list-shrink-recreate` を checkout した worktree（`external/resoloop/.worktrees/fix-list-shrink-recreate`）で行う。着手前に、その worktree が clean で HEAD が `origin/fix/list-shrink-recreate`（`929c9ae`）と一致することを確かめる。一致しなければ停止して報告する（2026-09-30 の計画時点では clean・一致を確認済み）。

1. 関連テスト: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter "FullyQualifiedName~ApplyWorkflowTests"`
2. 変更の種類に応じた検証（resoloop fork の変更）: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj`
3. `fix/list-shrink-recreate` に commit し、`git push origin HEAD` で既存 PR #5 に反映する。新しい PR や `*-review-fixes` ブランチは作らない
4. PR #5 の review-fix-planning コメント（`claude-opus-5-5` のマーカー）を更新する

`scripts/resoloop-fork.sh test` による全テストと、ワールドのプロジェクトの `uv run pytest` は反映の条件にしない。

## 範囲外と注意

- ラウンド 1〜3 と同じく、ベースの `fix/asset-url-save-migration` は PR #5 の分岐後に先へ進んでおり、追従時に競合する見込みが高い。今回もベースへの追従は行わない。
- 作り直し時に runtime 値を引き継ぐか（ラウンド 1 の O-M1a）、非同期 refill の実機確認（O-L3）、relocate の中断区間（S-L3・S-I3）は、別途判断が必要な論点として残す。
- ドキュメント（`docs/DECLARATIVE.md` など）への停止コードの復旧手順の追記は行わない（O-I1 ほか）。復旧手順はエラーのヒントを正本とする。
