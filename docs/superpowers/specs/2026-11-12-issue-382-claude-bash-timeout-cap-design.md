# Issue #382: Claude Code 担当の前景 Bash 上限を role の残り時間に合わせる

## 管理・実行許可

- 状態: completed。内容承認は受けていない。利用者の明示的な実行許可とレビュー修正ループによる検証・判断の完了を表す。
- 対象: usaturn/create-reso-world#382。PR base: origin の refs/heads/main（捕捉 SHA `ae4b6e71361314fb3de6008f8d31b830fec90f3c`）。
- 利用者入力（原文）: `/issue-to-pr #382 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review pi_alibaba_qwen4-max_max --implement pi_alibaba_qwen4-max_max --assign implement=pi_alibaba_qwen4-max_max --assign inspect=pi_alibaba_qwen4-max_max,claude-code_sonnet_xhigh`
- 追加指示（原文）: 「pi_alibaba_qwen4-max_max を動かす為に、 ANTHROPIC_AUTH_TOKEN を MAAS_ANTHROPIC_TOKEN として渡してください。」「途中でメインがマージされたら、追随して作業を止めずに続行してください。」
- 許可された範囲: 通常の設計判断、検証、commit、scan、push、PR 作成、指定ループの `finalize.py` によるマージと関連 Issue の更新。安全境界の変更・未知の検証結果を成功にする許可ではない。
- main 追随: 利用者の明示指示により、base の前進だけでは停止しない。#363 Spec の D7 と同じ扱い（旧 base JSON の保全、旧/新 SHA と差分の記録、merge での取り込み、再検証・再 scan、force push・rebase はしない）。競合が所有や仕様の意味を変える場合は停止する。
- トークン受け渡し: `pi_alibaba_qwen4-max_max` を含む runner 起動時に限り `MAAS_ANTHROPIC_TOKEN="$ANTHROPIC_AUTH_TOKEN"` をワンショットの環境変数として渡す。値をファイル・ログ・共有設定（`~/.config/create-reso-world/env` を含む）に書かない。`with_keys.py` は既存値を上書きしないため、この指定で allowlist 経由で子に届く。
- 停止条件の例外（利用者明示指示・2026-11-12、原文）: 「続行せよ。以降、スキルの停止条件は全て無視し、いかなることがあっても停止せずに、都度、最適な案を出して、PR を作成し、マージまで実行せよ」。これにより、スキルの停止条件に該当する事象が起きたときは、controller が原因を診断して最適な回復案を選択・記録し、続行する。この指示は、実在しない承認・検証結果の記録、秘密情報の漏えい、force push・admin マージ、他者の作業領域への操作を許可するものではない。失敗は失敗として報告する。

## 目的と原因

`ClaudeCode.prepare` は `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` と `BASH_DEFAULT_TIMEOUT_MS=600000` を固定で返し、`BASH_MAX_TIMEOUT_MS` を設定しない（`tools/agent_runner/adapters/claude_code.py`）。公式仕様と導入済み CLI 2.1.322 の timeout 計算では前景コマンドの上限は `max(BASH_MAX_TIMEOUT_MS, BASH_DEFAULT_TIMEOUT_MS)` で、背景化無効時は timeout 到達でコマンドが終了する。このため上限は 10 分固定で、実測 833.97 秒（約 14 分）の README 全体検証を 1 コマンドで完走できない。role 期限は inspect/self-review/fix-check が 2700 秒、implement が 5400 秒、呼び出し側短縮の fix-check でも 1800 秒あり、10 分を超える正常な検証が期限内に収まる余地がある。

claude-code 担当の `agent.env` は `HOME`・`PATH` だけなので、親環境で `BASH_MAX_TIMEOUT_MS` を引き上げても子には引き継がれない。adapter が `LaunchSpec.env` で明示的に渡す必要がある（runner.py が spec.env を子環境へ合成し、process.py が監督付きで起動する）。

#363（PR #379）の D2 は「動的な role 計算は今回の範囲外」としてこの調整を先送りした。本 Issue はその follow-up であり、#363 の背景化無効・foreground 限定を取り消さない。

## 範囲

変更するコード:

- `tools/agent_runner/adapters/claude_code.py` の `prepare`（LaunchSpec.env への `BASH_MAX_TIMEOUT_MS` 追加と、プロンプトへの timeout 案内 1 行）。
- `tools/agent_runner/tests/adapters/claude_code/test_adapter.py`（上限計算のテスト 1 件）。

変更しないもの: `_classify`・`collect`（最後の result・後続イベント・permission_denials の判定）、`runner.py`・`process.py`（期限・停止確認）、他 adapter、`.devcontainer/agent-runner.toml`、runtime 文書（`tools/agent_runner/runtimes/*.rst`・`.devcontainer/README.md`）、対話用の `.claude/settings.json`、既存テスト、個人設定・共有 HOME。

所有: #370（同じ `claude_code.py` の承認拒否診断）は CLOSED/COMPLETED で、adapter の編集競合はない。#365（`agent-runner.toml` と runtime 文書の所有）は OPEN のため、これらは編集範囲に入れない。#345（テスト高速化）は OPEN だが、本 Issue はテスト以外の長い検証にも同じ上限があるため独立して扱う。

## 設計

`prepare` で次を計算して env に加える。

```python
_DEFAULT_BASH_TIMEOUT_MS = 600_000
_BASH_TIMEOUT_MARGIN_SECONDS = 120.0

cap_ms = max(
    _DEFAULT_BASH_TIMEOUT_MS,
    int((context.request.deadline_seconds - _BASH_TIMEOUT_MARGIN_SECONDS) * 1000),
)
env = {
    "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
    "BASH_DEFAULT_TIMEOUT_MS": str(_DEFAULT_BASH_TIMEOUT_MS),
    "BASH_MAX_TIMEOUT_MS": str(cap_ms),
}
```

- `context.request.deadline_seconds` は runner が worktree 準備後に渡す**残り時間**（interfaces.rst「deadline_seconds: 残り時間」、runner.py の Request 生成）。role の名目値 `role.deadline_seconds` ではなくこちらを使う。
- margin 120 秒は、長いコマンド終了後に CLI が最終 result を生成し、パイプのドレイン・停止猶予が収まる予約。固定値にする（比例配分は role が短いときに予約も縮み、result 生成の保護が薄くなるため）。
- 下限 600000 は現行挙動の維持。残り時間が短い role でも既定 10 分を割り込まず、runner の外側の期限が引き続き優先する（期限・停止確認は変更しない）。
- 既定 timeout は 600000 のまま。上限だけを広げるので、短いコマンドの挙動は変わらない。
- プロンプトの末尾（result_shape の行の後）に 1 行を足す: 既定は 10 分で timeout すること、それより長いコマンドには計算した上限 `cap_ms` までの明示 timeout を渡せること。CLI の Bash tool schema は max 600000 と書くため、実上限を伝えないと担当が長い timeout を要求せず、修正が実効にならない。文言は英語 1 行（既存のプロンプト行と同じ言語）。

代表的な値（残り時間が名目値と同じ場合）:

| role / 残り時間 | BASH_MAX_TIMEOUT_MS |
| --- | --- |
| implement 5400 秒 | 5280000（88 分） |
| inspect / self-review 2700 秒 | 2580000（43 分） |
| fix-check 短縮 1800 秒 | 1680000（28 分） |
| 720 秒（境界） | 600000 |
| 60 秒（短い role） | 600000（下限） |

実測 833.97 秒の全体検証は、最短の fix-check 短縮（1800 秒）でも導出上限 1680000ms に収まる。

## 受け入れ基準

- 動作環境: Dev Container の uv / Python、非対話 agent-runner の claude-code adapter。導入済み Claude Code CLI 2.1.322（timeout 計算のプローブはこの版で取り直す）。
- 実入力: `request.deadline_seconds` = 5400 / 2700 / 1800 / 720 / 60 秒。日本語・改行を含む prompt（例「確認する\n結果を返す」）で argv・stdin の既存仕様を保つ。
- 防御範囲: runner の当該 CLI 子プロセスの env だけに適用する。親環境・対話設定・共有設定は書き換えない。対象外の反例: 対話の claude（env 変更なし）、他 runtime の adapter（変更なし）、親環境の `BASH_MAX_TIMEOUT_MS`（allowlist に無く継承されない）、個人設定の短い期限（外側の runner 期限が優先）。
- 条件:
  1. 背景化無効のまま、既定 10 分を超え role の残り期限内に収まる正常な検証を完走できる上限になること（現行最短 1800 秒で導出上限 1680000ms > 実測 833.97 秒）。既定 600000 と背景化無効は維持。
  2. 上限は `max(600000, int((残り秒数 - 120) * 1000))` であること。残り時間が 720 秒以上のときは残り時間から 120 秒の予約を引いた値を超えず、常に下限 600000 を下回らない（短い role では下限が優先し、runner の外側の期限が引き続き優先する）。runner の期限・停止確認は変更しない。
  3. `_classify` の最後の result・後続イベント・permission_denials の判定を緩めない（差分が prepare とテストに限定され、既存分類の回帰が通ること）。
  4. 短い通常コマンドと、既定上限を超えるが role 期限内の長いコマンドを対照にして確認すること。fake/一時プローブを使い、有料モデルの反復は行わない。
  5. 親の対話セッション・共有設定を変更しないこと。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | adapter が残り時間から `BASH_MAX_TIMEOUT_MS` を導出して LaunchSpec.env に追加 | (a) `BASH_DEFAULT_TIMEOUT_MS` 自体を role 由来の上限へ引き上げ (b) 依頼側での検証分割 (c) 親環境の上限を agent.env で継承 | Issue の例示「role残り時間を踏まえた上限と担当へのtimeout指定」。(a) はハングした短いコマンドも長時間待ち、既定挙動を変える。(b) は README の標準入口がそのまま使えず、ビルド等もカバーしない。(c) は #365 所有の toml 編集が必要で、role 由来にならない | 通常の設計判断の委任 |
| D2 | `max(600000, int((request.deadline_seconds - 120) * 1000))` | margin 60/300 秒・比例配分、role.deadline_seconds（名目値）使用、下限なし | request.deadline_seconds は文書化された残り時間で、worktree 準備の消費を反映する。120 秒は最終 result 生成・ドレイン・停止猶予の予約として十分で、比例配分より短い role でも保護が薄くならない。下限は現行挙動の維持 | 通常の設計判断の委任 |
| D3 | プロンプトに実上限を伝える 1 行を追加 | 案内なし（env だけ） | 既定が 10 分のままなので、担当が明示 timeout を要求しないと修正が実効にならない。CLI の tool schema は max 600000 と書くため、実上限の周知が必要 | 通常の設計判断の委任 |
| D4 | `_classify`・runner・process・toml・runtime 文書・対話設定は不変更 | 分類の緩和・期限の延長 | Issue の受け入れ条件と #365 の所有。安全境界の維持 | Issue の明示条件 |
| D5 | 上限計算のパラメータ化テスト 1 件（S）。env 配送・分類の既存テストは変更しない | 固定値の照合テスト（F）、配送テストの追加（D） | 誤った上限はエラーにならず検証の打ち切り・未検証の成果・有料実行枠の損失につながる（S）。入力→出力の単体テストなので F ではない。配送は `test_workflow_preserves_literal_environment` がガード済みで、同じ守りの重複（D）を避ける | AGENTS.md のテスト採用基準 |
| D6 | Plan の Task を runner の `pi_alibaba_qwen4-max_max` に 1 件ずつ依頼（SDD 形） | self 実装 | `implement_task.py check`: self=false、agents=[pi_alibaba_qwen4-max_max]、fallback=[]（明示 --implement、個人設定に fallback なし） | 利用者の --implement |
| D7 | ループ最大 3 サイクル、inspect=pi_alibaba_qwen4-max_max,claude-code_sonnet_xhigh、implement=pi_alibaba_qwen4-max_max | ループなし | --merge 明示。3 は既定の適用。self-review/fix-check は既定 self。check-options 成功（template は雛形、config は個人設定だが上書きなし） | 利用者の --merge・--assign |
| D8 | main 前進は merge で追随し再検証して継続 | 直ちに停止 / 捕捉 SHA の黙った差し替え / rebase | 利用者の明示指示と #363 D7 の前例。旧 base JSON・旧/新 SHA・差分・再検証を記録する。force push しない | 競合が所有や仕様の意味を変える場合は停止。finalize の guard は緩めない |
| D9 | runner 起動時に `MAAS_ANTHROPIC_TOKEN="$ANTHROPIC_AUTH_TOKEN"` をワンショット付与 | env ファイルへの書き込み・共有設定の変更 | 利用者の明示指示。piaq の allowlist は MAAS_ANTHROPIC_TOKEN で、with_keys.py は既存値を上書きしない。値をファイル・ログに残さない | 利用者の追加指示。トークン値の外部送信は runner の allowlist 経由のみ |
| D10 | 検証は対象テスト + 一時プローブ（native 計算・fake CLI 対照）+ README の 3 入口 | 実 CLI・有料モデルでの 10 分 timeout 再現 | Issue が fake/一時プローブを指定。プローブは導入済み版に依存するためコミットせず SESSION に記録する。全体検証（約 14 分）は controller がバックグラウンドで実行する（controller の対話 Bash は背景化で 10 分上限の対象外） | Issue の受け入れ条件。実機確認をマージ後の必須条件にしない |
| D11 | 停止条件該当事象は診断 → 最適な回復 → 記録 → 続行 | 停止して報告 / 失敗を成功扱い | 利用者の明示指示（2026-11-12）。Spec レビュー review-1 は controller の並行書き込みによる outside_changes で受け取り拒否されたため、並行書き込みなしで再実行する | 検証結果の捏造・安全境界の違反は許可されない。失敗は報告する |

## 検証と限界

- ベースライン: worktree `ae4b6e71` で `uv run --locked pytest tools/agent_runner/tests -q` → 289 passed（30.54s）、exit 0。ログ: `/workspaces/reso-world/tmp/agents/issue-382.mbplkg1i/baseline-pytest.log`。
- 実装 Task: 対象テスト（`tools/agent_runner/tests`）を同期実行。
- controller の検証:
  - native timeout 計算プローブ: 導入済み CLI 2.1.322 から timeout 計算関数を抽出し、隔離 Node vm で現行 env（default/max とも 600000）と新 env（default 600000・max 導出値）を対照。実測 833.97 秒との大小を確認する。CLI・モデル・外部サービスは起動しない。
  - fake CLI 対照プローブ: 偽の `claude` が受け取った env を記録し、公式の clamp 計算を論理時計で模擬する。短いコマンド（既定内）は旧 env・新 env とも成功、長いコマンド（834 秒相当）は旧 env で timeout・新 env で成功、を実 runner 経由で確認する。実時間の 14 分待ちはしない。
  - README の 3 入口: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`（約 14 分、バックグラウンド実行と監視）。
- fake/プローブは実 CLI の実測ではない。実機確認をマージ後の必須条件にはしない。有料モデルの再現実験は行わない（workflow のための担当起動はこれと区別する）。
- 手元の証拠（Issue 起票時の調査）: `/workspaces/reso-world/tmp/agents/pr379-followup.cu3tfxae/timeout-probe-results.json`・`probe-timeout.py`・`native-timeout-arithmetic.cjs`・`native-timeout-source.txt`・`timeout-official-docs.txt`。元の検証: `/workspaces/reso-world/tmp/agents/issue-363.1jibklo0/verification.json`・`verify-3.log`（833.966 秒、exit 0）。

## レビュー記録

### 設計レビュー 1 回目（helper `review_design.py`、外部 runner）

- 担当: 明示 `--design-review pi_openai-codex_gpt6-sol_xhigh`。requested_agent / actual_agent とも `pi_openai-codex_gpt6-sol_xhigh`。identity: model `gpt-6.1-sol` / provider `openai-codex` / effort `xhigh`。fallback の使用なし（個人設定に fallback なし）。
- review_dir: `/workspaces/reso-world/tmp/agents/issue-382.mbplkg1i/2026-11-12-issue-382-claude-bash-timeout-cap-design.design-review/review-1`
- review_id: `9ab14dd9e3994466ac688b6b3ce3c44c`。reviewed spec sha256: `7b15c03aebd9be979963cad1458ceffd2eb37cf506da9244a0441ae24049e5cc`。
- 結果: status completed / verdict **sound** / concerns 0 件 / questions_for_user 0 件 / incomplete 0 件。elapsed_seconds 73.78。
- 評価の要点: 残り時間から子プロセスの Bash 上限だけを導出する方式は Issue の原因と LaunchSpec.env の配送に適合。既定 10 分・背景化無効・runner の期限と停止確認・厳格な結果判定を維持でき、変更は局所的で戻しやすい。代替案比較と fake 対照の検証方針も妥当。
- 採否: 指摘 0 件のため採用・不採用の判断なし。
- outside_changes: なし。unprotected_changes: `/tmp/pr-review-376-*`・`/tmp/review-fix-planning.*` の使い捨て worktree（他セッションの prunable 登録）と `.worktrees/issue-355-herdr-merge` の観測。本 run の変更ではなく、受け取りは止めない（報告のみ）。

### Spec レビュー 1 回目（helper `review_spec.py`、外部 runner）— 受け取り拒否・再実行

- 担当: 明示 `--spec-review pi_alibaba_qwen4-max_max`。requested_agent / actual_agent とも同じ。identity: model `qwen4-max-preview` / provider `alibaba` / effort `max`。fallback なし。
- review_dir: `/workspaces/reso-world/tmp/agents/issue-382.mbplkg1i/2026-11-12-issue-382-claude-bash-timeout-cap-design.spec-review/review-1`
- review_id: `9e2689a3f3ab4c1f9d3d61398ee4cdb6`。reviewed spec sha256: `eac28bfcb5b2a9d0d203a6a3c14a0793c0d53491a9e4e7bd1158a6cee7153d60`。
- 結果: runner の batch は success（exit 0・stop_confirmed true・434.98 秒）。結果 JSON は完全に出力され findings 2 件を記録したが、helper は `outside_changes: CODE_ROOT` を理由に受け取りを拒否（state: failed）。原因は controller がレビュー実行中に Plan 草案を CODE_ROOT に書いたこと（監査対象の保護 checkout の内容変化）。
- 扱い: 失敗レビューの findings は採用しない。利用者の停止条件例外指示（D11）により、並行書き込みなしで review-2 として再実行する。cleanup 済み（停止確認済み・retained なし）。ledger は保存。

### Spec レビュー 2 回目（review-2、helper `review_spec.py`、外部 runner）

- 担当: 明示 `--spec-review pi_alibaba_qwen4-max_max`（review-1 と同じ）。requested_agent / actual_agent とも同じ。identity: model `qwen4-max-preview` / provider `alibaba` / effort `max`。fallback の使用なし。
- review_dir: `/workspaces/reso-world/tmp/agents/issue-382.mbplkg1i/2026-11-12-issue-382-claude-bash-timeout-cap-design.spec-review/review-2`
- review_id: `44dbbbcd2d934a3ea84d2508c89c5621`。reviewed spec sha256: `a3a462b8ad713f459eefe74d192d961af4e18dfbbdcb4b18c021a759cb2c78cb`。round 1（失敗した review-1 は回数に数えない）。
- 結果: status completed / findings **1 件（S1, minor）** / incomplete 0 件。elapsed_seconds 514.70。outside_changes: なし。
- unprotected_changes: `/tmp/pr-review-376-*`・`/tmp/review-fix-planning.*`（他セッションの prunable 登録）、`.worktrees/issue-355-herdr-merge`・`.worktrees/issue-396-flaky-deadline-test`・issue-396 の review-runner worktree（他セッションの作業）。本 run の変更ではなく、報告のみ。
- 採否:
  - **S1（採用・minor）**: 受け入れ基準の条件 2 が、720 秒未満の role で「残り − 120 秒以下」と「下限 600000 以上」を同時に要求する文面になっており、設計式 `max(600000, ...)` の「下限優先」挙動と文字どおりには矛盾する（60 秒 role の正しい実装を条件 2 違反と誤指摘する恐れ）。→ 条件 2 を設計式と一致する文面に修正（Spec と Plan の両方）。実装内容（式・定数・案内行）は変わらない。

## PR #411 サイクル 1 の判断・実行結果

planner: qwen4-max-preview（runtime: claude-code、controller）。対象 HEAD `a0469a787e3671b4571b7e4e1a117a1d39daa383`。サイクル 1。

| レビューファイル | モデル | ランタイム | レビュー HEAD | 再実行 | 推奨 |
| --- | --- | --- | --- | --- | --- |
| qwen4-max-preview.md | qwen4-max-preview | pi | a0469a787e36 | true | Approve |
| claude-sonnet-5-5.md | claude-sonnet-5-5 | claude-code | a0469a787e36 | true | Approve |

- 指摘: 0 件（両レビュアー、active 0）。分類: 解消済み 0 / 対応する 0 / 対応しない 0。**結論 2（修正不要）**。コード修正・自己レビューの起動は 0 回。
- 両レビュアーが独立に prepare の境界値プローブ（5400/2700/1800/小数/720/60 秒ほか）・導入済み CLI 2.1.322 の kK/kX 計算照合・`tools/agent_runner/tests`（295 passed）を実行し、受け入れ条件 5 件すべてを確認。
- 確認済み一覧: `reviews/usaturn/create-reso-world/#411-fix-issue-382-claude-bash-timeout-cap/verified/a0469a787e36.json`（0 件・coverage closed。sonnet の未実施 3 件は controller の実行証拠で閉じ、有料 CLI 再現は Issue #382 と D10 で対象外）。
- 検証（HEAD a0469a78・clean）: 対象テスト 295 passed / 全体 pytest 1454 passed（836.13s）/ run-tests.bash 27 PASS / check-layout.sh PASS、すべて exit 0。
- base 前進: 検証中に origin/main が ae4b6e71 → 7e2d1a89 へ前進（PR #410・devin adapter・本 PR と重複なし）。利用者指示（D8）と結論 2 の手順 2 により、head に新 base を merge した一時ツリー `43ea90d1` で再検証: 対象テスト 303 passed / 全体 pytest 1462 passed（801.43s）/ run-tests.bash 27 PASS / check-layout.sh PASS、すべて exit 0。検証の記録の base は `7e2d1a89`。一時ツリーは検証後に破棄（push せず）。
- 判断の記録: SESSION の round.json（review-records/v2・no_fix_needed）。工程の詳細は SESSION ディレクトリと PR の状況コメントに記録する。push・マージ・Issue 更新の結果はこの Spec に先取りせず、状況コメントと完了報告に記録する。