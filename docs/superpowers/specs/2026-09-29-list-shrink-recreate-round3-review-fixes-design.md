# list-shrink-recreate レビュー指摘の修正設計（ラウンド 3）

- 日付: 2026-09-29
- 対象 PR: usaturn/resoloop #5（`fix/list-shrink-recreate` → `fix/asset-url-save-migration`）
- 現行 HEAD: `30476c43d1e2ccb4b491d00feefcc31e7e748778`（レビュー対象 HEAD と同じ。ラウンド 2 の修正コミット）
- 入力: `external/resoloop/reviews/#5-fix-list-shrink-recreate/`（4 件とも対象 HEAD は `30476c43d1e2`。各指摘の検出時 HEAD は `d615eeb`・`dc1c651`・`30476c4`）
  - `claude-opus-5-5.md`
  - `SWE-2-Max.md`
  - `commandcode-deepseek-deepseek-v4.1-flash.md`
  - `qwen3.8-max.md`
- 前回: `docs/superpowers/specs/2026-09-29-list-shrink-recreate-round2-review-fixes-design.md`（ラウンド 2。G6 を `30476c4` で反映済み）
- brainstorming の経路: **bounded**（`WorldService.cs` の既存の照合とエラー生成を直す修正。state の形式は変えない。エラー context は候補ごとの値を追加するだけ）

## 検証の方法

`git -C external/resoloop worktree add --detach` で `30476c4` を一時 worktree に取り出し、偽クライアント（`ApplyWorkflowTests`）で再現テストを書いて `dotnet test --filter` で実行した。比較のため、同じ worktree で `WithoutHeldByOtherKeys` の呼び出しだけを外した版（`30476c4` 以前の照合）でも同じテストを実行した。修正案も同じ worktree で試作し、既存テストと再現テストを流した。worktree と一時ディレクトリは検証後に削除済み。

「管理外」は、どの state key も保持していない同型の `Test.Renderer`（`Label: "west"`）をテストから直接追加したもの。「中断後」はそれを中断した apply のあとに、「中断前」は中断する apply の前に追加した。

| 再現 | HEAD（`30476c4`） | フィルタ無し（`30476c4` 以前） | 試作した修正 |
| --- | --- | --- | --- |
| D-H1: 作り直しを `lost-add-response` で中断・sibling あり・管理外は中断後 | 管理外 C8 に束縛し、`Label` を書き換える。本物の置換 C7 は管理外のまま残る | 置換 C7 に束縛して収束 | 置換 C7 に束縛して収束 |
| D-H1: 同上・管理外は中断前 | `STABLE_COMPONENT_AMBIGUOUS` で停止（再実行しても同じ） | 置換 C8 に束縛して収束 | 置換 C8 に束縛して収束 |
| D-H1: 新しい key の作成を `lost-add-response` で中断・管理外は中断後 | 管理外 C7 に束縛する。作成済みの C6 は管理外で残る | C6 に束縛して収束 | C6 に束縛して収束 |
| D-H1: 同上・管理外は中断前 | `STABLE_COMPONENT_AMBIGUOUS` で停止 | C7 に束縛して収束 | C7 に束縛して収束 |
| D-H1（境界）: 作成前（`before-add`）に中断・管理外は中断前 | 管理外に束縛する | `STABLE_COMPONENT_AMBIGUOUS` で停止 | `STABLE_COMPONENT_AMBIGUOUS` で停止 |
| D-H1（境界）: 作成前に中断・管理外は中断後 | 管理外に束縛する | 管理外に束縛する | 管理外に束縛する（PR 以前からの挙動。下記「残る制約」） |
| S-M2: 新しい key の作成を `before-add` で中断 → その key を子 Slot `Debris` へ移す | plan・apply とも `APPLY_COMPONENT_OWNERSHIP_CONFLICT`（`renderer` の live と `extra` の relocation が C5 を取り合う）。再実行しても同じ | — | `Debris` に作成して収束。再 apply も成功 |
| S-M2: 同上を `lost-add-response` で中断 | 作成済みの C6 を移して収束 | — | 同じ |
| O-L5: `before-add` で中断 → 再読込（sibling 4 要素） | 停止。候補は旧 C11（4）と sibling C12（4）で、置換は存在しない。ヒントどおり C11 を消して `supersededId` を消すと `APPLY_COMPONENT_OWNERSHIP_CONFLICT` | — | — |
| O-L5: 同上（sibling 1 要素） | 同じく、ヒントどおりに直すと `APPLY_COMPONENT_OWNERSHIP_CONFLICT` | — | — |
| O-L5: `FailOnWrite=2` で中断 → 再読込（sibling 4 要素） | 停止。候補は C12（4）・C13（4）・C14（3）で、context には要素数しか無く、「リストが長いほう」が 2 件ある | — | — |
| O-L5: 復旧手順の比較 | `before-add`: 旧を消し、state から key ごと外す → 収束（sibling 4・1 要素とも）。`lost-add-response`: 旧だけ消して `supersededId` を消す → `APPLY_COMPONENT_OWNERSHIP_CONFLICT`（sibling の保存 index が古く、sibling が置換に束縛される）。この key の Component（旧と置換）をすべて消し、key ごと外す → 収束。`FailOnWrite=2`: 正しい旧を消して `supersededId` を消す → 収束 | — | — |
| 解消確認 | `FullyQualifiedName~ApplyWorkflowTests` の 132 件がすべて成功 | — | 132 件と再現テスト 19 件がすべて成功 |

## 分類

解消済み 8 / 対応する 5（修正は 3 系統）/ 判断保留 0 / 対応しない 21（計 34）。ID の接頭辞は O = claude-opus-5-5、S = SWE-2-Max、D = deepseek、Q = qwen3.8-max。U は各レビューの Unverified candidates の番号（記載順）。

### 解消済み

各レビューの Resolved findings に挙がったもの。現行 HEAD で該当テストを含む `ApplyWorkflowTests` 132 件の成功を確認した。

| ID | 根拠 |
| --- | --- |
| O-M1 | 作り直しで `initialFields` と未宣言 member が初期値に戻ることを `docs/DECLARATIVE.md:57`・`README-DETAILS.md:181`・`skills/codex/resonite-build/SKILL.md` に明記済み（ラウンド 1 の G5） |
| O-L1 | `UndoRecreateState` が sibling の `componentIndex` を保存し直す。`UndoneRecreateKeepsSiblingIndexesSoAWorldReloadStillBindsThem` が成功 |
| O-L2 | `BuildDeletionPlans` が旧 Component の削除を先に計画する。`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` が成功 |
| O-L4 | `30476c4` の G6。`InterruptedRecreateNextToASameTypeSiblingResumes`（2 ケース）・`InterruptedCreateOfANewKeyNextToAManagedSameTypeComponentResumes` が成功。今回の G7 で実現方法は変わるが、この 3 件は引き続き成功させる |
| S-M1 | 検証前の置換を `byKey` に入れない。`UndoneRecreateLeavesNoReferenceToTheRemovedReplacement` が成功 |
| S-L2 | 旧 Component を snapshot 全体から探して relocate・宣言削除でも削除し、再読込後は変更前に停止する。`Moving…`・`Pruning…`・`InterruptedRecreateStopsBeforeMutationAfterWorldReloadWhenTheKeyMovesOrIsRemoved` が成功 |
| Q-M1 | S-L2 と同じ修正・テスト |
| Q-M2 | `VerifiesRecreate` で再開した作り直しも refill を検証する。`ResumedRecreateThatTheRuntimeRefilledStopsAndKeepsTheOriginal` が成功 |

### 対応する

| ID | 区分 | 一行 |
| --- | --- | --- |
| D-H1 | (a) | `WithoutHeldByOtherKeys` が候補配列を縮めるため、保存した `componentIndex` と配列の位置がずれ、作成応答を失った中断の再開で管理外の同型 Component を採用するか、`STABLE_COMPONENT_AMBIGUOUS` で止まり続ける（`30476c4` 以前は収束していた回帰） |
| Q-U1 | (a) | D-H1 と同じ（index の意味ずれによる誤束縛）。再現を確認した |
| S-M2 | (a) | 作成前に中断した key を別 Slot へ移すと、移動元の照合に他の key の保持分の除外が無く、他の key の Component を移動元に選んで `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で止まり続ける |
| Q-U2 | (a) | S-M2 と同じ。再現を確認した |
| O-L5 | (a) | 再読込後の `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION` の候補に他の key の同型 Component が混ざり、ヒントは「もう一方の候補は置換」と断定する。置換の作成前（保存 ID が空）ではヒントどおりに直しても `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で止まり続け、sibling のリストが同じ長さだと旧 Component を区別できない |

### 判断保留

なし。

### 対応しない

| ID | 理由 |
| --- | --- |
| O-L3 | ラウンド 1・2 と同じ。実機で非同期に refill されるリストがあるかは未確認で、偽クライアントでは再現できない。対策には state に作り直しの履歴を残す設計が要る |
| O-U1 / Q-L1 | ラウンド 1・2 と同じ。空で作った置換の再開時に refill を見逃すのは、runtime がフィールド設定をきっかけにリストを埋め直す場合に限られ、実機の挙動が未確認。次の apply で `NOT_CONVERGED` として検出される |
| O-I1 / S-I1 / D-I1 / Q-I1 | ラウンド 1・2 と同じ。`recreate` と新しいエラーコード 3 件の記載漏れ（Info）。README の例に action の一覧は無く、fork の `AGENTS.md` は skill を「workflows, not command mirrors」とする。停止コードはヒントで復旧手順を自己記述する（O-L5 でその手順を正す）。qwen は作者の判断として解消扱いにしている |
| S-L1 | ラウンド 1・2 と同じ。`--prune` で消える Component からの参照も数えるのは、変更前に止まる安全側の停止。緩めるかは仕様の判断 |
| S-L3 | ラウンド 2 と同じ。通常の relocate も同じ中断区間で移動元を残す既存の挙動。塞ぐには state に削除待ちの ID を別に持たせる設計変更が要る |
| S-I2 | ラウンド 1・2 と同じ。偽クライアント `SetFields` に該当する入力は現行テストに無い |
| S-U1 | ラウンド 1・2 と同じ。未検証で、中断・手動削除・同型混在・フィールド無しが重なる場合に限られる |
| S-U2 | ラウンド 1・2 と同じ。空で作った Component の中断再開で `initialFields` が適用されないのは PR 以前からの挙動 |
| S-U3 / Q-I2 / D-U2 | ラウンド 2 と同じ。relocate 後に移動元 Slot の sibling の `componentIndex` を保存し直さないのは通常の relocate と同じ既存の挙動。誤束縛は再現されていない |
| S-U4 | ラウンド 1・2 と同じ。ResoniteLink が作成直後に member を完全に返すかは実機での確認事項 |
| D-L1 | ラウンド 1・2 と同じ。置換元がすでに無くても再読込後に停止するのは fail-closed の設計判断。レビュアーも【要設計判断】としている。O-L5 で書き直すヒントは「旧 Component がまだある」とは断定しない文言にする |
| D-I2 | ラウンド 1・2 と同じ。参照検査の範囲を plan で警告するのは機能追加の提案 |
| D-I3 | ラウンド 2 と同じ。置換側がすでに無い key が prune 後も state に残るのは、Component が消えた key を `BuildDeletionPlans` が `continue` で残す既存の挙動と同じ |
| D-U1 | レビュアー自身が「実害は確認できていない」とする未検証候補（同じ Node に recreate と relocation が同居する場合の index） |
| D-U3 | state の `id` が欠けていると保持分の除外が効かない点。この実装が書く state には必ず `""` 以上が入り、欠けるのは手編集だけ。欠けた場合も `30476c4` 以前と同じ挙動（停止）で、新たな誤動作ではない |

論点として残すもの（ラウンド 2 と同じ）: relocate の中断区間（S-L3）と移動元 Slot の index（S-U3 ほか）は、relocate 全体の設計として別途扱う。

## 修正方針

### G7: 他の key が保持する Component は、照合の位置を変えずに「単独の一致」からだけ外す（D-H1・Q-U1・S-M2・Q-U2）

原因: `WithoutHeldByOtherKeys`（`WorldService.cs:1180-1187`）は候補の配列そのものから他の key の保持分を取り除く。`StableComponentCandidates` の index の tie-break（`WorldService.cs:1917-1921`）と `MatchComponent` の `typeOrdinal` のフォールバック（`WorldService.cs:1853-1855`）は、渡された配列の位置を引く。保存した `componentIndex` は「旧 Component だけを除いた実レイアウト」の位置（`AssignComponentIndexes`）なので、配列を縮めると位置がずれる。また、このフィルタは同じ Slot の照合（`WorldService.cs:1085-1087`）にしか適用されず、relocate の移動元の照合（`WorldService.cs:1100-1102`）には適用されていない。

変更（`WorldService.cs`）:

- `WithoutHeldByOtherKeys` を、除外する ID の集合を返す `HeldByOtherKeys(prepared, key, state)` に置き換える。発動条件（同じセッションで state の `id` が空）と集合の中身（他の key の `id` と `supersededId`）は変えない。条件を満たさなければ `null` を返す。
- `MatchComponent` に省略可能な引数 `held` を足す。照合は従来どおり渡された配列（旧 Component だけを除いた実レイアウト）で行い、位置は変えない。次の 2 か所だけで `held` を見る:
  - 候補が 1 件に絞れたとき（index の tie-break で絞れた場合を含む）、それが `held` に含まれれば `null`（この key の Component はまだ無い＝作成する）を返す
  - `typeOrdinal` のフォールバックで選んだものが `held` に含まれれば `null` を返す
  - 候補が複数残る場合は従来どおり `STABLE_COMPONENT_AMBIGUOUS` で停止する。保持分を除けば 1 件になる場合でも、除外で曖昧さを解消しない（管理外 Component を自動で採用しないという既存方針に合わせる）
- 同じ Slot の照合（`WorldService.cs:1085-1087`）と relocate の移動元の照合（`WorldService.cs:1100-1102`）の両方に `HeldByOtherKeys(prepared, stableKey, stateComponent)` を渡す。
- 関数の上のコメントを、新しい規則（位置は変えず、他の key が保持する Component を単独の一致として採用しない）に合わせて書き直す。

挙動の変化（上の検証表の「試作した修正」列）:

- ラウンド 2 で直した経路（sibling の隣の作成前の中断、新しい key の作成前の中断）は、単独の一致が sibling になり `null` として扱うため、引き続き収束する。
- 作成応答を失った中断の再開は、`30476c4` 以前と同じく保存した index で置換（作成済みの Component）に束縛される。管理外の同型 Component の有無に左右されない。
- 作成前に中断し、中断前から管理外の同型 Component がある場合は `30476c4` 以前と同じく `STABLE_COMPONENT_AMBIGUOUS` で停止する（HEAD では管理外 Component を採用していた）。
- relocate の移動元で他の key の Component を選ばなくなり、作成前に中断した key の移動は移動先への作成として収束する。

残る制約: 作成前に中断した key と同じ Slot に、中断後に管理外の同型 Component が保存 index の位置へ追加された場合は、それを採用する。`30476c4` 以前・HEAD とも同じ挙動で、保存 ID が無い以上は型・member 名・位置でしか照合できないため、今回は扱わない。

検証（`tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` に既存の作法で追加。いずれも HEAD で失敗することを確認する）:

1. 作り直しの再開と管理外 Component: `identityFields` なしの同型 `sibling` を置き、`lost-add-response` で作り直しを中断する。管理外の同型 Component（`Label` が異なる）を、中断後に追加するケースと中断前から置くケースの両方で、再開の apply が成功し、`renderer` の state が中断で作られた置換を指し、管理外 Component の ID と `Label` が変わらず、Test.Renderer の数が「sibling・置換・管理外」の 3 件になる。再 apply の書き込みは 0
2. 新しい key の再開と管理外 Component: 管理済み `renderer` の隣に同型の新しい key を足す apply を `lost-add-response` で中断し、管理外の同型 Component を中断の前後に置く 2 ケースで、再開後の state の新しい key が中断で作られた Component を指し、管理外 Component が変わらない。再 apply の書き込みは 0
3. 作成前の中断と中断前からの管理外 Component: 2 と同じ構成を `before-add`（`FailOnWrite=1`）で中断すると、再開の apply が `STABLE_COMPONENT_AMBIGUOUS` で停止し、書き込みが 0 で、管理外 Component が変わらない
4. 作成前に中断した key の移動（S-M2）: 新しい key の作成を `before-add` で中断し、次の文書でその key を `Rubble` の子 Slot `Debris` へ移す。plan と apply が成功し、`Debris` に Component が 1 件でき、`renderer` の ID と state が変わらない。再 apply の書き込みは 0
5. 既存の `InterruptedRecreateNextToASameTypeSiblingResumes`・`InterruptedCreateOfANewKeyNextToAManagedSameTypeComponentResumes` が引き続き成功する

### G8: 再読込後の中断した作り直しの停止で、候補を区別できる値と、保存 ID の有無に応じた復旧手順を返す（O-L5）

原因: `InterruptedRecreateAcrossSession`（`WorldService.cs:1189-1203`）は、Slot 上の同型 Component をすべて候補に入れ、各候補のリストの要素数だけを返す。ヒントは「リストが長いほうが旧 Component。それだけを削除し `supersededId` を消す」「もう一方の候補は置換」と断定する。しかし候補には他の key の同型 Component も入り、置換の作成前に中断した場合（保存 ID が空）は置換が存在しないか、作成応答を失って ID が保存されていない。保存 ID が空のまま `supersededId` だけを消して再実行すると、別セッションでは型・member 名・index で照合するため、sibling に束縛されて `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で止まり続ける（作成応答を失った場合は、sibling 側の保存 index が古いまま残っていることも原因になる）。

変更（`InterruptedRecreateAcrossSession`。宣言済み key の経路と `BuildDeletionPlans` の経路の両方が使う）:

- 停止条件と停止位置は変えない（変更前に停止する）。
- `candidates` の各候補に、この key の管理 member（state の `memberNames`）のうち list 以外の値を `fields` として添える（field は値、reference は参照先 ID）。`lists` はそのまま残す。これで `Label` のような宣言値で、他の key の Component と旧・置換を区別できる。
- ヒントを保存 ID（`savedId`）の有無で分ける:
  - 保存 ID がある（置換は作成済み）: 「`fields` がこの key の宣言と一致する候補のうち、リストが宣言より長いものが旧 Component。それだけを削除し、state のこの key から `supersededId` を消して再実行する。他の候補には別の key の Component が含まれうる」
  - 保存 ID が空（置換の作成が中断した。置換は無いか、ID が保存されていない）: 「`fields` がこの key の宣言と一致する候補（旧 Component と、作成が済んでいれば置換）をすべて削除し、state からこの key を丸ごと削除して再実行する。apply が Component を作り直す」
  - どちらにも共通して「state ファイルを削除しない。位置で候補を選ばない。この key の候補を `fields` で絞れない場合は、Resonite 上で確認してから操作する」を残す
- 「もう一方の候補は置換」「旧 Component はまだ長いリストを持つ」という断定はやめる（D-L1 の状況、つまり旧 Component がすでに無い場合にも誤りにならない文言にする。停止条件は変えない）。

検証（既存の `InterruptedListShrinkRecreateStopsBeforeMutationAfterWorldReload` の近くに Theory として追加。HEAD では復旧後の再実行が失敗するか、context に `fields` が無いため失敗することを確認する）:

- `identityFields` なしの同型 `sibling`（`Materials` 4 要素、`Label: "south"`）を置き、`before-add`・`lost-add-response`・置換作成後（`FailOnWrite=2`）の 3 通りで作り直しを中断し、`ReloadWorld` のあとに apply が `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION` で停止し、書き込み 0 で state が変わらないこと
- context の各候補に `fields.Label` があり、sibling は `south`、旧と置換は `north` であること。ヒントが保存 ID の有無に応じた手順（空なら key を丸ごと削除、あれば `supersededId` を削除）を含むこと
- テストがヒントの手順どおりに操作する（保存 ID が空: `Label` が `north` の候補をすべて削除し、state から `renderer` を削除する。保存 ID がある: `north` のうちリストが長い候補を削除し、`supersededId` を削除する）と、再実行が成功して `renderer` が 3 要素で収束し、sibling の Component（`south`・4 要素）が残って state の `sibling` がそれを指し、再 apply の書き込みが 0 になること

## 反映の手順（承認後）

実装は `fix/list-shrink-recreate` を checkout した worktree（`external/resoloop/.worktrees/fix-list-shrink-recreate`）で行う。着手前に、その worktree が clean で HEAD が `origin/fix/list-shrink-recreate`（`30476c4`）と一致することを確かめる。一致しなければ停止して報告する（2026-09-29 の計画時点では clean・一致を確認済み）。

1. 関連テスト: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter "FullyQualifiedName~ApplyWorkflowTests"`
2. 変更の種類に応じた検証（resoloop fork の変更）: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj`
3. `fix/list-shrink-recreate` に commit し、`git push origin HEAD` で既存 PR #5 に反映する。新しい PR や `*-review-fixes` ブランチは作らない
4. PR #5 の review-fix-planning コメント（`claude-opus-5-5` のマーカー）を更新する

`scripts/resoloop-fork.sh test` による全テストと、ワールドのプロジェクトの `uv run pytest` は反映の条件にしない。

## 範囲外と注意

- ラウンド 1・2 と同じく、ベースの `fix/asset-url-save-migration` は PR #5 の分岐後に先へ進んでおり、追従時に競合する見込みが高い。今回もベースへの追従は行わない。
- 作り直し時に runtime 値を引き継ぐか（ラウンド 1 の O-M1a）、非同期 refill の実機確認（O-L3）、relocate の中断区間（S-L3）は、別途判断が必要な論点として残す。
- ドキュメント（`docs/DECLARATIVE.md` など）への停止コードの復旧手順の追記は行わない（O-I1 ほか）。復旧手順はエラーのヒントを正本とする。
