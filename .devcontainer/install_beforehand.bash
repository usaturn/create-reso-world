#!/bin/bash

set -u

# postCreate の出力は、途中でコンテナが止まると残らない。どのステップまで進んだかを
# 後から追えるよう、各ステップの開始を必ず1行で出し、失敗は ERROR 行を残して
# 打ち切る（2026-09-13 のリビルド中断インシデント）。継続してよい処理
# （同梱スキルの状態の表示と workspace cleanup）だけを明示的に続行させるため、スクリプト全体には set -e を
# 付けない。
readonly STEP_TOTAL=31
STEP_NUMBER=0

step() {
    STEP_NUMBER=$((STEP_NUMBER + 1))
    printf '[install_beforehand] [%2d/%2d] %s\n' "${STEP_NUMBER}" "${STEP_TOTAL}" "$@"
}

fail() {
    printf '[install_beforehand] ERROR: %s\n' "$@" >&2
    exit 1
}

warn() {
    printf '[install_beforehand] WARN: %s\n' "$@" >&2
}

# bind mount の target はホスト側に無いと Docker が root 所有で中間ディレクトリごと
# 作成する。書き込めない対象は、そのディレクトリだけを現在ユーザーへ chown して
# 復旧する。再帰しない（配下に bind mount があると、ホスト側データの所有権まで
# 変わるため）。
ensure_user_writable_dir() {
    local dir="$1"
    if ! mkdir -p "$dir" 2>/dev/null; then
        sudo mkdir -p "$dir" || return 1
    fi
    if [ ! -w "$dir" ]; then
        sudo chown "$(id -u):$(id -g)" "$dir" || return 1
    fi
    [ -w "$dir" ]
}

# スクリプトはどの cwd から呼ばれても親 workspace root を正とする。
# `.devcontainer/...` と `scripts/...` への相対参照を同一 root で行う。
WORKSPACE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)" || fail "Cannot resolve workspace root."
readonly WORKSPACE_ROOT
cd -- "$WORKSPACE_ROOT" || fail "Cannot enter workspace root."

step "Ensuring user-writable directories under ~"
# bind mount target の中間ディレクトリ（~/.local/share 等）と target 自体は、
# Docker が root 所有で作る・ホスト側に root 所有のまま残ることがある。
# 以降の全ステップが $HOME 配下へ書き込むため、最初に親から順に書き込み可能を
# 保証する。~/.claude.json はファイル mount のため対象外。ディレクトリの mount はすべてここに並べる
# （.devcontainer/test-initialize-mounts.bash が devcontainer.json の mounts と突き合わせる）。
for dir in \
    "${HOME}/.local" \
    "${HOME}/.local/share" \
    "${HOME}/.local/share/devin" \
    "${HOME}/.local/share/cursor-agent" \
    "${HOME}/.local/bin" \
    "${HOME}/.config" \
    "${HOME}/.config/devin" \
    "${HOME}/.config/gh" \
    "${HOME}/.config/glab-cli" \
    "${HOME}/.config/gcloud" \
    "${HOME}/.config/create-reso-world" \
    "${HOME}/.config/cursor" \
    "${HOME}/.codex" \
    "${HOME}/.claude" \
    "${HOME}/.pi" \
    "${HOME}/.cursor"; do
    if ! ensure_user_writable_dir "$dir"; then
        fail "Failed to prepare writable directory: ${dir}"
    fi
done

# 非対話のエージェントのランナー（tools/agent_runner）の個人設定。既存の設定（壊れた symlink も含む）は上書きしない。
# AGENT_RUNNER_CONFIG は個別の実行の指定なので、導入時の保存先には使わない。
place_agent_runner_config() {
    local config_home="${XDG_CONFIG_HOME:-}"
    case "$config_home" in
    /*) ;;
    *) config_home="${HOME}/.config" ;;
    esac
    local config="${config_home}/agent-runner/config.toml"
    if [ -e "$config" ] || [ -L "$config" ]; then
        return 0
    fi
    mkdir -p "${config_home}/agent-runner" || return 1
    cp .devcontainer/agent-runner.toml "$config" || return 1
}
if ! place_agent_runner_config; then
    fail "Failed to place the agent-runner config."
fi

step "Rewriting the apt sources to HTTPS and updating the package index"
if ! sudo perl -pi -e 's@http://archive\.ubuntu\.com@https://archive.ubuntu.com@g; s@http://security\.ubuntu\.com@https://security.ubuntu.com@g' /etc/apt/sources.list.d/ubuntu.sources; then
    fail "Failed to rewrite /etc/apt/sources.list.d/ubuntu.sources."
fi
if ! sudo apt update; then
    fail "apt update failed."
fi

step "Installing the base packages"
if ! sudo apt install -y vim tig ripgrep fzf jq bubblewrap libglib2.0-0t64 blender python3-numpy libegl1 libgl1; then
    fail "apt install of the base packages failed."
fi

step "Installing the latest ResoLoop release from NuGet"
export PATH="${HOME}/.dotnet/tools:${PATH}"
if ! bash .devcontainer/install_resoloop.bash; then
    fail "ResoLoop installation or update failed."
fi

step "Verifying the Resonite development toolchain"
if ! bash .devcontainer/verify-resonite-tooling.bash; then
    fail "Resonite development toolchain verification failed."
fi

step "Reporting the bundled ResoLoop skills of each project"
# 同梱スキルの同期は手動で行う（AGENTS.md の「プロジェクト運用」）。結果を表示するだけで、差分があっても続ける
if ! bash .devcontainer/report-resoloop-skills.bash; then
    warn "Reporting the bundled ResoLoop skills failed; continuing."
fi

step "Generating the Japanese locale"
if ! sudo perl -pi -e 's/# ja_JP\.UTF-8/ja_JP.UTF-8/' /etc/locale.gen; then
    fail "Failed to enable ja_JP.UTF-8 in /etc/locale.gen."
fi
if ! sudo locale-gen; then
    fail "locale-gen failed."
fi

step "Installing Claude Code"
if ! (
    set -o pipefail
    curl -fsSL https://claude.ai/install.sh | bash
); then
    fail "Claude Code installation failed."
fi
# 各 CLI インストーラは rc ファイルへ PATH を追記するだけで、実行中のシェルへは export しない。
# postCreateCommand の /bin/bash は非対話・非ログインで rc を読まないため、
# 以降の claude / uv 呼び出しのためにここで一度だけ PATH を通す。
export PATH="${HOME}/.local/bin:${PATH}"
if ! command -v claude >/dev/null 2>&1; then
    fail "Claude Code installation completed without placing claude on PATH."
fi

step "Installing the Claude Code plugins"
if ! claude plugin marketplace add dashed/claude-marketplace; then
    fail "Failed to add the dashed/claude-marketplace marketplace."
fi
# 一覧は .claude/settings.json の enabledPlugins と同じにする（.devcontainer/test-install-beforehand.bash が検査する）
for plugin in \
    example-skills@anthropic-agent-skills \
    superpowers@claude-plugins-official \
    feature-dev@claude-plugins-official \
    web-quality-skills@addy-web-quality-skills \
    ripgrep@alberto-marketplace; do
    if ! claude plugin install "$plugin"; then
        fail "Installing plugin ${plugin} failed."
    fi
done

step "Installing Codex"
# Codex CLI は npm で導入し、zshrc.txt の update() も同じ npm で更新する。npm は Node feature が PATH に置く
if ! npm install -g @openai/codex@latest; then
    fail "Codex installation failed."
fi
if ! command -v codex >/dev/null 2>&1; then
    fail "Codex installation completed without placing codex on PATH."
fi

step "Installing Meshy CLI (local verification only)"
if ! bash .devcontainer/install_meshy.bash; then
    fail "Meshy CLI installation or verification failed."
fi

step "Installing the pinned Context7 CLI (ctx7)"
# find-docs スキルが使う。版の固定と導入後の確認は install_ctx7.bash にある（#162）
if ! bash .devcontainer/install_ctx7.bash; then
    fail "Context7 CLI installation failed."
fi

step "Installing uv"
# Python ツールと後続のセットアップで使う uv を導入する。
# uv は ~/.local/bin に入り、この PATH は Claude Code の導入直後に通してある
if ! (
    set -o pipefail
    curl -LsSf https://astral.sh/uv/install.sh | sh
); then
    fail "uv installation failed."
fi
if ! command -v uv >/dev/null 2>&1; then
    fail "uv installation completed without placing uv on PATH."
fi

step "Installing the pinned Gitleaks"
# push の前の検査（scripts/scan-before-push.sh）が使う。版と SHA-256 は install_gitleaks.bash に固定してある
if ! bash .devcontainer/install_gitleaks.bash; then
    fail "Gitleaks installation failed."
fi

step "Installing the Cursor CLI"
# ~/.local/share/cursor-agent は devcontainer.json で bind mount している。ホスト側に
# 存在しない場合は Docker が root 所有で作成するため、所有権を直す（~/.pi と同じ対応）。
# 設定と会話履歴は ~/.cursor、認証情報（auth.json）は ~/.config/cursor に入り、どちらも bind mount 済み。
if ! ensure_user_writable_dir "${HOME}/.local/share/cursor-agent"; then
    fail "Failed to prepare writable directory: ${HOME}/.local/share/cursor-agent."
fi
if ! (
    set -o pipefail
    curl -fsSL https://cursor.com/install | bash
); then
    fail "Cursor CLI installation failed."
fi

step "Installing the Devin CLI"
# ~/.local/share/devin（認証情報と CLI 本体）と ~/.config/devin（設定）は
# devcontainer.json で bind mount し、リビルドでログインを失わないようにする。
# ホスト側に存在しない場合は Docker が root 所有で作成するため、install.sh と
# 以降の devin 呼び出しが書き込めるよう所有権を直す（~/.pi と同じ対応）。
install_devin_cli() {
    local devin_dir
    for devin_dir in "${HOME}/.local/share/devin" "${HOME}/.config/devin"; do
        ensure_user_writable_dir "${devin_dir}" || return 1
    done
    local installer
    installer="$(mktemp)" || return 1
    if ! curl -fsSL https://cli.devin.ai/install.sh -o "${installer}"; then
        rm -f "${installer}"
        return 1
    fi
    # install.sh の末尾は devin setup（対話ウィザード）を起動する。postCreate の実行には
    # TTY がなく、未ログインだとログイン選択プロンプトで停止するため stdin を閉じる。
    # 未ログイン時の setup は「Login canceled」で即失敗するが、バイナリの配置は setup
    # より前に完了しているため、終了コードではなく devin コマンドの存在で成否を判定する。
    bash "${installer}" </dev/null || true
    rm -f "${installer}"
    command -v devin >/dev/null 2>&1 || return 1
    # plugins install はログイン必須。bind mount でログインを永続化しても初回作成時は
    # 未ログインのことがあり、postCreate 中にログインする手段はないため、その場合は
    # 警告してスキップする。-y は install 前の確認プロンプトを自動承認する。
    # auth status は未ログインでも exit 0 で "Not logged in." を返すため終了コードでは
    # 判定できず、先頭が "Logged in" かで分岐する。実行失敗や想定外の出力は未ログインと
    # 区別して警告する。将来 CLI 側にプロンプトが追加されても postCreate が停止しない
    # よう、devin の各呼び出しは stdin を閉じる。
    local auth_status
    auth_status="$(devin auth status </dev/null 2>/dev/null || true)"
    case "${auth_status}" in
    [Ll]ogged\ in*)
        devin plugins install -y obra/superpowers </dev/null || return 1
        ;;
    Not\ logged\ in*)
        warn "devin is not logged in; skipping 'devin plugins install obra/superpowers'."
        warn "Run 'devin auth login' once, then re-run the plugin install."
        ;;
    *)
        warn "devin auth status returned an unexpected state; skipping 'devin plugins install obra/superpowers' (output: ${auth_status:-<empty>})."
        ;;
    esac
}
if ! install_devin_cli; then
    fail "Devin CLI installation failed."
fi

step "Installing pi"
# Validate shared settings before any Pi installation/extension mutation. In
# particular, never let a later cleanup silently sever a user's shared link.
if ! python3 "${WORKSPACE_ROOT}/.devcontainer/pi-provider-setup.py" --settings-check; then
    fail "Unsafe or invalid pi settings.json; aborting before pi installation."
fi
# ~/.pi は devcontainer.json で bind mount している。ホスト側に存在しない場合は
# Docker が root 所有で作成するため、以降の pi install が書き込めるよう所有権を直す。
if ! ensure_user_writable_dir "${HOME}/.pi"; then
    fail "Failed to prepare writable directory: ${HOME}/.pi."
fi
if ! npm install -g --ignore-scripts @earendil-works/pi-coding-agent; then
    fail "pi installation failed."
fi

step "Replacing npm:pi-subagents with @teelicht/pi-superagents"
# --approve は project trust の確認を自動承認する（.agents/skills があると対話プロンプトで止まる）
# npm:pi-subagents は @teelicht/pi-superagents の subagent tool と競合する。
# ~/.pi は bind mount なので、既存環境の settings.json に残った登録も消す。
# この置換は必須なので、失敗を成功扱いしない（fail-loud）。関数化は隔離テスト
# （test-pi-superagents.bash）が install_pi_extensions だけを取り出して fake pi で
# 実行できるようにするため。
install_pi_extensions() {
    local legacy_manifests
    local legacy_listed
    local agent_dir
    if ! agent_dir="$(python3 "${WORKSPACE_ROOT}/.devcontainer/pi-provider-setup.py" --agent-dir && printf .)"; then
        echo "Failed to resolve the pi agent directory; aborting pi-superagents replacement." >&2
        exit 1
    fi
    # Strip only the CLI delimiter and sentinel, not newlines owned by the path.
    agent_dir="${agent_dir%$'\n'.}"

    # 1) 導入前の一覧を取得する。取得できないと置換の前提が崩れるので打ち切る。
    if ! before="$(pi list 2>&1)"; then
        echo "Failed to list pi extensions (pi list); aborting pi-superagents replacement." >&2
        exit 1
    fi
    # 2) 旧 npm:pi-subagents の残骸を探す。settings の一覧（pi list）だけでなく、
    #    pi が管理する npm マニフェストも見る。一覧が綺麗でもマニフェストに残って
    #    いると、`pi update --extensions`（zsh の update() が実行する）で node_modules
    #    ごと再構築されて復活し、subagent ツール名が @teelicht/pi-superagents と
    #    衝突して pigo / pigod が起動できなくなる（#289）。
    legacy_listed=0
    case "$before" in
    *"npm:pi-subagents"*) legacy_listed=1 ;;
    esac
    legacy_manifests="$(grep -l -e '"pi-subagents"' -e '"node_modules/pi-subagents"' \
        "${agent_dir}/npm/package.json" \
        "${agent_dir}/npm/package-lock.json" 2>/dev/null || true)"
    # 3) 登録済み、またはマニフェストに残っていれば削除する。pi remove は未登録の
    #    とき「No matching package found」で exit 1 を返すが、マニフェストの掃除自体は
    #    行う。そのため成否は終了コードではなく、掃除後の実体で判定する。
    if [ "${legacy_listed}" -eq 1 ] || [ -n "${legacy_manifests}" ]; then
        pi remove npm:pi-subagents 2>&1 || true
        # 存在しないパスが混ざると grep は一致していても exit 2 になるため、
        # 終了コードではなく一致したファイルの有無で判定する。
        legacy_manifests="$(grep -l -e '"pi-subagents"' -e '"node_modules/pi-subagents"' \
            "${agent_dir}/npm/package.json" \
            "${agent_dir}/npm/package-lock.json" 2>/dev/null || true)"
        if [ -n "${legacy_manifests}" ]; then
            echo "Failed to remove npm:pi-subagents from the pi managed npm manifest under ${agent_dir}/npm." >&2
            exit 1
        fi
    fi
    # 4) 新拡張を導入する。導入失敗は対象を明示して打ち切る。
    if ! pi install --approve npm:@teelicht/pi-superagents 2>&1; then
        echo "Failed to install npm:@teelicht/pi-superagents." >&2
        exit 1
    fi
    # 5) 導入後に一覧を再取得し、事後条件（旧拡張が残らず新拡張が存在する）を確認する。
    if ! after="$(pi list 2>&1)"; then
        echo "Failed to re-list pi extensions after install." >&2
        exit 1
    fi
    case "$after" in
    *"npm:pi-subagents"*)
        echo "npm:pi-subagents is still registered after replacement." >&2
        exit 1
        ;;
    esac
    case "$after" in
    *"npm:@teelicht/pi-superagents"*)
        ;;
    *)
        echo "npm:@teelicht/pi-superagents is missing after replacement." >&2
        exit 1
        ;;
    esac
}
install_pi_extensions

step "Removing npm:pi-mcp-adapter (superseded by built-in MCP)"
# pi 1.0 の組み込み MCP 拡張（builtin:mcp）に一本化するため pi-mcp-adapter を外す。
# ~/.pi は bind mount なので、既存環境の settings.json には登録が残っている。
# adapter のインストーラは同じ settings.json に -builtin:mcp を書き込んで組み込み側を
# 無効化するため、パッケージ削除と併せてそのエントリも取り除く。
remove_pi_mcp_adapter() {
    local listed
    local after
    local agent_dir
    local adapter_manifests
    local adapter_listed=0

    # settings と npm マニフェストは同じ agent directory を参照する。
    if ! agent_dir="$(python3 "${WORKSPACE_ROOT}/.devcontainer/pi-provider-setup.py" --agent-dir && printf .)"; then
        echo "Failed to resolve the pi agent directory; aborting pi-mcp-adapter removal." >&2
        exit 1
    fi
    # Strip only the CLI delimiter and sentinel, not newlines owned by the path.
    agent_dir="${agent_dir%$'\n'.}"
    if ! python3 "${WORKSPACE_ROOT}/.devcontainer/pi-provider-setup.py" --settings-check "$agent_dir"; then
        echo "Unsafe or invalid ${agent_dir}/settings.json; aborting pi-mcp-adapter removal." >&2
        exit 1
    fi
    if ! listed="$(pi list 2>&1)"; then
        echo "Failed to list pi extensions (pi list); aborting pi-mcp-adapter removal." >&2
        exit 1
    fi
    # 一覧だけでなく pi 管理の npm マニフェストも見る。マニフェストに残っていると
    # pi update --extensions で node_modules ごと再構築されて復活する。
    adapter_manifests="$(grep -l -e '"pi-mcp-adapter"' -e '"node_modules/pi-mcp-adapter"' \
        "${agent_dir}/npm/package.json" \
        "${agent_dir}/npm/package-lock.json" 2>/dev/null || true)"
    case "$listed" in
    *"npm:pi-mcp-adapter"*) adapter_listed=1 ;;
    esac
    if [ "${adapter_listed}" -eq 1 ] || [ -n "${adapter_manifests}" ]; then
        # pi remove は未登録のとき「No matching package found」で exit 1 を返すが、
        # マニフェストの掃除自体は行う。成否は終了コードではなく掃除後の実体で判定する。
        pi remove npm:pi-mcp-adapter 2>&1 || true
        adapter_manifests="$(grep -l -e '"pi-mcp-adapter"' -e '"node_modules/pi-mcp-adapter"' \
            "${agent_dir}/npm/package.json" \
            "${agent_dir}/npm/package-lock.json" 2>/dev/null || true)"
        if [ -n "${adapter_manifests}" ]; then
            echo "Failed to remove npm:pi-mcp-adapter from the pi managed npm manifest under ${agent_dir}/npm." >&2
            exit 1
        fi
        if ! after="$(pi list 2>&1)"; then
            echo "Failed to re-list pi extensions (pi list) after pi-mcp-adapter removal." >&2
            exit 1
        fi
        case "$after" in
        *"npm:pi-mcp-adapter"*)
            echo "npm:pi-mcp-adapter is still registered after removal." >&2
            exit 1
            ;;
        esac
    fi
    # pi remove はパッケージ登録を消すだけで、adapter が書き込んだ extensions の
    # -builtin:mcp は settings.json に残る。そのままだと組み込み MCP が無効のまま
    # なので、該当エントリだけを取り除く。他の extensions エントリは保持する。
    # Re-read after pi remove: keep the packages it just updated. The shared
    # helper validates again and stages a complete file, cleaning up on I/O error.
    if ! python3 "${WORKSPACE_ROOT}/.devcontainer/pi-provider-setup.py" --settings-clean "$agent_dir"; then
        echo "Failed to clean -builtin:mcp from ${agent_dir}/settings.json." >&2
        exit 1
    fi
}
remove_pi_mcp_adapter

step "Removing npm:pi-distill (distillation retired)"
# pi-distill は廃止する（#508）。~/.pi は bind mount なので、インストール対象から
# 外すだけでは既存環境の settings.json 登録は消えない。依存の
# pi-extensions-tool-display / pi-extensions-i18n は通常 pi-distill の npm 依存と
# してのみ入るが、単独登録された環境では一緒に外す。
remove_pi_distill() {
    local agent_dir listed
    local distill_manifests
    local distill_listed=0 helpers_listed=0

    # settings.json の packages と npm マニフェストは同じ agent directory を参照する。
    # settings の検査と同じ resolver を使う。~ と ~/ だけを HOME へ展開し、
    # ~user は Pi と同じく cwd 基準の literal パスとして扱う。
    if ! agent_dir="$(python3 "${WORKSPACE_ROOT}/.devcontainer/pi-provider-setup.py" --agent-dir && printf .)"; then
        echo "Failed to resolve the pi agent directory; aborting pi-distill removal." >&2
        exit 1
    fi
    # Strip only the CLI delimiter and sentinel, not newlines owned by the path.
    agent_dir="${agent_dir%$'\n'.}"
    if ! listed="$(pi list 2>&1)"; then
        echo "Failed to list pi extensions (pi list); aborting pi-distill removal." >&2
        exit 1
    fi
    # 一覧が綺麗でも pi 管理の npm マニフェストに残っていると
    # `pi update --extensions`（zsh の update() が実行する）で node_modules ごと
    # 復活する（pi-subagents 撤去の #289 と同じ穴）。
    distill_manifests="$(grep -l -e '"pi-distill"' -e '"node_modules/pi-distill"' \
        "${agent_dir}/npm/package.json" \
        "${agent_dir}/npm/package-lock.json" 2>/dev/null || true)"
    case "$listed" in
    *"npm:pi-distill"*) distill_listed=1 ;;
    esac
    case "$listed" in
    *"npm:pi-extensions-tool-display"*|*"npm:pi-extensions-i18n"*) helpers_listed=1 ;;
    esac
    if [ "${distill_listed}" -eq 0 ] && [ -z "${distill_manifests}" ] && [ "${helpers_listed}" -eq 0 ]; then
        return 0
    fi
    # pi remove は未登録のとき「No matching package found」で exit 1 を返すが、
    # マニフェストの掃除自体は行う。成否は終了コードではなく掃除後の実体で判定する。
    if [ "${distill_listed}" -eq 1 ] || [ -n "${distill_manifests}" ]; then
        pi remove npm:pi-distill 2>&1 || true
    fi
    case "$listed" in
    *"npm:pi-extensions-tool-display"*)
        pi remove npm:pi-extensions-tool-display 2>&1 || true ;;
    esac
    case "$listed" in
    *"npm:pi-extensions-i18n"*)
        pi remove npm:pi-extensions-i18n 2>&1 || true ;;
    esac
    distill_manifests="$(grep -l -e '"pi-distill"' -e '"node_modules/pi-distill"' \
        "${agent_dir}/npm/package.json" \
        "${agent_dir}/npm/package-lock.json" 2>/dev/null || true)"
    if [ -n "${distill_manifests}" ]; then
        echo "Failed to remove npm:pi-distill from the pi managed npm manifest under ${agent_dir}/npm." >&2
        exit 1
    fi
    if ! listed="$(pi list 2>&1)"; then
        echo "Failed to re-list pi extensions (pi list) after pi-distill removal." >&2
        exit 1
    fi
    case "$listed" in
    *"npm:pi-distill"*|*"npm:pi-extensions-tool-display"*|*"npm:pi-extensions-i18n"*)
        echo "npm:pi-distill or its bundled extensions are still registered after removal." >&2
        exit 1
        ;;
    esac
}
remove_pi_distill

step "Removing npm:pi-lens (Pi extension retired)"
# pi-lens は廃止する（#684）。得ているものに比べて、整形による差分の混入・
# トークンと起動時間・回避策の保守の負担が大きい。~/.pi は bind mount なので、
# インストール対象から外すだけでは既存環境の登録は消えない。pi remove は共有の
# node_modules/pi-lens も消すため、ほかのコンテナの Pi を止めてから作り直す。
remove_pi_lens() {
    local agent_dir listed lens_manifests
    local lens_listed=0

    # remove_pi_distill と同じく、マニフェストの検査先を pi の agent directory の解決にそろえる。
    if ! agent_dir="$(python3 "${WORKSPACE_ROOT}/.devcontainer/pi-provider-setup.py" --agent-dir && printf .)"; then
        echo "Failed to resolve the pi agent directory; aborting pi-lens removal." >&2
        exit 1
    fi
    # Strip only the CLI delimiter and sentinel, not newlines owned by the path.
    agent_dir="${agent_dir%$'\n'.}"
    if ! listed="$(pi list 2>&1)"; then
        echo "Failed to list pi extensions (pi list); aborting pi-lens removal." >&2
        exit 1
    fi
    # 一覧が綺麗でも pi 管理の npm マニフェストに残っていると、
    # `pi update --extensions` で node_modules ごと復活する（#289）。
    lens_manifests="$(grep -l -e '"pi-lens"' -e '"node_modules/pi-lens"' \
        "${agent_dir}/npm/package.json" \
        "${agent_dir}/npm/package-lock.json" 2>/dev/null || true)"
    case "$listed" in
    *"npm:pi-lens"*) lens_listed=1 ;;
    esac
    if [ "${lens_listed}" -eq 0 ] && [ -z "${lens_manifests}" ]; then
        return 0
    fi
    # pi remove は未登録のとき「No matching package found」で exit 1 を返すが、
    # マニフェストの掃除自体は行う。成否は終了コードではなく掃除後の実体で判定する。
    pi remove npm:pi-lens 2>&1 || true
    lens_manifests="$(grep -l -e '"pi-lens"' -e '"node_modules/pi-lens"' \
        "${agent_dir}/npm/package.json" \
        "${agent_dir}/npm/package-lock.json" 2>/dev/null || true)"
    if [ -n "${lens_manifests}" ]; then
        echo "Failed to remove npm:pi-lens from the pi managed npm manifest under ${agent_dir}/npm." >&2
        exit 1
    fi
    if ! listed="$(pi list 2>&1)"; then
        echo "Failed to re-list pi extensions (pi list) after pi-lens removal." >&2
        exit 1
    fi
    case "$listed" in
    *"npm:pi-lens"*)
        echo "npm:pi-lens is still registered after removal." >&2
        exit 1
        ;;
    esac
}
remove_pi_lens

step "Installing the pi extensions"
# Context7 は ctx7 CLI と find-docs スキルで使い、npm:@upstash/context7-pi は導入しない。共有の ~/.pi に残っていても、
# .pi/settings.json の autoload: false の項目でこのリポジトリでは読み込まない（#162）。~/.pi を共有するほかの
# リポジトリが導入し続けるため、撤去の処理には加えない。
for extension in \
    npm:@jc4649/notify \
    npm:@plannotator/pi-extension \
    npm:pi-safe-search \
    npm:pi-diet-ripgrep \
    git:github.com/obra/superpowers \
    npm:pi-simplify \
    npm:@howaboua/pi-skill-skill-creator; do
    if ! pi install --approve "${extension}"; then
        fail "Failed to install the pi extension ${extension}."
    fi
done

step "Placing ~/.pi/agent/models.json"
# models.json は bind mount した ~/.pi 側を正とし、無い場合のみ雛形を配置する。
# 毎回上書きすると、ホスト側で加えたモデル定義の変更がリビルドで失われる。
if ! mkdir -p "${HOME}/.pi/agent"; then
    fail "Failed to create ~/.pi/agent."
fi
if [ ! -f "${HOME}/.pi/agent/models.json" ]; then
    if ! cp .devcontainer/pi-models.json "${HOME}/.pi/agent/models.json"; then
        fail "Failed to place pi models.json."
    fi
fi

step "Placing the launchers (pigo / pigod / piccg / piccd / piga / pigs / pigl / pixg / pigemf / pigemp / pigema)"
# Pi ランチャーは ~/.local/bin に置く。ここは bind mount の
# 対象外でリビルドのたびに失われるため、models.json と違い毎回上書きで配置する。
if ! mkdir -p "${HOME}/.local/bin"; then
    fail "Failed to create ~/.local/bin."
fi
if ! install -m 0755 .devcontainer/pigo "${HOME}/.local/bin/pigo"; then
    fail "Failed to place pigo."
fi
if ! install -m 0755 .devcontainer/pigod "${HOME}/.local/bin/pigod"; then
    fail "Failed to place pigod."
fi
if ! install -m 0755 .devcontainer/piccg "${HOME}/.local/bin/piccg"; then
    fail "Failed to place piccg."
fi
if ! install -m 0755 .devcontainer/piccd "${HOME}/.local/bin/piccd"; then
    fail "Failed to place piccd."
fi
if ! install -m 0755 .devcontainer/piga "${HOME}/.local/bin/piga"; then
    fail "Failed to place piga."
fi
if ! install -m 0755 .devcontainer/pigs "${HOME}/.local/bin/pigs"; then
    fail "Failed to place pigs."
fi
if ! install -m 0755 .devcontainer/pigl "${HOME}/.local/bin/pigl"; then
    fail "Failed to place pigl."
fi
if ! install -m 0755 .devcontainer/pixg "${HOME}/.local/bin/pixg"; then
    fail "Failed to place pixg."
fi

if ! install -m 0755 .devcontainer/pigemf "${HOME}/.local/bin/pigemf"; then
    fail "Failed to place pigemf."
fi
if ! install -m 0755 .devcontainer/pigemp "${HOME}/.local/bin/pigemp"; then
    fail "Failed to place pigemp."
fi
if ! install -m 0755 .devcontainer/pigema "${HOME}/.local/bin/pigema"; then
    fail "Failed to place pigema."
fi

step "Writing the pi-superagents launcher configs"
# pi-superagents のランチャー別 model tier 設定を配置する。既存の config は
# 保持する。tier 表を変更したときは、リポジトリのルートで
# zsh scripts/setup_pi_superagents.zsh を実行して反映する。
if ! zsh scripts/setup_pi_superagents.zsh --if-absent; then
    fail "Failed to set up pi-superagents launcher configs."
fi

step "Installing the shared skills (herdr / find-skills)"
if ! npx -y skills add herdrdev/herdr --skill herdr -g -y -a claude-code -a pi; then
    fail "Failed to install the herdr skill."
fi
if ! npx -y skills add vercel-labs/skills@find-skills -g -y -a claude-code -a pi; then
    fail "Failed to install the find-skills skill."
fi

step "Installing Starship"
if ! (
    set -o pipefail
    curl -fsSL https://starship.rs/install.sh | sh -s -- -y
); then
    fail "Starship installation failed."
fi
if ! mkdir -p "${HOME}/.config"; then
    fail "Failed to create ~/.config."
fi
if ! cp .devcontainer/starship.toml "${HOME}/.config/starship.toml"; then
    fail "Failed to place the Starship config."
fi

step "Placing the Herdr helper scripts in ~/bin"
# herdrstart は PATH 上の herdr-status-updater（拡張子なし）を呼ぶ。
# 各エージェントは PATH 上の herdr-agent-task（拡張子なし）を呼ぶ。
# zshrc.txt がシェル起動のたびに間引いて呼ぶための実体も ~/bin に置く。
# if ! ( set -e; ... ) では条件式の内側で errexit が無効になるため、関数内の || return 1 で失敗を伝える。
place_herdr_helpers() {
    mkdir -p "${HOME}/bin" || return 1
    cp .devcontainer/herdr-git-status.bash "${HOME}/bin/herdr-git-status.bash" || return 1
    chmod +x "${HOME}/bin/herdr-git-status.bash" || return 1
    cp .devcontainer/herdr-status-updater.bash "${HOME}/bin/herdr-status-updater.bash" || return 1
    chmod +x "${HOME}/bin/herdr-status-updater.bash" || return 1
    cp .devcontainer/herdr-status-updater.bash "${HOME}/bin/herdr-status-updater" || return 1
    chmod +x "${HOME}/bin/herdr-status-updater" || return 1
    cp .devcontainer/herdr-agent-task.bash "${HOME}/bin/herdr-agent-task.bash" || return 1
    chmod +x "${HOME}/bin/herdr-agent-task.bash" || return 1
    cp .devcontainer/herdr-agent-task.bash "${HOME}/bin/herdr-agent-task" || return 1
    chmod +x "${HOME}/bin/herdr-agent-task" || return 1
    cp .devcontainer/cleanup-workspace.bash "${HOME}/bin/cleanup-workspace.bash" || return 1
    chmod +x "${HOME}/bin/cleanup-workspace.bash" || return 1
}
if ! place_herdr_helpers; then
    fail "Failed to place the Herdr helper scripts in ~/bin."
fi

step "Cleaning up stale workspace debris"
# コンテナ作成時点のディスクを圧迫する使い捨て debris を掃除する（詳細は
# cleanup-workspace.bash を参照）。定期的な再発防止は zshrc.txt 側の間引き実行が
# 担う。失敗しても以降の必須処理は続ける（唯一の意図的なベストエフォート）。
if ! bash .devcontainer/cleanup-workspace.bash; then
    warn "Workspace cleanup reported a problem; continuing."
fi

step "Appending the shell setup to ~/.zshrc"
# 各 CLI インストーラが ~/.zshrc へ PATH を追記した後に zshrc.txt を連結する。
# Herdr の導入が失敗しても alias・環境変数・PATH 補助を利用できるよう、
# 失敗時に exit する Herdr block より前で行う。
if ! cat .devcontainer/zshrc.txt >>${HOME}/.zshrc; then
    fail "Failed to append .devcontainer/zshrc.txt to ~/.zshrc."
fi

step "Installing Herdr"
if ! (
    set -o pipefail
    curl -fsSL https://herdr.dev/install.sh | sh
); then
    fail "Herdr installation failed."
fi
if ! mkdir -p "${HOME}/.config/herdr"; then
    fail "Failed to create the Herdr config directory."
fi
if [ ! -f "${HOME}/.config/herdr/config.toml" ]; then
    if ! cp .devcontainer/herdr.toml "${HOME}/.config/herdr/config.toml"; then
        fail "Failed to place the Herdr config."
    fi
fi
if ! command -v herdr >/dev/null 2>&1; then
    fail "Herdr installation completed without placing herdr on PATH."
fi
if ! herdr --version; then
    fail "Herdr version verification failed."
fi
