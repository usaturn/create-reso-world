#!/bin/bash
# 実行するスクリプトが git の index 上で実行可能（100755）であることを検査する。仕様 7.2 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# 対象: .devcontainer 配下の *.bash と *.zsh、pi のランチャー 9 本、scripts/*.sh、テスト（tests/scripts/*.bash）
# 仕様 7.2 節: .devcontainer/*.bash はすべて 100755（mounts.bash・resoloop-tool.bash のように source される
# ライブラリも含む）。一方 tests/scripts/lib/ 配下は source して使う補助であり、この規則の対象外で 100644 のままでよい
launchers='piccd piccg piga pigl pigo pigod pigou pigs pixg'
checked=0 bad=()
while IFS= read -r -d '' record; do
  meta="${record%%$'\t'*}" path="${record#*$'\t'}"
  case "$path" in
    .devcontainer/*.bash | .devcontainer/*.zsh | scripts/*.sh | tests/scripts/*.bash) ;;
    .devcontainer/*)
      name="${path#.devcontainer/}"
      case " $launchers " in *" $name "*) ;; *) continue ;; esac ;;
    *) continue ;;
  esac
  case "$path" in tests/scripts/lib/*) continue ;; esac   # source して使う補助
  checked=$((checked + 1))
  [ "${meta%% *}" = 100755 ] || bad+=("$path (${meta%% *})")
done < <(git ls-files -s -z -- .devcontainer scripts tests/scripts)
[ ${#bad[@]} -eq 0 ] || fail "not executable in the index: ${bad[*]}"
for name in $launchers; do
  git ls-files --error-unmatch ".devcontainer/$name" >/dev/null 2>&1 || fail "launcher .devcontainer/$name is not tracked"
done
[ "$checked" -gt 30 ] || fail "too few files checked ($checked)"

printf 'PASS: %d scripts are executable in the index\n' "$checked"
