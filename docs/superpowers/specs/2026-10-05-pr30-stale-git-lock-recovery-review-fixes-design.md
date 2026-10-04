# PR #30 stale-git-lock-recovery のレビュー指摘の選別と修正設計

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/30
- リポジトリ: `usaturn/create-reso-world`
- 対象ブランチ: `feat/stale-git-lock-recovery`
- 指摘を検証した HEAD: `d096aafd207535e7bba06458d81cc214ad3c324e`
- 入力: `reviews/#30-feat-stale-git-lock-recovery/` 配下の全 3 ファイル
- 作成日: 2026-10-05
- 経路: **bounded**（PR が追加する 1 スキルに閉じた、既存フローへのレビュー修正）
- 状態: **approved**。2026-10-05 のユーザ依頼で「修正が必要なら推奨案を基本に修正し、検証・PR 全体の再レビューを完了してプッシュする」「同じ原因の関連箇所は PR 差分外も修正する」「後続のレビュー・修正で手戻りを発生させない」ことが事前に指示されている。下記「推奨案からの変更点」もこの指示の範囲として記録する

## 結論

修正が必要である。High の H-1（live な `git commit -a` が fd を閉じたまま保持している `index.lock` を stale と判定し、`clear` が削除して追跡ファイルを全削除するコミットが作られる）を現行 HEAD で再現した。これはスキルの中核の保証（live holder のロックを外さない）を壊す。

## レビュー入力

| ファイル | 対象 HEAD | 指摘 |
| --- | --- | --- |
| `claude-opus-5-5.md` | `d096aafd2075` | High 1、Low 2 |
| `SWE-2-Max.md` | `d096aafd2075` | Medium 1、Low 2、Info 1 |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `d096aafd2075` | Medium 1、Low 1 |

対象 HEAD はすべて現行 PR HEAD と一致する。PR 本文が自ら挙げた非ブロッキングの改善候補 3 件（P-1〜P-3）も、同じ関数・同じ手順を直すため一覧に含める。

## 分類結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 0 |
| 対応する | 11 |
| 判断保留 | 0 |
| 対応しない | 0 |

重複（Opus L-1 と DeepSeek L-1）は 1 件として数える。

### 全指摘一覧

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| Opus H-1 | fd を閉じてロックを保持する live な git を stale と判定し、`clear` が削除する | 対応する (a) | 一時リポジトリで再現。sleep する pre-commit hook とエディタの両方で `check` が exit 11、`clear` 後に空 tree のコミットができる |
| Opus L-1 / DeepSeek L-1 | 衝突する未追跡ファイルが 2 件以上あると、候補ごとの退避手順では ff マージが成立しない | 対応する (a) | 3 件の衝突で、候補ごとの手順の merge が毎回 exit 1、`sha256sum -c` は OK のまま HEAD が進まないことを再現 |
| Opus L-2 | スニペットの変数 `path` が zsh で `PATH` を壊し、候補 0 件・`command not found` になる | 対応する (a) | `zsh -fc` で列挙が exit 127・無出力、退避側で `mktemp` が見つからないことを再現 |
| SWE M-1 | 退避ブロックが cwd 依存（`$repo` を使わない） | 対応する (b) | SKILL.md 105〜112 行はすべて相対パスで、`repo` 以外の cwd では別の場所のファイルを消す |
| SWE L-1 | `cp -p` が symlink を dereference し、復元で通常ファイルになる | 対応する (a) | `cp -p link.md` の結果が `regular file` になることを再現 |
| SWE L-2 | `clear` の判定から `rm` までに排他が無く、並列実行で live lock を消しうる | 対応する (a) | 263〜298 行に直列化も再確認も無いことをコードで確認 |
| SWE I-1 | 提案コマンドがクォートされず、空白入りのパスで実行できない | 対応する (a) | 空白入りパスで引数過多の usage error になることを確認（数行の修正で実害が消えるため対応する） |
| DeepSeek M-1 | 継承した絶対 `GIT_DIR` が `--repo` を上書きし、別リポジトリのロックを消す | 対応する (a) | `GIT_DIR=<B>/.git ... clear --repo <A>` で B のロックが消えることを再現 |
| P-1（PR 本文） | `/proc` 走査で unlistable な git が先に見つかると、後続の明確な holder があっても exit 12（PID 順に依存） | 対応する (a) | H-1 の修正で同じ関数を書き直すため、走査を最後まで続けて present を優先する |
| P-2（PR 本文） | union 規則（lsof absent ＋ `/proc` unknown → unknown）の回帰テストが無い | 対応する (c) | H-1 の修正で union の分岐を変えるため、回帰ガードとして追加する |
| P-3（PR 本文） | SKILL.md の手動 `/proc` 例はパス文字列一致で、スクリプトの inode 比較とずれる | 対応する (b) | 手動の判定例を削除し、スクリプトの出力する PID の調べ方だけを残す（H-1 と同じ原因で手動判定は不完全なため） |

## 修正方針

### 1. ロックの保持者判定（Opus H-1、P-1、P-2）

`scripts/stale_git_lock.sh` の判定に、fd を閉じたままロックを持つ git プロセスの確認を加える。

- fd の走査（lsof・`/proc/*/fd`）で保持者が見つからなかったときに、`/proc` を走査して、同じワークツリーで動作中の git プロセスを探す
  - git プロセスの判定は `comm` か argv[0] のプログラム名が `git` / `git-*` であること。コマンドライン中の他の語では判定しない
  - git はワークツリーの top で動くので、cwd がワークツリーの top と同一（`-ef`）のプロセスと、cwd から `git rev-parse --git-path index.lock` で解決したロックのディレクトリが対象のロックのディレクトリと同一のプロセスを該当とする。cwd がワークツリーの配下なのに git が解決できない場合も該当とする。入れ子の worktree やサブモジュールの git は別の index を使うので該当しない
  - または、環境変数・オプションの絶対パスが、`GIT_DIR` / `--git-dir` / `GIT_COMMON_DIR` は対象の git dir と、`GIT_INDEX_FILE` はそのディレクトリがロックのディレクトリと同一（`-ef`）のとき該当とする。git が使う index は git dir と `GIT_INDEX_FILE` で決まるので、`GIT_WORK_TREE` / `--work-tree` は git dir が無いときだけ意味を持つ（R-18、R-32）。相対パスの値は、起動後に cwd が変わっていて解決できないため該当とみなす。ワークツリーだけを指定して git dir を指定していないプロセスも、git dir が起動時の cwd から決まっていて後から分からないため該当とみなす（R-18）
  - cwd・環境変数・コマンドラインを読めない git プロセスは除外できないため、該当とみなす
- `--repo` はワークツリーの中のパスに限る。`git rev-parse --is-inside-git-dir` が true になるパス（`.git`、`.git/worktrees/<name>`、サブモジュールの `.git/modules/<name>` など）では、対象のワークツリーの top が分からず git プロセスを見落とすため、exit 2 で何もしない
- 該当があれば `unknown`（exit 12）とし、PID・コマンド名・理由を stderr に出す。JSON のキーと exit code の意味は変えない
- `/proc` が使えない環境では git プロセスを確認できないため、lsof が absent でも `unknown` にする
- `/proc` の fd 走査は最後まで続け、present を unknown より優先する（P-1）
- SKILL.md の中核原則・Quick reference・検出の説明に「fd を開いていなくても、動作中の git プロセスはロックを保持しうる」ことを書く

検証: 一時リポジトリで、待機する pre-commit hook と、待機するエディタの `git commit -a` を実行し、その間の `check` / `clear` が exit 12 で削除しないこと、コミット完了後の HEAD の tree に既存ファイルが残ることを確かめるテスト。偽の `PROC_ROOT` で、cwd・環境変数・オプション・cwd 読み取り不可・無関係なプロセス・linked worktree の区別・PID 順・union 規則を固定するテスト。

### 2. 対象リポジトリの決定（DeepSeek M-1）

両スクリプトの冒頭で `git rev-parse --local-env-vars` が返す変数（`GIT_DIR`、`GIT_WORK_TREE`、`GIT_COMMON_DIR`、`GIT_INDEX_FILE` など）を unset する。git 自身が hook やサブモジュールで外側のリポジトリの文脈を外すときと同じ方法であり、`--repo` だけで対象が決まる。

検証: 別リポジトリを指す `GIT_DIR`、`GIT_DIR` ＋ `GIT_WORK_TREE`、`GIT_COMMON_DIR` を設定した状態で `check` / `clear` が `--repo` のロックだけを扱い、別リポジトリのロックを残すテスト。

### 3. `clear` の直列化（SWE L-2）

- `clear` は判定の前に、ロックのあるディレクトリ自体へ `flock -x -w 30` を掛ける。追加のファイルは作らない。`flock` が無い、または取得できない場合は削除せず exit 1（stderr のみ、JSON なし）
- 判定の前後でロックファイル自体の識別子（`stat -c '%d:%i:%z'`。inode 番号が再利用されても変更時刻のナノ秒で区別できる）を比べ、差し替わっていたら削除せず exit 12
- SKILL.md から手動の `rm` 手順を削除し、削除は `clear` だけで行うと明記する。手動の削除には H-1 の確認も直列化も無いためである

検証: テストからロックのディレクトリへ flock を掛けた間は `clear` が待ち、解放後に削除すること（偽の `PROC_ROOT` と `lsof` で判定を即座に終わらせ、flock を無効にすると失敗することを確認済み）。`--repo` に `.git` の中のパスを渡すと `check` / `clear` が exit 2 でロックを残すこと。`flock` が無い PATH では削除しないこと。判定中にロックを差し替える偽の `lsof` で、`clear` が exit 12 で差し替え後のロックを残すこと。

### 4. 提案コマンドのクォート（SWE I-1）

`printf 'remove it with: bash %q clear --repo %q\n'` にする。

検証: 空白入りのパスで、提案行をそのまま bash で実行してロックが消えるテスト。

### 5. ff マージの未追跡衝突の退避手順（Opus L-1・L-2、DeepSeek L-1、SWE M-1・L-1）

SKILL.md のスニペットを、テスト可能な同梱スクリプト `scripts/ff_merge_keep_untracked.sh --ref <rev> [--repo <path>]` に置き換える。

1. `<rev>` が ff で取り込めることを先に確かめる。取り込めなければ何も変えない
2. `<rev>` が追加するパスにある未追跡ファイルを、ignore 対象も含めて全件列挙する（再レビューの R-2 で変更）
3. 全件を `mktemp -d` の退避先へ `cp -a` でコピーし、種類（symlink / 通常ファイル）・内容（`cmp`）・パーミッションが一致することを確かめてから削除する。退避先とパスの一覧（NUL 区切り）を先に stderr とファイルへ残す
4. `git merge --ff-only` を 1 回だけ実行する。ただし、`<rev>` がファイルを置くパスにある未追跡・ignore 対象のファイルを含むディレクトリや、`<rev>` がディレクトリを置くパスにある未追跡・ignore 対象のファイル・symlink、`<rev>` がファイルを追加する未追跡の入れ子リポジトリは、git が確認なしに消したり上書きしたりし、ff 後に元の場所へ戻せない。これらがあれば手順 3 の前に何も変えず exit 1 で該当パスを表示する（R-13、R-19。`<rev>` が submodule を追加するパスは除く。R-20）
5. 成否にかかわらず全件を元のパスへ戻して一致を確かめる。merge が失敗した場合は exit 1 で HEAD は変わらない。HUP / INT / TERM でも復元し、HEAD が進んだかどうかを stderr に出す。退避先は消さない

cwd に依存せず、`path` などの zsh の特殊変数を貼り付け用スニペットで使わない。SKILL.md は「`repo-cleanup-after-merge` の手順 7 の中では使わない（手順 7 は未追跡ファイルがあれば停止して報告する）」と明記し、手順 7 の停止規則と矛盾しないようにする。

検証: 通常ファイル 2 件（一方は upstream と同一）・サブディレクトリの空白入りファイル・symlink の衝突で、リポジトリ外の cwd とサブディレクトリの `--repo` から実行して、ff 後に全件が元の内容・種類・パーミッションで戻ること。merge 失敗時・ff でない場合・退避先を作れない場合に何も失わず HEAD が変わらないこと。ignore 対象のファイルを残すこと。同名のディレクトリや symlink のディレクトリの先には触れないこと。merge 中の SIGTERM で全件を戻し、HEAD が進んだことを報告すること。継承した `GIT_DIR` を無視すること。usage エラーで何も変えないこと。SKILL.md の bash スニペットが `path=` / `status=` を使わず、`rm` を含まないことを、SKILL.md の記述を検査するテストで固定する。

## 再レビュー（6e1fc4c）で見つかった指摘と対応

上記 1〜5 を実装した 6e1fc4c に対し、PR 全体の独立した再レビューと、H-1 の挙動・環境変数・TOCTOU の個別検証を行った。見つかった指摘はすべて同じ PR で対応した。

| ID | 指摘 | 対応 |
| --- | --- | --- |
| R-1（High） | `--repo` に `.git`・`.git/worktrees/<name>`・`.git/hooks` を渡すと `--show-toplevel` が失敗し、ワークツリーの top が判定対象から抜ける。待機中の `git commit -a` のロックを stale と判定し、`clear` が削除した | ワークツリーの top を必須にし、取れなければ exit 2 で何もしない。SKILL.md に `<repo>` はワークツリーのパスと明記し、linked worktree のパスの調べ方を書いた |
| R-2（Medium） | ignore 対象の未追跡ファイルは退避されず、ff マージで黙って上書きされて消える | 候補を「`<ref>` が追加するパスにある未追跡ファイル（ignore 対象を含む）」に変えた。`git diff --diff-filter=A` と `git ls-files --others`（除外なし）の完全一致の積集合で求め、symlink のディレクトリの先はたどらない |
| R-3（Low） | SIGTERM で中断すると ff は済んでいるのに exit 1 で何も出力しない | 中断時に全件を戻し、HEAD が進んだかどうかと退避先を stderr に出す。ヘッダと SKILL.md の exit 1 の定義に中断を含めた |
| R-4（Low） | ワークツリーの外の cwd から相対パスの `--git-dir` / `--work-tree` で起動した git を見逃す | 相対パスの値は除外できないものとして判定不能にした |
| R-5（Low） | 並行 `clear` のテストが、遅い `/proc` 走査のせいで flock が無くても通る | 偽の `PROC_ROOT` と偽の `lsof` で即座に終わる条件にした。flock を無効にするとテストが失敗することを確かめた |
| R-6（Low） | ff スクリプトが未追跡ファイル 1 件ごとに `git cat-file` を起動する | R-2 の積集合の計算に置き換えた（git の起動は件数によらず定数回） |
| R-7（Info） | テストが `/tmp/ff-merge-keep-untracked.*` を残す | テストの `TMPDIR` を `tmp_path` に向けた。残っていた退避先は自分のテスト実行のものと確認して削除した |
| R-8（Info） | SKILL.md の「JSON を出さない」場合に flock の失敗が無い | 追記した |
| R-9（個別検証） | `.worktrees/<name>` のように main のワークツリーの中に置いた linked worktree で git が動くと、main のロックが常に判定不能になる | cwd の配下判定をやめ、cwd から git が使うロックを解決して比べる方式にした（上記 1） |
| R-10（個別検証） | `clear` が exit 12 で終わる JSON で、`exists` が true なのに `size` / `mtime` が null になることがある | 判定に数秒かかる間にロックが消えると起きる。size と mtime を判定の前に取得するようにした |
| R-11（個別検証） | git 以外の実装（JGit、libgit2）は fd を閉じたままロックを持つことがあり、検出できない | 既知の限界として SKILL.md に書き、その可能性がある場合は人間の確認を必須とした |
| R-12（自己レビュー） | 候補の列挙（`git diff` → `git ls-files` → `sort` → `comm`）が途中で失敗すると、候補 0 件として素の merge に進み、ignore 対象のファイルを上書きしうる | 一時ファイル経由で `pipefail` を付けて実行し、失敗したら何も変えずに exit 1。`comm` の無い PATH で確かめるテストを追加した |
| R-13（3 回目の再レビュー F-2、High） | ignore 対象の内容が、追加されるファイルのパスにあるディレクトリの下や、追加されるパスの親ディレクトリの位置（ファイル・symlink）にあると、git が確認なしに消す | ff の後には元の場所へ戻せないため、該当パスを表示して何も変えずに exit 1 にした。追跡済みのパスがファイルとディレクトリの間で入れ替わる ff は従来どおり通す |
| R-14（3 回目の再レビュー F-1、High） | `comm` だけ呼び出し元のロケールで動き、GNU coreutils で C 以外の照合順序だと候補を取りこぼす | `LC_ALL=C comm` にした（R-12 の修正で反映済み）。GNU 版の `sort` / `comm` と en_US.UTF-8 で確かめるテストを追加し、`comm` のロケールを外すと失敗することを確認した |
| R-15（3 回目の再レビュー F-3、High） | `core.worktree` で git dir と離れたワークツリーでは、待機中の `git commit -a` を見逃す | cwd がワークツリーの top と同一の git プロセスを該当とし、cwd がワークツリーの配下なのに git が解決できない場合も該当にした |
| R-16（3 回目の再レビュー F-4、Low） | linked worktree の git の子プロセス（`GIT_DIR=<common>/worktrees/<name>`）で、main のロックが判定不能になる | 環境変数・オプションを配下判定ではなく、git dir・ワークツリーの top・ロックのディレクトリとの同一性（`-ef`）で比べるようにした |
| R-17（3 回目の再レビュー F-5、Info） | サブモジュールの `.git/modules/<name>` を `--repo` に渡すと処理が進み、文書の「`.git` の中は exit 2」と食い違う | `--is-inside-git-dir` が true のパスを明示的に拒否するようにした |
| R-18（4 回目の再レビュー F-1、High） | リポジトリの中から `GIT_WORK_TREE` / `--work-tree` で外部のワークツリーを指定した `git commit -a` を見逃す。git は起動時の cwd で git dir を見つけてから外部へ移動するため、cwd でも環境変数でも結び付かない | ワークツリーだけを指定して git dir を指定していない git プロセスは除外できないものとして判定不能にした。環境変数とオプションの両方で、待機中の実際のコミットに対するテストを追加した |
| R-19（4 回目の再レビュー F-2、Medium） | ignore 対象ディレクトリの下にある未追跡の入れ子リポジトリへ `<rev>` がファイルを追加すると、`git ls-files` が中を見ないため退避されず、ローカルの内容が上書きされる | 追加パスの親を浅い側からたどり、追跡されていない `.git` を持つディレクトリがあれば、何も変えずに exit 1 で表示するようにした |
| R-20（4 回目の再レビュー F-3、Low） | `<rev>` が submodule を追加するパスに未追跡の clone があると、素の merge は通るのに不要に止まる | `<rev>` 側の mode が 160000（gitlink）の追加パスでは、ディレクトリの判定を省くようにした |
| R-21（4 回目の再レビュー F-4、Low） | 追跡済みの symlink がディレクトリに置き換わり、追加パスが深いと、symlink の先を見て不要に止まる | 親を深い側からではなく浅い側からたどり、最初の symlink・非ディレクトリで止めるようにした |
| R-22（4 回目の再レビュー F-5、Info） | ヘッダのコメントが、JSON を出さない場合（flock の失敗）と、退避先を消さない条件について不正確 | コメントを動作に合わせた |
| R-23（5 回目の再レビュー F-1、Medium） | symlink の別名で起動した git は comm と argv[0] が git にならず、待機中のコミットを見逃す | `/proc/<pid>/exe` がこのシステムの git と同一（`-ef`）のプロセスも git とみなす。別名の symlink から起動した実際のコミットで確かめるテストを追加した |
| R-24（5 回目の再レビュー F-2、Medium） | 追跡ディレクトリ `a` の位置に ignore 対象のファイル `a` を置くと、`git ls-files -- a` が `a/x` に一致して追跡済みと誤判定され、git が確認なしに消す | index の判定を完全一致（`git rev-parse --verify :0:<path>`）にした。入れ子のリポジトリの判定も同じ方法にした |
| R-25（5 回目の再レビュー F-3、Low） | `<rev>` が submodule を追加するパスに未追跡ファイルがあると、ff は進むのに復元に失敗する | submodule を追加するパスにディレクトリ以外があれば、何も変えずに exit 1 にした。submodule の追加パスは `git diff --raw` 1 回で求める |
| R-26（5 回目の再レビュー F-4、Info） | HEAD にコミットが無い branch で「not a fast-forward」と誤ったメッセージを出す | 対象外である旨を正しく表示して exit 1 にした |
| R-27（5 回目の再レビュー F-5、Low） | `--git-dir` / `GIT_DIR` に `.git` ファイル（linked worktree、サブモジュール）を渡した git を見逃す | ディレクトリでない値は `git rev-parse --resolve-git-dir` で解決してから比べ、解決できなければ除外できないものとした |
| R-28（5 回目の再レビュー F-6、Low） | zombie の git が 1 つでもあると、どのリポジトリの `check` も exit 12 になる | `/proc/<pid>/stat` の状態が Z / X のプロセスを、fd の走査と git プロセスの走査の両方で除外した |
| R-29（5 回目の再レビュー F-7、Info） | ヘッダの「JSON を出さない」場合に、ワークツリーの外（exit 2）が無い | コメントを直した |
| R-30（6 回目の再レビュー F-1、Low〜Medium） | git と判定した後、cwd や environ を読む前にそのプロセスが終了すると、無関係なリポジトリでも exit 12 になる。短命な git が多い開発環境ではテストも時々失敗した | 読み取りに失敗したらプロセスの生存を確かめ、終了していれば除外するようにした。偽の `readlink` で走査中の終了を再現するテストを追加した |
| R-31（6 回目の再レビュー F-2、Medium） | `diff.ignoreSubmodules=all` だと `git diff` が追加される submodule を出力せず、R-25 の拒否が働かずに ignore 対象のファイルが消える | 追加パスの取得を plumbing の `git diff-tree` に替え、設定の影響を受けないようにした。設定を入れた場合のテストを追加した |
| R-32（6 回目の再レビュー F-3、Low） | 別の worktree の `git difftool` の helper（絶対パスの `GIT_DIR` と `GIT_WORK_TREE=.`）が、どのリポジトリの判定も不能にする | git が使う index は git dir と `GIT_INDEX_FILE` で決まるため、git dir が分かっているときはワークツリーの指定を判定に使わないようにした |
| R-33（6 回目の再レビュー F-4、Info） | ff スクリプトのヘッダに、submodule を追加するパスでの拒否が書かれていない | ヘッダに追記した |
| R-34（自己検証） | 7 回目の再レビューと並行して一括テストを実行したところ、実際の `/proc` で exit 11 を期待するテストが 4 件、exit 12 で失敗した。同時に動いていた別の git プロセス（git dir を指定せずワークツリーだけを指定したものなど）を、仕様どおり除外できないと判定したためである | exit 11 を期待するテストは、git プロセスのいない偽の `PROC_ROOT` で実行するようにした。実際の `/proc` で stale と判定できることの確認は 1 件だけ残し、マシン上の別の git プロセスで判定不能になったときは skip する |
| R-35（7 回目の再レビュー F-1、Medium、発生はまれ） | HEAD の `.gitmodules` で `ignore = all` とした submodule を `<rev>` が追加すると、`git diff-tree` でも出力されず、R-25 の拒否が働かない | 両方の `git diff-tree` に `--ignore-submodules=none` を付けた。`.gitmodules` の設定を使うテストを追加し、修正前の版で失敗することを確かめた |
| R-36（7 回目の再レビュー F-2、Low） | git は hook に相対パスの `GIT_INDEX_FILE=.git/index` を渡すため、どこかのリポジトリで hook が git を起動している間、無関係なリポジトリも判定不能になる | 相対パスの `GIT_INDEX_FILE` は、git が動いている cwd（プロセスの現在の cwd）を基準に解決して比べるようにした。相対パスの `GIT_DIR` / `GIT_COMMON_DIR` は従来どおり除外できないものとする |
| R-37（7 回目の再レビュー F-3、Low〜Medium） | `<rev>` が submodule を普通のディレクトリに置き換えると、git は submodule の checkout を残したまま中へ書き込み、superproject で ignore 対象のファイルを確認なしに上書きする | 追加パスの親に index 上の submodule があり、その中の追加パスにファイルが既にあれば、何も変えずに exit 1 で表示するようにした |
| R-38（7 回目の再レビュー F-4、Low） | `GIT_INDEX_FILE` の比較の分岐を無効にしてもテストが通る | 絶対パスと相対パス（cwd 基準）の両方で、ロックのディレクトリの index を指すケースを確かめるテストにした。分岐を無効にすると失敗することを確かめた |
| R-39（8 回目の再レビュー F-1、Low） | R-37 は追加パスそのものしか見ておらず、submodule の checkout 内で途中の構成要素にある ignore 対象のファイル（`sub/x.log` に対する `sub/x.log/y` の追加）を git が消す | submodule の checkout に入った後も構成要素をたどり、途中や追加パスにあるファイル・symlink を拒否するようにした |
| R-40（8 回目の再レビュー F-2、Low〜Medium） | `<rev>` が submodule をファイルに置き換える型変更（T）では、git が checkout をまるごと消し、中の未追跡ファイルも失われる | `git diff-tree --raw` から旧 mode が 160000 の型変更を取り出し、その checkout に中身があれば、何も変えずに exit 1 で表示するようにした。checkout が空なら（未初期化の submodule）従来どおり ff する |
| R-41（9 回目の再レビュー F-1、Low〜Medium） | submodule `a/sub` を含むディレクトリ `a` を `<rev>` がファイルにすると（削除＋追加なので R-40 に掛からず、`git ls-files --others` も submodule の中を見ない）、git が checkout ごと消す | ファイルを置くパスのディレクトリについて、index 上の submodule（`git ls-files -s` の mode 160000）を調べ、checkout に中身があれば何も変えずに exit 1 で表示するようにした。未初期化なら従来どおり ff する |
| R-42（10 回目の再レビュー F-1、Low〜Medium） | パスの先頭が `-` だと、checkout の中身を調べる `find` がそれを式として扱って失敗し、エラーを「空」とみなして R-40 / R-41 の拒否をすり抜ける | `find` をやめ、bash の glob（`nullglob` と `dotglob`）でディレクトリの中身を調べるようにした。読めないディレクトリは中身ありとして拒否する。先頭が `-` の submodule で確かめるテストを追加した（`git submodule add` はそのようなパスを扱えないため、テストでは gitlink を index に直接登録する） |
| R-43（10 回目の再レビュー I-1・I-2、Info） | 文書が R-37 / R-39 の拒否範囲（追加パスにあるディレクトリも拒否する）と、exit 1 で退避先が残る条件を正確に書いていない | SKILL.md・ヘッダ・コード内のコメントを動作に合わせた |
| R-44（自己レビュー） | ファイルを置くパスのディレクトリを調べる `git ls-files` が失敗すると、出力が空として扱われ、「未追跡ファイルも submodule も無い」と判定されてしまう | 一覧の取得に失敗したら、何かが見つかったものとして拒否するようにした。特定のパスの一覧だけを失敗させる偽の git で確かめるテストを追加した |

## 同じ原因の関連箇所（PR 差分外の確認）

リポジトリ全体（`external/`・`reviews/`・`docs_draft/`・`tmp/` を除く）を調べた結果は次のとおり。

- 対応した: SKILL.md の `.git/pr-review-save.lock` の説明（「常設の flock」）は不正確だった。ファイルは常に置かれ、flock は `pr-review` の操作中だけ掛かる。削除すると排他が別のファイルに分かれて壊れることを理由として書き直した。`pr-review` の review worktree のロックが `/tmp` ではなくメインリポジトリの `.git/worktrees/<name>/index.lock` にあることと、`gitdir` での見分け方も追記した
- 対応した: `repo-cleanup-after-merge` 手順 7 は未追跡ファイルがあれば停止する規則であり、PR の退避手順と矛盾していた。上記 5 のとおり SKILL.md 側で使用範囲を限定した
- 対応しない（別機能の潜在的な同類）: `git -C` に継承 `GIT_DIR` を外さない呼び出しは `pr-review`・`cleanup-workspace.bash` など他のツールにもあるが、これらへ `GIT_DIR` を export する経路は現状無い。zsh で読み取り専用の `status` を使う貼り付け例が `rst-writer/evals/README.md` にある。いずれもロック復旧とは別の機能であり、この PR の範囲外として記録だけ残す
- 該当なし: fd だけで保持者を判定する箇所、`cp -p` で未追跡ファイルを退避する手順は、この PR の外に無い

## 推奨案からの変更点

- ff マージの退避手順は、レビュー推奨のスニペット修正ではなく、同梱スクリプトへ置き換えた。指摘 5 件（複数件・zsh・cwd・symlink・失敗時の扱い）を同時に解消し、手順そのものをテストで固定するためである（SWE-2-Max の Test suggestions 2 の「手順をスクリプト化して結合テストにする」に沿う）
- SKILL.md の手動の `rm` と手動の `/proc` 判定例を削除した。H-1 と SWE L-2 の原因（fd だけの判定、直列化の欠如）が手動手順にも残るためである
- H-1 の検出は、Opus 推奨の cwd に加え、git プロセスの環境変数とオプション（`--git-dir` / `--work-tree`）も見る。ワークツリーの外の cwd から別の方法でリポジトリを指定して実行された git を取りこぼさないためである

## 既知の限界

- 他ユーザーのプロセス、PID namespace の外、bind mount で共有する保持者と、git 以外の実装（JGit、libgit2）が fd を閉じたまま持つロックは検出できない。人間の確認を必須とする（SKILL.md に記載）
- `/proc` の fd 走査は fd ごとに `stat` を起動するため、プロセス数に比例して時間がかかる（既存の実装のまま。判定の正しさには影響しない）
