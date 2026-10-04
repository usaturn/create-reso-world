#!/bin/bash
# エージェントの設定ファイルと pi-superagents の定義が仕様 5.5・4.2 と判断事項 D-1 のとおりであることを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

uv run --no-project python - <<'PY'
import json
import tomllib

codex = tomllib.load(open(".codex/config.toml", "rb"))
# ユーザー設定の context7（HTTP）と、プロジェクト設定（stdio）を同名でマージさせない。
assert "context7" not in codex["mcp_servers"], "project MCP must not reuse the user-level context7 name"
c7 = codex["mcp_servers"]["context7_stdio"]
assert c7["command"] == "npx", c7
assert c7["args"] == ["-y", "@upstash/context7-mcp"], c7
assert c7.get("env_vars") == ["CONTEXT7_API_KEY"], c7

user_http = {"url": "https://mcp.context7.com/mcp", "bearer_token_env_var": "CONTEXT7_API_KEY"}
merged_servers = {"context7": dict(user_http)}
# 今回の設定はサーバー直下に項目が並ぶため、項目ごとのマージで Codex の挙動を再現する。
for name, server in codex["mcp_servers"].items():
    merged_servers.setdefault(name, {}).update(server)
assert merged_servers["context7"] == user_http, merged_servers
assert merged_servers["context7_stdio"] == c7, merged_servers
for server in merged_servers.values():
    if "command" in server:
        assert "url" not in server and "bearer_token_env_var" not in server, server

cursor = json.load(open(".cursor/mcp.json", encoding="utf-8"))
cc7 = cursor["mcpServers"]["context7"]
assert cc7["command"] == "npx" and cc7["args"] == ["-y", "@upstash/context7-mcp"], cc7

lens = json.load(open(".pi-lens.json", encoding="utf-8"))
assert "$schema" not in lens, lens
for pattern in (".devcontainer/devcontainer.json", "**/*.md", "**/*.markdown", "**/*.mdx",
                "**/tmp/**", "**/.venv/**", "**/artifacts/**", "**/.resoloop/**", "external/**", "private/**"):
    assert pattern in lens["ignore"], pattern
PY

# pi-superagents: 組み込み定義と内容が違う sp-implementer.md だけを追跡する（判断事項 D-1）
grep -qxF 'name: sp-implementer' .agents/sp-implementer.md || fail '.agents/sp-implementer.md missing'
grep -qxF 'model: balanced' .agents/sp-implementer.md || fail 'sp-implementer must keep model: balanced'
[ "$(cd .agents && ls sp-*.md 2>/dev/null)" = 'sp-implementer.md' ] || fail 'unexpected sp-*.md set under .agents'
# Devin は symlink 経由の同名スキルを 1 回だけ表示するので、Claude 互換読込は止めない（仕様 5.5 の条件が成立しない）
[ ! -e .devin/config.json ] || fail '.devin/config.json must not be created'

printf 'PASS: agent configuration follows spec 5.5\n'
