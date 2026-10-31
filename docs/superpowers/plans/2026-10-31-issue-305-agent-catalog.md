# Issue #305 Agent Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 既存設定を維持して agent 命名を統一し、新5 agent と安全な起動経路・同一モデル検出を追加する。

**Architecture:** runner の model/key 和集合比較、ローカル共通 helper に接続するランチャー、設定と文書の3単位を逐次実装する。司令塔が設定・カタログ・認証・引数の一連の流れを統合確認する。

**Tech Stack:** Python/Pydantic/uv、TOML/JSON、zsh/bash、Pi、bubblewrap。

**Spec:** `docs/superpowers/specs/2026-10-31-issue-305-agent-catalog-design.md`

**管理:** 状態 `draft`。実行許可は Spec の利用者指示、内容の承認ではない。CODE_ROOT=DOC_ROOT=`/workspaces/reso-world/.worktrees/issue-305-agent-catalog`、branch=`feat/issue-305-agent-catalog`。base は `/workspaces/reso-world/tmp/agents/issue-305.fq1ezuqt/code-base.json`。公開前の base 移動は停止。

## Global Constraints

- 既存11 agent は名前と参照以外を維持する（DeepSeek 2 agent への任意の model_key 追加を除く）。特に Sol の effort=`max`、Sol/pigod の env=`OPENCODE_API_KEY`、after_run の `uv --project .` を保持する。
- 比較集合は model があれば `{model}`、key もあれば `{model, model_key}`。キーで model の比較を置き換えず、自動正規化しない。
- 個人設定・過去の reviews/evals/provenance・完了済み Spec/Plan・ワールド・外部リポジトリを変更しない。alias、自動移行、rebuild、Actions は追加しない。
- 認証の実値を表示・保存しない。新5 agent各1回＋既存3 agent構成review1回、計8担当が実機の上限。実装担当は実モデルを起動せず fake のみ使う。
- bootstrap と zsh ヘルパ以外の Python は uv 必須。rm/rmdir の変数は `${VAR:?}` でガードしパス全体を引用する。HOME の永続 export はしない。
- テストは S の損害を防ぐ代表だけ。命名表・文言・モデル一覧等の写しや同じ守りの組合せ網羅は追加しない。

## 受け入れ基準（各 brief に同じ本文を渡す）

動作環境: Dev Container。個人設定なし／変更前の雛形を写した個人設定で `uv run --locked python -m tools.agent_runner check` と `list` が成功する。既存11 agent の起動設定を意味比較で保持する。pigt/pidid は隔離HOMEで新規・既存環境に配置でき、他 provider、バックアップ、利用者の有効な tier 編集を保持する。

実入力: `--assign inspect=pi_openai-codex_gpt6-sol_max,devin_swe2-max_default,pi_commandcode_deepseek4-flash_max`。プロンプト `確認依頼\n日本語と spaces を欠落させず扱ってください。` を使う。実機は新5 agent各1回と既存3担当review1回、計8担当のみ、認証不足等は未確認として追加試行しない。停止と想定外の書き込み・秘密出力も確認する。

防御範囲: 同じ役割の agents/fallback と exclude_same_model_as に model/key の集合比較を共通適用し、一致を起動前に duplicate_model で拒否する。同じ model はキーの有無や相違で回避できない。pigt/pidid は必要な認証・モデル・tier の不足で別モデルを選ばない。正常構成と利用者が明示編集した解決可能な tier は受け入れる。防御対象外: キー無しかつ異なる model の未知モデルを同一と推測すること。

## Review Focus

1. 同じ model に片側だけキー／異なるキー: Task 1 の既存 S テスト拡張で従来拒否を保持。
2. provider 別 model 文字列だが共通キー: Task 1 の S 代表で拒否、キー無しの正常例も通す。
3. pidid の前提不足／カスタム PI_CODING_AGENT_DIR: Task 2 の S 代表で拒否と正常起動、既存パス検査を利用。
4. pigt のカタログ欠落で既定モデルを選ぶ: Task 2 の S 代表で起動しないことを観測。
5. setup 後に利用者設定が失われる: Task 2 の既存 preservation テストを利用し、controller が新規・既存の隔離HOMEシナリオでモデル/tierの保持を実行確認。

## 実行方式と実行予算

implement_task.py check の既定は self。独立した3単位を同期の sp-implementer に逐次委譲する SDD を選ぶ（同時書き込みなし）。各 Task は sp-review が読み取り専用で仕様と品質をレビューし、司令塔が最終全体レビューと統合検証を担当する。モデルは tool のロール既定 tier を使用（明示 override はしない）。

能動時間の予算420分（3 Task・実機・正式検証と最大3サイクルのレビュー45分＋計画修正を含む）。準備45、実装75、統合/実機/正式検証50、PR20、ループ最大225、整理5分。開始前の調査約30分は ledger の開始前なので別に記録し総所要時間には含める。

ledger は `/workspaces/reso-world/tmp/agents/issue-305.fq1ezuqt/budget.jsonl`、SDD は同セッションの `sdd/2026-10-31-issue-305-agent-catalog/`。phase境界・50%/100%・worker失敗直後に checkpoint。100%か安全の失敗で停止。同じ信頼性失敗は再試行1回まで。scope/API前提の差は意味を保つ最小変更を記録して継続、意味変更は停止。

共有 feature に書く実装子と検証は途中停止しない。同期 tool の戻りで終了確認し、実装目安30分、読み取りレビュー目安10分。runner の実機inspectは45分の既存期限（新規試行の追加なし）、PR後のreview45分/implement90分は既定を維持。task_watch を使用する読み取り専用の実機 run は deadline=2700/reserve=300/no-progress=600/stop=INT/escalate無し、返ったら全 stop_confirmed を確認する。

## 要件と Task の対応

| 条件 | Task | 観測・検証 |
| --- | --- | --- |
| model/key 和集合、同役割とexclude | 1 | RED/GREENと runner 全テスト、双方の入力 |
| pigt/pidid・カタログ・認証・専用tier | 2 | fake Pi/bwrap、起動前提拒否、新規/既存setup |
| 11改名・5追加・既定構成・文書と手動移行 | 3 | TOML解析・旧新の意味比較、current参照差分確認 |
| 共有モデル解釈・パス・引数・認証・配置 | 司令塔 Task4 | 隔離HOMEの実フロー、8担当実機、正式入口 |
| 個人設定・凍結履歴不変更 | 全体/司令塔 | diff範囲・git status・元ファイル保持確認 |

## Task 1: model_key の共通比較

**Files:** Modify `tools/agent_runner/models.py`, `tools/agent_runner/config.py`, `tools/agent_runner/tests/test_config.py`。

**Interfaces:** Agent に `model_key: Nonblank | None = None`。`_model_identities(agent: Agent) -> set[str]` は存在する model/key の集合。役割ごとの集合にも同じ識別値を蓄積する。

**テスト:** S。異なるモデルの正常構成と provider 別 alias の重複、同じ model をキーで回避できないこと。fallback/exclude の同型テストは既存を再利用する。

- [ ] 既存 `test_duplicate_models_are_rejected_across_all_candidates` を拡張し、キー片側のみ（必要なら既存パラメータ内の別キー例も）で `duplicate_model` を確認。新代表 `test_model_identity_key_rejects_provider_aliases` は別モデルキー無し成功→共通キー重複を確認する。
- [ ] `uv run pytest tools/agent_runner/tests/test_config.py` で RED を保存。
- [ ] 比較を和集合に置換、models_by_role と exclude でも共通適用する。上流 patch はセッション `source-files.json` を参照できる。
- [ ] 同コマンドのGREEN、`uv run pytest tools/agent_runner` を同期実行。余分なテストを足さない。
- [ ] 明示パスを stage し `feat: detect provider aliases with model identity keys` で commit。

## Task 2: pigt/pidid と安全な配置

**Files:** Create `.devcontainer/pigt`, `.devcontainer/pidid`, `.devcontainer/pi-superagents/pigt.json`, `.devcontainer/pi-superagents/pidid.json`。Modify `.devcontainer/pi-models.json`, `.devcontainer/pi-superagents-exec.zsh`, `.devcontainer/install_beforehand.bash`, `scripts/setup_pi.zsh`, `scripts/setup_pi_superagents.zsh`, `.devcontainer/test-pi-superagents.bash`。必要な新しい前提検査は helper 内の小関数とし、既存ロジックを複製しない。

**Interfaces:** 両ランチャーは既存 `pi_agent_directory` / OAuth / `pi_superagents_exec` を利用。専用tierは既存 HOME 基準パス、Piモデルは正規化済 PI_CODING_AGENT_DIR。起動前検査は秘密を解決せずメタデータのみ。既存 helper のパス・認証overlay・bwrap隔離を変えない。

**テスト:** S。カタログ/モデル不足で別モデル起動を防ぐ代表を1件ずつ、必ず通る正常例を同じテストに持つ。setup保持・引数保持は既存テストを優先し重複追加しない。F/L は shell/JSON解析とfake起動で確認。

- [ ] Spec の起動経路/DeepInfra/受け入れ基準と、セッション内 `source-.devcontainer_pidid`、`source-.devcontainer_pi-models.json`、`source-scripts_setup_pi.zsh` を読む。upstreamは参考であり丸ごと置換しない。Pi docs models.md/configuration.md/models-configuration.md と関係する cross-reference を完全に読み、実カタログ構造を確認する。
- [ ] fake Pi/bwrap で pigt のモデル欠落、pidid の対象モデル欠落・正常例を観測する S テストを追加し RED。pidid の壊れた/読めない設定は検査不能を成功にしない。tier の解決可能な明示編集は尊重する。
- [ ] pigt: 親 `openai-codex/gpt-6.1-terra` / xhigh、cheap=`gpt-6-luna`/xhigh、balanced=`gpt-6.1-sol`/xhigh、max=`gpt-6.1-terra`/max。OAuthとモデル解決の前提を確認して起動。
- [ ] pidid: 親/初期全tier=`deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017` / high。DEEPINFRA_TOKEN、models.json、専用configとその全tierの解決を確認し、`--models` を限定、`"$@"` 保持。必要な情報が無ければsetup案内で停止。未知providerやカタログを推測しない。
- [ ] DeepInfra に Spec どおりの対象モデルを追加。旧モデル・他providerを保持。上限65536は運用上限。存在しないtier-guard拡張を参照しない。
- [ ] installとsetupの一覧に両方を追加。setup_pi.zsh は既存 provider helperを維持して、pidid・共通helper・未配置tierを配置。既存tierは --if-absent で保護。実HOMEを変更しない。
- [ ] dry-run用 env に偽 DEEPINFRA_TOKEN を追加、`.devcontainer/test-pi-superagents.bash` と `uv run pytest tools/devenv_migration/tests/test_pi_provider_setup.py`、zsh/bash構文・JSON解析を同期実行。テストの生成物は規定のセッションかmktemp内に置く。
- [ ] 明示パスを stage し `feat: add Terra and DeepInfra Pi launch paths` で commit。

## Task 3: agent 雛形・現在の案内と移行

**Files:** Modify `.devcontainer/agent-runner.toml`, `.devcontainer/README.md`, `tools/agent_runner/interfaces.rst`, `.agents/skills/review-fix-planning/SKILL.md`, `.agents/skills/review-fix-planning/references/execution.md`。他の現在使う旧名参照が見つかったら凍結記録かを判定して報告する。

**Interfaces:** Task1 の任意model_keyとTask2の配置済起動経路を消費。設定の11改名・5追加・3DeepSeek共通キー・割り当てを Spec 表の値で出力する。

**テスト:** F/Lのため新しい固定値テストなし。TOML/JSON解析・旧新の意味比較スクリプト（一時、非commit）・check/list・diff・RST検査で検証。2スキル参照の編集は既定名だけの機械的修正で行動手順は変更しない。writing-skills/skill-creatorが適用される場合は読んで、振る舞い変更のない理由を記録し、固定文言テストで代用しない。

- [ ] Specの命名表・追加表・既定構成を反映。model_key 3件を設定し、既存起動値と env/effort/after_run は保持。冒頭はREADME命名節へリンク。
- [ ] READMEに命名・集合比較・5追加・認証・ランチャー/tier・setupを記載。新規/既存環境を区別し、Piモデル更新手順を実装と整合させる。#243の削除対象旧名は残し移行先のみ新名にする。
- [ ] 個人設定の旧定義を持つ場合/参照だけの場合の手動移行（旧定義削除、agents/fallback更新）を説明。個人設定を変更しない。
- [ ] interfaces.rstのmodel完全一致のみという記述を和集合比較に更新（rst-writerの手順で検査）。review-fixの既定名2参照を更新、手順の意味は維持。
- [ ] 個人設定なし/旧雛形を丸ごと重ねたconfigでcheck/list（4実行）と11既存agentの意味比較を実施。JSON/TOML解析と `uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning tools/agent_runner/interfaces.rst`。
- [ ] 明示パスを stage し `feat: standardize agent catalog names and migration guidance` で commit。

## Task 4: 司令塔の統合・公開・指定ループ

**Files:** Spec/Planの実績追記のみ（PR前）、セッションのログ/検証記録/PR本文。新テストなし（既存とTask1/2の代表を統合実行）。

- [ ] 条件単位でSpec→Task→証拠を照合し、共有のPi解決/パス/setup/引数フローを隔離HOMEで実行確認。新規・旧環境で他provider、バックアップ、編集済tierを保持する。
- [ ] 新5 agentの各1回と既存3担当reviewを、変更版template・個人設定なし・公開設定のプロセス内overlayで実行する。実環境は無変更。runnerの結果・モデルidentity・stop_confirmed・outside_changes・sensitive_pathsを確認し、停止済みの自分の一時worktreeだけ回収。失敗試行は追加しない。
- [ ] 全体review前にSDDのfinal-review手順を読む。repository/ref/base SHAを指定して最終全体レビューを1回実行、必要な修正と検証を行う。
- [ ] README正式入口 `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。Issueの `uv run pytest tools/agent_runner` と launcher 検証も実績を確認。失敗はsystematic-debugging、未解決なら停止。
- [ ] PR前に実績をSpec/Planへ追記してcommit。最後のHEADでclean状態・全コマンドargv/exit/log/baseの検証記録とchecks-fileを作る。
- [ ] Issue/競合/baseを再確認、captured baseとの差分、親のgitleaks scanで確定したSHAだけpush。実PRのbase/head照合。必要な実機確認が残るならRefs #305、残らなければCloses #305。
- [ ] 親のloop.py startをユーザーが指定した空のloop_argsで起動。controllerモデルはpi-model-nameでPI_PROVIDER/PI_MODEL両方を確認。親の旧雛形・現在の個人設定を使う（引数を足して設定を取り替えない）。finalize以外でmergeしない。
- [ ] run結果/関連Issueの観測state/文書とログと資源/時間を報告、Herdrタスクをcompleted。マージ後の個人設定手動移行が必要であることは明記。worktree/branchを勝手に削除しない。

## contingency（代替策）

- 実出力やカタログschemaが想定と違えば、初回REDの証拠を残し、同じモデル・認証・停止保証を保つ最小修正にする。保証を弱める変更はしない。
- 大きなtier拡張は移植せずローカル前提検査を採用。実装規模が増えて予算不足なら切り出し候補と未達を報告し、存在しないpididで完了扱いにしない。
- 実機で認証/限度/接続の問題は未確認として残す。再試行やモデル切替をしない。setupが必要なら実HOMEを変更せず検証用namespaceに公開設定を重ねる。
- base移動・安全の失敗・停止未確認・gitleaks失敗は停止して残存資源を報告。既存ガードを回避しない。
