# Issue #418 Pi JSON Result Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** pi の最終回答に説明文と非 fence JSON が混在しても完了結果を失わず、壊れた候補を成功扱いしない。

**Architecture:** pi 独自の抽出関数を削除し、既存の `json_result.json_object` に直接接続する。イベントの完了判定は変更せず、抽出の配線を collect 経路で確認する。

**Tech Stack:** Python 3.14 / uv / pytest / reStructuredText。

**Spec:** `docs/superpowers/specs/2026-11-13-issue-418-pi-json-result-design.md`（内容版 `0bee265c0027ea30eff4c347cc8aa4a60e8b34e8`、Spec レビュー済み、draft）。

## 管理・実行許可

- 状態: draft。内容の approved は記録しない。確認用コピーは作らない。
- 対象: usaturn/create-reso-world #418。コード・文書は同じ worktree / PR。
- 利用者の今回の指定: `#418 --merge --spec-review devin_swe2_max --implement pi_openai-codex_gpt6-terra_xhigh --assign implement=pi_openai-codex_gpt6-terra_xhigh --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_xhigh`。
- 続く利用者の指示「claude-code_opus_default に変更してください。」により、最後の inspect 担当だけを `claude-code_opus_default` に訂正した。
- `check-options` 成功: max_cycles=3 は既定。inspect の3担当・fix.implement の Terra は明示指定。fallback は全て空。self-review / fix-check は既定 self。
- `implement_task.py check` 成功: agents=`[pi_openai-codex_gpt6-terra_xhigh]`、fallback=`[]`、self=false。実装担当は以前の self ではない。
- 実行方式: runner に Task を一つずつ依頼する SDD。実装・テスト・文書は同じ配線変更なので1 Taskにまとめる。取り込み後は別 context の読み取り専用 Task レビューを行う。最後の全体レビューは --merge ループ1回目で代える。
- 再開の実行許可: runner が旧 pi 抽出により response_failed となった後、controller の具体的な提案「保存済み成果を検証して取り込む方法で再開していいっちゃ？」に対し、利用者は「再開してください。」と指示した。failed を成功扱いせず、保存済みの実装 commit `ff3333420d5ff26907df8d61380193a61c023498` の範囲・履歴・差分を照合して取り込み、テストと独立 Task レビューをやり直す例外を許可されたものとする。新たな実装担当への切替・追加課金は行っていない。
- Spec レビューは前セッションの devin_swe2_max / SWE-2 Max、319.7秒、S1 minor採用、next=plan、cleanup retained=0 を引き継ぐ。builder check を重複して行わない。レビュー済み Spec のバイト列は変えない。
- base: origin / refs/heads/main / `777a67a8116d2d63652105802c9aa1dfc565e5aa`。新しい branch / worktree を作らず `fix/issue-418-pi-json-result` を使う。

## Global Constraints

- `_json_object`・`_FENCE` を削除し、`json_result.json_object` を import して `_payload` で使う。
- `_classify`・`_events`・`prepare`・`_identity` は変更しない。
- `json_result.py` のスキャナと `request_prompt`、他 adapter、#414・#416 の統合・close は対象外。
- pi の既存プロンプト指示（`Return your final answer as a JSON object.`）は維持する。
- 実 CLI・モデル・API で不具合を再現しない。挙動の検証は偽 pi イベントのみ。
- テストは AGENTS.md の S のみ追加し、json_result の規則網羅（D）・文書文言の転記（F）・単なる import エラー（L）のテストを追加しない。
- force push・branch 削除・直接マージは禁止。マージは --merge ループの finalize.py のみ。

## 受け入れ基準

### 動作環境

Dev Container（Ubuntu 26.04）・Python 3.14・`uv run pytest`。偽 NDJSON を保存して `ADAPTER.collect` を呼ぶ。実 CLI・モデル・API の再現はしない。

### 実入力

`session` → `agent_end`（最後の assistant の text）→ `agent_settled` を独立に組み立てる。

- `Review complete.\n{"status":"completed","findings":[]}` は success、payload はその object。
- 古い fence JSON → 日本語の訂正説明 → 新しい fence JSON は success、payload は最後の object（最初の object ではない）。
- `{"ok":true}\n{"broken": }` と、有効 fence の後に壊れた閉鎖 JSON fence を置く形は、どちらも response_failed / payload=None。以前の結果に巻き戻らない。
- prose + fence JSON・全体 JSON・文字列内の backtick は引き続き success。prose のみは response_failed。
- 未閉鎖 fence + 有効 JSON は json_result と同じ success とし、文書に明記する。

### 防御範囲

対象は pi collect の `_payload` → `json_object` の配線。正常な完了イベントがある場合の抽出だけを変更する。agent_end / agent_settled の必須、後続破損行、異常 stopReason、認証・承認診断の優先、argv、identity の観測範囲を緩めない。example（閉鎖 inline code span・明示した非 JSON 言語の閉鎖 fence）内の壊れた候補は既存 json_result の仕様どおり拒否理由にしない。スキャナ・他 adapter・request_prompt は変更しない。

## Review Focus

- 訂正形の最初の object への誤配線: Task 1 の collect テストで最後の payload を比較する。
- 閉鎖 JSON fence 内の壊れた候補を救済する回帰: Task 1 の拒否テストで非 fence 形と一緒に確認する。
- 抽出できてもイベントが未完了のケース: 既存 pi の lifecycle・破損イベント・診断テストを再実行する（新規の重複テストは書かない）。
- JSON 文字列内の backtick: 既存 `test_fenced_json_with_nested_code_backticks_is_data` を再実行する。
- 未閉鎖 fence の意図的変更と他 adapter の拒否の混同: Task 1 で旧 pi の parametrization だけを外し、非コミットの観測で success を確かめる。

## 要件照合・統合担当

実装担当と Task レビュアーには、上の Global Constraints と受け入れ基準を同じ brief で渡す。統合担当は controller。

| 条件 | 担当 / 観測 / 証拠 |
| --- | --- |
| prose + 裸 JSON の取り込み | Task 1 / success と payload / collect S テスト、RED→GREEN |
| 訂正結果と壊れた候補 | Task 1 / 最後の object、拒否時 payload=None / collect S テスト |
| 既存の完了判定・文字列 | controller / lifecycle・診断・backtick の既存テスト成功 / targeted pytest と diff |
| example 境界などの共有規則 | controller / json_result は不変、既存単体テスト成功 / diff と pytest |
| 文書と意図的挙動変更 | Task 1 + controller / pi.rst の意味、未閉鎖 fence・proseのみの実出力 / 差分と非コミットの観測 |

## Task 1: pi の抽出を共有ヘルパーへ接続する

**Files:**
- Modify: `tools/agent_runner/adapters/pi.py`
- Modify: `tools/agent_runner/runtimes/pi.rst`
- Test: `tools/agent_runner/tests/adapters/pi/test_adapter.py`
- Test: `tools/agent_runner/tests/adapters/test_parser_regressions.py`

**Interfaces:** Consumes `json_result.json_object(text: str) -> dict[str, object] | None`。Produces 既存 `_payload(text: str, shape: ResultShape) -> tuple[ReceiptStatus, Payload]` と collect の仕様。公開型や signature は変えない。

**テストの要否:** S。完了した有料結果の損失、古い訂正結果の静かな採用、壊れた結果の成功扱いを防ぐ配線テスト。json_result の規則自体は既存単体テストに任せる。文書は差分の意味を検査する。

- [x] Step 1: `test_collect_prose_json_result` を追加し、prose + 裸 JSON が success で期待 payload になることを確認する。既存 `_session` / `_assistant` / `_agent_end` / `_collect` を使う。
- [x] Step 2: `test_collect_uses_last_corrected_json_result` を追加する。古い fence `{"version":"old"}` → 日本語訂正 prose → 新しい fence `{"version":"new"}` を与え、success と payload `{"version":"new"}` を比較する。
- [x] Step 3: `test_collect_rejects_malformed_json_candidate` を追加する。先行有効結果の後に壊れた候補を置く非 fence 形と閉鎖 JSON fence 形を parametrize。両方 response_failed / payload=None を確認する。
- [x] Step 4: 新規テストのみ `uv run pytest tools/agent_runner/tests/adapters/pi/test_adapter.py -q -k 'prose_json_result or last_corrected_json_result or malformed_json_candidate'` で実行し、旧抽出で prose・訂正・閉鎖壊れ候補の失敗を確認する。既に通る非 fence 拒否の対照はそのまま残す。
- [x] Step 5: pi.py に `from tools.agent_runner.adapters.json_result import json_object` を加え、`_FENCE` と `_json_object` を削除し、`_payload` の呼出しを直接差し替える。モジュール docstring に共有抽出を使うことを追記する。`re` は診断等で引き続き必要。
- [x] Step 6: `test_invalid_fence_cannot_salvage_inner_json` の runtime parametrization から pi だけを外し、claude-code と既存 text fixtures は維持する。
- [x] Step 7: pi.rst の抽出説明を prose + 裸/fence JSON、最後の object、壊れた候補拒否と巻き戻し禁止、example の例外、未閉鎖 fence の接受へ更新する。RST 文書のラベル・構造は維持する。
- [x] Step 8: `uv run pytest tools/agent_runner/tests/adapters/pi tools/agent_runner/tests/adapters/test_parser_regressions.py tools/agent_runner/tests/adapters/test_json_result.py -q` と `uv run --locked python -m compileall -q tools/agent_runner/adapters/pi.py tools/agent_runner/tests/adapters/pi/test_adapter.py tools/agent_runner/tests/adapters/test_parser_regressions.py` を同期実行し、終了コード0を確認する。
- [x] Step 9: diff と自己レビューで編集禁止の関数・ファイルを変えていないことを確認し、担当4パスだけを stage・commit する。メッセージ `fix(agent-runner): use shared JSON result extraction for pi`。引き継いだ trailer `Co-Authored-By: Claude Code <noreply@anthropic.com>` を維持する。所要時間、RED/GREEN、テスト結果、commit、懸念を報告する。

## controller の統合・公開手順

1. runner の verdict に従って accept / cleanup。受け取り中の feature worktree を変更しない。
2. 同じ Task brief・担当報告・base..head diff を読み取り専用 sp-review に渡し、仕様準拠と品質の両方を確認する。採用指摘は原文のまま runner へ再依頼する。
3. 未閉鎖 fence・proseのみ・prose + fence の collect 実出力を一時観測する。新規コミットテストは追加しない。
4. Plan/Spec の状態は draft を維持し、実施結果は SESSION / PR に残す。最終commit後の cleanな HEAD で必須検証を記録する。
5. 必須検証（全てfeature cwd）: targeted pytest（Step 8）、`uv run pytest tools/agent_runner/tests -q`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools -q`、Step 8 の compileall。ruff は未導入かつ pyproject に依存定義が無いため追加導入せず、pytest・構文・diff で代える。
6. base・Issue状態・競合を再確認し、Gitleaksを通した同じSHAをpush。main向け1 PR（`Closes #418`）を作成。GitHub Actionsは無効のままでローカル検証を使う。
7. 指定3レビュアーと Terra の fix.implement で --merge ループを開始し、ループの finalize.py だけでマージする。所要時間・残存ログ・実 Issue state を報告する。

## 実行予算

再開後の能動時間の上限360分。前セッションの準備時間は未計測で、Specレビュー319.7秒のみ既知。今回の ledger は `/workspaces/reso-world/tmp/agents/issue-418.u_ouh3so/budget.jsonl`。
準備・計画30分、実装/Taskレビュー60分、統合検証45分、公開等の余裕0～15分、ループ3回×（レビュー45分＋計画/修正30分）=225分を見込む。
runner実装は絶対期限90分（5400秒）、そのうち最後の10分を検証・結果保存の目安とする。Piの同期実行では途中の実質進捗を観測できないため無進捗による独自killは行わず、runnerの期限と停止確認に従う。ループレビューは45分のrunner期限で待つ。
同じ reliability 失敗の再試行は1回まで。ただし helper が failed・設定拒否・停止未確認を返す場合は issue-to-pr の停止条件を優先する。安全の失敗は即停止。各phase境界・50%・100%・worker失敗直後にcheckpoint。100%で延長せず停止する。
SDD記録は SESSION の `sdd/2026-11-13-issue-418-pi-json-result/`。検証記録はループで再利用するため完了後もSESSIONを残し、絶対パスを報告する。

## contingency（代替策）

最初のREDでfixtureのAPI前提だけが違えば、仕様の意味を保つ最小修正をledgerに残して継続する。意味が変わる場合は停止。runnerが失敗したらselfで実装を引き取らない。
base前進は未push・非重複等の条件を満たす場合だけ、issue-to-prのinspect-advance→advance→必須再検証で累計3回まで追随する。重複・非FF・push済みなら停止する。
時間超過・監査拒否・外部送信の懸念・停止未確認では範囲や安全境界を緩めず、残作業を引き継ぐ。課金モデルでの不具合再現、スキャナ書き換え、他adapterのついで修正を代替策にしない。
