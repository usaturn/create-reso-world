#!/bin/bash
# scripts/check-layout.sh が通過・失敗を正しく判定することを一時リポジトリで検査する
set -euo pipefail
# GIT_CONFIG_GLOBAL=/dev/null だけでは XDG 既定の ~/.config/git/ignore が働いてしまうため、
# core.excludesFile も無効化し、システム設定も外してユーザの git 設定から隔離する
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
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

# 6. このリポジトリ自身が通過する
bash "$checker" | grep -qF 'PASS: check-layout'

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

# 仕様 4.2 を満たすプロジェクト demo を 1 つ持つリポジトリを作る
project_repo() {
  local r="$1" p="$1/demo"
  new_repo "$r"
  mkdir -p "$r/.claude" "$r/.pi" "$r/.agents" "$p/.agents/skills/resonite-build" "$p/.claude/skills" "$p/.resoloop" "$p/flux"
  printf '{}\n' > "$r/.claude/settings.json"
  printf 'pi\n' > "$r/.pi/APPEND_SYSTEM.md"
  printf -- '---\nname: sp-implementer\n---\n' > "$r/.agents/sp-implementer.md"
  printf '# guide\n\n## このプロジェクト固有\n\n- test\n' > "$p/AGENTS.md"
  printf '@AGENTS.md\n' > "$p/CLAUDE.md"
  printf '{}\n' > "$p/.resoloop.json"
  printf 'state/\nflux-state/\ncache/\n' > "$p/.resoloop/.gitignore"
  printf '[project]\nname = "demo"\n' > "$p/pyproject.toml"
  printf 'version = 1\n' > "$p/uv.lock"
  printf '{}\n' > "$p/.agents/skills/.resoloop-bundled.json"
  printf -- '---\nname: resonite-build\ndescription: d\n---\n' > "$p/.agents/skills/resonite-build/SKILL.md"
  printf '{}\n' > "$p/flux/resoloop.flux.json"
  ln -s ../../.agents/skills/resonite-build "$p/.claude/skills/resonite-build"
  ln -s ../../.claude/settings.json "$p/.claude/settings.json"
  ln -s ../.pi "$p/.pi"
  ln -s ../../.agents/sp-implementer.md "$p/.agents/sp-implementer.md"
  commit_paths "$r" .claude .pi .agents demo
}

# モックの resoloop: MOCK_RESOLOOP_FAIL と同名のプロジェクトだけ skills sync --check に失敗する
mkdir -p "$tmp/mockbin"
cat > "$tmp/mockbin/resoloop" <<'EOF'
#!/bin/bash
[ "$1 $2 $4" = 'skills sync --check' ] || exit 64
case "$3" in "${MOCK_RESOLOOP_FAIL:-__none__}"|*/"${MOCK_RESOLOOP_FAIL:-__none__}") echo 'SKILL_SYNC_REQUIRED' >&2; exit 6 ;; esac
exit 0
EOF
chmod +x "$tmp/mockbin/resoloop"
mock_path="$tmp/mockbin:$PATH"

# 21. 標準レイアウトのプロジェクトは通過し、resoloop があれば同期を確かめる
project_repo "$tmp/proj-ok"
PATH="$mock_path" bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-ok.out"
grep -qF 'ok: project demo layout' "$tmp/proj-ok.out"
grep -qF 'ok: resoloop skills sync --check (demo)' "$tmp/proj-ok.out"
grep -qF 'PASS: check-layout' "$tmp/proj-ok.out"

# 22. resoloop が無い環境（CI）では skip を表示して通過する
if PATH=/usr/local/bin:/usr/bin:/bin command -v resoloop >/dev/null 2>&1; then
  printf 'FAIL: resoloop visible on the reduced PATH\n' >&2; exit 1
fi
PATH=/usr/local/bin:/usr/bin:/bin bash "$checker" --root "$tmp/proj-ok" > "$tmp/proj-skip.out"
grep -qF 'skip: resoloop not found (skills sync check)' "$tmp/proj-skip.out"
grep -qF 'PASS: check-layout' "$tmp/proj-skip.out"

# 23. resoloop 同梱スキルの同期ずれは失敗する
PATH="$mock_path" MOCK_RESOLOOP_FAIL=demo expect_fail_with "$tmp/proj-ok" 'resoloop skills sync --check failed for demo'

# 24〜30. 標準レイアウトからの逸脱は失敗する（以降は mock の resoloop で実行する）
export PATH="$mock_path"
project_repo "$tmp/p24" && git -C "$tmp/p24" rm -q demo/CLAUDE.md && git -C "$tmp/p24" commit -q -m rm
expect_fail_with "$tmp/p24" 'demo: missing tracked file CLAUDE.md'

project_repo "$tmp/p25" && printf 'other\n' > "$tmp/p25/demo/CLAUDE.md" && commit_paths "$tmp/p25" demo
expect_fail_with "$tmp/p25" 'demo: CLAUDE.md must be exactly @AGENTS.md'

project_repo "$tmp/p26" && printf '# guide\n' > "$tmp/p26/demo/AGENTS.md" && commit_paths "$tmp/p26" demo
expect_fail_with "$tmp/p26" 'demo: AGENTS.md lacks ## このプロジェクト固有'

project_repo "$tmp/p27" && printf 'state/\nflux-state/\n' > "$tmp/p27/demo/.resoloop/.gitignore" && commit_paths "$tmp/p27" demo
expect_fail_with "$tmp/p27" 'demo: .resoloop/.gitignore lacks cache/'

project_repo "$tmp/p28" && rm "$tmp/p28/demo/.pi" && ln -s ../.agents "$tmp/p28/demo/.pi" && commit_paths "$tmp/p28" demo
expect_fail_with "$tmp/p28" 'demo: .pi must be a symlink to ../.pi'

project_repo "$tmp/p29" && git -C "$tmp/p29" rm -q demo/.claude/skills/resonite-build && git -C "$tmp/p29" commit -q -m rm
expect_fail_with "$tmp/p29" 'demo/.claude/skills: missing link resonite-build'

project_repo "$tmp/p30" && git -C "$tmp/p30" rm -q demo/.agents/sp-implementer.md && git -C "$tmp/p30" commit -q -m rm
expect_fail_with "$tmp/p30" 'demo: .agents/sp-implementer.md must be a symlink to ../../.agents/sp-implementer.md'

# 31. .resoloop.json の無いディレクトリはプロジェクトとして扱わない
project_repo "$tmp/p31"
mkdir -p "$tmp/p31/notes" && printf '# notes\n' > "$tmp/p31/notes/AGENTS.md" && commit_paths "$tmp/p31" notes
bash "$checker" --root "$tmp/p31" | grep -qF 'PASS: check-layout'

# 32. ネストした .resoloop.json が（ソート順で）最後に列挙されても検査を継続する
project_repo "$tmp/p32"
mkdir -p "$tmp/p32/zzz/sub" && printf '{}\n' > "$tmp/p32/zzz/sub/.resoloop.json" && commit_paths "$tmp/p32" zzz
bash "$checker" --root "$tmp/p32" > "$tmp/p32.out"
grep -qF 'ok: project demo layout' "$tmp/p32.out"
grep -qF 'PASS: check-layout' "$tmp/p32.out"

printf 'PASS: check-layout script behaves as specified\n'
