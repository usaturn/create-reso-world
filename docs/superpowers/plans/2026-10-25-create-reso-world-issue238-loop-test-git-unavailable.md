# Issue #238 loop の git_unavailable テスト Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `test_missing_output_checks_fail_closed[git_unavailable-audit]` を、pytest の basetemp が Git の作業ツリーの中にあっても通るようにする。

**Architecture:** テストが「Git を使えない」状態を作る方法だけを変える。`.git` を退けた跡に、存在しないパスを指す gitfile を置き、git をその階層で失敗させる。`loop.py`・`review_target.py`・fixture は変えない。

**Tech Stack:** Python 3.14、uv、pytest、git 2.55.0。

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue238-loop-test-git-unavailable-design.md`

状態: draft。実行許可は利用者の `/issue-to-pr #238 --merge`。内容の承認を意味しない。

## Global Constraints

- 変えるのは `.agents/skills/pr-review-fix-loop/tests/test_loop_review.py` の `test_missing_output_checks_fail_closed` と、この Spec・Plan だけ（Spec の「対象外」）
- 新しいテストは書かない（Spec D3）。#231 が消したパラメータを戻さない（Spec D2）
- 親の checkout（`/workspaces/reso-world`）の作業ツリーの中で実行するのは、対象のテストだけ（Spec D4）。テスト全体を作業ツリーの中で試すときは、使い捨ての外側のリポジトリ（`/tmp/claude-1000/-workspaces-reso-world/288e0a7d-b314-460f-a1ed-6a5832bf858c/scratchpad/outer-repo.Bw00ag`）の中に basetemp を置く
- 変更は `/workspaces/reso-world/.worktrees/issue-238-loop-test-git-unavailable`（branch `fix/issue-238-loop-test-git-unavailable`）で行う。ログは `/workspaces/reso-world/tmp/agents/issue-238.webd39ls/` に置く
- Python は `uv` で実行する。ruff はプロジェクトの環境に無いので、#231 と同じく `uvx ruff check` で代える

## Review Focus

| 観点 | Task と検証 |
| --- | --- |
| basetemp が Git の作業ツリーの中（`tmp/agents/` の下）にある | Task 1 の Step 4 |
| basetemp が作業ツリーの外にある（従来どおり通る） | Task 1 の Step 4 |
| `cleanup_output` が Git の照合の失敗を「登録なし」として扱う回帰を、引き続き検出する | Task 2 の Step 2 |
| 対象のテストが外側のリポジトリ（親の checkout）を書き換えない | Task 2 の Step 1 |
| pr-review-fix-loop のほかのテストに、同じ原因で落ちるものが無い | Task 2 の Step 3 |

## 実行方式

`implement_task.py check` の結果は `agents: [self]`、`fallback: []`、`self: true`（Spec D6）。変更は 1 ファイルの 1 関数で、Task は 2 つ（変更と統合の確認）、同じファイルを順に扱う。issue-to-pr の 4 章の表のとおり、`superpowers:executing-plans` で、このセッションが順に実装する。subagent-driven-development は、子に渡す文脈が作業そのものより大きくなるので選ばない。

## 実装前の要件照合

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 受け入れ条件 1（作業ツリーの中で全ケースが通る） | 1 | `tmp/agents/` の下の basetemp で 1 passed | Issue の再現コマンド |
| 受け入れ条件 2（外側のリポジトリを変更しない） | 2 | 実行の前後で親の checkout の写しが同じ | 写しの比較 |
| 受け入れ条件 3（作業ツリーの外でも通る） | 1 | `mktemp -d` の下の basetemp で 1 passed | Issue の再現コマンド |
| 受け入れ条件 4（守る性質を保つ） | 2 | 変異を入れたコピーで、内・外とも 1 failed | 使い捨てのコピー |
| 対象外（ほかのファイルを変えない） | 1・2 | 差分がテストのファイルと Spec・Plan だけ | `git diff --stat origin/main` |

共有する入力・状態・順序: 1 つのファイルを同じ担当（self）が順に変えるので、担当の間で共有するものは無い。条件ごとの統合の確認は Task 2 で行う。

## 実行予算

- 全体の能動時間: 240 分。内訳は、準備と調査 25 分、Task 1 が 10 分、Task 2 が 25 分、push と PR が 10 分、PR 修正ループが最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 15 分）＝ 180 分。根拠: 似た小さなテストの修正（#218・#219）は、ループ 1 サイクルで終わった
- worker: Plan の Task は self が実行するので、`task_watch.py` で宣言する worker は無い。ループのレビュアーは、runner の役割の期限（45 分）に従う
- 再試行の上限: 同じ失敗の再試行は 1 回まで（既定）
- checkpoint: Task 2 の後、PR の作成後、ループの各サイクルの後、予算の 50%（120 分）と 100%
- 縮小・切り出し・方法変更の候補: (1) 作業ツリーの中でほかのテストが落ちたら、原因が同じで pr-review-fix-loop の中にあるものだけをここで直し、ほかは持ち越しの候補として PR 本文に書く。(2) gitfile で git が失敗しない版があると分かったら、PATH の先頭に失敗する偽の git を置く方法（Spec D1 の (b)）に変える。(3) 外側のリポジトリの中での全体の実行が不安定なら、pr-review-fix-loop のテストに絞る
- ledger: `/workspaces/reso-world/tmp/agents/issue-238.webd39ls/budget.jsonl`

### Task 1: 壊れた gitfile で「Git を使えない」状態を作る

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/tests/test_loop_review.py:726-753`（`test_missing_output_checks_fail_closed` だけ）

**Interfaces:**
- Consumes: fixture の `env.parent`（tool root）と `tmp_path`。`loop.audit_resources(run, [])` は、記録した出力ディレクトリが無いときに `cleanup_output` を経て `git worktree list` を実行する
- Produces: 無し（Task 2 は、この関数の変更後の挙動を確かめる）

**テストの要否:** 既存の S のテストの前提を直すだけで、新しいテストは書かない（Spec D3）。確かめは、Issue の再現コマンドを変更の前後で実行して比べる。

- [x] **Step 1: 変更前の失敗を確かめる**

Run（worktree のルートで）:

```bash
T=/workspaces/reso-world/tmp/agents/issue-238.webd39ls
uv run --locked pytest -q -p no:cacheprovider --basetemp "$T/t1-inside-before" \
  .agents/skills/pr-review-fix-loop/tests/test_loop_review.py -k test_missing_output_checks_fail_closed
```

Expected: `1 failed`（`assert [] == [...]`）。

- [x] **Step 2: `git_unavailable` の準備に gitfile を足す**

`gitdir.rename(moved_gitdir)` の直後に、`gitdir.write_text(f"gitdir: {tmp_path / 'absent-gitdir'}\n", encoding="utf-8")` を足す。直前のコメント（2〜3 行）に、`.git` が無いだけだと外側のリポジトリを見つけること（#238）と、`git_output` が `GIT_*` を除くので `GIT_CEILING_DIRECTORIES` では止められないことを書く。

- [x] **Step 3: 後始末で gitfile を消す**

`finally` の `elif failure == "git_unavailable":` で、`moved_gitdir.rename(gitdir)` の前に `gitdir.unlink()` を足す。

- [x] **Step 4: 作業ツリーの中と外で実行する**

Run: Step 1 のコマンドを basetemp `"$T/t1-inside-after"` で実行し、続けて `--basetemp "$(mktemp -d)/t"` で実行する。

Expected: どちらも `1 passed`。

- [x] **Step 5: pr-review-fix-loop のテストと静的検査**

Run: `uv run --locked pytest -q .agents/skills/pr-review-fix-loop`、`uvx ruff check .agents/skills/pr-review-fix-loop/tests/test_loop_review.py`、`git diff --check`

Expected: すべて終了コード 0。

- [x] **Step 6: Commit**

```bash
git add .agents/skills/pr-review-fix-loop/tests/test_loop_review.py
git commit -m "test: make the git_unavailable loop test independent of basetemp (#238)"
```

### Task 2: 統合の確認と記録

**Files:**
- Modify: Spec の「経路表」に観測した結果を、この Plan の末尾に「完了」を足す

**Interfaces:**
- Consumes: Task 1 の commit（以下 `T1`）
- Produces: Spec・Plan の記録の commit。最後の全体の検証（5 章）は、この commit の後に行う

**テストの要否:** 新しいテストは書かない。変異・前後の写し・作業ツリーの中での全体の実行は、一時的な確認としてコミットしない（`AGENTS.md` の「テストの採用基準」）。

- [x] **Step 1: 外側のリポジトリを変えないことを確かめる（受け入れ条件 2）**

親の checkout の写しを、実行の前と後に同じ方法で取る: `git -C /workspaces/reso-world rev-parse HEAD`、`for-each-ref`、`worktree list --porcelain`、`--no-optional-locks status --porcelain`、`stash list`。間で、Task 1 の Step 1 のコマンドを basetemp `"$T/t2-inside-snapshot"` で実行する。

Expected: テストは `1 passed`。写しの差が無い。差があれば、並行する別のセッションによるものかを確かめて記録する。

- [x] **Step 2: 守る性質を変異で確かめる（受け入れ条件 4）**

`T1` を `git archive` で `/tmp` の `mktemp -d` に展開し、そのコピーの `.agents/skills/pr-review-fix-loop/scripts/loop.py` の `cleanup_output` で、`except LoopError:` の本体（`resource.state = "retained"` から `return [str(parent)]` までの 3 行）を `registrations = []` に置き換える（1 か所だけであることを確かめる）。コピーで、basetemp を使い捨ての外側のリポジトリの中と `mktemp -d` の下にして、対象のテストを実行する。

Expected: どちらも `1 failed`。変異を入れないコピーでは、どちらも `1 passed`（対照）。

- [x] **Step 3: 作業ツリーの中でテスト全体を実行する**

Run: worktree で `uv run --locked pytest -q --basetemp <使い捨ての外側のリポジトリ>/bt-after tests/skills .agents/skills .agents/scripts tools`

Expected: 全部通る。変更前（`bdbe02b`、`scan-before-inside-outer.log`）に落ちたのが対象の 1 件だけであることと比べる。ほかに落ちるものがあれば、実行予算の候補 (1) で扱う。

- [x] **Step 4: 記録して commit する**

Spec の「経路表」に観測した結果を書き、この Plan に「完了」の節（Task 別の所要時間、各確認のコマンド・終了コード・ログのパス）を足す。

```bash
git add docs/superpowers/specs/2026-10-25-create-reso-world-issue238-loop-test-git-unavailable-design.md \
  docs/superpowers/plans/2026-10-25-create-reso-world-issue238-loop-test-git-unavailable.md
git commit -m "docs: record issue 238 verification"
```

最後の commit の後、issue-to-pr の 5 章のとおり、README の「テスト」の 3 つの入口で全体を検証し、`finalize.py` の `--checks-file` の形の記録をセッションディレクトリに作る。この記録は Spec・Plan に書かず、PR 本文に書く（記録の commit の後に検証するため）。

## 完了

- Task 1: `9e97f11`（2026-10-24T16:05Z〜16:06Z）。作業ツリーの中の basetemp で 1 failed → 1 passed、`mktemp -d` の下で 1 passed。`uv run --locked pytest -q .agents/skills/pr-review-fix-loop` は 114 passed、`uvx ruff check`（ruff 0.17.2）と `git diff --check` は終了コード 0
- Task 2: 16:06Z〜16:14Z（`b69a475`）。Step 1〜3 の結果は Spec の経路表のとおり。どれも Expected と一致した
- ブランチ全体のレビュー（新しいコンテキストの Opus のサブエージェント、16:15Z〜16:27Z）: Critical・Important は無く、Ready to merge。Minor 2 件は、どちらも記録の誤りなので公開の前に直した。1 件は、Spec の着手時の確認 4 が根拠にした実験に別の要因が混じっていたこと（pytest のプロセス全体に設定した `GIT_*` は、ルートの `conftest.py` の autouse fixture が先に除く）。テストの中で設定する実験をやり直して書き換えた。もう 1 件は、この節の時刻が commit より遅かったこと
- Ruling: SDD の ledger を、worktree の中（`sdd-workspace` の `.superpowers/sdd/`）ではなく、`/workspaces/reso-world/tmp/agents/issue-238.webd39ls/sdd-ledger.md` に置いた。`AGENTS.md` の「worktree の中に、コミットしないファイルを作らない」に従った
- Ruling: push の前に、worktree と branch の名前を `issue-238-loop-test-git-ceiling` から `issue-238-loop-test-git-unavailable` に変えた。修正が `GIT_CEILING_DIRECTORIES` を使わないため。移動で `.venv` の shebang が旧パスを指して pytest を起動できなかったので（信頼性の失敗 1 回。ledger に記録）、`.venv` を作り直した
- 所要時間（着手 2026-10-24T15:47Z から Task 2 の commit まで）: 約 27 分。内訳は、入力・競合の確認 3 分、原因と案の検証 8 分（ベースラインの検証と並行）、Spec・Plan 7 分（変更前の全体の実行と並行）、Task 1 が 1 分、Task 2 が 8 分（全体の実行を含む）。続くブランチ全体のレビューと記録の訂正に約 20 分
