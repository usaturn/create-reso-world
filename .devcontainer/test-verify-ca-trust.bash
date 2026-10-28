#!/bin/bash
# verify-ca-trust.bash が、TLS の成立と、信頼の欠如を示さない失敗（期限切れ・接続できない）と、対象以外のホスト
# （リダイレクト先・uv の別の index）での拒否を「信頼していない」として 0 で終わらないことを、実際のクライアントと
# ローカルの HTTPS サーバで確かめる。外部のホストには接続しない
# 仕様: docs/superpowers/specs/2026-10-28-create-reso-world-issue-291-ca-trust-check-design.md（#291）
set -euo pipefail
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
script="$root/.devcontainer/verify-ca-trust.bash"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
servers=()
cleanup() {
  local pid
  for pid in "${servers[@]}"; do kill "$pid" 2>/dev/null || true; done
  rm -rf -- "${tmp:?}"
}
trap cleanup EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; printf '%s\n' "$out" >&2; exit 1; }
out=''

# テスト用の CA（Python 3.14 は CA に keyUsage が無いと検証に失敗する）と、localhost の証明書・期限切れの証明書
cd "$tmp"
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout ca.key -out ca.pem -days 2 \
  -subj '/CN=verify-ca-trust test CA' -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign' 2>/dev/null
openssl req -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout leaf.key -out leaf.csr -subj '/CN=localhost' 2>/dev/null
printf 'subjectAltName=DNS:localhost\nbasicConstraints=CA:FALSE\nextendedKeyUsage=serverAuth\n' > leaf.ext
openssl x509 -req -in leaf.csr -CA ca.pem -CAkey ca.key -out valid.pem -days 2 -extfile leaf.ext 2>/dev/null
openssl x509 -req -in leaf.csr -CA ca.pem -CAkey ca.key -out expired.pem \
  -not_before 20200101000000Z -not_after 20200102000000Z -extfile leaf.ext 2>/dev/null
# リダイレクト先の証明書を出す、信頼させない別の CA（ca.pem と同じだとリダイレクト先でも成立し、取り違えを確かめられない）
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout other-ca.key -out other-ca.pem -days 2 \
  -subj '/CN=verify-ca-trust other CA' -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign' 2>/dev/null
openssl x509 -req -in leaf.csr -CA other-ca.pem -CAkey other-ca.key -out other.pem -days 2 -extfile leaf.ext 2>/dev/null

# すべての GET に、argv[3] のポートの localhost の同じパスへの 302 を返す HTTPS サーバ（argv[1] の証明書、argv[2] の鍵）
readonly REDIRECT_SERVER='
import http.server, ssl, sys
cert, key, target = sys.argv[1:4]
class Redirect(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", f"https://localhost:{target}{self.path}")
        self.send_header("Content-Length", "0")
        self.end_headers()
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(cert, key)
server.socket = context.wrap_socket(server.socket, server_side=True)
print(f"ACCEPT 127.0.0.1:{server.server_address[1]}", flush=True)
server.serve_forever()
'

# HTTPS サーバのコマンドを起動し、出力の ACCEPT 行のポートを port に入れる（後片付けのためサブシェルで呼ばない）。
# ログは起動ごとに別の名前で先に作る（リダイレクトはバックグラウンドの子で行われ、sed が先に読むと無い。同じ名前だと前のサーバの
# ACCEPT 行を読む）
start_server() {
  local log="$tmp/server-${#servers[@]}.log" i
  port=''
  : >"$log"
  "$@" >"$log" 2>&1 &
  servers+=("$!")
  for i in $(seq 50); do
    port="$(sed -n 's/^ACCEPT .*:\([0-9][0-9]*\)$/\1/p' "$log")"
    [ -n "$port" ] && return 0
    sleep 0.1
  done
  out="$(cat "$log")"
  fail "server did not start: $*"
}
# 証明書を出す openssl s_server を空いているポートで起動する
start_tls_server() {
  start_server openssl s_server -accept 127.0.0.1:0 -cert "$1" -key leaf.key -www
}
start_tls_server valid.pem
valid_port="$port"
start_tls_server expired.pem
expired_port="$port"
start_tls_server other.pem
other_port="$port"
start_server uv run --no-project python -I -c "$REDIRECT_SERVER" valid.pem leaf.key "$other_port"
redirect_port="$port"
# 閉じたポート。localhost:1 は Node.js の fetch が bad port として接続の前に拒否するので、止めたサーバのポートを使う
start_tls_server valid.pem
closed_port="$port"
kill "${servers[-1]}"
wait "${servers[-1]}" 2>/dev/null || true
# uv の設定ファイルで足す別の index（閉じたポート）
printf 'extra-index-url = ["https://localhost:%s/simple/"]\n' "$closed_port" >uv-extra-index.toml

# 一時 HOME と、結果を変える CA の環境変数を外した環境で実行する。追加の NAME=VALUE は env に渡す
mkdir -p "$tmp/home"
run() {
  local target="$1"
  shift
  set +e
  out="$(env -u SSL_CERT_FILE -u SSL_CERT_DIR -u CURL_CA_BUNDLE -u NODE_EXTRA_CA_CERTS -u NODE_OPTIONS \
    -u NODE_USE_SYSTEM_CA -u UV_NATIVE_TLS -u UV_SYSTEM_CERTS \
    HOME="$tmp/home" XDG_CONFIG_HOME="$tmp/home/.config" XDG_CACHE_HOME="$tmp/home/.cache" GIT_CONFIG_NOSYSTEM=1 \
    "$@" bash "$script" "$target" 2>&1)"
  rc=$?
  set -e
}
# テスト用の CA を各クライアントに信頼させる
run_trusted() {
  run "$1" SSL_CERT_FILE="$tmp/ca.pem" CURL_CA_BUNDLE="$tmp/ca.pem" GIT_SSL_CAINFO="$tmp/ca.pem" \
    NODE_EXTRA_CA_CERTS="$tmp/ca.pem"
}
# 対象の行のうち、判定が $2 の行の数が $3 であること
expect_count() {
  local target="$1" verdict="$2" want="$3" got
  got="$(grep -cE "^[a-z]+ +${target} +${verdict}( |$)" <<<"$out" || true)"
  [ "$got" = "$want" ] || fail "$target: expected $want line(s) of $verdict, got $got"
}

# 信頼させない（正例）: 発行者を信頼しない検証エラーだけなので、0 で終わる。環境変数・設定ファイルで足した uv の index は
# 対象より先に問い合わせられ、別のホストの結果で判定してしまうので、混ぜずに対象だけへ接続すること
run "localhost:$valid_port" UV_EXTRA_INDEX_URL="https://localhost:$closed_port/simple/" \
  UV_CONFIG_FILE="$tmp/uv-extra-index.toml"
[ "$rc" -eq 0 ] || fail "an untrusted issuer must exit 0, got $rc"
expect_count "localhost:$valid_port" 信頼していない 6

# 信頼させた: TLS が成立するので「信頼している」と表示して非 0 で終わる
run_trusted "localhost:$valid_port"
[ "$rc" -ne 0 ] || fail 'a trusted chain must not exit 0'
expect_count "localhost:$valid_port" 信頼している 6
expect_count "localhost:$valid_port" 信頼していない 0

# 期限切れ: 検証エラーでも発行者の信頼とは関係ないので、「信頼していない」にせず非 0 で終わる
run_trusted "localhost:$expired_port"
[ "$rc" -ne 0 ] || fail 'an expired certificate must not exit 0'
expect_count "localhost:$expired_port" 信頼していない 0
expect_count "localhost:$expired_port" 判定不能 6

# 閉じたポート: 接続できないのは安全の証拠ではないので、判定不能で非 0 で終わる
run "localhost:$closed_port"
[ "$rc" -ne 0 ] || fail 'an unreachable port must not exit 0'
expect_count "localhost:$closed_port" 判定不能 6

# リダイレクト: 対象（信頼させた CA）は、信頼させない CA のホストへの 302 を返す。対象との TLS は成立しているので、
# リダイレクト先での拒否を対象の「信頼していない」にせず、非 0 で終わること。curl は .curlrc の --location でも追わないこと
printf -- '--location\n' >"$tmp/home/.curlrc"
run_trusted "localhost:$redirect_port"
[ "$rc" -ne 0 ] || fail 'a redirect over a trusted chain must not exit 0'
expect_count "localhost:$redirect_port" 信頼している 6
expect_count "localhost:$redirect_port" 信頼していない 0

printf 'PASS: verify-ca-trust.bash reports only issuer rejections as not trusted\n'
