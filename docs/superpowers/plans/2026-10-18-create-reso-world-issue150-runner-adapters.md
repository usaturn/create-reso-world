# Issue #150 runtime adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 非対話の5 runtime adapterを既存runnerへ追加し、payloadと観測identityを取得する。

**Architecture:** 移植元a47b2065のadapterを現行protocolへ適応する。runtimeごとにadapter・偽CLIテスト・runtime文書・対応agent定義をまとめ、同じ雛形への書き込みは直列にする。共有protocol/coreを変えない。

**Tech Stack:** Python >=3.14、既存pydantic、pytest、TOML、RST、各CLIの非対話イベント。

**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue150-runner-adapters-design.md`

**管理:** draft。利用者のissue-to-pr #150と今回のOKによる実行許可であり、内容承認は記録しない。反映先feat/issue-150-runner-adapters、main向けPR1本、マージ禁止。

**現在の実行許可（2026-10-18）:** 利用者の「OpenCode Go の認証確認は保留にして実装して。保留分は別の Issue にして。」により、`pigod`・`pi-go-glmf` の認証・実機確認を #172 に移管する。agent定義と実装は維持し、#150は残る9 agentの実機確認後にPRを公開する。過去の停止記録は履歴として残す。OpenCode Goの追加実行・認証設定変更は行わない。

## Global Constraints

- runner本体、`adapters/__init__.py`・`adapters/skills.py`・`models.py`、DSH、ランチャー、zshrc、雛形のroles.*・workflows.*・agents.dsh-*を変更しない。
- 追加するコードは5 adapterと各 `tests/adapters/<runtime>/`、文書は `tools/agent_runner/runtimes/`、設定は非DSH agents.*だけに置く。Spec/Planは `docs/superpowers/` に置く。
- `tools/workspace`・`projects.toml`・Grok Build・新しい依存・CIを導入しない。親 #116 のD-1〜D-24とreview-fix-planningの判断基準を維持する。
- `AdapterContext` → `LaunchSpec` → `AdapterOutcome` とモジュールの `ADAPTER` を使う。promptはstdinかattempt内のファイルで渡し、argvへ本文を入れない。collectはローカル解析のみでプロセスを起動しない。
- identityは観測値だけを返し、要求model/provider/effortをコピーしない。未観測はnull/空map。skill_versionsは成功した読み取りで内容を確認できた場合だけ記録する。
- 認証・承認待ち、不完全な応答、CLIの失敗を成功にしない。モデルや対話方式への暗黙fallbackは追加しない。
- Pythonはuvで実行する。通常テストは偽CLIだけを使い、実機確認はcontrollerが各agentにつき1回行う。認証値を取得・表示・更新しない。
- 親checkoutと他者のbranch/worktreeを変更しない。未コミットの記録はPARENT_ROOTの `tmp/agents/issue-150.x_25tm6g/` に保存する。


## 入力と実行方法

- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-150-runner-adapters`。PARENT_ROOT: `/workspaces/reso-world`。
- 移植元snapshot: `/workspaces/reso-world/tmp/agents/issue-150.x_25tm6g/upstream/`（usaturn/agent-workspace a47b2065fddad76b7475752fd0088af0733de204）。recon-report.mdを具体的な互換性の根拠に使う。
- 共通仕様: `tools/agent_runner/interfaces.rst`。各moduleは `ADAPTER`、`capabilities = Capabilities()`、`prepare(context: AdapterContext) -> LaunchSpec`、`collect(context: AdapterContext, stdout_path: Path, stderr_path: Path) -> AdapterOutcome` を公開する。
- 既存基準検証は同じa024a22で1891 passed。runtime個別テストを各実装者が同期実行し、全体回帰はcontrollerが最終コードで1回実行する。
- SDDの一時成果はworktreeの外の既存scratchに置く。helperの明示OUTFILEを使い、sdd-workspaceも一時GIT_WORK_TREEをscratchへ向けて解決する。永続envを変更しない。
- 実装者はTDD・verification-before-completion、RST編集はrst-writerを読む。サブエージェントを起動しない。認証・実機・push・Issue操作はcontrollerのみ。

## Review Focus

- 正常回答中のauth/approvalという語を誤って失敗扱いしない。各Taskの診断/失敗イベントと正常payloadを分けたテストで守る。
- CLIが0終了してもイベント/最終応答が欠けていれば失敗。各Taskに不完全出力のテストを置く。
- 未観測identityを設定で補わない。各Taskにnullのままになるケースを置き、Task 3はchild環境の異なるHOME/CODEX_HOMEも検証する。
- スキルの単なる指定/言及・失敗/部分readを版の証拠にしない。各Taskに偽イベントの肯定/否定テストを置く。完全なreadを証明できないCLIでは空mapを維持する。
- JSON/text、prompt-file/stdin、非ゼロ終了とtimeout/cancelを現実の偽CLIプロセスで検証する。各runtimeの統合テストを使い、共通runner機能の細部は重複して再実装しない。

## 実行予算

Issue全体は能動180分（handoffまで約14.5分、利用者待ちを除く）。既存budget.jsonlへ追記する。目安: 再確認/設計15分、5 Taskと個別レビュー90分、全体検証/最終レビュー30分、実機/公開30分。Taskの実装目標は各開始から20分、最後3分を保存に予約。レビュー目標は開始から10分、最後2分を保存に予約。controllerが10分ごとに実質進捗とレポート/agent状態を確認し、2回続けて変化が無ければstallを報告する。共有worktreeの実装者・検証は強制停止しない。ネイティブagentはPIDを取得できないのでtask_watchの自動打ち切りは適用しない。

同一信頼性失敗の再試行は1回まで、以後は方法変更。旧sp-reconの期限切れAPIは再試行せず、利用者が許可したCodex標準agentへ変更済み。安全の失敗は全体停止。phase境界・50%・100%・worker失敗直後にcheckpoint。100%に達したら延長せず残りを報告する。縮小候補は正確なidentity未観測をnullに保つことと固定文言テストの除外（受け入れ条件は減らさない）。切り出しが必要なら持ち越し候補を記録し、新Issueは作らない。実機認証の失敗は成功にせず停止して必要な利用者操作を報告する。

---

### Task 1: Pi adapter・偽CLI・runtime文書・agent定義

**Files:** create `tools/agent_runner/adapters/pi.py`、`tools/agent_runner/tests/adapters/pi/`（移植元のfakeとunit/integration testsを置く）、`tools/agent_runner/runtimes/pi.rst`。modify `.devcontainer/agent-runner.toml` の次のagents.*だけ。

**Interfaces:** 既存AdapterContext/LaunchSpec/AdapterOutcome/CapabilitiesとReceipt/Identityを消費し、上記のADAPTERを提供する。他Taskとの依存はTOMLの別agent節だけで、新APIを追加しない。

**Implementation:** `--print --mode json --no-session --no-approve` とprovider/model/thinkingを指定しstdinを使う。session、agent_endの最後のassistant、stopReason、agent_settledから解析する。現行Piの失敗は終了コード0のことがある。role.skillsとconfigured sourcesをpromptへ反映する。skill_versionsは完了した実readと内容一致の証拠に限り、既存のパスの列挙/現在のファイルのhashだけの実装をそのまま移植しない。

**Agent TOML:** 以下を使う。provider/effort/モデルの運用値をテストに固定して写さない。

```toml
[agents.pi-deepseek]
runtime = "pi"
command = ["piccd"]
model = "deepseek/deepseek-v4.1-flash"
provider = "commandcode"
effort = "max"
env = ["HOME", "PATH", "COMMANDCODE_API_KEY"]

[agents.pi-gpt]
runtime = "pi"
command = ["pigs"]
model = "gpt-6.1-sol"
provider = "openai-codex"
effort = "xhigh"
env = ["HOME", "PATH", "OPENCODE_API_KEY"]

[agents.pixg]
runtime = "pi"
command = ["pixg"]
model = "grok-4.7"
provider = "xai"
effort = "xhigh"
env = ["HOME", "PATH"]

[agents.pigod]
runtime = "pi"
command = ["pigod"]
model = "deepseek-v4.1-flash"
provider = "opencode-go"
effort = "max"
env = ["HOME", "PATH", "OPENCODE_API_KEY"]

[agents.pi-go-glmf]
runtime = "pi"
command = ["pi"]
model = "glm-5.3-flash"
provider = "opencode-go"
effort = "max"
env = ["HOME", "PATH", "OPENCODE_API_KEY"]

[agents.pi-gemf]
runtime = "pi"
command = ["pigemf"]
model = "gemini-3.8-flash"
provider = "google-vertex"
effort = "high"
env = ["HOME", "PATH", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]
```

`pi-go-glmf` は導入済みのraw `pi` を使い、上記のprovider/model/effortを明示して追加する。最終レビュー I-3 とSpec D-150-5のcontroller裁定により、当初の省略指示を撤回した。元のIssueの指定範囲に戻す実行許可内の修正であり、内容承認は記録しない。pigo/piglのモデルを変更/再解釈しない。configのparse/checkとcontrollerによる各agent1回の実機確認に含める。

**テストの要否:** 必要。実行するargv/入力/CLI出力解析/失敗分類という挙動を守る。文書・TOMLの固定文言テストは不要で、parse/checkとdiff/参照構造の確認を使う。

- [x] Step 1: snapshotから対応の偽CLIと挙動テストを適応する。`test_prepare`でpromptがargvになくstdinまたはfileで届くこと、model/effort/非対話指定を確認する。JSON/text成功、auth/approval失敗、不完全/不正応答、非ゼロ終了、未観測identity、skill指定と観測の区別を検証する。固定文言/文書/モデル名一覧だけのテストは持ち込まない。
- [x] Step 2: `uv run pytest tools/agent_runner/tests/adapters/pi -q` を同期実行し、まだmoduleが無いことによるREDを記録する。
- [x] Step 3: adapterを移植・適応して上の挙動を満たす。schema/pydantic/共通skillsが既に検証するだけの重複テストは追加しない。必要な追加の回帰もRED→GREENで行う。
- [x] Step 4: 同じruntime全体のテストを同期実行してGREEN、必要ならそのruntimeのfake process統合テストのtimeout/cancel/停止確認も含める。実CLIを起動しない。全root回帰はcontrollerの最終検証でまとめる。
- [x] Step 5: 対応agent節とruntime RSTを追加する。移植元の実機記録をこの環境の成功として転記せず、出所または未検証と記す。`uv run python -m tools.agent_runner --config .devcontainer/agent-runner.toml check` と `git diff --check` で検証する。
- [x] Step 6: 自己確認後、列挙した担当pathだけをstage/commitする。報告にRED/GREENのコマンド・出力・件数・終了コード、変更files、懸念、所要時間と内訳を残す。controllerの別担当レビューを待つ。

### Task 2: Claude Code adapter・偽CLI・runtime文書・agent定義

**Files:** create `tools/agent_runner/adapters/claude_code.py`、`tools/agent_runner/tests/adapters/claude_code/`（移植元のfakeとunit/integration testsを置く）、`tools/agent_runner/runtimes/claude-code.rst`。modify `.devcontainer/agent-runner.toml` の次のagents.*だけ。

**Interfaces:** 既存AdapterContext/LaunchSpec/AdapterOutcome/CapabilitiesとReceipt/Identityを消費し、上記のADAPTERを提供する。他Taskとの依存はTOMLの別agent節だけで、新APIを追加しない。

**Implementation:** `claude -p --output-format stream-json --verbose --model`、effortがあればCLIへ渡し非対話permissionを使う。stdinへJSON形状とrole.skills/configured sourceを含むpromptを送る。system/init、assistantモデル、resultを解析しpermission_denials/is_error/interruption/認証を区別する。Skill呼出しを見ただけでファイルをhashしない。

**Agent TOML:** 以下を使う。provider/effort/モデルの運用値をテストに固定して写さない。

```toml
[agents.claude-opus]
runtime = "claude-code"
command = ["claude"]
model = "opus"
env = ["HOME", "PATH"]
```

**テストの要否:** 必要。実行するargv/入力/CLI出力解析/失敗分類という挙動を守る。文書・TOMLの固定文言テストは不要で、parse/checkとdiff/参照構造の確認を使う。

- [x] Step 1: snapshotから対応の偽CLIと挙動テストを適応する。`test_prepare`でpromptがargvになくstdinまたはfileで届くこと、model/effort/非対話指定を確認する。JSON/text成功、auth/approval失敗、不完全/不正応答、非ゼロ終了、未観測identity、skill指定と観測の区別を検証する。固定文言/文書/モデル名一覧だけのテストは持ち込まない。
- [x] Step 2: `uv run pytest tools/agent_runner/tests/adapters/claude_code -q` を同期実行し、まだmoduleが無いことによるREDを記録する。
- [x] Step 3: adapterを移植・適応して上の挙動を満たす。schema/pydantic/共通skillsが既に検証するだけの重複テストは追加しない。必要な追加の回帰もRED→GREENで行う。
- [x] Step 4: 同じruntime全体のテストを同期実行してGREEN、必要ならそのruntimeのfake process統合テストのtimeout/cancel/停止確認も含める。実CLIを起動しない。全root回帰はcontrollerの最終検証でまとめる。
- [x] Step 5: 対応agent節とruntime RSTを追加する。移植元の実機記録をこの環境の成功として転記せず、出所または未検証と記す。`uv run python -m tools.agent_runner --config .devcontainer/agent-runner.toml check` と `git diff --check` で検証する。
- [x] Step 6: 自己確認後、列挙した担当pathだけをstage/commitする。報告にRED/GREENのコマンド・出力・件数・終了コード、変更files、懸念、所要時間と内訳を残す。controllerの別担当レビューを待つ。

### Task 3: Codex adapter・偽CLI・runtime文書・agent定義

**Files:** create `tools/agent_runner/adapters/codex.py`、`tools/agent_runner/tests/adapters/codex/`（移植元のfakeとunit/integration testsを置く）、`tools/agent_runner/runtimes/codex.rst`。modify `.devcontainer/agent-runner.toml` の次のagents.*だけ。

**Interfaces:** 既存AdapterContext/LaunchSpec/AdapterOutcome/CapabilitiesとReceipt/Identityを消費し、上記のADAPTERを提供する。他Taskとの依存はTOMLの別agent節だけで、新APIを追加しない。

**Implementation:** commandは`codex exec`。`--json -s read-only|workspace-write -m MODEL`、effortは`-c model_reasoning_effort=EFFORT`、最後に`-`を置きstdinを使う。thread.startedとagent_message、同じsessionのrolloutを解析する。rollout探索はcontext.environmentがあれば実際のchild環境を使い、無ければ直接呼出し互換としてos.environを使う。thread IDのパス/ワイルドカードを検証し他sessionを読まない。認証・承認失敗を診断から分類し、error/turn.failedは先行messageより優先する。shared prompt_lines/verified_versionsを再利用する。

**Agent TOML:** 以下を使う。provider/effort/モデルの運用値をテストに固定して写さない。

```toml
[agents.codex]
runtime = "codex"
command = ["codex", "exec"]
model = "gpt-6.1-sol"
provider = "openai"
approval = "noninteractive"
skill_sources = [".agents/skills", ".codex/skills"]
env = ["HOME", "PATH"]
```

**テストの要否:** 必要。実行するargv/入力/CLI出力解析/失敗分類という挙動を守る。文書・TOMLの固定文言テストは不要で、parse/checkとdiff/参照構造の確認を使う。

- [x] Step 1: snapshotから対応の偽CLIと挙動テストを適応する。`test_prepare`でpromptがargvになくstdinまたはfileで届くこと、model/effort/非対話指定を確認する。JSON/text成功、auth/approval失敗、不完全/不正応答、非ゼロ終了、未観測identity、skill指定と観測の区別を検証する。固定文言/文書/モデル名一覧だけのテストは持ち込まない。
- [x] Step 2: `uv run pytest tools/agent_runner/tests/adapters/codex -q` を同期実行し、まだmoduleが無いことによるREDを記録する。
- [x] Step 3: adapterを移植・適応して上の挙動を満たす。schema/pydantic/共通skillsが既に検証するだけの重複テストは追加しない。必要な追加の回帰もRED→GREENで行う。
- [x] Step 4: 同じruntime全体のテストを同期実行してGREEN、必要ならそのruntimeのfake process統合テストのtimeout/cancel/停止確認も含める。実CLIを起動しない。全root回帰はcontrollerの最終検証でまとめる。
- [x] Step 5: 対応agent節とruntime RSTを追加する。移植元の実機記録をこの環境の成功として転記せず、出所または未検証と記す。`uv run python -m tools.agent_runner --config .devcontainer/agent-runner.toml check` と `git diff --check` で検証する。
- [x] Step 6: 自己確認後、列挙した担当pathだけをstage/commitする。報告にRED/GREENのコマンド・出力・件数・終了コード、変更files、懸念、所要時間と内訳を残す。controllerの別担当レビューを待つ。

### Task 4: Cursor adapter・偽CLI・runtime文書・agent定義

**Files:** create `tools/agent_runner/adapters/cursor.py`、`tools/agent_runner/tests/adapters/cursor/`（移植元のfakeとunit/integration testsを置く）、`tools/agent_runner/runtimes/cursor.rst`。modify `.devcontainer/agent-runner.toml` の次のagents.*だけ。

**Interfaces:** 既存AdapterContext/LaunchSpec/AdapterOutcome/CapabilitiesとReceipt/Identityを消費し、上記のADAPTERを提供する。他Taskとの依存はTOMLの別agent節だけで、新APIを追加しない。

**Implementation:** `agent -p --output-format stream-json --trust`、writes=Falseは`--mode ask`、Trueは`-f`、modelを指定しstdinを使う。effortがあるときはCLI対応のmodel override構文を用いる。system/initのモデルとresultを解析する。エラー/認証/承認を成功回答中の説明文と区別する。shared prompt_linesと、完了した全体readToolCallの内容一致によるverified_versionsを維持する。

**Agent TOML:** 以下を使う。provider/effort/モデルの運用値をテストに固定して写さない。

```toml
[agents.cursor]
runtime = "cursor"
command = ["agent"]
model = "auto"
approval = "noninteractive"
skill_sources = [".cursor/skills", ".claude/skills", ".agents/skills", ".codex/skills"]
env = ["HOME", "PATH"]

[agents.cursor-grok47]
runtime = "cursor"
command = ["agent"]
model = "grok-4.7-xhigh"
approval = "noninteractive"
skill_sources = [".cursor/skills", ".claude/skills", ".agents/skills", ".codex/skills"]
env = ["HOME", "PATH"]
```

**テストの要否:** 必要。実行するargv/入力/CLI出力解析/失敗分類という挙動を守る。文書・TOMLの固定文言テストは不要で、parse/checkとdiff/参照構造の確認を使う。

- [x] Step 1: snapshotから対応の偽CLIと挙動テストを適応する。`test_prepare`でpromptがargvになくstdinまたはfileで届くこと、model/effort/非対話指定を確認する。JSON/text成功、auth/approval失敗、不完全/不正応答、非ゼロ終了、未観測identity、skill指定と観測の区別を検証する。固定文言/文書/モデル名一覧だけのテストは持ち込まない。
- [x] Step 2: `uv run pytest tools/agent_runner/tests/adapters/cursor -q` を同期実行し、まだmoduleが無いことによるREDを記録する。
- [x] Step 3: adapterを移植・適応して上の挙動を満たす。schema/pydantic/共通skillsが既に検証するだけの重複テストは追加しない。必要な追加の回帰もRED→GREENで行う。
- [x] Step 4: 同じruntime全体のテストを同期実行してGREEN、必要ならそのruntimeのfake process統合テストのtimeout/cancel/停止確認も含める。実CLIを起動しない。全root回帰はcontrollerの最終検証でまとめる。
- [x] Step 5: 対応agent節とruntime RSTを追加する。移植元の実機記録をこの環境の成功として転記せず、出所または未検証と記す。`uv run python -m tools.agent_runner --config .devcontainer/agent-runner.toml check` と `git diff --check` で検証する。
- [x] Step 6: 自己確認後、列挙した担当pathだけをstage/commitする。報告にRED/GREENのコマンド・出力・件数・終了コード、変更files、懸念、所要時間と内訳を残す。controllerの別担当レビューを待つ。

### Task 5: Devin adapter・偽CLI・runtime文書・agent定義

**Files:** create `tools/agent_runner/adapters/devin.py`、`tools/agent_runner/tests/adapters/devin/`（移植元のfakeとunit/integration testsを置く）、`tools/agent_runner/runtimes/devin.rst`。modify `.devcontainer/agent-runner.toml` の次のagents.*だけ。

**Interfaces:** 既存AdapterContext/LaunchSpec/AdapterOutcome/CapabilitiesとReceipt/Identityを消費し、上記のADAPTERを提供する。他Taskとの依存はTOMLの別agent節だけで、新APIを追加しない。

**Implementation:** `devin -p --prompt-file FILE --export FILE --model MODEL --permission-mode dangerous --respect-workspace-trust false`。prompt.txtをattempt内に作り本文をargvへ入れない。JSON形状とrole.skills/configured sourceをファイルへ反映する。stdoutとATIF exportの最終agent応答・agent.model_name/session_id/versionを解析する。exportが無い/壊れた/最終応答が無い場合は失敗、認証/承認診断は成功payloadへ隠さない。skillのパスがtool引数に出ただけではhashしない。

**Agent TOML:** 以下を使う。provider/effort/モデルの運用値をテストに固定して写さない。

```toml
[agents.devin-swe]
runtime = "devin"
command = ["devin"]
model = "swe-2-max"
env = ["HOME", "PATH"]
```

**テストの要否:** 必要。実行するargv/入力/CLI出力解析/失敗分類という挙動を守る。文書・TOMLの固定文言テストは不要で、parse/checkとdiff/参照構造の確認を使う。

- [x] Step 1: snapshotから対応の偽CLIと挙動テストを適応する。`test_prepare`でpromptがargvになくstdinまたはfileで届くこと、model/effort/非対話指定を確認する。JSON/text成功、auth/approval失敗、不完全/不正応答、非ゼロ終了、未観測identity、skill指定と観測の区別を検証する。固定文言/文書/モデル名一覧だけのテストは持ち込まない。
- [x] Step 2: `uv run pytest tools/agent_runner/tests/adapters/devin -q` を同期実行し、まだmoduleが無いことによるREDを記録する。
- [x] Step 3: adapterを移植・適応して上の挙動を満たす。schema/pydantic/共通skillsが既に検証するだけの重複テストは追加しない。必要な追加の回帰もRED→GREENで行う。
- [x] Step 4: 同じruntime全体のテストを同期実行してGREEN、必要ならそのruntimeのfake process統合テストのtimeout/cancel/停止確認も含める。実CLIを起動しない。全root回帰はcontrollerの最終検証でまとめる。
- [x] Step 5: 対応agent節とruntime RSTを追加する。移植元の実機記録をこの環境の成功として転記せず、出所または未検証と記す。`uv run python -m tools.agent_runner --config .devcontainer/agent-runner.toml check` と `git diff --check` で検証する。
- [x] Step 6: 自己確認後、列挙した担当pathだけをstage/commitする。報告にRED/GREENのコマンド・出力・件数・終了コード、変更files、懸念、所要時間と内訳を残す。controllerの別担当レビューを待つ。

## 最終検証・反映（controller）

- [x] 各Taskの仕様/品質レビューと全fixのscoped re-reviewを終える。deferred minorやRulingはledgerへ残し、最終レビュアーへ渡す。
- [x] `uv run pytest tools/agent_runner/tests/adapters`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`git diff --check` を最終コードで実行する。検証プロセスの終了コードとログを確認し、実行中にターンを終えない。
- [x] ブランチ全体を最上位モデルの別担当がレビューする。所定の1回のfix waveとscoped re-reviewを使い、未解決は根拠付きで判定する。
- [ ] OpenCode Go以外の9 agentの証跡を確認する。成功済み8件を再実行せず、`pi-gemf` だけを短いJSON marker、writes=False、deadline120秒、fallbackなしの最小一時configでrunnerから1回起動する。使い捨てgit repo/runner worktreeのstate/identity/payload/elapsed/stop_confirmed/outside_changesを #150 に記録する。`pigod`・`pi-go-glmf` は利用者の明示指示で #172 へ移管済みと記録し、成功とは書かない。agent定義・認証やproviderを変更しない。
- [ ] 問題が無ければSpec/Planに完了記録（承認とは別）を追記してcommit。最新Issue/PR/claimを再確認し親checkoutのscan-before-push.shで検査した非空SHAをそのままpushする。main向け `Closes #150` のPRを1本作成する。親Issue本文/他者の予約を触らずマージしない。
- [ ] 文書とhandoffを公開した内容から別領域へ復元してhash/bytesを照合し、予約をexact-SHA leaseで解放して不在を確認する。budgetと各担当時間、検証/実機の制限、残存pathを報告する。

## Plan自己確認

受け入れ1/2は各Task、3はcontroller実機と利用者が明示した#172への移管、4は最終検証に対応する。全Taskは同じprotocolに一致し、TOMLは異なる節を直列追加する。Review Focusの5種類は各Taskのテストへ割り当てた。固定文言テスト・新規依存・共有ファイル変更を要求していない。

### 利用者指示による保留分の切り出しと最終化

- 作業範囲: 既存Spec/Planの受け入れ条件と公開記録だけを更新する。5 Taskと全レビューは完了済みで再実行しない。`pigod`・`pi-go-glmf` の定義・adapter・テスト・ランチャーは変更しない。
- #172はOpenCode Goの復旧確認後に両agentを各1回実行し、正確なmarker・観測model・終了コード・停止・outside_changesを記録するIssueとした。#150のPR作成・マージの先行条件にせず、親#116のボードと依存関係は変更しない。
- 今回はGoogle Vertexの `pi-gemf` 1回だけを新しい使い捨てrepo・一時configで確認し、従来8件と合わせて9 agentの証跡を揃える。OpenCode Goの実APIは起動しない。
- テストの要否: 新規テスト不要。コード・設定・実行ロジックを変更しないため。代わりに実機1件の結果、config check、git diff --check、検証済みコード9a03f74からの差分がSpec/Planだけであること、Issue/PRの参照と公開後の文書復元を確認する。既存の2181 pytest・33 shell・depth adapter291件の終了コード0と全体レビューの証跡は保持し、再実行したとは書かない。
- 実行予算は既存ledgerを継続する。準備とIssue切り出し5分、残る実機最大2分、文書/公開/復元10分を目安とする。失敗時・phase境界でcheckpointを記録する。OpenCode Go以外で新たな失敗が起きた場合は、今回の保留指示を広げず停止する。

## 部分成果・実機検証・停止（2026-10-18 UTC）

- 状態はdraft、内容承認なし。実装コード `9a03f744e8544374fa52a400b4d5f3b240062f76` までの全5 Taskと全体レビュー後の修正を完了した。ローカルcommitのみで、コードのpush・PRは公開未実施。
- 最終レビューはCritical0/Important3/Minor1。Piの破損末尾、Cursorの後続未完了応答、pi-go-glmfの省略、Codexの不正typeを1回の修正waveで直し、scoped再レビューは4件すべてADDRESSED、新たな問題なし。Claude/Devinの先行修正も維持した。
- 最終コードで `uv run pytest tests/skills .agents/skills .agents/scripts tools` は2181 passed、exit0、431.53秒（wrapper432.385秒）。通常adapterを含む。`AGENT_RUNNER_DEPTH=1 uv run pytest tools/agent_runner/tests/adapters` は291 passed、exit0。shellは33PASS、exit0、327.932秒。layout、config（5 runtime/11 agent supported）、全branch diff checkもexit0。全検証プロセスの終了を確認済み。
- 実機では使い捨てgit repoと一時config、writes=False、各deadline120秒、fallbackなし。表の時間はrunner呼び出し全体の秒数。全9呼び出しでstop_confirmed=true、outside_changesは空。成功8件は正確なmarkerを返した。CursorのAutoはCLIが返した観測値で、内部の選択モデルまでは確定しない。

| agent | 観測model | attempt state | payload | 秒 | stop_confirmed |
| --- | --- | --- | --- | ---: | --- |
| codex | gpt-6.1-sol | success | `{"marker":"5cd780a703f2c374"}` | 7.215 | True |
| claude-opus | claude-opus-5-5 | success | `{"marker":"35578348db179f71"}` | 7.310 | True |
| devin-swe | SWE-2 Max | success | `{"marker":"98c588bb121e0036"}` | 4.755 | True |
| cursor | Auto | success | `{"marker":"e72f3e0fa8320eec"}` | 14.470 | True |
| cursor-grok47 | Grok 4.7 256K Extra High | success | `{"marker":"762355fe67bc4dc6"}` | 16.105 | True |
| pi-gpt | gpt-6.1-sol | success | `{"marker":"417794b0a8fa15ce"}` | 7.918 | True |
| pixg | grok-4.7 | success | `{"marker":"cb93583fd2d0655d"}` | 2.954 | True |
| pi-deepseek | deepseek/deepseek-v4.1-flash | success | `{"marker":"af6fa915faa73afd"}` | 3.209 | True |
| pigod | deepseek-v4.1-flash | awaiting_authentication | `null` | 1.628 | True |

9番目のpigodがopencode-goの認証待ちとなった。診断のAPI key期限切れを確認したが、秘密値は読まず、公開ログにも載せない。CLI自体のexitは0でも、adapter/runnerは正しく失敗と分類しrunnerはexit1。スモーク全体は65.658秒でexit1。停止条件に従い後続のpi-gemf/pi-go-glmfは未実行、認証設定・provider・modelの変更や再試行も行っていない。実機の全件成功を条件から外さない。

次の操作は利用者によるOpenCode Go認証の復旧とその確認。その後、再開セッションが新しいclaimを取得し、成功8件を繰り返さず、失敗したpigodと未実行2件の実機検証を別の明示的な再開runで行う。既存smokeディレクトリは再利用・上書きしない。残る受け入れを通してからscan・同じbranchのpush・mainへのPRを1本作成する。今回はコードのscan/push/PRは未実施。

能動時間は停止判断時点で約96.5分/180分（利用者待ちは除外、並行workerの時間を足さない）。主要Taskの担当時間: Pi約4分45秒、Claude約4分18秒＋修正約2分、Codex7分37秒、Cursor4分59秒、Devin約6〜7分＋修正約2分。全体レビュー約4分37秒、最終修正5分15秒、scoped再レビュー1分08秒。回帰は修正前8分44秒と修正後7分12秒（shellは並行）、実機約1分06秒。その他はhandoff検証・設計/計画・各Taskレビュー・記録/公開準備。準備の一部と各担当のphase内訳は親scratchの報告を参照し、計測していない時間を推測で加算しない。

残存記録は `/workspaces/reso-world/tmp/agents/issue-150.x_25tm6g/`、SDD ledger/reportsはその下の `.superpowers/sdd/2026-10-18-create-reso-world-issue150-runner-adapters/`、最終検証は `checks/`、実機は `live-smoke/summary.json`。コードの受け入れが未完了なので削除しない。Spec/Planと新しいhandoff対はIssueコメントで完全な内容とhash/bytesを公開し、別領域への復元検証後に自分のclaimだけをexact-SHA leaseで解放する。元のIssueはopenのまま、親Issue・他者の予約・worktreeには触れない。

## 認証復旧確認後の再開と再停止（2026-10-18 17:55 UTC）

- 利用者の「認証は復旧済みです」を実機再開の条件充足として記録した。内容承認は記録せず、Spec/Planの状態はdraftのまま。新しい担当予約 `56056413395c4bd37999619bb066213dc145a0c0` を取得し、#149 completed・PR #163 mainマージ済み、Issue #150 open、競合PRと他者の予約なしを再確認した。
- 既存HEAD `9395032` と検証済みコード `9a03f74` の差分はSpec/Planの記録だけ。全5 Task・個別レビュー・全体レビューと1回の修正・scoped再レビューは完了済みとして再実行しなかった。2181 pytest / 33 shell / depth adapter291件の既存の終了コード0とログを照合し、config check（5 runtime/11 agent supported）・branch全体のdiff checkを再実行して終了コード0を確認した。コード変更が無いため全回帰は繰り返していない。
- 新しい `resume-20261018T175317Z/live-smoke-remaining/` に使い捨てgit repo・一時configを作り、対象を `pigod`・`pi-gemf`・`pi-go-glmf` だけに限定した。writes=False、deadline120秒、fallbackなし。元のsmokeと成功8件は変更していない。
- `pigod` 1回の結果: runner exit1 / CLI exit0、`awaiting_authentication`、payload null、観測provider `opencode-go` / model `deepseek-v4.1-flash` / effort `max`、runner呼出し1.671秒（wrapper1.767秒、attempt1.299秒）。`stop_confirmed=true`、outside_changes=[]。実行プロセスの終了をharnessの終了コードとPIDの不在でも確認した。
- CLIの診断は `401 / authentication_error / api_key_expired`。この実行で使われたキーが期限切れと判定されたこと以外は推測しない。認証ファイル・秘密値は取得・表示・変更せず、どの設定元のキーだったかは未確認。利用者による更新の反映状況を確認する必要がある。再ログインだけではキーの期限が更新されないという診断だった。
- 停止条件に従い後続2件は未実行。`live-authentication:pigod` は記録上2回となり既定の再試行上限に達した。同条件の追加実行、認証やprovider/modelの変更、コードpush・PR作成は行わない。具体的な更新反映の確認または条件変更が必要であり、一般的な継続指示だけで同じrunを繰り返さない。
- 詳細は親scratchの `resume-20261018T175317Z/diagnosis.json`・`live-smoke-remaining/summary.json`、`checks/live-smoke-remaining-9395032.json`、既存SDD ledger。停止記録と更新したhandoff対を公開・復元検証してから、この再開runのclaimだけをexact-SHA leaseで解放する。実装・受け入れは未完了のまま保持し、SDD workspaceとscratchは削除しない。
