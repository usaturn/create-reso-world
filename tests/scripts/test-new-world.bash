#!/bin/bash
# scripts/new-world.sh の作成・適用・冪等性・食い違いの検出を、一時リポジトリとモックの resoloop / uv で検査する
set -euo pipefail
# 外から渡された GIT_* を除く。linked worktree の git rebase --exec は GIT_DIR を export するので、残すと
# 直接実行したときに一時リポジトリの git init・git -C が、そのリポジトリの設定・index・ブランチを書き換える（#200）
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')
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
trap 'rm -rf -- "${tmp:?}"' EXIT
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
  (cd "$1" && find . -printf '%y %m %p %l\n' | sort && find . -type f -print0 | sort -z | xargs -0 -r sha256sum)
}

# 固定するパス・値・mode は、利用者所有の指定を上書きしたり、競合検査前に
# chmod / JSON 編集してしまう不具合を防ぐため。本文の文字列ではなく実際の生成物を検査する。
expect_wrapper() {
  local p="$1"
  [ -x "$p/.resoloop/blender-system-python" ] || fail 'wrapper not executable'
  jq -e --arg path "$p/.resoloop/blender-system-python" \
    '.blenderExecutable == $path' "$p/.resoloop.json" >/dev/null || fail 'absolute wrapper path'
}

# 1. 不正な名前は 2
new_root "$tmp/r1"
for bad in '' 'a b' '../x' '-x' 'x/y' '.hidden' 'demo-' 'a_'; do
  expect_exit 2 '' "$tmp/r1" --no-sync "$bad"
done
[ -z "$(ls -A "$tmp/r1" | grep -vxE 'scripts|templates|\.claude|\.pi|\.agents|\.git')" ] || fail 'invalid name created something'

# 2. 新規作成: worlds/<name> に resoloop init の後で雛形と symlink を作る。
#    ルートの共有物を指すリンクは深さ 2（../.. してからルート）、.claude/skills はプロジェクト内で深さに依存しない
new_root "$tmp/r2"
expect_exit 0 'DONE: demo' "$tmp/r2" --no-sync demo
p="$tmp/r2/worlds/demo"
expect_wrapper "$p"
[ "$(cat "$p/CLAUDE.md")" = '@AGENTS.md' ] || fail 'CLAUDE.md content'
grep -qxF 'name = "demo"' "$p/pyproject.toml" || fail 'pyproject name'
grep -qxF '## このプロジェクト固有' "$p/AGENTS.md" || fail 'AGENTS.md section'
[ "$(grep -cxF 'cache/' "$p/.resoloop/.gitignore")" -eq 1 ] || fail 'cache/ appended once'
for link in '.claude/skills/resonite-build|../../.agents/skills/resonite-build' \
            '.claude/settings.json|../../../.claude/settings.json' '.pi|../../.pi' \
            '.agents/sp-implementer.md|../../../.agents/sp-implementer.md'; do
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
rm "$tmp/r6/worlds/demo/.pi" "$tmp/r6/worlds/demo/CLAUDE.md" && mkdir "$tmp/r6/worlds/demo/.pi"
before="$(snapshot "$tmp/r6/worlds/demo")"
expect_exit 1 'CONFLICT: .pi exists and is not a symlink' "$tmp/r6" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r6/worlds/demo")" ] || fail 'conflicting --apply changed files'

# 7. CLAUDE.md が雛形と違えば 1 を返し、何も変更しない
new_root "$tmp/r7"
run "$tmp/r7" --no-sync demo >/dev/null
printf 'other\n' > "$tmp/r7/worlds/demo/CLAUDE.md"
before="$(snapshot "$tmp/r7/worlds/demo")"
expect_exit 1 'CONFLICT: CLAUDE.md differs from templates/world-project/CLAUDE.md' "$tmp/r7" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r7/worlds/demo")" ] || fail 'case 7 changed files'

# 8. 対応する .agents/skills の無い .claude/skills のリンクは 1 を返し、何も変更しない
new_root "$tmp/r8"
run "$tmp/r8" --no-sync demo >/dev/null
ln -s ../../.agents/skills/stale "$tmp/r8/worlds/demo/.claude/skills/stale"
before="$(snapshot "$tmp/r8/worlds/demo")"
expect_exit 1 'CONFLICT: .claude/skills/stale has no matching .agents/skills/stale' "$tmp/r8" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r8/worlds/demo")" ] || fail 'case 8 changed files'

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
grep -qF "uv sync (cwd=$tmp/r11/worlds/demo)" "$MOCK_LOG" || fail 'uv sync not run in the project'
grep -qF "resoloop skills sync $tmp/r11/worlds/demo --check" "$MOCK_LOG" || fail 'skills sync --check not run'

# 12. 既存の .resoloop/.gitignore に cache/ が無ければ 1 回だけ追記する
new_root "$tmp/r12"
run "$tmp/r12" --no-sync demo >/dev/null
printf 'state/\nflux-state/\n' > "$tmp/r12/worlds/demo/.resoloop/.gitignore"
run "$tmp/r12" --apply --no-sync demo >/dev/null
run "$tmp/r12" --apply --no-sync demo >/dev/null
[ "$(grep -cxF 'cache/' "$tmp/r12/worlds/demo/.resoloop/.gitignore")" -eq 1 ] || fail 'cache/ appended more than once'

# 13. SKILL.md の無いディレクトリ（移動後に残った空ディレクトリなど）にはリンクを張らない
new_root "$tmp/r13"
run "$tmp/r13" --no-sync demo >/dev/null
mkdir -p "$tmp/r13/worlds/demo/.agents/skills/leftover"
expect_exit 0 'DONE: demo' "$tmp/r13" --apply --no-sync demo
if [ -e "$tmp/r13/worlds/demo/.claude/skills/leftover" ] || [ -L "$tmp/r13/worlds/demo/.claude/skills/leftover" ]; then
  fail 'linked a directory without SKILL.md'
fi

# 14. 同期ありで uv sync が失敗したら 3 を返し、雛形の適用が済んでいることを伝える
new_root "$tmp/r14"
mkdir -p "$tmp/uv-fail"
printf '#!/bin/bash\nexit 1\n' > "$tmp/uv-fail/uv"
chmod +x "$tmp/uv-fail/uv"
PATH="$tmp/uv-fail:$PATH" expect_exit 3 'already applied' "$tmp/r14" demo
[ "$(cat "$tmp/r14/worlds/demo/CLAUDE.md")" = '@AGENTS.md' ] || fail 'scaffold was not applied before the failing uv sync'

# 15. 同期ありで uv が無ければ、resoloop も呼ばず何も作らずに 3
new_root "$tmp/r15"
mkdir -p "$tmp/resoloop-only"
cp "$tmp/mockbin/resoloop" "$tmp/resoloop-only/resoloop"
no_uv="$(path_without "$tmp/no-uv" uv resoloop)"
if PATH="$no_uv" command -v uv >/dev/null 2>&1; then fail 'uv visible on the PATH without uv'; fi
: > "$MOCK_LOG"
PATH="$tmp/resoloop-only:$no_uv" expect_exit 3 'uv not found' "$tmp/r15" demo
[ ! -e "$tmp/r15/worlds/demo" ] || fail 'created the project although uv is missing'
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop although uv is missing'

# 16. ルートの .pi が無ければ、新規作成は resoloop init を呼ばず何も作らずに 3
new_root "$tmp/r16"
rm -rf "$tmp/r16/.pi"
: > "$MOCK_LOG"
expect_exit 3 '.pi is missing at the repository root' "$tmp/r16" --no-sync demo
[ ! -e "$tmp/r16/worlds/demo" ] || fail 'created the project although the root .pi is missing'
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
[ "$(cat "$tmp/r18/worlds/demo/CLAUDE.md")" = 'other' ] || fail 'changed CLAUDE.md after the conflict'
if [ -e "$tmp/r18/worlds/demo/.pi" ] || [ -L "$tmp/r18/worlds/demo/.pi" ]; then fail 'applied links after the conflict'; fi

# 19. 予約名 worlds と、ルート直下の既存エントリと同名の新規作成は 2。resoloop は呼ばず何も作らない
new_root "$tmp/r19"
mkdir -p "$tmp/r19/notes"
: > "$MOCK_LOG"
expect_exit 2 'is the work area' "$tmp/r19" --no-sync worlds
expect_exit 2 'already exists' "$tmp/r19" --no-sync notes
[ ! -e "$tmp/r19/worlds/worlds" ] && [ ! -e "$tmp/r19/worlds/notes" ] || fail 'created a reserved or colliding project'
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop for a reserved or colliding name'

# 20. 改行で終わらない AGENTS.md には、改行と空行を挟んでから固有節を追記する（N-9）
new_root "$tmp/r20"
run "$tmp/r20" --no-sync demo >/dev/null
printf '# guide' > "$tmp/r20/worlds/demo/AGENTS.md"
expect_exit 0 'appended: AGENTS.md' "$tmp/r20" --apply --no-sync demo
[ "$(sed -n '1p' "$tmp/r20/worlds/demo/AGENTS.md")" = '# guide' ] || fail 'the last line of AGENTS.md was changed'
[ -z "$(sed -n '2p' "$tmp/r20/worlds/demo/AGENTS.md")" ] || fail 'no blank line before the section'
[ "$(sed -n '3p' "$tmp/r20/worlds/demo/AGENTS.md")" = '## このプロジェクト固有' ] || fail 'the section does not start on its own line'

# 21. SKILL.md の無いディレクトリ（隠しディレクトリを含む）でも、ファイルがあればリンクを張る（check-layout と同じ定義、N-10）
new_root "$tmp/r21"
run "$tmp/r21" --no-sync demo >/dev/null
mkdir -p "$tmp/r21/worlds/demo/.agents/skills/shared-refs" && printf 'notes\n' > "$tmp/r21/worlds/demo/.agents/skills/shared-refs/notes.md"
mkdir -p "$tmp/r21/worlds/demo/.agents/skills/.hidden-refs" && printf 'notes\n' > "$tmp/r21/worlds/demo/.agents/skills/.hidden-refs/notes.md"
expect_exit 0 'linked: .claude/skills/shared-refs -> ../../.agents/skills/shared-refs' "$tmp/r21" --apply --no-sync demo
grep -qF 'linked: .claude/skills/.hidden-refs -> ../../.agents/skills/.hidden-refs' "$tmp/out.txt" || fail 'hidden directory was not linked'
expect_exit 0 'DONE: demo' "$tmp/r21" --apply --no-sync demo

# 22. 途中のディレクトリが通常ファイルなら 1 を返し、何も変更しない（N-16）
new_root "$tmp/r22"
run "$tmp/r22" --no-sync demo >/dev/null
rm -rf "$tmp/r22/worlds/demo/.claude" && printf 'x\n' > "$tmp/r22/worlds/demo/.claude"
before="$(snapshot "$tmp/r22/worlds/demo")"
expect_exit 1 'CONFLICT: .claude is not a directory' "$tmp/r22" --apply --no-sync demo
[ "$(grep -c 'is not a directory' "$tmp/out.txt")" -eq 1 ] || fail 'reported the same parent more than once'
[ "$before" = "$(snapshot "$tmp/r22/worlds/demo")" ] || fail 'case 22 changed files'

# 23. .claude/skills の隠しエントリも、対応するディレクトリが無ければ 1（N-16）
new_root "$tmp/r23"
run "$tmp/r23" --no-sync demo >/dev/null
ln -s ../../.agents/skills/.old "$tmp/r23/worlds/demo/.claude/skills/.old"
before="$(snapshot "$tmp/r23/worlds/demo")"
expect_exit 1 'CONFLICT: .claude/skills/.old has no matching .agents/skills/.old' "$tmp/r23" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r23/worlds/demo")" ] || fail 'case 23 changed files'

# 24. AGENTS.md が symlink なら追記せずに 1（リンク先を書き換えない、N-16）
new_root "$tmp/r24"
run "$tmp/r24" --no-sync demo >/dev/null
printf '# shared guide\n' > "$tmp/r24/shared-agents.md"
rm "$tmp/r24/worlds/demo/AGENTS.md" && ln -s ../../shared-agents.md "$tmp/r24/worlds/demo/AGENTS.md"
expect_exit 1 'CONFLICT: AGENTS.md is a symlink' "$tmp/r24" --apply --no-sync demo
[ "$(cat "$tmp/r24/shared-agents.md")" = '# shared guide' ] || fail 'wrote through the AGENTS.md symlink'

# 25. 食い違いが複数あればすべて報告し、何も変更しない（N-16）
new_root "$tmp/r25"
run "$tmp/r25" --no-sync demo >/dev/null
rm "$tmp/r25/worlds/demo/.pi" && mkdir "$tmp/r25/worlds/demo/.pi"
printf 'other\n' > "$tmp/r25/worlds/demo/CLAUDE.md"
before="$(snapshot "$tmp/r25/worlds/demo")"
expect_exit 1 'CONFLICT: .pi exists and is not a symlink' "$tmp/r25" --apply --no-sync demo
grep -qF 'CONFLICT: CLAUDE.md differs from templates/world-project/CLAUDE.md' "$tmp/out.txt" || fail 'did not report every conflict'
[ "$before" = "$(snapshot "$tmp/r25/worlds/demo")" ] || fail 'case 25 changed files'

# 26. 行き先の違う symlink は 1（N-16）
new_root "$tmp/r26"
run "$tmp/r26" --no-sync demo >/dev/null
rm "$tmp/r26/worlds/demo/.pi" && ln -s ../other "$tmp/r26/worlds/demo/.pi"
before="$(snapshot "$tmp/r26/worlds/demo")"
expect_exit 1 'CONFLICT: .pi points to ../other, expected ../../.pi' "$tmp/r26" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r26/worlds/demo")" ] || fail 'case 26 changed files'

# 27. 行き先が存在しないことになる symlink は 1（N-16）
new_root "$tmp/r27"
run "$tmp/r27" --no-sync demo >/dev/null
rm "$tmp/r27/worlds/demo/.claude/settings.json" "$tmp/r27/.claude/settings.json"
before="$(snapshot "$tmp/r27/worlds/demo")"
expect_exit 1 'CONFLICT: .claude/settings.json would point to missing ../../../.claude/settings.json' "$tmp/r27" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r27/worlds/demo")" ] || fail 'case 27 changed files'

# 28. ルートの .claude/settings.json が無ければ、新規作成は resoloop init を呼ばず何も作らずに 3（N-16）
new_root "$tmp/r28"
rm "$tmp/r28/.claude/settings.json"
: > "$MOCK_LOG"
expect_exit 3 '.claude/settings.json is missing at the repository root' "$tmp/r28" --no-sync demo
[ ! -e "$tmp/r28/worlds/demo" ] || fail 'created the project although the root .claude/settings.json is missing'
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop although the root .claude/settings.json is missing'

# 29. 名前に | を含むスキルディレクトリにも正しくリンクを張る（N-16）
new_root "$tmp/r29"
run "$tmp/r29" --no-sync demo >/dev/null
mkdir -p "$tmp/r29/worlds/demo/.agents/skills/a|b" && printf -- '---\nname: ab\n---\n' > "$tmp/r29/worlds/demo/.agents/skills/a|b/SKILL.md"
expect_exit 0 'DONE: demo' "$tmp/r29" --apply --no-sync demo
[ "$(readlink "$tmp/r29/worlds/demo/.claude/skills/a|b")" = '../../.agents/skills/a|b' ] || fail 'link for a name containing |'

# 30. 途中のディレクトリがディレクトリへの symlink でも 1 を返し、リンク先にも手元にも書かない（N-16）
new_root "$tmp/r30"
run "$tmp/r30" --no-sync demo >/dev/null
mv "$tmp/r30/worlds/demo/.claude" "$tmp/r30/claude-elsewhere" && ln -s ../../claude-elsewhere "$tmp/r30/worlds/demo/.claude"
rm "$tmp/r30/claude-elsewhere/settings.json"
before="$(snapshot "$tmp/r30/worlds/demo")"
before_target="$(snapshot "$tmp/r30/claude-elsewhere")"
expect_exit 1 'CONFLICT: .claude is not a directory' "$tmp/r30" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r30/worlds/demo")" ] || fail 'case 30 changed files'
[ "$before_target" = "$(snapshot "$tmp/r30/claude-elsewhere")" ] || fail 'case 30 wrote through the .claude symlink'

# 31. 既存プロジェクトの AGENTS.md が壊れた symlink なら 3。resoloop init を勧めず、何も変更しない（N-23）
new_root "$tmp/r31"
run "$tmp/r31" --no-sync demo >/dev/null
rm "$tmp/r31/worlds/demo/AGENTS.md" && ln -s ../missing-agents.md "$tmp/r31/worlds/demo/AGENTS.md"
before="$(snapshot "$tmp/r31/worlds/demo")"
expect_exit 3 'demo/AGENTS.md is a broken symlink' "$tmp/r31" --apply --no-sync demo
if grep -qF 'run resoloop init first' "$tmp/out.txt"; then fail 'case 31 still suggests resoloop init'; fi
grep -qF 'instead of running resoloop init in an existing project' "$tmp/out.txt" || fail 'case 31 does not warn against resoloop init'
[ "$before" = "$(snapshot "$tmp/r31/worlds/demo")" ] || fail 'case 31 changed files'

# 32. 既存プロジェクトに AGENTS.md が無くても同じく 3 で、init を勧めない（N-23）
new_root "$tmp/r32"
run "$tmp/r32" --no-sync demo >/dev/null
rm "$tmp/r32/worlds/demo/AGENTS.md"
before="$(snapshot "$tmp/r32/worlds/demo")"
expect_exit 3 'demo/AGENTS.md is missing or not a regular file' "$tmp/r32" --apply --no-sync demo
if grep -qF 'run resoloop init first' "$tmp/out.txt"; then fail 'case 32 still suggests resoloop init'; fi
grep -qF 'instead of running resoloop init in an existing project' "$tmp/out.txt" || fail 'case 32 does not warn against resoloop init'
[ "$before" = "$(snapshot "$tmp/r32/worlds/demo")" ] || fail 'case 32 changed files'

# 33. 新規作成で resoloop init が AGENTS.md を作らなければ 3（init をもう一度実行させない）
new_root "$tmp/r33"
mkdir -p "$tmp/init-noagents"
cat > "$tmp/init-noagents/resoloop" <<EOF
#!/bin/bash
"$tmp/mockbin/resoloop" "\$@" || exit
[ "\$1" != init ] || rm -f "\$2/AGENTS.md"
EOF
chmod +x "$tmp/init-noagents/resoloop"
PATH="$tmp/init-noagents:$PATH" expect_exit 3 'resoloop init did not create demo/AGENTS.md' "$tmp/r33" --no-sync demo

# 34. worlds/ が実ディレクトリでない（通常ファイル・symlink）なら、何も作らずに 3。
#     symlink の worlds/ は、プロジェクトの相対リンクがリンク先基準で解決されてルートに届かないため拒否する
new_root "$tmp/r34"
printf 'x\n' > "$tmp/r34/worlds"
: > "$MOCK_LOG"
expect_exit 3 'not a real directory' "$tmp/r34" --no-sync demo
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop although worlds/ is not a directory'
rm "$tmp/r34/worlds"
mkdir -p "$tmp/elsewhere"
ln -s "$tmp/elsewhere" "$tmp/r34/worlds"
expect_exit 3 'not a real directory' "$tmp/r34" --no-sync demo
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop although worlds/ is a symlink'

# 35. ルート直下の従来位置にあるプロジェクトは --apply で雛形を補える。リンクは深さ 1 の行き先
new_root "$tmp/r35"
MOCK_LOG="$MOCK_LOG" "$tmp/mockbin/resoloop" init "$tmp/r35/akichi"
expect_exit 0 'DONE: akichi' "$tmp/r35" --apply --no-sync akichi
p="$tmp/r35/akichi"
expect_wrapper "$p"
for link in '.claude/skills/resonite-build|../../.agents/skills/resonite-build' \
            '.claude/settings.json|../../.claude/settings.json' '.pi|../.pi' \
            '.agents/sp-implementer.md|../../.agents/sp-implementer.md'; do
  rel="${link%%|*}" target="${link#*|}"
  [ "$(readlink "$p/$rel")" = "$target" ] || fail "link $rel"
  [ -e "$p/$rel" ] || fail "dangling $rel"
done

# 35b. worlds/ が実ディレクトリでなくても、従来位置のプロジェクトへの --apply は worlds/ を触らないので通る
new_root "$tmp/r35b"
MOCK_LOG="$MOCK_LOG" "$tmp/mockbin/resoloop" init "$tmp/r35b/akichi"
printf 'x\n' > "$tmp/r35b/worlds"
expect_exit 0 'DONE: akichi' "$tmp/r35b" --apply --no-sync akichi
[ -e "$tmp/r35b/akichi/.pi" ] || fail 'did not link .pi for the legacy project'

# 36. worlds/<name> とルート直下 <name> の両方がある --apply は、対象が決められないので 2 で何も変更しない
new_root "$tmp/r36"
run "$tmp/r36" --no-sync demo >/dev/null
MOCK_LOG="$MOCK_LOG" "$tmp/mockbin/resoloop" init "$tmp/r36/demo"
before="$(snapshot "$tmp/r36/worlds/demo")"
expect_exit 2 'exists both' "$tmp/r36" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r36/worlds/demo")" ] || fail 'case 36 changed files'

# 37. --apply も欠落・null の設定を補い、他の JSON 値と元の mode を保つ。
new_root "$tmp/r37"
for state in missing null; do
  p="$tmp/r37/worlds/$state"
  "$tmp/mockbin/resoloop" init "$p"
  if [ "$state" = missing ]; then
    printf '{"custom":{"nested":[1,true,"a b"]},"port":8765}\n' > "$p/.resoloop.json"
  else
    printf '{"blenderExecutable":null,"custom":{"nested":[1,true,"a b"]},"port":8765}\n' > "$p/.resoloop.json"
  fi
  chmod 0640 "$p/.resoloop.json"
  expect_exit 0 'DONE:' "$tmp/r37" --apply --no-sync "$state"
  expect_wrapper "$p"
  jq -e '.custom == {"nested":[1,true,"a b"]} and .port == 8765' "$p/.resoloop.json" >/dev/null || fail 'other JSON keys changed'
  [ "$(stat -c %a "$p/.resoloop.json")" = 640 ] || fail 'JSON mode changed'
  before="$(snapshot "$p")"
  expect_exit 0 'DONE:' "$tmp/r37" --apply --no-sync "$state"
  [ "$before" = "$(snapshot "$p")" ] || fail "second apply changed $state"
done

# 38. 現在のラッパー値が設定済みなら、整形し直さずバイト列と mode も保持する。
p="$tmp/r37/worlds/missing"
printf '{ "blenderExecutable" : "%s", "custom" : 1 }\n\n' "$p/.resoloop/blender-system-python" > "$p/.resoloop.json"
before="$(snapshot "$p")"
expect_exit 0 'DONE:' "$tmp/r37" --apply --no-sync missing
[ "$before" = "$(snapshot "$p")" ] || fail 'rewrote the current wrapper setting'

# 39. カスタム値・古い絶対パス・空文字を利用者指定として保持し、案内する。
for value in '/custom/blender' '/previous/world/.resoloop/blender-system-python' ''; do
  jq -n --arg value "$value" '{blenderExecutable:$value, custom:42}' > "$p/.resoloop.json"
  before="$(snapshot "$p")"
  expect_exit 0 'kept: .resoloop.json (blenderExecutable' "$tmp/r37" --apply --no-sync missing
  [ "$before" = "$(snapshot "$p")" ] || fail "overwrote user setting '$value'"
done

# 40. root ごと移動したプロジェクトでも、古い絶対値は推測で変更しない。
new_root "$tmp/r40"
run "$tmp/r40" --no-sync demo >/dev/null
mv "$tmp/r40" "$tmp/r40-moved"
p="$tmp/r40-moved/worlds/demo"
before="$(snapshot "$p")"
expect_exit 0 'kept: .resoloop.json (blenderExecutable' "$tmp/r40-moved" --apply --no-sync demo
[ "$before" = "$(snapshot "$p")" ] || fail 'changed the old path after moving the root'

# 41. JSON 構文・文書数・root・値型の競合は exit 1、追加や +x の予定も含め無変更。
new_root "$tmp/r41"
run "$tmp/r41" --no-sync demo >/dev/null
p="$tmp/r41/worlds/demo"
chmod 0640 "$p/.resoloop/blender-system-python"
rm "$p/CLAUDE.md"
for json in '{broken' '{} {}' '[]' 'null' '' '{"blenderExecutable":1}' '{"blenderExecutable":false}' '{"blenderExecutable":{}}' '{"blenderExecutable":[]}'; do
  printf '%s\n' "$json" > "$p/.resoloop.json"
  before="$(snapshot "$p")"
  expect_exit 1 'CONFLICT: .resoloop.json' "$tmp/r41" --apply --no-sync demo
  [ "$before" = "$(snapshot "$p")" ] || fail "invalid JSON changed files: $json"
done

# 42. JSON の symlink はリンク先へ書かず、壊れたリンクも同じく競合にする。
new_root "$tmp/r42"
run "$tmp/r42" --no-sync demo >/dev/null
p="$tmp/r42/worlds/demo"
printf '{"blenderExecutable":null}\n' > "$tmp/r42/shared.json"
chmod 0640 "$p/.resoloop/blender-system-python"
rm "$p/.resoloop.json"
for target in '../../shared.json' '../../missing.json'; do
  ln -s "$target" "$p/.resoloop.json"
  # root 全体でプロジェクトと実リンク先を一度ずつ検査する。
  before="$(snapshot "$tmp/r42")"
  expect_exit 1 'CONFLICT: .resoloop.json' "$tmp/r42" --apply --no-sync demo
  [ "$before" = "$(snapshot "$tmp/r42")" ] || fail 'JSON symlink changed project or target'
  rm "$p/.resoloop.json"
done
mkdir "$p/.resoloop.json"
before="$(snapshot "$p")"
expect_exit 1 'CONFLICT: .resoloop.json' "$tmp/r42" --apply --no-sync demo
[ "$before" = "$(snapshot "$p")" ] || fail 'JSON directory changed project'

# 43. wrapper の symlink・内容差・非通常ファイル・親の symlink/通常ファイルを拒否する。
for kind in link broken different directory parent-link parent-file; do
  r="$tmp/r43-$kind"
  new_root "$r"
  run "$r" --no-sync demo >/dev/null
  p="$r/worlds/demo"
  printf '{"blenderExecutable":null}\n' > "$p/.resoloop.json"
  case "$kind" in
    link|broken)
      mv "$p/.resoloop/blender-system-python" "$r/shared-wrapper"
      chmod 0640 "$r/shared-wrapper"
      target="$r/shared-wrapper"
      [ "$kind" != broken ] || target="$r/missing-wrapper"
      ln -s "$target" "$p/.resoloop/blender-system-python"
      ;;
    different) printf '# user wrapper\n' > "$p/.resoloop/blender-system-python" ;;
    directory) rm "$p/.resoloop/blender-system-python"; mkdir "$p/.resoloop/blender-system-python" ;;
    parent-link)
      mv "$p/.resoloop" "$r/shared-resoloop"
      chmod 0640 "$r/shared-resoloop/blender-system-python"
      ln -s "$r/shared-resoloop" "$p/.resoloop"
      ;;
    parent-file) rm -r "$p/.resoloop"; printf 'not a directory\n' > "$p/.resoloop" ;;
  esac
  before="$(snapshot "$r")"
  expect_exit 1 'CONFLICT: .resoloop' "$r" --apply --no-sync demo
  [ "$before" = "$(snapshot "$r")" ] || fail "wrapper $kind changed project or target"
done

# 44. 同じ内容なら非実行 wrapper を +x にするが、別の競合があれば mode/JSON とも触らない。
new_root "$tmp/r44"
run "$tmp/r44" --no-sync demo >/dev/null
p="$tmp/r44/worlds/demo"
chmod 0644 "$p/.resoloop/blender-system-python"
printf '{"blenderExecutable":null}\n' > "$p/.resoloop.json"
printf 'other\n' > "$p/CLAUDE.md"
before="$(snapshot "$p")"
expect_exit 1 'CONFLICT: CLAUDE.md' "$tmp/r44" --apply --no-sync demo
[ "$before" = "$(snapshot "$p")" ] || fail 'other conflict changed wrapper mode or JSON'
printf '@AGENTS.md\n' > "$p/CLAUDE.md"
expect_exit 0 'DONE:' "$tmp/r44" --apply --no-sync demo
expect_wrapper "$p"
[ "$(stat -c %a "$p/.resoloop/blender-system-python")" = 755 ] || fail 'wrapper mode not repaired'
before="$(snapshot "$p")"
expect_exit 0 'DONE:' "$tmp/r44" --apply --no-sync demo
[ "$before" = "$(snapshot "$p")" ] || fail 'second apply after chmod changed files'

# 45. jq 不在なら init より前に exit 3。既存プロジェクトも無変更である。
new_root "$tmp/r45"
run "$tmp/r45" --no-sync existing >/dev/null
no_jq="$(path_without "$tmp/no-jq" jq)"
if PATH="$no_jq" command -v jq >/dev/null 2>&1; then fail 'jq visible on PATH without jq'; fi
before="$(snapshot "$tmp/r45")"
: > "$MOCK_LOG"
PATH="$no_jq" expect_exit 3 'jq not found' "$tmp/r45" --no-sync demo
PATH="$no_jq" expect_exit 3 'jq not found' "$tmp/r45" --apply --no-sync existing
[ "$before" = "$(snapshot "$tmp/r45")" ] || fail 'jq absence changed files'
[ ! -s "$MOCK_LOG" ] || fail 'jq absence ran init'

# 46. --no-sync なら uv 不在でも jq による設定を含めて成功する。
new_root "$tmp/r46"
PATH="$tmp/resoloop-only:$no_uv" expect_exit 0 'DONE: demo' "$tmp/r46" --no-sync demo
expect_wrapper "$tmp/r46/worlds/demo"

# 47. root の空白・引用符は --arg で JSON の絶対値へ安全に渡す。
r="$tmp/root with \"double\" and 'single' quotes"
new_root "$r"
expect_exit 0 'DONE: demo' "$r" --no-sync demo
expect_wrapper "$r/worlds/demo"
before="$(snapshot "$r/worlds/demo")"
expect_exit 0 'DONE: demo' "$r" --apply --no-sync demo
[ "$before" = "$(snapshot "$r/worlds/demo")" ] || fail 'quoted path second apply changed files'

printf 'PASS: new-world script behaves as specified\n'
