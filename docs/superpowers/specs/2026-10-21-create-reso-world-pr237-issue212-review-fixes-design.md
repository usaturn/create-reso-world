# PR #237（Issue #212）レビュー修正: 診断の原因は試行を終わらせた失敗から決め、観測できなければ推測しない

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 PR: https://github.com/usaturn/create-reso-world/pull/237（Issue #212）
- 状態: completed
- 関連する文書: 実装の Spec `docs/superpowers/specs/2026-10-21-create-reso-world-issue212-reviewer-failure-diagnostics-design.md`、Plan `docs/superpowers/plans/2026-10-21-create-reso-world-issue212-reviewer-failure-diagnostics.md`
- サイクル: 1（判断の記録は無かった）。planner: `claude-opus-5-5`（Claude Code 2.1.306）
- 判断の対象の HEAD（`reviewed_head`）: `d0004f264c85d18f3896ac3662635ea3aa6de2f6`、base `7d4435581c3aa0c0a06b94f9a92bd0326d0f4e2e`
- 実行許可: 利用者の `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/212 --merge --assign implement=self …`（実装の Spec の「管理・実行許可」に全文）。`--merge` により PR 修正ループ（run `3ef875d966de450db44f94773689151e`）の計画として review-fix-planning の完遂を行う（その PR の承認済み実装修正と、結論 2 のマージ・関連 Issue の更新の実行許可）。内容の承認（`approved`）ではない
- 専用の worktree: PR の head ブランチ `fix/issue-212-reviewer-failure-diagnostics` を checkout した `/workspaces/reso-world/.worktrees/issue-212-reviewer-failure-diagnostics`（clean・HEAD 一致のものを再利用。片付けの対象にしない）
- 担当（`run_roles.py` の割り当て。ループの `planning.run_roles_options` は `--template .devcontainer/agent-runner.toml --assign implement=self`）: 修正 `self`（利用者の指定）、自己レビュー `self`・修正の確認 `self`（雛形の既定）。自己レビューは `run_roles.py --phase self-review` の 1 回
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#237-fix-issue-212-reviewer-failure-diagnostics/verified/d0004f264c85.json`（review-verify mode cycle、V-1・V-2 とも confirmed）。修正の確認: 同じディレクトリの `a2ad29805761.fix-check.json`（V-1・V-2 とも confirmed）。工程の記録: `d0004f264c85.planning.json`
- 修正の commit: `a2ad298`（レビュアーの指摘 2 件）、`7dd2bdc`（自己レビューの M-1 と修正の確認の V-1）

## レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `SWE-2-Max` | SWE-2 Max | devin | `d0004f264c85` | はい | Approve |
| `claude-opus-5-5` | claude-opus-5-5 | claude-code | `d0004f264c85` | はい | Approve |
| `deepseek-deepseek-v4.1-flash` | deepseek/deepseek-v4.1-flash | pi | `d0004f264c85` | はい | Approve |
| `gpt-6.1-sol` | gpt-6.1-sol | pi | `d0004f264c85` | はい | Approve |
| `claude-opus-5-5-commit-a2ad298057618d6532436a21841ab53a2672fe81` | claude-opus-5-5 | claude-code | `a2ad29805761` | いいえ（修正の commit `a2ad298` の自己レビュー。指摘はこのサイクルで判断した） | Approve |

## 全指摘と区分

判断 4 件（指摘 6 件）: 解消済み 0 / 対応する 3（指摘 4）/ 対応しない 1（指摘 2）。

| 判断 ID | 出典 | 区分 | 理由 |
| --- | --- | --- | --- |
| `claude-opus-5-5#M-1@d0004f264c85`（確認済みの一覧の V-1） | claude-opus-5-5 | 対応する | 致命的（手順・ツールのとおりに使うと誤った結果）: 個人設定のレビュアー（claude-code 1 人・pi 2 人）が混雑時に出す自動の再試行の行（Claude Code の `system/api_retry`、pi の再試行の前の失敗メッセージ）を、試行を終わらせた失敗として分類し、原因を `connection`・`rate_limit` と誤って記録する。司令塔と利用者が「障害を待つ」「上限を待つ」と誤った対応を取る。(a) 再現した（`verified/d0004f264c85.json` の V-1） |
| `deepseek-deepseek-v4.1-flash#M-1@d0004f264c85`（V-2） | deepseek | 対応する | 致命的（手順・ツールのとおりに使うと誤った結果）: この PR が閉じる Issue #212 の受け入れ条件 2（原因を観測できなければ unknown）と `references/records.md` の `unknown` の定義（ログを読めなかった）に反し、停止確認済み・終了コード 0 でログが無い・置き換わった・読めない試行の原因を、観測していない `response_extraction` と記録する。担当のプロセスは試行の領域に書けるので、回収の前にログが消える・置き換わることがある。(a) 再現した（V-2。4 通り） |
| `claude-opus-5-5-commit-a2ad298057618d6532436a21841ab53a2672fe81#M-1@a2ad29805761`（`fix-check#V-1@a2ad29805761` と同じ問題） | 自己レビュー・修正の確認 | 対応する | 致命的（手順・ツールのとおりに使うと誤った結果）: pi のレビュアーが長いレビューの後に提供元の失敗（終了コード 0）で終わると、会話の履歴全体を含む 1 行の `agent_end`（ローカルの実際のレビューの出力で 1,664,145 バイト・1,913,481 バイト）が末尾 1 MiB の読み取りで切れ、最後の失敗を読めないまま、`partial` を観測とみなして `response_extraction` と記録する（503・500 は `connection`、分類できない 400 は `unknown` になるべき）。(a) 再現した（自己レビューの実際の runner と pi の adapter での再現、修正の確認の `adversarial.py` の B-pi-agent-end-over-limit）。`a2ad298` が明示した守る条件 2（`partial` は観測とみなす）の破れで、きっかけ 3 |
| `claude-opus-5-5-commit-a2ad298057618d6532436a21841ab53a2672fe81#I-1@a2ad29805761`（`fix-check#V-2@a2ad29805761` と同じ論点） | 自己レビュー・修正の確認 | 対応しない | 致命的でない（文書）: 実装は Issue の受け入れ条件 2 と守る条件に合い、動きは変わらない。運用で読む `references/records.md` 4.1 節の `response_extraction`・`unknown`・`partial` の行と、実装の Spec の設計 3 の `response_extraction` の行・設計 4 の後の段落・設計 7 のテストの項は、M-1 の修正（`7dd2bdc`）で守る条件に合わせて書き直した。残るのは、実装の Spec の設計 3 の `unknown` の行（「またはログを読めなかった」）と D-212-8 の選択（観測の条件を書いていない）、Plan の Task 2 の Interfaces の `classify_cause(text, attempt)`・`diagnostic_text(...) -> str` と Step 3 の `diagnostic_text` の説明（実装の前の計画のまま）で、いずれも同じ Spec の設計 4 の後の段落と D-212-13、この Spec が補う |

## 設計の見直し（きっかけ 1・2・3）

- きっかけ 1（同じ守る条件の 2 回目）: レビュアーの 2 件とも、直す仕組みが `_failure_event`・`_failed_messages`・`reported`・`classify_cause` の `response_extraction` の判定で、PR の作成の前の最後のブランチ全体のレビューの修正（`c8d42e0`、実装の Spec の D-212-13。I-1 として pi と DSH の失敗の分類を直した）が直したものと同じである
- きっかけ 2（修正が生んだ回帰）: V-1 の pi の部分は、`c8d42e0` が足した `_failed_messages`（すべての `message`・`messages[]` の失敗メッセージを拾う）が原因である（`git log -S'_failed_messages' 7d44355..d0004f2` は `c8d42e0`）
- きっかけ 3（自己レビューでの再発）: 自己レビューの M-1 と修正の確認の V-1 は、`a2ad298` が守る条件 2 に書いた「上限を超えて末尾だけを読んだ（`partial`）ときは、試行を終わらせた失敗は末尾にあるので、観測したとみなす」の破れである。pi は最後の失敗を、会話の履歴全体を 1 行に含む `agent_end` にも書くので、末尾 1 MiB の読み取りではその行の頭が切れる。`a2ad298` は pi の最後の失敗を `agent_end` からだけ取ったので、直前の小さい `message_end` の同じメッセージも使わなかった（修正の確認の V-1 によれば、同じ入力は `d0004f2` でも `response_extraction`）

### 守る条件の設計

**診断の原因の分類（`cause`）は、観測したログに残る、試行を終わらせた失敗の報告だけから決める。** 次の 3 つを、loop の review が扱うすべての担当の出力（claude-code・pi・dsh・devin・cursor。codex は inspect に割り当てられない）、すべての試行の状態、すべての停止の位置、すべてのログの大きさで保つ。

1. 担当が自動の再試行で回復した一時的な失敗（再試行の通知と、再試行の前の失敗）は、失敗の報告にしない。再試行を使い切って試行が失敗したときは、その最後の失敗を報告にする
2. 失敗の報告の有無を観測できないとき（stdout・stderr の一方でも、記録が無い・無い・リンクか特殊ファイル・読めない・出力の外・`sensitive_paths`・停止未確認で読まなかった・上限を超えて末尾だけを読んだ `partial`）は、「報告が無い」とみなして `response_extraction` と推測しない（`unknown`）。`partial` の読んだ部分は照合に使う（自己レビューで `partial` を観測とみなす前提の破れが見つかったので、`7dd2bdc` で `partial` も観測としないことにした）
3. pi の最後の失敗は、ログの行の大きさに依らずに取り出す。stream の中で最後に現れた assistant のメッセージ（pi の `message_start`・`message_end`・`turn_end` の `message` と `agent_end` の `messages`）が失敗で終わっていれば（`stopReason` が `error`）、その `errorMessage` を報告にする。pi は同じメッセージを、履歴を含む `agent_end` の行の前の小さい `message_end` にも書く。stream が `agent_end` で終わるときは、pi の adapter が状態の分類に使う最後の `agent_end` の最後の assistant のメッセージと同じものになる

この条件を保つ仕組みは `diagnostic_text`（stdout から試行を終わらせた失敗の報告を取り出す）、`diagnose_attempt`（観測できたかの判定）、`classify_cause`（`response_extraction` の推測の条件）の 3 か所にまとめる。以前の回の修正で足りなかった理由: `80dc442` は失敗のイベントを「トップレベルの `error` が空でない」などの形で数え、再試行の通知（Claude Code の `api_retry` は `error` を持つ）と区別しなかった。`c8d42e0` は pi の失敗を拾うために、すべての `message`・`messages[]` の失敗メッセージを足したが、pi は再試行の前の失敗も `message_end`・`turn_end` と `agent_end` の履歴に残す。どちらの回も、`response_extraction` の推測に、ログを読めたかを条件にしなかった。`a2ad298` は観測の条件を足したが、「試行を終わらせた失敗は末尾に出る」として `partial` を観測とみなし、pi の最後の失敗を 1 MiB を超えうる `agent_end` の行からだけ取った。

### 比べた直し方（きっかけ 1・2）

- (A) 点の修正を続ける: `api_retry` だけを除き、`_failed_messages` を `agent_end` だけにし、`classify_cause` に `unavailable` を渡す
- (B) 条件を 1 か所で保つ（選択）: `diagnostic_text` の中で、(1) 再試行の通知（`type` か `subtype` に `retry` を含むイベント。`success` が `false` のものだけは `finalError` を最後の失敗として数える）を失敗にしない、(2) pi のメッセージの失敗は、最後の assistant のメッセージだけを使う（pi の adapter と同じ）、(3) 戻り値に「報告の有無を観測できたか」を `classify_cause` の必須の引数として渡す。`classify_cause` の `reported`・`observed` は既定値を持たない
- (C) 保証を狭める: stdout からの分類をやめ、stderr と終了状態だけにする。または `response_extraction` をやめる
- 理由: (B) は条件を「試行を終わらせた失敗の報告」として 1 つの関数で定義し、ランタイムの再試行の形（Claude Code の `api_retry`、pi の `auto_retry_start`・`auto_retry_end`）と pi のメッセージの最終性を同じ場所で扱う。`classify_cause` の引数を必須にするので、観測の有無を渡し忘れる呼び出しが書けない。(A) は同じ関数に条件が散らばり、次の形（別のランタイムの再試行）でまた漏れる。(C) は pi の提供元の失敗（`errorMessage` にだけ出る）と PR #215 の形（終了コード 0 の取り出しの失敗）を分類できなくなり、Issue の目的（原因の切り分け）を狭める

### 比べた直し方（きっかけ 3）

- (A) `partial` を観測としないだけにする: 長いレビューの後の pi の提供元の失敗は、どれも `unknown` になる。誤りは消えるが、Issue の目的（原因の切り分け）を、実際のレビューで起きる大きさのログで失う
- (B) 3 つを合わせる（選択）: (1) pi の最後の失敗は、stream の中で最後に現れた assistant のメッセージから取る（守る条件 3）、(2) `partial` は観測としない（守る条件 2）、(3) 各ログの読み取りの上限を 1 MiB から 64 MiB にし、実際のレビューのログ（pi の stdout は 2 MB 前後）が丸ごと収まるようにする
- (C) 最後の `agent_end` の行だけは、上限を超えても行頭まで遡って読む: 読み取りの処理に行の境界を探す処理が要り、上限（読む量の上限）の意味が崩れる。`agent_end` の無い終わり方（再試行の途中の停止）を扱えない
- 理由: (B) は、pi の最後の失敗を履歴の行の大きさに依らずに取り出し（`message_end` は小さい）、上限を超える極端なログでは推測しない側に倒れる（`unknown`）。(1) は、pi の adapter が使うメッセージと同じものを取るので、回復した失敗を使わない条件（守る条件 1）も変わらない（後に別の assistant のメッセージが続く失敗は最後のメッセージではない）。`stopReason` を書くのは pi だけで、claude-code・cursor の assistant のメッセージは `stopReason` を持たないので、ほかの担当の分類は変わらない（ローカルの実際の出力 30 件で確かめた。実行した検証）。64 MiB は、レビューの 1 回の試行のログが収まり、読み取りの時間・メモリが問題にならない大きさとして選んだ

## 守る条件と影響経路

守る条件: 診断の `cause` は、観測したログに残る、試行を終わらせた失敗の報告だけから決める（回復した失敗を使わず、観測できなければ推測せず、pi の最後の失敗はログの行の大きさに依らずに取り出す）。

対象版は最後の修正の commit `7dd2bdc`。証拠の「loop のテスト」は `7dd2bdc` の `uv run pytest .agents/skills/pr-review-fix-loop/tests -q -p no:cacheprovider`（259 passed、終了コード 0。実行した検証）で、表の各テストはその中で通った。

| 経路 | 判定 | 変更前（`d0004f2`）の挙動 | 観測する結果 | 確かめる方法（assertion） | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| `_failure_event`: Claude Code の `system/api_retry`（`error` が空でない） | 修正する | 失敗のイベントとして数える | 再試行の後に JSON でない回答（終了コード 0）なら `response_extraction`、`rate_limit` の再試行でも同じ | `test_recovered_failures_do_not_decide_the_cause[claude-*]`: `cause` を比べる | `a2ad298` で RED→GREEN（修正の前は 10 failed）。[claude-retry-overloaded]・[claude-retry-rate-limit] は `response_extraction`（修正の前は `connection`・`rate_limit`）。レビュアーの再現の形（`repro.py`）でも `server_error` を含め `response_extraction`。`7dd2bdc` の loop のテストで同じテストが通った |
| Claude Code の再試行を使い切った（`api_retry` の後に `is_error` の `result`） | 既に満たす | 最後の `result` が失敗のイベント | `connection` のまま | 同じテストの `claude-retries-exhausted`: `cause == "connection"` | `a2ad298`・`7dd2bdc` の loop のテストで [claude-retries-exhausted] は `connection`（修正の前も同じ。回帰の確認） |
| pi の再試行の前の失敗（`message_end`・`turn_end` の `stopReason: error`、`agent_end` の履歴） | 修正する | すべて拾う | 再試行の後に JSON でない回答なら `response_extraction`、最後が 503 なら `connection` | 同じテストの `pi-*`: `cause` を比べる | `a2ad298` で RED→GREEN: [pi-retry-recovered] は `response_extraction`、[pi-retry-then-503] は `connection`（修正の前はどちらも `rate_limit`）。`7dd2bdc` は最後の assistant のメッセージの取り方を変えたが（下の行）、再試行の前の失敗は後に別の assistant のメッセージが続くので最後にならない。`7dd2bdc` の loop のテストで同じテストが通った |
| pi の `auto_retry_start`・成功した `auto_retry_end` | 修正する（明示） | `retry` の型は失敗のイベントに当たらないが、条件として明示していない | 失敗にしない | 同じテストの `pi-retry-recovered`（`auto_retry_end` が `success: true`） | `a2ad298`・`7dd2bdc` の loop のテストで [pi-retry-recovered] は `response_extraction` |
| pi の再試行を使い切った・取り消した（`auto_retry_end` の `success: false`・`finalError`） | 修正する | `finalError` を見ない | `finalError` で分類する（分類できなければ `unknown`、`response_extraction` にしない） | 同じテストの `pi-retries-exhausted`・`pi-retry-cancelled` | `a2ad298` で RED→GREEN: [pi-retries-exhausted-without-agent-end] は `connection`（修正の前は `rate_limit`）、[pi-retry-cancelled] は `unknown`（修正の前は `response_extraction`）。`7dd2bdc` の loop のテストで同じテストが通った |
| pi の最後の assistant のメッセージ（`stopReason: error`）の取り出し | 修正する（`7dd2bdc`） | すべての `messages` の失敗メッセージ（`a2ad298` は最後の `agent_end` の最後の assistant のメッセージだけ） | stream の中で最後に現れた assistant のメッセージ（`message_start`・`message_end`・`turn_end` の `message`、`agent_end` の `messages`）の `errorMessage` で分類し、プロンプトは使わない | `test_reported_failures_are_not_response_extraction`（`agent_end` の形）、`test_final_pi_failure_survives_a_long_history[final-message-without-agent-end]`（`message_end` だけ）: `cause` を比べる | `7dd2bdc` で RED→GREEN: [final-message-without-agent-end] は `connection`（修正の前は `response_extraction`）。`test_reported_failures_are_not_response_extraction` 4 件は `7dd2bdc` の loop のテストでも通った。ローカルの実際の pi の `awaiting_authentication`（2 件。401 を含む）は `authentication` |
| pi の `agent_end` の行（履歴全体）が 1 MiB を超える | 修正する（`7dd2bdc`） | 末尾 1 MiB の読み取りで行の頭が切れ、最後の失敗を読めず、`response_extraction`（`a2ad298` は `partial` を観測とみなして同じ結果） | 上限（64 MiB）の内なら行の大きさに依らず `message_end` の最後の失敗で分類する（503 は `connection`）。上限を超えて末尾しか読めなければ `unknown` | `test_final_pi_failure_survives_a_long_history[history-line-over-1-mib]`（約 1.5 MB の `agent_end`、上限は既定）・[history-line-over-the-limit]（上限を 4096 バイトにする）: `cause` を比べる | `7dd2bdc` で RED→GREEN（修正の前は 4 failed: この 2 件・上の行・下の [stdout-partial-unknown]、修正の後に `test_loop_diagnostics.py` 68 passed）: [history-line-over-1-mib] は `connection`、[history-line-over-the-limit] は `unknown`（修正の前はどちらも `response_extraction`）。自己レビューの再現（実際の runner と pi の adapter、1.3 MB の `agent_end`）は `a2ad298` で `response_extraction` |
| DSH の `type: error`・`turn_end` の `reason.kind: error`・stderr の `dsh: <CODE>:` | 既に満たす | 失敗の報告 | 変わらない（DSH は adapter の設定で再試行しない: `retryPolicy.maxRetries = 0`。DSH のイベントは `stopReason` を持たない） | 既存の `test_cause_uses_only_failure_channels[dsh-*]` | `7dd2bdc` の loop のテストで `test_cause_uses_only_failure_channels[dsh-*]` 7 件が通った。ローカルの実際の dsh-ccd の `TRANSPORT` は `connection`（`7dd2bdc` でも同じ） |
| claude-code・cursor の失敗した `result`（`is_error`・`subtype` が `error`）、`type: error`、`error` 付きの assistant | 既に満たす | 失敗の報告 | 変わらない。claude-code・cursor の assistant のメッセージは `stopReason` を持たないので、`7dd2bdc` の最後のメッセージの取り出しで失敗にならない | 既存の `test_cause_uses_only_failure_channels[event-*]` | `7dd2bdc` の loop のテストで `test_cause_uses_only_failure_channels[event-*]` 4 件が通った。ローカルの実際の claude-code・cursor・codex の成功した試行（6 件）は `unknown` |
| `classify_cause` の `response_extraction`: ログを読めない（`not_recorded`・`missing`・`not_regular_file`・`unreadable`・`outside_output`・`sensitive`・`not_stopped`） | 修正する | 終了状態だけで `response_extraction` | `unknown` | `test_unobservable_logs_are_not_response_extraction`: stdout・stderr それぞれで `cause == "unknown"` | `a2ad298` で RED→GREEN: [stdout-missing]・[stderr-missing]・[stderr-symlink]・[stderr-unreadable] は `unknown`（修正の前は `response_extraction`）。`repro.py` の 4 通りも `unknown`。`7dd2bdc` の loop のテストで同じテストが通った |
| `classify_cause` の `response_extraction`: 上限を超えて末尾だけを読んだ（`partial`） | 修正する（`7dd2bdc`） | `response_extraction`（`a2ad298` も同じ） | `unknown`（切れた行に最後の失敗が隠れうる） | `test_unobservable_logs_are_not_response_extraction[stdout-partial-unknown]`: `cause == "unknown"` と `unavailable.stdout == "partial"` | `7dd2bdc` で RED→GREEN（修正の前は `response_extraction`） |
| `classify_cause` の `response_extraction`: ログを丸ごと読めて報告が無い（空のログ） | 既に満たす | `response_extraction` | 変わらない | 既存の `test_response_extraction_is_decided_from_the_end_state` | `7dd2bdc` の loop のテストで 6 件が通った。ローカルの実際の Devin の終了コード 0 の `response_failed`（3 件）は `response_extraction`（`7dd2bdc` でも同じ） |
| stdout の JSON でない診断の行（devin・cursor の CLI の行）、stderr の全体 | 対象外 | 失敗の報告 | 変わらない。claude-code・pi は再試行を stdout のイベントで出す。devin・cursor の再試行の出力の形は、ローカルに出力が残っておらず確かめられない（確認済みの一覧と修正の確認の `coverage.remaining`）。形が分かったら同じ関数に足す | ― | 理由のとおり |
| codex | 対象外 | ― | loop の review は codex を inspect に割り当てられない（`load_assignments`） | ― | 理由のとおり |
| 文書: `references/records.md` 4.1 節、実装の Spec の設計 3・4・7 と D-212-6・D-212-13、`loop.py` の docstring・コメント | 修正する | 再試行・観測・読み取りの上限の条件が無い、または `partial` を観測とみなす | 守る条件を書く | `git diff` で照合 | `git diff d0004f2 a2ad298` と `git diff a2ad298 7dd2bdc` で、records.md 4.1 節（守る条件、最後の assistant のメッセージ、64 MiB、`response_extraction`・`unknown`・`partial` の行）、実装の Spec の設計 3・4・7 と D-212-6・D-212-13、`DIAGNOSTIC_READ_BYTES` のコメント・`diagnostic_text`・`classify_cause` の docstring・`diagnose_attempt` のコメントを照合した。残る文書の食い違いは「全指摘と区分」の I-1 の行のとおり（対応しない） |

## 修正方針

- `loop.py`
  - `diagnostic_text(stdout, stderr) -> tuple[str, bool]` は、stdout から試行を終わらせた失敗の報告だけを取り出す。再試行の通知（`type` か `subtype` に `retry` を含む）は失敗にせず、`success` が `false` のものだけ `finalError`（文字列でなければ空）を報告にする。pi のメッセージの失敗は、stream の中で最後に現れた assistant のメッセージ（`_latest_assistant`: `message`・`messages` の中の最後の assistant）が `stopReason: error` のときの `errorMessage` だけを使う（`a2ad298` は最後の `agent_end` だけ、`7dd2bdc` で全イベントに広げた）
  - `classify_cause(text, attempt, *, reported: bool, observed: bool)`。`response_extraction` は `observed` のときだけ（引数は既定値なし）
  - `diagnose_attempt` は、stdout・stderr の `unavailable` に理由が無いときだけ `observed` にする（`a2ad298` は `partial` も観測とした。`7dd2bdc` で外した）
  - `DIAGNOSTIC_READ_BYTES` は 64 MiB（`7dd2bdc`。それまでは 1 MiB）
- 文書: `references/records.md` 4.1 節、実装の Spec の設計 3・4・7・D-212-6・D-212-13、`loop.py` の docstring・コメントに、守る条件（回復した失敗を使わない、観測できなければ推測しない、最後の assistant のメッセージ、64 MiB）を書く
- テスト（`test_loop_diagnostics.py`）: 上の表の新しいテストを足し、`test_reported_failures_are_not_response_extraction` の pi の形を `agent_end` の形に直す（`message_end`・`turn_end` だけの再試行の前の失敗は試行を終わらせた報告ではない）。`7dd2bdc` で `test_final_pi_failure_survives_a_long_history` を足し、[stdout-partial] の期待を `unknown` に変えた

## 結論

結論 1（修正して push する）。対応する 3 件（指摘 4 件）を `a2ad298`・`7dd2bdc` で直し、最後の修正の後の検証（実装後の手順 1・2）は 4 つとも終了コード 0 だった。対応しない 1 件（自己レビューの I-1 と修正の確認の V-2）は文書の食い違いで、動きを変えない。

公開の前の照合（convergence.md の「3. 検証と閉じ方」）:

- 経路表の「修正する」「既に満たす」の各行に、対象版 `7dd2bdc` の観測結果と実行証拠がある。判定を変えた経路は、拒否する側（回復した失敗・観測できないログ・`partial` を `response_extraction` にしない）と受け入れる側（使い切った再試行の失敗・最後の失敗メッセージ・丸ごと読めた空のログの `response_extraction`）を対にした
- fixture は実装と同じ仮定を共有しうるので、独立した根拠として、ローカルに残る実際の runner の出力 30 件（分類だけを出した）、自己レビューの実際の runner と pi の adapter での再現、修正の確認の `adversarial.py`（16 通りの入力を修正の前後で実行）、導入済みの pi の `dist/core/agent-session.js` の読み取り（修正の確認）を使った
- 「対象外」の 2 行は、loop の review の割り当て（codex）と、確かめられない出力の形（devin・cursor の再試行）で、保証の範囲（失敗の報告を確かめられた形だけを使う）と矛盾しない

未確認の事項（修正の確認の `coverage.remaining`）:

- claim:C-10 と文書の候補 S-82・S-103: cursor・codex・devin・dsh の adapter が状態の分類に回復した失敗・モデルの本文を使わないこと（`diagnostic_text` の docstring と実装の Spec の D-212-6 の理由の記述）は、修正の確認が期限内に読み切れなかった。loop の分類は adapter の分類に依らないので、動きの保証には影響しない
- claim:C-19: 修正の確認の環境（一時 HOME・`UV_OFFLINE=1`・worktree の外の venv）で `run-tests.bash` の 2 件が pytest を解決できずに失敗した。司令塔の通常の環境では `a2ad298`・`7dd2bdc` とも 33 件 PASS（実行した検証）
- devin・cursor の自動の再試行の出力の形: ローカルに出力が残っておらず確かめられない（経路表の対象外の行）

## 実行した検証

修正の commit ごとに、専用の worktree で実装後の手順 1・2 を実行した。ログは `/workspaces/reso-world/tmp/agents/pr237-review-fix.9sw9xi3x/fix-verify-1/`（`a2ad298`）・`fix-verify-2/`（`7dd2bdc`）（どちらも commit しない）。実行の前後の HEAD は各 commit で、未 commit の変更はこの Spec（未追跡）だけ。

| argv | `a2ad298` | `7dd2bdc`（最後の修正） |
| --- | --- | --- |
| `uv run pytest .agents/skills/pr-review-fix-loop/tests -q -p no:cacheprovider` | 0（256 passed） | 0（259 passed） |
| `bash .devcontainer/run-tests.bash` | 0（PASS: 33 test(s)） | 0（PASS: 33 test(s)） |
| `bash scripts/check-layout.sh` | 0（PASS: check-layout） | 0（PASS: check-layout） |
| `uv run pytest tests/skills .agents/skills` | 0（1610 passed） | 0（1613 passed、578 秒） |

- TDD: `a2ad298` の新しいテストは修正の前に 10 failed（再試行 6、観測できないログ 4）、修正の後に `test_loop_diagnostics.py` 65 passed。`7dd2bdc` の新しいテスト・変えた期待は修正の前に 4 failed（[stdout-partial-unknown]、`test_final_pi_failure_survives_a_long_history` の 3 件）、修正の後に 68 passed
- レビュアーの再現の形（確認済みの一覧の `repro.py`）を `a2ad298` のコードで実行した（`repro-after.log`）: Claude Code の `api_retry`（overloaded・rate_limit・server_error）の後の JSON でない回答は `response_extraction`、再試行を使い切った場合は `connection`、pi の再試行の後の JSON でない回答は `response_extraction`、最後が 503 なら `connection`、ログが無い・symlink・読めない 4 通りは `unknown`
- ローカルに残る実際の runner の結果（`tmp/agents/` の 30 件の試行。pi の結果 10 件を足した。利用者が操作中の pixg は除いた。分類だけを出した）を `7dd2bdc` の `diagnose_attempt` で分類した: dsh-ccd の終了コード 1 の `TRANSPORT` は `connection`、pi の `awaiting_authentication`（2 件）は `authentication`、Devin の終了コード 0 の `response_failed`（3 件）は `response_extraction`、成功した試行 21 件（claude-code 3・codex 1・cursor 2・devin 4・dsh 4・pi 7）はすべて `unknown`（誤検出なし）。DSH の終了コード 0 の `response_failed`・`awaiting_approval` と Devin の `timed_out` は `unknown`（どれも照合に当たらない。DSH の `response_failed` は `sensitive_paths` があるので `response_extraction` と推測せず、ほかの 2 件は `response_extraction` の対象の状態ではない）
- push の前の検査（`scripts/scan-before-push.sh --base origin/main`）: 自己レビューの前に `a2ad298` まで 9 commit で検出なし（push はしていない）。push の前に Spec の commit まで検査し直す

## 自己レビュー

`run_roles.py --phase self-review` の 1 回（run `36fc66e627f741ba9dfc33201ef92a73`、reviewed commit `a2ad298`）。割り当てはどちらも `self` で、司令塔の代わりに新しいコンテキストの claude-opus-5-5 のサブエージェント 2 つが同時に実行した。自己レビュー後の修正（`7dd2bdc`）は再レビューしていない（2 回目のレビューはしない）。

- self-review（pr-review の非対話の入口、観点 2: PR 全体）: `claude-opus-5-5-commit-a2ad298057618d6532436a21841ab53a2672fe81.md`、05:33:58Z〜05:48:29Z（871 秒）。Approve。Medium 1（M-1: pi の 1 MiB を超える `agent_end` で `response_extraction`。実際の runner と pi の adapter で再現）、Info 1（I-1: `unknown` の説明が実装より広い）。差分の 13 ファイルをすべて読んだ
- fix-check（review-verify の `fix_check`、観点 1: 反証、観点 3: 検証の検出力）: `verified/a2ad29805761.fix-check.json`、05:33:42Z〜05:49:18Z（936 秒）。主張 19 件のうち holds 15・violates 2（V-1: `partial` の前提の破れ、V-2: 文書）・unchecked 2（C-10・C-19）。観点 1 は 16 通りの入力を修正の前後で実行し、破れたのは V-1・V-2 だけ。観点 3 は `loop.py` だけを修正の前に戻すと新しいテストが 10 件落ちることを確かめ、[stdout-partial] は V-1 を検出しないと指摘した（`7dd2bdc` で期待を `unknown` に変え、`test_final_pi_failure_survives_a_long_history` を足した）
- 判定: M-1 と V-1 は致命的として `7dd2bdc` で直した（きっかけ 3。経路表の `7dd2bdc` の行）。I-1 と V-2 は文書の食い違いで致命的でないので対応しない（「全指摘と区分」）
