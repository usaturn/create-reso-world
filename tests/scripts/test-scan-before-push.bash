#!/bin/bash
# push の前の検査（scripts/scan-before-push.sh）を、固定した版の実際の gitleaks で一時リポジトリに実行する。
# 未 push の commit（マージ commit の中だけで足した内容を含む）の秘密情報で止まること、.gitleaksignore・inline の allow・
# 作業ツリーや環境変数の設定で緩められないこと、設定の取得や gitleaks の失敗を成功として扱わないことを確かめる。
set -euo pipefail
# 外から渡された GIT_* を除く。linked worktree の git rebase --exec は GIT_DIR を export するので、残すと
# 直接実行したときに一時リポジトリの git init・git -C が、そのリポジトリの設定・index・ブランチを書き換える（#200）
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')
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

# F∩S: リポジトリの .gitleaks.toml の除外（既定の規則と、下で境界を確かめる generic-api-key の 3 つの allowlist）は、
# description を除いた全体をハッシュで固定する。allowlist を足す・入れ替える・正規表現や paths を足す・値を差し替える
# （2 つ目が除外するのは、過去の文書（commit 5a723fa の Plan）に残る既知の偽の値だけ）・規則を書き換えると、下の
# 確認はどれも通ったまま、その除外が秘密情報を通す。変えるときは、除外が秘密情報を通さないことを下の確認に足して
# から、ハッシュを更新する。偽の値は追跡するファイルに増やさないよう、解析した 2 つ目の allowlist から読む
fake="$(uv run --no-project python - "$root/.gitleaks.toml" <<'PY'
import hashlib, json, re, sys, tomllib
config = tomllib.load(open(sys.argv[1], "rb"))
for allowlist in config.get("allowlists", []):
    allowlist.pop("description", None)
digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
if digest != "d513ee442f98dd17d095ea78ddf11a8b6992ba9b3afbff4916d1d741a10caf3a":
    sys.exit(f"the exclusions in .gitleaks.toml changed (sha256 {digest})")
print(next(m.group(1) for a in config["allowlists"] if a["regexTarget"] == "secret"
           for m in [re.fullmatch(r"\^([A-Za-z0-9]{20,})\$", a["regexes"][0])] if m))
PY
)" || fail '.gitleaks.toml has exclusions other than the three allowlists checked below'

# リポジトリの .gitleaks.toml を base にしても、無作為な値は検出する。resoloop の識別子の除外（#135）に、
# 識別子の前後や区切りを付けた無作為な値が紛れない。値は実行時に作る（英字の大小と数字が入り混じる）
random="$(printf 'create-reso-world issue-135 random value' | sha256sum | cut -c1-64 | base64 -w0 | tr -dc 'A-Za-z0-9' | cut -c1-32)"
hash8="$(printf 'create-reso-world issue-135 name' | sha256sum | cut -c1-8)"
# 値は base64 として復号した後にも検出されることがある（Tags: [decoded:base64 ...]）。その検出だけで止まると、
# allowlist を広げても通ってしまうので、値そのものの検出を 1 件以上求める
expect_direct_leak() {
  expect_leak "$1"
  [ "$(grep -c '^Finding:' "$tmp/stderr")" -gt "$(grep -c '^Tags:.*decoded:' "$tmp/stderr")" ] \
    || { show; fail "$1: reported only decoded values"; }
}
leak_with_repo_config() {
  new_repo "$root/.gitleaks.toml"
  commit_file config.py "api_key = \"$2\""
  scan
  expect_direct_leak "$1 with the repository .gitleaks.toml"
}
leak_with_repo_config 'a random value after a prefix' "msy_$random"
leak_with_repo_config 'a random value shaped like an identifier' "mat_material_${random:0:16}_$hash8"
leak_with_repo_config 'a password of words and 8 digits without a key() prefix' "summer_Holiday2024_${hash8//[a-f]/7}"
# 2 つ目（テスト用の偽の値そのもの）と 3 つ目（key() の識別子）の allowlist は、前後に値が続くものを除外しない（^ と $）
identifier="mat_material_Slum02_rubber_$hash8"
leak_with_repo_config 'the fake token after a prefix' "x$fake"
leak_with_repo_config 'the fake token before a suffix' "${fake}x"
leak_with_repo_config 'a random value before an identifier' "${random:0:8}_$identifier"
leak_with_repo_config 'an identifier before a random value' "$identifier${random:0:8}"
leak_with_repo_config 'an identifier whose hash is not lowercase hex' "mat_material_Slum02_${random:0:8}"
# 1 つ目の allowlist（resoloop のマニフェストの "key": "<識別子>" の形）も、区切りの無い無作為な値は除外しない
new_repo "$root/.gitleaks.toml"
commit_file manifest.json "{\"key\": \"$random\"}"
scan
expect_direct_leak 'a random value as a manifest key with the repository .gitleaks.toml'
# 1 つ目の allowlist は "key" という名前の項目だけを対象にする（^）。api_key などの項目の値は除外しない
new_repo "$root/.gitleaks.toml"
commit_file config.json "{\"api_key\": \"msy_$random\"}"
scan
expect_direct_leak 'a random value with separators in an api_key item with the repository .gitleaks.toml'

# --- 検査できないときは止まる ---
new_repo
commit_file notes.txt hello
: > "$repo/.gitleaksignore"
scan
expect_stop 'an empty .gitleaksignore' '\.gitleaksignore'

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

# S: main への取り違えは成功したまま範囲と設定を変える。実際の非 main の履歴を使い、
# scan が Gitleaks へ渡した範囲・設定・属性の基準を観測する（秘密情報の検出自体は上の実 Gitleaks で確認）。
mkdir -p "$tmp/observing" "$tmp/observation"
cat > "$tmp/observing/gitleaks" <<'FAKE'
#!/bin/bash
set -euo pipefail
[ "$1" = version ] && { printf '%s\n' "$SCAN_TEST_VERSION"; exit 0; }
printf '%s\n' "$@" > "$SCAN_TEST_OBSERVATION/args"
printf '%s\n' "${GIT_ATTR_SOURCE-}" > "$SCAN_TEST_OBSERVATION/attributes"
while [ $# -gt 0 ]; do
  case "$1" in
    --config) cp "$2" "$SCAN_TEST_OBSERVATION/config.toml"; shift 2 ;;
    *) shift ;;
  esac
done
if [ -n "${SCAN_TEST_MOVE_TO-}" ]; then
  git -C "$SCAN_TEST_REMOTE" update-ref "$SCAN_TEST_REF" "$SCAN_TEST_MOVE_TO"
fi
FAKE
chmod +x "$tmp/observing/gitleaks"

new_repo "$tmp/default.toml"
integration_branch='feat/統合-v2'
git -C "$repo" switch -qc "$integration_branch"
commit_file .gitleaks.toml $'title = "integration rules"\n[extend]\nuseDefault = true'
commit_file integration.txt 'only on the integration branch'
integration_sha="$(git -C "$repo" rev-parse HEAD)"
git -C "$repo" push -q origin "HEAD:refs/heads/$integration_branch"
git -C "$repo" switch -q feature
git -C "$repo" merge -q --ff-only "$integration_branch"
commit_file notes.txt 'only on the feature branch'
feature_sha="$(git -C "$repo" rev-parse HEAD)"
scan_env=(PATH="$tmp/observing:$PATH" SCAN_TEST_VERSION="$pinned" SCAN_TEST_OBSERVATION="$tmp/observation")
scan --base "origin/$integration_branch" --expected-base-sha "$integration_sha"
expect_success 'a pinned non-main base'
grep -qxF -- "--log-opts=--no-color --no-ext-diff --no-textconv --diff-merges=remerge $integration_sha..$feature_sha" "$tmp/observation/args" \
  || fail 'the scan used a range other than the pinned integration base..HEAD'
[ "$(cat "$tmp/observation/attributes")" = "$integration_sha" ] || fail 'the scan used attributes from another base'
git -C "$repo" show "$integration_sha:.gitleaks.toml" > "$tmp/integration.toml"
cmp -s "$tmp/integration.toml" "$tmp/observation/config.toml" || fail 'the scan used a config from another base'

# S: 捕捉した SHA を確認しないと、scan 開始前に進んだ base を正しい基準として成功してしまう。
git -C "$repo" switch -q "$integration_branch"
commit_file advanced.txt 'base advanced after capture'
advanced_base_sha="$(git -C "$repo" rev-parse HEAD)"
git -C "$repo" push -q origin "HEAD:refs/heads/$integration_branch"
git -C "$repo" switch -q feature
scan_env=(PATH="$tmp/observing:$PATH" SCAN_TEST_VERSION="$pinned" SCAN_TEST_OBSERVATION="$tmp/observation")
scan --base "origin/$integration_branch" --expected-base-sha "$integration_sha"
expect_failure 'a base that moved after capture and before the scan'

# S: 開始時だけの確認では、検査中に動いた remote を見逃して古い基準の検査を成功と報告する。
# remote に次の commit だけを用意し、Gitleaks の実行時に同じ heads ref を進める。
origin_dir="$repo/../origin.git"
next_base_sha="$(git -C "$origin_dir" commit-tree "$advanced_base_sha^{tree}" -p "$advanced_base_sha" -m 'advance during scan')"
scan_env=(PATH="$tmp/observing:$PATH" SCAN_TEST_VERSION="$pinned" SCAN_TEST_OBSERVATION="$tmp/observation"
  SCAN_TEST_REMOTE="$origin_dir" SCAN_TEST_REF="refs/heads/$integration_branch" SCAN_TEST_MOVE_TO="$next_base_sha")
scan --base "origin/$integration_branch" --expected-base-sha "$advanced_base_sha"
expect_failure 'a base that moved during the scan'
[ "$(git -C "$origin_dir" rev-parse "refs/heads/$integration_branch")" = "$next_base_sha" ] \
  || fail 'the base did not move during the scan'

# --- 成功する ---
new_repo
commit_file notes.txt hello
merge_side merged.txt 'nothing secret'
scan
expect_success 'commits and a merge commit without secrets'

printf 'PASS: scan-before-push stops on secrets and failures and cannot be relaxed (%d repositories)\n' "$cases"
