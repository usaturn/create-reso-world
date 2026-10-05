# Issue #39 pr-review の create 中断への対策 設計

- 文書管理／対象リポジトリ: `usaturn/create-reso-world`
- 対象: Issue #39「pr-review の create が60秒のツールタイムアウトで中断し、session.json 未確定の worktree が残る」。PR は Plan の最後の Task で作る
- 基準: `main` の `a6e2c41`（Issue で helper・スキルを実行した親 checkout の HEAD と同じ）
- 経路: brainstorming の architectural 経路。helper の `create` に必須の引数を足し、新しいサブコマンド（`inspect`・`abandon`）を加え、スキルの手順と削除の規則を変えるため
- 状態: draft
- 実行許可: 利用者の 2026-10-05 の指示「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」。この Spec の判断（4 章の D-1〜D-10）は、その指示に基づきエージェント（Claude Code、claude-opus-5-5）が推奨案で決めたもので、Spec 自体の明示承認は得ていない。マージは指示に含まない
- 関連 Plan: `docs/superpowers/plans/2026-10-05-issue-39-pr-review-create-interruption.md`
- 作成: 2026-10-05

## 1. 目的

`pr-review` の準備（`create`）が、遅いだけなのに短いツールタイムアウトで打ち切られないようにする。打ち切られた場合でも、どの工程まで進んだか、プロセスがどう終わったか、何が残ったかが分かり、そのセッションだけを helper で安全に片付けられるようにする。既存の安全条件（HEAD の一致確認、destination のフィンガープリント検証、保存成功の確認、他のレビューと working tree の保護）は緩めない。

## 2. 範囲

変更するファイル:

- `.agents/skills/pr-review/scripts/pr_review_workspace.py`: `create` の試行 ID・進捗の記録・中断の記録、`inspect`・`abandon` サブコマンド、セッション内ファイルの fsync の削除
- `.agents/skills/pr-review/tests/test_pr_review_workspace.py`: 上の挙動のテストと、既存テストの `create` 呼び出しへの試行 ID の追加
- `.agents/skills/pr-review/SKILL.md`: helper の呼び出し方（タイムアウト）、試行 ID、`create` が結果を返さなかったときの手順、削除の規則、出力前セルフチェック
- `.agents/skills/pr-review/references/time-budget.md`: 準備が遅いときの扱いと検証シナリオ
- この Spec と Plan

変更しないファイル:

- `.agents/monitoring-runtimes.md`・`monitoring-long-tasks` スキル。helper の呼び出しは同期のツール呼び出しで待つもので、監視の対応表を変える必要がない（D-1）
- `save`・`verify`・`cleanup` の検査内容。`cleanup` は従来どおり保存成功を確認できたセッションだけを消す
- frontmatter の `allowed-tools`。`inspect`・`abandon` は既存の `Bash(uv run --no-project python *pr_review_workspace.py *)` に、試行 ID の生成は `Bash(date *)` に含まれる

### 範囲外

- レビュー用 worktree を sparse checkout などで軽くすること。計測（3.2 節）では `git worktree add` が準備時間の大半を占めるが、レビューで読めるファイルが変わるため別の検討とする
- この変更より前に残ったセッション（Issue の `/tmp/pr-review-38-wq1dp0rt` など）の片付け。進捗の記録（journal）が無く、`abandon` では本人のセッションだと確かめられない。利用者の判断で扱う
- `save`・`cleanup` が途中で打ち切られた場合の復旧手順。タイムアウトの規約（D-1）は `save`・`cleanup` にも適用するが、中断後の手順は今回の観測の対象外
- `create` が helper のエラー（`error:` で始まる出力と終了コード 2）で終わった場合の自動の片付け。従来どおり停止して報告し、残ったものは調査のために残す（D-7）

## 3. 現状と原因

### 3.1 Issue の時系列と helper の処理順

`create`（`a6e2c41` の `pr_review_workspace.py` L306-L369）は次の順に処理する。

1. モデル名・ブランチ名・main checkout・commit の検査（副作用なし）
2. `tempfile.mkdtemp` でセッションディレクトリ（`/tmp/pr-review-<PR>-<ランダム>`）と `review-backup` を作る
3. main checkout の状態を記録し、`git worktree add --detach` を実行する
4. 作った worktree と main checkout を検査する
5. 共有ロック（Git 共通ディレクトリの `pr-review-save.lock` の flock）を待って取る
6. ロックを持ったまま、既存レビューの snapshot を取り、`session.json` を一時ファイルへ書いて fsync し、`os.replace` で確定する
7. 結果の JSON を stdout に出す

Issue の時系列では、セッションディレクトリの作成が 12:09:47.008、worktree ディレクトリの mtime が 12:10:09.47、一時 JSON の書き込みが 12:10:20.10〜.11 である。ツール呼び出しは context helper の出力（12:09:30）より後に始まったので、60 秒のタイムアウトは 12:10:30 以降に来た。少なくとも約 10 秒、処理は 6 の一時ファイルの書き込み後から `os.replace` の前、つまり fsync の中かその前後にいた。残った状態（一時 JSON あり・`session.json` なし）はこれと整合する。strace などが無いため、fsync で止まっていたとは断定しない。

### 3.2 計測

同じ Dev Container で、`git clone --shared` で作った使い捨ての clone（`main` の `a6e2c41`）に対して、現行の helper の `create` を工程ごとの時刻を記録しながら実行した。worktree とセッションは scratchpad（コンテナの overlay 上。`/tmp` と同じファイルシステム）に作り、利用者の checkout と既存の worktree には触れていない。対象ツリーは 3,671 ファイル、1,534.7 MiB である。

| 条件 | `git worktree add` | `session.json` の fsync | `create` 全体 |
| --- | --- | --- | --- |
| 単独 | 18.4 秒 | 1.1 秒 | 19.9 秒 |
| 4 件同時 | 136.2〜138.6 秒（各件） | 最初にロックを取った 1 件が 95.2 秒。残り 3 件はその間ロックを待ち、fsync は 0.01 秒 | 234.7〜234.8 秒（全件） |

- 4 件同時では、最初の 1 件が共有ロックを持ったまま 95 秒 fsync で待ち、他の 3 件はその間ロックを待った。fsync は小さな `session.json` 1 個のためだが、直前に 4 件の checkout が書いた約 6 GiB の未書き出しデータの書き出しを待つことになったと考えられる
- 単独でも 60 秒のうち約 20 秒を `create` が使い、fetch・`gh`・`uv` を同じ呼び出しに入れると余裕は小さい。同時レビューでは 60 秒どころか Claude Code の Bash の既定（120 秒）も超える
- Issue の環境では同じ PR のレビュー用 worktree が他にも登録されていた。同時のレビューで `git worktree add` と fsync が遅くなった可能性が高い

### 3.3 60 秒の指定と規約の関係

- スキルにも時間予算の規約にも、ツール呼び出しのタイムアウトについての記述が無い。60 秒はエージェントが fetch・HEAD 確認・`create` をまとめた呼び出しに付けた値で、helper の仕様値ではない
- `references/time-budget.md` の「0〜5 分 準備」は目安で、「準備が遅れても期限は起点から固定」とある。期限はフェーズの境界で確かめるもので、実行中の処理を打ち切って守るものではない
- `monitoring-long-tasks` は「生きているが止まって見えるタスクを期限のために止めない」と定めている。短いツールタイムアウトは、生きている helper を止めるのと同じ結果になる
- スキルは `create` を一度だけ実行し、削除は保存成功後の `cleanup` だけに限っている。そのため `create` が打ち切られると、レビューを続ける手段も片付ける手段も無く、レビューが中止になり worktree が残る

### 3.4 state 確定前の中断で足りないもの

1. 進捗の記録が無い。どの工程にいたか、ロックを待っていたかが後から分からない
2. 自分のセッションを見分ける手がかりが無い。セッションディレクトリ名はランダムで、`create` の結果を受け取れなかったエージェントには、同じ PR の他のセッションと区別できない
3. 生存の確認手段が無い。PID は記録されず、記録しても再利用や子プロセス（`git worktree add` の checkout）の残存を判定できない
4. 正式な片付けの経路が無い。`cleanup` は正式な `session.json` と保存済みのレビューを前提にする

## 4. 設計

### D-1 helper の呼び出しを短いタイムアウトで打ち切らない

- helper の呼び出し（`create`・`verify`・`save`・`cleanup`・`inspect`・`abandon`）は、fetch・`gh` など所要時間の読めない別の処理と同じツール呼び出しにまとめない。結果の JSON を読む `jq` は同じ呼び出しでよい
- ツール呼び出しにタイムアウトを指定できるランタイムでは、指定しないか 600 秒以上を指定する。上限が 600 秒未満のランタイムではその上限を指定する。Claude Code の Bash は `timeout: 600000`（ミリ秒）、pi の bash は秒単位なので省略するか 600 以上とする
- 600 秒は、計測した同時 4 件の約 235 秒に余裕を持たせ、Claude Code の Bash の上限と一致する値である。全体予算（既定 45 分）はフェーズの境界で確かめる
- 進捗は helper の stderr（D-3）で見える。それでも打ち切られた場合は D-7 の手順に従う

### D-2 試行 ID

- エージェントは `create` の前に `ATTEMPT_ID=$(date -u +%Y%m%dT%H%M%S%NZ)` で試行 ID を決め、進捗記録に残してから `create --attempt-id "$ATTEMPT_ID"` に渡す。`create` が何も返さずに終わっても、エージェントは自分の試行を ID で指せる
- helper は形式（英数字で始まり、英数字と `.`・`_`・`-` だけの 1〜64 文字）を検査し、同じ一時ルートの同じ PR に同じ ID の試行が既にあれば、セッションディレクトリを作る前に拒否する
- `--attempt-id` は `create` の必須引数とする。ナノ秒の時刻を使うのは、Claude Code の `allowed-tools`（`Bash(date *)`）の範囲で生成でき、同時のレビューでも重ならないためである。万一重なっても、`inspect`・`abandon` は該当が複数あれば何もせずに拒否する

### D-3 進捗の記録（journal）と creator のロック

- `create` はセッションディレクトリを作った直後に `create-journal.jsonl` を作り、そのファイルの排他 flock を `create` の終了まで持ち続ける。この flock を「creator のロック」と呼ぶ
- `git worktree add` の子プロセスにはこのファイルの fd を引き継ぐ（`pass_fds`）。親の Python が先に強制終了されても、checkout を続けている子が生きている間はロックが残り、`inspect` は実行中と判断する
- 生存の判定は PID ではなくロックで行う。カーネルはプロセスの終了時にロックを解放するので、PID の再利用や子プロセスの取り違えが起きない
- journal は 1 行 1 レコードの JSON で、各レコードに UTC の時刻（ミリ秒）を持つ。最初のレコード（`started`）に試行 ID、PID、PR 番号、commit、ブランチ、モデル名、main checkout、セッションディレクトリ、worktree のパスを書く。以降は工程の開始ごとに 1 行足す

| phase | 意味 |
| --- | --- |
| `started` | セッションディレクトリと journal を作った |
| `worktree-add` | `git worktree add` を始めた |
| `worktree-verify` | 作った worktree と main checkout の検査を始めた |
| `lock-wait` | 共有ロックを待ち始めた |
| `state-write` | 共有ロックを取り、既存レビューの snapshot と `session.json` の書き込みを始めた |
| `completed` | `session.json` を確定した（終端） |
| `failed` | helper のエラーで終わった。`error` にメッセージ（終端） |
| `interrupted` | シグナルで中断した。`signal` にシグナル名（終端） |

- 同じ内容を 1 行ずつ stderr にも出す（例: `pr-review create 20261005T121530123456789Z: 2026-10-05T12:15:52.004Z worktree-add`）。最初の行にはセッションディレクトリを含める。ツールのタイムアウトで打ち切られても、ランタイムが途中の出力を返せば、どこまで進んだかが分かる
- journal の書き込みは fsync しない。OS が落ちた場合はセッションごと使えなくなるので、書き出しの保証は要らない
- journal とロックは `cleanup`・`abandon` がセッションディレクトリごと消す。`save`・`verify`・`load_state` は journal を読まない

### D-4 中断の記録

- `create` の実行中に SIGTERM・SIGHUP・SIGINT を受けたら、journal に `interrupted` とシグナル名を書き、終了コード 128＋シグナル番号で終わる。`subprocess.run` は例外で抜けるときに子の git を止める
- helper のエラー（`WorkspaceError` など）で終わったら、journal に `failed` とメッセージを書く。終了コードは従来どおり 2
- SIGKILL やクラッシュでは終端のレコードが残らない。`inspect` はロックが外れているのに終端が無い状態を `vanished`（終了コードは不明）と報告する
- 中断時に worktree を自動で消す巻き戻しはしない。ツールのタイムアウトは SIGTERM の後に SIGKILL を送ることが多く、巻き戻しが途中で止まると、より分かりにくい状態が残る。調査できる状態を残し、片付けは `abandon` に任せる

### D-5 `inspect`（読み取り専用）

```bash
uv run --no-project python "$HELPER" inspect --repo "$MAIN_ROOT" --pr-number "$PR_NUMBER" --attempt-id "$ATTEMPT_ID" --temp-root /tmp [--wait <秒>]
```

- `<temp-root>/pr-review-<PR>-*/create-journal.jsonl` の最初のレコードの試行 ID で、自分の試行のセッションを探す。シンボリックリンクのディレクトリ・journal は対象にしない。該当が 2 件以上なら何も報告せずにエラーとする
- journal の main checkout が `--repo` と一致しなければエラーとする
- `--wait <秒>` を付けると、状態が `running` の間は最大その秒数まで待ってから報告する。待つ間は 1 秒ごとに creator のロックを確かめる
- creator のロックは取れるかどうかを確かめるだけで、すぐに外す。ファイル・worktree・Git の状態は変えない

出力（JSON）:

| キー | 内容 |
| --- | --- |
| `attempt_id` | 渡した試行 ID |
| `status` | `absent`（該当なし）・`running`・`completed`・`failed`・`interrupted`・`vanished` |
| `session_dir` | セッションディレクトリ。`absent` では `null` |
| `pid` | journal に記録した `create` の PID |
| `phases` | 各レコードの `phase` と `at` の一覧 |
| `last_phase`・`last_phase_at` | 最後に記録した工程と時刻 |
| `error`・`signal` | `failed`・`interrupted` のときのメッセージ・シグナル名 |
| `state_file` | 正式な `session.json` があればそのパス、無ければ `null` |
| `worktree` | セッションの worktree のパス |
| `worktree_exists`・`worktree_registered` | ディレクトリの有無と、`git worktree list` への登録の有無 |
| `worktree_lock` | worktree のロックの理由（`initializing` など）。ロックされていなければ `null` |
| `entries` | セッションディレクトリ直下と `review-backup` 直下の名前の一覧（残存パスの確認用） |

### D-6 `abandon`（中断した試行の片付け）

```bash
uv run --no-project python "$HELPER" abandon --repo "$MAIN_ROOT" --pr-number "$PR_NUMBER" --attempt-id "$ATTEMPT_ID" --temp-root /tmp
```

共有ロックを取ったうえで、次をすべて満たすときだけ消す。1 つでも満たさなければ何も消さずにエラーで終わる。

1. 試行 ID に該当するセッションがちょうど 1 件あり、一時ルート直下の実ディレクトリである
2. journal の main checkout・セッションディレクトリ・PR 番号が、`--repo` で照合した main checkout と見つけたセッションに一致する
3. creator のロックを取れる（`create` とその子プロセスが終わっている）。取れたロックは片付けの終わりまで持つ
4. セッションディレクトリ直下が `create-journal.jsonl`・`review-backup`・`worktree`・`session.json`・`.session.json.*`（`session.json` の書き込み途中の一時ファイル）だけで、シンボリックリンクを含まない
5. `review-backup` 直下が `previous-review.md`・`.previous-review.md.*`（helper が作る既存レビューの snapshot）だけである。draft など、それ以外のファイルがあれば保存されていないレビューの内容とみなして残す
6. worktree の扱い:
   - ディレクトリがあり登録されている: `cleanup` と同じ検査（このリポジトリの linked worktree で、パスが一致する）を通ったら `git worktree remove --force` で消す。ロックの理由が `initializing`（`git worktree add` が途中で止まった印）のときだけ `--force` を 2 回付ける。それ以外の理由のロックは利用者が付けたものとみなし、git の拒否をそのまま返す
   - ディレクトリが無く、登録も無い: worktree を作る前に止まった。消す worktree は無い
   - ディレクトリがあり登録が無い: 中が空なら消してよい。空でなければ拒否する
   - 登録があるのにディレクトリが無い: 拒否する（`git worktree prune` は他のセッションにも作用するため使わない）
7. worktree を消した後、登録とディレクトリが無いことを確かめてから、セッションディレクトリを消す

- `abandon` は `reviews/`・main checkout の working tree・他のセッションに触れない。`git worktree remove` に渡すのは、セッションディレクトリから導いた自分の worktree のパスだけである
- `session.json` がある（`create` は完了したが結果を受け取れなかった）場合も片付けられる。draft が無ければ、失うのは既存レビューの snapshot（保存先の写し）だけである
- 出力は `attempt_id`・`session_dir`・`worktree`・`worktree_removed`・片付け前の `status` の JSON とする

### D-7 スキルの手順

- `create` は試行 ID ごとに一度だけ実行する
- `create` の呼び出しが、helper の結果の JSON も helper のエラー（`error:` で始まる出力）も返さずに終わった場合（ツールのタイムアウト、ランタイムによる中断など）は、次の順に扱う
  1. `inspect` を実行する。`running` なら `--wait 540` を付けて `inspect` をやり直し、終わるのを待つ。それでも `running` なら、`abandon` も再試行もせず停止して報告する
  2. `absent` 以外なら `abandon` を実行する。拒否されたら、削除を手で代行せず停止し、`inspect` の出力（工程・状態・残存パス）と拒否の理由を報告する
  3. `abandon` が成功した、または `inspect` が `absent` だった場合、調査期限まで 10 分以上残っていれば、新しい試行 ID で `create` を 1 回だけやり直してよい。残っていなければ停止して報告する
  4. やり直しの `create` も結果を返さなければ、同じく `inspect`・`abandon` を行い、再試行せずに停止して報告する
- `create` が helper のエラーで終わった場合は、従来どおり手動の代替コマンドを実行せずに停止して報告する。残存パスの報告に `inspect` を使ってよいが、`abandon` はしない
- 削除の規則は「自セッションの worktree の削除は helper の `cleanup` だけが行う」を保ったまま、「`create` が結果を返さずに中断した試行の残存物は helper の `abandon` だけが片付ける」を足す。`git worktree remove`・`rm -rf` を自分で組み立てない規則と、helper が拒否したら手で代行しない規則は両方に適用する
- 最終応答と停止時の報告には、扱った試行 ID と `inspect`・`abandon` の結果を含める

### D-8 セッション内のファイルの fsync をやめる

- `session.json`（`write_json`）と既存レビューの snapshot（`previous-review.md`）の書き込みから fsync を外す。一時ファイルへ書いて `os.replace` で置き換える手順は残すので、他のプロセスからは「無い」か「全部ある」かのどちらかしか見えない
- fsync が守るのは OS の停止・電源断の後の内容だけである。その場合はレビューのセッション自体を続けられず、壊れた `session.json` は `load_state` が JSON の解析や必須キーの検査で拒否する
- 計測では、この fsync が共有ロックを持ったまま 95 秒かかり、他のセッションの `create`・`save`・`cleanup` を止めていた
- レビュー成果物の保存（`save` の `atomic_copy`）の fsync は残す。リポジトリに残る成果物であり、保存成功の確認の前提になる

### D-9 変えない安全条件

- HEAD の一致確認 3 地点、`merge-base` の確認、destination のフィンガープリント検証、保存成功を確かめてからの `cleanup`、既存の worktree を再利用しない規則、`git clean`・強制 checkout・reset の禁止
- `save` で model・draft・destination を再指定しない規則、`create` が返した値を推測・再構築しない規則（`inspect` の出力から `create` の結果を組み立てて続行しない）
- 他モデルのレビュー本文を読まない規則

### D-10 判断の理由（採らなかった案）

- 巻き戻しだけで済ませる案（中断時に helper が worktree を消す）: SIGKILL では動かず、SIGTERM の後の SIGKILL で途中のまま止まる。調査できる状態も残らない
- `create` を 2 段に分け、先に軽い準備コマンドでセッションのパスを返す案: 呼び出しが増え、準備コマンド自体の中断も扱う必要がある。試行 ID なら呼び出しは増えない
- 中断したセッションを `inspect` の出力から引き継いで続行する案: `create` の結果を再構築しない規則に反し、確認すべき分岐が増える。片付けて作り直す手順に揃える
- ロック外へ fsync を移す案: 他のセッションは止まらなくなるが、自分の `create` は同じだけ待つ

## 5. 受け入れ条件との対応

| Issue の受け入れ条件 | 対応 |
| --- | --- |
| 単独・同時レビューで、遅いだけの準備を短いタイムアウトで中断せず、監視・待機できる | D-1（タイムアウトの規約）、D-3（stderr の進捗）、D-5（`inspect --wait`）、D-8（ロック内の fsync をやめる） |
| 意図的に中断したケースで、到達工程・プロセス終了状態・残存パスが分かる | D-3・D-4・D-5。SIGKILL と SIGTERM で中断するテスト（8 章） |
| 正式な state が未確定のケースに、危険な手動復旧や別セッションの流用を必要としない取り扱いがある | D-2・D-6・D-7 |
| 他レビューの成果物、working tree、他セッションの worktree を保護できる | D-6 の条件 1〜7。保護を確かめるテスト（8 章） |
| 既存の安全条件を緩めない | D-9。fsync の変更の理由は D-8 |

## 6. Issue の調査依頼への回答

| 調査してほしい点 | 回答 |
| --- | --- |
| 60 秒を指定した経緯と、全体予算・監視規約との整合 | 3.3 節。スキルにタイムアウトの規約が無く、エージェントが fetch から `create` までをまとめて 60 秒にした。予算はフェーズの境界で確かめるもので、監視規約は生きている処理を期限のために止めない。D-1 で明文化する |
| 遅いだけの場合と停止・異常終了を見分けるために取るべき情報 | 工程と時刻（journal・stderr）、creator のロックによる生存、終端のレコード（`completed`・`failed`・`interrupted`）と終了コード。終端が無くロックも外れていれば `vanished` |
| `session.json` 確定前の中断で、自セッションだけを識別して調査・復旧する経路 | 試行 ID（D-2）で `inspect`（D-5）し、`abandon`（D-6）で片付けて作り直す（D-7） |
| `write_json` の区間と共有ロック保持時間の実測 | 3.2 節。単独で fsync 1.1 秒、同時 4 件ではロック内の fsync が 95.2 秒 |
| 同時レビューやストレージ遅延の影響 | 3.2 節。同時 4 件で `git worktree add` が単独の約 7.4 倍、`create` 全体が約 235 秒。既存の worktree と他のセッションには触れず、使い捨ての clone で計測した |

## 7. スキル・参照文書の変更

- `SKILL.md` の「規約」: helper の呼び出し方（D-1）、削除の規則の追記（D-7）
- `SKILL.md` の「ランタイム別の注意」: Claude Code と pi のタイムアウトの指定
- `SKILL.md` の手順 2: 試行 ID の生成と記録、2 つの `create` の行への `--attempt-id "$ATTEMPT_ID"`、`create` が結果を返さなかったときの手順（D-7）
- `SKILL.md` の手順 9 と出力前セルフチェック: 試行 ID と `inspect`・`abandon` の結果の報告、短いタイムアウトを付けていないかの確認
- `references/time-budget.md`: 準備が遅れても helper を打ち切らないこと、`create` の再試行は調査期限まで 10 分以上あるときだけであること、検証シナリオ S23〜S25

## 8. テスト方針

helper の挙動をテストで確かめる。文書の文言を固定値で比べるテストは新しく書かない。既存の契約テストが文言の変更で失敗した場合は、変更の意図に照らして検査が要るかを確かめてから扱う。

- `create`: 試行 ID の必須・形式・重複の拒否。成功時の journal（工程の順と最初のレコードの内容）
- 中断（別プロセスで実行）: `git worktree add` の直後で止まる git のラッパーを PATH に置き、`create` を実行する
  - 実行中に `inspect` が `running` と工程 `worktree-add` を返す
  - SIGKILL でプロセスグループを止めると `vanished`、SIGTERM では終了コード 143 と `interrupted`（`SIGTERM`）
  - 共有ロックをテスト側で持って `lock-wait` で止め、SIGKILL した後に `abandon` で片付けられる（Issue の状態の再現。`.session.json.*` の一時ファイルも含める）
- `abandon` の保護: 実行中・draft あり・未知のファイルあり・別リポジトリ・`initializing` 以外のロックでは何も消さない。`initializing` のロックは消せる。他の試行のセッション、`reviews/` の他のファイル、main checkout の状態は変わらない
- `inspect`: 該当なしで `absent`、同じ試行 ID が 2 件で拒否
- fsync: `create` は fsync を呼ばない（共有ロック内で長く待たない）
- 既存のテストは、`create` の呼び出しに試行 ID を足すだけで挙動の期待を変えない

## 9. 実装の記録

（実装の完了後に追記する）
