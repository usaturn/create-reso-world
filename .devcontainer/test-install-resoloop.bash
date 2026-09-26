#!/bin/bash
# .devcontainer/install_resoloop.bash が仕様 6.2 節の表どおりに動くことを、モックの dotnet と一時ロックで検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# モックの dotnet: 呼び出しを DOTNET_CALLS に記録する。tool install/update は MOCK_STATE に版を書き、
# ~/.dotnet/tools/resoloop に版（MOCK_SHIM_VERSION があればその値）を返す shim を置く
mkdir -p "$tmp/home/.dotnet/tools" "$tmp/bin"
cat > "$tmp/bin/dotnet" <<'MOCK'
#!/bin/bash
case "$*" in
  --list-sdks)
    [ "${DOTNET_SDK_FAIL:-0}" = 0 ] || exit 20
    printf '%s\n' "${DOTNET_SDKS:-10.0.100 [/usr/share/dotnet/sdk]}" ;;
  'tool list --global')
    [ "${DOTNET_LIST_FAIL:-0}" = 0 ] || exit 15
    printf 'Package Id Version Commands\n'
    [ -z "${DOTNET_LIST_LINE:-}" ] || printf '%s\n' "$DOTNET_LIST_LINE"
    [ ! -s "$MOCK_STATE" ] || printf 'resoloop %s resoloop\n' "$(cat "$MOCK_STATE")" ;;
  'tool install --global ResoLoop --version '*|'tool update --global ResoLoop --version '*)
    printf '%s\n' "$*" >> "$DOTNET_CALLS"
    [ "${DOTNET_INSTALL_FAIL:-0}" = 0 ] || exit 16
    ver="$6"
    printf '%s\n' "$ver" > "$MOCK_STATE"
    printf '#!/bin/bash\nprintf "%%s\\n" %q\n' "${MOCK_SHIM_VERSION:-$ver}" > "$HOME/.dotnet/tools/resoloop"
    chmod +x "$HOME/.dotnet/tools/resoloop" ;;
  *) printf 'Unexpected dotnet invocation: %s\n' "$*" >&2; exit 17 ;;
esac
MOCK
chmod +x "$tmp/bin/dotnet"
export HOME="$tmp/home" PATH="$tmp/bin:$PATH" DOTNET_CALLS="$tmp/calls" MOCK_STATE="$tmp/installed"

write_lock() {  # $1=モード。nuget の期待版は 1.2.3-preview.4、fork の期待版は 1.2.3-preview.4.pr1.test
  cat > "$tmp/resoloop.lock" <<EOF
RESOLOOP_MODE=$1
RESOLOOP_NUGET_VERSION=1.2.3-preview.4
RESOLOOP_FORK_ORIGIN=https://example.com/fork/resoloop.git
RESOLOOP_FORK_UPSTREAM=https://example.com/upstream/resoloop.git
RESOLOOP_FORK_REF=fix/x
RESOLOOP_FORK_COMMIT=0123456789abcdef0123456789abcdef01234567
RESOLOOP_FORK_PACKAGE_VERSION=1.2.3-preview.4.pr1.test
RESOLOOP_FORK_PR=https://example.com/upstream/resoloop/pull/1
RESOLOOP_FORK_SDK=10.0.201
EOF
}
export RESOLOOP_LOCK_FILE="$tmp/resoloop.lock"
reset() {  # 未導入の状態に戻す
  : > "$DOTNET_CALLS"
  : > "$MOCK_STATE"
  rm -f "$HOME/.dotnet/tools/resoloop"
}
installer="$root/.devcontainer/install_resoloop.bash"
expect_fail() {  # $1=出力に含まれるべき文字列、残り=環境変数の代入（env に渡す）
  local needle="$1" out
  shift
  if out="$(env "$@" bash "$installer" 2>&1)"; then fail "installer succeeded (expected: $needle)"; fi
  grep -qF -- "$needle" <<<"$out" || fail "expected '$needle' in: $out"
}
expect_ok() {  # $1=出力に含まれるべき文字列、残り=環境変数の代入（env に渡す）
  local needle="$1" out
  shift
  out="$(env "$@" bash "$installer" 2>&1)" || fail "installer failed (expected: $needle): $out"
  grep -qF -- "$needle" <<<"$out" || fail "expected '$needle' in: $out"
}

# 1. nuget モード・未導入: ロックの版を --version で指定して install する
write_lock nuget
reset
expect_ok 'resoloop 1.2.3-preview.4 matches the lock'
grep -qx 'tool install --global ResoLoop --version 1.2.3-preview.4' "$DOTNET_CALLS" || fail 'nuget install call'

# 2. nuget モード・同じ版を導入済み: 何もせず、--version の照合だけ行う
: > "$DOTNET_CALLS"
expect_ok '1.2.3-preview.4 is already installed'
[ ! -s "$DOTNET_CALLS" ] || fail 'reinstalled an installed version'
printf '#!/bin/bash\nprintf "0.0.1\\n"\n' > "$HOME/.dotnet/tools/resoloop"
expect_fail 'resoloop --version reports 0.0.1, but'

# 3. nuget モード・別の版を導入済み: --allow-downgrade 付きで update する（ダウングレードも含む）
reset
printf '9.0.0\n' > "$MOCK_STATE"
expect_ok 'matches the lock'
grep -qx 'tool update --global ResoLoop --version 1.2.3-preview.4 --allow-downgrade' "$DOTNET_CALLS" || fail 'nuget update call'

# 4. 名前の一部だけが一致するパッケージは未導入として扱う
reset
expect_ok 'matches the lock' DOTNET_LIST_LINE='my-resoloop-plugin 1.0.0 other'
grep -qx 'tool install --global ResoLoop --version 1.2.3-preview.4' "$DOTNET_CALLS" || fail 'partial match treated as installed'

# 5. 導入後の --version がロックと違えば失敗する
reset
expect_fail 'resoloop --version reports 0.0.2, but' MOCK_SHIM_VERSION=0.0.2

# 6. 失敗の伝達: 一覧取得の失敗（何も導入しない）、install / update の失敗、SDK が無い・一覧が取れない、shim が無い、ロックが不正
reset
expect_fail 'cannot list global .NET tools' DOTNET_LIST_FAIL=1
[ ! -s "$DOTNET_CALLS" ] || fail 'installed although the tool list failed'
expect_fail 'installing the global tool 1.2.3-preview.4 failed' DOTNET_INSTALL_FAIL=1
reset
printf '9.0.0\n' > "$MOCK_STATE"
expect_fail 'updating the global tool from 9.0.0 to 1.2.3-preview.4 failed' DOTNET_INSTALL_FAIL=1
reset
expect_fail '.NET 10 SDK is not installed' 'DOTNET_SDKS=8.0.100 [/usr/share/dotnet/sdk]'
expect_fail 'cannot list .NET SDKs' DOTNET_SDK_FAIL=1
printf '1.2.3-preview.4\n' > "$MOCK_STATE"
expect_fail 'installed CLI cannot run on this container'
sed -i '/^RESOLOOP_FORK_SDK=/d' "$tmp/resoloop.lock"
expect_fail 'cannot read'

# 7. fork モード: 導入済みの版が違えば scripts/resoloop-fork.sh install に任せ、同じなら呼ばない
#    （install_resoloop.bash は自分の位置からリポジトリを決めるので、一時リポジトリへ写して実行する）
mkdir -p "$tmp/repo/.devcontainer" "$tmp/repo/scripts"
cp "$installer" "$root/.devcontainer/resoloop-lock.bash" "$tmp/repo/.devcontainer/"
cat > "$tmp/repo/scripts/resoloop-fork.sh" <<'MOCK'
#!/bin/bash
printf 'fork %s lock=%s\n' "$*" "$RESOLOOP_LOCK_FILE" >> "$DOTNET_CALLS"
[ "${FORK_FAIL:-0}" = 0 ] || exit 4
printf '1.2.3-preview.4.pr1.test\n' > "$MOCK_STATE"
printf '#!/bin/bash\nprintf "1.2.3-preview.4.pr1.test\\n"\n' > "$HOME/.dotnet/tools/resoloop"
chmod +x "$HOME/.dotnet/tools/resoloop"
MOCK
installer="$tmp/repo/.devcontainer/install_resoloop.bash"
write_lock fork
reset
printf '1.2.3-preview.4\n' > "$MOCK_STATE"
expect_ok 'resoloop 1.2.3-preview.4.pr1.test matches the lock'
grep -qx "fork install lock=$tmp/resoloop.lock" "$DOTNET_CALLS" || fail 'fork mode did not delegate to resoloop-fork.sh install'
if grep -q '^tool ' "$DOTNET_CALLS"; then fail 'fork mode ran dotnet tool itself'; fi
: > "$DOTNET_CALLS"
expect_ok '1.2.3-preview.4.pr1.test is already installed'
[ ! -s "$DOTNET_CALLS" ] || fail 'fork mode rebuilt an installed version'
reset
expect_fail 'building and installing the fork failed' FORK_FAIL=1

printf 'PASS: ResoLoop install follows the lock (nuget and fork modes, failures)\n'
