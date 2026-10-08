# Issue #57 ローカルワールド化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4 つのワールドプロジェクトを Git の管理外にし、新規ワールドの作る場所を `worlds/` に定めて、検出・検査・規約をその前提に更新する。

**Architecture:** `.gitignore` で `/worlds/` と 4 名を除外し `git rm -r --cached` で追跡を外す。プロジェクト検出は git の index から外して「`worlds/` の直下 + 移行済み 4 名」の作業ツリー走査に統一し、`new-world.sh`・`check-layout.sh`・`report-resoloop-skills.bash` とテストを揃える。

**Tech Stack:** Bash、Git、uv / pytest。

**Spec:** `docs/superpowers/specs/2026-10-08-issue-57-local-worlds-design.md`

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`、Issue #57
- 状態: completed（実行許可に基づき全 Task 実施・検証済み。内容の承認は PR #58 のレビューで受ける）
- 基準 HEAD: `f3bc010847a6bde9ee9b4705e20d843337ce3c2f`
- 関連 PR: https://github.com/usaturn/create-reso-world/pull/58
- 実行方法: executing-plans（controller が直列に実行）
- 実行許可: 利用者の「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」。内容の承認とは区別する。マージは含まない
- 検証: `bash .devcontainer/run-tests.bash` PASS（28 本）、`bash scripts/check-layout.sh` PASS、`uv run pytest tests/skills .agents/skills` PASS（475 件）、`git diff --check` clean

## Global Constraints

- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-57-local-worlds`（ブランチ `feat/issue-57-local-worlds`）。PARENT_ROOT: `/workspaces/reso-world`（基準 HEAD の detached checkout。編集しない）
- 作業領域の定義（D-5）: `worlds/` の直下のディレクトリと、ルート直下の `MyResoniteProject`・`akichi`・`slum02`・`slum03`。`external/`・`private/`・worktree・2 階層以上は走査しない。`.resoloop.json` があればプロジェクト
- ルートを指す symlink の深さ（D-9）: 深さ n のプロジェクトの `.pi` は `'../'×n + .pi`、`.claude/settings.json` と `.agents/sp-*.md` は `'../'×(n+1)` + 対象。`.claude/skills/<name> -> ../../.agents/skills/<name>` は深さに依存しない
- Python は uv で実行する。シェル変数を使う `rm` は `${VAR:?}` で守り、パス全体を引用する
- PARENT_ROOT の 4 ディレクトリには未コミット変更と未追跡ファイルがある。PARENT_ROOT では `git rm`・`git checkout`・`git clean` を実行しない
- 完了した文書・過去の Spec・Plan は書き換えも削除もしない

## 各 Task 共通のテスト要否

挙動を変えるスクリプトの Task（1〜4）は、その変更を確かめる実行テストを同じファイルで更新・追加する。Task 5（文書）はテストを書かず、`test-instructions.bash` など既存の構造検査と `git diff` で代える。

## Review Focus

1. `worlds/` 以外の場所（ルート直下の任意名、`external/`、worktree 内）をプロジェクトとして誤検出する → Task 3・4 の検出テストが拒否を確かめる
2. 深さの違うプロジェクトで symlink の行き先を 1 段ずらす → Task 2・3 が `worlds/`（深さ 2）とルート直下（深さ 1）の両方で行き先を検査する
3. `.gitignore` の除外だけして追跡解除を忘れる、または逆に実ファイルを消す → Task 1 が index 0 件と実ファイルの残存を確かめる
4. ローカルプロジェクトが無い新規 clone で検査やセットアップが壊れる → Task 3・4 が 0 件時の通過を確かめる
5. `resoloop` に `./` なしや絶対パスで渡して `-` 始まりの名前や別リポジトリを読ませる → Task 3・4 が `./worlds/x`・`./akichi` の形を固定する

---

### Task 1: `.gitignore` と追跡解除

**Files:**
- Modify: `.gitignore`
- Modify: `tests/scripts/test-gitignore.bash`
- Index: `MyResoniteProject/`・`akichi/`・`slum02/`・`slum03/` の追跡解除

**Interfaces:**
- Produces: `worlds/` と 4 名が ignore の作業領域。以降の Task が前提にする検出対象

**テストの要否:** 要る。ignore 規則の適用と追跡解除の実効は実行して確かめる挙動である。

- [x] **Step 1: `test-gitignore.bash` を新方針に書き換える**
  - ignored に加える: `worlds/demo/.resoloop.json`、`worlds/demo/modeling/x.py`、4 名の配下（例: `akichi/x.py`）
  - not ignored に残す: `scripts/new-world.sh`、`templates/world-project/CLAUDE.md`、`docs/worlds/tokyo-nova/tokyo-nova-assets.rst` など共通側。`slum02/.resoloop/.gitignore`・`slum02/assets/...` など 4 名の配下の項目は消す（全体が ignore になるため区別できない）
  - 汎用規則（`**/.resoloop/**`、`*.blend1`、`tmp/`、`docs_draft/`、秘密情報）は従来どおり ignored
  - 末尾の tracked-but-ignored 照合は「空であること」に変える（pipeline.json の例外は無くなる）
- [x] **Step 2: `.gitignore` を更新して追跡解除する**
  - 追加: `/MyResoniteProject/`・`/akichi/`・`/slum02/`・`/slum03/`・`/worlds/`（「ワールドはローカル作業物」の旨のコメント付き）
  - 削除: `MyResoniteProject/content/tokyo-nova/` の 2 行の個別除外
  - 実行: `git rm -r --cached --quiet MyResoniteProject akichi slum02 slum03`
  - 実ファイルの残存: `test -d MyResoniteProject && git status --porcelain | grep -c '^??' ` が 0 であること（ignore 済みなので `??` は出ない）
- [x] **Step 3: テスト実行**
  Run: `bash tests/scripts/test-gitignore.bash`、`bash scripts/check-layout.sh`
  Expected: PASS（check-layout はこの時点でも通る。プロジェクト検出が 0 件になるだけ）
- [x] **Step 4: コミット**
  `chore: untrack world projects and ignore local world areas (issue 57)`

### Task 2: `scripts/new-world.sh`

**Files:**
- Modify: `scripts/new-world.sh`
- Modify: `tests/scripts/test-new-world.bash`

**Interfaces:**
- Consumes: Task 1 の作業領域の定義
- Produces: 作成先の解決（`worlds/<name>` 優先・legacy 名の `--apply`）、深さ対応の symlink 行き先

**テストの要否:** 要る。作成・適用・拒否の分岐と symlink の行き先は実行して確かめる。

- [x] **Step 1: `test-new-world.bash` を新仕様に合わせる**
  - プロジェクトの期待位置を `$r/worlds/demo` に変え、`.claude/settings.json` -> `../../../.claude/settings.json`、`.pi` -> `../../.pi`、`.agents/sp-implementer.md` -> `../../../.agents/sp-implementer.md`、`.claude/skills/<n>` -> `../../.agents/skills/<n>` を確かめる
  - 旧ケース 19（ignore 名の拒否）を次に替える: 名前 `worlds` は 2 で拒否。ルート直下に同名のファイル・ディレクトリがあるとき新規作成は 2
  - 追加: ルート直下の `akichi` 相当（雛形不足の resoloop プロジェクト）への `--apply` が深さ 1 の行き先で通る。`worlds/demo` とルート直下 `demo` の両方がある `--apply` は 2（曖昧さ）
- [x] **Step 2: テストが現仕様で失敗することを確認**
  Run: `bash tests/scripts/test-new-world.bash`
  Expected: FAIL（`worlds/` への作成や深さ 2 の行き先が未実装）
- [x] **Step 3: `new-world.sh` を実装する**
  - `git check-ignore` による拒否を削除。予約名 `worlds` を 2 で拒否。`$root/worlds` が存在してディレクトリでなければ（dangling symlink も含む）3 で拒否
  - 作成先 `$root/worlds/<name>`。`--apply` は `worlds/<name>` を優先し、無ければルート直下 `<name>`。両方あれば 2。新規作成はどちらかの存在で 2
  - `resoloop init` の前に `mkdir -p "$root/worlds"`
  - `proj` の `$root` 相対の深さ n を求め、`.pi` は `'../'×n + .pi`、`.claude/settings.json` と `.agents/sp-*.md` は `'../'×(n+1)` + 対象名にする
  - ヘッダーの終了コード 2 の説明と usage を新仕様に合わせる
- [x] **Step 4: テスト実行**
  Run: `bash tests/scripts/test-new-world.bash`
  Expected: PASS
- [x] **Step 5: コミット**
  `feat: create new worlds under untracked worlds/ (issue 57)`

### Task 3: `scripts/check-layout.sh`

**Files:**
- Modify: `scripts/check-layout.sh`
- Modify: `tests/scripts/test-check-layout.bash`

**Interfaces:**
- Consumes: Task 1 の作業領域の定義、Task 2 と同じ深さの行き先規則
- Produces: `collect_projects`（作業ツリー走査）、`check_project`（作業ツリー検査）、`check_work_areas_untracked`（新規）、`check_local_skill_links`（作業ツリー版）

**テストの要否:** 要る。検出・検査・追跡混入の検出は実行して確かめる。

- [x] **Step 1: `test-check-layout.bash` を新仕様に合わせる**
  - `project_repo` は `worlds/<name>` にプロジェクトを作り、追跡は `.gitignore`（`/worlds/`）のある共通側だけにする。期待する symlink の行き先は深さ 2
  - 追加: ルート直下の `akichi`（4 名の 1 つ）もプロジェクトとして検出される。ルート直下の任意名 `demo` や `worlds/demo/sub` のような深い場所は対象外。プロジェクト 0 件でも PASS
  - 追加: 作業領域に追跡ファイルを置くと失敗する（`git add -f worlds/demo/x` → FAIL）
  - resoloop の呼び出しは `./worlds/demo` の形を確かめる
  - 従来の逸脱ケース（CLAUDE.md・AGENTS.md・`cache/`・行き先違い・1:1 対応）はそのまま作業ツリーで確かめる
- [x] **Step 2: テストが現仕様で失敗することを確認**
  Run: `bash tests/scripts/test-check-layout.bash`
  Expected: FAIL（`worlds/` の検出と作業ツリー検査が未実装）
- [x] **Step 3: `check-layout.sh` を実装する**
  - `collect_projects` を「`worlds/*/` と 4 名のうち `.resoloop.json` を持つディレクトリ」の作業ツリー走査に変え、LC_ALL=C でソートする。`.devcontainer/report-resoloop-skills.bash` と同じ定義であることをコメントで相互参照する
  - `check_project` を作業ツリー版に書き換える。必須ファイルは「symlink でない通常ファイル」、CLAUDE.md・AGENTS.md・`cache/` の中身、symlink の行き先（深さ n: `.pi` は `'../'×n`、`.claude/settings.json`・`.agents/sp-*` は `'../'×(n+1)`）。`.claude/skills` の 1:1 対応は `check_local_skill_links`（ファイルを 1 つ以上持つ `.agents/skills` の直下ディレクトリ、dotglob 込み）
  - `check_tracked_ignored` の許可リストを削除する
  - `check_work_areas_untracked` を追加する（`worlds/` と 4 名の下に追跡ファイルが無いこと）
  - ルートの `check_skill_links ""` と他の index 検査は変えない
- [x] **Step 4: テスト実行**
  Run: `bash tests/scripts/test-check-layout.bash`、`bash scripts/check-layout.sh`
  Expected: PASS
- [x] **Step 5: コミット**
  `feat: check local world projects on the worktree (issue 57)`

### Task 4: `.devcontainer/report-resoloop-skills.bash`

**Files:**
- Modify: `.devcontainer/report-resoloop-skills.bash`
- Modify: `.devcontainer/test-report-resoloop-skills.bash`

**Interfaces:**
- Consumes: Task 3 の `collect_projects` と同じ作業領域の定義

**テストの要否:** 要る。検出の対象と resoloop への渡し方を実行して確かめる。

- [x] **Step 1: `test-report-resoloop-skills.bash` を新仕様に合わせる**
  - プロジェクトを `worlds/ok`・`worlds/stale`・`worlds/edited`・`worlds/-dash` とルート直下の `akichi` にする。`worlds/deep/sub`（深い）とルート直下の `loose`（作業領域外）は対象外
  - git への追加・コミットなしで検出されることを確かめる（追跡状態に依存しない）
  - resoloop の呼び出しは `./worlds/ok`・`./akichi` の形を確かめる
- [x] **Step 2: `report-resoloop-skills.bash` を実装する**
  - `git ls-files` の検出を Task 3 と同じ作業ツリー走査に変え、git への依存を外す。`cd` の失敗は従来どおり skip メッセージにする
- [x] **Step 3: テスト実行**
  Run: `bash .devcontainer/test-report-resoloop-skills.bash`
  Expected: PASS
- [x] **Step 4: コミット**
  `feat: detect local world projects without git index (issue 57)`

### Task 5: 規約・文書

**Files:**
- Modify: `AGENTS.md`、`README.md`、`.devcontainer/README.md`

**テストの要否:** なし。文書だけの変更で、守る実行時の挙動が無い。代わりの検証: `bash tests/scripts/test-instructions.bash`、`bash tests/scripts/test-docs.bash`（存在すれば）、`git diff` で対象箇所だけの変更であること。

- [x] **Step 1: `AGENTS.md` を更新する**
  - リポジトリ概要: プロジェクトを同じリポジトリで追跡する説明を、「ワールドはローカル作業物で追跡しない。作る場所は `worlds/` と既存の 4 名」に変える
  - プロジェクト運用: `new-world.sh` が `worlds/<name>` を作ること、`--apply` が 4 名の従来位置も対象にすること、ワールド作業に branch・commit・PR を要求しないこと、`git clean -fdx` で消えることを書く
- [x] **Step 2: `README.md` を更新する**
  - 構成ツリーと「プロジェクトを作る」を新仕様にし、専用リポジトリを選ぶ条件（履歴管理・再現性・共同開発が要るとき）と、プロジェクトの symlink はリポジトリの共有物を指すのでそのまま持ち出せない注意を書く。別 checkout への取り込みは README「追跡解除コミットを取り込む」の保全手順を使う。事前の `git rm --cached` だけでは取り込めず、コミット・stash だけでは実ファイルが残らないことは、Spec の PR #58 レビュー修正の記録に従って訂正する
- [x] **Step 3: `.devcontainer/README.md` を更新する**
  - テスト実行のプロジェクト例と `report-resoloop-skills` の説明を新仕様に合わせる
- [x] **Step 4: 検証**
  Run: `bash tests/scripts/test-instructions.bash`、`bash tests/scripts/test-docs.bash`、`git diff --check`
  Expected: PASS
- [x] **Step 5: コミット**
  `docs: describe local world projects (issue 57)`

### Task 6: 検証と PR

- [x] **Step 1: 全体検証**
  Run: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills`、`git diff --check origin/main...HEAD`
  Expected: すべて PASS
- [x] **Step 2: Spec・Plan の確認用コピー**
  `scripts/superpowers-review-copy.sh` で PARENT_ROOT の `tmp/superpowers-review/` へ `issue-57-local-worlds-spec.md`・`issue-57-local-worlds-plan.md` としてコピーし、PARENT_ROOT の `docs_draft/superpowers/specs/`・`docs_draft/superpowers/plan/` にも置く
- [x] **Step 3: Spec・Plan の状態を更新してコミット**
  検証結果と PR 番号を記録する。`approved` にはしない
- [x] **Step 4: push と PR 作成**
  `git push -u origin feat/issue-57-local-worlds` の後、`gh pr create` で `Refs #57` の PR を作る。本文に Issue の完了条件との対応と、別 checkout での取り込み時の保全確認を書く
