# Issue #391 issue 実装担当の既定変更 Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development; issue-to-pr の runner で Task ごとに依頼する。

**Goal:** issue-to-pr の実装担当の雛形の既定を self にし、説明を揃える。
**Architecture:** 既存の設定解決を使い、設定と文書だけを同時に更新する。
**Tech Stack:** TOML、Markdown、reStructuredText、agent-runner、uv。
**Spec:** `docs/superpowers/specs/2026-11-11-issue-391-issue-implement-self-design.md`（draft）。
**実行許可:** Issue #391 に対する `issue-to-pr --merge` 指示。承認済みではない。

## Global Constraints

fix の assignment、agent 定義、明示指定と個人設定の優先順位、個人設定、runner とレビュー機構、#353 の履歴は変更しない。固定値や文言を写すテストは追加しない（F）。

## 受け入れ基準

Dev Container の現行環境で、空の一時 TOML と作業 worktree の雛形を `implement_task.py check --config ... --template ...` に渡すと self true、空 fallback。さらに `--implement claude-code_sonnet_xhigh` で明示 agent を選択。個人設定と明示指定の優先順位は変えない。5 ファイルで新しい既定の説明と実設定が一致し、fix とレビュー担当は変わらない。対象外は個人設定や runner の変更。日本語説明も実際の設定に照らして確認する。

## Review Focus

- 雛形のみの入力と明示指定の両方を実際の helper で確認する。
- 個人設定を自動変更せず既存の優先順位を維持する。
- fix とレビュー担当を含む無関係な設定の差分が無いことを確認する。
- 5 ファイルの新しい説明を肯定的に確認し、古い既定の説明を探す。
- 履歴の移行案内と現行の既定を混同しない。

## Task 1: 設定と説明を揃える

**Files:** `.devcontainer/agent-runner.toml`、`.agents/skills/issue-to-pr/SKILL.md`、`.devcontainer/README.md`、`README.md`、`tools/agent_runner/interfaces.rst`。
**Interfaces:** 既存の `implement_task.py check` の template/config/implement 入力は変更しない。

- [ ] 雛形の `[workflows.issue.assignments.implement]` を `agents = ["self"]` にし、空 fallback の既存挙動を保つ。対応コメントを self と明示選択の説明に更新する。
- [ ] 上記 4 文書の現行の issue.implement の既定説明を self に更新し、明示指定、個人設定、履歴の移行案内と矛盾させない。
- [ ] 新規テストは不要（設定・文言の固定値に該当）。一時空 TOML と worktree の template を使って helper の既定と sonnet 明示を実行し、2 つの結果を確認する。`rg 'issue\.implement|claude-code_sonnet_xhigh' README.md .devcontainer/README.md tools/agent_runner/interfaces.rst .agents/skills/issue-to-pr/SKILL.md` と差分で全説明と除外範囲を確認する。
- [ ] `uv run pytest tools/agent_runner/tests/test_config.py .agents/skills/issue-to-pr/tests` を実行する。コミット `fix: default issue implementation to self`。

## 統合検証と要件対応

統合担当が Task 1 の変更と受け入れを照合し、実 helper の 2 経路、5 ファイルの説明、無関係の fix・review 設定、移行案内を確認する。`uv run pytest`、`bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash` を実行し、最後の HEAD、clean status、コマンド・終了コード・ログと捕捉 base を記録する。要件に対応しない検証結果を成功の代わりにしない。

## 実行予算・contingency

全体 360 分（準備・Spec 35、実装 90、検証・PR 70、3 サイクルのレビュー各 45 分と修正 30 分）。worker は runner の役割期限を適用し、Task 実装 90 分、Spec レビュー 30 分、レビューは各 45 分。新たな途中停止は宣言せず、runner 自身の期限と停止確認を使う。信頼性の同一失敗の再試行は 1 回、安全の失敗は即停止。phase 境界、50%・100%、失敗直後に checkpoint。予算 100% または停止条件で報告し、範囲縮小や別担当への暗黙切替はしない。ledger は親の `tmp/agents/` の session に保存し、停止確認後に手順に従って片付ける。
