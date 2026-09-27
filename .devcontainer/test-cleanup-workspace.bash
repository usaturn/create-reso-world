#!/bin/bash
# .devcontainer/cleanup-workspace.bash の設定と dry-run を、一時ディレクトリだけを対象に検査する。仕様 7.2 節
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/.devcontainer/cleanup-workspace.bash"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "$TEST_ROOT"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

mkdir -p "$TEST_ROOT/current/pr-review-42-abandoned" "$TEST_ROOT/legacy/pr-review-7-abandoned" "$TEST_ROOT/home/.cache/yarn"

# 1. dry-run は WORKSPACE_CLEANUP_TMP_ROOT の対象を表示するだけで、何も消さない
output="$(
    HOME="$TEST_ROOT/home" \
    WORKSPACE_CLEANUP_TMP_ROOT="$TEST_ROOT/current" \
    WORKSPACE_CLEANUP_DRY_RUN=1 \
    WORKSPACE_CLEANUP_MIN_AGE_DAYS=0 \
    bash "$SCRIPT"
)"
[[ "$output" == *"dry-run: would remove pr-review debris: $TEST_ROOT/current/pr-review-42-abandoned"* ]] \
    || fail "dry-run did not report the review directory under WORKSPACE_CLEANUP_TMP_ROOT
$output"
[ -d "$TEST_ROOT/current/pr-review-42-abandoned" ] || fail 'dry-run removed a review directory'

# 2. 移行元の MAATLOG_CLEANUP_* は読まない。yarn キャッシュは掃除の対象にしない
output="$(
    HOME="$TEST_ROOT/home" \
    MAATLOG_CLEANUP_TMP_ROOT="$TEST_ROOT/legacy" \
    WORKSPACE_CLEANUP_TMP_ROOT="$TEST_ROOT/current" \
    WORKSPACE_CLEANUP_DRY_RUN=1 \
    WORKSPACE_CLEANUP_MIN_AGE_DAYS=0 \
    bash "$SCRIPT"
)"
[[ "$output" != *"$TEST_ROOT/legacy"* ]] || fail "MAATLOG_CLEANUP_TMP_ROOT was honoured
$output"
[[ "$output" != *yarn* ]] || fail "the cleanup still handles the yarn cache
$output"
[ -d "$TEST_ROOT/home/.cache/yarn" ] || fail 'the cleanup removed the yarn cache'

# 3. 設定の既定値: 変数を渡さなければ /tmp、1 日、dry-run なし。移行元の変数は既定値を変えない
config="$(
    env -u WORKSPACE_CLEANUP_TMP_ROOT -u WORKSPACE_CLEANUP_DRY_RUN -u WORKSPACE_CLEANUP_MIN_AGE_DAYS \
    MAATLOG_CLEANUP_TMP_ROOT="$TEST_ROOT/legacy" MAATLOG_CLEANUP_DRY_RUN=1 MAATLOG_CLEANUP_MIN_AGE_DAYS=0 \
    bash -c '
        source <(sed -n "/^readonly TMP_ROOT=/,/^readonly DRY_RUN=/p" "$1")
        printf "%s|%s|%s" "$TMP_ROOT" "$MIN_AGE_DAYS" "$DRY_RUN"
    ' _ "$SCRIPT"
)"
[ "$config" = '/tmp|1|0' ] || fail "unexpected default configuration: $config"

# 4. 移行元リポジトリの名残（MAATLOG_CLEANUP_*、yarn、verify.sh、Issue 番号）を残さない
if grep -nE 'MAATLOG|yarn|verify\.sh|#[0-9]{3}\b' "$SCRIPT"; then
    fail 'cleanup-workspace.bash still refers to the migration source'
fi

printf 'PASS: workspace cleanup uses only WORKSPACE_CLEANUP_* and keeps the dry-run safe\n'
