# Issue #264 並行の上限のテストを区間の順序で確かめる Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者の 2026-10-25（JST）の指示（`/issue-to-pr #264 --merge --max-cycles 3`。Spec の「実行許可」と同じ範囲）

**Goal:** `test_concurrency_bounds_whole_assignments` を、開始時刻の差のしきい値ではなく、偽の CLI の待ち合わせと区間の順序で確かめる形にし、並行の上限を壊した版で落ちる守りを保ったまま、負荷による誤った失敗を無くす。

**Architecture:** `tools/agent_runner/tests/test_runner.py` の偽の CLI（`_SCRIPT`）に、他の担当の `marker` を待つ option と終了時刻の追記を足し、テスト 1 件の assert を区間の順序に変える。runner の本体は変えない。負荷をかけた繰り返しの実行と、`runner.py` の semaphore を一時的に壊した版で確かめる。

**Tech Stack:** Python 3.14（uv）、pytest、asyncio

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue264-concurrency-test-overlap-design.md`

## Global Constraints

- 変えるのは `tools/agent_runner/tests/test_runner.py` の `_SCRIPT` と `test_concurrency_bounds_whole_assignments` だけ。runner・process・workspace の本体は変えない（Spec の「範囲外」）
- テストに渡す値: `peers` は 3 つの `marker` のパス、`quorum=2`、`sleep=0.25`、`concurrency=2`（Spec の設計の 1、D-264-3）
- 待ち合わせに独自の上限を持たせない。上限は `configuration()` の既定の役割の期限 30 秒（D-264-2）
- 終了時刻は、眠り終えた後に同じ `marker` に空白区切りで追記する（D-264-4）
- テストを足さない（D-264-5）
- ログ・検証の記録・SDD の ledger は worktree の外の `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/` に置く（`AGENTS.md` の「コミットしないファイルの置き場所」）

## Review Focus

新しいテストは足さない（D-264-5）ので、各項目は下の Task の検証の手順で確かめる。

1. 負荷で 2 件目の開始が大きく遅れても、正しい実装では落ちない → Task 2 の負荷の下の 20 回と 3 回
2. 上限を無視する壊れ方（3 件同時）を見逃す → Task 1 の Step 4 で `asyncio.Semaphore(3)` の版を 3 回実行し、3 回とも落ちることを確かめる
3. 1 件ずつ走らせる壊れ方でテストが止まらない → Task 1 の Step 4 で `asyncio.Semaphore(1)` の版が、役割の期限（30 秒）の後に落ちて終わることを確かめる
4. `marker` の追記が、`marker` を使う他のテスト（`test_cancel_during_run_prevents_fallback` など）を変える → Task 1 の Step 3 の `test_runner.py` 全体の実行
5. 一時的に壊した `runner.py` が差分に残る → Task 1 の Step 5 の `git diff`

## 要件と Task の対応（実装前の照合）

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 1 しきい値を使わず 3 つの assert で確かめ、他の `marker` の扱いは変わらない | Task 1 | 差分は `_SCRIPT` とテスト 1 件だけ | `git diff origin/main -- tools/` |
| 2 単独と `tools/agent_runner` で通り、所要時間が同程度 | Task 1 | 単独の所要時間が基準（1.26 秒）と同程度 | `--durations` のログ |
| 3 負荷の下の 20 回と 3 回が落ちない | Task 2（統合担当: このセッション） | 20 回・3 回とも終了コード 0 | 負荷のログ |
| 4 壊れた版で落ち、`runner.py` が元に戻る | Task 1 | `Semaphore(3)` の 3 回・`Semaphore(1)` の 1 回がすべて失敗。`git diff` に `runner.py` が無い | 壊れた版のログ・`git diff` |
| 5 README の入口がすべて終了コード 0 | Task 3（統合担当: このセッション） | 3 つのコマンドの終了コード | ログ・検証の記録 |

共有する条件は、偽の CLI の `marker` を他の 3 つのテストも使うことだけで、Task 1 の Step 3 が `test_runner.py` 全体を実行して確かめる。ほかに共有する入力・状態・順序・外部仕様は無い。

## 実行方式

`superpowers:executing-plans`（このセッションが inline で実装する）。`implement_task.py check` が `self=true` で、コードの変更は 1 つのファイルの偽の CLI とテスト 1 件だけ。子に文脈を渡す手間が実装より大きい（Spec の D-264-7）。最後に、ブランチ全体のレビューを新しいレビュアー（サブエージェント 1 つ）に依頼する。

## 実行予算

- 全体の能動時間: 315 分（ledger の予算。ledger の開始は 2026-10-25T02:04:05Z で、それより前の準備（Issue・競合の確認、worktree の作成、Spec）は含まない）。実装・PR の作成まで 90 分、`--merge` のループの段階 225 分（サイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 約 30 分））。#223 の実績（PR の作成まで約 40 分、負荷の pytest の待ちを含めて約 60 分）から見積もった。ledger は `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/budget.jsonl`
- phase の目安: Plan 10 分、Task 1 で 15 分、Task 2 で 30 分、Task 3（最終レビュー・記録・README の入口）で 30 分、PR 5 分、ループ 225 分
- worker: 実装は inline。長い検証はバックグラウンドで実行し、終了の通知で待つ。絶対期限は `tools/agent_runner` 1 回が 15 分（基準 40〜100 秒）、負荷の検証の全体が 60 分、README の入口が 90 分。ログが 10 分変わらなければ stall を疑う。最終レビューのサブエージェントは 1 回で、期限 30 分。ループの worker の期限は pr-review-fix-loop の SKILL.md のとおり
- 再試行の上限: 同じ失敗の再試行は 1 回まで。負荷の検証でこのテストが落ちたら、確かめる性質そのものなので再実行で上書きせず、`superpowers:systematic-debugging` で調べる
- checkpoint: 各 Task の完了時、PR の作成時、予算の 50%（157 分）・100%、検証の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) 上限を無視する版を 3 回とも検出できなければ、眠る時間を 0.5 秒にして Step 4 をやり直し、Spec の D-264-3 に追記する (2) README の入口が環境の要因で失敗したら、`origin/main`（親の checkout）で同じコマンドを実行して既存の失敗と切り分ける (3) 負荷が軽すぎて意味が薄いと判断したら、負荷の pytest を増やしてやり直す

## Contingency

1. Task 1 の Step 3 で `marker` を使う他のテストが落ちたら、追記をやめて終了時刻を別の option に書く（D-264-4 の別案）。Spec の決定記録に追記してからやり直す
2. Task 2 でこのテストが落ちたら、失敗した assert・値・load average を記録して `superpowers:systematic-debugging` で原因を調べる。根拠なく値を伸ばさない。解消できなければ止まる
3. Task 2 でこのテストと関係の無い失敗（#128 など）が出たら、そのテストを単独で 1 回実行し直して切り分け、記録する。回数は数え直さない

---

### Task 1: 偽の CLI の待ち合わせと区間の assert

**Files:**
- Modify: `tools/agent_runner/tests/test_runner.py`（`_SCRIPT` の 34-60 行、`test_concurrency_bounds_whole_assignments` の 547-562 行）

**Interfaces:**
- 偽の CLI の option（`FakeAdapter` の `options` の担当ごとの dict）: `peers: list[str]`（待つ `marker` のパス）、`quorum: int`（`peers` のうち存在しなければならない件数。無ければ 0 で待たない）。`marker: str` は、開始時に `time.monotonic()` を書き、眠り終えた後に `" " + str(time.monotonic())` を追記する

**テストの要否:** テストを足さない。既存の S のテスト（並行の上限）を、負荷で落ちない形に直す（Spec の D-264-5）。守りが残ることは Step 4 の壊れた版で確かめる。

- [x] **Step 1: `_SCRIPT` を変える** — `time.sleep(options.get('sleep', 0))` の直前に、`peers` のうち存在するパスが `quorum` 件未満の間 0.01 秒ずつ待つループを足す。`time.sleep(...)` の直後に、`marker` があれば終了時刻を追記する。ファイルの先頭のコメント（semaphore を外すと落ちる assert）は変えない
- [x] **Step 2: テストを変える** — 3 つの担当に `{"peers": [3 つの marker], "quorum": 2, "sleep": 0.25, "marker": <自分の marker>}` を渡す。assert は次のとおり（名前は実装に任せる）。テストの前に、待ち合わせで重なりを作り、slot が空くのは偽の CLI が終了を書いて終わった後なので順序で確かめられること、時間のしきい値を使わないのは負荷で worktree の作成と起動が伸びるため（#264）であること、0.25 秒は上限を無視する壊れ方を検出する幅のためだけであることを短いコメントで書く

```python
assert batch.state == "success"
(first_start, first_end), (second_start, second_end), (third_start, _) = sorted(
    tuple(map(float, path.read_text().split())) for path in markers.values()
)
assert second_start < first_end
assert third_start > min(first_end, second_end)
```

- [x] **Step 3: 実行する** — worktree のルートで `uv run pytest tools/agent_runner/tests/test_runner.py --durations=10 -q` を実行し、ログを `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/task1-test-runner.log` に書く。期待: 終了コード 0、49 passed、このテストの所要時間が基準（1.26 秒）と同程度
- [x] **Step 4: 壊れた版で落ちることを確かめる** — `tools/agent_runner/runner.py` の `asyncio.Semaphore(concurrency)` を一時的に `asyncio.Semaphore(3)` に変えてこのテストだけを 3 回、`asyncio.Semaphore(1)` に変えて 1 回実行する。期待: 4 回とも失敗（`Semaphore(3)` は `third_start > ...` の assert、`Semaphore(1)` は `batch.state == "success"` の assert）。ログを `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/task1-mutations.log` に書く。終わったら `git checkout -- tools/agent_runner/runner.py` で戻す
- [x] **Step 5: 差分を確かめる** — `git diff origin/main -- tools/` が `test_runner.py` の `_SCRIPT` とこのテストだけであること。`runner.py` が差分に無いこと
- [x] **Step 6: commit**

```bash
git add tools/agent_runner/tests/test_runner.py
git commit -m "fix(agent-runner): check the concurrency bound by interval order, not start gaps (#264)"
```

### Task 2: 負荷をかけた検証

**担当:** このセッション（統合担当）。**テストの要否:** 書かない（Spec の D-264-5・D-264-6）。この Task 自体が検証である。

- [x] **Step 1: 負荷の pytest を起動する** — worktree のルートで、停止用のファイル `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/load.stop` が現れるまで `uv run pytest tests/skills .agents/skills .agents/scripts tools -q` を繰り返すループを、3 本並行でバックグラウンドで起動する。各回の終了コードと時刻をログ `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/load-generator-<n>.log` に書く
- [x] **Step 2: このテストを 20 回実行する** — 負荷の pytest が走っている間に、`uv run pytest tools/agent_runner/tests/test_runner.py -k test_concurrency_bounds_whole_assignments -q` を 20 回続けて実行する（バックグラウンド、1 本のシェルで順に）。各回の前の `/proc/loadavg` と終了コードをログ `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/load-single.log` に書く。期待: 20 回とも終了コード 0
- [x] **Step 3: `tools/agent_runner` を 3 回実行する** — 続けて `uv run pytest tools/agent_runner --durations=10 -q` を 3 回実行し、各回の前後の `/proc/loadavg`、終了コード、`--durations` の上位をログ `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/load-runs.log` に書く。期待: 3 回とも、このテストが落ちない（ほかの失敗は Contingency の 3）
- [x] **Step 4: 負荷の pytest を止める** — 停止用のファイルを作り、ループが今の回を終えて抜けるのを終了の通知で待つ。負荷の pytest の各回の結果も記録する（受け入れ条件ではない）

### Task 3: 統合の確認と記録

**テストの要否:** 新しいテストは書かない。README の「テスト」の入口と最終レビューで確かめる。

- [x] **Step 1: 条件ごとの照合** — 上の「要件と Task の対応」の各行について、差分・ログの該当箇所を挙げる
- [x] **Step 2: 最終レビュー** — 新しいレビュアー（サブエージェント 1 つ）にブランチ全体（`origin/main...HEAD`）を渡し、Spec・Plan との一致、テストの採用基準、Review Focus、待ち合わせと区間の順序の推論の正しさを確かめさせる。Critical・Important を直したら、関係する検証をやり直してから Step 1 からやり直す
- [x] **Step 3: 記録** — 下に「完了」の節を足し、所要時間と主要 Task 別の内訳、Task 1・2 の検証の結果、レビューの結果を書いて commit する。これを最後の commit にする（`--merge` の検証の記録は最後の commit の後に作る）
- [ ] **Step 4: README の「テスト」** — 最後の commit の後に、worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を実行する。終了コード・ログの完全パス・検証した HEAD・`git status --porcelain` が空だったことを `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/` に記録し、`finalize.py` の `--checks-file` の形のファイルも作る。結果は PR の本文に書く（この Plan には書かない。書くと HEAD が変わる）

## 完了

実装と最終レビューは完了した。README の「テスト」（Task 3 の Step 4）はこの記録の commit の後に実行し、結果は PR の本文に書く。状態は `draft` のまま（内容の承認は記録しない）。

- 所要時間（2026-10-25 UTC、worktree の作成 02:00:04Z〜この記録 約 02:33Z、約 33 分。それより前の Issue・競合の確認は数分で、時刻は記録していない）
  - 準備（worktree、対象のコードの調査、変更の前の基準の測定）・Spec（`9cdaeb5`、〜02:03:48Z）: 約 4 分
  - Plan（`385e271`、〜02:04:59Z）: 約 1 分
  - Task 1（`d041d76`、〜02:07:14Z）: 約 2 分（壊れた版の確認の約 40 秒を含む）
  - Task 2（02:07:21Z〜02:30:58Z）: 受け入れ条件の 20 回と 3 回は 02:12:48Z までの約 5 分。負荷の pytest 3 本が今の回を終えるまでに約 18 分
  - Task 3 の最終レビュー（opus のサブエージェント 1 回、02:07Z〜02:13Z ごろ、Task 2 と並行）と記録: 約 3 分（レビューの待ちを除く）
- 実行方式: inline（`superpowers:executing-plans`）。SDD の ledger は worktree の外の `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/sdd/progress.md` に置いた
- 条件ごとの照合（Task 3 の Step 1）
  - 受け入れ条件 1: `git diff origin/main -- tools/` は `test_runner.py` の `_SCRIPT`（待ち合わせのループと終了時刻の追記）と `test_concurrency_bounds_whole_assignments` だけ。開始の差のしきい値（`< 0.2`・`>= 0.23`）は無くなり、設計の 2 の 3 つの assert になった。`marker` を使う他の 3 つのテストは変えていない
  - 受け入れ条件 2: `test_runner.py` 全体は 49 passed（load average 13.99〜14.71、このテストは 1.81 秒。基準は load average 7.77 で 1.26 秒）。負荷の下の `tools/agent_runner` の 3 回では 1.82〜1.98 秒。ログは `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/task1-test-runner.log`
  - 受け入れ条件 3: 下の Task 2 の表
  - 受け入れ条件 4: 負荷をかけない状態（load average 15.54〜16.02。並行する別の作業による）で、`asyncio.Semaphore(3)` の版は 3 回とも 3 つ目の assert（`third_start > min(first_end, second_end)`）で失敗し（0.85〜1.09 秒）、`asyncio.Semaphore(1)` の版は役割の期限の後に `batch.state == "partial_success"` で失敗した（31.74 秒）。確かめた後に `git checkout -- tools/agent_runner/runner.py` で戻し、`git status --porcelain` には `test_runner.py` だけが残った。ログは `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/task1-mutations.log`
  - 受け入れ条件 5: Task 3 の Step 4（PR の本文）
- Task 2（負荷をかけた検証）の結果。HEAD `d041d76`、並行させた pytest は README の pytest の入口全体 3 本

  | 実行 | 回数 | load average（1 分） | 結果 |
  | --- | --- | --- | --- |
  | このテストだけ | 20 | 15.26〜21.02（各回の前） | 20 回とも終了コード 0（1.64〜5.66 秒） |
  | `uv run pytest tools/agent_runner` | 3 | 21.01〜23.12（前後） | 3 回とも終了コード 0・274 passed（71.75〜91.43 秒） |
  | 負荷の pytest（受け入れ条件ではない） | 3 本 × 1 回 | — | 3 本とも終了コード 0・1224 passed（1366〜1415 秒） |

  - load average は最大約 23 で、#264 の発生時（13.35〜16.63）と #218 の発生時（約 21）を越えた
  - ログ: `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/load-single.log`・`load-single-1.out`〜`load-single-20.out`・`load-runs.log`・`load-run-1.out`〜`load-run-3.out`・`load-generator-1.log`〜`load-generator-3.log`
- 最終レビュー: Ready to merge: Yes（Critical 0、Important 0、Minor 3）。レビュアーは、正しい runner での合否が待ち合わせと slot が空く順序だけで決まることをコード（`_supervisor.py` の `waitpid` の後の終了の通知、`process.py` の成功の返り値、`runner.py` の `async with semaphore`）で確かめ、写しで偽の CLI の開始を 1 件だけ 1.5 秒遅らせても通ることを確かめた。Minor はどれも直していない
  - 上限を無視する壊れ方の検出は時間に依存したまま（開始のずれが約 0.25 秒を越えると見逃す。旧テストより弱くはない。D-264-3）。壊れた版の検出は、負荷の無い条件で確かめたものである
  - `second_start < first_end` は、待ち合わせが効いている限り `success` から成り立つ。待ち合わせが将来 no-op になったときに 1 件ずつの runner を捕まえる守りとして残す
  - 1・2 件目が `marker` を書く前に失敗すると、もう片方が役割の期限の 30 秒まで待つ（失敗が分かるまでの時間だけが延びる。D-264-2 の代償）
- エージェントの判断（ledger の `Ruling:`）
  - SDD の ledger を worktree の外に置き、`sdd-workspace`・`task-start`・`task-done` を使わなかった（`AGENTS.md` の SDD 実行運用）
  - TDD の RED は、テスト自身の変更なので、壊れた runner で落ちること（Task 1 の Step 4）で代えた
  - 最終レビューを Task 2 の実行中に依頼した（Task 2 はコードを変えない）。レビュアーには worktree を変えないよう指示し、実験は `git archive` の写しで行わせた
  - レビュアーが判断しなかった「whole assignments」（semaphore が worktree の作成と後始末まで囲むこと）は、旧テストと同じく区別しないまま（Spec の範囲外）
- 持ち越し候補（直していない）
  - 上の Minor の 1 件目（上限を無視する壊れ方の検出が時間に依存する）
  - テスト名の「whole assignments」（semaphore が試行のプロセスだけを囲む版でも通る）
