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

# cleanup の導入先は実体への絶対 symlink とし、既存コピーを置換する。導入先から helper を解決して
# 保存済みだけを退役し、保存本文・未保存 draft・未保存側の git worktree 登録を保持することを、
# 偽 HOME・一時 git repo・一時 TMP_ROOT だけで確かめる（#359）。
herdr_function="$(sed -n '/^place_herdr_helpers() {$/,/^}$/p' "$installer")"
[ -n "$herdr_function" ] || fail 'no place_herdr_helpers in install_beforehand.bash'
cleanup_case="$tmp/cleanup install"
cleanup_home="$cleanup_case/home"
cleanup_tmp="$cleanup_case/tmp root"
cleanup_repo="$cleanup_case/repo with space"
cleanup_helper="$root/.agents/skills/pr-review/scripts/pr_review_workspace.py"
mkdir -p "$cleanup_home/bin" "$cleanup_tmp" "$cleanup_repo"
# 現行のコピー方式で導入済みの HOME から移行できることを確かめる。
cp "$root/.devcontainer/cleanup-workspace.bash" "$cleanup_home/bin/cleanup-workspace.bash"
install_herdr_helpers() {
  env HOME="$1" WORKSPACE_ROOT="$root" bash -c "cd \"\$1\" && $herdr_function"$'\n''place_herdr_helpers' _ "$root"
}
install_herdr_helpers "$cleanup_home" || fail 'place_herdr_helpers failed with an existing cleanup copy'

cleanup_git() { env HOME="$cleanup_home" git "$@"; }
cleanup_git init -q -b main "$cleanup_repo"
printf 'x\n' > "$cleanup_repo/README.md"
cleanup_git -C "$cleanup_repo" add README.md
cleanup_git -C "$cleanup_repo" -c user.name=Test -c user.email=test@example.com commit -q -m init
cleanup_sha="$(cleanup_git -C "$cleanup_repo" rev-parse HEAD)"
cleanup_python() { env HOME="$cleanup_home" UV_CACHE_DIR="$cleanup_case/uv-cache" uv run --no-project python "$@"; }
cleanup_json_field() { cleanup_python -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"; }
cleanup_create() { # $1=model $2=attempt
  cleanup_python "$cleanup_helper" create --repo "$cleanup_repo" --pr-repo usaturn/create-reso-world --pr-number 359 \
    --commit "$cleanup_sha" --head-branch fix/issue-359-cleanup-symlink --model-name "$1" \
    --temp-root "$cleanup_tmp" --attempt-id "$2"
}

saved_json="$(cleanup_create model-saved a1)" || fail 'failed to create the saved cleanup fixture'
saved_state="$(cleanup_json_field state_file <<<"$saved_json")"
saved_draft="$(cleanup_json_field draft <<<"$saved_json")"
saved_destination="$cleanup_repo/$(cleanup_json_field destination <<<"$saved_json")"
saved_worktree="$(cleanup_json_field worktree <<<"$saved_json")"
saved_session="$(dirname "$saved_state")"
saved_body=$'# 保存済みレビュー\n\n- 日本語の指摘\n- 複数行の本文'
printf '%s' "$saved_body" > "$saved_draft"
cleanup_python "$cleanup_helper" save --state "$saved_state" >/dev/null \
  || fail 'failed to save the cleanup fixture review'

unsaved_json="$(cleanup_create model-unsaved a2)" || fail 'failed to create the unsaved cleanup fixture'
unsaved_state="$(cleanup_json_field state_file <<<"$unsaved_json")"
unsaved_draft="$(cleanup_json_field draft <<<"$unsaved_json")"
unsaved_worktree="$(cleanup_json_field worktree <<<"$unsaved_json")"
unsaved_session="$(dirname "$unsaved_state")"
unsaved_body=$'# 未保存の下書き\n\n- 日本語の未保存本文\n- 保存してはいけない'
printf '%s' "$unsaved_body" > "$unsaved_draft"

worktrees_before="$(cleanup_git -C "$cleanup_repo" worktree list --porcelain)"
grep -Fq "worktree $saved_worktree" <<<"$worktrees_before" || fail 'the saved fixture worktree is not registered'
grep -Fq "worktree $unsaved_worktree" <<<"$worktrees_before" || fail 'the unsaved fixture worktree is not registered'

# helper の場所を明示せず、導入先を直接実行する。
run_installed_cleanup() {
  env -u WORKSPACE_CLEANUP_PR_REVIEW_HELPER -u WORKSPACE_CLEANUP_DRY_RUN \
    HOME="$cleanup_home" WORKSPACE_CLEANUP_TMP_ROOT="$cleanup_tmp" WORKSPACE_CLEANUP_MIN_AGE_DAYS=0 \
    bash "$cleanup_home/bin/cleanup-workspace.bash"
}
cleanup_output="$(run_installed_cleanup)" || fail "the installed cleanup failed\n$cleanup_output"
[ ! -e "$saved_session" ] || fail "the saved session was not retired through the installed helper\n$cleanup_output"
[[ "$cleanup_output" == *"retired pr-review session: $saved_session:"* ]] \
  || fail "no retired line for the saved session\n$cleanup_output"
[ -e "$unsaved_session" ] || fail "the unsaved session was removed\n$cleanup_output"
[ -e "$unsaved_draft" ] || fail "the unsaved draft was removed\n$cleanup_output"
[ "$(cat "$unsaved_draft")" = "$unsaved_body" ] || fail 'the unsaved draft was changed'
[ "$(cat "$saved_destination")" = "$saved_body" ] || fail "the saved review was changed or removed: $saved_destination"
[[ "$cleanup_output" == *"keep "*"$unsaved_session:"* ]] || fail "no keep line for the unsaved session\n$cleanup_output"
worktrees_after="$(cleanup_git -C "$cleanup_repo" worktree list --porcelain)"
grep -Fq "worktree $saved_worktree" <<<"$worktrees_after" \
  && fail 'the retired session worktree is still registered'
grep -Fq "worktree $unsaved_worktree" <<<"$worktrees_after" \
  || fail 'the unsaved session worktree registration was removed'

# 再配置と再実行でも、リンク先を壊さず未保存データを保持する。
install_herdr_helpers "$cleanup_home" || fail 'the second place_herdr_helpers failed'
cleanup_output_second="$(run_installed_cleanup)" || fail "the second installed cleanup failed\n$cleanup_output_second"
[[ "$cleanup_output_second" == *"keep "*"$unsaved_session:"* ]] \
  || fail "no keep line for the unsaved session on the second run\n$cleanup_output_second"
[[ "$cleanup_output_second" != *"pr-review helper unavailable"* ]] \
  || fail "the second run could not resolve the installed helper\n$cleanup_output_second"
[ "$(cat "$unsaved_draft")" = "$unsaved_body" ] || fail 'the unsaved draft was changed on the second run'
[ "$(cat "$saved_destination")" = "$saved_body" ] || fail 'the saved review was changed or removed on the second run'
worktrees_second="$(cleanup_git -C "$cleanup_repo" worktree list --porcelain)"
grep -Fq "worktree $unsaved_worktree" <<<"$worktrees_second" \
  || fail 'the unsaved session worktree registration was removed on the second run'

printf 'PASS: postCreate preserves the agent-runner personal config, upgrades ca-certificates, and installs cleanup through a working symlink\n'
