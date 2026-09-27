# create-reso-world 再設計 フェーズ 0・1（安全確保と衛生）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 既存の履歴と進行中の作業を GitHub に退避してから、リポジトリの追跡方針（.gitignore、個人設定の追跡解除、実行権、死んだスクリプト、レイアウト検査の骨組み）を整える。

**Architecture:** フェーズ 0 はメインリポジトリの `.git` に対する git 操作だけで、作業ツリーのファイルは変更しない。フェーズ 1 は worktree `chore/repo-redesign` 上で、`.gitignore` の全面改訂と検査スクリプト `scripts/check-layout.sh` を TDD で作り、以降のフェーズがこの検査に項目を足していけるようにする。

**Tech Stack:** git、gh CLI、bash（`set -euo pipefail`、既存 `.devcontainer/test-*.bash` と同じ書き方）、uv（ルート `pyproject.toml`）

**Spec:** `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md`（2 章、4.4 節、9.1 節、10 章）

## Global Constraints

- 変数: `M=/workspaces/reso-world`（メインの作業ツリー、ブランチ feat/slum02-slum、別セッションが slum02 を編集中）、`W=/workspaces/reso-world/.worktrees/repo-redesign`（作業用 worktree、ブランチ chore/repo-redesign）。各ステップのコマンドはこの 2 変数を先に `export` してから実行する。
- メイン作業ツリー `$M` では、追跡ファイルの編集、`git add`、`git commit`、`git checkout`、`git stash`、`git clean`、`git reset` を行わない。許可されるのは、読み取り、`git remote add`、`git branch -f main`（main はどの worktree にもチェックアウトされていないことを確認してから）、`git push`、`$M/.worktrees/` 配下の worktree の追加・削除、未追跡ファイルの移動（Task 9 で指定したものだけ）、空ディレクトリ `tools/` の削除だけ。
- 変更のコミットはすべて `$W` で行い、コミットメッセージ末尾に `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` を付ける。
- Python は uv で実行する（`python3` を直接呼ばない）。
- 説明・文書では「契約」「原子的」「製品」「着地」を使わない。
- TRPG 本文（`ATS.txt`、`BTD.txt`、`TNX.txt`）はどのブランチにも追加しない。
- `git push --force` は使わない。既存リモートブランチが無い前提で、あった場合は停止して報告する。

## Review Focus

- push 先 usaturn/create-reso-world が空でなかった場合: 上書きせず停止する（Task 1 Step 1 の `isEmpty` 事前確認で担保）。
- `main` がどこかの worktree にチェックアウトされていた場合: `git branch -f` は失敗するが、事前に `git worktree list` で確認して停止する（Task 1 Step 1）。
- WIP 退避コミットに環境ファイル 3 件や巨大な未追跡 export が混入する場合: 対象を明示リストで指定し、コミット前に件数と内容を照合する（Task 2 Step 3〜4）。
- 新しい `.gitignore` が追跡済みファイルを ignore 対象にしてしまう場合: `git ls-files -i -c --exclude-standard` が既知の 1 件だけであることをテストで固定する（Task 4 のテスト）。
- `scripts/check-layout.sh` が空の clone や symlink の無いリポジトリで誤検出・誤通過する場合: 一時リポジトリで通過と失敗の両方を検査する（Task 8 のテスト）。

---

### Task 1: フェーズ 0 の前提確認、remote 追加、main の ff、既存ブランチの push

**Files:**
- 変更なし（`$M/.git` の設定とリモートだけ）

**Interfaces:**
- Produces: リモート `origin`（https://github.com/usaturn/create-reso-world.git）、リモートブランチ `main`（既定）、`feat/slum02-slum`、`feat/tokyo-nova-world`、`chore/repo-redesign`

- [ ] **Step 1: 前提を確認する**

```bash
export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign
git -C "$M" remote -v | wc -l                       # 0 であること
gh auth status 2>&1 | grep -F 'account usaturn'     # usaturn でログイン済み
gh repo view usaturn/create-reso-world --json isEmpty,visibility,defaultBranchRef --jq '[.isEmpty,.visibility,.defaultBranchRef.name]'
# [true,"PRIVATE",null] であること。isEmpty が false なら停止して報告する
git -C "$M" merge-base --is-ancestor main feat/slum02-slum && echo "main is ancestor"
git -C "$M" worktree list | grep -F '[main]' && { echo "main is checked out somewhere; stop"; exit 1; } || echo "main not checked out"
```

Expected: remote 0 件、usaturn、`isEmpty` true、`main is ancestor`、`main not checked out`。

- [ ] **Step 2: remote を追加し、main を feat/slum02-slum の HEAD に fast-forward する**

```bash
git -C "$M" remote add origin https://github.com/usaturn/create-reso-world.git
git -C "$M" branch -f main feat/slum02-slum
git -C "$M" log --oneline -1 main
git -C "$M" rev-parse main feat/slum02-slum   # 同じ SHA
```

Expected: 2 つの SHA が一致する。

- [ ] **Step 3: main を最初に push して既定ブランチにする**

```bash
git -C "$M" push -u origin main
gh repo view usaturn/create-reso-world --json defaultBranchRef --jq .defaultBranchRef.name
```

Expected: `main`。

- [ ] **Step 4: 残りのブランチを push する**

```bash
git -C "$M" push -u origin feat/slum02-slum feat/tokyo-nova-world chore/repo-redesign
git -C "$M" ls-remote --heads origin
```

Expected: `refs/heads/main`、`refs/heads/feat/slum02-slum`、`refs/heads/feat/tokyo-nova-world`、`refs/heads/chore/repo-redesign` の 4 本。

---

### Task 2: tokyo-nova の未コミット作業を `wip/tokyo-nova-refinement` に退避する

**Files:**
- 一時 worktree: `$M/.worktrees/wip-tokyo-nova`（作業後に削除）
- コミット対象（メイン作業ツリーからのコピー）: 変更済み 12 件と新規 6 件

```
MyResoniteProject/artifacts/tokyo-nova/city-resource-report.json
MyResoniteProject/content/tokyo-nova/blockout.json
MyResoniteProject/content/tokyo-nova/layout.json
MyResoniteProject/modeling/tokyo_nova/build.py
MyResoniteProject/modeling/tokyo_nova/districts.py
MyResoniteProject/modeling/tokyo_nova/interiors.py
MyResoniteProject/modeling/tokyo_nova/layout.py
MyResoniteProject/modeling/tokyo_nova/pipeline.py
MyResoniteProject/modeling/tokyo_nova/skyline.py
MyResoniteProject/tests/tokyo_nova/test_ground_topology.py
MyResoniteProject/tests/tokyo_nova/test_layout.py
MyResoniteProject/tests/tokyo_nova/test_task1_fix_regressions.py
MyResoniteProject/modeling/tokyo_nova/prop_forms.py
MyResoniteProject/modeling/tokyo_nova/uv.py
MyResoniteProject/tests/tokyo_nova/test_task3_refinement.py
MyResoniteProject/tests/tokyo_nova/test_task3a_basement.py
MyResoniteProject/tests/tokyo_nova/test_task3a_circulation.py
MyResoniteProject/tests/tokyo_nova/test_task3b_uv_gn.py
```

**Interfaces:**
- Consumes: Task 1 の `origin` と `main`
- Produces: リモートブランチ `wip/tokyo-nova-refinement`

- [ ] **Step 1: 現在の変更一覧が上のリストと一致することを確認する**

```bash
export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign
git -C "$M" diff --name-only HEAD -- MyResoniteProject | sort
git -C "$M" ls-files --others --exclude-standard -- MyResoniteProject/modeling/tokyo_nova MyResoniteProject/tests/tokyo_nova | grep -E '\.py$' | grep -v '\.orig$' | sort
```

Expected: 1 つ目が 12 行、2 つ目が 6 行で、上のリストと一致する。増減があれば停止して報告する（別セッションの進行による差異の可能性）。

- [ ] **Step 2: 一時 worktree を main から作る**

```bash
git -C "$M" worktree add "$M/.worktrees/wip-tokyo-nova" -b wip/tokyo-nova-refinement main
git -C "$M/.worktrees/wip-tokyo-nova" status --short | wc -l   # 0
```

- [ ] **Step 3: 18 ファイルをコピーする**

```bash
WIP="$M/.worktrees/wip-tokyo-nova"
while IFS= read -r f; do
  install -D -m 0644 "$M/$f" "$WIP/$f"
done <<'EOF'
MyResoniteProject/artifacts/tokyo-nova/city-resource-report.json
MyResoniteProject/content/tokyo-nova/blockout.json
MyResoniteProject/content/tokyo-nova/layout.json
MyResoniteProject/modeling/tokyo_nova/build.py
MyResoniteProject/modeling/tokyo_nova/districts.py
MyResoniteProject/modeling/tokyo_nova/interiors.py
MyResoniteProject/modeling/tokyo_nova/layout.py
MyResoniteProject/modeling/tokyo_nova/pipeline.py
MyResoniteProject/modeling/tokyo_nova/skyline.py
MyResoniteProject/tests/tokyo_nova/test_ground_topology.py
MyResoniteProject/tests/tokyo_nova/test_layout.py
MyResoniteProject/tests/tokyo_nova/test_task1_fix_regressions.py
MyResoniteProject/modeling/tokyo_nova/prop_forms.py
MyResoniteProject/modeling/tokyo_nova/uv.py
MyResoniteProject/tests/tokyo_nova/test_task3_refinement.py
MyResoniteProject/tests/tokyo_nova/test_task3a_basement.py
MyResoniteProject/tests/tokyo_nova/test_task3a_circulation.py
MyResoniteProject/tests/tokyo_nova/test_task3b_uv_gn.py
EOF
```

- [ ] **Step 4: コピー結果を照合する**

```bash
git -C "$WIP" status --short | wc -l                     # 18
git -C "$WIP" status --short | grep -cE '^ M '            # 12
git -C "$WIP" status --short | grep -cE '^\?\? '          # 6
git -C "$WIP" status --short | grep -E 'CLAUDE|APPEND_SYSTEM|settings\.local' && { echo "env files leaked; stop"; exit 1; } || echo "no env files"
for f in $(git -C "$WIP" status --short | awk '{print $2}'); do cmp -s "$M/$f" "$WIP/$f" || echo "DIFF $f"; done   # 出力なし
```

Expected: 18 / 12 / 6、`no env files`、`DIFF` 行なし。

- [ ] **Step 5: コミットして push し、一時 worktree を外す**

```bash
git -C "$WIP" add -A
git -C "$WIP" commit -q -F - <<'EOF'
wip(tokyo-nova): back up uncommitted refinement work

Snapshot of the uncommitted tokyo-nova changes from the main working tree
(12 modified files plus 6 new source/test files) taken before the
repository redesign. Known inconsistency: content/tokyo-nova/layout.json
was generated before the latest edit to modeling/tokyo_nova/layout.py
(roof_access_ramp_lower coordinates differ) and must be regenerated
before this work continues.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
git -C "$WIP" show --stat HEAD | tail -n 3
git -C "$WIP" push -u origin wip/tokyo-nova-refinement
git -C "$M" worktree remove "$M/.worktrees/wip-tokyo-nova"
git -C "$M" ls-remote --heads origin | wc -l           # 5
git -C "$M" status --short | wc -l                     # Step 1 の前と同じ件数（作業ツリーは不変）
```

Expected: `18 files changed`、リモートブランチ 5 本、メイン作業ツリーの status 件数は変わらない。

---

### Task 3: 個人設定 `.claude/settings.local.json` の追跡解除と `.git/info/exclude` の整理

**Files:**
- Modify (index only): `.claude/settings.local.json` を追跡解除
- Modify: `$M/.git/info/exclude`（worktree と共有）

**Interfaces:**
- Produces: `.claude/settings.local.json` が `git ls-files` に含まれない状態

- [ ] **Step 1: 追跡状態を確認する**

```bash
export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign
git -C "$W" ls-files .claude/settings.local.json     # 1 行出る
```

- [ ] **Step 2: 追跡を外す（ファイルは残す）**

```bash
git -C "$W" rm --cached -q .claude/settings.local.json
test -f "$W/.claude/settings.local.json" && echo "file kept"
git -C "$W" ls-files .claude/settings.local.json | wc -l   # 0
```

- [ ] **Step 3: `.git/info/exclude` から存在しないファイルの行を外す**

```bash
grep -vxF '.devin/mcp_config.local.json' "$M/.git/info/exclude" > "$M/.git/info/exclude.tmp" && mv "$M/.git/info/exclude.tmp" "$M/.git/info/exclude"
grep -v '^#' "$M/.git/info/exclude" | grep -v '^$' | wc -l    # 0
```

- [ ] **Step 4: コミット**

```bash
git -C "$W" commit -q -m "chore: stop tracking .claude/settings.local.json

Personal Claude Code settings are local-only. The file stays on disk and
is ignored by the root .gitignore in the next commit.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git -C "$W" show --stat HEAD | tail -n 2
```

Expected: `1 file changed`（削除）。

---

### Task 4: ルート `.gitignore` の全面改訂、`slum02/.gitignore` の吸収、lock の追跡、下書き文書の移動

**Files:**
- Test: `tests/scripts/test-gitignore.bash`（新規、実行権付き）
- Modify: `.gitignore`（全置換）
- Delete: `slum02/.gitignore`
- Create: `.devcontainer/devcontainer-lock.json`（`$M` から複製）
- Move: `MyResoniteProject/docs_draft/tokyo-nova-assets.rst`、`MyResoniteProject/docs_draft/tokyo-nova-resources.rst` → `docs/worlds/tokyo-nova/`

**Interfaces:**
- Produces: 追跡方針（仕様 4.4）を満たす `.gitignore`。`git ls-files -i -c --exclude-standard` の出力は `MyResoniteProject/.resoloop/tokyo-nova/pipeline.json` の 1 行だけ

- [ ] **Step 1: 失敗するテストを書く**

`$W/tests/scripts/test-gitignore.bash`:

```bash
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign
mkdir -p "$W/tests/scripts"
chmod +x "$W/tests/scripts/test-gitignore.bash"
bash "$W/tests/scripts/test-gitignore.bash"
```

Expected: `FAIL: expected ignored: akichi/.uv-cache/x`（旧 .gitignore に無い規則で最初に失敗する）。

- [ ] **Step 3: `.gitignore` を書き換える**

`$W/.gitignore` を次の内容で全置換する。

```gitignore
# create-reso-world: ローカル専用物と生成物だけを除外する。
# 追跡方針は docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md の 4.4 節を参照。

## Python / uv
__pycache__/
*.py[cod]
.venv/
.uv-cache/
.pytest_cache/
.ruff_cache/
.coverage
.coverage.*

## Blender のバックアップ
*.blend1
*.blend2
*.blend@

## 編集の残骸
*.orig
*.rej
*.bak
*.log

## resoloop の状態・キャッシュ・作業物（scaffold の .gitignore だけは追跡する）
**/.resoloop/**
!**/.resoloop/.gitignore
**/flux/build/
**/flux/.protograph/
*.brson

## ローカル専用ディレクトリ
tmp/
docs_draft/
/reviews/
/external/
/private/
/.worktrees/
/.claude/worktrees/
/.superpowers/
/.restructure-backup/

## 個人設定・秘密情報
**/.claude/settings.local.json
**/.devin/mcp_config.local.json
.env
.env.*
.secrets/

## Node（npx などが作る）
node_modules/
```

（この節の `tmp/` と `docs_draft/` は実装後の最終レビューを受けた書き方で、末尾だけに `/` があるのでどの階層にも一致する。`**/` の前置は、途中に `/` を含むパターンにだけ要る。フェーズ 6 で注記を訂正した。）

- [ ] **Step 4: lock を追跡し、`slum02/.gitignore` を削除し、下書き文書を移動する**

```bash
cp "$M/.devcontainer/devcontainer-lock.json" "$W/.devcontainer/devcontainer-lock.json"
git -C "$W" add .devcontainer/devcontainer-lock.json
git -C "$W" rm -q slum02/.gitignore
mkdir -p "$W/docs/worlds/tokyo-nova"
git -C "$W" mv MyResoniteProject/docs_draft/tokyo-nova-assets.rst docs/worlds/tokyo-nova/tokyo-nova-assets.rst
git -C "$W" mv MyResoniteProject/docs_draft/tokyo-nova-resources.rst docs/worlds/tokyo-nova/tokyo-nova-resources.rst
git -C "$W" status --short
```

Expected: `A .devcontainer/devcontainer-lock.json`、`D slum02/.gitignore`、`R MyResoniteProject/docs_draft/... -> docs/worlds/tokyo-nova/...` 2 件、`M .gitignore`、`?? tests/`。

- [ ] **Step 5: テストが通ることを確認する**

```bash
bash "$W/tests/scripts/test-gitignore.bash"
git -C "$W" check-ignore -v --no-index slum02/.resoloop/cache/reflection/x.json   # .gitignore の **/.resoloop/** 行
```

Expected: `PASS: root .gitignore matches the tracking policy`。

- [ ] **Step 6: コミット**

```bash
git -C "$W" add .gitignore tests/scripts/test-gitignore.bash
git -C "$W" commit -q -m "chore: rewrite root .gitignore for the resoloop monorepo

Replace the inherited node/python template with rules for uv, Blender
backups, resoloop state and caches, local-only directories and personal
settings. Track devcontainer-lock.json, fold slum02/.gitignore into the
root file and move the two tracked tokyo-nova draft documents to
docs/worlds/tokyo-nova/. tests/scripts/test-gitignore.bash pins the policy.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git -C "$W" show --stat HEAD | tail -n 8
```

---

### Task 5: `.devcontainer` と `scripts` の実行権を git index に記録する

**Files:**
- Modify (mode only): `.devcontainer/*.bash`、`.devcontainer/pi-superagents-exec.zsh`、`.devcontainer/{piccd,piccg,piga,pigl,pigo,pigod,pigou,pigs,pixg}`、`scripts/*.zsh`、`tests/scripts/test-gitignore.bash`

**Interfaces:**
- Produces: clone 直後でも `[ -x ]` を要求する Dev Container テストが通る状態

- [ ] **Step 1: 対象を確認する**

```bash
export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign
git -C "$W" ls-files -s .devcontainer scripts tests | awk '$1=="100644"{print $4}' | grep -E '\.(bash|zsh|sh)$|/(pigo|pigod|pigou|piccg|piccd|piga|pigs|pigl|pixg)$'
```

Expected: 31 行（`.devcontainer` 27、`scripts` 4）。`tests/scripts/test-gitignore.bash` は Task 4 で `chmod +x` してから `git add` したので 100755 で記録済みであり、ここには出ない。

- [ ] **Step 2: 実行権を付ける（index とディスクの両方）**

```bash
cd "$W"
git ls-files -s .devcontainer scripts tests | awk '$1=="100644"{print $4}' | grep -E '\.(bash|zsh|sh)$|/(pigo|pigod|pigou|piccg|piccd|piga|pigs|pigl|pixg)$' > /tmp/exec-list.txt
xargs -a /tmp/exec-list.txt chmod +x
xargs -a /tmp/exec-list.txt git update-index --chmod=+x
git ls-files -s .devcontainer scripts tests | awk '$1=="100644"{print $4}' | grep -cE '\.(bash|zsh|sh)$|/(pigo|pigod|pigou|piccg|piccd|piga|pigs|pigl|pixg)$' || echo "0 remaining"
```

Expected: `0 remaining`。

- [ ] **Step 3: 実行権が原因で失敗していた 4 本のテストが通ることを確認する**

```bash
cd "$W"
for t in test-herdr-status test-herdr-agent-task test-pi-openai-codex test-pi-superagents; do
  bash ".devcontainer/$t.bash" && echo "RESULT $t PASS" || echo "RESULT $t FAIL"
done
bash .devcontainer/test-herdr-migration.bash || echo "RESULT test-herdr-migration FAIL (expected until phase 4: install_pinned_gitleaks assertion)"
```

Expected: 4 本 PASS。`test-herdr-migration` だけ FAIL（フェーズ 4 で解消する既知事項）。

- [ ] **Step 4: コミット**

```bash
git -C "$W" commit -q -m "chore: record executable bits for devcontainer scripts and launchers

All scripts and pi launchers were tracked as 100644 since the initial
commit, so the [ -x ] checks in four Dev Container tests failed on a
fresh clone.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git -C "$W" show --stat HEAD | tail -n 1
```

Expected: `31 files changed` と mode change の表示。

---

### Task 6: 呼び出し元の無いスクリプトを削除する

**Files:**
- Delete: `scripts/add_pi_skills_setting.py`、`scripts/poke_claude_onboarding.py`、`scripts/unpoke_claude_onboarding.py`

- [ ] **Step 1: 参照が無いことを確認する**

```bash
export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign
git -C "$W" grep -n -E 'add_pi_skills_setting|poke_claude_onboarding' -- . ':!scripts' ':!docs/superpowers'
```

Expected: 出力なし（仕様書内の言及だけが除外対象）。

- [ ] **Step 2: 削除してコミット**

```bash
git -C "$W" rm -q scripts/add_pi_skills_setting.py scripts/poke_claude_onboarding.py scripts/unpoke_claude_onboarding.py
ls "$W/scripts"
git -C "$W" commit -q -m "chore: remove unreferenced pi and Claude onboarding scripts

add_pi_skills_setting.py wrote absolute repository paths into the global
pi settings, which pi no longer needs because it discovers .agents/skills
itself. The two onboarding scripts have no callers.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

Expected: `scripts/` に `setup_pi*.zsh` 4 本と `setup_pi_tool_display.py` だけが残る。

---

### Task 7: ルート `pyproject.toml` とテスト用ディレクトリ

**Files:**
- Create: `pyproject.toml`、`uv.lock`

**Interfaces:**
- Produces: リポジトリルートで `uv run pytest <paths>` が使える（pytest と pyyaml 入り）。`tests/scripts/` は bash テスト、`tests/skills/` はフェーズ 2 で Python テストを置く

- [ ] **Step 1: `pyproject.toml` を書く**

`$W/pyproject.toml`:

```toml
[project]
name = "create-reso-world"
version = "0.0.0"
description = "Dev Container environment for building Resonite worlds with resoloop and Blender"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = [
    "pytest>=8",
    "pyyaml>=6",
]

[tool.pytest.ini_options]
testpaths = ["tests", ".agents/skills"]
addopts = "-p no:cacheprovider"

[tool.uv]
package = false
```

- [ ] **Step 2: lock を作り、収集だけ実行する**

```bash
export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign
cd "$W" && uv lock && uv run pytest --collect-only -q .agents/skills 2>/dev/null | tail -n 1
```

Expected: `uv.lock` が生成され、`206 tests collected` 相当（ベースライン 169 + 37）。件数が違う場合は、フェーズ 2 以降で変わるので数だけ記録する。

- [ ] **Step 3: 各プロジェクトの uv がルートに引きずられないことを確認する**

```bash
cd "$W/slum02" && uv run python -c "import sys; print(sys.prefix)"
```

Expected: `/workspaces/reso-world/.worktrees/repo-redesign/slum02/.venv`（プロジェクト直下の `.venv`）。

- [ ] **Step 4: コミット**

```bash
git -C "$W" add pyproject.toml uv.lock
git -C "$W" commit -q -m "build: add root pyproject for repository-level tests

Provides pytest and pyyaml through uv for the skill contract tests and
the tests/ directory. No uv workspace: each world project keeps its own
pyproject and .venv.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: `scripts/check-layout.sh` の骨組み（TDD）

**Files:**
- Test: `tests/scripts/test-check-layout.bash`（新規、実行権付き）
- Create: `scripts/check-layout.sh`（実行権付き）

**Interfaces:**
- Produces: `scripts/check-layout.sh [--root DIR]`。終了コード 0 = 全検査通過、1 = 失敗あり、64 = 引数エラー。標準出力に `ok: <検査名>` と最後に `PASS: check-layout`、標準エラーに `FAIL: <理由>` を出す。フェーズ 2〜4 は `check_*` 関数を追加し、末尾の呼び出し列に並べる
- 検査項目（フェーズ 1）: (1) 追跡してはいけないファイルが無い、(2) 追跡中の symlink がすべて解決できる、(3) 追跡中かつ ignore 対象のファイルが許可リスト（`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json`）だけ

- [ ] **Step 1: 失敗するテストを書く**

`$W/tests/scripts/test-check-layout.bash`:

```bash
#!/bin/bash
# scripts/check-layout.sh が通過・失敗を正しく判定することを一時リポジトリで検査する
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
checker="$root/scripts/check-layout.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

new_repo() {
  git init -q "$1"
  git -C "$1" config user.email test@example.com
  git -C "$1" config user.name test
  printf 'ok\n' > "$1/README.md"
  git -C "$1" add README.md
  git -C "$1" commit -q -m init
}

expect_fail_with() {
  local dir="$1" needle="$2" out="$tmp/out.txt"
  if bash "$checker" --root "$dir" > "$out" 2>&1; then
    printf 'FAIL: %s was accepted\n' "$dir" >&2; exit 1
  fi
  grep -qF "$needle" "$out" || { printf 'FAIL: expected message %q for %s\n' "$needle" "$dir" >&2; cat "$out" >&2; exit 1; }
}

# 1. 何も問題の無いリポジトリは通過する
new_repo "$tmp/clean"
bash "$checker" --root "$tmp/clean" | grep -qF 'PASS: check-layout'

# 2. 追跡禁止ファイル
new_repo "$tmp/forbidden"
printf 'x\n' > "$tmp/forbidden/TNX.txt"
git -C "$tmp/forbidden" add TNX.txt && git -C "$tmp/forbidden" commit -q -m add
expect_fail_with "$tmp/forbidden" 'forbidden tracked files'

# 3. 行き先の無い追跡 symlink
new_repo "$tmp/symlink"
ln -s missing-target "$tmp/symlink/link"
git -C "$tmp/symlink" add link && git -C "$tmp/symlink" commit -q -m link
expect_fail_with "$tmp/symlink" 'dangling tracked symlinks'

# 4. 追跡中かつ ignore 対象
new_repo "$tmp/ignored"
printf 'secret.txt\n' > "$tmp/ignored/.gitignore"
printf 's\n' > "$tmp/ignored/secret.txt"
git -C "$tmp/ignored" add -f .gitignore secret.txt && git -C "$tmp/ignored" commit -q -m ignored
expect_fail_with "$tmp/ignored" 'tracked but ignored'

# 5. 不正な引数は 64
if bash "$checker" --bogus > /dev/null 2>&1; then
  printf 'FAIL: bogus argument accepted\n' >&2; exit 1
fi

# 6. このリポジトリ自身が通過する
bash "$checker" | grep -qF 'PASS: check-layout'

printf 'PASS: check-layout script behaves as specified\n'
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign
chmod +x "$W/tests/scripts/test-check-layout.bash"
bash "$W/tests/scripts/test-check-layout.bash"
```

Expected: `scripts/check-layout.sh: No such file or directory` で失敗する。

- [ ] **Step 3: スクリプトを書く**

`$W/scripts/check-layout.sh`:

```bash
#!/bin/bash
# リポジトリのレイアウト検査。仕様: docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md 9.1 節
# 使い方: scripts/check-layout.sh [--root DIR]
set -euo pipefail

usage() {
  printf 'usage: %s [--root DIR]\n' "${BASH_SOURCE[0]}" >&2
  exit 64
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(git -C "$script_dir" rev-parse --show-toplevel)"
while [ $# -gt 0 ]; do
  case "$1" in
    --root)
      [ $# -ge 2 ] || usage
      root="$(cd "$2" && pwd)"
      shift 2
      ;;
    *) usage ;;
  esac
done
cd "$root"

failures=0
fail() { failures=$((failures + 1)); printf 'FAIL: %s\n' "$1" >&2; }
ok() { printf 'ok: %s\n' "$1"; }

# 1. 追跡してはいけないファイル（仕様 9.1）
check_forbidden_tracked() {
  local pattern='(^|/)(ATS|BTD|TNX)\.txt$|(^|/)\.claude/settings\.local\.json$|\.blend1$|\.blend2$|\.orig$|\.rej$|(^|/)__pycache__/|(^|/)\.venv/'
  local hits
  hits="$(git ls-files | grep -E "$pattern" || true)"
  if [ -n "$hits" ]; then
    fail "forbidden tracked files: $(printf '%s' "$hits" | tr '\n' ' ')"
  else
    ok "no forbidden tracked files"
  fi
}

# 2. 追跡中の symlink がすべて解決できる
check_symlinks_resolve() {
  local broken=() mode _obj _stage path
  while read -r mode _obj _stage path; do
    [ "$mode" = 120000 ] || continue
    [ -e "$path" ] || broken+=("$path")
  done < <(git ls-files -s)
  if [ ${#broken[@]} -gt 0 ]; then
    fail "dangling tracked symlinks: ${broken[*]}"
  else
    ok "tracked symlinks resolve"
  fi
}

# 3. 追跡中かつ ignore 対象は既知の例外だけ
check_tracked_ignored() {
  local allow='MyResoniteProject/.resoloop/tokyo-nova/pipeline.json'
  local hits
  hits="$(git ls-files -i -c --exclude-standard | grep -vxF "$allow" || true)"
  if [ -n "$hits" ]; then
    fail "tracked but ignored: $(printf '%s' "$hits" | tr '\n' ' ')"
  else
    ok "no unexpected tracked-but-ignored files"
  fi
}

check_forbidden_tracked
check_symlinks_resolve
check_tracked_ignored

if [ "$failures" -gt 0 ]; then
  printf 'FAIL: check-layout (%d failure(s))\n' "$failures" >&2
  exit 1
fi
printf 'PASS: check-layout\n'
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
chmod +x "$W/scripts/check-layout.sh"
bash "$W/tests/scripts/test-check-layout.bash"
bash "$W/scripts/check-layout.sh"
```

Expected: `PASS: check-layout script behaves as specified` と、実リポジトリで `ok:` 3 行の後に `PASS: check-layout`。

- [ ] **Step 5: コミット（実行権付き）**

```bash
cd "$W"
git add scripts/check-layout.sh tests/scripts/test-check-layout.bash
git update-index --chmod=+x scripts/check-layout.sh tests/scripts/test-check-layout.bash
git ls-files -s scripts/check-layout.sh tests/scripts/test-check-layout.bash | awk '{print $1, $4}'   # 両方 100755
git commit -q -m "feat: add scripts/check-layout.sh with tracking-policy checks

First three checks from spec 9.1: forbidden tracked files, dangling
tracked symlinks and tracked-but-ignored files. Later phases append the
project layout, lock and devcontainer consistency checks.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: メイン作業ツリーの未追跡ファイルの整理と統合メモ

**Files:**
- Move (ファイルシステムのみ、`$M`): `MyResoniteProject/{ATS,BTD,TNX}.txt` → `private/trpg/`
- Delete (`$M`): 空ディレクトリ `tools/`
- Create (`$W`): `docs/integration.md`

**Interfaces:**
- Produces: TRPG 本文が `git add` の射程外に出た状態と、マージ後の手順を記す `docs/integration.md`（フェーズ 6 で完成させる）

- [ ] **Step 1: 対象が未追跡で、`tmp/` の複製と同一であることを確認する**

```bash
export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign
cd "$M"
git ls-files --error-unmatch MyResoniteProject/ATS.txt MyResoniteProject/BTD.txt MyResoniteProject/TNX.txt 2>&1 | grep -c 'did not match' # 3
md5sum MyResoniteProject/ATS.txt tmp/ATS.txt MyResoniteProject/BTD.txt tmp/BTD.txt MyResoniteProject/TNX.txt tmp/TNX.txt
find tools -mindepth 1 | wc -l    # 0
```

Expected: 3、各ペアの md5 が一致、`tools` は空。

- [ ] **Step 2: 移動と削除を行う**

```bash
mkdir -p "$M/private/trpg"
mv "$M/MyResoniteProject/ATS.txt" "$M/MyResoniteProject/BTD.txt" "$M/MyResoniteProject/TNX.txt" "$M/private/trpg/"
rmdir "$M/tools"
git -C "$M" status --short | grep -E 'ATS|BTD|TNX' || echo "trpg texts no longer visible to git"
ls "$M/private/trpg"
```

Expected: `trpg texts no longer visible to git`（`private/` は現行の .gitignore では ignore されないため、`?? private/` と出るのは正常。マージ後に ignore される）。

- [ ] **Step 3: 統合メモを書く**

`$W/docs/integration.md`:

```markdown
# 再設計の統合手順

仕様: `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md` 10.1 節。フェーズ 6 で完成させる。ここには各フェーズで実施した「メイン作業ツリー側の操作」と、マージ後に必要な手順を積み上げる。

## フェーズ 0 で実施したこと

- `origin` を https://github.com/usaturn/create-reso-world.git に設定し、`main`（feat/slum02-slum の HEAD へ fast-forward 済み）、`feat/slum02-slum`、`feat/tokyo-nova-world`、`chore/repo-redesign` を push した。
- tokyo-nova の未コミット変更（変更 12 件、新規 6 件）を `wip/tokyo-nova-refinement` にコミットして push した。作業ツリーの内容は変えていない。`content/tokyo-nova/layout.json` は `modeling/tokyo_nova/layout.py` より古い生成物なので、作業再開時に再生成が必要。

## フェーズ 1 で実施したこと（メイン作業ツリー）

- `MyResoniteProject/ATS.txt`、`BTD.txt`、`TNX.txt` を `private/trpg/` へ移動した（`tmp/` の同一コピーはそのまま）。`tokyo_nova_resoloop_world_prompt.md` は本文中で名前に触れるだけなので変更していない。
- 空の `tools/` を削除した。
- `.git/info/exclude` から存在しない `.devin/mcp_config.local.json` の行を外した（同じ規則はルート `.gitignore` に移した）。

## マージ後にユーザが行うこと（随時追記）

1. `git -C /workspaces/reso-world fetch origin` の後、`feat/slum02-slum` を `origin/main` に rebase するか ff-merge する。
2. `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更は新設計に取り込み済みなので `git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄してよい。`.claude/settings.local.json` はマージで削除されるので、マージの前に退避してマージ後に書き戻す（この雛形は古い。現行の手順は `docs/integration.md`。フェーズ 6 で注記）。
3. `MyResoniteProject/modeling/tokyo_nova/layout.py.orig` は新しい `.gitignore` で見えなくなる。不要なら削除する。
```

- [ ] **Step 4: コミット**

```bash
git -C "$W" add docs/integration.md
git -C "$W" commit -q -m "docs: start the integration notes for the repository redesign

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: フェーズ 1 の検証と push

- [ ] **Step 1: リポジトリ側の検査をすべて実行する**

```bash
export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign
cd "$W"
bash tests/scripts/test-gitignore.bash
bash tests/scripts/test-check-layout.bash
bash scripts/check-layout.sh
for t in .devcontainer/test-*.bash; do bash "$t" > /dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done
uv run pytest .agents/skills -q 2>&1 | tail -n 1
```

Expected: 3 つの検査が PASS。Dev Container テストは 8 本 PASS、`test-herdr-migration` だけ FAIL。スキルテストはベースラインと同じ `37 failed, 169 passed`（フェーズ 1 ではスキルに触れないため。数が違えば原因を報告する）。

- [ ] **Step 2: 作業ツリーがきれいで、コミット数が期待どおりであることを確認する**

```bash
git -C "$W" status --short | wc -l        # 0
git -C "$W" log --oneline main..HEAD | wc -l   # 10（文書コミット 3 件 + 本計画の 7 コミット）
```

- [ ] **Step 3: push する**

```bash
git -C "$W" push origin chore/repo-redesign
git -C "$M" ls-remote --heads origin
```

Expected: `chore/repo-redesign` が更新され、リモートブランチは 5 本。

- [ ] **Step 4: 報告**

着手から完了までの所要時間と Task 別の内訳、ベースラインとの差分（Dev Container テスト 4→8 PASS、スキルテストは不変）、メイン作業ツリーで行った操作（Task 9）を報告する。
