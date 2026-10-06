#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZSHRC_TEMPLATE="${REPO_ROOT}/.devcontainer/zshrc.txt"
HERDR_CONFIG="${REPO_ROOT}/.devcontainer/herdr.toml"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "${TEST_ROOT}"' EXIT

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
assert_contains() {
    rg -q -- "$2" "$1" || fail "$1 does not contain $2"
}
assert_absent() {
    ! rg -q -i -- "$2" "$1" || fail "$1 must not contain $2"
}
assert_before() {
    local file="$1"
    local earlier_pattern="$2"
    local later_pattern="$3"
    local earlier_line
    local later_line
    earlier_line="$(rg -n -m1 -- "$earlier_pattern" "$file" | cut -d: -f1)" \
        || fail "$file does not contain $earlier_pattern"
    later_line="$(rg -n -m1 -- "$later_pattern" "$file" | cut -d: -f1)" \
        || fail "$file does not contain $later_pattern"
    [ "$earlier_line" -lt "$later_line" ] \
        || fail "$earlier_pattern must appear before $later_pattern in $file"
}
extract_cc_launcher_unsets() {
    sed -n '/^typeset -a cc_launcher_unsets=(/,/^)/p' "$1" \
        | rg -o -- '-u [A-Z0-9_]+' \
        | sort -u \
        | sed 's/^-u //'
}
# zshrc テンプレートを隔離環境で実行する共通部。$@ で追加の VAR=value を渡せる。
run_zshrc_code() {
    local test_home="$1"
    local zsh_code="$2"
    shift 2
    env -u TMUX -u HERDR_ENV -u HERDR_SOCKET_PATH \
        HOME="$test_home" \
        PATH="$test_home/bin:/usr/bin:/bin" \
        HERDR_TEST_LOG="$test_home/herdr.log" \
        ZSHRC_TEMPLATE="$ZSHRC_TEMPLATE" \
        "$@" /usr/bin/zsh -f -c "$zsh_code" </dev/null >/dev/null
}
run_zshrc() {
    local test_home="$1"
    shift
    run_zshrc_code "$test_home" 'source "$ZSHRC_TEMPLATE"' "$@"
}
run_zshrc_tty() {
    local test_home="$1"
    # 意図的に HOME から起動し、herdrstart がワークスペースへ cd するかを検証できるようにする
    local zsh_command='cd "$HOME" && /usr/bin/zsh -f -c '\''source "$ZSHRC_TEMPLATE"'\'' 2>"$HERDR_TEST_STDERR"'
    shift
    env -u TMUX -u HERDR_ENV -u HERDR_SOCKET_PATH \
        HOME="$test_home" \
        PATH="$test_home/bin:/usr/bin:/bin" \
        HERDR_TEST_LOG="$test_home/herdr.log" \
        HERDR_TEST_STDERR="$test_home/stderr.log" \
        ZSHRC_TEMPLATE="$ZSHRC_TEMPLATE" \
        "$@" script -qec "$zsh_command" /dev/null
}
# herdr / herdr-status-updater / starship のスタブと空ログを用意する。
make_stub_home() {
    local dir="$1"
    mkdir -p "$dir/bin"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$dir/bin/starship"
    printf '%s\n' '#!/bin/sh' \
        'if [ "${1:-} ${2:-} ${3:-}" = "status server --json" ]; then' \
        '    printf "%s\n" "${HERDR_TEST_STATUS_JSON:-{\"running\":false\}}"' \
        '    exit "${HERDR_TEST_STATUS_RC:-0}"' \
        'fi' \
        'printf "called TZ=%s PWD=%s\\n" "${TZ:-}" "$PWD" >> "$HERDR_TEST_LOG"' \
        > "$dir/bin/herdr"
    printf '%s\n' '#!/bin/sh' \
        'printf "updater %s\\n" "$*" >> "$HERDR_TEST_LOG.upd"' \
        > "$dir/bin/herdr-status-updater"
    chmod +x "$dir/bin/starship" "$dir/bin/herdr" "$dir/bin/herdr-status-updater"
    # set -e 下で `wc -l < 不在ファイル` が無言終了しないよう先に空で作る
    : > "$dir/herdr.log"
    : > "$dir/herdr.log.upd"
}

write_session_fixture() {
    local session_file="$1"
    local workspace_root="$2"
    local workspace_dir="$3"
    local worktree_dir="$4"
    mkdir -p "$(dirname "$session_file")" "$workspace_dir" "$worktree_dir"
    python3 - "$session_file" "$workspace_root" "$worktree_dir" <<'PY'
import json
import os
import sys

session_file, workspace_root, worktree_dir = sys.argv[1:]
data = {
    "version": 3,
    "unknown_top_level": {"keep": True},
    "workspaces": [{
        "id": "w1",
        "identity_cwd": "/home/vscode",
        "unknown_workspace_field": "keep",
        "tabs": [{
            "id": "w1:t1",
            "panes": {
                "0": {
                    "cwd": "/deleted/worktree",
                    "agent_session": {"provider": "codex", "id": "resume-me"},
                },
                "1": {"cwd": worktree_dir},
                "2": {"cwd": os.path.join(workspace_root, "deleted-repo")},
            },
        }],
    }],
}
with open(session_file, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
}

write_multi_workspace_fixture() {
    local session_file="$1"
    local workspace_dir="$2"
    mkdir -p "$(dirname "$session_file")" "$workspace_dir"
    python3 - "$session_file" <<'PY'
import json
import sys

session_file = sys.argv[1]
data = {
    "version": 3,
    "workspaces": [
        {
            "id": "w1",
            "identity_cwd": "/home/vscode",
            "tabs": [{"id": "w1:t1", "panes": {"0": {"cwd": "/home/vscode"}}}],
        },
        {
            "id": "w2",
            "identity_cwd": "/home/vscode/other",
            "tabs": [{"id": "w2:t1", "panes": {"0": {"cwd": "/nonexistent/gone"}}}],
        },
    ],
}
with open(session_file, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
}

run_session_repair() {
    local test_home="$1"
    local workspace_root="$2"
    local workspace_dir="$3"
    shift 3
    run_zshrc_code "$test_home" \
        'source "$ZSHRC_TEMPLATE"; herdr_repair_session_cwd "$HERDR_TEST_WORKSPACE"' \
        HERDR_WORKSPACE_ROOT="$workspace_root" \
        HERDR_TEST_WORKSPACE="$workspace_dir" \
        "$@"
}

test_config_and_syntax() {
    zsh -n "$ZSHRC_TEMPLATE"
    assert_contains "$HERDR_CONFIG" '^prefix = "ctrl\+k"$'
    assert_contains "$HERDR_CONFIG" '\$clock'
    assert_contains "${REPO_ROOT}/.devcontainer/devcontainer.json" \
        '"userEnvProbe": "loginShell"'
    assert_contains "$ZSHRC_TEMPLATE" '^function herdrstart\(\)\{$'
    assert_contains "$ZSHRC_TEMPLATE" 'herdr-status-updater'
    assert_contains "$ZSHRC_TEMPLATE" '^function herdr_select_workspace\(\)\{$'
    assert_contains "$ZSHRC_TEMPLATE" '^function herdr_repair_session_cwd\(\)\{$'
    assert_contains "$ZSHRC_TEMPLATE" 'workspace_dir="\$\(herdr_select_workspace\)"'
    assert_contains "$ZSHRC_TEMPLATE" 'cd -- "\$workspace_dir"'
    assert_before "$ZSHRC_TEMPLATE" \
        'herdr_repair_session_cwd "\$workspace_dir"' '^    herdr$'

    # herdrstart が herdr セッション内で no-op になるガード
    assert_contains "$ZSHRC_TEMPLATE" 'HERDR_ENV'

    # tmux 撤去後の再混入防止。assert_absent は -i 付きのため TMUX も検出する
    assert_absent "$ZSHRC_TEMPLATE" 'tmux'
    local removed
    for removed in tmux.conf tmux-git-status.bash tmux-url-copy.zsh; do
        [ ! -e "${REPO_ROOT}/.devcontainer/${removed}" ] \
            || fail "${removed} must not exist"
    done
}

# ここで検証するのは herdrstart 経路のみ。
# herdr-status-updater の起動経路は現在 herdrstart 内の 1 本だけである
# （precmd フックは production から削除済み）。
test_launch_and_guards() {
    local test_home="${TEST_ROOT}/home"
    # 実機の /workspaces に依存しないよう、テスト用のワークスペースルートを用意する
    local workspace_root="${TEST_ROOT}/workspaces"
    local workspace_dir="${workspace_root}/reso-world"
    mkdir -p "$workspace_dir"
    make_stub_home "$test_home"

    # 起動元 cwd が HOME でも herdr プロセスは HERDR_WORKSPACE_ROOT 配下の
    # ワークスペースで起動すること
    run_zshrc_tty "$test_home" HERDR_WORKSPACE_ROOT="$workspace_root"
    [ "$(wc -l < "$test_home/herdr.log")" -eq 1 ] || fail 'TTY herdr call count'
    assert_contains "$test_home/herdr.log" "^called TZ=Asia/Tokyo PWD=${workspace_dir}"
    assert_contains "$test_home/herdr.log.upd" '^updater --daemon$'
    [ "$(wc -l < "$test_home/herdr.log.upd")" -eq 1 ] || fail 'TTY herdrstart updater call count'

    : > "$test_home/herdr.log"
    : > "$test_home/herdr.log.upd"
    run_zshrc "$test_home"
    [ ! -s "$test_home/herdr.log" ] || fail 'non-TTY guard'
    [ ! -s "$test_home/herdr.log.upd" ] || fail 'non-TTY herdrstart updater guard'

    : > "$test_home/herdr.log"
    : > "$test_home/herdr.log.upd"
    run_zshrc_tty "$test_home" HERDR_ENV=1
    [ ! -s "$test_home/herdr.log" ] || fail 'HERDR_ENV guard'
    # herdrstart 経路では updater を起動しないこと（precmd 経路は存在しない）
    [ ! -s "$test_home/herdr.log.upd" ] || fail 'HERDR_ENV herdrstart updater guard'

    # tmux 撤去後は TMUX が立っていても herdrstart は進行する
    : > "$test_home/herdr.log"
    : > "$test_home/herdr.log.upd"
    run_zshrc_tty "$test_home" TMUX=/tmp/tmux-test
    [ "$(wc -l < "$test_home/herdr.log")" -eq 1 ] || fail 'TMUX must not suppress herdrstart'
    [ "$(wc -l < "$test_home/herdr.log.upd")" -eq 1 ] || fail 'TMUX must not suppress herdrstart updater'

    mv "$test_home/bin/herdr" "$test_home/bin/herdr.disabled"
    : > "$test_home/herdr.log.upd"
    run_zshrc_tty "$test_home"
    assert_contains "$test_home/stderr.log" 'herdr not found'
    [ ! -s "$test_home/herdr.log.upd" ] || fail 'herdrstart updater skipped when herdr missing'
}

# セッション cwd 修復は guard 済みで、precmd 経路は存在しない（production で削除済み）。

test_session_cwd_repair() {
    local test_home="${TEST_ROOT}/home-repair"
    local workspace_root="${TEST_ROOT}/workspaces"
    local workspace_dir="${workspace_root}/reso-world"
    local worktree_dir="${workspace_dir}/.worktrees/feature"
    local session_file="${test_home}/.config/herdr/session.json"
    make_stub_home "$test_home"

    write_session_fixture "$session_file" "$workspace_root" "$workspace_dir" "$worktree_dir"
    run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
        HERDR_TEST_STATUS_JSON='{"running":false}'
    python3 - "$session_file" "$workspace_dir" "$worktree_dir" <<'PY'
import json
import sys

session_file, workspace_dir, worktree_dir = sys.argv[1:]
with open(session_file, encoding="utf-8") as handle:
    data = json.load(handle)
workspace = data["workspaces"][0]
panes = workspace["tabs"][0]["panes"]
assert workspace["identity_cwd"] == workspace_dir
assert panes["0"]["cwd"] == workspace_dir
assert panes["1"]["cwd"] == worktree_dir
assert panes["2"]["cwd"] == workspace_dir
assert panes["0"]["agent_session"] == {"provider": "codex", "id": "resume-me"}
assert workspace["unknown_workspace_field"] == "keep"
assert data["unknown_top_level"] == {"keep": True}
PY
    [ ! -e "${session_file}.tmp" ] || fail 'repair must not leave a temporary file'

    write_session_fixture "$session_file" "$workspace_root" "$workspace_dir" "$worktree_dir"
    cp "$session_file" "${session_file}.before"
    run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
        HERDR_TEST_STATUS_JSON='{"running":true}'
    cmp -s "$session_file" "${session_file}.before" \
        || fail 'running server must leave session unchanged'

    printf '%s\n' '{invalid json' > "$session_file"
    cp "$session_file" "${session_file}.before"
    run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
        HERDR_TEST_STATUS_JSON='{"running":false}'
    cmp -s "$session_file" "${session_file}.before" \
        || fail 'invalid session JSON must remain unchanged'
    [ ! -e "${session_file}.tmp" ] || fail 'invalid JSON must not leave a temporary file'

    write_session_fixture "$session_file" "$workspace_root" "$workspace_dir" "$worktree_dir"
    python3 - "$session_file" <<'PY'
import json
import sys

session_file = sys.argv[1]
with open(session_file, encoding="utf-8") as handle:
    data = json.load(handle)
data["version"] = 4
with open(session_file, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
    cp "$session_file" "${session_file}.before"
    run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
        HERDR_TEST_STATUS_JSON='{"running":false}'
    cmp -s "$session_file" "${session_file}.before" \
        || fail 'unknown session version must remain unchanged'
    [ ! -e "${session_file}.tmp" ] \
        || fail 'unknown session version must not leave a temporary file'

    local restricted_dir="${workspace_root}/restricted"
    mkdir -p "$restricted_dir"
    chmod 0444 "$restricted_dir"
    local bad_workspace
    for bad_workspace in "${workspace_root}/no-such-dir" "$restricted_dir"; do
        write_session_fixture "$session_file" "$workspace_root" "$workspace_dir" "$worktree_dir"
        cp "$session_file" "${session_file}.before"
        run_session_repair "$test_home" "$workspace_root" "$bad_workspace" \
            HERDR_TEST_STATUS_JSON='{"running":false}'
        cmp -s "$session_file" "${session_file}.before" \
            || fail "invalid repair destination must leave session unchanged: $bad_workspace"
        [ ! -e "${session_file}.tmp" ] \
            || fail "invalid repair destination must not leave a temporary file: $bad_workspace"
    done
    chmod 0755 "$restricted_dir"

    local status_case
    for status_case in command_failure malformed_json missing_running string_false numeric_zero; do
        write_session_fixture "$session_file" "$workspace_root" "$workspace_dir" "$worktree_dir"
        cp "$session_file" "${session_file}.before"
        case "$status_case" in
            command_failure)
                run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
                    HERDR_TEST_STATUS_JSON='{"running":false}' HERDR_TEST_STATUS_RC=1
                ;;
            malformed_json)
                run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
                    HERDR_TEST_STATUS_JSON='not-json'
                ;;
            missing_running)
                run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
                    HERDR_TEST_STATUS_JSON='{"status":"unknown"}'
                ;;
            string_false)
                run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
                    HERDR_TEST_STATUS_JSON='{"running":"false"}'
                ;;
            numeric_zero)
                run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
                    HERDR_TEST_STATUS_JSON='{"running":0}'
                ;;
        esac
        cmp -s "$session_file" "${session_file}.before" \
            || fail "$status_case must leave session unchanged"
        [ ! -e "${session_file}.tmp" ] \
            || fail "$status_case must not leave a temporary file"
    done

    # 修復先がワークスペースルート自身: fzf キャンセル相当。session を焼き付けない
    write_session_fixture "$session_file" "$workspace_root" "$workspace_dir" "$worktree_dir"
    cp "$session_file" "${session_file}.before"
    run_session_repair "$test_home" "$workspace_root" "$workspace_root" \
        HERDR_TEST_STATUS_JSON='{"running":false}'
    cmp -s "$session_file" "${session_file}.before" \
        || fail 'repair target equal to workspace root must leave session unchanged'
    [ ! -e "${session_file}.tmp" ] \
        || fail 'workspace-root repair target must not leave a temporary file'
}

# 複数エントリの収束回避: 修復されるのは最大 1 エントリ。
test_session_cwd_repair_multi_workspace() {
    local test_home="${TEST_ROOT}/home-repair-multi"
    local workspace_root="${TEST_ROOT}/workspaces-multi"
    local workspace_dir="${workspace_root}/reso-world"
    local session_file="${test_home}/.config/herdr/session.json"
    make_stub_home "$test_home"

    # 修復先をまだ誰も持たない場合: 先頭の壊れたエントリだけを修復し、2 件目は触らない
    write_multi_workspace_fixture "$session_file" "$workspace_dir"
    run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
        HERDR_TEST_STATUS_JSON='{"running":false}'
    python3 - "$session_file" "$workspace_dir" <<'PY'
import json
import sys

session_file, workspace_dir = sys.argv[1:]
with open(session_file, encoding="utf-8") as handle:
    data = json.load(handle)
w1, w2 = data["workspaces"]
assert w1["identity_cwd"] == workspace_dir
assert w1["tabs"][0]["panes"]["0"]["cwd"] == workspace_dir
assert w2["identity_cwd"] == "/home/vscode/other"
assert w2["tabs"][0]["panes"]["0"]["cwd"] == "/nonexistent/gone"
PY

    # 修復先を既に identity_cwd に持つエントリがある場合: 壊れたエントリは無変更
    python3 - "$session_file" "$workspace_dir" <<'PY'
import json
import sys

session_file, workspace_dir = sys.argv[1:]
data = {
    "version": 3,
    "workspaces": [
        {"id": "w1", "identity_cwd": workspace_dir, "tabs": []},
        {
            "id": "w2",
            "identity_cwd": "/home/vscode/other",
            "tabs": [{"id": "w2:t1", "panes": {"0": {"cwd": "/nonexistent/gone"}}}],
        },
    ],
}
with open(session_file, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
    cp "$session_file" "${session_file}.before"
    run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
        HERDR_TEST_STATUS_JSON='{"running":false}'
    cmp -s "$session_file" "${session_file}.before" \
        || fail 'workspace entry must remain unchanged when repair target is taken'
    [ ! -e "${session_file}.tmp" ] \
        || fail 'taken repair target must not leave a temporary file'

    # 健全な兄弟 identity + 壊れた pane: pane は兄弟 identity へ。起動中 workspace へ流れない
    local other_dir="${workspace_root}/other-project"
    mkdir -p "$other_dir"
    python3 - "$session_file" "$workspace_dir" "$other_dir" <<'PY'
import json
import sys

session_file, workspace_dir, other_dir = sys.argv[1:]
data = {
    "version": 3,
    "workspaces": [
        {
            "id": "w-other",
            "identity_cwd": other_dir,
            "tabs": [{
                "id": "w-other:t1",
                "panes": {
                    "0": {
                        "cwd": "/home/vscode",
                        "agent_session": {"provider": "codex", "id": "keep-me"},
                    },
                },
            }],
        },
        {
            "id": "w-current",
            "identity_cwd": workspace_dir,
            "tabs": [{"id": "w-current:t1", "panes": {"0": {"cwd": workspace_dir}}}],
        },
    ],
}
with open(session_file, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
    run_session_repair "$test_home" "$workspace_root" "$workspace_dir" \
        HERDR_TEST_STATUS_JSON='{"running":false}'
    python3 - "$session_file" "$workspace_dir" "$other_dir" <<'PY'
import json
import sys

session_file, workspace_dir, other_dir = sys.argv[1:]
with open(session_file, encoding="utf-8") as handle:
    data = json.load(handle)
other, current = data["workspaces"]
assert other["identity_cwd"] == other_dir
assert other["tabs"][0]["panes"]["0"]["cwd"] == other_dir
assert other["tabs"][0]["panes"]["0"]["agent_session"] == {
    "provider": "codex",
    "id": "keep-me",
}
assert current["identity_cwd"] == workspace_dir
assert current["tabs"][0]["panes"]["0"]["cwd"] == workspace_dir
assert other["tabs"][0]["panes"]["0"]["cwd"] != workspace_dir
PY
}

test_installer_wiring() {
    local installer="${REPO_ROOT}/.devcontainer/install_beforehand.bash"
    bash -n "$installer"

    assert_before "$installer" 'https://astral\.sh/uv/install\.sh' 'https://herdr\.dev/install\.sh'
    assert_before "$installer" 'Installing Starship' 'https://herdr\.dev/install\.sh'
    assert_absent "$installer" 'bun\.com'
    assert_absent "$installer" 'headroom'
    assert_before "$installer" 'cat \.devcontainer/zshrc\.txt >>\$\{HOME\}/\.zshrc' \
        'Installing Herdr'

    assert_contains "$installer" 'if \[ ! -f "\$\{HOME\}/\.config/herdr/config\.toml" \]'
    assert_contains "$installer" 'if ! mkdir -p "\$\{HOME\}/\.config/herdr"; then'
    assert_contains "$installer" 'if ! cp \.devcontainer/herdr\.toml "\$\{HOME\}/\.config/herdr/config\.toml"; then'
    assert_contains "$installer" 'command -v herdr'
    assert_contains "$installer" 'herdr --version'

    assert_contains "$installer" 'curl -fsSL https://claude\.ai/install\.sh \| bash'
    assert_contains "$installer" 'command -v claude'
    assert_contains "$installer" 'if ! claude plugin marketplace add dashed/claude-marketplace; then'
    assert_contains "$installer" 'if ! claude plugin install "\$plugin"; then'
    assert_before "$installer" 'curl -fsSL https://claude\.ai/install\.sh \| bash' \
        'if ! claude plugin marketplace add dashed/claude-marketplace; then'

    assert_contains "$installer" 'herdr-git-status\.bash'
    assert_contains "$installer" 'herdr-status-updater\.bash'
    assert_contains "$installer" 'herdr-agent-task\.bash'
    assert_contains "$installer" 'cp \.devcontainer/herdr-agent-task\.bash "\$\{HOME\}/bin/herdr-agent-task"'

    # tmux 撤去後の再混入防止: apt 行・cp・コメントを含め全体で検査
    assert_absent "$installer" 'tmux'
}

# ccdd / ccddg / ccdu の env -u 共有リストが、親シェルで export された
# 主要な認証材料・プロバイダ切替・モデルピン留系の値を子 claude へ漏らさない
# ことを検査する。対象範囲の正本は下の expected_unsets。
# 共有配列ブロックから抽出した unset_vars は下の expected_unsets と集合比較する。
# 配列への追加・削除のどちらでも expected_unsets の更新が必要になる（下限検査では
# リストからの削除を検出できない）。配列外の env -u は比較対象にしない。
test_cc_launcher_env_unsets() {
    local test_home="${TEST_ROOT}/home-cc-launcher"
    make_stub_home "$test_home"
    local dump_dir="${TEST_ROOT}/cc-launcher-env"
    mkdir -p "$dump_dir"

    printf '%s\n' \
        '#!/bin/sh' \
        'env | sort >> "$HERDR_TEST_CLAUDE_DUMP"' \
        > "$test_home/bin/claude"
    chmod +x "$test_home/bin/claude"

    assert_contains "$ZSHRC_TEMPLATE" 'typeset -a cc_launcher_unsets'
    [ "$(rg -c -- 'env "\$\{cc_launcher_unsets\[@\]\}"' "$ZSHRC_TEMPLATE")" -ge 3 ] \
        || fail 'cc_launcher_unsets must be shared by all 3 launcher functions'
    # 撤去した ccda（claude-alibaba）を戻さない
    assert_absent "$ZSHRC_TEMPLATE" 'claude-alibaba|ccda|MAAS_ANTHROPIC_TOKEN|maas\.aliyuncs'

    local -a expected_unsets=(
        ANTHROPIC_API_KEY
        ANTHROPIC_AUTH_TOKEN
        ANTHROPIC_AWS_API_KEY
        ANTHROPIC_BETAS
        ANTHROPIC_CUSTOM_HEADERS
        ANTHROPIC_CUSTOM_MODEL_OPTION
        ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION
        ANTHROPIC_CUSTOM_MODEL_OPTION_NAME
        ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES
        ANTHROPIC_DEFAULT_MODEL
        ANTHROPIC_FOUNDRY_API_KEY
        ANTHROPIC_FOUNDRY_AUTH_TOKEN
        ANTHROPIC_IDENTITY_TOKEN
        ANTHROPIC_IDENTITY_TOKEN_FILE
        ANTHROPIC_MODEL
        ANTHROPIC_SMALL_FAST_MODEL
        ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION
        CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR
        CLAUDE_CODE_AUTO_MODE_MODEL
        CLAUDE_CODE_BG_CLASSIFIER_MODEL
        CLAUDE_CODE_CLIENT_KEY
        CLAUDE_CODE_CLIENT_KEY_PASSPHRASE
        CLAUDE_CODE_GATEWAY_TOKEN
        CLAUDE_CODE_GATEWAY_TOKEN_FILE_DESCRIPTOR
        CLAUDE_CODE_HFI_BEARER_TOKEN
        CLAUDE_CODE_MAX_CONTEXT_TOKENS
        CLAUDE_CODE_OAUTH_REFRESH_TOKEN
        CLAUDE_CODE_OAUTH_TOKEN
        CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR
        CLAUDE_CODE_SESSION_ACCESS_TOKEN
        CLAUDE_CODE_SUBAGENT_MODEL
        CLAUDE_CODE_SUBAGENT_MODEL_FORCE
        CLAUDE_CODE_USE_ANTHROPIC_AWS
        CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD
        CLAUDE_CODE_USE_BEDROCK
        CLAUDE_CODE_USE_FOUNDRY
        CLAUDE_CODE_USE_GATEWAY
        CLAUDE_CODE_USE_MANTLE
        CLAUDE_CODE_USE_VERTEX
        CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR
        COMMANDCODE_API_KEY
        DEEPINFRA_TOKEN
        OPENCODE_API_KEY
        OPENCODE_GO_API_KEY
        OPENCODE_GO_CLAUDE_API_KEY
    )
    local -a unset_vars
    mapfile -t unset_vars < <(extract_cc_launcher_unsets "$ZSHRC_TEMPLATE")
    diff <(printf '%s\n' "${expected_unsets[@]}" | sort -u) \
        <(printf '%s\n' "${unset_vars[@]}") \
        || fail 'cc_launcher_unsets must match expected_unsets exactly'

    # 配列外の無関係な env -u は共有リストの集合比較へ混ぜない。
    local unrelated_unset_fixture="${TEST_ROOT}/zshrc-unrelated-unset.txt"
    cp "$ZSHRC_TEMPLATE" "$unrelated_unset_fixture"
    printf '%s\n' 'alias unrelated-check="env -u UNRELATED_REPRO_VAR true"' \
        >> "$unrelated_unset_fixture"
    local -a fixture_unset_vars
    mapfile -t fixture_unset_vars < \
        <(extract_cc_launcher_unsets "$unrelated_unset_fixture")
    diff <(printf '%s\n' "${expected_unsets[@]}" | sort -u) \
        <(printf '%s\n' "${fixture_unset_vars[@]}") \
        || fail 'cc_launcher_unsets extraction must ignore unrelated env -u entries'

    local -a env_args=(
        DEEPINFRA_TOKEN=fake-di
        # ccdu のキー解決チェーンをテスト値で固定する。空値は :- で未設定扱いとなり、
        # 親シェルの export が残っていても OPENCODE_API_KEY=fake-open へ必ず倒れる
        OPENCODE_GO_CLAUDE_API_KEY=
        OPENCODE_API_KEY=fake-open
        OPENCODE_GO_API_KEY=
    )
    local v
    for v in "${unset_vars[@]}"; do
        case "$v" in
            DEEPINFRA_TOKEN | OPENCODE_API_KEY | \
                OPENCODE_GO_API_KEY | OPENCODE_GO_CLAUDE_API_KEY)
                continue
                ;;
        esac
        env_args+=("${v}=POLLUTED_${v}")
    done

    local fn log
    for fn in ccdd ccddg ccdu claude-deepinfra claude-deepinfra-glm claude-opencode-union; do
        log="${dump_dir}/${fn}.log"
        : > "$log"
        run_zshrc_code "$test_home" \
            "source \"\$ZSHRC_TEMPLATE\" >/dev/null 2>&1; ${fn} probe" \
            HERDR_TEST_CLAUDE_DUMP="$log" \
            "${env_args[@]}"
        assert_absent "$log" 'POLLUTED_'
    done

    # 入力元の資格情報は ANTHROPIC_* へ値を渡したあと、子 claude へ残さない。
    local source_key
    for source_key in \
        DEEPINFRA_TOKEN \
        OPENCODE_GO_CLAUDE_API_KEY \
        OPENCODE_API_KEY \
        OPENCODE_GO_API_KEY; do
        for fn in ccdd ccddg ccdu claude-deepinfra claude-deepinfra-glm claude-opencode-union; do
            assert_absent "${dump_dir}/${fn}.log" "^${source_key}="
        done
    done

    # 各関数が実際に起動し、自身の割り当て値で子プロセスを呼んだことの裏付け
    assert_contains "${dump_dir}/ccdd.log" '^ANTHROPIC_AUTH_TOKEN=fake-di$'
    assert_contains "${dump_dir}/ccddg.log" '^ANTHROPIC_AUTH_TOKEN=fake-di$'
    assert_contains "${dump_dir}/ccdu.log" '^ANTHROPIC_API_KEY=fake-open$'
    assert_contains "${dump_dir}/ccdu.log" '^CLAUDE_CODE_SUBAGENT_MODEL=union-alpha$'
    assert_contains "${dump_dir}/ccdu.log" '^CLAUDE_CODE_MAX_CONTEXT_TOKENS=262144$'
}

# 誤ったモデル・権限フラグや "$@" の分割を、子 CLI に実際に渡る値で検出する。
# 実プロバイダには接続せず、指定した環境変数だけを記録する。
make_claude_probe() {
    local test_home="$1"
    make_stub_home "$test_home"
    cat > "$test_home/bin/claude" <<'PY'
#!/usr/bin/python3
import json
import os
import sys

keys = [
    "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY",
    "ANTHROPIC_DEFAULT_FABLE_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ENABLE_CLAUDEAI_MCP_SERVERS", "CLAUDE_CODE_EFFORT_LEVEL",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "CLAUDE_CODE_MAX_CONTEXT_TOKENS",
    "CLAUDE_CODE_SUBAGENT_MODEL",
]
with open(os.environ["HERDR_TEST_CLAUDE_DUMP"], "w", encoding="utf-8") as handle:
    json.dump({"argv": sys.argv[1:], "env": {k: os.environ.get(k) for k in keys}}, handle)
sys.exit(int(os.environ.get("HERDR_TEST_CLAUDE_RC", "0")))
PY
    chmod +x "$test_home/bin/claude"
}

test_cc_launcher_arguments_and_models() {
    local test_home="${TEST_ROOT}/home-cc-arguments"
    make_claude_probe "$test_home"
    local fn log
    local probe_code='"" "two words" "line
break" "*.blend" --model sonnet'
    for fn in ccd ccdo ccds; do
        log="${test_home}/${fn}.json"
        # source の後に解析し直すことで、起動するシェルと同じ alias 展開を行う。
        run_zshrc_code "$test_home" \
            'source "$ZSHRC_TEMPLATE"; eval "$HERDR_TEST_CLAUDE_COMMAND"' \
            HERDR_TEST_CLAUDE_COMMAND="${fn} ${probe_code}" \
            HERDR_TEST_CLAUDE_DUMP="$log"
        # alias は実行したシェルから取得せず、テンプレートを独立に解析する。
        python3 - "$log" "$fn" "$ZSHRC_TEMPLATE" <<'PY'
import json
from pathlib import Path
import re
import shlex
import sys

log, name, template = sys.argv[1:]
definitions = [shlex.split(line, comments=True)
               for line in Path(template).read_text(encoding="utf-8").splitlines()
               if re.match(rf"^\s*alias\s+{re.escape(name)}=", line)]
assert len(definitions) == 1, (name, definitions)
_, definition = definitions[0]
command = shlex.split(definition.split("=", 1)[1])
assert command[0] == "claude", (name, command)
prefix = command[1:]
# モデル以外の既存の権限フラグ・引数構造は維持する。
assert prefix[:1] == ["--dangerously-skip-permissions"], (name, prefix)
if name == "ccd":
    assert len(prefix) == 1, (name, prefix)
else:
    assert len(prefix) == 3 and prefix[1] == "--model", (name, prefix)
want = prefix + ["", "two words", "line\nbreak", "*.blend", "--model", "sonnet"]
with open(log, encoding="utf-8") as handle:
    got = json.load(handle)["argv"]
assert got == want, (name, got, want)
PY
    done

    for fn in ccdd ccddg ccdu claude-deepinfra claude-deepinfra-glm claude-opencode-union; do
        log="${test_home}/${fn}.json"
        run_zshrc_code "$test_home" \
            "source \"\$ZSHRC_TEMPLATE\"; ${fn} ${probe_code}" \
            HERDR_TEST_CLAUDE_DUMP="$log" \
            DEEPINFRA_TOKEN=fake-di OPENCODE_GO_CLAUDE_API_KEY=fake-union
        python3 - "$log" "$fn" <<'PY'
import json
import sys

log, name = sys.argv[1:]
with open(log, encoding="utf-8") as handle:
    data = json.load(handle)
di = name in ("ccdd", "claude-deepinfra")
glm = name in ("ccddg", "claude-deepinfra-glm")
union = name in ("ccdu", "claude-opencode-union")
prefix = ["--model", "union-alpha" if union else "opus"]
if name in ("ccdd", "ccddg", "ccdu"):
    prefix += ["--dangerously-skip-permissions"]
assert data["argv"] == prefix + ["", "two words", "line\nbreak", "*.blend", "--model", "sonnet"], (name, data["argv"])
models = (
    ["zai-org/GLM-5.3", "deepseek-ai/DeepSeek-V4.1-Flash", "deepseek-ai/DeepSeek-V4-Flash-0731", "openai/gpt-oss-20b"] if di else
    ["deepseek-ai/DeepSeek-V4.1-Flash", "zai-org/GLM-5.3-Flash", "deepseek-ai/DeepSeek-V4-Flash-0731", "openai/gpt-oss-20b"] if glm else
    ["union-alpha"] * 4
)
env = data["env"]
for alias, model in zip(("FABLE", "OPUS", "SONNET", "HAIKU"), models):
    assert env[f"ANTHROPIC_DEFAULT_{alias}_MODEL"] == model, (name, alias, env)
assert env["ANTHROPIC_BASE_URL"] == ("https://opencode.ai/zen/go" if union else "https://api.deepinfra.com/anthropic")
assert env["ANTHROPIC_AUTH_TOKEN"] == (None if union else "fake-di")
assert env["ANTHROPIC_API_KEY"] == ("fake-union" if union else None)
assert env["ENABLE_CLAUDEAI_MCP_SERVERS"] == "false"
assert env["CLAUDE_CODE_EFFORT_LEVEL"] == "max"
assert env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == ("131072" if union else "65536")
assert env["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == ("262144" if union else None)
assert env["CLAUDE_CODE_SUBAGENT_MODEL"] == ("union-alpha" if union else None)
PY
    done
}

test_cc_launcher_auth_and_exit_status() {
    local test_home="${TEST_ROOT}/home-cc-auth"
    make_claude_probe "$test_home"
    local fn log rc mode
    local -a keys
    for fn in ccdd ccddg ccdu claude-deepinfra claude-deepinfra-glm claude-opencode-union; do
        log="${test_home}/${fn}.json"
        for mode in unset empty; do
            rm -f "$log"
            keys=(DEEPINFRA_TOKEN= OPENCODE_GO_CLAUDE_API_KEY= OPENCODE_API_KEY= OPENCODE_GO_API_KEY=)
            local unset_code=''
            if [ "$mode" = unset ]; then
                unset_code='unset DEEPINFRA_TOKEN OPENCODE_GO_CLAUDE_API_KEY OPENCODE_API_KEY OPENCODE_GO_API_KEY; '
            fi
            rc=0
            run_zshrc_code "$test_home" \
                "source \"\$ZSHRC_TEMPLATE\"; ${unset_code}${fn} probe" \
                "${keys[@]}" HERDR_TEST_CLAUDE_DUMP="$log" \
                2>"${test_home}/missing-key.log" || rc=$?
            [ "$rc" -ne 0 ] || fail "${fn}: ${mode} credentials must fail"
            [ ! -e "$log" ] || fail "${fn}: missing credentials must not call claude"
            assert_contains "${test_home}/missing-key.log" 'is not set'
        done

        rc=0
        run_zshrc_code "$test_home" \
            "source \"\$ZSHRC_TEMPLATE\"; ${fn} probe; result=\$?; [[ \$ANTHROPIC_MODEL == parent-model ]] || exit 99; [[ \$DEEPINFRA_TOKEN == fake-di ]] || exit 98; [[ \$OPENCODE_GO_CLAUDE_API_KEY == fake-union ]] || exit 97; exit \$result" \
            HERDR_TEST_CLAUDE_DUMP="$log" HERDR_TEST_CLAUDE_RC=23 \
            DEEPINFRA_TOKEN=fake-di OPENCODE_GO_CLAUDE_API_KEY=fake-union \
            ANTHROPIC_MODEL=parent-model || rc=$?
        [ "$rc" -eq 23 ] || fail "${fn}: CLI exit status and parent env (got ${rc})"
    done

    local tier
    for fn in ccdu claude-opencode-union; do
        for tier in dedicated generic go; do
            log="${test_home}/${fn}-${tier}.json"
            case "$tier" in
                dedicated) keys=(OPENCODE_GO_CLAUDE_API_KEY=fake-dedicated OPENCODE_API_KEY=fake-generic OPENCODE_GO_API_KEY=fake-go) ;;
                generic) keys=(OPENCODE_GO_CLAUDE_API_KEY= OPENCODE_API_KEY=fake-generic OPENCODE_GO_API_KEY=fake-go) ;;
                go) keys=(OPENCODE_GO_CLAUDE_API_KEY= OPENCODE_API_KEY= OPENCODE_GO_API_KEY=fake-go) ;;
            esac
            run_zshrc_code "$test_home" \
                "source \"\$ZSHRC_TEMPLATE\"; ${fn} probe" \
                HERDR_TEST_CLAUDE_DUMP="$log" "${keys[@]}"
            python3 - "$log" "$tier" <<'PY'
import json
import sys

log, tier = sys.argv[1:]
with open(log, encoding="utf-8") as handle:
    got = json.load(handle)["env"]["ANTHROPIC_API_KEY"]
assert got == {"dedicated": "fake-dedicated", "generic": "fake-generic", "go": "fake-go"}[tier]
PY
        done
    done
}

test_config_and_syntax
test_installer_wiring
test_launch_and_guards
test_session_cwd_repair
test_session_cwd_repair_multi_workspace
test_cc_launcher_env_unsets
test_cc_launcher_arguments_and_models
test_cc_launcher_auth_and_exit_status
printf 'PASS: herdr Dev Container migration\n'
