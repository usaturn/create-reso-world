# Issue #370 Approval Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude の承認待ちの構造化された根拠を、生ログ回収後も秘密を残さず区別できる診断に保存する。
**Architecture:** awaiting_approval の Receipt.payload に許可リストで作った approval 情報を載せ、既存 runner が Attempt.payload に伝搬する。loop の診断節が再度検査・正規化して保存する。受入判定は変えない。
**Tech Stack:** Python、uv、pydantic、pytest、偽 CLI/NDJSON fixture。
**Spec:** `docs/superpowers/specs/2026-11-10-issue-370-approval-diagnostics-design.md`
**State:** `draft`。issue-to-pr の実行委任で進め、内容承認としない。

## Global Constraints

- 変更範囲は `tools/agent_runner/adapters/claude_code.py`、`.agents/skills/pr-review-fix-loop/scripts/loop.py` の診断節とそれぞれの関連テスト。runner 全体のモデル・受入判定、設定、他の子の所有文書は変えない。
- 実 API/有料モデルをテストから起動しない。tool_input・コマンド全文・認証値・生 stdout/stderr/native session を追加保存しない。
- permission_denials による awaiting_approval は exit0・最終JSON・成果物があっても成功にしない。既存の認証優先・停止確認・sensitive_paths・保存先境界を維持する。
- 正常回答・引用・ツール戻り値の承認語だけでは分類しない。成功 payload の同名キーを構造化された判定根拠にしない。

## 受け入れ基準

動作環境: Linux Dev Container、uv のプロジェクト環境、pytest。実 API/有料モデルをテストから起動しない。
実入力: terminal success / is_error=false / permission_denials 非空の NDJSON、stderr requires approval、複数行・日本語の正常回答/引用/ツール出力。tool_input と subtype に偽の秘密マーカーを入れる。
防御範囲: 承認待ちを実際に判定した安全な構造情報だけを保存する。正常回答・他 runtime の同名キー・不正なメタデータは根拠にしない。旧結果の根拠不在を推測で埋めない。停止・sensitive・保存先・特殊ファイルの既存ガードを保つ。

- A1: 実 adapter.collect → runner の既存保存経路 → verify_reviewer → keep_diagnostic → 生ログ回収後、terminal denial と stderr 承認要求の判定元・件数・terminal 情報が安全な診断で区別できる。
- A2: 正常回答・引用・ツールデータだけの承認語や approval 同名キーで、成功を失敗扱いしたり診断根拠を作らない。
- A3: 保存結果と診断に tool_input・秘密マーカー・任意 subtype 等が漏れず、停止未確認・sensitive_paths・保存先境界の既存ガードを維持する。
- A4: exit0・最終JSON・成果物があっても permission_denials 非空は awaiting_approval のまま、レビュアーを受け入れない。
- A5: terminal denial / stderr 対照 / 成功 / 秘密入り fixture の実行検証が通り、既存 adapter/診断の回帰がない。

## Review Focus

- 承認テキストと terminal denial が共存する入力: 実際の既存優先順を変えず、選ばれた経路を保存する。
- 異常な permission_denials や任意 subtype: raw 値や真偽値を件数として取り込まない。
- 成功 payload の approval キー: 状態と runtime を照合し、偽の根拠を保存しない。
- 回収後の診断: receipt の保存だけでなく keep_diagnostic の永続結果を確認する。
- 停止未確認・秘密あり・保存先外: 新しい解析経路で既存の安全ガードを迂回しない。

## 実行方式と要件対応

指定 --implement による agent-runner 担当 pi_opencode-go_deepseek4-flash_max、fallback=[]。密接な2ファイルの変更を1 Taskとして依頼し、取り込み後に独立した Task レビューと最後の全体レビューを行う。実装を self へ変更しない。
controller は共有条件（同じ NDJSON → 同じ状態 → payload → 保存診断 → 回収の順序）を統合確認する。A1/A3 は保存結果と fixture 秘密マーカーの不在、A2/A4 は成功対照と拒否、A5 は関連回帰の実行証拠で照合する。別版の成功を現行版の証拠にしない。

### Task 1: 安全な承認根拠を adapter から回収後の診断へ伝搬する

**Files:** Modify `tools/agent_runner/adapters/claude_code.py`、`.agents/skills/pr-review-fix-loop/scripts/loop.py`（診断節）。Test `tools/agent_runner/tests/adapters/claude_code/test_adapter.py`、`.agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py`。
**Interfaces:** 既存 `_classify(context, events, stderr) -> tuple[ReceiptStatus, Payload]` と Receipt.payload → Attempt.payload を消費する。awaiting_approval の payload.approval と AttemptDiagnostic.approval に小さな許可リストを追加する。source は permission_denials / diagnostic_text、後者は stderr / error_event / terminal_result の列挙で経路を区別する。terminal subtype は success / error / other / 未観測、is_error は厳密 bool / 未観測、拒否の有無と list の件数を保存する。キー名の微調整は実装判断として一貫させ、report に書く。
**Tests:** S のため必要。失敗根拠の静かな消失・もっともらしい誤分類・拒否の成功化・秘密の永続化を防ぐ。既存ガードの代表テストを再利用し D の網羅を増やさない。文書/設定の固定値テストは追加しない。

- [x] **Step 1:** 実 adapter を使う terminal denial と stderr の対照を追加し、回収後の保存診断が根拠を失う RED を観測する。正常回答/引用/tool result の承認語、成功 payload の同名キーを対照にする。秘密 fixture の raw 入力・任意 subtype・不正メタデータの非漏えいも確認する。
- [x] **Step 2:** `uv run --locked pytest -q tools/agent_runner/tests/adapters/claude_code .agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py` を同期実行し、意図した理由で失敗したことを report へ記す。
- [x] **Step 3:** Spec の設計1〜5に従い最小実装を行う。allowlist の再構築を使い、認証・承認の状態優先順、成功 payload、停止/秘密/境界ガードは変えない。実装上の診断専用 failure payload の意味をコードの docstring/comment に残す。
- [x] **Step 4:** 同じ関連テストを GREEN にし、`uv run --locked pytest -q tools/agent_runner/tests .agents/skills/pr-review-fix-loop/tests` と `git diff --check` を同期実行する。実モデルは起動しない。最後の成果提出までに検証の終了を待つ。
- [x] **Step 5:** 上記4ファイルだけを stage して `fix: preserve sanitized Claude approval diagnostics` で commit。報告は実際の変更・RED/GREEN・argv/終了コード・HEAD・所要時間と内訳・懸念を含む JSON。入れ子 agent、push/PR/Issue/Herdr、他 checkout の編集は禁止。

## 統合・公開（controller）

Task 受取後に同じ関連回帰を実行し、同じ受け入れ基準を Task レビュアーへ渡す。全体差分は origin/refs/heads/main/捕捉SHAから生成して別レビュアーで確認する。
README の入口: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools`。ボード #349 の共有資源の同時検証を避ける。CI は create-reso-world の Actions 無効に従い不要。
最終 commit 後 clean HEAD と各 argv/終了コード/ログを SESSION に保存。全 worktree の秘密検査後に検査SHAを pushし、PRへ Closes #370 を書く（マージ後専用の未確認項目なし）。指定3レビュアーのループを起動し、review-fix-planning の採否と finalize のガードを守る。

## 実行予算

能動時間360分（準備20、実装/Taskレビュー60、統合/公開30、ループ最大3×（レビュー45＋計画・修正30）と予備25）。既に行った準備調査約15分は別途記録し、残りを無断延長しない。
runner implement の期限90分、レビュー45分は既存設定。同期 foreground で待ち timeout は付けない。追加 watcher による停止は使わず、共有 feature worktree・検証は打ち切らない。
同じ信頼性失敗は再試行1回まで。ただし failed はその Task で停止（別モデル引取不可）。retry/rejected は同じ担当への補足後1回まで。安全失敗は即停止。checkpoint は準備/実装/検証/公開/各ループ境界、50%/100%、worker失敗直後。
ledger: `/workspaces/reso-world/tmp/agents/issue-370.kiyh524z/budget.jsonl` と同 SESSION の `sdd/2026-11-10-issue-370-approval-diagnostics/progress.md`。実装依頼ごとに accept 前後を記録して cleanup。ログは最終化の検証再利用のため残し完全パスを報告する。

## contingency（代替策）

- RED で fixture/API前提が違えば意味を保つ最小修正を ledger へ記録する。要件や安全境界が変わる場合は停止。
- main 進行は利用者の明示指示により続行対象。旧/新SHA・差分を別ファイルに残し、取り込み・影響経路と全必要検証の成功後に捕捉値を更新する。未検証のSHA差替え・force/rebase push・helperガード解除はしない。
- runner model失敗、停止未確認、所有不明変更、秘密検査失敗は所定の停止経路。成果・ログを保持する。
- 実装が拡大したらまず既存 payload と2箇所の診断処理に絞る。runner全体の型変更や他Issueの分類改良へ広げない。

## 実施記録

準備: 基準SHA上の関連テスト58件 PASS / exit0。検証ログ `/workspaces/reso-world/tmp/agents/issue-370.kiyh524z/baseline.log`。

再開時の救出: 旧担当は約549秒で認証待ち・停止確認済み、未コミット4ファイルを残し正式成果なし。利用者の再開指示で差分を救出し、担当を変更せず再依頼した。元の失敗を成功扱いせず、`d3eca560`（担当実測447.3秒）をaccept後、Taskレビューの指摘を `9f838ec4`（担当実測247.5秒）で修正した。実装担当への依頼は旧1件＋救出再開1件＋レビュー修正1件。いずれも pi_opencode-go_deepseek4-flash_max、観測モデル opencode-go/deepseek-v4.1-flash/max、fallbackなし。

Task 1は実装・修正レビュー完了。調整役の関連テストは69件 PASS / exit0。認証優先の回帰は実adapterの対照で再現し、修正後は承認根拠を保持したままauthenticationになることを確認した。新規の重複stderrケースはD基準に従って削除し、代表となる既存テストを残した。

A1/A3: 実adapter → runner保存 → keep_diagnostic → 生ログ回収後の構造情報・秘密マーカー非漏えいを統合テストで確認。A2/A4: 正常回答の同名キー/承認語を除外し、exit0でも拒否を受け入れない対照を確認。A5: 担当と調整役の関連テスト、実装担当の回帰が成功。全体回帰・配置検査・ブランチ全体レビュー・秘密検査・PR/ループはこの後の証拠に基づいて報告する。

救出・担当ログ・controller検証は `/workspaces/reso-world/tmp/agents/issue-370-recovery.evovwtrp/`。旧進捗・予算は継続し、停止中の未記録時間も保守的に能動時間へ含めた。旧attemptのcleanupは未コミット変更のため保持、新しい2回の担当領域は記録・ログを保存後にcleanup成功。公開とマージの結果を先取りせず、Spec/Planの状態はdraftを維持する。
