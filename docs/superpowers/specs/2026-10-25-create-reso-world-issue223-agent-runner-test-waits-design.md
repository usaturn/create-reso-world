# Issue #223: agent_runner のテストで、時間切れを確かめないのに明示した短い期限・待ちを 30 秒にする

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/223（ラベル `bug`。親 Issue・依存・コメントは無い。関連: #218、PR #222）
- 状態: completed（PR #263 のサイクル 1 で修正不要と判断した。末尾の「PR #263 のレビュー修正（サイクル 1）」）。内容の承認は記録しない
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue223-agent-runner-test-waits.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-223-agent-runner-test-deadlines`（branch `fix/issue-223-agent-runner-test-deadlines`）。PARENT_ROOT: `/workspaces/reso-world`
- 基準: `origin/main` の `dcdc0d9`
- 実行許可: 2026-10-25（JST）、利用者が `/issue-to-pr #223 --merge --max-cycles 3` を実行した。issue-to-pr の規則により、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成（`Closes #223`）まで続け、PR の作成後に PR 修正ループを回し、修正不要と確かめられたらループの中の `finalize.py` がマージと関連 Issue の更新まで行う。これは実行の許可であり、この文書の内容の承認ではない。下の判断は、どれも確認を取らずに決めたエージェントの判断である
- ループの設定: `loop.py check-options --max-cycles 3` の出力は `options={"max_cycles": 3, "assign": {}, "template": "/workspaces/reso-world/.devcontainer/agent-runner.toml", "config": null}`。`--max-cycles 3` は利用者の指定、`assign: {}`・`template`・`config: null` は既定の適用。レビュアーは `claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正の担当は `claude-opus`、自己レビューと修正の確認は `self`（いずれも設定のとおり）
- 実装の担当: `implement_task.py check` の出力は `assignment={"agents": ["self"], "fallback": []}`、`self=true`。雛形 `.devcontainer/agent-runner.toml` の既定の適用で、`--implement` は付けていない

## 意図

#218（PR #222）で、`tools/agent_runner` のテストの補助の既定の期限を 30 秒にした。同じ仕組み（子プロセスの起動・git の worktree の作成・後始末が、並行作業の負荷で伸びる）で切れうる、時間切れを確かめないテストが自分で明示した短い期限と待ちが残っている。一括の検証が PR と無関係に不安定に失敗すると、issue-to-pr の `--merge` の検証の記録（すべての終了コードが 0）や review-fix-planning の結論 2 の検証で、再実行と切り分けの手間がかかる。テストの意図（時間切れ・中断・子の停止の検査）を変えずに、負荷による誤った失敗だけを減らす。

## 確認した事実（2026-10-25、`dcdc0d9`）

- Issue の表は `0de1a7d` の行番号で書かれている。その後の #230 の削減（`4c4a964`・`c13ea67`）で `test_process.py` が短くなり、行がずれた。今の対象は次のとおり

  | 場所 | 値 | テスト | 待つもの |
  | --- | --- | --- | --- |
  | `tools/agent_runner/tests/test_process.py:65` | `execute(..., deadline_seconds=5)` | `test_stdin_quotes_multiline_cwd_and_environment_are_literal` | Python の子が stdin を読んで書き終えること |
  | `tools/agent_runner/tests/test_process.py:175` | `execute(..., deadline_seconds=5)` | `test_supervisor_preserves_literal_environment` | supervisor 経由の `/usr/bin/env -0` の終了 |
  | `tools/agent_runner/tests/test_process.py:249`（`wait_for()`。呼び出しは 271・391・448 行） | `asyncio.timeout(5)` | 子の停止・中断のテスト 3 件 | 子が pid ファイルを書くこと |
  | `tools/agent_runner/tests/test_process.py:275` | `asyncio.timeout(2)` | `test_immediate_exit_before_ownership_observation_stops_children` | leader が reap されること |
  | `tools/agent_runner/tests/test_process.py:395`・`454` | `asyncio.wait_for(task, 3)` | cancel のテスト 2 件 | cancel した task の後始末 |
  | `tools/agent_runner/tests/test_process.py:385`・`442` | `execute(..., deadline_seconds=10)` | 同じ cancel のテスト 2 件 | cancel するまでの実行（Issue の表に無い。D-223-3） |
  | `tools/agent_runner/tests/test_workspace.py:273` | `prepare_worktree(..., deadline_seconds=3)` | `test_async_preparation_uses_pinned_commit_and_safe_environment` | 本物の `prepare_worktree`（git の worktree の作成）の成功 |
  | `tools/agent_runner/tests/test_workspace.py:305` | `prepare_worktree(..., deadline_seconds=3)` | `test_git_preparation_stops_term_resistant_child_of_exited_hook` | hook が起動した Python の子を含む準備の成功 |

- Issue の表にあって、今の `main` に無いもの: `test_large_parallel_output_is_streamed_to_files`（`run(..., deadline=10)`）と `test_thread_event_cancels_running_process`（`wait_for()` の呼び出しと `asyncio.wait_for(task, 3)` の 1 件ずつ）。どちらも #230 で消えた（`git log -S` で `4c4a964`）
- `execute` の期限は、関数の先頭（`started = time.monotonic()`）から数え、起動の後のループで `time.monotonic() - started >= deadline_seconds` のときに `timed_out` にする（`tools/agent_runner/process.py` 327-438 行）。`create_subprocess_exec` を差し替えたテストでは、差し替えた関数の中の待ちも期限と `elapsed_seconds` に入る
- cancel のテスト 2 件は、子が pid ファイルを書くのを `wait_for()` で待ってから task を cancel し、`CancelledError` を確かめる。期限の扱いは 2 件で違う（最終レビューの M-1 で直した）
  - `test_coroutine_cancellation_stops_leader_and_escaped_descendant`: 起動の後のループで cancel を受ける。cancel の前に `execute` の期限 10 秒が来ると、期限の後始末がプロセスを止めるので、テストは失敗する（`wait_for()` の `TimeoutError`、`CancelledError` が出ない）か、cancel の後始末を確かめないまま通る（レビュアーが期限を 1 ms にして確かめた）。`wait_for()` の待ちだけを 30 秒にしても、負荷で起動が 10 秒を越えると期限が先に来る
  - `test_repeated_cancellation_during_launch_still_stops_process`: 起動の途中で cancel するので、`execute` は期限を判定するループの前に `CancelledError` を投げる（`process.py` の `if launch_cancelled: raise asyncio.CancelledError`）。期限には届かない（レビュアーが期限を 0.001 秒にしても通ることを確かめた）
- `test_immediate_exit_before_ownership_observation_stops_children` は `run(..., deadline=3)` と `result.elapsed_seconds < 2` を明示する。差し替えた起動の中の待ち（`wait_for()` と `asyncio.timeout(2)`）は `elapsed_seconds` に入るので、このテストは待ちが 2 秒を越えると、待ちの長さに関係なく `elapsed_seconds < 2` で失敗する。待ちの `TimeoutError` で失敗すると、60 秒の子は `children` に記録される前なので、テストの `finally` が止める対象に入らない
- 時間切れを確かめるテスト・子を待たないことを時間で確かめるテストは、短い期限を意図して明示している（#218 の Spec の「確認した事実」と同じ）
  - `test_process.py:151`（`test_buffered_original_exit_survives_anchor_reap`、`deadline=3` で `timed_out` を確かめる）
  - `test_process.py:298`（`test_immediate_exit_before_ownership_observation_stops_children`、`deadline=3` と `elapsed_seconds < 2`）
  - `test_process.py:333`（`test_leader_exit_stops_observed_descendants`、`deadline=3` と `elapsed_seconds < 3`）
  - `test_process.py:357`（`test_deadline_kills_term_resistant_leader`、`deadline=3` で `timed_out` を確かめる）
- `test_process.py:226`（`test_already_cancelled_does_not_spawn` の `deadline_seconds=5`）は、起動の前に `interrupted` で返るので、期限の判定に届かない
- `tools/agent_runner/tests` の他のファイルに、同じ種類の短い期限・待ちは無い（`grep` で `deadline_seconds`・`deadline=`・`asyncio.timeout`・`wait_for`・`timeout=` を探した）。`test_runner.py:561` の `starts[1] - starts[0] < 0.2` は、並行の上限（2 件が同時に始まる）そのものを時間で確かめる
- 変更の前の基準（load average 4.63〜7.26 で `uv run pytest tools/agent_runner --durations=40` を 1 回）: 274 passed、39.67 秒。所要時間の上位 3 件は、期限 3 秒を明示した時間切れ・中断のテスト（3.04〜3.70 秒。`test_checkout_preparation_is_supervised[late_cancel]`、`test_deadline_kills_term_resistant_leader[False]`、`test_buffered_original_exit_survives_anchor_reap`）で、その次は 2.05 秒（`test_concurrency_bounds_whole_assignments`）、以下 1.10 秒以下。ログは `/workspaces/reso-world/tmp/agents/issue-223.m5gmy2ln/baseline-agent-runner.log`
- 負荷の観測: #223 の失敗はまだ観測していない。PR #222 の検証（load average 2.7〜10.9 の 16 回）でも切れなかった。#218 の発生時の load average は約 21（8 コア）

## 設計

### 1. 時間切れを確かめないテストの期限と待ちを 30 秒にする（Issue の案 (a)）

「確認した事実」の表の 10 か所を、補助の既定（`run()` の `deadline: float = 30`）と同じ 30 秒にする。

- `execute` を直接呼ぶ 2 か所の `deadline_seconds=5` を `30` にする
- `wait_for()` の `asyncio.timeout(5)` と、同じ差し替えの中の `asyncio.timeout(2)` を `30` にする
- cancel のテスト 2 件の `asyncio.wait_for(task, 3)` と `deadline_seconds=10` を `30` にする（D-223-3）
- `prepare_worktree` を呼ぶ 2 か所の `deadline_seconds=3` を `30` にする
- 値は今のコードの書き方（数値をそのまま書く）に合わせる。`wait_for()` の直前に、テストの足場の待ちは止まらなくなったときの上限にすぎず、負荷の高いホストでは子の起動だけで伸びること（#218・#223）を短いコメントで書く。ほかの箇所は `run()` のコメントと同じ趣旨なので、必要なら 1 行で足す

### 2. 時間切れ・子の停止を時間で確かめるテストは変えない

「確認した事実」の 4 つのテストの `deadline=3` と `elapsed_seconds` の上限、`test_already_cancelled_does_not_spawn` の 5 秒、`test_runner.py` の並行の検査は変えない。

### 3. 検証（テストは足さない。D-223-5）

- 30 秒まで待つテストが無いこと: 変更の前と後で `uv run pytest tools/agent_runner --durations=40` を実行し、時間切れ・中断のテストの所要時間が増えず、30 秒近くかかるテストが無いことを確かめる
- 負荷をかけた検証: 別の pytest を並行で動かした状態で、`uv run pytest tools/agent_runner` を 3 回実行し、3 回とも期限切れ・`TimeoutError` の失敗が出ないことを確かめる。各回の load average と `--durations` の上位を記録する
- `README.md` の「テスト」の入口（ワールドの行を除く）

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-223-1 Issue の案 (a) を採る**
  - 選択: 時間切れを確かめないテストが明示した短い期限と待ちを、補助の既定と同じ 30 秒にする
  - 別案: (b) 失敗を観測するまで待ち、観測したものから 1 件ずつ直す
  - 理由: (b) は #218 と同じく、負荷の高い時間帯にどれが落ちるかが毎回変わり、見つかるたびの対応になる。30 秒は #218 で既定にした値で、通る場合の所要時間は変わらず、長くなるのはテストが壊れて止まらなくなった場合の待ちだけである
- **D-223-2 Issue の表を今の `main` に合わせて読み替える**
  - 選択: 「確認した事実」の表の箇所を対象にする。消えた 2 件のテスト（`test_process.py:104` の `deadline=10` を含む）は、対応が要らない
  - 別案: Issue の表の行番号のまま探して、見つからないものを止まる理由にする
  - 理由: #230 で消えたことを `git log -S` で確かめた。Issue の目的（残っている短い期限・待ちを直す）は変わらない
- **D-223-3 cancel のテスト 2 件の `execute` の期限 10 秒も 30 秒にする（Issue の表に無い）**
  - 選択: `test_process.py:385`・`442` の `deadline_seconds=10` を `30` にする
  - 別案: Issue の表のとおり、`wait_for()` と `asyncio.wait_for(task, 3)` だけを変える
  - 理由: `test_coroutine_cancellation_stops_leader_and_escaped_descendant` は、`wait_for()` の待ちが終わってから cancel する。待ちを 30 秒にしても、負荷で起動が 10 秒を越えると期限 10 秒が先に来て、テストが失敗するか、cancel を確かめなくなる（「確認した事実」）。`test_repeated_cancellation_during_launch_still_stops_process` は期限に届かないので、30 秒は値をそろえるためだけで、害も無い。どちらも cancel を確かめるテストで、期限を確かめない。Issue の案 (a) の基準（時間切れを確かめないテストの期限を 30 秒にする）にそのまま当たり、範囲を広げない
- **D-223-4 `test_immediate_exit_before_ownership_observation_stops_children` の差し替えの中の `asyncio.timeout(2)` も 30 秒にし、`deadline=3` と `elapsed_seconds < 2` は変えない**
  - 選択: `asyncio.timeout(2)` を `30` にする（共有の `wait_for()` も 30 秒になる）。テスト自身の `deadline=3` と `elapsed_seconds < 2` は残す
  - 別案: (a) このテストの待ちを 2 秒・5 秒のまま残す、(b) `deadline=3` と `elapsed_seconds < 2` も緩める
  - 理由: このテストの負荷への強さは、自身の `elapsed_seconds < 2` で決まり、待ちを伸ばしても変わらない（「確認した事実」）。それでも待ちを 30 秒にそろえると、負荷で遅れたときに `elapsed_seconds` の assert で失敗し、`finally` が 60 秒の子を止める。2 秒の `TimeoutError` で失敗すると、子が `finally` の対象に入らない。(b) は、子を待たないこと（60 秒の子を待てば `timed_out`、短い待ちを足せば `elapsed_seconds` の上限で落ちる）を確かめる意図の期限を変えるので、Issue の「時間切れを確かめる意図のある短い期限は変えない」に反する。このテストが負荷で落ちることが分かったら、別の Issue の候補にする（PR の持ち越し候補に書く）
- **D-223-5 テストを足さない**
  - 選択: 実行して確かめる（設計の 3）。テストのコードは期限・待ちの値とコメントだけを変える
  - 別案: (a) 値が 30 秒であることを確かめるテスト、(b) 所要時間を確かめるテスト
  - 理由: `AGENTS.md` の「テストの採用基準」で、値だけの変更にはテストを書かない。(a) は今の値を写す F に当たる。(b) は負荷で所要時間がぶれるので、それ自体が不安定なテストになる
- **D-223-6 負荷をかけた検証の形**
  - 選択: README の pytest の入口全体（`uv run pytest tests/skills .agents/skills .agents/scripts tools`）を同じ worktree で 3 本並行で繰り返し実行し続けた状態で、`uv run pytest tools/agent_runner` を 3 回続けて実行する。各回の前後の load average と `--durations` の上位を記録する
  - 別案: (a) 負荷をかける専用のプログラム（`stress` など）を使う、(b) 変更の前の値でも同じ負荷で実行して失敗を再現する、(c) 並行の pytest を 1 本にする
  - 理由: Issue の検証（別の pytest を並行で動かす）に合わせ、発生（別の作業の pytest や git が並行する）に近い形にする。#218 の検証で 1 本では load average が 5 前後にしかならず意味が薄かったので、3 本にする。pyproject の `addopts` に `-p no:cacheprovider` があり、テストは `tmp_path` を使うので、同じ worktree で並行しても互いの結果を書き換えない。(a) は新しい依存が要る。(b) は再現が負荷の大きさに左右され、再現しなくても修正の正しさは否定されないので、受け入れ条件にしない
- **D-223-7 実行方式は inline（`superpowers:executing-plans`）**
  - 選択: このセッションが Plan の Task を順に実装する
  - 別案: `superpowers:subagent-driven-development`
  - 理由: `check` の `self` が true。変更は 2 つのファイルの値とコメントだけで、子に文脈を渡す手間が実装より大きい。最後のブランチ全体のレビューは省かない

## 受け入れ条件

1. 「確認した事実」の表の 10 か所が 30 秒になり、時間切れ・子の停止を時間で確かめるテストの期限と上限、`test_already_cancelled_does_not_spawn` の 5 秒は変わらない（`git diff` で確かめる）
2. 変更の後の `uv run pytest tools/agent_runner` が通り、時間切れ・中断のテストの所要時間が変更の前と同程度で、30 秒まで待つテストが無い
3. 別の pytest を並行で動かした状態で、`uv run pytest tools/agent_runner` を 3 回実行し、3 回とも期限切れ・`TimeoutError` の失敗が出ない
4. `README.md` の「テスト」の入口（ワールドの行を除く）が、すべて終了コード 0 になる

## 範囲外

- runner・process・workspace の本体（`tools/agent_runner/` のテスト以外）の変更
- 時間切れ・子の停止を時間で確かめるテストの期限と上限（D-223-4 の (b)。負荷で落ちることが分かったら別の Issue の候補）
- `test_runner.py:561` の並行の上限の時間の検査
- #128（一括実行で不安定に失敗する別のテスト）
- CI（`AGENTS.md` の「GitHub Actions」）

## 実装者に任せること

- コメントの文面（周りのテストの期限の説明に合わせる）

## PR #263 のレビュー修正（サイクル 1）

- 実行許可: 利用者の `/issue-to-pr #223 --merge --max-cycles 3`。issue-to-pr の 5 章のとおり PR 修正ループ（run `56b0486529c6422995ed58609a3b79a6`）を回し、review-fix-planning の完遂で判断した。結論 2 のマージと関連 Issue の更新は `finalize.py` が行う
- planner: `claude-opus-5-5`（claude-code）。サイクル 1（判断の記録の round 1）で、前のサイクルの記録は無い
- 対象: PR の head `cc54fe10a594470430c98b06de3adfb469fa05ec`。base `main` の先端は、PR の作成の前に PR #260 のマージで `7e21c10f1c60309622f116572141a7fceb4cbe61` に進んでいた（merge-base は `dcdc0d9`）
- 入力: `reviews/usaturn/create-reso-world/#263-fix-issue-223-agent-runner-test-deadlines/` の 4 レビューファイルと `findings/*-cc54fe10a594.json`。候補 JSON は 4 件とも `validate`・`check-pair` を通った
- 確認済みの一覧: `verified/cc54fe10a594.json`（review-verify の mode cycle。確認担当は planner 自身）。confirmed 1（V-1）・not_reproduced 0・unverified 0。未確認の範囲は load average 約 21 での再現だけ（共有ホストで他の作業の検証を壊すおそれがあるため。観測した最大は約 18）

| レビューファイル | モデル | ランタイム | 担当 | レビュー HEAD | 今回再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus-5-5 | claude-code | claude-opus | `cc54fe10a594` | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | devin-swe | `cc54fe10a594` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | pi-deepseek | `cc54fe10a594` | はい | Approve |
| `Grok-4.7.md` | Grok 4.7 | cursor | cursor-grok47 | `cc54fe10a594` | はい | Approve |

- 指摘の振り分け: 解消済み 0 / 対応する 0 / 対応しない 1
  - 対応しない `SWE-2-Max#I-1@cc54fe10a594`（Info）: `wait_for()` のコメント（`test_process.py:248`）が、`deadline=3` と `elapsed_seconds < 2` を確かめる `test_immediate_exit_before_ownership_observation_stops_children` の呼び出し元に当てはまらず、278 行の `asyncio.timeout(30)` にも説明が無い。確認済みの一覧の V-1 で、静的な主張として事実を確かめた。コメントの文面だけで、テストの合否・挙動・後続の手順の結果を変えないので、致命的ではない。最終レビューの M-3 と同じ点で、PR 本文と Plan に持ち越し候補として書いてある
  - 「対応する」項目が無いので、守る条件と影響経路の表は作らない
- planner の確認: PR の変更ファイルの全文（`test_process.py`・`test_workspace.py`、この Spec、Plan）、関連する処理（`process.py` の `execute` の期限と `elapsed_seconds` の扱い、`workspace.py` の `prepare_worktree`）と、`wait_for()` の 3 つの呼び出し元を読んだ。PR の欠陥は見つからなかった
- 結論: 2 修正不要としてマージする
- 検証: head `cc54fe1` に base の先端 `7e21c10` を一時の隔離 worktree で merge したツリー（競合なし。push しない）で、`bash .devcontainer/run-tests.bash` は終了コード 0（PASS: 23 test(s)）、`bash scripts/check-layout.sh` は 0、`uv run pytest tests/skills .agents/skills .agents/scripts tools` は 0（1224 passed）。検証した base は `7e21c10f1c60309622f116572141a7fceb4cbe61`。head だけのツリー（未 commit の変更なし）でも 3 つとも 0（PR の作成の前の記録。pytest は 1224 passed）
- 自己レビュー: 修正が無い（結論 2）ので行っていない。`run_roles.py` も実行していない
- 所要時間: レビュー 19:51Z〜20:03Z（約 12 分）、確認済みの一覧と計画・merge したツリーの検証 20:04Z〜20:18Z ごろ（約 14 分）
