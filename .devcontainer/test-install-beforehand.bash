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

# agent-runner の個人設定は、無いときだけ雛形を写す。既存の設定（壊れた symlink も）は変えず、置けなければ失敗を返す。
# 保存先は runner の resolve_config_path と同じく、絶対パスの XDG_CONFIG_HOME か ~/.config の下
function="$(sed -n '/^place_agent_runner_config() {$/,/^}$/p' "$installer")"
[ -n "$function" ] || fail 'no place_agent_runner_config in install_beforehand.bash'
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
place() { env HOME="$1" XDG_CONFIG_HOME="$2" bash -c "cd \"\$1\" && $function"$'\n''place_agent_runner_config' _ "$root"; }
for xdg in '' relative absolute; do
  home="$tmp/home-${xdg:-empty}"
  mkdir -p "$home"
  value="$xdg" config_home="$home/.config"
  if [ "$xdg" = absolute ]; then value="$tmp/xdg" config_home="$tmp/xdg"; fi
  target="$config_home/agent-runner/config.toml"
  place "$home" "$value" || fail "place_agent_runner_config failed (XDG_CONFIG_HOME='$value')"
  cmp -s "$target" "$root/.devcontainer/agent-runner.toml" || fail "the template was not copied to $target"
  printf 'user customization\n' > "$target"
  place "$home" "$value" || fail "the second run failed (XDG_CONFIG_HOME='$value')"
  [ "$(cat "$target")" = 'user customization' ] || fail "an existing personal config was overwritten: $target"
done
home="$tmp/broken-home"
mkdir -p "$home/.config/agent-runner"
ln -s "$home/not-created" "$home/.config/agent-runner/config.toml"
place "$home" '' || fail 'place_agent_runner_config failed on a broken symlink'
[ "$(readlink "$home/.config/agent-runner/config.toml")" = "$home/not-created" ] && [ ! -e "$home/not-created" ] \
  || fail 'a broken personal symlink was replaced or followed'
home="$tmp/unwritable-home"
mkdir -p "$home"
printf 'not a directory\n' > "$home/.config"
if place "$home" '' 2>/dev/null; then fail 'place_agent_runner_config succeeded without a writable destination'; fi

printf 'PASS: postCreate parses, installs the enabled Claude Code plugins and places the agent-runner config\n'
