# SDD 受け入れ基準と指摘の裁定 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Issue #120 の7項目を、既存の停止条件・テスト採用基準・Pi の権限を変えずに共通規約へ取り込む。

**Architecture:** `AGENTS.md` の SDD 節へ集約する。共有の判断基準を実装担当とレビュー担当に同じ形で渡し、controller が範囲外指摘を裁定する。

**Tech Stack:** Markdown、既存 bash/pytest、Pi 同期 role subagent。

**Spec:** `docs/superpowers/specs/2026-10-26-create-reso-world-issue120-sdd-acceptance-design.md`

## 管理・実行方式

- 文書管理・対象: usaturn/create-reso-world、Issue #120、状態 `draft`、開始 HEAD `5b2c535`。
- 実行許可: `issue-to-pr #120 --merge --max-cycles 3`。内容承認は未取得。確認コピー・実装前の利用者確認は同スキルにより省略する。
- 1 Task の同期 SDD。実装・タスクレビュー・最終レビューは別の子へ委譲する。単一節の変更で分割すると共有状態が重なるため並列 writer は作らない。
- controller が Task の完了チェック・要件照合・行動比較・最終全検証・公開を担当する。子は Plan の metadata を変更しない。

## Global Constraints

- 変更対象は `AGENTS.md` の「SDD 実行運用」のみ。既存の実行予算・作業領域・監視・同期テストの規則を保持する。
- 新しい Plan に適用し、既存の Spec・Plan、review-fix-planning の採否基準、共有 fixture、スキルや実行コードは変更しない。
- Pi の読み取り専用レビューと同期実行の制限は変更しない。
- 文書の固定文言テストは F なので追加しない。

## Review Focus

- 実装前テスト化が F/L の固定文言テストを強制しないこと（Task 1 の文書照合）。
- 最初の RED の差異が仕様変更や安全境界の回避にならないこと（Task 1 のシナリオ）。
- brief が同じ基準を持ち、指定文言自体の誤りも指摘できること（Task 1 のシナリオ）。
- 範囲外指摘の裁定が原文転送と混ざらないこと（Task 1 のシナリオ）。
- issue-to-pr 以外の連続実行指示で確認を省略しないこと、Pi の最終レビューが権限を拡張しないこと（Task 1 の文書照合）。

## 受け入れ基準

- 動作環境: Claude Code・pi の subagent-driven-development・executing-plans。Pi の読み取り専用レビューと同期実行の制限は変更しない。
- 実入力: 新しく作成する Plan、実装担当とタスクレビュー担当への brief、レビュー指摘の原文。実際の入力の形（複数行・非 ASCII 等）は各 Plan が対象に応じて記す。
- 防御範囲: Plan の動作環境・実入力・対象条件と対象外の反例/設定を明記し、同じ受け入れ基準を双方の brief に写す。指摘された文言自体の妥当性もレビュー対象とする。範囲外・Plan と矛盾する指摘は修正前に裁定・記録し、採用した指摘は原文のまま渡す。既存文書の遡及変更やレビュー後の採否基準の変更は対象外。

## 要件・担当・証拠

7項目全ては Task 1 が担当する。controller は、移植元 `e80433ab2d59620a279d4c4f95a8a78a82a4cc3e` の差分と Issue 本文を独立根拠に照合する。条件1/2/3/4/5は同じ仮想 Issue の前後比較、条件6/7は権限・委任の文書照合でも確認する。共有条件は実装前テスト化と既存テスト採用基準、最終レビューとPiの実行制限、確認省略とissue-to-prの委任。controller が全て統合確認する。

## 実行予算

能動時間300分（準備・設計30、実装と行動比較25、レビュー20、全検証15、公開10、ループ最大3×60、予備20）。開始前の調査・baseline約15分も壁時計内訳として最終報告に含める。ledger は `/workspaces/reso-world/tmp/agents/issue-120.frs5sdx4/budget.jsonl`、SDD は同じ session の `sdd/2026-10-26-create-reso-world-issue120-sdd-acceptance/`。

同期子は目安10分（最終レビュー15分）、保存予約2分。停止APIがないので強制打ち切りは宣言せず、同期終了まで待つ。loop の review 期限45分・fixの期限90分は runner が管理し、同時に100%予算を越えないようphase境界で確認する。信頼性失敗は同じ署名で再試行1回、安全失敗は全停止。行動評価は前後各1回を基本とし、形式不備・不明確な観測時だけ追加で前後1組。checkpoint はphase境界、50%/100%、失敗直後。縮小候補は追加評価の省略（必須の1組は維持）、切り出し候補は範囲外のスキル改修。100%で停止し勝手に延長しない。

## contingency

最初の RED が実出力形式/API前提違いで失敗したら、仕様の意味を変えない最小修正を ledger に記録して継続する。意味・安全境界・実装対象を変える場合は停止する。行動比較の変更前が既に一部を満たす場合は、その事実を記録し改善を捏造しない。Pi child のコマンド実行不可は調整役が実行・結果返却で補い、権限を変えない。

### Task 1: SDD 共通規約を更新し前後の行動を比較する

**Files:** Modify `AGENTS.md` の「SDD 実行運用」のみ。controller の記録は既存 Spec/Plan へ追記可。未追跡の評価・ログは親 session に保存。

**Interfaces:** Consumes 現行のSDD節と次の受け入れ基準。Produces 新しい Plan と brief・裁定のための共通規約。

**受け入れ基準（実装担当・レビュー担当に同じ本文を渡す）:**
- 動作環境: Claude Code・pi の subagent-driven-development・executing-plans。Pi の読み取り専用レビューと同期実行の制限は変更しない。
- 実入力: 新しく作成する Plan、実装担当とタスクレビュー担当への brief、レビュー指摘の原文。実際の入力の形（複数行・非 ASCII 等）は各 Plan が対象に応じて記す。
- 防御範囲: Plan の動作環境・実入力・対象条件と対象外の反例/設定を明記し、同じ受け入れ基準を双方の brief に写す。指摘された文言自体の妥当性もレビュー対象とする。範囲外・Plan と矛盾する指摘は修正前に裁定・記録し、採用した指摘は原文のまま渡す。既存文書の遡及変更やレビュー後の採否基準の変更は対象外。

**テストの要否:** 文書固定値は F のため追加しない。controller が writing-skills の行動比較を変更前後各1回行う。実装担当は文書照合・`git diff --check`・`bash scripts/check-layout.sh` を同期実行し、既存全 suite は controller が変更後に1回実行する。

- [x] **Step 1:** controller が同じ小さな Issue シナリオを固定し、変更前の規則で Plan・双方の brief・実出力差/範囲外指摘への判断を fresh context の子に生成させる。原文と観測を親 session に保存する。
- [x] **Step 2:** 実装担当が7項目をSDD節へ追加する。contingency、3点の受け入れ基準（テストは採用基準に従う）、brief共通基準と指定文言の意味照合、範囲外指摘の事前裁定、原文転送、具体的疑いに限定した最終再現（Piはcontroller実行）とend-to-endの担当分割、Plan提示とissue-to-pr限定省略。用語は初出で controller（司令塔）・ledger（進捗記録）・brief（依頼書）と説明し、既存規則を保つ。
- [x] **Step 3:** 実装担当が7項目・対象外・既存5項目を照合し、`git diff --check` と `bash scripts/check-layout.sh` を実行、`docs(agents): align SDD acceptance criteria and review adjudication` として AGENTS.md のみ commit、詳細レポートを指定パスに保存する。
- [x] **Step 4:** controller が同じシナリオを変更後の規則・fresh context で実行し、基準節・双方のbriefの一致・裁定/原文転送・意味を保つ差異対応を前後比較する。タスクレビューと要件照合を行い、結果をこのPlanへ追記する。最終全体レビューとREADMEの3検証は、次節の統合・公開で行う。

## 統合・公開

controller がTask完了を記録し、最後のcommit後のcleanなHEADでREADMEの3コマンドを実行、argv・終了コード・ログをsessionのchecks-fileへ保存する。変更前はbash23・pytest1237・layout成功。秘密検査を通った同じSHAのみpushし、`Closes #120` のPRをmain向けに作る。`--merge --max-cycles 3` の既定割当てを使うループへ進み、最終結果とIssue状態を確認する。公開前にIssue/競合を再確認。private CIは確認しない。

## Task の結果（2026-10-26）

- Task 1: `d3e6e1a..112d998`。実装 `8c5647c`、要件照合による修正 `112d998`。タスクレビューは spec適合・品質Approved、修正後の限定レビューはI1〜I6全てADDRESSED、新しい問題なし。
- 初版に残った欠落: 最初のREDでの意味保持/意味変更の分岐、基準節と実装前テストの時点、レビュアー限定資料の禁止、修正手段の付加禁止、レビュアーの流れ単位の分割、提示する3点。Specの既存要件との照合で修正し、新しい要求は足していない。
- 観測ログ: `/workspaces/reso-world/tmp/agents/issue-120.frs5sdx4/` の `scenario.md`、`behavior-before.md`、`behavior-after.md`、`behavior-after-fix.md`、`integration-findings.md`、`task-1-report.md`。
- 前比較（fresh sp-research、1回）ではレビュー担当だけへのSpec追加を許し、指摘原文へ具体的な修正手段を付け足した。初回の後比較では両briefへ同じ基準を全文記載し、レビュー担当限定資料を拒否したが、修正手段の付加は残った。
- 修正後に同一シナリオの後比較を追加1回実施し、原文への修正手段付加をしないことと、範囲外指摘を作業に混ぜないことを観測した。この標本ではbriefの本文コピーを「§1.2をそのまま貼る」という参照で省略したため、最終標本だけで全文コピーまで実行したとは扱わない。文書の全文コピー要求は明示したまま維持する。前後全体の完全合格や統計的な効果は主張しない。
- contingency と範囲外指摘の理由付き裁定は変更前にも現れた。これらを新規の改善実績には数えない。
- 実装担当のfocused検証: 文書照合・`git diff --check`・`bash scripts/check-layout.sh` は各修正後に終了0。固定文言テストや実装コードは追加していない。
- controllerがTask内と全体工程の境界を整理した（Step4の全体レビュー・全suiteを統合・公開へ移動）。実施する検証や受け入れ条件は削減していない。
- 作業時間（18:21 UTCまで）: 開始から約50分。調査・設計・baseline約23分、前後の行動比較合計約16分、実装担当約7分、タスク/限定レビュー約4分（丸めたcontroller壁時計内訳）。子の実測は初回4分17秒、修正2分49秒。
- 最終全体レビュー、最後のcommit後の全suiteと秘密検査、PR/ループはこの後に実施する。最終HEAD・コマンドargv・終了コード・ログは同sessionの `checks.json` とPR本文・ループ記録を参照する。未実行の結果をここでは成功としない。
