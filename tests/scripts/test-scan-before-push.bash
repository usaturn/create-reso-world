#!/bin/bash
# push の前の検査（scripts/scan-before-push.sh）を、固定した版の実際の gitleaks で一時リポジトリに実行する。
# 未 push の commit（マージ commit の中だけで足した内容を含む）の秘密情報で止まること、.gitleaksignore・inline の allow・
# 作業ツリーや環境変数の設定で緩められないこと、設定の取得や gitleaks の失敗を成功として扱わないことを確かめる。
# base を取り込んだマージ commit で、base で公開済みの内容を検出し直さないことも確かめる
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
scan="$root/scripts/scan-before-push.sh"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# skip しない。検査を確かめずに PASS と表示すると、検査が動かない環境を見逃す
command -v gitleaks >/dev/null 2>&1 || fail "gitleaks is not on PATH; install it with: bash $root/.devcontainer/install_gitleaks.bash"

export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid
# GitHub の personal access token の形の偽の値。追跡するファイルにトークンの形の文字列を残さないよう、実行時に作る
token="ghp_$(printf 'create-reso-world scan-before-push test' | sha256sum | cut -c1-36)"

# 作業ツリー・環境変数から渡そうとする、すべてを除外する設定
cat > "$tmp/permissive.toml" <<'TOML'
[extend]
useDefault = true

[[allowlists]]
description = "allow everything"
paths = ['''.*''']
TOML
printf '[extend]\nuseDefault = true\n' > "$tmp/default.toml"

# new_repo [<base の .gitleaks.toml>]: bare の origin を持つ clone を作り、main を push して feature branch に移る
cases=0
new_repo() {
  cases=$((cases + 1))
  local dir="$tmp/case$cases"
  git init -q --bare -b main "$dir/origin.git"
  git clone -q "$dir/origin.git" "$dir/work" 2>/dev/null
  echo base > "$dir/work/README"
  if [ -n "${1:-}" ]; then cp "$1" "$dir/work/.gitleaks.toml"; fi
  git -C "$dir/work" add -A
  git -C "$dir/work" commit -qm base
  git -C "$dir/work" push -q origin HEAD:refs/heads/main
  git -C "$dir/work" switch -qc feature
  repo="$dir/work"
}
# commit_file <path> <content>: $repo に commit する
commit_file() {
  printf '%s\n' "$2" > "$repo/$1"
  git -C "$repo" add -- "$1"
  git -C "$repo" commit -qm "add $1"
}
# merge_side <path> <content>: side branch をマージし、その途中で両方の親に無いファイルを足してマージ commit にする
merge_side() {
  git -C "$repo" switch -qc side
  commit_file side.txt side
  git -C "$repo" switch -q feature
  commit_file mine.txt mine
  git -C "$repo" merge -q --no-ff --no-commit side > /dev/null 2>&1
  printf '%s\n' "$2" > "$repo/$1"
  git -C "$repo" add -- "$1"
  git -C "$repo" commit -qm merge
}

# scan [<引数>...]: $repo で検査する。scan_env の代入を env で渡す
scan_env=()
scan() {
  status=0
  (cd "$repo" && env "${scan_env[@]}" bash "$scan" "$@") > "$tmp/stdout" 2> "$tmp/stderr" || status=$?
  scan_env=()
}
show() { sed 's/^/    /' "$tmp/stderr" >&2; }
expect_failure() {
  [ "$status" -ne 0 ] || { show; fail "$1: the scan succeeded"; }
  [ ! -s "$tmp/stdout" ] || fail "$1: printed '$(cat "$tmp/stdout")' although the scan failed"
  if grep -qF "$token" "$tmp/stderr"; then fail "$1: printed the secret"; fi
}
expect_leak() {
  expect_failure "$1"
  # git が失敗したときも gitleaks は「no leaks found」と出すので、検出した件数まで見る
  grep -Eq 'leaks found: [1-9]' "$tmp/stderr" || { show; fail "$1: stopped without reporting a leak"; }
}
# expect_stop <理由> <標準エラーに出るはずの ERE>
expect_stop() {
  expect_failure "$1"
  grep -Eq -- "$2" "$tmp/stderr" || { show; fail "$1: stderr lacks /$2/"; }
}
expect_success() {
  [ "$status" -eq 0 ] || { show; fail "$1: the scan failed with status $status"; }
  [ "$(cat "$tmp/stdout")" = "$(git -C "$repo" rev-parse HEAD)" ] || fail "$1: printed '$(cat "$tmp/stdout")' instead of the HEAD SHA"
}

# --- 検出して止まる ---
new_repo
commit_file config.txt "token = \"$token\""
scan
expect_leak 'a token in an unpushed commit'

new_repo
merge_side merged.txt "token = \"$token\""
scan
expect_leak 'a token added only in a merge commit'

new_repo
commit_file config.txt "token = \"$token\" # gitleaks:allow"
scan
expect_leak 'a token with an inline gitleaks:allow comment'

# git の設定で git log -p の出力が変わっても見逃さない（gitleaks 8.30.1 は色付きの diff の追加行を読めず、0 で終わる）
new_repo
git -C "$repo" config color.ui always
git -C "$repo" config color.diff always
commit_file config.txt "token = \"$token\""
scan
expect_leak 'a token when the git config forces colored diffs'

new_repo
mkdir -p "$repo/.git/info"
printf '*.txt diff=hide\n' > "$repo/.git/info/attributes"
git -C "$repo" config diff.hide.textconv 'sed d'
commit_file config.txt "token = \"$token\""
scan
expect_leak 'a token that a textconv driver would hide'

# 属性は base から読む。branch で足した .gitattributes で binary 扱いにしても見逃さない
new_repo
printf '* -diff\n' > "$repo/.gitattributes"
git -C "$repo" add .gitattributes
commit_file config.txt "token = \"$token\""
scan
expect_leak 'a token in a file that a .gitattributes on the branch marks as binary'

new_repo "$tmp/default.toml"
cp "$tmp/permissive.toml" "$repo/.gitleaks.toml"
git -C "$repo" add .gitleaks.toml
git -C "$repo" commit -qm 'allow everything'
commit_file config.txt "token = \"$token\""
scan_env=(GITLEAKS_CONFIG="$tmp/permissive.toml" GITLEAKS_CONFIG_TOML="$(cat "$tmp/permissive.toml")")
scan
expect_leak 'a token with a permissive .gitleaks.toml on the branch and in GITLEAKS_CONFIG / GITLEAKS_CONFIG_TOML'

new_repo
commit_file config.txt "token = \"$token\""
cp "$tmp/permissive.toml" "$repo/.gitleaks.toml"
scan_env=(GITLEAKS_CONFIG="$tmp/permissive.toml" GITLEAKS_CONFIG_TOML="$(cat "$tmp/permissive.toml")")
scan
expect_leak 'a token when the base has no .gitleaks.toml and the working tree has a permissive one'
grep -q 'default rules' "$tmp/stderr" || { show; fail 'did not say that the default rules were used'; }

# --- 検査できないときは止まる ---
new_repo
commit_file notes.txt hello
: > "$repo/.gitleaksignore"
scan
expect_stop 'an empty .gitleaksignore' '\.gitleaksignore'
rm -- "$repo/.gitleaksignore"
ln -s "$tmp/missing" "$repo/.gitleaksignore"
scan
expect_stop 'a dangling .gitleaksignore symlink' '\.gitleaksignore'

printf 'this is = = not toml\n' > "$tmp/broken.toml"
new_repo "$tmp/broken.toml"
commit_file notes.txt hello
scan
expect_stop 'a broken base .gitleaks.toml' 'gitleaks exited with status'

# gitleaks 8.30.1 は git log が失敗しても終了コード 0 で「no leaks found」と出す
new_repo
commit_file notes.txt 'only in this commit'
blob="$(git -C "$repo" rev-parse HEAD:notes.txt)"
object="$repo/.git/objects/${blob:0:2}/${blob:2}"
chmod u+w "$object"
: > "$object"
scan
expect_stop 'a corrupt object in the range' 'gitleaks reported an error'

# マージ commit を読む --diff-merges=remerge は octopus マージの中身を出さない
new_repo
git -C "$repo" switch -qc side1
commit_file side1.txt side1
git -C "$repo" switch -qc side2 feature
commit_file side2.txt side2
git -C "$repo" switch -q feature
commit_file mine.txt mine
git -C "$repo" merge -q --no-edit side1 side2 > /dev/null
scan
expect_stop 'an octopus merge in the range' 'octopus merge'

new_repo
commit_file notes.txt hello
scan --base origin/nope
expect_stop 'a base branch that does not exist' 'origin/nope'
scan --base nope/main
expect_stop 'a base remote that does not exist' "no remote 'nope'"
scan --base main
expect_stop '--base without a remote' 'usage'
[ "$status" -eq 2 ] || fail "--base without a remote exited with $status, not 2"
scan --unknown
[ "$status" -eq 2 ] || fail "an unknown argument exited with $status, not 2"

pinned="$(sed -n 's/^readonly GITLEAKS_VERSION="\([^"]*\)"$/\1/p' "$root/.devcontainer/install_gitleaks.bash")"
mkdir -p "$tmp/other-version" "$tmp/failing"
printf '#!/bin/bash\necho 0.0.0\n' > "$tmp/other-version/gitleaks"
cat > "$tmp/failing/gitleaks" <<FAKE
#!/bin/bash
[ "\$1" = version ] && { echo "$pinned"; exit 0; }
exit 3
FAKE
chmod +x "$tmp/other-version/gitleaks" "$tmp/failing/gitleaks"
scan_env=(PATH="$tmp/other-version:$PATH")
scan
expect_stop 'a gitleaks of another version' 'not the pinned'
scan_env=(PATH="$tmp/failing:$PATH")
scan
expect_stop 'a gitleaks that fails' 'status 3'

# --- 成功する ---
new_repo
commit_file notes.txt hello
merge_side merged.txt 'nothing secret'
scan
expect_success 'commits and a merge commit without secrets'

# base を取り込んだマージ commit で、base で公開済みの内容を検出し直さない（止まると、base の設定を変えるまで push できない）
new_repo
commit_file notes.txt hello
git -C "$repo" switch -q main
commit_file published.txt "token = \"$token\""
git -C "$repo" push -q origin main
git -C "$repo" switch -q feature
git -C "$repo" merge -q --no-edit origin/main > /dev/null
scan
expect_success 'a merge commit that brings in a token already published on the base'

# base の .gitleaks.toml の allowlist が効く（base の設定で検査している）
{ cat "$tmp/default.toml"; printf "\n[[allowlists]]\nregexTarget = \"match\"\nregexes = ['''%s''']\n" "$token"; } > "$tmp/allow-token.toml"
new_repo "$tmp/allow-token.toml"
commit_file config.txt "token = \"$token\""
scan
expect_success 'a token that the base .gitleaks.toml allows'

new_repo
commit_file notes.txt hello
mkdir "$repo/sub"
status=0
(cd "$tmp" && bash "$scan" -C "$repo/sub") > "$tmp/stdout" 2> "$tmp/stderr" || status=$?
expect_success '-C with a subdirectory of the checkout'

printf 'PASS: scan-before-push stops on secrets and failures and cannot be relaxed (%d repositories)\n' "$cases"
