# Issue #364 checkout 監査説明 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** #350 後の監査の区分を4か所の説明に反映する。

**Architecture:** `interfaces.rst` の既存仕様を基準に、下流4か所だけを更新する。1 Task を controller が直列実装し、独立した全体レビューと指定の PR 修正ループを行う。

**Tech Stack:** Markdown、Git、既存の Bash / uv 検証。

**Spec:** `docs/superpowers/specs/2026-11-09-issue-364-checkout-audit-docs-design.md`

**状態・実行許可:** `draft`。issue-to-pr の明示指示による実行許可であり、内容承認ではない。

## Global Constraints

- 変更は Spec の4か所と本 Spec・Plan のみ。コード・テスト・設定・過去の文書は変更しない。
- base は origin / refs/heads/main / `7f008486fdf43d9d79b84d0adcde02fc4e41d8ef`。移動・競合・close・安全の失敗を検出したら停止する。
- `unprotected_changes` は起動も受け取りも止めない。sandbox・書込元の特定を保証しない。
- 新規テストは不要（文書の文言は AGENTS.md の F）。固定文字列テストを追加しない。

## Review Focus

以下は文言テストではなく、Task 1 の意味照合で確認する。

- main worktree が依頼対象でない場合を、保護対象として説明しない。
- 対象を特定できない場合の全登録保護を省略して誤解させない。
- runner が返す警告と、受け取り入口が拒否する条件を区別する。
- `unprotected_changes` を古い記録の必須項目として説明しない。
- 他セッションの変化から担当の書込を断定せず、利用者の確認を促す。

## 受け入れ基準

- 動作環境: 現在の Dev Container、専用 linked worktree。実機操作や rebuild は不要。
- 実入力: 指定4か所の日本語・複数行の Markdown、`repository`、`outside_changes`、`unprotected_changes`。現行 `interfaces.rst`「期限と保持」を独立の比較元にする。
- 防御範囲: 保護対象の変化・消失・監査不能と、main worktree を含む保護しない checkout の内容の変化・回収・監査不能を取り違えない。対象特定不能なら全登録。古い記録を考慮する。sandbox、Gitignored 資源、監査範囲外の書込の保証や実装変更は対象外。

## Task 1: 4か所の説明を現行の区分へ合わせる

**Files:** Modify `.agents/monitoring-runtimes.md`、`.agents/skills/pr-review-fix-loop/references/records.md`、`.devcontainer/README.md`、`docs/agent-runner-checkout-recovery.md`（Spec が指定する各1か所のみ）。

**Interfaces:** Consumes: `tools/agent_runner/interfaces.rst`「期限と保持」。Produces: 現行仕様に一致する運用・記録・cursor・回収の説明。共有する意味の統合担当は controller。

**テスト:** 新規不要（F）。代替検証は下記の実行・差分・意味照合。

- [x] 4か所を最小置換する。両方の区分、保護対象と特定不能の例外、受け取り拒否と報告のみ、古い記録への注記、因果を断定しない既存注意を文脈に応じて記す。
- [x] Spec の条件1〜5と Review Focus を、現行 interfaces.rst と4か所の diff に対応付けて意味照合する。回収手順や隣接段落が変わっていないことも確認する。
- [x] `git diff --check`、`bash scripts/check-layout.sh` を実行する。Expected: 終了コード0。新規テスト・実装差分がない。
- [x] 明示した4パスだけを stage し `docs: align checkout audit reporting guidance` で commit する。実行証拠は親のセッションに記録する。

## 要件・検証対応 / 統合

保護対象と両区分（条件1〜3）→4か所の diff と仕様の意味照合。因果（条件4）→monitoring と回収冒頭の既存注意を確認。記録の互換（条件5）→records の review.batch 行を確認。controller がすべて担当し、独立レビュアーにも同じ受け入れ基準・Review Focus・Spec・Plan・差分・検証結果を渡す。

全体レビュー後、README の共通入口 `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` と `git diff --check` を clean な最終 HEAD で同期実行し、HEAD・base・argv・終了コード・ログ絶対パスを保存する。Gitleaks 検査した SHA を push、PR の base/head を照合する。GitHub Actions は規約どおり無効のまま。マージ後の実機確認は残らないので `Closes #364`。

## 実行予算

全体240分（準備・設計20、編集・統合レビュー15、共通検証25、公開10、PRループ最大3×55=165、予備5）。単純な文書変更だが共通検証・利用者指定ループを含む。ledger は親の `tmp/agents/issue-364.95_cvygq/budget.jsonl`、Task 記録は同セッションの `sdd/2026-11-09-issue-364-checkout-audit-docs/`。ループ review の期限は runner の45分、修正担当は最大90分だが全体予算を延長する根拠にしない。同期のロール子は自己完結した調査・全体レビューを各1回、実装は self。共有 worktree に書く worker は起動しない。任意停止用 worker はなく、予約枠・無進捗停止は適用しない。同期終了と終了コード・実ログを確認する。

同じ信頼性の失敗は原因修正後1回まで。安全の失敗は再試行せず停止。checkpoint は準備・Task・検証・公開・各ループの境界、50%・100%、worker失敗直後。成果を残す必要がある検証ログ・base記録・finalize証拠はセッションに保持し、不要なものは最後に回収する。残す場合は完全パスを報告する。

## contingency（代替策）

最初の検証で出力や前提に差があれば、仕様を変えない最小修正を ledger に記して継続する。意味が変わる、範囲外の修正や本体の不具合が必要なら停止して報告し、他の Issue へ広げない。共通検査の既存不具合を本件で隠さない。時間不足なら文書と証拠を保存して未完了で報告し、テスト件数や別版の成功で代用しない。baseの移動は再取得した値へ無検証で差し替えず停止する。
