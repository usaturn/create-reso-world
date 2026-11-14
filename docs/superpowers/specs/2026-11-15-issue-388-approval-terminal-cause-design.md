# Issue #388: 承認拒否がある試行でも、試行を終わらせた別の失敗の原因を診断に残す

## 管理・実行許可

- 状態: `draft`（承認していない。下の実行指示は実行許可であり、内容の承認ではない）
- Issue: https://github.com/usaturn/create-reso-world/issues/388
- 利用者の指示（`/issue-to-pr` の引数）: `#388 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review claude-code_sonnet_xhigh --implement claude-code_sonnet_xhigh --assign implement=claude-code_sonnet_xhigh --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,pi_openai-codex_gpt6-sol_xhigh`
- 許可された範囲: issue-to-pr の手順に従い、通常の設計判断を推奨案で決め、検証・commit・push・PR 作成まで進め、`--merge` により PR 修正ループ（pr-review-fix-loop）の `finalize.py` が修正不要と確かめたときだけマージする
- base: `usaturn/create-reso-world` の `main`、`273ace19215430fa05042a512d63dc19e4e3a058`

## 目的

Claude Code の試行に構造化された承認拒否（`permission_denials`）があり、同じ試行が利用上限・接続失敗など別の原因で終わったとき、ログ回収後の診断（`cycle-<n>/diagnostics/<request_id>.json`）から、承認拒否の根拠と、試行を終わらせた失敗の原因の両方を区別できるようにする。利用上限なら時間・残高、接続障害なら通信の回復、承認拒否なら拒否された操作の見直しと、取る手が違うためである。

## 現状（base `273ace19` で観測）

- `diagnose_attempt`（`.agents/skills/pr-review-fix-loop/scripts/loop.py`）は、`classify_cause` の結果が `authentication` 以外なら、承認根拠（`approval_evidence`）があるだけで `cause` を `approval` に上書きする
- Issue の再現（`b0deb7f8`）では、429 と接続拒否を terminal result の `result` 本文にだけ書いていた。その後にマージした #356（PR #439）は「`result`・`content` は `type=result` かつ `is_error=true` でもモデルの最終応答と区別できないので分類に使わない」と決めた。そのため今の base では、Issue の入力のままだと denial の無い対照も `unknown` になり、denial の有無で差が出ない（この run の間だけの一時的な観測。`tmp/agents/issue-388.zzoas0k7/probe-base.*`。Issue の `probe-e2e.py` を今の base で実行: denial+429・denial+接続は `approval`、denial なしの 429 は `unknown`、denial+成功は `approval`）
- CLI が付ける失敗の欄（assistant イベントの `error` 欄の `rate_limit`、stderr の `Error: connect ECONNREFUSED ...`）で同じ失敗を表すと、今の base でも本題の不具合が出る（この run の間だけの一時的な観測。`tmp/agents/issue-388.zzoas0k7/probe-cli.*`。入力は下の「受け入れ基準」の実入力の 4 組と同じ形で、利用上限は stdout の assistant イベント `{"type": "assistant", "error": "rate_limit", ...}` と失敗の terminal result、接続失敗は stderr の `Error: connect ECONNREFUSED 127.0.0.1:443` と失敗の terminal result、どちらも終了コード 1。観測: denial+429・denial+接続は `approval`、denial なしの 429 は `rate_limit`、denial+成功は `approval`。4 件とも `unavailable={}`）

## 設計

`diagnose_attempt` の上書きの条件を次に変える。承認根拠（`approval_evidence`）がある試行で、`classify_cause` の結果を `cause` に残すのは、次のどちらかのときだけである。それ以外は今までどおり `cause` を `approval` にする。

1. 結果が `authentication`（既存の認証優先。terminal の成否によらない。今と同じ）
2. 試行が失敗で終わり、かつ結果が既知の原因（`rate_limit`・`sandbox`・`timeout`・`connection`・`runtime_error`・`approval`）。「失敗で終わった」は、承認根拠の `is_error` が true、`terminal_subtype` が `success` でない、終了コードが 0 でない（null を含む）のどれかに当たること

- 2 の条件により、成功 terminal・終了コード 0 で承認拒否だけで終わった試行は、stderr の雑音や途中の回復済みエラーに上限・接続などの語があっても `approval` のままになる（別の原因を選ばない）
- `unknown`・`response_extraction`（原因を特定できなかった）は、試行の成否によらず `approval` にする
- 承認根拠は今までどおり `approval` 欄（`ApprovalDiagnostic`）に保存する。`state` は adapter と runner が決めた `awaiting_approval` のままで、拒否を成功にしない
- 診断の形（`AttemptDiagnostic`・`ApprovalDiagnostic`）とスキーマ名は変えない。新しい欄を足さない
- adapter（`tools/agent_runner/adapters/claude_code.py`）・runner は変えない。分類の文に使う欄（#356 が決めた CLI の失敗の欄だけ）も変えない

これで、回収後の診断から次のように読める。

| 入力 | `state` | `cause` | `approval` |
| --- | --- | --- | --- |
| denial ＋ CLI の利用上限（assistant の `error: rate_limit`） | `awaiting_approval` | `rate_limit` | 承認根拠が残る |
| denial ＋ CLI の接続失敗（stderr の `Error: connect ECONNREFUSED`） | `awaiting_approval` | `connection` | 承認根拠が残る |
| denial なし ＋ 同じ利用上限 | `response_failed` | `rate_limit`（今と同じ） | なし |
| denial ＋ 成功 terminal・終了コード 0 | `awaiting_approval` | `approval`（今と同じ） | 承認根拠が残る |
| denial ＋ 成功 terminal・終了コード 0 ＋ stderr に `Error: connect ECONNREFUSED`（雑音） | `awaiting_approval` | `approval`（今と同じ。試行は失敗で終わっていない） | 承認根拠が残る |
| denial ＋ 認証の失敗の文（既存のテスト） | `awaiting_approval` | `authentication`（今と同じ） | 承認根拠が残る |
| denial ＋ `result` 本文だけに書いた失敗 | `awaiting_approval` | `approval`（今と同じ。本文は #356 により分類しない） | 承認根拠が残る |

`records.md` の 4.1 節（診断の記録）と `loop.py` の説明を、新しい規則と矛盾しないように直す。対象は次のとおり。

- `attempts[]` の欄の列挙に `approval` を足し、子キー（`source`・`terminal_subtype`・`is_error`・`permission_denials`・`denial_count`・`diagnostic_sources`）の意味と、Claude Code の承認待ちの試行だけに付き、拒否の中身・`tool_input`・本文は保存しないことを書く
- `cause` の段落の冒頭（「試行を終わらせた失敗の報告だけから決める」）に、承認根拠がある試行の扱い（上の 1・2 の規則）を足す
- `cause` の表の `approval` の行、`unknown`・`response_extraction` の行を、承認根拠がある試行では `approval` になることと矛盾しない説明にする
- 限定（利用者の決定）: 承認根拠と別の原因を併存して残すのは、CLI の失敗の欄（assistant の `error`、stderr など分類の文に使う欄）に根拠がある場合だけで、terminal result の `result` 本文だけに書かれた失敗は #356 により分類せず、承認根拠があれば `approval` のままになることを書く
- `loop.py` の `diagnose_attempt` の docstring と上書きのコメント、`ApprovalDiagnostic` の docstring を同じ意味にする

PR 本文には、Issue の受け入れ条件の字句（`result` 本文だけの 429・接続拒否）との差と、それが利用者の決定による限定であること、残る限定を書く。

## 受け入れ基準

- 動作環境: 隔離した worktree、テストごとの一時 HOME（`conftest.py` の `env` fixture）、偽の CLI（`ClaudeNDJSONReviewers`）と偽の GitHub。実モデル・有料 API・実資格情報は使わない。本物の Claude adapter の `collect` → runner の結果の保存 → `loop.review`／`keep_diagnostic` → 生ログの回収までを通す
- 実入力:
  - denial は `{"tool_name": "Bash", "tool_input": {"command": "fixture-<uuid>"}}` の 1 件（`tool_input` は fixture の値だけ）
  - 利用上限: assistant イベントに `error: "rate_limit"`、本文（`message.content`）と terminal result の `result` に複数行・非 ASCII の文（例: `API Error: 429 rate limit exceeded\n利用上限に達しました`）。terminal は `subtype: error_during_execution`、`is_error: true`、終了コード 1
  - 接続失敗: stderr に `Error: connect ECONNREFUSED 127.0.0.1:443`、terminal result の `result` に複数行・非 ASCII の文。terminal は失敗、終了コード 1
  - 対照: 同じ利用上限で denial が空の入力、denial があり成功 terminal・終了コード 0 の入力、その成功 terminal の入力に stderr の `Error: connect ECONNREFUSED 127.0.0.1:443` を足した入力（雑音）
- 合格条件:
  - denial＋利用上限で `cause` が `rate_limit`、denial＋接続失敗で `connection`。どちらも `approval` 欄に `source: permission_denials`・`denial_count: 1` が残り、`state` は `awaiting_approval`
  - denial なしの利用上限は `response_failed`／`rate_limit`／`approval` なし（今と同じ）
  - denial＋成功 terminal は `awaiting_approval`／`approval`／承認根拠あり（今と同じ）。stderr の雑音を足しても `approval`
  - 各ケースとも、拒否側のレビュアーは却下（`rejected_stage: runner`）され成功にならない、`unavailable == {}`、runner の出力領域は回収済み（`removed`、パスが存在しない）、保存した記録に fixture の秘密値・本文の文が写らない
- 防御範囲（対象）: 承認拒否がある試行の原因の分類と承認根拠の保存。認証優先、停止の確認、`sensitive_paths`、出力の外のログを読まないこと、保存先の境界は今のまま
- 防御範囲（対象にしない反例）: `tool_input`・コマンド全文・任意のメッセージ・実資格情報・生ログを追加保存しない。terminal result の `result` 本文を分類に使わない（#356）。denial を成功として扱わない。adapter の `awaiting_approval` の判定を変えない

## テスト

「テストの採用基準」の S（別の原因を選ぶ・情報を失う、失敗を成功と報告する）に当たる。

- `test_loop_diagnostics.py` に、本物の adapter → runner → 保存 → 回収の流れで、denial＋利用上限・denial＋接続失敗・denial なしの利用上限・denial＋成功 terminal＋stderr の雑音の 4 ケースを確かめる parametrize のテストを 1 つ足す。実装の前に RED を確かめる（denial の失敗 2 ケースが `approval` で落ちる。雑音のケースは今の実装でも通るが、2 の条件を外した実装で落ちる守りとして置く）
- 利用上限と接続失敗を両方残す理由: 分類の入力の経路が違う（利用上限は stdout の assistant の `error` 欄、接続失敗は stderr）うえ、Issue の受け入れ条件が両方を要求する
- 4 つ目の対照（denial＋成功 terminal）は、既存の `test_claude_approval_evidence_survives_cleanup` の `terminal-denial` が同じ入力を同じ流れで確かめているので、新しいケースを足さず（D）、そのテストに `unavailable == {}` の確認だけを足す
- 既存の認証優先（`test_claude_authentication_priority_keeps_approval_evidence`）と停止確認・`sensitive_paths` のテストは残す
- 文書の文言のテストは書かない（F）

## 決定記録

| # | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| 1 | 単一の `cause` の優先順を変える（試行が失敗で終わり原因を特定できたときはその原因、認証は今どおり常に優先、それ以外は `approval`） | (b) `cause` は `approval` のまま、`terminal_cause` のような欄を足す。(c) adapter が terminal result の本文を分類して payload に入れる | `cause` は records.md で「試行を終わらせた失敗の原因」と定義され、`approval` 欄が承認根拠を別に保存しているので、優先順の変更だけで両方が残る。既存の認証優先も同じ規則の特別な場合になる。(b) は同じ情報を 2 か所に持ち、診断の形を変える。(c) は #356 の「本文を分類しない」に反する | Issue の「エージェントに任せる事項」（単一 cause の優先順変更か別フィールドの併存かの設計）による委任 |
| 2 | 試験の入力は、CLI が付ける失敗の欄（assistant の `error`、stderr）で 429・接続失敗を表し、`result` 本文にも複数行・非 ASCII の文を置く | Issue の再現どおり `result` 本文だけに書く | Issue の起票後にマージした #356 が `result` 本文の分類を禁じたため、本文だけでは denial の有無によらず `unknown` になり、本題（denial による上書き）を確かめられない。Issue の目的（回収後に原因を区別できる）と対照（denial なしは今と同じ）は保たれ、`result` 本文の扱いは #356 の決定に従う。AGENTS.md の「RED で前提が異なると判明した場合は、仕様の意味を保つ最小修正を記録して継続する」に当たると判断した | 設計レビュー D1（blocking・ask_user）を受けて、利用者が 2026-11-15 に決定: 「推奨案で進めてください。今後、止めることは許しません。PRを出してマージをするところまで実行してください。」。対象は CLI の失敗の欄（assistant の `error`、stderr など #356 が分類に使う欄）に根拠がある試行に限る。`result` 本文だけに書いた失敗は #356 の本文非分類に従い、denial の有無によらず識別しない（Issue の受け入れ対象の限定として利用者が承認） |
| 3 | 承認で置き換える `cause` は `unknown` と `response_extraction` だけ | `unknown` だけ | `response_extraction` は「失敗の報告が無いのに結果を得られなかった」の推測で、承認待ちの試行では承認拒否のほうが確かな説明になる。今の実装では `awaiting_approval` は `_EXTRACTION_STATES` に無く出ないが、条件として明示する | 委任 |
| 4 | 新しいテストは 4 ケース（失敗 3 ＋成功 terminal の雑音 1）の parametrize 1 つ、denial＋成功 terminal（雑音なし）は既存テストに確認を 1 行足す | 雑音なしの成功 terminal も新しいテストにする | 雑音なしの成功 terminal は既存テストと同じ入力・同じ流れで、「テストの採用基準」の D に当たる | 委任 |
| 5 | records.md 4.1 の `attempts[]` に `approval` を足し、`cause` との関係を書く | 列挙漏れを直さない | Issue の完了条件（採用した設計と一致する形で説明する）。`approval` 欄を書かずに関係は説明できない | Issue の完了条件 |
| 7 | 原因を残すのは、認証か、試行が失敗で終わったとき（`is_error` true・`terminal_subtype` が success でない・終了コードが 0 でない）だけ | (b) ログのどこかにある失敗の報告で決め、`cause` の定義を「報告された失敗」に変える | Spec レビュー S1。`cause` は「試行を終わらせた失敗の原因」であり、承認拒否だけで成功 terminal に終わった試行で雑音の語を原因にすると別の原因を選ぶ（S）。認証は既存のテストと復旧の必要から今どおり常に優先する | 委任（Spec レビューの採否） |
| 6 | #357・#443 とは `loop.py` の `diagnose_attempt` と records.md 4.1 の範囲だけを変えて重ならないようにする | — | Issue のコメント（#388 → #357 の順） | #357 の範囲・ボードの依存は変えない |

### 実行の設定（2 章の検査結果）

- 実装の担当: `--implement claude-code_sonnet_xhigh`（利用者の指定）。`fallback` は個人設定のもの（空）。`self` は false なので、各 Task を `implement_task.py` で runner の担当に依頼する
- 設計レビュー: `--design-review pi_openai-codex_gpt6-sol_xhigh`（利用者の指定）、`fallback` 空
- Spec レビュー: `--spec-review claude-code_sonnet_xhigh`（利用者の指定）、`fallback` 空。builder check は行わない
- PR 修正ループ（`check-options`）: `max_cycles` 3（既定の適用）、`assign.implement` = `claude-code_sonnet_xhigh`、`assign.inspect` = `devin_swe2_max`・`pi_opencode-go_deepseek4-flash_max`・`pi_openai-codex_gpt6-sol_xhigh`（利用者の指定）。`self-review`・`fix-check` は `self`（既定の適用）。`template` は `.devcontainer/agent-runner.toml`（既定）

### 設計レビューの記録

- 担当: `pi_openai-codex_gpt6-sol_xhigh`（利用者の明示、`fallback` 空）。`actual_agent` 同じ、`identity` は gpt-6.1-sol / openai-codex / xhigh。1 回、`elapsed_seconds` 約 151
- `review_dir`: `/workspaces/reso-world/tmp/agents/issue-388.zzoas0k7/2026-11-15-issue-388-approval-terminal-cause-design.design-review/review-1`、`review_id` `029a5a28b3f949a78cd25f09f375daa5`、reviewed の Spec SHA-256 `e623233c4701ca41f731ff8ab87a7485635c3ece0afce59014edea28c270a622`
- verdict `concerns`。D1（決定記録 2 の読み替えが Issue の対応範囲を狭める、blocking・ask_user）は `needs_judgment` として記録し、helper の `next: stop` で一度止めた。その後の利用者の決定で、決定記録 2 のとおり対象を限定して続ける
- `outside_changes` なし。`unprotected_changes` は別の作業の worktree 8 件（この run の対象外）

### Spec レビューの記録

- 担当: `claude-code_sonnet_xhigh`（利用者の明示、`fallback` 空）。`actual_agent` 同じ、`identity` は claude-sonnet-5-5（CLI 2.1.325）。1 回目、`elapsed_seconds` 約 220
- `review_dir`: `tmp/agents/issue-388.zzoas0k7/2026-11-15-issue-388-approval-terminal-cause-design.spec-review/review-1`、`review_id` `3708889b007f42098709046b7aee4f4c`、reviewed の Spec SHA-256 `247a5f5881a9a0980770bfeafd78c1fd4dd4d241438c416c67d743d90b206184`
- 指摘 5 件（S1 important、S2〜S5 minor）をすべて採用し、本文に反映した: S1 は設計の 2 の条件と雑音のケース、S2・S3 は records.md と loop.py の説明の対象と PR 本文の記載、S4 はテストの理由、S5 は一時パスの扱いと fixture の形
- `outside_changes` なし。`unprotected_changes` は別の作業の worktree 7 件（この run の対象外）

## 対象外

- 承認拒否を成功として扱うこと、認証優先の解除
- `tool_input`・コマンド全文・任意メッセージ・実資格情報・生ログの追加保存
- terminal result の `result` 本文を分類に戻すこと（#356 の決定の変更）。`result` 本文だけに書いた失敗の識別（利用者の決定で対象外）
- adapter・runner の状態の判定の変更
- 過去の本番試行でこの組合せが起きた、または特定の頻度で起きるという断定
- #357 の収集の保存点・#443 の範囲の変更
