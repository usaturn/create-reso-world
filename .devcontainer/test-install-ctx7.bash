#!/bin/bash
# Context7 CLI の導入（.devcontainer/install_ctx7.bash）を、偽の npm と偽の ctx7 でネットワークを使わずに実行する。
# ctx7@latest を入れること、ctx7 を --version 以外で呼ばないこと（ctx7 setup は共有の ~/.claude・~/.codex などへ
# 書き込み、導入は成功するので気付けない）、PATH の前のほうにある別の ctx7 を受け入れないこと（黙って別の ctx7 を
# 使い続ける）を確かめる
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
installer="$root/.devcontainer/install_ctx7.bash"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 偽の npm は引数を記録し、root -g には偽のグローバルの node_modules（NPM_ROOT）を返す。install では NPM_ROOT/ctx7/ に
# 偽の ctx7 を置き、グローバルの bin（NPM_BIN）から symlink する。ファイル名は実物と変え、名前を仮定しないことも確かめる
mkdir -p "$tmp/bin" "$tmp/shadow" "$tmp/prefix/bin" "$tmp/prefix/lib/node_modules"
cat > "$tmp/bin/npm" <<'FAKE'
#!/bin/bash
printf 'npm %s\n' "$*" >> "$CALLS"
if [ "$*" = 'root -g' ]; then printf '%s\n' "$NPM_ROOT"; exit 0; fi
mkdir -p "$NPM_ROOT/ctx7/bin"
cat > "$NPM_ROOT/ctx7/bin/fake-cli" <<'CTX7'
#!/bin/bash
printf 'ctx7 %s\n' "$*" >> "$CALLS"
[ "$*" = --version ] || exit 0
printf '9.9.9\n'
CTX7
chmod +x "$NPM_ROOT/ctx7/bin/fake-cli"
ln -sf ../lib/node_modules/ctx7/bin/fake-cli "$NPM_BIN/ctx7"
FAKE
chmod +x "$tmp/bin/npm"
# PATH の前のほうに置く別の ctx7
cat > "$tmp/shadow/ctx7" <<'SHADOW'
#!/bin/bash
printf 'shadow %s\n' "$*" >> "$CALLS"
printf '9.9.9\n'
SHADOW
chmod +x "$tmp/shadow/ctx7"

export CALLS="$tmp/calls" NPM_ROOT="$tmp/prefix/lib/node_modules" NPM_BIN="$tmp/prefix/bin"
export PATH="$tmp/bin:$NPM_BIN:/usr/bin:/bin"
run() {
  rm -rf -- "${NPM_ROOT:?}/ctx7" "${NPM_BIN:?}/ctx7"
  : > "$CALLS"
  env "$@" bash "$installer" > "$tmp/output" 2>&1
}
ctx7_calls() { grep '^ctx7 ' "$CALLS" || true; }

run || fail "installer failed: $(cat "$tmp/output")"
grep -qxF 'npm install -g ctx7@latest' "$CALLS" || fail "installer did not install ctx7@latest: $(cat "$CALLS")"
[ "$(ctx7_calls)" = 'ctx7 --version' ] || fail "installer ran ctx7 for more than its version: $(ctx7_calls)"

if run PATH="$tmp/bin:$tmp/shadow:$NPM_BIN:/usr/bin:/bin"; then
  fail 'installer accepted a ctx7 that comes before the npm global one on PATH'
fi
grep -qF '[install_ctx7] ERROR: ' "$tmp/output" || fail "no ERROR line for the other ctx7: $(cat "$tmp/output")"
! grep -qF 'installed at' "$tmp/output" || fail "installer reported success for the other ctx7: $(cat "$tmp/output")"

printf 'PASS: install_ctx7.bash installs ctx7@latest and rejects another ctx7 first on PATH\n'
