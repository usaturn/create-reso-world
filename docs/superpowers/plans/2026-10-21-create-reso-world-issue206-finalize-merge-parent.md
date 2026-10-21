# Issue #206: finalize.py のマージの後の merge commit の照合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 最後の base の照合の後にマージの処理までに base が進んだ PR を、finalize.py が完了扱いせず、マージ済みの事実と照合した SHA を残して止まり、merge commit のツリーで検証し直した記録の再実行でだけ関連 Issue を更新する。

**Architecture:** マージの後の確認（state・`mergedAt`・head）の直後に、PR の `mergeCommit` と Git の commit の API の `parents` の先頭を読み、検証の記録の `base` と比べる `check_merge_parent` を足す。一致しない・読めないときは `merge_parent` 付きの `Stop` で、`merged: true` の `stopped` を返す。ループ（`loop.py`）は変えず、手順書に補足のコメント・再検証・再実行の手順を書く。

**Tech Stack:** Python 3.14、pytest（偽の gh）

**Spec:** `docs/superpowers/specs/2026-10-21-create-reso-world-issue206-finalize-merge-parent-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/206
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-206-finalize-merge-parent`（branch `fix/issue-206-finalize-merge-parent`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr … --merge --assign implement=self`。PR の作成後に PR 修正ループを回し、修正不要ならループの `finalize.py` がマージする）
- 実行方式: inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true で、Task 1 は `finalize.py` とそのテストを TDD の順に逐次変更し、Task 2 は Task 1 の結果の形を、Task 3 の文書は Task 1 の挙動をそのまま使い、Task 4 はそれらを照合する統合確認である。委譲しても並行できず、文脈を渡す手間が上回る。独立したレビューは Task 4 の最後のブランチ全体のレビュー（新しいコンテキストのサブエージェント）で受ける
- 検証のログ・実行の記録（ledger `budget.jsonl` を含む）: `/workspaces/reso-world/tmp/agents/issue-206.zn83426u/`（commit しない。worktree の中には置かない）。以下 `$SESSION`
- 基準: `origin/main` の `49aa950`（基準の検証は `$SESSION/baseline-*.log`）

## Global Constraints

- 完了条件: マージの後の確認で、PR の `mergeCommit.oid` を `gh api repos/<repo>/git/commits/<oid>` で読み、`parents` の先頭の `sha` が検証の記録の `base` と同じこと。応答の `sha` が `oid` と同じで、どれも完全な SHA のときだけ読めたとする（Spec の設計 1、D-206-2・D-206-3）
- 照合の位置: state・`mergedAt`・head の照合の直後、closing Issue の更新の前。この run がマージした PR にも、最初から既にマージ済みの PR（Issue の更新の再開・手動マージ）にも同じに行う（設計 1）
- 止まったとき: `outcome: stopped`・`merged: true`・`issues: []`・`merge_parent = {"verified": <検証の記録の base>, "merge_commit": <oid か null>, "first_parent": <最初の親か null>}`。`stop_reason` は `external:` で始まる。関連 Issue を読まず、閉じない（D-206-1・D-206-4・D-206-6）
- 一致したときの結果は今までと同じで、新しいキーを足さない（D-206-4）
- 検証の記録の形（`head`・`base`・`commands`）は変えない。再検証の記録は `base` を merge commit の最初の親にしたもの（D-206-5）
- 変えないもの: マージの前の照合（`check_base`・`base_moved`・`wait_for`）と順序、`loop.py`、`upsert_pr_comment.py`、issue-to-pr の SKILL.md、pr-review-fix-loop の `references/records.md`、`Closes` の扱い（#138）（設計 6）
- テストは偽の gh だけを使い、実際の GitHub を読ませない。文書の文言を照合するテストと GitHub Actions は作らない（AGENTS.md「テストの採用基準」「GitHub Actions」）

## Review Focus

- 記録の投稿の後に、人が base の進んだ main へ手でマージした（最初の確認で既に MERGED）: Issue の更新の再開の経路でも止まる → Task 1 の `test_manual_merge_on_a_moved_base_is_merged_but_not_completed`
- マージの直後に merge commit の取得だけが一時的に失敗した: マージ済みを失わず、読めるようになった同じ記録の再実行で完了する → Task 1 の `test_merge_commit_read_failure_after_the_merge_recovers_with_the_same_record`
- 不一致で止まった後、司令塔が検証し直さずに同じ記録で再実行した: 止まったまま、何も書き込まない → Task 1 の `test_only_a_record_verified_on_the_merge_commit_completes_the_issue_update`
- `--spec-commit`（マージするのは Spec の commit）: 最初の親の照合は同じに働く → Task 1 の各テストの `spec` の組み合わせ
- GitHub の応答の形の崩れ（`mergeCommit` が null・短い SHA、応答の `sha` の違い、`parents` が空・形の違い）: 例外にせず、読めないとして止まる → Task 1 の `test_unreadable_merge_commit_is_merged_but_not_completed`

## 要件と Task・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. マージの処理までに base が進むと、両方の経路で `merged: true` の `stopped`・`merge_parent` を返し、Issue を更新しない | Task 1 | `base_moved_at_merge` の組み合わせが `stopped`・`merged: true`・`issues: []`・`merge_parent`（`BASE`・`MERGE_COMMIT`・`NEW_BASE`）で、`issue view`・`issue close` を呼ばない | Task 1 の Step 3（修正前は失敗）・Step 5、Task 4 の Step 1（照合を外すと落ちる対照） |
| 2. base が動かない対照は `no_fix_needed`。既にマージ済みの PR の再実行は過去の merge commit を照合して完了する | Task 1 | `base_kept` の組み合わせが `no_fix_needed` で `merge_parent` が無い。既存の再開のテストが通り、再実行が merge commit を読む | Task 1 の Step 5、Task 4 の Step 1・Step 4 |
| 3. 同じ記録の再実行は止まったまま。再検証した記録で Issue の更新だけが進む。読めないときも `merged: true` の `stopped` | Task 1 | 操作の順のテストで、2 回目は書き込みなし、3 回目は `issue close` だけ。読めない組み合わせは `merged: true`・`issues: []`・読めた値だけの `merge_parent` | Task 1 の Step 5、Task 4 の Step 1 |
| 4. ループは新しい停止を `stopped`・`merged: true` で終え、`merge_parent` を記録に残す。手順書が新しい結果と手順を書く | Task 2（ループ）、Task 3（文書）、統合は Task 4 | `true_merge_parent` の組み合わせで run が `stopped`・`merged: true`、`planning.finalize.result.merge_parent` が残る。文書の記述が Global Constraints と一致する | Task 2 の Step 3、Task 3 の Step 4、Task 4 の Step 2 |
| 5. 偽の gh で操作の順と状態を確かめる。文言の照合テストと Actions を足さない。README の入口で失敗が無い | Task 1・Task 2、Task 4 | 新しいテストは偽の gh だけを呼ぶ。README の 3 つの入口が終了コード 0 | Task 4 の Step 2・Step 4 |

共有する前提: `merge_parent` の形（3 つのキーと null の意味）、`stopped`・`merged: true`・`issues: []` の組、再検証の記録の `base`（最初の親）を、`finalize.py`（Task 1）、ループのテスト（Task 2）、3 つの文書（Task 3）が同じに扱う。統合担当の Task 4 が、文書の記述とテストを Global Constraints と照合する（Step 2 のレビューの観点に含める）。

## 実行予算

- Issue 全体の能動時間の予算: 400 分（ledger: `$SESSION/budget.jsonl`）。根拠は #221（300 分の予算で、PR 修正ループ 1 サイクル）。この Issue は helper の変更とテストが #221 より大きく、`--merge` のループの段階を最大 3 サイクル分含める。ledger は 10:31（JST）に 300 分で作ったが、ループの段階を含めていなかったので、ほかの記録を足す前に 10:37 に 400 分で作り直した。着手（10:15 ごろ）から 10:37 までの約 22 分は ledger に入っておらず、予算の 400 分はその分を含めて見積もった
- phase の目安: 準備・調査 45 分（済）、Spec・Plan 35 分、Task 1 50 分、Task 2 10 分、Task 3 25 分、Task 4 50 分（対照 5 分、最後のレビューの待ちと判定 20 分、README の入口 25 分）、PR 10 分、PR 修正ループ 最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 15 分）のうち、予算に収まる範囲
- worker は使わない（inline）。最後のレビューのサブエージェントは 1 回だけ起動し、完了の通知で待つ。長時間の実行（`run-tests.bash`・pytest 全体）はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 30 分。README の入口は並行させず順に実行する
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・環境の I/O の停止）は 1 回まで。安全の失敗（実際の GitHub への書き込み、実リポジトリ・親の `.venv` の書き換えの疑い、本物の担当の起動）は再試行せず止まる
- checkpoint: Task 1 の後、Task 2 の後、Task 3 の後、Task 4 の後、ループの各サイクルの後、予算の 50%・100%（100% では停止して報告する）
- 縮小・方法変更の候補: 読めない組み合わせのテストが偽の gh の都合で書きにくければ、`mergeCommit` が無い・取得の失敗・`parents` の形の 3 つに絞る。Task 2 のテストが今の `loop.py` で通らなければ（Spec の事実と違う）、`loop.py` を直さずに止まり、Spec を見直す。README の入口が環境の要因で落ちたら、基準（`49aa950`）の同じ実行（`$SESSION/baseline-*.log`）と比べて差分だけを判定する

## Task 1: マージの後に merge commit の最初の親を照合する（TDD）

**Files:**
- Modify: `.agents/skills/review-fix-planning/tests/test_finalize.py:102-210`（`FakeGh`）、`:903-914`（`test_rerun_after_the_merge_does_not_compare_the_moved_base`）、末尾に新しい節
- Modify: `.agents/skills/review-fix-planning/scripts/finalize.py:1-8`（docstring）、`:48-59`（`FIELDS`）、`:64-78`（`Stop`）、`:218-244` の後（`check_merge_parent`）、`:423-424`（コメント）、`:435-449`（マージの後の確認）、`:451-456`（`except Stop`）

**Interfaces:**
- Produces: `check_merge_parent(runner: Any, repo: str, view: Mapping[str, Any], verified: str) -> None`、`Stop(reason, *, wait_for=None, base_moved=None, merge_parent=None)` と `Stop.merge_parent: dict[str, str | None] | None`、finalize の結果の `merge_parent`（Global Constraints の 3 行目の形）。偽の gh の `FakeGh.merge_parents: dict[str, list[str]]`・`tip_at_merge: str | None`・`commit: Any`・`commit_fails: bool`・`commit_requests() -> list[str]`

**テストの要否:** 書く。マージの後の完了条件（分岐）と、止まったときの結果の形、再実行の操作の順を新しく足すので、拒否する側（base が進んだ・手動マージ・読めない）と受け入れる側（base が動かない・再検証した記録・読めるようになった再実行）を対にして、偽の gh の実経路で確かめる（AGENTS.md「テストの採用基準」の「書く」と、Issue の再現の再発防止）。

- [ ] **Step 1: 偽の gh に merge commit とその親を持たせる**（`test_finalize.py`）

`FakeGh.__init__` に足す（コメントは既存の属性と同じ書き方）:
- `self.view["mergeCommit"]`: `{"oid": MERGE_COMMIT}`（`state == "MERGED"`）か `None`
- `self.merge_parents: dict[str, list[str]]`: merge commit ごとの親。最初から MERGED なら `{MERGE_COMMIT: [BASE, HEAD]}`、それ以外は空
- `self.tip_at_merge: str | None = None`: マージの処理の直前に base の先端をこれに進める（最後の照合の後の、別のセッションのマージ）
- `self.commit: Any = None`・`self.commit_fails = False`: Git の commit の API の応答の差し替えと、取得の失敗

`pr merge` の分岐（マージする側）: `tip_at_merge` があれば base の先端をそれにしてから、`merge_parents[MERGE_COMMIT] = [その時の base の先端, view["headRefOid"]]`、`view` に `mergeCommit={"oid": MERGE_COMMIT}` も入れ、最後に base の先端を `MERGE_COMMIT` に進める（今の 2 行の前後に足す）。

新しい分岐: `len(argv) == 3 and argv[1] == "api" and "/git/commits/" in argv[2]` のとき、末尾の SHA が `merge_parents` に無いか `commit_fails` なら終了コード 1。そうでなければ `self.commit`、無ければ `{"sha": <SHA>, "parents": [{"sha": p} for p in merge_parents[SHA]]}` を返す。`commit_requests()` は、その呼び出しのパスの一覧（`branch_requests()` と同じ書き方）。

- [ ] **Step 2: 失敗するテストを書く**（`test_finalize.py`）

`test_rerun_after_the_merge_does_not_compare_the_moved_base` の docstring に「代わりに、過去のマージの merge commit の最初の親を照合する（#206）」を足し、2 回目の前の `len(gh.commit_requests())` を取って、2 回目の後に 1 件増えたことを確かめる。

末尾に節 `# --- マージの後のmerge commitの照合（#206） ---` を足す（節の説明のコメント 2 行: 最後のbaseの照合からGitHubがマージを処理するまでの間に別のセッションのマージでbaseが進む。GitHubのマージはbaseを固定できないので、マージの後にmerge commitの最初の親と検証したbaseを比べる）。`written(gh)` と `finalize_with(gh, spec, evidence)` は既存のものを使う。

- `test_merge_commit_parent_must_be_the_verified_base`（`spec` を `[False, True]`、`moved` を `[True, False]`、ids `base_moved_at_merge`・`base_kept`）: docstring「Issue #206 の再現と対照。マージの処理の直前にbaseが進むと、マージ済みのまま止まり、Issueを閉じない。」。`gh = spec_gh() if spec else FakeGh()`、`moved` なら `gh.tip_at_merge = NEW_BASE`、`result = finalize_with(gh, spec, checks())`、`posted = [] if spec else ["POST"]`

  ```python
  assert gh.merge_parents[MERGE_COMMIT][0] == (NEW_BASE if moved else BASE)
  assert gh.commit_requests() == [f"repos/{REPO}/git/commits/{MERGE_COMMIT}"]
  if moved:
      assert (result["outcome"], result["merged"], result["issues"]) == ("stopped", True, [])
      assert result["merge_parent"] == {"verified": BASE, "merge_commit": MERGE_COMMIT, "first_parent": NEW_BASE}
      assert result["stop_reason"].startswith("external:")
      assert "wait_for" not in result and "base_moved" not in result
      assert written(gh) == [*posted, ("pr", "merge")]
      assert all(call[1:3] != ("issue", "view") for call in gh.calls)
  else:
      assert result["outcome"] == "no_fix_needed" and result["issues"] == [901] and "merge_parent" not in result
      assert written(gh) == [*posted, ("pr", "merge"), ("issue", "close")]
  ```

- `test_only_a_record_verified_on_the_merge_commit_completes_the_issue_update`（`spec` を `[False, True]`）: docstring「止まった後、同じ記録の再実行は止まったまま。merge commitのツリーで検証し直した記録でだけ、Issueの更新に進む。」。`gh.tip_at_merge = NEW_BASE` で `first = finalize_with(gh, spec, checks())`、`before = written(gh)`

  ```python
  again = finalize_with(gh, spec, checks())
  assert (again["outcome"], again["merged"], again["issues"]) == ("stopped", True, [])
  assert again["merge_parent"] == first["merge_parent"] and again["stop_reason"] == first["stop_reason"]
  assert written(gh) == before
  # merge commitのツリーで同じ検証をした記録（baseは実際の最初の親）
  reverified = finalize_with(gh, spec, {**checks(), "base": NEW_BASE})
  assert (reverified["outcome"], reverified["merged"], reverified["issues"]) == ("no_fix_needed", True, [901])
  assert "merge_parent" not in reverified
  assert written(gh) == [*before, ("issue", "close")]
  ```

- `test_manual_merge_on_a_moved_base_is_merged_but_not_completed`: docstring「記録を投稿した後、人がbaseの進んだmainへ手でマージした。Issueの更新の再開の経路でも、Issueを閉じない。」。`gh = FakeGh(state="MERGED")`、`gh.comments = [status_comment(record())]`、`gh.merge_parents[MERGE_COMMIT] = [NEW_BASE, HEAD]` で `mod.finalize(record(), "状況", checks(), runner=gh)` が `stopped`・`merged: true`・`issues: []`・`merge_parent == {"verified": BASE, "merge_commit": MERGE_COMMIT, "first_parent": NEW_BASE}`、`gh.writes() == []`
- `test_unreadable_merge_commit_is_merged_but_not_completed`（`problem` は `no_merge_commit`・`short_oid`・`request_fails` と、下の表の応答の差し替え）: docstring「マージ済みのPRで、merge commitかその最初の親を読めない。照合できないのでIssueを閉じず、読めた値だけを残す。」。`gh = FakeGh(state="MERGED")`・`gh.comments = [status_comment(record())]` に、`no_merge_commit` は `gh.view["mergeCommit"] = None`、`short_oid` は `{"oid": MERGE_COMMIT[:12]}`、`request_fails` は `gh.commit_fails = True`、ほかは `gh.commit = <応答>`。`read = None if problem in ("no_merge_commit", "short_oid") else MERGE_COMMIT`

  ```python
  assert (result["outcome"], result["merged"], result["issues"]) == ("stopped", True, [])
  assert result["stop_reason"].startswith("external:") and "wait_for" not in result
  assert result["merge_parent"] == {"verified": BASE, "merge_commit": read, "first_parent": None}
  assert len(gh.commit_requests()) == (0 if read is None else 1)
  assert gh.writes() == [] and all(call[1:3] != ("issue", "view") for call in gh.calls)
  ```

  | id | 応答 |
  | --- | --- |
  | `wrong_sha` | `{"sha": "d" * 40, "parents": [{"sha": BASE}, {"sha": HEAD}]}` |
  | `no_parents` | `{"sha": MERGE_COMMIT, "parents": []}` |
  | `parents_not_a_list` | `{"sha": MERGE_COMMIT, "parents": {"sha": BASE}}` |
  | `parent_not_an_object` | `{"sha": MERGE_COMMIT, "parents": [BASE]}` |
  | `short_parent` | `{"sha": MERGE_COMMIT, "parents": [{"sha": BASE[:12]}]}` |
  | `not_an_object` | `[MERGE_COMMIT]` |

- `test_merge_commit_read_failure_after_the_merge_recovers_with_the_same_record`: docstring「マージの直後にmerge commitの取得だけが失敗した。マージ済みは失わず、読めるようになった同じ記録の再実行で完了する。」。`gh = FakeGh()`・`gh.commit_fails = True` で 1 回目が `stopped`・`merged: true`・`issues: []`・`merge_parent == {"verified": BASE, "merge_commit": MERGE_COMMIT, "first_parent": None}`、`written(gh) == ["POST", ("pr", "merge")]`。`gh.commit_fails = False` で 2 回目が `no_fix_needed`・`issues == [901]`・`merge_parent` 無し、`written(gh) == ["POST", ("pr", "merge"), ("issue", "close")]`

- [ ] **Step 3: 失敗を確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests/test_finalize.py -q`（worktree のルート）
Expected: 新しいテストと、`commit_requests` を足した既存のテストが失敗する（`base_moved_at_merge`・手動マージ・読めない組み合わせは `no_fix_needed` か `KeyError: 'merge_parent'`、`base_kept` は commit を読まないこと）。ほかの既存のテストは通る。ログは `$SESSION/task1-red.log`

- [ ] **Step 4: 実装する**（`finalize.py`）

- `FIELDS` の `"mergedAt"` の後に `"mergeCommit"`
- `Stop.__init__` に `merge_parent: dict[str, str | None] | None = None` を足して属性に持つ。docstring に「merge_parent は、マージの後に merge commit の最初の親が検証の記録のbaseと違う・読めない停止（verified・merge_commit・first_parent。読めなかった値はNone）。PRはマージ済みで、司令塔がmerge commitのツリーで検証し直してから再実行する」を足す
- `check_merge_parent` を `check_base` の後に置く。docstring に、最初の親がGitHubがマージしたときのbaseの先端であること、最後の照合からマージの処理までの前進をここで見つけること（`references/execution.md` の 3.5 節）、読めたとする条件（Global Constraints の 1 行目）を書く。`gh` の失敗（`poster.CommentError`）は読めないとして扱う。停止理由は次の 2 つ（文言はこのとおり）
  - 読めない: `external: マージの後にmerge commitの最初の親を読めず、検証したbaseで作られたかを確かめられない。読めるようになってから同じ記録で再実行し、違っていればmerge commitのツリーで再検証する`
  - 違う: `f"external: merge commit {oid[:12]} の最初の親 {first[:12]} が検証したbase {verified[:12]} と違い、検証していない組み合わせがマージされた。merge commitのツリーで同じ検証をし、検証の記録を作り直してから再実行する"`
- `finalize` のマージの後の確認: head の照合の後に `step = "merge commit"`、`check_merge_parent(active, repo, view, checks["base"])`。`except Stop` で `merge_parent` があれば結果に写す
- モジュールの docstring の 4 行目の後に「マージの後は、merge commitの最初の親がそのbaseと同じことを確かめ、違う・読めなければ関連Issueを更新せずにマージ済みのまま止まる。」、マージの直前のコメント（`:423-424`）に「マージの後にmerge commitの最初の親で確かめる」を足す

- [ ] **Step 5: 通ることを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests -q`（worktree のルート）
Expected: すべて passed、終了コード 0。ログは `$SESSION/task1-green.log`

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/review-fix-planning/scripts/finalize.py .agents/skills/review-fix-planning/tests/test_finalize.py
git commit -m "fix(review-fix-planning): stop without closing issues when the merge commit is not on the verified base (#206)"
```

## Task 2: ループが新しい停止を `stopped`・`merged: true` で残すことを確かめる

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/tests/conftest.py:389-399`（`finalize_result`）、`:565-568`（`Kit.finalize_result`）
- Modify: `.agents/skills/pr-review-fix-loop/tests/test_loop_state.py:437-472`（`test_finalize_stopped_keeps_the_real_merge`）

**Interfaces:**
- Consumes: Task 1 の結果の形（`stopped`・`merged: true`・`merge_parent`）
- Produces: `finalize_result(path, outcome, *, merged, stop_reason=None, spec_commit=None, merge_parent=None) -> Path`（`Kit` も同じ引数）

**テストの要否:** 書く。finalize がマージ済み（`true`）を返して止まり、PR の head がサイクルの HEAD と同じ組み合わせは、`cycle_end` の `merge_mismatch` の分岐の受け入れ側で、テストが無い（Spec の確認した事実）。`loop.py` は変えないので、通ることを確かめる（受け入れ条件 4 の、ループが新しい停止を `no_fix_needed` にも `merge_mismatch` にもせず、結果を残すことの保証）。

- [ ] **Step 1: 偽の結果ファイルに `merge_parent` を渡せるようにする**（`conftest.py`）

`finalize_result` と `Kit.finalize_result` に `merge_parent: dict[str, str | None] | None = None` を足し、渡されたら結果に入れる。docstring に「merge_parent は、マージの後の merge commit の照合で止まったときだけ入る（#206）」を足す。

- [ ] **Step 2: 組み合わせを足す**（`test_loop_state.py`）

`test_finalize_stopped_keeps_the_real_merge` の組み合わせに `(True, False)`（id `true_merge_parent`）を足し、コメントに「finalize がマージの後の merge commit の照合で止まった（#206）。PR は検証した HEAD でマージ済み」を書く。この組み合わせだけ、停止理由を `"external: merge commitの最初の親が検証したbaseと違う"`、`merge_parent = {"verified": "a" * 40, "merge_commit": "c" * 40, "first_parent": "b" * 40}` を `kit.finalize_result(..., merge_parent=...)` に渡す。最後に足す

```python
assert cycle["planning"]["finalize"]["result"].get("merge_parent") == merge_parent
```

（ほかの組み合わせは `merge_parent` が None で、結果にキーが無いこと）

- [ ] **Step 3: 通ることを確かめる**

Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests/test_loop_state.py -q`（worktree のルート）
Expected: 70 passed、終了コード 0（`loop.py` を変えずに通る）。通らなければ、`loop.py` を直さずに止まって Spec を見直す。ログは `$SESSION/task2.log`

- [ ] **Step 4: Commit**

```bash
git add .agents/skills/pr-review-fix-loop/tests/conftest.py .agents/skills/pr-review-fix-loop/tests/test_loop_state.py
git commit -m "test(pr-review-fix-loop): keep a finalize stop after the merge as stopped and merged (#206)"
```

## Task 3: 手順書に新しい結果と再検証・再実行の手順を書く

**Files:**
- Modify: `.agents/skills/review-fix-planning/references/execution.md:155`・`:158` の後（3.3 節）、`:167-171` の後（3.4 節）、`:177-180`（3.5 節）
- Modify: `.agents/skills/review-fix-planning/SKILL.md:263`（結論 2 の手順 7）、`:267`（base が進んだときのやり直し）
- Modify: `.agents/skills/pr-review-fix-loop/SKILL.md:68`（サイクルの 3）、`:109`（最終化の停止）、「最終報告」の関連 Issue の項

**Interfaces:**
- Consumes: Task 1 の挙動（Global Constraints の 1〜5 行目）

**テストの要否:** 書かない。文書だけの変更で、文言を照合するテストは AGENTS.md「テストの採用基準」の作らない型 1・4 に当たる。代わりに、`git diff` の確認、`scripts/check-layout.sh`、スキルの frontmatter のテスト（`tests/skills`）、Task 4 のレビューで、記述が Task 1 の挙動と一致することを確かめる。

- [ ] **Step 1: `references/execution.md`**（Spec の設計 2）
  - 3.3 節の base の項の最後の文（マージ済みの PR では base の先端を確かめない）に「代わりに、過去の merge commit の最初の親を照合する（下）」を足す
  - 3.3 節の「マージの後に MERGED・`mergedAt`・head を読み戻し…」の項の前に、マージの後の照合の項を足す: `mergeCommit` と `gh api repos/<repo>/git/commits/<merge commit>` の `parents` の先頭を読み、検証の記録の `base` と同じことを確かめる。違う・読めないときは、関連 Issue を更新せずに `merge_parent` 付きの `merged: true` の `stopped` を返す。この run がマージした PR にも、既にマージ済みの PR の再実行にも同じに行う
  - 3.4 節の `base_moved` の項の後に `merge_parent` の項を足す（Spec の設計 2 の 3.4 節の 4 項目。補足のコメントの形は同じ節の手順 3 と同じで、書くのはサイクル・3 つの SHA・merge commit のツリーで検証し直すまで関連 Issue を更新しないこと。完了させる手順の 5 つの段と、検証が失敗したときに再実行しないこと）
  - 3.5 節を、Spec の設計 2 の 3.5 節（防げないこと、helper がマージの後に見つけて止まること、その時点で base には検証していない組み合わせが入っていること、`Closes` による自動の close は照合と関係なく起きること（#138））に書き換える
- [ ] **Step 2: review-fix-planning の SKILL.md**（Spec の設計 3）
  - 手順 7 の `base_moved` の文の後に、`merge_parent` 付きの `stopped` の扱いを足す（マージ済みで helper は関連 Issue を更新していない。読めないだけならほかの `stopped` と同じく結論 3。最初の親が違えば、execution.md 3.4 節のとおり補足のコメントを投稿し、再検証せずに結論 3。再検証と再実行は利用者の指示で別に行う）
  - 「base が進んだときのやり直し」の最後の文を「`finalize.py` が最後に base を確かめてから GitHub がマージを処理するまでの間の前進は止められない。helper はマージの後に merge commit の最初の親で見つけて止まる（[execution.md](references/execution.md) 3.4 節の `merge_parent`、3.5 節）。この停止はやり直しの回数に数えない。」にする
- [ ] **Step 3: pr-review-fix-loop の SKILL.md**（Spec の設計 4）
  - サイクルの 3 の `wait_for`・`base_moved` の文の後に「マージの後の照合で止まったとき（結果に `merge_parent`）は、計画の中で再検証せずに `cycle-end` に渡す（run は `stopped`・`merged: true` で終わる）。」
  - 「最終化の停止」の `base_moved` の文の後に、`merge_parent` の扱いを足す（PR はマージ済みで、関連 Issue は finalize が更新していない。`first_parent` が null なら、原因が解消してから同じ記録で再実行する。違っていればループの中では再検証しない。完了させるときは、利用者の指示で、execution.md 3.4 節のとおり merge commit のツリーで検証し、`--round-dir` の検証の記録を作り直してから finalize.py を再実行する（Issue の更新だけを行う）。そのため `--round-dir` を消さずに残し、完全パスを報告する）
  - 「最終報告」の関連 Issue の項の後に「finalize の結果に `merge_parent` があれば、3 つの SHA と、関連 Issue を finalize が更新していないこと（`Closes` による GitHub の自動の close は別。#138）、再検証の手順（`.agents/skills/review-fix-planning/references/execution.md` の 3.4 節）」
- [ ] **Step 4: 確かめる**

Run: `git diff -- .agents/skills/review-fix-planning/references/execution.md .agents/skills/review-fix-planning/SKILL.md .agents/skills/pr-review-fix-loop/SKILL.md` を読み、`bash scripts/check-layout.sh` と `uv run pytest tests/skills -q` を実行する
Expected: 記述が Global Constraints の 1〜5 行目と一致し、AGENTS.md「日本語表現」で避ける語が無い。2 つのコマンドが終了コード 0。ログは `$SESSION/task3-*.log`

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/review-fix-planning/references/execution.md .agents/skills/review-fix-planning/SKILL.md .agents/skills/pr-review-fix-loop/SKILL.md
git commit -m "docs(review-fix-planning,pr-review-fix-loop): stop and re-verify when the merge commit is not on the verified base (#206)"
```

## Task 4: 統合確認と最後のレビュー

**Files:**
- Modify: `docs/superpowers/plans/2026-10-21-create-reso-world-issue206-finalize-merge-parent.md`（チェックと「検証の記録」）

**Interfaces:**
- Consumes: Task 1〜3 の commit

**テストの要否:** 書かない。新しい挙動は Task 1・Task 2 のテストが受け持つ。ここでは照合を外す対照、ブランチ全体のレビュー、README の入口で、条件単位の証拠をそろえる。

- [ ] **Step 1: 照合を外す対照**

`finalize.py` の `check_merge_parent(active, repo, view, checks["base"])` の呼び出しを一時的に消して `uv run pytest .agents/skills/review-fix-planning/tests/test_finalize.py -q` を実行し、`git checkout -- .agents/skills/review-fix-planning/scripts/finalize.py` で戻して `git status --porcelain` が空であることを確かめる
Expected: Task 1 の新しいテストのうち、拒否する側（`base_moved_at_merge`、操作の順、手動マージ、読めない組み合わせ、読めない後の回復の 1 回目）と commit を読むことを確かめるテストが失敗し、ほかの既存のテストは通る（テストが元の不具合を検出することの対照）。ログは `$SESSION/verify/control.log`

- [ ] **Step 2: ブランチ全体のレビュー**（新しいコンテキストのサブエージェント 1 回）

Spec・Plan・`git diff origin/main...HEAD` を渡し、(1) Spec の受け入れ条件と決定記録を満たすか、(2) 文書の記述（Task 3）が `finalize.py` の挙動とテストに一致するか、(3) マージの前の照合・既存の再実行・ループの `cycle-end` の挙動を変えていないか、(4) テストが AGENTS.md「テストの採用基準」に反していないかを見てもらう。致命的な指摘だけを直し、直したら関係する Task の検証をやり直す

- [ ] **Step 3: Plan の「検証の記録」を書いて commit する**（これが最後の commit）

各 Step のチェック、Task 別の所要時間、Task 1 の Step 3・Step 5、Task 2 の Step 3、Step 1 の結果、レビューの結果と対応を「検証の記録」の節に書き、`git commit -m "docs: record the Issue #206 verification and final review in the plan"`

- [ ] **Step 4: 最後の commit で README の「テスト」の入口を実行し、検証の記録を作る**（`--merge` のループで再利用する）

最後の commit の上で `git status --porcelain` が空であることを確かめてから、worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` をバックグラウンドで順に実行する（各 30 分まで。並行させない）
Expected: 3 つとも終了コード 0。落ちたら基準（`$SESSION/baseline-*.log`）の同じ実行と比べ、この変更による失敗かを判定する。検証した HEAD・`git status --porcelain` が空だったこと・各コマンドの argv・終了コード・ログの完全パスを `$SESSION/verify/record.md` に、`finalize.py --checks-file` の形（`{"head", "base", "commands"}`。`base` は検証したツリーが含む `origin/main` の SHA）を `$SESSION/verify/checks.json` に書く。結果は Plan に書かず（HEAD が変わるので）、PR 本文に書く

## 検証の記録

ログはどれも `/workspaces/reso-world/tmp/agents/issue-206.zn83426u/` にある（commit しない）。

### 修正の前（`49aa950`）

| 対象 | 結果 | ログ |
| --- | --- | --- |
| Issue の再現（偽の gh） | `--spec-commit` の有無の両方が `no_fix_needed`・`merged: true`・`issues: [901]`（マージの最初の親 `NEW_BASE`、検証した base `BASE`） | `repro-before.log` |
| `uv run pytest tests/skills .agents/skills .agents/scripts tools` | 3535 passed（757.29 秒）、終了コード 0 | `baseline-pytest.log` |
| `bash .devcontainer/run-tests.bash` | 33 件 PASS、終了コード 0 | `baseline-run-tests.log` |
| `bash scripts/check-layout.sh` | PASS、終了コード 0 | `baseline-check-layout.log` |
