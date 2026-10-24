# Issue #241 finalize.py の比較の失敗を待てば進む停止にする Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/241

**Goal:** Spec の commit が PR の head になった後の比較の API の失敗を `wait_for: compare` にし、`gh` の失敗の要点を結果の `error_detail` に残し、2 つの手順書の食い違いをなくす。

**Architecture:** `finalize.py` の `check_spec_change` で `run_gh` の失敗だけを `Stop(wait_for="compare")` にする。`Stop` に `detail` を足し、`failure_detail()` で 1 行・500 文字・トークンを伏せた要点を作って、`finalize` が結果の `error_detail` に写す。手順書は execution.md 3.3・3.4 節、review-fix-planning の結論 2 の手順 7、pr-review-fix-loop の「最終化の停止」と「最終報告」を直す。

**Tech Stack:** Python 3.14（uv）、pytest、偽の gh（`test_finalize.py` の `FakeGh`）

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue241-finalize-compare-wait-design.md`

## Global Constraints

- 待つのは、比較の API の `run_gh` の失敗（`gh` の非 0 の終了）だけ。JSON の不正は `external:`、応答の形の違いは `environment:` で、どちらも待たない（D-241-2）
- `wait_for` の新しい値は `"compare"`（D-241-1）
- `stop_reason` に `gh` の出力を入れない。要点は結果のキー `error_detail` に入れる（D-241-3）
- `error_detail`: 空白・改行を 1 つの空白にまとめ → 印字できない文字を除く → `(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+` を `[REDACTED]` に置き換える → 500 文字に切る（D-241-4）
- `error_detail` を入れるのは、比較の `wait_for: compare`、`finalize` の `except poster.CommentError`、`check_merge_parent` の commit の取得の失敗の 3 か所だけ（D-241-5）
- テストは AGENTS.md の「テストの採用基準」の S だけ。テスト用のトークンは実行時に組み立てる（AGENTS.md「push の前の秘密情報の検査」）
- 文書の文言を照合するテストと GitHub Actions は足さない

## Review Focus

- 比較の失敗が、PR がマージ済み（手動マージ・Issue の更新の再開）のときにも `wait_for: compare` になり、再実行で Issue の更新だけに進むこと（書き込みはマージをしない）。実装は open と同じ経路なので、Task 1 の確認で手で確かめる
- 比較の失敗で止まったときに、投稿・マージが一度も起きないこと（Task 1 のテストが `gh.writes() == []` で確かめる）
- 比較の JSON の不正（`gh` は成功）を `wait_for` にしないこと（Task 1 の確認で手で確かめる）
- `error_detail` が改行を含む標準エラーでも 1 行になること（Task 1 の追加テストの標準エラーに改行を入れる）
- `stop_reason` が今の決まった文のまま、判断の記録の検査（制御文字・`<!--` の禁止）を通ること（Task 1 の追加テストが `stop_reason` に標準エラーが入らないことを確かめる）

## 要件・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1 比較の失敗 → `wait_for: compare`、再実行でマージ | Task 1 | 1 回目 `stopped`・`compare`・`merged: false`・書き込みなし、2 回目 `no_fix_needed`・マージと close | 置き換えたテスト |
| 2 応答の形の違いは待たない | Task 1 | `environment:`（既存） | 既存の `test_spec_commit_compare_must_be_one_spec_file_on_the_reviewed_head` |
| 3 `error_detail` が残り、トークンを伏せ、`stop_reason` に入らない | Task 1 | `error_detail` に要点、トークンが結果に無い | 追加テスト |
| 4 手順書の食い違いが無い | Task 2 | 3 つの文書の記述が新しい停止と `error_detail` を書き、計画の中の再実行と run の後の回復を分ける | `git diff` の確認、最後のブランチ全体のレビュー |
| 5 README の入口で失敗が無い | 統合（このセッション） | 3 つのコマンドの終了コード 0 | README の「テスト」の入口 |

共有する前提: `wait_for: compare` と `error_detail` の意味は Task 1 の実装が決め、Task 2 の文書はそれを書く。統合の確認（Task 2 の後）で、文書の記述が実装の挙動（どの停止に `error_detail` が付くか、待つ条件）と合うことを、このセッションが `finalize.py` と見比べて確かめる。

## 実行方式

inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true で、Task は 2 つ、Task 2 は Task 1 の挙動をそのまま書く（Spec D-241-8）。

## 実行予算

- 全体の能動時間: 240 分（実装と文書 45 分、検証 15 分、PR 作成 10 分、ループ 最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 15 分）＝ 180 分）。ledger: `/workspaces/reso-world/tmp/agents/issue-241.ftivqlbo/budget.jsonl`
- phase の目安: 準備（Spec・Plan）20 分、Task 1 25 分、Task 2 20 分、検証・PR 25 分、ループ 150 分
- worker: 実装はこのセッション（worker なし）。ループのレビュアーは `inspect` の期限 2700 秒（runner が守る）。無進捗の打ち切りは pr-review-fix-loop の「監視」（10 分間隔で 2 回変わらなければ stall として報告）
- 再試行の上限: 同じ失敗の再試行は 1 回まで（テストの失敗、`gh` の失敗、ループの段の失敗）。`finalize.py` の `wait_for` の待ちは 15 分を期限にする
- checkpoint: Task 2 の後（実装の完了）、PR の作成の後、予算の 50%（120 分）・100%、ループの各サイクルの後
- 縮小・切り出し・方法変更の候補: `check_merge_parent` の `error_detail` を外す（D-241-5 の 3 か所目）、手順書の変更を「最終化の停止」と execution.md 3.4 節だけに絞る、ループで収束しなければ上限で止めて報告する

---

### Task 1: 比較の失敗を待てば進む停止にし、`gh` の失敗の要点を残す

テスト: 要る。比較の失敗のテストは、実際に起きた気付けない不具合（修正不要の PR がマージされない）の再発防止、トークンを伏せるテストは秘密情報の漏れの防止で、どちらも S（Spec D-241-7）。

**Files:**
- Modify: `.agents/skills/review-fix-planning/scripts/finalize.py`（`Stop` `:66-89`、`check_spec_change` `:219-226`、`check_merge_parent` `:276-281`、`finalize` の `except` `:503-516`。定数は `FULL_SHA` の近く）
- Test: `.agents/skills/review-fix-planning/tests/test_finalize.py`（`FakeGh` `:102-231`、`:666-671` のテストの置き換え）

**Interfaces:**
- Produces: `Stop(reason, *, wait_for=None, base_moved=None, merge_parent=None, detail: str | None = None)`、`failure_detail(error: Exception) -> str`、`DETAIL_LIMIT = 500`、結果のキー `error_detail: str`（入るのは上の 3 か所の停止だけ）、`wait_for` の値 `"compare"`

- [ ] **Step 1: 偽の gh に `stderr` を足し、比較の失敗のテストを置き換える**

`FakeGh.__init__` に `self.stderr = "fake failure"` を足し、`__call__` の最後の `"fake failure" if code else ""` を `self.stderr if code else ""` にする。`test_spec_commit_compare_request_failure_is_external_and_does_not_merge` を次に置き換える。

```python
def test_spec_commit_compare_failure_after_the_push_waits_and_the_rerun_merges() -> None:
    """#241: PRのheadがSpecのcommitになった直後に、GitHubの比較だけが失敗した（PR #240）。
    マージせずに待てば進む停止にし、gh の応答の要点を残す。比較が戻った同じ入力の再実行でマージする。"""
    gh = spec_gh()
    gh.compare_fails = True
    gh.stderr = "gh: Not Found (HTTP 404)"
    first = finalize_spec(gh)
    assert (first["outcome"], first["merged"], first.get("wait_for")) == ("stopped", False, "compare")
    assert first["stop_reason"].startswith("external:") and first["error_detail"] == "gh: Not Found (HTTP 404)"
    assert gh.writes() == []
    gh.compare_fails = False
    second = finalize_spec(gh)
    assert second["outcome"] == "no_fix_needed" and "wait_for" not in second and "error_detail" not in second
    assert [call[1:3] for call in gh.writes()] == [("pr", "merge"), ("issue", "close")]
```

- [ ] **Step 2: トークンを伏せるテストを足す（`test_issue_update_failure_is_reported_after_real_merge` の後）**

```python
def test_gh_failure_detail_is_kept_without_tokens_or_stop_reason() -> None:
    """gh の失敗の要点は結果に残すが、トークンの形の文字列は伏せる。stop_reason は判断の記録・PRのコメントに
    写されうるので、gh の出力を入れない。"""
    # gitleaks に検出されないよう、トークンの形の偽の値は実行時に組み立てる
    token = "_".join(["ghp", "Ab3" * 12])
    gh = FakeGh()
    gh.login_fails = True
    gh.stderr = f"HTTP 401: Bad credentials\n(token {token})"
    result = mod.finalize(record(), "状況", checks(), runner=gh)
    assert result["outcome"] == "stopped" and result["stop_reason"].startswith("external:")
    # authenticated_login は gh の標準エラーに前置きを付ける
    assert result["error_detail"] == "cannot read the authenticated login: HTTP 401: Bad credentials (token [REDACTED])"
    assert token not in json.dumps(result) and "Bad credentials" not in result["stop_reason"]
    assert gh.writes() == []
```

- [ ] **Step 3: 2 件が失敗することを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests/test_finalize.py -k "compare_failure_after_the_push or detail_is_kept" -q`
Expected: 2 failed（`wait_for` が無い、`error_detail` が無い）

- [ ] **Step 4: `finalize.py` を実装する**

- `DETAIL_LIMIT = 500` と、トークンの形の正規表現の定数を足す（Global Constraints の形）
- `failure_detail(error: Exception) -> str`: Global Constraints の順で作る
- `Stop.__init__` に `detail: str | None = None` を足して `self.detail` に入れ、docstring に `wait_for` の `compare`（push した S が PR の head になった後に、GitHub の比較の取得が失敗した）と `detail` を足す
- `check_spec_change`: `poster.run_gh(...)` だけを `try` で囲み、`except poster.CommentError as error` で `Stop("external: GitHubの比較を取得できない（Specのcommitのpushの直後は比較が遅れることがある）", wait_for="compare", detail=failure_detail(error))` を `from None` で上げる。`load_json` と形の検査は `try` の外。docstring に、呼ぶ前に PR の head が S と確かめていることと #241 を書く
- `check_merge_parent`: `except poster.CommentError as error` で `detail = failure_detail(error)` を取り、読めないときの 2 つの `Stop(unreadable, merge_parent=found)` に `detail=detail`（取得していなければ None）を渡す
- `finalize`: `except Stop` で `error.detail` が None でなければ `result["error_detail"]` に入れる。`except poster.CommentError as error` で `result["error_detail"] = failure_detail(error)` を足す（`stop_reason` は今のまま）
- モジュールの docstring に、`gh` の失敗の要点を `error_detail` に残し、`stop_reason` には入れないことを 1 行足す

- [ ] **Step 5: テスト全体と静的検査を通す**

Run: `uv run pytest .agents/skills/review-fix-planning/tests/test_finalize.py -q && uv run ruff check .agents/skills/review-fix-planning && uv run ruff format --check .agents/skills/review-fix-planning`
Expected: 66 passed、ruff の指摘なし

- [ ] **Step 6: Review Focus の手の確認（一時的なスクリプト。コミットしない）**

`/workspaces/reso-world/tmp/agents/issue-241.ftivqlbo/` に置いたスクリプトで、(a) `spec_gh(state="MERGED")` で比較だけを失敗させると `wait_for: compare`・`merged: true`・書き込みなし、戻した再実行は `no_fix_needed` で書き込みは Issue の close だけ、(b) `gh.compare` を JSON でない応答にする（`__call__` の比較の分岐が文字列を返すよう一時的に差し替える）と `wait_for` が無い `external:`、を確かめ、出力を `repro-after.log` に残す。`repro.py` を再実行した出力も同じ log に残す

- [ ] **Step 7: Commit**

```bash
git add .agents/skills/review-fix-planning/scripts/finalize.py .agents/skills/review-fix-planning/tests/test_finalize.py
git commit -m "fix(review-fix-planning): wait when the Spec commit comparison fails after the push (#241)"
```

### Task 2: 手順書を新しい停止と `error_detail` に合わせ、食い違いをなくす

テスト: 要らない。文書の文言で、テストにすると F（固定値）になる。代わりに `git diff` で Spec の設計 3 と見比べ、`scripts/check-layout.sh` を通す。

**Files:**
- Modify: `.agents/skills/review-fix-planning/references/execution.md`（3.3 節 `:156`、3.4 節 `:167` と `:183` の `gh`・API の失敗の行）
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（結論 2 の手順 7 `:263`）
- Modify: `.agents/skills/pr-review-fix-loop/SKILL.md`（「最終化の停止」 `:109`、「最終報告」 `:122-133`）

**Interfaces:**
- Consumes: Task 1 の `wait_for: "compare"` と `error_detail`（入る停止と形）

- [ ] **Step 1: execution.md を直す**

- 3.3 節の `wait_for: head` の項の後に 1 項: `--spec-commit` で、PR の head が S になった後に GitHub の比較の取得（`gh`）が失敗したら、`wait_for: compare` で止まる（push の直後は比較が遅れることがある。#241）。応答の形が違うときは今までどおり `environment:` で、待たない
- 3.4 節の `wait_for` の項: 少し間を置く対象に `compare`（push した S が PR の head になった後に、GitHub の比較を取得できなかった）を足す
- 3.4 節の「`gh`・API の失敗は `external:`」の行の後に 1 項: `gh` の失敗で止まったとき（`external:` と、比較の `wait_for: compare`、`merge_parent` の commit の取得の失敗）は、`error_detail` に `gh` の標準エラー（無ければ標準出力）か、応答を使えなかった理由の要点が入る（1 行・500 文字まで・GitHub のトークンの形は `[REDACTED]`）。停止の報告に書き、判断の記録の `stop_reason` には写さない（`stop_reason` は helper の文のまま）

- [ ] **Step 2: review-fix-planning の SKILL.md の手順 7 に 1 文足す**

最後の「それ以外の `stopped` は結論 3 にする（…）」の後に: 結果に `error_detail`（`gh` の失敗の要点）があれば停止の報告に書き、判断の記録の `stop_reason` には写さない（[execution.md](references/execution.md) 3.4 節）。

- [ ] **Step 3: pr-review-fix-loop の SKILL.md を直す**

- 「最終化の停止」の最初の文を、次の 2 文に置き換える: 計画の中の finalize.py の再実行は、review-fix-planning の結論 2 の手順 7 のとおり（`wait_for` は待って同じ入力で、`base_moved` は検証し直してから再実行し、それ以外の `stopped` は結論 3 にして `cycle-end` に渡す）。run が `stopped` で終わった後に、同じ HEAD のまま原因（一時的な API の失敗など）が解消したら、利用者の指示で、`cycle-end` に渡した `--round-dir` の記録・本文・検証記録で finalize.py を再実行する（`.agents/skills/review-fix-planning/references/execution.md` の 3 章。手動マージ済みでも Issue の更新だけを行う）。続く `merged`・`base_moved`・`merge_parent` の文は変えない
- 「最終報告」の `stop_reason` の項に、finalize の結果の `error_detail`（あれば）を足す

- [ ] **Step 4: 差分と配置を確かめる**

Run: `git diff -- .agents/skills/review-fix-planning/references/execution.md .agents/skills/review-fix-planning/SKILL.md .agents/skills/pr-review-fix-loop/SKILL.md && bash scripts/check-layout.sh`
Expected: 差分が Spec の設計 3 の項目だけ、`check-layout.sh` が終了コード 0

- [ ] **Step 5: 統合の確認**

`finalize.py` の `Stop(..., wait_for="compare")` を上げる条件と `error_detail` を入れる 3 か所を、execution.md 3.3・3.4 節の記述と見比べ、食い違いが無いことを確かめる。review-fix-planning の手順 7 と pr-review-fix-loop の「サイクル」の 3・「最終化の停止」を続けて読み、計画の中の再実行（`wait_for`・`base_moved`）と run の後の回復（利用者の指示）が同じに書かれていることを確かめる

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/review-fix-planning/references/execution.md .agents/skills/review-fix-planning/SKILL.md .agents/skills/pr-review-fix-loop/SKILL.md
git commit -m "docs(review-fix-planning): document the compare wait and error_detail, align the finalize stop (#241)"
```

### 検証（統合）

README の「テスト」の入口（ワールドの行を除く）を worktree のルートで実行し、各コマンドの argv・終了コード・ログを `/workspaces/reso-world/tmp/agents/issue-241.ftivqlbo/` に残す。`--merge` のため、検証した HEAD・`git status --porcelain` が空だったこと・`finalize.py` の `--checks-file` の形のファイルも同じ場所に作る。

```bash
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
uv run pytest tests/skills .agents/skills .agents/scripts tools
```

### contingency

- 既存のテストが `error_detail` のキーで壊れたら、テストの期待値ではなく、キーを足す経路（3 か所だけ）を見直す
- ループの `_read_finalize` が新しいキーを拒否したら（確認では拒否しない）、止まって原因を Spec の確認した事実に足す
- README の入口の失敗がこの変更と無関係なら、`origin/main` の同じコマンドで再現するかを確かめ、再現すれば既存の失敗として PR 本文に書く
