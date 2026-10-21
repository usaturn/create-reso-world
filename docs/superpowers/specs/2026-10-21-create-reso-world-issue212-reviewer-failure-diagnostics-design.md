# Issue #212: 失敗したレビュアーの原因の手がかりを、試行領域の回収の前に run の記録に残す

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/212（親 Issue・ボード・先行 Issue・依存関係は無い。関連: PR #210・PR #215・PR #217（#209）・#175）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-21-create-reso-world-issue212-reviewer-failure-diagnostics.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-212-reviewer-failure-diagnostics`（branch `fix/issue-212-reviewer-failure-diagnostics`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-21（JST）、利用者が次のとおり指示した

  ```text
  /issue-to-pr https://github.com/usaturn/create-reso-world/issues/212 --merge --assign implement=self 利用者の決定を /workspaces/reso-world/tmp/agents/commander-219-220-221-206-212.0smdd1hj/decisions/issue-212.md に置いた。読んで Spec の決定記録に引用せよ
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #212`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う
  - 方針（D-212-1）は利用者の決定に従う。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`（既定の適用）、`assign = {"implement": ["self"]}`（利用者の指定 `--assign implement=self`）、`template = .devcontainer/agent-runner.toml`（既定の適用）、`config = null`。割り当ては、レビュー（`inspect`）が `devin-swe`・`pi-deepseek`・`claude-opus`・`pi-gpt`（個人設定 `~/.config/agent-runner/config.toml` の適用）、修正（`implement`）が `self`（利用者の指定）、自己レビュー（`self-review`）・修正の確認（`fix-check`）が `self`（雛形の既定の適用）。いずれも `fallback` なし
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の `workflows.issue` の既定の適用。個人設定に `workflows.issue` は無い。利用者の指定ではない）
- 基準: `origin/main` の `7d44355`

## 意図

PR 修正ループ（`.agents/skills/pr-review-fix-loop/scripts/loop.py`）の `review` は、runner でレビュアーを起動し、結果を検査した後、同じコマンドの中で runner の出力ディレクトリ（試行ごとの `stdout.log`・`stderr.log`、DSH の session を含む）を回収する。失敗したレビュアーについて run の記録に残るのは、state・終了コード・観測したモデル・消えたログのパスだけなので、司令塔が `review` の結果を受け取ってから原因を調べようとしても、通信・認証・ランタイム・応答の取り出しのどこで失敗したかを切り分ける手がかりが無い（PR #210 の `dsh-ccd`、約 14.3 分の試行。PR #215 の `cursor-grok47`、約 12 分の試行）。

利用者の決定（D-212-1）のとおり、回収の前に、失敗した担当ごとの構造化した診断を run の記録に保存する。診断には、担当・役割・段階・state・adapter が上書きする前に返した state・終了コード・停止確認・所要時間・原因の分類・取得できなかった情報を入れる。原因の分類は、stdout・stderr を既知のパターンと照合した分類名だけを残し、照合した文字列や生のログは写さない。保存できなかったときは、その理由を記録して司令塔に返す。

## 確認した事実（2026-10-21 JST、`7d44355`）

- `_review_batch`（`loop.py:1657-1874`）は、runner の結果を `verify_reviewer`（`loop.py:973-1099`）で検査し、却下した試行の `request.json` を `keep_rejected_request`（`loop.py:1637-1654`）で `cycle-<n>/requests/` に写し（`loop.py:1856-1857`）、結果の写しを書いた後（`loop.py:1858-1859`）、`cleanup_output` を呼ぶ（`loop.py:1861`）。診断を残す段は無い
- `cleanup_output`（`loop.py:1127-1190`）は、記録した出力の名前・種類を確かめ、全試行の停止を確認できなければ何も消さない。停止を確認できたら、出力の中の worktree を外し、`sensitive_paths` が無ければ出力ディレクトリを丸ごと消す（`loop.py:1187`）。失敗した試行でも同じ
- `verify_reviewer` の runner の段階の却下の理由は、停止未確認か「runner の結果が success ではない（state、終了コード）」だけ（`loop.py:991-994`）。`ReviewerEntry`（`loop.py:221-241`）は `rejected_stage`・`reason`・`identity`・`request_file` を持ち、原因の手がかりは持たない
- `keep_rejected_request` は、停止を確認できた試行の通常のファイルの `request.json` だけを写し、秘密が残りうる stdout・stderr は写さない（docstring と `references/records.md` 4 章）
- runner（`tools/agent_runner/runner.py`）は、adapter の `collect` が返した状態（`_collect`、`runner.py:219-282`）を、プロセスの結果で上書きする（`runner.py:531-539`）。期限切れ・起動失敗はその状態、停止未確認は `response_failed`、0 以外の終了は認証待ち・承認待ち・中断以外を `response_failed` にする。上書きの前の値は `Attempt`（`models.py:211-223`）に残らない
- DSH の adapter の `collect`（`tools/agent_runner/adapters/dsh.py:337-379`）は、stdout のイベントを `_classify` で分類し（`dsh.py:347`）、`response_failed` なら stderr で認証待ち・承認待ちを見分ける（`dsh.py:350-354`）。その後、session の識別を読めない（`ValueError` など）と、分類を `response_failed` に上書きする（`dsh.py:359-368`）。Issue のコメント（2026-10-20）のとおり、最初の要求が 401 のときは `awaiting_authentication` が `response_failed` に上書きされる
- 各 adapter（claude-code・cursor・codex・pi・devin・dsh）は、認証・承認の分類に、stderr と stdout の失敗のイベント（`error` の型、`is_error`、失敗した `result` など）だけを使い、モデルの本文やツールの出力は使わない（claude-code の `_classify` のコメント「Successful model prose and tool data may discuss authentication」）
- runner のログは、既知の秘密の値を `[REDACTED]` に置き換えて書く（`process.py:170-244` の `_Redactor`・`_drain`）。大きさの上限は無い。環境の値でない秘密（CLI が表示したトークンなど）は置き換わらない
- `AdapterOutcome`（`adapters/__init__.py:39-43`）は `receipt`・`identity`・`state` だけを持つ。`tools/agent_runner/interfaces.rst` の「Adapter」「結果」の節が形を定める
- `Attempt` を読む側（`review_run_record.py` の `runner_block`、`implement_task.py`、`run_roles.py`、`review-verify` の `dispatch.py`）は、名前を指定して項目を読む。項目が増えても動きは変わらない。`result.json` などの JSON は、同じ checkout の `BatchResult` で読む
- テストの補助: loop は偽の gh・一時 Git・偽のレビュアー（`tests/conftest.py`）、runner は偽の CLI と `FakeAdapter`（`tools/agent_runner/tests/test_runner.py`）、DSH は session の補助 `tools/test_support/dsh.py` を持つ。既存の `test_runner_level_failure_is_not_rerun` と `test_review_records_partial_failure_and_cleans_owned_worktrees` は、失敗の判定と回収を確かめるが、回収の後に原因の手がかりが残ることは確かめない
- 基準の検証（`/workspaces/reso-world/tmp/agents/issue-212.28g3rn4w/baseline/`）の結果は Plan に書く

## 設計

### 1. runner が「上書きする前の状態」を記録する（`tools/agent_runner`）

- `AdapterOutcome` に `reported_state: State | None = None` を足す。adapter が出力から分類した状態を、adapter 自身の後段の検査（DSH の session の識別など）で置き換えたとき、置き換える前の状態を入れる
- `Attempt` に `reported_state: State | None = None` を足す。担当の出力から adapter が分類した状態で、adapter 自身の後段の検査と runner の検査（終了コード・期限・停止・receipt の照合）で `state` を置き換える前の値である。adapter が分類しなかったとき（起動の前の失敗、停止を確認できず収集しない、`collect` の例外、DSH の receipt ファイルの拒否、Devin の export を伏せ字にできない）は null
- `_collect` は、`collect` の戻り値から次の順で `reported_state` を決め、`Attempt` に入れる。`outcome.reported_state`（State の値のときだけ。ほかの値は null として扱い、試行の状態は変えない）、無ければ `outcome.state`（成功以外のとき）、無ければ receipt（ファイル、無ければ adapter が返したもの）の `status`、無ければ `outcome.state`（null か `success`）。`outcome.state` が adapter に許されない値で `invalid_result` にするときは null
- DSH の `collect` は、session の識別の検査で状態を置き換えるとき、置き換える前の状態を `reported_state` に入れる
- `state` の決め方、fallback、各 workflow の採否は変えない。`reported_state` は記録だけに使う
- `interfaces.rst` の `AdapterOutcome` と `Attempt` の説明に、`reported_state` の意味を足す

### 2. loop が回収の前に診断を保存する（`loop.py`）

- 対象: runner の結果の各 `Result` のうち、loop が却下したもの（`verdict == "rejected"`）と、試行に `success` 以外の状態があるもの（fallback で失敗した担当がいて、後の担当が受け付けられたもの）
- 置き場所: `<run_dir>/cycle-<n>/diagnostics/<request_id>.json`。再実行（`rerun`）の結果も同じディレクトリに置く（request ID が違う）。`ReviewerEntry` に `diagnostic_file`・`diagnostic_sha256`・`diagnostic_error` を足す
- 時点: `keep_rejected_request` の直後、`cleanup_output` の前。中断から再開したときも同じ段を通り、同じ内容で書き直す
- 形（`schema` は `pr-review-fix-loop/v1`、`kind` は `diagnostic`）

  | キー | 値 |
  | --- | --- |
  | `request_id`・`role`・`requested_agent`・`actual_agent` | runner の `Result` の値 |
  | `verdict`・`stage` | loop の判定（`accepted`・`rejected`）と却下の段階（`rejected_stage`。受け付けたレビュアーは null） |
  | `state` | runner の `Result.state` |
  | `attempts[]` | 試行ごとに `agent_id`・`state`・`reported_state`・`exit_code`・`stop_confirmed`・`elapsed_seconds`・`cause`・`unavailable` |

- 決定の項目との対応: 担当は `requested_agent`・`actual_agent`・`attempts[].agent_id`、役割は `role`、段階は `stage`、state は `state`・`attempts[].state`、adapter が上書きする前に返した state は `attempts[].reported_state`、終了コードは `attempts[].exit_code`、停止確認は `attempts[].stop_confirmed`、所要時間は `attempts[].elapsed_seconds`、原因の分類は `attempts[].cause`、取得できなかった情報は `attempts[].unavailable`
- 値は、runner・loop の列挙値・数値・識別子（設定の agent 名、runner の request ID）だけで、ログの文字列を入れない

### 3. 原因の分類（`attempts[].cause`）

照合の対象（診断の文）:

- stderr の全体
- stdout の行のうち、JSON の object として読めるものは失敗のイベントだけ（`type` に `error`・`fail` を含む、`is_error` が true、`subtype` が `error` で始まる、`error` が空でない、`reason.kind` が `error`）。失敗のイベントでなければ、stream の中で最後に現れた assistant のメッセージ（pi の `message_start`・`message_end`・`turn_end` の `message` と `agent_end` の `messages`）が失敗で終わっていれば（`stopReason` が `error`）その `errorMessage` だけ（pi の adapter の最後のメッセージと同じ。プロンプトとモデルの本文は使わない）
- 担当が自動の再試行で回復した一時的な失敗は使わない（PR #237 のレビュー修正）。再試行の通知（`type` か `subtype` に `retry` を含む。Claude Code の `system/api_retry`、pi の `auto_retry_start`・`auto_retry_end`）は失敗にせず、再試行を使い切った・取り消した通知（`success` が false）だけを `finalError` で数える。pi の再試行の前の失敗（後に別の assistant のメッセージが続く失敗メッセージ）も使わない
- stdout の行のうち、JSON として読めないものは、行頭（字下げなし）のコロン付き・角括弧付きの診断の行だけ（`Error:`・`fatal:`・`panic:`・`[ERROR]`、`<名前>Error:`・`<名前>Exception:`、`Traceback (most recent call last)`、`dsh:`・`dsh-sandbox:`・`bwrap:` など）。Devin の stdout はモデルの発言の平文なので、「Error handling for ...」のような本文の行や字下げした引用は数えない
- stdout の失敗のイベント・使い切った再試行・pi の最後の失敗メッセージ・診断の行が 1 つでもあれば、ランタイムが試行を終わらせた失敗を報告した（`response_extraction` にしない）
- 各ログは末尾から 64 MiB までを読む（PR #237 のレビュー修正で 1 MiB から広げた。pi の `agent_end` は会話の履歴全体を 1 行に含み、実際のレビューの出力で 1.9 MB ある）

分類（上から順に、最初に当たったものを採る）:

| 分類 | 意味 | 照合の例 |
| --- | --- | --- |
| `authentication` | 認証の失敗（資格情報が無い・無効・期限切れ） | unauthorized、forbidden、invalid api key、not logged in、authentication_error、`MISSING_CREDENTIAL`、DSH の `AUTH`、`HTTP 401`・`status 403` |
| `approval` | 承認待ち・承認の拒否 | approval required、requires approval、workspace trust、the user rejected tool |
| `rate_limit` | 利用上限・残高 | rate limit、too many requests、quota、insufficient credits、`status 429`、DSH の `RATE_LIMIT`・`QUOTA`・`ACCOUNT_QUOTA` |
| `sandbox` | DSH の隔離（bubblewrap）の失敗 | `dsh-sandbox:`、`bwrap:` |
| `timeout` | 提供元・通信の期限切れ | timed out、deadline exceeded、`ETIMEDOUT`、`TimeoutError`、gateway timeout、`status 408`・`504`、DSH の `TIMEOUT` |
| `connection` | 提供元への接続と提供元の一時的な障害 | connection reset・refused、`ECONNRESET`、`ENOTFOUND`、socket hang up、fetch failed、TLS・SSL の失敗、bad gateway、service unavailable、overloaded、internal server error、`status 500`・`502`・`503`・`529`、DSH の `TRANSPORT`・`SERVER` |
| `runtime_error` | ランタイム（CLI）自身の例外・異常終了 | `Traceback (most recent call last)`、panic、uncaught exception、unhandled rejection、segmentation fault、core dumped |
| `response_extraction` | 応答を取り出せなかった | DSH の `EMPTY_RESPONSE`。または上のどれにも当たらず、stdout・stderr を丸ごと観測でき（`unavailable` に `stdout`・`stderr` が無い。`partial` も観測としない）、停止を確認でき、終了コードが 0 で、stdout でランタイムが試行を終わらせた失敗を報告しておらず、state が `response_failed`・`missing_result`・`invalid_result`、`reported_state` が `success` でなく、`sensitive_paths` が無い |
| `unknown` | どれにも当てはまらない、またはログを読めなかった | ― |

- HTTP の状態コードは、`HTTP`・`status`・`error code` などの語に続くときだけ数える（Traceback の `line 401` などを数えない）
- DSH のエラーコード（stderr の `dsh: <CODE>:` と、`turn_end` の `reason.error.code`）は、大文字のときだけ数える
- 残すのは分類名だけで、照合した文字列・行・位置は残さない
- 分類は記録だけに使い、再実行・採否・fallback を変えない

### 4. ログを読む条件（`attempts[].unavailable`）

次のときはログを読まず、`unavailable` に理由を書く。キーは `stdout`・`stderr`・`exit_code`・`reported_state`。

| 理由 | 条件 |
| --- | --- |
| `not_recorded` | runner がパスを記録していない |
| `not_stopped` | 試行の停止を確認できていない（生きた書き手が差し替えうるので読まない。`keep_rejected_request` と同じ） |
| `sensitive` | パスが試行の `sensitive_paths`（その下を含む）にある |
| `outside_output` | パスがこのレビューの runner の出力ディレクトリ（`cycle-<n>-review`）の外にある（別の run・別の場所を読まない） |
| `missing` | ファイルが無い |
| `not_regular_file` | symlink・特殊ファイル（`O_NOFOLLOW`・`O_NONBLOCK` で開き、通常のファイルだけを読む） |
| `unreadable` | 開けない・読めない |
| `partial` | 64 MiB を超えたので、末尾だけを読んだ（読んだ部分は照合に使うが、`response_extraction` の推測には観測としない） |
| `not_observed` | `exit_code`・`reported_state` が null |

stdout・stderr の一方でも丸ごと観測できないとき（`partial` を含む）は、終了状態だけから `response_extraction` と推測しない（PR #237 のレビュー修正。受け入れ条件 2）。観測できたログの照合に当たれば、その分類になる。

### 5. 保存できなかったとき

- 診断の組み立て・書き込みが `OSError`・`ValueError` で失敗したら、`ReviewerEntry.diagnostic_error` に理由（「診断を保存できない（`<errno の名前か例外の型>`）」。パスやログの文字列は入れない）を書く
- その出力ディレクトリは回収しない。停止を確認できていれば worktree の登録は今までどおり外し、ログを含む出力ディレクトリを消さずに残す。`resources` の状態は `retained`、理由は「失敗した担当の診断を保存できなかったので、ログを含む出力を消さずに残す」。`review` の出力の `retained` に完全パスが入る
- `review` は止めずに続ける（受け付けたレビュアーがいれば計画に進む。全員が失敗なら今までどおり終了コード 6）

### 6. 司令塔への出力と文書

- `review` の出力の `accepted`・`rejected` の各レビュアーに `diagnostic_file`（保存した診断の完全パス。無ければ null）と `diagnostic_error` を足す。全レビュアーの失敗（終了コード 6）のエラーの出力にも、同じ形の `rejected` を足す（`LoopError` の `details`）。`status`・`finish` の出力は変えない
- `references/records.md`: 1 章の置き場所に `diagnostics/`、3 章の `resources` の `retained` の理由、4 章の `reviewers[]` に 3 項目、診断の形・分類・読む条件の節を足す
- `SKILL.md`: サイクルの 2（`review`）に、失敗したレビュアーの原因は `diagnostic_file` の診断で調べること、`diagnostic_error` があれば理由と残したパス（`retained`）を利用者に伝えることを足す。最終報告に、失敗したレビュアーの診断のパスと原因の分類、保存できなかった理由を足す
- `tools/agent_runner/interfaces.rst`: 設計 1

### 7. テスト

- runner（`tools/agent_runner/tests/test_runner.py`）: 担当が success の receipt を書いて終了コード 1 で終わると、`state` は `response_failed`、`reported_state` は `success`。adapter が返した `reported_state` は `Attempt` に残り、State でない値は null になる。停止を確認できない試行・起動の前の失敗は null
- DSH（`tools/agent_runner/tests/adapters/dsh/test_adapter.py`）: 401（`AUTH`）の `turn_end` と、assistant の応答が無い session では、receipt の `status` は今までどおり `response_failed`、`reported_state` は `awaiting_authentication`。識別を読めるときは `reported_state` は null
- loop（新しい `tests/test_loop_diagnostics.py`。偽の gh・一時 Git・偽の CLI。実モデル・実 API・資格情報は使わない）
  - 異なる既知の失敗（接続の切断、ランタイムの例外）を stderr に書いて終了コード 1 で終わる偽の CLI 2 人: `review` が終了コード 6 で終わった後も、出力ディレクトリとログは消え、診断が残り、分類は `connection`・`runtime_error` で互いに区別できる。保存したファイルに、偽の CLI が書いた文字列は含まれない
  - 秘密の値の対照: 認証の失敗と偽のトークン（実行時に組み立てる）を stderr に書く偽の CLI と、成功するレビュアー: 分類は `authentication`、`reported_state` は adapter が返した値。run のディレクトリのどのファイルにも、`review` の出力にも、偽のトークンが含まれない
  - 保存できないとき: `cycle-1/diagnostics` を通常のファイルにしておく: `diagnostic_error` が入り、`review` は計画に進み、出力ディレクトリとログは残り（`retained`）、worktree の登録は外れ、`finish --abort` が残したパスを返す
  - 読む条件と分類の単体の確認: 停止未確認・`sensitive_paths`・出力の外・symlink・無いファイル・記録の無いパスはログを読まず、理由が入る。上限を超えるログは `partial`。ログを丸ごと読めた終了コード 0 の `response_failed` は `response_extraction`、`reported_state` が `success` なら `unknown`。Traceback の `line 401` は `runtime_error`、成功したツールの出力の「401 Unauthorized」は分類に使わない、失敗のイベントの invalid api key は `authentication`、認証と接続の両方が出たら `authentication`。失敗のイベントの各条件、Devin の本文の行・字下げした引用は数えない、DSH のエラーコード
  - pi の形（終了コード 0）: 最後の失敗メッセージの `errorMessage` で分類し（503 overloaded は `connection`、429 は `rate_limit`）、プロンプトと再試行の前の失敗は使わない。履歴の行が 1 MiB を超えても分類は変わらない。分類できない報告された失敗は `unknown` で、`response_extraction` にしない
  - 全レビュアーの失敗（終了コード 6）: CLI のエラーの出力の `rejected` に、診断のパスか保存できなかった理由が入る
- テストは AGENTS.md の「テストの採用基準」に従い、コードを実行して確かめる挙動だけを書く。文書の文言のテストは書かない

### 8. 変えないもの

- 試行の停止の確認、`sensitive_paths` の扱い、別の run の領域を読まない・消さない条件、`cleanup_output` の名前・種類の検査
- 同じサイクルでの再実行の条件（runner の段階の失敗は再実行しない）、レビュアーの採否の基準、全員失敗の終了コード 6、`hold`・`recover`・`finish` の手順
- 生の stdout・stderr・session を run の記録に写さない
- DSH の adapter が状態を上書きすること自体（上書き前の状態を記録するだけ）

## 受け入れ条件

1. 司令塔が `review` の結果を受け取った後でも、失敗した担当・段階・原因の分類・観測した終了状態（state・上書き前の state・終了コード・停止確認・所要時間）を、run の記録の診断で調べられる。診断は試行領域の回収の前に保存される（Issue の受け入れ条件 1）
2. 原因を観測できなければ `unknown` と、取得できなかった情報とその理由が入る。DSH の原因を推測で補わない（Issue の受け入れ条件 2）
3. 生の stdout・stderr・session を写さず、診断には分類名・列挙値・数値・識別子だけが入る。保存できなければ理由が記録され、`review` の出力で司令塔に伝わり、ログは消されずに残る（Issue の受け入れ条件 3）
4. 停止未確認・`sensitive_paths`・別の run の領域を読まず、消さない。再実行の回数とレビュアーの採否の基準は変わらない（Issue の受け入れ条件 4。既存のテストが通る）
5. 異なる既知の失敗を起こす偽の CLI で、回収の後も安全な原因の分類が残ることを実行して確かめる。秘密の値を混ぜる対照と、保存できないときの扱いも確かめる（Issue の受け入れ条件 5）
6. `reported_state` が runner の `Attempt` に残り、DSH の 401 の上書きで `awaiting_authentication` が残る（利用者の決定の「adapter が上書きする前に返した state」）
7. README の「テスト」の入口（ワールドの行を除く）で、この変更による失敗が無い

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-212-1 回収の前に、失敗した担当ごとの構造化した診断を run の記録に保存する（利用者の決定）**
  - 選択: `cleanup_output` の前に、失敗した担当ごとの構造化した診断を run の記録に保存する。項目は、担当・役割・段階・state・adapter が上書きする前に返した state・終了コード・停止確認・所要時間・原因の分類・取得できなかった情報。原因の分類は、stderr・stdout を既知のパターン（認証・接続・応答の取り出し・期限切れなど）と照合した分類名だけを残し、照合した文字列は保存しない。どれにも当てはまらなければ unknown。生の stdout・stderr・session は写さない。診断を保存できなかったときは、その理由を記録して司令塔に返す
  - 別案: Issue の対応案の範囲の、ほかの安全な形式（ログを伏せ字にして写す、など）
  - 理由: 利用者の決定
  - 委任指示: 利用者の決定。`/workspaces/reso-world/tmp/agents/commander-219-220-221-206-212.0smdd1hj/decisions/issue-212.md` の全文を次に引用する

    ```text
    ### #212
    - `cleanup_output` の前に、失敗した担当ごとの構造化診断を run の記録に保存する。項目は、担当・役割・段階・state・adapter が上書きする前に返した state・終了コード・停止確認・所要時間・原因の分類・取得できなかった情報
    - 原因の分類は、stderr・stdout を既知のパターン（認証・接続・応答の取り出し・期限切れなど）と照合した分類名だけを残し、照合した文字列は保存しない。どれにも当てはまらなければ unknown にする
    - 生の stdout・stderr・session は写さない。診断を保存できなかったときは、その理由を記録して controller に返す
    ```

- **D-212-2 診断は `cycle-<n>/diagnostics/<request_id>.json` に置き、`ReviewerEntry` からパスと SHA-256 で参照する**
  - 選択: 設計 2 の置き場所と形。pydantic のモデル（`schema`・`kind` 付き）で書き、`write_json` で途中の状態を残さずに置き換える
  - 別案: (a) `cycle-<n>.json` の `reviewers[]` に診断を埋め込む、(b) サイクル（と再実行）ごとに 1 ファイルにまとめる
  - 理由: (a) のレビュアーの記録は `review` が `_review_batch` から戻った後に保存されるので、回収の前に保存できない（回収の後にサイクルの保存が失敗すると診断も失われる）。決定の「回収の前に保存する」を満たすには、回収の前に書く別のファイルが要る。記録はほかの成果をパスと SHA-256 で参照する形（`SKILL.md` の「記録」）で、`requests/<request_id>.json` と同じ並びになる。(b) は、レビュアーと診断の対応を request ID で引く手間が増え、1 人分の書き込みの失敗が全員分に及ぶ
- **D-212-3 診断を作るのは、却下したレビュアーと、失敗した試行のあるレビュアー**
  - 選択: `verdict == "rejected"` か、試行に `success` 以外の状態がある `Result`。試行（fallback を含む）ごとに項目を入れる
  - 別案: (a) 却下したレビュアーだけ、(b) runner の段階で却下したレビュアーだけ
  - 理由: 決定は「失敗した担当ごと」で、fallback で失敗した担当は、後の担当が受け付けられても失敗した担当である。(b) は、runner は成功したが pr-review が失敗した（`payload`・`artifacts` の段階）レビュアーの、ランタイム側の手がかりを落とす。今の雛形と個人設定のレビュアーには fallback が無いので、(a) との差は fallback を設定したときだけで、費用は小さい
- **D-212-4 「段階」は loop の却下の段階（`rejected_stage`）にする**
  - 選択: `stage` に `runner`・`payload`・`binding`・`head`・`artifacts`（受け付けたレビュアーは null）。runner の中の段階（worktree の準備・起動・実行・収集）は、試行の `state`・`exit_code`・`unavailable` から読む
  - 別案: runner の中の段階を記録する（runner に項目を足すか、ログのファイル名から推測する）
  - 理由: `rejected_stage` は `SKILL.md`・`records.md` で使っている loop の語で、司令塔の状況コメントも同じ語を使う。runner の中の段階は、今の `Attempt` に無く、足すには runner の全経路を変える必要がある。ログのファイル名（`worktree.stdout.log`）からの推測は runner の内部の命名に依存する。起動の前の失敗は `exit_code` の null（`not_observed`）と state（`launch_failed` など）で区別できる
- **D-212-5 「adapter が上書きする前に返した state」は runner の `Attempt.reported_state` に記録する**
  - 選択: 設計 1。`AdapterOutcome.reported_state` を足して DSH の上書き前の状態を受け取り、runner が `_collect` の段で `Attempt.reported_state` に入れる。runner 自身の上書き（終了コードなど）の前の値も同じ項目に入る
  - 別案: (a) loop が stdout を DSH の adapter の内部の関数（`_classify`）で読み直す、(b) DSH が識別を読めないときに状態を上書きしないようにする、(c) runner の上書きの前の値（`_collect` の値）だけを記録する
  - 理由: (a) は adapter の非公開の実装に loop が依存し、adapter ごとに読み方が要る。(b) は状態の表示を変え（`awaiting_authentication` になる）、決定（上書き前の状態を残す）より範囲が広い。(c) は Issue のコメントの事例（DSH が adapter の中で上書きする）を残せない。runner は adapter の値と自身の上書きの両方を知る唯一の場所で、`Attempt` に足せば loop 以外（`run_roles.py`・`implement_task.py`）の記録にも残る。項目は既定 null で、読む側は名前で項目を読むので動きは変わらない
- **D-212-6 分類の照合の対象は、stderr と、stdout の失敗のイベント・診断の行（末尾 1 MiB。PR #237 のレビュー修正で 64 MiB に広げた）にする**
  - 選択: 設計 3 の照合の対象
  - 別案: (a) stdout と stderr の全体、(b) stderr だけ、(c) 各 adapter が自分の失敗の経路で分類して `AdapterOutcome` で返す
  - 理由: (a) は、モデルの本文とツールの出力（レビュー対象のコードや PR の本文。この Issue 自身も「401」「connection reset」を含む）で誤って分類する。各 adapter も同じ理由で、失敗の経路と stderr だけを分類に使っている。(b) は、DSH の `turn_end` の理由（`{"kind":"error","error":{"code":"AUTH"}}`）や、cursor・claude-code の失敗した `result` のように、stdout にだけ出る原因を落とす。(c) は 6 つの adapter を変え、adapter が成功と分類した後の runner の上書き（終了コード 1 など）や、`collect` を呼ばない経路を覆えない。loop の側で同じ規則を全試行に使えば、PR #210 の事例（終了コード 1 の `response_failed`）も分類できる。末尾に限るのは、失敗がストリームを終わらせるので原因が末尾に出ることと、大きさの上限が無いログを無制限に読まないため
- **D-212-7 分類は固定の語彙と優先順位で、試行ごとに 1 つ**
  - 選択: 設計 3 の表の 9 個。上から順に最初に当たったものを採る
  - 別案: (a) 当たった分類を全部並べる、(b) 決定の例（認証・接続・応答の取り出し・期限切れ）の 4 個と unknown だけ
  - 理由: 調べる人が最初に取る手（資格情報を直す、上限を待つ、提供元の障害を待つ、ランタイムを調べる）が分類ごとに違うので、行動につながる具体的なものを先に採る。ランタイムの例外の Traceback は接続の失敗などの結果でも出るので、`runtime_error` を後に置く。(a) は読み方（どれが原因か）を読む人に残す。(b) は、Issue の再現に使った「ランタイムの例外」や、有料の API で起きやすい利用上限、DSH の隔離の失敗を `unknown` に落とす。決定は「など」と例を挙げているので、例を含む固定の語彙にした
- **D-212-8 「応答の取り出し」は終了状態から決める**
  - 選択: ログの照合がどれにも当たらず、停止を確認でき、終了コードが 0 で、state が `response_failed`・`missing_result`・`invalid_result`、`reported_state` が `success` でなく、`sensitive_paths` が無いときに `response_extraction`
  - 別案: ログの照合だけで決め、`response_extraction` を作らない
  - 理由: 決定は「応答の取り出し」を既知の分類に挙げているが、応答を取り出せなかったことはログの文には出ない（adapter が出力を解析して判断する）。PR #215 の事例（終了コード 0 の `response_failed`）は、この形である。`reported_state` が `success` の上書き（伏せ字にできない export など）や、停止未確認は、取り出しの失敗ではないので除く
- **D-212-9 ログを読まない条件と、取得できなかった情報の語彙**
  - 選択: 設計 4 の表。理由は固定の語彙で書き、パスや例外の文は書かない
  - 別案: 理由を自由な文で書く
  - 理由: Issue の受け入れ条件 4 の「停止未確認・sensitive_paths・別 run の領域を勝手に読まない」を、読む前の検査として明示する。固定の語彙なら、ログの文字列や秘密が混ざらず、司令塔がそのまま報告できる。1 MiB を超えたログの頭を読んでいないことも、取得できなかった情報として `partial` に入れる
- **D-212-10 保存できなかったときは、理由を記録し、ログを含む出力を消さずに残す**
  - 選択: 設計 5。理由を `diagnostic_error` と `review` の出力に入れ、その出力ディレクトリを `retained` にする（worktree の登録は外す）
  - 別案: (a) 理由を記録するだけで、今までどおり回収する、(b) 出力を丸ごと残す（worktree の登録も残す）、(c) `review` を止める
  - 理由: (a) は、診断も無くログも消えるので、この Issue の不具合がそのまま残る。決定は「理由を記録して返す」で、残すことを禁じていない。残すのは消さないだけで、ログを run の記録に写さない（決定の「写さない」を守る）。`retained` は既存の資源の状態で、司令塔は最終報告に完全パスを書く（`SKILL.md`）。(b) の worktree はレビュー対象のコードの写しで原因の手がかりではなく、登録が残ると後の checkout の監査に影響しうる。(c) は、受け付けたレビュアーの成果があるのに計画に進めない。理由に例外の型と errno の名前だけを入れるのは、パスや文の混入を避けるため
- **D-212-11 司令塔には `review` の出力の各レビュアーの `diagnostic_file`・`diagnostic_error` で伝える**
  - 選択: 設計 6
  - 別案: (a) 出力に分類（`cause`）も入れる、(b) 出力は変えず、記録だけに残す
  - 理由: 決定の「保存できなかったときは controller に返す」は出力に要る。保存できたときはパスがあれば診断を読める。(a) は試行ごとの分類を出力に写す形を別に決める必要があり、記録と出力の二重管理になる。(b) は決定に反する
- **D-212-13 最後のブランチ全体のレビューを受けた変更**
  - 選択: (1) 照合の対象に、pi の失敗で終わった assistant のメッセージの `errorMessage` を足し、DSH のエラーコード（大文字）を分類の語に足す。(2) stdout でランタイムが失敗を報告していたら `response_extraction` にしない。(3) JSON でない行は、行頭のコロン付き・角括弧付きの診断だけを数える。(4) 全レビュアーの失敗（終了コード 6）のエラーの出力に、`rejected`（`diagnostic_file`・`diagnostic_error`）を足す
  - 別案: (1)(2) は変えない（レビュアーのローカルの実データで、pi の 401 と dsh-ccd の `TRANSPORT` が `unknown`、pi の形の 503・429 が `response_extraction` になる）。(3) は今のまま。(4) は SKILL.md に「`cycle-<n>.json` を読む」と書くだけにする
  - 理由: 個人設定のレビュアー 4 人のうち 2 人が pi で、提供元の失敗を「応答の取り出し」と記録すると、司令塔と利用者が adapter の解析を疑い、障害を待つ・資格情報を直すという対応を取れない。原因が失敗の経路に出ているのに `unknown` になるのは受け入れ条件 2 とも違う。pi の adapter も、最後の `agent_end` の最後の assistant のメッセージの `errorMessage` を分類に使う（PR #237 のレビュー修正で、再試行の前の失敗を使わないように同じ範囲に絞った）。プロンプト（PR の本文）を含む `messages` の行全体は使わない。(3) は Devin の stdout がレビュー本文で、本文の行で原因を誤って分類しうるので、D-212-6 の意図に合わせて絞った（devin の adapter と同じくコロン付き）。(4) は、全員の失敗が原因を最も調べたい経路で、D-212-1 の「理由を記録して返す」を出力で満たすため。成功の出力と同じ形で返し、`status`・`finish` の出力は変えない
  - 委任指示: issue-to-pr の「通常の設計判断は推奨案で決める」。D-212-1 の範囲の中の設計の抜けの修正
- **D-212-12 対象外とするもの**
  - 選択: 次は変えない。`finish`・`recover` の回収（`audit_resources` と `force`）の前の診断、`run_roles.py`（review-fix-planning の担当）と `implement_task.py`（issue-to-pr の Task の担当）の失敗の診断、DSH の上書きそのもの
  - 別案: 回収のすべての経路で診断を作る
  - 理由: `finish`・`recover` で回収されるのは、`review` が途中で止まった出力か、停止を確認できずに残っていた出力で、どちらも `review` を再開すれば診断の段を通るか、利用者が回収を指示するまで残っている（調べる機会がある）。全経路に足すと、却下の判定の前の出力の扱いを別に決める必要がある。ほかの workflow はこの Issue の回収経路ではない。持ち越し候補として PR 本文に書く
