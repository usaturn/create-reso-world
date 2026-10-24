# Issue #233 Skill Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 状態: draft。対象: `usaturn/create-reso-world`。利用者の実行指示: `$issue-to-pr #233 --merge`（2026-10-24）。内容の承認ではない。Spec のコミット: `e9a29381dd9d08255eefcc6ed529e062ac11ca2b`。

**Goal:** #233 が担当する 10 スキルと `tests/skills/` のテストを、気付けない損害を防ぐ代表だけに減らし、全テストの棚卸しと前後の計測を残す。

**Architecture:** テスト関数と理由を共有する parametrize 群を単位に、Spec の分類表どおり削除・縮約する。担当領域を 3 つのファイル群に分け、各群のテストとレビューを終えてから統合担当が相互の守り、計測、全体の実行結果を確認する。呼び出し元が無いと実証できないワールド保護経路と API の入出力は保つ。

**Tech Stack:** Python 3.14、pytest、uv、Bash、Git。Python コマンドは `uv` 経由で実行する。

**Spec:** `docs/superpowers/specs/2026-10-24-create-reso-world-issue233-skill-tests-design.md`

## Global Constraints

- 編集可能な追跡ファイルは Spec の「範囲と制約」に列挙されたものだけ。`AGENTS.md`、`tools/test_support/`、ルート `conftest.py`、`pyproject.toml`、`.devcontainer/run-tests.bash`、`README.md` の「テスト」、別の子 Issue の担当領域を変えない。
- F（F∩S を除く）、L、D の余りを削除する。S、F∩S、迷いは維持する。テストごとに損害と気付ける経路を Spec の棚卸しで説明する。件数のために S を削除しない。
- 拒否テストと正常に通る例を対に残す。同じ守りの組み合わせを網羅しない。`resolve_issue.py`、`implement_task.py`、`task_watch.py` の入出力と終了コードを変えない。
- 使われないと実証できない経路を削除しない。`repo-cleanup-after-merge` のワールド保護は現行 README と手順が参照しており、撤去しない。
- コミットしない検証・変異テストのコピーとログは `PARENT_ROOT/tmp/agents/issue-233.*` または `/tmp` の `mktemp -d` に置く。worktree 直下には置かない。

## Review Focus

各行は新規テストの要求ではない。Task 内で残す既存の S/F∩S と、統合で確認する振る舞いを示す。

1. `#N` の origin・対応リポジトリを取り違えず、許可外の対象を拒否する（Task 1 の resolver テスト）。
2. `allowed_files` の最終 tree、途中 commit、rename の移動元と先を監査する（Task 1 の runner テスト）。
3. 生きた Git の `index.lock`、symlink の参照先、ff merge の未追跡・ignored 内容を守る（Task 2 の Git テスト）。
4. detached 更新でローカル main、別 worktree、ワールドの追跡済みデータを動かさない（Task 2 の cleanup テスト）。
5. 未確認の停止を成功と記録せず、別 session のモデル名を採用しない（Task 3 の task_watch / pi-model-name テスト）。

## 実装前の要件照合

| Spec の条件 | 担当 Task | 観測結果と検証 |
| --- | --- | --- |
| 全テストの分類と理由 | Spec に全 254 関数を記録済み。Task 4 で差分と照合 | 対象の全テスト関数・parametrize 群の分類、S の重さ、D の代表がある |
| F・L・D の余りを削除し、S を残す | Task 1～3 | 各領域の pytest が通り、diff に範囲外の編集が無い |
| 高い守りの代表が実際に損害を検出する | Task 4 | `/tmp` の使い捨てコピーで一時的に壊した処理に対し、対応する既存テストが失敗する |
| 件数と行数、全体検証 | Task 4 | コミット済み状態の前後値、3 つの README 入口の終了コード 0、ログパス |

共有前提: Task 1～3 は同じ採用基準を用い、`tests/skills/` が他スキルの固定値を広く検査する。Task 4 の統合担当が、両側のテストと所有範囲を条件単位で照合する。API と操作順の変更はしない。

## 実行方式

`implement_task.py check` は既定の `self: true` を返した。3 つの Task は異なるテストファイルを担当し、各 Task の成果を独立に検査できるため、`superpowers:subagent-driven-development` で 1 Task ずつ順に実装・レビューする。並行編集はしない。Task 4 の統合、Spec の結果追記、最終検証と公開は controller が担当する。全体のブランチレビューを最後に行う。

## Task 1: issue-to-pr のテストを整理する

**Files:** `.agents/skills/issue-to-pr/tests/test_implement_task.py`、`test_implement_task_run.py`、`test_resolve_issue.py`。

**Interfaces:** 既存の `resolve_issue.py` と `implement_task.py` の public CLI、Pydantic model、JSON の形をそのまま利用する。ほかの Task へ API を提供しない。

**テストの要否と理由:** 既存の S/F∩S は残す。誤リポジトリの選択、担当外ファイルの取り込み、未確認停止、既定 `self` の破損はエラーなしに損害を残す。F/L/D の新規テストは書かない。

- [ ] Step 1: Spec の issue-to-pr 棚卸し表と実際の各関数・parametrize を照合する。分類が混在する関数は、S に当たる代表ケースだけに縮める。
- [ ] Step 2: F/L/D とされたテスト、残るテストから参照されない helper・fixture・import を消す。`allowed_files` の途中 commit・rename と、拒否に対する正常例を残す。
- [ ] Step 3: `uv run --locked pytest .agents/skills/issue-to-pr/tests` を実行し、終了コード 0 を確認する。`git diff --check` と担当 3 ファイルの diff を確認する。
- [ ] Step 4: この Task の 3 ファイルだけを stage し、`test: reduce issue-to-pr tests to safety guards` でコミットする。

## Task 2: Git ロック復旧とマージ後の片付けのテストを整理する

**Files:** `.agents/skills/stale-git-lock-recovery/tests/test_stale_git_lock_recovery_contract.py`、`test_ff_merge_keep_untracked.py`、`.agents/skills/repo-cleanup-after-merge/tests/test_detached_update.py`、`test_repo_cleanup_after_merge_contract.py`。

**Interfaces:** 既存のロック確認・解放 helper、`ff_merge_keep_untracked.sh`、cleanup 手順を使う。ワールド保護のコードと手順は維持する。

**テストの要否と理由:** 生きた保持者のロック削除、symlink の参照先削除、ignored 内容の消失、ローカル main の移動は S。操作禁止の固定値は F∩S。明示エラーで気付けるものと同じ守りの組み合わせは消す。

- [ ] Step 1: Spec の Git 領域表に従って F/L/D の関数を削除し、混在する parametrize を代表へ縮める。残る S の fixture を保持する。
- [ ] Step 2: `uv run --locked pytest .agents/skills/stale-git-lock-recovery .agents/skills/repo-cleanup-after-merge` を実行し、終了コード 0 を確認する。`git diff --check` と担当 4 ファイルの diff を確認する。
- [ ] Step 3: 担当 4 ファイルだけを stage し、`test: reduce git recovery and cleanup tests` でコミットする。

## Task 3: 監視・モデル名・スキル共通テストを整理する

**Files:** `tests/skills/test_skill_frontmatter.py`、`test_skill_packages.py`、`.agents/skills/monitoring-long-tasks/tests/test_task_watch_core.py`、`test_task_watch_process.py`、`fake_worker.py`、`.agents/skills/pi-model-name/tests/test_pi_model_name_contract.py`、`.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py`、`.agents/skills/planning-parallel-issues/tests/test_planning_parallel_issues_contract.py`、`.agents/skills/rst-writer/tests/test_rst_writer_contract.py`、`.agents/skills/herdr-agent-task/tests/test_herdr_agent_task_contract.py`、`.agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py`。

**Interfaces:** `task_watch.py` と `pi-model-name` CLI、各スキルの現行ファイルをそのまま参照する。`fake_worker.py` は残る process テストが使う限り保持する。

**テストの要否と理由:** 未確認停止・虚偽の完了・別 session のモデル名・`$ARGUMENTS` の誤展開は S/F∩S。文書やファイルの存在、JSON 形式の固定だけの検査は F/L。残る S に必要な fixture だけ維持する。

- [ ] Step 1: Spec のその他領域表に従い F/L/D を削除し、混在するテストは S の観測へ縮める。守りの実装側で残るテストとの重複を避ける。
- [ ] Step 2: `uv run --locked pytest tests/skills .agents/skills/monitoring-long-tasks .agents/skills/pi-model-name .agents/skills/agent-handoff .agents/skills/planning-parallel-issues .agents/skills/rst-writer .agents/skills/herdr-agent-task .agents/skills/simplify-in-subagent` を実行し、終了コード 0 を確認する。`git diff --check` と担当ファイルの diff を確認する。
- [ ] Step 3: 担当ファイルだけを stage し、`test: reduce skill package and monitoring tests` でコミットする。

## Task 4: 統合検証、計測、結果の記録

**Files:** `docs/superpowers/specs/2026-10-24-create-reso-world-issue233-skill-tests-design.md`。検証ログは `PARENT_ROOT/tmp/agents/issue-233.*`、使い捨てコピーは `/tmp` の `mktemp -d` に置く。

**テストの要否と理由:** 新規のテストは不要。Task 1～3 で残した S/F∩S を実行し、高い守りの代表が実際に損害を検出するかは使い捨てコピーの一時的な破損で確認する。件数・行数はテストの期待値にせず、計測して Spec に記録する。

- [ ] Step 1: 3 Task の diff と Spec の全件表を照合し、同じ守りの余分なテスト、削除したテスト専用の helper、担当外の変更が無いことを確認する。拒否と正常の両側、操作順の影響、各テストの独立した根拠を確認する。
- [ ] Step 2: 高い守りの代表へ絞った群から各 1 件を選び、`/tmp` に `mktemp -d` で作ったコピーの処理だけを一時的に壊し、残したテストが失敗する証拠を採る。対象、変更点、失敗したテスト名と終了コードを Spec に記す。実 worktree の実装は壊さない。
- [ ] Step 3: 領域の pytest と、`README.md`「テスト」の 3 入口（`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`）を同期実行し、各終了コードとログを記録する。
- [ ] Step 4: テスト変更のコミット後、#233 の「検証」に記された `pytest --collect-only` と `git ls-files ... | xargs -0 cat | wc -l` で件数・行数を測り、Spec に前後の値と削減率、残る重い守り、実行時間を追記する。
- [ ] Step 5: Spec だけを stage し、`docs: record issue 233 test reduction results` でコミットする。最終 HEAD で README の 3 入口を再確認し、`--merge` の checks-file に HEAD・clean status・argv・終了コード・ログパスを記録する。

## 実行予算

- Issue 全体の能動時間予算: 420 分。基準の領域テストが約 4 分、対象 17 テストファイル・254 関数、PR 後に最大 3 サイクルのレビューを回すため。
- 目安: 準備・Spec/Plan 30 分、Task 1～3 合計 125 分、統合・検証・計測 55 分、push/PR 15 分、ループ最大 195 分。時間の重なりと予備を含め 420 分。
- ledger: `/workspaces/reso-world/tmp/agents/issue-233.i98txoe1/budget.jsonl`。能動時間は `.agents/execution-budget.md` の定義に従う。
- 実装 worker の各 Task の絶対期限は 90 分、調査 75 分と成果保存の予約 15 分、無進捗 20 分。共有 worktree を編集する worker は時間だけを理由に強制停止せず、controller が生存・進捗・終了を監視する。レビュー worker の目安は Task ごと 20 分。ループのレビュー期限は既定の 45 分／サイクル。
- 同じ信頼性の失敗は再試行 1 回まで。安全の失敗は再試行せず全体停止。Task 境界、予算 50%・100%、失敗直後に `issue_budget.py show` と checkpoint を記録する。
- 予算不足時は S の削減で件数を合わせず、余分な F/L/D の調査を縮小する。受け入れ条件を満たせない場合は結果と残作業を残して停止し、勝手に新しい Issue を作らない。100% 到達は停止条件。

## 公開と完了の手順

1. 最後のブランチ全体のレビューを行う。`verification-before-completion` で終了コードと実ログを確かめる。必要な修正は担当 Task と検証に戻す。
2. push・PR 作成直前に Issue 状態、open PR、予約 ref、branch/worktree、先行 PR を再確認する。`scripts/scan-before-push.sh` で検査した HEAD SHA をそのまま push する。検査に失敗したら push せず、スキルの停止条件に従う。
3. `main` 向けの PR を 1 つ作り、本文に `Closes #233`、Spec の決定と理由、実行方式、検証、前後の計測、所要時間を書く。作成後に #233 へ計測と状態をコメントする。
4. `pr-review-fix-loop` の既定設定でレビュー修正を回す。`finalize.py` が修正不要と検証した場合だけマージする。PR の直後に予約を解放しない。ループの結果と次の作業を #233 に記録した後、保存した SHA の lease で自分の claim だけ解放する。
