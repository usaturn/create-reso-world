---
name: stale-git-lock-recovery
description: "Use when git の操作が fatal: Unable to create '.../index.lock': File exists. Another git process seems to be running in this repository, or the lock file may be stale で失敗する場合。残留した stale な index.lock（.git/index.lock、.git/worktrees/*/index.lock）が疑われ、git switch / git checkout / git merge / git add / git commit がブロックされ、git status だけは exit 0 で成功する状況が対象。live holder がいるロック、holder の有無を判定できないロック、open PR が使っている /tmp/pr-review-* worktree のロック、常設の .git/pr-review-save.lock には使用しない。"
---

# stale な git index.lock の復旧

## 概要

`index.lock` を取得できずに git の操作が止まったとき、live holder の不在を確認してからロックを外し、止められていた操作を再開する。

**中核原則: live holder がいないと確認できるまでロックを外さない。除去したら、ロックを取得できなかった元の操作を再実行する。force しない。**

- ロックの保持者は、ロックの fd を開いているプロセスだけではない。git は `git commit -a` などで、新しい index を `index.lock` に書いて fd を閉じたまま、pre-commit hook やコミットメッセージのエディタを実行する。この間に消すと、hook の実行中なら git は消えたロックを空の index として読み直し、追跡ファイルをすべて削除するコミット（空の tree）が現在の branch に入る。エディタの待機中ならコミットはできるが、index の更新に失敗して古いまま残る。fd が見つからないことだけを stale の根拠にしない。
- `git status` はロックがあっても exit 0 で成功する。status が通ることを「ロックは無い」の根拠にしない。
- サイズと mtime は判定基準にしない。判定は保持者の不在で行い、0 バイトかどうかや mtime は参考情報にすぎない。
- `.git/pr-review-save.lock` は、`pr-review` が操作のたびに `flock` を掛けるために常に置いてあるファイルである。stale な `index.lock` ではない。削除すると、次の操作が別のファイルに flock を掛けることになり、排他が効かなくなる。
- 他ユーザーのプロセス、PID namespace の外（ホスト側・別コンテナ）の保持者は検出できない。git 以外の実装（JGit や libgit2 を使うツール）が fd を閉じたまま持つロックも検出できない。bind mount でロックを共有している場合や、そうしたツールが同じリポジトリを操作している可能性がある場合は、検出結果だけで削除せず、人間の確認を必須とする。

## When to Use

- `fatal: Unable to create '.../index.lock': File exists. Another git process seems to be running in this repository, or the lock file may be stale` で `git switch` / `git checkout` / `git merge` / `git add` / `git commit` が失敗した
- そのエラーが出るのに `git status` は exit 0 で成功する
- 中断した並列処理の後に `index.lock` が残っている（linked worktree の `.git/worktrees/<name>/index.lock` を含む）

## When NOT to Use

- live holder が見つかった: そのプロセスの完了を待つ。待てない場合は状況を報告して停止する
- holder の有無を判定できない（`/proc` が使えない、他ユーザー・PID namespace 外・bind mount 共有・git 以外の実装の可能性がある）: 削除せず、人間の確認を必須とする
- `pr-review` の review worktree（`/tmp/pr-review-*`）のロック: そのレビューセッションが進行中かもしれない。該当セッションと調整するまで触らない。ロックの実体は `/tmp` ではなくメインリポジトリの `.git/worktrees/<name>/index.lock` にあり、`.git/worktrees/<name>/gitdir` の中身が `/tmp/pr-review-*` を指していれば review worktree のロックである
- `.git/pr-review-save.lock`: `pr-review` が flock に使う常設のファイルであり、削除しない

## Quick reference

| 症状 | 対応 |
| --- | --- |
| `Unable to create ... index.lock: File exists` | 下記「検出」の `check` で保持者を確認する。exit 11 のときだけ「除去」に進む |
| `Another git process seems to be running` | 保持者がいれば待つ。fd を開いているプロセスも、同じワークツリーで動作中の git プロセスもいないときだけ stale として扱う |
| `check` が exit 12 で git プロセスを表示した | fd を閉じたままロックを持っている可能性がある。そのプロセスが終わるのを待ってから `check` をやり直す |
| `git status` だけ成功する | status の成功をロック不在の根拠にしない。`git rev-parse --path-format=absolute --git-path index.lock` で存在を確かめる |
| linked worktree のロック | `--repo` にはその worktree のパスを渡す。`.git/worktrees/<name>` は渡せない（worktree のパスは `.git/worktrees/<name>/gitdir` の中身から末尾の `/.git` を除いたもの）。手で確かめるときは `git -C <worktree> rev-parse --path-format=absolute --git-path index.lock` で解決し、`.git/index.lock` を決め打ちしない |
| fd を列挙できない git プロセスがいる | 保持者の可能性を否定できない。判定不能として削除しない |
| `index.lock` が symlink | `clear` は link 自体を消す。参照先は消さない |
| ff マージが未追跡ファイルと衝突する | 同梱の `ff_merge_keep_untracked.sh` で、未追跡ファイルを退避・復元しながら ff マージする |
| `.git/pr-review-save.lock` | 削除対象ではない。`pr-review` の flock 用の常設ファイルである |

## 検出（ロックの特定と保持者の確認）

同梱スクリプトの `check` で判定する。exit code で状態を返す。

```bash
bash .agents/skills/stale-git-lock-recovery/scripts/stale_git_lock.sh check --repo <repo>
# 0 = ロックなし / 10 = live holder あり / 11 = holder なし (stale) / 12 = 判定不能
```

`<repo>` はワークツリーのパス（その中のサブディレクトリでもよい）である。`.git` やその中のパス（`.git/worktrees/<name>`、サブモジュールの `.git/modules/<name>` を含む）を渡すと exit 2 で何もしない。対象のワークツリーの top が分からないと、そこで動作中の git プロセスを見落とすためである。

`--json` を付けると stdout に機械可読な 1 オブジェクト（キーは `path` / `exists` / `removed` / `size` / `mtime` / `holder` / `stale`）だけを出す。`removed` は clear が実際に削除したかを示す。usage エラー（exit 2）、削除の失敗や `clear` の直列化に使う `flock` を取得できない場合（exit 1）は stderr のみに出て JSON は出力しない。

スクリプトは次の順で判定する。

- ロックのパスは `git rev-parse --git-path index.lock` で解決する。linked worktree では `.git/worktrees/<name>/index.lock` になる。呼び出し元から引き継いだ `GIT_DIR` / `GIT_WORK_TREE` などは無視し、`--repo` だけで対象のリポジトリを決める
- ロックの fd を開いているプロセスを `lsof` と `/proc/*/fd`（inode の比較）で探す。1 つでも見つかれば live holder（exit 10）
- fd を列挙できない git プロセスがいれば判定不能（exit 12）とし、保持者不在とみなさない。git プロセスかどうかは、実行ファイル名・argv[0]・実行ファイルそのもので判定する（別名の symlink から起動した git も含む）。終了して回収待ちの zombie は何も保持していないので除く
- fd を開いている保持者がいなくても、同じワークツリーで動作中の git プロセスがいれば判定不能（exit 12）とする。fd を閉じたままロックを持っている可能性を否定できないためである。git はワークツリーの top で動くので、cwd がワークツリーの top と同じプロセスと、cwd から git が解決する `index.lock` が対象と同じプロセスを該当とする（`core.worktree` で git dir と離れたワークツリーも含む）。入れ子の worktree（`.worktrees/<name>` など）やサブモジュールで動く git は、別の index を使うので対象外になる
- ワークツリーの外の cwd から、環境変数 `GIT_DIR` / `GIT_COMMON_DIR` / `GIT_INDEX_FILE` やオプション `--git-dir` でこのワークツリーの git dir や index を指している git プロセスも判定不能とする。git が使う index は git dir と `GIT_INDEX_FILE` で決まるので、指す先は対象の git dir・ロックのディレクトリと同一かで比べる。git dir を共有する linked worktree の git は含まない。git dir が絶対パスで分かっていれば、`GIT_WORK_TREE` / `--work-tree` の指定は判定に使わない。`.git` ファイル（linked worktree やサブモジュール）を指す値は、その中の git dir に解決して比べる。`GIT_DIR` などの値が相対パスのとき（git は起動時の cwd を基準にするので、cwd が変わった後では解決できない。ただし hook に渡る相対パスの `GIT_INDEX_FILE` は、git が動いている cwd を基準に解決して比べる）、ワークツリーだけを指定して git dir を指定していないとき（git dir は起動時の cwd から決まっていて、後から分からない）、cwd・環境変数・コマンドラインを読めないときも、除外できないので判定不能とする（走査中に終了したプロセスは何も保持していないので除く）
- `/proc` が使えない環境では、git プロセスを確認できないため判定不能（exit 12）とする
- 保持者または判定不能の原因になったプロセスは、PID とコマンド名を stderr に出す

exit 12 で git プロセスが表示されたら、そのプロセスが何をしているかを確かめ、終わるのを待ってから `check` をやり直す。別のターミナルで開いたままのコミットメッセージのエディタや、時間のかかる hook が典型である。

```bash
ps -o pid,etime,args -p <pid>   # 何をしているプロセスか、いつから動いているか
readlink /proc/<pid>/cwd        # どのディレクトリで動いているか
```

他ユーザーのプロセス、PID namespace の外（ホスト側・別コンテナ）の保持者や、git 以外の実装（JGit や libgit2 を使うツール）が fd を閉じたまま持つロックは検出できない。bind mount で共有している構成や、そうしたツールが同じリポジトリを操作している可能性がある場合は、exit 11 だったことだけを根拠にせず、人間の確認を必須とする。

## 除去

`check` が exit 11（stale）を返したときだけ、次を実行する。

```bash
bash .agents/skills/stale-git-lock-recovery/scripts/stale_git_lock.sh clear --repo <repo>
```

`clear` は保持者の判定をやり直し、exit 11 のときだけ削除して、削除後の不在を確認する。exit 10 / 12 では何も削除しない。`index.lock` が symlink の場合は link 自体を消し、参照先は消さない。

- 同じロックに対する `clear` の同時実行は `flock` で 1 つずつ順に処理する。`flock` が使えない環境では削除しない
- 判定に使ったロックのファイルが判定中に差し替わっていたら（新しい git プロセスが作ったかもしれない）、削除せず exit 12 を返す

削除は `clear` だけで行う。`rm` で手動削除しない。手動の削除には、fd を閉じたまま動作中の git プロセスの確認も、同時実行の直列化も無い。スクリプトを実行できない環境では削除せず、人間に確認する。

除去したら、ロックを取得できなかった元の操作を再実行する（例: `git switch main`、`git merge --ff-only origin/main`、`git add`、`git commit`）。「復旧した」と報告するのは、この再実行が成功してからにする。

## ロック解除後の復旧（ff マージが未追跡ファイルと衝突する場合）

再実行した `git merge --ff-only <ref>` が `untracked working tree files would be overwritten` で失敗することがある。これはロックとは別の問題であり、同梱の `ff_merge_keep_untracked.sh` で内容を失わずに解決する。`git clean` や `git reset --hard`、`git checkout -f` は使わない（未保存の作業を消すため）。

```bash
bash .agents/skills/stale-git-lock-recovery/scripts/ff_merge_keep_untracked.sh --repo <repo> --ref origin/main
```

スクリプトは次の順で処理する。どのディレクトリから実行してもよく、対象のリポジトリは `--repo` だけで決まる。

1. `<ref>` が ff で取り込めることを確かめる。取り込み済みなら何もせず exit 0、ff で取り込めなければ何も変えずに exit 1。HEAD にまだコミットが無い branch は対象外で、何も変えずに exit 1
2. `<ref>` が追加するパスと同じパスにある未追跡ファイルをすべて列挙する。ignore 対象のファイルも含める（git merge は ignore 対象のファイルを確認なしに上書きするため）。symlink のディレクトリの先はたどらない。列挙に失敗したら、何も変えずに exit 1
3. 次の場合は、何も変えずに exit 1 で該当パスを表示する。git はこれらも確認なしに消したり上書きしたりし、ff の後には元の場所へ戻せないためである。表示されたパスをワークツリーの外へ移してから再実行する
   - `<ref>` がファイルを置くパスに、未追跡・ignore 対象のファイルを含むディレクトリがある
   - `<ref>` が submodule を追加するパスに、ディレクトリ以外（ファイルや symlink）がある
   - `<ref>` がディレクトリを置くパスに、index に無いファイルや symlink がある（追跡ディレクトリの位置に置かれた ignore 対象のファイルを含む）
   - `<ref>` がファイルを追加する先が、index に submodule として無い入れ子のリポジトリ（`.git` を持つディレクトリ）の中にある
   - `<ref>` が submodule を普通のディレクトリに置き換え、追加するパスやその途中に、submodule の checkout 内のファイルや symlink がある（git は checkout を残したまま中へ書き込む）
   - `<ref>` が submodule をファイルや symlink に置き換え、その checkout に中身がある（git は checkout をまるごと消す）
4. 全件を一時ディレクトリへ `cp -a` で退避し（symlink は symlink のまま、パーミッションとタイムスタンプも保つ）、退避したコピーが元と一致することを確かめる。退避先は削除前に stderr へ表示する
5. 全件を削除してから、`git merge --ff-only` を 1 回だけ実行する
6. merge の成否にかかわらず全件を元のパスへ戻し、元と一致することを確かめる。merge が失敗した場合は HEAD を変えずに exit 1
7. HUP / INT / TERM で中断されたときも全件を戻し、HEAD が進んだかどうかを stderr に出して exit 1 で終わる

復元後、`<ref>` と同一だったファイルは追跡ファイルとして clean になり、差分のある下書きは ` M` として残る。これは想定どおりであり、内容は失われていない。退避先はスクリプトが消さない。結果を確認してから消す。

`repo-cleanup-after-merge` の手順 7 の中では使わない。手順 7 は `git status --short` が空でなければ停止してユーザーへ報告する規則であり、未追跡ファイルがある状態では ff マージに進まない。

## Red Flags: 手を止めて検出に戻る

- 保持者を確認せずに `rm` しようとしている。`clear` を使わず手動で削除しようとしている
- ロックの fd を開いているプロセスがいないことだけを根拠に stale と断定している
- 0 バイトだったことだけを根拠に stale と断定している
- `git clean` / `git reset --hard` / `git checkout -f` で回避しようとしている。使わない（未保存の作業を消す）
- open PR の review worktree（`/tmp/pr-review-*`）のロックに触ろうとしている
- fd を列挙できない PID や、exit 12 で表示された git プロセスを「保持者なし」と解釈している
- 他ユーザーや PID namespace の外の保持者まで確認したつもりになっている
- 除去しただけで元の git 操作を再実行せず、「復旧した」と報告しようとしている
- `git status` が成功したので影響なしと判断している
- `.git/pr-review-save.lock` を stale な `index.lock` と混同している

**いずれかに該当したら、削除を中止して「検出」の手順に戻る。判定不能なら停止して人間に確認する。**

## ガードレール

- live holder のいるロックを削除しない。判定できない場合も削除しない
- 削除は `clear` だけで行う。`--force` 相当の操作をしない（`clear` にも `--force` は無い）
- `git clean` / `git reset --hard` / `git checkout -f` を使わない
- open PR の review worktree と `.git/pr-review-save.lock` を対象にしない
- 他ユーザー・PID namespace 外・bind mount 共有・git 以外の実装の保持者は検出できない前提で、人間の確認を必須とする
- 未追跡ファイルとの衝突は `ff_merge_keep_untracked.sh` で解決し、結果を確認するまで退避先を消さない

## 関連スキル

- `repo-cleanup-after-merge` — 手順 7 の `git switch main` / `git merge --ff-only origin/main` は stale な `index.lock` で失敗しうる。失敗した場合は本スキルの「検出」「除去」で復旧してから手順 7 に戻る
- `pr-review` — `/tmp/pr-review-*` worktree と `.git/pr-review-save.lock` を作る側。進行中セッションのロックは本スキルの対象外である
