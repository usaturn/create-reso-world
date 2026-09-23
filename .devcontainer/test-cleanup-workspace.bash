#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "$TEST_ROOT"' EXIT

# 旧環境変数にも隔離先を渡しておき、変更前のコードが実際の /tmp を掃除しないようにする。
mkdir -p "$TEST_ROOT/legacy" "$TEST_ROOT/current/pr-review-42-abandoned"

output="$(
    MAATLOG_CLEANUP_TMP_ROOT="$TEST_ROOT/legacy" \
    MAATLOG_CLEANUP_DRY_RUN=1 \
    MAATLOG_CLEANUP_MIN_AGE_DAYS=0 \
    MAATLOG_CLEANUP_YARN_CACHE_DIR="$TEST_ROOT/legacy/yarn" \
    WORKSPACE_CLEANUP_TMP_ROOT="$TEST_ROOT/current" \
    WORKSPACE_CLEANUP_DRY_RUN=1 \
    WORKSPACE_CLEANUP_MIN_AGE_DAYS=0 \
    WORKSPACE_CLEANUP_YARN_CACHE_DIR="$TEST_ROOT/current/yarn" \
    bash "$REPO_ROOT/.devcontainer/cleanup-workspace.bash"
)"

if [[ "$output" != *"dry-run: would remove pr-review debris: $TEST_ROOT/current/pr-review-42-abandoned"* ]]; then
    printf 'FAIL: workspace cleanup did not honor the new temp root in dry-run mode\n%s\n' "$output" >&2
    exit 1
fi
if [ ! -d "$TEST_ROOT/current/pr-review-42-abandoned" ]; then
    printf 'FAIL: dry-run removed a review directory\n' >&2
    exit 1
fi
# 旧変数だけが指定された場合も、設定値の解決結果を検証する。
# 設定の代入だけを評価し、変更前のスクリプトが /tmp を実際に掃除しないようにする。
legacy_config="$(
    env -u WORKSPACE_CLEANUP_TMP_ROOT -u WORKSPACE_CLEANUP_DRY_RUN \
        -u WORKSPACE_CLEANUP_MIN_AGE_DAYS -u WORKSPACE_CLEANUP_YARN_CACHE_DIR \
    MAATLOG_CLEANUP_TMP_ROOT="$TEST_ROOT/legacy" \
    MAATLOG_CLEANUP_DRY_RUN=1 \
    MAATLOG_CLEANUP_MIN_AGE_DAYS=0 \
    MAATLOG_CLEANUP_YARN_CACHE_DIR="$TEST_ROOT/legacy/yarn" \
    bash -c '
        source <(sed -n "/^readonly TMP_ROOT=/,/^readonly DRY_RUN=/p" "$1")
        printf "%s|%s|%s|%s" "$TMP_ROOT" "$MIN_AGE_DAYS" "$YARN_CACHE_DIR" "$DRY_RUN"
    ' _ "$REPO_ROOT/.devcontainer/cleanup-workspace.bash"
)"
if [ "$legacy_config" != "$TEST_ROOT/legacy|0|$TEST_ROOT/legacy/yarn|1" ]; then
    printf 'FAIL: legacy dry-run configuration is no longer safe: %s\n' "$legacy_config" >&2
    exit 1
fi
printf 'PASS: workspace cleanup uses the project-neutral configuration and safe legacy fallback\n'
