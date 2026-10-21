# Issue #221: finish --abort がマージ済みの事実を失わない Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** finalize がマージした後にループが止まり `finish --abort` で終えても、run の結果と issue-to-pr の最終報告がマージ済みの事実を失わず、PR を読めないときは未マージとも書かない。

**Architecture:** `finish --abort` が PR の実際の状態（`GitHub.pull`）と、司令塔が `--finalize-result` で渡す最後の finalize の結果を読み、`RunResult.merged` を finalize の `merged` と同じ意味の 3 値（true・false・null）にする。読む側（`records.md`・pr-review-fix-loop の SKILL.md・issue-to-pr の表）を 3 値に合わせ、`cycle-end` が finalize の後に止まったときの段を SKILL.md に足す。

**Tech Stack:** Python 3.14、pydantic 2、pytest（偽の gh とローカルの bare リポジトリの fixture）

**Spec:** `docs/superpowers/specs/2026-10-21-create-reso-world-issue221-abort-merged-state-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/221
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-221-abort-merged-state`（branch `fix/issue-221-abort-merged-state`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr … --merge --assign implement=self`。PR の作成後に PR 修正ループを回し、修正不要ならループの `finalize.py` がマージする）
- 実行方式: inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true で、Task 1 は `loop.py` とそのテストを TDD の順に逐次変更し、Task 2 の文書は Task 1 で決まる挙動を書き、Task 3 は両方を照合する統合確認である。委譲しても並行できず、文脈を渡す手間が上回る。独立したレビューは Task 3 の最後のブランチ全体のレビュー（新しいコンテキストのサブエージェント）で受ける
- 検証のログ・実行の記録（ledger `budget.jsonl` を含む）: `/workspaces/reso-world/tmp/agents/issue-221.439bd74f/`（commit しない。worktree の中には置かない）
- 基準: `origin/main` の `b741085`（基準の検証は `baseline/` の下）

## Global Constraints

- `RunResult.merged` は `bool | None`。null を書くのは `finish --abort` だけで、`cycle-end` が保存する `merged`（`planning.merged`・`result.merged`）は今までどおり PR の実際の状態の真偽値（Spec の設計 1・6）
- `finish --abort` の `merged`: PR を読めたら PR の `merged`。ただし finalize の結果が `true` で PR が未マージなら null。読めなければ finalize の結果の `merged`、渡されていなければ null（D-221-4）
- PR の読み取りは `GitHub.pull`（`gh api repos/<repo>/pulls/<N>`）。`LoopError`・`OSError` は「読めない」として abort を続ける（D-221-3・D-221-8）
- `--finalize-result` は `--abort` と一緒のときだけ。誤りは `_read_finalize` と同じ検査で、run を変えずに終了コード 2（`arguments`）（D-221-2・D-221-8）
- PR の状態だけで決められなかったとき（読めない・食い違い）だけ、`notes` に `<時刻> finish --abort: <理由>` を足す（D-221-7）
- テストは偽の gh とローカルの Git の fixture だけを使う。実際の GitHub を読ませない（既存の abort の呼び出しにも偽の gh を渡す）。文書の文言を照合するテストは作らない（AGENTS.md「テストの採用基準」）
- `cycle-end`・`finalize.py`・review-fix-planning は変えない

## Review Focus

- GitHub の障害が続く間の abort（Issue の場面で PR も読めない）: abort は止まらず、渡した finalize の `true` を保つ → Task 1 の `test_abort_after_a_finalize_merge_keeps_the_merge[pr-unreadable]`
- gh を起動できない（`OSError`）: traceback で止まらず、読めないとして扱う → Task 1 の `test_abort_treats_a_gh_that_cannot_start_as_unreadable`
- 資源の停止を確認できない run の abort（`held`）: `result` を保存してから終了コード 7 で止まり、PR を読めたときは `notes` も変えない → 既存の `test_unconfirmed_after_run_keeps_outputs_and_lock_until_the_operator_confirms[finish_abort-*]`（Task 1 で偽の gh を渡す。`held_state` が `notes` を含めて比べる）
- 形の違う・存在しない finalize の結果ファイル: run を変えず、PR も読まずに終了コード 2 → Task 1 の `test_finalize_result_is_only_for_abort_and_must_be_a_finalize_result`
- finalize を渡さない abort の後に、PR が手でマージされていた（`cycle-begin` の `pr_not_open` の後など）: PR を読めれば `true` → Task 1 の `test_abort_records_the_merge_state_it_observed[merged]`

## 要件と Task・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. finalize のマージの後に `cycle-end` が止まって abort しても `merged: true`。報告の手順もマージ済みを失わない | Task 1（コード）、Task 2（報告の手順）、統合は Task 3 | 再現の手順で、PR を読める・読めないの両方で `finish` の出力と run.json の `merged` が `true`。issue-to-pr の表のループのエラーの行が、run の `true` を使う | Task 1 の Step 3（修正前は失敗）・Step 5、Task 3 の Step 1（古い判定に戻すと落ちる対照）・Step 2 |
| 2. PR も finalize の観測も無ければ null で、`false` にしない | Task 1、Task 2 | `unreadable`・`unreadable-finalize-null` が null。文書が null を未マージと書かない | Task 1 の Step 5、Task 3 の Step 1・Step 2 |
| 3. マージしていない run の abort は `false`。正常な `finish` と `cycle-end` の照合は変わらない | Task 1 | `open` 系の組み合わせが `false`、`test_abort_needs_a_classified_reason` が `false`、既存の loop のテストが通る | Task 1 の Step 5、Task 3 の Step 4 |
| 4. 偽の gh とローカルの Git の fixture | Task 1 | 新しいテストは `env`・`kit` の fixture だけを使い、`env.gh.calls` 以外の gh を呼ばない | Task 1 の Step 5、Task 3 の Step 2 |
| 5. 読む側が 3 値に合う。README の入口で失敗が無い | Task 2、Task 3 | `records.md`・SKILL.md・issue-to-pr の表の記述がコードの挙動と一致。各入口の終了コード 0 | Task 2 の Step 4、Task 3 の Step 2・Step 4 |

共有する前提: `merged` の 3 値の意味と決め方（D-221-4）を、`loop.py`（Task 1）と 3 つの文書（Task 2）が同じに書く。統合担当の Task 3 が、文書の記述をテストの組み合わせの表と照合する（Step 2 のレビューの観点に含める）。

## 実行予算

- Issue 全体の能動時間の予算: 300 分（ledger: `/workspaces/reso-world/tmp/agents/issue-221.439bd74f/budget.jsonl`）。根拠は #220（240 分の予算。runner の判定とテストの変更）。この Issue はコードの変更が小さい代わりに文書が 3 つあり、PR 修正ループ（最大 3 サイクル）を含む
- phase の目安: 準備・調査 45 分（済）、Spec・Plan 35 分、Task 1 40 分、Task 2 20 分、Task 3 45 分（README の入口・対照検証・最後のレビューの待ち）、PR 10 分、PR 修正ループは残り（最大 3 サイクル ×（レビューの期限 45 分＋計画・修正 15 分）のうち、予算に収まる範囲）
- worker は使わない（inline）。最後のレビューのサブエージェントは 1 回だけ起動する。長時間の実行（`run-tests.bash`・pytest 全体）はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 30 分。README の入口は並行させず順に実行する
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・環境の I/O の停止）は 1 回まで。安全の失敗（実際の GitHub への書き込み、実リポジトリ・親の `.venv` の書き換えの疑い、本物の担当の起動）は再試行せず止まる
- checkpoint: Task 1 の後、Task 2 の後、Task 3 の後、ループの各サイクルの後、予算の 50%・100%（100% では停止して報告する）
- 縮小・方法変更の候補: CLI の配線のテスト（Task 1）が引数の解析の都合で書きにくければ、`dispatch` の呼び出しの確認に縮める。README の入口が環境の要因で落ちたら、基準（`b741085`）の同じ実行（`baseline/`）と比べて差分だけを判定する

## Task 1: `finish --abort` が観測したマージ状態を保存する（TDD）

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/tests/conftest.py:166-239`（`FakeGitHub` の `pull_status`）
- Modify: `.agents/skills/pr-review-fix-loop/tests/test_loop_state.py:561-570`（`test_abort_needs_a_classified_reason`）と、その後に新しいテスト
- Modify: `.agents/skills/pr-review-fix-loop/tests/test_loop_review.py:719`・`:878`・`:1051`・`:1077`・`:1726`（`finish(..., abort=...)` に `github=env.github`）
- Modify: `.agents/skills/pr-review-fix-loop/scripts/loop.py:178-183`（`RunResult`）、`:2021-2060`（`finish`）、`:2152-2154`・`:2201-2202`（CLI）

**Interfaces:**
- Produces: `finish(run_dir: Path, *, abort: str | None = None, finalize_result: Path | None = None, github: GitHub | None = None) -> dict[str, Any]`、`_abort_merged(run: RunRecord, github: GitHub, finalize: Mapping[str, Any] | None) -> tuple[bool | None, str | None]`（保存する `merged` と、`notes` に足す理由。PR の状態だけで決まったときは理由が None）、CLI の `finish --finalize-result <file>`、偽の gh の `FakeGitHub.pull_status: int`

**テストの要否:** 書く。abort の結果の分岐（PR を読める・読めない・食い違い × finalize の結果の有無と値）と、引数の検査、CLI の配線を新しく足すので、拒否する入力（引数の誤り）と受け入れる入力を対にして実経路で確かめる（AGENTS.md「テストの採用基準」の「書く」と、実際に起きた不具合の再発防止）。

- [x] **Step 1: 偽の gh に `pull_status` を足す**（`conftest.py`）

`FakeGitHub.__init__` に `self.pull_status = 0` を足し、docstring に「`pull_status` が 0 以外なら、PR の読み取り（`gh api repos/<repo>/pulls/<N>`）がその終了コードで失敗する（GitHub の障害）」を足す。`runner` の pulls の分岐の先頭で、`self.pull_status` が 0 以外なら `subprocess.CompletedProcess(args, self.pull_status, "", "HTTP 502")` を返す。

- [x] **Step 2: 失敗するテストを書く**（`test_loop_state.py`、`test_loop_review.py`）

既存の呼び出しを直す:
- `test_abort_needs_a_classified_reason` の 2 つの `loop.finish` に `github=env.github` を渡し、最後に `assert finished["result"]["merged"] is False` を足す（マージしていない run の abort。受け入れ条件 3）
- `test_loop_review.py` の 5 か所の `loop.finish(run_dir, abort=…)` に `github=env.github` を渡す

`test_abort_needs_a_classified_reason` の後に足す:

- `test_abort_after_a_finalize_merge_keeps_the_merge`（`pr_readable` を `[True, False]`、ids `pr-read`・`pr-unreadable`）: docstring は「finalize がマージした後に cycle-end が GitHub の失敗で止まり、司令塔が abort した（#221 の再現）」。`env.start()` → `reuse_or_run` → `kit.round_record(1, head, "no_fix_needed", [])` を投稿 → `env.gh.merge()` → `kit.finalize_result(tmp_path / "final.json", "no_fix_needed", merged=True)` → `env.gh.login_status = 1` で `loop.cycle_end(run_dir, github=env.github, finalize_result=result)` が `(5, "github")` → `env.gh.pull_status = 0 if pr_readable else 1` → `loop.finish(run_dir, abort="external: GitHub の読み取りが失敗した", finalize_result=result, github=env.github)`

  ```python
  assert (finished["result"]["ended_by"], finished["result"]["merged"]) == ("abort", True)
  run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
  assert run["result"]["merged"] is True
  # PR を読めなかったときだけ、finalize の結果を使った理由を残す
  assert len(run["notes"]) == (0 if pr_readable else 1)
  ```

- `test_abort_records_the_merge_state_it_observed`（パラメータ `pr`・`reported`・`expected`）: `env.start()` → `reuse_or_run`。`pr == "merged"` なら `env.gh.merge()`、`pr == "unreadable"` なら `env.gh.pull_status = 1`。`reported` が「無し」でなければ `kit.finalize_result(tmp_path / "final.json", "no_fix_needed" if reported is True else "stopped", merged=reported, stop_reason=…)`（`stopped` のときだけ `"external: テスト"`）を `finalize_result` に渡して `loop.finish(run_dir, abort="external: テスト", …, github=env.github)`。出力と run.json の `result.merged` がどちらも `expected` で、run の `state` が `ended`

  | id | `pr` | `reported` | `expected` |
  | --- | --- | --- | --- |
  | `open` | open | 無し | False |
  | `open-finalize-false` | open | False | False |
  | `open-finalize-null` | open | None | False |
  | `merged` | merged | 無し | True |
  | `merged-finalize-false` | merged | False | True |
  | `unreadable-finalize-true` | unreadable | True | True |
  | `unreadable-finalize-false` | unreadable | False | False |
  | `unreadable-finalize-null` | unreadable | None | None |
  | `unreadable` | unreadable | 無し | None |
  | `open-finalize-true` | open | True | None |

- `test_abort_treats_a_gh_that_cannot_start_as_unreadable`: `env.start()` の後、`FileNotFoundError` を出す runner の `loop.GitHub(...)` を渡し、`kit.finalize_result(…, "no_fix_needed", merged=True)` を渡した abort が成功して `result.merged is True`、run.json の `notes` が 1 件
- `test_finalize_result_is_only_for_abort_and_must_be_a_finalize_result`: `env.start()` の後、(a) `--abort` なしで正しい結果ファイル、(b) `merged` が `"yes"` の結果ファイル、(c) 存在しないパスを、それぞれ `loop.finish(run_dir, github=env.github, …)` に渡す。3 つとも `(2, "arguments")`。最後に run.json が `state == "running"`・`result is None`、`loop/lock.json` が残り、3 回の呼び出しの間に `env.gh.calls` が増えていない（PR を読む前に止まる）
- `test_cli_finish_abort_passes_the_finalize_result`: `env.start()` → `env.gh.merge()` → `env.gh.pull_status = 1`。`monkeypatch.setattr(loop, "GitHub", lambda: env.github)` の後、`loop.main(["finish", "--run", str(run_dir), "--abort", "external: GitHub の読み取りが失敗した", "--finalize-result", str(result)])` が 0 で、標準出力の JSON の `result.merged` が True（PR を読めないので、渡したファイルが使われたことが分かる）

- [x] **Step 3: 失敗を確かめる**

Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests -q -k "abort or finalize_result"`（worktree のルートで実行）
Expected: 新しいテストと、`github=` を渡した既存のテストが `TypeError`（`finish` が `github`・`finalize_result` を受け付けない）で失敗する。ログは `$SESSION/task1-red.log`

- [x] **Step 4: 実装する**（`loop.py`）

- `RunResult.merged: bool | None`。行の上のコメントに「PR の実際のマージ状態。finish --abort が PR も finalize の結果も読めなければ null（未確認）（#221）」
- `_abort_merged(run, github, finalize)` を `finish` の前に置く。docstring に、意味が finalize の `merged` と同じであること、決め方（Global Constraints の 2 行目）、食い違いで abort を止めない理由（run を終えられず、ロックが残る）を書く。`github.pull` の `LoopError`・`OSError` を捕まえ、理由の注記は `PR の状態を読めない（<理由の先頭 300 文字>）。merged は <finalize の結果のもの|未確認（null）>`、食い違いは `finalize の結果はマージ済みだが、PR は未マージ。merged は未確認（null）`
- `finish(run_dir, *, abort=None, finalize_result=None, github=None)`: 状態の検査の後、`finalize_result is not None and abort is None` なら `LoopError(2, "arguments", "--finalize-result は --abort と一緒のときだけ使う")`。`--abort` の形と「結果が決まっていない」の検査の後に、`_read_finalize(finalize_result)`（渡されたときだけ）→ `_abort_merged(run, github or GitHub(), finalize)` → 理由があれば `run.notes.append(f"{now()} finish --abort: {note}")` → `RunResult(..., merged=merged, ...)`
- CLI: `finish` の parser に `--finalize-result`（`type=Path`、help「--abort のとき、このサイクルで実行した finalize.py の最後の結果ファイル」）。`dispatch` で `finalize_result=args.finalize_result` を渡す

- [x] **Step 5: 通ることを確かめる**

Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests -q`（worktree のルート）
Expected: すべて passed（基準の件数＋新しいテストの件数）、終了コード 0。ログは `$SESSION/task1-green.log`

- [x] **Step 6: Commit**

```bash
git add .agents/skills/pr-review-fix-loop/scripts/loop.py .agents/skills/pr-review-fix-loop/tests/conftest.py \
  .agents/skills/pr-review-fix-loop/tests/test_loop_state.py .agents/skills/pr-review-fix-loop/tests/test_loop_review.py
git commit -m "fix(pr-review-fix-loop): keep the observed merge state when a run is aborted (#221)"
```

## Task 2: 読む側の文書を 3 値に合わせる

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/SKILL.md:76-85`（拒否の表の後に 1 行）、`:97`（abort の項）、`:107` の後（新しい項）、`:124`（最終報告）
- Modify: `.agents/skills/pr-review-fix-loop/references/records.md:55`・`:57`（3 章の表）、`:113`（6 章）
- Modify: `.agents/skills/issue-to-pr/SKILL.md:219-224`（5 章の表）

**Interfaces:**
- Consumes: Task 1 の `finish --abort --finalize-result <file>` と `merged` の決め方（Global Constraints の 2・5 行目）

**テストの要否:** 書かない。文書だけの変更で、文言を照合するテストは AGENTS.md「テストの採用基準」の作らない型 1・4 に当たる。代わりに、`git diff` の確認、`scripts/check-layout.sh`、スキルの frontmatter のテスト（`tests/skills`）、Task 3 のレビューで、記述が Task 1 の挙動と一致することを確かめる。

- [x] **Step 1: pr-review-fix-loop の SKILL.md**
  - 拒否の表の後に「finalize.py を実行した後の拒否は、「止まったとき」の「finalize の後の `cycle-end` の停止」も読む。」
  - 「終わり方」の abort の項の後に「このサイクルで finalize.py を実行していたら、最後の結果ファイルを `--finalize-result <file>` で足す。`finish --abort` は PR の実際のマージ状態を `result.merged` に保存し、PR を読めなければ渡した結果の `merged` を、それも無ければ `null`（未確認）を保存する（[records.md](references/records.md) の 6 章）。」
  - 「止まったとき」の「最終化の停止」の後に、Spec の設計 2 の 1 項目め（「finalize の後の `cycle-end` の停止」）を 1 項で書く: 渡した結果ファイルの `merged` を確かめる、`true` は取り消せないマージの観測なので PR に commit を足さない、abort するときは同じファイルを `--finalize-result` で渡す（`false`・`null` のときも渡す）、`null` を未マージと報告しない
  - 「最終報告」の「マージしたか」を「マージしたか（`result.merged`。`null` は未確認で、未マージと書かず、PR の状態を読み直して書く）」にする
- [x] **Step 2: `references/records.md`**
  - 3 章の `result` の行の末尾に「。`merged` は `true`・`false`・`null`（`null` は `finish --abort` だけが書く未確認。6 章）」
  - 3 章の `notes` の行を「`recover` で受け取った確認の事実、`finish --abort` が `merged` を PR の状態だけで決められなかった理由など」にする
  - 6 章の `merged` の項から「`finish --abort` が書く `result.merged` は PR を読まずに `false` なので、マージ状態を表さない（確かめるときは PR を読み直す）。」を除き、直後に新しい項を足す: `finish --abort` の `merged` は finalize.py の `merged`（`execution.md` 3.4 節）と同じ意味の最後の観測。決め方（PR を読めればその状態、読めなければ `--finalize-result` の結果、渡されていなければ `null`、finalize が `true` で PR が未マージなら `null`）、理由を `notes` に残すこと、`null` を未マージとして扱わないこと
- [x] **Step 3: issue-to-pr の SKILL.md の表**（Spec の設計 4・D-221-6）
  - `stopped` の行の 1 列目を「`stopped`（`ended_by: outcome`）」にする
  - ループのエラーの行の 1 列目を「ループのエラー（`lock_held`、全レビュアーの失敗、資源の停止を確認できない など。`finish --abort` で終えた run（`ended_by: abort`）を含む）」、3 列目を「PR の状態（`gh pr view <PR の URL> --json state,mergedAt,headRefOid`）を読み直して書く。読めなければ未確認（`finish --abort` の結果の `merged` が `true` なら、マージ済みと書く）」にする
- [x] **Step 4: 確かめる**

Run: `git diff -- .agents/skills/pr-review-fix-loop/SKILL.md .agents/skills/pr-review-fix-loop/references/records.md .agents/skills/issue-to-pr/SKILL.md` を読み、`bash scripts/check-layout.sh` と `uv run pytest tests/skills -q` を実行する
Expected: 記述が Global Constraints の 2・5 行目と一致し、AGENTS.md「日本語表現」に反する語が無い。2 つのコマンドが終了コード 0

- [x] **Step 5: Commit**

```bash
git add .agents/skills/pr-review-fix-loop/SKILL.md .agents/skills/pr-review-fix-loop/references/records.md .agents/skills/issue-to-pr/SKILL.md
git commit -m "docs(pr-review-fix-loop,issue-to-pr): read the run merge state as true, false or null (#221)"
```

## Task 3: 統合確認と最後のレビュー

**Files:**
- Modify: `docs/superpowers/plans/2026-10-21-create-reso-world-issue221-abort-merged-state.md`（チェックと「検証の記録」）

**Interfaces:**
- Consumes: Task 1・Task 2 の commit

**テストの要否:** 書かない。新しい挙動は Task 1 のテストが受け持つ。ここでは古い判定に戻す対照、ブランチ全体のレビュー、README の入口で、条件単位の証拠をそろえる。

- [x] **Step 1: 古い判定に戻す対照**

`_abort_merged` を一時的に `return False, None`（PR を読まずに false。基準の挙動）に変えて `uv run pytest .agents/skills/pr-review-fix-loop/tests -q -k "abort"` を実行し、`git checkout -- .agents/skills/pr-review-fix-loop/scripts/loop.py` で戻して `git status --porcelain` が空であることを確かめる
Expected: 再現のテスト（`pr-read`・`pr-unreadable`）と、`expected` が True・None の組み合わせが失敗し、`expected` が False の組み合わせは通る（テストが元の不具合を検出し、マージしていない run の abort を変えていないことの対照）。ログは `$SESSION/verify/control.log`

- [x] **Step 2: ブランチ全体のレビュー**（新しいコンテキストのサブエージェント 1 回）

Spec・Plan・`git diff origin/main...HEAD` を渡し、(1) Spec の受け入れ条件と決定記録を満たすか、(2) 文書の記述（Task 2）が `loop.py` の挙動とテストの組み合わせの表に一致するか、(3) 既存の `cycle-end`・正常な `finish`・`recover`・`status` の挙動を変えていないか、(4) テストが AGENTS.md「テストの採用基準」に反していないかを見てもらう。致命的な指摘だけを直し、直したら Task 1 の Step 5 をやり直す

- [x] **Step 3: Plan の「検証の記録」を書いて commit する**（これが最後の commit）

各 Step のチェック、Task 別の所要時間、Task 1 の Step 3・Step 5 と Step 1 の結果、レビューの結果と対応を「検証の記録」の節に書き、`git commit -m "docs: record the Issue #221 verification and final review in the plan"`

- [ ] **Step 4: 最後の commit で README の「テスト」の入口を実行し、検証の記録を作る**（`--merge` のループで再利用する）

最後の commit の上で `git status --porcelain` が空であることを確かめてから、worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` をバックグラウンドで順に実行する（各 30 分まで。並行させない）
Expected: 3 つとも終了コード 0。落ちたら基準（`baseline/`）の同じ実行と比べ、この変更による失敗かを判定する。検証した HEAD・`git status --porcelain` が空だったこと・各コマンドの argv・終了コード・ログの完全パスを `$SESSION/verify/record.md` に、`finalize.py --checks-file` の形（`{"head", "base", "commands"}`。`base` は検証したツリーが含む `origin/main` の SHA）を `$SESSION/verify/checks.json` に書く。結果は Plan に書かず（HEAD が変わるので）、PR 本文に書く

## 検証の記録

ログはどれも `/workspaces/reso-world/tmp/agents/issue-221.439bd74f/` にある（commit しない）。SDD の ledger は `sdd/progress.md`、予算の ledger は `budget.jsonl`。

### 修正の前（`b741085`）

| 対象 | 結果 | ログ |
| --- | --- | --- |
| `bash .devcontainer/run-tests.bash` | 終了コード 0 | `baseline/run-tests.log` |
| `bash scripts/check-layout.sh` | 終了コード 0 | `baseline/check-layout.log` |
| `uv run pytest tests/skills .agents/skills .agents/scripts tools` | 3520 passed（943.82 秒）、終了コード 0 | `baseline/pytest.log` |

### Task 1（`c5d86b6`）

- Step 3（RED）: `-k "abort or finalize_result"` で 18 failed・2 passed。新しいテストと、偽の gh を渡した既存のテストが `TypeError`（`finish` が `github`・`finalize_result` を受け付けない）、CLI のテストが argparse の unrecognized arguments で失敗した（`sdd/task1-red.log`）
- Step 5（GREEN）: `.agents/skills/pr-review-fix-loop/tests` 全体が 190 passed（新しいテスト 15 件を含む。`sdd/task1-green.log`）。コメントだけを直した後に `test_loop_state.py` を 69 passed で確かめ直した（`sdd/task1-state.log`）

### Task 2（`c9c6494`）

- 差分を Global Constraints の 2〜5 行目と照合した。AGENTS.md「日本語表現」で避ける語は無い。`bash scripts/check-layout.sh` は終了コード 0、`uv run pytest tests/skills -q` は 31 passed（`sdd/task2-check-layout.log`・`sdd/task2-tests-skills.log`）

### Task 3

- Step 1（対照）: `_abort_merged` の先頭を `return False, None`（基準の挙動）にすると、`-k abort` で 10 failed・9 passed。落ちたのは再現のテスト（`pr-read`・`pr-unreadable`）、`expected` が True・None の組み合わせ（`merged`・`merged-finalize-false`・`unreadable-finalize-true`・`unreadable-finalize-null`・`unreadable`・`open-finalize-true`）、`OSError` と CLI のテスト。`expected` が False の組み合わせ（`open`・`open-finalize-false`・`open-finalize-null`・`unreadable-finalize-false`）、引数の誤りのテスト、既存の abort のテストは通った。戻した後の `git status --porcelain` は空（`verify/control.log`）
- Step 2（ブランチ全体のレビュー。新しいコンテキストの Opus のサブエージェント 1 回、約 15 分）: Ready to merge: Yes。Critical・Important は無く、Minor が 7 件。レビュアーは loop のテスト（190 passed）と、写しでの変異の確認（食い違いの規則、`OSError`、PR だけで決まったときの notes、PR を読めないときの finalize の無視、held の経路の `result` の削除を検出）を行った。Minor は致命的でないので直さず、持ち越しとして記録する
  1. 食い違いのときと、finalize が無く PR を読めないときの notes、held の経路で保存する `merged` の値が、テストで固定されていない
  2. SKILL.md の abort の項に、食い違いのときの `null` が書かれていない（`records.md` の 6 章にはある）
  3. issue-to-pr の表の補足が `finish --abort` の結果に限られている（held の abort など、結果が run.json と `status` にだけある run は、報告のときに PR を読めないと「未確認」になる）
  4. `finish --abort` が期限なしで gh を呼ぶ（応答が返らない障害のとき abort が戻らない。ほかのサブコマンドと同じで、保存の前に読むので途中の状態は残らない）
  5. notes に、使った finalize の結果ファイルのパスが残らない（値は `result.merged`）
  6. SKILL.md の後片付けの順序（`cycle-end` の後にセッションディレクトリを消す）と、新しい abort の手順の関係が書かれていない（`execution.md` の 4 章は失敗・復旧に使う記録を残すとしている）
  7. `finish` に偽の gh を渡していない 2 か所のテスト（`test_loop_state.py` の `not_owner`、`test_loop_review.py` の `<理由>` の拒否。今は PR を読む前に止まる）
- レビュアーが判断しなかったことへの判定は、ledger の `Final: Ruling:` の行に書いた

### 所要時間（Task 3 の Step 3 の commit まで）

- 着手は 2026-10-21 08:38（JST）
- 準備・調査 約 9 分、Spec・Plan 約 7 分、Task 1 約 4 分、Task 2 約 1 分、Task 3（対照、レビューの待ちと判定、記録）約 20 分
