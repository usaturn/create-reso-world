# list-shrink-recreate レビュー指摘の修正設計（ラウンド 2）

- 日付: 2026-09-29
- 対象 PR: usaturn/resoloop #5（`fix/list-shrink-recreate` → `fix/asset-url-save-migration`）
- 現行 HEAD: `dc1c651499e165b1aecc5a668cf9c013ac95454e`（レビュー対象 HEAD と同じ。ラウンド 1 の修正コミット）
- 入力: `external/resoloop/reviews/#5-fix-list-shrink-recreate/`
  - `claude-opus-5-5.md`（対象 HEAD `dc1c651499e1`。各指摘の検出時 HEAD は `d615eeb` と `dc1c651`）
  - `SWE-2-Max.md`（同上）
  - `commandcode-deepseek-deepseek-v4.1-flash.md`（同上）
  - `qwen3.8-max.md`（同上）
- 前回: `docs/superpowers/specs/2026-09-29-list-shrink-recreate-review-fixes-design.md`（ラウンド 1、`d615eeb` 対象。G1〜G5 を `dc1c651` で反映済み）
- brainstorming の経路: **bounded**（既存の `BuildComponentPlans` の候補選択を 1 か所直す修正。state の形式や公開インターフェースは変えない）

## 検証の方法

`git -C external/resoloop worktree add --detach` で `dc1c651` を一時 worktree に取り出し、偽クライアント（`ApplyWorkflowTests`）で再現テストを書いて `dotnet test --filter` で実行した。worktree と一時ディレクトリは検証後に削除済み。

| 再現 | 結果 |
| --- | --- |
| O-L4 | `identityFields` なしの同型 `sibling` を置き、3 要素への縮小 apply を `FailOnWrite=1`（置換の作成）で中断。state の `renderer` は `id: ""`・`supersededId: 旧 ID`。同じ文書の plan・apply が両方 `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で停止し、conflict に `sibling` の ID が入る |
| O-L4（対照） | 同じ構成で作成の応答だけを失わせた場合（`LoseNextComponentCreateResponse`）は、index の tie-break で置換に束縛され、再実行で収束する（再 apply の書き込み 0） |
| O-L4（PR 以前からの経路） | 管理済み `renderer` の隣に新しい key `extra`（同型・`identityFields` なし）を足す apply を `FailOnWrite=1` で中断 → 再実行が `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で停止する |
| S-L3 | 中断した作り直し（`FailOnWrite=2`）のあと key を `Debris` へ移す apply を、移動先作成後・置換側の削除前（`FailOnWrite=3`）で中断 → 再実行で旧 Component は消えるが、置換側が `Rubble` に管理外で残り、`supersededId` は無い |
| S-L3（対照） | 作り直しを伴わない通常の relocate を同じ位置（`FailOnWrite=3`）で中断 → 再実行後、移動元の Component が `Rubble` に管理外で残る |
| 解消確認 | `FullyQualifiedName~Recreate\|ListShrink\|ListMember\|Undone\|Pruning\|MovingAComponent\|Interrupted` の 27 件（再現テスト 2 件を含む）がすべて成功 |

## 分類

解消済み 7 / 対応する 1 / 判断保留 0 / 対応しない 24（計 32）。ID の接頭辞は O = claude-opus-5-5、S = SWE-2-Max、D = deepseek、Q = qwen3.8-max。U は各レビューの Unverified candidates、Q-X は qwen が「検討したが報告しなかった候補」として挙げたもの。

### 解消済み

| ID | 根拠 |
| --- | --- |
| O-M1 | `initialFields` の値を引き継がない挙動は仕様として維持し、`docs/DECLARATIVE.md:57`・`README-DETAILS.md:181`・`skills/codex/resonite-build/SKILL.md` が作り直しで初期値に戻ることを明記した（ラウンド 1 の G5） |
| O-L1 | `UndoRecreateState`（`WorldService.cs:1205-1217`）が取り消し時に sibling の `componentIndex` を保存し直す。`UndoneRecreateKeepsSiblingIndexesSoAWorldReloadStillBindsThem` が成功 |
| O-L2 | `BuildDeletionPlans`（`WorldService.cs:1417-1430`）が旧 Component の削除を先に計画する。`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent`（2 ケース）が成功 |
| S-M1 | 検証前の置換を `byKey` に入れない（`WorldService.cs:449,476,487-489`）。`UndoneRecreateLeavesNoReferenceToTheRemovedReplacement` が成功 |
| S-L2 | `FindSnapshotComponent` で旧 Component を snapshot 全体から探し、relocate・宣言削除でも削除する。再読込後は変更前に停止する。`Moving…`・`Pruning…`・`InterruptedRecreateStopsBeforeMutationAfterWorldReloadWhenTheKeyMovesOrIsRemoved` が成功 |
| Q-M1 | S-L2 と同じ修正・テスト（O の前回の未検証候補「中断した作り直しの relocate」を含む） |
| Q-M2 | `VerifiesRecreate` で再開した作り直しも refill を検証する。`ResumedRecreateThatTheRuntimeRefilledStopsAndKeepsTheOriginal` が成功 |

### 対応する

| ID | 区分 | 一行 |
| --- | --- | --- |
| O-L4 | (a) | 作り直しの置換 Component の作成前に中断すると、`identityFields` の無い同型 sibling がある Slot では、再実行が `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で止まり続ける |

### 判断保留

なし。

### 対応しない

| ID | 理由 |
| --- | --- |
| O-L3 | ラウンド 1 と同じ判断。実機で非同期に refill されるリストがあるかは未確認で、偽クライアントでは再現できない。対策には state に作り直しの履歴を残す設計が要る |
| O-U1 / Q-L1 | 空で作った置換の再開時に refill を見逃すのは、runtime がフィールド設定をきっかけにリストを埋め直す場合に限られ、実機の挙動が未確認。偽クライアントは作成時に埋め直すため再現しない。ラウンド 1 の Spec（G2）に「残る制約」として記載済みで、次の apply で `NOT_CONVERGED` として検出される |
| O-I1 / S-I1 / D-I1 / Q-I1 | `recreate` と新しいエラーコード 3 件の記載漏れ（Info）。ラウンド 1 と同じく、README の例に action の一覧は無く、fork の `AGENTS.md` は skill を「workflows, not command mirrors」とする。`docs/DECLARATIVE.md:185` の action の列挙は PR 以前から `relocate` も含んでおらず、`--deletes-only` に作り直しの削除が出ないのも `relocate` の既存の挙動と同じ。qwen は作者の判断として解消扱いにしている |
| S-L1 | ラウンド 1 と同じ判断。`--prune` で消える Component からの参照も数えるのは、変更前に止まる安全側の停止。検査を緩めるかは仕様の判断 |
| S-L3 | 再現したが、作り直しを伴わない通常の relocate でも、同じ位置で中断すると移動元が管理外で残る（対照で確認）。旧 Component 側は `supersededId` で後始末されており、残るのは既存の relocate の中断区間と同じもの。塞ぐには state に削除待ちの ID を別に持たせる設計変更が要る |
| S-I2 | ラウンド 1 と同じ判断。偽クライアント `SetFields` に該当する入力は現行テストに無く、テスト基盤の将来の保険 |
| S-U1 | ラウンド 1 と同じ。未検証で、中断・手動削除・同型混在・フィールド無しが重なる場合に限られる |
| S-U2 | ラウンド 1 と同じ。空で作った Component の中断再開で `initialFields` が適用されないのは、PR 以前の通常作成にもある挙動 |
| S-U3 / Q-I2 / D-U2 | relocate 後に移動元 Slot の sibling の `componentIndex` を保存し直さないのは、通常の relocate にもある既存の挙動（ずれが 1 から 2 に増えるだけ）。誤束縛は誰も再現しておらず、qwen も PR の範囲外としている |
| S-U4 | ラウンド 1 と同じ。実機の ResoniteLink が作成直後に member を完全に返すかは実機での確認事項 |
| D-L1 | ラウンド 1 と同じ判断。再読込後は旧 Component がすでに消えていても停止するのは fail-closed の設計判断。停止メッセージの復旧手順は、通常の経路（旧 Component が残っている場合）では正しい |
| D-I2 | ラウンド 1 と同じ。参照検査の範囲を plan で警告するのは機能追加の提案 |
| D-I3 | 置換側がすでに無い key を prune すると state に key が残るのは、Component が消えた key を `BuildDeletionPlans` が `continue` で残す既存の挙動と同じ（`WorldService.cs:1438` 付近）。レビュアーも【要設計判断】としている |
| D-U1 | レビュアー自身が実害を確認できなかった未検証候補 |
| Q-X1 | 取り消し時の sibling の index の仮定。qwen が実害経路なしとして報告から外した |
| Q-X2 | 旧 Component の削除と checkpoint の間でプロセスが落ちた場合の停止メッセージの文言。窓が極めて狭く fail-closed で、qwen が報告から外した（D-L1 と同じ論点） |
| Q-X3 | 相互参照する 2 つの作り直しで片方だけ取り消した場合の一時的な参照。再開時に直り、qwen が報告から外した（ラウンド 1 の Spec G3 に「残る制約」として記載済み） |
| Q-X4 | S-U2 と同じ。PR 以前からの挙動 |

論点として残すもの: 作り直しを伴う relocate を含め、relocate の中断区間で移動元が残る問題（S-L3）と、relocate 後の移動元 Slot の index（S-U3 ほか）は、relocate 全体の設計として別途扱う。

## 修正方針

### G6: 作成前に中断した key の再解決で、他の key が保持する Component を候補にしない（O-L4）

原因: 作成前の checkpoint（`WorldService.cs:469`）は state の `id` を空で保存する。同じセッションの再実行では、`MatchComponent`（`WorldService.cs:1826-1847`）が空の ID で見つけられず、型・管理 member 名・index で候補を選ぶ。候補が 1 件なら index を見ずにそれを返す（`WorldService.cs:1843`）ため、同じ Slot に `identityFields` の無い同型の管理 Component が 1 つだけ残っていると、他の key が ID で保持するその Component に束縛され、`ValidateComponentOwnership`（`WorldService.cs:1462-1481`）が停止する。作り直しでは、置換を作る前の Slot に旧 Component（`Without` で除外済み）と sibling しかないため、必ずこの経路に入る。

変更（`BuildComponentPlans`、`WorldService.cs:1053` 以降）:

- ループの前に、state のすべての key が保持する Component の ID（`id` と `supersededId` のうち空でないもの）を key ごとに集める。
- 同じセッション（`prepared.SameSession`）で state の `id` が空の key を `existing` として再解決するとき（`WorldService.cs:1085-1087`）は、他の key が保持する ID を候補から除いてから `MatchComponent` に渡す。自分の `supersededId` は従来どおり `Without` で除く。
- 別セッションでは変えない（保存 ID が再読込で無効になるため除外に使えない。作り直しの中断は `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION` で停止する既存の挙動のまま）。
- 適用範囲は作成前の中断全般とする（ユーザ選択）。作り直しの再開に加え、新しい key を同型 Component の隣に作る apply が作成前に中断した場合（PR 以前からの同じ弱点）も直る。他の key の Component に束縛すると必ず `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で停止するため、変わるのは「停止」が「収束」になる経路だけである。
- 作成の応答を失った場合（置換は存在するが `id` が空）も、sibling を除いた候補から置換だけが残るため、index の tie-break に頼らずに束縛される。

検証（`tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` に既存の作法で追加。修正前に失敗することを確認する）:

1. 作り直し・sibling あり: `identityFields` なしの同型 `sibling` を置き、`before-add`（`FailOnWrite=1`）と `lost-add-response` で作り直しを中断 → 同じ文書で plan（`renderer` が `recreate` 1 件）と apply が成功し、Test.Renderer が 2 件、`renderer` の state が置換を指して `supersededId` が無く、`sibling` の ID と state が変わらない。再 apply の書き込みは 0。`before-add` は修正前に `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で失敗する
2. 新しい key: 管理済み `renderer` の隣に同型の新しい key を足す apply を `FailOnWrite=1` で中断 → 再実行で新しい key の Component が 1 件だけ作られ、`renderer` の ID と state が変わらない。再 apply の書き込みは 0。修正前は `APPLY_COMPONENT_OWNERSHIP_CONFLICT` で失敗する

## 反映の手順（承認後）

実装は `fix/list-shrink-recreate` を checkout した worktree（`external/resoloop/.worktrees/fix-list-shrink-recreate`）で行う。着手前に、その worktree が clean で HEAD が `origin/fix/list-shrink-recreate`（`dc1c651`）と一致することを確かめる。一致しなければ停止して報告する。

1. 関連テスト: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter "FullyQualifiedName~ApplyWorkflowTests"`
2. 変更の種類に応じた検証（resoloop fork の変更）: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj`
3. `fix/list-shrink-recreate` に commit し、`git push origin HEAD` で既存 PR #5 に反映する。新しい PR や `*-review-fixes` ブランチは作らない
4. PR #5 の review-fix-planning コメント（`claude-opus-5-5` のマーカー）を更新する

`scripts/resoloop-fork.sh test` による全テストと、ワールドのプロジェクトの `uv run pytest` は反映の条件にしない。

## 範囲外と注意

- ラウンド 1 と同じく、ベースの `fix/asset-url-save-migration` は PR #5 の分岐後に先へ進んでおり（`e61d83d`・`bf8616e`・`4931814` など）、追従時に競合する見込みが高い。今回もベースへの追従は行わない。
- 作り直し時に runtime 値を引き継ぐか（ラウンド 1 の O-M1a）、非同期 refill の実機確認（O-L3）、relocate の中断区間（S-L3）は、別途判断が必要な論点として残す。
