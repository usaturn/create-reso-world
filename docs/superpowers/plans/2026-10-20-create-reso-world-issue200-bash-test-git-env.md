# Issue #200: bash のテストの直接実行で `GIT_*` を除く Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一時リポジトリを作る 8 本の bash のテストが、直接実行でも外から渡された `GIT_*`（`git rebase --exec` が export する `GIT_DIR`）のリポジトリを書き換えないようにする。

**Architecture:** 8 本それぞれの `set -euo pipefail` の直後に、`.devcontainer/test-run-tests.bash` と同じ `GIT_*` の除去の 1 行を置く。今後のテストの書き方を `.devcontainer/README.md` に 1 文足す。テストは足さず、Issue の再現と同じ形の検証用スクリプトで修正の前後を比べる。

**Tech Stack:** bash 5.2、git

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue200-bash-test-git-env-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/200
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-200-bash-test-git-env`（branch `fix/issue-200-bash-test-git-env`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr #200`。PR の作成まで、マージはしない）
- 実行方式: inline（`superpowers:executing-plans`）。理由は Spec の D-200-5
- 検証用スクリプトとログ: `/workspaces/reso-world/tmp/agents/issue-200.zk8vujd2/`（`repro.bash`・`rebase.bash`。commit しない）

## Global Constraints

- 除去の 1 行は `while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')`（`test-run-tests.bash` と同じ文字列）
- 置く位置は `set -euo pipefail` の直後。テストが自分で `GIT_*` を export する行より前
- テストの対象のスクリプト（`scripts/`・`.devcontainer/` の本体）は変えない
- テストを足さない（Spec の D-200-3）

## Review Focus

- テストが自分で export する `GIT_CONFIG_*`・`GIT_AUTHOR_*` を、除去の行が消さないこと（行の位置）。8 本の通常の実行（`run-tests.bash`）が通ることで確かめる
- `set -u` のもとで、外に `GIT_*` が 1 つも無い（`compgen` が何も出さない）ときも止まらないこと。通常の実行（Claude Code の `GIT_EDITOR` 以外が無い環境）と、`run-tests.bash` 経由（すべて除かれた環境）で確かめる
- `GIT_DIR` を export した直接実行で、8 本が通ること（壊れた環境で FAIL して気づかれないまま、という状態にしない）
- `git rebase --exec` が `GIT_DIR` 以外に export する `GIT_*`（`GIT_REFLOG_ACTION` など）も除かれ、rebase 自体は成功すること
- 読むだけの 3 本（`test-file-modes`・`test-gitignore`・`test-readme`）は変えず、`run-tests.bash` の結果が変わらないこと

## 要件と Task・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. 直接実行で clone が変わらない（修正の前は変わる） | Task 1（実装）・Task 2（統合確認） | `repro.bash` の `summary.tsv` の `changed` が修正の前は `yes`、後はすべて `no` | 修正の前: `d29c93c`、後: Task 1 の commit |
| 2. `GIT_DIR` 付きの直接実行で 8 本が通る | Task 1・Task 2 | `summary.tsv` の `exit` がすべて 0 | 同上 |
| 3. `git rebase --exec` で `core.bare` が書かれない | Task 2 | `rebase.bash` の出力で `rebase exit=0`・`config unchanged`・`main status exit=0` | Task 1 の commit を `HEAD`、`HEAD~1` を upstream にする |
| 4. 入口のテストが基準と同じ | Task 2 | 基準（`d29c93c`）と同じ PASS/FAIL | `README.md` の「テスト」の 3 つのコマンド |
| 5. README の「実環境を変えない」が成り立つ | Task 1（文書）・Task 2 | 1・3 の結果 | 1・3 の結果で代える |

共有する条件は「除去の行を自分の `GIT_*` の export より前に置く」だけで、Task 1 が 8 本をまとめて扱う。統合確認（Task 2）で 8 本を同じ形で実行し、条件単位で確かめる。

## 実行予算

- Issue 全体の能動時間の予算: 120 分（ledger: `/workspaces/reso-world/tmp/agents/issue-200.zk8vujd2/budget.jsonl`）。目安は Spec・Plan 30 分、Task 1 15 分、Task 2 45 分（テストの実行の待ちが大半）、レビューと PR 30 分
- worker は使わない（inline）。長時間の実行（`run-tests.bash`・`repro.bash`・pytest）はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 20 分
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・環境の I/O の停止）は 2 回まで。安全の失敗（実リポジトリの書き換えの疑い）は再試行せず止まる
- checkpoint: Task 1 の後（修正の後の `repro.bash` の結果）と、Task 2 の後（予算の残りを `budget show` で確かめる）
- 縮小・方法変更の候補: 入口のテストが環境の要因で落ちたら、基準（`d29c93c`）の同じ実行と比べて差分だけを判定する

## Task 1: 8 本の冒頭で `GIT_*` を除き、今後の書き方を文書に書く

**Files:**
- Modify: `tests/scripts/test-check-layout.bash`・`tests/scripts/test-new-world.bash`・`tests/scripts/test-resoloop-fork.bash`・`tests/scripts/test-resoloop-meshy.bash`・`tests/scripts/test-scan-before-push.bash`・`tests/scripts/test-superpowers-review-copy.bash`・`.devcontainer/test-herdr-status.bash`・`.devcontainer/test-report-resoloop-skills.bash`（それぞれ `set -euo pipefail` の直後）
- Modify: `.devcontainer/README.md`（「テストの実行」の「実環境を変えない」の文の直後）

**テストの要否:** 足さない（Spec の D-200-3）。代わりに、修正の前後の `repro.bash` の結果と、8 本の通常の実行で確かめる。

- [ ] **Step 1: 修正の前の再現を記録する**

Run: `bash /workspaces/reso-world/tmp/agents/issue-200.zk8vujd2/repro.bash /workspaces/reso-world d29c93c12a817ca45cb8d0eb918a0a07615916ce /workspaces/reso-world/tmp/agents/issue-200.zk8vujd2/before`
Expected: `summary.tsv` の `changed` に `yes` がある（Issue の表と同じ傾向）

- [ ] **Step 2: 8 本に除去の行を置く**

各ファイルの `set -euo pipefail` の直後に、次の 2 行を置く（コメントは `test-run-tests.bash` に合わせる）。

```bash
# 外から渡された GIT_* を除く。linked worktree の git rebase --exec は GIT_DIR を export するので、残すと
# 直接実行したときに一時リポジトリの git init・git -C が、そのリポジトリの設定・index・ブランチを書き換える（#200）
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')
```

- [ ] **Step 3: `.devcontainer/README.md` に 1 文足す**

「テストは一時ディレクトリの `HOME` と、…実環境を変えない。」の直後に、一時リポジトリを作るテストは冒頭で外から渡された `GIT_*` を除くこと（`git rebase --exec` が export する `GIT_DIR` のため。1 本だけ直接実行しても効く）と、新しく足すテストも同じ形にすることを書く。

- [ ] **Step 4: 構文と通常の実行を確かめる**

Run: `for f in <8 本>; do bash -n "$f" || echo "syntax: $f"; done` と `bash .devcontainer/run-tests.bash <8 本>`
Expected: 構文の誤りが無く、`PASS: 8 test(s)`

- [ ] **Step 5: Commit**

```bash
git add <8 本> .devcontainer/README.md
git commit -m "fix: drop inherited GIT_* in bash tests run directly (#200)"
```

## Task 2: 統合確認

**Files:** 無し（結果をこの Plan の「検証の記録」に書いて commit する）

**テストの要否:** 足さない。この Task が検証そのもの。

- [ ] **Step 1: 修正の後の再現**

Run: `bash .../repro.bash /workspaces/reso-world <Task 1 の commit> .../after`
Expected: `summary.tsv` の 8 行すべてが `exit=0`・`changed=no`

- [ ] **Step 2: `git rebase --exec`**

Run: `bash .../rebase.bash /workspaces/reso-world <Task 1 の commit> .../rebase-after HEAD~1 tests/scripts/test-new-world.bash`
Expected: `rebase exit=0`、`exec.txt` に `GIT_DIR=<clone>/.git/worktrees/linked` と `exit=0`、`core.bare=`（空）、`config unchanged`、`main status exit=0`

- [ ] **Step 3: 入口のテスト**

Run（worktree のルート）: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`
Expected: 基準（`d29c93c` の worktree で変更の前に実行した結果）と同じ PASS/FAIL

- [ ] **Step 4: 記録して commit**

下の「検証の記録」に結果を書き、`git commit -m "docs: record the Issue #200 verification (#200)"`

## 検証の記録

（Task 2 の後に書く）
