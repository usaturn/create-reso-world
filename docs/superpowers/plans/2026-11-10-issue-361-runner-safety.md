# Issue #361 Runner Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全 workflow の runner 共通指示で共有 stash と他セッションのプロセスを保護する。
**Architecture:** 既存の共通指示の1行目に安全制限を折り込み、2行構成と例外一覧の配置を維持する。fake adapter が受け取る依頼文で回帰を検査する。
**Tech Stack:** Python >=3.14、uv、pytest、既存の fake adapter。
**Spec:** `docs/superpowers/specs/2026-11-10-issue-361-runner-safety-design.md`
**状態:** `draft`。利用者の issue-to-pr による実行許可で進める。内容の承認は未取得。

## Global Constraints

- コードの変更は `tools/agent_runner/runner.py` と `tools/agent_runner/tests/test_runner.py` のみ。
- 禁止は書き込み可否の両方に適用する。write exceptions は許可された書き込み範囲の指定であって、これらの安全制限の解除ではない。read-only の担当へコピーや commit の許可を新たに与えない。
- 指示は従来どおり空でない2行と区切りの空行とし、禁止事項を1行目に折り込む。`writes=...` の2行目と exceptions の見出し・順序・本文を維持する。呼出元の複数行・日本語本文を変えない。
- Python は uv。実モデルを使うテストは追加しない。共有 stash・他セッションのプロセスを使った検証はしない。

## Review Focus

- 書き込み例外付きの依頼でも安全制限が共通部分にあり、既存の例外順序を変えない（既存依頼文テストで確認）。
- read-only の依頼に copy/commit を無条件で許可しない（文意のレビューと既存 writes 行の維持を確認）。
- Python の bootstrap 例外を repository 全体から削除したと誤読させない（担当が直接実行する場合の制約とする。文意のレビュー）。
- 複数行・非ASCII本文を保持する（fake 入力の既存テストを利用し、必要なら対象の既存検査の本文を変更して実行）。
- 新規の固定文言テストは F∩S の安全範囲だけにする（レビューで採用基準と照合）。

## 受け入れ基準（実装・レビューへ同文を渡す）

動作環境: Ubuntu Dev Container、Python >=3.14、uv。実入力: fake adapter の caller 本文 `変更を確認する\n次の行も保持する` と、書き込み例外 `/x/reviews: run records`・`uv cache with spaces`。防御範囲: 共通指示に全 git stash（pop を含む）の禁止と全 worktree で共有される理由、pkill -f/killall の禁止と自分が起動したプロセスだけ PID 指定で停止可、担当の bare python/python3 と python - heredoc を禁止し uv run を使う指示がある。2行構成・writes 行・例外順序・caller 本文は維持する。例外や read-only によって禁止が消えず、read-only に copy/commit の許可を増やさない。対象外: sandbox による強制、self 割当、付属 bootstrap の内部実装。コード変更は runner.py と test_runner.py のみ。新規の永続テストは stash・プロセスの安全指示を守る F∩S に限定し、防ぐ損害と理由を書く。

## 実行方式

SDD。`implement_task.py` で利用者指定 `pi_opencode-go_deepseek4-flash_max`（fallbackなし）に1 Taskを依頼し、accept後に controller が再検証。Task review と最後の全体レビューは pi-superagents `sp-review` に読み取り専用で依頼する。公開後は指定3レビュアーの pr-review-fix-loop に進む。実装担当の暗黙の変更はしない。

## 要件・Task・証拠の対応

Spec 1–4 は Task 1 の共通指示と文意レビュー。stash/プロセスは同 Task の RED→GREEN、Python は実際の request と差分で検査。Spec 5 は同 Task の既存 API/CLI と関連 workflow 回帰検査。Spec 6–7 は同 Task の F∩S コメントと関連スイート。統合担当 controller は使い捨て2 worktreeで共有 stash の根拠を独立に確認し、最後の HEAD・base・検証ログを結び付ける。別 Task 間の共有状態はない。

### Task 1: 共通指示へ安全制限を追加する

**Files:**
- Modify: `tools/agent_runner/runner.py:296-303`
- Test: `tools/agent_runner/tests/test_runner.py:645-663`

**Interfaces:**
- Consumes: `run_workflow` が作る `Request.prompt`、既存 `FakeAdapter` の payload、既存 `_scope_lines`。
- Produces: 既存の2行構成を保った共通指示。APIの引数・戻り値は変更しない。

- [ ] **Step 1: RED を追加する。** 既存 `test_write_exceptions_follow_the_work_scope_lines` で実際に捕捉した共通指示に、全 git stash（pop含む）の禁止・worktree共有の理由、pkill -f/killall の禁止・自分が起動したプロセスだけ PID 指定で停止可が含まれることを確認する。F∩S: 文が落ちても通常の実行ではエラーにならず、他セッションの作業消失・無関係のプロセス停止になるため。テストにこの理由を書く。無関係な固定文言・一覧のテストは足さない。既存の例外有無の対照を保ち、caller 本文は受け入れ基準の複数行日本語にする。
- [ ] **Step 2: RED を観測する。** `uv run pytest tools/agent_runner/tests/test_runner.py::test_write_exceptions_follow_the_work_scope_lines -q`。禁止がまだ無いことによる失敗を記録する。
- [ ] **Step 3: 最小実装。** `instructions` の1行目で既存の checkout 制限の直後へ Spec の禁止事項と理由を自然な英語で追加する。文字列リテラルを分割して読みやすくするが生成される改行数は変えない。代替手段も writes と許可範囲に従う。安全制限は write exceptions で解除されないことを明記する。別モジュール・共通定数の新設や既存処理の整理は不要。
- [ ] **Step 4: GREEN・回帰を同期実行。** focused test、`uv run pytest tools/agent_runner/tests .agents/skills/issue-to-pr/tests -q`、`uv run pytest .agents/skills/review-fix-planning/tests/test_run_roles.py .agents/skills/review-verify/tests/test_dispatch.py .agents/skills/pr-review-fix-loop/tests/test_loop_reviewer_protocol.py -q`。各終了0を確認。`git diff --check`。異常時は原因を調べ、範囲外変更が必要なら報告する。
- [ ] **Step 5: commit・報告。** 2ファイルだけを stage して `fix: clarify runner safety instructions for shared resources` で commit。自己レビューし、RED/GREEN、実コマンド・終了コード、所要時間・懸念を結果に含める。サブエージェントを起動しない。push・PR・Issue更新は controller の担当。

## 統合・公開（controller）

Task の受け取り・cleanup後、同じ関連検査と `bash scripts/check-layout.sh` を同期実行。最後の全体レビューと要件照合を行い、文書へ結果を追記して commit。最後の commit 後の clean HEAD で検証記録（argv、終了コード、ログ、code base SHA）を保存する。base/Issue/競合の再確認→Gitleaks→SHA指定push→base/head照合付きPR作成。Actions は無効のまま。PR は Closes #361、マージ後確認項目は現時点なし。ループの finalize 以外でマージしない。

## 実行予算

全体240分（準備20、実装・Task review25、統合検証・全体review・PR25、残りは最大3サイクルのレビュー45分＋短い計画修正）。ledger は `/workspaces/reso-world/tmp/agents/issue-361.vyd2ce_h/budget.jsonl` と同セッションの `sdd/2026-11-10-issue-361-runner-safety/progress.md`。実装の期限はrunner既定90分、レビューは45分。同期 foreground で待つ（tool timeoutなし）、独自の途中停止は宣言しないので予約枠・無進捗の打切りは適用しない。失敗の同原因の再試行は1回まで、failed・安全失敗は停止。実 agent の起動は recon 1回、Task実装1回（retry/修正は各1回まで）、Task review 1回、全体review 1回、ループは指定3人×最大3サイクルと必要な修正だけ。phase境界・失敗直後・50%/100%でcheckpoint。最終検証の記録はループ再利用に必要なのでセッションを残す。

## contingency（代替策）

RED が fixture や出力前提の差なら意味を維持する最小変更を ledger に残す。2行構成が破れる場合は1行目への折り込みを直し、所有範囲外へ広げない。担当の不足文脈は同じ担当に上限内で補足して再依頼。failed は self で引き取らない。base 移動・競合・安全失敗・予算超過・必須ツール失敗は規則どおり停止。縮小候補は重複の検証を省くことだけで、3種類の禁止や安全検査を削らない。
