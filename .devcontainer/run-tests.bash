#!/bin/bash
# Dev Container とリポジトリのスクリプトのテストを一括で実行する。仕様 7.2・9.2 節（CI の devcontainer-tests ジョブ）
# 使い方: bash .devcontainer/run-tests.bash [--list | テストのパス...]
#   引数なし: .devcontainer/test-*.bash と tests/scripts/*.bash をすべて実行する
#   --list:   実行するテストを表示するだけ
# 1 本ずつ実行して PASS / FAIL と所要秒数を表示し、失敗したテストは出力を字下げして続けて示す。1 本でも失敗すれば 1
set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root" || exit 1

if [ $# -eq 0 ] || [ "$1" = --list ]; then
  tests=(.devcontainer/test-*.bash tests/scripts/*.bash)
else
  tests=("$@")
fi
if [ "${1:-}" = --list ]; then
  printf '%s\n' "${tests[@]}"
  exit 0
fi

log="$(mktemp)"
trap 'rm -f -- "$log"' EXIT
failed=()
for t in "${tests[@]}"; do
  start=$SECONDS
  if bash "$t" > "$log" 2>&1; then
    printf 'PASS %s (%ds)\n' "$t" $((SECONDS - start))
  else
    printf 'FAIL %s (%ds)\n' "$t" $((SECONDS - start))
    sed 's/^/    /' "$log"
    failed+=("$t")
  fi
done
if [ ${#failed[@]} -gt 0 ]; then
  printf 'FAIL: %d of %d test(s) failed: %s\n' "${#failed[@]}" "${#tests[@]}" "${failed[*]}"
  exit 1
fi
printf 'PASS: %d test(s)\n' "${#tests[@]}"
