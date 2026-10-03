# Superpowers Spec・Plan 保存運用 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 日付: 2026-10-03
- 状態: approved（Spec と同じ 2026-10-03 のユーザ指示により、レビュー待ちで止まらずに実行する。実行方法は Native）
- 文書管理リポジトリ: `usaturn/create-reso-world`
- 設計・実装対象リポジトリ: `usaturn/create-reso-world`
- 対象 Issue・PR: なし（Task 9 で PR を作成する）
- 作業 worktree: `/workspaces/reso-world/.worktrees/superpowers-document-lifecycle`（branch `docs/superpowers-document-lifecycle`、base は main `9b0d47d`）

**Goal:** どのリポジトリの作業でも Spec・Plan を create-reso-world に保存・コミットし、確認用コピーと公開の手順を規約・スキル・補助スクリプトとして整え、既存の未追跡文書 22 件を取り込む。

**Architecture:** 確認用コピーの作成と検証は、新しい `scripts/superpowers-review-copy.sh` に集約し、`AGENTS.md` と各スキルはこのスクリプトを呼ぶように書く。任意リポジトリの対象 checkout は、ユーザが明示した `CODE_ROOT` だけを使い、その checkout 自身の toplevel であることと remote の一致を照合する。規約・スキルの変更は、既存の契約テスト（pytest と tests/scripts の bash）を先に書き換えてから本文を直す。

**Tech Stack:** bash、git、pytest（`uv run`）、Markdown

**Spec:** `docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-design.md`

## Global Constraints

- Spec・Plan の正本の保存・コミット先は `usaturn/create-reso-world` だけ。対象リポジトリには置かない
- 確認用コピーは `PARENT_ROOT/tmp/superpowers-review/<内容が分かる短い名前>-spec.md` または `-plan.md`。親の `tmp/` 直下や追加の階層には置かない
- 確認用コピーは、コミット済みの blob から作る。Git の追跡対象にせず、`git add -f` しない
- Python は `uv run` で実行し、`python3` コマンドを使わない
- `AGENTS.md` の `## ` 節の並び（`tests/scripts/test-instructions.bash` の期待値）と、`README.md` の `## ` 節の並び（`tests/scripts/test-docs.bash` の期待値）を変えない。追加は `### ` 以下で行う
- `scripts/*.sh` と `tests/scripts/*.bash` は index 上で 100755 にする
- 既存文書の本文・パスを変えない。取り込みは Spec 第8.2節の 22 件だけで、1 件ずつステージする
- 退避先 `/workspaces/reso-world/docs_draft/untracked-main-20261003/` と親 checkout `/workspaces/reso-world` を変更しない（確認用コピーの `tmp/superpowers-review/` だけは例外）
- インストール済み Superpowers スキルを変更しない
- push と PR 作成は Task 9 だけで行う。マージはしない

## Review Focus

- `CODE_ROOT` に別リポジトリの checkout のサブディレクトリや、remote が対象と一致しない checkout を渡された場合は、推測せずに停止する（Task 3 のテスト）
- 別の作業で同じ名前の確認用コピーが既にある場合は、上書きせずに停止する（Task 1 のテスト）
- ユーザが確認用コピーを編集したあとで新しい版をコピーしようとした場合は、差し替えずに停止する（Task 1 のテスト）
- `tmp/` や `tmp/superpowers-review/` が symlink で外へ向いている場合は、何も書かずに停止する（Task 1 のテスト）
- 取り込み先に同名で内容の異なるファイルがある場合（main の `pr8-round2` など）は、上書きせずに停止する（Task 8 の照合）

---

## File Structure

| ファイル | 変更 | 責務 |
| --- | --- | --- |
| `scripts/superpowers-review-copy.sh` | 新規 | 確認用コピーの作成・検証（Spec 3.3） |
| `tests/scripts/test-superpowers-review-copy.bash` | 新規 | 上記スクリプトの回帰テスト（一時リポジトリで実行） |
| `tests/scripts/test-gitignore.bash` | 変更 | `tmp/superpowers-review/` が無視されることを追加で検査 |
| `AGENTS.md` | 変更 | 保存先・3 つのルート・確認用コピー・公開、リポジトリ境界の「それ以外」 |
| `tests/scripts/test-instructions.bash` | 変更 | AGENTS.md の新しい記述と参照先の実在を検査 |
| `docs/superpowers/README.md` | 新規 | 運用の簡潔な案内（Spec 7） |
| `README.md`・`tests/scripts/test-docs.bash` | 変更 | `docs/superpowers/README.md` への案内と、その検査 |
| `.agents/skills/pr-review/SKILL.md`・`tests/test_pr_review_skill_contract.py` | 変更 | 明示された `CODE_ROOT` の経路と照合 |
| `.agents/skills/review-fix-planning/SKILL.md`・`tests/test_review_fix_planning_skill_contract.py` | 変更 | 任意対象、Spec のコミット・確認用コピー・文書側の公開 |
| `.agents/skills/agent-handoff/SKILL.md`・`references/handoff-schema.md`・`tests/test_agent_handoff_skill_contract.py` | 変更 | 文書とコードの復元元、親 checkout、確認用コピーの記録 |
| `.agents/skills/planning-parallel-issues/SKILL.md`・`references/session-workflow.md`・`tests/test_planning_parallel_issues_contract.py` | 変更 | 任意対象の識別、文書の保存先、確認用コピー |
| `docs/superpowers/{specs,plans}/` の 22 件 | 追加 | Spec 8.2 の既存文書の取り込み |

---

### Task 1: 確認用コピーの補助スクリプト

**Files:**
- Create: `scripts/superpowers-review-copy.sh`
- Create: `tests/scripts/test-superpowers-review-copy.bash`
- Modify: `tests/scripts/test-gitignore.bash`（`expect_ignored` の一覧）

**Interfaces:**
- Produces: `bash scripts/superpowers-review-copy.sh --doc-root <DOC_ROOT> --parent-root <PARENT_ROOT> --path <docs/superpowers/{specs,plans}/*.md> --name <name>-{spec,plan}.md [--commit <rev>] [--replace-from <rev>]`
  - 成功（終了 0）: 1 行目 `created: tmp/superpowers-review/<name>`（または `unchanged:`・`replaced:`）、2 行目 `source: <path> at <40 桁の SHA>`、3 行目 `sha256: <hash>`
  - 拒否（終了 1）: `superpowers-review-copy: <理由>` を stderr に出し、コピー先を変更しない
  - 引数の誤り（終了 2）

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-superpowers-review-copy.bash` を次の内容で作る。

```bash
#!/bin/bash
# scripts/superpowers-review-copy.sh が確認用コピーを作り、危険な状態では何も書き換えずに止まることを一時リポジトリで検査する。
# 仕様: docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-design.md 3.3・10 節
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# ユーザの git 設定から隔離する（test-check-layout.bash と同じ）
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$root"
copier="$root/scripts/superpowers-review-copy.sh"
tmp="$(realpath "$(mktemp -d)")"
trap 'rm -rf "$tmp"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
origin=https://github.com/usaturn/create-reso-world.git
spec=docs/superpowers/specs/2026-10-03-sample-design.md
out="$tmp/out.txt"

# new_repo DIR [ORIGIN] [IGNORE]: create-reso-world に見立てた checkout を作る。既定では tmp/ を無視する
new_repo() {
  git init -q "$1"
  git -C "$1" config user.email test@example.com
  git -C "$1" config user.name test
  git -C "$1" remote add origin "${2:-$origin}"
  printf '%s\n' "${3-tmp/}" > "$1/.gitignore"
  mkdir -p "$1/docs/superpowers/specs" "$1/docs/superpowers/plans"
  printf '# sample v1\n' > "$1/$spec"
  git -C "$1" add .gitignore "$spec"
  git -C "$1" commit -q -m init
}

# run CODE NEEDLE ARGS...: 終了コードと出力の一部を確かめる。出力は $out に残す
run() {
  local expected="$1" needle="$2" code=0
  shift 2
  bash "$copier" "$@" > "$out" 2>&1 || code=$?
  [ "$code" -eq "$expected" ] || { cat "$out" >&2; fail "expected exit $expected, got $code: $*"; }
  grep -qF -- "$needle" "$out" || { cat "$out" >&2; fail "expected output '$needle': $*"; }
}

same_as() {   # same_as FILE REPO REV: FILE が REV の正本と同じバイト列である
  git -C "$2" show "$3:$spec" | cmp -s - "$1" || fail "$1 differs from $spec at $3"
}

parent="$tmp/parent"
new_repo "$parent"
doc="$tmp/doc"
git -C "$parent" worktree add -q -b docs/sample "$doc"
copy="$parent/tmp/superpowers-review/sample-doc-spec.md"
args=(--doc-root "$doc" --parent-root "$parent" --path "$spec")

# 1. コミット済みの正本からコピーを作り、コミット SHA とハッシュを表示する。親の status は変わらない
v1="$(git -C "$doc" rev-parse HEAD)"
run 0 'created: tmp/superpowers-review/sample-doc-spec.md' "${args[@]}" --name sample-doc-spec.md
grep -qxF "source: $spec at $v1" "$out" || fail 'source line'
grep -qxF "sha256: $(sha256sum "$copy" | cut -d' ' -f1)" "$out" || fail 'sha256 line'
same_as "$copy" "$doc" "$v1"
[ -z "$(git -C "$parent" status --porcelain)" ] || fail 'the copy must stay ignored and unstaged'

# 2. 同じ版をもう一度コピーしても書き換えない
run 0 'unchanged: tmp/superpowers-review/sample-doc-spec.md' "${args[@]}" --name sample-doc-spec.md

# 3. 未コミットの変更（作業ツリー、index）がある正本はコピーしない
printf '# sample dirty\n' > "$doc/$spec"
run 1 'commit it first' "${args[@]}" --name sample-doc-spec.md
git -C "$doc" add "$spec"
run 1 'commit it first' "${args[@]}" --name sample-doc-spec.md
git -C "$doc" reset -q --hard
same_as "$copy" "$doc" "$v1"

# 4. 新しい版は、確認済みの版を --replace-from で示した場合だけ差し替える
printf '# sample v2\n' > "$doc/$spec"
git -C "$doc" commit -q -am v2
v2="$(git -C "$doc" rev-parse HEAD)"
run 1 'already exists with other content' "${args[@]}" --name sample-doc-spec.md
same_as "$copy" "$doc" "$v1"
run 0 'replaced: tmp/superpowers-review/sample-doc-spec.md' "${args[@]}" --name sample-doc-spec.md --replace-from "$v1"
same_as "$copy" "$doc" "$v2"

# 5. ユーザが編集したコピーは差し替えない
printf 'user note\n' >> "$copy"
edited="$(cat "$copy")"
printf '# sample v3\n' > "$doc/$spec"
git -C "$doc" commit -q -am v3
run 1 'not replaced' "${args[@]}" --name sample-doc-spec.md --replace-from "$v2"
[ "$(cat "$copy")" = "$edited" ] || fail 'an edited copy was overwritten'

# 6. ファイル名と正本のパスの検査
run 1 'must be a short lowercase file name' "${args[@]}" --name spec.md
run 1 'must be a short lowercase file name' "${args[@]}" --name ../escape-spec.md
run 1 'but --path is a spec' "${args[@]}" --name sample-doc-plan.md
run 1 'must be docs/superpowers/specs/*.md' --doc-root "$doc" --parent-root "$parent" --path README.md --name readme-spec.md
run 1 'is not committed' --doc-root "$doc" --parent-root "$parent" --path docs/superpowers/specs/missing.md --name missing-spec.md
run 2 'usage' "${args[@]}"

# 7. コピー先が symlink のときは書かない
mkdir -p "$tmp/outside"
ln -s "$tmp/outside/target.md" "$parent/tmp/superpowers-review/link-doc-spec.md"
run 1 'is a symlink' "${args[@]}" --name link-doc-spec.md
[ ! -e "$tmp/outside/target.md" ] || fail 'wrote through a symlinked copy'

# 8. tmp/superpowers-review/ が外を指す symlink なら書かない
linked="$tmp/linked"
new_repo "$linked"
mkdir -p "$linked/tmp" "$tmp/elsewhere"
ln -s "$tmp/elsewhere" "$linked/tmp/superpowers-review"
run 1 'is a symlink' --doc-root "$linked" --parent-root "$linked" --path "$spec" --name sample-doc-spec.md
[ -z "$(ls -A "$tmp/elsewhere")" ] || fail 'wrote through a symlinked review directory'

# 9. コピー先が ignore 対象でない親には書かない
unignored="$tmp/unignored"
new_repo "$unignored" "$origin" 'nothing-ignored/'
run 1 'is not ignored' --doc-root "$unignored" --parent-root "$unignored" --path "$spec" --name sample-doc-spec.md
[ ! -e "$unignored/tmp/superpowers-review" ] || fail 'created a review directory in an unignored parent'

# 10. checkout の検査: origin、親が worktree でないこと、絶対パス、checkout のルート
foreign="$tmp/foreign"
new_repo "$foreign" https://github.com/someone/other.git
run 1 'origin is not usaturn/create-reso-world' --doc-root "$foreign" --parent-root "$parent" --path "$spec" --name foreign-doc-spec.md
run 1 'must be the main checkout' "${args[@]}" --parent-root "$doc" --name sample-doc-spec.md
run 1 'must be an absolute path' --doc-root doc --parent-root "$parent" --path "$spec" --name sample-doc-spec.md
run 1 'is not the root of its checkout' --doc-root "$doc/docs" --parent-root "$parent" --path "$spec" --name sample-doc-spec.md

printf 'PASS: superpowers-review-copy copies committed documents and refuses unsafe targets\n'
```

`tests/scripts/test-gitignore.bash` の `expect_ignored` の一覧で、`.claude/worktrees/x/README.md .superpowers/sdd/x.log \` の行の後に次の行を足す。

```bash
  tmp/superpowers-review/x-spec.md \
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `chmod +x tests/scripts/test-superpowers-review-copy.bash && bash tests/scripts/test-superpowers-review-copy.bash`
Expected: FAIL（`scripts/superpowers-review-copy.sh` が無いため、ケース 1 で `expected exit 0, got 127`）

Run: `bash tests/scripts/test-gitignore.bash`
Expected: PASS（`.gitignore` の `tmp/` で既に無視されている。回帰の固定のための追加）

- [ ] **Step 3: スクリプトを書く**

`scripts/superpowers-review-copy.sh` を次の内容で作り、`chmod +x` する。

```bash
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
    -e 's#^git@github[.]com:([^/]+/[^/#?]+)([.]git)?$#\1#p' | sed 's/[.]git$//'
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
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash tests/scripts/test-superpowers-review-copy.bash && bash tests/scripts/test-gitignore.bash`
Expected: 両方 PASS

Run: `bash .devcontainer/run-tests.bash tests/scripts/test-file-modes.bash`
Expected: FAIL（新しい 2 ファイルが index に無いか 100644）。Step 5 で `git add --chmod=+x` してから再実行し PASS

- [ ] **Step 5: コミット**

```bash
git add --chmod=+x scripts/superpowers-review-copy.sh tests/scripts/test-superpowers-review-copy.bash
git add tests/scripts/test-gitignore.bash
bash .devcontainer/run-tests.bash tests/scripts/test-file-modes.bash
git commit -m "feat: add the Superpowers review-copy helper"
```

---

### Task 2: AGENTS.md の規約と案内文書

**Files:**
- Modify: `AGENTS.md`（`## ファイルとドラフト` と `## リポジトリ境界`）
- Create: `docs/superpowers/README.md`
- Modify: `README.md:71`
- Modify: `tests/scripts/test-instructions.bash`、`tests/scripts/test-docs.bash`

**Interfaces:**
- Consumes: Task 1 の `scripts/superpowers-review-copy.sh` とその引数
- Produces: `PARENT_ROOT`・`DOC_ROOT`・`CODE_ROOT` の定義と、リポジトリ境界の「それ以外」の行（Task 3〜6 のスキルが参照する）

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-instructions.bash` の「メイン作業ツリーの未コミット変更」の `for` の後に次を足す。

```bash
# Spec・Plan の保存と公開（仕様 2026-10-03-superpowers-document-lifecycle 3・6・9 節）
for s in '### Spec・Plan の保存と公開' 'PARENT_ROOT' 'DOC_ROOT' 'CODE_ROOT' 'tmp/superpowers-review/' \
  'scripts/superpowers-review-copy.sh' 'docs/superpowers/README.md' '文書専用 PR' '公開未実施'; do
  has AGENTS.md "$s"
done
boundary="$(sed -n '/^## リポジトリ境界$/,/^## ResoLoop の版管理$/p' AGENTS.md)"
other_row="$(grep -F '| それ以外 |' <<<"$boundary")" || fail 'AGENTS.md boundary table lacks the other-repository row'
for s in '`CODE_ROOT`' 'remote' '推測せず停止する' '`pr-review`' '`review-fix-planning`'; do
  [[ "$other_row" == *"$s"* ]] || fail "the other-repository row lacks: $s"
done
```

同じファイルの「AGENTS.md が参照するファイルが実在する」の `for f in` の一覧に `scripts/superpowers-review-copy.sh docs/superpowers/README.md` を足す。

`tests/scripts/test-docs.bash` の「README.md が案内するファイルは実在する」の一覧（`.agents/sp-implementer.md` の前）に `docs/superpowers/README.md` を足す。

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash tests/scripts/test-instructions.bash; bash tests/scripts/test-docs.bash`
Expected: FAIL（`AGENTS.md lacks: ### Spec・Plan の保存と公開`、`README.md lacks: docs/superpowers/README.md`）

- [ ] **Step 3: AGENTS.md を書く**

`## ファイルとドラフト` の最後の箇条書き（`- リポジトリに残す文書は docs/ に置く。…`）の後に、次の小節を足す。

```markdown
### Spec・Plan の保存と公開

- どのリポジトリの作業でも、Spec・Plan の正本は `usaturn/create-reso-world` の `docs/superpowers/` に保存してコミットする。ResoLoop や無関係なリポジトリの作業でも、対象リポジトリには置かず、二重管理もしない。運用の要点は `docs/superpowers/README.md` にある
- 作業先は 3 つを区別する。`PARENT_ROOT` はユーザが確認用ファイルを読む create-reso-world の親 checkout、`DOC_ROOT` は正本をコミットする create-reso-world の checkout または worktree、`CODE_ROOT` はユーザの依頼または確認済みの引き継ぎで明示された、コード対象の checkout の絶対パスである。コード対象の cwd の `git rev-parse --show-toplevel` を、`DOC_ROOT` や `PARENT_ROOT` とみなさない
- 文書を create-reso-world に集めることは、他のリポジトリのコード変更・clone・push・PR 作成の許可ではない。対象 checkout の `AGENTS.md` 等も守る
- 正式な Spec・Plan は、承認前でも `draft` のまま `DOC_ROOT` の作業ブランチにコミットする。状態は `draft`・`approved`・`completed`・`superseded`・`cancelled` で書き、コミットしただけで `approved` にしない。同じテーマのレビュー修正は既存の文書を更新し、過去の版は Git の履歴に残す。完了した文書も削除しない
- ユーザに Spec・Plan の確認を依頼する前に、コミット済みの版を `scripts/superpowers-review-copy.sh` で `PARENT_ROOT` の `tmp/superpowers-review/` へコピーし、コピー先・文書のコミット SHA・正本のパスを示す。ファイル名は内容が分かる短い名前に `-spec.md` か `-plan.md` を付け、関連する Issue・PR があれば `<repo>-pr<N>-` のように番号を含める。番号を発明しない。確認中のコピーを差し替えるときは、確認済みの版を `--replace-from` で示す
- 公開: create-reso-world 自身の変更に伴う文書は、その作業の PR に含める。他のリポジトリの変更に伴う文書は、create-reso-world の文書用ブランチから、テーマごとに 1 つの文書専用 PR で公開する。コミット・push・PR 作成・マージは別の段階であり、ユーザまたは使っているワークフローの明示指示があるときだけ行う。ローカルのコミットだけのときは、報告と handoff に「公開未実施」と書く
```

`## リポジトリ境界` の表の最後の行（`| それ以外 | 推測せず停止する | — |`）を次の行に置き換える。

```markdown
| それ以外 | ユーザの依頼または確認済みの引き継ぎで明示された checkout の絶対パス（`CODE_ROOT`） | その checkout 自身のルートであり、remote のうち 1 つだけが対象の owner/repo と一致すること。明示が無い・一致しない・候補が複数ある場合は推測せず停止する。この経路を持つのは `pr-review` と `review-fix-planning` だけで、他の作業は推測せず停止する。checkout の探索・clone はしない |
```

- [ ] **Step 4: docs/superpowers/README.md と README.md を書く**

`docs/superpowers/README.md` を次の内容で作る。

````markdown
# Superpowers の Spec・Plan

この下には、Superpowers のスキル（brainstorming、writing-plans など）で作った設計（`specs/`）と実装計画（`plans/`）を置く。運用の設計は `specs/2026-10-03-superpowers-document-lifecycle-design.md` にある。

## 保存先

- 対象のリポジトリにかかわらず、Spec・Plan はこのリポジトリ（`usaturn/create-reso-world`）の `docs/superpowers/` にコミットする。ResoLoop や無関係なリポジトリの作業でも、そちらには置かない
- Spec は `specs/YYYY-MM-DD-<topic>-design.md`、Plan は `plans/YYYY-MM-DD-<topic>.md` とする。Issue・PR に関する文書の `<topic>` には、リポジトリを表す語と番号を含める（例: `usaturn-resoloop-pr9-list-shrink-review-fixes`）
- 同じテーマのレビュー修正は、新しいファイルを作らずに既存の文書を更新する。過去の版は Git の履歴で追う

## 状態

文書の冒頭に、文書管理リポジトリ、対象リポジトリと Issue・PR、検証したコードの HEAD、状態、関連する文書を書く。

| 状態 | 意味 |
| --- | --- |
| draft | 明示承認をまだ得ていない |
| approved | 指定された版の内容について明示承認を得た |
| completed | 作業が完了した。結果と検証の根拠を併記する |
| superseded | 後継の文書に置き換えた |
| cancelled | 取りやめた。理由を残す |

コミットしただけでは `approved` にしない。承認は、確認したコミットの SHA に結び付けて記録する。完了・置換・取りやめの後も、文書は削除しない。

## 確認用コピー

ユーザに確認を依頼する前に、コミット済みの版を親 checkout の `tmp/superpowers-review/` にコピーする。

```bash
bash scripts/superpowers-review-copy.sh --doc-root "$DOC_ROOT" --parent-root "$PARENT_ROOT" \
  --path docs/superpowers/specs/2026-10-03-example-design.md --name usaturn-resoloop-pr9-list-shrink-spec.md
```

- コピーは閲覧のためのもので、正本ではない。引き継ぎや復元には、コミット済みの正本を使う
- 確認中のコピーを新しい版に差し替えるときは、確認済みの版を `--replace-from <commit>` で示す。ユーザが編集したコピーは差し替えず、差分を正本へ反映してからコピーし直す

## 公開

- このリポジトリ自身の変更に伴う文書は、その作業の PR に含める
- 他のリポジトリの変更に伴う文書は、このリポジトリの文書用ブランチから、テーマごとに 1 つの文書専用 PR で公開する。コード側の PR とは相互に参照する
- push・PR 作成・マージは、ユーザまたは使っているワークフローの明示指示があるときだけ行う。ローカルのコミットだけのときは「公開未実施」と報告する

## 履歴と現行仕様

Spec・Plan は判断と実装の経緯の記録である。完了した Plan の手順を、今の環境でそのまま再実行してよいという意味ではない。利用者が参照する現在の手順は、各リポジトリの README などの通常のドキュメントに書く。
````

`README.md` の 71 行目を次に置き換える。

```markdown
- 設計と実装計画は、対象のリポジトリにかかわらず `docs/superpowers/` に置く。運用は `docs/superpowers/README.md` にある。ローカルの下書きは `docs_draft/`（git の追跡対象外）に置く。
```

- [ ] **Step 5: テストが通ることを確かめる**

Run: `bash tests/scripts/test-instructions.bash && bash tests/scripts/test-docs.bash`
Expected: 両方 PASS

- [ ] **Step 6: コミット**

```bash
git add AGENTS.md README.md docs/superpowers/README.md tests/scripts/test-instructions.bash tests/scripts/test-docs.bash
git commit -m "docs: define where Superpowers specs and plans live for every repository"
```

---

### Task 3: pr-review の任意対象 checkout

**Files:**
- Modify: `.agents/skills/pr-review/SKILL.md`（規約の `MAIN_ROOT` の箇条書き、`reviews/` の箇条書き、手順 2 の resolver、出力前セルフチェック）
- Test: `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py`

**Interfaces:**
- Consumes: AGENTS.md の `CODE_ROOT` の定義（Task 2）
- Produces: resolver の終了コード `64`（明示が無い）、`65`（fork が検証できない）、`66`（`CODE_ROOT` が不正・不一致）

- [ ] **Step 1: 失敗するテストを書く**

`ResolverFixture.resolve` に `code_root` 引数を足し、harness で `CODE_ROOT` を設定する。

```python
    def resolve(self, pr_url: str, *, skill_path: Path, code_root: str | None = None) -> tuple[Path, str]:
        script = extract_resolver_script(read(skill_path))
        pr_json = json.dumps({"url": pr_url})
        # Emit MAIN_ROOT and PR_REMOTE after the skill block for the test harness.
        harness = f"""set -euo pipefail
PR_JSON={json.dumps(pr_json)}
CODE_ROOT={json.dumps(code_root or "")}
{script}
printf '%s\\n' "$MAIN_ROOT" "$PR_REMOTE"
"""
```

ファイル末尾近く（`test_pr_review_resolver_stops_without_a_verified_fork_checkout` の後）に次を足す。

```python
OTHER_URL = "https://github.com/other/repository/pull/3"


def build_checkout(path: Path, remotes: dict[str, str]) -> Path:
    """A checkout of its own outside the parent, with the given remotes."""
    path.mkdir(parents=True)
    _git(path, "init")
    _git(path, "commit", "--allow-empty", "-m", "init")
    for name, url in remotes.items():
        _git(path, "remote", "add", name, url)
    return path.resolve()


@pytest.mark.parametrize(
    ("remotes", "expected_remote"),
    [
        ({"origin": "https://github.com/other/repository.git"}, "origin"),
        # A fork checkout: the PR's pull/<N>/head lives in the base repository.
        (
            {"origin": "https://github.com/someone/repository.git", "upstream": "git@github.com:other/repository.git"},
            "upstream",
        ),
    ],
)
def test_pr_review_resolver_uses_an_explicit_code_root(
    tmp_path: Path, remotes: dict[str, str], expected_remote: str
) -> None:
    resolver = make_resolver(tmp_path)
    checkout = build_checkout(tmp_path / "elsewhere" / "repository", remotes)
    main_root, pr_remote = resolver.resolve(OTHER_URL, skill_path=AGENTS_SKILL, code_root=str(checkout))
    assert main_root == checkout
    assert pr_remote == expected_remote


@pytest.mark.parametrize(
    "case",
    ["relative", "subdirectory", "missing", "no-matching-remote", "two-matching-remotes"],
)
def test_pr_review_resolver_rejects_an_unverified_code_root(tmp_path: Path, case: str) -> None:
    resolver = make_resolver(tmp_path)
    remotes = {"origin": "https://github.com/other/repository.git"}
    if case == "no-matching-remote":
        remotes = {"origin": "https://github.com/someone/repository.git"}
    if case == "two-matching-remotes":
        remotes["mirror"] = "git@github.com:other/repository.git"
    checkout = build_checkout(tmp_path / "elsewhere" / "repository", remotes)
    code_root = {
        "relative": "elsewhere/repository",
        "subdirectory": str(checkout / ".git"),
        "missing": str(tmp_path / "absent"),
    }.get(case, str(checkout))
    with pytest.raises(ResolverStopped) as stopped:
        resolver.resolve(OTHER_URL, skill_path=AGENTS_SKILL, code_root=code_root)
    assert stopped.value.returncode == 66
    assert "CODE_ROOT" in stopped.value.stderr


def test_pr_review_resolver_rejects_a_code_root_that_contradicts_a_known_route(tmp_path: Path) -> None:
    resolver = make_resolver(tmp_path)
    checkout = build_checkout(tmp_path / "elsewhere" / "repository", {"origin": PARENT_ORIGIN})
    with pytest.raises(ResolverStopped) as stopped:
        resolver.resolve(
            "https://github.com/usaturn/create-reso-world/pull/1", skill_path=AGENTS_SKILL, code_root=str(checkout)
        )
    assert stopped.value.returncode == 66
    main_root, pr_remote = resolver.resolve(
        "https://github.com/usaturn/create-reso-world/pull/1",
        skill_path=AGENTS_SKILL,
        code_root=str(resolver.toplevel),
    )
    assert (main_root, pr_remote) == (resolver.toplevel, "origin")


def test_other_repositories_keep_reviews_out_of_the_document_store() -> None:
    content = read(AGENTS_SKILL)
    assert 'CODE_ROOT="${CODE_ROOT:-}"' in content
    assert "推測で埋めない" in content
    assert "`$CODE_ROOT/reviews/`" in content
    assert "Spec・Plan ではない" in content
```

`assert_review_contract` に次の 2 行を足す。

```python
    assert 'elif [[ -n "$CODE_ROOT" ]]; then' in content
    assert "exit 66" in content
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_skill_contract.py -q`
Expected: FAIL（`test_pr_review_resolver_uses_an_explicit_code_root` が `unsupported PR repository` で停止、`assert_review_contract` の新しい 2 行、`test_other_repositories_keep_reviews_out_of_the_document_store`）

- [ ] **Step 3: SKILL.md を書く**

規約の箇条書きの `MAIN_ROOT` の行（`- \`MAIN_ROOT\` は PR URL の GitHub \`owner/repository\` を、…それ以外は推測せず停止する`）の末尾の「それ以外は推測せず停止する」を、次に置き換える。

```markdown
それ以外は、ユーザの依頼または確認済みの引き継ぎで明示された checkout（`CODE_ROOT`）が、その checkout 自身のルートで、remote のうち 1 つだけが PR のリポジトリと一致する場合だけ、その checkout を使う。明示が無い・一致しない・候補が複数ある場合は推測せず停止する。checkout の探索・clone はしない
```

`reviews/` の箇条書き（`- 保存先の \`reviews/\` は \`MAIN_ROOT\` の直下にある。…\`reviews/\` を含めない`）の末尾に次を足す。

```markdown
。その他のリポジトリでは `$CODE_ROOT/reviews/` になり、その checkout の `.gitignore` が無視するとは限らないため、同じく `git add` に明示したパスだけを渡す。レビュー成果物は Spec・Plan ではないため、create-reso-world の `docs/superpowers/` へ集約しない
```

手順 2 の `MAIN_ROOT` の説明の末尾「それ以外は推測せず停止する。」の後に次を足す。

```markdown
その他のリポジトリは、ユーザの依頼または確認済みの引き継ぎで checkout が明示されている場合だけ、その絶対パスを `CODE_ROOT` に入れてから次を実行する。推測で埋めない。明示されていなければ空のままにする。
```

resolver のコードブロックを次に置き換える（字下げは既存のブロックと同じ 5 個の空白）。

```bash
PR_URL=$(printf '%s' "$PR_JSON" | jq -r .url)
TOPLEVEL=$(git rev-parse --show-toplevel)
CODE_ROOT="${CODE_ROOT:-}"
github_repository() {
  sed -nE \
    -e 's#^https://github[.]com/([^/]+/[^/#?]+)(/.*)?$#\1#p' \
    -e 's#^git@github[.]com:([^/]+/[^/#?]+)([.]git)?$#\1#p' | \
    sed 's/[.]git$//'
}
pr_repository="$(printf '%s\n' "$PR_URL" | github_repository)"
origin_repository="$(printf '%s\n' \
  "$(git -C "$TOPLEVEL" remote get-url origin)" | github_repository)"
test -n "$pr_repository"
test -n "$origin_repository"
if [[ "$pr_repository" == "$origin_repository" ]]; then
  MAIN_ROOT="$TOPLEVEL"
  PR_REMOTE=origin
elif [[ "$pr_repository" == "usaturn/resoloop" || "$pr_repository" == "orange3134/resoloop" ]]; then
  FORK_ROOT="$TOPLEVEL/external/resoloop"
  if [[ "$(git -C "$FORK_ROOT" remote get-url origin 2>/dev/null | github_repository)" != "usaturn/resoloop" ]] ||
    [[ "$(git -C "$FORK_ROOT" remote get-url upstream 2>/dev/null | github_repository)" != "orange3134/resoloop" ]]; then
    printf '%s is not the resoloop fork checkout; run scripts/resoloop-fork.sh clone first\n' "$FORK_ROOT" >&2
    exit 65
  fi
  MAIN_ROOT="$FORK_ROOT"
  if [[ "$pr_repository" == "orange3134/resoloop" ]]; then PR_REMOTE=upstream; else PR_REMOTE=origin; fi
elif [[ -n "$CODE_ROOT" ]]; then
  # その他のリポジトリは、明示された checkout だけを使う。探索・clone はしない
  if [[ "$CODE_ROOT" != /* ]] || ! code_toplevel=$(git -C "$CODE_ROOT" rev-parse --show-toplevel 2>/dev/null) ||
    [[ "$(realpath -e -- "$code_toplevel")" != "$(realpath -e -- "$CODE_ROOT")" ]]; then
    printf 'CODE_ROOT is not the root of a git checkout: %s\n' "$CODE_ROOT" >&2
    exit 66
  fi
  matches=()
  for remote in $(git -C "$CODE_ROOT" remote); do
    if [[ "$(git -C "$CODE_ROOT" remote get-url "$remote" | github_repository)" == "$pr_repository" ]]; then
      matches+=("$remote")
    fi
  done
  if [[ ${#matches[@]} -ne 1 ]]; then
    printf 'CODE_ROOT %s has %d remotes for %s; exactly one is required\n' "$CODE_ROOT" "${#matches[@]}" "$pr_repository" >&2
    exit 66
  fi
  MAIN_ROOT=$(realpath -e -- "$CODE_ROOT")
  PR_REMOTE="${matches[0]}"
else
  printf 'unsupported PR repository: %s (name its checkout as CODE_ROOT)\n' "$pr_repository" >&2
  exit 64
fi
if [[ -n "$CODE_ROOT" && "$(realpath -m -- "$CODE_ROOT")" != "$(realpath -m -- "$MAIN_ROOT")" ]]; then
  printf 'CODE_ROOT %s does not match %s for %s\n' "$CODE_ROOT" "$MAIN_ROOT" "$pr_repository" >&2
  exit 66
fi
```

出力前セルフチェックの `MAIN_ROOT` の行の「その他は停止」を「その他は明示された `CODE_ROOT` を照合し、明示が無い・不一致なら停止」に置き換える。

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/pr-review/tests -q`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add .agents/skills/pr-review/SKILL.md .agents/skills/pr-review/tests/test_pr_review_skill_contract.py
git commit -m "feat(pr-review): review other repositories through an explicit CODE_ROOT"
```

---

### Task 4: review-fix-planning の任意対象と文書の扱い

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（frontmatter の `allowed-tools`、手順 2・7、実装後、作業終了前の PR 投稿のテンプレート、「Spec は経路に関わらず必須」）
- Test: `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`

**Interfaces:**
- Consumes: Task 1 のスクリプト、Task 2 の `PARENT_ROOT`・`DOC_ROOT`・`CODE_ROOT`、Task 3 の `CODE_ROOT` 照合規則

- [ ] **Step 1: 失敗するテストを書く**

`test_allowed_tools_match_the_verification_and_spec_location` の `for entry in (` の一覧に `"Bash(bash scripts/superpowers-review-copy.sh*)",` を足す。ファイル末尾に次を足す。

```python
def test_other_repositories_need_an_explicit_code_root() -> None:
    step2 = read(AGENTS_SKILL).split("2. **現行 HEAD を特定する**", 1)[1].split("3. **", 1)[0]
    assert "`CODE_ROOT`" in step2
    assert "推測せず停止する" in step2
    assert "pr-review" in step2


def test_spec_is_committed_and_copied_before_approval() -> None:
    content = read(AGENTS_SKILL)
    section = content.split("## Spec のコミットと確認用コピー", 1)[1].split("\n## ", 1)[0]
    for phrase in (
        "`DOC_ROOT`",
        "`PARENT_ROOT`",
        "bash scripts/superpowers-review-copy.sh",
        "--replace-from",
        "文書用ブランチ",
        "文書専用 PR",
        "公開未実施",
    ):
        assert phrase in section, phrase
    step7 = content.split("7. **承認を得て停止する**", 1)[1].split("\n## ", 1)[0]
    assert "## Spec のコミットと確認用コピー" not in step7
    assert "確認用コピー" in step7
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests -q`
Expected: FAIL（allowed-tools、新しい 2 テスト）

- [ ] **Step 3: SKILL.md を書く**

frontmatter の `allowed-tools` の `Bash(bash tests/scripts/*), ` の後に `Bash(bash scripts/superpowers-review-copy.sh*), ` を足す。

手順 2 の「それ以外は推測せず停止する。」を次に置き換える。

```markdown
それ以外は、ユーザの依頼または確認済みの引き継ぎで明示された checkout（`CODE_ROOT`）を、`pr-review` と同じ照合（その checkout 自身のルートで、remote のうち 1 つだけが `PR_REPO` と一致する）で確かめて `MAIN_ROOT` にする。明示が無い・一致しない・候補が複数ある場合は推測せず停止する。レビューディレクトリは `CODE_ROOT` 配下の `reviews/` をフルパスで受け取る。
```

手順 7 を次に置き換える。

```markdown
7. **承認を得て停止する** — 下記「Spec のコミットと確認用コピー」に従って Spec をコミットし、確認用コピーを作ってから提示する。ユーザが明示的に「進めて」と言うまで実装に入らない。実装せず止まる場合の **作業終了前の PR 投稿** は任意であり、commit / push まで完了したターンのみ必須である。実装が終わったら **実装後** に従う。
```

`## 実装後` の直前に次の節を足す。

```markdown
## Spec のコミットと確認用コピー

Spec の正本は `$TOPLEVEL`（create-reso-world。ルート `AGENTS.md` の `DOC_ROOT`）にだけ置く。`MAIN_ROOT` が別のリポジトリでも、そちらへ置かない。

1. **コミットする** — 提示の前に、Spec を `draft` のままコミットする。コミット先は、`PR_REPO` が `usaturn/create-reso-world` ならレビュー対象ブランチ（実装を載せるブランチ）、それ以外なら create-reso-world の文書用ブランチ（テーマごとに 1 本。例 `docs/usaturn-resoloop-pr9-list-shrink`）である。そのブランチの checkout を `DOC_ROOT` とする。既存の文書用ブランチがあれば再利用し、レビュー回ごとに作らない。`DOC_ROOT` を特定できない場合は推測せず停止する。
2. **確認用コピーを作る** — `PARENT_ROOT`（ユーザが読む create-reso-world の親 checkout）を確かめてから、次を `$TOPLEVEL` で実行する。名前は `<repo>-pr<N>-<topic>-spec.md` の形にする。再提示で既存のコピーを差し替えるときは、前回提示した文書コミットを `--replace-from` に渡す。スクリプトが拒否したら、worktree のパスだけを代わりに示さず、失敗を報告して止まる。

   ```bash
   bash scripts/superpowers-review-copy.sh --doc-root "$DOC_ROOT" --parent-root "$PARENT_ROOT" \
     --path docs/superpowers/specs/<file> --name <repo>-pr<N>-<topic>-spec.md
   ```

3. **提示する** — コピー先（`tmp/superpowers-review/...`）、文書コミットの SHA、正本のパスを示して承認を求める。承認はその SHA の版に結び付ける。
4. **公開する** — `PR_REPO` が create-reso-world なら、Spec は実装と同じ PR に載る。それ以外では、**実装後** の push の後で文書用ブランチを push し、同じテーマの文書専用 PR があればそこへ反映する。文書専用 PR はコード修正の第二の PR ではない。文書専用 PR が無ければ、作らずに文書のコミット SHA を報告し、「公開未実施」と書いて作成の指示を求める。
```

`### 作業結果` のテンプレートの `- Spec: \`<path>\`（コミットしていなければローカルにしか無い）または未作成` を次に置き換える。

```markdown
- Spec: `<path>` @ `<文書コミット SHA>`（create-reso-world。文書専用 PR があればその URL、無ければ公開未実施）または未作成
```

「Spec は経路に関わらず必須」の配置の行の「`MAIN_ROOT` が `external/resoloop` のときも fork の中へ置かない」を「`MAIN_ROOT` が `external/resoloop` や他のリポジトリの checkout のときも、そちらへ置かない」に置き換える。

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/review-fix-planning/tests -q`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add .agents/skills/review-fix-planning/SKILL.md .agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py
git commit -m "feat(review-fix-planning): commit specs in create-reso-world and copy them for review"
```

---

### Task 5: agent-handoff の記録項目

**Files:**
- Modify: `.agents/skills/agent-handoff/SKILL.md`（handoff を書く 2・4、handoff を読む 5）
- Modify: `.agents/skills/agent-handoff/references/handoff-schema.md`（`sources` と `git`）
- Test: `.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py`

**Interfaces:**
- Consumes: Task 2 の `PARENT_ROOT`・`DOC_ROOT`・`CODE_ROOT`、Task 1 の確認用コピー
- Produces: schema の任意項目 `sources.doc_root`・`sources.document_commit`・`sources.document_published`・`sources.review_copy`・`git.parent_checkout`・`git.code`

- [ ] **Step 1: 失敗するテストを書く**

ファイル末尾に次を足す。

```python
def test_documents_and_code_are_restored_from_separate_sources() -> None:
    content = read(AGENTS_SKILL)
    for phrase in ("`PARENT_ROOT`", "`DOC_ROOT`", "`CODE_ROOT`", "`sources.review_copy`", "閲覧補助", "公開未実施"):
        assert phrase in content, phrase
    schema = read(SCHEMA)
    for field in (
        "`doc_root`",
        "`document_commit`",
        "`document_published`",
        "`review_copy`",
        "`parent_checkout`",
        "`code`",
    ):
        assert field in schema, field
    assert "never a restore source" in schema
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/agent-handoff/tests -q`
Expected: FAIL（新しいテスト）

- [ ] **Step 3: SKILL.md と schema を書く**

SKILL.md の「handoff を書く」の手順 2 の末尾に次を足す。

```markdown
Spec・Plan の正本は、対象のリポジトリにかかわらず create-reso-world にある（ルート `AGENTS.md` の「Spec・Plan の保存と公開」）。正本をコミットした checkout（`DOC_ROOT`）と文書のコミット SHA を `sources.doc_root`・`sources.document_commit` に、push 済みかどうかを `sources.document_published` に書く。ローカルのコミットだけなら「公開未実施」と書く。`tmp/superpowers-review/` の確認用コピーは `sources.review_copy` に閲覧補助として書くだけで、復元元にしない。
```

手順 4 の `git.worktree` の箇条書きの末尾に次を足す。

```markdown
   ユーザが読む親 checkout（`PARENT_ROOT`）は `git.parent_checkout` に書く。コードが create-reso-world 以外のリポジトリにあるときは、コード側の checkout（`CODE_ROOT`）を `git.code` に、リポジトリ・branch・HEAD・PR と一緒に書き、文書側の `git.*` と混ぜない。
```

「handoff を読む」の手順 5 の末尾に次を足す。

```markdown
Spec・Plan は `sources.document_commit` の正本から読む。確認用コピー（`sources.review_copy`）しか無い、または文書のコミットが公開されていない環境では、続きに入る前に正本を取得できるかを確かめる。
```

`references/handoff-schema.md` の `sources` の箇条書き（`- \`plan\`, \`ledger\`, …: when they exist.`）の後に次を足す。

```markdown
  - `doc_root`: the create-reso-world checkout where the spec and plan are committed
    (`DOC_ROOT`). Specs and plans for every repository live there.
  - `document_commit`: the full SHA of the commit that holds the spec and plan, and
    `document_published`: the remote ref it was pushed to, or `null` when it is a local
    commit only (say "公開未実施" in Markdown).
  - `review_copy`: the copy under the parent checkout's `tmp/superpowers-review/` that a
    person reads. It is a viewing aid, never a restore source; restore from
    `document_commit`.
```

`git` の箇条書きの `merge_base` の後に次を足す。

```markdown
  - `parent_checkout`: the parent checkout a person reads (`PARENT_ROOT`) with its branch,
    HEAD and status, when it differs from `worktree`.
  - `code`: when the code lives in a repository other than create-reso-world, its
    `repository`, `worktree` (`CODE_ROOT`), `branch`, `head`, `status` and `pr`. Keep them
    apart from the document checkout above.
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/agent-handoff/tests -q`
Expected: PASS（参照パスの実在検査も通る。`scripts/superpowers-review-copy.sh` を参照する場合は Task 1 で作成済み）

- [ ] **Step 5: コミット**

```bash
git add .agents/skills/agent-handoff/SKILL.md .agents/skills/agent-handoff/references/handoff-schema.md .agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py
git commit -m "feat(agent-handoff): record document, parent and code checkouts separately"
```

---

### Task 6: planning-parallel-issues の任意対象と文書

**Files:**
- Modify: `.agents/skills/planning-parallel-issues/SKILL.md`（`## Target repository`）
- Modify: `.agents/skills/planning-parallel-issues/references/session-workflow.md`（`## Required artifact set`）
- Test: `.agents/skills/planning-parallel-issues/tests/test_planning_parallel_issues_contract.py`

**Interfaces:**
- Consumes: Task 1 のスクリプト、Task 2 の定義

- [ ] **Step 1: 失敗するテストを書く**

ファイル末尾に次を足す。

```python
def test_children_may_target_other_repositories_but_documents_stay_here() -> None:
    target = read(SKILL).split("## Target repository", 1)[1].split("\n## ", 1)[0]
    assert "exact identifier" in target
    assert "`CODE_ROOT`" in target
    assert "Stop instead of guessing for any other repository." not in target
    workflow = read(SKILL_DIR / "references/session-workflow.md")
    artifacts = workflow.split("## Required artifact set", 1)[1].split("\n## ", 1)[0]
    assert "`usaturn/create-reso-world`" in artifacts
    assert "scripts/superpowers-review-copy.sh" in artifacts
    assert "viewing aid" in artifacts
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/planning-parallel-issues/tests -q`
Expected: FAIL（新しいテスト）

- [ ] **Step 3: SKILL.md と session-workflow.md を書く**

`## Target repository` の最後の文「Stop instead of guessing for any other repository.」を次に置き換える。

```markdown
Do not build a board in any other repository. A child may still name another repository as its implementation target: record its exact identifier (`owner/repo` on GitHub), and the checkout only when the user or a verified handoff names it (`CODE_ROOT`). Its Spec and Plan are still committed in `usaturn/create-reso-world`, as the root `AGENTS.md` requires for every repository. Stop instead of guessing when the target or its checkout is unclear.
```

`references/session-workflow.md` の `## Required artifact set` の最初の段落（`Determine paths from repository instructions. …`）の後に次の段落を足す。

```markdown
Specs and Plans for every child, whatever repository its code targets, are committed under `docs/superpowers/` of `usaturn/create-reso-world` (the root `AGENTS.md`). When a person is asked to read one, first create the review copy with `bash scripts/superpowers-review-copy.sh` in the parent checkout's `tmp/superpowers-review/`. The copy is a viewing aid, not a recovery artifact; recovery still uses the published manifest below.
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/planning-parallel-issues/tests -q`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add .agents/skills/planning-parallel-issues/SKILL.md .agents/skills/planning-parallel-issues/references/session-workflow.md .agents/skills/planning-parallel-issues/tests/test_planning_parallel_issues_contract.py
git commit -m "feat(planning-parallel-issues): keep child specs in create-reso-world for any target"
```

---

### Task 7: スキル全体の回帰確認

**Files:** なし（Task 3〜6 の後の確認だけ）

- [ ] **Step 1: スキルのテスト全体を実行する**

Run: `uv run pytest tests/skills .agents/skills -q`
Expected: PASS。失敗したら、Task 3〜6 の本文と他のスキルの契約テスト（`simplify-in-subagent`・`repo-cleanup-after-merge` のリポジトリ境界の検査など）の食い違いを直してから次へ進む

- [ ] **Step 2: レイアウトを確認する**

Run: `bash scripts/check-layout.sh`
Expected: `PASS: check-layout`

---

### Task 8: 既存文書 22 件の取り込み

**Files:**
- Create: Spec 第8.2節の 22 件（`docs/superpowers/plans/` 3 件、`docs/superpowers/specs/` 19 件）

**Interfaces:**
- Consumes: 退避先 `/workspaces/reso-world/docs_draft/untracked-main-20261003/` と、引継ぎ書 `tmp/docs_draft/claude_handoffs/20261003T105943Z-4575ae93-superpowers-doc-storage.handoff.json` の `sources.evacuated_import_manifest`（22 件の SHA-256）

- [ ] **Step 1: 取り込み元のハッシュを照合する**

```bash
H=/workspaces/reso-world/tmp/docs_draft/claude_handoffs/20261003T105943Z-4575ae93-superpowers-doc-storage.handoff.json
D=/workspaces/reso-world/docs_draft/untracked-main-20261003
jq -r '.sources.evacuated_import_manifest[] | "\(.sha256)  \(.path)"' "$H" > /tmp/claude-1000/-workspaces-reso-world/4575ae93-f3ee-4245-8ce4-7c5c9aa01210/scratchpad/import.sha256
(cd "$D" && sha256sum -c /tmp/claude-1000/-workspaces-reso-world/4575ae93-f3ee-4245-8ce4-7c5c9aa01210/scratchpad/import.sha256)
```

Expected: 22 行すべて `OK`。1 件でも違えば止まって報告する

- [ ] **Step 2: 取り込み先に同名のファイルが無いことを確かめる**

```bash
jq -r '.sources.evacuated_import_manifest[].path' "$H" | while read -r f; do
  [ ! -e "$f" ] || { echo "exists: $f"; exit 1; }
  git ls-files --error-unmatch -- "$f" >/dev/null 2>&1 && { echo "tracked: $f"; exit 1; }
  true
done
```

Expected: 何も表示されずに終了 0

- [ ] **Step 3: 機密情報と参照切れを確認する**

```bash
jq -r '.sources.evacuated_import_manifest[].path' "$H" | (cd "$D" && xargs grep -nE '(ghp_|github_pat_|gho_|sk-[A-Za-z0-9]{20}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|(SECRET|TOKEN|PASSWORD|API_KEY)[A-Z_]*=[^ $]+)' || true)
command -v gitleaks >/dev/null && gitleaks dir --no-banner --config .gitleaks.toml "$D/docs" || true
jq -r '.sources.evacuated_import_manifest[].path' "$H" | (cd "$D" && xargs grep -ohE 'docs/superpowers/(specs|plans)/[A-Za-z0-9._-]+\.md' | sort -u) > /tmp/claude-1000/-workspaces-reso-world/4575ae93-f3ee-4245-8ce4-7c5c9aa01210/scratchpad/refs.txt
while read -r ref; do [ -e "$ref" ] || [ -e "$D/$ref" ] || echo "missing: $ref"; done < /tmp/claude-1000/-workspaces-reso-world/4575ae93-f3ee-4245-8ce4-7c5c9aa01210/scratchpad/refs.txt
```

Expected: 機密情報の一致なし。`missing:` の行は、取り込み後も実在しない文書への参照として PR の説明に一覧を残す（本文は変えない）

- [ ] **Step 4: コピーして 1 件ずつステージする**

```bash
jq -r '.sources.evacuated_import_manifest[].path' "$H" | while read -r f; do
  cp --no-clobber --preserve=mode -- "$D/$f" "$f"
  git add -- "$f"
done
(cd . && sha256sum -c /tmp/claude-1000/-workspaces-reso-world/4575ae93-f3ee-4245-8ce4-7c5c9aa01210/scratchpad/import.sha256)
git diff --cached --name-only | wc -l
git diff --cached --name-only | grep -v -F -x -f <(jq -r '.sources.evacuated_import_manifest[].path' "$H") || true
```

Expected: `sha256sum -c` が 22 行すべて `OK`、ステージは 22 件、一覧外のステージは無し（最後のコマンドは何も表示しない）

- [ ] **Step 5: 取り込み元が変わっていないことを確かめてコミットする**

```bash
(cd "$D" && sha256sum -c /tmp/claude-1000/-workspaces-reso-world/4575ae93-f3ee-4245-8ce4-7c5c9aa01210/scratchpad/import.sha256) | grep -c ': OK$'
git commit -m "docs: import the 22 untracked Superpowers documents"
```

Expected: `22`

---

### Task 9: 最終検証、確認用コピー、PR

**Files:**
- Create（ignore 対象）: `/workspaces/reso-world/tmp/superpowers-review/superpowers-doc-storage-plan.md`
- Update（ignore 対象）: `/workspaces/reso-world/tmp/superpowers-review/superpowers-doc-storage-spec.md`
- Create（ignore 対象）: 最新の引継ぎ書の対

- [ ] **Step 1: 完了条件の検証を同期実行する**

```bash
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
uv run pytest tests/skills .agents/skills
```

Expected: `PASS: <N> test(s)`、`PASS: check-layout`、pytest はすべて passed

- [ ] **Step 2: Spec・Plan の確認用コピーを作る**

```bash
bash scripts/superpowers-review-copy.sh --doc-root "$PWD" --parent-root /workspaces/reso-world \
  --path docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-design.md \
  --name superpowers-doc-storage-spec.md --replace-from 8c7767c0ebfa2d3ccba43ab34d5f07780081e2ef
bash scripts/superpowers-review-copy.sh --doc-root "$PWD" --parent-root /workspaces/reso-world \
  --path docs/superpowers/plans/2026-10-03-superpowers-document-lifecycle.md --name superpowers-doc-storage-plan.md
```

Expected: `replaced:` と `created:`。既存の Spec コピーは 8c7767c の版と一致しているはずで、違えば止まって差分を確認する（ユーザ編集の可能性）

- [ ] **Step 3: push して PR を作る**

```bash
git push -u origin docs/superpowers-document-lifecycle
gh pr create --repo usaturn/create-reso-world --base main --head docs/superpowers-document-lifecycle \
  --title "docs: keep Superpowers specs and plans in create-reso-world for every repository" --body-file <本文>
```

本文には、目的、変更点（規約・スキル・スクリプト・取り込み 22 件）、取り込まなかった 7 件と理由、参照切れの一覧、検証結果、Spec・Plan のパスと確認用コピー、Spec の承認がユーザの「途中で止めずに PR まで」の指示によることを書き、最後に `🤖 Generated with [Claude Code](https://claude.com/claude-code)` を付ける。マージはしない。

- [ ] **Step 4: 引継ぎ書を更新する**

`agent-handoff` の書く側の手順で、PR の URL、最終 HEAD、検証結果、残作業（PR のレビューとマージ）を記録した新しい対を `tmp/docs_draft/claude_handoffs/` に作る。
