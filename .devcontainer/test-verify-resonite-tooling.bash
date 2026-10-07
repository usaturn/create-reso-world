#!/bin/bash
# .devcontainer/verify-resonite-tooling.bash（.NET 10 SDK・resoloop・Blender の確認）と、postCreate の手順数を検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# Resolve before PATH is replaced with doubles. The NumPy rejection test below
# executes real headless Blender; no source-text assertion or fake import result.
real_blender="${RESOLOOP_BLENDER_EXECUTABLE:-$(command -v blender || true)}"
mkdir -p "$tmp/bin"
cat > "$tmp/bin/dotnet" <<'MOCK'
#!/bin/bash
[ "$*" = '--list-sdks' ] || exit 11
printf '10.0.100 [/usr/share/dotnet/sdk]\n'
MOCK
cat > "$tmp/bin/resoloop" <<'MOCK'
#!/bin/bash
[ "$*" = '--version' ] || exit 12
[ "${RESOLOOP_FAIL:-0}" = 0 ] || exit 15
printf '%s\n' "$MOCK_RESOLOOP_VERSION"
MOCK
cat > "$tmp/bin/blender" <<'MOCK'
#!/bin/bash
case " $* " in *' --background '*' --python-expr '*) ;; *) exit 13 ;; esac
[ "${BLENDER_FAIL:-0}" = 0 ] || exit 14
MOCK
chmod +x "$tmp/bin/"*
export PATH="$tmp/bin:$PATH" MOCK_RESOLOOP_VERSION=1.2.3-preview.4
verify="$root/.devcontainer/verify-resonite-tooling.bash"

# 1. resoloop が版を表示すれば通り、確かめた版を表示する（版の値は比べない）
out="$(bash "$verify" 2>&1)" || fail "verification failed: $out"
grep -qF 'Toolchain verification: resoloop 1.2.3-preview.4' <<<"$out" || fail "the checked version was not shown: $out"
# 2. resoloop が動かない・版を表示しない、Blender が動かないときは失敗する
if RESOLOOP_FAIL=1 bash "$verify" 2>/dev/null; then fail 'passed although resoloop cannot run'; fi
if out="$(MOCK_RESOLOOP_VERSION='' bash "$verify" 2>&1)"; then fail 'passed although resoloop printed no version'; fi
grep -qF 'resoloop --version printed nothing' <<<"$out" || fail "unexpected message: $out"
if BLENDER_FAIL=1 bash "$verify" 2>/dev/null; then fail 'passed although Blender cannot run'; fi

# glTF needs NumPy even when bpy itself works. Catch a verifier that probes only
# bpy by making this single import unavailable in a real Blender process.
if [ -n "$real_blender" ]; then
    cat > "$tmp/block_numpy.py" <<'PY'
import sys

class BlockNumpy:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "numpy" or fullname.startswith("numpy."):
            raise ModuleNotFoundError("NumPy unavailable for the dependency probe test")

for name in list(sys.modules):
    if name == "numpy" or name.startswith("numpy."):
        del sys.modules[name]
sys.meta_path.insert(0, BlockNumpy())
PY
    cat > "$tmp/bin/blender" <<'SH'
#!/bin/bash
exec "$REAL_BLENDER" --background --factory-startup --python-exit-code 1 \
    --python "$NUMPY_BLOCKER" "$@"
SH
    export REAL_BLENDER="$real_blender" NUMPY_BLOCKER="$tmp/block_numpy.py"
    if out="$(bash "$verify" 2>&1)"; then
        fail 'passed although NumPy is unavailable to real Blender'
    fi
    grep -qF 'NumPy unavailable for the dependency probe test' <<<"$out" || fail "unexpected failure: $out"
else
    printf 'SKIP: real Blender unavailable for the NumPy dependency rejection test\n'
fi

# 3. postCreate の進捗表示の総数（STEP_TOTAL）が実際の手順の数と同じ
installer="$root/.devcontainer/install_beforehand.bash"
declared_steps="$(sed -n 's/^readonly STEP_TOTAL=//p' "$installer")"
actual_steps="$(grep -c '^step "' "$installer")"
[ "$declared_steps" -eq "$actual_steps" ] || fail "STEP_TOTAL is $declared_steps, but there are $actual_steps steps"
printf 'PASS: toolchain smoke test and postCreate step count\n'
