#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export WORKSPACE_ROOT="$REPO_ROOT"
HELPER="${REPO_ROOT}/.devcontainer/pi-superagents-exec.zsh"
TEST_ROOT="$(mktemp -d)"
ZSH_BIN="$(command -v zsh)"
trap 'rm -rf -- "${TEST_ROOT:?}"' EXIT

# 呼び出し側の PI_CODING_AGENT_DIR で結果が変わらないよう、スイート全体で
# 無効化する。必要なテストは呼び出し単位で明示的に設定する。
unset PI_CODING_AGENT_DIR

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

assert_eq() {
    local actual="$1" expected="$2" msg="$3"
    [ "$actual" = "$expected" ] || fail "$msg: expected='$expected' actual='$actual'"
}

assert_contains() {
    local haystack="$1" needle="$2" msg="$3"
    case "$haystack" in
        *"$needle"*) ;;
        *) fail "$msg: '$needle' not found in '$haystack'" ;;
    esac
}

# ランチャー用の一時 HOME を作る。config を置くかどうかを引数で選ぶ。
# config はヘルパの起動前の検査を通るよう cheap / balanced / max をそろえる（cheap は文字列の形）。
make_home() {
    local name="$1" with_config="$2"
    local home="${TEST_ROOT}/${name}"
    mkdir -p "${home}/.pi/agent/extensions/subagent"
    if [ "$with_config" = "with-config" ]; then
        mkdir -p "${home}/.pi/agent/extensions/subagent.d/${name}"
        printf '%s\n' \
            '{"superagents":{"modelTiers":{"cheap":"test/cheap","balanced":{"model":"test/balanced","thinking":"high"},"max":{"model":"test/max"}}}}' \
            > "${home}/.pi/agent/extensions/subagent.d/${name}/config.json"
    fi
    printf '%s' "$home"
}

# OAuth で起動前に確認するランチャー（openai-codex・xai）をまとめて起動できる auth.json を置く。
write_oauth_auth() {
    local home="$1"
    mkdir -p "${home}/.pi/agent"
    printf '%s\n' \
        '{"openai-codex":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999},"xai":{"type":"oauth","access":"test-access","refresh":"test-refresh","expires":9999999999999}}' \
        > "${home}/.pi/agent/auth.json"
}

# ヘルパを source して pi_superagents_exec を dry-run で呼ぶ。
run_helper() {
    local home="$1" launcher="$2"; shift 2
    env HOME="$home" PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
        "${ZSH_BIN}" -c "source '${HELPER}'; pi_superagents_exec '${launcher}' \"\$@\"" _ "$@"
}

# 防ぐ損害: tier の bind 先が PI_CODING_AGENT_DIR に引きずられると、拡張が読む ~/.pi/agent/extensions/subagent に
# 重ならず、tier が黙って効かない（モデル割当が変わる。エラーにならない）。
test_bind_target_ignores_pi_coding_agent_dir() {
    # 拡張は os.homedir() を直接見るので、PI_CODING_AGENT_DIR を設定しても
    # bind 先は HOME 基準でなければならない。
    local home out
    home="$(make_home pigo with-config)"
    out="$(env PI_CODING_AGENT_DIR="${TEST_ROOT}/elsewhere" \
        HOME="$home" PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
        "${ZSH_BIN}" -c "source '${HELPER}'; pi_superagents_exec pigo")"
    assert_contains "$out" "${home}/.pi/agent/extensions/subagent" "bind target must follow HOME"
    # 重ね先 (argv[8]) を HOME 基準の共有ディレクトリに位置で固定する。
    assert_eq "$(printf '%s\n' "$out" | sed -n 8p)" \
        "${home}/.pi/agent/extensions/subagent" "bind dst must equal HOME-based shared dir"
    case "$out" in
        *"${TEST_ROOT}/elsewhere"*) fail "bind target must not follow PI_CODING_AGENT_DIR" ;;
    esac
}

# 防ぐ損害: config が無いまま（fail-open で）tier 無しに起動すると、気付かないままモデル割当が変わる。
# 代表はヘルパ。各ランチャーは同じヘルパを使う。
test_missing_config_fails_closed() {
    local home status out
    home="$(make_home pigod without-config)"
    set +e
    out="$(run_helper "$home" pigod 2>&1)"
    status=$?
    set -e
    assert_eq "$status" "1" "missing config must exit 1"
    assert_contains "$out" "setup_pi_superagents.zsh" "must point at the setup script"
    assert_contains "$out" "pigod" "must name the launcher"
}

# 防ぐ損害: pi-superagents は欠けた tier を同梱の既定 model（1.14.4 の balanced は opencode-go/glm-5.3-flash）で埋める。
# 検査が tier の欠けや provider の無い model を通すと、利用者が選んでいない provider へ子の要求が黙って送られる（#307）。
# 代表はヘルパ。各ランチャーは同じヘルパを使う。そろった設定（make_home。cheap は文字列の形）は通す。
test_incomplete_tiers_fail_closed() {
    local home config status out
    home="$(make_home pigs with-config)"
    config="${home}/.pi/agent/extensions/subagent.d/pigs/config.json"
    out="$(run_helper "$home" pigs)"
    assert_eq "$(printf '%s\n' "$out" | sed -n 1p)" "bwrap" "complete tiers must reach bwrap"

    printf '%s\n' '{"superagents":{"modelTiers":{"cheap":{"model":"test/cheap"},"max":{"model":"test/max"}}}}' > "$config"
    set +e
    out="$(run_helper "$home" pigs 2>"${TEST_ROOT}/tiers.err")"
    status=$?
    set -e
    assert_eq "$status" "1" "missing balanced tier must exit 1"
    assert_eq "$out" "" "missing balanced tier must not reach bwrap"
    assert_contains "$(<"${TEST_ROOT}/tiers.err")" "[pigs]" "must name the launcher"
    assert_contains "$(<"${TEST_ROOT}/tiers.err")" "$config" "must name the config"

    printf '%s\n' '{"superagents":{"modelTiers":{"cheap":"test/cheap","balanced":{"model":"glm-5.3-flash"},"max":"test/max"}}}' > "$config"
    set +e
    out="$(run_helper "$home" pigs 2>/dev/null)"
    status=$?
    set -e
    assert_eq "$status" "1" "a tier model without provider must exit 1"
    assert_eq "$out" "" "a tier model without provider must not reach bwrap"
}

# 防ぐ損害: bwrap が無いのに止まらないと、サンドボックス（mount namespace による分離）無しで Pi が起動する。
test_missing_bwrap_fails_closed() {
    # command -v bwrap を失敗させるため PATH を空にする。zsh 自体は絶対パスで
    # 起動するので、PATH 制限は zsh プロセス側だけに効く。
    local home status out
    home="$(make_home piccg with-config)"
    mkdir -p "${TEST_ROOT}/emptybin"
    set +e
    out="$(env HOME="$home" PATH="${TEST_ROOT}/emptybin" \
        PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
        "${ZSH_BIN}" -c "source '${HELPER}'; pi_superagents_exec piccg" 2>&1)"
    status=$?
    set -e
    assert_eq "$status" "1" "missing bwrap must exit 1"
    assert_contains "$out" "bwrap" "must name bwrap"
}
# ------------------------------------------------------------------ dry-run 判定
# PI_SUPERAGENTS_LAUNCHER_DRY_RUN が文字列 "1" のときだけ argv 表示になり、
# それ以外（未設定 / "" / "0" / "false"）は本当に bwrap を起動する。本当の
# bwrap を起動しないよう、PATH 先頭に呼び出しを記録する fake bwrap を置く。
BWRAP_SHIM_DIR="${TEST_ROOT}/bwrapbin"
FAKE_BWRAP_LOG="${TEST_ROOT}/bwrap-state/log"

make_bwrap_shim() {
    mkdir -p "$BWRAP_SHIM_DIR" "${TEST_ROOT}/bwrap-state"
    cat > "${BWRAP_SHIM_DIR}/bwrap" <<'BWRAP_SHIM_EOF'
#!/bin/bash
printf 'bwrap invoked with %s args\n' "$#" >> "${FAKE_BWRAP_LOG:?}"
printf '%s\n' "$@" >> "${FAKE_BWRAP_LOG:?}"
BWRAP_SHIM_EOF
    chmod +x "${BWRAP_SHIM_DIR}/bwrap"
}

# ヘルパを指定の dry-run 値で呼ぶ。PATH 先頭に fake bwrap を載せ、実環境の
# bwrap に影響を与えない。
run_helper_dry_run() {
    local home="$1" launcher="$2" drv="$3"; shift 3
    env HOME="$home" PATH="${BWRAP_SHIM_DIR}:${PATH}" FAKE_BWRAP_LOG="$FAKE_BWRAP_LOG" \
        PI_SUPERAGENTS_LAUNCHER_DRY_RUN="$drv" \
        "${ZSH_BIN}" -c "source '${HELPER}'; pi_superagents_exec '${launcher}' \"\$@\"" _ "$@"
}

# 防ぐ損害: dry-run の argv と実際に bwrap へ渡る argv が食い違うと、argv を見るほかの検査が意味を失い、
# 通るのに実際は違う結果になる。=0 で exec されることも兼ねる。
test_actual_and_dry_run_argv_match() {
    local home out expected
    local -a command_args
    home="$(make_home argv-match with-config)"
    make_bwrap_shim
    rm -f -- "${FAKE_BWRAP_LOG:?}"
    out="$(run_helper "$home" argv-match --session 'session with spaces.jsonl' -- 'message with spaces')"
    mapfile -t command_args <<< "$out"
    expected="$(printf 'bwrap invoked with %s args\n' "$((${#command_args[@]} - 1))"; \
        printf '%s\n' "${command_args[@]:1}")"
    run_helper_dry_run "$home" argv-match 0 --session 'session with spaces.jsonl' -- 'message with spaces'
    assert_eq "$(<"$FAKE_BWRAP_LOG")" "$expected" "actual and dry-run must use identical argv"
}

CONFIG_DIR="${REPO_ROOT}/.devcontainer/pi-superagents"

# ランチャーは .devcontainer/pi-superagents/<launcher>.json の tier 設定と 1 対 1 に対応する。
# 一覧をテストへ書き写さず、設定ファイルから導く。
mapfile -t LAUNCHERS < <(find "$CONFIG_DIR" -maxdepth 1 -name '*.json' -printf '%f\n' \
    | sed 's/\.json$//' | LC_ALL=C sort)
[ "${#LAUNCHERS[@]}" -gt 0 ] || fail "no launcher configs in ${CONFIG_DIR}"

# ランチャーは install 後 ~/.local/bin に置かれるが、テストはリポジトリ内の
# 元ファイルを直接叩く。ヘルパの探索がリポジトリ相対で解決できることも同時に見る。
run_launcher() {
    local home="$1" launcher="$2"; shift 2
    local pi_path="$PATH"
    case "$launcher" in
        pigt|pidid) model_home "$launcher" >/dev/null; pi_path="${MODEL_SHIM}/bin:${PATH}" ;;
    esac
    env HOME="$home" PATH="$pi_path" \
        PI_CODING_AGENT_DIR="${home}/.pi/agent" \
        COMMANDCODE_API_KEY="dummy-for-dry-run" \
        OPENCODE_API_KEY="dummy-for-dry-run" \
        DEEPINFRA_TOKEN="dummy-for-dry-run" \
        PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 \
        zsh "${REPO_ROOT}/.devcontainer/${launcher}" "$@"
}

# dry-run 出力から pi へ渡る引数だけを取り出す（"--" の次の "pi" より後ろ）。
pi_args_of() {
    printf '%s\n' "$1" | awk 'seen { print } $0 == "pi" { seen = 1 }'
}

# 防ぐ損害: 各ランチャーが別ランチャーの tier 設定を重ねても起動は成功し、モデル割当（費用・能力）が黙って変わる。
# 各ランチャーは自分の tier 設定を共有ディレクトリへ重ねて Pi を起動する。
# bind 元・重ね先は --bind の直後の 2 要素で見る（部分一致だと重ね先が bind 元の
# 部分文字列に化けて通るため）。
test_launchers_wrap_pi_with_their_own_config() {
    local launcher home out
    local -a argv
    local i bind_at
    for launcher in "${LAUNCHERS[@]}"; do
        home="$(make_home "$launcher" with-config)"
        write_oauth_auth "$home"
        out="$(run_launcher "$home" "$launcher")"
        mapfile -t argv <<< "$out"
        assert_eq "${argv[0]}" "bwrap" "${launcher} argv[0]"
        bind_at=""
        for i in "${!argv[@]}"; do
            if [ "${argv[$i]}" = "--bind" ]; then
                bind_at="$i"
                break
            fi
        done
        [ -n "$bind_at" ] || fail "${launcher} must pass --bind to bwrap"
        assert_eq "${argv[$((bind_at + 1))]}" \
            "${home}/.pi/agent/extensions/subagent.d/${launcher}" "${launcher} bind src"
        assert_eq "${argv[$((bind_at + 2))]}" \
            "${home}/.pi/agent/extensions/subagent" "${launcher} bind dst"
    done
}

# <option> <args...>: args の中で option の直後にある値を出す。
option_value() {
    local option="$1"
    shift
    while [ "$#" -gt 1 ]; do
        if [ "$1" = "$option" ]; then
            printf '%s\n' "$2"
            return 0
        fi
        shift
    done
    return 1
}

# Pi に google-vertex を渡すランチャーだけが auth.json の読み取り専用 overlay を重ねる。
# helper の Vertex ランチャーの一覧へ登録し忘れると、保存済みの Vertex key や OAuth が
# overlay なしで Pi に渡る。bwrap 側の引数（"pi" の行より前）だけを見る。
test_only_vertex_launchers_overlay_auth() {
    local launcher home out provider overlay
    local -a own
    for launcher in "${LAUNCHERS[@]}"; do
        home="$(make_home "$launcher" with-config)"
        write_oauth_auth "$home"
        out="$(run_launcher "$home" "$launcher")"
        mapfile -t own < <(pi_args_of "$out")
        provider="$(option_value --provider "${own[@]}")" || provider=""
        overlay=0
        if printf '%s\n' "$out" | awk '$0 == "pi" { exit } $0 == "--ro-bind-data" { found = 1 } END { exit !found }'; then
            overlay=1
        fi
        if [ "$provider" = google-vertex ]; then
            assert_eq "$overlay" 1 "${launcher} passes google-vertex to Pi and must overlay auth.json"
        else
            assert_eq "$overlay" 0 "${launcher} does not use google-vertex and must not overlay auth.json"
        fi
    done
}

SETUP="${REPO_ROOT}/scripts/setup_pi_superagents.zsh"

run_setup() {
    local home="$1"; shift
    env HOME="$home" PATH="${MODEL_SHIM}/bin:${PATH}" zsh "$SETUP" "$@"
}

# 固定時刻の date shim。PATH の先頭に載せて setup_pi_superagents.zsh から見える
# ようにする。実時刻に依存せず、同一 "秒" での退避衝突を再現できるようにする。
DATE_SHIM_DIR="${TEST_ROOT}/dateshim"

make_date_shim() {
    local ts="$1"
    mkdir -p "$DATE_SHIM_DIR"
    cat > "${DATE_SHIM_DIR}/date" <<DATE_SHIM_EOF
#!/bin/bash
if [ "\$1" = "+%Y%m%d-%H%M%S" ]; then
    printf '%s\n' '$ts'
    exit 0
fi
exec /usr/bin/date "\$@"
DATE_SHIM_EOF
    chmod +x "${DATE_SHIM_DIR}/date"
}

# date shim を PATH に載せて setup を実行する。
run_setup_shim() {
    local home="$1"; shift
    env HOME="$home" PATH="${DATE_SHIM_DIR}:${MODEL_SHIM}/bin:${PATH}" zsh "$SETUP" "$@"
}

# 防ぐ損害: 利用者が編集した config を退避せず上書きする、同一秒の退避で前の世代を上書きする、のどちらも
# 気付けないデータ消失（利用者の tier 編集）になる。
test_setup_preserves_prior_generation_on_name_collision() {
    # 固定時刻の date shim で「同一秒」の退避名衝突を作る。内容の異なる config を
    # 2 回退避させ、2 世代が別ファイル (.bak.<ts> と .bak.<ts>.1) に残り、
    # それぞれの世代の内容が上書きされず保存されることを内容まで検証する。
    local ts home config dir gen1 gen2 backups base
    ts='20260912-094438'
    make_date_shim "$ts"
    home="${TEST_ROOT}/setup-collision"
    mkdir -p "$home"
    run_setup_shim "$home" >/dev/null
    dir="${home}/.pi/agent/extensions/subagent.d/pigo"
    config="${dir}/config.json"
    gen1='{"superagents":{"modelTiers":{"gen":"one"}}}'
    gen2='{"superagents":{"modelTiers":{"gen":"two"}}}'
    printf '%s\n' "$gen1" > "$config"
    run_setup_shim "$home" >/dev/null
    printf '%s\n' "$gen2" > "$config"
    run_setup_shim "$home" >/dev/null

    backups="$(find "$dir" -name 'config.json.bak.*' | sort)"
    assert_eq "$(printf '%s\n' "$backups" | wc -l)" "2" \
        "two generations must be preserved, not overwritten"
    base="config.json.bak.${ts}"
    assert_contains "$backups" "${base}" "generation 1 must keep the base name"
    assert_contains "$backups" "${base}.1" "generation 2 must be saved as .1 on collision"
    grep -q '"gen":"one"' "${dir}/${base}" \
        || fail "generation 1 content must be preserved in ${base}"
    grep -q '"gen":"two"' "${dir}/${base}.1" \
        || fail "generation 2 content must be preserved in ${base}.1"
}

# 防ぐ損害: rebuild のたびに --if-absent で呼ばれる。壊れると rebuild で利用者の tier 編集が（退避も無く）消える。
test_setup_if_absent_preserves_user_edits() {
    local home config
    home="${TEST_ROOT}/setup-if-absent"
    mkdir -p "$home"
    run_setup "$home" >/dev/null
    config="${home}/.pi/agent/extensions/subagent.d/pidid/config.json"
    mkdir -p "${config%/*}"
    printf '{"superagents":{"modelTiers":{"cheap":{"model":"x/y","thinking":"max"}}}}\n' > "$config"
    printf '# stale helper\n' > "${home}/.local/bin/pi-superagents-exec.zsh"
    env HOME="$home" PATH="${MODEL_SHIM}/bin:${PATH}" DEEPINFRA_TOKEN="dummy-for-setup" \
        zsh "${REPO_ROOT}/scripts/setup_pi.zsh" >/dev/null
    grep -q '"x/y"' "$config" || fail "--if-absent must not overwrite an existing config"
    cmp -s "$HELPER" "${home}/.local/bin/pi-superagents-exec.zsh" \
        || fail "--if-absent must refresh the helper while preserving configs"
}

# 防ぐ損害: ランチャーを通さない Pi（素の pi、Herdr の復元による再開）は bwrap の mount が無く、共有の bind 先を読む。
# そこに停止用の設定が無いと、pi-superagents は同梱の既定 model（opencode-go/glm-5.3-flash など）の子を黙って
# 動かす（#307）。既存の共有設定を退避せずに置き換えると利用者の設定を失う。rebuild の経路（--if-absent）を代表にする。
# 通る例: 停止用のキーが残る設定（拡張の移行処理が書き足したもの）は置き換えない。ランチャーの設定は止めない。
SHARED_GUARD_KEY=launcherRequired_doNotRemove_restartPiViaLauncher
test_setup_guards_shared_bind_target() {
    local home shared ext out
    local -a backups
    home="${TEST_ROOT}/setup-shared-guard"
    shared="${home}/.pi/agent/extensions/subagent"
    mkdir -p "$shared"
    printf '%s\n' '{"superagents":{"modelTiers":{"balanced":{"model":"opencode-go/glm-5.3-flash","thinking":"high"}}}}' \
        > "${shared}/config.json"
    cp "${shared}/config.json" "${TEST_ROOT}/shared-original.json"
    run_setup "$home" --if-absent >/dev/null
    mapfile -t backups < <(find "$shared" -name 'config.json.bak.*')
    assert_eq "${#backups[@]}" "1" "the existing shared config must be backed up once"
    cmp -s "${backups[0]}" "${TEST_ROOT}/shared-original.json" || fail "the backup must keep the original bytes"
    node -e 'process.exit(Object.hasOwn(JSON.parse(require("node:fs").readFileSync(process.argv[1], "utf8")), process.argv[2]) ? 0 : 1)' \
        "${shared}/config.json" "$SHARED_GUARD_KEY" || fail "the shared config must carry the guard key"

    # 拡張の移行処理は読み込みのたびに superagents を書き足す。その代わりに書き足してから setup をやり直す。
    node -e 'const fs = require("node:fs"), f = process.argv[1], c = JSON.parse(fs.readFileSync(f, "utf8"));
c.superagents = {makeSuperpowersSkillsOptInOnly: true}; fs.writeFileSync(f, JSON.stringify(c, null, 2) + "\n");' \
        "${shared}/config.json"
    cp "${shared}/config.json" "${TEST_ROOT}/shared-migrated.json"
    run_setup "$home" --if-absent >/dev/null
    assert_eq "$(find "$shared" -name 'config.json.bak.*' | wc -l)" "1" "a guarded shared config must not be backed up again"
    cmp -s "${shared}/config.json" "${TEST_ROOT}/shared-migrated.json" || fail "a guarded shared config must be kept as is"

    # 停止の効き目は、導入済みの拡張の設定の読み込みで確かめる。Node は node_modules の下の .ts の型除去を
    # 拒むので、src を一時の場所へ複製して読む。拡張が無い環境（postCreate の前）だけ省く。
    ext="${HOME}/.pi/agent/npm/node_modules/@teelicht/pi-superagents"
    if [ ! -f "${ext}/src/extension/config-store.ts" ]; then
        printf 'SKIP: pi-superagents is not installed at %s; guard effect not checked\n' "$ext" >&2
        return 0
    fi
    mkdir -p "${TEST_ROOT}/superagents-copy"
    cp -r "${ext}/src" "${ext}/default-config.json" "${ext}/package.json" "${TEST_ROOT}/superagents-copy/"
    out="$(node --input-type=module - "${TEST_ROOT}/superagents-copy" "$shared" \
        "${home}/.pi/agent/extensions/subagent.d/pigs" 2>/dev/null <<'JS'
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [ext, ...dirs] = process.argv.slice(2);
const {loadRuntimeConfigState} = await import(pathToFileURL(path.join(ext, 'src/extension/config-store.ts')).href);
console.log(dirs.map(dir => loadRuntimeConfigState(ext, dir, []).blocked).join(' '));
JS
)" || fail "the installed pi-superagents config loader must be readable"
    assert_eq "$out" "true false" "the guard must disable pi-superagents, the launcher config must not"
}

# 防ぐ損害: ランチャーの中では bwrap が共有の bind 先にランチャーのディレクトリを重ねる。そこで setup を実行すると、
# 停止用の設定がランチャーの設定を置き換え、本物の共有の bind 先は守られないまま成功と表示される（#307 のレビュー）。
# 本物の bwrap で同じ mount を作り、何も書かずに止まることを見る。外での実行（通る例）は上のテストが見る。
test_setup_refuses_inside_a_launcher() {
    local home shared launcher_dir status real_bwrap
    home="${TEST_ROOT}/setup-inside-launcher"
    mkdir -p "$home"
    run_setup "$home" >/dev/null
    shared="${home}/.pi/agent/extensions/subagent"
    launcher_dir="${home}/.pi/agent/extensions/subagent.d/pigs"
    # MODEL_SHIM の bwrap は mount をしない偽物なので、本物を絶対パスで使う。
    real_bwrap="$(command -v bwrap)" || real_bwrap=""
    if [ -z "$real_bwrap" ] || ! "$real_bwrap" --dev-bind / / --bind "$launcher_dir" "$shared" -- true 2>/dev/null; then
        printf 'SKIP: bwrap cannot create the launcher mount here; inside-launcher refusal not checked\n' >&2
        return 0
    fi
    cp -a "$home" "${TEST_ROOT}/setup-inside-launcher.before"
    set +e
    env HOME="$home" PATH="${MODEL_SHIM}/bin:${PATH}" \
        "$real_bwrap" --dev-bind / / --bind "$launcher_dir" "$shared" -- zsh "$SETUP" --if-absent >/dev/null 2>&1
    status=$?
    set -e
    [ "$status" -ne 0 ] || fail "setup inside a launcher mount must fail"
    diff -r "${TEST_ROOT}/setup-inside-launcher.before" "$home" >/dev/null \
        || fail "setup inside a launcher mount must not write anything"
}

# 防ぐ損害: setup が共有の settings.json（書式・CRLF・世代バックアップ）を書き換えると、共有の設定が黙って壊れる。
# 通常と --if-absent の 2 通りで、書式を含めて既存のバイト列を比較し、無いときに作らないことも見る。
test_setup_leaves_user_settings_untouched() {
    local mode case_home dir settings snapshot shim setup_args name
    shim="${TEST_ROOT}/settings-pi-shim"
    mkdir -p "$shim"
    cat > "${shim}/pi" <<'PI_EOF'
#!/bin/bash
if [ "${1:-}" = list ]; then
    printf '%s\n' 'npm:@teelicht/pi-superagents'
    exit 0
fi
exit 64
PI_EOF
    chmod +x "${shim}/pi"

    for mode in normal if-absent missing; do
        setup_args=()
        if [ "$mode" = if-absent ]; then
            setup_args=(--if-absent)
        fi
        case_home="${TEST_ROOT}/settings-${mode}"
        dir="${case_home}/.pi/agent"
        settings="${dir}/settings.json"
        snapshot="${TEST_ROOT}/snapshot-${mode}"
        mkdir -p "$dir" "$snapshot"
        if [ "$mode" != missing ]; then
            printf '{\r\n\t"skills": ["./other skill"], "packages": ["npm:x"],\r\n\t"theme": "dark"\r\n}\r\n\r\n' > "$settings"
        fi
        printf 'generation one\r\n\n' > "${dir}/settings.json.bak.20260922-000000"
        cp "$dir"/settings.json* "$snapshot/"
        PATH="${shim}:${PATH}" run_setup "$case_home" "${setup_args[@]}" >/dev/null 2>&1 \
            || fail "setup failed: ${mode}"
        if [ "$mode" = missing ]; then
            [ ! -e "$settings" ] && [ ! -L "$settings" ] || fail "setup created settings"
        fi
        for name in "$snapshot"/settings.json*; do
            cmp -s "$name" "${dir}/${name##*/}" || fail "setup changed settings bytes: ${mode}/${name##*/}"
        done
        [ "$(find "$dir" -maxdepth 1 -name 'settings.json*' | wc -l)" = "$(find "$snapshot" -name 'settings.json*' | wc -l)" ] \
            || fail "setup changed settings file names: ${mode}"
    done
}

INSTALL_SCRIPT="${REPO_ROOT}/.devcontainer/install_beforehand.bash"

# install_beforehand.bash 全体は sudo apt 等を含みテストで実行できないため、install_pi_extensions() だけを
# 取り出し、fake pi を PATH に載せた独立スクリプトで実行する。
FAKE_STATE="${TEST_ROOT}/pi-state/registry"
FAKE_LOG="${TEST_ROOT}/pi-state/log"

make_fake_pi() {
    mkdir -p "${TEST_ROOT}/bin" "${TEST_ROOT}/pi-state"
    cat > "${TEST_ROOT}/bin/pi" <<'FAKE_PI_EOF'
#!/bin/bash
set -u
state="${PI_FAKE_STATE:?}"
log="${PI_FAKE_LOG:?}"
cmd="${1:-}"
shift || true
case "$cmd" in
    list)
        if [ "${FAKE_PI_MISSING_NEW:-0}" = 1 ]; then
            exit 0
        fi
        [ -f "$state" ] && cat "$state" || true
        ;;
    install)
        printf 'install: %s\n' "$*" >> "$log"
        touch "$state"
        printf '%s\n' "$2" >> "$state"
        ;;
    *)
        printf '%s: %s\n' "$cmd" "$*" >> "$log"
        exit 1
        ;;
esac
FAKE_PI_EOF
    chmod +x "${TEST_ROOT}/bin/pi"
}

run_install_fragment() {
    local src="${TEST_ROOT}/fragment.bash"
    awk '/^install_pi_extensions\(\) \{/{p=1} p{print} p && /^\}/{exit}' "$INSTALL_SCRIPT" > "$src"
    printf 'install_pi_extensions\n' >> "$src"
    env HOME="${TEST_ROOT}/fake-home" PATH="${TEST_ROOT}/bin:${PATH}" \
        PI_FAKE_STATE="$FAKE_STATE" PI_FAKE_LOG="$FAKE_LOG" bash "$src"
}

# 迷い（L 寄り・中）: pi install が 0 を返したのに一覧へ新拡張が無いとき、postCreate が成功扱いで終わると
# pigo / pigod で subagent ツールが無いまま気付かない（失敗を成功と報告する損害）。導入の成功と合わせて確かめる。
test_install_registers_and_verifies_superagents() {
    local status out
    make_fake_pi
    rm -f -- "${FAKE_STATE:?}" "${FAKE_LOG:?}"
    run_install_fragment >/dev/null 2>&1 || fail "install must succeed"
    grep -q '^install: --approve npm:@teelicht/pi-superagents$' "$FAKE_LOG" \
        || fail "install of pi-superagents must be called"
    [ "$(wc -l < "$FAKE_LOG")" = 1 ] || fail "install must call only pi install (no remove)"
    rm -f -- "${FAKE_STATE:?}" "${FAKE_LOG:?}"
    set +e
    out="$(FAKE_PI_MISSING_NEW=1 run_install_fragment 2>&1)"
    status=$?
    set -e
    assert_eq "$status" "1" "new extension missing after install must exit 1"
    assert_contains "$out" "npm:@teelicht/pi-superagents" "must name the missing extension"
}


# Only the external TUI/network and mount boundary are fake. Native Pi metadata
# readers/composition remain real, with a private bundled catalog we can damage.
MODEL_SHIM="${TEST_ROOT}/model-shim"
make_model_shim() {
    local package native
    native="$(realpath "$(command -v pi)")"
    native="${native%/dist/bundle/cli.js}"
    package="${MODEL_SHIM}/package"
    mkdir -p "${MODEL_SHIM}/bin" "${package}/node_modules"
    cp -a "${native}/dist" "${native}/package.json" "$package/"
    cp -as "${native}/node_modules/." "${package}/node_modules/"
    rm -rf -- "${package:?}/node_modules/@earendil-works/pi-ai"
    cp -a "${native}/node_modules/@earendil-works/pi-ai" "${package}/node_modules/@earendil-works/pi-ai"
    printf '#!/bin/sh\nif [ "${1:-}" = list ]; then echo "npm:@teelicht/pi-superagents"; exit 0; fi\nprintf "%%s\\n" "$@"\n' > "${package}/dist/bundle/cli.js"
    chmod +x "${package}/dist/bundle/cli.js"
    ln -s "${package}/dist/bundle/cli.js" "${MODEL_SHIM}/bin/pi"
    printf '#!/bin/sh\nwhile [ "$1" != -- ]; do shift; done\nshift\nexec "$@"\n' > "${MODEL_SHIM}/bin/bwrap"
    chmod +x "${MODEL_SHIM}/bin/bwrap"
}

model_home() {
    local launcher="$1" home
    home="$(make_home "$launcher" with-config)"
    # Native catalog is grouped by API, not provider ID. Terra is deliberately
    # cache-only: preflight must use the newer saved public catalog as Pi does.
    node - "$MODEL_SHIM" "$home" "$launcher" <<'JS'
const fs = require('node:fs');
const [shim, home, launcher] = process.argv.slice(2);
const data = `${shim}/package/node_modules/@earendil-works/pi-ai/dist/providers/data`;
const catalog = JSON.parse(fs.readFileSync(`${data}/openai-codex.json`));
const template = catalog['openai-codex-responses']['chat:gpt-6-luna'];
fs.writeFileSync(`${home}/.pi/agent/models-store.json`, JSON.stringify({
    'openai-codex': { lastModified: 9999999999999, models: [
        {...template, id: 'gpt-6.1-terra', name: 'Synthetic Terra'}] }
}));
const model = launcher === 'pigt' ? 'openai-codex/gpt-6-luna' : 'deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731';
fs.writeFileSync(`${home}/.pi/agent/extensions/subagent.d/${launcher}/config.json`, JSON.stringify({
    superagents: {modelTiers: Object.fromEntries(['cheap', 'balanced', 'max'].map(tier =>
        [tier, {model, thinking: 'low'}]))}
}));
JS
    cp "${REPO_ROOT}/.devcontainer/pi-models.json" "${home}/.pi/agent/models.json"
    # Independent registered custom model; never resolve its credential command.
    node - "${home}/.pi/agent/models.json" <<'JS'
const fs = require('node:fs');
const file = process.argv[2], data = JSON.parse(fs.readFileSync(file));
const p = data.providers.deepinfra;
p.apiKey = '!this-command-must-never-run';
p.models.push({...p.models[0], id: 'deepseek-ai/DeepSeek-V4.1-Flash-1017', thinkingLevelMap: {high: 'high', max: null}});
fs.writeFileSync(file, JSON.stringify(data));
JS
    printf '%s' "$home"
}

run_model_helper() {
    local home="$1" launcher="$2"; shift 2
    env HOME="$home" PATH="${MODEL_SHIM}/bin:${PATH}" PI_SUPERAGENTS_LAUNCHER_DRY_RUN=0 \
        "${ZSH_BIN}" -c 'source "$1"; shift; pi_superagents_exec "$@"' _ "$HELPER" "$launcher" "$@"
}

# S: accepting an unresolved child model lets Pi silently pick/fuzzily match
# another model even though the parent exists. One denial and one valid launch.
test_missing_child_catalog_model_stops_before_pi() {
    local home out status catalog saved
    home="$(model_home pigt)"
    out="$(run_model_helper "$home" pigt --provider openai-codex --model gpt-6.1-terra --thinking xhigh)"
    assert_contains "$out" gpt-6.1-terra "valid cached parent and bundled child must reach Pi"
    catalog="${MODEL_SHIM}/package/node_modules/@earendil-works/pi-ai/dist/providers/data/openai-codex.json"
    saved="$(<"$catalog")"
    node - "$catalog" <<'JS'
const fs = require('node:fs'), file = process.argv[2];
const data = JSON.parse(fs.readFileSync(file));
delete data['openai-codex-responses']['chat:gpt-6-luna'];
fs.writeFileSync(file, JSON.stringify(data));
JS
    set +e
    out="$(run_model_helper "$home" pigt --provider openai-codex --model gpt-6.1-terra --thinking xhigh 2>&1)"
    status=$?
    set -e
    printf '%s' "$saved" > "$catalog"
    assert_eq "$status" 1 "missing child catalog model must not reach Pi"
}

# S: checking only edited tiers or falling back on an old provider model starts
# the wrong parent; retain explicit resolvable user tier edits in the valid case.
test_missing_custom_parent_stops_before_pi() {
    local home out status
    home="$(model_home pidid)"
    out="$(run_model_helper "$home" pidid --provider deepinfra --model deepseek-ai/DeepSeek-V4.1-Flash-1017 --thinking high)"
    assert_contains "$out" deepseek-ai/DeepSeek-V4.1-Flash-1017 "valid custom parent with edited tiers must reach Pi"
    node - "${home}/.pi/agent/models.json" <<'JS'
const fs = require('node:fs'), file = process.argv[2], data = JSON.parse(fs.readFileSync(file));
data.providers.deepinfra.models = data.providers.deepinfra.models.filter(m => m.id !== 'deepseek-ai/DeepSeek-V4.1-Flash-1017');
fs.writeFileSync(file, JSON.stringify(data));
JS
    set +e
    out="$(run_model_helper "$home" pidid --provider deepinfra --model deepseek-ai/DeepSeek-V4.1-Flash-1017 --thinking high 2>&1)"
    status=$?
    set -e
    assert_eq "$status" 1 "missing custom parent must not reach Pi"
}

# S: checking launcher defaults instead of the effective CLI options lets an
# unsupported parent thinking level silently clamp. A valid final override must
# still launch; option-looking values/messages must not become parent options.
test_effective_parent_options_are_checked() {
    local home out status prompt
    home="$(model_home pidid)"
    set +e
    out="$(run_model_helper "$home" pidid --provider deepinfra \
        --model deepseek-ai/DeepSeek-V4.1-Flash-1017 --thinking high --thinking max 2>&1)"
    status=$?
    set -e
    assert_eq "$status" 1 "effective unsupported parent thinking must not reach Pi"

    prompt=$'確認依頼\n日本語と spaces を欠落させず扱ってください。'
    out="$(run_model_helper "$home" pidid --provider missing-provider --model missing-model \
        --thinking max --provider deepinfra --model deepseek-ai/DeepSeek-V4.1-Flash-1017 \
        --thinking high --system-prompt --thinking -- "$prompt" \
        --provider missing-provider --model missing-model --thinking max)"
    assert_contains "$out" "$prompt" "valid final parent options must reach Pi with the prompt"
}

# S: invalid thinking gets clamped, silently changing the tier; unreadable or
# malformed metadata must not be treated as a successful check.
test_unverifiable_or_unsupported_tiers_stop_before_pi() {
    local home out status config
    home="$(model_home pidid)"
    config="${home}/.pi/agent/extensions/subagent.d/pidid/config.json"
    out="$(run_model_helper "$home" pidid --provider deepinfra --model deepseek-ai/DeepSeek-V4.1-Flash-1017 --thinking high)"
    assert_contains "$out" deepseek-ai/DeepSeek-V4.1-Flash-1017 "supported edited tier thinking must reach Pi"
    node - "$config" <<'JS'
const fs = require('node:fs'), file = process.argv[2], data = JSON.parse(fs.readFileSync(file));
data.superagents.modelTiers.max = {model: 'deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017', thinking: 'max'};
fs.writeFileSync(file, JSON.stringify(data));
JS
    set +e
    out="$(run_model_helper "$home" pidid --provider deepinfra --model deepseek-ai/DeepSeek-V4.1-Flash-1017 --thinking high 2>&1)"
    status=$?
    set -e
    assert_eq "$status" 1 "unsupported tier thinking must not be clamped by Pi"
    home="$(model_home pidid)"
    printf '{"synthetic-private":' > "${home}/.pi/agent/models.json"
    set +e
    out="$(run_model_helper "$home" pidid --provider deepinfra --model deepseek-ai/DeepSeek-V4.1-Flash-1017 --thinking high 2>&1)"
    status=$?
    set -e
    assert_eq "$status" 1 "unverifiable models must not reach Pi"
    case "$out" in *synthetic-private*) fail "parser details must not leak config contents";; esac
}

make_model_shim
test_effective_parent_options_are_checked
test_missing_child_catalog_model_stops_before_pi
test_missing_custom_parent_stops_before_pi
test_unverifiable_or_unsupported_tiers_stop_before_pi
test_bind_target_ignores_pi_coding_agent_dir
test_missing_config_fails_closed
test_incomplete_tiers_fail_closed
test_missing_bwrap_fails_closed
test_actual_and_dry_run_argv_match
test_launchers_wrap_pi_with_their_own_config
test_only_vertex_launchers_overlay_auth
test_setup_preserves_prior_generation_on_name_collision
test_setup_if_absent_preserves_user_edits
test_setup_guards_shared_bind_target
test_setup_refuses_inside_a_launcher
test_setup_leaves_user_settings_untouched
test_install_registers_and_verifies_superagents
printf 'OK test-pi-superagents\n'
