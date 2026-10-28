#!/bin/bash
# eMudhra の中間CA の秘密鍵の侵害（2026-10-20）に対して、この環境の主なクライアントが侵害された中間CA を信頼していないかを、
# 確認用ホストへ接続して確かめる。外部へ接続するので postCreate と run-tests.bash には入れず、rebuild の後とツールの更新の後に手で実行する。
# 拒否と成立のどちらも出力にある証拠だけで判定し、証拠の無い失敗（接続できない・期限切れなど）は「判定不能」にする
# （ネットワーク障害や確認用ホストの変化を、安全と報告しない）。証拠は対象のホストとの接続と、その応答だけから取る。
# リダイレクトは追わずに対象の 3xx を成立に数え、設定の別の index やリダイレクト先など、別のホストでの拒否を対象の判定にしない。
# 仕様: docs/superpowers/specs/2026-10-28-create-reso-world-issue-291-ca-trust-check-design.md（#291）
set -uo pipefail

readonly CLIENT_TIMEOUT=15
readonly OUTER_TIMEOUT=30
readonly CLIENTS=(openssl curl git python node uv)
# 確認サイト（https://emudhra.we-have-a-problem.com/）がコマンドラインのクライアント向けに挙げるホスト
readonly DEFAULT_TARGETS=(
    dv-g3b-emudhra.we-have-a-problem.com:443
    dv-g3b-aaa-emudhra.we-have-a-problem.com:443
    dv-g3b-noct-emudhra.we-have-a-problem.com:443
    dv-g3b-aaa-noct-emudhra.we-have-a-problem.com:443
)

# 1 行目に http <状態>・verify <検証コード> <理由>・error <名前> <理由> のどれかを出す。HOST・PORT・タイムアウトは引数で受け取る。
# リダイレクトは追わず、対象が返した 3xx を HTTPError として受け取る（プロキシの環境変数は反映する）
readonly PYTHON_PROBE='
import ssl, sys, urllib.error, urllib.request
host, port, timeout = sys.argv[1], sys.argv[2], float(sys.argv[3])
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None
opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context()))
try:
    with opener.open(f"https://{host}:{port}/", timeout=timeout) as response:
        print("http", response.status)
except urllib.error.HTTPError as error:
    print("http", error.code)
except urllib.error.URLError as error:
    reason = error.reason
    if isinstance(reason, ssl.SSLCertVerificationError):
        print("verify", reason.verify_code, reason.verify_message)
    else:
        print("error", type(reason).__name__, reason)
except ssl.SSLCertVerificationError as error:
    print("verify", error.verify_code, error.verify_message)
except Exception as error:
    print("error", type(error).__name__, error)
'
readonly NODE_PROBE='
const [host, port, timeout] = process.argv.slice(1);
fetch(`https://${host}:${port}/`, { redirect: "manual", signal: AbortSignal.timeout(Number(timeout) * 1000) })
  .then((response) => console.log(`http ${response.status}`))
  .catch((error) => {
    const cause = error.cause ?? error;
    console.log(`error ${cause.code ?? cause.name} ${cause.message}`);
  })
  .finally(() => process.exit(0));
'

usage() {
    cat <<'EOF'
使い方: bash .devcontainer/verify-ca-trust.bash [HOST[:PORT] ...]

openssl（システムの CA バンドル）・curl・git・python・node・uv で HOST へ接続し、侵害された中間CA を
信頼していないかを確かめる。HOST を省くと、確認サイトの 4 つのホスト（ポート 443）を使う。
終了コード: 0 すべて信頼していない / 1 信頼している がある / 2 判定不能 がある / 64 使い方の誤り
EOF
}

targets=()
for arg in "$@"; do
    case "$arg" in
    -h | --help)
        usage
        exit 0
        ;;
    esac
    host="${arg%%:*}"
    port=443
    if [[ "$arg" == *:* ]]; then
        port="${arg#*:}"
    fi
    if ! [[ "$host" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ ]] \
        || ! [[ "$port" =~ ^[0-9]{1,5}$ ]] || ((10#$port < 1 || 10#$port > 65535)); then
        printf 'verify-ca-trust: 不正な HOST[:PORT]: %s\n' "$arg" >&2
        usage >&2
        exit 64
    fi
    targets+=("${host}:$((10#$port))")
done
if [ "${#targets[@]}" -eq 0 ]; then
    targets=("${DEFAULT_TARGETS[@]}")
fi

# 接続はリポジトリの外の一時ディレクトリで行う（uv・git がリポジトリの設定を読まないように）
work="$(mktemp -d)" || exit 1
trap 'rm -rf -- "${work:?}"' EXIT
cd -- "$work" || exit 1
printf 'verify-ca-trust-probe\n' >requirements.in

# 接続の出力（標準エラーを含む）を probe_out に、終了コードを probe_rc に入れる
run_probe() {
    probe_out="$(timeout -k 5 "$OUTER_TIMEOUT" "$@" </dev/null 2>&1)"
    probe_rc=$?
}

probe() {
    local client="$1" host="$2" port="$3"
    case "$client" in
    openssl)
        run_probe openssl s_client -connect "${host}:${port}" -servername "$host" -verify_hostname "$host" \
            -verify_return_error -brief
        ;;
    curl)
        # 利用者の .curlrc の --location を打ち消し、リダイレクトを追わない
        run_probe curl -sS -o /dev/null -w '%{http_code}' --no-location --max-time "$CLIENT_TIMEOUT" "https://${host}:${port}/"
        ;;
    git)
        # HTTP の応答ヘッダを受け取ったこと（TLS の成立）を GIT_TRACE_CURL の記録で確かめる。git はリダイレクトを追うが、
        # 最初の応答ヘッダは対象のもの（対象が拒否されればヘッダは無い）
        run_probe env GIT_TERMINAL_PROMPT=0 GIT_TRACE_CURL=1 GIT_TRACE_CURL_NO_DATA=1 \
            git ls-remote "https://${host}:${port}/"
        ;;
    python)
        run_probe uv run --no-project python -I -c "$PYTHON_PROBE" "$host" "$port" "$CLIENT_TIMEOUT"
        ;;
    node)
        run_probe node -e "$NODE_PROBE" "$host" "$port" "$CLIENT_TIMEOUT"
        ;;
    uv)
        # 確認用ホストだけを index にする。-vv の記録で応答の受信を確かめる。設定ファイルと環境変数の別の index を混ぜない
        # （extra の index は対象より先に問い合わせられる。UV_CONFIG_FILE は --no-config でも読まれる）
        run_probe env -u UV_CONFIG_FILE -u UV_INDEX -u UV_DEFAULT_INDEX -u UV_INDEX_URL -u UV_EXTRA_INDEX_URL \
            -u UV_FIND_LINKS -u UV_TORCH_BACKEND -u UV_NO_INDEX -u UV_OFFLINE \
            UV_HTTP_RETRIES=0 UV_HTTP_TIMEOUT="$CLIENT_TIMEOUT" \
            uv -vv pip compile requirements.in --no-config --no-cache --index-url "https://${host}:${port}/simple/"
        ;;
    esac
}

# 発行者を信頼しないことを示す OpenSSL の検証コード。期限切れ（10）・名前の不一致（62）などは含めない
is_issuer_code() {
    case "$1" in
    2 | 19 | 20 | 21 | 23 | 27 | 28) return 0 ;;
    esac
    return 1
}

is_node_issuer_code() {
    case "$1" in
    UNABLE_TO_GET_ISSUER_CERT | SELF_SIGNED_CERT_IN_CHAIN | UNABLE_TO_GET_ISSUER_CERT_LOCALLY | \
        UNABLE_TO_VERIFY_LEAF_SIGNATURE | CERT_REVOKED | CERT_UNTRUSTED | CERT_REJECTED) return 0 ;;
    esac
    return 1
}

# 出力のうち PATTERN に合う最後の行（無ければ最後の空でない行）を、前後の空白を除いて 200 文字までにする
summary_line() {
    local line
    line="$(grep -E "$1" <<<"$probe_out" | tail -n 1)"
    if [ -z "$line" ]; then
        line="$(grep -v '^[[:space:]]*$' <<<"$probe_out" | tail -n 1)"
    fi
    line="${line#"${line%%[![:space:]]*}"}"
    printf '%s' "${line:0:200}"
}

# uv の出力の最後の Failed to fetch の行（error: か cause:）の URL を 1 行目に、その行に続く cause: の行にある
# 発行者を信頼しない拒否の文言を 2 行目に出す（無ければ空行）
uv_fetch_failure() {
    awk '
        /^(error:|[[:space:]]+cause:) Failed to fetch: / {
            url = $0
            sub(/^.*Failed to fetch: `?/, "", url)
            sub(/`?[[:space:]]*$/, "", url)
            rejection = ""
            in_causes = 1
            next
        }
        in_causes && /^[[:space:]]+cause:/ {
            if (rejection == "" && match($0, /invalid peer certificate: (UnknownIssuer|Revoked|Other\(OtherError\(CertDistrusted\)\))[[:space:]]*$/)) {
                rejection = substr($0, RSTART, RLENGTH)
                sub(/[[:space:]]+$/, "", rejection)
            }
            next
        }
        { in_causes = 0 }
        END { print url; print rejection }
    ' <<<"$probe_out"
}

# probe の結果を verdict（判定）と detail（根拠）にする。成立の証拠を拒否の証拠より優先し、どちらも無ければ判定不能
classify() {
    local client="$1" host="$2" port="$3" marker='' code='' reason='' url='' rejection=''
    verdict='判定不能'
    detail=''
    case "$client" in
    openssl)
        if [ "$probe_rc" -eq 0 ] && grep -q '^CONNECTION ESTABLISHED' <<<"$probe_out"; then
            verdict='信頼している'
            detail='TLS の接続が成立した'
            return
        fi
        code="$(sed -n 's/^verify error:num=\([0-9][0-9]*\):.*/\1/p' <<<"$probe_out" | head -n 1)"
        reason="$(sed -n 's/^verify error:num=[0-9][0-9]*:\(.*\)/\1/p' <<<"$probe_out" | head -n 1)"
        detail="$(summary_line 'verify error|errno|error:')"
        ;;
    curl | git)
        if { [ "$client" = curl ] && [ "$probe_rc" -eq 0 ]; } \
            || { [ "$client" = git ] && grep -q '<= Recv header: HTTP/' <<<"$probe_out"; }; then
            verdict='信頼している'
            detail='HTTP の応答を受け取った'
            return
        fi
        code="$(sed -n 's/.*verify result: .* (\([0-9][0-9]*\))$/\1/p' <<<"$probe_out" | head -n 1)"
        reason="$(sed -n 's/.*verify result: \(.*\) ([0-9][0-9]*)$/\1/p' <<<"$probe_out" | head -n 1)"
        detail="$(summary_line '^(curl: \(|fatal:)')"
        ;;
    python | node)
        marker="$(grep -E '^(http|verify|error) ' <<<"$probe_out" | tail -n 1)"
        case "$marker" in
        http\ *)
            verdict='信頼している'
            detail="HTTP ${marker#http } の応答を受け取った"
            return
            ;;
        verify\ *)
            code="$(cut -d ' ' -f 2 <<<"$marker")"
            reason="$(cut -d ' ' -f 3- <<<"$marker")"
            ;;
        error\ *)
            if [ "$client" = node ] && is_node_issuer_code "$(cut -d ' ' -f 2 <<<"$marker")"; then
                verdict='信頼していない'
                detail="${marker#error }"
                return
            fi
            ;;
        esac
        detail="$(summary_line '^(verify|error) ')"
        ;;
    uv)
        # 対象が返した HTTP の応答を成立の証拠にする。uv はリダイレクトを自分で追うので、3xx の受信の記録も数える
        # （リダイレクト先での失敗も、元の URL の Failed to fetch として出る）
        marker="$(sed -nE -e 's/.*Received response for .* with status ([0-9]{3}).*/\1/p' \
            -e 's/.*Received HTTP ([0-9]{3}) .*Redirecting to .*/\1/p' <<<"$probe_out" | head -n 1)"
        if [ -n "$marker" ]; then
            verdict='信頼している'
            detail="HTTP ${marker} の応答を受け取った"
            return
        fi
        # 拒否は、最後に失敗した URL が対象の index のときだけ数える（ポート 443 は uv が URL から省く）。
        # 設定の別の index など、別のホストでの拒否を対象の判定にしない
        { IFS= read -r url; IFS= read -r rejection; } <<<"$(uv_fetch_failure)"
        if [ "$url" = "https://${host,,}:${port}/simple/verify-ca-trust-probe/" ] \
            || { [ "$port" -eq 443 ] && [ "$url" = "https://${host,,}/simple/verify-ca-trust-probe/" ]; }; then
            if [ -n "$rejection" ]; then
                verdict='信頼していない'
                detail="$rejection"
                return
            fi
            detail="$(summary_line 'invalid peer certificate:|cause:|^error:')"
        elif [ -n "$url" ]; then
            detail="対象ではない URL での失敗: ${url}"
        else
            detail="$(summary_line 'invalid peer certificate:|cause:|^error:')"
        fi
        ;;
    esac
    if [ -n "$code" ]; then
        detail="OpenSSL ${code}: ${reason}"
        if is_issuer_code "$code"; then
            verdict='信頼していない'
        fi
    fi
}

# 表示名ごとの必要なコマンド
required_command() {
    case "$1" in
    python) printf 'uv' ;;
    *) printf '%s' "$1" ;;
    esac
}

printf 'eMudhra の侵害された中間CA を信頼していないかを、確認用ホストへの接続で確かめる（#291）\n'
trusted=0
rejected=0
unknown=0
for target in "${targets[@]}"; do
    host="${target%:*}"
    port="${target##*:}"
    for client in "${CLIENTS[@]}"; do
        command_name="$(required_command "$client")"
        if ! command -v "$command_name" >/dev/null 2>&1; then
            verdict='判定不能'
            detail="${command_name} が見つからない"
        else
            probe "$client" "$host" "$port"
            classify "$client" "$host" "$port"
            if [ "$verdict" = '判定不能' ] && { [ "$probe_rc" -eq 124 ] || [ "$probe_rc" -eq 137 ]; }; then
                detail="${OUTER_TIMEOUT} 秒でタイムアウトした"
            fi
        fi
        case "$verdict" in
        信頼している) trusted=$((trusted + 1)) ;;
        信頼していない) rejected=$((rejected + 1)) ;;
        *) unknown=$((unknown + 1)) ;;
        esac
        printf '%-7s  %s  %s  %s\n' "$client" "$target" "$verdict" "$detail"
    done
done

if [ "$trusted" -gt 0 ]; then
    printf '結果: 信頼している が %d 件ある。.devcontainer/README.md の「トラストストアの確認（eMudhra 中間CA の侵害）」に従って、そのクライアントを更新する\n' "$trusted"
    exit 1
fi
if [ "$unknown" -gt 0 ]; then
    printf '結果: 判定不能 が %d 件ある（信頼していない %d 件）。ネットワークと確認用ホストの状態を確かめて、もう一度実行する\n' "$unknown" "$rejected"
    exit 2
fi
printf '結果: %d 件すべてで信頼していない\n' "$rejected"
