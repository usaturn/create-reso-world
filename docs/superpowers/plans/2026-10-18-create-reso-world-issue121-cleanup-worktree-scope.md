# Issue #121 repo-cleanup-after-merge の worktree の削除範囲 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（内容の承認は無い。実行許可は Spec の「管理・実行許可」のとおり）
- Spec: `docs/superpowers/specs/2026-10-18-create-reso-world-issue121-cleanup-worktree-scope-design.md`（`98de8e3`）
- 作業場所: `/workspaces/reso-world/.worktrees/issue-121-cleanup-worktree-scope`、branch `fix/issue-121-cleanup-worktree-scope`（`origin/main` `50e4a6b` から pi のセッションが作り、Claude Code が引き継いだ）
- セッションディレクトリ: `/workspaces/reso-world/tmp/agents/issue-121.ry0nizlf`（場面・RED の写し・ledger・ログ。コミットしない）

**Goal:** `repo-cleanup-after-merge` が消す worktree を、マージ済みの branch の worktree とオープン PR に対応しない `/tmp/pr-review-*` だけに限り、範囲を限らない `git worktree prune` をやめる。

**Architecture:** `.agents/skills/repo-cleanup-after-merge/SKILL.md` の手順 1・4・5・11 と Red Flags・言い訳と現実・ガードレールの文面を Spec の D-1〜D-5・D-8 のとおりに変え、`evals/evals.json` に id 17 を足す（D-6）。手順 6〜10 のコードブロックとテストは変えない。

**Tech Stack:** Markdown（SKILL.md）、JSON（evals.json）、writing-skills の行動比較（Claude Code の Agent ツール）

## Global Constraints

- 手順 6（ゲート A）は変えない（#131 の対象）
- `--force` を付けない規則、手順 4 の ignore 対象の確認、ローカル `main` の保持、保護領域の検査、fork の経路の手順は変えない
- 手順 7・8・11 のコードブロックは、テストが実行するので変えない（`tests/test_detached_update.py` の `step_bash` は手順ごとに bash のブロックが 1 つであることを求める）
- 移植元の #651 と関係の無い変更（submodule の `--force`、`refs/pr-review/*`、`tmp/agents/` の報告、手順 7 の dirty の扱い）を持ち込まない
- 文面は移植元に揃え、移植先に無い `.devcontainer/README.md` の節は参照しない
- 実在する worktree の clean・prune・repair・remove・unlock をしない。行動比較はコマンドを実行しない机上の判断で行う

## Review Focus

1. 手順 1 の「オープン PR があれば対象外」と手順 5 の「オープン PR に対応しない `/tmp/pr-review-*` は削除してよい」が食い違わないこと（RED で 2/3 が読み違えた）
2. `status --short --ignored` だけが失敗して 1 つ目が成功した worktree も、clean と確認できていない扱いになること
3. branch を checkout していても、その branch がマージ済みと判定されていない worktree（`locked` でない、`feat/locked` のような PR の無い branch）は削除しないこと
4. `prunable` の worktree の branch（`feat/moved` のようにマージ済み）を手順 8 で消そうとしても、登録が branch を掴んでいるので消えず、それを理由に登録を消そうとしないこと
5. 手順 5 のコードブロックが `git worktree remove <path>` だけになり、`--force` も prune も含まないこと

これらは SKILL.md の文面で決まるので、Task 3 の GREEN の行動比較（`scenario-raw.md` が 1・4 を、`scenario.md` が 2 以外を含む）と差分の確認で確かめる。2 は文面の確認で確かめる。3 は `scenario-raw.md` の `feat/locked` が `locked` の行も持つので確かめられず、ブランチ全体のレビューの後に `scenario-nopr.md` で確かめた（「完了」の節）。

---

### Task 1: SKILL.md の手順と Red Flags・ガードレールを変える

**Files:**
- Modify: `.agents/skills/repo-cleanup-after-merge/SKILL.md`（手順 1: 57〜62 行、手順 4: 87〜100 行、手順 5: 112〜123 行、手順 11: 258〜268 行、Red Flags: 270〜281 行、言い訳と現実: 283〜296 行、ガードレール: 298〜305 行）

**テストの要否:** 不要。SKILL.md の文面だけの変更で、実行して確かめる挙動が無い（AGENTS.md「テストの採用基準」、Spec D-7）。代わりの検証は Task 3 の行動比較と既存のテスト。

- [ ] **Step 1:** 手順 1 の `/tmp/pr-review-*` の行を D-8 の文面に書き換え、オープン PR の列挙の後に D-1 の段落（`prunable`・`locked` の行を持つ worktree は整理対象外、手順 11 で報告。`prunable` と `locked` の意味の 2 行）を足す
- [ ] **Step 2:** 手順 4 に D-2 の段落を足す。clean とするのは 2 つの status がどちらも終了コード 0 で、1 つ目の出力が空のときだけ。0 以外（`cannot change to` なら 128）は削除せず手順 11 で報告
- [ ] **Step 3:** 手順 5 の最初の段落を D-3 の列挙（削除してよい 2 種類と、それ以外は残すこと、別 run の detached な worktree を残す理由）に置き換え、コードブロックを `git worktree remove <path>` の 1 行にし、prune をやめる理由と、`prunable` な worktree に `git worktree remove` を使わない理由の段落を足す。`--force` の段落と「別の判断」の段落は残す
- [ ] **Step 4:** 手順 11 の最後に D-4 の段落を足す（報告する対象と理由、repair・回収は所有者が行い、このスキルでは行わない）
- [ ] **Step 5:** Red Flags に 2 項目を足し、戻る先を「手順 1・4・5・6・9」にする。言い訳と現実に 3 行、ガードレールに 2 項目を足す（D-5）
- [ ] **Step 6:** 確認する

Run: `git -C <worktree> diff --check && grep -n 'worktree prune' .agents/skills/repo-cleanup-after-merge/SKILL.md`
Expected: diff --check は出力なし。grep は「実行しない」と書いた説明・ガードレールの行だけで、コードブロックの中に無い

Run: `uv run pytest .agents/skills/repo-cleanup-after-merge -q`
Expected: 33 passed

- [ ] **Step 7:** commit（`fix(repo-cleanup-after-merge): remove only the selected worktrees`）

### Task 2: eval id 17 を足す

**Files:**
- Modify: `.agents/skills/repo-cleanup-after-merge/evals/evals.json`（末尾の id 16 の後）

**テストの要否:** 不要。eval の一覧の追加で、構造は既存の `test_evals_have_valid_structure_and_existing_files` が確かめる。

- [ ] **Step 1:** id 17、name `keep-unrelated-worktree-registrations` を足す。prompt・expected_output・expectations は移植元の eval 12（`tmp/agents/issue-121.ry0nizlf/upstream-evals.json`）のとおり。`files` は `[]`
- [ ] **Step 2:** 確認する

Run: `jq -e '.evals | map(.id) | (length == (unique | length)) and (.[-1] == 17)' .agents/skills/repo-cleanup-after-merge/evals/evals.json && uv run pytest .agents/skills/repo-cleanup-after-merge -q`
Expected: `true`、33 passed

- [ ] **Step 3:** commit（`test(repo-cleanup-after-merge): add eval for unrelated worktree registrations`）

### Task 3: GREEN の行動比較と全体の検証

**Files:** 変更なし（結果は Spec の「行動比較」に追記して commit する）

- [ ] **Step 1:** 変更後の SKILL.md を `tmp/agents/issue-121.ry0nizlf/green-SKILL.md` に写し、`scenario-raw.md` で 3 体、`scenario.md` で 2 体、RED と同じ指示で新しいサブエージェントに解かせる
Expected: 全員が `detached-other`・`prunable`・`locked`・終了コード 128 の worktree を残し、`done` と `/tmp/pr-review-11-example/worktree` を削除し、`git worktree prune` を実行せず、残した登録を所有者の確認が要るものとして報告する
- [ ] **Step 2:** 新しい言い訳・読み違いが出たら、文面を直して同じ場面で再実行する（REFACTOR。再実行は 1 回まで）
- [ ] **Step 3:** 検証の入口（README の「テスト」、ワールドの行を除く）を実行する

Run: `uv run pytest tests/skills .agents/skills .agents/scripts`
Expected: 失敗が #128 の既知の不安定テスト（`test_abandon_waits_for_a_checkout_that_outlives_create` など）だけ。それ以外が失敗したら systematic-debugging

Run: `bash scripts/check-layout.sh` / `bash .devcontainer/run-tests.bash` / `git diff --check origin/main...HEAD`
Expected: それぞれ終了コード 0（環境要因の失敗は、変更前の HEAD でも同じかを確かめて報告する）

- [ ] **Step 4:** ブランチ全体のレビューを新しいサブエージェントに依頼する（Spec・Plan・差分・Global Constraints を渡す）。致命的な指摘だけを直す
- [ ] **Step 5:** Spec に GREEN の結果、Plan に「完了」を追記して commit

### Task 4: 公開

- [ ] **Step 1:** Issue・PR・branch の競合を調べ直す（issue-to-pr 2 章 6）
- [ ] **Step 2:** `SHA="$(bash scripts/scan-before-push.sh -C <worktree>)" && [ -n "$SHA" ] && git -C <worktree> push origin "${SHA}:refs/heads/fix/issue-121-cleanup-worktree-scope"`
- [ ] **Step 3:** `gh pr create --repo usaturn/create-reso-world --base main --head fix/issue-121-cleanup-worktree-scope`（本文に `Closes #121`、Spec の決定と理由、実行方式と理由、検証と結果、作業時間）。CI は private で停止しているので確かめない

## 実行方式

`superpowers:executing-plans`（inline）。Task 1・2 は同じスキルの 2 ファイルへの逐次の文面変更で、Task 3 の行動比較が Task 1 の文面に依存する。行動比較とブランチ全体のレビューだけを、新しい文脈のサブエージェント（Agent ツール）に任せる。

## 実行予算

- Issue 全体の能動時間: 90 分（pi のセッションが 03:38 に `budget.jsonl` で開始した値を引き継ぐ。Task 4 つ、文面の変更 2 ファイル）。03:54 時点で 16 分使用
- phase の目安: 準備・RED（済み）30 分、実装 15 分、GREEN・検証 30 分、レビュー・PR 15 分
- worker: 行動比較とレビューのサブエージェントは読み取り専用。Claude Code の Agent ツールは task_watch で起動できないので、事前宣言した打ち切りは使わず、完了通知を待つ。1 体の目安は 3 分、10 分を超えたら stall として報告する
- 再試行: 同じ失敗の再試行は 1 回まで（`subagent-empty-result` などの信頼性の失敗）。安全の失敗は全体停止
- checkpoint: phase の境界、予算の 50%（45 分）・100%（90 分）、worker の失敗の直後。100% は停止して報告する
- 縮小・方法変更の候補: GREEN を `scenario-raw.md` の 3 体だけにする。`run-tests.bash` が環境要因で失敗したら、変更前の HEAD との比較で切り分けて報告する。eval の追加を別の PR に切り出す（利用者の許可を得てから）

## Contingency

- 既存のテストが失敗したら: 変更前の HEAD（`50e4a6b`）の baseline（624 件成功、#128 の 1 件失敗、`tmp/agents/issue-121.ry0nizlf/baseline-pytest.log`）と比べ、新しい失敗だけを調べる
- GREEN で失敗が残ったら: 文面を直して 1 回だけ再実行し、なお残れば停止して報告する
- 競合（同じ Issue の PR・予約）が見つかったら: push・PR をせずに停止する

## 完了

状態は draft のまま（内容の承認は無い）。Task 1〜3 を完了し、公開（Task 4）に進む。

- Task 1: `d1eac7a`（SKILL.md）。`uv run pytest .agents/skills/repo-cleanup-after-merge -q` → 33 passed、`git diff --check` → 出力なし、手順 5 のコードブロックは `git worktree remove <path>` だけ
- Task 2: `87003ae`（evals.json の id 17）。id の重複なし・末尾 17、移植元の eval 12 と id 以外一致、33 passed
- Task 3: GREEN 5/5 準拠（Spec の「行動比較」）、`34c7b7c` で記録。検証（HEAD `87003ae`）: `uv run pytest tests/skills .agents/skills .agents/scripts` → 625 passed（EXIT 0）、`bash scripts/check-layout.sh` → PASS（EXIT 0）、`bash .devcontainer/run-tests.bash` → 32/32 PASS（EXIT 0）、`git diff --check origin/main...HEAD` → EXIT 0
- ブランチ全体のレビュー（Opus）: Critical 0・Important 1・Minor 2。Important 1 は `scenario-nopr.md` の確認で失敗が出なかったので文面を変えず、Minor 2 件は見送った（Spec の「ブランチ全体のレビューと追加の確認」）
- `run-tests.bash` は実行前に確かめた。Codex のテストが切り出すのは `install_beforehand.bash` の「Placing the launchers」と「Writing the pi-superagents」の 2 step だけで、次の step で止まり、一時 HOME で実行する。PR #141 が報告した危険は、その PR が最初に持ち込んだ版のもので、`main` の版には当てはまらない

### 判断の記録（Rulings）

- executing-plans の作業ディレクトリ（worktree 内の `.superpowers/sdd/`）を使わず、ledger を `PARENT_ROOT` の `tmp/agents/issue-121.ry0nizlf/sdd-progress.md` に置いた。AGENTS.md の「worktree の中にコミットしないファイルを作らない」に合わせた。誤りの影響は ledger の場所だけ
- TDD のテストを書かず、writing-skills の行動比較で代えた（Spec D-7）。誤りの影響は、手順 5 の回帰テストが無いこと
- レビューの「Declined to judge」の各項目（閉じた未マージ PR の pr-review worktree の削除、実行中の pr-review との競合、手順 6 の固定名、detached な worktree が自動で減らないこと、`gh pr list --limit 20`、`main` を掴む worktree の報告の重複）は変えない。変更前からの挙動か Spec で受け入れ済みで、安全側に倒れる
- Important 1 は文面を変えない（上のとおり）

### 実行予算と時間

- ledger（`tmp/agents/issue-121.ry0nizlf/budget.jsonl`）: 予算 90 分、04:10 時点で能動時間 32 分（使用率 36%）。失敗は pi のセッションの `subagent-empty-result:sp-recon` 2 件（信頼性、上限到達）で、checkpoint で方法変更（Claude Code の Agent ツールへの切り替え）を記録した。安全の失敗は無い
- pi のセッション（03:37〜03:42、約 4 分）: 事前確認、worktree の作成、baseline のテスト、停止と引き継ぎ資料
- Claude Code（03:50〜）: 引き継ぎと競合の再確認 約 4 分、RED と Spec 約 5 分、Plan 約 1 分、実装（Task 1・2）約 2 分、GREEN・検証・レビュー 約 9 分、追加の確認と記録 約 2 分（公開は Task 4）
