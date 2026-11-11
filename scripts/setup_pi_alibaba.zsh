#!/usr/bin/env zsh

set -euo pipefail

#
# Pi + Alibaba Cloud Model Studio Token Plan (qwen4-max-preview)
#
# Idempotent setup script
#
# Creates:
#   ~/.pi/agent/models.json   Alibaba provider/model definition
#   ~/.local/bin/piaq         Pi launcher
#
# alibaba は Pi の built-in provider ではない（opencode-go と違う）
# ため、auth.json は使わない。認証は models.json の apiKey フィールド
# （"$MAAS_ANTHROPIC_TOKEN"）が実行時に環境変数を参照して解決する。
# このスクリプトは key をファイルに書かない。ローテーションで実行し直す必要はない。
#
# モデル定義の元データは .devcontainer/pi-models.json である。
#
# 新規コンテナは install_beforehand.bash が piaq を置く。~/.pi は bind mount
# で残るが ~/.local/bin はリビルドで失われる。既存の models.json へ
# providers.alibaba を反映するとき、またはランチャーを置き直すときに使う。
# tier 設定は書かない。最後に案内する setup_pi_superagents.zsh が置く。
#

readonly PROVIDER="alibaba"
readonly THINKING="max"

#
# pi --list-models で確かめるモデル。既定は qwen4-max-preview。
# qwen3.8-flash は tier の cheap で、piaq の --models には載らない。
#
readonly MODELS=(
    "qwen4-max-preview"
    "qwen3.8-flash"
)

readonly DEFAULT_MODEL="qwen4-max-preview"

# Keep path-owned trailing newlines; remove only the CLI delimiter and sentinel.
PI_DIR="$(python3 "${0:A:h}/../.devcontainer/pi-provider-setup.py" --agent-dir && printf .)"
PI_DIR="${PI_DIR%$'\n'.}"
readonly PI_DIR
# Follow-up Pi commands must reuse this interpretation, even after joining paths.
export PI_CODING_AGENT_DIR="${PI_DIR}"
readonly MODELS_JSON="${PI_DIR}/models.json"

readonly DEVCONTAINER_DIR="${0:A:h}/../.devcontainer"
readonly MODELS_SOURCE="${DEVCONTAINER_DIR}/pi-models.json"
readonly LAUNCHER_SOURCE="${DEVCONTAINER_DIR}/piaq"

readonly BIN_DIR="${HOME}/.local/bin"


log() {
    print -r -- "[setup_pi_alibaba] $*"
}

die() {
    print -ru2 -- "[setup_pi_alibaba] ERROR: $*"
    exit 1
}

# pi の出力に key が混ざっても表示しない。値は引数やコマンド行に載せない。
redact_key() {
    python3 -c '
import os
import sys

key = os.environ.get("MAAS_ANTHROPIC_TOKEN") or ""
text = sys.stdin.read()
if key:
    text = text.replace(key, "")
sys.stdout.write(text)
'
}


#
# ----------------------------------------------------------------------
# 0. Preconditions
# ----------------------------------------------------------------------
#

command -v python3 >/dev/null 2>&1 ||
    die "python3 is required."

command -v pi >/dev/null 2>&1 ||
    die "pi is not installed or is not in PATH."

[[ -f "${MODELS_SOURCE}" ]] ||
    die "Model definition source not found: ${MODELS_SOURCE}"
[[ -f "${DEVCONTAINER_DIR}/pi-superagents-exec.zsh" ]] ||
    die "Launcher helper source not found: ${DEVCONTAINER_DIR}/pi-superagents-exec.zsh"
[[ -f "${LAUNCHER_SOURCE}" ]] ||
    die "Launcher source not found: ${LAUNCHER_SOURCE}"

#
# The launcher is installed verbatim, so the model this script expects
# must be the one piaq actually runs.
#
grep -Fq -- "--provider ${PROVIDER}" "${LAUNCHER_SOURCE}" ||
    die "${LAUNCHER_SOURCE} does not use --provider ${PROVIDER}."

grep -Fq -- "--model ${DEFAULT_MODEL}" "${LAUNCHER_SOURCE}" ||
    die "${LAUNCHER_SOURCE} does not use --model ${DEFAULT_MODEL}."

log "Pi executable : $(command -v pi)"
log "Pi config dir : ${PI_DIR}"
log "Model source  : ${MODELS_SOURCE}"
log "Launcher      : ${BIN_DIR}/piaq"


#
# ----------------------------------------------------------------------
# 1. Apply the Alibaba model definition
#
# key は要らない。providers.alibaba だけを置き換える。ほかの provider は
# 保ち、変更があるときだけ更新前を models.json.bak.* へ退避する。
# ----------------------------------------------------------------------
#

python3 "${0:A:h}/../.devcontainer/pi-provider-setup.py" \
    "${PI_DIR}" "${MODELS_SOURCE}" "${PROVIDER}"

mkdir -p "${BIN_DIR}"
# Ship the matching helper with the launcher; leave all existing tier configs alone.
install -m 0644 "${DEVCONTAINER_DIR}/pi-superagents-exec.zsh" "${BIN_DIR}/pi-superagents-exec.zsh"

log "models.json: ${PROVIDER} definition applied."


#
# ----------------------------------------------------------------------
# 2. Install ~/.local/bin/piaq
#
# Copied verbatim from .devcontainer/piaq, the same file
# install_beforehand.bash places on rebuild.
# ----------------------------------------------------------------------
#

if [[ -f "${BIN_DIR}/piaq" ]] && cmp -s "${LAUNCHER_SOURCE}" "${BIN_DIR}/piaq"; then
    log "piaq launcher: already up to date."
else
    install -m 0755 "${LAUNCHER_SOURCE}" "${BIN_DIR}/piaq"
    log "piaq launcher: installed."
fi

[[ -x "${BIN_DIR}/piaq" ]] ||
    die "${BIN_DIR}/piaq was not created correctly."

log "Launcher executable: piaq: OK"


#
# ----------------------------------------------------------------------
# 3. Validate provider/model availability
#
# Pi は key を解決できない provider をモデル一覧から外す。key が無いときの
# pi --list-models は必ず失敗するので、確認しない。判定は ccda / piaq と
# 同じ [[ ${MAAS_ANTHROPIC_TOKEN:-} != *[A-Za-z0-9]* ]]。値は表示しない。
#
# 一覧は `<provider> <model> <context> ...` の 1・2 列目で比べる。失敗
# メッセージ `No models matching "<id>"` は ID 自身を含むので、部分一致は
# 使わない。
# ----------------------------------------------------------------------
#

if [[ ${MAAS_ANTHROPIC_TOKEN:-} != *[A-Za-z0-9]* ]]; then
    log "MAAS_ANTHROPIC_TOKEN is unset, empty, or has no letters or digits."
    log "Skipping 'pi --list-models' validation."
    log "Export the key in this shell, then run piaq:"
    log '  export MAAS_ANTHROPIC_TOKEN="..."'
    log "  piaq"
else
    log "Checking Alibaba model availability..."

    for _model in "${MODELS[@]}"; do
        MODEL_LIST="$(
            pi --list-models "${_model}" 2>&1 || true
        )"

        if ! print -r -- "${MODEL_LIST}" |
            awk -v p="${PROVIDER}" -v m="${_model}" \
                '$1 == p && $2 == m { found = 1 } END { exit !found }'; then
            print -ru2 -- ""
            print -ru2 -- "Alibaba model was not found."
            print -ru2 -- ""
            print -ru2 -- "Expected:"
            print -ru2 -- "  ${PROVIDER}/${_model}"
            print -ru2 -- ""
            print -ru2 -- "Pi output:"
            print -ru2 -- "$(print -r -- "${MODEL_LIST}" | redact_key)"
            print -ru2 -- ""
            print -ru2 -- "provider 定義はこのスクリプトが適用済みです:"
            print -ru2 -- "  ${MODELS_JSON}"
            print -ru2 -- ""
            print -ru2 -- "MAAS_ANTHROPIC_TOKEN が有効か確認してください。"
            print -ru2 -- "key を解決できない provider は pi のモデル一覧に現れません。"
            print -ru2 -- "値はこのスクリプトでは表示しません。"
            print -ru2 -- ""
            exit 1
        fi

        log "Model found: ${PROVIDER}/${_model}"
    done
fi


#
# ----------------------------------------------------------------------
# 4. Summary
#
# tier 設定はここでは書かない。フラグ無しの setup_pi_superagents.zsh は
# 既存の全ランチャーの tier 設定を退避して上書きする。piaq の設定だけを
# 新しく置く --if-absent を案内する（install_beforehand.bash と同じ）。
# ----------------------------------------------------------------------
#

print
print "========================================"
print " Pi + Alibaba Token Plan setup complete"
print "========================================"
print
print "Provider : ${PROVIDER}"
print "Thinking : ${THINKING}"
print "Models   : ${MODELS[*]}"
print "Models   : ${MODELS_JSON}"
print "Launcher : ${BIN_DIR}/piaq"
print "Auth     : MAAS_ANTHROPIC_TOKEN environment variable (not written to a file)"
print
print "piaq passes the following arguments to Pi:"
print
print "  pi \\"
print "    --provider ${PROVIDER} \\"
print "    --model ${DEFAULT_MODEL} \\"
print "    --thinking ${THINKING}"
print
print "Tier config is not written by this script. From the repository root,"
print "place only missing launcher configs (including piaq):"
print
print "  zsh scripts/setup_pi_superagents.zsh --if-absent"
print
print "Without --if-absent, existing tier configs for every launcher are"
print "backed up and replaced. Use --if-absent unless that replacement is intended."
print
print "Run piaq from a shell where the key is exported"
print "(a launcher-started session does not have the key):"
print
print '  export MAAS_ANTHROPIC_TOKEN="..."'
print "  piaq"
print
