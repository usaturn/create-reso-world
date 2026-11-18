# Issue #467 agent-workspace 同期 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（issue-to-pr の run。実行許可は Spec の「管理」のとおりで、内容の承認ではない）
- Issue: https://github.com/usaturn/create-reso-world/issues/467

**Goal:** create-reso-world が使っている agent 定義・Pi ラッパー（親と子）・Claude Code のランチャーを、agent-workspace の最終構成（Sol・Astra の新モデル、DeepSeek V4.1 Flash の既定 `high` と Pi の明示的な `max`、Devin SWE-2 の 3 段）に揃え、残す差と既存環境の更新手順を README に書く。

**Architecture:** 参照元のファイルは写さず、対象の値だけを手で移す（Spec の D1）。ファイルの構成・共通ヘルパー・setup の配置処理・env は create-reso-world のものを残す。

**Tech Stack:** TOML（agent-runner の雛形）、zsh（Pi のラッパー・`zshrc.txt`・setup）、bash（`claude-ollama-exec`）、JSON（子 Pi の tier）、Markdown（README）。

**Spec:** `docs/superpowers/specs/2026-11-18-issue-467-agent-workspace-sync-design.md`

## Global Constraints

- 参照元は `usaturn/agent-workspace` `bab7dd2b08a79dd66514e88bd2cfef7093424ae1`。写しは `/workspaces/reso-world/tmp/agents/issue-467.vk70s9bd/ref/`（読み取り用）
- Sol は `gpt-6.2-sol`、Astra は `gpt-6.2-astra`。Terra（`gpt-6.1-terra`）・Luna（`gpt-6-luna`）は変えない。agent 名の `gpt6-sol`・`gpt6-astra` は変えない
- DeepSeek V4.1 Flash の既定は `high`。DeepSeek 以外のモデルの effort・thinking は変えない
- Pi の OpenCode Go・Command Code の `_max` は残す。DeepInfra と Claude Code に `_max` を作らない
- Devin は `devin_swe2_max`・`devin_swe2_high`・`devin_swe2_medium`、どれも `model_key = "swe-2"`
- OpenDesign Go は採用しない（`pigs` の cheap は `opencode-go/deepseek-v4.1-flash`、`pigs` の runner の env は `OPENCODE_API_KEY`）
- `agy_*` を足さない。Command Code を既定の割当に入れない。DSH・Grok Build を入れない
- `pi-superagents-model-guard.ts`・共通ヘルパー（`pi-superagents-exec.zsh`）・`scripts/setup_pi_superagents.zsh` の配置処理・`cc_launcher_unsets` の一覧・`after_run` の `--project .`・`issue.implement` の `self` は変えない
- 恒久テストは Spec の D15 の 2 つ（Task 2・Task 3）だけを足す。既存テストが変更で壊れたら、その期待値だけを合わせる
- 文書は AGENTS.md の「日本語表現」に従う。当時の変更記録（#305・#337・#341 などの表、移植元・実機の観測）は書き換えない

## Review Focus

- runner の `_max`（`--thinking max`）がラッパーの既定 `--thinking high` に打ち消される → 実効は `max` であるべき（Task 2 の追加テストと DRY_RUN の確認）
- Claude Code の複数モデルのランチャーで、DeepSeek 以外（DeepSeek V4 Flash 0731・GLM・Muse Spark）まで `high` になる → `max` のままであるべき（Task 3 の受け口サーバーの確認）
- 親シェルの `CLAUDE_CODE_EFFORT_LEVEL` が残り、`--effort` の既定を上書きする → 外されるべき（Task 3 の追加テスト）
- 子 Pi の tier の DeepSeek 以外の枠（Muse Spark・Grok・Qwen）まで `high` になる → 変えないべき（Task 2 の jq の確認）
- 更新前の tier・個人設定の上書きが残る環境で、古いモデル・古い effort のまま動いても気付けない → README の確認手順で見つけられるべき（Task 4）

## 受け入れ基準

（Spec の「受け入れ基準」と同じ本文。実装担当とタスクレビュー担当の両方の依頼に写す）

### 動作環境

- 既存の Ubuntu Dev Container（Pi 1.5.2、Claude Code 2.1.327、Codex CLI 0.170.0、Devin 3000.14）
- 新規の環境（tier・個人設定が無い）と、更新前の tier・個人設定の上書きがある環境を区別する。確かめるのは一時 HOME での新規配置と、更新前の tier が残る場合の案内（起動前の検査の結果と README の手順）
- 実サービスへの要求はしない。外部 API の実応答は未確認として扱う

### 実入力

- runner の雛形: `uv run --project . --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml --config <空の個人設定> check`・`list`。`--assign inspect=pi_opencode-go_deepseek4-flash_high,pi_opencode-go_deepseek4-flash_max` のように同じ `model_key` を並べた設定は `duplicate_model` で拒否される
- runner の Pi の argv: `pigod --print --mode json --no-session --no-approve --provider opencode-go --model deepseek-v4.1-flash --thinking max`（`_max`）と `--thinking high`（`_high`）を、共通ヘルパーの `PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1` と Pi の `parseArgs` で解析し、実効の thinking がそれぞれ `max`・`high` になる。runner の引数なしの直接起動は `high`
- 子 Pi の tier: setup で一時 HOME に配置した `config.json` の DeepSeek の枠がすべて `high`、DeepSeek 以外の枠は変更前と同じ
- Claude Code: 受け口サーバー（127.0.0.1）に向けた `zshrc.txt` と `claude-ollama-exec` の写しで、`ccdd`（opus）・`ccddg`（fable）・`ccdgo`（opus）の DeepSeek が `high`、`ccdd` の fable（GLM-5.3）と sonnet（DeepSeek V4 Flash 0731）・`ccddg` の opus（GLM-5.3-Flash）・`ccdgo` の sonnet（Muse Spark）が `max`。`ccdol`・`claude-ollama-exec` は `high`、後ろの `--effort max` で `max`、親の `CLAUDE_CODE_EFFORT_LEVEL=max` があっても `high`。プロンプトは改行と日本語を含む 1 件（例: `確認\n日本語の行`）

### 防御範囲

- 対象: Spec の「変更の内容」の agent・ラッパー・tier・ランチャー。DeepSeek V4.1 Flash の判定は provider のモデル ID と Claude Code の別名の割り当てで行う（`opus`・`sonnet` という名前では判定しない）
- 対象外の反例（変えないことを確かめる）: DeepSeek V4 Flash 0731、GLM、Muse Spark、Hy4、gpt-oss、Qwen、Grok、Gemini の effort・thinking。`pigo`・`piccg`・`piaq` の親の `--thinking max`。`ccda`・`claude-alibaba-exec`。Terra・Luna のモデル。`cc_launcher_unsets` の一覧。共通ヘルパー・`pi-superagents-model-guard.ts`・setup の配置処理。利用者の `~/.pi`・`~/.config/agent-runner`（検証は一時 HOME と空の個人設定で行う）
- 残す `_max`: Pi の OpenCode Go・Command Code の `_max` は雛形に残り、`check`・`list` で解決できる

## 実行方式

- 方式: issue-to-pr の「Task の実装を runner の担当に依頼する」（`implement_task.py`、担当は `devin_swe2_max`）。`implement_task.py check` の `self` が false のため（利用者の `--implement devin_swe2_max`）。Task は 1 つずつ順に依頼し、並行しない
- 各 Task の取り込み後、controller が関連テストと静的チェックを実行し、SDD の Task のレビューを読み取り専用のサブエージェントで行う（受け入れ基準の本文を写す）
- `--merge` のため、全 Task の後のブランチ全体のレビューは行わず、PR 修正ループの 1 サイクル目で代える。minor の指摘（ledger の `deferred`）は PR 本文に一覧で書く
- 作業領域: `/workspaces/reso-world/tmp/agents/issue-467.vk70s9bd/sdd/2026-11-18-issue-467-agent-workspace-sync/`（ledger `progress.md`）。実装担当の出力は `issue-467-implement` のセッションディレクトリ

## 要件・Task・検証の対応

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| runner の対象定義（D3・D4・D5・D8・D9） | Task 1 | `check` exit 0、`list` に新名、旧 Ollama `_max` 名が無い、同じ `model_key` の組は `duplicate_model` | Task 1 の手順 |
| 親 Pi・子 Pi（D6・D7・D8）、setup の表示（D13）、テスト D15 (a) | Task 2 | DRY_RUN の実効 thinking、tier の枠ごとの値 | Task 2 の手順、`test-pi-superagents.bash`（追加テストを含む） |
| Claude Code（D10・D11）、テスト D15 (b) | Task 3 | 受け口サーバーの `output_config.effort`、子の環境に親の `CLAUDE_CODE_EFFORT_LEVEL` が無い | Task 3 の手順、`test-herdr-migration.bash`（追加テストを含む） |
| README（D14） | Task 4 | 現行の値の記述、新しい節、旧値の取り残し 0 件 | Task 4 の手順、`test-readme.bash` |
| 共有の条件（モデル ID・agent 名・effort が runner・ラッパー・tier・README で一致する。参照元との採用／除外表） | 統合確認（controller） | 参照元との突き合わせの表、`git grep` の結果 | 下の「統合確認」 |

共有の条件: DeepSeek の判定（provider のモデル ID と Claude Code の別名）、agent 名（Task 1 で決まり、Task 4 の README が参照する）、runner の argv の順序（Task 2・3 の前提）。

---

### Task 1: agent-runner の雛形

**Files:**
- Modify: `.devcontainer/agent-runner.toml`

**Interfaces:**
- Produces: agent 名 `devin_swe2_high`・`pi_commandcode_deepseek4-flash_high`・`pi_opencode-go_deepseek4-flash_high`・`claude-code_ollama_opus_high`・`claude-code_ollama_sonnet_high`（Task 4 の README が参照する）

**テストの要否:** 不要。設定値の写し（F）で、参照切れは `check` のエラーで気付ける（L）。代わりに下の `check`・`list` と `duplicate_model` の確認を行う。

- [ ] **Step 1: 定義を変える**（Spec の「変更の内容」の `agent-runner.toml` の項のとおり）
  - `[agents.devin_swe2_high]` を `devin_swe2_max` と `devin_swe2_medium` の間に足し、前のコメントを「3 つは同じ model_key」にする
  - `[agents.pi_commandcode_deepseek4-flash_high]` を `pi_commandcode_deepseek4-flash_max` の直前に、`[agents.pi_opencode-go_deepseek4-flash_high]` を `pi_opencode-go_deepseek4-flash_max` の直前に足す（`effort = "high"` 以外は直後の `_max` と同じ値）
  - `pi_openai-codex_gpt6-sol_xhigh`・`codex_openai_gpt6-sol_default` の `model = "gpt-6.2-sol"`、`pi_openai-codex_gpt6-astra_xhigh` の `model = "gpt-6.2-astra"`。Codex の前のコメントを `# codex exec --json。model は runner が -m で渡す。Codex CLI のモデル一覧に gpt-6.2-sol がある（2026-11-18）。` にする
  - `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` を `claude-code_ollama_opus_high`・`claude-code_ollama_sonnet_high`（`effort = "high"`）に改名し、前のコメントの agent 名の列挙を今の名前（Pi の DeepSeek は `_high`・`_max` の両方）に直す
  - `[agents.pi_deepinfra_deepseek4-flash_high]` の直前に `# DeepInfra の reasoning_effort の上限は high で、Pi は --thinking max を high に丸めるため _max は置かない（README の「DeepSeek V4.1 Flash の推論強度」）。` を足す
  - `[workflows.review.assignments.inspect]` の `agents` を `["claude-code_opus_xhigh", "devin_swe2_max", "pi_opencode-go_deepseek4-flash_high"]` にする
- [ ] **Step 2: 読み込みと一覧を確かめる**

  Run（リポジトリのルート）:
  ```bash
  empty="$(mktemp -d)"; printf 'schema_version = 1\n' > "$empty/config.toml"
  uv run --project . --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml --config "$empty/config.toml" check
  uv run --project . --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml --config "$empty/config.toml" list
  ```
  Expected: `check` が終了コード 0。`list` に Step 1 の 5 つの新名と、残した `pi_commandcode_deepseek4-flash_max`・`pi_opencode-go_deepseek4-flash_max` があり、`claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` が無い
- [ ] **Step 3: 同じ model_key の拒否を確かめる**

  空の個人設定に `[workflows.review.assignments.inspect]` `agents = ["pi_opencode-go_deepseek4-flash_high", "pi_opencode-go_deepseek4-flash_max"]` を書いた設定で `check` を実行する。Expected: `duplicate_model` で終了コードが 0 でない。`["devin_swe2_high", "pi_opencode-go_deepseek4-flash_high"]` は終了コード 0
- [ ] **Step 4: Commit** — `git add .devcontainer/agent-runner.toml` → `feat(agent-runner): DeepSeek の high と Devin の high を足し、Sol・Astra を 6.2 にする (#467)`

### Task 2: Pi の親・子と setup の表示

**Files:**
- Modify: `.devcontainer/pigs`・`.devcontainer/piga`・`.devcontainer/pigod`・`.devcontainer/piccd`
- Modify: `.devcontainer/pi-superagents/{piga,pigt,pigs,pigl,piccd,piccg,pigo,pigod,pixg}.json`
- Modify: `scripts/setup_pi_opencode_go.zsh`・`scripts/setup_pi_commandcode_goat.zsh`
- Test: `.devcontainer/test-pi-superagents.bash`

**Interfaces:**
- Consumes: なし（Task 1 と独立）
- Produces: 親の `--model`・`--thinking` と tier の値（Task 4 の README が参照する）

**テストの要否:** 1 つだけ足す（Spec の D15 (a)、S）。runner の明示した `--thinking` がラッパーの既定に打ち消されないこと。壊れると runner の `_max` が黙って `high` で動く。値の写し（モデル名・thinking の一覧）は F なので足さない。

- [ ] **Step 0: テストを足す** — `.devcontainer/test-pi-superagents.bash` に `test_runner_thinking_overrides_launcher_default` を足し、末尾の実行一覧に加える。前のコメントに `# S:` で防ぐ損害を書く（「runner の _max は --thinking max をラッパーの既定の後ろに付ける。順序が崩れても起動は成功し、黙って既定の thinking で動く。代表は pigod（piccd は同じ形）」の趣旨）
  - 既存の `make_home`・`run_launcher`・`pi_args_of` を使う（`make_home pigod with-config` で tier と照合の拡張を置き、`run_launcher` で DRY_RUN の argv を得る）
  - runner と同じ引数 `--print --mode json --no-session --no-approve --provider opencode-go --model deepseek-v4.1-flash --thinking <値>` を渡し、`pi_args_of` で取り出した引数を Pi 自身の `parseArgs`（`command -v pi` の実体から上へたどった `dist/cli/args.js`。共通ヘルパーの `pi_launcher_require_models` と同じ探し方）で解析する
  - assert: `<値>` が `max` のとき実効の thinking が `max`、`high` のとき `high`。どちらも model は `deepseek-v4.1-flash`
- [ ] **Step 0b: テストを走らせる** — `bash .devcontainer/run-tests.bash .devcontainer/test-pi-superagents.bash`。Expected: PASS（base でも順序は正しいので通る。壊れたときに落ちることは controller が一時的な写しで確かめる）

- [ ] **Step 1: 親のラッパーを変える**
  - `pigs`: `--model gpt-6.2-sol`。`piga`: `--model gpt-6.2-astra`
  - `pigod`: `--thinking high`。直前のコメントの「`--thinking max` はこのエンドポイントで受理される。pi は thinkingLevelMap の max -> "max" をそのまま reasoning_effort として送る。」を「`--thinking high` はこのエンドポイントで受理される。pi は thinkingLevelMap に対応する値が無い high もそのまま reasoning_effort として送る。runner の `_max` は後ろに `--thinking max` を付けるので、Pi は後ろの値を使う。」にする
  - `piccd`: `--thinking high`
- [ ] **Step 2: 子の tier を変える**（`thinking` は DeepSeek の枠だけ）
  - GPT: `piga.json` balanced `openai-codex/gpt-6.2-sol`・max `openai-codex/gpt-6.2-astra`、`pigt.json` balanced `openai-codex/gpt-6.2-sol`、`pigs.json` balanced・max `openai-codex/gpt-6.2-sol`、`pigl.json` balanced・max `openai-codex/gpt-6.2-sol`
  - DeepSeek の `thinking: "high"`: `piccd.json` balanced・max、`piccg.json` max、`pigo.json` max、`pigod.json` balanced・max、`pigs.json` cheap、`pixg.json` cheap・balanced
- [ ] **Step 3: setup の表示を分ける**
  - `scripts/setup_pi_opencode_go.zsh`: `readonly THINKING="max"` を `readonly LAUNCHER_THINKING=(max high)`（`LAUNCHER_NAMES=(pigo pigod)` と同じ順）にし、`Thinking :` の行を `${LAUNCHER_THINKING[*]}`、Launchers の各行を `(--model ${LAUNCHER_MODELS[_i]}, --thinking ${LAUNCHER_THINKING[_i]})`、引数の例の `--thinking` を `--thinking <the value shown above>` にする
  - `scripts/setup_pi_commandcode_goat.zsh`: `readonly THINKING="max"` を `readonly PICCG_THINKING="max"`・`readonly PICCD_THINKING="high"` にし、`Thinking :` の行を `piccg ${PICCG_THINKING} / piccd ${PICCD_THINKING}`、piccg・piccd の引数の例をそれぞれの変数にする
- [ ] **Step 4: 値を確かめる**

  Run:
  ```bash
  for f in .devcontainer/pi-superagents/*.json; do jq -c --arg f "${f##*/}" '.superagents.modelTiers | to_entries[] | {f:$f, tier:.key, model:.value.model, thinking:.value.thinking}' "$f"; done | grep -iE 'deepseek|gpt-6'
  zsh -n .devcontainer/pigs .devcontainer/piga .devcontainer/pigod .devcontainer/piccd scripts/setup_pi_opencode_go.zsh scripts/setup_pi_commandcode_goat.zsh
  ```
  Expected: DeepSeek（`deepseek-v4.1-flash`・`DeepSeek-V4.1-Flash-1017`）の行がすべて `thinking` `high`。GPT の Sol・Astra の行が `gpt-6.2-*`。DeepSeek 以外の `thinking` は変更前と同じ（`git diff` で DeepSeek と GPT の行だけが変わる）。`zsh -n` がすべて終了コード 0
- [ ] **Step 5: 既存テスト** — `bash .devcontainer/run-tests.bash .devcontainer/test-pi-superagents.bash`。Expected: PASS
- [ ] **Step 6: Commit** — 上の Files → `feat(pi): Sol・Astra を 6.2 にし、DeepSeek の親子の既定を high にする (#467)`

controller が取り込み後に行う確認（実装担当は不要）: (1) 一時 HOME（`models.json`・`models-store.json` を写し、`scripts/setup_pi_superagents.zsh` で tier を配置）で `PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1` の `pigod`・`piccd`・`pigs`・`piga` を、runner の argv の有無で実行し、出力の argv を Pi の `parseArgs` で解析して実効の `model`・`thinking` を確かめる（`verify-pi.bash`）。(2) `pigod` の `"$@"` を既定の引数より前に動かした一時的な写しで、Step 0 のテストが落ちることを確かめる（写しは commit しない）。

### Task 3: Claude Code のランチャー

**Files:**
- Modify: `.devcontainer/zshrc.txt`（`ccdd`・`ccddg`・`ccdgo`・`ccdol` の関数だけ）
- Modify: `.devcontainer/claude-ollama-exec`
- Test: `.devcontainer/test-herdr-migration.bash`

**Interfaces:**
- Consumes: なし
- Produces: ランチャーの effort の渡し方（Task 4 の README が参照する）

**テストの要否:** 1 つだけ足す（Spec の D15 (b)、S）。親シェルの `CLAUDE_CODE_EFFORT_LEVEL` を子の `claude` に渡さないこと。この変更でランチャーの代入をやめるので、`-u` が抜けると親の値が `--effort` の既定に黙って勝つ。effort の値そのもの（F）と Claude Code の送信値は、controller が受け口サーバーで確かめる。

- [ ] **Step 0: 失敗するテストを書く** — `.devcontainer/test-herdr-migration.bash` に `test_cc_launchers_drop_parent_effort_level` を足し、末尾の実行一覧に加える。前のコメントに `# S:` で防ぐ損害を書く
  - 偽の `claude`（既存の `make_claude_probe` の形。子の環境の `CLAUDE_CODE_EFFORT_LEVEL` を記録する。既存の `keys` に足すか、テスト専用の probe を作る）
  - 親に `CLAUDE_CODE_EFFORT_LEVEL=parent-sentinel` を置き、`ccdd`・`ccddg`・`ccdgo`・`ccdol` を `run_zshrc_code` で、`claude-ollama-exec` を既存の `claude-ollama-exec` のテスト（`install -m 0755` で一時 HOME の `~/.local/bin` に置く形）と同じように起動する（キーは偽の値）
  - assert: 5 つとも、子の環境に `CLAUDE_CODE_EFFORT_LEVEL` が無い（`None`）
- [ ] **Step 0b: 失敗を確かめる** — `bash .devcontainer/run-tests.bash .devcontainer/test-herdr-migration.bash`。Expected: FAIL（変更の前は、ランチャーが代入した `max` が子に届く）

- [ ] **Step 1: 複数モデルの 3 関数**（Spec の D10）
  - `ccdd`・`ccddg`・`ccdgo` の `env "${cc_launcher_unsets[@]}"` を `env "${cc_launcher_unsets[@]}" -u CLAUDE_CODE_EFFORT_LEVEL` にし、`CLAUDE_CODE_EFFORT_LEVEL=max \` の行を消す
  - 各関数に `local effort_cap="{\"modelSettings\":{\"<ID>\":{\"maxEffortLevel\":\"high\"}}}"` を足す。`<ID>` は `ccdd` が `${opus}`、`ccddg` が `${fable}`、`ccdgo` が `${opus%\[1m\]}`
  - 起動を `claude --effort max --settings "${effort_cap}" --model opus "${opts[@]}" "$@"` にする
  - 関数の前（共通の場所でよい）に、「DeepSeek V4.1 Flash だけを `maxEffortLevel` で `high` に抑え、他のモデルは `--effort max` のまま。後ろの `--effort` は上限以下で効き、後ろの `--settings` で上限を外せる。`CLAUDE_CODE_EFFORT_LEVEL` は `--effort` より優先されるので親の値を外す（#467）」の趣旨のコメントを書く
- [ ] **Step 2: Ollama**（Spec の D11）
  - `ccdol`: `env "${cc_launcher_unsets[@]}" -u CLAUDE_CODE_EFFORT_LEVEL`、`CLAUDE_CODE_EFFORT_LEVEL=max \` を消し、`claude --effort high --model opus "${opts[@]}" "$@"`
  - `claude-ollama-exec`: `exec env` の `-u` の並びに `-u CLAUDE_CODE_EFFORT_LEVEL` を足し、`CLAUDE_CODE_EFFORT_LEVEL=max \` を消し、`claude --effort high "$@"` にする。冒頭のコメントの呼び出し元を `claude-code_ollama_opus_high`・`claude-code_ollama_sonnet_high` にし、`--effort high` を既定にして後ろの `--effort` を優先すること、親の `CLAUDE_CODE_EFFORT_LEVEL` を外す理由を書く
  - `ccda`・`claude-alibaba-exec`・`cc_launcher_unsets` は変えない
- [ ] **Step 3: 構文とテスト** — `zsh -n .devcontainer/zshrc.txt`・`bash -n .devcontainer/claude-ollama-exec`、`bash .devcontainer/run-tests.bash .devcontainer/test-herdr-migration.bash`。Expected: 終了コード 0、PASS（Step 0 のテストを含む）
- [ ] **Step 4: Commit** — 上の Files → `feat(claude): DeepSeek V4.1 Flash の既定 effort を high にする (#467)`

controller が取り込み後に行う確認: `zshrc.txt` と `claude-ollama-exec` の写しの接続先を `http://127.0.0.1:<port>` に置き換え、一時 HOME・偽 token で受け口サーバー（`/tmp/claude-1000/-workspaces-reso-world/7f748098-a55a-42ba-b6eb-bb2acef859e3/scratchpad/fake_anthropic.py`）につないで、受け入れ基準の実入力の Claude Code の行を確かめる。

### Task 4: README

**Files:**
- Modify: `.devcontainer/README.md`

**Interfaces:**
- Consumes: Task 1〜3 の agent 名・モデル・effort（取り込み済みのファイルを読む）

**テストの要否:** 不要。文書（F）。代わりに `test-readme.bash` と `git grep` の確認を行う。

- [ ] **Step 1: 現行の値の記述を直す**（Spec の「変更の内容」の README の項の各節。「pi-superagents のランチャー別 model tier」は表のモデルと、表の下の thinking の説明（`pigs` の cheap、`pixg` の cheap・balanced を `high`）の両方）。当時の変更記録（#305 の表、#337・#341 の記録、移植元・実機の観測の節）は書き換えない
- [ ] **Step 2: 新しい節を足す** — 「Devin の agent 名の変更（#341）」の後に `### agent-workspace の現行構成との同期（#467）` を足し、Spec の D14 の 5 項目（推論強度、`max` の agent、既存環境の更新、個人設定の確認、参照元との残す差）を書く。個人設定の確認のコマンドは次を含める:
  ```bash
  # (1) 旧モデル・旧名
  grep -n -E 'gpt-6\.1-sol|gpt-6-astra|claude-code_ollama_(opus|sonnet)_max' ~/.config/agent-runner/config.toml
  # (2) この Issue で値を変えた・足した agent の節の上書き。あれば雛形の同じ節と model・effort・provider・env を見比べる
  grep -n -A8 -E '^\[agents\.(pi_openai-codex_gpt6-(sol|astra)_xhigh|codex_openai_gpt6-sol_default|pi_(opencode-go|commandcode)_deepseek4-flash_(high|max)|claude-code_ollama_(opus|sonnet)_high|devin_swe2_high)\]' \
    ~/.config/agent-runner/config.toml
  ```
  個人設定の場所は README の「非対話エージェントのランナー（agent-runner）」の既存の説明（`AGENT_RUNNER_CONFIG`、`XDG_CONFIG_HOME`、既定は `~/.config/agent-runner/config.toml` の順に 1 か所）に合わせて書く。Spec の D14 の「個人設定の確認」の (1)〜(3)（直し方と、`list` に上書きが出ないこと）を書く
- [ ] **Step 3: 取り残しを確かめる**

  Run: `git grep -n -E 'gpt-6\.1-sol|gpt-6-astra|claude-code_ollama_(opus|sonnet)_max|CLAUDE_CODE_EFFORT_LEVEL' -- .devcontainer/README.md`
  Expected: 残る行は、当時の記録・移行の説明（旧名から新名への対応、確認コマンド）・Alibaba（`ccda`）の effort だけ。各行を確認して理由を報告に書く
- [ ] **Step 4: 既存テスト** — `bash .devcontainer/run-tests.bash .devcontainer/test-readme.bash`。Expected: PASS
- [ ] **Step 5: Commit** — `git add .devcontainer/README.md` → `docs(devcontainer): agent-workspace 同期の値と既存環境の更新手順を書く (#467)`

## 統合確認（controller）

全 Task の取り込み後、PR の前に controller が行う。

1. 参照元（`ref/.devcontainer`）と変更後の `agent-runner.toml`・ラッパー・tier・`zshrc.txt` を突き合わせ、Spec の「参照元との残す差」以外の差が無いことを表にする（PR 本文に書く）
2. `git grep` で旧モデル・旧 effort の取り残しを確かめる（`.agents/` の評価記録・テスト、`docs/superpowers/` の過去の文書は除く）
3. Task 2・3 の controller の確認（DRY_RUN、受け口サーバー）
4. 全体の検証: `bash .devcontainer/run-tests.bash`、`uv run --project . --locked pytest tools/agent_runner -q`、`bash scripts/check-layout.sh`

## 実行予算

- Issue 全体の能動時間: 480 分（Issue の見積もり 2〜5 時間に、外部担当の Spec・設計レビュー、4 Task の外部実装と、`--merge` のループ 3 サイクル ×（レビュー 45 分＋計画・修正 30 分）を足した）
- phase の目安: 準備・Spec・レビュー 80 分、実装（4 Task、依頼と取り込み・レビュー）160 分、統合確認・検証 30 分、PR 作成 10 分、PR 修正ループ 200 分
- worker: 実装担当は runner の `implement` の期限 90 分（`deadline_seconds = 5400`）。レビューの担当は 30 分（spec-review・design-review）。controller は完了通知で待ち、ログは 10 分ごとに mtime・サイズを見る。事前宣言の打ち切りは使わない（実装担当は共有の feature worktree に取り込むため）
- 再試行の上限: 同じ失敗は 1 回まで（`retry`・`rejected` は Task ごとに依頼し直し 1 回）。`failed` は再試行せず止まる。テストの失敗は `systematic-debugging` で調べ、同じ原因で 2 回失敗したら止まる
- checkpoint: Spec レビュー後、各 Task の取り込み後、統合確認の後、PR 作成後、予算の 50%（240 分）・100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) README の新しい節を短くし、細部を PR 本文に移す、(2) Task 4 の取り残しの修正を、現行の値の表と新しい節に絞る、(3) 実装担当が `failed` のときは、その Task で止まって利用者に担当の変更を求める（`self` で引き取らない）

## contingency（代替策）

- Pi の保存済みカタログに `gpt-6.2-*` が無い一時 HOME で、起動前の検査が止まる → 実環境の `models-store.json` を写して確かめる。それでも無ければ、README の `pi update --models` の手順の確認に切り替え、未確認として PR に書く
- 受け口サーバーの確認で、Claude Code の版の違いにより `maxEffortLevel` が効かない → 2.1.327 で確かめた事前確認の記録と比べ、版を記録する。効かない場合は利用者の裁定を待つ（D10 の方法の前提が崩れるため）
- 既存テストが変更と無関係の理由で落ちる → base（`9d5b25af`）で同じテストを実行して切り分ける。base でも落ちるなら記録して続ける
- 実装担当が `retry`（`BLOCKED`・`NEEDS_CONTEXT`）→ `concerns`・`incomplete` に答える文脈を足して 1 回だけ依頼し直す
- 最初の確認で前提（runner の argv の順、Pi の `parseArgs`、Claude Code の上限の効き方）が違うと分かった → 仕様の意味を保つ最小の修正を ledger に書いて続ける。意味が変わるなら止まる
