# Issue #397 ccda（Token Plan）ランチャー 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`（issue-to-pr の実行許可で進める。内容の承認は得ていない）

**Goal:** `.devcontainer/zshrc.txt` に `claude-alibaba` / `ccda` を足し、テストと案内を本リポジトリの形で更新する。

**Architecture:** 既存の `ccdol` と同じ構造の zsh 関数を足し、共有の `cc_launcher_unsets` に `MAAS_ANTHROPIC_TOKEN` を加える。守りは既存の stub の `claude` を使う bash テストに入力を足し、キーの確認だけ代表 1 件を新設する。

**Tech Stack:** zsh（ランチャー）、bash（テスト）、python3（テスト内の stub。`.devcontainer/` 配下なので AGENTS.md の例外）、Markdown。

**Spec:** `docs/superpowers/specs/2026-11-11-issue-397-ccda-token-plan-design.md`

## Global Constraints

- 接続先: `https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic`
- 認証: `ANTHROPIC_AUTH_TOKEN="$MAAS_ANTHROPIC_TOKEN"` だけ。`ANTHROPIC_API_KEY` は子に渡さない
- モデル: fable・opus `qwen4-max-preview`、sonnet・haiku `qwen3.8-flash`。`[1m]` を付けない
- `ENABLE_CLAUDEAI_MCP_SERVERS=false`、`CLAUDE_CODE_EFFORT_LEVEL=max`、`CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536`、起動は `claude --model opus "${opts[@]}" "$@"`
- `ccda` だけが `--dangerously-skip-permissions` を付ける。`claude-alibaba` は付けない
- キーの確認は `[[ ${MAAS_ANTHROPIC_TOKEN:-} != *[A-Za-z0-9]* ]]`（移植元の `cc_launcher_require_key` は使わない）。値を表示しない
- テストは AGENTS.md の「テストの採用基準」の S・F∩S だけ。実キー・課金 API をテストで使わない
- 対象外: ステータスライン、agent-runner、Pi・Codex、既存ランチャーのモデル、利用者の settings・env ファイル、過去の Spec・Plan、`docs/maatlog-poc-porting.md` の表と R-4・R-9 の本文

## 受け入れ基準

- 動作環境: Dev Container の zsh（`~/.zshrc` は `.devcontainer/zshrc.txt` の写し）。自動テストは stub の `claude` と隔離した HOME で、実キー・課金 API を使わない
- 実入力: ランチャーの後ろの引数（`-p`・空白を含むプロンプト・`--model sonnet`・`--output-format json`）がそのまま `claude` に渡る。tier を指定しなければ opus（`qwen4-max-preview`）で起動する。キーの入力は ASCII の空白・NBSP（U+00A0）・BOM（U+FEFF）だけの値を含む
- 防御範囲:
  - 対象: `MAAS_ANTHROPIC_TOKEN` が未設定・空・ASCII の英数字を含まないとき、値を表示せず非 0 で止まり `claude` を起動しない。親シェルの `ANTHROPIC_*`・各プロバイダのキー（`MAAS_ANTHROPIC_TOKEN` を含む）が `ccda`・`ccdd`・`ccddg`・`ccdol`・`ccdgo` の子に届かない（`ccda` の子の `ANTHROPIC_AUTH_TOKEN` はこのキー）。`ccda` だけが `--dangerously-skip-permissions` を付け、`claude-alibaba` は付けない。送り先は Token Plan の URL で、`ENABLE_CLAUDEAI_MCP_SERVERS=false`
  - 対象外（反例）: 利用者が `env` などで直接 `claude` を起動した場合の漏れ、`~/.claude/settings.json` の `env` による上書き、英数字を 1 文字でも含む誤ったキー（API が 401 を返す）、ステータスライン
- 実 API: `ccda -p "1+1 の答えを数字だけで答えて" --model <tier> --output-format json` を fable・opus・sonnet・haiku で 1 回ずつ実行し、終了コード 0 で、`modelUsage` のモデルが表のとおりになる。指定のモデルが無い・応答しないときは別のモデルに替えずに止まり、実際のエラーを報告する
- `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` が通る

## Review Focus

1. 親シェルの `MAAS_ANTHROPIC_TOKEN` が他の 4 つのランチャーの子に残る → `test_cc_launcher_env_unsets` の入力元キーの不在の確認（Task 1）
2. `ccda` の子に `ANTHROPIC_API_KEY` が残る（親の値・関数の誤設定）→ 送り先のテストの `ANTHROPIC_API_KEY is None`（Task 1）
3. NBSP・BOM だけのキーで起動する → `test_alibaba_launcher_requires_key`（Task 1）
4. `claude-alibaba` に省略のフラグが付く → 送り先のテストの短縮名の判定（Task 1）
5. 「既存環境の更新」を #397 の後に読んだ人がキーや新しい `ccda` を消す → Task 2 の文書の確認手順（テストは F なので書かない）

## 要件・Task・検証の対応

| Spec の条件 | Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| ランチャーの値・省略フラグ・送り先・認証の経路 | 1 | stub の argv・env | `test_cc_launcher_destination_and_exit_status` |
| unset の一覧と漏れ防止 | 1 | `expected_unsets` の完全一致、子の env に `POLLUTED_`・入力元キーが無い | `test_cc_launcher_env_unsets` |
| キーの確認 | 1 | 非 0、stub が起動しない | `test_alibaba_launcher_requires_key` |
| 実 API の 4 tier | controller（Task 3） | 終了コード 0、`modelUsage` のモデル | 実行ログ |
| README・移植記録 | 2 | 書き換えた箇所 | `git diff` の確認、`test-readme.bash`、`check-layout.sh` |

共有する条件: ランチャーの名前・変数名・URL・モデル ID を Task 1（コード）と Task 2（文書）が共有する。controller が Task 2 の後に、README の値と `zshrc.txt` の値の一致を `git diff` で照合する（統合担当は controller）。

---

### Task 1: ランチャーとテスト

**テスト:** 要る（S・F∩S。秘密情報の送り先・漏れ・権限の省略は壊れてもエラーにならない）。

**Files:**
- Modify: `.devcontainer/zshrc.txt`（`cc_launcher_unsets` とその前のコメント、`ccdgo` の後に新しい関数）
- Modify: `.devcontainer/test-herdr-migration.bash`（`test_cc_launcher_env_unsets`、`test_cc_launcher_destination_and_exit_status` とその前のコメント、新しい `test_alibaba_launcher_requires_key`、末尾の実行の一覧）

**Interfaces:**
- Produces: zsh 関数 `claude-alibaba` / `ccda`、`cc_launcher_unsets` の `-u MAAS_ANTHROPIC_TOKEN`

- [ ] **Step 1: テストを先に変える**
  - `test_cc_launcher_env_unsets`: `expected_unsets` に `MAAS_ANTHROPIC_TOKEN` を（辞書順の位置に）足す。`env_args` に `MAAS_ANTHROPIC_TOKEN=fake-maas`、`POLLUTED_` を置かない `case` に `MAAS_ANTHROPIC_TOKEN` を足す。2 つの `for fn in ccdd ccddg ccdgo ccdol` に `ccda` を足し、`for source_key` の一覧に `MAAS_ANTHROPIC_TOKEN` を足す。`assert_contains "${dump_dir}/ccda.log" '^ANTHROPIC_AUTH_TOKEN=fake-maas$'` を足す。テストの前のコメントの短縮名の一覧に `ccda` を足す
  - `test_cc_launcher_destination_and_exit_status`: ループに `ccda claude-alibaba`、`run_zshrc_code` の環境に `MAAS_ANTHROPIC_TOKEN=fake-maas` を足す。Python で `skip` を付ける名前に `"ccda"` を足し、`alibaba = name in ("ccda", "claude-alibaba")` の分岐で次を確かめる

    ```python
    assert env["ANTHROPIC_BASE_URL"] == "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic", (name, env)
    assert env["ANTHROPIC_AUTH_TOKEN"] == "fake-maas", (name, env)
    assert env["ANTHROPIC_API_KEY"] is None, (name, env)
    ```

    上のコメントの短縮名の一覧に `ccda` を足す
  - `test_alibaba_launcher_requires_key` を `test_ollama_launcher_requires_key` と同じ形で足す（HOME は `${TEST_ROOT}/home-alibaba-key`、ログは `${TEST_ROOT}/alibaba-key-claude.log`、`ccda probe`、`MAAS_ANTHROPIC_TOKEN=$' \xc2\xa0\xef\xbb\xbf'`、失敗文は `ccda must fail when MAAS_ANTHROPIC_TOKEN is blank` と `ccda must not start claude when MAAS_ANTHROPIC_TOKEN is blank`）。コメントは `# S:` で始め、損害（ガードが外れても起動は成功し、claude.ai の認証情報が `maas.aliyuncs.com` に送られる）と、この 1 件で `-z` と `[[:space:]]` の誤りの両方が分かること、正しいキーで起動する例は送り先のテストにあることを書く。末尾の実行の一覧の `test_deepinfra_launcher_requires_key` の後に足す

- [ ] **Step 2: 失敗を確かめる**

  Run: `bash .devcontainer/test-herdr-migration.bash`
  Expected: 終了コード 1。`cc_launcher_unsets must match expected_unsets exactly` で止まる（まだ関数も一覧も無い）

- [ ] **Step 3: ランチャーを実装する**
  - `cc_launcher_unsets` の `-u OPENCODE_GO_API_KEY` の後に `-u MAAS_ANTHROPIC_TOKEN`。前のコメントの「（ccdd / ccddg / ccdgo / ccdol）」を「（ccdd / ccddg / ccdgo / ccdol / ccda）」にする
  - `ccdgo` の関数の後（`function cod()` の前）に `function claude-alibaba ccda ()` を足す。値は Global Constraints のとおり（`local fable=qwen4-max-preview` などの 4 つの local）。キーの確認と案内文は Spec のとおりで、`ccdol` と同じ 4 行の理由のコメントを付ける。関数の前のコメントに、出典（#397、移植元 usaturn/agent-workspace#923）、Bearer の `ANTHROPIC_AUTH_TOKEN` だけを渡す理由（移植元の実測で Bearer が 200。`ANTHROPIC_API_KEY` だけだと承認まで claude.ai の OAuth が送られうる）、`[1m]` を付けない理由（`/v1/models` が 404 で 1M の根拠が無い）を書く

- [ ] **Step 4: 通ることを確かめる**

  Run: `bash .devcontainer/test-herdr-migration.bash`
  Expected: 終了コード 0、`PASS: herdr Dev Container migration`

- [ ] **Step 5: ガードが効いていることを一時的に確かめる（commit しない）**

  キーの確認の `if` を一時的に `[[ -z ${MAAS_ANTHROPIC_TOKEN:-} ]]` に変えて Step 4 を実行し、`ccda must fail when MAAS_ANTHROPIC_TOKEN is blank` で失敗することを確かめてから元に戻す（`git diff` で戻ったことを確かめる）

- [ ] **Step 6: commit**

  ```bash
  git add .devcontainer/zshrc.txt .devcontainer/test-herdr-migration.bash
  git commit -m "feat: add ccda launcher for Alibaba Token Plan (#397)"
  ```

### Task 2: 案内と移植の記録

**テスト:** 要らない（文書の文言は F）。代わりに `bash .devcontainer/test-readme.bash`、`bash scripts/check-layout.sh`、`git diff` の確認。

**Files:**
- Modify: `.devcontainer/README.md`
- Modify: `docs/maatlog-poc-porting.md`（「### Grok Build・`ccda`」の表の直後に 1 文）

**Interfaces:**
- Consumes: Task 1 のランチャー名・変数名・URL・モデル ID（Global Constraints の値）

- [ ] **Step 1: README を書き換える**

  Spec の「ドキュメント」の `.devcontainer/README.md` の各項目をすべて反映する。移植元の README の節の本文は `/workspaces/reso-world/tmp/agents/issue-397.07kekhs0/upstream-925.diff` の `.devcontainer/README.md` の部分にある。新しい節は「### OpenCode Go のモデルで Claude Code を起動する（#368）」の節の終わり（「## 非対話エージェントのランナー（agent-runner）」の直前）に `### Alibaba Cloud Model Studio の Token Plan で Claude Code を起動する（#397）` として置き、小見出しは `####` にする。起動の例は `ccdol` の節と同じく `read -rs 'MAAS_ANTHROPIC_TOKEN?Model Studio API key (非表示): ' && export MAAS_ANTHROPIC_TOKEN` の形にし、キーの値を例に書かない。移植元の実測は「移植元（usaturn/agent-workspace#923）が 2026-11-11 に Claude Code 2.1.322 で確かめた」と明記する。判定の説明は「ASCII の英数字を 1 文字も含まない（NBSP・BOM などの Unicode の空白だけを含む）」と書く

- [ ] **Step 2: 移植の記録に注記を足す**

  `docs/maatlog-poc-porting.md` の「### Grok Build・`ccda`」の表の直後に、Spec の注記の 1 文を足す。表と R-4・R-9 は変えない

- [ ] **Step 3: 検証**

  Run: `bash .devcontainer/test-readme.bash && bash scripts/check-layout.sh`
  Expected: どちらも終了コード 0
  Run: `git diff --stat` と `git diff -- .devcontainer/README.md`
  Expected: README・移植の記録の 2 ファイルだけ。README に「`ccda`（`claude-alibaba`）も置かない」「もう使わない」「`MAAS_ANTHROPIC_TOKEN` を削除し」「`unset MAAS_ANTHROPIC_TOKEN` で外す」「`ccda`（`claude-alibaba`）の関数…も削除する」の旧い指示が残らない（`grep -n 'MAAS_ANTHROPIC_TOKEN\|ccda' .devcontainer/README.md` で 1 件ずつ確かめる）

- [ ] **Step 4: commit**

  ```bash
  git add .devcontainer/README.md docs/maatlog-poc-porting.md
  git commit -m "docs: document ccda Token Plan launcher (#397)"
  ```

### Task 3: 統合の確認（controller）

**テスト:** 追加しない。全体の検証と実 API の確認。

- [ ] **Step 1:** `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` が終了コード 0
- [ ] **Step 2:** README の URL・モデル ID・変数名・起動名が `zshrc.txt` と一致する（`git diff` の照合）
- [ ] **Step 3: 実 API（各 tier 1 回、費用がかかるので再実行しない）**

  `zshrc.txt` の `cc_launcher_unsets` から `ccda` の関数の終わりまでだけを zsh に読み込み（`~/.zshrc` の herdr の起動などを避ける）、実の HOME で次を tier ごとに 1 回実行する。ログは `SESSION` の下に置き、キーの値を記録しない。

  ```bash
  ccda -p "1+1 の答えを数字だけで答えて" --model <tier> --output-format json
  ```

  Expected: 4 つとも終了コード 0、`is_error: false`、`modelUsage` のモデルが fable・opus → `qwen4-max-preview`、sonnet・haiku → `qwen3.8-flash`。違うモデル・エラーのときは再実行・モデルの変更をせず、実際の出力を PR に書いて停止の判断をする

## 実行方式

`implement_task.py check` が `self=false`（`--implement pi_opencode-go_deepseek4-flash_max`、fallback 無し）なので、Task 1・2 を `implement_task.py run` で順に 1 つずつ依頼する（並行しない）。Task 1 の取り込みの後に Task 2 を依頼する（Task 2 は Task 1 の値を文書にするため）。各 Task の後に controller が関連テストを実行し、SDD の Task のレビューを行う。Task 3 は controller が行う。

## 実行予算

- 全体の能動時間: 300 分（PR 修正ループを含む。#368 の実績と、ループの上限 3 サイクル ×（レビューの期限 45 分＋計画・修正 20 分））
- phase の目安: 準備・Spec・Spec レビュー・Plan 40 分、Task 1 30 分、Task 2 30 分、統合・実 API・PR 20 分、ループ 180 分
- worker: `implement` の役割の期限は 90 分（runner の既定）。無進捗の打ち切りは runner の既定に従う
- 再試行: 同じ失敗の再試行は 1 回まで（`retry`・`rejected` を含む依頼し直しは Task ごとに 1 回）。実 API は再実行しない
- checkpoint: 各 Task の後、予算の 50%（150 分）・100%、担当の失敗の直後
- 縮小・切り出し・方法変更の候補: README の新しい節を要点（表・起動・確認・未確認）に絞る。実 API を確かめられなければ未確認として PR に書く。担当が 2 回失敗したら停止して利用者に担当の変更を求める（self で代行しない）

## contingency（代替策）

- 最初の RED が `expected_unsets` の照合以外で止まる（stub・HOME の前提が違う）: 原因を確かめ、テストの意味（漏れ・送り先・起動しないこと）を保つ最小の修正を ledger に記録して続ける。意味が変わるなら停止する
- 実 API でモデルが無い・401・応答しない: 別のモデル・別の接続先に替えず、実際のエラーを PR と Issue に書く。ランチャーの値は Issue の表のままにし、変更が要るなら利用者の裁定を待つ
- 担当が `failed`・上限の `retry` / `rejected`: その Task で停止して報告する（self で引き取らない）

## Spec レビューの記録

- helper（`review_spec.py`）で外部の担当が実施。担当は `pi_opencode-go_deepseek4-flash_max`（`--spec-review` で利用者が指定、fallback 無し）。`actual_agent` も同じで、runner が観測したモデルは `opencode-go` の `deepseek-v4.1-flash`（effort `max`）。1 回、483 秒
- `review_id` `0ed0b7794cea4f4792fa63477334d39d`、reviewed の Spec SHA-256 `142425c17fc127e3a115d2578821478c1eeb8feb21e021a5be7256c32b113eee`（指摘 0 件のため reflected も同じ値）。`next: plan`
- `outside_changes` は無し。`unprotected_changes` は、この run の前からある他の作業の `/tmp/pr-review-376-*`・`/tmp/review-fix-planning.*` の 6 つの worktree で、触れていない
- `cleanup` は runner の worktree と runner-dir を消し、`retained` は無し。記録は commit しない `tmp/agents/issue-397.07kekhs0/` にある

## 実行の記録

- 実装の担当: `pi_opencode-go_deepseek4-flash_max`（`--implement` で利用者が指定、fallback 無し）。runner が観測したモデルは `opencode-go` の `deepseek-v4.1-flash`（effort `max`）。依頼は Task ごとに 1 回で、依頼し直しは無し
  - Task 1（ランチャーとテスト）: 223 秒、`importable`、`255c3fb9`。Task のレビューは承認（軽微 1 件は直さない裁定）
  - Task 2（案内と移植の記録）: 296 秒、`importable`、`42f25687`。Task のレビューは承認（軽微 2 件は最終レビューで直すと判定）
  - 最終レビューの修正: 207 秒、`importable`、`c92c976d`
- Task 3（controller）: `bash .devcontainer/run-tests.bash`（27 本 PASS）と `bash scripts/check-layout.sh` が終了コード 0。実 API は 4 tier を各 1 回実行し、すべて終了コード 0・`is_error: false`・結果 `2`。`modelUsage` は fable・opus → `qwen4-max-preview`、sonnet・haiku → `qwen3.8-flash`。標準エラーに `[claude-code:unrecognized_model]` が 1 行ずつ
- 最終レビュー（ブランチ全体）は「修正すれば可」で、Important 1 件と Minor 2 件を 1 回の修正で直した。範囲を絞った再レビューで 4 件とも解消を確認した
- 残した指摘（裁定）: 修正で、移植元の Context7 の照会の段落が「#397 で確認したこと」の節の後ろに来て、この checkout の作業と読める（Important）。ほかに、#18 の文の主語と「上記」の曖昧さ（Minor 2 件）。SDD の規定で 2 回目の修正は出さず、PR 本文に既知の残りとして書いた
- 能動時間: 着手から PR の前まで約 32 分（Spec と Spec レビュー 約 12 分、Task 1 約 6 分、Task 2 約 7 分、最終レビューと修正 約 7 分）
