#!/bin/bash
# scripts/check-layout.sh が通過・失敗を正しく判定することを一時リポジトリで検査する
set -euo pipefail
# GIT_CONFIG_GLOBAL=/dev/null だけでは XDG 既定の ~/.config/git/ignore が働いてしまうため、
# core.excludesFile も無効化し、システム設定も外してユーザの git 設定から隔離する
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
checker="$root/scripts/check-layout.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

new_repo() {
  git init -q "$1"
  git -C "$1" config user.email test@example.com
  git -C "$1" config user.name test
  printf 'ok\n' > "$1/README.md"
  git -C "$1" add README.md
  git -C "$1" commit -q -m init
}

expect_fail_with() {
  local dir="$1" needle="$2" out="$tmp/out.txt" code=0
  bash "$checker" --root "$dir" > "$out" 2>&1 || code=$?
  if [ "$code" -eq 0 ]; then
    printf 'FAIL: %s was accepted\n' "$dir" >&2; exit 1
  fi
  if [ "$code" -ne 1 ]; then
    printf 'FAIL: expected exit code 1 for %s, got %d\n' "$dir" "$code" >&2; cat "$out" >&2; exit 1
  fi
  grep -qF "$needle" "$out" || { printf 'FAIL: expected message %q for %s\n' "$needle" "$dir" >&2; cat "$out" >&2; exit 1; }
}

assert_exit_code() {
  local expected="$1" out="$tmp/exit-out.txt"
  shift
  local actual=0
  "$@" > "$out" 2>&1 || actual=$?
  if [ "$actual" -ne "$expected" ]; then
    printf 'FAIL: expected exit %d, got %d for: %s\n' "$expected" "$actual" "$*" >&2
    cat "$out" >&2
    exit 1
  fi
}

# 1. 何も問題の無いリポジトリは通過する
new_repo "$tmp/clean"
bash "$checker" --root "$tmp/clean" | grep -qF 'PASS: check-layout'

# 2. 追跡禁止ファイル
new_repo "$tmp/forbidden"
printf 'x\n' > "$tmp/forbidden/TNX.txt"
git -C "$tmp/forbidden" add TNX.txt && git -C "$tmp/forbidden" commit -q -m add
expect_fail_with "$tmp/forbidden" 'forbidden tracked files'

# 3. 行き先の無い追跡 symlink
new_repo "$tmp/symlink"
ln -s missing-target "$tmp/symlink/link"
git -C "$tmp/symlink" add link && git -C "$tmp/symlink" commit -q -m link
expect_fail_with "$tmp/symlink" 'dangling tracked symlinks'

# 4. 追跡中かつ ignore 対象
new_repo "$tmp/ignored"
printf 'secret.txt\n' > "$tmp/ignored/.gitignore"
printf 's\n' > "$tmp/ignored/secret.txt"
git -C "$tmp/ignored" add -f .gitignore secret.txt && git -C "$tmp/ignored" commit -q -m ignored
expect_fail_with "$tmp/ignored" 'tracked but ignored'

# 5. 不正な引数は 64
assert_exit_code 64 bash "$checker" --bogus

# 6. このリポジトリ自身が通過する
bash "$checker" | grep -qF 'PASS: check-layout'

# 7. --root が git リポジトリでないディレクトリなら 64
mkdir -p "$tmp/notgit"
assert_exit_code 64 bash "$checker" --root "$tmp/notgit"

# 8. --root が存在しないパスなら 64
assert_exit_code 64 bash "$checker" --root "$tmp/does-not-exist"

# 9. --root にリポジトリのサブディレクトリを渡しても、トップレベルの禁止ファイルを検出する
new_repo "$tmp/subdir"
mkdir -p "$tmp/subdir/nested/deep"
printf 'x\n' > "$tmp/subdir/TNX.txt"
git -C "$tmp/subdir" add TNX.txt && git -C "$tmp/subdir" commit -q -m add
expect_fail_with "$tmp/subdir/nested/deep" 'forbidden tracked files'

# 10. 非 ASCII パス配下の追跡禁止ファイルも検出する
new_repo "$tmp/nonascii-forbidden"
mkdir -p "$tmp/nonascii-forbidden/資料"
printf 'x\n' > "$tmp/nonascii-forbidden/資料/TNX.txt"
git -C "$tmp/nonascii-forbidden" add 資料/TNX.txt && git -C "$tmp/nonascii-forbidden" commit -q -m add
expect_fail_with "$tmp/nonascii-forbidden" 'forbidden tracked files'

# 11. 行き先のある非 ASCII 名の symlink は誤検知しない
new_repo "$tmp/nonascii-symlink"
printf 't\n' > "$tmp/nonascii-symlink/target"
ln -s target "$tmp/nonascii-symlink/リンク"
git -C "$tmp/nonascii-symlink" add target リンク && git -C "$tmp/nonascii-symlink" commit -q -m link
bash "$checker" --root "$tmp/nonascii-symlink" | grep -qF 'PASS: check-layout'

printf 'PASS: check-layout script behaves as specified\n'
