# Issue #360 Submodule Retirement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** strict なレビュー worktree 退役から submodule のローカル成果を保護する。

**Architecture:** `_require_clean_worktree` の既存の submodule 再帰検査を補強する。実装は runner の指定担当が1 Taskを扱い、controller が受領、統合確認、Task review、全体 review、公開と PR 修正ループを行う。

**Tech Stack:** Python、Git、pytest、uv。新規依存無し。

**Spec:** `docs/superpowers/specs/2026-11-10-issue-360-submodule-reap-design.md`（draft、issue-to-pr の実行許可）。

## Global Constraints

- strict な退役判定で、各初期化済み submodule の HEAD を直近の親の HEAD に記録した gitlink と照合し、不一致を保持する。`ignore=all` で免除しない。
- submodule の status、ignored（既存の再生成可能キャッシュだけ許可）、skip-worktree / assume-unchanged を直接検査し、利用者作業を保持する。入れ子にも同じ条件を適用する。
- `_require_clean_worktree` の呼出元・保存ロック内の再判定・CLI JSON / 終了コード・既存の pin / ownership / stop / draft ガードを変えない。
- 実 PR の削除実験、定期掃除スクリプト変更、非 strict cleanup の意味の変更、未初期化 submodule に関する新たな仕様、汎用 submodule 走査の作り直しは対象外。

## Review Focus

HEAD 比較の親を取り違えないこと、設定で隠れた index flags を直接見ること、foreach の非0を保持へ伝播すること、pathをシェルへ安全に渡すこと、clean の通過を保つこと。前2件と clean の通過は Task 1 の S テスト、残りは同テストの実 Git fixture と差分/関連呼出元の確認で検証する。固定文言・構文エラーだけのテストは追加しない。

## 受け入れ基準（実装担当とレビュアーに同文で渡す）

動作環境はこの Dev Container の Git / uv / pytest。実入力は一意な一時ディレクトリのローカル親 repo、初期化済み submodule（空白・非ASCIIの path を1例含む）、入れ子 submodule、`.gitmodules` の `ignore=all`、複数行の追跡ファイルを含む。防御範囲は HEAD と直近の親 HEAD の gitlink の不一致、submodule 内の skip-worktree / assume-unchanged、既存の status / ignored の検査。拒否時は `reap-check` と `cleanup --strict-reap` が1を返し、ローカル成果とセッションを保持する。対となる gitlink と一致した clean な初期化済み submodule は0で退役し、保存レビューを残す。未初期化 submodule の新仕様、非 strict cleanup、実 PR 上の削除実験は対象外。

## 要件と証拠の対応

| 条件 | 担当 | 観測 / 検証 |
| --- | --- | --- |
| HEAD 不一致を保持 | Task 1 / controller | ignore=all とローカル commit、両入口1と commit/ファイル残存、変更前 RED と修正後 GREEN |
| flags と入れ子を保持 | Task 1 / controller | 入れ子 submodule の skip-worktree 変更、両入口1と内容保持。assume-unchanged は同じ守りのため一時的な実入力確認 |
| clean を退役 | Task 1 / controller | 同じ種類の clean fixture で両入口0、session/worktree削除と保存レビュー保持 |
| 既存の保護 | controller | 対象107件と新規分、READMEの検証入口、差分確認 |

共有前提は reap-check と strict cleanup が同じ判定を呼び、strict cleanup がロック内で再判定すること。controller が関連呼出元と最終 HEAD の証拠を照合し、Taskの成功だけで全体成功にしない。

### Task 1: submodule の直接検査とデータ保持の回帰防止

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py` (`_require_clean_worktree`)
- Test: `.agents/skills/pr-review/tests/test_pr_review_workspace.py` (`test_strict_reap_*` 近傍)

**Interfaces:**
- Consumes: `_require_clean_worktree(worktree: Path, target: Path, state: Mapping[str, Any]) -> None`、既存の git helper / saved_session fixture。
- Produces: 同じAPI。変更や検査失敗を WorkspaceError により既存の保持結果へ伝播する。

**テストの要否:** S。誤った eligible は削除につながり、利用者の commit / ファイルを無言で失う。別の守りに対する拒否2例と正しい通過1例を代表として残す。F/L/D のテストは足さない。

- [ ] **Step 1: 実 Git の回帰テストを書く。** `test_strict_reap_keeps_a_submodule_local_commit`（ignore=all、ローカル commit）、`test_strict_reap_keeps_nested_submodule_index_flags`（入れ子で skip-worktree の付いたファイルを変更）、`test_strict_reap_retires_clean_submodules`。既存 fixture を最小拡張し、変更を入れる前に保存済み状態を作る。両拒否例は `workspace.main(["reap-check", "--state", state_file]) == 1` と `workspace.main(["cleanup", "--strict-reap", "--state", state_file]) == 1`、内容・HEAD・session残存を確認する。通過例は両入口0、退役および保存レビュー残存を確認する。
- [ ] **Step 2: RED を確認する。** `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py -k 'submodule' -v`。現行実装の拒否例が eligible/削除につながるため失敗し、clean例は通ることをログへ保存する。構文/import失敗をREDにしない。
- [ ] **Step 3: 最小実装。** 既存 foreach 再帰内で、直近 superproject HEAD の gitlink と submodule HEAD の一致、status、index flags、ignoredを直接確認する。コマンド代入を引用し、Git失敗を握り潰さない。必要なら親と子のstatusに `--ignore-submodules=none` を明示する。新しい汎用ツリー走査は導入しない。
- [ ] **Step 4: GREEN と回帰確認。** 上の対象テストと `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py` を同期実行する。assume-unchanged は一時的な実 Git シナリオでも保持を確認する。ログは attempt外の指定セッションに保存する。
- [ ] **Step 5: Commit。** 明示した2ファイルだけ stageし `fix: preserve submodule work during strict review retirement` でcommitする。RED/GREEN、HEAD、所要時間、残る懸念を報告する。

### 統合・レビュー・公開（controller）

- [ ] 取り込んだHEADで対象テストを再実行しTask reviewのspec/qualityを確認する。全体reviewは捕捉base `1f20820f0b628c707784aa6f7f55146225139fd2` から行う。
- [ ] `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を同期実行し、最終HEAD・clean status・argv・終了コード・ログを記録する。
- [ ] Spec→Plan→Task→証拠を照合し、base/競合再確認、scan、検査SHA push、PRを作る（Closes #360）。CIはAGENTS.mdに従い無効のまま。
- [ ] 指定inspect3担当・implement担当で修正ループを最大3サイクル実施し、finalize以外でマージしない。

## 実行予算

全体360分（準備30、実装/Task review60、統合検証/公開30、ループ最大240）。ledgerは `/workspaces/reso-world/tmp/agents/issue-360.hqqem4gb/budget.jsonl`。SDD記録も同セッションの `sdd/2026-11-10-issue-360-submodule-reap/`。実装担当は runner の implement 期限90分、ループinspect各45分。同期runner自身の期限と停止確認を使い、追加watcherは使わない（予約枠・無進捗での独自停止無し）。controllerは完了まで待ち、失敗/段階境界/50%/100%でcheckpoint。信頼性の同一失敗は再試行1回、failedは入口規則どおり停止。安全失敗と100%で停止。指定担当からselfへ切り替えない。本物のモデル起動は調査1、実装1（文脈不足の再依頼は最大1）、Task review1、全体review1、必要な各修正/限定レビューのみ。PR後は最大3×inspect3、必要なfixはループ規則の範囲。

## contingency（代替策）

最初のREDでfixtureやGit実出力が異なれば、仕様を維持する最小のfixture修正をledgerに残す。API・テストの表記差で意味を変えないものは記録して継続する。意味の変更・安全境界・base移動・必要な検証を解消できない場合は停止。広範なsubmodule再設計は切り出し候補とし、本Issueに混ぜない。runner失敗はselfで引き取らず、保持パスと次の操作を報告する。
