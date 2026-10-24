# Issue #231 pr-review 系テスト削減 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pr-review` と `pr-review-fix-loop` のテストを、#228 と `AGENTS.md` の採用基準に沿って S・F∩S・D の代表へ整理する。

**Architecture:** 二つのスキル領域のテストを独立に整理し、Spec の棚卸し表で各テストの採否を追跡する。最後に両領域を一緒に実行し、残す高い守りの代表を使い捨てコピーで確かめてから全体検証と前後計測を行う。現行のサブコマンド・JSON と、後片付けで使う version 7 の読取を維持する。

**Tech Stack:** Python 3.14、uv、pytest、git、bash。

**Spec:** `docs/superpowers/specs/2026-10-24-create-reso-world-issue231-pr-review-tests-design.md`。

状態: draft。実行許可は利用者の `$issue-to-pr #231 --merge`。内容の承認を意味しない。

## Global Constraints

- #228 の決定と `AGENTS.md` の F / F∩S / L / S / D を適用し、S の件数を数合わせのために減らさない。迷うものは残して表に書く。
- 変更先は #231 の「変えてよいもの」に限る。`tools/test_support/`、ルートの `conftest.py`、`.agents/scripts/`、他スキルと担当のファイルを変えない。
- 旧 API は呼び出し元の無いことを確かめられた場合だけ撤去する。`repo-cleanup-after-merge` が使う `sessions` と version 7 の読取は保持する。
- テストに `--basetemp` を指定する場合は worktree の外に置く。Python コマンドは `uv` を使う。
- すべての変更は `/workspaces/reso-world/.worktrees/issue-231-pr-review-tests` で行い、ログ・使い捨ての検証ファイルは親 checkout の `tmp/agents/issue-231.qhu0z91i/` か `/tmp` の一意のディレクトリに置く。
- PR は `usaturn/create-reso-world` の `main` 向け。push 前の Gitleaks 検査を通し、`--merge` の結果は pr-review-fix-loop の `finalize.py` だけに委ねる。

## Review Focus

| 観点 | Task と検証 |
| --- | --- |
| 開いた PR や別リポジトリの同番号 PR を後片付け可能と誤判定しない | Task 2 の `sessions` 代表テスト、Task 3 の高い守りの確認 |
| HEAD が動いた後のレビューを保存・再利用しない | Task 1・2 の HEAD 代表テスト、Task 3 の領域テスト |
| 他 run のロック、worktree、記録を片付けない | Task 1・2 の所有範囲の代表、Task 3 の使い捨てコピー |
| 0 人の受理済みレビュアーや未停止の試行を成功扱いしない | Task 1 の reviewer/state の代表、Task 3 の領域テスト |
| version 7 の読取・version 6 の保守的拒否が後片付け手順と一致する | Task 2 の旧 session の代表と Task 3 の参照・構造確認 |

## 実行方式

`implement_task.py check` の結果は `agents:[self]`、`self:true`、fallback 無し。二つのテスト領域は担当ファイルが分かれ、判断の文脈を Spec と Task に渡せるため、`superpowers:subagent-driven-development` で Task 1・2 を**順に**依頼し、各 Task の確認を済ませてから次へ進む。統合と外部への公開は controller が担当する。共有する分類基準・棚卸し表・ログの意味は Task 3 で一括照合する。作業者が別であっても同じファイルを同時に編集しない。

## 実装前の要件照合

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 514 件の全テストに分類と理由を残す | 1・2・3 | 棚卸し表の件数が着手時の収集数と一致 | AST/pytest の収集一覧と表を突合 |
| F・L・余分な D と専用 fixture を消す | 1・2 | 差分に削除の根拠があり、参照切れがない | `rg`、ruff、領域 pytest、`git diff` |
| S・F∩S と正例を保持する | 1・2・3 | 拒否と正常例の両側が残る | 残すテスト、使い捨てコピーでの高い守りの確認 |
| 現行入口と版 7 の読取を守る | 2・3 | `review_run.py`、`sessions` の呼び出し元が継続 | 参照元検索、領域・全体検証 |
| 前後計測・PR・`--merge` | 3・公開 | commit 済み HEAD の数値と検証の記録、PR とループ結果 | Issue の計測コマンド、Gitleaks、PR/loop の結果 |

Task 1 と Task 2 は異なるディレクトリを担当するが、F/L/S/D の解釈と「成功と報告してよい状態」は共通する。controller が Task 3 で統合判断を行う。#231 の範囲外ファイルが必要になった場合は変更せず、理由を Spec と報告へ記す。

### Task 1: pr-review-fix-loop のテストを整理する

**Files:** `.agents/skills/pr-review-fix-loop/tests/` の既存ファイルだけ。Spec・Plan は controller が扱う。

**Interfaces:** `loop.py` の現在のサブコマンド、JSON、ロック、レビュアーの照合を変更しない。Task 2 とのコード依存は無い。Spec の棚卸し表にある F∩S・S・D・L を作業の根拠にする。

**テストの要否:** S・F∩S の既存テストを残し、同じ守りの D の代表と正例を保つため必要。新しい固定値・L のテストは書かない。消すテストの確認は pytest の実行と静的解析で代える。

- [x] **Step 1:** Spec の loop 側の全関数と parametrize の分類を読み、削除する L・D と残す S の代表を確定する。`test_pr_review_fix_loop_skill_contract.py` の権限の守りを残す。
- [x] **Step 2:** `test_loop_herdr_pane.py` などの L を削除し、同じ守りの重なりを代表へ縮める。`conftest.py` の `no_herdr` は残し、消したテストだけが使う fixture/import だけを消す。
- [x] **Step 3:** `uv run --locked pytest .agents/skills/pr-review-fix-loop` と `uv run ruff check .agents/skills/pr-review-fix-loop/tests` を実行し、終了コード 0 を確認する。`git diff --check` と差分で境界を確認する。
- [x] **Step 4:** 明示した loop のテストファイルだけ stage し、`test: reduce pr-review-fix-loop coverage to safety guards` で commit する。

### Task 2: pr-review のテストを整理する

**Files:** `.agents/skills/pr-review/tests/` の既存ファイルだけ。旧 API のコード撤去は、呼び出し元の無さを十分に確かめられた場合だけ別の判断として controller が扱う。

**Interfaces:** `review_run.py prepare/complete/fail`、`pr_review_workspace.py` の現行入口・`sessions` と version 7 の読取を変えない。Task 1 が残した loop のレビュアー照合が依存する pair の保存と cleanup を維持する。

**テストの要否:** 誤った PR、HEAD、保存先、Git の共有状態、利用者ファイルの削除を防ぐ S と、書込許可の F∩S の既存テストが必要。F/L/D の余りは消し、通常実行、静的解析、参照先の確認で代える。

- [x] **Step 1:** Spec の pr-review 側の分類と、旧 API の非テスト呼び出し元を照合する。`repo-cleanup-after-merge` が使う `sessions` と version 7 の読取のテストを残す。
- [x] **Step 2:** F/L/D の余りとその専用 helper/import を消し、parametrize を守りごとの代表へ縮める。拒否を残した守りには正常例も残す。API と JSON の変更はしない。
- [x] **Step 3:** `uv run --locked pytest .agents/skills/pr-review` と `uv run ruff check .agents/skills/pr-review/tests` を実行し、終了コード 0 を確認する。`git diff --check` と差分で境界を確認する。
- [x] **Step 4:** 明示した pr-review のテストファイルだけ stage し、`test: reduce pr-review coverage to safety guards` で commit する。

### Task 3: 守りの確認、統合検証、計測と公開準備

**Files:** 本 Spec の検証と計測の節、Plan の完了記録。テストの修正が必要なら Task 1・2 の担当に戻す。

**Interfaces:** Task 1・2 のコミット済み結果を統合し、#231 の受け入れ条件を条件単位で確認する。検証した HEAD と clean な作業ツリーをループの再利用可能な記録へ結び付ける。

**テストの要否:** 追加テストは不要。残す S の実効性は既存テストを使い捨てのコード変異へ当てて確認する。全体は指定のコマンドで実行する。

- [x] **Step 1:** 棚卸し表と収集一覧を突き合わせ、全テストの分類が一度ずつあり、残す拒否には正例があることを確認する。Task 間で同じ守りを消していないか確かめる。
- [x] **Step 2:** 高い守りで D の代表へ絞った経路を、`/tmp` の `mktemp -d` に作った使い捨てコピーで 1 か所ずつ壊し、残した代表テストが失敗することを確かめる。失敗した変異、対象テスト、観測結果を Spec に記録する。検出しない守りは代表を戻すか「迷い」として残す。
- [x] **Step 3:** `uv run --locked pytest .agents/skills/pr-review .agents/skills/pr-review-fix-loop`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` を実行し、実ログ・終了コードを保存する。`git diff --check` と `uv run ruff check` の対象を確認する。
- [x] **Step 4:** テスト変更の commit 済み状態で件数・行数を再計測し、Spec・Plan に前後と守りの確認結果を記録して commit する。最後の文書 commit の HEAD と clean な作業ツリーで必要な検証を再実行し、`finalize.py --checks-file` 用の記録をセッションディレクトリに作る。文書 commit がテストの収集対象を変えていないことを `git diff` で確かめる。
- [x] **Step 5:** Issue の状態・競合を再確認し、`scripts/scan-before-push.sh` が検査した SHA を push する。`gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-231-pr-review-tests` で `Closes #231` の PR を作る。`--merge` のループは親 checkout のスキルで開始する。

### Task 4: PR #255 サイクル 1 の指摘を反映する

**テストの要否:** CLI の担当指定、非ログの機密保持物、マージ状態の `false` は、壊れてももっともらしい誤記録が残る S。CLI・診断・マージ状態の独立ケースだけを戻し、共有 ref の同じ守りを重ねた 8 ケースは D として削る。未使用補助、Plan の表示、Issue への計測はテスト不要で、参照検索・差分・API 読取で確かめる。

- [x] **Step 1:** 4 レビュアーの 7 件を指定 HEAD の隔離コピーで確かめ、確認済み一覧を保存する。
- [x] **Step 2:** `claude-opus` 担当に独立した S の代表と D の縮約を依頼し、担当の停止・コミット差分・領域テスト・変異検証を確認して取り込む。
- [x] **Step 3:** 専用 worktree で全体・bash・配置・Ruff を再実行し、Spec の一覧・前後計測と Plan の実行状態を更新する。変更ファイルと `git diff --check` を確かめる。
- [ ] **Step 4:** `run_roles.py` の自己レビューと修正確認を 1 回行い、指摘を判定する。Gitleaks の検査した SHA を既存 PR へ push し、判断の記録を付けて状況を投稿する。

## 実行予算

- 能動時間の予算: 420 分。514 件と 2 スキルのテスト整理、全体検証、最大 3 サイクルのレビュー修正ループを含める。着手時に置いた 240 分の記録は Plan 作成前に予算を見直し、`tmp/agents/issue-231.qhu0z91i/budget-initial.jsonl` として残した。以後は同じディレクトリの `budget.jsonl` を使う。
- phase の目安: 調査・Spec・Plan 35 分、Task 1 55 分、Task 2 85 分、統合・検証・PR 65 分、ループ 180 分。ループは 3 ×（レビューの期限 45 分 + 計画・修正 15 分）を目安とし、合計 420 分。
- 共有 worktree に書く実装担当は停止の対象にしない。Task ごとに 90 分を checkpoint とし、20 分の予約枠を検証・記録に充てる。15 分の無進捗は状況を確かめる目安で、勝手に kill しない。ループのレビュアー期限は設定の 45 分、停止確認はループの手順に従う。
- 同じ信頼性失敗の再試行は 1 回まで。安全の失敗は再試行せず全体停止。worker が失敗した直後、各 Task の終了、50%・100% の時点で `issue_budget.py show` と checkpoint を記録する。100% に達したら止め、必要な追加予算を報告する。
- 進捗が増えないときは、削除候補を「迷い」として保持し、既に分類した S の守りと必須の検証に集中する。受け入れ条件の変更、新 Issue の切り出し、未検証のマージは独断で行わない。

## 完了

PR #255 を公開し、`--merge` のレビュー修正ループを実行中。Task 1 は初回約 9.7 分、Task 2 は初回約 31.8 分。Task 3 は公開前約 53 分（08:14–09:07 UTC。棚卸し・変異確認が約 24 分、統合検証が約 18 分、独立レビューと修正が約 11 分）。Task 2 の最後の 8.5 分は Task 3 と並行し、全体の所要時間へ二重計上しない。サイクル 1 の確認担当は約 7.3 分、実装担当は約 14 分。公開以降の全体内訳は最終報告に記す。

- Task 1 のサイクル 1 修正後: 234 → 114 件、4,381 → 3,552 行。初回レビューで外側の runner 失敗と adapter の成功報告を別の S と確認し各 1 ケースを復元した。PR のサイクル 1 で CLI 引数、非ログの機密パス、false のマージ状態という独立条件を 4 ケース復元し、不要になった補助を削除した。
- Task 2 のサイクル 1 修正後: 280 → 173 件、4,449 → 3,749 行。missing ref、request の無い記録の来歴、resolver 前の ghost 記録を独立した S として残した。PR のサイクル 1 で共有 ref の 5×2 の組み合わせを 1×2 に縮めた。
- 統合の計測: 514 → 287 件（227 件、44.2% 削減）、8,830 → 7,301 行（1,529 行、17.3% 削減）。269 関数と 514 収集件数を棚卸し表と突合し、未対応・重複・削除済み関数の誤記は 0 件。修正後の最終計測は `7924043` のコミット済みテストで実行した。
- 高い守りの確認: `/tmp` の使い捨て worktree で 32 か所を 1 つずつ変更し、31 件は代表テストが失敗した。残る 1 件は既存 lock の fixture だけでは検出しなかったが、同じ実装変更を別の代表が検出し、lock 削除の変異は lock 保存の代表が検出した。独立レビューで戻した 2 ケースも通常版では通り、対応する判定を外した版で各 1 件失敗した。Spec に全件の結果を記録した。
- 最初のテスト変更後の commit `fdc525c` で領域 pytest は **289 passed / exit 0**、全体 pytest は **1,501 passed / exit 0**、bash は **23 tests / exit 0**、配置検査と `git diff --check` は **exit 0**。Ruff は project 環境に無かったため、合意済みの代替 `uvx ruff check .agents/skills/pr-review/tests .agents/skills/pr-review-fix-loop/tests` を実行し **exit 0**。実ログは `tmp/agents/issue-231.qhu0z91i/` の `combined-domain-final.log`、`full-pytest-final-code.log`、`bash-suite-final.log`、`check-layout-final.log`、`ruff-final2.log`。レビュー後のテスト commit `a28ad4e` で領域 pytest は **291 passed / exit 0**（`combined-domain-post-review.log`）、対象 2 ケースと Ruff も **exit 0**。文書 commit 後の全体検証を続ける。
- PR サイクル 1 のテスト変更は `7924043`。独立確認で 7 件すべてを現行 HEAD に照らして確かめ、実装担当の使い捨てコピーで CLI・診断・マージ状態・共有 ref の変異による検出力を確認した。領域は **287 passed / exit 0**、全体は **1,499 passed / exit 0**、bash は **23 tests / exit 0**、配置と Ruff は **exit 0**。各ログは `tmp/agents/issue-231.qhu0z91i/` に保存した。
- 最終 HEAD、領域・全体・bash・配置・lint の結果、公開とレビュー修正ループの結論は、終了時のセッション記録と PR 本文に記載する。
