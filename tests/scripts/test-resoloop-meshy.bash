#!/bin/bash
# scripts/resoloop-meshy.sh を、ローカルの bare リポジトリで検査する（ネットワークを使わない）
# 仕様: docs/superpowers/specs/2026-10-16-create-reso-world-issue-96-plugin-repo-design.md D-4・D-5
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# ユーザの git 設定から隔離する（システム・グローバル設定と core.excludesFile を外す）。グローバル設定の
# safe.directory も外れるので、このリポジトリだけは所有者が違っても読めるようにしておく
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$repo_root"
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com
script="$repo_root/scripts/resoloop-meshy.sh"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# プラグインのリポジトリ（origin.git）と、別のリポジトリ（other.git）
git init -q -b main "$tmp/seed"
printf 'v1\n' > "$tmp/seed/file.txt"
git -C "$tmp/seed" add . && git -C "$tmp/seed" commit -q -m v1
git clone -q --bare "$tmp/seed" "$tmp/origin.git"
git clone -q --bare "$tmp/seed" "$tmp/other.git"
v1="$(git -C "$tmp/seed" rev-parse HEAD)"
export RESOLOOP_MESHY_ORIGIN_URL="$tmp/origin.git" RESOLOOP_MESHY_CHECKOUT="$tmp/work/external/resoloop-meshy"
co="$RESOLOOP_MESHY_CHECKOUT"

expect_exit() {  # $1=期待する終了コード、$2=出力に含まれるべき文字列、残り=$script の引数
  local want="$1" needle="$2" got=0
  shift 2
  bash "$script" "$@" > "$tmp/out.txt" 2>&1 || got=$?
  [ "$got" -eq "$want" ] || { cat "$tmp/out.txt" >&2; fail "expected exit $want, got $got: $*"; }
  grep -qF -- "$needle" "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; fail "expected output '$needle': $*"; }
}

# 1. 引数の誤りは 2
expect_exit 2 'usage:'
expect_exit 2 'usage:' bogus
expect_exit 2 'usage:' clone extra

# 2. clone の前の status は、checkout が無いことを示して 0
expect_exit 0 "checkout: $co is missing (run scripts/resoloop-meshy.sh clone)" status
grep -qF 'remote: unknown (no checkout)' "$tmp/out.txt" || fail 'status lacks the remote line'

# 3. clone は origin を持つ checkout を作り、2 回目は origin を確かめるだけ
expect_exit 0 "cloned: $co (origin $tmp/origin.git)" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/origin.git" ] || fail 'origin url'
[ "$(git -C "$co" rev-parse HEAD)" = "$v1" ] || fail 'clone did not check out main'
expect_exit 0 "ok: $co is already cloned (origin is as expected)" clone

# 4. status は HEAD・ブランチ・追跡ファイルの変更の有無と origin を表示する（未追跡ファイルは変更に数えない）
printf 'notes\n' > "$co/untracked.txt"
expect_exit 0 "checkout: $co at $v1 (main, clean)" status
grep -qF 'remote: origin is as expected' "$tmp/out.txt" || fail 'status remote'
printf 'edit\n' >> "$co/file.txt"
expect_exit 0 "checkout: $co at $v1 (main, uncommitted changes)" status
git -C "$co" checkout -q -- file.txt
rm -- "${co:?}/untracked.txt"

# 5. 末尾の / と .git の有無だけが違う URL は同じとみなす
git -C "$co" remote set-url origin "$tmp/origin.git/"
expect_exit 0 'is already cloned' clone
git -C "$co" remote set-url origin "$tmp/origin"
expect_exit 0 'is already cloned' clone

# 6. origin が違う・無いときは、clone は何も変えずに 1。status は食い違いを示して 0
git -C "$co" remote set-url origin "$tmp/other.git"
expect_exit 1 "origin is $tmp/other.git (expected $tmp/origin.git)" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/other.git" ] || fail 'clone changed a mismatching origin'
expect_exit 0 "remote: origin is $tmp/other.git (expected $tmp/origin.git)" status
git -C "$co" remote remove origin
expect_exit 1 "origin is missing (expected $tmp/origin.git)" clone
if git -C "$co" remote get-url origin >/dev/null 2>&1; then fail 'clone added a missing origin'; fi
git -C "$co" remote add origin "$tmp/origin.git"

# 7. 外側のリポジトリの中にある、自前の checkout でないディレクトリは 1。外側の origin が期待する URL でも
#    clone 済みとみなさない
git init -q "$tmp/outer"
git -C "$tmp/outer" remote add origin "$tmp/origin.git"
mkdir -p "$tmp/outer/external/resoloop-meshy"
RESOLOOP_MESHY_CHECKOUT="$tmp/outer/external/resoloop-meshy" expect_exit 1 'is not a git checkout of its own' clone
RESOLOOP_MESHY_CHECKOUT="$tmp/outer/external/resoloop-meshy" expect_exit 0 'is not a git checkout of its own' status
grep -qF 'remote: unknown (no checkout)' "$tmp/out.txt" || fail 'status lacks the remote line for a directory that is not a checkout'

# 8. clone に失敗したら 4 で、ディレクトリを残さない
RESOLOOP_MESHY_CHECKOUT="$tmp/work/broken" RESOLOOP_MESHY_ORIGIN_URL="$tmp/no-such-remote.git" expect_exit 4 'git clone failed' clone
[ ! -e "$tmp/work/broken" ] || fail 'a failed clone left a directory'

# 9. 既定の checkout 先は、スクリプトを含むリポジトリの親 checkout の external/resoloop-meshy。worktree の
#    スクリプトから clone しても、worktree の中には作らない
git init -q -b main "$tmp/parent"
mkdir -p "$tmp/parent/scripts"
cp -- "$script" "$tmp/parent/scripts/resoloop-meshy.sh"
git -C "$tmp/parent" add . && git -C "$tmp/parent" commit -q -m init
git -C "$tmp/parent" worktree add -q "$tmp/parent/.worktrees/topic"
(
  unset RESOLOOP_MESHY_CHECKOUT
  script="$tmp/parent/scripts/resoloop-meshy.sh"
  expect_exit 0 "checkout: $tmp/parent/external/resoloop-meshy is missing" status
  script="$tmp/parent/.worktrees/topic/scripts/resoloop-meshy.sh"
  expect_exit 0 "cloned: $tmp/parent/external/resoloop-meshy" clone
  [ ! -e "$tmp/parent/.worktrees/topic/external" ] || fail 'clone from a worktree wrote into the worktree'
  [ "$(git -C "$tmp/parent/external/resoloop-meshy" rev-parse HEAD)" = "$v1" ] || fail 'clone from a worktree'
)

printf 'PASS: resoloop-meshy script behaves as specified\n'
