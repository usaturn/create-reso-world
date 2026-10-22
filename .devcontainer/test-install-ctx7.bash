#!/bin/bash
# Context7 CLI の導入（.devcontainer/install_ctx7.bash）を、偽の npm と偽の ctx7 でネットワークを使わずに実行する。
# 固定した版を入れること、ctx7 を --version 以外で呼ばないこと（ctx7 setup は共有の ~/.claude・~/.codex などへ
# 書き込み、導入は成功するので気付けない）、別の版の ctx7 を受け入れないことを確かめる
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
installer="$root/.devcontainer/install_ctx7.bash"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

version="$(sed -n 's/^readonly CTX7_CLI_VERSION="\([^"]*\)"$/\1/p' "$installer" 2>/dev/null || true)"
[ -n "$version" ] || fail 'install_ctx7.bash lacks readonly CTX7_CLI_VERSION'

# 偽の npm は install -g の引数を記録し、npm のグローバルの bin（NPM_BIN）に偽の ctx7 を置く
mkdir -p "$tmp/bin" "$tmp/npm-bin"
cat > "$tmp/bin/npm" <<'FAKE'
#!/bin/bash
printf 'npm %s\n' "$*" >> "$CALLS"
[ "${FAIL_NPM:-0}" = 0 ] || exit 1
[ "${PLACE_CTX7:-1}" = 1 ] || exit 0
cat > "$NPM_BIN/ctx7" <<'CTX7'
#!/bin/bash
printf 'ctx7 %s\n' "$*" >> "$CALLS"
[ "$*" = --version ] || exit 0
printf '%s\n' "$FAKE_VERSION"
CTX7
chmod +x "$NPM_BIN/ctx7"
FAKE
chmod +x "$tmp/bin/npm"

export PATH="$tmp/bin:$tmp/npm-bin:/usr/bin:/bin" CALLS="$tmp/calls" NPM_BIN="$tmp/npm-bin" FAKE_VERSION="$version"
run() {
  rm -f -- "$NPM_BIN/ctx7"
  : > "$CALLS"
  env "$@" bash "$installer" > "$tmp/output" 2>&1
}
ctx7_calls() { grep '^ctx7 ' "$CALLS" || true; }

run || fail "installer failed with the pinned version: $(cat "$tmp/output")"
grep -qxF "npm install -g ctx7@$version" "$CALLS" || fail "installer did not install ctx7@$version: $(cat "$CALLS")"
[ "$(ctx7_calls)" = 'ctx7 --version' ] || fail "installer ran ctx7 for more than its version: $(ctx7_calls)"

if run FAKE_VERSION=0.0.0-unexpected; then fail 'installer accepted another ctx7 version'; fi
grep -qF '[install_ctx7] ERROR: ' "$tmp/output" || fail "no ERROR line for another version: $(cat "$tmp/output")"
grep -qF '0.0.0-unexpected' "$tmp/output" || fail "the version error does not show the found version: $(cat "$tmp/output")"

printf 'PASS: install_ctx7.bash installs the pinned ctx7 and rejects another version\n'
