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
  if ! git ls-files -z -i -c --exclude-standard > "$tmp_list"; then
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

check_forbidden_tracked
check_symlinks_resolve
check_tracked_ignored

if [ "$failures" -gt 0 ]; then
  printf 'FAIL: check-layout (%d failure(s))\n' "$failures" >&2
  exit 1
fi
printf 'PASS: check-layout\n'
