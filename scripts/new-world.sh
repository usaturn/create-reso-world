#!/bin/bash
# ワールドのプロジェクトを作る、または既存プロジェクトに雛形の不足分を適用する。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 4.2・4.3 節
# 使い方: scripts/new-world.sh [--apply] [--no-sync] [--root DIR] <name>
# 終了コード: 0 成功 / 1 既存ファイルとの食い違いあり（何も変更しない） / 2 使い方の誤り / 3 前提不足
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
[[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || die 2 "invalid project name '$name' (use letters, digits, '-' and '_'; start with a letter or digit)"
[ -n "$root" ] || root="$(git -C "$script_dir" rev-parse --show-toplevel)"
tmpl="$root/templates/world-project"
[ -d "$tmpl" ] || die 3 "template directory not found: $tmpl"
proj="$root/$name"

if [ -e "$proj" ] || [ -L "$proj" ]; then
  [ "$apply" -eq 1 ] || die 2 "$name already exists; use --apply to add the missing scaffold"
else
  [ "$apply" -eq 0 ] || die 2 "$name does not exist; drop --apply to create it"
  command -v resoloop >/dev/null 2>&1 || die 3 "resoloop not found; install it before creating a project"
  resoloop init "$proj" --json >/dev/null
fi
[ -f "$proj/.resoloop.json" ] || die 3 "$name is not a resoloop project (.resoloop.json is missing)"
[ -f "$proj/AGENTS.md" ] || die 3 "$name/AGENTS.md is missing; run resoloop init first"

render() { sed -e "s/{{name}}/$name/g" "$1"; }

# 1 周目: 作るもの・追記するものを集め、既存ファイルとの食い違いを集める。食い違いがあれば何も変更しない
conflicts=() plan_files=() plan_links=() append_section=0 append_cache=0

want_file() {  # $1=相対パス、$2=雛形、$3=既存と比べるなら 1
  local rel="$1" src="$2" compare="$3"
  if [ -L "$proj/$rel" ] || { [ -e "$proj/$rel" ] && [ ! -f "$proj/$rel" ]; }; then
    conflicts+=("$rel is not a regular file")
  elif [ -f "$proj/$rel" ]; then
    if [ "$compare" -eq 1 ] && ! diff -q <(render "$src") "$proj/$rel" >/dev/null; then
      conflicts+=("$rel differs from templates/world-project/$(basename "$src")")
    fi
  else
    plan_files+=("$rel|$src")
  fi
}

want_link() {  # $1=相対パス、$2=期待する行き先
  local rel="$1" target="$2" current
  if [ -L "$proj/$rel" ]; then
    current="$(readlink "$proj/$rel")"
    [ "$current" = "$target" ] || conflicts+=("$rel points to $current, expected $target")
  elif [ -e "$proj/$rel" ]; then
    conflicts+=("$rel exists and is not a symlink")
  elif [ ! -e "$(realpath -m "$(dirname "$proj/$rel")/$target")" ]; then
    conflicts+=("$rel would point to missing $target")
  else
    plan_links+=("$rel|$target")
  fi
}

want_file CLAUDE.md "$tmpl/CLAUDE.md" 1
want_file pyproject.toml "$tmpl/pyproject.toml" 0
grep -qxF '## このプロジェクト固有' "$proj/AGENTS.md" || append_section=1
if [ -f "$proj/.resoloop/.gitignore" ] && [ ! -L "$proj/.resoloop/.gitignore" ]; then
  grep -qxF 'cache/' "$proj/.resoloop/.gitignore" || append_cache=1
else
  want_file .resoloop/.gitignore "$tmpl/resoloop-gitignore" 0
fi
want_link .claude/settings.json ../../.claude/settings.json
want_link .pi ../.pi
for sp in "$root"/.agents/sp-*.md; do
  [ -f "$sp" ] || continue
  want_link ".agents/$(basename "$sp")" "../../.agents/$(basename "$sp")"
done
for f in "$proj"/.agents/skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  n="$(basename "$(dirname "$f")")"
  want_link ".claude/skills/$n" "../../.agents/skills/$n"
done
for l in "$proj"/.claude/skills/*; do
  [ -e "$l" ] || [ -L "$l" ] || continue
  n="$(basename "$l")"
  [ -f "$proj/.agents/skills/$n/SKILL.md" ] || conflicts+=(".claude/skills/$n has no matching .agents/skills/$n")
done

if [ ${#conflicts[@]} -gt 0 ]; then
  printf 'CONFLICT: %s\n' "${conflicts[@]}" >&2
  printf 'no changes were made to %s\n' "$name" >&2
  exit 1
fi

# 2 周目: 適用する
for entry in ${plan_files[@]+"${plan_files[@]}"}; do
  rel="${entry%%|*}" src="${entry#*|}"
  mkdir -p "$(dirname "$proj/$rel")"
  render "$src" > "$proj/$rel"
  printf 'created: %s\n' "$rel"
done
if [ "$append_section" -eq 1 ]; then
  { printf '\n'; render "$tmpl/AGENTS.local.md"; } >> "$proj/AGENTS.md"
  printf 'appended: AGENTS.md (## このプロジェクト固有)\n'
fi
if [ "$append_cache" -eq 1 ]; then
  printf 'cache/\n' >> "$proj/.resoloop/.gitignore"
  printf 'appended: .resoloop/.gitignore (cache/)\n'
fi
for entry in ${plan_links[@]+"${plan_links[@]}"}; do
  rel="${entry%%|*}" target="${entry#*|}"
  mkdir -p "$(dirname "$proj/$rel")"
  ln -s "$target" "$proj/$rel"
  printf 'linked: %s -> %s\n' "$rel" "$target"
done

if [ "$sync" -eq 1 ]; then
  (cd "$proj" && uv sync)
  if ! command -v resoloop >/dev/null 2>&1; then
    printf 'skip: resoloop not found (skills sync check)\n'
  elif resoloop skills sync "$proj" --check; then
    printf 'ok: resoloop skills sync --check\n'
  else
    printf 'WARN: resoloop skills sync --check failed for %s; review the report, then run resoloop skills sync %s --update\n' "$name" "$name" >&2
  fi
fi
printf 'DONE: %s\n' "$name"
