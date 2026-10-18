# Issue #150: 非対話ランタイム adapter の移植

## 管理と実行許可

- 状態: draft。対象: usaturn/create-reso-world #150、親 #116。
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-150-runner-adapters`。PARENT_ROOT: `/workspaces/reso-world`。
- 実行許可: handoff に記録された issue-to-pr #150（推奨案で設計・実装・検証・commit・scan・push・PRまで）と、今回の利用者の「OK」（Codex標準のサブエージェントで設計・計画作成からPR作成まで進める）。認証設定の変更・マージは含まない。内容承認の記録はなく approved にしない。
- 継承元: `tmp/docs_draft/claude_handoffs/20261018T153829Z-issue-150.handoff.json`。旧piの期限切れキーを変更せず、調査・実装・レビューをCodex標準サブエージェントで行う。
- 移植元: usaturn/agent-workspace `a47b2065fddad76b7475752fd0088af0733de204`。保存済みの26ファイルを基に移植する。外部リポジトリのclone・変更は行わない。

## 目的と受け入れ条件

既存 runner から Claude Code・Codex・Cursor・Devin・pi を非対話で起動し、最終payloadとCLIのイベント・出力記録から観測したモデルを受け取れるようにする。後続の #153・#155・#156・#157 が同じagent名と既存protocolを使えることが目的である。

1. 各adapterのprepare/collectと偽CLIを使う実プロセスのテストが通る。stdinまたはpromptファイル、JSON/text、認証・承認待ち、失敗終了、不完全な出力、identityの未観測を検証する。
2. 雛形が有効で、移植したruntimeがsupportedとなる。agentの一覧は運用値なのでテストへ固定して写さない。
3. 各定義agentを短い依頼で1回ずつ使い捨て対象に起動し、payload・観測モデル・所要時間・state・stop_confirmedを #150 に記録する。認証/承認待ちや未観測のモデルは受け入れ成功にしない。
4. `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` が通る。private repository のActionsは無効でCI確認不要。

## Global Constraints

- runner本体、`adapters/__init__.py`・`adapters/skills.py`・`models.py`、DSH、ランチャー、zshrc、雛形のroles.*・workflows.*・agents.dsh-*を変更しない。
- 追加するコードは5 adapterと各 `tests/adapters/<runtime>/`、文書は `tools/agent_runner/runtimes/`、設定は非DSH agents.*だけに置く。Spec/Planは `docs/superpowers/` に置く。
- `tools/workspace`・`projects.toml`・Grok Build・新しい依存・CIを導入しない。親 #116 のD-1〜D-24とreview-fix-planningの判断基準を維持する。
- `AdapterContext` → `LaunchSpec` → `AdapterOutcome` とモジュールの `ADAPTER` を使う。promptはstdinかattempt内のファイルで渡し、argvへ本文を入れない。collectはローカル解析のみでプロセスを起動しない。
- identityは観測値だけを返し、要求model/provider/effortをコピーしない。未観測はnull/空map。skill_versionsは成功した読み取りで内容を確認できた場合だけ記録する。
- 認証・承認待ち、不完全な応答、CLIの失敗を成功にしない。モデルや対話方式への暗黙fallbackは追加しない。
- Pythonはuvで実行する。通常テストは偽CLIだけを使い、実機確認はcontrollerが各agentにつき1回行う。認証値を取得・表示・更新しない。
- 親checkoutと他者のbranch/worktreeを変更しない。未コミットの記録はPARENT_ROOTの `tmp/agents/issue-150.x_25tm6g/` に保存する。

## 先行条件と現在の状態

2026-10-18の再確認で #149 はclosed/completed、PR #163 はmainにマージ済み（`6ca0ec8`）。native blocked_byは #149 のみ。最新origin/mainは `a024a22626d4ff6daa46e92aa7cb8aae081aa7ac`。継承worktreeは同じHEAD・clean・独自commitなしで、既存の基準テストは1891 passed（426.68秒）。#150の競合PR・他者の予約は無い。専用refを今回のセッションで取得し、所有権を各外部書き込み前に再確認する。

## 設計

共通の起動・停止・worktree・receipt検証・redactは #149 のrunnerへ任せる。各adapterは既存protocolだけに依存し、CLIのargv構築と形式固有の解析を担当する。`ADAPTER` を公開すれば固定の登録表から自動的に見つかる。共有コードへの新しい抽象化や登録は追加しない。

| runtime | 入力・起動 | payload・identityの根拠 |
| --- | --- | --- |
| pi | 既存launcher + print/json/no-session、provider/model/thinkingを明示、stdin | agent_endの最後のassistant、正常stopReasonとagent_settled、session/メッセージのモデル |
| claude-code | claude -p、stream-json/verbose、model/effort、非対話permission | system/initとresult。permission_denials、is_errorを解析 |
| codex | codex exec --json、roleに応じread-only/workspace-write、model/effort、stdin | thread.started、最後のagent_message、同じsessionのrollout。探索は実際のchild環境に合わせる |
| cursor | agent -p、stream-json/trust、read roleはask、write roleはforce、stdin | system/initとresult。診断と最終回答を区別する |
| devin | devin -p、prompt-file/export、model、非対話permission | stdoutとATIF exportのagent/session。exportの欠落・不完全な最終応答を失敗にする |

model identityがログに無ければnullとし、起動設定を観測結果の代わりにしない。スキルのパスに言及しただけでは読み取りの証拠にせず、既存の `verified_versions` を利用できる場合は再利用する。CLIの版やイベント形式の相違は偽CLIのfixtureとruntime文書へ反映し、追加CLI呼び出しをcollectへ持ち込まない。

### agent定義

移植元の `claude-opus`・`devin-swe`・`pi-gpt`・`pixg`・`pi-deepseek`・`pigod`・`pi-go-glmf`・`codex`・`cursor`・`cursor-grok47` を、移植先の導入済みコマンド/launcherに合わせる。`origin/main` に `pigemf` があるので `pi-gemf` も定義する。既定のレビュアーやworkflowはここでは追加しない。

`pi-go-glmf` は移植元と同じ導入済みの raw `pi` を使い、provider `opencode-go`・model `glm-5.3-flash`・effort `max` を明示する。モデル専用launcherは必要なく、現行のpigo/piglは変更・代用しない。Piの現行launcherが使う `OPENCODE_API_KEY` をenv許可へ反映する。その他のlauncherは現行ファイルを確認して設定を合わせる。envは資格情報の名前だけを列挙する。

### エラーと安全条件

CLIが終了コード0でも完全な応答・receiptが無ければ成功にしない。認証/承認エラーはCLIの診断や失敗イベントから判別し、正常回答に含まれる説明文はエラーにしない。runnerが担当するtimeout・cancel・子孫停止・redactを偽CLIの統合テストで確認する。skill_versionsの記録は成功したreadと内容の一致が根拠であり、設定したskill名や単なるパスの出現は根拠にしない。

## 決定記録

- D-150-1 選択: 既存adapterの移植と必要な適応。別案: CLI wrapperだけでreceiptを生成、新規に共通adapterを設計。既存のイベント解析とテストを保て、#149の範囲へ手を入れずに済むため移植を選ぶ。通常設計判断として委任範囲内。
- D-150-2 選択: runtimeごとに実装・テスト・runtime文書・対応agents.*をまとめ、5 Taskを直列SDDで実行する。別案: 全runtime一括または並列実装。個別にレビューでき、同じTOMLへの競合を避けられるため直列を選ぶ。利用者の指定した実行方式を保つ。
- D-150-3 選択: skill_versionsの不確かな観測を空mapのままにする。別案: 設定/パスから現在のファイルをhash。既存protocolの「実測」に合わないので後者は採らない。正確な観測を追加する範囲は各adapter内に限る。
- D-150-4 選択: fakeを先に検証し、実機は最終レビュー後に各定義agentを1回ずつ確認する。別案: 実装中の反復実機。不要なAPI実行と他者の環境への変更を避ける。必要なAPIが失敗した場合は停止して未完了の条件を報告する。

- D-150-5 選択: `pi-go-glmf` を移植元と同じ raw `pi` と明示的なprovider/model/effortで定義する。最終レビュー I-3 で、元の起動コマンドは導入済みの `pi` であり、モデル専用launcherを使っていないと確認した。親D-13は利用可能なrawコマンドによるagentを除外しないため、当初の省略判断を撤回する。元のIssueが指定したagentを復元する通常の設計修正として、issue-to-prの実行許可内でcontrollerが裁定した。利用者による内容承認は記録せずdraftを維持する。pigo/piglの変更や再解釈はしない。`pi-gemf` は現行pigemfが存在するため含める。

## 検証と反映

各Taskは対象runtimeのテストでRED→GREENを記録し、実装者の自己確認と別担当による仕様・品質レビューを行う。文書・TOMLだけの固定文言テストは作らず、TOMLのparse/check、RSTの参照・構造、git diff --checkで確認する。最後に全adapter・README所定の全検証とブランチ全体の独立レビューを行う。

実機では一時configに最小workflowを定義し `--config` で渡す。個人設定は更新せず、runnerをrepository rootからforegroundで起動し、bash timeoutを付けない。全結果を確認してから非空のscan済みSHAをpushし、main向けに `Closes #150` のPRを1本作る。マージしない。失敗時は部分成果と残る受け入れ条件を公開して予約をexact-SHA leaseで解放する。

## 部分成果と停止記録（2026-10-18 UTC）

5 adapter、対応テスト・文書、11 agentの設定を実装した。各Taskの独立レビューと、全体レビュー後の1回の修正・再レビューが完了し、指摘4件は修正済み。最終コードは `9a03f744e8544374fa52a400b4d5f3b240062f76`。Python 2181件、shell33件、子エージェント環境のadapter291件、layout/config/diff検査は終了コード0。通常環境のadapterは全体pytestにも含まれる。

実機は8 agentが成功し、9番目の `pigod` が `awaiting_authentication` で停止した。診断にAPI keyの期限切れがあり、`stop_confirmed=true`、payloadなし、outside_changesなし。`pi-gemf` と `pi-go-glmf` は未実行。認証設定・provider・modelは変更せず、再試行しない。全agentの受け入れ条件を満たしていないため状態はdraftのまま、コードのpush・PRは未実施。詳細な観測値・所要時間と再開条件はPlan末尾に記録する。内容の承認記録はない。

### 認証復旧確認後の再開結果（2026-10-18 17:55 UTC）

利用者の「認証は復旧済みです」を受け、新しい担当予約を取得し、残り3 agentだけを新しい使い捨てrepo・一時configで確認するrunを開始した。最初の `pigod` 1回が再び `awaiting_authentication` となり、OpenCode Goの診断は `401 / authentication_error / api_key_expired` だった。runnerは終了コード1、CLIは0、payloadはnull、観測modelは `deepseek-v4.1-flash`、`stop_confirmed=true`、outside_changesは空。run全体は1.767秒で終了した。

停止条件に従い `pi-gemf`・`pi-go-glmf` は未実行のまま。成功済み8件・元ログ・完了済みTaskとレビューは再実行していない。認証ファイル・秘密値は取得・表示・変更せず、別provider/modelや対話へのfallbackも行っていない。この実行で有効だったキーが期限切れと判定されたことは確認できたが、そのキーの設定元や利用者の更新が反映されなかった理由は未確認である。同じ実機認証失敗は記録上2回となったため、同条件の追加実行は行わない。コードは変更せず、停止記録だけを追記した。コードpush・PRは引き続き未実施で、状態はdraft、内容承認なし。
