# Issue #145 push の refspec を `${SHA:?}` にする Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（内容の承認は無い。実行許可は Spec の「管理・実行許可」のとおり）
- Spec: `docs/superpowers/specs/2026-10-18-create-reso-world-issue145-push-refspec-guard-design.md`（`be32831`）
- 作業場所: `/workspaces/reso-world/.worktrees/issue-145-push-refspec-guard`、branch `fix/issue-145-push-refspec-guard`（`origin/main` `2deb900` から作成）
- セッションディレクトリ: `/workspaces/reso-world/tmp/agents/issue-145.5u0itijo`（再現の script とログ。コミットしない）

**Goal:** push の手順の refspec を `"${SHA:?}:refs/heads/..."` にして、SHA が空のときに remote の branch を消さないようにする。

**Architecture:** Spec の 5 か所の refspec に `:?` を足し、`AGENTS.md` に注意を 1 文足し、zsh の注意を `${SHA:?}` の形に合わせる。検査のスクリプトの動作は変えない。

**Tech Stack:** Markdown、bash のコメント、bash 5.3・zsh 5.9 での再現

## Global Constraints

- 対象は Spec の 5 か所だけ。`.agents/skills/issue-to-pr/evals/scenarios.json`、過去の Spec・Plan、claim ref の削除、`scripts/resoloop-fork.sh` は変えない
- `[ -n "$SHA" ]` は残す
- `AGENTS.md` に足す文: 「SHA が空だと refspec が branch の削除になるので、呼び出しを分けるときも `:?` を外さない。」
- 再現は一時ディレクトリの bare repo だけで行い、実在の remote に push しない

## Review Focus

1. zsh で `"${SHA:?}:refs/heads/<branch>"` が、SHA があるときに正しい refspec になること（波括弧の外の `:r` は修飾子にならない）→ Task 2 の場面 D を `zsh -f` でも実行する
2. SHA が空文字列（未設定ではない）のときも止まること → Task 2 の場面 B
3. 5 か所の形が互いに、また issue-to-pr の 5 章と食い違わないこと → Task 1 の Step 2 の grep

---

### Task 1: 5 か所の refspec と注意を直す

**Files:**
- Modify: `AGENTS.md:151`
- Modify: `.agents/skills/review-fix-planning/SKILL.md:316`
- Modify: `docs/resoloop-fork-workflow.md:80`
- Modify: `docs/resoloop-meshy-workflow.md:44`
- Modify: `scripts/scan-before-push.sh:4-5`（コメント）

**テストの要否:** 不要。文書・SKILL.md の文面とコメントだけの変更（`AGENTS.md` の「テストの採用基準」、Spec の決定記録）。代わりの検証は Task 2 の再現と既存のテスト。

- [ ] **Step 1:** 5 か所の `"${SHA}:refs/heads/` を `"${SHA:?}:refs/heads/` にする。`AGENTS.md` と `scripts/scan-before-push.sh` の zsh の注意を「`${SHA:?}` と波括弧で書く」にし、`AGENTS.md` の注意の後に Global Constraints の 1 文を足す
- [ ] **Step 2:** 確かめる

Run: `grep -rn --exclude-dir=.git -F '${SHA}:refs/heads' . | grep -v '^./docs/superpowers/' ; grep -rn --exclude-dir=.git -F 'SHA:?}:refs/heads' . | grep -v '^./docs/superpowers/'`
Expected: 1 つ目は `.agents/skills/issue-to-pr/evals/scenarios.json:108` だけ。2 つ目は 5 か所と issue-to-pr の 2 行

Run: `bash -n scripts/scan-before-push.sh && git diff --check`
Expected: 出力なし、終了コード 0

- [ ] **Step 3:** commit（`fix: guard push refspecs against an empty SHA`）

### Task 2: 再現と全体の検証

**Files:** 変更なし（結果は Spec の「検証の結果」と Plan の「完了」に追記して commit する）

- [ ] **Step 1:** セッションディレクトリに再現の script を置き、Spec の場面 A〜D を bash と `zsh -f` で実行する。場面 D は Task 1 の後の `scripts/scan-before-push.sh` を使い、作業用の clone の `origin/main` を bare repo の `main` にする

Expected: Spec の「検証と受け入れ条件」の表のとおり。A・B は push の前に止まり `fix/x` が残る、C は `fix/x` が消える、D は終了コード 0 で `fix/x` が HEAD と同じ

- [ ] **Step 2:** `README.md` の「テスト」のコマンド（ワールドの行を除く）を実行する

Run: `bash .devcontainer/run-tests.bash` / `bash scripts/check-layout.sh` / `uv run pytest tests/skills .agents/skills .agents/scripts`
Expected: それぞれ終了コード 0。失敗したら変更前の `origin/main` でも同じかを確かめ、#128 の既知の不安定テストと区別する

- [ ] **Step 3:** ブランチ全体のレビューを新しいサブエージェントに依頼する（Spec・Plan・`git diff origin/main...HEAD` を渡す）。致命的な指摘だけを直す
- [ ] **Step 4:** Spec の「検証の結果」と Plan の「完了」を追記して commit（`docs: record issue 145 verification`）

### Task 3: 公開

- [ ] **Step 1:** Issue・PR・branch の競合を調べ直す（issue-to-pr 2 章 6）
- [ ] **Step 2:** `SHA="$(bash /workspaces/reso-world/scripts/scan-before-push.sh -C /workspaces/reso-world/.worktrees/issue-145-push-refspec-guard)" && [ -n "$SHA" ] && git -C /workspaces/reso-world/.worktrees/issue-145-push-refspec-guard push origin "${SHA:?}:refs/heads/fix/issue-145-push-refspec-guard"`
- [ ] **Step 3:** `gh pr create --repo usaturn/create-reso-world --base main --head fix/issue-145-push-refspec-guard`（本文に `Closes #145`、Spec の決定と理由、実行方式と理由、検証と結果、作業時間）。CI は private で停止しているので確かめない

## 実行方式

`superpowers:executing-plans`（inline）。5 か所への同じ置き換え 1 つと、その検証で、Task 2 は Task 1 の結果に依存する。サブエージェントに渡す利点が無い。ブランチ全体のレビューだけを新しい文脈のサブエージェント（Agent ツール）に任せる。

## 実行予算

単純な変更として、全体の目安を能動時間 45 分（準備・Spec・Plan 15 分、実装 5 分、検証・レビュー 20 分、PR 5 分）とし、ledger は省く（`.agents/execution-budget.md` の適用範囲）。45 分を超えたら停止して報告する。

## Contingency

- 既存のテストが失敗したら: 変更前の `origin/main`（`2deb900`）で同じテストを実行して比べ、新しい失敗だけを systematic-debugging で調べる
- 再現で期待と違う結果が出たら: 形を直す前に、シェルの展開を `printf '%s\n'` で確かめ、原因を Spec に書く。解消できなければ停止する
- 競合（同じ Issue の PR・予約）が見つかったら: push・PR をせずに停止する

## 完了

（実装後に追記する）
