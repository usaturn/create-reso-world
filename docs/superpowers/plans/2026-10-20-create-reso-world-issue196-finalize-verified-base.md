# Issue #196 finalize.py の検証した base の照合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者の 2026-10-20 の `/issue-to-pr #196`（Spec の「実行許可」と同じ範囲。マージはしない）

**Goal:** `finalize.py` が、検証の記録の `base` と PR の base ブランチの今の先端を、投稿の前とマージの直前に照合し、違えば `base_moved` を返してマージしない。review-fix-planning と PR 修正ループの手順書に、再確認の時点・止まったときの再実行・既知の制限を書く。

**Architecture:** `check_evidence` で `base`（完全な SHA）を必須にし、新しい `check_base` が `gh api repos/<repo>/branches/<baseRefName>` の先端と照合する。`Stop` に `base_moved` を足して結果に写す。`--spec-commit` の最初の PR の読み取りでは、head がまだ検証した HEAD なら `wait_for: head` にする。`loop.py` は変えない。

**Tech Stack:** Python 3.14（uv）、pytest、偽の `gh`（`tests/test_finalize.py` の `FakeGh`）

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue196-finalize-verified-base-design.md`

## Global Constraints

- 検証の記録のキーは `head`・`base`・`commands` の 3 つちょうど。`base` は `FULL_SHA`（小文字の 16 進数 40 桁か 64 桁）
- base の先端は `gh api repos/<repo>/branches/<baseRefName>` の `commit.sha`。応答の `name` が `baseRefName` と同じことを確かめる。PR の `baseRefOid` は使わない。名前を URL の符号化しない
- 照合の時点は、`--spec-commit` が無い経路の投稿の直前と、両経路のマージの直前（`check_ci` の後、`gh pr merge` の前）。マージ済みの PR では照合しない
- 前進したら、`stop_reason` は `external:` で始めて branch の名前を含めず、結果に `base_moved = {"ref", "verified", "current"}` を足す。`wait_for` は付けない
- `--spec-commit` の最初の PR の読み取りで、open で head が `reviewed_head` なら `wait_for: "head"`
- 新しい停止理由の文
  - `environment: 検証の記録に、検証したツリーが含む base の commit（完全な SHA）が無い`
  - `external: PRのbaseブランチの先端を確認できない`
  - `external: 検証した後にPRのbaseブランチが進んだ（検証したbase <先頭12桁>、今の先端 <先頭12桁>）`
  - `external: PRのheadがまだ検証したHEADのまま（Specのcommitのpushが反映される前）`
- やり直しの上限は 1 サイクルで合わせて 3 回。超えたら結論 3（`external: 検証の間に base が進み続けた`）
- `loop.py`・`upsert_pr_comment.py`・`review_records.py`・`.agents/review-records.md` は変えない
- テストは `AGENTS.md`「テストの採用基準」に従う。文面の照合のテストを足さない

## Review Focus

1. base ブランチの名前に `/` を含む（`release/1.0`）→ 名前の全体で `repos/<repo>/branches/release/1.0` を読み、先端が同じならマージする。Task 1 の `test_base_branch_name_with_a_slash_is_read_whole`
2. 検証の記録の `base` が大文字の 16 進数 → GitHub に問い合わせる前に `environment:` で止まる。Task 1 の負例 `upper_base`
3. 検証の後に PR の base を別のブランチ（`develop`）に変えた → そのブランチの先端と照合し、`base_moved.ref` が `develop` で止まる。Task 1 の `test_retargeted_base_is_compared_with_the_new_base_branch`
4. マージの後に Issue の更新をやり直す再実行（base の先端はマージの commit）→ 照合せずに完了する。Task 1 の `test_rerun_after_the_merge_does_not_compare_the_moved_base`
5. `--spec-commit` で、マージ済みかつ head が検証した HEAD（Spec の push の前に手でマージされた）→ 待ち続けず、待たずに止まる。Task 2 の `test_spec_commit_with_another_head_stops_without_waiting`

## 要件と Task の対応（実装前の照合）

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| A-1 base が進んだらマージしない。検証し直した記録ならマージする | Task 1 | 両経路で書き込みが無い（`--spec-commit` が無い経路は投稿も無い）、`base_moved`。新しい記録での再実行はマージする | 新しいテスト |
| A-2 記録の `base`、先端との照合、`baseRefOid` を使わない、既存の照合を弱めない | Task 1 | `base` の負例で `gh` を呼ばない。`baseRefOid` が古くても先端で判定する。既存テストが通る | 新しいテスト・既存テスト |
| A-3 手順書と PR 修正ループ | Task 3 | `SKILL.md` の結論 2 の手順 2・5・6・7、やり直しの上限、合理化・Red flags、`execution.md` の 3.1〜3.4、loop の `SKILL.md` の 3 か所 | 差分を Task 1・2 の実装とテストに対応させる |
| A-4 既知の制限 | Task 3 | `execution.md` の 3.5 | 差分の確認 |
| A-5 `wait_for: head` | Task 2 | open で head が検証した HEAD なら `wait_for: head`。別の head とマージ済みは待たない | 新しいテスト |

共有する条件は、結果のキー（`base_moved` の `ref`・`verified`・`current`、`wait_for` の `head`）と照合の時点である。Task 1・2 が実装し、Task 3 の手順書がそれを説明する。統合の確認は Task 4 で、手順書の記述を実装とテストに 1 つずつ対応させて行う。

## 実行方式

`superpowers:executing-plans`（このセッションが inline で実装する）。`implement_task.py check` が `self=true` で、Task 1・2 は同じ 2 ファイルの逐次の変更、Task 3 の手順書は Task 1・2 の結果のキーと時点に依存する。子に渡す文脈（Spec の判断）が大きく、委譲すると同じ説明を重ねることになる。最後に、ブランチ全体のレビューを新しいレビュアー（サブエージェント 1 つ）に依頼する。

## 実行予算

- 全体の能動時間: 240 分。Task 3 つと統合で、似た規模の #177 の予算 150 分より手順書の変更が大きい。ledger は `/workspaces/reso-world/tmp/agents/issue-196.1dvcegcd/budget.jsonl`
- phase の目安: 準備 25 分（済）、Spec・Plan 45 分、Task 1 で 40 分、Task 2 で 15 分、Task 3 で 45 分、Task 4（検証・最終レビュー）で 45 分、PR 15 分
- worker: 実装は inline。全体のテスト（Task 4）はバックグラウンドで実行し、終了の通知で待つ（絶対期限 40 分、ログが 10 分変わらなければ stall を疑う）。最終レビューのサブエージェントは 1 回で、期限 30 分
- 再試行の上限: 同じ失敗の再試行は 1 回まで。既知の不安定なテストは 1 回だけ再実行し、再発したら `superpowers:systematic-debugging` で調べる
- checkpoint: 各 Task の完了時、予算の 50%（120 分）・100%、検証の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) Task 2（`wait_for: head`）を外し、PR に持ち越しの候補として書く (2) 補足のコメント（Spec の D-7）を、完了報告への記載に縮める (3) 全体のテストが環境の要因で失敗したら、`origin/main` の一時 worktree で同じコマンドを実行して既存の失敗と切り分ける

## Contingency

- 既存テストが `base` の必須化で失敗したら、fixture の `checks()` に `base` を足したかを先に確かめる（`cli_args` も `checks()` を使う）
- 偽の `gh` は知らない呼び出しで `AssertionError` を上げる。base の API の呼び出しの形（`("gh", "api", "repos/<repo>/branches/<name>")`）を確かめる
- `.agents/skills/pr-review-fix-loop/tests` が finalize の結果の形で失敗したら、`loop.py` を変えずに止まって報告する（Spec の D-10 の前提が崩れる）

---

### Task 1: 検証した base の照合（`finalize.py`）

**テストの要否:** 書く。base が進んだ PR をマージしないことは安全の条件で、偽の `gh` で確かめる（`AGENTS.md`「テストの採用基準」）。

**Files:**
- Modify: `.agents/skills/review-fix-planning/scripts/finalize.py`（docstring、`FIELDS`、`Stop`、`check_evidence`、新しい `check_base`、`finalize`）
- Test: `.agents/skills/review-fix-planning/tests/test_finalize.py`

**Interfaces:**
- Produces:
  - `FIELDS` に `"baseRefName"`
  - `Stop.__init__(self, reason: str, *, wait_for: str | None = None, base_moved: dict[str, str] | None = None)`
  - `check_evidence(checks: Mapping[str, Any], head: str) -> None`（`base` の検査を足す）
  - `check_base(runner: Any, repo: str, view: Mapping[str, Any], verified: str) -> None`
  - `finalize` の結果の `base_moved: {"ref": str, "verified": str, "current": str}`

- [ ] **Step 1: 偽の `gh` と fixture を変える**

  - 定数 `BASE = "a" * 40`、`NEW_BASE = "b" * 40`、`MERGE_COMMIT = "c" * 40`。`checks()` に `"base": BASE`
  - `FakeGh.view` に `"baseRefName": "main"`。属性 `tips: dict[str, str] = {"main": BASE}`、`tip_after_post: str | None = None`、`branch: Any = None`（応答の差し替え）、`branch_fails = False`
  - `__call__`: `len(argv) == 3 and argv[1] == "api" and "/branches/" in argv[2]` なら、名前を `argv[2].split("/branches/", 1)[1]` で取る。`branch_fails` か `tips` に無い名前は終了コード 1。`branch` があればそれを、無ければ `{"name": 名前, "commit": {"sha": tips[名前]}}` を返す
  - 投稿（`--method`）の後、`tip_after_post` があれば `tips[view["baseRefName"]]` をそれにして `None` に戻す。マージ（`merge_stays_open` でないとき）では `tips[view.get("baseRefName", "main")] = MERGE_COMMIT`
  - `branch_requests() -> list[str]`: base の API の呼び出しのパスの一覧

- [ ] **Step 2: 失敗するテストを書く**

  ```python
  def finalize_with(gh: FakeGh, spec: bool, evidence: dict[str, Any]) -> dict[str, Any]:
      return mod.finalize(record(), "状況", evidence, runner=gh, spec_commit=SPEC_HEAD if spec else None)

  # 既存の test_missing_or_wrong_verification_stops_before_network の mutation に足す。
  # no_base: del evidence["base"]、short_base: BASE[:12]、upper_base: "A" * 40、null_base: None。
  # 4 つとも stop_reason が "environment:" で始まり、gh.calls == []

  @pytest.mark.parametrize("spec", [False, True])
  def test_base_moved_after_verification_is_not_merged_until_the_new_base_is_verified(spec: bool) -> None:
      gh = spec_gh() if spec else FakeGh()
      gh.tips["main"] = NEW_BASE
      gh.view["baseRefOid"] = BASE  # 先端に追従しない baseRefOid が検証した base のままでも、先端で判定する
      first = finalize_with(gh, spec, checks())
      assert first["outcome"] == "stopped" and first["merged"] is False and "wait_for" not in first
      assert first["stop_reason"].startswith("external:")
      assert first["base_moved"] == {"ref": "main", "verified": BASE, "current": NEW_BASE}
      assert gh.writes() == [] and gh.branch_requests() == [f"repos/{REPO}/branches/main"]
      second = finalize_with(gh, spec, {**checks(), "base": NEW_BASE})  # 新しい先端を merge したツリーの記録
      assert second["outcome"] == "no_fix_needed" and second["merged"] is True and "base_moved" not in second
      posted = [] if spec else [("api", "--method")]
      assert [call[1:3] for call in gh.writes()] == [*posted, ("pr", "merge"), ("issue", "close")]

  def test_base_moved_after_posting_is_not_merged_and_the_rerun_updates_the_comment() -> None:
      gh = FakeGh()
      gh.tip_after_post = NEW_BASE
      first = mod.finalize(record(), "状況", checks(), runner=gh)
      assert first["outcome"] == "stopped" and first["merged"] is False
      assert first["base_moved"] == {"ref": "main", "verified": BASE, "current": NEW_BASE}
      assert [call[3] for call in gh.writes()] == ["POST"]
      second = mod.finalize(record(), "状況", {**checks(), "base": NEW_BASE}, runner=gh)
      assert second["outcome"] == "no_fix_needed" and second["comment"]["action"] == "updated"
      assert [call[3] if call[1] == "api" else call[1:3] for call in gh.writes()] == [
          "POST", "PATCH", ("pr", "merge"), ("issue", "close")]

  @pytest.mark.parametrize("spec", [False, True])
  def test_rerun_after_the_merge_does_not_compare_the_moved_base(spec: bool) -> None:
      gh = spec_gh() if spec else FakeGh()
      gh.issue_fails = True
      first = finalize_with(gh, spec, checks())
      assert first["outcome"] == "stopped" and first["merged"] is True and gh.tips["main"] == MERGE_COMMIT
      gh.issue_fails = False
      requests = len(gh.branch_requests())
      second = finalize_with(gh, spec, checks())
      assert second["outcome"] == "no_fix_needed" and second["issues"] == [901]
      assert len(gh.branch_requests()) == requests

  UNREADABLE_BASES: dict[str, Any] = {
      "renamed": {"name": "trunk", "commit": {"sha": BASE}},
      "short_sha": {"name": "main", "commit": {"sha": BASE[:12]}},
      "no_commit": {"name": "main"},
      "not_an_object": ["main"],
  }

  @pytest.mark.parametrize("problem", [*UNREADABLE_BASES, "request_fails", "no_base_ref", "blank_base_ref"])
  @pytest.mark.parametrize("spec", [False, True])
  def test_unreadable_base_tip_stops_without_merging(spec: bool, problem: str) -> None:
      # request_fails: gh.branch_fails、no_base_ref: del gh.view["baseRefName"]、blank_base_ref: ""、ほかは gh.branch
      ...
      assert result["outcome"] == "stopped" and result["stop_reason"].startswith("external:")
      assert result["merged"] is False and "base_moved" not in result and gh.writes() == []

  def test_base_branch_name_with_a_slash_is_read_whole() -> None:
      gh = FakeGh()
      gh.view["baseRefName"] = "release/1.0"
      gh.tips = {"release/1.0": BASE}
      assert mod.finalize(record(), "状況", checks(), runner=gh)["outcome"] == "no_fix_needed"
      assert gh.branch_requests()[0] == f"repos/{REPO}/branches/release/1.0"

  def test_retargeted_base_is_compared_with_the_new_base_branch() -> None:
      gh = FakeGh()
      gh.view["baseRefName"] = "develop"
      gh.tips["develop"] = NEW_BASE
      result = mod.finalize(record(), "状況", checks(), runner=gh)
      assert result["base_moved"] == {"ref": "develop", "verified": BASE, "current": NEW_BASE}
      assert gh.writes() == []
  ```

- [ ] **Step 3: 失敗を確かめる**

  Run: `uv run pytest -q .agents/skills/review-fix-planning/tests/test_finalize.py`
  Expected: FAIL。新しいテストに加え、`checks()` に `base` を足したので、既存の多くも `check_evidence` で止まって失敗する

- [ ] **Step 4: 実装する**

  - `FIELDS` に `"baseRefName"`。`Stop` に `base_moved` を足し、docstring に意味（待っても解消しない。検証し直して記録を作り直す）を書く
  - `check_evidence`: 先頭で `base` が `str` で `FULL_SHA` に合うことを確かめ、キーの集合を `{"head", "base", "commands"}` にする
  - `check_base`: `view["baseRefName"]` が空でない `str`、応答がオブジェクトで `name` が同じ、`commit.sha` が `FULL_SHA` に合う、を確かめ、満たさなければ `Stop("external: PRのbaseブランチの先端を確認できない")`。先端が `verified` と違えば `base_moved` 付きの `Stop`。docstring に、`baseRefOid` を使わない理由と、名前の照合の理由を書く
  - `finalize`: `--spec-commit` が無い経路は、`check_ci` の後・投稿の前に `step = "base before posting"` で `check_base`。マージの直前は、読み直した PR の `check_ci` の後に `step = "pre-merge base"` で `check_base`。`except Stop` で `base_moved` を結果に写す。モジュールの docstring に base の照合を書く

- [ ] **Step 5: 通ることを確かめる**

  Run: `uv run pytest -q .agents/skills/review-fix-planning/tests .agents/skills/pr-review-fix-loop/tests`
  Expected: 全件 PASS

- [ ] **Step 6: Commit**

  ```bash
  git add .agents/skills/review-fix-planning/scripts/finalize.py .agents/skills/review-fix-planning/tests/test_finalize.py
  git commit -m "fix(review-fix-planning): stop finalize.py when the base moved after verification (#196)"
  ```

### Task 2: Spec の commit の push の反映待ち（`wait_for: head`）

**テストの要否:** 書く。待てば進む停止と待たない停止の分岐で、手順 7 の扱い（待つか結論 3 か）が変わる。

**Files:**
- Modify: `.agents/skills/review-fix-planning/scripts/finalize.py`（`check_view`、`finalize` の最初の `check_view` の呼び出し、`Stop` の docstring）
- Test: `.agents/skills/review-fix-planning/tests/test_finalize.py`

**Interfaces:**
- Consumes: Task 1 の `Stop`
- Produces: `check_view(view: Mapping[str, Any], head: str, *, allow_merged: bool = False, pushed_from: str | None = None) -> None`。`finalize` は `--spec-commit` の最初の読み取りだけで `pushed_from=reviewed_head` を渡す

- [ ] **Step 1: テストを書く。既存の `test_spec_commit_requires_the_pr_head_to_be_the_spec_commit` はこの 2 つで置き換える**

  ```python
  def test_spec_commit_waits_until_the_pushed_spec_commit_is_the_pr_head() -> None:
      # push の直後は、GitHub がまだ前の head（検証した HEAD）を返すことがある（PR #192）
      gh = spec_gh()
      gh.view["headRefOid"] = HEAD
      first = finalize_spec(gh)
      assert first["outcome"] == "stopped" and first["wait_for"] == "head"
      assert first["stop_reason"].startswith("external:") and first["merged"] is False and gh.writes() == []
      gh.view["headRefOid"] = SPEC_HEAD
      assert finalize_spec(gh)["outcome"] == "no_fix_needed"

  @pytest.mark.parametrize(("state", "head"), [("OPEN", "2" * 40), ("MERGED", HEAD)])
  def test_spec_commit_with_another_head_stops_without_waiting(state: str, head: str) -> None:
      # head が別の commit に動いた。または、Spec の commit の push の前に、検証した HEAD のまま手でマージされた
      gh = spec_gh(state=state)
      gh.view["headRefOid"] = head
      result = finalize_spec(gh)
      assert result["outcome"] == "stopped" and result["stop_reason"].startswith("external:")
      assert "wait_for" not in result and gh.writes() == []
  ```

- [ ] **Step 2: 失敗を確かめる**

  Run: `uv run pytest -q .agents/skills/review-fix-planning/tests/test_finalize.py -k "pushed_spec_commit or another_head"`
  Expected: 1 つ目が FAIL（`wait_for` が無い）、2 つ目の 2 件は PASS

- [ ] **Step 3: 実装する**

  head が違い、`pushed_from` と同じで state が `OPEN` なら `Stop("external: PRのheadがまだ検証したHEADのまま（Specのcommitのpushが反映される前）", wait_for="head")`。それ以外は今の `Stop`。`Stop` の docstring の `wait_for` に `head` を足す

- [ ] **Step 4: 通ることを確かめる**

  Run: `uv run pytest -q .agents/skills/review-fix-planning/tests .agents/skills/pr-review-fix-loop/tests`
  Expected: 全件 PASS

- [ ] **Step 5: Commit**

  ```bash
  git add .agents/skills/review-fix-planning/scripts/finalize.py .agents/skills/review-fix-planning/tests/test_finalize.py
  git commit -m "fix(review-fix-planning): wait for the pushed Spec commit to become the PR head (#196)"
  ```

### Task 3: 手順書（review-fix-planning・pr-review-fix-loop）

**テストの要否:** 書かない。文書だけの変更。差分を読み、Task 1・2 の結果のキー・照合の時点・停止理由と一致することを確かめる。

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（結論 2 の手順 2・5・6・7、手順 9 の後のやり直しの段落、結論 3 の外部障害、合理化の表、Red flags）
- Modify: `.agents/skills/review-fix-planning/references/execution.md`（3.1〜3.4、新しい 3.5）
- Modify: `.agents/skills/pr-review-fix-loop/SKILL.md`（24 行、手順 3、「最終化の停止」）

- [ ] **Step 1: `SKILL.md` の結論 2 を直す（Spec の D-6・D-7・D-8）**
  - 手順 2: 取り直した先端の SHA を検証の記録の `base` にする。head の祖先でなければ、その SHA を merge したツリーで検証してそのコマンドを記録する
  - 手順 5: 本文の検証の状況に、検証したツリーと `base` を書く
  - 手順 6: 投稿の直前と push の直前に base を取り直し、先端が `base` と違えば、投稿・push をせずに手順 2〜5 を新しい先端でやり直し、Spec を直して `git -C "$MAIN_ROOT" commit --amend` で作り直し、commit の後の確認から続ける。結論 1 に切り替えるときは Spec の commit を結論 3 の方法で取り消す
  - 手順 7: helper が投稿の前とマージの直前に base を照合すること、`base_moved` は待たずに `execution.md` 3.4 節のとおり検証し直して再実行すること
  - 手順 9 の後: やり直しは合わせて 3 回まで、超えたら結論 3。検証し直さずに `base` だけを書き換えない。既知の制限は `execution.md` 3.5 節
  - 結論 3 の外部障害、合理化の表、Red flags に 1 行ずつ
- [ ] **Step 2: `execution.md` を直す**
  - 3.1: 検証の記録に `base`（意味と、どの検証のコマンドを書くか）
  - 3.2: create-reso-world の 2〜4 に、投稿・push の直前の再確認、`wait_for: head`、マージの直前の照合。resoloop の文に、投稿の前とマージの直前の照合
  - 3.3: base の照合の箇条（時点、`baseRefOid` を使わない、マージ済みでは照合しない）と、`--spec-commit` の head の箇条
  - 3.4: `wait_for` の `head`。`base_moved` の箇条（検証し直し、記録の作り直し、create-reso-world の補足のコメントの形、それ以外の本文の更新、同じ判断の記録での再実行）
  - 3.5（新規）既知の制限
- [ ] **Step 3: loop の `SKILL.md` を直す（Spec の D-10）**
  - 24 行: PR への書き込みに、review-fix-planning の補足のコメントを含める
  - 手順 3: `finalize.py` の `wait_for`・`base_moved` による再実行は計画の中で行い、終わってから `cycle-end` を呼ぶ
  - 「最終化の停止」: `base_moved` では検証し直し、`--round-dir` の検証記録を作り直してから再実行する
- [ ] **Step 4: 確かめる**
  - `git diff` を読み、キー名（`base`・`base_moved`・`ref`・`verified`・`current`）、`wait_for` の `head`、照合の時点、`baseRefOid` を使わないこと、停止理由が Task 1・2 と一致することを確かめる
  - Run: `uv run pytest -q .agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py .agents/skills/pr-review-fix-loop/tests/test_pr_review_fix_loop_skill_contract.py`
  - Expected: PASS（投稿のブロックと共通 context のブロックが崩れていない）
- [ ] **Step 5: Commit**

  ```bash
  git add .agents/skills/review-fix-planning/SKILL.md .agents/skills/review-fix-planning/references/execution.md .agents/skills/pr-review-fix-loop/SKILL.md
  git commit -m "docs(review-fix-planning): recheck the base before posting, pushing and merging (#196)"
  ```

### Task 4: 統合の検証と最終レビュー

**テストの要否:** 新しいテストは無い。検証の入口を実行し、ガードを外した対照で新しいテストの検出力を確かめる。

- [ ] **Step 1: ガードを外した対照** — feature の HEAD から `mktemp -d` の中に `git worktree add --detach` で一時 worktree を作り、`finalize.py` のガードを 1 つずつ外して `test_finalize.py` を実行する。外すもの: (a) `check_base` を何もしない関数に (b) 投稿の前の照合だけ (c) マージの直前の照合だけ (d) `check_base` の先端を `view.get("baseRefOid")` に (e) `check_evidence` の `base` の検査 (f) `check_view` の `pushed_from`。それぞれ、そのガードを確かめるテストが失敗することを記録する。終わったら worktree を外して一時ディレクトリを消す
- [ ] **Step 2: README の「テスト」** — worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を実行し、終了コードとログの要点を記録する
- [ ] **Step 3: 要件の照合** — `review-fix-planning/references/convergence.md` の「3. 検証と閉じ方」に従い、Spec の A-1〜A-5・D-1〜D-11 を commit と Step 1・2 の結果に対応させる
- [ ] **Step 4: 最終レビュー** — ブランチ全体（`origin/main...HEAD`）のレビューを新しいレビュアー 1 つに依頼し、指摘を判定する。直したら関連テストと Step 2 の該当コマンドをやり直す
- [ ] **Step 5: 記録** — この Plan の「完了」に、検証の結果・対照の結果・レビューの判定・所要時間を書いて commit する

## 完了

（Task 4 の後に書く）
