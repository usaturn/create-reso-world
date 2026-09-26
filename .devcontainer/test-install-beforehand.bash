#!/bin/bash
# postCreate（.devcontainer/install_beforehand.bash）の導入手順が仕様 7.1・7.2 節のとおりであることを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
installer="$root/.devcontainer/install_beforehand.bash"
settings="$root/.claude/settings.json"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# first_line PATTERN: install_beforehand.bash で PATTERN（grep -E）に一致する最初の行番号。無ければ失敗
first_line() {
  local n
  n="$(grep -m 1 -nE -- "$1" "$installer" | cut -d: -f1 || true)"
  [ -n "$n" ] || fail "install_beforehand.bash lacks: $1"
  printf '%s\n' "$n"
}
# commands PATTERN: コメント行を除いて PATTERN（grep -E）に一致する行数
commands() {
  local body
  body="$(grep -vE '^[[:space:]]*#' "$installer")"
  grep -cE -- "$1" <<<"$body" || true
}

bash -n "$installer"

# 1. Claude Code のプラグインは .claude/settings.json の enabledPlugins と同じ集合を導入する（仕様 7.1）
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
for p in superpowers@claude-plugins-official feature-dev@claude-plugins-official; do
  grep -qxF "$p" <<<"$installed" || fail "$p is not installed"
done

# 2. Codex は npm で導入し、PATH に載ったことを確かめる（仕様 7.1・7.2）
codex_step="$(first_line '^step "Installing Codex"$')"
[ "$(first_line '^if ! npm install -g @openai/codex@latest; then$')" -gt "$codex_step" ] || fail 'npm install of Codex is not in its step'
first_line 'command -v codex' >/dev/null

# 3. uv は pi の設定より前に導入し、setup_pi_tool_display.py は uv run で実行する（仕様 7.2）
uv_step="$(first_line '^step "Installing uv"$')"
[ "$uv_step" -lt "$(first_line '^step "Installing pi"$')" ] || fail 'uv must be installed before pi'
[ "$uv_step" -lt "$(first_line 'uv run ')" ] || fail 'uv must be installed before the first uv run'
first_line '^if ! uv run --no-project \.devcontainer/setup_pi_tool_display\.py; then$' >/dev/null
[ "$(commands 'python3')" -eq 0 ] || fail 'install_beforehand.bash must not run python3 directly'

# 4. 重複していた apt update と ~/.local/bin の PATH の export は 1 回だけ（仕様 7.2）
[ "$(commands 'sudo apt update')" -eq 1 ] || fail 'apt update must run exactly once'
[ "$(commands '^export PATH="\$\{HOME\}/\.local/bin:\$\{PATH\}"$')" -eq 1 ] || fail '~/.local/bin must be exported exactly once'

# 5. 移行元リポジトリの Issue 番号をコメントに残さない
if grep -nE '#[0-9]{3}\b' "$installer"; then fail 'install_beforehand.bash still refers to old issue numbers'; fi

printf 'PASS: postCreate installs the tools listed in spec 7.1\n'
