#!/bin/bash
# Spec・Plan の確認用コピーを、文書管理リポジトリのコミット済み blob から親 checkout の tmp/superpowers-review/ へ作る。
# 仕様: docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-design.md 3.3 節
# 使い方: scripts/superpowers-review-copy.sh --doc-root DIR --parent-root DIR --path PATH --name NAME [--commit REV] [--replace-from REV]
#   --doc-root      正本をコミットした create-reso-world の checkout または worktree（DOC_ROOT）の絶対パス
#   --parent-root   ユーザが確認用ファイルを読む create-reso-world の親 checkout（PARENT_ROOT）の絶対パス
#   --path          正本の DOC_ROOT 相対パス（docs/superpowers/specs/*.md または docs/superpowers/plans/*.md）
#   --name          確認用コピーのファイル名。Spec は <名前>-spec.md、Plan は <名前>-plan.md
#   --commit        コピー元のコミット（既定: HEAD）。正本の作業ツリーと index はこのコミットと一致していること
#   --replace-from  既存のコピーを差し替えるときだけ指定する。既存のコピーがこのコミットの正本と同じ場合だけ上書きする
# 成功すると、コピー先（PARENT_ROOT 相対）、コピー元のコミット SHA と正本のパス、SHA-256 を表示する。
# 拒否したときはコピー先を変えずに 1、引数の誤りは 2 で終了する。コミット、ステージ、push はしない
set -euo pipefail

DOC_REPOSITORY=usaturn/create-reso-world
REVIEW_DIR=tmp/superpowers-review

usage() { sed -n '4,10p' "$0" | sed 's/^# \{0,1\}/usage: /' >&2; exit 2; }
die() { printf 'superpowers-review-copy: %s\n' "$1" >&2; exit 1; }

github_repository() {
  sed -nE \
    -e 's#^https://github[.]com/([^/]+/[^/#?]+)(/.*)?$#\1#p' \
    -e 's#^git@github[.]com:([^/]+/[^/#?]+)([.]git)?$#\1#p' \
    -e 's#^ssh://git@github[.]com/([^/]+/[^/#?]+)([.]git)?$#\1#p' | sed 's/[.]git$//'
}

doc_root='' parent_root='' rel='' name='' rev=HEAD replace_from=''
while [ $# -gt 0 ]; do
  [ $# -ge 2 ] || usage
  case "$1" in
    --doc-root) doc_root="$2" ;;
    --parent-root) parent_root="$2" ;;
    --path) rel="$2" ;;
    --name) name="$2" ;;
    --commit) rev="$2" ;;
    --replace-from) replace_from="$2" ;;
    *) usage ;;
  esac
  shift 2
done
[ -n "$doc_root" ] && [ -n "$parent_root" ] && [ -n "$rel" ] && [ -n "$name" ] || usage

# checkout_root LABEL DIR: DIR が create-reso-world の checkout のルートであることを確かめ、実パスを出力する
checkout_root() {
  local label="$1" dir="$2" top
  [[ "$dir" == /* ]] || die "$label must be an absolute path: $dir"
  top="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || die "$label is not a git checkout: $dir"
  [ "$(realpath -e -- "$top")" = "$(realpath -e -- "$dir")" ] || die "$label is not the root of its checkout: $dir"
  [ "$(git -C "$dir" remote get-url origin 2>/dev/null | github_repository)" = "$DOC_REPOSITORY" ] \
    || die "$label origin is not $DOC_REPOSITORY: $dir"
  realpath -e -- "$dir"
}
doc_root="$(checkout_root --doc-root "$doc_root")"
parent_root="$(checkout_root --parent-root "$parent_root")"
[ "$(realpath -e -- "$(git -C "$parent_root" rev-parse --absolute-git-dir)")" = \
  "$(realpath -e -- "$(git -C "$parent_root" rev-parse --path-format=absolute --git-common-dir)")" ] \
  || die "--parent-root must be the main checkout, not a linked worktree: $parent_root"

case "${rel%/*}" in
  docs/superpowers/specs) kind=spec ;;
  docs/superpowers/plans) kind=plan ;;
  *) kind='' ;;
esac
[[ -n "$kind" && "$rel" == *.md && "${rel##*/}" != .* ]] \
  || die "--path must be docs/superpowers/specs/*.md or docs/superpowers/plans/*.md: $rel"
[[ "$name" =~ ^[a-z0-9][a-z0-9.-]*-(spec|plan)[.]md$ ]] \
  || die "--name must be a short lowercase file name ending in -spec.md or -plan.md: $name"
[ "${BASH_REMATCH[1]}" = "$kind" ] || die "--name ends in -${BASH_REMATCH[1]}.md but --path is a $kind"

commit="$(git -C "$doc_root" rev-parse --verify --quiet "$rev^{commit}")" || die "--commit is not a commit in $doc_root: $rev"
entry="$(git -C "$doc_root" ls-tree "$commit" -- "$rel")"
[ -n "$entry" ] || die "$rel is not committed in $commit"
case "${entry%% *}" in 100644 | 100755) ;; *) die "$rel is not a regular file in $commit" ;; esac
blob="$(git -C "$doc_root" rev-parse --verify --quiet "$commit:$rel")"
git -C "$doc_root" diff --quiet "$commit" -- "$rel" && git -C "$doc_root" diff --quiet --cached "$commit" -- "$rel" \
  || die "$rel in $doc_root differs from $commit; commit it first"

for d in "$parent_root/tmp" "$parent_root/$REVIEW_DIR"; do
  [ ! -L "$d" ] || die "$d is a symlink"
  [ ! -e "$d" ] || [ -d "$d" ] || die "$d is not a directory"
done
dest_rel="$REVIEW_DIR/$name"
git -C "$parent_root" check-ignore -q -- "$dest_rel" || die "$dest_rel is not ignored in $parent_root"
mkdir -p -- "$parent_root/$REVIEW_DIR"
[ "$(realpath -e -- "$parent_root/$REVIEW_DIR")" = "$parent_root/$REVIEW_DIR" ] \
  || die "$parent_root/$REVIEW_DIR resolves outside the parent checkout"
dest="$parent_root/$dest_rel"

staged=''
trap '[ -z "$staged" ] || rm -f -- "$staged"' EXIT
staged="$(mktemp "$parent_root/$REVIEW_DIR/.$name.XXXXXX")"
git -C "$doc_root" cat-file blob "$blob" > "$staged"
if [ -L "$dest" ]; then
  die "$dest_rel is a symlink"
elif [ ! -e "$dest" ]; then
  status=created
elif [ ! -f "$dest" ]; then
  die "$dest_rel is not a regular file"
elif cmp -s -- "$staged" "$dest"; then
  status=unchanged
elif [ -n "$replace_from" ]; then
  old="$(git -C "$doc_root" rev-parse --verify --quiet "$replace_from^{commit}")" || die "--replace-from is not a commit: $replace_from"
  git -C "$doc_root" cat-file -e "$old:$rel" 2>/dev/null || die "$rel is not committed in $old"
  git -C "$doc_root" cat-file blob "$old:$rel" | cmp -s - "$dest" \
    || die "$dest_rel differs from $rel at $old (edited, or another document); not replaced"
  status=replaced
else
  die "$dest_rel already exists with other content; choose another --name, or pass --replace-from with the reviewed commit"
fi
if [ "$status" != unchanged ]; then
  chmod 0644 -- "$staged"
  mv -f -- "$staged" "$dest"
  staged=''
fi
git -C "$doc_root" cat-file blob "$blob" | cmp -s - "$dest" || die "$dest_rel does not match $rel at $commit after copying"

printf '%s: %s\n' "$status" "$dest_rel"
printf 'source: %s at %s\n' "$rel" "$commit"
printf 'sha256: %s\n' "$(sha256sum -- "$dest" | cut -d' ' -f1)"
