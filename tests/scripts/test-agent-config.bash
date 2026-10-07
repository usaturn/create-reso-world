#!/bin/bash
# Codex のプロジェクト設定（.codex/config.toml）の MCP サーバーが、ユーザー設定と混ざらず、外部パッケージへ渡す
# 環境変数を API キーだけに限っていることを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

uv run --no-project python - <<'PY'
import tomllib

codex = tomllib.load(open(".codex/config.toml", "rb"))
# Codex は同名の MCP 設定を項目ごとにマージする。ユーザー設定の context7（HTTP）と同名にすると、stdio の項目が
# 混ざって接続できなくなる（8a95021 で直した不具合）。
assert "context7" not in codex["mcp_servers"], "project MCP must not reuse the user-level context7 name"
# npx で取得する外部パッケージに渡す環境変数は、API キーだけに限る。増やすと他の秘密情報もそのプロセスに渡る
c7 = codex["mcp_servers"]["context7_stdio"]
assert c7.get("env_vars") == ["CONTEXT7_API_KEY"], c7
PY

printf 'PASS: Codex MCP config keeps the user-level name and forwards only the API key\n'
