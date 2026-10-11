#!/bin/bash
# 雛形そのものを別 Bash で実行し、Blender の外部起動境界だけを置き換える。
# PATH 除去・環境解除・引数の分割や終了コードの変更があると失敗する。
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
wrapper="$repo_root/templates/world-project/blender-system-python"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
[ -f "$wrapper" ] || fail 'wrapper template missing'

# /usr/bin/blender の実起動だけを止める。source するのは元のラッパーであり、
# 関数 exec に渡った実際の PATH・環境・引数を NUL 区切りで観測する。
for status in 0 37; do
  got=0
  bash -c '
    exec() {
      printf "%s\0" "$PATH" "${VIRTUAL_ENV+set}" "$@" > "$record"
      return "$status"
    }
    record="$1" status="$2" wrapper="$3"
    shift 3
    export PATH="/world/.venv/bin:/keep/first:/other/.venv/bin:/keep with spaces/bin:/keep/.venv/bin-extra:/keep/last:/tail/.venv/bin"
    export VIRTUAL_ENV="/world/.venv"
    source "$wrapper" "$@"
  ' bash "$tmp/record" "$status" "$wrapper" --background 'two words' '' '"quoted"' || got=$?
  [ "$got" -eq "$status" ] || fail "wrapper exit: expected $status, got $got"
  mapfile -d '' -t observed < "$tmp/record"
  [ "${#observed[@]}" -eq 7 ] || fail 'wrapper changed the argument count'
  [ "${observed[0]}" = '/keep/first:/keep with spaces/bin:/keep/.venv/bin-extra:/keep/last' ] || fail 'PATH removal or retained order'
  [ "${observed[1]}" = '' ] || fail 'VIRTUAL_ENV is still set'
  # システム Python を使う安全境界と、空白・空引数の保持を守る固定値。
  [ "${observed[2]}" = /usr/bin/blender ] || fail 'not invoking system Blender'
  [ "${observed[3]}" = --background ] || fail 'first argument changed'
  [ "${observed[4]}" = 'two words' ] || fail 'argument with spaces split'
  [ "${observed[5]}" = '' ] || fail 'empty argument dropped'
  [ "${observed[6]}" = '"quoted"' ] || fail 'quoted argument changed'
done
printf 'PASS: Blender wrapper preserves the system environment and launch arguments\n'
