# Issue #259 Devin の export の error の欄のテスト Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `test_export_error_fields_override_answer` が、`_export_failure` の `is_error`・`error` の欄の検出をそれぞれ守るようにする。

**Architecture:** テストの入力だけを変える。失敗の step を最終応答の前に挿入し、標準出力が最終応答で終わる状態にして、`response_failed` の理由を失敗の step の欄だけにする。`devin.py` は変えない。

**Tech Stack:** Python 3.14、uv、pytest。

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue259-devin-export-error-fields-test-design.md`

状態: draft。実行許可は利用者の `/issue-to-pr #259 --merge --max-cycles 3`。内容の承認を意味しない。

## Global Constraints

- 変えるのは `tools/agent_runner/tests/adapters/devin/test_adapter.py` の `test_export_error_fields_override_answer` と、この Spec・Plan だけ（Spec の「対象外」）
- テスト・パラメータを足さない（Spec D2）。パラメータ 2 件・標準出力 `'{"ok": true}'`・期待値 `response_failed` は変えない
- 変更は `/workspaces/reso-world/.worktrees/issue-259-devin-export-error-test`（branch `fix/issue-259-devin-export-error-test`）で行う。ログは `/workspaces/reso-world/tmp/agents/issue-259.lr_064lf/` に置く
- 変異の確認は、`git archive` で `mktemp -d` に展開したコピーで行い、worktree の `devin.py` を書き換えない
- Python は `uv` で実行する。ruff はプロジェクトの環境に無いので `uvx ruff check` で代える

## Review Focus

| 観点 | Task と検証 |
| --- | --- |
| `is_error` の検出を外すと、テストが失敗する | Task 2 の Step 1 |
| `error` の検出を外すと、テストが失敗する | Task 2 の Step 1 |
| 変異なしでは通る（何でも失敗にする入力になっていない） | Task 1 の Step 3、Task 2 の Step 1 の対照 |
| `devin.py` の挙動を変えない | Task 2 の Step 2 |

## 実行方式

`implement_task.py check` の結果は `agents: [self]`、`fallback: []`、`self: true`（Spec D4）。変更は 1 ファイルの 1 行とコメントで、Task は 2 つ（変更と統合の確認）、同じファイルを順に扱う。issue-to-pr の 4 章の表のとおり、`superpowers:executing-plans` で、このセッションが順に実装する。subagent-driven-development は、子に渡す文脈が作業そのものより大きくなるので選ばない。最後のブランチ全体のレビューは、新しいコンテキストのサブエージェントに依頼する。

## 実装前の要件照合

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 受け入れ条件 1（変異でそれぞれ失敗する） | 2 | `is_error` を外すと `[failure1]`、`error` を外すと `[failure0]` が 1 failed | 使い捨てのコピーの変異 |
| 受け入れ条件 2（挙動を変えない） | 2 | 差分がテストのファイルと Spec・Plan だけ | `git diff --stat origin/main` |
| 受け入れ条件 3（変異なしで通る） | 1・5 章 | devin の adapter のテストが 29 passed、README の入口が終了コード 0 | pytest と README の「テスト」 |
| 対象外（ほかのテストを変えない） | 1 | 差分がこの関数の中だけ | `git diff origin/main -- tools/` |

共有する入力・状態・順序: 1 つのファイルを同じ担当（self）が順に変えるので、担当の間で共有するものは無い。条件ごとの統合の確認は Task 2 で行う。

## 実行予算

- 全体の能動時間: 240 分。内訳は、準備と調査 15 分、Task 1 が 5 分、Task 2 が 10 分、ブランチ全体のレビューと記録 15 分、push と PR が 10 分、PR 修正ループが最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 15 分）＝ 180 分。根拠: 似た小さなテストの修正（#238）は、ループ 1 サイクルで終わった
- worker: Plan の Task は self が実行するので、`task_watch.py` で宣言する worker は無い。ループのレビュアーは、runner の役割の期限（45 分）に従う
- 再試行の上限: 同じ失敗の再試行は 1 回まで（既定）
- checkpoint: Task 2 の後、PR の作成後、ループの各サイクルの後、予算の 50%（120 分）と 100%
- 縮小・切り出し・方法変更の候補: (1) 挿入で変異が検出できない版があると分かったら、Spec D1 の (c)（`_tool_run_export()` の形）に変える。(2) 同じ形の守りの不足をほかのテストで見つけたら、ここでは直さず、持ち越しの候補として PR 本文に書く
- ledger: `/workspaces/reso-world/tmp/agents/issue-259.lr_064lf/budget.jsonl`

### Task 1: 失敗の step を最終応答の前に挿入する

**Files:**
- Modify: `tools/agent_runner/tests/adapters/devin/test_adapter.py:448-454`（`test_export_error_fields_override_answer` だけ）

**Interfaces:**
- Consumes: 同じファイルの `_export()`（最後の step が `{"source": "agent", "message": '{"ok": true}'}`）と `_collect()`
- Produces: 無し（Task 2 は、この関数の変更後の挙動を確かめる）

**テストの要否:** 既存の S のテストの入力を直すだけで、新しいテストは書かない（Spec D2）。守りの確かめは Task 2 の変異で行う。

- [x] **Step 1: 挿入に変える**

`cast(list[object], export["steps"]).append(failure)` を `cast(list[object], export["steps"]).insert(-1, failure)` にする。

- [x] **Step 2: 理由のコメントを足す**

挿入の直前に 2 行ほどのコメントを足す。内容: 失敗の step を最終応答の前に置くので、標準出力は最終応答で終わり、`response_failed` にできるのは step の `error`・`is_error` の欄だけである（#259）。

- [x] **Step 3: devin の adapter のテストと静的検査**

Run: `uv run --locked pytest -q -p no:cacheprovider tools/agent_runner/tests/adapters/devin`、`uvx ruff check tools/agent_runner/tests/adapters/devin/test_adapter.py`、`git diff --check`

Expected: 29 passed、ruff と diff の検査は終了コード 0。

- [x] **Step 4: Commit**

```bash
git add tools/agent_runner/tests/adapters/devin/test_adapter.py
git commit -m "test: guard the devin export error fields with a step before the answer (#259)"
```

### Task 2: 統合の確認と記録

**Files:**
- Modify: Spec の「経路表」に観測した結果を、この Plan の末尾に「完了」を足す

**Interfaces:**
- Consumes: Task 1 の commit（以下 `T1`）
- Produces: Spec・Plan の記録の commit。最後の全体の検証（issue-to-pr の 5 章）は、この commit の後に行う

**テストの要否:** 新しいテストは書かない。変異は一時的な確認としてコミットしない（`AGENTS.md` の「テストの採用基準」）。

- [x] **Step 1: 変異で守りを確かめる（受け入れ条件 1）**

`T1` を `git archive` で `mktemp -d` に展開したコピーを 3 つ作る。対照（変更なし）、`devin.py` の `_export_failure` から `or step.get("is_error") is True` の行を消したもの、`or step.get("error")` の行を消したもの（どちらも 1 か所だけであることを確かめる）。それぞれで `uv run --locked pytest -q -p no:cacheprovider tools/agent_runner/tests/adapters/devin/test_adapter.py` を実行する。

Expected: 対照は 29 passed。`is_error` を外すと `test_export_error_fields_override_answer[failure1]` だけ、`error` を外すと `[failure0]` だけが失敗し、失敗の内容は `status='success'`。

- [x] **Step 2: 挙動を変えないことを確かめる（受け入れ条件 2）**

Run: `git diff --stat origin/main` と `git diff origin/main -- tools/`

Expected: 変更は `test_adapter.py` と Spec・Plan だけで、`tools/` の差分は `test_export_error_fields_override_answer` の中だけ。

- [x] **Step 3: 記録して commit する**

Spec の「経路表」に観測した結果を書き、この Plan に「完了」の節（Task 別の所要時間、各確認のコマンド・終了コード・ログのパス）を足す。

```bash
git add docs/superpowers/specs/2026-10-25-create-reso-world-issue259-devin-export-error-fields-test-design.md \
  docs/superpowers/plans/2026-10-25-create-reso-world-issue259-devin-export-error-fields-test.md
git commit -m "docs: record issue 259 verification"
```

最後の commit の後、issue-to-pr の 5 章のとおり、README の「テスト」の 3 つの入口で全体を検証し、`finalize.py` の `--checks-file` の形の記録をセッションディレクトリに作る。この記録は Spec・Plan に書かず、PR 本文に書く（記録の commit の後に検証するため）。

## 完了

- Task 1: `0ec4843`（2026-10-24T19:12Z）。`uv run --locked pytest -q -p no:cacheprovider tools/agent_runner/tests/adapters/devin` は 29 passed（`task1-devin.log`）、`uvx ruff check` と `git diff --check` は終了コード 0
- Task 2: 19:12Z〜19:15Z。Step 1・2 の結果は Spec の経路表のとおりで、どれも Expected と一致した（`mutation-t1/`）
- Ruling: SDD の ledger を、worktree の中（`sdd-workspace` の `.superpowers/sdd/`）ではなく、`/workspaces/reso-world/tmp/agents/issue-259.lr_064lf/sdd-ledger.md` に置いた。`AGENTS.md` の「worktree の中に、コミットしないファイルを作らない」に従った
- ログ: `/workspaces/reso-world/tmp/agents/issue-259.lr_064lf/`（`baseline-adapters.log`、`mutation-before/`、`task1-devin.log`、`mutation-t1/`）
- 所要時間（着手 2026-10-24T19:05Z ごろから Task 2 の記録まで）: 約 10 分。内訳は、入力・競合の確認と原因・案の検証 5 分、Spec・Plan 3 分、Task 1 が 1 分、Task 2 が 2 分
