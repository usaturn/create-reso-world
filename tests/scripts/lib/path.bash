#!/bin/bash
# tests/scripts のテストが source して使う補助関数。
# path_without DIR NAME...
#   今の PATH にあるコマンドのうち NAME... 以外を DIR に symlink で並べ、DIR を出力する。「NAME... だけが無い PATH」を、
#   コマンドの置き場所が違う環境（CI のランナーなど）でも同じように作るために使う（PATH="$(path_without ...)"）
path_without() {
  local dir="$1" entry file name skip x
  local -a entries=()
  shift
  mkdir -p "$dir"
  IFS=: read -r -a entries <<<"$PATH"
  for entry in "${entries[@]}"; do
    [ -d "$entry" ] || continue
    for file in "$entry"/*; do
      name="${file##*/}"
      [ -x "$file" ] && [ ! -d "$file" ] || continue
      [ ! -e "$dir/$name" ] && [ ! -L "$dir/$name" ] || continue   # PATH の先にあるものを優先する
      skip=0
      for x in "$@"; do [ "$name" != "$x" ] || skip=1; done
      [ "$skip" = 1 ] || ln -s "$file" "$dir/$name"
    done
  done
  printf '%s\n' "$dir"
}
