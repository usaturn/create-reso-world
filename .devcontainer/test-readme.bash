#!/bin/bash
# .devcontainer/README.md の mount・initialize・zshrc・update の表を実装と比較する。
# あわせて移行元の名残、撤去済みツール、無効な設定の案内を検査する。
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

# 無効な Codex 設定を案内しない。
if grep -nE '^project_doc_fallback_filenames' "$readme"; then fail 'README still tells Codex users to add project_doc_fallback_filenames'; fi

# .devcontainer 配下に移行元の名残を残さない（このテスト自身と、旧変数を無視することを確かめる cleanup のテストは除く）
cd "$root"
self=':!.devcontainer/test-readme.bash'
if git grep -n -i maatlog -- .devcontainer "$self" ':!.devcontainer/test-cleanup-workspace.bash'; then fail '.devcontainer refers to maatlog'; fi
if git grep -nE '#[0-9]{3}\b' -- .devcontainer "$self"; then fail '.devcontainer refers to issue numbers of the migration source'; fi
if git grep -nF '/workspaces/reso-world' -- .devcontainer "$self"; then fail '.devcontainer hard-codes the workspace path'; fi

# 除外したエージェントの導入・mount・起動を .devcontainer に戻さない（ホストに残るパスを案内する README の注記は対象外）
excluded='@deepseek-ai/dsh|DeepSeek Harness|DSH_|dsh-settings|dsh-cordis|dsh (plugin|web|--)|HOME\}?/\.dsh|vscode/\.dsh|pnpmVersion": "[0-9]|3080'
excluded+='|x\.ai/cli|HOME\}?/\.grok|vscode/\.grok|grok update|-a grok'
excluded+='|function claude-alibaba|ccda \(\)|-u MAAS_ANTHROPIC_TOKEN|maas\.aliyuncs'
if git grep -n -E "$excluded" -- .devcontainer "$self"; then fail '.devcontainer still sets up an excluded agent'; fi

printf 'PASS: README implementation table, migration-source and retired/invalid configuration guards\n'
