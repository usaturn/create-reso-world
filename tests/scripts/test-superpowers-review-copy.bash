#!/bin/bash
# scripts/superpowers-review-copy.sh が確認用コピーを作り、危険な状態では何も書き換えずに止まることを一時リポジトリで検査する。
# 非置換コピー: 既存のコピーは決して差し替えない。新しい版は ...-r2-spec.md のような別名で公開し、--replace-from は拒否する。
# 仕様: docs/superpowers/specs/2026-10-04-create-reso-world-pr16-document-lifecycle-root-cause-review-fixes-design.md 5.2 節
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
  timeout 300 bash "$copier" "$@" > "$out" 2>&1 || code=$?
  [ "$code" -eq "$expected" ] || { cat "$out" >&2; fail "expected exit $expected, got $code: $*"; }
  grep -qF -- "$needle" "$out" || { cat "$out" >&2; fail "expected output '$needle': $*"; }
}

same_as() {   # same_as FILE REPO REV: FILE が REV の正本と同じバイト列である
  git -C "$2" show "$3:$spec" | cmp -s - "$1" || fail "$1 differs from $spec at $3"
}

# no_residue: 確認用ディレクトリに一時ファイル（ドット始まり）が残っていない
no_residue() {
  for entry in "$parent/tmp/superpowers-review"/.*; do
    [ -e "$entry" ] || continue
    case "${entry##*/}" in .|..) ;; *) fail "temporary residue: $entry" ;; esac
  done
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
no_residue

# 2. 同じ版をもう一度コピーしても書き換えない
run 0 'unchanged: tmp/superpowers-review/sample-doc-spec.md' "${args[@]}" --name sample-doc-spec.md

# 3. 未コミットの変更（作業ツリー、index）がある正本はコピーしない
printf '# sample dirty\n' > "$doc/$spec"
run 1 'commit it first' "${args[@]}" --name sample-doc-spec.md
git -C "$doc" add "$spec"
run 1 'commit it first' "${args[@]}" --name sample-doc-spec.md
git -C "$doc" reset -q --hard
same_as "$copy" "$doc" "$v1"

# 4. 新しい版は同名では差し替えず、別名の新コピーへ公開する。--replace-from は拒否して何も変えない
printf '# sample v2\n' > "$doc/$spec"
git -C "$doc" commit -q -am v2
v2="$(git -C "$doc" rev-parse HEAD)"
run 1 'already exists with other content' "${args[@]}" --name sample-doc-spec.md
same_as "$copy" "$doc" "$v1"
no_residue
run 2 'replace-from' "${args[@]}" --name sample-doc-spec.md --replace-from "$v1"
same_as "$copy" "$doc" "$v1"
no_residue
run 0 'created: tmp/superpowers-review/sample-doc-r2-spec.md' "${args[@]}" --name sample-doc-r2-spec.md
same_as "$parent/tmp/superpowers-review/sample-doc-r2-spec.md" "$doc" "$v2"
same_as "$copy" "$doc" "$v1"

# 5. ユーザが編集した同名コピーも差し替えない。別名なら旧コピーに触れずに公開できる
printf 'user note\n' >> "$parent/tmp/superpowers-review/sample-doc-r2-spec.md"
edited="$(cat "$parent/tmp/superpowers-review/sample-doc-r2-spec.md")"
printf '# sample v3\n' > "$doc/$spec"
git -C "$doc" commit -q -am v3
run 1 'already exists with other content' "${args[@]}" --name sample-doc-r2-spec.md
[ "$(cat "$parent/tmp/superpowers-review/sample-doc-r2-spec.md")" = "$edited" ] || fail 'an edited copy was overwritten'
no_residue
run 0 'created: tmp/superpowers-review/sample-doc-r3-spec.md' "${args[@]}" --name sample-doc-r3-spec.md
[ "$(cat "$parent/tmp/superpowers-review/sample-doc-r2-spec.md")" = "$edited" ] || fail 'a new versioned copy overwrote the old one'

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
no_residue

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

# 11. remote URL の形式: 独立した checkout で doc / parent の検査を別々に実行する。
# linked worktree は remote 設定を共有するため、片方だけ変えるこの検査には使わない。
url_doc="$tmp/url-doc"
url_parent="$tmp/url-parent"
new_repo "$url_doc"
new_repo "$url_parent"
url_args=(--doc-root "$url_doc" --parent-root "$url_parent" --path "$spec")
url_formats=(
  "$origin"
  'git@github.com:usaturn/create-reso-world.git'
  'ssh://git@github.com/usaturn/create-reso-world.git'
  'ssh://git@github.com/usaturn/create-reso-world'
)
url_failures=0
for side in doc parent; do
  index=0
  for remote_url in "${url_formats[@]}"; do
    git -C "$url_doc" remote set-url origin "$origin"
    git -C "$url_parent" remote set-url origin "$origin"
    if [ "$side" = doc ]; then url_root="$url_doc"; else url_root="$url_parent"; fi
    git -C "$url_root" remote set-url origin "$remote_url"
    url_name="url-$side-$index-spec.md"
    printf 'URL format check: %s origin=%s\n' "$side" "$remote_url"
    (
      run 0 "created: tmp/superpowers-review/$url_name" "${url_args[@]}" --name "$url_name"
      same_as "$url_parent/tmp/superpowers-review/$url_name" "$url_doc" HEAD
    ) || url_failures=$((url_failures + 1))
    index=$((index + 1))
  done
done
[ "$url_failures" -eq 0 ] || fail "$url_failures independent-root URL format checks failed"

# 12. 不一致の host / repository はどちらの root でも拒否し、コピー先を作らない。
for side in doc parent; do
  for remote_url in \
    'https://example.com/usaturn/create-reso-world.git' \
    'git@example.com:usaturn/create-reso-world.git' \
    'ssh://git@example.com/usaturn/create-reso-world.git' \
    'ssh://git@github.com/someone/other.git'; do
    git -C "$url_doc" remote set-url origin "$origin"
    git -C "$url_parent" remote set-url origin "$origin"
    if [ "$side" = doc ]; then url_root="$url_doc"; else url_root="$url_parent"; fi
    git -C "$url_root" remote set-url origin "$remote_url"
    run 1 "--$side-root origin is not usaturn/create-reso-world" "${url_args[@]}" --name rejected-url-spec.md
    [ ! -e "$url_parent/tmp/superpowers-review/rejected-url-spec.md" ] || fail 'copied from a mismatched remote'
  done
done
[ -z "$(git -C "$url_doc" status --porcelain)" ] || fail 'URL checks changed the document working tree or index'
[ -z "$(git -C "$url_parent" status --porcelain)" ] || fail 'URL checks changed the parent working tree or index'

# 13. コピー先が FIFO のときは読み込まずに止まり、一時ファイルを残さない
mkfifo "$parent/tmp/superpowers-review/fifo-doc-spec.md"
run 1 'is not a regular file' "${args[@]}" --name fifo-doc-spec.md
[ -p "$parent/tmp/superpowers-review/fifo-doc-spec.md" ] || fail 'the FIFO destination was replaced'
no_residue

# 14. 公開の失敗後も、他の actor が作った既存コピーはそのまま残る
run 1 'already exists with other content' "${args[@]}" --name sample-doc-spec.md
same_as "$copy" "$doc" "$v1"
no_residue

printf 'PASS: superpowers-review-copy publishes non-replacing copies and refuses unsafe targets\n'
