# Issue #223 agent_runner のテストの短い期限・待ち Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者の 2026-10-25（JST）の指示（`/issue-to-pr #223 --merge --max-cycles 3`。Spec の「実行許可」と同じ範囲）

**Goal:** 時間切れを確かめないテストが明示した短い期限と待ち 10 か所を 30 秒にし、時間切れ・子の停止を時間で確かめるテストの短い期限を保ったまま、並行作業の負荷による誤った失敗を減らす。

**Architecture:** `tools/agent_runner/tests/test_process.py` と `tools/agent_runner/tests/test_workspace.py` の数値とコメントだけを変える。runner・process・workspace の本体は変えない。所要時間の比較、負荷をかけた 3 回の実行、README の入口で確かめる。

**Tech Stack:** Python 3.14（uv）、pytest

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue223-agent-runner-test-waits-design.md`

## Global Constraints

- 30 秒にする 10 か所（`dcdc0d9` の行）: `test_process.py` の 65・175 行（`deadline_seconds=5`）、249 行（`wait_for()` の `asyncio.timeout(5)`）、275 行（`asyncio.timeout(2)`）、385・442 行（`deadline_seconds=10`）、395・454 行（`asyncio.wait_for(task, 3)`）、`test_workspace.py` の 273・305 行（`deadline_seconds=3`）
- 変えないもの: `test_process.py` の 151・298・333・357 行の `deadline=3`、302 行の `elapsed_seconds < 2`、340 行の `elapsed_seconds < 3`、364 行の `elapsed_seconds < 30`、226 行の `deadline_seconds=5`、`test_runner.py` のすべて（Spec の設計の 2）
- runner・process・workspace の本体（`tools/agent_runner/` のテスト以外）は変えない
- テストを足さない（Spec の D-223-5）
- ログ・検証の記録・SDD の ledger は worktree の外の `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/` に置く（`AGENTS.md` の「コミットしないファイルの置き場所」）

## Review Focus

新しいテストは足さない（D-223-5）ので、各項目は下の Task の検証の手順で確かめる。

1. 30 秒にした期限に頼って時間切れを確かめるテストがあると、そのテストが 30 秒待つか、時間切れにならずに落ちる → Task 1 の Step 3 の所要時間の比較で、30 秒近いテストが無いことと、時間切れのテストが基準（3.04〜3.70 秒）と同程度であることを確かめる
2. cancel のテストで cancel が効かないと、失敗までの待ちが 3 秒から 30 秒に伸びる → 失敗するときだけの影響。Task 2 の負荷の下で `CancelledError` のまま通ることを確かめる
3. `test_immediate_exit_before_ownership_observation_stops_children` は自身の `elapsed_seconds < 2` で負荷に弱いまま（D-223-4）→ Task 2 で落ちたら下の Contingency の 2
4. 30 秒でも足りない負荷 → Task 2 の各回の load average と `--durations` の上位を記録し、余裕を示す
5. 変えないと決めた短い期限を誤って変える → Task 1 の Step 4 の差分の確認

## 要件と Task の対応（実装前の照合）

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 1 10 か所が 30 秒、変えないものは変わらない | Task 1 | 差分は 10 か所の数値とコメントだけ | `git diff origin/main -- tools/` |
| 2 所要時間が基準と同程度、30 秒まで待つテストが無い | Task 1 | `--durations=40` の上位が基準と同じテストで同程度の秒数 | 基準のログとの比較 |
| 3 負荷の下の 3 回で期限切れ・`TimeoutError` の失敗が出ない | Task 2（統合担当: このセッション） | 3 回とも `timed_out`・`TimeoutError` の失敗なし（最終レビューの M-4 で Spec の受け入れ条件 3 に合わせた。それ以外の失敗は Contingency の 2・4 で切り分けて記録する） | 負荷のログ |
| 4 README の入口がすべて終了コード 0 | Task 3（統合担当: このセッション） | 3 つのコマンドの終了コード | ログ・検証の記録 |

共有する条件は、`test_process.py` の `wait_for()` を 3 つのテストが使うことだけで、Task 1 の Step 3 が 3 つとも実行する。ほかに共有する入力・状態・順序・外部仕様は無い。

## 実行方式

`superpowers:executing-plans`（このセッションが inline で実装する）。`implement_task.py check` が `self=true` で、コードの変更は 1 Task・10 か所の数値とコメントだけ。子に文脈を渡す手間が実装より大きい（Spec の D-223-7）。最後に、ブランチ全体のレビューを新しいレビュアー（サブエージェント 1 つ）に依頼する。

## 実行予算

- 全体の能動時間: 330 分（ledger の予算。ledger の開始は 2026-10-24T19:11:15Z で、それより前の準備（Issue・競合の確認と worktree の作成）は含まない）。実装・PR の作成まで 105 分、`--merge` のループの段階 225 分（サイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 約 30 分））。ledger は `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/budget.jsonl`
- phase の目安: 準備 10 分（済）、Spec・Plan 20 分、Task 1 で 10 分、Task 2 で 30 分、Task 3（最終レビュー・記録・README の入口）で 45 分、PR 10 分、ループ 225 分
- worker: 実装は inline。長い検証はバックグラウンドで実行し、終了の通知で待つ。絶対期限は `tools/agent_runner` 1 回が 15 分（基準 40 秒）、負荷の検証の全体が 60 分、README の入口が 90 分。ログが 10 分変わらなければ stall を疑う。最終レビューのサブエージェントは 1 回で、期限 30 分。ループの worker の期限は pr-review-fix-loop の SKILL.md のとおり
- 再試行の上限: 同じ失敗の再試行は 1 回まで。負荷の検証での期限切れ・`TimeoutError` の失敗は、確かめる性質そのものなので再実行で上書きせず、`superpowers:systematic-debugging` で調べる
- checkpoint: 各 Task の完了時、PR の作成時、予算の 50%（165 分）・100%、検証の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) 負荷の検証で、変えないと決めた短い期限のテストだけが落ちたら、下の Contingency の 2 (2) README の入口が環境の要因で失敗したら、`origin/main`（親の checkout）で同じコマンドを実行して既存の失敗と切り分ける (3) 負荷が軽すぎて意味が薄いと判断したら、負荷の pytest を増やして 3 回をやり直す

## Contingency

1. Task 1 の所要時間の比較で、30 秒近くかかるテストが見つかったら、そのテストは 30 秒にした期限に頼って時間切れを確かめている。元の短い値に戻し、Spec の「確認した事実」と決定記録に追記してから Step 3 をやり直す
2. Task 2 で、変えないと決めた短い期限・上限のテスト（Spec の設計の 2）が落ちたら、変えずに load average・所要時間・失敗の内容を記録し、PR の持ち越し候補に書く（D-223-4）。3 回の実行は数え直さない
3. Task 2 で、30 秒にしたテストが期限切れ・`TimeoutError` になったら、load average とそのテストの所要時間を記録して `superpowers:systematic-debugging` で原因を調べる。根拠なく期限をさらに伸ばさない。解消できなければ止まる
4. Task 2 で期限と関係の無い失敗（#128 など）が出たら、そのテストを単独で 1 回実行し直して切り分け、記録する。3 回の実行は数え直さない

---

### Task 1: 時間切れを確かめないテストの期限と待ちを 30 秒にする

**Files:**
- Modify: `tools/agent_runner/tests/test_process.py:65,175,248-251,275,385,395,442,454`
- Modify: `tools/agent_runner/tests/test_workspace.py:273,305`

**テストの要否:** 書かない。テストの期限・待ちの値だけの変更で、`AGENTS.md` の「テストの採用基準」の F に当たる（Spec の D-223-5）。代わりに Step 3 の所要時間の比較と Step 4 の差分の確認で確かめる。

- [x] **Step 1: `test_process.py` の 8 か所を 30 にする** — 65・175 行の `deadline_seconds=5`、249 行の `asyncio.timeout(5)`、275 行の `asyncio.timeout(2)`、385・442 行の `deadline_seconds=10`、395・454 行の `asyncio.wait_for(task, 3)`。`wait_for()` の直前に、テストの足場の待ちは止まらなくなったときの上限にすぎず、負荷の高いホストでは子の起動だけで伸びること（#218・#223）を 1〜2 行のコメントで書く。cancel のテストの期限には、cancel を確かめるテストで期限は上限にすぎないことが分かる短いコメントを足してよい
- [x] **Step 2: `test_workspace.py` の 2 か所を 30 にする** — 273・305 行の `deadline_seconds=3`
- [x] **Step 3: 所要時間を比べる** — worktree のルートで `uv run pytest tools/agent_runner --durations=40 -q` をバックグラウンドで実行し、ログを `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/task1-agent-runner.log` に書く。期待: 終了コード 0、274 passed。`--durations` の上位が基準（`baseline-agent-runner.log`）と同じ時間切れ・中断のテストで 3〜4 秒程度、30 秒近いテストが無い
- [x] **Step 4: 差分を確かめる** — `git diff origin/main -- tools/` が、10 か所の数値とコメントだけであること。Global Constraints の「変えないもの」が差分に無いこと
- [x] **Step 5: commit**

```bash
git add tools/agent_runner/tests/test_process.py tools/agent_runner/tests/test_workspace.py
git commit -m "fix(agent-runner): give test waits that do not check timeouts 30 s (#223)"
```

### Task 2: 負荷をかけた検証

**担当:** このセッション（統合担当）。**テストの要否:** 書かない（Spec の D-223-5・D-223-6）。この Task 自体が検証である。

- [x] **Step 1: 負荷の pytest を起動する** — worktree のルートで、停止用のファイル `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/load.stop` が現れるまで `uv run pytest tests/skills .agents/skills .agents/scripts tools -q` を繰り返すループを、3 本並行でバックグラウンドで起動する。各回の終了コードと時刻をログ `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/load-generator-<n>.log` に書く
- [x] **Step 2: 3 回実行する** — 負荷の pytest が 1 回目の途中にある間に、`uv run pytest tools/agent_runner --durations=15 -q` を 3 回続けて実行する（バックグラウンド、1 本のシェルで順に）。各回の前後の `/proc/loadavg`、終了コード、`--durations` の上位をログ `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/load-runs.log` に書く。期待: 3 回とも終了コード 0、`timed_out`・`TimeoutError` の失敗が無い
- [x] **Step 3: 負荷の pytest を止める** — 停止用のファイルを作り、ループが今の回を終えて抜けるのを終了の通知で待つ（途中で kill しない）。負荷の pytest の各回の結果も記録する（受け入れ条件ではない。失敗があれば Contingency の 4 と同じく切り分けて記録する）

### Task 3: 統合の確認と記録

**テストの要否:** 新しいテストは書かない。README の「テスト」の入口と最終レビューで確かめる。

- [x] **Step 1: 条件ごとの照合** — 上の「要件と Task の対応」の各行について、差分・ログの該当箇所を挙げる
- [x] **Step 2: 最終レビュー** — 新しいレビュアー（サブエージェント 1 つ）にブランチ全体（`origin/main...HEAD`）を渡し、Spec・Plan との一致、テストの採用基準、Review Focus を確かめさせる。Critical・Important を直したら、関係する検証をやり直してから Step 1 からやり直す
- [x] **Step 3: 記録** — 下の「完了」に、所要時間と主要 Task 別の内訳、Task 1・2 の検証の結果、レビューの結果を書いて commit する。これを最後の commit にする（`--merge` の検証の記録は最後の commit の後に作る）
- [ ] **Step 4: README の「テスト」** — 最後の commit の後に、worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を実行する。終了コード・ログの完全パス・検証した HEAD・`git status --porcelain` が空だったことを `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/` に記録し、`finalize.py` の `--checks-file` の形のファイルも作る。結果は PR の本文に書く（この Plan には書かない。書くと HEAD が変わる）

## 完了

実装と最終レビューの修正は完了した。README の「テスト」（Task 3 の Step 4）はこの記録の commit の後に実行し、結果は PR の本文に書く。状態は `draft` のまま（内容の承認は記録しない）。

- 所要時間（2026-10-24 UTC、worktree の作成 19:08:48Z〜この記録 約 19:45Z、約 37 分。それより前の Issue・競合の確認は数分で、時刻は記録していない）
  - 準備（worktree、対象の箇所の調査、変更の前の基準の測定）: 約 4 分
  - Spec・Plan（`c2f87d6`・`fe77c12`、〜19:14:10Z）: 約 2 分
  - Task 1（`74cb4cc`、〜19:17:06Z）: 約 3 分。274 passed（69.78 秒、load average 9.25〜13.19）。時間切れ・中断のテストは 3.29〜3.87 秒（基準 3.04〜3.70 秒）、30 秒近いテストなし
  - Task 2（19:17〜19:39Z）: 負荷の下の 3 回は約 5 分。負荷の pytest 3 本が終わるまでに約 21 分
  - Task 3 の最終レビュー（opus のサブエージェント 1 回、19:18〜19:31Z、Task 2 と並行）と M-1・M-2 の修正（`3b27b92`、〜19:39:24Z）: 約 4 分（レビューの待ちを除く）
- 実行方式: inline（`superpowers:executing-plans`）。SDD の ledger は worktree の外の `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/sdd/progress.md` に置いた（`AGENTS.md` が worktree の中にコミットしないファイルを置くことを禁じるため）
- 条件ごとの照合（Task 3 の Step 1）
  - 受け入れ条件 1: `git diff origin/main -- tools/` は 10 か所の数値とコメントだけで、Global Constraints の「変えないもの」は差分に無い（Task 1 の Step 4。最終レビューも行番号で確かめた）
  - 受け入れ条件 2: `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/task1-agent-runner.log` の上位 3 件が基準（`baseline-agent-runner.log`）と同じ時間切れ・中断のテストで、3.29〜3.87 秒
  - 受け入れ条件 3: 下の Task 2 の表
  - 受け入れ条件 4: Task 3 の Step 4（PR の本文）
- Task 2（負荷をかけた検証）の結果。HEAD `74cb4cc`、並行させた pytest は README の pytest の入口全体 3 本。3 回とも `timed_out`・`TimeoutError` の失敗は無い

  | 回 | load average（1 分、前〜後） | 終了コード | 所要時間 | 備考 |
  | --- | --- | --- | --- | --- |
  | 1 回目 | 13.35〜16.63 | 1 | 85.35 秒 | `test_concurrency_bounds_whole_assignments` が失敗（下） |
  | 2 回目 | 16.63〜15.85 | 0 | 94.91 秒 | |
  | 3 回目 | 15.85〜18.28 | 0 | 99.65 秒 | 既定 30 秒を使う `test_devin_retained_export_is_redacted_after_nonzero_exit` が 11.49 秒 |

  - 1 回目の失敗は、範囲外とした `test_runner.py:561` の並行の上限の時間の検査（`starts[1] - starts[0] < 0.2`）で、2 件目の開始が 0.26 秒遅れた。期限・待ちの失敗ではない。Contingency の 2 のとおり変えずに記録し、負荷が下がった後（load average 10.49）に単独で 1 回実行すると通った（`isolate-concurrency.log`）。持ち越し候補にする
  - 変更した 10 か所のテストは、3 回とも `--durations=15` の上位に入らなかった（最大は 1 回目の `test_git_preparation_stops_term_resistant_child_of_exited_hook` の 1.11 秒）
  - 並行させた pytest 3 本も、どれも終了コード 0・1224 passed（1253〜1265 秒）だった
  - 負荷は最大で load average 約 18 で、#218 の発生時の約 21 には届いていない。30 秒の余裕は、今回の最大の 11.49 秒（30 秒はその約 2.6 倍）から見積もったもの
  - ログ: `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/load-runs.log`・`load-run-1.out`〜`load-run-3.out`・`load-generator-1.log`〜`load-generator-3.log`
- 最終レビュー: Ready to merge: Yes（Critical 0、Important 0、Minor 4）
  - M-1・M-2（Important に付け直して直した。`3b27b92`）: Spec の「確認した事実」と D-223-3、cancel のテストのコメントが、2 件目の cancel のテスト（期限に届かない）と、1 件目で期限が先に来たときの結果（失敗するか、cancel を確かめないまま通る）を誤って書いていた。文書とコメントだけを直し、`test_process.py` を実行した（24 passed）
  - M-3（直していない）: `wait_for()` のコメントが、`deadline=3` と `elapsed_seconds < 2` を持つ `test_immediate_exit_before_ownership_observation_stops_children` も使うことに触れず、278 行の `asyncio.timeout(30)` に説明が無い
  - M-4（直した）: 上の「要件と Task の対応」の 3 行目を Spec の受け入れ条件 3 に合わせた
- エージェントの判断（ledger の `Ruling:`）
  - SDD の ledger を worktree の外に置き、TDD の RED を行わなかった（値だけの変更で、テストを足さない。D-223-5）
  - 負荷の pytest を今の回の終わりを待たずに SIGINT で止めようとした（待つと約 40 分かかり、同時に走る別のセッションの検証も遅らせるため）。SIGINT は中断を起こさず、3 本とも最後まで走った
  - 最終レビューを Task 2 の実行中に依頼した（Task 2 はコードを変えない）
- 持ち越し候補（直していない）
  - `test_runner.py:561` の `test_concurrency_bounds_whole_assignments` が、負荷（load average 約 16）で並行の開始の差 0.2 秒を越えて落ちる
  - M-3
  - `test_immediate_exit_before_ownership_observation_stops_children` と `test_leader_exit_stops_observed_descendants` は、自身の `elapsed_seconds` の上限と `deadline=3` で負荷に弱いまま（D-223-4。今回の負荷では落ちなかった）
