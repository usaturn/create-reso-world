#!/bin/bash
# .devcontainer/verify-resonite-tooling.bash（.NET 10 SDK・resoloop・Blender の確認）と、postCreate からの呼び出しを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
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
export PATH="$tmp/bin:$PATH" MOCK_RESOLOOP_VERSION=1.2.3-preview.4
verify="$root/.devcontainer/verify-resonite-tooling.bash"

# 1. resoloop が版を表示すれば通り、確かめた版を表示する（版の値は比べない）
out="$(bash "$verify" 2>&1)" || fail "verification failed: $out"
grep -qF 'Toolchain verification: resoloop 1.2.3-preview.4' <<<"$out" || fail "the checked version was not shown: $out"
# 2. resoloop が動かない・版を表示しない、Blender が動かないときは失敗する
if RESOLOOP_FAIL=1 bash "$verify" 2>/dev/null; then fail 'passed although resoloop cannot run'; fi
if out="$(MOCK_RESOLOOP_VERSION='' bash "$verify" 2>&1)"; then fail 'passed although resoloop printed no version'; fi
grep -qF 'resoloop --version printed nothing' <<<"$out" || fail "unexpected message: $out"
if BLENDER_FAIL=1 bash "$verify" 2>/dev/null; then fail 'passed although Blender cannot run'; fi

# 3. postCreate が導入・確認・同梱スキルの表示を呼び、宣言した手順の数が実際の手順の数と同じ
installer="$root/.devcontainer/install_beforehand.bash"
for s in 'bash .devcontainer/install_resoloop.bash' 'bash .devcontainer/verify-resonite-tooling.bash' \
  'bash .devcontainer/report-resoloop-skills.bash'; do
  grep -qF -- "$s" "$installer" || fail "install_beforehand.bash does not run: $s"
done
declared_steps="$(sed -n 's/^readonly STEP_TOTAL=//p' "$installer")"
actual_steps="$(grep -c '^step "' "$installer")"
[ "$declared_steps" -eq "$actual_steps" ] || fail "STEP_TOTAL is $declared_steps, but there are $actual_steps steps"
grep -qF 'PATH="$HOME/.dotnet/tools:$PATH"' "$root/.devcontainer/zshrc.txt" || fail 'zshrc.txt does not put ~/.dotnet/tools on PATH'
printf 'PASS: toolchain smoke test and postCreate integration\n'
