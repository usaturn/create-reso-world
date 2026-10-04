# list-shrink-recreate レビュー指摘の修正設計（ラウンド 5）

- 日付: 2026-09-30
- 対象 PR: usaturn/resoloop #5（`fix/list-shrink-recreate` → `fix/asset-url-save-migration`）
- 現行 HEAD: `616c510b6ffeb85693124e3eebdd8df33aed0dad`（ラウンド 4 の修正コミット）
- 入力: `external/resoloop/reviews/#5-fix-list-shrink-recreate/`（5 件）
  - `claude-opus-5-5.md`（対象 HEAD `616c510`）
  - `SWE-2-Max.md`（対象 HEAD `616c510`）
  - `qwen3.8-max.md`（対象 HEAD `616c510`）
  - `deepseek-deepseek-v4.1-flash.md`（対象 HEAD `616c510`。今回が初回）
  - `commandcode-deepseek-deepseek-v4.1-flash.md`（対象 HEAD `929c9ae`。ラウンド 4 以降は更新されていない）
- 前回: `docs/superpowers/specs/2026-09-30-list-shrink-recreate-round4-review-fixes-design.md`（ラウンド 4。G9〜G11 を `616c510` で反映済み）
- brainstorming の経路: **bounded**（`WorldService.cs` の既存の作成ループと照合の流れを直す修正。state の形式とエラーコードの集合は変えない）

## 目的と成功条件

- 目的: 作り直しを含む apply が途中で止まったあと、ワールドを再読込しても、state を手で直さずに収束すること。保存 ID の無い key が、位置だけで束縛した管理外 Component を `--prune` なしで削除しないこと。
- 制約: ラウンド 4 までの修正（L-6・L-7・D-H2）を壊さない。変更前に止まる既存の停止は緩めない。state の形式とエラーコードの集合は変えない。修正は PR #5 のブランチに載せる。
- 成功条件: 下記の再現テストが修正前に失敗し、修正後に成功すること。既存の `ApplyWorkflowTests` 148 件がすべて成功すること。

## 検証の方法

`git -C external/resoloop worktree add --detach` で `616c510` を一時 worktree に取り出し、偽クライアント（`ApplyWorkflowTests`）で再現テストを書いて `dotnet test --filter "FullyQualifiedName~ApplyWorkflowTests"` で実行した。未改変の `616c510` では既存の 148 件がすべて成功した。修正案も同じ worktree で試作し、既存テストと再現テストを流した。worktree と一時ディレクトリは検証後に削除済み。

表の `C5(north,4)` は「ID C5・`Label` が `north`・`Materials` が 4 要素の `Test.Renderer`」を表す。`ApplyFourMaterialsAsync` で 4 要素の `renderer` を作ったあと、3 要素に縮める文書で apply した。

| 再現 | HEAD（`616c510`） | 試作した修正 |
| --- | --- | --- |
| O-L8: `renderer` の後に同型の `sibling`（south、4 要素）を宣言。Rubble の先頭に新しい key `marker`（`Test.Material`）を足し、その作成を `FailOnWrite=1` で失敗させる → `ReloadWorld` → 再実行 | 中断後の state は `renderer{id=C5, supersededId なし}`・`sibling{componentIndex=0}`（実際は 1）。再実行は `APPLY_COMPONENT_OWNERSHIP_CONFLICT`（`sibling` の live と `renderer` の superseded が同じ Component）、書き込み 0。state は変わらないので、何度再実行しても同じ停止になる | 中断後の `sibling` は `componentIndex=1`。再実行は書き込み 3 で `[south, north(3)]` に収束 |
| O-L8: 同上で sibling が 2 つ（south・east） | 同じく `APPLY_COMPONENT_OWNERSHIP_CONFLICT`、書き込み 0 | 中断後の index は 1・2。書き込み 3 で `[south, east, north(3)]` に収束 |
| O-L8（対照）: 同上で再読込しない | 収束する | 収束する |
| O-L8 の変形: `sibling` を `renderer` より前に宣言するが、Slot 上では `renderer` の後ろにある（後の apply で追加した）。`sibling`・`marker`・`renderer` の順に宣言して `marker` の作成で失敗 → `ReloadWorld` → 再実行 | `sibling` は自分の checkpoint で最終配置の `componentIndex=0` を保存する。再実行は `APPLY_COMPONENT_OWNERSHIP_CONFLICT`、書き込み 0（`929c9ae` 以前からある経路） | 中断後の `sibling` は `componentIndex=1`。書き込み 3 で収束 |
| O-L9: 同型の新しい key `extra`（`Materials: ["$ref:m4"]`、`Label: "east"`）を足す apply を `FailOnWrite=1` で `extra` の作成前に止める（state は `extra{id="", componentIndex=1}`）→ 管理外の同型 C6（west、4 要素）を追加 → 再実行（同じセッションと `ReloadWorld` 後） | plan は `recreate …/@extra list member Materials shrinks from 4 to 1`。apply は書き込み 2（作成・削除）で成功し、管理外の C6 が削除される | `STABLE_COMPONENT_AMBIGUOUS`（`candidateIds: [C6]`）で変更前に停止。書き込み 0、C6 は変わらない |
| N-H1: 作り直しを `before-add`（`FailOnWrite=1`）で中断 → 管理外の同型 C6（west、1 要素）を末尾に追加 → 同じセッションで再実行 | C6 を置換として採用し、`[C6(north,3)]` に書き換えて C5 を削除する（書き込み 2） | 変わらない（今回は扱わない。下記「対応しない」） |
| N-M1: 作り直しを `lost-add-response` で中断 → 管理外の同型 C7（west、1 要素）を Slot の先頭に追加 → 同じセッションで再実行 | C7 を置換として採用して `[C7(north,3), C6(north,3)]`。中断時に作られた C6 は管理外で残る | 変わらない（同上） |
| 既存テスト | `ApplyWorkflowTests` 148 件がすべて成功 | 148 件と再現テストがすべて成功 |

## 分類

解消済み 14 / 対応する 3 / 判断保留 0 / 対応しない 26（計 43）。これとは別に、ユーザ指示による追加が 1 件（O-L8 の変形、(d)）ある。

ID の接頭辞は O = claude-opus-5-5、S = SWE-2-Max、Q = qwen3.8-max、N = deepseek-deepseek-v4.1-flash、D = commandcode-deepseek-deepseek-v4.1-flash。U は各レビューの Unverified candidates の番号（記載順）。前回までと同じ ID でも、今回のファイルでの番号を使う（例: S-U4 は今回の 4 件目の候補）。

### 解消済み

未改変の `616c510` で、該当テストを含む `ApplyWorkflowTests` 148 件がすべて成功することを確認した。

| ID | 根拠 |
| --- | --- |
| O-M1 | 作り直しで `initialFields` と未宣言 member が初期値に戻ることを `docs/DECLARATIVE.md:57`・`README-DETAILS.md:181`・`skills/codex/resonite-build/SKILL.md` に明記済み |
| O-L1 | `UndoRecreateState` が sibling の `componentIndex` を保存し直す。`UndoneRecreateKeepsSiblingIndexesSoAWorldReloadStillBindsThem` が成功 |
| O-L2 | `BuildDeletionPlans` が旧 Component の削除を先に計画する。`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` が成功 |
| O-L4 | `InterruptedRecreateNextToASameTypeSiblingResumes`（2 ケース）・`InterruptedCreateOfANewKeyNextToAManagedSameTypeComponentResumes` が成功 |
| O-L5 | `InterruptedRecreateNextToSameTypeSiblingsRecoversAfterWorldReloadByFollowingTheHint`（sibling 1 つの 3 ケース）が成功 |
| O-L6 | ラウンド 4 の G9（`RecreatedOnNode`）。`ResumedCreateOfANewKeyNextToARecreateBindsWhatItCreated`（2 ケース）が成功 |
| O-L7 | ラウンド 4 の G10。`InterruptedRecreateNextToSameTypeSiblingsRecoversAfterWorldReloadByFollowingTheHint`（sibling 2 つの 2 ケース）が成功。ただし G10 の実装位置が O-L8 の回帰を生んだ（下記 G12 で位置を直す） |
| S-M1 | 検証前の置換を `byKey` に入れない。`UndoneRecreateLeavesNoReferenceToTheRemovedReplacement` が成功 |
| S-L2 | 旧 Component を snapshot 全体から探し、relocate・宣言削除でも削除する。`Moving…`・`Pruning…`・`InterruptedRecreateStopsBeforeMutationAfterWorldReloadWhenTheKeyMovesOrIsRemoved` が成功 |
| S-M2 | relocate の移動元の照合にも `HeldByOtherKeys` を渡す。`InterruptedCreateOfANewKeyThatMovesIsCreatedOnTheNewSlot` が成功 |
| Q-M1 | S-L2 と同じ修正・テスト |
| Q-M2 | `VerifiesRecreate` で再開した作り直しも refill を検証する。`ResumedRecreateThatTheRuntimeRefilledStopsAndKeepsTheOriginal` が成功 |
| D-H1 | `HeldByOtherKeys` が候補の配列を縮めない。`ResumedRecreateBindsItsReplacementNextToAnUnmanagedSameTypeComponent`・`ResumedCreateOfANewKeyBindsWhatItCreatedNextToAnUnmanagedSameTypeComponent`（各 2 ケース）が成功 |
| D-H2 | ラウンド 4 の G11（位置で束縛した置換は削除せず `keptComponentId` で報告する）。`UndoneRecreateKeepsAReplacementMatchedWithoutItsSavedId`（2 ケース）が成功。レビューは `929c9ae` のまま更新されていないが、`616c510` では再現しない |

### 対応する

| ID | 区分 | 一行 |
| --- | --- | --- |
| O-L8 | (a) | `616c510` の G10 の回帰。作り直しのある Slot で、作成ループの前に sibling の `componentIndex` を最終配置で保存するため、作り直す key の `supersededId` を保存する前に止まってワールドを再読込すると、sibling が旧 Component に束縛されて `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で止まり続ける。state を手で直す以外に収束させる手段が無い。sibling 1 つ・2 つとも再現した |
| Q-U1 | (a) | O-L8 と同じ経路。レビュアーは「変更前の停止に収まる」としたが、その停止は state が変わらないため何度再実行しても続き、収束しないことを再現で確かめた |
| O-L9 | (a) | 保存 ID の無い key（作成前に中断した新しい key）が、型と位置だけで管理外の同型 Component を束縛し、そのリストが宣言より長いと作り直し対象にして `--prune` なしで削除する。fork の `AGENTS.md`（Resonite safety）の「Do not change existing user content」に反する。ラウンド 4 で D-U3 を「削除は伴わない」として見送ったが、その前提は誤りだった。同じセッションと再読込後の両方で再現した |

ユーザ指示による追加:

| ID | 区分 | 一行 |
| --- | --- | --- |
| O-L8 の変形 | (d) | 作り直す key より前に宣言した sibling が Slot 上で旧 Component より後ろにあると、sibling 自身の checkpoint が最終配置の index を保存するため、O-L8 と同じ食い違いで止まり続ける。レビューには挙がっていないが、O-L8 の修正を試作する過程で見つけ、`616c510` で再現した。ユーザの判断で G12 の修正範囲に含める |

### 判断保留

なし。

### 対応しない

| ID | 理由 |
| --- | --- |
| O-L3 | ラウンド 1〜4 と同じ。実機で非同期に refill されるリストがあるかは未確認で、偽クライアントでは再現できない。対策には state に作り直しの履歴を残す設計が要る |
| O-U1 / Q-L1 | ラウンド 1〜4 と同じ。空で作った置換の再開時に refill を見逃すのは、runtime がフィールド設定をきっかけにリストを埋め直す場合に限られ、実機の挙動が未確認。次の apply で `NOT_CONVERGED` として検出される |
| O-I1 / S-I1 / D-I1 / Q-I1 | ラウンド 1〜4 と同じ。`recreate` と新しいエラーコード 3 件の記載漏れ（Info）。README の例に action の一覧は無く、fork の `AGENTS.md` は skill を「workflows, not command mirrors」とする。停止コードはヒントで復旧手順を示す。qwen は作者の判断として解消扱いにしている |
| S-L1 | ラウンド 1〜4 と同じ。`--prune` で消える Component からの参照も数えるのは、変更前に止まる安全側の停止。緩めるかは仕様の判断 |
| S-L3 | ラウンド 2〜4 と同じ。通常の relocate も同じ中断区間で移動元を残す既存の挙動。塞ぐには state に削除待ちの ID を別に持たせる設計変更が要る |
| S-I2 | ラウンド 1〜4 と同じ。偽クライアント `SetFields` に該当する入力は現行テストに無い |
| S-I3 | ラウンド 4 と同じ。作り直しの中断・その key の relocate の中断・再読込の 3 つが重なる場合に限る。変更前に停止し、候補を絞れなければ Resonite で確認するヒントが残る。relocate 全体の設計として別途扱う |
| S-U1 | レビュアー自身が実行で確認していない未検証候補（保存 ID が古い key が別の Component を作り直し、同じ Slot の ID の無い key と同じ Component を指す場合）。レビュアーの分析でも、変更前の `APPLY_COMPONENT_OWNERSHIP_CONFLICT` に収まる。管理 Component の手動削除など複数の条件が重なる必要がある |
| S-U2 | ラウンド 1〜4 と同じ。空で作った Component の中断再開で `initialFields` が適用されないのは PR 以前からの挙動 |
| S-U3 / Q-I2 / D-U2 | ラウンド 2〜4 と同じ。relocate 後に移動元 Slot の sibling の `componentIndex` を保存し直さないのは通常の relocate と同じ既存の挙動。誤束縛は再現されていない |
| S-U4 | レビュアー自身が実行で確認していない未検証候補（relocate の移動元の照合に `RecreatedOnNode` の除外が効かない）。レビュアーの見込みでも、多くは新規作成に落ちる。relocate 全体の設計として別途扱う |
| S-U5 | ラウンド 1〜4 と同じ。ResoniteLink が作成直後に member を完全に返すかは実機での確認事項 |
| N-H1 | ラウンド 3・4 の「残る制約」と同じ。作り直しの置換を作る前に止まったあと、管理外の同型 Component（リストが宣言以下）が 1 つだけあると、それを置換として採用して書き換える（再現済み）。作成要求を送る前に止まったのか、作成応答を失ったのかは今の state では区別できない。区別するには state の形式を変えるか、作成応答を失った置換の自動再開（`InterruptedListShrinkRecreateResumesWithoutDuplicates` などが固定する既存の挙動）をやめる設計判断が要る |
| N-M1 | N-H1 と同じ原因（保存 ID の無い再開は位置で照合する）。管理外 Component を Slot の先頭に挿入する操作が実機でできるかも未確認（偽クライアントの `PrependComponent` で再現）。N-H1 と合わせて設計判断として扱う |
| N-U1 | レビュアー自身が実行で確認していない未検証候補（中断が 2 回続く場合の index） |
| D-L1 | ラウンド 1〜4 と同じ。置換元がすでに無くても再読込後に停止するのは fail-closed の設計判断。レビュアーも【要設計判断】としている |
| D-I2 | ラウンド 1〜4 と同じ。参照検査の範囲を plan で警告するのは機能追加の提案 |
| D-I3 | ラウンド 2〜4 と同じ。置換側がすでに無い key が prune 後も state に残るのは、Component が消えた key を `BuildDeletionPlans` が残す既存の挙動と同じ |
| D-U1 | ラウンド 3・4 と同じ。レビュアー自身が実行で確認していない未検証候補（同じ Node に recreate と relocation が同居する場合の index） |
| D-U3 | 作成の再開で管理外 Component を型と位置で採用して書き換える点は、N-H1 と同じ「残る制約」。ラウンド 4 の判断理由の「削除は伴わない」は誤りで、リストが宣言より長いと削除まで進むことを O-L9 として対応する。state の `id` が欠けると保持分の除外が効かない点は、この実装が書く state には必ず `""` 以上が入り、欠けるのは手で編集した場合だけ |

論点として残すもの:

- 保存 ID の無い再開が管理外の同型 Component を採用して書き換える（N-H1・N-M1・D-U3）。作成要求の送信を state に記録するなど、state の形式を変える設計として別途扱う。
- relocate の中断区間（S-L3・S-I3）と移動元 Slot の index（S-U3 ほか）は、relocate 全体の設計として別途扱う（ラウンド 2〜4 と同じ）。

## 修正方針

### G12: `supersededId` を保存するまでは、束縛済み Component の `componentIndex` を実際の配置で保存する（O-L8・Q-U1・O-L8 の変形）

原因: ラウンド 4 の G10 は、作り直しのある Slot について、作成ループに入る前に束縛済み Component の `componentIndex` を最終配置（旧 Component を除き、新しい Component を末尾に足した配置）で保存し、checkpoint する（`WorldService.cs:452-462`）。作り直す key の `supersededId` は、その key の作成直前の checkpoint で初めて保存される（`WorldService.cs:480-481`）。その間（先に処理される新しい key の作成失敗、接続断、キャンセル）で止まると、state には「作り直す key は旧 ID のままで `supersededId` なし」「sibling は最終配置の index」という食い違いが残る。同じセッションなら保存 ID で照合するので問題ないが、再読込後は保存 index で照合する（`WorldService.cs:1982-1986`）ため、sibling の index が旧 Component を指し、作り直す key の superseded と sibling の live が同じ Component を指して `APPLY_COMPONENT_OWNERSHIP_CONFLICT`（`WorldService.cs:1536-1557`）で止まる。state は変わらないので、再実行しても同じ停止を繰り返す。変形は同じ食い違いが別の順序で起きるもので、作り直す key より前に処理される束縛済み Component が、自分の checkpoint（`WorldService.cs:487-489`）で最終配置の index（`AssignComponentIndexes`、`WorldService.cs:1128-1131`）を保存することによる。

守る規則: 作り直しのある Slot では、その Slot で最初に `supersededId` を state に書く checkpoint までは、束縛済み Component の `componentIndex` を実際の配置（作り直し前）の値で保存する。その checkpoint で、束縛済み Component をすべて最終配置の値で保存し直す。

変更（`ApplyAsync` の作成ループ）:

- 作成ループの前にある index の保存し直しと checkpoint（`WorldService.cs:452-462` の `if` ブロック）を削除する。`recreatingNodes` の集合は残し、「まだ `supersededId` を保存していない作り直しのある Slot」として使う。
- 作成ループで `Superseded` を持つ Component を処理するとき、その Slot で最初のもの（`recreatingNodes.Remove(component.Node)` が真）なら、その Component の最初の checkpoint の前に、同じ Slot の束縛済み Component（`Existing` がある）の state の `componentIndex` を最終配置の値（`ComponentIndex`）に書き換える。新しく作る場合は作成直前の checkpoint（ここで `supersededId` を書く）、再開した作り直し（`Existing` がある）の場合は解決後の checkpoint（`supersededId` は前回の apply で保存済み）に一緒に載る。
- 作成ループで束縛済み Component の state を保存するとき（`WorldService.cs:487-489`）、その Slot がまだ `recreatingNodes` にあれば、`componentIndex` を実際の配置の値（`node.Existing.Components` での位置）で保存する。
- 新しく作る key（`Existing` が無い）の index は変えない。作成直前の checkpoint で保存する最終配置の index は、ラウンド 4 の G9（同じセッションで保存 ID の無い key を作り直し後の配置で照合する）が前提にしている。
- フィールドのループ以降は変えない。作成ループを抜けた時点で、作り直す key はすべて `supersededId` を保存済みで、sibling も最終配置で保存し直している。
- 作成ループの前にあったコメントを、上の規則に合わせて書き直す（最初の `supersededId` と同じ checkpoint で保存し直す理由と、それまでは実際の配置を保存する理由）。

結果: 最初の作り直しの checkpoint より前に止まった場合は、state が作り直し前の配置のままで `supersededId` も無いので、再読込後も `929c9ae` と同じく収束する。その checkpoint 以降に止まった場合は、`supersededId` と最終配置の index が揃い、L-7 の対策どおり再読込後のヒントで収束する。

検証（`tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` に既存の作法で追加。いずれも `616c510` で失敗することを確認する）:

1. 作り直しより先に処理される新しい key の作成で止まり、再読込後に再実行する Theory。Rubble の先頭に新しい key `marker`（`Test.Material`）を宣言し、`FailOnWrite=1` でその作成を失敗させる。パラメータは次の 3 通り:
   - `renderer` の後に同型の sibling を 1 つ（south、4 要素）
   - `renderer` の後に同型の sibling を 2 つ（south・east、4 要素）
   - sibling を `renderer` の前に宣言する（先に `renderer` だけの文書と、sibling を先頭に足した 4 要素の文書を apply して、Slot 上では sibling が `renderer` の後ろにある状態を作る）

   中断後の state の `renderer` に `supersededId` が無いことを確かめ、`ReloadWorld` のあと再実行する。再実行が成功し、`renderer` が 3 要素になり、sibling の ID・state・4 要素のリストが変わらないこと、次の apply の書き込みが 0 であることを確かめる。
2. 既存の `InterruptedRecreateNextToSameTypeSiblingsRecoversAfterWorldReloadByFollowingTheHint`（5 ケース）と `ResumedCreateOfANewKeyNextToARecreateBindsWhatItCreated`（2 ケース）が引き続き成功する。

### G13: 保存 ID の無い key が位置だけで束縛した Component は、作り直さずに変更前に停止する（O-L9）

原因: `BuildComponentPlans` は、束縛した Component のリストが宣言より長ければ、束縛の根拠を問わず作り直し対象にする（`WorldService.cs:1106-1107`）。作成前に中断した新しい key は state の `id` が空で、型・member 名・保存 index だけで照合する（`MatchComponent`、`WorldService.cs:1900-1925`）。保存 index の位置に管理外の同型 Component が来ると、それを束縛して作り直し対象にし、旧 Component の削除（`WorldService.cs:566-575`）で `--prune` なしに削除する。plan には `recreate` と縮小の理由しか出ず、削除されるのが管理外 Component だとは分からない。

変更（`BuildComponentPlans`）:

- `ListShrinkReason` が作り直しを返し、`superseded` が無いとき（作り直しの再開ではないとき）に、state の `id` が空（`stateComponent?.Id is { Length: 0 }`）なら、作り直し対象にせず `STABLE_COMPONENT_AMBIGUOUS` で停止する。plan・apply とも prepare の段階で止まるので書き込みは起きない。
  - エラーコードは既存の `STABLE_COMPONENT_AMBIGUOUS` を使う（エラーコードの集合を変えない）。保存 ID で確定できない Component を採用しないという意味で、既存テスト `InterruptedCreateOfANewKeyDoesNotAdoptAnUnmanagedSameTypeComponent`（管理外 Component が中断前からあった場合）と同じ結果に揃う。
  - メッセージは、この key の作成が中断して ID が保存されていないこと、Component `<id>` を型と位置だけで照合したこと、その Component のリストが宣言より長いこと、管理外の Component かもしれないので作り直さないこと、変更は何もしていないことを述べる。
  - context は既存の `STABLE_COMPONENT_AMBIGUOUS` と同じ形（`candidateIds` に束縛した Component の ID、`type`）に、`componentKey` を加える。
  - ヒントは次の 2 つ。「中断した apply が Component `<id>` を作ったのなら、Resonite で削除する。そうでなければこの文書の管理外なので、そのまま残す」「そのあと state ファイルからこの key を外して再実行すると、apply がこの key の Component を作る」。state に無い key は管理済みの Slot では照合せずに作成する（`newManagedComponent`）ので、この手順で収束する。
- 対象は state の `id` が空の key だけにする。保存 ID がある key は変えない。再読込後は ID が振り直されるため位置で照合するのが通常の経路であり、ここを止めると再読込後の作り直しができなくなる。作り直しの再開（`supersededId` がある）はラウンド 4 の G11 が扱うので変えない。リストが宣言以下の場合の採用（N-H1・D-U3）も変えない。

トレードオフ: 中断した apply が作った Component の作成応答を失い、その Component のリストを runtime が埋め直した場合も停止する。これまでは作り直しに進み、新しい置換も埋め直されて `APPLY_LIST_SHRINK_NOT_CONVERGED` で止まっていた経路で、ヒントどおり Resonite で削除して key を外せば収束する。管理外 Component を削除するより安全側に倒す（ラウンド 4 の G11 と同じ方針）。

検証:

3. 新しい key の作成前に中断し、管理外の長いリストを持つ同型 Component を足してから再実行する Theory（同じセッションと `ReloadWorld` 後）。`ApplyFourMaterialsAsync` のあと、`extra`（`Materials: ["$ref:m4"]`、`Label: "east"`）を足した文書を `FailOnWrite=1` で apply して `extra` の作成前に止め、管理外の `Test.Renderer`（`Label: "west"`、`Materials` 4 要素）を追加する。
   - plan と apply が `STABLE_COMPONENT_AMBIGUOUS` で止まり、`candidateIds` が管理外 Component を指し、書き込みが 0 で、管理外 Component の `Label` とリストが変わらない
   - ヒントどおり state から `extra` を外して再実行すると成功し、`extra` が 1 要素で新しく作られ、管理外 Component は変わらない。次の apply の書き込みは 0
4. 既存の `InterruptedCreateOfANewKeyDoesNotAdoptAnUnmanagedSameTypeComponent`・`ResumedCreateOfANewKeyBindsWhatItCreatedNextToAnUnmanagedSameTypeComponent`・`UndoneRecreateKeepsAReplacementMatchedWithoutItsSavedId`・`ResumedRecreateKeepsARefilledReplacementWhoseCreateResponseWasLost` が引き続き成功する。

## 反映の手順（承認後）

実装は `fix/list-shrink-recreate` を checkout した worktree（`external/resoloop/.worktrees/fix-list-shrink-recreate`）で行う。着手前に、その worktree が clean で HEAD が `origin/fix/list-shrink-recreate`（`616c510`）と一致することを確かめる。一致しなければ停止して報告する（2026-09-30 の計画時点では clean・一致を確認済み）。

1. 関連テスト: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter "FullyQualifiedName~ApplyWorkflowTests"`
2. 変更の種類に応じた検証（resoloop fork の変更）: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj`
3. `fix/list-shrink-recreate` に commit し、`git push origin HEAD` で既存 PR #5 に反映する。新しい PR や `*-review-fixes` ブランチは作らない
4. PR #5 の review-fix-planning コメント（`claude-opus-5-5` のマーカー）を更新する

`scripts/resoloop-fork.sh test` による全テストと、ワールドのプロジェクトの `uv run pytest` は反映の条件にしない。

## 範囲外と注意

- ラウンド 1〜4 と同じく、ベースの `fix/asset-url-save-migration` は PR #5 の分岐後に先へ進んでおり、追従時に競合する見込みが高い。今回もベースへの追従は行わない。
- 作り直し時に runtime 値を引き継ぐか（ラウンド 1 の O-M1a）、非同期 refill の実機確認（O-L3）、relocate の中断区間（S-L3・S-I3）、保存 ID の無い再開での採用（N-H1・N-M1・D-U3）は、別途判断が必要な論点として残す。
- ドキュメント（`docs/DECLARATIVE.md` など）への停止コードの復旧手順の追記は行わない（O-I1 ほか）。復旧手順はエラーのヒントを正本とする。
