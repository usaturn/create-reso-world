#!/bin/bash

set -u

# DeepSeek Harness
readonly DSH_VERSION="0.1.5-rc.1"
readonly DSH_COMMANDCODE_PROVIDER_VERSION="0.10.6"

# postCreate の出力は、途中でコンテナが止まると残らない。どのステップまで進んだかを
# 後から追えるよう、各ステップの開始を必ず1行で出し、失敗は ERROR 行を残して
# 打ち切る（2026-09-13 のリビルド中断インシデント）。継続してよい処理
# （workspace cleanup）だけを明示的に続行させるため、スクリプト全体には set -e を
# 付けない。
readonly STEP_TOTAL=24
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
# 保証する（#296）。~/.claude.json はファイル mount のため対象外。
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
    "${HOME}/.claude" \
    "${HOME}/.pi" \
    "${HOME}/.dsh" \
    "${HOME}/.cursor"; do
    if ! ensure_user_writable_dir "$dir"; then
        fail "Failed to prepare writable directory: ${dir}"
    fi
done

step "Rewriting the apt sources to HTTPS and updating the package index"
if ! sudo perl -pi -e 's@http://archive\.ubuntu\.com@https://archive.ubuntu.com@g; s@http://security\.ubuntu\.com@https://security.ubuntu.com@g' /etc/apt/sources.list.d/ubuntu.sources; then
    fail "Failed to rewrite /etc/apt/sources.list.d/ubuntu.sources."
fi
if ! sudo apt update; then
    fail "apt update failed."
fi

step "Installing the base packages"
if ! sudo apt update; then
    fail "apt update failed before installing the base packages."
fi
if ! sudo apt install -y vim tig ripgrep fzf bubblewrap libglib2.0-0t64 blender; then
    fail "apt install of the base packages failed."
fi

step "Installing or updating the latest ResoLoop tool"
export PATH="${HOME}/.dotnet/tools:${PATH}"
if ! bash .devcontainer/install_resoloop.bash; then
    fail "ResoLoop installation or update failed."
fi

step "Verifying the Resonite development toolchain"
if ! bash .devcontainer/verify-resonite-tooling.bash; then
    fail "Resonite development toolchain verification failed."
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
for plugin in \
    example-skills@anthropic-agent-skills \
    web-quality-skills@addy-web-quality-skills \
    ripgrep@alberto-marketplace; do
    if ! claude plugin install "$plugin"; then
        fail "Installing plugin ${plugin} failed."
    fi
done

step "Installing the Cursor CLI"
# ~/.local/share/cursor-agent は devcontainer.json で bind mount している。ホスト側に
# 存在しない場合は Docker が root 所有で作成するため、所有権を直す（~/.pi と同じ対応）。
# 認証情報と設定が入る ~/.cursor は既に bind mount 済み。
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
        "${HOME}/.pi/agent/npm/package.json" \
        "${HOME}/.pi/agent/npm/package-lock.json" 2>/dev/null || true)"
    # 3) 登録済み、またはマニフェストに残っていれば削除する。pi remove は未登録の
    #    とき「No matching package found」で exit 1 を返すが、マニフェストの掃除自体は
    #    行う。そのため成否は終了コードではなく、掃除後の実体で判定する。
    if [ "${legacy_listed}" -eq 1 ] || [ -n "${legacy_manifests}" ]; then
        pi remove npm:pi-subagents 2>&1 || true
        # 存在しないパスが混ざると grep は一致していても exit 2 になるため、
        # 終了コードではなく一致したファイルの有無で判定する。
        legacy_manifests="$(grep -l -e '"pi-subagents"' -e '"node_modules/pi-subagents"' \
            "${HOME}/.pi/agent/npm/package.json" \
            "${HOME}/.pi/agent/npm/package-lock.json" 2>/dev/null || true)"
        if [ -n "${legacy_manifests}" ]; then
            echo "Failed to remove npm:pi-subagents from the pi managed npm manifest under ${HOME}/.pi/agent/npm." >&2
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

step "Installing the pi extensions"
for extension in \
    npm:pi-distill \
    npm:@jc4649/notify \
    npm:@upstash/context7-pi \
    npm:pi-safe-search \
    npm:pi-diet-ripgrep \
    git:github.com/obra/superpowers \
    npm:pi-mcp-adapter \
    npm:pi-lens \
    npm:pi-simplify \
    npm:@howaboua/pi-skill-skill-creator; do
    if ! pi install --approve "${extension}"; then
        fail "Failed to install the pi extension ${extension}."
    fi
done
if ! python3 scripts/setup_pi_tool_display.py; then
    fail "Failed to disable the pi tool-display Bash override."
fi

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

step "Placing the launchers (pigo / pigod / pigou / piccg / piccd / piga / pigs / pigl / pixg)"
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
if ! install -m 0755 .devcontainer/pigou "${HOME}/.local/bin/pigou"; then
    fail "Failed to place pigou."
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

step "Writing the pi-superagents launcher configs"
# pi-superagents のランチャー別 model tier 設定を配置する。既存の config は
# 保持する。tier 表を変更したときは、リポジトリのルートで
# zsh scripts/setup_pi_superagents.zsh を実行して反映する。
if ! zsh scripts/setup_pi_superagents.zsh --if-absent; then
    fail "Failed to set up pi-superagents launcher configs."
fi

step "Installing DeepSeek Harness"
# DeepSeek Harness（dsh）は pi と並行して使う（#282）。dsh の plugin 管理は PATH 上の
# pnpm を直接 spawn するため、devcontainer.json の Node feature で pnpm を明示導入
# している（pnpmVersion "none" は導入省略）。
install_deepseek_harness() {
    echo "Installing DeepSeek Harness ${DSH_VERSION}..."
    if ! npm install -g "@deepseek-ai/dsh@${DSH_VERSION}"; then
        echo "DeepSeek Harness installation failed." >&2
        exit 1
    fi
    if ! command -v dsh >/dev/null 2>&1; then
        echo "DeepSeek Harness installation completed without placing dsh on PATH." >&2
        exit 1
    fi
    # 想定と違う版が入ると Developer Preview の仕様差を踏むため fail-loud にする。
    if ! dsh_version="$(dsh --version)"; then
        echo "dsh --version failed." >&2
        exit 1
    fi
    if [ "${dsh_version//[[:space:]]/}" != "${DSH_VERSION}" ]; then
        echo "Unexpected dsh version: ${dsh_version} (expected ${DSH_VERSION})." >&2
        exit 1
    fi
    # ~/.dsh は devcontainer.json で bind mount している。ホスト側に存在しない場合は
    # Docker が root 所有で作成するため、以降の dsh が書き込めるよう所有権を直す。
    ensure_user_writable_dir "${HOME}/.dsh" || {
        echo "Failed to prepare writable directory: ${HOME}/.dsh." >&2
        exit 1
    }
    # settings.yaml は bind mount 側を正とし、無い場合のみ雛形を配置する。
    # 毎回上書きすると、Web UI や利用者が更新した設定がリビルドで失われる。
    if [ ! -f "${HOME}/.dsh/settings.yaml" ]; then
        if ! cp .devcontainer/dsh-settings.yaml "${HOME}/.dsh/settings.yaml"; then
            echo "Failed to place dsh settings.yaml." >&2
            exit 1
        fi
    fi
    # cordis.patch.yml も settings.yaml と同じく無い場合のみ配置する。plugin の
    # 無効化を settings.yaml に書いても効かないため、この patch 層に置く（理由は
    # dsh-cordis.patch.yml のコメントを参照）。
    if [ ! -f "${HOME}/.dsh/cordis.patch.yml" ]; then
        if ! cp .devcontainer/dsh-cordis.patch.yml "${HOME}/.dsh/cordis.patch.yml"; then
            echo "Failed to place dsh cordis.patch.yml." >&2
            exit 1
        fi
    fi
    # Command Code plugin は web profile にだけ導入する。plugin add は導入済みなら
    # lockfile 一致で成功する（冪等）ため、rebuild のたびに実行して欠落を検出する。
    if ! dsh plugin --profile web add "@mars-sea/dsh-commandcode-provider@${DSH_COMMANDCODE_PROVIDER_VERSION}"; then
        echo "Failed to add the Command Code provider to the dsh web profile." >&2
        exit 1
    fi
    # 既に別内容の cordis.patch.yml を持つ環境では無効化が入らない。効いていない
    # 設定を silent に通すと「設定したつもり」を再生産するため、解決後の構成を見て
    # fail-loud にする。
    if ! dsh_config="$(dsh --profile web --dump-config)"; then
        echo "dsh --profile web --dump-config failed." >&2
        exit 1
    fi
    # 当該 entry のブロック内だけを見る。次の top-level entry（行頭の "- "）で
    # 抜けるので、隣の plugin の enabled で通ってしまうことがない。
    if ! printf '%s\n' "${dsh_config}" | awk '
        /^- id: plugin-package-inventory-deepseek$/ { inside = 1; next }
        inside && /^- / { inside = 0 }
        inside && /^[[:space:]]+enabled: false$/ { found = 1 }
        END { exit found ? 0 : 1 }
    '; then
        echo "dsh still enables plugin-package-inventory-deepseek; check ${HOME}/.dsh/cordis.patch.yml." >&2
        exit 1
    fi
}
install_deepseek_harness

step "Installing the shared skills (herdr / find-skills)"
if ! npx -y skills add herdrdev/herdr --skill herdr -g -y -a claude-code -a pi; then
    fail "Failed to install the herdr skill."
fi
if ! npx -y skills add vercel-labs/skills@find-skills -g -y -a claude-code -a pi; then
    fail "Failed to install the find-skills skill."
fi

step "Installing uv"
if ! (
    set -o pipefail
    curl -LsSf https://astral.sh/uv/install.sh | sh
); then
    fail "uv installation failed."
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
# zshrc.txt がシェル起動のたびに間引いて呼ぶための実体も ~/bin に置く（#146）。
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
if ! mkdir -p "${HOME}/.local/bin"; then
    fail "Failed to create ~/.local/bin."
fi
export PATH="${HOME}/.local/bin:${PATH}"

step "Cleaning up stale workspace debris"
# コンテナ作成時点のディスクを圧迫する使い捨て debris を掃除する（#146。詳細は
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

