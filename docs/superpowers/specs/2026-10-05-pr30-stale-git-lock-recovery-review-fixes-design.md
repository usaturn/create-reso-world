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
  - git はワークツリーの top で動くので、そのプロセスの cwd から `git rev-parse --git-path index.lock` で解決したロックのディレクトリが、対象のロックのディレクトリと同じ（`-ef`）なら該当とする。入れ子の worktree やサブモジュールの git は別の index を使うので該当しない
  - または、環境変数 `GIT_DIR` / `GIT_WORK_TREE` / `GIT_COMMON_DIR` / `GIT_INDEX_FILE`、オプション `--git-dir` / `--work-tree` の絶対パスが、ワークツリーの top・git dir・共通 git dir の配下を指す。相対パスの値は、起動後に cwd が変わっていて解決できないため該当とみなす
  - cwd・環境変数・コマンドラインを読めない git プロセスは除外できないため、該当とみなす
- `--repo` はワークツリーの中のパスに限る。`.git` やその中（`.git/worktrees/<name>` など）では、ワークツリーの top が分からず git プロセスを見落とすため、exit 2 で何もしない
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
4. `git merge --ff-only` を 1 回だけ実行する
5. 成否にかかわらず全件を元のパスへ戻して一致を確かめる。merge が失敗した場合は exit 1 で HEAD は変わらない。HUP / INT / TERM でも復元し、HEAD が進んだかどうかを stderr に出す。退避先は消さない

cwd に依存せず、`path` などの zsh の特殊変数を貼り付け用スニペットで使わない。SKILL.md は「`repo-cleanup-after-merge` の手順 7 の中では使わない（手順 7 は未追跡ファイルがあれば停止して報告する）」と明記し、手順 7 の停止規則と矛盾しないようにする。

検証: 通常ファイル 2 件（一方は upstream と同一）・サブディレクトリの空白入りファイル・symlink の衝突で、リポジトリ外の cwd とサブディレクトリの `--repo` から実行して、ff 後に全件が元の内容・種類・パーミッションで戻ること。merge 失敗時・ff でない場合・退避先を作れない場合に何も失わず HEAD が変わらないこと。ignore 対象のファイルを残すこと。同名のディレクトリや symlink のディレクトリの先には触れないこと。merge 中の SIGTERM で全件を戻し、HEAD が進んだことを報告すること。継承した `GIT_DIR` を無視すること。usage エラーで何も変えないこと。SKILL.md の bash スニペットが `path=` / `status=` を使わず、`rm` を含まないことを契約テストで固定する。

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
