#!/bin/bash
# NuGet の最新の公開版の ResoLoop を導入する。postCreate と、rebuild せずに最新へ上げるときに実行する。
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-1〜D-3
# 公開版は今はプレリリースだけなので --prerelease を付ける。fork のビルド（公開版より大きい版になり得る）からも
# 戻せるよう --allow-downgrade を付ける。update は未導入なら導入する。
# NuGet に届かないなどで更新できなくても、導入済みの版があれば警告してその版のまま続ける。
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail() { printf 'ResoLoop setup: %s\n' "$1" >&2; exit 1; }
# shellcheck source=resoloop-tool.bash
source "$root/.devcontainer/resoloop-tool.bash"

command -v dotnet >/dev/null 2>&1 || fail 'dotnet is not available.'
sdks="$(dotnet --list-sdks </dev/null)" || fail 'cannot list .NET SDKs.'
grep -qE '^10\.' <<<"$sdks" || fail '.NET 10 SDK is not installed.'
before="$(resoloop_installed_version)" || fail 'cannot list global .NET tools.'

if ! dotnet tool update --global ResoLoop --prerelease --allow-downgrade </dev/null; then
    [ -n "$before" ] || fail 'installing the latest ResoLoop release from NuGet failed.'
    printf 'ResoLoop setup: WARN: updating to the latest release failed (is NuGet reachable?); keeping %s.\n' "$before" >&2
fi

installed="$(resoloop_installed_version)" || fail 'cannot list global .NET tools.'
[ -n "$installed" ] || fail 'ResoLoop is missing from dotnet tool list --global after the update.'
# PATH 上の別の resoloop で誤って通らないよう、グローバルツールの配置先を直接呼ぶ
out="$("$HOME/.dotnet/tools/resoloop" --version </dev/null)" || fail 'installed CLI cannot run on this container.'
actual="$(resoloop_version_of "$out")" || fail 'resoloop --version printed nothing.'
[ "$actual" = "$installed" ] || fail "resoloop --version reports $actual, but dotnet tool list --global reports $installed."
if [ -z "$before" ]; then
    printf 'ResoLoop setup: installed resoloop %s.\n' "$actual"
elif [ "$before" = "$actual" ]; then
    printf 'ResoLoop setup: resoloop %s is installed (unchanged).\n' "$actual"
else
    printf 'ResoLoop setup: resoloop %s is installed (was %s).\n' "$actual" "$before"
fi
