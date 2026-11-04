#!/bin/bash
# .devcontainer/pi-superagents-model-guard.ts（pi-superagents の子 Pi が、tier の model と違う model で最初の要求を送る前に止める拡張。#310）のテスト。
# 実際の Pi を、一時の HOME・PI_CODING_AGENT_DIR と偽の provider（baseUrl はローカルの偽のサーバー）で動かす。env -i で資格情報の
# 環境変数を渡さず、PI_OFFLINE=1 で起動時の通信を止める。偽のサーバー以外へ要求を送らない。利用者の ~/.pi には触れない。
# pi-superagents と同じく stdin を閉じて起動する（開いたままだと Pi の -p は stdin を待ち続ける）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTENSION="${REPO_ROOT}/.devcontainer/pi-superagents-model-guard.ts"
TEST_ROOT="$(mktemp -d)"
SERVER_PID=""
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    rm -rf -- "${TEST_ROOT:?}"
}
trap cleanup EXIT

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

assert_not_contains() {
    local haystack="$1" needle="$2" msg="$3"
    case "$haystack" in
        *"$needle"*) fail "$msg: '$needle' must not appear in '$haystack'" ;;
    esac
}

PI_BIN="$(command -v pi || true)"
if [ -z "$PI_BIN" ]; then
    printf 'SKIP: pi is not installed; the model guard is not checked\n' >&2
    exit 0
fi
# 子の環境には、Pi と node を見つけられる PATH だけを渡す（資格情報の環境変数を持ち込まない）。
CHILD_PATH="$(dirname "$PI_BIN"):$(dirname "$(command -v node)"):/usr/bin:/bin"

# 偽のサーバー: 受けた要求を 1 行ずつ記録し、400 を返す（Pi は 400 を再試行しない）。
cat > "${TEST_ROOT}/server.mjs" <<'JS'
import fs from "node:fs";
import http from "node:http";
const [log, portFile] = process.argv.slice(2);
const server = http.createServer((request, response) => {
    let body = "";
    request.on("data", (chunk) => { body += chunk; });
    request.on("end", () => {
        let model = null;
        try { model = JSON.parse(body).model ?? null; } catch {}
        fs.appendFileSync(log, `${JSON.stringify({ url: request.url, model })}\n`);
        response.writeHead(400, { "content-type": "application/json" });
        response.end(JSON.stringify({ error: { message: "fake server" } }));
    });
});
server.listen(0, "127.0.0.1", () => fs.writeFileSync(portFile, String(server.address().port)));
JS
: > "${TEST_ROOT}/requests.log"
node "${TEST_ROOT}/server.mjs" "${TEST_ROOT}/requests.log" "${TEST_ROOT}/port" < /dev/null > /dev/null 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 50); do
    [ -s "${TEST_ROOT}/port" ] && break
    sleep 0.1
done
[ -s "${TEST_ROOT}/port" ] || fail "the fake server did not start"
PORT="$(<"${TEST_ROOT}/port")"

# fakeok は資格情報があり、fakenokey は無い。どちらも model-a を持つ。
mkdir -p "${TEST_ROOT}/agent" "${TEST_ROOT}/home" "${TEST_ROOT}/cwd"
cat > "${TEST_ROOT}/agent/models.json" <<JSON
{
  "providers": {
    "fakeok": {
      "baseUrl": "http://127.0.0.1:${PORT}/v1",
      "apiKey": "fake-key",
      "api": "openai-completions",
      "models": [{"id": "model-a", "reasoning": true}, {"id": "vendor/model-b", "reasoning": true}]
    },
    "fakenokey": {
      "baseUrl": "http://127.0.0.1:${PORT}/v1",
      "api": "openai-completions",
      "models": [{"id": "model-a", "reasoning": true}]
    }
  }
}
JSON

# pi-superagents が子 Pi に渡す形（--mode json -p、--models、--no-extensions と --extension）で起動する。
# STATUS に終了コード、REQUESTS に偽のサーバーが受けた要求の数、ERR に stderr を入れる。
run_child() {
    local pattern="$1"
    : > "${TEST_ROOT}/requests.log"
    set +e
    (cd "${TEST_ROOT}/cwd" && env -i PATH="$CHILD_PATH" HOME="${TEST_ROOT}/home" \
        PI_CODING_AGENT_DIR="${TEST_ROOT}/agent" PI_OFFLINE=1 \
        timeout 60 "$PI_BIN" --mode json -p --no-session --models "$pattern" \
        --no-extensions --extension "$EXTENSION" 'Task: reply with ok' \
        < /dev/null > "${TEST_ROOT}/child.out" 2> "${TEST_ROOT}/child.err")
    STATUS=$?
    set -e
    REQUESTS="$(wc -l < "${TEST_ROOT}/requests.log")"
    ERR="$(<"${TEST_ROOT}/child.err")"
}

# 防ぐ損害: 名指しの provider に資格情報が無いと、Pi は警告だけを出して同じ ID を持つ別の provider の model を選び、
# 終了コード 0 で要求を送る（#310）。照合が ID だけを見ると通してしまう。Pi が session_start の前に要求を送るよう
# 変わったときも、要求の数で気付く。通る例: 要求どおりに解決できる model（ID に / を含む）。
test_mismatched_model_stops_before_the_first_request() {
    run_child 'fakenokey/model-a:high'
    assert_eq "$STATUS" 1 "a child whose model resolves elsewhere must exit 1"
    assert_eq "$REQUESTS" 0 "a child whose model resolves elsewhere must not send a request"
    assert_contains "$ERR" "[pi-superagents-model-guard]" "the guard must explain the stop"
    assert_contains "$ERR" "fakenokey/model-a:high" "the stop must name the requested model"
    assert_contains "$ERR" "fakeok/model-a" "the stop must name the model Pi selected"

    run_child 'fakeok/vendor/model-b:high'
    [ "$REQUESTS" -ge 1 ] || fail "a child whose model resolves as requested must send its request (stderr: $ERR)"
    assert_not_contains "$ERR" "[pi-superagents-model-guard]" "a matching child must not be stopped"
}

# 防ぐ損害: 例外の内容（資格情報・コマンドの文字列を含みうる）を書くと、pi-superagents が子の stderr を
# run-history.jsonl・meta.json・親の結果に残し、秘密が実行記録に漏れる。
test_exception_details_are_not_written() {
    local secret status err
    secret="secret-$(head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    set +e
    node --input-type=module - "$EXTENSION" "$secret" > /dev/null 2> "${TEST_ROOT}/exception.err" <<'JS'
import { pathToFileURL } from "node:url";
const [extensionPath, secret] = process.argv.slice(2);
const { default: extension } = await import(pathToFileURL(extensionPath).href);
let handler;
extension({ on: (name, fn) => { if (name === "session_start") handler = fn; } });
process.argv = [process.argv[0], "pi", "--mode", "json", "-p", "--models", "fakeok/model-a:high"];
const ctx = {
    get model() { throw new Error(`auth command failed: ${secret}`); },
    modelRegistry: { getAll: () => [{ provider: "fakeok", id: "model-a" }] },
};
await handler({ reason: "startup" }, ctx);
process.exit(0);
JS
    status=$?
    set -e
    err="$(<"${TEST_ROOT}/exception.err")"
    assert_eq "$status" 1 "an exception while checking must stop the child"
    assert_contains "$err" "[pi-superagents-model-guard]" "the guard must explain the stop"
    assert_not_contains "$err" "$secret" "the exception text must not be written"
}

test_mismatched_model_stops_before_the_first_request
test_exception_details_are_not_written
printf 'PASS: pi-superagents model guard\n'
