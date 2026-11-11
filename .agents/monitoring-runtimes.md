# 長時間タスク監視のランタイム対応表

`monitoring-long-tasks` が定める監視手順を、この Dev Container の各ランタイムでどのツールに割り当てるかだけを示す。

- OR 待機の型、レポートが無いまま対象が消えた場合の異常終了扱い、ログ名からの PID 導出と終了コードの確認は、スキルの手順 1〜3 に従う。ここでは重複させない
- controller がターンを完了通知に委ねてよいかは扱わない

## 対応表

| ランタイム | 完了 | 生存 | 進捗 / stall | OR 待機の組み方 |
| --- | --- | --- | --- | --- |
| Claude Code | Bash `run_in_background: true` の完了通知（終了コードを含む）。サブエージェントは `Agent` の完了通知 | 既知の PID を `kill -0` | 完了通知やツール結果が返す出力ファイル path を `Read`。ログ path を印字するコマンドはその path を使い、固定パスを仮定しない | 下の参考実装を `run_in_background: true` に渡す。進捗を都度イベントとして受け取るときだけ `Monitor` を使う |
| Devin | バックグラウンド `exec`（`timeout: 0`、または既定の自動バックグラウンド化）で起動した対象を `get_output` で待つ。`get_output` は対象プロセスの終了で即復帰し、終了コードは出力末尾の `Exit code: <n>` で確認する。1 回の待機上限は約 280 秒のため、タイムアウトしたら呼び直す。非同期の完了通知が届くのは `run_subagent` のサブエージェント（`<subagent_completion_notification>`）だけであり、シェルプロセスの終了は push されない | 既知の PID を `kill -0`（`exec` 経由）。PID の同一性確認はスキルの手順 3 のまま適用する | コマンドが印字したログ path を `read` で読む。mtime / サイズが必要なら `exec` で `stat` を使う | 下の参考実装をそのままバックグラウンド `exec`（`timeout: 0`）で動かし、その監視シェルを `get_output` で待つ。ループの脱出がそのまま `report exists OR worker is not alive` の解消になる |
| pi | 完了通知もバックグラウンド実行も無い（pi 1.3.0 の bash ツールの引数は `command`・`timeout` だけ）。対象を bash ツールの foreground で実行し、戻った後に終了コードと結果を確認する。PR 修正ループの `loop.py review` も、全レビュアーの終了と停止の確認まで戻らない同期のコマンドなので、bash ツールの `timeout` を付けずに foreground で実行し、標準出力の JSON と終了コードを確かめる（期限は runner が守る） | foreground の呼び出しが戻らない間は、対象が動いている。既知の PID は `kill -0`（bash ツール） | 実行中は確かめられない。戻った後にログを必要な範囲だけ読む。途中で止める条件が要る対象は、起動前に `task_watch.py` で宣言して包む（下の「task_watch による途中の判断と停止」） | foreground の実行が戻ることが、そのまま `report exists OR worker is not alive` の解消になる。ただし `task_watch.py` で包んだ対象は別の session で動くので、戻っただけでは解消しない（下の「task_watch による途中の判断と停止」）。`loop.py review` が中断で結果を残さずに終わったときは、`loop.py status` の `next` と `recover --operator-confirmed-stopped`（`pr-review-fix-loop` の「止まったとき」）で回収する |
| Cursor | TBD | TBD | TBD | TBD |

```bash
# $pid の導出と、待機終了後の終了コードの確認はスキルの手順 3 に従う
until [ -f "$REPORT" ] || ! kill -0 "$pid" 2>/dev/null; do
  sleep 30
done
```

## PR レビュー委譲の起動可否

`pr-review` の補助委譲は、バックグラウンド起動・期限付き待機・停止・停止確認をそのランタイムで利用できる場合だけ起動できる。委譲 worker の停止・停止確認の手段と起動可否の対応は次のとおり。TBD のセルは、停止系ツール名をリポジトリまたは公式文書で確認できたときだけ埋める。

| ランタイム | 委譲 worker の停止・停止確認 | 起動可否 |
| --- | --- | --- |
| Claude Code | TBD | TBD |
| Devin | サブエージェント（`run_subagent`）に停止手段が無い。`kill_shell` は `exec` シェルのみが対象 | 起動条件を満たせず常時省略 |
| pi | サブエージェントは pi-superagents の Superpowers role API による同期実行のみで、async は指定しない（`.pi/APPEND_SYSTEM.md`）。バックグラウンド起動と停止ができない | 起動条件を満たせず常時省略 |
| Cursor | TBD | TBD |

## task_watch による途中の判断と停止

`monitoring-long-tasks` の「事前宣言した打ち切り」の対象は、同スキルの `scripts/task_watch.py run` で起動する。判定と停止は watcher が行うので、controller が同期の呼び出しで待っている間も、宣言した期限・無進捗・予約枠・失敗の条件で止まる。controller は watcher の終了（完了通知・同期の戻り）を待ち、途中では `status` の短い JSON だけを読む。

| ランタイム | 起動と完了 | 途中の確認 | 方針を変えるとき（宣言どおりの停止） |
| --- | --- | --- | --- |
| Claude Code | `run` を Bash の `run_in_background: true` で起動する。watcher の終了が終了コード付きの完了通知になる | `status` を Bash で実行する | `stop` を Bash で実行する |
| Devin | `run` をバックグラウンド `exec`（`timeout: 0`）で起動し、`get_output` で待つ | `status` を `exec` で実行する | `stop` を `exec` で実行する |
| pi | `run` を bash ツールの foreground で実行する。bash ツールの `timeout` は付けない（既定の timeout は無い。期限は watcher が守る）。controller は戻るまで待つが、watcher が宣言どおりに判定・停止する。これが同期のみのランタイムでの代替策である | 途中では確認できない。戻った後に標準出力の JSON か `final.json` を読む。`final.json` が無ければ `status` を実行する（下の箇条） | 途中ではできない。起動前に宣言した条件（期限・無進捗・予約枠・失敗）が代わりに働くので、止める条件は起動前に決めておく |
| Cursor | TBD | TBD | TBD |

- `run` の終了コードは 0 = `completed`、1 = 完了していない、2 = 入力の誤り、3 = `hold`（停止を確認できない、終了後も同じ group にプロセスが残っている、または `--stop none` の watcher に `stop` を送った）。3 のときは `final.json` の `residual_pids` と `paths` を報告し、依存する作業を始めない
- `--stop none` の watcher は停止の条件を満たしても止めず、対象が自分で終わるまで動き続ける。pi の行の「宣言した条件が代わりに働く」は `INT`・`TERM` を宣言した場合に限る
- pi 1.3.0 の bash ツールは、`timeout` を超えたとき・利用者が中断したとき・pi が終わるとき（SIGHUP・SIGTERM・端末の切断・異常終了）に、シェルの process group へ SIGKILL を送る。`task_watch.py` は対象を別の session で起動するので、消えるのは watcher だけで、対象は宣言した期限を過ぎても止まらない。このときは `final.json` が無いので、スキルの「task_watch で宣言・判定・停止する」のとおり `status` で確かめる
- `task_watch.py` は CLI のプロセスを包むもので、Claude Code の `Agent` などのサブエージェントを止める手段にはならない。上の「PR レビュー委譲の起動可否」の表は変わらない
- agent_runner を包むときは `--stop INT` にし、`--escalate-kill` を付けない。下の節の「中断」と同じ経路で runner が子孫を止め、結果を保存する

## agent-runner の同期実行と停止確認

`uv run --project "$PARENT_ROOT" --locked python tools/agent_runner/with_keys.py -- python -m tools.agent_runner run ...`（リポジトリのルートを cwd にする。wrapper は後段と同じ checkout のものを使う。別の checkout の wrapper を使うときは、後段の雛形を `--template` で wrapper に渡す）は、全ての担当の終了と停止の確認まで戻らない同期のコマンドである。`with_keys.py` は、ランチャー起動セッションでも runner に key を届ける wrapper である（`.devcontainer/README.md` の「API トークン」節）。完了・生存・進捗を分ける原則は `monitoring-long-tasks` のまま適用する。Herdr の pane・idle の判定や、別のランタイムへの暗黙の切り替えは使わない。

| ランタイム | 起動と完了 |
| --- | --- |
| Claude Code | Bash の `run_in_background: true` で起動し、終了コード付きの完了通知で待つ（役割の期限は最大 90 分で、foreground の上限 10 分を超えうる） |
| Devin | バックグラウンド `exec`（`timeout: 0`）で起動し、`get_output` で待つ |
| pi | bash ツールの foreground で実行し、戻るまで待つ。bash ツールの `timeout` は付けない（timeout・中断で runner が SIGKILL され、結果を保存できず、別の session の担当が残る）。途中で止める条件が要るときは `task_watch.py run --stop INT` で包む |
| Cursor | TBD |

- 完了: コマンドの終了コード（成功・self は 0、失敗・部分成功は 1、設定・入力の誤りは 2、SIGINT は 130）と、summary が示す `result.json` を確かめる。result の state・識別情報・各 attempt の `stop_confirmed` も確かめ、ログの更新や receipt のファイルがあることだけで成功と扱わない
- 生存: 既知の runner の PID を `kill -0` で確かめ、コマンドと cwd が同じことも確かめる
- 進捗: 起動時に指定した一意の `--output-dir`（または完了の summary の実際の `artifact_dir`）の、担当ごとの `stdout.log`・`stderr.log` を必要な範囲だけ読む。時間のかかる仕事は、起動時に新しい `--output-dir` を指定し、既存の領域を使い回さない
- 中断: runner 自体に SIGINT を送り、終了まで待つ。runner は共有の cancel と、process group・観測済みの子孫への TERM → KILL で停止を試み、確かめた結果を保存する。runner をいきなり SIGKILL すると、この終了処理と結果の保存は保証されない
- 停止未確認: `stop_confirmed=false` と、保存された `work_dir`・ログの実際のパスを報告し、依存する仕事や fallback を始めない。使用中の領域は消さない。`sensitive_paths` に挙がった receipt などは秘密が残っているおそれがあるので、その内容を転載しない

役割の期限は実行枠を得た時点から数え、worktree の準備と明示した fallback を含む。停止の確認の猶予で期限を超えることがある。既存の checkout の外部の変更のうち、runner が保護する checkout（依頼された checkout。特定できなければ全登録）の変化・消失・監査不能は `outside_changes`、保護しない checkout（main worktree も、依頼された checkout でなければ保護しない）の内容の変化・回収・監査不能は `unprotected_changes` として報告される。受け取り入口は `outside_changes` があれば拒否するが、`unprotected_changes` は報告だけで起動も受け取りも止めない。`unprotected_changes` を確かめ、必要なら成果を確かめ直す。どちらも他のセッションの変更との因果は断定しない。

ログと worktree は成功のときも残る。停止を確かめて成果を保存した後に、対象の repository で `git worktree remove <work_dir>` を実行して登録を外し、その run が所有する領域だけを回収する。停止未確認・変更が残る worktree を勝手に消したり、他の run の領域を掃除したりしない。

## 注記

- スキルの手順 1 が禁じる foreground sleep ループとは、エージェント本体のターンを `sleep` で占有することを指す。上の `sleep 30` のように監視スクリプト内に閉じた `sleep` は該当しない。待機はバックグラウンドへ置き、ターンは通知で戻す
- `BashOutput` と `TaskOutput` は使わない
- Devin にはシェルプロセス終了を届ける非同期通知が無く、`Monitor` 相当のツールも無い。controller は `get_output` のブロッキング呼び出しを繰り返してターンを保持し、stall ポーリングはその合間にログを読んで行う
- TBD のセルは埋めない。ツール名をリポジトリまたは公式文書で確認できたときだけ書く。Cursor / Codex / Grok は CLI が導入済みでも、監視ツール名が確認できるまで行を追加しない。pi の行は、bash ツールの foreground 実行と `task_watch.py`、PR 修正ループの `loop.py review` の同期実行という、このリポジトリで確認済みの仕組みだけを書く
