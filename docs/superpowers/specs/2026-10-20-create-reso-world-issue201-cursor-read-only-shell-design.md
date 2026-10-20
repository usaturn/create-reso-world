# Issue #201: Cursor の `writes = false` の役割を `-f --sandbox disabled` で起動する

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/201（親・ボード・依存なし。関連 #116・#150）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue201-cursor-read-only-shell.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-201-cursor-review-sandbox`（branch `fix/issue-201-cursor-review-sandbox`、`origin/main` の `d29c93c` から作成）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-20（JST）、利用者が `/issue-to-pr #201` で着手を指示した。issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #201`）まで行う。マージはしない
  - 実機の確認（本物の Cursor CLI の起動）は、Issue の「検証の進め方」が書いた対象と回数（下の D-201-4）に限る
  - 下の判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- Plan の実装の担当: `implement_task.py check` の結果は `agents = ["self"]`・`fallback = []`。雛形 `.devcontainer/agent-runner.toml` の既定の適用であり（個人設定の該当の節はコメントだけ）、利用者の `--implement` の指定は無い

## 意図

runtime が `cursor` の担当を `writes = false` の役割（`inspect`・`self-review`・`fix-check`）に割り当てたときに、pr-review・review-verify の helper をシェルで実行できるようにする。今の adapter は `--mode ask` で起動するので、Cursor CLI がシェルのコマンドを拒否し、PR 修正ループでは利用枠を使った後でレビュアーが `rejected` になりうる。

`writes = false` は runner が依頼の冒頭に書く指示（「This is an instruction, not a sandbox.」）であり、Cursor・OS による書き込みの禁止ではない。この位置付けは変えない。

## 確認した事実（2026-10-20）

- `tools/agent_runner/adapters/cursor.py:157` は `argv += ["-f"] if context.role.writes else ["--mode", "ask"]`
- 単体のテスト（`tools/agent_runner/tests/adapters/cursor/test_cursor.py:64`）と偽の CLI（`fake_cli.py:14`）は `--mode ask` を前提にしている。runner を通すテスト（`test_integration.py`）の役割は `inspect`（`writes = false`）だけで、担当の名前は `cursor-agent` 1 つ、fallback は無い
- 雛形の `inspect`・`self-review`・`fix-check` はどれも `writes = false`、`implement` は `writes = true`。`cursor`（model `auto`）と `cursor-grok47`（model `grok-4.7-xhigh`）が定義されている。既定の割り当てに cursor の担当は無い
- runner は担当の名前によらず、役割の `writes` を adapter に渡す（`tools/agent_runner/runner.py:437-446`）。fallback は、一次担当が `response_failed` などで止まったときに、同じ役割で起動される（`runner.py:554-565`）
- `run_roles.py` と loop の起動前の検査は `READ_ONLY_SANDBOX_RUNTIMES = {"codex"}` だけを拒否する。cursor の担当は拒否されない
- インストール済みの CLI は `2026.10.19-6bbf2c4`（`agent --version`）、ログイン済み。`agent --help` は `-f, --force: Force allow commands unless explicitly denied`、`--sandbox <mode>: Explicitly enable or disable sandbox mode (overrides config)`、`--mode`: `plan`・`ask` はどちらも read-only と説明する
- 利用者の `~/.cursor/cli-config.json` は `sandbox.mode = "disabled"`、`approvalMode = "allowlist"`、`permissions.allow = ["Shell(ls)"]`、`permissions.deny = []`。このため、この環境の実機の確認は、`--sandbox disabled` が無くても sandbox が掛からない設定で動く。sandbox の範囲の観測（worktree の外・共有 `.git`・HOME の下への書き込みが拒否される）は参照 PR（usaturn/agent-workspace#753）の記録であり、この run では再観測しない
- 参照 PR のテストのコメントは、`-f` と sandbox の相互作用の観測版を `2026.10.16` と書くが、Issue の調査で `2026.10.18-ea085cb` が正しいとされた。この版の誤記は写さない

## 設計

1. `prepare` の分岐を `argv += ["-f"] if context.role.writes else ["-f", "--sandbox", "disabled"]` にする。担当の名前・モデルで分けない。コメントで、`--mode ask`・`plan` がシェルを拒否すること、Cursor の sandbox が helper の書き込み先を拒否すること、`-f` が sandbox を外す挙動は文書に無いので明示することを書く
2. テストを、起動処理を実行して確かめる形で直す（D-201-2）
3. `tools/agent_runner/runtimes/cursor.rst` と `.devcontainer/README.md` を、実際の起動と一致させる（D-201-3）
4. 実機で、runner を通した読み取り・シェルの確認と、この PR のレビューを行い、結果を `cursor.rst` と PR 本文に記録する（D-201-4・D-201-5）

## 受け入れ条件

| # | 条件（Issue の受け入れ条件との対応） | 確かめ方 |
| --- | --- | --- |
| C1 | 追加の起動引数が無いとき、`writes = false` の `prepare` は `-f` と `--sandbox disabled` を含み、`--mode`・`--plan` を含まない（Issue の 1） | 単体のテスト |
| C2 | `writes = true` の `prepare` は `-f` だけを足し、`--sandbox`・`--mode` を足さない。stdin の prompt、`--trust`、`stream-json`、model と effort、利用者の追加引数の扱いは変わらない（Issue の 2） | 単体のテスト（既存のテストを含む） |
| C3 | 任意の名前の cursor の担当と、fallback で起動された cursor の担当が、`inspect`・`self-review`・`fix-check` の名前の `writes = false` の役割で、C1 の起動になる（Issue の 3） | 偽の CLI で runner を通すテスト |
| C4 | runner を通した、使い捨てのリポジトリの読み取りとシェルの操作が、`cursor`・`cursor-grok47` で 1 回ずつ `success` になる（Issue の 4 の前半） | 実機（R1） |
| C5 | 修正した adapter で、`cursor-grok47` がこの PR をレビューし、pr-review の `prepare → complete → cleanup` を終え、loop が `accepted` にする（Issue の 4 の後半） | 実機（R2） |
| C6 | 実機の記録（CLI の版、起動形、担当、観測したモデル、対象 HEAD、終了・停止の確認、レビューの成果、cleanup、`outside_changes`、残した資源）を `cursor.rst` と PR 本文に書き、参照 PR の記録と区別し、実機で確かめていない役割（`self-review`・`fix-check`）を未検証と書く（Issue の 5） | 差分の確認 |
| C7 | `writes = true` の起動と既定の割り当てを変えず、文書が実際の起動と一致する。文書の文言・版・モデル名を写したテストを足さない（Issue の 6） | `git diff` の確認、rstcheck |
| C8 | `uv run pytest tools/agent_runner/tests/adapters/cursor`、runner のテスト、README の「テスト」の入口が通る | 実行して終了コードを見る |

## 除外範囲

- 既定のレビュアー、個人設定、モデル・effort、`writes = true` の起動、Codex・DSH の制限、loop・`run_roles.py`・dispatch の判定は変えない
- cursor を起動前の拒否（`READ_ONLY_SANDBOX_RUNTIMES`）に加えない
- 利用者の `~/.cursor/cli-config.json`（`sandbox`・`approvalMode`・`permissions`）を書き換えない
- grok-build は扱わない（導入・復活・動作確認をしない）
- 実際の `self-review`・`fix-check` の 1 回枠を、配線の確認のために使わない
- R2 のレビューの後に、計画・修正・マージへ進まない

## 決定記録

### D-201-1 起動の分岐

- 選択した案: `writes = false` は `-f --sandbox disabled`、`writes = true` は今のまま `-f`。runtime が `cursor` の全担当で共通にする
- 検討した別案: (a) `--mode plan` に替える。(b) `-f` だけにして、`-f` が sandbox を外す挙動に任せる。(c) cursor を起動前の拒否に加える
- 選択理由: (a) も read-only でシェルを拒否する（`agent --help`）。(b) は文書に無い挙動で、版によって変わりうる。(c) はレビュアーとして使えなくなる。Issue の「採用する解決方針」と参照 PR の最終版に合わせる
- 委任指示: Issue の「採用する解決方針」

### D-201-2 テスト

- 選択した案:
  - `test_cursor.py`: `writes = false` の起動のテストを足し（C1）、既存の読み取りの起動のテストから `--mode ask` の検査を外す。`writes = true` のテストに `--sandbox` が無いことと `-f` が 1 つであることを足す（C2）
  - 偽の CLI: `--mode ask` の検査を外し、`--echo-argv` を受け取ったら、受け取った引数を result の JSON に入れて返す
  - `test_integration.py`: 1 つの workflow に `inspect`・`self-review`・`fix-check`（どれも `writes = false`）を置き、任意の名前の担当、失敗する一次担当の後の fallback を割り当てて runner を 1 回実行し、各担当が受け取った引数が C1 の起動であることを確かめる（C3）
- 検討した別案: `run_roles.py`・loop を偽の CLI で通す。雛形 `.devcontainer/agent-runner.toml` の役割の定義を読んでテストに使う
- 選択理由: adapter は役割の `writes` だけで分岐し、runner は担当の名前・一次担当か fallback かによらず役割を渡す。runner を通すテストで、名前・fallback・役割の名前の経路を確かめられる。`run_roles.py`・loop を通すと PR・レビューディレクトリの準備が大きく、確かめる分岐は増えない。雛形の役割を読むと、運用で変わる設定値をテストに写すことになる（AGENTS.md の「テストの採用基準」）。起動の引数は、利用者の CLI の安全な操作範囲を決める固定値なので、テストに書いてよい。防ぐ誤りと理由をテストのコメントに書き、観測の版はテストに写さず `cursor.rst` を参照する
- 委任指示: issue-to-pr の推奨案での委任（Issue の受け入れ条件 1〜3）

### D-201-3 文書

- 選択した案:
  - `tools/agent_runner/runtimes/cursor.rst`: 起動の形式と各引数の理由、`--mode ask`・`plan` を使わない理由、`--sandbox disabled` を明示する理由（参照 PR の観測を出所として区別して書く）、`writes = false` の意味、既知の制限、この環境の実機の記録を、今の節の構成（概要・起動と入力・応答と失敗の判定・観測する identity・検証と出所）に合わせて書く
  - `.devcontainer/README.md` の「非対話エージェントのランナー（agent-runner）」に、cursor の担当の `writes = false` の起動と制約を 1 段落で足す
- 検討した別案: 参照 PR の `cursor.rst` の節（sandbox の観測の表など）をそのまま写す
- 選択理由: 参照 PR の文書は節の構成が違い、この環境で観測していない表を写すと、移植先の成功実績と区別しにくい。出所の文書・commit を示して要点だけを書く
- 委任指示: Issue の「変更範囲」

### D-201-4 実機の確認の対象・回数・方法

- 選択した案:
  - R1: runner（この branch の `tools.agent_runner`）を、一時の個人設定（雛形に読み取りの確認用の workflow を 1 つ足すだけ）で起動し、`PARENT_ROOT/tmp/agents/issue-201.*` の下の使い捨ての git リポジトリに対して、ファイルの読み取りとシェルの操作（`date -u +%Y`・`uv --version`・`mktemp -d` で作ったディレクトリへの書き込み・読み取り・削除）を依頼する。`cursor`・`cursor-grok47` で 1 回ずつ（計 2 回、`inspect` の役割）
  - R2: PR の作成の後に、この branch の `loop.py` で `start <PR の URL> --assign inspect=cursor-grok47` → `cycle-begin` → `review` を実行する（1 回）。`accepted` と、pr-review の `prepare → complete → cleanup` の完了を確かめたら、計画に進まず `finish --abort` で終える
  - 再試行: 同じ原因の失敗は 1 回まで（Plan の「実行予算」）。それでも失敗したら、未達として記録して止まる
- 検討した別案: R1 の読み取りとシェルを別の依頼にする（参照 PR は 2 回ずつ）。R2 を親の main checkout の `loop.py` で実行する
- 選択理由: Issue は「各 1 回」としているので、1 回の依頼に読み取りとシェルをまとめる。main の `loop.py` は main の adapter（`--mode ask`）で runner を起動するので、修正した adapter を確かめられない。pr-review-fix-loop の SKILL.md は feature worktree の `loop.py` を使わないとするが、これは PR を修正するループのための規則で、R2 は Issue が求める確認のための run であり、計画・修正・マージへ進まない。参照 PR も PR の版の `loop.py` で確かめた
- 委任指示: Issue の「検証の進め方」（対象・回数）。方法は issue-to-pr の推奨案での委任

### D-201-5 公開と実機の記録の順序

- 選択した案: R1 を PR の作成の前に行う。R2 は PR が要るので、PR を作った後に行い、結果を `cursor.rst` に足した commit を push の前の検査を通して push し、PR 本文を更新する
- 検討した別案: R2 も済ませてから PR を作る（PR が無いと loop を起動できないので不可能）。下書きの PR にする
- 選択理由: R2 はこの PR を対象にするので、PR が先に要る。R2 がレビューする HEAD と、記録を足した後の HEAD は違う。記録の commit は文書だけで、PR 本文と `cursor.rst` に、レビューした HEAD を書く
- 委任指示: issue-to-pr の推奨案での委任

### D-201-6 R2 の `--abort` の分類

- 選択した案: `finish --abort "external: #201 の実機確認（レビューの受け付けまで）のための run なので、計画・修正・マージへ進まない"`
- 検討した別案: `environment`・`permission`
- 選択理由: helper の `--abort` は `permission|environment|external` のどれかを求める。止める理由は環境・権限の障害ではなく、ループの外の要件（Issue の指示）なので `external` にする
- 委任指示: issue-to-pr の推奨案での委任

## 既知の制限（PR 本文にも書く）

- `writes = false` は runner の指示であり、cursor の担当は `-f` でファイルを書き換えられる。ほかの checkout の変更は runner の `outside_changes`・`checkout_audit` が事後に報告するだけで、任意のパスへの書き込みは防がない
- 利用者が `permissions.deny` に書いたコマンド（`uv`・`git` など）は `-f` でも拒否され、そのときレビューは完了しない
- この環境の利用者の設定は `sandbox.mode = "disabled"` なので、実機の確認は `--sandbox disabled` の効果を独立には確かめない。sandbox の範囲は参照 PR の観測による
- 実機で確かめる役割は `inspect` だけで、`self-review`・`fix-check` は偽の CLI のテストだけ
