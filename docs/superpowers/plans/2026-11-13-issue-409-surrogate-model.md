# Issue #409 Surrogate Model Rejection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 単一サロゲートを含むモデル名を既存の RecordError 経路で拒否し、コメント ID 付き診断を回復する。

**Architecture:** agent_id_for の UTF-8 encode の失敗だけを RecordError に変換する。caller の捕捉・信頼判定・正常モデルの ID は変更しない。

**Tech Stack:** uv、CPython 3.14、pytest、標準 json/hashlib、オフラインの fixture/fake。

**Spec:** `docs/superpowers/specs/2026-11-13-issue-409-surrogate-model-design.md`（draft、外部 Spec レビュー済み）

## 管理・実行方式

- 状態 `draft`。issue-to-pr の実行許可で進め、内容承認を記録しない。
- worktree `/workspaces/reso-world/.worktrees/issue-409-surrogate-model`、branch `fix/issue-409-surrogate-model`。
- base: usaturn/create-reso-world / origin / refs/heads/main @ `9c3ad41e99bfc91e557f900a301bc6d6884edf0d`（SESSION/code-base.json の捕捉値）。
- `subagent-driven-development`。Task 1 の実装は明示指定の `pi_openai-codex_gpt6-terra_xhigh` に implement_task.py で依頼する。取り込み後に読み取り専用の Task レビュー、controller の統合検証を行う。
- 全体レビューは `--merge` の PR 修正ループの 1 サイクル目で代替する。Task レビューは省略しない。
- SESSION `/workspaces/reso-world/tmp/agents/issue-409.8hux350m`。SDD 作業領域はその下の `sdd/2026-11-13-issue-409-surrogate-model/`。

## Global Constraints

- strict UTF-8 のまま拒否し、置換・無視・surrogatepass による ID は作らない。
- 正常なモデル ID、記録スキーマ、信頼判定、コメントの選択・除外、書込対象は変えない。
- UTF-8 エンコード失敗だけを共通の agent_id_for 境界で RecordError に戻す。問題文は planner.model: から始め、生の不正文字列を埋め込まない。
- S の回帰テストを代表 1 件だけ追加する。同じ守りの caller/v1/v2/文字種の網羅は D なので追加しない。正常側の既存テストを保持する。
- 対象外: _text() の全欄への新しい制約、自由記述・seat model 等の出力エンコード問題、スキーマ変更、投稿者信頼や ID 導出の刷新、他セッションの worktree の片付け。
- Python は uv 経由。作業ログ・下書きは SESSION に置く。モデルの検証用実起動、不正な実 GitHub コメント、push/PR/Issue 更新を実装担当にさせない。

## 受け入れ基準（実装・レビューの brief 共通）

1. 動作環境: Ubuntu Dev Container、uv 管理の CPython、オフラインの fixture/fake を使用。実 GitHub への不正コメント投稿や有料モデルの検証用起動はしない。
2. 実入力: 有効な v2 JSON の planner.model が x\ud800y、コメント ID 12345、信頼済み投稿者のコメント。JSON としては有効だが、モデル識別子としては不正である。
3. 防御範囲: agent_id_for() に渡る UTF-8 エンコード不能なモデル名を拒否する。fold はコメント ID 付きの診断・終了コード 65・トレースバックなし。validate も 65、upsert のモデル名変換は既存 CommentError で拒否し外部書込へ進まない。
4. 正常側: 既存 ASCII 形式と日本語等の有効なモデル名の ID・compose/extract/fold の往復は変わらない。不正コメントの --exclude-comment 12345 では残った正常記録を従来どおり処理できる。
5. 対象外: _text() の全欄への新しい制約、自由記述・seat model 等の出力エンコード問題、スキーマ変更、投稿者信頼や ID 導出の刷新、他セッションの worktree の片付け。

## Review Focus

新規 S の代表テストは不正記録の診断を守る。高低サロゲート・v1/v2 の組み合わせ網羅はしない。以下は既存テストまたは Task 1 の一時統合検証で確かめる（L/D のテストはコミットしない）。

- 有効な非 ASCII モデルの SHA-256 ID と旧 ASCII 形式の ID を変えない。
- コメント ID を含む安全な診断を出し、不正モデルを黙って読み飛ばさない。
- --exclude-comment による不正コメント除外後、正常な記録の処理を再開できる。
- validate/upsert の既存捕捉へ接続し、外部書込へ進まない。
- 他の入力エラーの捕捉を広げず、今回の原因以外を巻き込まない。

### Task 1: 共通 encode 境界の修正と回帰・統合検証

**Files:**
- Modify: `.agents/scripts/review_records.py`（agent_id_for、約234–254行）
- Test: `.agents/scripts/tests/test_review_records.py`（collect_records の壊れたコメントの検査付近）
- controller のみ: 本 Plan の完了記録。Spec のレビュー済みバイト列は変更しない。

**Interfaces:**
- Consumes: `agent_id_for(model: str) -> str`、`RecordError.problems`、`collect_records(comments, ...)`、既存テストの `round_v2()/comment()/status_body()/problems_of()`。
- Produces: encode 不能なモデル名は `RecordError`。正常入力では従来の str ID。同じ例外を既存 caller が捕捉する。

**テスト要否:** S（実際に再発した、記録診断からコメント ID を失う不具合）の代表 1 件をコミットする。同じ守りの別組み合わせは D、CLI 終了コードだけのテストは L とし、一時検証にする。

- [x] **Step 1: S 回帰テストを先に書く。** 名前 `test_collect_records_reports_surrogate_model_with_comment_id`。正常 v2 記録から生成したコメントの JSON の planner.model だけを `x\ud800y` にし、JSON エスケープのまま collect_records に入れる。render/compose に不正モデルを直接渡して fixture 作成中に落とさない。`problems_of()` の結果に `comment 12345: planner.model:` で始まる診断があることを assert する。拒否の理由をテスト内コメントに書く。
- [x] **Step 2: RED を確認。** `uv run pytest .agents/scripts/tests/test_review_records.py -k surrogate_model -q`。encode の `UnicodeEncodeError` による FAIL を記録する。fixture/構文/import の失敗は RED の根拠にしない。
- [x] **Step 3: 最小修正。** agent_id_for の `model.encode("utf-8")` だけの失敗を捕捉し、安全な `RecordError` にする。hashlib の入力は成功時の同じ UTF-8 バイト列。caller や _text、正常 ID への変換は変えない。
- [x] **Step 4: GREEN と関連回帰。** Step 2 のコマンド、続いて `uv run pytest .agents/scripts/tests/test_review_records.py .agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py -q`、`git diff --check`。新規 1 件、正常側を含む全成功を確認する。
- [x] **Step 5: コミットと報告。** 明示パスのみ stage、`fix: reject unencodable model names as record errors`。self-review と実行した RED/GREEN、変更ファイル、所要時間、concerns を報告する。担当の full suite は `uv run pytest tests/skills .agents/skills .agents/scripts tools -q`。実行を同期で待ち、成功/失敗とログを報告する（他原因の失敗を隠さない）。
- [x] **Step 6: controller の取り込み・Task レビュー。** helper の判定と停止を確認して accept、実際の取り込み HEAD で関連回帰を実行。実装時と同じ brief・受け入れ基準、担当報告、Task 開始 BASE からの review package を読み取り専用レビュアーに渡す。spec compliance と task quality の両方を確認する。元の findings をそのまま渡して必要な修正も同じ担当に依頼する。
- [x] **Step 7: controller の統合検証。** SESSION の不正 v2 コメントを fold に入力し 65/コメント12345/tracebackなしを確認。validate の同じ record で65を確認。正常コメントだけと、不正＋正常コメントから --exclude-comment 12345 した結果が等しいことを確認。upsert の compose_body を不正モデルで直接呼び CommentError を確認（ネットワークなし）。既存正常モデルのテストを対応する証拠とする。
- [ ] **Step 8: 完了記録と最終検証。** Plan のチェックボックス・Task/検証/所要時間を事実に基づき更新して commit。以下の必須検証 3 本を clean な最後の HEAD で実行し、head/base/status/argv/終了コード/ログを SESSION の checks.json 等に記録する。

## 要件・原因・検証の対応

| Spec 条件 | 担当 | 観測・証拠 |
|---|---|---|
| encode不能をRecordErrorに変換、コメントID診断 | Task 1 実装担当 | SテストのRED/GREEN、controller foldの65/診断 |
| 正常なASCII/非ASCIIと旧IDを保持 | Task 1 実装・controller統合 | 既存のagent IDとcompose/extract/foldの関連回帰 |
| 同じ入力を既存validate/upsertが拒否 | controller統合（Step 7） | 一時スクリプト、65/CommentError、実外部操作なし |
| 不正コメント除外後に正常記録を復旧 | controller統合（Step 7） | 正常単独foldとexclude後の出力比較 |
| 対象外や共有例外の範囲を変えない | Taskレビュアー/controller | diff確認、同じ入力・例外境界を因果関係で確認 |

## 必須検証・公開

次の argv を Plan commit 後に SESSION/verify-cmds.json へ固定する。検証失敗は systematic-debugging で原因を確認し、解消できなければ停止する。

1. `bash .devcontainer/run-tests.bash`
2. `bash scripts/check-layout.sh`
3. `uv run pytest tests/skills .agents/skills .agents/scripts tools -q`

捕捉した base を各段階で recheck。未 push の非重複 fast-forward だけ helper によって最大 3 回追随し、固定した全検証を再実行する。scan は親 checkout の `scripts/scan-before-push.sh --expected-base-sha`、検査した同じ SHA を push。PR は main 向け、`Closes #409`。この repo の Actions は規約どおり無効、CI を作成/有効化しない。

## 実行予算

- 能動時間の予算 300 分（小修正だが、明示 Spec レビューと既定上限 3 サイクルのレビュー待ちを含む）。準備/設計/計画 20 分、Spec レビュー最大30分、実装/Taskレビュー30分、全検証/公開25分、ループ3×（45分レビュー＋20分計画/修正）を目安とする。ledger は SESSION/budget.jsonl。
- worker は role の既存期限を使用: spec-review 1800秒、implement 5400秒、inspect 2700秒。共有featureへの書込・検証は途中打切り対象にしない。runner は同期で終了と停止確認まで待つ。監視は monitoring-long-tasks とランタイム対応に従い、bash timeout を付けない。
- 再試行: 同じ信頼性失敗は1回まで（Spec review/runner failed等のスキル上即停止する失敗は再試行しない）。retry/rejected の依頼し直しは1回、fallbackは検査済みの空。安全失敗は全体停止。Taskレビュー修正はSDDの上限を守る。ループは既定3サイクル。
- checkpoint: Specレビュー後、Task取り込み・レビュー後、検証・公開前、各ループ境界、50%・100%、worker失敗直後。予算100%は停止。縮小候補は重複した調査/再検証をなくすこと、別原因の自由記述問題を混ぜないこと。必須検証や拒否条件は削減しない。

## contingency（代替策）

- 最初のREDがfixtureの前提違いなら、仕様の意味を変えないfixtureの最小修正をledgerに残し続行する。仕様の意味や正常モデルIDを変える必要があれば停止する。
- encode失敗が共通境界への変換だけで閉じなければ caller の接続を再調査する。同じ試みを繰り返さず、範囲を広げる前に原因と残条件を記録する。
- 指定担当が失敗したら self や別モデルに切り替えない。cleanup後に停止し、残存パスと次の操作を報告する。
- base移動はissue-to-prの条件付き前進追随のみ。所有パスの重複、前提変更、非fast-forward、push後の移動は停止する。
- PR修正ループ以外でマージしない。PR後の記録はSESSIONとPR/Issueに置き、featureへ独自の追加commitをしない。

## 完了記録

- Task 1 実装: `pi_openai-codex_gpt6-terra_xhigh`（明示指定）、runner 実測 model `gpt-6.1-terra` / provider `openai-codex` / effort `xhigh`、session `01a1d2d4-9d5b-724d-b77e-04fc48ae5967`。依頼1回、fallbackなし、所要1430.647秒（担当内訳: 実装/関連確認約35秒、全体検証1342.03秒、最終確認/commit約18秒）。
- 実装commit `8ea11df444cee63f89853b85144d6d62f13305b0`。Sテスト1件でRED（UnicodeEncodeError）→GREEN。関連110 passed、全体1486 passed、すべて期待する終了コード（REDのみ1、ほか0）。
- controller が accept 成功、関連110 passedを再確認。Taskレビューは spec compliant / quality Approved、Critical/Important/Minorなし。最初のレビュー依頼は `Review scope: task` の追記要求があり、追記後に同スコープで実施（追加の実装依頼なし）。
- controller統合: foldは65・comment12345付き診断・stdout空・tracebackなし、validateは65、正常foldと不正コメント除外後のfoldは同じ正常記録、upsert compose_bodyはCommentError。全て実入力で観測し、実ネットワーク書込は行っていない。
- 原因に関わる読取・検証・書込前変換・除外復旧の接続はこの実装HEADで確認済み。既存正常ASCII/非ASCIIの回帰も成功。対象外の自由記述の別原因は変更していない。
- 証拠: `/workspaces/reso-world/tmp/agents/issue-409-implement.xi2dl71o/task-1-evidence/`（担当RED/GREEN/関連/全体ログ・report）、`/workspaces/reso-world/tmp/agents/issue-409.8hux350m/integration.log`・`integration-result.json`・`related-after-import.log`。runnerの停止確認true、cleanupは専用worktree/run-dirを除去しretainedなし。証拠はコミットしないため残す。
- Specレビューのcleanupもretainedなし。reviewed/reflected SHAとdecide結果は SESSION/spec-decide.json に記録。Specレビュー済みバイト列は変更していない。
- Step 8の必須3検証・公開は、この文書のコミット後にcleanな最後のHEADで実施する。結果とHEAD/base/status/ログはSESSION/checks.json・verification.jsonとPR本文に記録し、未実行を成功としない。公開後のループ記録もSESSION/PRに置き、このチェックボックス更新のためだけに検証済みHEADを変更しない。
- deferred/parked: なし。実装担当の監査で unprotected_changes（他セッションと親checkoutを含む）が報告されたが、outside_changesは空。親や他者の変更は回収せず、取込後に今回の差分と統合確認を行った。
