#!/bin/bash
# Spec・Plan の確認用コピーを、文書管理リポジトリのコミット済み blob から親 checkout の tmp/superpowers-review/ へ作る。
# 非置換コピー: 既存のコピーは決して差し替えない。新しい版は ...-r2-spec.md のような別名で公開する。
# 仕様: docs/superpowers/specs/2026-10-04-create-reso-world-pr16-document-lifecycle-root-cause-review-fixes-design.md 5.2 節
# 使い方: scripts/superpowers-review-copy.sh --doc-root DIR --parent-root DIR --path PATH --name NAME [--commit REV]
#   --doc-root      正本をコミットした create-reso-world の checkout または worktree（DOC_ROOT）の絶対パス
#   --parent-root   ユーザが確認用ファイルを読む create-reso-world の親 checkout（PARENT_ROOT）の絶対パス
#   --path          正本の DOC_ROOT 相対パス（docs/superpowers/specs/*.md または docs/superpowers/plans/*.md）
#   --name          確認用コピーのファイル名。Spec は <名前>-spec.md、Plan は <名前>-plan.md
#   --commit        コピー元のコミット（既定: HEAD）。正本の作業ツリーと index はこのコミットと一致していること
# 成功すると、コピー先（PARENT_ROOT 相対）、コピー元のコミット SHA と正本のパス、SHA-256 を表示する。
# 既存の異なる内容・symlink・directory・特殊ファイルのコピー先は差し替えず、別名を案内して 1 で終了する。
# 廃止された --replace-from は移行案内付きの 2 で拒否する。引数の誤りも 2。コミット、ステージ、push はしない
set -euo pipefail

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
entry="$here/superpowers_review_copy.py"
if [ ! -f "$entry" ]; then
  printf 'superpowers-review-copy: missing Python entrypoint: %s; use the create-reso-world scripts checkout\n' "$entry" >&2
  exit 1
fi
exec uv run --no-project python "$entry" "$@"
