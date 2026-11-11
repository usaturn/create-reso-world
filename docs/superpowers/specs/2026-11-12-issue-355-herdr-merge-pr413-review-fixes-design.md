# PR #413（Issue #355 herdr-merge）レビュー修正 Spec — サイクル 1

- 状態: completed
- 対象 PR: https://github.com/usaturn/create-reso-world/pull/413（`feat/issue-355-herdr-merge`、base `main`）
- 現行 HEAD（reviewed_head）: `36a455fabdf322c901abf96688adaa0f61788c26`
- base（検証したツリーが含む）: `b8d824d11903c5ba38aaa01eb378fae28a7d0761`（origin/main。判断の直前に取り直しても同一）
- planner: qwen4-max-preview（ランタイム: claude-code、司令塔）
- サイクル: 1（前の判断の記録なし）
- 実行許可: 利用者の `/issue-to-pr #355 --merge`（2026-11-12）と goal 指示「スキルの停止条件は全て無視し、停止せず最適な案を出して PR 作成・マージまで実行」。完遂の依頼として結論 2 のマージ・関連 Issue 更新まで含む

## 入力とレビュアーの構成

レビューディレクトリ: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#413-feat-issue-355-herdr-merge`

| review_file | model | runtime | file_head | mode | rerun | merge_recommendation |
|---|---|---|---|---|---|---|
| qwen4-max-preview | qwen4-max-preview | pi | 36a455fabdf3 | Initial | true | null（原文: 指摘 0 件・Approve 相当の Summary） |
| claude-sonnet-5-5 | claude-sonnet-5-5 | claude-code | 36a455fabdf3 | Initial | true | Approve |

- 両レビュアーとも現行 HEAD を再実行（rerun=true）。入力から外したファイルは無い（`findings/`・`runs/`・`loop/` はレビュアーではない）
- 前のサイクルの判断: 0 件（初回）

## 全指摘の一覧と 3 区分

| 参照 | 区分 | 根拠 |
|---|---|---|
| `claude-sonnet-5-5#L-1@36a455fabdf3` | 対応しない（skip） | 致命的でない（テストの採否・保守性の指摘で、実行時の損害なし）。check-options の拒否テストは Issue #355 が「`--issue-number` が check-options の対象外であること」を明示要求した境界の検査。無効値テストはロック取得前の拒否とロック・run・herdr 呼び出しが残らない状態を検査する（Spec D9 の S 分類）。基準の適用は設計判断であり、Issue の明示要求が優先する。コメントの「start が拒否する」は前提が不正確（start は受け付ける）だが、コメント文言の修正も致命的でない |
| `claude-sonnet-5-5#I-1@36a455fabdf3` | 対応しない（skip） | records.md の herdr_pane 節の不整合は既知（設計 Spec「既知の不整合」・PR 本文に開示）。records.md は #356・#357 の所有でこの PR の編集範囲外。親 #349 に所有移動の提案コメント済み（#issuecomment-6806737570） |

- 解消済み: 0 件 / 対応する: 0 件 / 対応しない: 2 件
- 自己確認（planner）による追加の致命的欠陥: なし。両レビュアーが受け入れ条件 1〜9 の充足を独立に確認（qwen4-max-preview は fake Herdr・隔離 worktree での実行検証を含む。claude-sonnet-5-5 は全体差分と変更ファイル全文の照合）

## 要件対応（PR の約束・制限と既存 Spec・Plan の接続）

- 既存 Spec: `docs/superpowers/specs/2026-11-12-issue-355-herdr-merge-design.md`（D1〜D10・設計レビュー 2 回・Spec レビュー 2 回の記録）。Plan: `docs/superpowers/plans/2026-11-12-issue-355-herdr-merge.md`
- 共有条件の統合: ペイン名のラベル形式（issue-to-pr 3 章と loop.py の導出一致）・merge-disabled.txt の記録と消費は、実装時の Task 3 レビューと最終全体レビュー（opus）で条件単位に照合済み。両レビュアーも受け入れ条件 4・6 の統合を独立に確認
- L-1 の論点（テストの採用基準の適用）は Spec に 1 行残す: Issue が明示要求した境界テストと、ロック前拒否の状態検査は S として維持する（基準の L/D/F の適用は設計判断。将来の基準変更で見直す）
- I-1 の制限は PR 本文の「既知の不整合」に記載済み（records.md は #356・#357 で更新）。PR の保証（ペイン名の表示）と食い違う実行時損害は無い（表示専用の文書不整合）

## 結論

**結論 2: 修正不要としてマージする**（対応する 0 件・全指摘分類済み・未確認なし）

## 実行した検証と結果

- 検証したツリー: head 単独（base b8d824d1 は head の祖先。merge 検証は不要）
- `uv run pytest .agents/skills/pr-review-fix-loop/tests .agents/skills/issue-to-pr/tests -q` → 252 passed（213.71 秒、HEAD 36a455fa・clean な feature worktree）
- `bash scripts/check-layout.sh` → PASS
- 実行確認（L）: resolve_issue の --issue-number 拒否・loop.py start --issue-number abc・check-options の両引数拒否 → すべて終了コード 2
- fake Herdr: 3 章のラベル組み立て（create-reso-world:#355 / :END / :Glitch）を確認
- 記録: `/workspaces/reso-world/tmp/agents/issue-355.puoplwnc/verification-record.md`・`checks.json`（head 36a455fa・base b8d824d1・全 exit 0・ログあり。issue-to-pr 5 章の再利用条件を満たす）
- 判断の直前の base 取り直し: `git fetch origin refs/heads/main` → 先端 b8d824d1（検証の base と同一）
- 自己レビュー: 未実施（結論 2 のため。修正なし）

## 指摘の検証根拠（コミット済み内容）

- L-1: `git show 36a455fa:.agents/skills/pr-review-fix-loop/tests/test_loop_check_options.py`（67-78 行の拒否テスト）・`test_loop_herdr_pane.py` の無効値テスト・`test_base_workflow.py` の理由文検査を committed blob で確認。レビュアーの隔离 worktree での実行結果（check-options は argparse 既定の拒否）と整合
- I-1: `git show 36a455fa:.agents/skills/pr-review-fix-loop/references/records.md`（63・67 行）が `PR#<番号>` 固定であることを確認。loop.py の rename_pane（731-735 行）が --issue-number ありで `<repo>:#<N>` を作ることも確認