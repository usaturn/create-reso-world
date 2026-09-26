#!/bin/bash
# リポジトリのレイアウト検査。仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 9.1 節
# 使い方: scripts/check-layout.sh [--root DIR]
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

# 2. 追跡中の symlink がすべて解決できる
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

# 3. 追跡中かつ ignore 対象は既知の例外だけ
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
check_skill_links() {
  local prefix="$1"
  local agents="${prefix}.agents/skills/" claude="${prefix}.claude/skills/"
  local -A dirs=() links=()
  local problems=() path record meta mode rest name target
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
    rest="${path#"$claude"}"
    name="${rest%%/*}"
    [ -z "${links[$name]+x}" ] || continue
    links["$name"]=1
    if [ "$mode" != 120000 ] || [ "$rest" != "$name" ]; then
      problems+=("${claude}${name} is not a symlink")
      continue
    fi
    target="$(readlink "$path" 2>/dev/null || true)"
    [ "$target" = "../../.agents/skills/$name" ] || problems+=("${claude}${name} has unexpected target ${target:-<none>}")
    [ -n "${dirs[$name]+x}" ] || problems+=("${claude}${name} has no matching ${agents}${name}")
  done < "$tmp_list"
  for name in "${!dirs[@]}"; do
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
  local hits=() record meta path mode re='(^|/)\.(agents|claude)/skills/'
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
    [ "$mode" != 120000 ] || continue
    [[ "$path" =~ $re ]] || continue
    [ -s "$path" ] || hits+=("empty tracked file: $path")
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
  local p="$1" problems=() f link target sp
  for f in AGENTS.md CLAUDE.md .resoloop.json .resoloop/.gitignore pyproject.toml uv.lock \
           .agents/skills/.resoloop-bundled.json flux/resoloop.flux.json; do
    git ls-files --error-unmatch -- "$p/$f" >/dev/null 2>&1 || problems+=("missing tracked file $f")
  done
  [ "$(cat "$p/CLAUDE.md" 2>/dev/null)" = '@AGENTS.md' ] || problems+=("CLAUDE.md must be exactly @AGENTS.md")
  grep -qxF '## このプロジェクト固有' "$p/AGENTS.md" 2>/dev/null || problems+=("AGENTS.md lacks ## このプロジェクト固有")
  grep -qxF 'cache/' "$p/.resoloop/.gitignore" 2>/dev/null || problems+=(".resoloop/.gitignore lacks cache/")
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
    if [ "$(git ls-files -s -- "$p/$f" | cut -d' ' -f1)" != 120000 ] || [ "$(readlink "$p/$f" 2>/dev/null)" != "$target" ]; then
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

# 7. resoloop が使える環境では resoloop skills sync --check が各プロジェクトで成功する
check_resoloop_skills() {
  local p
  if ! command -v resoloop >/dev/null 2>&1; then
    printf 'skip: resoloop not found (skills sync check)\n'
    return
  fi
  for p in ${projects[@]+"${projects[@]}"}; do
    if resoloop skills sync "$p" --check >/dev/null 2>&1; then
      ok "resoloop skills sync --check ($p)"
    else
      fail "resoloop skills sync --check failed for $p"
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
