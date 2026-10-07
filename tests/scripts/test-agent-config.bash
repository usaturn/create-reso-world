#!/bin/bash
# Codex のプロジェクト設定（.codex/config.toml）の MCP サーバーが、ユーザー設定と混ざらず、外部パッケージへ渡す
# 環境変数を API キーだけに限っていること、共有する MCP 設定の HTTP header に鍵を直書きしていないことを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

uv run --no-project python - <<'PY'
import json
import re
import tomllib

codex = tomllib.load(open(".codex/config.toml", "rb"))
# Codex は同名の MCP 設定を項目ごとにマージする。ユーザー設定の context7（HTTP）と同名にすると、stdio の項目が
# 混ざって接続できなくなる（8a95021 で直した不具合）。
assert "context7" not in codex["mcp_servers"], "project MCP must not reuse the user-level context7 name"
# npx で取得する外部パッケージに渡す環境変数は、API キーだけに限る。増やすと他の秘密情報もそのプロセスに渡る
c7 = codex["mcp_servers"]["context7_stdio"]
assert c7.get("env_vars") == ["CONTEXT7_API_KEY"], c7

# 追跡する MCP 設定（pi の .pi/mcp.json はワールドからも symlink で読む、Claude Code の .mcp.json）の HTTP header は、
# X-Goog-Api-Key などの鍵を運ぶ。値を ${NAME} の環境変数の参照に限り、鍵の直書きをコミットして露出させない。
# private リポジトリの CI は停止しており gitleaks も実行されないので、この検査だけが直書きを止める
env_ref = re.compile(r"\$\{[A-Z0-9_]+\}")
for path in (".pi/mcp.json", ".mcp.json"):
    for name, server in json.load(open(path))["mcpServers"].items():
        for header, value in server.get("headers", {}).items():
            assert env_ref.fullmatch(value), f"{path}: {name} header {header} must be an ${{ENV}} reference, not a literal"
PY

printf 'PASS: Codex MCP config keeps the user-level name and forwards only the API key; MCP headers use env references\n'
