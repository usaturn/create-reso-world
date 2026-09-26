#!/bin/bash
# ResoLoop の fork を取得・追従・checkout・ビルド・導入する。
# 仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 6.3 節。運用手順: docs/resoloop-fork-workflow.md
# 使い方: scripts/resoloop-fork.sh <clone|sync|checkout|build|test|install|status>
# 環境変数（テストと特殊な運用向け）:
#   RESOLOOP_LOCK_FILE      ロックファイル（既定: <リポジトリ>/.devcontainer/resoloop.lock）
#   RESOLOOP_FORK_CHECKOUT  fork の checkout 先（既定: <リポジトリ>/external/resoloop）
# 終了コード:
#   0 成功
#   1 状態が期待と違う（git の checkout でない、remote の URL、未コミットの変更、コミットが origin に無い、
#     fork の main が上流から分岐、nuget モードでの install、導入後の版の不一致）
#   2 使い方の誤り
#   3 前提不足（ロックの欠落・不正、git / dotnet が無い、必要な SDK が無い、checkout が無い）
#   4 外部コマンドの失敗（git clone / fetch / push / checkout、dotnet build / pack / test / tool）
set -euo pipefail

usage() {
  printf 'usage: %s <clone|sync|checkout|build|test|install|status>\n' "${BASH_SOURCE[0]}" >&2
  exit 2
}
die() { printf 'ERROR: %s\n' "$2" >&2; exit "$1"; }
run() {  # $1=失敗時に表示する名前、残り=コマンド。失敗したら終了コード 4
  local what="$1"
  shift
  "$@" || die 4 "$what failed"
}

[ $# -eq 1 ] || usage
cmd="$1"
case "$cmd" in
  clone|sync|checkout|build|test|install|status) ;;
  *) usage ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lock="${RESOLOOP_LOCK_FILE:-$root/.devcontainer/resoloop.lock}"
dir="${RESOLOOP_FORK_CHECKOUT:-$root/external/resoloop}"
# shellcheck source=../.devcontainer/resoloop-lock.bash
source "$root/.devcontainer/resoloop-lock.bash"
resoloop_lock_load "$lock" || die 3 "fix $lock first"
command -v git >/dev/null 2>&1 || die 3 "git not found"

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

require_checkout() {
  [ -e "$dir" ] || [ -L "$dir" ] || die 3 "$dir is missing; run scripts/resoloop-fork.sh clone"
  is_checkout || die 1 "$dir exists but is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-fork.sh clone"
}

check_remotes() {  # origin と upstream をロックと比べ、食い違いを 1 件 1 行で出力する。食い違いがあれば 1
  local name want got bad=0
  for name in origin upstream; do
    if [ "$name" = origin ]; then want="$RESOLOOP_FORK_ORIGIN"; else want="$RESOLOOP_FORK_UPSTREAM"; fi
    if ! got="$(git -C "$dir" remote get-url "$name" 2>/dev/null)"; then
      printf 'remote %s is missing (expected %s)\n' "$name" "$want"
      bad=1
    elif ! same_url "$got" "$want"; then
      printf 'remote %s is %s (expected %s)\n' "$name" "$got" "$want"
      bad=1
    fi
  done
  return "$bad"
}

require_remotes() {
  local problems
  if ! problems="$(check_remotes)"; then
    printf '%s\n' "$problems" >&2
    die 1 "$dir has unexpected remotes; fix them with git remote add/set-url (see docs/resoloop-fork-workflow.md)"
  fi
}

dirty() {  # 追跡ファイルに未コミットの変更があれば 0（未追跡ファイルは数えない）
  [ -n "$(git -C "$dir" status --porcelain --untracked-files=no)" ]
}

do_clone() {
  if [ -e "$dir" ] || [ -L "$dir" ]; then
    is_checkout || die 1 "$dir exists but is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-fork.sh clone"
    require_remotes
    printf 'ok: %s is already cloned (origin and upstream match the lock)\n' "$dir"
    return
  fi
  run 'git clone' git clone --quiet --origin origin -- "$RESOLOOP_FORK_ORIGIN" "$dir"
  run 'git remote add upstream' git -C "$dir" remote add upstream "$RESOLOOP_FORK_UPSTREAM"
  run 'git fetch upstream' git -C "$dir" fetch --quiet upstream
  printf 'cloned: %s (origin %s, upstream %s)\n' "$dir" "$RESOLOOP_FORK_ORIGIN" "$RESOLOOP_FORK_UPSTREAM"
}

do_sync() {
  local up origin_main local_main
  require_checkout
  require_remotes
  run 'git fetch upstream' git -C "$dir" fetch --quiet upstream
  run 'git fetch origin' git -C "$dir" fetch --quiet origin
  up="$(git -C "$dir" rev-parse --verify -q refs/remotes/upstream/main)" || die 1 "upstream has no main branch"
  origin_main="$(git -C "$dir" rev-parse --verify -q refs/remotes/origin/main)" || die 1 "origin has no main branch"
  if [ "$origin_main" = "$up" ]; then
    printf 'ok: origin/main already matches upstream/main (%s)\n' "$up"
  elif git -C "$dir" merge-base --is-ancestor "$origin_main" "$up"; then
    run 'git push origin main' git -C "$dir" push --quiet origin "$up:refs/heads/main"
    printf 'pushed: origin/main %s -> %s\n' "$origin_main" "$up"
  else
    die 1 "origin/main has commits that upstream/main lacks; the fork's main only mirrors upstream, so move those commits to a branch before syncing"
  fi
  # ローカルの main があれば同じく fast-forward する
  local_main="$(git -C "$dir" rev-parse --verify -q refs/heads/main)" || return 0
  [ "$local_main" != "$up" ] || return 0
  git -C "$dir" merge-base --is-ancestor "$local_main" "$up" \
    || die 1 "local main has commits that upstream/main lacks; left it unchanged"
  if [ "$(git -C "$dir" symbolic-ref -q --short HEAD || true)" = main ]; then
    dirty && die 1 "$dir has uncommitted changes on main; local main was left unchanged (origin/main is already synced)"
    run 'git merge --ff-only' git -C "$dir" merge --quiet --ff-only "$up"
  else
    run 'git branch -f main' git -C "$dir" branch --quiet -f main "$up"
  fi
  printf 'updated: local main -> %s\n' "$up"
}

do_checkout() {
  local commit="$RESOLOOP_FORK_COMMIT"
  require_checkout
  require_remotes
  dirty && die 1 "$dir has uncommitted changes to tracked files; commit or stash them before checking out $commit"
  if ! git -C "$dir" cat-file -e "$commit^{commit}" 2>/dev/null; then
    run 'git fetch origin' git -C "$dir" fetch --quiet origin
    git -C "$dir" cat-file -e "$commit^{commit}" 2>/dev/null \
      || die 1 "commit $commit is not on origin ($RESOLOOP_FORK_ORIGIN); push it to the fork first"
  fi
  if [ "$(git -C "$dir" rev-parse HEAD)" = "$commit" ] && ! git -C "$dir" symbolic-ref -q HEAD >/dev/null; then
    printf 'ok: %s is already at %s (detached)\n' "$dir" "$commit"
    return
  fi
  run 'git checkout' git -C "$dir" checkout --quiet --detach "$commit"
  printf 'checked out: %s at %s (detached)\n' "$dir" "$commit"
}

require_sdk() {  # fork の global.json が要求する SDK（RESOLOOP_FORK_SDK）があることを確かめる
  local sdks
  command -v dotnet >/dev/null 2>&1 || die 3 "dotnet not found"
  sdks="$(dotnet --list-sdks </dev/null)" || die 4 "dotnet --list-sdks failed"
  awk -v want="$RESOLOOP_FORK_SDK" '$1 == want { found = 1 } END { exit !found }' <<<"$sdks" \
    || die 3 ".NET SDK $RESOLOOP_FORK_SDK is not installed; it comes from additionalVersions of the dotnet feature in .devcontainer/devcontainer.json (rebuild the container)"
}

# dotnet は global.json をカレントディレクトリから探すため、ビルドとテストは checkout に cd して実行する
do_build() {
  local version="$RESOLOOP_FORK_PACKAGE_VERSION"
  require_checkout
  require_sdk
  (cd "$dir" && run 'dotnet build' dotnet build ResoLoop.slnx -c Release --nologo </dev/null)
  (cd "$dir" && run 'dotnet pack' dotnet pack src/RLoop.Cli/RLoop.Cli.csproj -c Release --nologo \
    -o artifacts/fork "-p:PackageVersion=$version" "-p:Version=$version" </dev/null)
  [ -f "$dir/artifacts/fork/ResoLoop.$version.nupkg" ] \
    || die 4 "dotnet pack did not produce artifacts/fork/ResoLoop.$version.nupkg"
  printf 'built: %s/artifacts/fork/ResoLoop.%s.nupkg\n' "$dir" "$version"
}

do_test() {
  require_checkout
  require_sdk
  (cd "$dir" && run 'dotnet test' dotnet test ResoLoop.slnx --nologo </dev/null)
  printf 'ok: dotnet test passed\n'
}

verify_installed() {  # $1=期待版。~/.dotnet/tools の resoloop が期待版を返すことを確かめる
  local out actual
  out="$("$HOME/.dotnet/tools/resoloop" --version </dev/null)" \
    || die 1 "the installed resoloop cannot run ($HOME/.dotnet/tools/resoloop --version failed)"
  actual="$(resoloop_version_of "$out")" || die 1 "resoloop --version printed nothing"
  [ "$actual" = "$1" ] || die 1 "resoloop --version reports $actual, but the lock expects $1"
  printf 'ok: resoloop --version is %s\n' "$actual"
}

do_install() {
  local want="$RESOLOOP_FORK_PACKAGE_VERSION" installed verb=install
  [ "$RESOLOOP_MODE" = fork ] \
    || die 1 "RESOLOOP_MODE is $RESOLOOP_MODE; run bash .devcontainer/install_resoloop.bash to install the NuGet release"
  command -v dotnet >/dev/null 2>&1 || die 3 "dotnet not found"
  installed="$(resoloop_installed_version)" || die 4 "dotnet tool list --global failed"
  if [ "$installed" = "$want" ]; then
    printf 'ok: ResoLoop %s is already installed (to install a rebuilt package, raise RESOLOOP_FORK_PACKAGE_VERSION in the lock)\n' "$want"
  else
    require_sdk
    do_clone
    do_checkout
    do_build
    [ -z "$installed" ] || verb=update
    (cd "$root" && run "dotnet tool $verb" dotnet tool "$verb" --global ResoLoop \
      --add-source "$dir/artifacts/fork" --version "$want" --allow-downgrade </dev/null)
    printf 'installed: ResoLoop %s from %s/artifacts/fork\n' "$want" "$dir"
  fi
  verify_installed "$want"
}

do_status() {
  local installed head branch state problems
  printf 'lock: %s\n' "$lock"
  printf 'mode: %s\n' "$RESOLOOP_MODE"
  printf 'expected version: %s\n' "$RESOLOOP_EXPECTED_VERSION"
  if ! command -v dotnet >/dev/null 2>&1; then
    printf 'installed version: unknown (dotnet not found)\n'
  elif ! installed="$(resoloop_installed_version)"; then
    printf 'installed version: unknown (dotnet tool list --global failed)\n'
  elif [ -z "$installed" ]; then
    printf 'installed version: none\n'
  elif [ "$installed" = "$RESOLOOP_EXPECTED_VERSION" ]; then
    printf 'installed version: %s (matches the lock)\n' "$installed"
  else
    printf 'installed version: %s (DIFFERS from the lock)\n' "$installed"
  fi
  printf 'lock commit: %s (%s)\n' "$RESOLOOP_FORK_COMMIT" "$RESOLOOP_FORK_REF"
  if [ ! -e "$dir" ] && [ ! -L "$dir" ]; then
    printf 'checkout: %s is missing (run scripts/resoloop-fork.sh clone)\n' "$dir"
    return
  fi
  if ! is_checkout; then
    printf 'checkout: %s exists but is not a git checkout of its own\n' "$dir"
    return
  fi
  head="$(git -C "$dir" rev-parse -q --verify HEAD || printf 'none')"
  branch="$(git -C "$dir" symbolic-ref -q --short HEAD || printf 'detached')"
  if dirty; then state='uncommitted changes'; else state='clean'; fi
  if [ "$head" = "$RESOLOOP_FORK_COMMIT" ]; then
    printf 'checkout: %s at %s (%s, %s, matches the lock)\n' "$dir" "$head" "$branch" "$state"
  else
    printf 'checkout: %s at %s (%s, %s, DIFFERS from the lock)\n' "$dir" "$head" "$branch" "$state"
  fi
  if problems="$(check_remotes)"; then
    printf 'remotes: origin and upstream match the lock\n'
  else
    printf 'remotes: %s\n' "${problems//$'\n'/; }"
  fi
}

"do_$cmd"
