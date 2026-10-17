# PR #127: 実行予算と task_watch（Issue #115）のレビュー修正要否

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/127（`feat/issue-115-budget-task-watch` → `main`）
- 関連 Issue: #115（`closingIssuesReferences`、本文の `Closes #115`）
- 関連文書: `docs/superpowers/specs/2026-10-17-create-reso-world-issue115-budget-task-watch-design.md`、`docs/superpowers/plans/2026-10-17-create-reso-world-issue115-budget-task-watch.md`（どちらも draft のまま。この文書では変えない）
- 検証したコード HEAD: `e8d1287bf87e8f8885897a4db955249b14f5d1f4`。PR の分岐点は `cd602e6`。作業中に base `main` が PR #129・#130 のマージで `61763dc` に進んだ（「確認の範囲」の S-1）
- 状態: completed
- 実行許可: 利用者が 2026-10-17（JST）に `/review-fix-planning #127` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が必要なら既存 PR への push）として扱う
- 結論: 1（修正して push）
- 設計の見直し: あり。L-1 の修正後の自己レビューで、直した条件がまた破れていた（きっかけ 3「自己レビューでの再発」）。下の「守る条件の設計」
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-115-budget-task-watch`（PR head を checkout 済みの既存 worktree を、clean・PR head 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`reviews/#127-feat-issue-115-budget-task-watch/` の 2 ファイル。対象 HEAD はどちらも `e8d1287bf87e` で、取得した `pull/127/head` と一致する。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `claude-opus-5-5.md` | Approve | L-1、I-1 |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | Approve | なし |

## 分類

| ID | 出どころ | 内容 | 分類と根拠 |
| --- | --- | --- | --- |
| L-1 | Opus | pi の bash ツールが timeout・中断で戻ると、watcher だけが消えて対象が監視なしで残ることが `monitoring-runtimes.md` に書かれていない | **対応する**（(a) 再現した誤動作、(b) 事実誤認の記述）。下の「L-1」 |
| I-1 | Opus | `execution-budget.md` の適用範囲と checkpoint の節が、まだ無い `issue-to-pr`（#114）を挙げている | 対応しない。致命的ではない。`issue-to-pr` が無い間はその run が起きないので、規則が適用されないだけである。読んだエージェントが誤った操作をする経路は無い。#114 がスキルを足した時点で記述が有効になる |
| SR-1 | 自己レビュー（反証・検証の検出力の両方） | `status` の `target_alive` が対象の先頭のプロセスしか見ないので、process group に子が残っていても `false` になる | **対応する**（(a) 再現した誤動作）。L-1 で直した条件の再発（きっかけ 3）。下の「守る条件の設計」 |
| SR-2 | 自己レビュー（検証の検出力） | `--stop none` では、pi の行に最初に書いた timeout の目安の式が watcher の戻る時刻の上限にならない | 対応しない。致命的ではない（watcher が消えても `status` が `target_alive: true` を返して保留になる）。設計の見直しで式そのものを外し「`timeout` は付けない」にしたので、この式は残らない |
| SR-3 | 自己レビュー（反証） | 同じ式で、フラグを省略したときの既定値（ポーリング 5 秒・停止確認 30 秒）を書いていない | 対応しない。致命的ではない。SR-2 と同じく式を外した |
| SR-4 | 自己レビュー（反証） | pi が SIGKILL を送るのは SIGHUP/SIGTERM のときだけではない（端末の切断（EIO）・捕捉されない例外でも `killTrackedDetachedChildren` を呼ぶ） | 致命的ではない（どの条件でも `final.json` が無ければ `status` の規則で扱える）が、この回に書いた箇条の事実の誤りなので、`interactive-mode.js` で確かめて文言を直した |
| SR-5 | 自己レビュー（反証） | Claude Code の TaskStop は background の Bash のプロセスツリー全体に SIGTERM・SIGKILL を送るので、宣言した停止（`--stop INT` での保存など）が飛ばされる | 対応しない。文書は Claude Code でも `stop` を使うよう定めており、文書どおりの経路の問題ではない。TaskStop で止めた後も、`final.json` が無いので `status` の規則で扱える |
| SR-6 | 自己レビュー（反証） | 対象の起動から `declaration.json` を書くまでの間（`task_watch.py` 605〜622 行）に watcher が消えると、`status` が終了コード 2 になる | 対応しない。数ミリ秒の窓で、`status` は失敗するだけで対象を終わったとは報告しない |
| SR-7 | 自己レビュー（PR 全体） | 安全の失敗を記録して終わった対象が group に子を残すと、`final.json` は `hold`・`residual_processes` になり、`reason` から `safety` が消える | 対応しない。保留なので依存する作業は始まらず、`failures` に safety の分類が残る。判定 0 の記述どおり |
| SR-8 | 自己レビュー（PR 全体） | 起動し直すときに前回と同じ進捗・結果のパスを使うと、古い記録を読む | 対応しない。手順はパスの再利用を指示しておらず、古い失敗を数える分には止まる側に倒れる |

分類: **解消済み 0 / 対応する 2（L-1・SR-1）/ 対応しない 7（I-1・SR-2〜SR-8。SR-4 は文言だけ直した）**。DeepSeek のレビューと、自己レビューの PR 全体の観点は、致命的な指摘が無い。

仕様の論点として残すもの: なし。

## L-1

### 致命的である理由

`monitoring-runtimes.md` の pi の行のとおりに使うと、生きている worker を終わったものとして扱う。

- 最初の対応表の pi の行は「foreground の実行が戻ることが、そのまま `report exists OR worker is not alive` の解消になる」としている。`task_watch.py` で包んだ対象では、これが誤りになる
- pi 1.3.0 の bash ツール（`@earendil-works/pi-coding-agent` の `dist/core/tools/bash.js`）は、シェルを `detached: true` で起動し、`timeout` を超えたとき・中断（abort）のときに `killProcessTree(child.pid)` を呼ぶ。`dist/utils/shell.js` の `killProcessTree` は Linux では `process.kill(-pid, "SIGKILL")`。pi が終わるとき（SIGHUP・SIGTERM・端末の切断・捕捉されない例外）も、追跡中の子の process group に同じ SIGKILL を送る（`killTrackedDetachedChildren`。`dist/modes/interactive/interactive-mode.js`・`print-mode.js`・`rpc-mode.js`）
- `task_watch.py` は対象を `start_new_session=True` で起動する（605〜607 行）。watcher のシグナルハンドラーは SIGINT・SIGTERM・SIGCHLD だけ（597〜602 行）で、SIGKILL では `final.json` を書けない。消えるのは watcher だけで、対象は宣言した期限を過ぎても止まらない
- 到達する条件: pi のエージェントが bash ツールに `timeout` を付けるのは、このリポジトリでも普通の使い方である（`.agents/skills/pr-review/SKILL.md:42` は helper に 600 以上の `timeout` を付けるよう求めている）。利用者が長い foreground の待ちを中断することや、pi を終えることもある
- 起きること: 宣言した期限・予約枠・無進捗の判定が止まり、評価 worker が LLM の CLI なら期限を過ぎても API の利用が続く。controller は「戻った = worker は生存していない」として、依存する作業を始めたり、同じ worker を起動し直したりしうる。どちらも `monitoring-long-tasks` が防ぐべき誤りである

### 再現（レビュー時の HEAD `e8d1287` の隔離 worktree）

pi 1.3.0 の `createLocalBashOperations()`（pi の bash ツールが使う実行部）をそのまま Node から呼び、`task_watch.py run` を実行した。

| 場面 | 宣言 | 結果 |
| --- | --- | --- |
| V1: `timeout: 8` | 期限 20 秒、`--stop INT`、停止確認 5 秒、ポーリング 1 秒、対象 `sleep 40` | 8 秒で `timeout:8` が返る。`final.json` は無い。`status` は `{"source": "status", "decision": "continue", "watcher_alive": false, "target_alive": true}`。対象は別の session（`Ss`）で、27 秒（期限 + 停止確認を過ぎた後）でも生存していた |
| V1b: V1 の後の `stop` | 同上 | `watcher identity does not match` で拒否（終了コード 2）。対象にはシグナルを送らない |
| V4: 5 秒で abort | 期限 20 秒、停止確認 3 秒 | `aborted` が返る。`final.json` は無く、`status` は `watcher_alive: false`・`target_alive: true`。`stop` は拒否（2）で、対象は生存 |
| V2: `timeout: 70` | 期限 6 秒、停止確認 3 秒 | 9.6 秒で戻る（終了コード 1）。`final.json` は `stopped`・`deadline`・`confirmed: true`・`residual_pids: []` |
| V3: `timeout` なし | 期限 4 秒、停止確認 2 秒、`--escalate-kill`、SIGINT を無視する対象 | 6.6 秒で戻る。`final.json` は `stopped`・`confirmed: true`（SIGKILL で停止、`exit_code: -9`） |

再現に使った対象は手で止め、残存プロセスが無いことを確かめてから worktree を外した。

## 守る条件の設計（L-1・SR-1）

### きっかけと根拠

L-1 を最初に直した版（未公開。`SKILL.md` に「`final.json` が無ければ `status` を実行し、`watcher_alive: false` と `target_alive: true` なら保留」、pi の行に timeout の目安の式を書いた）の自己レビューで、反証と検証の検出力の 2 つの担当が、同じ穴を独立に再現した。`status` の `target_alive`（`task_watch.py` 691 行）は対象の先頭のプロセスの PID と starttime だけを照合する。先頭が終わって同じ process group に子が残ると `false` を返すので、規則をすり抜ける。

- 経路 A: watcher が停止確認の途中で消え、先頭は SIGINT で終わったが、SIGINT を無視するバックグラウンドの子が残った。`final.json` は無く、`status` は `watcher_alive: false`・`target_alive: false`
- 経路 B: 対象が子を残して終わり、watcher は正しく `hold`・`residual_processes`（終了コード 3）を書いた。その後の `status` は `watcher_alive: false`・`target_alive: false`。私も `bash -c 'sleep 120 & exit 0'` で再現し、group に `sleep 120` が生きていることを確かめた
- 起きること: `SKILL.md` の新しい規則は保留にしない。`.agents/execution-budget.md:46` の片付けは「両方 `false`」を満たすので、子がまだ書いている `$SESSION` を `rm -rf` できる。依存する作業や起動し直しにも進める

これは L-1 で直した条件（生きている対象を終わったとみなさない）の再発である。

### 守る条件

対象（watcher が起動した process group）に生きているプロセスが 1 つでもある間は、どの観測の経路（`run` の戻り、`final.json`、`status`）も対象を終わったと報告しない。この条件は、watcher の生死、停止の宣言（`INT`・`TERM`・`none`）、watcher が消えた位置（ポーリング中・停止確認中・終了後の待ち合わせ中・`final.json` を書いた後）のすべてで成り立つ必要がある。controller が対象の終了とみなしてよいのは、`final.json` が `completed`・`exited_incomplete`・`stopped`（停止確認済みで `residual_pids` が空）を示すか、`status` が `target_alive: false` を返したときだけである。

### 条件を保つ仕組み

- watcher が生きている間: watcher 自身が group 全体を見る（`_wait_group_empty`・`_wait_stopped`・`_live_group_members`）。group が空にならなければ `hold` にし、`residual_pids` を書く（既存）
- watcher が消えた後: `status` の `target_alive` を、先頭のプロセスの照合か、group（pgid = 対象の PID）に生きているプロセスがあることにする。残った PID を `target_group_pids` に返す（今回の変更）。`SKILL.md` の規則と `execution-budget.md:46` の片付けは `target_alive` を読むので、そのままで条件を満たす

### 以前の修正で足りなかった理由

最初の版は、watcher の終了と対象の終了を区別する規則を足したが、対象の終了を確かめる手段として `target_alive` をそのまま使った。`target_alive` は watcher が持つ group 単位の残存の検査（移植元からある `residual_processes`）と粒度が違い、watcher が消えた後には group を見る経路が無かった。影響経路の表を「文書の行」から作り、`status` が何を見ているかを経路として挙げなかったのが原因である。

### 影響経路（仕組みから列挙）

対象の生存を書く・読むすべての箇所と、watcher が止まりうるすべての位置を挙げた。

| 経路 | 変更前の挙動 | 判定 | 確かめる assertion |
| --- | --- | --- | --- |
| `_status` の `target_alive` | 先頭のプロセスだけを照合 | 修正する（group も見る。`target_group_pids` を足す） | 経路 B: `run` が `hold`・`residual_processes` の後、`status` が `(watcher_alive, target_alive) == (False, True)` で `target_group_pids == residual_pids`。経路 A: watcher を SIGKILL し先頭が終わった後、`final.json` が無く、`status` が `(False, True)` で `target_group_pids` の全 PID が生存。group を止めた後は `target_alive: false`・`target_group_pids == []` |
| watcher の終了判定（`_run` の `completed`/`exited_incomplete` の後の `_wait_group_empty`） | group が空でなければ `hold`・`residual_processes` | 既に満たす | 既存の `test_processes_left_in_the_group_after_exit_are_held` |
| watcher の停止確認（`_stop_target`・`_wait_stopped`） | group が空になるまで確認、だめなら `hold` | 既に満たす | 既存の `test_unstoppable_worker_is_held_and_left_running` |
| `run` の終了コード 3 と `final.json` の `next_step` | 保留、依存作業を始めない | 既に満たす | 既存のテスト（上の 2 件が終了コード 3 を確かめる） |
| watcher がポーリング中に消える（L-1 の V1・V4） | `final.json` 無し、`status` は先頭の生存で `true` | 既に満たす（先頭が生きている）。今回の変更で、先頭が終わった後も group で `true` | 再現 V1・V4、経路 A のテスト |
| watcher が停止確認中・終了後の待ち合わせ中に消える（経路 A） | `status` が `false` を返して見落とす | 修正する（`_status`） | 経路 A のテスト |
| watcher が `final.json` を書いた後（経路 B） | 同上 | 修正する（`_status`） | 経路 B のテスト |
| watcher が `declaration.json` を書く前に消える（SR-6） | `status` が終了コード 2 | 対象外。数ミリ秒の窓で、対象を終わったとは報告しない | — |
| `status.json` の `target.alive`（watcher が書いた最後の値） | watcher が消えると古いまま残る | 対象外。文書は `target_alive` を読むよう定めている。古い値は `true` の側に残る | — |
| `_stop` | watcher の識別情報が一致しなければ拒否し、対象にシグナルを送らない | 既に満たす | 再現 V1b・V4、既存の `test_stop_refuses_unrelated_and_caller_pids` |
| `SKILL.md`「task_watch で宣言・判定・停止する」の `watcher_alive: false` の箇条（全ランタイム共通） | 規則なし（`status` が `(false, true)` のときの扱いだけ） | 修正する（`final.json` が無ければ `status`、`target_alive` は group 全体、保留なら依存作業を始めない） | `git diff`、上のテスト |
| `monitoring-runtimes.md` の最初の対応表の pi の行 | 「戻れば解消」 | 修正する（`task_watch.py` で包んだ対象を除く） | 再現 V1・V4 |
| 同「task_watch による途中の判断と停止」の pi の行 | 戻った後に JSON か `final.json` を読む | 修正する（`timeout` は付けない。`final.json` が無ければ `status`） | 再現 V2・V3（`timeout` が watcher の後なら `final.json` が残る） |
| 同じ節の箇条 | 記述なし | 修正する（pi が SIGKILL を送る条件と結果） | pi 1.3.0 の `bash.js`・`shell.js`・各 mode の読み取り、再現 V1・V4 |
| 同 Claude Code・Devin の行 | 完了通知・`get_output` の戻りを watcher の終了として扱う | 既に満たす（`SKILL.md` の共通の規則で扱う）。Claude Code の TaskStop はツリー全体を止める（SR-5、自己レビューで実測）。Devin の `kill_shell` のシグナルは確かめていない | `SKILL.md` の規則がランタイムを限定していないこと |
| `.agents/execution-budget.md:46` のセッションディレクトリの片付け | `target_alive` が先頭だけなので、子が残っていても消せた | 既に満たす（`target_alive` の変更で、子が残る間は `true`。文書は変えない） | 経路 A・B のテストの `target_alive: true` |
| `AGENTS.md`「SDD 実行運用」の controller の箇条 | 停止を確認できなければ報告してターンを終えてよい | 既に満たす | 本文の読み取り |
| setsid で group を抜けた子孫 | 見えない | 対象外。`SKILL.md`・`task_watch.py` の docstring に「sandbox ではない」と既にある | — |
| group が空になった後の番号の再利用 | — | 対象外。別の group が同じ番号を使うと生存と誤るが、保留の側に倒れる（コードのコメントに記載） | — |

### 直し方の比較

- **採用: 条件を 1 か所で保つ** — 対象の生存の判定を `status` の 1 か所で group 全体に広げ、`SKILL.md` の規則と片付けはそれを読むだけにする。watcher が生きている間の判定（`residual_processes`）と、消えた後の判定の粒度がそろう
- 点の修正を続ける（文書で「`status` の後に `ps` で group を確かめる」と書く）: `SKILL.md`・`execution-budget.md` の両方で、エージェントが毎回 pgid を引いて手で調べる必要があり、片付けの経路で漏れやすい。採らない
- 保証を狭める（`final.json` が無いか `hold` なら、常に保留のままにする）: watcher が消えた後に対象が本当に終わっても、片付けに進む手段が無くなる。採らない
- コードで watcher の消失を防ぐ（`prctl(PR_SET_PDEATHSIG)` など）: 届くのは直接の子だけで group の子孫には届かない。採らない

### PR の Spec D-3（コードは移植元のまま）からの変更

PR の Spec D-3 は「判定・集計のロジックは変えない」としていた。今回の変更は判定（`decide`）・集計（進捗の読み取り）ではなく、`status` の出力（`target_alive` の意味と `target_group_pids` の追加）だが、移植元（usaturn/agent-workspace `84469b9`）とコードが分かれる。条件を構造で保つにはこの変更が要るので、D-3 の例外としてこの文書に記録し、PR 本文の「変えたのは…だけ」の記述を直す。移植元にも同じ穴がある（報告は利用者の判断）。

### pi の timeout の扱いの選び直し

最初の版は「`timeout` は付けないか、期限 + ポーリング + 停止確認（+ 60 秒）より長くする」とした。自己レビューで、`--stop none` では watcher が期限で戻らないので式が上限にならないこと（SR-2）、既定値を書いていないこと（SR-3）が分かった。期限は watcher が守るので、bash ツールの `timeout` は役に立たず、付ければ L-1 の経路を作るだけである。式を外し「付けない（既定の timeout は無い。期限は watcher が守る）」にした。付けた場合・中断した場合は、`final.json` が無いので `status` の規則で扱う。

### テスト

`AGENTS.md` の「テストの採用基準」の「コードを実行して安全条件を確かめる場合」に当たる。`status` の判定はコードで、watcher が消えた後に残存プロセスを見落とすと、依存作業や片付けが誤って進む。

- 既存の `test_processes_left_in_the_group_after_exit_are_held` に、`run` の後の `status` が `(0, False, True)` で `target_group_pids == residual_pids` であることを足した（経路 B）
- `test_status_sees_the_group_after_the_watcher_is_killed` を足した（経路 A）。fake worker の `orphan-child`（`sleep 30` を残して終わる）を watcher で起動し、`declaration.json` ができた直後に watcher を SIGKILL する。watcher は対象の終了の後に最大 2 秒待ってから `final.json` を書くので、kill の時点で `final.json` は無い。先頭が終わった後、`final.json` が無いこと、`status` が `(0, False, True)` で `target_group_pids` の全 PID が生存していることを確かめる。group を止めた後は `target_alive: false`・`target_group_pids == []` になる（誤って生存と言い続けないこと）

## 失敗時の検証

守る条件は中断・失敗したときの扱いなので、この節のとおりに確かめた。

1. 状態全体を比べる: 中断・停止の後に、state dir（`final.json` の有無と `decision`・`residual_pids`）、`status` の `watcher_alive`・`target_alive`・`target_group_pids`、対象の group の各プロセス（PID・pgid・状態）を確かめた（V1・V4・経路 A・B）。期待値は、その時点の実際の group のメンバー（`residual_pids`、`/proc` の生存）から取った
2. 副作用の順序: `status` は読むだけでシグナルを送らない。`stop` は watcher の識別情報を照合してからシグナルを送り、不一致なら何も送らない（V1b・V4）
3. 負例には異常を 1 つだけ入れる: 経路 A のテストは「watcher の SIGKILL」と「先頭の終了後に残る子」のうち、確かめたいガード（group の判定）に関わる異常を子の残存だけにした（watcher の SIGKILL は L-1 の前提で、先頭が生きている間は既存の判定でも `true` になる）。経路 B は子の残存だけ
4. ガードを外した対照: 修正後の内容を写した隔離 worktree で、`target_alive` を先頭だけの照合に戻した版を作り、`test_task_watch_process.py` を実行した。新しい負例 2 件（経路 A・B）がどちらも `assert (0, False, False) == (0, False, True)` で失敗し、他の 18 件は通った。対照の worktree は外して消した

## 確認の範囲

- 全文: `.agents/skills/monitoring-long-tasks/scripts/task_watch.py`（786 行）、`.agents/scripts/issue_budget.py`（283 行）、`.agents/skills/monitoring-long-tasks/SKILL.md`、`.agents/execution-budget.md`、`.agents/monitoring-runtimes.md`、`tests/fake_worker.py`、`tests/test_task_watch_process.py`、`evals/2026-10-17-issue-115.md`、PR の Spec、Plan の実行予算と完了の節、PR 本文とコメント
- 差分: `AGENTS.md`、`README.md`、`.github/workflows/ci.yml`、`pyproject.toml`、`docs/maatlog-poc-porting.md`
- 関連: pi 1.3.0 の `dist/core/tools/bash.js`・`dist/utils/shell.js`・各 mode、`.agents/skills/pr-review/SKILL.md` の bash ツールの `timeout` の規約、`git grep task_watch` の参照元すべて
- 自己確認 S-1（対応しない）: base の `main` は PR #129・#130 のマージで `61763dc` に進んだ。#130 は `AGENTS.md` に「コミットしないファイルの置き場所」を足し、`tmp/agents/<topic>.XXXXXX/` を `agent_tmp.py mkdir <topic>` で作るとした。この PR の `execution-budget.md` は同じ場所を `mktemp -d` で作るので、マージ後に作り方の書き方が 2 通りになる。`agent_tmp.py` は `root`・`mkdir` だけで削除の処理を持たず、`cleanup-workspace.bash` も `tmp/agents/` に触れないので、ledger が消える経路は無い。致命的ではない。テキストの merge（`git merge-tree`）は衝突しない。自己レビューの PR 全体の担当は、merge したツリーで `uv lock --check` と `.agents/scripts`・`monitoring-long-tasks` のテスト（76 passed）を確かめた（修正の前の版で）
- 自己確認で、ほかに PR が持ち込んだ致命的な欠陥は見つからなかった

## 検証

修正後の専用の worktree で実行した。

| コマンド | 結果 |
| --- | --- |
| `uv run --locked pytest -q .agents/skills/monitoring-long-tasks .agents/scripts` | 56 passed（24 秒。新しいテスト 1 件を含む） |
| 変更した 2 つの Python ファイルを `ast.parse(..., feature_version=(3, 12))` | OK（`requires-python = ">=3.12"`。このリポジトリに ruff は入っていない） |
| ガードを外した対照（上の「失敗時の検証」4） | 負例 2 件が失敗、18 件が通過 |
| `bash scripts/check-layout.sh` | PASS |
| `bash .devcontainer/run-tests.bash` | `PASS: 30 test(s)`（終了コード 0。`test-docs.bash`・`test-instructions.bash` を含む） |
| `uv run pytest tests/skills .agents/skills` | 515 passed（170 秒。最初の版の 514 件に新しいテスト 1 件） |

最初の版（文書だけ）でも `check-layout.sh` PASS・`run-tests.bash` 30/30・`uv run pytest tests/skills .agents/skills` 514 passed だった。

結論 1 なのでマージはしない。base の `61763dc` を merge したツリーでの検証はしていない（テキストの merge が衝突しないことだけを `git merge-tree` で確かめた）。private の create-reso-world は CI を使わない（`AGENTS.md` の「GitHub Actions」）。

## 自己レビュー

L-1 を最初に直した版（文書だけ）に対して、読み取り専用のサブエージェント 3 件で、反証・PR 全体・検証の検出力の観点を同時に 1 回だけ行った。

- 反証: 致命的 1 件（SR-1）。ほかに SR-3〜SR-6 を挙げた。timeout の式は `INT`・`TERM` なら上限を押さえていると確かめた。Claude Code の TaskStop の挙動を実測した（SR-5）
- PR 全体: 致命的な指摘なし。ほかに SR-7・SR-8 を挙げた。`execution-budget.md`・`SKILL.md` の例を実行し、base を merge したツリーでのテストも確かめた
- 検証の検出力: 致命的 2 件（SR-1 と同じ穴、SR-2）。再現が pi の実際の経路（bundle の `cli.js` と同じ実行部、拡張の差し替えなし、uv の起動では uv・watcher・bash が同じ pgid）を写していることを確かめた

SR-1 は L-1 で直した条件の再発なので、点の修正ではなく上の「守る条件の設計」で直した。自己レビュー後の修正（`task_watch.py` の `_status`、テスト 2 件、文書の書き直し）は再レビューしていない。

## PR の説明の既知の制限

- pi で `task_watch.py` を使うとき、bash ツールの呼び出しが timeout・中断・pi の終了で切られると、watcher だけが消えて対象は止まらない。修正後の文書と `status` は、この状態を検出して保留にするが、対象を止めることはできない。PR 本文に「既知の制限」の節を足し、条件と回避方法を書く
- PR 本文の「変えたのは Issue 番号の表記と `except` の括弧だけ」を、`status` の `target_alive` の変更を含む書き方に直す

## 所要時間

着手（2026-10-17 12:45Z ごろ）から Spec の記録（13:30Z ごろ）まで約 45 分。

- レビュー・PR の読み込み、共通 context と worktree の確認: 約 3 分
- 変更ファイルと pi 1.3.0 の実装の読み込み、L-1 の再現（V1〜V4）: 約 9 分
- 最初の修正（文書）、Spec の下書き、検証（`run-tests.bash`・pytest の待ち時間と重ねた）: 約 12 分
- 自己レビュー（サブエージェント 3 件、並行）: 約 10 分
- 設計の見直し（経路 B の再現、`_status` とテスト、ガードを外した対照）: 約 6 分
- 修正後の全体の検証と記録: 約 5 分
