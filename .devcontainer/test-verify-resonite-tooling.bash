#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
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
printf 'resoloop test-version\n'
MOCK
cat > "$tmp/bin/blender" <<'MOCK'
#!/bin/bash
case " $* " in *' --background '*' --python-expr '*) ;; *) exit 13 ;; esac
[ "${BLENDER_FAIL:-0}" = 0 ] || exit 14
MOCK
chmod +x "$tmp/bin/"*
export PATH="$tmp/bin:$PATH"
bash "$root/.devcontainer/verify-resonite-tooling.bash"
if RESOLOOP_FAIL=1 bash "$root/.devcontainer/verify-resonite-tooling.bash"; then exit 1; fi
if BLENDER_FAIL=1 bash "$root/.devcontainer/verify-resonite-tooling.bash"; then exit 1; fi
installer="$root/.devcontainer/install_beforehand.bash"
grep -qF 'bash .devcontainer/install_resoloop.bash' "$installer"
grep -qF 'bash .devcontainer/verify-resonite-tooling.bash' "$installer"
declared_steps="$(sed -n 's/^readonly STEP_TOTAL=//p' "$installer")"
actual_steps="$(grep -c '^step "' "$installer")"
[ "$declared_steps" -eq "$actual_steps" ]
grep -qF 'PATH="$HOME/.dotnet/tools:$PATH"' "$root/.devcontainer/zshrc.txt"
printf 'PASS: toolchain smoke test and postCreate integration\n'
