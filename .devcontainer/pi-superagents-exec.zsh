#
# pi-superagents のランチャー別 model tier 設定を Pi に見せるための共通ヘルパ。
#
# pi-superagents は設定を os.homedir()/.pi/agent/extensions/subagent/config.json
# から読む。このパスは拡張のソースに直接書かれており、環境変数による override が
# 無い。そこで bwrap の mount namespace を使い、ランチャー固有のディレクトリを
# その共有パスへプロセスツリー単位で重ねる。
#
#   - HOME を変えないので git / ssh の設定の見え方には影響しない
#   - 共有ファイルをコピー・上書きしないので、同時起動でも競合しない
#   - mount namespace はプロセスツリー固有なので、別ランチャーからは見えない
#   - 子 Pi は namespace を継承するので、親子で同じ tier を見る
#
# ただし bwrap は no_new_privs を立てるため、このヘルパ経由で起動した Pi の
# 配下では sudo / su などの setuid バイナリが使えない。
#
# bind 先は必ず HOME から組み立てる。PI_CODING_AGENT_DIR は Pi 本体の設定
# ディレクトリを移すだけで、拡張の読み先は動かないため、ここで使うと bind 先が
# 実際の読み先とずれる。
#
# 前提が欠けたときは共有 config へ暗黙にフォールバックせず、起動を止める。
# 黙って落ちると tier が警告なく混線するため。
#
# PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 のときは exec せず、実行予定の argv を
# 1 行 1 要素で出力する。テスト用。
#

pi_openai_codex_require_oauth() {
    local agent_dir="${PI_CODING_AGENT_DIR:-${HOME}/.pi/agent}"
    if [[ "${agent_dir}" == "~" ]]; then
        agent_dir="${HOME}"
    elif [[ "${agent_dir}" == "~/"* ]]; then
        agent_dir="${HOME}/${agent_dir#'~/'}"
    fi
    local auth_file="${agent_dir}/auth.json"

    if [[ -f "${auth_file}" ]] && node -e '
const fs = require("node:fs");
let credential;
try {
    credential = JSON.parse(fs.readFileSync(process.argv[1], "utf8"))["openai-codex"];
} catch {
    process.exit(1);
}
process.exit(credential?.type === "oauth" &&
    typeof credential.access === "string" && credential.access.length > 0 &&
    typeof credential.refresh === "string" && credential.refresh.length > 0 &&
    typeof credential.expires === "number" ? 0 : 1);
' "${auth_file}" >/dev/null 2>&1; then
        return 0
    fi

    print -ru2 -- "OpenAI Codex OAuth authentication is not configured."
    print -ru2 -- ""
    print -ru2 -- "Run:"
    print -ru2 -- "  pi"
    print -ru2 -- ""
    print -ru2 -- "and execute:"
    print -ru2 -- "  /login openai-codex"
    return 1
}

pi_xai_require_oauth() {
    local agent_dir="${PI_CODING_AGENT_DIR:-${HOME}/.pi/agent}"
    if [[ "${agent_dir}" == "~" ]]; then
        agent_dir="${HOME}"
    elif [[ "${agent_dir}" == "~/"* ]]; then
        agent_dir="${HOME}/${agent_dir#'~/'}"
    fi
    local auth_file="${agent_dir}/auth.json"

    if [[ -f "${auth_file}" ]] && node -e '
const fs = require("node:fs");
let credential;
try {
    credential = JSON.parse(fs.readFileSync(process.argv[1], "utf8"))["xai"];
} catch {
    process.exit(1);
}
process.exit(credential?.type === "oauth" &&
    typeof credential.access === "string" && credential.access.length > 0 &&
    typeof credential.refresh === "string" && credential.refresh.length > 0 &&
    typeof credential.expires === "number" ? 0 : 1);
' "${auth_file}" >/dev/null 2>&1; then
        return 0
    fi

    print -ru2 -- "xAI subscription authentication is not configured."
    print -ru2 -- ""
    print -ru2 -- "Run:"
    print -ru2 -- "  pi"
    print -ru2 -- ""
    print -ru2 -- "and execute:"
    print -ru2 -- "  /login xai"
    print -ru2 -- ""
    print -ru2 -- "Then sign in with:"
    print -ru2 -- "  SuperGrok or X Premium"
    return 1
}

pi_superagents_exec() {
    local launcher="$1"
    shift

    local shared_dir="${HOME}/.pi/agent/extensions/subagent"
    local launcher_dir="${HOME}/.pi/agent/extensions/subagent.d/${launcher}"
    local config="${launcher_dir}/config.json"

    if ! command -v bwrap >/dev/null 2>&1; then
        print -ru2 -- "[${launcher}] ERROR: bwrap (bubblewrap) が見つかりません。"
        print -ru2 -- ""
        print -ru2 -- "pi-superagents の model tier をランチャーごとに分離するために必要です。"
        print -ru2 -- ""
        print -ru2 -- "  sudo apt install -y bubblewrap"
        return 1
    fi

    if [[ ! -f "${config}" ]]; then
        print -ru2 -- "[${launcher}] ERROR: pi-superagents の設定が見つかりません:"
        print -ru2 -- "  ${config}"
        print -ru2 -- ""
        print -ru2 -- "リポジトリのルートで setup スクリプトを一度実行してください:"
        print -ru2 -- ""
        print -ru2 -- "  zsh .devcontainer/setup_pi_superagents.zsh"
        return 1
    fi

    # 注: zsh では $@ は特殊配列 argv に他ならないため、ローカル変数を argv と
    # 名付けると位置パラメータを影(shadow)にしてしまう。args_ などの別名で
    # 宣言して、pi への引数引き継ぎ(下の "$@")が空にならないようにする。
    local -a args_
    args_=(
        bwrap
        --dev-bind / /
        --die-with-parent
        --bind "${launcher_dir}" "${shared_dir}"
        --
        # Pi 1.0.0 の fullscreen 既定を避け、Herdr の通常のスクロール履歴を残す。
        # 利用者の引数は後ろに並ぶので、--tui-mode fullscreen を渡せばそちらが勝つ。
        pi --tui-mode regular "$@"
    )

    if [[ "${PI_SUPERAGENTS_LAUNCHER_DRY_RUN:-}" == "1" ]]; then
        printf '%s\n' "${args_[@]}"
        return 0
    fi

    # bwrap は bind 先が存在することを要求する。dry-run に副作用を残さないよう、
    # 実際に起動するときだけ用意する。
    mkdir -p "${shared_dir}"

    exec "${args_[@]}"
}
