#!/bin/bash
set -euo pipefail

if ! command -v dotnet >/dev/null 2>&1; then
    echo 'ResoLoop setup: dotnet is not available.' >&2
    exit 1
fi
if ! dotnet --list-sdks | grep -qE '^10\.'; then
    echo 'ResoLoop setup: .NET 10 SDK is not installed.' >&2
    exit 1
fi
if ! installed="$(dotnet tool list --global)"; then
    echo 'ResoLoop setup: cannot list global .NET tools.' >&2
    exit 1
fi
if printf '%s\n' "$installed" | awk 'tolower($1)=="resoloop" {found=1} END {exit !found}'; then
    dotnet tool update --global ResoLoop --prerelease </dev/null || {
        echo 'ResoLoop setup: updating the global tool failed.' >&2
        exit 1
    }
else
    dotnet tool install --global ResoLoop --prerelease </dev/null || {
        echo 'ResoLoop setup: installing the global tool failed.' >&2
        exit 1
    }
fi
export PATH="$HOME/.dotnet/tools:$PATH"
if ! "$HOME/.dotnet/tools/resoloop" --version </dev/null; then
    echo 'ResoLoop setup: installed CLI cannot run on this container.' >&2
    exit 1
fi
