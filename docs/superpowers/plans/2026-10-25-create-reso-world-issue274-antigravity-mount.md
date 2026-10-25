# Issue #274 Antigravity CLI の mount を揃える Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者の 2026-10-25（JST）の指示（`/issue-to-pr https://github.com/usaturn/create-reso-world/issues/274 --merge`。Spec の「実行許可」と同じ範囲）

**Goal:** PR #272 で足した Antigravity CLI の mount を、`initialize.bash`・`test-initialize-mounts.bash` の固定の一覧・`install_beforehand.bash` の書き込み可能にする一覧・README の表・`update()` に揃え、main の `check-layout.sh` と `run-tests.bash` を終了コード 0 に戻す。

**Architecture:** 設定とシェルの数行ずつの変更だけで、仕組み（`mounts.bash` の比較）は変えない。mount の書き方を他の行に合わせ、mount の露出を守る固定の一覧（F∩S）を意図した追加に合わせて更新し、関係する一覧・表・実行権限を揃える。

**Tech Stack:** bash、JSON with comments（devcontainer.json）、Markdown

**Spec:** `docs/superpowers/specs/2026-10-25-create-reso-world-issue274-antigravity-mount-design.md`

## Global Constraints

- devcontainer.json の Antigravity CLI の行は `"source=${localEnv:HOME}/.gemini/antigravity-cli,target=/home/vscode/.gemini/antigravity-cli,type=bind,consistency=cached",`（D-274-1）
- test-initialize-mounts.bash の固定の一覧は 15 個。`.gemini/antigravity-cli` は `.cursor` と `.local/share/create-reso-world/resonite-screenshots` の間（`LC_ALL=C sort` の順）。コメントは「15 個」（D-274-2）
- install_beforehand.bash の一覧は `"${HOME}/.cursor"` の後に `"${HOME}/.gemini"`、`"${HOME}/.gemini/antigravity-cli"` の順（D-274-3）
- README の表の行は Devin の行の後（D-274-4）
- `update()` の項目は `update_if_present agy agy update`（D-274-5）
- `initialize.bash` と `install_beforehand.bash` は 100755（D-274-6）
- テストを足さない（D-274-7）
- ログ・検証の記録・SDD の ledger は worktree の外の `/workspaces/reso-world/tmp/agents/issue-274.nc182s8l/` に置く（`AGENTS.md` の「コミットしないファイルの置き場所」）

## Review Focus

新しいテストは足さない（D-274-7）ので、各項目は下の Task の検証の手順で確かめる。

1. check-layout は git の index から devcontainer.json などを取り出して比べるので、未 commit の変更で通ったと誤認する → Task 1 の Step 4 は commit の後に実行する
2. 固定の一覧の並びが `LC_ALL=C sort` と違い、`unexpected mounts` で落ちる → Task 1 の Step 3 の test-initialize-mounts.bash
3. install_beforehand.bash の行末の `\` の抜けで、for の一覧が途中で切れる・構文エラーになる → Task 2 の Step 4 の `bash -n` と、一覧の取り出しの確かめ
4. `update_if_present` に渡す引数の誤りで、`agy` があっても更新されない・無いときに飛ばされない → Task 2 の Step 4 の一時的な確かめ（`agy` がある場合と無い場合）
5. README の表の行の列数が他の行と違い、表が崩れる → Task 2 の Step 4 の列数の確かめ

## 要件と Task の対応（実装前の照合）

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 1 3 つのコマンドが commit の後に終了コード 0 | Task 1（mount）、Task 3（全体。統合担当: このセッション） | 3 つとも 0 | Task 1 の Step 4、Task 3 の Step 4 のログ |
| 2 末尾が `/` の source・target が無い | Task 1 | `grep` で 0 件 | Task 1 の Step 3 |
| 3 固定の一覧が 15 個で `.gemini/antigravity-cli` を含み、コメントが「15 個」 | Task 1 | 差分と test-initialize-mounts.bash の PASS | `git diff`、Task 1 の Step 3 |
| 4 書き込み可能にする一覧に親・子の順で入り、`bash -n` が通る | Task 2 | 一覧の取り出しの結果と `bash -n` の終了コード 0 | Task 2 の Step 4 |
| 5 README の表の行の値が設計と #272 に一致 | Task 2 | 列数 6、値が一致 | Task 2 の Step 4 |
| 6 `update_if_present agy agy update`、無いときに飛ばす | Task 2 | 一時的な確かめの出力 | Task 2 の Step 4 |
| 7 2 つのスクリプトが 100755 | Task 2 | `git ls-files -s` | Task 2 の Step 4 |
| 8 README の「テスト」の入口がすべて 0 | Task 3（統合担当: このセッション） | 3 つのコマンドの終了コード | ログ・検証の記録 |

共有する条件: mount の一覧（`.gemini/antigravity-cli`）を devcontainer.json・initialize.bash・test-initialize-mounts.bash・install_beforehand.bash・README の表の 5 か所が持つ。前の 3 か所は Task 1 の test-initialize-mounts.bash と check-layout.sh が突き合わせ、後の 2 か所は Task 3 の Step 1 でこのセッションが値を照合する。ほかに共有する入力・状態・順序・外部仕様は無い。

## 実行方式

`superpowers:executing-plans`（このセッションが inline で実装する）。`implement_task.py check` が `self=true` で、変更は 5 つのファイルの数行ずつ。子に文脈を渡す手間が実装より大きい（Spec の D-274-8）。最後に、ブランチ全体のレビューを新しいレビュアー（サブエージェント 1 つ）に依頼する。

## 実行予算

- 全体の能動時間: 270 分（ledger の予算。ledger の開始は 2026-10-25T09:04:00Z で、それより前の準備（Issue・競合の確認、worktree の作成、Spec）は含まない）。実装・PR の作成まで 45 分、`--merge` のループの段階 225 分（サイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 約 30 分））。ledger は `/workspaces/reso-world/tmp/agents/issue-274.nc182s8l/budget.jsonl`
- phase の目安: Plan 5 分、Task 1 で 5 分、Task 2 で 10 分、Task 3（最終レビュー・記録・README の入口）で 20 分、PR 5 分、ループ 225 分
- worker: 実装は inline。README の入口の検証はバックグラウンドで実行し、終了の通知で待つ。絶対期限は README の入口の全体が 60 分（pytest の基準は 1225 passed で数分〜20 分）。ログが 10 分変わらなければ stall を疑う。最終レビューのサブエージェントは 1 回で、期限 30 分。ループの worker の期限は pr-review-fix-loop の SKILL.md のとおり
- 再試行の上限: 同じ失敗の再試行は 1 回まで
- checkpoint: 各 Task の完了時、PR の作成時、予算の 50%（135 分）・100%、検証の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) README の入口が今回の変更と無関係に失敗したら、`origin/main`（親の checkout）で同じコマンドを実行して既存の失敗と切り分ける (2) README の表や `update()` の変更（D-274-4・D-274-5）にレビューで異論が出たら、mount の 2 か所（Task 1）だけに縮小し、Spec の決定記録に追記する

## Contingency

1. Task 1 の Step 3・4 で、mount 以外の失敗が出たら、親の checkout（`08255ca`）で同じコマンドを実行して既存の失敗かを切り分け、記録する
2. Task 2 の一時的な確かめで `update_if_present` が期待どおり動かなければ、`zshrc.txt` を zsh で読む前提（`print -u2`）を確かめ、zsh で関数だけを取り出して実行し直す

---

### Task 1: mount の書き方と固定の一覧

**Files:**
- Modify: `.devcontainer/devcontainer.json:14`
- Modify: `.devcontainer/test-initialize-mounts.bash:20-35`（2 の検査のコメントと `expected`）

**Interfaces:**
- Produces: mount の相対パス `.gemini/antigravity-cli`（Task 2 の README の表と install_beforehand.bash が同じ値を使う）

**テストの要否:** テストを足さない。test-initialize-mounts.bash の固定の一覧は mount の露出を守る既存の F∩S の値で、意図した mount の追加に合わせて値を更新するだけ（Spec の D-274-7）。確かめは test-initialize-mounts.bash と check-layout.sh の実行で行う。

- [ ] **Step 1: devcontainer.json を直す** — 14 行の source と target の末尾の `/` を外し、Global Constraints の 1 行目のとおりにする
- [ ] **Step 2: 固定の一覧を直す** — test-initialize-mounts.bash の 2 のコメントの「14 個」を「15 個」にし、`expected` の `.cursor` の次の行に `.gemini/antigravity-cli` を足す
- [ ] **Step 3: 実行する** — worktree のルートで次を実行し、ログを `/workspaces/reso-world/tmp/agents/issue-274.nc182s8l/task1.log` に書く。期待: `grep` は 0 件（終了コード 1）、test-initialize-mounts.bash は `PASS: mounts agree with initialize.bash, which keeps ~/.claude.json` で終了コード 0

```bash
grep -nE '"source=[^"]*/,|target=[^,"]*/,' .devcontainer/devcontainer.json
bash .devcontainer/test-initialize-mounts.bash
```

- [ ] **Step 4: commit して check-layout を実行する** — commit の後に `bash scripts/check-layout.sh` を実行し、`FAIL` が無く終了コード 0 であることを確かめる（check-layout は index から取り出して比べるため、commit の後に実行する）。ログは同じファイルに追記する

```bash
git add .devcontainer/devcontainer.json .devcontainer/test-initialize-mounts.bash
git commit -m "fix(devcontainer): align the Antigravity CLI mount with initialize.bash and the fixed mount list (#274)"
```

### Task 2: 関係する一覧・表・実行権限を揃える

**Files:**
- Modify: `.devcontainer/install_beforehand.bash:54-70`（書き込み可能にするディレクトリの一覧）
- Modify: `.devcontainer/README.md:30` の後（ツールの表）
- Modify: `.devcontainer/zshrc.txt:422`（`update()` の `agy update`）
- Mode: `.devcontainer/initialize.bash`、`.devcontainer/install_beforehand.bash`（100644 → 100755）

**Interfaces:**
- Consumes: Task 1 の mount の相対パス `.gemini/antigravity-cli`

**テストの要否:** テストを足さない。README の表は F、書き込み可能にする一覧の漏れと `update()` の項目は普段の利用で現れる（L）。実行権限も L（Spec の D-274-7）。確かめは Step 4 の一時的な実行で行う。

- [ ] **Step 1: install_beforehand.bash の一覧に足す** — `"${HOME}/.cursor"; do` を `"${HOME}/.cursor" \`、`"${HOME}/.gemini" \`、`"${HOME}/.gemini/antigravity-cli"; do` の 3 行にする
- [ ] **Step 2: README の表に行を足す** — Devin の行の次に次の行を足す

```markdown
| Antigravity CLI | installer（`antigravity.google/cli/install.sh`） | `~/.gemini/antigravity-cli` | `~/.gemini/antigravity-cli` | `agd`（alias） | `agy update` |
```

- [ ] **Step 3: `update()` と実行権限を直す** — `zshrc.txt` の `    agy update` を `    update_if_present agy agy update` にする。`git update-index --chmod=+x` と `chmod +x` で 2 つのスクリプトを 100755 にする
- [ ] **Step 4: 確かめる** — 次を実行し、ログを `/workspaces/reso-world/tmp/agents/issue-274.nc182s8l/task2.log` に書く
  - `bash -n .devcontainer/install_beforehand.bash` が終了コード 0
  - `sed -n '/^for dir in \\$/,/; do$/p' .devcontainer/install_beforehand.bash` の出力の末尾 3 行が `.cursor`・`.gemini`・`.gemini/antigravity-cli` の順で、`.gemini/antigravity-cli` の行が `; do` で終わる
  - README の表の Antigravity CLI の行の `|` が 7 個（列が 6 個）で、他の行と同じ
  - `update()` の一時的な確かめ: `zshrc.txt` から `update_if_present` の関数を取り出し、zsh で `PATH` に偽の `agy`（引数を表示するだけ）を置いた場合と置かない場合に `update_if_present agy agy update` を実行する。期待: 置いた場合は偽の `agy` が `update` を受け取る、置かない場合は `update: agy not found; skipped: agy update` を stderr に出して終了コード 0。偽の `agy` は `mktemp -d` のディレクトリに置き、確かめた後に消す
  - `git ls-files -s .devcontainer/initialize.bash .devcontainer/install_beforehand.bash` がどちらも 100755
- [ ] **Step 5: commit**

```bash
git add .devcontainer/install_beforehand.bash .devcontainer/README.md .devcontainer/zshrc.txt .devcontainer/initialize.bash
git commit -m "fix(devcontainer): list the Antigravity CLI directories, tool row and update step; restore script modes (#274)"
```

### Task 3: 統合の確認と記録

**担当:** このセッション（統合担当）。**テストの要否:** 新しいテストは書かない。README の「テスト」の入口と最終レビューで確かめる。

- [ ] **Step 1: 条件ごとの照合** — 上の「要件と Task の対応」の各行について、差分・ログの該当箇所を挙げる。共有する条件として、`.gemini/antigravity-cli` が 5 か所で同じ値であることを `grep -rn 'antigravity' .devcontainer/` で確かめる
- [ ] **Step 2: 最終レビュー** — 新しいレビュアー（サブエージェント 1 つ）にブランチ全体（`origin/main...HEAD`）を渡し、Spec・Plan との一致、テストの採用基準、Review Focus を確かめさせる。Critical・Important を直したら、関係する検証をやり直してから Step 1 からやり直す
- [ ] **Step 3: 記録** — 下に「完了」の節を足し、所要時間と主要 Task 別の内訳、Task 1・2 の検証の結果、レビューの結果を書いて commit する。これを最後の commit にする（`--merge` の検証の記録は最後の commit の後に作る）
- [ ] **Step 4: README の「テスト」** — 最後の commit の後に、worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を実行する。終了コード・ログの完全パス・検証した HEAD・`git status --porcelain` が空だったことを `/workspaces/reso-world/tmp/agents/issue-274.nc182s8l/` に記録し、`finalize.py` の `--checks-file` の形のファイルも作る。結果は PR の本文に書く（この Plan には書かない。書くと HEAD が変わる）
