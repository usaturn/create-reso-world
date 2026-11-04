#!/usr/bin/env zsh

set -euo pipefail

#
# pi-superagents のランチャー別 model tier 設定をセットアップする
#
# 冪等なセットアップスクリプト
#
# 作成するもの:
#   ~/.pi/agent/extensions/subagent/config.json    bwrap の bind 先。ランチャーを通さない Pi で
#                                                  pi-superagents を止める停止用の設定（#307）
#   ~/.pi/agent/extensions/subagent.d/<launcher>/  ランチャー別の config.json
#   ~/.local/bin/pi-superagents-exec.zsh           ランチャー共通ヘルパ
#
# リポジトリの .devcontainer/pi-superagents/<launcher>.json が正。tier 表を
# 変更したときは、このスクリプトを実行して実環境へ反映する。
# install_beforehand.bash は --if-absent で呼ぶため、rebuild だけでは既存の
# config は更新されない。
#
# 使い方:
#   zsh scripts/setup_pi_superagents.zsh              置き直す（既存はバックアップ）
#   zsh scripts/setup_pi_superagents.zsh --if-absent  ランチャー別の config は無いものだけ置く
#
# 共有の bind 先の停止用の設定は、どちらの使い方でも揃える（停止用のキーが無ければ退避して置き換える）。
#

readonly REPO_ROOT="${0:A:h}/.."
readonly SOURCE_DIR="${REPO_ROOT}/.devcontainer/pi-superagents"
readonly HELPER_SOURCE="${REPO_ROOT}/.devcontainer/pi-superagents-exec.zsh"

#
# bind 先は必ず HOME から組み立てる。pi-superagents は os.homedir() を直接
# 使っており PI_CODING_AGENT_DIR を参照しないため、ここで PI_CODING_AGENT_DIR を
# 使うと配置先が拡張の読み先とずれる。
#
readonly EXT_DIR="${HOME}/.pi/agent/extensions"
readonly SHARED_DIR="${EXT_DIR}/subagent"
readonly LAUNCHER_ROOT="${EXT_DIR}/subagent.d"
readonly BIN_DIR="${HOME}/.local/bin"

readonly LAUNCHERS=(pigo pigod piccg piccd piga pigt pidid pigs pigl pixg pigemf pigemp pigema)

#
# ランチャーを通さない Pi（素の pi、Herdr の復元による再開）は bwrap の mount が無く、共有の bind 先の
# config.json を読む。pi-superagents は tier ごとに設定を同梱の既定（default-config.json）の上に重ねるので、
# 設定が無い・tier が欠けると、利用者が選んでいない同梱の既定 model（1.14.4 の balanced は
# opencode-go/glm-5.3-flash）の子に要求を送る（#307）。未知のトップレベルのキーは拡張の検証で
# エラーになり、拡張は subagent ツールを止めて、キーの名前を表示する。
#
readonly GUARD_KEY="launcherRequired_doNotRemove_restartPiViaLauncher"
readonly GUARD_NOTE="このキーは、ランチャー（pigs など）を通さずに起動した Pi で pi-superagents を止めるための目印です。ランチャーを通さない Pi（素の pi、Herdr の復元による再開）は、この共有の bind 先を読み、欠けた tier を pi-superagents に同梱の既定 model（利用者が選んでいない model）で埋めて子に要求を送ります。このキーを消さず、Pi を終了してランチャーから起動し直してください（例: pigs --session <セッションファイル>）。詳細は create-reso-world の .devcontainer/README.md の「ランチャーを通さない Pi と同梱の既定 model」にあります。"

typeset if_absent=0
if [[ "${1:-}" == "--if-absent" ]]; then
    if_absent=1
elif [[ -n "${1:-}" ]]; then
    print -ru2 -- "usage: setup_pi_superagents.zsh [--if-absent]"
    exit 2
fi

if ! command -v bwrap >/dev/null 2>&1; then
    print -ru2 -- "ERROR: bwrap (bubblewrap) が見つかりません。"
    print -ru2 -- ""
    print -ru2 -- "ランチャーごとの設定分離に必要です:"
    print -ru2 -- ""
    print -ru2 -- "  sudo apt install -y bubblewrap"
    exit 1
fi

mkdir -p "${SHARED_DIR}" "${BIN_DIR}"

# 退避名の基本形は従来どおり <file>.bak.YYYYMMDD-HHMMSS。同一秒に再実行して基本名が既に存在する場合は、
# 既存世代を上書きしないよう .1, .2, … と空いている名前まで連番を増やす。退避先のパスを REPLY に入れる。
backup_existing() {
    local file="$1" base backup i=0
    base="${file}.bak.$(date +%Y%m%d-%H%M%S)"
    backup="${base}"
    while [[ -e "${backup}" ]]; do
        i=$(( i + 1 ))
        backup="${base}.${i}"
    done
    cp "${file}" "${backup}" || return 1
    REPLY="${backup}"
}

# 共有の bind 先に停止用の設定を揃える。停止用のキーを持つ JSON のオブジェクトなら、拡張の移行処理が
# 書き足した内容ごと残す（拡張と同じく BOM は外さずに読む）。それ以外は退避してから置き換える。
ensure_shared_guard() {
    local config="${SHARED_DIR}/config.json" tmp REPLY
    if [[ -L "${config}" || ( -e "${config}" && ! -f "${config}" ) ]]; then
        print -ru2 -- "ERROR: ${config} が通常のファイルではないため、触らずに中止します。"
        print -ru2 -- "別の場所へ移してから、もう一度このスクリプトを実行してください。"
        return 1
    fi
    if [[ -f "${config}" ]] && node -e '
const fs = require("node:fs");
try {
    const config = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
    process.exit(config && typeof config === "object" && !Array.isArray(config) && Object.hasOwn(config, process.argv[2]) ? 0 : 1);
} catch {
    process.exit(1);
}
' "${config}" "${GUARD_KEY}" >/dev/null 2>&1; then
        print -r -- "shared: 停止用の設定を保持しました"
        return 0
    fi
    if [[ -f "${config}" ]]; then
        backup_existing "${config}" || return 1
        print -r -- "shared: 既存の設定を ${REPLY:t} へ退避しました"
    fi
    tmp="$(mktemp "${SHARED_DIR}/.config.json.XXXXXX")" || return 1
    if ! node -e '
const fs = require("node:fs");
fs.writeFileSync(process.argv[1], JSON.stringify({[process.argv[2]]: process.argv[3]}, null, 2) + "\n");
' "${tmp}" "${GUARD_KEY}" "${GUARD_NOTE}"; then
        rm -f -- "${tmp:?}"
        return 1
    fi
    chmod 0644 "${tmp}"
    mv -f -- "${tmp}" "${config}"
    print -r -- "shared: ${config} に停止用の設定を置きました（ランチャーを通さない Pi では pi-superagents が止まります）"
}

install -m 0644 "${HELPER_SOURCE}" "${BIN_DIR}/pi-superagents-exec.zsh"
print -r -- "helper: ${BIN_DIR}/pi-superagents-exec.zsh"

typeset launcher source dest
for launcher in "${LAUNCHERS[@]}"; do
    source="${SOURCE_DIR}/${launcher}.json"
    dest="${LAUNCHER_ROOT}/${launcher}/config.json"

    if [[ ! -f "${source}" ]]; then
        print -ru2 -- "ERROR: ${source} が見つかりません。"
        exit 1
    fi

    mkdir -p "${LAUNCHER_ROOT}/${launcher}"

    if [[ -f "${dest}" ]]; then
        if (( if_absent )); then
            print -r -- "${launcher}: 既存の設定を保持しました"
            continue
        fi
        if cmp -s "${source}" "${dest}"; then
            print -r -- "${launcher}: 変更なし"
            continue
        fi
        backup_existing "${dest}"
        print -r -- "${launcher}: 既存の設定を ${REPLY:t} へ退避しました"
    fi

    install -m 0644 "${source}" "${dest}"
    print -r -- "${launcher}: ${dest} を配置しました"
done

ensure_shared_guard
print -r -- "shared bind target: ${SHARED_DIR}"

if command -v pi >/dev/null 2>&1; then
    typeset installed
    installed="$(pi list 2>/dev/null || true)"
    if print -r -- "${installed}" | grep -q "pi-subagents"; then
        print -ru2 -- ""
        print -ru2 -- "WARNING: npm:pi-subagents がまだ登録されています。"
        print -ru2 -- "pi-superagents の subagent tool と競合するため、削除してください:"
        print -ru2 -- ""
        print -ru2 -- "  pi remove npm:pi-subagents"
    fi
    if ! print -r -- "${installed}" | grep -q "@teelicht/pi-superagents"; then
        print -ru2 -- ""
        print -ru2 -- "WARNING: npm:@teelicht/pi-superagents が未導入です:"
        print -ru2 -- ""
        print -ru2 -- "  pi install --approve npm:@teelicht/pi-superagents"
    fi
fi
