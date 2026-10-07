#!/bin/bash
# .devcontainer/README.md の mount・initialize・zshrc・update の表を実装と比較する。
# あわせて .devcontainer にワークスペースの絶対パスを書いていないことを検査する。
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readme="$root/.devcontainer/README.md"
zshrc="$root/.devcontainer/zshrc.txt"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# shellcheck source=mounts.bash
source "$root/.devcontainer/mounts.bash"

# column N: 表の N 列目（1 始まり）を行ごとに出力する
table="$(sed -n '/^<!-- tool-table:start -->$/,/^<!-- tool-table:end -->$/p' "$readme" | { grep '^| ' || true; } | tail -n +3)"
[ -n "$table" ] || fail 'README lacks the tool table between the tool-table markers'
column() { awk -F' [|] ' -v n="$1" '{ sub(/^[|] /, ""); sub(/ [|]$/, ""); print $n }' <<<"$table"; }
# ticks: 標準入力の `...` の中身を 1 行ずつ出力する
ticks() { grep -o '`[^`]*`' | tr -d '`' || true; }

# mount の列は devcontainer.json の mounts、initialize.bash の列は initialize.bash が作るパスと同じ集合
mounted="$(mounts_from_devcontainer "$root/.devcontainer/devcontainer.json" | cut -f1 | sed 's|^|~/|' | LC_ALL=C sort)"
[ "$(column 3 | ticks | LC_ALL=C sort)" = "$mounted" ] || fail "the mount column differs from devcontainer.json:
$(column 3 | ticks | LC_ALL=C sort)"
created="$(mounts_from_initialize "$root/.devcontainer/initialize.bash" | sed 's|^|~/|' | LC_ALL=C sort)"
[ "$(column 4 | ticks | LC_ALL=C sort)" = "$created" ] || fail "the initialize.bash column differs from initialize.bash:
$(column 4 | ticks | LC_ALL=C sort)"

# zshrc の列の関数と alias は zshrc.txt にあり、update() の列の項目は update() が実行する
while IFS= read -r name; do
  grep -qE "^(function ([a-z-]+ )*${name} ?\(\)|alias ${name}=)" "$zshrc" || fail "zshrc.txt lacks $name listed in the tool table"
done < <(column 5 | ticks)
update_body="$(sed -n '/^function update(){$/,/^}$/p' "$zshrc")"
while IFS= read -r item; do
  grep -qF -- "$item" <<<"$update_body" || fail "update() lacks '$item' listed in the tool table"
done < <(column 6 | ticks)

# .devcontainer にワークスペースの絶対パスを書かない。固定したパスを使うと、worktree や別名の checkout から
# 実行しても親の checkout を操作するため、このパスは固定値で禁止する
cd "$root"
if git grep -nF '/workspaces/reso-world' -- .devcontainer ':!.devcontainer/test-readme.bash'; then
  fail '.devcontainer hard-codes the workspace path'
fi

printf 'PASS: README implementation table and no hard-coded workspace path\n'
