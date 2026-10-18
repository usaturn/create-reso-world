# DSH Headless Reviewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DSH headless を runner から隔離して起動し、payload と観測した識別情報を回収する。

**Architecture:** agent-workspace `a47b2065fddad76b7475752fd0088af0733de204` の DSH adapter・v4 log reader・scoped bubblewrap helper を #149 の protocol に接続する。停止後の cleanup / redact は既存 runner に任せる。postCreate は固定版 CLI だけを導入する。

**Tech Stack:** Python >=3.14、uv / pytest / pydantic、Bash、bubblewrap、npm、DSH 0.2.0-rc.2。

**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue151-dsh-headless-design.md`（draft）

## 管理・実行許可

- 対象: usaturn/create-reso-world#151、親 #116 の利用者決定と D-1〜D-24 を維持する。
- 状態: draft。利用者の `issue-to-pr #151` で実装・検証・commit・push・main 向け PR を許可。内容の承認ではない。マージ・rebuild は行わない。
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-151-dsh-headless`、branch `feat/issue-151-dsh-headless`。
- 実行方式: inline（executing-plans）。2 Task の小さい移植であり、調査子 2 回とも応答本文なし。最終レビューも独立した結果が取得できなければ自己レビューであることを明記する。

## Global Constraints

- `tools/workspace`・`projects.toml` は導入せず、review-fix-planning の判断基準・三択・修正後の自己レビュー最大 1 回を変更しない。
- #149 の runner / models / adapter 登録 / plugin、#150 の adapter、roles/workflows、AGENTS.md、対話用 DSH は編集しない。
- agent 名は `dsh-ccd` と `dsh-go`、公開関数は Spec の名前・引数・戻り値を保つ。
- dsh は `0.2.0-rc.2`、native scripts は `@deepseek-ai/dsh-subprocess-local,koffi,node-pty` のみ。共有 ~/.dsh、pi-tui、web plugin、pnpm、3080 を足さない。
- テストは fake CLI のみ。文書・一覧・版の固定文言をテストに複写しない。Git fixture は GIT_* を除去した独立した repository。
- 未コミットのログ・ledger・brief は `/workspaces/reso-world/tmp/agents/issue-151.w64st80v/` に置く。スキルの sdd-workspace/task-start/task-done は worktree 内に未コミットのファイルを置くため使わず、この Plan の Task を brief、同ディレクトリの progress.md を ledger とする（AGENTS.md が優先）。

## Review Focus

1. stdout は成功でも durable log が無い: payload を破棄し response_failed。Task 1 の missing-session テストで固定。
2. model route が後で変わる / assistant と違う / session が曖昧: 観測を捏造せず拒否。Task 1 の identity パラメータ検査で固定。
3. bwrap 不在: prepare と helper の両方で本体コマンドを実行しない。Task 1 の missing_bwrap テストで固定。
4. readonly profile に追加 grant が指定される: writable に昇格しない。Task 1 の実 bwrap 検査で固定。
5. npm 成功だが CLI 不在・版不一致: postCreate の後段に進まない。Task 2 の stub 実行で固定。

## Task 1: Adapter・識別・sandbox と実行テスト

**Files:**
- Create: `tools/agent_runner/adapters/dsh.py`、`tools/agent_runner/dsh_identity.py`、`tools/agent_runner/dsh_sandbox.py`
- Create: `tools/agent_runner/tests/adapters/dsh/{fake_cli.py,test_adapter.py,test_identity.py,test_runner.py,test_sandbox.py}`
- Create: `tools/test_support/dsh.py`

**Interfaces:**
- Consumes: #149 の AdapterContext / LaunchSpec / AdapterOutcome / Capabilities、Identity / Receipt、run_workflow、既存 DSH cleanup。
- Produces: `ADAPTER = Dsh()`、`read_session_identity(dsh_home, work_dir, session_id, *, live=False) -> Identity`、`write_session(home, cwd, *, session_id='session-test', provider='observed-provider', model='observed-model', effort='high') -> Path`。
- Tests: 必要。実行の入出力、認証・停止・cleanup・識別・write grant の安全条件を守る。

- [ ] **Step 1:** upstream の実行テストと fake CLI / write_session を先に移植。create_workspace 依存は一時 git repository に置換。fake CLI は正常時に write_session で stdout と同じ sessionId の v4 log を作る。unit fixture も成功時の durable log を用意する。ログ不在 / 重複 / route 変更 / missing bwrap を追加し、成功 payload の自由記述（Unicode/fence）を維持する。
- [ ] **Step 2:** `uv run pytest tools/agent_runner/tests/adapters/dsh tools/test_support` を実行。Expected: adapter/identity/sandbox がまだ無く失敗する。エラー原因と終了コードを記録。
- [ ] **Step 3:** upstream の 3 実装ファイルを移植。prepare は許可 env の PATH（無いとき os.defpath）で bwrap を検索して状態作成前に拒否。collect は成功候補のログ不在を response_failed / None にし、既知の認証・承認・abort を保持。残りの strict parser / v4 reader / scoped helper は source を保つ。
- [ ] **Step 4:** 同じ pytest コマンドを実行。Expected: 全件成功。実 bubblewrap も省略せず動かす。失敗は systematic-debugging で分類して原因を特定する。
- [ ] **Step 5:** `env AGENT_RUNNER_DEPTH=1 uv run pytest tools/agent_runner/tests/adapters/dsh tools/test_support`。Expected: 成功、fake 以外を起動しない。`git diff --check` 後に Task 1 の明示パスを commit（`feat: add isolated DSH headless adapter`）。ledger にテスト・時間を記録。

## Task 2: CLI 導入・雛形・撤去履歴の更新

**Files:**
- Modify: `.devcontainer/install_beforehand.bash`（dsh の導入段と段数のみ）
- Modify: `.devcontainer/test-install-beforehand.bash`（dsh 導入の stub 実行）
- Modify: `.devcontainer/agent-runner.toml`（[agents.dsh-*] のみ）
- Modify: `.devcontainer/README.md`（dsh の案内のみ）
- Modify: `docs/maatlog-poc-porting.md`（dsh の行と R-2/R-3 のみ）

**Interfaces:**
- Consumes: Task 1 の dsh runtime、agent 名、provider 設定。
- Produces: `install_deepseek_harness() -> shell status`、雛形の 2 agent、rebuild 後の実機確認手順。
- Tests: installer のロジックは必要。設定・文書だけの追加テストは不要。runner check / TOML 解析 / diff で代替。

- [ ] **Step 1:** test-install-beforehand に installer 内の関数を抽出して実行するテストを追加。stub npm は要求 package を保存、stub dsh はその版を返す。正常 / npm 失敗 / CLI 不在 / version 失敗 / 版不一致を検査。Expected（変更前のテスト実行）: 関数が無く失敗。実 npm/dsh は起動しない。
- [ ] **Step 2:** install_deepseek_harness を追加し npm の固定版導入、存在、--version の一致を確認。if ! function の fail で必ず停止。段数を実際の step 数に合わせる。
- [ ] **Step 3:** `bash .devcontainer/test-install-beforehand.bash`。Expected: 成功。雛形に source の [agents.dsh-*] だけを追加し、`uv run python -m tools.agent_runner check --config .devcontainer/agent-runner.toml`（CLI help で位置を確認）を実行。Expected: check 成功。
- [ ] **Step 4:** README の全除外を headless CLI のみ導入と区別。maatlog の過去の実測は保持し、#151 の新期待値・rebuild 後未検証を明記。devcontainer.json / initialize.bash は追加要件が無い限り変更しない。
- [ ] **Step 5:** 全体検証を同期実行しログと終了コードを確認。`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`git diff --check`。Expected: 全件成功。Task 2 の明示パスを commit（`feat: install pinned DSH for headless reviewers`）。

## 実行予算

- 能動時間 120 分。基準確認・設計 20、Task 1 35、Task 2 20、全体検証・レビュー 25、公開 20 分。並行 worker 時間は加算しない。
- budget ledger: `/workspaces/reso-world/tmp/agents/issue-151.w64st80v/budget.jsonl`、開始 2026-10-18T14:26Z。
- worker: inline。同期 subagent は usable result が得られず、停止手段・事前宣言の無い子を再起動し続けない。検証は foreground、timeout を付けず完了まで待つ。実装 worker / 検証の強制停止はしない。
- 信頼性の同じ失敗は再試行 1 回まで。安全の失敗は即全体停止。checkpoint は各 Task 終了、50% / 100%、失敗直後。100% で延長せず停止。
- contingency: source fixture を移植先の git fixture に変える、実機は rebuild 後の利用者の確認として分離、共有担当ファイルの変更が必要なら親 #116 に連絡して停止。隔離を外す・期待値だけ弱める・テストを skip する方法は採らない。

## 最終レビュー・公開

- Task 1/2 の共有: `dsh` runtime の agent 名・provider と CLI 引数が一致すること。#153 が追加する workflow に先回りしない。
- ブランチ全体を別の確認パスとしてレビュー。独立 subagent の結果が得られなければ自己レビューと記録し、無かった独立レビューを捏造しない。重要な問題は再現 RED→GREEN で修正、Minor は記録。
- Issue が open、予約が自分、競合 PR/branch が無いことを再確認。PARENT_ROOT の scan-before-push.sh で HEAD を検査し、その SHA だけを feature branch に push。main 向け PR を 1 件作る（Closes #151、Spec の決定理由、inline の理由、実測した検証、時間、実機未検証を記載）。マージしない。
- Spec / Plan は draft のまま PR で公開。公開した commit から別ディレクトリに取り出し、SHA-256 / バイト数を照合。#151 に manifest、PR、planning: ready / implementation: in-progress（マージ・rebuild 後実機待ち）を書き、自分の claim だけを解放。実装まで同じ run で進めたため planning-only の handoff 2 ファイルは作らない。

## 実行記録

- 準備: 必要な GitHub の権限・rulesets 等のプラン制限、Actions 無効、先行完了と main 包含、競合不在、ignore、clean worktree を確認。
- 基準 `uv run pytest tools`: 758 passed、228.49 秒、終了コード 0（`baseline.log`）。
- 設計・Plan の自己確認: Spec の範囲を Task 1/2 で網羅。観測値と要求値の区別、既知の診断の保持、cleanup の所有者、workflow/個人設定の注意を一致させた。
