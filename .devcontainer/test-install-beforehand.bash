#!/bin/bash
# postCreate（.devcontainer/install_beforehand.bash）の agent-runner の個人設定の配置（仕様 7.1 節）と、ca-certificates の更新（#291）を検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
installer="$root/.devcontainer/install_beforehand.bash"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# agent-runner の個人設定は、無いときだけ最小のファイル（agent-runner-personal.toml）を置く。既存の設定（壊れた symlink も）は変えず、
# 置けなければ失敗を返す。
# 保存先は runner の resolve_config_path と同じく、絶対パスの XDG_CONFIG_HOME か ~/.config の下
function="$(sed -n '/^place_agent_runner_config() {$/,/^}$/p' "$installer")"
[ -n "$function" ] || fail 'no place_agent_runner_config in install_beforehand.bash'
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
place() { env HOME="$1" XDG_CONFIG_HOME="$2" bash -c "cd \"\$1\" && $function"$'\n''place_agent_runner_config' _ "$root"; }
home="$tmp/home"
mkdir -p "$home"
target="$home/.config/agent-runner/config.toml"
place "$home" '' || fail 'place_agent_runner_config failed'
cmp -s "$target" "$root/.devcontainer/agent-runner-personal.toml" || fail "the minimal personal config was not placed at $target"
cp "$target" "$tmp/placed.toml"
printf 'user customization\n' > "$target"
place "$home" '' || fail 'the second run failed'
[ "$(cat "$target")" = 'user customization' ] || fail "an existing personal config was overwritten: $target"
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

# ca-certificates は更新した索引の最新版へ上げ、apt-get が失敗したら失敗を返す（#291）。成功として返すと、
# 古いトラストストアのまま postCreate が進む。偽の sudo・apt-get で実行し、実際のパッケージには触れない
upgrade_function="$(sed -n '/^upgrade_ca_certificates() {$/,/^}$/p' "$installer")"
[ -n "$upgrade_function" ] || fail 'no upgrade_ca_certificates in install_beforehand.bash'
mkdir -p "$tmp/bin"
printf '#!/bin/bash\nexec "$@"\n' > "$tmp/bin/sudo"
printf '#!/bin/bash\nprintf "%%s\\n" "$*" >> "$FAKE_APT_LOG"\nexit "$FAKE_APT_EXIT"\n' > "$tmp/bin/apt-get"
chmod +x "$tmp/bin/sudo" "$tmp/bin/apt-get"
upgrade() {
  env PATH="$tmp/bin:$PATH" FAKE_APT_LOG="$tmp/apt.log" FAKE_APT_EXIT="$1" \
    bash -c "$upgrade_function"$'\n''upgrade_ca_certificates'
}
if upgrade 100; then
  fail 'upgrade_ca_certificates returned success although apt-get failed'
fi
: > "$tmp/apt.log"
upgrade 0 || fail 'upgrade_ca_certificates failed although apt-get succeeded'
grep -qE '(^| )install( |$)' "$tmp/apt.log" && grep -qE '(^| )ca-certificates( |$)' "$tmp/apt.log" \
  || fail "upgrade_ca_certificates did not install ca-certificates: $(cat "$tmp/apt.log")"

printf 'PASS: postCreate preserves the agent-runner personal config and upgrades ca-certificates\n'
