#!/bin/bash
# 共有する MCP 設定（.pi/mcp.json・.mcp.json）の HTTP header に、鍵を直書きしていないことを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

uv run --no-project python - <<'PY'
import json
import re

# 追跡する MCP 設定（pi の .pi/mcp.json はワールドからも symlink で読む、Claude Code の .mcp.json）の HTTP header は、
# X-Goog-Api-Key などの鍵を運ぶ。値を ${NAME} の環境変数の参照に限り、鍵の直書きをコミットして露出させない。
# create-reso-world は GitHub Actions を無効にしていて CI の gitleaks は動かないので、ローカルで実行するこの検査で直書きを止める
env_ref = re.compile(r"\$\{[A-Z0-9_]+\}")
for path in (".pi/mcp.json", ".mcp.json"):
    for name, server in json.load(open(path))["mcpServers"].items():
        for header, value in server.get("headers", {}).items():
            assert env_ref.fullmatch(value), f"{path}: {name} header {header} must be an ${{ENV}} reference, not a literal"
PY

printf 'PASS: MCP headers use env references\n'
