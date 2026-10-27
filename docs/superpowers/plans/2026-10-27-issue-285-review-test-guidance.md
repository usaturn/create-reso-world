# Issue #285 Review Test Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** pr-review の出力テンプレートを対象リポジトリのテスト方針と整合させる。

**Architecture:** テンプレートとセルフチェックの文言のみを最小編集する。既存見出し・ラベルと後段の形式を変えず、分類は対象リポジトリの規約へ委ねる。

**Tech Stack:** Markdown、既存のbash/pytest検証。

**Spec:** `docs/superpowers/specs/2026-10-27-issue-285-review-test-guidance-design.md`

**状態:** draft。実行許可は `issue-to-pr #285 --merge --max-cycles 3`。内容の承認は未取得。

## Global Constraints

- create-reso-world では `AGENTS.md`「テストの採用基準」を参照し、分類の定義をスキルへ複製しない。
- 外部リポジトリではそのリポジトリのテスト方針に従う。
- テスト提案が不要なら「なし」と記載でき、必要に応じてツール実行・静的解析・構造確認等の代替検証を記載できる。
- `Test suggestions` の見出し、指摘のラベル、既存のレビュー形式は維持する。
- 共通基準や既存テストの再分類・削減、パーサーの変更、他文書の例の一括修正は対象外。

## Review Focus

F/Lへの一律追加、必要な安全テストの抑止、外部方針の上書き、分類定義の重複、見出し・ラベル変更を確認する。固定文言テストはFなので追加しない。3例の判断照合と構造・参照・diff確認に置き換える。

## 受け入れ基準

- 動作環境: 現在のUbuntu Dev Container、create-reso-worldの隔離worktree。ワールド実体や外部リポジトリを変更しない。
- 実入力: 日本語の複数行レビューについて「文書の追随漏れ」「静的解析で検出できる誤り」「失敗を成功として報告する不具合」の3例で、テストなし＋代替検証／代表の必要なテストの両側をAGENTS.mdと照合する。
- 防御範囲: 一律のテスト追加要求と必要なテストの抑止を避ける文言、外部対象の方針、既存形式を守る。モデルの実際の遵守率、外部方針の内容、既存テスト整理は対象外。
- 新しい固定文言・見出しテストおよび有料モデル評価は追加しない。Issue指定の構造・参照・意味照合を採用する。

## 実行予算

全体540分（ループ上限3×レビュー45分＋修正90分を含む最大枠）。準備35分、実装・SDDレビュー40分、最終検証・公開30分、ループ405分、余裕30分。子は同期実行し、目安は実装15分・レビュー各10分、保存枠各3分。共有worktreeの実装・検証は強制終了しない。PRループはrunnerの期限と停止確認を使う。同一信頼性失敗の再試行は1回まで、安全失敗は再試行なし。phase境界・50%・100%・失敗直後にcheckpoint。ledgerは `/workspaces/reso-world/tmp/agents/issue-285.xk_yzd1u/budget.jsonl`。停止条件・後片付けは `.agents/execution-budget.md` と monitoring-long-tasks に従う。

## contingency（代替策）

初回の観測で形式等の前提が異なる場合、仕様の意味を保つ最小修正だけledgerへ裁定を残す。意味・安全境界が変わるなら停止する。委譲が止まれば同じ条件で再起動せず、既存の部分成果と停止条件を確認する。広範な文書整備やモデル評価への拡大はしない。

## 要件・Task・検証の対応

Task 1 がすべての文言変更と3例の照合を担当。統合担当（controller）が、観点→推奨対応→Test suggestions→セルフチェックの共通条件と見出し・参照を確認し、最終HEADでREADMEの3コマンドを記録する。共有コード/APIの変更なし。

### Task 1: 出力テンプレートの一律要求を除く

**Files:** Modify `.agents/skills/pr-review/SKILL.md` の「推奨対応」、`Test suggestions`、必要なら出力前セルフチェックのみ。

**Interfaces:** Consumes: AGENTS.md「テストの採用基準」、既存のレビュー形式。Produces: 形式を保持し方針に応じたテスト要否と代替検証を記載できるテンプレート。

**テスト:** 新設不要（Fの固定文言チェックとなるため）。実装は文書のみ。Issueの明示する検証方法を優先し、writing-skillsの有料の無し/あり評価は行わず、現状の誘因と修正後の意味を比較して報告する。モデル挙動の改善を実測したと主張しない。

**受け入れ基準（実装担当・レビュアー共通）:**
- 動作環境: 現在のUbuntu Dev Container、create-reso-worldの隔離worktree。ワールド実体や外部リポジトリを変更しない。
- 実入力: 日本語の複数行レビューについて「文書の追随漏れ」「静的解析で検出できる誤り」「失敗を成功として報告する不具合」の3例で、テストなし＋代替検証／代表の必要なテストの両側をAGENTS.mdと照合する。
- 防御範囲: 一律のテスト追加要求と必要なテストの抑止を避ける文言、外部対象の方針、既存形式を守る。モデルの実際の遵守率、外部方針の内容、既存テスト整理は対象外。
- 新しい固定文言・見出しテストおよび有料モデル評価は追加しない。Issue指定の構造・参照・意味照合を採用する。

- [x] **Step 1:** 変更前の2テンプレートと観点・セルフチェックを読み、3例で現状が一律要求に読める箇所を報告へ記録する。
- [x] **Step 2:** 「推奨対応」から無条件のテスト要求を除き、`Test suggestions` に対象リポジトリ方針、create-reso-worldの参照、不要時の「なし」と任意の代替検証を明示する。必要なセルフチェックも整合させる。
- [x] **Step 3:** 3例の判断を照合し、S/F∩Sの必要な守り・拒否に対応する正例を妨げずDの網羅を求めないことを確認する。分類はスキルへ複製しない。
- [x] **Step 4:** `git diff --check`、相対参照先・見出しとラベルの前後比較、`uv run pytest tests/skills .agents/skills/pr-review .agents/scripts/tests/test_review_findings.py -q` を同期実行する。前後比較は一時的な確認に留め、固定文言テストをコミットしない。
- [x] **Step 5:** 自己レビュー後に対象ファイルだけcommit（`docs: align review test suggestions with repository policy`）し、所要時間・3例・検証ログと終了コードをTask reportへ記録する。Planのチェックはcontrollerが行う。push/PR/他エージェント起動はしない。

## Controller integration

- [ ] Task 1 の差分と証拠を検査し、Taskレビューと最終全体レビューを実行する。
- [ ] Planを更新・commitした最終HEADのclean状態で、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を実行してchecks-fileへ記録する。
- [ ] 競合を再確認し、Gitleaks検査したSHAをpush、PRを作成する。PR作成後はfeature worktreeをループ外で変更しない。
- [ ] pr-review-fix-loopを `--max-cycles 3` で実行し、finalizeの観測結果とIssueの状態を報告する。
