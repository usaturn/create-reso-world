# Issue #218: agent_runner のテストの補助の既定の期限を、並行作業の負荷で切れない長さにする

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/218（ラベル `bug`。親 Issue・依存・コメントは無い。関連: PR #214（#198）、#128）
- 状態: draft。内容の承認は記録しない
- 関連 Plan: `docs/superpowers/plans/2026-10-21-create-reso-world-issue218-agent-runner-test-deadline.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-218-agent-runner-test-deadline`（branch `fix/issue-218-agent-runner-test-deadline`）。PARENT_ROOT: `/workspaces/reso-world`
- 基準: `origin/main` の `5a6b096`
- 実行許可: 2026-10-21（JST）、利用者が 6 件の Issue を 1 件ずつ issue-to-pr で処理するよう指示し、この Issue の引数を `usaturn/create-reso-world#218 --merge --assign implement=self` とした（「`--merge` と `--assign implement=self` は利用者の指定」「途中で利用者に質問しない」）。issue-to-pr の規則により、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成（`Closes #218`）まで続け、PR の作成後に PR 修正ループを回し、修正不要と確かめられたらループの中の `finalize.py` がマージと関連 Issue の更新まで行う。これは実行の許可であり、この文書の内容の承認ではない。利用者の決定（下の引用）以外の判断は、確認を取らずに決めたエージェントの判断である
- 利用者の決定（指示の「#218」の節をそのまま引用）:
  > - 案 (a) を採る。テストの補助の既定の期限（`tools/agent_runner/tests/test_runner.py` の `configuration()`、`tools/agent_runner/tests/test_process.py` の `run()`）を 5 秒から 30 秒にする
  > - 時間切れ・中断を確かめるテストは、短い期限を明示したままにする。既定の期限に頼って時間切れを確かめるテストが見つかったら、そのテストに短い期限を明示する
  > - 負荷をかけた検証は、別の pytest を並行で動かした状態で `uv run pytest tools/agent_runner` を 3 回実行する
- ループの設定: `loop.py check-options --assign implement=self` の出力は `options={"max_cycles": 3, "assign": {"implement": ["self"]}, "template": "/workspaces/reso-world/.devcontainer/agent-runner.toml", "config": null}`。`--assign implement=self` は利用者の指定、`max_cycles: 3`・`template`・`config: null` は既定の適用。レビュアーは `pi-gpt`・`devin-swe`・`dsh-ccd`・`cursor-grok47`（設定のとおり）、修正の担当は `self`（利用者の指定）、自己レビューと修正の確認は `self`（設定のとおり）
- 実装の担当: `implement_task.py check` の出力は `assignment={"agents": ["self"], "fallback": []}`、`self=true`。雛形 `.devcontainer/agent-runner.toml` の既定の適用で、`--implement` は付けていない（利用者の指示「Plan の Task の実装は、雛形の既定の self（このセッション）で行う」と一致する）

## 意図

`tools/agent_runner` のテストの補助が既定で使う期限 5 秒が、並行作業で負荷の高い時間帯に切れ、時間切れを確かめるのではないテストが `timed_out` で失敗する。失敗するテストは毎回変わり、単独で実行し直すと通る。一括の検証が PR と無関係に不安定に失敗すると、issue-to-pr の `--merge` の検証の記録（すべての終了コードが 0）や review-fix-planning の結論 2 の検証で、再実行と切り分けの手間がかかり、PR の欠陥と取り違えるおそれもある。テストの意図（時間切れの検査）を変えずに、負荷による誤った失敗だけを減らす。

## 確認した事実（2026-10-21、`5a6b096`）

- 補助の定義
  - `tools/agent_runner/tests/test_runner.py` の `configuration()`（180-200 行）は `deadline: float = 5.0` を役割 `inspect` の `deadline_seconds` にする。runner の役割の期限は、並行の枠を取った後から始まり、worktree の作成・準備・すべての fallback を含む（`tools/agent_runner/runner.py` の先頭の docstring）
  - `tools/agent_runner/tests/test_process.py` の `run()`（34-47 行）は `deadline: float = 5` を `execute` の `deadline_seconds` にする
  - `configuration` は `test_review_regressions.py`・`test_checkout_policy.py` も import する。`run` を import するファイルは無い（`alive` だけを import する）
- 時間切れ・中断を確かめるテストは、どれも期限を明示するか、期限の計算を差し替えている
  - `test_runner.py`: `test_role_deadline_covers_fallback_attempts`（`deadline` 4.0・8.0、`execute` と時計を差し替え）、中断の 3 通りのテスト（`deadline=60 if interruption == "cancel" else 3`）、`test_devin_retained_export_is_redacted_after_timeout`（3.0）、`..._after_interruption`（6.0）
  - `test_process.py`: 期限 3 秒を明示する 4 か所（200・373・401・425 行）
  - `test_review_regressions.py`: `test_success_receipt_survives_cli_immediate_exit_with_child` は `configuration(deadline=10)` を明示し、60 秒の子を待つ runner を期限切れで落とす
- 既定の期限を使う中断のテスト（`test_cancel_during_run_prevents_fallback`・`test_preexisting_cancel_launches_nothing`・`test_cancel_at_preparation_completion_retains_log_paths`）は、cancel で止めて `interrupted` を確かめる。期限には頼らない。負荷で 5 秒を越えると `interrupted` の代わりに `timed_out` になりうる
- 既定の期限に頼って時間切れを確かめるテストは、静的に探した範囲では無い（`timed_out` を期待するテストはどれも上のとおり期限を明示する）。変更の後に所要時間で確かめる（設計の 3）
- 補助の外にある 5 秒: `test_process.py` で `execute(..., deadline_seconds=5)` を直接呼ぶ 3 か所（`test_stdin_quotes_multiline_cwd_and_environment_are_literal`、環境変数の受け渡しのテスト、`test_already_cancelled_does_not_spawn`。最後のものは起動しない）と、`test_cli.py` の TOML の `deadline_seconds = 5`（agent の command は `never-invoke-this-command` で、起動しない）
- 変更の前の基準（負荷の低い状態（load average 0.5〜0.9）で `uv run pytest tools/agent_runner --durations=40` を 1 回）: 1056 passed、77.79 秒。所要時間の上位 7 件は、期限 3 秒を明示した時間切れ・中断のテスト（3.01〜3.66 秒。`test_checkout_preparation_is_supervised[late_cancel]`・`[none]`、`test_deadline_kills_term_resistant_leader[True]`・`[False]` など）で、その次は 1.00 秒以下。ログは `/workspaces/reso-world/tmp/agents/issue-218.4_mv9dka/baseline-agent-runner.log`

## 設計

### 1. 2 つの補助の既定の期限を 30 秒にする

- `configuration()` の `deadline: float = 5.0` を `30.0` に、`run()` の `deadline: float = 5` を `30` にする
- それぞれの補助に、既定の期限は止まらなくなった実行の上限にすぎず、負荷の高いホストでは準備と起動だけで伸びること（#218）、期限そのものを確かめるテストは短い期限を明示することを、短いコメントで書く。周りのテストが期限の選び方をコメントで説明している書き方に合わせる

### 2. 時間切れ・中断を確かめるテストは変えない

明示している短い期限（3・4・6・8・10 秒、cancel の場合の 60 秒）はそのまま残す。既定の期限に頼って時間切れを確かめるテストが見つかったら、そのテストに短い期限を明示する（利用者の決定）。

### 3. 検証（テストは足さない。D-218-4）

- 既定の期限まで待つテストが無いこと: 変更の後に `uv run pytest tools/agent_runner --durations=40` を実行し、基準と比べて、時間切れ・中断のテストの所要時間が増えず、30 秒近くかかるテストが無いことを確かめる
- 負荷をかけた検証: 別の pytest（README の pytest の入口全体を繰り返し実行するもの）を並行で動かした状態で、`uv run pytest tools/agent_runner` を 3 回実行し、3 回とも期限切れの失敗が出ないことを確かめる。各回の load average と、遅いテストの所要時間（`--durations`）を記録する
- `README.md` の「テスト」の入口（ワールドの行を除く）

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-218-1 補助の既定の期限を 30 秒にする（Issue の案 (a)）**
  - 選択: `configuration()` と `run()` の既定の期限を 5 秒から 30 秒にする
  - 別案: (b) 失敗したテストを 1 件ずつ直す。既定を 10 秒・60 秒にする。load average から期限を伸ばす
  - 理由: 利用者の決定。(b) は毎回別のテストが落ちるので、見つかるたびの対応になる。Issue の観測では負荷（load average 約 21、8 コア）で 1 件が最大 11.5 秒かかり、30 秒はその 2.6 倍の余裕がある。長くなるのは、テストが止まらなくなって失敗する場合の待ち時間だけで、通る場合の所要時間は変わらない
  - 委任指示: 利用者の決定（上の引用の 1 項目め）
- **D-218-2 時間切れ・中断を確かめるテストは短い期限を明示したままにする**
  - 選択: 明示している期限を変えない。既定の期限に頼って時間切れを確かめるテストは静的に探して見つからなかったので、期限を足す変更は無い。設計の 3 の所要時間の比較で見つかったら、そのテストに短い期限を明示する
  - 別案: 中断のテストにも期限を明示する
  - 理由: 利用者の決定。cancel で止める中断のテストは期限に頼らず、既定の期限が長いほど負荷に強くなる
  - 委任指示: 利用者の決定（上の引用の 2 項目め）
- **D-218-3 補助の外にある 5 秒は変えない**
  - 選択: `test_process.py` で `execute` を直接呼ぶ 3 か所と、`test_cli.py` の TOML の `deadline_seconds = 5` を変えない
  - 別案: これらも 30 秒にする
  - 理由: 利用者の決定は 2 つの補助の既定の期限に限る。これらは個々のテストが明示した値で、#218 の実際の発生には含まれない。`test_cli.py` の agent と `test_already_cancelled_does_not_spawn` は子プロセスを起動しない。負荷で切れることが分かったら、別の Issue の候補として扱う（PR に持ち越し候補として書く）
- **D-218-4 テストを足さない**
  - 選択: 実行して確かめる（設計の 3）。テストのコードは補助の既定値とコメントだけを変える
  - 別案: (a) 既定値が 30 秒であることを確かめるテスト、(b) 所要時間を確かめるテスト
  - 理由: `AGENTS.md` の「テストの採用基準」で、設定値だけの変更にはテストを書かない。(a) は運用で変わる値をテストに写す型（「作らない型」の 3）に当たる。(b) は負荷で所要時間がぶれるので、それ自体が不安定なテストになる
- **D-218-5 負荷をかけた検証の形**
  - 選択: README の pytest の入口全体（`uv run pytest tests/skills .agents/skills .agents/scripts tools`）を同じ worktree で繰り返し実行し続けた状態で、`uv run pytest tools/agent_runner` を 3 回続けて実行する。各回の前後の load average と `--durations` の上位を記録する
  - 別案: (a) 負荷をかける専用のプログラム（`stress` など）を使う、(b) 修正の前の 5 秒でも同じ負荷で実行して失敗を再現する
  - 理由: 利用者の決定（別の pytest を並行で動かす）に合わせ、Issue の発生（別の作業の pytest や git が並行する）に近い形にする。pyproject の `addopts` に `-p no:cacheprovider` があり、テストは `tmp_path` を使うので、同じ worktree で並行しても互いの結果を書き換えない。(a) は新しい依存が要る。(b) は再現が負荷の大きさに左右され、再現しなくても修正の正しさは否定されないので、受け入れ条件にしない
  - 委任指示: 利用者の決定（上の引用の 3 項目め）。並行させる pytest の選び方は推奨案
- **D-218-6 実行方式は inline（`superpowers:executing-plans`）**
  - 選択: このセッションが Plan の Task を順に実装する
  - 別案: `superpowers:subagent-driven-development`
  - 理由: `check` の `self` が true。変更は 2 つのファイルの既定値とコメントだけで、子に文脈を渡す手間が実装より大きい。最後のブランチ全体のレビューは省かない

## 受け入れ条件

1. `configuration()` と `run()` の既定の期限が 30 秒になり、時間切れ・中断を確かめるテストの明示の期限は変わらない（`git diff` で確かめる）
2. 変更の後の `uv run pytest tools/agent_runner` が通り、時間切れ・中断のテストの所要時間が基準と同程度で、既定の 30 秒まで待つテストが無い
3. 別の pytest を並行で動かした状態で、`uv run pytest tools/agent_runner` を 3 回実行し、3 回とも期限切れの失敗が出ない
4. `README.md` の「テスト」の入口（ワールドの行を除く）が、変更の前の基準と同じ結果になる

## 範囲外

- runner・process の本体（`tools/agent_runner/` のテスト以外）の変更
- 補助の外にある 5 秒（D-218-3）と、adapter のテストの期限
- #128（一括実行で不安定に失敗する別のテスト）と、`tools/devenv_migration/tests/test_pi_agent_paths.py` の subprocess の 20 秒の期限切れ（Issue が対象外とした）
- CI（`AGENTS.md` の「GitHub Actions」）

## 実装者に任せること

- コメントの文面（周りのテストの期限の説明に合わせる）
