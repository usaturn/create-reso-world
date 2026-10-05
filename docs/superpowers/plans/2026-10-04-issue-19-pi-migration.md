# Issue #19 pi 拡張構成の移行 Implementation Plan

- 文書管理／対象リポジトリ: `usaturn/create-reso-world`
- 対象Issue／PR: #19／#27
- 検証したコードHEAD: base `c40a3bdc86c2b7349ec3b7859d5b06af5d81e6e5`、初回実装 `6f0cd9ee9d04da2f177c0ab97551945583b78d49`
- 状態: completed（初回実装と PR 作成を完了。以降のレビュー修正は `docs/superpowers/specs/2026-10-04-pr27-pi-migration-round2-review-fixes-design.md` を参照）
- 実行許可: Issue #19 の作業時のユーザ指示「推奨案で進めて、途中で止めずに PR まで作成して」
- 内容承認: 個別のコミット済み版の内容承認は確認できない
- 関連Spec: `docs/superpowers/specs/2026-10-04-issue-19-pi-migration-design.md`
- 手順のチェックボックスは作成時のまま残している。実施の記録は PR #27 と Issue #19 のコメントにある。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 廃止した pi 拡張を復活させず、組み込み MCP と移植元の拡張構成へ移行して PR を作る。

**Architecture:** 既存 Python cleanup に対象・設定修正・バックアップを追加する。pi に npm 依存の整合を委ね、provisioning は cleanup の成功後に8種の拡張を導入する。既存 models は保持する。

**Tech Stack:** Python 標準ライブラリ、uv、bash / zsh、pi CLI、npm、unittest。

**Spec:** `docs/superpowers/specs/2026-10-04-issue-19-pi-migration-design.md`

## Global Constraints

- `.worktrees/issue-19-pi-migration` の `feat/issue-19-pi-migration`、base `c40a3bdc86c2b7349ec3b7859d5b06af5d81e6e5` で作業する。
- `uv run --no-project .devcontainer/cleanup_pi_mcp.py` と PI_CODING_AGENT_DIR の解決・リンク拒否を維持する。
- 認証・既存 models.json・native MCP・無関係な packages / extensions を保持する。
- Context7 を pi に再導入せず、スキル・ランチャー・Claude・ワールド・ResoLoop を編集しない。
- 初回の空環境や既に整理済みならバックアップや settings を新設しない。
- STEP_TOTAL=25 を維持する。Dev Container rebuild は #22 の担当。

## Review Focus

- 単独登録が無く npm transitive helper だけが残る場合：distill 撤去後の npm 整合で消えること。
- -builtin:mcp だけが残る BOM settings：必要なフィルター以外は保持し再実行でバイト列が変わらないこと。
- 変更途中の pi remove 失敗：バックアップが残り、設定フィルターと新拡張導入に進まないこと。
- 不正 extensions と symlink backup 保存先：最初の撤去前に停止すること。
- ワールド cwd：共有 .pi から builtin と MCP を読み、移植元専用 skill / Context7 を読み込まないこと。

---

### Task 1: 安全な旧拡張・設定移行

**Files:** `.devcontainer/cleanup_pi_mcp.py`、`.devcontainer/tests/fake_pi_packages.py`、`.devcontainer/tests/test_pi_mcp_cleanup.py`、`.devcontainer/test-pi-mcp-cleanup.bash`。

**Interfaces:** Consumes: PI_CODING_AGENT_DIR と pi remove npm:<name> --no-approve。Produces: 5種の撤去と -builtin:mcp フィルターを行う既存 cleanup()、理由付き非ゼロ終了、migration-backups/pi-retired-*。

- [ ] Step 1: 既存 KEPT fixture の pi-distill を無関係な keep-extension に変更し、REMOVED に distill / tool-display / i18n を追加。settings-only フィルター、初回・再実行、無効 extensions、全バックアップのバイト列と失敗保存、リンク保存先拒否、update --extensions、実 npm のローカル distill dependency fixture をテストに追加する。
- [ ] Step 2: `bash .devcontainer/test-pi-mcp-cleanup.bash` を実行。Expected: 未撤去の対象、残る -builtin:mcp、未作成バックアップで FAIL。provisioning 更新は Task 2 で行うので当該テストだけ後段に分離する。
- [ ] Step 3: PACKAGES を5種へ拡張。`extension_entries(settings: dict, path: Path) -> list` で型を事前検証。`backup_storage(agent: Path) -> Path` で settings と MANIFESTS のバイト列を固有0700ディレクトリに保存。`enable_builtin_mcp(agent: Path) -> None` で -builtin:mcp だけを取り除き mode を保持して置換保存。全事前検査後・pi remove 前にバックアップを実行する。fake の update は登録と npm マニフェストから installed package を復元する。
- [ ] Step 4: cleanup の unittest（provisioning 2件を除く）を実行。Expected: 全件 PASS。既存 real npm 回帰も保持する。
- [ ] Step 5: Task 1 の対象ファイルを commit `fix: safely retire legacy pi extensions`。

### Task 2: provisioning と共有設定の移植

**Files:** `install_beforehand.bash`、`setup_pi.zsh`、`pi-models.json`、`zshrc.txt`、`setup_pi_tool_display.py`（削除）、`.pi/settings.json` / `.pi/mcp.json`（新規）、`.pi/APPEND_SYSTEM.md`、`test-install-beforehand.bash`、`tests/scripts/test-agent-config.bash` / `test-instructions.bash`、`.devcontainer/README.md`。

**Interfaces:** Consumes: Task 1 の cleanup CLI。Produces: cleanup 後の8種の拡張導入、extensions=["+builtin:mcp"]、Context7 を除いた google-dev-knowledge HTTP MCP。

- [ ] Step 1: fake provisioning テストを新雛形と既存状態で2回実行し、update --extensions 後も5対象が消えたことを検査。pi project 設定をルートと4ワールド cwd で読み、MCP server / env 参照が一致することを検査。setup_pi.zsh を隔離 HOME とダミー token で実行し既存独自 provider を保持することを検査する。install 順序と旧 helper / env / provider 参照の除去を既存検査へ追加する。
- [ ] Step 2: 個別 provisioning / agent-config / instructions / install テストを実行。Expected: distill 再導入と未追加の project 設定で FAIL。
- [ ] Step 3: pi-distill 導入行と tool-display 呼び出し・ファイル、deepinfra-distill 雛形、setup の廃止 provider / echo、zsh の PI_* と APPEND_SYSTEM の該当記述を除去する。新規設定に +builtin:mcp と Google MCP のみを書く。pi-lens ignore は変更しない。README に既存 models 保持・バックアップ・project trust・廃止拡張の移行を説明する。
- [ ] Step 4: `bash .devcontainer/test-pi-mcp-cleanup.bash` と `bash .devcontainer/run-tests.bash .devcontainer/test-install-beforehand.bash tests/scripts/test-instructions.bash tests/scripts/test-agent-config.bash`。Expected: 全件 PASS。
- [ ] Step 5: Task 2 の対象ファイルを commit `feat: migrate pi to builtin MCP without distillation`。

### Task 3: 公開・全体検証・PR

**Files:** この Spec / Plan、新規 handoff 対と復元 manifest（main checkout の tmp/docs_draft/claude_handoffs、追跡外）。

**Interfaces:** Consumes: #19 予約 SHA、Task 1 / 2 と全体検証結果。Produces: 復元可能な4ファイルと main 向け PR1本、本文 Closes #19。

- [ ] Step 1: 実装前に Spec / Plan を自己点検し commit。agent-handoff schema_version=2 の対を作り、#19 に全文を公開。manifest から空ディレクトリへ4ファイルを復元し SHA-256 / バイト数 / JSON 必須項目 / sources を照合する。planning: ready を公開して実装を継続する。
- [ ] Step 2: `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`、`uv run pytest tests/skills .agents/skills` を実行。Expected: slum03 未同期による既存配置検査2件だけが失敗し、他は PASS。結果をベースラインと比較する。
- [ ] Step 3: whole-branch の独立レビューを1回実行。重大な指摘は RED→GREEN で修正し該当スイートを再実行。scope、persona、残留、全明示条件を実際の diff / テスト結果で監査する。
- [ ] Step 4: feature branch を push し既存 PR があれば再利用、なければ main 向け PR を作成。CI と PR head を確認し、#19 に PR・検証・所要時間を記録。マージ前なので implementation: in-progress のまま。
- [ ] Step 5: 保存した SHA の exact lease で予約を解放し remote ref 不在を確認。PR を報告する。マージは行わない。
