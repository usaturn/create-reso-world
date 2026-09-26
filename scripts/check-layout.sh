#!/bin/bash
# リポジトリのレイアウト検査。仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 9.1 節
# 使い方: scripts/check-layout.sh [--root DIR]
# 追跡の有無と mode、symlink の行き先、ファイルの中身は git の index（ステージ 0）から読む（検査 1・4・5・6・8・9）。これらの結果は
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

# 一時ディレクトリ。list は git ls-files の出力を NUL 区切りで受け渡すファイルで、各 check 関数が使い捨てる
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
tmp_list="$tmp_dir/list"
empty_blob="$(git hash-object -t blob --stdin </dev/null)"

# git ls-files -s -z の 1 レコード（"<mode> <oid> <stage>\t<path>"）を rec_mode・rec_oid・rec_stage・rec_path に分ける
rec_mode="" rec_oid="" rec_stage="" rec_path=""
split_record() {
  local meta="${1%%$'\t'*}"
  rec_path="${1#*$'\t'}"
  rec_mode="${meta%% *}"
  meta="${meta#* }"
  rec_oid="${meta%% *}"
  rec_stage="${meta#* }"
}

# index のステージ 0 にあるパスと完全に一致するエントリを "mode oid" で出力する。無ければ 1（衝突の解決中で
# ステージ 1〜3 にしか無いパスも 1）。パスはワイルドカードとして解釈しない。git ls-files はディレクトリの
# 前方一致でも列挙するので、パスの一致を確かめる
index_entry() {
  local want="$1" record
  while IFS= read -r -d '' record; do
    split_record "$record"
    [ "$rec_path" = "$want" ] && [ "$rec_stage" = 0 ] || continue
    printf '%s %s\n' "$rec_mode" "$rec_oid"
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
  local broken=() record
  while IFS= read -r -d '' record; do
    split_record "$record"
    [ "$rec_mode" = 120000 ] || continue
    [ -e "$rec_path" ] || broken+=("$rec_path")
  done < "$tmp_list"
  if [ ${#broken[@]} -gt 0 ]; then
    fail "dangling tracked symlinks: ${broken[*]}"
  else
    ok "tracked symlinks resolve"
  fi
}

# 3. 追跡中かつ ignore 対象は既知の例外だけ（ignore 規則は作業ツリーの .gitignore と .git/info/exclude から読まれる）
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
  local problems=() names=() path record rest name target
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
    split_record "$record"
    if [ "$rec_path" = "${claude%/}" ]; then
      problems+=("${claude%/} must be a directory, not a symlink")
      continue
    fi
    rest="${rec_path#"$claude"}"
    name="${rest%%/*}"
    [ -z "${links[$name]+x}" ] || continue
    links["$name"]=1
    if [ "$rec_mode" != 120000 ] || [ "$rest" != "$name" ]; then
      problems+=("${claude}${name} is not a symlink")
      continue
    fi
    if ! target="$(git cat-file blob "$rec_oid" 2>/dev/null)"; then
      problems+=("cannot read the target of ${claude}${name} from the index")
      continue
    fi
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
  local hits=() record re='(^|/)\.(agents|claude)/skills/'
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
    split_record "$record"
    [ "$rec_mode" != 120000 ] || continue
    [[ "$rec_path" =~ $re ]] || continue
    [ "$rec_oid" != "$empty_blob" ] || hits+=("empty tracked file: $rec_path")
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

# .devcontainer/ の NAME... を index から DEST に書き出す（検査 8・9 が使う）。無いものと読めないものは
# 1 件ずつ FAIL にし、1 つでもあれば 1 を返す
extract_devcontainer_files() {
  local dest="$1" name entry bad=0
  shift
  mkdir -p "$dest"
  for name in "$@"; do
    if ! entry="$(index_entry ".devcontainer/$name")"; then
      if [ -n "$(git ls-files -u -- ":(literal).devcontainer/$name")" ]; then
        fail ".devcontainer/$name has unresolved merge conflicts"
      else
        fail "missing tracked file .devcontainer/$name"
      fi
      bad=1
    elif ! git cat-file blob "${entry#* }" > "$dest/$name" 2>/dev/null; then
      fail "cannot read .devcontainer/$name from the index"
      bad=1
    fi
  done
  return "$bad"
}

# 8. ResoLoop のロック（仕様 6.1・9.1）。.devcontainer/devcontainer.json を追跡しているリポジトリだけが対象。
# ロック・読み込み関数・devcontainer.json を index から取り出し、読み込み関数（.devcontainer/resoloop-lock.bash）で検証する
check_resoloop_lock() {
  local out line d="$tmp_dir/lock"
  if ! index_entry .devcontainer/devcontainer.json >/dev/null; then
    printf 'skip: .devcontainer/devcontainer.json is not tracked (resoloop lock check)\n'
    return
  fi
  extract_devcontainer_files "$d" resoloop.lock resoloop-lock.bash devcontainer.json || return 0
  if out="$(validate_lock "$d" 2>&1)"; then
    ok "resoloop lock ($out)"
  else
    while IFS= read -r line; do fail "$line"; done <<<"$out"
  fi
}

# 検証はサブシェルで行い、読み込み関数が設定する変数を check-layout に持ち込まない
validate_lock() (
  # shellcheck source=/dev/null
  source "$1/resoloop-lock.bash"
  resoloop_lock_load "$1/resoloop.lock" || exit 1
  if ! resoloop_lock_sdk_declared "$1/devcontainer.json" "$RESOLOOP_FORK_SDK"; then
    printf 'resoloop.lock: RESOLOOP_FORK_SDK %s is not in additionalVersions of .devcontainer/devcontainer.json\n' "$RESOLOOP_FORK_SDK"
    exit 1
  fi
  printf 'mode %s, expects %s' "$RESOLOOP_MODE" "$RESOLOOP_EXPECTED_VERSION"
)

# 9. devcontainer.json の mounts のソースと initialize.bash が作るパスが一致する（仕様 7.2・9.1）。
# .devcontainer/devcontainer.json を追跡しているリポジトリだけが対象。3 つのファイルを index から取り出し、
# .devcontainer/mounts.bash の mounts_compare で突き合わせる
check_mounts() {
  local out line d="$tmp_dir/mounts"
  if ! index_entry .devcontainer/devcontainer.json >/dev/null; then
    printf 'skip: .devcontainer/devcontainer.json is not tracked (mount check)\n'
    return
  fi
  extract_devcontainer_files "$d" mounts.bash initialize.bash devcontainer.json || return 0
  if out="$(compare_mounts "$d" 2>&1)"; then
    ok "mounts match .devcontainer/initialize.bash"
  else
    while IFS= read -r line; do fail "$line"; done <<<"$out"
  fi
}

# 比較はサブシェルで行い、mounts.bash の関数を check-layout に持ち込まない
compare_mounts() (
  # shellcheck source=/dev/null
  source "$1/mounts.bash"
  mounts_compare "$1/devcontainer.json" "$1/initialize.bash"
)

check_forbidden_tracked
check_symlinks_resolve
check_tracked_ignored
check_skill_links ""
check_skill_hygiene
collect_projects
for p in ${projects[@]+"${projects[@]}"}; do check_project "$p"; done
check_resoloop_skills
check_resoloop_lock
check_mounts

if [ "$failures" -gt 0 ]; then
  printf 'FAIL: check-layout (%d failure(s))\n' "$failures" >&2
  exit 1
fi
printf 'PASS: check-layout\n'
