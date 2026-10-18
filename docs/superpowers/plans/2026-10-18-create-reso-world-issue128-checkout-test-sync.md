# Issue #128 Checkout Test Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 子 git の起動前に kill する競合を、2 つの中断テストの待ち合わせだけで解消する。

**Architecture:** wrapper が checkout 成功後に書く既存の PID ファイルを期限付きで待つ。helper と既存の assertion は変更しない。

**Tech Stack:** Python、pytest、Git、POSIX process/signal。

**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue128-checkout-test-sync-design.md`

## 管理・実行許可

- 文書管理・実装対象: `usaturn/create-reso-world`、Issue https://github.com/usaturn/create-reso-world/issues/128
- 状態: `draft`。利用者が `issue-to-pr` を明示して `#128` と指示。通常設計判断・commit・push・main 向け PR 作成までの実行許可であり、内容の承認ではない。マージしない。
- 基準コード: `50e4a6bcbbc3e04fc20802e74997b9b00afbe6c2`
- 実行方式: inline（executing-plans）。1 ファイル・1 Task のため。Spec の builder check と最後のブランチ全体レビューを同期の sp-review に委譲する。同じ worktree へ並行して書き込ませない。

## Global Constraints

- `pr_review_workspace.py`、SKILL.md、installer、CI、ローカルワールドと他者の作業は変更しない。
- 既存の kill・inspect・abandon の assertion と finally の cleanup は維持する。
- 待機の期限 30 秒・ポーリング間隔 0.05 秒。固定時間 sleep の追加や成功するまでのテスト再実行では代用しない。
- 実行は uv を使う。確認用 Spec/Plan コピーは作らず、この PR に draft 文書を含める。
- AGENTS.md を優先し、ledger・brief・隔離コピー・ログは `/workspaces/reso-world/tmp/agents/issue-128.6jfkkfsu/` に置く。既定の `.superpowers/sdd` を worktree 内に作るスキル補助スクリプトは使わず、同じ進捗情報をこの場所に記録する。

## Review Focus

1. PID ファイルのない状態では成功として kill へ進まないこと（隔離実行で期限切れを検査）。
2. journal 記録と子起動の間が遅くても既存 assertion が通ること（遅延コピーで両テストを実行）。
3. 子の lock 継承と checkout 完了が保たれること（両テストの running/vanished/abandon assertion）。
4. kill と cleanup の対象がテスト所有のプロセスだけであること（既存 finally を保持し差分確認）。
5. SIGTERM の挙動を変えないこと（pr-review 全体の既存テスト）。

## Task 1: 既存の中断テストを PID ファイルで同期する

**Files:** Modify/Test: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`（wait helper と該当 2 テストのみ）。

**Interfaces:** Consumes: `stalling_git_env(tmp_path)` が書く `stalled-git.pid`、`wait_for_phase(...)`。Produces: テスト専用 `wait_for_stalled_git(tmp_path: Path) -> None`。

**テストの要否:** 必要。実際に起きたタイミング不具合の再発防止。新しい固定文言テストやメタテストは追加せず、既存の実 Git・プロセス・lock 検査を維持し、隔離遅延コピーで RED/GREEN を確認する。Spec/Plan の文章自体のテストは不要。

- [x] Step 1: Task の開始 SHA と brief を session ledger に記録する。基準版の test と helper を session 下に同じ相対配置でコピーする。コピー内の helper の `journal.record("worktree-add")` 直後に `time.sleep(0.5)` を挿入する。
- [x] Step 2: `uv run pytest <copy>/.agents/skills/pr-review/tests/test_pr_review_workspace.py -q -k 'test_killed_create_reports_its_last_phase_and_leftovers or test_abandon_waits_for_a_checkout_that_outlives_create'` を実行する。Expected: 両方失敗（running のはずが vanished、または abandon が still running を拒否しない）。実 helper は変更しない。
- [x] Step 3: テストファイルに `wait_for_stalled_git(tmp_path: Path) -> None` を追加する。PID ファイルの `is_file()` を monotonic deadline まで 0.05 秒ごとに調べる。期限切れは具体的な AssertionError。該当 2 テストの phase 待機の直後、kill の直前に呼ぶ。
- [x] Step 4: 修正したテストを隔離コピーに同期して同じコマンドを実行する。Expected: 2 passed。通常コピーでも該当 2 件を実行し、Expected: 2 passed。隔離実行で、ファイル無しの期限切れ（時計だけ制御）とファイル有りの成功を確認する。Expected: 期限切れは AssertionError、有りは正常終了。
- [x] Step 5: `uv run pytest .agents/skills/pr-review -q`、`git diff --check` を実行する。Expected: 全件成功・終了 0。テストファイルだけを明示 stage して `git commit -m "test: wait for checkout startup before killing create"`。Task 完了を ledger に記録する。
- [x] Step 6: README の非ワールド向け入口を worktree から実行する: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts`。Expected: 全コマンド終了 0。実 API の opt-in live check は無効にする。失敗は systematic-debugging で原因を調べ、同じ信頼性の失敗の再試行は 1 回まで。
- [x] Step 7: 基準 SHA からの diff と Spec/Plan/ledger を渡して、読み取り専用の独立したブランチ全体レビューを実施。重要な問題は 1 回の修正工程で RED/GREEN と全体検証、軽微な指摘は記録する。検証結果を文書へ追記し commit。
- [x] Step 8: Issue の open 状態・PR/claim/branch の競合を再確認。Gitleaks 検査後の SHA をそのまま `fix/issue-128-checkout-test-sync` に push。再確認後、`--repo usaturn/create-reso-world --base main` で `Closes #128` の PR を作成する。private Actions は確認対象外。PR URL と実在パス・所要時間を報告する。マージしない。

## 実行予算

- 能動時間 60 分。今回の準備開始（2026-10-18 03:38 JST）から数え、予算 ledger は 03:39 頃からの計測との差も最終記録に含める。1 Task の最小修正に加え全体テストとレビューを含むため。
- phase 目安: 準備・設計 12 分、再現・実装 8 分、全体検証 20 分、レビュー 10 分、公開・記録 10 分。
- worker は読み取り専用の同期呼び出し。目安 10 分、保存予約枠 2 分、無進捗 5 分。ランタイムに停止 API が無いため事前宣言した強制打ち切りは適用せず、同期終了を待つ。検証コマンドも中断しない。
- 同じ信頼性の失敗は再試行 1 回まで（2 回発生で方法変更）、安全の失敗は即時全体停止。最初の builder check は scope 欠落で開始を拒否され、明示 scope を付けた 1 回の再呼び出しで終了した。テスト失敗とは区別する。
- checkpoint: phase 境界、予算 50%・100%、失敗直後。100% で自動延長せず停止。RED の意図した失敗は受け入れ条件の証拠として記録し、信頼性失敗とは区別する。
- contingency: 遅延再現が不安定なら sleep を増やす前に実行された copy と kill の位置を調査する。全体検証の既知でない失敗は隠さず、範囲外の実装を無断で変えず停止。不要な負荷反復は行わない。
- PR 公開後、結果を本文・文書に転記し ledger を終了する。残存プロセス・必要な証拠がないと確認できた session を削除する。残す場合は絶対パスを報告する。

## 実行記録

- Spec builder check: nothing important left（読み取り専用）。
- baseline: pr-review 190 passed、exit 0、27.87 秒。
- 実装 commit: `a483c40`。遅延 RED は 2 failed（exit 1）、同一条件 GREEN は 2 passed（exit 0）。通常条件 2 passed。待機の期限切れ・ファイル有りの隔離実行も成功。
- 実装後 pr-review: 190 passed、exit 0、29.59 秒。
- README の全体検証: run-tests.bash 32/32 PASS、check-layout PASS、pytest 625 passed（167.37 秒）。すべて exit 0、再試行なし。実 API の opt-in live check は無効。
- `git diff --check` 成功。helper 本体・既存 assertion/cleanup は差分なし。
- 03:49 JST checkpoint: 約 11 分経過。受け入れ条件を満たしたため、読み取り専用のブランチ全体レビューと公開へ進む。
- ブランチ全体レビュー `50e4a6b..a34554c`: Critical・Important・Minor・判断見送りはすべて 0。追加修正なし。
- PR 公開済み: https://github.com/usaturn/create-reso-world/pull/142 。base `main`、head `fix/issue-128-checkout-test-sync`。自身の branch 以外の競合なし。Gitleaks は検出なし、検査済み SHA のみ push。この記録追記も push 前に再検査する。マージは未実施。
- Task 1: complete。実装・検証・独立レビュー・PR 作成を完了。draft は内容の未承認を表し、完了の証拠とは区別する。
- 実行予算の要約: ledger 開始 03:38:48 JST、03:52:27 時点の能動時間 819.63 秒、使用率 22.8%、安全失敗 0、信頼性失敗 0（意図した RED は除く）、期限超過 0。builder check 初回の scope 欠落は拒否後に修正して開始。task_watch による worker は起動していない。
- 全体所要は約 15 分。目安内訳: 準備・設計 4 分、再現・実装 1 分、全体検証 6 分、レビュー・確認 2 分、公開・記録 2 分。子の自己申告時間は加算していない。session は終了記録後に削除し、残る場合は最終報告へ明記する。
