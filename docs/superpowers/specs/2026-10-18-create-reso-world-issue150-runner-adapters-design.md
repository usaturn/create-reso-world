# Issue #150: 非対話ランタイム adapter の移植

## 実装・検証の完了記録

5 adapterと11 agent定義を実装し、全5 Task・独立レビュー・全体レビューと1回の修正・再レビューを完了した。2026-10-18 18:10 UTC、利用者の障害復旧・実行指示後に `pigod`・`pi-go-glmf`・`pi-gemf` が成功し、既存8件と合わせて全11 agentの実機証跡が揃った。#172はcompletedでclose済み。保留中の認証確認はない。初期実装時はdraftとして記録した。現在の状態とPR #173レビュー修正の結果は末尾の節を基準とし、実行許可・内容承認・実装完了を区別する。以下の停止・保留記録は当時の履歴である。公開と予約解放の結果は#150のPR・完了コメントに記録する。

## 管理と実行許可

- 状態: completed。対象: usaturn/create-reso-world #150、親 #116、PR #173。レビュー修正の実行許可・判定・結果は末尾に記録する。内容の承認を意味しない。
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-150-runner-adapters`。PARENT_ROOT: `/workspaces/reso-world`。
- 実行許可: handoff に記録された issue-to-pr #150（推奨案で設計・実装・検証・commit・scan・push・PRまで）と、今回の利用者の「OK」（Codex標準のサブエージェントで設計・計画作成からPR作成まで進める）。認証設定の変更・マージは含まない。内容承認の記録はなく approved にしない。
- 受け入れ変更の明示許可（2026-10-18）: 「現在、OpenCode Go で障害が起きてるので、OpenCode Go の認証確認は保留にして実装して。保留分は別の Issue にして。」。`pigod`・`pi-go-glmf` の認証・実機確認だけを #172 に移し、#150のコード実装・PR作成を継続する。内容承認を新たに記録せずdraftを維持する。
- 最新の実行許可: 「OpenCode Go の障害がなおったので、認証確認を実行して。」。外部障害復旧という条件変更後、#172の確認として `pigod`・`pi-go-glmf` を新しい使い捨て対象へ各1回実行する。以前の認証失敗や再試行上限を消さず、今回の明示指示と条件変更を区別して記録する。
- 継承元: `tmp/docs_draft/claude_handoffs/20261018T153829Z-issue-150.handoff.json`。旧piの期限切れキーを変更せず、調査・実装・レビューをCodex標準サブエージェントで行う。
- 移植元: usaturn/agent-workspace `a47b2065fddad76b7475752fd0088af0733de204`。保存済みの26ファイルを基に移植する。外部リポジトリのclone・変更は行わない。

## 目的と受け入れ条件

既存 runner から Claude Code・Codex・Cursor・Devin・pi を非対話で起動し、最終payloadとCLIのイベント・出力記録から観測したモデルを受け取れるようにする。後続の #153・#155・#156・#157 が同じagent名と既存protocolを使えることが目的である。

1. 各adapterのprepare/collectと偽CLIを使う実プロセスのテストが通る。stdinまたはpromptファイル、JSON/text、認証・承認待ち、失敗終了、不完全な出力、identityの未観測を検証する。
2. 雛形が有効で、移植したruntimeがsupportedとなる。agentの一覧は運用値なのでテストへ固定して写さない。
3. OpenCode Go以外の9 agentを短い依頼で1回ずつ使い捨て対象に起動し、payload・観測モデル・所要時間・state・stop_confirmedを #150 に記録する。成功済み8件は繰り返さず、未実行の `pi-gemf` だけを確認する。`pigod`・`pi-go-glmf` の認証・実機確認は利用者の明示指示で #172 に移管し、#150の公開を待たせない。認証/承認待ちや未観測のモデルを成功にせず、この2件の定義と失敗分類は維持する。
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

現在の進行条件はD-150-6・D-150-7と受け入れ条件3を基準とする。後半の停止記録は、その時点の全agent実機確認条件と観測結果を残した履歴である。OpenCode Goに関する過去の停止・再試行上限は維持し、最新の明示指示による#172の確認だけを各1回行う。外部サービスの障害・復旧状況は利用者申告であり、別途のサービス状態確認や秘密値の調査は行わない。

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

- D-150-6 選択: OpenCode Goの `pigod`・`pi-go-glmf` の認証・実機確認を [#172](https://github.com/usaturn/create-reso-world/issues/172) に切り出し、残る9 agentの実機証跡と全偽CLI検証で#150のPRを公開する。別案は障害復旧まで全体を待つ、またはagent定義を削除すること。利用者が保留と別Issue化を明示したため、実装と定義を保持し、外部サービスに依存する2件の確認だけを分離する。#172を#150の依存に追加せず、親ボードや他子Issueを変更しない。認証失敗を成功と扱うこと、provider/modelの変更・fallback・資格情報の調査は許可されていない。誤った判断だった場合の影響は、この2 agentの実接続を未確認のまま公開することであり、PRに明記して追跡する。

- D-150-7 選択: 利用者の障害復旧と認証確認実行の明示指示を受け、#172の両agentを各1回確認する。成功すれば結果を#172・#150へ記録して#172を完了し、保留解除をSpec/Planへ追記する。失敗すれば#172は未完了を維持し、D-150-6による#150との切り分けを守る。同条件の追加実行、認証設定変更、provider/modelの差し替えは行わない。これは最新の具体的な指示に基づく実行であり、一般的な継続指示から再試行を推測したものではない。

## 検証と反映

各Taskは対象runtimeのテストでRED→GREENを記録し、実装者の自己確認と別担当による仕様・品質レビューを行う。文書・TOMLだけの固定文言テストは作らず、TOMLのparse/check、RSTの参照・構造、git diff --checkで確認する。最後に全adapter・README所定の全検証とブランチ全体の独立レビューを行う。

実機では一時configに最小workflowを定義し `--config` で渡す。個人設定は更新せず、runnerをrepository rootからforegroundで起動し、bash timeoutを付けない。D-150-6の移管を含む現在の受け入れ条件を確認してから非空のscan済みSHAをpushし、main向けに `Closes #150` のPRを1本作る。マージしない。保留2件を除く実行で失敗した場合は部分成果と残る受け入れ条件を公開して予約をexact-SHA leaseで解放する。

## 部分成果と停止記録（2026-10-18 UTC）

5 adapter、対応テスト・文書、11 agentの設定を実装した。各Taskの独立レビューと、全体レビュー後の1回の修正・再レビューが完了し、指摘4件は修正済み。最終コードは `9a03f744e8544374fa52a400b4d5f3b240062f76`。Python 2181件、shell33件、子エージェント環境のadapter291件、layout/config/diff検査は終了コード0。通常環境のadapterは全体pytestにも含まれる。

実機は8 agentが成功し、9番目の `pigod` が `awaiting_authentication` で停止した。診断にAPI keyの期限切れがあり、`stop_confirmed=true`、payloadなし、outside_changesなし。`pi-gemf` と `pi-go-glmf` は未実行。認証設定・provider・modelは変更せず、再試行しない。全agentの受け入れ条件を満たしていないため状態はdraftのまま、コードのpush・PRは未実施。詳細な観測値・所要時間と再開条件はPlan末尾に記録する。内容の承認記録はない。

### 認証復旧確認後の再開結果（2026-10-18 17:55 UTC）

利用者の「認証は復旧済みです」を受け、新しい担当予約を取得し、残り3 agentだけを新しい使い捨てrepo・一時configで確認するrunを開始した。最初の `pigod` 1回が再び `awaiting_authentication` となり、OpenCode Goの診断は `401 / authentication_error / api_key_expired` だった。runnerは終了コード1、CLIは0、payloadはnull、観測modelは `deepseek-v4.1-flash`、`stop_confirmed=true`、outside_changesは空。run全体は1.767秒で終了した。

停止条件に従い `pi-gemf`・`pi-go-glmf` は未実行のまま。成功済み8件・元ログ・完了済みTaskとレビューは再実行していない。認証ファイル・秘密値は取得・表示・変更せず、別provider/modelや対話へのfallbackも行っていない。この実行で有効だったキーが期限切れと判定されたことは確認できたが、そのキーの設定元や利用者の更新が反映されなかった理由は未確認である。同じ実機認証失敗は記録上2回となったため、同条件の追加実行は行わない。コードは変更せず、停止記録だけを追記した。コードpush・PRは引き続き未実施で、状態はdraft、内容承認なし。

## PR #173 レビュー修正（2026-10-18 UTC）

### 範囲・実行許可

- 利用者は `review-fix-planning #173` を指定した。計画のみの指定はなく、同スキルの完遂経路として検証・必要な修正・既存PRへのcommit/pushを実行する。内容の承認とは区別する。本節は上記の初期実装時の公開制限とは別の、今回の実行許可を記録する。
- 結論: **1 修正してpushする**。承認待ち・新規PR・実機/API/認証の再実行は行わない。
- 現行/レビュー対象HEAD: `1242de097593680dca42552493f82f8bfef75139`。入力は `reviews/usaturn/create-reso-world/#173-feat-issue-150-runner-adapters/` の4ファイル。SWE-2-Max、claude-opus-5-5、gpt-6.1-sol、opencode-go-deepseek-v4.1-flash はすべて同HEAD。
- CODE_ROOT / DOC_ROOT は既存のクリーンな `issue-150-runner-adapters` worktreeを再利用。親checkoutは編集しない。文書検索で本Specと対応Planを特定し、同じテーマの別文書は作らない。
- 確認範囲: PR変更28ファイルの全文、5 adapter、runnerのcollect/プロセス終了/fallback、models、skills helperと関連テスト。独立した読み取り担当が非Codex範囲を確認し、controllerがCodexと実行再現を担当した。

### 指摘の全件分類

主指摘9件に加え、Unverified candidatesを7件として個別に数える。重複指摘も元ファイルのIDごとに残す。Test suggestionsは対応する指摘の検証案であり別件には数えない。

| ID | 区分 | 現行HEADでの根拠・判断 |
| --- | --- | --- |
| SWE-L1 | 対応しない | 成功出力＋stderr `Login complete; continuing` で3 adapterが認証待ちになることを再現。ただし現行CLIの成功stderrでこの診断を出す実在経路は確認されず、診断チャンネルの保守的な扱いという設計論点。現行11 agentの成功記録と矛盾しない。 |
| SWE-I1 | 対応しない | runtime RSTの実機未確認の表現と後続Planの成功記録の時点差。実行手順や結果を誤らせる変更ではなく、記録の追随漏れ。 |
| SWE-U1 | 対応しない | Devinの途中error step拒否はコード上存在するが、通常ATIFのstep直下にはerror/is_errorがなく、観測された成功形式は通る。拡張形式の回復可能errorの意味は未検証で、現行CLIの致命的な経路は確認されない。 |
| SWE-U2 | 対応しない | Claudeは `[` 開始行を無視するが、サポートするstream-jsonはobjectイベント。配列行を出す実在経路による誤成功は示されない。 |
| SWE-U3 | 対応しない | Cursorの未知typed event・型なしobjectの扱いはruntime文書に記された範囲。後続assistant/init・破損JSONの拒否は生きており、正常な通知を捨てる設計変更はしない。 |
| SWE-U4 | 解消済み | 導入版pi 1.3.0 `dist/cli/args.js` のhelpは `--skill` にfileまたはdirectoryを許可する。ディレクトリ指定は正しい。 |
| SWE-U5 | 対応しない | skills helperの解決後境界チェックは意図した制限。出荷Codex/Cursorは `.agents/skills` を直接sourceに含み、symlinkのみの第三者source構成は対象外。 |
| OPUS-M1 | 対応する | JSON文字列値の中に三連バッククォートを含む完全なfenced objectをClaude/Pi/Devinのcollectがresponse_failedにすることを隔離HEADで再現。正しいレビューpayloadを失い主要処理が停止する。(a) |
| OPUS-I1 | 対応しない | SWE-I1と同じ記録の時点差。検証済み度の記載だけで、誤操作を生む手順ではない。 |
| OPUS-U1 | 対応しない | SWE-L1と同じ診断チャンネルの保守的判定。実在する成功stderr経路は確認されない。 |
| GPT-H1 | 対応する | error(Reconnecting)→新しいagent_message→turn.completedのcollectがresponse_failed。導入Codexが再接続後に正常終了する順序でpayloadを失うため致命的。(a) |
| GPT-M1 | 対応する | literal U+2028/U+2029を含む完全な成功イベントでClaude/Pi/Cursor/Codexのcollectがすべてresponse_failed。JSONとして有効な出力をsplitlinesが破壊する。(a) |
| GPT-M2 | 対応しない | OAuth refreshの期限切れ/再利用/失効の3診断がresponse_failedになることを再現。ただし両分類ともrunnerは失敗にし、明示fallbackの規則・停止確認も同じ。正しい回答の消失・誤成功・資格情報変更はなく、復旧案内の粒度の差である。 |
| FLASH-L1 | 対応しない | 空objectがClaude/Pi/Cursorのcollectでsuccessになることを再現したが、正式呼出元runner._collectはinvalid_result/payloadなしにする。response_failedとの差は失敗分類だけで、空回答の成功は起きない。 |
| FLASH-I1 | 対応しない | pi定義にskill_sourcesはないが、現行roleはすべてskills=[]。現行用途を止める不具合ではなく、後続workflowでskillを割り当てる際の設定事項。 |
| FLASH-U1 | 対応しない | SWE-U1と同じDevin拡張error stepの仮説。通常スキーマ・成功記録から致命的な到達経路は示されない。 |
| SR1（反証） | 対応する | Devinのstdout/最終ATIF診断走査もsplitlinesでJSON内Unicodeを切り、後続の `Error: not logged in` / `Approval required` を誤診断。3区切り文字×2診断×片チャネルずつの12件を実行再現し、すべて修正前に失敗。正しいpayloadの消失なので(a)。 |
| SR2（検出力） | 対応しない | snapshotはhardlinkのinode同一性まではassertしないが、現実装のcollectはファイル書込も置換もしない。現行の破損や誤操作ではなくテストの将来の強化案。 |
| SR3（検出力） | 対応しない | 非ゼロ終了統合ケースに解析済みpayloadのassertがないが、失敗state・exit7・停止を検査しており、runnerがpayloadの証跡を保持する既存挙動は変更していない。致命的な欠陥ではない。 |

入力の計: **解消済み1 / 対応する3 / 対応しない12**。自己レビューでSR1（対応する）、SR2・SR3（対応しない）を加えた最終計は **解消済み1 / 対応する4 / 対応しない14**。未確認の候補を解消済みにはしていない。SWE-U1/FLASH-U1の外部拡張形式の意味とSWE-L1/OPUS-U1の実CLI成功stderr到達性は、上記のとおり未検証として残す。課金のある実機起動は追加しない。

### 守る条件の設計と再発判定

- GPT-M1は、`cb240b3`・`9a03f74`で修正したイベントparserと同じ仕組みの2回目。OPUS-M1は `01c37c2` のDevin `_json_object` と同じ仕組みの2回目。直す関数が過去の致命的修正と同じため、今回は設計の見直しとして扱う。
- 過去の修正は破損・未完了出力を拒否することを重視し、有効なJSON文字列内の区切りをデータとして保持する条件が不足していた。GPT-H1の全error拒否は初期Codex実装からあり、9a03f74の不正typeガードが生んだ回帰ではない。
- 条件A: JSONLのレコードはLFだけで区切り、すべてのJSON文字列内の有効なUnicode文字を、payload・identity・skill観測・診断のどの再解析でも保存する。Devinのstdout/最終ATIFの未解析テキストを診断走査する経路も含む。破損や未完了の拒否は維持する。
- SR1は自己レビューでの同じ条件の再発（きっかけ3）。初期表でDevinの走査を「prose」とだけ見て対象外にしたことが不足だった。仕組みを起点に5 adapterのJSON入力と診断走査を再確認し、Devinのdecode前の両回答チャネルの走査もLFだけにする。JSONをdecodeした後のtailは既にobject外なので、そこでのprose行分割・診断拒否は維持する。点の文字列特例・Unicode非対応への保証縮小ではなく、構造上の区切りを統一する案を継続する。自己レビュー後のこの変更は再レビューしていない。
- 条件B: JSONの構造境界はJSON decoderに決めさせ、文字列値中のバッククォートをMarkdownの閉じ境界にしない。欠けた閉じフェンス・破損object・Devinの後続診断や二つ目のJSONは従来どおり拒否する。
- 条件C: Codexのerrorは直ちに最終失敗と決めず、後続の新しい完全なagent_messageとturn.completedで回復を確定する。未回復error・turn.failed・後続未完了・破損・非ゼロ終了・停止未確認を成功にしない。認証/承認診断を通常payloadの検索へ広げない。

| 守る条件 | 経路 | 判定 | 変更前の挙動 | 確かめるassertion・方法 |
| --- | --- | --- | --- | --- |
| A | Claude/Pi `_events` とcollect→identity/skill evidence | 修正する | splitlinesがU+2028/U+2029を途中で切る | literal区切り文字入り成功のpayload・観測model・skill hashが元と一致、破損末尾はfailure |
| A | Cursor collect・破損検査・diagnostics・skill_versions | 修正する | 同じ出力を4経路でsplitlines | payload/identity/skill hashを保持し、診断と破損検査も同じLF分割 |
| A | Codex collect・malformed・diagnostics・rollout照合・rollout_fields・skill_versions | 修正する | 同じJSONLを6経路でsplitlines | stdoutとrollout双方のliteral Unicode、session一致・model/effort/hash、失敗イベント分類 |
| A | Devin stdout/最終ATIFのdecode前の診断行走査 | 修正する（SR1） | JSON文字列をsplitlinesで切り出し認証/承認の誤診断 | 3区切り文字×2診断×stdout/ATIF単独の12件がsuccess、stdoutのpayloadを元objectと比較 |
| A | Devin export JSON・decode後tail、runnerの書込例外行検査 | 既に満たす／対象外 | exportはjson.loads、tailはobject外、runnerは別目的 | export内Unicodeを保持し、実際の後続診断/別JSONは拒否。runnerの例外行検査は変更しない |
| B | Claude/Pi `_json_object`→`_payload`→collect | 修正する | 非貪欲フェンスregexが値の中で切る | fenced JSONに内側のコード片を含めても元objectと一致、破損/閉じ不足を拒否 |
| B | Devin stdoutと最終ATIFの両方の `_json_object` | 修正する | 非貪欲regexが閉じを誤認 | 両チャネルの成功と各チャネル単独破損、後続診断/別JSONの拒否を比較 |
| B | Codex/Cursor `_json_object` | 既に満たす | raw_decodeを使用 | 同じfenced JSONを元objectで回帰確認、parser自体は変更しない |
| C | Codex collectのtext/completed/error診断とturn.started/item.completed/turn.completed/turn.failed | 修正する | any(error)と全診断が回復を無視 | retry error後の新message+completedだけsuccess、末尾error/失敗/欠けたmessageはpayloadなし |
| C | runner._collect・execute後のexit/停止判定・assignment fallback | 既に満たす | 非ゼロ/停止未確認を成功にせず明示fallbackのみ | 偽CLI統合でexit0/停止/identity/payload/outside_changesを比較、非ゼロも引き続きfailure |

比較した案:
1. 点の修正（フェンスregexを貪欲化、Reconnecting文字列だけ特例）: JSON中のバッククォート数や診断文面に依存し、同じ誤りを再発させるので不採用。
2. **採用**: 既存adapterの範囲内で、JSONL再解析をすべてLFに統一し、フェンス開始後のJSONをraw_decodeしてから閉じフェンスを検査する。Codexはイベント順の未回復error・新message・完了を一つの状態判定にまとめ、診断分類にもその結果を使う。共有runnerやskills helperへ新しい責務を持ち込まない。
3. PRの保証を狭め、Unicodeやフェンス内コードを非対応にする: 正当なJSONと通常のレビュー回答を除外するため不採用。別PRへの分割もしない。

### 実装・検証チェックリスト

- [x] 全レビュー、固定HEAD、PR/remote/context、既存Spec/Plan、過去の修正を確認。
- [x] 隔離worktreeで上記のUnicode4経路・fence3経路・Codex復旧と分類差をcollectで再現。固定HEADの一致を確認し、調査用worktreeと親一時ディレクトリはSpec更新前に削除済み。
- [x] Task 1: 3件と自己レビューSR1の実行回帰テストを先に追加してREDを確認し、adapter内を修正してGREEN。テスト必要: 入出力解析と既存不具合を実行で検査するため。境界は成功payload/identity/skill読み取り、未完了・後続失敗を含める。
- [x] Task 2: 全adapterと関連runnerのpytest、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、config parse/check、diff check。文書の固定文言テストは不要で、Spec/PR説明は参照と整合を確認する。
- [x] Task 3: 反証・PR全体・検証の検出力を1回だけ自己レビュー。出た致命的問題を修正して検証を再実行し、2回目のレビューはしない。
- Task 4（公開手順）: 実在する非対応制約をPR本文へ記録し、Specに最終結果を記載してcompletedにし、一度だけcommit。head再確認・context・Gitleaks検査後に既存PRへpushし状況コメント。再利用worktreeは削除しない。

実行予算: 今回の能動時間60分目安（調査15、実装15、検証15、自己レビュー/公開15）。実装担当は同期でテスト完了を待つ。安全失敗は再試行せず停止、テスト/信頼性失敗は原因を切り分け同条件の再試行は1回まで。各phaseで進捗と残作業を確認し、課金のあるlive実行・不要な文書修正を追加しない。これらは中断や未検証のままpushする根拠にはしない。

### 最終検証・自己レビュー結果

- TDD: 初回の回帰は正しいfixtureで40 failed / 41 passed、偽Codexの復旧統合は1 failed / 11 passedを確認してから実装した。テスト作成時の必須引数欠落とoutside_changesの参照先誤りは修正し、setup失敗をREDの根拠にはしていない。SR1は3区切り文字×2診断×2チャネルの12件すべてが期待どおりRED、その後GREEN。
- 修正後の最終検証: `uv run --locked pytest -q` **2291 passed / 464.99秒 / exit0**。全adapterは **401 passed / 6.32秒 / exit0**（初期291から110件追加）。`bash .devcontainer/run-tests.bash` **33 PASS / 335秒 / exit0**。`bash scripts/check-layout.sh` **PASS / exit0**、config check **5 runtime / 11 agent supported / exit0**、diff check **exit0**。private repoのActionsは規約により確認不要。実モデル・API・認証設定は追加で実行/変更していない。
- 自己レビューは反証・PR全体・検出力の3担当を同期で直列に起動し、1サイクルだけ実施した。ツール不足による最初の2 dispatchはレビューを行わずNEEDS_CONTEXTで終了し、controllerがdiffをファイル化した後に各担当がレビューを完了した。PR全変更ファイルに未読箇所はない。反証のSR1は修正し、検出力のSR2/SR3は上表の理由で対応しない。**SR1修正後は再レビューしていない**。最終検証はその後にやり直した。
- 失敗時の検証: Devinのstdout/ATIFそれぞれに異常を一つだけ入れ、stdout・stderr・export・receipt・hardlink先・symlink先を含む試験ツリー全体の有無/bytes/mode/種類/リンク先を前後比較した。collect中はPopen/os.systemも禁止し、書換えや外部実行がないことを検査した。hardlinkのinode同一性そのものはassertしていない（SR2）。
- 検出力の対照: 別の隔離worktreeに修正後の内容を写し、1回につきガードを一つだけ外した。Claude閉じフェンス1、Pi閉じフェンス1、Devin閉じフェンス2、Codex旧message無効化1、turn.failed保持1、session不一致拒否3、計 **6変異・9負例すべてが失敗（各pytest exit1、setup error0）**。元の専用worktreeではガードを外していない。隔離worktree・親一時ディレクトリは検証直後に削除済み。
- 初回調査の再現結果と過去の致命的修正を根拠に設計を見直し、自己レビューSR1で診断の入口まで経路表を広げた。残る未検証事項は全件分類で明示した外部CLI成功stderr・ATIF拡張形式であり、指摘0件を解消の根拠にしていない。
- 所要時間: 着手19:11 UTCから公開前の最終確認 **20:04 UTC頃まで約53分**。調査/選別/設計約10分、実装担当約13分（検証を含む）、controllerの追加検証/対照約7分、自己レビュー準備と3担当約11分、SR1修正と最終回帰約10分、記録/公開準備約2分。初期・最終のPython回帰とshell検証は並行時間を二重計上しない。公開結果は本Specへ追記せず、状況コメントと完了報告に残す。
