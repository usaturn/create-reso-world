# PR #9 第3回レビュー修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** recreate / undo 中断後の手作業復旧で、保存 index が管理外 Component を指して書き込む事故を防ぐ。

**Architecture:** prune / 移動と同じ削除直前の未確認化を recreate / undo に加える。別セッションでは自動再開せず、現在の候補位置と同じ Slot の保存 key をエラーで示して手作業の復旧を案内する。文書は既存の対象範囲とこの復旧手順に合わせる。

**Tech Stack:** C# / .NET 10、既存 xUnit、FakeResoniteClient、System.Text.Json.Nodes。

**Spec:** `/workspaces/reso-world/docs/superpowers/specs/2026-10-03-pr9-list-shrink-round3-review-fixes-design.md`

## Global Constraints

- 維持する PR #9 の設計判断: 再読込後に作り直しを自動では再開しない。未確認 index（`componentIndex: -1`）が残る state は、再読込後に変更前で停止する。state の schema は変えない。
- 成功条件: 下記の3つの再現手順を、新しい案内どおりに辿っても管理外 Component の値が変わらないこと（収束するか、書き込み0回で停止する）。関連する既存テストが、新しい案内に沿って収束すること。
- `MarkSlotIndexesUnverified` が `supersededId` を持つ key を対象外にする挙動（`:2451`）は変えない。
- `-1` の停止（`:1013-1023`）、`:1126`・`:1534` の案内は変えない（「仕様論点」を参照）。
- README・README_JA・スキルは「エラーの suggestions に従う」とだけ書いており、変更しない。
- 入れ子 list の検出機能は追加しない。
- 実機 Resonite での確認は今回の範囲外で、fake client のテスト結果から実機での挙動を保証済みとは書かない。
- 実装先は `/workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split` の `fix/list-shrink-recreate-split`。基準 HEAD は `36d955e8de7f4f9413c2d5209058b177ae307037`。親 checkout・他 worktree・レビュー成果物・旧 Spec / plan は変更しない。
- 方針 A だけを実装する。fields 段の checkpoint、schemaVersion、オプトイン、件数、参照判定、既存コメントを変更しない。依存を追加しない。
- 関連検証は `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter FullyQualifiedName~ApplyWorkflowTests` と変更したテストの focused filter。ソリューション全体や fork 全テストを反映条件にしない。
- 全テストは `T=$(mktemp -d)` を作り `TMPDIR="$T" DOTNET_CLI_HOME="$T/dotnethome"` をコマンド限定で指定する。HOME / PATH を書き換えない。実機テストを実行しない。
- 各実装担当はテストを同期実行し、終了を待って結果を記録してから関連ファイルだけを commit する。Generated with [Devin](https://devin.ai) と Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com> を commit message に含める。push、PR 投稿、merge、作業領域削除は担当しない。

## Review Focus

- 旧 Component の削除が成立して応答だけ失われる場合: 兄弟の保存 index は -1 となり、同セッションでは修復、再読込後は未確認のまま書き込まない（Task 1 A）。
- undo の削除直後のキャンセル: checkpoint の兄弟 index が -1 のままでも管理外値を変えない（Task 1 C）。
- 手作業削除より前後に候補がある場合: 現在の position を設定し、削除より後ろだけを1減らす。候補が1件なら減らさない（Task 1 B と全書き込み位置）。
- -1 の位置が特定できない場合: 推測せず state を保持して書き込み0回で停止する（Task 1 A / C）。
- 同じ Slot の別 key が recreate と同じ型の場合: 自動識別や手作業削除を勧める分岐へ変更しない（Task 1 既存 shared-slot シナリオ）。

## File Map

すべての相対パスは実装 worktree 基準。
- `src/RLoop.Core/WorldService.cs`: 未確認化2か所、エラー context / suggestions。
- `tests/RLoop.Tests/ApplyWorkflowTests.RecreateRecovery.cs`（新規）: 再現 A / B / C の固定と、必要最小限のテスト専用復旧 helper。
- `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`: 既存全書き込み位置の復旧更新、管理外同型 Component シナリオ。
- `docs/DECLARATIVE.md`: 未確認化対象と session-changed 復旧の説明。
- `README-DETAILS.md`: fields 直下だけが recreate 対象であること。

### Task 1: 削除前未確認化と session-changed 復旧を回帰テストで固定

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（recreate 完了ループ、VerifyReplacementsAsync の undo、RecreateInterrupted）
- Create: `tests/RLoop.Tests/ApplyWorkflowTests.RecreateRecovery.cs`
- Modify: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`（AWorldReloadDuringARecreateStopsBeforeAnyWrite）

**Interfaces:**
- Consumes: 既存 `MarkSlotIndexesUnverified(PreparedApply prepared, string slotKey)`、`SaveSlotIndexesAsync`、`ReconcileUnverifiedIndexesAsync`、`FakeResoniteClient` の故障注入と `ReloadWorld`。既存 partial test class の helper を再利用する。
- Produces: 全 reason の `candidates[]` に既存項目を残して `position: int` を加える。`session-changed` だけに `slotKeys`（配列、要素 `{ key: string, componentIndex: int? }`）を加える。同じ SlotKey を持つ state key を全て含み、recreate 自身も含む。Task 2 はこの名称で説明する。

- [x] **Step 1: 回帰テストを先に書く。** 新規 partial test file に A / B / C の focused テストを作り、以下を固定する。
  - A: renderer (Test.Renderer, Materials 3→2)、v1 (Test.Indexed, Value=1)、末尾の管理外 Test.Indexed (Value=999)。旧 renderer 削除の応答を失う `LoseResponseOnWrite=2` の構成。兄弟 v1 の checkpoint index が -1 となる。同セッションは収束する。別の独立した構成で再読込、session-changed 案内で supersededId を消して renderer の位置だけ修復し、v1 を -1 のままにすれば STABLE_COMPONENT_AMBIGUOUS / writes=0 / 管理外 Value=999、v1 の確認済み位置も設定すれば収束 / 管理外 Value=999。
  - B: source (Test.Source, Target=$ref:renderer) も配置。旧 renderer の Remove を FailRemovingComponent で失敗させて再読込。candidates の position は現在の Slot の0始まり、slotKeys は全同 Slot key と一致する。参照されている候補を残し、他方だけを削除、state をバックアップ、空 id を supersededId に、supersededId を削除、残す候補の position を設定し、削除位置より後ろの index を1減らし、-1 は fixture で確認済みの現在位置に設定する。次の apply は収束し管理外 Value=999。suggestions 自身もこの手順を含むことを具体的な assertions で確認し、旧 suggestions ではテストが失敗するようにする。英文全体の不要な完全一致は避ける。
  - C: renderer だけから開始し、縮小と k3 (Test.Indexed, Value=3) 追加を旧 renderer 削除失敗で中断。置換の Materials を3へ戻し、末尾に管理外 Test.Indexed (999) を追加。同セッション undo の置換削除直後 `CancelAfterWrites=2` でキャンセル。兄弟 k3 の保存 index=-1、再読込後の復旧で未確認なら writes=0、確認済み位置設定後も管理外 Value=999。
  - 上記の値・故障位置は Spec の再現 A / B / C に合わせる。故障を注入する前に write counters を reset する。
- [x] **Step 2: focused filter で RED を観測し、期待した理由で失敗したことを report に記録する。** コンパイル失敗を RED と扱わない。
- [x] **Step 3: 最小修正を実装する。** 旧 Component RemoveComponentAsync の直前、および undo の置換 RemoveComponentAsync の直前に `MarkSlotIndexesUnverified(prepared, component.Node.StableKey)` を加える。削除後の既存 index 保存 / checkpoint と helper 本体は維持する。
- [x] **Step 4: RecreateInterrupted の context と案内を実装する。** position は saved.SlotKey の node.Existing.Components における現在位置で、候補だけの連番ではない。session-changed の同型別 key が無い分岐に3つの suggestions: (1) 現状の候補選択と exact ID / --yes の制限、(2) バックアップと id / supersededId 編集後は index 調整を行ってから再実行、(3) 削除で後続が1つ前へ詰まること、identityFields が無ければ再読込後に保存 index で照合すること、残す候補の position 設定→削除位置より後ろだけ1減らすこと、slotKeys の全 key を対象にすること、-1 は component inspect で確認して現在位置を設定すること、特定できなければ state をそのまま残して推測しないこと。候補1件で削除しなければ index を減らさない。既存の同型別 key 分岐と他 reason の suggestions は変更しない。
- [x] **Step 5: 既存全書き込み位置テストを新しい手順へ更新する。** AWorldReloadDuringARecreateStopsBeforeAnyWrite の one-recreate 復旧に index 調整と確認済み -1 解決を適用。管理外 Test.Indexed (999) を同 Slot に置くシナリオを追加し、全書き込み位置で復旧が収束または writes=0 で停止し、値が999のままを検証する。shared-slot の分岐は維持。テスト専用 helper の必要以上の汎用化や重複した復旧ロジックを避ける。
- [x] **Step 6: focused テストを GREEN にする。** A / B / C、AWorldReloadDuringARecreateStopsBeforeAnyWrite、ARecreateInterruptedAtAnyWriteConvergesInTheSameSession、AnUndoInterruptedAtEitherRemovalResumesOnTheNextApply、SlotIndexes tests を実行。
- [x] **Step 7: 効き目を一度確認する。** 新しい未確認化を1か所ずつ一時的に外し、A / C がそれぞれ失敗することを観測。session-changed suggestions を旧版へ一時的に戻し B が失敗することを観測。毎回 exact edits で復元し、checkout / reset で作業を上書きしない。report に各コマンド、失敗結果、復元を残す。
- [x] **Step 8: ApplyWorkflowTests 全件を通して self-review 後 commit。** `git diff --check` も通す。変更した3ファイルだけを stage。テスト・lint に非ゼロ終了が残る状態では commit しない。report に RED / GREEN / mutation のコマンドと結果、所要時間・主要 step の内訳、懸念を記載する。

### Task 2: 対象範囲と復旧手順の文書を揃える

**Files:**
- Modify: `docs/DECLARATIVE.md:189,197`
- Modify: `README-DETAILS.md:181`

**Interfaces:**
- Consumes: Task 1 の `candidates[].position`、`slotKeys`、削除前の index 未確認化と復旧 suggestions。
- Produces: 実装に一致する2文書。README.md / README_JA.md / skills は unchanged。

- [x] **Step 1: 2文書と比較対象を読み、変更前の不足を確認する。** README.md、README_JA.md、DECLARATIVE.md の fields 直下・入れ子対象外の説明と README-DETAILS.md の不足を照合。
- [x] **Step 2: 最小限の文書変更。** DECLARATIVE.md の index 未確認化の対象へ「作り直しの旧 Component の削除」「APPLY_LIST_SHRINK_NOT_CONVERGED の取り消しの削除」を加える。session-changed の説明へ「手作業の候補削除で後続が前へ詰まるため、candidates の position と slotKeys を使い state の componentIndex を直してから再実行」を1文で加える。既存の slot inspect の例は触らない。README-DETAILS.md を「`fields`直下に宣言したlist member」に限定し、「syncObject内などの入れ子のlistはこの作り直しの対象外で、短く宣言しても収束は保証されません」を1文追加。
- [x] **Step 3: 文書比較と関連テスト。** grep tool で4文書の list member 周辺を確認し対象範囲が一致することを report に引用。isolated dotnet test の filter `FullyQualifiedName~AShorterListInsideASyncObjectIsNotRecreated` が PASS、git diff --check が PASS。
- [x] **Step 4: self-review 後、2文書だけを stage / commit。** report に変更・比較結果・テストコマンド / 出力・所要時間の内訳を記載する。

## 最終レビューの1回の修正波

Task 1 / 2 の gate 完了後、全体レビュー I1（候補の所有確認）/ I2（stable selector の中断 state 消費）/ M1（plan recovery の prune 限定）を1担当にまとめる。Spec の「最終レビューでの追加裁定」と SDD ledger の裁定を適用し、まず各経路を RED で確認してから最小修正を行う。具体的な requirements / file boundary / test cases は、この plan の SDD workspace にある `final-fix-brief.md` を単一の実装 brief とする。

許可する追加変更は `WorldService.cs`、`StableReferences.cs`、関連 partial ApplyWorkflowTests と、`docs/DECLARATIVE.md` の最小注意書きだけ。schema・marker helper・fields checkpoint・別 reason の suggestions・README / skills・既存コメントは変更しない。SDK workload notice は環境 Minor として保留する。追加テストと関連 ApplyWorkflowTests を通して commit した後、FIX_BASE `b4018a9bda14106e3c2172b205b463a51c8d315d` からの差分で scoped re-review を1回行い、残存 finding は裁定して報告する。
