#!/bin/bash
# scripts/new-world.sh の作成・適用・冪等性・食い違いの検出を、一時リポジトリとモックの resoloop / uv で検査する
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# ユーザの git 設定から隔離する（システム・グローバル設定と core.excludesFile を外す）。グローバル設定の
# safe.directory も外れるので、このリポジトリだけは所有者が違っても読めるようにしておく
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$repo_root"
# shellcheck source=lib/path.bash
source "$repo_root/tests/scripts/lib/path.bash"
script="$repo_root/scripts/new-world.sh"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# モック: resoloop init は最小の scaffold を作り、skills sync と uv は呼び出しを記録するだけ
mkdir -p "$tmp/mockbin"
cat > "$tmp/mockbin/resoloop" <<'EOF'
#!/bin/bash
printf '%s\n' "resoloop $*" >> "$MOCK_LOG"
case "$1" in
  init)
    d="$2"
    mkdir -p "$d/.agents/skills/resonite-build" "$d/.resoloop" "$d/flux"
    printf '{}\n' > "$d/.resoloop.json"
    printf '# ResoLoop project guide\n' > "$d/AGENTS.md"
    printf -- '---\nname: resonite-build\ndescription: mock\n---\n' > "$d/.agents/skills/resonite-build/SKILL.md"
    printf '{}\n' > "$d/.agents/skills/.resoloop-bundled.json"
    printf 'state/\nflux-state/\n' > "$d/.resoloop/.gitignore"
    printf '{}\n' > "$d/flux/resoloop.flux.json"
    ;;
  skills) exit 0 ;;
  *) exit 64 ;;
esac
EOF
cat > "$tmp/mockbin/uv" <<'EOF'
#!/bin/bash
printf '%s\n' "uv $* (cwd=$PWD)" >> "$MOCK_LOG"
EOF
chmod +x "$tmp/mockbin/resoloop" "$tmp/mockbin/uv"
export MOCK_LOG="$tmp/mock.log"
: > "$MOCK_LOG"
export PATH="$tmp/mockbin:$PATH"

# 雛形と共有物（.claude/settings.json、.pi、.agents/sp-implementer.md）を持つ一時リポジトリ
new_root() {
  local r="$1"
  git init -q "$r"
  mkdir -p "$r/scripts" "$r/.claude" "$r/.pi" "$r/.agents"
  cp -r "$repo_root/templates" "$r/templates"
  cp "$script" "$r/scripts/new-world.sh"
  printf '{}\n' > "$r/.claude/settings.json"
  printf 'pi\n' > "$r/.pi/APPEND_SYSTEM.md"
  printf -- '---\nname: sp-implementer\n---\n' > "$r/.agents/sp-implementer.md"
}
run() { local r="$1"; shift; bash "$r/scripts/new-world.sh" --root "$r" "$@"; }
expect_exit() {  # $1=期待する終了コード、$2=出力に含まれるべき文字列、残り=run の引数
  local want="$1" needle="$2" got=0
  shift 2
  run "$@" > "$tmp/out.txt" 2>&1 || got=$?
  [ "$got" -eq "$want" ] || { cat "$tmp/out.txt" >&2; fail "expected exit $want, got $got: $*"; }
  grep -qF -- "$needle" "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; fail "expected output '$needle': $*"; }
}
snapshot() {
  (cd "$1" && find . -printf '%y %p %l\n' | sort && find . -type f -print0 | sort -z | xargs -0 -r sha256sum)
}

# 1. 不正な名前は 2
new_root "$tmp/r1"
for bad in '' 'a b' '../x' '-x' 'x/y' '.hidden' 'demo-' 'a_'; do
  expect_exit 2 '' "$tmp/r1" --no-sync "$bad"
done
[ -z "$(ls -A "$tmp/r1" | grep -vxE 'scripts|templates|\.claude|\.pi|\.agents|\.git')" ] || fail 'invalid name created something'

# 2. 新規作成: resoloop init の後に雛形と symlink を作る
new_root "$tmp/r2"
expect_exit 0 'DONE: demo' "$tmp/r2" --no-sync demo
p="$tmp/r2/demo"
[ "$(cat "$p/CLAUDE.md")" = '@AGENTS.md' ] || fail 'CLAUDE.md content'
grep -qxF 'name = "demo"' "$p/pyproject.toml" || fail 'pyproject name'
grep -qxF '## このプロジェクト固有' "$p/AGENTS.md" || fail 'AGENTS.md section'
[ "$(grep -cxF 'cache/' "$p/.resoloop/.gitignore")" -eq 1 ] || fail 'cache/ appended once'
for link in '.claude/skills/resonite-build|../../.agents/skills/resonite-build' \
            '.claude/settings.json|../../.claude/settings.json' '.pi|../.pi' \
            '.agents/sp-implementer.md|../../.agents/sp-implementer.md'; do
  rel="${link%%|*}" target="${link#*|}"
  [ "$(readlink "$p/$rel")" = "$target" ] || fail "link $rel"
  [ -e "$p/$rel" ] || fail "dangling $rel"
done
grep -qF "resoloop init $p" "$MOCK_LOG" || fail 'resoloop init not called'

# 3. 既存ディレクトリに --apply 無しで実行すると 2
expect_exit 2 'use --apply' "$tmp/r2" --no-sync demo

# 4. --apply を繰り返しても何も変わらない
before="$(snapshot "$p")"
expect_exit 0 'DONE: demo' "$tmp/r2" --apply --no-sync demo
[ "$before" = "$(snapshot "$p")" ] || fail 'second --apply changed files'

# 5. 存在しないプロジェクトへの --apply は 2
expect_exit 2 'drop --apply' "$tmp/r2" --apply --no-sync missing

# 6. .pi が実ディレクトリなら 1 を返し、何も変更しない（CLAUDE.md も作らない）
new_root "$tmp/r6"
run "$tmp/r6" --no-sync demo >/dev/null
rm "$tmp/r6/demo/.pi" "$tmp/r6/demo/CLAUDE.md" && mkdir "$tmp/r6/demo/.pi"
before="$(snapshot "$tmp/r6/demo")"
expect_exit 1 'CONFLICT: .pi exists and is not a symlink' "$tmp/r6" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r6/demo")" ] || fail 'conflicting --apply changed files'

# 7. CLAUDE.md が雛形と違えば 1 を返し、何も変更しない
new_root "$tmp/r7"
run "$tmp/r7" --no-sync demo >/dev/null
printf 'other\n' > "$tmp/r7/demo/CLAUDE.md"
before="$(snapshot "$tmp/r7/demo")"
expect_exit 1 'CONFLICT: CLAUDE.md differs from templates/world-project/CLAUDE.md' "$tmp/r7" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r7/demo")" ] || fail 'case 7 changed files'

# 8. 対応する .agents/skills の無い .claude/skills のリンクは 1 を返し、何も変更しない
new_root "$tmp/r8"
run "$tmp/r8" --no-sync demo >/dev/null
ln -s ../../.agents/skills/stale "$tmp/r8/demo/.claude/skills/stale"
before="$(snapshot "$tmp/r8/demo")"
expect_exit 1 'CONFLICT: .claude/skills/stale has no matching .agents/skills/stale' "$tmp/r8" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r8/demo")" ] || fail 'case 8 changed files'

# 9. resoloop プロジェクトでないディレクトリへの --apply は 3
new_root "$tmp/r9"
mkdir "$tmp/r9/plain"
expect_exit 3 'not a resoloop project' "$tmp/r9" --apply --no-sync plain

# 10. resoloop が無ければ新規作成は 3
new_root "$tmp/r10"
no_resoloop="$(path_without "$tmp/no-resoloop" resoloop)"
if PATH="$no_resoloop" command -v resoloop >/dev/null 2>&1; then fail 'resoloop visible on the PATH without resoloop'; fi
PATH="$no_resoloop" expect_exit 3 'resoloop not found' "$tmp/r10" --no-sync demo

# 11. 同期ありでは uv sync をプロジェクトで実行し、resoloop skills sync --check を呼ぶ
new_root "$tmp/r11"
: > "$MOCK_LOG"
expect_exit 0 'ok: resoloop skills sync --check' "$tmp/r11" demo
grep -qF "uv sync (cwd=$tmp/r11/demo)" "$MOCK_LOG" || fail 'uv sync not run in the project'
grep -qF "resoloop skills sync $tmp/r11/demo --check" "$MOCK_LOG" || fail 'skills sync --check not run'

# 12. 既存の .resoloop/.gitignore に cache/ が無ければ 1 回だけ追記する
new_root "$tmp/r12"
run "$tmp/r12" --no-sync demo >/dev/null
printf 'state/\nflux-state/\n' > "$tmp/r12/demo/.resoloop/.gitignore"
run "$tmp/r12" --apply --no-sync demo >/dev/null
run "$tmp/r12" --apply --no-sync demo >/dev/null
[ "$(grep -cxF 'cache/' "$tmp/r12/demo/.resoloop/.gitignore")" -eq 1 ] || fail 'cache/ appended more than once'

# 13. SKILL.md の無いディレクトリ（移動後に残った空ディレクトリなど）にはリンクを張らない
new_root "$tmp/r13"
run "$tmp/r13" --no-sync demo >/dev/null
mkdir -p "$tmp/r13/demo/.agents/skills/leftover"
expect_exit 0 'DONE: demo' "$tmp/r13" --apply --no-sync demo
if [ -e "$tmp/r13/demo/.claude/skills/leftover" ] || [ -L "$tmp/r13/demo/.claude/skills/leftover" ]; then
  fail 'linked a directory without SKILL.md'
fi

# 14. 同期ありで uv sync が失敗したら 3 を返し、雛形の適用が済んでいることを伝える
new_root "$tmp/r14"
mkdir -p "$tmp/uv-fail"
printf '#!/bin/bash\nexit 1\n' > "$tmp/uv-fail/uv"
chmod +x "$tmp/uv-fail/uv"
PATH="$tmp/uv-fail:$PATH" expect_exit 3 'already applied' "$tmp/r14" demo
[ "$(cat "$tmp/r14/demo/CLAUDE.md")" = '@AGENTS.md' ] || fail 'scaffold was not applied before the failing uv sync'

# 15. 同期ありで uv が無ければ、resoloop も呼ばず何も作らずに 3
new_root "$tmp/r15"
mkdir -p "$tmp/resoloop-only"
cp "$tmp/mockbin/resoloop" "$tmp/resoloop-only/resoloop"
no_uv="$(path_without "$tmp/no-uv" uv resoloop)"
if PATH="$no_uv" command -v uv >/dev/null 2>&1; then fail 'uv visible on the PATH without uv'; fi
: > "$MOCK_LOG"
PATH="$tmp/resoloop-only:$no_uv" expect_exit 3 'uv not found' "$tmp/r15" demo
[ ! -e "$tmp/r15/demo" ] || fail 'created the project although uv is missing'
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop although uv is missing'

# 16. ルートの .pi が無ければ、新規作成は resoloop init を呼ばず何も作らずに 3
new_root "$tmp/r16"
rm -rf "$tmp/r16/.pi"
: > "$MOCK_LOG"
expect_exit 3 '.pi is missing at the repository root' "$tmp/r16" --no-sync demo
[ ! -e "$tmp/r16/demo" ] || fail 'created the project although the root .pi is missing'
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop init although the root .pi is missing'

# 17. resoloop init が失敗したら 3（resoloop 自身の終了コードをそのまま返さない）
new_root "$tmp/r17"
mkdir -p "$tmp/init-fail"
printf '#!/bin/bash\nexit 1\n' > "$tmp/init-fail/resoloop"
chmod +x "$tmp/init-fail/resoloop"
PATH="$tmp/init-fail:$PATH" expect_exit 3 'resoloop init failed for demo' "$tmp/r17" --no-sync demo

# 18. 新規作成で resoloop init の後に食い違いが見つかったら、init が作ったディレクトリが残ることを伝えて 1
new_root "$tmp/r18"
mkdir -p "$tmp/init-claude"
cat > "$tmp/init-claude/resoloop" <<EOF
#!/bin/bash
"$tmp/mockbin/resoloop" "\$@" || exit
[ "\$1" != init ] || printf 'other\n' > "\$2/CLAUDE.md"
EOF
chmod +x "$tmp/init-claude/resoloop"
PATH="$tmp/init-claude:$PATH" expect_exit 1 'demo was created by resoloop init and remains' "$tmp/r18" --no-sync demo
if grep -qF 'no changes were made' "$tmp/out.txt"; then fail 'claimed no changes after resoloop init created the project'; fi
[ "$(cat "$tmp/r18/demo/CLAUDE.md")" = 'other' ] || fail 'changed CLAUDE.md after the conflict'
if [ -e "$tmp/r18/demo/.pi" ] || [ -L "$tmp/r18/demo/.pi" ]; then fail 'applied links after the conflict'; fi

# 19. ルートの .gitignore で無視される名前は、resoloop を呼ばず何も作らずに 2（N-9）
new_root "$tmp/r19"
printf 'tmp/\n/private/\n' > "$tmp/r19/.gitignore"
: > "$MOCK_LOG"
expect_exit 2 "'tmp' is ignored by git" "$tmp/r19" --no-sync tmp
expect_exit 2 "'private' is ignored by git" "$tmp/r19" --no-sync private
[ ! -e "$tmp/r19/tmp" ] && [ ! -e "$tmp/r19/private" ] || fail 'created an ignored project'
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop for an ignored name'

# 20. 改行で終わらない AGENTS.md には、改行と空行を挟んでから固有節を追記する（N-9）
new_root "$tmp/r20"
run "$tmp/r20" --no-sync demo >/dev/null
printf '# guide' > "$tmp/r20/demo/AGENTS.md"
expect_exit 0 'appended: AGENTS.md' "$tmp/r20" --apply --no-sync demo
[ "$(sed -n '1p' "$tmp/r20/demo/AGENTS.md")" = '# guide' ] || fail 'the last line of AGENTS.md was changed'
[ -z "$(sed -n '2p' "$tmp/r20/demo/AGENTS.md")" ] || fail 'no blank line before the section'
[ "$(sed -n '3p' "$tmp/r20/demo/AGENTS.md")" = '## このプロジェクト固有' ] || fail 'the section does not start on its own line'

# 21. SKILL.md の無いディレクトリ（隠しディレクトリを含む）でも、ファイルがあればリンクを張る（check-layout と同じ定義、N-10）
new_root "$tmp/r21"
run "$tmp/r21" --no-sync demo >/dev/null
mkdir -p "$tmp/r21/demo/.agents/skills/shared-refs" && printf 'notes\n' > "$tmp/r21/demo/.agents/skills/shared-refs/notes.md"
mkdir -p "$tmp/r21/demo/.agents/skills/.hidden-refs" && printf 'notes\n' > "$tmp/r21/demo/.agents/skills/.hidden-refs/notes.md"
expect_exit 0 'linked: .claude/skills/shared-refs -> ../../.agents/skills/shared-refs' "$tmp/r21" --apply --no-sync demo
grep -qF 'linked: .claude/skills/.hidden-refs -> ../../.agents/skills/.hidden-refs' "$tmp/out.txt" || fail 'hidden directory was not linked'
expect_exit 0 'DONE: demo' "$tmp/r21" --apply --no-sync demo

# 22. 途中のディレクトリが通常ファイルなら 1 を返し、何も変更しない（N-16）
new_root "$tmp/r22"
run "$tmp/r22" --no-sync demo >/dev/null
rm -rf "$tmp/r22/demo/.claude" && printf 'x\n' > "$tmp/r22/demo/.claude"
before="$(snapshot "$tmp/r22/demo")"
expect_exit 1 'CONFLICT: .claude is not a directory' "$tmp/r22" --apply --no-sync demo
[ "$(grep -c 'is not a directory' "$tmp/out.txt")" -eq 1 ] || fail 'reported the same parent more than once'
[ "$before" = "$(snapshot "$tmp/r22/demo")" ] || fail 'case 22 changed files'

# 23. .claude/skills の隠しエントリも、対応するディレクトリが無ければ 1（N-16）
new_root "$tmp/r23"
run "$tmp/r23" --no-sync demo >/dev/null
ln -s ../../.agents/skills/.old "$tmp/r23/demo/.claude/skills/.old"
before="$(snapshot "$tmp/r23/demo")"
expect_exit 1 'CONFLICT: .claude/skills/.old has no matching .agents/skills/.old' "$tmp/r23" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r23/demo")" ] || fail 'case 23 changed files'

# 24. AGENTS.md が symlink なら追記せずに 1（リンク先を書き換えない、N-16）
new_root "$tmp/r24"
run "$tmp/r24" --no-sync demo >/dev/null
printf '# shared guide\n' > "$tmp/r24/shared-agents.md"
rm "$tmp/r24/demo/AGENTS.md" && ln -s ../shared-agents.md "$tmp/r24/demo/AGENTS.md"
expect_exit 1 'CONFLICT: AGENTS.md is a symlink' "$tmp/r24" --apply --no-sync demo
[ "$(cat "$tmp/r24/shared-agents.md")" = '# shared guide' ] || fail 'wrote through the AGENTS.md symlink'

# 25. 食い違いが複数あればすべて報告し、何も変更しない（N-16）
new_root "$tmp/r25"
run "$tmp/r25" --no-sync demo >/dev/null
rm "$tmp/r25/demo/.pi" && mkdir "$tmp/r25/demo/.pi"
printf 'other\n' > "$tmp/r25/demo/CLAUDE.md"
before="$(snapshot "$tmp/r25/demo")"
expect_exit 1 'CONFLICT: .pi exists and is not a symlink' "$tmp/r25" --apply --no-sync demo
grep -qF 'CONFLICT: CLAUDE.md differs from templates/world-project/CLAUDE.md' "$tmp/out.txt" || fail 'did not report every conflict'
[ "$before" = "$(snapshot "$tmp/r25/demo")" ] || fail 'case 25 changed files'

# 26. 行き先の違う symlink は 1（N-16）
new_root "$tmp/r26"
run "$tmp/r26" --no-sync demo >/dev/null
rm "$tmp/r26/demo/.pi" && ln -s ../other "$tmp/r26/demo/.pi"
before="$(snapshot "$tmp/r26/demo")"
expect_exit 1 'CONFLICT: .pi points to ../other, expected ../.pi' "$tmp/r26" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r26/demo")" ] || fail 'case 26 changed files'

# 27. 行き先が存在しないことになる symlink は 1（N-16）
new_root "$tmp/r27"
run "$tmp/r27" --no-sync demo >/dev/null
rm "$tmp/r27/demo/.claude/settings.json" "$tmp/r27/.claude/settings.json"
before="$(snapshot "$tmp/r27/demo")"
expect_exit 1 'CONFLICT: .claude/settings.json would point to missing ../../.claude/settings.json' "$tmp/r27" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r27/demo")" ] || fail 'case 27 changed files'

# 28. ルートの .claude/settings.json が無ければ、新規作成は resoloop init を呼ばず何も作らずに 3（N-16）
new_root "$tmp/r28"
rm "$tmp/r28/.claude/settings.json"
: > "$MOCK_LOG"
expect_exit 3 '.claude/settings.json is missing at the repository root' "$tmp/r28" --no-sync demo
[ ! -e "$tmp/r28/demo" ] || fail 'created the project although the root .claude/settings.json is missing'
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop init although the root .claude/settings.json is missing'

# 29. 名前に | を含むスキルディレクトリにも正しくリンクを張る（N-16）
new_root "$tmp/r29"
run "$tmp/r29" --no-sync demo >/dev/null
mkdir -p "$tmp/r29/demo/.agents/skills/a|b" && printf -- '---\nname: ab\n---\n' > "$tmp/r29/demo/.agents/skills/a|b/SKILL.md"
expect_exit 0 'DONE: demo' "$tmp/r29" --apply --no-sync demo
[ "$(readlink "$tmp/r29/demo/.claude/skills/a|b")" = '../../.agents/skills/a|b' ] || fail 'link for a name containing |'

# 30. 途中のディレクトリがディレクトリへの symlink でも 1 を返し、リンク先にも手元にも書かない（N-16）
new_root "$tmp/r30"
run "$tmp/r30" --no-sync demo >/dev/null
mv "$tmp/r30/demo/.claude" "$tmp/r30/claude-elsewhere" && ln -s ../claude-elsewhere "$tmp/r30/demo/.claude"
rm "$tmp/r30/claude-elsewhere/settings.json"
before="$(snapshot "$tmp/r30/demo")"
before_target="$(snapshot "$tmp/r30/claude-elsewhere")"
expect_exit 1 'CONFLICT: .claude is not a directory' "$tmp/r30" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r30/demo")" ] || fail 'case 30 changed files'
[ "$before_target" = "$(snapshot "$tmp/r30/claude-elsewhere")" ] || fail 'case 30 wrote through the .claude symlink'

printf 'PASS: new-world script behaves as specified\n'
