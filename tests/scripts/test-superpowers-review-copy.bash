#!/bin/bash
# scripts/superpowers-review-copy.sh が確認用コピーを作り、危険な状態では何も書き換えずに止まることを一時リポジトリで検査する。
# 仕様: docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-design.md 3.3・10 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# ユーザの git 設定から隔離する（test-check-layout.bash と同じ）
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$root"
copier="$root/scripts/superpowers-review-copy.sh"
tmp="$(realpath "$(mktemp -d)")"
trap 'rm -rf "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
origin=https://github.com/usaturn/create-reso-world.git
spec=docs/superpowers/specs/2026-10-03-sample-design.md
out="$tmp/out.txt"

# new_repo DIR [ORIGIN] [IGNORE]: create-reso-world に見立てた checkout を作る。既定では tmp/ を無視する
new_repo() {
  git init -q "$1"
  git -C "$1" config user.email test@example.com
  git -C "$1" config user.name test
  git -C "$1" remote add origin "${2:-$origin}"
  printf '%s\n' "${3-tmp/}" > "$1/.gitignore"
  mkdir -p "$1/docs/superpowers/specs" "$1/docs/superpowers/plans"
  printf '# sample v1\n' > "$1/$spec"
  git -C "$1" add .gitignore "$spec"
  git -C "$1" commit -q -m init
}

# run CODE NEEDLE ARGS...: 終了コードと出力の一部を確かめる。出力は $out に残す
run() {
  local expected="$1" needle="$2" code=0
  shift 2
  bash "$copier" "$@" > "$out" 2>&1 || code=$?
  [ "$code" -eq "$expected" ] || { cat "$out" >&2; fail "expected exit $expected, got $code: $*"; }
  grep -qF -- "$needle" "$out" || { cat "$out" >&2; fail "expected output '$needle': $*"; }
}

same_as() {   # same_as FILE REPO REV: FILE が REV の正本と同じバイト列である
  git -C "$2" show "$3:$spec" | cmp -s - "$1" || fail "$1 differs from $spec at $3"
}

parent="$tmp/parent"
new_repo "$parent"
doc="$tmp/doc"
git -C "$parent" worktree add -q -b docs/sample "$doc"
copy="$parent/tmp/superpowers-review/sample-doc-spec.md"
args=(--doc-root "$doc" --parent-root "$parent" --path "$spec")

# 1. コミット済みの正本からコピーを作り、コミット SHA とハッシュを表示する。親の status は変わらない
v1="$(git -C "$doc" rev-parse HEAD)"
run 0 'created: tmp/superpowers-review/sample-doc-spec.md' "${args[@]}" --name sample-doc-spec.md
grep -qxF "source: $spec at $v1" "$out" || fail 'source line'
grep -qxF "sha256: $(sha256sum "$copy" | cut -d' ' -f1)" "$out" || fail 'sha256 line'
same_as "$copy" "$doc" "$v1"
[ -z "$(git -C "$parent" status --porcelain)" ] || fail 'the copy must stay ignored and unstaged'

# 2. 同じ版をもう一度コピーしても書き換えない
run 0 'unchanged: tmp/superpowers-review/sample-doc-spec.md' "${args[@]}" --name sample-doc-spec.md

# 3. 未コミットの変更（作業ツリー、index）がある正本はコピーしない
printf '# sample dirty\n' > "$doc/$spec"
run 1 'commit it first' "${args[@]}" --name sample-doc-spec.md
git -C "$doc" add "$spec"
run 1 'commit it first' "${args[@]}" --name sample-doc-spec.md
git -C "$doc" reset -q --hard
same_as "$copy" "$doc" "$v1"

# 4. 新しい版は、確認済みの版を --replace-from で示した場合だけ差し替える
printf '# sample v2\n' > "$doc/$spec"
git -C "$doc" commit -q -am v2
v2="$(git -C "$doc" rev-parse HEAD)"
run 1 'already exists with other content' "${args[@]}" --name sample-doc-spec.md
same_as "$copy" "$doc" "$v1"
run 0 'replaced: tmp/superpowers-review/sample-doc-spec.md' "${args[@]}" --name sample-doc-spec.md --replace-from "$v1"
same_as "$copy" "$doc" "$v2"

# 5. ユーザが編集したコピーは差し替えない
printf 'user note\n' >> "$copy"
edited="$(cat "$copy")"
printf '# sample v3\n' > "$doc/$spec"
git -C "$doc" commit -q -am v3
run 1 'not replaced' "${args[@]}" --name sample-doc-spec.md --replace-from "$v2"
[ "$(cat "$copy")" = "$edited" ] || fail 'an edited copy was overwritten'

# 6. ファイル名と正本のパスの検査
run 1 'must be a short lowercase file name' "${args[@]}" --name spec.md
run 1 'must be a short lowercase file name' "${args[@]}" --name ../escape-spec.md
run 1 'but --path is a spec' "${args[@]}" --name sample-doc-plan.md
run 1 'must be docs/superpowers/specs/*.md' --doc-root "$doc" --parent-root "$parent" --path README.md --name readme-spec.md
run 1 'is not committed' --doc-root "$doc" --parent-root "$parent" --path docs/superpowers/specs/missing.md --name missing-spec.md
run 2 'usage' "${args[@]}"

# 7. コピー先が symlink のときは書かない
mkdir -p "$tmp/outside"
ln -s "$tmp/outside/target.md" "$parent/tmp/superpowers-review/link-doc-spec.md"
run 1 'is a symlink' "${args[@]}" --name link-doc-spec.md
[ ! -e "$tmp/outside/target.md" ] || fail 'wrote through a symlinked copy'

# 8. tmp/superpowers-review/ が外を指す symlink なら書かない
linked="$tmp/linked"
new_repo "$linked"
mkdir -p "$linked/tmp" "$tmp/elsewhere"
ln -s "$tmp/elsewhere" "$linked/tmp/superpowers-review"
run 1 'is a symlink' --doc-root "$linked" --parent-root "$linked" --path "$spec" --name sample-doc-spec.md
[ -z "$(ls -A "$tmp/elsewhere")" ] || fail 'wrote through a symlinked review directory'

# 9. コピー先が ignore 対象でない親には書かない
unignored="$tmp/unignored"
new_repo "$unignored" "$origin" 'nothing-ignored/'
run 1 'is not ignored' --doc-root "$unignored" --parent-root "$unignored" --path "$spec" --name sample-doc-spec.md
[ ! -e "$unignored/tmp/superpowers-review" ] || fail 'created a review directory in an unignored parent'

# 10. checkout の検査: origin、親が worktree でないこと、絶対パス、checkout のルート
foreign="$tmp/foreign"
new_repo "$foreign" https://github.com/someone/other.git
run 1 'origin is not usaturn/create-reso-world' --doc-root "$foreign" --parent-root "$parent" --path "$spec" --name foreign-doc-spec.md
run 1 'must be the main checkout' "${args[@]}" --parent-root "$doc" --name sample-doc-spec.md
run 1 'must be an absolute path' --doc-root doc --parent-root "$parent" --path "$spec" --name sample-doc-spec.md
run 1 'is not the root of its checkout' --doc-root "$doc/docs" --parent-root "$parent" --path "$spec" --name sample-doc-spec.md

printf 'PASS: superpowers-review-copy copies committed documents and refuses unsafe targets\n'
