# #389 / #390 Review Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Task は implement_task.py 経由の指定 runner 担当へ 1 件ずつ直列依頼する。

**状態:** `draft`。issue-to-pr の実行許可に基づく。内容承認ではない。
**Goal:** 不適切な出力先を担当起動前に拒否し、review cleanup の削除成功後の JSONL 追記障害から通常再実行で回復する。
**Architecture:** 正規パスの共通判定を起動前にも適用する。review cleanup に削除後の成功 sidecar を追加し、保存済みレビュー・試行・実 common-dir と照合して欠落 JSONL を再追記する。共有分類の拒否は弱めない。
**Tech Stack:** Python / uv / pydantic / 実 Git / Linux flock、既存 agent-runner と fake adapter。
**Spec:** `docs/superpowers/specs/2026-11-12-issue-390-review-cleanup-design.md`（commit ab7f999e。最終 reflected SHA-256 dca7f39473ccfabbe279e18568a376fa64bcfbdca6a7e470e058ded48f57eb7e）。

## Global Constraints

- #389 を最初の独立実装コミットにし、#390 はその後。実装担当は `pi_opencode-go_deepseek4-flash_max`、fallback=[]。失敗で self へ切り替えない。
- 成功証拠は削除成功後だけ保存する。削除予定と不在だけで成功と判断しない。既存記録の内容を上書きしない。
- 証拠不明の消失・再出現、symlink/別 common-dir、private receipt、停止未確認・sensitive_paths の拒否を維持する。
- fake と一時 Git だけをテストに使う。実モデル・認証情報・実サービスを試験に使わない。
- #389 の明示拒否は L のため一時検証だけ。恒久追加は #390 の S の代表ケースだけ。F/L/D のテストを増やさない。
- main base は origin / refs/heads/main / c3a8e113c3af010fac94820266b93e107d6dbfaf。移動は停止し、新 SHA を無検証で採用しない。
- 非コミットのログ・検証スクリプトは親の SESSION または一意の /tmp。worktree 内に残さない。rm/rmdir に変数を使うときは全変数に :? ガード。

## 受け入れ基準

### 動作環境・実入力・防御範囲

Linux Dev Container、uv、実 Git worktree と実 agent-runner、fake adapter/CLI。複数試行・非 ASCII のパスと review 内容・複数行 JSON 入力を扱う。外部の実モデルや資格情報・実サービスをテストには使わない。実モデル起動は指定 Spec レビューと実装担当・PR ループの workflow 作業だけに限る。

対象は issue-to-pr の出力先検査と Spec/design cleanup。runner 本体の仕様変更、implement cleanup 全体の再設計、任意の破損修復、過去失敗証拠の書換え、実際の他セッションの資源回収は対象外。

### #389 の条件

1. `real/sub/../run` と `alias/run`（alias は祖先 symlink）を、外部担当起動・runner 成果物作成前に拒否する。fake adapter 起動 0 回、出力先不在、参照先・既存 worktree 登録・feature HEAD 不変を確認する。
2. 正規実パスで run → accept → cleanup が成功し、実行後の worktree 差替えは拒否する。
3. fake と一時 Git だけを使用する。明示拒否の L テストは恒久追加せず一時検証、既存 S テストを維持する。

### #390 の条件

1. 修正後の実 runner＋fake の成功 1 試行、および失敗 primary＋成功 fallback のそれぞれで、worktree 削除成功後の cleanup.jsonl 最初の os.write だけへ EIO を注入する。初回は明示失敗し、I/O 回復後の別 CLI プロセスから通常 cleanup で残る worktree・runner-dir を回収し、さらに再実行が no-op である。各 normal 対照も確認する。runner-dir 削除後の JSONL 追記失敗も一時検証し、2 回目で欠落イベントが追記され、3 回目が no-op である。
2. 同一レビュー・試行・worktree の成功証拠を用いる。証拠のない旧記録・不明消失は拒否して手動照合情報を示す。予定＋不在だけで成功としない。
3. 中断時に全未処理試行と runner-dir を削除せず、完全パスと理由、照合先 records を報告する。
4. 既存 Spec/ledger/runner メタデータの生バイト、無関係な登録、CODE_ROOT HEAD/status を前後比較し、不正な改変がない。
5. 予期しない消失・再出現、symlink/別 common-dir、private receipt、停止未確認の既存拒否を維持する。design の委譲も同じ仕様である。
6. 過去記録を改変しない。旧 Spec `docs/superpowers/specs/2026-11-09-issue-353-review-steps-design.md` の #L-3 の一般化は元の行を残して末尾に訂正する。旧 #L-2 は関連ケースだが対象外で、implement cleanup の従来の回収挙動は変えない。
7. main 向けの 1 本の PR 本文に `Closes #389` と `Closes #390` をそれぞれ記載し、両 Task の各受け入れ条件に対応する検証結果を示す。

## Review Focus

- 実 runner が worktree 外へ残す request.json を fixture から落とさない（Task 2 の real runner fake で確認）。
- runner-dir 削除後の JSONL 失敗にも成功証拠を使い、早期 return 前に再追記する（Task 2 の一時検証）。
- 不正・共有 sidecar／現在の別 common-dir を成功にしない（Task 2 S の代表ケースと既存回帰）。
- lock 競合時に削除せず、プロセス終了後の逐次再実行は通る（Task 2 S）。
- callback 中断の後続全試行・runner-dir と records の報告（Task 2 S）。

## Task 1: #389 の出力先を起動前に拒否

**担当:** 指定 runner 実装担当。
**Files:** Modify `.agents/skills/issue-to-pr/scripts/implement_task.py` の run（507行付近）。恒久テストファイルは変更しない。
**Interfaces:** `run(config, request, output_dir, ...)` の引数・結果を維持。既存 `_canonical_absolute(Path)`・`_symlink_component(Path)` と同じ判定を起動前に適用。assess/accept/cleanup の後段再検査を維持。
**条件:** 上の Task 1 全条件と動作環境・実入力・防御範囲をそのまま適用。
**テスト要否:** L の新規拒否は恒久不要。既存 S を実行し、一時 script で副作用の不在と正常対照を確認。

- [ ] 一時再現を SESSION 下へ作り、fake の起動回数・出力先・Git登録・HEAD の前後を記録する。変更前に問題を観測する。
- [ ] run_workflow より前で正規絶対パス・symlink 構成要素を検査する。読取不能も起動せず拒否する。resolve で黙って受理しない。
- [ ] 一時検証の両拒否例と正規 run→accept→cleanup、実行後の差替え拒否を実行する。
- [ ] `uv run pytest .agents/skills/issue-to-pr/tests/test_implement_task.py .agents/skills/issue-to-pr/tests/test_implement_task_run.py -q`、`git diff --check` を実行し、ログの完全パスと終了コードを報告。
- [ ] 明示ファイルだけ commit: `fix(issue-to-pr): validate implementation output before launch`。

## Task 2: #390 の成功証拠・復旧・中断報告

**担当:** 同じ指定 runner 実装担当（新規依頼）。Task 1 完了・レビュー後に開始。
**Files:** Modify `.agents/skills/issue-to-pr/scripts/review_spec.py`、`review_design.py`（共通 cleanup と CLI エラー情報）、`implement_task.py`（callback 失敗後の報告だけ）、`tests/test_review_spec.py`・`tests/test_review_design.py`（`.agents/skills/issue-to-pr/` 基準）、旧 Spec の末尾訂正。
**Interfaces:** `cleanup(review_dir, kind=SPEC_REVIEW)` は正常結果を維持し、retained 非空のときだけトップレベル records を付ける。`remove_attempts` の callback 署名は Path のまま。証拠フォーマット・取得順・出力は Spec「成功証拠と復旧の仕様」に定義したとおり。新しい import 先が必要なら `.agents/skills/issue-to-pr/scripts/review_cleanup.py` と対応する `tests/test_review_cleanup.py` へ責務を分離できるが、runner 本体は変更しない。
**条件:** 上の Task 2 全条件と動作環境・実入力・防御範囲をそのまま適用。Task 1 の判定を維持。
**テスト要否:** 削除証拠の誤認・記録欠落・競合は S。real runner＋fake の代表復旧、未知消失拒否、証拠・lock の安全境界を先に RED にする。正常対照を残し D は統合する。

- [ ] 既存 fixture と実 runner の差を確認し、成功1試行／失敗primary＋成功fallback の fault/normal を構成する。実 runner の request.json をそのまま使い、_append_cleanup_event 内の最初の os.write だけに単発 EIO を注入する。変更前の missing 継続と後続一覧欠落を確認する。
- [ ] 恒久 S の代表テストを先に RED にする。別 CLI での復旧→再実行、既存 bytes/無関係登録/HEAD保全、証拠なし・不正証拠拒否、後続一覧、lock 競合を assert。L/F/D を足さない。
- [ ] Spec の flat sidecar、strict schema、key、fsync 保存順、private regular file、現在の common-dir と batch/path一意性の照合を実装。lock を読取前に取得。欠落イベントの再追記を早期 no-op より前にする。
- [ ] callback 失敗後の削除を止め、後続を報告だけ行う。通常 retained の records と事前拒否の互換例外・CLI終了2（Spec/design両方）を実装。
- [ ] 旧 Spec 末尾に #390 の訂正根拠と旧 #L-2 の対象外を追記する。元の行・失敗証拠は書き換えない。
- [ ] Task 2 全条件の四対照、別 CLI、runner-dir 追記失敗の一時検証、design 委譲、既存安全境界を実行する。`uv run pytest .agents/skills/issue-to-pr/tests -q` と `git diff --check`、利用可能な静的検査を実行しログを報告。
- [ ] 明示ファイルだけ commit: `fix(issue-to-pr): recover review cleanup from receipt append failures`。

## Task 3: controller の統合・検証・公開

**Files:** 実装ファイルは編集しない。SESSION の証拠・PR本文、必要な Plan の記録追記だけ。
**テスト要否:** 新規テスト不要。Task 1/2 の共有入力・状態・順序・証拠を条件単位で照合する。

- [ ] 同じ受け入れ基準本文を各実装 brief と Task review brief に写す。実装結果を accept 後に関連テストを再実行して read-only sp-review に依頼する。全 Plan/Spec をレビュアーだけへ追加しない。
- [ ] Task1 の起動前判定と Task2 の後段分類、Spec/design 共通 cleanup、保存→JSONL→復旧→no-op の順序、fail-closed の両側、旧記録の訂正を条件単位で照合する。
- [ ] 最後の commit 後の clean HEAD で `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`git diff --check <captured-base>...HEAD` を同期実行し、argv/終了コード/絶対ログパス/HEAD/clean/base を SESSION の validation と finalize checks-file に記録する。
- [ ] base・両Issue状態・競合を再確認。親 scan-before-push --expected-base-sha で検査した SHA をそのまま push。main 向け PR を1本作り、Closes #389 / Closes #390 と全条件の結果を記す。spec/planも同じPR。
- [ ] --merge のため最終全体レビューは PR ループ1回目で代える。指定 inspect 3担当、fix implement の loop を親 helper で実行する。マージは finalize.py のみ。Actions は無効。Issue の観測 state を報告する。

## 実行予算

全体能動時間は 480 分（2 修正・Spec レビュー最大2回・最大3サイクルのPRレビュー/修正を含む）。開始前の調査約17分も最終所要へ含める。ledger: `/workspaces/reso-world/tmp/agents/issue-390.bq1npfwa/budget.jsonl`。準備/設計70分、実装100分、Task review/統合/検証50分、公開10分、ループ最大250分が目安。

worker の期限は helper の役割上限（implement 5400秒、Spec/inspect 2700秒）。pi は timeout を付けず foreground 同期で待ち、戻りの終了コード・stop_confirmed・実ログを確認する。今回は実行途中の独自打ち切りを宣言せず、予約枠・無進捗停止は追加しない（runner の期限・停止確認を使う）。同じ reliability 原因は再試行1回まで、safety は即全体停止。失敗・phase境界・50%/100%に checkpoint、100%で停止。Task レビュー修正は上限5サイクルだが予算・指定担当の制約を優先。

## contingency（代替策）

初回 RED の fixture/API 前提差は意味を保つ最小修正を ledger に残して継続する。証拠が保存できない crash 窓・部分JSONLは自動修復へ広げず停止情報を返す。実装で責務が肥大化するなら同 scripts の小モジュールへ分離し、共有 classifier と runner は作り直さない。Task が rejected/retry なら同じ担当へ文脈を補い新RUN_DIRで1回まで、failed は停止しselfへ切替不可。base移動・競合・未知の外部送信・安全境界違反は停止。必要条件を削って成功にせず、未完了は根拠と残作業を保存して引き継ぐ。
