#!/bin/bash
# .devcontainer/run-tests.bash の対象と結果の伝え方を検査する。仕様 7.2・9.2 節
# （自分自身も対象に含まれるので、ここでは引数でテストを渡すか --list だけを使い、全体の実行はしない）
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runner="$root/.devcontainer/run-tests.bash"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
# 4 番目の場合の git が、外から渡された GIT_* のリポジトリを書き換えないように（直接実行したときも。#166）
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')

# 1. 既定の対象は .devcontainer/test-*.bash と tests/scripts/*.bash のすべてで、補助の tests/scripts/lib は含まない
listed="$(bash "$runner" --list)"
expected="$(cd "$root" && printf '%s\n' .devcontainer/test-*.bash tests/scripts/*.bash)"
[ "$listed" = "$expected" ] || fail "unexpected test list:
$listed"
grep -qxF .devcontainer/test-run-tests.bash <<<"$listed" || fail 'the list lacks this test'
grep -qxF tests/scripts/test-check-layout.bash <<<"$listed" || fail 'the list lacks tests/scripts'
if grep -qF tests/scripts/lib/ <<<"$listed"; then fail 'the list includes a helper under tests/scripts/lib'; fi

# 2. 失敗したテストがあれば 1 を返し、そのテストの出力を字下げして示す。成功したテストの出力は出さない
printf '#!/bin/bash\necho quiet-output\n' > "$tmp/pass.bash"
printf '#!/bin/bash\necho broken-detail\nexit 3\n' > "$tmp/fail.bash"
code=0
bash "$runner" "$tmp/pass.bash" "$tmp/fail.bash" > "$tmp/out" 2>&1 || code=$?
[ "$code" -eq 1 ] || fail "expected exit 1, got $code"
grep -qE "^PASS $tmp/pass\.bash \([0-9]+s\)$" "$tmp/out" || fail 'no PASS line'
grep -qE "^FAIL $tmp/fail\.bash \([0-9]+s\)$" "$tmp/out" || fail 'no FAIL line'
grep -qxF '    broken-detail' "$tmp/out" || fail 'the failing output was not shown'
if grep -qF quiet-output "$tmp/out"; then fail 'the passing output was shown'; fi
grep -qxF "FAIL: 1 of 2 test(s) failed: $tmp/fail.bash" "$tmp/out" || fail 'no summary line'

# 3. すべて通れば 0 を返し、件数を示す
bash "$runner" "$tmp/pass.bash" "$tmp/pass.bash" > "$tmp/out" 2>&1 || fail 'a passing run returned non-zero'
[ "$(tail -n 1 "$tmp/out")" = 'PASS: 2 test(s)' ] || fail "unexpected summary: $(tail -n 1 "$tmp/out")"

# 4. 外から渡された GIT_* をテストに渡さない。linked worktree の git rebase --exec は GIT_DIR を export するので、
#    残すと一時リポジトリを作るテストの git init・git -C が、そのリポジトリの設定を書き換える（#166）
git init -q "$tmp/victim"
cp "$tmp/victim/.git/config" "$tmp/victim-config"
printf '#!/bin/bash\nset -e\ngit init -q "%s/fixture"\ngit -C "%s/fixture" config user.name Test\n' "$tmp" "$tmp" > "$tmp/git.bash"
GIT_DIR="$tmp/victim/.git" bash "$runner" "$tmp/git.bash" > "$tmp/out" 2>&1 || fail "the git test failed: $(cat "$tmp/out")"
cmp -s "$tmp/victim/.git/config" "$tmp/victim-config" || fail 'a test changed the repository named by the inherited GIT_DIR'
[ -d "$tmp/fixture/.git" ] || fail 'the test did not get its own repository'

printf 'PASS: run-tests.bash runs every test and reports failures\n'
