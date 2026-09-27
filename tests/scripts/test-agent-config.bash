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
c7 = codex["mcp_servers"]["context7"]
assert c7["command"] == "npx", c7
assert c7["args"] == ["-y", "@upstash/context7-mcp"], c7
assert c7.get("env_vars") == ["CONTEXT7_API_KEY"], c7

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
