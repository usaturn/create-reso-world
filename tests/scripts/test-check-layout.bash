#!/bin/bash
# scripts/check-layout.sh が通過・失敗を正しく判定することを一時リポジトリで検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# GIT_CONFIG_GLOBAL=/dev/null だけでは XDG 既定の ~/.config/git/ignore が働いてしまうため、
# core.excludesFile も無効化し、システム設定も外してユーザの git 設定から隔離する。
# グローバル設定の safe.directory も外れるので、このリポジトリだけは所有者が違っても（CI のコンテナや
# Dev Container の bind mount）読めるようにしておく
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$root"
# shellcheck source=lib/path.bash
source "$root/tests/scripts/lib/path.bash"
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

assert_exit_code() {
  local expected="$1" out="$tmp/exit-out.txt"
  shift
  local actual=0
  "$@" > "$out" 2>&1 || actual=$?
  if [ "$actual" -ne "$expected" ]; then
    printf 'FAIL: expected exit %d, got %d for: %s\n' "$expected" "$actual" "$*" >&2
    cat "$out" >&2
    exit 1
  fi
}

# 1. 何も問題の無いリポジトリは通過する
new_repo "$tmp/clean"
bash "$checker" --root "$tmp/clean" | grep -qF 'PASS: check-layout'

# 2. 追跡禁止ファイル
new_repo "$tmp/forbidden"
printf 'x\n' > "$tmp/forbidden/TNX.txt"
git -C "$tmp/forbidden" add TNX.txt && git -C "$tmp/forbidden" commit -q -m add
expect_fail_with "$tmp/forbidden" 'forbidden tracked files'

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

# 5. 不正な引数は 64
assert_exit_code 64 bash "$checker" --bogus

# 6. このリポジトリ自身が通過し、mounts も検査される（skip されない）
bash "$checker" > "$tmp/self.out"
grep -qF 'ok: mounts match .devcontainer/initialize.bash' "$tmp/self.out"
grep -qF 'PASS: check-layout' "$tmp/self.out"

# 7. --root が git リポジトリでないディレクトリなら 64
mkdir -p "$tmp/notgit"
assert_exit_code 64 bash "$checker" --root "$tmp/notgit"

# 8. --root が存在しないパスなら 64
assert_exit_code 64 bash "$checker" --root "$tmp/does-not-exist"

# 9. --root にリポジトリのサブディレクトリを渡しても、トップレベルの禁止ファイルを検出する
new_repo "$tmp/subdir"
mkdir -p "$tmp/subdir/nested/deep"
printf 'x\n' > "$tmp/subdir/TNX.txt"
git -C "$tmp/subdir" add TNX.txt && git -C "$tmp/subdir" commit -q -m add
expect_fail_with "$tmp/subdir/nested/deep" 'forbidden tracked files'

# 10. 非 ASCII パス配下の追跡禁止ファイルも検出する
new_repo "$tmp/nonascii-forbidden"
mkdir -p "$tmp/nonascii-forbidden/資料"
printf 'x\n' > "$tmp/nonascii-forbidden/資料/TNX.txt"
git -C "$tmp/nonascii-forbidden" add 資料/TNX.txt && git -C "$tmp/nonascii-forbidden" commit -q -m add
expect_fail_with "$tmp/nonascii-forbidden" 'forbidden tracked files'

# 11. 行き先のある非 ASCII 名の symlink は誤検知しない
new_repo "$tmp/nonascii-symlink"
printf 't\n' > "$tmp/nonascii-symlink/target"
ln -s target "$tmp/nonascii-symlink/リンク"
git -C "$tmp/nonascii-symlink" add target リンク && git -C "$tmp/nonascii-symlink" commit -q -m link
bash "$checker" --root "$tmp/nonascii-symlink" | grep -qF 'PASS: check-layout'

# 12. リポジトリの外にコピーしたスクリプトでも --root を渡せば動く
mkdir -p "$tmp/detached"
cp "$checker" "$tmp/detached/check-layout.sh"
GIT_CEILING_DIRECTORIES="$tmp" bash "$tmp/detached/check-layout.sh" --root "$tmp/clean" | grep -qF 'PASS: check-layout'

# .agents/skills/foo を持つ一時リポジトリを作る（.claude 側は各ケースで作る）
skill_repo() {
  new_repo "$1"
  mkdir -p "$1/.agents/skills/foo" "$1/.claude/skills"
  printf -- '---\nname: foo\ndescription: d\n---\n' > "$1/.agents/skills/foo/SKILL.md"
}
commit_paths() {  # $1=リポジトリ、残り=追加するパス
  local r="$1"; shift
  git -C "$r" add -- "$@" && git -C "$r" commit -q -m change
}

# 13. .agents/skills と .claude/skills が 1:1 の symlink なら通過する
skill_repo "$tmp/skills-ok"
ln -s ../../.agents/skills/foo "$tmp/skills-ok/.claude/skills/foo"
commit_paths "$tmp/skills-ok" .agents .claude
bash "$checker" --root "$tmp/skills-ok" | grep -qF 'PASS: check-layout'

# 14. symlink が無ければ失敗する
skill_repo "$tmp/skills-missing"
commit_paths "$tmp/skills-missing" .agents
expect_fail_with "$tmp/skills-missing" 'missing link foo'

# 15. .claude/skills/foo が実ディレクトリなら失敗する
skill_repo "$tmp/skills-realdir"
mkdir -p "$tmp/skills-realdir/.claude/skills/foo"
cp "$tmp/skills-realdir/.agents/skills/foo/SKILL.md" "$tmp/skills-realdir/.claude/skills/foo/SKILL.md"
commit_paths "$tmp/skills-realdir" .agents .claude
expect_fail_with "$tmp/skills-realdir" '.claude/skills/foo is not a symlink'

# 16. 行き先が .agents/skills/foo でなければ失敗する
skill_repo "$tmp/skills-target"
mkdir -p "$tmp/skills-target/other/foo" && printf 'x\n' > "$tmp/skills-target/other/foo/SKILL.md"
ln -s ../../other/foo "$tmp/skills-target/.claude/skills/foo"
commit_paths "$tmp/skills-target" .agents .claude other
expect_fail_with "$tmp/skills-target" '.claude/skills/foo has unexpected target ../../other/foo'

# 17. 対応する .agents/skills の無いリンクは失敗する
skill_repo "$tmp/skills-extra"
ln -s ../../.agents/skills/foo "$tmp/skills-extra/.claude/skills/foo"
mkdir -p "$tmp/skills-extra/elsewhere/bar" && printf 'x\n' > "$tmp/skills-extra/elsewhere/bar/SKILL.md"
ln -s ../../elsewhere/bar "$tmp/skills-extra/.claude/skills/bar"
commit_paths "$tmp/skills-extra" .agents .claude elsewhere
expect_fail_with "$tmp/skills-extra" '.claude/skills/bar has no matching .agents/skills/bar'

# 18. .devin/skills を追跡していれば失敗する
new_repo "$tmp/devin"
mkdir -p "$tmp/devin/.devin/skills/x" && printf 'x\n' > "$tmp/devin/.devin/skills/x/SKILL.md"
commit_paths "$tmp/devin" .devin
expect_fail_with "$tmp/devin" '.devin/skills is still tracked'

# 19. スキル配下の 0 バイトの追跡ファイルは失敗する
skill_repo "$tmp/empty"
ln -s ../../.agents/skills/foo "$tmp/empty/.claude/skills/foo"
mkdir -p "$tmp/empty/.agents/skills/foo/scripts" && : > "$tmp/empty/.agents/skills/foo/scripts/helper.py"
commit_paths "$tmp/empty" .agents .claude
expect_fail_with "$tmp/empty" 'empty tracked file: .agents/skills/foo/scripts/helper.py'

# 20. ユーザのグローバル ignore が追跡ファイルを ignore していても誤検知しない（L72）
printf 'README.md\n' > "$tmp/global-ignore"
printf '[core]\n\texcludesFile = %s\n' "$tmp/global-ignore" > "$tmp/global-gitconfig"
GIT_CONFIG_COUNT=0 GIT_CONFIG_GLOBAL="$tmp/global-gitconfig" bash "$checker" --root "$tmp/clean" | grep -qF 'PASS: check-layout'

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

# モックの resoloop: MOCK_RESOLOOP_FAIL と同名のプロジェクトは同梱スキルの更新（SKILL_SYNC_REQUIRED）、
# MOCK_RESOLOOP_CONFLICT と同名のプロジェクトは手で編集した同梱スキル（SKILL_SYNC_CONFLICT）で skills sync --check に失敗する。
# 実物と同じく、- で始まるプロジェクト引数はオプションと解釈して拒む
mkdir -p "$tmp/mockbin"
cat > "$tmp/mockbin/resoloop" <<'EOF'
#!/bin/bash
[ "$1 $2 $4" = 'skills sync --check' ] || exit 64
case "$3" in -*) echo "unknown option $3" >&2; exit 64 ;; esac
case "$3" in "${MOCK_RESOLOOP_FAIL:-__none__}"|*/"${MOCK_RESOLOOP_FAIL:-__none__}") echo 'SKILL_SYNC_REQUIRED' >&2; exit 6 ;; esac
case "$3" in "${MOCK_RESOLOOP_CONFLICT:-__none__}"|*/"${MOCK_RESOLOOP_CONFLICT:-__none__}") echo 'SKILL_SYNC_CONFLICT' >&2; exit 6 ;; esac
exit 0
EOF
chmod +x "$tmp/mockbin/resoloop"
mock_path="$tmp/mockbin:$PATH"

# 21. 標準レイアウトのローカルプロジェクトは通過し、resoloop があれば同期を確かめる
project_repo "$tmp/proj-ok"
PATH="$mock_path" bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-ok.out"
grep -qF 'ok: project worlds/demo layout' "$tmp/proj-ok.out"
grep -qF 'ok: resoloop skills sync --check (worlds/demo)' "$tmp/proj-ok.out"
grep -qF 'PASS: check-layout' "$tmp/proj-ok.out"

# 22. resoloop が無い環境（CI）では skip を表示して通過する
no_resoloop="$(path_without "$tmp/no-resoloop" resoloop)"
if PATH="$no_resoloop" command -v resoloop >/dev/null 2>&1; then
  printf 'FAIL: resoloop visible on the PATH without resoloop\n' >&2; exit 1
fi
PATH="$no_resoloop" bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-skip.out"
grep -qF 'skip: resoloop not found (skills sync check)' "$tmp/proj-skip.out"
grep -qF 'PASS: check-layout' "$tmp/proj-skip.out"

# 23. 新しい版による同梱スキルの更新（SKILL_SYNC_REQUIRED）は warn を表示して通過し、手で編集した同梱スキル
#     （SKILL_SYNC_CONFLICT）は失敗する。どちらも resoloop の出力を字下げして示す
PATH="$mock_path" MOCK_RESOLOOP_FAIL=demo bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-drift.out" 2>&1 \
  || { cat "$tmp/proj-drift.out" >&2; printf 'FAIL: an outdated bundled skill failed check-layout\n' >&2; exit 1; }
grep -qF 'warn: resoloop skills sync --check (worlds/demo)' "$tmp/proj-drift.out" || { cat "$tmp/proj-drift.out" >&2; printf 'FAIL: no warn line\n' >&2; exit 1; }
grep -qxF '    SKILL_SYNC_REQUIRED' "$tmp/proj-drift.out" || { cat "$tmp/proj-drift.out" >&2; printf 'FAIL: resoloop output was not relayed\n' >&2; exit 1; }
grep -qF 'PASS: check-layout' "$tmp/proj-drift.out"
PATH="$mock_path" MOCK_RESOLOOP_CONFLICT=demo expect_fail_with "$tmp/proj-ok" 'resoloop skills sync --check failed for worlds/demo'
grep -qxF '    SKILL_SYNC_CONFLICT' "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; printf 'FAIL: resoloop output was not relayed\n' >&2; exit 1; }

# 24〜30. 標準レイアウトからの逸脱は失敗する（以降は mock の resoloop で実行する）。
# ローカルプロジェクトは追跡しないので、作業ツリーの変更がそのまま検査対象になる
export PATH="$mock_path"
project_repo "$tmp/p24" && rm "$tmp/p24/worlds/demo/CLAUDE.md"
expect_fail_with "$tmp/p24" 'worlds/demo: missing regular file CLAUDE.md'

project_repo "$tmp/p25" && printf 'other\n' > "$tmp/p25/worlds/demo/CLAUDE.md"
expect_fail_with "$tmp/p25" 'worlds/demo: CLAUDE.md must be exactly @AGENTS.md'

project_repo "$tmp/p26" && printf '# guide\n' > "$tmp/p26/worlds/demo/AGENTS.md"
expect_fail_with "$tmp/p26" 'worlds/demo: AGENTS.md lacks ## このプロジェクト固有'

project_repo "$tmp/p27" && printf 'state/\nflux-state/\n' > "$tmp/p27/worlds/demo/.resoloop/.gitignore"
expect_fail_with "$tmp/p27" 'worlds/demo: .resoloop/.gitignore lacks cache/'

project_repo "$tmp/p28" && rm "$tmp/p28/worlds/demo/.pi" && ln -s ../../.agents "$tmp/p28/worlds/demo/.pi"
expect_fail_with "$tmp/p28" 'worlds/demo: .pi must be a symlink to ../../.pi'

project_repo "$tmp/p29" && rm "$tmp/p29/worlds/demo/.claude/skills/resonite-build"
expect_fail_with "$tmp/p29" 'worlds/demo/.claude/skills: missing link resonite-build'

project_repo "$tmp/p30" && rm "$tmp/p30/worlds/demo/.agents/sp-implementer.md"
expect_fail_with "$tmp/p30" 'worlds/demo: .agents/sp-implementer.md must be a symlink to ../../../.agents/sp-implementer.md'

# 31. .resoloop.json の無いディレクトリはローカルプロジェクトとして扱わない（作業領域の直下でも同じ）。
#     作業領域の外（ルート直下の任意名）は .resoloop.json があっても検出しない
project_repo "$tmp/p31"
mkdir -p "$tmp/p31/notes" && printf '# notes\n' > "$tmp/p31/notes/AGENTS.md" && commit_paths "$tmp/p31" notes
mkdir -p "$tmp/p31/worlds/scratch" && printf '{}\n' > "$tmp/p31/worlds/scratch/notes.json"
mkdir -p "$tmp/p31/notwork" && printf '{}\n' > "$tmp/p31/notwork/.resoloop.json"
bash "$checker" --root "$tmp/p31" | grep -qF 'PASS: check-layout'

# 32. 作業領域の更に深い階層にある .resoloop.json は検出しない（プロジェクトは直下だけ）
project_repo "$tmp/p32"
mkdir -p "$tmp/p32/worlds/zzz/sub" && printf '{}\n' > "$tmp/p32/worlds/zzz/sub/.resoloop.json"
bash "$checker" --root "$tmp/p32" > "$tmp/p32.out"
grep -qF 'ok: project worlds/demo layout' "$tmp/p32.out"
grep -qF 'PASS: check-layout' "$tmp/p32.out"

# 33. .agents/skills 直下のファイルはリンクの対象外
skill_repo "$tmp/direct-file"
ln -s ../../.agents/skills/foo "$tmp/direct-file/.claude/skills/foo"
printf '# index\n' > "$tmp/direct-file/.agents/skills/README.md"
commit_paths "$tmp/direct-file" .agents .claude
bash "$checker" --root "$tmp/direct-file" | grep -qF 'PASS: check-layout'

# 34. .claude/skills/<name> が通常ファイル（mode 100644）なら失敗する
skill_repo "$tmp/regular-file"
printf '../../.agents/skills/foo\n' > "$tmp/regular-file/.claude/skills/foo"
commit_paths "$tmp/regular-file" .agents .claude
expect_fail_with "$tmp/regular-file" '.claude/skills/foo is not a symlink'

# 35. .claude/skills 自体が symlink なら、そのことを失敗として示す
skill_repo "$tmp/skills-dir-link"
rmdir "$tmp/skills-dir-link/.claude/skills"
ln -s ../.agents/skills "$tmp/skills-dir-link/.claude/skills"
commit_paths "$tmp/skills-dir-link" .agents .claude
expect_fail_with "$tmp/skills-dir-link" '.claude/skills must be a directory, not a symlink'
if grep -qF '.claude/skills/.claude' "$tmp/out.txt"; then printf 'FAIL: misleading message for a symlinked .claude/skills\n' >&2; exit 1; fi

# 36. 足りないリンクは名前順に報告する
skill_repo "$tmp/order"
for s in zeta alpha mid beta omega kappa delta; do   # bash の連想配列の列挙順が名前順にならない組
  mkdir -p "$tmp/order/.agents/skills/$s" && printf -- '---\nname: %s\n---\n' "$s" > "$tmp/order/.agents/skills/$s/SKILL.md"
done
commit_paths "$tmp/order" .agents
expect_fail_with "$tmp/order" 'missing link alpha'
[ "$(grep -o 'missing link [a-z]*' "$tmp/out.txt" | sed 's/^missing link //' | tr '\n' ' ')" = 'alpha beta delta foo kappa mid omega zeta ' ] \
  || { cat "$tmp/out.txt" >&2; printf 'FAIL: missing links are not sorted\n' >&2; exit 1; }

# 37. ローカルプロジェクトの .claude/skills でも、余分・向き違い・実ディレクトリを検出する
project_repo "$tmp/p37a"
mkdir -p "$tmp/p37a/worlds/demo/elsewhere/extra" && printf 'x\n' > "$tmp/p37a/worlds/demo/elsewhere/extra/SKILL.md"
ln -s ../../elsewhere/extra "$tmp/p37a/worlds/demo/.claude/skills/extra"
expect_fail_with "$tmp/p37a" 'worlds/demo/.claude/skills/extra has no matching worlds/demo/.agents/skills/extra'
project_repo "$tmp/p37b"
rm "$tmp/p37b/worlds/demo/.claude/skills/resonite-build" && ln -s ../../../.agents/skills/resonite-build "$tmp/p37b/worlds/demo/.claude/skills/resonite-build"
expect_fail_with "$tmp/p37b" 'worlds/demo/.claude/skills/resonite-build has unexpected target ../../../.agents/skills/resonite-build'
project_repo "$tmp/p37c"
rm "$tmp/p37c/worlds/demo/.claude/skills/resonite-build" && mkdir "$tmp/p37c/worlds/demo/.claude/skills/resonite-build"
cp "$tmp/p37c/worlds/demo/.agents/skills/resonite-build/SKILL.md" "$tmp/p37c/worlds/demo/.claude/skills/resonite-build/SKILL.md"
expect_fail_with "$tmp/p37c" 'worlds/demo/.claude/skills/resonite-build is not a symlink'

# 38. CLAUDE.md は @AGENTS.md の 1 行だけ（末尾の空行も認めない）
project_repo "$tmp/p38" && printf '@AGENTS.md\n\n\n' > "$tmp/p38/worlds/demo/CLAUDE.md"
expect_fail_with "$tmp/p38" 'worlds/demo: CLAUDE.md must be exactly @AGENTS.md'

# 39. 必須ファイルと同名のディレクトリ（worlds/demo/uv.lock/x）は必須ファイルとして数えない
project_repo "$tmp/p39" && rm "$tmp/p39/worlds/demo/uv.lock"
mkdir -p "$tmp/p39/worlds/demo/uv.lock" && printf 'x\n' > "$tmp/p39/worlds/demo/uv.lock/x"
expect_fail_with "$tmp/p39" 'worlds/demo: missing regular file uv.lock'

# 40. - で始まるプロジェクト名も検査でき、resoloop には ./ 付きで渡す
project_repo "$tmp/p40" -dash
bash "$checker" --root "$tmp/p40" > "$tmp/p40.out"
grep -qF 'ok: project worlds/-dash layout' "$tmp/p40.out"
grep -qF 'ok: resoloop skills sync --check (worlds/-dash)' "$tmp/p40.out"

# 41. 追跡解除した従来位置（ルート直下・深さ 1）のプロジェクトも検出し、深さに合う symlink を要求する
legacy_project_repo "$tmp/p41a"
bash "$checker" --root "$tmp/p41a" > "$tmp/p41a.out"
grep -qF 'ok: project akichi layout' "$tmp/p41a.out"
grep -qF 'ok: resoloop skills sync --check (akichi)' "$tmp/p41a.out"
legacy_project_repo "$tmp/p41b" && rm "$tmp/p41b/akichi/.pi" && ln -s ../../.pi "$tmp/p41b/akichi/.pi"
expect_fail_with "$tmp/p41b" 'akichi: .pi must be a symlink to ../.pi'
skill_repo "$tmp/p41c"
ln -s ../../.agents/skills/foo "$tmp/p41c/.claude/skills/foo"
commit_paths "$tmp/p41c" .agents .claude
rm "$tmp/p41c/.agents/skills/foo/SKILL.md"
bash "$checker" --root "$tmp/p41c" > "$tmp/p41c.out" 2>&1 || true
if grep -qF 'empty tracked file:' "$tmp/p41c.out"; then printf 'FAIL: a file deleted only from the worktree was reported as empty\n' >&2; exit 1; fi
grep -qF 'ok: skill trees hold no retired or empty tracked files' "$tmp/p41c.out" || { cat "$tmp/p41c.out" >&2; printf 'FAIL: case 41c did not run the hygiene check to the end\n' >&2; exit 1; }
grep -qF 'PASS: check-layout' "$tmp/p41c.out" || { cat "$tmp/p41c.out" >&2; printf 'FAIL: case 41c did not pass\n' >&2; exit 1; }

# 42. ローカルプロジェクトは clone に含まれない（追跡しない）。clone はプロジェクト無しで通過する
git clone -q "$tmp/proj-ok" "$tmp/cloned"
[ ! -e "$tmp/cloned/worlds" ] || { printf 'FAIL: the clone contains the ignored worlds directory\n' >&2; exit 1; }
bash "$checker" --root "$tmp/cloned" | grep -qF 'PASS: check-layout'
# 作業領域の下に追跡ファイルがあれば失敗する（git add -f による再混入も含む）
project_repo "$tmp/p42a" && git -C "$tmp/p42a" add -f worlds/demo/.resoloop.json && git -C "$tmp/p42a" commit -q -m track
expect_fail_with "$tmp/p42a" 'tracked files under the world work areas'
legacy_project_repo "$tmp/p42b" && git -C "$tmp/p42b" add -f akichi/.resoloop.json && git -C "$tmp/p42b" commit -q -m track
expect_fail_with "$tmp/p42b" 'tracked files under the world work areas'

# 42c. ルートの共有物（行き先）を消せば、プロジェクトの symlink は行き先文字列が正しくても dangling として失敗する
project_repo "$tmp/p42c" && rm -rf "$tmp/p42c/.pi"
expect_fail_with "$tmp/p42c" 'worlds/demo: .pi is a dangling symlink to ../../.pi'

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

# 43. .devcontainer を持つリポジトリは mount を検査して通過する。devcontainer.json を追跡していないリポジトリでは skip を表示する
devcontainer_repo "$tmp/dc-ok"
bash "$checker" --root "$tmp/dc-ok" > "$tmp/dc-ok.out"
grep -qF 'ok: mounts match .devcontainer/initialize.bash' "$tmp/dc-ok.out"
grep -qF 'PASS: check-layout' "$tmp/dc-ok.out"
bash "$checker" --root "$tmp/clean" > "$tmp/dc-skip.out"
grep -qF 'skip: .devcontainer/devcontainer.json is not tracked (mount check)' "$tmp/dc-skip.out"

# 45. devcontainer.json が作業ツリーにあっても追跡していなければ skip
devcontainer_repo "$tmp/dc-untracked" && git -C "$tmp/dc-untracked" rm -q --cached .devcontainer/devcontainer.json \
  && git -C "$tmp/dc-untracked" commit -q -m untrack
[ -f "$tmp/dc-untracked/.devcontainer/devcontainer.json" ] || { printf 'FAIL: case 45 lost the untracked file\n' >&2; exit 1; }
bash "$checker" --root "$tmp/dc-untracked" > "$tmp/dc-untracked.out"
grep -qF 'skip: .devcontainer/devcontainer.json is not tracked (mount check)' "$tmp/dc-untracked.out"

# 46. 衝突の解決中（ステージ 0 に無い）の .devcontainer のファイルは、終了コード 1 で解決を促す（128 で止まらない）
devcontainer_repo "$tmp/dc-conflict"
git -C "$tmp/dc-conflict" checkout -q -b other
printf '# other\n' >> "$tmp/dc-conflict/.devcontainer/initialize.bash" && commit_paths "$tmp/dc-conflict" .devcontainer
git -C "$tmp/dc-conflict" checkout -q -
printf '# mine\n' >> "$tmp/dc-conflict/.devcontainer/initialize.bash" && commit_paths "$tmp/dc-conflict" .devcontainer
if git -C "$tmp/dc-conflict" merge -q other >/dev/null 2>&1; then printf 'FAIL: case 46 merged without a conflict\n' >&2; exit 1; fi
expect_fail_with "$tmp/dc-conflict" '.devcontainer/initialize.bash has unresolved merge conflicts'

# 47. index から読めない blob（壊れたオブジェクト）は、終了コード 1 の FAIL として報告する
remove_object() {  # $1=リポジトリ、$2=パス。index にある blob のオブジェクトファイルを消す
  local oid
  oid="$(git -C "$1" rev-parse ":$2")"
  rm -f -- "${1:?}/.git/objects/${oid:0:2}/${oid:2}"
}
devcontainer_repo "$tmp/dc-corrupt" && remove_object "$tmp/dc-corrupt" .devcontainer/initialize.bash
expect_fail_with "$tmp/dc-corrupt" 'cannot read .devcontainer/initialize.bash from the index'
skill_repo "$tmp/link-corrupt"
ln -s ../../.agents/skills/foo "$tmp/link-corrupt/.claude/skills/foo"
commit_paths "$tmp/link-corrupt" .agents .claude
remove_object "$tmp/link-corrupt" .claude/skills/foo
expect_fail_with "$tmp/link-corrupt" 'cannot read the target of .claude/skills/foo from the index'

# 48. mounts のソースと initialize.bash が作るパスが違えば失敗し、食い違いを示す
devcontainer_repo "$tmp/mount-diff" && sed -i 's|^  "${HOME}/.claude"$|  "${HOME}/.claude" \\\n  "${HOME}/.codex"|' "$tmp/mount-diff/.devcontainer/initialize.bash" \
  && commit_paths "$tmp/mount-diff" .devcontainer
expect_fail_with "$tmp/mount-diff" 'mounts: ~/.codex is created by initialize.bash but not mounted by devcontainer.json'
devcontainer_repo "$tmp/mount-missing" && git -C "$tmp/mount-missing" rm -q .devcontainer/initialize.bash .devcontainer/mounts.bash \
  && git -C "$tmp/mount-missing" commit -q -m rm
expect_fail_with "$tmp/mount-missing" 'missing tracked file .devcontainer/mounts.bash'
grep -qF 'missing tracked file .devcontainer/initialize.bash' "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; printf 'FAIL: missing initialize.bash was not reported\n' >&2; exit 1; }

# 49. mounts も index の内容で判定する（作業ツリーの initialize.bash だけが違っても通過する）
devcontainer_repo "$tmp/mount-worktree"
printf '#!/bin/bash\n' > "$tmp/mount-worktree/.devcontainer/initialize.bash"
bash "$checker" --root "$tmp/mount-worktree" > "$tmp/mount-worktree.out"
grep -qF 'ok: mounts match .devcontainer/initialize.bash' "$tmp/mount-worktree.out"

# 50. assets は明示された最小プロジェクトだけを受け入れ、同梱スキル同期を呼ばない。
# 設定なしでは同じ構成も標準ワールドとして失敗する（欠落を自動分類で隠さない）。
new_repo "$tmp/assets"
mkdir -p "$tmp/assets/worlds/source"
printf '{}\n' > "$tmp/assets/worlds/source/.resoloop.json"
expect_fail_with "$tmp/assets" 'missing regular file AGENTS.md'
printf '{"worlds/source":"assets"}\n' > "$tmp/assets/.check-layout-projects.json"
MOCK_RESOLOOP_CONFLICT=source bash "$checker" --root "$tmp/assets" > "$tmp/assets.out"
grep -qF 'ok: project worlds/source layout (assets)' "$tmp/assets.out"
grep -qF 'skip: resoloop skills sync --check (worlds/source): assets profile' "$tmp/assets.out"
printf 'bad\n' > "$tmp/assets/TNX.txt"
commit_paths "$tmp/assets" TNX.txt
expect_fail_with "$tmp/assets" 'forbidden tracked files'

# 51. items は共通の配置とスキル検査を維持し、root flux の代わりに実ディレクトリ items を要求する。
project_repo "$tmp/items"
rm -- "${tmp:?}/items/worlds/demo/flux/resoloop.flux.json"
mkdir "$tmp/items/worlds/demo/items"
printf '{"worlds/demo":"items"}\n' > "$tmp/items/.check-layout-projects.json"
bash "$checker" --root "$tmp/items" > "$tmp/items.out"
grep -qF 'ok: project worlds/demo layout (items)' "$tmp/items.out"
grep -qF 'ok: resoloop skills sync --check (worlds/demo)' "$tmp/items.out"
rm -- "${tmp:?}/items/worlds/demo/uv.lock"
expect_fail_with "$tmp/items" 'missing regular file uv.lock'
printf 'version = 1\n' > "$tmp/items/worlds/demo/uv.lock"
rm -- "${tmp:?}/items/worlds/demo/.pi"
expect_fail_with "$tmp/items" '.pi must be a symlink'
ln -s ../../.pi "$tmp/items/worlds/demo/.pi"
rmdir -- "${tmp:?}/items/worlds/demo/items"
expect_fail_with "$tmp/items" 'missing real directory items'
ln -s flux "$tmp/items/worlds/demo/items"
expect_fail_with "$tmp/items" 'missing real directory items'

# 52. 壊れた設定や未収集パスは、暗黙の無視ではなく終了コード1になる。
project_repo "$tmp/profiles"
for config in '{' '[]' 'null' '{"worlds/demo":null}' '{"worlds/demo":"skip"}' \
  '{} {}' \
  '{"../elsewhere":"assets"}' '{"worlds/demo/deep":"assets"}' \
  '{"worlds/demo*":"assets"}' '{"worlds/missing":"assets"}'; do
  printf '%s\n' "$config" > "$tmp/profiles/.check-layout-projects.json"
  expect_fail_with "$tmp/profiles" '.check-layout-projects.json'
done
printf '{}\n' > "$tmp/profiles/.check-layout-projects.json"
bash "$checker" --root "$tmp/profiles" > "$tmp/empty-profiles.out"
printf '{"worlds/demo":"world"}\n' > "$tmp/profiles/.check-layout-projects.json"
bash "$checker" --root "$tmp/profiles" > "$tmp/profiles.out"
rm -- "${tmp:?}/profiles/worlds/demo/uv.lock"
expect_fail_with "$tmp/profiles" 'missing regular file uv.lock'
printf 'version = 1\n' > "$tmp/profiles/worlds/demo/uv.lock"
no_jq="$(path_without "$tmp/no-jq" jq)"
PATH="$no_jq" expect_fail_with "$tmp/profiles" 'jq is required for .check-layout-projects.json'
# 設定が無ければjqを追加の依存にしない。
rm -- "${tmp:?}/profiles/.check-layout-projects.json"
PATH="$no_jq" bash "$checker" --root "$tmp/profiles" > "$tmp/no-jq.out"
ln -s nowhere "$tmp/profiles/.check-layout-projects.json"
expect_fail_with "$tmp/profiles" '.check-layout-projects.json must be a regular file'
rm -- "${tmp:?}/profiles/.check-layout-projects.json"
mkdir "$tmp/profiles/.check-layout-projects.json"
expect_fail_with "$tmp/profiles" '.check-layout-projects.json must be a regular file'

# 53. assets のmanifestも通常ファイルが必要。--rootは呼出元ではなく対象の設定を読む。
new_repo "$tmp/asset-link"
mkdir -p "$tmp/asset-link/worlds/source"
printf '{}\n' > "$tmp/asset-link/manifest.json"
ln -s ../../manifest.json "$tmp/asset-link/worlds/source/.resoloop.json"
printf '{"worlds/source":"assets"}\n' > "$tmp/asset-link/.check-layout-projects.json"
expect_fail_with "$tmp/asset-link" 'missing regular file .resoloop.json'
legacy_project_repo "$tmp/legacy-profile"
printf '{"akichi":"items"}\n' > "$tmp/legacy-profile/.check-layout-projects.json"
mkdir "$tmp/legacy-profile/akichi/items"
bash "$checker" --root "$tmp/legacy-profile" > "$tmp/legacy-profile.out"
grep -qF 'ok: project akichi layout (items)' "$tmp/legacy-profile.out"

printf 'PASS: check-layout script behaves as specified\n'
