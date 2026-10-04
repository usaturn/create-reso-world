---
name: stale-git-lock-recovery
description: "Use when git の操作が fatal: Unable to create '.../index.lock': File exists. Another git process seems to be running in this repository, or the lock file may be stale で失敗する場合。残留した stale な index.lock（.git/index.lock、.git/worktrees/*/index.lock）が疑われ、git switch / git checkout / git merge / git add / git commit がブロックされ、git status だけは exit 0 で成功する状況が対象。live holder がいるロック、holder の有無を判定できないロック、open PR が使っている /tmp/pr-review-* worktree のロック、常設の .git/pr-review-save.lock には使用しない。"
---

# stale な git index.lock の復旧

## 概要

`index.lock` を取得できずに git の操作が止まったとき、live holder の不在を確認してからロックを外し、止められていた操作を再開する。

**中核原則: live holder がいないと確認できるまでロックを外さない。除去したら、ロックを取得できなかった元の操作を再実行する。force しない。**

- `git status` はロックがあっても exit 0 で成功する。status が通ることを「ロックは無い」の根拠にしない。
- ロックファイルのサイズは判定基準にしない。0 バイトは典型例にすぎない。判定は mtime と保持プロセスの不在で行う。
- `.git/pr-review-save.lock` は `pr-review` が `flock` で保持する常設のロックである。stale な `index.lock` ではない。

## When to Use

- `fatal: Unable to create '.../index.lock': File exists. Another git process seems to be running in this repository, or the lock file may be stale` で `git switch` / `git checkout` / `git merge` / `git add` / `git commit` が失敗した
- そのエラーが出るのに `git status` は exit 0 で成功する
- 中断した並列処理の後に `index.lock` が残っている（linked worktree の `.git/worktrees/<name>/index.lock` を含む）

## When NOT to Use

- live holder が見つかった: そのプロセスの完了を待つ。待てない場合は状況を報告して停止する
- holder の有無を判定できない（`lsof` も `/proc` も使えない）: 削除せず、人間に確認する
- `/tmp/pr-review-*` の review worktree のロック: そのレビューセッションが進行中かもしれない。該当セッションと調整するまで触らない
- `.git/pr-review-save.lock`: 常設の flock であり、削除しない

## Quick reference

| 症状 | 対応 |
| --- | --- |
| `Unable to create ... index.lock: File exists` | 下記「検出」で保持者を確認する。いなければ「除去」に進む |
| `Another git process seems to be running` | 保持者がいれば待つ。いなければ stale として除去してよい |
| `git status` だけ成功する | status の成功をロック不在の根拠にしない。`git rev-parse --git-path index.lock` で存在を確かめる |
| linked worktree のロック | `git -C <worktree> rev-parse --git-path index.lock` で解決する。`.git/index.lock` を決め打ちしない |
| ff マージが未追跡ファイルと衝突する | `cp -p` と `sha256sum` で退避してから merge し、復元して `sha256sum -c` で検証する |
| `.git/pr-review-save.lock` | 削除対象ではない。常設 flock である |

## 検出（ロックの特定と保持者の確認）

第一手段は同梱スクリプトである。`check` は exit code で状態を返す。

```bash
bash .agents/skills/stale-git-lock-recovery/scripts/stale_git_lock.sh check --repo <repo>
# 0 = ロックなし / 10 = live holder あり / 11 = holder なし (stale) / 12 = 判定不能
```

`--json` を付けると機械可読な 1 オブジェクトを stdout に出す。

手動で確かめる場合は次の順で行う。

```bash
lock="$(git -C <repo> rev-parse --git-path index.lock)"
stat -- "$lock"                    # 存在と mtime を見る（サイズは判定基準にしない）
lsof -- "$lock"                    # 何か出力されれば保持者あり
for fd in /proc/[0-9]*/fd/*; do readlink "$fd" 2>/dev/null; done | grep -F -- "$lock"
```

- 保持者が 1 つでも見つかれば、それは live holder である。削除しない
- `lsof` が無い場合は `/proc` の走査を使う。両方使えないときは「保持者なし」ではなく「判定不能」として削除しない
- スクリプトは自身の fd と `lsof` 自身の行を保持者と誤認しないよう除外する

## 除去

保持者の不在を確認できたときだけ、次を実行する。

```bash
bash .agents/skills/stale-git-lock-recovery/scripts/stale_git_lock.sh clear --repo <repo>
```

`clear` は exit 11（stale）のときだけ削除し、削除後の不在を確認する。exit 10 / 12 では何も削除しない。手動で行う場合も保持者不在の確認後だけにする。

```bash
rm -f -- "$(git -C <repo> rev-parse --git-path index.lock)"
```

除去したら、ロックを取得できなかった元の操作を再実行する（例: `git switch main`、`git merge --ff-only origin/main`、`git add`、`git commit`）。「復旧した」と報告するのは、この再実行が成功してからにする。

## ロック解除後の復旧（ff マージが未追跡ファイルと衝突する場合）

`git merge --ff-only origin/main` が `untracked working tree files would be overwritten` で失敗することがある。これはロックとは別の問題であり、次の無損失手順で解決する。`git clean` や `git reset --hard`、`git checkout -f` は使わない（未保存の作業を消すため）。

まず衝突候補を列挙する。`git status --porcelain` の `??`（未追跡）のうち、マージ先に同じ path が存在するものだけが衝突する。

```bash
git status --porcelain --untracked-files=all | sed -n 's/^?? //p' | while IFS= read -r path; do
  git cat-file -e "origin/main:$path" 2>/dev/null && printf '%s\n' "$path"
done
```

候補ごとに退避 → マージ → 復元 → 検証を行う。`cp -p` でパーミッションを保ち、`sha256sum` の控えでバイト一致を確認する。

```bash
path=<衝突ファイル>                     # リポジトリ root からの相対パス
backup="$(mktemp -d)" && mkdir -p "$backup/$(dirname "$path")"
cp -p "$path" "$backup/$path"
sha256sum "$path" > "$backup/$path.sha256"
rm -- "$path"
git merge --ff-only origin/main
cp -p "$backup/$path" "$path"
sha256sum -c "$backup/$path.sha256"
```

復元後、`origin/main` と同一だったファイルは追跡化されて clean になり、差分のある下書きは ` M` として残る。これは想定どおりであり、内容は失われていない。退避先は検証が終わるまで消さない。

## Red Flags: 手を止めて検出に戻る

- 保持者を確認せずに `rm` しようとしている
- 0 バイトだったことだけを根拠に stale と断定している
- `git clean` / `git reset --hard` / `git checkout -f` で回避しようとしている。使わない（未保存の作業を消す）
- open PR の review worktree（`/tmp/pr-review-*`）のロックに触ろうとしている
- 除去しただけで元の git 操作を再実行せず、「復旧した」と報告しようとしている
- `git status` が成功したので影響なしと判断している
- `.git/pr-review-save.lock` を stale な `index.lock` と混同している

**いずれかに該当したら、削除を中止して「検出」の手順に戻る。判定不能なら停止して人間に確認する。**

## ガードレール

- live holder のいるロックを削除しない。判定できない場合も削除しない
- `--force` 相当の操作をしない（`clear` にも `--force` は無い）
- `git clean` / `git reset --hard` / `git checkout -f` を使わない
- open PR の review worktree と `.git/pr-review-save.lock` を対象にしない
- untracked 衝突の退避では、内容の照合（`sha256sum -c`）が終わるまで退避先を消さない

## 関連スキル

- `repo-cleanup-after-merge` — 手順 7 の `git switch main` / `git merge --ff-only origin/main` は stale な `index.lock` で失敗しうる。失敗した場合は本スキルで復旧してから手順 7 に戻る
- `pr-review` — `/tmp/pr-review-*` worktree と `.git/pr-review-save.lock` を作る側。進行中セッションのロックは本スキルの対象外である
