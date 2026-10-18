# Issue #149 agent_runner の土台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 文書管理・実装対象: `usaturn/create-reso-world`（Issue #149、親 #116、子のキー `runner-core`）
- 状態: `draft`。実行許可は利用者の `/issue-to-pr #149`（検証・commit・push・PR の作成まで。マージは含まない）
- 基準: 移植先 `3e3c1a3`（origin/main）、移植元 usaturn/agent-workspace `a47b2065fddad76b7475752fd0088af0733de204`

**Goal:** 移植元の `tools/agent_runner/` の本体と `tools/test_support/` の一部を写し、偽の adapter・偽の CLI だけで runner の挙動をテストで確かめられるようにする。

**Architecture:** コードは移植元のまま写し、Spec の C-3（grok-build を外す）・C-4（出力先の接頭辞）・C-13（コメントの Issue 番号）だけを変える。Python の環境はルートの `pyproject.toml`（importlib mode、C-1）。具体的な adapter は入れず、全ての runtime は未対応になる。

**Tech Stack:** Python 3.14、pydantic 2、pytest 9（importlib mode）、bash、git

**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue149-agent-runner-core-design.md`

## Global Constraints

- `requires-python = ">=3.14"`。依存は変えない（`pydantic>=2.12,<3`、dev は `pytest>=8`・`pyyaml>=6`）。ruff・pyright は加えない
- pytest: `addopts = "-p no:cacheprovider --import-mode=importlib"`、`pythonpath = [".", "tools/devenv_migration/tests"]`、`testpaths = ["tests/skills", ".agents/skills", ".agents/scripts", "tools"]`
- 移植元のファイルは `git -C "$SRC" show a47b206:<path>` で取り出す。`SRC=/workspaces/reso-world/tmp/agents/issue-149.i17bhabl/src-aw`（usaturn/agent-workspace の clone。無ければ `git clone https://github.com/usaturn/agent-workspace.git "$SRC"`）
- `Runtime` と adapter の名前の表は `claude-code`・`devin`・`pi`・`codex`・`cursor`・`dsh` の 6 つ（grok-build を外す）
- 公開の API の名前と形（`Request`・`Receipt`・`Result`・`BatchResult`・`Attempt`・`Identity`、adapter の protocol、`run_workflow` の引数）は変えない
- 既定の出力先: `tempfile.mkdtemp(prefix="create-reso-world-agent-runner-", dir="/tmp")`
- 写したコメントの移植元の Issue 番号は `agent-workspace#<番号>` と書く
- 本物の担当（モデル）を起動しない。テストは偽の adapter・偽の CLI だけ
- テストを書く基準は `AGENTS.md` の「テストの採用基準」。写さないテスト: `test_install.py`（C-10 の bash の検査に置き換える）、`tools/test_support/tests/`（C-6）
- 編集は worktree `/workspaces/reso-world/.worktrees/issue-149-agent-runner-core` だけ。コミットしないファイルは `PARENT_ROOT` の `tmp/agents/issue-149.i17bhabl/` に置く

## Review Focus

1. 個人設定が雛形の写し（postCreate の直後の状態）のときに `check` が通る（Task 5 の `test_shipped_template_passes_check` を「個人設定が無い」「雛形の写し」の 2 通りにする）
2. runner の担当（`AGENT_RUNNER_DEPTH=1`）の中からテストを実行しても、偽の担当だけのテストが通る（Task 8 の検証手順。`outside_runner` の効果）
3. `.devcontainer/test-pi-migrations.bash`（ルートの pytest の設定を読む）が importlib mode でも通る（Task 1 の検証手順）
4. CLI をリポジトリのルート以外の cwd から `python -m tools.agent_runner` で起動すると `tools` を import できない。文書（`interfaces.rst`・`.devcontainer/README.md`）に「リポジトリのルートを cwd にする」と書く（Task 5・6）
5. `XDG_CONFIG_HOME` が相対パス・空のときの個人設定の保存先が、読む側（`resolve_config_path`）と置く側（`place_agent_runner_config`）で一致する（Task 6 の bash の検査と Task 2 の `test_personal_path_precedence`）

## 受け入れ基準

- 動作環境: Dev Container の親 checkout と `.worktrees/<topic>` の worktree（`.venv` はそれぞれ `uv run` が作る）。同梱の雛形 `.devcontainer/agent-runner.toml`（役割だけ）と、その写しの個人設定
- 受け付けるべき実入力: 改行・引用符・非 ASCII を含むプロンプト、全角空白を含む write exception、改行を含むパスの checkout
- 防御範囲: 対象にする — 未知のキー・版・不正な参照・同じモデルの重複、入れ子の起動、adapter の無い runtime、停止を確認できない試行、秘密の値の漏えい（エラー・ログ・payload・receipt）。対象にしない — 悪意のある二重 fork（sandbox ではない）、名前から秘密と判別できない値、gitignore された資源の監査

## 実行方式

`superpowers:executing-plans`（controller が自分で実装する）。理由: Task は順に前の Task のモジュールを import し（models → adapters → process → workspace → runner → cli）、同じ `pyproject.toml` と移植元の読み取りを共有する。作業の大半は移植元からの写しと小さな変更で、文脈を子に渡すより controller が続けて行う方が早い。最後にブランチ全体のレビューを `superpowers:requesting-code-review` で 1 回行う。

## 実行予算

- 能動時間の予算: 300 分（Task 8 つ、写すコード約 2,900 行・テスト約 4,000 行、全体の検証 1 回あたり約 10 分）。ledger は `/workspaces/reso-world/tmp/agents/issue-149.i17bhabl/budget.jsonl`
- phase の目安: 準備（調査・Spec・Plan）60 分、Task 1〜7 で 150 分、Task 8（全体の検証・レビュー・PR）90 分
- worker: 長時間の検証（`uv run pytest ... tools`、`bash .devcontainer/run-tests.bash`）は Bash の `run_in_background: true` で起動し、終了コード付きの完了通知で待つ。期限 20 分、無進捗の打ち切りは使わない（検証コマンドは「事前宣言した打ち切り」の対象にしない）
- 再試行の上限: 同じ失敗の再試行は 1 回まで。時間に依存するテストの失敗（負荷）は、単独で 1 回だけ再実行し、再現すれば `systematic-debugging` で調べる
- checkpoint: Task 1 の後（既存のテストが新しい設定で通るか）、Task 5 の後（runner のテストが全部通るか）、予算の 50%・100%、検証の失敗の直後
- 縮小・方法変更の候補: (1) 時間に依存して不安定なテストが直せなければ、移植元の値のまま残し、PR に既知の制限として書く。(2) devenv_migration の importlib mode での不具合が `pythonpath` で解けなければ、README の入口を `tools/agent_runner` に絞り（C-11 の別案 a）、Spec の判断を更新する。(3) 予算の 100% に達したら停止して報告する

## Contingency

- 最初の RED で、移植先の環境の出力や挙動が移植元の前提と違う場合は、仕様の意味を保つ最小の修正にし、下の「記録」に書いて続ける
- 仕様の意味を変える必要が出たら止まる（issue-to-pr の停止条件）

---

### Task 1: Python の環境と pytest の設定

**Files:**
- Create: `tools/__init__.py`（空）
- Modify: `pyproject.toml`、`uv.lock`

**Interfaces:**
- Produces: `tools` パッケージ。importlib mode の pytest の設定（Global Constraints のとおり）

テスト: 書かない（設定値の変更。代わりに既存のテストを新しい設定で実行する）

- [ ] **Step 1:** `pyproject.toml` の `requires-python` と `[tool.pytest.ini_options]` を Global Constraints の値にし、`tools/__init__.py` を空で作る
- [ ] **Step 2:** `uv lock` を実行する。Expected: `uv.lock` の `requires-python = ">=3.14"`、パッケージの版の変化が無い（`git diff uv.lock` で確かめる）
- [ ] **Step 3:** `uv run pytest --collect-only -q tests/skills .agents/skills .agents/scripts tools/devenv_migration/tests` を実行する。Expected: 1075 件（656 + 419）、エラー 0
- [ ] **Step 4:** `bash .devcontainer/test-pi-migrations.bash` を実行する。Expected: 終了コード 0（419 passed）
- [ ] **Step 5:** commit（`build: run pytest in importlib mode on Python 3.14 for the agent runner (#149)`）

### Task 2: models・設定の検査・adapter の表・環境・receipt

**Files:**
- Create: `tools/agent_runner/models.py`、`config.py`、`environ.py`、`receipts.py`、`adapters/__init__.py`、`adapters/skills.py`
- Test: `tools/agent_runner/tests/test_config.py`、`test_environ.py`、`tests/adapters/test_skills.py`

**Interfaces:**
- Produces: `models.Runtime`（6 つ）、`Config`・`Agent`・`Role`・`Workflow`・`Assignment`・`Request`・`Receipt`・`Identity`・`Attempt`・`Result`・`BatchResult`・`CheckoutAudit`・`AuditReason`・`State`・`Payload`。`config.load_config(template, personal=None, assignments=None, workflow=None) -> Config`、`validate_config(config, workflow=None) -> Config`、`check_depth() -> None`、`resolve_config_path() -> Path`、`ConfigError(category)`。`adapters.load_adapter(runtime) -> Adapter`、`module_name`、`runtime_supported`、`UnsupportedRuntime`、`AdapterContext`・`LaunchSpec`・`Capabilities`・`AdapterOutcome`・`Adapter`。`environ.literal_environ()`・`secret_values(env)`。`receipts.read_receipt(path)`
- この Task では `tools/agent_runner/__init__.py` を作らない（namespace package として import する。Task 5 で作る）

- [ ] **Step 1:** 3 つのテストを移植元から写す（変更なし）
- [ ] **Step 2:** `uv run pytest tools/agent_runner/tests/test_config.py tools/agent_runner/tests/test_environ.py tools/agent_runner/tests/adapters/test_skills.py -q` を実行する。Expected: 収集エラー（`tools.agent_runner.adapters` などが無い）
- [ ] **Step 3:** 6 つのコードを写し、`models.Runtime` と `adapters._MODULES` から `grok-build` を外す
- [ ] **Step 4:** Step 2 を再実行する。Expected: 全て PASS（`test_absent_adapters_are_unsupported_without_import_error_leaks` は 6 runtime + unknown の 7 件）
- [ ] **Step 5:** commit

### Task 3: 監督プロセスと実行

**Files:**
- Create: `tools/agent_runner/_supervisor.py`、`process.py`
- Test: `tools/agent_runner/tests/conftest.py`、`test_process.py`

**Interfaces:**
- Consumes: `adapters.LaunchSpec`、`models.State`
- Produces: `process.execute(spec, *, cwd, env, deadline_seconds, stdout_path, stderr_path, cancel, secrets=(), stop_grace_seconds=0.3) -> ProcessResult`、`ProcessResult(state, exit_code, stop_confirmed, elapsed_seconds)`、`redact_file(path, secrets) -> bool`。テストの補助 `test_process.alive(pid) -> bool`（Task 5 のテストが import する）

- [ ] **Step 1:** 2 つのテストを写す。コメントの `#705` を `agent-workspace#705` にする
- [ ] **Step 2:** `uv run pytest tools/agent_runner/tests/test_process.py -q` を実行する。Expected: 収集エラー（`tools.agent_runner.process` が無い）
- [ ] **Step 3:** 2 つのコードを写す（変更なし）
- [ ] **Step 4:** Step 2 を再実行する。Expected: 全て PASS
- [ ] **Step 5:** commit

### Task 4: worktree と監査

**Files:**
- Create: `tools/agent_runner/workspace.py`
- Test: `tools/agent_runner/tests/test_workspace.py`

**Interfaces:**
- Consumes: `process.execute`・`ProcessResult`、`environ.literal_environ`、`models.CheckoutAudit`・`AuditReason`
- Produces: `WorkspaceError(reason)`、`resolve_revision(repository, revision="HEAD") -> str`、`git_common_dir(repository) -> Path`、`create_worktree(repository, revision, destination) -> Path`、`async prepare_worktree(repository, commit, destination, *, deadline_seconds, cancel, stdout_path, stderr_path, secrets=()) -> ProcessResult`、`snapshot_checkouts(repository) -> CheckoutSnapshot`、`require_auditable_checkouts(repository) -> CheckoutSnapshot`、`audit_checkouts(before) -> list[CheckoutAudit]`、`changed_checkouts(before) -> list[str]`、`CheckoutAuditError(findings)`

- [ ] **Step 1:** テストを写す。`from tools.test_support.repos import SubmoduleState, create_parent_repo` を外し、`test_audit_detects_submodule_dirty_content` をテストの中で submodule を作る形にする（C-7）。作り方: `repository` fixture と同じ形の repository をもう 1 つ（submodule の元）作り、`git -c protocol.file.allow=always -C <親> submodule add -q <元のパス> sub` と commit で、初期化済み・gitlink と一致した submodule を持つ親にする。検査は移植元と同じ（submodule の中の追跡ファイルを先に dirty にしてから snapshot を取り、さらに変えると `changed_checkouts(before) == [str(親)]`）。コメントの `#6..` を `agent-workspace#...` にする
- [ ] **Step 2:** `uv run pytest tools/agent_runner/tests/test_workspace.py -q` を実行する。Expected: 収集エラー
- [ ] **Step 3:** `workspace.py` を写す（変更なし）
- [ ] **Step 4:** Step 2 を再実行する。Expected: 全て PASS
- [ ] **Step 5:** commit

### Task 5: runner・後処理・CLI・テスト補助・雛形・共通仕様

**Files:**
- Create: `tools/agent_runner/__init__.py`、`__main__.py`、`runner.py`、`hooks.py`、`cli.py`、`interfaces.rst`、`tools/test_support/__init__.py`、`plugin.py`、`texts.py`、`.devcontainer/agent-runner.toml`
- Test: `tools/agent_runner/tests/test_runner.py`、`test_review_regressions.py`、`test_cli.py`

**Interfaces:**
- Consumes: Task 2〜4 の全て
- Produces: `run_workflow(config, workflow, prompt, repository, *, revision="HEAD", concurrency=2, output_dir=None, cancel=None, adapter_loader=load_adapter, environment=None, sandbox_write_paths=(), write_exceptions=(), payload_check=None) -> BatchResult`、`RunnerError(category)`、`EXCEPTIONS_HEADING`、`hooks.run_after_run(commands, *, result_path, cwd, cancel) -> list[dict[str, object]]`、`AFTER_RUN_DEADLINE_SECONDS = 60.0`、`cli.main(argv=None) -> int`、`tools.test_support.plugin.outside_runner`、`tools.test_support.texts.FINDING_CONTENT`・`FINDING_REASON`

- [ ] **Step 1:** 3 つのテストを写し、次を変える
  - `test_runner.py`: `test_default_artifact_directory_is_unique` の接頭辞を `/tmp/create-reso-world-agent-runner-` にする。コメントの `#694` を `agent-workspace#694` にする
  - `test_review_regressions.py`: コメントの `#694` を `agent-workspace#694` にする
  - `test_cli.py`: 節の見出しの `Issue #601`・`Issue #656` を `agent-workspace#601`・`agent-workspace#656` にする。`test_shipped_template_passes_check` を `@pytest.mark.parametrize("personal", ["absent", "template-copy"])` にし、`template-copy` では同梱の雛形を `tmp_path` に写して `AGENT_RUNNER_CONFIG` に指定する。検査は `cli.main(["check"]) == 0` と `all(agent["supported"] is True for agent in agents)`（「agent が 1 つ以上」の条件を外す。C-9）
- [ ] **Step 2:** `uv run pytest tools/agent_runner/tests/test_runner.py tools/agent_runner/tests/test_review_regressions.py tools/agent_runner/tests/test_cli.py -q` を実行する。Expected: 収集エラー（`tools.agent_runner.runner`・`tools.test_support` が無い）
- [ ] **Step 3:** コードを写し、次を変える
  - `runner.py`: 既定の出力先の接頭辞（C-4）
  - `tools/test_support/__init__.py`: docstring を移植先の内容（`outside_runner` と自由記述のサンプル）にし、`texts` の 2 つだけを `__all__` に出す
  - `plugin.py`: `outside_runner` の fixture だけを残す（`workspace_factory`・`workspace`・`owned_worktree` と `repos` の import を外す）。module の docstring は使い方（`pytest_plugins`・`pytestmark`）と、autouse にしない理由にする
  - `texts.py`: `FINDING_CONTENT` の「`tools/devenv/.venv` 済み」を「親 checkout の `.venv` 済み」にする（改行・タブ・CRLF・非 ASCII は保つ）
- [ ] **Step 4:** `.devcontainer/agent-runner.toml` を作る。`schema_version = 1` と `[roles.inspect]`（`writes = false`、`deadline_seconds = 2700`）・`[roles.implement]`（`writes = true`、5400）・`[roles.self-review]`（false、2700）・`[roles.fix-check]`（false、2700）。全て `skills = []`・`result_shape = "json"`。冒頭のコメントに、資格情報の値を書かないこと、`[agents.*]` は #150・#151、`[workflows.*]` は参照する子が足すことを書く
- [ ] **Step 5:** `interfaces.rst` を写し、C-12 のとおり直す（題、Issue 番号、runtime の一覧から grok-build、起動の形とルートの cwd、後処理の例は #153 が入れること）
- [ ] **Step 6:** Step 2 を再実行する。Expected: 全て PASS
- [ ] **Step 7:** `uv run --project . --locked python -m tools.agent_runner check` と `list` を実行する。Expected: 終了コード 0、`runtimes` の 6 件が全て `"supported": false`、`agents` が空、`roles` が 4 つ
- [ ] **Step 8:** commit

### Task 6: 個人設定の導入と Dev Container の文書

**Files:**
- Modify: `.devcontainer/install_beforehand.bash`（1 段目の後）、`.devcontainer/test-install-beforehand.bash`、`.devcontainer/README.md`（新しい節と 144 行目の 1 文）

**Interfaces:**
- Consumes: `.devcontainer/agent-runner.toml`
- Produces: `place_agent_runner_config`（シェル関数。`XDG_CONFIG_HOME` が絶対パスならその下、それ以外は `$HOME/.config` の下の `agent-runner/config.toml` に、無いときだけ雛形を写す。既存のファイル・symlink（壊れたものも）は変えない。失敗は `return 1`）

- [ ] **Step 1:** `test-install-beforehand.bash` に検査を足す: `sed -n '/^place_agent_runner_config() {$/,/^}$/p'` で関数を取り出し、`env HOME="$tmp/home" XDG_CONFIG_HOME="$xdg" bash -c "cd \"$root\"; $function; place_agent_runner_config"` で実行する。3 通り（`XDG_CONFIG_HOME` が空・`relative`・絶対パス）で、保存先が雛形とバイト一致（`cmp`）し、書き換えた内容が 2 回目の実行で残ること。壊れた symlink の保存先がそのまま残り、参照先が作られないこと。`$HOME/.config` が通常のファイルのとき、終了コードが 0 でないこと。一時ディレクトリは `mktemp -d` と `trap 'rm -rf -- "${tmp:?}"' EXIT`
- [ ] **Step 2:** `bash .devcontainer/test-install-beforehand.bash` を実行する。Expected: FAIL（関数が無い）
- [ ] **Step 3:** `install_beforehand.bash` の 1 段目の `for dir in ...; done` の後に、移植元の `place_agent_runner_config` とその呼び出し（失敗は `fail "Failed to place the agent-runner config."`）を置く。コメントは移植元の内容を移植先の言い方にする（「実行器」を使わない）
- [ ] **Step 4:** Step 2 を再実行する。Expected: `PASS`
- [ ] **Step 5:** `.devcontainer/README.md` の「Claude Code の起動と更新」の節の後（「pi の旧拡張・MCP 設定の移行」の前）に `## 非対話エージェントのランナー（agent-runner）` を足す（C-12）。144 行目の文を「雛形の `requires-python`（`>=3.12`）は変えていない。ルートは agent_runner が Python 3.14 の構文を使うので `>=3.14` にした（#149）。」の趣旨にする
- [ ] **Step 6:** `bash .devcontainer/test-readme.bash` と `bash tests/scripts/test-docs.bash` を実行する。Expected: PASS
- [ ] **Step 7:** commit

### Task 7: 規約・監視の文書とテストの入口

**Files:**
- Modify: `README.md`（「テスト」）、`AGENTS.md`（「エージェント運用」）、`.agents/monitoring-runtimes.md`、`.agents/skills/monitoring-long-tasks/SKILL.md`

テスト: 書かない（文書の変更。代わりに構造の検査を実行する）

- [ ] **Step 1:** `README.md` の「テスト」の pytest の行を `uv run pytest tests/skills .agents/skills .agents/scripts tools` にし、コメントに agent_runner を足す
- [ ] **Step 2:** `AGENTS.md` の「エージェント運用」の最初の箇条の後に、C-12 の規則を 1〜2 項目で足す（runner の起動の形と `interfaces.rst`、入れ子にしない、本物の担当の起動は Issue・Plan に書いた回数に限る）
- [ ] **Step 3:** `.agents/monitoring-runtimes.md` に「agent-runner の同期実行と停止確認」の節を足す（移植元の同名の節を、起動の形を `uv run --project "$PARENT_ROOT" --locked python -m tools.agent_runner run ...` にして写す）。task_watch の節の箇条に「agent_runner を包むときは `--stop INT`、`--escalate-kill` を付けない」を足す。注記の最後の文を「PR 修正ループの使い方は #156 で足す」にする
- [ ] **Step 4:** `monitoring-long-tasks/SKILL.md` の「対象にしてよい worker」の 2 つ目を「専用の使い捨て領域（agent_runner の attempt の worktree、評価用の scratch など）だけに書く worker」にし、`--stop INT` の箇条に「agent_runner はこの作りで、止めた後は result.json の各 attempt の `stop_confirmed` も確かめる」を足す
- [ ] **Step 5:** `bash tests/scripts/test-instructions.bash`、`bash tests/scripts/test-docs.bash`、`uv run pytest .agents/skills/monitoring-long-tasks tests/skills -q` を実行する。Expected: PASS
- [ ] **Step 6:** commit

### Task 8: 全体の検証・レビュー・PR

テスト: 書かない（検証と公開）

- [ ] **Step 1:** 次を実行し、終了コードと件数を記録する。Expected: 全て終了コード 0
  - `uv run pytest tools`
  - `env AGENT_RUNNER_DEPTH=1 uv run pytest tools/agent_runner`
  - `uv run pytest tests/skills .agents/skills .agents/scripts tools`
  - `bash .devcontainer/run-tests.bash`
  - `bash scripts/check-layout.sh`
- [ ] **Step 2:** `superpowers:requesting-code-review` でブランチ全体（`origin/main..HEAD`）をレビューする。致命的な指摘だけを直し、直したら Step 1 の該当するコマンドを再実行する
- [ ] **Step 3:** この Plan の「記録」に、実行した検証・所要時間・逸脱を書いて commit する
- [ ] **Step 4:** `scripts/scan-before-push.sh` で検査した SHA を push し、`gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-149-agent-runner-core` で PR を作る（本文: `Closes #149`、変更概要、Spec の判断と理由、実行方式と理由、検証の結果、所要時間と内訳、既知の重複（C-11））
- [ ] **Step 5:** #149 に PR の URL と状態を書き、予約を解放する（`planning-parallel-issues` の手順）

## 記録

2026-10-18（JST）、`superpowers:executing-plans` で実行した。台帳は `PARENT_ROOT` の `tmp/agents/issue-149.i17bhabl/sdd/progress.md`（worktree にコミットしないファイルを置かないため、スキルの `.superpowers/sdd` は使わなかった）。

- 各 Task は、写したテストがモジュールの無い状態で失敗する（収集エラー）ことを確かめてからコードを写した。submodule の監査の検査（Task 4）と個人設定の導入の検査（Task 6）は、対象の処理を一時的に壊すと失敗することも確かめた
- 全体の検証（Task 8 Step 1、`4f1f020` の前の `39a4f07` で実行。その後の変更は文書だけで、文書の検査を再実行した）:

| コマンド | 結果 |
| --- | --- |
| `uv run pytest tools` | 終了コード 0、758 passed（runner 339、devenv_migration 419）、281 秒 |
| `env AGENT_RUNNER_DEPTH=1 uv run pytest tools/agent_runner` | 終了コード 0、339 passed、59 秒 |
| `uv run pytest tests/skills .agents/skills .agents/scripts tools` | 終了コード 0、1414 passed、465 秒 |
| `bash .devcontainer/run-tests.bash` | 終了コード 0、PASS 32 本、390 秒 |
| `bash scripts/check-layout.sh` | 終了コード 0、PASS |
| `bash .devcontainer/test-pi-migrations.bash`（Task 1） | 終了コード 0、419 passed |
| 文書の修正の後の `test-docs.bash`・`test-instructions.bash`・`test-readme.bash` | PASS 3 本 |

- 最後のブランチ全体のレビュー（別のエージェント、Opus、1 回）: Critical・Important なし、Minor 7 件。影響で格付けし直し、3 件を直した（`4f1f020`）: `AGENTS.md` の規則に adapter が入るまでの扱いを足す、pi で runner に bash ツールの timeout を付けない、`.devcontainer/README.md` の個人設定の場所の説明を実装に合わせる。残りの 4 件は先送り: テストのたびに `/tmp/create-reso-world-agent-runner-*` が約 80 個（約 30 MB）残る（移植元と同じ）、`interfaces.rst`・雛形のコメントがまだ取り入れていないスクリプトを例に挙げる、雛形を丸ごと写すので後の雛形の変更が rebuild まで個人設定に負ける（#150 で扱いを決める）、`.devcontainer/README.md` の `uv run pytest tools` は devenv_migration も含む
- 逸脱と判断（台帳の `Ruling:`）: Task 4 の C-7、Task 5 の `interfaces.rst` への cwd の追記（Review Focus 4）、Task 7 の monitoring-runtimes.md をランタイムごとの起動の表にしたこと（Claude Code の foreground の上限 10 分）、レビューの 3 件の格上げ
- 所要時間（能動、JST）: 準備（Issue・親・移植元の調査、予約、worktree、基準のテスト）約 20 分、Spec・Plan 約 7 分、Task 1〜7 約 9 分（テストの実行を含む）、全体の検証 約 20 分（レビューと並行）、レビューの修正 約 4 分、PR の作成と記録 約 10 分。合計 約 70 分
