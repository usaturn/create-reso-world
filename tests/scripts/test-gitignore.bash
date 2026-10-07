#!/bin/bash
# ルート .gitignore が仕様 4.4 の追跡方針どおりに働くことを検査する
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

# 理由付きの固定値: 秘密情報・ローカル設定・私的なデータ・別リポジトリ・生成物を誤って追跡しないための範囲
for p in \
  slum02/.venv/bin/python slum02/tmp/x akichi/.uv-cache/x slum02/__pycache__/x.pyc \
  docs_draft/x.md MyResoniteProject/docs_draft/x.rst \
  slum02/.resoloop/cache/reflection/x.json slum02/.resoloop/state/x.json \
  MyResoniteProject/.resoloop/tokyo-nova/task3b/x.json \
  slum02/artifacts/slum02/market.blend1 MyResoniteProject/modeling/tokyo_nova/layout.py.orig \
  external/resoloop/README.md private/trpg/TNX.txt reviews/x.md .worktrees/x/README.md \
  .claude/worktrees/x/README.md .superpowers/sdd/x.log \
  tmp/superpowers-review/x-spec.md \
  .claude/settings.local.json .devin/mcp_config.local.json .env .env.local .secrets/x \
  slum02/flux/build/x slum02/flux/x.brson node_modules/x \
  slum02/.claude/settings.local.json akichi/.devin/mcp_config.local.json \
  akichi/flux/build/x MyResoniteProject/flux/.protograph/x \
  MyResoniteProject/content/tokyo-nova/city/export-static/x.mesh.json \
  MyResoniteProject/content/tokyo-nova/city/export-refinement/x.mesh.json; do
  expect_ignored "$p"
done

# 理由付きの固定値: ignore が広がって、ワールドのデータ・ロック・雛形が追跡から漏れないための範囲
for p in \
  slum02/.resoloop/.gitignore .devcontainer/devcontainer-lock.json \
  slum02/assets/images/tex.png MyResoniteProject/lib/foo.py slum02/build/x.json docs/x.pdf \
  slum02/artifacts/slum02/market.blend akichi/content/x.mesh.json templates/world-project/CLAUDE.md \
  docs/worlds/tokyo-nova/tokyo-nova-assets.rst scripts/new-world.sh \
  MyResoniteProject/content/tokyo-nova/city/export/x.mesh.json; do
  expect_not_ignored "$p"
done

# 理由付きの固定値: pipeline.json はプロジェクト規約で追跡し続ける唯一の例外。ほかの ignore 対象を追跡すると私的データ・生成物が混ざる
actual="$(git ls-files -i -c --exclude-standard)"
expected='MyResoniteProject/.resoloop/tokyo-nova/pipeline.json'
if [ "$actual" != "$expected" ]; then
  printf 'FAIL: tracked-but-ignored set differs from the known exception:\n%s\n' "$actual" >&2
  exit 1
fi

printf 'PASS: root .gitignore matches the tracking policy\n'
