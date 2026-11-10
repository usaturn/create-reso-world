# Issue #363: Claude Code の非対話コマンドを foreground に限定する

## 管理・実行許可
- 状態: completed。内容承認は受けていない。利用者の明示的な実行許可とレビュー修正ループによる検証・判断の完了を表す。
- 対象: usaturn/create-reso-world#363、PR base: origin の refs/heads/main。
- 利用者入力: `#363 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max`
- 追加指示: 「途中で main が進んでいる場合は留意して止めずに進めてください」。
- 通常の設計判断、検証、commit、scan、push、PR、指定ループの finalize によるマージまで実行許可。安全境界・未知の検証結果を成功にする許可ではない。

## 目的と原因
Claude Code が長い Bash を自動でバックグラウンドへ移すと、完了通知による次ターンが最後の result を置き換える。正しい JSON が先にあっても response_failed になる。以前の回答を採用して後続の作業を隠すのではなく、非対話の担当の起動時だけバックグラウンドを無効化する。

## 範囲
変更するコードは `tools/agent_runner/adapters/claude_code.py` の prepare が返す LaunchSpec.env のみ。
coordinator の裁定 https://github.com/usaturn/create-reso-world/issues/363#issuecomment-6764066596 に従う。
`.devcontainer/agent-runner.toml`、`tools/agent_runner/runtimes/claude-code.rst`、対話用の `.claude/settings.json`、_classify、runner、他 adapter、既存テストは変更しない。
#363 は #349 の native な子ではなく、先行なしの単独 follow-up。#370 は本件の完了後に同じファイルへ着手する。

## 設計・受け入れ基準
- 動作環境: Dev Container の uv / Python、非対話 agent-runner の claude-code adapter。
- 実入力: json/text の役割と日本語・改行を含む prompt（例「確認する\n結果を返す」）。prepare が返す env に `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS="1"` と `BASH_DEFAULT_TIMEOUT_MS="600000"` を設定する。argv と stdin の既存仕様は保つ。
- 防御範囲: runner の当該 CLI 子プロセスだけへ適用する。親環境や対話設定は書き換えない。成功 result の後の通知・非 JSON result を成功扱いにせず、_classify の拒否を維持する。
- timeout は adapter の固定値。600 秒が有効な設定の最短役割期限を超えないことを一時プローブで確認する。現行雛形の最短は inspect/self-review/fix-check の2700秒、implement は5400秒。個人設定が短い期限を設定した一般の場合に合わせる動的な調整は今回の範囲外で、runner の外側の期限が引き続き優先する。
- 実 CLI で自動バックグラウンド化を再現する有料実験は行わない。今回の指定された実装担当と PR レビューの起動は workflow のためだけに行い、効果確認の実験とは区別する。

## 決定記録
|項目|選択した案|検討した別案|選択理由|委任または停止条件|
|---|---|---|---|---|
|D1|LaunchSpec.env に固定2値|共通設定や個人 env の継承|coordinator が adapter に限定。対話を巻き込まず、継承漏れをなくす|Issue の明示裁定|
|D2|既定 timeout 600000ms|2分のまま、動的 role 計算|約5分の既存検証を収め、現行最短45分の期限より短い。runner の期限は維持|通常設計の委任|
|D3|_classify は変更しない|最後より前の有効 JSON を採用|後続作業を隠す誤成功を防ぐ|既存の安全境界|
|D4|恒久テストは追加しない|env の固定値照合テスト|採用基準 L。失敗は response_failed として可視化される|Issue と裁定のテスト方針|
|D5|runner の指定担当へTaskを1件依頼|self実装|implement_task.py check: self=false、agents=[pi_opencode-go_deepseek4-flash_max]、fallback=[]|利用者の --implement|
|D6|最大3サイクル、指定inspect3名・implement1名|ループなし|--merge 明示。3は既定適用、self-review/fix-check は既定self、fallbackなし|check-options成功|
|D7|main 前進は証拠を残し再検証して継続|捕捉SHAを黙って差し替える、直ちに停止|追加指示により前進だけでは止めない。元のbase JSONを保全し、旧/新差分・取り込み・検証・新記録を別名で保存する。履歴はrebaseせずmergeし、force pushしない|競合が所有や仕様の意味を変える場合は停止。finalizeのguardは緩めない|

## 検証と限界
Context7 CLI で公式 env-vars / interactive-mode / tools-reference を照会済み。公式仕様では背景無効時は timeout でコマンドが止まり、BASH_DEFAULT_TIMEOUT_MS はms単位の既定timeoutである。
一時プローブで prepare の変更前後と json/text・stdin・最短期限・既存分類を確認し、既存adapterテストを回帰する。README の非ワールド検査入口3本も実行する。
fake/一時ファイルによる検査は実 CLI の実測ではない。実機確認をマージ後の必須条件にはしない。

## PR #379 サイクル1の判断・実行結果
planner: gpt-6.1-sol（pi、PI_PROVIDER=openai-codex を確認）。入力の対象HEADはすべて `c075f48fbc99e3a81447208671f904d0c667d28c`。

|レビューファイル|モデル|runtime|レビューHEAD|再実行|推奨|
|---|---|---|---|---|---|
|claude-opus-5-5.md|claude-opus-5-5|claude-code|c075f48fbc99|true|Approve|
|SWE-2-Max.md|SWE-2 Max|devin|c075f48fbc99|true|Approve|
|deepseek-v4.1-flash.md|deepseek-v4.1-flash|pi|c075f48fbc99|true|Approve|

前の判断は0件、active指摘0件、未検証候補1件。全入力を採用し、除外したレビュアーはない。分類: 解消済み0 / 対応する0 / 対応しない1。結論2（修正不要）、コードの追加修正・自己レビュー・fix-checkの起動は0回。修正担当の割り当ては利用者指定の `pi_opencode-go_deepseek4-flash_max`、self-review/fix-checkは既定selfだが、修正がないため起動していない。

### 対応しない候補
- `SWE-2-Max#U-1@c075f48fbc99`: Monitor/MCP taskの完了通知も防ぐという追加保証は採用しない。公式env-varsは、この2経路は背景で動くと明記している。今回の要件はtimeoutしたBashの自動背景化の停止であり、すべての非同期通知をなくすことではない。`_classify` はbaseと同じで、通知後の非JSON resultを失敗にする経路は変更前にも存在する。実CLIでこの候補の第2ターンが発生するかは未検証であり、「起きない」「解消した」とは判断しない。PR起因の致命的欠陥や今回の必須条件の欠落とは認めず、範囲外の設計要求として対応しない。実環境の発生証拠と別の実行許可、または全通知抑止を求める要件が出た場合に見直す。
- この制限はPR本文にも明記する。分類の基準をレビュー後に変えたものではなく、当初からBashの背景化・prepare.envに限定した要件との照合である。

### 要件・証拠の対応
|条件|判定|観測結果・根拠|
|---|---|---|
|固定env、json/text、日本語・複数行stdin、親環境不変|満たす|controllerのprobe.py、base比較でargv/stdin不変、2値を確認。runner.py:315-345/process.py:368の子への適用も精読|
|timeoutが最短期限より短い|満たす|設定の最短2700秒。呼出側のfix-check短縮1800秒（run_roles.py:135、dispatch.py:117）も600秒より長い|
|厳格な回答分類、所有境界|維持|単一result成功/通知後result拒否のbase対照。コード差分はprepareのみ。toml・runtime文書・対話設定・既存テストに差分なし|
|今回の変更の回帰・全体検証|満たす|clean HEAD c075f48fでadapter140件、README入口のPython1387件（832.87秒）、シェル27件、配置検査、probe、diff-checkがすべてexit0|
|実CLIの背景化・Monitor/MCPの通知|対象外|有料再現実験は0回。公式仕様とfakeによる検査を実機成功に読み替えない|

共有条件の統合担当はcontroller。変更ファイルの全文、runnerの環境合成、process起動、adapterテストを読み、条件単位のプローブ・既存検証と照合した。最後の追加はこのSpecの記録だけで実装経路は変わらないため、同一clean HEADの検証記録を再利用する。

確認済み一覧: `reviews/usaturn/create-reso-world/#379-fix-issue-363-claude-foreground/verified/c075f48fbc99.json`。工程記録: 同ディレクトリの `c075f48fbc99.planning.json`。runtimeの未確認候補は一覧でも未確認として残し、採否は本節で区別する。

実装依頼1回・176.4秒（実測opencode-go/deepseek-v4.1-flash、effort=max、exit0、停止確認済み）。Task/全ブランチレビューは修正要求なし。PRレビュー段階は約578秒（3名並行、全員accepted、保持資源なし）。全体の経過は約46分時点で最終化へ進む。検証記録とログは `/workspaces/reso-world/tmp/agents/issue-363.1jibklo0/` に保持する。uvのVIRTUAL_ENV不一致警告は親を使わずworktree環境を選ぶ旨であり、終了コード0と実行先を確認した。push・マージ・Issue更新の結果はこのSpecへ先取りせず、状況コメントと完了報告へ記録する。
