# Issue #187 checkout 監査 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**状態:** `draft`。実行許可は Spec の利用者指示に基づく。内容の承認は未取得。
**Goal:** 隔離した担当の成果を並行作業と両立して受け取り、消えた worktree の登録を安全に個別回収できるようにする。
**Architecture:** adapter の保証から必須 checkout の集合を決め、起動前と終了後に共通で使う。観測情報と受け取りを拒否する情報を別のフィールドに返す。
**Tech Stack:** Python 3.14 / uv、Git、既存の bubblewrap sandbox、pytest。
**Spec:** `docs/superpowers/specs/2026-10-20-issue-187-checkout-audit-spec.md`

## 全体の制約

- main checkout は編集せず、`/workspaces/reso-world/.worktrees/issue-187-checkout-audit` で作業する。
- 非隔離担当と fallback は全登録の必須監査を保つ。監査不能な必須対象を成功にしない。
- 他者の worktree・登録は削除しない。設定に監査除外リストを作らない。
- Python は uv で実行する。実モデル・実資格情報での隔離評価はしない。

## 実行方式と共有前提

issue.implement の検査結果は self。共通 policy と 3 入口は逐次変更するため inline の executing-plans を使う。統合担当はこのセッション。runner の実行と各入口の起動前判定で、投影後の role・全 fallback・main/依頼元の解釈を統一する。Task 1 が policy と全入口を担当し、Task 2 が手順と統合証拠を担当する。最後にブランチ全体をレビューし、PR 作成後は既定構成で最大 3 サイクルの独立レビュー修正ループを行う。

## Review Focus

- 非隔離 fallback が未実行でも、限定監査を許してはいけない。
- adapter のロード失敗、保証値が bool の true でない場合、保証の変化は限定監査の根拠にしない。
- 必須集合を得られない、または snapshot に必須パスが無い場合は監査不能として止める。
- runner が新しく作った試行と、既存の別セッションの checkout を混同しない。
- 消失と移動、locked と prunable を区別し、複数の消失登録のうち指定した 1 件だけを回収する。

### Task 1: 隔離保証と共通監査 policy を全入口へ適用

**担当ファイル:** `tools/agent_runner/{adapters/__init__.py,adapters/dsh.py,models.py,workspace.py,runner.py,checkout_policy.py}`、`.agents/skills/issue-to-pr/scripts/implement_task.py`、`.agents/skills/review-verify/scripts/dispatch.py`、`.agents/skills/review-fix-planning/scripts/run_roles.py`。関連する既存テストと新規 `tools/agent_runner/tests/test_checkout_policy.py`。

**Interfaces:**
- `Capabilities.confined_writes: bool = False`。DSH の既存 outer sandbox だけ true。
- `workflow_checkout_scope(config, workflow, repository, *, adapter_loader=load_adapter) -> frozenset[str] | None`。None は全件必須。
- `require_auditable_workflow(config, workflow, repository, *, adapter_loader=load_adapter)`。予約・起動前に呼ぶ。
- workspace の `protected_checkout_paths(repository) -> frozenset[str] | None` は Git が示す main と依頼元の root を返す。bare 等で限定できなければ全件必須。
- `require_auditable_checkouts(repository, *, required_paths=None)` は選択した必須パスの失敗と欠落を拒否。
- `BatchResult.unrelated_checkout_audit: list[CheckoutAudit] = []`。既存の拒否用フィールドは必須対象だけを含む。

**テスト要否:** 必要。受け取りの安全条件と並行編集による実際の不具合を実行して確かめる。

- [ ] RED: 実 Git と偽 adapter で C1〜C3/C5 を再現。別 checkout の編集・消失、main/依頼元の編集・監査不能、混在 fallback、全 self、ロード失敗を対照にする。起動前の拒否では出力先が作られず、有料起動に進まないことを確認する。
- [ ] GREEN: policy を追加し、全候補の保証を判定。runner は実際に使う adapter の保証も起動直前に確認し、保証が変わった場合に非隔離で起動しない。全 snapshot を保ち、終了後の診断を分ける。3 入口に同じ事前判定を適用する。
- [ ] C4: 実 DSH adapter と偽 CLI で、main・依頼元・隣・共有 .git・host /tmp への書き込み拒否と試行内出力を確認する。別セッション相当の controller の編集は sandbox の外から行う。
- [ ] 検証: `uv run --locked pytest tools/agent_runner/tests .agents/skills/issue-to-pr/tests/test_implement_task.py .agents/skills/issue-to-pr/tests/test_implement_task_run.py .agents/skills/review-verify/tests/test_dispatch.py .agents/skills/review-fix-planning/tests/test_run_roles.py`。Expected: exit 0。
- [ ] `git diff --check` と差分レビュー後、明示パスを stage して `fix: scope checkout audits to confined agent workflows` で commit。

### Task 2: 個別回収の手順と統合検証

**担当ファイル:** `docs/agent-runner-checkout-recovery.md`、`tools/agent_runner/interfaces.rst`、上記 Spec/Plan の実施記録。
**Interfaces:** Task 1 の監査フィールドと、変更しない厳格監査の制限を説明する。
**テスト要否:** 文書の文字列照合テストは不要。使い捨て Git リポジトリでコマンドを実行し、移動の repair と 1 件の消失登録だけの remove、locked の拒否を確かめる。証拠はセッションログに保存する。

- [ ] find-docs で取得した Git の公式仕様と実コマンドで、登録・所有者・停止・rebuild の時点・未保存データの照合手順をまとめる。回収許可は prunable だけから推測しない。
- [ ] 既存の interfaces.rst を更新し、監査範囲・診断フィールド・非隔離担当の直列運用と回収手順への参照を記載する。
- [ ] 全体検証を実行: README の非ワールド用 3 コマンド（`.devcontainer/run-tests.bash`、`scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`）と `git diff --check`。Expected: exit 0。worktree での配置検査の制約があれば、実ログに基づいて原因と代替を記録する。
- [ ] ブランチ全体レビューと C1〜C6 の証拠照合。Spec/Plan に実施結果を追記し、`docs: describe targeted checkout registration recovery` で commit。最後の commit 後、clean HEAD に対して再利用可能な検証記録と finalize 用 checks-file を作る。
- [ ] Issue・競合を再確認し、PARENT_ROOT の scan-before-push.sh で検査した SHA を push。`Closes #187` と設計判断・時間・検証結果を含む PR を作成する。
- [ ] PARENT_ROOT の loop.py を使い review-fix-loop を起動する。既定担当・最大 3 サイクル。マージは finalize.py のみ。親 checkout のスクリプトが未適用の変更のため止まる場合も、回避せず状態と次の操作を報告する。

## 実行予算

能動時間は 240 分を上限とする。準備・設計 20 分、実装 45 分、検証・PR 40 分、レビュー修正ループ 135 分（3 × レビュー 45 分を上限の目安。早く終われば残りを計画・修正に使う）。ledger は `/workspaces/reso-world/tmp/agents/issue-187.wfma953n/budget.jsonl`。

実装 worker は起動しない。テスト・lint を途中停止しない。ループのレビュアーは既存 runner の 45 分の期限・停止確認を使う。修正担当は既定 claude-opus、self-review/fix-check は self で、ループ外の有料モデル評価は 0 回。信頼性の同じ失敗は再試行 1 回まで、安全の失敗は即停止。phase 境界、50%・100%、worker 失敗直後に checkpoint を記録する。

隔離の証拠が不足した場合、無条件の監査緩和へ変更しない。実装を止めて不足を報告する。回収手順の範囲を自動回収へ広げない。ループが既存の監査不能登録や外部ツール障害で止まれば、その資源を残して再開方法を報告する。scope の採用条件を広げる変更は Spec の決定記録を更新し、委任の範囲を再確認する。

## 実施記録

未着手。実行の証拠は Task ごとに追記する。
