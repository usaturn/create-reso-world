#!/bin/bash
# 実行するスクリプトが git の index 上で実行可能（100755）であることを検査する。仕様 7.2 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 対象: .devcontainer 配下の *.bash と *.zsh、scripts/*.sh、テスト（tests/scripts/*.bash）
# 仕様 7.2 節: .devcontainer/*.bash はすべて 100755（mounts.bash・resoloop-tool.bash のように source される
# ライブラリも含む）。一方 tests/scripts/lib/ 配下は source して使う補助であり、この規則の対象外で 100644 のままでよい
checked=0 bad=()
while IFS= read -r -d '' record; do
  meta="${record%%$'\t'*}" path="${record#*$'\t'}"
  case "$path" in
    .devcontainer/*.bash | .devcontainer/*.zsh | scripts/*.sh | tests/scripts/*.bash) ;;
    *) continue ;;
  esac
  case "$path" in tests/scripts/lib/*) continue ;; esac   # source して使う補助
  checked=$((checked + 1))
  [ "${meta%% *}" = 100755 ] || bad+=("$path (${meta%% *})")
done < <(git ls-files -s -z -- .devcontainer scripts tests/scripts)
[ ${#bad[@]} -eq 0 ] || fail "not executable in the index: ${bad[*]}"
# git ls-files がプロセス置換の中で失敗しても set -e は止まらないので、1 件も読めなければ失敗にする
[ "$checked" -gt 0 ] || fail 'no script was checked'

printf 'PASS: %d scripts are executable in the index\n' "$checked"
