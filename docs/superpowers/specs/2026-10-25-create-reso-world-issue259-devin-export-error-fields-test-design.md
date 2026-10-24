# Issue #259: Devin の adapter のテストで、export の step の `is_error`・`error` の欄の検出を守る

- 状態: draft
- 文書管理リポジトリ: `usaturn/create-reso-world`（`docs/superpowers/`）
- 対象: `usaturn/create-reso-world` / [Issue #259](https://github.com/usaturn/create-reso-world/issues/259)
- 検証したコードの HEAD: `origin/main` `dcdc0d9adee1f4e6757c1e584ae5a581169b1ac5`（2026-10-24T19:08Z ごろ、worktree を作る前の fetch の時点）
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue259-devin-export-error-fields-test.md`
- 関連: #239・PR #258（発見の経緯）、#228（テストの採用基準）
- 実行許可: 利用者の `/issue-to-pr #259 --merge --max-cycles 3`。通常の設計判断を推奨案で決め、実装・検証・commit・push・PR の作成と、PR 修正ループ（サイクルの上限 3）、その結論に従う `finalize.py` のマージまでを許可する。本 Spec の内容の承認（`approved`）ではない

## 目的

`tools/agent_runner/tests/adapters/devin/test_adapter.py` の `test_export_error_fields_override_answer` が、`tools/agent_runner/adapters/devin.py` の `_export_failure` の `is_error`・`error` の欄の検出を、実際に確かめるようにする。

今のテストは、`_export()` の最後の agent の step の後ろに失敗の step（`source: "agent"`・`message: "answer"`）を足す。最終応答が `"answer"` になり、標準出力 `{"ok": true}` がそれで終わらないので、`_export_failure` が失敗の step を見なくても、回答の照合で `response_failed` になる。検出が壊れると、agent の step に `is_error`・`error` が付いた export で、標準出力が最終応答で終わる実行を `success` と報告する（`AGENTS.md` のテストの採用基準の S: 失敗を成功と報告する）。

## 着手時の確認

1. worktree（`dcdc0d9`）で `uv run --locked pytest -q tools/agent_runner/tests/adapters` は 140 passed
2. `dcdc0d9` を `git archive` で `mktemp -d` に展開したコピーで、devin の adapter のテスト（29 件）を実行した。`_export_failure` から `or step.get("is_error") is True` の行を消す変異、`or step.get("error")` の行を消す変異のどちらでも 29 passed のまま（Issue の主張を再現）
3. 同じコピーで、テストの `.append(failure)` を `.insert(-1, failure)` に変えると、変異なしは 29 passed、`is_error` を外す変異は `[failure1]` が、`error` を外す変異は `[failure0]` が 1 failed になる。失敗の内容はどちらも `status='success', payload={'ok': True}`（失敗を成功と報告する）
4. fixture の `context` の `result_shape` は `json`。Issue の別案（標準出力を足した step の message `"answer"` で終わらせる）では、最終応答 `"answer"` が JSON として読めないので、検出を外しても `response_failed` のままになり、守りにならない

ログは `/workspaces/reso-world/tmp/agents/issue-259.lr_064lf/`（`baseline-adapters.log`、`mutation-before/`）にある。

## 変更の内容

`test_export_error_fields_override_answer` で、失敗の step を最終応答の前に挿入する（`.append(failure)` を `.insert(-1, failure)` にする）。最終応答は `_export()` の `{"ok": true}` のままで、標準出力 `{"ok": true}` はそれで終わるので、`response_failed` にできるのは失敗の step の欄だけになる。その理由を短いコメントに書く。

変えるのは、この関数だけである。パラメータ（2 件）、標準出力、期待値は変えない。

## 対象外

- `tools/agent_runner/adapters/devin.py`（`_export_failure` などの動作）。Issue の対象はテストの守りの不足で、受け入れ条件 2 のとおり挙動を変えない
- 新しいテスト・パラメータ（決定記録の D2）
- 同じファイルのほかのテスト。`test_latest_empty_agent_message_cannot_reuse_earlier_answer`・`test_incomplete_or_failed_export_does_not_reuse_prior_answer` は、最後の step が不完全な場合を確かめるもので、末尾に足すのが意図どおりである。`source: "error"` の step は `test_export_error_step_authentication_overrides_answer`（PR #258）が守る
- 実機の devin の export でこれらの欄が使われるかの観測（Issue の「影響」のとおり未観測で、今回は調べない）

## 受け入れ条件

1. `_export_failure` から `is_error`・`error` の検出をそれぞれ外す変異で、`test_export_error_fields_override_answer` が失敗する
2. 今の挙動（error の欄を持つ step は `response_failed`、その文が認証・承認に当たれば `awaiting_*`）は変わらない。`devin.py` を変えず、差分がテストのファイルと Spec・Plan だけである
3. 変異なしでは、devin の adapter のテストと README の「テスト」の入口が通る

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | 失敗の step を最終応答の前に挿入する（`.insert(-1, failure)`）。標準出力は `{"ok": true}` のまま | (a) 末尾に足したまま、標準出力を `"answer"` で終わらせる（Issue の別案）。(b) 失敗の step の message を JSON にして末尾に足し、標準出力をそれで終わらせる。(c) 隣の `test_export_error_step_authentication_overrides_answer` と同じ `_tool_run_export()`・`_tool_run_stdout()` を使う形に書き直す。(d) 標準出力に `"answer"` も含める（`'answer{"ok": true}'`） | (a) は `result_shape` が `json` なので `"answer"` が読めず、守りにならない（着手時の確認 4）。(b) は失敗の step を最終応答にするので、最終応答と失敗の欄が同じ step に重なり、Issue の現象（最終応答の前の step の欄）から離れる。(c) は変更が大きくなり、変異で確かめる性質は変わらない。(d) は devin が error の欄を持つ step を標準出力に出すかを観測していないので、根拠の無い形を足すことになる。挿入なら 1 行の変更で、変異でそれぞれ失敗することを確かめた（着手時の確認 3） | 委任: `/issue-to-pr #259 --merge --max-cycles 3` の推奨案での決定 |
| D2 | テスト・パラメータを足さない | `is_error`・`error` の欄の文が認証・承認に当たる場合（`awaiting_*`）のパラメータを足す | Issue の方針（テストの件数を増やさない、#228）。文の判定（`_failure_status`）は、`source: "error"` の step の `awaiting_authentication` を確かめる既存のテストと同じ守りで、足すと D（重複）になる | `AGENTS.md` の「テストの採用基準」 |
| D3 | `--merge` のループは `check-options` の結果のままにする。サイクルの上限 3（利用者の指定）、雛形 `.devcontainer/agent-runner.toml`、`--config` なし。inspect は `claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正は `claude-opus`、自己レビューと fix-check は `self`（どれも雛形と個人設定の既定の適用） | ループ用のオプションを足す | 利用者が書いたループ用のオプションは `--max-cycles 3` だけ。ほかは既定の適用で、利用者の指定ではない | 委任: `/issue-to-pr #259 --merge --max-cycles 3`。`check-options` は終了コード 0 |
| D4 | Plan の Task の担当は `self` にする | 別の担当に依頼する | `implement_task.py check` は `agents: [self]`、`fallback: []`、`self: true`。雛形の既定の適用で、利用者は `--implement` を書いていない | 委任: `/issue-to-pr #259 --merge --max-cycles 3`。`check` は終了コード 0 |

## 経路表

観測した結果は、Task 1 の commit `0ec4843` に対するものである。ログは `/workspaces/reso-world/tmp/agents/issue-259.lr_064lf/` の `task1-devin.log`・`mutation-t1/` にある。

| 経路 | 判定 | 観測した結果 | 確かめた方法 |
| --- | --- | --- | --- |
| `is_error` の欄の検出（受け入れ条件 1） | 修正した | 変更前は、検出を外しても 29 passed。変更後は、検出を外すと `test_export_error_fields_override_answer[failure1]` だけが 1 failed（`status='success', payload={'ok': True}`） | `0ec4843` を `git archive` で `mktemp -d` に展開したコピーの変異（`or step.get("is_error") is True` の行を消す） |
| `error` の欄の検出（受け入れ条件 1） | 修正した | 変更前は、検出を外しても 29 passed。変更後は、検出を外すと `[failure0]` だけが 1 failed（同じく `status='success'`） | 同じコピーの変異（`or step.get("error")` の行を消す） |
| 変異なし（受け入れ条件 3） | 既に満たす | 対照のコピーと worktree で 29 passed。`uvx ruff check` と `git diff --check` は終了コード 0 | pytest・ruff |
| `devin.py` の挙動（受け入れ条件 2） | 既に満たす | `git diff --stat origin/main` はテストのファイルと Spec・Plan だけ。`tools/` の差分は `test_export_error_fields_override_answer` の挿入とコメントだけ | `git diff` |
| `source: "error"` の step | 対象外 | `test_export_error_step_authentication_overrides_answer` が守る（Issue の確認のとおり） | — |
