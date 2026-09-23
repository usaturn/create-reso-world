---
name: repo-cleanup-after-merge
description: PR がマージされた後にローカルリポジトリを片付けるときに使う。「PR が全て Merge されたことを確認して branch, worktree を整理してローカルを更新して」「マージ済みのブランチを消して」「worktree を掃除して」「origin/main に追従して」「リポジトリを整理して」といった依頼、および `git worktree list` に使い終わった作業ツリーが溜まっている、ローカルの `origin/main` が古い、レビュー用の使い捨て worktree の残骸が残っている、といった場面でトリガーする。
allowed-tools: Read, Grep, Glob, AskUserQuestion, Bash(git *), Bash(gh *), Bash(ls *), Bash(diff *), Bash(cmp *), Bash(find *), Bash(rm *)
---

# マージ後のリポジトリ整理

PR がマージされた後に、ローカルの branch / worktree / 残骸を片付け、作業ツリーを `origin/main` に追従させる。

**中核原則: 整理とは「消すこと」ではなく「もう失うものが無いと確かめてから消すこと」である。**

git の操作はほぼ全て取り消せる。取り消せないのは次の 2 つだけであり、この 2 つにだけ注意を集中する。

- **ゲート A**: git 管理外ファイルの `rm` — 復元手段が無い
- **ゲート B**: リモートへの push（ブランチ削除を含む）— 他人が見る共有物への外向き操作

## 対象リポジトリの確定

整理対象の PR が属するリポジトリで root を決める。`usaturn/maatlog`（公開アプリケーション）の PR なら `public/` submodule の checkout が root であり、Git コマンドは `git -C public ...`、`gh` 呼び出しには `--repo usaturn/maatlog` を付けて実行する。親 `usaturn/maatlog-poc` の PR なら親の toplevel が root である。両リポジトリにまたがる整理は、リポジトリごとにこの手順を回す。

公開経路では次が変わる。手順 7 の `git submodule update --init public` は親側だけの操作なので実行しない。手順 6 の `session.json` の `destination` は対象リポジトリ側の `reviews/` を指す（公開 PR なら `public/reviews/`）。手順 1 の `gh pr list` は `--repo usaturn/maatlog` で公開側を見る。

公開 checkout で手順 7 を実行すると、親には `modified: public (new commits)` が残る。これは次回 checkpoint までの正常な状態であり、`git submodule update` で巻き戻したり gitlink を stage して「直さない」。

## 手順

### 1. 何も消す前に状態を把握する

```bash
git status && git worktree list --porcelain && git branch -vv && git remote -v
gh pr list --state open --json number,title,headRefName,headRefOid
gh pr list --state all --limit 20 --json number,title,state,headRefName,mergedAt
```

Open PR が残っていれば、次は **整理対象外**である。残存 PR をユーザに報告し、それ以外だけを進める。

- `headRefName` の branch
- その branch をチェックアウトしている worktree
- `git worktree list --porcelain` の `HEAD` がオープン PR の `headRefOid` と一致する worktree（detached でも対象外）
- パスが `/tmp/pr-review-*` の worktree と親ディレクトリ。親の `session.json` の `head_branch` がオープン PR の `headRefName` である場合も含む

### 2. リモートを取り込む

```bash
git fetch --all --prune
```

**マージ判定の前に必ず実行する。** ローカルの `origin/main` は古いのが普通で、fetch 前の「マージ済みか」の判定は誤る。

### 3. マージ済みか判定する

```bash
git log --oneline origin/main..<branch>
```

出力が空 = `origin/main` に取り込み済み。`gh pr list --state all` の `state: MERGED` と突き合わせる。空でなければ削除しない。

### 4. worktree ごとに clean を確認する

```bash
git -C <worktree の絶対パス> status --short
```

`-C` には絶対パスを渡す（worktree 隔離セッションでは相対パスが拒否されることがある）。出力があれば **その worktree は消さない**。ユーザに報告して判断を仰ぐ。

#### 毎回ここで止まるなら、直すのは片付け側ではなく生成側である

untracked ファイルは正本と照合する述語を持たないため、ゲート A の対象として必ず人間の判断を要求する。同じ種類のファイルで毎回止まるのは、**worktree 内に判定不能な生成物を残す手順が上流にある**ということである。ゲートを緩めて解決してはならない。

報告時は「どのスキル・どの手順の生成物か」を添えて指摘し、生成側を次の原則へ合わせるよう促す。

**生成物は worktree の外（scratchpad / `mktemp -d`）に出す。** untracked が発生しないので手順 4 で止まらない。本スキルは worktree 直下の untracked を機械的に照合する述語を持たない（手順 6 のゲート A は `session.json` を持つ残骸ディレクトリ専用である）ため、worktree 内に残す限り毎回ユーザ確認になる。

`.gitignore` へ追加して黙らせてはならない。gitignore 対象は本スキルの「やらないこと」で削除禁止であり、`git status` からも消えるため、判定不能なまま永久に残る。

### 5. worktree を削除する

手順 1 で対象外にした worktree（オープン PR の `headRefOid` と HEAD が一致するもの、`/tmp/pr-review-*` で親 `session.json` の `head_branch` がオープン PR と一致するもの）は消さない。

サブモジュール（本リポジトリの `public`）を含む worktree は `git worktree remove` が次で失敗する。

```
fatal: working trees containing submodules cannot be moved or removed
```

手順 4 で clean を確認済みの worktree に限り `--force` を付けてよい。確認していない worktree に `--force` を付けない。

```bash
git worktree remove --force <path>
git worktree prune
```

worktree 本体の削除と、手順 6 の残骸削除は **別の判断**である。worktree 本体は追跡済みの内容であり、マージ済み・clean を確認していれば削除してよい。手順 6 で保留が発生しても、worktree 本体の削除まで止める必要はない。

### 6. ゲート A — 残骸ディレクトリは照合してから消す

`git worktree remove` は作業ツリーだけを消す。親ディレクトリに残る `session.json` や `review-backup/` は **git 管理外**であり、`git status` にも `git worktree list` にも現れない。

正本パスは残骸の `session.json` の `destination` から取る。ブランチ名の変換で推測しない。

```bash
python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["destination"])' <残骸>/session.json
```

`session.json` が無い、`destination` が読めない、またはその親がリポジトリの `reviews/` 配下に無い場合は削除せず停止する。

```bash
diff -rq <残骸>/review-backup <正本ディレクトリ> > /tmp/gate-a.out 2> /tmp/gate-a.err; echo $?
```

削除してよいのは、次をすべて満たすときだけである。空の `grep '^Only in .*review-backup'` だけを削除許可にしてはならない。

- `diff` の stderr が空（正本ディレクトリ不在は終了コード 2 でここに出る）
- stdout に `Files ... differ` が無い
- stdout の `Only in ...review-backup` が `previous-review.md` 以外に無い。`previous-review.md` はセッション snapshot なので正本へコピーせず、この判定からも除外する

どれか一つでも欠ければ削除しない。

- `Only in ...review-backup` の対象が `<model>.md` なら正本へ `cp` する。コピーは非破壊なので AskUserQuestion は不要。コピー後に述語を再実行する
- `previous-review.md` は正本へコピーしない
- `Files ... differ` の `<model>.md` は正本を上書きしない。残すか別名退避するかをユーザに確認し、確認が終わるまで残骸は消さない

```bash
cp <残骸>/review-backup/<model>.md <正本ディレクトリ>/
```

`reviews/` は `.gitignore` 対象なので、git は一切守ってくれない。

### 7. 作業ツリーを `origin/main` へ更新する

メイン作業ツリーの `git status --short` が空であることを確認する。空でなければ checkout もブランチ削除もせず、ユーザへ報告する。

```bash
git checkout --detach origin/main
git submodule update --init public
```

ローカル `main` ブランチは作らない（プロジェクト規約）。

### 8. マージ済みローカルブランチを削除する

手順 7 の detach のあとで実行する。メイン作業ツリーが feature を checkout したままだと `git branch -d` は `used by worktree` / `checked out` で失敗する。

```bash
git branch -d <branch>
```

`-D` は使わない。

`-d` が拒否した場合、理由で分岐する。拒否を未マージと同一視しない。

- `used by worktree` または `checked out`: 未マージではない。手順 7 の detach が済んでいなければ手順 7 に戻る。他 worktree が掴んでいるならその worktree を残し、このブランチは削除しない
- `not fully merged`: 未マージである。手順 3 の判定が誤っている。削除しない

detached HEAD では次の warning が出るが、**削除が成功していれば正常**である。upstream にマージ済みであることは確認できており、拒否ではない。

```
warning: deleting branch '<branch>' that has been merged to
         'refs/remotes/origin/<branch>', but not yet merged to HEAD
```

### 9. ゲート B — リモートブランチ削除はユーザに確認する

手順 8 でローカルブランチを消すと対象名が手元から消える。リモート側から独立に洗い出す。

```bash
git branch -r --merged origin/main | grep -vE 'origin/(HEAD|main)$'
```

候補が複数ある場合は、手順 1 で取得した `gh pr list --state all` の `headRefName` と突き合わせ、**どの PR 由来か**を添えて提示する。対応する PR が見つからないリモートブランチは候補から外し、そのまま残す。

マージ済みでも、リモートブランチの削除を勝手に実行しない。`AskUserQuestion` で確認し、承認を得てから実行する。

```bash
git push origin --delete <branch>
git fetch --prune
```

### 10. 最終状態を報告する

`git status` / `git worktree list` / `git branch -a` の出力と、削除した対象を報告する。

## Red Flags — 手を止めて手順に戻れ

- 「Merge 済みなので役目は終えている」を根拠に git 管理外ファイルを消そうとしている
- 「ディレクトリ名が `stale` / `tmp` / `pr-review-*` だから」を削除の根拠にしている
- 中身を正本と照合せずに「軽微なメモ」「レビューのメタデータ」と分類している
- `rm -rf` を打とうとしているが、直前に `diff` / `cmp` を実行していない
- `Files ... differ` や `diff` の失敗を無視して「固有ファイルが無いから消してよい」としている
- リモートブランチを削除してから「不要なら戻せます」と報告しようとしている
- 「時間が無い」「手早く」と言われたので確認を飛ばそうとしている

**いずれかに該当したら、削除をやめて手順 6 または 9 に戻る。**

## 言い訳と現実

| 言い訳 | 現実 |
|---|---|
| 「PR は Merge 済みだから、レビュー成果物の役目も終わった」 | マージされたのは追跡対象のコードだけである。git 管理外のレビュー結果は 1 バイトもマージされていない |
| 「ディレクトリ名が stale なので消してよい」 | 名前は中身を保証しない。照合していないなら未保存データの有無を知らないだけである |
| 「中を見たら軽微なメモだった」 | 軽微だと判断したのではなく、正本と照合していないだけである。照合は `diff -r` 1 回で済む |
| 「内容差分があっても固有ファイルが無ければ失うものはない」 | 同名の未保存稿は `Files ... differ` になる。`previous-review.md` だけをコピーして消すと新しい原稿が消える |
| 「worktree は clean だったのでデータ損失はない」 | `git status` は gitignore 対象ファイルも、worktree の外にある残骸も見ない |
| 「消した後で問題があれば言ってもらえばいい」 | `rm -rf` に取り消しは無い。削除の前だけが確認である |
| 「マージ済みブランチの削除は cleanup の一環」 | ローカルはそうである。リモートは他人が見る共有物であり、外向きの操作である |
| 「手早くと言われた」 | 照合は数秒で終わる。失ったレビューの再生成はそれより桁違いに高い |
| 「untracked が出るのは仕方ない。毎回訊けばよい」 | 訊かれるのは、判定不能な生成物を作り続けている上流の手順があるからである。生成側を直せば訊く必要そのものが無くなる |
| 「毎回同じ確認で面倒なので `.gitignore` に入れる」 | `git status` から消えるだけで、復元不能なファイルであることは変わらない。gitignore 対象は本スキルで削除禁止であり、判定不能なまま残り続ける |

## やらないこと

- ローカル `main` ブランチの作成
- `git branch -D` によるマージ判定の握り潰し
- clean を確認していない worktree への `--force`
- ユーザ確認なしの `git push`（`--delete` を含む）
- Open PR が残っている branch / worktree の削除（detached な pr-review worktree を含む）
- `reviews/` や `docs_draft/` など gitignore 対象ディレクトリの内容の削除

## 関連スキル

- `pr-review` — `/tmp/pr-review-*/` の使い捨て worktree と `review-backup/` を作る側。手順 6 の残骸はこのスキルの生成物である
- `version-export` — リリース手順。一時生成物を worktree の外（scratchpad）へ出す原則を共有する
