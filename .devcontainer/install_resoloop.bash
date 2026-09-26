#!/bin/bash
# .devcontainer/resoloop.lock が指定する版の ResoLoop を導入する。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 6.2 節
# 環境変数 RESOLOOP_LOCK_FILE でロックファイルを差し替えられる（テスト用。fork モードでは scripts/resoloop-fork.sh にも引き継がれる）
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lock="${RESOLOOP_LOCK_FILE:-$root/.devcontainer/resoloop.lock}"
fail() { printf 'ResoLoop setup: %s\n' "$1" >&2; exit 1; }
# shellcheck source=resoloop-lock.bash
source "$root/.devcontainer/resoloop-lock.bash"
resoloop_lock_load "$lock" || fail "cannot read $lock."
expected="$RESOLOOP_EXPECTED_VERSION"

command -v dotnet >/dev/null 2>&1 || fail 'dotnet is not available.'
sdks="$(dotnet --list-sdks </dev/null)" || fail 'cannot list .NET SDKs.'
grep -qE '^10\.' <<<"$sdks" || fail '.NET 10 SDK is not installed.'
installed="$(resoloop_installed_version)" || fail 'cannot list global .NET tools.'

if [ "$installed" = "$expected" ]; then
    printf 'ResoLoop setup: %s is already installed.\n' "$expected"
elif [ "$RESOLOOP_MODE" = fork ]; then
    bash "$root/scripts/resoloop-fork.sh" install </dev/null \
        || fail 'building and installing the fork failed (check with bash scripts/resoloop-fork.sh status).'
elif [ -n "$installed" ]; then
    dotnet tool update --global ResoLoop --version "$expected" --allow-downgrade </dev/null \
        || fail "updating the global tool from $installed to $expected failed."
else
    dotnet tool install --global ResoLoop --version "$expected" </dev/null \
        || fail "installing the global tool $expected failed."
fi

# PATH 上の別の resoloop で誤って通らないよう、グローバルツールの配置先を直接呼ぶ
out="$("$HOME/.dotnet/tools/resoloop" --version </dev/null)" || fail 'installed CLI cannot run on this container.'
actual="$(resoloop_version_of "$out")" || fail 'resoloop --version printed nothing.'
[ "$actual" = "$expected" ] || fail "resoloop --version reports $actual, but $lock expects $expected."
printf 'ResoLoop setup: resoloop %s matches the lock.\n' "$actual"
