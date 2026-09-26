#!/bin/bash
# scripts/check-layout.sh が通過・失敗を正しく判定することを一時リポジトリで検査する
set -euo pipefail
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
  local dir="$1" needle="$2" out="$tmp/out.txt"
  if bash "$checker" --root "$dir" > "$out" 2>&1; then
    printf 'FAIL: %s was accepted\n' "$dir" >&2; exit 1
  fi
  grep -qF "$needle" "$out" || { printf 'FAIL: expected message %q for %s\n' "$needle" "$dir" >&2; cat "$out" >&2; exit 1; }
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
if bash "$checker" --bogus > /dev/null 2>&1; then
  printf 'FAIL: bogus argument accepted\n' >&2; exit 1
fi

# 6. このリポジトリ自身が通過する
bash "$checker" | grep -qF 'PASS: check-layout'

printf 'PASS: check-layout script behaves as specified\n'
