# Issue #149: agent_runner の土台（本体・設定の検査・CLI・役割の雛形・テスト補助）を取り入れる

## 管理・実行許可

- 文書管理・実装対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/149（親 #116、ボード `review-automation-board`、子のキー `runner-core`）
- 状態: `draft`。内容の承認（`approved`）は無い。
- 利用者の指示: `/issue-to-pr #149`（issue-to-pr スキルの明示）。許可された範囲は、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成（`Closes #149`）まで続けること。マージ・リリース・本物の担当（モデル）の起動・他者の作業の変更は含まない。下の判断は、確認を取らずに決めたエージェントの判断である。
- 調査基準: 移植先 `3e3c1a3aacdda66678ba37da651e62e483cf06e4`（origin/main。Issue の基準 `84f417f` の後に #141・#146・#145・#159 がマージされている）、移植元 usaturn/agent-workspace `a47b2065fddad76b7475752fd0088af0733de204`（`main`、2026-10-17T19:08Z）。
- 予約: `refs/heads/agent-claims/issue-149` = `a296300a51b1ea586cd1a84e9c51e12e8ba3fc51`（セッション `2c79646a-289a-4ab8-983e-2d29b6d80b53`）。
- 作業場所: `/workspaces/reso-world/.worktrees/issue-149-agent-runner-core`、branch `feat/issue-149-agent-runner-core`。
- 親の方針: #116 の「着手するエージェントへの注意（利用者決定: 2026-10-18）」と、親の Spec `docs/superpowers/specs/2026-10-18-create-reso-world-issue116-review-automation-board-design.md` の D-1〜D-24 に従う。この子に関係するのは、`tools/workspace`・`projects.toml` を入れないこと（移植元の `Registry` などへの依存を持ち込まない）、`tools/test_support` を丸ごと持ち込まないこと（D-8）、ruff・pyright を加えないこと（D-7）、Grok Build を持ち込まないこと（D-3・D-9）。
- Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue149-agent-runner-core.md`

## 意図

後続の子（#150〜#158）が使う、非対話のエージェントのランナーの土台を入れる。`uv run --project "$PARENT_ROOT" --locked python -m tools.agent_runner` の CLI が動き、偽の adapter・偽の CLI だけで、役割ごとの担当・fallback・同じモデルの重複の禁止・停止の確認・結果の受け取りがテストで確かめられる状態にする。

具体的な adapter（Claude Code・Codex・Cursor・Devin・pi・DSH）は #150・#151 が入れる。この子の時点では、どの runtime も「未対応」と表示され、実行は `unsupported` で返る。

## 目標・対象外

目標（Issue の「受け入れ」）:

1. `uv run pytest tools` が通る。本物のモデルを起動しない（偽の adapter・偽の CLI だけ）。
2. adapter が無い runtime は、CLI の一覧で未対応と表示され、実行は秘密情報を出さずに拒否される。
3. `AGENT_RUNNER_DEPTH=1` の中での入れ子の起動を拒否する。
4. `requires-python` の変更の後も、`README.md` の「テスト」の既存の入口が全て通る。
5. `.agents/monitoring-runtimes.md` と `monitoring-long-tasks` に、runner の同期実行と停止の確認（`stop_confirmed`）の使い方がある。
6. テストは `AGENTS.md` の「テストの採用基準」に従う。

公開する仕様（後続の子が使う。名前と形は移植元のまま）:

- `tools.agent_runner`: `run_workflow`、`RunnerError`、models（`Request`・`Receipt`・`Result`・`BatchResult`・`Attempt`・`Assignment`・`Identity`・`Agent`・`Role`・`Workflow`・`Config`・`State`）、`load_config`・`validate_config`・`check_depth`・`resolve_config_path`・`ConfigError`
- `tools.agent_runner.adapters`: `load_adapter`・`Adapter`・`AdapterContext`・`LaunchSpec`・`AdapterOutcome`・`Capabilities`・`UnsupportedRuntime`・`module_name`・`runtime_supported` と固定の名前の表
- `tools.agent_runner.workspace` の監査（`snapshot_checkouts`・`audit_checkouts`・`require_auditable_checkouts`・`CheckoutAuditError`・`git_common_dir`）、`hooks.run_after_run`、`environ.literal_environ`
- `tools.test_support.plugin` の `outside_runner`（`pytest_plugins = ("tools.test_support.plugin",)` で読み込む）
- helper の起動の形 `uv run --project "$PARENT_ROOT" --locked python ...`、`requires-python = ">=3.14"`、pytest の設定（下の C-1）

対象外:

- 具体的な adapter、`dsh_identity.py`・`dsh_sandbox.py`、`tools/agent_runner/runtimes/`、`grok_build`（#150・#151、D-3）
- 雛形の `[agents.*]`・`[workflows.*]`（#150・#151・#153・#155・#157）
- `tools/workspace`・`projects.toml`・`tools/devenv/`（D-5・D-7）
- `.github/workflows/ci.yml`（C-11）
- 本物の担当を起動する確認（D-21。この子では adapter が無いので起動できない）

## 設計

移植元の `tools/agent_runner/` の本体（`adapters/` は `__init__.py`・`skills.py` だけ）と、`tools/test_support/` の `plugin.py`（`outside_runner` だけ）・`texts.py` を写す。コードは移植元のまま写し、次の点だけを変える。

- `models.Runtime` と `adapters._MODULES` から `grok-build` を外す（D-9）
- 既定の出力先の接頭辞を `create-reso-world-agent-runner-` にする（C-4）

runner.py の DSH・Devin に固有の処理（DSH の作業範囲の追記、`sandbox_write_paths`、`dsh/` の HOME の片付けと redact、Devin の `export.json` の redact）は、runner.py の一部なのでそのまま写す。#151 が runner.py を変えずに DSH の adapter を足せるようにするため。

### 判断

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」の順に書く。

- **C-1 pytest の import の方式**
  - 選択: ルートの `pyproject.toml` の pytest の設定を `addopts = "-p no:cacheprovider --import-mode=importlib"`、`pythonpath = [".", "tools/devenv_migration/tests"]`、`testpaths` に `tools` を足す形にする。
  - 別案: (a) prepend のまま、`tools/agent_runner/tests/` などに `__init__.py` を置く。(b) devenv_migration のテストの側（`.devcontainer/test-pi-migrations.bash` に `--import-mode=prepend`、またはテストの import を直す）を変える。
  - 理由: 移植元のテストは importlib mode を前提にしている。#150 で入る adapter のテストは `test_adapter.py`・`fake_cli.py`・`conftest.py` を複数のディレクトリに持ち、prepend では basename が衝突する（a は後続の子に `__init__.py` の追加を強い、Issue の範囲外のファイルも増える）。importlib mode では、#125 の `tools/devenv_migration/tests/` が使う兄弟の import（`from test_pi_mcp_adapter_migration import ...`）が壊れることを、収集で確かめた（`--import-mode=importlib` だけで 1 件の収集エラー、`pythonpath` にそのディレクトリを足すと 419 件を収集）。b は #125 の所有するファイルを変える。`pythonpath` にそのディレクトリを足す形なら、`.devcontainer/test-pi-migrations.bash`（ルートの設定を読む）も `uv run pytest tools` も同じ設定で通る。既存の `.agents` のテストは `importlib.util` でパスから読み込んでいて、importlib mode でも 656 件を収集できる。
  - 委任・停止: 既定。

- **C-2 `requires-python` と uv.lock**
  - 選択: `requires-python = ">=3.14"` にし、`uv lock` で uv.lock を作り直す。依存は変えない（pydantic、dev は pytest・pyyaml）。`.devcontainer/README.md` の「ルートと雛形の `requires-python`（`>=3.12`）は変えていない」の文を、事実に合わせて直す（雛形 `templates/world-project/pyproject.toml` は `>=3.12` のまま）。
  - 別案: `>=3.12` のまま。
  - 理由: 移植元のコードは Python 3.14 の構文（括弧の無い `except A, B:`、PEP 758）を使い、3.12 では読み込めない（D-7）。Dev Container の uv はシステムの 3.14.4 を使う（#122）。README の文は Issue の範囲（「新しい段落」）の外だが、この変更で誤りになる 1 文なので直す。
  - 委任・停止: 既定。

- **C-3 Grok Build**
  - 選択: `Runtime` の型・adapter の名前の表・`interfaces.rst` から `grok-build` を外す。
  - 別案: 未対応として残す。
  - 理由: D-3・D-9 の決定。`check`・`list` は `Runtime` の全ての値を報告するので、残すと常に未対応の行が出る。
  - 委任・停止: 親の決定。

- **C-4 既定の出力先**
  - 選択: `--output-dir` を省いたときの `/tmp` の一意のディレクトリの接頭辞を `create-reso-world-agent-runner-` にする。
  - 別案: 移植元の `agent-workspace-agent-runner-` のまま。
  - 理由: 移植元を参照する名前は、どの checkout の runner が作ったかを誤らせる。移植元でもこの名前を参照するのは runner.py とそのテストだけで、公開の仕様に含まれない。
  - 委任・停止: 既定。

- **C-5 テスト補助**
  - 選択: `tools/test_support/__init__.py`（`texts` の 2 つの定数だけを出す）、`plugin.py`（`outside_runner` だけ）、`texts.py`（内容は移植元のまま。`tools/devenv/.venv` の語だけ移植先の言い方にする）を置く。`README.rst` は写さず、使い方は `plugin.py` の docstring に書く。
  - 別案: 移植元の `README.rst` も写す。
  - 理由: D-8。`README.rst` の大半は写さない `repos.py`・`uv.py` の説明である。
  - 委任・停止: 親の決定（D-8）と既定。

- **C-6 写すテストと写さないテスト**
  - 選択: `tools/agent_runner/tests/` の `conftest.py`・`test_cli.py`・`test_config.py`・`test_environ.py`・`test_process.py`・`test_review_regressions.py`・`test_runner.py`・`test_workspace.py`、`tests/adapters/test_skills.py` を写す。どれも、実際の git の repository・偽の CLI のプロセス・実ファイルで、設定の検査・失敗の分類・期限・停止・redact・監査を実行して確かめる。`test_install.py`・`tools/test_support/tests/test_plugin.py`・`test_texts.py` は写さない。
  - 別案: Issue の一覧のファイルをすべて写す。
  - 理由: 「テストの採用基準」。`test_texts.py` は定数の文字を照合するだけで、ロジックを実行しない。`test_plugin.py` の移植元の内容は写さない `workspace` の fixture の検査で、`outside_runner` は `monkeypatch.delenv` の 1 行である（その効果は、`AGENT_RUNNER_DEPTH=1` を付けた `uv run pytest tools/agent_runner` が通ることで検証手順として確かめる）。`test_install.py` は C-10 のとおり bash の検査に置き換える。
  - 委任・停止: 既定。

- **C-7 test_workspace.py の submodule の検査**
  - 選択: `test_workspace.py` を写し、`create_parent_repo` を使う 1 件（`test_audit_detects_submodule_dirty_content`）だけを、テストの中で `git submodule add` する fixture に置き換える。
  - 別案: 親の Spec D-8 の文のとおり、`test_workspace.py` を写さない。
  - 理由: D-8 は「`create_parent_repo` を使う 3 モジュールのうち `test_workspace.py`（`tools/workspace` を入れない）は持ち込まない」とするが、移植元で `create_parent_repo` を使う `test_workspace.py` は `tools/agent_runner/tests/test_workspace.py` で、検査の対象は `tools/agent_runner/workspace.py`（この子が入れる監査）であって `tools/workspace` ではない。Issue #149 の「変えてよいもの」もこのファイルを挙げ、監査は後続の子（#154）が使う公開の仕様である。監査を検査せずに公開しないため、写す。D-8 の「それらを使うテストは、移植先の構成を作る fixture に置き換える」に沿って、`create_parent_repo` の代わりに必要な形（初期化済みの submodule）だけをテストの中で作る。
  - 委任・停止: 範囲を変えない通常のあいまいさとして、推奨案で決めた。

- **C-8 雛形 `.devcontainer/agent-runner.toml`**
  - 選択: `schema_version = 1` と `[roles.inspect]`・`[roles.implement]`・`[roles.self-review]`・`[roles.fix-check]` だけを置く。値は移植元と同じ（`writes`、`deadline_seconds` は 2700・5400・2700・2700、`result_shape = "json"`、`skills = []`）。コメントは移植先の子の番号に合わせる。`[agents.*]`・`[workflows.*]` は置かない。
  - 別案: 移植元の雛形を全部写す。
  - 理由: D-12 の節の担当。`[agents.*]` は adapter と一緒に #150・#151 が足し、`[workflows.*]` はそれを参照する子が足す。workflow が無い雛形でも `check`・`list` は通り、`run` は `invalid_reference` で止まる。
  - 委任・停止: 親の決定。

- **C-9 `test_shipped_template_passes_check` の扱い**
  - 選択: 「同梱の雛形で `check` が成功し、定義された agent はすべて adapter がある（`supported`）」を検査する。移植元の「agent が 1 つ以上ある」の条件は外す。
  - 別案: このテストを写さない。
  - 理由: この子の雛形には agent が無いので、移植元の条件は満たせない。雛形の TOML・参照の検査と、後続の子が agent を足すときに adapter も足すことの検査は、そのまま意味がある。
  - 委任・停止: 既定。

- **C-10 個人設定の導入と検査**
  - 選択: `.devcontainer/install_beforehand.bash` の 1 段目（`~` の書き込み可能なディレクトリ）の後に `place_agent_runner_config` とその呼び出しを置く（移植元と同じ位置。段の数 `STEP_TOTAL` は変えない）。検査は `.devcontainer/test-install-beforehand.bash` で、関数を取り出して一時 HOME で実行する（`XDG_CONFIG_HOME` が空・相対・絶対、既存の設定と壊れた symlink を変えない、書けない保存先で失敗を返す）。
  - 別案: 移植元の `tools/agent_runner/tests/test_install.py`（同じ検査の Python 版）を写す。
  - 理由: 移植先では `install_beforehand.bash` の検査を `.devcontainer/test-install-beforehand.bash`（`run-tests.bash` が実行する）に置いている。同じ検査を 2 か所に置かない。
  - 委任・停止: 既定。

- **C-11 テストの入口と CI**
  - 選択: `README.md` の「テスト」の pytest の行を `uv run pytest tests/skills .agents/skills .agents/scripts tools` にする（Issue の検証の節のとおり）。`.devcontainer/README.md` の「テストの実行」と `.github/workflows/ci.yml` は変えない。
  - 別案: (a) `tools/agent_runner` だけを足す。(b) ci.yml の skill-tests にも `tools` を足す。
  - 理由: Issue は README の入口を `... tools` と指定している。`tools` には #125 の `tools/devenv_migration/tests`（419 件、約 4 分）も入るので、`run-tests.bash`（`.devcontainer/test-pi-migrations.bash`）と二重に実行することになる（既知の重複として PR に書く）。b は、ci.yml の skill-tests のジョブに bubblewrap が無く、devenv_migration のテストが落ちる。`.devcontainer/README.md` の「テストの実行」は CI と同じコマンドの一覧なので、CI を変えない限り変えない。
  - 委任・停止: Issue の指定と既定。

- **C-12 文書**
  - 選択:
    - `tools/agent_runner/interfaces.rst` は RST のまま写し、題を「汎用の非対話エージェントのランナー v1」にする（`AGENTS.md` は「実行器」を使わない）。移植元の Issue 番号（#560 など）を外し、runtime の一覧から grok-build を除き、起動の形を `uv run --project "$PARENT_ROOT" --locked python -m tools.agent_runner`（リポジトリのルートを cwd にする）に直す。後処理の例の pr-review の helper は #153 が入れることを書く。
    - `.devcontainer/README.md` に「非対話エージェントのランナー（agent-runner）」の節を足す（「Claude Code の起動と更新」の後）。個人設定の場所・導入・上書きの順、`check`・`list`・`run` の形、adapter が無い時点の表示、rebuild で個人設定が雛形から作り直されること（`~/.config/agent-runner` は mount していない。移植元と同じ）、テストの入口を書く。
    - `AGENTS.md` の「エージェント運用」に、非対話で別のエージェントを起動するときは runner を使うこと、入れ子にしないこと、本物の担当を起動する確認は Issue・Plan に書いた回数に限ることを足す。
    - `.agents/monitoring-runtimes.md` に「agent-runner の同期実行と停止確認」の節を足し、task_watch の節に runner を包むときの `--stop INT` を足す。注記の「PR 修正ループと agent_runner の使い方は #116 で足す」を、残りの PR 修正ループ（#156）だけにする。
    - `monitoring-long-tasks/SKILL.md` の「事前宣言した打ち切り」の対象に runner の attempt の worktree を、`--stop INT` の箇条に runner と result.json の `stop_confirmed` の確認を足す。
  - 別案: interfaces.rst を Markdown にする（親の Spec が実装者に任せた点）。
  - 理由: Issue の一覧が `interfaces.rst` を挙げ、#150 の `runtimes/*.rst` も RST で入るので、そろえる。
  - 委任・停止: 既定。

- **C-13 コメントの Issue 番号**
  - 選択: 写すコードとテストのコメントに残る移植元の Issue 番号（`#694`・`#705`・`#601`・`#656` など）を `agent-workspace#694` の形にする。
  - 別案: そのまま。
  - 理由: 移植先では `#694` が create-reso-world の番号に読める。
  - 委任・停止: 既定。

- **C-14 ruff・pyright**
  - 選択: 加えない。移植元のコードの `# pyright: ignore[...]`・`# noqa` のコメントは残す。
  - 別案: dev の依存に足して検証に加える。
  - 理由: D-7 の既定。移植先の検証は pytest と bash のテストだけで、加えると全ての既存のコードが対象になる。
  - 委任・停止: 親の決定。

## 受け入れの検証

- `uv run pytest tools`（目標 1・2・3。2 は `test_cli.py` の check/list・unsupported の run・引数とエラーの漏えいの検査、3 は `test_config.py` と `test_runner.py` の入れ子の検査）
- `env AGENT_RUNNER_DEPTH=1 uv run pytest tools/agent_runner`（runner の担当の中からテストを実行する場合。`outside_runner` が効くこと）
- `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`（目標 4）
- `uv run --project . --locked python -m tools.agent_runner check`・`list`（同梱の雛形と、adapter の無い runtime の表示）
- 文書の目標 5 は、`git diff` で節があることを確かめる（文言のテストは作らない）

## 実装者に任せること

- 写したテストの中で、移植先の環境で不安定なもの（負荷の高いときの時間の依存）が見つかったときの扱い。仕様の意味を保つ最小の修正にとどめ、Plan の記録に書く
- 文書の節の中の書き方
