#!/bin/bash
# Dev Container の zshrc.txt（herdr のセッション cwd 修復と Claude Code のランチャー）の、
# 壊れてもエラーにならずに損害が残る守りだけを確かめる（#234）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZSHRC_TEMPLATE="${REPO_ROOT}/.devcontainer/zshrc.txt"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "${TEST_ROOT}"' EXIT

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
assert_contains() {
    rg -q -- "$2" "$1" || fail "$1 does not contain $2"
}
assert_absent() {
    ! rg -q -i -- "$2" "$1" || fail "$1 must not contain $2"
}
extract_cc_launcher_unsets() {
    sed -n '/^typeset -a cc_launcher_unsets=(/,/^)/p' "$1" \
        | rg -o -- '-u [A-Z0-9_]+' \
        | sort -u \
        | sed 's/^-u //'
}
# zshrc テンプレートを隔離環境で実行する共通部。標準出力は $2 のファイルへ書き、
# $@ で追加の VAR=value を渡せる。
run_zshrc_code_with_stdout() {
    local test_home="$1"
    local stdout_file="$2"
    local zsh_code="$3"
    shift 3
    env -u TMUX -u HERDR_ENV -u HERDR_SOCKET_PATH \
        HOME="$test_home" \
        PATH="$test_home/bin:/usr/bin:/bin" \
        HERDR_TEST_LOG="$test_home/herdr.log" \
        ZSHRC_TEMPLATE="$ZSHRC_TEMPLATE" \
        "$@" /usr/bin/zsh -f -c "$zsh_code" </dev/null >"$stdout_file"
}
# 標準出力を捨てて実行する。出力を検査しない呼び出しはこちらを使う。
run_zshrc_code() {
    local test_home="$1"
    local zsh_code="$2"
    shift 2
    run_zshrc_code_with_stdout "$test_home" /dev/null "$zsh_code" "$@"
}
# herdr（status server だけ応答する）と starship のスタブを用意する。
make_stub_home() {
    local dir="$1"
    mkdir -p "$dir/bin"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$dir/bin/starship"
    printf '%s\n' '#!/bin/sh' \
        'if [ "${1:-} ${2:-} ${3:-}" = "status server --json" ]; then' \
        '    printf "%s\n" "${HERDR_TEST_STATUS_JSON:-{\"running\":false\}}"' \
        '    exit "${HERDR_TEST_STATUS_RC:-0}"' \
        'fi' \
        > "$dir/bin/herdr"
    chmod +x "$dir/bin/starship" "$dir/bin/herdr"
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


# herdr_repair_session_cwd は、利用者の herdr セッション記録（session.json）を直接書き換える。
# 守るのは、修復が壊れてもエラーにならず、復元先やエージェントの再開情報が気付かないまま変わる損害。
test_session_cwd_repair() {
    local test_home="${TEST_ROOT}/home-repair"
    local workspace_root="${TEST_ROOT}/workspaces"
    local workspace_dir="${workspace_root}/reso-world"
    local worktree_dir="${workspace_dir}/.worktrees/feature"
    local session_file="${test_home}/.config/herdr/session.json"
    make_stub_home "$test_home"

    # 壊れた cwd だけを直し、worktree 配下・agent_session・未知のフィールドを保つ
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

    # 次の場合は session.json を変えない: サーバー稼働中（保存と競合する）、未知の version、
    # 修復先が無い、サーバー状態が判定できない（`running` が 0）、修復先がワークスペースルート自身
    local case_name
    for case_name in running unknown_version missing_destination numeric_zero workspace_root; do
        write_session_fixture "$session_file" "$workspace_root" "$workspace_dir" "$worktree_dir"
        local status_json='{"running":false}' destination="$workspace_dir"
        case "$case_name" in
            running) status_json='{"running":true}' ;;
            numeric_zero) status_json='{"running":0}' ;;
            missing_destination) destination="${workspace_root}/no-such-dir" ;;
            workspace_root) destination="$workspace_root" ;;
            unknown_version)
                python3 - "$session_file" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
data["version"] = 4
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
                ;;
        esac
        cp "$session_file" "${session_file}.before"
        run_session_repair "$test_home" "$workspace_root" "$destination" HERDR_TEST_STATUS_JSON="$status_json"
        cmp -s "$session_file" "${session_file}.before" || fail "${case_name} must leave session unchanged"
        [ ! -e "${session_file}.tmp" ] || fail "${case_name} must not leave a temporary file"
    done
}

# 複数の workspace が同じ identity に収束したり、pane が別の workspace へ流れたりすると、
# セッションの復元先が気付かないまま取り違えられる。
test_session_cwd_repair_multi_workspace() {
    local test_home="${TEST_ROOT}/home-repair-multi"
    local workspace_root="${TEST_ROOT}/workspaces-multi"
    local workspace_dir="${workspace_root}/reso-world"
    local other_dir="${workspace_root}/other-project"
    local session_file="${test_home}/.config/herdr/session.json"
    make_stub_home "$test_home"
    mkdir -p "$(dirname "$session_file")" "$workspace_dir" "$other_dir"

    # 修復先をまだ誰も持たない: 先頭の壊れたエントリだけを直し、2 件目は触らない
    python3 - "$session_file" <<'PY'
import json
import sys

data = {"version": 3, "workspaces": [
    {"id": "w1", "identity_cwd": "/home/vscode",
     "tabs": [{"id": "w1:t1", "panes": {"0": {"cwd": "/home/vscode"}}}]},
    {"id": "w2", "identity_cwd": "/home/vscode/other",
     "tabs": [{"id": "w2:t1", "panes": {"0": {"cwd": "/nonexistent/gone"}}}]},
]}
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
    run_session_repair "$test_home" "$workspace_root" "$workspace_dir" HERDR_TEST_STATUS_JSON='{"running":false}'
    python3 - "$session_file" "$workspace_dir" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    w1, w2 = json.load(handle)["workspaces"]
assert w1["identity_cwd"] == sys.argv[2]
assert w1["tabs"][0]["panes"]["0"]["cwd"] == sys.argv[2]
assert w2["identity_cwd"] == "/home/vscode/other"
assert w2["tabs"][0]["panes"]["0"]["cwd"] == "/nonexistent/gone"
PY

    # 修復先を既に identity_cwd に持つエントリがある: 壊れたエントリは無変更
    python3 - "$session_file" "$workspace_dir" <<'PY'
import json
import sys

data = {"version": 3, "workspaces": [
    {"id": "w1", "identity_cwd": sys.argv[2], "tabs": []},
    {"id": "w2", "identity_cwd": "/home/vscode/other",
     "tabs": [{"id": "w2:t1", "panes": {"0": {"cwd": "/nonexistent/gone"}}}]},
]}
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
    cp "$session_file" "${session_file}.before"
    run_session_repair "$test_home" "$workspace_root" "$workspace_dir" HERDR_TEST_STATUS_JSON='{"running":false}'
    cmp -s "$session_file" "${session_file}.before" \
        || fail 'workspace entry must remain unchanged when repair target is taken'

    # 健全な兄弟 identity の壊れた pane は兄弟へ戻す。起動中の workspace へ流さない
    python3 - "$session_file" "$workspace_dir" "$other_dir" <<'PY'
import json
import sys

session_file, workspace_dir, other_dir = sys.argv[1:]
data = {"version": 3, "workspaces": [
    {"id": "w-other", "identity_cwd": other_dir, "tabs": [{"id": "w-other:t1", "panes": {
        "0": {"cwd": "/home/vscode", "agent_session": {"provider": "codex", "id": "keep-me"}}}}]},
    {"id": "w-current", "identity_cwd": workspace_dir,
     "tabs": [{"id": "w-current:t1", "panes": {"0": {"cwd": workspace_dir}}}]},
]}
with open(session_file, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
    run_session_repair "$test_home" "$workspace_root" "$workspace_dir" HERDR_TEST_STATUS_JSON='{"running":false}'
    python3 - "$session_file" "$workspace_dir" "$other_dir" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    other, current = json.load(handle)["workspaces"]
assert other["tabs"][0]["panes"]["0"]["cwd"] == sys.argv[3]
assert other["tabs"][0]["panes"]["0"]["agent_session"] == {"provider": "codex", "id": "keep-me"}
assert current["tabs"][0]["panes"]["0"]["cwd"] == sys.argv[2]
PY
}

# F∩S: ccdd / ccddg / ccdgo / ccdol / ccda の env -u 共有リストが、親シェルで export された認証材料・プロバイダ切替・
# モデルのピン留めの値を子 claude へ漏らさない。漏れても子は動くので、気付かないまま別の資格情報で
# 動いたり、資格情報が他のプロバイダへ渡ったりする。unset の一覧は expected_unsets が基準で、
# 配列の追加・削除のどちらでも更新が要る（配列外の env -u は比較しない）。
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
        MAAS_ANTHROPIC_TOKEN
        OLLAMA_API_KEY
        OPENCODE_API_KEY
        OPENCODE_GO_API_KEY
        OPENCODE_GO_CLAUDE_API_KEY
    )
    local -a unset_vars
    mapfile -t unset_vars < <(extract_cc_launcher_unsets "$ZSHRC_TEMPLATE")
    diff <(printf '%s\n' "${expected_unsets[@]}" | sort -u) \
        <(printf '%s\n' "${unset_vars[@]}") \
        || fail 'cc_launcher_unsets must match expected_unsets exactly'

    local -a env_args=(
        DEEPINFRA_TOKEN=fake-di
        MAAS_ANTHROPIC_TOKEN=fake-maas
        OLLAMA_API_KEY=fake-ollama
        # ccdgo のキー解決チェーンをテスト値で固定する。3 つを別の値にして、
        # 親シェルの export が残っていても最初の非空値 OPENCODE_GO_CLAUDE_API_KEY が選ばれることを確かめる
        OPENCODE_GO_CLAUDE_API_KEY=fake-go-claude
        OPENCODE_API_KEY=fake-open
        OPENCODE_GO_API_KEY=fake-go
    )
    local v
    for v in "${unset_vars[@]}"; do
        case "$v" in
            DEEPINFRA_TOKEN | MAAS_ANTHROPIC_TOKEN | OLLAMA_API_KEY | OPENCODE_API_KEY | \
                OPENCODE_GO_API_KEY | OPENCODE_GO_CLAUDE_API_KEY)
                continue
                ;;
        esac
        env_args+=("${v}=POLLUTED_${v}")
    done

    local fn log
    for fn in ccdd ccddg ccdgo ccdol ccda; do
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
        MAAS_ANTHROPIC_TOKEN \
        OLLAMA_API_KEY \
        OPENCODE_GO_CLAUDE_API_KEY \
        OPENCODE_API_KEY \
        OPENCODE_GO_API_KEY; do
        for fn in ccdd ccddg ccdgo ccdol ccda; do
            assert_absent "${dump_dir}/${fn}.log" "^${source_key}="
        done
    done

    # 各関数が実際に起動し、自身の割り当て値で子プロセスを呼んだことの裏付け
    assert_contains "${dump_dir}/ccdd.log" '^ANTHROPIC_AUTH_TOKEN=fake-di$'
    assert_contains "${dump_dir}/ccddg.log" '^ANTHROPIC_AUTH_TOKEN=fake-di$'
    assert_contains "${dump_dir}/ccdgo.log" '^ANTHROPIC_API_KEY=fake-go-claude$'
    assert_contains "${dump_dir}/ccdgo.log" '^ANTHROPIC_AUTH_TOKEN=fake-go-claude$'
    assert_contains "${dump_dir}/ccdol.log" '^ANTHROPIC_AUTH_TOKEN=fake-ollama$'
    assert_contains "${dump_dir}/ccda.log" '^ANTHROPIC_AUTH_TOKEN=fake-maas$'
}


# F∩S: 資格情報の送り先（ANTHROPIC_BASE_URL）と claude.ai の MCP 接続を他社のモデルへ渡さない設定。
# 送り先を変えても動くが、DEEPINFRA_TOKEN・OLLAMA_API_KEY などを別のホストへ送り、MCP を有効にすると利用者の接続先のデータを渡す。
# 実プロバイダには接続せず、子 CLI に実際に渡る値だけを記録する。
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
    "ENABLE_CLAUDEAI_MCP_SERVERS",
]
with open(os.environ["HERDR_TEST_CLAUDE_DUMP"], "w", encoding="utf-8") as handle:
    json.dump({"argv": sys.argv[1:], "env": {k: os.environ.get(k) for k in keys}}, handle)
sys.exit(int(os.environ.get("HERDR_TEST_CLAUDE_RC", "0")))
PY
    chmod +x "$test_home/bin/claude"
}

# F∩S: 権限確認を省く --dangerously-skip-permissions は短縮名（ccdd / ccddg / ccdgo / ccdol / ccda）だけに付ける。
# 通常名に付いても動くので、了承の無いまま権限確認が外れる。
test_cc_launcher_destination_and_exit_status() {
    local test_home="${TEST_ROOT}/home-cc-destination"
    make_claude_probe "$test_home"
    local fn log rc
    for fn in ccdd ccddg ccdgo ccdol ccda claude-deepinfra claude-deepinfra-glm claude-opencode-go claude-ollama claude-alibaba; do
        log="${test_home}/${fn}.json"
        run_zshrc_code "$test_home" "source \"\$ZSHRC_TEMPLATE\"; ${fn} probe" \
            HERDR_TEST_CLAUDE_DUMP="$log" DEEPINFRA_TOKEN=fake-di MAAS_ANTHROPIC_TOKEN=fake-maas OPENCODE_GO_CLAUDE_API_KEY=fake-go OLLAMA_API_KEY=fake-ollama
        python3 - "$log" "$fn" <<'PY'
import json
import sys

log, name = sys.argv[1:]
with open(log, encoding="utf-8") as handle:
    data = json.load(handle)
argv, env = data["argv"], data["env"]
# 利用者の引数より前の、ランチャーが付ける部分にだけ省略のフラグが入る（モデル名などは照合しない）
assert argv[-1] == "probe", (name, argv)
skip = "--dangerously-skip-permissions"
if name in ("ccdd", "ccddg", "ccdgo", "ccdol", "ccda"):
    assert skip in argv[:-1], (name, argv)
else:
    assert skip not in argv, (name, argv)
opencode_go = name in ("ccdgo", "claude-opencode-go")
ollama = name in ("ccdol", "claude-ollama")
alibaba = name in ("ccda", "claude-alibaba")
if ollama:
    assert env["ANTHROPIC_BASE_URL"] == "https://ollama.com", (name, env)
    assert env["ANTHROPIC_AUTH_TOKEN"] == "fake-ollama", (name, env)
    assert env["ANTHROPIC_API_KEY"] is None, (name, env)
elif alibaba:
    assert env["ANTHROPIC_BASE_URL"] == "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic", (name, env)
    assert env["ANTHROPIC_AUTH_TOKEN"] == "fake-maas", (name, env)
    assert env["ANTHROPIC_API_KEY"] is None, (name, env)
elif opencode_go:
    assert env["ANTHROPIC_BASE_URL"] == "https://opencode.ai/zen/go", (name, env)
    assert env["ANTHROPIC_AUTH_TOKEN"] == "fake-go", (name, env)
    assert env["ANTHROPIC_API_KEY"] == "fake-go", (name, env)
else:
    assert env["ANTHROPIC_BASE_URL"] == "https://api.deepinfra.com/anthropic", (name, env)
    assert env["ANTHROPIC_AUTH_TOKEN"] == "fake-di", (name, env)
    assert env["ANTHROPIC_API_KEY"] is None, (name, env)
assert env["ENABLE_CLAUDEAI_MCP_SERVERS"] == "false", (name, env)
PY
    done

    # 子の終了コードを返し、親シェルの変数を消さない（迷い: 対話ランチャーの影響は小さい）
    rc=0
    run_zshrc_code "$test_home" \
        "source \"\$ZSHRC_TEMPLATE\"; ccdd probe; result=\$?; [[ \$ANTHROPIC_MODEL == parent-model ]] || exit 99; [[ \$DEEPINFRA_TOKEN == fake-di ]] || exit 98; exit \$result" \
        HERDR_TEST_CLAUDE_DUMP="${test_home}/exit.json" HERDR_TEST_CLAUDE_RC=23 \
        DEEPINFRA_TOKEN=fake-di ANTHROPIC_MODEL=parent-model || rc=$?
    [ "$rc" -eq 23 ] || fail "CLI exit status and parent env (got ${rc})"
}

# S: ccdol は OLLAMA_API_KEY が無いとき、子 claude を起動せずに失敗する。
# Claude Code は ANTHROPIC_AUTH_TOKEN が空か空白だけだと、保存済みの claude.ai の OAuth トークンを
# 接続先へ送る。このガードが外れても起動は成功し、claude.ai の認証情報が ollama.com に送られる。
# 入力は ASCII の空白・NBSP（U+00A0）・BOM（U+FEFF）だけの 1 件にする。Claude Code は trim で
# これらを除いて空とみなす。空だけを止める書き方（[[ -z ... ]]）も、空白（[[:space:]]）だけを除く書き方も
# NBSP・BOM を通すので、この 1 件でどちらの誤りも分かる。正しい key で起動する例は送り先のテストにある。
test_ollama_launcher_requires_key() {
    local test_home="${TEST_ROOT}/home-ollama-key"
    make_stub_home "$test_home"
    local log="${TEST_ROOT}/ollama-key-claude.log"
    : > "$log"
    printf '%s\n' '#!/bin/sh' 'echo started >> "$HERDR_TEST_CLAUDE_DUMP"' > "$test_home/bin/claude"
    chmod +x "$test_home/bin/claude"

    local rc=0
    run_zshrc_code "$test_home" \
        'source "$ZSHRC_TEMPLATE" >/dev/null 2>&1; ccdol probe' \
        HERDR_TEST_CLAUDE_DUMP="$log" OLLAMA_API_KEY=$' \xc2\xa0\xef\xbb\xbf' 2>/dev/null || rc=$?
    [ "$rc" -ne 0 ] || fail 'ccdol must fail when OLLAMA_API_KEY is blank'
    [ ! -s "$log" ] || fail 'ccdol must not start claude when OLLAMA_API_KEY is blank'
}

# S: ccda は MAAS_ANTHROPIC_TOKEN が未設定・空、または ASCII 英数字を 1 文字も含まないとき、
# 子 claude を起動せずに失敗する。Claude Code は ANTHROPIC_AUTH_TOKEN が空か空白だけだと、
# 保存済みの claude.ai の OAuth トークンを接続先へ送る。このガードが外れても起動は成功し、
# claude.ai の認証情報が maas.aliyuncs.com に送られる。未設定・空の拒否は同じ判定
# （${MAAS_ANTHROPIC_TOKEN:-} と *[A-Za-z0-9]*）が担うので、入力は ASCII の空白・NBSP（U+00A0）・
# BOM（U+FEFF）だけの 1 件にする。空だけを止める書き方（[[ -z ... ]]）も、空白（[[:space:]]）だけを
# 除く書き方も NBSP・BOM を通すので、この 1 件でどちらの誤りも分かる。
# 正しいキーで起動する例は送り先のテストにある。
test_alibaba_launcher_requires_key() {
    local test_home="${TEST_ROOT}/home-alibaba-key"
    make_stub_home "$test_home"
    local log="${TEST_ROOT}/alibaba-key-claude.log"
    : > "$log"
    printf '%s\n' '#!/bin/sh' 'echo started >> "$HERDR_TEST_CLAUDE_DUMP"' > "$test_home/bin/claude"
    chmod +x "$test_home/bin/claude"

    local rc=0
    run_zshrc_code "$test_home" \
        'source "$ZSHRC_TEMPLATE" >/dev/null 2>&1; ccda probe' \
        HERDR_TEST_CLAUDE_DUMP="$log" MAAS_ANTHROPIC_TOKEN=$' \xc2\xa0\xef\xbb\xbf' 2>/dev/null || rc=$?
    [ "$rc" -ne 0 ] || fail 'ccda must fail when MAAS_ANTHROPIC_TOKEN is blank'
    [ ! -s "$log" ] || fail 'ccda must not start claude when MAAS_ANTHROPIC_TOKEN is blank'
}

# S: claude-alibaba-exec は MAAS_ANTHROPIC_TOKEN が ASCII の英数字を 1 文字も含まないとき、子 claude を起動せずに失敗する。
# ガードが外れても起動は成功し、claude.ai の認証情報が maas.aliyuncs.com に送られる。
# ANTHROPIC_API_KEY が残ると承認まで OAuth が送られうる。正しい key でも、親の ANTHROPIC_API_KEY・
# CLAUDE_CODE_OAUTH_TOKEN・MAAS_ANTHROPIC_TOKEN を子に残すと、起動は成功したまま claude.ai の認証情報が
# maas.aliyuncs.com に送られる。空白だけの拒否と、英数字を含む key で stub が起動する例を同じ関数で確かめる。
# env -i で locale（LANG・LC_*）を渡さない。runner の子はそれらを引き継がない。範囲の比較が locale に依ると、
# このテストの locale では止まり、locale の無い起動では通る（またはその逆）ことがある。
test_alibaba_exec_requires_key() {
    local test_home="${TEST_ROOT}/home-alibaba-exec-key"
    make_stub_home "$test_home"
    mkdir -p "$test_home/.local/bin"
    install -m 0755 "${REPO_ROOT}/.devcontainer/claude-alibaba-exec" "$test_home/.local/bin/claude-alibaba-exec"
    local log="${TEST_ROOT}/alibaba-exec-key-claude.log"
    : > "$log"
    printf '%s\n' '#!/bin/sh' 'env > "$HERDR_TEST_CLAUDE_DUMP"' > "$test_home/bin/claude"
    chmod +x "$test_home/bin/claude"

    local rc=0
    env -i HOME="$test_home" PATH="$test_home/.local/bin:$test_home/bin:/usr/bin:/bin" \
        HERDR_TEST_CLAUDE_DUMP="$log" \
        MAAS_ANTHROPIC_TOKEN=$' \xc2\xa0\xef\xbb\xbf\xe3\x80\x80' \
        "$test_home/.local/bin/claude-alibaba-exec" probe || rc=$?
    [ "$rc" -ne 0 ] || fail 'claude-alibaba-exec must fail when MAAS_ANTHROPIC_TOKEN has no letters or digits'
    [ ! -s "$log" ] || fail 'claude-alibaba-exec must not start claude when MAAS_ANTHROPIC_TOKEN has no letters or digits'

    : > "$log"
    rc=0
    env -i HOME="$test_home" PATH="$test_home/.local/bin:$test_home/bin:/usr/bin:/bin" \
        HERDR_TEST_CLAUDE_DUMP="$log" \
        ANTHROPIC_API_KEY=fake-anthropic \
        CLAUDE_CODE_OAUTH_TOKEN=fake-oauth \
        MAAS_ANTHROPIC_TOKEN=fake-maas \
        "$test_home/.local/bin/claude-alibaba-exec" probe || rc=$?
    [ "$rc" -eq 0 ] || fail 'claude-alibaba-exec must start claude when MAAS_ANTHROPIC_TOKEN has letters or digits'
    assert_contains "$log" '^ANTHROPIC_AUTH_TOKEN=fake-maas$'
    assert_contains "$log" '^ANTHROPIC_BASE_URL=https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic$'
    assert_absent "$log" '^ANTHROPIC_API_KEY='
    assert_absent "$log" '^CLAUDE_CODE_OAUTH_TOKEN='
    assert_absent "$log" '^MAAS_ANTHROPIC_TOKEN='
}

# S: ccdgo は空白だけの優先キーを、有効な下位キーへ黙って読み替えず、子 claude を起動せずに失敗する。
# 読み替えると、利用者が優先キーで使うつもりのアカウントとは別のキーで外部へ要求を送る。さらに
# Claude Code は両方の認証変数を trim（Unicode の空白も除く）して空とみなすため、空白だけでも
# 起動してしまえば保存済みの claude.ai の OAuth トークンを opencode.ai へ送る。優先キーには
# ASCII の空白・NBSP（U+00A0）・BOM（U+FEFF）だけを置き、下位の OPENCODE_API_KEY には有効な
# 偽値を置く。下位へ切り替える実装も、空白を通す実装も、この 1 件で止まる。
# 正しいキーで起動する例は送り先と env 隔離のテストにある。
test_opencode_go_launcher_requires_key() {
    local test_home="${TEST_ROOT}/home-opencode-go-key"
    make_stub_home "$test_home"
    local log="${TEST_ROOT}/opencode-go-key-claude.log"
    : > "$log"
    printf '%s\n' '#!/bin/sh' 'echo started >> "$HERDR_TEST_CLAUDE_DUMP"' > "$test_home/bin/claude"
    chmod +x "$test_home/bin/claude"

    local rc=0
    run_zshrc_code "$test_home" \
        'source "$ZSHRC_TEMPLATE" >/dev/null 2>&1; ccdgo probe' \
        HERDR_TEST_CLAUDE_DUMP="$log" \
        OPENCODE_GO_CLAUDE_API_KEY=$' \xc2\xa0\xef\xbb\xbf' \
        OPENCODE_API_KEY=fake-valid-lower 2>/dev/null || rc=$?
    [ "$rc" -ne 0 ] || fail 'ccdgo must fail when the first non-empty key is blank'
    [ ! -s "$log" ] || fail 'ccdgo must not start claude when the first non-empty key is blank'
}

# S: ccdd / ccddg は DEEPINFRA_TOKEN が未設定・空、または ASCII 英数字を 1 文字も含まないとき、
# 子 claude を起動せずに失敗する。Claude Code は ANTHROPIC_AUTH_TOKEN が空か空白だけだと、
# 保存済みの claude.ai の OAuth トークンを接続先へ送る。このガードが外れても起動は成功し、
# claude.ai の認証情報が DeepInfra に送られる。未設定・空の拒否は同じ判定（${DEEPINFRA_TOKEN:-} と
# *[A-Za-z0-9]*）が担うので、入力は ASCII の空白・NBSP（U+00A0）・BOM（U+FEFF）だけの 1 件にする。
# 空だけを止める書き方（[[ -z ... ]]）も、空白（[[:space:]]）だけを除く書き方も NBSP・BOM を通すので、
# この 1 件でどちらの誤りも分かる。通常名は同じ関数本体なので短縮名で代表させ、
# 正しいキーで起動する例は送り先と env 隔離のテストにある。
test_deepinfra_launcher_requires_key() {
    local test_home="${TEST_ROOT}/home-deepinfra-key"
    make_stub_home "$test_home"
    local log="${TEST_ROOT}/deepinfra-key-claude.log"
    : > "$log"
    printf '%s\n' '#!/bin/sh' 'echo started >> "$HERDR_TEST_CLAUDE_DUMP"' > "$test_home/bin/claude"
    chmod +x "$test_home/bin/claude"

    local fn out err rc
    for fn in ccdd ccddg; do
        out="${TEST_ROOT}/deepinfra-key-${fn}.out"
        err="${TEST_ROOT}/deepinfra-key-${fn}.err"
        rc=0
        run_zshrc_code_with_stdout "$test_home" "$out" \
            "source \"\$ZSHRC_TEMPLATE\" >/dev/null 2>&1; ${fn} probe" \
            HERDR_TEST_CLAUDE_DUMP="$log" DEEPINFRA_TOKEN=$' \xc2\xa0\xef\xbb\xbf' 2>"$err" || rc=$?
        [ "$rc" -ne 0 ] || fail "${fn} must fail when DEEPINFRA_TOKEN has no letters or digits"
        [ ! -s "$log" ] || fail "${fn} must not start claude when DEEPINFRA_TOKEN has no letters or digits"
        # 失敗は固定文で知らせ、入力した値をそのまま出さない（端末・ログへの漏えいを避ける）。
        # 出力先が stderr から stdout へ変わっても値が漏れないよう、両方を検査する。
        [ -s "$err" ] || fail "${fn} must report an error without the token value"
        assert_absent "$err" $'\xc2\xa0'
        assert_absent "$err" $'\xef\xbb\xbf'
        assert_absent "$out" $'\xc2\xa0'
        assert_absent "$out" $'\xef\xbb\xbf'
    done
}

test_session_cwd_repair
test_session_cwd_repair_multi_workspace
test_cc_launcher_env_unsets
test_cc_launcher_destination_and_exit_status
test_ollama_launcher_requires_key
test_opencode_go_launcher_requires_key
test_deepinfra_launcher_requires_key
test_alibaba_launcher_requires_key
test_alibaba_exec_requires_key
printf 'PASS: herdr Dev Container migration\n'
