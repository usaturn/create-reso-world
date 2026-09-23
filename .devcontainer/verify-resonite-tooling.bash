#!/bin/bash
set -euo pipefail

if ! dotnet --list-sdks | grep -qE '^10\.'; then
    echo 'Toolchain verification: .NET 10 SDK is unavailable.' >&2
    exit 1
fi
if ! resoloop --version </dev/null; then
    echo 'Toolchain verification: resoloop cannot run.' >&2
    exit 1
fi
if ! blender --background --factory-startup --python-exit-code 1 \
    --python-expr 'import bpy; assert bpy.app.background' </dev/null; then
    echo 'Toolchain verification: Blender cannot run headlessly.' >&2
    exit 1
fi
