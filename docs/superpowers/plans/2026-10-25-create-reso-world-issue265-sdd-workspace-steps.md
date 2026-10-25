# Issue #265 SDD の作業領域の手順 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `AGENTS.md` の SDD の作業領域の手順を、そのとおりに実行して止まらず、Plan ごとに分かれ、完了の行がスキルの決まりと一致する形に直す。

**Architecture:** 文書の変更だけ。`AGENTS.md` の「SDD 実行運用」の作業領域の項目を 1 項目のまま書き直し、「コミットしないファイルの置き場所」の表の行の置き場所をそろえる。スクリプトとほかのスキルは変えない。

**Tech Stack:** Markdown、bash、superpowers 7.0.0（Claude Code）・7.0.1（Codex・pi・Devin）のスクリプト。

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue265-sdd-workspace-steps-design.md`

状態: draft。実行許可は利用者の `/issue-to-pr #265 --merge --max-cycles 3`。内容の承認を意味しない。

## Global Constraints

- 変えるのは `AGENTS.md` と、この Spec・Plan だけ（Spec の「対象外」）
- 新しいテストは書かない（Spec D6）
- 項目は 1 項目のまま簡潔に書く（Spec D1）
- 変更は `/workspaces/reso-world/.worktrees/issue-265-sdd-workspace-steps`（branch `fix/issue-265-sdd-workspace-steps`）で行う。ログ・実行予算の ledger は `/workspaces/reso-world/tmp/agents/issue-265.e91podil/` に置き、この run の作業領域は、この変更の規則どおり `/workspaces/reso-world/tmp/agents/issue-265.e91podil/sdd/2026-10-25-create-reso-world-issue265-sdd-workspace-steps/` にする

## Review Focus

| 観点 | Task と検証 |
| --- | --- |
| 新しいセッションディレクトリで、手順どおりの最初の `task-brief` が止まらない | Task 2 の Step 1 |
| 同じセッションディレクトリの 2 つ目の Plan が、1 つ目の Plan の brief・ledger を置き換えない | Task 2 の Step 1 |
| 修正後の再レビューの review package が、前の review package を置き換えない | Task 2 の Step 1 |
| 7.0.1 のスクリプトでも同じ | Task 2 の Step 1 |
| 完了の行の条件と書式が、SDD・executing-plans それぞれのスキルと一致する | Task 2 の Step 2 |

## 実行方式

`implement_task.py check` の結果は `agents: [self]`、`fallback: []`、`self: true`（Spec D8）。Task は 1 ファイルの 2 か所の変更と統合の確認で、同じファイルを順に扱う。issue-to-pr の 4 章の表のとおり、`superpowers:executing-plans` で、このセッションが順に実装する。subagent-driven-development は、子に渡す文脈が作業そのものより大きくなるので選ばない。

## 実装前の要件照合

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 受け入れ条件 1（新しいセッションディレクトリで終了コード 0、リポジトリに何も作られない） | Task 1（規則）、Task 2（確認） | 手順どおりの `mkdir -p`・`task-brief`・`review-package` が 7.0.0・7.0.1 とも終了コード 0。一時リポジトリの `git status --porcelain --ignored` と `find . -name .superpowers` が空 | Task 2 の Step 1 |
| 受け入れ条件 2（2 つ目の Plan で 1 つ目が残る） | Task 1、Task 2 | 2 つ目の Plan の brief と ledger を作った後も、1 つ目の Plan の brief・ledger の内容が変わらない | Task 2 の Step 1 |
| 受け入れ条件 3（再レビューの review package が上書きされない） | Task 1、Task 2 | 範囲の違う 2 つの review package が別のファイルとして残る | Task 2 の Step 1 |
| 受け入れ条件 4（完了の行がスキルと一致） | Task 1、Task 2 | 項目の条件・書式が、7.0.0・7.0.1 の SDD の SKILL.md の「Complete the task」と `task-done` の行に一致する | Task 2 の Step 2 |
| 受け入れ条件 5（表と項目が同じ場所） | Task 1 | 表と項目がどちらも `sdd/<plan>/` を指す | Task 2 の Step 2 |

共有する条件は、作業領域のパス（`tmp/agents/<topic>.XXXXXX/sdd/<plan>/`）、`<plan>` の作り方（Plan のファイル名から `.md` を除いた名前。`sdd-workspace` の `basename PLAN .md`）、出力先のファイル名（スクリプトの既定）である。統合担当（このセッション）が Task 2 で、表・項目・スクリプトの既定がこれに合うかを確かめる。

## 実行予算

1. 全体の能動時間: 300 分。根拠: 文書 1 ファイルの変更で、実装と検証は 1 時間ほど（#132 の実績は約 30 分）。`--merge` のループはサイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 20 分）で最大 195 分
2. phase の目安: 準備・Spec・Plan 40 分、実装 10 分、検証 30 分、PR 10 分、ループ 195 分
3. worker: `bash .devcontainer/run-tests.bash` と `uv run pytest tests/skills .agents/skills .agents/scripts tools` は、それぞれ絶対期限 20 分、無進捗の打ち切りは出力が 10 分増えないとき。ループは pr-review-fix-loop の期限に従う
4. 再試行: 同じ失敗の再試行は 1 回まで（既定）
5. checkpoint: phase の境界、予算の 50%（150 分）・100%、worker の失敗の直後
6. 縮小・切り出し・方法変更の候補: レビューで表の行の変更（Spec D5）が不要とされたら外す（縮小）。上流への提案は持ち越し候補として PR 本文に書く（切り出し。Issue 化は利用者の許可を得てから）

ledger は `/workspaces/reso-world/tmp/agents/issue-265.e91podil/budget.jsonl`。

---

### Task 1: `AGENTS.md` の作業領域の手順を直す

**Files:**
- Modify: `AGENTS.md`（「コミットしないファイルの置き場所」の表の superpowers の作業領域の行、「SDD 実行運用」の 2 つ目の項目）

**Interfaces:**
- Produces: 作業領域 `tmp/agents/<topic>.XXXXXX/sdd/<plan>/`、出力先のファイル名 `task-<N>-brief.md`・`review-<base7>..<head7>.diff`、完了の行の条件。Task 2 がこの手順をそのまま実行する

**テスト:** 書かない（Spec D6。文書の文言は F）。代わりに Task 2 で手順のコマンドを実行する。

- [ ] **Step 1: 表の行の置き場所を直す**

superpowers の作業領域の行を次にする（置き場所の列だけを変える）。

```markdown
| superpowers の subagent-driven-development・executing-plans の作業領域（ledger・Task の brief・報告・review package） | `tmp/agents/<topic>.XXXXXX/sdd/<plan>/`（使い方は「SDD 実行運用」） |
```

- [ ] **Step 2: 「SDD 実行運用」の作業領域の項目を書き直す**

「superpowers の subagent-driven-development・executing-plans の作業領域は、…」の項目を、次の 1 項目に置き換える。

```markdown
- superpowers の subagent-driven-development・executing-plans の作業領域は、スキルの言う `.superpowers/sdd/<plan>/` ではなく、実行予算の ledger と同じセッションディレクトリの `sdd/<plan>/`（`<plan>` は Plan のファイル名から `.md` を除いた名前）にし、最初に `mkdir -p` で作る。`sdd-workspace`・`task-start`・`task-done` は作業領域を worktree に作るので使わない。`task-brief` は 3 つ目、`review-package` は 4 つ目の引数に、作業領域の下のスクリプトの既定の名前（`task-<N>-brief.md`・`review-<base7>..<head7>.diff`）を渡す。BASE は Task の開始時に `git rev-parse HEAD` で控える。ledger（`progress.md`）の完了の行は手で書き、SDD は Task のレビューが clean か、上限で残りを parked にしたときにスキルの書式で、executing-plans は Task のテストが通ったときだけ `task-done` と同じ書式で書く
```

- [ ] **Step 3: 差分を確かめて commit する**

Run: `git -C /workspaces/reso-world/.worktrees/issue-265-sdd-workspace-steps diff -- AGENTS.md`
Expected: 表の 1 行と「SDD 実行運用」の 1 項目の置き換えだけ。

```bash
git add AGENTS.md
git commit -m "docs: make the SDD workspace steps runnable per plan (#265)"
```

### Task 2: 統合の確認

**Files:** 変更しない（スクリプトとログは `/workspaces/reso-world/tmp/agents/issue-265.e91podil/` に置く）

**テスト:** 書かない。下の実行で確かめる。

- [ ] **Step 1: `AGENTS.md` の手順のコマンドを一時リポジトリで実行する**

`/workspaces/reso-world/tmp/agents/issue-265.e91podil/verify-sdd-steps.bash` を書いて実行し、出力を同じディレクトリの `verify-sdd-steps.log` に残す。7.0.0（`~/.claude/plugins/cache/claude-plugins-official/superpowers/7.0.0/skills`）と 7.0.1（`~/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills`）のそれぞれで次を行う。git は `env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE` で呼ぶ。

1. `mktemp -d` の一時リポジトリに、`docs/superpowers/plans/` の Plan A・B（それぞれ `### Task 1:`・`### Task 2:` を持つ）を commit し、続けて 2 つの commit を足す（BASE・HEAD1・HEAD2）
2. `agent_tmp.py mkdir issue-265-accept` で新しいセッションディレクトリ `S` を作る
3. 対照: `mkdir -p` をせずに `task-brief A 1 "$S/sdd/<A>/task-1-brief.md"` を実行する
4. 手順どおり: `mkdir -p "$S/sdd/<A>"`、`task-brief A 1 "$S/sdd/<A>/task-1-brief.md"`、`review-package A BASE HEAD1 "$S/sdd/<A>/review-<base7>..<head1 の 7>.diff"`、`review-package A HEAD1 HEAD2 "$S/sdd/<A>/review-<head1 の 7>..<head2 の 7>.diff"`、ledger `"$S/sdd/<A>/progress.md"` を手で書く
5. 2 つ目の Plan: `mkdir -p "$S/sdd/<B>"`、`task-brief B 1 "$S/sdd/<B>/task-1-brief.md"`、ledger `"$S/sdd/<B>/progress.md"` を手で書く
6. 終わったら `S` と一時リポジトリを消す（`${VAR:?}` の空値ガード付き）

Expected: 3 は終了コード 1（`No such file or directory`）。4・5 のコマンドはどれも終了コード 0。2 つの review package が別のファイルとして残り、1 つ目の Plan の brief・ledger の sha256 は 5 の前後で変わらず、2 つ目の Plan の brief は Plan B の Task 1 の本文を持つ。一時リポジトリで `git status --porcelain --ignored` と `find . -name .superpowers` の出力が空。版ごとに `PASS` を出し、最後に `ALL PASS` を出す。

- [ ] **Step 2: 差分全体を読み、スキルと照合する**

Run: `git -C /workspaces/reso-world/.worktrees/issue-265-sdd-workspace-steps diff origin/main -- AGENTS.md`
Expected: 表の 1 行と「SDD 実行運用」の 1 項目の置き換えだけ。表と項目がどちらも `sdd/<plan>/` を指す。完了の行の条件が、7.0.0・7.0.1 の SDD の SKILL.md の「5. Complete the task」（clean か、上限で parked）と、`task-done` の「テストの終了コードが 0 のときだけ」に一致する。「worktree の中に、コミットしないファイルを作らない」の規則と食い違わない。

- [ ] **Step 3: README の「テスト」のコマンドを実行する**

worktree のルートで、それぞれ終了コードとログを `/workspaces/reso-world/tmp/agents/issue-265.e91podil/` に残す。

Run: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`
Expected: どれも終了コード 0（ワールドの行は対象外）。

- [ ] **Step 4: 検証の記録を作る（`--merge`）**

最後の commit の後の HEAD、そのときの `git status --porcelain` が空だったこと、各コマンドの argv・終了コード・ログの完全パスを `/workspaces/reso-world/tmp/agents/issue-265.e91podil/` に記録し、`finalize.py` の `--checks-file` の形のファイルも作る（review-fix-planning の `references/execution.md` の 3 章）。

## 完了

- Task 1: `5cd06f5`（2026-10-25T02:04Z）。差分は Expected どおり、表の 1 行と「SDD 実行運用」の 1 項目の置き換えだけ
- Task 2: Step 1 は 7.0.0・7.0.1 とも `ALL PASS`（`/workspaces/reso-world/tmp/agents/issue-265.e91podil/verify-sdd-steps.log`）。対照の `mkdir -p` なしの `task-brief` は終了コード 1（`No such file or directory`）、手順どおりのコマンドはどれも終了コード 0。2 つの review package が別のファイルとして残り、2 つ目の Plan の後も 1 つ目の Plan の brief・ledger・review package の sha256 は変わらず、一時リポジトリの `git status --porcelain --ignored` と `find . -name .superpowers` は空。Step 2 は Expected どおり。Step 3 は `5cd06f5` で `run-tests.bash`（23 件 PASS）・`check-layout.sh`・`uv run pytest tests/skills .agents/skills .agents/scripts tools`（1224 passed）がどれも終了コード 0。最後の commit の後の検証は、`--merge` の検証の記録（Step 4）と PR 本文に書く
- ブランチ全体のレビュー（新しいコンテキストの Opus のサブエージェント、02:05Z〜02:12Z）: Critical・Important は無く、マージしてよいの判定。Minor 5 件
  - Ruling: 指摘 2（項目から `tmp/agents/<topic>.XXXXXX/` の完全なパスが消えた）を Important に上げて直した（`61b7d9a`）。旧文の括弧書きを消した退行で、項目だけを読むと worktree の中の相対パスに作りうるため
  - Ruling: 推奨（Spec の着手時の確認 1 の「4 つとも」がどの 4 か所か分からない）は記録の誤りなので Spec を直した（`61b7d9a`）
  - 持ち越し（Minor）: 指摘 1（テストを書かない Task で、executing-plans の「テストが通ったとき」が何を指すか書いていない。変更前から同じ）、指摘 3（PR #262 の平置きの `sdd/progress.md` で進行中の run が、マージの後に新しい規則を読むと完了済みの Task をやり直しうる。PR 本文に注意を書く）、指摘 4（「SDD は」の SDD が、節名・`sdd/` の両スキルに共通の意味とずれる）、指摘 5（「ledger（`progress.md`）」をセッション直下と読む余地）
  - 範囲外のまま: レビュアーの「Declined to judge」の 9 件（ledger に Ruling として記録）
- Ruling: Task 1 の完了の行の tests に、Plan の Step 3 の `git diff`（目視）ではなく `git diff --check` を使った。終了コードで判定できるコマンドにするため
- Ruling: この run の作業領域は、この変更の規則どおり `/workspaces/reso-world/tmp/agents/issue-265.e91podil/sdd/2026-10-25-create-reso-world-issue265-sdd-workspace-steps/` に置いた（ledger・brief・review package）
- Ruling: `superpowers:test-driven-development` は読み込まなかった。変更は文書だけで、`AGENTS.md` の「テストの採用基準」と Spec D6 によりテストを書かないため。修正は一時の確認（commit しない grep）の RED→GREEN で確かめた
- 所要時間（着手 2026-10-25T02:00Z ごろから修正の commit まで）: 約 26 分。内訳は、入力・競合・スクリプトの確認 8 分、Spec・Plan 6 分、Task 1 が 1 分、Task 2 とブランチ全体のレビューが並行して約 21 分（README のテストの実行 約 20 分を含む）、修正 1 分
