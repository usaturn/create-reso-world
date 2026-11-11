# Issue #396 / PR #412 レビュー修正 Spec（サイクル 1・結論 2: 修正不要）

- 状態: `completed`
- 日付: 2026-11-12
- PR: https://github.com/usaturn/create-reso-world/pull/412（usaturn/create-reso-world・base `main`）
- レビュー対象 HEAD: `3c8cb52c9c2ead6ef45bf4810f9f48833532f8e1`
- 実行許可: issue-to-pr #396 `--merge` のループ（pr-review-fix-loop）の計画フェーズ。review-fix-planning 完遂の依頼（ループが委譲）。マージは `finalize.py` が行う
- 既存 Spec・Plan: `docs/superpowers/specs/2026-11-12-issue-396-monitoring-deadline-test-design.md`・`docs/superpowers/plans/2026-11-12-issue-396-monitoring-deadline-test.md`（本 PR に同梱・draft）

## 全指摘の一覧と 3 区分

指摘 0 件（両レビュアーとも active findings 0・Unverified candidates なし・Test suggestions なし）。

- 解消済み: 0 件
- 対応する: 0 件
- 対応しない: 0 件

確認済みの一覧（`verified/`）は作成していない。指摘が 0 件で検証対象の指摘が無く、review-verify（mode cycle）の実行対象がないため。planner によるコミット済み内容の確認（下記）と両レビュアーの実行検証で代える。

## 要件対応（PR の約束と既存 Spec・Plan の照合）

PR の約束（Issue #396 受け入れ条件 1〜4）と検証証拠の対応。今回の修正は無い（結論 2）。

| 条件 | 観測する結果 | 検証方法と証拠 |
| --- | --- | --- |
| 1. 固定秒数に依存しない「期限後も生存」の確認 | worker は hold/deadline 記録前に終了しない | 両レビュアーが SIGSTOP/SIGCONT ハーネスで実行確認（旧 worker は誤失敗再現・新 worker は 3 秒/8 秒停止でも hold/deadline 記録）。controller の RED/GREEN（repro-old-2.log・repro-green.log） |
| 2. 終了優先仕様との整合・守りを弱めない | task_watch.py・テスト本体・SKILL.md 無変更 | `git diff base..HEAD` で無変更を確認（planner・両レビュアー）。monitoring スイート 25 passed |
| 3. 単独・並行での安定性 | 反復・並行負荷で成功 | controller: 30/30 反復・並行全体スイート。レビュアー: 10/10・15/15（CPU 負荷下）・並行負荷 |
| 4. #345 との分離・参照可能性 | 変更は fake worker と文書に閉じる | PR 本文「#345 への参照」節。マージ後に Issue コメントで結果を共有（本 Spec の完了後） |

共有条件の統合担当: planner（controller）。worker と watcher の同期（events.jsonl・state ディレクトリ）は条件 1 のハーネスで端到端に確認済み。

## 守る条件と影響経路

「対応する」項目が無いため作成しない（0 件）。

## 同じ条件の再発と設計の見直し

きっかけに当たる項目なし（初回サイクル・修正なし）。

## 検証（結論 2 の手順 1〜2）

PR head `3c8cb52c` は base `7e2d1a89` に基づく。計画の base 再取得で `origin/main` が `189f64e8aeffcbbb3b25d847c94ae75db38136cc`（PR #411 のマージ）へ進んだため、head に新 base を merge した隔離ツリー（`/tmp/review-fix-planning.pLKU4Z/worktree`・merge commit `66ea20d6a5f58a375575a490e068866b30866643`・push しない）で検証し直した。

隔離ツリーでの実行（cwd: 隔離 worktree）:

| コマンド | 結果 |
| --- | --- |
| `env -u CODEX_THREAD_ID uv run pytest .agents/skills/monitoring-long-tasks -q -p no:cacheprovider` | 25 passed (12.20s)・exit 0 |
| `bash scripts/check-layout.sh` | PASS・exit 0 |
| `env -u CODEX_THREAD_ID uv run pytest tests/skills .agents/skills .agents/scripts tools -q -p no:cacheprovider`（run-tests.bash と並行） | 1462 passed (653.71s)・exit 0・warnings なし |
| `bash .devcontainer/run-tests.bash`（全体スイートと並行） | 27 test(s) PASS・exit 0 |

検証の記録（`finalize.py --checks-file`）: head `3c8cb52c9c2ead6ef45bf4810f9f48833532f8e1`・base `189f64e8aeffcbbb3b25d847c94ae75db38136cc`・上記コマンドと終了コード。ログ: `tmp/agents/issue-396.z5hf2du1/verify-*-merge.log`。

（参考）PR head 単体（base 7e2d1a89）での検証も実施済み: 1456 passed（並行）・27 PASS・25 passed・check-layout PASS（`verify-pytest-rebase.log` ほか）。base 前進により merge ツリーの検証を正式な記録とする。

## レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| qwen4-max-preview.md | qwen4-max-preview | pi | 3c8cb52c9c2e | はい（Initial） | Approve |
| claude-sonnet-5-5.md | claude-sonnet-5-5 | claude-code | 3c8cb52c9c2e | はい（Initial） | Approve |

- planner: qwen4-max-preview（ランタイム: claude-code・司令塔 self）
- サイクル: 1（前の判断の記録なし）
- 入力から外したファイル: なし（findings/・runs/ はレビュアーではないため seats に含めない）
- 両レビュアーとも Issue 受け入れ条件 1〜4 を実行検証で確認。piaq（pi_alibaba_qwen4-max_max）は今回のレビューで結果を正常に回収（Spec レビュー 1 回目の response_failed は再現せず）

## 結論

**結論 2: 修正不要としてマージする。** 対応する 0 件・全指摘（0 件）と変更ファイル全文・関連処理（task_watch.py の decide/record/_run・回収・停止確認、テスト本体）の確認済み。マージ・closing Issue（#396）の更新は `finalize.py --spec-commit` が行う。

- 自己レビュー: 未実施（結論 2 のため）
- 修正・自己レビューの担当: なし（run_roles.py 未実行）
- 実行した検証: 上記「検証」節（隔離 merge ツリー）
- 残作業: マージ後の Issue #345 への結果コメント（参照 Issue・PR 本文で言及）
