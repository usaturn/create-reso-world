#!/bin/bash
# .devcontainer/install_resoloop.bash が NuGet の最新の公開版を導入することを、モックの dotnet で検査する
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-1〜D-3
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# モックの dotnet: tool update の呼び出しを DOTNET_CALLS に記録する。update は MOCK_STATE に MOCK_LATEST の版を書き、
# ~/.dotnet/tools/resoloop に版を返す shim を置く
mkdir -p "$tmp/home/.dotnet/tools" "$tmp/bin"
cat > "$tmp/bin/dotnet" <<'MOCK'
#!/bin/bash
case "$*" in
  --list-sdks) printf '10.0.100 [/usr/share/dotnet/sdk]\n' ;;
  'tool list --global')
    printf 'Package Id Version Commands\n'
    [ ! -s "$MOCK_STATE" ] || printf 'resoloop %s resoloop\n' "$(cat "$MOCK_STATE")" ;;
  'tool update --global ResoLoop --prerelease --allow-downgrade')
    printf '%s\n' "$*" >> "$DOTNET_CALLS"
    printf '%s\n' "$MOCK_LATEST" > "$MOCK_STATE"
    printf '#!/bin/bash\nprintf "%%s\\n" %q\n' "$MOCK_LATEST" > "$HOME/.dotnet/tools/resoloop"
    chmod +x "$HOME/.dotnet/tools/resoloop" ;;
  *) printf 'Unexpected dotnet invocation: %s\n' "$*" >&2; exit 17 ;;
esac
MOCK
chmod +x "$tmp/bin/dotnet"
export HOME="$tmp/home" PATH="$tmp/bin:$PATH" DOTNET_CALLS="$tmp/calls" MOCK_STATE="$tmp/installed" MOCK_LATEST=1.2.3-preview.4
installer="$root/.devcontainer/install_resoloop.bash"

installed_as() {  # $1=導入済みとして扱う版（空なら未導入）。shim もその版を返す
  : > "$DOTNET_CALLS"
  rm -f -- "${HOME:?}/.dotnet/tools/resoloop"
  if [ -z "$1" ]; then
    : > "$MOCK_STATE"
    return
  fi
  printf '%s\n' "$1" > "$MOCK_STATE"
  printf '#!/bin/bash\nprintf "%%s\\n" %q\n' "$1" > "$HOME/.dotnet/tools/resoloop"
  chmod +x "$HOME/.dotnet/tools/resoloop"
}
expect_ok() {  # $1=出力に含まれるべき文字列、残り=環境変数の代入（env に渡す）
  local needle="$1"
  shift
  env "$@" bash "$installer" > "$tmp/out.txt" 2>&1 || fail "installer failed (expected: $needle): $(cat "$tmp/out.txt")"
  grep -qF -- "$needle" "$tmp/out.txt" || fail "expected '$needle' in: $(cat "$tmp/out.txt")"
}
updated_once() {
  [ "$(cat "$DOTNET_CALLS")" = 'tool update --global ResoLoop --prerelease --allow-downgrade' ] \
    || fail "expected one update call, got: $(cat "$DOTNET_CALLS")"
}

# 1. 未導入（正例）: --prerelease で最新を導入し、導入した版を表示する
installed_as ''
expect_ok 'installed resoloop 1.2.3-preview.4.'
updated_once

# 2. fork のビルド（公開版より大きい版）を導入済み: --allow-downgrade 付きの update で最新の公開版に戻す。
#    戻せないと「常に最新」（#45）が黙って崩れ、fork のビルドが残ったまま気付けない
installed_as 1.2.3-preview.4.fork.20261006.gabc1234
expect_ok 'resoloop 1.2.3-preview.4 is installed (was 1.2.3-preview.4.fork.20261006.gabc1234).'
updated_once
[ "$(cat "$MOCK_STATE")" = 1.2.3-preview.4 ] || fail 'the fork build was not replaced'

printf 'PASS: ResoLoop install brings in the latest NuGet release and returns from a fork build\n'
