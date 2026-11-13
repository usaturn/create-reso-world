# Issue #356 Loop Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** マージ後 abort の読み取り専用照合と、本文を失敗原因にしない安全な診断を追加する。

**Architecture:** 既存 loop.py 内へ AW の該当処理だけを適応する。finalize の ID 保持と reconcile を1つの成果物、診断と fd 安全性をもう1つの成果物とする。同じ loop.py と records.md を共有するので逐次実行する。

**Tech Stack:** Python 3.14、uv、pydantic、pytest、fake gh、一時 Git。

**Spec:** `docs/superpowers/specs/2026-11-14-issue-356-loop-reconcile-design.md`（draft、利用者の issue-to-pr 実行許可。Spec レビュー2回、最終指摘0）。

## Global Constraints

- 運用環境は既存 Dev Container / Python 3.14 / uv / pydantic。実装検証は fake gh と一時 Git のみ。
- `finish.merged: bool | None` と `_abort_merged` はそのまま維持する。
- 既存 cycle_end の spec_commit 許容処理を変更せず、新しい reconcile の HEAD 条件を緩めない。
- loop.py の Herdr 実装・collect 呼出し、checkout-audit の所有ファイル、diagnostics.py モジュール分割、AW Hold/無条件 stop gate、#388 は対象外。全レビュアー不受理の 6→finish held を残す。
- 新しい CI、実サービス呼出し、権限/認証回避、他者 worktree/claim の回収は禁止。
- 恒久テストは AGENTS.md の S のみ。F/L は実コマンド・構造確認にし、D は既存の代表テストの拡張にする。拒否だけで何でも止める実装が通らないよう成功例を残す。
- ソースの作業は runner の使い捨て worktree 内だけ。git stash、パターン停止、python/python3 の直接実行、push・PR・Issue・claim・Herdr 操作は禁止。長時間コマンドは同期で終了を待つ。
- 実装担当は pi_alibaba_qwen4-max_max。失敗時、停止確認・記録・cleanup 後に利用者の明示許可で devin_swe2_max へ切替再試行する。controller が実装を引き取らない。

## Review Focus

1. 保存後の run/cycle 改変で status が不正に merged=true を返さない（Task 1 の既存証拠照合テスト）。
2. 一覧取得後のコメント変更/削除を元の成功と取り違えない（Task 1 の単一コメント再取得・404の代表拒否）。
3. 複数行日本語の本文を改行正規化や文字列化で同一と誤判定しない（Task 1 の成功と本文差分対照）。
4. is_error のツール結果・result 本文を CLI エラーと取り違えない（Task 2 の原因抽出対照）。
5. 親ディレクトリの差替えで出力外または機密ログを読まない（Task 2 の os.open 境界差替えと通常読取対照）。

## 受け入れ基準（実装・Task レビュー双方へ同じ本文を渡す）

- 動作環境: Dev Container、Python 3.14、uv。fake gh と一時 Git だけでテストし、実 PR・実マージ・実 API・実モデルは使わない。HOME は `env HOME=<一時dir> ...` の1回のコマンドだけで置き換え、継承 GIT_* を除去する。`/tmp` には mktemp -d の一意ディレクトリだけを作る。
- 実入力: `loop.py reconcile --run <run_dir> --finalize-result <file> --comment-id <正整数>`。finalize は no_fix_needed / merged=True / 指定 comment ID。判断記録本文には日本語、複数行、末尾改行を含む。GitHub PR は cycle.head と一致しマージ済み。trusted_login が投稿したこの PR の整合する判断記録が、中断前に確定している。
- 成功: 証拠がすべて整合するときだけ reconcile.json を exclusive に追記し、status.reconciled と no_fix_needed/merged=true を返す。元の run/cycle の bytes と abort 結果は保持する。同じ証拠の再実行は既存 bytes を保持する。
- 防御範囲: 対象は ended/abort・最後が planning 未完了・lock なしの run。finalize/ID/PR/HEAD/投稿者/本文/過去記録/日時/既存証拠の不一致は終了4で証拠を上書きしない。存在しない/別PRのコメントも4。状態・lock は3。基盤障害は5。未知の証拠や日時のない旧runを成功にしない。新しいコメント・マージ・push は行わない。
- status は保存済み証拠が元記録と不整合なら4で止まり merged=true を返さない。spec_commit で別HEADとなる run は新しい reconcile では受け付けず、既存 cycle_end/finalize の処理はそのまま維持する。
- finalize MERGED 再開は検証済み comment_id を返し、非マージ分岐の comment は保つ。finish merged の true/false/null、全失敗の終了6、unprotected_changes の非致命性、trusted_login と repo 修飾 ref、承認拒否根拠・prose 制御を維持する。
- 診断: attempt.state==success は cause=unknown。JSON 全体・モデル本文・ツール出力・result/content は分類に使わない。安全な CLI エラー欄・pi の最後の errorMessage・retry.finalError・既存診断行と stderr を使い、本文しかない報告は reported=true/unknown。CLAUDE_OVERLOADED の旧 result-only の期待は unknown に更新し、本物のエラー欄の接続報告は connection。
- ログ: 停止確認・sensitive・字句上の出力内を検証し、root から全祖先を dir_fd/O_DIRECTORY/O_NOFOLLOW で固定する。末端も O_NOFOLLOW/O_NONBLOCK、特殊ファイルは読まない。outside_output/sensitive/not_regular_file と既存の読取上限・分類を維持し、fd を閉じる。
- 統合: 指定 pytest と `bash scripts/check-layout.sh` が成功。fake gh/一時GitのCLIで成功・コメント不一致・HEAD不一致・既存証拠の4ケースを実行。スキル無し/ありの手順適用を比較し、文言固定テストを作らない。

## 要件と担当の対応

- Spec 1〜4・reconcile/ID/status/記録/Herdr文書: Task 1。
- Spec 5〜6・安全な原因分類/ancestor fd/診断文書: Task 2。
- Spec 編集境界・全体回帰・CLI/スキル適用・共有状態/順序: controller の統合工程。Task 1 の保存結果と Task 2 の未変更部分を最終 tree で確認する。
- Task 1 と Task 2 の共有は loop.py と records.md。Task 2 は Task 1 のモデル/照合を変更せず診断節に限定する。

### Task 1: finalize の記録IDと読み取り専用 reconcile

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/scripts/loop.py`（モデル、JSON writer、GitHub.comment、finish/status/reconcile/CLIのみ）
- Modify: `.agents/skills/review-fix-planning/scripts/finalize.py`（MERGED 再開分岐のみ）
- Modify: `.agents/skills/pr-review-fix-loop/references/records.md`（reconcile/aborted_at/status/herdr_pane）
- Modify: `.agents/skills/pr-review-fix-loop/SKILL.md`（停止後の reconcile 手順のみ）
- Create: `.agents/skills/pr-review-fix-loop/tests/test_loop_reconcile.py`
- Modify: `.agents/skills/pr-review-fix-loop/tests/test_loop_state.py`、`test_loop_review.py`、`.agents/skills/review-fix-planning/tests/test_finalize.py`（必要な既存代表ケースの拡張のみ）

**Interfaces:** Consumes `_read_records(github,run)->(comments,state,login)`、records.read_state/check_against、cycle_path/load_cycles、_read_finalize、FinalizePart。Produces `reconcile(run_dir: Path, *, finalize_result: Path, comment_id: int, github: GitHub | None = None)->dict[str,Any]`、GitHub.comment(repository,comment_id)、PullState.merged_at（任意項目）、RunRecord.aborted_at、Reconciliation、status.reconciled/original_result。write_json の exclusive は既定false。

**テストの要否:** S（誤ったPR/証拠の成功報告・上書き・履歴の喪失・信頼境界を防ぐ）。新規 fixture はこのテスト内に閉じ、conftest.py は変更しない。L の argparse/構文/文言固定テストは恒久追加しない。unprotected_changes は loop 層の受け取りを既存成功ケース1件で確認し、他層の全組合せは増やさない。

- [ ] **Step 1: RED** 新規 reconcile の成功対照＋以下の独立した守りを代表テストで固定する: finalize/ID/PR所属/author/body/HEAD/record/times の不整合→4・未作成、lock/不適格run→3、既存証拠不一致→4・bytes不変、同一再実行→bytes不変、statusの元記録改変→4、finish abort日時とmerged3値、MERGED再開comment_id。正常記録には日本語と複数行・末尾改行を使う。新規未実装で失敗することを同期実行し理由を記録する。
- [ ] **Step 2: 実装** Specの設計1〜4に従う。単一コメントのraw応答から日時/user/所属を読み、PR APIから任意merged_atを取る。対象IDの一覧所属を先に確認し、単一取得404も4。コメント本文を正規化しない。先行記録の照合にtrusted_loginを渡す。exclusive公開、既存結果検証、aborted_atをfinish --abortで初回だけ保存（hold()は変更しない）。元ファイルを書き換えずstatusの論理結果だけを切り替える。spec_commit許容の既存cycle_endは変更しない。
- [ ] **Step 3: GREEN** `uv run --locked pytest .agents/skills/pr-review-fix-loop/tests .agents/skills/review-fix-planning/tests/test_finalize.py -q` を同期実行し全成功を確認する。fake gh/一時Gitで実CLIの成功/コメント不一致/HEAD不一致/既存証拠4ケースも実行し結果を報告する（pytest内で実CLIを呼ぶ同じS代表テストでもよい）。
- [ ] **Step 4: 文書** records.md に証拠の形/冪等/abort日時/status/旧runと別spec_commit HEADの非対応、herdr_pane labelを --issue-numberありなら `<repo>:#<Issue番号>`（--issue-repositoryのrepo）、無ければ `PR#<番号>` と例を追加。SKILL.md は止まったときのreconcileコマンドと読取専用・不一致時停止を追加する。controllerが実施するスキル適用の基準シナリオ（元SKILLではマージ後abortに確定手順がなく、変更後は証拠を渡して照合できる）に合わせる。ほかの手順を再設計しない。
- [ ] **Step 5: Commit** 指定パスのみstage、`git diff --check`、`git commit -m "feat: reconcile merged aborted review loops without changing evidence"`。自己レビューと所要時間・RED/GREEN・実CLI結果・懸念を返す。

### Task 2: 終端診断と祖先 fd 固定

**Files:** Modify `.agents/skills/pr-review-fix-loop/scripts/loop.py`（診断節のみ）、`.agents/skills/pr-review-fix-loop/tests/test_loop_diagnostics.py`、`.agents/skills/pr-review-fix-loop/references/records.md`（4.1診断節のみ）。

**Interfaces:** Consumes Task 1 の全体状態/記録を維持。Produces `diagnostic_text(stdout: str|None, stderr: str|None, *, prose: bool, successful: bool)->tuple[str,bool]`、既存署名のread_log_tail、diagnose_attemptがstate==successでunknown。新規モジュールは作らない。

**テストの要否:** S（成功/本文を失敗と誤分類、出力外・機密を読む危険）。Dは既存パラメータケースの拡張にし、同じguardの別path/全組合せは増やさない。通常ログと本物エラーフィールドの陽性対照を残す。

- [ ] **Step 1: RED** 成功ログのUnauthorizedがunknown、失敗の同じstderrはauthentication。is_errorのtool_result/result本文/無関係JSON欄の偽HTTP401はunknown、error系message/error.messageとretry.finalErrorは従来の原因。reportedのみの失敗はresponse_extractionにならない。os.openの境界で祖先をsymlinkへ差替え、出力外の認証文字列を読まない（not_regular_file）と通常読取対照。既存CLAUDE_OVERLOADEDのresult-only期待をunknownへ直し、修正前の失敗を記録する。
- [ ] **Step 2: 実装** Spec設計5〜6に従い、JSON全体でなく安全なCLIエラー欄だけを抽出する。pi最終errorMessage/retry.finalError/prose=True/既存の認証優先と承認拒否根拠を維持。successfulはattempt.stateを使う。ログは字句上のoutput所属とsensitiveを検査し、rootから各祖先をO_NOFOLLOW/dir_fdで開き最後のfdまで全経路を閉じる。ENOTDIR/ELOOPはnot_regular_file。読取上限とpartialの既存意味は維持する。
- [ ] **Step 3: GREEN** `uv run --locked pytest .agents/skills/pr-review-fix-loop/tests .agents/skills/review-fix-planning/tests/test_finalize.py -q` 全成功。既存prose/retry/approval/秘密非保存も含む。Task 1のテストを削除・弱化しない。
- [ ] **Step 4: 文書・Commit** records.md 4.1を成功はunknown、安全な欄だけ、result/content非分類、祖先fdと分類に追従。`git diff --check`、指定3パスのみcommit: `git commit -m "fix: classify only failed attempts and pin log directory descriptors"`。自己レビューと時間・RED/GREEN・懸念を返す。

## 統合・公開工程（controller）

1. Taskごとに同じbrief・実装報告・BASE..HEAD review packageをsp-reviewへ渡す。Review scopeはtask、base/head/依頼条件を明示、読み取り専用・テスト実行不可。Critical/ImportantをSDD上限内で同担当に修正依頼し、範囲外指摘は先に裁定記録する。minorはdeferred一覧に残す。
2. task-1前に元SKILLを渡した読み取り専用の手順適用シナリオを1回、task-1後に同じ入力を変更後SKILLで1回行い、返された手順と実CLIの4ケースを照合する。追加の恒久文言テストは作らない。
3. 必須検証をPlan commit直後にverify-cmds.jsonで固定する。clean HEADで `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`git diff --check <捕捉base>...HEAD` を同期実行し、HEAD/base/argv/exit/log/cleanを記録する。GIT_*除去、HOMEはコマンド単位の隔離を守る。失敗はsystematic-debuggingで調査する。
4. --mergeにより最終ブランチ全体レビューはPR後のループ第1サイクルに置換する。Spec/Planはdraftのまま、進捗はセッションledgerへ。未pushのbase前進は既存helperの最大3回・所有重複/前提検査/再検証条件の下で追随し、無条件rebaseしない。
5. 差分・claim・Issueと競合を再確認しGitleaks後のSHAをそのままpush。PR本文は `Refs #356`（ボードの子）、Specの判断/レビュー/担当/実行方式/検証/所要時間/残件を記す。CIはActions無効を維持。親ボードは書き換えない。
6. 親checkoutのloop.py startへ指定loop_args（順序維持）とIssue表示引数・正確なcontroller IDを渡す。pr-review-fix-loop/review-fix-planningに従い、マージはfinalize.pyだけ。finish後に結果を子へコメントし、自claimだけexpected-SHA leaseで解放する。マージ後のIssueは観測したstateを報告し、親snapshot/子closeは調整役の規則を守る。

## 実行予算

能動時間360分（2026-11-14 04:12 JST開始のbudget.jsonl）。Issue規模M、2実装Taskと指定Specレビュー最大2回、ループ最大3サイクルを含む。内訳目安: 準備/設計/Specレビュー60分、実装・Taskレビュー90分、統合/検証/公開35分、ループ175分。

- 実装role期限90分/依頼（runner設定）。同じTaskの信頼性失敗は1回まで。Qwen失敗後のDevin切替はその再試行に数える。Taskレビュー修正はSDDの上限を守り、最初の3回は元担当へ依頼する。
- Specレビューはrole期限30分、最大2回を消化済み。レビュー/実装runnerは同期で全停止確認まで待ち、共有feature worktreeや検証を時間のためにkillしない。
- PRレビュアー期限45分、最大3サイクルは既定。停止手順はmonitoring-long-tasksとrunner自身の期限を使用。読み取り専用の追加調査はtask_watchを使う場合のみ絶対期限600秒/予約120秒/無進捗300秒/INT/猶予30秒/同じ失敗の再試行1回を事前宣言する。
- checkpoint: Spec後、各Task後、検証前、loop各サイクル、予算50%/100%、失敗直後。安全失敗/停止未確認は全停止、100%は延長せず停止。付随処理が成果を上回れば残りの追加調査を減らし、範囲を変えず必要な受け入れだけに集中する。
- ledger: `/workspaces/reso-world/tmp/agents/issue-356.6bqr0_mq/budget.jsonl`、SDD: 同ディレクトリ `sdd/2026-11-14-issue-356-loop-reconcile/`。終了後は記録を報告へ移し、自分の非稼働領域のみ片付ける。handoff時はパスを保存する。

## contingency（代替策）

- 初回REDでfixture/API前提だけが違えば意味を保つ最小修正をledgerに記録して続行。Specの成功条件や防御を弱めない。
- Qwenの起動/出力形式/期限等の信頼性失敗は停止確認後Devinで1回再試行。安全失敗や停止未確認は切り替えない。controllerの自己実装へ逃げない。
- 既存テストがresult本文を原因にしていた場合はSpecレビューS1の裁定どおりunknownへ期待を直す。別の診断原因の同時保存は#388へ残し本Taskへ広げない。
- 動作する最小reconcileを残して診断を別Issueへ切り出すことは成功条件を変えるため、このrunで独断実施せず未完了として報告する。
- PlannotatorはSpecで利用不可（review-resultタイムアウト）だった。Planも指定のbridgeを呼び、利用不可ならissue-to-prの実行委任に基づき追加質問なしで進む。人間の承認は記録しない。

## Self-review

Spec1〜4→Task1、5〜6→Task2、編集禁止→Global Constraintsと各Files、全受入→同一本文/統合工程に対応済み。2Taskの共有fileは直列、interfacesの名前は既存型に一致。F/L/Dテストの新設は要求していない。Review Focusの5件は担当TaskのREDに含めた。
