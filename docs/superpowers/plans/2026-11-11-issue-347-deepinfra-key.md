# Issue #347 DeepInfra キーガード実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Task の実装は issue-to-pr の `implement_task.py` で指定 runner へ逐次依頼する。

**Goal:** DeepInfra の Claude Code ランチャーが空白などの無効なトークンで起動しないようにする。

**Architecture:** 既存の Ollama と同じ英数字ガードを 2 つの DeepInfra 関数に追加する。既存の隔離テストと README を合わせる。

**Tech Stack:** zsh、bash、隔離 HOME/PATH と stub Claude。

**Spec:** `docs/superpowers/specs/2026-11-11-issue-347-deepinfra-key-design.md`。

## 管理・制約

- 状態: `draft`。利用者の `#347 --merge --spec-review pi_deepinfra_deepseek4-flash_high --implement pi_deepinfra_deepseek4-flash_high --assign inspect=devin_swe2_max,pi_openai-codex_gpt6-sol_max --assign implement=pi_deepinfra_deepseek4-flash_high` は実行許可であり、内容の承認ではない。
- 実キー・実 API・実 HOME の認証情報は使わない。他ランチャーとその優先順位、モデル・送り先・env 隔離・権限省略・引数・終了コードは変えない。
- テストは AGENTS.md の S/F∩S のみ。Python は `uv` を使う。コミットしないファイルは親 checkout の `tmp/agents/` に置く。

## 受け入れ基準と要件照合

Linux Dev Container の zsh/bash、隔離 HOME/PATH、stub Claude を使う。`ccdd` と `ccddg` のそれぞれについて ASCII 空白・NBSP・BOM を含む代表の無効値で終了コード非 0、キーの値を表示せず、Claude を起動しない。未設定・空・英数字を含まない値も拒否し、正常なキーでは従来の接続先と認証を維持する。通常名はそれぞれ同じ関数本体を使用し、既存の成功側の接続先テストで検証する。旧 `ccdu`、`ccdgo`、`ccdol` の挙動変更、実通信は対象外。

Task 1 が拒否・正常側と README を担当する。controller が実装後の差分と既存の正常側テストを照合し、共有条件（同じキー判定と両関数の接続先・README の意味）を統合確認する。実装前の RED と実装後 GREEN、全テスト・layout で観測する。入力ごとに同じ守りの組合せを増やさない。

## Task 1: DeepInfra ガードと利用案内

**Files:**
- Modify: `.devcontainer/zshrc.txt`
- Modify: `.devcontainer/test-herdr-migration.bash`
- Modify: `.devcontainer/README.md`

**Interfaces:** `claude-deepinfra` / `ccdd` と `claude-deepinfra-glm` / `ccddg` は同じ zsh 関数本体をそれぞれ共有し、`DEEPINFRA_TOKEN` を入力とする。

- [ ] 既存の stub と隔離 fixture を使い、上記受け入れ基準の代表無効入力について両関数本体の拒否を検査する S の回帰テストを追加する。正常側は既存の接続先・env テストを使う。出力に入力値が含まれないことも検査する。
- [ ] `bash .devcontainer/test-herdr-migration.bash` を実装前に同期実行し、追加テストが旧コードで失敗することを記録する。
- [ ] 両関数の `env` より前に `[[ ${DEEPINFRA_TOKEN:-} != *[A-Za-z0-9]* ]]` を使うガードと値を表示しない固定エラーを追加する。有効なキーの受け渡しとその他の設定を維持する。
- [ ] `.devcontainer/README.md` の第三者プロバイダ説明と API トークン節に DeepInfra の検査条件を正確に記す。Pi の検査とは区別する。
- [ ] `bash .devcontainer/test-herdr-migration.bash` を同期実行して成功を確認し、`git diff --check` と差分を確認する。担当が RED/GREEN と所要時間を報告する。
- [ ] `git add .devcontainer/zshrc.txt .devcontainer/test-herdr-migration.bash .devcontainer/README.md` と `git commit -m 'fix: reject invalid DeepInfra launcher tokens'`。

テストが必要な理由: 無効キーを通すと動作は成功して見え、保存済み OAuth を第三者に送るおそれがある（S）。文書の固定値やエラー文言の照合は不要（F/L）。

## 統合と公開

controller が Task の仕様・品質レビューと全体レビューを行う。最後の clean HEAD で `env -u CODEX_THREAD_ID bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、必要な構文と差分確認を実施し、ログ・HEAD・base・終了コードを保存する。`CODEX_THREAD_ID` を外すのは、隔離 HOME に実セッション ID が残って cleanup fixture が不正に実セッションを探す既存の問題を避けるため。変更前の無修飾実行の失敗と、2 個別テストが変数除去で成功した事実を記録する。秘密情報検査後、検査した SHA を push し、PR を作成。`--merge` のループで指定レビュアー・担当を使い、finalize のみでマージする。

## 実行予算

全体 360 分を目安とする。準備・Spec 30 分、実装とレビュー 100 分、検証・公開 45 分、最大 3 サイクルのレビュー（各 45 分＋計画・修正）185 分。runner の役割期限は Spec レビュー 45 分・実装 90 分、各ループレビュー 45 分。外部 runner は停止と結果を確認するまで待ち、監視用の追加中断は設けない。信頼性の同一失敗は再試行 1 回まで、安全の失敗は全体停止。phase 境界・50%・100%・worker 失敗直後に checkpoint を記録する。範囲縮小や別担当の暗黙の代行はせず、必要なら未完了として報告する。

## contingency（代替策）

RED で fixture の実挙動が想定と違えば、安全条件を維持した最小のテスト修正を ledger に記録する。仕様の意味や安全境界が変わる場合、runner の failed、停止未確認、base 移動、検証を解消できない場合は停止する。実装担当の失敗を controller が代行しない。既存無関係の検証失敗は原因と切り分け結果を明記し、成功と偽らない。
