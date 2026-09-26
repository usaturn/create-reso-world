#!/bin/bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lock="${RESOLOOP_LOCK_FILE:-$root/.devcontainer/resoloop.lock}"
# shellcheck source=resoloop-lock.bash
source "$root/.devcontainer/resoloop-lock.bash"

if ! dotnet --list-sdks | grep -qE '^10\.'; then
    echo 'Toolchain verification: .NET 10 SDK is unavailable.' >&2
    exit 1
fi
if ! resoloop_lock_load "$lock"; then
    echo "Toolchain verification: cannot read $lock." >&2
    exit 1
fi
if ! version_output="$(resoloop --version </dev/null)"; then
    echo 'Toolchain verification: resoloop cannot run.' >&2
    exit 1
fi
actual="$(resoloop_version_of "$version_output" || true)"
if [ "$actual" != "$RESOLOOP_EXPECTED_VERSION" ]; then
    echo "Toolchain verification: resoloop reports ${actual:-nothing}, but $lock expects $RESOLOOP_EXPECTED_VERSION." >&2
    exit 1
fi
if ! blender --background --factory-startup --python-exit-code 1 \
    --python-expr 'import bpy; assert bpy.app.background' </dev/null; then
    echo 'Toolchain verification: Blender cannot run headlessly.' >&2
    exit 1
fi
