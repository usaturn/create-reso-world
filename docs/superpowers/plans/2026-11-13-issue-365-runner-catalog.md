# Issue #365 Runner Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AW 現行のカタログに、CRW 固有の key・配置・履歴を守って揃える。
**Architecture:** 1 Task でカタログと参照文書を一緒に変更する。runner の実装は変更しない。
**Tech Stack:** TOML / Markdown、既存 uv locked Python、agent-runner helper。
**Spec:** `docs/superpowers/specs/2026-11-13-issue-365-runner-catalog-design.md`
**状態:** `draft`。issue-to-pr と利用者の具体的な継続指示による実行許可。内容の approved ではない。

## Global Constraints

- base: `usaturn/create-reso-world` / `origin` / `refs/heads/main` / `768c7c410558c1b4b705e82ac0c4687c35b51734`。
- AW 比較元は blob `93f200f1504d8214fce26dc5f83cdf12b77631b2`。SESSION の `aw-agent-runner.toml` を使う。
- `review.inspect` の先頭は `claude-code_opus_xhigh`（Spec D2 の利用者委任による裁定）。旧 Sol 条件は不採用。
- Sol / OpenCode Go DeepSeek は `OPENCODE_API_KEY`、after_run は `--project .`。fix / issue の implement は `self`。
- adapter・helper・監査・key 導出・exec・配置・runtime 文書・個人設定・履歴の Spec/Plan/レビュー記録・#407 の tier 修正は対象外。
- #408 の Ollama 定義は並びと Opus の参照名以外を変えない。roles の値・権限・期限も変えない。
- 同じ worktree への並行書込は禁止。runner 実行中は controller も対象 worktree を変更しない。
- 実装は明示の `pi_openai-codex_gpt6-terra_xhigh`。失敗時に controller が引き取らない。Task は順に依頼し、各依頼を cleanup する。

## Review Focus

1. 個人 config の旧名参照だけ / 旧名の完全な独自定義 / 部分定義を区別する。自動変更せず、前者の拒否と移行後の成功を一時 config で実行する。
2. max を保持する個人 Sol 定義と xhigh を同じ役割に並べると duplicate_model になる。完全な独自定義の正例も確認する。
3. README の歴史表・移行用旧名と、現在の説明に残る旧名を混同しない。変更箇所を意味でレビューする。
4. AW の古い Alibaba コメントで CRW の現在の値を後退させない。#408 の key 説明を維持する。
5. 実行中の親雛形と変更後の feature 雛形を混同しない。利用者のループ指定は親で解決し、雛形単独の検証は空 config で隔離する。

## 受け入れ基準（実装・レビュー双方へ同じ本文を渡す）

- 動作環境: Ubuntu Dev Container、uv / Python の既存 locked 環境。実入力は日本語の複数行 TOML コメント、現行 AW の 21 agent、空の個人 config、旧名参照だけ / 完全な独自旧名定義 / 移行後の個人 config。
- Opus xhigh、Sol xhigh が有効で、review.inspect の先頭は D2 により Opus xhigh。roles と Ollama の値は base から変わらない。agent の値は上記の意図的差分以外 AW と一致する。
- agent / roles / workflow の並びとコメントを AW と対比でき、CRW の差異には理由がある。
- README の現行割当、effort、スキルの self の説明が実際の設定と一致する。履歴・移行説明以外に旧 Opus 名への現行参照が残らない。
- 雛形単独の check / list は成功し、既定に duplicate_model は無い。旧名参照だけの設定は拒否し、手動移行後は成功する。独自の旧名完全定義と max の個人設定は自動で失われない。
- 防御範囲: 実個人設定・key・ログイン・履歴・#408 の値を変更しない。alias と自動移行は対象外。check の成功を認証や実サービス起動の成功と表示しない。
- 新規の固定値テストは追加しない。スキルの説明変更は、変更前後の説明に従う一時適用シナリオと実際の設定解決・helper の self 分岐を比較する。既定割当を外部モデルと説明する変更前に不一致を観測し、変更後は self と一致することを確認する。対象手順を実行する検証であって固定文言の照合だけで代えない。個人設定は空の一時 config に隔離し、self の helper 呼出しまたは fake adapter / fake CLI のみを使う。検証のために実モデルを追加起動せず、別 context に説明させることは必須条件にしない。
- Issue 指定と README の検証入口を実行する。マージは PR 修正ループ内の finalize.py に限る。ボードの子なので PR は `Refs #365` とし、マージ後に完了状態を記録する。

## Task 1: カタログと参照の一括更新

**Files (Modify):**
- `.devcontainer/agent-runner.toml`
- `.devcontainer/README.md`
- `.agents/skills/review-fix-planning/SKILL.md`
- `.agents/skills/review-fix-planning/references/execution.md`

**Interfaces:** 既存の Config / load_config / run_roles.py の入力は不変。変更する外部参照名は Opus の `_default` → `_xhigh`。Sol は既に xhigh。出力は既存の設定スキーマ。

**テスト要否:** 新規の恒久テストは不要（F / L）。権限・env・duplicate_model の S は既存テストを実行する。下記の一時適用シナリオと CLI 検査を行い、文字列の固定値テストはコミットしない。

- [x] Step 1 (controller): base のスキルの既定担当説明と、空 config の設定解決・run_roles.py の self 分岐を使う一時適用シナリオを実行し、不一致を記録する。コード編集前に RED の根拠を残す。実モデルを呼ばない。ログ・一時スクリプトは controller が SESSION に作る。runner 担当には結果を渡し、許可4ファイル以外への書込を要求しない。
- [x] Step 2: AW の定義順にカタログを並べ、Opus xhigh / effort を変更する。AW のコメントを基本にし、Spec の CRW 固有説明と #408 の値を保つ。roles は AW の順序と説明に揃え、値は維持する。
- [x] Step 3: README の現行名・割当・effort・旧名手動移行・Sol max の完全な個人設定例を整える。#305 の履歴表は当時の記録として残す。API key の値は書かない。Ollama 節は機械的な名前追従以外を変更しない。
- [x] Step 4: review-fix-planning の 2 文書は実効の既定 implement=`self` と明示変更/fallback の説明に揃える。安全・レビュー・マージ手順を変えない。
- [x] Step 5 (controller、取り込み後): Step 1 を変更後で再実行し、説明と helper の self 分岐の一致を確認する。空 config check/list、旧名参照だけは拒否 / 移行後は成功、完全な旧名定義は保持、Sol max の独自定義は成功 / 同一モデルとの混在は拒否を、実設定解決で確認する。入力ファイルのバイトが変わらないことも確認する。AW との差異を TOML parse と diff で説明する。
- [x] Step 6: `uv run --locked pytest tools/agent_runner/tests -q`、`bash .devcontainer/test-install-beforehand.bash`、`bash scripts/check-layout.sh`、`git diff --check` を同期実行する。追加テスト無し、許可外差分無しを確認する。
- [x] Step 7: 4 ファイルだけ stage し `git commit -m "chore: align runner catalog and migration docs with current AW"`。結果 JSON の commands / concerns に commit・実行 argv / exit・所要時間・実装の要点を返す。ログと報告ファイルは controller が runner 出力から保存する。worker は SESSION・他 checkout に書かない。

## 統合担当（controller）

Task は 1 つ。名前 → workflow 参照 → CLI check/list → README/スキルの説明の一連の一致を controller が確認する。Task のテスト結果だけで満了とせず、受け入れ基準ごとの証拠を SESSION の ledger に残す。Spec/Plan の更新は controller だけが行う。

Task ごとに読み取り専用の sp-review を使い、必要な再現・テストは controller が実行する。指摘を採用するときは原文を担当へ渡す。`--merge` 適用 run なので、最終全体レビューは PR 修正ループの 1 サイクル目で代える。

## 必須の最終検証

cwd は CODE_ROOT。config は SESSION の `empty-config.toml`（空ファイル）を明示する。以下を Plan commit 直後に verify-cmds.json に固定する。

1. `uv run --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml --config /workspaces/reso-world/tmp/agents/issue-365.iuvh4cpo/empty-config.toml check`
2. 同じ global options で `list`
3. `uv run --locked pytest tools/agent_runner/tests -q`
4. `bash .devcontainer/test-install-beforehand.bash`
5. `bash .devcontainer/run-tests.bash`
6. `bash scripts/check-layout.sh`
7. `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`
8. `git diff --check`

一時の適用シナリオは Task 1 の controller 作業として実行してログを保持する。controller は実行結果と入力・出力を再確認し、最後の修正があればその経路を再実行する。共有の devcontainer 検証は他セッションと同時実行しない。最初の依頼は書込範囲と外部ログ保存の矛盾を担当が編集前に検出し NEEDS_CONTEXT を返したため、検証ファイル保存の責任だけを controller に明確化した（受け入れの意味・担当するコードは不変）。

## 実行方式・実行予算

- SDD の実装担当を implement_task.py の指定 runner に置換する。Task を分割しないのは同じ参照名・同じ文書の一括検証だから。
- 全体能動時間 360 分。準備約20分（予算 ledger 開始前の調査を含む）、Spec/Plan 20分、実装40分、Task review 15分、最終検証25分、公開10分、ループは最大3×（レビュー45分＋計画修正30分）を目安とする。重なる待機を二重計上しない。
- ledger: `/workspaces/reso-world/tmp/agents/issue-365.iuvh4cpo/budget.jsonl` と `sdd/2026-11-13-issue-365-runner-catalog/progress.md`。終了時は検証ログ・レビュー ledger を再利用するため SESSION を保持し、完全パスを報告する。
- Spec review 期限1800秒、実装5400秒、PR review2700秒は runner が守る。pi の同期 foreground（timeout を付けない）で終了と stop_confirmed を確認する。子の保存予約枠は終了前300秒を目安に prompt で案内する。別の強制停止宣言は行わず、無進捗だけで kill しない。
- 信頼性失敗の同じ原因の再依頼は最大1回。ただし helper の failed・停止未確認・Spec review 失敗などの停止規則を優先する。安全の失敗は再試行せず停止。個人設定・別担当へ黙って切り替えない。
- phase 境界、50%/100%、失敗直後に checkpoint。100% は停止。縮小候補は新規テスト・付随リファクタを行わないこと。受け入れ条件は勝手に削らない。

## contingency（代替策）

- 最初の RED が API 前提違いなら、意味を保つ最小の一時シナリオ修正を ledger に記録する。意味が変われば裁定を待つ。Opus/Sol の裁定は Spec D2 と利用者の具体的委任で済んでおり蒸し返さない。
- AW のコメントが CRW の現在の key/tier と矛盾するときは CRW の値と説明を保持し理由を記録する。所有外の修正は行わない。
- 未 push の base 前進は issue-to-pr の inspect-advance/advance/reverify で、非重複 fast-forward の累計3回まで。push 後の base 前進は停止し公開済み資源を報告する。
- 指定担当が失敗したら self に変更しない。禁止操作や課金の実機実験を回避策にしない。

## 要件照合・self-review

Spec のカタログ・並び・固有差分・移行・スキル修正は全て Task 1 に対応。各条件の観測は Step 1/5 の一時シナリオ、Step 6 の実行検証と controller の差分照合で得る。共有前提の確認は統合担当に集約する。未実施の検証を成功と記録しない。Plan の長さと変更4ファイルの規模を照合済み。

## Task 実行記録

Task 1 は `7f5fe7c8..f15bab49`、読み取り専用 Task レビューは Spec compliance PASS / quality APPROVED。初回依頼は書込先の文脈不足で NEEDS_CONTEXT（29.11秒・変更無し）、controller の一時検証へ責任を分けた2回目は importable（185.995秒）、requested=actual `pi_openai-codex_gpt6-terra_xhigh` / identity `openai-codex / gpt-6.1-terra / xhigh`。両方 stop_confirmed=true、outside_changes=[]、cleanup の retained=[]。再依頼の上限を消費済み。

controller が AW の21 agentの順・値、roles の順・値、workflows を比較し、env の2箇所と project の意図的相違だけであることを確認した。旧名参照の拒否・移行後成功・旧完全定義保持・部分定義拒否・README max例・duplicate_model の11ケースは全て期待どおりで、入力バイト不変。スキル適用シナリオは変更前の不一致（exit1）→変更後の一致（exit0）、実helper self分岐・保存、外部attempt0を確認した。CLI check/list・関連pytest305件・install-beforehand・layout・diff checkは成功。最後の README 全体検証と PR 修正ループはこの記録時点では未実施。ログと報告は SESSION に保持する。
