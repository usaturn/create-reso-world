#!/bin/bash
# scripts/check-layout.sh が壊れた配置を通さないことを一時リポジトリで検査する（守りごとに代表の 1 件）
set -euo pipefail
# 外から渡された GIT_* を除く。linked worktree の git rebase --exec は GIT_DIR を export するので、残すと
# 直接実行したときに一時リポジトリの git init・git -C が、そのリポジトリの設定・index・ブランチを書き換える（#200）
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# GIT_CONFIG_GLOBAL=/dev/null だけでは XDG 既定の ~/.config/git/ignore が働いてしまうため、
# core.excludesFile も無効化し、システム設定も外してユーザの git 設定から隔離する。
# グローバル設定の safe.directory も外れるので、このリポジトリだけは所有者が違っても（CI のコンテナや
# Dev Container の bind mount）読めるようにしておく
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$root"
checker="$root/scripts/check-layout.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

new_repo() {
  git init -q "$1"
  git -C "$1" config user.email test@example.com
  git -C "$1" config user.name test
  printf 'ok\n' > "$1/README.md"
  git -C "$1" add README.md
  git -C "$1" commit -q -m init
}

expect_fail_with() {
  local dir="$1" needle="$2" out="$tmp/out.txt" code=0
  bash "$checker" --root "$dir" > "$out" 2>&1 || code=$?
  if [ "$code" -eq 0 ]; then
    printf 'FAIL: %s was accepted\n' "$dir" >&2; exit 1
  fi
  if [ "$code" -ne 1 ]; then
    printf 'FAIL: expected exit code 1 for %s, got %d\n' "$dir" "$code" >&2; cat "$out" >&2; exit 1
  fi
  grep -qF "$needle" "$out" || { printf 'FAIL: expected message %q for %s\n' "$needle" "$dir" >&2; cat "$out" >&2; exit 1; }
}

commit_paths() {  # $1=リポジトリ、残り=追加するパス
  local r="$1"; shift
  git -C "$r" add -- "$@" && git -C "$r" commit -q -m change
}

# .agents/skills/foo を持つ一時リポジトリを作る（.claude 側は各ケースで作る）
skill_repo() {
  new_repo "$1"
  mkdir -p "$1/.agents/skills/foo" "$1/.claude/skills"
  printf -- '---\nname: foo\ndescription: d\n---\n' > "$1/.agents/skills/foo/SKILL.md"
}

# 1. 何も問題の無いリポジトリは通過する
new_repo "$tmp/clean"
bash "$checker" --root "$tmp/clean" | grep -qF 'PASS: check-layout'

# 2. 追跡禁止ファイルは、非 ASCII 名のディレクトリの中でも、リポジトリのサブディレクトリを --root に渡しても検出する
new_repo "$tmp/forbidden"
mkdir -p "$tmp/forbidden/資料/deep"
printf 'x\n' > "$tmp/forbidden/資料/TNX.txt"
git -C "$tmp/forbidden" add 資料/TNX.txt && git -C "$tmp/forbidden" commit -q -m add
expect_fail_with "$tmp/forbidden/資料/deep" 'forbidden tracked files'

# 3. 行き先の無い追跡 symlink
new_repo "$tmp/symlink"
ln -s missing-target "$tmp/symlink/link"
git -C "$tmp/symlink" add link && git -C "$tmp/symlink" commit -q -m link
expect_fail_with "$tmp/symlink" 'dangling tracked symlinks'

# 4. 追跡中かつ ignore 対象
new_repo "$tmp/ignored"
printf 'secret.txt\n' > "$tmp/ignored/.gitignore"
printf 's\n' > "$tmp/ignored/secret.txt"
git -C "$tmp/ignored" add -f .gitignore secret.txt && git -C "$tmp/ignored" commit -q -m ignored
expect_fail_with "$tmp/ignored" 'tracked but ignored'

# 5. .agents/skills と .claude/skills が 1:1 の symlink なら通過し、リンクが無い・実ディレクトリ（コピーは元と食い違う）・
#    リンクの行き先を書いた通常ファイル・行き先が違うものは失敗する
skill_repo "$tmp/skills-ok"
ln -s ../../.agents/skills/foo "$tmp/skills-ok/.claude/skills/foo"
commit_paths "$tmp/skills-ok" .agents .claude
bash "$checker" --root "$tmp/skills-ok" | grep -qF 'PASS: check-layout'

skill_repo "$tmp/skills-missing"
commit_paths "$tmp/skills-missing" .agents
expect_fail_with "$tmp/skills-missing" 'missing link foo'

skill_repo "$tmp/skills-realdir"
mkdir -p "$tmp/skills-realdir/.claude/skills/foo"
cp "$tmp/skills-realdir/.agents/skills/foo/SKILL.md" "$tmp/skills-realdir/.claude/skills/foo/SKILL.md"
commit_paths "$tmp/skills-realdir" .agents .claude
expect_fail_with "$tmp/skills-realdir" '.claude/skills/foo is not a symlink'

skill_repo "$tmp/skills-regular"
printf '../../.agents/skills/foo\n' > "$tmp/skills-regular/.claude/skills/foo"
commit_paths "$tmp/skills-regular" .agents .claude
expect_fail_with "$tmp/skills-regular" '.claude/skills/foo is not a symlink'

skill_repo "$tmp/skills-target"
mkdir -p "$tmp/skills-target/other/foo" && printf 'x\n' > "$tmp/skills-target/other/foo/SKILL.md"
ln -s ../../other/foo "$tmp/skills-target/.claude/skills/foo"
commit_paths "$tmp/skills-target" .agents .claude other
expect_fail_with "$tmp/skills-target" '.claude/skills/foo has unexpected target ../../other/foo'

# 仕様 4.2 を満たすローカルプロジェクトを 1 つ持つリポジトリを作る。$2 はプロジェクト名（既定: demo）。
# 作る場所は ignore 対象の worlds/<name> で、プロジェクトのファイルは追跡しない（共有の設定だけを追跡する）。
# worlds/<name> は深さ 2 なので、ルートを指す symlink は ../ を 3 つ使う
project_repo() {
  local r="$1" n="${2:-demo}"
  local p="$r/worlds/$n"
  new_repo "$r"
  printf '/worlds/\n' > "$r/.gitignore"
  mkdir -p "$r/.claude" "$r/.pi" "$r/.agents" "$p/.agents/skills/resonite-build" "$p/.claude/skills" "$p/.resoloop" "$p/flux"
  printf '{}\n' > "$r/.claude/settings.json"
  printf 'pi\n' > "$r/.pi/APPEND_SYSTEM.md"
  printf -- '---\nname: sp-implementer\n---\n' > "$r/.agents/sp-implementer.md"
  printf '# guide\n\n## このプロジェクト固有\n\n- test\n' > "$p/AGENTS.md"
  printf '@AGENTS.md\n' > "$p/CLAUDE.md"
  printf '{}\n' > "$p/.resoloop.json"
  printf 'state/\nflux-state/\ncache/\n' > "$p/.resoloop/.gitignore"
  printf '[project]\nname = "%s"\n' "$n" > "$p/pyproject.toml"
  printf 'version = 1\n' > "$p/uv.lock"
  printf '{}\n' > "$p/.agents/skills/.resoloop-bundled.json"
  printf -- '---\nname: resonite-build\ndescription: d\n---\n' > "$p/.agents/skills/resonite-build/SKILL.md"
  printf '{}\n' > "$p/flux/resoloop.flux.json"
  ln -s ../../.agents/skills/resonite-build "$p/.claude/skills/resonite-build"
  ln -s ../../../.claude/settings.json "$p/.claude/settings.json"
  ln -s ../../.pi "$p/.pi"
  ln -s ../../../.agents/sp-implementer.md "$p/.agents/sp-implementer.md"
  commit_paths "$r" .claude .pi .agents .gitignore
}

# 追跡解除した従来位置のプロジェクト（ルート直下・深さ 1）を持つリポジトリを作る
legacy_project_repo() {
  local r="$1" n="${2:-akichi}"
  local p="$r/$n"
  new_repo "$r"
  printf '/%s/\n' "$n" > "$r/.gitignore"
  mkdir -p "$r/.claude" "$r/.pi" "$r/.agents" "$p/.agents/skills/resonite-build" "$p/.claude/skills" "$p/.resoloop" "$p/flux"
  printf '{}\n' > "$r/.claude/settings.json"
  printf 'pi\n' > "$r/.pi/APPEND_SYSTEM.md"
  printf -- '---\nname: sp-implementer\n---\n' > "$r/.agents/sp-implementer.md"
  printf '# guide\n\n## このプロジェクト固有\n\n- test\n' > "$p/AGENTS.md"
  printf '@AGENTS.md\n' > "$p/CLAUDE.md"
  printf '{}\n' > "$p/.resoloop.json"
  printf 'state/\nflux-state/\ncache/\n' > "$p/.resoloop/.gitignore"
  printf '[project]\nname = "%s"\n' "$n" > "$p/pyproject.toml"
  printf 'version = 1\n' > "$p/uv.lock"
  printf '{}\n' > "$p/.agents/skills/.resoloop-bundled.json"
  printf -- '---\nname: resonite-build\ndescription: d\n---\n' > "$p/.agents/skills/resonite-build/SKILL.md"
  printf '{}\n' > "$p/flux/resoloop.flux.json"
  ln -s ../../.agents/skills/resonite-build "$p/.claude/skills/resonite-build"
  ln -s ../../.claude/settings.json "$p/.claude/settings.json"
  ln -s ../.pi "$p/.pi"
  ln -s ../../.agents/sp-implementer.md "$p/.agents/sp-implementer.md"
  commit_paths "$r" .claude .pi .agents .gitignore
}

# モックの resoloop: MOCK_RESOLOOP_CONFLICT と同名のプロジェクトは手で編集した同梱スキル（SKILL_SYNC_CONFLICT）で
# skills sync --check に失敗する
mkdir -p "$tmp/mockbin"
cat > "$tmp/mockbin/resoloop" <<'EOF'
#!/bin/bash
[ "$1 $2 $4" = 'skills sync --check' ] || exit 64
case "$3" in "${MOCK_RESOLOOP_CONFLICT:-__none__}"|*/"${MOCK_RESOLOOP_CONFLICT:-__none__}") echo 'SKILL_SYNC_CONFLICT' >&2; exit 6 ;; esac
exit 0
EOF
chmod +x "$tmp/mockbin/resoloop"
export PATH="$tmp/mockbin:$PATH"

# 6. 標準レイアウトのローカルプロジェクトは通過する。手で編集した同梱スキル（SKILL_SYNC_CONFLICT）は失敗する
project_repo "$tmp/proj-ok"
bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-ok.out"
grep -qF 'ok: project worlds/demo layout' "$tmp/proj-ok.out"
grep -qF 'PASS: check-layout' "$tmp/proj-ok.out"
MOCK_RESOLOOP_CONFLICT=demo expect_fail_with "$tmp/proj-ok" 'resoloop skills sync --check failed for worlds/demo'

# 7. 標準レイアウトからの逸脱（必須ファイルの欠落・CLAUDE.md の内容・symlink の行き先・スキルのリンクの欠落・
#    向き違い・実ディレクトリ）は失敗する
project_repo "$tmp/p-file" && rm "$tmp/p-file/worlds/demo/CLAUDE.md"
expect_fail_with "$tmp/p-file" 'worlds/demo: missing regular file CLAUDE.md'

# CLAUDE.md は指示ファイルの読み込み指定（@AGENTS.md）。違う内容を通すと、Claude Code がプロジェクトの
# AGENTS.md（規約と安全ルール）を読まないまま、エラーにならずに作業が進む
project_repo "$tmp/p-claude" && printf 'other\n' > "$tmp/p-claude/worlds/demo/CLAUDE.md"
expect_fail_with "$tmp/p-claude" 'worlds/demo: CLAUDE.md must be exactly @AGENTS.md'

project_repo "$tmp/p-pi" && rm "$tmp/p-pi/worlds/demo/.pi" && ln -s ../../.agents "$tmp/p-pi/worlds/demo/.pi"
expect_fail_with "$tmp/p-pi" 'worlds/demo: .pi must be a symlink to ../../.pi'

project_repo "$tmp/p-link" && rm "$tmp/p-link/worlds/demo/.claude/skills/resonite-build"
expect_fail_with "$tmp/p-link" 'worlds/demo/.claude/skills: missing link resonite-build'

# プロジェクト側のスキルのリンクは、ルート側（場面 5）とは別の関数が作業ツリーで検査するので、ここでも確かめる
project_repo "$tmp/p-target" && rm "$tmp/p-target/worlds/demo/.claude/skills/resonite-build" \
  && ln -s ../../../.agents/skills/resonite-build "$tmp/p-target/worlds/demo/.claude/skills/resonite-build"
expect_fail_with "$tmp/p-target" 'worlds/demo/.claude/skills/resonite-build has unexpected target ../../../.agents/skills/resonite-build'

project_repo "$tmp/p-realdir" && rm "$tmp/p-realdir/worlds/demo/.claude/skills/resonite-build" \
  && mkdir "$tmp/p-realdir/worlds/demo/.claude/skills/resonite-build"
cp "$tmp/p-realdir/worlds/demo/.agents/skills/resonite-build/SKILL.md" "$tmp/p-realdir/worlds/demo/.claude/skills/resonite-build/SKILL.md"
expect_fail_with "$tmp/p-realdir" 'worlds/demo/.claude/skills/resonite-build is not a symlink'

# 8. 追跡解除した従来位置（ルート直下・深さ 1）のプロジェクトも検出して通過する
legacy_project_repo "$tmp/legacy"
bash "$checker" --root "$tmp/legacy" > "$tmp/legacy.out"
grep -qF 'ok: project akichi layout' "$tmp/legacy.out"

# 9. 作業領域の下に追跡ファイルがあれば失敗する（git add -f による再混入も含む）
project_repo "$tmp/p-tracked" && git -C "$tmp/p-tracked" add -f worlds/demo/.resoloop.json && git -C "$tmp/p-tracked" commit -q -m track
expect_fail_with "$tmp/p-tracked" 'tracked files under the world work areas'
legacy_project_repo "$tmp/legacy-tracked" && git -C "$tmp/legacy-tracked" add -f akichi/.resoloop.json && git -C "$tmp/legacy-tracked" commit -q -m track
expect_fail_with "$tmp/legacy-tracked" 'tracked files under the world work areas'

# .devcontainer に devcontainer.json・mount の関数集・initialize.bash を持つ一時リポジトリを作る。
# mounts は ~/.claude と ~/.claude.json の 2 つ
devcontainer_repo() {
  local r="$1"
  new_repo "$r"
  mkdir -p "$r/.devcontainer"
  cp "$root/.devcontainer/mounts.bash" "$r/.devcontainer/"
  cat > "$r/.devcontainer/devcontainer.json" <<'JSON'
{
	"mounts": [
		"source=${localEnv:HOME}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached",
		"source=${localEnv:HOME}/.claude.json,target=/home/vscode/.claude.json,type=bind,consistency=cached"
	],
	"features": {
		"ghcr.io/devcontainers/features/dotnet:2": {
			"version": "10.0",
			"additionalVersions": "10.0.201"
		}
	}
}
JSON
  printf '#!/bin/bash\nmkdir -p \\\n  "${HOME}/.claude"\ntouch \\\n  "${HOME}/.claude.json"\n' > "$r/.devcontainer/initialize.bash"
  commit_paths "$r" .devcontainer
}

# 10. mounts のソースと initialize.bash が作るパスが一致すれば通過し、違えば失敗して食い違いを示す
devcontainer_repo "$tmp/dc-ok"
bash "$checker" --root "$tmp/dc-ok" > "$tmp/dc-ok.out"
grep -qF 'ok: mounts match .devcontainer/initialize.bash' "$tmp/dc-ok.out"
devcontainer_repo "$tmp/mount-diff" && sed -i 's|^  "${HOME}/.claude"$|  "${HOME}/.claude" \\\n  "${HOME}/.codex"|' "$tmp/mount-diff/.devcontainer/initialize.bash" \
  && commit_paths "$tmp/mount-diff" .devcontainer
expect_fail_with "$tmp/mount-diff" 'mounts: ~/.codex is created by initialize.bash but not mounted by devcontainer.json'

# 11. assets は、設定で明示された最小プロジェクトだけを受け入れる。設定なしでは同じ構成も標準ワールドとして失敗する
#     （欠落を自動分類で隠さない）
new_repo "$tmp/assets"
mkdir -p "$tmp/assets/worlds/source"
printf '{}\n' > "$tmp/assets/worlds/source/.resoloop.json"
expect_fail_with "$tmp/assets" 'missing regular file AGENTS.md'
printf '{"worlds/source":"assets"}\n' > "$tmp/assets/.check-layout-projects.json"
bash "$checker" --root "$tmp/assets" > "$tmp/assets.out"
grep -qF 'ok: project worlds/source layout (assets)' "$tmp/assets.out"

# 12. 壊れた設定や、収集できないパスを指す設定は、暗黙に無視せず失敗する。正しい設定は通過する
project_repo "$tmp/profiles"
for config in '{' '{"../elsewhere":"assets"}' '{"worlds/missing":"assets"}'; do
  printf '%s\n' "$config" > "$tmp/profiles/.check-layout-projects.json"
  expect_fail_with "$tmp/profiles" '.check-layout-projects.json'
done
printf '{"worlds/demo":"world"}\n' > "$tmp/profiles/.check-layout-projects.json"
bash "$checker" --root "$tmp/profiles" | grep -qF 'PASS: check-layout'

printf 'PASS: check-layout script rejects broken layouts\n'
