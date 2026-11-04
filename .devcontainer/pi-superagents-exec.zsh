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
# tier config の bind 先は必ず HOME から組み立てる。PI_CODING_AGENT_DIR は Pi 本体の設定
# ディレクトリを移すだけで、拡張の読み先は動かないため、ここで使うと bind 先が
# 実際の読み先とずれる。
#
# 前提が欠けたときは共有 config へ暗黙にフォールバックせず、起動を止める。
# 黙って落ちると tier が警告なく混線するため。
#
# PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 のときは exec せず、実行予定の argv を
# 1 行 1 要素で出力する。テスト用。
#

# Match native Pi: expand only ~ / ~/ once, then collapse . / .. lexically.
# :a must precede filesystem traversal; :A is reserved for the auth mount target.
# REPLY avoids losing trailing newlines in a path through command substitution.
pi_agent_directory() {
    local agent_dir="${PI_CODING_AGENT_DIR:-${HOME}/.pi/agent}"
    if [[ "${agent_dir}" == "~" ]]; then
        agent_dir="${HOME}"
    elif [[ "${agent_dir}" == "~/"* ]]; then
        agent_dir="${HOME}/${agent_dir#'~/'}"
    fi
    REPLY="${agent_dir:a}"
}

pi_openai_codex_require_oauth() {
    local REPLY
    pi_agent_directory
    local auth_file="${REPLY}/auth.json"

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
    local REPLY
    pi_agent_directory
    local auth_file="${REPLY}/auth.json"

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

# Vertex ランチャーの一覧と、起動前に bundled catalog で確かめる exact model ID は
# ここだけで定義する。ID は親 Pi の --model と、.devcontainer/pi-superagents/<launcher>.json
# の tier が使う google-vertex のモデルに合わせる。Vertex ランチャーなら ID を reply に
# 入れて 0 を返し、それ以外は 1 を返す。呼び出し側は local -a reply を宣言しておく。
pi_google_vertex_models() {
    case "$1" in
        pigemf) reply=(gemini-3.8-flash) ;;
        pigemp) reply=(gemini-3.8-flash gemini-3.1-pro-preview) ;;
        pigema) reply=(gemini-3.8-flash gemini-4-argon) ;;
        *) return 1 ;;
    esac
}

# メタデータだけを読む。Pi CLI / provider availability API は認証を調べるため
# 使わない。npm で配置された Pi の実体から bundled catalog を探す。
pi_google_vertex_require_models() {
    local launcher="$1"
    local -a reply
    pi_google_vertex_models "${launcher}" || return 1
    if ! node -e '
const fs = require("node:fs");
const path = require("node:path");
try {
    let dir = path.dirname(fs.realpathSync(process.argv[1]));
    let catalog;
    while (true) {
        const file = path.join(dir, "node_modules/@earendil-works/pi-ai/dist/providers/data/google-vertex.json");
        if (fs.existsSync(file)) {
            catalog = JSON.parse(fs.readFileSync(file, "utf8"))["google-vertex"];
            break;
        }
        const parent = path.dirname(dir);
        if (parent === dir) throw new Error();
        dir = parent;
    }
    for (const id of process.argv.slice(2)) {
        const model = catalog?.[`chat:${id}`];
        if (model?.id !== id || model.provider !== "google-vertex" || model.api !== "google-vertex") {
            throw new Error();
        }
    }
} catch {
    process.exit(1);
}
' "$(command -v pi)" "${reply[@]}" >/dev/null 2>&1; then
        print -ru2 -- "[${launcher}] ERROR: Vertex model catalog が無いか、必要な exact model ID がありません。Pi を更新してください。"
        return 1
    fi
}

# auth.json は設定としてだけ読む。credential の検証、!command の実行、ADC の
# 探索はしない。出力は呼び出し元が変数に取り込み、pipe FD で bwrap に渡す。
pi_google_vertex_auth_overlay() {
    node -e '
const fs = require("node:fs");
try {
    let auth = {};
    try {
        auth = JSON.parse(fs.readFileSync(process.argv[1], "utf8").replace(/^\uFEFF/, ""));
    } catch (error) {
        if (error.code !== "ENOENT") throw error;
        // bwrap は存在しない mount 先を host に空ファイルとして作る。そのままだと
        // 次の素の Pi が JSON を読めないため、未作成時だけ空の設定を一括で置く。
        // link は既存ファイルを置き換えず、同時起動でも先に作られた設定を尊重する。
        const path = require("node:path");
        const dir = path.dirname(process.argv[1]);
        fs.mkdirSync(dir, { recursive: true });
        const staging = fs.mkdtempSync(path.join(dir, ".pi-vertex-mount-"));
        try {
            const empty = path.join(staging, "auth.json");
            fs.writeFileSync(empty, "{}\n", { mode: 0o600 });
            try {
                fs.linkSync(empty, process.argv[1]);
            } catch (linkError) {
                if (linkError.code !== "EEXIST") throw linkError;
            }
        } finally {
            fs.rmSync(staging, { recursive: true, force: true });
        }
        auth = JSON.parse(fs.readFileSync(process.argv[1], "utf8").replace(/^\uFEFF/, ""));
    }
    if (!auth || typeof auth !== "object" || Array.isArray(auth)) throw new Error();
    const adcPath = auth["google-vertex"]?.env?.GOOGLE_APPLICATION_CREDENTIALS;
    // Pi は起動時やモデル切替時にも OAuth を更新する。readonly の snapshot では
    // 更新後の token を保存できないため、期限にかかわらず OAuth entry を外す。
    for (const [provider, credential] of Object.entries(auth)) {
        if (credential?.type === "oauth") delete auth[provider];
    }
    // Pi native google-vertex API はこの marker を API key ではなく ADC と扱う。
    auth["google-vertex"] = { type: "api_key", key: "gcp-vertex-credentials" };
    if (typeof adcPath === "string" && adcPath.length > 0) {
        auth["google-vertex"].env = { GOOGLE_APPLICATION_CREDENTIALS: adcPath };
    }
    process.stdout.write(JSON.stringify(auth));
} catch {
    // JSON parser の例外には秘密が含まれる可能性があるので表示しない。
    process.stderr.write("ERROR: auth.json の設定を読み取れません。起動を中止します。\n");
    process.exit(1);
}
' "$1"
}


# New launch paths validate exact parent/child metadata without asking Pi for
# available models (which resolves auth). Native parsers/composition keep JSONC,
# custom overrides, catalog freshness and supported thinking aligned with Pi.
pi_launcher_require_models() {
    local launcher="$1"
    shift
    local REPLY
    pi_agent_directory
    if ! node --input-type=module - "$(command -v pi)" "${REPLY}" \
        "${HOME}/.pi/agent/extensions/subagent.d/${launcher}/config.json" \
        "$@" <<'JS'
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
try {
    const [pi, agentDir, tierFile, ...args] = process.argv.slice(2);
    let packageDir = path.dirname(fs.realpathSync(pi));
    while (!fs.existsSync(path.join(packageDir, 'dist/core/model-config.js'))) {
        const next = path.dirname(packageDir);
        if (next === packageDir) throw new Error();
        packageDir = next;
    }
    const load = file => import(pathToFileURL(path.join(packageDir, file)).href);
    // Use Pi's parser so repeated options, consumed values and -- match the
    // actual invocation. Keep the original argv untouched for bwrap/Pi.
    const {parseArgs} = await load('dist/cli/args.js');
    const {provider, model: parentModel, thinking} = parseArgs(args);
    const parent = {model: `${provider}/${parentModel}`, thinking};
    const {findExactModelReferenceMatch} = await load('dist/core/model-resolver.js');
    const {ModelConfig} = await load('dist/core/model-config.js');
    const {composeModelProvider} = await load('dist/core/provider-composer.js');
    const {withRemoteCatalog, withPersonalizedCatalog} = await load('dist/core/remote-catalog-provider.js');
    const ai = 'node_modules/@earendil-works/pi-ai/dist/';
    const {builtinProviders, getBuiltinModelDataGeneratedAt} = await load(`${ai}providers/all.js`);
    const {getSupportedThinkingLevels} = await load(`${ai}models.js`);
    const readJson = file => {
        if (!fs.statSync(file).isFile()) throw new Error();
        return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
    };
    const modelsFile = path.join(agentDir, 'models.json');
    if (fs.existsSync(modelsFile) && !fs.statSync(modelsFile).isFile()) throw new Error();
    const config = await ModelConfig.load(modelsFile);
    if (config.getError()) throw new Error();
    const tiers = readJson(tierFile)?.superagents?.modelTiers;
    if (!tiers || Array.isArray(tiers) || typeof tiers !== 'object') throw new Error();
    for (const required of ['cheap', 'balanced', 'max']) {
        if (!Object.hasOwn(tiers, required)) throw new Error();
    }
    const storeFile = path.join(agentDir, 'models-store.json');
    const store = fs.existsSync(storeFile) ? readJson(storeFile) : {};
    const builtins = new Map(builtinProviders().map(p => [p.id, p]));
    const providers = new Map();
    for (const tier of [parent, ...Object.values(tiers)]) {
        if (typeof tier?.model !== 'string' || typeof tier.thinking !== 'string') throw new Error();
        const slash = tier.model.indexOf('/');
        if (slash <= 0) throw new Error();
        const id = tier.model.slice(0, slash), modelId = tier.model.slice(slash + 1);
        if (!providers.has(id)) {
            let base = builtins.get(id);
            if (!base && !config.getProvider(id)) throw new Error();
            // Restore only public saved metadata. Never use FileModelsStore
            // (locks/writes), refresh auth, or call a provider availability API.
            if (base && id !== 'radius') {
                const wrap = id === 'openrouter' ? withPersonalizedCatalog : withRemoteCatalog;
                const generated = getBuiltinModelDataGeneratedAt();
                base = id === 'openrouter'
                    ? wrap(base, () => {throw new Error();}, undefined, generated)
                    : wrap(base, undefined, generated);
                await base.refreshModels({stored: store[id], allowNetwork: false,
                    signal: new AbortController().signal,
                    publish: async ({update}) => {update?.(); return true;}});
            }
            providers.set(id, config.getProvider(id) ? composeModelProvider(id, base, config) : base);
        }
        const models = providers.get(id)?.getModels().filter(m => m.provider === id) ?? [];
        // Parent CLI references may be bare IDs (including slashes) or provider/id.
        // Native exact lookup handles both without fuzzy fallback or auth checks.
        // Tier config keeps its existing literal provider/id matching.
        const model = tier === parent
            ? findExactModelReferenceMatch(modelId, models)
            : models.find(m => m.id === modelId);
        if (!model || !getSupportedThinkingLevels(model).includes(tier.thinking)) throw new Error();
    }
} catch {
    // Parser/composition errors may contain user-owned secrets. Do not echo them.
    process.exit(1);
}
JS
    then
        print -ru2 -- "[${launcher}] ERROR: model catalog / models.json / tier config を解決できません。起動を中止します。"
        print -ru2 -- "Pi の更新: pi update --models（必要なら Pi 本体も更新）"
        print -ru2 -- "provider の配置: zsh scripts/setup_pi.zsh"
        print -ru2 -- "tier の配置・確認: zsh scripts/setup_pi_superagents.zsh --if-absent"
        return 1
    fi
}

# pi-superagents は tier ごとに、ランチャーの設定を同梱の既定（default-config.json）の上に重ねる。
# 欠けた tier は警告なく同梱の既定 model（1.14.4 の balanced は opencode-go/glm-5.3-flash）になり、
# 利用者が選んでいない provider へ子の要求が送られる（#307）。全ランチャーで、cheap / balanced / max の
# model が provider/model の形でそろっているかを起動前に確かめる。値は拡張と同じく文字列か {model}。
# thinking は欠けても model が変わらないので見ない。設定の中身はエラーに出さない。
pi_launcher_require_tiers() {
    local launcher="$1" config="$2"
    if ! node -e '
const fs = require("node:fs");
try {
    const tiers = JSON.parse(fs.readFileSync(process.argv[1], "utf8").replace(/^﻿/, ""))?.superagents?.modelTiers;
    if (!tiers || typeof tiers !== "object" || Array.isArray(tiers)) throw new Error();
    for (const name of ["cheap", "balanced", "max"]) {
        const tier = Object.hasOwn(tiers, name) ? tiers[name] : undefined;
        const model = typeof tier === "string" ? tier : tier?.model;
        if (typeof model !== "string" || !/^[^/]+\/./.test(model)) throw new Error();
    }
} catch {
    process.exit(1);
}
' "${config}" >/dev/null 2>&1; then
        print -ru2 -- "[${launcher}] ERROR: pi-superagents の tier 設定に cheap / balanced / max の model（provider/model の形）がそろっていません:"
        print -ru2 -- "  ${config}"
        print -ru2 -- ""
        print -ru2 -- "欠けた tier は pi-superagents に同梱の既定 model（利用者が選んでいない model）に切り替わるため、起動を中止します。"
        print -ru2 -- "リポジトリの .devcontainer/pi-superagents/${launcher}.json に合わせて補うか、リポジトリのルートで次を実行してください（既存の設定は退避されます）:"
        print -ru2 -- ""
        print -ru2 -- "  zsh scripts/setup_pi_superagents.zsh"
        return 1
    fi
}

pi_superagents_exec() {
    local launcher="$1"
    shift

    case "${launcher}" in
        pigt|pidid) pi_launcher_require_models "${launcher}" "$@" || return 1 ;;
    esac

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
        print -ru2 -- "  zsh scripts/setup_pi_superagents.zsh"
        return 1
    fi

    pi_launcher_require_tiers "${launcher}" "${config}" || return 1

    # 注: zsh では $@ は特殊配列 argv に他ならないため、ローカル変数を argv と
    # 名付けると位置パラメータを影(shadow)にしてしまう。args_ などの別名で
    # 宣言して、pi への引数引き継ぎ(下の "$@")が空にならないようにする。
    # Pin the interpreted directory for every native consumer and child cwd.
    local REPLY
    pi_agent_directory
    export PI_CODING_AGENT_DIR="${REPLY}"

    local -a args_
    args_=(
        bwrap
        --dev-bind / /
        --die-with-parent
    )

    local agent_dir="${PI_CODING_AGENT_DIR}" auth_file vertex=0
    local -a reply
    if pi_google_vertex_models "${launcher}"; then
        vertex=1
        auth_file="${agent_dir}/auth.json"

        # auth のファイルだけを重ねる。settings / sessions とそれらの lock は
        # 元のディレクトリに残し、素の Pi や別ランチャーとの永続化・排他を保つ。
        # bwrap cannot mount data onto a symlink. Pi follows it, so mount only
        # its resolved destination; keep the host link and shared bytes intact.
        args_+=(--ro-bind-data 3 "${auth_file:A}")
    fi

    args_+=(
        --bind "${launcher_dir}" "${shared_dir}"
        --
        # Pi 1.0.0 の fullscreen 既定を避け、Herdr の通常のスクロール履歴を残す。
        pi --tui-mode regular "$@"
    )

    if [[ "${PI_SUPERAGENTS_LAUNCHER_DRY_RUN:-}" == "1" ]]; then
        printf '%s\n' "${args_[@]}"
        return 0
    fi

    if (( vertex )); then
        pi_google_vertex_require_models "${launcher}" || return 1
        local auth_overlay
        auth_overlay="$(pi_google_vertex_auth_overlay "${auth_file}")" || return 1
        if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
            local saved_adc
            # marker の key 分岐は saved env を SDK に渡さないため実効環境へ移す。
            # 同じ snapshot を stdin で読み、末尾の改行も失わないよう点を付ける。
            saved_adc="$(printf '%s' "${auth_overlay}" | node -e '
const fs = require("node:fs");
try {
    const auth = JSON.parse(fs.readFileSync(0, "utf8"));
    process.stdout.write((auth["google-vertex"].env?.GOOGLE_APPLICATION_CREDENTIALS ?? "") + ".");
} catch {
    process.stderr.write("ERROR: ADC パスの設定を読み取れません。起動を中止します。\n");
    process.exit(1);
}
')" || return 1
            saved_adc="${saved_adc%.}"
            if [[ -n "${saved_adc}" ]]; then
                export GOOGLE_APPLICATION_CREDENTIALS="${saved_adc}"
            fi
        fi
        # <(...) は pipe。here-string / 一時ファイルや argv に秘密を置かず、
        # Pi の TUI 用 stdin は元の端末のままにする。FD 3 は bwrap が消費する。
        exec 3< <(printf '%s' "${auth_overlay}")
        unset auth_overlay
    fi

    # bwrap は bind 先が存在することを要求する。dry-run に副作用を残さないよう、
    # 実際に起動するときだけ用意する。
    mkdir -p "${shared_dir}"

    exec "${args_[@]}"
}
