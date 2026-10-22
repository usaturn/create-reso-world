#!/bin/bash
# .devcontainer/run-tests.bash の終了コードと GIT_* の隔離を検査する。仕様 7.2・9.2 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runner="$root/.devcontainer/run-tests.bash"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# 3 の場合の git が、外から渡された GIT_* のリポジトリを書き換えないように（直接実行したときも。#166）
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')

# 1. 失敗したテストがあれば 1 を返す（失敗を成功と報告すると、壊れた bash テストを見逃す）
printf '#!/bin/bash\ntrue\n' > "$tmp/pass.bash"
printf '#!/bin/bash\nexit 3\n' > "$tmp/fail.bash"
code=0
bash "$runner" "$tmp/pass.bash" "$tmp/fail.bash" > "$tmp/out" 2>&1 || code=$?
[ "$code" -eq 1 ] || fail "expected exit 1, got $code"

# 2. すべて通れば 0 を返す（上の拒否に対する正例）
bash "$runner" "$tmp/pass.bash" "$tmp/pass.bash" > "$tmp/out" 2>&1 || fail 'a passing run returned non-zero'

# 3. 外から渡された GIT_* をテストに渡さない。linked worktree の git rebase --exec は GIT_DIR を export するので、
#    残すと一時リポジトリを作るテストの git init・git -C が、そのリポジトリの設定を書き換える（#166）
git init -q "$tmp/victim"
cp "$tmp/victim/.git/config" "$tmp/victim-config"
printf '#!/bin/bash\nset -e\ngit init -q "%s/fixture"\ngit -C "%s/fixture" config user.name Test\n' "$tmp" "$tmp" > "$tmp/git.bash"
GIT_DIR="$tmp/victim/.git" bash "$runner" "$tmp/git.bash" > "$tmp/out" 2>&1 || fail "the git test failed: $(cat "$tmp/out")"
cmp -s "$tmp/victim/.git/config" "$tmp/victim-config" || fail 'a test changed the repository named by the inherited GIT_DIR'
[ -d "$tmp/fixture/.git" ] || fail 'the test did not get its own repository'

printf 'PASS: run-tests.bash reports failures and isolates GIT_*\n'
