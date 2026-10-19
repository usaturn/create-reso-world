# repo-cleanup-after-merge のゲート A の一時ファイルを `mktemp -d` のディレクトリに置く 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 手順 6（ゲート A）の `diff` の出力を、`/tmp` 直下の固定名のファイルではなく、その実行が `mktemp -d` で作ったディレクトリに書いて読み、同じ実行の中で消す。

**Architecture:** 変更は `.agents/skills/repo-cleanup-after-merge/SKILL.md` だけ。手順 6 のコマンド例を 1 回で実行するブロックにし、stdout・stderr を見出し付きで表示してから空値ガード付きで消す。判定の 3 条件は変えない。

**Tech Stack:** bash、GNU coreutils（`mktemp`・`diff`）

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue131-gate-a-mktemp-design.md`

- 状態: `draft`（内容の明示承認は受けていない。実行許可は Spec の「管理・実行許可」のとおり）

## Global Constraints

- 一時ディレクトリは `mktemp -d "${TMPDIR:-/tmp}/repo-cleanup-gate-a.XXXXXX"`。片付けは `rm -rf -- "${GATE:?}"`
- 削除の 3 条件、`<model>.md` のコピー、`Files ... differ` の保留の扱いは変えない
- 手順 6 以外の手順、他のスキル、#123 の Spec・Plan は変えない
- テストは書かない（`AGENTS.md` の「テストの採用基準」。文書の変更）

## Review Focus

1. ランタイムがブロックを複数の呼び出しに分けた → 後の呼び出しでは `GATE` が空になり、`rm` は `${GATE:?}` で止まって何も消さない（Task 2 の Step 4）
2. 正本ディレクトリが無い → stderr に出て終了コード 2 を表示し、ディレクトリは消える（Task 2 の Step 2 の場合 d）
3. 2 つのセッションが同時に実行する → それぞれが自分の fixture の結果だけを表示する（Task 2 の Step 3）
4. `mktemp` が失敗する（`TMPDIR` が無いディレクトリ）→ `exit 1` で止まり、`diff` を実行せず、`/stdout` などに書かない（Task 2 の Step 4）
5. 実行の後に一時ディレクトリが残る → どの場合も `${TMPDIR:-/tmp}/repo-cleanup-gate-a.*` が残らない（Task 2 の Step 2・3）

## 要件と Task の対応

| Spec の「必要な挙動」 | 担当 Task | 観測する結果 | 検証方法 |
|---|---|---|---|
| 1. 固定名を使わない | Task 1 | ブロックが `mktemp -d` のディレクトリに書く | Task 2 で `/tmp/gate-a.*` の作成・更新が無いこと |
| 2. 同じ実行のディレクトリから読み、見出しで表示 | Task 1 | 終了コード・`--- stderr ---`・`--- stdout ---` が出る | Task 2 の Step 2・3 |
| 3. 同じ実行の中で空値ガード付きで消す | Task 1 | 実行の後にディレクトリが残らない | Task 2 の Step 2〜4 |
| 4. 本文の参照を見出しに合わせる | Task 1 | `/tmp/gate-a.err` の参照が無い | Task 1 の Step 4（`git diff`・`grep`） |
| 5. 判定の条件・再実行 | Task 1 | 3 条件の文が変わらない | Task 1 の Step 4（`git diff`） |
| 6. `allowed-tools` に `Bash(mktemp *)` | Task 1 | frontmatter が読める | Task 3 の `tests/skills`（frontmatter の検査） |

共有する入力・状態・順序は無い（1 ファイルを 1 担当が変える）。

---

### Task 1: 手順 6 と frontmatter を書き換える

**テストの要否:** 不要。文書の変更で、守る挙動はコマンド例の実行で確かめる（Task 2）。

**Files:**
- Modify: `.agents/skills/repo-cleanup-after-merge/SKILL.md:4`（`allowed-tools`）
- Modify: `.agents/skills/repo-cleanup-after-merge/SKILL.md:164-176`（手順 6 のコマンド例・条件・コピー後の再実行）

**Interfaces:**
- Produces: 手順 6 の bash のブロック（`repo-cleanup-gate-a` を含む唯一のブロック。Task 2 が取り出して実行する）

- [ ] **Step 1: `allowed-tools` の `Bash(diff *)` の後に `Bash(mktemp *)` を足す**

- [ ] **Step 2: コマンド例を次に置き換え、直前に説明を 1 段落足す**

説明: 出力は `mktemp -d` で作ったディレクトリに書き、同じブロックで表示してから消す。固定名を使わない理由（並行するセッションの結果と混ざる）。ブロックを分けずに 1 回で実行する理由（シェルの変数が次の呼び出しに残らないランタイムがある）。

```bash
GATE=$(mktemp -d "${TMPDIR:-/tmp}/repo-cleanup-gate-a.XXXXXX") || exit 1
diff -rq <残骸ディレクトリ>/review-backup <正本ディレクトリ> > "$GATE/stdout" 2> "$GATE/stderr"
echo "diff の終了コード: $?"
echo '--- stderr ---'; cat -- "$GATE/stderr"
echo '--- stdout ---'; cat -- "$GATE/stdout"
rm -rf -- "${GATE:?}"
```

- [ ] **Step 3: 条件の文を見出しに合わせる**

`（/tmp/gate-a.err）` を `（--- stderr --- の下）` に、`stdout に` を `stdout（--- stdout --- の下）に` に変える。コピー後の「述語を再実行する」を「上のブロックを実行し直す」に変える。条件の中身は変えない。

- [ ] **Step 4: 差分を確かめる**

Run: `git diff -- .agents/skills/repo-cleanup-after-merge/SKILL.md` と `grep -n 'gate-a' .agents/skills/repo-cleanup-after-merge/SKILL.md`
Expected: 変更が frontmatter と手順 6 だけ。`grep` は `repo-cleanup-gate-a` の 1 行だけ

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/repo-cleanup-after-merge/SKILL.md
git commit -m "fix(repo-cleanup-after-merge): keep gate A diff output in a mktemp -d directory (#131)"
```

### Task 2: 書き換えたブロックを実行して確かめる

**テストの要否:** 不要（Issue の「検証」）。リポジトリにファイルを足さず、scratchpad の使い捨てのスクリプトで、`SKILL.md` から取り出したブロックをそのまま実行する。

**Files:** なし（scratchpad だけ）

**Interfaces:**
- Consumes: Task 1 のブロック。`<残骸ディレクトリ>`・`<正本ディレクトリ>` を fixture のパスに `sed` で置き換え、`bash` で 1 回ずつ実行する

- [ ] **Step 1: 実行前の状態を記録する**

`ls -d "${TMPDIR:-/tmp}"/repo-cleanup-gate-a.* 2>/dev/null` が空であること。`/tmp/gate-a.out`・`/tmp/gate-a.err` の有無と mtime を記録する。

- [ ] **Step 2: 4 つの fixture で実行する**

| 場合 | `review-backup/` | 正本 | 期待する表示 |
|---|---|---|---|
| a 削除してよい | `previous-review.md`、正本と同じ `m.md` | `m.md` | 終了コード 1、stderr 空、stdout は `Only in ...review-backup: previous-review.md` だけ |
| b differ | 正本と違う `m.md` | `m.md` | 終了コード 1、stdout に `Files ... differ` |
| c コピーの対象 | `previous-review.md`、`n.md` | `m.md` | stdout に `previous-review.md` 以外の `Only in ...review-backup`（`n.md`） |
| d 正本が無い | `m.md` | 無い | 終了コード 2、stderr に正本のパス、stdout 空 |

各実行の後に `repo-cleanup-gate-a.*` が残らないこと。

- [ ] **Step 3: 違う fixture（a と b）で 2 つの実行を同時に動かす**

Expected: それぞれの表示が Step 2 の a・b と同じで、相手の結果が混ざらない。実行の後に `repo-cleanup-gate-a.*` が残らない。

- [ ] **Step 4: 失敗の経路を確かめる**

- `TMPDIR` を存在しないディレクトリにして実行する。Expected: 終了コード 1、`diff の終了コード` の行が出ない、`/stdout`・`/stderr` が作られない
- `env -u GATE bash -c 'rm -rf -- "${GATE:?}"'`。Expected: 終了コード 1 と `GATE` のエラー、何も消さない

- [ ] **Step 5: `/tmp/gate-a.*` が Step 1 から変わっていないことを確かめ、結果を Plan の「実行記録」に書く**

### Task 3: 全体の検証・レビュー・PR

**テストの要否:** 新しいテストは書かない。既存のテストを実行する。

- [ ] **Step 1: README の「テスト」のコマンドを実行する（ワールドの行を除く）**

Run: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`
Expected: どれも終了コード 0。環境による失敗が出たら、`origin/main` の親の checkout でも同じかを確かめて切り分ける

- [ ] **Step 2: ブランチ全体のレビュー（新しいレビュアー 1 回）を行い、致命的な指摘だけ直す**

- [ ] **Step 3: Plan の「実行記録」を埋めて commit し、push の前の検査・push・PR 作成を issue-to-pr の 5 章のとおりに行う**

## 実行方式

`superpowers:executing-plans`（このセッションが自分で実装する）。`implement_task.py check` の `self` が true で、Task 1 の変更は 1 ファイル、Task 2・3 は検証なので、サブエージェントに渡す利点が無い。最後のブランチ全体のレビューだけ新しいレビュアーに依頼する。

## 実行予算

全体の能動時間の目安は 60 分（Task 3 つ、文書 1 ファイル）。単純な変更なので ledger は省く。同じ失敗の再試行は 1 回まで。超えそうなら止まって報告する。

## 実行記録

（実行後に書く）
