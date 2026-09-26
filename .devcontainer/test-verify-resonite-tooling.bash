#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
# shellcheck source=resoloop-lock.bash
source "$root/.devcontainer/resoloop-lock.bash"
resoloop_lock_load "$root/.devcontainer/resoloop.lock"
mkdir -p "$tmp/bin"
cat > "$tmp/bin/dotnet" <<'MOCK'
#!/bin/bash
[ "$*" = '--list-sdks' ] || exit 11
printf '10.0.100 [/usr/share/dotnet/sdk]\n'
MOCK
cat > "$tmp/bin/resoloop" <<'MOCK'
#!/bin/bash
[ "$*" = '--version' ] || exit 12
[ "${RESOLOOP_FAIL:-0}" = 0 ] || exit 15
printf '%s\n' "$MOCK_RESOLOOP_VERSION"
MOCK
cat > "$tmp/bin/blender" <<'MOCK'
#!/bin/bash
case " $* " in *' --background '*' --python-expr '*) ;; *) exit 13 ;; esac
[ "${BLENDER_FAIL:-0}" = 0 ] || exit 14
MOCK
chmod +x "$tmp/bin/"*
export PATH="$tmp/bin:$PATH" MOCK_RESOLOOP_VERSION="$RESOLOOP_EXPECTED_VERSION"
bash "$root/.devcontainer/verify-resonite-tooling.bash"
if RESOLOOP_FAIL=1 bash "$root/.devcontainer/verify-resonite-tooling.bash"; then exit 1; fi
if BLENDER_FAIL=1 bash "$root/.devcontainer/verify-resonite-tooling.bash"; then exit 1; fi
# resoloop の版がロックの期待版と違えば失敗し、両方の版を表示する
if out="$(MOCK_RESOLOOP_VERSION=0.0.1 bash "$root/.devcontainer/verify-resonite-tooling.bash" 2>&1)"; then exit 1; fi
grep -qF "resoloop reports 0.0.1, but $root/.devcontainer/resoloop.lock expects $RESOLOOP_EXPECTED_VERSION" <<<"$out"
# ロックが読めなければ失敗する
if RESOLOOP_LOCK_FILE="$tmp/missing.lock" bash "$root/.devcontainer/verify-resonite-tooling.bash" 2>/dev/null; then exit 1; fi
installer="$root/.devcontainer/install_beforehand.bash"
grep -qF 'bash .devcontainer/install_resoloop.bash' "$installer"
grep -qF 'bash .devcontainer/verify-resonite-tooling.bash' "$installer"
grep -qF 'step "Installing the ResoLoop version pinned in .devcontainer/resoloop.lock"' "$installer"
declared_steps="$(sed -n 's/^readonly STEP_TOTAL=//p' "$installer")"
actual_steps="$(grep -c '^step "' "$installer")"
[ "$declared_steps" -eq "$actual_steps" ]
grep -qF 'PATH="$HOME/.dotnet/tools:$PATH"' "$root/.devcontainer/zshrc.txt"
printf 'PASS: toolchain smoke test and postCreate integration\n'
