# Issue #132 superpowers の SDD の作業領域 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** superpowers の SDD・executing-plans の作業領域を worktree の外（`tmp/agents/` のセッションディレクトリ）に置く規則を `AGENTS.md` に書き、repo-cleanup-after-merge の手順 4 の報告先をそろえる。

**Architecture:** 文書の変更だけ。`AGENTS.md` の「コミットしないファイルの置き場所」の表に 1 行、「SDD 実行運用」に 1 項目を足し、repo-cleanup-after-merge の SKILL.md の手順 4 に 1 文を足す。削除の判定とスクリプトは変えない。

**Tech Stack:** Markdown、bash、superpowers 7.0.0（Claude Code）・7.0.1（pi・Codex・Devin）のスクリプト。

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue132-sdd-workspace-outside-worktree-design.md`

状態: draft。実行許可は利用者の `/issue-to-pr #132 --merge --max-cycles 3`。内容の承認を意味しない。

## Global Constraints

- 変えるのは `AGENTS.md`、`.agents/skills/repo-cleanup-after-merge/SKILL.md`、この Spec・Plan だけ（Spec の「対象外」）
- repo-cleanup-after-merge の削除の判定（手順 4 の `.superpowers/` を利用者の確認が要るものとする扱い）を変えない（Spec D5）
- 新しいテストは書かない（Spec D6）
- 変更は `/workspaces/reso-world/.worktrees/issue-132-sdd-workspace-outside-worktree`（branch `fix/issue-132-sdd-workspace-outside-worktree`）で行う。ログ・ledger は `/workspaces/reso-world/tmp/agents/issue-132.5u7egjt7/` に置き、この run の SDD の作業領域は、この変更の規則どおり `/workspaces/reso-world/tmp/agents/issue-132.5u7egjt7/sdd/` にする
- 指示文は簡潔に書く（規則は「何をする／しない」を短く）

## Review Focus

| 観点 | Task と検証 |
| --- | --- |
| `AGENTS.md` の手順どおりにスクリプトを使うと、リポジトリに何も作られない（ignore 対象を含む） | Task 3 の Step 1 |
| pi・Codex・Devin の 7.0.1 のスクリプトでも同じ | Task 3 の Step 1 |
| 表の行と「SDD 実行運用」の項目が、同じ置き場所を指して食い違わない | Task 3 の Step 2 |
| repo-cleanup-after-merge の手順 4 の削除の判定が変わっていない（足したのは報告の 1 文だけ） | Task 3 の Step 2 |
| 既存の検査（`check-layout.sh`・テスト）が通る | Task 3 の Step 3 |

## 実行方式

`implement_task.py check` の結果は `agents: [self]`、`fallback: []`、`self: true`（Spec D8）。Task は文書の 2 か所の追記と統合の確認で、どれも短く、順に扱う。issue-to-pr の 4 章の表のとおり、`superpowers:executing-plans` で、このセッションが順に実装する。subagent-driven-development は、子に渡す文脈が作業そのものより大きくなるので選ばない。

## 実装前の要件照合

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 受け入れ条件 1（手順どおりなら作業領域が worktree に作られない） | Task 1（規則）、Task 3（確認） | 一時リポジトリで `git status --short --ignored` が空、`.superpowers` が無い | Task 3 の Step 1 |
| 受け入れ条件 2（表・規則と食い違わない） | Task 1 | 表の行と「SDD 実行運用」が同じ `tmp/agents/<topic>.XXXXXX/sdd/` を指す。worktree の中に作らない規則と矛盾しない | Task 3 の Step 2 |
| 受け入れ条件 3（片付けの報告先がそろう、判定は不変） | Task 2 | 手順 4 の差分が 1 文の追加だけ | Task 3 の Step 2 |

共有する条件は、置き場所のパス（`tmp/agents/<topic>.XXXXXX/sdd/`）と、使わないスクリプトの名前（`sdd-workspace`・`task-start`・`task-done`）である。Task 1 と Task 2 の文がこれに合うかを、統合担当（このセッション）が Task 3 の Step 2 で確かめる。

## 実行予算

1. 全体の能動時間: 300 分。根拠: 文書 2 か所の変更で、実装と検証は 1 時間ほど。`--merge` のループはサイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 20 分）で最大 195 分
2. phase の目安: 準備・Spec・Plan 50 分、実装 20 分、検証 25 分、PR 10 分、ループ 195 分
3. worker: `bash .devcontainer/run-tests.bash` と `uv run pytest tests/skills .agents/skills .agents/scripts tools` は、それぞれ絶対期限 20 分、無進捗の打ち切りは出力が 10 分増えないとき。ループは pr-review-fix-loop の期限に従う
4. 再試行: 同じ失敗の再試行は 1 回まで（既定）
5. checkpoint: phase の境界、予算の 50%（150 分）・100%、worker の失敗の直後
6. 縮小・切り出し・方法変更の候補: レビューで Task 2 の 1 文が不要とされたら外す（縮小）。上流への提案（案 C）は持ち越し候補として PR 本文に書く（切り出し。Issue 化は利用者の許可を得てから）

ledger は `/workspaces/reso-world/tmp/agents/issue-132.5u7egjt7/budget.jsonl`。

---

### Task 1: `AGENTS.md` に作業領域の置き場所と使い方を書く

**Files:**
- Modify: `AGENTS.md`（「コミットしないファイルの置き場所」の表、「SDD 実行運用」）

**Interfaces:**
- Produces: 置き場所 `tmp/agents/<topic>.XXXXXX/sdd/` と、節の名前「SDD 実行運用」。Task 2 がこの節名を参照する

**テスト:** 書かない（Spec D6。文書の文言は F）。代わりに Task 3 で手順のコマンドを実行する。

- [ ] **Step 1: 表に行を足す**

「セッション後も参照し得るスクラッチ・検証ログ・下書き」の行の直後に、次の行を足す。

```markdown
| superpowers の subagent-driven-development・executing-plans の作業領域（ledger・Task の brief・報告・review package） | `tmp/agents/<topic>.XXXXXX/sdd/`（使い方は「SDD 実行運用」） |
```

- [ ] **Step 2: 「SDD 実行運用」に項目を足す**

1 つ目の項目（「Plan に「実行予算」の節を設け…」）の直後に、次の項目を足す。

```markdown
- superpowers の subagent-driven-development・executing-plans の作業領域は、スキルの言う `.superpowers/sdd/<plan>/` ではなく、実行予算の ledger と同じセッションディレクトリの `sdd/`（`tmp/agents/<topic>.XXXXXX/sdd/`）に置く。`sdd-workspace`・`task-start`・`task-done` は作業領域を worktree に作るので使わない。`task-brief` は 3 つ目、`review-package` は 4 つ目の引数に `sdd/` の下の出力先を渡し、ledger（`sdd/progress.md`）と Task の完了の行は手で書く
```

- [ ] **Step 3: 差分を確かめて commit する**

Run: `git -C <worktree> diff -- AGENTS.md`
Expected: 上の 2 行の追加だけ。

```bash
git add AGENTS.md
git commit -m "docs: keep superpowers SDD workspaces outside worktrees (#132)"
```

### Task 2: repo-cleanup-after-merge の手順 4 に生成元と直す先を書く

**Files:**
- Modify: `.agents/skills/repo-cleanup-after-merge/SKILL.md`（手順 4 の「毎回ここで止まるなら、直すのは片付け側ではなく生成側である」）

**Interfaces:**
- Consumes: Task 1 の節名「SDD 実行運用」と置き場所 `tmp/agents/`

**テスト:** 書かない（Spec D6）。判定を変えないことは Task 3 の Step 2 の差分で確かめる。

- [ ] **Step 1: 1 文を足す**

「報告時は「どのスキル・どの手順の生成物か」を添えて指摘し、生成側を次の原則へ合わせるよう促す。」の段落の末尾に、次の文を続ける。

```markdown
たとえば `.superpowers/sdd/` は superpowers の subagent-driven-development・executing-plans のスクリプト（`sdd-workspace`・`task-start`・`task-done`）の生成物で、ルート `AGENTS.md` の「SDD 実行運用」が置き場所を `tmp/agents/` に定めている。
```

- [ ] **Step 2: 差分を確かめて commit する**

Run: `git -C <worktree> diff -- .agents/skills/repo-cleanup-after-merge/SKILL.md`
Expected: 上の 1 文の追加だけで、手順 4 の ignore 対象の一覧と「削除しない」の文は変わらない。

```bash
git add .agents/skills/repo-cleanup-after-merge/SKILL.md
git commit -m "docs: name the SDD workspace source in repo cleanup step 4 (#132)"
```

### Task 3: 統合の確認

**Files:** 変更しない（ログは `/workspaces/reso-world/tmp/agents/issue-132.5u7egjt7/` に置く）

**テスト:** 書かない。下の実行で確かめる。

- [ ] **Step 1: `AGENTS.md` の手順のコマンドを一時リポジトリで実行する**

`mktemp -d` の一時リポジトリ（Plan を 1 つ commit したもの）と、その外のセッションディレクトリの代わりの `mktemp -d` を作る。7.0.0（`~/.claude/plugins/cache/claude-plugins-official/superpowers/7.0.0/skills`）と 7.0.1（`~/.pi/agent/git/github.com/obra/superpowers/skills`）のそれぞれで、`task-brief PLAN 1 <sdd>/task-1-brief.md` と `review-package PLAN BASE HEAD <sdd>/review.diff` を実行し、`<sdd>/progress.md` を手で書く。git の環境変数は `env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE` で外す。

Expected: どちらの版も、両方のコマンドが終了コード 0。一時リポジトリで `git status --short --ignored` の出力が空、`find . -name .superpowers` の出力が空。`<sdd>` に brief・review package・ledger がある。

- [ ] **Step 2: 差分全体を読む**

Run: `git -C <worktree> diff origin/main -- AGENTS.md .agents/skills/repo-cleanup-after-merge/SKILL.md`
Expected: 表の 1 行、「SDD 実行運用」の 1 項目、手順 4 の 1 文の追加だけ。表と項目が同じ `tmp/agents/<topic>.XXXXXX/sdd/` を指し、「worktree の中に、コミットしないファイルを作らない」の規則と食い違わない。手順 4 の ignore 対象の一覧と「削除しない」の文が変わっていない。

- [ ] **Step 3: README の「テスト」のコマンドを実行する**

worktree のルートで、それぞれ終了コードとログを残す。

Run: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`
Expected: どれも終了コード 0（ワールドの行は対象外）。

- [ ] **Step 4: 検証の記録を作る（`--merge`）**

最後の commit の後の HEAD、そのときの `git status --porcelain` が空だったこと、各コマンドの argv・終了コード・ログの完全パスを `/workspaces/reso-world/tmp/agents/issue-132.5u7egjt7/` に記録し、`finalize.py` の `--checks-file` の形のファイルも作る（review-fix-planning の `references/execution.md` の 3 章）。

## 完了

- Task 1: `2cc1db7`（2026-10-24T19:15Z）。差分は Expected どおり 2 行の追加だけ
- Task 2: `2cc72e7`（19:16Z）。段落の末尾への 1 文の追記だけで、手順 4 の ignore 対象の一覧と「削除しない」の文は変わらない
- Task 3: Step 1 は 7.0.0・7.0.1 とも終了コード 0、一時リポジトリの `git status --short --ignored` と `find . -name .superpowers` の出力は空（`/workspaces/reso-world/tmp/agents/issue-132.5u7egjt7/sdd-outfile-check.log`）。Step 2 は Expected どおり。Step 3 は `2cc72e7` で `run-tests.bash`（23 件 PASS）・`check-layout.sh`・`uv run pytest tests/skills .agents/skills .agents/scripts tools`（1224 passed）がどれも終了コード 0。最後の commit の後の検証は、`--merge` の検証の記録（Step 4）と PR 本文に書く
- ブランチ全体のレビュー（新しいコンテキストの Opus のサブエージェント、19:21Z〜19:29Z）: Critical・Important は無く、マージしてよいの判定。Minor 6 件
  - Ruling: 指摘 1（`task-start`・`task-done` を使わないときの BASE の控え方と、テストが通ったときだけ完了の行を書く条件が無い）を Important に上げて直した（`7bd0605`）。今回の変更が `task-done` のゲートを外したのに代わりを書いておらず、再開のときに未検証の Task を完了扱いで飛ばしうるため。Task 1 の Step 2 の文に 1 文を足した形になる
  - Ruling: 指摘 5・6（Spec の根拠の書き方の誤り、D1 に失う機能との比較が無い）は記録の誤りなので Spec を直した
  - 持ち越し（Minor）: 指摘 2（1 つの `sdd/` を 2 つ目の Plan に使うと前の ledger を上書きしうる）、指摘 3（出力先のファイル名をスクリプトの既定に合わせると書いていない。この Plan の Task 3 の `review.diff` も固定名）、指摘 4（repo-cleanup-after-merge に足した 1 文の列挙が、出力先を渡さない `task-brief`・`review-package` を含まず、「次の原則」との間に入って流れが切れる）
  - 範囲外のまま: SDD の Finish で `sdd/` を消すと runner への依頼の記録が失われうること、Codex で superpowers 5.1.3 と 7.0.1 が併存していること（どちらも変更前からの状況）
- 未確認: SDD の実装サブエージェントが worktree の外の `sdd/` に報告を書く経路は、この run（executing-plans）でも PR #190・#224・#257 でも実行していない
- Ruling: この run の作業領域は、この変更の規則どおり `/workspaces/reso-world/tmp/agents/issue-132.5u7egjt7/sdd/` に置いた（ledger・brief・review package）
- Ruling: `superpowers:test-driven-development` は読み込まなかった。変更は文書だけで、`AGENTS.md` の「テストの採用基準」と Spec D6 によりテストを書かないため
- 所要時間（着手 2026-10-24T19:10Z から修正の commit まで）: 約 30 分。内訳は、入力・競合・スクリプトの確認 10 分、Spec・Plan 5 分、Task 1・2 が 2 分、Task 3 とブランチ全体のレビューが並行して約 18 分（テストの実行 約 20 分を含む）、修正 1 分
