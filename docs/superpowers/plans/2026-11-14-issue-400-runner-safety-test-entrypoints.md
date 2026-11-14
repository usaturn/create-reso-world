# Issue #400: runner の安全指示にテスト・検証の入口の許可を明記する Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** runner の安全指示に、リポジトリのテスト・検証の入口は内部で python3 を使っても実行してよいことを明記し、既存の F∩S テストで許可と禁止の両方を確認する。

**Architecture:** `tools/agent_runner/runner.py` の先頭の安全指示 1 行に許可文を連結し、行・段落構造を変えない。`tools/agent_runner/tests/test_runner.py` の既存 F∩S テストに許可と禁止の assertion を足す。新しい恒久テストは作らない。

**Tech Stack:** Python、pytest、uv。新規依存なし。

**Spec:** `docs/superpowers/specs/2026-11-14-issue-400-runner-safety-test-entrypoints-design.md`（状態 `draft`、issue-to-pr の実行委任。内容の承認とは扱わない）

## Global Constraints

- コードの変更は `tools/agent_runner/runner.py` と `tools/agent_runner/tests/test_runner.py` だけ。
- 安全指示は先頭の 1 行のまま。生成する文字列に `\n`・`\n\n` を足さない。`writes=...` の行、例外の見出しと一覧、空行、caller 本文の順序を変えない。
- `.devcontainer/test-*.bash`、`exception_lines()`、`.agents/skills/review-fix-planning/tests/test_run_roles.py` は編集しない。
- プロンプト全文・段落構造だけを固定する新しいテストを追加しない。`writes=true` は一時プローブで確認する。
- 既存の安全指示（git stash・pkill -f・killall・PID 所有）と、テスト・検証の入口以外の python・python3 の禁止を弱めない。
- worktree `/workspaces/reso-world/.worktrees/issue-400-test-entrypoints`、branch `feat/issue-400-test-entrypoints`、base `950186cdac1ff52f42f8b212235f06074e2c84d6`。
- `--merge` の指定は無いため、PR のマージは行わない。PR を作った後にブランチ全体のレビューを行い、結果を PR に記録する。
- Issue #400 の完了条件は main へのマージのため、マージ前にクローズしない。関連 Issue #415 には結合検証の結果をコメントする。

## 受け入れ基準（実装・Task レビュー双方へ同じ本文を渡す）

- **動作環境:** Dev Container（Ubuntu 26.04 LTS）のリポジトリルート。`uv` と pytest が使えること。
- **実入力:** runner が `writes=true` と `writes=false` で生成する依頼文（書き込み例外あり・なしの両方）。許可の対象として `bash .devcontainer/run-tests.bash`、`bash .devcontainer/test-herdr-migration.bash`、`bash .devcontainer/test-cleanup-workspace.bash`、`bash scripts/check-layout.sh` を想定する。
- **防御範囲:** 許可するのはリポジトリが定めたテスト・検証の入口の実行だけ。担当自身による `python`・`python3` の直接起動、`python -` への heredoc、禁止回避のための任意のラッパーは対象外とし、禁止のままにする。
- runner の依頼文に、テスト・検証の入口は内部で python3 を使っても実行してよいこと、python・python3 の直接起動と heredoc は禁止のままであることが書かれる。
- `writes=true`・`writes=false` のどちらでも同じ許可・禁止の指示になる。write exceptions で外せない点は変えない。
- 安全指示の 1 行目・`writes=...` の行・例外の見出しと一覧・空行・caller 本文の順序を維持し、安全指示の途中に `\n`・`\n\n` を入れない。
- 既存の F∩S テストを更新し、許可と禁止の両方を確認する。
- `uv run --project . --locked pytest tools/agent_runner -q` が通る。
- 実装 worktree のルートで `uv run --project . --locked pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q` も通る。両変更が揃った状態で確認する。偽の adapter のみを使用し、有料モデルは起動しない。

## Review Focus

1. 許可文が安全指示の先頭 1 行にあり、python・python3 の直接起動と heredoc の禁止文が残っているか。
2. 許可の対象がリポジトリのテスト・検証の入口（3 つの例示と内部 python3 の利用）に限定され、任意のラッパーを許していないか。
3. write exceptions の有無で先頭行が変わらず、例外の見出し・一覧・caller 本文の構造が保たれているか。
4. `writes=true` でも同じ先頭行になるか（一時プローブ）。
5. 既存の F∩S テストの禁止 assertion を弱めていないか。追加した assertion が文言の意味（禁止と許可）を確認しているか。
6. 変更ファイルが 2 つに限定され、`.devcontainer/` と #415 のテストを変更していないか。

## Task 1: 安全指示と F∩S テストの更新（controller・self）

**Files:**
- Modify `tools/agent_runner/runner.py`（安全指示の先頭 1 行）
- Modify `tools/agent_runner/tests/test_runner.py`（`test_write_exceptions_follow_the_work_scope_lines`）

**Interfaces:** `runner.py` の `instructions` は、1 行目の f-string 連結に許可文を足す。2 行目以降は変更しない。テストは既存の `_scope_lines`・`scope`・`lines` を使い、先頭行の小文字化した `safety` に対して許可と禁止の部分文字列を確認する。

**テスト要否:** 既存の F∩S テスト 1 件を更新する。許可文が落ちると担当がリポジトリのテスト入口を実行せず、より狭い確認のまま成果が返る（S）。禁止文が落ちると uv 環境外の Python 実行や heredoc を止められない（S）。新しいテストは、プロンプト全文・段落構造の固定（F）または同じ守りの別組み合わせ（D）になるため追加しない。`writes=true` は一時プローブで確認する。

- [x] **Step 1: ベースラインの記録。** worktree のルートで `uv run --project . --locked pytest tools/agent_runner -q` と `uv run --project . --locked pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q` を実行し、終了コードと件数を SESSION のログに記録する。
- [x] **Step 2: runner.py の文言更新。** 禁止文の直後、末尾の「These safety restrictions apply whether writes=true or writes=false and are not lifted by write exceptions.」の前に、次を同じ 1 行の文字列連結として足す。物理行は分けてよいが、生成文字列に改行を足さない。

  `You may run the repository's test and verification entry points, such as bash .devcontainer/run-tests.bash, bash .devcontainer/test-*.bash, and bash scripts/check-layout.sh, even when they use python3 internally; this does not permit wrapping python or python3 in a command of your own.`

- [x] **Step 3: F∩S テストの更新。** `test_write_exceptions_follow_the_work_scope_lines` の既存ループに、小文字の `safety` に対して次を確認する assertion と、防ぐ損害のコメントを足す。
  - 許可: `repository's test and verification entry points`、`bash .devcontainer/run-tests.bash`、`bash .devcontainer/test-*.bash`、`bash scripts/check-layout.sh`、`even when they use python3 internally`、`does not permit wrapping python or python3`。
  - 禁止の維持: `do not run python or python3 directly`、`do not pass a heredoc to python -`。
- [x] **Step 4: 対象テストの GREEN と一時プローブ。** `uv run --project . --locked pytest tools/agent_runner/tests/test_runner.py -q -k write_exceptions_follow_the_work_scope_lines` を実行する。続けて `$SESSION/writes_true_probe.py` に、`pytest_plugins = ("tools.agent_runner.tests.test_runner", "tools.test_support.plugin")` と `@pytest.mark.usefixtures("outside_runner")` を付け、既存の `configuration()` の `inspect` 役割を `model_copy(update={"writes": True})` に置き換えた config で `run_workflow` を実行する一時テストを置く。`_scope_lines` で先頭行を取り出し、Step 3 と同じ許可・禁止の部分文字列を含むことを確認する。worktree のルートから `uv run --project . --locked pytest "$SESSION/writes_true_probe.py" -q` を実行する。一時ファイルはコミットせず、worktree に置かない。
- [x] **Step 5: commit。** 2 ファイルだけを stage し、`fix: allow repository test entry points in runner safety instruction` で commit する。`git diff --check` と `git status --porcelain` を確認する。

## Task 2: 最終検証・ブランチ全体レビュー・公開（controller）

**Files:** コードは変更しない。必要なら Spec・Plan の実施記録だけ更新する。

**テスト要否:** 追加なし。既存テスト、リポジトリの入口（check-layout・全 pytest）、ビルド・解析の実行で確かめる。ブランチ全体のレビューは `superpowers:requesting-code-review` に従い、読み取り専用の別 context で行う。

- [x] **Step 1: 最終検証。** 最後の commit 後の clean な HEAD で、base の再確認後に次を実行し、argv・終了コード・ログのパスを SESSION に記録する。
  - `uv run --project . --locked pytest tools/agent_runner -q`
  - `uv run --project . --locked pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q`
  - `uv run --project . --locked pytest tests/skills .agents/skills .agents/scripts tools -q`（README の全 pytest）
  - `bash scripts/check-layout.sh`
  - `git diff --check` と `git status --porcelain`（空であること）
- [x] **Step 2: ブランチ全体レビュー。** `superpowers:requesting-code-review` に従い、base からの差分（2 ファイル + Spec・Plan）を読み取り専用のレビュアーに渡す。指摘は採否を決めて記録し、致命的な指摘だけを修正して再検証する。レビューは PR に記録する。
- [ ] **Step 3: 公開。** Issue の状態・競合・base を再確認し、`scripts/scan-before-push.sh` で検査した commit だけを push し、PR を作成する。PR 本文に変更概要、Spec の決定と理由、実行方式、検証結果、レビュー結果、作業時間を書く。Issue は `Closes #400` とせず `Refs #400` とし（マージはこの run では行わない）、残項目を書く。
- [ ] **Step 4: Issue の更新。** Issue #400 に、実装・検証・PR の結果と残項目（マージ、マージ後のレビュー修正 run 3 回の評価）をコメントする。Issue #415 に、#400 の変更と #415 のテストを両方含む結合検証の結果をコメントする。Issue #400 は完了条件が main へのマージのためクローズせず、その理由を報告する。

## 要件・原因・検証の対応

- 原因（安全指示の解釈のばらつき）: Task 1 Step 2 が先頭行に許可を明記し、Step 3 が許可と禁止の両方を F∩S で固定する。
- 入力→保存→検証: runner が生成するプロンプト（実入力）→ `_scope_lines` で先頭行を分離→許可・禁止の部分文字列と構造（例外の有無）を照合する。`exception_lines()` は Task 2 Step 1 の test_run_roles で実プロンプトから例外一覧を抽出できることを確認する。
- 防御範囲: 許可はリポジトリの入口に限定し、任意ラッパーを許さない assertion を置く。`.devcontainer/` の python3 利用自体は変更しない。
- 未確認にすること: `writes=true` の恒久テストは追加せず、一時プローブの結果だけを記録する。マージ後の実レビュー run 3 回の評価はこの run の対象外。

## 実行予算

- 能動時間の上限: 120 分（利用者待ちを除く）。Spec/Plan 30 分、実装 15 分、最終検証 30 分、ブランチ全体レビュー 20 分、PR・Issue 更新 15 分、予備 10 分を目安にする。
- タイムアウト: 各 pytest は 1 回 15 分、全 pytest は 20 分、check-layout は 5 分。超えたら監視スキルに従い、生存と進捗を確認する。
- 再試行: テスト失敗の修正は 2 回まで。同じ失敗が続く場合は systematic-debugging で原因を調べ、それでも解消しなければ停止する。安全検査を弱める変更はしない。
- checkpoint: Spec/Plan 完了時、Task 1 の commit 後、最終検証の後、PR 作成後に、実績と残作業を SESSION の ledger に記録する。
- ledger: `/workspaces/reso-world/tmp/agents/issue-400.2wum565u/sdd/2026-11-14-issue-400-runner-safety-test-entrypoints/progress.md`。依頼ログ・検証ログは同じ SESSION に置く。
- 縮小・切り出し: 全 pytest が環境要因で完走できない場合は、失敗の原因が今回の変更と無関係であることを個別ログで示し、Issue の必須 2 コマンドと check-layout の結果を報告する。無関係を確かめられない場合は停止する。

## contingency（代替策）

- 最初の RED で実出力・API の前提が異なる場合は、仕様の意味を保つ最小修正（文言の分割位置・assertion の対象）を ledger に残して続ける。段落構造や禁止の意味を変える場合は、#415 の結合方針を先に更新せずに進めない。
- 既存テストが想定外に失敗した場合は `systematic-debugging` で、変更前との差分・プロンプトの実出力・`exception_lines()` の挙動を順に確認する。テストを緩める・削る修正はしない。
- 全 pytest で今回の変更と無関係な時間依存の失敗が出た場合は、#415 の安定化後も残る負荷依存かを切り分ける。同じ失敗が再現するなら、対象テストと変更前の挙動を比較し、今回の範囲で直せるか判断する。直せない場合は停止して報告する。
- `writes=true` の一時プローブが作れない場合は、先頭行が `role.writes` を参照しない実装であることをコードと差分で確認し、未実施の確認として報告する。
- 予算を超える場合は、追加の反復を増やさず、未実施事項・残項目・必要な予算を記録して停止する。

## 実施記録

- ベースライン（変更前）: runner 305 passed、roles 18 passed、いずれも終了 0。
- Task 1: TDD の順序にするため、Plan の Step 3（テストの assertion 追加）を先に実行した。RED は許可文の不在による assertion 失敗（1 failed、終了 1）。次に Step 2（runner.py の文言）を実装し、対象テスト 1 passed、runner 305 passed、roles 18 passed、`git diff --check` 終了 0 を確認した。
- `writes=true` の一時プローブ: `writes=False` と `writes=True` の先頭行が同じで、許可・禁止の部分文字列を含むことを確認した（1 passed、終了 0）。プローブは `$SESSION/writes_true_probe.py` に置き、コミットしていない。
- Task 1 の commit: `6776160e`。Spec は `4327e994`、Plan は `9ae0de67`。実施記録の commit は `7cc48d96`。
- 最終検証（HEAD `7cc48d96`、clean）: `uv run --project . --locked pytest tests/skills .agents/skills .agents/scripts tools -q` は 1561 passed（889.68 秒、終了 0）。`bash scripts/check-layout.sh` は終了 0。`uv run --project . --locked pytest tools/agent_runner -q` は 305 passed、`uv run --project . --locked pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q` は 18 passed、`git diff --check` は終了 0。ログは `/workspaces/reso-world/tmp/agents/issue-400.2wum565u/logs/final-verify-1.log`。
- ブランチ全体レビュー（`950186cd..7cc48d96`、読み取り専用の別 context、モデル opus）: Critical 0、Important 0、Minor 3、判定 Yes（Ready to merge）。レビュアーも runner 305 passed、roles 18 passed、review-verify 64 passed、diff check 0 を確認した。Minor 3 件（ラッパー禁止 assertion の後半未固定、`use uv run for Python` 未固定、Plan のチェックボックス）は、いずれも任意の改善として ledger に記録し、今回は対応しない。
- 最終の文書 commit の後に、必須 2 コマンド（runner・roles）を再実行して結果を確定する。全 pytest・check-layout はコード変更のない文書追記のみのため、上の `7cc48d96` の結果を維持する。
- 最終検証・ブランチ全体レビュー・PR・Issue 更新は Task 2 で記録する。
