# Issue #207 マージ済み・確認未了の状態の報告 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者の 2026-10-20 の `/issue-to-pr #207 --merge`（Spec の「実行許可」と同じ範囲）

**Goal:** `finalize.py` が観測した PR のマージ状態を判定より先に保持し、確かめていない状態を `merged: null` で返す。`loop.py` の `cycle_end` が、停止のときに実際の PR のマージ状態を run・cycle に保存する。

**Architecture:** `finalize.py` に、`pr view` の応答からマージ状態を決める小さな関数を足し、3 回の読み取りの直後（`check_view` の前）に呼ぶ。`gh pr merge` の直前に `merged` を `None` にする。`loop.py` は `_read_finalize` で `null` を受け付け、`cycle_end` の `no_fix_needed` と `stopped` の扱いを分ける。手順書 4 つに 3 値と復旧の方法を書く。

**Tech Stack:** Python 3.14（uv）、pytest、偽の `gh`（`test_finalize.py` の `FakeGh`、`pr-review-fix-loop/tests/conftest.py` の `FakeGitHub`）

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue207-finalize-merged-state-design.md`

## Global Constraints

- finalize の結果の `merged` は `True`・`False`・`None`。`None` は、GitHub に問い合わせる前の停止・PR の状態を読めない・マージを依頼した後に状態を読めない
- 観測: `state == "MERGED"` → `True`、`state` が `"OPEN"` か `"CLOSED"` → `False`、それ以外 → `None`。一度 `True` なら戻さない
- 別の head でマージ済みの停止理由: `external: PRが検証済みHEADと別のHEADでマージされた`。`--spec-commit` で検証した HEAD のままマージ済みなら `external: Specのcommitを載せる前に、PRが検証したHEADのままマージされた`（最終レビューで追加）
- `outcome`・`wait_for`・`base_moved`・停止理由の接頭辞・マージの方法・照合の順序は変えない。GitHub に問い合わせる前の停止で `gh` を呼ばない
- run・cycle の `merged` は真偽値のまま。`no_fix_needed` の `merge_mismatch` の条件を弱めない
- `upsert_pr_comment.py`・`review_records.py`・`.agents/review-records.md`・issue-to-pr の `SKILL.md` は変えない
- テストは `AGENTS.md`「テストの採用基準」に従う。文面の照合のテストを足さない

## Review Focus

1. 状況の投稿の後に、別の head で手でマージされた → 投稿だけで止まり、`merged: True`・新しい停止理由。Task 1 の `test_manual_merge_with_another_head_after_posting_keeps_the_merge`
2. `gh pr merge` が失敗を返した（GitHub が処理したかは分からない）→ `merged: None`、再実行で状態を読み直して完了する。Task 1 の `test_failed_merge_request_is_unconfirmed_and_the_rerun_recovers`
3. 最初の `pr view` が失敗、または `state` が想定外の値 → `merged: None`、書き込みなし。Task 1 の `test_unreadable_pr_state_is_unconfirmed`
4. finalize が `stopped`・`merged: true` なのに PR が未マージ → `merge_mismatch` で止まり、何も保存しない。Task 2 の `test_finalize_merged_but_pr_not_merged_is_a_mismatch_when_stopped`
5. 判断の記録が `stopped`（finalize を呼ばない）で、その間に PR が手でマージされた → `merged: True` で保存する。Task 2 の `test_recorded_stop_keeps_a_manual_merge`

## 要件と Task の対応（実装前の照合）

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| A-1 観測した MERGED を失わず、head の違いは停止 | Task 1 | Issue の表の 4 経路で `merged: True`・`stopped`、書き込みは既存の経路のまま | 新しいテスト、既存の `test_spec_commit_with_another_head_stops_without_waiting` に `merged` の期待を足す |
| A-2 未確認と未マージを区別し、読み直して復旧 | Task 1・3 | 確認の失敗・マージの依頼の失敗で `merged: None`、再実行で `no_fix_needed`。手順書に復旧の方法 | 新しいテスト、手順書の差分 |
| A-3 `cycle_end` が実際のマージ状態を保存、正常完了の照合は保つ | Task 2・3 | `stopped`・`false`/`null` で PR がマージ済みなら `merged: True`。`no_fix_needed` の照合は既存のテストのまま | 新しいテスト、既存のテスト |
| A-4 正常な OPEN・同じ head の既存のマージ・Issue の更新の再開・問い合わせ前の拒否 | Task 1・2 | 既存のテストが通る。問い合わせ前の停止は `merged: None` で `gh` を呼ばない | 既存のテストの期待を直す |
| A-5 偽の `gh` とローカルの fixture だけ | Task 1・2 | 実際の GitHub・エージェントを呼ばない | テストの fixture |

共有する条件は、finalize の結果の `merged` の 3 値と意味である。Task 1 が作り、Task 2（`loop.py`）が読み、Task 3 の手順書が説明する。統合の確認は Task 4 で、手順書の記述を Task 1・2 の実装とテストに 1 つずつ対応させて行う。

## 実行方式

`superpowers:executing-plans`（このセッションが inline で実装する）。`implement_task.py check` が `self=true` で、Task は 4 つ、Task 2・3 は Task 1 の 3 値に依存する逐次の変更である。Spec の判断を子に渡しきるより、同じ文脈で続けるほうが確実。最後に、ブランチ全体のレビューを新しいレビュアー（サブエージェント 1 つ）に依頼する。

## 実行予算

- 全体の能動時間: 460 分（ledger の予算 450 分と、ledger の開始前の準備の約 8 分）。実装・PR の作成まで 230 分（#196 の実績 約 240 分より変更が小さい）、`--merge` のループの段階 230 分（サイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 約 30 分））。ledger は `/workspaces/reso-world/tmp/agents/issue-207.zssx2rku/budget.jsonl`
- phase の目安: 準備 15 分（済）、Spec・Plan 35 分、Task 1 で 40 分、Task 2 で 30 分、Task 3 で 25 分、Task 4（全体のテスト・最終レビュー）で 70 分、PR 15 分、ループ 230 分
- worker: 実装は inline。全体のテスト（Task 4）はバックグラウンドで実行し、終了の通知で待つ（絶対期限 60 分、ログが 10 分変わらなければ stall を疑う。#196 では 38 分）。最終レビューのサブエージェントは 1 回で、期限 30 分。ループの worker の期限は pr-review-fix-loop の SKILL.md のとおり
- 再試行の上限: 同じ失敗の再試行は 1 回まで。既知の不安定なテストは 1 回だけ再実行し、再発したら `superpowers:systematic-debugging` で調べる
- checkpoint: 各 Task の完了時、PR の作成時、予算の 50%（225 分）・100%、検証の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) D-6 の「判断の記録が `stopped` のとき」を外し、PR に持ち越しとして書く (2) D-3 の停止理由の分割を外す (3) 全体のテストが環境の要因で失敗したら、`origin/main` の一時 worktree で同じコマンドを実行して既存の失敗と切り分ける

## Contingency

- 既存の finalize のテストが `merged is False` で落ちたら、GitHub に問い合わせる前の停止か（期待を `None` に直す）、観測の後の停止か（実装を疑う）を、`gh.calls` で切り分ける
- `pr-review-fix-loop/tests` の別のテストが `finalize_result(..., merged=...)` の型で落ちたら、conftest の引数の注釈だけを直す
- `cycle_end` の変更で `test_loop_review.py` の 2 サイクルのテストが落ちたら、`no_fix_needed` の照合の順序を変えていないかを先に確かめる

---

### Task 1: 観測したマージ状態の保持（`finalize.py`）

**テストの要否:** 書く。マージ状態の報告は取り消せない操作の復旧の判断に使う値で、偽の `gh` で経路ごとに確かめる（`AGENTS.md`「テストの採用基準」）。

**Files:**
- Modify: `.agents/skills/review-fix-planning/scripts/finalize.py`（docstring、新しい `observe_merged`、`check_view`、`finalize`、`main`）
- Test: `.agents/skills/review-fix-planning/tests/test_finalize.py`

**Interfaces:**
- Produces: finalize の結果の `merged: bool | None`（Task 2・3 が読む）。`def observe_merged(view: Mapping[str, Any], known: bool | None) -> bool | None`

- [ ] **Step 1: `FakeGh` に失敗の切り替えを足し、失敗するテストを書く**

`FakeGh` に `view_fails`（`pr view` が終了コード 1）、`confirm_fails`（`state` が `MERGED` の間だけ `pr view` が終了コード 1）、`merge_fails`（`pr merge` が終了コード 1 で状態を変えない）を足す。新しいテスト:

```python
MERGED_ELSEWHERE = "external: PRが検証済みHEADと別のHEADでマージされた"

@pytest.mark.parametrize("spec", [False, True])
def test_merged_with_another_head_keeps_the_merge(spec): ...
    # FakeGh(state="MERGED") / spec_gh(state="MERGED")、headRefOid="2"*40
    # → outcome stopped、merged is True、stop_reason == MERGED_ELSEWHERE、issues == []、writes() == []

def test_manual_merge_with_another_head_after_posting_keeps_the_merge(): ...
    # after_post={"headRefOid": "2"*40, "state": "MERGED", "mergedAt": ...}
    # → stopped、merged is True、stop_reason == MERGED_ELSEWHERE、writes() は POST の 1 件だけ

def test_failed_confirmation_after_the_merge_is_unconfirmed_and_the_rerun_recovers(): ...
    # confirm_fails=True → stopped、merged is None、stop_reason は external:、writes() は POST と pr merge だけ
    # confirm_fails=False で同じ入力を再実行 → no_fix_needed、merged is True、issues == [901]、
    # 足された書き込みは issue close だけ（2 回目のマージも投稿もしない）

def test_failed_merge_request_is_unconfirmed_and_the_rerun_recovers(): ...
    # merge_fails=True → stopped、merged is None、Issue を close しない
    # merge_fails=False で再実行 → no_fix_needed、merged is True

@pytest.mark.parametrize("problem", ["request_fails", "unknown_state"])
def test_unreadable_pr_state_is_unconfirmed(problem): ...
    # view_fails=True、または view["state"]="UNKNOWN" → stopped、merged is None、writes() == []
```

既存のテストの期待を直す: `test_spec_commit_with_another_head_stops_without_waiting` に `merged is (state == "MERGED")`。GitHub に問い合わせる前の停止（`test_missing_or_wrong_verification_stops_before_network`・`test_repository_outside_the_merge_scope_stops_before_network`・`test_malformed_record_is_stopped_before_network`・`test_blank_status_body_is_an_input_problem_found_before_network`・`test_invalid_spec_commit_stops_before_network`）は `merged is None`。`test_unusable_result_path_stops_before_gh` は標準出力の JSON の `merged is None` も確かめる。

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest -q .agents/skills/review-fix-planning/tests/test_finalize.py`
Expected: 新しいテストと直した期待が FAIL（`merged` が `False`、停止理由が `PRのHEADが検証済みHEADから変わった`）。ほかは PASS

- [ ] **Step 3: 実装する**

- `observe_merged`: Global Constraints の観測の規則
- `check_view`: head が違い、`--spec-commit` の待てば進む場合に当たらず、`state` が `MERGED` なら `MERGED_ELSEWHERE` の文で止める
- `finalize`: `merged` の初期値と結果の既定を `None` に。3 回の `view_pr` の直後に `merged = observe_merged(view, merged)`。`gh pr merge` の直前に `merged = None`。既存の `merged = view["state"] == "MERGED"` と `merged = True` の代入を除く（マージの後の確認を通れば観測で `True`）
- `main`: 結果の既定の `merged` を `None` に
- docstring に `merged` の 3 値を 1 行で書く

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run pytest -q .agents/skills/review-fix-planning/tests`
Expected: PASS

- [ ] **Step 5: Commit**

`git add` の対象は Files の 2 つ。メッセージ: `fix(review-fix-planning): keep the observed merge state in finalize results (#207)`

### Task 2: `cycle_end` が実際のマージ状態を保存する（`loop.py`）

**テストの要否:** 書く。run・cycle の `merged` は最終報告と復旧の判断に使う値で、偽の `gh` とローカルの bare リポジトリで確かめる。

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/scripts/loop.py`（`_read_finalize`、`cycle_end`）
- Modify: `.agents/skills/pr-review-fix-loop/tests/conftest.py`（`finalize_result` の `merged` の注釈を `bool | None` に。2 か所）
- Test: `.agents/skills/pr-review-fix-loop/tests/test_loop_state.py`

**Interfaces:**
- Consumes: Task 1 の finalize の結果の `merged: bool | None`

- [ ] **Step 1: 失敗するテストを書く**

```python
@pytest.mark.parametrize(("reported", "another_head"), [(False, True), (None, False), (True, True)])  # (True, True) は最終レビューで追加
def test_finalize_stopped_keeps_the_real_merge(loop, env, kit, tmp_path, reported, another_head): ...
    # no_fix_needed の記録を投稿。another_head なら env.push で head を進めてから env.gh.merge()
    # finalize_result("stopped", merged=reported, stop_reason=...) で cycle_end
    # → 返り値の outcome stopped・merged True、run.json の result.merged True・stop_reason は渡したもの、
    #    cycle-1.json の planning.merged True

def test_finalize_merged_but_pr_not_merged_is_a_mismatch_when_stopped(loop, env, kit, tmp_path): ...
    # finalize_result("stopped", merged=True, stop_reason=...)、PR は未マージ
    # → LoopError (4, "merge_mismatch")、cycle-1.json の state は planning のまま

def test_recorded_stop_keeps_a_manual_merge(loop, env, kit): ...
    # stopped の判断の記録を投稿し、env.gh.merge() → cycle_end（finalize なし）
    # → outcome stopped、merged True、run.json の result.merged True
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest -q .agents/skills/pr-review-fix-loop/tests/test_loop_state.py`
Expected: `null` のケースは `arguments` の LoopError、ほかは `merged` が False で FAIL

- [ ] **Step 3: 実装する**

- `_read_finalize`: `merged` は `None` か真偽値。拒否の文は今のまま
- `cycle_end`（Spec の D-6）: `no_fix_needed` は finalize の `merged is True`・`pull.merged`・`pull.head_sha == merged_head` を求め、どれかが違えば今の 2 つの文のどちらかで `merge_mismatch`。`stopped` は、finalize の `merged is True` で `pull.merged` が偽なら `merge_mismatch`、それ以外は `merged = pull.merged`。判断の記録が `stopped` なら `merged = pull.merged`。`pushed_head_mismatch` の文に `merged={pull.merged}` を足す

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run pytest -q .agents/skills/pr-review-fix-loop/tests`
Expected: PASS

- [ ] **Step 5: Commit**

`git add` の対象は Files の 3 つ。メッセージ: `fix(pr-review-fix-loop): save the real merge state when finalize stops (#207)`

### Task 3: 手順書

**テストの要否:** 書かない。文書だけの変更で、守る挙動は Task 1・2 のテストが確かめる。代わりに差分を Task 1・2 の実装と対応させ、構造のテスト（skill contract）を実行する。

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（結論 2 の手順 7 の括弧書き）
- Modify: `.agents/skills/review-fix-planning/references/execution.md`（3.3 節の最後の項目、3.4 節）
- Modify: `.agents/skills/pr-review-fix-loop/SKILL.md`（「止まったとき」の「最終化の停止」）
- Modify: `.agents/skills/pr-review-fix-loop/references/records.md`（6 章の `merged`）

- [ ] **Step 1: 書く**

- 手順 7: `merged: true` はマージ済み、`merged: null` は確かめられていないことを分けて報告し、`null` を未マージと書かない。復旧は execution.md の 3.4 節
- 3.3 節: 別の head でマージ済みなら、何も書き込まずに `MERGED_ELSEWHERE` の `merged: true` の `stopped`
- 3.4 節: `merged` の 3 値（Spec の D-1・D-5）と、`null` の復旧（D-4: `gh pr view <PR> --repo <repo> --json state,mergedAt,headRefOid` で読み直して報告し、原因を直して同じ入力で再実行する）。終了コード 2 の項目の「`merged`」の説明と食い違わないようにする
- 「最終化の停止」: finalize の `merged` が `false`・`null` でも、`cycle-end` は読んだ PR の実際のマージ状態を保存する。`null` で止まったら 3.4 節のとおり再実行する
- records.md 6 章: `merged` は `cycle-end` が読んだ PR の実際の状態。`no_fix_needed` の照合（Spec の D-6）と、`stopped` で finalize の値を上書きしないこと

- [ ] **Step 2: 確かめる**

Run: `uv run pytest -q .agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py .agents/skills/pr-review-fix-loop/tests/test_pr_review_fix_loop_skill_contract.py`
Expected: PASS。`git diff` の各文を Task 1・2 の実装とテストに対応させる

- [ ] **Step 3: Commit**

メッセージ: `docs: describe the three merge states of finalize results (#207)`

### Task 4: 統合の確認

**テストの要否:** 新しいテストは書かない。README の「テスト」の入口と最終レビューで確かめる。

- [ ] **Step 1: 条件ごとの照合** — 上の「要件と Task の対応」の各行について、実装・テスト・手順書の該当箇所を挙げる。共有する 3 値の意味が、finalize・loop・手順書の 4 か所で同じことを確かめる
- [ ] **Step 2: 最終レビュー** — 新しいレビュアー（サブエージェント 1 つ）にブランチ全体（`origin/main...HEAD`）を渡し、Spec・Plan との一致、テストの採用基準、Review Focus を確かめさせる。Critical・Important を直したら、関係するテストを実行してから Step 1 からやり直す
- [ ] **Step 3: 記録** — 下の「完了」に、所要時間と主要 Task 別の内訳、レビューの結果を書いて commit する。これを最後の commit にする（`--merge` の検証の記録は最後の commit の後に作る）
- [ ] **Step 4: README の「テスト」** — 最後の commit の後に、worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を実行する。終了コード・ログの完全パス・検証した HEAD・`git status --porcelain` が空だったことを `/workspaces/reso-world/tmp/agents/issue-207.zssx2rku/` に記録し、`finalize.py` の `--checks-file` の形のファイル（`{"head", "base", "commands"}`）も作る。結果は PR の本文に書く（この Plan には書かない。書くと HEAD が変わる）

## 完了

（Task 4 で書く）
