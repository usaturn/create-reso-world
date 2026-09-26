#!/bin/bash
# リポジトリのレイアウト検査。仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 9.1 節
# 使い方: scripts/check-layout.sh [--root DIR]
set -euo pipefail

usage() {
  printf 'usage: %s [--root DIR]\n' "${BASH_SOURCE[0]}" >&2
  exit 64
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(git -C "$script_dir" rev-parse --show-toplevel)"
while [ $# -gt 0 ]; do
  case "$1" in
    --root)
      [ $# -ge 2 ] || usage
      root="$(cd "$2" && pwd)"
      shift 2
      ;;
    *) usage ;;
  esac
done
cd "$root"

failures=0
fail() { failures=$((failures + 1)); printf 'FAIL: %s\n' "$1" >&2; }
ok() { printf 'ok: %s\n' "$1"; }

# 1. 追跡してはいけないファイル（仕様 9.1）
check_forbidden_tracked() {
  local pattern='(^|/)(ATS|BTD|TNX)\.txt$|(^|/)\.claude/settings\.local\.json$|\.blend1$|\.blend2$|\.orig$|\.rej$|(^|/)__pycache__/|(^|/)\.venv/'
  local hits
  hits="$(git ls-files | grep -E "$pattern" || true)"
  if [ -n "$hits" ]; then
    fail "forbidden tracked files: $(printf '%s' "$hits" | tr '\n' ' ')"
  else
    ok "no forbidden tracked files"
  fi
}

# 2. 追跡中の symlink がすべて解決できる
check_symlinks_resolve() {
  local broken=() mode _obj _stage path
  while read -r mode _obj _stage path; do
    [ "$mode" = 120000 ] || continue
    [ -e "$path" ] || broken+=("$path")
  done < <(git ls-files -s)
  if [ ${#broken[@]} -gt 0 ]; then
    fail "dangling tracked symlinks: ${broken[*]}"
  else
    ok "tracked symlinks resolve"
  fi
}

# 3. 追跡中かつ ignore 対象は既知の例外だけ
check_tracked_ignored() {
  local allow='MyResoniteProject/.resoloop/tokyo-nova/pipeline.json'
  local hits
  hits="$(git ls-files -i -c --exclude-standard | grep -vxF "$allow" || true)"
  if [ -n "$hits" ]; then
    fail "tracked but ignored: $(printf '%s' "$hits" | tr '\n' ' ')"
  else
    ok "no unexpected tracked-but-ignored files"
  fi
}

check_forbidden_tracked
check_symlinks_resolve
check_tracked_ignored

if [ "$failures" -gt 0 ]; then
  printf 'FAIL: check-layout (%d failure(s))\n' "$failures" >&2
  exit 1
fi
printf 'PASS: check-layout\n'
