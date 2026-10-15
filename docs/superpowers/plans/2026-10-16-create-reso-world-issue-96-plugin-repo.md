# create-reso-world#96 Meshy プラグインのリポジトリ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 文書管理: `usaturn/create-reso-world`（ブランチ `feat/issue-96-plugin-repo`）
- 対象 Issue: usaturn/create-reso-world#96
- 状態: draft（内容の承認は得ていない。実行の指示は Spec の「管理・実行許可」）
- 実行方法: 利用者の指示「途中で止めずに推奨案で PR まで作成して」により、エージェントが選んだ。このセッションで controller が自分で実装する（superpowers:executing-plans）。Task が少なく、互いのインターフェースへの依存が小さいため

**Goal:** `usaturn/resoloop-meshy` を作り、create-reso-world の `external/resoloop-meshy` から開発できるようにする。

**Architecture:** create-reso-world には取得と状態表示のスクリプト（`scripts/resoloop-meshy.sh`）、運用文書、`AGENTS.md` の「リポジトリ境界」の行を足す。新しいリポジトリには、uv の仮想プロジェクトと規約の雛形だけを置く。

**Tech Stack:** bash、git、gh、uv、pytest

**Spec:** `docs/superpowers/specs/2026-10-16-create-reso-world-issue-96-plugin-repo-design.md`

## Global Constraints

- リポジトリ: `usaturn/resoloop-meshy`、private、ライセンス AGPL-3.0-or-later（Spec D-1〜D-3）
- checkout: `<PARENT_ROOT>/external/resoloop-meshy`、remote は `origin` = `https://github.com/usaturn/resoloop-meshy.git` だけ（D-4）
- スクリプトの終了コード: 0 成功、1 状態が期待と違う、2 使い方の誤り、3 前提不足、4 `git clone` の失敗（D-5）
- Python は uv で実行する。`python3` を直接使わない。`requires-python = ">=3.12"`
- CI（`.github/workflows/`）は作らない。リポジトリを作ったら、その場で Actions を無効にする
- 変えないもの: `.devcontainer/`、create-reso-world の `README.md`・既存の Meshy のファイル、`scripts/resoloop-fork.sh`、`scripts/superpowers_context.py`
- rm の削除対象にシェル変数を使うときは `${VAR:?}` を付けて引用する

## Review Focus

- create-reso-world の worktree から `clone` しても、worktree の中ではなく親 checkout の `external/resoloop-meshy` に作る（worktree を消したときにプラグインの作業が消えない）。Task 1 のケース 9
- `external/resoloop-meshy` が自前の checkout でない普通のディレクトリのとき、外側の create-reso-world の `origin` を見て「clone 済み」としない。Task 1 のケース 7（外側の `origin` を期待する URL にしておく）
- 既存の checkout の `origin` が違う・無いとき、`clone` は何も変えずに 1 で止まる。Task 1 のケース 6
- `clone` の失敗（認証が無い private のリポジトリなど）は 4 で、ディレクトリを残さない。Task 1 のケース 8
- URL の表記の違い（末尾の `/`、`.git` の有無）だけで食い違いとしない。Task 1 のケース 5

---

### Task 1: `scripts/resoloop-meshy.sh` とそのテスト

**テストの要否:** 要る。分岐（引数、checkout の有無、自前の checkout かどうか、`origin` の一致、clone の失敗、既定の場所の解決）を、スクリプトを実行して確かめる。

**Files:**
- Create: `tests/scripts/test-resoloop-meshy.bash`（100755）
- Create: `scripts/resoloop-meshy.sh`（100755）

**Interfaces:**
- Produces: `bash scripts/resoloop-meshy.sh <clone|status>`。環境変数 `RESOLOOP_MESHY_CHECKOUT`・`RESOLOOP_MESHY_ORIGIN_URL`。出力の行: `cloned: <dir> (origin <url>)`、`ok: <dir> is already cloned (origin is as expected)`、`checkout: <dir> at <HEAD> (<branch|detached>, <clean|uncommitted changes>)`、`checkout: <dir> is missing (run scripts/resoloop-meshy.sh clone)`、`remote: origin is as expected`、`remote: origin is <got> (expected <want>)`、`remote: origin is missing (expected <want>)`、`remote: unknown (no checkout)`

- [ ] **Step 1: 失敗するテストを書く**

`tests/scripts/test-resoloop-meshy.bash`:

```bash
#!/bin/bash
# scripts/resoloop-meshy.sh を、ローカルの bare リポジトリで検査する（ネットワークを使わない）
# 仕様: docs/superpowers/specs/2026-10-16-create-reso-world-issue-96-plugin-repo-design.md D-4・D-5
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# ユーザの git 設定から隔離する（システム・グローバル設定と core.excludesFile を外す）。グローバル設定の
# safe.directory も外れるので、このリポジトリだけは所有者が違っても読めるようにしておく
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=core.excludesFile GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1="$repo_root"
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com
script="$repo_root/scripts/resoloop-meshy.sh"
tmp="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf -- "${tmp:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# プラグインのリポジトリ（origin.git）と、別のリポジトリ（other.git）
git init -q -b main "$tmp/seed"
printf 'v1\n' > "$tmp/seed/file.txt"
git -C "$tmp/seed" add . && git -C "$tmp/seed" commit -q -m v1
git clone -q --bare "$tmp/seed" "$tmp/origin.git"
git clone -q --bare "$tmp/seed" "$tmp/other.git"
v1="$(git -C "$tmp/seed" rev-parse HEAD)"
export RESOLOOP_MESHY_ORIGIN_URL="$tmp/origin.git" RESOLOOP_MESHY_CHECKOUT="$tmp/work/external/resoloop-meshy"
co="$RESOLOOP_MESHY_CHECKOUT"

expect_exit() {  # $1=期待する終了コード、$2=出力に含まれるべき文字列、残り=$script の引数
  local want="$1" needle="$2" got=0
  shift 2
  bash "$script" "$@" > "$tmp/out.txt" 2>&1 || got=$?
  [ "$got" -eq "$want" ] || { cat "$tmp/out.txt" >&2; fail "expected exit $want, got $got: $*"; }
  grep -qF -- "$needle" "$tmp/out.txt" || { cat "$tmp/out.txt" >&2; fail "expected output '$needle': $*"; }
}

# 1. 引数の誤りは 2
expect_exit 2 'usage:'
expect_exit 2 'usage:' bogus
expect_exit 2 'usage:' clone extra

# 2. clone の前の status は、checkout が無いことを示して 0
expect_exit 0 "checkout: $co is missing (run scripts/resoloop-meshy.sh clone)" status
grep -qF 'remote: unknown (no checkout)' "$tmp/out.txt" || fail 'status lacks the remote line'

# 3. clone は origin を持つ checkout を作り、2 回目は origin を確かめるだけ
expect_exit 0 "cloned: $co (origin $tmp/origin.git)" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/origin.git" ] || fail 'origin url'
[ "$(git -C "$co" rev-parse HEAD)" = "$v1" ] || fail 'clone did not check out main'
expect_exit 0 "ok: $co is already cloned (origin is as expected)" clone

# 4. status は HEAD・ブランチ・追跡ファイルの変更の有無と origin を表示する（未追跡ファイルは変更に数えない）
printf 'notes\n' > "$co/untracked.txt"
expect_exit 0 "checkout: $co at $v1 (main, clean)" status
grep -qF 'remote: origin is as expected' "$tmp/out.txt" || fail 'status remote'
printf 'edit\n' >> "$co/file.txt"
expect_exit 0 "checkout: $co at $v1 (main, uncommitted changes)" status
git -C "$co" checkout -q -- file.txt
rm -- "${co:?}/untracked.txt"

# 5. 末尾の / と .git の有無だけが違う URL は同じとみなす
git -C "$co" remote set-url origin "$tmp/origin.git/"
expect_exit 0 'is already cloned' clone
git -C "$co" remote set-url origin "$tmp/origin"
expect_exit 0 'is already cloned' clone

# 6. origin が違う・無いときは、clone は何も変えずに 1。status は食い違いを示して 0
git -C "$co" remote set-url origin "$tmp/other.git"
expect_exit 1 "origin is $tmp/other.git (expected $tmp/origin.git)" clone
[ "$(git -C "$co" remote get-url origin)" = "$tmp/other.git" ] || fail 'clone changed a mismatching origin'
expect_exit 0 "remote: origin is $tmp/other.git (expected $tmp/origin.git)" status
git -C "$co" remote remove origin
expect_exit 1 "origin is missing (expected $tmp/origin.git)" clone
if git -C "$co" remote get-url origin >/dev/null 2>&1; then fail 'clone added a missing origin'; fi
git -C "$co" remote add origin "$tmp/origin.git"

# 7. 外側のリポジトリの中にある、自前の checkout でないディレクトリは 1。外側の origin が期待する URL でも
#    clone 済みとみなさない
git init -q "$tmp/outer"
git -C "$tmp/outer" remote add origin "$tmp/origin.git"
mkdir -p "$tmp/outer/external/resoloop-meshy"
RESOLOOP_MESHY_CHECKOUT="$tmp/outer/external/resoloop-meshy" expect_exit 1 'is not a git checkout of its own' clone
RESOLOOP_MESHY_CHECKOUT="$tmp/outer/external/resoloop-meshy" expect_exit 0 'is not a git checkout of its own' status
grep -qF 'remote: unknown (no checkout)' "$tmp/out.txt" || fail 'status lacks the remote line for a directory that is not a checkout'

# 8. clone に失敗したら 4 で、ディレクトリを残さない
RESOLOOP_MESHY_CHECKOUT="$tmp/work/broken" RESOLOOP_MESHY_ORIGIN_URL="$tmp/no-such-remote.git" expect_exit 4 'git clone failed' clone
[ ! -e "$tmp/work/broken" ] || fail 'a failed clone left a directory'

# 9. 既定の checkout 先は、スクリプトを含むリポジトリの親 checkout の external/resoloop-meshy。worktree の
#    スクリプトから clone しても、worktree の中には作らない
git init -q -b main "$tmp/parent"
mkdir -p "$tmp/parent/scripts"
cp -- "$script" "$tmp/parent/scripts/resoloop-meshy.sh"
git -C "$tmp/parent" add . && git -C "$tmp/parent" commit -q -m init
git -C "$tmp/parent" worktree add -q "$tmp/parent/.worktrees/topic"
(
  unset RESOLOOP_MESHY_CHECKOUT
  script="$tmp/parent/scripts/resoloop-meshy.sh"
  expect_exit 0 "checkout: $tmp/parent/external/resoloop-meshy is missing" status
  script="$tmp/parent/.worktrees/topic/scripts/resoloop-meshy.sh"
  expect_exit 0 "cloned: $tmp/parent/external/resoloop-meshy" clone
  [ ! -e "$tmp/parent/.worktrees/topic/external" ] || fail 'clone from a worktree wrote into the worktree'
  [ "$(git -C "$tmp/parent/external/resoloop-meshy" rev-parse HEAD)" = "$v1" ] || fail 'clone from a worktree'
)

printf 'PASS: resoloop-meshy script behaves as specified\n'
```

`chmod +x tests/scripts/test-resoloop-meshy.bash`

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash tests/scripts/test-resoloop-meshy.bash`
Expected: FAIL（`scripts/resoloop-meshy.sh` が無いので、ケース 1 で `expected output 'usage:'` か終了コードの不一致）

- [ ] **Step 3: スクリプトを書く**

`scripts/resoloop-meshy.sh`:

```bash
#!/bin/bash
# resoloop の Meshy プラグインのリポジトリ（usaturn/resoloop-meshy）を external/resoloop-meshy に取得し、状態を表示する。
# 仕様: docs/superpowers/specs/2026-10-16-create-reso-world-issue-96-plugin-repo-design.md D-4・D-5。運用手順: docs/resoloop-meshy-workflow.md
# 使い方: scripts/resoloop-meshy.sh <clone|status>
# 既定の checkout 先は、このスクリプトを含む create-reso-world の親 checkout（git の common dir の親）の
# external/resoloop-meshy。create-reso-world の worktree から実行しても同じ場所を指す。
# 環境変数（テストと特殊な運用向け）:
#   RESOLOOP_MESHY_CHECKOUT    checkout 先（既定: <親 checkout>/external/resoloop-meshy）
#   RESOLOOP_MESHY_ORIGIN_URL  origin の URL（既定: https://github.com/usaturn/resoloop-meshy.git）
# 終了コード:
#   0 成功（status は常に 0）
#   1 状態が期待と違う（自前の git の checkout でない、origin が無い・違う）
#   2 使い方の誤り
#   3 前提不足（git が無い）
#   4 git clone の失敗
set -euo pipefail

usage() {
  printf 'usage: %s <clone|status>\n' "${BASH_SOURCE[0]}" >&2
  exit 2
}
die() { printf 'ERROR: %s\n' "$2" >&2; exit "$1"; }

[ $# -eq 1 ] || usage
cmd="$1"
case "$cmd" in clone|status) ;; *) usage ;; esac
command -v git >/dev/null 2>&1 || die 3 "git not found"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# worktree の中に clone すると、worktree を消したときにプラグインの作業ごと消える。親 checkout を基準にする
if common="$(git -C "$root" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; then
  root="$(dirname "$common")"
fi
# 相対パスの RESOLOOP_MESHY_CHECKOUT は呼び出し時の cwd を基準に絶対パスにする。symlink は解決しない
dir="$(realpath -ms -- "${RESOLOOP_MESHY_CHECKOUT:-$root/external/resoloop-meshy}")"
origin_url="${RESOLOOP_MESHY_ORIGIN_URL:-https://github.com/usaturn/resoloop-meshy.git}"

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

not_a_checkout="exists but is not a git checkout of its own; remove it (or move a checkout there) and rerun scripts/resoloop-meshy.sh clone"

check_origin() {  # origin を期待する URL と比べ、食い違いを 1 行で出力する。食い違いがあれば 1
  local got
  if ! got="$(git -C "$dir" remote get-url origin 2>/dev/null)"; then
    printf 'origin is missing (expected %s)\n' "$origin_url"
    return 1
  fi
  same_url "$got" "$origin_url" && return 0
  printf 'origin is %s (expected %s)\n' "$got" "$origin_url"
  return 1
}

do_clone() {
  local problem
  if [ -e "$dir" ] || [ -L "$dir" ]; then
    is_checkout || die 1 "$dir $not_a_checkout"
    if ! problem="$(check_origin)"; then
      printf '%s\n' "$problem" >&2
      die 1 "$dir has an unexpected origin; fix it with git remote add/set-url (see docs/resoloop-meshy-workflow.md)"
    fi
    printf 'ok: %s is already cloned (origin is as expected)\n' "$dir"
    return
  fi
  git clone --quiet --origin origin -- "$origin_url" "$dir" \
    || die 4 "git clone failed (the repository is private; check gh auth status)"
  printf 'cloned: %s (origin %s)\n' "$dir" "$origin_url"
}

do_status() {
  local head branch state problem
  if [ ! -e "$dir" ] && [ ! -L "$dir" ]; then
    printf 'checkout: %s is missing (run scripts/resoloop-meshy.sh clone)\n' "$dir"
    printf 'remote: unknown (no checkout)\n'
    return
  fi
  if ! is_checkout; then
    printf 'checkout: %s %s\n' "$dir" "$not_a_checkout"
    printf 'remote: unknown (no checkout)\n'
    return
  fi
  head="$(git -C "$dir" rev-parse -q --verify HEAD || printf 'none')"
  branch="$(git -C "$dir" symbolic-ref -q --short HEAD || printf 'detached')"
  if [ -n "$(git -C "$dir" status --porcelain --untracked-files=no)" ]; then
    state='uncommitted changes'
  else
    state='clean'
  fi
  printf 'checkout: %s at %s (%s, %s)\n' "$dir" "$head" "$branch" "$state"
  if problem="$(check_origin)"; then
    printf 'remote: origin is as expected\n'
  else
    printf 'remote: %s\n' "$problem"
  fi
}

"do_$cmd"
```

`chmod +x scripts/resoloop-meshy.sh`

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash tests/scripts/test-resoloop-meshy.bash`
Expected: `PASS: resoloop-meshy script behaves as specified`

Run: `bash tests/scripts/test-file-modes.bash`
Expected: PASS（2 本とも index 上で 100755）。`git add` の後に実行する

- [ ] **Step 5: コミットする**

```bash
git add scripts/resoloop-meshy.sh tests/scripts/test-resoloop-meshy.bash
git commit -m "feat: add resoloop-meshy clone/status script (#96)"
```

### Task 2: 運用文書と `AGENTS.md`

**テストの要否:** 要らない。文書と規約の文面だけの変更で、守る挙動が無い（`AGENTS.md` の「テストの採用基準」）。代わりに、参照先の実在を `tests/scripts/test-docs.bash --refs` と `tests/scripts/test-instructions.bash` で確かめ、`git diff` を確認する。

**Files:**
- Create: `docs/resoloop-meshy-workflow.md`
- Modify: `AGENTS.md`（「リポジトリ概要」の段落の末尾に 1 文、「リポジトリ境界」の表の「それ以外」の行の前に 1 行）

**Interfaces:**
- Consumes: Task 1 のサブコマンド・終了コード・環境変数
- Produces: 「リポジトリ境界」の行（#90・#102・#103 が使う）

- [ ] **Step 1: `docs/resoloop-meshy-workflow.md` を書く**

節: リポジトリ（名前・公開範囲・ライセンス・Actions）、checkout の位置と remote、`scripts/resoloop-meshy.sh`（表・終了コード・環境変数）、開発の流れ（clone → `pull --ff-only` → worktree → `uv run pytest` → push・PR・マージは利用者の指示 → 片付け）、PR のレビューと修正（`CODE_ROOT` の明示）、Spec・Plan の置き場所。内容は Spec の D-2〜D-6 に合わせる。コードブロックの外で、拡張子付きのパスを backtick で書くときは create-reso-world に実在するものだけにする（`test-docs.bash` の参照検査の対象になる）

- [ ] **Step 2: `AGENTS.md` を変える**

「リポジトリ概要」の段落の末尾に足す:

```markdown
resoloop のプラグイン（Meshy 用の usaturn/resoloop-meshy）は、別のリポジトリとして `external/resoloop-meshy` に checkout して開発する（「リポジトリ境界」）。
```

「リポジトリ境界」の表の「それ以外」の行の前に足す:

```markdown
| usaturn/resoloop-meshy | `<PARENT_ROOT>/external/resoloop-meshy` | `origin` が usaturn/resoloop-meshy であること。checkout が無ければ `bash scripts/resoloop-meshy.sh clone` を案内して停止する。実装は作業ルートの `.worktrees/<topic>` の worktree で行う。`pr-review`・`review-fix-planning` には作業ルートを `CODE_ROOT` として明示する。手順は `docs/resoloop-meshy-workflow.md` |
```

- [ ] **Step 3: 参照先の実在を確かめる**

Run: `bash tests/scripts/test-docs.bash --refs docs/resoloop-meshy-workflow.md AGENTS.md && bash tests/scripts/test-instructions.bash`
Expected: 失敗なし

- [ ] **Step 4: コミットする**

```bash
git add docs/resoloop-meshy-workflow.md AGENTS.md
git commit -m "docs: add resoloop-meshy repository boundary and workflow (#96)"
```

### Task 3: GitHub のリポジトリと初期コミット

**テストの要否:** 新しいリポジトリにはテストを書かない。雛形と設定だけで、守る挙動が無い。代わりに、Actions の状態の API、`clone`・`status` の実行、`uv run pytest` の終了コード、`tests/conftest.py` の手での確認で確かめる。

**Files（新しいリポジトリ、`/workspaces/reso-world/external/resoloop-meshy`）:**
- Create: `README.md`、`AGENTS.md`、`CLAUDE.md`、`LICENSE`、`.gitignore`、`pyproject.toml`、`uv.lock`、`tests/conftest.py`

**Interfaces:**
- Consumes: Task 1 の `bash scripts/resoloop-meshy.sh clone`（worktree から実行しても親 checkout に作る）

- [ ] **Step 1: リポジトリを作り、Actions を無効にする**

```bash
gh repo create usaturn/resoloop-meshy --private --description "Meshy の Web アプリで作った GLB を resoloop へ渡すプラグイン"
gh api -X PUT repos/usaturn/resoloop-meshy/actions/permissions -F enabled=false
gh api repos/usaturn/resoloop-meshy/actions/permissions
```

Expected: 最後の出力が `{"enabled":false}`

- [ ] **Step 2: スクリプトで clone する**

Run（worktree から）: `bash scripts/resoloop-meshy.sh clone && bash scripts/resoloop-meshy.sh status`
Expected: `cloned: /workspaces/reso-world/external/resoloop-meshy (origin https://github.com/usaturn/resoloop-meshy.git)`、status は `remote: origin is as expected`。空のリポジトリなので HEAD は `none`。`git -C /workspaces/reso-world/external/resoloop-meshy symbolic-ref --short HEAD` が `main` でなければ `git -C ... switch --orphan main`

- [ ] **Step 3: 初期の構成を書く**

`CLAUDE.md`:

```markdown
@AGENTS.md
```

`AGENTS.md`:

```markdown
# resoloop-meshy の規約

resoloop のプラグインのリポジトリ。Meshy の Web アプリで作った GLB を仕上げて resoloop へ渡す道具とスキルを置く。このリポジトリで作業するコーディングエージェント（Claude Code、Codex、pi、Cursor、Devin）が従う。

## 前提

- create-reso-world（usaturn/create-reso-world）の `external/resoloop-meshy` に checkout して開発する。create-reso-world の `AGENTS.md`（このリポジトリから `../../AGENTS.md`）にも従う
- Meshy の API（生成、ダウンロード、`meshy-cli`）は使わず、実装もしない。入力は Meshy の Web アプリからダウンロードした GLB だけ
- プラグインの manifest・コマンドの呼び出し・スキルの配布の仕様は resoloop の fork（usaturn/resoloop）で決まる。決まっていない仕様を推測で作らない

## 開発

- Python は uv で実行する。`python3` を直接使わない
- テストはこのディレクトリで `uv run pytest` を実行する
- 作業は `main` から作ったブランチで行い、`.worktrees/<topic>` の worktree を使う。checkout そのものは `main` のまま切り替えない
- push・PR の作成・マージは、利用者の指示があるときだけ行う
- CI（GitHub Actions のワークフロー）は作らない。このリポジトリの Actions は無効にしてある
- Spec・Plan はこのリポジトリに置かず、create-reso-world の `docs/superpowers/` に置く
- Meshy で作った GLB・テクスチャなどの原本はコミットしない。テストの素材は小さく作る
```

`README.md`:

```markdown
# resoloop-meshy

[resoloop](https://github.com/orange3134/resoloop) のプラグイン。Meshy の Web アプリで作った GLB を仕上げて、resoloop の `blender export`・`validate` まで通せる形で渡す。Meshy の API は使わない。

## 状態

準備中。今はリポジトリの土台だけがある。

- 仕上げの道具とスキル: usaturn/create-reso-world#90
- プラグインの manifest とコマンド: usaturn/create-reso-world#102
- resoloop のプラグイン機構: usaturn/resoloop の fork で作っている（usaturn/create-reso-world#97〜#100）

## 開発

create-reso-world の Dev Container で、create-reso-world のルートから取得する。

    bash scripts/resoloop-meshy.sh clone
    cd external/resoloop-meshy
    uv run pytest

手順の詳細は create-reso-world の `docs/resoloop-meshy-workflow.md`、規約は `AGENTS.md` にある。

## ライセンス

GNU Affero General Public License v3.0 or later（`LICENSE`）。resoloop と同じ。
```

`.gitignore`:

```gitignore
# Python / uv
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.uv-cache/

# Blender のバックアップ
*.blend1
*.blend2
*.blend@

# エージェントやツールが作る作業物（worktree、PR のレビュー結果、一時ファイル、個人設定）
/.worktrees/
/reviews/
tmp/
**/.claude/settings.local.json
```

`pyproject.toml`:

```toml
[project]
name = "resoloop-meshy"
version = "0.1.0"
description = "resoloop plugin that hands GLB files made with the Meshy web app to resoloop"
readme = "README.md"
license = "AGPL-3.0-or-later"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = ["pytest>=8"]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`tests/conftest.py`:

```python
from pathlib import Path

import pytest


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """テストのファイルがまだ 1 つも無い間だけ、テストを集められなかった終了（5）を成功にする。

    tests/ に conftest.py 以外の .py を置くと、pytest の既定どおり 5 で失敗に戻る。
    """
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED and not any(
        path.name != "conftest.py" for path in Path(__file__).parent.rglob("*.py")
    ):
        session.exitstatus = pytest.ExitCode.OK
```

`LICENSE`: `gh api licenses/agpl-3.0 --jq .body > LICENSE`

- [ ] **Step 4: lock とテストの入口を確かめる**

```bash
cd /workspaces/reso-world/external/resoloop-meshy
uv lock
uv run pytest; echo "exit=$?"          # Expected: no tests ran、exit=0
printf 'def helper():\n    pass\n' > tests/test_placeholder.py
uv run pytest; echo "exit=$?"          # Expected: no tests ran、exit=5（テストのファイルがあるので既定に戻る）
rm -- tests/test_placeholder.py
```

- [ ] **Step 5: 初期コミットを push する**

```bash
git -C /workspaces/reso-world/external/resoloop-meshy add -A
git -C /workspaces/reso-world/external/resoloop-meshy status --short   # .venv・.pytest_cache が入っていないこと
git -C /workspaces/reso-world/external/resoloop-meshy commit -m "chore: scaffold resoloop-meshy plugin repository"
git -C /workspaces/reso-world/external/resoloop-meshy push -u origin main
bash scripts/resoloop-meshy.sh status   # Expected: (main, clean)、remote: origin is as expected
bash scripts/resoloop-meshy.sh clone    # Expected: ok: ... is already cloned
gh api repos/usaturn/resoloop-meshy --jq '.visibility, .default_branch'   # Expected: private、main
```

### Task 4: 検証・記録・PR

**テストの要否:** 新しいテストは無い。既存の一括検証を実行する。

**Files:**
- Modify: Spec と Plan（状態と結果の記録）

- [ ] **Step 1: 一括検証**

Run: `bash scripts/check-layout.sh` と `bash .devcontainer/run-tests.bash`（worktree のルートで）
Expected: どちらも成功。失敗したら、変更によるものか環境によるものかを切り分けて記録する

- [ ] **Step 2: Spec・Plan に結果を記録してコミットする**

状態は draft のまま（内容の承認は得ていない）。「結果」の節に、作ったリポジトリ・初期コミットの SHA・検証の結果・所要時間を書く

- [ ] **Step 3: push と PR の作成**

```bash
git push -u origin feat/issue-96-plugin-repo
gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-96-plugin-repo --title "..." --body "..."
```

PR の本文に、決定（D-1〜D-3）、受け入れ条件と検証の結果、マージは利用者の指示によること、`Closes #96` は書かず `Refs #96`（completed での close は調整役と利用者の判断）を書く

- [ ] **Step 4: Issue に記録し、予約を解放する**

#96 に、決めた名前・作業ルート・PR・リポジトリ・状態（planning: done 相当で実装済み、PR はマージ待ち）・handoff を作らなかった理由（Spec D-10）を書く。予約は `git push --force-with-lease=refs/heads/agent-claims/issue-96:b066ccef078603e70438a4f36e2c8ffcd4d0388c origin :refs/heads/agent-claims/issue-96` で解放し、ref が無くなったことを確かめる
