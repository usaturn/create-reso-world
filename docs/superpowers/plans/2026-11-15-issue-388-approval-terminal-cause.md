# Issue #388 実装計画: 承認拒否がある試行でも別の終端失敗原因を診断に残す

- 状態: `draft`（issue-to-pr の実行指示は実行許可であり、内容の承認ではない）
- Spec: `docs/superpowers/specs/2026-11-15-issue-388-approval-terminal-cause-design.md`
- Issue: https://github.com/usaturn/create-reso-world/issues/388
- base: `main` `273ace19215430fa05042a512d63dc19e4e3a058`

## 実行方式

`--implement claude-code_sonnet_xhigh` の指定で `implement_task.py check` の `self` が false のため、各 Task を `implement_task.py run` で runner の担当（claude-code_sonnet_xhigh）に 1 つずつ依頼する（issue-to-pr 4 章「Task の実装を runner の担当に依頼する」）。Task は 1 つ（コード・テスト・文書が同じ判定の一連の変更で、分けると同じファイルの逐次変更になる）。Task のレビューは司令塔（このセッション）がサブエージェントで行う。`--merge` が適用されるので、最終のブランチ全体レビューは PR 修正ループの 1 サイクル目で代える。

## Task 1: 承認根拠で既知の原因を上書きしない

担当ファイル:

- `.agents/skills/pr-review-fix-loop/scripts/loop.py`（`diagnose_attempt` とその docstring だけ）
- `.agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py`
- `.agents/skills/pr-review-fix-loop/references/records.md`（4.1 節だけ）

手順:

1. `test_loop_diagnostics.py` に、本物の Claude adapter（`ClaudeNDJSONReviewers`）→ runner → `loop.review`／`keep_diagnostic` → 回収の流れで、次の 5 ケースを parametrize で確かめるテストを足す（既存の `test_claude_approval_evidence_survives_cleanup` と同じ組み立て方）
   - `denial-rate-limit`: stdout に assistant イベント（`error: "rate_limit"`、`message.content` に `API Error: 429 rate limit exceeded\n利用上限に達しました` のような複数行・非 ASCII の文）と、terminal result（`subtype: error_during_execution`、`is_error: true`、`result` に複数行・非 ASCII の文、`permission_denials` に `{"tool_name": "Bash", "tool_input": {"command": <fixture の秘密値>}}` を 1 件）。終了コード 1。期待: `awaiting_approval`／`rate_limit`／`approval.source == "permission_denials"`・`denial_count == 1`
   - `denial-connection`: stdout は同じ形の terminal result（denial 1 件）だけ、stderr に `Error: connect ECONNREFUSED 127.0.0.1:443`。終了コード 1。期待: `awaiting_approval`／`connection`／同じ承認根拠
   - `no-denial-rate-limit`: `denial-rate-limit` と同じで `permission_denials` だけ空。期待: `response_failed`／`rate_limit`／`approval is None`
   - `denial-success-noise`: terminal result は成功（`subtype: success`、`is_error: false`、`result: '{"status": "success"}'`、denial 1 件）、stderr に `Error: connect ECONNREFUSED 127.0.0.1:443`、終了コード 0。期待: `awaiting_approval`／`approval`／同じ承認根拠（`terminal_subtype == "success"`、`is_error is False`）、`exit_code == 0`
   - `denial-result-only`: terminal result は失敗（`subtype: error_during_execution`、`is_error: true`、`result` に `API Error: 429 rate limit exceeded\n利用上限に達しました`、denial 1 件）だけで、assistant の `error` 欄・stderr は空、終了コード 1。期待: `awaiting_approval`／`approval`／同じ承認根拠（Issue の再現入力の形。利用者の決定による限定の回帰検査）
   - 共通の確認: 通常の偽レビュアー（alpha）は受け付け、beta は `rejected_stage == "runner"`・`diagnostic_error is None`。ケースごとの `exit_code`、`stop_confirmed`、`unavailable == {}`。`load_run(run_dir).resources` がすべて `removed` でパスが存在しない。`saved_text(env.review_dir)` に秘密値と、`result`・本文に置いた文が含まれない
2. 既存の `test_claude_approval_evidence_survives_cleanup` に `assert attempt.unavailable == {}` を 1 行足す（4 つ目の対照: denial＋成功 terminal・終了コード 0 は `approval` のまま）
3. RED を確かめる: `denial-rate-limit`・`denial-connection` が `cause == "approval"` で失敗し、`no-denial-rate-limit`・`denial-success-noise`・`denial-result-only` は通る
4. `loop.py` の `diagnose_attempt` を Spec の「設計」の規則に変える。承認根拠があるとき、`cause` を残すのは (1) `authentication`、または (2) 試行が失敗で終わり（`approval.is_error is True`、`approval.terminal_subtype != "success"`、`attempt.exit_code != 0`（None を含む）のどれか）かつ `cause` が `unknown`・`response_extraction` 以外のときだけで、それ以外は `approval` にする。`diagnose_attempt` の docstring・上書きのコメント・`ApprovalDiagnostic` の docstring を同じ意味に直す
5. GREEN を確かめる
6. `records.md` 4.1 節を Spec の「設計」の records.md の対象の列挙どおりに直す（`cause` の段落の文面は Spec の S7 の指定どおり、実装が保証する範囲に合わせる）: `attempts[]` の列挙に `approval`（子キーの意味、Claude Code の承認待ちの試行だけ、拒否の中身・`tool_input`・本文は保存しない、それ以外は null）、`cause` の段落の冒頭に承認根拠がある試行の規則、表の `approval`・`unknown`・`response_extraction` の行、CLI の失敗の欄に根拠がある場合だけ併存し `result` 本文だけの失敗は `approval` のままという限定
7. commit（メッセージ: `fix: keep terminal failure cause alongside approval evidence (#388)`）

テスト: 要る。S（別の原因を選ぶ・回収後に情報を失う、拒否を成功にする）の再発防止。新しいテスト 1 つ（5 ケース）と既存テストへの 1 行。雑音なしの成功 terminal の対照は既存テストと同じ入力・流れなので D として新しいケースにしない。利用上限と接続失敗は分類の入力の経路が違い、Issue が両方を要求するので両方残す。文書の文言のテストは書かない（F）。

検証:

- 文書・コメントの代わりの検証: `git diff` で Spec の S8 の変更対象（`approval` の子キーの列挙、`cause` の段落の冒頭、表の `approval`・`unknown`・`response_extraction` の行、限定の説明、docstring と上書きのコメント）を 1 つずつ確かめる
- worktree の root で `uv run --locked pytest .agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py -q`
- `uv run --locked pytest .agents/skills/pr-review-fix-loop/tests tools/agent_runner/tests -q`

## 受け入れ基準

（Spec の「受け入れ基準」と同じ本文。実装担当・レビュー担当の brief に写す）

- 動作環境: 隔離した worktree、テストごとの一時 HOME（`conftest.py` の `env` fixture）、偽の CLI（`ClaudeNDJSONReviewers`）と偽の GitHub。実モデル・有料 API・実資格情報は使わない。本物の Claude adapter の `collect` → runner の結果の保存 → `loop.review`／`keep_diagnostic` → 生ログの回収までを通す
- 実入力:
  - denial は `{"tool_name": "Bash", "tool_input": {"command": "fixture-<uuid>"}}` の 1 件（`tool_input` は fixture の値だけ）
  - 利用上限: assistant イベントに `error: "rate_limit"`、本文（`message.content`）と terminal result の `result` に複数行・非 ASCII の文（例: `API Error: 429 rate limit exceeded\n利用上限に達しました`）。terminal は `subtype: error_during_execution`、`is_error: true`、終了コード 1
  - 接続失敗: stderr に `Error: connect ECONNREFUSED 127.0.0.1:443`、terminal result の `result` に複数行・非 ASCII の文。terminal は失敗、終了コード 1
  - 対照: 失敗 terminal（`error_during_execution`、`is_error: true`、終了コード 1）の `result` 本文にだけ `API Error: 429 rate limit exceeded\n利用上限に達しました` を書き、assistant の `error` 欄・stderr は空で denial 1 件の入力（Issue の再現入力の形）、同じ利用上限で denial が空の入力、denial があり成功 terminal・終了コード 0 の入力、その成功 terminal の入力に stderr の `Error: connect ECONNREFUSED 127.0.0.1:443` を足した入力（雑音）
- 合格条件:
  - denial＋利用上限で `cause` が `rate_limit`、denial＋接続失敗で `connection`。どちらも `approval` 欄に `source: permission_denials`・`denial_count: 1` が残り、`state` は `awaiting_approval`
  - denial なしの利用上限は `response_failed`／`rate_limit`／`approval` なし（今と同じ）
  - denial＋失敗 terminal で `result` 本文だけに失敗の文があるときは `awaiting_approval`／`approval`／承認根拠あり（今と同じ。利用者の決定による限定）
  - denial＋成功 terminal は `awaiting_approval`／`approval`／承認根拠あり（今と同じ）。stderr の雑音を足しても `approval`
  - 各ケースとも、拒否側のレビュアーは却下（`rejected_stage: runner`）され成功にならない、`unavailable == {}`、runner の出力領域は回収済み（`removed`、パスが存在しない）、保存した記録に fixture の秘密値・本文の文が写らない
- 防御範囲（対象）: 承認拒否がある試行の原因の分類と承認根拠の保存。認証優先、停止の確認、`sensitive_paths`、出力の外のログを読まないこと、保存先の境界は今のまま
- 防御範囲（対象にしない反例）: `tool_input`・コマンド全文・任意のメッセージ・実資格情報・生ログを追加保存しない。terminal result の `result` 本文を分類に使わない（#356）。denial を成功として扱わない。adapter の `awaiting_approval` の判定を変えない

## 検証の入口（最終）

clean な HEAD で次を同期実行し、HEAD・argv・終了コード・ログを SESSION に記録する（`verify-cmds.json` に固定する）。

- `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`
- `bash .devcontainer/run-tests.bash`
- `bash scripts/check-layout.sh`
- `git diff --check 273ace19215430fa05042a512d63dc19e4e3a058...HEAD`
- `git diff 273ace19...HEAD --stat` で担当ファイルと Spec・Plan 以外の変更が無いこと（目視）

## 実行予算

- Issue 全体の能動時間の予算: 5 時間（Issue の見積もり 2〜5 時間の上限）
- phase の目安: Spec・設計レビュー・Spec レビュー 1.5 時間、Task 1 の実装とレビュー 1 時間、最終検証・PR 0.5 時間、PR 修正ループ 最大 3 サイクル ×（レビュー 45 分＋計画・修正 30 分）
- worker の期限: 実装担当は `implement` の役割の期限 90 分。無進捗の打ち切りは runner の既定
- 再試行の上限: 実装の依頼の `retry`・`rejected` は合わせて 2 回まで。Task のレビュー指摘の修正の依頼は 2 回まで
- checkpoint: Task 1 の取り込み後、最終検証の後、ループの各サイクルの後
- 縮小・切り出し・方法変更の候補: records.md の説明が #357 と衝突する場合は 4.1 節の最小の追記だけにする

## contingency（代替策）

- RED で `denial-connection` の stderr が adapter の判定に影響する（`awaiting_approval` にならない）と分かったら、接続失敗を `{"type": "error", "message": "connect ECONNREFUSED ..."}` の error イベントで表す。どちらも CLI の失敗の欄であり、仕様の意味は変わらない。ledger に記録して続ける
- RED で `no-denial-rate-limit` が `rate_limit` にならない（前提の違い）と分かったら、その観測を ledger に書き、Spec の前提が崩れたとして止まる
- 実装担当の `failed`、再試行の上限到達は issue-to-pr の規則どおりその Task で止まる
