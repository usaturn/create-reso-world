# Issue #415 Stable Role Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 外部役割の安全な書き込み例外を検査するテストから、実 worktree 準備と役割期限の競合を除き、失敗の状態を診断できるようにする。

**Architecture:** テスト内の局所fixtureで runner の `prepare_worktree` だけを偽物にする。例外生成、runnerのプロンプト組立、fake adapterの実行・collect、改ざんや停止未確認を拒否する処理は残す。

**Tech Stack:** Python、pytest、uv、Git、fake adapter。新規依存なし。

**Spec:** `docs/superpowers/specs/2026-11-13-issue-415-stable-role-tests-design.md`。状態draft、issue-to-prの実行委任。Spec有効レビュー2回完了、最後のdecideはnext=plan。内容承認とは扱わない。

## Global Constraints

- コードの変更は `.agents/skills/review-fix-planning/tests/test_run_roles.py` だけ。
- `tools/agent_runner/runner.py`、runner のテスト、`scripts/run_roles.py`、`exception_lines()`、`config()` の20秒期限は変更しない。
- 外部2役割の同一一覧・各行の役割限定・許可パス付与数・改ざんと停止未確認の拒否を弱めない。安全指示全文を複製しない。
- fixtureはSpec列挙の5テストだけに明示適用。autouseで全体を置き換えない。
- テスト・検証はfake adapterのみ。実装担当は `devin_swe2_max`。SpecレビューのDeepSeek指定を実装へ推測で広げない。
- worktree `/workspaces/reso-world/.worktrees/issue-415-stable-role-tests`、branch `fix/issue-415-stable-role-tests`、base `ae50a14428bb4200054dfdcefd135dcacec20654`。
- マージは元の --merge 指示によるループ内finalize.pyのみ。PR前の全体レビューはループ1回目で代替、Taskレビューは維持。

## 受け入れ基準（実装・Taskレビュー双方へ同じ本文を渡す）

- 動作環境: Dev Container、uvのlocked project、実Gitの一時fixture、fake adapterのみ。
- 実入力: 外部2役割a/b、片側self、既存の複数行の例外一覧と非ASCIIパス。
- 防御範囲: 実際のrun_rolesの例外生成→runnerのプロンプト追加→FakeAdapter要求を通し、2役割で同一一覧・各行の役割限定・許可パスの既存assertionを維持する。準備のみ置換し、改ざん・停止未確認の拒否や回数枠保持も実処理で検査する。
- 対象5テスト: `test_external_review_roles_list_their_write_exceptions_with_the_role`、`test_only_the_externally_assigned_role_lists_exceptions`、`test_single_call_uses_both_review_roles_and_retains_self_instructions`、`test_review_directory_tampering_is_not_accepted_or_cleaned`、`test_unconfirmed_stop_blocks_fix_check_accept_and_keeps_budget`。
- 対象外: 実worktree作成そのもの、任意の安全文言の全文一致、#400の実装変更。exception_lines()と20秒期限は不変。
- 失敗時には役割名・state・attemptのstate/終了コード等で原因が分かる。外部役割の失敗を無視して一覧だけで合格させない。
- 対象ファイル単独実行、runner全体、README共通検証を成功させる。対象ファイルのpytestとシェル共通検証の同時実行を2回行い、ファイル全体で失敗0回。
- #400未マージなら両変更での結合確認は未確認としてRefs #415、残項目をIssueへ報告する。

## Review Focus

既存S/F∩Sの安全検査を維持する。新しい恒久テストは不要（安定化や診断の自己検査はL）。Task 1の一時対照と既存検査を使う。

1. 準備期限切れで要求0/1件: 対象の準備処理を通らず既存の一覧検査へ到達することを一時対照で確認。
2. 片側self: 外部側だけの役割限定一覧とself指示の保持を既存テストで確認。
3. 改ざん・停止未確認: prepare以外を偽物にして検査を空洞化していないか既存テスト・diffで確認。
4. プロンプトの段落構造: exception_lines()不変、runnerが実際に追加した例外一覧を抽出することを確認。
5. 外部役割失敗: 状態が分かる診断を一時注入で確認し、診断文だけの恒久テストは追加しない。

## Task 1: テストの準備分離と状態診断（runner担当 Devin）

**Files:** Modify/Test `.agents/skills/review-fix-planning/tests/test_run_roles.py` のみ。

**Interfaces:** 既存 `launch(inputs, tmp_path, selected, **kwargs)` → BatchResultを利用。新規fixture `prepared_worktree(monkeypatch: pytest.MonkeyPatch) -> None` は runnerモジュールの `prepare_worktree` の束縛だけを置換する。fakeは空のdestinationと準備ログを作り成功ProcessResultを返す。診断用の小さいhelperは必要な場合だけ同ファイルに置く。

**テスト要否:** 新規恒久テストなし。既存の安全権限S/F∩Sの検査を弱めず更新し、Lに当たるfixture自身と診断の確認は一時検証で行う。

- [ ] **Step 1: 現状とRED相当の対照。** 対象テストを読む。セッション領域の一時pluginで元のrunner準備を即時timed_outにしたとき、対象テストが要求不足で失敗することを観測する。実20秒待機や実モデル再現はしない。一時ファイルは担当用セッション領域、追跡worktree外に置く。
- [ ] **Step 2: 局所fixture。** 上記signatureのfixtureを追加し、Spec列挙5テストへ明示適用。実行・receipt・collect・監査を丸ごと置き換えない。既存runnerテストのquick_prepareの前例を参照できる。
- [ ] **Step 3: 状態診断。** 必要な外部役割の成功を要求し、失敗した役割名/stateとattempt診断をassertionに含めてから要求件数・例外一覧を照合する。既存の安全assertionは残す。意図的に失敗を作る改ざん・停止未確認テストに成功必須を誤適用しない。
- [ ] **Step 4: GREEN・診断対照。** 一時pluginの同じ準備失敗条件でも新fixtureが適用された対象テストは成功することを確認。別の一時注入でadapterの失敗を起こし、失敗が状態付きで分かることを確認する。`uv run --project . --locked pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q` と `git diff --check` を同期実行し結果を報告する。受け入れ基準と禁止範囲の構造確認も行う。
- [ ] **Step 5: commitと報告。** 対象ファイルのみstageし `test: decouple external role assertions from worktree preparation` でcommit。所要時間・対照/テストのコマンド/終了コード・限界を報告。サブエージェント・有料再現・GitHub書込は禁止。

## Task 2: 取り込み後の統合・検証・公開（controller）

**Files:** Planの実施記録のみ必要に応じ更新。コードは変更せず修正が必要なら同担当へ依頼する。

**テスト要否:** 追加なし。既存テストの実行と一時対照・構造検査で証拠を残す。

- [ ] **Step 1: accept・Taskレビュー。** Task 1のBASEを記録。helper accept後に対象ファイルpytestとdiff検査を実行。brief・実装報告・diffパッケージを読み取り専用sp-reviewへ渡し、仕様準拠・品質双方の判定を得る。レビュー子にはテストを実行させない。重要指摘だけを同担当へ原文で渡す。
- [ ] **Step 2: 共通条件の統合確認。** controllerが5テストの適用先、実例外生成/プロンプト付与の保持、exception_lines()/期限/runner不変、状態診断を条件ごとに確認する。差分外のrunner準備はrunner全体の検証で担う。#400の実状態と段落構造の前提を再確認する。
- [ ] **Step 3: 最終検証。** 最後のcommit後、cleanなHEADで固定したverify-cmdsをhelper --reverifyにより実行。対象ファイルとrunner、全pytest、シェル27本、check-layout、diff検査。さらに対象ファイルpytestとシェル検証の同時実行を2回（同じ1回用の一時スクリプトを2回）行い、両者の終了を待ちexit0を確認する。親環境のCODEX_THREAD_IDは検証プロセスだけから除外し、永続環境を変更しない。
- [ ] **Step 4: 公開。** Issue/競合/baseを再確認。scan-before-push.shは親のものを使い捕捉baseのSHAを照合。全scan後の検査SHAだけをpushし、PRのbase/headを照合する。Refs #415と#400の残結合確認、Spec採否・実装担当・時間・base前進と再検証をPRに記録する。
- [ ] **Step 5: ループ。** 元のinspect 3担当、実装は利用者指示でDevinへ変更したことを記録しloop起動。自己レビュー/fix-checkは既定self。finalize.pyのみがマージする。終了時にIssue state・残項目・資源・Herdrを報告する。

## 要件・原因・検証の対応

Task 1が同原因の準備依存と失敗診断を修正、Task 2が入力→例外保存→要求→照合を通して5テストと共有runnerの条件を統合確認する。偽物の期待値で実装自身を照合しないよう、既存の独立した許可パス期待値と実プロンプトを比較する。一時RED/GREENは準備seamだけを対照にする。#400の両変更の実行証拠が無い場合は未確認を維持する。

## 実行予算

能動時間300分（利用者待ちを除く）。準備/Spec45分、Plan/実装/Taskレビュー35分、統合検証25分、PR10分、ループ最大3×（レビュー45分＋計画/修正15分）=180分、報告5分が目安。既に消費した時間もSESSION/budget.jsonlで数える。phase境界・50%・100%・worker失敗直後にcheckpoint。100%または安全失敗で停止。

runner実装期限90分、Specレビュー30分、ループinspect45分。提出の予約枠は実装15分・レビュー5分を目安とするが、事前停止宣言は行わずrunnerの期限と停止確認を使う。piは同期foreground待機、ツールtimeoutを付けない。監視ログを後から確認し、未確認停止を成功にしない。追加有料の評価は行わない。実装依頼1回、重要指摘の修正は上限2回、同一信頼性失敗の再試行は最大1回。ただしhelperがfailedなら停止し、controllerがselfで引き取らない。

ledgerとbrief等は `/workspaces/reso-world/tmp/agents/issue-415.gjerrhip/sdd/2026-11-13-issue-415-stable-role-tests/`、実装runnerの依頼は別のagent_tmpセッションに置く。失敗記録と最終検証ログを必要な間保持し、停止未確認やユーザ所有領域を削除しない。

## contingency（代替策）

- 最初の一時REDでAPI前提が異なれば、意味を保つ最小の一時検証修正だけをledgerに記録する。安全検査を弱める変更はしない。
- fake準備で他の処理が実Gitを必要として失敗するなら、必要な最小準備をテスト内だけで実施する案を調べる。runner変更が必要ならSpecの#400依存・停止条件に従い着手しない。
- 診断に問題があればTask 1範囲内で同担当へ依頼する。設定・quota・結果形式・監査失敗は失敗のまま保存して停止。担当の暗黙変更やJSON補正はしない。
- 予算が不足したら追加反復を増やさず、未実施事項・残結合確認・必要予算を記録して停止する。
