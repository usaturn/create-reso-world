# Issue #264: agent_runner の並行の上限のテストを、開始の差ではなく区間の順序で確かめる

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/264（ラベル `bug`。親 Issue・依存・コメントは無い。関連: #218、#223、PR #263）
- 状態: draft。内容の承認は記録しない
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue264-concurrency-test-overlap.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-264-concurrency-test-overlap`（branch `fix/issue-264-concurrency-test-overlap`）。PARENT_ROOT: `/workspaces/reso-world`
- 基準: `origin/main` の `115f7c3`
- 実行許可: 2026-10-25（JST）、利用者が `/issue-to-pr #264 --merge --max-cycles 3` を実行した。issue-to-pr の規則により、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成（`Closes #264`）まで続け、PR の作成後に PR 修正ループを回し、修正不要と確かめられたらループの中の `finalize.py` がマージと関連 Issue の更新まで行う。これは実行の許可であり、この文書の内容の承認ではない。下の判断は、どれも確認を取らずに決めたエージェントの判断である
- ループの設定: `loop.py check-options --max-cycles 3` の出力は `options={"max_cycles": 3, "assign": {}, "template": "/workspaces/reso-world/.devcontainer/agent-runner.toml", "config": null}`。`--max-cycles 3` は利用者の指定、`assign: {}`・`template`・`config: null` は既定の適用。レビュアーは `claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正の担当は `claude-opus`、自己レビューと修正の確認は `self`（いずれも設定のとおり）
- 実装の担当: `implement_task.py check` の出力は `assignment={"agents": ["self"], "fallback": []}`、`self=true`。雛形 `.devcontainer/agent-runner.toml` の既定の適用で、`--implement` は付けていない

## 意図

`tools/agent_runner/tests/test_runner.py` の `test_concurrency_bounds_whole_assignments` は、`concurrency=2` で 3 つの担当を走らせ、偽の CLI が書く開始時刻の差（1 件目と 2 件目が 0.2 秒未満、3 件目が 0.23 秒以上）で並行の上限を確かめている。開始時刻には worktree の作成・supervisor と子の起動の時間が入るので、負荷が高いと、本当に同時に始めていても差が 0.2 秒を越えて落ちる（PR #263 の検証で 1 回、約 0.26 秒）。一括の検証が PR と無関係に失敗すると、issue-to-pr の `--merge` の検証の記録や review-fix-planning の結論 2 の検証で、再実行と切り分けの手間がかかる。

並行の上限を壊した版（上限を無視する、1 件ずつ走らせる）で落ちるというテストの守りは残したまま、負荷で所要時間が伸びても正しい実装では落ちない形にする。

## 確認した事実（2026-10-25、`115f7c3`）

- テスト（`test_runner.py:547-562`）は、3 つの担当に `{"sleep": 0.25, "marker": <path>}` を渡し、`starts[1] - starts[0] < 0.2` と `starts[2] - starts[0] >= 0.23` を確かめる
- 偽の CLI（`test_runner.py` の `_SCRIPT`）は、`marker` があれば開始時に `time.monotonic()` を書き、`sleep` だけ眠ってから、出力・receipt を書いて終わる
- runner（`tools/agent_runner/runner.py` の `batch()`）は、担当ごとに `async with semaphore:`（`asyncio.Semaphore(concurrency)`）の中で、worktree の作成・起動・後始末を含む `attempt()` を、fallback を含めて順に行う。slot は、担当の最後の試行のプロセスが終わり、結果を集めた後に空く。役割の期限は slot を取った後から数え、テストの `configuration()` の既定は 30 秒（#218）
- `marker` を使う他のテスト（`test_cancel_during_run_prevents_fallback`、`test_checkout_preparation_is_supervised`、`test_cancel_at_preparation_completion_retains_log_paths`）は、ファイルの有無か大きさ（`written()`）だけを見る。どれも、偽の CLI が眠り終える前に止まるか、起動されない
- `time.monotonic()` は Linux ではシステム全体の `CLOCK_MONOTONIC` なので、別のプロセスが書いた値を比べられる（今のテストも同じ前提）
- 変更の前の基準（load average 7.77、単独で 1 回）: このテストは 1.26 秒で通った。ログは `/workspaces/reso-world/tmp/agents/issue-264.1kdw7dgt/baseline-single.log`

## 設計

### 1. 1 件目と 2 件目の重なりを、偽の CLI の待ち合わせで作る

偽の CLI に、他の担当の `marker` を待つ option（`peers`: 待つ `marker` のパスの一覧、`quorum`: 開始していなければならない件数）を足す。偽の CLI は、自分の `marker` を書いた後、`peers` のうち `quorum` 件の `marker` が現れるまで短い間隔で待ち、それから `sleep` だけ眠る。眠り終えたら、自分の `marker` に終了時刻を追記する。

テストは 3 つの担当に `peers`（3 つの `marker`）・`quorum=2`・`sleep=0.25` を渡す。

- 正しい実装では、先に slot を取った 2 件が互いの開始を待ち合わせる。1 件目は 2 件目の `marker` を見てから終わるので、2 件目の開始がどれだけ遅れても（役割の期限 30 秒の中で）、2 件の区間は必ず重なる
- 3 件目は、どちらかの slot が空いてから worktree を作って起動する。slot が空くのは、偽の CLI が終了時刻を書いて終わった後なので、3 件目の開始は、先に終わった担当の終了時刻より必ず後になる
- どちらも処理の順序で決まり、時間のしきい値に依らない

### 2. assert を区間の順序にする

各 `marker` から（開始, 終了）を読み、開始の順に並べて、次を確かめる。

- `batch.state == "success"`（今と同じ）
- 2 件目の開始 < 1 件目の終了（同時に 2 件動く）
- 3 件目の開始 > 1 件目と 2 件目の終了の早い方（同時に 3 件は動かない）

### 3. 壊れた版での失敗

- 上限を無視する（3 件同時に走らせる）: 3 件とも同時に起動され、2 件がそろった時点で待ち合わせが終わる。各担当は 0.25 秒眠ってから終わるので、3 件目がその間に始まれば、3 件目の開始が 2 件の終了より前になり、3 つ目の assert で落ちる。0.25 秒は、この壊れ方を検出する幅のためだけに残す（正しい実装の合否には関係しない）
- 1 件ずつ走らせる: 1 件目は 2 件目の開始を待ち続け、役割の期限（30 秒）で止められる。`batch.state` が `success` にならず、1 つ目の assert で落ちる

### 4. 検証（テストは足さない。D-264-5）

- 単独と `uv run pytest tools/agent_runner` で、このテストが通ること。所要時間を変更の前と比べる
- 負荷をかけた検証: README の pytest の入口全体を 3 本並行で繰り返し実行し続けた状態で、(a) このテストだけを 20 回続けて実行し、(b) `uv run pytest tools/agent_runner` を 3 回実行する。どれも落ちないこと。各回の load average を記録する
- 壊れた版: `runner.py` の `asyncio.Semaphore(concurrency)` を、上限を無視する版（`asyncio.Semaphore(3)`）と 1 件ずつの版（`asyncio.Semaphore(1)`）に一時的に変え、このテストが落ちることを確かめる（負荷をかけない状態。上限を無視する版は 3 回）。確かめた後に元に戻し、`git diff` に残らないことを確かめる
- `README.md` の「テスト」の入口（ワールドの行を除く）

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-264-1 Issue の案 (a)（区間で確かめる）を採り、重なりは待ち合わせで作る**
  - 選択: 開始の差ではなく区間の順序で確かめる。1 件目と 2 件目の重なりは、偽の CLI が互いの開始を待ち合わせて作る
  - 別案: (a') 眠る 0.25 秒のまま終了時刻を足して、重なりを時間で確かめる、(b) 眠る時間としきい値を大きくする、(c) 失敗を再び観測するまで待つ
  - 理由: (a') は、観測した失敗の開始の差（約 0.26 秒）が眠る 0.25 秒を越えているので、同じ負荷で重なりの assert が落ちる。(b) は負荷への余裕が増えるだけで、時間で確かめる形が残り、所要時間も伸びる。(c) は #218・#223 と同じ手間が続く。待ち合わせなら、重なりも上限も処理の順序で決まり、負荷で所要時間が伸びても崩れない
- **D-264-2 待ち合わせに独自の上限を持たせない**
  - 選択: 偽の CLI は `quorum` 件がそろうまで待ち続ける。上限は役割の期限（`configuration()` の既定 30 秒）に任せる
  - 別案: 偽の CLI に待ちの上限（例: 5 秒）を持たせ、越えたら先に進んで重なりの assert で落とす
  - 理由: 待ちの上限が、負荷に左右される新しいしきい値になる。役割の期限は #218 で負荷の高いホストに合わせた値で、1 件ずつ走らせる壊れ方は期限切れで `success` にならないので、テストは落ちる（その版では期限の 30 秒ほどかかる）
- **D-264-3 待ち合わせの後に 0.25 秒眠る（今の値を残す）**
  - 選択: 待ち合わせの後に `sleep=0.25` を残す
  - 別案: (a) 眠らない、(b) 3 件目を待つ 2 段目の待ち合わせ（3 件そろうか一定時間まで待つ）、(c) 眠る時間を伸ばす
  - 理由: 正しい実装の合否には関係せず、上限を無視する壊れ方で 3 件目が 2 件の実行中に始まる幅を作るためだけに要る。(a) はその壊れ方を検出できない。(b) は検出の条件が (眠る) と同じで、仕組みが増えるだけ。(c) は所要時間が伸びる。強い負荷の下では、上限を無視する壊れ方を見逃すことがありうるが、正しい実装を誤って落とすことはない
- **D-264-4 終了時刻は同じ `marker` のファイルに追記する**
  - 選択: 偽の CLI が眠り終えた後、`marker` に空白区切りで終了時刻を追記する
  - 別案: 終了時刻を別の option（別のファイル）に書く
  - 理由: `marker` を使う他のテストは、ファイルの有無か大きさだけを見ていて、どれも眠り終える前に止まるか起動されない（「確認した事実」）ので、追記しても結果は変わらない。option を増やさずに済む
- **D-264-5 テストを足さない**
  - 選択: 既存のテスト 1 件と偽の CLI を変えるだけにし、新しいテストは足さない。並行の上限は `AGENTS.md` の「テストの採用基準」の S（競合の防止）に当たる既存の守りで、その代表のまま直す
  - 別案: 待ち合わせの option そのもののテスト、所要時間のテスト
  - 理由: 偽の CLI はテストの足場で、壊れればこのテストが落ちる（L）。所要時間のテストは、それ自体が負荷で不安定になる
- **D-264-6 負荷をかけた検証の形**
  - 選択: #223 と同じく、README の pytest の入口全体（`uv run pytest tests/skills .agents/skills .agents/scripts tools`）を同じ worktree で 3 本並行で繰り返し実行し続けた状態で検証する。このテストだけの 20 回の繰り返しを足す
  - 別案: (a) `stress` などの負荷のプログラム、(b) 変更の前の版でも同じ負荷で失敗を再現する
  - 理由: Issue の検証（別の pytest を並行で動かす）と発生の状況に合わせる。このテストは 1 回が短いので、繰り返しで負荷の高い時間帯を多く通す。(a) は新しい依存が要る。(b) は再現が負荷の大きさに左右され、再現しなくても修正の正しさは否定されないので、受け入れ条件にしない
- **D-264-7 実行方式は inline（`superpowers:executing-plans`）**
  - 選択: このセッションが Plan の Task を順に実装する
  - 別案: `superpowers:subagent-driven-development`
  - 理由: `check` の `self` が true。変更は 1 つのファイルの偽の CLI とテスト 1 件だけで、子に文脈を渡す手間が実装より大きい。最後のブランチ全体のレビューは省かない

## 受け入れ条件

1. `test_concurrency_bounds_whole_assignments` が、開始の差のしきい値を使わず、設計の 2 の 3 つの assert で確かめる。他のテストの `marker` の扱いは変わらない（`git diff` で確かめる）
2. 変更の後、このテストが単独と `uv run pytest tools/agent_runner` で通り、所要時間が変更の前と同程度である
3. 負荷をかけた状態で、このテストの 20 回と `uv run pytest tools/agent_runner` の 3 回が、どれも落ちない
4. 上限を無視する版（3 回）と 1 件ずつの版で、このテストが落ちる。確かめた後に `runner.py` が元に戻っている
5. `README.md` の「テスト」の入口（ワールドの行を除く）が、すべて終了コード 0 になる

## 範囲外

- runner・process・workspace の本体（`tools/agent_runner/` のテスト以外）の変更
- 他のテストの時間の検査（`test_checkout_preparation_is_supervised` の `starts[-1] < stops[0]` など）
- #128（一括実行で不安定に失敗する別のテスト）
- CI（`AGENTS.md` の「GitHub Actions」）

## 実装者に任せること

- option の名前、待つ間隔、コメントの文面（周りのテストの説明に合わせる）
