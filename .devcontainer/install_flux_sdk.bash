#!/bin/bash
# ProtoFlux 用の Flux-SDK（NuGet の Papaltine.FluxSDK、コマンド flux-sdk）を、ResoLoop が検証している版で導入する。
# postCreate が呼び、失敗しても postCreate は警告して続ける。未導入のときに入れる・別の版から戻すときも実行する。
# 仕様: docs/superpowers/specs/2026-10-24-create-reso-world-issue251-252-flux-sdk-postcreate-design.md D-2〜D-5
# ResoLoop と違い版を固定する。ResoLoop が検証しているのは 1.9 系で、NuGet の最新（1.10 系）は resoloop doctor が
# 警告する。ResoLoop が検証する系列を変えたら（doctor の flux-sdk が outside tested series の warning になる）、
# ResoLoop が案内する版に FLUX_SDK_VERSION を合わせる。update は未導入なら導入し、
# --allow-downgrade で別の版からも戻す。NuGet に届かなくても、同じ版が導入済みなら警告してその版のまま続ける。
set -euo pipefail

readonly FLUX_SDK_VERSION=1.9.0
fail() { printf 'Flux-SDK setup: %s\n' "$1" >&2; exit 1; }

# dotnet tool list --global から Papaltine.FluxSDK の導入済み版を出力する（未導入なら何も出力しない）
installed_version() {
    local listing
    listing="$(dotnet tool list --global </dev/null)" || return 1
    awk 'tolower($1) == "papaltine.fluxsdk" && !found { print $2; found = 1 }' <<<"$listing"
}

command -v dotnet >/dev/null 2>&1 || fail 'dotnet is not available.'
before="$(installed_version)" || fail 'cannot list global .NET tools.'

if ! dotnet tool update --global Papaltine.FluxSDK --version "$FLUX_SDK_VERSION" --allow-downgrade </dev/null; then
    [ "$before" = "$FLUX_SDK_VERSION" ] \
        || fail "installing Papaltine.FluxSDK $FLUX_SDK_VERSION from NuGet failed (is NuGet reachable?)."
    printf 'Flux-SDK setup: WARN: updating Papaltine.FluxSDK failed (is NuGet reachable?); keeping %s.\n' "$before" >&2
fi

installed="$(installed_version)" || fail 'cannot list global .NET tools.'
[ "$installed" = "$FLUX_SDK_VERSION" ] \
    || fail "dotnet tool list --global reports Papaltine.FluxSDK ${installed:-missing}, not $FLUX_SDK_VERSION."
# flux-sdk --version は版を表示した後にサブコマンドの一覧を出して 2 で終わるので、終了コードではなく表示した版で確かめる。
# PATH 上の別の flux-sdk で誤って通らないよう、グローバルツールの配置先を直接呼ぶ
out="$("$HOME/.dotnet/tools/flux-sdk" --version </dev/null 2>&1)" || true
actual="$(sed -n '/^[[:space:]]*Flux SDK Version:/{s/^[[:space:]]*Flux SDK Version:[[:space:]]*\([^+[:space:]]*\).*/\1/p;q;}' <<<"$out")"
[ -n "$actual" ] || fail 'installed flux-sdk cannot run on this container (flux-sdk --version printed no version).'
[ "$actual" = "$FLUX_SDK_VERSION" ] || fail "flux-sdk --version reports $actual, but dotnet tool list --global reports $installed."
if [ -z "$before" ]; then
    printf 'Flux-SDK setup: installed flux-sdk %s.\n' "$actual"
elif [ "$before" = "$actual" ]; then
    printf 'Flux-SDK setup: flux-sdk %s is installed (unchanged).\n' "$actual"
else
    printf 'Flux-SDK setup: flux-sdk %s is installed (was %s).\n' "$actual" "$before"
fi
