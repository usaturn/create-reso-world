---
name: repo-cleanup-after-merge
description: Use when ユーザーが、PR がマージされた後のローカルリポジトリの片付けを依頼する場合。マージ済み branch の削除、使い終わった worktree の整理、レビュー用の使い捨て worktree の残骸の掃除、作業ツリーの origin/main への追従が対象。未マージの作業のリベース、コンフリクト解消、リリース作業には使用しない。例:「PR が全て Merge されたことを確認して branch, worktree を整理してローカルを更新して」「マージ済みのブランチを消して」「worktree を掃除して」「origin/main に追従して」「リポジトリを整理して」
allowed-tools: Read, Grep, Glob, AskUserQuestion, Bash(git *), Bash(gh *), Bash(ls *), Bash(diff *), Bash(cmp *), Bash(find *), Bash(cp *), Bash(rm *), Bash(uv run --no-project python -c *), Bash(bash scripts/resoloop-fork.sh sync)
---

# マージ後のリポジトリ整理

## 概要

PR がマージされた後に、ローカルの branch / worktree / 残骸を片付け、作業ツリーを `origin/main` に追従させる。ただし、`MyResoniteProject/`・`akichi/`・`slum02/`・`slum03/`・`worlds/` の追跡ファイルを削除する更新は自動実行せず、README の「追跡解除コミットを取り込む」の保全手順を利用者へ案内する。

**中核原則: 整理とは「消すこと」ではなく「もう失うものが無いと確かめてから消すこと」である。**

git の操作はほぼ全て取り消せる。取り消せないのは次の 2 つだけであり、この 2 つにだけ注意を集中する。

- **ゲート A**: git 管理外ファイルの `rm` — 復元手段が無い
- **ゲート B**: リモートへの push（ブランチ削除を含む）— 他人が見る共有物への外向き操作

## 対象リポジトリの確定

整理対象の PR が属するリポジトリで root を決める。対応はルート `AGENTS.md` の「リポジトリ境界」の表に従う。

- `usaturn/create-reso-world`（このリポジトリ）の PR: リポジトリのルート（`git rev-parse --show-toplevel`）が root である
- `usaturn/resoloop` または `orange3134/resoloop` の PR: fork の checkout `external/resoloop`（リポジトリのルート基準）が root である。Git コマンドは `git -C external/resoloop ...`、`gh` 呼び出しには PR が属するリポジトリに合わせて `--repo usaturn/resoloop` か `--repo orange3134/resoloop` を付けて実行する。checkout が無い、または `origin` が `usaturn/resoloop`、`upstream` が `orange3134/resoloop` でない場合は、`scripts/resoloop-fork.sh clone` を案内して停止する
- それ以外: 推測せず停止する

両方にまたがる整理は、リポジトリごとにこの手順を回す。手順 6 の `session.json` の `destination` は相対パス（`reviews/<dir>/<model>.md`）であり、同じ `session.json` の `main_root` に結合して正本パスを得る（fork の経路では `main_root` が `external/resoloop` 配下を指す）。

### fork の経路（`external/resoloop`）だけの手順

fork の checkout は、`scripts/resoloop-fork.sh checkout <ref>` や `install <ref>` が取り出したコミットで detached HEAD になっていることが多く、利用者が作業ブランチにいることもある。`build` はこれを動かさない。この前提から、fork の経路は次の順で進める。

1. ユーザー確認を得てから（Claude Code では AskUserQuestion）、手順 10 の `sync` を先に実行し、fork の `main` を上流へ追従させる。手順 2 の `fetch --prune` の前でよい
2. マージ済みかの判定（手順 3）は、上流 `orange3134/resoloop` 発の PR は `upstream/main` を、fork 内（`usaturn/resoloop` 発）の PR は `origin/main` を基準にする。`sync` を先に済ませていないと、上流でマージ済みの PR がこの fork の `origin/main` ではまだ未取り込みに見える
3. 手順 7（メイン作業ツリーを `origin/main` の detached HEAD に更新する操作）は実行しない。`external/resoloop` の HEAD は、detached でもブランチでもそのまま残す。誤って動かしていた場合は、`git -C external/resoloop reflog` で元の位置を確かめて戻す

`bash scripts/resoloop-fork.sh sync` と `git -C external/resoloop ...` は、エージェントがどの作業ディレクトリから開始していても、リポジトリのルート（`cd "$(git rev-parse --show-toplevel)"`）で実行する。

## ワークフロー

### 1. 何も消す前に状態を把握する

次の read-only コマンドを実行する。

```bash
git status
git worktree list --porcelain
git branch -vv
git remote -v
gh pr list --state open --json number,title,headRefName,headRefOid
gh pr list --state all --limit 20 --json number,title,state,headRefName,mergedAt
```

`gh` が非0終了した場合、PR の状態は不明である。マージ判定を推測で進めず、エラーを報告して停止する。

Open PR が 1 件以上ある場合、次は **整理対象外**である。残存 PR をユーザーへ報告し、それ以外だけを進める。

- `headRefName` に一致する branch
- その branch をチェックアウトしている worktree
- `git worktree list --porcelain` の `HEAD` が、オープン PR の `headRefOid` と一致する worktree（detached でも対象外）
- パスが `/tmp/pr-review-*` の worktree と、その親ディレクトリ。親の `session.json` の `head_branch` がオープン PR の `headRefName` である場合も含む

### 2. リモートを取り込む

```bash
git fetch --all --prune
```

**マージ判定より前に必ず実行する。** ローカルの `origin/main` は古いのが普通であり、fetch 前の「マージ済みか」の判定は誤る。

### 3. マージ済みか判定する

`usaturn/create-reso-world` の既存ローカル `main` は保持対象であり、この判定から除外する。古い・分岐している場合もそのまま残し、対応する PR の `MERGED` 確認は要求しない。fork の経路でも `external/resoloop` のローカル `main`（ベース branch）を同様に除外し、削除しない。

それ以外の branch ごとに次を実行する。

```bash
git log --oneline origin/main..<branch>
```

- 出力が空: `origin/main` に取り込み済みである。`gh pr list --state all` の対応する要素が `"state": "MERGED"` であることも確認する。
- 出力がある: 未取り込みである。この branch と対応する worktree は削除しない。

fork の経路で上流 PR を判定する場合は基準が異なる。「fork の経路だけの手順」を見る。

### 4. 削除候補の worktree ごとに clean を確認する

`usaturn/create-reso-world` のメイン作業ツリーと、ローカル `main` を checkout している他の worktree は削除対象から外す。手順 7 は detached checkout なので、他 worktree が `main` を保持していても進められる。`main` を解放するためにその worktree を削除・detach・更新しない。

以下の dirty / ignore 対象ファイルに関する削除・退避のユーザー確認は、削除候補の worktree にだけ必要である。ただし、保持するメイン作業ツリーも手順 7 の `MAIN_ROOT` の clean 確認は省略せず、dirty または status 失敗なら checkout と後続の branch 削除を停止する。

```bash
git -C <worktree の絶対パス> status --short
git -C <worktree の絶対パス> status --short --ignored
```

`-C` には絶対パスを渡す。worktree 隔離セッションでは相対パスが拒否されることがある。1 つ目に出力がある worktree は **削除しない**。ユーザーへ報告して判断を仰ぐ。

`git worktree remove` は ignore 対象のファイルを確認せずに消す。2 つ目の出力の `!!` の行（ignore 対象）も確かめる。再生成できるキャッシュ（`.venv/`、`.uv-cache/`、`.pytest_cache/`、`.ruff_cache/`、`__pycache__/`、`node_modules/`）だけなら、worktree と一緒に消えてよい。それ以外（`reviews/`、`docs_draft/`、`tmp/`、`external/`、`private/`、`.superpowers/`、各プロジェクトの `.resoloop/` など）が 1 つでもある worktree は **削除しない**。一覧をユーザーへ報告し、正本への退避か削除の確認を得るまで残す（ゲート A と同じ扱い）。

#### 毎回ここで止まるなら、直すのは片付け側ではなく生成側である

削除候補の worktree にある untracked ファイルは正本と照合する述語を持たないため、ゲート A の対象として必ず人間の判断を要求する。同じ種類のファイルで毎回止まるのは、**worktree 内に判定不能な生成物を残す手順が上流にある**ということである。ゲートを緩めて解決してはならない。

報告時は「どのスキル・どの手順の生成物か」を添えて指摘し、生成側を次の原則へ合わせるよう促す。

**生成物は worktree の外（scratchpad / `mktemp -d`）に出す。** untracked が発生しないので手順 4 で止まらない。本スキルは worktree 直下の untracked を機械的に照合する述語を持たない。手順 6 のゲート A は `session.json` を持つ残骸ディレクトリ専用であり、worktree 内に残す限り毎回ユーザー確認になる。

`.gitignore` への追加で黙らせてはならない。gitignore 対象は、再生成できるキャッシュを除き、本スキルのガードレールで照合なしの削除を禁じており、`git status` からも消えるため、照合する術が無いまま残り続ける。

### 5. worktree を削除する

手順 1 で対象外にした worktree（オープン PR の `headRefOid` と HEAD が一致するもの、`/tmp/pr-review-*` で親 `session.json` の `head_branch` がオープン PR と一致するもの）は削除しない。削除するのは、手順 4 で clean を確認し、ignore 対象が再生成できるキャッシュだけだった worktree に限る。

```bash
git worktree remove <path>
git worktree prune
```

`--force` は付けない。`git worktree remove` が拒否した場合（未追跡のファイルがある、lock されているなど）は、理由をユーザーへ報告して止まる。

worktree 本体の削除と、手順 6 の残骸削除は **別の判断**である。worktree 本体は追跡済みの内容であり、マージ済み・clean を確認していれば削除してよい。手順 6 で保留が発生しても、worktree 本体の削除まで止める必要はない。

### 6. ゲート A: 残骸ディレクトリは照合してから消す

`git worktree remove` は作業ツリーだけを消す。親ディレクトリに残る `session.json` や `review-backup/` は **git 管理外**であり、`git status` にも `git worktree list` にも現れない。

正本パスは残骸ディレクトリの `session.json` の `destination`（`reviews/<dir>/<model>.md` の相対パス）を、同じ `session.json` の `main_root` に結合して取る。branch 名の変換で推測しない。

```bash
uv run --no-project python -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); print(d["main_root"] + "/" + d["destination"])' <残骸ディレクトリ>/session.json
```

`session.json` が無い、`main_root` または `destination` が読めない、または結合した正本パスがリポジトリの `reviews/` 配下に無い場合は削除せず停止する。

```bash
diff -rq <残骸ディレクトリ>/review-backup <正本ディレクトリ> > /tmp/gate-a.out 2> /tmp/gate-a.err; echo $?
```

削除してよいのは、次をすべて満たすときだけである。空の `grep '^Only in .*review-backup'` だけを削除許可にしてはならない。

- `diff` の stderr（`/tmp/gate-a.err`）が空である。正本ディレクトリ不在はここに出る（終了コード 2）。stderr があれば削除しない
- stdout に `Files ... differ` が無い
- stdout の `Only in ...review-backup` が、`previous-review.md` 以外に無い。`previous-review.md` はセッション snapshot であり、正本へコピーせず、この判定からも除外する

どれか一つでも欠ければ削除しない。

- `Only in ...review-backup` の対象が `<model>.md` なら正本へ `cp` する。コピーは非破壊であり、AskUserQuestion は不要。コピー後に述語を再実行する
- `previous-review.md` は正本へコピーしない
- `Files ... differ` の `<model>.md` は正本を上書きしない。残すか別名退避するかをユーザーに確認し、確認が終わるまで残骸は消さない

```bash
cp <残骸ディレクトリ>/review-backup/<model>.md <正本ディレクトリ>/
```

`reviews/` は `.gitignore` 対象であり、git は一切保護しない。

### 7. メイン作業ツリーを origin/main の detached HEAD へ更新する

fork の経路ではこの手順を実行しない。「fork の経路だけの手順」を見る。

`usaturn/create-reso-world` では、ルート `AGENTS.md` に従い、ローカル `main` の有無にかかわらず detached HEAD にする。既存の `main` は古い・分岐している場合も変更せず保持する。作成・切り替え・reset・fast-forward は行わない。

入力 `MAIN_ROOT` は、手順 1 の `git worktree list --porcelain` の先頭の `worktree <絶対パス>`（メイン作業ツリー）から特定し、下のブロックを実行するシェルに事前に設定する。linked worktree やプロジェクトからの呼び出しでは、cwd や `git rev-parse --show-toplevel` の結果をメイン作業ツリーと取り違えない。パスを特定できなければ停止して報告する。

ブロック内でメイン作業ツリーの clean を再確認する。出力が空でない、または status が失敗した場合は checkout も後続の branch 削除もせず、ユーザーへ報告する。

続いて、HEAD と `origin/main` の tree 間で保護領域の追跡ファイル削除を read-only で調べる。取得失敗または削除対象が 1 件でもあれば、checkout と後続の branch 削除を停止する。`--no-renames` は、rename と判定されて元のパスの削除を見落とさないために必要である。

```bash
set -e
: "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}"
if ! tree_state=$(git -C "$MAIN_ROOT" status --short --untracked-files=all); then
    printf '%s\n' 'status の確認に失敗したため、checkout と branch 削除を停止する。' >&2
    exit 1
fi
if [ -n "$tree_state" ]; then
    printf '%s\n' "$tree_state"
    printf '%s\n' '作業ツリーが clean でないため、checkout と branch 削除を停止する。' >&2
    exit 1
fi
if ! deleted_world_paths=$(git -C "$MAIN_ROOT" diff --no-renames --name-only --diff-filter=D HEAD origin/main -- MyResoniteProject akichi slum02 slum03 worlds); then
    printf '%s\n' '保護領域の追跡ファイル削除を確認できないため、checkout と branch 削除を停止する。' >&2
    exit 1
fi
if [ -n "$deleted_world_paths" ]; then
    printf '%s\n' "$deleted_world_paths"
    printf '%s\n' '保護領域の追跡ファイルが削除されるため、checkout と branch 削除を停止する。README の「追跡解除コミットを取り込む」の保全手順を利用者へ案内する。' >&2
    exit 1
fi
if ! git -C "$MAIN_ROOT" checkout --detach --no-overwrite-ignore origin/main; then
    printf '%s\n' 'checkout に失敗したため、branch 削除を停止する。' >&2
    exit 1
fi
head_name=$(git -C "$MAIN_ROOT" rev-parse --abbrev-ref HEAD)
head_oid=$(git -C "$MAIN_ROOT" rev-parse HEAD)
origin_oid=$(git -C "$MAIN_ROOT" rev-parse origin/main)
if [ "$head_name" != HEAD ] || [ "$head_oid" != "$origin_oid" ]; then
    printf '%s\n' 'detached HEAD と origin/main の一致を確認できないため停止する。' >&2
    exit 1
fi
```

Git は通常 ignore 対象のファイルを確認なしに上書きするため、`--no-overwrite-ignore` を外さない。ただし、clean でも `--no-overwrite-ignore` でも追跡ファイルの削除は防げない。保護領域の削除検査を外したり、自動復元や `--force` で回避したりしない。checkout が失敗したらエラーを報告して停止し、`--force`・clean・reset や `main` への切り替えで回避しない。成功後も既存ローカル `main` は保持対象として報告し、手順 8 で削除しない。

### 8. マージ済みローカル branch を削除する

手順 7 が成功したあとで実行する（fork の経路では手順 7 を省略する）。手順 7 で停止した場合は branch 削除に進まない。`usaturn/create-reso-world` の既存ローカル `main` と、fork の経路では `external/resoloop` のローカル `main` は、マージ済みでも候補から必ず除外し、そのまま保持する。メイン作業ツリーが feature を checkout したままだと `git branch -d` は `used by worktree` / `checked out` で失敗する。

以下は `usaturn/create-reso-world` 用である。削除は、手順 7 で更新した `MAIN_ROOT` を対象にする。ツール呼び出しごとにシェルや環境変数が引き継がれない実行環境があるため、手順 7 と別の呼び出しでこのブロックを実行するときも、その呼び出しで `MAIN_ROOT` を設定する。fork の経路では、リポジトリのルートで `git -C external/resoloop branch -d <branch>` に読み替える。fork では手順 7 を省略し、削除のために HEAD を動かさない。`MAIN_ROOT` の設定も要求しない。

```bash
git -C "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}" branch -d <branch>
```

`-D` は使わない。例外は、後述の `merge-base` 再確認で取り込み済みと確かめた branch だけである。

`-d` が拒否した場合、理由で分岐する。拒否を未マージと同一視しない。

- `used by worktree` または `checked out`: 未マージではない。手順 7 が済んでいなければ手順 7 に戻る。他 worktree が掴んでいるならその worktree を残し、この branch は削除しない
- `not fully merged`: そのまま未マージと断定しない。`-d` の取り込み判定は upstream と実行先の HEAD を基準にするため、upstream の remote-tracking ref が削除・prune 済みのときや、実行先の HEAD がその branch の取り込み点より古いときは、マージ済みでも拒否される。fork の経路では削除のために HEAD を動かさないので、古い detached HEAD へのこの拒否は普通に起きる。手順 3 と同じ基準へ再確認する。create-reso-world では `git -C "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}" merge-base --is-ancestor <branch> origin/main`、fork の経路では `git -C external/resoloop merge-base --is-ancestor <branch> <基準>`（上流 PR の基準は `upstream/main`、fork 内 PR は `origin/main`）を実行する。取り込み済みならその branch に限り `git -C <対象> branch -D <branch>` で削除してよい。明示的な取り込み確認を済ませた上での削除であり、マージ判定を握り潰すことには当たらない（`-D` も worktree に掴まれた branch は拒否する）。未取り込み、または再確認できない場合は削除せず、手順 3 の結果とともにユーザーへ報告する

detached HEAD では次の warning が出るが、**削除が成功していれば正常**である。upstream にマージ済みであることは確認できており、拒否ではない。

```
warning: deleting branch '<branch>' that has been merged to
         'refs/remotes/origin/<branch>', but not yet merged to HEAD
```

### 9. ゲート B: リモート branch の削除はユーザー確認を得る

手順 8 でローカル branch を消すと対象名が手元から消える。リモート側から独立に洗い出す。

```bash
git branch -r --merged origin/main | grep -E '^ *origin/' | grep -vE 'origin/(HEAD|main)$'
```

候補が複数ある場合は、手順 1 で取得した `gh pr list --state all` の `headRefName` と突き合わせ、**どの PR 由来か**を添えて提示する。対応する PR が見つからないリモート branch は候補から外し、そのまま残す。

マージ済みでも、リモート branch の削除を独断で実行しない。対象を提示してユーザー確認を求め（Claude Code では AskUserQuestion を使う）、承認を得てから実行する。

```bash
git push origin --delete <branch>
git fetch --prune
```

### 10. resoloop の上流に追従する（fork の経路だけ）

上流 `orange3134/resoloop` で PR がマージされたら、fork の `main` を上流へ追従させる。リポジトリのルートで実行する。fork の経路ではこの手順を手順 3 の判定より先に行う。「fork の経路だけの手順」を見る。

```bash
bash scripts/resoloop-fork.sh sync
```

`sync` は fork（`usaturn/resoloop`）の `main` へ push するので、ゲート B と同じくユーザー確認を得てから実行する（Claude Code では AskUserQuestion を使う）。fork の `main` に上流に無いコミットがある場合、スクリプトは何も push せずに止まる。`external/resoloop` で `main` を checkout していて未コミットの変更がある場合は、fork の `main` への push を済ませてから、ローカルの `main` を動かさずに止まる（出力に `origin/main is already synced` と出る）。その出力をそのまま報告し、手で push や reset をしない。詳しい流れは `docs/resoloop-fork-workflow.md` にある。

### 11. 最終状態を報告する

以下は `usaturn/create-reso-world` 用である。status は更新対象の `MAIN_ROOT` で確認する。手順 8 と同様、このブロックを実行する呼び出しでも `MAIN_ROOT` を設定する。fork の経路では、リポジトリのルートで各 Git コマンドに `-C external/resoloop` を指定し、最初の行は `git -C external/resoloop status` に読み替える。fork では `MAIN_ROOT` の設定を要求しない。

```bash
git -C "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}" status
git -C "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}" worktree list
git -C "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}" branch -a
```

`usaturn/create-reso-world` では `MAIN_ROOT` の HEAD が detached で `origin/main` と一致することを報告する。既存ローカル `main` と、それを checkout している他 worktree は「変更せず保持」として報告する。削除した対象、保留した対象、その理由も報告する。

## Red Flags: 手を止めてワークフローに戻る

- 「Merge 済みなので役目は終えている」を根拠に git 管理外ファイルを消そうとしている
- 「ディレクトリ名が `stale` / `tmp` / `pr-review-*` だから」を削除の根拠にしている
- 中身を正本と照合せずに「軽微なメモ」「レビューのメタデータ」と分類している
- `rm -rf` を実行しようとしているが、直前に `diff` または `cmp` を実行していない
- `Files ... differ` や `diff` の失敗を無視して「固有ファイルが無いから消してよい」としている
- リモート branch を削除してから「不要なら戻せます」と報告しようとしている
- 「時間が無い」「手早く」と言われたので確認を飛ばそうとしている
- `git worktree remove` の前に `status --short --ignored` を見ていない

**いずれかに該当したら、削除を中止して手順 4・6・9 のいずれかに戻る。**

## 言い訳と現実

| 言い訳 | 現実 |
|---|---|
| 「PR は Merge 済みだから、レビュー成果物の役目も終わった」 | マージされたのは追跡対象のコードだけである。git 管理外のレビュー結果は 1 バイトもマージされていない |
| 「ディレクトリ名が stale なので消してよい」 | 名前は中身を保証しない。照合していないなら未保存データの有無を知らないだけである |
| 「中を見たら軽微なメモだった」 | 軽微だと判断したのではなく、正本と照合していないだけである。照合は `diff -r` 1 回で済む |
| 「内容差分があっても固有ファイルが無ければ失うものはない」 | 同名の未保存稿は `Files ... differ` になる。`previous-review.md` だけをコピーして消すと新しい原稿が消える |
| 「worktree は clean だったのでデータ損失はない」 | `git status` は gitignore 対象ファイルも、worktree の外にある残骸も見ない。`git worktree remove` は worktree 内の gitignore 対象ファイルを確認せずに消す |
| 「消した後で問題があれば言ってもらえばいい」 | `rm -rf` に取り消しは無い。削除の前だけが確認である |
| 「マージ済み branch の削除は cleanup の一環」 | ローカルはそうである。リモートは他人が見る共有物であり、外向きの操作である |
| 「手早くと言われた」 | 照合は数秒で終わる。失ったレビューの再生成はそれより桁違いに高い |
| 「untracked が出るのは仕方ない。毎回訊けばよい」 | 訊かれるのは、判定不能な生成物を作り続けている上流の手順があるからである。生成側を直せば訊く必要そのものが無くなる |
| 「毎回同じ確認で面倒なので `.gitignore` に入れる」 | `git status` から消えるだけで、復元不能なファイルであることは変わらない。gitignore 対象は、再生成できるキャッシュを除き、本スキルのガードレールで照合なしの削除を禁じており、判定不能なまま残り続ける |

## ガードレール

- `git branch -D` でマージ判定を握り潰さない。使ってよいのは、手順 8 の `merge-base` 再確認で取り込み済みと確かめた branch だけである。
- `git worktree remove` に `--force` を付けない。
- ユーザー確認なしに `git push`（`--delete` を含む）や `scripts/resoloop-fork.sh sync` を実行しない。
- Open PR が残っている branch と worktree を削除しない。detached な pr-review worktree も含む。
- gitignore 対象のファイルは、再生成できるキャッシュを除き、正本と照合するかユーザーの確認を得るまで削除しない（`reviews/`、`docs_draft/`、`tmp/`、`external/` など。worktree ごと消す場合も同じ）。
- コンフリクト解消、rebase、リリース作業は行わない。

## 関連スキル

- `pr-review` — `/tmp/pr-review-*/` の使い捨て worktree と `review-backup/` を作る側。手順 6 の残骸はこのスキルの生成物である
