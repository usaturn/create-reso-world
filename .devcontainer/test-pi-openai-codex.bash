#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "${TEST_ROOT}"' EXIT
unset PI_CODING_AGENT_DIR
cd "$REPO_ROOT"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
assert_eq() {
    [ "$1" = "$2" ] || fail "$3: expected='$2' actual='$1'"
}
setup_for_home() {
    local output
    output="$(env HOME="$1" zsh "${REPO_ROOT}/.devcontainer/setup_pi_superagents.zsh" 2>&1)" \
        || fail "pi-superagents setup failed: ${output}"
}

test_setup_places_independent_gpt6_tiers() {
    local home="${TEST_ROOT}/setup" launcher tier model thinking config row
    local -a expected_tiers=(
        "piga:cheap:gpt-6-luna:xhigh"
        "piga:balanced:gpt-6.1-sol:xhigh"
        "piga:max:gpt-6-astra:max"
        "pigs:balanced:gpt-6.1-sol:xhigh"
        "pigs:max:gpt-6.1-sol:max"
        "pigl:cheap:gpt-6-luna:xhigh"
        "pigl:balanced:gpt-6.1-sol:xhigh"
        "pigl:max:gpt-6.1-sol:xhigh"
    )
    mkdir -p "$home"
    setup_for_home "$home"

    for row in "${expected_tiers[@]}"; do
        IFS=: read -r launcher tier model thinking <<< "$row"
        config="${home}/.pi/agent/extensions/subagent.d/${launcher}/config.json"
        [ -f "$config" ] || fail "setup did not place ${launcher} config"
        python3 - "$config" "$tier" "openai-codex/${model}" "$thinking" <<'PY' \
            || fail "${launcher}.${tier} must use ${model} at ${thinking} thinking"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    tier = json.load(source)["superagents"]["modelTiers"][sys.argv[2]]
assert tier == {"model": sys.argv[3], "thinking": sys.argv[4]}
PY
    done
}

test_launchers_select_models_and_forward_arguments() {
    local home="${TEST_ROOT}/launch" launcher model output args expected
    mkdir -p "${home}/.pi/agent"
    printf '%s\n' '{"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
        > "${home}/.pi/agent/auth.json"
    setup_for_home "$home"

    for launcher in piga pigs pigl; do
        case "$launcher" in
            piga) model=gpt-6-astra ;;
            pigs) model=gpt-6.1-sol ;;
            pigl) model=gpt-6-luna ;;
        esac
        [ -x "${REPO_ROOT}/.devcontainer/${launcher}" ] || fail "${launcher} must be executable"
        output="$(env HOME="$home" PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
            zsh "${REPO_ROOT}/.devcontainer/${launcher}" --resume)"
        args="$(printf '%s\n' "$output" | awk 'seen { print } $0 == "pi" { seen = 1 }')"
        expected="$(printf '%s\n' --tui-mode regular --provider openai-codex --model "$model" --thinking xhigh --resume)"
        assert_eq "$args" "$expected" "${launcher} Pi arguments"
        # grep -q は一致した時点で終了するので、printf でパイプすると残りの行を書く側が SIGPIPE で落ちる
        grep -Fxq "${home}/.pi/agent/extensions/subagent.d/${launcher}" <<<"$output" \
            || fail "${launcher} must use its own tier config"
    done
}

test_launchers_accept_tilde_agent_dir() {
    local home="${TEST_ROOT}/tilde-auth" launcher model agent_dir output args expected
    mkdir -p "${home}/.pi/agent"
    printf '%s\n' '{"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
        > "${home}/.pi/agent/auth.json"
    printf '%s\n' '{"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
        > "${home}/auth.json"
    setup_for_home "$home"

    for launcher in piga pigs pigl; do
        case "$launcher" in
            piga) model=gpt-6-astra ;;
            pigs) model=gpt-6.1-sol ;;
            pigl) model=gpt-6-luna ;;
        esac
        expected="$(printf '%s\n' --tui-mode regular --provider openai-codex --model "$model" --thinking xhigh --resume)"
        for agent_dir in "${home}/.pi/agent" '~/.pi/agent' '~'; do
            output="$(env HOME="$home" PI_CODING_AGENT_DIR="$agent_dir" \
                PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
                zsh "${REPO_ROOT}/.devcontainer/${launcher}" --resume 2>&1)" \
                || fail "${launcher} rejected ${agent_dir}: ${output}"
            args="$(printf '%s\n' "$output" | awk 'seen { print } $0 == "pi" { seen = 1 }')"
            assert_eq "$args" "$expected" "${launcher} Pi arguments with ${agent_dir}"
        done
    done
}

test_missing_oauth_guides_login_without_requesting_api_key() {
    local home="${TEST_ROOT}/no-oauth" launcher output status
    mkdir -p "$home"
    setup_for_home "$home"

    for launcher in piga pigs pigl; do
        set +e
        output="$(env HOME="$home" PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
            zsh "${REPO_ROOT}/.devcontainer/${launcher}" 2>&1)"
        status=$?
        set -e
        assert_eq "$status" "1" "${launcher} must stop without OAuth"
        grep -Fq '/login openai-codex' <<<"$output" \
            || fail "${launcher} must explain direct Codex OAuth login"
        case "$output" in
            *'ChatGPT Plus/Pro (Codex)'*) fail "${launcher} must not name a nonexistent login choice" ;;
            *OPENAI_API_KEY*) fail "${launcher} must not request OPENAI_API_KEY" ;;
        esac
    done
}

test_install_places_all_launchers_with_regular_mode() {
    local home="${TEST_ROOT}/install" launcher output
    local -a args
    mkdir -p "${home}/.pi/agent"
    printf '%s\n' '{"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999},"xai":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
        > "${home}/.pi/agent/auth.json"
    cp "${REPO_ROOT}/.devcontainer/pi-models.json" "${home}/.pi/agent/models.json"
    # ランチャーの配置と、ヘルパを置く pi-superagents の手順だけを切り出す。
    # 終わりは「この 2 つ以外の次の step」にし、後続の手順の並びに依存しない。
    {
        printf '%s\n' 'step() { :; }' 'fail() { printf "%s\n" "$1" >&2; exit 1; }'
        awk '/^step "Placing the launchers / { copy = 1 }
            /^step "/ && !/^step "(Placing the launchers |Writing the pi-superagents )/ { copy = 0 }
            copy' "${REPO_ROOT}/.devcontainer/install_beforehand.bash"
    } | env HOME="$home" bash -e
    cmp -s "${REPO_ROOT}/.devcontainer/pi-superagents-exec.zsh" "${home}/.local/bin/pi-superagents-exec.zsh" \
        || fail "install must place the current helper"

    for launcher in pigo pigod pigou piccg piccd piga pigs pigl pixg; do
        [ -x "${home}/.local/bin/${launcher}" ] || fail "install did not place executable ${launcher}"
        cmp -s "${REPO_ROOT}/.devcontainer/${launcher}" "${home}/.local/bin/${launcher}" \
            || fail "installed ${launcher} differs from the source"
        output="$(env HOME="$home" PI_CODING_AGENT_DIR="${home}/.pi/agent" \
            COMMANDCODE_API_KEY=dummy-for-dry-run OPENCODE_API_KEY=dummy-for-dry-run \
            PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
            zsh "${home}/.local/bin/${launcher}" --resume)"
        mapfile -t args < <(awk 'seen { print } $0 == "pi" { seen = 1 }' <<<"$output")
        assert_eq "${args[0]:-}" --tui-mode "installed ${launcher} tui option"
        assert_eq "${args[1]:-}" regular "installed ${launcher} tui mode"
        assert_eq "${args[${#args[@]}-1]}" --resume "installed ${launcher} user argument"
    done
}

test_live_openai_codex_models() {
    [ "${PI_CODEX_LIVE_CHECK:-0}" = 1 ] || return 0

    local version model output
    version="$(pi --version)" || fail "pi --version failed"
    dpkg --compare-versions "$version" ge 0.87.1 \
        || fail "Pi 0.87.1 or newer is required (installed: ${version})"

    for model in gpt-6-astra gpt-6.1-sol gpt-6-luna; do
        output="$(pi --list-models "$model")" || fail "pi --list-models ${model} failed"
        printf '%s\n' "$output" | awk -v model="$model" \
            '$1 == "openai-codex" && $2 == model { found = 1 } END { exit !found }' \
            || fail "openai-codex/${model} is unavailable; log in with /login or update Pi"
    done
}

test_setup_places_independent_gpt6_tiers
test_launchers_select_models_and_forward_arguments
test_launchers_accept_tilde_agent_dir
test_missing_oauth_guides_login_without_requesting_api_key
test_install_places_all_launchers_with_regular_mode
test_live_openai_codex_models
printf 'OK test-pi-openai-codex\n'
