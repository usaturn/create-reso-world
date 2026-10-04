#!/bin/bash
# .devcontainer/README.md の導入ツール一覧（仕様 7.1）が各ファイルと一致し、仕様 7.2 の記述を持つことを検査する。
# あわせて .devcontainer 配下に移行元リポジトリの名残（maatlog、Issue 番号、固定のワークスペースパス）が無いことを確かめる
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

# 1. 仕様 7.1 の行がそろっている
for tool in 'Claude Code' Codex pi Cursor Devin gh 'gcloud / glab / bun' 秘密情報; do
  column 1 | grep -qxF "$tool" || fail "tool table lacks the row for $tool"
done

# 2. mount の列は devcontainer.json の mounts、initialize.bash の列は initialize.bash が作るパスと同じ集合
mounted="$(mounts_from_devcontainer "$root/.devcontainer/devcontainer.json" | cut -f1 | sed 's|^|~/|' | LC_ALL=C sort)"
[ "$(column 3 | ticks | LC_ALL=C sort)" = "$mounted" ] || fail "the mount column differs from devcontainer.json:
$(column 3 | ticks | LC_ALL=C sort)"
created="$(mounts_from_initialize "$root/.devcontainer/initialize.bash" | sed 's|^|~/|' | LC_ALL=C sort)"
[ "$(column 4 | ticks | LC_ALL=C sort)" = "$created" ] || fail "the initialize.bash column differs from initialize.bash:
$(column 4 | ticks | LC_ALL=C sort)"

# 3. zshrc の列の関数と alias は zshrc.txt にあり、update() の列の項目は update() が実行する
while IFS= read -r name; do
  grep -qE "^(function ([a-z-]+ )*${name} ?\(\)|alias ${name}=)" "$zshrc" || fail "zshrc.txt lacks $name listed in the tool table"
done < <(column 5 | ticks)
update_body="$(sed -n '/^function update(){$/,/^}$/p' "$zshrc")"
while IFS= read -r item; do
  grep -qF -- "$item" <<<"$update_body" || fail "update() lacks '$item' listed in the tool table"
done < <(column 6 | ticks)

# 4. 仕様 7.2 の記述: ResoniteLink への到達、秘密情報の置き場、Cursor の制約、flux-sdk、テストの実行
for s in 'networkingMode=mirrored' 'resoloop discover' 'RESONITE_LINK_URL' '~/.config/create-reso-world/env' \
  '## エージェントの読み込みの制約' 'Cursor は' 'flux-sdk' 'bash .devcontainer/run-tests.bash' \
  'bash scripts/check-layout.sh' 'uv run pytest tests/skills .agents/skills' '.devcontainer/resoloop.lock'; do
  grep -qF -- "$s" "$readme" || fail "README lacks: $s"
done
if grep -nE '^project_doc_fallback_filenames' "$readme"; then fail 'README still tells Codex users to add project_doc_fallback_filenames'; fi

# 5. .devcontainer 配下に移行元の名残を残さない（このテスト自身と、旧変数を無視することを確かめる cleanup のテストは除く）
cd "$root"
self=':!.devcontainer/test-readme.bash'
if git grep -n -i maatlog -- .devcontainer "$self" ':!.devcontainer/test-cleanup-workspace.bash'; then fail '.devcontainer refers to maatlog'; fi
if git grep -nE '#[0-9]{3}\b' -- .devcontainer "$self"; then fail '.devcontainer refers to issue numbers of the migration source'; fi
if git grep -nF '/workspaces/reso-world' -- .devcontainer "$self"; then fail '.devcontainer hard-codes the workspace path'; fi
if git grep -n 'symlink' -- .devcontainer/docs/herdr-session-cwd-restore.md; then fail 'the herdr doc still describes .devcontainer as a symlink'; fi

# 6. 除外したエージェントの導入・mount・起動を .devcontainer に戻さない（ホストに残るパスを案内する README の注記は対象外）
excluded='@deepseek-ai/dsh|DeepSeek Harness|DSH_|dsh-settings|dsh-cordis|dsh (plugin|web|--)|HOME\}?/\.dsh|vscode/\.dsh|pnpmVersion": "[0-9]|3080'
excluded+='|x\.ai/cli|HOME\}?/\.grok|vscode/\.grok|grok update|-a grok'
excluded+='|function claude-alibaba|ccda \(\)|-u MAAS_ANTHROPIC_TOKEN|maas\.aliyuncs'
if git grep -n -E "$excluded" -- .devcontainer "$self"; then fail '.devcontainer still sets up an excluded agent'; fi
# 撤去した ccda の MAAS_ANTHROPIC_TOKEN を env から消すよう案内する（残すとプロバイダ切替ランチャーの子プロセスに渡る）
grep -qF '`MAAS_ANTHROPIC_TOKEN` は、もう使わない' "$readme" || fail 'README must tell users to remove MAAS_ANTHROPIC_TOKEN from env'

printf 'PASS: README tool table matches the Dev Container files\n'
