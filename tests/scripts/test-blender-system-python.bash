#!/bin/bash
# 雛形の Blender の wrapper（templates/world-project/blender-system-python）が、Blender の終了コードをそのまま返すことを確かめる。
# resoloop は Blender の終了コードが 0 以外なら BLENDER_FAILED で止まるので、wrapper が終了コードを捨てると、Blender の
# 失敗を成功と報告する。PATH・VIRTUAL_ENV・引数の扱いが壊れたときは、NumPy の import や Blender の起動のエラーとして
# 現れるので確かめない（AGENTS.md の L）
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
wrapper="$repo_root/templates/world-project/blender-system-python"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
[ -f "$wrapper" ] || fail 'wrapper template missing'

# /usr/bin/blender の実起動だけを止める。元の wrapper を、Blender の終了コードを返す関数 exec を定義した bash で source する
for status in 0 37; do
  got=0
  bash -c 'exec() { return "$status"; }; status="$1" wrapper="$2"; shift 2; source "$wrapper" "$@"' \
    bash "$status" "$wrapper" --background || got=$?
  [ "$got" -eq "$status" ] || fail "wrapper exit: expected $status, got $got"
done
printf 'PASS: Blender wrapper returns the exit status of Blender\n'
