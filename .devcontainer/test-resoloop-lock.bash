#!/bin/bash
# .devcontainer/resoloop.lock と読み込み関数（.devcontainer/resoloop-lock.bash）を検査する。仕様 6.1・6.3・9.1 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# shellcheck source=resoloop-lock.bash
source "$root/.devcontainer/resoloop-lock.bash"

# 1. リポジトリのロックは読めて、RESOLOOP_FORK_SDK が devcontainer.json の additionalVersions にある
resoloop_lock_load "$root/.devcontainer/resoloop.lock" || fail 'the repository lock is invalid'
[ -n "$RESOLOOP_EXPECTED_VERSION" ] || fail 'no expected version'
resoloop_lock_sdk_declared "$root/.devcontainer/devcontainer.json" "$RESOLOOP_FORK_SDK" \
  || fail "RESOLOOP_FORK_SDK $RESOLOOP_FORK_SDK is not in additionalVersions of devcontainer.json"

# 以降は一時ファイルのロックで検査する。write_lock MODE [追加の行...]
write_lock() {
  local mode="$1"; shift
  {
    printf '# comment\n\n'
    printf 'RESOLOOP_MODE=%s\n' "$mode"
    printf 'RESOLOOP_NUGET_VERSION=1.2.3-preview.4\n'
    printf 'RESOLOOP_FORK_ORIGIN=https://example.com/fork/resoloop.git\n'
    printf 'RESOLOOP_FORK_UPSTREAM=https://example.com/upstream/resoloop.git\n'
    printf 'RESOLOOP_FORK_REF=fix/x\n'
    printf 'RESOLOOP_FORK_COMMIT=%s\n' 0123456789abcdef0123456789abcdef01234567
    printf 'RESOLOOP_FORK_PACKAGE_VERSION=1.2.3-preview.4.pr1.20260101\n'
    printf 'RESOLOOP_FORK_PR=https://example.com/upstream/resoloop/pull/9\n'
    printf 'RESOLOOP_FORK_SDK=10.0.201\n'
    [ $# -eq 0 ] || printf '%s\n' "$@"
  } > "$tmp/lock"
}
# expect_invalid NEEDLE: ロックの読み込みが失敗し、標準エラーに NEEDLE が出ることを確かめる
expect_invalid() {
  local out
  if out="$( (resoloop_lock_load "$tmp/lock") 2>&1 )"; then fail "accepted an invalid lock (expected: $1)"; fi
  grep -qF -- "$1" <<<"$out" || fail "expected '$1' in: $out"
}

# 2. fork モードの期待版は RESOLOOP_FORK_PACKAGE_VERSION、nuget モードは RESOLOOP_NUGET_VERSION
write_lock fork
( resoloop_lock_load "$tmp/lock" && [ "$RESOLOOP_EXPECTED_VERSION" = 1.2.3-preview.4.pr1.20260101 ] ) || fail 'fork expected version'
write_lock nuget
( resoloop_lock_load "$tmp/lock" && [ "$RESOLOOP_EXPECTED_VERSION" = 1.2.3-preview.4 ] ) || fail 'nuget expected version'

# 3. 必須キーの欠落、未知のキー、重複、不正なモード、短いコミット ID、SDK の書式
write_lock fork && sed -i '/^RESOLOOP_FORK_SDK=/d' "$tmp/lock"
expect_invalid 'missing key RESOLOOP_FORK_SDK'
write_lock fork 'RESOLOOP_FORK_CHECKOUT=/tmp/x'
expect_invalid 'unknown key RESOLOOP_FORK_CHECKOUT'
write_lock fork 'RESOLOOP_MODE=nuget'
expect_invalid 'duplicate key RESOLOOP_MODE'
write_lock source
expect_invalid 'RESOLOOP_MODE must be nuget or fork, not source'
write_lock fork && sed -i 's/^RESOLOOP_FORK_COMMIT=.*/RESOLOOP_FORK_COMMIT=1ef4d18/' "$tmp/lock"
expect_invalid 'RESOLOOP_FORK_COMMIT must be a full 40-character commit id'
write_lock fork && sed -i 's/^RESOLOOP_FORK_SDK=.*/RESOLOOP_FORK_SDK=10.0/' "$tmp/lock"
expect_invalid 'RESOLOOP_FORK_SDK must be an exact SDK version'

# 4. 値にコマンドを書いても実行せずに拒否する。空の値、CRLF の行も拒否する
write_lock fork "RESOLOOP_FORK_PR=\$(touch $tmp/executed)"
expect_invalid 'is not KEY=VALUE'
[ ! -e "$tmp/executed" ] || fail 'the lock was executed'
write_lock fork && sed -i 's/^RESOLOOP_FORK_PR=.*/RESOLOOP_FORK_PR=/' "$tmp/lock"
expect_invalid 'is not KEY=VALUE'
write_lock fork && sed -i 's/^RESOLOOP_FORK_REF=fix\/x$/RESOLOOP_FORK_REF=fix\/x\r/' "$tmp/lock"
expect_invalid 'is not KEY=VALUE'

# 5. 失敗したときは変数を設定しない。最終行に改行が無くても読める。ファイルが無ければ失敗する
write_lock fork && sed -i '/^RESOLOOP_FORK_SDK=/d' "$tmp/lock"
( unset RESOLOOP_MODE; resoloop_lock_load "$tmp/lock" 2>/dev/null; [ -z "${RESOLOOP_MODE+x}" ] ) || fail 'set variables from an invalid lock'
write_lock fork && printf 'RESOLOOP_FORK_SDK=10.0.201' > "$tmp/last" && sed -i '/^RESOLOOP_FORK_SDK=/d' "$tmp/lock" && cat "$tmp/last" >> "$tmp/lock"
( resoloop_lock_load "$tmp/lock" && [ "$RESOLOOP_FORK_SDK" = 10.0.201 ] ) || fail 'last line without a newline'
if (resoloop_lock_load "$tmp/missing") 2>/dev/null; then fail 'accepted a missing lock'; fi

# 6. additionalVersions はカンマ区切りの中から探し、// のコメント行は数えない
printf '{\n  "a": { "additionalVersions": "8.0.100, 10.0.201" }\n}\n' > "$tmp/list.json"
resoloop_lock_sdk_declared "$tmp/list.json" 10.0.201 || fail 'SDK in a comma list'
printf '{\n  // "additionalVersions": "10.0.201"\n  "a": { "version": "10.0" }\n}\n' > "$tmp/comment.json"
if resoloop_lock_sdk_declared "$tmp/comment.json" 10.0.201; then fail 'counted a commented-out line'; fi
if resoloop_lock_sdk_declared "$tmp/list.json" 10.0.2; then fail 'matched a version prefix'; fi
if resoloop_lock_sdk_declared "$tmp/none.json" 10.0.201; then fail 'accepted a missing devcontainer.json'; fi
# 値の後ろの // コメントは読み飛ばす（キーと値は同じ行に書く前提。devcontainer.json を改訂したときに見直す）
printf '{\n  "a": {\n    "additionalVersions": "10.0.201" // fork の SDK\n  }\n}\n' > "$tmp/trailing.json"
resoloop_lock_sdk_declared "$tmp/trailing.json" 10.0.201 || fail 'a trailing comment hid the SDK'

# 7. resoloop --version の出力から版を取り出す
[ "$(resoloop_version_of $'0.1.0-preview.14\n')" = 0.1.0-preview.14 ] || fail 'plain version'
[ "$(resoloop_version_of $'  1.2.3+abc123  \n')" = 1.2.3 ] || fail 'whitespace and build metadata'
[ "$(resoloop_version_of $'\n\n2.0.0\nextra\n')" = 2.0.0 ] || fail 'first non-empty line'
if resoloop_version_of $'\n  \n' >/dev/null; then fail 'accepted empty output'; fi

# 8. dotnet tool list --global から導入済み版を読む（モックの dotnet）
mkdir -p "$tmp/bin"
cat > "$tmp/bin/dotnet" <<'EOF'
#!/bin/bash
[ "$*" = 'tool list --global' ] || exit 64
[ "${MOCK_LIST_FAIL:-0}" = 0 ] || exit 1
printf 'Package Id      Version      Commands\n-------------------------------------\n'
[ -z "${MOCK_LIST_LINE:-}" ] || printf '%s\n' "$MOCK_LIST_LINE"
EOF
chmod +x "$tmp/bin/dotnet"
[ "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='resoloop  0.1.0-preview.14.pr1.20260925  resoloop' resoloop_installed_version)" = 0.1.0-preview.14.pr1.20260925 ] \
  || fail 'installed version'
[ "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='ResoLoop 1.0.0 resoloop' resoloop_installed_version)" = 1.0.0 ] || fail 'package id is case-insensitive'
[ -z "$(PATH="$tmp/bin:$PATH" MOCK_LIST_LINE='my-resoloop-plugin 1.0.0 other' resoloop_installed_version)" ] || fail 'matched a different package'
[ -z "$(PATH="$tmp/bin:$PATH" resoloop_installed_version)" ] || fail 'reported a version when nothing is installed'
if PATH="$tmp/bin:$PATH" MOCK_LIST_FAIL=1 resoloop_installed_version >/dev/null; then fail 'ignored a failing dotnet tool list'; fi

printf 'PASS: resoloop lock and its reader behave as specified\n'
