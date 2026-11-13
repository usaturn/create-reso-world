#!/bin/bash

set -u

# postCreate の出力は、途中でコンテナが止まると残らない。どのステップまで進んだかを
# 後から追えるよう、各ステップの開始を必ず1行で出し、失敗は ERROR 行を残して
# 打ち切る（2026-09-13 のリビルド中断インシデント）。継続してよい処理
# （flux-sdk の導入、同梱スキルの状態の表示と workspace cleanup）だけを明示的に続行させるため、スクリプト全体には set -e を
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
    "${HOME}/.cursor" \
    "${HOME}/.gemini" \
    "${HOME}/.gemini/antigravity-cli"; do
    if ! ensure_user_writable_dir "$dir"; then
        fail "Failed to prepare writable directory: ${dir}"
    fi
done

# 非対話のエージェントのランナー（tools/agent_runner）の個人設定。雛形を写すと雛形の変更が rebuild まで効かないので、
# 上書きの例だけの最小のファイルを置く（#167）。既存の設定（壊れた symlink も含む）は上書きしない。
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
    cp .devcontainer/agent-runner-personal.toml "$config" || return 1
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

step "Upgrading ca-certificates to the latest release"
# トラストストアの修正（eMudhra の中間CA の侵害、#291）は ca-certificates の更新で届く。タグを固定していないベースイメージでも、
# 古いイメージのキャッシュから作ると古いままなので、更新した索引の最新版へ上げる（入っていなければ入れる。--only-upgrade は
# 入っていないと何もせずに成功する）。後の step の HTTPS による導入も、新しいトラストストアで検証される。
# 確かめるのは .devcontainer/verify-ca-trust.bash（外部へ接続するので postCreate では実行しない）
upgrade_ca_certificates() {
    sudo apt-get install -y ca-certificates
}
if ! upgrade_ca_certificates; then
    fail "Upgrading ca-certificates failed."
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

step "Installing the ProtoFlux SDK (flux-sdk)"
# ResoLoop が検証している版に固定して入れる。版と導入後の確認は install_flux_sdk.bash にある（#251）。
# ProtoFlux を使わない作業には要らず、後から同じスクリプトで入れ直せるので、NuGet に届かないなどで失敗しても続ける
if ! bash .devcontainer/install_flux_sdk.bash; then
    warn "Installing the ProtoFlux SDK (flux-sdk) failed; continuing. Retry with: bash .devcontainer/install_flux_sdk.bash"
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

step "Installing Antigravity CLI"
if ! (
    set -o pipefail
    curl -fsSL https://antigravity.google/cli/install.sh | bash
); then
    fail "Antigravity CLI installation failed."
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
for marketplace in \
    anthropics/skills \
    anthropics/claude-plugins-official \
    addyosmani/web-quality-skills \
    dashed/claude-marketplace; do
    if ! claude plugin marketplace add "$marketplace"; then
        fail "Failed to add marketplace ${marketplace}."
    fi
done

# ローカルに残った古いカタログでのインストール失敗を防ぐ
if ! claude plugin marketplace update anthropic-agent-skills; then
    fail "Failed to update anthropic-agent-skills marketplace."
fi

# 既存の for plugin in ... done はこの後に残す
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

step "Installing the latest Context7 CLI (ctx7)"
# find-docs スキルが使う。最新版の導入と導入後の確認は install_ctx7.bash にある（#162・#290）
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
# ~/.pi は devcontainer.json で bind mount している。ホスト側に存在しない場合は
# Docker が root 所有で作成するため、以降の pi install が書き込めるよう所有権を直す。
if ! ensure_user_writable_dir "${HOME}/.pi"; then
    fail "Failed to prepare writable directory: ${HOME}/.pi."
fi
if ! npm install -g --ignore-scripts @earendil-works/pi-coding-agent; then
    fail "pi installation failed."
fi

step "Installing npm:@teelicht/pi-superagents"
# --approve は project trust の確認を自動承認する（.agents/skills があると対話プロンプトで止まる）
# 導入に失敗した場合と、導入後の一覧に無い場合は、失敗を成功扱いしない（fail-loud）。関数化は隔離テスト
# （test-pi-superagents.bash）が install_pi_extensions だけを取り出して fake pi で実行できるようにするため。
# 旧拡張（pi-subagents・pi-mcp-adapter・pi-distill・pi-lens）の自動撤去は #234 で外した。共有の ~/.pi に残って
# いれば、手で `pi remove npm:<名前>` する（.devcontainer/README.md）。
install_pi_extensions() {
    if ! pi install --approve npm:@teelicht/pi-superagents 2>&1; then
        echo "Failed to install npm:@teelicht/pi-superagents." >&2
        exit 1
    fi
    if ! after="$(pi list 2>&1)"; then
        echo "Failed to re-list pi extensions after install." >&2
        exit 1
    fi
    case "$after" in
    *"npm:@teelicht/pi-superagents"*)
        ;;
    *)
        echo "npm:@teelicht/pi-superagents is missing after install." >&2
        exit 1
        ;;
    esac
}
install_pi_extensions

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

step "Placing the launchers (pigo / pigod / piga / pigt / pidid / piaq / pigs / pigl / pixg / pigemf / pigemp / pigema / claude-alibaba-exec / claude-ollama-exec)"
# Pi ランチャーと claude-alibaba-exec・claude-ollama-exec は ~/.local/bin に置く。ここは bind mount の
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
if ! install -m 0755 .devcontainer/piga "${HOME}/.local/bin/piga"; then
    fail "Failed to place piga."
fi
if ! install -m 0755 .devcontainer/pigt "${HOME}/.local/bin/pigt"; then
    fail "Failed to place pigt."
fi
if ! install -m 0755 .devcontainer/pidid "${HOME}/.local/bin/pidid"; then
    fail "Failed to place pidid."
fi
if ! install -m 0755 .devcontainer/piaq "${HOME}/.local/bin/piaq"; then
    fail "Failed to place piaq."
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
if ! install -m 0755 .devcontainer/claude-alibaba-exec "${HOME}/.local/bin/claude-alibaba-exec"; then
    fail "Failed to place claude-alibaba-exec."
fi
if ! install -m 0755 .devcontainer/claude-ollama-exec "${HOME}/.local/bin/claude-ollama-exec"; then
    fail "Failed to place claude-ollama-exec."
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
    local cleanup_helper="${HOME}/bin/cleanup-workspace.bash"
    # 既存のコピーは、実体への絶対 symlink に置き換える。宛先が通常のディレクトリなら、
    # その中へリンクを作らず失敗させる。cleanup 本体は git モード 100755 なので、
    # リンク先の chmod はしない。
    if [ -d "$cleanup_helper" ] && [ ! -L "$cleanup_helper" ]; then
        return 1
    fi
    ln -sfn "${WORKSPACE_ROOT}/.devcontainer/cleanup-workspace.bash" "$cleanup_helper" || return 1
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
