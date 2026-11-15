# Issue #434 Review scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pi の初回 sp-review 依頼に scope・選択した upstream テンプレート・証拠が揃うよう常設指示を補う。

**Architecture:** `.pi/APPEND_SYSTEM.md` の既存のサブエージェント起動節だけを更新する。共通スキルやパッケージは変更しない。runner に1つの Task を依頼する SDD とし、統合担当が静的シナリオ照合と既存の検証を行う。

**Tech Stack:** Markdown、Pi、pi-superagents 1.14.4、既存 Bash/Python 検査（Python は uv）。

**Spec:** `docs/superpowers/specs/2026-11-15-issue-434-review-scope-design.md`

## 管理・実行許可

- 状態 `draft`。利用者の `#434 --merge` と担当指定に基づく issue-to-pr run。追加の内容承認は得ていない。
- 対象 `usaturn/create-reso-world`、code/docs は `/workspaces/reso-world/.worktrees/issue-434-review-scope`、branch `fix/issue-434-review-scope`。
- base は `origin/refs/heads/main`、捕捉 SHA `eb9e378bd803a77c75fa01a30d92ccf0b3682f48`。未 push の非重複 fast-forward だけ helper の上限3回と再検証で追随する。
- 明示の設計・Spec レビューを実施済み。設計 sound、Spec S1（minor）を採用しテスト実行禁止の優先を明確化。両方の helper が次工程への継続を返した。レビュー記録の追記後の SHA はセッション JSON に保持する。

## Global Constraints

- **動作環境:** Ubuntu 26.04 LTS の Dev Container、信頼済みプロジェクト内の Pi、導入済み `@teelicht/pi-superagents` 1.14.4。非 Pi や信頼前の挙動を保証しない。
- **実入力:** 日本語の Task と受け入れ条件を含む複数行の依頼。初回は `Review scope: task` と task-reviewer-prompt.md の入力、限定再レビューは `Review scope: re-review` と前回指摘・修正 diff、ブランチ全体は `Review scope: branch` と全体 diff を渡せる。
- **防御範囲:** 対象は sp-review の依頼文を作る常設指示。パッケージや upstream を変更せず、NEEDS_CONTEXT の拒否・レビュー子の読み取り専用・テスト実行禁止・利用者所有の Persona 節を維持する。マーカーだけ、証拠なし、scope の取り違えを十分な依頼として案内しない。
- `## Response Persona` 以降は利用者所有のため、1 バイトも変更しない。
- 上流テンプレートに focused test 実行を許す記述があっても、このリポジトリの禁止を優先し、テストや最小再現は実装担当か調整役に依頼する。依頼例にもこの制限を含める。

## Review Focus

恒久テストを足す項目はない（文言の F/L）。次の5点を Task の静的照合と controller の統合確認で確認する。

1. 初回 Task のマーカー不足を常設指示から補える。
2. 文脈不足の再送を、修正後の `re-review` と取り違えない。
3. ブランチ全体のレビューを Task の diff だけで済ませない。
4. マーカーだけでなく、upstream テンプレート本文と必要な証拠を渡す。
5. NEEDS_CONTEXT をレビュー未実施と扱い、上流の Tests 節よりレビュー子のテスト実行禁止を優先する。

## 実行方式と担当

`--implement pi_opencode-go_deepseek4-flash_max` により self=false、fallback は空。`implement_task.py` に1 Taskずつ依頼し、accept 後に controller が関連検証と sp-review の Task レビューを行う。実装担当の失敗を理由に controller が実装を引き取らない。レビュー子は読み取り専用・テスト実行禁止。sp-review のモデルはロールの tier を使用し、通常の呼び出しに model を足さない。

共有する前提（マーカーの意味、テンプレートの要求、テスト権限）は1ファイルに集約する。controller が導入済みロール・Task brief・依頼例・実 diff を条件単位で照合する責任を持つ。`--merge` により、SDD 最終のブランチ全体レビューは PR 修正ループ1サイクル目で代える。Task レビューは省略しない。

### Task 1: 常設指示に sp-review の依頼要件を加える

**Files:**
- Modify: `.pi/APPEND_SYSTEM.md` の `## サブエージェントの起動` のみ
- Test: 新規・既存テストの編集なし（F/L）。既存保護テストを実行する。

**Interfaces:**
- Consumes: 導入済みロール `/home/vscode/.pi/agent/npm/node_modules/@teelicht/pi-superagents/agents/sp-review.md`、選択した upstream task/re-review/branch のレビュー用テンプレート。
- Produces: Pi の controller が初回から正しい scope と必要な証拠を含む依頼文を作れる常設指示。

**受け入れ基準:** Global Constraints の動作環境・実入力・防御範囲と、その後の Persona・テスト実行禁止の2行を同じ本文で実装担当・Taskレビュアーへ渡す。

- [x] **Step 1: 変更前の不足と upstream の要求を読む**
  `.pi/APPEND_SYSTEM.md` の現状を読み、3マーカーの案内が無いことを確認する。導入済みロールと upstream の `subagent-driven-development/task-reviewer-prompt.md`、`re-review-prompt.md`、`references/final-review.md`、`requesting-code-review/code-reviewer.md` を照合する。上流 checkout は `/home/vscode/.pi/agent/git/github.com/obra/superpowers/skills/`。
- [x] **Step 2: 既存節に最小の案内を追加する**
  単独行の必須マーカーを1依頼1つ、task/re-review/branch の使い分け、テンプレートと証拠、NEEDS_CONTEXT 未実施、文脈補充の同scope再送、レビュー子のテスト禁止優先を加える。各テンプレート名を短い表などで示し、本文全文の複製を避ける。新しいツール引数・制限緩和・他ファイル編集をしない。
- [x] **Step 3: 3種類の複数行依頼例を静的に照合する**
  日本語の受け入れ条件を含む Task、前回指摘原文と修正 diff の限定再レビュー、全体 diff のブランチレビューを、追加後の指示から組み立てられるか確かめる。例には必要な証拠の種類とレビュー子のテスト実行禁止を含める。例の保存は controller に任せ、tracked ファイルに例や固定テストを追加しない。追加の動作試験用 runner/CLI 起動は禁止。
- [x] **Step 4: 既存の関連検査を同期実行する**
  `bash tests/scripts/test-instructions.bash`、`bash scripts/check-layout.sh`、`git diff --check`。すべて終了コード0を確認する。新しい固定文言テストは書かない。
- [x] **Step 5: 差分を自己確認し commit する**
  `git add .pi/APPEND_SYSTEM.md`、`git commit -m "docs: document pi sp-review scope requirements"`。変更点・検証コマンドと終了コード・所要時間・懸念を報告する。指示だけのためTDDの恒久テストは不要。Persona保護の既存テストは F∩S として維持する。

## 統合担当の検証と公開

1. accept 後の関連検証を実行し、実装の自己申告だけに頼らない。Task開始前の BASE と accept 後 HEAD の review package を作り、同一 brief・受け入れ基準・report と upstream テンプレートを sp-review に渡す。依頼に `Review scope: task` の単独行を含める。
2. 3種類の静的依頼例と意味の照合結果を `/workspaces/reso-world/tmp/agents/issue-434.pe2kx9ad/` に保存する。初回 Task の実レビュー結果は Task gate の証拠とし、将来のSDD3回の効果評価には数えない。
3. Spec の条件→Task 1→静的例・実 diff→検証ログを対応させる。マーカーなし・証拠なしは十分な依頼ではないこと、NEEDS_CONTEXT 後の再送と修正後再レビューを区別することを確認する。
4. 最後の commit 後、clean HEAD と捕捉 base を確認して、次の必須検証を worktree root で実行する。実 argv・終了コード・ログ・HEAD・base を SESSION に記録する。必須コマンドは Plan commit 後に `verify-cmds.json` と helper で固定する。
   - `bash .devcontainer/run-tests.bash`
   - `bash scripts/check-layout.sh`
   - `uv run pytest tests/skills .agents/skills .agents/scripts tools`
   - `git diff --check`
5. Gitleaks で検査した SHA のみ push。PR に Spec の決定理由・担当・検証・時間・未確認事項を書く。CI は AGENTS.md により無効のまま。`Refs #434` とし、後続SDD3回の評価は未実施と明記する。
6. PR 修正ループを利用者の指定のまま実行し、finalize.py のみでマージする。ループ後、Issue に PR URL と残るSDD3回の評価をコメントする。Issue state は実際の観測値を書く。

## 要件・Task・観測の対応

| 要件 | 担当 | 観測・検証 |
|---|---|---|
| 3 scope の選択 | Task 1 / controller | 3例と installed role・upstream を静的照合 |
| テンプレート本文と証拠 | Task 1 / controller | brief・report・受け入れ条件・前回指摘・diff の範囲の対応 |
| NEEDS_CONTEXT とテスト権限 | Task 1 / controller | 文言と依頼例の意味を確認、既存指示保護テスト |
| Persona・対象外を保護 | Task 1 / controller | test-instructions・diffの編集範囲 |
| 今後3回の効果 | マージ後の運用 | 未確認としてPR/Issueに残し、自動closeしない |

## 実行予算

全体270分（準備後からの ledger、先行の読み取り調査約18分は別記）。設計・Spec20分、Planと実装25分、Taskレビュー15分、統合検証20分、公開10分、ループは最大3×（レビュー45分＋計画・修正15分）を目安とする。270分到達では延長せず停止する。

- 設計・Spec worker: runner既定期限（各45分）内、再起動を繰り返さない。完了済みの所要は107.96秒・768.69秒。
- 実装 worker: runner の90分期限、Taskごと直列。retry/rejected の同一原因の再試行は1回まで、failed は停止。共有worktreeを変更せず、完了まで同期で待つ。
- Taskレビュー: 同期 subagent、通常10〜15分目安。非同期化・途中kill・未完了の成功扱いはしない。
- PRレビュー: runner/loop の45分期限、ループ上限3サイクル。予約枠・無進捗打ち切りは別途設定せず、runtime既定の同期終了・停止確認に従う。動作試験のための追加の有料起動は0回。
- checkpoint: 設計/Spec・Task・検証/公開・ループの各境界、予算50%・100%、worker失敗直後。ledger は `SESSION/budget.jsonl`、SDD領域は `SESSION/sdd/2026-11-15-issue-434-review-scope/`。
- SESSION はレビュー記録・再利用する検証ログを含むため終了後も残し、完全パスを報告する。runnerの各依頼は結果処理の直後にhelper cleanup、未停止資源は消さない。

## contingency（代替策）

- 既存案内だけで要件を表現できなければ、最小範囲の説明に戻してSpecの意味を維持する。共通スキル・ロールへ無断で広げない。
- 上流テンプレートと既存制約の違いは、既存の安全境界を優先しledgerに記録する。仕様の意味を変える必要がある場合は停止する。
- 初回の検証で環境前提が異なれば、出力を保存して原因を調べる。既存の失敗を成功扱い・検査削減で回避しない。安全の失敗・停止未確認・担当failedでは全体停止する。
- base 前進時は所有パスの非重複・未push等のhelper条件を満たす場合だけ追随し、必須検証をすべて再実行する。条件外なら公開せず報告する。

## 実行記録

- Task 1 の BASE `13750f248ed8a114722a5a8556cab46e1d5bd0fc`、実装 `8bb150a0138be3da18cd9e4a0dd69430f62ba416`。依頼1回、requested/actual は `pi_opencode-go_deepseek4-flash_max`、identity `opencode-go/deepseek-v4.1-flash` max、fallbackなし。所要167.55秒（worker158.19秒）、exit0・stop_confirmed=true、accept成功、cleanupのretainedは空。担当自身とcontrollerが指示保護・配置検査・diff --checkを実行しすべてexit0。
- sp-review の初回Task依頼は `Review scope: task` と、同じbrief・受け入れ基準・report・Task全体diff・上流テンプレートを使用した。Spec compliant / Task quality Approved、Critical/Important/Minorなし、NEEDS_CONTEXTなし。レビュー子はテストを実行していない。
- 「3種類の依頼例の照合はdiffから確認不能」の⚠️はcontrollerが3例を保存し、導入済みロールと対応するupstreamテンプレートへ意味を照合して解消。`.pi/APPEND_SYSTEM.md:20-31` がscope・証拠・同scope再送・テスト禁止優先を案内し、Personaは既存SHA検査で不変。
- 静的例と照合記録: `/workspaces/reso-world/tmp/agents/issue-434.pe2kx9ad/static-scenarios.md`、`static-re-review-request.txt`、`static-branch-request.txt`、Task依頼は同SESSIONの`sdd/2026-11-15-issue-434-review-scope/task-1-review-prompt.md`。限定再レビューと全体の例は未送信。実行時の効果を確認したとは主張しない。
- 関連ログとレビュー記録は同SESSIONに保存。設計・Spec両レビューのcleanupもretainedなし。保護checkoutのoutside_changesなし。unprotected_changesの他作業の領域は触っていない。
- 残り: 最後のcommit後の必須検証、秘密検査・push・PR作成、PR修正ループ。以後SDD3回の運用評価はマージ後に残し、Refs #434 とする。

## 実装前の照合結果

Spec の全条件と対象外を上表に対応させた。変更は文書1ファイルで共有状態・新規APIはなく、実行時強制や3回評価の代用は行わない。Review Focus はTask 1とcontrollerのシナリオ照合で扱い、AGENTS.mdのF/L基準に反する恒久テストは足さない。
