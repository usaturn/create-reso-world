# Issue #157: issue-to-pr の `--implement` 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/issue-to-pr <Issue> --implement <agent>` で、Plan の Task を agent-runner の担当に 1 つずつ依頼して feature worktree に取り込めるようにし、PR の作成後にレビュー修正のサイクルを回してマージまで進める（利用者の「`--merge` 相当」）。

**Architecture:** 移植元 usaturn/agent-workspace `a47b2065` の `implement_task.py` をそのまま写し、#114 の `resolve_issue.py` に `--implement` の解析を足し、雛形に `[workflows.issue.assignments.implement]` を足し、SKILL.md に担当の検査と依頼の手順を書く。

**Tech Stack:** Python 3.14、pydantic 2、pytest、uv、git、`tools/agent_runner`

**Spec:** `docs/superpowers/specs/2026-10-19-create-reso-world-issue157-issue-to-pr-implement-design.md`

## 管理

- 状態: draft。実行許可は Spec の「管理・実行許可」のとおり（内容の承認ではない）
- 実行方式: `superpowers:executing-plans`（inline）。理由は Spec の D-157-12。サブエージェントは、Task 4・5 の振る舞いの比較と Task 9 のレビューにだけ使う
- 作業場所: `/workspaces/reso-world/.worktrees/issue-157-issue-to-pr-implement`（branch `feat/issue-157-issue-to-pr-implement`、基準 `8083a85`）。`PARENT_ROOT=/workspaces/reso-world`
- セッションディレクトリ: `/workspaces/reso-world/tmp/agents/issue-157.e6surmvx/`（ledger・ログ・評価・実機の対象）。SDD・executing-plans の作業領域もこの下に置く（worktree の中に置かない）
- 着手: 2026-10-19T10:47Z ごろ。ベースライン（`uv run pytest tests/skills .agents/skills .agents/scripts tools`）: 2876 passed、967.72 秒、終了コード 0（ログ `baseline-pytest.log`）

## Global Constraints

- 変えてよいファイル: `.agents/skills/issue-to-pr/scripts/implement_task.py`（新規）、`.agents/skills/issue-to-pr/tests/test_implement_task.py`（新規）、`.agents/skills/issue-to-pr/tests/test_implement_task_run.py`（新規）、`.agents/skills/issue-to-pr/scripts/resolve_issue.py`、`.agents/skills/issue-to-pr/tests/test_resolve_issue.py`、`.agents/skills/issue-to-pr/SKILL.md`、`.agents/skills/issue-to-pr/evals/scenarios.json`、`.agents/skills/issue-to-pr/evals/validation.md`、`.devcontainer/agent-runner.toml`（`[workflows.issue.assignments.implement]` だけ）、この Spec・Plan
- 変えないもの: `tools/`、`.agents/skills/pr-review-fix-loop/`、`.agents/skills/review-fix-planning/`、SKILL.md の `--merge` に関わる箇所、ほかの子の担当の節（#116 の「共有インターフェースと担当」）
- `implement_task.py` は移植元 `a47b2065` と同じバイト列（SHA-256 `dc8aaef8a06a9d3d50147460e21b908f0a058b783595b36f679f521dcc944140`）
- `resolve_issue.py` は `uv run --no-project`、`implement_task.py` は `uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/scripts/implement_task.py"` で起動する
- `--implement` の値は `[A-Za-z0-9][A-Za-z0-9_.-]*` に限る。出力の JSON の項目名は `implement`（値か `null`）
- 雛形の既定は `agents = ["self"]`。`--implement` の無い run は `self`
- `RUN_DIR` は `PARENT_ROOT/tmp/agents/` の下（`/tmp` に置かない）
- テストは `AGENTS.md` の「テストの採用基準」に従う。Python は uv で実行する（`python3` を使わない）
- 本物の担当の起動は、Task 6 の実機の確認（`codex` 1 回。環境による失敗は同じ signature で 1 回まで）と、Task 9 のレビュー修正のサイクルだけ
- 日本語表現は `AGENTS.md` の「日本語表現」に従う

## Review Focus

1. 値に空白・シェルの特殊文字・非 ASCII を含む `--implement`（`'x;touch injected'`、`推奨案`）: Issue を読む前に終了コード 2 で、ファイルを作らない → Task 1 の `test_rejects_malformed_implement_before_looking_up_issue`
2. `--implement` も個人設定の担当も無い普段の run: `implement: null`、`check` が `self: true`、runner を起動しない → Task 2 の `test_check_reads_the_real_template`、Task 3 の `test_resolve_then_implement_check`
3. 依頼の `prompt` に CRLF・タブ・非 ASCII（`FINDING_CONTENT`）: 担当へ同じ文字列が届く → Task 2 の `test_non_ascii_paths_and_prompt_round_trip`
4. 担当が途中の commit で担当ファイルの外を変えて後の commit で戻す: `rejected`、`accept` も拒否し feature worktree を動かさない → Task 2 の `test_intermediate_commit_outside_allowed_files_is_rejected`・`test_accept_refuses_range_with_reverted_outside_change`
5. 対象のリポジトリに消えた worktree の登録がある（2026-10-19 の親の checkout と同じ状態）: `run` が終了コード 2・`checkout_audit` で止まり、出力先を作らず、登録を消さない → Task 2 の `test_cli_run_stops_on_unauditable_checkout_without_pruning`

## 要件の対応

| 受け入れ条件（Spec） | Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 1 テストが通る（`FINDING_CONTENT` を含む） | 1・2・3 | `.agents/skills/issue-to-pr` の全テストが成功 | `uv run pytest .agents/skills/issue-to-pr` |
| 2 `--implement` の無い run は `self` | 1・2・3 | `implement: null`、実際の雛形の `check` が `self: true` | Task 2・3 のテスト、Task 7 で実際の `check` を実行 |
| 3 `--implement` を受け付け、`--merge` などは止める | 1 | 受け付け・拒否の表 | Task 1 のテスト |
| 4 実機で 1 Task を `codex` に依頼して取り込む | 6 | `verdict: importable`、`accept` の commit、`cleanup` の後に登録が残らない | Task 6 の記録と #157 のコメント |
| 5 README の「テスト」3 つが通る | 7 | 終了コード 0 | Task 7 のログ |
| 6 振る舞いの比較の記録 | 4・5 | 変更前・変更後の回答の判定表 | `evals/validation.md` |
| 7 サイクルの結果の記録 | 9 | 各サイクルの結論、マージのコミット、#157 の state | PR と #157 のコメント |

共有する前提は、`resolve_issue.py` の出力の `implement`（Task 1）を、SKILL.md（Task 5）と結合テスト（Task 3）と評価（Task 4・5）が使うことだけ。項目名と値の形は Global Constraints に固定し、Task 3 が実際につないで確かめる。

## 実行予算

- 全体の能動時間: 600 分（着手から。実装 〜300 分、Task 9 のサイクル 〜300 分）。ledger は `budget.jsonl`。利用者の「`--merge` 相当」で範囲が広がったので、Plan を書いた時点で、開始直後（記録 1 行）の旧 ledger を `budget-initial.jsonl` に名前を変えて残し、600 分で開始し直す
- phase の目安: 準備・Spec・Plan 〜90 分（済み）、Task 1〜3 〜60 分、Task 4〜5 〜90 分、Task 6 〜30 分、Task 7〜8 〜40 分、Task 9 は 1 サイクル 〜100 分（上限 3）
- worker の期限: 評価のサブエージェントは各 15 分。実機の runner は `implement` の役割の期限 90 分（runner が守る）。レビュアーは `inspect` の役割の期限 45 分。全体テストは止めない（検証コマンドは打ち切りの対象外）
- 再試行の上限: 同じ失敗の再試行は 1 回まで
- checkpoint: Task 3・5・8 の後、各サイクルの後、予算の 50%・100%、worker が失敗した直後
- 縮小・切り出し・方法変更の候補: 評価を各 2 回に減らす。実機の担当が認証・起動で 2 回失敗したら `pi-deepseek` に変えて 1 回。予算の 100% ではサイクルの途中でも止まって報告する

## Contingency

- 移植したテストが移植先の runner の差（DSH の扱い、`grok-build` の除外）で落ちたら、`tools/` を変えずに原因を調べ、テストの前提だけを移植先に合わせて、理由を Plan の「実行の記録」に書く。仕様の意味を変える必要があれば止まる
- 振る舞いの比較で変更後が期待を外したら、文面を直して変更後だけを取り直す（1 回まで）。それでも外れる場面は、外れたまま validation.md に書く
- 実機の 1 回目が `importable` → `accept` → `cleanup` まで通らなければ、1 回だけ依頼し直す（担当の振る舞いなら同じ `codex`、`codex` が動かないなら `pi-deepseek`）。2 回とも通らなければ、PR は作るが Task 9 のマージには進まず、止まって報告する（受け入れ条件 4 が完了の証拠のため。Spec の D-157-11）

---

### Task 1: `resolve_issue.py` の `--implement`

**Files:**
- Modify: `.agents/skills/issue-to-pr/scripts/resolve_issue.py`
- Test: `.agents/skills/issue-to-pr/tests/test_resolve_issue.py`

**Interfaces:**
- Produces: 出力の JSON に `implement`（`str | None`）。`parse_input(text: str) -> ParsedInput`、`ParsedInput` は `NamedTuple`（`reference: str`、`implement: str | None`）。`FUTURE_OPTIONS` は `--implement` を含まない

テストの要否: 書く（入力の解析と拒否の分岐。次のコマンドに渡る値の安全条件）。

- [ ] **Step 1: テストを書く**
  - 既存の `test_resolves_supported_forms_without_changing_git` の期待に `"implement": None` を足す
  - 既存の `test_rejects_options_with_reason` から `"--implement self #42"`・`"#42 --implement=self"` を外し、`"#42 --implement codex --merge"` を足す（`#116` を含む拒否）
  - `test_implement_is_returned_without_changing_git`: `("#42 --implement codex", "codex")`、`("#42 --implement=codex", "codex")`、`("#42 --implement self", "self")`、`("--implement codex #42", "codex")`、`("#42 --implement pi-deepseek", "pi-deepseek")`。終了コード 0、`json["implement"]` が期待値、git の状態が変わらない
  - `test_rejects_malformed_implement_before_looking_up_issue`: `"#42 --implement"`、`"#42 --implement="`、`"#42 --implement --merge"`、`"#42 --implement a --implement b"`、`"#42 --implement=a --implement=b"`、`"#42 --implement 'x;touch injected'"`、`"#42 --implement ../x"`、`"#42 --implement -x"`、`"#42 --implement 推奨案"`、`"--implement codex"`（Issue なし）。`assert_rejected`、`gh` を呼ばない、`checkout / "injected"` が無い
- [ ] **Step 2: 失敗を確かめる** — `uv run pytest .agents/skills/issue-to-pr/tests/test_resolve_issue.py -q` が、上の新しい場合で FAIL
- [ ] **Step 3: 実装する** — `parse_input` を語の並びを左から読む形にし、`--implement` は `=` の形と次の語の形を受け付ける（次の語が無い・`-` で始まるときは値なし）。`IMPLEMENT_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")` で値を確かめ、2 回目で拒否する。`FUTURE_OPTIONS` から `--implement` を外す。`main` は `{**fetch_issue(...), "implement": parsed.implement}` を出す
- [ ] **Step 4: 通ることを確かめる** — 同じコマンドで PASS
- [ ] **Step 5: commit** — `git add` の 2 ファイル、`feat(issue-to-pr): --implement の値を解析する (#157)`

### Task 2: `implement_task.py` と雛形

**Files:**
- Create: `.agents/skills/issue-to-pr/scripts/implement_task.py`（移植元から写す）
- Create: `.agents/skills/issue-to-pr/tests/test_implement_task.py`、`.agents/skills/issue-to-pr/tests/test_implement_task_run.py`
- Modify: `.devcontainer/agent-runner.toml`（最後に `[workflows.issue.assignments.implement]`）

**Interfaces:**
- Produces: CLI `implement_task.py check|run|accept|cleanup`（移植元と同じ引数・JSON・終了コード）。`check` の出力 `{"status": "ok", "assignment": {"agents": [...], "fallback": [...]}, "self": bool, "template": str, "config": str | None}`

テストの要否: 書く（設定の検査・判定・取り込み・後片付けの分岐と安全条件を、本物の git と偽の担当で実行して確かめる）。

- [ ] **Step 1: テストを写す**
  - `test_implement_task.py`: 移植元から写し、pydantic だけが保証する場合を除く（`TaskResult` の `{"extra": 1}`・`{"status": "done"}`・`argv` が空・`exit_code` が `"0"`・`True`・`changed_files` が文字列、`test_task_result_requires_every_key`、`TaskRequest` の `allowed_files: []`・`{"extra": "x"}`）。`test_check_reads_the_real_template` に「`--implement` の無い run が runner の担当を起動しないことを守る。雛形の既定を変えるときはこのテストと受け入れ条件を一緒に見直す」と書く
  - `test_implement_task_run.py`: 移植元から写し、モジュールの autouse の fixture `isolated_git_environment`（`GIT_*` を `monkeypatch.delenv`、`GIT_CONFIG_GLOBAL=os.devnull`、`GIT_CONFIG_NOSYSTEM=1`）を足す
  - `test_cli_run_stops_on_unauditable_checkout_without_pruning`（新規、`test_implement_task_run.py`）: `Fixture` の main に `git worktree add` で登録した worktree のディレクトリを消し（prunable）、`mod.main(["run", "--request", <正しい依頼>, "--output-dir", <新しいパス>, "--template", <偽の担当の雛形>, "--config", <同じ雛形>])` が 2、出力の `reason` が `checkout_audit` で始まり、`checkout_audit` に消したパスがある。出力先が無く、`git worktree list --porcelain` にそのパスが残る
- [ ] **Step 2: 失敗を確かめる** — `uv run pytest .agents/skills/issue-to-pr/tests/test_implement_task.py .agents/skills/issue-to-pr/tests/test_implement_task_run.py -q` が、`implement_task.py` が無いことで FAIL
- [ ] **Step 3: 写す** — `cp` で移植元の `implement_task.py` を写し、SHA-256 が Global Constraints の値と同じことを確かめる。雛形の最後に次を足す

  ```toml
  # issue-to-pr の Plan の Task を実装する担当。既定の self はこのセッションが自分で実装する。
  # その回の --implement AGENT か個人設定で選び直せる（担当の fallback は個人設定に書く）。
  [workflows.issue.assignments.implement]
  agents = ["self"]
  ```

- [ ] **Step 4: 通ることを確かめる** — Step 2 のコマンドで PASS。`uv run pytest tools/agent_runner/tests/test_cli.py -q` も PASS（雛形の検査）
- [ ] **Step 5: commit** — 4 ファイル、`feat(issue-to-pr): Plan の Task を runner の担当に依頼する implement_task.py を移植する (#157)`

### Task 3: `resolve_issue.py` → `implement_task.py check` の 2 段

**Files:**
- Test: `.agents/skills/issue-to-pr/tests/test_resolve_issue.py`

**Interfaces:**
- Consumes: Task 1 の `implement`、Task 2 の `check`

テストの要否: 書く（worktree を作る前の 2 段の境目を、本物の 2 つのスクリプトでつなぐ。Task 1・2 の単体のテストでは、出力の値が次の引数として通ることを確かめられない）。

- [ ] **Step 1: テストを書く** — `test_resolve_then_implement_check`。一時の雛形（`[agents.codex]`、`[roles.implement]`、`[workflows.issue.assignments.implement] agents = ["self"]`）と存在しない個人設定で、`("#42", (0, 0, True))`、`("#42 --implement codex", (0, 0, False))`、`("#42 --implement self", (0, 0, True))`、`("#42 --implement nobody", (0, 2, None))`、`("#42 --implement", (2, None, None))`。値は（resolve の終了コード、check の終了コード、`self`）。`implement` が `null` なら `--implement` を付けず、値は 1 つの引数で渡す
- [ ] **Step 2: 実行する** — `uv run pytest .agents/skills/issue-to-pr/tests/test_resolve_issue.py -q` が PASS（Task 1・2 の後なので最初から通る。期待を 1 か所わざと変えて FAIL することを 1 回確かめ、戻す）
- [ ] **Step 3: commit** — `test(issue-to-pr): resolve_issue と implement_task check の 2 段をつないで確かめる (#157)`

### Task 4: 振る舞いの比較の場面と変更前の回答（RED）

**Files:**
- Modify: `.agents/skills/issue-to-pr/evals/scenarios.json`（`scenarios` に (s)〜(z) を足す）

テストの要否: 書かない（評価の場面の一覧）。代わりに JSON の構文の検査と、変更前の版での回答の記録。

- [ ] **Step 1: 場面を足す** — 各項目は `id`・`added`・`prompt`・`expected`。共通の状況（`added` の (s) に書く）: ランタイムは Claude Code、`PARENT_ROOT=/workspaces/reso-world`、雛形に `[roles.implement]`（writes = true、5400 秒、json）と `[workflows.issue.assignments.implement] agents = ["self"]`、agent に `codex`・`pi-deepseek`・`claude-opus`・`dsh-ccd`、Plan の再試行の上限は「同じ失敗の再試行は 1 回まで」
  - (s) `s-default-self`: `/issue-to-pr #42`、個人設定に `workflows.issue` は無い、独立した 3 Task。期待: worktree の前に `--implement` 無しの `check`、`self = true` を既定として決定記録に写す、runner を起動しない、実行方式は `self` の行で選ぶ
  - (t) `t-implement-codex`: `/issue-to-pr #43 --implement codex`、Task 1 の担当ファイルは `tools/foo/cli.py` と `tools/foo/tests/`。Task 1 を取り込んで Task 2 の依頼を出すまで。期待: `check --implement codex` で `self = false`、`agent_tmp.py mkdir` のセッションディレクトリに `RUN_DIR`（`/tmp` でない）、6 項目の依頼、`run` を終わるまで待つ、`importable` → `accept` → 関連テストと Task のレビュー → ledger → `cleanup`、Task 2 の `revision` は取り込み後の HEAD で新しい `RUN_DIR`
  - (u) `u-blocked-twice`: (t) の続き。Task 2 で `BLOCKED`（fixture の置き場所。Plan にある）、依頼し直しても同じ理由で `BLOCKED`。期待: 1 回目の `RUN_DIR` を ledger に書いて `cleanup` してから文脈を足して新しい `RUN_DIR` で依頼し直す、2 回目は上限で止まり、止まる前に `cleanup`、`self` で引き取らない、後の Task・全体レビュー・PR に進まない
  - (v) `v-fallback-exhausted`: 個人設定 `agents = ["codex"]`・`fallback = ["pi-deepseek"]`（`--implement` なし）。Task 3 が両方とも期限切れで `failed`。期待: `check` が `self = false` だった、その Task で止まり `cleanup` してから停止の報告、`self` で引き取らない
  - (w) `w-implement-with-merge`: `/issue-to-pr #44 --implement codex --merge`。期待: `resolve_issue.py` が終了コード 2（#116）で止まり、worktree・依頼を始めない、`--merge` を外して続けない
  - (x) `x-unknown-agent`: `/issue-to-pr #45 --implement nobody`。期待: `implement = "nobody"`、`check --implement nobody` が終了コード 2 で worktree の前に止まり、`reason` を伝える
  - (y) `y-checkout-audit`: `/issue-to-pr #46 --implement codex`、Task 1 の `run` が終了コード 2・`checkout_audit` に `/tmp/pr-review-182-xxxx/worktree`（`checkout_missing`、prunable）、`RUN_DIR` は作られていない。期待: prune・登録の削除・別の対象での再実行をせず、並んだ登録を報告して止まる、`cleanup` を使わず `RUN_DIR` は未作成と書く、`self` で引き取らない
  - (z) `z-cleanup-retained`: 別の run。Task 2 が `failed`（stop_unconfirmed）、`cleanup` が終了コード 1・`retained` に `<RUN_DIR>/<run_id>/attempt-1`（stop not confirmed）・`removed_run_dir = false`。期待: force・`rm -rf` で消さず完全パスを停止の報告に書く、セッションディレクトリを `rm -rf` しない
- [ ] **Step 2: 構文を確かめる** — `uv run --no-project python -c "import json,sys; json.load(open(sys.argv[1]))" .agents/skills/issue-to-pr/evals/scenarios.json` が終了コード 0
- [ ] **Step 3: 変更前の回答を取る** — scratchpad の `eval-before/` に `origin/main` の SKILL.md と `AGENTS.md` を置き、Agent ツールの新しいサブエージェント（model `sonnet`）に、(s)〜(z) の指示文で 3 回答えさせる。ツールは 2 つのファイルの Read だけ。回答をセッションディレクトリの `eval/before-<n>.md` に保存する
- [ ] **Step 4: commit** — `test(issue-to-pr): --implement の振る舞いの比較の場面を足す (#157)`

### Task 5: SKILL.md と変更後の回答（GREEN）

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`、`.agents/skills/issue-to-pr/evals/validation.md`

テストの要否: 書かない（スキルの文面）。代わりに振る舞いの比較（writing-skills）、参照先の実在、`bash scripts/check-layout.sh`。

- [ ] **Step 1: SKILL.md を変える**（Spec の「設計」の SKILL.md の 6 点）
  - frontmatter: `argument-hint: "<Issue> [--implement AGENT]"`
  - 1 章: 「オプションは受け付けない」を「`--implement` だけを受け付ける。`--merge` とループ用のオプションは #116 で入れる（#158）…」にし、`### --implement` の節（担当の決まり方、`--implement AGENT`・`=AGENT`、位置・1 回、値は agent 名か `self`、`fallback` を保つ）
  - 2 章の 3: 成功の JSON に `implement`。続けて `check` のコマンド（`--implement` は値を 1 つの引数で渡す）、終了コード 0 で `assignment`・`self` を決定記録に写す（既定の `self` は既定の適用と書く）、2 で止まる、worktree・Herdr・予約に触れない
  - 4 章の 4: 表の先頭に「`check` の `self` が false → 下の節」、既存の 2 行に「`self` が true で」を足す
  - 4 章の 5 の後に `### Task の実装を runner の担当に依頼する（self 以外のとき）`: 出力先、依頼の JSON、依頼と `verdict` の表、確認とレビュー、依頼ごとの記録と後片付け、`run` の終了コード 2（`checkout_audit` は報告して止まり、prune・削除しない）、セッションディレクトリ、`self` で引き取らない、PR 本文に書くこと
  - 「停止時の報告」: `check` の終了コード 2、依頼の `failed`、上限に達した `retry`・`rejected`、残したもの（`retained`）と `cleanup` を使えなかった `RUN_DIR` の完全パス
  - 「ランタイムごとの違い」: Claude Code は `/issue-to-pr <Issue> [--implement AGENT]`、Pi の `/sp-brainstorm` は Issue の直後に `--implement` を続け、入口を案内するときも利用者が書いた `--implement` だけを含める
- [ ] **Step 2: 変更後の回答を取る** — Task 4 の Step 3 と同じ指示文・同じ方法で、`eval-after/` の新しい SKILL.md で 3 回。`eval/after-<n>.md` に保存
- [ ] **Step 3: 判定する** — 全回答を読み、場面ごとに期待を満たした回数を数える。変更後が外れた場面は文面を直して変更後だけを 3 回取り直す（Contingency）
- [ ] **Step 4: validation.md に書く** — 「`--implement`（#157）の振る舞いの比較」の節: 評価の方法と範囲、結果の表（場面 × 変更前・変更後）、実行した検証、行っていない確認
- [ ] **Step 5: 構造を確かめる** — SKILL.md の相対リンクの実在、コマンドの `implement_task.py` のパスの実在、`bash scripts/check-layout.sh` が終了コード 0
- [ ] **Step 6: commit** — `docs(issue-to-pr): --implement の担当の検査と依頼の手順を書く (#157)`

### Task 6: 実機の確認（使い捨ての対象、`codex`）

テストの要否: 書かない（本物の担当の起動の記録）。

- [ ] **Step 1: 対象を作る** — `$S=/workspaces/reso-world/tmp/agents/issue-157.e6surmvx/live`。`$S/repo` に `git init -b main`、`calc/__init__.py`（空）、`calc/ops.py`（`add(a: int, b: int) -> int`）、`tests/__init__.py`（空）、`tests/test_ops.py`（unittest の `AddTest`）、`.gitignore`（`__pycache__/`）を commit。remote は作らない。`git -C $S/repo worktree add -b feature $S/feature`
- [ ] **Step 2: 担当を検査する** — `implement_task.py check --implement codex` が終了コード 0・`self: false`・`assignment.agents == ["codex"]`（実際の雛形と個人設定）
- [ ] **Step 3: 依頼する** — `agent_tmp.py mkdir issue-157-implement` の `SESSION`、`RUN_DIR=$SESSION/task-1-attempt-1`。依頼の JSON（`repository=$S/feature`、`revision`=その HEAD、`task`=`Task 1: subtract を足す`、`allowed_files=["calc/ops.py", "tests/test_ops.py"]`、`commit_message`=`feat: subtract を足す`、`prompt`=小さな Plan の Task 1 の全文（`subtract(a: int, b: int) -> int` は `a - b`、`SubtractTest` で `subtract(5, 3) == 2` と `subtract(3, 5) == -2`、検証は `uv run --no-project python -m unittest discover -s tests -t . -q`、uv を実行できない環境ならそのことを `concerns` に書く））。`implement_task.py run --request ... --output-dir "$RUN_DIR" --implement codex` を `run_in_background: true` で起動し、完了通知を待つ
- [ ] **Step 4: 判定と取り込み** — `verdict` を記録する。`importable` なら `accept`、feature の HEAD が取り込んだ commit、`$S/feature` で `uv run --no-project python -m unittest discover -s tests -t . -q` が終了コード 0
- [ ] **Step 5: 後片付け** — `cleanup` の結果と、`git -C $S/repo worktree list --porcelain` に repo と feature だけが残ることを記録する
- [ ] **Step 6: #157 に記録する** — 予約が自分の SHA のままかを確かめてから、担当・観測したモデル・所要時間・`verdict`・`helper_commit`・取り込んだ commit・テスト・`cleanup` の結果をコメントする

### Task 7: 全体の検証と記録

テストの要否: 書かない（検証の実行）。

- [ ] **Step 1: 実際の `check`** — `PARENT_ROOT` の個人設定で、worktree の `implement_task.py check` が `self: true`（`--implement` なし）
- [ ] **Step 2: README の「テスト」** — worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を `monitoring-long-tasks` に従ってバックグラウンドで実行し、終了コード 0 とログの要約を記録する（ログはセッションディレクトリ）
- [ ] **Step 3: 記録を足す** — Plan の末尾に「実行の記録」（Task ごとの所要時間、検証の結果、実機の結果、評価の結果、判断）を足す。Spec の状態は `draft` のまま
- [ ] **Step 4: commit し、検証した HEAD と `git status --porcelain` が空なことを記録する**

### Task 8: push と PR

- [ ] **Step 1: 再確認** — #157 が open、予約が自分の SHA、同じ Issue の open PR が無い
- [ ] **Step 2: 検査と push** — `SHA="$(bash "$PARENT_ROOT/scripts/scan-before-push.sh" -C <worktree>)" && [ -n "$SHA" ] && git -C <worktree> push origin "${SHA:?}:refs/heads/feat/issue-157-issue-to-pr-implement"`
- [ ] **Step 3: PR を作る** — `gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-157-issue-to-pr-implement`（draft にしない）。本文: `Closes #157`、変更概要、Spec の決定と理由、実行方式と理由、検証と結果、実機の結果、作業時間と Task 別の内訳
- [ ] **Step 4: #157 に状況を書く** — PR の URL、Spec・Plan の manifest（GitHub から取り出した SHA-256・バイト数）、`planning: ready / implementation: in-progress`、Task 9 に進むこと

### Task 9: レビュー修正のサイクル（Spec の D-157-13）

各サイクル（最大 3 回）:

- [ ] **Step 1: レビュー** — `PARENT_ROOT` の pr-review の `references/noninteractive.md` を読み、`prepare-parent`（DSH の親入力。新しい出力先）→ `uv run --project "$PARENT_ROOT" --locked python -m tools.agent_runner run --workflow review --repository "$PARENT_ROOT" --revision <PR の HEAD> --prompt-file <セッションディレクトリのプロンプト> --concurrency 5 --output-dir <新しい出力先>`（`--write-exception` は `helper_write_exceptions` の値を 1 つずつ。プロンプトは、各レビュアーが `PARENT_ROOT` の pr-review の非対話の入口で PR 全体を独立にレビューし、他のレビュアーの成果を読まない指示と `parent_pr_data`）を `run_in_background: true` で起動する。雛形の `after_run`（`finalize-parent`・`attach-runner`）の結果、各試行の state・`stop_confirmed`・payload を確かめる。runner は成功したが結果を受け付けられなかったレビュアーだけを同じサイクルで 1 回起動し直す。受け付けたレビューが 0 なら止まる。`outside_changes` は中身を記録し、起動の前から監査できない登録（2026-10-19 の `/tmp/pr-review-182-177dc8a7/worktree`）と、同じ時間に動いている他のセッションの worktree だけなら、それを理由にレビューの失敗にしない（runner は他のセッションの変更との因果を断定しない）。それ以外の checkout が出たら、原因を確かめるまで次の段に進まない
- [ ] **Step 2: 修正の要否** — `review-fix-planning` をレビューディレクトリ（`PARENT_ROOT/reviews/usaturn/create-reso-world/#<PR>-feat/issue-157-issue-to-pr-implement/`）で実行する。判断基準・三択・自己レビューの上限は review-fix-planning に従う
- [ ] **Step 3: 結論ごとの操作**
  - 修正する: 修正・検証（関連テストと README の「テスト」の 3 つ。SKILL.md の振る舞いに関わる文面を変えたら変更後の評価を 3 回、`implement_task.py` の `run`・`accept`・`cleanup` の経路を変えたら実機を 1 回）・自己レビュー（最大 1 回）の後、Task 8 の Step 2 の形で push し、次のサイクルへ。3 回目の後は止まって報告する（マージしない）
  - 修正不要: `origin/main` が進んでいれば feature branch に merge（force push しない。機械的に解消できない競合なら止まる）して全体の検証をやり直し push する。PR が draft でない、`headRefOid` が検証した HEAD、マージできる状態を確かめてから `gh pr merge --repo usaturn/create-reso-world --merge <PR>` でマージする（branch は消さない）。#157 が `completed` で close したことを確かめる
  - 停止: 理由を報告する
- [ ] **Step 4: 記録と解放** — 各サイクルの結論を PR と #157 に書き、#116 に結果をコメントする（調整役の表は変えない）。予約を `git push --force-with-lease=refs/heads/agent-claims/issue-157:36c163d4419705386e0d96850889112f0be6b541 origin :refs/heads/agent-claims/issue-157` で解放し、ref が無いことを確かめる

### Task 10: 片付けと報告

- [ ] **Step 1:** 使い捨ての対象とセッションディレクトリ（`issue-157-implement.*` を含む）の中身を確かめ、要らないものだけを空値ガード付きで消す。残すものは完全パスを報告する
- [ ] **Step 2:** Herdr のタスクを completed にし、PR の URL・検証結果・worktree・branch・Spec・Plan・残したログの絶対パス・所要時間を報告する

---

## 実行の記録

ledger（SDD の進み）: `/workspaces/reso-world/tmp/agents/issue-157.e6surmvx/sdd/progress.md`。予算の ledger: 同じディレクトリの `budget.jsonl`（開始し直す前のものは `budget-initial.jsonl`）。

### 判断（Ruling）

- 作業領域: SDD・executing-plans の作業領域（`.superpowers/sdd/`）は worktree の中に作られるので、`tmp/agents/issue-157.e6surmvx/sdd/` に置き、スクリプトを使わずに ledger を手で書いた（AGENTS.md の「コミットしないファイルの置き場所」）
- Task 5: writing-skills の手順（変更前の失敗を見てから文面を書く）に対し、変更前の回答の取得中に、移植元の評価（agent-workspace #679・#696）で確かめた文を土台に文面を書いた。変更前の回答は文面を書いた後に読んだ。変更後の回答を関門にした
- Task 6: SKILL.md の手順（ledger を `cleanup` の前に書く）に対し、`task.json`・`accept.json` を `cleanup` の前に写して記録を保ち、ledger の行は `cleanup` の直後に書いた

### Task ごとの結果

| Task | commit | 検証 |
| --- | --- | --- |
| 1 `resolve_issue.py` の `--implement` | `3e5ce92` | RED: 14 件が失敗（`implement` の項目が無い・`--implement` を #116 で拒否）。GREEN: `test_resolve_issue.py` 84 passed |
| 2 `implement_task.py` と雛形 | `4c6c3fc` | RED: `implement_task.py` が無いことで収集の段で失敗。GREEN: 2 つのテストと `tools/agent_runner/tests/test_cli.py` で 133 passed。`implement_task.py` の SHA-256 は移植元と一致。新しい `checkout_audit` のテストは、監査を外す変異で失敗することを確かめた |
| 3 2 段の結合 | `6f515e7` | `test_resolve_issue.py` 89 passed。期待を 1 か所変えると失敗することを確かめて戻した |
| 4 評価の場面と変更前の回答 | `6b7384f` | `scenarios.json` の構文 OK（既存の部分は変えず 78 行の追加）。変更前の回答 3 回（sonnet、各回 Read 2 回だけ） |
| 5 SKILL.md と変更後の回答 | `f365a09` | 変更後の回答 3 回で 9 行とも 3/3（変更前は 5 行が 0/3）。REFACTOR なし。参照先の実在 OK |
| 6 実機 | （リポジトリの変更なし） | `codex` に 1 回依頼して `importable` → `accept`（helper の commit）→ テスト成功 → `cleanup`（`retained` なし）。#157 のコメントに記録 |

Task 7 の全体の検証は、この記録を commit した HEAD で行う。その後に足す commit が Spec・Plan の記録だけなら、全体の検証をやり直さず、マージの前に、検証した HEAD からの差分が `docs/superpowers/` だけであることを確かめる（Spec の D-157-13）。
