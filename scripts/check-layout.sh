#!/bin/bash
# リポジトリのレイアウト検査。仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 9.1 節
# 使い方: scripts/check-layout.sh [--root DIR]
# 追跡の有無と mode、symlink の行き先、ファイルの中身は git の index から読む（検査 1・4・5・6）。これらの結果は
# 作業ツリーの未ステージの変更で変わらず、core.symlinks=false の checkout（symlink が通常ファイルになる）でも同じになる。
# 例外として次の 3 つは作業ツリーを読む: 検査 2（追跡中の symlink が解決できるか）、検査 3（ignore 規則は作業ツリーの
# .gitignore と .git/info/exclude から git が読む）、検査 7（resoloop が作業ツリーのプロジェクトを読む）。
set -euo pipefail

usage() {
  printf 'usage: %s [--root DIR]\n' "${BASH_SOURCE[0]}" >&2
  exit 64
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root=""
root_given=0
while [ $# -gt 0 ]; do
  case "$1" in
    --root)
      [ $# -ge 2 ] || usage
      root="$(git -C "$2" rev-parse --show-toplevel)" || usage
      root_given=1
      shift 2
      ;;
    *) usage ;;
  esac
done
# --root が無い場合だけ、スクリプト自身の位置からデフォルトのルートを求める。
# 引数解析より前に求めると、リポジトリの外にコピーしたスクリプトが --root 付きでも動かない。
if [ "$root_given" -eq 0 ]; then
  root="$(git -C "$script_dir" rev-parse --show-toplevel)"
fi
cd "$root"

failures=0
fail() { failures=$((failures + 1)); printf 'FAIL: %s\n' "$1" >&2; }
ok() { printf 'ok: %s\n' "$1"; }

# git ls-files の出力を NUL 区切りで受け渡す一時ファイル。各 check 関数が使い捨てる
tmp_list="$(mktemp)"
trap 'rm -f "$tmp_list"' EXIT
empty_blob="$(git hash-object -t blob --stdin </dev/null)"

# index（ステージ 0）にあるパスと完全に一致するエントリを "mode oid" で出力する。無ければ 1。
# パスはワイルドカードとして解釈しない。git ls-files はディレクトリの前方一致でも列挙するので、パスの一致を確かめる
index_entry() {
  local want="$1" record meta fields
  while IFS= read -r -d '' record; do
    [ "${record#*$'\t'}" = "$want" ] || continue
    meta="${record%%$'\t'*}"
    fields="${meta#* }"
    printf '%s %s\n' "${meta%% *}" "${fields%% *}"
    return 0
  done < <(git ls-files -s -z -- ":(literal)$want")
  return 1
}

# 1. 追跡してはいけないファイル（仕様 9.1）
check_forbidden_tracked() {
  local pattern='(^|/)(ATS|BTD|TNX)\.txt$|(^|/)\.claude/settings\.local\.json$|\.blend1$|\.blend2$|\.orig$|\.rej$|(^|/)__pycache__/|(^|/)\.venv/'
  if ! git ls-files -z > "$tmp_list"; then
    fail "git ls-files failed"
    return
  fi
  local hits=() path
  while IFS= read -r -d '' path; do
    [[ "$path" =~ $pattern ]] && hits+=("$path")
  done < "$tmp_list"
  if [ ${#hits[@]} -gt 0 ]; then
    fail "forbidden tracked files: ${hits[*]}"
  else
    ok "no forbidden tracked files"
  fi
}

# 2. 追跡中の symlink がすべて解決できる（作業ツリーで確かめる）
check_symlinks_resolve() {
  if ! git ls-files -s -z > "$tmp_list"; then
    fail "git ls-files -s failed"
    return
  fi
  local broken=() record meta path mode
  while IFS= read -r -d '' record; do
    meta="${record%%$'\t'*}"
    path="${record#*$'\t'}"
    mode="${meta%% *}"
    [ "$mode" = 120000 ] || continue
    [ -e "$path" ] || broken+=("$path")
  done < "$tmp_list"
  if [ ${#broken[@]} -gt 0 ]; then
    fail "dangling tracked symlinks: ${broken[*]}"
  else
    ok "tracked symlinks resolve"
  fi
}

# 3. 追跡中かつ ignore 対象は既知の例外だけ（ignore 規則は作業ツリーの .gitignore から読まれる）
check_tracked_ignored() {
  local allow='MyResoniteProject/.resoloop/tokyo-nova/pipeline.json'
  if ! git -c core.excludesFile=/dev/null ls-files -z -i -c --exclude-standard > "$tmp_list"; then
    fail "git ls-files -i failed"
    return
  fi
  local hits=() path
  while IFS= read -r -d '' path; do
    [ "$path" = "$allow" ] && continue
    hits+=("$path")
  done < "$tmp_list"
  if [ ${#hits[@]} -gt 0 ]; then
    fail "tracked but ignored: ${hits[*]}"
  else
    ok "no unexpected tracked-but-ignored files"
  fi
}

# 4. <prefix>.claude/skills の各エントリが <prefix>.agents/skills の同名ディレクトリへの symlink で、1:1 に対応する（仕様 4.2・8.1・9.1）
# 引数: 接頭辞。ルートは ""、プロジェクトは "slum02/" のように末尾に / を付ける
# リンクが要るのは、追跡ファイルを 1 つ以上持つ .agents/skills 直下のディレクトリ。SKILL.md の有無は問わない
# （ルートの references/ のように、SKILL.md を持たない共有ディレクトリにもリンクが要る）。
# scripts/new-world.sh も、ファイルを 1 つ以上持つディレクトリという同じ定義でリンクを張る。
check_skill_links() {
  local prefix="$1"
  local agents="${prefix}.agents/skills/" claude="${prefix}.claude/skills/"
  local -A dirs=() links=()
  local problems=() names=() path record meta fields mode oid rest name target
  if ! git ls-files -z -- "${prefix}.agents/skills" > "$tmp_list"; then
    fail "git ls-files failed for ${agents}"
    return
  fi
  while IFS= read -r -d '' path; do
    rest="${path#"$agents"}"
    [ "$rest" != "${rest#*/}" ] || continue   # 直下のファイル（.resoloop-bundled.json など）は対象外
    dirs["${rest%%/*}"]=1
  done < "$tmp_list"
  if ! git ls-files -s -z -- "${prefix}.claude/skills" > "$tmp_list"; then
    fail "git ls-files -s failed for ${claude}"
    return
  fi
  while IFS= read -r -d '' record; do
    meta="${record%%$'\t'*}"
    path="${record#*$'\t'}"
    mode="${meta%% *}"
    fields="${meta#* }"
    oid="${fields%% *}"
    if [ "$path" = "${claude%/}" ]; then
      problems+=("${claude%/} must be a directory, not a symlink")
      continue
    fi
    rest="${path#"$claude"}"
    name="${rest%%/*}"
    [ -z "${links[$name]+x}" ] || continue
    links["$name"]=1
    if [ "$mode" != 120000 ] || [ "$rest" != "$name" ]; then
      problems+=("${claude}${name} is not a symlink")
      continue
    fi
    target="$(git cat-file blob "$oid")"
    [ "$target" = "../../.agents/skills/$name" ] || problems+=("${claude}${name} has unexpected target ${target:-<none>}")
    [ -n "${dirs[$name]+x}" ] || problems+=("${claude}${name} has no matching ${agents}${name}")
  done < "$tmp_list"
  if [ ${#dirs[@]} -gt 0 ]; then
    mapfile -t names < <(printf '%s\n' "${!dirs[@]}" | LC_ALL=C sort)
  fi
  for name in ${names[@]+"${names[@]}"}; do
    [ -n "${links[$name]+x}" ] || problems+=("${claude%/}: missing link ${name}")
  done
  if [ ${#problems[@]} -gt 0 ]; then
    local p
    for p in "${problems[@]}"; do fail "$p"; done
  else
    ok "${claude%/} links are 1:1 with ${agents%/}"
  fi
}

# 5. 旧 .devin/skills を追跡していない。スキル配下に 0 バイトの追跡ファイルが無い（仕様 5.5・8.1・11 章）
check_skill_hygiene() {
  local hits=() record meta fields path mode re='(^|/)\.(agents|claude)/skills/'
  if ! git ls-files -z -- .devin/skills > "$tmp_list"; then
    fail "git ls-files failed for .devin/skills"
    return
  fi
  [ ! -s "$tmp_list" ] || hits+=(".devin/skills is still tracked")
  if ! git ls-files -s -z > "$tmp_list"; then
    fail "git ls-files -s failed"
    return
  fi
  while IFS= read -r -d '' record; do
    meta="${record%%$'\t'*}"
    path="${record#*$'\t'}"
    mode="${meta%% *}"
    fields="${meta#* }"
    [ "$mode" != 120000 ] || continue
    [[ "$path" =~ $re ]] || continue
    [ "${fields%% *}" != "$empty_blob" ] || hits+=("empty tracked file: $path")
  done < "$tmp_list"
  if [ ${#hits[@]} -gt 0 ]; then
    local h
    for h in "${hits[@]}"; do fail "$h"; done
  else
    ok "skill trees hold no retired or empty tracked files"
  fi
}

# 6. 各プロジェクト（.resoloop.json を追跡している直下のディレクトリ）が仕様 4.2 の標準レイアウトを満たす
projects=()
collect_projects() {
  local path
  if ! git ls-files -z -- '*/.resoloop.json' > "$tmp_list"; then
    fail "git ls-files failed for */.resoloop.json"
    return
  fi
  while IFS= read -r -d '' path; do
    [[ "$path" =~ ^[^/]+/\.resoloop\.json$ ]] || continue
    projects+=("${path%%/*}")
  done < "$tmp_list"
}

check_project() {
  local p="$1" problems=() f link target sp entry content
  for f in AGENTS.md CLAUDE.md .resoloop.json .resoloop/.gitignore pyproject.toml uv.lock \
           .agents/skills/.resoloop-bundled.json flux/resoloop.flux.json; do
    if ! entry="$(index_entry "$p/$f")"; then
      problems+=("missing tracked file $f")
    elif [ "${entry%% *}" != 100644 ] && [ "${entry%% *}" != 100755 ]; then
      problems+=("$f must be a regular file (index mode ${entry%% *})")
    fi
  done
  # 比較と検索は変数に取り込んでから行う（pipefail の下で grep -q が上流を SIGPIPE で落とすのを避ける）
  content="$(git cat-file blob ":$p/CLAUDE.md" 2>/dev/null; printf x)"
  [ "$content" = $'@AGENTS.md\nx' ] || problems+=("CLAUDE.md must be exactly @AGENTS.md")
  content="$(git cat-file blob ":$p/AGENTS.md" 2>/dev/null || true)"
  grep -qxF '## このプロジェクト固有' <<<"$content" || problems+=("AGENTS.md lacks ## このプロジェクト固有")
  content="$(git cat-file blob ":$p/.resoloop/.gitignore" 2>/dev/null || true)"
  grep -qxF 'cache/' <<<"$content" || problems+=(".resoloop/.gitignore lacks cache/")
  local links=(".claude/settings.json|../../.claude/settings.json" ".pi|../.pi")
  if ! git ls-files -z -- '.agents/sp-*.md' > "$tmp_list"; then
    fail "git ls-files failed for .agents/sp-*.md"
    return
  fi
  while IFS= read -r -d '' sp; do
    links+=(".agents/${sp##*/}|../../.agents/${sp##*/}")
  done < "$tmp_list"
  for link in "${links[@]}"; do
    f="${link%%|*}" target="${link#*|}"
    entry="$(index_entry "$p/$f" || true)"
    if [ "${entry%% *}" != 120000 ] || [ "$(git cat-file blob "${entry#* }")" != "$target" ]; then
      problems+=("$f must be a symlink to $target")
    fi
  done
  if [ ${#problems[@]} -gt 0 ]; then
    local q
    for q in "${problems[@]}"; do fail "$p: $q"; done
  else
    ok "project $p layout"
  fi
  check_skill_links "$p/"
}

# 7. resoloop が使える環境では resoloop skills sync --check が各プロジェクトで成功する。失敗したら resoloop の出力を字下げして示す（resoloop は作業ツリーを読む）
check_resoloop_skills() {
  local p out
  if ! command -v resoloop >/dev/null 2>&1; then
    printf 'skip: resoloop not found (skills sync check)\n'
    return
  fi
  for p in ${projects[@]+"${projects[@]}"}; do
    # ./ を付けて、- で始まるプロジェクト名をオプションとして読ませない
    if out="$(resoloop skills sync "./$p" --check 2>&1)"; then
      ok "resoloop skills sync --check ($p)"
    else
      fail "resoloop skills sync --check failed for $p"
      [ -z "$out" ] || printf '%s\n' "$out" | sed 's/^/    /' >&2
    fi
  done
}

check_forbidden_tracked
check_symlinks_resolve
check_tracked_ignored
check_skill_links ""
check_skill_hygiene
collect_projects
for p in ${projects[@]+"${projects[@]}"}; do check_project "$p"; done
check_resoloop_skills

if [ "$failures" -gt 0 ]; then
  printf 'FAIL: check-layout (%d failure(s))\n' "$failures" >&2
  exit 1
fi
printf 'PASS: check-layout\n'
