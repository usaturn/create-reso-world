# Issue #416 json_result の adapter 展開と request_prompt 接続 実装計画

## 管理

- 状態: draft
- Spec: `docs/superpowers/specs/2026-11-15-issue-416-json-result-adapters-design.md`
- Issue: https://github.com/usaturn/create-reso-world/issues/416
- 実行許可: Spec の「管理」と同じ（issue-to-pr の明示起動。内容の承認ではない）
- 作業 base: `main` `9800cf36445dd4f1ec67df6e911060df39d8622e`、branch `fix/issue-416-json-result-adapters`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（この run では issue-to-pr の「Task の実装を runner の担当に依頼する」で代える）。Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** claude_code・codex・cursor の JSON 抽出を `json_result.json_object` に、pi・claude_code・codex・cursor の JSON 指示を `request_prompt` に接続する。

**Architecture:** 各 adapter の独自 `_json_object` と手書きの JSON 指示を消し、共有ヘルパーを直接呼ぶ。完了イベントの選択・診断は各 adapter のまま。runtime 文書の JSON の記述を pi.rst に揃える。

**Tech Stack:** Python 3.14、uv、pytest、reStructuredText

## Global Constraints

- 実 CLI・モデル・API は起動しない。偽イベントと `prepare` の戻り値だけを使う
- `json_result.py` の関数本体（スキャナ）を変えない。devin（`adapters/devin.py`・`tests/adapters/devin/`）を変えない
- 完了条件・malformed event・認証/承認の診断を変えない
- テストは AGENTS.md の「テストの採用基準」の S だけを足す

## Review Focus

- codex で、認証・承認エラーの後に空 object `{}` の完了 message が来る: エラーを解除せず `awaiting_authentication` / `awaiting_approval` のまま（Task 1 のテスト）
- claude_code の未閉鎖の `json` fence 内の完全な object: pi と同じく受け付ける（Spec D9。完了条件の `result` イベントで途中切れは別に拒否される）。既存テストの該当の場合を消す（Task 1 の手順 7）
- text の役割の依頼文に `JSON_REQUEST` が入らない: 統合の確認の一時スクリプトで確かめる
- devin の依頼文が変わらない: 統合の確認で base と比べる
- cursor・claude_code で、成功 result の後に新しい応答が続く既存の拒否（先行結果の再利用禁止）が変わらない: 既存テストの全件通過で確かめる

## 実行方式

`implement_task.py check --implement devin_swe2_max` の `self` が false なので、issue-to-pr の「Task の実装を runner の担当に依頼する」で、Task を 1 つずつ順に devin_swe2_max に依頼する（並行しない）。司令塔（Claude Code）は取り込み後のテスト・静的チェック・Task レビューと、統合の確認を行う。`--merge` が適用されるので、最後のブランチ全体のレビューは PR 修正ループの 1 サイクル目で代える。

## 受け入れ基準

（実装担当・Task レビュー担当の brief にこの節をそのまま写す）

- 動作環境: Dev Container、`uv run --locked`、偽イベント（`tools/agent_runner/tests/adapters/test_parser_regressions.py` の `_events`）と `prepare` の戻り値だけを使う。実 CLI・モデル・API は起動しない
- 実入力:
  - 文章 → 裸の JSON（複数行・非 ASCII）: `"レビュー完了。指摘は以下です。\n{\n  \"status\": \"completed\",\n  \"findings\": [\"日本語の指摘\"]\n}"`
  - 文章 → fence 付き JSON: `"Review complete.\n```json\n{\"status\": \"completed\", \"findings\": []}\n```"`
  - 訂正: `"```json\n{\"status\": \"OLD\"}\n```\nI corrected the result.\n```json\n{\"status\": \"NEW\"}\n```"`
  - JSONC の設定例 + 正常な最終結果: `test_json_result.py` の `test_jsonc_example_accepts_result_after_fence` と同じ形
  - 壊れた候補・途切れ: `"{\"status\": \"OLD\"}\nDone.\n{\"status\": \"DONE\","`、文章だけ: `"Review complete."`
- 合格条件:
  - claude_code・codex・cursor の collect が、文章 → 裸の JSON・訂正・JSONC の例 + 最終結果で `success` になり、payload が最後の有効な object と一致する
  - 同じ 3 adapter で、途切れ（先行する有効な object あり）・文章だけが `response_failed` になり、先行する object を返さない
  - pi・claude_code・codex・cursor の JSON の役割の stdin が `request_prompt(prompt, "json")` で始まり、`JSON_REQUEST` を 1 回だけ含み、旧文 `"Return your final answer as a JSON object."` を含まない。text の役割の stdin は `JSON_REQUEST` を含まない
  - codex で、認証エラーの後の空 object `{}` の完了 message はエラーを解除せず、`awaiting_authentication` のまま
  - devin の `prepare` の stdin と argv が base と同じ
  - 既存の adapter テスト（完了条件・診断・隔離）がすべて通る
- 防御範囲（対象）: 上の形で完了結果を採用し、壊れた回答・設定例の object・古い object を成功にしないこと
- 防御範囲（対象にしない反例）: 壊れた候補を含まない正常 object だけの例示は、後続結果が無ければ候補になる（#425 で委任された限界）。意味から例示かどうかを推測しない。実 CLI の出力形式の変化は扱わない

## Task 1: adapter の抽出と JSON 指示を共有ヘルパーに接続する

- 担当ファイル: `tools/agent_runner/adapters/claude_code.py`、`tools/agent_runner/adapters/codex.py`、`tools/agent_runner/adapters/cursor.py`、`tools/agent_runner/adapters/pi.py`、`tools/agent_runner/adapters/json_result.py`（docstring のみ）、`tools/agent_runner/tests/adapters/test_parser_regressions.py`
- 変更しない: `tools/agent_runner/adapters/devin.py`、`json_result.py` の関数本体、`tests/adapters/test_json_result.py`、`tests/adapters/devin/`、各 adapter の完了条件・malformed event・認証/承認の診断
- 手順:
  1. （RED）`test_parser_regressions.py` に S のテストを 3 つ足す（Spec の「テスト」）。
     - `claude-code`・`codex`・`cursor` を parametrize し、訂正形の collect が `{"status": "NEW"}` を payload にする（`_success` を使う）。テストのコメントに「古い object を成功にする誤りを各 adapter の接続ごとに守る」と防ぐ損害を書く
     - 同じ 3 adapter で、`"{\"status\": \"OLD\"}\nDone.\n{\"status\": \"DONE\","` の collect が `response_failed` になり payload が無い（codex・cursor は `outcome.state == "response_failed" and outcome.receipt is None`、claude_code は `outcome.receipt.status == "response_failed" and outcome.receipt.payload is None`。既存テストの判定の書き方に合わせる）
     - codex で、`{"type": "error", "message": "authentication required"}` → `{}` の agent_message → `turn.completed` の collect が `outcome.state == "awaiting_authentication"` かつ `outcome.receipt is None` になる（Spec D4）。コメントに「空 object でエラーを解除すると認証待ちが invalid_result に変わって気付けない」と書く。既存の `test_codex_fresh_completed_message_recovers_error` が陽性対照
     - `uv run --locked pytest tools/agent_runner/tests/adapters/test_parser_regressions.py -q` で、訂正形のテストが claude_code・codex・cursor で失敗することを確かめる
  2. `claude_code.py`: `_FENCE` と `_json_object` を消し、`from tools.agent_runner.adapters.json_result import json_object, request_prompt` を足して `_payload` で `json_object` を使う。`prepare` の `lines` を `[request_prompt(context.request.prompt, context.role.result_shape)]` で始め、`prompt_lines` を続け、`"Return your final answer as a JSON object."` を足す 3 行を消す。Bash の timeout の案内は最後のまま
  3. `codex.py`: `_json_object` を消し、`json_object` と `request_prompt` を import する。`turn.completed` の解除判定と最終 payload の 2 か所を `json_object` にする。解除判定は、抽出した dict が空でないときだけ `pending_errors` を消す（Spec D4。例: `(parsed := json_object(text)) is not None and bool(parsed)` の意味）。`_prompt` を `parts = [request_prompt(context.request.prompt, context.request.result_shape)]` で始め、独自の JSON の文を消す
  4. `cursor.py`: codex と同じ（payload の 1 か所と `_prompt`）
  5. `pi.py`: `request_prompt` を import し、`lines = [request_prompt(context.request.prompt, context.role.result_shape)]` で始め、末尾の独自の文を消す
  6. `json_result.py`: モジュール docstring を「pi・claude_code・codex・cursor・devin は `json_object`。`first_json_object` は現行の adapter から呼ばず、上流との対応と #457 の確認のために残す」の意味に直し、`first_json_object` の docstring にも同じ 1 文を足す。関数本体は変えない
  7. `test_parser_regressions.py`: `test_invalid_fence_cannot_salvage_inner_json` の `'```json\n{"ok":true}'` の場合を消す（Spec D9。もう一方の場合は残す）
  8. （GREEN）検証コマンドを実行する
- テストの要否: 要。訂正形で古い object を成功にする誤り、途切れで先行 object に巻き戻る誤り、空 object で認証待ちの診断が消える誤りは、壊れてもエラーにならない S。3 adapter はそれぞれ別の呼び出し箇所なので D ではない。成功例（訂正形）が拒否例の陽性対照になる。文章 → 裸の JSON・JSONC・壊れた候補の分類は `test_json_result.py` が守る（adapter ごとの網羅は D）。依頼文の文言は L/F なので一時スクリプトで確かめる
- 検証:
  - `uv run --locked pytest tools/agent_runner/tests -q`（終了コード 0）
  - 静的チェック: リポジトリの dev 依存に ruff・型検査は無いので、`uv run --locked python -m compileall -q tools/agent_runner/adapters` で構文を確かめる
- commit: `fix(agent-runner): json_result と request_prompt を claude_code・codex・cursor・pi に接続 (#416)`

## Task 2: runtime 文書を新しい抽出仕様と JSON 指示に合わせる

- 担当ファイル: `tools/agent_runner/runtimes/claude-code.rst`、`tools/agent_runner/runtimes/codex.rst`、`tools/agent_runner/runtimes/cursor.rst`、`tools/agent_runner/runtimes/pi.rst`
- 手順:
  1. claude-code.rst・codex.rst・cursor.rst の「応答と失敗の判定」の JSON の記述を、pi.rst の同じ段落（最後の object、結果 fence の判定、例示の扱い、壊れた候補での拒否・巻き戻らないこと、未閉鎖 fence 内の object）と同じ意味に書き換える。cursor.rst の「最初の JSON オブジェクトを取り出す」は消す。claude-code.rst の「JSON は object 全体か JSON code fence 内の object を受け付ける」は置き換える。codex の「空でないオブジェクト」は、空 object は runner が `invalid_result` にする旨に直す
  2. 4 つの文書の起動（標準入力）の記述の近くに、JSON の役割では共有の `request_prompt` が依頼文の直後に `JSON_REQUEST`（"Answer with a single JSON object as your final message."）を足し、その後に skill の指示が続くことを 1 行で書く
  3. 完了条件・identity・認証/承認の記述は変えない
- テストの要否: 不要（文書の文言は F）。代わりに `git diff` で意味を確かめ、`bash scripts/check-layout.sh` を実行する
- commit: `docs(agent-runner): runtime 文書を json_object と request_prompt に合わせる (#416)`

## 統合の確認（司令塔）

- Spec の受け入れ基準の各合格条件を、Task 1 のテストと一時スクリプト（`PARENT_ROOT/tmp/agents/issue-416.*/` に置く、commit しない）で確かめる: 3 adapter の collect に実入力の全形（文章 → 裸の JSON・fence 付き・訂正・JSONC + 最終・途切れ・文章だけ）を与えた結果、4 adapter の JSON/text の役割の `prepare` の stdin、devin の `prepare` の stdin/argv を base（`9800cf36`）と比べた結果
- 必須の検証コマンド: `uv run --locked pytest tools/agent_runner/tests -q`、`uv run --locked python -m compileall -q tools/agent_runner/adapters`、`bash scripts/check-layout.sh`

## 実行予算

- Issue 全体の能動時間: 360 分（Issue の見積り 2〜5 時間に、外部担当の設計・Spec レビュー、PR 修正ループ最大 3 サイクルを足す）
- phase の目安: 準備・Spec・レビュー 90 分、実装（Task 1・2）90 分、統合の確認と PR 30 分、PR 修正ループ 150 分
- worker: 実装担当（devin_swe2_max）は `implement` の役割の期限 90 分、1 依頼あたりの予約枠 60 分、無進捗の打ち切りは runner の期限に任せる。レビュー担当はループの期限 45 分
- 再試行: 同じ失敗の再試行は 1 回まで（`retry`・`rejected` とも）。上限で止まり、担当は変えない
- checkpoint: Task 1 の取り込み後、Task 2 の取り込み後、PR 作成後、予算の 50%・100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: runtime 文書の更新を最小（JSON の段落だけ）にする。D の整理（devin のテスト）は持ち越す。実装担当が止まった場合は issue-to-pr の規則どおり止まり、担当の変更は利用者が決める

## contingency

- 最初の RED で、訂正形のテストが既に通る adapter があった場合: その adapter の旧抽出の前提が Spec と違うので、ledger に記録し、テストはそのまま残して実装を続ける（意味は変わらない）
- 既存テストが新しい抽出で落ちた場合: 新しい仕様で意味が変わる入力（未閉鎖 fence など）なら Spec D9 と同じく直し ledger に記録する。完了条件・診断のテストが落ちたら実装の誤りとして直す
- devin のテストが落ちた場合: 実装を戻す（devin は対象外）
- 外部担当の `failed`、上限に達した `retry`・`rejected`: その Task で止まり、自分で引き取らない

## 実行の記録

- Task 1: devin_swe2_max（SWE-2 Max、session `angry-burn`）に 1 回依頼、250 秒、`importable`、commit `002a0771`。担当の concern（手順 1 の「2 つ」と Spec の 3 つの食い違い）は Plan の書き漏れで、手順を「3 つ」に修正した（`ea92dfdc`）。Task レビュー: 314 passed、`compileall` 成功、`ruff --select F401,F841` 成功、codex の空 object ガードを `is not None` に戻すミューテーションでテストが 1 件失敗することを確認
- Task 2: devin_swe2_max（session `various-bass`）に 1 回依頼、297 秒、`importable`、commit `e56c3aca`。concern 2 件（pi.rst の既存の曖昧な文を置き換えた、claude-code.rst の要件文を pi.rst に揃えた）は Spec の意味に合うので採用。`bash scripts/check-layout.sh` 成功
- 統合の確認（commit しない一時スクリプト `PARENT_ROOT/tmp/agents/issue-416.q59dbn2x/integration_check.py`）: base `9800cf36` では 29 件中 8 件が NG（claude_code の文章 → 裸の JSON、3 adapter の訂正形で OLD、codex・cursor の JSONC の例 + 最終結果、pi・claude_code の JSON 指示）。HEAD では 31 件すべて OK（3 adapter × 7 形の collect、4 adapter × JSON/text の `prepare`、devin の `prepare` の argv と依頼文ファイルが base と同じ）
- 再試行・失敗: なし。実行予算の使用率は統合の確認の時点で約 6%（ledger は Spec の commit の後に開始）
- `--merge` のため、最後のブランチ全体のレビューは PR 修正ループの 1 サイクル目で代える。ledger の `deferred`（minor の持ち越し）は無い
