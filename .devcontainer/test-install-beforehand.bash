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

# agent-runner の個人設定は、無いときだけ最小のファイル（agent-runner-personal.toml）を置く。既存の設定（壊れた symlink も）は変えず、
# 置けなければ失敗を返す。
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
  cmp -s "$target" "$root/.devcontainer/agent-runner-personal.toml" || fail "the minimal personal config was not placed at $target"
  [ -e "$tmp/placed.toml" ] || cp "$target" "$tmp/placed.toml"
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
# 置いた個人設定と一緒に読んでも、雛形で変えた値が効く（#167）。各役割の期限と各 agent のモデルを変えた雛形で確かめる
(cd "$root" && uv run --project "$root" --locked python - "$root/.devcontainer/agent-runner.toml" "$tmp/placed.toml" "$tmp/changed.toml") <<'PY' \
  || fail 'a value changed in the template did not take effect with the personal config placed by postCreate'
import re
import sys
from pathlib import Path

from tools.agent_runner import load_config

template, placed, changed = map(Path, sys.argv[1:])
text = template.read_text(encoding="utf-8")
text = re.sub(r"(?m)^(deadline_seconds = )(\d+)$", lambda match: f"{match[1]}{int(match[2]) + 1}", text)
text = re.sub(r'(?m)^(model = "[^"]*)"$', r'\1-changed"', text)
changed.write_text(text, encoding="utf-8")
base = load_config(template)
merged = load_config(changed, placed)
assert base.roles and base.agents
assert merged == load_config(changed)
assert all(merged.roles[name].deadline_seconds == role.deadline_seconds + 1 for name, role in base.roles.items())
assert all(merged.agents[name].model == f"{agent.model}-changed" for name, agent in base.agents.items())
PY

# Execute the DSH installation function and its actual postCreate call with shell stubs.
# The stub derives its version from the requested package, rather than copying a changing version into this test.
dsh_function="$(sed -n '/^install_deepseek_harness() {$/,/^}$/p' "$installer")"
dsh_stage="$(sed -n '/^step "Installing the pinned DSH headless CLI"$/,/^fi$/p' "$installer")"
[ -n "$dsh_function" ] && [ -n "$dsh_stage" ] || fail 'no DSH installation stage in install_beforehand.bash'
for mode in success npm-failure missing-cli version-failure wrong-version; do
  probe="$tmp/dsh-$mode"
  mkdir -p "$probe/bin" "$probe/home"
  status=0
  env HOME="$probe/home" PATH="$probe/bin" PROBE="$probe" MODE="$mode" /bin/bash --noprofile --norc -c '
    step() { :; }
    fail() { printf "failed: %s\n" "$*" >&2; exit 1; }
    npm() {
      printf "%s\n" "$@" > "$PROBE/npm-args"
      [ "$MODE" != npm-failure ] || return 23
      [ "$1" = install ] && [ "$2" = -g ] || return 24
      case "$3" in --allow-scripts=?*) ;; *) return 25 ;; esac
      case "$4" in @deepseek-ai/dsh@?*) printf "%s\n" "${4#@deepseek-ai/dsh@}" > "$PROBE/version" ;; *) return 26 ;; esac
      [ "$#" = 4 ] || return 27
    }
    if [ "$MODE" != missing-cli ]; then
      dsh() {
        printf "%s\n" "$@" > "$PROBE/dsh-args"
        [ "$1" = --version ] && [ "$#" = 1 ] || return 28
        [ "$MODE" != version-failure ] || return 29
        if [ "$MODE" = wrong-version ]; then printf "not-the-requested-version\n"; return; fi
        read -r version < "$PROBE/version"
        printf "%s\n" "$version"
      }
    fi
  '"$dsh_function"$'\n'"$dsh_stage"$'\n''printf "reached\n" > "$PROBE/after"' > "$probe/stdout" 2> "$probe/stderr" || status=$?
  if [ "$mode" = success ]; then
    [ "$status" = 0 ] && [ -f "$probe/after" ] && [ -f "$probe/dsh-args" ] || fail 'DSH installation did not reach the next stage'
  else
    [ "$status" != 0 ] && [ ! -e "$probe/after" ] || fail "DSH installation continued after $mode"
  fi
done

printf 'PASS: postCreate parses, installs enabled plugins, preserves agent-runner config and checks pinned DSH installation\n'
