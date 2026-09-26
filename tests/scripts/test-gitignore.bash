#!/bin/bash
# ルート .gitignore が仕様 4.4 の追跡方針どおりに働くことを検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

expect_ignored() {
  git check-ignore -q --no-index "$1" || { printf 'FAIL: expected ignored: %s\n' "$1" >&2; exit 1; }
}
expect_not_ignored() {
  if git check-ignore -q --no-index "$1"; then
    printf 'FAIL: expected NOT ignored: %s\n' "$1" >&2; exit 1
  fi
}

for p in \
  slum02/.venv/bin/python slum02/tmp/x akichi/.uv-cache/x slum02/__pycache__/x.pyc \
  docs_draft/x.md MyResoniteProject/docs_draft/x.rst \
  slum02/.resoloop/cache/reflection/x.json slum02/.resoloop/state/x.json \
  MyResoniteProject/.resoloop/tokyo-nova/task3b/x.json \
  slum02/artifacts/slum02/market.blend1 MyResoniteProject/modeling/tokyo_nova/layout.py.orig \
  external/resoloop/README.md private/trpg/TNX.txt reviews/x.md .worktrees/x/README.md \
  .claude/worktrees/x/README.md .superpowers/sdd/x.log \
  .claude/settings.local.json .devin/mcp_config.local.json .env .env.local .secrets/x \
  slum02/flux/build/x slum02/flux/x.brson node_modules/x; do
  expect_ignored "$p"
done

for p in \
  slum02/.resoloop/.gitignore .devcontainer/devcontainer-lock.json \
  slum02/assets/images/tex.png MyResoniteProject/lib/foo.py slum02/build/x.json docs/x.pdf \
  slum02/artifacts/slum02/market.blend akichi/content/x.mesh.json templates/world-project/CLAUDE.md \
  docs/worlds/tokyo-nova/tokyo-nova-assets.rst scripts/new-world.sh; do
  expect_not_ignored "$p"
done

actual="$(git ls-files -i -c --exclude-standard)"
expected='MyResoniteProject/.resoloop/tokyo-nova/pipeline.json'
if [ "$actual" != "$expected" ]; then
  printf 'FAIL: tracked-but-ignored set differs from the known exception:\n%s\n' "$actual" >&2
  exit 1
fi

printf 'PASS: root .gitignore matches the tracking policy\n'
