#!/bin/bash
# Resonite の開発ツール（.NET 10 SDK・resoloop・Blender）が動くことを確かめる。postCreate の確認と手動の確認に使う。
# ResoLoop は版を固定せず最新を使うので、版の値は比べず、動いて版を表示することだけを確かめる
# （仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-4）
set -euo pipefail

# 一覧を変数に取ってから探す（pipefail の下で grep -q が dotnet を SIGPIPE で止めないように）
if ! sdks="$(dotnet --list-sdks </dev/null)" || ! grep -qE '^10\.' <<<"$sdks"; then
    echo 'Toolchain verification: .NET 10 SDK is unavailable.' >&2
    exit 1
fi
if ! version_output="$(resoloop --version </dev/null)"; then
    echo 'Toolchain verification: resoloop cannot run.' >&2
    exit 1
fi
version="$(sed -n '/[^[:space:]]/{s/^[[:space:]]*//;s/[[:space:]]*$//;p;q;}' <<<"$version_output")"
if [ -z "$version" ]; then
    echo 'Toolchain verification: resoloop --version printed nothing.' >&2
    exit 1
fi
printf 'Toolchain verification: resoloop %s\n' "$version"
if ! blender --background --factory-startup --python-exit-code 1 \
    --python-expr 'import bpy; assert bpy.app.background' </dev/null; then
    echo 'Toolchain verification: Blender cannot run headlessly.' >&2
    exit 1
fi
