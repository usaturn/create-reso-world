#!/bin/bash
# ResoLoop の fork を取得・追従・checkout・ビルド・テストし、fork のビルドを一時的に導入する。
# 仕様: docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md D-5〜D-10。運用手順: docs/resoloop-fork-workflow.md
# 使い方: scripts/resoloop-fork.sh <clone|sync|build|test|status>
#         scripts/resoloop-fork.sh <checkout|install> <ref>
#   <ref> は fork（origin）のブランチ名。origin に無い名前は、git がそのまま解決できる名前（コミット、タグ、ローカルのブランチ、
#   upstream/main など）として扱う
# fork のビルドの導入は一時的な上書きで、次の rebuild か bash .devcontainer/install_resoloop.bash で最新の公開版に戻る。
# 環境変数（テストと特殊な運用向け）:
#   RESOLOOP_CHECKOUT      fork の checkout 先（既定: <リポジトリ>/external/resoloop）
#   RESOLOOP_ORIGIN_URL    origin の URL（既定: https://github.com/usaturn/resoloop.git）
#   RESOLOOP_UPSTREAM_URL  upstream の URL（既定: https://github.com/orange3134/resoloop.git）
# 終了コード:
#   0 成功
#   1 状態が期待と違う（git の checkout でない、remote の URL、未コミットの変更、ref を解決できない、
#     fork の main が上流から分岐、csproj の版を読めない、導入後の版の不一致）
#   2 使い方の誤り
#   3 前提不足（git / dotnet が無い、global.json が要求する SDK が無い、checkout が無い）
#   4 外部コマンドの失敗（git clone / fetch / push / checkout、dotnet build / pack / test / tool）
set -euo pipefail

usage() {
  printf 'usage: %s <clone|sync|build|test|status>\n       %s <checkout|install> <ref>\n' "${BASH_SOURCE[0]}" "${BASH_SOURCE[0]}" >&2
  exit 2
}
die() { printf 'ERROR: %s\n' "$2" >&2; exit "$1"; }
run() {  # $1=失敗時に表示する名前、残り=コマンド。失敗したら終了コード 4
  local what="$1"
  shift
  "$@" || die 4 "$what failed"
}

[ $# -ge 1 ] || usage
cmd="$1" ref=""
case "$cmd" in
  clone|sync|build|test|status) [ $# -eq 1 ] || usage ;;
  checkout|install)
    [ $# -eq 2 ] && [ -n "$2" ] || usage
    case "$2" in -*) usage ;; esac
    ref="$2" ;;
  *) usage ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# 相対パスの RESOLOOP_CHECKOUT は呼び出し時の cwd を基準に絶対パスにする（install は $root に cd してから
# --add-source を渡すため）。symlink は解決しない
dir="$(realpath -ms -- "${RESOLOOP_CHECKOUT:-$root/external/resoloop}")"
origin_url="${RESOLOOP_ORIGIN_URL:-https://github.com/usaturn/resoloop.git}"
upstream_url="${RESOLOOP_UPSTREAM_URL:-https://github.com/orange3134/resoloop.git}"
# shellcheck source=../.devcontainer/resoloop-tool.bash
source "$root/.devcontainer/resoloop-tool.bash"
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

not_a_checkout="exists but is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-fork.sh clone"

require_checkout() {
  [ -e "$dir" ] || [ -L "$dir" ] || die 3 "$dir is missing; run scripts/resoloop-fork.sh clone"
  is_checkout || die 1 "$dir $not_a_checkout"
}

check_remotes() {  # origin と upstream を期待する URL と比べ、食い違いを 1 件 1 行で出力する。食い違いがあれば 1
  local name want got bad=0
  for name in origin upstream; do
    if [ "$name" = origin ]; then want="$origin_url"; else want="$upstream_url"; fi
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
    is_checkout || die 1 "$dir $not_a_checkout"
    require_remotes
    printf 'ok: %s is already cloned (origin and upstream are as expected)\n' "$dir"
    return
  fi
  run 'git clone' git clone --quiet --origin origin -- "$origin_url" "$dir"
  run 'git remote add upstream' git -C "$dir" remote add upstream "$upstream_url"
  run 'git fetch upstream' git -C "$dir" fetch --quiet upstream
  printf 'cloned: %s (origin %s, upstream %s)\n' "$dir" "$origin_url" "$upstream_url"
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

resolved_commit="" resolved_name=""
resolve_ref() {  # origin と upstream を fetch し、$ref を resolved_commit と resolved_name に解決する（origin のブランチを優先）
  run 'git fetch origin' git -C "$dir" fetch --quiet --prune origin
  run 'git fetch upstream' git -C "$dir" fetch --quiet upstream
  # origin のブランチは名前が完全に一致するときだけ使う。origin/HEAD（symbolic ref）や ~・^ を付けた式は git の解決に任せる
  # （HEAD が origin の既定のブランチに化けないように）
  if git -C "$dir" show-ref --verify -q "refs/remotes/origin/$ref" \
    && ! git -C "$dir" symbolic-ref -q "refs/remotes/origin/$ref" >/dev/null 2>&1 \
    && resolved_commit="$(git -C "$dir" rev-parse --verify -q "refs/remotes/origin/$ref^{commit}")"; then
    resolved_name="origin/$ref"
  elif resolved_commit="$(git -C "$dir" rev-parse --verify -q "$ref^{commit}")"; then
    resolved_name="$ref"
  else
    die 1 "cannot resolve $ref: it is neither a branch on origin ($origin_url) nor a name git can resolve in $dir"
  fi
}

do_checkout() {
  require_checkout
  require_remotes
  dirty && die 1 "$dir has uncommitted changes to tracked files; commit or stash them before checking out $ref"
  resolve_ref
  if [ "$(git -C "$dir" rev-parse HEAD)" = "$resolved_commit" ] && ! git -C "$dir" symbolic-ref -q HEAD >/dev/null; then
    printf 'ok: %s is already at %s (%s, detached)\n' "$dir" "$resolved_commit" "$resolved_name"
    return
  fi
  run 'git checkout' git -C "$dir" checkout --quiet --detach "$resolved_commit"
  printf 'checked out: %s at %s (%s, detached)\n' "$dir" "$resolved_commit" "$resolved_name"
}

require_sdk() {  # checkout の global.json が要求する SDK があることを確かめる（rollForward を含む解決は dotnet に任せる）
  local want
  command -v dotnet >/dev/null 2>&1 || die 3 "dotnet not found"
  (cd "$dir" && dotnet --version </dev/null >/dev/null 2>&1) && return 0
  want="$(sed -n '/"version"/{s/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p;q;}' "$dir/global.json" 2>/dev/null || true)"
  die 3 ".NET SDK ${want:+$want }(required by $dir/global.json) is not installed; add it to additionalVersions of the dotnet feature in .devcontainer/devcontainer.json and rebuild the container"
}

fork_version() {  # HEAD のコミットから fork のビルドの版を出力する: <csproj の Version>.fork.<UTC のコミット日>.g<短い SHA>
  local csproj="$dir/src/RLoop.Cli/RLoop.Cli.csproj" base date sha
  base="$(sed -n '/<Version>/{s|.*<Version>[[:space:]]*\([^<[:space:]]*\)[[:space:]]*</Version>.*|\1|p;q;}' "$csproj" 2>/dev/null || true)"
  base="${base%%+*}"
  [ -n "$base" ] || die 1 "cannot read <Version> from $csproj"
  date="$(TZ=UTC git -C "$dir" log -1 --format=%cd --date=format-local:%Y%m%d HEAD)" || die 4 'git log failed'
  sha="$(git -C "$dir" rev-parse --short=7 HEAD)" || die 4 'git rev-parse failed'
  # SemVer: プレリリースがあれば識別子を足し、無ければプレリリースとして付ける。SHA の前の g は、数字だけの SHA が
  # 先頭が 0 の数値の識別子（不正）になるのを避ける
  case "$base" in *-*) base="$base.fork" ;; *) base="$base-fork" ;; esac
  printf '%s.%s.g%s\n' "$base" "$date" "$sha"
}

# dotnet は global.json をカレントディレクトリから探すため、ビルドとテストは checkout に cd して実行する
build_package() {  # $1=版
  local version="$1"
  (cd "$dir" && run 'dotnet build' dotnet build ResoLoop.slnx -c Release --nologo </dev/null)
  (cd "$dir" && run 'dotnet pack' dotnet pack src/RLoop.Cli/RLoop.Cli.csproj -c Release --nologo \
    -o artifacts/fork "-p:PackageVersion=$version" "-p:Version=$version" </dev/null)
  [ -f "$dir/artifacts/fork/ResoLoop.$version.nupkg" ] \
    || die 4 "dotnet pack did not produce artifacts/fork/ResoLoop.$version.nupkg"
  printf 'built: %s/artifacts/fork/ResoLoop.%s.nupkg\n' "$dir" "$version"
}

do_build() {
  local version
  require_checkout
  dirty && die 1 "$dir has uncommitted changes to tracked files; commit them first (the package version names the commit)"
  require_sdk
  version="$(fork_version)" || exit "$?"
  build_package "$version"
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
  [ "$actual" = "$1" ] || die 1 "resoloop --version reports $actual, but $1 was installed"
  printf 'ok: resoloop --version is %s\n' "$actual"
}

do_install() {
  local want installed
  command -v dotnet >/dev/null 2>&1 || die 3 "dotnet not found"
  do_clone
  do_checkout
  want="$(fork_version)" || exit "$?"
  installed="$(resoloop_installed_version)" || die 4 "dotnet tool list --global failed"
  if [ "$installed" = "$want" ]; then
    printf 'ok: ResoLoop %s is already installed\n' "$want"
  else
    require_sdk
    build_package "$want"
    (cd "$root" && run 'dotnet tool update' dotnet tool update --global ResoLoop \
      --add-source "$dir/artifacts/fork" --version "$want" --allow-downgrade </dev/null)
    printf 'installed: ResoLoop %s from %s/artifacts/fork\n' "$want" "$dir"
  fi
  verify_installed "$want"
  printf 'note: this fork build stays until the next rebuild; return to the latest NuGet release with bash .devcontainer/install_resoloop.bash\n'
}

do_status() {
  local installed="" kind="" head branch state problems match=""
  if ! command -v dotnet >/dev/null 2>&1; then
    printf 'installed version: unknown (dotnet not found)\n'
  elif ! installed="$(resoloop_installed_version)"; then
    installed=""
    printf 'installed version: unknown (dotnet tool list --global failed)\n'
  elif [ -z "$installed" ]; then
    printf 'installed version: none\n'
  else
    case "$installed" in *[.-]fork.*) kind='fork build' ;; *) kind='NuGet release' ;; esac
    printf 'installed version: %s (%s)\n' "$installed" "$kind"
    [ "$kind" != 'fork build' ] || printf 'return to the latest NuGet release: bash .devcontainer/install_resoloop.bash\n'
  fi
  if [ ! -e "$dir" ] && [ ! -L "$dir" ]; then
    printf 'checkout: %s is missing (run scripts/resoloop-fork.sh clone)\n' "$dir"
    printf 'remotes: unknown (no checkout)\n'
    return
  fi
  if ! is_checkout; then
    printf 'checkout: %s %s\n' "$dir" "$not_a_checkout"
    printf 'remotes: unknown (no checkout)\n'
    return
  fi
  head="$(git -C "$dir" rev-parse -q --verify HEAD || printf 'none')"
  branch="$(git -C "$dir" symbolic-ref -q --short HEAD || printf 'detached')"
  if dirty; then state='uncommitted changes'; else state='clean'; fi
  if [ "$kind" = 'fork build' ]; then
    if [[ "$head" == "${installed##*.g}"* ]]; then
      match=', matches the installed fork build'
    else
      match=', differs from the installed fork build'
    fi
  fi
  printf 'checkout: %s at %s (%s, %s%s)\n' "$dir" "$head" "$branch" "$state" "$match"
  if problems="$(check_remotes)"; then
    printf 'remotes: origin and upstream are as expected\n'
  else
    printf 'remotes: %s\n' "${problems//$'\n'/; }"
  fi
}

"do_$cmd"
