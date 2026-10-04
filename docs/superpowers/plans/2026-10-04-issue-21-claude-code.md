# Issue #21 Claude Code 設定とランチャーの実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude Code の起動挙動を移植元に揃え、設定隔離と移植先の feature-dev/ccdu を維持して PR を作成する。

**Architecture:** zshrc の alias と ccdd の値のみを変更し、共通 unset 配列と残りの関数を維持する。fake CLI に渡る環境と argv を実行して検証し、onboarding は不採用理由を記録する。

**Tech Stack:** zsh、Bash、Python（Dev Container 検証内では python3、リポジトリの操作では uv）、pytest、GitHub CLI。

**Spec:** `docs/superpowers/specs/2026-10-04-issue-21-claude-code-design.md`

## Global Constraints

- base は `c40a3bdc86c2b7349ec3b7859d5b06af5d81e6e5`、ブランチは `feat/issue-21-claude-code`。PR は main 向けに 1 本、本文に `Closes #21`。
- 編集は zshrc の Claude 節、test-herdr-migration の Claude 検証、CLAUDE.md、README の Claude 節、この Spec/Plan の新規ファイルに限定する。
- feature-dev と ccdu を維持し、settings.local.json を取得・コピー・コミットしない。
- install_beforehand.bash、MCP、pi、スキル、ワールド、ResoLoop、既存 Spec/Plan は編集しない。
- onboarding スクリプトは不採用。実 HOME・実認証は使わず、一時 HOME と fake CLI で検証する。
- slum03 未同期による check-layout と tests/scripts/test-check-layout.bash は既知の範囲外失敗。名前と理由を報告する。

## Review Focus

- zsh の alias 展開は source と同じ構文解析単位だと実行できないことがある。source 後の eval で実際の argv を確認する。
- 空文字、空白、改行、glob を含む引数が壊れないこと。6 関数で argv を JSON にして literal の期待値と比較する。
- 親の認証・モデル・プロバイダ変数の汚染が長い関数名でも漏れないこと。既存 expected_unsets の実行対象を 6 関数へ広げる。
- 認証が空・未設定のとき CLI を呼ばないこと。非空値による ccdu の優先順位を 3 段とも確認する。
- fake CLI が 23 で終了したときランチャーも 23 で終了すること。関数を実行した後も親の設定は変更しない。

## Task 1: ランチャーと起動境界の回帰テスト

**Files:** Modify `.devcontainer/zshrc.txt`、`.devcontainer/test-herdr-migration.bash`。

**Interfaces:** Consumes: source 可能な zshrc、既存 `run_zshrc_code(test_home, code, VAR=value...)` と expected_unsets。Produces: Spec の alias と 6 関数の argv/環境/戻り値を保つ起動処理。

- [ ] Step 1: `test_cc_launcher_arguments_and_models` を追加する。fake claude は argv と選択された Claude 環境変数だけを JSON に記録する。alias の期待値は ccd=`["--dangerously-skip-permissions"]`、ccdo/ccds はそれに `--model` と opus/sonnet。6 関数のモデルは Spec の literal 値、短い名前にだけ権限フラグ。プローブ引数は `['', 'two words', 'line\nbreak', '*.blend', '--model', 'sonnet']`。
- [ ] Step 2: 既存環境隔離検査を 6 関数へ拡張する。`test_cc_launcher_auth_and_exit_status` で、DeepInfra 空/未設定、ccdu キー優先順位、全キー空/未設定、CLI exit 23、親の ANTHROPIC_MODEL 保持を確認する。
- [ ] Step 3: `bash .devcontainer/run-tests.bash .devcontainer/test-herdr-migration.bash` を実行する。Expected: ccd の余計なモデル引数、または ccdo/ccds の欠落、ccdd のモデル差で FAIL。テスト環境のエラーなら修正してから RED を確認する。
- [ ] Step 4: ccd の `--model opus` を外し、ccdo/ccds を追加する。ccdd は fable=`zai-org/GLM-5.3`、opus=`deepseek-ai/DeepSeek-V4.1-Flash`、既定 `--model opus`。それ以外の関数本体・配列は変更しない。
- [ ] Step 5: 同じ個別テストを実行する。Expected: PASS。zsh syntax も既存テストで確認する。
- [ ] Step 6: 2 ファイルを commit する。`feat(claude): align launchers with maatlog-poc`。

## Task 2: Claude 固有の説明と統合検証

**Files:** Modify `CLAUDE.md`、`.devcontainer/README.md` の Claude 関連記述。Validate `.claude/settings.json` と installer（編集しない）。

**Interfaces:** Consumes: Task 1 のランチャー。Produces: ユーザー向け対応表と更新案内、監視ルールとの接続、main 向け PR、#21 の復元済み manifest と完了報告。

- [ ] Step 1: CLAUDE.md の途中出力規約を monitoring-long-tasks の終了コード確認につなげる。`@AGENTS.md`、AskUserQuestion、日本語、ワールド継承を保つ。
- [ ] Step 2: README に ccd/ccdo/ccds と 6 関数のモデル・権限・認証を説明する。再構築前は Claude alias/関数部分を ~/.zshrc に反映して新しいシェルを開く案内を記載する。onboarding 不採用、feature-dev と ccdu 維持を説明する。
- [ ] Step 3: `bash .devcontainer/run-tests.bash .devcontainer/test-herdr-migration.bash .devcontainer/test-install-beforehand.bash`。Expected: 全 PASS、プラグイン集合一致。
- [ ] Step 4: `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`、`uv run pytest tests/skills .agents/skills`、`uv run pytest`。Expected: 配置検査と shell の test-check-layout のみ既知の slum03 失敗、pytest は成功。ログと終了コードを確認する。
- [ ] Step 5: 説明の変更を commit し、ブランチ全体を独立レビューする。重要な指摘は再現テストを RED→GREEN にして修正する。
- [ ] Step 6: ブランチを push し、既存 PR がなければ main 向け PR を作成する。本文に Closes #21、既知の失敗、rebuild/API 未検証を記載する。Issue の状態と PR/検証/作業時間をコメントし、自分の予約 SHA を lease 付きで解放して不存在を確認する。

## Contingency

最初の RED が実際の zsh の構文解析や fake CLI の形式の違いによるエラーなら、仕様の意味を保つ最小修正を ledger に記録する。公開時の応答が失われたらコメント/ref/PR を再取得してから判断し、重複作成しない。新たな main の変更が担当範囲に影響すれば差分を確認して統合する。認証欠落や所有権の喪失時は推測で進めない。

## 自己点検と実行方法

Spec の受け入れ条件 1–3 は Task 1、4–5 は両 Task、6 は実装前の計画公開、7 は Task 2 が担当する。共有インターフェースはランチャーの利用法のみ。推奨は同一セッションの直列実装で、利用者の PR まで進める指示に基づき追加承認待ちを挟まない。
