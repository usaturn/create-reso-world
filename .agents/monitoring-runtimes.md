# 長時間タスク監視のランタイム対応表

`monitoring-long-tasks` が定める監視手順を、この Dev Container の各ランタイムでどのツールに割り当てるかだけを示す。

- OR 待機の型、レポートが無いまま対象が消えた場合の異常終了扱い、`verify.sh` の PID 導出とログ末尾 `EXIT=<code>` の確認は、スキル step 1〜3 に従う。ここでは重複させない
- controller がターンを完了通知に委ねてよいかは扱わない

## 対応表

| ランタイム | 完了 | 生存 | 進捗 / stall | OR 待機の組み方 |
| --- | --- | --- | --- | --- |
| Claude Code | Bash `run_in_background: true` の完了通知（終了コードを含む）。サブエージェントは `Agent` の完了通知 | 既知の PID を `kill -0` | 完了通知やツール結果が返す出力ファイル path を `Read`。`verify.sh` は印字されたログ path を使い、固定パスを仮定しない | 下の参考実装を `run_in_background: true` に渡す。進捗を都度イベントとして受け取るときだけ `Monitor` を使う |
| Devin | バックグラウンド `exec`（`timeout: 0`、または既定の自動バックグラウンド化）で起動した対象を `get_output` で待つ。`get_output` は対象プロセスの終了で即復帰し、終了コードは出力末尾の `Exit code: <n>` で確認する。1 回の待機上限は約 280 秒のため、タイムアウトしたら呼び直す。非同期の完了通知が届くのは `run_subagent` のサブエージェント（`<subagent_completion_notification>`）だけであり、シェルプロセスの終了は push されない | 既知の PID を `kill -0`（`exec` 経由）。`verify.sh` の PID 同一性確認はスキル step 3 のまま適用する | `verify.sh` が印字したログ path を `read` で読む。mtime / サイズが必要なら `exec` で `stat` を使う | 下の参考実装をそのままバックグラウンド `exec`（`timeout: 0`）で動かし、その監視シェルを `get_output` で待つ。ループの脱出がそのまま `report exists OR worker is not alive` の解消になる |
| Cursor | TBD | TBD | TBD | TBD |

```bash
# $pid の導出と、待機終了後の EXIT=<code> 確認はスキル step 3 に従う
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
| pi | 単発サブエージェントは `async: false` の同期起動のみ（`.pi/APPEND_SYSTEM.md`）。バックグラウンド起動と停止ができない | 起動条件を満たせず常時省略 |
| Cursor | TBD | TBD |

## 注記

- スキル step 1 が禁じる foreground sleep ループとは、エージェント本体のターンを `sleep` で占有することを指す。上の `sleep 30` のように監視スクリプト内に閉じた `sleep` は該当しない。待機はバックグラウンドへ置き、ターンは通知で戻す
- `BashOutput` と `TaskOutput` は使わない
- Devin にはシェルプロセス終了を届ける非同期通知が無く、`Monitor` 相当のツールも無い。controller は `get_output` のブロッキング呼び出しを繰り返してターンを保持し、stall ポーリングはその合間にログを読んで行う
- TBD のセルは埋めない。ツール名をリポジトリまたは公式文書で確認できたときだけ書く。Cursor / Codex / Grok / pi は CLI が導入済みでも、監視ツール名が確認できるまで行を追加しない
