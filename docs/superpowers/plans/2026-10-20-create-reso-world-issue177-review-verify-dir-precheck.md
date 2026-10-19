# Issue #177 review_dir の起動前検査 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者の 2026-10-20 の `/issue-to-pr #177`（Spec の「実行許可」と同じ範囲。マージはしない）

**Goal:** review-verify の `dispatch.py` が、保存できない `review_dir`（root が無い・ディレクトリでない、`verified` がディレクトリでない）を、担当の起動と runner の成果物の作成より前に終了コード 2 で拒否する。

**Architecture:** いまのリンクの検査を `reject_review_links` に分け、`check_review_directories` を「リンク＋種類」の起動前の検査にする。`snapshot_review` は `reject_review_links` だけを呼ぶ。`run_roles.py` は `check_review_directories` を予約の前に呼んでいるので、コードを変えずに同じ検査が効く。

**Tech Stack:** Python 3.14（uv）、pytest、pydantic。テストは偽の adapter と実 Git・実 subprocess

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue177-review-verify-dir-precheck-design.md`

## Global Constraints

- stderr の分類の文（パスを含めない）: `review_dir must be an existing directory`、`verified must be absent or a directory`
- 拒否は `ValueError`（`main` が終了コード 2）。保存先を作らない・消さない・置き換えない
- 判定は `lstat`（リンクを辿らない）。リンクの拒否の文 `review_dir and verified must not be symlinks` と、その対象（root・全祖先・`verified`）を変えない
- `self` の割り当てにも適用する
- `run_roles.py` のコードと review-fix-planning の手順書は変えない
- テストは AGENTS.md「テストの採用基準」に従う。文面の一致のテストを足さない

## Review Focus

1. root の祖先が通常ファイル（`NotADirectoryError`）→ root が無いのと同じく終了コード 2。Task 1 の `lstat` の `OSError` の扱いで決まる（テストは root が通常ファイルの場合で代表する）
2. 起動の後に `verified` が通常ファイルになる → accept が終了コード 1 で `verified` を列挙し、traceback にならない。Task 1 の Step 1 の 2 つ目のテスト
3. `self` の割り当てでも成果物（`main-run`）を作らない。Task 1 の Step 1 の parametrize
4. `run_roles.py` の 1 回枠が消費されない（`activities` が空のまま）。Task 2
5. 既存の `verified/` ディレクトリ（前回の結果を含む）は通る。既存テスト `test_unchanged_existing_results_and_temporary_probe_outputs_are_allowed` で守る（変更しない）

## 要件と Task の対応（実装前の照合）

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| A-1 起動・成果物の前に検査、リンクの拒否を保つ | Task 1 | 3 つの異常 × 2 割り当てで adapter 未起動・`main-run` 無し | 新しいテスト、既存のリンクのテスト |
| A-2 非 0・状態不変・単一の異常 | Task 1 | 終了コード 2、`managed_state(tmp_path)` が前後で同じ | 新しいテスト |
| A-3 暗黙に作らない・消さない | Task 1 | 同上（root・通常ファイルが残る） | 新しいテスト |
| A-4 正常系 | Task 1 | 既存の受け取りのテストが通る | 既存テスト |
| A-5 起動後の拒否・照合・停止確認 | Task 1 | 既存テストと、起動後の `verified` の通常ファイル | 既存＋新しいテスト |
| A-6 手順書 | Task 3 | `fix-check.md` の 19・36・41 行の記述 | 差分の確認 |
| D-1 の `run_roles.py` への効果 | Task 2 | 予約の前の `ValueError`、adapter 未起動 | 新しいテスト |

共有する条件は「`check_review_directories` が起動・予約の前に呼ばれること」だけで、Task 1 の関数を Task 2 が使う。統合の確認は最後の全体の検証（Task 4）で、両方のテストを同じ HEAD で実行して行う。

## 実行方式

`superpowers:executing-plans`（このセッションが inline で実装する）。`implement_task.py check` が `self=true`、Task は 4 つで、Task 2 は Task 1 の関数に依存し、同じ領域の逐次の変更である。

## 実行予算

- 全体の能動時間: 150 分（Task 4 つ、似た規模の #145・#139 の実績は 60〜120 分）。ledger は `/workspaces/reso-world/tmp/agents/issue-177.2nm8561f/budget.jsonl`
- phase の目安: Spec・Plan 30 分、実装 Task 1〜3 で 45 分、検証 Task 4 で 30 分、PR 15 分
- worker: 起動しない（inline）。全体のテストは同期実行し、`timeout 1800` を付ける
- 再試行の上限: 同じ失敗の再試行は 1 回まで。テストの不安定（既知の #128 など）は 1 回だけ再実行し、再発したら `systematic-debugging` で調べる
- checkpoint: 実装の完了時、検証の完了時、予算の 50%（75 分）・100%
- 縮小・方法変更の候補: Task 2 のテストを fixture の都合で書けなければ、`run_roles.run` の代わりに `fix_context` を直接呼ぶテストに縮小する。全体のテストが環境の要因（`check-layout.sh` の既知の失敗など）で失敗したら、対象のテストを個別に実行して原因を切り分け、PR に記録する

## Contingency

- 既存テストが新しい条件で失敗したら、その fixture が存在しない `review_dir` を渡していないかを先に確かめる（`verification_input` 以外にもあれば、同じく作る）
- `run_roles.py` の既存テストが失敗したら、その fixture の保存先の準備を確かめる。`run_roles.py` のコードは変えず、変える必要があれば止まって報告する

---

### Task 1: 起動前の保存先の検査（`dispatch.py`）

**テストの要否:** 書く。起動の前の拒否・状態の不変は、コードを実行して確かめる安全の条件である。

**Files:**
- Modify: `.agents/skills/review-verify/scripts/dispatch.py:205-214`（検査関数と `snapshot_review`）、`:374-381`（`REQUEST_ERRORS`）
- Test: `.agents/skills/review-verify/tests/test_dispatch.py`（fixture `verification_input` と新しいテスト 2 つ）

**Interfaces:**
- Produces: `reject_review_links(root: Path) -> None`（いまの `check_review_directories` の本体。`snapshot_review` が呼ぶ）、`check_review_directories(root: Path) -> None`（`reject_review_links` の後に種類を確かめ、`ValueError` を上げる。`dispatch()` と `run_roles.fix_context` が呼ぶ）

- [ ] **Step 1: 失敗するテストを書く**

  fixture `verification_input` で `(tmp_path / "review").mkdir()` を足す（新しい入力の条件に合わせる）。テストを足す:

  ```python
  @pytest.mark.parametrize("assign", ["probe", "self"])
  @pytest.mark.parametrize(
      "anomaly,reason",
      [
          ("missing", "review_dir must be an existing directory"),
          ("file", "review_dir must be an existing directory"),
          ("verified-file", "verified must be absent or a directory"),
      ],
  )
  def test_unusable_review_directory_is_rejected_before_launch_or_any_state_change(
      dispatch, scenario, tmp_path, managed_state, capsys, anomaly, reason, assign
  ):
      # missing: rmdir。file: rmdir して同じパスに通常ファイル。verified-file: review_dir/verified に通常ファイル
      argv = main_argv(tmp_path, scenario.request, assign)
      before = managed_state(tmp_path)
      assert dispatch.main(argv, adapter_loader=<読み込んだら AssertionError の loader>) == 2
      assert reason in capsys.readouterr().err
      assert managed_state(tmp_path) == before


  def test_accept_lists_a_verified_file_created_after_dispatch(dispatch, scenario, tmp_path, capsys):
      run_dir = run_external(dispatch, scenario, tmp_path, scenario.payload())
      # review_dir/verified に通常ファイルを書いてから accept
      assert accept(dispatch, run_dir) == 1
      # stderr は 1 行で '"verified"' を含む。ファイルの bytes は残る
  ```

  2 つ目は変更の前から通る回帰の防止（D-1 で `snapshot_review` に種類の検査を入れない理由）。

- [ ] **Step 2: 失敗を確かめる**

  Run: `uv run pytest -q .agents/skills/review-verify/tests/test_dispatch.py -k "unusable_review_directory or verified_file_created"`
  Expected: 1 つ目の 6 件が FAIL（終了コード 0 または 1、`main-run` が作られる）。2 つ目は PASS

- [ ] **Step 3: 実装する**

  `reject_review_links` を分け、`check_review_directories` で root を `lstat` して `S_ISDIR` でなければ（`OSError` を含む）`ValueError("review_dir must be an existing directory")`、`root / "verified"` を `lstat` して `FileNotFoundError` か `S_ISDIR` 以外なら `ValueError("verified must be absent or a directory")`。`snapshot_review` の先頭を `reject_review_links(root)` にする。2 つの文を `REQUEST_ERRORS` に足す。docstring に「作成・削除・置換はしない。root は呼び出し側が用意する」を書く。

- [ ] **Step 4: 通ることを確かめる**

  Run: `uv run pytest -q .agents/skills/review-verify/tests`
  Expected: 全件 PASS（新しい 7 件を含む）

- [ ] **Step 5: Commit**

  ```bash
  git add .agents/skills/review-verify/scripts/dispatch.py .agents/skills/review-verify/tests/test_dispatch.py
  git commit -m "fix(review-verify): reject an unusable review_dir before launching fix-check (#177)"
  ```

### Task 2: `run_roles.py` の予約の前に止まること

**テストの要否:** 書く。1 回枠を消費しないことは安全の条件で、D-1 で意図して挙動を変える経路である。

**Files:**
- Test: `.agents/skills/review-fix-planning/tests/test_run_roles.py`

**Interfaces:**
- Consumes: Task 1 の `check_review_directories`（`run_roles.fix_context` が呼ぶ）

- [ ] **Step 1: テストを書く**

  ```python
  @pytest.mark.parametrize(
      "anomaly,reason",
      [("missing", "review_dir must be an existing directory"), ("verified-file", "verified must be absent or a directory")],
  )
  def test_unusable_fix_check_destination_stops_before_reservation_or_launch(inputs, tmp_path, parent, anomaly, reason):
      # missing: fix_input["review_dir"] を存在しない tmp_path / "absent-staging" に（verified_file は元の場所のまま）
      # verified-file: Path(fix_input["review_dir"], "verified") に通常ファイル
      adapter = FakeAdapter()
      with pytest.raises(ValueError, match=reason):
          launch(inputs, tmp_path, config("a", "b"), adapter_loader=adapter)
      assert adapter.requests == []
      assert json.loads(planning.read_text())["activities"] == []
      assert not (tmp_path / "run").exists()
      assert not planning.with_suffix(".json.review-lock").exists()
  ```

- [ ] **Step 2: 通ることを確かめる（Task 1 の後なので PASS）**

  Run: `uv run pytest -q .agents/skills/review-fix-planning/tests`
  Expected: 全件 PASS。Task 1 の前の版で失敗すること（予約が足される）は、Task 1 の commit を一時的に外さず、`git stash` も使わずに、Task 4 の対照で確かめる

- [ ] **Step 3: Commit**

  ```bash
  git add .agents/skills/review-fix-planning/tests/test_run_roles.py
  git commit -m "test(review-fix-planning): stop before the reservation for an unusable fix-check destination (#177)"
  ```

### Task 3: fix-check の手順に root の準備の時点を合わせる

**テストの要否:** 書かない。文書だけの変更。代わりに差分を読み、`dispatch.py` の検査・cycle の保存先の時点と一致することを確かめる。

**Files:**
- Modify: `.agents/skills/review-verify/references/fix-check.md:19`、`:36`、`:41`

- [ ] **Step 1: 19 行に、PR の照合と保存先のリンクの確認の後、dispatch の前に `OUTPUT_REVIEW_DIR` を作ること（cycle の「新規成果物の保存先」と同じ時点）、`verified/` は作らなくてよいこと、起動の後に作った保存先は受け取れないことを書く**
- [ ] **Step 2: 36 行に、dispatch が起動の前に root が既存のディレクトリで `verified` が無いかディレクトリであることを確かめ、満たさなければ担当も成果物も作らず、保存先を作らないことを書く**
- [ ] **Step 3: 41 行の終了コード 2 に、保存先の不備（root が無い・ディレクトリでない、`verified` がディレクトリでない）を含める**
- [ ] **Step 4: `git diff` を読み、Spec の D-5 と一致することを確かめて commit**

  ```bash
  git add .agents/skills/review-verify/references/fix-check.md
  git commit -m "docs(review-verify): prepare the fix-check review_dir before dispatch (#177)"
  ```

### Task 4: 統合の検証

**テストの要否:** 新しいテストは無い。検証の入口を実行する。

- [ ] **Step 1: 変更前との対照** — `git worktree add --detach` で `origin/main` の一時 worktree を `/tmp` の一意のディレクトリに作り、Task 1・2 の新しいテストのファイルだけを写して実行し、Task 1 の 6 件と Task 2 の 2 件が失敗することを確かめる。確かめたら worktree を消す
- [ ] **Step 2: README の「テスト」** — worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を実行し、終了コードとログを記録する
- [ ] **Step 3: 要件の照合** — Spec の A-1〜A-6 と D-1〜D-6 を、Task の commit と Step 1・2 の結果に対応させ、この Plan の「完了」に書く

## 完了

（実装後に記録する）
