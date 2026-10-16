#!/bin/bash
# resoloop の Meshy プラグインのリポジトリ（usaturn/resoloop-meshy）を external/resoloop-meshy に取得し、状態を表示する。
# 仕様: docs/superpowers/specs/2026-10-16-create-reso-world-issue-96-plugin-repo-design.md D-4・D-5。運用手順: docs/resoloop-meshy-workflow.md
# 使い方: scripts/resoloop-meshy.sh <clone|status>
# 既定の checkout 先は、このスクリプトを含む create-reso-world の親 checkout（git の common dir の親）の
# external/resoloop-meshy。create-reso-world の worktree から実行しても同じ場所を指す。
# 環境変数（テストと特殊な運用向け）:
#   RESOLOOP_MESHY_CHECKOUT    checkout 先（既定: <親 checkout>/external/resoloop-meshy）
#   RESOLOOP_MESHY_ORIGIN_URL  origin の URL（既定: https://github.com/usaturn/resoloop-meshy.git）
# 終了コード:
#   0 成功（status は常に 0）
#   1 状態が期待と違う（自前の git の checkout でない、origin が無い・違う）
#   2 使い方の誤り
#   3 前提不足（git が無い）
#   4 git clone の失敗
set -euo pipefail

usage() {
  printf 'usage: %s <clone|status>\n' "${BASH_SOURCE[0]}" >&2
  exit 2
}
die() { printf 'ERROR: %s\n' "$2" >&2; exit "$1"; }

[ $# -eq 1 ] || usage
cmd="$1"
case "$cmd" in clone|status) ;; *) usage ;; esac
command -v git >/dev/null 2>&1 || die 3 "git not found"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# worktree の中に clone すると、worktree を消したときにプラグインの作業ごと消える。親 checkout を基準にする
if common="$(git -C "$root" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; then
  root="$(dirname "$common")"
fi
# 相対パスの RESOLOOP_MESHY_CHECKOUT は呼び出し時の cwd を基準に絶対パスにする。symlink は解決しない
dir="$(realpath -ms -- "${RESOLOOP_MESHY_CHECKOUT:-$root/external/resoloop-meshy}")"
origin_url="${RESOLOOP_MESHY_ORIGIN_URL:-https://github.com/usaturn/resoloop-meshy.git}"

same_url() {  # 末尾の / と .git の有無だけが違う URL は同じとみなす
  local a="${1%/}" b="${2%/}"
  [ "${a%.git}" = "${b%.git}" ]
}

is_checkout() {  # $dir がそれ自体 git の checkout のルートなら 0（外側のリポジトリのサブディレクトリは 1）
  local top
  [ -d "$dir" ] || return 1
  top="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || return 1
  [ "$(cd "$top" && pwd -P)" = "$(cd "$dir" && pwd -P)" ]
}

not_a_checkout="exists but is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-meshy.sh clone"

check_origin() {  # origin を期待する URL と比べ、食い違いを 1 行で出力する。食い違いがあれば 1
  local got
  if ! got="$(git -C "$dir" remote get-url origin 2>/dev/null)"; then
    printf 'origin is missing (expected %s)\n' "$origin_url"
    return 1
  fi
  same_url "$got" "$origin_url" && return 0
  printf 'origin is %s (expected %s)\n' "$got" "$origin_url"
  return 1
}

do_clone() {
  local problem
  if [ -e "$dir" ] || [ -L "$dir" ]; then
    is_checkout || die 1 "$dir $not_a_checkout"
    if ! problem="$(check_origin)"; then
      printf '%s\n' "$problem" >&2
      die 1 "$dir has an unexpected origin; fix it with git remote add/set-url (see docs/resoloop-meshy-workflow.md)"
    fi
    printf 'ok: %s is already cloned (origin is as expected)\n' "$dir"
    return
  fi
  git clone --quiet --origin origin -- "$origin_url" "$dir" \
    || die 4 "git clone failed (the repository is private; check gh auth status)"
  printf 'cloned: %s (origin %s)\n' "$dir" "$origin_url"
}

do_status() {
  local head branch state problem
  if [ ! -e "$dir" ] && [ ! -L "$dir" ]; then
    printf 'checkout: %s is missing (run scripts/resoloop-meshy.sh clone)\n' "$dir"
    printf 'remote: unknown (no checkout)\n'
    return
  fi
  if ! is_checkout; then
    printf 'checkout: %s %s\n' "$dir" "$not_a_checkout"
    printf 'remote: unknown (no checkout)\n'
    return
  fi
  head="$(git -C "$dir" rev-parse -q --verify HEAD || printf 'none')"
  branch="$(git -C "$dir" symbolic-ref -q --short HEAD || printf 'detached')"
  if [ -n "$(git -C "$dir" status --porcelain --untracked-files=no)" ]; then
    state='uncommitted changes'
  else
    state='clean'
  fi
  printf 'checkout: %s at %s (%s, %s)\n' "$dir" "$head" "$branch" "$state"
  if problem="$(check_origin)"; then
    printf 'remote: origin is as expected\n'
  else
    printf 'remote: %s\n' "$problem"
  fi
}

"do_$cmd"
