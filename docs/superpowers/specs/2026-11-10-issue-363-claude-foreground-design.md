# Issue #363: Claude Code の非対話コマンドを foreground に限定する

## 管理・実行許可
- 状態: draft。内容承認は受けていない。
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
