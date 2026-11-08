# Issue #344 第1段階 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Issue指定の最初のPR単位で、不要なpytest 12ケースを削除し安全ガードの代表を維持する。

**Architecture:** 動作コードを変えず、2つの既存テストファイルだけを縮約する。runnerの1担当へ1 Taskを依頼し、controllerが収集差分・全体回帰・レビューを統合確認する。

**Tech Stack:** Python 3.14 / uv / pytest / Git / agent-runner。

**Spec:** `docs/superpowers/specs/2026-11-08-issue-344-review-test-pruning-design.md`（draft、実行許可のみ）。

状態: draft。利用者指示と実装/ループ割当はSpecの管理・決定記録に従う。内容承認を推測しない。

## Global Constraints

- 編集するテストは `.agents/skills/pr-review/tests/test_pr_review_workspace.py` と `.agents/skills/pr-review-fix-loop/tests/test_loop_state.py` だけ。
- S・F∩S・曖昧な候補を残し、Dの代表と正しい入力が通る対照を残す。件数目標を理由に削除しない。
- 新しいテスト関数・入力ケース・削除検査テストを追加しない。Spec #12の既存assert移管のみ行う。
- 動作コード・SKILL.md・AGENTS.md・bashテスト・ローカルワールド・CIを変えない。
- 第1段階だけを `Refs #344` のPRにする。残る4領域の完了やIssue全体の89件棚卸しを主張しない。
- 現在の基準 repository/ref/SHA: usaturn/create-reso-world / origin / refs/heads/main / 776673b57d848f304e369a4da8e73471ea56f6ad。当初の基準c871b718f64233ce4d21cf0468d978516f0562d0は履歴・初回検証記録として保持。利用者「main 取り込んで再レビューして」による明示的な再開。
- 実装担当は pi_opencode-go_deepseek4-flash_max、fallback無し。失敗を理由にcontrollerが実装を引き取らない。

## Review Focus

新しい挙動を実装しないためテストを追加しない。残る既存代表が次を守るかレビューと実行で確認する。

1. 保存先fingerprintの競合で他者レビューを上書きしない。
2. repository/modelのpin違いを保存前に拒否する。
3. createの既存レビューコピーと非regular/race拒否を維持する。
4. snapshotのtracked両列とuntracked、index/lock不変を維持する。
5. finalizeの未マージ誤報告でcycleを完了保存しない。正常なマージは通る。

## 受け入れ基準

1. Dev Container・uv/Python 3.14・ローカルの偽CLI/一時gitリポジトリで検証する。実モデル起動は実装担当と指定レビューだけであり、テスト入力には本物のCLI/課金APIを使わない。
2. 上表の候補判断を実装・PRへ対応付ける。文字列の一致だけでなく、ガードの同一性と残る正例/負例で判断する。
3. 本PRの全収集件数は1309から12減る想定（1297）。対象297ケースは285となる想定。実測で照合し、増加や別領域の欠落は認めない。
4. 保存先改変、競合、モデル取り違え、repository指定、既存レビュー内容、merge誤報告を防ぐS/F∩Sを維持する。動作コード・SKILL.md・AGENTS.md・bashテスト・ローカルワールド・CIは変更しない。
5. `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、diff checkを実施し成功を確認する。
6. 新しいテスト関数・入力ケース・削除確認用テストは追加しない。#12の既存assertの移管のみ認める。
7. 残る4領域とIssue全体の棚卸し・完了判断は対象外。高速化#345も対象外。


## 実装前の要件照合

| Spec条件 | 担当 | 観測結果 / 検証 |
| --- | --- | --- |
| 棚卸し12項目と保護の維持 | Task 1 / Task reviewer | 変更前後の関数・ケース・assertを表に照合。Dの代表と正例を読む |
| 収集数は削除分だけ減る | 統合担当controller | 全体1309→1297、対象297→285。新規入力0・削除12を一時ログで確認（単一ケース化によるnodeidのsuffix除去は同じ入力へ対応付ける） |
| 動作コード等を変更しない | Task 1 / controller | captured baseからのgit diffとallowed_filesの照合 |
| pytest/bash/layout成功 | Task 1は対象回帰、controllerは全体 | ログ、HEAD、clean状態、argv、終了コードを保存 |
| 公開単位と実際のIssue状態 | controller | Refs、PR/base/head、ループ結果、Issue stateを読む |

共有前提は「同じガードを通る代表が残ること」。ファイル単位の成功だけでは証明しない。ガードと正例/負例の対応、収集差分を統合担当が確認する。外部APIや入力形式の新規仕様は無い。

### Task 1: 棚卸しに従い既存テスト2ファイルを縮約する

**Files:**
- Modify: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`
- Modify: `.agents/skills/pr-review-fix-loop/tests/test_loop_state.py`

**Interfaces:**
- Consumes: Spec「棚卸し表」の12候補と「維持に回す候補」、変更前297ケース/全体1309ケース。
- Produces: 同じ安全性を守る既存代表、対象285ケース。公開インターフェースと動作コードは不変。

**テスト要否:** 新規テスト不要（削除の検査はF、Issueも新規追加を禁止）。代わりに既存の正例/負例と対象全体を実行する。Spec #12のcycle.state=planning assertは代表へ移す。

- [x] **Step 1:** Specの全12行と保持代表を読む。assert・ガードに未解消の疑義があれば勝手に削らず報告する。
- [x] **Step 2:** Spec #1/#2/#3/#9/#12の5関数を削除。#4/#5/#6/#7/#8/#10/#11の7ケースを削除し、不要なparametrize/引数/分岐だけを片付ける。
- [x] **Step 3:** #12固有の未保存assertを `test_no_fix_needed_needs_a_merged_finalize_result_at_the_same_head` の未マージ拒否直後へ移す。以後の正常マージ対照も残す。
- [x] **Step 4:** 孤立したimport/helper/fixtureがあるか確認し、削除候補のみが使っていたものだけ片付ける。S/F∩S/他利用helperを削らない。
- [x] **Step 5:** `uv run --locked pytest .agents/skills/pr-review/tests .agents/skills/pr-review-fix-loop/tests -q` を同期実行し成功を確認。`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools --collect-only -q` で1297、対象285を照合。`git diff --check` を実行。
- [x] **Step 6:** 明示2パスだけstageして `test: prune redundant review workflow cases for issue 344` でcommit。自己確認と件数・所要時間・ログを報告。

## 統合確認・公開（controller）

- [ ] runnerの結果がimportableならacceptし、毎回ログ要点をledgerへ写してcleanupする。
- [ ] feature worktreeで対象回帰と収集差分を再検証。Taskレビューは同じbrief/受け入れ基準・レポート・diffを渡す。
- [ ] 最後のブランチ全体レビューを1回行い、Spec/Planと残る代表の整合を確認する。
- [ ] Spec/Planへ実測結果と候補判断の最終状態を記録しcommit。最後のcommit後clean HEADで全pytest・run-tests・layout・diff checkを同期実行し検証記録を残す。
- [ ] base/Issue/競合を再確認し、Gitleaksで捕捉baseから検査したSHAだけをpush。PR作成後base/headを照合。
- [ ] 指定3名のループを起動。マージはループ内finalize.pyだけが実施する。後続4領域をIssueコメント・最終報告へ明記しIssueを未完了のまま保つ。

## 実行方式

`subagent-driven-development` の1 Task。実装はissue-to-prの `implement_task.py` で指定runner担当へ委譲する。依頼は直列、同一worktreeへ複数workerを書き込ませない。Task reviewと全体reviewは読み取り専用のsp-review。controllerは文書・検証・裁定・GitHub操作を担当する。

## 実行予算

全体能動時間300分。準備・監査30分、実装とTask review30分、統合回帰・公開40分、レビュー修正ループ180分（既定3サイクル×レビュー最大45分+計画修正15分）、予備20分。

- 一次担当の役割期限90分（runner管理）。予約枠0、無進捗による独自停止は設定せず同期終了を待つ。レビュー期限45分はrunner管理。
- 調査sp-reconは1回、Task reviewer1回、全体reviewer1回。利用者の追加指示「main 取り込んで再レビューして」により、統合後の全体レビューをもう1回行う。実装1依頼を基本とし、context不足/rejectedの同じ失敗は再試行1回まで。レビュー修正はSDD上限と全体予算の小さい方まで。runner failedは停止。実モデルによるテストsmokeは行わない。
- 各phase境界・予算50%/100%・worker失敗直後にcheckpoint。100%・安全失敗は停止。
- ledger: `/workspaces/reso-world/tmp/agents/issue-344.utaqtap6/budget.jsonl`。
- SDD領域: 同じsessionの `sdd/2026-11-08-issue-344-review-test-pruning/`。ログはworktreeへ置かない。
- 縮小候補: 安全性の疑義が残る候補は削らず維持へ戻し、理由・実際の件数へSpec/Planを更新する。別領域へ拡張しない。

## contingency（代替策）

候補に独立したS保護が判明した場合は保持へ戻す（目的は件数でなく安全な削減）。意味を保つ最小の表記/fixture整理差はledgerへ記録する。基準・安全境界を変える必要があれば停止。最初の実出力が想定と違えば、収集nodeidと実ガードを確認し、数を合わせるための追加削除は行わない。指定担当の失敗はselfへ切り替えない。base移動・所有権競合・秘密情報検出はissue-to-prの停止条件を守る。

## 完了記録

実装とTaskレビューを完了。変更前297 passed/443.49s・全体1309 collected、取り込み後285 passed/253.52s・全体1297 collected（すべてexit0）。候補12件を表どおり削除し、cycle.state assertは代表へ移管。raw nodeidは15削除/3追加だが、3件は同じ入力のparametrize suffix除去であり新しいケースは無い。Taskレビューは仕様準拠・品質Approved、指摘0。

実装は利用者指定のrunner担当（観測opencode-go/deepseek-v4.1-flash、effort=max）。1回目3261.66秒は他worktreeのoutside_changesでrejected・未取込（因果は未確定）、2回目374.44秒をacceptしcommit fb7f66db254fc259bcca9a049f9dd3270451df81を取り込んだ。両試行は停止確認済み・cleanupのretained=[]。初回のテスト結果は採用したfeatureの検証には使わない。

初回最終HEADの全体pytest1297 passed/873.29秒、bash27本PASS、layout/diff checkも成功し、全体レビュー指摘0だったが、公開前のbase移動で停止した。公開未実施。

利用者「main 取り込んで再レビューして」により既存featureへmain `776673b57d848f304e369a4da8e73471ea56f6ad` を競合無しで取り込んだ（merge commit `b104ea8c63cfa450a0d45e6b7b2f45fcc5a4f68c`）。実装のやり直しは不要。今回の文書commit後、新HEADで収集・対象と全体pytest・bash/layout/diff checkを実行し、追加の全体レビューを1回行う。検証は実行後にresume-verification-record.json / resume-checks.jsonへ記録する。基準JSONはresume-code-base.jsonであり、初回記録と混ぜない。

証拠は /workspaces/reso-world/tmp/agents/issue-344.utaqtap6/ とPR本文に保存し、未実行の確認を成功としない。状態draftは実行許可と内容承認を区別するため維持。
