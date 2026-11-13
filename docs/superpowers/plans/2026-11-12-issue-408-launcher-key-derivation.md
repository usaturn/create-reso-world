# Issue #408 ランチャー環境の key 導出と Ollama runner agent 追加 実装 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** プロバイダ切替ランチャー（`ccda`・`ccdol`・`ccdd` / `ccddg`・`ccdgo`）起動セッションで `tools/agent_runner/with_keys.py` が `ANTHROPIC_BASE_URL` の完全一致と `ANTHROPIC_AUTH_TOKEN` から対応プロバイダの key 1 変数だけを補うように一般化し、あわせて `.devcontainer/claude-ollama-exec` と Ollama の runner agent 2 件（`claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max`）を追加し、関連テスト・配置処理・`.devcontainer/README.md` を揃える。

**Architecture:** 先に Task 1 で `.devcontainer/claude-ollama-exec`・`.devcontainer/install_beforehand.bash`・`.devcontainer/agent-runner.toml`（Ollama 2 agent 追加と Alibaba コメント更新）および `.devcontainer/test-herdr-migration.bash` の代表テストを入れることで、既定雛形の `needed_names` に `OLLAMA_API_KEY` が入った状態を確立する。続く Task 2 で `tools/agent_runner/with_keys.py` の `fill_environment` を「今の環境 → ランチャー環境の導出 → `~/.config/create-reso-world/env`（未解決 `pending` のみ解析）」の 3 段階へ拡張し、既存の代表テスト `test_wrapper_fills_missing_allowlisted_names_only` を実雛形のまま拡張する。Task 3 で `.devcontainer/README.md` の配置一覧・Ollama runner 節・Alibaba 食い違い 3 か所・API トークン節を一括で揃え、Task 4（統合担当 = 司令塔）で `duplicate_model` 拒否・反例偽 CLI 観測・マージ前実機観測（各 agent 最大 1 回）・秘密非露出検査・全体検証を実行する。

**Tech Stack:** Python 3.14 / `uv` / `pytest` / Bash（`#!/bin/bash -p`）/ TOML（`agent-runner.toml`）

**Spec:** `docs/superpowers/specs/2026-11-12-issue-408-launcher-key-derivation-design.md`（コミット `f652d9f7708b09bc5b659166c799eeffbf939539`、状態 `draft`、設計レビュー 1 回・Spec レビュー 2 回完了）

## 管理・実行許可

- 状態: `draft`（`issue-to-pr` スキルによる実行許可で進行。内容の承認 `approved` にはせず、確認用コピー `scripts/superpowers-review-copy.sh` は作らない）
- 利用者の指示（原文引用）:
  ```text
  /issue-to-pr #408 --merge
  --design-review claude-code_opus_default
  --spec-review pi_opencode-go_deepseek4-flash_max
  --implement pi_opencode-go_deepseek4-flash_max
  --assign implement=pi_opencode-go_deepseek4-flash_max
  --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default
  途中でメインがマージされたら、追随して作業を止めずに続行してください。
  ```
- 作業先:
  - `PARENT_ROOT`: `/workspaces/reso-world`
  - `CODE_ROOT` / `DOC_ROOT`: `/workspaces/reso-world/.worktrees/issue-408-launcher-key-derivation`（ブランチ `feat/issue-408-launcher-key-derivation`）
  - 捕捉した base: `c3a8e113c3af010fac94820266b93e107d6dbfaf`（`origin/main`）
  - セッション領域: `/workspaces/reso-world/tmp/agents/issue-408.kwkykzl6`

## Global Constraints

- 追加・変更してよいファイルは Spec「追加・変更するファイル」に列挙したファイルに限る。`.devcontainer/zshrc.txt`、`tools/agent_runner/` の他ファイル（`runner.py`・`config.py`・`cli.py`・各 adapter）、`[workflows]` の既定割り当て、個人設定（`~/.pi/`・`~/.config/`）、既存スキルや過去の `docs/superpowers/` 文書は編集禁止。
- `.devcontainer/` 配下のどのファイルにもワークスペースの絶対パス（`/workspaces/...`）を書かない（`test-readme.bash` が失敗する）。
- Python の実行は `uv run` 必須であり、`python3` コマンドを直接使わない。
- テストの採用基準は `AGENTS.md` に従い、壊れてもエラーにならず気付けない損害が残る **S**（および安全境界を守る **F∩S**）の代表 1 件だけを書く。F（文書・モデル一覧・設定値の写し）・L（構文エラーや `check-layout.sh` で気付けるもの）・D（同じ守りの重複）は書かない。
- テスト内の偽トークン文字列は Gitleaks の誤検知を防ぐため、リテラルで連結済みの文字列を書かず `"-".join([...])` 等で実行時に組み立てる。実環境の API key 値はログ・標準出力・標準エラー・ファイルへ一切出さない。
- 日本語表現は `AGENTS.md` に従う（「契約」「原子的」「製品／製品実装」「着地」「正本」「巡／席」「実行器」を使用しない）。

## 受け入れ基準

- **動作環境**:
  - Dev Container（Ubuntu 26.04 LTS）上の `uv`（Python 3.14）・`pytest`・`bash`。自動テストおよび反例確認は隔離 HOME・`env -i`・存在しない `AGENT_RUNNER_CONFIG`・偽 CLI を使い、実 API・共有 `~/.local/bin`・実 `~/.config/create-reso-world/env` に触れない。
  - 最終的な対話・Rebuild 動作環境は Rebuild 後の Dev Container である。稼働中コンテナからは Rebuild を行えないため、マージ前の実機確認（Task 4）では `claude-ollama-exec` のみ `$SESSION` 内の一時 bin ディレクトリを `PATH` に置いて実 API と導出経路を確認し、Rebuild による `~/.local/bin/claude-ollama-exec` 配置と対話セッションからの再確認はマージ後の確認項目（`Refs #408`）とする。
- **実入力**:
  - `with_keys.py` への環境入力:
    - 4 種の登録済み `ANTHROPIC_BASE_URL`:
      1. `https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic` → `MAAS_ANTHROPIC_TOKEN`
      2. `https://ollama.com` → `OLLAMA_API_KEY`
      3. `https://api.deepinfra.com/anthropic` → `DEEPINFRA_TOKEN`
      4. `https://opencode.ai/zen/go` → `OPENCODE_API_KEY`
    - 有効な `ANTHROPIC_AUTH_TOKEN`（ASCII 英数字 `[A-Za-z0-9]` を含むトークン）と、無効な `ANTHROPIC_AUTH_TOKEN`（未設定、空文字 `""`、ASCII 空白・NBSP `\u00a0`・BOM `\ufeff`・全角空白 `\u3000` のみで構成された非 ASCII 空白文字列 `" \u00a0\ufeff\u3000"`）。
    - 複数行・コメント・引用符・`export`・解析不能なコマンド置換 `DEEPINFRA_TOKEN="$(touch ...)"` を含む `~/.config/create-reso-world/env`。
  - `claude-ollama-exec` への環境・引数入力:
    - 隔離環境（`env -i`、locale 非継承）での `OLLAMA_API_KEY=$' \xc2\xa0\xef\xbb\xbf\xe3\x80\x80'`（非 ASCII 空白のみ）と、有効な `OLLAMA_API_KEY` + `.devcontainer/zshrc.txt` の `cc_launcher_unsets` 全変数（`OLLAMA_API_KEY` 以外の 46 変数）に `POLLUTED_<変数名>` を入れた汚染環境 + 追加引数（`probe` 等）。
- **防御範囲**:
  - **対象条件（守るべき境界）**:
    1. `ANTHROPIC_BASE_URL` が 4 種の URL のいずれかと完全一致し、対応する変数名が `needed_names` に含まれ、今の環境で未設定または空であり、かつ `ANTHROPIC_AUTH_TOKEN` が `[A-Za-z0-9]` を 1 文字以上含むときだけ、その 1 変数に `ANTHROPIC_AUTH_TOKEN` を補い、標準エラーに `with_keys: filled <NAME> from launcher environment (ANTHROPIC_BASE_URL)` を 1 行出す（値は一切出さない）。
    2. 優先順位は `1. 今の環境（非空値を保持・上書きしない） → 2. ランチャー環境の導出 → 3. ~/.config/create-reso-world/env（未解決の pending のみを parse_assignments に渡す）` とする。段階 1・2 で解決済みの変数については、env ファイルに別値や解析不能な再代入行があっても上書きせず、`skipped` 警告も出さない。
    3. `claude-ollama-exec` は `#!/bin/bash -p`・`set -euo pipefail`・`shopt -s globasciiranges` で動作し、`OLLAMA_API_KEY` に `[A-Za-z0-9]` が無ければ値を出さず終了コード 1 で止まり子 `claude` を起動しない。有効時は `claude-alibaba-exec` と同一の 46 個の `-u` 指定で親環境の認証・モデル変数をすべて除去し、`ANTHROPIC_BASE_URL=https://ollama.com`・`ANTHROPIC_AUTH_TOKEN="$key"`（`ANTHROPIC_API_KEY` と `OLLAMA_API_KEY` は渡さない）・4 tier すべて `deepseek-v4.1-flash:1017[1m]`・`ENABLE_CLAUDEAI_MCP_SERVERS=false`・`CLAUDE_CODE_EFFORT_LEVEL=max`・`CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536` で `claude "$@"` を `exec` する。
    4. `.devcontainer/agent-runner.toml` に `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max`（`model_key = "deepseek-v4.1-flash"`, `env = ["HOME", "PATH", "OLLAMA_API_KEY"]`）を追加し、`install_beforehand.bash` と `.devcontainer/README.md`（配置手順・配置一覧・Ollama runner 小節・Alibaba 食い違い 3 か所・API トークン節の箇条書きと解決経路表・`auth.json` 注記）を実装と一致させる。
  - **対象外の反例・除外範囲**:
    - 未設定・空・未知 URL・前方一致／末尾スラッシュ違い（例: `https://ollama.com/v1`・`https://ollama.com/`）では 1 変数も導出しない。
    - あるプロバイダの URL から別プロバイダの変数（例: `ccda` URL から `OLLAMA_API_KEY` や `DEEPINFRA_TOKEN`）を導出しない。`COMMANDCODE_API_KEY` はどの URL からも導出しない。`needed_names` 外の変数（`MESHY_API_KEY` 等）は導出も env ファイル補充もしない。
    - 今の環境に非空値（空白のみの非空値を含む）が既にある変数は上書きしない。
    - `.devcontainer/zshrc.txt` の `ccdol` や `cc_launcher_unsets`、`[workflows]` の既定割り当て、`MAAS_ANTHROPIC_TOKEN`・`OLLAMA_API_KEY` をファイルに書かない方針は変更しない。

## 要件・原因・検証の照合（convergence.md 1 章）

| Spec の条件・除外範囲 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| `claude-ollama-exec` の英数字 key ガード・46 個の `-u` 隔離・Bearer のみ送信・4 tier モデル設定 | Task 1 | 非 ASCII 空白のみの key で exit 1 かつ stub `claude` 不起動。有効 key で `cc_launcher_unsets` 全 46 変数の `POLLUTED_` と `OLLAMA_API_KEY` が子環境から消え、`ANTHROPIC_BASE_URL` と `ANTHROPIC_AUTH_TOKEN` のみ届く | `bash .devcontainer/test-herdr-migration.bash`（`test_ollama_exec_requires_key`） |
| `install_beforehand.bash` への `claude-ollama-exec` 配置追加 | Task 1 | 構文エラー無く、既存の postCreate テストが通る（Rebuild 実配置はマージ後確認項目） | `bash -n .devcontainer/install_beforehand.bash`、`bash .devcontainer/test-install-beforehand.bash` |
| `agent-runner.toml` への Ollama 2 agent 追加・Alibaba 2 agent コメント更新・既定 `[workflows]` 不変 | Task 1・Task 4 | `check`・`list` に 2 agent が現れ、`OLLAMA_API_KEY` が `needed_names` に入り、DeepSeek V4.1 Flash 系および同 tier Claude agent との同時指定が `duplicate_model` で拒否される | `tools.agent_runner check` / `list`、Task 4 の一時 `duplicate_model` 確認 |
| `with_keys.py` の 4 URL 完全一致導出・英数字ガード・解決順序（今の環境 → 導出 → env の `pending` のみ）・stderr 出力・docstring 更新 | Task 2・Task 4 | 一致する 1 変数のみ導出、他プロバイダ・未知/部分一致 URL・空白トークン・`COMMANDCODE_API_KEY` は非導出、既存値非上書き、解決済み変数は env の解析不能行でも `skipped` 非出力、stderr に値非露出 | `pytest tools/agent_runner/tests/test_with_keys.py`（`test_wrapper_fills_missing_allowlisted_names_only`）および Task 4 の 4 URL 反例偽 CLI 確認 |
| `.devcontainer/README.md` の配置一覧（91・128・763・1617 行付近）・Ollama runner 節・Alibaba 食い違い 3 か所・API トークン節（2224〜2345 行）と `auth.json` 注記 | Task 3 | Spec 3 章の全項目が漏れなく反映され、ワークスペース絶対パス混入やレイアウト違反が無い | `bash .devcontainer/test-readme.bash`、`bash scripts/check-layout.sh`、Task 3 レビューでの Spec 対照 |
| 共有条件（Task 1 の `agent-runner.toml` の `env` allowlist と Task 2 の `with_keys.py` 導出変数名の整合、実ランチャー環境から実 agent 子プロセスへの受け渡し、実 key 値のログ非露出） | Task 4（統合担当 = 司令塔） | 反例偽 CLI と 5 経路のマージ前実機観測で期待どおり成功/失敗し、全出力ファイルで実 key 文字列の一致が 0 件 | Task 4 の統合検証スクリプト・実機観測・秘密値 0 件検査・全体テストスイート |

## 実行方式

- `implement_task.py check` の結果が `self = false`（担当 `pi_opencode-go_deepseek4-flash_max`、`fallback = []`）のため、`issue-to-pr` 4 章「Task の実装を runner の担当に依頼する」に従い、実装を要する Task 1〜Task 3 を 1 つずつ順番に `implement_task.py run` で `pi_opencode-go_deepseek4-flash_max` へ依頼する（並行しない）。Task 4 は共有条件・実機観測・全体検証を担う統合担当 Task として司令塔が実行する。
- SDD 作業領域: `/workspaces/reso-world/tmp/agents/issue-408.kwkykzl6/sdd/2026-11-12-issue-408-launcher-key-derivation/`（`progress.md`・各 Task の brief・review 記録を保持。worktree 内には作らない）。
- 実装担当用のセッションディレクトリ: `IMPLEMENT_SESSION="$(uv run --no-project python "$PARENT_ROOT/.agents/scripts/agent_tmp.py" mkdir issue-408-implement)"` を作成し、各依頼を `$IMPLEMENT_SESSION/task-<N>-attempt-<M>` に出して `accept` → SDD ledger 記録 → `cleanup` の順で毎回片付ける。全 Task 完了後に空であれば `rmdir "$IMPLEMENT_SESSION"` で消す。
- Task ごとのレビュー: `accept` と関連テストの同期実行の後、読み取り専用の `research` サブエージェントに「この Plan の『受け入れ基準』全文 + 当該 Task の要件 + `git diff <base>..<head>`」だけを渡してレビューさせ（全 Spec・全 Plan は渡さない）、司令塔も diff とテスト結果を照合する。採用する指摘があれば原文のまま同じ担当（`pi_opencode-go_deepseek4-flash_max`）へ新しい `implement_task.py run` 依頼として出し、司令塔が `self` で直接修正しない。
- 最終のブランチ全体レビュー: 本 run は `--merge` が適用される run（`merge-disabled.txt` 無し）であるため、`issue-to-pr` 4 章 8 に従い、全 Task 完了後のブランチ全体レビューは省略して PR 作成後の `pr-review-fix-loop` 1 サイクル目で代える（Task レビューで `deferred` にした minor 指摘があれば PR 本文に一覧で記載する）。

## 実行予算

- Issue 全体の能動時間予算: **480 分**（`tmp/agents/issue-408.kwkykzl6/budget.jsonl` で開始済み。根拠: 設計・Spec レビュー 2 回で約 100 分消化済み、Plan・Task 1〜3 実装と Task レビューで 150 分、統合検証・実機観測 5 件・PR 作成で 60 分、PR レビュー修正ループの司令塔処理で 170 分）。
- worker ごとの期限: `implement` 5400 秒/依頼（role 既定）、`inspect` 2700 秒、`design-review` / `spec-review` 1800 秒。共有 worktree に取り込む実装や検証コマンドに対して独自の途中 SIGINT 打ち切りは行わない。
- 失敗の種類ごとの再試行上限:
  - 安全の失敗（秘密露出・保護外 checkout 汚染・権限境界違反）: **0 回（即全体停止）**。
  - 信頼性の失敗（一時エラー等）: 同じ signature につき **1 回まで**。
  - `implement_task.py` の `retry`（`BLOCKED` / `NEEDS_CONTEXT`）・`rejected`: Task あたり **2 回まで**文脈を補って再依頼し、上限到達または `failed` の場合は `self` で引き取らずその Task で停止して報告する。
- checkpoint の時点: Spec レビュー完了時（記録済み）、Task 1〜3 完了時、PR 作成前、予算 50%・100%、worker 失敗直後。
- 縮小・切り出し・方法変更の候補:
  - 実機観測で特定プロバイダの外部 API 側が一時障害（5xx / レート制限）を返した場合は 1 回だけ間隔を置いて再試行し、解消しなければ偽成功にせず観測事実を PR 本文と Issue コメントに明記してマージ後確認へ切り出すか停止判断を行う。
  - `origin/main` が前進した場合は利用者の明示委任に従い push 前は `rebase`、push 後は `merge --no-edit` で追随し、再検証後に `code-base.json` を更新して続行する。

## contingency（代替策）

- **`pi` アダプタの JSON 形式エラー予防**: `pi` アダプタは最終メッセージに説明文が混ざると `invalid_result` / `response_failed` になりうるため、各 Task の `prompt` 末尾に「最終出力は前後の説明文を一切含めず、`RESULT_SHAPE` に合致する JSON オブジェクト 1 つだけ（または ````json` コードブロック 1 つだけ）を返すこと」を明記する。
- **最初の RED で前提の細部が異なった場合**: 仕様の意味と安全境界が変わらない範囲（例: bash テストの補助関数呼び出し形式）は ledger に理由を記録して最小修正で継続する。仕様の意味が変わる場合は停止して利用者の判断を待つ。
- **`origin/main` の前進**: 実行中の `agent_runner` が完了するのを待ってから、push 前は `git -C "$CODE_ROOT" rebase <new_sha>`、push 後は `git -C "$CODE_ROOT" merge --no-edit <new_sha>` を実行し、`$SESSION/code-base.json` の `sha` を更新して検証をやり直してから次段階へ進む。
- **PR 作成後の `loop.py start` における `--controller-runtime` 検証**: 司令塔は Antigravity CLI（`antigravity`、モデル `Gemini 4 Carbon (Medium)`）で動作しているため、別のランタイム名を偽装せずそのまま渡す。`PARENT_ROOT` の `loop.py start` が未対応ランタイムとして終了コード 2 で拒否した場合は、`issue-to-pr` 3 章・5 章の「想定された停止（ペイン名を維持）」として扱い、検証済み PR の URL・マージ後確認項目・対応ランタイムからの `/pr-review-fix-loop <PR_URL>` 実行コマンドを報告する。

---

## Task 1: `.devcontainer/claude-ollama-exec`・配置処理・Ollama runner agent 2 件・隔離テストの追加

**Files:**
- Create: `.devcontainer/claude-ollama-exec`（mode `0755`）
- Modify: `.devcontainer/install_beforehand.bash`（374〜420 行付近）
- Modify: `.devcontainer/agent-runner.toml`（177〜220 行付近）
- Modify: `.devcontainer/test-herdr-migration.bash`（550・620 行付近）

**Interfaces:**
- Produces:
  - `.devcontainer/claude-ollama-exec`（`OLLAMA_API_KEY` の ASCII 英数字ガード、46 個の `-u` 指定、`https://ollama.com` 向け `claude` exec）
  - `.devcontainer/agent-runner.toml` の `[agents.claude-code_ollama_opus_max]`・`[agents.claude-code_ollama_sonnet_max]`（これにより `needed_names` に `OLLAMA_API_KEY` が追加され、Task 2 のテストが実雛形で `OLLAMA_API_KEY` を検証できる）
- Consumes:
  - `.devcontainer/claude-alibaba-exec`（構造・46 個の `-u` 指定の参照元）
  - `.devcontainer/zshrc.txt` の `cc_launcher_unsets` と `ccdol`（編集せず参照のみ）

**テストの要否**: **要（S および F∩S、代表 1 件）**。`claude-ollama-exec` は独立した新規スクリプトであり、(1) `OLLAMA_API_KEY` が非 ASCII 空白のみのときに起動を通すと Claude Code が保存済み `claude.ai` OAuth トークンを `ollama.com` に送る損害（S）、(2) `cc_launcher_unsets` の `-u` 漏れがあると親環境の他社 key やモデル固定が子プロセスへ漏れる損害（S・F∩S）は通常利用でエラーにならないため、`.devcontainer/test-herdr-migration.bash` に `test_ollama_exec_requires_key` を 1 件追加する。`install_beforehand.bash` の 1 行追加や `agent-runner.toml` の設定値そのものの写しテストは F / L のため書かず、`bash -n`・`test-install-beforehand.bash`・`tools.agent_runner check` / `list` で検証する。

- [ ] **Step 1: `.devcontainer/test-herdr-migration.bash` に失敗するテスト `test_ollama_exec_requires_key` を追加する（RED）**

`test_alibaba_exec_requires_key`（510〜549 行）の直後に `test_ollama_exec_requires_key` を追加し、ファイル末尾の呼び出し一覧（`test_alibaba_exec_requires_key` の直後）に `test_ollama_exec_requires_key` を追加する。テスト内容は次の 2 段階を 1 関数にまとめる:
1. 隔離 HOME（`make_stub_home "$test_home"`、`mkdir -p "$test_home/.local/bin"`）に `${REPO_ROOT}/.devcontainer/claude-ollama-exec` を `0755` で配置し、`$test_home/bin/claude` に `env > "$HERDR_TEST_CLAUDE_DUMP"` の stub を置く。
2. **拒否側**: `env -i HOME="$test_home" PATH="$test_home/.local/bin:$test_home/bin:/usr/bin:/bin" HERDR_TEST_CLAUDE_DUMP="$log" ANTHROPIC_API_KEY=fake-anthropic CLAUDE_CODE_OAUTH_TOKEN=fake-oauth OLLAMA_API_KEY=$' \xc2\xa0\xef\xbb\xbf\xe3\x80\x80'` で `"$test_home/.local/bin/claude-ollama-exec" probe` を実行し、終了コードが非 0 かつ `$log` が空（stub `claude` 不起動）であること、標準エラー出力に空白文字そのもの（`$'\xc2\xa0'`・`$'\xef\xbb\xbf'`）が出ないことを確認する。
3. **陽性対照と全 `cc_launcher_unsets` 隔離確認**: `extract_cc_launcher_unsets "$ZSHRC_TEMPLATE"` で取り出した全変数（`OLLAMA_API_KEY` 自身を除く 46 変数）に `<VAR>=POLLUTED_<VAR>` を組み立てて `env -i` に渡し、さらに `OLLAMA_API_KEY=fake-ollama` を渡して `"$test_home/.local/bin/claude-ollama-exec" probe` を実行する（引数の受け渡しも stub で記録するか `env` ダンプで確認する）。終了コード 0 で起動し、`^ANTHROPIC_AUTH_TOKEN=fake-ollama$`・`^ANTHROPIC_BASE_URL=https://ollama.com$`・`^ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4.1-flash:1017\[1m\]$` が含まれ、`POLLUTED_` と `^OLLAMA_API_KEY=` と `^ANTHROPIC_API_KEY=` が一切含まれないことを `assert_contains` / `assert_absent` で確認する（偽値リテラルは `fake-ollama` 等の短い識別子にし、Gitleaks に掛かる高エントロピー文字列を使わない）。

- [ ] **Step 2: テストが失敗することを確認する**

Run: `bash .devcontainer/test-herdr-migration.bash`
Expected: `.devcontainer/claude-ollama-exec` がまだ存在しないため FAIL する。

- [ ] **Step 3: `.devcontainer/claude-ollama-exec`・`.devcontainer/install_beforehand.bash`・`.devcontainer/agent-runner.toml` を実装する（GREEN）**

1. `.devcontainer/claude-ollama-exec` を新規作成し、`chmod +x`（`0755`）を付与する（ワークスペース絶対パスは書かない）:
   - 先頭 `#!/bin/bash -p`、`set -euo pipefail`、コメントで `-p` の理由・呼び出し元（`claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max`）・`zshrc.txt` の `ccdol` と設定を揃えること（片方を変えるときはもう片方も揃えること）を記載する。
   - 4 変数 `fable='deepseek-v4.1-flash:1017[1m]'`、`opus='deepseek-v4.1-flash:1017[1m]'`、`sonnet='deepseek-v4.1-flash:1017[1m]'`、`haiku='deepseek-v4.1-flash:1017[1m]'`。
   - `shopt -s globasciiranges`、`key="${OLLAMA_API_KEY-}"`、`if [[ $key != *[A-Za-z0-9]* ]]; then echo "claude-ollama-exec: OLLAMA_API_KEY is not set, empty, or has no letters or digits; export an Ollama API key before starting agent-runner" >&2; exit 1; fi`。
   - `.devcontainer/claude-alibaba-exec` の 45〜90 行と完全に同一の 46 個の `-u` 指定を持つ `exec env` で、`ANTHROPIC_BASE_URL=https://ollama.com`、`ANTHROPIC_AUTH_TOKEN="$key"`、`ANTHROPIC_DEFAULT_FABLE_MODEL="$fable"`、`ANTHROPIC_DEFAULT_OPUS_MODEL="$opus"`、`ANTHROPIC_DEFAULT_SONNET_MODEL="$sonnet"`、`ANTHROPIC_DEFAULT_HAIKU_MODEL="$haiku"`、`ENABLE_CLAUDEAI_MCP_SERVERS=false`、`CLAUDE_CODE_EFFORT_LEVEL=max`、`CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536` を設定して `claude "$@"` を実行する。
2. `.devcontainer/install_beforehand.bash`:
   - 374〜375 行の `step` メッセージとコメントに `claude-ollama-exec` を加え、419 行の `claude-alibaba-exec` 配置直後に `if ! install -m 0755 .devcontainer/claude-ollama-exec "${HOME}/.local/bin/claude-ollama-exec"; then fail "Failed to place claude-ollama-exec."; fi` を追加する。
3. `.devcontainer/agent-runner.toml`:
   - `[agents.pi_alibaba_qwen4-max_max]`（177〜188 行）と `[agents.claude-code_alibaba_opus_max]`（206〜209 行）のコメントを更新し、`ccda` セッションから `with_keys.py` 経由でランナーを起動する場合は `ANTHROPIC_BASE_URL` の一致で `ANTHROPIC_AUTH_TOKEN` から `MAAS_ANTHROPIC_TOKEN` が補われること、それ以外のランチャー（`ccdd`・`ccddg`・`ccdgo`・`ccdol`）セッションや `with_keys.py` を通さない直接起動では届かず key ガードで終了コード 1 で止まることを明記する。
   - `[agents.claude-code_alibaba_opus_max]` の直後（`[workflows.review]` の前）に、Spec 2.3 のコメント付きで `[agents.claude-code_ollama_opus_max]` と `[agents.claude-code_ollama_sonnet_max]` を追加する（`[workflows]` は一切変更しない）。

- [ ] **Step 4: 関連テストと構造チェックを実行する**

Run:
- `bash -n .devcontainer/claude-ollama-exec .devcontainer/install_beforehand.bash .devcontainer/test-herdr-migration.bash`
- `bash .devcontainer/test-herdr-migration.bash`
- `bash .devcontainer/test-install-beforehand.bash`
- `bash .devcontainer/test-readme.bash`
- `uv run --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml check`
- `uv run --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml list`
Expected: すべて終了コード 0 で成功し、`list` に `claude-code_ollama_opus_max` と `claude-code_ollama_sonnet_max` が表示される。

- [ ] **Step 5: コミットする**

commit message: `feat(devcontainer): add claude-ollama-exec and Ollama runner agents`

---

## Task 2: `tools/agent_runner/with_keys.py` のランチャー key 導出と代表テストの拡張

**Files:**
- Modify: `tools/agent_runner/with_keys.py`
- Modify: `tools/agent_runner/tests/test_with_keys.py`

**Interfaces:**
- Consumes: Task 1 で更新された `.devcontainer/agent-runner.toml`（`OLLAMA_API_KEY` を含む `needed_names`）
- Produces:
  - `tools/agent_runner/with_keys.py` の `_LAUNCHER_BASE_URL_KEYS`・`_ASCII_ALNUM`・`fill_environment(environ, names, source) -> tuple[dict[str, str], list[str], list[str], list[str]]`（`(environment, derived, filled, skipped)`）・`_report_derived`
  - `tools/agent_runner/tests/test_with_keys.py` の拡張された単一テスト関数 `test_wrapper_fills_missing_allowlisted_names_only`

**テストの要否**: **要（S、既存代表テスト 1 件の拡張・新設関数 0 件）**。異プロバイダへの誤導出、既存環境変数の上書き、非 ASCII 空白のみのトークン導出、解決済み変数に対する env ファイルからの上書きや不要な `skipped` 警告、標準エラーへの秘密値露出はいずれもエラーにならず損害が残る S である。`#issuecomment-6816243774` と Spec テスト計画 1 に従い、テスト関数は新設せず `test_wrapper_fills_missing_allowlisted_names_only` 1 関数内で検証する。

- [ ] **Step 1: `tools/agent_runner/tests/test_with_keys.py` の `test_wrapper_fills_missing_allowlisted_names_only` を拡張して失敗を確認する（RED）**

テスト関数を増やさず `test_wrapper_fills_missing_allowlisted_names_only` を拡張する（すべての偽トークンは `"-".join(...)` で組み立てる）:
1. サブプロセス実行ケースの `child_env` に `"ANTHROPIC_BASE_URL": "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic"` と `"ANTHROPIC_AUTH_TOKEN": fake_f`（`fake_f = "-".join(["fake", "maas", "launcher"])`）を追加し、既存の全アサーション（`COMMANDCODE_API_KEY == fake_a`、`OPENCODE_API_KEY == fake_d`、`"MESHY_API_KEY" not in environment`、`"DEEPINFRA_TOKEN" not in environment`、`not marker.exists()`）を維持したうえで次を追加検証する:
   - `environment["MAAS_ANTHROPIC_TOKEN"] == fake_f`（`ccda` の URL から導出される）
   - `"OLLAMA_API_KEY" not in environment`（`OLLAMA_API_KEY` は雛形 allowlist にあるが、別プロバイダの URL からは導出されない）
   - `"with_keys: filled MAAS_ANTHROPIC_TOKEN from launcher environment (ANTHROPIC_BASE_URL)" in completed.stderr`
   - `fake_f` を含む全偽トークン実値が `completed.stderr` に含まれないこと
2. 同じテスト関数の後半で `from tools.agent_runner.with_keys import TEMPLATE, fill_environment, needed_names` を呼び、`names = needed_names(TEMPLATE, None)` と `missing_env = tmp_path / "missing" / "env"` を使って境界対照を確認する:
   - **(a) 部分一致・未知 URL**: `fill_environment({"ANTHROPIC_BASE_URL": "https://ollama.com/v1", "ANTHROPIC_AUTH_TOKEN": fake_f}, names, missing_env)` で `derived == []`、`"OLLAMA_API_KEY" not in env_a`、`"COMMANDCODE_API_KEY" not in env_a`。
   - **(b) 非 ASCII 空白のみの `ANTHROPIC_AUTH_TOKEN`**: `fill_environment({"ANTHROPIC_BASE_URL": "https://ollama.com", "ANTHROPIC_AUTH_TOKEN": " \u00a0\ufeff\u3000"}, names, missing_env)` で `derived == []`、`"OLLAMA_API_KEY" not in env_b`。
   - **(c) 既存環境変数の保持**: `existing = "-".join(["fake", "maas", "existing"])` に対し、`fill_environment({"MAAS_ANTHROPIC_TOKEN": existing, "ANTHROPIC_BASE_URL": "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic", "ANTHROPIC_AUTH_TOKEN": fake_f}, names, missing_env)` で `env_c["MAAS_ANTHROPIC_TOKEN"] == existing` かつ `derived == []`。
   - **(d) `ccdgo` 導出と env ファイル優先順・`skipped` 抑止**: `opencode_bad_env = tmp_path / "opencode.env"` に `OPENCODE_API_KEY={fake_b}` と解析不能な再代入 `OPENCODE_API_KEY="$(touch {marker})"` を書き、`launcher_go = "-".join(["fake", "opencode", "launcher"])` で `fill_environment({"ANTHROPIC_BASE_URL": "https://opencode.ai/zen/go", "ANTHROPIC_AUTH_TOKEN": launcher_go}, names, opencode_bad_env)` を呼ぶ。`env_d["OPENCODE_API_KEY"] == launcher_go`、`derived == ["OPENCODE_API_KEY"]`、`"OPENCODE_API_KEY" not in skipped_d`、`not marker.exists()` であることを確認する。あわせて `https://api.deepinfra.com/anthropic` でも対応する `DEEPINFRA_TOKEN` 1 変数だけが導出され `DEEPINFRA_TOKEN` が `skipped` に入らないことを確認する。

- [ ] **Step 2: テストが失敗することを確認する**

Run: `uv run --locked pytest tools/agent_runner/tests/test_with_keys.py`
Expected: ランチャー導出が未実装かつ `fill_environment` が 3 要素タプルを返すため FAIL する。

- [ ] **Step 3: `tools/agent_runner/with_keys.py` を実装する（GREEN）**

Spec 1.1〜1.3 に従い、`tools/agent_runner/with_keys.py` を次のとおり更新する:
1. モジュール docstring（7〜12 行付近）と `fill_environment` の docstring（135〜140 行付近）を、「今の環境（非空値を保持） → ランチャー環境の導出（`ANTHROPIC_BASE_URL` 完全一致かつ `ANTHROPIC_AUTH_TOKEN` が ASCII 英数字を含むとき対応する 1 変数のみ） → `~/.config/create-reso-world/env`（未解決の名前のみ）」の 3 段階および戻り値 `(environment, derived, filled, skipped)` に合わせて更新する。
2. モジュール定数を追加する:
   ```python
   _LAUNCHER_BASE_URL_KEYS: Mapping[str, str] = {
       "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic": "MAAS_ANTHROPIC_TOKEN",
       "https://ollama.com": "OLLAMA_API_KEY",
       "https://api.deepinfra.com/anthropic": "DEEPINFRA_TOKEN",
       "https://opencode.ai/zen/go": "OPENCODE_API_KEY",
   }
   _ASCII_ALNUM = re.compile(r"[A-Za-z0-9]")
   ```
3. `fill_environment(environ: Mapping[str, str], names: set[str], source: Path) -> tuple[dict[str, str], list[str], list[str], list[str]]`:
   - `environment = dict(environ)`
   - `pending = {name for name in names if not environment.get(name)}`
   - `derived: list[str] = []`
   - `derived_name = _LAUNCHER_BASE_URL_KEYS.get(environment.get("ANTHROPIC_BASE_URL", ""))`
   - `auth_token = environment.get("ANTHROPIC_AUTH_TOKEN", "")`
   - `if derived_name is not None and derived_name in pending and _ASCII_ALNUM.search(auth_token) is not None:` のとき `environment[derived_name] = auth_token`、`pending.remove(derived_name)`、`derived.append(derived_name)`。
   - `if not pending: return environment, derived, [], []`
   - `source` 読み込み時、`FileNotFoundError` と `(OSError, UnicodeDecodeError)`（stderr に `with_keys: cannot read {source}`）は `return environment, derived, [], []`。
   - `assignments, skipped = parse_assignments(text, pending)`（**`names` ではなく `pending` だけを渡す**）。
   - `filled` を組み立てて `return environment, derived, filled, skipped` を返す。
4. `_report_derived(names: Sequence[str]) -> None` を追加し、各 `name` について `print(f"with_keys: filled {name} from launcher environment (ANTHROPIC_BASE_URL)", file=sys.stderr)` を出力する。`main()` では `environment, derived, filled, skipped = fill_environment(os.environ, names, source)` を受け、`_report_derived(derived)` → `_report_skipped(skipped, source)` → `_report_filled(filled, source)` の順に出力する。

- [ ] **Step 4: 関連テストとコンパイル検査を実行する**

Run:
- `uv run --locked python -m py_compile tools/agent_runner/with_keys.py tools/agent_runner/tests/test_with_keys.py`
- `uv run --locked pytest tools/agent_runner/tests`
Expected: すべて PASS。

- [ ] **Step 5: コミットする**

commit message: `feat(agent-runner): derive provider keys from launcher environment in with_keys`

---

## Task 3: `.devcontainer/README.md` の更新（Ollama runner・key 導出・PR #405 食い違い解消）

**Files:**
- Modify: `.devcontainer/README.md`

**Interfaces:**
- Consumes: Task 1・Task 2 で確定した `claude-ollama-exec`・Ollama 2 agent・`with_keys.py` の導出規則と標準エラー文面
- Produces: 実装と矛盾のない `.devcontainer/README.md`

**テストの要否**: **不要（F）**。文書の文言・見出し・表の内容を写して照合するテストは `AGENTS.md` の F（固定値）に当たり禁止されている。代わりに既存の不変条件検査 `bash .devcontainer/test-readme.bash`（ワークスペース絶対パス非混入等）と `bash scripts/check-layout.sh`、および Spec 3 章の全項目に対する `git diff` 精読で検証する。

- [ ] **Step 1: Spec 3 章の 4 領域すべてを `.devcontainer/README.md` に反映する**

ワークスペースの絶対パス（`/workspaces/...`）を一切書かず、また `AGENTS.md` の日本語規約（「契約」「原子的」「製品」「着地」「正本」「巡」「席」「実行器」を使わない）を守って次の箇所を更新する:
1. **既存環境の更新・導入手順・`install_beforehand.bash` 配置一覧**:
   - 91 行付近: postCreate が `~/.local/bin` に置く一覧に `claude-ollama-exec`（「Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）」参照）を追加する。
   - 128〜129 行付近: rebuild しない場合の手動配置に `claude-ollama-exec`（同じ節の `22` の `install -m 0755` で `~/.local/bin` に置くこと、未配置だと `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` が `launch_failed` になること）を追加する。
   - 763〜765 行付近: `21. install -m 0755 .devcontainer/claude-alibaba-exec ~/.local/bin/claude-alibaba-exec` の直後に `22. install -m 0755 .devcontainer/claude-ollama-exec ~/.local/bin/claude-ollama-exec` を追加し、後続の `setup_pi_superagents.zsh` と `install_ctx7.bash` を `23.`・`24.` に繰り下げる。
   - 1606〜1617 行付近: `install_beforehand.bash` が配置する一覧の `claude-alibaba-exec` の直後に `- .devcontainer/claude-ollama-exec → ~/.local/bin/claude-ollama-exec。同様に毎回上書き` を追加する。
2. **「Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）」節（912 行付近、`### OpenCode Go...` の直前）**:
   - `#397` の `#### agent-runner から使う（#401）` にならい、`#### agent-runner から使う（#408）` 小節を追加する。
   - `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` の設定表（`command = claude-ollama-exec`、`model = opus` / `sonnet`、`model_key = deepseek-v4.1-flash`、`provider = ollama`、`effort = max`、`env = HOME・PATH・OLLAMA_API_KEY`）、Rebuild 前の `~/.local/bin/claude-ollama-exec` 未配置時は `launch_failed` になること、4 つの tier すべて `deepseek-v4.1-flash:1017[1m]` で `zshrc.txt` の `ccdol` と揃えること、通常シェルで `OLLAMA_API_KEY` を export して `with_keys.py` 経由で起動するコマンド例、`ccdol` セッションからは `with_keys.py` が `ANTHROPIC_BASE_URL`（`https://ollama.com`）の一致で `ANTHROPIC_AUTH_TOKEN` から `OLLAMA_API_KEY` を補うこと（他プロバイダのランチャーセッションからは補われないこと）、`claude-ollama-exec` の ASCII 英数字ガードと Bearer のみ送信、`duplicate_model` で同じ役割に並べられない組み合わせ（`model_key` が `deepseek-v4.1-flash` の agent 同士、さらに `opus` は `claude-code_opus_default`・`claude-code_alibaba_opus_max`、`sonnet` は `claude-code_sonnet_xhigh`）を記載する。
3. **Alibaba 関連の食い違い 3 か所解消と `#397`・`agent の命名と同一モデルの比較` 更新**:
   - 1234〜1237 行（`#397` の `claude-code_alibaba_opus_max`）: env ファイルには置かない方針だが、key を export した通常シェルのほか、`ccda` 起動セッションから `with_keys.py` 経由で起動するときは `ANTHROPIC_BASE_URL` の一致で `ANTHROPIC_AUTH_TOKEN` から `MAAS_ANTHROPIC_TOKEN` が補われること（`ccdd`・`ccddg`・`ccdgo`・`ccdol` のセッションからは補われないこと）に更新する。
   - 1310〜1314 行（`#397` 内の `#402` `piaq` 説明）、1442〜1455 行（`pi_alibaba_qwen4-max_max` 説明と起動例。起動コマンド例も `tools/agent_runner/with_keys.py -- python -m tools.agent_runner run ...` 経由に揃える）、1892〜1903 行（`#402` の `piaq` 節）の 3 か所にある「`with_keys.py` で補う経路も無い」を解消する。具体的には、対話の `piaq` をランチャーセッション内で直接起動する場合は引き続き `MAAS_ANTHROPIC_TOKEN` が無く終了コード 1 で止まる一方、`ccda` セッションから `with_keys.py` 経由で agent-runner の `pi_alibaba_qwen4-max_max` を起動する場合は `ANTHROPIC_AUTH_TOKEN` から補われる（他プロバイダのランチャーセッションからは補われない）と明確に書き分ける。
   - 1427〜1441 行付近（`agent の命名と同一モデルの比較` 節）: #305 で追加した 6 agent の説明の近くに、以降に追加した Claude Code 用の exec を使う雛形 agent（#401 の `claude-code_alibaba_opus_max`、#408 の `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max`）への参照を短く補う。
4. **「API トークン」節の各変数箇条書き（2224〜2248 行）と「ランチャー起動セッションから runner を使う（#401・#408）」小節（2260〜2345 行）**:
   - 2224〜2230 行（`DEEPINFRA_TOKEN`）: `ccdd`・`ccddg` セッションから `with_keys.py` 経由でランナーを起動するときは `ANTHROPIC_AUTH_TOKEN` から補われることを追記する。
   - 2231〜2236 行（`OLLAMA_API_KEY`）: 「`ccdol`・`claude-ollama` だけが読む」「どの agent の `env` にも無いので、wrapper では補えない」を改め、agent-runner の `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` が呼ぶ `claude-ollama-exec` も読むこと、env ファイルには置かないが `ccdol` セッションからは `with_keys.py` が `ANTHROPIC_AUTH_TOKEN` から補うこと（他ランチャーセッションからは補われないこと）に更新する。
   - 2237〜2248 行（`MAAS_ANTHROPIC_TOKEN`）: 2241 行の「通常は補われない」を改め、env ファイルには置かないが `ccda` セッションからは `with_keys.py` が `ANTHROPIC_AUTH_TOKEN` から補うこと（他ランチャーセッションからは補われないこと）に更新する。
   - 2260〜2345 行: 見出しを `#### ランチャー起動セッションから runner を使う（#401・#408）` とし、「補う条件」「読み元と順序」「使わなかった行」「出力」を 3 段階の順序（`今の環境` → `ランチャー環境の導出（4 つの ANTHROPIC_BASE_URL 完全一致かつ ANTHROPIC_AUTH_TOKEN が ASCII 英数字を含むとき、対応する 1 変数のみ）` → `~/.config/create-reso-world/env`）、4 ランチャー URL と補う変数名の対応表、`COMMANDCODE_API_KEY` 非導出、Vertex `GOOGLE_*` が `cc_launcher_unsets` 対象外で残ること、標準エラー `with_keys: filled <NAME> from launcher environment (ANTHROPIC_BASE_URL)`（値は出さず、導出済み変数は env ファイルの解析対象 `pending` から外れるため上書きも `skipped` 表示もしないこと）に合わせて更新する。
   - 2319〜2345 行の古い記述（「`OLLAMA_API_KEY` はどの agent の `env` にも無い」「雛形に Ollama の runner agent は無い」等）を更新し、プロバイダ別 key 解決経路の表（2328〜2342 行）に Spec 3.4 のとおり各ランチャー導出、`MAAS_ANTHROPIC_TOKEN` 行への `pi_alibaba_qwen4-max_max` 追加、`OLLAMA_API_KEY` 行（`claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max`）の追加を行い、`auth.json` について根拠のない実機起動確認済みの表現を書かない。

- [ ] **Step 2: 文書テストとレイアウト検査を実行する**

Run:
- `bash .devcontainer/test-readme.bash`
- `bash scripts/check-layout.sh`
Expected: どちらも終了コード 0 で PASS する。

- [ ] **Step 3: コミットする**

commit message: `docs(devcontainer): document launcher key derivation and Ollama runner agents`

---

## Task 4: 統合検証・反例確認・マージ前実機観測・記録コミット（統合担当 = 司令塔）

**Files:**
- Modify: `docs/superpowers/plans/2026-11-12-issue-408-launcher-key-derivation.md`（実行記録・検証結果・所要時間の追記のみ）

**Interfaces:**
- Consumes: Task 1〜Task 3 の全コミット、`$SESSION` の一時検証領域
- Produces: `$SESSION` 配下の反例検証・実機観測ログ、`$SESSION/checks.json`、Plan の完了記録コミット

**テストの要否**: **不要（統合検証・実機観測 Task）**。S の自動テストは Task 1・Task 2 で追加済みであり、本 Task では一時設定・偽 CLI・実プロバイダ API（各 agent 最大 1 回）およびリポジトリ全体のテストスイートを実行して証拠を `$SESSION` に残す。

- [ ] **Step 1: `duplicate_model` 拒否の一時検証と、反例（偽 CLI・隔離環境）の実行観測を行う**

`$SESSION/integration-probes/` 配下で次を実行し、結果を JSON で保存する（worktree には何も残さない）:
1. `claude-code_ollama_opus_max` と `pi_opencode-go_deepseek4-flash_max`、`claude-code_ollama_opus_max` と `claude-code_ollama_sonnet_max`、`claude-code_ollama_opus_max` と `claude-code_opus_default`、`claude-code_ollama_sonnet_max` と `claude-code_sonnet_xhigh` を同一役割に並べたとき、`tools.agent_runner check` がすべて `duplicate_model` で拒否すること。
2. 4 ランチャー URL（`ccda`・`ccdol`・`ccdd`・`ccdgo`）それぞれで偽 CLI を使った `with_keys.py -- python -m tools.agent_runner run` を動かし、対応する 1 変数だけがその `agent.env` を持つ担当の子に渡り、別プロバイダの担当の子には渡らないこと、`COMMANDCODE_API_KEY` が補われないこと、全出力に偽トークン実値が 0 件であること。

- [ ] **Step 2: マージ前の実機観測（各 agent 最大 1 回）と秘密値 0 件検査を実行する**

`$SESSION/live-checks/` 配下に一時ディレクトリと外側 `claude` shim（`.devcontainer/zshrc.txt` の実関数 `ccda`・`ccdol`・`ccdd` が作る環境をそのまま受け取り、元の `PATH` に戻して指定コマンドを実行する shim）および `live-bin/claude-ollama-exec`（Task 1 の `.devcontainer/claude-ollama-exec` を `install -m 0755` で配置）を用意し、次の 5 件を 1 回ずつ実行する:
1. `ccda` セッション環境 + `with_keys.py`（手当てなし）→ `pi_alibaba_qwen4-max_max`（1 回）
2. `ccda` セッション環境 + `with_keys.py`（手当てなし）→ `claude-code_alibaba_opus_max`（1 回）
3. 通常のシェル（`MAAS_ANTHROPIC_TOKEN` export 済み、`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` 無し）+ `with_keys.py` → `claude-code_alibaba_opus_max`（1 回）
4. `ccdol` セッション環境 + `with_keys.py`（一時 `PATH` に `claude-ollama-exec`）→ `claude-code_ollama_opus_max`（1 回）
5. `ccdd` セッション環境 → `pi_deepinfra_deepseek4-flash_high`: (a) `with_keys.py` 無しで `pidid` の key ガードにより失敗すること（API 課金なし）、(b) `with_keys.py` 経由（手当てなし）で成功すること（1 回）
6. 実行後、`$SESSION/live-checks/` 以下の全ファイルに対して親環境の `MAAS_ANTHROPIC_TOKEN`・`OLLAMA_API_KEY`・`DEEPINFRA_TOKEN`・`OPENCODE_API_KEY` 等の実値文字列が **0 件**であることを Python スクリプトで検査し、値自体は出力せず一致件数 `0` を記録する。

- [ ] **Step 3: Plan に実行記録・検証要約を追記してコミットする**

Task 1〜Task 4 の実行結果・観測した `identity`・所要時間内訳を本 Plan 末尾の「実行記録」節に追記してコミットする。

- [ ] **Step 4: 最終 HEAD（`git status --porcelain` が空）でリポジトリ全体検証を実行し、`$SESSION/checks.json` を作成する**

Run（`CODE_ROOT` で実行し、各ログと終了コードを `$SESSION` に保存）:
1. `bash .devcontainer/run-tests.bash`
2. `bash scripts/check-layout.sh`
3. `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools`
4. `uv run --locked python -m tools.agent_runner check` および `list`
すべて終了コード 0 であることを確認し、検証した `HEAD` と `CODE_BASE_SHA` を記録した `$SESSION/checks.json` を保存してから Step 5（`scan-before-push.sh` → push → PR 作成 → `--merge` ループ）へ進む。

## 実行記録（2026-11-13）

Issue #408 の残作業を、既存の Spec（`2026-11-12-issue-408-launcher-key-derivation-design.md`）と Plan に従って実行した。担当は `--implement pi_opencode-go_deepseek4-flash_max`（Plan の管理・実行許可のとおり）で、Task 1〜3 の実装とレビュー指摘の修正を runner 経由で依頼した。Task 4 は司令塔が実行した。

### Task ごとの結果

- **Task 1**: `.devcontainer/claude-ollama-exec`・`install_beforehand.bash`・`agent-runner.toml`・`test-herdr-migration.bash` を追加（`9b41a3b4`）。レビュー 1 回目で 3 件（コメント矛盾・stub の引数記録・モデル名固定値の削除）を採用し、修正（`a99e67c7`）。再レビューは clean。`test-herdr-migration.bash`・`test-install-beforehand.bash`・`test-readme.bash`・`agent_runner check` / `list` はすべて exit 0。
- **Task 2**: `with_keys.py` に 4 URL の完全一致導出と 3 段階の解決順序を実装し、既存の代表テストを拡張（`35c6a51f`）。レビュー 1 回目で 2 件（Ollama の陽性対照の追加・重複した marker 確認の整理）を採用し、修正（`57cc0203`）。`pytest tools/agent_runner/tests` は 303 passed、exit 0。
- **Task 3**: `.devcontainer/README.md` を更新（`04a37c28`）。レビュー 1 回目で 1 件（`pi_alibaba_qwen4-max_max` の起動経路の記述が `ccda` + `with_keys.py` の導出と矛盾して見える）を採用し、修正（`4bb3ae67`）。`test-readme.bash`・`check-layout.sh`・`git diff --check` は exit 0。
- **Task 4**: 下記の統合検証を実行。

### 統合検証

- `duplicate_model` の一時確認（コミットしない）: `claude-code_ollama_opus_max` と `pi_opencode-go_deepseek4-flash_max`、`claude-code_ollama_sonnet_max`、`claude-code_opus_default`、`claude-code_sonnet_xhigh` の各組み合わせを同じ役割に置くと、`check` はすべて `duplicate_model`（exit 2）で拒否した。変更前の雛形コピーは exit 0。
- 反例（偽 CLI・隔離環境）: 4 つのランチャー URL それぞれで、`with_keys.py` は対応する 1 変数だけを導出し（stderr の `filled` 行で確認）、偽 CLI の子環境ではその変数が対応する担当にだけ渡り、他の担当には渡らなかった。`COMMANDCODE_API_KEY` はどの URL でも導出されず、全ログ・result.json に偽トークンの実値は 0 件だった。
- 実機観測（マージ前、各 agent 1 回）: 後述の表のとおり。出力ファイルに実 key の値の一致は 0 件（件数のみ確認）。
- 最終 HEAD のリポジトリ全体検証: `bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`・`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools`・`uv run --locked python -m tools.agent_runner check` / `list` を実行し、すべて exit 0。

### 実機観測の結果（マージ前、各 agent 1 回）

| 確認 | 起動元 | agent | state | identity（実測） | 所要 | 備考 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `ccda` セッション + wrapper | `pi_alibaba_qwen4-max_max` | success | `qwen4-max-preview` / `alibaba` / `max` | 10.9 秒 | 導出した `MAAS_ANTHROPIC_TOKEN` で成功 |
| 2 | `ccda` セッション + wrapper | `claude-code_alibaba_opus_max` | success | `qwen4.0-max-preview` / CLI 2.1.323 | 22.8 秒 | 導出した `MAAS_ANTHROPIC_TOKEN` で成功 |
| 3 | 通常のシェル（`MAAS_ANTHROPIC_TOKEN` export） | `claude-code_alibaba_opus_max` | success | `qwen4.0-max-preview` / CLI 2.1.323 | 27.2 秒 | 既存値を上書きせず成功 |
| 4 | `ccdol` セッション + wrapper（一時 PATH の `claude-ollama-exec`） | `claude-code_ollama_opus_max` | success | `deepseek-v4.1-flash:1017` / CLI 2.1.323 | 8.6 秒 | 導出した `OLLAMA_API_KEY` で成功。初回は確認用 shim の PATH 設定不備で `launch_failed`（API 未呼出）となり、shim を直して 1 回だけ再実行した |
| 5a | `ccdd` セッション + wrapper なし | `pi_deepinfra_deepseek4-flash_high` | failed（`response_failed`） | 未観測 | 0.3 秒 | `pidid` が `DEEPINFRA_TOKEN is not set.` で終了コード 1。API 課金なし |
| 5b | `ccdd` セッション + wrapper | `pi_deepinfra_deepseek4-flash_high` | success | `deepseek-ai/DeepSeek-V4.1-Flash-1017` / `deepinfra` / `high` | 5.5 秒 | 導出した `DEEPINFRA_TOKEN` で成功 |

- 生成物（`result.json`・stdout/stderr・outer ログ）の実 key 値の一致は、`live-checks/secret-scan.json` のとおり全 key 0 件（5629 ファイルを走査）。
- 実 API を呼んだ成功試行は、各 agent 1 回（ccdol の初回 `launch_failed` は API 未呼出のため成功試行に数えない）。

### 所要時間

- Task 1: 実装 151.7 秒 + 修正 218.7 秒（runner 実測）、レビュー 2 回（約 5 分・約 5 分）
- Task 2: 実装 203.9 秒 + 修正 95.9 秒（runner 実測）、レビュー 1 回（約 10 分）
- Task 3: 実装 421.2 秒 + 修正 30.3 秒（runner 実測）、レビュー 1 回（約 16 分）
- Task 4: `duplicate_model` 確認・偽 CLI 反例（4 URL × 5 agent）・実機 6 試行・秘密走査・base 前進追随・最終検証
- 司令塔の作業開始からマージ前検証まで: 約 60 分（2026-11-13 10:20〜11:20）

### 注記

- Plan Task 2 Step 1(d) の `assert not marker.exists()` は、Task 2 レビューの T2-R2（同じ守りの重複・検出力なし、`AGENTS.md` の D）を採用して削除した。前半のサブプロセス検査が同じ守りを確認している。
- `origin/main` は実行中に `c3a8e113` から `777a67a8` へ前進した。利用者の「途中でメインがマージされたら、追随して作業を止めずに続行してください」の委任に従い、Task 3 完了後に rebase して再検証した。前進分は issue-to-pr スキル・helper・テストと他 Issue の文書のみで、本 Issue の変更ファイルとは重複しない。
