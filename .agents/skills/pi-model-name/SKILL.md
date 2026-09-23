---
name: pi-model-name
description: Use when asking which AI model or provider is currently running in pi, displaying the current model name, or recording MODEL_NAME for reviews and artifacts in a pi session.
---

# Pi Model Name

pi が今どの provider / model で動いているかは、bash ツールに注入される `PI_PROVIDER` / `PI_MODEL` で確認する。システムプロンプトの推測、`PI_DISTILL_MODEL`、セッション履歴の `model_change` / `modelId` を根拠にしない。

## When to Use

- 「今のモデル名を表示して」と聞かれた
- レビューや成果物へ `MODEL_NAME` を記録する
- `PI_MODEL` が空、または `PI_DISTILL_MODEL` と区別できない
- provider / reasoning / session を合わせて確認したい

When NOT to use:

- pi 以外のランタイム（Codex / Claude / Cursor / Grok）のモデル確認
- モデルカタログの一覧や切替操作（`pi --list-models`、`--model` 起動引数の話）
- 料金・性能比較などのモデル選定相談

## Core Pattern

```bash
# ✅ GOOD: ランタイム提示をそのまま読む（bash ツール内で実行）
printf '%s/%s\n' "$PI_PROVIDER" "$PI_MODEL"
```

```bash
# ❌ BAD: 要約用モデルを主モデルと混同する
echo "$PI_DISTILL_MODEL"

# ❌ BAD: 履歴を正式な MODEL_NAME の根拠にする
grep -o '"modelId":"[^"]*"' ~/.pi/agent/sessions/--*/ *.jsonl | tail -1
```

正式な `MODEL_NAME` に履歴を使わない。`PI_PROVIDER` / `PI_MODEL` が空なら履歴へフォールバックせず、停止してユーザに確認する。これは `pr-review` の契約と同じである。

## Quick Reference

| 変数 | 意味 | 備考 |
| --- | --- | --- |
| `PI_PROVIDER` | 現在の provider | bash / powershell ツールにのみ注入 |
| `PI_MODEL` | 現在の model ID | `MODEL_NAME` の正本 |
| `PI_SESSION_ID` | 現セッション ID | ホストシェルの `!` では入らない |
| `PI_SESSION_FILE` | 現セッション jsonl | ephemeral では未設定 |
| `PI_SUBAGENT_SESSION` | 子エージェントのセッション jsonl | `PI_SESSION_FILE` が無いときだけ照合に使う |
| `PI_REASONING_LEVEL` | reasoning 強度 | `off` / `minimal` / `low` / `medium` / `high` / `xhigh` / `max` |
| `PI_DISTILL_MODEL` | 要約・distill 用 | 主モデルではない |
| `AI_AGENT=pi` / `PI_CODING_AGENT=true` | pi 配下の目印 | モデル特定には使わない |

## Implementation

同梱スクリプトが strict 既定で表示する。ランタイム変数が揃い、現在のセッションファイルがある場合は、選択値と直近の応答記録を照合する。履歴読みは情報表示の明示指定だけに使う。

親 checkout の root にいるうちにスクリプトの絶対パスを取得する。同じシェルなら `public/` や公開側 worktree に移動した後も使える。

```bash
# 親 checkout の root で実行
PI_MODEL_SCRIPT="$(git rev-parse --show-toplevel)/.agents/skills/pi-model-name/scripts/print-pi-model.sh"

# 公開側 checkout に移動した後も実行できる
cd public

# 既定: provider/model を表示。欠けたら exit 2 で停止
"$PI_MODEL_SCRIPT"

# 部分だけ要る場合
"$PI_MODEL_SCRIPT" --model
"$PI_MODEL_SCRIPT" --provider
"$PI_MODEL_SCRIPT" --json
"$PI_MODEL_SCRIPT" --session

# 自分のセッションファイルを明示して照合する場合
"$PI_MODEL_SCRIPT" --session-file "$PI_SESSION_FILE" --json

# 情報表示として履歴を許す場合のみ（MODEL_NAME には使わない）
"$PI_MODEL_SCRIPT" --allow-session-history
```

`--allow-session-history` は stdout へ参考値を出し、stderr へ `provenance=session-history` と警告する。この経路の exit 0 は参考値を表示できたことだけを示す。`--json` での出力は `provider` / `model` / `provenance=session-history` の 3 フィールドで、ランタイム照合用の `ok` / `conflicts` / `warnings` は含まない。レビュー本文・ファイル名・`MODEL_NAME` には使わない。

ランタイム照合と明示した履歴表示では、ファイルを `--session-file`、`PI_SESSION_FILE`、`PI_SUBAGENT_SESSION` の順に選ぶ。明示するファイルは自分のセッションと確認したものに限る。cwd や更新時刻から他のセッションを推測しない。ランタイム照合では JSONL の現在の枝だけを読み、`model_change` を `selected`、直近の assistant メッセージを `observed` として比べる。`observed` がモデル切替前なら警告だけを出す。`responseModel` は参考情報で、照合条件には使わない。

値が矛盾すると exit 2 になり、通常のテキスト出力は空になる。`--json` は `ok=false` と `conflicts` を含む。照合できない自動選択ファイルは警告に留め、ランタイム変数の値を返す。明示したファイルを読めない、または別セッションと判明した場合は exit 2 になる。セッションファイルが無くても、ランタイム変数が揃えば従来どおり返す。ランタイム変数が欠けたら strict 既定では exit 2 のままで、セッションファイルから正式値を採用しない。

ランタイム経路の `--json` では `provider` / `model` と `provenance=runtime` が正式値を示す。`ok` は終了コード 0 と対応する。`session_file` は照合ファイルが無い場合に `null` になる。`selected` / `observed` はセッション内の証拠、`conflicts` は矛盾、`warnings` は切替前の応答や照合不可の理由を示す。

## Common Mistakes

- ホストのターミナル（`!` / `!!` / 素の shell）で `env` を見て「空だから履歴で代用する」。注入対象は LLM-callable な bash / powershell だけだ。まずツール内で `printf` する。
- `PI_DISTILL_MODEL=deepinfra-distill/openai/gpt-oss-20b` を主モデルとして報告する。distill は要約用であり、`PI_PROVIDER` / `PI_MODEL` と別物である。
- `~/.pi/agent/sessions` の最後の `model_change` を正式値として記録する。並行セッションや古い切替が混ざる。情報表示の参考値に留め、正式値が無ければユーザ確認で止める。
- `provider/model` を手で組み立て直す。`/`・空白を含む形式はそのまま渡す。ファイル名化が必要な場合の置換は各スキルのヘルパーに任せる。
