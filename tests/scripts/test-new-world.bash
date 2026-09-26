#!/bin/bash
# scripts/new-world.sh の作成・適用・冪等性・食い違いの検出を、一時リポジトリとモックの resoloop / uv で検査する
set -euo pipefail
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
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

# 7. CLAUDE.md が雛形と違えば 1
new_root "$tmp/r7"
run "$tmp/r7" --no-sync demo >/dev/null
printf 'other\n' > "$tmp/r7/demo/CLAUDE.md"
expect_exit 1 'CONFLICT: CLAUDE.md differs from templates/world-project/CLAUDE.md' "$tmp/r7" --apply --no-sync demo

# 8. 対応する .agents/skills の無い .claude/skills のリンクは 1
new_root "$tmp/r8"
run "$tmp/r8" --no-sync demo >/dev/null
ln -s ../../.agents/skills/stale "$tmp/r8/demo/.claude/skills/stale"
expect_exit 1 'CONFLICT: .claude/skills/stale has no matching .agents/skills/stale' "$tmp/r8" --apply --no-sync demo

# 9. resoloop プロジェクトでないディレクトリへの --apply は 3
new_root "$tmp/r9"
mkdir "$tmp/r9/plain"
expect_exit 3 'not a resoloop project' "$tmp/r9" --apply --no-sync plain

# 10. resoloop が無ければ新規作成は 3
new_root "$tmp/r10"
if PATH=/usr/local/bin:/usr/bin:/bin command -v resoloop >/dev/null 2>&1; then fail 'resoloop visible on the reduced PATH'; fi
PATH=/usr/local/bin:/usr/bin:/bin expect_exit 3 'resoloop not found' "$tmp/r10" --no-sync demo

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
if PATH=/usr/bin:/bin command -v uv >/dev/null 2>&1; then fail 'uv visible on the reduced PATH'; fi
: > "$MOCK_LOG"
PATH="$tmp/resoloop-only:/usr/bin:/bin" expect_exit 3 'uv not found' "$tmp/r15" demo
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

printf 'PASS: new-world script behaves as specified\n'
