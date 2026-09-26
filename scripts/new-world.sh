#!/bin/bash
# ワールドのプロジェクトを作る、または既存プロジェクトに雛形の不足分を適用する。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 4.2・4.3 節
# 使い方: scripts/new-world.sh [--apply] [--no-sync] [--root DIR] <name>
# 終了コード:
#   0 成功
#   1 既存ファイルとの食い違いあり。雛形の変更は何もしない（新規作成では resoloop init が作ったディレクトリだけが残り、その旨を表示する）
#   2 使い方の誤り（git に無視される名前を含む）。何も変更しない
#   3 前提不足。uv（同期ありのとき）・resoloop・ルートの共有物（.claude/settings.json、.pi）の欠落は何かを作る前に検出する。
#     resoloop init の失敗や init 後の生成物の不足では init が作ったものが残る。uv sync の失敗では雛形の適用は済んでおり、その旨を表示する
set -euo pipefail

usage() {
  printf 'usage: %s [--apply] [--no-sync] [--root DIR] <name>\n' "${BASH_SOURCE[0]}" >&2
  exit 2
}
die() { printf 'ERROR: %s\n' "$2" >&2; exit "$1"; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
apply=0 sync=1 root="" name="" name_given=0
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) apply=1; shift ;;
    --no-sync) sync=0; shift ;;
    --root)
      [ $# -ge 2 ] || usage
      root="$(git -C "$2" rev-parse --show-toplevel 2>/dev/null)" || usage
      shift 2
      ;;
    -*) usage ;;
    *) [ "$name_given" -eq 0 ] || usage; name="$1"; name_given=1; shift ;;
  esac
done
[ "$name_given" -eq 1 ] || usage
name_re='^[A-Za-z0-9]([A-Za-z0-9_-]*[A-Za-z0-9])?$'
[[ "$name" =~ $name_re ]] || die 2 "invalid project name '$name' (use letters, digits, '-' and '_'; start and end with a letter or digit)"
[ -n "$root" ] || root="$(git -C "$script_dir" rev-parse --show-toplevel)"
# ルートの .gitignore（や利用者の除外設定）で無視される名前のプロジェクトは、git からも check-layout からも見えない
if git -C "$root" check-ignore -q -- "$name/.resoloop.json" 2>/dev/null; then
  die 2 "'$name' is ignored by git in $root (root .gitignore or your excludes); choose another name"
fi
tmpl="$root/templates/world-project"
[ -d "$tmpl" ] || die 3 "template directory not found: $tmpl"
proj="$root/$name"

if [ -e "$proj" ] || [ -L "$proj" ]; then
  [ "$apply" -eq 1 ] || die 2 "$name already exists; use --apply to add the missing scaffold"
else
  [ "$apply" -eq 0 ] || die 2 "$name does not exist; drop --apply to create it"
fi
# 何かを作る前に前提を確かめる
if [ "$sync" -eq 1 ]; then
  command -v uv >/dev/null 2>&1 || die 3 "uv not found; install it or pass --no-sync"
fi
initialized=0
if [ "$apply" -eq 0 ]; then
  command -v resoloop >/dev/null 2>&1 || die 3 "resoloop not found; install it before creating a project"
  for shared in .claude/settings.json .pi; do
    [ -e "$root/$shared" ] || die 3 "$shared is missing at the repository root ($root/$shared); the new project links to it"
  done
  resoloop init "$proj" --json >/dev/null || die 3 "resoloop init failed for $name"
  initialized=1
fi
[ -f "$proj/.resoloop.json" ] || die 3 "$name is not a resoloop project (.resoloop.json is missing)"
if [ ! -f "$proj/AGENTS.md" ]; then
  # 既存プロジェクトの中で resoloop init を実行すると content/main.json やスキルを作り直すので、init は勧めない
  [ "$apply" -eq 1 ] || die 3 "resoloop init did not create $name/AGENTS.md"
  if [ -L "$proj/AGENTS.md" ] && [ ! -e "$proj/AGENTS.md" ]; then
    what='is a broken symlink'
  else
    what='is missing or not a regular file'
  fi
  die 3 "$name/AGENTS.md $what; restore the project's AGENTS.md (for example with git restore) instead of running resoloop init in an existing project"
fi

render() { sed -e "s/{{name}}/$name/g" "$1"; }
# リンクが要る .agents/skills 直下のディレクトリ: ファイルを 1 つ以上持つもの（SKILL.md の有無は問わない）。
# scripts/check-layout.sh の定義（追跡ファイルを 1 つ以上持つディレクトリ）と揃えている
has_files() { [ -d "$1" ] && [ -n "$(find "$1" -type f -print -quit 2>/dev/null)" ]; }

# 1 周目: 作るもの・追記するものを集め、既存ファイルとの食い違いを集める。食い違いがあれば何も変更しない
conflicts=() plan_file_rel=() plan_file_src=() plan_link_rel=() plan_link_target=() append_section=0 append_cache=0
declare -A reported_parent=()

parent_ok() {  # $1=相対パス。途中のディレクトリが symlink や通常ファイルなら食い違いに加え（1 回だけ）、1 を返す
  local parent result=0
  parent="$(dirname -- "$1")"
  while [ "$parent" != . ]; do
    if [ -L "$proj/$parent" ] || { [ -e "$proj/$parent" ] && [ ! -d "$proj/$parent" ]; }; then
      if [ -z "${reported_parent[$parent]+x}" ]; then
        conflicts+=("$parent is not a directory")
        reported_parent["$parent"]=1
      fi
      result=1
    fi
    parent="$(dirname -- "$parent")"
  done
  return "$result"
}

want_file() {  # $1=相対パス、$2=雛形、$3=既存と比べるなら 1
  local rel="$1" src="$2" compare="$3"
  parent_ok "$rel" || return 0
  if [ -L "$proj/$rel" ] || { [ -e "$proj/$rel" ] && [ ! -f "$proj/$rel" ]; }; then
    conflicts+=("$rel is not a regular file")
  elif [ -f "$proj/$rel" ]; then
    if [ "$compare" -eq 1 ] && ! diff -q <(render "$src") "$proj/$rel" >/dev/null; then
      conflicts+=("$rel differs from templates/world-project/$(basename "$src")")
    fi
  else
    plan_file_rel+=("$rel")
    plan_file_src+=("$src")
  fi
}

want_link() {  # $1=相対パス、$2=期待する行き先
  local rel="$1" target="$2" current
  parent_ok "$rel" || return 0
  if [ -L "$proj/$rel" ]; then
    current="$(readlink "$proj/$rel")"
    [ "$current" = "$target" ] || conflicts+=("$rel points to $current, expected $target")
  elif [ -e "$proj/$rel" ]; then
    conflicts+=("$rel exists and is not a symlink")
  elif [ ! -e "$(realpath -m "$(dirname "$proj/$rel")/$target")" ]; then
    conflicts+=("$rel would point to missing $target")
  else
    plan_link_rel+=("$rel")
    plan_link_target+=("$target")
  fi
}

want_file CLAUDE.md "$tmpl/CLAUDE.md" 1
want_file pyproject.toml "$tmpl/pyproject.toml" 0
if [ -L "$proj/AGENTS.md" ]; then
  conflicts+=("AGENTS.md is a symlink; refusing to append to its target")
elif ! grep -qxF '## このプロジェクト固有' "$proj/AGENTS.md"; then
  append_section=1
fi
if parent_ok .resoloop/.gitignore; then
  if [ -f "$proj/.resoloop/.gitignore" ] && [ ! -L "$proj/.resoloop/.gitignore" ]; then
    grep -qxF 'cache/' "$proj/.resoloop/.gitignore" || append_cache=1
  else
    want_file .resoloop/.gitignore "$tmpl/resoloop-gitignore" 0
  fi
fi
want_link .claude/settings.json ../../.claude/settings.json
want_link .pi ../.pi
for sp in "$root"/.agents/sp-*.md; do
  [ -f "$sp" ] || continue
  want_link ".agents/$(basename "$sp")" "../../.agents/$(basename "$sp")"
done
# 隠しエントリ（.old など）も含めて、リンクが要るディレクトリと、対応するディレクトリの無いリンクを探す
shopt -s dotglob
for d in "$proj"/.agents/skills/*/; do
  d="${d%/}"
  has_files "$d" || continue
  n="$(basename "$d")"
  want_link ".claude/skills/$n" "../../.agents/skills/$n"
done
for l in "$proj"/.claude/skills/*; do
  [ -e "$l" ] || [ -L "$l" ] || continue
  n="$(basename "$l")"
  has_files "$proj/.agents/skills/$n" || conflicts+=(".claude/skills/$n has no matching .agents/skills/$n")
done
shopt -u dotglob

if [ ${#conflicts[@]} -gt 0 ]; then
  printf 'CONFLICT: %s\n' "${conflicts[@]}" >&2
  if [ "$initialized" -eq 1 ]; then
    printf '%s was created by resoloop init and remains; no scaffold changes were applied to it\n' "$name" >&2
  else
    printf 'no changes were made to %s\n' "$name" >&2
  fi
  exit 1
fi

# 2 周目: 適用する
for i in "${!plan_file_rel[@]}"; do
  rel="${plan_file_rel[$i]}" src="${plan_file_src[$i]}"
  mkdir -p "$(dirname "$proj/$rel")"
  render "$src" > "$proj/$rel"
  printf 'created: %s\n' "$rel"
done
if [ "$append_section" -eq 1 ]; then
  # 改行で終わっていない AGENTS.md には、先に改行を足してから空行と固有節を追記する
  { [ -z "$(tail -c 1 "$proj/AGENTS.md")" ] || printf '\n'; printf '\n'; render "$tmpl/AGENTS.local.md"; } >> "$proj/AGENTS.md"
  printf 'appended: AGENTS.md (## このプロジェクト固有)\n'
fi
if [ "$append_cache" -eq 1 ]; then
  printf 'cache/\n' >> "$proj/.resoloop/.gitignore"
  printf 'appended: .resoloop/.gitignore (cache/)\n'
fi
for i in "${!plan_link_rel[@]}"; do
  rel="${plan_link_rel[$i]}" target="${plan_link_target[$i]}"
  mkdir -p "$(dirname "$proj/$rel")"
  ln -s "$target" "$proj/$rel"
  printf 'linked: %s -> %s\n' "$rel" "$target"
done

if [ "$sync" -eq 1 ]; then
  (cd "$proj" && uv sync) \
    || die 3 "uv sync failed in $name; the scaffold changes were already applied and only the sync failed (fix the cause, then run 'uv sync' in $name)"
  if ! command -v resoloop >/dev/null 2>&1; then
    printf 'skip: resoloop not found (skills sync check)\n'
  elif resoloop skills sync "$proj" --check; then
    printf 'ok: resoloop skills sync --check\n'
  else
    printf 'WARN: resoloop skills sync --check failed for %s; review the report, then run resoloop skills sync %s --update\n' "$name" "$name" >&2
  fi
fi
printf 'DONE: %s\n' "$name"
