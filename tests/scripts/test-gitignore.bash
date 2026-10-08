#!/bin/bash
# ルート .gitignore が新しい追跡方針どおりに働くことを検査する
# 方針: docs/superpowers/specs/2026-10-08-issue-57-local-worlds-design.md の 4.1 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# GIT_CONFIG_GLOBAL=/dev/null だけでは XDG 既定の ~/.config/git/ignore が働いてしまうため、
# core.excludesFile も無効化し、システム設定も外してユーザの git 設定から隔離する。
# グローバル設定の safe.directory も外れるので、このリポジトリだけは所有者が違っても（CI のコンテナや
# Dev Container の bind mount）読めるようにしておく
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$root"
cd "$root"

expect_ignored() {
  git check-ignore -q --no-index "$1" || { printf 'FAIL: expected ignored: %s\n' "$1" >&2; exit 1; }
}
expect_not_ignored() {
  if git check-ignore -q --no-index "$1"; then
    printf 'FAIL: expected NOT ignored: %s\n' "$1" >&2; exit 1
  fi
}

# 理由付きの固定値: ワールドのプロジェクトとその中身を追跡しないための範囲（issue 57）
for p in \
  worlds/demo/.resoloop.json worlds/demo/modeling/x.py worlds/demo/AGENTS.md \
  MyResoniteProject/AGENTS.md akichi/pyproject.toml slum02/flux/resoloop.flux.json slum03/x \
  MyResoniteProject/.resoloop/tokyo-nova/pipeline.json \
  MyResoniteProject/content/tokyo-nova/city/export-static/x.mesh.json \
  MyResoniteProject/content/tokyo-nova/city/export-refinement/x.mesh.json \
  MyResoniteProject/content/tokyo-nova/city/export/x.mesh.json; do
  expect_ignored "$p"
done

# 理由付きの固定値: 秘密情報・ローカル設定・私的なデータ・別リポジトリ・生成物を誤って追跡しないための範囲
for p in \
  docs_draft/x.md \
  .resoloop/state/x.json other-dir/.resoloop/cache/reflection/x.json \
  artifacts/x/market.blend1 lib/foo.py.orig \
  external/resoloop/README.md private/trpg/TNX.txt reviews/x.md .worktrees/x/README.md \
  .claude/worktrees/x/README.md .superpowers/sdd/x.log \
  tmp/superpowers-review/x-spec.md \
  .claude/settings.local.json .devin/mcp_config.local.json .env .env.local .secrets/x \
  worlds/demo/flux/build/x worlds/demo/flux/x.brson flux/build/x flux/.protograph/x node_modules/x \
  worlds/demo/.claude/settings.local.json worlds/demo/.devin/mcp_config.local.json; do
  expect_ignored "$p"
done

# 理由付きの固定値: ignore が広がって、共通ツール・雛形・文書が追跡から漏れないための範囲
for p in \
  .devcontainer/devcontainer-lock.json \
  docs/x.pdf docs/superpowers/specs/x.md templates/world-project/CLAUDE.md \
  scripts/new-world.sh scripts/check-layout.sh .agents/skills/foo/SKILL.md \
  .claude/settings.json .resoloop/.gitignore AGENTS.md README.md; do
  expect_not_ignored "$p"
done

# 理由付きの固定値: 追跡中かつ ignore の組は 0 件であること。1 件でもあれば、ignore の過剰適用か
# 追跡解除の漏れなので失敗にする（旧来の pipeline.json の例外は無くなった）
actual="$(git ls-files -i -c --exclude-standard)"
if [ -n "$actual" ]; then
  printf 'FAIL: tracked-but-ignored files exist:\n%s\n' "$actual" >&2
  exit 1
fi

printf 'PASS: root .gitignore matches the tracking policy\n'
