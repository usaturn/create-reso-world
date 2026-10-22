#!/bin/bash
# scripts/new-world.sh が既存のファイルを壊さず、失敗を成功と報告しないことを、一時リポジトリとモックの resoloop・uv で
# 検査する（守りごとに代表の 1 件）
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
script="$repo_root/scripts/new-world.sh"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# モック: resoloop init は最小の scaffold を作り、呼び出しを記録する
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
chmod +x "$tmp/mockbin/resoloop"
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

# 1. 不正な名前（パスの脱出を含む）は 2 で、何も作らない
new_root "$tmp/r1"
for bad in '' 'a b' '../x' '-x' 'x/y' '.hidden' 'demo-' 'a_'; do
  expect_exit 2 '' "$tmp/r1" --no-sync "$bad"
done
[ -z "$(ls -A "$tmp/r1" | grep -vxE 'scripts|templates|\.claude|\.pi|\.agents|\.git')" ] || fail 'invalid name created something'

# 2. 新規作成: worlds/<name> に resoloop init の後で雛形を作る
new_root "$tmp/r2"
expect_exit 0 'DONE: demo' "$tmp/r2" --no-sync demo
p="$tmp/r2/worlds/demo"
[ "$(cat "$p/CLAUDE.md")" = '@AGENTS.md' ] || fail 'CLAUDE.md content'
expect_wrapper "$p"

# 3. 既存ディレクトリに --apply 無しで実行すると 2
expect_exit 2 'use --apply' "$tmp/r2" --no-sync demo

# 4. --apply を繰り返しても何も変わらない
before="$(snapshot "$p")"
expect_exit 0 'DONE: demo' "$tmp/r2" --apply --no-sync demo
[ "$before" = "$(snapshot "$p")" ] || fail 'second --apply changed files'

# 5. ルートの .pi が無ければ、新規作成は resoloop init を呼ばず何も作らずに 3
new_root "$tmp/r5"
rm -rf "$tmp/r5/.pi"
: > "$MOCK_LOG"
expect_exit 3 '.pi is missing at the repository root' "$tmp/r5" --no-sync demo
[ ! -e "$tmp/r5/worlds/demo" ] || fail 'created the project although the root .pi is missing'
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop init although the root .pi is missing'

# 6. worlds/<name> とルート直下 <name> の両方がある --apply は、対象が決められないので 2 で何も変更しない
new_root "$tmp/r6"
run "$tmp/r6" --no-sync demo >/dev/null
MOCK_LOG="$MOCK_LOG" "$tmp/mockbin/resoloop" init "$tmp/r6/demo"
before="$(snapshot "$tmp/r6/worlds/demo")"
expect_exit 2 'exists both' "$tmp/r6" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r6/worlds/demo")" ] || fail 'case 6 changed files'

# 7. --apply も欠落・null の設定を補い、他の JSON 値と元の mode を保つ。
new_root "$tmp/r7"
for state in missing null; do
  p="$tmp/r7/worlds/$state"
  "$tmp/mockbin/resoloop" init "$p"
  if [ "$state" = missing ]; then
    printf '{"custom":{"nested":[1,true,"a b"]},"port":8765}\n' > "$p/.resoloop.json"
  else
    printf '{"blenderExecutable":null,"custom":{"nested":[1,true,"a b"]},"port":8765}\n' > "$p/.resoloop.json"
  fi
  chmod 0640 "$p/.resoloop.json"
  expect_exit 0 'DONE:' "$tmp/r7" --apply --no-sync "$state"
  expect_wrapper "$p"
  jq -e '.custom == {"nested":[1,true,"a b"]} and .port == 8765' "$p/.resoloop.json" >/dev/null || fail 'other JSON keys changed'
  [ "$(stat -c %a "$p/.resoloop.json")" = 640 ] || fail 'JSON mode changed'
done

# 8. カスタム値・古い絶対パス・空文字を利用者指定として保持し、案内する。
p="$tmp/r7/worlds/missing"
for value in '/custom/blender' '/previous/world/.resoloop/blender-system-python' ''; do
  jq -n --arg value "$value" '{blenderExecutable:$value, custom:42}' > "$p/.resoloop.json"
  before="$(snapshot "$p")"
  expect_exit 0 'kept: .resoloop.json (blenderExecutable' "$tmp/r7" --apply --no-sync missing
  [ "$before" = "$(snapshot "$p")" ] || fail "overwrote user setting '$value'"
done

# 9. JSON 構文・値型の競合は exit 1、追加や +x の予定も含め無変更。
new_root "$tmp/r9"
run "$tmp/r9" --no-sync demo >/dev/null
p="$tmp/r9/worlds/demo"
chmod 0640 "$p/.resoloop/blender-system-python"
rm "$p/CLAUDE.md"
for json in '{broken' '[]' '{"blenderExecutable":1}'; do
  printf '%s\n' "$json" > "$p/.resoloop.json"
  before="$(snapshot "$p")"
  expect_exit 1 'CONFLICT: .resoloop.json' "$tmp/r9" --apply --no-sync demo
  [ "$before" = "$(snapshot "$p")" ] || fail "invalid JSON changed files: $json"
done

# 10. JSON の symlink はリンク先へ書かず、壊れたリンクも同じく競合にする。
new_root "$tmp/r10"
run "$tmp/r10" --no-sync demo >/dev/null
p="$tmp/r10/worlds/demo"
printf '{"blenderExecutable":null}\n' > "$tmp/r10/shared.json"
chmod 0640 "$p/.resoloop/blender-system-python"
rm "$p/.resoloop.json"
for target in '../../shared.json' '../../missing.json'; do
  ln -s "$target" "$p/.resoloop.json"
  # root 全体でプロジェクトと実リンク先を一度ずつ検査する。
  before="$(snapshot "$tmp/r10")"
  expect_exit 1 'CONFLICT: .resoloop.json' "$tmp/r10" --apply --no-sync demo
  [ "$before" = "$(snapshot "$tmp/r10")" ] || fail 'JSON symlink changed project or target'
  rm "$p/.resoloop.json"
done

# 11. wrapper の symlink・内容差（利用者が書いた wrapper）は上書きせず、リンク先も変えない。
for kind in link different; do
  r="$tmp/r11-$kind"
  new_root "$r"
  run "$r" --no-sync demo >/dev/null
  p="$r/worlds/demo"
  printf '{"blenderExecutable":null}\n' > "$p/.resoloop.json"
  case "$kind" in
    link)
      mv "$p/.resoloop/blender-system-python" "$r/shared-wrapper"
      chmod 0640 "$r/shared-wrapper"
      ln -s "$r/shared-wrapper" "$p/.resoloop/blender-system-python"
      ;;
    different) printf '# user wrapper\n' > "$p/.resoloop/blender-system-python" ;;
  esac
  before="$(snapshot "$r")"
  expect_exit 1 'CONFLICT: .resoloop' "$r" --apply --no-sync demo
  [ "$before" = "$(snapshot "$r")" ] || fail "wrapper $kind changed project or target"
done

# 12. 同じ内容なら非実行 wrapper を +x にするが、別の競合があれば mode/JSON とも触らない。
new_root "$tmp/r12"
run "$tmp/r12" --no-sync demo >/dev/null
p="$tmp/r12/worlds/demo"
chmod 0644 "$p/.resoloop/blender-system-python"
printf '{"blenderExecutable":null}\n' > "$p/.resoloop.json"
printf 'other\n' > "$p/CLAUDE.md"
before="$(snapshot "$p")"
expect_exit 1 'CONFLICT: CLAUDE.md' "$tmp/r12" --apply --no-sync demo
[ "$before" = "$(snapshot "$p")" ] || fail 'other conflict changed wrapper mode or JSON'
printf '@AGENTS.md\n' > "$p/CLAUDE.md"
expect_exit 0 'DONE:' "$tmp/r12" --apply --no-sync demo
expect_wrapper "$p"
[ "$(stat -c %a "$p/.resoloop/blender-system-python")" = 755 ] || fail 'wrapper mode not repaired'

# 13〜15. symlink の先には書かない。AGENTS.md・途中のディレクトリ・worlds/ はそれぞれ別の経路で検査するので、
#     経路ごとに確かめる。リンク先はルートの外（利用者のファイル）に置く
# 13. AGENTS.md が symlink なら追記せずに 1。リンク先を書き換えない
new_root "$tmp/r13"
run "$tmp/r13" --no-sync demo >/dev/null
p="$tmp/r13/worlds/demo"
mkdir "$tmp/r13-user" && printf '# shared guide\n' > "$tmp/r13-user/AGENTS.md"
rm "$p/AGENTS.md" && ln -s "$tmp/r13-user/AGENTS.md" "$p/AGENTS.md"
before="$(snapshot "$p")"
before_target="$(snapshot "$tmp/r13-user")"
expect_exit 1 'CONFLICT: AGENTS.md is a symlink' "$tmp/r13" --apply --no-sync demo
[ "$before" = "$(snapshot "$p")" ] || fail 'case 13 changed files'
[ "$before_target" = "$(snapshot "$tmp/r13-user")" ] || fail 'wrote through the AGENTS.md symlink'

# 14. 途中のディレクトリ（.claude）がディレクトリへの symlink なら 1 を返し、リンク先にも手元にも書かない。
#     リンク先の settings.json を消し、書けば差が出るようにしておく
new_root "$tmp/r14"
run "$tmp/r14" --no-sync demo >/dev/null
p="$tmp/r14/worlds/demo"
mv "$p/.claude" "$tmp/r14-claude" && ln -s "$tmp/r14-claude" "$p/.claude"
rm "$tmp/r14-claude/settings.json"
before="$(snapshot "$p")"
before_target="$(snapshot "$tmp/r14-claude")"
expect_exit 1 'CONFLICT: .claude is not a directory' "$tmp/r14" --apply --no-sync demo
[ "$before" = "$(snapshot "$p")" ] || fail 'case 14 changed files'
[ "$before_target" = "$(snapshot "$tmp/r14-claude")" ] || fail 'wrote through the .claude symlink'

# 15. worlds/ が symlink なら、新規作成は resoloop を呼ばず何も作らずに 3。
#     プロジェクトの相対リンクがリンク先基準で解決されてルートに届かないため拒否する
new_root "$tmp/r15"
mkdir "$tmp/r15-worlds" && ln -s "$tmp/r15-worlds" "$tmp/r15/worlds"
: > "$MOCK_LOG"
expect_exit 3 'not a real directory' "$tmp/r15" --no-sync demo
[ ! -s "$MOCK_LOG" ] || fail 'ran resoloop although worlds/ is a symlink'
[ -z "$(ls -A "$tmp/r15-worlds")" ] || fail 'created the project through the worlds/ symlink'

# 16. .pi が実ディレクトリなら 1 を返し、何も変更しない（CLAUDE.md も作らない）。通すと、プロジェクトが共有の .pi を
#     読まないまま作業が進む
new_root "$tmp/r16"
run "$tmp/r16" --no-sync demo >/dev/null
rm "$tmp/r16/worlds/demo/.pi" "$tmp/r16/worlds/demo/CLAUDE.md" && mkdir "$tmp/r16/worlds/demo/.pi"
before="$(snapshot "$tmp/r16/worlds/demo")"
expect_exit 1 'CONFLICT: .pi exists and is not a symlink' "$tmp/r16" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r16/worlds/demo")" ] || fail 'case 16 changed files'

# 17. 行き先の違う symlink は 1 を返し、何も変更しない
new_root "$tmp/r17"
run "$tmp/r17" --no-sync demo >/dev/null
rm "$tmp/r17/worlds/demo/.pi" && ln -s ../other "$tmp/r17/worlds/demo/.pi"
before="$(snapshot "$tmp/r17/worlds/demo")"
expect_exit 1 'CONFLICT: .pi points to ../other, expected ../../.pi' "$tmp/r17" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r17/worlds/demo")" ] || fail 'case 17 changed files'

# 18. 同期ありで uv sync が失敗したら、成功と報告せずに 3 を返し、雛形の適用が済んでいることを伝える
new_root "$tmp/r18"
mkdir -p "$tmp/uv-fail"
printf '#!/bin/bash\nexit 1\n' > "$tmp/uv-fail/uv"
chmod +x "$tmp/uv-fail/uv"
PATH="$tmp/uv-fail:$PATH" expect_exit 3 'already applied' "$tmp/r18" demo
[ "$(cat "$tmp/r18/worlds/demo/CLAUDE.md")" = '@AGENTS.md' ] || fail 'scaffold was not applied before the failing uv sync'

# 19. 既存プロジェクトに AGENTS.md が無ければ、--apply は 3 で止まり何も変更しない。通すと、規約の本文の無い
#     固有節だけの AGENTS.md を作って成功と報告する
new_root "$tmp/r19"
run "$tmp/r19" --no-sync demo >/dev/null
rm "$tmp/r19/worlds/demo/AGENTS.md"
before="$(snapshot "$tmp/r19/worlds/demo")"
expect_exit 3 'demo/AGENTS.md is missing or not a regular file' "$tmp/r19" --apply --no-sync demo
[ "$before" = "$(snapshot "$tmp/r19/worlds/demo")" ] || fail 'case 19 changed files'

printf 'PASS: new-world script keeps existing files intact\n'
