# Issue #115 実行予算と monitoring-long-tasks の新しい版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** usaturn/agent-workspace の実行予算（`execution-budget.md`・`issue_budget.py`）と、`monitoring-long-tasks` の新しい版（`task_watch.py` を含む）を、移植先の構成に合わせて取り入れる。

**Architecture:** スクリプトとテストは移植元のまま持ち込み、依存はルートの `pyproject.toml` に足す。文書（`execution-budget.md`・`SKILL.md`・`monitoring-runtimes.md`・`AGENTS.md`）は、移植先の `PARENT_ROOT`・検証の入口・ランタイムに合わせて書き換え、PR 修正ループと agent_runner の部分は #116 に回す。

**Tech Stack:** Python 3.14（uv）、pydantic 2、pytest、bash

**Spec:** `docs/superpowers/specs/2026-10-17-create-reso-world-issue115-budget-task-watch-design.md`

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`、Issue #115
- 基準 HEAD: 移植先 `cd602e63e04e51616cd5043dd46b0cbefd8fc60e`（`origin/main`）、移植元 usaturn/agent-workspace `84469b9bb1c35febc6e94e0a8bfa92cf75e7f4c4`
- 状態: draft（文書の内容に対する利用者の明示承認は無い）
- 実行許可: 2026-10-17（JST）、利用者の「#115 に着手せよ。専用 worktree を作成し、途中で止めずに推奨案で PR を出せ」。推奨案での実装、commit、push、PR の作成まで。マージは利用者が行う
- 実行方法: Native（このセッションでインライン実行）。利用者に実行方法を選んでもらう段は、止めずに進める指示に従って省いた。サブエージェントは、Issue の検証が求める writing-skills の行動比較（2 件、読み取り専用）にだけ使う。Spec の builder check は、利用者が質問を省く指示をしたので行わない
- 作業場所: worktree `.worktrees/issue-115-budget-task-watch`、ブランチ `feat/issue-115-budget-task-watch`

## 実行予算

- Issue 全体の能動時間の予算: 240 分。根拠は、同規模の移植（#20 の PR #25 +1,437 行、#22 の PR #33 +1,955 行）が 1 セッションで終わったことと、Task が 7 つであること
- phase の目安: 準備（調査・Spec・Plan）60 分、実装（Task 1〜5）90 分、行動比較（Task 6）30 分、検証（Task 7）30 分、PR（Task 8）30 分
- worker: 行動比較のサブエージェント（Claude Code の `Agent`）は CLI のプロセスではないので `task_watch.py` で包まない。完了通知を待つ。検証のコマンド（`bash .devcontainer/run-tests.bash` など）は宣言があっても止めない対象なので、バックグラウンドで起動して終了コードを待つ
- 再試行の上限: 同じ失敗の再試行は 1 回まで。`test_task_watch_process.py` がこの環境の I/O の停止で時間切れになった場合も 1 回だけ再実行し、2 回目も失敗したら方法を変える（失敗するテストと時間を記録し、テストを変えずに PR 本文に書く）
- checkpoint: phase の境界、予算の 50%（120 分）・100%（240 分）、検証が失敗した直後
- 縮小・切り出し・方法変更の候補: (1) 行動比較の状況を 3 つに絞る、(2) `monitoring-runtimes.md` の最初の表の pi の行を #116 に回す、(3) process のテストが不安定なら、記録して持ち越し候補にする
- ledger: Task 1 で `issue_budget.py` を入れた後、`/workspaces/reso-world/tmp/agents/issue-115.XXXXXX/budget.jsonl` で始める（準備の phase は ledger の外で、Plan の「完了」に壁時計の値を書く）。この worktree の版のスクリプトを使う（`PARENT_ROOT` にはまだ無いため）

## Global Constraints

- 移植元のコードの判定・集計のロジックは変えない（Spec D-3）
- `pr-review`・`review-fix-planning` の本文と `.devcontainer/` は変えない（Spec D-2）
- CI は作らない。private の create-reso-world の Actions は確かめない
- 文言を照合するテストは書かない。スキルの文面は行動比較で確かめる（Spec D-11）
- PR の本文は `Closes #115`（Spec D-13）

## Review Focus

- `task_watch.py` が宣言の無い対象にシグナルを送る → fake worker の `undeclared` のテスト
- `stop` が無関係な PID や caller に送る → 無関係な PID・caller のテスト
- 文書の参照先が無い → `tests/scripts/test-docs.bash --refs`（`test-instructions.bash` から）と `check-layout.sh`
- 打ち切りの対象に検証のコマンドが入る → 行動比較の状況 B

---

### Task 1: 依存と issue_budget.py

**Files:**
- Modify: `pyproject.toml`、`uv.lock`
- Create: `.agents/scripts/issue_budget.py`、`.agents/scripts/tests/test_issue_budget.py`

**テスト:** 要る。ledger の集計と CLI の挙動をコードの実行で確かめる。移植元のテストを持ち込む。

- [x] `pyproject.toml` の `dependencies` を `["pydantic>=2.12,<3"]` にし、`testpaths` に `.agents/scripts` を足す。`uv lock` を実行する
- [x] 移植元の 2 ファイルを写し、docstring の `Issue #598` を `usaturn/agent-workspace#598` にする。`except A, B:` があれば括弧を付ける
- [x] `uv run pytest .agents/scripts -q` が通る
- [x] ledger を始める: `mkdir -p /workspaces/reso-world/tmp/agents` の後に `mktemp -d /workspaces/reso-world/tmp/agents/issue-115.XXXXXX`、`start --budget-minutes 240`
- [x] コミット

### Task 2: task_watch.py とテスト

**Files:**
- Create: `.agents/skills/monitoring-long-tasks/scripts/task_watch.py`、`tests/fake_worker.py`、`tests/test_task_watch_core.py`、`tests/test_task_watch_process.py`

**テスト:** 要る。判定の優先順と、実プロセスの起動・停止を fake worker で確かめる。移植元のテストを持ち込む。

- [x] 移植元の 4 ファイルを写し、Issue 番号の表記を直し、`except A, B:` に括弧を付ける
- [x] `uv run pytest .agents/skills/monitoring-long-tasks -q` が通る。process のテストを続けてもう 1 回実行し、安定していることを確かめる
- [x] コミット

### Task 3: execution-budget.md

**Files:**
- Create: `.agents/execution-budget.md`

**テスト:** 不要（文書だけ）。代わりに Task 6 の行動比較の状況 D と、Task 7 の参照の検査で確かめる。

- [x] 移植元を基に、実行の入口（Spec D-5）、置き場所と片付け（D-5・D-6）、適用範囲（D-10）を書き換える。`#220` など移植元の Issue への参照を外す
- [x] コミット

### Task 4: monitoring-long-tasks の SKILL.md と monitoring-runtimes.md

**Files:**
- Modify: `.agents/skills/monitoring-long-tasks/SKILL.md`、`.agents/monitoring-runtimes.md`

**テスト:** 不要（文書だけ）。代わりに Task 6 の行動比較と、Task 7 の frontmatter・参照の検査で確かめる。

- [x] `SKILL.md` を Spec D-7 のとおり書き換える。`description` は今のまま
- [x] `monitoring-runtimes.md` を Spec D-8 のとおり書き換える
- [x] コミット

### Task 5: AGENTS.md・README.md・ci.yml・移植の記録

**Files:**
- Modify: `AGENTS.md`、`README.md`、`.github/workflows/ci.yml`、`docs/maatlog-poc-porting.md`

**テスト:** 不要（文書と設定値だけ）。代わりに `bash tests/scripts/test-instructions.bash` と `bash tests/scripts/test-docs.bash` で参照先の実在を確かめ、`git diff` を確認する。

- [x] `AGENTS.md` の「SDD 実行運用」を Spec D-9 のとおりにする
- [x] `README.md` の「テスト」と `ci.yml` の `skill-tests` のコマンドに `.agents/scripts` を足す（D-4）
- [x] `docs/maatlog-poc-porting.md` の 4 行に追記する（D-12）
- [x] checkpoint（phase の境界）を ledger に記録する
- [x] コミット

### Task 6: 行動比較（arm B）と記録

**Files:**
- Create: `.agents/skills/monitoring-long-tasks/evals/2026-10-17-issue-115.md`

**テスト:** 不要（評価の記録）。行動比較そのものが文面の検証にあたる。

- [x] 改訂後の `SKILL.md`・`monitoring-runtimes.md`・`execution-budget.md` を scratch の `eval/arm-b/` に写し、arm A と同じ指示文でサブエージェントを 1 件起動する（arm A は準備の phase に実施済み）
- [x] 結果を比べ、arm B が「定めが無い」と答えた点のうち、規則の欠けにあたるものを文書に足す。足したら再比較するかを記録に書く
- [x] 記録を書いてコミット

### Task 7: 検証

**テスト:** 既存と移植したテストの全体を実行する。

- [x] `bash .devcontainer/run-tests.bash`（バックグラウンドで起動して終了コードを待つ）
- [x] `bash scripts/check-layout.sh`
- [x] `uv run pytest tests/skills .agents/skills .agents/scripts`
- [x] `git diff origin/main --stat` と差分の全体を読み、範囲外の変更が無いことを確かめる
- [x] checkpoint を ledger に記録する

### Task 8: 完了の記録と PR

- [x] `issue_budget.py show` の要約を下の「完了」に書き、Spec・Plan の状態は draft のまま（利用者の承認が無いため）にする
- [x] push して PR を作る（本文: 変更の要約、Spec・Plan のパス、検証の結果、行動比較の要約、持ち越し候補、`Closes #115`）
- [x] ledger に `end` を記録し、セッションのディレクトリを片付ける（Spec D-6）

## 完了

2026-10-17（JST）に Task 1〜7 を終え、PR を作った。Spec・Plan の状態は、内容に対する利用者の明示承認が無いので draft のまま。

### 検証

- `bash .devcontainer/run-tests.bash`: `PASS: 30 test(s)`（終了コード 0）
- `bash scripts/check-layout.sh`: `PASS: check-layout`（終了コード 0。worktree にはローカルのワールドが無いので、プロジェクトの検査は対象が無い）
- `uv run pytest tests/skills .agents/skills .agents/scripts`: 528 passed・1 failed（221 秒）。失敗は `pr-review` の `test_pr_review_workspace.py::test_killed_create_reports_its_last_phase_and_leftovers`（process group を kill した直後に、別 session の `git worktree add` が `running` のはずが `vanished`）。`run-tests.bash` と同時に実行して負荷が重なった時間依存の失敗と判断した。`pr-review` はこの変更で触っておらず、そのスクリプトは pydantic も新しいスクリプトも読み込まない。再試行の上限（1 回）の範囲でこのテストだけを再実行し、成功した（7.7 秒）。テストは変えていない
- `uv run pytest .agents/skills/monitoring-long-tasks`: 40 passed（22 秒）。続けて process のテストだけを再実行し、19 passed（20 秒）
- `uv run pytest .agents/scripts`: 15 passed
- 移植したコードと移植元の差分は、Issue 番号の表記と `except (A, B):` の括弧だけ（`diff` で確認）。3.12 の文法で構文解析できることを `ast.parse(..., feature_version=(3, 12))` で確かめた
- 文書に書いた失敗の記録の例（`mark --event failure --failure-class reliability --signature pytest-timeout:test_task_watch_process`）を scratch の ledger で実行し、`show` の `failures` に数えられることを確かめた

### 行動比較

`.agents/skills/monitoring-long-tasks/evals/2026-10-17-issue-115.md` に記録した。4 つの状況すべてで、改訂後の文書だけを読んだサブエージェントが期待どおりに判断した。改訂後が挙げた不足のうち 3 点を文書に足し、再比較はしていない。

### 実行予算の記録

- 準備（調査・Spec・Plan）は ledger の外で、壁時計で約 16 分（20:52 の worktree の更新から、21:08 の ledger の開始まで）。利用者待ちは無い
- ledger（`/workspaces/reso-world/tmp/agents/issue-115.QqGjQF/budget.jsonl`）の検証の checkpoint の時点（21:18）の `show`: 能動時間 578 秒、利用者待ち 0 秒、予算 240 分の 4.0%、期日を過ぎた checkpoint は無い。失敗は上の pytest の 1 件（reliability、1 回。上限には達していない）。安全の失敗は無い
- checkpoint は 3 回（準備の終わり、実装の終わり、検証の終わり）。判断はすべて `continue`
- 予算の 50%・100% には達していない。縮小・切り出し・方法変更の候補は使わなかった
- PR: https://github.com/usaturn/create-reso-world/pull/127 。作成の後に `end` を記録した最終の `show`: 能動時間 653 秒（予算の 4.5%）、利用者待ち 0 秒、状態 `ended`
- セッションのディレクトリには `task_watch.py` の watch が無く（`budget.jsonl` だけ）、上の記録を転記した後に削除した（Spec D-6）
