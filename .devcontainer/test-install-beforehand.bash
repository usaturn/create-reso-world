#!/bin/bash
# postCreate（.devcontainer/install_beforehand.bash）の構文と、導入する Claude Code のプラグインを検査する。仕様 7.1 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
installer="$root/.devcontainer/install_beforehand.bash"
settings="$root/.claude/settings.json"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

bash -n "$installer"

# Claude Code のプラグインは .claude/settings.json の enabledPlugins と同じ集合を導入する（仕様 7.1）
installed="$(sed -n '/^for plugin in \\$/,/; do$/p' "$installer" | sed -n 's/^[[:space:]]*\([^[:space:];\\]*@[^[:space:];\\]*\).*/\1/p' | LC_ALL=C sort)"
enabled="$(uv run --no-project python - "$settings" <<'PY' | LC_ALL=C sort
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    plugins = json.load(handle)["enabledPlugins"]
for name, enabled in plugins.items():
    if enabled is True:
        print(name)
PY
)"
[ -n "$installed" ] || fail 'no plugin list found in install_beforehand.bash'
[ "$installed" = "$enabled" ] || fail "plugins installed by install_beforehand.bash differ from enabledPlugins:
installed:
$installed
enabled:
$enabled"

printf 'PASS: postCreate parses and installs the enabled Claude Code plugins\n'
