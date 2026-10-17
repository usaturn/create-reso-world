#!/bin/bash
# push の前に、まだ push していない commit を Gitleaks で検査する（AGENTS.md の「push の前の秘密情報の検査」）。
# 成功したら、検査した commit の SHA だけを標準出力に出す。その SHA をそのまま push する:
#   SHA="$(bash scripts/scan-before-push.sh)" && [ -n "$SHA" ] && git push origin "$SHA:refs/heads/<branch>"
# 使い方: scripts/scan-before-push.sh [-C <dir>] [--base <remote>/<branch>]
#   -C      検査する checkout（既定は現在のディレクトリ）。そのルートで検査する
#   --base  未 push とみなす範囲の基準（既定は origin/main）。fetch してから <base>..HEAD を検査する。
#           設定は base の .gitleaks.toml を使い、base に無ければ Gitleaks の既定の規則だけを使う
# 作業ツリーの設定、環境変数（GITLEAKS_*）、.gitleaksignore、inline の gitleaks:allow では検査を緩められない。
# マージ commit も各親との差分として検査する。gitleaks は git log が失敗しても終了コード 0 で終わるので、
# 出力の ERR・FTL の行も失敗にする（このため、.devcontainer/install_gitleaks.bash で固定した版でないと検査しない）。
# 終了コード: 0 成功、1 検出または検査の失敗、2 使い方の誤り。ログはすべて標準エラーに出す
set -euo pipefail

say() { printf 'scan-before-push: %s\n' "$1" >&2; }
die() { say "$1"; exit 1; }
usage() {
  say "$1"
  printf 'usage: scripts/scan-before-push.sh [-C <dir>] [--base <remote>/<branch>]\n' >&2
  exit 2
}

dir=. base=origin/main
while [ $# -gt 0 ]; do
  case "$1" in
    -C) [ $# -ge 2 ] || usage '-C needs a directory'; dir="$2"; shift 2 ;;
    --base) [ $# -ge 2 ] || usage '--base needs <remote>/<branch>'; base="$2"; shift 2 ;;
    *) usage "unknown argument: $1" ;;
  esac
done
case "$base" in
  ?*/?*) remote="${base%%/*}" branch="${base#*/}" ;;
  *) usage "--base must be <remote>/<branch>: $base" ;;
esac

# GITLEAKS_CONFIG・GITLEAKS_CONFIG_TOML などで設定を差し替えさせない
for name in $(compgen -e); do
  case "$name" in GITLEAKS_*) unset "$name" ;; esac
done

installer="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)/.devcontainer/install_gitleaks.bash"
pinned="$(sed -n 's/^readonly GITLEAKS_VERSION="\([^"]*\)"$/\1/p' "$installer")" || die "cannot read $installer"
case "$pinned" in
  '' | *$'\n'*) die "cannot read the pinned GITLEAKS_VERSION from $installer" ;;
esac
command -v gitleaks >/dev/null 2>&1 || die "gitleaks is not on PATH; install it with: bash $installer"
actual="$(gitleaks version)" || die 'gitleaks version failed'
[ "$actual" = "$pinned" ] || die "gitleaks is version $actual, not the pinned $pinned; install it with: bash $installer"

top="$(git -C "$dir" rev-parse --show-toplevel)" || die "$dir is not in a git checkout"
cd "$top"
if [ -e .gitleaksignore ] || [ -L .gitleaksignore ]; then
  die "$top/.gitleaksignore exists; the scan does not use ignore files. Do not push; report it to the user"
fi
git remote get-url "$remote" >/dev/null 2>&1 || die "no remote '$remote' in $top"
git fetch --quiet --no-tags "$remote" "+refs/heads/$branch:refs/remotes/$remote/$branch" >&2 || die "fetching $base failed"
base_sha="$(git rev-parse --verify --quiet "refs/remotes/$remote/$branch^{commit}")" || die "cannot resolve $base"
head_sha="$(git rev-parse --verify --quiet 'HEAD^{commit}')" || die 'cannot resolve HEAD'

scan_dir="$(mktemp -d)" || die 'cannot create a temporary directory'
trap 'rm -rf -- "${scan_dir:?}"' EXIT
# 「base に無い」と「取得に失敗した」を区別する。前者だけを既定の規則にする
listed="$(git ls-tree --name-only "$base_sha" -- .gitleaks.toml)" || die "cannot list .gitleaks.toml in $base"
if [ -z "$listed" ]; then
  say "$base has no .gitleaks.toml; scanning with the Gitleaks default rules only"
  # --config を渡さないと、gitleaks は作業ツリーの .gitleaks.toml を読む
  printf '[extend]\nuseDefault = true\n' > "$scan_dir/config.toml"
else
  git show "$base_sha:.gitleaks.toml" > "$scan_dir/config.toml" || die "cannot read .gitleaks.toml from $base"
fi
: > "$scan_dir/ignore"

say "scanning $base_sha..$head_sha against $base"
status=0
gitleaks git --no-banner --no-color --redact --verbose --ignore-gitleaks-allow \
  --config "$scan_dir/config.toml" --gitleaks-ignore-path "$scan_dir/ignore" \
  --log-opts="--diff-merges=separate $base_sha..$head_sha" . 2>&1 | tee "$scan_dir/log" >&2 || status=$?
[ "$status" -eq 0 ] || die "gitleaks exited with status $status (leaks found or the scan failed). Do not push"
if grep -Eq '^[^ ]+ (ERR|FTL) ' "$scan_dir/log"; then
  die 'gitleaks reported an error although it exited with 0. Do not push'
fi
printf '%s\n' "$head_sha"
