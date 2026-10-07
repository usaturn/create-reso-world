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

# 静的な期待値の読み取りを共有する。専用モードはスイートを実行しない。
launcher_pi_args_from_source() {
    bash "${REPO_ROOT}/.devcontainer/test-pi-superagents.bash" \
        --launcher-pi-args-from-source "$1"
}

test_launchers_accept_tilde_agent_dir() {
    local home="${TEST_ROOT}/tilde-auth" launcher agent_dir output args prefix expected
    mkdir -p "${home}/.pi/agent"
    printf '%s\n' '{"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
        > "${home}/.pi/agent/auth.json"
    printf '%s\n' '{"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
        > "${home}/auth.json"
    setup_for_home "$home"

    for launcher in piga pigs pigl; do
        prefix="$(launcher_pi_args_from_source "$launcher")" \
            || fail "cannot read ${launcher} source arguments"
        expected="$(printf '%s\n' "$prefix" --resume)"
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

test_missing_oauth_guides_login() {
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
    done
}

test_install_places_all_launchers_with_regular_mode() {
    local home="${TEST_ROOT}/install" launcher output args prefix expected
    local -a launchers
    # ランチャーは定義元の .devcontainer/pi-superagents/<launcher>.json から列挙し、一覧をテストへ写さない
    mapfile -t launchers < <(find "${REPO_ROOT}/.devcontainer/pi-superagents" -maxdepth 1 -name '*.json' -printf '%f\n' \
        | sed 's/\.json$//' | LC_ALL=C sort)
    [ "${#launchers[@]}" -gt 0 ] || fail "no launcher definitions"
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

    for launcher in "${launchers[@]}"; do
        [ -x "${home}/.local/bin/${launcher}" ] || fail "install did not place executable ${launcher}"
        cmp -s "${REPO_ROOT}/.devcontainer/${launcher}" "${home}/.local/bin/${launcher}" \
            || fail "installed ${launcher} differs from the source"
        output="$(env HOME="$home" PI_CODING_AGENT_DIR="${home}/.pi/agent" \
            COMMANDCODE_API_KEY=dummy-for-dry-run OPENCODE_API_KEY=dummy-for-dry-run \
            PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
            zsh "${home}/.local/bin/${launcher}" --resume)"
        prefix="$(launcher_pi_args_from_source "$launcher")" \
            || fail "cannot read ${launcher} source arguments"
        args="$(awk 'seen { print } $0 == "pi" { seen = 1 }' <<<"$output")"
        expected="$(printf '%s\n' "$prefix" --resume)"
        assert_eq "$args" "$expected" "installed ${launcher} Pi arguments must match the source"
    done
}

test_live_openai_codex_models() {
    [ "${PI_CODEX_LIVE_CHECK:-0}" = 1 ] || return 0

    local version launcher model output models prefix
    version="$(pi --version)" || fail "pi --version failed"
    dpkg --compare-versions "$version" ge 0.99.1 \
        || fail "Pi 0.99.1 or newer is required (installed: ${version})"

    models="$(python3 - "${REPO_ROOT}/.devcontainer/pi-superagents" <<'PY_MODELS'
import json
from pathlib import Path
import sys

models = set()
for launcher in ("piga", "pigs", "pigl"):
    config = json.loads((Path(sys.argv[1]) / f"{launcher}.json").read_text(encoding="utf-8"))
    for tier in config["superagents"]["modelTiers"].values():
        provider, model = tier["model"].split("/", 1)
        if provider == "openai-codex":
            models.add(model)
print(*sorted(models), sep="\n")
PY_MODELS
)" || fail "cannot read Codex tier models"
    for launcher in piga pigs pigl; do
        prefix="$(launcher_pi_args_from_source "$launcher")" \
            || fail "cannot read ${launcher} source arguments"
        model="$(awk '$0 == "--model" { getline; print; exit }' <<<"$prefix")"
        models="$(printf '%s\n' "$models" "$model")"
    done
    models="$(sort -u <<<"$models")"
    while IFS= read -r model; do
        output="$(pi --list-models "$model")" || fail "pi --list-models ${model} failed"
        printf '%s\n' "$output" | awk -v model="$model" \
            '$1 == "openai-codex" && $2 == model { found = 1 } END { exit !found }' \
            || fail "openai-codex/${model} is unavailable; log in with /login or update Pi"
    done <<<"$models"
}

test_launchers_accept_tilde_agent_dir
test_missing_oauth_guides_login
test_install_places_all_launchers_with_regular_mode
test_live_openai_codex_models
printf 'OK test-pi-openai-codex\n'
