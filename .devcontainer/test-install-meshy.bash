#!/bin/bash
# Execute the installer offline: catch swallowed install/probe failures and credential leakage.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
mkdir -p "$tmp/bin" "$tmp/home"
export HOME="$tmp/home" PATH="$tmp/bin:/usr/bin:/bin" CALLS="$tmp/calls" FAKE_BIN="$tmp/bin"
export MESHY_API_KEY='installer-secret-sentinel'
cat > "$tmp/bin/npm" <<'FAKE'
#!/bin/bash
printf 'npm %s\n' "$*" >> "$CALLS"
# Verify the global package-install shape, not a copied version setting.
[ "$#" -eq 3 ] && [ "$1" = install ] && [ "$2" = -g ] || exit 91
[[ "$3" == meshy-cli@?* ]] || exit 91
[ -z "${MESHY_API_KEY+x}" ] || exit 92
[ "${FAIL_NPM:-0}" = 0 ] || exit 1
[ "${MISSING_CLI:-0}" = 0 ] || exit 0
cat > "$FAKE_BIN/meshy" <<'CLI'
#!/bin/bash
[ -z "${MESHY_API_KEY+x}" ] || exit 92
printf 'meshy %s\n' "$*" >> "$CALLS"
case "$*" in
  '--no-update-check --version') [ "${FAIL_VERSION:-0}" = 0 ] || exit 1 ;;
  '--no-update-check --help') [ "${FAIL_HELP:-0}" = 0 ] || exit 1 ;;
  *) exit 93 ;;
esac
printf 'offline probe OK\n'
CLI
chmod +x "$FAKE_BIN/meshy"
FAKE
chmod +x "$tmp/bin/npm"
run() {
    rm -f "$tmp/bin/meshy"
    : > "$CALLS"
    env "$@" bash "$root/.devcontainer/install_meshy.bash" > "$tmp/output" 2>&1
}
run || fail 'installation with no usable CLI credentials should succeed'
[ "$(wc -l < "$CALLS")" -eq 3 ] || fail 'installer did not run both offline probes'
grep -q 'installer-secret-sentinel' "$tmp/output" && fail 'installer exposed the key'
for setting in FAIL_NPM=1 MISSING_CLI=1 FAIL_VERSION=1 FAIL_HELP=1; do
    if run "$setting"; then fail "installer ignored $setting"; fi
done
unset MESHY_API_KEY
run || fail 'keyless installation failed'
printf 'PASS: Meshy installer succeeds offline and propagates all install/probe failures\n'
