#!/bin/bash
# scripts/resoloop-meshy.sh が別のリポジトリの checkout を自分の checkout として扱わないことを、ローカルの bare リポジトリで検査する
# （ネットワークを使わない。clone・remote の処理は resoloop-fork.sh と同じなので、代表の 1 件だけを確かめる）
# 仕様: docs/superpowers/specs/2026-10-16-create-reso-world-issue-96-plugin-repo-design.md D-4・D-5
set -euo pipefail
# 外から渡された GIT_* を除く。linked worktree の git rebase --exec は GIT_DIR を export するので、残すと
# 直接実行したときに一時リポジトリの git init・git -C が、そのリポジトリの設定・index・ブランチを書き換える（#200）
while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')
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

# 1. clone は origin を持つ checkout を作り、2 回目は origin を確かめるだけ
expect_exit 0 "cloned: $co (origin $tmp/origin.git)" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/origin.git" ] || fail 'origin url'
[ "$(git -C "$co" rev-parse HEAD)" = "$v1" ] || fail 'clone did not check out main'
expect_exit 0 "ok: $co is already cloned (origin is as expected)" clone

# 2. origin が違う・無いときは、clone は何も変えずに 1
git -C "$co" remote set-url origin "$tmp/other.git"
expect_exit 1 "origin is $tmp/other.git (expected $tmp/origin.git)" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/other.git" ] || fail 'clone changed a mismatching origin'
git -C "$co" remote remove origin
expect_exit 1 "origin is missing (expected $tmp/origin.git)" clone
if git -C "$co" remote get-url origin >/dev/null 2>&1; then fail 'clone added a missing origin'; fi

# 3. 外側のリポジトリの中にある、自前の checkout でないディレクトリは 1。外側の origin が期待する URL でも
#    clone 済みとみなさない
git init -q "$tmp/outer"
git -C "$tmp/outer" remote add origin "$tmp/origin.git"
mkdir -p "$tmp/outer/external/resoloop-meshy"
RESOLOOP_MESHY_CHECKOUT="$tmp/outer/external/resoloop-meshy" expect_exit 1 'is not a git checkout of its own' clone

printf 'PASS: resoloop-meshy script does not adopt another repository as the checkout\n'
