# pr-review-fix-loop の記録（`pr-review-fix-loop/v1`）

helper（`scripts/loop.py`）が書く記録の形式・置き場所・終了コードを定める。記録を書くのは helper だけで、司令塔とレビュアーは書かない。

この文書では、レビュー修正ループの 1 回分を「サイクル」、レビューを行う 1 モデル分を「レビュアー」と書く。

## 1. 置き場所

レビューディレクトリ（親の main checkout の `reviews/<owner>/<repo>/#<PR>-<ブランチ>/`。保存先の規則は `.agents/scripts/review_target.py`）の下に置く。どれも commit しない。

```text
reviews/<owner>/<repo>/#<PR>-<ブランチ>/
└── loop/
    ├── lock.json                   # PR ごとのロック（使用中の run だけ）
    └── <run_id>/
        ├── run.json                # run の設定・割り当て・状態・結果・資源
        ├── cycle-<n>.json          # サイクルごとの記録
        └── cycle-<n>/
            ├── comments.json       # レビュアーに渡した PR の全コメント（gh api --paginate --slurp の出力）
            ├── after-run-<i>.stdout.log・after-run-<i>.stderr.log  # 後処理（after_run）のログの写し（再実行は rerun- を付ける）
            ├── review-result.json  # runner の結果（BatchResult）の写し
            ├── rerun-result.json   # 再実行したときだけ。再実行の runner の結果の写し
            ├── requests/
            │   └── <request_id>.json  # 却下したレビュアーの試行に渡した指示（runner の request.json）の写し
            └── diagnostics/
                └── <request_id>.json  # 失敗した担当がいるレビュアーの、試行ごとの診断（4.1 節。分類名だけを残し、ログは写さない）
```

- レビューディレクトリの直下には `<model>.md` 以外のファイルを置かない（`.agents/review-findings.md` 2 章）。`loop/` はサブディレクトリである。
- runner の worktree と出力は、`${TMPDIR:-/tmp}/create-reso-world-pr-loop-XXXXXX/cycle-<n>-review/` に一意に作る。停止を確認した後に helper が回収する（`run.json` の `resources`）。回収するのは、この接頭辞の名前のディレクトリだけである。

## 2. ロック（`lock.json`）

| キー | 値 |
| --- | --- |
| `schema`・`kind` | `"pr-review-fix-loop/v1"`・`"lock"` |
| `run_id` | 32 桁の hex |
| `pr` | `{"repository", "number", "url"}` |
| `run_dir` | run のディレクトリの完全パス |
| `created_at` | UTC の `YYYY-MM-DDTHH:MM:SSZ` |

- `start` が新規作成だけで取る（既にあれば終了コード 3）。古く見えても上書きしない。
- 消すのは `finish` と `recover` だけで、`run_id` が一致する場合に限る。

## 3. run（`run.json`）

| キー | 値 |
| --- | --- |
| `run_id`・`pr`・`review_dir` | 対象 |
| `tool_root`・`tool_commit` | helper とスキルを読んだ checkout と、その commit（レビュアーの worktree はこの commit から作る） |
| `controller` | `{"model", "runtime"}`（司令塔） |
| `options` | `max_cycles`、`assign`（`--assign` の値）、`template`、`config`、`fresh_review` |
| `assignments` | 読み込んだ設定の有効な割り当て。`review.inspect` と `fix.implement`・`fix.self-review`・`fix.fix-check`（`agents`・`fallback`） |
| `started_at`・`ended_at` | 時刻 |
| `state` | `running`・`ended`・`held`（停止を確認できない試行・後処理があり、ロックを保持）・`abandoned`（結果の無いまま回収した） |
| `result` | `{"outcome", "ended_by", "stop_reason", "merged", "cycles"}`。`outcome` は `fixes_pushed`・`no_fix_needed`・`stopped`、`ended_by` は `outcome`・`cycle_limit`・`abort`。`merged` は `true`・`false`・`null`（`null` は `finish --abort` だけが書く未確認。6 章） |
| `resources` | `[{"path", "kind": "runner_output", "cycle", "state", "reason"}]`。`state` は `created`（未回収）・`removed`・`retained`（消さずに残した）。`retained` の `reason` は、外せない worktree・秘密が残りうるファイル・runner の結果が無い、または失敗した担当の診断を保存できなかった（4.1 節）など |
| `notes` | `recover` で受け取った確認の事実、`finish --abort` が `merged` を PR の状態だけで決められなかった理由など |
| `herdr_pane` | `{"state", "pane_id", "label", "reason"}`。`start` が現在の Herdr ペインの名前を変えた結果 |

移植元の `options.hold_action` は無い。移植先の review-fix-planning には判断保留が無いので、`start` は `--hold-action` を受け付けない。

`herdr_pane` の `state` は次のどれかで、`start` の出力の `herdr_pane` にも同じ値を返す。`label` は `PR#<番号>`（番号は GitHub が返した PR の番号。リポジトリ名は付けない）。

| `state` | 意味 | `pane_id` | `reason` |
| --- | --- | --- | --- |
| `renamed` | `herdr pane rename <HERDR_PANE_ID> PR#<番号>` が終了コード 0 で終わった | `HERDR_PANE_ID` | `null` |
| `skipped` | `HERDR_ENV` が `1` ではない、または `HERDR_PANE_ID` が空なので、`herdr` を呼ばなかった | `null` | 呼ばなかった理由 |
| `failed` | `herdr` が無い、0 以外で終わった、または期限（10 秒）までに終わらなかった | `HERDR_PANE_ID` | 失敗の理由（`start` の `warnings` にも入る） |

名前を変えるのは、`start` がロックを取って `run.json` を保存した後だけである。`start` が失敗する場合は `herdr` を呼ばない。`failed` でも `start` は成功し、run はロックを持ったまま続く。

## 4. サイクル（`cycle-<n>.json`）

| キー | 値 |
| --- | --- |
| `cycle`・`head` | サイクルの番号（run の中で 1 から）と、対象の PR HEAD |
| `state` | `reviewing`・`planning`・`ended` |
| `prior_round` | `cycle-begin` の時点で PR にあった判断の記録の最大の `round`。`cycle-end` はこれより後の記録だけをこのサイクルの記録として受け付ける（前の run の同じ HEAD の記録を拾わない） |
| `review.mode` | `run`（レビュアーを起動した）・`reuse`（現在の HEAD の成果を使った） |
| `review.reviewers[]` | `requested_agent`・`actual_agent`、runner の state、`verdict`（`accepted`・`rejected`）と `reason`、runner が観測した `identity`、payload の `reviewer`・`timing`、成果 2 件のパスと SHA-256、`active_findings`、pr-review の `cleanup`・`warnings`・`retained_paths`。却下したときは `rejected_stage`（`runner`: 停止未確認・runner の失敗、`payload`: payload の形・pr-review の失敗、`binding`: request・担当・PR の不一致、`head`: レビューした HEAD の不一致、`artifacts`: 成果 2 件の欠落・不整合）と、その試行の `request.json` の写しの `request_file`・`request_sha256`（写せないときは null）。失敗した担当がいるレビュアーは、診断の `diagnostic_file`・`diagnostic_sha256`（保存できなかったときは null）と、保存できなかった理由の `diagnostic_error`（4.1 節） |
| `review.rerun` | 再実行したときだけ。`agents`（起動し直した実担当）、`replaced`（置き換えた 1 回目の `reviewers[]` の記録）、再実行の `output_dir`・`started_at`・`ended_at`・`seconds`・`batch`・`after_run`・`cleanup`。`review.reviewers` は再実行の結果で置き換えた後の記録 |
| `review.reused[]` | 再利用した成果 2 件のパスと SHA-256、`model`・`runtime`・`reviewed_head`・`active_findings` |
| `review.batch` | runner の run ID・state・assignments・`result_file`（写し）・`outside_changes` |
| `review.output_dir`・`comments_file`・`started_at`・`ended_at`・`seconds`・`cleanup` | レビューの実行と回収 |
| `planning` | `round`・`comment_id`・`posted`、`outcome`・`commit`・`stop_reason`・`merged`、判断の件数（`state` 別・`change` 別）、`planning_file`・`verified_file` とその SHA-256、`finalize`（結果の内容・`result_file`・`round_dir`）、`role_runs[]`（`run_roles.py` の出力ごとの実際の担当と状態）、`ended_at` |

レビュー・確認・判断の中身は写さない。参考データ（`.agents/review-findings.md` の識別情報・時間）は、パスで参照する成果の側にある。

再実行の対象は、runner は成功（停止確認済み・終了コード 0）したのに loop が受け付けなかったレビュアー（`rejected_stage` が `runner` 以外）だけで、1 サイクルに 1 回まで。1 回目の runner の結果に、別の担当でも停止を確かめられない試行があれば再実行しない（資源を残す）。1 回目・再実行のどちらでも、runner の結果に停止を確かめられない試行があれば、受け付けたレビュアーがいても計画に進まず、run を `held` にして終了コード 7（`resources`）で `recover` の経路に返す。受け付けたレビュアーが 0 人なら終了コード 6 で、`finish` が run を `held` にする。最初の `review` はサイクルを `reviewing` のまま `review.rerun` を保存し、`next` に `review` を返す。2 回目の `review` は PR の HEAD を確かめてから、その実担当だけを fallback 無し・同じ role の期限で起動し、同じ検査を行う。却下した試行の `request.json` は runner の仕様で環境の値を含まない（`tools/agent_runner/interfaces.rst`）。停止を確かめられない試行の `request.json` は読まない。秘密が残りうる stdout・stderr は写さず、失敗した担当のログからは 4.1 節の診断（分類名と列挙値）だけを残す。

### 4.1 失敗した担当の診断（`cycle-<n>/diagnostics/<request_id>.json`）

`review` は、runner の出力を回収する前に、却下したレビュアーと、success 以外の試行（fallback で失敗した担当）があるレビュアーについて、試行ごとの診断を書く（#212）。runner のログ（stdout・stderr）は回収で消えるので、失敗の原因はこの診断と `rejected_stage`・`reason` で調べる。生の stdout・stderr は写さず、値は列挙値・数値・識別子だけである。再実行の診断も同じディレクトリに置く（request ID が違う）。

| キー | 値 |
| --- | --- |
| `schema`・`kind` | `"pr-review-fix-loop/v1"`・`"diagnostic"` |
| `request_id`・`role`・`requested_agent`・`actual_agent` | runner の `Result` の値 |
| `verdict`・`stage` | loop の判定（`accepted`・`rejected`）と、却下の段階（`rejected_stage`。受け付けたレビュアーは null） |
| `state` | runner の `Result.state` |
| `attempts[]` | 試行（fallback を含む起動順）ごとに `agent_id`・`state`・`reported_state`（adapter が出力から分類した、adapter と runner が置き換える前の状態。`tools/agent_runner/interfaces.rst`）・`exit_code`・`stop_confirmed`・`elapsed_seconds`・`cause`・`unavailable` |

`cause`（原因の分類）は、試行を終わらせた失敗の報告だけから決める。stderr の全体と、stdout のうち失敗のイベント（`type` に `error`・`fail` を含む、`is_error` が true、`subtype` が `error` で始まる、`error` が空でない）、stream の中で最後に現れた assistant のメッセージ（pi の `message_start`・`message_end`・`turn_end` の `message` と `agent_end` の `messages`）が失敗で終わっていれば（`stopReason` が `error`）その `errorMessage`、JSON でない行のうち行頭（字下げなし）のコロン付き・角括弧付きの診断の行（`Error:`・`fatal:`・`panic:`・`[ERROR]`・`<名前>Error:`・`Traceback (most recent call last)`・`bwrap:` など）を、既知のパターンと上から照合して、最初に当たった分類名である。stdout を照合に使うのは、stdout が JSON のイベントの stream の担当（設定のランタイムが `claude-code`・`codex`・`cursor`・`pi`）だけである。Devin（`devin -p`）はモデルの発言を平文で stdout に書き、コードブロックの中のログの例も行頭から始まるので、Devin と設定からランタイムが分からない担当の stdout は照合の文にしない（stderr は使う）。その stdout に失敗の報告に見える行（診断の行・失敗のイベントなど）があれば、報告の有無を判定できないので `response_extraction` と推測しない。担当が自動の再試行で回復した一時的な失敗は使わない: 再試行の通知（`type` か `subtype` に `retry` を含むイベント。Claude Code の `system/api_retry`、pi の `auto_retry_start`・`auto_retry_end`）は失敗にせず、再試行を使い切った・取り消した通知（`success` が false）だけを、その `finalError` で数える。pi の再試行の前の失敗（後に別の assistant のメッセージが続く失敗メッセージ）も使わない。照合した文字列は残さない。モデルの本文・ツールの出力・プロンプトは使わない（レビュー対象のコードや PR の本文が認証・接続などの語を含みうる）。HTTP の状態コードは `HTTP`・`status`・`error code` などに続くときだけ数える。各ログは末尾から 64 MiB までを読む（pi の `agent_end` は会話の履歴全体を 1 行に含み、1 MiB を超える）。

| `cause` | 意味 |
| --- | --- |
| `authentication` | 認証の失敗（資格情報が無い・無効・期限切れ） |
| `approval` | 承認待ち・承認の拒否 |
| `rate_limit` | 利用上限・残高 |
| `sandbox` | bubblewrap による隔離の失敗 |
| `timeout` | 提供元・通信の期限切れ（runner の期限切れは `state` の `timed_out`） |
| `connection` | 提供元への接続の失敗と、提供元の一時的な障害（5xx・過負荷） |
| `runtime_error` | ランタイム（CLI）自身の例外・異常終了 |
| `response_extraction` | ログの照合はどれにも当たらず、stdout・stderr を丸ごと観測でき（`unavailable` に `stdout`・`stderr` が無い。`partial` も観測としない）、停止を確認でき、終了コードが 0 で、試行を終わらせた失敗の報告が無い（失敗のイベント・使い切った再試行・pi の最後の失敗メッセージ・診断の行が無い）のに結果を得られなかった（`reported_state` が `success` でなく、`sensitive_paths` が無い） |
| `unknown` | 観測したログの照合がどれにも当たらず、`response_extraction` の条件も満たさない。stdout・stderr の一方でも丸ごと観測できなかった（`unavailable` に `stdout`・`stderr` がある）ときは、終了状態から推測しない |

`unavailable` は、取得できなかった情報（キーは `stdout`・`stderr`・`exit_code`・`reported_state`）と、その理由である。

| 理由 | 意味 |
| --- | --- |
| `not_recorded` | runner がログのパスを記録していない |
| `not_stopped` | 停止を確認できない試行なので読まない（生きた書き手が差し替えうる） |
| `sensitive` | runner の `sensitive_paths`（その下を含む）にあるので読まない |
| `outside_output` | このレビューの runner の出力ディレクトリの外なので読まない |
| `missing`・`not_regular_file`・`unreadable` | ファイルが無い・symlink か特殊ファイル・読めない |
| `partial` | 64 MiB を超えたので末尾だけを読んだ。読んだ部分は照合に使うが、切れた行に最後の失敗が隠れうるので `response_extraction` の推測には観測としない |
| `not_observed` | `exit_code`・`reported_state` が null |

`review` の出力の各レビュアー（`accepted`・`rejected`）にも、`diagnostic_file` と `diagnostic_error` を返す。全レビュアーの失敗（終了コード 6）のエラーの出力にも、同じ形の `rejected` が入る（5 章）。診断を書けなかったとき（ディレクトリを作れない・書けないなど）は、`diagnostic_error` に理由（errno の名前か例外の型の名前だけ）を書き、その出力ディレクトリは worktree の登録だけを外して、ログを含めて消さずに残す（`resources` の `retained`、出力の `retained`）。`review` は止めない。

## 5. 終了コードと `stage`

| コード | 意味 | 主な `stage` |
| --- | --- | --- |
| 0 | 成功 | ― |
| 1 | 想定外の内部エラー（stderr に traceback） | ― |
| 2 | 引数・入力の誤り | `arguments`、`config` |
| 3 | 排他・状態の順序の違反 | `lock_held`、`not_owner`、`state`、`interrupted_review` |
| 4 | 対象の食い違い | `pr_not_open`、`head_moved`、`record_missing`、`record_inconsistent`、`pushed_head_mismatch`、`merge_mismatch` |
| 5 | 外部（GitHub・git・runner）の失敗 | `github`、`git`、`parent`、`parent_preparation`、`runner`、`after_run` |
| 6 | 全レビュアーの結果を受け付けられなかった | `review` |
| 7 | 資源・後処理の停止を確認できない（run を `held` にしてロックを保持する。`next` は `recover`） | `resources`、`after_run` |

`check-options` は記録を書かない。成功の出力は `{"status": "ok", "options", "assignments", "next": null}` で、`options` は `run.json` の `options` から `fresh_review` を除いた形、`assignments` は `run.json` と同じ形である。失敗は終了コード 2（`arguments`・`config`）で、`run_dir` と `next` は null。

失敗の出力は `{"status": "error", "stage", "reason", "run_dir", "next", "requires_input"}`。全レビュアーの結果を受け付けられなかった（終了コード 6）ときだけ、`review` の成功の出力と同じ形の `rejected`（却下したレビュアーごとの `reason`・`rejected_stage`・`diagnostic_file`・`diagnostic_error` など。4.1 節）も入る。`requires_input` は、`next` に足すオプションと、そこに書く事実の説明（`recover` の `--operator-confirmed-stopped` など）。書きかけの値を実行させないよう、`next` にはそのオプションを含めない。失敗しても、それまでに保存した記録と runner の結果は書き換えない。引数の書式の誤り（argparse が拒否するもの）だけは、標準エラー出力の usage と終了コード 2 で、JSON を書かない。

## 6. 読む側の注意

- サイクルの番号は run の中の通し番号で、判断の記録の `round`（PR 全体の通し番号）とは別である。対応は `planning.round` にある。
- 判断の記録は、書き込み権限のある投稿者（`OWNER`・`MEMBER`・`COLLABORATOR`）と、認証済みの利用者自身（`gh api user` の login）のコメントからだけ読む。login を取れないときは、`cycle-begin`・`cycle-end` が終了コード 5（`github`）で止まる（`.agents/review-records.md` 8.1）。
- `review.reviewers[].identity` は runner の事後の観測、`reviewer` は pr-review が成果に記録した値で、同じとは限らない。未観測の値を設定から補わない。
- `cycle-end` が保存する `merged`（`planning.merged` と、そのときの `result.merged`）は、`cycle-end` が読んだ PR の実際のマージ状態である。結果が `no_fix_needed` になるのは、finalize の結果の `merged` が `true` で、PR がマージ済みで、PR の head が finalize の結果の `spec_commit`（create-reso-world の PR の結論 2 の、Spec だけの commit）と、無ければサイクルの HEAD と同じときだけで、食い違えば `merge_mismatch` で止まる。finalize が `stopped` のときは、finalize の `merged`（`false`・`null`。`null` は確かめられていない）で上書きせず、PR の実際の状態を保存する。別の head のマージも `stopped` のままで、停止理由は finalize のものである。finalize が `true` なのに PR が未マージなら `merge_mismatch`。判断の記録が `stopped`（finalize を呼ばない）のときも、PR の実際の状態を保存する。finalize の結果そのものは `planning.finalize.result` に残る。
- `finish --abort` が書く `result.merged` は、finalize.py の `merged`（`.agents/skills/review-fix-planning/references/execution.md` 3.4 節）と同じ意味で、最後に観測した PR のマージ状態である。`finish` が PR を読めればその状態を書く。読めなければ `--finalize-result` で渡された finalize の結果の `merged` を書き、渡されていなければ `null`（未確認）を書く。finalize の結果が `true` なのに PR が未マージなら、どちらかの読み取りが誤っているので、abort は止めずに `null` を書く。PR の状態だけで決められなかったときは、理由を `notes` に残す。`null` を未マージとして扱わない（確かめるときは PR を読み直す）。
- `recover` は、runner の試行が停止済みでも、その出力で始めた後処理（after_run）の停止を確かめられない資源（後処理の報告が無い、または `stop_confirmed` が true でない報告を含む）を、事実なしには回収しない。停止を確かめた事実を受け取った資源でも、秘密が残りうるファイル（runner の `sensitive_paths`。runner の結果が無いときはディレクトリ全体）を消さずに残し、`retained` に完全パスを書く。
