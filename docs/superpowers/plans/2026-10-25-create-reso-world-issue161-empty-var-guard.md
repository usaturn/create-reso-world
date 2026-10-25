# Issue #161 空の変数で別の対象を書き換える呼び出しを `${VAR:?}` で止める Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（内容の承認は無い。実行許可は Spec の「管理・実行許可」のとおり）
- 作業場所: `/workspaces/reso-world/.worktrees/issue-161-merge-var-guard`、branch `fix/issue-161-merge-var-guard`（`origin/main` `c1fdc56` から作成）
- セッションディレクトリ: `/workspaces/reso-world/tmp/agents/issue-161.4te9xs1z`（再現の script とログ、実行予算の ledger、SDD の作業領域。コミットしない）

**Goal:** review-fix-planning の手順のうち、変数が空だと別の PR・リポジトリ・checkout を書き換える呼び出しを、`${VAR:?}` でコマンドの起動前に止める。

**Architecture:** Spec の「調べた呼び出し」で「付ける」とした 10 の呼び出しの変数に `:?` を足し、SKILL.md の「共通 context の確認」に規則の 2 文を、Red flags に空の `--match-head-commit` を足す。`finalize.py` などの helper は変えず、空の値で止まることを実行で確かめる。

**Tech Stack:** Markdown、bash 5.3.9・zsh 5.9・git 2.55.0・gh 2.101.0 での再現

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue161-empty-var-guard-design.md`（`11f4d7c`）

## Global Constraints

- 変えるのは `.agents/skills/review-fix-planning/SKILL.md` と `.agents/skills/review-fix-planning/references/execution.md` と、この Spec・Plan だけ
- 新しい形は Spec の「調べた呼び出し」の「新しい形」の列のとおりに書く。「変えない」の行は触らない
- 規則の 2 文は Spec の「必要な挙動」の 3 のとおり
- テストは書かない（Spec の決定記録）。再現は一時リポジトリと偽の `gh` だけで行い、実際の PR・remote を書き換えない
- 一時的な script・ログは `/workspaces/reso-world/tmp/agents/issue-161.4te9xs1z/` に置き、worktree に作らない

## Review Focus

1. zsh で `$()` の中の `"${MAIN_ROOT:?}"` が失敗したとき、外の `&&` の連鎖が止まって push しないこと → Task 2 の Step 2 の A を `zsh -f` でも実行する
2. 変数が未設定ではなく空文字列のときも止まること → Task 2 の Step 2 の B
3. `gh` の番号か `--repo` の片方だけが空でも `gh` を起動しないこと → Task 2 の Step 2 で片方だけを外した場合も実行する
4. 値があるとき、新しい形が旧い形と同じ引数・同じ結果になること。`gh pr edit` は旧い形に引数が無いので、番号と `--repo` を付けて起動すること → Task 2 の Step 2 の D
5. Markdown の inline code の中の `${VAR:?}` と二重引用符が崩れず、文書から写した文字列がそのまま動くこと → Task 2 の Step 2 は文書から取り出した文字列を実行する

## 要件の照合

| Spec の条件 | Task | 観測する結果 | 確かめる方法 |
|---|---|---|---|
| 必要な挙動 1（付ける行の新しい形） | Task 1 | 2 ファイルに新しい形があり、その行の旧い形が無い | Task 1 の Step 2、Task 2 の Step 2 の A・B・C |
| 必要な挙動 2（値があるときは同じ引数） | Task 2 | 新旧で同じ引数（`gh`）・同じ終了コードと状態（git） | Task 2 の Step 2 の D |
| 必要な挙動 3（規則の 2 文） | Task 1 | 「共通 context の確認」の最後にある | Task 1 の Step 2 |
| 必要な挙動 4（Red flags） | Task 1 | 項目に空の値の場合が入っている | Task 1 の Step 2 |
| 必要な挙動 5（`finalize.py`） | Task 2 | 空の値の記録・`--spec-commit ""` で `gh` を起動せずに `stopped`、正しい記録では `gh pr view` を起動する | Task 2 の Step 3 |
| 除外範囲（「変えない」の行、helper、他のスキル） | Task 1・2 | 差分が 2 ファイルと Spec・Plan だけ。「変えない」の git の行が空の値で止まる | Task 1 の Step 2 の `git diff --stat`、Task 2 の Step 4 |

共有する条件: 2 ファイルの新しい形は、どれも同じ規則（「共通 context の確認」の 2 文）に従う。統合の確認は自分（inline）が Task 2 で、両ファイルの形を同じ script で確かめる。

---

### Task 1: 新しい形・規則の文・Red flags を書く

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（165・169・226・257・288・289・351〜352・355 行と、「共通 context の確認」の最後（143 行の後）、Red flags の 575 行）
- Modify: `.agents/skills/review-fix-planning/references/execution.md`（45・172 行）

**テストの要否:** 不要。SKILL.md・参照文書の文面だけの変更（`AGENTS.md` の「テストの採用基準」の F、Spec の決定記録）。代わりの検証は Step 2 と Task 2。

- [ ] **Step 1:** Spec の「調べた呼び出し」の「付ける」の 10 行を「新しい形」にし、規則の 2 文と Red flags の変更を書く。Red flags の項目は次の文にする: 「`--match-head-commit` を付けずに、または値が空のまま（`--match-head-commit ""` は head を照合しない）マージしようとしている、修正不要のマージを `finalize.py` を使わずに行おうとしている」
- [ ] **Step 2:** 確かめる

Run: `git -C /workspaces/reso-world/.worktrees/issue-161-merge-var-guard diff --stat origin/main...HEAD; git -C /workspaces/reso-world/.worktrees/issue-161-merge-var-guard diff --check`
Expected: 変更は 2 ファイルと Spec・Plan だけ。`--check` は出力なし

Run: 2 ファイルを `grep -c -F` で、新しい形 10 件・規則の 2 文・Red flags の文がそれぞれ 1 回ずつあり、付けた行の旧い形（Spec の表の「呼び出し」の列の文字列）が 0 回であることを数える
Expected: 新しい形・規則・Red flags は各 1、旧い形は各 0

- [ ] **Step 3:** commit（`fix: guard review-fix-planning writes against empty target variables`）

### Task 2: 文書の形の実行と全体の確認

**Files:** 変更なし（結果は Step 6 で Spec の「検証の結果」と Plan の「完了」に追記して commit する）

- [ ] **Step 1:** `verify-doc-forms.bash` をセッションディレクトリの `repro/` に書く。Spec の「付ける」の行ごとに、新しい形を worktree の文書から、旧い形を `git show origin/main:<file>` から文字列のまま取り出し（見つからなければ失敗）、プレースホルダー（`<Spec>`→`docs/spec.md`、`<file>`→本文のファイル、`<commit>`→担当の commit、`<base>`→`main`、`<PR>`→`"$PR_NUMBER"`、`<repo>`→`"$PR_REPO"`）だけを置き換えて、Spec の「検証と受け入れ条件」の 1 の A〜D を bash と `zsh -f` で実行する
  - git の行: 呼び出しごとに一時リポジトリを作り直す（`origin.git`、親の checkout に当たる detached HEAD の `repo`、PR の head の `fix`、別の作業の `other`、PR の head の上に積んだ `stacked`、同じ名前のブランチを持つ別のリポジトリ `repo2`）。commit の日時を固定して、作り直しても SHA が同じになるようにする。旧い形（C）は Spec の「空のとき」の書き換えが起きること、新しい形（A・B）は終了コード 0 以外で状態が変わらないこと、値あり（D）は新旧の終了コードと状態が同じことを確かめる。push の行は `TOPLEVEL` を worktree にして `scan-before-push.sh` をそのまま使う
  - `gh` の行: 起動と引数を記録する偽の `gh` を `PATH` の先頭に置く。未設定・空文字列・番号だけ・`--repo` だけを外した場合に新しい形が `gh` を起動しないこと、値ありで旧い形と同じ引数になることを確かめる
- [ ] **Step 2:** 実行する

Run: `bash /workspaces/reso-world/tmp/agents/issue-161.4te9xs1z/repro/verify-doc-forms.bash > /workspaces/reso-world/tmp/agents/issue-161.4te9xs1z/repro/verify-doc-forms.log 2>&1; echo "EXIT=$?"`
Expected: `EXIT=0`。ログの各行が A・B は止まる、C は書き換える、D は新旧が同じ

- [ ] **Step 3:** `finalize.py` を確かめる

Run: `uv run --project /workspaces/reso-world/.worktrees/issue-161-merge-var-guard --locked python /workspaces/reso-world/tmp/agents/issue-161.4te9xs1z/repro/finalize-empty-values.py /workspaces/reso-world/.worktrees/issue-161-merge-var-guard`
Expected: 終了コード 0。6 つの空の値がどれも `gh_calls=0` の `stopped`、対照は最初の起動が `gh pr view`

- [ ] **Step 4:** 「変えない」の git の行を確かめる

Run: `bash /workspaces/reso-world/tmp/agents/issue-161.4te9xs1z/repro/git-empty-vars.bash > /workspaces/reso-world/tmp/agents/issue-161.4te9xs1z/repro/git-empty-vars.log 2>&1`
Expected: 「変えないもの」の節の各行が終了コード 0 以外（`rm -rf -- ''` だけは 0 で何もしない）。`repo2` のブランチが残る

- [ ] **Step 5:** ブランチ全体のレビューを、新しいサブエージェント（Agent ツール）に依頼する。Spec・Plan・`git diff origin/main...HEAD` と Step 2〜4 のログのパスを渡し、Spec の「変えない」の判定に漏れ（空で別の対象を書き換える呼び出しが残っていないか）が無いかも見させる。致命的な指摘だけを直す（直したら Task 1 の Step 2 と Task 2 の Step 2 をやり直す）
- [ ] **Step 6:** Spec に「検証の結果」、Plan に「完了」（Task ごとの commit、検証、レビューの結果と判断、所要時間）を書いて commit（`docs: record issue 161 verification`）

### Task 3: 最後の commit の検証と公開

**Files:** 変更なし

- [ ] **Step 1:** 最後の commit の後に `README.md` の「テスト」のコマンド（ワールドの行を除く）を実行し、HEAD、`git status --porcelain` が空だったこと、各コマンドの argv と終了コード、ログの完全パスをセッションディレクトリの `verification/record.md` に、`finalize.py` の `--checks-file` の形（`{"head": ..., "base": ..., "commands": [...]}`、`base` は検証のときの `origin/main` の完全な SHA）を `verification/checks.json` に書く

Run: `bash .devcontainer/run-tests.bash` / `bash scripts/check-layout.sh` / `uv run pytest tests/skills .agents/skills .agents/scripts tools`（それぞれ worktree のルートで）
Expected: それぞれ終了コード 0。失敗したら `c1fdc56` のベースライン（23 件 PASS、PASS、1225 passed）と比べる

- [ ] **Step 2:** Issue・PR・branch の競合を調べ直す（issue-to-pr 2 章 6）
- [ ] **Step 3:** `SHA="$(bash /workspaces/reso-world/scripts/scan-before-push.sh -C /workspaces/reso-world/.worktrees/issue-161-merge-var-guard)" && [ -n "$SHA" ] && git -C /workspaces/reso-world/.worktrees/issue-161-merge-var-guard push origin "${SHA:?}:refs/heads/fix/issue-161-merge-var-guard"`
- [ ] **Step 4:** `gh pr create --repo usaturn/create-reso-world --base main --head fix/issue-161-merge-var-guard`（draft にしない。本文に `Closes #161`、変更概要、Spec の決定と理由、実行方式と理由、検証と結果、作業時間と Task 別の内訳）。CI は private で停止しているので確かめない

### Task 4: PR 修正ループ（`--merge`）

- [ ] **Step 1:** `herdr-agent-task set "PR #<番号> レビュー・マージ"`
- [ ] **Step 2:** `/workspaces/reso-world/.agents/skills/pr-review-fix-loop/SKILL.md` を読み、`uv run --project /workspaces/reso-world --locked python /workspaces/reso-world/.agents/skills/pr-review-fix-loop/scripts/loop.py start "<PR の URL>" --controller-model claude-opus-5-5 --controller-runtime claude-code --max-cycles 3` で始め、その SKILL.md に従って最後まで回す
- [ ] **Step 3:** 1 サイクル目が修正不要で、サイクルの HEAD が Task 3 の Step 1 で検証した HEAD と同じなら、`verification/checks.json` を結論 2 の `--checks-file` に使う（base が進んでいたら、review-fix-planning の結論 2 の手順 2 のとおり merge したツリーで検証し直す）
- [ ] **Step 4:** issue-to-pr 5 章の「`--merge` のとき」の 6 の区分で報告する

## 実行方式

`superpowers:executing-plans`（inline）。`implement_task.py check` の `self` が true で、変更は 2 ファイルへの同じ種類の置き換えと、その検証である。Task 2 は Task 1 の文面に依存し、分けて任せる利点が無い。ブランチ全体のレビュー（Task 2 の Step 5）だけを、新しい文脈のサブエージェントに任せる。

## 実行予算

- 全体: 能動時間 300 分（`--merge` のループを含む）。着手は 04:25:38Z。ledger（`/workspaces/reso-world/tmp/agents/issue-161.4te9xs1z/budget.jsonl`）は 04:46Z に残りの 280 分で始めた
- phase の目安: 準備・調査・Spec 60 分、Plan 10 分、Task 1 10 分、Task 2 30 分、Task 3 15 分、Task 4 は 3 サイクル ×（レビューの期限 45 分＋計画・修正 15 分）＝ 180 分まで
- worker: ブランチ全体のレビューのサブエージェントは 30 分を目安にし、完了の通知で待つ（Agent ツールは `task_watch.py` で包めないので、事前宣言の打ち切りの対象にしない）。ループのレビュアー・修正の担当の期限は agent-runner の設定（レビュー 45 分、implement 90 分）に従う
- 再試行の上限: 同じ失敗の再試行は 1 回まで（既定）。安全の失敗（想定外の外部送信・実際の PR の書き換え）は全体停止
- checkpoint: Task 2 の後、PR の作成の後、ループの各サイクルの後、予算の 50%・100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) 予算が足りなければ、push の `MAIN_ROOT` と push の先を決める `gh pr view` のガードを外し、Issue が名指しした範囲（`gh pr edit`・Red flags・git の書き換え）に縮める（Spec の決定記録に変更として書く）。(2) evals の古い期待値（`evals/evals.json` の `gh pr merge`）は持ち越し候補として PR に書く。(3) ループで同じ指摘が続いたら、上限 3 で止めて報告する

## Contingency

- `README.md` のテストが失敗したら: `c1fdc56` のベースラインと比べ、新しい失敗だけを `superpowers:systematic-debugging` で調べる
- 文書から写した形の実行で期待と違う結果が出たら: `printf '%s\n'` でシェルの展開を確かめ、原因を Spec に書く。直せなければ停止する
- 競合（同じ Issue の PR・予約）が見つかったら: push・PR をせずに停止する
- push の前の検査で検出したら: `AGENTS.md` の「push の前の秘密情報の検査」に従う
