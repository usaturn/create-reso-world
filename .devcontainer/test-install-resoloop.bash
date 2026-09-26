#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
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
    printf '%s\n' "${DOTNET_LIST_LINE:-}" ;;
  'tool install --global ResoLoop --prerelease'|'tool update --global ResoLoop --prerelease')
    printf '%s\n' "$*" >> "$DOTNET_CALLS"
    [ "${DOTNET_INSTALL_FAIL:-0}" = 0 ] || exit 16 ;;
  *) printf 'Unexpected dotnet invocation: %s\n' "$*" >&2; exit 17 ;;
esac
MOCK
chmod +x "$tmp/bin/dotnet"
cat > "$tmp/home/.dotnet/tools/resoloop" <<'MOCK'
#!/bin/bash
[ "${RESOLOOP_VERSION_FAIL:-0}" = 0 ] || exit 18
[ "$*" = '--version' ] || exit 19
printf 'resoloop test-version\n'
MOCK
chmod +x "$tmp/home/.dotnet/tools/resoloop"
export HOME="$tmp/home" PATH="$tmp/bin:$PATH" DOTNET_CALLS="$tmp/calls"
# 初回導入: 一覧が空でも --prerelease を付け、--version は付けない。
bash "$root/.devcontainer/install_resoloop.bash"
grep -qx 'tool install --global ResoLoop --prerelease' "$DOTNET_CALLS"
# 更新: 一覧の ID が一致したときだけ update する。
: > "$DOTNET_CALLS"
DOTNET_LIST_LINE='ResoLoop 0.1.0-preview.1 resoloop' bash "$root/.devcontainer/install_resoloop.bash"
grep -qx 'tool update --global ResoLoop --prerelease' "$DOTNET_CALLS"
# 無関係の部分一致はインストール扱い。
: > "$DOTNET_CALLS"
DOTNET_LIST_LINE='my-resoloop-plugin 1.0.0 other' bash "$root/.devcontainer/install_resoloop.bash"
grep -qx 'tool install --global ResoLoop --prerelease' "$DOTNET_CALLS"
# 一覧取得失敗時はインストールしない。
: > "$DOTNET_CALLS"
if DOTNET_LIST_FAIL=1 bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
[ ! -s "$DOTNET_CALLS" ]
# インストーラ成功でも CLI 起動失敗なら失敗。
if RESOLOOP_VERSION_FAIL=1 bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
if DOTNET_LIST_LINE='ResoLoop 0.1.0-preview.1 resoloop' DOTNET_INSTALL_FAIL=1 \
    bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
# SDK 不在、SDK 一覧取得失敗、ダウンロード失敗も伝える。
if DOTNET_SDKS='8.0.100 [/usr/share/dotnet/sdk]' bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
if DOTNET_SDK_FAIL=1 bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
if DOTNET_INSTALL_FAIL=1 bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
# shim がない場合も PATH の別位置にあるコマンドで誤って通さない。
rm "$HOME/.dotnet/tools/resoloop"
if bash "$root/.devcontainer/install_resoloop.bash"; then exit 1; fi
printf 'PASS: ResoLoop global tool install/update and failures\n'
