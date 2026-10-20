#!/bin/bash
# scripts/superpowers-review-copy.sh（Python モジュールを起動するラッパー）で確認用コピーを作れることを一時リポジトリで検査する。
# 拒否・非置換・競合の検査は、モジュールを直接実行する tests/scripts/test_superpowers_review_copy.py と
# test_superpowers_context.py にある。
# 仕様: docs/superpowers/specs/2026-10-04-create-reso-world-pr16-document-lifecycle-root-cause-review-fixes-design.md 5.2 節
set -euo pipefail
# 外から渡された GIT_* を除く。linked worktree の git rebase --exec は GIT_DIR を export するので、残すと
# 直接実行したときに一時リポジトリの git init・git -C が、そのリポジトリの設定・index・ブランチを書き換える（#200）
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# ユーザの git 設定から隔離する（test-check-layout.bash と同じ）
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$root"
copier="$root/scripts/superpowers-review-copy.sh"
tmp="$(realpath "$(mktemp -d)")"
trap 'rm -rf "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
spec=docs/superpowers/specs/2026-10-03-sample-design.md
out="$tmp/out.txt"

# create-reso-world に見立てた親 checkout（tmp/ を無視する）と、文書用の worktree
parent="$tmp/parent"
git init -q "$parent"
git -C "$parent" config user.email test@example.com
git -C "$parent" config user.name test
git -C "$parent" remote add origin https://github.com/usaturn/create-reso-world.git
printf 'tmp/\n' > "$parent/.gitignore"
mkdir -p "$parent/docs/superpowers/specs"
printf '# sample v1\n' > "$parent/$spec"
git -C "$parent" add .gitignore "$spec"
git -C "$parent" commit -q -m init
doc="$tmp/doc"
git -C "$parent" worktree add -q -b docs/sample "$doc"
copy="$parent/tmp/superpowers-review/sample-doc-spec.md"

# コミット済みの正本からコピーを作り、コミット SHA とハッシュを表示する。親の status は変わらず、一時ファイルも残さない
v1="$(git -C "$doc" rev-parse HEAD)"
code=0
timeout 300 bash "$copier" --doc-root "$doc" --parent-root "$parent" --path "$spec" --name sample-doc-spec.md > "$out" 2>&1 || code=$?
[ "$code" -eq 0 ] || { cat "$out" >&2; fail "expected exit 0, got $code"; }
grep -qxF 'created: tmp/superpowers-review/sample-doc-spec.md' "$out" || { cat "$out" >&2; fail 'created line'; }
grep -qxF "source: $spec at $v1" "$out" || fail 'source line'
grep -qxF "sha256: $(sha256sum "$copy" | cut -d' ' -f1)" "$out" || fail 'sha256 line'
git -C "$doc" show "$v1:$spec" | cmp -s - "$copy" || fail "the copy differs from $spec at $v1"
[ -z "$(git -C "$parent" status --porcelain)" ] || fail 'the copy must stay ignored and unstaged'
for entry in "$parent/tmp/superpowers-review"/.*; do
  [ -e "$entry" ] || continue
  case "${entry##*/}" in .|..) ;; *) fail "temporary residue: $entry" ;; esac
done

printf 'PASS: superpowers-review-copy.sh publishes a review copy through the Python module\n'
