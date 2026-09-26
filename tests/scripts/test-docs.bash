#!/bin/bash
# ルートの README.md と統合手順（docs/integration.md）が仕様 4.1・5.1・9.3・10.1 と持ち越しの N-3・N-4・N-12・N-17・N-18・N-24・N-25・P-1〜P-3・P-7 のとおりで、
# 書いてあるファイルや節が実在することを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
has() { grep -qF -- "$2" "$1" || fail "$1 lacks: $2"; }
lacks() { if grep -qF -- "$2" "$1"; then fail "$1 must not contain: $2"; fi; }

# 1. README.md: 仕様 4.1 の内容（目的、Dev Container の起動、プロジェクトの作成、ResoLoop の版、変更の流れ）とテストの節がある
[ "$(head -n 1 README.md)" = '# create-reso-world' ] || fail 'README.md title'
expected='## 構成
## Dev Container を起動する
## エージェントで作業する
## プロジェクトを作る
## ResoLoop の版
## 変更の流れ
## テスト
## 対象外'
[ "$(grep -E '^## ' README.md)" = "$expected" ] || fail "README.md sections differ:
$(grep -E '^## ' README.md)"

# 2. README.md が案内するファイルは実在する
for f in AGENTS.md CLAUDE.md .agents/skills .devcontainer/README.md .devcontainer/install_beforehand.bash \
  .devcontainer/verify-resonite-tooling.bash .devcontainer/resoloop.lock .devcontainer/run-tests.bash \
  scripts/new-world.sh scripts/resoloop-fork.sh scripts/check-layout.sh templates/world-project \
  docs/resoloop-fork-workflow.md docs/integration.md .github/workflows/ci.yml .codex/config.toml .cursor/mcp.json \
  .agents/sp-implementer.md; do
  has README.md "$f"
  [ -e "$f" ] || fail "README.md refers to missing $f"
done
# .devcontainer/README.md の節への案内は、その節が実在する
for section in 秘密情報 エージェントの読み込みの制約; do
  has README.md "「$section」"
  grep -qxF "## $section" .devcontainer/README.md || fail ".devcontainer/README.md lacks ## $section"
done

# 3. N-3: エージェントごとに初回に要る操作と制約
for s in 'trust' 'cursor-agent' '.devin/config.json' 'sp-*.md' 'Cursor と dsh'; do has README.md "$s"; done
lacks README.md 'maatlog'

# 4. 統合手順: マージ前の片付け（P-1）、一覧の件数（N-4）、sp-implementer.md の比較先と同じシェル（N-12）、
#    main の再 ff（M-5）、/private/ の行を消す時期（P-2）、Rebuild 後の確認（N-17・N-18・N-25・N-27）
doc=docs/integration.md
before_merge="$(sed -n '/^## マージ前にユーザが行うこと$/,/^## マージ後にユーザが行うこと$/p' "$doc")"
for s in 'git checkout -- .claude/settings.local.json' 'git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md' \
  '同じシェル' 'ルートの `.agents/sp-implementer.md` と比べる' '2026-09-27 時点の該当: 68 件'; do
  grep -qF -- "$s" <<<"$before_merge" || fail "the pre-merge section of $doc lacks: $s"
done
for s in 'git fetch . feat/slum02-slum:main' 'マージに置き換えた' '## Rebuild 後に確かめること（仕様 9.3）' \
  'dotnet --list-sdks' '/home/vscode/.local/bin' '~/.config/create-reso-world' 'simplify-in-subagent' \
  'GitHub Actions' 'resoloop-fork.sh sync' 'wip/tokyo-nova-refinement` を新しい `main` に rebase した後'; do
  has "$doc" "$s"
done
lacks "$doc" '随時追記'
lacks "$doc" 'Task 14'

# 5. 仕様・運用文書・フェーズ 0・1 の計画書の表記（P-3・P-7・N-24）
spec=docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md
lacks "$spec" '`**/tmp/`'
lacks "$spec" '`.agents/skills/*/SKILL.md` ごとに'
has "$spec" 'git fetch . feat/slum02-slum:main'
has "$spec" 'フェーズ 4 の D-10'
has "$spec" '`install` の `checkout` は origin にあるコミットしか取り出せない'
has docs/resoloop-fork-workflow.md 'テストと特殊な運用向け'
lacks docs/resoloop-fork-workflow.md '主にテスト用'
phase01=docs/superpowers/plans/2026-09-26-redesign-phase0-1-safety-and-hygiene.md
lacks "$phase01" '`**/` 前置に修正された'
lacks "$phase01" '追跡解除後もローカルファイルとして残る'

printf 'PASS: README and integration docs follow spec 4.1 and 10.1\n'
