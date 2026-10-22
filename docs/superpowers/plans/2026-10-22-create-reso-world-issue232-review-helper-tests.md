# Issue #232: レビュー補助のテストを新しい採用基準で減らす Implementation Plan

## 管理

- 状態: draft
- Spec: `docs/superpowers/specs/2026-10-22-create-reso-world-issue232-review-helper-tests-design.md`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/232（親 #228）
- worktree: `/workspaces/reso-world/.worktrees/issue-232-review-helper-tests`（branch `feat/issue-232-review-helper-tests`、基準 `481a047`）
- セッションディレクトリ: `/workspaces/reso-world/tmp/agents/issue-232.ni5kw2fx`（ledger `budget.jsonl`、担当ごとの棚卸しの断片）
- 実行方式: `superpowers:subagent-driven-development`。Task 1〜5 を並行（ファイルが重ならない）、Task 6 はその後、Task 7・8 は controller。理由は Spec の D-232-2・D-232-3

## Global Constraints

- 方針は #228 の「利用者の決定」「削除と採用の基準」と `AGENTS.md` の「テストの採用基準」。議論し直さない。気付けない損害を防ぐテストは、数を合わせるために消さない。迷うものは残して「迷い」と書く
- 変えてよいのは Spec の設計 1 の範囲だけ。`tools/test_support/`・ルートの `conftest.py`・`pyproject.toml`・`AGENTS.md`・`pr-review`・`pr-review-fix-loop`・`scripts/superpowers_context.py` は変えない
- 担当は commit・push しない。テストは同期実行する。`/tmp` に固定名のファイルを作らず、削除の変数には `${VAR:?}` を付ける
- 担当が返すもの: 棚卸しの断片（Markdown の表。テストの群ごとに 分類・理由。S は損害と重さ、撤去は根拠）、前後の件数と行数、撤去したコードの一覧、重さが高の守りの確認結果

## 要件と Task・検証の対応

| Spec の条件 | Task | 検証 |
| --- | --- | --- |
| 受け入れ 1（棚卸し） | 1〜6 の断片を Task 7 で Spec に統合 | 全テスト関数が表のどこかの群に入っていること（担当が収集名の一覧と突き合わせる） |
| 受け入れ 2（消す） | 1〜6 | 領域の pytest が通り、`ruff` の未使用 import が無い |
| 受け入れ 3（高の守りの確認） | 1〜6 の各担当 | 使い捨てのコピーで、残したテストが失敗した記録 |
| 受け入れ 4・5 | 7 | 全体の入口と計測 |

## 実行予算

- 全体: 能動時間 360 分（担当 6 つの並行の実行 120 分、統合・検証 60 分、PR 作成 30 分、ループ 3 サイクル × 約 45〜50 分）
- phase の目安: 準備 30 分、実装（Task 1〜6）150 分、統合・検証 60 分、PR 30 分、ループ 90 分
- worker: 絶対期限 90 分、無進捗 20 分。再試行の上限は同じ失敗につき 1 回（信頼性）。安全の失敗は全体停止
- checkpoint: Task 1〜5 の完了後、Task 6 の完了後、予算の 50%・100%、worker の失敗の直後
- 縮小・切り出し: 担当が期限内に終わらないファイルは、その時点で分類を終えた群だけ消し、残りを持ち越し候補として Spec と PR に書く

## Task 1: `test_review_findings.py`（`.agents/scripts/tests/`、231 件）

- 担当ファイル: `.agents/scripts/tests/test_review_findings.py`、`.agents/scripts/review_findings.py` と `.agents/review-findings.md`（撤去だけ）
- 注意: `.agents/skills/review-verify/tests/test_dispatch.py` が読み込む factory（`document_v2`・`fix_check` など。`grep` で全て確かめる）は残す。統計・出所の分析（約 370 行）、statement の候補の推定（約 300 行）は損害が低の候補
- テストの要否: 消す作業。残すテストの追加は不要。検証: `uv run --locked pytest .agents/scripts/tests/test_review_findings.py .agents/skills/review-verify`

## Task 2: `test_review_records.py`（205 件）

- 担当ファイル: `.agents/scripts/tests/test_review_records.py`、`.agents/scripts/review_records.py` と `.agents/review-records.md`（撤去だけ）
- 注意: 有効な変種 12 件と往復は L、`INVALID_RECORDS` 75 件は 10 件ほどの代表、`VALID_VARIANTS`・`EMPTY_STATE` は使われなくなれば消す
- 検証: `uv run --locked pytest .agents/scripts/tests/test_review_records.py .agents/skills/review-fix-planning`

## Task 3: `test_review_target.py`・`test_agent_tmp.py`・`test_issue_budget.py`・`test_evaluation.py`（計 106 件）

- 担当ファイル: `.agents/scripts/tests/test_review_target.py`・`test_agent_tmp.py`・`test_issue_budget.py`、`.agents/skills/review-verify/tests/test_evaluation.py`（`conftest.py` は Task 6 が整理）、対応するコード（撤去だけ）
- 注意: `review_target` の fork と上流の振り分けと clone しないこと、`agent_tmp` のパスの脱出の拒否は S。`issue_budget` の CLI の 3 件は L
- 検証: `uv run --locked pytest .agents/scripts/tests/test_review_target.py .agents/scripts/tests/test_agent_tmp.py .agents/scripts/tests/test_issue_budget.py .agents/skills/review-verify/tests/test_evaluation.py`

## Task 4: `test_finalize.py`（169 件）

- 担当ファイル: `.agents/skills/review-fix-planning/tests/test_finalize.py`、`finalize.py`（撤去だけ）
- 注意: 未検証の head・base、CI、base の移動、merged の状態（#207）、再実行で重複コメントしない、ほかの Issue を close しない、は S。spec commit の比較 30 件は 4 件ほどの代表
- 検証: `uv run --locked pytest .agents/skills/review-fix-planning/tests/test_finalize.py`

## Task 5: `test_run_roles.py`・`test_upsert_pr_comment.py`・`test_review_fix_planning_skill_contract.py`（計 194 件）

- 担当ファイル: `.agents/skills/review-fix-planning/tests/` の該当 3 ファイルと、`run_roles.py`・`upsert_pr_comment.py`（撤去だけ）
- 注意: skill_contract は F が中心（権限を決める frontmatter などの F∩S は残す）。upsert はほかの担当・信頼できない・引用した marker のコメントを書き換えないこと、全ページを読むことは S。run_roles の checkout の事前検査は `tools/agent_runner` のテストと重なるので消す。`TEMPLATE`（42 行）は使われなくなれば消す
- 検証: `uv run --locked pytest .agents/skills/review-fix-planning/tests`（Task 4 のファイルを除く）

## Task 6: `test_dispatch.py`・`conftest.py`（151 件。Task 1 の完了後）

- 担当ファイル: `.agents/skills/review-verify/tests/test_dispatch.py`・`conftest.py`、review-verify のコード（撤去だけ）
- 注意: 使えない保存先（#177）とレビューディレクトリの改ざんは、run_roles と dispatch の両方にあれば実装している側を残す。`test_review_findings.py` から読み込む factory は、使うものだけを残すか、本ファイルに移して読み込みをやめる（Task 1 の担当と調整せず、Task 1 の完了後に行う）
- 検証: `uv run --locked pytest .agents/skills/review-verify`

## Task 7: 統合と計測（controller）

- 断片を Spec の「棚卸し」に統合し、領域・全体の入口、`ruff`、`git diff --check`、`bash scripts/check-layout.sh`、計測を実行し、「検証の記録」と Issue に前後の数を書く。`README.md`・`docs/` に撤去した経路の説明が残っていれば行だけ消す
- 検証の記録（最後の commit の後の HEAD、`git status --porcelain` が空、argv・終了コード・ログ）を `PARENT_ROOT/tmp/agents/` に残し、`--checks-file` の形のファイルを作る

## Task 8: 最後の全体レビュー・PR・ループ

- ブランチ全体のレビュー（requesting-code-review）で、基準に反して消したもの（S を消した）と残したもの（L・F を残した）を点検する。push の前の検査、PR 作成（`Closes #232`）、`--merge` のループ
