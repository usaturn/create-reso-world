# Issue #401 ランチャー起動セッションの runner 用 key wrapper と Alibaba の runner agent 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`（issue-to-pr の実行許可で進める。内容の承認は得ていない）

**Goal:** `tools/agent_runner/with_keys.py` を足して runner を起動する手順をその wrapper 経由にし、Alibaba の runner agent（`claude-code_alibaba_opus_max`・`.devcontainer/claude-alibaba-exec`）を足す。

**Architecture:** wrapper は runner と同じ設定（雛形 + `resolve_config_path()` の個人設定）を `load_config` で読み、全 agent の `env` の和集合のうち、今の環境に無いか空の名前だけを `~/.config/create-reso-world/env` から静的に解析して補い、`os.execvpe` で後ろのコマンドを起動する。runner を起動するスキルのコマンドと `loop.py` の `command("review")` を wrapper 経由にする。`claude-alibaba-exec` は `ccda` と同じ値・同じキーの確認の bash スクリプト。

**Tech Stack:** Python 3.14（uv）、pytest、bash（`.devcontainer/` のスクリプトとテスト）、TOML、Markdown。

**Spec:** `docs/superpowers/specs/2026-11-11-issue-401-runner-key-wrapper-design.md`（設計レビュー・Spec レビュー・再レビューを反映した版。reflected の SHA-256 `6570d905427a25078424d19ada632933092c323252822359f2d1364c6ac224f7`）

**実行方式:** Task の実装は runner の担当 `pi_xai_grok4_xhigh`（`--implement` の明示、`self` は false）に `implement_task.py run` で 1 Task ずつ順に依頼する（issue-to-pr の「Task の実装を runner の担当に依頼する」）。Task 1〜3 は担当ファイルが重ならないが、runner の担当は入れ子に起動できず、取り込みは `--ff-only` なので並行しない。Task 4 は controller が行う

## Global Constraints

- wrapper の読み元は今の環境 → `~/.config/create-reso-world/env` だけ。`keys.env`・`~/.zshrc` は読まない
- 補う名前は全 agent の `env` の和集合から `HOME`・`PATH`・`GIT_*` を除いたもの。今の環境に値がある名前は上書きしない
- env ファイルは shell として実行しない。値を stderr・ログに出さない
- 起動の形: `uv run --project "$PARENT_ROOT" --locked python "$PARENT_ROOT/tools/agent_runner/with_keys.py" [--template PATH] [--config PATH] -- python <helper> ...`。helper に `--template`・`--config` を渡すときは wrapper にも同じ値を渡す
- 補う名前への解析できない代入（`$` の展開など）が env ファイルにあれば、その名前は前の行の値も含めて補わない
- `claude-alibaba-exec`: `#!/bin/bash -p`、`shopt -s globasciiranges` と `[[ $key == *[A-Za-z0-9]* ]]` の確認、`ANTHROPIC_AUTH_TOKEN` だけ（`ANTHROPIC_API_KEY` なし）、`env -u MAAS_ANTHROPIC_TOKEN` と `cc_launcher_unsets` の名前のうち自分で設定しないもの（`ANTHROPIC_API_KEY`・`CLAUDE_CODE_OAUTH_TOKEN` など）の `-u`、接続先・モデル・`ENABLE_CLAUDEAI_MCP_SERVERS=false`・`CLAUDE_CODE_EFFORT_LEVEL=max`・`CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536` は `zshrc.txt` の `ccda` と同じ
- テストは AGENTS.md の「テストの採用基準」の S・F∩S だけ。偽の key は実行時に組み立てる（gitleaks の検出を避ける）。実キー・課金 API をテストで使わない
- 対象外: `cc_launcher_unsets` とランチャー関数、runner 本体の環境の組み立て、各 adapter、pi の `auth.json`、Ollama の runner agent、ステータスライン、pr-review の `review_run.py`、`AGENTS.md` の「エージェント運用」の一文以外、利用者の env ファイル・個人設定

## 受け入れ基準

- 動作環境: Dev Container（WSL2 上の Ubuntu 26.04）、uv の Python 3.14、worktree `/workspaces/reso-world/.worktrees/issue-401-runner-key-wrapper` のルートを cwd にする。runner の担当の中では `AGENT_RUNNER_DEPTH=1` なので `python -m tools.agent_runner check` は `nested_invocation` で拒否される。担当は `load_config` と pytest で確かめ、`check` は司令塔が行う。自動テストは一時 HOME・偽の key・stub の `claude` だけを使う
- 実入力: env ファイルの実際の形。例:

  ```text
  # comment
  COMMANDCODE_API_KEY=<偽の値>
  export OPENCODE_API_KEY="<偽の値>"
  MESHY_API_KEY='<偽の値>'

  DEEPINFRA_TOKEN=<偽の値>
  DEEPINFRA_TOKEN="$(touch /path/to/marker)"
  ```

  `claude-alibaba-exec` のキーは ASCII の空白・NBSP（U+00A0）・BOM（U+FEFF）・全角空白（U+3000）だけの値と、英数字を含む偽の値
- 防御範囲:
  - 対象: (1) `agent.env` にある名前（例 `COMMANDCODE_API_KEY`）が今の環境に無ければ env ファイルから子に届く。(2) 今の環境に値がある名前（例 `OPENCODE_API_KEY`）は env ファイルの別の値で上書きされない。(3) どの agent の `env` にも無い名前（例 `MESHY_API_KEY`）は env ファイルにあっても子に届かない。(4) `$(...)` を含む行は実行されず、その名前（例 `DEEPINFRA_TOKEN`）は前の literal の行があっても補われない。(5) key の値が wrapper の stderr に出ない。(6) `claude-alibaba-exec` は英数字を含まない key で非 0 で止まり `claude` を起動しない。正しい key では `ANTHROPIC_AUTH_TOKEN` だけを渡し、親にあっても `ANTHROPIC_API_KEY`・`CLAUDE_CODE_OAUTH_TOKEN`・`MAAS_ANTHROPIC_TOKEN` を子に残さず、接続先は Token Plan
  - 対象外（反例）: key がどこにも無いときの起動（今と同じエラーで失敗する）、ランチャー起動セッションからの Alibaba・Ollama の key の補い、個別の provider の実機の起動確認（マージの後）

## Review Focus

1. 今の環境の key を env ファイルの値で上書きする → `test_with_keys.py`（Task 1）
2. `agent.env` に無い名前が子に届く → `test_with_keys.py`（Task 1）
3. env ファイルの行を shell として評価する・解析できない再代入の前の literal を使う → `test_with_keys.py` の `$(...)` 行（Task 1）
4. key の値が stderr に出る → `test_with_keys.py`（Task 1）
5. 空白だけの `MAAS_ANTHROPIC_TOKEN` で `claude` が起動する・`ANTHROPIC_API_KEY` が子に残る → `test_alibaba_exec_requires_key`（Task 2）
6. runner を起動する手順に wrapper を通さない箇所が残る → Task 3 の `rg` の確認

## 要件・Task・検証の対応

| Spec の条件 | Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| wrapper の補う名前・条件・解析・出力 | 1 | 子の環境の JSON、stderr、目印のファイルの不在 | `test_with_keys.py` |
| wrapper の usage・設定の読み込みの失敗 | 1 | 終了コード 2 | 手で実行（テストにしない。L） |
| `claude-alibaba-exec` のキーの確認・子の環境 | 2 | 非 0・stub の不起動、stub の env | `test_alibaba_exec_requires_key` |
| agent-runner.toml の agent | 2 | `check` の成功、`list` に出る | controller が `check`・`list`（Task 4） |
| install_beforehand の配置 | 2 | 差分 | `git diff`、`bash -n` |
| runner を起動する経路 | 3 | 各箇所が wrapper 経由、`loop.py` の `next` | `rg`、`uv run --locked pytest .agents/skills/pr-review-fix-loop` |
| README | 3 | 書き換えた箇所 | `git diff`、`test-readme.bash`、`check-layout.sh` |

共有する条件: wrapper のパスと起動の形を Task 1（実装）・Task 3（手順と README）が共有し、agent 名・exec 名・env の名前を Task 2・Task 3 が共有する。controller（Task 4）が `git diff` で照合する。

---

### Task 1: wrapper とテスト

**テスト:** 要る（S。上書き・補いすぎ・shell の評価・値の漏れは壊れてもエラーにならない）。

**Files:**
- Create: `tools/agent_runner/with_keys.py`
- Create: `tools/agent_runner/tests/test_with_keys.py`

**Interfaces:**
- Produces: CLI `python tools/agent_runner/with_keys.py -- <command> [args...]`

- [ ] **Step 1: テストを先に書く**

  `tools/agent_runner/tests/test_with_keys.py` に 1 件のテストを書く。

  - `tmp_path` に `home/.config/create-reso-world/env` を作る。偽の値は `"-".join(["fake", "deepinfra", "value"])` のように実行時に組み立てる
  - env ファイルの内容: コメント行、空行、`COMMANDCODE_API_KEY=<偽 A>`、`export OPENCODE_API_KEY="<偽 B>"`、`MESHY_API_KEY='<偽 C>'`、`DEEPINFRA_TOKEN=<偽 E>`、最後に `DEEPINFRA_TOKEN="$(touch <tmp_path>/marker)"`
  - 子の環境: `HOME=<tmp home>`、`PATH=os.environ["PATH"]`、`AGENT_RUNNER_CONFIG=<tmp_path>/missing/config.toml`（存在しない。利用者の個人設定を読まない）、`OPENCODE_API_KEY=<偽 D>`（今の環境の値）
  - `subprocess.run([sys.executable, str(WRAPPER), "--", sys.executable, "-c", "import json, os; print(json.dumps(dict(os.environ)))"], env=..., capture_output=True, text=True)`
  - 確かめること: 終了コード 0。`COMMANDCODE_API_KEY == 偽 A`。`OPENCODE_API_KEY == 偽 D`。`"MESHY_API_KEY" not in 子の環境`。`"DEEPINFRA_TOKEN" not in 子の環境`（前の literal に戻らない）。`<tmp_path>/marker` が無い。stderr に偽 A〜E のどれも含まれない。stderr に `COMMANDCODE_API_KEY` が含まれる
  - docstring とコメントに、守る損害（別のアカウントの key で外部へ要求を送る、allowlist の外の秘密情報が runner に入る、env ファイルの行が実行される、値がログに出る）を書く

- [ ] **Step 2: 失敗を確かめる**

  Run: `uv run --locked pytest tools/agent_runner/tests/test_with_keys.py -q`
  Expected: 失敗（`with_keys.py` が無く、子の起動が失敗して終了コードが 0 でない）

- [ ] **Step 3: wrapper を実装する**

  Spec の「wrapper の仕様」のとおりに実装する。移植元の `tools/agent_runner/with_keys.py`（usaturn/agent-workspace PR #929）を元にしてよい。違い: 読み元は `Path.home() / ".config/create-reso-world/env"` の 1 つだけで、`export` の有無を問わない。`--` の前に `--template PATH`・`--config PATH` を受け付ける（無ければ雛形は同じ checkout の `.devcontainer/agent-runner.toml`、個人設定は `resolve_config_path()` のファイルがあればそれ）。補う名前への代入に見える行（`^[ \t]*(export[ \t]+)?NAME=`）を解析できなければ、その名前の候補を捨てて以後の行でも補わず、`with_keys: skipped <名前> (unparsable assignment in <パス>)` を stderr に出す。`ConfigError` は分類名（`str(error)`）だけを出して終了コード 2。補ったときの stderr は `with_keys: filled <名前, ...> from <パス>` の 1 行。モジュールの docstring に、なぜ exec し直すか（runner は `/proc/self/environ` から子の環境を組み立てる）を書く

- [ ] **Step 4: 通ることと静的チェック**

  Run: `uv run --locked pytest tools/agent_runner/tests/test_with_keys.py -q && uv run --locked ruff check tools/agent_runner && uv run --locked ruff format --check tools/agent_runner`
  Expected: すべて終了コード 0（ruff が設定に無ければ、その旨を報告して pytest の結果だけを使う）

- [ ] **Step 5: 守りが効くことを一時的に確かめる（commit しない）**

  `fill_environment` の「今の環境に値がある名前を除く」条件を一時的に外して Step 4 の pytest を実行し、`OPENCODE_API_KEY` の assert で失敗することを確かめてから元に戻す（`git diff` で戻ったことを確かめる）

- [ ] **Step 6: commit**

  ```bash
  git add tools/agent_runner/with_keys.py tools/agent_runner/tests/test_with_keys.py
  git commit -m "feat: add with_keys wrapper for launcher sessions (#401)"
  ```

### Task 2: Alibaba の runner agent

**テスト:** 要る（S・F∩S。空白だけの key での起動と、認証情報の送り先は壊れてもエラーにならない）。

**Files:**
- Create: `.devcontainer/claude-alibaba-exec`（mode 0755）
- Modify: `.devcontainer/agent-runner.toml`（`pi_deepinfra_deepseek4-flash_high` の後）
- Modify: `.devcontainer/install_beforehand.bash`（「Placing the launchers」の段）
- Modify: `.devcontainer/test-herdr-migration.bash`（新しい `test_alibaba_exec_requires_key` と末尾の実行の一覧）

**Interfaces:**
- Produces: agent `claude-code_alibaba_opus_max`、実行ファイル `claude-alibaba-exec`

- [ ] **Step 1: テストを先に書く**

  `test-herdr-migration.bash` に `test_alibaba_exec_requires_key` を足す。

  - テスト用 HOME（`${TEST_ROOT}/home-alibaba-exec-key`）を `make_stub_home` で作り、`install -m 0755 "${REPO_ROOT}/.devcontainer/claude-alibaba-exec" "$test_home/.local/bin/claude-alibaba-exec"`（`mkdir -p` を先に）
  - stub の `claude`: 起動したら `env` を `$HERDR_TEST_CLAUDE_DUMP` に書く
  - 拒否: `env -i HOME="$test_home" PATH="$test_home/.local/bin:$test_home/bin:/usr/bin:/bin" HERDR_TEST_CLAUDE_DUMP="$log" MAAS_ANTHROPIC_TOKEN=$' \xc2\xa0\xef\xbb\xbf\xe3\x80\x80' "$test_home/.local/bin/claude-alibaba-exec" probe` が非 0 で、ログが空
  - 通る例: 親の環境に偽の `ANTHROPIC_API_KEY=fake-anthropic`・`CLAUDE_CODE_OAUTH_TOKEN=fake-oauth` を置き、偽の key（`fake-maas` のような英数字を含む値）で起動する。終了コード 0、ログに `^ANTHROPIC_AUTH_TOKEN=fake-maas$` と `^ANTHROPIC_BASE_URL=https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic$` があり、`^ANTHROPIC_API_KEY=`・`^CLAUDE_CODE_OAUTH_TOKEN=`・`^MAAS_ANTHROPIC_TOKEN=` が無い
  - コメントは `# S:` で始め、損害（ガードが外れても起動は成功し、claude.ai の認証情報が `maas.aliyuncs.com` に送られる。`ANTHROPIC_API_KEY` が残ると承認まで OAuth が送られうる）と、`env -i` で locale を渡さない理由を書く
  - 末尾の実行の一覧の `test_alibaba_launcher_requires_key` の後に足す

- [ ] **Step 2: 失敗を確かめる**

  Run: `bash .devcontainer/test-herdr-migration.bash`
  Expected: 終了コード 1（`claude-alibaba-exec` が無く install が失敗する）

- [ ] **Step 3: 実装する**
  - `.devcontainer/claude-alibaba-exec`: Spec の「`.devcontainer/claude-alibaba-exec`」のとおり。移植元のファイル（PR #929）を元にし、キーの確認を `shopt -s globasciiranges` と `if [[ $key != *[A-Za-z0-9]* ]]; then ... exit 1; fi` に替える。`exec env` には `-u MAAS_ANTHROPIC_TOKEN` に加え、`zshrc.txt` の `cc_launcher_unsets` の名前のうち自分で設定しないものをすべて `-u` で並べ、`cc_launcher_unsets` と揃えるとコメントに書く。案内文は `claude-alibaba-exec: MAAS_ANTHROPIC_TOKEN is not set, empty, or has no letters or digits; export the Alibaba Cloud Model Studio Token Plan key before starting agent-runner`。コメントの出典は #401（移植元 usaturn/agent-workspace#927）、`ccda` と揃えること。`chmod 0755`
  - `.devcontainer/agent-runner.toml`: Spec のとおりの `[agents.claude-code_alibaba_opus_max]` と前のコメント
  - `.devcontainer/install_beforehand.bash`: 段の見出しに `claude-alibaba-exec` を足し、`pigema` の配置の後に `if ! install -m 0755 .devcontainer/claude-alibaba-exec "${HOME}/.local/bin/claude-alibaba-exec"; then fail "Failed to place claude-alibaba-exec."; fi`

- [ ] **Step 4: 通ることを確かめる**

  Run: `bash .devcontainer/test-herdr-migration.bash && bash -n .devcontainer/install_beforehand.bash && bash -n .devcontainer/claude-alibaba-exec`
  Expected: すべて終了コード 0、`PASS: herdr Dev Container migration`
  Run: `uv run --locked python -c "from pathlib import Path; from tools.agent_runner.config import load_config; c = load_config(Path('.devcontainer/agent-runner.toml')); print(c.agents['claude-code_alibaba_opus_max'])"`
  Expected: 終了コード 0、agent が表示される

- [ ] **Step 5: ガードが効いていることを一時的に確かめる（commit しない）**

  キーの確認を一時的に `[[ -z $key ]]` に変えて Step 4 のテストを実行し、拒否の assert で失敗することを確かめてから元に戻す

- [ ] **Step 6: commit**

  ```bash
  git add .devcontainer/claude-alibaba-exec .devcontainer/agent-runner.toml .devcontainer/install_beforehand.bash .devcontainer/test-herdr-migration.bash
  git commit -m "feat: add claude-code_alibaba_opus_max runner agent (#401)"
  ```

### Task 3: runner を起動する手順と README

**テスト:** 要らない（手順・README の文言は F。`loop.py` の `next` の形は L）。代わりに `rg`、既存の pytest、`test-readme.bash`、`check-layout.sh`、`git diff`。

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`
- Modify: `.agents/skills/pr-review-fix-loop/scripts/loop.py`（`command()`）
- Modify: `.agents/skills/review-fix-planning/references/execution.md`
- Modify: `.agents/skills/review-verify/references/fix-check.md`
- Modify: `.agents/monitoring-runtimes.md`
- Modify: `.devcontainer/README.md`
- Modify: `AGENTS.md`（「エージェント運用」の agent-runner の一文）
- Modify: `tools/agent_runner/interfaces.rst`（「CLI と API」の `run` の例）

**Interfaces:**
- Consumes: Task 1 の CLI、Task 2 の agent 名と exec 名

- [ ] **Step 1: 手順を書き換える**

  Spec の「runner を起動する経路の変更」の表のとおり。各コマンドは次の形にし、直後に Spec の 1 文を足す。

  ```bash
  uv run --project "$PARENT_ROOT" --locked python "$PARENT_ROOT/tools/agent_runner/with_keys.py" -- \
    python "$SKILL_DIR/scripts/implement_task.py" run \
    --request "$REQUEST_JSON" --output-dir "$RUN_DIR" [--implement <値>]
  ```

  execution.md では、その文書が使う変数（`$TOPLEVEL`）のまま `"$TOPLEVEL/tools/agent_runner/with_keys.py"` にする。`loop.py` は、`review` の `next` を `["uv", "run", "--project", str(ROOT), "--locked", "python", str(ROOT / "tools/agent_runner/with_keys.py"), "--template", <run.options.template>, ("--config", <run.options.config> があれば), "--", "python", str(HELPER), "review", "--run", <run_dir>]` にする。`review` の `next` を作る箇所（`command("review", ...)` の呼び出し）すべてで、その run の保存済みの `options.template`・`options.config` を使う。docstring に理由を書く（`ROOT` が `PARENT_ROOT` を指すことを先に確かめる）。`interfaces.rst`・README の CLI の `run` の例が `--config` を示すときは、同じ値を `with_keys.py` の `--` の前と runner のサブコマンドの前の両方に置き、省略する既定では両方とも同じ設定を使うと書く。`interfaces.rst` の Python API の例には、同じプロセスで `run_workflow` を呼ぶと wrapper を通せないので、ランチャー起動セッションではプロセス自体を `with_keys.py` 経由で起動するか CLI の `run` を使う、と注記する。issue-to-pr の SKILL.md（`implement_task.py`・`review_spec.py`・`review_design.py`）、execution.md、fix-check.md には、helper に `--template`・`--config` を渡すときは wrapper の `--` の前にも同じ値を渡すこと、渡さない既定では何も足さなくてよいことを書く。`AGENTS.md` の一文には「`run` で担当を起動するときは `tools/agent_runner/with_keys.py` 経由にする（`.devcontainer/README.md` の「API トークン」節）。`check`・`list` はそのまま」の趣旨を足し、`interfaces.rst` の `run` の例を wrapper 経由にする

- [ ] **Step 2: README を書き換える**

  Spec の「ドキュメント」の各項目をすべて反映する。移植元の README の該当部分は PR #929 の `.devcontainer/README.md`（`gh pr diff 929 --repo usaturn/agent-workspace`）にある。読み元・`keys.env`・`~/.zshrc` の記述は本リポジトリの決定（`~/.config/create-reso-world/env` だけ）に置き換え、Ollama の runner agent の記述は取り込まない。プロバイダの表は本リポジトリの雛形の agent に合わせる（ollama の行は無し）。key の値を例に書かない

- [ ] **Step 3: 検証**

  Run: `rg -n 'tools\.agent_runner run|tools\.agent_runner \\$|implement_task\.py" run|review_design\.py" review|run_roles\.py" \\|scripts/dispatch\.py" \\' .agents .devcontainer/README.md AGENTS.md tools/agent_runner/interfaces.rst`
  Expected: どの行も、同じコマンドの中に `with_keys.py` がある（`accept` など runner を起動しないものは対象外）
  Run: `uv run --locked pytest .agents/skills/pr-review-fix-loop .agents/skills/issue-to-pr -q && bash .devcontainer/test-readme.bash && bash scripts/check-layout.sh`
  既存のテストが `next[-3:]` を照合しているので、`review` の `next` の末尾が `["review", "--run", <run_dir>]` のままであることも確かめる
  Expected: すべて終了コード 0

- [ ] **Step 4: commit**

  ```bash
  git add .agents/skills/issue-to-pr/SKILL.md .agents/skills/pr-review-fix-loop/scripts/loop.py .agents/skills/review-fix-planning/references/execution.md .agents/skills/review-verify/references/fix-check.md .agents/monitoring-runtimes.md .devcontainer/README.md
  git commit -m "docs: route agent-runner launches through with_keys (#401)"
  ```

### Task 4: 統合の確認（controller）

**テスト:** 追加しない。

- [ ] **Step 1:** `bash .devcontainer/run-tests.bash`、`uv run --locked pytest tools/agent_runner .agents/skills -q`、`bash scripts/check-layout.sh`、`uv run --locked python -m tools.agent_runner check`・`list`（雛形だけと、実際の個人設定の解決の両方）が終了コード 0
- [ ] **Step 2:** 一時 HOME と偽の値の env ファイルで、`env -u DEEPINFRA_TOKEN HOME=<tmp> AGENT_RUNNER_CONFIG=<tmp>/none.toml uv run --locked python tools/agent_runner/with_keys.py -- printenv DEEPINFRA_TOKEN` を手で実行し、stderr が補った名前の 1 行だけで値を含まないことを確かめる（値は標準出力で偽の値と照合し、記録しない）。`with_keys.py` を引数なしで実行して終了コード 2
- [ ] **Step 3:** README・手順の agent 名・exec 名・env の名前・起動の形が Task 1・2 の実装と一致する（`git diff` の照合）
- [ ] **Step 4:** 実機の観測はマージの後（Spec の「マージの後に確かめる項目」）。PR 本文と Issue のコメントに未実施として書く

## 実行予算

- 全体の能動時間: 360 分（PR 修正ループを含む。#397 の実績 300 分に、Task が 1 つ多いことと設計レビューの分を足した。ループは上限 3 サイクル ×（レビューの期限 45 分＋計画・修正 20 分））
- phase の目安: 準備・Spec・設計レビュー・Spec レビュー・Plan 60 分、Task 1 40 分、Task 2 35 分、Task 3 40 分、統合・PR 20 分、ループ 195 分
- worker: `implement` の役割の期限は 90 分（runner の既定）。無進捗の打ち切りは runner の既定に従う
- 再試行: 同じ失敗の再試行は 1 回まで（`retry`・`rejected` を含む依頼し直しは Task ごとに 1 回）。並行するセッションとの `outside_changes` は、他の runner が無いことを確かめてから 1 回だけ依頼し直す
- checkpoint: 各 Task の後、予算の 50%（180 分）・100%、担当の失敗の直後
- 縮小・切り出し・方法変更の候補: README の小節を要点（読み元・条件・表・起動の例）に絞る。プロバイダの表を省き、本文で列挙する。担当が上限まで失敗したら停止して利用者に担当の変更を求める（self で代行しない）

## contingency（代替策）

- Task 1 の最初の RED が想定と違う理由で止まる（`load_config` の引数・雛形の `env` の名前が違う）: 実際の API を確かめ、テストの意味（補う・上書きしない・届かない・実行しない・漏らさない）を保つ最小の修正を ledger に記録して続ける。意味が変わるなら停止する
- `ruff` の設定が Python 3.14 の `except A, B:` を受け付けない: 括弧の形 `except (A, B):` にする
- `loop.py` の `ROOT` が `PARENT_ROOT` と違う: `ROOT` の定義に合わせ、wrapper のパスを `loop.py` と同じ checkout の `tools/agent_runner/with_keys.py` にする（意味は同じ）
- 担当が `failed`・上限の `retry` / `rejected`: その Task で停止して報告する（self で引き取らない）
- `main` が進んだ（`recheck_bases` が移動を観測した。利用者の指示「途中でメインがマージされたら、追随して作業を止めずに続行してください」）: push の前なら `git -C "$CODE_ROOT" rebase <新しい SHA>`、push の後なら `git -C "$CODE_ROOT" merge --no-edit <新しい SHA>`（force push しない）。`code-base.json` の `sha` と `vars.sh` の `CODE_BASE_SHA` を新しい SHA にし、Task 4 の検証をやり直してから続ける。競合を解消できない・検証が失敗するなら止まる。runner の担当に依頼している最中は、その依頼の完了を待ってから追随する（依頼の `revision` と取り込みの `--ff-only` を崩さない）
- 実装担当の `pi_xai_grok4_xhigh` が JSON 以外を返して `response_failed` になる: 再試行の上限（1 回）の中で、依頼の `prompt` に応答の形式を明記して依頼し直す。また失敗したら止まる（担当を変えるかは利用者が決める）
