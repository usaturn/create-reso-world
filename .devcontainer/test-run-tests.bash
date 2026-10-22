#!/bin/bash
# .devcontainer/run-tests.bash の終了コード、GIT_* の隔離と既定の対象を検査する。仕様 7.2・9.2 節
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

# 4. 引数なしの既定の対象は .devcontainer/ と tests/scripts/ の両方を含み、補助の tests/scripts/lib/ を含まない。
#    片方が落ちると、そのテストが 1 本も走らないまま PASS を報告する（ファイル名と件数は照合しない）
listed="$(bash "$runner" --list)"
grep -q '^\.devcontainer/' <<<"$listed" || fail 'the default list lacks .devcontainer/'
grep -q '^tests/scripts/' <<<"$listed" || fail 'the default list lacks tests/scripts/'
if grep -q '^tests/scripts/lib/' <<<"$listed"; then fail 'the default list includes a helper under tests/scripts/lib/'; fi

printf 'PASS: run-tests.bash reports failures, isolates GIT_* and lists both test roots\n'
