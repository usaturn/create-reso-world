#!/bin/bash
# .devcontainer/cleanup-workspace.bash の設定と dry-run を、一時ディレクトリだけを対象に検査する。仕様 7.2 節
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/.devcontainer/cleanup-workspace.bash"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "$TEST_ROOT"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

mkdir -p "$TEST_ROOT/current/pr-review-42-abandoned"

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

# 2. 設定の既定値: 変数を渡さなければ /tmp、1 日、dry-run なし。
#    削除の範囲（/tmp 配下で 1 日より古いもの）を固定値で守る。既定値を広げると、使用中のレビュー用
#    worktree や /tmp 以外のディレクトリを消すため、スクリプトの値から期待値を作らない
config="$(
    env -u WORKSPACE_CLEANUP_TMP_ROOT -u WORKSPACE_CLEANUP_DRY_RUN -u WORKSPACE_CLEANUP_MIN_AGE_DAYS \
    bash -c '
        source <(sed -n "/^readonly TMP_ROOT=/,/^readonly DRY_RUN=/p" "$1")
        printf "%s|%s|%s" "$TMP_ROOT" "$MIN_AGE_DAYS" "$DRY_RUN"
    ' _ "$SCRIPT"
)"
[ "$config" = '/tmp|1|0' ] || fail "unexpected default configuration: $config"

printf 'PASS: workspace cleanup reports in dry-run and keeps its default scope\n'
