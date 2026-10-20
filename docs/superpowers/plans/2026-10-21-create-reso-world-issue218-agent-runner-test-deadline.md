# Issue #218 agent_runner のテストの既定の期限 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者の 2026-10-21 の指示（引数 `usaturn/create-reso-world#218 --merge --assign implement=self`。Spec の「実行許可」と同じ範囲）

**Goal:** `configuration()` と `run()` の既定の期限を 30 秒にし、時間切れ・中断のテストの短い期限を保ったまま、並行作業の負荷による `timed_out` の誤った失敗を無くす。

**Architecture:** テストの補助の既定値 2 か所と、その理由のコメントだけを変える。runner・process の本体は変えない。所要時間の比較、負荷をかけた 3 回の実行、README の入口で確かめる。

**Tech Stack:** Python 3.14（uv）、pytest

**Spec:** `docs/superpowers/specs/2026-10-21-create-reso-world-issue218-agent-runner-test-deadline-design.md`

## Global Constraints

- 既定の期限: `tools/agent_runner/tests/test_runner.py` の `configuration(..., deadline: float = 30.0, ...)`、`tools/agent_runner/tests/test_process.py` の `run(..., deadline: float = 30, ...)`。最終レビューの I-1 で、`tools/agent_runner/tests/test_cli.py` の `_TEMPLATE` の `deadline_seconds = 30` を追加した（Spec の D-218-3）
- 明示している期限（3・4・6・8・10 秒、cancel の場合の 60 秒）は変えない
- `test_process.py` で `execute` を直接呼ぶ 3 か所の 5 秒は変えない（Spec の D-218-3）
- runner・process の本体（`tools/agent_runner/` のテスト以外）は変えない
- テストを足さない（Spec の D-218-4）
- ログ・検証の記録は worktree の外の `/workspaces/reso-world/tmp/agents/issue-218.4_mv9dka/` に置く（`AGENTS.md` の「コミットしないファイルの置き場所」）

## Review Focus

新しいテストは足さない（D-218-4）ので、各項目は下の Task の検証の手順で確かめる。

1. 既定の期限に頼って時間切れを確かめるテストがあれば、30 秒待つか、時間切れにならずに落ちる → Task 1 の Step 3 の所要時間の比較で、30 秒近いテストが無いことと、時間切れのテストが基準（3.01〜3.66 秒）と同程度であることを確かめる
2. `configuration` を import する別のファイル（`test_review_regressions.py`・`test_checkout_policy.py`）も新しい既定を使う → Task 1 の Step 3 は `tools/agent_runner` 全体を実行するので、両方を含む
3. cancel で止める中断のテスト（`test_cancel_during_run_prevents_fallback` など）で cancel が来ないと、失敗までの待ちが 5 秒から 30 秒に伸びる → 失敗するときだけの影響。Task 2 の負荷の下で `interrupted` のまま通ることを確かめる
4. 負荷の下で、補助の外にある 5 秒のテストが期限切れになる → Task 2 で確かめ、起きたら下の Contingency に従う（最終レビューの I-1 で、`test_cli.py` の `_TEMPLATE` の 5 秒は補助の既定と同じ仕組みと分かり、30 秒にした）
5. 30 秒でも足りない負荷 → Task 2 の各回の load average と `--durations` の上位を記録し、余裕を示す

## 要件と Task の対応（実装前の照合）

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 1 既定が 30 秒、明示の期限は変わらない | Task 1 | 差分は 2 つの既定値とコメントだけ | `git diff origin/main -- tools/` |
| 2 時間切れ・中断のテストの所要時間が基準と同程度、30 秒まで待つテストが無い | Task 1 | `--durations=40` の上位が基準と同じテストで同程度の秒数 | 基準のログとの比較 |
| 3 負荷の下の 3 回で期限切れの失敗が出ない | Task 2（統合担当: このセッション） | 3 回とも終了コード 0、`timed_out` の失敗なし | 負荷のログ |
| 4 README の入口が基準と同じ結果 | Task 3（統合担当: このセッション） | 3 つのコマンドの終了コード | ログ・検証の記録 |

共有する条件は、`configuration()` を 3 つのテストのファイル（`test_runner.py`・`test_review_regressions.py`・`test_checkout_policy.py`）が使うことだけで、Task 1 の Step 3 が 3 つとも実行する。ほかに共有する入力・状態・順序・外部仕様は無い。

## 実行方式

`superpowers:executing-plans`（このセッションが inline で実装する）。`implement_task.py check` が `self=true` で、コードの変更は 1 Task・2 行とコメントだけ。子に文脈を渡す手間が実装より大きい（Spec の D-218-6）。最後に、ブランチ全体のレビューを新しいレビュアー（サブエージェント 1 つ）に依頼する。

## 実行予算

- 全体の能動時間: 340 分（ledger の予算 330 分と、ledger の開始前の準備 約 6 分。Issue の着手は 2026-10-20T19:23:28Z）。実装・PR の作成まで 105 分、`--merge` のループの段階 225 分（サイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 約 30 分））。ledger は `/workspaces/reso-world/tmp/agents/issue-218.4_mv9dka/budget.jsonl`
- phase の目安: 準備 10 分（済）、Spec・Plan 25 分、Task 1 で 10 分、Task 2 で 30 分、Task 3（最終レビュー・記録・README の入口）で 45 分、PR 10 分、ループ 225 分
- worker: 実装は inline。長い検証はバックグラウンドで実行し、終了の通知で待つ。絶対期限は `tools/agent_runner` 1 回が 15 分（基準 78 秒）、負荷の検証の全体が 60 分、README の入口が 90 分。ログが 10 分変わらなければ stall を疑う。最終レビューのサブエージェントは 1 回で、期限 30 分。ループの worker の期限は pr-review-fix-loop の SKILL.md のとおり
- 再試行の上限: 同じ失敗の再試行は 1 回まで。負荷の検証での `timed_out` の失敗は、確かめる性質そのものなので再実行で上書きせず、`superpowers:systematic-debugging` で調べる
- checkpoint: 各 Task の完了時、PR の作成時、予算の 50%（165 分）・100%、検証の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) 負荷の検証で補助の外の 5 秒のテストだけが期限切れになったら、下の Contingency の 2 (2) README の入口が環境の要因で失敗したら、`origin/main`（親の checkout）で同じコマンドを実行して既存の失敗と切り分ける (3) 負荷が軽すぎて意味が薄いと判断したら、負荷の pytest を 2 本にして 3 回をやり直す（利用者の決定の範囲内）

## Contingency

1. Task 1 の所要時間の比較で、30 秒近くかかるテストが見つかったら、そのテストは既定の期限に頼って時間切れを確かめている。そのテストに短い期限（周りと同じ 3 秒）を明示し（利用者の決定）、Spec の D-218-2 に追記してから Step 3 をやり直す
2. Task 2 で、補助の外の明示の 5 秒（`test_process.py` の `execute` の直接呼び出し）のテストが期限切れになったら、D-218-3 を見直してそのテストの 5 秒も 30 秒にする。Issue の目的（時間切れを確かめないテストの負荷による失敗を減らす）の範囲内なので、Spec の決定記録に変更として書いてから Task 2 をやり直す
3. Task 2 で、補助を使うテストが 30 秒でも期限切れになったら、load average とそのテストの所要時間を記録して `superpowers:systematic-debugging` で原因を調べる。根拠なく期限をさらに伸ばさない。解消できなければ止まる
4. Task 2 で期限と関係の無い失敗（#128 など）が出たら、そのテストを単独で 1 回実行し直して切り分け、記録する。3 回の実行は数え直さない

---

### Task 1: 補助の既定の期限を 30 秒にする

**Files:**
- Modify: `tools/agent_runner/tests/test_runner.py:180-186`（`configuration()`）
- Modify: `tools/agent_runner/tests/test_process.py:34`（`run()`）

**テストの要否:** 書かない。補助の既定値だけの変更で、`AGENTS.md` の「テストの採用基準」の「書かない: 設定値」に当たる（Spec の D-218-4）。代わりに Step 3 の所要時間の比較と Step 4 の差分の確認で確かめる。

- [ ] **Step 1: `configuration()` の既定を `deadline: float = 30.0` にする** — 関数の直前に、既定の期限は止まらなくなった実行の上限で、負荷の高いホストでは worktree の準備と起動だけで伸びること（#218）、期限を確かめるテストは短い期限を明示することを、1〜2 行のコメントで書く
- [ ] **Step 2: `run()` の既定を `deadline: float = 30` にする** — 同じ趣旨のコメントを関数の直前に書く（子プロセスの起動が伸びることに合わせる）
- [ ] **Step 3: 所要時間を比べる** — worktree のルートで `uv run pytest tools/agent_runner --durations=40 -q` をバックグラウンドで実行し、ログを `/workspaces/reso-world/tmp/agents/issue-218.4_mv9dka/task1-agent-runner.log` に書く。期待: 終了コード 0、1056 passed。`--durations` の上位が基準（`baseline-agent-runner.log`）と同じ時間切れ・中断のテストで 3〜4 秒程度、30 秒近いテストが無い
- [ ] **Step 4: 差分を確かめる** — `git diff origin/main -- tools/` が、2 つの既定値とコメントだけであること
- [ ] **Step 5: commit**

```bash
git add tools/agent_runner/tests/test_runner.py tools/agent_runner/tests/test_process.py
git commit -m "fix(agent-runner): give the test helpers a 30 s default deadline (#218)"
```

### Task 2: 負荷をかけた検証

**担当:** このセッション（統合担当）。**テストの要否:** 書かない（Spec の D-218-4・D-218-5）。この Task 自体が検証である。

- [ ] **Step 1: 負荷の pytest を起動する** — worktree のルートで、停止用のファイル `/workspaces/reso-world/tmp/agents/issue-218.4_mv9dka/load.stop` が現れるまで `uv run pytest tests/skills .agents/skills .agents/scripts tools -q` を繰り返すループを、バックグラウンドで起動する。各回の終了コードと時刻をログ `/workspaces/reso-world/tmp/agents/issue-218.4_mv9dka/load-generator.log` に書く
- [ ] **Step 2: 3 回実行する** — 負荷の pytest が 1 回目の途中にある間に、`uv run pytest tools/agent_runner --durations=15 -q` を 3 回続けて実行する（バックグラウンド、1 本のシェルで順に）。各回の前後の `/proc/loadavg`、終了コード、`--durations` の上位をログ `/workspaces/reso-world/tmp/agents/issue-218.4_mv9dka/load-runs.log` に書く。期待: 3 回とも終了コード 0、`timed_out` の失敗が無い
- [ ] **Step 3: 負荷の pytest を止める** — 停止用のファイルを作り、ループが今の回を終えて抜けるのを終了の通知で待つ（途中で kill しない）。負荷の pytest の各回の結果も記録する（受け入れ条件ではない。失敗があれば Contingency の 4 と同じく切り分けて記録する）

### Task 3: 統合の確認と記録

**テストの要否:** 新しいテストは書かない。README の「テスト」の入口と最終レビューで確かめる。

- [ ] **Step 1: 条件ごとの照合** — 上の「要件と Task の対応」の各行について、差分・ログの該当箇所を挙げる
- [ ] **Step 2: 最終レビュー** — 新しいレビュアー（サブエージェント 1 つ）にブランチ全体（`origin/main...HEAD`）を渡し、Spec・Plan との一致、テストの採用基準、Review Focus を確かめさせる。Critical・Important を直したら、関係する検証をやり直してから Step 1 からやり直す
- [ ] **Step 3: 記録** — 下の「完了」に、所要時間と主要 Task 別の内訳、Task 1・2 の検証の結果、レビューの結果を書いて commit する。これを最後の commit にする（`--merge` の検証の記録は最後の commit の後に作る）
- [ ] **Step 4: README の「テスト」** — 最後の commit の後に、worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を実行する。終了コード・ログの完全パス・検証した HEAD・`git status --porcelain` が空だったことを `/workspaces/reso-world/tmp/agents/issue-218.4_mv9dka/` に記録し、`finalize.py` の `--checks-file` の形のファイル（`{"head", "base", "commands"}`）も作る。結果は PR の本文に書く（この Plan には書かない。書くと HEAD が変わる）

## 完了

（Task 3 の Step 3 で書く）
