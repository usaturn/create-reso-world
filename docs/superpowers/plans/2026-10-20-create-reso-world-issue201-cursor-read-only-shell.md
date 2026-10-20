# Issue #201 Cursor の読み取りの役割の起動 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft
- 実行方式: `superpowers:executing-plans`（このセッションが inline で実装する）。理由: `implement_task.py check` の `self` が true。Task は 4 つで、Task 1 のテストと adapter は同じ 3 ファイルを逐次に変え、Task 3・4 は実機と PR を扱う controller の作業なので、子に渡すと文脈を渡しきれない

**Goal:** runtime が `cursor` の担当を `writes = false` の役割で `-f --sandbox disabled` で起動し、pr-review の helper をシェルで実行できるようにする。

**Architecture:** `tools/agent_runner/adapters/cursor.py` の `prepare` の分岐を 1 行変える。runner・設定・loop は変えない。テストは単体（`prepare`）と、偽の CLI で runner を通すもの。実機は runner の読み取り・シェル（R1）と、この PR のレビュー（R2）。

**Tech Stack:** Python 3.14、pytest、uv、Cursor Agent CLI（`agent`）

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue201-cursor-read-only-shell-design.md`

## Global Constraints

- `writes = false`: `["-f", "--sandbox", "disabled"]`、`writes = true`: `["-f"]`。担当の名前・モデルで分けない
- 既定の割り当て、個人設定、`writes = true` の起動、Codex・DSH の制限、loop・`run_roles.py` の判定、利用者の `~/.cursor/cli-config.json` を変えない
- テストに観測の版・モデル名・文書の文言を写さない（AGENTS.md「テストの採用基準」）。起動の引数は安全な操作範囲の固定値として書き、理由をコメントに書く
- 実機の起動は R1（`cursor`・`cursor-grok47` で各 1 回）と R2（`cursor-grok47` のレビュー 1 回）だけ。同じ原因の失敗の再試行は 1 回まで
- 参照 PR の版の誤記（`2026.10.16`）を写さない。参照 PR の記録と、この環境の結果を区別して書く

## Review Focus

- 利用者が `args` に `--mode` などを足した担当: adapter は利用者の引数を `--model` の後に足すだけで、検査しない（今の挙動）。Task 1 のテストで、追加引数が今のまま残ることだけを確かめる
- fallback で起動された担当: 一次担当と同じ役割の `writes` で起動されること（Task 1 の runner のテスト）
- `self-review`・`fix-check` の名前の役割: adapter は役割の名前を見ないので、`writes = false` なら同じ起動（Task 1 の runner のテスト）
- 実機で CLI が自動更新される: R1・R2 の前後で `agent --version` を記録する（Task 3・4）
- 利用者の CLI の設定が実行で変わらないこと: R1・R2 の前後で `~/.cursor/cli-config.json` の `sandbox`・`approvalMode`・`permissions` を比べる（Task 3・4）

## 要件の照合

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| C1 | Task 1 | `prepare` の argv | `test_cursor.py` |
| C2 | Task 1 | `prepare` の argv（writes = true）、stdin、追加引数 | `test_cursor.py`（既存を含む） |
| C3 | Task 1 | 偽の CLI が受け取った argv（任意名・fallback・3 つの役割名） | `test_integration.py` |
| C4 | Task 3 | runner の `result.json` の state・payload・identity・`outside_changes` | 実機 R1 |
| C5 | Task 4 | loop の `review` の `accepted`、レビューの成果と cleanup | 実機 R2 |
| C6 | Task 2・3・4 | `cursor.rst` と PR 本文の記録 | 差分の確認 |
| C7 | Task 2・5 | 文書と起動の一致、既定の割り当ての不変 | `git diff`、rstcheck |
| C8 | Task 1・5 | テストの終了コード | pytest、README の「テスト」 |

共有する前提: adapter の argv（Task 1）を、文書（Task 2）と実機の記録（Task 3・4）が説明する。最終の一致は Task 5（統合確認、このセッション）が条件単位で確かめる。

---

### Task 1: adapter の分岐とテスト

テストの要否: 要る。起動の引数の分岐（安全な操作範囲）と runner の経路を、コードを実行して確かめる。実際に起きた不具合（参照 Issue のシェルの拒否）の再発を防ぐ。

**Files:**
- Modify: `tools/agent_runner/adapters/cursor.py:157`
- Modify: `tools/agent_runner/tests/adapters/cursor/test_cursor.py:59-75`
- Modify: `tools/agent_runner/tests/adapters/cursor/fake_cli.py:14,26`
- Modify: `tools/agent_runner/tests/adapters/cursor/test_integration.py`

**Interfaces:**
- Produces: 偽の CLI の `--echo-argv`（result の JSON に `"argv": sys.argv[1:]` を足す）

- [ ] **Step 1: 失敗するテストを書く**

`test_cursor.py`:
- `test_prepare_reads_prompt_from_stdin_and_trusts_worktree` から `--mode ask` の検査を外す
- `test_prepare_read_only_role_allows_shell_without_cursor_sandbox`: `writes=False` で `argv.count("-f") == 1`、`argv[argv.index("--sandbox") + 1] == "disabled"`、`"--mode" not in argv and "--plan" not in argv`。コメントに防ぐ誤り（ask・plan はシェルを拒否、sandbox は helper の書き込み先を拒否、`-f` の sandbox の扱いは文書に無い）と、観測は `runtimes/cursor.rst` にあることを書く
- `test_prepare_write_role_forces_and_effort_uses_bracket`: `spec.argv.count("-f") == 1` と `"--sandbox" not in spec.argv` を足す

`fake_cli.py`: `--mode ask` の検査を外す。`--echo-argv` があれば result の JSON を `{"answer": 42, "argv": sys.argv[1:]}` にする。

`test_integration.py`: `test_read_only_roles_launch_any_cursor_agent_with_shell_and_without_sandbox`。役割 `inspect`・`self-review`・`fix-check`（`writes=False`）を 1 つの workflow に置き、`inspect` → `reviewer-one`、`self-review` → 一次担当 `broken-primary`（`--fail-bad`）・fallback `fallback-reviewer`、`fix-check` → `my-cursor` を割り当てる（`--echo-argv` は `broken-primary` 以外）。`run_workflow` を 1 回実行し、
- `batch.state == "success"`
- `self-review` の結果は `actual_agent == "fallback-reviewer"`、1 回目の試行は `response_failed`
- 3 つの結果の payload の `argv` が、どれも `-f` を 1 つ、`--sandbox` の次が `disabled`、`--mode`・`--plan` を含まない

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tools/agent_runner/tests/adapters/cursor -q`
Expected: 足したテストが `--sandbox` の欠落・`--mode ask` で FAIL

- [ ] **Step 3: `prepare` の分岐を変える**

`argv += ["-f"] if context.role.writes else ["-f", "--sandbox", "disabled"]`。上に 2 行の理由のコメント（#201）。

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run pytest tools/agent_runner/tests/adapters/cursor tools/agent_runner/tests/test_runner.py -q`
Expected: PASS（終了コード 0）

- [ ] **Step 5: commit**

```bash
git add tools/agent_runner/adapters/cursor.py tools/agent_runner/tests/adapters/cursor/
git commit -m "fix(agent-runner): launch cursor read-only roles with -f --sandbox disabled (#201)"
```

### Task 2: 文書

テストの要否: 要らない（文書だけ）。代わりに `uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning tools/agent_runner/runtimes/cursor.rst` と `git diff` で、起動の記述が Task 1 の argv と一致することを確かめる。

**Files:**
- Modify: `tools/agent_runner/runtimes/cursor.rst`（「起動と入力」「検証と出所」、新しい節「既知の制限」）
- Modify: `.devcontainer/README.md`（「非対話エージェントのランナー（agent-runner）」の最後の段落の後）

- [ ] **Step 1: `cursor.rst` を直す**
  - 起動の形式: `agent -p --output-format stream-json --trust -f [--sandbox disabled] --model <model> [args...]`
  - `-f` は allowlist に無いシェルのコマンドも確認なしで実行し、`permissions.deny` は引き続き拒否される（CLI のヘルプ）。`--sandbox disabled` は `writes = false` の役割だけに付け、利用者の `sandbox.mode` を上書きする
  - `--mode ask`・`plan` を使わない理由（read-only でシェルを拒否。#201 の前は pr-review の helper を実行できなかった）
  - `--sandbox disabled` を明示する理由: 参照 PR（usaturn/agent-workspace#753、merge `6e7b16e5e5de11e4beb711b4a5a84f5f274249e1` の `tools/agent_runner/runtimes/cursor.rst`）の観測で、sandbox は worktree と `/tmp` の外・共有 `.git`・ネットワークを拒否し、helper の書き込み先（レビューの保存先、共有 Git、uv のキャッシュ）と両立しない。`-f` が sandbox を外す挙動（同 PR で `2026.10.18-ea085cb` で観測）は文書に無いので頼らない。この環境では再観測していない
  - `writes = false` は runner の指示であって sandbox ではない
  - 「既知の制限」: Spec の「既知の制限」の 4 項目と、`writes = true` は `--sandbox` を付けず利用者の設定と `-f` の挙動に従うこと
  - 「検証と出所」: 実機の記録は Task 3・4 で足す。ここでは「#201 の変更は偽 CLI のテストで確かめた」まで
- [ ] **Step 2: README に 1 段落を足す**（cursor の担当の `writes = false` の起動、helper を実行できること、`writes = false` は指示であること、`outside_changes` の事後の報告、詳細は `cursor.rst`）
- [ ] **Step 3: 検査**: rstcheck、`git diff --stat`。
- [ ] **Step 4: commit**（`docs(agent-runner): ...`）

### Task 3: 実機 R1（runner の読み取り・シェル）

テストの要否: 要らない（実機の 1 回限りの確認。テストに写さない）。

**Files:**
- 一時: `$SESSION/r1/`（`SESSION=/workspaces/reso-world/tmp/agents/issue-201.p2cop2y9`）。使い捨てのリポジトリ `repo/`（`marker.txt` に `8642`）、一時の個人設定 `config.toml`、prompt、runner の出力
- Modify: `tools/agent_runner/runtimes/cursor.rst`（「検証と出所」に結果）

- [ ] **Step 1: 前の状態を記録**: `agent --version`、`jq '{sandbox, approvalMode, permissions}' ~/.cursor/cli-config.json`
- [ ] **Step 2: 一時の個人設定**: `schema_version = 1` と `[workflows.cursor-smoke.assignments.inspect] agents = ["cursor"]`。この branch の worktree を cwd にし、`--template .devcontainer/agent-runner.toml --config "$SESSION/r1/config.toml"` で `check` を通す
- [ ] **Step 3: 実行**: `run --workflow cursor-smoke --repository "$SESSION/r1/repo" --revision HEAD --prompt-file "$SESSION/r1/prompt.txt" --output-dir "$SESSION/r1/out-<agent>" --assign inspect=<agent>` を `cursor`、`cursor-grok47` の順に 1 回ずつ（Bash の `run_in_background: true` で終了通知を待つ。期限は役割の 2700 秒＋停止の猶予）。prompt は、`marker.txt` を読む、`date -u +%Y`・`uv --version`・`mktemp -d` のディレクトリへの書き込み・読み取り・削除を実行し、`{"marker": ..., "year": ..., "uv": ..., "tmp": "ok"}` だけを返すよう求める
- [ ] **Step 4: 確かめる**: 終了コード、`state`、payload、`identity.model`、`elapsed_seconds`、試行の `stop_confirmed`、`outside_changes`、stdout の `shellToolCall` の終了コード、runner の worktree の変更の有無、後の `agent --version` と CLI の設定
- [ ] **Step 5: `cursor.rst` に記録して commit**

### Task 4: PR と実機 R2（この PR のレビュー）

テストの要否: 要らない（実機の 1 回限りの確認）。

- [ ] **Step 1**: Task 5 の統合確認の後、push の前の検査 → push → `gh pr create`（本文に R2 は実施中と書く）
- [ ] **Step 2**: この branch の worktree の `loop.py` で `start <PR の URL> --controller-model claude-opus-5-5 --controller-runtime claude-code --assign inspect=cursor-grok47` → `cycle-begin` → `review`（`run_in_background: true`、終了通知を待つ。stall は 10 分間隔で `stdout.log` の更新時刻）
- [ ] **Step 3**: `accepted` に `cursor-grok47` があり、レビューの成果（レビューファイル・候補一覧・実行記録）と pr-review の cleanup の成功を確かめる。`finish --run <run_dir> --abort "external: ..."`（Spec の D-201-6）
- [ ] **Step 4**: `cursor.rst` に記録（レビューした HEAD、版、所要、観測したモデル、指摘の数、cleanup、`outside_changes`、残した資源）→ commit → 検査 → push → PR 本文の更新

### Task 5: 統合確認（このセッション）

- [ ] `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`（終了コード 0。環境要因の失敗は main で再現して区別する）
- [ ] Spec の C1〜C8 を、Task の結果と実行の証拠で 1 つずつ照合する。既定の割り当て（`git diff origin/main -- .devcontainer/agent-runner.toml` が空）を確かめる
- [ ] ブランチ全体のレビュー（新しいサブエージェント 1 つ）

## 実行予算

- Issue 全体の能動時間: 240 分（実装は小さいが、実機の R1 2 回と R2 のレビュー 1 回（参照 PR の実績でレビュー約 11 分、loop 全体約 13 分）と、記録・PR の更新がある）。ledger: `/workspaces/reso-world/tmp/agents/issue-201.p2cop2y9/budget.jsonl`
- phase の目安: 準備・Spec・Plan 45 分、Task 1 25 分、Task 2 20 分、Task 3 25 分、Task 5 30 分、Task 4 50 分、予備 45 分
- worker: R1 の各 run は期限 50 分（役割の 2700 秒＋猶予）・無進捗 10 分で stall を疑う。R2 の `review` は期限 50 分・同じ。全体レビューのサブエージェントは 30 分。pytest の全体は 20 分
- 再試行の上限: 同じ失敗（同じ signature）の再試行は 1 回まで。実機の失敗は原因を調べ、同じ原因で 2 回失敗したら未達として記録して止まる。安全の失敗（範囲外の変更・CLI の設定の変化・秘匿値の露出）は再試行しない
- checkpoint: phase の境界、予算の 50%（120 分）・100%、失敗の直後
- 縮小・切り出し・方法変更の候補: runner を通すテストを 1 つの役割に絞る。R1 の 1 回目が成功し 2 回目が CLI の利用枠などの外部要因で失敗したら、未達として記録する（別のモデルに替えない）。R2 が失敗したら原因を記録し、修正が要るなら PR に書いて止まる

## Contingency

- `--sandbox disabled` を CLI が拒否する（版の違い）: 実装を止め、`agent --help` の出力を Issue に書く
- R1・R2 が認証待ち・利用枠で止まる: 利用者の操作が要るので、記録して止まる（自分でログインしない）
- R2 で `rejected`: `rejected_stage` と理由を記録し、`next` が `review` の再実行なら 1 回だけ実行する。直らなければ `finish --abort` で止め、PR に未達として書く

## 完了

2026-10-20（JST）に実行した。状態は draft のまま（内容の承認ではない）。

- 所要: 着手（12:55 JST ごろ、Issue の解決）から記録の commit（14:10 JST ごろ）まで約 75 分。予算の ledger（13:02 JST から）の能動時間は約 67 分で、予算 240 分の約 28%
- 内訳: 調査・Spec・Plan 約 10 分、Task 1 約 3 分、Task 2 約 2 分、Task 3（R1 の 2 回）約 3 分、全体レビュー（サブエージェント、並行）約 8 分とその修正 約 5 分、Task 5 の全体テストの待ち 約 48 分（ほかのセッションの全体テストと並行して遅かった）、push・PR 約 2 分、Task 4（R2）約 8 分、記録・PR の更新 約 5 分
- 受け入れ条件: C1〜C3 は cursor のテスト（`d6b9daf` の後 60 passed。足した 2 つのテストは adapter を変える前に失敗した）、C4 は R1（`cursor`・`cursor-grok47` とも `success`）、C5 は R2（loop の `accepted`、pr-review の実行記録 `success`、cleanup 済み）、C6 は `runtimes/cursor.rst` の「実機の確認（#201）」と PR 本文、C7 は `git diff origin/main -- .devcontainer/agent-runner.toml` が空・rstcheck Success・全体レビュー（必須・推奨 0 件）、C8 は `uv run pytest tests/skills .agents/skills .agents/scripts tools`（`c499d2e` で 3411 passed）・`run-tests.bash`（PASS 33）・`check-layout.sh`（PASS）
- 判断（ledger の Ruling）: SDD の workspace を worktree の中に作らず `tmp/agents` に置いた。偽 CLI の `--model` の検査に fallback 用の値を足した（`duplicate_model`）。helper のネットワーク利用の出所を `gh`・`git fetch` にした。全体レビューの軽微 4 件のうち、Spec の設計 1 と C6 に関わる 3 点を直し、残り 3 点（`args` での上書き、CLI の自動更新、runner の worktree 自体の変更）は PR 本文の既知の制限に書いて見送った
- ledger・実機の出力: `/workspaces/reso-world/tmp/agents/issue-201.p2cop2y9/`（PR を作った後に片付ける）
