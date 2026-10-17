# Issue #115: Issue の実行予算と monitoring-long-tasks の新しい版を取り入れる

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/115
- 検証した基準 HEAD: 移植先 `cd602e63e04e51616cd5043dd46b0cbefd8fc60e`（`origin/main`）、移植元 usaturn/agent-workspace `84469b9bb1c35febc6e94e0a8bfa92cf75e7f4c4`（`main`、2026-10-17）
- 状態: draft（文書の内容に対する利用者の明示承認は無い）
- 関連 Plan: `docs/superpowers/plans/2026-10-17-create-reso-world-issue115-budget-task-watch.md`
- 実行許可: 2026-10-17（JST）、利用者が「#115 に着手せよ。専用 worktree を作成し、途中で止めずに推奨案で PR を出せ」と指示した。推奨案での実装、隔離 worktree、commit、push、create-reso-world への PR の作成まで許可されている。マージは利用者が行う。下の判断は確認を取らずに決めたエージェントの判断である

## 意図

Issue 対応が長引いたときに、当初の計画の完遂や再試行そのものが目的にならないよう、予算と見直しの時点を先に決めて記録する仕組み（実行予算）と、起動前に宣言した worker を宣言どおりに止める仕組み（`task_watch.py`）を、usaturn/agent-workspace から取り入れる。PR #33 の 9 回の再レビューや resoloop PR #5 の打ち切りのような、長引く作業への対策にする。`AGENTS.md` の「SDD 実行運用」にある、事前宣言した PR レビュー委譲の打ち切りを、実際に動かせる仕組みにする。

## 確認した事実（2026-10-17）

- 移植元の対象（`.agents/execution-budget.md`、`.agents/scripts/issue_budget.py` とテスト、`.agents/skills/monitoring-long-tasks/`、`.agents/monitoring-runtimes.md`）は、Issue で照合した `3bc4769` から `84469b9` までに、`monitoring-runtimes.md` の「PR レビュー委譲の起動可否」の pi の行の 1 行だけが変わった。移植先はこの行を自分の書き方で持つので、影響しない
- 移植先の `monitoring-long-tasks` は英語の 49 行の版で、`verify.sh` に依存しない書き方（ログ名の末尾の PID、`EXIT=<code>` を書くコマンドならそれを、無ければ通知の終了コードを確かめる）になっている。止めてよい例外は、事前宣言した読み取り専用の PR レビュー委譲だけ
- 移植元の `SKILL.md` は日本語の 133 行の版で、手順 2〜5 に `verify.sh` 固有の手順がある。「事前宣言した打ち切り」「実質進捗」「task_watch」の節と、agent_runner への言及がある
- 移植先に `agent_tmp.py`・`tools/devenv`・agent_runner・PR 修正ループ（`loop.py`）は無い。ルートの `pyproject.toml` は `dependencies = []`、`testpaths = ["tests/skills", ".agents/skills"]`。`uv run python` は CPython 3.14.4 で、`requires-python = ">=3.12"`
- `issue_budget.py`・`task_watch.py` は pydantic だけに依存する。`task_watch.py` の `except OSError, ValueError:` の形（PEP 758）は Python 3.14 以降でしか構文として通らない
- `tmp/` は `.gitignore` で無視される。`.devcontainer/cleanup-workspace.bash` が自動で消すのは `/tmp` の `pr-review-*`・`review-fix-planning.*` だけで、リポジトリの `tmp/` には触れない
- `tests/scripts/test-docs.bash --refs` が `AGENTS.md`・`README.md` の backtick のパスの実在を確かめる
- テストの実行コマンド `uv run pytest tests/skills .agents/skills` は、`README.md`・`.devcontainer/README.md`・`.github/workflows/ci.yml`・`review-fix-planning` の本文にある

## 判断

### D-1 取り入れるファイルと判断

| 移植元 | 移植先 | 判断 |
| --- | --- | --- |
| `.agents/execution-budget.md` | 同じ | 適応（D-4〜D-6） |
| `.agents/scripts/issue_budget.py`・`.agents/scripts/tests/test_issue_budget.py` | 同じ | 移植（D-3） |
| `.agents/skills/monitoring-long-tasks/SKILL.md` | 同じ（置き換え） | 適応（D-7） |
| `.agents/skills/monitoring-long-tasks/scripts/task_watch.py`・`tests/fake_worker.py`・`tests/test_task_watch_core.py`・`tests/test_task_watch_process.py` | 同じ | 移植（D-3） |
| `.agents/skills/monitoring-long-tasks/evals/2026-10-10-issue-598.md` | なし | 持ち込まない。agent-workspace の記録（非公開のローカル証拠への参照を含む）なので、移植元の SHA でリンクする。この移植の行動比較は `evals/2026-10-17-issue-115.md` に新しく書く（D-11） |
| `.agents/monitoring-runtimes.md` の「task_watch による途中の判断と停止」と pi の行 | 同じファイル | 適応（D-8） |
| `.agents/monitoring-runtimes.md` の「agent-runner の同期実行と停止確認」、pi の行の `loop.py` の部分 | なし | #116 に回す |
| `.agents/scripts/agent_tmp.py` | なし | 持ち込まない（D-5） |
| `AGENTS.md` の「実行予算」の規則と、事前宣言した打ち切りの例外 | `AGENTS.md` の「SDD 実行運用」 | 適応（D-9） |

### D-2 変えないもの

- `pr-review`・`review-fix-planning` の本文。`pr-review` の time-budget は委譲の具体値（10 分・無進捗 5 分）を持ち、新しい `SKILL.md` はそれを参照するだけなので、書き方を合わせる変更は要らない
- `monitoring-runtimes.md` の「PR レビュー委譲の起動可否」の表。Claude Code の行は TBD のまま、pi の行は移植先の書き方のまま。`task_watch.py` は CLI のプロセスを包むもので、`Agent` ツールのサブエージェントの停止手段にはならない
- `.devcontainer/`（#114 だけが変える）。`.devcontainer/README.md` のテストのコマンドは、スキルのテストの説明としては今も正しいので変えない

### D-3 コードとテストは移植元のまま

判定・集計のロジックは変えない。変えるのは次の 2 点だけ。

- docstring・コメントの「Issue #598」を `usaturn/agent-workspace#598` にする。移植先の Issue 番号と取り違えないため
- `except A, B:` を `except (A, B):` にする。ルートの `requires-python = ">=3.12"` の範囲で構文として通るようにする

テストは移植元の判定関数のテストと、fake worker で実プロセスを起動するテストをそのまま持ち込む。`AGENTS.md` の「テストの採用基準」の「コードを実行してロジック・分岐・安全条件・入出力の解析を確かめる場合」に当たる。

### D-4 依存とテストの範囲

- ルートの `pyproject.toml` の `[project] dependencies` に `pydantic>=2.12,<3`（移植元と同じ範囲）を足し、`uv lock` で `uv.lock` を更新する。テストだけでなく運用で実行するスクリプトの依存なので、`dev` のグループには入れない
- `testpaths` に `.agents/scripts` を足す。`README.md` の「テスト」の節と `.github/workflows/ci.yml` の `skill-tests` のコマンドにも `.agents/scripts` を足す（CI は止めているが、記載を揃える）
- `.devcontainer/README.md` と `review-fix-planning` の本文のテストのコマンドは変えない（D-2）。持ち越し候補として PR 本文に書く

### D-5 ledger とセッションのディレクトリの置き場所

- 置き場所は `PARENT_ROOT` の `tmp/agents/<topic>.XXXXXX/`（`<topic>` は `issue-115` のような短い名前）。`mkdir -p "$PARENT_ROOT/tmp/agents"` の後に `mktemp -d "$PARENT_ROOT/tmp/agents/<topic>.XXXXXX"` で作る。`mktemp -d` は 0700 で作り、既存のディレクトリと重ならない
- 中身は `budget.jsonl`（ledger）、`watch-<name>/`（`task_watch.py` の state dir。watcher が作るので、起動前には作らない）、`<name>.progress.jsonl`・`<name>.result.json`（worker の進捗と結果）
- 作業用の worktree ではなく `PARENT_ROOT` に置く理由: worktree はマージ後に `repo-cleanup-after-merge` で消され、記録を転記する前に失われうる。`PARENT_ROOT` の `tmp/` は git の無視の対象で、`AGENTS.md` が既に定義している場所（`tmp/superpowers-review/` と同じ親）である
- `agent_tmp.py` は持ち込まない。移植先は `PARENT_ROOT` を `AGENTS.md` で定義しており、`mktemp -d` の 2 行で足りる。agent-workspace の submodule・リリース worktree の解決は移植先に無い
- スクリプトの実行は `uv run --project "$PARENT_ROOT" --locked python "$PARENT_ROOT/<スクリプトのパス>"` とする。`PARENT_ROOT` は `origin/main` に保つ checkout なので、マージ済みのスクリプトを使う

### D-6 片付けの責任

- セッションのディレクトリを作った controller が片付ける。Issue の作業を終える時（PR を作り、`issue_budget.py show` の要約と `final.json` の要点を Plan の「完了」・PR 本文・handoff に転記した後）に、各 watch の `status` で `watcher_alive` と `target_alive` が両方 `false` であることを確かめ、`rm -rf -- "${SESSION:?}"` で消す
- 停止を確認できない watch（`hold`、`target_alive: true`）があるときは消さない。対象・停止状態・残存パスを報告と handoff に書く
- 作業を引き継ぐときは、セッションのパスを handoff に書く。受け取った側が同じ ledger に追記し、最後に片付ける
- `cleanup-workspace.bash` の自動の掃除の対象には加えない。ledger は利用者を待つ間をはさんで数日残ることがあり、経過時間だけでは使用中かを判断できない

### D-7 monitoring-long-tasks の書き換え

移植元の 133 行の版を基にし、日本語にする。frontmatter の `description` は、起動の条件が変わらないので移植先の英語のまま残す。

- 手順 2〜5 は移植先の一般化した書き方を日本語にして使う。ログ名の末尾の PID の取り出し、`ps -p` と `/proc/<pid>/cwd` の同一性の確認、`EXIT=<code>` を書くコマンドならそれを、無ければ終了通知の終了コードを確かめる。`pgrep` のブラケットの例は `[.]devcontainer/run-tests[.]bash`。`verify.sh` 固有の手順は持ち込まない
- 手順 6 に、移植元の「確認した時刻と値を進捗の記録に残す」を足す
- 「事前宣言した打ち切り」の対象の例から agent_runner を外す（「専用の使い捨て領域（評価用の scratch など）だけに書く worker」）。対象にしない worker の例は「`bash .devcontainer/run-tests.bash`・テスト・lint などの検証コマンド」にする。打ち切りの対象から、検証のコマンド、共有の worktree に書く実装 worker、取り消せない外部操作を除く条件は移植元のまま
- 「task_watch で宣言・判定・停止する」の実行例は D-5 の入口にする。agent_runner を対象にするときの箇条は #116 に回す
- 「停止した後」の Issue 全体の扱いは `.agents/execution-budget.md` の checkpoint の判断に従う（移植元のまま）

### D-8 monitoring-runtimes.md の分け方

- 今回入れる: 「task_watch による途中の判断と停止」の節（Claude Code・Devin・pi・Cursor の 4 行と終了コードの箇条）。agent_runner の箇条は除く
- 今回入れる: 最初の対応表の pi の行のうち、`loop.py` に依存しない部分。完了は bash ツールの foreground 実行の終了コード、生存は既知の PID の `kill -0`、進捗と stall は実行中には確かめられないので、止める条件が要る対象は起動前に `task_watch.py` で宣言する
- #116 に回す: 最初の対応表の pi の行の `loop.py review`・`loop.py status`・`recover` の部分と、「agent-runner の同期実行と停止確認」の節
- 注記の「pi は監視ツール名が確認できるまで行を追加しない」は、「pi の行は bash ツールの foreground 実行と `task_watch.py` という、このリポジトリで確認済みの仕組みだけを書く」に変える

### D-9 AGENTS.md の「SDD 実行運用」

- 箇条を 1 つ足す: Plan に「実行予算」の節を設け、予算・phase の目安・worker の期限・再試行の上限・checkpoint・縮小などの候補を書く。時間の数え方と checkpoint での判断は `.agents/execution-budget.md` に従う
- controller の箇条の例外を、「事前宣言した読み取り専用の PR レビュー委譲」から「`monitoring-long-tasks` の「事前宣言した打ち切り」の対象」に広げる。宣言した条件で止めてよく、停止を確認できないときは対象・停止状態・残存パスを報告してターンを終えてよい
- 「エージェント運用」の節と他の節は変えない

### D-10 実行予算を必須にする範囲

- Plan を書く Issue 対応で、`superpowers:subagent-driven-development`・`superpowers:executing-plans`・`issue-to-pr`（#114）で実行するものと、評価・反復実行を含む run（移植元のまま）
- 30 分ほどで終わる単純な変更は、「実行予算」の節を全体の目安 1 行にしてよい（移植元のまま）。このときは ledger も省いてよい（エージェントの判断。小さな変更に記録の手間を足さないため）
- `review-fix-planning` の修正計画は対象にしない。本文を変えない方針（D-2）のため。必要になれば別の Issue で扱う

### D-11 スキルの文面の確かめ方

writing-skills の行動比較で確かめる。文言を照合するテストは書かない。

- 読み取り専用の general-purpose サブエージェントを 2 件起動する。無し（arm A）には移植先の `origin/main` の `SKILL.md` と `monitoring-runtimes.md`、あり（arm B）には改訂後の `SKILL.md`・`monitoring-runtimes.md`・`execution-budget.md` だけを scratch に写して渡す。各 1 回で、反復はしない
- 状況は 4 つ: A（pi で予約枠のある評価 worker を起動し、予約枠の中で新しい調査を続ける）、B（`bash .devcontainer/run-tests.bash` が生存したまま 20 分変化しない、利用者は急いでいる）、C（Claude Code で宣言した評価 worker に同じ失敗が 2 回）、D（Issue の実装で見積もり 3 時間を超え、同じ失敗が 2 回）
- 期待する結果（あり）: A は起動前に `task_watch.py` で宣言して foreground で起動し、予約枠の新規調査で止まる。B は止めない（検証のコマンドは宣言があっても止めない）。C は宣言どおり止めて方法を変える。D は利用者待ちを除いた能動時間で数え、checkpoint の判断を ledger に残す
- 結果と、比較で見つけた不足への対応は `evals/2026-10-17-issue-115.md` に記録する

### D-12 docs/maatlog-poc-porting.md

maatlog-poc からの移植の記録なので、判断と担当 Issue（#17）は変えない。スキル・`.claude/skills/`・`monitoring-runtimes.md`・`.agents/scripts/**` の 4 行の理由の末尾に、#115 で usaturn/agent-workspace の版を基に置き換えた（maatlog-poc の版ではない）ことを足す。

### D-13 PR と Issue

PR の本文は `Closes #115` にする。受け入れ条件は、テストとこの作業の Plan での ledger の記録で確かめられ、rebuild を要しない。

## 受け入れ条件との対応

| 受け入れ条件 | 確かめ方 |
| --- | --- |
| Plan に「実行予算」の節を書き、`start`・`mark`・`show` で能動時間・利用者を待った時間・失敗の回数を記録・集計できる | この作業の Plan に「実行予算」の節を書き、ledger を実際に使って `show` の結果を Plan の「完了」に転記する。`test_issue_budget.py` が集計と CLI を確かめる |
| `task_watch.py run` で起動した worker が、宣言した期限・無進捗・失敗の条件で止まり、`status` で状態を読める | `test_task_watch_process.py` の fake worker のテスト（期限・heartbeat のみ・繰り返しの失敗・安全の失敗・状態の読み取り） |
| 宣言の無い worker・検証のコマンドは、`task_watch.py` で止められない | `--stop none` の watcher はシグナルを送らず `hold` にする（fake worker の `undeclared`）。`stop` は自分が起動した watcher の識別情報に一致しない PID と caller を拒否する（無関係な PID・caller のテスト）。検証のコマンドを `--stop INT`・`TERM` で包まない規則は `SKILL.md` に書き、行動比較の状況 B で確かめる |

## 範囲外

- PR 修正ループ・agent_runner・pr-review の新しい版（#116）
- `cleanup-workspace.bash` への ledger の掃除の追加（D-6）
- `.devcontainer/` の変更（#114）
- 実モデルを長時間動かす `task_watch.py` の検証。テストは fake worker で行う
