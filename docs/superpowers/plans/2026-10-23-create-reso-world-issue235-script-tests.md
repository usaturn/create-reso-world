# Issue #235: tests/scripts のテストを、新しい採用基準で減らす Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tests/scripts` のテストを `AGENTS.md` の「テストの採用基準」で分類し、F（F∩S を除く）・L・D の余りと、それだけが使っていた補助を消して、S（F∩S を含む）と D の代表だけにする。棚卸しの表と前後の計測を Spec に残す。

**Architecture:** テストのファイルごとに、守りごとの代表の 1 件だけを残す。bash のテストは場面（`# N.` の見出し）、Python は関数を単位にする。残した守りのうち重さが高く代表に絞ったものは、使い捨てのコピーで守る処理を壊し、残したテストが失敗することを確かめる。`scripts/` のコードは変えない。

**Tech Stack:** bash（`tests/scripts/test-*.bash`）、Python の unittest（`tests/scripts/test_superpowers_*.py`）、gitleaks（`test-scan-before-push.bash`）

**Spec:** `docs/superpowers/specs/2026-10-23-create-reso-world-issue235-script-tests-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/235（親 #228、子のキー `script-tests`）
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-235-script-tests`（branch `feat/issue-235-script-tests`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr #235 --merge`。PR の作成後に PR 修正ループを回し、修正不要ならループの `finalize.py` がマージする）
- 実行方式: inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true で、各ファイルの整理は読み取った分類を使って順に行うので、並行できず、文脈を渡す手間が上回る。独立したレビューは PR 修正ループのレビュアーが行う
- 検証のログ: `/workspaces/reso-world/tmp/agents/issue-235.9hro_7qe/`（commit しない。worktree の中には置かない）。以下 `$SESSION`
- 基準: `origin/main` の `481a047`

## Global Constraints

- 変えるのは `tests/scripts/` のテストと補助、この子の Spec・Plan だけ。`scripts/` のコード、Meshy の 2 ファイル、`test-superpowers-python.bash`、`.devcontainer/`、`AGENTS.md`、`.gitleaks.toml` は変えない
- F∩S の値（ペルソナ節の SHA、`CLAUDE.md` の 1 行目、取り込んだ過去文書の SHA の一覧、gitignore の 3 つの一覧）は変えない
- 拒否を確かめるテストには、正しく通る例を少なくとも 1 件残す
- テストは足さない（残したテストの整理だけ）。確かめは、残したテストの実行、変異の確認、計測で行う
- `AGENTS.md` の「日本語表現」で避ける語（契約・原子的・製品・着地・正本・巡・席・実行器）を使わない

## 実行予算

- Issue 全体の能動時間の予算: 300 分（開始 2026-10-23 01:00 JST ごろ）。根拠は、読む量（テスト 5,725 行のうち Meshy を除く 3,293 行）と、PR 修正ループ（最大 3 サイクル）
- phase の目安: 読む・分類 60 分、整理 90 分、変異の確認 20 分、Spec・Plan 30 分、全体の検証 30 分、PR 10 分、PR 修正ループは残り（最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 30 分）のうち、予算に収まる範囲）
- worker は使わない（inline）。長時間の実行（`run-tests.bash`・pytest 全体）はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 30 分
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・負荷による期限切れ。#218）は 1 回まで。安全の失敗（親の checkout や他の worktree の書き換えの疑い）は再試行せず止まる
- checkpoint: 整理の後、変異の確認の後、全体の検証の後、PR の作成の後、ループの各サイクルの後
- 縮小・方法変更の候補: 全体の検証が負荷で落ちたら（#218）、落ちたテストだけを単独で再実行し、基準（`481a047`）の同じテストと比べて、この変更による失敗かを判定する。重くて確かめにくい整理は、Spec の「迷い」に移し、残す

## 要件と Task・検証の対応

| Issue の受け入れ・範囲 | Task | 検証 |
| --- | --- | --- |
| Spec に棚卸しの表がある | Task 1・6 | Spec の表が全てのテストの場面・関数を含むことを、前のファイルの一覧と照合する |
| F・L・D の余り・撤去した経路のテストと、それだけが使っていた補助が消えている | Task 2〜5 | `git diff --stat`、使う側の無い補助（`lib/path.bash`）の `git grep` |
| 重さが高の守りの代表を、壊した使い捨てのコピーで確かめる | Task 7 | 13 件の変異で、残したテストが失敗する |
| 残したテストが通る | Task 8 | `bash .devcontainer/run-tests.bash tests/scripts/*.bash`、README の「テスト」の入口 |
| 件数・行数の前後を測る | Task 8 | Issue の「検証」の計測コマンド |
| 範囲外を変えない | Task 8 | `git diff --name-only origin/main` が `tests/scripts/` と `docs/superpowers/` の中だけ |

## Task 1: 棚卸し

**Files:** 変更なし（読むだけ）

**テストの要否:** 不要（読み取り）。結果は Task 6 の Spec の表にする。

- [x] **Step 1:** `tests/scripts/` の全てのテスト（bash 14 本、Python 61 件）を読み、AGENTS.md の分類で F・F∩S・L・S・D・迷いに分ける
- [x] **Step 2:** 消すテストだけが使っていた補助（`lib/path.bash`）、参照元（`git grep`）を確かめる。`.devcontainer/test-run-tests.bash` が `tests/scripts/test-check-layout.bash` の存在を確かめるので、このファイルは残す

## Task 2: 小さなファイルの整理

**Files:**
- Delete: `tests/scripts/test-blender-system-python.bash`・`test-ci.bash`・`test-docs.bash`・`test-file-modes.bash`・`test-superpowers-review-copy.bash`
- Modify: `tests/scripts/test-instructions.bash`（参照実在の検査を外す）、`tests/scripts/test-gitignore.bash`（4 つ目の検査を外す）

**テストの要否:** 書かない。残したテストを実行して通ることを確かめる。

- [x] **Step 1:** 5 本を `git rm` する。`test-instructions.bash` は `bash tests/scripts/test-docs.bash --refs ...` の行とコメントを消す。`test-gitignore.bash` は追跡中かつ ignore の組の検査を消す（3 つの一覧は変えない）
- [x] **Step 2:** `bash tests/scripts/test-instructions.bash` と `bash tests/scripts/test-gitignore.bash` が通る

## Task 3: check-layout と new-world の組み直し

**Files:**
- Modify: `tests/scripts/test-check-layout.bash`（53 場面 → 12 場面）、`tests/scripts/test-new-world.bash`（47 場面 → 12 場面）
- Delete: `tests/scripts/lib/path.bash`（使う側が無くなる）

**テストの要否:** 書かない。残す場面は Spec の棚卸しの表のとおり。

- [x] **Step 1:** `test-check-layout.bash` を、守りごとの代表（追跡禁止ファイル、symlink、追跡中の ignore、スキルのリンク 3 種、プロジェクトのレイアウト 3 種、従来位置、作業領域の追跡、mount、assets、壊れた設定）と通る例に組み直す。モックの resoloop は `SKILL_SYNC_CONFLICT` だけにする
- [x] **Step 2:** `test-new-world.bash` を、名前の検査、新規作成、既存の非上書き、冪等、前提の欠落、対象の曖昧さ、JSON と wrapper の保持と競合、symlink の先に書かないことに組み直す。モックは resoloop だけにする（`uv` を使う場面は消えた）
- [x] **Step 3:** 2 本が通る。`lib/path.bash` を消し、`git grep path_without` が 0 件

## Task 4: resoloop-fork・resoloop-meshy・scan-before-push

**Files:**
- Modify: `tests/scripts/test-resoloop-fork.bash`（28 場面 → 9 場面）、`tests/scripts/test-resoloop-meshy.bash`（9 場面 → 3 場面）、`tests/scripts/test-scan-before-push.bash`（D と L の場面を消す）

**テストの要否:** 書かない。`test-resoloop-fork.bash` は、前の場面の状態に頼っていたので、場面の順序を保ったまま、使う状態だけを組み直す。

- [x] **Step 1:** `test-resoloop-fork.bash` を組み直す（モックの dotnet は build・pack・tool update・list だけ）
- [x] **Step 2:** `test-resoloop-meshy.bash` を 3 場面にする。`test-scan-before-push.bash` は、D（allowlist の無作為な値 2 件、壊れた `.gitleaksignore` の symlink）と L（`--base` の remote 名・usage・未知の引数）、通ると気付ける側の場面を消す
- [x] **Step 3:** 3 本が通る

## Task 5: Python のテスト

**Files:**
- Modify: `tests/scripts/test_superpowers_context.py`（35 件 → 21 件）、`tests/scripts/test_superpowers_review_copy.py`（23 件 → 10 件）、`tests/scripts/test_superpowers_lifecycle.py`（3 件 → 2 件）

**テストの要否:** 書かない。

- [x] **Step 1:** Spec の表のとおり、関数を消し、残す関数の値の組み合わせを代表にする（未使用になった定数・import を消す）
- [x] **Step 2:** `uv run --no-project python -m unittest discover -s tests/scripts -p 'test_superpowers_*.py'` が通る（33 件）

## Task 6: Spec の棚卸しの表

**Files:**
- Create: `docs/superpowers/specs/2026-10-23-create-reso-world-issue235-script-tests-design.md`、この Plan

- [x] **Step 1:** 前のファイルの全てのテストを、分類・理由・扱いで表にする（同じ理由のテストは群で 1 行）
- [x] **Step 2:** 表の「残す」と実際に残ったテストが一致することを、`grep -c '    def test_'`・場面の見出しで照合する

## Task 7: 変異の確認

**Files:** 変更なし（`mktemp -d` の使い捨てのコピーだけ。終了時に削除）

**テストの要否:** 不要（確認作業）。結果は Spec の「変異の確認」に書く。

- [x] **Step 1:** 追跡するファイルだけを写した使い捨てのコピーで、守る処理を 13 通りに壊し、残したテストが失敗することを確かめる（Spec の表）
- [x] **Step 2:** 失敗しなかった変異があれば、テストを直してやり直す（今回は 13 件とも失敗した）

## Task 8: 統合確認

**Files:** 変更なし

- [ ] **Step 1:** 領域のテスト: `bash .devcontainer/run-tests.bash tests/scripts/*.bash`
- [ ] **Step 2:** 全体: `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`
- [ ] **Step 3:** 計測（コミット済みの状態で、Issue の「検証」の 3 つのコマンド）
- [ ] **Step 4:** `git diff --name-only origin/main` が `tests/scripts/` と `docs/superpowers/` の中だけ。`git diff --check`
- [ ] **Step 5:** 最後のブランチ全体のレビュー（PR 修正ループのレビュアー）

## PR と PR 修正ループ（issue-to-pr の 5 章）

- push の前に `scripts/scan-before-push.sh` で検査し、検査した SHA を push する。PR の作成（`Closes #235`）の後、`--merge` により PR 修正ループを回す
- PR の本文に、計測の前後、棚卸しの要約、変異の確認、実行方式、検証の結果を書く

## 検証の記録

### Task 2〜5（整理）

- 整理した各ファイルを単独で実行し、通ることを確かめた（`test-check-layout.bash` 3 秒、`test-new-world.bash` 4 秒、`test-resoloop-fork.bash` 1 秒、`test-scan-before-push.bash` 15 秒、`test_superpowers_*.py` 33 件）
- 実装を先に行い、Spec・Plan を同じ branch の commit として後から書いた。issue-to-pr の「Spec → Plan → 実装」の順に反するので、ここに記録する。Spec の分類は、実装の前に読んで決めたものを表にしたもので、実装で変えた分類は無い（`test-resoloop-fork.bash` の `HEAD` の解決だけは、表を書くときに D としかけたが、迷うものは残す基準に従い、場面を戻した）

### Task 7（変異の確認）

- Spec の「変異の確認」の 13 件が全て失敗した（使い捨てのコピーは終了時に削除した）
